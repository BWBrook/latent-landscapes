"""Synthesis for the registered Goal053 prospective background comparison.

The parent runner writes the metadata in ``evidence.npz`` and the four large
likelihood rectangles as separate NumPy files.  This module reads the latter
read-only (memory mapped), evaluates only the registered grid, and writes
descriptive estimation, prediction, geometry, and paired-bootstrap summaries.
It does not refit, redraw, or make per-history inferential claims.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.adjusted_background_synthesis import (
    BETAS,
    EFFECTS,
    _surface_metrics,
    maximum_on_grid,
)

FloatArray = NDArray[np.float64]

CELL_IDS = ("E0_h1", "E0_h3", "E06_h1", "E06_h3", "B100-A_h1", "B100-A_h3")
CELL_COUNT = len(CELL_IDS)
PRODUCTION_HISTORY_COUNT = 6000
PRODUCTION_BLOCK_COUNT = PRODUCTION_HISTORY_COUNT // CELL_COUNT
ORACLE_CELL_COUNT = 4
PRODUCTION_ORACLE_COUNT = 1000
PRODUCTION_ORACLE_BLOCK_COUNT = PRODUCTION_ORACLE_COUNT // ORACLE_CELL_COUNT
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 2026092703
POINT_ERROR_LOG_THRESHOLD = float(np.log(1.5))
ROUNDING_TOLERANCE = 1e-12
MODEL_TIE_TOLERANCE = 1e-12
SITE_COUNT = 160
MAP_SHAPE = (72, 84)
SCORE_FILES = {
    "latent_training": "latent_training.npy",
    "latent_holdout_joint": "latent_holdout_joint.npy",
    "oracle_training": "oracle_training.npy",
    "oracle_holdout": "oracle_holdout.npy",
}


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"cannot serialize {type(value)!r}")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _required(values: Mapping[str, Any], name: str) -> Any:
    if name not in values:
        raise ValueError(f"evidence metadata is missing required array: {name}")
    return values[name]


def _as_strings(values: Any, name: str) -> NDArray[np.str_]:
    array = np.asarray(values)
    if array.ndim != 1 or array.dtype.kind not in "SU":
        raise ValueError(f"{name} must be a one-dimensional string array")
    return array.astype(str)


def expected_score_shapes(history_count: int) -> dict[str, tuple[int, int, int]]:
    """Return score shapes for a metadata panel, useful for small unit fixtures."""
    if history_count < CELL_COUNT or history_count % CELL_COUNT:
        raise ValueError("history_count must be a positive multiple of six")
    oracle_blocks = min(history_count // CELL_COUNT, PRODUCTION_ORACLE_BLOCK_COUNT)
    oracle_count = oracle_blocks * ORACLE_CELL_COUNT
    return {
        "latent_training": (history_count, len(BETAS), len(EFFECTS)),
        "latent_holdout_joint": (history_count, len(BETAS), len(EFFECTS)),
        "oracle_training": (oracle_count, len(BETAS), len(EFFECTS)),
        "oracle_holdout": (oracle_count, len(BETAS), len(EFFECTS)),
    }


def validate_metadata(values: Mapping[str, Any], *, strict: bool = True) -> dict[str, Any]:
    """Validate frozen metadata and return its dimensions.

    ``strict=True`` is used by production and requires the registered 6,000 /
    1,000-history shapes.  ``strict=False`` deliberately validates the same
    ordering and invariants for a smaller six-cell test panel.
    """
    effects = np.asarray(_required(values, "effects"), dtype=np.float64)
    betas = np.asarray(_required(values, "betas"), dtype=np.float64)
    if effects.shape != EFFECTS.shape or not np.array_equal(effects, EFFECTS):
        raise ValueError("metadata effects do not match the frozen h grid")
    if betas.shape != BETAS.shape or not np.array_equal(betas, BETAS):
        raise ValueError("metadata betas do not match the frozen beta grid")

    cell_ids = _as_strings(_required(values, "cell_ids"), "cell_ids")
    n_histories = len(cell_ids)
    if n_histories < CELL_COUNT or n_histories % CELL_COUNT:
        raise ValueError("cell_ids must contain complete six-cell blocks")
    blocks = n_histories // CELL_COUNT
    if strict and n_histories != PRODUCTION_HISTORY_COUNT:
        raise ValueError("production metadata must contain exactly 6,000 histories")
    expected_cells = np.tile(np.asarray(CELL_IDS), blocks)
    if not np.array_equal(cell_ids, expected_cells):
        raise ValueError("cell_ids do not follow the frozen block-major six-cell order")

    replicate_indices = np.asarray(_required(values, "replicate_indices"))
    if replicate_indices.shape != (n_histories,) or not np.array_equal(
        replicate_indices, np.repeat(np.arange(blocks), CELL_COUNT)
    ):
        raise ValueError("replicate_indices do not match block-major history order")
    truth_h = np.asarray(_required(values, "truth_h"), dtype=np.float64)
    truth_beta = np.asarray(_required(values, "truth_beta"), dtype=np.float64)
    if truth_h.shape != (n_histories,) or truth_beta.shape != (n_histories,):
        raise ValueError("truth arrays must contain one value per history")
    expected_h = np.tile(np.asarray((1.0, 3.0, 1.0, 3.0, 1.0, 3.0)), blocks)
    expected_beta = np.tile(np.asarray((0.0, 0.0, 0.6, 0.6, np.nan, np.nan)), blocks)
    if not np.array_equal(
        np.nan_to_num(truth_h, nan=-999.0), np.nan_to_num(expected_h, nan=-999.0)
    ):
        raise ValueError("truth_h values do not match the registered six-cell design")
    if not np.array_equal(
        np.nan_to_num(truth_beta, nan=-999.0), np.nan_to_num(expected_beta, nan=-999.0)
    ):
        raise ValueError("truth_beta values do not match the registered exact-cell design")
    if not np.isnan(truth_beta[4::6]).all():
        raise ValueError("B100-A cells must have unknown truth beta")
    opaque_ids = _as_strings(_required(values, "opaque_ids"), "opaque_ids")
    if (
        opaque_ids.shape != (n_histories,)
        or not np.all(opaque_ids)
        or len(np.unique(opaque_ids)) != n_histories
    ):
        raise ValueError("opaque_ids must be nonempty and unique")

    oracle_indices = np.asarray(_required(values, "oracle_history_indices"))
    oracle_blocks = min(blocks, PRODUCTION_ORACLE_BLOCK_COUNT)
    expected_oracle = (
        np.arange(oracle_blocks)[:, None] * CELL_COUNT + np.arange(ORACLE_CELL_COUNT)
    ).ravel()
    if oracle_indices.shape != expected_oracle.shape or not np.array_equal(
        oracle_indices, expected_oracle
    ):
        raise ValueError("oracle_history_indices must select the first four cells of every block")
    if strict and len(oracle_indices) != PRODUCTION_ORACLE_COUNT:
        raise ValueError("production metadata must contain exactly 1,000 oracle histories")

    site_ids = _as_strings(_required(values, "site_ids"), "site_ids")
    n_sites = len(site_ids)
    if n_sites < 2 or len(np.unique(site_ids)) != n_sites or not np.all(site_ids):
        raise ValueError("site_ids must be nonempty and unique")
    if strict and n_sites != SITE_COUNT:
        raise ValueError("production metadata must contain exactly 160 sites")
    training_mask = np.asarray(_required(values, "training_mask"), dtype=bool)
    if training_mask.shape != (n_sites,) or training_mask.all() or (~training_mask).all():
        raise ValueError("training_mask must split sites into training and holdout")
    if strict and int(training_mask.sum()) != 120:
        raise ValueError("production training_mask must contain 120 training sites")
    site_a = np.asarray(_required(values, "site_A"), dtype=np.float64)
    map_a = np.asarray(_required(values, "map_A"), dtype=np.float64)
    if site_a.shape != (n_sites,) or not np.isfinite(site_a).all():
        raise ValueError("site_A must be finite and match site_ids")
    if map_a.ndim != 2 or not np.isfinite(map_a).all() or (strict and map_a.shape != MAP_SHAPE):
        raise ValueError("map_A must be a finite two-dimensional complete map")

    for name in ("true_arrival", "true_extirpation", "true_hazards"):
        array = np.asarray(_required(values, name), dtype=np.float64)
        expected_shape = (n_histories, n_sites)
        if array.shape != expected_shape or not np.isfinite(array).all():
            raise ValueError(f"{name} must have shape {expected_shape} and finite values")
    for name in ("predator_counts", "prey_counts"):
        array = np.asarray(_required(values, name))
        if array.shape != (n_histories, n_sites, 6) or not np.isfinite(array).all():
            raise ValueError(f"{name} must have one six-occasion row per history and site")
    predator = np.asarray(_required(values, "latent_holdout_predator"), dtype=np.float64)
    if predator.shape != (n_histories,) or not np.isfinite(predator).all():
        raise ValueError("latent_holdout_predator must contain one finite value per history")
    return {
        "history_count": n_histories,
        "block_count": blocks,
        "oracle_count": len(oracle_indices),
        "oracle_block_count": oracle_blocks,
        "site_count": n_sites,
    }


def _load_bundle(
    input_dir: Path, *, strict: bool
) -> tuple[dict[str, NDArray[Any]], dict[str, np.ndarray], dict[str, str]]:
    metadata_path = input_dir / "evidence.npz"
    if not metadata_path.is_file():
        raise ValueError(f"missing metadata bundle: {metadata_path}")
    with np.load(metadata_path, allow_pickle=False) as loaded:
        metadata = {name: np.asarray(loaded[name]).copy() for name in loaded.files}
    dimensions = validate_metadata(metadata, strict=strict)
    score_arrays: dict[str, np.ndarray] = {}
    input_hashes = {metadata_path.name: _sha256(metadata_path)}
    for name, filename in SCORE_FILES.items():
        path = input_dir / filename
        if not path.is_file():
            raise ValueError(f"missing score array: {path}")
        score = np.load(path, mmap_mode="r", allow_pickle=False)
        expected = (dimensions["history_count"], len(BETAS), len(EFFECTS))
        if name.startswith("oracle"):
            expected = (dimensions["oracle_count"], len(BETAS), len(EFFECTS))
        if score.shape != expected or score.dtype != np.dtype("float64"):
            raise ValueError(
                f"{filename} has shape/dtype {score.shape}/{score.dtype}; "
                f"expected {expected}/float64"
            )
        if not np.isfinite(score).all():
            raise ValueError(f"{filename} contains non-finite likelihood values")
        score_arrays[name] = score
        input_hashes[filename] = _sha256(path)
    metadata["_dimensions"] = np.asarray([dimensions["history_count"], dimensions["oracle_count"]])
    return metadata, score_arrays, input_hashes


def _known_beta_fit(surface: FloatArray, truth_beta: float) -> tuple[float, float, int, int]:
    beta_index = int(np.argmin(np.abs(BETAS - truth_beta)))
    if abs(float(BETAS[beta_index]) - truth_beta) > ROUNDING_TOLERANCE:
        raise ValueError(f"known truth beta {truth_beta} is not on the registered grid")
    fit = maximum_on_grid(surface[beta_index][None, :], np.asarray([truth_beta]), EFFECTS)
    return fit.h, fit.value, beta_index, fit.h_index


def _metric_row(
    training: FloatArray,
    holdout: FloatArray,
    *,
    history_index: int,
    block_index: int,
    cell_id: str,
    truth_h: float,
    truth_beta: float,
    lane: str,
    score_denominator: float = 40.0,
) -> dict[str, Any]:
    metrics = _surface_metrics(training, holdout)
    fit_h = float(metrics["fit_h"])
    constant_h = float(metrics["constant_fit_h"])
    fit = maximum_on_grid(training)
    beta_zero_index = int(np.flatnonzero(BETAS == 0.0)[0])
    constant_h_index = int(np.argmin(np.abs(EFFECTS - constant_h)))
    direct_score_nats = float(holdout[fit.beta_index, fit.h_index]) - float(
        holdout[beta_zero_index, constant_h_index]
    )
    direct_score = direct_score_nats / score_denominator
    adjusted_null_score = (
        float(metrics["holdout_adjusted_minus_fitted_adjustednull_conditional_prey"])
        / score_denominator
    )
    adjusted_log_error = float(np.log(fit_h / truth_h)) if np.isfinite(truth_h) else None
    constant_log_error = float(np.log(constant_h / truth_h)) if np.isfinite(truth_h) else None
    known_h: float | None = None
    known_log_error: float | None = None
    known_beta_fit_value: float | None = None
    if np.isfinite(truth_beta) and np.isfinite(truth_h):
        known_h, known_beta_fit_value, _known_beta_index, _known_h_index = _known_beta_fit(
            training, truth_beta
        )
        known_log_error = float(np.log(known_h / truth_h))
    row: dict[str, Any] = {
        "history_index": history_index,
        "block_index": block_index,
        "cell_id": cell_id,
        "lane": lane,
        "truth_h": truth_h if np.isfinite(truth_h) else None,
        "truth_beta": truth_beta if np.isfinite(truth_beta) else None,
        "fit_h": fit_h,
        "fit_beta": float(metrics["fit_beta"]),
        "constant_fit_h": constant_h,
        "known_beta_fit_h": known_h,
        "known_beta_fit_value": known_beta_fit_value,
        "signed_log_h_error_adjusted": adjusted_log_error,
        "signed_log_h_error_constant": constant_log_error,
        "signed_log_h_error_known_beta": known_log_error,
        "signed_log_h_error_adjusted_minus_known_beta": (
            adjusted_log_error - known_log_error
            if adjusted_log_error is not None and known_log_error is not None
            else None
        ),
        "abs_log_h_error_adjusted": abs(adjusted_log_error)
        if adjusted_log_error is not None
        else None,
        "abs_log_h_error_constant": abs(constant_log_error)
        if constant_log_error is not None
        else None,
        "abs_log_h_error_known_beta": abs(known_log_error) if known_log_error is not None else None,
        "squared_log_h_error_adjusted": (
            adjusted_log_error**2 if adjusted_log_error is not None else None
        ),
        "squared_log_h_error_known_beta": (
            known_log_error**2 if known_log_error is not None else None
        ),
        "abs_log_h_error_change_adjusted_minus_constant": (
            abs(adjusted_log_error) - abs(constant_log_error)
            if adjusted_log_error is not None and constant_log_error is not None
            else None
        ),
        "direct_holdout_score_adjusted_minus_constant_nats": direct_score_nats,
        "direct_holdout_score_adjusted_minus_constant_per_site": direct_score,
        "adjusted_minus_adjusted_null_holdout_score_per_site": adjusted_null_score,
        "point_error_1_5fold_adjusted": (
            abs(adjusted_log_error) >= POINT_ERROR_LOG_THRESHOLD - ROUNDING_TOLERANCE
            if adjusted_log_error is not None
            else None
        ),
        "point_error_1_5fold_constant": (
            abs(constant_log_error) >= POINT_ERROR_LOG_THRESHOLD - ROUNDING_TOLERANCE
            if constant_log_error is not None
            else None
        ),
        "point_error_1_5fold_known_beta": (
            abs(known_log_error) >= POINT_ERROR_LOG_THRESHOLD - ROUNDING_TOLERANCE
            if known_log_error is not None
            else None
        ),
        "beta_error": (
            float(metrics["fit_beta"]) - truth_beta if np.isfinite(truth_beta) else None
        ),
        "abs_beta_error": (
            abs(float(metrics["fit_beta"]) - truth_beta) if np.isfinite(truth_beta) else None
        ),
        "direct_score_preference": (
            "adjusted"
            if direct_score_nats > MODEL_TIE_TOLERANCE
            else "constant"
            if direct_score_nats < -MODEL_TIE_TOLERANCE
            else "tie"
        ),
        "profile_interpretation": (
            "UNCALIBRATED LR<=2 likelihood geometry; not a confidence interval"
        ),
    }
    row.update(metrics)
    return row


def _rows_for_lane(
    metadata: Mapping[str, Any], scores: Mapping[str, np.ndarray], lane: str
) -> list[dict[str, Any]]:
    if lane == "latent":
        indices = np.arange(len(metadata["cell_ids"]), dtype=int)
        training = scores["latent_training"]
        holdout = scores["latent_holdout_joint"]
    else:
        indices = np.asarray(metadata["oracle_history_indices"], dtype=int)
        training = scores["oracle_training"]
        holdout = scores["oracle_holdout"]
    cell_ids = np.asarray(metadata["cell_ids"]).astype(str)
    replicate_indices = np.asarray(metadata["replicate_indices"], dtype=int)
    truth_h = np.asarray(metadata["truth_h"], dtype=np.float64)
    truth_beta = np.asarray(metadata["truth_beta"], dtype=np.float64)
    rows: list[dict[str, Any]] = []
    for score_index, history_index in enumerate(indices):
        rows.append(
            _metric_row(
                training[score_index],
                holdout[score_index],
                history_index=int(history_index),
                block_index=int(replicate_indices[history_index]),
                cell_id=str(cell_ids[history_index]),
                truth_h=float(truth_h[history_index]),
                truth_beta=float(truth_beta[history_index]),
                lane=lane,
            )
        )
    return rows


def _mean(values: Sequence[Any]) -> float:
    array = np.asarray([value for value in values if value is not None], dtype=np.float64)
    return float(array.mean()) if array.size else math.nan


def _cell_summary(
    rows: Sequence[Mapping[str, Any]],
    *,
    bootstrap: Mapping[tuple[str, str], Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    present_cells = tuple(dict.fromkeys(str(row["cell_id"]) for row in rows))
    for cell_id in present_cells:
        subset = [row for row in rows if row["cell_id"] == cell_id]
        result: dict[str, Any] = {
            "cell_id": cell_id,
            "lane": str(subset[0]["lane"]),
            "n_histories": len(subset),
        }
        for name in (
            "fit_h",
            "fit_beta",
            "constant_fit_h",
            "known_beta_fit_h",
            "signed_log_h_error_adjusted",
            "signed_log_h_error_constant",
            "signed_log_h_error_known_beta",
            "abs_log_h_error_adjusted",
            "abs_log_h_error_constant",
            "abs_log_h_error_known_beta",
            "abs_log_h_error_change_adjusted_minus_constant",
            "direct_holdout_score_adjusted_minus_constant_per_site",
            "adjusted_minus_adjusted_null_holdout_score_per_site",
            "beta_error",
            "abs_beta_error",
        ):
            result[f"{name}_mean"] = _mean([row[name] for row in subset])
        for estimator in ("adjusted", "constant", "known_beta"):
            values = [row[f"signed_log_h_error_{estimator}"] for row in subset]
            finite = [value for value in values if value is not None]
            result[f"rmse_log_h_error_{estimator}"] = (
                float(np.sqrt(np.mean(np.square(finite)))) if finite else math.nan
            )
        result["point_error_1_5fold_adjusted_count"] = int(
            sum(
                bool(row["point_error_1_5fold_adjusted"])
                for row in subset
                if row["point_error_1_5fold_adjusted"] is not None
            )
        )
        result["point_error_1_5fold_adjusted_rate"] = result[
            "point_error_1_5fold_adjusted_count"
        ] / len(subset)
        for estimator in ("constant", "known_beta"):
            key = f"point_error_1_5fold_{estimator}"
            available = [row[key] for row in subset if row[key] is not None]
            result[f"{key}_count"] = int(sum(bool(value) for value in available))
            result[f"{key}_rate"] = (
                result[f"{key}_count"] / len(available) if available else math.nan
            )
        result["direct_score_adjusted_wins"] = int(
            sum(row["direct_score_preference"] == "adjusted" for row in subset)
        )
        result["direct_score_constant_wins"] = int(
            sum(row["direct_score_preference"] == "constant" for row in subset)
        )
        result["direct_score_ties"] = int(
            sum(row["direct_score_preference"] == "tie" for row in subset)
        )
        result["direct_score_adjusted_win_rate_excluding_ties"] = (
            result["direct_score_adjusted_wins"]
            / (result["direct_score_adjusted_wins"] + result["direct_score_constant_wins"])
            if result["direct_score_adjusted_wins"] + result["direct_score_constant_wins"]
            else math.nan
        )
        for prefix in ("fit_", "coarse_fit_"):
            for edge in ("beta_lower_edge", "beta_upper_edge", "h_lower_edge", "h_upper_edge"):
                key = f"{prefix}{edge}"
                if key in subset[0]:
                    result[f"{key}_count"] = int(sum(bool(row[key]) for row in subset))
        result["resolution_sensitive_count"] = int(
            sum(bool(row["resolution_sensitive"]) for row in subset)
        )
        result["h_profile_touches_lower_count"] = int(
            sum(bool(row["h_profile_touches_lower"]) for row in subset)
        )
        result["h_profile_touches_upper_count"] = int(
            sum(bool(row["h_profile_touches_upper"]) for row in subset)
        )
        output.append(result)
    return output


BOOTSTRAP_METRICS = {
    "mean_abs_log_h_error_change": "abs_log_h_error_change_adjusted_minus_constant",
    "mean_direct_holdout_score_per_site": "direct_holdout_score_adjusted_minus_constant_per_site",
    "mean_signed_log_h_error_adjusted": "signed_log_h_error_adjusted",
    "mean_signed_log_h_error_constant": "signed_log_h_error_constant",
    "mean_signed_log_h_error_known_beta": "signed_log_h_error_known_beta",
    "mean_adjusted_minus_known_signed_log_h_error": "signed_log_h_error_adjusted_minus_known_beta",
    "mean_squared_log_h_error_adjusted": "squared_log_h_error_adjusted",
    "mean_squared_log_h_error_known_beta": "squared_log_h_error_known_beta",
    "point_error_1_5fold_rate_adjusted": "point_error_1_5fold_adjusted",
    "point_error_1_5fold_rate_constant": "point_error_1_5fold_constant",
    "point_error_1_5fold_rate_known_beta": "point_error_1_5fold_known_beta",
    "mean_beta_error": "beta_error",
    "mean_abs_beta_error": "abs_beta_error",
    "model_preference_adjusted": "direct_adjusted_win",
    "model_preference_constant": "direct_constant_win",
    "model_preference_tie": "direct_tie",
}


def _bootstrap(
    rows: Sequence[Mapping[str, Any]], *, seed: int, draws: int
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], Mapping[str, Any]]]:
    if not rows:
        return [], {}
    lane = str(rows[0]["lane"])
    lane_cells = CELL_IDS if lane == "latent" else CELL_IDS[:ORACLE_CELL_COUNT]
    blocks = sorted({int(row["block_index"]) for row in rows})
    block_map = {block: index for index, block in enumerate(blocks)}
    matrix: dict[str, np.ndarray] = {}
    for metric_name, column in BOOTSTRAP_METRICS.items():
        values = np.empty((len(blocks), len(lane_cells)), dtype=np.float64)
        values.fill(np.nan)
        for row in rows:
            cell_index = lane_cells.index(str(row["cell_id"]))
            value: float
            if metric_name == "model_preference_adjusted":
                value = float(row["direct_score_preference"] == "adjusted")
            elif metric_name == "model_preference_constant":
                value = float(row["direct_score_preference"] == "constant")
            elif metric_name == "model_preference_tie":
                value = float(row["direct_score_preference"] == "tie")
            else:
                raw = row.get(column)
                value = float(raw) if raw is not None else np.nan
            values[block_map[int(row["block_index"])], cell_index] = value
            # Beta-specific diagnostics are unavailable for B100-A; h-error
            # metrics remain defined because truth h is known.
            matrix[metric_name] = values
    rng = np.random.default_rng(seed)
    bootstrap_values = {
        name: np.empty((draws, len(lane_cells)), dtype=np.float64) for name in matrix
    }
    for start in range(0, draws, 256):
        stop = min(start + 256, draws)
        indices = rng.integers(0, len(blocks), size=(stop - start, len(blocks)))
        for name, values in matrix.items():
            valid_columns = np.isfinite(values).any(axis=0)
            if not valid_columns.any():
                bootstrap_values[name][start:stop] = np.nan
                continue
            sampled = values[:, valid_columns][indices]
            with np.errstate(invalid="ignore"):
                bootstrap_values[name][start:stop, valid_columns] = np.nanmean(sampled, axis=1)
    rows_out: list[dict[str, Any]] = []
    lookup: dict[tuple[str, str], Mapping[str, Any]] = {}
    for cell_index, cell_id in enumerate(lane_cells):
        for metric_name, values in bootstrap_values.items():
            point_values = matrix[metric_name][:, cell_index]
            if not np.isfinite(point_values).any():
                continue
            draws_for_cell = values[:, cell_index]
            draws_for_cell = draws_for_cell[np.isfinite(draws_for_cell)]
            summary = {
                "lane": lane,
                "cell_id": cell_id,
                "metric": metric_name,
                "estimate": float(point_values.mean()),
                "analytic_mcse": float(point_values.std(ddof=1) / np.sqrt(len(point_values)))
                if len(point_values) > 1
                else 0.0,
                "bootstrap_draws": draws,
                "bootstrap_seed": seed,
                "bootstrap_p2_5": float(np.quantile(draws_for_cell, 0.025)),
                "bootstrap_median": float(np.quantile(draws_for_cell, 0.5)),
                "bootstrap_p97_5": float(np.quantile(draws_for_cell, 0.975)),
                "_draws": draws_for_cell,
            }
            rows_out.append(
                {key: value for key, value in summary.items() if not key.startswith("_")}
            )
            lookup[(cell_id, metric_name)] = summary
    return rows_out, lookup


def _paired_contrasts(
    rows: Sequence[Mapping[str, Any]], bootstrap: Mapping[tuple[str, str], Mapping[str, Any]]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    lane = str(rows[0]["lane"])
    lane_cells = CELL_IDS if lane == "latent" else CELL_IDS[:ORACLE_CELL_COUNT]
    for cell_id in lane_cells:
        subset = [row for row in rows if row["cell_id"] == cell_id]
        result: dict[str, Any] = {
            "cell_id": cell_id,
            "lane": str(subset[0]["lane"]),
            "n_histories": len(subset),
        }
        for metric, key in (
            ("abs_log_h_error_change", "mean_abs_log_h_error_change"),
            ("direct_holdout_score_per_site", "mean_direct_holdout_score_per_site"),
            ("signed_log_h_error_adjusted", "mean_signed_log_h_error_adjusted"),
            ("signed_log_h_error_constant", "mean_signed_log_h_error_constant"),
            ("signed_log_h_error_known_beta", "mean_signed_log_h_error_known_beta"),
            (
                "adjusted_minus_known_signed_log_h_error",
                "mean_adjusted_minus_known_signed_log_h_error",
            ),
            ("beta_error", "mean_beta_error"),
            ("abs_beta_error", "mean_abs_beta_error"),
            ("point_error_1_5fold_rate_adjusted", "point_error_1_5fold_rate_adjusted"),
            ("point_error_1_5fold_rate_constant", "point_error_1_5fold_rate_constant"),
            ("point_error_1_5fold_rate_known_beta", "point_error_1_5fold_rate_known_beta"),
            ("model_preference_adjusted", "model_preference_adjusted"),
            ("model_preference_constant", "model_preference_constant"),
            ("model_preference_tie", "model_preference_tie"),
        ):
            summary = bootstrap.get((cell_id, key))
            if summary is None:
                continue
            result[f"{metric}_estimate"] = summary["estimate"]
            result[f"{metric}_analytic_mcse"] = summary["analytic_mcse"]
            result[f"{metric}_bootstrap_p2_5"] = summary["bootstrap_p2_5"]
            result[f"{metric}_bootstrap_p97_5"] = summary["bootstrap_p97_5"]
        output.append(result)
    return output


def _forecast_metrics(
    rows: Sequence[Mapping[str, Any]],
    bootstrap: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    def cell(cell_id: str) -> list[Mapping[str, Any]]:
        return [row for row in rows if row["cell_id"] == cell_id]

    exact_ratio: dict[str, Any] = {}
    for cell_id, target, contradiction in (("E0_h3", 1.25, 1.6), ("E06_h3", 1.05, 1.3)):
        subset = cell(cell_id)
        free = float(
            np.sqrt(np.mean(np.square([row["signed_log_h_error_adjusted"] for row in subset])))
        )
        known = float(
            np.sqrt(np.mean(np.square([row["signed_log_h_error_known_beta"] for row in subset])))
        )
        ratio = free / known if known else None
        free_draws = np.asarray(bootstrap[(cell_id, "mean_squared_log_h_error_adjusted")]["_draws"])
        known_draws = np.asarray(
            bootstrap[(cell_id, "mean_squared_log_h_error_known_beta")]["_draws"]
        )
        valid_ratio = known_draws > 0
        ratio_draws = np.sqrt(free_draws[valid_ratio] / known_draws[valid_ratio])
        ratio_interval = (
            {
                "bootstrap_ratio_p2_5": float(np.quantile(ratio_draws, 0.025)),
                "bootstrap_ratio_median": float(np.quantile(ratio_draws, 0.5)),
                "bootstrap_ratio_p97_5": float(np.quantile(ratio_draws, 0.975)),
            }
            if ratio_draws.size
            else {
                "bootstrap_ratio_p2_5": None,
                "bootstrap_ratio_median": None,
                "bootstrap_ratio_p97_5": None,
            }
        )
        exact_ratio[cell_id] = {
            "free_rmse_log_ratio_to_known_beta": ratio,
            "free_rmse_log": free,
            "known_beta_rmse_log": known,
            "forecast_target_ratio": target,
            "contradiction_bound_ratio": contradiction,
            "distance_from_forecast_target_ratio": ratio - target if ratio is not None else None,
            **ratio_interval,
            "contradiction_bound_exceeded": bool(ratio > contradiction)
            if ratio is not None
            else None,
        }
    exact06_h3 = cell("E06_h3")
    adjusted_mean = _mean([row["signed_log_h_error_adjusted"] for row in exact06_h3])
    known_mean = _mean([row["signed_log_h_error_known_beta"] for row in exact06_h3])
    constant_mean = _mean([row["signed_log_h_error_constant"] for row in exact06_h3])
    diff_summary = bootstrap[("E06_h3", "mean_adjusted_minus_known_signed_log_h_error")]
    null_balance: dict[str, Any] = {}
    for cell_id in ("E0_h1", "E06_h1"):
        subset = cell(cell_id)
        truth_beta = float(subset[0]["truth_beta"])
        adjusted = np.asarray([row["fit_h"] for row in subset])
        null_known = np.asarray([row["known_beta_fit_h"] for row in subset])
        over = adjusted > 1.0
        over_count = int(over.sum())
        below_count = int(
            sum(
                row["fit_beta"] < truth_beta - ROUNDING_TOLERANCE
                for row in subset
                if row["fit_h"] > 1.0
            )
        )
        above_count = int(
            sum(
                row["fit_beta"] > truth_beta + ROUNDING_TOLERANCE
                for row in subset
                if row["fit_h"] > 1.0
            )
        )
        tie_count = int(
            sum(
                abs(row["fit_beta"] - truth_beta) <= ROUNDING_TOLERANCE
                for row in subset
                if row["fit_h"] > 1.0
            )
        )
        null_balance[cell_id] = {
            "adjusted_h_ge_1_5_frequency": float(np.mean(adjusted >= 1.5)),
            "known_beta_h_ge_1_5_frequency": float(np.mean(null_known >= 1.5)),
            "adjusted_minus_known_frequency": float(
                np.mean(adjusted >= 1.5) - np.mean(null_known >= 1.5)
            ),
            "adjusted_h_gt_1_beta_below_truth_count": below_count,
            "adjusted_h_gt_1_beta_above_truth_count": above_count,
            "adjusted_h_gt_1_beta_tie_truth_count": tie_count,
            "adjusted_h_gt_1_beta_below_truth_rate": below_count / over_count
            if over_count
            else None,
            "adjusted_h_gt_1_beta_above_truth_rate": above_count / over_count
            if over_count
            else None,
            "adjusted_h_gt_1_beta_tie_truth_rate": tie_count / over_count if over_count else None,
            "adjusted_h_gt_1_count": over_count,
            "truth_beta": truth_beta,
        }
    direct_exact06: dict[str, Any] = {}
    for cell_id in ("E06_h1", "E06_h3"):
        subset = cell(cell_id)
        scores = np.asarray(
            [row["direct_holdout_score_adjusted_minus_constant_per_site"] for row in subset]
        )
        direct_exact06[cell_id] = {
            "direct_score_mean_per_site": float(scores.mean()),
            "direct_score_win_rate": float(
                np.mean([row["direct_score_preference"] == "adjusted" for row in subset])
            ),
            "forecast_mean_range_per_site": [0.01, 0.025],
            "forecast_win_rate_target": 2 / 3,
            "advisory_mean_in_range": bool(0.01 <= scores.mean() <= 0.025),
            "distance_from_forecast_mean_lower_bound": float(scores.mean() - 0.01),
            "distance_from_forecast_mean_upper_bound": float(scores.mean() - 0.025),
            "distance_from_forecast_win_rate_target": float(
                np.mean([row["direct_score_preference"] == "adjusted" for row in subset]) - 2 / 3
            ),
            "bootstrap_score_p2_5": bootstrap[(cell_id, "mean_direct_holdout_score_per_site")][
                "bootstrap_p2_5"
            ],
            "bootstrap_score_p97_5": bootstrap[(cell_id, "mean_direct_holdout_score_per_site")][
                "bootstrap_p97_5"
            ],
            "bootstrap_win_rate_p2_5": bootstrap[(cell_id, "model_preference_adjusted")][
                "bootstrap_p2_5"
            ],
            "bootstrap_win_rate_p97_5": bootstrap[(cell_id, "model_preference_adjusted")][
                "bootstrap_p97_5"
            ],
        }
    return {
        "interpretation": (
            "Fable forecasts are advisory predictions; they never gate completion or "
            "interpretation."
        ),
        "exact_h3_free_vs_known_beta": exact_ratio,
        "exact_E06_h3_constant_and_known_beta": {
            "constant_mean_signed_log_error": constant_mean,
            "adjusted_mean_signed_log_error": adjusted_mean,
            "known_beta_mean_signed_log_error": known_mean,
            "constant_mean_log_error_lower_target": 0.10,
            "abs_adjusted_minus_known_mean_log_error": abs(adjusted_mean - known_mean),
            "bootstrap_constant_mean_p2_5": bootstrap[
                ("E06_h3", "mean_signed_log_h_error_constant")
            ]["bootstrap_p2_5"],
            "bootstrap_constant_mean_p97_5": bootstrap[
                ("E06_h3", "mean_signed_log_h_error_constant")
            ]["bootstrap_p97_5"],
            "bootstrap_adjusted_mean_p2_5": bootstrap[
                ("E06_h3", "mean_signed_log_h_error_adjusted")
            ]["bootstrap_p2_5"],
            "bootstrap_adjusted_mean_p97_5": bootstrap[
                ("E06_h3", "mean_signed_log_h_error_adjusted")
            ]["bootstrap_p97_5"],
            "bootstrap_known_beta_mean_p2_5": bootstrap[
                ("E06_h3", "mean_signed_log_h_error_known_beta")
            ]["bootstrap_p2_5"],
            "bootstrap_known_beta_mean_p97_5": bootstrap[
                ("E06_h3", "mean_signed_log_h_error_known_beta")
            ]["bootstrap_p97_5"],
            "bootstrap_adjusted_minus_known_p2_5": diff_summary["bootstrap_p2_5"],
            "bootstrap_adjusted_minus_known_p97_5": diff_summary["bootstrap_p97_5"],
            "adjusted_known_mean_difference_bound": 0.05,
            "advisory_constant_target_met": bool(constant_mean >= 0.10),
            "advisory_adjusted_known_difference_within_bound": bool(
                abs(adjusted_mean - known_mean) <= 0.05
            ),
        },
        "exact_null_beta_balance": null_balance,
        "exact_E06_direct_score": direct_exact06,
    }


def _geometry_diagnostics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for lane in ("latent", "oracle"):
        subset = [row for row in rows if row["lane"] == lane]
        result[lane] = {
            "rows": len(subset),
            "fit_edge_counts": {
                name: int(sum(bool(row[name]) for row in subset))
                for name in (
                    "fit_beta_lower_edge",
                    "fit_beta_upper_edge",
                    "fit_h_lower_edge",
                    "fit_h_upper_edge",
                )
            },
            "coarse_grid_sensitive_count": int(
                sum(bool(row["resolution_sensitive"]) for row in subset)
            ),
            "coarse_fine_lr_movement_max": float(
                max(row["coarse_fine_lr_movement"] for row in subset)
            ),
            "uncalibrated_geometry": True,
        }
    result["interpretation"] = (
        "LR<=2 profiles, edge contacts, and coarse-grid movements are uncalibrated "
        "geometry; no confidence or test claim is attached."
    )
    return result


def _write_figures(
    cell_summary: Sequence[Mapping[str, Any]], contrasts: Sequence[Mapping[str, Any]], output: Path
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [str(row["cell_id"]) for row in cell_summary if row["lane"] == "latent"]
    summary = [row for row in cell_summary if row["lane"] == "latent"]
    contrast = [row for row in contrasts if row["lane"] == "latent"]
    x = np.arange(len(labels))
    fig, axis = plt.subplots(figsize=(11, 5), constrained_layout=True)
    axis.bar(
        x - 0.18,
        [row["abs_log_h_error_adjusted_mean"] for row in summary],
        width=0.36,
        label="adjusted",
    )
    axis.bar(
        x + 0.18,
        [row["abs_log_h_error_constant_mean"] for row in summary],
        width=0.36,
        label="constant",
    )
    axis.set_xticks(x, labels, rotation=35, ha="right")
    axis.set_ylabel("mean absolute log h error")
    axis.set_title("Goal053 mean h-estimation errors")
    axis.legend()
    fig.savefig(output / "mean_errors.png", dpi=180)
    fig.savefig(output / "mean_errors.pdf")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(11, 5), constrained_layout=True)
    means = np.asarray([row["direct_holdout_score_per_site_estimate"] for row in contrast])
    lower = np.asarray([row["direct_holdout_score_per_site_bootstrap_p2_5"] for row in contrast])
    upper = np.asarray([row["direct_holdout_score_per_site_bootstrap_p97_5"] for row in contrast])
    axis.errorbar(x, means, yerr=np.vstack((means - lower, upper - means)), fmt="o")
    axis.axhline(0.0, color="black", linewidth=0.7)
    axis.set_xticks(x, labels, rotation=35, ha="right")
    axis.set_ylabel("adjusted minus constant held-out score (nats/site)")
    axis.set_title("Direct held-out paired contrasts; bootstrap 95% intervals")
    fig.savefig(output / "paired_contrasts.png", dpi=180)
    fig.savefig(output / "paired_contrasts.pdf")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(11, 5), constrained_layout=True)
    axis.bar(
        x - 0.24,
        [row["model_preference_adjusted_estimate"] for row in contrast],
        width=0.24,
        label="adjusted wins",
    )
    axis.bar(
        x,
        [row["model_preference_constant_estimate"] for row in contrast],
        width=0.24,
        label="constant wins",
    )
    axis.bar(
        x + 0.24,
        [row["model_preference_tie_estimate"] for row in contrast],
        width=0.24,
        label="ties",
    )
    axis.set_ylim(0, 1)
    axis.set_xticks(x, labels, rotation=35, ha="right")
    axis.set_ylabel("proportion of histories")
    axis.set_title("Direct model preference with ties retained")
    axis.legend()
    fig.savefig(output / "model_preference.png", dpi=180)
    fig.savefig(output / "model_preference.pdf")
    plt.close(fig)


def _testing_metadata(
    blocks: int = 2, site_count: int = 8, map_shape: tuple[int, int] = (3, 4)
) -> dict[str, NDArray[Any]]:
    """Build valid small metadata for unit tests without weakening production checks."""
    if blocks < 1 or site_count < 2 or len(map_shape) != 2:
        raise ValueError("testing dimensions are invalid")
    n = blocks * CELL_COUNT
    cell_ids = np.tile(np.asarray(CELL_IDS), blocks)
    metadata: dict[str, NDArray[Any]] = {
        "effects": EFFECTS.copy(),
        "betas": BETAS.copy(),
        "cell_ids": cell_ids,
        "replicate_indices": np.repeat(np.arange(blocks), CELL_COUNT),
        "truth_h": np.tile(np.asarray((1.0, 3.0, 1.0, 3.0, 1.0, 3.0)), blocks),
        "truth_beta": np.tile(np.asarray((0.0, 0.0, 0.6, 0.6, np.nan, np.nan)), blocks),
        "opaque_ids": np.asarray([f"test-{i:04d}" for i in range(n)]),
        "oracle_history_indices": (
            np.arange(min(blocks, PRODUCTION_ORACLE_BLOCK_COUNT))[:, None] * CELL_COUNT
            + np.arange(ORACLE_CELL_COUNT)
        ).ravel(),
        "site_ids": np.asarray([f"site-{i:03d}" for i in range(site_count)]),
        "training_mask": np.asarray([i < site_count // 2 for i in range(site_count)]),
        "site_A": np.linspace(-1.0, 1.0, site_count),
        "map_A": np.zeros(map_shape),
        "true_arrival": np.full((n, site_count), 20.0),
        "true_extirpation": np.full((n, site_count), 40.0),
        "true_hazards": np.full((n, site_count), 0.002),
        "predator_counts": np.zeros((n, site_count, 6), dtype=np.int64),
        "prey_counts": np.zeros((n, site_count, 6), dtype=np.int64),
        "latent_holdout_predator": np.zeros(n),
    }
    return metadata


def synthesize(input_dir: Path, output_dir: Path, *, strict: bool = True) -> dict[str, Any]:
    """Synthesize a registered evidence directory into reviewable artefacts."""
    started = time.perf_counter()
    input_path = Path(input_dir)
    output = Path(output_dir)
    if (output / "summary.json").exists():
        raise ValueError(f"refusing to overwrite completed synthesis: {output}")
    metadata, scores, input_hashes = _load_bundle(input_path, strict=strict)
    primary_rows = _rows_for_lane(metadata, scores, "latent")
    oracle_rows = _rows_for_lane(metadata, scores, "oracle")
    output.mkdir(parents=True, exist_ok=True)
    _write_csv(output / "metrics.csv", primary_rows)
    _write_csv(output / "oracle_metrics.csv", oracle_rows)
    primary_bootstrap_rows, primary_bootstrap = _bootstrap(
        primary_rows, seed=BOOTSTRAP_SEED, draws=BOOTSTRAP_DRAWS
    )
    oracle_bootstrap_rows, oracle_bootstrap = _bootstrap(
        oracle_rows, seed=BOOTSTRAP_SEED, draws=BOOTSTRAP_DRAWS
    )
    _write_csv(output / "bootstrap_summary.csv", primary_bootstrap_rows)
    _write_csv(output / "oracle_bootstrap_summary.csv", oracle_bootstrap_rows)
    cell_summary = _cell_summary(primary_rows, bootstrap=primary_bootstrap)
    cell_summary.extend(_cell_summary(oracle_rows, bootstrap=oracle_bootstrap))
    _write_csv(output / "cell_summary.csv", cell_summary)
    contrasts = _paired_contrasts(primary_rows, primary_bootstrap)
    contrasts.extend(_paired_contrasts(oracle_rows, oracle_bootstrap))
    _write_csv(output / "paired_contrasts.csv", contrasts)
    diagnostics = _geometry_diagnostics(primary_rows + oracle_rows)
    _write_json(output / "diagnostics.json", diagnostics)
    _write_figures(cell_summary, contrasts, output)

    config = {
        "workflow": "goal053_prospective_background_synthesis_v1",
        "effects": EFFECTS.tolist(),
        "betas": BETAS.tolist(),
        "cell_ids": list(CELL_IDS),
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "point_error_threshold": 1.5,
        "point_error_log_threshold": POINT_ERROR_LOG_THRESHOLD,
        "model_tie_tolerance": MODEL_TIE_TOLERANCE,
        "score_denominator_sites": 40,
        "strict": strict,
    }
    config_serialized = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    output_files = [
        "metrics.csv",
        "oracle_metrics.csv",
        "bootstrap_summary.csv",
        "oracle_bootstrap_summary.csv",
        "cell_summary.csv",
        "paired_contrasts.csv",
        "diagnostics.json",
        "mean_errors.png",
        "mean_errors.pdf",
        "paired_contrasts.png",
        "paired_contrasts.pdf",
        "model_preference.png",
        "model_preference.pdf",
    ]
    output_hashes = {name: _sha256(output / name) for name in output_files}
    source_paths = [
        Path(__file__),
        Path(__file__).resolve().parents[2] / "scripts/synthesize_prospective_background.py",
    ]
    source_hashes = {
        str(path.relative_to(Path(__file__).resolve().parents[2])): _sha256(path)
        for path in source_paths
        if path.is_file()
    }
    summary = {
        "status": "complete_descriptive_prospective_comparison",
        "input_directory": str(input_path),
        "input_hashes": input_hashes,
        "source_hashes": source_hashes,
        "config_sha256": hashlib.sha256(config_serialized).hexdigest(),
        "history_count": len(primary_rows),
        "oracle_history_count": len(oracle_rows),
        "block_count": len(primary_rows) // CELL_COUNT,
        "oracle_block_count": len(oracle_rows) // ORACLE_CELL_COUNT,
        "output_hashes": output_hashes,
        "geometry": diagnostics,
        "fable_forecasts": _forecast_metrics(primary_rows, primary_bootstrap),
        "uncertainty": {
            "primary_bootstrap": "2,000 whole-block draws, shared across all six cells",
            "oracle_bootstrap": (
                "2,000 whole-block draws over the registered first 250 blocks using "
                "the registered root 2026092703"
            ),
            "interpretation": (
                "Bootstrap uncertainty is across simulation blocks; it is not parameter "
                "uncertainty or a per-history test."
            ),
        },
        "elapsed_seconds": time.perf_counter() - started,
    }
    _write_json(output / "summary.json", summary)
    return summary


__all__ = [
    "BETAS",
    "BOOTSTRAP_DRAWS",
    "BOOTSTRAP_SEED",
    "CELL_IDS",
    "EFFECTS",
    "_testing_metadata",
    "expected_score_shapes",
    "synthesize",
    "validate_metadata",
]
