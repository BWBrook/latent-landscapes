#!/usr/bin/env python3
"""Check direct-kernel Laplace core gradients at bounded B_H3 incumbents."""

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
from latent_landscapes.differentiable_likelihood import prepare_site_likelihood
from latent_landscapes.spatial_profile import SpatialProfileCriterion, SpatialProfileData

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / "artifacts/goal060_execution/audit-repair/public_inputs"
RAW_BANK = ROOT / "artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy"
COMPRESSED = ROOT / "artifacts/paper1_profile_development_20261018/arrival-bank-order192.npz"
OBSERVATIONS = (
    ROOT
    / "artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation"
    / "cell-09/rep-000/observations.npz"
)
ARCHIVED = ROOT / "artifacts/paper1_planning_20261018/gp-prototype/results.json"
DRIVER = ROOT / "scripts/benchmark_spatial_profile.py"
MODULE = ROOT / "src/latent_landscapes/differentiable_likelihood.py"
SPATIAL = ROOT / "src/latent_landscapes/spatial_profile.py"
SCRIPT = Path(__file__).resolve()
OUTPUT = Path(__file__).with_name("laplace-gradient-receipt.json")


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


def load_data() -> SpatialProfileData:
    driver = load_module("laplace_gradient_benchmark_driver", DRIVER)
    public, exposure = driver.load_public_arrays(PUBLIC)
    observed, observation_ids = driver.load_observations(
        OBSERVATIONS, public=public, history=0
    )
    site_a, rows, cols = driver._exposure_for_sites(public, exposure, observation_ids)
    public_ids = driver._as_site_ids(public["site_ids"], name="public site ids")
    bank, _, _ = driver.load_bank(
        raw_path=RAW_BANK,
        compressed_path=COMPRESSED,
        public_ids=public_ids,
        selected_ids=observation_ids,
    )
    training = np.asarray(observed.training_mask, dtype=bool)
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
    return SpatialProfileData(bank, observed, site_a, covariance)


def check_effect(
    data: SpatialProfileData, parameters: dict[str, Any], effect: float
) -> dict[str, Any]:
    criterion = SpatialProfileCriterion(
        data,
        evaluator_factory=lambda h, sd: prepare_site_likelihood(
            data.observed, data.bank, h, detection_sd=sd
        ),
    )
    point = np.asarray(
        [
            float(parameters["alpha"]),
            float(parameters["beta"]),
            math.log(float(parameters["sigma"])),
            float(parameters["detection_sd"]),
        ]
    )
    started = time.perf_counter()
    base = criterion.evaluate_positive(point, fixed_h=effect)
    row: dict[str, Any] = {
        "effect": effect,
        "parameters": point.tolist(),
        "base_success": bool(base.success),
        "base_message": base.message,
        "base_seconds": time.perf_counter() - started,
        "criterion": float(base.criterion) if math.isfinite(base.criterion) else None,
        "analytic_core_gradient": base.criterion_gradient[:3].tolist(),
        "checks": [],
    }
    if not base.success or base.mode is None:
        return row
    row["mode"] = {
        "score_inf": float(base.mode.score_inf),
        "newton_step_inf": float(base.mode.newton_step_inf),
        "newton_decrement": float(base.mode.newton_decrement),
        "proposal_eta_min": float(base.mode.proposal_eta_min),
        "proposal_eta_max": float(base.mode.proposal_eta_max),
    }
    mode_start = base.mode.u
    names = ("alpha", "beta", "log_sigma")
    checks = []
    for coordinate, name in enumerate(names):
        analytic = float(base.criterion_gradient[coordinate])
        for step in (1e-4, 1e-5):
            plus = point.copy()
            minus = point.copy()
            plus[coordinate] += step
            minus[coordinate] -= step
            plus_result = criterion.evaluate_positive(
                plus, fixed_h=effect, mode_start=mode_start
            )
            minus_result = criterion.evaluate_positive(
                minus, fixed_h=effect, mode_start=mode_start
            )
            check = {
                "coordinate": name,
                "step": step,
                "plus_success": bool(plus_result.success),
                "minus_success": bool(minus_result.success),
                "plus_message": plus_result.message,
                "minus_message": minus_result.message,
            }
            if plus_result.success and minus_result.success:
                numerical = (plus_result.criterion - minus_result.criterion) / (2.0 * step)
                check.update(
                    {
                        "analytic": analytic,
                        "centered": float(numerical),
                        "centered_minus_analytic": float(numerical - analytic),
                    }
                )
            checks.append(check)
    row["checks"] = checks
    differences = [
        abs(float(check["centered_minus_analytic"]))
        for check in checks
        if "centered_minus_analytic" in check
    ]
    row["all_perturbations_successful"] = len(differences) == 6
    row["max_abs_centered_minus_analytic"] = max(differences, default=None)
    row["evaluator_stats"] = {
        "curve_builds": int(criterion.stats["curve_builds"]),
        "curve_seconds": float(criterion.stats["curve_seconds"]),
        "mode_calls": int(criterion.stats["mode_calls"]),
    }
    return row


def main() -> None:
    data = load_data()
    archived = json.loads(ARCHIVED.read_text(encoding="utf-8"))
    parameters = archived["cases"]["B_H3"]["fits"]["free_h"]["best"]["parameters"]
    rows = [check_effect(data, parameters, effect) for effect in (4.19158607954585, 6.05348, 30.0)]
    completed = [
        row
        for row in rows
        if row.get("all_perturbations_successful")
        and row.get("max_abs_centered_minus_analytic") is not None
    ]
    receipt = {
        "schema": "paper1-fast-likelihood-laplace-gradient-v1",
        "status": "bounded_gradient_replay_complete",
        "generated_utc": datetime.now(UTC).isoformat(),
        "scope": (
            "actual 120-site B_H3 observed history at archived incumbent nuisance/core "
            "parameters; three fixed effects; no fitting, profile or retuning"
        ),
        "site_count": len(data.observed.site_ids),
        "rows": rows,
        "summary": {
            "effects_requested": 3,
            "effects_with_complete_checks": len(completed),
            "max_abs_centered_minus_analytic": max(
                (float(row["max_abs_centered_minus_analytic"]) for row in completed),
                default=None,
            ),
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (
                MODULE,
                SPATIAL,
                DRIVER,
                RAW_BANK,
                COMPRESSED,
                OBSERVATIONS,
                ARCHIVED,
                SCRIPT,
            )
        },
    }
    OUTPUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
