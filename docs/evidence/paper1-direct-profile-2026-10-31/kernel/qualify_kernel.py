#!/usr/bin/env python3
"""Qualify the differentiable kernel on one bounded B_H3 history."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import platform
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import log_domain_likelihood
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.capstone_qualification import subset_bank, subset_observations
from latent_landscapes.differentiable_likelihood import prepare_site_likelihood

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / "artifacts/goal060_execution/audit-repair/public_inputs"
RAW_BANK = ROOT / "artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy"
COMPRESSED = ROOT / "artifacts/paper1_profile_development_20261018/arrival-bank-order192.npz"
ORDER816 = (
    ROOT / "artifacts/paper1_profile_development_20261018/arrival-bank-order816-max290.npz"
)
OBSERVATIONS = (
    ROOT
    / "artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation"
    / "cell-09/rep-000/observations.npz"
)
ARCHIVED = ROOT / "artifacts/paper1_planning_20261018/gp-prototype/results.json"
DRIVER = ROOT / "scripts/benchmark_spatial_profile.py"
MODULE = ROOT / "src/latent_landscapes/differentiable_likelihood.py"
REFERENCE = ROOT / "src/latent_landscapes/log_domain_likelihood.py"
TEST = ROOT / "tests/test_differentiable_likelihood.py"
OUTPUT = Path(__file__).with_name("kernel-receipt.json")
SCRIPT = Path(__file__).resolve()
AUDITED_SNAPSHOT = Path(__file__).with_name("differentiable_likelihood-19157fbe.py")
INDEPENDENT_AUDIT = Path(__file__).with_name("fixed-h3-independent-audit-receipt.json")
HIGH_SITE = "cell_35_04"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(name: str, path: Path) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def load_training() -> tuple[Any, Any, np.ndarray, tuple[str, ...]]:
    driver = load_module("fast_likelihood_benchmark_driver", DRIVER)
    public, exposure = driver.load_public_arrays(PUBLIC)
    observed, observation_ids = driver.load_observations(
        OBSERVATIONS, public=public, history=0
    )
    site_a, _, _ = driver._exposure_for_sites(public, exposure, observation_ids)
    public_ids = driver._as_site_ids(public["site_ids"], name="public site_ids")
    bank, _, _ = driver.load_bank(
        raw_path=None,
        compressed_path=COMPRESSED,
        public_ids=public_ids,
        selected_ids=observation_ids,
    )
    training = np.asarray(observed.training_mask, dtype=bool)
    bank = subset_bank(bank, training)
    observed = subset_observations(observed, training)
    site_a = np.ascontiguousarray(site_a[training])
    raw = np.load(RAW_BANK, mmap_mode="r", allow_pickle=False)
    positions = {site_id: index for index, site_id in enumerate(public_ids)}
    selected = np.asarray([positions[site_id] for site_id in observed.site_ids])
    arrivals = np.ascontiguousarray(raw[:, selected])
    return replace(bank, bank_arrivals=arrivals), observed, site_a, public_ids


def time_call(callable_: Any, repetitions: int) -> tuple[Any, list[float]]:
    result = None
    elapsed = []
    for _ in range(repetitions):
        started = time.perf_counter()
        result = callable_()
        elapsed.append(time.perf_counter() - started)
    return result, elapsed


def high_hazard_rows(public_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    with np.load(OBSERVATIONS, allow_pickle=False) as saved:
        ids = tuple(str(value) for value in saved["site_ids"])
        site = ids.index(HIGH_SITE)
        prey = np.asarray(saved["prey_counts"])[site][None, None, :]
        predator = np.asarray(saved["predator_counts"])[site][None, None, :]
    observed = likelihood.prepare_observations(
        prey, predator, (HIGH_SITE,), np.ones(1, dtype=bool)
    )
    raw = np.load(RAW_BANK, mmap_mode="r", allow_pickle=False)
    arrivals = np.ascontiguousarray(raw[:, [public_ids.index(HIGH_SITE)]])
    bank = likelihood.compress_bank(arrivals, observed.site_ids, series_order=192)
    evaluator = prepare_site_likelihood(
        observed, bank, 30.0, detection_sd=0.2013292938847899
    )
    rows = []
    for eta in (-2.0, -0.9375, -0.875, 0.0):
        started = time.perf_counter()
        result = evaluator.evaluate(np.asarray([eta]))
        elapsed = time.perf_counter() - started
        reference = log_domain_likelihood.exact_log_scores(
            observed,
            bank,
            [30.0],
            np.exp(np.asarray([eta])),
            detection_sd=0.2013292938847899,
        ).joint_loglikelihood[0, 0, 0]
        rows.append(
            {
                "eta": eta,
                "joint_loglikelihood": float(result[0][0]),
                "d1": float(result[1][0]),
                "d2": float(result[2][0]),
                "d3": float(result[3][0]),
                "minus_log_domain_reference": float(result[0][0] - reference),
                "elapsed_seconds": elapsed,
                "branch": "exact_raw",
            }
        )
    return rows


def high_x_roundoff(
    observed: Any, public_ids: tuple[str, ...]
) -> list[dict[str, Any]]:
    selected_mask = np.zeros(len(observed.site_ids), dtype=bool)
    selected_mask[[0, len(selected_mask) // 2, len(selected_mask) - 1]] = True
    selected_observed = subset_observations(observed, selected_mask)
    with np.load(ORDER816, allow_pickle=False) as saved:
        source_ids = tuple(str(value) for value in saved["site_ids"])
        positions = np.asarray([source_ids.index(value) for value in selected_observed.site_ids])
        raw = np.load(RAW_BANK, mmap_mode="r", allow_pickle=False)
        public_positions = np.asarray(
            [public_ids.index(value) for value in selected_observed.site_ids]
        )
        bank = likelihood.CompressedBank(
            selected_observed.site_ids,
            int(saved["bank_size"]),
            np.ascontiguousarray(saved["category_counts"][positions]),
            np.ascontiguousarray(saved["category_mass"][positions]),
            np.ascontiguousarray(saved["power_moments"][positions]),
            np.ascontiguousarray(raw[:, public_positions]),
            str(saved["bank_checksum"]),
            int(saved["series_order"]),
            float(saved["max_x"]),
        )
    series = prepare_site_likelihood(
        selected_observed, bank, 30.0, detection_sd=0.13
    )
    exact = prepare_site_likelihood(
        selected_observed, replace(bank, max_x=0.0), 30.0, detection_sd=0.13
    )
    rows = []
    for x in (150.0, 289.0):
        eta = np.full(len(selected_observed.site_ids), math.log(x / 290.0))
        series_result = series.evaluate(eta)
        exact_result = exact.evaluate(eta)
        rows.append(
            {
                "x": x,
                "eta": float(eta[0]),
                "max_abs_series_minus_exact": [
                    float(np.max(np.abs(series_result[index] - exact_result[index])))
                    for index in range(4)
                ],
            }
        )
    return rows


def main() -> None:
    bank, observed, site_a, public_ids = load_training()
    archived = json.loads(ARCHIVED.read_text(encoding="utf-8"))
    parameters = archived["cases"]["B_H3"]["fits"]["free_h"]["best"]["parameters"]
    effect = float(parameters["h"])
    detection_sd = float(parameters["detection_sd"])
    eta = float(parameters["alpha"]) + float(parameters["beta"]) * site_a

    started = time.perf_counter()
    series = prepare_site_likelihood(
        observed, bank, effect, detection_sd=detection_sd
    )
    series_preparation = time.perf_counter() - started
    started = time.perf_counter()
    series_result = series.evaluate(eta)
    series_times = [time.perf_counter() - started]
    last_eta = eta
    for index in range(1, 7):
        last_eta = eta + index * 1e-9
        started = time.perf_counter()
        series.evaluate(last_eta)
        series_times.append(time.perf_counter() - started)
    started = time.perf_counter()
    series.evaluate(last_eta.copy())
    series_cache_seconds = time.perf_counter() - started

    started = time.perf_counter()
    exact = prepare_site_likelihood(
        observed, replace(bank, max_x=0.0), effect, detection_sd=detection_sd
    )
    exact_preparation = time.perf_counter() - started
    exact_result, exact_times = time_call(lambda: exact.evaluate(eta), 1)
    assert exact_result is not None

    reference_result, reference_times = time_call(
        lambda: log_domain_likelihood.exact_log_scores(
            observed,
            bank,
            [effect],
            np.exp(eta),
            detection_sd=detection_sd,
        ).joint_loglikelihood[0, 0],
        1,
    )
    derivative_differences = [
        float(np.max(np.abs(series_result[index] - exact_result[index])))
        for index in range(1, 4)
    ]
    receipt = {
        "schema": "paper1-fast-differentiable-likelihood-kernel-v1",
        "status": "bounded_kernel_qualified",
        "generated_utc": datetime.now(UTC).isoformat(),
        "scope": (
            "one archived observed B_H3 training history and the known high-hazard site; "
            "not a profile, campaign, bank-precision certificate or inferential result"
        ),
        "runtime": {"python": sys.version, "platform": platform.platform()},
        "law": {
            "empirical_draws": int(bank.bank_size),
            "pseudo_arrivals": [float(value) for value in arc2b.PSEUDO_ARRIVALS],
            "denominator": int(bank.bank_size + arc2b.CATEGORY_COUNT),
            "category_rule": "searchsorted(canonical survey times, side=left)",
            "series_representation": "positive existing power-moment series",
            "unsupported_series_branch": "exact positive raw-arrival sum",
        },
        "b_h3_120_site": {
            "site_count": len(observed.site_ids),
            "effect": effect,
            "detection_sd": detection_sd,
            "eta_range": [float(np.min(eta)), float(np.max(eta))],
            "max_x": float(np.max(10.0 * np.exp(eta) * (effect - 1.0))),
            "series_preparation_seconds": series_preparation,
            "series_evaluation_seconds": series_times,
            "series_evaluation_median_seconds": float(np.median(series_times)),
            "series_exact_array_cache_seconds": series_cache_seconds,
            "exact_preparation_seconds": exact_preparation,
            "exact_evaluation_seconds": exact_times[0],
            "log_domain_value_reference_seconds": reference_times[0],
            "speedup_vs_exact_analytic": exact_times[0] / float(np.median(series_times)),
            "speedup_vs_log_domain_value_reference": reference_times[0]
            / float(np.median(series_times)),
            "max_abs_value_minus_log_domain_reference": float(
                np.max(np.abs(series_result[0] - reference_result))
            ),
            "max_abs_d1_d2_d3_minus_exact_analytic": derivative_differences,
            "series_stats": dict(series.stats),
            "exact_stats": dict(exact.stats),
        },
        "high_hazard_site": {
            "site_id": HIGH_SITE,
            "effect": 30.0,
            "detection_sd": 0.2013292938847899,
            "rows": high_hazard_rows(public_ids),
        },
        "high_x_series_roundoff": {
            "scope": "three actual B_H3 sites and order-816 actual bank moments",
            "tail_bound_scope": "series truncation only; excludes floating-point roundoff",
            "rows": high_x_roundoff(observed, public_ids),
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (
                MODULE,
                REFERENCE,
                TEST,
                RAW_BANK,
                COMPRESSED,
                ORDER816,
                OBSERVATIONS,
                DRIVER,
                SCRIPT,
                AUDITED_SNAPSHOT,
                INDEPENDENT_AUDIT,
            )
        },
    }
    receipt["acceptance"] = {
        "all_120_series": series.stats["series_site_evaluations"] >= 120,
        "all_120_exact_comparison": exact.stats["last_exact_site_count"] == 120,
        "value_error_le_1e_11": receipt["b_h3_120_site"][
            "max_abs_value_minus_log_domain_reference"
        ]
        <= 1e-11,
        "derivative_error_le_1e_10": max(derivative_differences) <= 1e-10,
        "high_hazard_error_le_1e_10": max(
            abs(row["minus_log_domain_reference"])
            for row in receipt["high_hazard_site"]["rows"]
        )
        <= 1e-10,
        "high_x_d3_roundoff_le_2e_minus_9": max(
            row["max_abs_series_minus_exact"][3]
            for row in receipt["high_x_series_roundoff"]["rows"]
        )
        <= 2e-9,
    }
    OUTPUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
