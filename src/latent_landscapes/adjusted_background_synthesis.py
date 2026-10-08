"""Deterministic synthesis for the Goal 052 adjusted-background pilot.

The evidence bundle contains complete latent and oracle likelihood rectangles
for the fixed 24-history panel.  This module only summarizes those saved
rectangles; it never draws, bootstraps, optimizes outside the registered grid,
or adds calibration claims.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.adjusted_background_replay import REPLAY_CELL_IDS

FloatArray = NDArray[np.float64]

EFFECTS = np.linspace(1.0, 10.0, 181, dtype=np.float64)
BETAS = np.linspace(-2.0, 2.0, 81, dtype=np.float64)
SURVEY_TIMES = np.arange(10.0, 61.0, 10.0, dtype=np.float64)
CONTOUR_LEVELS = (0.5, 2.0, 4.0, 8.0)
LR_PROFILE_LIMIT = 2.0
RESOLUTION_LR_LIMIT = 0.10
RESOLUTION_COORDINATE_LIMIT = 0.10
RESOLUTION_EPSILON = 1e-12
EXPECTED_HISTORY_COUNT = 24
EXPECTED_SURFACE_SHAPE = (EXPECTED_HISTORY_COUNT, len(BETAS), len(EFFECTS))


@dataclass(frozen=True, slots=True)
class FitPoint:
    """Grid maximum with deterministic lowest-beta/lowest-h tie breaking."""

    beta_index: int
    h_index: int
    beta: float
    h: float
    value: float


@dataclass(frozen=True, slots=True)
class ProfileSummary:
    """Uncalibrated LR<=2 profile geometry for one axis."""

    minimum: float | None
    maximum: float | None
    components: tuple[tuple[float, float], ...]
    touches_lower: bool
    touches_upper: bool


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
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
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


def _require_array(values: Mapping[str, NDArray[Any]], name: str) -> NDArray[Any]:
    if name not in values:
        raise ValueError(f"evidence bundle is missing required array: {name}")
    return values[name]


def _validate_evidence(values: Mapping[str, NDArray[Any]]) -> None:
    effects = np.asarray(_require_array(values, "effects"), dtype=np.float64)
    betas = np.asarray(_require_array(values, "betas"), dtype=np.float64)
    if effects.shape != EFFECTS.shape or not np.array_equal(effects, EFFECTS):
        raise ValueError("evidence effects do not match the frozen h grid")
    if betas.shape != BETAS.shape or not np.array_equal(betas, BETAS):
        raise ValueError("evidence betas do not match the frozen beta grid")
    cell_ids = np.asarray(_require_array(values, "cell_ids"))
    replicate_indices = np.asarray(_require_array(values, "replicate_indices"))
    truth_h = np.asarray(_require_array(values, "truth_h"), dtype=np.float64)
    expected_ids = tuple(cell_id for _replicate in range(6) for cell_id in REPLAY_CELL_IDS)
    expected_indices = np.repeat(np.arange(6, dtype=np.int64), len(REPLAY_CELL_IDS))
    expected_truths = np.asarray(
        [1.0, 3.0, 1.0, 3.0] * 6,
        dtype=np.float64,
    )
    if cell_ids.shape != (EXPECTED_HISTORY_COUNT,) or tuple(map(str, cell_ids)) != expected_ids:
        raise ValueError("evidence cell IDs do not match the frozen six-block order")
    if replicate_indices.shape != (EXPECTED_HISTORY_COUNT,) or not np.array_equal(
        replicate_indices, expected_indices
    ):
        raise ValueError("evidence replicate indices do not match the frozen six-block order")
    if truth_h.shape != (EXPECTED_HISTORY_COUNT,) or not np.array_equal(truth_h, expected_truths):
        raise ValueError("evidence truth_h values do not match the fixed panel")
    for name in ("latent_training", "latent_holdout_joint", "oracle_training", "oracle_holdout"):
        array = np.asarray(_require_array(values, name), dtype=np.float64)
        if array.shape != EXPECTED_SURFACE_SHAPE:
            raise ValueError(f"evidence array has wrong surface shape: {name}")
        if not np.isfinite(array).all():
            raise ValueError(f"evidence array contains non-finite values: {name}")
    optional = {"site_A", "training_mask", "true_arrival", "true_extirpation"}
    present = optional.intersection(values)
    if present and present != optional:
        raise ValueError("geometry evidence must include all four optional arrays")
    if present:
        if np.asarray(values["site_A"]).shape != (160,):
            raise ValueError("site_A must contain one value per accepted site")
        if np.asarray(values["training_mask"]).shape != (160,):
            raise ValueError("training_mask must contain one value per accepted site")
        for name in ("true_arrival", "true_extirpation"):
            if np.asarray(values[name]).shape != (EXPECTED_HISTORY_COUNT, 160):
                raise ValueError(f"{name} must have one row per replay history")
        if not all(
            np.isfinite(np.asarray(values[name], dtype=np.float64)).all() for name in present
        ):
            raise ValueError("geometry evidence contains non-finite values")


def maximum_on_grid(
    surface: FloatArray, betas: FloatArray = BETAS, effects: FloatArray = EFFECTS
) -> FitPoint:
    """Return the maximum in beta-major, h-minor order with stable ties."""

    surface = np.asarray(surface, dtype=np.float64)
    if surface.shape != (len(betas), len(effects)) or not np.isfinite(surface).all():
        raise ValueError("likelihood surface shape or finiteness is invalid")
    flat_index = int(np.argmax(surface.ravel(order="C")))
    beta_index, h_index = np.unravel_index(flat_index, surface.shape)
    return FitPoint(
        int(beta_index),
        int(h_index),
        float(betas[beta_index]),
        float(effects[h_index]),
        float(surface[beta_index, h_index]),
    )


def profile_summary(
    profile_values: FloatArray,
    grid: FloatArray,
    *,
    limit: float = LR_PROFILE_LIMIT,
) -> ProfileSummary:
    """Summarize connected LR<=limit regions on one registered grid axis."""

    values = np.asarray(profile_values, dtype=np.float64)
    grid = np.asarray(grid, dtype=np.float64)
    if values.shape != grid.shape or not np.isfinite(values).all():
        raise ValueError("profile and grid shapes/finiteness differ")
    maximum = float(values.max())
    included = 2.0 * (maximum - values) <= limit + 1e-12
    components: list[tuple[float, float]] = []
    start: int | None = None
    for index, present in enumerate(np.r_[included, False]):
        if present and start is None:
            start = index
        elif not present and start is not None:
            components.append((float(grid[start]), float(grid[index - 1])))
            start = None
    return ProfileSummary(
        None if not components else components[0][0],
        None if not components else components[-1][1],
        tuple(components),
        bool(included[0]),
        bool(included[-1]),
    )


def _profile_strings(summary: ProfileSummary) -> tuple[str, str]:
    return (
        json.dumps(summary.components, separators=(",", ":")),
        json.dumps(
            {
                "min": summary.minimum,
                "max": summary.maximum,
                "touches_lower": summary.touches_lower,
                "touches_upper": summary.touches_upper,
            },
            separators=(",", ":"),
        ),
    )


def _surface_metrics(surface: FloatArray, holdout: FloatArray) -> dict[str, Any]:
    fit = maximum_on_grid(surface)
    beta_zero = int(np.flatnonzero(BETAS == 0.0)[0])
    h_one = 0
    constant_curve = surface[beta_zero]
    constant_fit = maximum_on_grid(constant_curve[None, :], np.asarray([0.0]), EFFECTS)
    null_curve = surface[:, h_one]
    null_fit = maximum_on_grid(null_curve[:, None], BETAS, np.asarray([1.0]))
    constant_null = float(surface[beta_zero, h_one])
    adjusted_lr = 2.0 * (fit.value - constant_fit.value)
    adjusted_null_lr = 2.0 * (fit.value - null_fit.value)
    constant_null_lr = 2.0 * (constant_fit.value - constant_null)
    holdout_adjusted = float(holdout[fit.beta_index, fit.h_index])
    holdout_adjusted_null = float(holdout[null_fit.beta_index, h_one])
    holdout_constant = float(holdout[beta_zero, constant_fit.h_index])
    holdout_constant_null = float(holdout[beta_zero, h_one])
    h_profile = profile_summary(np.max(surface, axis=0), EFFECTS)
    beta_profile = profile_summary(np.max(surface, axis=1), BETAS)
    h_components, h_range = _profile_strings(h_profile)
    beta_components, beta_range = _profile_strings(beta_profile)

    coarse = surface[::2, ::2]
    coarse_fit = maximum_on_grid(coarse, BETAS[::2], EFFECTS[::2])
    coarse_lr_movement = 2.0 * (fit.value - coarse_fit.value)
    h_shift = abs(fit.h - coarse_fit.h)
    beta_shift = abs(fit.beta - coarse_fit.beta)
    resolution_sensitive = bool(
        coarse_lr_movement > RESOLUTION_LR_LIMIT + RESOLUTION_EPSILON
        or h_shift > RESOLUTION_COORDINATE_LIMIT + RESOLUTION_EPSILON
        or beta_shift > RESOLUTION_COORDINATE_LIMIT + RESOLUTION_EPSILON
    )
    return {
        "fit_beta": fit.beta,
        "fit_h": fit.h,
        "fit_beta_lower_edge": fit.beta_index == 0,
        "fit_beta_upper_edge": fit.beta_index == len(BETAS) - 1,
        "fit_h_lower_edge": fit.h_index == 0,
        "fit_h_upper_edge": fit.h_index == len(EFFECTS) - 1,
        "fit_value": fit.value,
        "constant_fit_h": constant_fit.h,
        "constant_fit_value": constant_fit.value,
        "adjusted_null_fit_beta": null_fit.beta,
        "adjusted_null_fit_value": null_fit.value,
        "constant_null_value": constant_null,
        "adjusted_minus_constant_lr": adjusted_lr,
        "adjusted_minus_adjustednull_lr": adjusted_null_lr,
        "constant_minus_constantnull_lr": constant_null_lr,
        "holdout_adjusted_minus_fitted_adjustednull_conditional_prey": holdout_adjusted
        - holdout_adjusted_null,
        "holdout_constant_minus_constantnull_conditional_prey": holdout_constant
        - holdout_constant_null,
        "h_profile_components_lr_le_2": h_components,
        "h_profile_range_lr_le_2": h_range,
        "h_profile_topology_lr_le_2": "disconnected"
        if len(h_profile.components) > 1
        else "connected",
        "h_profile_touches_lower": h_profile.touches_lower,
        "h_profile_touches_upper": h_profile.touches_upper,
        "beta_profile_components_lr_le_2": beta_components,
        "beta_profile_range_lr_le_2": beta_range,
        "beta_profile_topology_lr_le_2": "disconnected"
        if len(beta_profile.components) > 1
        else "connected",
        "beta_profile_touches_lower": beta_profile.touches_lower,
        "beta_profile_touches_upper": beta_profile.touches_upper,
        "coarse_fit_beta": coarse_fit.beta,
        "coarse_fit_h": coarse_fit.h,
        "coarse_fit_value": coarse_fit.value,
        "coarse_fine_lr_movement": coarse_lr_movement,
        "coarse_fine_h_shift": h_shift,
        "coarse_fine_beta_shift": beta_shift,
        "resolution_sensitive": resolution_sensitive,
    }


def _lane_rows(values: Mapping[str, NDArray[Any]], lane: str) -> list[dict[str, Any]]:
    training = np.asarray(values[f"{lane}_training"], dtype=np.float64)
    holdout_name = f"{lane}_holdout_joint" if lane == "latent" else f"{lane}_holdout"
    holdout = np.asarray(values[holdout_name], dtype=np.float64)
    cell_ids = np.asarray(values["cell_ids"])
    replicate_indices = np.asarray(values["replicate_indices"])
    truth_h = np.asarray(values["truth_h"])
    rows: list[dict[str, Any]] = []
    for history in range(EXPECTED_HISTORY_COUNT):
        row = _surface_metrics(training[history], holdout[history])
        rows.append(
            {
                "history_index": history,
                "replicate_index": int(replicate_indices[history]),
                "cell_id": str(cell_ids[history]),
                "truth_h": float(truth_h[history]),
                "lane": lane,
                "profile_interpretation": "UNCALIBRATED likelihood geometry; not a 95% interval",
                **row,
            }
        )
    return rows


def _merge_lane_rows(values: Mapping[str, NDArray[Any]]) -> list[dict[str, Any]]:
    latent = _lane_rows(values, "latent")
    oracle = _lane_rows(values, "oracle")
    merged: list[dict[str, Any]] = []
    for latent_row, oracle_row in zip(latent, oracle, strict=True):
        row: dict[str, Any] = {
            key: value
            for key, value in latent_row.items()
            if key not in {"lane"}
        }
        for key, value in oracle_row.items():
            if key not in {"history_index", "replicate_index", "cell_id", "truth_h", "lane"}:
                row[f"oracle_{key}"] = value
        merged.append(row)
    return merged


def _cell_summary(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for cell_id in REPLAY_CELL_IDS:
        subset = [row for row in rows if row["cell_id"] == cell_id]
        if len(subset) != 6:
            raise ValueError("each fixed cell must have six history rows")
        result: dict[str, Any] = {"cell_id": cell_id, "n_histories": len(subset)}
        for prefix in ("", "oracle_"):
            for name in (
                "fit_h",
                "fit_beta",
                "adjusted_minus_constant_lr",
                "adjusted_minus_adjustednull_lr",
                "holdout_adjusted_minus_fitted_adjustednull_conditional_prey",
                "coarse_fine_lr_movement",
            ):
                values = np.asarray([float(row[f"{prefix}{name}"]) for row in subset])
                label = f"{prefix}{name}"
                result[f"{label}_mean"] = float(values.mean())
                result[f"{label}_minimum"] = float(values.min())
                result[f"{label}_maximum"] = float(values.max())
        result["resolution_sensitive_count"] = int(
            sum(bool(row["resolution_sensitive"]) for row in subset)
        )
        result["oracle_resolution_sensitive_count"] = int(
            sum(bool(row["oracle_resolution_sensitive"]) for row in subset)
        )
        for prefix in ("", "oracle_"):
            for name in (
                "fit_beta_lower_edge",
                "fit_beta_upper_edge",
                "fit_h_lower_edge",
                "fit_h_upper_edge",
            ):
                result[f"{prefix}{name}_count"] = int(
                    sum(bool(row[f"{prefix}{name}"]) for row in subset)
                )
        output.append(result)
    return output


def _geometry_rows(values: Mapping[str, NDArray[Any]]) -> list[dict[str, Any]]:
    if "site_A" not in values:
        return []
    site_a = np.asarray(values["site_A"], dtype=np.float64)
    training_mask = np.asarray(values["training_mask"], dtype=bool)
    arrival = np.asarray(values["true_arrival"], dtype=np.float64)
    extirpation = np.asarray(values["true_extirpation"], dtype=np.float64)
    train_a, hold_a = site_a[training_mask], site_a[~training_mask]
    overlap_min = max(float(train_a.min()), float(hold_a.min()))
    overlap_max = min(float(train_a.max()), float(hold_a.max()))
    rows: list[dict[str, Any]] = []
    for history in range(EXPECTED_HISTORY_COUNT):
        row_arrival, row_extirpation = arrival[history], extirpation[history]
        split = training_mask
        prearrival = row_arrival[:, None] > SURVEY_TIMES[None, :]
        alive_before_arrival = (
            np.minimum(row_arrival, row_extirpation)[:, None] > SURVEY_TIMES[None, :]
        )
        row: dict[str, Any] = {
            "history_index": history,
            "replicate_index": int(np.repeat(np.arange(6), 4)[history]),
            "cell_id": str(np.tile(np.asarray(REPLAY_CELL_IDS), 6)[history]),
            "A_train_min": float(train_a.min()),
            "A_train_max": float(train_a.max()),
            "A_holdout_min": float(hold_a.min()),
            "A_holdout_max": float(hold_a.max()),
            "A_overlap_min": overlap_min,
            "A_overlap_max": overlap_max,
            "A_overlap_exists": bool(overlap_min <= overlap_max),
            "training_finite_arrival_count": int(np.isfinite(row_arrival[split]).sum()),
            "holdout_finite_arrival_count": int(np.isfinite(row_arrival[~split]).sum()),
            "training_arrival_min": float(np.min(row_arrival[split])),
            "training_arrival_max": float(np.max(row_arrival[split])),
            "holdout_arrival_min": float(np.min(row_arrival[~split])),
            "holdout_arrival_max": float(np.max(row_arrival[~split])),
            "training_prearrival_survey_occasions": int(prearrival[split].sum()),
            "holdout_prearrival_survey_occasions": int(prearrival[~split].sum()),
            "training_alive_before_arrival_opportunities": int(alive_before_arrival[split].sum()),
            "holdout_alive_before_arrival_opportunities": int(alive_before_arrival[~split].sum()),
            "training_alive_before_arrival_site_count": int(
                alive_before_arrival[split].any(axis=1).sum()
            ),
            "holdout_alive_before_arrival_site_count": int(
                alive_before_arrival[~split].any(axis=1).sum()
            ),
            "training_continuous_latent_risk": float(
                np.minimum.reduce(
                    [row_arrival[split], row_extirpation[split], np.full(split.sum(), 60.0)]
                ).sum()
            ),
            "holdout_continuous_latent_risk": float(
                np.minimum.reduce(
                    [row_arrival[~split], row_extirpation[~split], np.full((~split).sum(), 60.0)]
                ).sum()
            ),
        }
        rows.append(row)
    return rows


def _write_figures(
    values: Mapping[str, NDArray[Any]], output: Path, rows: Sequence[Mapping[str, Any]]
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colours = {cell_id: plt.cm.tab10(index) for index, cell_id in enumerate(REPLAY_CELL_IDS)}
    fig, axes = plt.subplots(4, 2, figsize=(14, 16), squeeze=False, constrained_layout=True)
    for cell_id in REPLAY_CELL_IDS:
        subset = [row for row in rows if row["cell_id"] == cell_id]
        x = np.asarray([row["replicate_index"] for row in subset])
        row_index = REPLAY_CELL_IDS.index(cell_id)
        constant_style = {"color": colours[cell_id], "linestyle": "--", "marker": "o"}
        adjusted_style = {"color": colours[cell_id], "linestyle": "-", "marker": "o"}
        axes[row_index, 0].plot(
            x,
            [row["constant_fit_h"] for row in subset],
            label="constant h",
            **constant_style,
        )
        axes[row_index, 0].plot(
            x,
            [row["fit_h"] for row in subset],
            label="adjusted h",
            **adjusted_style,
        )
        axes[row_index, 1].plot(
            x,
            [row["holdout_adjusted_minus_fitted_adjustednull_conditional_prey"] for row in subset],
            label="adjusted vs adjusted-null",
            **adjusted_style,
        )
        axes[row_index, 1].plot(
            x,
            [row["holdout_constant_minus_constantnull_conditional_prey"] for row in subset],
            label="constant vs constant-null",
            **constant_style,
        )
        axes[row_index, 0].set_title(cell_id)
        axes[row_index, 1].set_title(cell_id)
        axes[row_index, 1].axhline(0.0, color="black", linewidth=0.7)
        axes[row_index, 0].set_ylabel("fitted h")
        axes[row_index, 1].set_ylabel("held-out conditional-prey advantage")
        axes[row_index, 0].legend(fontsize=8)
        axes[row_index, 1].legend(fontsize=8)
    for axis in axes[-1]:
        axis.set_xlabel("production replicate index")
    fig.suptitle("Goal 052 latent lane; descriptive six-block panel")
    for suffix in ("png", "pdf"):
        fig.savefig(output / f"primary_paired_comparison.{suffix}", dpi=180)
    plt.close(fig)

    for lane in ("latent", "oracle"):
        surfaces = np.asarray(values[f"{lane}_training"], dtype=np.float64)
        fig, axes = plt.subplots(4, 6, figsize=(18, 12), squeeze=False, constrained_layout=True)
        for cell_row in range(4):
            for replicate_column in range(6):
                history = replicate_column * 4 + cell_row
                axis = axes[cell_row, replicate_column]
                surface = surfaces[history]
                fit = maximum_on_grid(surface)
                lr = 2.0 * (fit.value - surface)
                with suppress(ValueError):
                    axis.contour(BETAS, EFFECTS, lr.T, levels=CONTOUR_LEVELS, linewidths=0.8)
                axis.axvline(0.0, color="black", linestyle=":", linewidth=0.6)
                truth_h = float(np.asarray(values["truth_h"])[history])
                axis.axhline(truth_h, color="tab:red", linestyle=":", linewidth=0.6)
                axis.plot(fit.beta, fit.h, marker="o", color="tab:blue", markersize=3)
                axis.set_title(
                    f"{values['cell_ids'][history]!s} r{int(values['replicate_indices'][history])}",
                    fontsize=8,
                )
                axis.set_xlim(BETAS[0], BETAS[-1])
                axis.set_ylim(EFFECTS[0], EFFECTS[-1])
                if cell_row == 3:
                    axis.set_xlabel("beta")
                if replicate_column == 0:
                    axis.set_ylabel("h")
        fig.suptitle(
            f"Goal 052 {lane} joint LR geometry; UNCALIBRATED, not 95% intervals",
            fontsize=14,
        )
        for suffix in ("png", "pdf"):
            fig.savefig(output / f"joint_contours_{lane}.{suffix}", dpi=180)
        plt.close(fig)


def _prediction_descriptives(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    aligned = [row for row in rows if row["cell_id"] == "B100-A_h1"]
    baseline_h3 = [row for row in rows if row["cell_id"] == "B_h3"]
    aligned_h3 = [row for row in rows if row["cell_id"] == "B100-A_h3"]
    latent = np.asarray([row["adjusted_minus_adjustednull_lr"] for row in rows], dtype=np.float64)
    oracle = np.asarray(
        [row["oracle_adjusted_minus_adjustednull_lr"] for row in rows], dtype=np.float64
    )
    latent_widths = np.asarray(
        [
            json.loads(row["h_profile_range_lr_le_2"])["max"]
            - json.loads(row["h_profile_range_lr_le_2"])["min"]
            for row in rows
        ],
        dtype=np.float64,
    )
    oracle_widths = np.asarray(
        [
            json.loads(row["oracle_h_profile_range_lr_le_2"])["max"]
            - json.loads(row["oracle_h_profile_range_lr_le_2"])["min"]
            for row in rows
        ],
        dtype=np.float64,
    )
    block_differences = [
        float(
            aligned_row["adjusted_minus_adjustednull_lr"]
            - baseline_row["adjusted_minus_adjustednull_lr"]
        )
        for baseline_row, aligned_row in zip(baseline_h3, aligned, strict=True)
    ]
    return {
        "interpretation": (
            "descriptive six-block comparisons only; no significance or population claim"
        ),
        "aligned_null_adjusted_minus_constant_h_mean": float(
            np.mean([row["fit_h"] - row["constant_fit_h"] for row in aligned])
        ),
        "aligned_null_adjusted_minus_constant_h_positive_count": int(
            sum(row["fit_h"] > row["constant_fit_h"] for row in aligned)
        ),
        "baseline_h3_adjusted_minus_constant_h_mean": float(
            np.mean([row["fit_h"] - row["constant_fit_h"] for row in baseline_h3])
        ),
        "aligned_h3_adjusted_minus_constant_h_mean": float(
            np.mean([row["fit_h"] - row["constant_fit_h"] for row in aligned_h3])
        ),
        "p2_baseline_h3_hhat_gt_one_count": int(sum(row["fit_h"] > 1.0 for row in baseline_h3)),
        "p2_aligned_null_h1_hhat_gt_one_count": int(
            sum(row["fit_h"] > 1.0 for row in aligned)
        ),
        "p2_baseline_h3_h_profile_lower_contact_count": int(
            sum(row["h_profile_touches_lower"] for row in baseline_h3)
        ),
        "p2_aligned_null_h1_h_profile_lower_contact_count": int(
            sum(row["h_profile_touches_lower"] for row in aligned)
        ),
        "p2_baseline_h3_adjusted_null_lr_mean": float(
            np.mean([row["adjusted_minus_adjustednull_lr"] for row in baseline_h3])
        ),
        "p2_aligned_null_h1_adjusted_null_lr_mean": float(
            np.mean([row["adjusted_minus_adjustednull_lr"] for row in aligned])
        ),
        "p2_aligned_null_h1_minus_baseline_h3_adjusted_null_lr_by_block": block_differences,
        "p2_aligned_null_h1_minus_baseline_h3_adjusted_null_lr_mean": float(
            np.mean(block_differences)
        ),
        "p3_h_profile_lr_le_2_narrower_oracle_than_latent_count": int(
            np.sum(oracle_widths < latent_widths)
        ),
        "p3_h_profile_lr_le_2_narrower_oracle_than_latent_mean_width_difference": float(
            np.mean(latent_widths - oracle_widths)
        ),
        "latent_vs_oracle_adjusted_null_lr_mean_difference": float(np.mean(oracle - latent)),
    }


def synthesize(evidence_path: Path, output_dir: Path) -> dict[str, Any]:
    """Summarize one frozen Goal052 evidence bundle into CSV, JSON and figures."""

    evidence_path = Path(evidence_path)
    output = Path(output_dir)
    if not evidence_path.is_file():
        raise ValueError(f"missing Goal052 evidence bundle: {evidence_path}")
    if (output / "summary.json").exists():
        raise ValueError(f"refusing to overwrite completed synthesis: {output}")
    with np.load(evidence_path, allow_pickle=False) as loaded:
        values = {name: np.asarray(loaded[name]).copy() for name in loaded.files}
    _validate_evidence(values)
    output.mkdir(parents=True, exist_ok=True)
    rows = _merge_lane_rows(values)
    metrics_path = output / "metrics.csv"
    summary_path = output / "cell_summary.csv"
    _write_csv(metrics_path, rows)
    _write_csv(summary_path, _cell_summary(rows))
    geometry_rows = _geometry_rows(values)
    geometry_path: Path | None = None
    if geometry_rows:
        geometry_path = output / "geometry_summary.csv"
        _write_csv(geometry_path, geometry_rows)
    _write_figures(values, output, _lane_rows(values, "latent"))
    output_paths = [
        metrics_path,
        summary_path,
        output / "primary_paired_comparison.png",
        output / "primary_paired_comparison.pdf",
        output / "joint_contours_latent.png",
        output / "joint_contours_latent.pdf",
        output / "joint_contours_oracle.png",
        output / "joint_contours_oracle.pdf",
    ]
    if geometry_path is not None:
        output_paths.append(geometry_path)
    output_hashes = {path.name: _sha256(path) for path in output_paths}
    edge_contact_counts = {
        lane: {
            name: int(sum(bool(row[f"{prefix}{name}"]) for row in rows))
            for name in (
                "fit_beta_lower_edge",
                "fit_beta_upper_edge",
                "fit_h_lower_edge",
                "fit_h_upper_edge",
            )
        }
        for lane, prefix in (("latent", ""), ("oracle", "oracle_"))
    }
    summary: dict[str, Any] = {
        "status": "complete_descriptive_uncalibrated_geometry",
        "input_path": str(evidence_path),
        "input_sha256": _sha256(evidence_path),
        "history_count": EXPECTED_HISTORY_COUNT,
        "cell_ids": list(REPLAY_CELL_IDS),
        "metrics_rows": len(rows),
        "geometry_included": bool(geometry_rows),
        "uncalibrated_boundary": (
            "LR contours and profile ranges are uncalibrated likelihood geometry, "
            "not 95% intervals; no recovery, coverage, power, or structural-identifiability claim."
        ),
        "scientific_scope": {
            "no_nonzero_beta_generating_positive_control_in_panel": True,
            "h_equals_one_boundary": (
                "physical h=1 contact is expected under a null and may be one-sided/truncated; "
                "h=1 contact at truth h=3 is reported as a warning, not a failure."
            ),
            "truth_beta_guides": (
                "not shown; the panel does not supply a true beta for B100-A histories"
            ),
        },
        "h_equals_one_at_truth_h3_warning_count": int(
            sum(row["fit_h"] == 1.0 and row["truth_h"] == 3.0 for row in rows)
        ),
        "fit_edge_contact_counts": edge_contact_counts,
        "prediction_descriptives": _prediction_descriptives(rows),
        "output_sha256": output_hashes,
    }
    _write_json(output / "summary.json", summary)
    return summary


__all__ = [
    "BETAS",
    "CONTOUR_LEVELS",
    "EFFECTS",
    "FitPoint",
    "maximum_on_grid",
    "profile_summary",
    "synthesize",
]
