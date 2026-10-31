#!/usr/bin/env python3
"""Reproduce the archived underflow case with the raw-law log reference kernel."""

from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from latent_landscapes import log_domain_likelihood, preinvasion_likelihood

ROOT = Path(__file__).resolve().parents[2]
RAW_BANK = ROOT / "artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy"
PUBLIC = ROOT / "artifacts/goal060_execution/audit-repair/public_inputs/public_inputs.npz"
OBSERVATIONS = (
    ROOT
    / "artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation"
    / "cell-09/rep-000/observations.npz"
)
ORACLE = Path(__file__).with_name("parent_terminal_oracle.json")
OUTPUT = Path(__file__).with_name("reference-kernel-receipt.json")
SITE_ID = "cell_35_04"
EFFECT = 30.0
DETECTION_SD = 0.2013292938847899
ETAS = (-2.0, -0.9375, -0.875, 0.0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_inputs(site_ids: tuple[str, ...]) -> tuple[Any, Any]:
    with np.load(PUBLIC, allow_pickle=False) as saved:
        public_ids = tuple(str(value) for value in saved["site_ids"])
    with np.load(OBSERVATIONS, allow_pickle=False) as saved:
        observed_ids = tuple(str(value) for value in saved["site_ids"])
        positions = np.asarray([observed_ids.index(site_id) for site_id in site_ids])
        prey = np.asarray(saved["prey_counts"])[positions][None, :, :]
        predator = np.asarray(saved["predator_counts"])[positions][None, :, :]
    observations = preinvasion_likelihood.prepare_observations(
        prey, predator, site_ids, np.ones(len(site_ids), dtype=bool)
    )
    raw = np.load(RAW_BANK, mmap_mode="r", allow_pickle=False)
    public_positions = np.asarray([public_ids.index(site_id) for site_id in observations.site_ids])
    arrivals = np.ascontiguousarray(raw[:, public_positions])
    bank = preinvasion_likelihood.compress_bank(arrivals, observations.site_ids)
    return bank, observations


def stable_score(bank: Any, observations: Any, effect: float, eta: float) -> tuple[float, float]:
    started = time.perf_counter()
    score = log_domain_likelihood.exact_log_scores(
        observations,
        bank,
        [effect],
        np.full(len(bank.site_ids), math.exp(eta)),
        detection_sd=DETECTION_SD,
    )
    elapsed = time.perf_counter() - started
    return float(score.joint_loglikelihood[0, 0, 0]), elapsed


def direct_score(bank: Any, observations: Any, effect: float, eta: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            integration = preinvasion_likelihood.build_integration(
                bank,
                [effect],
                np.full(len(bank.site_ids), math.exp(eta)),
                exact=True,
            )
            score = preinvasion_likelihood.score_observations(
                observations, integration, detection_sd=DETECTION_SD
            )
        return {
            "status": "finite",
            "joint_loglikelihood": float(score.joint_loglikelihood[0, 0, 0]),
            "elapsed_seconds": time.perf_counter() - started,
        }
    except RuntimeError as error:
        return {
            "status": "failed",
            "error": str(error),
            "elapsed_seconds": time.perf_counter() - started,
        }


def main() -> None:
    bank, observations = load_inputs((SITE_ID,))
    rows = []
    for eta in ETAS:
        value, elapsed = stable_score(bank, observations, EFFECT, eta)
        rows.append(
            {
                "eta": eta,
                "stable_joint_loglikelihood": value,
                "stable_finite": math.isfinite(value),
                "stable_elapsed_seconds": elapsed,
                "probability_scale_direct": direct_score(
                    bank, observations, EFFECT, eta
                ),
            }
        )

    oracle_comparison: list[dict[str, float]] = []
    if ORACLE.is_file():
        oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
        oracle_values = {
            float(row["eta"]): float(row["joint_loglikelihood"])
            for row in oracle["results"]
        }
        oracle_comparison = [
            {
                "eta": float(row["eta"]),
                "stable_minus_oracle": (
                    float(row["stable_joint_loglikelihood"])
                    - oracle_values[float(row["eta"])]
                ),
            }
            for row in rows
        ]

    benchmark_ids = ("cell_00_02", SITE_ID, "cell_71_64")
    benchmark_bank, benchmark_observations = load_inputs(benchmark_ids)
    benchmark_hazards = np.exp(np.asarray((-4.0, -2.0, -0.875)))
    started = time.perf_counter()
    benchmark = log_domain_likelihood.exact_log_scores(
        benchmark_observations,
        benchmark_bank,
        [1.0, 3.0, 30.0],
        benchmark_hazards,
        detection_sd=DETECTION_SD,
    )
    benchmark_elapsed = time.perf_counter() - started

    source = Path(log_domain_likelihood.__file__).resolve()
    receipt = {
        "schema": "paper1-log-domain-reference-kernel-v1",
        "status": "prototype_verified",
        "generated_utc": datetime.now(UTC).isoformat(),
        "law": {
            "empirical_draws": bank.bank_size,
            "pseudo_arrivals": list(map(float, preinvasion_likelihood.arc2b.PSEUDO_ARRIVALS)),
            "denominator": bank.bank_size + 7,
            "arrival_category_rule": "searchsorted(canonical survey times, side=left)",
            "representation": (
                "raw draws; logsumexp arrival transforms; log survival-loss differences"
            ),
        },
        "actual_underflow_case": {
            "site_id": SITE_ID,
            "effect": EFFECT,
            "detection_sd": DETECTION_SD,
            "rows": rows,
            "independent_terminal_oracle_comparison": oracle_comparison,
            "max_abs_stable_minus_oracle": max(
                (abs(row["stable_minus_oracle"]) for row in oracle_comparison), default=None
            ),
        },
        "bounded_benchmark": {
            "site_ids": list(benchmark_observations.site_ids),
            "effects": [1.0, 3.0, 30.0],
            "site_log_hazards": [-4.0, -2.0, -0.875],
            "elapsed_seconds": benchmark_elapsed,
            "score_shape": list(benchmark.joint_loglikelihood.shape),
            "all_finite": bool(np.isfinite(benchmark.joint_loglikelihood).all()),
            "minimum_joint_loglikelihood": float(np.min(benchmark.joint_loglikelihood)),
            "maximum_joint_loglikelihood": float(np.max(benchmark.joint_loglikelihood)),
        },
        "inputs": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (RAW_BANK, PUBLIC, OBSERVATIONS)
        },
        "sources": {
            str(source.relative_to(ROOT)): sha256(source),
            str(Path(__file__).resolve().relative_to(ROOT)): sha256(Path(__file__).resolve()),
        },
    }
    if ORACLE.is_file():
        receipt["independent_oracle"] = {
            "path": str(ORACLE.relative_to(ROOT)),
            "sha256": sha256(ORACLE),
        }
    OUTPUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
