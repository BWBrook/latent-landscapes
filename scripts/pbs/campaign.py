"""Run immutable tasks in preserved attempt directories and reconcile their evidence.

Tasks specify task_id, argv, source_commit, input_sha256, result_path and
result_schema plus the expected runtime. The literal {attempt_dir} in argv is
replaced by the new attempt directory. Execution failures may be retried;
scientific failures are terminal.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import re
import resource
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THREADS = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
SCIENTIFIC_FAILURES = {
    "numerical_error",
    "family_fit_failed",
    "search_unresolved",
    "multimodal_latent",
}
TERMINAL = {"resolved", "scientific_failure", "completed"}


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def task_digest(task: dict) -> str:
    return hashlib.sha256(
        json.dumps(task, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def load_tasks(path: Path) -> list[dict]:
    tasks = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    for task in tasks:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", task["task_id"]):
            raise ValueError("task_id must be a single safe path component")
        if not task["argv"] or not all(isinstance(a, str) for a in task["argv"]):
            raise ValueError("argv must be a nonempty string list")
        if not any("{attempt_dir}" in a for a in task["argv"]):
            raise ValueError("argv must direct output to {attempt_dir}")
        if not re.fullmatch(r"[0-9a-f]{40}", task["source_commit"]):
            raise ValueError("source_commit must be a full Git commit")
        if not isinstance(task["input_sha256"], dict) or not task["input_sha256"]:
            raise ValueError("input_sha256 must bind task inputs and the runtime")
        if any(not re.fullmatch(r"[0-9a-f]{64}", v) for v in task["input_sha256"].values()):
            raise ValueError("invalid input digest")
        result = Path(task["result_path"])
        if result.is_absolute() or ".." in result.parts or not result.parts:
            raise ValueError("result_path must be inside the attempt directory")
        if not isinstance(task["result_schema"], str) or not task["result_schema"]:
            raise ValueError("result_schema must be specified")
        runtime = task["runtime"]
        if runtime["context"] != "apptainer" or not Path(runtime["python"]).is_absolute():
            raise ValueError("runtime must specify Apptainer and an absolute Python path")
        if task["input_sha256"].get(runtime["sif"]) != runtime["sif_sha256"]:
            raise ValueError("runtime SIF must be an explicitly hashed task input")
    if len({t["task_id"] for t in tasks}) != len(tasks):
        raise ValueError("task identifiers must be unique")
    return tasks


def source_identity() -> dict:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return {"commit": commit, "tracked_changes": dirty}


def verify_inputs(task: dict) -> None:
    for name, expected in task["input_sha256"].items():
        path = Path(name)
        if sha256(path if path.is_absolute() else ROOT / path) != expected:
            raise ValueError(f"input/runtime drift: {name}")


def verify_source(task: dict) -> dict:
    identity = source_identity()
    if identity["commit"] != task["source_commit"] or identity["tracked_changes"]:
        raise ValueError("source checkout differs from the frozen clean commit")
    return identity


def verify_runtime(task: dict) -> None:
    runtime = task["runtime"]
    if (
        os.environ.get("LL_EXECUTION_CONTEXT") != runtime["context"]
        or os.environ.get("LL_RUNTIME_SIF_SHA256") != runtime["sif_sha256"]
        or sys.executable != runtime["python"]
    ):
        raise ValueError("running interpreter/container differs from the frozen runtime")


def outcome(task: dict, directory: Path, code: int) -> tuple[str, str | None]:
    if code != 0:
        return "execution_failure", None
    result = json.loads((directory / task["result_path"]).read_text())
    if result.get("schema") != task["result_schema"]:
        raise ValueError("result schema differs from task contract")
    if task["result_schema"] != "fit-dataset-v1":
        return "completed", None
    failure = result.get("failure_class")
    if failure == "resolved":
        return "resolved", failure
    if failure == "execution_error":
        return "execution_failure", failure
    if failure in SCIENTIFIC_FAILURES:
        return "scientific_failure", failure
    raise ValueError(f"unknown fit failure class: {failure!r}")


def verify_record(task: dict, directory: Path, record: dict) -> None:
    if record["task_sha256"] != task_digest(task):
        raise ValueError(f"task identity changed: {task['task_id']}")
    verify_inputs(task)
    attempt = directory / record["attempt"]
    for name, expected in record["output_sha256"].items():
        if sha256(attempt / name) != expected:
            raise ValueError(f"saved output changed: {task['task_id']}/{name}")
    if record["status"] in TERMINAL:
        status, failure = outcome(task, attempt, record["exit_code"])
        if (status, failure) != (record["status"], record["failure_class"]):
            raise ValueError("result disagrees with task receipt")


def run_task(task: dict, out: Path, retry_failed: bool) -> dict:
    directory = (out / task["task_id"]).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / "_task.json"
    if receipt.exists():
        previous = json.loads(receipt.read_text())
        verify_record(task, directory, previous)
        if previous["status"] in TERMINAL or not retry_failed:
            return {**previous, "skipped": True}
    attempts = sorted(directory.glob("attempt-[0-9]*"))
    for existing in attempts:
        started_record = json.loads((existing / "_started.json").read_text())
        if started_record["task_sha256"] != task_digest(task):
            raise ValueError(f"unfinished task identity changed: {task['task_id']}")
    if attempts and not retry_failed and not receipt.exists():
        raise ValueError(f"unfinished attempt requires --retry-failed: {task['task_id']}")
    attempt_number = max((int(p.name.split("-")[1]) for p in attempts), default=0) + 1
    attempt = directory / f"attempt-{attempt_number:04d}"
    attempt.mkdir()
    (attempt / "_started.json").write_text(
        json.dumps({"task_sha256": task_digest(task), "task": task}, indent=1) + "\n"
    )
    argv = [value.replace("{attempt_dir}", str(attempt)) for value in task["argv"]]
    env = {**os.environ, **dict.fromkeys(THREADS, "1"), "LL_TASK_DIR": str(attempt)}
    started, wall = time.time(), time.perf_counter()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    code, status, failure, error, identity = None, "execution_failure", None, None, None
    try:
        identity = verify_source(task)
        verify_runtime(task)
        verify_inputs(task)
        with (
            (attempt / "_stdout.log").open("w") as stdout,
            (attempt / "_stderr.log").open("w") as stderr,
        ):
            code = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr).returncode
        verify_source(task)
        verify_inputs(task)
        status, failure = outcome(task, attempt, code)
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    outputs = {
        str(p.relative_to(attempt)): sha256(p) for p in sorted(attempt.rglob("*")) if p.is_file()
    }
    record = {
        "task_id": task["task_id"],
        "task_sha256": task_digest(task),
        "task": task,
        "attempt": attempt.name,
        "argv": argv,
        "status": status,
        "failure_class": failure,
        "exit_code": code,
        "error": error,
        "started_unix": started,
        "wall_seconds": time.perf_counter() - wall,
        "cpu_seconds": (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime),
        "worker_children_peak_rss_bytes": after.ru_maxrss
        * (1 if sys.platform == "darwin" else 1024),
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version,
        "source": identity,
        "output_sha256": outputs,
        "pbs_job_id": os.environ.get("PBS_JOBID"),
        "pbs_array_index": os.environ.get("PBS_ARRAY_INDEX"),
    }
    encoded = json.dumps(record, indent=1) + "\n"
    (attempt / "_task.json").write_text(encoded)
    temporary = directory / "_task.json.tmp"
    temporary.write_text(encoded)
    temporary.replace(receipt)
    return record


def work(args: argparse.Namespace) -> int:
    tasks = load_tasks(args.tasks)
    index = int(os.environ.get("PBS_ARRAY_INDEX", args.index))
    if args.chunk < 1 or index < 0 or index * args.chunk >= len(tasks):
        raise ValueError("invalid or empty array slice")
    chunk = tasks[index * args.chunk : (index + 1) * args.chunk]
    workers = args.workers
    if workers < 1:
        raise ValueError("workers must be explicitly positive")
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(
            pool.map(run_task, chunk, [args.out] * len(chunk), [args.retry_failed] * len(chunk))
        )
    failed = [r["task_id"] for r in results if r["status"] == "execution_failure"]
    print(json.dumps({"array_index": index, "tasks": len(chunk), "execution_failed": failed}))
    return int(bool(failed))


def reconcile(args: argparse.Namespace) -> int:
    tasks = load_tasks(args.tasks)
    summary = {
        key: []
        for key in (
            "resolved",
            "scientific_failure",
            "completed",
            "execution_failure",
            "missing",
            "invalid",
        )
    }
    errors = {}
    for task in tasks:
        directory = args.out / task["task_id"]
        receipt = directory / "_task.json"
        if not receipt.exists():
            summary["missing"].append(task["task_id"])
            continue
        try:
            record = json.loads(receipt.read_text())
            verify_record(task, directory, record)
            summary[record["status"]].append(task["task_id"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            summary["invalid"].append(task["task_id"])
            errors[task["task_id"]] = str(exc)
    counts = {key: len(value) for key, value in summary.items()}
    print(json.dumps({"tasks": len(tasks), **counts}, indent=1))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "_reconcile.json").write_text(
        json.dumps({**summary, "errors": errors}, indent=1) + "\n"
    )
    return int(any(summary[k] for k in ("execution_failure", "missing", "invalid")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("work", "reconcile"):
        p = sub.add_parser(name)
        p.add_argument("--tasks", type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
        if name == "work":
            p.add_argument("--chunk", type=int, required=True)
            p.add_argument("--index", type=int, default=0)
            p.add_argument("--workers", type=int, required=True)
            p.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    return {"work": work, "reconcile": reconcile}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
