"""Observe, interrupt and compare one registered real-fit twin without changing its solver."""

from __future__ import annotations

import argparse
import contextlib
import copy
import getpass
import hashlib
import importlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

SOURCE = "432bb6e56e672f9e57f2f7bc369546023b07662e"
PRIOR = "a77e849ce0b0381b5c378b222bacfadce9beaf96"
SELECTION_SHA = "099f28d9a45a8a4eb12b103ddaf23714ed3ced72120bb5c9184c9c75e514dfaf"
PLAN_SHA = "09b627de8e09f26c8e0bf0da556d8aa2d2bac5b57d1d4c4b7a1096a0b9d62207"
JOB_ID = re.compile(r"[0-9]+(?:\[[0-9]*\])?(?:\.[A-Za-z0-9_.-]+)?")
JOB_NAMES = ("ll_tw_s1", "ll_tw_s2", "ll_tw_s3")


class TwinError(RuntimeError):
    pass


class BarrierExpired(SystemExit):
    pass


def sha(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def seal(path: Path, payload: dict[str, Any]) -> None:
    atomic(path, {"payload": payload, "payload_sha256": digest(payload)})


def unseal(path: Path) -> dict[str, Any]:
    saved = read(path)
    if saved.get("payload_sha256") != digest(saved.get("payload")):
        raise TwinError(f"control payload hash differs: {path.name}")
    return cast(dict[str, Any], saved["payload"])


def task_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_plan(path: Path) -> dict[str, Any]:
    plan = read(path)
    if (
        plan.get("schema"),
        plan.get("candidate_commit"),
        plan.get("segments"),
        plan.get("selection_sha256"),
    ) != ("interrupted-real-twin-plan-v1", SOURCE, 3, SELECTION_SHA):
        raise TwinError("twin plan is outside the accepted source, schema or three-segment scope")
    if sha(path) != PLAN_SHA:
        raise TwinError("twin plan differs from the frozen exact shortest-task selection")
    return cast(dict[str, Any], plan)


def select_plan(selection: Path, prior_results: Path) -> dict[str, Any]:
    if sha(selection) != SELECTION_SHA:
        raise TwinError("non-regression selection differs from the frozen 24-task sample")
    selected = read(selection)
    if len(selected["nonregression"]) != 24:
        raise TwinError("selection must have exactly 24 non-regression tasks")
    inventory = []
    for row in selected["nonregression"]:
        path = prior_results / ("repair-" + row["task_id"]) / "_task.json"
        record = read(path)
        if record["status"] != "resolved" or record["source"]["commit"] != PRIOR:
            raise TwinError("prior task is not a resolved frozen A+B+C replay")
        if record["task"]["original_task_id"] != row["task_id"]:
            raise TwinError("prior task identity differs")
        wall = record["wall_seconds"]
        if isinstance(wall, bool) or not math.isfinite(wall) or wall <= 0:
            raise TwinError("prior task walltime is invalid")
        fit_path = path.parent / record["attempt"] / "fit/receipt.json"
        fit_hash = sha(fit_path)
        if record["output_sha256"]["fit/receipt.json"] != fit_hash:
            raise TwinError("prior fit receipt hash differs")
        audit = read(fit_path)["latent_audit"]
        inventory.append(
            {
                "original_task_id": row["task_id"],
                "task_wall_seconds": wall,
                "task_record_sha256": sha(path),
                "fit_receipt_sha256": fit_hash,
                "prior_audit_count": audit["audit_count"],
                "prior_audit_locations": audit["locations"],
            }
        )
    inventory.sort(key=lambda r: (r["task_wall_seconds"], r["original_task_id"]))
    return {
        "schema": "interrupted-real-twin-plan-v1",
        "candidate_commit": SOURCE,
        "selection_sha256": sha(selection),
        "prior_source_commit": PRIOR,
        "selection_rule": "Minimum prior completed task wall_seconds; task ID breaks exact ties.",
        "selected_original_task_id": inventory[0]["original_task_id"],
        "prior_inventory": inventory,
        "segments": 3,
        "interruption_stages": ["search", "latent_audit"],
        "audit_scope": "A rendezvous after actual audit-loop calls; no claim of interrupted "
        "latent-mode numerical solves when the selected task skips them.",
        "fresh_panel_gate": True,
        "replay_launch_gate": False,
    }


def source_task(path: Path, plan: dict[str, Any]) -> dict[str, Any]:
    rows = task_rows(path)
    if len(rows) != 51 or len({r["task_id"] for r in rows}) != 51:
        raise TwinError("source replay must contain exactly 51 unique tasks")
    if (
        sum(r["replay_group"] == "nonregression" for r in rows),
        sum(r["replay_group"] == "development_failed" for r in rows),
    ) != (24, 27):
        raise TwinError("source replay does not preserve the 24+27 groups")
    if any(
        r["source_commit"] != plan["candidate_commit"] or r.get("max_segments") != 3 for r in rows
    ):
        raise TwinError("source replay does not match the frozen candidate or segment cap")
    found = [r for r in rows if r["original_task_id"] == plan["selected_original_task_id"]]
    if len(found) != 1 or found[0]["replay_group"] != "nonregression":
        raise TwinError("selected twin is not the required non-regression task")
    if "--exhaustive-audit" not in found[0]["original_fit_argv"]:
        raise TwinError("the selected task must retain its exhaustive audit")
    return found[0]


def prepare_task(plan_path: Path, source_tasks: Path, repo: Path, control: Path) -> dict[str, Any]:
    plan = load_plan(plan_path)
    source = source_task(source_tasks, plan)
    if repo.resolve() != Path(source["candidate_import_root"]).resolve():
        raise TwinError("twin candidate import root differs from its source task")
    result = copy.deepcopy(source)
    result.update(
        task_id="interrupted-twin-" + source["original_task_id"],
        source_task_id=source["task_id"],
        source_task_sha256=digest(source),
        twin_plan_sha256=sha(plan_path),
    )
    result["argv"] = [
        source["runtime"]["python"],
        str(Path(__file__).resolve()),
        "worker",
        "--plan",
        str(plan_path.resolve()),
        "--source-tasks",
        str(source_tasks.resolve()),
        "--repo",
        str(repo.resolve()),
        "--control-dir",
        str(control.resolve()),
        "--output-dir",
        "{attempt_dir}/fit",
        "--checkpoint-dir",
        "{checkpoint_dir}",
    ]
    result["input_sha256"].update(
        {
            str(Path(__file__).resolve()): sha(Path(__file__)),
            str(plan_path.resolve()): sha(plan_path),
            str(source_tasks.resolve()): sha(source_tasks),
        }
    )
    return result


def register(
    plan_path: Path,
    source_tasks: Path,
    twin_tasks: Path,
    control: Path,
    jobs: list[str],
    controller_job: str,
) -> dict[str, Any]:
    if (
        len(jobs) != 3
        or len(set(jobs)) != 3
        or not all(JOB_ID.fullmatch(j) for j in [*jobs, controller_job])
    ):
        raise TwinError("three distinct native twin jobs and a controller job must be registered")
    if controller_job in jobs:
        raise TwinError("controller may not be a twin worker job")
    plan, twins = load_plan(plan_path), task_rows(twin_tasks)
    source = source_task(source_tasks, plan)
    if len(twins) != 1 or twins[0]["source_task_sha256"] != digest(source):
        raise TwinError("twin task does not bind its source replay task")
    expected = prepare_task(plan_path, source_tasks, Path(source["candidate_import_root"]), control)
    if digest(twins[0]) != digest(expected):
        raise TwinError("twin task changes the registered model, runtime or harness contract")
    value = {
        "schema": "interrupted-real-twin-registration-v1",
        "candidate_commit": plan["candidate_commit"],
        "plan": str(plan_path.resolve()),
        "plan_sha256": sha(plan_path),
        "source_tasks": str(source_tasks.resolve()),
        "source_tasks_sha256": sha(source_tasks),
        "source_task_sha256": digest(source),
        "source_task_id": source["task_id"],
        "twin_tasks": str(twin_tasks.resolve()),
        "twin_tasks_sha256": sha(twin_tasks),
        "twin_task_sha256": digest(twins[0]),
        "harness": str(Path(__file__).resolve()),
        "harness_sha256": sha(Path(__file__)),
        "jobs": [
            {"job_id": job, "job_name": name} for job, name in zip(jobs, JOB_NAMES, strict=True)
        ],
        "controller_job_id": controller_job,
        "controller_job_name": "ll_tw_ctl",
    }
    destination = control / "registration.json"
    if destination.exists():
        raise FileExistsError(destination)
    seal(destination, value)
    return value


def registration(control: Path) -> tuple[dict[str, Any], str]:
    path = control / "registration.json"
    value = unseal(path)
    for key in ("plan", "source_tasks", "twin_tasks", "harness"):
        if sha(Path(value[key])) != value[key + "_sha256"]:
            raise TwinError(f"registered {key} bytes differ")
    if value["harness_sha256"] != sha(Path(__file__)):
        raise TwinError("running harness differs from registration")
    plan = load_plan(Path(value["plan"]))
    source = source_task(Path(value["source_tasks"]), plan)
    twins = task_rows(Path(value["twin_tasks"]))
    if value.get("candidate_commit") != SOURCE or value.get("plan_sha256") != PLAN_SHA:
        raise TwinError("registration is outside the accepted source/plan scope")
    expected = prepare_task(
        Path(value["plan"]),
        Path(value["source_tasks"]),
        Path(source["candidate_import_root"]),
        control,
    )
    if (
        len(twins) != 1
        or digest(source) != value["source_task_sha256"]
        or digest(twins[0]) != value["twin_task_sha256"]
        or digest(twins[0]) != digest(expected)
    ):
        raise TwinError("registered scientific task or harness inputs differ")
    jobs = value["jobs"]
    if (
        len(jobs) != 3
        or [j["job_name"] for j in jobs] != list(JOB_NAMES)
        or len({j["job_id"] for j in jobs}) != 3
        or not all(JOB_ID.fullmatch(j["job_id"]) for j in jobs)
        or value["controller_job_id"] in {j["job_id"] for j in jobs}
        or value["controller_job_name"] != "ll_tw_ctl"
    ):
        raise TwinError("registered native job whitelist differs")
    return value, sha(path)


def pinned_modules(repo: Path, expected: str) -> tuple[Any, Any, Any]:
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo, text=True
    ).strip()
    if actual != expected or dirty:
        raise TwinError("candidate checkout source is not the registered clean commit")
    sys.path[:0] = [str(repo / "scripts"), str(repo / "src")]
    fit = importlib.import_module("fit_dataset")
    checkpoint = importlib.import_module("fit_checkpoints")
    campaign = importlib.import_module("pbs.campaign")
    names = {
        "fit_dataset",
        "fit_checkpoints",
        "run_development_profile",
        "qualify_spatial_profiles",
        "benchmark_spatial_profile",
        "profile_level_sets",
        "mode_diagnosis",
    }
    for name, module in sys.modules.copy().items():
        if name in names or name.startswith(("latent_landscapes", "pbs.")):
            location = getattr(module, "__file__", None)
            if location and not Path(location).resolve().is_relative_to(repo):
                raise TwinError(f"production import is outside the pinned candidate: {name}")
    return fit, checkpoint, campaign


def native_status(
    text: str, expected: dict[str, str], *, owner: str | None = None
) -> dict[str, str]:
    match = re.search(r"^Job Id:\s*(\S+)\s*$", text, re.MULTILINE)
    fields = dict(
        re.findall(
            r"^\s+(Job_Name|job_state|Exit_status|Job_Owner)\s*=\s*(\S+)", text, re.MULTILINE
        )
    )
    if (
        not match
        or match[1] != expected["job_id"]
        or fields.get("Job_Name") != expected["job_name"]
    ):
        raise TwinError("native job identity differs from the registered twin job")
    if not fields.get("Job_Owner") or (owner is not None and fields["Job_Owner"] != owner):
        raise TwinError("native job owner differs from the registered controller owner")
    return fields


def checkpoint_proof(directory: Path) -> dict[str, Any]:
    header = read(directory / "identity.json")
    if header.get("header_sha256") != digest(
        {k: v for k, v in header.items() if k != "header_sha256"}
    ):
        raise TwinError("checkpoint identity header hash differs")
    if header["identity_sha256"] != digest(header["identity"]):
        raise TwinError("checkpoint identity payload hash differs")
    return {
        "checkpoint_dir": str(directory.resolve()),
        "checkpoint_identity_sha256": header["identity_sha256"],
        "checkpoint_header_sha256": sha(directory / "identity.json"),
    }


def validate_pause(
    value: dict[str, Any],
    reg: dict[str, Any],
    reg_sha: str,
    segment: int,
    *,
    now: float,
    max_age: float = 30.0,
) -> None:
    expected = reg["jobs"][segment - 1]
    if value.get("state") != "paused" or value.get("segment") != segment:
        raise TwinError("missed or invalid interruption rendezvous")
    for key in ("candidate_commit", "harness_sha256", "source_task_sha256", "twin_task_sha256"):
        if value.get(key) != reg[key]:
            raise TwinError(f"interruption identity differs: {key}")
    if value.get("registration_sha256") != reg_sha or value.get("job_id") != expected["job_id"]:
        raise TwinError("interruption registration or native worker job differs")
    if not 0 <= now - value["heartbeat_unix"] <= max_age:
        raise TwinError("interruption heartbeat is stale")
    stage = "search" if segment == 1 else "latent_audit"
    if value.get("stage") != stage or stage not in value.get("active_stages", []):
        raise TwinError("interruption is outside the registered active stage")
    proof = value["progress"]
    if segment == 1:
        if (
            proof.get("durable_operation_count", 0) < 1
            or proof.get("completed_real_family_count", 0) < 1
            or proof.get("completed_real_evaluations", 0) < 1
        ):
            raise TwinError("search interruption lacks durable prior and actual pending work")
        operation = (
            Path(value["checkpoint_dir"])
            / "search"
            / (f"operation-{proof['durable_operation_count'] - 1:06d}.json")
        )
        if sha(operation) != proof["last_operation_file_sha256"]:
            raise TwinError("durable prior operation hash differs")
        saved = read(operation)
        if saved.get("payload_sha256") != digest(saved.get("payload")):
            raise TwinError("durable prior operation payload hash differs")
        if saved.get("identity_sha256") != value["checkpoint_identity_sha256"]:
            raise TwinError("durable prior operation checkpoint identity differs")
    elif not (1 <= proof.get("audit_call_ordinal", 0) < proof.get("audit_call_total", 0)):
        raise TwinError("audit interruption is not inside the actual audit loop")
    elif proof["audit_call_ordinal"] != max(1, proof["audit_call_total"] // 2):
        raise TwinError("audit rendezvous is not at the prescribed middle call")
    current = checkpoint_proof(Path(value["checkpoint_dir"]))
    if current != {k: value[k] for k in current}:
        raise TwinError("interruption checkpoint identity changed")


def confirmed_cancel(
    control: Path, segment: int, reg: dict[str, Any], reg_sha: str
) -> dict[str, Any]:
    value = unseal(control / f"cancel-{segment}.json")
    expected = reg["jobs"][segment - 1]
    if (
        value.get("status"),
        value.get("segment"),
        value.get("job_id"),
        value.get("registration_sha256"),
        value.get("qdel_returncode"),
    ) != ("deleted_confirmed", segment, expected["job_id"], reg_sha, 0):
        raise TwinError("previous segment deletion is not bound to this registration")
    proof = value["proof"]
    for key in ("candidate_commit", "harness_sha256", "source_task_sha256", "twin_task_sha256"):
        if proof.get(key) != reg[key]:
            raise TwinError("deletion proof source/task identity differs")
    if proof.get("job_id") != expected["job_id"] or proof.get("registration_sha256") != reg_sha:
        raise TwinError("deletion proof worker registration differs")
    intent_path = control / f"delete-intent-{segment}.json"
    if sha(intent_path) != value["delete_intent_sha256"]:
        raise TwinError("native delete intent hash differs")
    intent = unseal(intent_path)
    if intent["requested_job_id"] != expected["job_id"] or intent["proof"] != proof:
        raise TwinError("native delete intent is not bound to the confirmed rendezvous")
    validate_pause(proof, reg, reg_sha, segment, now=intent["requested_unix"])
    controller_path = control / f"native-controller-before-{segment}.txt"
    if sha(controller_path) != value["native_controller_sha256"]:
        raise TwinError("native controller accounting hash differs")
    controller_fields = native_status(
        controller_path.read_text(),
        {"job_id": reg["controller_job_id"], "job_name": reg["controller_job_name"]},
        owner=value["controller_owner"],
    )
    if controller_fields.get("job_state") != "R":
        raise TwinError("native controller was not running at the deletion request")
    for phase, state in (("before", "R"), ("after", "F")):
        path = control / f"native-{phase}-{segment}.txt"
        if sha(path) != value[f"native_{phase}_sha256"]:
            raise TwinError("native deletion accounting hash differs")
        fields = native_status(path.read_text(), expected, owner=value["controller_owner"])
        if fields.get("job_state") != state:
            raise TwinError("native deletion accounting state differs")
        if phase == "after" and (
            fields.get("Exit_status") in (None, "0")
            or fields["Exit_status"] != value["native_exit_status"]
        ):
            raise TwinError("native deletion was not a nonzero interrupted terminal job")
    return value


def wait_confirmation(
    control: Path, segment: int, reg: dict[str, Any], reg_sha: str, timeout: float = 120.0
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        path = control / f"cancel-{segment}.json"
        if path.exists():
            confirmed_cancel(control, segment, reg, reg_sha)
            return
        time.sleep(1.0)
    raise TwinError("previous segment deletion confirmation is missing")


class Observer:
    def __init__(
        self,
        reg: dict[str, Any],
        reg_sha: str,
        control: Path,
        checkpoint_dir: Path,
        segment: int,
        *,
        hold_seconds: float = 600.0,
    ):
        self.reg, self.reg_sha, self.control = reg, reg_sha, control
        self.checkpoint_dir, self.segment = checkpoint_dir, segment
        self.hold_seconds = hold_seconds
        self.active: list[str] = []
        self.audit_total, self.audit_ordinal = 0, 0
        self.paused = False

    def rendezvous(self, stage: str, progress: dict[str, Any]) -> None:
        if self.paused:
            raise TwinError("duplicate interruption rendezvous")
        self.paused = True
        payload = {
            key: self.reg[key]
            for key in (
                "candidate_commit",
                "harness_sha256",
                "source_task_sha256",
                "twin_task_sha256",
            )
        }
        payload.update(
            state="paused",
            stage=stage,
            segment=self.segment,
            registration_sha256=self.reg_sha,
            job_id=os.environ["PBS_JOBID"],
            worker_pid=os.getpid(),
            active_stages=self.active[:],
            progress=progress,
            **checkpoint_proof(self.checkpoint_dir),
        )
        path = self.control / f"pause-{self.segment}.json"
        deadline = time.monotonic() + self.hold_seconds
        while time.monotonic() < deadline:
            payload["heartbeat_unix"] = time.time()
            seal(path, payload)
            time.sleep(1.0)
        payload.update(state="expired", heartbeat_unix=time.time())
        seal(path, payload)
        raise BarrierExpired("native qdel did not interrupt the registered live rendezvous")

    def install(self, fit: Any) -> None:
        original_stage = fit.Run.stage
        original_family = fit.SpatialProfileCriterion._fit_family
        original_audit_all, original_audit = fit.audit_all, fit.latent_audit
        observer = self

        @contextlib.contextmanager
        def stage(run: Any, name: str, *, guard: bool = True) -> Any:
            observer.active.append(name)
            try:
                with original_stage(run, name, guard=guard):
                    yield
            finally:
                observer.active.pop()

        def family(criterion: Any, *args: Any, **kwargs: Any) -> Any:
            result = original_family(criterion, *args, **kwargs)
            evaluations = sum(int(getattr(candidate, "evaluations", 0)) for candidate in result)
            operations = sorted((observer.checkpoint_dir / "search").glob("operation-*.json"))
            if observer.segment == 1 and "search" in observer.active and operations and evaluations:
                observer.rendezvous(
                    "search",
                    {
                        "durable_operation_count": len(operations),
                        "last_operation_file_sha256": sha(operations[-1]),
                        "completed_real_family_count": 1,
                        "completed_real_evaluations": evaluations,
                        "returned_candidates": len(result),
                        "fixed_h": kwargs.get("fixed_h"),
                        "sigma_zero": kwargs.get("sigma_zero"),
                    },
                )
            return result

        def audit_all(search: Any, diagnosis: Any, *, exhaustive: bool = False) -> Any:
            if not exhaustive:
                raise TwinError("selected twin lost its original exhaustive audit")
            observer.audit_total = len(search.free) + sum(len(p) for p in search.points.values())
            observer.audit_ordinal = 0
            return original_audit_all(search, diagnosis, exhaustive=exhaustive)

        def audit(*args: Any, **kwargs: Any) -> Any:
            result = original_audit(*args, **kwargs)
            observer.audit_ordinal += 1
            if observer.segment == 2 and observer.audit_ordinal == max(
                1, observer.audit_total // 2
            ):
                observer.rendezvous(
                    "latent_audit",
                    {
                        "audit_call_ordinal": observer.audit_ordinal,
                        "audit_call_total": observer.audit_total,
                        "result_performed": result["performed"],
                        "sigma": result["sigma"],
                        "scope": "actual audit-loop call; not a numerical-mode claim",
                    },
                )
            return result

        fit.Run.stage, fit.SpatialProfileCriterion._fit_family = stage, family
        fit.audit_all, fit.latent_audit = audit_all, audit


def worker(args: argparse.Namespace) -> None:
    reg, reg_sha = registration(args.control_dir)
    attempt = args.output_dir.parent.resolve()
    match = re.fullmatch(r"attempt-000([123])", attempt.name)
    if not match or Path(os.environ["LL_TASK_DIR"]).resolve() != attempt:
        raise TwinError("worker must execute inside its preserved campaign attempt")
    segment = int(match[1])
    if os.environ.get("PBS_JOBID") != reg["jobs"][segment - 1]["job_id"]:
        raise TwinError("worker native job differs from its registered segment")
    started = read(attempt / "_started.json")
    if (
        started["task_sha256"] != reg["twin_task_sha256"]
        or digest(started["task"]) != reg["twin_task_sha256"]
    ):
        raise TwinError("worker task identity differs from registration")
    source = source_task(args.source_tasks, load_plan(args.plan))
    if digest(source) != reg["source_task_sha256"]:
        raise TwinError("source replay task changed")
    if segment > 1:
        wait_confirmation(args.control_dir, segment - 1, reg, reg_sha)
    fit, _, campaign = pinned_modules(args.repo.resolve(), reg["candidate_commit"])
    campaign.verify_source(source)
    campaign.verify_runtime(source)
    campaign.verify_inputs(source)
    Observer(reg, reg_sha, args.control_dir, args.checkpoint_dir, segment).install(fit)
    forwarded = source["original_fit_argv"][2:]
    forwarded[forwarded.index("--output-dir") + 1] = str(args.output_dir)
    forwarded += ["--checkpoint-dir", str(args.checkpoint_dir)]
    if args.checkpoint_dir.exists():
        forwarded.append("--resume")
    sys.argv = [str(Path(fit.__file__)), *forwarded]
    result = fit.main()
    if segment != 3:
        raise TwinError("interruption stage completed without its required native deletion")
    campaign.verify_source(source)
    campaign.verify_inputs(source)
    seal(
        args.control_dir / "worker-complete-3.json",
        {
            "status": "completed",
            "segment": 3,
            "job_id": os.environ["PBS_JOBID"],
            "registration_sha256": reg_sha,
            "exit_code": result,
        },
    )


def controller(control: Path, qstat: str, qdel: str, timeout: float) -> None:
    if not math.isfinite(timeout) or timeout <= 0:
        raise TwinError("controller timeout must be finite and positive")
    reg, reg_sha = registration(control)
    if os.environ.get("PBS_JOBID") != reg["controller_job_id"]:
        raise TwinError("controller must run in its registered native job")
    if reg["controller_job_name"] != "ll_tw_ctl":
        raise TwinError("registered controller role/name differs")
    control_identity = {"job_id": reg["controller_job_id"], "job_name": "ll_tw_ctl"}
    own_text = subprocess.check_output([qstat, "-xf", control_identity["job_id"]], text=True)
    own = native_status(own_text, control_identity)
    owner = own["Job_Owner"]
    if own.get("job_state") != "R" or owner.split("@", 1)[0] != getpass.getuser():
        raise TwinError("native controller owner/state does not match this execution")
    initial = control / "native-controller-ready.txt"
    initial.write_text(own_text)
    seal(
        control / "controller-ready.json",
        {
            "status": "ready",
            "job_id": reg["controller_job_id"],
            "registration_sha256": reg_sha,
            "owner": owner,
            "source_commit": reg["candidate_commit"],
            "harness_sha256": reg["harness_sha256"],
            "native_controller_sha256": sha(initial),
            "ready_unix": time.time(),
        },
    )
    deadline = time.monotonic() + timeout
    for segment in (1, 2):
        path = control / f"pause-{segment}.json"
        while not path.exists():
            if (control / f"worker-failed-{segment}.json").exists():
                raise TwinError("worker failed before the required interruption rendezvous")
            if time.monotonic() >= deadline:
                raise TwinError("timed out waiting for a required real-stage interruption")
            time.sleep(1.0)
        proof = unseal(path)
        validate_pause(proof, reg, reg_sha, segment, now=time.time())
        expected = reg["jobs"][segment - 1]
        before = subprocess.check_output([qstat, "-xf", expected["job_id"]], text=True)
        before_fields = native_status(before, expected, owner=owner)
        if before_fields.get("job_state") != "R":
            raise TwinError("registered twin is not natively running at its rendezvous")
        before_path = control / f"native-before-{segment}.txt"
        before_path.write_text(before)
        own_text = subprocess.check_output([qstat, "-xf", control_identity["job_id"]], text=True)
        own = native_status(own_text, control_identity, owner=owner)
        if own.get("job_state") != "R":
            raise TwinError("native controller is no longer running")
        controller_path = control / f"native-controller-before-{segment}.txt"
        controller_path.write_text(own_text)
        proof = unseal(path)
        validate_pause(proof, reg, reg_sha, segment, now=time.time())
        incomplete_stage = "search" if segment == 1 else "latent_audit"
        if (Path(proof["checkpoint_dir"]) / "stages" / (incomplete_stage + ".json")).exists():
            raise TwinError("interruption target stage is already durably complete")
        seal(
            control / f"delete-intent-{segment}.json",
            {
                "segment": segment,
                "proof": proof,
                "native_before_sha256": sha(before_path),
                "requested_job_id": expected["job_id"],
                "requested_unix": time.time(),
            },
        )
        deleted = subprocess.run(
            [qdel, expected["job_id"]], capture_output=True, text=True, check=True
        )
        while True:
            after = subprocess.check_output([qstat, "-xf", expected["job_id"]], text=True)
            fields = native_status(after, expected, owner=owner)
            if fields.get("job_state") == "F":
                break
            if time.monotonic() >= deadline:
                raise TwinError("native deletion did not reach a terminal scheduler state")
            time.sleep(1.0)
        latest = unseal(path)
        if latest.get("state") != "paused" or fields.get("Exit_status") in (None, "0"):
            raise TwinError("deletion did not interrupt the live real-stage rendezvous")
        after_path = control / f"native-after-{segment}.txt"
        after_path.write_text(after)
        seal(
            control / f"cancel-{segment}.json",
            {
                "status": "deleted_confirmed",
                "segment": segment,
                "job_id": expected["job_id"],
                "registration_sha256": reg_sha,
                "proof": proof,
                "native_before_sha256": sha(before_path),
                "native_after_sha256": sha(after_path),
                "native_exit_status": fields["Exit_status"],
                "controller_owner": owner,
                "native_controller_sha256": sha(controller_path),
                "delete_intent_sha256": sha(control / f"delete-intent-{segment}.json"),
                "qdel_returncode": deleted.returncode,
                "qdel_stdout": deleted.stdout,
                "qdel_stderr": deleted.stderr,
            },
        )
    seal(
        control / "controller-complete.json",
        {"status": "completed", "native_qdel_count": 2, "registration_sha256": reg_sha},
    )


def artifacts(
    record_path: Path, campaign: Any, checkpoint: Any
) -> tuple[dict[str, str], dict[str, str], Any]:
    record = read(record_path)
    task, directory = record["task"], record_path.parent
    if not re.fullmatch(r"attempt-[0-9]{4}", record["attempt"]):
        raise TwinError("task record contains an invalid attempt directory")
    attempt = directory / record["attempt"]
    if (attempt / "_task.json").read_bytes() != record_path.read_bytes():
        raise TwinError("root and attempt task records differ")
    listed = record["output_sha256"]
    for name in listed:
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or name == "_task.json":
            raise TwinError("task output inventory contains an unsafe path")
    actual = {}
    for path in attempt.rglob("*"):
        if path.is_file() and path != attempt / "_task.json":
            if not path.resolve().is_relative_to(attempt.resolve()):
                raise TwinError("task output resolves outside its preserved attempt")
            actual[str(path.relative_to(attempt))] = sha(path)
    if actual != listed:
        raise TwinError("task output inventory is incomplete or has changed bytes")
    campaign.verify_record(task, directory, record)
    if record["status"] not in {"resolved", "scientific_failure"}:
        raise TwinError("comparison requires a terminal scientific fit receipt")
    fit_path = attempt / task["result_path"]
    fit = read(fit_path)
    search_path = Path(fit["search"]["receipt"])
    if (
        not search_path.resolve().is_relative_to(attempt.resolve())
        or sha(search_path) != fit["search"]["receipt_sha256"]
    ):
        raise TwinError("nested search receipt hash/path differs")
    search = read(search_path)
    events_path = Path(search["evaluation_stream"]["path"])
    if (
        not events_path.resolve().is_relative_to(attempt.resolve())
        or sha(events_path) != search["evaluation_stream"]["sha256"]
    ):
        raise TwinError("nested event stream hash/path differs")
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    raw = {
        "task_record": sha(record_path),
        "fit": sha(fit_path),
        "search": sha(search_path),
        "events": sha(events_path),
    }
    scientific = {
        name: checkpoint.digest(checkpoint.scientific_payload(value, artifact=name))
        for name, value in (("fit", fit), ("search", search), ("events", events))
    }
    return raw, scientific, record


def compare(control: Path, repo: Path, baseline: Path, twin: Path, output: Path) -> dict[str, Any]:
    reg, reg_sha = registration(control)
    _, checkpoint, campaign = pinned_modules(repo.resolve(), reg["candidate_commit"])
    proofs = []
    for segment in (1, 2):
        value = confirmed_cancel(control, segment, reg, reg_sha)
        proofs.append(
            {
                "segment": segment,
                "cancel_sha256": sha(control / f"cancel-{segment}.json"),
                "stage": value["proof"]["stage"],
                "progress": value["proof"]["progress"],
            }
        )
    baseline_raw, baseline_science, old = artifacts(baseline, campaign, checkpoint)
    twin_raw, twin_science, new = artifacts(twin, campaign, checkpoint)
    if (
        old["task_sha256"] != reg["source_task_sha256"]
        or new["task_sha256"] != reg["twin_task_sha256"]
    ):
        raise TwinError("comparison task identity differs from frozen registration")
    if (
        old["task"]["source_commit"] != reg["candidate_commit"]
        or new["task"]["source_commit"] != reg["candidate_commit"]
    ):
        raise TwinError("comparison numerical source identity differs")
    if (
        old["task"]["runtime"] != new["task"]["runtime"]
        or old["task"]["original_fit_argv"] != new["task"]["original_fit_argv"]
    ):
        raise TwinError("comparison model arguments or runtime differ")
    if new["pbs_job_id"] != reg["jobs"][2]["job_id"]:
        raise TwinError("final twin record belongs to a different native job")
    if old["attempt"] != "attempt-0001" or len(list(baseline.parent.glob("attempt-*"))) != 1:
        raise TwinError("reference fit was interrupted rather than uninterrupted")
    if new["attempt"] != "attempt-0003" or len(list(twin.parent.glob("attempt-*"))) != 3:
        raise TwinError("twin did not use exactly the three registered attempts")
    for index in (1, 2):
        directory = twin.parent / f"attempt-{index:04d}"
        if (directory / "fit/receipt.json").exists():
            raise TwinError("a deleted twin segment contains an unexpected final fit receipt")
        started = read(directory / "_started.json")
        if started["task_sha256"] != reg["twin_task_sha256"]:
            raise TwinError("a deleted twin attempt belongs to a different task")
    complete = unseal(control / "worker-complete-3.json")
    if (
        complete.get("status"),
        complete.get("segment"),
        complete.get("job_id"),
        complete.get("registration_sha256"),
        complete.get("exit_code"),
    ) != ("completed", 3, reg["jobs"][2]["job_id"], reg_sha, 0):
        raise TwinError("final worker completion does not match the registered native job")
    finished_controller = unseal(control / "controller-complete.json")
    if (
        finished_controller.get("status"),
        finished_controller.get("native_qdel_count"),
        finished_controller.get("registration_sha256"),
    ) != ("completed", 2, reg_sha):
        raise TwinError("controller did not confirm both native interruptions")
    baseline_identity = checkpoint_proof(baseline.parent / "checkpoints")
    twin_identity = checkpoint_proof(twin.parent / "checkpoints")
    if (
        baseline_identity["checkpoint_identity_sha256"]
        != twin_identity["checkpoint_identity_sha256"]
    ):
        raise TwinError("baseline and resumed checkpoint source/input/runtime identities differ")
    equal = baseline_science == twin_science
    result = {
        "schema": "interrupted-real-twin-comparison-v1",
        "status": "passed" if equal else "failed",
        "source_commit": reg["candidate_commit"],
        "registration_sha256": reg_sha,
        "harness_sha256": reg["harness_sha256"],
        "baseline_raw_sha256": baseline_raw,
        "twin_raw_sha256": twin_raw,
        "baseline_scientific_sha256": baseline_science,
        "twin_scientific_sha256": twin_science,
        "native_interruptions": proofs,
        "baseline_checkpoint_identity": baseline_identity,
        "twin_checkpoint_identity": twin_identity,
        "control_sha256": {p.name: sha(p) for p in sorted(control.iterdir()) if p.is_file()},
        "normalization": "exact pinned fit_checkpoints.scientific_payload; no extra exclusions",
        "audit_limit": "Selected shortest task has no prior numerical-mode audits; "
        "the synchronized interruption tests the actual audit loop/stage, "
        "not interrupted mode solves.",
    }
    if output.exists():
        raise FileExistsError(output)
    atomic(output, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("select")
    p.add_argument("--selection", type=Path, required=True)
    p.add_argument("--prior-results", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = commands.add_parser("prepare")
    for name in ("plan", "source-tasks", "repo", "control-dir", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p = commands.add_parser("register")
    for name in ("plan", "source-tasks", "twin-tasks", "control-dir"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--jobs", nargs=3, required=True)
    p.add_argument("--controller-job", required=True)
    p = commands.add_parser("worker")
    for name in ("plan", "source-tasks", "repo", "control-dir", "output-dir", "checkpoint-dir"):
        p.add_argument("--" + name, type=Path, required=True)
    p = commands.add_parser("controller")
    p.add_argument("--control-dir", type=Path, required=True)
    p.add_argument("--qstat", default="/opt/pbs/bin/qstat")
    p.add_argument("--qdel", default="/opt/pbs/bin/qdel")
    p.add_argument("--timeout-seconds", type=float, default=43200.0)
    p = commands.add_parser("compare")
    for name in ("control-dir", "repo", "baseline-record", "twin-record", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.command == "select":
        atomic(args.output, select_plan(args.selection, args.prior_results))
    elif args.command == "prepare":
        task = prepare_task(args.plan, args.source_tasks, args.repo, args.control_dir)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as handle:
            handle.write(json.dumps(task, sort_keys=True, allow_nan=False) + "\n")
        print(json.dumps({"task_id": task["task_id"], "task_sha256": digest(task)}))
    elif args.command == "register":
        register(
            args.plan,
            args.source_tasks,
            args.twin_tasks,
            args.control_dir,
            args.jobs,
            args.controller_job,
        )
    elif args.command == "worker":
        try:
            worker(args)
        except BaseException as error:
            match = re.fullmatch(r"attempt-000([123])", args.output_dir.parent.name)
            if match:
                seal(
                    args.control_dir / f"worker-failed-{match[1]}.json",
                    {
                        "status": "failed",
                        "segment": int(match[1]),
                        "job_id": os.environ.get("PBS_JOBID"),
                        "error_type": type(error).__name__,
                        "error": str(error),
                    },
                )
            raise
    elif args.command == "controller":
        controller(args.control_dir, args.qstat, args.qdel, args.timeout_seconds)
    else:
        try:
            result = compare(
                args.control_dir, args.repo, args.baseline_record, args.twin_record, args.output
            )
        except Exception as error:
            if not args.output.exists():
                atomic(
                    args.output,
                    {
                        "schema": "interrupted-real-twin-comparison-v1",
                        "status": "failed",
                        "source_commit": SOURCE,
                        "identity_verified": False,
                        "error_type": type(error).__name__,
                        "error": str(error),
                    },
                )
            raise
        print(json.dumps({"status": result["status"], "source_commit": result["source_commit"]}))
        if result["status"] != "passed":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
