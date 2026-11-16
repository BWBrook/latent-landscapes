from __future__ import annotations

import contextlib
import getpass
import importlib
import importlib.util
import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


@pytest.fixture
def twin(monkeypatch: pytest.MonkeyPatch) -> Any:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "interrupted_twin_test", root / "scripts/run_interrupted_twin.py"
    )
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def checkpoint(twin: Any, directory: Path) -> dict[str, Any]:
    identity = {
        "source": {"commit": twin.SOURCE},
        "input_sha256": {"data": "same"},
        "runtime": "same",
    }
    header = {
        "identity": identity,
        "identity_sha256": twin.digest(identity),
        "origin": {"host": "node"},
    }
    header["header_sha256"] = twin.digest(header)
    twin.atomic(directory / "identity.json", header)
    payload = {"operation_index": 0, "fit": {"criterion": 3.0}}
    twin.atomic(
        directory / "search/operation-000000.json",
        {
            "identity_sha256": header["identity_sha256"],
            "payload": payload,
            "payload_sha256": twin.digest(payload),
        },
    )
    return header


def registration(twin: Any) -> dict[str, Any]:
    return {
        "candidate_commit": twin.SOURCE,
        "harness_sha256": "harness",
        "source_task_sha256": "source",
        "twin_task_sha256": "twin",
        "jobs": [{"job_id": f"{101 + i}.cluster", "job_name": f"ll_tw_s{i + 1}"} for i in range(3)],
        "controller_job_id": "200.cluster",
        "controller_job_name": "ll_tw_ctl",
    }


def pause(twin: Any, reg: dict[str, Any], directory: Path, segment: int) -> dict[str, Any]:
    value = {
        key: reg[key]
        for key in ("candidate_commit", "harness_sha256", "source_task_sha256", "twin_task_sha256")
    }
    stage = "search" if segment == 1 else "latent_audit"
    value.update(
        state="paused",
        segment=segment,
        stage=stage,
        registration_sha256="registered",
        job_id=reg["jobs"][segment - 1]["job_id"],
        active_stages=[stage],
        heartbeat_unix=time.time(),
        **twin.checkpoint_proof(directory),
    )
    value["progress"] = (
        {
            "durable_operation_count": 1,
            "completed_real_family_count": 1,
            "completed_real_evaluations": 3,
            "last_operation_file_sha256": twin.sha(directory / "search/operation-000000.json"),
        }
        if segment == 1
        else {"audit_call_ordinal": 71, "audit_call_total": 142, "result_performed": False}
    )
    return value


def native(job: dict[str, str], *, owner: str, state: str = "R") -> str:
    return (
        f"Job Id: {job['job_id']}\n    Job_Name = {job['job_name']}\n"
        f"    Job_Owner = {owner}\n    job_state = {state}\n"
        + ("    Exit_status = 271\n" if state == "F" else "")
    )


def exercise_controller(
    twin: Any,
    monkeypatch: pytest.MonkeyPatch,
    control: Path,
    reg: dict[str, Any],
    cp: Path,
    *,
    bad: str | None = None,
) -> list[str]:
    checkpoint(twin, cp)
    for segment in (1, 2):
        twin.seal(control / f"pause-{segment}.json", pause(twin, reg, cp, segment))
    monkeypatch.setattr(twin, "registration", lambda _: (reg, "registered"))
    monkeypatch.setenv("PBS_JOBID", reg["controller_job_id"])
    owner = getpass.getuser() + "@submit-node"
    deleted: list[str] = []

    def qstat(argv: list[str], **kwargs: Any) -> str:
        job = next((v for v in reg["jobs"] if v["job_id"] == argv[-1]), None)
        if job is None:
            job = {
                "job_id": reg["controller_job_id"],
                "job_name": "wrong" if bad == "controller_name" else "ll_tw_ctl",
            }
            return native(
                job,
                owner="other@submit-node" if bad == "controller_owner" else owner,
                state="Q" if bad == "controller_state" else "R",
            )
        return native(
            job,
            owner="other@submit-node" if bad == "worker_owner" else owner,
            state="F" if job["job_id"] in deleted else "R",
        )

    def qdel(argv: list[str], **kwargs: Any) -> Any:
        deleted.append(argv[-1])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(twin.subprocess, "check_output", qstat)
    monkeypatch.setattr(twin.subprocess, "run", qdel)
    twin.controller(control, "qstat", "qdel", 100.0)
    return deleted


def test_real_prior_shortest_is_selected_from_all_24_hash_bound_task_receipts(
    twin: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    selection = {"nonregression": [{"task_id": f"case-{i:02d}"} for i in range(24)]}
    selected = tmp_path / "selection.json"
    twin.atomic(selected, selection)
    monkeypatch.setattr(twin, "SELECTION_SHA", twin.sha(selected))
    for i, row in enumerate(selection["nonregression"]):
        directory = tmp_path / "prior" / ("repair-" + row["task_id"])
        fit = directory / "attempt-0001/fit/receipt.json"
        twin.atomic(fit, {"latent_audit": {"audit_count": 0, "locations": 142}})
        twin.atomic(
            directory / "_task.json",
            {
                "status": "resolved",
                "source": {"commit": twin.PRIOR},
                "task": {"original_task_id": row["task_id"]},
                "wall_seconds": 10.0 if i in (3, 4) else 20 + i,
                "attempt": "attempt-0001",
                "output_sha256": {"fit/receipt.json": twin.sha(fit)},
            },
        )
    plan = twin.select_plan(selected, tmp_path / "prior")
    assert plan["selected_original_task_id"] == "case-03"
    assert len(plan["prior_inventory"]) == 24
    assert plan["prior_inventory"][0]["prior_audit_count"] == 0
    record = tmp_path / "prior/repair-case-03/attempt-0001/fit/receipt.json"
    record.write_text("tampered")
    with pytest.raises(twin.TwinError, match="hash differs"):
        twin.select_plan(selected, tmp_path / "prior")


def test_preparation_preserves_model_runtime_and_registration_rejects_mutation(
    twin: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    plan_path, source_path = tmp_path / "plan.json", tmp_path / "source.jsonl"
    twin.atomic(
        plan_path,
        {
            "schema": "interrupted-real-twin-plan-v1",
            "segments": 3,
            "selection_sha256": twin.SELECTION_SHA,
            "candidate_commit": twin.SOURCE,
            "selected_original_task_id": "case-00",
        },
    )
    monkeypatch.setattr(twin, "PLAN_SHA", twin.sha(plan_path))
    rows = [
        {
            "task_id": f"repair-case-{i:02d}",
            "original_task_id": f"case-{i:02d}",
            "replay_group": "nonregression" if i < 24 else "development_failed",
            "source_commit": twin.SOURCE,
            "max_segments": 3,
            "candidate_import_root": str(tmp_path),
            "input_sha256": {"data": "same"},
            "runtime": {"python": "/original/python"},
            "original_fit_argv": [
                "/original/python",
                "scripts/fit_dataset.py",
                "--exhaustive-audit",
                "--output-dir",
                "{attempt_dir}/fit",
            ],
        }
        for i in range(51)
    ]
    source_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    prepared = twin.prepare_task(plan_path, source_path, tmp_path, tmp_path / "control")
    assert prepared["original_fit_argv"] == rows[0]["original_fit_argv"]
    assert prepared["runtime"] == rows[0]["runtime"]
    assert prepared["input_sha256"]["data"] == "same"
    tasks = tmp_path / "twins.jsonl"
    tasks.write_text(json.dumps(prepared) + "\n")
    reg = twin.register(
        plan_path,
        source_path,
        tasks,
        tmp_path / "control",
        ["101.cluster", "102.cluster", "103.cluster"],
        "200.cluster",
    )
    assert reg["source_task_sha256"] == twin.digest(rows[0])
    checked, _ = twin.registration(tmp_path / "control")
    assert checked["candidate_commit"] == twin.SOURCE
    forged = twin.unseal(tmp_path / "control/registration.json")
    forged["candidate_commit"] = "other"
    twin.seal(tmp_path / "control/registration.json", forged)
    with pytest.raises(twin.TwinError, match="outside the accepted"):
        twin.registration(tmp_path / "control")
    prepared["runtime"]["python"] = "/changed/python"
    tasks.write_text(json.dumps(prepared) + "\n")
    with pytest.raises(twin.TwinError, match="changes the registered"):
        twin.register(
            plan_path,
            source_path,
            tasks,
            tmp_path / "other-control",
            ["104.cluster", "105.cluster", "106.cluster"],
            "201.cluster",
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("candidate_commit", "other"),
        ("segments", 4),
        ("schema", "other"),
        ("selection_sha256", "other"),
    ],
)
def test_other_source_or_plan_scope_is_rejected_before_task_preparation(
    twin: Any, tmp_path: Path, field: str, value: Any
) -> None:
    plan = {
        "schema": "interrupted-real-twin-plan-v1",
        "candidate_commit": twin.SOURCE,
        "segments": 3,
        "selection_sha256": twin.SELECTION_SHA,
    }
    plan[field] = value
    path = tmp_path / "plan.json"
    twin.atomic(path, plan)
    with pytest.raises(twin.TwinError, match="outside the accepted"):
        twin.prepare_task(path, tmp_path / "does-not-exist", tmp_path, tmp_path / "control")


@pytest.mark.parametrize(
    "change",
    ["job", "stale", "stage", "no_evaluation", "no_durable", "audit_end", "audit_not_middle"],
)
def test_live_pause_rejects_wrong_native_identity_or_unproven_progress(
    twin: Any, tmp_path: Path, change: str
) -> None:
    reg = registration(twin)
    checkpoint(twin, tmp_path)
    segment = 2 if change.startswith("audit") else 1
    value = pause(twin, reg, tmp_path, segment)
    if change == "job":
        value["job_id"] = "999.cluster"
    elif change == "stale":
        value["heartbeat_unix"] -= 31
    elif change == "stage":
        value["active_stages"] = []
    elif change == "no_evaluation":
        value["progress"]["completed_real_evaluations"] = 0
    elif change == "no_durable":
        value["progress"]["durable_operation_count"] = 0
    elif change == "audit_end":
        value["progress"]["audit_call_ordinal"] = 142
    else:
        value["progress"]["audit_call_ordinal"] = 1
    with pytest.raises(twin.TwinError):
        twin.validate_pause(value, reg, "registered", segment, now=time.time())


@pytest.mark.parametrize(
    "bad", ["controller_name", "controller_owner", "controller_state", "worker_owner"]
)
def test_controller_whitelist_blocks_qdel_before_wrong_owner_or_controller(
    twin: Any, monkeypatch: Any, tmp_path: Path, bad: str
) -> None:
    reg = registration(twin)
    with pytest.raises(twin.TwinError):
        exercise_controller(
            twin, monkeypatch, tmp_path / "control", reg, tmp_path / "checkpoint", bad=bad
        )
    assert not (tmp_path / "control/cancel-1.json").exists()
    if bad.startswith("controller"):
        assert not (tmp_path / "control/controller-ready.json").exists()


def test_controller_ready_is_published_after_identity_checks_before_worker_wait(
    twin: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    reg = registration(twin)
    control = tmp_path / "control"
    control.mkdir()
    monkeypatch.setattr(twin, "registration", lambda _: (reg, "registered"))
    monkeypatch.setenv("PBS_JOBID", reg["controller_job_id"])
    owner = getpass.getuser() + "@submit-node"
    own_job = {"job_id": reg["controller_job_id"], "job_name": "ll_tw_ctl"}
    monkeypatch.setattr(
        twin.subprocess, "check_output", lambda *args, **kwargs: native(own_job, owner=owner)
    )

    class WaitReached(RuntimeError):
        pass

    def first_wait(seconds: float) -> None:
        ready = twin.unseal(control / "controller-ready.json")
        assert (ready["status"], ready["job_id"], ready["registration_sha256"], ready["owner"]) == (
            "ready",
            reg["controller_job_id"],
            "registered",
            owner,
        )
        assert ready["native_controller_sha256"] == twin.sha(
            control / "native-controller-ready.txt"
        )
        raise WaitReached

    monkeypatch.setattr(twin.time, "sleep", first_wait)
    monkeypatch.setattr(
        twin.subprocess, "run", lambda *args, **kwargs: pytest.fail("qdel before worker proof")
    )
    with pytest.raises(WaitReached):
        twin.controller(control, "qstat", "qdel", 100.0)


def test_controller_deletes_only_registered_live_jobs_and_seals_native_evidence(
    twin: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    reg = registration(twin)
    control = tmp_path / "control"
    deleted = exercise_controller(twin, monkeypatch, control, reg, tmp_path / "checkpoint")
    assert deleted == ["101.cluster", "102.cluster"]
    for segment in (1, 2):
        assert (
            twin.confirmed_cancel(control, segment, reg, "registered")["native_exit_status"]
            == "271"
        )
    record = twin.unseal(control / "cancel-1.json")
    record["registration_sha256"] = "wrong"
    twin.seal(control / "cancel-1.json", record)
    with pytest.raises(twin.TwinError, match="registration"):
        twin.wait_confirmation(control, 1, reg, "registered", timeout=0.1)


def test_observers_pause_after_genuine_pending_search_work_and_half_actual_audit_calls(
    twin: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    log: list[str] = []

    class Run:
        @contextlib.contextmanager
        def stage(self, name: str, *, guard: bool = True) -> Any:
            yield

    class Criterion:
        def _fit_family(self, **kwargs: Any) -> Any:
            log.append("real-family-return")
            return [SimpleNamespace(evaluations=3)]

    fit = SimpleNamespace(Run=Run, SpatialProfileCriterion=Criterion)

    def audit(*args: Any, **kwargs: Any) -> Any:
        log.append("real-audit-return")
        return {"performed": False, "sigma": 1e-4}

    def audit_all(search: Any, diagnosis: Any, *, exhaustive: bool = False) -> Any:
        return [fit.latent_audit() for _ in range(4)]

    fit.latent_audit, fit.audit_all = audit, audit_all
    observer = twin.Observer(
        registration(twin), "registered", tmp_path / "control", tmp_path / "checkpoint", 1
    )

    def stop(stage: str, progress: Any) -> None:
        log.append("pause:" + stage)
        assert observer.active == [stage]
        if stage == "search":
            assert progress["completed_real_evaluations"] == 3
        else:
            assert progress["audit_call_ordinal"] == 2 and progress["result_performed"] is False
        raise twin.BarrierExpired("test rendezvous")

    monkeypatch.setattr(observer, "rendezvous", stop)
    observer.install(fit)
    with fit.Run().stage("search"):
        fit.SpatialProfileCriterion()._fit_family()
        checkpoint(twin, tmp_path / "checkpoint")
        with pytest.raises(twin.BarrierExpired):
            fit.SpatialProfileCriterion()._fit_family()
    assert log[-2:] == ["real-family-return", "pause:search"]
    observer.segment = 2
    with fit.Run().stage("latent_audit"), pytest.raises(twin.BarrierExpired):
        fit.audit_all(
            SimpleNamespace(free={False: {}}, points={False: {1: {}, 2: {}, 3: {}}}),
            None,
            exhaustive=True,
        )
    assert log[-3:] == ["real-audit-return", "real-audit-return", "pause:latent_audit"]


def fit_record(
    twin: Any,
    directory: Path,
    task: dict[str, Any],
    attempt_number: int,
    job: str,
    *,
    criterion: float = 3.0,
) -> Path:
    for index in range(1, attempt_number + 1):
        twin.atomic(
            directory / f"attempt-{index:04d}/_started.json",
            {"task_sha256": twin.digest(task), "task": task},
        )
    attempt = directory / f"attempt-{attempt_number:04d}"
    events = attempt / "fit/search/evaluations.jsonl"
    events.parent.mkdir(parents=True)
    events.write_text(
        json.dumps({"elapsed_seconds": attempt_number, "criterion": criterion}) + "\n"
    )
    search = attempt / "fit/search_receipt.json"
    twin.atomic(
        search,
        {
            "evaluation_stream": {"path": str(events), "sha256": twin.sha(events)},
            "criterion_stats": {"mode_failures": 0},
            "criterion": criterion,
        },
    )
    fit = attempt / "fit/receipt.json"
    twin.atomic(
        fit,
        {
            "schema": "fit-dataset-v1",
            "failure_class": "resolved",
            "source": {"commit": twin.SOURCE},
            "search": {"receipt": str(search), "receipt_sha256": twin.sha(search)},
            "cost": {"total_wall_seconds": attempt_number},
            "host": str(attempt_number),
            "families": {"spatial": {"criterion": criterion}},
        },
    )
    files = {str(p.relative_to(attempt)): twin.sha(p) for p in attempt.rglob("*") if p.is_file()}
    record = {
        "task": task,
        "task_sha256": twin.digest(task),
        "attempt": attempt.name,
        "status": "resolved",
        "exit_code": 0,
        "pbs_job_id": job,
        "output_sha256": files,
    }
    twin.atomic(attempt / "_task.json", record)
    (directory / "_task.json").write_bytes((attempt / "_task.json").read_bytes())
    return directory / "_task.json"


def comparison_fixture(
    twin: Any, monkeypatch: Any, tmp_path: Path, *, criterion: float = 3.0
) -> tuple[Any, ...]:
    checkpoint_module = importlib.import_module("fit_checkpoints")
    campaign = SimpleNamespace(verify_record=lambda *args: None)
    monkeypatch.setattr(twin, "pinned_modules", lambda *args: (None, checkpoint_module, campaign))
    source = {
        "task_id": "source",
        "source_commit": twin.SOURCE,
        "result_path": "fit/receipt.json",
        "runtime": {"identity": "same"},
        "original_fit_argv": ["python", "fit", "same"],
    }
    task = {**source, "task_id": "twin", "source_task_id": "source"}
    reg = registration(twin)
    reg.update(source_task_sha256=twin.digest(source), twin_task_sha256=twin.digest(task))
    control = tmp_path / "control"
    exercise_controller(twin, monkeypatch, control, reg, tmp_path / "twin/checkpoints")
    checkpoint(twin, tmp_path / "baseline/checkpoints")
    baseline = fit_record(twin, tmp_path / "baseline", source, 1, "300.cluster")
    resumed = fit_record(
        twin, tmp_path / "twin", task, 3, reg["jobs"][2]["job_id"], criterion=criterion
    )
    twin.seal(
        control / "worker-complete-3.json",
        {
            "status": "completed",
            "segment": 3,
            "job_id": reg["jobs"][2]["job_id"],
            "registration_sha256": "registered",
            "exit_code": 0,
        },
    )
    return control, baseline, resumed, reg, checkpoint_module, campaign


@pytest.mark.parametrize("criterion,status", [(3.0, "passed"), (3.000001, "failed")])
def test_exact_scientific_comparison_has_no_new_numeric_tolerance(
    twin: Any, monkeypatch: Any, tmp_path: Path, criterion: float, status: str
) -> None:
    control, baseline, resumed, _, _, _ = comparison_fixture(
        twin, monkeypatch, tmp_path, criterion=criterion
    )
    result = twin.compare(control, tmp_path, baseline, resumed, tmp_path / "comparison.json")
    assert result["status"] == status
    assert result["source_commit"] == twin.SOURCE


@pytest.mark.parametrize(
    "damage", ["omitted", "extra", "unsafe", "wrong_final_job", "wrong_native_accounting"]
)
def test_comparison_refuses_incomplete_inventory_and_native_provenance(
    twin: Any, monkeypatch: Any, tmp_path: Path, damage: str
) -> None:
    control, baseline, resumed, _reg, _cp, _campaign = comparison_fixture(
        twin, monkeypatch, tmp_path
    )
    record = twin.read(resumed)
    attempt = resumed.parent / record["attempt"]
    if damage == "omitted":
        record["output_sha256"].pop("fit/receipt.json")
    elif damage == "extra":
        (attempt / "unlisted.json").write_text("{}")
    elif damage == "unsafe":
        record["output_sha256"]["../outside"] = "hash"
    elif damage == "wrong_final_job":
        record["pbs_job_id"] = "999.cluster"
    else:
        after = control / "native-after-1.txt"
        after.write_text(after.read_text().replace("job_state = F", "job_state = R"))
        cancel = twin.unseal(control / "cancel-1.json")
        cancel["native_after_sha256"] = twin.sha(after)
        twin.seal(control / "cancel-1.json", cancel)
    twin.atomic(resumed, record)
    (attempt / "_task.json").write_bytes(resumed.read_bytes())
    with pytest.raises(twin.TwinError):
        twin.compare(control, tmp_path, baseline, resumed, tmp_path / "comparison.json")
