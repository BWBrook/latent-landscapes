"""Goal 050 model-adequacy detector and crossed-null synthesis.

The primary statistic is the conditional held-out prey log score (low is
adverse).  This module deliberately keeps the rank-990 Berger--Boos candidate
set separate from Goal 049's rank-950 effect set.  Bootstrap resampling uses
replicate multiplicities so the original calibration weights are shared by
the score reference table and every LR cutoff without repeatedly sorting the
large arrays.
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal002.calibration import wilson_interval

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

CALIBRATION_REPLICATES = 999
EVALUATION_REPLICATES = 1000
C99_RANK = 990
EFFECT_RANK = 950
GAMMA = 0.01
REJECTION_LEVEL = 0.05
BOOTSTRAP_DRAWS = 1000
BOOTSTRAP_SEED = 2026092006
ENDPOINTS = ("detector_rejection", "c99_inclusion", "effect_null_exclusion")


@dataclass(frozen=True)
class PreparedReference:
    """Sorted original references and observed-score rank indices."""

    score_order: IntArray
    lr_order: IntArray
    old_score_ranks: IntArray
    fresh_score_ranks: IntArray


@dataclass(frozen=True)
class BootstrapResult:
    retrospective: FloatArray
    fresh_null: FloatArray
    null_cells: FloatArray
    null_contrasts: FloatArray
    seconds: float


@dataclass(frozen=True)
class SynthesisResult:
    summary: dict[str, Any]
    retrospective_p: FloatArray
    retrospective_p_bb: FloatArray
    retrospective_c99: BoolArray
    fresh_p: FloatArray
    fresh_p_bb: FloatArray
    fresh_c99: BoolArray
    bootstrap: BootstrapResult


def conservative_lower_tail_pvalues(
    reference_scores: FloatArray, observed_scores: FloatArray
) -> FloatArray:
    """Compute (1 + count(reference <= observed)) / (B + 1), including ties.

    ``reference_scores`` has shape ``(candidate, reference_replicate)`` and
    ``observed_scores`` can have any leading shape.  The returned candidate
    axis is last.
    """
    reference_scores = np.asarray(reference_scores, dtype=np.float64)
    observed_scores = np.asarray(observed_scores, dtype=np.float64)
    if reference_scores.ndim != 2 or reference_scores.shape[0] == 0:
        raise ValueError("reference scores must have candidate and replicate axes")
    if not np.isfinite(reference_scores).all() or not np.isfinite(observed_scores).all():
        raise ValueError("scores must be finite")
    ordered = np.sort(reference_scores, axis=1)
    counts = np.empty((*observed_scores.shape, reference_scores.shape[0]), dtype=np.int64)
    for node in range(reference_scores.shape[0]):
        counts[..., node] = np.searchsorted(
            ordered[node], observed_scores, side="right"
        )
    return np.asarray(
        (counts + 1.0) / (reference_scores.shape[1] + 1.0), dtype=np.float64
    )


def diagonal_lr(calibration_profiles: FloatArray) -> FloatArray:
    """Extract candidate-specific LR references, shape (candidate, replicate)."""
    profiles = np.asarray(calibration_profiles, dtype=np.float64)
    if profiles.ndim != 3 or profiles.shape[0] != profiles.shape[2]:
        raise ValueError("calibration profiles must be candidate x replicate x candidate")
    if not np.isfinite(profiles).all() or (profiles < 0).any():
        raise ValueError("LR profiles must be finite and nonnegative")
    nodes = profiles.shape[0]
    return profiles[np.arange(nodes), :, np.arange(nodes)]


def order_cutoff(values: FloatArray, rank: int) -> FloatArray:
    """Return the one-indexed order statistic along the last axis."""
    values = np.asarray(values, dtype=np.float64)
    if values.ndim == 0 or not 1 <= rank <= values.shape[-1]:
        raise ValueError("rank is outside the reference sample")
    if not np.isfinite(values).all():
        raise ValueError("order-statistic inputs must be finite")
    return np.partition(values, rank - 1, axis=-1)[..., rank - 1]


def berger_boos_pvalues(
    candidate_p: FloatArray, profiles: FloatArray, c99_cutoffs: FloatArray
) -> tuple[FloatArray, BoolArray]:
    """Return p_BB and full-grid C99 membership for each observed history."""
    candidate_p = np.asarray(candidate_p, dtype=np.float64)
    profiles = np.asarray(profiles, dtype=np.float64)
    cutoffs = np.asarray(c99_cutoffs, dtype=np.float64)
    if candidate_p.shape != profiles.shape or profiles.shape[-1] != len(cutoffs):
        raise ValueError("candidate p-values, profiles and cutoffs do not align")
    if (
        not np.isfinite(candidate_p).all()
        or not np.isfinite(profiles).all()
        or not np.isfinite(cutoffs).all()
        or (candidate_p < 0).any()
        or (candidate_p > 1).any()
        or (profiles < 0).any()
    ):
        raise ValueError("detector inputs are outside their finite valid ranges")
    membership = profiles <= cutoffs
    if not membership.any(axis=-1).all():
        raise ValueError("C99 is empty for at least one history")
    maximizers = np.argmin(profiles, axis=-1)
    if not np.take_along_axis(membership, maximizers[..., None], axis=-1)[..., 0].all():
        raise ValueError("C99 does not contain a fitted training maximizer")
    maximum = np.max(np.where(membership, candidate_p, -np.inf), axis=-1)
    return np.minimum(1.0, maximum + GAMMA), membership


def detector_endpoints(
    reference_scores: FloatArray,
    calibration_profiles: FloatArray,
    observed_scores: FloatArray,
    evaluation_profiles: FloatArray,
    truth_indices: IntArray,
) -> tuple[FloatArray, FloatArray, BoolArray, BoolArray]:
    """Evaluate the frozen detector and its two registered companion endpoints."""
    diag = diagonal_lr(calibration_profiles)
    p_values = conservative_lower_tail_pvalues(reference_scores, observed_scores)
    p_bb, c99 = berger_boos_pvalues(p_values, evaluation_profiles, order_cutoff(diag, C99_RANK))
    truth_indices = np.asarray(truth_indices, dtype=np.int64)
    if evaluation_profiles.ndim != 3 or truth_indices.shape != (evaluation_profiles.shape[0],):
        raise ValueError("one grid truth index is required per evaluation truth")
    truth_member = np.take_along_axis(
        c99, truth_indices[:, None, None], axis=-1
    )[..., 0]
    effect_cutoffs = order_cutoff(diag, EFFECT_RANK)
    null_exclusion = evaluation_profiles[..., 0] > effect_cutoffs[0]
    outcomes = np.stack((p_bb <= REJECTION_LEVEL, truth_member, null_exclusion), axis=-1)
    return p_values, p_bb, c99, outcomes


def _score_rank_indices(sorted_reference: FloatArray, observed: FloatArray) -> IntArray:
    ranks = np.empty((*observed.shape, sorted_reference.shape[0]), dtype=np.int64)
    for node in range(sorted_reference.shape[0]):
        ranks[..., node] = np.searchsorted(sorted_reference[node], observed, side="right")
    return ranks


def prepare_reference(
    reference_scores: FloatArray,
    calibration_lr: FloatArray,
    old_observed: FloatArray,
    fresh_observed: FloatArray,
) -> PreparedReference:
    """Pre-sort calibration arrays and precompute inclusive observed ranks."""
    score_order = np.argsort(reference_scores, axis=1, kind="stable")
    lr_order = np.argsort(calibration_lr, axis=1, kind="stable")
    sorted_scores = np.take_along_axis(reference_scores, score_order, axis=1)
    return PreparedReference(
        score_order=score_order,
        lr_order=lr_order,
        old_score_ranks=_score_rank_indices(sorted_scores, old_observed),
        fresh_score_ranks=_score_rank_indices(sorted_scores, fresh_observed),
    )


def _weighted_cutoff(order: IntArray, weights: IntArray, rank: int) -> IntArray:
    """Indices of weighted order statistics, one row per node."""
    sorted_weights = weights[order]
    cumulative = np.cumsum(sorted_weights, axis=1)
    locations = np.argmax(cumulative >= rank, axis=1)
    return order[np.arange(order.shape[0]), locations]


def _weighted_score_pvalues(
    score_order: IntArray, weights: IntArray, ranks: IntArray
) -> FloatArray:
    sorted_weights = weights[score_order]
    cumulative = np.cumsum(sorted_weights, axis=1)
    padded = np.concatenate((np.zeros((len(cumulative), 1), dtype=np.int64), cumulative), axis=1)
    nodes = np.arange(score_order.shape[0])[:, None, None]
    counts = padded[nodes, np.moveaxis(ranks, -1, 0)]
    return np.moveaxis((counts + 1.0) / (weights.sum() + 1.0), 0, -1)


def _rates(outcomes: BoolArray, weights: IntArray) -> FloatArray:
    rates = np.asarray(
        np.einsum("trm,r->tm", outcomes, weights, optimize=True) / weights.sum(),
        dtype=np.float64,
    )
    return np.clip(rates, 0.0, 1.0)


def _null_contrasts(cells: FloatArray) -> FloatArray:
    """Paired cutoff changes within blocks plus their interaction."""
    # cell axes: calibration (old,new), evaluation (old,new)
    old_eval_change = cells[1, 0] - cells[0, 0]
    fresh_eval_change = cells[1, 1] - cells[0, 1]
    return np.asarray(
        [
            old_eval_change,
            fresh_eval_change,
            cells[0, 1] - cells[0, 0],
            cells[1, 1] - cells[1, 0],
            fresh_eval_change - old_eval_change,
        ],
        dtype=np.float64,
    )


NULL_CONTRASTS = (
    "fresh_minus_original_cutoff_on_retrospective_evaluation",
    "fresh_minus_original_cutoff_on_fresh_evaluation",
    "fresh_minus_retrospective_evaluation_at_original_cutoff",
    "fresh_minus_retrospective_evaluation_at_fresh_cutoff",
    "cutoff_by_evaluation_interaction",
)


def calibration_aware_bootstrap(
    reference_scores: FloatArray,
    calibration_lr: FloatArray,
    old_observed_scores: FloatArray,
    old_profiles: FloatArray,
    old_truth_indices: IntArray,
    fresh_calibration_lr: FloatArray,
    fresh_observed_scores: FloatArray,
    fresh_profiles: FloatArray,
    *,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> BootstrapResult:
    """Run the registered four-block bootstrap using shared multiplicities.

    Original/fresh calibration and evaluation blocks are mutually independent.
    One original calibration weight vector is shared over all nodes and between
    reference-score ranks and LR cutoffs.  One original evaluation vector is
    shared over the six paired truths.
    """
    if draws < 1:
        raise ValueError("bootstrap draws must be positive")
    if reference_scores.shape != calibration_lr.shape:
        raise ValueError("score and LR references must share node/replicate shape")
    if fresh_calibration_lr.ndim != 1:
        raise ValueError("fresh calibration LR must be one-dimensional")
    start = time.monotonic()
    prepared = prepare_reference(
        reference_scores, calibration_lr, old_observed_scores, fresh_observed_scores
    )
    ncal = reference_scores.shape[1]
    neval = old_observed_scores.shape[1]
    nfcal = len(fresh_calibration_lr)
    nfeval = fresh_observed_scores.shape[1]
    if ncal < C99_RANK or ncal < EFFECT_RANK or nfcal < EFFECT_RANK:
        raise ValueError("calibration arrays are shorter than registered ranks")
    roots = np.random.SeedSequence(seed).spawn(4)
    rng_old_cal, rng_new_cal, rng_old_eval, rng_new_eval = (
        np.random.default_rng(root) for root in roots
    )
    old_lr_sorted = np.take_along_axis(calibration_lr, prepared.lr_order, axis=1)
    fresh_lr_order = np.argsort(fresh_calibration_lr, kind="stable")
    old_truth_indices = np.asarray(old_truth_indices, dtype=np.int64)
    retrospective = np.empty((draws, old_profiles.shape[0], len(ENDPOINTS)))
    fresh = np.empty((draws, 1, len(ENDPOINTS)))
    null_cells = np.empty((draws, 2, 2))
    contrasts = np.empty((draws, len(NULL_CONTRASTS)))
    for draw in range(draws):
        old_cal_weights = np.bincount(
            rng_old_cal.integers(ncal, size=ncal), minlength=ncal
        )
        new_cal_weights = np.bincount(
            rng_new_cal.integers(nfcal, size=nfcal), minlength=nfcal
        )
        old_eval_weights = np.bincount(
            rng_old_eval.integers(neval, size=neval), minlength=neval
        )
        new_eval_weights = np.bincount(
            rng_new_eval.integers(nfeval, size=nfeval), minlength=nfeval
        )

        lr_sorted_weights = old_cal_weights[prepared.lr_order]
        lr_cumulative = np.cumsum(lr_sorted_weights, axis=1)
        c99_locations = np.argmax(lr_cumulative >= C99_RANK, axis=1)
        c99_cutoffs = old_lr_sorted[np.arange(len(calibration_lr)), c99_locations]
        effect_locations = np.argmax(lr_cumulative >= EFFECT_RANK, axis=1)
        old_effect_cutoff = old_lr_sorted[0, effect_locations[0]]
        new_cumulative = np.cumsum(new_cal_weights[fresh_lr_order])
        new_location = int(np.argmax(new_cumulative >= EFFECT_RANK))
        new_effect_cutoff = fresh_calibration_lr[fresh_lr_order[new_location]]

        old_p = _weighted_score_pvalues(
            prepared.score_order, old_cal_weights, prepared.old_score_ranks
        )
        old_c99 = old_profiles <= c99_cutoffs
        if not old_c99.any(axis=-1).all():
            raise ValueError("bootstrap C99 lost all maximizers")
        old_p_bb = np.minimum(1.0, np.max(np.where(old_c99, old_p, -np.inf), axis=-1) + GAMMA)
        old_truth_member = np.take_along_axis(
            old_c99, old_truth_indices[:, None, None], axis=-1
        )[..., 0]
        old_outcomes = np.stack(
            (
                old_p_bb <= REJECTION_LEVEL,
                old_truth_member,
                old_profiles[..., 0] > old_effect_cutoff,
            ),
            axis=-1,
        )
        retrospective[draw] = _rates(old_outcomes, old_eval_weights)

        fresh_p = _weighted_score_pvalues(
            prepared.score_order, old_cal_weights, prepared.fresh_score_ranks
        )
        fresh_c99 = fresh_profiles <= c99_cutoffs
        if not fresh_c99.any(axis=-1).all():
            raise ValueError("fresh bootstrap C99 lost all maximizers")
        fresh_p_bb = np.minimum(
            1.0, np.max(np.where(fresh_c99, fresh_p, -np.inf), axis=-1) + GAMMA
        )
        fresh_outcomes = np.stack(
            (
                fresh_p_bb <= REJECTION_LEVEL,
                fresh_c99[..., 0],
                fresh_profiles[..., 0] > old_effect_cutoff,
            ),
            axis=-1,
        )
        fresh[draw] = _rates(fresh_outcomes, new_eval_weights)

        old_lr = old_profiles[0, :, 0]
        new_lr = fresh_profiles[0, :, 0]
        cell_flags = (
            (old_lr > old_effect_cutoff, new_lr > old_effect_cutoff),
            (old_lr > new_effect_cutoff, new_lr > new_effect_cutoff),
        )
        cells = np.clip(
            np.asarray(
            [
                [
                    np.dot(cell_flags[c][0], old_eval_weights) / neval,
                    np.dot(cell_flags[c][1], new_eval_weights) / nfeval,
                ]
                for c in range(2)
            ]
            ),
            0.0,
            1.0,
        )
        null_cells[draw] = cells
        contrasts[draw] = _null_contrasts(cells)
    seconds = time.monotonic() - start
    if not all(
        np.isfinite(array).all()
        for array in (retrospective, fresh, null_cells, contrasts)
    ):
        raise ValueError("bootstrap generated non-finite summaries")
    return BootstrapResult(retrospective, fresh, null_cells, contrasts, seconds)


def _wilson(successes: int, total: int) -> tuple[float, float]:
    interval = wilson_interval(successes, total)
    return float(interval.lower), float(interval.upper)


def _bootstrap_fields(samples: FloatArray) -> dict[str, float | None]:
    low, high = np.quantile(samples, (0.025, 0.975))
    if len(samples) <= 1 or np.ptp(samples) == 0:
        se = 0.0
    else:
        centered = samples - np.mean(samples)
        se = float(np.sqrt(np.dot(centered, centered) / (len(samples) - 1)))
    return {
        "bootstrap_se": se,
        "bootstrap_low": float(low),
        "bootstrap_high": float(high),
    }


def standardized_change(change: float, se: float) -> float | None:
    """Return a standardized change; zero uncertainty remains undefined."""
    return change / se if se > 0 else None


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty table: {path.name}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _endpoint_rows(
    block: str,
    truths: FloatArray,
    outcomes: BoolArray,
    bootstrap: FloatArray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for truth_index, truth in enumerate(truths):
        for metric_index, metric in enumerate(ENDPOINTS):
            count = int(outcomes[truth_index, :, metric_index].sum())
            n = outcomes.shape[1]
            low, high = _wilson(count, n)
            rows.append(
                {
                    "block": block,
                    "truth": float(truth),
                    "endpoint": metric,
                    "count": count,
                    "n": n,
                    "estimate": count / n,
                    "conditional_wilson_low": low,
                    "conditional_wilson_high": high,
                    **_bootstrap_fields(bootstrap[:, truth_index, metric_index]),
                }
            )
    return rows


def _predator_rows(
    original_calibration: FloatArray,
    original_evaluation: FloatArray,
    fresh_calibration: FloatArray,
    fresh_evaluation: FloatArray,
    truths: FloatArray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    blocks = [
        ("original_calibration_g1_reference", 1.0, original_calibration[0]),
        ("fresh_null_calibration", 1.0, fresh_calibration[0]),
        ("fresh_null_evaluation", 1.0, fresh_evaluation[0]),
    ]
    blocks.extend(
        ("retrospective_evaluation", float(truth), original_evaluation[index])
        for index, truth in enumerate(truths)
    )
    for block, truth, values in blocks:
        rows.append(
            {
                "block": block,
                "truth": truth,
                "n": len(values),
                "mean_predator_score": float(np.mean(values)),
                "sd_predator_score": float(np.std(values, ddof=1)),
                "q025_predator_score": float(np.quantile(values, 0.025)),
                "median_predator_score": float(np.median(values)),
                "q975_predator_score": float(np.quantile(values, 0.975)),
                "role": "secondary_descriptive_only_no_omnibus",
            }
        )
    return rows


def write_synthesis(
    output: Path,
    effects: FloatArray,
    truths: FloatArray,
    original_calibration_profiles: FloatArray,
    original_evaluation_profiles: FloatArray,
    original_calibration_prey: FloatArray,
    original_evaluation_prey: FloatArray,
    original_calibration_predator: FloatArray,
    original_evaluation_predator: FloatArray,
    fresh_calibration_profiles: FloatArray,
    fresh_evaluation_profiles: FloatArray,
    fresh_calibration_prey: FloatArray,
    fresh_evaluation_prey: FloatArray,
    fresh_calibration_predator: FloatArray,
    fresh_evaluation_predator: FloatArray,
    *,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> SynthesisResult:
    """Validate registered shapes and write all numerical/figure products."""
    effects = np.asarray(effects, dtype=np.float64)
    truths = np.asarray(truths, dtype=np.float64)
    nodes = len(effects)
    expected = {
        "original_calibration_profiles": (nodes, CALIBRATION_REPLICATES, nodes),
        "original_evaluation_profiles": (len(truths), EVALUATION_REPLICATES, nodes),
        "original_calibration_prey": (nodes, CALIBRATION_REPLICATES),
        "original_evaluation_prey": (len(truths), EVALUATION_REPLICATES),
        "original_calibration_predator": (nodes, CALIBRATION_REPLICATES),
        "original_evaluation_predator": (len(truths), EVALUATION_REPLICATES),
        "fresh_calibration_profiles": (1, CALIBRATION_REPLICATES, nodes),
        "fresh_evaluation_profiles": (1, EVALUATION_REPLICATES, nodes),
        "fresh_calibration_prey": (1, CALIBRATION_REPLICATES),
        "fresh_evaluation_prey": (1, EVALUATION_REPLICATES),
        "fresh_calibration_predator": (1, CALIBRATION_REPLICATES),
        "fresh_evaluation_predator": (1, EVALUATION_REPLICATES),
    }
    supplied = locals()
    for name, shape in expected.items():
        array = np.asarray(supplied[name])
        if array.shape != shape or not np.isfinite(array).all():
            raise ValueError(f"{name} must have finite registered shape {shape}, got {array.shape}")
    if nodes != 181 or not np.array_equal(effects, 1.0 + 0.05 * np.arange(nodes)):
        raise ValueError("the registered full 181-node effect grid is required")
    if not np.array_equal(truths, np.asarray([1.0, 2.0, 3.0, 4.0, 5.0, 10.0])):
        raise ValueError("the six registered retrospective truths are required")
    if seed != BOOTSTRAP_SEED or draws != BOOTSTRAP_DRAWS:
        raise ValueError("Goal 050 requires exactly 1000 draws from root 2026092006")
    calibration_predator_difference = float(
        np.max(
            np.abs(
                original_calibration_predator
                - original_calibration_predator[:1]
            )
        )
    )
    evaluation_predator_difference = float(
        np.max(
            np.abs(original_evaluation_predator - original_evaluation_predator[:1])
        )
    )
    if calibration_predator_difference > 1e-10 or evaluation_predator_difference > 1e-10:
        raise ValueError("predator-only score changed across h despite its registered invariance")
    output.mkdir(parents=True, exist_ok=False)

    original_lr = diagonal_lr(original_calibration_profiles)
    truth_indices = np.asarray(
        [int(np.flatnonzero(np.isclose(effects, truth))[0]) for truth in truths], dtype=np.int64
    )
    retro_p, retro_p_bb, retro_c99, retro_outcomes = detector_endpoints(
        original_calibration_prey,
        original_calibration_profiles,
        original_evaluation_prey,
        original_evaluation_profiles,
        truth_indices,
    )
    fresh_p, fresh_p_bb, fresh_c99, fresh_outcomes = detector_endpoints(
        original_calibration_prey,
        original_calibration_profiles,
        fresh_evaluation_prey,
        fresh_evaluation_profiles,
        np.asarray([0], dtype=np.int64),
    )
    bootstrap = calibration_aware_bootstrap(
        original_calibration_prey,
        original_lr,
        original_evaluation_prey,
        original_evaluation_profiles,
        truth_indices,
        fresh_calibration_profiles[0, :, 0],
        fresh_evaluation_prey,
        fresh_evaluation_profiles,
        draws=draws,
        seed=seed,
    )

    endpoint_rows = _endpoint_rows(
        "retrospective_baseline", truths, retro_outcomes, bootstrap.retrospective
    )
    endpoint_rows += _endpoint_rows(
        "fresh_null_prospective",
        np.asarray([1.0]),
        fresh_outcomes,
        bootstrap.fresh_null,
    )
    _write_csv(output / "endpoint_results.csv", endpoint_rows)

    old_cutoff = float(order_cutoff(original_lr[0], EFFECT_RANK))
    new_null_lr = fresh_calibration_profiles[0, :, 0]
    new_cutoff = float(order_cutoff(new_null_lr, EFFECT_RANK))
    old_eval_lr = original_evaluation_profiles[0, :, 0]
    new_eval_lr = fresh_evaluation_profiles[0, :, 0]
    null_flags = np.asarray(
        [
            [old_eval_lr > old_cutoff, new_eval_lr > old_cutoff],
            [old_eval_lr > new_cutoff, new_eval_lr > new_cutoff],
        ]
    )
    null_rows: list[dict[str, Any]] = []
    for c, calibration in enumerate(("original", "fresh")):
        for e, evaluation in enumerate(("retrospective", "fresh")):
            flags = null_flags[c, e]
            count = int(flags.sum())
            low, high = _wilson(count, len(flags))
            null_rows.append(
                {
                    "calibration_block": calibration,
                    "evaluation_block": evaluation,
                    "rank": EFFECT_RANK,
                    "cutoff": (old_cutoff, new_cutoff)[c],
                    "count": count,
                    "n": len(flags),
                    "estimate": count / len(flags),
                    "conditional_wilson_low": low,
                    "conditional_wilson_high": high,
                    **_bootstrap_fields(bootstrap.null_cells[:, c, e]),
                }
            )
    _write_csv(output / "crossed_null_cells.csv", null_rows)

    point_cells = np.asarray([[row[0].mean(), row[1].mean()] for row in null_flags])
    point_contrasts = _null_contrasts(point_cells)
    contrast_rows = []
    for index, name in enumerate(NULL_CONTRASTS):
        samples = bootstrap.null_contrasts[:, index]
        fields = _bootstrap_fields(samples)
        contrast_rows.append(
            {
                "contrast": name,
                "change": float(point_contrasts[index]),
                **fields,
                "change_over_bootstrap_se": standardized_change(
                    float(point_contrasts[index]), float(fields["bootstrap_se"] or 0.0)
                ),
            }
        )
    _write_csv(output / "crossed_null_contrasts.csv", contrast_rows)
    predator_rows = _predator_rows(
        original_calibration_predator,
        original_evaluation_predator,
        fresh_calibration_predator,
        fresh_evaluation_predator,
        truths,
    )
    _write_csv(output / "predator_diagnostic.csv", predator_rows)

    np.savez_compressed(
        output / "detector_values.npz",
        retrospective_candidate_p=retro_p,
        retrospective_p_bb=retro_p_bb,
        retrospective_c99=retro_c99,
        fresh_candidate_p=fresh_p,
        fresh_p_bb=fresh_p_bb,
        fresh_c99=fresh_c99,
        original_c99_cutoffs=order_cutoff(original_lr, C99_RANK),
        original_effect_cutoffs=order_cutoff(original_lr, EFFECT_RANK),
        fresh_null_effect_cutoff=np.asarray(new_cutoff),
        bootstrap_retrospective=bootstrap.retrospective,
        bootstrap_fresh_null=bootstrap.fresh_null,
        bootstrap_null_cells=bootstrap.null_cells,
        bootstrap_null_contrasts=bootstrap.null_contrasts,
    )
    if not np.isfinite(retro_p).all() or not np.isfinite(fresh_p).all():
        raise ValueError("candidate p-values must all be finite")

    summary: dict[str, Any] = {
        "scope": (
            "Synthetic known-nuisance finite 181-node grid conditional on the frozen "
            "integration bank; detector validity is marginal, not conditional 5% control"
        ),
        "primary_detector": {
            "statistic": "conditional held-out prey log score; lower tail adverse",
            "candidate_p": "(1 + count(reference <= observed)) / 1000; inclusive ties",
            "candidate_set_rank": C99_RANK,
            "gamma": GAMMA,
            "reject_at_or_below": REJECTION_LEVEL,
            "all_grid_nodes_used": True,
        },
        "goal049_effect_table": {
            "status": "unchanged",
            "diagnostic_rank": EFFECT_RANK,
            "original_null_cutoff": old_cutoff,
            "fresh_null_cutoff": new_cutoff,
            "interpretation": (
                "Crossed cells diagnose block sensitivity but do not identify a unique cause"
            ),
        },
        "blocks": {
            "retrospective": "six archived truths; outcomes informed detector design",
            "fresh_null": "prospective registered independent h=1 evaluation",
        },
        "bootstrap": {
            "draws": draws,
            "seed": seed,
            "seconds": bootstrap.seconds,
            "pairing": (
                "independent original/fresh calibration/evaluation resampling; original "
                "calibration weights shared across all S/T nodes; original evaluation "
                "indices paired across all six truths"
            ),
            "constant_series_rule": "SE exactly zero; standardized change undefined",
        },
        "secondary_predator_score": {
            "role": "descriptive only; no omnibus decision",
            "calibration_reference": "g=1 because predator score is h-invariant by construction",
            "calibration_max_abs_candidate_difference": calibration_predator_difference,
            "evaluation_max_abs_truth_difference": evaluation_predator_difference,
            "invariance_tolerance": 1e-10,
        },
        "endpoint_rows": endpoint_rows,
        "crossed_null_cells": null_rows,
        "crossed_null_contrasts": contrast_rows,
        "scientific_limits": [
            "Retrospective rates are not prospective validation.",
            "Fresh null evaluation measures null behaviour, not alternative-generator power.",
            "The crossed four-cell diagnostic cannot establish a unique phase or chance cause.",
            "The effect cutoff is diagnostic and is not a detector of an identifiable cause.",
        ],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    _plot(output, truths, endpoint_rows, null_rows)
    return SynthesisResult(
        summary,
        retro_p,
        retro_p_bb,
        retro_c99,
        fresh_p,
        fresh_p_bb,
        fresh_c99,
        bootstrap,
    )


def benchmark_full_shape(draws: int = 2, seed: int = 1701) -> dict[str, float | int]:
    """Time bootstrap mechanics on a deterministic full-shape synthetic fixture."""
    if not 1 <= draws <= 10:
        raise ValueError("fixture timing uses between one and ten draws")
    rng = np.random.default_rng(seed)
    nodes = 181
    truths = 6
    reference = rng.normal(size=(nodes, CALIBRATION_REPLICATES))
    cal_lr = rng.exponential(size=(nodes, CALIBRATION_REPLICATES))
    old_scores = rng.normal(size=(truths, EVALUATION_REPLICATES))
    old_profiles = rng.exponential(size=(truths, EVALUATION_REPLICATES, nodes))
    old_profiles -= old_profiles.min(axis=-1, keepdims=True)
    fresh_cal = rng.exponential(size=CALIBRATION_REPLICATES)
    fresh_scores = rng.normal(size=(1, EVALUATION_REPLICATES))
    fresh_profiles = rng.exponential(size=(1, EVALUATION_REPLICATES, nodes))
    fresh_profiles -= fresh_profiles.min(axis=-1, keepdims=True)
    result = calibration_aware_bootstrap(
        reference,
        cal_lr,
        old_scores,
        old_profiles,
        np.asarray([0, 20, 40, 60, 80, 180], dtype=np.int64),
        fresh_cal,
        fresh_scores,
        fresh_profiles,
        draws=draws,
        seed=seed,
    )
    return {
        "fixture_draws": draws,
        "fixture_seconds": result.seconds,
        "projected_1000_draw_seconds": result.seconds * BOOTSTRAP_DRAWS / draws,
        "nodes": nodes,
        "calibration_replicates": CALIBRATION_REPLICATES,
        "evaluation_replicates": EVALUATION_REPLICATES,
    }


def _plot(
    output: Path,
    truths: FloatArray,
    endpoint_rows: list[dict[str, Any]],
    null_rows: list[dict[str, Any]],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8), layout="constrained")
    retro = [
        row
        for row in endpoint_rows
        if row["block"] == "retrospective_baseline"
        and row["endpoint"] == "detector_rejection"
    ]
    values = np.asarray([row["estimate"] for row in retro])
    low = np.asarray([row["conditional_wilson_low"] for row in retro])
    high = np.asarray([row["conditional_wilson_high"] for row in retro])
    axes[0].errorbar(truths, values, yerr=(values - low, high - values), fmt="o-")
    axes[0].axhline(0.05, color="black", ls="--", lw=1)
    axes[0].set(
        xlabel="Generating effect h",
        ylabel="Detector rejection frequency",
        title="Retrospective baseline (six truths)",
        ylim=(-0.02, 1.02),
    )

    fresh = [
        row
        for row in endpoint_rows
        if row["block"] == "fresh_null_prospective"
    ]
    labels = ["Detector\nrejection", "C99 truth\ninclusion", "Effect-set\nnull exclusion"]
    fvalues = np.asarray([row["estimate"] for row in fresh])
    flow = np.asarray([row["conditional_wilson_low"] for row in fresh])
    fhigh = np.asarray([row["conditional_wilson_high"] for row in fresh])
    axes[1].errorbar(
        np.arange(3), fvalues, yerr=(fvalues - flow, fhigh - fvalues), fmt="o", capsize=3
    )
    axes[1].set_xticks(np.arange(3), labels)
    axes[1].set(
        ylabel="Frequency",
        title="Fresh null (prospective)",
        ylim=(-0.02, 1.02),
    )

    x = np.arange(2)
    old = np.asarray([null_rows[0]["estimate"], null_rows[2]["estimate"]])
    new = np.asarray([null_rows[1]["estimate"], null_rows[3]["estimate"]])
    width = 0.34
    axes[2].bar(x - width / 2, old, width, label="Retrospective evaluation")
    axes[2].bar(x + width / 2, new, width, label="Fresh evaluation")
    axes[2].set_xticks(x, ("Original cutoff", "Fresh cutoff"))
    axes[2].set(
        ylabel="Effect-set null exclusion frequency",
        title="Crossed rank-950 null diagnostic",
        ylim=(0, max(0.12, float(max(old.max(), new.max()) * 1.25))),
    )
    axes[2].legend(fontsize=8)
    fig.suptitle("Goal 050 model-adequacy qualification; Wilson intervals condition on tables")
    fig.savefig(output / "model_adequacy.png", dpi=200)
    fig.savefig(output / "model_adequacy.pdf")
    plt.close(fig)
