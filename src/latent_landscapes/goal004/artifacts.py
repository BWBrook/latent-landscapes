"""Deterministic 12-file review bundle for Goal 004."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.figure import Figure

from .benchmark import (
    BANK_VARIANT_NAMES,
    SOURCE_IDENTITY,
    BankSummary,
    Goal004Result,
)

DEFAULT_OUTPUT_DIR = Path("artifacts/goal004_stochastic_one_rate_recovery")
ROOT_FILES = (
    "config.json",
    "seed_manifest.csv",
    "calibration_results.csv",
    "validation_results.csv",
    "bank_stability_summary.csv",
    "predictive_summary.csv",
    "representative_profile.csv",
    "summary.json",
    "verification.json",
    "review.md",
)
VISUAL_FILES = (
    "recovery_calibration.svg",
    "predictive_comparison.svg",
)
EXPECTED_FILE_COUNT = 12
BETWEEN_SITE_LIMITATION = "omitted"

type CsvValue = str | int | float | bool
type CsvRow = Mapping[str, CsvValue]


def write_review_bundle(
    result: Goal004Result,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, ...]:
    """Write and reconcile the exact deterministic Goal 004 review surface."""
    if result.outcome == "implementation_blocked":
        raise ValueError("an implementation-blocked result has no scientific review bundle")
    target = Path(output_dir)
    visuals = target / "visuals"
    visuals.mkdir(parents=True, exist_ok=True)
    paths = {
        **{name: target / name for name in ROOT_FILES},
        **{name: visuals / name for name in VISUAL_FILES},
    }

    # Verification is the final publication marker; remove any prior marker
    # before refreshing an otherwise valid target.
    paths["verification.json"].unlink(missing_ok=True)
    _write_json(paths["config.json"], _config_payload(result))
    _write_csv(paths["seed_manifest.csv"], _seed_rows(result))
    _write_csv(paths["calibration_results.csv"], _calibration_rows(result))
    _write_csv(paths["validation_results.csv"], _validation_rows(result))
    _write_csv(paths["bank_stability_summary.csv"], _bank_rows(result))
    _write_csv(paths["predictive_summary.csv"], _predictive_rows(result))
    _write_csv(paths["representative_profile.csv"], _representative_rows(result))
    _write_json(paths["summary.json"], _summary_payload(result))
    paths["review.md"].write_text(_render_review(result), encoding="utf-8")
    paths["recovery_calibration.svg"].write_text(
        _recovery_calibration_svg(result),
        encoding="utf-8",
    )
    paths["predictive_comparison.svg"].write_text(
        _predictive_comparison_svg(result),
        encoding="utf-8",
    )

    expected = {
        *ROOT_FILES,
        *(f"visuals/{name}" for name in VISUAL_FILES),
    }
    expected_without_verification = expected - {"verification.json"}
    observed_without_verification = {
        path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()
    }
    if observed_without_verification != expected_without_verification:
        raise RuntimeError(
            "artifact contract mismatch before verification: "
            f"expected {sorted(expected_without_verification)}, "
            f"got {sorted(observed_without_verification)}"
        )
    _write_json(
        paths["verification.json"],
        _verification_payload(
            result,
            observed_artifact_file_count=len(observed_without_verification) + 1,
        ),
    )
    observed = {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()}
    if observed != expected:
        paths["verification.json"].unlink(missing_ok=True)
        raise RuntimeError(
            f"artifact contract mismatch: expected {sorted(expected)}, got {sorted(observed)}"
        )
    return tuple(paths[name] for name in (*ROOT_FILES, *VISUAL_FILES))


def _config_payload(result: Goal004Result) -> dict[str, object]:
    config = result.config
    return {
        "goal": "004-stochastic-one-rate-recovery-calibration",
        "method": "site-history simulated composite likelihood",
        "is_full_joint_spatial_likelihood": False,
        "between_site_process_dependence": "omitted",
        "source_identity": SOURCE_IDENTITY,
        "master_seed": config.master_seed,
        "bit_generator": "PCG64",
        "phase_root_order": ["integration_bank", "calibration", "validation"],
        "integration_bank_size": config.bank_size,
        "half_bank_size": config.half_bank_size,
        "calibration_replicates": config.calibration_replicates,
        "validation_replicates": config.validation_replicates,
        "calibration_rank_one_based": config.calibration_rank_one_based,
        "survey_times": list((10, 20, 30, 40, 50, 60)),
        "visits_per_site_time": 2,
        "records_per_dataset": 1920,
        "detection_probability": 0.65,
        "false_positive_probability": 0.0,
        "truth_rate": 1.0,
        "truth_grid_index": config.truth_index,
        "rate_domain": [config.rates[0], config.rates[-1]],
        "rate_grid_size": len(config.rates),
        "rate_grid": list(config.rates),
        "rate_grid_formula": "2 ** (-2 + 4 * j / 600), j = 0,...,600",
        "category_count": 7,
        "smoothing": "(category count + 0.5) / (bank size + 7 * 0.5)",
        "calibration_scope": "rho = 1 under the frozen design only",
        "production_configuration": config.is_production,
    }


def _seed_rows(result: Goal004Result) -> list[CsvRow]:
    return [
        {
            "phase": record.phase,
            "index": record.index,
            "stream_role": record.stream_role,
            "entropy": record.entropy,
            "spawn_key": _tuple_json(record.spawn_key),
            "pool_size": record.pool_size,
            "state_words": _tuple_json(record.state_words),
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for record in result.seed_manifest.stream_records
    ]


def _calibration_rows(result: Goal004Result) -> list[CsvRow]:
    return [
        {
            "phase": "calibration",
            "dataset_index": row.dataset_index,
            "bank_variant": row.bank_variant,
            "record_count": row.record_count,
            "no_false_positives": row.no_false_positives,
            "truth_grid_index": row.truth_grid_index,
            "lr_at_truth": row.lr_at_truth,
            "truth_log_likelihood": row.truth_log_likelihood,
            "maximum_log_likelihood": row.maximum_log_likelihood,
            "mle_indices": _tuple_json(row.mle_indices),
            "mle_rates": _tuple_json(row.mle_rates),
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for row in result.calibration_results
    ]


def _validation_rows(result: Goal004Result) -> list[CsvRow]:
    return [
        {
            "phase": "validation",
            "dataset_index": row.dataset_index,
            "bank_variant": row.bank_variant,
            "record_count": row.record_count,
            "training_record_count": row.training_record_count,
            "holdout_record_count": row.holdout_record_count,
            "split_isolated": row.split_isolated,
            "no_false_positives": row.no_false_positives,
            "truth_grid_index": row.truth_grid_index,
            "lr_at_truth": row.lr_at_truth,
            "truth_log_likelihood": row.truth_log_likelihood,
            "maximum_log_likelihood": row.maximum_log_likelihood,
            "truth_included": row.truth_included,
            "support_component_count": row.support_component_count,
            "support_boundary_contact": row.support_boundary_contact,
            "support_arithmetic_width": row.support_arithmetic_width,
            "support_log_rate_width": row.support_log_rate_width,
            "support_indices": _tuple_json(row.support_indices),
            "mle_indices": _tuple_json(row.mle_indices),
            "mle_rates": _tuple_json(row.mle_rates),
            "truth_to_mle_set_distance": row.truth_to_mle_set_distance,
            "absolute_log_rate_error": row.absolute_log_rate_error,
            "training_mle_indices": _tuple_json(row.training_mle_indices),
            "training_mle_rates": _tuple_json(row.training_mle_rates),
            "stochastic_log_score_minimum": row.stochastic_log_score_minimum,
            "stochastic_log_score_maximum": row.stochastic_log_score_maximum,
            "stochastic_brier_minimum": row.stochastic_brier_minimum,
            "stochastic_brier_maximum": row.stochastic_brier_maximum,
            "stochastic_probability_minimum": row.stochastic_probability_minimum,
            "stochastic_probability_maximum": row.stochastic_probability_maximum,
            "neutral_log_score": row.neutral_log_score,
            "neutral_brier_score": row.neutral_brier_score,
            "neutral_probability_minimum": row.neutral_probability_minimum,
            "neutral_probability_maximum": row.neutral_probability_maximum,
            "paired_brier_difference": row.paired_brier_difference,
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for row in result.validation_results
    ]


def _bank_rows(result: Goal004Result) -> list[CsvRow]:
    return [
        {
            "bank_variant": row.bank_variant,
            "draw_count": row.draw_count,
            "calibration_cutoff": row.cutoff.cutoff,
            "calibration_rank_one_based": row.cutoff.rank_one_based,
            "calibration_sample_size": row.cutoff.sample_size,
            "coverage_success_count": row.coverage_success_count,
            "coverage_estimate": row.calibrated_coverage.estimate,
            "coverage_wilson_lower": row.calibrated_coverage.lower,
            "coverage_wilson_upper": row.calibrated_coverage.upper,
            "topology_success_count": row.topology_success_count,
            "topology_success_proportion": row.topology_success_proportion,
            "boundary_contact_count": row.boundary_contact_count,
            "mean_support_arithmetic_width": row.mean_support_arithmetic_width,
            "mean_support_log_rate_width": row.mean_support_log_rate_width,
            "mean_mle_set_size": row.mean_mle_set_size,
            "mean_truth_to_mle_set_distance": row.mean_truth_to_mle_set_distance,
            "mean_absolute_log_rate_error": row.mean_absolute_log_rate_error,
            "paired_brier_estimate": row.paired_brier_interval.estimate,
            "paired_brier_lower": row.paired_brier_interval.lower,
            "paired_brier_upper": row.paired_brier_interval.upper,
            "downstream_class": row.downstream_class,
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for row in result.bank_summaries
    ]


def _predictive_rows(result: Goal004Result) -> list[CsvRow]:
    return [
        {
            "bank_variant": row.bank_variant,
            "validation_replicates": result.config.validation_replicates,
            "stochastic_score_rule": "maximum Brier across the training MLE set",
            "mean_stochastic_brier_worst_mle": row.mean_stochastic_brier_worst_mle,
            "mean_neutral_brier": row.mean_neutral_brier,
            "paired_brier_estimate": row.paired_brier_interval.estimate,
            "paired_brier_normal_lower": row.paired_brier_interval.lower,
            "paired_brier_normal_upper": row.paired_brier_interval.upper,
            "finite_stochastic_log_score_count": row.finite_stochastic_log_score_count,
            "finite_neutral_log_score_count": row.finite_neutral_log_score_count,
            "neutral_fit_scope": "training records only",
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for row in result.bank_summaries
    ]


def _representative_rows(result: Goal004Result) -> list[CsvRow]:
    rows: list[CsvRow] = []
    for representative in result.representative_profiles:
        profile = representative.profile
        support = set(representative.summary.support_indices)
        mle = set(profile.mle_indices)
        for index, rate in enumerate(profile.rates):
            rows.append(
                {
                    "dataset_index": representative.dataset_index,
                    "bank_variant": representative.bank_variant,
                    "rate_index": index,
                    "rho": float(rate),
                    "log_composite_likelihood": float(profile.log_likelihoods[index]),
                    "relative_lr": float(
                        2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods[index])
                    ),
                    "calibrated_cutoff": representative.cutoff,
                    "in_calibrated_support": index in support,
                    "in_mle_set": index in mle,
                    "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
                }
            )
    return rows


def _summary_payload(result: Goal004Result) -> dict[str, object]:
    full = _bank_summary(result, "full")
    return {
        "outcome": result.outcome,
        "method": "site-history simulated composite likelihood",
        "between_site_process_dependence": "omitted",
        "calibration_scope": "rho = 1 under the frozen design only",
        "truth_rate": 1.0,
        "full_bank": _bank_payload(full),
        "bank_variants": [_bank_payload(row) for row in result.bank_summaries],
        "bank_classes_agree": len({row.downstream_class for row in result.bank_summaries}) == 1,
        "interpretation": _outcome_interpretation(result.outcome),
    }


def _verification_payload(
    result: Goal004Result,
    *,
    observed_artifact_file_count: int,
) -> dict[str, object]:
    return {
        "expected_artifact_file_count": EXPECTED_FILE_COUNT,
        "observed_artifact_file_count": observed_artifact_file_count,
        "invariants": result.invariants,
        "all_invariants_pass": all(result.invariants.values()),
        "full_and_half_bank_classes": {
            row.bank_variant: row.downstream_class for row in result.bank_summaries
        },
        "method_label": "site-history simulated composite likelihood",
        "full_joint_spatial_likelihood_claimed": False,
        "calibration_valid_away_from_rho_1": False,
        "representative_profile_dataset_index": 0,
        "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
    }


def _render_review(result: Goal004Result) -> str:
    full = _bank_summary(result, "full")
    table_header = (
        "| bank | draws | cutoff | coverage | interior topology | log-rate error | "
        "paired Brier 95% interval | class |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |"
    )
    table_rows = "\n".join(
        "| "
        + " | ".join(
            (
                row.bank_variant,
                str(row.draw_count),
                _number(row.cutoff.cutoff),
                _percent(row.calibrated_coverage.estimate),
                f"{row.topology_success_count}/{result.config.validation_replicates}",
                _number(row.mean_absolute_log_rate_error),
                (
                    f"{_number(row.paired_brier_interval.estimate)} "
                    f"[{_number(row.paired_brier_interval.lower)}, "
                    f"{_number(row.paired_brier_interval.upper)}]"
                ),
                row.downstream_class,
            )
        )
        + " |"
        for row in result.bank_summaries
    )
    return f"""# Goal 004 Stochastic One-Rate Recovery And Calibration Review

**Outcome:** `{result.outcome}`

## Observations

Each of the {result.config.calibration_replicates} calibration and
{result.config.validation_replicates} validation datasets contains one complete
stochastic edge field at `rho = 1` and 1,920 jointly generated detection records.
The frozen survey calendar is `10, 20, 30, 40, 50, 60`, detection is known at
0.65, and generating false positives are zero. Training and holdout clusters
remain disjoint.

## Inference

The fitted object is a **site-history simulated composite likelihood**. Complete
12-record histories are marginalized over seven Jeffreys-smoothed onset
categories before site contributions are multiplied.
It is not a full joint spatial likelihood.

{table_header}
{table_rows}

For the full bank, the calibrated cutoff is {_number(full.cutoff.cutoff)},
coverage is {_percent(full.calibrated_coverage.estimate)} with Wilson interval
[{_percent(full.calibrated_coverage.lower)},
{_percent(full.calibrated_coverage.upper)}], and
{full.topology_success_count}/{result.config.validation_replicates} supports
form one component strictly inside the rate domain. Mean set-valued absolute
natural-log-rate error is {_number(full.mean_absolute_log_rate_error)} and mean
support log-rate width is {_number(full.mean_support_log_rate_width)}.

Held-out stochastic predictions score every training MLE rate and use the worst
MLE Brier score. The neutral is fit on training records only. The full-bank
paired Brier interval is [{_number(full.paired_brier_interval.lower)},
{_number(full.paired_brier_interval.upper)}].

## Assumptions

The landscape, 81 sources, conductance, exponential edge law, 160 sites,
cluster split, calendar, known detection, zero false positives, rate domain,
601-point production grid, and finite integration scheme are treated as fixed.
The accepted faster Goal 003 time scale is unchanged and unnormalized.

## Uncertainty

The likelihood-ratio cutoff is the prespecified calibration order statistic.
The Wilson interval describes repeated validation coverage, while the normal
Monte Carlo interval describes the mean paired Brier difference. Calibration
is established only at `rho = 1` for this frozen design and integration scheme;
it is not Wilks support and does not establish coverage at other rates. Support
width and MLE precision are reported without an invented pass threshold.

## Limitations

The site-history construction preserves dependence across visits and surveys
within each site but omits between-site process dependence from the shared
stochastic edge field. Its calibrated support is conditional on one synthetic
landscape and observation design. A negative scientific class is a completed
result and has not triggered retuning, seed replacement, normalization, or
bank enlargement.
"""


def _recovery_calibration_svg(result: Goal004Result) -> str:
    colors = {
        "full": "#24557a",
        "first_half": "#b04a3a",
        "second_half": "#2f7d58",
    }
    with plt.rc_context(_svg_rc()):
        figure, axes = plt.subplots(1, 2, figsize=(10.8, 4.8), layout="constrained")
        for representative in result.representative_profiles:
            profile = representative.profile
            relative = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
            axes[0].plot(
                profile.rates,
                relative,
                color=colors[representative.bank_variant],
                label=representative.bank_variant.replace("_", " "),
            )
            axes[0].axhline(
                representative.cutoff,
                color=colors[representative.bank_variant],
                linestyle=":",
                linewidth=1.0,
            )
        axes[0].axvline(1.0, color="#222222", linestyle="--", linewidth=1.0)
        axes[0].set_xscale("log", base=2)
        axes[0].set_xlabel("spread-rate multiplier rho")
        axes[0].set_ylabel("2 x (CLmax - CL)")
        axes[0].set_title("Validation replicate 0 profiles; rho = 1")
        axes[0].legend()

        names = [row.bank_variant.replace("_", " ") for row in result.bank_summaries]
        coverage = [row.calibrated_coverage.estimate for row in result.bank_summaries]
        lower = [
            row.calibrated_coverage.estimate - row.calibrated_coverage.lower
            for row in result.bank_summaries
        ]
        upper = [
            row.calibrated_coverage.upper - row.calibrated_coverage.estimate
            for row in result.bank_summaries
        ]
        axes[1].bar(
            names,
            coverage,
            color=[colors[name] for name in BANK_VARIANT_NAMES],
            alpha=0.82,
        )
        axes[1].errorbar(
            names,
            coverage,
            yerr=[lower, upper],
            fmt="none",
            ecolor="#222222",
            capsize=4,
        )
        axes[1].axhline(0.95, color="#222222", linestyle="--", linewidth=1.0)
        axes[1].set_ylim(0.0, 1.02)
        axes[1].set_ylabel("truth coverage with 95% Wilson interval")
        axes[1].set_title("Calibration applies at rho = 1 only")
        figure.suptitle(
            "Recovery and calibrated support\n"
            "site-history simulated composite likelihood\n"
            "between-site process dependence omitted"
        )
        return _figure_svg(figure)


def _predictive_comparison_svg(result: Goal004Result) -> str:
    colors = {
        "full": "#24557a",
        "first_half": "#b04a3a",
        "second_half": "#2f7d58",
    }
    with plt.rc_context(_svg_rc()):
        figure, axes = plt.subplots(1, 2, figsize=(10.8, 4.8), layout="constrained")
        for name in BANK_VARIANT_NAMES:
            rows = [row for row in result.validation_results if row.bank_variant == name]
            axes[0].scatter(
                [row.dataset_index for row in rows],
                [row.paired_brier_difference for row in rows],
                s=18,
                alpha=0.65,
                color=colors[name],
                label=name.replace("_", " "),
            )
        axes[0].axhline(0.0, color="#222222", linestyle="--", linewidth=1.0)
        axes[0].set_xlabel("validation replicate index")
        axes[0].set_ylabel("worst stochastic-MLE Brier - neutral Brier")
        axes[0].set_title("Paired Brier differences")
        axes[0].legend()

        for name in BANK_VARIANT_NAMES:
            rows = [row for row in result.validation_results if row.bank_variant == name]
            axes[1].scatter(
                [row.neutral_brier_score for row in rows],
                [row.stochastic_brier_maximum for row in rows],
                s=18,
                alpha=0.65,
                color=colors[name],
                label=name.replace("_", " "),
            )
        all_scores = [
            score
            for row in result.validation_results
            for score in (row.neutral_brier_score, row.stochastic_brier_maximum)
        ]
        bounds = (min(all_scores), max(all_scores))
        axes[1].plot(bounds, bounds, color="#222222", linestyle="--", linewidth=1.0)
        axes[1].set_xlabel("neutral mean Brier")
        axes[1].set_ylabel("worst stochastic-MLE mean Brier")
        axes[1].set_title("training-only fits")
        figure.suptitle("Held-out predictive comparison\nbetween-site process dependence omitted")
        return _figure_svg(figure)


def _bank_summary(result: Goal004Result, name: str) -> BankSummary:
    return next(row for row in result.bank_summaries if row.bank_variant == name)


def _bank_payload(row: BankSummary) -> dict[str, object]:
    return {
        "bank_variant": row.bank_variant,
        "draw_count": row.draw_count,
        "calibration_cutoff": row.cutoff.cutoff,
        "coverage": _interval_payload(row.calibrated_coverage),
        "topology_success_count": row.topology_success_count,
        "topology_success_proportion": row.topology_success_proportion,
        "boundary_contact_count": row.boundary_contact_count,
        "mean_support_arithmetic_width": row.mean_support_arithmetic_width,
        "mean_support_log_rate_width": row.mean_support_log_rate_width,
        "mean_mle_set_size": row.mean_mle_set_size,
        "mean_truth_to_mle_set_distance": row.mean_truth_to_mle_set_distance,
        "mean_absolute_log_rate_error": row.mean_absolute_log_rate_error,
        "paired_brier": _interval_payload(row.paired_brier_interval),
        "downstream_class": row.downstream_class,
    }


def _interval_payload(interval: Any) -> dict[str, float]:
    return {
        "estimate": float(interval.estimate),
        "lower": float(interval.lower),
        "upper": float(interval.upper),
    }


def _outcome_interpretation(outcome: str) -> str:
    return {
        "likelihood_approximation_unstable": (
            "Full- and half-bank downstream scientific classes differ."
        ),
        "design_limited": "Too few full-bank supports are one strictly interior component.",
        "calibration_not_ready": "The full-bank Wilson interval excludes 0.95.",
        "rate_recoverable_neutral_better": (
            "Recovery gates pass, but the neutral has lower held-out Brier score."
        ),
        "rate_recoverable_mechanism_inconclusive": (
            "Recovery gates pass and the paired Brier interval contains zero."
        ),
        "advance_one_rate_stochastic_spread": (
            "Recovery gates pass and stochastic predictions improve held-out Brier score."
        ),
    }[outcome]


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


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
        return format(value, ".17g")
    return value


def _tuple_json(values: tuple[int | float, ...]) -> str:
    return json.dumps(values, separators=(",", ":"), allow_nan=False)


def _number(value: float) -> str:
    return format(value, ".6g")


def _percent(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def _svg_rc() -> Any:
    return {
        "svg.hashsalt": "latent-landscapes-goal004",
        "svg.fonttype": "none",
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.labelsize": 9,
    }


def _figure_svg(figure: Figure) -> str:
    buffer = io.StringIO()
    figure.savefig(
        buffer,
        format="svg",
        metadata={"Date": None, "Creator": "Latent Landscapes Goal 004"},
    )
    plt.close(figure)
    return buffer.getvalue()
