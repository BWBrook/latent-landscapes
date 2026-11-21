"""Submit and reconcile a single capped fresh-qualification campaign on Kunanyi."""

from __future__ import annotations

import argparse
import fcntl
import getpass
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any

CAP_SECONDS = 9000 * 3600
PBS_MARGIN_SECONDS = 120
WORKER = Path(__file__).resolve().with_name("fresh_worker.pbs")
SCRIPT = Path(__file__).resolve()
NUMERIC_BASE = "432bb6e56e672f9e57f2f7bc369546023b07662e"
SIF_SHA256 = "e71239ad4246ba7a1037d3dd3bc3d29667b7c3081992d95ab33d5d979e3f12ce"
TERMINAL = {"resolved", "scientific_failure", "completed"}
JOB_ID = re.compile(r"[0-9]+(?:\.[A-Za-z0-9_.-]+)?")
SCHEMAS = {
    "sprint2-map-arrival-bank-v1": (8 * 3600, "4gb"),
    "sprint1-history-v1": (15 * 60, "2gb"),
    "fit-dataset-v1": (48 * 3600, "8gb"),
    "sprint2-common-anchors-v1": (48 * 3600, "8gb"),
    "sprint2-free-gradient-v1": (12 * 3600, "8gb"),
    "sprint2-integration-screen-v1": (48 * 3600, "8gb"),
}
Json = dict[str, Any]


def encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path: Path) -> Json:
    return json.loads(path.read_text())


def save(path: Path, value: Json) -> None:
    temp = path.with_suffix(".tmp")
    with temp.open("wb") as stream:
        stream.write(encoded(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def locked(root: Path):
    with (root / "lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def task_digest(task: Json) -> str:
    return hashlib.sha256(encoded(task)).hexdigest()


def walltime(seconds: int) -> str:
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def seconds(value: str) -> int:
    if not re.fullmatch(r"\d+:[0-5]\d:[0-5]\d", value):
        raise ValueError(f"invalid PBS walltime {value!r}")
    hours, minutes, portion = map(int, value.split(":"))
    return hours * 3600 + minutes * 60 + portion


def committed(ledger: Json, *, closeout: bool) -> int:
    return sum(
        record.get("accounted_seconds", record["reserved_seconds"])
        for record in ledger["jobs"].values()
        if record["closeout"] == closeout
    )


def charged(ledger: Json) -> int:
    return (
        ledger["earmarked_external_seconds"]
        + max(ledger["closeout_seconds"], committed(ledger, closeout=True))
        + committed(ledger, closeout=False)
    )


def guard_budget(ledger: Json, requested: int, *, closeout: bool = False) -> None:
    if ledger.get("accounting_fault"):
        raise ValueError("native accounting anomaly freezes all new submissions")
    remaining = CAP_SECONDS - charged(ledger)
    if closeout:
        remaining = ledger["closeout_seconds"] - committed(ledger, closeout=True)
    if not 1 <= requested <= remaining:
        raise ValueError("no admissible reservation under the 9000-core-hour cap")


def panel_reference(path: Path, runtime_hash: str, source: str) -> Json:
    panel = read(path)
    if (
        panel["schema"] != "sprint2-next-qualification-freeze-v1"
        or panel["source_commit"] != source
        or panel["numerical_base_commit"] != NUMERIC_BASE
        or panel["runtime_receipt"]["sha256"] != runtime_hash
        or digest(Path(panel["panel"]["path"])) != panel["panel"]["sha256"]
    ):
        raise ValueError("panel freeze differs from ledger source, runtime or panel")
    return {"path": str(path.resolve()), "sha256": digest(path)}


def initial_ledger(args: argparse.Namespace) -> Json:
    root = args.ledger.resolve()
    runtime = read(args.runtime_receipt)
    if runtime["sif_sha256"] != SIF_SHA256:
        raise ValueError("expected the unchanged Kunanyi SIF")
    if not 1 <= args.closeout_hours < 9000 or not 0 <= args.external_hours < (
        9000 - args.closeout_hours
    ):
        raise ValueError("external upper-bound reservation must be inside the campaign cap")
    if not re.fullmatch(r"[^,\s@]+@[^,\s@]+", args.email):
        raise ValueError("one valid PBS notification address required")
    if not args.external_evidence and args.external_hours:
        raise ValueError("external envelope needs a frozen job/budget manifest")
    candidate = args.candidate.resolve(strict=True)
    candidate_sha = runtime["source_commit"]
    if (
        not re.fullmatch(r"[0-9a-f]{40}", candidate_sha)
        or pbs("git", "-C", str(candidate), "rev-parse", "HEAD") != candidate_sha
        or pbs("git", "-C", str(candidate), "status", "--porcelain", "--untracked-files=no")
    ):
        raise ValueError("clean campaign candidate does not match the runtime receipt")
    pbs("git", "-C", str(candidate), "merge-base", "--is-ancestor", NUMERIC_BASE, candidate_sha)
    root.mkdir(parents=True)
    for name in ("tickets", "claims", "native", "logs"):
        (root / name).mkdir()
    return {
        "schema": "sprint2-fresh-budget-v1",
        "root": str(root),
        "cap_seconds": CAP_SECONDS,
        "earmarked_external_seconds": args.external_hours * 3600,
        "closeout_seconds": args.closeout_hours * 3600,
        "external_evidence": (
            {
                "path": str(args.external_evidence.resolve()),
                "sha256": digest(args.external_evidence),
            }
            if args.external_evidence
            else None
        ),
        "runtime_receipt": {
            "path": str(args.runtime_receipt.resolve()),
            "sha256": digest(args.runtime_receipt),
        },
        "source_commit": candidate_sha,
        "panel_freeze": None,
        "owner": getpass.getuser(),
        "email": args.email,
        "worker_sha256": digest(WORKER),
        "controller_sha256": digest(SCRIPT),
        "environment": {
            "LL_REPO": str(candidate),
            "LL_IMAGE": runtime["sif"],
            "LL_PYTHON": runtime["python_executable"],
            "LL_CONTROL": str(SCRIPT),
            "LL_BIND": ":".join(str(p.resolve()) for p in args.bind),
        },
        "results_root": str(args.results_root.resolve()),
        "jobs": {},
    }


def initialize(args: argparse.Namespace) -> None:
    ledger = initial_ledger(args)
    save(Path(ledger["root"]) / "budget.json", ledger)


def load_ledger(root: Path) -> Json:
    ledger = read(root / "budget.json")
    if (
        ledger["root"] != str(root)
        or ledger["schema"] != "sprint2-fresh-budget-v1"
        or ledger["cap_seconds"] != CAP_SECONDS
        or ledger["controller_sha256"] != digest(SCRIPT)
        or ledger["worker_sha256"] != digest(WORKER)
        or getpass.getuser() != ledger["owner"]
    ):
        raise ValueError("campaign ledger, controller, owner or cap mismatch")
    for ref in (ledger["panel_freeze"], ledger["external_evidence"], ledger["runtime_receipt"]):
        if ref and digest(Path(ref["path"])) != ref["sha256"]:
            raise ValueError(f"campaign control file changed: {ref['path']}")
    return ledger


def pbs(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def native_records(jobs: list[str]) -> dict[str, Json]:
    output = subprocess.run(["qstat", "-xf", "-F", "json", *jobs], capture_output=True, text=True)
    if not output.stdout.strip():
        return {}
    return json.loads(output.stdout)["Jobs"]


def native_identity(ledger: Json, record: Json, row: Json) -> None:
    requested = row["Resource_List"]
    if (
        row["Job_Name"] != record["name"]
        or row["Job_Owner"].split("@", 1)[0] != ledger["owner"]
        or str(row["Rerunable"]).lower() != "false"
        or int(requested["ncpus"]) != 1
        or seconds(requested["walltime"]) != record["requested_wall_seconds"]
    ):
        raise ValueError("PBS job has an unexpected owner, name, resources or rerun setting")


def native_charge(record: Json, row: Json) -> tuple[int, str]:
    ceiling = record["reserved_seconds"]
    if str(row.get("run_count", "")).isdigit() and int(row["run_count"]) > 1:
        return int(row["run_count"]) * ceiling, "anomalous execution exceeds contract"
    try:
        used = row["resources_used"]
        elapsed = seconds(used["walltime"])
        runs = int(row["run_count"])
        cores = int(used["ncpus"])
        if runs > 1 or cores > 1 or elapsed >= ceiling:
            return max(ceiling, cores * (elapsed + 1)), "anomalous execution exceeds contract"
        if runs == 1 and cores == 1 and "Exit_status" in row and elapsed > 0:
            return elapsed + 1, "native terminal single execution, rounded conservatively"
    except (KeyError, TypeError, ValueError):
        pass
    return ceiling, "full reservation retained: ambiguous or anomalous native accounting"


def release(ledger: Json, root: Path, record: Json, job: str) -> None:
    if ledger.get("accounting_fault"):
        raise ValueError("native accounting anomaly freezes job release")
    if not JOB_ID.fullmatch(job):
        raise ValueError("expected one non-array PBS identifier; leave the reservation held")
    row = native_records([job])[job]
    native_identity(ledger, record, row)
    if row["job_state"] != "H" or "u" not in row.get("Hold_Types", ""):
        raise ValueError("native job must still be held by its owner")
    record["job"], record["state"] = job, "held"
    save(root / "native" / f"{record['name']}-held.json", row)
    save(root / "budget.json", ledger)
    pbs("qrls", job)
    record["state"] = "released"
    save(root / "budget.json", ledger)


def reserve_and_submit(
    ledger: Json, ticket: Json, wall: int, memory: str, *, notify: bool, closeout: bool = False
) -> str:
    reserve = wall + PBS_MARGIN_SECONDS
    guard_budget(ledger, reserve, closeout=closeout)
    root = Path(ledger["root"])
    name = "llf" + uuid.uuid4().hex[:10]
    ticket = {**ticket, "name": name, "claim": str(root / "claims" / name)}
    ticket_path = root / "tickets" / f"{name}.json"
    save(ticket_path, ticket)
    env = {
        **ledger["environment"],
        "LL_TICKET": str(ticket_path),
        "LL_TICKET_SHA256": digest(ticket_path),
        "LL_CONTROL_SHA256": ledger["controller_sha256"],
        "LL_IMAGE_SHA256": SIF_SHA256,
    }
    if any(re.search(r"[,\n\r]", value) for value in env.values()):
        raise ValueError("PBS variable values cannot include commas or newlines")
    command = [
        "qsub",
        "-h",
        "-r",
        "n",
        "-N",
        name,
        "-l",
        f"select=1:ncpus=1:mem={memory}",
        "-l",
        f"walltime={walltime(wall)}",
        "-m",
        "ae" if notify else "a",
        "-M",
        ledger["email"],
        "-o",
        str(root / "logs" / f"{name}.log"),
        "-v",
        ",".join(f"{k}={v}" for k, v in env.items()),
        str(WORKER),
    ]
    record = {
        "name": name,
        "key": ticket["key"],
        "identity": ticket["identity"],
        "state": "pending_submit",
        "requested_wall_seconds": wall,
        "reserved_seconds": reserve,
        "closeout": closeout,
        "command": command,
    }
    ledger["jobs"][name] = record
    save(root / "budget.json", ledger)
    job = pbs(*command)
    record["returned_job"] = job
    save(root / "budget.json", ledger)
    release(ledger, root, record, job)
    return job


def reconcile(ledger: Json) -> None:
    root = Path(ledger["root"])
    by_job = {
        record["job"]: record
        for record in ledger["jobs"].values()
        if record["state"] in ("held", "released")
    }
    jobs = list(by_job)
    for start in range(0, len(jobs), 100):
        for job, row in native_records(jobs[start : start + 100]).items():
            record = by_job[job]
            native_identity(ledger, record, row)
            if row["job_state"] != "F":
                if record["state"] == "held" and row["job_state"] != "H":
                    record["state"] = "released"
                continue
            charge, reason = native_charge(record, row)
            if reason == "anomalous execution exceeds contract":
                ledger["accounting_fault"] = True
            save(root / "native" / f"{record['name']}-terminal.json", row)
            record.update(state="terminal", accounted_seconds=charge, charge_reason=reason)
        save(root / "budget.json", ledger)


def task_finished(task: Json, root: Path) -> bool:
    top = root / task["task_id"] / "_task.json"
    try:
        record = read(top)
    except FileNotFoundError:
        return False
    if record["task_sha256"] != task_digest(task):
        raise ValueError(f"result exists from a different task: {task['task_id']}")
    return record["status"] in TERMINAL


def launch_tasks(ledger: Json, path: Path, limit: int) -> list[str]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if len({t["task_id"] for t in rows}) != len(rows) or len({task_digest(t) for t in rows}) != len(
        rows
    ):
        raise ValueError("phase contains duplicate task identifiers or task digests")
    plan = read(path.parent / "plan.json")
    freeze = ledger["panel_freeze"]
    if (
        freeze is None
        or rows != plan["tasks"]
        or plan["source_commit"] != ledger["source_commit"]
        or plan["panel_sha256"] != read(Path(freeze["path"]))["panel"]["sha256"]
    ):
        raise ValueError("task rows and fresh registered phase plan differ")
    attempts: dict[str, list[Json]] = {}
    for row in ledger["jobs"].values():
        attempts.setdefault(row["key"], []).append(row)
    waiting = []
    results = Path(ledger["results_root"])
    for task in rows:
        key, identity = task["task_id"], task_digest(task)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", key):
            raise ValueError("invalid ledger task identifier")
        if (
            task["source_commit"] != ledger["source_commit"]
            or task["input_sha256"].get(freeze["path"]) != freeze["sha256"]
        ):
            raise ValueError("task does not bind the accepted source and fresh freeze")
        prior = attempts.get(key, [])
        if any(r["identity"] != identity for r in prior):
            raise ValueError(f"task changed after admission: {key}")
        if (
            len(prior) >= 3
            or any(r["state"] != "terminal" for r in prior)
            or task_finished(task, results)
        ):
            continue
        waiting.append((len(prior), task))
    jobs = []
    for _, task in sorted(waiting, key=lambda item: item[0]):
        if len(jobs) == limit:
            break
        wall, memory = SCHEMAS[task["result_schema"]]
        if charged(ledger) + wall + PBS_MARGIN_SECONDS > CAP_SECONDS:
            continue
        if task["result_schema"] == "fit-dataset-v1" and task.get("max_segments") != 3:
            raise ValueError("fresh fits require the frozen three-attempt limit")
        ticket = {
            "kind": "task",
            "key": task["task_id"],
            "identity": task_digest(task),
            "task": task,
            "results_root": ledger["results_root"],
        }
        jobs.append(reserve_and_submit(ledger, ticket, wall, memory, notify=False))
    return jobs


def launch_aux(ledger: Json, args: argparse.Namespace) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", args.label):
        raise ValueError("invalid one-shot auxiliary label")
    if any(r["key"] == f"aux:{args.label}" for r in ledger["jobs"].values()):
        raise ValueError("label already reserved; use a distinct label for another allocation")
    if not 1 <= args.wall_minutes <= 48 * 60 or not re.fullmatch(r"[1-9]\d*gb", args.memory):
        raise ValueError("auxiliary allocation must be one core for at most 48 hours")
    script = args.script.resolve(strict=True)
    ticket = {
        "kind": "aux",
        "key": f"aux:{args.label}",
        "script": str(script),
        "identity": digest(script),
        "interpreter": "python" if args.python else "bash",
        "parameters": args.parameters,
    }
    return reserve_and_submit(
        ledger,
        ticket,
        args.wall_minutes * 60,
        args.memory,
        notify=args.notify,
        closeout=args.closeout,
    )


def summary(ledger: Json) -> Json:
    jobs = ledger["jobs"].values()
    return {
        "cap_core_seconds": CAP_SECONDS,
        "committed_core_seconds": charged(ledger),
        "remaining_core_seconds": CAP_SECONDS - charged(ledger),
        "earmarked_external_core_seconds": ledger["earmarked_external_seconds"],
        "closeout_envelope_core_seconds": ledger["closeout_seconds"],
        "closeout_committed_core_seconds": committed(ledger, closeout=True),
        "accounting_fault": ledger.get("accounting_fault", False),
        "panel_bound": ledger["panel_freeze"] is not None,
        "settled_core_seconds": sum(row.get("accounted_seconds", 0) for row in jobs),
        "outstanding_reserved_core_seconds": sum(
            row["reserved_seconds"] for row in jobs if "accounted_seconds" not in row
        ),
        "jobs_by_state": dict(Counter(row["state"] for row in jobs)),
    }


def run_ticket(path: Path, wanted_hash: str, candidate: Path) -> int:
    if digest(path) != wanted_hash:
        raise ValueError("compute ticket hash mismatch")
    ticket = read(path)
    root = path.parent.parent
    record = read(root / "budget.json")["jobs"][ticket["name"]]
    job = os.environ["PBS_JOBID"]
    if record["state"] not in ("held", "released") or record["job"] != job:
        raise ValueError("worker requires the recorded native job for this reservation")
    with Path(ticket["claim"]).open("x") as claim:
        claim.write(job + "\n")
        claim.flush()
        os.fsync(claim.fileno())
    if ticket["kind"] == "aux":
        script = Path(ticket["script"])
        if digest(script) != ticket["identity"]:
            raise ValueError("auxiliary script drift")
        interpreter = sys.executable if ticket["interpreter"] == "python" else "/bin/bash"
        return subprocess.run([interpreter, str(script), *ticket["parameters"]]).returncode
    task = ticket["task"]
    if task_digest(task) != ticket["identity"]:
        raise ValueError("task identity mismatch")
    sys.path.insert(0, str(candidate.resolve() / "scripts"))
    from pbs import campaign

    if candidate.resolve() != campaign.ROOT:
        raise ValueError("campaign runner loaded from outside the candidate checkout")
    registered_outcome = campaign.outcome

    def status(task: Json, attempt: Path, code: int) -> tuple[str, str | None]:
        observed = registered_outcome(task, attempt, code)
        if observed[0] == "completed" and task["result_schema"] in (
            "sprint2-common-anchors-v1",
            "sprint2-free-gradient-v1",
        ):
            receipt = read(attempt / task["result_path"])
            if receipt["status"] == "execution_error":
                return "execution_failure", "execution_error"
        return observed

    campaign.outcome = status
    record = campaign.run_task(task, Path(ticket["results_root"]), retry_failed=True)
    print(json.dumps({key: record[key] for key in ("task_id", "status", "failure_class")}))
    return int(record["status"] not in TERMINAL)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    for name in ("candidate", "runtime-receipt", "results-root"):
        init.add_argument(f"--{name}", type=Path, required=True)
    init.add_argument("--email", required=True)
    init.add_argument("--bind", type=Path, action="append", default=[])
    init.add_argument("--external-hours", type=int, default=0)
    init.add_argument("--external-evidence", type=Path)
    init.add_argument("--closeout-hours", type=int, default=12)
    bind = commands.add_parser("bind-panel")
    bind.add_argument("--freeze", type=Path, required=True)
    submit = commands.add_parser("submit")
    submit.add_argument("--tasks", type=Path, required=True)
    submit.add_argument("--max-jobs", type=int, required=True)
    aux = commands.add_parser("submit-aux")
    aux.add_argument("--label", required=True)
    aux.add_argument("--script", type=Path, required=True)
    aux.add_argument("--wall-minutes", type=int, required=True)
    aux.add_argument("--memory", required=True)
    aux.add_argument("--notify", action="store_true")
    aux.add_argument("--closeout", action="store_true")
    aux.add_argument("--python", action="store_true")
    aux.add_argument("parameters", nargs=argparse.REMAINDER)
    commands.add_parser("status")
    commands.add_parser("reconcile")
    recover = commands.add_parser("recover-held")
    recover.add_argument("--name", required=True)
    recover.add_argument("--job", required=True)
    worker = commands.add_parser("worker")
    worker.add_argument("--ticket", type=Path, required=True)
    worker.add_argument("--sha256", required=True)
    worker.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "worker":
        return run_ticket(args.ticket, args.sha256, args.candidate)
    if args.ledger is None:
        parser.error("--ledger is required")
    if args.command == "init":
        initialize(args)
        return 0
    root = args.ledger.resolve(strict=True)
    with locked(root):
        ledger = load_ledger(root)
        report = {}
        if args.command in ("submit", "submit-aux", "reconcile", "recover-held"):
            reconcile(ledger)
        if args.command == "bind-panel":
            if ledger["panel_freeze"] is not None:
                raise ValueError("a qualification panel is already bound to this ledger")
            ledger["panel_freeze"] = panel_reference(
                args.freeze, ledger["runtime_receipt"]["sha256"], ledger["source_commit"]
            )
            save(root / "budget.json", ledger)
        if args.command == "recover-held":
            record = ledger["jobs"][args.name]
            if record["state"] not in ("pending_submit", "held"):
                raise ValueError("reservation is no longer recoverable as a held job")
            if record.get("returned_job", args.job) != args.job:
                raise ValueError("supplied job differs from the reserved job")
            release(ledger, root, record, args.job)
        if args.command == "submit":
            if args.max_jobs < 1:
                parser.error("--max-jobs must be positive")
            report["submitted"] = launch_tasks(ledger, args.tasks, args.max_jobs)
        if args.command == "submit-aux":
            if args.parameters[:1] == ["--"]:
                args.parameters = args.parameters[1:]
            report["submitted"] = [launch_aux(ledger, args)]
        print(json.dumps({**report, **summary(ledger)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
