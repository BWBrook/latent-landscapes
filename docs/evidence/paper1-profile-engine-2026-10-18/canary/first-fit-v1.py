#!/usr/bin/env python3
"""Run the reviewed nested-grid canary for the unresolved high-h profile."""

from __future__ import annotations

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

from latent_landscapes.capstone_qualification import subset_bank, subset_observations

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PUBLIC = ROOT / "artifacts/goal060_execution/audit-repair/public_inputs"
OBSERVATIONS = (
    ROOT
    / "artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation"
    / "cell-09/rep-000/observations.npz"
)
OLD_BANK = HERE / "arrival-bank-order192.npz"
WIDE_BANK = HERE / "arrival-bank-order816-max290.npz"
BENCHMARK = HERE / "benchmark/B_H3-training120/receipt.json"
DRIVER_SOURCE = (
    HERE
    / "benchmark-executed-source/benchmark_spatial_profile-clean.py"
)
ENGINE_SOURCE = HERE / "benchmark-executed-source/spatial_profile.py"
LIKELIHOOD_SOURCE = ROOT / "src/latent_landscapes/preinvasion_likelihood.py"
OUTPUT = HERE / "wide-grid-canary.json"
UNDERFLOW_DIAGNOSTIC = HERE / "upper0-underflow-diagnostic.json"
OLD_GRID = np.linspace(-12.0, -2.0, 161)
STRESS_GRID = np.linspace(-14.0, 0.0, 225)
FIT_GRID = np.linspace(-14.0, -1.0, 209)
CANARY_H = (6.053483599717359, 30.0)


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


driver = load_module("profile_canary_driver", DRIVER_SOURCE)
engine = load_module("profile_canary_engine", ENGINE_SOURCE)


def finite(value: float) -> float | None:
    return float(value) if math.isfinite(float(value)) else None


def build_data(bank_path: Path) -> Any:
    public, exposure = driver.load_public_arrays(PUBLIC)
    observed, observation_ids = driver.load_observations(
        OBSERVATIONS,
        public=public,
        history=0,
    )
    site_a, rows, cols = driver._exposure_for_sites(
        public,
        exposure,
        observation_ids,
    )
    public_ids = driver._as_site_ids(public["site_ids"], name="public site_ids")
    bank, _, _ = driver.load_bank(
        raw_path=None,
        compressed_path=bank_path,
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
    covariance = driver.build_covariance(
        rows,
        cols,
        site_ids=observed.site_ids,
        range_cells=10.0,
    )
    return engine.SpatialProfileData(bank, observed, site_a, covariance)


def evaluation_summary(evaluation: Any, grid: np.ndarray) -> dict[str, Any]:
    mode = evaluation.mode
    result: dict[str, Any] = {
        "success": bool(evaluation.success),
        "message": str(evaluation.message),
        "criterion": finite(evaluation.criterion),
        "h": float(evaluation.h),
        "detection_sd": float(evaluation.detection_sd),
        "parameters": [float(value) for value in evaluation.parameters],
        "criterion_gradient": [finite(value) for value in evaluation.criterion_gradient],
    }
    if mode is None:
        result["mode"] = None
        return result
    result["mode"] = {
        "success": bool(mode.success),
        "message": str(mode.message),
        "score_inf": finite(mode.score_inf),
        "newton_step_inf": finite(mode.newton_step_inf),
        "newton_decrement": finite(mode.newton_decrement),
        "branch_count": int(mode.branch_count),
        "eta_min": float(np.min(mode.eta)),
        "eta_max": float(np.max(mode.eta)),
        "proposal_eta_min": finite(mode.proposal_eta_min),
        "proposal_eta_max": finite(mode.proposal_eta_max),
        "proposal_grid_supported": bool(mode.proposal_grid_supported),
        "lower_support_slack": finite(mode.proposal_eta_min - float(grid[0])),
        "upper_support_slack": finite(float(grid[-1]) - mode.proposal_eta_max),
        "bound_touch": bool(mode.bound_touch),
    }
    return result


def candidate_summary(candidate: Any, grid: np.ndarray) -> dict[str, Any]:
    return {
        "family": str(candidate.family),
        "source": str(candidate.source),
        "parameters": [float(value) for value in candidate.parameters],
        "eligible": bool(candidate.eligible),
        "optimizer_success": bool(candidate.optimizer_success),
        "optimizer_message": str(candidate.optimizer_message),
        "iterations": int(candidate.iterations),
        "evaluations": int(candidate.evaluations),
        "projected_gradient_inf": finite(candidate.projected_gradient_inf),
        "evaluation": evaluation_summary(candidate.evaluation, grid),
    }


def probability_headroom(
    criterion: Any,
    *,
    h: float,
    detection_sd: float,
) -> dict[str, Any]:
    integration = criterion._integrations(h)[-1]
    events, alive = criterion._prey_emissions(detection_sd)
    moments = integration.survival_moments
    weighted = np.einsum(
        "gstc,nsc->gnst",
        moments,
        criterion._predator_emissions,
        optimize=True,
    )
    probability = np.einsum(
        "gnst,nst->gns",
        weighted[:, :, :, :-1] - weighted[:, :, :, 1:],
        events,
        optimize=True,
    )
    probability += weighted[:, :, :, -1] * alive[None, :, :]
    positive = probability[np.isfinite(probability) & (probability > 0.0)]
    return {
        "h": h,
        "eta": float(criterion.grid[-1]),
        "x": 10.0 * math.exp(float(criterion.grid[-1])) * (h - 1.0),
        "detection_sd": detection_sd,
        "all_finite": bool(np.isfinite(probability).all()),
        "zero_count": int(np.count_nonzero(probability == 0.0)),
        "negative_count": int(np.count_nonzero(probability < 0.0)),
        "nonfinite_count": int(np.count_nonzero(~np.isfinite(probability))),
        "min_positive": None if not positive.size else float(np.min(positive)),
        "min_log_positive": None if not positive.size else float(np.log(np.min(positive))),
    }


def fd_headroom(criterion: Any, h: float, detection_sd: float) -> dict[str, Any]:
    return {
        label: probability_headroom(
            criterion,
            h=h,
            detection_sd=detection_sd + offset,
        )
        for label, offset in (("minus_sd", -1e-4), ("base", 0.0), ("plus_sd", 1e-4))
    }


def positive_start(row: dict[str, Any]) -> np.ndarray:
    p = row["parameters"]
    return np.asarray(
        [p["alpha"], p["beta"], p["log_sigma"], p["detection_sd"]],
        dtype=np.float64,
    )


def zero_start(row: dict[str, Any]) -> np.ndarray:
    p = row["parameters"]
    return np.asarray([p["alpha"], p["beta"], p["detection_sd"]], dtype=np.float64)


def select_starts(receipt: dict[str, Any], h: float) -> tuple[np.ndarray, np.ndarray]:
    positive = [
        row
        for row in receipt["profile"]["raw_start_receipts"]
        if row["family"] == "positive_sigma" and math.isclose(row["h"], h, rel_tol=1e-12)
    ]
    if not positive:
        raise RuntimeError(f"no recorded positive candidate at h={h}")
    positive_row = max(positive, key=lambda row: float(row["criterion"]))
    zero = [
        row
        for row in receipt["profile"]["grid_statuses"]
        if row["family"] == "sigma_zero"
        and row["status"] == "resolved"
        and math.isclose(row["h"], h, rel_tol=1e-12)
    ]
    if len(zero) != 1:
        raise RuntimeError(f"expected one recorded sigma-zero fit at h={h}")
    return positive_start(positive_row), zero_start(zero[0])


def fit_summary(fit: Any) -> dict[str, Any]:
    return {
        "resolved": bool(fit.resolved),
        "elapsed_seconds": float(fit.elapsed_seconds),
        "best_positive": None
        if fit.best_positive is None
        else candidate_summary(fit.best_positive, FIT_GRID),
        "best_sigma_zero": None
        if fit.best_sigma_zero is None
        else candidate_summary(fit.best_sigma_zero, FIT_GRID),
        "candidates": [candidate_summary(row, FIT_GRID) for row in fit.candidates],
    }


def main() -> None:
    benchmark = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    old_data = build_data(OLD_BANK)
    wide_data = build_data(WIDE_BANK)
    old = engine.SpatialProfileCriterion(old_data, grid=OLD_GRID)
    stress = engine.SpatialProfileCriterion(wide_data, grid=STRESS_GRID)
    fit_criterion = engine.SpatialProfileCriterion(wide_data, grid=FIT_GRID)

    free = benchmark["profile"]["best_positive"]["parameters"]
    free_point = np.asarray(
        [
            free["alpha"],
            free["beta"],
            free["log_sigma"],
            free["log_h"],
            free["detection_sd"],
        ],
        dtype=np.float64,
    )
    old_free = old.evaluate_positive(free_point, nuisance_fd=True)
    wide_free = stress.evaluate_positive(free_point, nuisance_fd=True)
    free_shift = float(wide_free.criterion - old_free.criterion)

    canaries: dict[str, Any] = {}
    for h in CANARY_H:
        p_start, z_start = select_starts(benchmark, h)
        old_base = old.evaluate_positive(p_start, fixed_h=h, nuisance_fd=False)
        old_fd = old.evaluate_positive(p_start, fixed_h=h, nuisance_fd=True)
        start_headroom = fd_headroom(fit_criterion, h, float(p_start[-1]))
        perturbations: dict[str, Any] = {}
        for label, offset in (("minus_sd", -1e-4), ("plus_sd", 1e-4)):
            point = p_start.copy()
            point[-1] += offset
            perturbations[label] = evaluation_summary(
                old.evaluate_positive(point, fixed_h=h, nuisance_fd=False),
                OLD_GRID,
            )
        started = time.perf_counter()
        fit = fit_criterion.fit_profile(
            fixed_h=h,
            positive_starts=(p_start,),
            sigma_zero_starts=(z_start,),
            kkt_tolerance=1e-3,
            maxiter=80,
        )
        wall_seconds = time.perf_counter() - started
        fit_record = fit_summary(fit)
        final_headroom = None
        if fit.best_positive is not None:
            final_headroom = fd_headroom(
                fit_criterion,
                h,
                float(fit.best_positive.evaluation.detection_sd),
            )
        canaries[f"h={h:.15g}"] = {
            "positive_start": p_start.tolist(),
            "sigma_zero_start": z_start.tolist(),
            "old_grid_base": evaluation_summary(old_base, OLD_GRID),
            "old_grid_ordinary_nuisance_fd": evaluation_summary(old_fd, OLD_GRID),
            "old_grid_sd_perturbations": perturbations,
            "fit_grid_start_probability_headroom": start_headroom,
            "fit_grid_final_probability_headroom": final_headroom,
            "fit_grid_fit_wall_seconds": wall_seconds,
            "fit_grid_fit": fit_record,
        }

    positive_best = [row["fit_grid_fit"]["best_positive"] for row in canaries.values()]
    fits_resolved = all(row["fit_grid_fit"]["resolved"] for row in canaries.values())
    positive_eligible = all(row is not None and row["eligible"] for row in positive_best)
    positive_kkt = all(
        row is not None
        and row["projected_gradient_inf"] is not None
        and row["projected_gradient_inf"] <= 1e-3
        for row in positive_best
    )
    positive_supported = all(
        row is not None
        and row["evaluation"]["mode"] is not None
        and row["evaluation"]["mode"]["proposal_grid_supported"]
        and row["evaluation"]["mode"]["upper_support_slack"] > 0.0
        and row["evaluation"]["mode"]["lower_support_slack"] > 0.0
        for row in positive_best
    )
    material_support_slack = all(
        row is not None
        and row["evaluation"]["mode"] is not None
        and row["evaluation"]["mode"]["upper_support_slack"] >= 0.25
        and row["evaluation"]["mode"]["lower_support_slack"] >= 0.25
        for row in positive_best
    )
    final_headroom_valid = all(
        row["fit_grid_final_probability_headroom"] is not None
        and all(
            diagnostic["all_finite"]
            and diagnostic["zero_count"] == 0
            and diagnostic["negative_count"] == 0
            and diagnostic["nonfinite_count"] == 0
            for diagnostic in row["fit_grid_final_probability_headroom"].values()
        )
        for row in canaries.values()
    )
    acceptance = {
        "old_free_point_success_on_both_grids": bool(old_free.success and wide_free.success),
        "old_free_abs_criterion_shift_le_1e-6": abs(free_shift) <= 1e-6,
        "h6_old_grid_fd_failure_reproduced": bool(
            not canaries["h=6.05348359971736"]["old_grid_ordinary_nuisance_fd"]["success"]
        ),
        "both_wide_grid_fits_resolved": fits_resolved,
        "both_positive_fits_eligible": positive_eligible,
        "both_positive_kkt_le_1e-3": positive_kkt,
        "both_positive_proposals_strictly_supported": positive_supported,
        "both_positive_proposals_have_ge_0.25_support_slack": material_support_slack,
        "final_base_and_nuisance_fd_probability_headroom_valid": final_headroom_valid,
    }
    receipt = {
        "schema": "paper1-wide-grid-canary-v1",
        "status": "passed" if all(acceptance.values()) else "diagnostic_complete",
        "scope": (
            "reviewed development canary only: nested-grid shift at the recorded free "
            "point and fixed-h fits at the first failed and maximum h; the [-14,0] "
            "stress-grid underflow is recorded separately; not a full profile"
        ),
        "interpretive_limit": (
            "Projected-gradient eligibility is evaluated together with ordinary central "
            "nuisance finite differences and proposal support. A pointwise projected "
            "gradient alone is not a smooth KKT certificate at or arbitrarily near a "
            "cubic-spline knot surface."
        ),
        "generated_utc": datetime.now(UTC).isoformat(),
        "grids": {
            "old": {"min": -12.0, "max": -2.0, "nodes": 161, "spacing": 0.0625},
            "stress": {"min": -14.0, "max": 0.0, "nodes": 225, "spacing": 0.0625},
            "fit": {"min": -14.0, "max": -1.0, "nodes": 209, "spacing": 0.0625},
        },
        "old_free_point": {
            "old_grid": evaluation_summary(old_free, OLD_GRID),
            "stress_grid": evaluation_summary(wide_free, STRESS_GRID),
            "criterion_shift_wide_minus_old": free_shift,
        },
        "canaries": canaries,
        "acceptance": acceptance,
        "inputs": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (
                OLD_BANK,
                WIDE_BANK,
                BENCHMARK,
                OBSERVATIONS,
                UNDERFLOW_DIAGNOSTIC,
            )
        },
        "sources": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (
                Path(__file__).resolve(),
                DRIVER_SOURCE,
                ENGINE_SOURCE,
                LIKELIHOOD_SOURCE,
            )
        },
    }
    OUTPUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "acceptance": acceptance}, indent=2))
    print(OUTPUT)


if __name__ == "__main__":
    main()
