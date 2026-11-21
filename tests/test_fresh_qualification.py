from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prep = load_script("fresh_prepare", "prepare_fresh_qualification.py")
budget = load_script("fresh_budget", "pbs/fresh_campaign.py")


def test_replicate_advances_only_address_in_synthetic_rows():
    old = {
        "address_namespace": 5,
        "datasets": [
            {"dataset_id": f"fixture-{i}", "address": [5, 99, i // 3, 1, 0, 0], "arm": "ABC"[i % 3]}
            for i in range(207)
        ],
    }
    new = prep.next_replicate(old)
    for before, after in zip(old["datasets"], new["datasets"], strict=True):
        assert after == {**before, "address": [*before["address"][:-1], 1]}
        assert before["address"][-1] == 0
    assert new["datasets"][0]["address"] == new["datasets"][2]["address"]
    assert new["datasets"][0]["address"] != new["datasets"][3]["address"]


def test_adapter_changes_only_fit_execution_and_binds_selected_commit():
    task = {
        "source_commit": "a" * 40,
        "argv": ["/env/python", "scripts/fit_dataset.py", "--exhaustive-audit"],
        "result_schema": "fit-dataset-v1",
    }
    adapted = prep.resumable_fit(task)
    assert adapted["max_segments"] == 3
    assert adapted["argv"] == [
        "/env/python",
        "scripts/prepare_solver_repair_replay.py",
        "run-fit",
        "--candidate-commit",
        "a" * 40,
        "--",
        "--exhaustive-audit",
        "--checkpoint-dir",
        "{checkpoint_dir}",
    ]
    assert adapted["result_schema"] == task["result_schema"]


def test_planner_hash_cache_fails_on_input_drift(tmp_path):
    path = tmp_path / "fixed-input"
    path.write_text("same bytes seen once")
    calls = []

    def record(path):
        calls.append(path)
        return budget.digest(path)

    producer = SimpleNamespace(campaign=SimpleNamespace(sha256=record))
    check = prep.memoise_input_hashes(producer)
    original = producer.campaign.sha256(path)
    assert producer.campaign.sha256(path) == original
    check()
    assert calls == [path.resolve()]
    path.write_text("input drift")
    with pytest.raises(ValueError, match="input changed"):
        check()


@pytest.fixture
def ledger(tmp_path):
    for directory in ("tickets", "native", "claims", "logs"):
        (tmp_path / directory).mkdir()
    state = {
        "root": str(tmp_path),
        "jobs": {},
        "owner": "fixture",
        "email": "fixture@example.test",
        "controller_sha256": "0" * 64,
        "environment": {"LL_REPO": str(tmp_path)},
        "earmarked_external_seconds": 25 * 3600,
        "closeout_seconds": 12 * 3600,
    }
    budget.save(tmp_path / "budget.json", state)
    return state


def test_failed_submission_retains_reservation_and_child_cannot_repeat_it(ledger, monkeypatch):
    def broken(*args):
        assert args[:4] == ("qsub", "-h", "-r", "n")
        (record,) = budget.read(Path(ledger["root"]) / "budget.json")["jobs"].values()
        assert record["state"] == "pending_submit"
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(budget, "pbs", broken)
    with pytest.raises(subprocess.CalledProcessError):
        budget.reserve_and_submit(
            ledger, {"kind": "task", "key": "t", "identity": "x"}, 3600, "4gb", notify=False
        )
    resumed = budget.read(Path(ledger["root"]) / "budget.json")
    assert budget.charged(resumed) == (25 + 12 + 1) * 3600 + budget.PBS_MARGIN_SECONDS
    assert len(resumed["jobs"]) == 1


def test_native_terminal_single_run_refunds_but_ambiguous_keeps_full_charge(ledger, monkeypatch):
    root = Path(ledger["root"])
    rows = {}

    def run(*args):
        if args[0] == "qsub":
            name = args[args.index("-N") + 1]
            job = f"{len(rows) + 1}.fixture"
            rows[job] = {
                "job_state": "H",
                "Job_Name": name,
                "Job_Owner": "fixture@fixture",
                "Hold_Types": "u",
                "Rerunable": False,
                "Resource_List": {"ncpus": 1, "walltime": "01:00:00"},
            }
            return job
        assert args[0] == "qrls"
        assert rows[args[1]]["job_state"] == "H"
        rows[args[1]]["job_state"] = "Q"

    monkeypatch.setattr(budget, "pbs", run)
    monkeypatch.setattr(budget, "native_records", lambda jobs: {k: rows[k] for k in jobs})
    one, two = [
        budget.reserve_and_submit(
            ledger, {"kind": "task", "key": key, "identity": key}, 3600, "4gb", notify=False
        )
        for key in ("one", "two")
    ]
    rows[one].update(
        job_state="F",
        run_count=1,
        Exit_status=143,
        resources_used={"ncpus": 1, "walltime": "00:15:03"},
    )
    rows[two].update(job_state="F", Exit_status=1)
    budget.reconcile(ledger)
    resumed = budget.read(root / "budget.json")
    actual = {r["job"]: r["accounted_seconds"] for r in resumed["jobs"].values()}
    assert actual == {one: 904, two: 3600 + budget.PBS_MARGIN_SECONDS}
    assert len(list((root / "native").glob("*-terminal.json"))) == 2


def test_suspicious_native_autorestart_freezes_all_admission(ledger):
    record = {"reserved_seconds": 1000}
    charge, reason = budget.native_charge(record, {"run_count": 2})
    assert charge == 2000 and "anomalous" in reason
    ledger["accounting_fault"] = True
    with pytest.raises(ValueError, match="anomaly"):
        budget.guard_budget(ledger, 1, closeout=True)


def test_closeout_budget_remains_available_at_ordinary_budget_limit(ledger):
    ledger["jobs"]["ordinary"] = {
        "closeout": False,
        "reserved_seconds": budget.CAP_SECONDS - budget.charged(ledger),
    }
    assert budget.charged(ledger) == budget.CAP_SECONDS
    with pytest.raises(ValueError, match="no admissible"):
        budget.guard_budget(ledger, 1)
    budget.guard_budget(ledger, ledger["closeout_seconds"], closeout=True)
    with pytest.raises(ValueError, match="no admissible"):
        budget.guard_budget(ledger, ledger["closeout_seconds"] + 1, closeout=True)


def test_shared_lock_serializes_two_near_cap_reservations(ledger):
    root = Path(ledger["root"])
    ledger["jobs"]["already"] = {
        "closeout": False,
        "reserved_seconds": budget.CAP_SECONDS - budget.charged(ledger) - 1000,
    }
    budget.save(root / "budget.json", ledger)
    child = """
import sys
from pathlib import Path
from fresh_campaign import charged, guard_budget, locked, read, save
root = Path(sys.argv[1])
with locked(root):
    ledger = read(root / 'budget.json')
    try:
        guard_budget(ledger, 1000)
    except ValueError:
        sys.exit(3)
    ledger['jobs'][sys.argv[2]] = {'closeout': False, 'reserved_seconds': 1000}
    save(root / 'budget.json', ledger)
"""
    processes = [
        subprocess.Popen([sys.executable, "-c", child, str(root), key], cwd=budget.SCRIPT.parent)
        for key in ("a", "b")
    ]
    assert sorted(p.wait(timeout=10) for p in processes) == [0, 3]
    assert budget.charged(budget.read(root / "budget.json")) == budget.CAP_SECONDS


def test_fit_slice_skips_terminal_active_and_three_accounted_attempts(ledger, monkeypatch):
    root = Path(ledger["root"])
    freeze = root / "freeze.json"
    freeze.write_text(json.dumps({"panel": {"sha256": "test-panel"}}))
    freeze_ref = {"path": str(freeze), "sha256": budget.digest(freeze)}
    ledger.update(panel_freeze=freeze_ref, source_commit="a" * 40, results_root=str(root))
    rows = {
        key: {
            "task_id": key,
            "source_commit": ledger["source_commit"],
            "input_sha256": {freeze_ref["path"]: freeze_ref["sha256"]},
            "result_schema": "fit-dataset-v1",
            "max_segments": 3,
        }
        for key in ("done", "active", "exhausted", "retry", "fresh")
    }
    for key, states in {
        "active": ("released",),
        "exhausted": ("terminal",) * 3,
        "retry": ("terminal",),
    }.items():
        for index, state in enumerate(states):
            ledger["jobs"][f"{key}-{index}"] = {
                "key": key,
                "identity": budget.task_digest(rows[key]),
                "state": state,
                "reserved_seconds": 100,
                "closeout": False,
            }
    (root / "done").mkdir()
    budget.save(
        root / "done" / "_task.json",
        {
            "task_sha256": budget.task_digest(rows["done"]),
            "status": "scientific_failure",
        },
    )
    task_path = root / "tasks.jsonl"
    task_path.write_text("".join(json.dumps(t) + "\n" for t in rows.values()))
    budget.save(
        root / "plan.json",
        {
            "tasks": list(rows.values()),
            "panel_sha256": "test-panel",
            "source_commit": "a" * 40,
        },
    )
    monkeypatch.setattr(budget, "reserve_and_submit", lambda _, ticket, *a, **k: ticket["key"])
    assert budget.launch_tasks(ledger, task_path, 5) == ["fresh", "retry"]


def test_admission_rejects_duplicate_task_in_a_consistent_plan(ledger):
    root = Path(ledger["root"])
    rows = [{"task_id": "same", "argv": ["one"]}, {"task_id": "same", "argv": ["two"]}]
    path = root / "tasks.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    budget.save(root / "plan.json", {"tasks": rows})
    with pytest.raises(ValueError, match="duplicate task"):
        budget.launch_tasks(ledger, path, 2)
    assert not ledger["jobs"]


def test_worker_accepts_the_reserved_native_id_once(ledger, monkeypatch):
    root = Path(ledger["root"])
    script = root / "fake-aux.sh"
    script.write_text("exit 0\n")
    ticket = root / "tickets" / "ticket.json"
    budget.save(
        ticket,
        {
            "kind": "aux",
            "name": "worker",
            "script": str(script),
            "identity": budget.digest(script),
            "interpreter": "bash",
            "parameters": [],
            "claim": str(root / "claims" / "ticket"),
        },
    )
    ledger["jobs"]["worker"] = {"job": "123.site", "state": "held"}
    budget.save(root / "budget.json", ledger)
    monkeypatch.setenv("PBS_JOBID", "124.site")
    with pytest.raises(ValueError, match="recorded native job"):
        budget.run_ticket(ticket, budget.digest(ticket), root)
    monkeypatch.setenv("PBS_JOBID", "123.site")
    assert budget.run_ticket(ticket, budget.digest(ticket), root) == 0
    with pytest.raises(FileExistsError):
        budget.run_ticket(ticket, budget.digest(ticket), root)
