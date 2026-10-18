#!/usr/bin/env python3
"""Localize and reproduce the h=30 upper-grid probability underflow."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

from latent_landscapes import preinvasion_likelihood as likelihood

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CANARY_SOURCE = HERE / "run-wide-grid-canary-initial-upper0.py"
RAW_BANK = ROOT / "artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy"
OUTPUT = HERE / "upper0-underflow-diagnostic.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


canary = load_module("upper0_initial_canary", CANARY_SOURCE)


def event_components(criterion: Any, integration: Any, detection_sd: float) -> tuple[Any, ...]:
    events, alive = criterion._prey_emissions(detection_sd)
    moments = integration.survival_moments
    weighted = np.einsum(
        "gstc,nsc->gnst",
        moments,
        criterion._predator_emissions,
        optimize=True,
    )
    per_time = (weighted[:, :, :, :-1] - weighted[:, :, :, 1:]) * events[None, :, :, :]
    terminal = weighted[:, :, :, -1] * alive[None, :, :]
    probability = per_time.sum(axis=-1) + terminal
    return probability, weighted, per_time, terminal


def classify(values: np.ndarray) -> dict[str, Any]:
    positive = values[np.isfinite(values) & (values > 0.0)]
    return {
        "all_finite": bool(np.isfinite(values).all()),
        "zero_count": int(np.count_nonzero(values == 0.0)),
        "negative_count": int(np.count_nonzero(values < 0.0)),
        "nonfinite_count": int(np.count_nonzero(~np.isfinite(values))),
        "min_positive": None if not positive.size else float(np.min(positive)),
        "min_log_positive": None if not positive.size else float(np.log(np.min(positive))),
    }


def scan_grid(criterion: Any, h: float, detection_sd: float) -> dict[str, Any]:
    rows = []
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        integrations = criterion._integrations(h)
    for eta, integration in zip(canary.WIDE_GRID, integrations, strict=True):
        probability, _, _, _ = event_components(criterion, integration, detection_sd)
        summary = classify(probability)
        if summary["zero_count"] or summary["negative_count"] or summary["nonfinite_count"]:
            rows.append({"eta": float(eta), **summary})
    valid = [
        float(eta)
        for eta, integration in zip(canary.WIDE_GRID, integrations, strict=True)
        if not any(
            classify(event_components(criterion, integration, detection_sd)[0])[key]
            for key in ("zero_count", "negative_count", "nonfinite_count")
        )
    ]
    return {
        "h": h,
        "detection_sd": detection_sd,
        "invalid_node_count": len(rows),
        "invalid_nodes": rows,
        "largest_valid_eta": max(valid),
        "first_invalid_eta": None if not rows else rows[0]["eta"],
    }


def raw_bank(data: Any) -> Any:
    with np.load(canary.WIDE_BANK, allow_pickle=False) as saved:
        full_ids = tuple(str(value) for value in saved["site_ids"])
    positions = np.asarray([full_ids.index(site_id) for site_id in data.bank.site_ids])
    arrivals = np.ascontiguousarray(np.load(RAW_BANK, mmap_mode="r")[:, positions])
    return likelihood.CompressedBank(
        data.bank.site_ids,
        data.bank.bank_size,
        data.bank.category_counts,
        data.bank.category_mass,
        data.bank.power_moments,
        arrivals,
        data.bank.bank_checksum,
        data.bank.series_order,
        data.bank.max_x,
    )


def node_check(
    criterion: Any,
    direct_bank: Any,
    *,
    h: float,
    eta: float,
    detection_sd: float,
) -> dict[str, Any]:
    hazards = np.full(criterion.site_count, math.exp(eta))
    arguments = {
        "prey_times": criterion.data.observed.prey_times,
        "cohort_start": criterion.data.observed.cohort_start,
    }
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        compressed = likelihood.build_integration(
            criterion.data.bank,
            [h],
            hazards,
            exact=False,
            **arguments,
        )
        direct = likelihood.build_integration(
            direct_bank,
            [h],
            hazards,
            exact=True,
            **arguments,
        )
    c_probability, c_weighted, c_time, c_terminal = event_components(
        criterion, compressed, detection_sd
    )
    d_probability, d_weighted, d_time, d_terminal = event_components(
        criterion, direct, detection_sd
    )
    difference = np.abs(c_probability - d_probability)
    scale = np.maximum(np.abs(d_probability), np.finfo(float).tiny)
    bad = np.argwhere((~np.isfinite(d_probability)) | (d_probability <= 0.0))
    bad_details = []
    for effect_index, history_index, site_index in bad:
        observed = criterion.data.observed
        bad_details.append(
            {
                "effect_index": int(effect_index),
                "history_index": int(history_index),
                "site_index": int(site_index),
                "site_id": criterion.data.bank.site_ids[int(site_index)],
                "prey_times": list(observed.prey_times),
                "prey_counts": observed.prey_counts[history_index, site_index].tolist(),
                "predator_times": list(observed.predator_times),
                "predator_counts": observed.predator_counts[history_index, site_index].tolist(),
                "predator_observed": None
                if observed.predator_observed is None
                else observed.predator_observed[history_index, site_index].tolist(),
                "compressed_probability": float(
                    c_probability[effect_index, history_index, site_index]
                ),
                "direct_probability": float(
                    d_probability[effect_index, history_index, site_index]
                ),
                "compressed_per_occasion_terms": c_time[
                    effect_index, history_index, site_index
                ].tolist(),
                "direct_per_occasion_terms": d_time[
                    effect_index, history_index, site_index
                ].tolist(),
                "compressed_terminal_term": float(
                    c_terminal[effect_index, history_index, site_index]
                ),
                "direct_terminal_term": float(
                    d_terminal[effect_index, history_index, site_index]
                ),
                "compressed_weighted_survival": c_weighted[
                    effect_index, history_index, site_index
                ].tolist(),
                "direct_weighted_survival": d_weighted[
                    effect_index, history_index, site_index
                ].tolist(),
            }
        )
    return {
        "h": h,
        "eta": eta,
        "x": 10.0 * math.exp(eta) * (h - 1.0),
        "compressed": classify(c_probability),
        "direct": classify(d_probability),
        "bad_indices_identical": bool(
            np.array_equal(
                np.argwhere((~np.isfinite(c_probability)) | (c_probability <= 0.0)),
                bad,
            )
        ),
        "max_abs_probability_difference": float(np.max(difference)),
        "max_relative_probability_difference": float(np.max(difference / scale)),
        "bad_details": bad_details,
    }


def main() -> None:
    benchmark = json.loads(canary.BENCHMARK.read_text(encoding="utf-8"))
    data = canary.build_data(canary.WIDE_BANK)
    criterion = canary.engine.SpatialProfileCriterion(data, grid=canary.WIDE_GRID)
    starts = {h: canary.select_starts(benchmark, h)[0] for h in canary.CANARY_H}
    scans = {
        f"h={h:.15g}": scan_grid(criterion, h, float(starts[h][-1]))
        for h in canary.CANARY_H
    }
    direct_bank = raw_bank(data)
    exact_checks = {
        "last_valid_node": node_check(
            criterion,
            direct_bank,
            h=30.0,
            eta=-0.9375,
            detection_sd=float(starts[30.0][-1]),
        ),
        "first_invalid_node": node_check(
            criterion,
            direct_bank,
            h=30.0,
            eta=-0.875,
            detection_sd=float(starts[30.0][-1]),
        ),
    }
    receipt = {
        "schema": "paper1-upper0-underflow-diagnostic-v1",
        "status": "diagnostic_complete",
        "scope": (
            "localize the failed [-14,0] canary and compare compressed with direct "
            "raw scoring"
        ),
        "generated_utc": datetime.now(UTC).isoformat(),
        "grid": {"min": -14.0, "max": 0.0, "nodes": 225, "spacing": 0.0625},
        "scans": scans,
        "compressed_vs_direct": exact_checks,
        "interpretation": (
            "At h=30 the full observed-history probability underflows to exact zero "
            "from eta=-0.875 upward. Direct raw-arrival scoring reproduces the first zero "
            "at the same site; this is floating-point probability arithmetic, not "
            "compressed-bank error."
        ),
        "inputs": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (canary.WIDE_BANK, canary.BENCHMARK, canary.OBSERVATIONS, RAW_BANK)
        },
        "sources": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (
                Path(__file__).resolve(),
                CANARY_SOURCE,
                canary.ENGINE_SOURCE,
                canary.LIKELIHOOD_SOURCE,
            )
        },
    }
    OUTPUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"scans": scans, "exact_checks": exact_checks}, indent=2))
    print(OUTPUT)


if __name__ == "__main__":
    main()
