"""Execute a finite, frozen list of development jobs with retained exit receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def run_job(job: dict[str, Any], ledger: Path) -> dict[str, Any]:
    started = time.perf_counter()
    key = job["job_id"]
    receipt_path = ledger / f"{key}.json"
    if receipt_path.exists():
        raise FileExistsError(receipt_path)
    env = {
        **os.environ,
        **{
            name: "1"
            for name in ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_NUM_THREADS")
        },
    }
    command = [sys.executable, str(ROOT / job["script"]), *job["arguments"]]
    result: dict[str, Any] = {"job_id": key, "command": command, "state": "running", "pid": None}
    for name, expected in job.get("input_sha256", {}).items():
        if sha256(Path(name)) != expected:
            raise ValueError(f"job input drift: {name}")
    with (ledger / f"{key}.log").open("w") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        result["pid"] = process.pid
        receipt_path.write_text(json.dumps(result, indent=2) + "\n")
        returncode = process.wait()
    receipt = Path(job["output_dir"]) / "receipt.json"
    manifest = Path(job["output_dir"]) / "manifest.json"
    product = receipt if receipt.exists() else manifest if manifest.exists() else None
    result.update(
        state="completed" if returncode == 0 and product is not None else "failed",
        returncode=returncode,
        elapsed_seconds=time.perf_counter() - started,
        output_receipt=None if product is None else str(product),
        output_sha256=None if product is None else sha256(product),
    )
    receipt_path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--workers", type=int, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.workers <= 56:
        raise ValueError("workers outside reviewed allocation")
    jobs = json.loads(args.jobs.read_text())["jobs"]
    ids = [row["job_id"] for row in jobs]
    if len(set(ids)) != len(ids) or any("/" in key or key in {".", ".."} for key in ids):
        raise ValueError("job IDs must be unique simple names")
    allowed = {
        "scripts/prepare_development_banks.py",
        "scripts/run_development_profile.py",
        "scripts/screen_spatial_importance.py",
        "scripts/compare_development_banks.py",
    }
    if any(job["script"] not in allowed for job in jobs):
        raise ValueError("unexpected job entrypoint")
    if len({str(Path(job["output_dir"]).resolve()) for job in jobs}) != len(jobs):
        raise ValueError("job output directories collide")
    args.ledger.mkdir(parents=True, exist_ok=False)
    identity = sha256(args.jobs)
    (args.ledger / "started.json").write_text(
        json.dumps({"jobs_sha256": identity, "workers": args.workers, "jobs": ids}, indent=2) + "\n"
    )
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_job, job, args.ledger): job["job_id"] for job in jobs}
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as error:
                result = {
                    "job_id": futures[future],
                    "state": "failed",
                    "type": type(error).__name__,
                    "message": str(error),
                }
                (args.ledger / f"{futures[future]}.json").write_text(
                    json.dumps(result, indent=2) + "\n"
                )
            results.append(result)
            print(json.dumps({k: result[k] for k in ("job_id", "state")}), flush=True)
    if sha256(args.jobs) != identity:
        raise RuntimeError("job manifest drift")
    (args.ledger / "receipt.json").write_text(
        json.dumps(
            {
                "jobs_sha256": identity,
                "results": results,
                "complete": len(results) == len(jobs),
                "all_executed": all(r["state"] == "completed" for r in results),
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
