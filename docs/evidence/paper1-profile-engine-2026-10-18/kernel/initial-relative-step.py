#!/usr/bin/env python3
"""Reproduce the bounded 120-site spatial-profile kernel checks.

This is development evidence, not a profile fit or qualification run.  It
uses archived observation history 000 for B_H3 and H3, evaluates only their
four stored endpoints, and times one B_H3 curve build.  It never opens truth
or evaluator arrays.
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import math
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.capstone_qualification import (
    subset_bank,
    subset_observations,
)
from latent_landscapes.spatial_profile import SpatialProfileCriterion, SpatialProfileData


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PUBLIC = ROOT / "artifacts/goal060_execution/audit-repair/public_inputs"
OBSERVATIONS = (
    ROOT / "artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation"
)
BANK = ROOT / "artifacts/paper1_profile_development_20261018/arrival-bank-order192.npz"
ARCHIVED = ROOT / "artifacts/paper1_planning_20261018/gp-prototype/results.json"
ENGINE_SOURCE = ROOT / "src/latent_landscapes/spatial_profile.py"
LIKELIHOOD_SOURCE = ROOT / "src/latent_landscapes/preinvasion_likelihood.py"
DRIVER_SOURCE = ROOT / "scripts/benchmark_spatial_profile.py"
PROTOTYPE_SOURCE = (
    ROOT / "artifacts/paper1_planning_20261018/gp-prototype/run_gp_prototype.py"
)
OUTPUT = HERE / "kernel-check.json"


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


driver = load_module("profile_benchmark_driver_check", DRIVER_SOURCE)
prototype = load_module("archived_gp_prototype_check", PROTOTYPE_SOURCE)


def load_case(case: str) -> tuple[SpatialProfileData, np.ndarray, Path]:
    public, exposure = driver.load_public_arrays(PUBLIC)
    cell = "cell-09" if case == "B_H3" else "cell-04"
    observation_path = OBSERVATIONS / cell / "rep-000/observations.npz"
    observed, observation_ids = driver.load_observations(
        observation_path,
        public=public,
        history=0,
    )
    site_a, rows, cols = driver._exposure_for_sites(public, exposure, observation_ids)
    public_ids = driver._as_site_ids(public["site_ids"], name="public site_ids")
    bank, _, _ = driver.load_bank(
        raw_path=None,
        compressed_path=BANK,
        public_ids=public_ids,
        selected_ids=observation_ids,
    )
    training = np.asarray(observed.training_mask, dtype=bool)
    if int(training.sum()) != 120:
        raise RuntimeError(f"expected 120 training sites, found {int(training.sum())}")
    bank = subset_bank(bank, training)
    observed = subset_observations(observed, training)
    site_a = np.ascontiguousarray(site_a[training])
    rows = np.ascontiguousarray(rows[training])
    cols = np.ascontiguousarray(cols[training])
    covariance = driver.build_covariance(rows, cols, range_cells=10.0)
    coords = np.column_stack((rows, cols)).astype(np.float64)
    return SpatialProfileData(bank, observed, site_a, covariance), coords, observation_path


def endpoint_point(record: dict[str, Any], fixed_h: float | None) -> tuple[np.ndarray, bool]:
    parameters = record["parameters"]
    sigma_zero = bool(record["sigma_zero"])
    values = [float(parameters["alpha"]), float(parameters["beta"])]
    if not sigma_zero:
        values.append(math.log(float(parameters["sigma"])))
    if fixed_h is None:
        values.append(math.log(float(parameters["h"])))
    values.append(float(parameters["detection_sd"]))
    return np.asarray(values, dtype=np.float64), sigma_zero


def evaluate_endpoint(
    criterion: SpatialProfileCriterion,
    point: np.ndarray,
    *,
    fixed_h: float | None,
    sigma_zero: bool,
) -> dict[str, Any]:
    evaluator = criterion.evaluate_sigma_zero if sigma_zero else criterion.evaluate_positive
    started = time.perf_counter()
    base = evaluator(point, fixed_h=fixed_h)
    cold_seconds = time.perf_counter() - started
    if not base.success:
        raise RuntimeError(base.message)
    core_count = 2 if sigma_zero else 3
    central = np.empty(len(point), dtype=np.float64)
    for index in range(len(point)):
        delta = 1e-4 * max(1.0, abs(float(point[index])))
        plus = point.copy()
        minus = point.copy()
        plus[index] += delta
        minus[index] -= delta
        if sigma_zero:
            vp = evaluator(plus, fixed_h=fixed_h).criterion
            vm = evaluator(minus, fixed_h=fixed_h).criterion
        else:
            mode_start = None if base.mode is None else base.mode.u
            vp = evaluator(plus, fixed_h=fixed_h, mode_start=mode_start).criterion
            vm = evaluator(minus, fixed_h=fixed_h, mode_start=mode_start).criterion
        if not (math.isfinite(vp) and math.isfinite(vm)):
            raise RuntimeError(f"finite-difference support failed at coordinate {index}")
        central[index] = (vp - vm) / (2.0 * delta)
    started = time.perf_counter()
    if sigma_zero:
        cached = evaluator(point, fixed_h=fixed_h)
    else:
        cached = evaluator(
            point,
            fixed_h=fixed_h,
            mode_start=None if base.mode is None else base.mode.u,
        )
    cached_seconds = time.perf_counter() - started
    mode = base.mode
    return {
        "criterion": float(base.criterion),
        "success": bool(base.success),
        "cold_endpoint_seconds": cold_seconds,
        "cached_endpoint_seconds": cached_seconds,
        "analytic_core_indices": list(range(core_count)),
        "analytic_core_gradient": base.criterion_gradient[:core_count].tolist(),
        "central_gradient_all_coordinates": central.tolist(),
        "max_abs_analytic_core_vs_central": float(
            np.max(np.abs(base.criterion_gradient[:core_count] - central[:core_count]))
        ),
        "mode": None
        if mode is None
        else {
            "raw_score_inf": float(mode.score_inf),
            "newton_step_inf": float(mode.newton_step_inf),
            "newton_decrement": float(mode.newton_decrement),
            "branch_count": int(mode.branch_count),
            "proposal_eta_min": float(mode.proposal_eta_min),
            "proposal_eta_max": float(mode.proposal_eta_max),
        },
    }


def scalar_vector_check(
    data: SpatialProfileData,
    coords: np.ndarray,
    *,
    h: float,
    detection_sd: float,
) -> dict[str, Any]:
    criterion = SpatialProfileCriterion(data)
    integrations_started = time.perf_counter()
    integrations = criterion._integrations(h)
    integrations_seconds = time.perf_counter() - integrations_started

    scalar_started = time.perf_counter()
    scalar = np.column_stack(
        [
            likelihood.score_observations(
                data.observed,
                integration,
                detection_sd=detection_sd,
            ).joint_loglikelihood[0, 0]
            for integration in integrations
        ]
    )
    scalar_seconds = time.perf_counter() - scalar_started
    vector_started = time.perf_counter()
    vector = criterion._score_integrations(integrations, detection_sd)
    vector_seconds = time.perf_counter() - vector_started

    fresh = SpatialProfileCriterion(data)
    new_started = time.perf_counter()
    new_curves = fresh.curves(h, detection_sd)
    new_cold_seconds = time.perf_counter() - new_started
    old_data = prototype.GPData(
        data.bank,
        data.observed,
        data.exposure,
        coords,
        data.covariance,
        "B_H3",
        len(data.exposure),
    )
    old_criterion = prototype.Criterion(old_data)
    old_started = time.perf_counter()
    old_curves = old_criterion.curves(h, detection_sd)
    old_cold_seconds = time.perf_counter() - old_started
    return {
        "grid_node_count": len(integrations),
        "site_count": len(data.exposure),
        "integration_build_seconds": integrations_seconds,
        "scalar_score_seconds": scalar_seconds,
        "vector_score_seconds": vector_seconds,
        "score_speedup": scalar_seconds / vector_seconds,
        "scalar_vector_max_abs_difference": float(np.max(np.abs(scalar - vector))),
        "new_cold_curve_seconds": new_cold_seconds,
        "archived_cold_curve_seconds": old_cold_seconds,
        "cold_curve_speedup": old_cold_seconds / new_cold_seconds,
        "archived_new_curve_max_abs_difference": float(
            np.max(np.abs(old_curves.values - new_curves.values))
        ),
        "timing_scope": (
            "local development timing for one B_H3 curve only; excludes endpoint fitting, "
            "profile traversal and the six-model analysis"
        ),
    }


def main() -> None:
    archived = json.loads(ARCHIVED.read_text(encoding="utf-8"))
    cases: dict[str, Any] = {}
    observation_paths: list[Path] = []
    loaded: dict[str, tuple[SpatialProfileData, np.ndarray]] = {}
    for case in ("B_H3", "H3"):
        data, coords, observation_path = load_case(case)
        loaded[case] = (data, coords)
        observation_paths.append(observation_path)
        criterion = SpatialProfileCriterion(data)
        endpoints: dict[str, Any] = {}
        for label, fixed_h in (("free_h", None), ("h1", 1.0)):
            archived_record = archived["cases"][case]["fits"][label]["best"]
            point, sigma_zero = endpoint_point(archived_record, fixed_h)
            result = evaluate_endpoint(
                criterion,
                point,
                fixed_h=fixed_h,
                sigma_zero=sigma_zero,
            )
            result.update(
                {
                    "family": "sigma_zero" if sigma_zero else "positive_sigma",
                    "parameters": point.tolist(),
                    "archived_criterion": float(archived_record["criterion"]),
                    "criterion_minus_archived": float(
                        result["criterion"] - float(archived_record["criterion"])
                    ),
                }
            )
            endpoints[label] = result
        cases[case] = {
            "site_count": len(data.exposure),
            "site_ids_sha256": hashlib.sha256(
                "\n".join(data.observed.site_ids).encode()
            ).hexdigest(),
            "endpoints": endpoints,
        }

    b_data, b_coords = loaded["B_H3"]
    b_record = archived["cases"]["B_H3"]["fits"]["free_h"]["best"]
    curve_check = scalar_vector_check(
        b_data,
        b_coords,
        h=float(b_record["parameters"]["h"]),
        detection_sd=float(b_record["parameters"]["detection_sd"]),
    )
    endpoint_rows = [
        endpoint
        for case in cases.values()
        for endpoint in case["endpoints"].values()
    ]
    receipt = {
        "schema": "paper1-spatial-profile-kernel-check-v1",
        "status": "passed",
        "scope": (
            "post-hoc development check on two archived history-000 cases and stored "
            "endpoints; no profile optimization or qualification inference"
        ),
        "generated_utc": datetime.now(UTC).isoformat(),
        "cases": cases,
        "curve_scoring": curve_check,
        "acceptance": {
            "all_four_endpoints_successful": all(row["success"] for row in endpoint_rows),
            "max_abs_criterion_minus_archived": max(
                abs(row["criterion_minus_archived"]) for row in endpoint_rows
            ),
            "max_abs_analytic_core_vs_central": max(
                row["max_abs_analytic_core_vs_central"] for row in endpoint_rows
            ),
            "scalar_vector_max_abs_difference": curve_check[
                "scalar_vector_max_abs_difference"
            ],
            "archived_new_curve_max_abs_difference": curve_check[
                "archived_new_curve_max_abs_difference"
            ],
        },
        "inputs": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in [
                PUBLIC / "public_inputs.npz",
                PUBLIC / "exposure.npz",
                BANK,
                ARCHIVED,
                *observation_paths,
            ]
        },
        "sources": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in [
                Path(__file__).resolve(),
                ENGINE_SOURCE,
                LIKELIHOOD_SOURCE,
                DRIVER_SOURCE,
                PROTOTYPE_SOURCE,
            ]
        },
    }
    OUTPUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt["acceptance"], indent=2, sort_keys=True))
    print(OUTPUT)


if __name__ == "__main__":
    main()
