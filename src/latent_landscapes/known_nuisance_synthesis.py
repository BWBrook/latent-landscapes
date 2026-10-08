"""Paired uncertainty for the registered, known-nuisance calibration experiment.

This evaluator consumes frozen score arrays. It does not fit models or generate
histories. Calibration indices are shared across nodes, and evaluation indices
across paired truths, methods and numerical variants.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.stats import binom, chi2  # type: ignore[import-untyped]

from latent_landscapes.goal002.calibration import wilson_interval

FloatArray = NDArray[np.float64]
VARIANTS = (
    "low_k65536_alpha050",
    "high_k131072_alpha100",
    "high_k131072_alpha050",
    "high_k131072_alpha025",
)
METHODS = ("candidate", "oracle_flat", "null_flat", "chi_square")
METRICS = (
    "truth_inclusion",
    "null_exclusion",
    "log_hull_span",
    "cardinality",
    "components",
    "boundary_contact",
    "disconnected",
    "absolute_log_error",
)
TOLERANCES = {
    "truth_inclusion": 0.01,
    "null_exclusion": 0.01,
    "log_hull_span": 0.01,
    "boundary_contact": 0.01,
    "disconnected": 0.01,
    "absolute_log_error": 0.005,
}


def quantile_bands(scores: FloatArray, probability: float = 0.95) -> FloatArray:
    """Pointwise distribution-free order-statistic CI for a population quantile.

    With N samples and B~Bin(N,p), choose [X_(l),X_(u)] so P(l<=B<u)>=.95.
    Endpoints outside 1..N are infinite. Atoms require conservative interpretation.
    """
    n = scores.shape[-1]
    lower = int(binom.ppf(0.025, n, probability))
    upper = int(binom.ppf(0.975, n, probability)) + 1
    ordered = np.sort(scores, axis=-1)
    lo = ordered[..., lower - 1] if lower else np.full(scores.shape[:-1], -np.inf)
    hi = ordered[..., upper - 1] if upper <= n else np.full(scores.shape[:-1], np.inf)
    return np.stack((lo, hi), axis=-1)


def evaluate_sets(
    drops: FloatArray,
    cutoffs: FloatArray,
    effects: FloatArray,
    truths: FloatArray,
) -> FloatArray:
    """Return [variant,method,truth,replicate,metric] from evaluator-owned truths."""
    indices: NDArray[np.int64] = np.asarray(
        [int(np.flatnonzero(np.isclose(effects, h))[0]) for h in truths], dtype=np.int64
    )
    if drops.ndim != 4 or drops.shape[-1] != len(effects):
        raise ValueError("drops must have variant, truth, replicate and node axes")
    if cutoffs.shape != (drops.shape[0], len(effects)) or len(truths) != drops.shape[1]:
        raise ValueError("cutoffs and truth dimensions must match")
    if (
        not np.isfinite(drops).all()
        or not np.isfinite(cutoffs).all()
        or (drops < 0).any()
        or (cutoffs < 0).any()
    ):
        raise ValueError("scores and cutoffs must be finite nonnegative LR values")
    mle = np.argmin(drops, axis=-1)
    error = np.abs(np.log(effects[mle] / truths[None, :, None]))
    result = np.empty((*drops.shape[:1], len(METHODS), *drops.shape[1:3], len(METRICS)))
    for method in range(len(METHODS)):
        if method == 0:
            cutoff = cutoffs[:, None, None, :]
        elif method == 1:
            cutoff = cutoffs[:, indices, None, None]
        elif method == 2:
            cutoff = cutoffs[:, :1, None, None]
        else:
            cutoff = np.asarray(chi2.ppf(0.95, 1))
        inside = drops <= cutoff
        counts = inside.sum(axis=-1)
        if (counts == 0).any():
            raise ValueError("full-grid set lost all maximizers")
        first = np.argmax(inside, axis=-1)
        last = len(effects) - 1 - np.argmax(inside[..., ::-1], axis=-1)
        components = inside[..., 0].astype(int) + np.sum(
            inside[..., 1:] & ~inside[..., :-1], axis=-1
        )
        truth_member = np.take_along_axis(inside, indices[None, :, None, None], axis=-1)[..., 0]
        result[:, method] = np.stack(
            (
                truth_member,
                ~inside[..., 0],
                np.log(effects[last] / effects[first]),
                counts,
                components,
                inside[..., 0] | inside[..., -1],
                components > 1,
                error,
            ),
            axis=-1,
        )
    if not np.array_equal(result[:, 0, ..., 0], result[:, 1, ..., 0]):
        raise ValueError("candidate/oracle truth-membership identity failed")
    null = np.flatnonzero(np.isclose(truths, 1))
    if len(null) and not np.array_equal(result[:, 0, null, :, 1], result[:, 1, null, :, 1]):
        raise ValueError("null-size identity failed")
    return result


def paired_bootstrap(
    calibration_truth_scores: FloatArray,
    evaluation_drops: FloatArray,
    effects: FloatArray,
    truths: FloatArray,
    rank: int,
    *,
    draws: int = 2000,
    seed: int = 2026092003,
) -> tuple[FloatArray, float]:
    """Resample whole histories, independently by phase; preserve all pairing."""
    if draws < 2 or not 1 <= rank <= calibration_truth_scores.shape[-1]:
        raise ValueError("bootstrap count/rank invalid")
    cal_rng, eval_rng = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(2)]
    ncal, neval = calibration_truth_scores.shape[-1], evaluation_drops.shape[-2]
    output = np.empty((draws, evaluation_drops.shape[0], len(METHODS), len(truths), len(METRICS)))
    start = time.monotonic()
    for draw in range(draws):
        ci = cal_rng.integers(ncal, size=ncal)
        ei = eval_rng.integers(neval, size=neval)
        cutoffs = np.partition(calibration_truth_scores[..., ci], rank - 1, axis=-1)[..., rank - 1]
        # Multiplicities avoid copying all 181 profile values for repeated histories.
        weights = np.bincount(ei, minlength=neval) / neval
        metrics = evaluate_sets(evaluation_drops, cutoffs, effects, truths)
        output[draw] = np.einsum("vmtrk,r->vmtk", metrics, weights)
    return output, time.monotonic() - start


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_synthesis(
    output: Path,
    calibration: FloatArray,
    evaluation: FloatArray,
    effects: FloatArray,
    truths: FloatArray,
    variants: list[str],
    rank: int,
    *,
    holdout: FloatArray,
    paired_across_truths: bool,
    draws: int = 2000,
    seed: int = 2026092003,
) -> dict[str, Any]:
    """Write numerical results; caller verifies provenance before this evaluator."""
    if tuple(variants) != VARIANTS:
        raise ValueError("variant identities/order differ from the registered comparison")
    if not paired_across_truths:
        raise ValueError("shared resampling requires receipt-certified CRN history pairing")
    if holdout.shape != evaluation.shape or not np.isfinite(holdout).all():
        raise ValueError("frozen holdout score curves are required for prediction context")
    output.mkdir(parents=True, exist_ok=False)
    if calibration.shape[:2] != (len(variants), len(effects)):
        raise ValueError("calibration truth-score table must cover every node")
    cutoffs = np.partition(calibration, rank - 1, axis=-1)[..., rank - 1]
    values = evaluate_sets(evaluation, cutoffs, effects, truths)
    means = values.mean(axis=-2)
    bootstrap, seconds = paired_bootstrap(
        calibration, evaluation, effects, truths, rank, draws=draws, seed=seed
    )
    np.save(output / "bootstrap_means.npy", bootstrap)
    np.save(output / "cutoffs.npy", cutoffs)
    bands = quantile_bands(calibration)
    rows: list[dict[str, Any]] = []
    for v, variant in enumerate(variants):
        for m, method in enumerate(METHODS):
            for t, truth in enumerate(truths):
                for k, metric in enumerate(METRICS):
                    samples = bootstrap[:, v, m, t, k]
                    low, high = np.quantile(samples, [0.025, 0.975])
                    row: dict[str, Any] = dict(
                        variant=variant,
                        method=method,
                        truth=float(truth),
                        metric=metric,
                        mean=float(means[v, m, t, k]),
                        n=evaluation.shape[2],
                        calibration_aware_se=float(samples.std(ddof=1)),
                        calibration_aware_low=float(low),
                        calibration_aware_high=float(high),
                        conditional_binomial_low="",
                        conditional_binomial_high="",
                    )
                    if metric in {
                        "truth_inclusion",
                        "null_exclusion",
                        "boundary_contact",
                        "disconnected",
                    }:
                        interval = wilson_interval(
                            int(values[v, m, t, :, k].sum()), evaluation.shape[2]
                        )
                        row.update(
                            conditional_binomial_low=interval.lower,
                            conditional_binomial_high=interval.upper,
                        )
                    rows.append(row)
    _write_csv(output / "outcomes.csv", rows)
    contrasts: list[dict[str, Any]] = []
    # Primary numerical comparison plus all candidate-minus-comparator method contrasts.
    pairs = [(1, 0, 0, 0, "matched_bank_high_minus_low")] + [
        (v, 0, v, m, "candidate_minus_" + METHODS[m])
        for v in range(len(variants))
        for m in range(1, 4)
    ]
    pairs += [
        (a, 0, b, 0, "fixed_high_bank_alpha_sensitivity") for a, b in ((1, 2), (1, 3), (2, 3))
    ]
    for va, ma, vb, mb, label in pairs:
        for t, truth in enumerate(truths):
            for k, metric in enumerate(METRICS):
                delta = float(means[va, ma, t, k] - means[vb, mb, t, k])
                samples = bootstrap[:, va, ma, t, k] - bootstrap[:, vb, mb, t, k]
                lo, hi = np.quantile(samples, [0.025, 0.975])
                se = float(samples.std(ddof=1))
                # Reference endpoint SE, not the SE of a paired numerical difference.
                reference_se = float(bootstrap[:, va, ma, t, k].std(ddof=1))
                tol = TOLERANCES.get(metric) if label == "matched_bank_high_minus_low" else None
                contrasts.append(
                    dict(
                        comparison=label,
                        variant_a=variants[va],
                        variant_b=variants[vb],
                        truth=float(truth),
                        metric=metric,
                        change=delta,
                        paired_se=se,
                        low=float(lo),
                        high=float(hi),
                        reference_endpoint_se=reference_se,
                        movement_over_reference_se=abs(delta) / reference_se
                        if reference_se > 0
                        else "",
                        absolute_tolerance=tol if tol is not None else "",
                        within_tolerance=abs(delta) <= tol if tol is not None else "",
                    )
                )
    _write_csv(output / "contrasts.csv", contrasts)
    cutoff_rows = [
        dict(
            variant=variants[v],
            effect=float(g),
            cutoff=float(cutoffs[v, i]),
            pointwise_quantile_low=float(bands[v, i, 0]),
            pointwise_quantile_high=float(bands[v, i, 1]),
            zero_score_fraction=float(np.mean(calibration[v, i] == 0)),
        )
        for v in range(len(variants))
        for i, g in enumerate(effects)
    ]
    _write_csv(output / "cutoff_curve.csv", cutoff_rows)
    membership_rows = []
    all_membership = evaluation <= cutoffs[:, None, None, :]
    disagreement = all_membership[1] != all_membership[0]
    np.save(output / "matched_bank_membership_changes.npy", disagreement)
    _write_csv(
        output / "matched_bank_membership_changes.csv",
        [
            dict(
                truth=float(h),
                candidate=float(g),
                disagreement_frequency=float(disagreement[t, :, i].mean()),
                high_only_frequency=float(
                    (all_membership[1, t, :, i] & ~all_membership[0, t, :, i]).mean()
                ),
                low_only_frequency=float(
                    (all_membership[0, t, :, i] & ~all_membership[1, t, :, i]).mean()
                ),
            )
            for t, h in enumerate(truths)
            for i, g in enumerate(effects)
        ],
    )
    prediction = (
        np.take_along_axis(holdout, np.argmin(evaluation, axis=-1)[..., None], axis=-1)[..., 0]
        - holdout[..., 0]
    )
    prediction_rng = np.random.default_rng(np.random.SeedSequence(seed).spawn(2)[1])
    prediction_boot = np.empty((draws, len(variants), len(truths)))
    for draw in range(draws):
        indices = prediction_rng.integers(evaluation.shape[2], size=evaluation.shape[2])
        prediction_boot[draw] = prediction[:, :, indices].mean(axis=-1)
    _write_csv(
        output / "prediction_context.csv",
        [
            dict(
                variant=variant,
                truth=float(h),
                mean_advantage=float(prediction[v, t].mean()),
                low=float(np.quantile(prediction_boot[:, v, t], 0.025)),
                high=float(np.quantile(prediction_boot[:, v, t], 0.975)),
                se=float(prediction_boot[:, v, t].std(ddof=1)),
                calibration_method_identity=True,
                interpretation="Same fitted MLE and holdout score for every set construction",
            )
            for v, variant in enumerate(variants)
            for t, h in enumerate(truths)
        ],
    )

    for v, variant in enumerate(variants):
        candidate = evaluation[v] <= cutoffs[v, None, None, :]
        oracle = (
            evaluation[v]
            <= cutoffs[v, [int(np.argmin(abs(effects - h))) for h in truths], None, None]
        )
        chi = evaluation[v] <= chi2.ppf(0.95, 1)
        for t, truth in enumerate(truths):
            for i, g in enumerate(effects):
                membership_rows.append(
                    dict(
                        variant=variant,
                        truth=float(truth),
                        candidate=float(g),
                        candidate_inclusion=float(candidate[t, :, i].mean()),
                        oracle_inclusion=float(oracle[t, :, i].mean()),
                        chi_square_inclusion=float(chi[t, :, i].mean()),
                        candidate_oracle_disagreement=float(
                            (candidate[t, :, i] != oracle[t, :, i]).mean()
                        ),
                        candidate_chi_square_disagreement=float(
                            (candidate[t, :, i] != chi[t, :, i]).mean()
                        ),
                    )
                )
    _write_csv(output / "candidate_membership.csv", membership_rows)
    interior = (effects >= 2) & (effects <= 8)
    primary = cutoffs[1]
    summary: dict[str, Any] = dict(
        scope="known nuisance, fixed reference map, finite effect grid; no exact-integration claim",
        matched_bank_any_membership_change_frequency=disagreement.any(axis=-1)
        .mean(axis=-1)
        .tolist(),
        prediction_method_identity=(
            "All set methods share frozen fitted MLE and holdout profiles; "
            "no predictive gain is attributed to calibration."
        ),
        bootstrap_pairing=(
            "CRN replicate pairing across truths and variants; "
            "calibration/evaluation phases independent"
        ),
        bootstrap_draws=draws,
        bootstrap_seed=seed,
        bootstrap_seconds=seconds,
        p1_boundary_to_interior_median=float(primary[0] / np.median(primary[interior])),
        p1_ratio_prediction=bool(primary[0] / np.median(primary[interior]) <= 0.85),
        p2_fraction_outside_30pct=float(
            np.mean(
                (primary[interior] < 0.7 * chi2.ppf(0.95, 1))
                | (primary[interior] > 1.3 * chi2.ppf(0.95, 1))
            )
        ),
        p2_interior_max_min=float(primary[interior].max() / primary[interior].min()),
        primary_tolerance_failures=[r for r in contrasts if r["within_tolerance"] is False],
        uncertainty_note=(
            "Pointwise quantile bands and conditional Wilson intervals are distinct "
            "from paired calibration-aware bootstrap intervals."
        ),
    )
    summary["p1_null_flat_truth_inclusion"] = {
        str(h): float(means[1, 2, int(np.flatnonzero(truths == h)[0]), 0])
        for h in (3.0, 5.0)
        if h in truths
    }
    summary["p1_candidate_minus_oracle_power"] = {
        str(h): float(
            means[1, 0, int(np.flatnonzero(truths == h)[0]), 1]
            - means[1, 1, int(np.flatnonzero(truths == h)[0]), 1]
        )
        for h in (3.0, 5.0)
        if h in truths
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    _plot(output, effects, truths, variants, cutoffs, bands, means, calibration, bootstrap)
    return summary


def _plot(
    output: Path,
    effects: FloatArray,
    truths: FloatArray,
    variants: list[str],
    cutoffs: FloatArray,
    bands: FloatArray,
    means: FloatArray,
    calibration: FloatArray,
    bootstrap: FloatArray,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6), layout="constrained")
    for v in (0, 1):
        axes[0].plot(effects, cutoffs[v], label=variants[v])
    axes[0].fill_between(
        effects,
        bands[1, :, 0],
        bands[1, :, 1],
        alpha=0.18,
        label="High-bank pointwise 95% quantile CI",
    )
    axes[0].axhline(chi2.ppf(0.95, 1), ls="--", color="black", label="Chi-square(1), 95%")
    axes[0].axhline(chi2.ppf(0.9, 1), ls=":", color="grey", label="Chi-square(1), 90%")
    axes[0].set(
        xlabel="Candidate effect",
        ylabel="Calibrated LR cutoff",
        title="Known-nuisance candidate calibration",
    )
    axes[0].legend(fontsize=7)
    zero = np.mean(calibration[1] == 0, axis=-1)
    axes[0].text(
        0.98,
        0.02,
        f"Zero LR: h=1 {zero[0]:.1%}; h=10 {zero[-1]:.1%}",
        transform=axes[0].transAxes,
        ha="right",
        fontsize=8,
    )
    for m in (0, 1, 2, 3):
        axes[1].plot(truths, means[1, m, :, 2], marker="o", label=METHODS[m])
    axes[1].set(
        xlabel="Generating effect",
        ylabel="Mean log hull span",
        title="High-bank set resolution (hull summary)",
    )
    axes[1].legend(fontsize=8)
    for m in range(4):
        line = axes[2].plot(truths, means[1, m, :, 1], marker="o", label=METHODS[m])[0]
        low, high = np.quantile(bootstrap[:, 1, m, :, 1], [0.025, 0.975], axis=0)
        axes[2].fill_between(truths, low, high, color=line.get_color(), alpha=0.10)
    axes[2].set(
        xlabel="Generating effect",
        ylabel="Frequency of excluding effect 1",
        title="Null size at h=1; non-null power elsewhere",
        ylim=(-0.02, 1.02),
    )
    axes[2].legend(fontsize=8)
    fig.suptitle("Fixed reference map and supplied nuisance values; pointwise uncertainty")
    fig.savefig(output / "calibration_resolution.png", dpi=180)
    fig.savefig(output / "calibration_resolution.pdf")
    plt.close(fig)
