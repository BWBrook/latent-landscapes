from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.differentiable_likelihood import prepare_site_likelihood


ROOT = Path("/Users/bwbrook/papers/latent-landscapes")
OBSERVATIONS = ROOT / (
    "artifacts/goal062_execution/completed-20261015/snapshot/production/"
    "evaluation/cell-09/rep-000/observations.npz"
)
PUBLIC = ROOT / "artifacts/goal060_execution/audit-repair/public_inputs/public_inputs.npz"
RAW = ROOT / "artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy"
ORDER816 = ROOT / (
    "artifacts/paper1_profile_development_20261018/"
    "arrival-bank-order816-max290.npz"
)
SOURCE = ROOT / "src/latent_landscapes/differentiable_likelihood.py"
OUTPUT = Path("/private/tmp/cell35-high-order-series-replay.json")
SITE = "cell_35_04"
DETECTION_SD = 0.2013292938847899


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    with np.load(OBSERVATIONS, allow_pickle=False) as saved:
        ids = tuple(str(value) for value in saved["site_ids"])
        position = ids.index(SITE)
        prey = np.asarray(saved["prey_counts"])[position][None, None, :]
        predator = np.asarray(saved["predator_counts"])[position][None, None, :]
    observed = likelihood.prepare_observations(
        prey, predator, (SITE,), np.ones(1, dtype=bool)
    )
    with np.load(PUBLIC, allow_pickle=False) as saved:
        public_ids = tuple(str(value) for value in saved["site_ids"])
    with np.load(ORDER816, allow_pickle=False) as saved:
        source_ids = tuple(str(value) for value in saved["site_ids"])
        compressed_position = source_ids.index(SITE)
        raw = np.load(RAW, mmap_mode="r", allow_pickle=False)
        raw_position = public_ids.index(SITE)
        bank = likelihood.CompressedBank(
            observed.site_ids,
            int(saved["bank_size"]),
            np.ascontiguousarray(saved["category_counts"][[compressed_position]]),
            np.ascontiguousarray(saved["category_mass"][[compressed_position]]),
            np.ascontiguousarray(saved["power_moments"][[compressed_position]]),
            np.ascontiguousarray(raw[:, [raw_position]]),
            str(saved["bank_checksum"]),
            int(saved["series_order"]),
            float(saved["max_x"]),
        )
    series = prepare_site_likelihood(
        observed, bank, 30.0, detection_sd=DETECTION_SD
    )
    exact = prepare_site_likelihood(
        observed, replace(bank, max_x=0.0), 30.0, detection_sd=DETECTION_SD
    )
    rows = []
    for eta in (-2.0, -0.9375, -0.875, 0.0):
        point = np.asarray([eta])
        series_result = series.evaluate(point)
        exact_result = exact.evaluate(point)
        rows.append(
            {
                "eta": eta,
                "x": 290.0 * math.exp(eta),
                "series_branch_site_count": int(
                    series.stats["last_series_site_count"]
                ),
                "exact_branch_site_count": int(exact.stats["last_exact_site_count"]),
                "series_value_d1_d2_d3": [
                    float(result[0]) for result in series_result
                ],
                "exact_value_d1_d2_d3": [
                    float(result[0]) for result in exact_result
                ],
                "series_minus_exact": [
                    float(series_result[index][0] - exact_result[index][0])
                    for index in range(4)
                ],
            }
        )
    receipt = {
        "schema": "paper1-cell35-high-order-series-replay-v1",
        "status": "bounded_replay_complete",
        "generated_utc": datetime.now(UTC).isoformat(),
        "scope": (
            "Actual formerly underflowing B_H3 site under the production order-816 "
            "positive-series path versus the same empirical-plus-pseudo raw sum; not a "
            "profile, bank-precision certificate, or Laplace-accuracy result."
        ),
        "site_id": SITE,
        "effect": 30.0,
        "detection_sd": DETECTION_SD,
        "bank_size": int(bank.bank_size),
        "series_order": int(bank.series_order),
        "series_max_x": float(bank.max_x),
        "tail_bound_scope": str(series.stats["tail_bound_scope"]),
        "rows": rows,
        "max_abs_series_minus_exact": [
            max(abs(row["series_minus_exact"][index]) for row in rows)
            for index in range(4)
        ],
        "acceptance": {
            "all_rows_used_series_path": all(
                row["series_branch_site_count"] == 1 for row in rows
            ),
            "all_rows_used_exact_comparator": all(
                row["exact_branch_site_count"] == 1 for row in rows
            ),
            "value_d1_d2_error_le_1e_minus_11": max(
                max(abs(value) for value in row["series_minus_exact"][:3])
                for row in rows
            )
            <= 1e-11,
            "d3_roundoff_le_2e_minus_9": max(
                abs(row["series_minus_exact"][3]) for row in rows
            )
            <= 2e-9,
        },
        "runtime": {"python": sys.version, "platform": platform.platform()},
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for path in (OBSERVATIONS, PUBLIC, RAW, ORDER816, SOURCE)
        },
        "script_sha256": None,
    }
    receipt["script_sha256"] = sha256_file(Path(__file__).resolve())
    OUTPUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
