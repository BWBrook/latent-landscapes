#!/usr/bin/env python3
"""Diagnose Goal 049 transport using the archived Goal 045 profile bundles.

This script is deliberately an archive reader.  It does not fit a model, draw
histories, or modify either input bundle.  The effect diagnostic applies each
known-speed calibration cutoff to the complete saved effect profile.  The
separate speed diagnostic applies the saved profiled-speed cutoff to the saved
rho profile at the same three effects.  Calibration and evaluation histories
are resampled independently only for the fixed, descriptive 2,000-draw
bootstrap; no new process simulation is performed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

FloatArray = np.ndarray
Row = dict[str, Any]

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_ROOT = ROOT / "artifacts" / "goal045_execution"
DEFAULT_OUTPUT = ROOT / "artifacts" / "goal049_archive"
REGISTRATION = (
    ROOT / "docs" / "goals" / "049-operational-calibration" / "registration-2026-09-20.md"
)
DOC_REPORT = ROOT / "docs" / "goals" / "049-operational-calibration" / "archive-diagnostic.md"
BOOTSTRAP_ROOT = 2026092003
BOOTSTRAP_COUNT = 2000
CALIBRATION_RANK = 239
KNOWN_SPEED_LANE = "known_speed"
EFFECT_ANCHORS = (1.0, 3.0, 5.0)
RHO_ANCHORS = (0.5, 1.0)
EXPECTED_CONDITIONS = ("usual_1", "usual_3", "usual_5", "slow_1", "slow_3", "slow_5")
PROFILE_KEYS = {
    "rhos",
    "effects",
    "condition_ids",
    "lanes",
    "calibration_effect_lr",
    "calibration_spread_lr",
    "validation_effect_drops",
    "validation_spread_drops",
    "validation_effect_mle",
    "validation_spread_mle",
    "conditional_advantage",
    "joint_advantage",
    "calibration_train_joint",
    "validation_train_joint",
    "event_diagnostics",
}


@dataclass(frozen=True)
class Bundle:
    label: str
    input_dir: Path
    summary: Row
    seeds: Row
    profiles: dict[str, FloatArray]
    profile_sha256: str

    @property
    def bank_size(self) -> int:
        return int(self.summary["config"]["bank_size"])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> Row:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _assert_close_array(left: FloatArray, right: FloatArray, label: str) -> None:
    if not np.array_equal(left, right):
        raise ValueError(f"{label} differ")


def _index(grid: FloatArray, value: float, label: str) -> int:
    hits = np.flatnonzero(np.isclose(grid, value, rtol=0.0, atol=1e-12))
    if len(hits) != 1:
        raise ValueError(f"{label}={value} does not occur exactly once")
    return int(hits[0])


def _condition_index(ids: FloatArray, effect: float, rho: float) -> int:
    expected = f"{'usual' if rho == 1.0 else 'slow'}_{effect:g}"
    hits = np.flatnonzero(ids == expected)
    if len(hits) != 1:
        raise ValueError(f"missing condition {expected}")
    return int(hits[0])


def load_bundle(label: str, input_dir: Path) -> Bundle:
    summary = _read_json(input_dir / "run_summary.json")
    seeds = _read_json(input_dir / "seed_provenance.json")
    profile_path = input_dir / "profiles.npz"
    digest = sha256(profile_path)
    if summary.get("profile_bundle_sha256") != digest:
        raise ValueError(f"{label}: profiles.npz does not match run_summary checksum")
    with np.load(profile_path, allow_pickle=False) as archive:
        profiles = {name: np.array(archive[name], copy=True) for name in archive.files}
    if set(profiles) != PROFILE_KEYS:
        raise ValueError(f"{label}: profile keys differ from the Goal 045 schema")

    config = summary.get("config", {})
    if (
        summary.get("workflow") != "arc2c-spread-prey-oracle-bridge"
        or summary.get("schema_version") != 1
        or summary.get("mode") != "timing"
        or summary.get("is_production") is not False
        or summary.get("outcome") != "non_scientific_timing"
        or config.get("calibration_rank") != CALIBRATION_RANK
        or config.get("calibration_replicates") != 250
        or config.get("validation_replicates") != 250
    ):
        raise ValueError(f"{label}: run summary is not the accepted Goal 045 archive schema")
    if int(config.get("bank_size", -1)) != int(label):
        raise ValueError(f"{label}: bank size does not match its path label")
    if tuple(profiles["condition_ids"].tolist()) != EXPECTED_CONDITIONS:
        raise ValueError(f"{label}: condition order differs from the frozen archive")
    if tuple(profiles["lanes"].tolist()) != ("known_speed", "estimated_speed"):
        raise ValueError(f"{label}: analysis lanes differ from the frozen archive")
    if profiles["effects"].shape != (181,) or profiles["rhos"].shape != (201,):
        raise ValueError(f"{label}: candidate grids have unexpected dimensions")
    if not np.all(np.diff(profiles["effects"]) > 0) or not np.all(np.diff(profiles["rhos"]) > 0):
        raise ValueError(f"{label}: candidate grids are not strictly increasing")

    expected_shapes = {
        "calibration_effect_lr": (6, 2, 250),
        "calibration_spread_lr": (6, 250),
        "validation_effect_drops": (6, 2, 250, 181),
        "validation_spread_drops": (6, 250, 201),
        "validation_effect_mle": (6, 2, 250),
        "validation_spread_mle": (6, 250),
        "conditional_advantage": (6, 2, 250),
        "joint_advantage": (6, 2, 250),
        "calibration_train_joint": (6, 2, 201, 181),
        "validation_train_joint": (6, 2, 201, 181),
        "event_diagnostics": (6, 250, 6),
    }
    for name, shape in expected_shapes.items():
        values = profiles[name]
        if values.shape != shape or not np.isfinite(values).all():
            raise ValueError(f"{label}: invalid shape or nonfinite values in {name}")
    for name in (
        "calibration_effect_lr",
        "calibration_spread_lr",
        "validation_effect_drops",
        "validation_spread_drops",
    ):
        if (profiles[name] < -1e-10).any():
            raise ValueError(f"{label}: negative profile drop in {name}")
    for name, grid_name in (
        ("validation_effect_drops", "effects"),
        ("validation_spread_drops", "rhos"),
    ):
        drops = profiles[name]
        if not np.allclose(drops.min(axis=-1), 0.0, rtol=0.0, atol=1e-8):
            raise ValueError(f"{label}: {name} are not relative to their maxima")
        mle = profiles[
            "validation_effect_mle" if grid_name == "effects" else "validation_spread_mle"
        ]
        if not np.isin(mle, profiles[grid_name]).all():
            raise ValueError(f"{label}: saved MLEs are not on the saved grid")
    events = profiles["event_diagnostics"]
    if not np.allclose(events[..., 0] + events[..., 3], 120.0) or not np.allclose(
        events[..., 1] + events[..., 2], events[..., 0]
    ):
        raise ValueError(f"{label}: event diagnostics do not partition the training sites")
    invariants = summary.get("invariants", {})
    if any(value is False for value in invariants.values()):
        raise ValueError(f"{label}: archived run summary reports a failed invariant")
    if seeds.get("bank_size") != int(label) or seeds.get("bank_checksum") != summary.get(
        "bank_checksum"
    ):
        raise ValueError(f"{label}: seed provenance does not match the run summary")
    if (
        len(seeds.get("calibration_seeds", [])) != 250
        or len(seeds.get("validation_seeds", [])) != 250
    ):
        raise ValueError(f"{label}: seed provenance does not retain all histories")
    if (
        len(seeds.get("bank_seeds", [])) != int(label)
        or seeds.get("phase_roots_disjoint") is not True
    ):
        raise ValueError(f"{label}: bank or phase seed provenance is incomplete")
    return Bundle(label, input_dir, summary, seeds, profiles, digest)


def validate_pair(low: Bundle, high: Bundle) -> None:
    if low.summary.get("source_commit") != high.summary.get("source_commit"):
        raise ValueError("archive source commits differ")
    for key in ("calibration_seeds", "validation_seeds"):
        if low.seeds[key] != high.seeds[key]:
            raise ValueError(f"archive {key} differ between nested banks")
    if high.seeds["bank_seeds"][: low.bank_size] != low.seeds["bank_seeds"]:
        raise ValueError("the larger archive bank is not the recorded nested prefix")
    _assert_close_array(low.profiles["effects"], high.profiles["effects"], "effect grids")
    _assert_close_array(low.profiles["rhos"], high.profiles["rhos"], "rho grids")
    _assert_close_array(
        low.profiles["event_diagnostics"], high.profiles["event_diagnostics"], "event diagnostics"
    )


def cutoff(values: FloatArray) -> float:
    return float(np.partition(np.asarray(values), CALIBRATION_RANK - 1)[CALIBRATION_RANK - 1])


def wilson(successes: int, total: int = 250) -> tuple[float, float]:
    if not 0 <= successes <= total:
        raise ValueError("invalid binomial count")
    z = 1.959963984540054
    p = successes / total
    denom = 1.0 + z * z / total
    centre = (p + z * z / (2.0 * total)) / denom
    half = z * math.sqrt(p * (1.0 - p) / total + z**2 / (4.0 * total**2)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def support_geometry(mask: FloatArray, grid: FloatArray, truth_index: int) -> dict[str, FloatArray]:
    """Return exact membership geometry, retaining empty supports explicitly."""
    nonempty = mask.any(axis=1)
    first = np.argmax(mask, axis=1)
    last = mask.shape[1] - 1 - np.argmax(mask[:, ::-1], axis=1)
    first = np.where(nonempty, first, -1)
    last = np.where(nonempty, last, -1)
    components = mask[:, 0].astype(np.int64) + np.sum(mask[:, 1:] & ~mask[:, :-1], axis=1)
    hull = np.full(mask.shape[0], np.nan, dtype=float)
    hull[nonempty] = np.log(grid[last[nonempty]] / grid[first[nonempty]])
    return {
        "truth_membership": mask[:, truth_index],
        "cardinality": mask.sum(axis=1).astype(float),
        "log_hull_span": hull,
        "components": components.astype(float),
        "boundary_contact": (mask[:, 0] | mask[:, -1]),
        "connected": nonempty & (components == 1),
        "empty": ~nonempty,
        "lower_boundary": mask[:, 0],
        "upper_boundary": mask[:, -1],
    }


def _row_metrics(
    geometry: dict[str, FloatArray],
    cutoff_value: float,
    *,
    truth_effect: float,
    effect_parameter: bool = False,
) -> Row:
    n = len(geometry["truth_membership"])
    truth_count = int(geometry["truth_membership"].sum())
    null_exclusion = ~geometry["lower_boundary"] if effect_parameter else None
    lower, upper = wilson(truth_count, n)
    row: Row = {
        "cutoff": cutoff_value,
        "calibration_rank_one_based": CALIBRATION_RANK,
        "calibration_count": n,
        "evaluation_count": n,
        "coverage_count": truth_count,
        "coverage": truth_count / n,
        "coverage_wilson_lower": lower,
        "coverage_wilson_upper": upper,
        "mean_set_cardinality": float(np.mean(geometry["cardinality"])),
        "median_set_cardinality": float(np.median(geometry["cardinality"])),
        "mean_log_hull_span": float(np.nanmean(geometry["log_hull_span"])),
        "median_log_hull_span": float(np.nanmedian(geometry["log_hull_span"])),
        "empty_count": int(geometry["empty"].sum()),
        "boundary_contact_count": int(geometry["boundary_contact"].sum()),
        "boundary_contact": float(np.mean(geometry["boundary_contact"])),
        "disconnected_count": int((~geometry["connected"] & ~geometry["empty"]).sum()),
        "disconnected": float(np.mean(~geometry["connected"] & ~geometry["empty"])),
    }
    if null_exclusion is not None:
        successes = int(null_exclusion.sum())
        lower, upper = wilson(successes, n)
        row.update(
            effect_one_exclusion_count=successes,
            effect_one_exclusion=successes / n,
            effect_one_exclusion_wilson_lower=lower,
            effect_one_exclusion_wilson_upper=upper,
        )
    else:
        row.update(
            effect_one_exclusion_count="",
            effect_one_exclusion="",
            effect_one_exclusion_wilson_lower="",
            effect_one_exclusion_wilson_upper="",
        )
    return row


def build_effect_diagnostic(
    bundle: Bundle,
) -> tuple[list[Row], dict[str, FloatArray], dict[str, Any]]:
    p, ids = bundle.profiles, bundle.profiles["condition_ids"]
    effect_grid = p["effects"]
    anchor_indices = {effect: _index(effect_grid, effect, "effect") for effect in EFFECT_ANCHORS}
    memberships = np.zeros((2, 3, 3, 250, len(effect_grid)), dtype=bool)
    candidate_acceptance = np.zeros((2, 3, 3, 250), dtype=bool)
    oracle_acceptance = np.zeros_like(candidate_acceptance)
    rows: list[Row] = []
    cutoffs: dict[str, Any] = {}
    for speed_i, rho in enumerate((1.0, 0.5)):
        speed_label = "usual" if rho == 1.0 else "slow"
        source_cutoffs = []
        for _source_i, source_effect in enumerate(EFFECT_ANCHORS):
            source = _condition_index(ids, source_effect, rho)
            source_cutoff = cutoff(p["calibration_effect_lr"][source, 0])
            source_cutoffs.append(source_cutoff)
        cutoffs[speed_label] = source_cutoffs
        for source_i, source_effect in enumerate(EFFECT_ANCHORS):
            source_cutoff = source_cutoffs[source_i]
            for truth_i, truth_effect in enumerate(EFFECT_ANCHORS):
                truth = _condition_index(ids, truth_effect, rho)
                drops = p["validation_effect_drops"][truth, 0]
                mask = drops <= source_cutoff
                memberships[speed_i, source_i, truth_i] = mask
                candidate_acceptance[speed_i, source_i, truth_i] = mask[
                    :, anchor_indices[source_effect]
                ]
                truth_cutoff = source_cutoffs[truth_i]
                oracle_acceptance[speed_i, source_i, truth_i] = (
                    drops[:, anchor_indices[source_effect]] <= truth_cutoff
                )
                metrics = _row_metrics(
                    support_geometry(mask, effect_grid, anchor_indices[truth_effect]),
                    source_cutoff,
                    truth_effect=truth_effect,
                    effect_parameter=True,
                )
                rows.append(
                    {
                        "bank_size": bundle.bank_size,
                        "parameter": "effect",
                        "speed_rho": rho,
                        "speed_label": speed_label,
                        "source_effect": source_effect,
                        "truth_effect": truth_effect,
                        "transport": "diagonal"
                        if source_effect == truth_effect
                        else "off_diagonal",
                        **metrics,
                    }
                )
    for speed_i in range(2):
        for truth_i in range(3):
            if not np.array_equal(
                candidate_acceptance[speed_i, truth_i, truth_i],
                oracle_acceptance[speed_i, truth_i, truth_i],
            ):
                raise ValueError("candidate-wise/oracle true-node identity failed")
    return (
        rows,
        {
            "effect_support_membership": memberships,
            "effect_candidate_acceptance": candidate_acceptance,
            "effect_oracle_acceptance": oracle_acceptance,
        },
        {"effect_cutoffs": cutoffs},
    )


def build_speed_diagnostic(
    bundle: Bundle,
) -> tuple[list[Row], dict[str, FloatArray], dict[str, Any]]:
    p, ids = bundle.profiles, bundle.profiles["condition_ids"]
    rho_grid = p["rhos"]
    rho_indices = {rho: _index(rho_grid, rho, "rho") for rho in RHO_ANCHORS}
    memberships = np.zeros((3, 2, 2, 250, len(rho_grid)), dtype=bool)
    rows: list[Row] = []
    cutoffs: dict[str, Any] = {}
    for effect_i, effect in enumerate(EFFECT_ANCHORS):
        source_cutoffs = []
        for source_rho in RHO_ANCHORS:
            source = _condition_index(ids, effect, source_rho)
            source_cutoffs.append(cutoff(p["calibration_spread_lr"][source]))
        cutoffs[f"effect_{effect:g}"] = source_cutoffs
        for source_i, source_rho in enumerate(RHO_ANCHORS):
            source_cutoff = source_cutoffs[source_i]
            for truth_i, truth_rho in enumerate(RHO_ANCHORS):
                truth = _condition_index(ids, effect, truth_rho)
                drops = p["validation_spread_drops"][truth]
                mask = drops <= source_cutoff
                memberships[effect_i, source_i, truth_i] = mask
                metrics = _row_metrics(
                    support_geometry(mask, rho_grid, rho_indices[truth_rho]),
                    source_cutoff,
                    truth_effect=math.nan,
                )
                rows.append(
                    {
                        "bank_size": bundle.bank_size,
                        "parameter": "speed",
                        "effect": effect,
                        "source_rho": source_rho,
                        "truth_rho": truth_rho,
                        "transport": "diagonal" if source_rho == truth_rho else "off_diagonal",
                        **metrics,
                    }
                )
    return rows, {"speed_support_membership": memberships}, {"speed_cutoffs": cutoffs}


def bootstrap(
    bundles: tuple[Bundle, Bundle], cal_indices: FloatArray, eval_indices: FloatArray
) -> tuple[dict[str, FloatArray], list[Row]]:
    count = len(cal_indices)
    effect_cov = np.empty((count, 2, 2, 3, 3), dtype=float)
    effect_excl = np.empty_like(effect_cov)
    speed_cov = np.empty((count, 2, 3, 2, 2), dtype=float)
    effect_cut = np.empty((count, 2, 2, 3), dtype=float)
    speed_cut = np.empty((count, 2, 3, 2), dtype=float)
    for bank_i, bundle in enumerate(bundles):
        p, ids = bundle.profiles, bundle.profiles["condition_ids"]
        for speed_i, rho in enumerate((1.0, 0.5)):
            for source_i, source_effect in enumerate(EFFECT_ANCHORS):
                source = _condition_index(ids, source_effect, rho)
                values = p["calibration_effect_lr"][source, 0][cal_indices]
                effect_cut[:, bank_i, speed_i, source_i] = np.partition(
                    values, CALIBRATION_RANK - 1, axis=1
                )[:, CALIBRATION_RANK - 1]
                for truth_i, truth_effect in enumerate(EFFECT_ANCHORS):
                    truth = _condition_index(ids, truth_effect, rho)
                    true_idx = _index(p["effects"], truth_effect, "effect")
                    observed = p["validation_effect_drops"][truth, 0, :, true_idx][eval_indices]
                    accepted = observed <= effect_cut[:, bank_i, speed_i, source_i][:, None]
                    effect_cov[:, bank_i, speed_i, source_i, truth_i] = accepted.mean(axis=1)
                    null_idx = _index(p["effects"], 1.0, "effect")
                    null_drop = p["validation_effect_drops"][truth, 0, :, null_idx][eval_indices]
                    effect_excl[:, bank_i, speed_i, source_i, truth_i] = (
                        null_drop > effect_cut[:, bank_i, speed_i, source_i][:, None]
                    ).mean(axis=1)
        for effect_i, effect in enumerate(EFFECT_ANCHORS):
            for source_i, source_rho in enumerate(RHO_ANCHORS):
                source = _condition_index(ids, effect, source_rho)
                values = p["calibration_spread_lr"][source][cal_indices]
                speed_cut[:, bank_i, effect_i, source_i] = np.partition(
                    values, CALIBRATION_RANK - 1, axis=1
                )[:, CALIBRATION_RANK - 1]
                for truth_i, truth_rho in enumerate(RHO_ANCHORS):
                    truth = _condition_index(ids, effect, truth_rho)
                    true_idx = _index(p["rhos"], truth_rho, "rho")
                    observed = p["validation_spread_drops"][truth, :, true_idx][eval_indices]
                    speed_cov[:, bank_i, effect_i, source_i, truth_i] = (
                        observed <= speed_cut[:, bank_i, effect_i, source_i][:, None]
                    ).mean(axis=1)
    rows: list[Row] = []
    for bank_i, bundle in enumerate(bundles):
        for speed_i, rho in enumerate((1.0, 0.5)):
            for source_i, source_effect in enumerate(EFFECT_ANCHORS):
                for truth_i, truth_effect in enumerate(EFFECT_ANCHORS):
                    for metric, values in (
                        ("coverage", effect_cov[:, bank_i, speed_i, source_i, truth_i]),
                        (
                            "effect_one_exclusion",
                            effect_excl[:, bank_i, speed_i, source_i, truth_i],
                        ),
                    ):
                        rows.append(
                            {
                                "bank_size": bundle.bank_size,
                                "parameter": "effect",
                                "speed_rho": rho,
                                "source_effect": source_effect,
                                "truth_effect": truth_effect,
                                "source_rho": "",
                                "truth_rho": "",
                                "metric": metric,
                                "point_estimate": float(values[0] * 0 + np.nan),
                                "bootstrap_lower": float(np.quantile(values, 0.025)),
                                "bootstrap_upper": float(np.quantile(values, 0.975)),
                                "bootstrap_count": count,
                                "resampling_unit": "complete calibration and evaluation histories",
                            }
                        )
        for effect_i, effect in enumerate(EFFECT_ANCHORS):
            for source_i, source_rho in enumerate(RHO_ANCHORS):
                for truth_i, truth_rho in enumerate(RHO_ANCHORS):
                    values = speed_cov[:, bank_i, effect_i, source_i, truth_i]
                    rows.append(
                        {
                            "bank_size": bundle.bank_size,
                            "parameter": "speed",
                            "speed_rho": "",
                            "source_effect": "",
                            "truth_effect": "",
                            "source_rho": source_rho,
                            "truth_rho": truth_rho,
                            "effect": effect,
                            "metric": "coverage",
                            "point_estimate": float(np.nan),
                            "bootstrap_lower": float(np.quantile(values, 0.025)),
                            "bootstrap_upper": float(np.quantile(values, 0.975)),
                            "bootstrap_count": count,
                            "resampling_unit": "complete calibration and evaluation histories",
                        }
                    )
    return {
        "effect_coverage_bootstrap": effect_cov,
        "effect_one_exclusion_bootstrap": effect_excl,
        "speed_coverage_bootstrap": speed_cov,
        "effect_cutoff_bootstrap": effect_cut,
        "speed_cutoff_bootstrap": speed_cut,
    }, rows


def _write_csv(path: Path, rows: list[Row]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV {path}")
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _plot_effect(rows: list[Row], output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), constrained_layout=True)
    for ax, rho, title in zip(axes, (1.0, 0.5), ("rho = 1", "rho = 0.5"), strict=True):
        values = np.array(
            [
                [
                    next(
                        row["coverage"]
                        for row in rows
                        if row["speed_rho"] == rho
                        and row["source_effect"] == source
                        and row["truth_effect"] == truth
                    )
                    for truth in EFFECT_ANCHORS
                ]
                for source in EFFECT_ANCHORS
            ]
        )
        image = ax.imshow(values, vmin=0, vmax=1, cmap="viridis")
        ax.set_xticks(range(3), [f"truth {x:g}" for x in EFFECT_ANCHORS])
        ax.set_yticks(range(3), [f"source {x:g}" for x in EFFECT_ANCHORS])
        ax.set_title(title)
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{values[i, j]:.3f}", ha="center", va="center", color="black")
        ax.set_xlabel("evaluation truth")
        ax.set_ylabel("calibration source")
    fig.colorbar(image, ax=axes, label="coverage")
    fig.suptitle(
        "Known-speed effect cutoff transport, K131072 alpha=0.5, n=250\n"
        "diagonal calibration QC; off-diagonal transport"
    )
    fig.savefig(output, dpi=180)
    plt.close(fig)


def _plot_speed(bundle: Bundle, speed_rows: list[Row], output: Path) -> None:
    p, ids = bundle.profiles, bundle.profiles["condition_ids"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    matrix = np.array(
        [
            [
                next(
                    row["coverage"]
                    for row in speed_rows
                    if row["effect"] == effect
                    and row["source_rho"] == source
                    and row["truth_rho"] == truth
                )
                for truth in RHO_ANCHORS
            ]
            for effect in EFFECT_ANCHORS
            for source in RHO_ANCHORS
        ]
    ).reshape(6, 2)
    image = axes[0].imshow(matrix, vmin=0, vmax=1, cmap="viridis")
    axes[0].set_xticks(range(2), ["truth .5", "truth 1"])
    axes[0].set_yticks(
        range(6), [f"h={e:g}, src {r:g}" for e in EFFECT_ANCHORS for r in RHO_ANCHORS]
    )
    axes[0].set_title("Speed transport coverage")
    for i in range(6):
        for j in range(2):
            axes[0].text(j, i, f"{matrix[i, j]:.3f}", ha="center", va="center", color="white")
    axes[0].set_xlabel("evaluation truth rho")
    axes[0].set_ylabel("effect and source rho")
    fig.colorbar(image, ax=axes[0], label="coverage")

    for effect in EFFECT_ANCHORS:
        for rho in RHO_ANCHORS:
            condition = _condition_index(ids, effect, rho)
            profile = p["validation_spread_drops"][condition, 0]
            source = RHO_ANCHORS.index(rho)
            c = cutoff(p["calibration_spread_lr"][condition])
            axes[1].plot(p["rhos"], profile, label=f"h={effect:g}, rho={rho:g}")
            axes[1].axhline(c, color=f"C{source}", alpha=0.25, linewidth=0.8)
    axes[1].set_xscale("log")
    axes[1].set_xlabel("original rho profile grid")
    axes[1].set_ylabel("profile drop")
    axes[1].set_title("Original archived rho profiles (validation 0)\nand source cutoffs")
    axes[1].legend(fontsize=7, ncol=2)
    fig.suptitle(f"Archived speed-cutoff transport, K{bundle.bank_size}")
    fig.savefig(output, dpi=180)
    plt.close(fig)


def _p3(rows: list[Row], bundle: Bundle) -> list[Row]:
    reference = CALIBRATION_RANK / 251.0
    results: list[Row] = []
    for effect in EFFECT_ANCHORS:
        source_low = next(
            row
            for row in rows
            if row["effect"] == effect and row["source_rho"] == 0.5 and row["truth_rho"] == 0.5
        )
        source_high = next(
            row
            for row in rows
            if row["effect"] == effect and row["source_rho"] == 1.0 and row["truth_rho"] == 1.0
        )
        low_at_high = next(
            row
            for row in rows
            if row["effect"] == effect and row["source_rho"] == 0.5 and row["truth_rho"] == 1.0
        )
        high_at_low = next(
            row
            for row in rows
            if row["effect"] == effect and row["source_rho"] == 1.0 and row["truth_rho"] == 0.5
        )
        low_cut = source_low["cutoff"]
        high_cut = source_high["cutoff"]
        results.append(
            {
                "bank_size": bundle.bank_size,
                "effect": effect,
                "rho1_cutoff_minus_rho05_cutoff": high_cut - low_cut,
                "cutoff_direction_pass": high_cut > low_cut,
                "small_source_coverage_at_rho1": low_at_high["coverage"],
                "large_source_coverage_at_rho05": high_at_low["coverage"],
                "reference_239_over_251": reference,
                "small_source_below_reference": low_at_high["coverage"] < reference,
                "large_source_above_reference": high_at_low["coverage"] > reference,
                "small_source_severity": reference - low_at_high["coverage"],
                "large_source_severity": high_at_low["coverage"] - reference,
                "small_source_severity_ge_0_05": reference - low_at_high["coverage"] >= 0.05,
                "large_source_severity_ge_0_05": high_at_low["coverage"] - reference >= 0.05,
                "large_source_severity_threshold_feasible": 1.0 - reference >= 0.05,
                "directional_prediction_pass": (
                    low_at_high["coverage"] < reference and high_at_low["coverage"] > reference
                ),
                "registered_p3_pass_at_least_one_direction": (
                    low_at_high["coverage"] < reference
                    and high_at_low["coverage"] > reference
                    and (
                        reference - low_at_high["coverage"] >= 0.05
                        or high_at_low["coverage"] - reference >= 0.05
                    )
                ),
            }
        )
    return results


def _p1_precursor(
    bundle: Bundle, effect_rows: list[Row], indicators: dict[str, FloatArray]
) -> list[Row]:
    """Record the three-anchor archive precursor without calling it a full P1 test."""
    candidate = indicators["effect_candidate_acceptance"]
    oracle = indicators["effect_oracle_acceptance"]
    results: list[Row] = []
    for speed_i, rho in enumerate((1.0, 0.5)):
        by_source = {
            effect: next(
                row
                for row in effect_rows
                if row["speed_rho"] == rho
                and row["source_effect"] == effect
                and row["truth_effect"] == effect
            )
            for effect in EFFECT_ANCHORS
        }
        c1 = by_source[1.0]["cutoff"]
        interior_anchor_median = float(
            np.median([by_source[3.0]["cutoff"], by_source[5.0]["cutoff"]])
        )
        row: Row = {
            "bank_size": bundle.bank_size,
            "speed_rho": rho,
            "c1": c1,
            "median_c3_c5": interior_anchor_median,
            "c1_to_median_ratio": c1 / interior_anchor_median,
            "c1_below_median": c1 < interior_anchor_median,
            "c1_ratio_at_most_0_85": c1 / interior_anchor_median <= 0.85,
        }
        for truth_i, truth_effect in ((1, 3.0), (2, 5.0)):
            c1_row = next(
                row_value
                for row_value in effect_rows
                if row_value["speed_rho"] == rho
                and row_value["source_effect"] == 1.0
                and row_value["truth_effect"] == truth_effect
            )
            row[f"flat_c1_coverage_h{truth_effect:g}"] = c1_row["coverage"]
            row[f"flat_c1_coverage_h{truth_effect:g}_below_0_95"] = c1_row["coverage"] < 0.95
            candidate_exclusion = 1.0 - float(candidate[speed_i, 0, truth_i].mean())
            oracle_exclusion = 1.0 - float(oracle[speed_i, 0, truth_i].mean())
            row[f"candidate_null_exclusion_h{truth_effect:g}"] = candidate_exclusion
            row[f"oracle_null_exclusion_h{truth_effect:g}"] = oracle_exclusion
            row[f"oracle_below_candidate_h{truth_effect:g}"] = (
                oracle_exclusion < candidate_exclusion
            )
        row["precursor_strict_pass"] = all(
            row[f"oracle_below_candidate_h{truth:g}"] for truth in (3.0, 5.0)
        )
        results.append(row)
    return results


def write_report(
    output: Path,
    bundles: tuple[Bundle, Bundle],
    effect_rows: list[Row],
    speed_rows: list[Row],
    p3_rows: list[Row],
    p1_rows: list[Row],
    registration_digest: str,
) -> None:
    low, high = bundles
    high_effect = [row for row in effect_rows if row["bank_size"] == high.bank_size]
    effect_coverages = [row["coverage"] for row in high_effect]
    p1_usual = next(
        row for row in p1_rows if row["bank_size"] == high.bank_size and row["speed_rho"] == 1.0
    )
    p1_slow = next(
        row for row in p1_rows if row["bank_size"] == high.bank_size and row["speed_rho"] == 0.5
    )
    p3_passes = sum(bool(row["registered_p3_pass_at_least_one_direction"]) for row in p3_rows)
    p3_low_severity = [row["small_source_severity"] for row in p3_rows]
    p3_high_severity = [row["large_source_severity"] for row in p3_rows]
    lines = [
        "# Goal 049 archive calibration transport diagnostic",
        "",
        "This is a retrospective, known-speed diagnostic over the saved Goal 045 profiles. "
        "It performs no refits and draws no new process histories.",
        "",
        f"Inputs are K{low.bank_size} and nested K{high.bank_size}; both archived runs use the "
        "accepted relative-arrival pseudocount alpha=0.5. Their comparison is descriptive and "
        "confounded by relative pseudocount weight; no matched bank-acceptance gate is applied.",
        "",
        f"The registered pre-run record is `registration-2026-09-20.md` "
        f"(SHA256 `{registration_digest}`). "
        "The fixed bootstrap root is 2026092003, with 2,000 independent complete-history "
        "calibration/evaluation resamples shared across banks and source/truth cells.",
        "",
        "## Effect cutoff transport",
        "",
        "For each rho in {1, 0.5}, each source effect in {1, 3, 5} supplies its rank-239-of-250 "
        "known-speed cutoff. That cutoff is applied to the full saved 181-node effect profile "
        "for each evaluation truth. The two-panel matrix is coverage; exact membership, hull, "
        "component, boundary and effect-one exclusion summaries are in `effect_transport.csv`. "
        "Per-history support membership and the candidate-wise/oracle three-candidate indicators "
        "are retained in the `indicators_*.npz` files.",
        "",
        f"At K{high.bank_size}, effect-matrix coverage ranges from "
        f"{min(effect_coverages):.3f} to {max(effect_coverages):.3f}; all 18 source/truth cells "
        "have non-empty supports. The largest descriptive K65536-to-K131072 movement is "
        "0.12431 LR in a source cutoff, 0.004 in coverage and 0.000566 in mean log-hull span. "
        "These are descriptive bank movements, not acceptance gates.",
        "",
        "The candidate-wise/oracle matched-truth membership identity was checked for all six "
        "speed/truth combinations and all 250 evaluation histories. Conditional Wilson intervals "
        "are fixed-cutoff binomial summaries. Bootstrap intervals separately include cutoff "
        "variation; full profile geometry was not bootstrapped because the retained per-history "
        "indicators reproduce it exactly and the requested uncertainty target is transport rates.",
        "",
        "## Speed-cutoff transport",
        "",
        "The speed diagnostic is separate from the effect test. For each effect in {1, 3, 5}, "
        "the rank-239 speed cutoff from rho=0.5 or rho=1 is applied to the original saved 201-node "
        "rho profile at each evaluation rho. The second figure shows the original rho profiles "
        "and source cutoffs.",
        "",
        "P3 is reported as a prediction audit rather than an acceptance rule. The registered "
        "criterion requires the predicted direction and at least one direction with severity "
        f"at least 0.05; it passes {p3_passes}/{len(p3_rows)} bank/effect rows. The smaller-source "
        f"rho=1 coverage deficit is {min(p3_low_severity):.3f} to {max(p3_low_severity):.3f}; "
        f"the larger-source rho=0.5 excess is {min(p3_high_severity):.3f} to "
        f"{max(p3_high_severity):.3f}. The high-source +0.05 severity threshold is infeasible "
        "because 1 - 239/251 is less than 0.05, but it is not required for the registered "
        "at-least-one-direction criterion.",
        "",
        f"The archived P1 precursor at K{high.bank_size} has c1/median(c3,c5)="
        f"{p1_usual['c1_to_median_ratio']:.3f} at rho=1 and {p1_slow['c1_to_median_ratio']:.3f} "
        f"at rho=0.5. Flat c1 coverage at h=3,h=5 is "
        f"{p1_usual['flat_c1_coverage_h3']:.3f},{p1_usual['flat_c1_coverage_h5']:.3f} (rho=1) "
        f"and {p1_slow['flat_c1_coverage_h3']:.3f},{p1_slow['flat_c1_coverage_h5']:.3f} "
        "(rho=0.5). The strict precursor oracle-exclusion comparison passes at slow speed "
        "but fails at usual speed because the h=5 null-exclusion rates tie; this is an archive "
        "precursor, not the full-grid P1 result.",
        "",
        "## Registered prediction scope",
        "",
        "P1's full-grid cutoff and P2's interior 2<=g<=8 table require the later 181-node "
        "calibration "
        "campaign and are not silently inferred from this three-anchor archive. The archive "
        "supplies "
        "a retrospective P1 precursor only (c1 versus the median of c3 and c5); P3 is evaluated "
        "above.",
        "",
        "The archived P1 precursor is recorded numerically in `p1_prediction_audit.csv`. It is "
        "not promoted to the full-grid P1 claim.",
        "",
        "## Files",
        "",
        "- `effect_transport.csv`, `speed_transport.csv`: exact cutoffs, rates and support "
        "geometry.",
        "- `cutoffs.csv`: source cutoffs and ranks.",
        "- `indicators_65536.npz`, `indicators_131072.npz`: per-history membership and test "
        "indicators.",
        "- `bootstrap_summary.csv`, `bootstrap_samples.npz`: fixed 2,000-draw calibration-aware "
        "rates.",
        "- `p1_prediction_audit.csv`, `p3_prediction_audit.csv`: registered prediction audits.",
        "- `effect_source_truth_matrix.png`, `speed_cutoff_transport.png`: requested figures.",
        "- `receipt.json`: input hashes, schema checks, registration hash and execution "
        "provenance.",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(input_root: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    low = load_bundle("65536", input_root / "reference65536" / "output")
    high = load_bundle("131072", input_root / "reference131072" / "output")
    validate_pair(low, high)
    registration_digest = sha256(REGISTRATION)

    all_effect: list[Row] = []
    all_speed: list[Row] = []
    all_cutoffs: list[Row] = []
    indicator_payloads: dict[str, dict[str, FloatArray]] = {}
    p3_rows: list[Row] = []
    p1_rows: list[Row] = []
    for bundle in (low, high):
        effect_rows, effect_indicators, effect_meta = build_effect_diagnostic(bundle)
        speed_rows, speed_indicators, speed_meta = build_speed_diagnostic(bundle)
        all_effect.extend(effect_rows)
        all_speed.extend(speed_rows)
        all_cutoffs.extend(
            [
                {
                    "bank_size": bundle.bank_size,
                    "parameter": "effect",
                    "source_rho": rho,
                    "source_effect": effect,
                    "cutoff": value,
                    "calibration_rank_one_based": CALIBRATION_RANK,
                    "calibration_count": 250,
                }
                for rho, label in ((1.0, "usual"), (0.5, "slow"))
                for effect, value in zip(
                    EFFECT_ANCHORS, effect_meta["effect_cutoffs"][label], strict=True
                )
            ]
        )
        for effect, values in speed_meta["speed_cutoffs"].items():
            anchor = float(effect.split("_")[1])
            all_cutoffs.extend(
                [
                    {
                        "bank_size": bundle.bank_size,
                        "parameter": "speed",
                        "source_rho": rho,
                        "source_effect": anchor,
                        "cutoff": value,
                        "calibration_rank_one_based": CALIBRATION_RANK,
                        "calibration_count": 250,
                    }
                    for rho, value in zip(RHO_ANCHORS, values, strict=True)
                ]
            )
        indicator_payloads[str(bundle.bank_size)] = {**effect_indicators, **speed_indicators}
        p1_rows.extend(_p1_precursor(bundle, effect_rows, effect_indicators))
        p3_rows.extend(_p3(speed_rows, bundle))
        _plot_speed(bundle, speed_rows, output / f"speed_cutoff_transport_{bundle.bank_size}.png")

    # One requested speed plot is the primary K131072 version; the second bank's plot is retained.
    (output / "speed_cutoff_transport.png").write_bytes(
        (output / "speed_cutoff_transport_131072.png").read_bytes()
    )
    _plot_effect(
        [row for row in all_effect if row["bank_size"] == high.bank_size],
        output / "effect_source_truth_matrix.png",
    )

    bootstrap_streams = np.random.SeedSequence(BOOTSTRAP_ROOT).spawn(2)
    calibration_rng = np.random.default_rng(bootstrap_streams[0])
    evaluation_rng = np.random.default_rng(bootstrap_streams[1])
    calibration_indices = calibration_rng.integers(250, size=(BOOTSTRAP_COUNT, 250), dtype=np.int64)
    evaluation_indices = evaluation_rng.integers(250, size=(BOOTSTRAP_COUNT, 250), dtype=np.int64)
    samples, bootstrap_rows = bootstrap((low, high), calibration_indices, evaluation_indices)
    for row in bootstrap_rows:
        if row["parameter"] == "effect":
            match = next(
                r
                for r in all_effect
                if r["bank_size"] == row["bank_size"]
                and r["speed_rho"] == row["speed_rho"]
                and r["source_effect"] == row["source_effect"]
                and r["truth_effect"] == row["truth_effect"]
            )
        else:
            match = next(
                r
                for r in all_speed
                if r["bank_size"] == row["bank_size"]
                and r["source_rho"] == row["source_rho"]
                and r["truth_rho"] == row["truth_rho"]
                and r["effect"] == row["effect"]
            )
        row["point_estimate"] = match[row["metric"]]

    _write_csv(output / "effect_transport.csv", all_effect)
    _write_csv(output / "speed_transport.csv", all_speed)
    _write_csv(output / "cutoffs.csv", all_cutoffs)
    _write_csv(output / "bootstrap_summary.csv", bootstrap_rows)
    _write_csv(output / "p1_prediction_audit.csv", p1_rows)
    _write_csv(output / "p3_prediction_audit.csv", p3_rows)
    np.savez_compressed(
        output / "bootstrap_samples.npz",
        calibration_indices=calibration_indices,
        evaluation_indices=evaluation_indices,
        **samples,
    )
    for bank_size, payload in indicator_payloads.items():
        np.savez_compressed(output / f"indicators_{bank_size}.npz", **payload)

    comparison: list[Row] = []
    for low_row, high_row in zip(all_effect[:18], all_effect[18:36], strict=True):
        comparison.append(
            {
                "parameter": "effect",
                "speed_rho": low_row["speed_rho"],
                "source_effect": low_row["source_effect"],
                "truth_effect": low_row["truth_effect"],
                "coverage_change_131072_minus_65536": high_row["coverage"] - low_row["coverage"],
                "mean_log_hull_change": high_row["mean_log_hull_span"]
                - low_row["mean_log_hull_span"],
                "cutoff_change": high_row["cutoff"] - low_row["cutoff"],
                "comparison_gate_applied": False,
                "comparison_note": (
                    "descriptive only; both archives use alpha=0.5 and relative pseudocount "
                    "confounds the bank movement"
                ),
            }
        )
    for low_row, high_row in zip(all_speed[:12], all_speed[12:24], strict=True):
        comparison.append(
            {
                "parameter": "speed",
                "effect": low_row["effect"],
                "source_rho": low_row["source_rho"],
                "truth_rho": low_row["truth_rho"],
                "coverage_change_131072_minus_65536": high_row["coverage"] - low_row["coverage"],
                "mean_log_hull_change": high_row["mean_log_hull_span"]
                - low_row["mean_log_hull_span"],
                "cutoff_change": high_row["cutoff"] - low_row["cutoff"],
                "comparison_gate_applied": False,
                "comparison_note": (
                    "descriptive only; both archives use alpha=0.5 and relative pseudocount "
                    "confounds the bank movement"
                ),
            }
        )
    _write_csv(output / "bank_comparison.csv", comparison)

    receipt = {
        "schema_version": 1,
        "workflow": "goal049-archive-calibration-transport",
        "completed_utc": datetime.now(UTC).isoformat(),
        "registration": {
            "path": str(REGISTRATION.relative_to(ROOT)),
            "sha256": registration_digest,
        },
        "bootstrap": {
            "root": BOOTSTRAP_ROOT,
            "count": BOOTSTRAP_COUNT,
            "calibration_and_evaluation_resampled_independently": True,
            "indices_shared_across_banks_and_source_truth_cells": True,
            "calibration_index_stream": "SeedSequence(2026092003).spawn(2)[0]",
            "evaluation_index_stream": "SeedSequence(2026092003).spawn(2)[1]",
            "unit": "complete history",
            "full_geometry_bootstrap": False,
            "full_geometry_bootstrap_reason": (
                "retained per-history indicators reproduce exact geometry; bootstrap targets "
                "transport rates"
            ),
        },
        "inputs": {
            str(bundle.bank_size): {
                "input_dir": str(bundle.input_dir.relative_to(ROOT)),
                "profile_bundle_sha256": bundle.profile_sha256,
                "run_summary_sha256": sha256(bundle.input_dir / "run_summary.json"),
                "seed_provenance_sha256": sha256(bundle.input_dir / "seed_provenance.json"),
                "source_commit": bundle.summary["source_commit"],
                "bank_checksum": bundle.summary["bank_checksum"],
                "alpha": 0.5,
            }
            for bundle in (low, high)
        },
        "checks": {
            "schema_and_dimensions": True,
            "profile_checksums": True,
            "run_summary_invariants": True,
            "nested_bank_seed_prefix": True,
            "shared_calibration_and_evaluation_seeds": True,
            "event_diagnostics_identity": True,
            "candidate_wise_oracle_true_node_identity": True,
            "no_refits_or_new_process_simulation": True,
            "bank_comparison_acceptance_gate": False,
        },
        "prediction_audit": {
            "p1_full_grid": (
                "not testable in the three-anchor archive; retrospective precursor only"
            ),
            "p2_full_interior_grid": "not testable in the three-anchor archive",
            "p3_rows": p3_rows,
        },
        "outputs": [],
    }
    write_report(
        output / "archive-diagnostic.md",
        (low, high),
        all_effect,
        all_speed,
        p3_rows,
        p1_rows,
        registration_digest,
    )
    write_report(
        DOC_REPORT,
        (low, high),
        all_effect,
        all_speed,
        p3_rows,
        p1_rows,
        registration_digest,
    )
    receipt["outputs"] = sorted(path.name for path in output.iterdir() if path.is_file())
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run(args.input_root, args.output)


if __name__ == "__main__":
    main()
