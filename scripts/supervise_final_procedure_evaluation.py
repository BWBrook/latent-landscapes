#!/usr/bin/env python3
"""Bound a Goal 062 process group by RSS and an immutable wall deadline."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

CARRY_SCHEMA = "goal062-carry-forward-v1"
MAX_WALL_SECONDS = 72 * 3600
REPAIR_ALLOWLIST = tuple(
    sorted(
        {
            "scripts/audit_final_procedure_evaluation.py",
            "scripts/freeze_final_procedure_evaluation.py",
            "scripts/run_final_procedure_evaluation.py",
            "scripts/supervise_final_procedure_evaluation.py",
            "tests/test_final_procedure_evaluation_audit.py",
            "tests/test_final_procedure_evaluation_qualification.py",
            "tests/test_final_procedure_evaluation_runner.py",
        }
    )
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CARRY_HISTORY_FILES = {
    "observations.npz",
    "evaluator.npz",
    "evaluator.json",
    "inputs-complete.json",
    "inputs-audit.json",
    "main.json",
    "main-audit.json",
    "pre.npz",
    "main-complete.json",
    "decision.json",
}
_CARRY_PRODUCTION_FILES = {
    "production/seed-ledger.json",
    "production/bootstrap-seed-ledger.json",
}
_CARRY_KEYS = {
    "schema",
    "predecessor_binding_sha256",
    "predecessor_root",
    "predecessor_deadline",
    "files",
    "allowed_source_changes",
}


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


def _sha256_value(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{label} is not a lowercase SHA-256 digest")
    return value


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{label} is not an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{label} is not an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{label} is missing a timezone")
    return parsed.astimezone(UTC)


def _safe_carry_file(relative: Any) -> str:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("carry-forward file path is unsafe")
    path = Path(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("carry-forward file path is unsafe")
    parts = path.parts
    name = path.name
    if re.fullmatch(r"references/effect/node-[0-9]{4}(?:\.sqlite|-complete\.json)", relative):
        return relative
    if re.fullmatch(r"references/audits/node-[0-9]{4}\.json", relative):
        return relative
    if relative in {"reference-cache.npz", "reference-cache.json"}:
        return relative
    if relative in _CARRY_PRODUCTION_FILES:
        return relative
    if (
        len(parts) == 5
        and parts[:2] == ("production", "evaluation")
        and re.fullmatch(r"cell-[0-9]{2}", parts[2])
        and re.fullmatch(r"rep-[0-9]{3}", parts[3])
        and name in _CARRY_HISTORY_FILES
    ):
        return relative
    raise ValueError("carry-forward file path is outside the permitted artifact classes")


def _validate_deadline_record(
    record: Any, binding: str, label: str
) -> tuple[datetime, datetime, int]:
    if not isinstance(record, dict):
        raise ValueError(f"{label} is not a mapping")
    required = {"binding_sha256", "started_utc", "deadline_utc", "wall_seconds"}
    if set(record) != required or record.get("binding_sha256") != binding:
        raise ValueError(f"{label} binding changed")
    started = _timestamp(record["started_utc"], f"{label} started_utc")
    deadline = _timestamp(record["deadline_utc"], f"{label} deadline_utc")
    wall_seconds = record["wall_seconds"]
    if isinstance(wall_seconds, bool) or not isinstance(wall_seconds, int):
        raise ValueError(f"{label} wall_seconds is invalid")
    if not 0 < wall_seconds <= MAX_WALL_SECONDS:
        raise ValueError(f"{label} wall_seconds exceeds the approved limit")
    if deadline <= started or (deadline - started).total_seconds() != wall_seconds:
        raise ValueError(f"{label} times do not match wall_seconds")
    return started, deadline, wall_seconds


def _validate_source_changes(
    predecessor: dict[str, Any], manifest: dict[str, Any], allowed: list[str]
) -> None:
    old = predecessor.get("source_hashes")
    new = manifest.get("source_hashes")
    if not isinstance(old, dict) or not isinstance(new, dict) or set(old) != set(new):
        raise ValueError("predecessor and new source file sets differ")
    for name, value in old.items():
        _sha256_value(value, f"predecessor source hash {name}")
    for name, value in new.items():
        _sha256_value(value, f"new source hash {name}")
    if any(not isinstance(name, str) for name in allowed):
        raise ValueError("allowed source changes are not an exact sorted list")
    if allowed != sorted(set(allowed)):
        raise ValueError("allowed source changes are not an exact sorted list")
    changed = sorted(name for name in old if old[name] != new[name])
    if changed != allowed:
        raise ValueError("source changes do not match allowed_source_changes")
    if any(name not in REPAIR_ALLOWLIST for name in changed):
        raise ValueError("source change is outside the explicit repair allowlist")


def load_carry_forward(root: Path, manifest: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Validate and return a source-bound carry record, if one is pinned."""
    root = root.resolve()
    if manifest is None:
        manifest = json.loads((root / "source-manifest.json").read_text())
    input_hashes = manifest.get("input_hashes")
    if not isinstance(input_hashes, dict):
        raise ValueError("source manifest input hashes are malformed")
    carry_path = root / "carry-forward.json"
    pinned = input_hashes.get("carry-forward.json")
    if not carry_path.exists():
        if pinned is not None:
            raise ValueError("carry-forward input is pinned but missing")
        return None
    if pinned is None or sha256(carry_path) != pinned:
        raise ValueError("carry-forward file is not hash-bound by the source manifest")
    predecessor_path = root / "predecessor-source-manifest.json"
    predecessor_pinned = input_hashes.get("predecessor-source-manifest.json")
    if (
        predecessor_pinned is None
        or not predecessor_path.exists()
        or sha256(predecessor_path) != predecessor_pinned
    ):
        raise ValueError("predecessor source manifest is not hash-bound")
    carry = json.loads(carry_path.read_text())
    if (
        not isinstance(carry, dict)
        or set(carry) != _CARRY_KEYS
        or carry.get("schema") != CARRY_SCHEMA
    ):
        raise ValueError("carry-forward schema changed")
    predecessor_manifest = json.loads(predecessor_path.read_text())
    predecessor_binding = _sha256_value(
        carry.get("predecessor_binding_sha256"), "predecessor_binding_sha256"
    )
    if predecessor_binding != sha256(predecessor_path):
        raise ValueError("predecessor binding does not match frozen predecessor manifest")
    predecessor_root = carry.get("predecessor_root")
    if not isinstance(predecessor_root, str) or not predecessor_root:
        raise ValueError("predecessor root is invalid")
    if Path(predecessor_root).expanduser().resolve() == root:
        raise ValueError("predecessor root must differ from the new root")
    remote_root = manifest.get("remote_root")
    if remote_root is not None:
        if not isinstance(remote_root, str) or not remote_root:
            raise ValueError("remote root is invalid")
        predecessor_path = Path(predecessor_root).expanduser().resolve()
        if predecessor_path == Path(remote_root).expanduser().resolve():
            raise ValueError("predecessor root must differ from the remote root")
    if (
        not isinstance(predecessor_manifest, dict)
        or predecessor_manifest.get("schema") != "goal062-source-freeze-v1"
    ):
        raise ValueError("predecessor manifest schema changed")
    _validate_deadline_record(
        carry.get("predecessor_deadline"), predecessor_binding, "predecessor deadline"
    )
    allowed = carry.get("allowed_source_changes")
    if not isinstance(allowed, list):
        raise ValueError("allowed_source_changes is not a list")
    _validate_source_changes(predecessor_manifest, manifest, allowed)
    files = carry.get("files")
    if not isinstance(files, dict):
        raise ValueError("carry-forward files are not a mapping")
    for relative, expected in files.items():
        safe = _safe_carry_file(relative)
        _sha256_value(expected, f"carry-forward file {safe}")
        path = root / safe
        try:
            path.resolve().relative_to(root)
        except ValueError as error:
            raise ValueError("carry-forward file escapes the new root") from error
    return carry


def production_deadline(
    root: Path,
    now: datetime,
    binding: str,
    manifest: dict[str, Any],
    carry: dict[str, Any] | None,
) -> tuple[datetime, dict[str, Any]]:
    """Load or create the immutable production deadline, carrying it across repairs."""
    deadline_path = root / "production-deadline.json"
    if carry is not None:
        predecessor_binding = _sha256_value(
            carry["predecessor_binding_sha256"], "predecessor_binding_sha256"
        )
        _started, deadline, wall_seconds = _validate_deadline_record(
            carry["predecessor_deadline"], predecessor_binding, "predecessor deadline"
        )
        original = carry["predecessor_deadline"]
        expected = {
            "binding_sha256": binding,
            "predecessor_binding_sha256": predecessor_binding,
            "started_utc": original["started_utc"],
            "deadline_utc": original["deadline_utc"],
            "wall_seconds": wall_seconds,
        }
        if deadline_path.exists():
            saved = json.loads(deadline_path.read_text())
            if saved != expected:
                raise ValueError("production deadline binding changed")
        else:
            write(deadline_path, expected)
        return deadline, expected
    if deadline_path.exists():
        saved = json.loads(deadline_path.read_text())
        if saved.get("binding_sha256") != binding:
            raise ValueError("production deadline binding changed")
        deadline = _timestamp(saved.get("deadline_utc"), "production deadline")
        return deadline, saved
    budget = min(MAX_WALL_SECONDS, int(manifest["production_wall_seconds"]))
    deadline = now + timedelta(seconds=budget)
    record = {
        "binding_sha256": binding,
        "started_utc": now.isoformat(),
        "deadline_utc": deadline.isoformat(),
        "wall_seconds": budget,
    }
    with deadline_path.open("x") as handle:
        json.dump(record, handle)
    return deadline, record


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
        carry = load_carry_forward(root, manifest)
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
            if benchmark.get("runtime_changed") or carry is not None:
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
            deadline, _deadline_record = production_deadline(
                root, now, binding, manifest, carry
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
                "predecessor_binding_sha256": (
                    carry["predecessor_binding_sha256"] if carry is not None else None
                ),
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
