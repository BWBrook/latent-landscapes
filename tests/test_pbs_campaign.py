from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def campaign(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts/pbs/campaign.py"
    spec = importlib.util.spec_from_file_location("pbs_campaign_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module, "source_identity", lambda: {"commit": "a" * 40, "tracked_changes": []}
    )
    monkeypatch.setenv("LL_EXECUTION_CONTEXT", "apptainer")
    monkeypatch.setenv("LL_RUNTIME_SIF_SHA256", hashlib.sha256(b"frozen").hexdigest())
    return module


def make_task(campaign, tmp_path, *, failure="resolved", retry_resolves=False):
    source = tmp_path / "input"
    source.write_text("frozen")
    code = (
        "import json,sys; from pathlib import Path; p=Path(sys.argv[1]); p.mkdir(); "
        f"failure={failure!r}; "
        + (
            "failure='resolved' if 'attempt-0002' in str(p) else failure; "
            if retry_resolves
            else ""
        )
        + "(p/'receipt.json').write_text(json.dumps("
        "{'schema':'fit-dataset-v1','failure_class':failure})); "
        "print(failure)"
    )
    return {
        "task_id": "case",
        "argv": [sys.executable, "-c", code, "{attempt_dir}/result"],
        "source_commit": "a" * 40,
        "input_sha256": {str(source): campaign.sha256(source)},
        "result_path": "result/receipt.json",
        "result_schema": "fit-dataset-v1",
        "runtime": {
            "context": "apptainer",
            "python": sys.executable,
            "sif": str(source),
            "sif_sha256": campaign.sha256(source),
        },
    }


def test_execution_error_retries_without_losing_attempts(campaign, tmp_path):
    task = make_task(campaign, tmp_path, failure="execution_error", retry_resolves=True)
    out = tmp_path / "out"
    first = campaign.run_task(task, out, False)
    assert first["status"] == "execution_failure"
    assert first["exit_code"] == 0
    assert campaign.run_task(task, out, False)["skipped"]
    second = campaign.run_task(task, out, True)
    assert second["status"] == "resolved"
    assert (out / "case/attempt-0001/result/receipt.json").exists()
    assert (out / "case/attempt-0001/_stdout.log").read_text().strip() == "execution_error"
    assert (out / "case/attempt-0002/_stdout.log").read_text().strip() == "resolved"
    assert json.loads((out / "case/attempt-0001/_task.json").read_text()) == first


@pytest.mark.parametrize(
    "failure",
    sorted(["numerical_error", "family_fit_failed", "search_unresolved", "multimodal_latent"]),
)
def test_scientific_failure_is_terminal(campaign, tmp_path, failure):
    task = make_task(campaign, tmp_path, failure=failure)
    out = tmp_path / "out"
    assert campaign.run_task(task, out, False)["status"] == "scientific_failure"
    again = campaign.run_task(task, out, True)
    assert again["skipped"] and again["failure_class"] == failure
    assert not (out / "case/attempt-0002").exists()


def test_resume_rejects_changed_task_or_missing_result(campaign, tmp_path):
    task = make_task(campaign, tmp_path)
    out = tmp_path / "out"
    campaign.run_task(task, out, False)
    with pytest.raises(ValueError, match="task identity changed"):
        campaign.run_task({**task, "source_commit": "b" * 40}, out, False)
    (out / "case/attempt-0001/result/receipt.json").unlink()
    with pytest.raises(FileNotFoundError):
        campaign.run_task(task, out, False)


def test_missing_executable_records_execution_failure(campaign, tmp_path):
    task = make_task(campaign, tmp_path)
    task["argv"][0] = "/nonexistent/executable"
    record = campaign.run_task(task, tmp_path / "out", False)
    assert record["status"] == "execution_failure"
    assert record["error"]["type"] == "FileNotFoundError"
    assert (tmp_path / "out/case/attempt-0001/_task.json").exists()


def test_zero_exit_without_result_is_execution_failure(campaign, tmp_path):
    task = make_task(campaign, tmp_path)
    task["argv"] = [sys.executable, "-c", "pass", "{attempt_dir}"]
    assert campaign.run_task(task, tmp_path / "out", False)["status"] == "execution_failure"


@pytest.mark.parametrize("drift", ["source", "input"])
def test_drift_is_caught_before_launch(campaign, tmp_path, monkeypatch, drift):
    task = make_task(campaign, tmp_path)
    if drift == "source":
        monkeypatch.setattr(
            campaign, "source_identity", lambda: {"commit": "b" * 40, "tracked_changes": []}
        )
    else:
        (tmp_path / "input").write_text("changed")
    record = campaign.run_task(task, tmp_path / "out", False)
    assert record["status"] == "execution_failure" and record["exit_code"] is None
    assert not (tmp_path / "out/case/attempt-0001/result").exists()


def test_reconcile_distinguishes_science_and_execution(campaign, tmp_path):
    tasks = []
    for number, failure in enumerate(("resolved", "numerical_error", "execution_error")):
        task = make_task(campaign, tmp_path, failure=failure)
        task["task_id"] = f"case-{number}"
        tasks.append(task)
        campaign.run_task(task, tmp_path / "out", False)
    tasks.append({**tasks[0], "task_id": "missing"})
    path = tmp_path / "tasks.jsonl"
    path.write_text("".join(json.dumps(t) + "\n" for t in tasks))
    assert campaign.reconcile(SimpleNamespace(tasks=path, out=tmp_path / "out")) == 1
    report = json.loads((tmp_path / "out/_reconcile.json").read_text())
    assert report["resolved"] == ["case-0"]
    assert report["scientific_failure"] == ["case-1"]
    assert report["execution_failure"] == ["case-2"]
    assert report["missing"] == ["missing"]
    (tmp_path / "out/case-0/attempt-0001/result/receipt.json").write_text("changed")
    campaign.reconcile(SimpleNamespace(tasks=path, out=tmp_path / "out"))
    report = json.loads((tmp_path / "out/_reconcile.json").read_text())
    assert report["invalid"] == ["case-0"]


def test_unfinished_attempt_is_preserved(campaign, tmp_path):
    task = make_task(campaign, tmp_path)
    partial = tmp_path / "out/case/attempt-0001"
    partial.mkdir(parents=True)
    (partial / "_started.json").write_text(json.dumps({"task_sha256": campaign.task_digest(task)}))
    (partial / "_stdout.log").write_text("interrupted")
    with pytest.raises(ValueError, match="unfinished attempt"):
        campaign.run_task(task, tmp_path / "out", False)
    assert campaign.run_task(task, tmp_path / "out", True)["attempt"] == "attempt-0002"
    assert (partial / "_stdout.log").read_text() == "interrupted"
