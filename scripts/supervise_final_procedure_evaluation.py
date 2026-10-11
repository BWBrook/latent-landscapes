#!/usr/bin/env python3
"""Bound a Goal 062 process group by RSS and an immutable wall deadline."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path: Path, data: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def group_status(group: int) -> tuple[int, list[int]]:
    pages, members = 0, []
    for entry in Path("/proc").glob("[0-9]*/stat"):
        try:
            raw = entry.read_text()
            fields = raw[raw.rfind(")") + 2 :].split()
            if int(fields[2]) == group and fields[0] != "Z":
                pages += int(fields[21])
                members.append(int(entry.parent.name))
        except (OSError, ValueError, IndexError):
            continue
    return pages * os.sysconf("SC_PAGE_SIZE"), members


def stop_group(group: int) -> None:
    with suppress(ProcessLookupError):
        os.killpg(group, signal.SIGTERM)
    deadline = time.monotonic() + 10
    while group_status(group)[1] and time.monotonic() < deadline:
        time.sleep(0.2)
    if group_status(group)[1]:
        with suppress(ProcessLookupError):
            os.killpg(group, signal.SIGKILL)


def verify_source(root: Path) -> tuple[dict[str, Any], str]:
    path = root / "source-manifest.json"
    manifest = json.loads(path.read_text())
    for relative, expected in manifest["source_hashes"].items():
        if sha256(root / "source" / relative) != expected:
            raise ValueError("frozen source changed: " + relative)
    for relative, expected in manifest["input_hashes"].items():
        if sha256(root / relative) != expected:
            raise ValueError("frozen input changed: " + relative)
    return manifest, sha256(path)


def run(root: Path, phase: str, attempt: str, workers: int) -> int:
    root = root.resolve()
    with (root / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest, binding = verify_source(root)
        if not 1 <= workers <= min(51, manifest["maximum_workers"]):
            raise ValueError("worker count exceeds approved envelope")
        if not attempt.isdigit() or len(attempt) != 3:
            raise ValueError("attempt must be three digits")
        now = datetime.now(UTC)
        if phase == "run":
            benchmark = json.loads((root / "benchmark/qualification.json").read_text())
            if benchmark.get("passed") is not True or benchmark.get("binding_sha256") != binding:
                raise ValueError("unchanged successful qualification is required")
            if workers > int(benchmark["qualified_workers"]):
                raise ValueError("requested workers exceed measured qualification")
            if benchmark.get("runtime_changed"):
                approval = json.loads((root / "production-runtime-approval.json").read_text())
                if (
                    approval.get("approved") is not True
                    or approval.get("binding_sha256") != binding
                    or approval.get("runtime_sha256") != benchmark["runtime_sha256"]
                    or approval.get("qualification_sha256")
                    != sha256(root / "benchmark/qualification.json")
                ):
                    raise ValueError(
                        "explicit approval of the qualified runtime change is required"
                    )
            deadline_path = root / "production-deadline.json"
            if deadline_path.exists():
                saved = json.loads(deadline_path.read_text())
                if saved.get("binding_sha256") != binding:
                    raise ValueError("production deadline binding changed")
                deadline = datetime.fromisoformat(saved["deadline_utc"])
            else:
                budget = min(72 * 3600, int(manifest["production_wall_seconds"]))
                deadline = now + timedelta(seconds=budget)
                with deadline_path.open("x") as handle:
                    json.dump(
                        {
                            "binding_sha256": binding,
                            "started_utc": now.isoformat(),
                            "deadline_utc": deadline.isoformat(),
                            "wall_seconds": budget,
                        },
                        handle,
                    )
        else:
            deadline = now + timedelta(
                seconds=min(3 * 3600, int(manifest["qualification_wall_seconds"]))
            )
        remaining = (deadline - now).total_seconds()
        if remaining <= 0:
            raise ValueError("campaign wall deadline exhausted; unfinished work remains pending")
        receipt_path = root / f"{phase}-attempt-{attempt}.json"
        with receipt_path.open("x") as handle:
            json.dump({"state": "starting", "phase": phase}, handle)
        environment = dict(os.environ)
        environment["GOAL062_SUPERVISOR_PID"] = str(os.getpid())
        if shutil.disk_usage(root).free < manifest["minimum_scratch_bytes"]:
            raise ValueError("less than the approved scratch allowance is free")
        for name in (
            "OPENBLAS_NUM_THREADS",
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
        ):
            environment[name] = "1"
        environment.update(
            PYTHONUNBUFFERED="1",
            MPLBACKEND="Agg",
            PYTHONPATH=os.pathsep.join((str(root / "source/src"), str(root / "source/scripts"))),
        )
        command = [
            sys.executable,
            str(root / "source/scripts/run_final_procedure_evaluation.py"),
            phase,
            "--root",
            str(root),
            "--workers",
            str(workers),
        ]
        with (root / f"{phase}-{attempt}.log").open("x") as log:
            started = time.monotonic()
            process = subprocess.Popen(
                command,
                cwd=root / "source",
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            receipt: dict[str, Any] = {
                "state": "running",
                "phase": phase,
                "attempt": attempt,
                "pid": process.pid,
                "created_utc": now.isoformat(),
                "deadline_utc": deadline.isoformat(),
                "binding_sha256": binding,
                "rss_cap_bytes": 64 * 1024**3,
                "workers": workers,
                "peak_group_rss_bytes": 0,
                "stop_reason": None,
                "command": command,
            }
            write(receipt_path, receipt)
            try:
                while process.poll() is None:
                    rss, _ = group_status(process.pid)
                    receipt["peak_group_rss_bytes"] = max(receipt["peak_group_rss_bytes"], rss)
                    if datetime.now(UTC) >= deadline or rss > 64 * 1024**3:
                        receipt["stop_reason"] = (
                            "wall_budget" if datetime.now(UTC) >= deadline else "rss_budget"
                        )
                        stop_group(process.pid)
                        break
                    time.sleep(1)
                code = process.wait()
                if group_status(process.pid)[1]:
                    stop_group(process.pid)
                    receipt["stop_reason"] = receipt["stop_reason"] or "orphaned_workers"
                    code = code or 1
            except BaseException:
                stop_group(process.pid)
                raise
            receipt.update(
                state="finished",
                exit_code=code,
                finished_utc=datetime.now(UTC).isoformat(),
                elapsed_seconds=time.monotonic() - started,
                remaining_group_members=group_status(process.pid)[1],
                pending_due_to_resource_stop=receipt["stop_reason"]
                in {"wall_budget", "rss_budget"},
            )
            write(receipt_path, receipt)
            print(json.dumps(receipt), flush=True)
            return code if receipt["stop_reason"] is None else (code or 124)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("benchmark", "run"))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--attempt", default="001")
    parser.add_argument("--workers", default=51, type=int)
    args = parser.parse_args()
    raise SystemExit(run(args.root, args.phase, args.attempt, args.workers))


if __name__ == "__main__":
    main()
