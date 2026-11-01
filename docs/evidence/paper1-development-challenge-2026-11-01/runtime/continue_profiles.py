"""Finish the finite profile dispatch after the running banks terminate."""

from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
receipt = BASE / "profile-dispatch-receipt.json"
started = BASE / "profile-dispatch-started.json"
if started.exists() or receipt.exists():
    raise FileExistsError("profile continuation has already been started")
started.write_text(json.dumps({"pid": os.getpid(), "started_epoch": time.time()}) + "\n")
try:
    deadline = time.monotonic() + 4 * 3600
    bank_pid = int((BASE / "bank-runner.pid").read_text())
    bank_result = None
    while time.monotonic() < deadline:
        path = BASE / "bank-ledger/receipt.json"
        if path.exists():
            try:
                bank_result = json.loads(path.read_text())
            except json.JSONDecodeError:
                pass
            if bank_result is not None:
                break
        try:
            os.kill(bank_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(30)
    if (
        not bank_result
        or not bank_result.get("complete")
        or len(bank_result.get("results", [])) != 6
    ):
        receipt.write_text(
            json.dumps(
                {
                    "state": "dispatch_blocked",
                    "reason": "bank runner has no complete six-job ledger; no additional profiles launched",
                    "bank_processes_not_terminated": True,
                },
                indent=2,
            )
            + "\n"
        )
        sys.exit(0)
    all_banks = bool(
        bank_result
        and bank_result.get("complete")
        and bank_result.get("all_executed")
        and len(bank_result["results"]) == 6
    )
    if all_banks:
        subprocess.run(
            [sys.executable, str(BASE / "build_jobs.py"), "--phase", "profiles"],
            cwd=ROOT,
            check=True,
        )
        source = BASE / "jobs-profiles.json"
        expected = 60
    else:
        source = BASE / "jobs-profiles-archived.json"
        expected = 48
    full = json.loads(source.read_text())
    initial = json.loads((BASE / "jobs-profiles-first12.json").read_text())
    prior = {row["job_id"]: row for row in initial["jobs"]}
    lookup = {row["job_id"]: row for row in full["jobs"]}
    if len(lookup) != expected or len(prior) != 12 or not set(prior) <= set(lookup):
        raise ValueError("finite profile membership does not match the planned dispatch")
    for key, row in prior.items():
        if (
            row["arguments"] != lookup[key]["arguments"]
            or row["input_sha256"] != lookup[key]["input_sha256"]
        ):
            raise ValueError("initial profile identity differs from full manifest")
    pending = [row for row in full["jobs"] if row["job_id"] not in prior]
    target = BASE / "jobs-profiles-after-banks.json"
    with target.open("x") as handle:
        json.dump({**full, "phase": "profiles-after-banks", "jobs": pending}, handle, indent=2)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/execute_development_jobs.py"),
            "--jobs",
            str(target),
            "--workers",
            "48",
            "--ledger",
            str(BASE / "profiles-after-banks-ledger"),
        ],
        cwd=ROOT,
    )
    receipt.write_text(
        json.dumps(
            {
                "state": "dispatch_finished",
                "all_banks_executed": all_banks,
                "planned_total_profile_jobs": expected,
                "initial_profile_jobs": 12,
                "subsequent_profile_jobs": len(pending),
                "runner_exit_code": result.returncode,
                "run_receipt": str(BASE / "profiles-after-banks-ledger/receipt.json"),
                "completion_is_not_scientific_acceptance": True,
            },
            indent=2,
        )
        + "\n"
    )
except Exception as error:
    receipt.write_text(
        json.dumps(
            {"state": "failed", "type": type(error).__name__, "message": str(error)}, indent=2
        )
        + "\n"
    )
    raise
