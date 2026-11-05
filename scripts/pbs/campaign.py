"""Packed task driver for PBS array campaigns.

A campaign is a JSONL task list; each line is {"task_id": str, "argv": [...]}
run from the repository root. Array subjob k runs tasks k*chunk .. k*chunk+chunk-1
on a local process pool with one numerical thread per task. Every attempt
writes <out>/<task_id>/_task.json; a task whose receipt records exit 0 is
skipped on resume. Failed tasks are never deleted or silently retried:
--retry-failed reruns them and keeps the earlier receipt as _task.<n>.json.
Scheduler exits and task receipts are reconciled separately.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import platform
import resource
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THREADS = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")


def load_tasks(path: Path) -> list[dict]:
    tasks = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    ids = [t["task_id"] for t in tasks]
    if len(set(ids)) != len(ids):
        raise ValueError("task identifiers must be unique")
    return tasks


def source_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return os.environ.get("LL_SOURCE_COMMIT", "unknown")


def run_task(task: dict, out: Path, retry_failed: bool) -> dict:
    directory = out / task["task_id"]
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / "_task.json"
    if receipt.exists():
        previous = json.loads(receipt.read_text())
        if previous["exit_code"] == 0:
            return {"task_id": task["task_id"], "skipped": True, "exit_code": 0}
        if not retry_failed:
            return {"task_id": task["task_id"], "skipped": True, "exit_code": previous["exit_code"]}
        attempt = len(list(directory.glob("_task.*.json"))) + 1
        receipt.rename(directory / f"_task.{attempt}.json")
    env = {**os.environ, **dict.fromkeys(THREADS, "1"), "LL_TASK_DIR": str(directory)}
    started, wall = time.time(), time.perf_counter()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with (
        (directory / "_stdout.log").open("w") as stdout,
        (directory / "_stderr.log").open("w") as stderr,
    ):
        code = subprocess.run(
            task["argv"], cwd=ROOT, env=env, stdout=stdout, stderr=stderr
        ).returncode
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    record = {
        "task_id": task["task_id"],
        "argv": task["argv"],
        "exit_code": code,
        "started_unix": started,
        "wall_seconds": time.perf_counter() - wall,
        "cpu_seconds": (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime),
        "max_rss_children_kb": after.ru_maxrss,
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version,
        "source_commit": source_commit(),
        "pbs_job_id": os.environ.get("PBS_JOBID"),
        "pbs_array_index": os.environ.get("PBS_ARRAY_INDEX"),
    }
    receipt.write_text(json.dumps(record, indent=1) + "\n")
    return record


def work(args: argparse.Namespace) -> None:
    tasks = load_tasks(args.tasks)
    index = int(os.environ.get("PBS_ARRAY_INDEX", args.index))
    chunk = tasks[index * args.chunk : (index + 1) * args.chunk]
    workers = args.workers or int(os.environ.get("NCPUS", "1"))
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(
            pool.map(run_task, chunk, [args.out] * len(chunk), [args.retry_failed] * len(chunk))
        )
    failed = [r["task_id"] for r in results if r["exit_code"] != 0]
    print(json.dumps({"array_index": index, "tasks": len(chunk), "failed": failed}))


def reconcile(args: argparse.Namespace) -> None:
    tasks = load_tasks(args.tasks)
    summary = {"completed": [], "failed": [], "missing": []}
    for task in tasks:
        receipt = args.out / task["task_id"] / "_task.json"
        if not receipt.exists():
            summary["missing"].append(task["task_id"])
            continue
        record = json.loads(receipt.read_text())
        summary["completed" if record["exit_code"] == 0 else "failed"].append(task["task_id"])
    counts = {key: len(value) for key, value in summary.items()}
    arrays = -(-len(tasks) // args.chunk)
    print(json.dumps({"tasks": len(tasks), "array_indices": arrays, **counts}, indent=1))
    (args.out / "_reconcile.json").write_text(json.dumps(summary, indent=1) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("work", "reconcile"):
        p = sub.add_parser(name)
        p.add_argument("--tasks", type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--chunk", type=int, required=True)
        if name == "work":
            p.add_argument("--index", type=int, default=0)
            p.add_argument("--workers", type=int, default=0)
            p.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    {"work": work, "reconcile": reconcile}[args.command](args)


if __name__ == "__main__":
    main()
