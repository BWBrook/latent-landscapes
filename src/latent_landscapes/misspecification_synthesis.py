"""Goal 051 paired synthesis for the frozen misspecification screen.

The independent unit is a complete simulated history.  Bootstrap draws resample
one replicate index jointly across all 17 cells; the frozen Goal 049/050 score
references and LR cutoffs are never resampled.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal002.calibration import wilson_interval
from latent_landscapes.model_adequacy_synthesis import (
    REJECTION_LEVEL,
    berger_boos_pvalues,
    conservative_lower_tail_pvalues,
)

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
IntArray = NDArray[np.int64]

REPLICATES = 1000
NODES = 181
BOOTSTRAP_DRAWS = 1000
BOOTSTRAP_SEED = 2026092304
MATERIAL_FACTOR = 1.5
NOMINATION_DELTA = 0.05

CELL_IDS = (
    "B_h1",
    "B_h3",
    "B_h5",
    "D10_h1",
    "D10_h3",
    "D10_h5",
    "D20_h1",
    "D20_h3",
    "D20_h5",
    "PD10_h1",
    "PD10_h3",
    "PD10_h5",
    "B50-I_h1",
    "B100-I_h1",
    "B50-A_h1",
    "B100-A_h1",
    "B100-A_h3",
)
TRUTHS = np.asarray((1, 3, 5, 1, 3, 5, 1, 3, 5, 1, 3, 5, 1, 1, 1, 1, 3), dtype=np.float64)
BASELINE_BY_CELL = {
    cell_id: f"B_h{int(truth)}" for cell_id, truth in zip(CELL_IDS, TRUTHS, strict=True)
}
CLASS_BY_CELL = {
    **{cell_id: "baseline" for cell_id in CELL_IDS[:3]},
    **{cell_id: "prey_detection" for cell_id in CELL_IDS[3:9]},
    **{cell_id: "predator_detection" for cell_id in CELL_IDS[9:12]},
    **{cell_id: "background" for cell_id in CELL_IDS[12:]},
}

BINARY_METRICS = (
    "H_primary",
    "H_plugin",
    "M",
    "M_truth_excluded",
    "M_point_error",
    "M_caught_primary",
    "M_caught_plugin",
    "primary_rejection",
    "plugin_rejection",
    "truth_inclusion",
    "c99_truth_inclusion",
    "effect_disconnected",
    "effect_boundary_contact",
    "strict_false_effect",
    "strict_false_effect_unflagged",
    "strict_false_effect_unflagged_plugin",
)
CONTINUOUS_METRICS = (
    "signed_log_bias",
    "absolute_log_error",
    "fitted_h",
    "effect_log_width",
    "effect_cardinality",
    "effect_components",
    "effect_raw_span",
    "prey_score",
    "training_predator_score",
    "recovered_holdout_predator_score",
)
METRICS = BINARY_METRICS + CONTINUOUS_METRICS


@dataclass(frozen=True)
class SynthesisResult:
    summary: dict[str, Any]
    cell_rows: list[dict[str, Any]]
    contrast_rows: list[dict[str, Any]]
    prediction_rows: list[dict[str, Any]]
    evidence: dict[str, FloatArray | BoolArray | IntArray]
    bootstrap_indices: IntArray
    bootstrap_cell_means: FloatArray
    bootstrap_deltas: FloatArray


def _components(mask: BoolArray) -> IntArray:
    return mask[:, 0].astype(np.int64) + np.sum(mask[:, 1:] & ~mask[:, :-1], axis=1)


def _truth_indices(effects: FloatArray, truths: FloatArray) -> IntArray:
    indices = []
    for truth in truths:
        matched = np.flatnonzero(np.isclose(effects, truth, rtol=0, atol=1e-12))
        if len(matched) != 1:
            raise ValueError(f"truth {truth:g} is not represented exactly once on the effect grid")
        indices.append(int(matched[0]))
    return np.asarray(indices, dtype=np.int64)


def evaluate_histories(
    effects: FloatArray,
    truths: FloatArray,
    profiles: FloatArray,
    prey_score: FloatArray,
    predator_score: FloatArray,
    mle_index: IntArray,
    holdout_joint: FloatArray,
    reference_scores: FloatArray,
    effect_cutoffs: FloatArray,
    c99_cutoffs: FloatArray,
) -> dict[str, FloatArray | BoolArray | IntArray]:
    """Evaluate frozen effect sets, primary detector, and plug-in diagnostic."""
    effects = np.asarray(effects, dtype=np.float64)
    truths = np.asarray(truths, dtype=np.float64)
    profiles = np.asarray(profiles, dtype=np.float64)
    prey_score = np.asarray(prey_score, dtype=np.float64)
    predator_score = np.asarray(predator_score, dtype=np.float64)
    mle_index = np.asarray(mle_index, dtype=np.int64)
    holdout_joint = np.asarray(holdout_joint, dtype=np.float64)
    reference_scores = np.asarray(reference_scores, dtype=np.float64)
    effect_cutoffs = np.asarray(effect_cutoffs, dtype=np.float64)
    c99_cutoffs = np.asarray(c99_cutoffs, dtype=np.float64)
    cells, replicates, nodes = profiles.shape
    expected = {
        "truths": (cells,),
        "prey_score": (cells, replicates),
        "predator_score": (cells, replicates),
        "mle_index": (cells, replicates),
        "holdout_joint": (cells, replicates, nodes),
        "reference_scores": (nodes, 999),
        "effect_cutoffs": (nodes,),
        "c99_cutoffs": (nodes,),
    }
    supplied = locals()
    for name, shape in expected.items():
        if np.asarray(supplied[name]).shape != shape:
            observed_shape = np.asarray(supplied[name]).shape
            raise ValueError(f"{name} must have shape {shape}, got {observed_shape}")
    numeric = (
        effects,
        profiles,
        prey_score,
        predator_score,
        holdout_joint,
        reference_scores,
        effect_cutoffs,
        c99_cutoffs,
    )
    if not all(np.isfinite(value).all() for value in numeric):
        raise ValueError("synthesis inputs must be finite")
    if (profiles < 0).any() or (effect_cutoffs < 0).any() or (c99_cutoffs < 0).any():
        raise ValueError("LR profiles and cutoffs must be nonnegative")
    if not np.array_equal(mle_index, np.argmin(profiles, axis=-1)):
        raise ValueError("mle_index must use the lowest-index profile minimum")
    selected_joint = np.take_along_axis(holdout_joint, mle_index[..., None], axis=-1)[..., 0]

    truth_index = _truth_indices(effects, truths)
    effect_member = profiles <= effect_cutoffs
    c99_member = profiles <= c99_cutoffs
    if not effect_member.any(axis=-1).all() or not c99_member.any(axis=-1).all():
        raise ValueError("a frozen confidence/effect set is empty")
    if not np.take_along_axis(c99_member, mle_index[..., None], axis=-1)[..., 0].all():
        raise ValueError("C99 does not contain a fitted node")

    candidate_p = conservative_lower_tail_pvalues(reference_scores, prey_score)
    p_bb, checked_c99 = berger_boos_pvalues(candidate_p, profiles, c99_cutoffs)
    if not np.array_equal(c99_member, checked_c99):
        raise AssertionError("C99 evaluation disagrees with the frozen detector helper")
    plugin_p = np.take_along_axis(candidate_p, mle_index[..., None], axis=-1)[..., 0]
    primary_rejection = p_bb <= REJECTION_LEVEL
    plugin_rejection = plugin_p <= REJECTION_LEVEL
    if np.any(primary_rejection & ~plugin_rejection):
        raise ValueError("primary rejection must be nested inside plug-in rejection")

    rows = np.arange(cells)[:, None]
    reps = np.arange(replicates)[None, :]
    truth_inclusion = effect_member[rows, reps, truth_index[:, None]]
    c99_truth = c99_member[rows, reps, truth_index[:, None]]
    truth_excluded = ~truth_inclusion
    fitted_h = effects[mle_index]
    signed_bias = np.log(fitted_h / truths[:, None])
    point_error = np.abs(signed_bias) >= np.log(MATERIAL_FACTOR)
    misleading = truth_excluded | point_error
    hidden = misleading & ~primary_rejection
    hidden_plugin = misleading & ~plugin_rejection
    strict_false = truth_excluded & (fitted_h >= MATERIAL_FACTOR) & (truths[:, None] == 1.0)

    first = np.argmax(effect_member, axis=-1)
    last = nodes - 1 - np.argmax(effect_member[..., ::-1], axis=-1)
    component_count = np.empty((cells, replicates), dtype=np.int64)
    for cell in range(cells):
        component_count[cell] = _components(effect_member[cell])
    return {
        "candidate_p": candidate_p,
        "p_bb": p_bb,
        "plugin_p": plugin_p,
        "effect_membership": effect_member,
        "c99_membership": c99_member,
        "H_primary": hidden,
        "H_plugin": hidden_plugin,
        "M": misleading,
        "M_truth_excluded": truth_excluded,
        "M_point_error": point_error,
        "M_caught_primary": misleading & primary_rejection,
        "M_caught_plugin": misleading & plugin_rejection,
        "primary_rejection": primary_rejection,
        "plugin_rejection": plugin_rejection,
        "truth_inclusion": truth_inclusion,
        "c99_truth_inclusion": c99_truth,
        "effect_disconnected": component_count > 1,
        "effect_boundary_contact": effect_member[..., 0] | effect_member[..., -1],
        "strict_false_effect": strict_false,
        "strict_false_effect_unflagged": strict_false & ~primary_rejection,
        "strict_false_effect_unflagged_plugin": strict_false & ~plugin_rejection,
        "signed_log_bias": signed_bias,
        "absolute_log_error": np.abs(signed_bias),
        "fitted_h": fitted_h,
        "effect_log_width": np.log(effects[last] / effects[first]),
        "effect_cardinality": effect_member.sum(axis=-1),
        "effect_components": component_count,
        "effect_raw_span": effects[last] - effects[first],
        "prey_score": prey_score,
        "training_predator_score": predator_score,
        # This decomposition is reported, not treated as an independent identity check.
        "recovered_holdout_predator_score": selected_joint - prey_score,
    }


def _wilson(values: FloatArray) -> tuple[float, float]:
    interval = wilson_interval(int(np.sum(values)), len(values))
    return float(interval.lower), float(interval.upper)


def _interval_status(low: float, high: float, relation: str, lower: float | None = None,
                     upper: float | None = None) -> str:
    """Classify whether a 95% interval wholly satisfies a registered inequality."""
    if relation == "lt":
        assert upper is not None
        return "supported" if high < upper else ("contradicted" if low > upper else "unresolved")
    if relation == "le":
        assert upper is not None
        return "supported" if high <= upper else ("contradicted" if low > upper else "unresolved")
    if relation == "gt":
        assert lower is not None
        return "supported" if low > lower else ("contradicted" if high < lower else "unresolved")
    if relation == "ge":
        assert lower is not None
        return "supported" if low >= lower else ("contradicted" if high < lower else "unresolved")
    if relation == "between":
        assert lower is not None and upper is not None
        if low > lower and high < upper:
            return "supported"
        if high < lower or low > upper:
            return "contradicted"
        return "unresolved"
    if relation == "abs_lt":
        assert upper is not None
        if low > -upper and high < upper:
            return "supported"
        if high < -upper or low > upper:
            return "contradicted"
        return "unresolved"
    raise ValueError(f"unknown interval relation: {relation}")


def _prediction_row(
    prediction: str,
    component: str,
    estimate: float,
    low: float,
    high: float,
    relation: str,
    *,
    lower: float | None = None,
    upper: float | None = None,
    interval_override: str | None = None,
) -> dict[str, Any]:
    if relation == "lt":
        assert upper is not None
        point = estimate < upper
    elif relation == "le":
        assert upper is not None
        point = estimate <= upper
    elif relation == "gt":
        assert lower is not None
        point = estimate > lower
    elif relation == "ge":
        assert lower is not None
        point = estimate >= lower
    elif relation == "between":
        assert lower is not None and upper is not None
        point = lower < estimate < upper
    elif relation == "abs_lt":
        assert upper is not None
        point = abs(estimate) < upper
    else:
        raise ValueError(relation)
    status = interval_override or _interval_status(low, high, relation, lower, upper)
    return {
        "prediction": prediction,
        "component": component,
        "estimate": estimate,
        "interval_low": low,
        "interval_high": high,
        "point_predicate": bool(point),
        "interval_status": status,
        "relation": relation,
        "lower_bound": lower,
        "upper_bound": upper,
    }


def classify_nomination(contrast_rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Apply the registered one-cell primary-H nomination heuristic."""
    rows = [row for row in contrast_rows if row["metric"] == "H_primary"]
    eligible = [
        row for row in rows
        if row["delta"] >= NOMINATION_DELTA and row["bootstrap_low"] > 0.0
    ]
    if not eligible:
        return {"status": "none", "cell_id": None, "departure_class": None}
    order = {cell_id: index for index, cell_id in enumerate(CELL_IDS)}
    selected = sorted(eligible, key=lambda row: (-row["delta"], order[row["cell_id"]]))[0]
    return {
        "status": "nominated_for_independent_confirmation",
        "cell_id": selected["cell_id"],
        "departure_class": selected["departure_class"],
        "delta_H": selected["delta"],
        "bootstrap_low": selected["bootstrap_low"],
        "bootstrap_high": selected["bootstrap_high"],
    }


def paired_bootstrap(
    metric_arrays: FloatArray,
    baseline_index: IntArray,
    *,
    draws: int,
    seed: int,
) -> tuple[IntArray, FloatArray, FloatArray]:
    """Resample replicate indices jointly across cells and return means/deltas."""
    values = np.asarray(metric_arrays, dtype=np.float64)
    baseline_index = np.asarray(baseline_index, dtype=np.int64)
    if values.ndim != 3 or baseline_index.shape != (values.shape[0],):
        raise ValueError("metrics must be cell x replicate x metric with one baseline per cell")
    if draws < 1 or not np.isfinite(values).all():
        raise ValueError("paired bootstrap requires positive draws and finite metrics")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, values.shape[1], size=(draws, values.shape[1]), dtype=np.int64)
    means = np.empty((draws, values.shape[0], values.shape[2]), dtype=np.float64)
    for draw, sampled in enumerate(indices):
        means[draw] = values[:, sampled].mean(axis=1)
    return indices, means, means - means[:, baseline_index]


def _prediction_rows(
    cell_index: dict[str, int],
    metric_index: dict[str, int],
    point_means: FloatArray,
    bootstrap_means: FloatArray,
    bootstrap_deltas: FloatArray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def delta(cell: str, metric: str) -> tuple[float, float, float]:
        c, m = cell_index[cell], metric_index[metric]
        values = bootstrap_deltas[:, c, m]
        low, high = np.quantile(values, (0.025, 0.975))
        base = cell_index[BASELINE_BY_CELL[cell]]
        return (float(point_means[c, m] - point_means[base, m]), float(low), float(high))

    def level(cell: str, metric: str, *, wilson: bool = False) -> tuple[float, float, float]:
        c, m = cell_index[cell], metric_index[metric]
        estimate = float(point_means[c, m])
        if wilson:
            # Bootstrap cell means deliberately do not replace conditional binomial uncertainty.
            count = round(estimate * REPLICATES)
            interval = wilson_interval(count, REPLICATES)
            return estimate, float(interval.lower), float(interval.upper)
        low, high = np.quantile(bootstrap_means[:, c, m], (0.025, 0.975))
        return estimate, float(low), float(high)

    for severity in ("D10",):
        for truth in (1, 3, 5):
            cell = f"{severity}_h{truth}"
            estimate, low, high = delta(cell, "signed_log_bias")
            rows.append(_prediction_row("P1", f"{cell}: abs(delta signed log bias) < 0.05",
                                        estimate, low, high, "abs_lt", upper=0.05))
            estimate, low, high = delta(cell, "H_primary")
            rows.append(_prediction_row("P1", f"{cell}: delta H < 0.02",
                                        estimate, low, high, "lt", upper=0.02))
    for truth in (3, 5):
        cell = f"D20_h{truth}"
        estimate, low, high = delta(cell, "signed_log_bias")
        rows.append(
            _prediction_row(
                "P1",
                f"{cell}: 0.85 < exp(delta signed log bias) < 1",
                float(np.exp(estimate)),
                float(np.exp(low)),
                float(np.exp(high)),
                "between",
                lower=0.85,
                upper=1.0,
            )
        )
    for truth in (1, 3, 5):
        cell = f"D20_h{truth}"
        estimate, low, high = delta(cell, "M_truth_excluded")
        rows.append(_prediction_row("P1", f"{cell}: truth-exclusion delta < 0.03",
                                    estimate, low, high, "lt", upper=0.03))

    for metric, relation, bound, label in (
        ("strict_false_effect", "gt", 0.20, "strict false-effect rate > 0.20"),
        ("primary_rejection", "lt", 0.10, "primary rejection rate < 0.10"),
    ):
        estimate, low, high = level("B100-A_h1", metric, wilson=True)
        rows.append(_prediction_row("P2", f"B100-A_h1: {label}", estimate, low, high, relation,
                                    lower=bound if relation == "gt" else None,
                                    upper=bound if relation == "lt" else None))
    estimate, low, high = delta("B100-A_h1", "H_primary")
    rows.append(_prediction_row("P2", "B100-A_h1: delta H > 0.10", estimate, low, high,
                                "gt", lower=0.10))

    for cell in ("B50-I_h1", "B100-I_h1"):
        estimate, low, high = delta(cell, "strict_false_effect")
        met = low <= 0.0 <= high
        rows.append({
            **_prediction_row("P3", f"{cell}: strict false-effect delta interval includes zero",
                              estimate, low, high, "ge", lower=0.0,
                              interval_override="met" if met else "unmet"),
            "point_predicate": met,
            "relation": "interval_contains_zero",
        })
        estimate, low, high = delta(cell, "effect_log_width")
        rows.append(_prediction_row("P3", f"{cell}: mean effect-set width > baseline",
                                    estimate, low, high, "gt", lower=0.0))

    for truth in (3, 5):
        pd, d20 = cell_index[f"PD10_h{truth}"], cell_index[f"D20_h{truth}"]
        m = metric_index["signed_log_bias"]
        estimate = abs(point_means[pd, m]) - abs(point_means[d20, m])
        draws = np.abs(bootstrap_means[:, pd, m]) - np.abs(bootstrap_means[:, d20, m])
        low, high = np.quantile(draws, (0.025, 0.975))
        rows.append(
            _prediction_row(
                "P4",
                f"h={truth}: abs(mean bias PD10) - abs(mean bias D20) > 0",
                float(estimate),
                float(low),
                float(high),
                "gt",
                lower=0.0,
            )
        )
    p4_exclusion_estimates = []
    p4_exclusion_draws = []
    for truth in (1, 3, 5):
        cell = f"PD10_h{truth}"
        estimate, _, _ = delta(cell, "M_truth_excluded")
        p4_exclusion_estimates.append(estimate)
        p4_exclusion_draws.append(
            bootstrap_deltas[:, cell_index[cell], metric_index["M_truth_excluded"]]
        )
    maximum_draws = np.max(np.stack(p4_exclusion_draws, axis=1), axis=1)
    maximum_low, maximum_high = np.quantile(maximum_draws, (0.025, 0.975))
    rows.append(_prediction_row(
        "P4",
        "PD10: maximum truth-exclusion delta across registered truths >= 0.03",
        max(p4_exclusion_estimates),
        float(maximum_low),
        float(maximum_high),
        "ge",
        lower=0.03,
    ))
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _diagnostic_rows(
    diagnostics: dict[str, FloatArray], cells: tuple[str, ...]
) -> list[dict[str, Any]]:
    """Summarize evaluator-only fields without feeding them into inference."""
    rows: list[dict[str, Any]] = []
    for name in sorted(diagnostics):
        values = np.asarray(diagnostics[name], dtype=np.float64)
        if values.shape != (len(cells), REPLICATES):
            raise ValueError(
                f"diagnostic {name} must have shape {(len(cells), REPLICATES)}, got {values.shape}"
            )
        for index, cell_id in enumerate(cells):
            finite = values[index, np.isfinite(values[index])]
            rows.append({
                "cell_id": cell_id,
                "departure_class": CLASS_BY_CELL[cell_id],
                "diagnostic": name,
                "n_defined": len(finite),
                "n_undefined": REPLICATES - len(finite),
                "mean": float(np.mean(finite)) if len(finite) else None,
                "sd": float(np.std(finite, ddof=1)) if len(finite) > 1 else None,
                "q025": float(np.quantile(finite, 0.025)) if len(finite) else None,
                "median": float(np.median(finite)) if len(finite) else None,
                "q975": float(np.quantile(finite, 0.975)) if len(finite) else None,
                "role": "evaluator_only_descriptive_not_fit_or_tuning_input",
            })
    return rows


def _plot(
    output: Path, cell_rows: list[dict[str, Any]], contrast_rows: list[dict[str, Any]]
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    h_rows = [row for row in cell_rows if row["metric"] == "H_primary"]
    contrast_h = [row for row in contrast_rows if row["metric"] == "H_primary"]
    bias_rows = [row for row in cell_rows if row["metric"] == "signed_log_bias"]
    x = np.arange(len(CELL_IDS))
    fig, axes = plt.subplots(3, 1, figsize=(13.5, 10.5), layout="constrained")
    axes[0].errorbar(x, [r["estimate"] for r in h_rows],
                     yerr=([r["estimate"] - r["interval_low"] for r in h_rows],
                           [r["interval_high"] - r["estimate"] for r in h_rows]), fmt="o")
    axes[0].set(
        ylabel="Primary hidden-failure H",
        ylim=(-0.02, 1.02),
        title="A  Cell rates (Wilson 95% intervals)",
    )
    axes[1].errorbar(np.arange(len(contrast_h)), [r["delta"] for r in contrast_h],
                     yerr=([r["delta"] - r["bootstrap_low"] for r in contrast_h],
                           [r["bootstrap_high"] - r["delta"] for r in contrast_h]), fmt="o")
    axes[1].axhline(0, color="black", lw=0.8)
    axes[1].axhline(NOMINATION_DELTA, color="black", lw=0.8, ls="--")
    axes[1].set(ylabel="Departure - baseline", title="B  Paired change in primary H")
    axes[2].plot(x, [r["estimate"] for r in bias_rows], "o")
    axes[2].axhline(0, color="black", lw=0.8)
    axes[2].set(ylabel="Mean signed log bias", title="C  Effect-estimate bias")
    for axis in axes:
        axis.grid(axis="y", alpha=0.2)
    axes[0].set_xticks(x, CELL_IDS, rotation=55, ha="right", fontsize=8)
    axes[1].set_xticks(
        np.arange(len(contrast_h)),
        [r["cell_id"] for r in contrast_h],
        rotation=55,
        ha="right",
        fontsize=8,
    )
    axes[2].set_xticks(x, CELL_IDS, rotation=55, ha="right", fontsize=8)
    fig.suptitle("Goal 051 misspecification screen; complete histories are the replicate unit")
    fig.savefig(output / "misspecification_screen.png", dpi=200)
    fig.savefig(output / "misspecification_screen.pdf")
    plt.close(fig)


def write_synthesis(
    output: Path,
    effects: FloatArray,
    cell_ids: Iterable[str],
    truths: FloatArray,
    profiles: FloatArray,
    prey_score: FloatArray,
    predator_score: FloatArray,
    mle_index: IntArray,
    holdout_joint: FloatArray,
    opaque_ids: NDArray[np.str_],
    reference_scores: FloatArray,
    effect_cutoffs: FloatArray,
    c99_cutoffs: FloatArray,
    *,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
    metadata: dict[str, Any] | None = None,
    diagnostics: dict[str, FloatArray] | None = None,
) -> SynthesisResult:
    """Validate the frozen 17-cell campaign and write its reviewable synthesis."""
    effects = np.asarray(effects, dtype=np.float64)
    cells = tuple(str(value) for value in cell_ids)
    truths = np.asarray(truths, dtype=np.float64)
    profiles = np.asarray(profiles, dtype=np.float64)
    prey_score = np.asarray(prey_score, dtype=np.float64)
    predator_score = np.asarray(predator_score, dtype=np.float64)
    mle_index = np.asarray(mle_index, dtype=np.int64)
    holdout_joint = np.asarray(holdout_joint, dtype=np.float64)
    opaque_ids = np.asarray(opaque_ids)
    if cells != CELL_IDS or not np.array_equal(truths, TRUTHS):
        raise ValueError("the frozen 17-cell IDs, order, and truths are required")
    if profiles.shape != (17, REPLICATES, NODES):
        raise ValueError("profiles must contain the full 17 x 1000 x 181 screen")
    if opaque_ids.shape != (17, REPLICATES) or opaque_ids.dtype.kind not in "SU":
        raise ValueError("opaque_ids must be a 17 x 1000 string array")
    if len(np.unique(opaque_ids)) != opaque_ids.size:
        raise ValueError("opaque history IDs must be unique across the complete screen")
    if effects.shape != (NODES,) or not np.array_equal(effects, 1.0 + 0.05 * np.arange(NODES)):
        raise ValueError("the frozen 181-node effect grid is required")
    if draws != BOOTSTRAP_DRAWS or seed != BOOTSTRAP_SEED:
        raise ValueError("Goal 051 requires exactly 1000 paired draws from seed 2026092304")

    evidence = evaluate_histories(
        effects, truths, profiles, prey_score, predator_score, mle_index, holdout_joint,
        reference_scores, effect_cutoffs, c99_cutoffs,
    )
    metric_arrays = np.stack(
        [np.asarray(evidence[name], dtype=np.float64) for name in METRICS], axis=-1
    )
    point_means = metric_arrays.mean(axis=1)
    baseline_index = np.asarray(
        [cells.index(BASELINE_BY_CELL[cell]) for cell in cells], dtype=np.int64
    )
    bootstrap_indices, bootstrap_means, bootstrap_deltas = paired_bootstrap(
        metric_arrays, baseline_index, draws=draws, seed=seed
    )

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cell_rows: list[dict[str, Any]] = []
    for cell, cell_id in enumerate(cells):
        for metric, name in enumerate(METRICS):
            estimate = float(point_means[cell, metric])
            if name in BINARY_METRICS:
                low, high = _wilson(metric_arrays[cell, :, metric])
                interval_kind = "conditional_wilson_95"
            else:
                low, high = np.quantile(bootstrap_means[:, cell, metric], (0.025, 0.975))
                interval_kind = "paired_replicate_bootstrap_95"
            cell_rows.append({
                "cell_id": cell_id,
                "departure_class": CLASS_BY_CELL[cell_id],
                "truth_h": float(truths[cell]),
                "metric": name,
                "n": REPLICATES,
                "estimate": estimate,
                "interval_low": float(low),
                "interval_high": float(high),
                "interval_kind": interval_kind,
            })

    contrast_rows: list[dict[str, Any]] = []
    for cell, cell_id in enumerate(cells[3:], start=3):
        base = baseline_index[cell]
        for metric, name in enumerate(METRICS):
            samples = bootstrap_deltas[:, cell, metric]
            low, high = np.quantile(samples, (0.025, 0.975))
            delta = float(point_means[cell, metric] - point_means[base, metric])
            if name in ("H_primary", "M"):
                if delta >= NOMINATION_DELTA and low > 0:
                    classification = "qualifies"
                elif delta >= NOMINATION_DELTA and low <= 0 <= high:
                    classification = "unresolved"
                else:
                    classification = "below_relevance_threshold"
            else:
                classification = "descriptive"
            contrast_rows.append({
                "cell_id": cell_id,
                "baseline_id": cells[base],
                "departure_class": CLASS_BY_CELL[cell_id],
                "truth_h": float(truths[cell]),
                "metric": name,
                "delta": delta,
                "bootstrap_low": float(low),
                "bootstrap_high": float(high),
                "classification": classification,
            })

    cell_index = {name: index for index, name in enumerate(cells)}
    metric_index = {name: index for index, name in enumerate(METRICS)}
    prediction_rows = _prediction_rows(
        cell_index, metric_index, point_means, bootstrap_means, bootstrap_deltas
    )
    nomination = classify_nomination(contrast_rows)
    diagnostic_rows = _diagnostic_rows(diagnostics or {}, cells)
    summary = {
        "workflow": "goal051-misspecification-screen-synthesis",
        "scope": (
            "Synthetic 17-cell robustness screen on one accepted landscape; physical h is "
            "evaluated under a deliberately misspecified constant-detection/background fit"
        ),
        "cell_ids": list(cells),
        "truths": truths.tolist(),
        "replicates_per_cell": REPLICATES,
        "primary_detector": {
            "candidate_p": "(1 + count(reference <= observed)) / 1000; inclusive ties",
            "berger_boos": "min(1, max over frozen C99 of candidate p + 0.01)",
            "reject_at_or_below": REJECTION_LEVEL,
        },
        "secondary_plugin": {
            "node": "lowest-index training-grid MLE",
            "role": "secondary diagnostic only; cannot nominate a departure",
            "validity": "Data-selected reference row has no fixed-node finite-sample guarantee.",
            "combination": "No reject-on-either-detector omnibus is used.",
        },
        "misleading_event": (
            "truth excluded from frozen rank-950 effect set OR "
            "abs(log(fitted_h / physical_h)) >= log(1.5)"
        ),
        "bootstrap": {
            "draws": draws,
            "seed": seed,
            "unit": "complete replicate index jointly across all 17 cells",
            "reference_bootstrap": False,
        },
        "nomination": nomination,
        "nomination_rule": (
            "at most one cell globally: primary delta H >= 0.05 and paired lower 95% > 0; "
            "largest delta, exact ties by frozen cell order; confirmation still required"
        ),
        "M_classification_role": "reported separately; never an automatic nomination",
        "prediction_status_counts": {
            status: sum(row["interval_status"] == status for row in prediction_rows)
            for status in ("supported", "contradicted", "unresolved", "met", "unmet")
        },
        "cell_metrics": cell_rows,
        "paired_contrasts": contrast_rows,
        "predictions": prediction_rows,
        "field_diagnostic_rows": diagnostic_rows,
        "metadata": metadata or {},
        "field_diagnostics": {
            "variables": sorted((diagnostics or {}).keys()),
            "table": "field_diagnostics.csv" if diagnostic_rows else None,
            "role": "evaluator-only descriptive summaries; not inference or tuning inputs",
        },
        "scientific_limits": [
            "The screen is marginal over complete histories on one accepted landscape.",
            "Detector non-rejection is not evidence that the fitted model is adequate.",
            "Physical h need not be the pseudo-true parameter of the misspecified fitted model.",
            (
                "Nomination is a winner-biased heuristic and requires an independent "
                "confirmation block."
            ),
            "The bootstrap conditions on frozen calibration references and cutoffs.",
            "Cell and prediction intervals are not simultaneous or multiplicity-controlled.",
            "The secondary plug-in rule has no fixed-node finite-sample guarantee after selection.",
            "Only Berger-Boos determines primary H and nomination; no either-test omnibus.",
        ],
    }

    _write_csv(output / "cell_metrics.csv", cell_rows)
    _write_csv(output / "paired_contrasts.csv", contrast_rows)
    _write_csv(output / "predictions.csv", prediction_rows)
    if diagnostic_rows:
        _write_csv(output / "field_diagnostics.csv", diagnostic_rows)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    evidence_values: dict[str, Any] = dict(evidence)
    np.savez_compressed(
        output / "evidence.npz",
        cell_ids=np.asarray(cells),
        truths=truths,
        opaque_ids=opaque_ids,
        **evidence_values,
    )
    np.savez_compressed(
        output / "bootstrap_draws.npz",
        seed=np.asarray(seed),
        replicate_indices=bootstrap_indices,
        metrics=np.asarray(METRICS),
        cell_means=bootstrap_means,
        paired_deltas=bootstrap_deltas,
    )
    _plot(output, cell_rows, contrast_rows)
    return SynthesisResult(
        summary, cell_rows, contrast_rows, prediction_rows, evidence,
        bootstrap_indices, bootstrap_means, bootstrap_deltas,
    )
