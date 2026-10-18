#!/usr/bin/env python3
"""Run one reproducible development fit of the sampled-site spatial profile.

This driver is deliberately an observed-data adapter.  It reads the released
public map inputs, an arrival-bank representation, and one observation package;
it never opens evaluator or truth files.  The JSON receipt records compact
candidate and profile diagnostics rather than latent dense matrices.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import platform
import resource
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.spatial_profile import (
    DEFAULT_PROFILE_H_GRID,
    FitCandidate,
    ProfileFit,
    SpatialProfileCriterion,
    SpatialProfileData,
)


THREAD_ENVIRONMENT = ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_NUM_THREADS")
SCHEMA = "spatial-profile-benchmark-v1"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 of one input/source file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _read_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as values:
        return {key: np.array(values[key], copy=True) for key in values.files}


def _one_history(value: np.ndarray, name: str, history: int) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim == 2:
        if history != 0:
            raise IndexError(f"{name} contains one history; --history must be 0")
        return array[None, ...]
    if array.ndim != 3:
        raise ValueError(f"{name} must have shape (site, occasion) or (history, site, occasion)")
    if not 0 <= history < array.shape[0]:
        raise IndexError(f"history {history} is outside {name} with {array.shape[0]} histories")
    return np.asarray(array[history : history + 1])


def _one_history_mask(value: np.ndarray, history: int, *, name: str) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim == 2:
        if history != 0:
            raise IndexError(f"{name} contains one history; --history must be 0")
        return np.asarray(array[None, ...], dtype=bool)
    if array.ndim != 3:
        raise ValueError(f"{name} must have shape (site, occasion) or (history, site, occasion)")
    if not 0 <= history < array.shape[0]:
        raise IndexError(f"history {history} is outside {name}")
    return np.asarray(array[history : history + 1], dtype=bool)


def _align_site_metadata(
    value: np.ndarray | bool,
    *,
    observation_ids: Sequence[str],
    public_ids: Sequence[str],
    name: str,
) -> np.ndarray | bool:
    """Align optional site-valued metadata when a package is a public superset."""
    array = np.asarray(value)
    if array.ndim == 0 or len(observation_ids) == len(public_ids):
        return value
    if array.ndim == 1 and array.shape[0] == len(observation_ids):
        return value
    if array.ndim == 2 and (
        array.shape[0] == len(observation_ids) or array.shape[1] == len(observation_ids)
    ):
        return value
    if array.ndim == 3 and array.shape[1] == len(observation_ids):
        return value
    positions = _site_index(public_ids, observation_ids, name="public inputs")
    if array.ndim == 1 and array.shape[0] == len(public_ids):
        return array[positions]
    if array.ndim == 2 and array.shape[1] == len(public_ids):
        return array[:, positions]
    if array.ndim == 2 and array.shape[0] == len(public_ids):
        return array[positions]
    if array.ndim == 3 and array.shape[1] == len(public_ids):
        return array[:, positions]
    raise ValueError(f"{name} does not have a site dimension matching observations/public inputs")


def _as_site_ids(value: np.ndarray, *, name: str) -> tuple[str, ...]:
    ids = tuple(str(item) for item in np.asarray(value).reshape(-1))
    if not ids or any(not item for item in ids) or len(set(ids)) != len(ids):
        raise ValueError(f"{name} must contain unique nonempty site identifiers")
    return ids


def _site_index(
    source_ids: Sequence[str], requested_ids: Sequence[str], *, name: str
) -> np.ndarray:
    positions = {site_id: index for index, site_id in enumerate(source_ids)}
    missing = [site_id for site_id in requested_ids if site_id not in positions]
    if missing:
        raise ValueError(f"{name} is missing site identifiers: {missing[:5]}")
    return np.asarray([positions[site_id] for site_id in requested_ids], dtype=np.int64)


def _subset_bank(
    bank: likelihood.CompressedBank, positions: np.ndarray
) -> likelihood.CompressedBank:
    """Subset a bank by validated site positions without duplicating sites."""
    selected = np.asarray(positions, dtype=np.int64)
    ids = tuple(bank.site_ids[int(index)] for index in selected)
    if len(set(ids)) != len(ids):
        raise ValueError("bank site subsetting would duplicate site identifiers")
    return dataclasses.replace(
        bank,
        site_ids=ids,
        category_counts=np.ascontiguousarray(bank.category_counts[selected]),
        category_mass=np.ascontiguousarray(bank.category_mass[selected]),
        power_moments=np.ascontiguousarray(bank.power_moments[selected]),
        bank_arrivals=np.ascontiguousarray(bank.bank_arrivals[:, selected]),
        bank_checksum=bank.bank_checksum + ":sites:" + ",".join(str(int(i)) for i in selected),
    )


def load_public_arrays(input_dir: Path) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Load only ``public_inputs.npz`` and ``exposure.npz`` from input_dir."""
    public_path = input_dir / "public_inputs.npz"
    exposure_path = input_dir / "exposure.npz"
    if not public_path.is_file() or not exposure_path.is_file():
        raise FileNotFoundError(
            f"input directory must contain public_inputs.npz and exposure.npz: {input_dir}"
        )
    public = _read_npz(public_path)
    exposure = _read_npz(exposure_path)
    if "site_ids" not in public:
        raise ValueError("public_inputs.npz is missing site_ids")
    ids = _as_site_ids(public["site_ids"], name="public site_ids")
    if "site_a" not in exposure and "map_a" not in exposure:
        raise ValueError("exposure.npz must contain site_a or map_a")
    if "site_a" in exposure and np.asarray(exposure["site_a"]).shape != (len(ids),):
        raise ValueError("exposure site_a does not match public site count")
    return public, exposure


def _exposure_for_sites(
    public: Mapping[str, np.ndarray], exposure: Mapping[str, np.ndarray], site_ids: Sequence[str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    public_ids = _as_site_ids(public["site_ids"], name="public site_ids")
    positions = _site_index(public_ids, site_ids, name="public inputs")
    if "site_a" in exposure:
        site_a = np.asarray(exposure["site_a"], dtype=np.float64)[positions]
    else:
        if not {"map_a", "site_rows", "site_cols"}.issubset(public):
            raise ValueError("map_a exposure requires site_rows and site_cols in public inputs")
        rows = np.asarray(public["site_rows"], dtype=np.int64)[positions]
        cols = np.asarray(public["site_cols"], dtype=np.int64)[positions]
        map_a = np.asarray(exposure["map_a"], dtype=np.float64)
        site_a = map_a[rows, cols]
    if not np.isfinite(site_a).all():
        raise ValueError("site exposure contains nonfinite values")
    if not {"site_rows", "site_cols"}.issubset(public):
        raise ValueError("public inputs must contain site_rows and site_cols")
    rows = np.asarray(public["site_rows"], dtype=np.int64)[positions]
    cols = np.asarray(public["site_cols"], dtype=np.int64)[positions]
    return np.asarray(site_a, dtype=np.float64), rows, cols


def build_covariance(
    rows: np.ndarray,
    cols: np.ndarray,
    *,
    range_cells: float = 10.0,
    covariance_path: Path | None = None,
) -> np.ndarray:
    """Build the registered range-10 kernel or load an explicit covariance."""
    if covariance_path is not None:
        if covariance_path.suffix == ".npy":
            matrix = np.load(covariance_path, allow_pickle=False)
        else:
            values = _read_npz(covariance_path)
            key = (
                "covariance"
                if "covariance" in values
                else "matrix"
                if "matrix" in values
                else None
            )
            if key is None:
                raise ValueError("covariance NPZ must contain covariance or matrix")
            matrix = values[key]
        result = np.asarray(matrix, dtype=np.float64)
    else:
        if not math.isfinite(range_cells) or range_cells <= 0:
            raise ValueError("covariance range must be finite and positive")
        row_values = np.asarray(rows, dtype=np.float64)
        col_values = np.asarray(cols, dtype=np.float64)
        delta_rows = row_values[:, None] - row_values[None, :]
        delta_cols = col_values[:, None] - col_values[None, :]
        distance = np.hypot(delta_rows, delta_cols)
        result = np.exp(-distance / float(range_cells))
    if result.shape != (len(rows), len(rows)) or not np.isfinite(result).all():
        raise ValueError("covariance must be a finite square matrix matching selected sites")
    if not np.allclose(result, result.T, rtol=1e-12, atol=1e-12):
        raise ValueError("covariance must be symmetric")
    return np.ascontiguousarray(result)


def load_compressed_bank(path: Path) -> likelihood.CompressedBank:
    values = _read_npz(path)
    # Historical mechanical compressed banks intentionally omit raw arrivals;
    # the profile uses the compressed series path and therefore needs only a
    # correctly shaped empty placeholder for the exact-only field.
    required = {
        "site_ids",
        "bank_size",
        "category_counts",
        "category_mass",
        "power_moments",
        "bank_checksum",
    }
    missing = required.difference(values)
    if missing:
        raise ValueError(f"compressed bank is missing {sorted(missing)}")
    ids = _as_site_ids(values["site_ids"], name="bank site_ids")
    if "bank_arrivals" in values:
        arrivals = np.asarray(values["bank_arrivals"], dtype=np.float64)
        if arrivals.shape != (int(values["bank_size"]), len(ids)):
            raise ValueError(
                "compressed bank bank_arrivals shape does not match bank_size/site_ids"
            )
    else:
        arrivals = np.empty((0, len(ids)), dtype=np.float64)
    category_counts = np.asarray(values["category_counts"], dtype=np.int64)
    category_mass = np.asarray(values["category_mass"], dtype=np.float64)
    power_moments = np.asarray(values["power_moments"], dtype=np.float64)
    if category_counts.shape != (len(ids), 7) or category_mass.shape != (len(ids), 7):
        raise ValueError("compressed bank category arrays must have shape (site, 7)")
    if power_moments.ndim != 3 or power_moments.shape[:2] != (len(ids), 6):
        raise ValueError("compressed bank power_moments must have shape (site, 6, order+1)")
    series_order = int(np.asarray(values.get("series_order", likelihood.SERIES_ORDER)).item())
    max_x = float(np.asarray(values.get("max_x", likelihood.SERIES_DOMAIN)).item())
    if series_order < 0 or power_moments.shape[2] != series_order + 1:
        raise ValueError("compressed bank series_order does not match power_moments")
    if not math.isfinite(max_x) or max_x <= 0:
        raise ValueError("compressed bank max_x must be finite and positive")
    return likelihood.CompressedBank(
        ids,
        int(values["bank_size"]),
        category_counts,
        category_mass,
        power_moments,
        arrivals,
        str(np.asarray(values["bank_checksum"]).item()),
        series_order,
        max_x,
    )


def load_bank(
    *,
    raw_path: Path | None,
    compressed_path: Path | None,
    public_ids: Sequence[str],
    selected_ids: Sequence[str],
) -> tuple[likelihood.CompressedBank, Path, str]:
    if compressed_path is None and raw_path is None:
        raise ValueError("one of --arrival-bank or --compressed-bank is required")
    if compressed_path is not None:
        full = load_compressed_bank(compressed_path)
        positions = _site_index(full.site_ids, selected_ids, name="compressed bank")
        return _subset_bank(full, positions), compressed_path, "compressed"
    assert raw_path is not None
    raw = np.load(raw_path, mmap_mode="r", allow_pickle=False)
    if raw.ndim != 2 or raw.shape[1] != len(public_ids):
        raise ValueError(
            "raw arrival bank has no site metadata; its columns must match all public site_ids"
        )
    full = likelihood.compress_bank(raw, public_ids)
    positions = _site_index(tuple(public_ids), selected_ids, name="raw bank/public inputs")
    return _subset_bank(full, positions), raw_path, "raw"


def load_observations(
    path: Path,
    *,
    public: Mapping[str, np.ndarray],
    history: int,
) -> tuple[likelihood.PreInvasionObservations, tuple[str, ...]]:
    values = _read_npz(path)
    required = {"site_ids", "prey_counts", "predator_counts"}
    missing = required.difference(values)
    if missing:
        raise ValueError(f"observations.npz is missing {sorted(missing)}")
    ids = _as_site_ids(values["site_ids"], name="observation site_ids")
    public_ids = _as_site_ids(public["site_ids"], name="public site_ids")
    _site_index(public_ids, ids, name="public inputs")
    training = values.get("training_mask")
    if training is None:
        if "site_splits" not in public:
            raise ValueError("observations omit training_mask and public inputs omit site_splits")
        public_split = np.asarray(public["site_splits"]).astype(str)
        public_positions = _site_index(public_ids, ids, name="public inputs")
        training = public_split[public_positions] == "training"
    training = _align_site_metadata(
        training,
        observation_ids=ids,
        public_ids=public_ids,
        name="training_mask",
    )
    initial_alive = _align_site_metadata(
        values.get("initial_alive", True),
        observation_ids=ids,
        public_ids=public_ids,
        name="initial_alive",
    )
    predator_observed = values.get("predator_observed")
    if predator_observed is None:
        predator_observed = values.get("availability_mask", values.get("predator_available"))
    if predator_observed is not None:
        predator_observed = _align_site_metadata(
            predator_observed,
            observation_ids=ids,
            public_ids=public_ids,
            name="availability mask",
        )
    prey_times = values.get(
        "prey_times", values.get("prey_calendar", likelihood.DEFAULT_PREY_TIMES)
    )
    predator_times = values.get(
        "predator_times", values.get("predator_calendar", likelihood.DEFAULT_PREDATOR_TIMES)
    )
    predator_times = np.asarray(predator_times, dtype=np.float64).reshape(-1)
    canonical_predator_times = np.asarray(likelihood.DEFAULT_PREDATOR_TIMES, dtype=np.float64)
    if predator_times.shape != canonical_predator_times.shape or not np.array_equal(
        predator_times, canonical_predator_times
    ):
        raise ValueError(
            "benchmark driver requires the canonical six-occasion predator calendar "
            f"{tuple(canonical_predator_times)}; received {tuple(predator_times)}"
        )
    cohort_start = values.get("cohort_start", values.get("initial_cohort", -60.0))
    prey = _one_history(values["prey_counts"], "prey_counts", history)
    predator = _one_history(values["predator_counts"], "predator_counts", history)
    available = (
        None
        if predator_observed is None
        else _one_history_mask(predator_observed, history, name="availability mask")
    )
    observed = likelihood.prepare_observations(
        prey,
        predator,
        ids,
        training,
        initial_alive=initial_alive,
        prey_times=np.asarray(prey_times, dtype=np.float64).reshape(-1),
        predator_times=predator_times,
        cohort_start=float(np.asarray(cohort_start).item()),
        predator_observed=available,
    )
    return observed, ids


def _rss_bytes() -> dict[str, Any]:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if platform.system() == "Darwin":
        return {"value": value, "unit": "bytes"}
    return {"value": value * 1024, "unit": "bytes", "raw_unit": "KiB"}


def _git_identity(root: Path) -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--short"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "working_tree_changes": None}
    return {"commit": commit, "working_tree_changes": status}


def _parameter_names(candidate: FitCandidate) -> tuple[str, ...]:
    if candidate.family == "positive_sigma":
        if len(candidate.parameters) == 5:
            return ("alpha", "beta", "log_sigma", "log_h", "detection_sd")
        return ("alpha", "beta", "log_sigma", "detection_sd")
    if len(candidate.parameters) == 4:
        return ("alpha", "beta", "log_h", "detection_sd")
    return ("alpha", "beta", "detection_sd")


def _candidate_summary(
    candidate: FitCandidate, *, family_max: float, global_max: float
) -> dict[str, Any]:
    evaluation = candidate.evaluation
    mode = evaluation.mode
    return {
        "family": candidate.family,
        "source": candidate.source,
        "h": float(evaluation.h),
        "detection_sd": float(evaluation.detection_sd),
        "criterion": float(evaluation.criterion),
        "profile_lr_from_family_max": float(2.0 * (family_max - evaluation.criterion)),
        "profile_lr_from_global_max": float(2.0 * (global_max - evaluation.criterion)),
        "parameters": {
            name: float(value)
            for name, value in zip(_parameter_names(candidate), candidate.parameters, strict=True)
        },
        "optimizer_success": bool(candidate.optimizer_success),
        "evaluation_success": bool(evaluation.success),
        "eligible": bool(candidate.eligible),
        "optimizer_message": candidate.optimizer_message,
        "iterations": int(candidate.iterations),
        "evaluations": int(candidate.evaluations),
        "projected_gradient_inf": float(candidate.projected_gradient_inf),
        "mode": None
        if mode is None
        else {
            "success": bool(mode.success),
            "score_inf": float(mode.score_inf),
            "newton_step_inf": float(mode.newton_step_inf),
            "newton_decrement": float(mode.newton_decrement),
            "message": mode.message,
            "iterations": int(mode.iterations),
            "evaluations": int(mode.evaluations),
            "branch_count": int(mode.branch_count),
            "bound_touch": bool(mode.bound_touch),
            "proposal_grid_supported": bool(mode.proposal_grid_supported),
        },
    }


def _profile_summary(fit: ProfileFit, h_grid: Sequence[float]) -> dict[str, Any]:
    families = ("positive_sigma", "sigma_zero")
    family_candidates = {
        family: [row for row in fit.candidates if row.family == family]
        for family in families
    }
    # Fixed-h mesh rows are profile evidence and starts.  Only the explicit
    # free-h endpoint rows define the likelihood envelope used for LR values.
    endpoint_candidates = {
        family: [
            row
            for row in family_candidates[family]
            if fit.fixed_h is not None or str(row.source).startswith("free")
        ]
        for family in families
    }
    eligible = {
        family: [
            row
            for row in endpoint_candidates[family]
            if row.eligible and math.isfinite(row.evaluation.criterion)
        ]
        for family in families
    }
    family_max = {
        family: max(
            (row.evaluation.criterion for row in eligible[family]), default=-math.inf
        )
        for family in families
    }
    global_max = max(family_max.values(), default=-math.inf)
    envelope_tolerance = {
        family: (
            None
            if not math.isfinite(family_max[family])
            else 1e-8 * max(1.0, abs(family_max[family]))
        )
        for family in families
    }
    candidates = [
        _candidate_summary(
            row, family_max=family_max[row.family], global_max=global_max
        )
        for row in fit.candidates
    ]
    branch_counts = {
        family: [
            int(row["mode"]["branch_count"])
            for row in candidates
            if row["family"] == family and row["mode"] is not None
        ]
        for family in ("positive_sigma", "sigma_zero")
    }
    unresolved_above_envelope = []
    for row in fit.candidates:
        criterion = float(row.evaluation.criterion)
        tolerance = envelope_tolerance[row.family]
        unresolved = not (
            row.optimizer_success and row.evaluation.success and row.eligible
        )
        if unresolved and math.isfinite(criterion) and tolerance is not None:
            if criterion > family_max[row.family] + tolerance:
                unresolved_above_envelope.append(
                    {
                        "family": row.family,
                        "source": row.source,
                        "h": float(row.evaluation.h),
                        "criterion": criterion,
                        "eligible_envelope": float(family_max[row.family]),
                        "tolerance": float(tolerance),
                    }
                )

    fixed_above_free = []
    for family in families:
        if not math.isfinite(family_max[family]):
            continue
        for row in family_candidates[family]:
            if not str(row.source).startswith("profile_"):
                continue
            criterion = float(row.evaluation.criterion)
            if (
                row.eligible
                and row.optimizer_success
                and row.evaluation.success
                and math.isfinite(criterion)
                and criterion > family_max[family] + 1e-4
            ):
                fixed_above_free.append(
                    {
                        "family": family,
                        "source": row.source,
                        "h": float(row.evaluation.h),
                        "criterion": criterion,
                        "free_endpoint_envelope": float(family_max[family]),
                        "excess": float(criterion - family_max[family]),
                        "threshold": 1e-4,
                    }
                )

    def best_grid_candidate(family: str, h: float) -> FitCandidate | None:
        rows = [
            row
            for row in family_candidates[family]
            if str(row.source).startswith("profile_")
            and math.isclose(row.evaluation.h, h, rel_tol=0.0, abs_tol=1e-13)
            and row.eligible
            and row.evaluation.success
            and row.optimizer_success
            and math.isfinite(row.evaluation.criterion)
        ]
        return max(rows, key=lambda row: row.evaluation.criterion, default=None)

    grid_envelope_rows: list[dict[str, Any]] = []
    for h in h_grid:
        selected: dict[str, FitCandidate] = {}
        for family in families:
            row = best_grid_candidate(family, float(h))
            if row is not None:
                selected[family] = row
                summary = _candidate_summary(
                    row,
                    family_max=family_max[family],
                    global_max=global_max,
                )
                grid_envelope_rows.append(
                    {
                        "family": family,
                        "h": float(h),
                        "status": "resolved",
                        "source": row.source,
                        "criterion": summary["criterion"],
                        "profile_lr_from_family_max": summary[
                            "profile_lr_from_family_max"
                        ],
                        "profile_lr_from_global_max": summary[
                            "profile_lr_from_global_max"
                        ],
                        "profile_lr_from_h_envelope": None,
                        "parameters": summary["parameters"],
                        "branch_count": None
                        if summary["mode"] is None
                        else summary["mode"]["branch_count"],
                    }
                )
            else:
                grid_envelope_rows.append(
                    {
                        "family": family,
                        "h": float(h),
                        "status": "unresolved",
                        "source": None,
                        "criterion": None,
                        "profile_lr_from_family_max": None,
                        "profile_lr_from_global_max": None,
                        "profile_lr_from_h_envelope": None,
                        "parameters": None,
                        "branch_count": None,
                    }
                )
        if len(selected) == len(families):
            all_family = max(selected.values(), key=lambda row: row.evaluation.criterion)
            all_criterion = float(all_family.evaluation.criterion)
            grid_envelope_rows.append(
                {
                    "family": "all_families",
                    "h": float(h),
                    "status": "resolved",
                    "source": all_family.source,
                    "criterion": all_criterion,
                    "profile_lr_from_family_max": None,
                    "profile_lr_from_h_envelope": 0.0,
                    "profile_lr_from_global_max": float(2.0 * (global_max - all_criterion)),
                    "parameters": {
                        name: float(value)
                        for name, value in zip(
                            _parameter_names(all_family),
                            all_family.parameters,
                            strict=True,
                        )
                    },
                    "branch_count": None
                    if all_family.evaluation.mode is None
                    else int(all_family.evaluation.mode.branch_count),
                    "available_family_count": len(selected),
                    "available_envelope": True,
                    "diagnostic": False,
                    "complete": True,
                }
            )
        elif selected:
            all_criterion = float(
                max(
                    selected.values(), key=lambda row: row.evaluation.criterion
                ).evaluation.criterion
            )
            grid_envelope_rows.append(
                {
                    "family": "all_families",
                    "h": float(h),
                    "status": "partial",
                    "source": None,
                    "criterion": all_criterion,
                    "profile_lr_from_family_max": None,
                    "profile_lr_from_h_envelope": None,
                    "profile_lr_from_global_max": float(2.0 * (global_max - all_criterion)),
                    "parameters": None,
                    "branch_count": None,
                    "available_family_count": len(selected),
                    "available_envelope": True,
                    "diagnostic": True,
                    "complete": False,
                }
            )
        else:
            grid_envelope_rows.append(
                {
                    "family": "all_families",
                    "h": float(h),
                    "status": "unresolved",
                    "source": None,
                    "criterion": None,
                    "profile_lr_from_family_max": None,
                    "profile_lr_from_global_max": None,
                    "profile_lr_from_h_envelope": None,
                    "parameters": None,
                    "branch_count": None,
                    "available_family_count": 0,
                    "available_envelope": False,
                    "diagnostic": True,
                    "complete": False,
                }
            )

    best = (
        None
        if fit.best is None
        else _candidate_summary(
            fit.best, family_max=family_max[fit.best.family], global_max=global_max
        )
    )
    return {
        "profile_h_grid": [float(value) for value in h_grid],
        "h_grid": [float(value) for value in h_grid],
        "profile_h_grid_count": len(h_grid),
        "grid_statuses": grid_envelope_rows,
        "branches": branch_counts,
        "profile_lr": grid_envelope_rows,
        "candidate_count": len(candidates),
        "raw_start_receipts": candidates,
        "family_resolution": {
            family: {
                "resolved": bool(
                    fit.best_positive is not None
                    if family == "positive_sigma"
                    else fit.best_sigma_zero is not None
                ),
                "eligible_candidate_count": len(eligible[family]),
                "grid_points_resolved": sum(
                    row["family"] == family and row["status"] == "resolved"
                    for row in grid_envelope_rows
                ),
                "grid_points_requested": len(h_grid),
                "eligible_envelope": (
                    None
                    if not math.isfinite(family_max[family])
                    else float(family_max[family])
                ),
            }
            for family in families
        },
        "best": best,
        "best_positive": None
        if fit.best_positive is None
        else _candidate_summary(
            fit.best_positive,
            family_max=family_max["positive_sigma"],
            global_max=global_max,
        ),
        "best_sigma_zero": None
        if fit.best_sigma_zero is None
        else _candidate_summary(
            fit.best_sigma_zero,
            family_max=family_max["sigma_zero"],
            global_max=global_max,
        ),
        "endpoint_families_resolved": bool(fit.resolved),
        "eligible_envelope": {
            family: None if not math.isfinite(family_max[family]) else float(family_max[family])
            for family in families
        },
        "eligible_envelope_tolerance": envelope_tolerance,
        "unresolved_candidates_above_eligible_envelope": unresolved_above_envelope,
        "fixed_points_above_free_endpoint": fixed_above_free,
        "fixed_point_above_free_endpoint_flag": bool(fixed_above_free),
        "free_endpoint_dominates_retained_points": not fixed_above_free,
        "envelope_check_passed": not unresolved_above_envelope and not fixed_above_free,
        "elapsed_seconds": float(fit.elapsed_seconds),
    }


def run(args: argparse.Namespace) -> Path:
    started = time.perf_counter()
    root = Path(__file__).resolve().parents[1]
    output = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else (args.output_root / args.label).resolve()
    )
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output path: {output}")
    input_dir = args.input_dir.resolve()
    observations_path = args.observations.resolve()
    raw_path = None if args.arrival_bank is None else args.arrival_bank.resolve()
    compressed_path = None if args.compressed_bank is None else args.compressed_bank.resolve()
    covariance_path = None if args.covariance is None else args.covariance.resolve()
    if not observations_path.is_file():
        raise FileNotFoundError(observations_path)
    public, exposure = load_public_arrays(input_dir)
    public_ids = _as_site_ids(public["site_ids"], name="public site_ids")
    observed, observation_ids = load_observations(
        observations_path, public=public, history=args.history
    )
    selected_ids = tuple(observed.site_ids)
    full_input_site_count = len(selected_ids)
    site_a, rows, cols = _exposure_for_sites(public, exposure, selected_ids)
    bank, bank_path, bank_kind = load_bank(
        raw_path=raw_path,
        compressed_path=compressed_path,
        public_ids=public_ids,
        selected_ids=selected_ids,
    )
    if bank.site_ids != selected_ids or observed.site_ids != selected_ids:
        raise ValueError("bank and observations are not aligned on canonical site identifiers")

    # The spatial criterion is a training-site criterion.  Apply the shared
    # capstone subsetting helpers after all source arrays are aligned so that
    # optional predator-availability masks and the frozen calendar survive.
    from latent_landscapes.capstone_qualification import (
        subset_bank as subset_capstone_bank,
        subset_observations as subset_capstone_observations,
    )

    training_mask = np.asarray(observed.training_mask, dtype=bool)
    if not training_mask.any():
        raise ValueError("observation package has no training sites")
    training_site_count = int(training_mask.sum())
    if training_site_count != full_input_site_count:
        bank = subset_capstone_bank(bank, training_mask)
        observed = subset_capstone_observations(observed, training_mask)
        site_a = np.ascontiguousarray(site_a[training_mask])
        rows = np.ascontiguousarray(rows[training_mask])
        cols = np.ascontiguousarray(cols[training_mask])
    criterion_site_ids = tuple(observed.site_ids)

    kernel_started = time.perf_counter()
    covariance = build_covariance(
        rows,
        cols,
        range_cells=float(args.covariance_range),
        covariance_path=covariance_path,
    )
    criterion = SpatialProfileCriterion(
        SpatialProfileData(bank, observed, site_a, covariance)
    )
    kernel_seconds = time.perf_counter() - kernel_started
    h_grid = tuple(float(value) for value in np.geomspace(1.0, 30.0, args.profile_points))
    requested_x_max = 10.0 * math.exp(float(criterion.grid[-1])) * (max(h_grid) - 1.0)
    has_raw_arrivals = bank.bank_arrivals.shape[0] == bank.bank_size
    if requested_x_max > bank.max_x * (1.0 + 1e-14) and not has_raw_arrivals:
        raise ValueError(
            "compressed bank max_x does not cover the requested profile grid and omits "
            f"raw arrivals (requested x={requested_x_max:g}, max_x={bank.max_x:g})"
        )
    fit_started = time.perf_counter()
    fit = criterion.fit_profile(profile_h_grid=h_grid)
    fit_seconds = time.perf_counter() - fit_started

    output.mkdir(parents=True)
    source_paths = {
        "script": Path(__file__).resolve(),
        "spatial_profile_module": root / "src/latent_landscapes/spatial_profile.py",
        "preinvasion_likelihood_module": root / "src/latent_landscapes/preinvasion_likelihood.py",
        "capstone_qualification_module": root / "src/latent_landscapes/capstone_qualification.py",
        "public_inputs": input_dir / "public_inputs.npz",
        "exposure": input_dir / "exposure.npz",
        "observations": observations_path,
        "arrival_bank": bank_path,
    }
    if covariance_path is not None:
        source_paths["covariance"] = covariance_path
    bank_receipt = bank_path.with_name(f"{bank_path.stem}.json")
    if bank_receipt.is_file():
        source_paths["bank_receipt"] = bank_receipt
    bank_preparation = (
        root / "artifacts/paper1_profile_development_20261018/prepare-wide-series-bank.py"
    )
    if bank_receipt.is_file() and bank_preparation.is_file():
        source_paths["bank_preparation_script"] = bank_preparation
    source_identity = {
        str(key): {
            "path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
            "sha256": sha256_file(path),
        }
        for key, path in source_paths.items()
    }
    receipt = {
        "schema": SCHEMA,
        "status": "run_completed",
        "label": args.label,
        "development_only": True,
        "truth_accessed": False,
        "endpoint_families_resolved": bool(fit.resolved),
        "profile_certified": False,
        "source_identity": source_identity,
        "git": _git_identity(root),
        "inputs": {
            "site_count": full_input_site_count,
            "full_input_site_count": full_input_site_count,
            "training_site_count": training_site_count,
            "holdout_site_count": full_input_site_count - training_site_count,
            "criterion_site_count": len(criterion_site_ids),
            "site_ids_sha256": hashlib.sha256("\n".join(selected_ids).encode()).hexdigest(),
            "training_site_ids_sha256": hashlib.sha256(
                "\n".join(criterion_site_ids).encode()
            ).hexdigest(),
            "history_index": args.history,
            "prey_times": [float(value) for value in observed.prey_times],
            "predator_times": [float(value) for value in observed.predator_times],
            "cohort_start": float(observed.cohort_start),
            "observation_site_count": len(observation_ids),
            "bank_kind": bank_kind,
            "bank_size": int(bank.bank_size),
            "bank_checksum": bank.bank_checksum,
            "bank_series_order": int(bank.series_order),
            "bank_max_x": float(bank.max_x),
            "bank_has_raw_arrivals": has_raw_arrivals,
            "covariance": (
                "explicit" if covariance_path is not None else "exponential_grid_distance"
            ),
            "covariance_range_cells": float(args.covariance_range),
        },
        "integration_support": {
            "curve_grid_log_hazard_max": float(criterion.grid[-1]),
            "requested_x_max": float(requested_x_max),
            "compressed_series_supported": bool(requested_x_max <= bank.max_x * (1.0 + 1e-14)),
        },
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
            "threads": {name: os.environ.get(name) for name in THREAD_ENVIRONMENT},
            "single_thread_timing_contract": all(
                os.environ.get(name) == "1" for name in THREAD_ENVIRONMENT
            ),
        },
        "timing": {
            "load_seconds": float(kernel_started - started),
            "kernel_seconds": float(kernel_seconds),
            "fit_seconds": float(fit_seconds),
            "profile_seconds": float(fit.elapsed_seconds),
            "elapsed_seconds": float(time.perf_counter() - started),
        },
        "peak_rss": _rss_bytes(),
        "profile": _profile_summary(fit, h_grid),
        "criterion_stats": _jsonable(dict(criterion.stats)),
    }
    (output / "receipt.json").write_text(
        json.dumps(_jsonable(receipt), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return output


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        "--public-input-dir",
        "--public-inputs",
        dest="input_dir",
        type=Path,
        required=True,
    )
    parser.add_argument("--arrival-bank", type=Path)
    parser.add_argument("--compressed-bank", type=Path)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--label", default="development")
    parser.add_argument("--output-dir", "--output", dest="output_dir", type=Path)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/paper1_profile_development_20261018/benchmark"),
    )
    parser.add_argument(
        "--profile-points",
        "--profilepoints",
        dest="profile_points",
        type=int,
        default=len(DEFAULT_PROFILE_H_GRID),
    )
    parser.add_argument("--history", type=int, default=0)
    parser.add_argument("--covariance", type=Path)
    parser.add_argument("--covariance-range", type=float, default=10.0)
    args = parser.parse_args(argv)
    if args.output_dir is None and not args.label:
        parser.error("--label is required when --output-dir is omitted")
    if args.profile_points < 3:
        parser.error("--profile-points must be at least 3")
    if args.history < 0:
        parser.error("--history must be nonnegative")
    if args.arrival_bank is None and args.compressed_bank is None:
        parser.error("one of --arrival-bank or --compressed-bank is required")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output = run(args)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
