from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import resume_archived_repair as recovery


@pytest.fixture
def archive(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "path", sys.path[:])
    attempt = tmp_path / "archive" / "attempt-0001"
    (attempt / "fit/search").mkdir(parents=True)
    root = tmp_path / "old-repo"
    root.mkdir()
    case = "test-case"
    task = {
        "source_commit": recovery.FROZEN,
        "original_task_id": case,
        "task_id": "repair-" + case,
        "replay_group": "development_failed",
        "candidate_import_root": str(root),
        "runtime": {"context": "apptainer"},
        "input_sha256": {},
        "original_fit_argv": [
            sys.executable,
            "scripts/fit_dataset.py",
            "--input-dir",
            str(root),
            "--observations",
            str(root / "o"),
            "--arrival-bank",
            str(root / "a"),
            "--compressed-bank",
            str(root / "c"),
            "--search",
            "dense",
            "--output-dir",
            "{attempt_dir}/fit",
        ],
    }
    digest = hashlib.sha256(recovery.canonical(task)).hexdigest()
    started = {"task": task, "task_sha256": digest}
    (attempt / "_started.json").write_text(json.dumps(started))
    events = []
    for tight in (False, True):
        fit = {
            "positive_sigma": {"criterion": -2.0, "eligible": True},
            "sigma_zero": {"criterion": -1.0, "eligible": True},
            "criterion": -1.0,
            "candidates": [{"family": "sigma_zero", "criterion": -1.0}],
            "unresolved_above_envelope": [],
            "log_h": 0.0,
            "h": 1.0,
            "tight": tight,
        }
        events.append({"kind": "fixed_fit", "fit": fit, "elapsed_seconds": len(events) + 1.0})
        free = {k: v for k, v in fit.items() if k not in ("log_h", "h", "tight")}
        events.append(
            {"kind": "free_fit", "tight": tight, "fit": free, "elapsed_seconds": len(events) + 1.0}
        )
    stream = attempt / "fit/search/evaluations.jsonl"
    stream.write_text("".join(json.dumps(e) + "\n" for e in events))
    snapshot = {
        "status": "profile_numerically_resolved",
        "mode": "dense",
        "cutoffs": [3.84],
        "free": {str(t): recovery.compact(events[i]["fit"]) for t, i in ((False, 1), (True, 3))},
        "points": {
            str(t): [recovery.compact(events[i]["fit"])] for t, i in ((False, 0), (True, 2))
        },
        "level_sets": [{"roots": [{"log_h": 0.0}]}],
        "tight_level_sets": [{"roots": [{"log_h": 0.0}]}],
        "mesh_log_h": [0.0],
        "tight_mesh_log_h": [0.0],
        "midpoint_triggers": [],
        "closure_history": [],
        "backend_diagnostics": {"evaluate_calls": 12},
        "criterion_stats": {"mode_failures": 0, "mode_calls": 4},
        "cost": {
            "search": {"elapsed_seconds": 4.1, "fixed_fit_events": 2},
            "post_search_seconds": 0.0,
            "total_fixed_fit_events": 2,
        },
        "evaluation_stream": {"path": str(stream), "sha256": recovery.sha(stream)},
    }
    (attempt / "fit/search_receipt.json").write_text(json.dumps(snapshot))
    binding = {
        name: recovery.sha(attempt / name)
        for name in ("_started.json", "fit/search_receipt.json", "fit/search/evaluations.jsonl")
    }
    binding["task_sha256"] = digest
    monkeypatch.setitem(recovery.CASE_BINDINGS, case, binding)
    return SimpleNamespace(case=case, attempt=attempt, root=root, snapshot=snapshot, events=events)


class SearchStub:
    cutoffs = (3.84,)

    def __init__(self, output):
        self.mode = "dense"
        self.events = output / "search/evaluations.jsonl"
        self.events.parent.mkdir()
        self.stats = {}
        self.criterion = SimpleNamespace(stats={})

    def run(self):
        raise AssertionError("the old search must not run")

    def receipt(self):
        return {"points": self.points, "free": self.free}


def test_restore_complete_candidates_and_reject_search_operations(archive, tmp_path):
    saved = recovery.inspect_archive(archive.case, archive.attempt)
    restored = recovery.restored_search_class(SearchStub, saved, archive.attempt)
    output = tmp_path / "restore"
    output.mkdir()
    search = restored(output)
    search.run()
    assert search.point(0.0)["candidates"] == archive.events[0]["fit"]["candidates"]
    assert search.free[True] == archive.events[3]["fit"]
    assert search.criterion.stats == archive.snapshot["criterion_stats"]
    assert search.stats == archive.snapshot["backend_diagnostics"]
    assert recovery.sha(search.events) == saved["archive_sha256"]["fit/search/evaluations.jsonl"]
    for action in (
        lambda: search.point(1.0),
        lambda: search.point(0.0, refresh=True),
        search.fit_free,
    ):
        with pytest.raises(recovery.RecoveryExecutionError):
            action()


@pytest.mark.parametrize(
    "change", ["incomplete", "missing_candidates", "point_drift", "missing_root", "clock_order"]
)
def test_incomplete_or_inconsistent_state_is_rejected(archive, change):
    snapshot, events = copy.deepcopy(archive.snapshot), copy.deepcopy(archive.events)
    if change == "incomplete":
        snapshot["status"] = "indeterminate"
    elif change == "missing_candidates":
        events[0]["fit"].pop("candidates")
    elif change == "point_drift":
        events[0]["fit"]["criterion"] -= 1.0
    elif change == "missing_root":
        snapshot["level_sets"][0]["roots"][0]["log_h"] = 1.0
    else:
        events[-1]["elapsed_seconds"] = 0.5
    with pytest.raises(ValueError):
        recovery.restore_rows(snapshot, events)


def test_archive_hash_tamper_is_rejected(archive):
    with (archive.attempt / "fit/search/evaluations.jsonl").open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="frozen historical file differs"):
        recovery.inspect_archive(archive.case, archive.attempt)


def test_terminal_original_is_not_recovered_again(archive):
    (archive.attempt / "fit/receipt.json").write_text("{}")
    with pytest.raises(ValueError, match="already has a terminal"):
        recovery.inspect_archive(archive.case, archive.attempt)


def test_pinned_source_rejects_changed_commit_or_tracked_file(tmp_path, monkeypatch):
    root = tmp_path / "source"
    root.mkdir()
    for name in ("scripts/fit_dataset.py", "src/latent_landscapes/spatial_profile.py"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n")

    def git(*args):
        return subprocess.check_output(["git", "-c", "core.hooksPath=/dev/null", *args], cwd=root)

    git("init", "-q")
    git("add", ".")
    git(
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "fixture",
    )
    commit = git("rev-parse", "HEAD").decode().strip()
    monkeypatch.setattr(recovery, "FROZEN", commit)
    assert len(recovery.verify_source(root)) == 2
    (root / "scripts/fit_dataset.py").write_text("x = 2\n")
    with pytest.raises(ValueError, match="tracked changes"):
        recovery.verify_source(root)
    monkeypatch.setattr(recovery, "FROZEN", "0" * 40)
    with pytest.raises(ValueError, match="not pinned"):
        recovery.verify_source(root)


def mock_continuation(
    archive, monkeypatch, *, reject_runtime=False, reject_inputs=False, new_point=False
):
    calls = []

    def runtime(task):
        calls.append("runtime")
        if reject_runtime:
            raise ValueError("running interpreter/container differs from frozen runtime")

    def inputs(task):
        calls.append("inputs")
        if reject_inputs:
            raise ValueError("input/runtime drift")

    campaign = SimpleNamespace(
        verify_source=lambda task: calls.append("source"),
        verify_inputs=inputs,
        verify_runtime=runtime,
    )
    fit = SimpleNamespace(FitSearch=SearchStub, THREAD_ENVIRONMENT=("OMP_NUM_THREADS",))

    def run(args):
        search = fit.FitSearch(args.output_dir)
        search.run()
        classification = "resolved"
        try:
            search.point(1.0 if new_point else 0.0)
        except Exception as error:
            classification = "execution_error" if isinstance(error, OSError) else "numerical_error"
        receipt = {"failure_class": classification}
        (args.output_dir / "receipt.json").write_text(json.dumps(receipt))
        return receipt

    fit.fit_dataset = run
    original = recovery.importlib.import_module

    def imported(name):
        return (
            fit if name == "fit_dataset" else campaign if name == "pbs.campaign" else original(name)
        )

    monkeypatch.setattr(recovery.importlib, "import_module", imported)
    monkeypatch.setattr(recovery, "verify_source", lambda root: {})
    monkeypatch.setattr(recovery, "verify_imports", lambda root, hashes: None)
    monkeypatch.setenv("OMP_NUM_THREADS", "1")
    return calls, fit


def test_recovery_continues_separately_and_preserves_archived_bytes(archive, tmp_path, monkeypatch):
    calls, fit = mock_continuation(archive, monkeypatch)
    before = recovery.inspect_archive(archive.case, archive.attempt)["archive_sha256"]
    output = tmp_path / "recovered"
    report = recovery.recover(
        archive.case, archive.attempt, archive.root, output, recovery.sha(Path(recovery.__file__))
    )
    assert report["status"] == "completed" and report["failure_class"] == "resolved"
    assert recovery.inspect_archive(archive.case, archive.attempt)["archive_sha256"] == before
    assert calls.count("runtime") == calls.count("inputs") == 2
    assert fit.FitSearch is SearchStub
    with pytest.raises(FileExistsError):
        recovery.recover(
            archive.case,
            archive.attempt,
            archive.root,
            output,
            recovery.sha(Path(recovery.__file__)),
        )


def test_runtime_mismatch_rejects_before_creating_output(archive, tmp_path, monkeypatch):
    mock_continuation(archive, monkeypatch, reject_runtime=True)
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="interpreter/container"):
        recovery.recover(
            archive.case,
            archive.attempt,
            archive.root,
            output,
            recovery.sha(Path(recovery.__file__)),
        )
    assert not output.exists()


def test_input_mismatch_rejects_before_creating_output(archive, tmp_path, monkeypatch):
    mock_continuation(archive, monkeypatch, reject_inputs=True)
    output = tmp_path / "rejected-input"
    with pytest.raises(ValueError, match="input/runtime drift"):
        recovery.recover(
            archive.case,
            archive.attempt,
            archive.root,
            output,
            recovery.sha(Path(recovery.__file__)),
        )
    assert not output.exists()


def test_unretained_point_is_execution_error_and_never_promoted(archive, tmp_path, monkeypatch):
    _, fit = mock_continuation(archive, monkeypatch, new_point=True)
    output = tmp_path / "blocked"
    with pytest.raises(recovery.RecoveryExecutionError):
        recovery.recover(
            archive.case,
            archive.attempt,
            archive.root,
            output,
            recovery.sha(Path(recovery.__file__)),
        )
    report = json.loads((output / "recovery.json").read_text())
    assert report["status"] == "execution_failure"
    assert not (output / "fit/receipt.json").exists()
    assert fit.FitSearch is SearchStub


def test_adapter_mismatch_rejects_before_recovery(archive, tmp_path):
    with pytest.raises(ValueError, match="adapter differs"):
        recovery.recover(archive.case, archive.attempt, archive.root, tmp_path / "bad", "0" * 64)
