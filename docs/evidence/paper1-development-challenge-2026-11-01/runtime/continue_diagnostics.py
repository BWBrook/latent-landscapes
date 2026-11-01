"""Finish the frozen development challenge after the profile jobs terminate.

This controller owns execution bookkeeping only.  A completed process or
receipt is evidence that a job ran; it is not evidence of scientific success.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
INITIAL_SCREEN_ID = "cell-00-rep-005-arm-A"
TERMINAL_STATES = {"completed", "failed"}


class ContinuationError(RuntimeError):
    """Raised when continuation cannot be reconciled safely."""


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContinuationError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise ContinuationError(f"JSON object required: {path}")
    return value


def write_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def process_active(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0 or pid == os.getpid():
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def expected_command(job: dict[str, Any], executable: str) -> list[str]:
    return [executable, str(ROOT / job["script"]), *job["arguments"]]


def normalized_initial_arguments(arguments: Any) -> Any:
    """Resolve only the known relative initial-screen profile argument."""
    if not isinstance(arguments, list):
        return arguments
    result = list(arguments)
    for index, value in enumerate(result):
        if index and result[index - 1] == "--profile" and isinstance(value, str):
            profile = Path(value)
            if not profile.is_absolute():
                result[index] = str((ROOT / profile).resolve())
    return result


def verify_job_manifest(
    path: Path, expected_count: int | None = None, *, allow_missing_panel: bool = False
) -> dict[str, Any]:
    manifest = read_json(path)
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list) or not all(isinstance(row, dict) for row in jobs):
        raise ContinuationError(f"{path} does not contain a jobs list")
    if expected_count is not None and len(jobs) != expected_count:
        raise ContinuationError(f"{path} has an unexpected job count")
    identifiers = [row.get("job_id") for row in jobs]
    if any(not isinstance(identifier, str) for identifier in identifiers):
        raise ContinuationError(f"{path} contains a malformed job ID")
    if len(set(identifiers)) != len(identifiers):
        raise ContinuationError(f"{path} contains duplicate job IDs")
    panel_hash = manifest.get("frozen_panel_sha256")
    if panel_hash is None and allow_missing_panel:
        return manifest
    if panel_hash != sha256(BASE / "panel-manifest.json"):
        raise ContinuationError(f"{path} is not bound to the frozen panel")
    return manifest


def verify_current_inputs(job: dict[str, Any]) -> None:
    for name, expected in job.get("input_sha256", {}).items():
        path = Path(name)
        if not path.is_file() or sha256(path) != expected:
            raise ContinuationError(f"job input drift: {name}")


def verify_ledger(
    *,
    manifest_path: Path,
    ledger_path: Path,
    executable: str,
    expected_ids: set[str],
    require_all_executed: bool = False,
    allow_missing_panel: bool = False,
) -> dict[str, Any]:
    manifest = verify_job_manifest(manifest_path, allow_missing_panel=allow_missing_panel)
    jobs = {row["job_id"]: row for row in manifest["jobs"]}
    if set(jobs) != expected_ids:
        raise ContinuationError(f"manifest/ledger population differs for {manifest_path}")
    receipt_path = ledger_path / "receipt.json"
    if not receipt_path.is_file():
        raise ContinuationError(f"execution ledger is incomplete: {receipt_path}")
    receipt = read_json(receipt_path)
    if receipt.get("jobs_sha256") != sha256(manifest_path) or receipt.get("complete") is not True:
        raise ContinuationError(f"execution ledger identity or completion differs: {ledger_path}")
    results = receipt.get("results")
    if not isinstance(results, list) or not all(isinstance(row, dict) for row in results):
        raise ContinuationError(f"execution ledger results are malformed: {ledger_path}")
    if {row.get("job_id") for row in results} != expected_ids:
        raise ContinuationError(f"execution ledger job IDs differ: {ledger_path}")
    if len(results) != len(expected_ids):
        raise ContinuationError(f"execution ledger contains duplicate or missing results: {ledger_path}")
    for result in results:
        job_id = result.get("job_id")
        if result.get("state") not in TERMINAL_STATES:
            raise ContinuationError(f"non-terminal job state for {job_id}")
        if process_active(result.get("pid")):
            raise ContinuationError(f"job process remains active for {job_id}")
        job = jobs[job_id]
        verify_current_inputs(job)
        command = result.get("command")
        if not isinstance(command, list) or command != expected_command(job, executable):
            raise ContinuationError(f"job command differs for {job_id}")
        detail = ledger_path / f"{job_id}.json"
        if not detail.is_file() or read_json(detail) != result:
            raise ContinuationError(f"per-job terminal receipt differs for {job_id}")
        if result.get("state") == "completed":
            output = result.get("output_receipt")
            output_sha = result.get("output_sha256")
            if not isinstance(output, str) or not isinstance(output_sha, str):
                raise ContinuationError(f"completed job lacks output identity: {job_id}")
            output_path = Path(output)
            if not output_path.is_file() or sha256(output_path) != output_sha:
                raise ContinuationError(f"completed output identity differs: {job_id}")
    if require_all_executed and receipt.get("all_executed") is not True:
        raise ContinuationError(f"required ledger contains failed jobs: {ledger_path}")
    return receipt


def wait_for_profiles(deadline: float, poll_seconds: float) -> dict[str, Any]:
    full_path = BASE / "jobs-profiles.json"
    first_path = BASE / "jobs-profiles-first12.json"
    after_path = BASE / "jobs-profiles-after-banks.json"
    dispatch_path = BASE / "profile-dispatch-receipt.json"
    manifest_ids: tuple[set[str], set[str], set[str]] | None = None
    while time.monotonic() < deadline:
        if manifest_ids is None:
            if not full_path.is_file() or not first_path.is_file() or not after_path.is_file():
                started = BASE / "profile-dispatch-started.json"
                if started.is_file() and not process_active(read_json(started).get("pid")):
                    raise ContinuationError("profile controller stopped before complete manifests")
                time.sleep(poll_seconds)
                continue
            full = verify_job_manifest(full_path, expected_count=60)
            first = verify_job_manifest(first_path, expected_count=12)
            after = verify_job_manifest(after_path, expected_count=48)
            full_ids = {row["job_id"] for row in full["jobs"]}
            first_ids = {row["job_id"] for row in first["jobs"]}
            after_ids = {row["job_id"] for row in after["jobs"]}
            if first_ids & after_ids or first_ids | after_ids != full_ids:
                raise ContinuationError("profile ledgers do not partition the frozen sixty-job manifest")
            full_jobs = {row["job_id"]: row for row in full["jobs"]}
            for subset_name, subset in (("initial", first), ("after-banks", after)):
                for row in subset["jobs"]:
                    reference = full_jobs[row["job_id"]]
                    for field in ("script", "arguments", "input_sha256", "output_dir"):
                        if (
                            field not in row
                            or field not in reference
                            or row[field] != reference[field]
                        ):
                            raise ContinuationError(
                                f"{subset_name} profile binding differs for {row['job_id']}"
                            )
            manifest_ids = (full_ids, first_ids, after_ids)
        _, first_ids, after_ids = manifest_ids
        if dispatch_path.exists():
            dispatch = read_json(dispatch_path)
            if dispatch.get("state") != "dispatch_finished":
                raise ContinuationError(f"profile dispatch did not finish: {dispatch}")
            if (
                dispatch.get("planned_total_profile_jobs") != 60
                or dispatch.get("initial_profile_jobs") != 12
                or dispatch.get("subsequent_profile_jobs") != 48
                or dispatch.get("all_banks_executed") is not True
                or dispatch.get("runner_exit_code") != 0
            ):
                raise ContinuationError("profile dispatch receipt is not the full sixty-job run")
        first_receipt = BASE / "profiles-first12-ledger/receipt.json"
        after_receipt = BASE / "profiles-after-banks-ledger/receipt.json"
        if first_receipt.is_file() and after_receipt.is_file() and dispatch_path.is_file():
            first_result = verify_ledger(
                manifest_path=first_path,
                ledger_path=first_receipt.parent,
                executable=sys.executable,
                expected_ids=first_ids,
            )
            after_result = verify_ledger(
                manifest_path=after_path,
                ledger_path=after_receipt.parent,
                executable=sys.executable,
                expected_ids=after_ids,
            )
            return {
                "manifest": str(full_path),
                "manifest_sha256": sha256(full_path),
                "first12": first_result,
                "after_banks": after_result,
            }
        first_complete = False
        if first_receipt.is_file():
            first_complete = read_json(first_receipt).get("complete") is True
        if not first_complete:
            runner_pid_path = BASE / "profiles-first12-runner.pid"
            if runner_pid_path.is_file() and not process_active(
                int(runner_pid_path.read_text().strip())
            ):
                if not first_receipt.is_file() or read_json(first_receipt).get("complete") is not True:
                    raise ContinuationError(
                        "initial profile runner stopped before its ledger completed"
                    )
        after_complete = (
            read_json(after_receipt).get("complete") is True
            if after_receipt.is_file()
            else False
        )
        dispatch_complete = (
            read_json(dispatch_path).get("state") == "dispatch_finished"
            if dispatch_path.is_file()
            else False
        )
        if not (after_complete and dispatch_complete):
            started = BASE / "profile-dispatch-started.json"
            if started.is_file() and not process_active(read_json(started).get("pid")):
                final_after = (
                    read_json(after_receipt).get("complete") is True
                    if after_receipt.is_file()
                    else False
                )
                final_dispatch = (
                    read_json(dispatch_path).get("state") == "dispatch_finished"
                    if dispatch_path.is_file()
                    else False
                )
                if not (final_after and final_dispatch):
                    raise ContinuationError("profile controller stopped before complete ledgers")
        time.sleep(poll_seconds)
    raise ContinuationError("profile ledgers did not complete before the finite deadline")


def run_builder(phase: str, python: str) -> Path:
    manifest_path = BASE / f"jobs-{phase}.json"
    unavailable_path = BASE / f"unavailable-{phase}.json"
    if manifest_path.exists():
        verify_job_manifest(manifest_path)
        return manifest_path
    if unavailable_path.exists():
        raise ContinuationError(f"builder left an orphaned unavailable file: {unavailable_path}")
    result = subprocess.run(
        [python, str(BASE / "build_jobs.py"), "--phase", phase],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0 or not manifest_path.is_file():
        raise ContinuationError(f"job builder failed for {phase}")
    verify_job_manifest(manifest_path)
    return manifest_path


def reject_unknown_outputs(root: Path, expected: set[str], allowed_existing: set[str]) -> None:
    if not root.exists():
        return
    for child in root.iterdir():
        if child.name not in expected or child.name not in allowed_existing:
            raise ContinuationError(f"unknown or pre-existing output: {child}")


def reconcile_initial_screen(screen_manifest: Path) -> dict[str, Any]:
    initial_manifest_path = BASE / "jobs-screens-initial.json"
    ledger_path = BASE / "screens-initial-ledger"
    initial = verify_job_manifest(
        initial_manifest_path, expected_count=1, allow_missing_panel=True
    )
    full_jobs = {row["job_id"]: row for row in read_json(screen_manifest)["jobs"]}
    row = initial["jobs"][0]
    if row.get("job_id") != INITIAL_SCREEN_ID or INITIAL_SCREEN_ID not in full_jobs:
        raise ContinuationError("initial screen is not the authorised single dataset")
    full_row = full_jobs[INITIAL_SCREEN_ID]
    optional_builder_metadata = {"site_count", "observations_sha256"}
    for field in set(row) | set(full_row):
        if field in optional_builder_metadata and field not in row:
            continue
        if field not in row or field not in full_row:
            raise ContinuationError(
                "initial screen arguments or bindings differ from the full screen manifest"
            )
        left = normalized_initial_arguments(row[field]) if field == "arguments" else row[field]
        right = (
            normalized_initial_arguments(full_row[field])
            if field == "arguments"
            else full_row[field]
        )
        if left != right:
            raise ContinuationError(
                "initial screen arguments or bindings differ from the full screen manifest"
            )
    receipt = verify_ledger(
        manifest_path=initial_manifest_path,
        ledger_path=ledger_path,
        executable=sys.executable,
        expected_ids={INITIAL_SCREEN_ID},
        require_all_executed=True,
        allow_missing_panel=True,
    )
    return receipt


def write_subset(full_path: Path, subset_path: Path, excluded: set[str], phase: str) -> Path:
    full = read_json(full_path)
    jobs = [row for row in full["jobs"] if row["job_id"] not in excluded]
    value = {**full, "phase": phase, "jobs": jobs}
    if subset_path.exists():
        if read_json(subset_path) != value:
            raise ContinuationError(f"existing finite manifest differs: {subset_path}")
    else:
        write_exclusive(subset_path, value)
    return subset_path


def run_executor(
    manifest: Path,
    ledger: Path,
    python: str,
    workers: int,
    timeout_hours: float,
    poll_seconds: float = 30.0,
) -> dict[str, Any]:
    if ledger.exists():
        raise ContinuationError(f"finite execution ledger already exists: {ledger}")
    process = subprocess.Popen(
        [
            python,
            str(ROOT / "scripts/execute_development_jobs.py"),
            "--jobs",
            str(manifest),
            "--workers",
            str(workers),
            "--ledger",
            str(ledger),
        ],
        cwd=ROOT,
    )
    deadline = time.monotonic() + timeout_hours * 3600
    while process.poll() is None:
        if time.monotonic() >= deadline:
            raise ContinuationError(f"executor exceeded finite deadline; left running: {process.pid}")
        time.sleep(poll_seconds)
    if process.returncode != 0:
        raise ContinuationError(f"executor stopped with exit code {process.returncode}")
    jobs = read_json(manifest)["jobs"]
    return verify_ledger(
        manifest_path=manifest,
        ledger_path=ledger,
        executable=python,
        expected_ids={row["job_id"] for row in jobs},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    parser.add_argument("--timeout-hours", type=float, default=24.0)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()
    if args.poll_seconds <= 0 or args.timeout_hours <= 0:
        raise ValueError("polling and timeout values must be positive")
    started_path = BASE / "continue-diagnostics-started.json"
    receipt_path = BASE / "continue-diagnostics-receipt.json"
    if started_path.exists() or receipt_path.exists():
        raise FileExistsError("diagnostic continuation has already been started")
    write_exclusive(
        started_path,
        {"schema": "development-challenge-continuation-v1", "pid": os.getpid(), "started_epoch": time.time()},
    )
    stage = "profiles"
    try:
        profile_result = wait_for_profiles(
            time.monotonic() + args.timeout_hours * 3600, args.poll_seconds
        )
        stage = "screens"
        screens_manifest = run_builder("screens", args.python)
        reconcile_initial_screen(screens_manifest)
        all_screen_ids = {row["job_id"] for row in read_json(screens_manifest)["jobs"]}
        reject_unknown_outputs(BASE / "importance", all_screen_ids, {INITIAL_SCREEN_ID})
        remaining_screens = write_subset(
            screens_manifest,
            BASE / "jobs-screens-remaining.json",
            {INITIAL_SCREEN_ID},
            "screens-remaining",
        )
        screen_result = run_executor(
            remaining_screens,
            BASE / "screens-remaining-ledger",
            args.python,
            max(1, min(56, len(read_json(remaining_screens)["jobs"]))),
            args.timeout_hours,
            args.poll_seconds,
        )
        stage = "comparisons"
        comparisons_manifest = run_builder("comparisons", args.python)
        comparison_ids = {row["job_id"] for row in read_json(comparisons_manifest)["jobs"]}
        reject_unknown_outputs(BASE / "bank-comparisons", comparison_ids, set())
        comparisons_final = write_subset(
            comparisons_manifest,
            BASE / "jobs-comparisons-final.json",
            set(),
            "comparisons-final",
        )
        comparison_result = run_executor(
            comparisons_final,
            BASE / "comparisons-final-ledger",
            args.python,
            max(1, min(56, len(comparison_ids))),
            args.timeout_hours,
            args.poll_seconds,
        )
        stage = "summary"
        summary_dir = BASE / "summary-final"
        if summary_dir.exists():
            raise ContinuationError(f"summary output already exists: {summary_dir}")
        summary_jobs = BASE / "jobs-summary.json"
        if not summary_jobs.is_file():
            raise ContinuationError("enriched jobs-summary.json is missing")
        summary = subprocess.run(
            [
                args.python,
                str(ROOT / "scripts/summarize_development_challenge.py"),
                "--jobs",
                str(summary_jobs),
                "--manifest",
                str(BASE / "panel-manifest.json"),
                "--output-dir",
                str(summary_dir),
            ],
            cwd=ROOT,
            check=False,
        )
        if summary.returncode != 0 or not (summary_dir / "summary.json").is_file():
            raise ContinuationError("summary builder failed")
        write_exclusive(
            receipt_path,
            {
                "schema": "development-challenge-continuation-v1",
                "state": "completed",
                "profile_ledgers": profile_result,
                "initial_screen_skipped": INITIAL_SCREEN_ID,
                "screens": screen_result,
                "comparisons": comparison_result,
                "summary": {"path": str(summary_dir / "summary.json"), "sha256": sha256(summary_dir / "summary.json")},
                "completion_is_not_scientific_acceptance": True,
            },
        )
    except Exception as error:
        write_exclusive(
            receipt_path,
            {
                "schema": "development-challenge-continuation-v1",
                "state": "failed",
                "stage": stage,
                "type": type(error).__name__,
                "message": str(error),
                "completion_is_not_scientific_acceptance": True,
            },
        )
        raise


if __name__ == "__main__":
    main()
