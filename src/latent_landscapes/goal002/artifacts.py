"""Deterministic ten-file human review bundle for Goal 002."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping, Sequence
from math import isfinite
from pathlib import Path
from statistics import median
from typing import Any

import matplotlib
from matplotlib import pyplot as plt
from matplotlib.figure import Figure

matplotlib.use("Agg")

from .benchmark import CalibrationSummary, Goal002Result, ValidationSummary
from .calibration import EstimateInterval, MleInterval

DEFAULT_OUTPUT_DIR = Path("artifacts/goal002_detection_calibration")
ROOT_FILES = (
    "seed_manifest.csv",
    "replicate_results.csv",
    "calibration_summary.csv",
    "predictive_summary.csv",
    "summary.json",
    "verification.json",
    "review.md",
)
VISUAL_FILES = (
    "coverage_support.svg",
    "mle_recovery.svg",
    "predictive_scores.svg",
)

type CsvValue = str | int | float | bool
type CsvRow = Mapping[str, CsvValue]


def write_review_bundle(
    result: Goal002Result,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, ...]:
    if result.outcome == "implementation_blocked":
        raise ValueError("an implementation-blocked result has no scientific review bundle")
    target = Path(output_dir)
    visuals = target / "visuals"
    visuals.mkdir(parents=True, exist_ok=True)
    paths = {
        **{name: target / name for name in ROOT_FILES},
        **{name: visuals / name for name in VISUAL_FILES},
    }

    _write_csv(paths["seed_manifest.csv"], _seed_rows(result))
    _write_csv(paths["replicate_results.csv"], _replicate_rows(result))
    _write_csv(paths["calibration_summary.csv"], _calibration_summary_rows(result))
    _write_csv(paths["predictive_summary.csv"], _predictive_summary_rows(result))
    paths["summary.json"].write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    paths["verification.json"].write_text(
        json.dumps(_verification_payload(result), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    paths["review.md"].write_text(_render_review(result), encoding="utf-8")
    paths["coverage_support.svg"].write_text(_coverage_support_svg(result), encoding="utf-8")
    paths["mle_recovery.svg"].write_text(_mle_recovery_svg(result), encoding="utf-8")
    paths["predictive_scores.svg"].write_text(_predictive_scores_svg(result), encoding="utf-8")

    expected = {
        *ROOT_FILES,
        *(f"visuals/{name}" for name in VISUAL_FILES),
    }
    observed = {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()}
    if observed != expected:
        raise RuntimeError(
            f"artifact contract mismatch: expected {sorted(expected)}, got {sorted(observed)}"
        )
    return tuple(paths[name] for name in (*ROOT_FILES, *VISUAL_FILES))


def _seed_rows(result: Goal002Result) -> list[CsvRow]:
    return [
        {
            "phase": record.phase,
            "replicate_index": record.replicate_index,
            "entropy": record.entropy,
            "spawn_key": json.dumps(record.spawn_key, separators=(",", ":")),
            "pool_size": record.pool_size,
            "state_words": json.dumps(record.state, separators=(",", ":")),
        }
        for record in (*result.calibration_seeds, *result.validation_seeds)
    ]


def _replicate_rows(result: Goal002Result) -> list[CsvRow]:
    rows = [_calibration_row(summary) for summary in result.calibration_results]
    rows.extend(_validation_row(summary) for summary in result.validation_results)
    return rows


def _empty_replicate_row() -> dict[str, CsvValue]:
    return {
        "phase": "",
        "replicate_index": "",
        "record_count": "",
        "training_record_count": "",
        "holdout_record_count": "",
        "split_isolated": "",
        "no_false_positives": "",
        "lr_at_truth": "",
        "truth_log_likelihood": "",
        "maximum_log_likelihood": "",
        "nominal_truth_included": "",
        "calibrated_truth_included": "",
        "calibrated_support_component_count": "",
        "calibrated_support_boundary_contact": "",
        "calibrated_support_total_width": "",
        "mle_class_count": "",
        "mle_set": "",
        "mle_total_width": "",
        "truth_to_mle_distance": "",
        "habitat_partition_count": "",
        "habitat_log_score_minimum": "",
        "habitat_log_score_maximum": "",
        "habitat_brier_minimum": "",
        "habitat_brier_maximum": "",
        "habitat_impossible_positive_minimum": "",
        "habitat_impossible_positive_maximum": "",
        "habitat_any_zero_probability": "",
        "habitat_every_zero_probability": "",
        "neutral_log_score": "",
        "neutral_brier_score": "",
        "neutral_probability_minimum": "",
        "neutral_probability_maximum": "",
        "paired_brier_difference": "",
        "hard_front_partition_count": "",
        "hard_front_log_score_minimum": "",
        "hard_front_log_score_maximum": "",
        "hard_front_brier_minimum": "",
        "hard_front_brier_maximum": "",
        "hard_front_impossible_positive_minimum": "",
        "hard_front_impossible_positive_maximum": "",
        "hard_front_any_zero_probability": "",
        "hard_front_every_zero_probability": "",
    }


def _calibration_row(summary: CalibrationSummary) -> CsvRow:
    row = _empty_replicate_row()
    row.update(
        {
            "phase": "calibration",
            "replicate_index": summary.replicate_index,
            "record_count": summary.record_count,
            "no_false_positives": summary.no_false_positives,
            "lr_at_truth": summary.lr_at_truth,
            "truth_log_likelihood": summary.truth_log_likelihood,
            "maximum_log_likelihood": summary.maximum_log_likelihood,
        }
    )
    return row


def _validation_row(summary: ValidationSummary) -> CsvRow:
    row = _empty_replicate_row()
    row.update(
        {
            "phase": "validation",
            "replicate_index": summary.replicate_index,
            "record_count": summary.record_count,
            "training_record_count": summary.training_record_count,
            "holdout_record_count": summary.holdout_record_count,
            "split_isolated": summary.split_isolated,
            "no_false_positives": summary.no_false_positives,
            "lr_at_truth": summary.lr_at_truth,
            "truth_log_likelihood": summary.truth_log_likelihood,
            "maximum_log_likelihood": summary.maximum_log_likelihood,
            "nominal_truth_included": summary.nominal_truth_included,
            "calibrated_truth_included": summary.calibrated_truth_included,
            "calibrated_support_component_count": (summary.calibrated_support_component_count),
            "calibrated_support_boundary_contact": (summary.calibrated_support_boundary_contact),
            "calibrated_support_total_width": summary.calibrated_support_total_width,
            "mle_class_count": summary.mle_class_count,
            "mle_set": _mle_set_text(summary.mle_intervals),
            "mle_total_width": summary.mle_total_width,
            "truth_to_mle_distance": summary.truth_to_mle_distance,
            "habitat_partition_count": summary.habitat_partition_count,
            "habitat_log_score_minimum": summary.habitat_log_score_minimum,
            "habitat_log_score_maximum": summary.habitat_log_score_maximum,
            "habitat_brier_minimum": summary.habitat_brier_minimum,
            "habitat_brier_maximum": summary.habitat_brier_maximum,
            "habitat_impossible_positive_minimum": (summary.habitat_impossible_positive_minimum),
            "habitat_impossible_positive_maximum": (summary.habitat_impossible_positive_maximum),
            "habitat_any_zero_probability": summary.habitat_any_zero_probability,
            "habitat_every_zero_probability": summary.habitat_every_zero_probability,
            "neutral_log_score": summary.neutral_log_score,
            "neutral_brier_score": summary.neutral_brier_score,
            "neutral_probability_minimum": summary.neutral_probability_minimum,
            "neutral_probability_maximum": summary.neutral_probability_maximum,
            "paired_brier_difference": summary.paired_brier_difference,
            "hard_front_partition_count": summary.hard_front_partition_count,
            "hard_front_log_score_minimum": summary.hard_front_log_score_minimum,
            "hard_front_log_score_maximum": summary.hard_front_log_score_maximum,
            "hard_front_brier_minimum": summary.hard_front_brier_minimum,
            "hard_front_brier_maximum": summary.hard_front_brier_maximum,
            "hard_front_impossible_positive_minimum": (
                summary.hard_front_impossible_positive_minimum
            ),
            "hard_front_impossible_positive_maximum": (
                summary.hard_front_impossible_positive_maximum
            ),
            "hard_front_any_zero_probability": (summary.hard_front_any_zero_probability),
            "hard_front_every_zero_probability": (summary.hard_front_every_zero_probability),
        }
    )
    return row


def _calibration_summary_rows(result: Goal002Result) -> list[CsvRow]:
    statistics = sorted(summary.lr_at_truth for summary in result.calibration_results)
    return [
        {
            "calibration_replicates": len(statistics),
            "probability": result.cutoff.probability,
            "rank_one_based": result.cutoff.rank_one_based,
            "rank_zero_based": result.cutoff.rank_one_based - 1,
            "cutoff": result.cutoff.cutoff,
            "minimum_lr_at_truth": statistics[0],
            "median_lr_at_truth": median(statistics),
            "maximum_lr_at_truth": statistics[-1],
        }
    ]


def _predictive_summary_rows(result: Goal002Result) -> list[CsvRow]:
    aggregate = result.aggregate
    count = len(result.validation_results)
    return [
        {
            "validation_replicates": count,
            "nominal_coverage": aggregate.nominal_coverage.estimate,
            "nominal_wilson_lower": aggregate.nominal_coverage.lower,
            "nominal_wilson_upper": aggregate.nominal_coverage.upper,
            "calibrated_coverage": aggregate.calibrated_coverage.estimate,
            "calibrated_wilson_lower": aggregate.calibrated_coverage.lower,
            "calibrated_wilson_upper": aggregate.calibrated_coverage.upper,
            "topology_success_count": aggregate.topology_success_count,
            "topology_success_proportion": aggregate.topology_success_proportion,
            "paired_brier_mean": aggregate.paired_brier_interval.estimate,
            "paired_brier_normal_lower": aggregate.paired_brier_interval.lower,
            "paired_brier_normal_upper": aggregate.paired_brier_interval.upper,
            "neutral_finite_count": aggregate.neutral_finite_count,
            "habitat_finite_all_partitions_count": (aggregate.habitat_finite_all_partitions_count),
            "hard_front_finite_all_partitions_count": (
                aggregate.hard_front_finite_all_partitions_count
            ),
            "habitat_any_zero_probability_count": (aggregate.habitat_any_zero_probability_count),
            "habitat_every_zero_probability_count": (
                aggregate.habitat_every_zero_probability_count
            ),
            "hard_front_any_zero_probability_count": (
                aggregate.hard_front_any_zero_probability_count
            ),
            "hard_front_every_zero_probability_count": (
                aggregate.hard_front_every_zero_probability_count
            ),
            "mean_truth_to_mle_distance": aggregate.mean_truth_to_mle_distance,
            "outcome": result.outcome,
        }
    ]


def _summary_payload(result: Goal002Result) -> dict[str, object]:
    aggregate = result.aggregate
    validation_count = len(result.validation_results)
    return {
        "goal": "002-detection-noise-calibration",
        "outcome": result.outcome,
        "fixed_design": {
            "truth_rate": result.config.truth_rate,
            "rate_domain": [0.25, 4.0],
            "detection_probability": 0.65,
            "records_per_realization": 1920,
            "training_records_per_realization": 1440,
            "holdout_records_per_realization": 480,
            "process_stochasticity": False,
        },
        "seed_design": {
            "master_seed": result.config.master_seed,
            "phase_order": ["calibration", "validation"],
            "calibration_children": len(result.calibration_seeds),
            "validation_children": len(result.validation_seeds),
        },
        "calibration": {
            "truth_rate": result.config.truth_rate,
            "exact_truth_likelihood": True,
            "cutoff": {
                "probability": result.cutoff.probability,
                "rank_one_based": result.cutoff.rank_one_based,
                "rank_zero_based": result.cutoff.rank_one_based - 1,
                "sample_size": result.cutoff.sample_size,
                "value": result.cutoff.cutoff,
                "interpolation": False,
            },
        },
        "validation": {
            "replicates": validation_count,
            "nominal_lr_threshold": result.config.nominal_lr_threshold,
            "coverage": {
                "nominal": _estimate_payload(aggregate.nominal_coverage),
                "calibrated": _estimate_payload(aggregate.calibrated_coverage),
                "interval_method": "95% Wilson",
                "uncertainty_type": "Monte Carlo uncertainty",
            },
            "support_topology": {
                "success_definition": (
                    "one connected calibrated component strictly inside [0.25, 4]"
                ),
                "success_count": aggregate.topology_success_count,
                "success_proportion": aggregate.topology_success_proportion,
            },
            "mle_recovery": {
                "sets_preserved": True,
                "mean_distance_from_truth_to_mle_set": (aggregate.mean_truth_to_mle_distance),
            },
            "neutral_baseline": {
                "model": "time-specific Jeffreys-smoothed Bernoulli prevalence",
                "fit_scope": "training records only",
                "uses_spatial_or_truth_inputs": False,
                "full_support": aggregate.neutral_finite_count == validation_count,
                "finite_log_score_count": aggregate.neutral_finite_count,
            },
            "paired_brier": {
                **_estimate_payload(aggregate.paired_brier_interval),
                "definition": (
                    "maximum habitat training-MLE-partition mean Brier minus neutral mean Brier"
                ),
                "habitat_uses_worst_mle_partition": True,
                "interval_method": "95% normal Monte Carlo interval",
                "lower_is_better": True,
            },
            "habitat_diagnostics": {
                "finite_all_partition_log_score_count": (
                    aggregate.habitat_finite_all_partitions_count
                ),
                "any_zero_probability_count": (aggregate.habitat_any_zero_probability_count),
                "every_zero_probability_count": (aggregate.habitat_every_zero_probability_count),
            },
            "hard_front": {
                "model": "geometry-only hard-front comparator",
                "role": "diagnostic only",
                "finite_all_partition_log_score_count": (
                    aggregate.hard_front_finite_all_partitions_count
                ),
                "any_zero_probability_count": (aggregate.hard_front_any_zero_probability_count),
                "every_zero_probability_count": (aggregate.hard_front_every_zero_probability_count),
            },
        },
        "decision_precedence": [
            "implementation_blocked",
            "design_limited",
            "calibration_not_ready",
            "mechanism_inconclusive",
            "advance_stochastic_spread",
        ],
        "invariants": result.invariants,
        "limitations": [
            "calibration is conditional on rho = 1 for one frozen landscape and design",
            "process truth remains deterministic",
            "Wilson and normal intervals describe finite-ensemble Monte Carlo uncertainty",
            "per-realization exact support and MLE sets express inferential uncertainty",
            "hard-front log scores are diagnostics and do not determine the decision",
        ],
    }


def _verification_payload(result: Goal002Result) -> dict[str, object]:
    return {
        "goal": "002-detection-noise-calibration",
        "outcome": result.outcome,
        "production_defaults": {
            "active": result.config.is_production,
            "master_seed": result.config.master_seed,
            "calibration_replicates": result.config.calibration_replicates,
            "validation_replicates": result.config.validation_replicates,
            "calibration_rank_one_based": result.config.calibration_rank_one_based,
        },
        "invariants": result.invariants,
        "all_invariants_pass": all(result.invariants.values()),
        "expected_artifact_file_count": 10,
        "observed_artifact_file_count": 10,
        "retains_raw_ensemble_observations": False,
        "retains_likelihood_profiles": False,
        "retains_prediction_signatures": False,
    }


def _render_review(result: Goal002Result) -> str:
    aggregate = result.aggregate
    validation_count = len(result.validation_results)
    calibrated = aggregate.calibrated_coverage
    paired = aggregate.paired_brier_interval
    inference = {
        "design_limited": (
            "The fixed observation design does not yield the prespecified frequency of "
            "single, interior calibrated support intervals."
        ),
        "calibration_not_ready": (
            "Support topology passes, but calibrated validation coverage is not yet "
            "compatible with 0.95 under the frozen Wilson criterion."
        ),
        "mechanism_inconclusive": (
            "Calibration and topology pass, but the paired Brier evidence does not "
            "establish a predictive advantage for habitat-aware spread."
        ),
        "advance_stochastic_spread": (
            "Under this frozen design and truth, calibration passes and the habitat-aware "
            "spread model has a graded predictive advantage over the neutral baseline."
        ),
    }[result.outcome]
    return f"""# Goal 002 Detection-Noise Calibration Review

**Decision class:** `{result.outcome}`

## Observation

The calibration phase used {len(result.calibration_results)} fixed child seeds. Its
prespecified rank-{result.cutoff.rank_one_based} likelihood-ratio cutoff was
{_number(result.cutoff.cutoff)}. The separate validation phase used {validation_count}
child seeds.

Nominal truth coverage was {_percent(aggregate.nominal_coverage.estimate)}
(95% Wilson interval {_percent(aggregate.nominal_coverage.lower)} to
{_percent(aggregate.nominal_coverage.upper)}). Calibrated truth coverage was
{_percent(calibrated.estimate)} (95% Wilson interval {_percent(calibrated.lower)} to
{_percent(calibrated.upper)}).

{aggregate.topology_success_count} of {validation_count} calibrated supports
({_percent(aggregate.topology_success_proportion)}) were one connected interval
strictly inside `[0.25, 4]`. The mean paired Brier difference, defined as the maximum
habitat MLE-partition score minus the neutral score, was
{_number(paired.estimate)} (95% normal Monte Carlo interval
{_number(paired.lower)} to {_number(paired.upper)}).

The time-stratified Jeffreys-smoothed neutral baseline retained full support and had
finite log score in
{aggregate.neutral_finite_count} of {validation_count} realizations. It was fitted from
training records only and used no coordinates, habitat, conductance, sources, path
costs, latent arrivals, truth labels, or holdout outcomes.

The geometry-only hard-front comparator assigned zero probability to at least one
held-out detection in {aggregate.hard_front_any_zero_probability_count} realizations
and did so for every training-MLE partition in
{aggregate.hard_front_every_zero_probability_count} realizations. These are diagnostic
structural-support results, not the graded decision evidence.

## Inference

{inference}

This inference is conditional on the fixed landscape, deterministic `rho = 1` truth,
survey design, known detection probability, and zero generating false positives. A
negative decision class is a completed result and has not triggered retuning.

## Assumptions

- The Goal 001 landscape, source cells, conductance, design, rate domain, and endpoint
  conventions are fixed and correctly reconciled.
- Detection probability is known and constant at `0.65`; generating false-positive
  probability is zero.
- Calibration and validation children are fixed, separate, replayable, and analyzed
  without filtering or extension.
- Habitat prediction retains every training-MLE partition; the primary comparison uses
  the worst habitat MLE-partition Brier score.
- The full-support neutral model is a non-spatial predictive baseline, while the
  geometry-only hard-front comparator remains diagnostic only.

## Limitations

Monte Carlo uncertainty describes the finite detection ensemble; inferential uncertainty
describes each realization's exact support components and set-valued MLE. The Wilson
coverage intervals and paired-Brier normal interval quantify the former, not the latter.

Calibration is established only at `rho = 1` for this frozen landscape and observation
design. It does not establish coverage over other rates, landscapes, detection
conditions, or process-stochastic systems. No stochastic spread, additional focal
parameter, prey dynamics, real data, MCMC, ABC, or survey redesign is included.
"""


def _coverage_support_svg(result: Goal002Result) -> str:
    aggregate = result.aggregate
    coverage = (aggregate.nominal_coverage, aggregate.calibrated_coverage)
    with plt.rc_context(_svg_rc()):
        figure, axes = plt.subplots(1, 2, figsize=(10.2, 4.5), layout="constrained")
        estimates = [value.estimate for value in coverage]
        lower_errors = [value.estimate - value.lower for value in coverage]
        upper_errors = [value.upper - value.estimate for value in coverage]
        axes[0].errorbar(
            (0, 1),
            estimates,
            yerr=(lower_errors, upper_errors),
            fmt="o",
            color="#176b5b",
            ecolor="#222222",
            capsize=5,
            markersize=7,
        )
        axes[0].axhline(0.95, color="#c23b32", linestyle="--", linewidth=1.4)
        axes[0].set_xticks((0, 1), ("Nominal", "Calibrated"))
        axes[0].set_ylim(0.0, 1.02)
        axes[0].set_ylabel("Truth inclusion proportion")
        axes[0].set_title("Validation truth coverage")
        axes[0].text(
            0.02,
            0.04,
            "Points: estimates\nBars: 95% Wilson intervals\nDashed line: 0.95",
            transform=axes[0].transAxes,
            fontsize=9,
            va="bottom",
        )

        proportion = aggregate.topology_success_proportion
        axes[1].bar((0,), (proportion,), color="#3465a4", width=0.55)
        axes[1].axhline(0.95, color="#c23b32", linestyle="--", linewidth=1.4)
        axes[1].set_xticks((0,), ("Single interior\ncomponent",))
        axes[1].set_ylim(0.0, 1.02)
        axes[1].set_ylabel("Validation proportion")
        axes[1].set_title("Calibrated support topology")
        axes[1].text(
            0,
            min(0.98, proportion + 0.035),
            f"{aggregate.topology_success_count}/{len(result.validation_results)}",
            ha="center",
        )
        figure.suptitle("Coverage calibration and support topology")
        return _figure_svg(figure)


def _mle_recovery_svg(result: Goal002Result) -> str:
    validation = result.validation_results
    indices = [summary.replicate_index for summary in validation]
    distances = [summary.truth_to_mle_distance for summary in validation]
    widths = [summary.mle_total_width for summary in validation]
    with plt.rc_context(_svg_rc()):
        figure, axes = plt.subplots(1, 2, figsize=(10.2, 4.5), layout="constrained")
        axes[0].scatter(indices, distances, s=20, color="#176b5b", alpha=0.72)
        axes[0].axhline(0.0, color="#222222", linewidth=1.0)
        axes[0].set_xlabel("Validation replicate index")
        axes[0].set_ylabel("Distance from rho = 1 to MLE set")
        axes[0].set_title("Truth-to-MLE-set distance")
        axes[1].hist(widths, bins=min(24, max(5, len(widths))), color="#a85d19")
        axes[1].set_xlabel("Total MLE-set width")
        axes[1].set_ylabel("Validation replicate count")
        axes[1].set_title("Set-valued MLE width")
        figure.suptitle("MLE-set recovery across validation replicates")
        return _figure_svg(figure)


def _predictive_scores_svg(result: Goal002Result) -> str:
    validation = result.validation_results
    indices = [summary.replicate_index for summary in validation]
    differences = [summary.paired_brier_difference for summary in validation]
    habitat = [summary.habitat_brier_maximum for summary in validation]
    neutral = [summary.neutral_brier_score for summary in validation]
    interval = result.aggregate.paired_brier_interval
    with plt.rc_context(_svg_rc()):
        figure, axes = plt.subplots(1, 2, figsize=(10.2, 4.5), layout="constrained")
        axes[0].scatter(indices, differences, s=20, color="#3465a4", alpha=0.7)
        axes[0].axhline(0.0, color="#222222", linewidth=1.0)
        axes[0].axhline(interval.estimate, color="#c23b32", linewidth=1.5)
        axes[0].axhspan(interval.lower, interval.upper, color="#c23b32", alpha=0.14)
        axes[0].set_xlabel("Validation replicate index")
        axes[0].set_ylabel("Worst habitat Brier - neutral Brier")
        axes[0].set_title("Paired Brier differences")

        axes[1].scatter(neutral, habitat, s=22, color="#176b5b", alpha=0.7)
        bounds = (
            min((*neutral, *habitat)),
            max((*neutral, *habitat)),
        )
        axes[1].plot(bounds, bounds, color="#222222", linestyle="--", linewidth=1.0)
        axes[1].set_xlabel("Neutral mean Brier score")
        axes[1].set_ylabel("Worst habitat MLE-partition Brier")
        axes[1].set_title("Habitat versus full-support neutral")
        figure.suptitle("Paired predictive scores")
        return _figure_svg(figure)


def _write_csv(path: Path, rows: Sequence[CsvRow]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path.name}")
    columns = tuple(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_csv_value(row[column]) for column in columns])


def _csv_value(value: CsvValue) -> str | int:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value == float("-inf"):
            return "-inf"
        if value == float("inf"):
            return "inf"
        return format(value, ".17g")
    return value


def _estimate_payload(interval: EstimateInterval) -> dict[str, float]:
    return {
        "estimate": interval.estimate,
        "lower": interval.lower,
        "upper": interval.upper,
    }


def _mle_set_text(intervals: tuple[MleInterval, ...]) -> str:
    return ";".join(
        (
            ("[" if lower_closed else "(")
            + f"{format(lower, '.17g')},{format(upper, '.17g')}"
            + ("]" if upper_closed else ")")
        )
        for lower, upper, lower_closed, upper_closed in intervals
    )


def _number(value: float) -> str:
    if not isfinite(value):
        return "-Infinity" if value < 0.0 else "Infinity"
    return format(value, ".6g")


def _percent(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def _svg_rc() -> Any:
    return {
        "svg.hashsalt": "latent-landscapes-goal002",
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
    }


def _figure_svg(figure: Figure) -> str:
    buffer = io.StringIO()
    figure.savefig(
        buffer,
        format="svg",
        metadata={"Date": None, "Creator": "Latent Landscapes Goal 002"},
    )
    plt.close(figure)
    return buffer.getvalue()
