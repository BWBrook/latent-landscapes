"""Replay the six challenge datasets through scripts/fit_dataset.py and summarise.

Run from the repository root on a clean commit:

    uv run python docs/evidence/paper1-sprint1-2026-11-05/replay_fit_dataset.py \
        --output-root artifacts/sprint1/replays --workers 6

Receipts stay under the (git-ignored) output root; the committed summary is
replay-fit-dataset.json beside this script.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PANEL = ROOT / "artifacts/paper1_development_challenge_20261101/archived-panel"
DATASETS = (
    "cell-00-rep-005-arm-B",
    "cell-01-rep-006-arm-A",
    "cell-04-rep-005-arm-A",
    "cell-06-rep-006-arm-B",
    "cell-08-rep-006-arm-B",
    "cell-09-rep-005-arm-B",
)
INPUTS = {
    "--input-dir": PANEL / "public/legacy",
    "--arrival-bank": ROOT / "artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy",
    "--compressed-bank": ROOT
    / "artifacts/paper1_profile_development_20261018/arrival-bank-order192.npz",
}
THREADS = ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_NUM_THREADS")


def run_one(dataset: str, output_root: Path) -> Path:
    out = output_root / dataset
    command = [sys.executable, str(ROOT / "scripts/fit_dataset.py")]
    for flag, path in INPUTS.items():
        command += [flag, str(path)]
    command += ["--observations", str(PANEL / "datasets" / dataset / "observations.npz")]
    command += ["--output-dir", str(out)]
    env = {**os.environ, **{name: "1" for name in THREADS}}
    log = output_root / f"{dataset}.log"
    with log.open("w") as handle:
        subprocess.run(
            command, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT, check=True
        )
    return out / "receipt.json"


def summarise(receipt_path: Path) -> dict[str, Any]:
    receipt = json.loads(receipt_path.read_text())
    search = json.loads(Path(receipt["search"]["receipt"]).read_text())
    spatial = receipt["families"].get("spatial", {}).get("standard", {})
    free = search["free"]["False"]
    sigmas = [
        math.exp(row["positive_sigma"]["parameters"]["log_sigma"])
        for row in search["points"]["False"]
    ]
    contacts = sorted(
        {
            contact
            for row in search["points"]["False"]
            for contact in row["positive_sigma"].get("bound_contacts", [])
        }
    )
    level = next((lv for lv in search["level_sets"] if abs(lv["cutoff"] - 3.84) < 1e-9), None)
    audit = receipt["latent_audit"]
    return {
        "dataset": receipt_path.parent.name,
        "failure_class": receipt["failure_class"],
        "all_triggered": receipt["all_triggered"],
        "search_status": search["status"],
        "free": {
            family: {"h": free[family]["h"], "criterion": free[family]["criterion"]}
            for family in ("positive_sigma", "sigma_zero")
        },
        "roots_3_84": [root["h"] for root in level["roots"]] if level else [],
        "spatial_lr1": spatial.get("lr1"),
        "positive_sigma_range": [min(sigmas), max(sigmas)],
        "positive_sigma_at_upper_bound": sum(s >= 1.5 * (1 - 1e-9) for s in sigmas),
        "positive_bound_contacts": contacts,
        "unique_h": len(search["points"]["False"]),
        "audit": {
            k: audit.get(k)
            for k in ("lr_limit", "audit_count", "skipped_beyond_lr_limit", "multimodal_latent")
        },
        "audit_seconds": audit.get("wall_seconds"),
        "criterion_stats": receipt["cost"]["criterion_stats"],
        "stages": {k: v["wall_seconds"] for k, v in receipt["cost"]["stages"].items()},
        "peak_rss_bytes": receipt["cost"]["peak_rss_bytes"],
        "source": receipt["source"],
        "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=len(DATASETS))
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(args.workers) as pool:
        receipts = list(pool.map(run_one, DATASETS, [args.output_root] * len(DATASETS)))
    summary = [summarise(path) for path in receipts]
    (HERE / "replay-fit-dataset.json").write_text(json.dumps(summary, indent=1) + "\n")
    for row in summary:
        print(row["dataset"], row["failure_class"], row["roots_3_84"], row["stages"].get("search"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
