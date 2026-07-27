"""Deterministic review-pack writer for Goal 007."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from math import isfinite
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from .benchmark import SOURCE_IDENTITY, Goal007Result

DEFAULT_OUTPUT_DIR = Path("artifacts/goal007_joint_rho_eta_perfect_detection")
ROOT_FILES = (
    "config.json",
    "seed_manifest.csv",
    "observation_signal_summary.csv",
    "calibration_results.csv",
    "validation_results.csv",
    "bank_summary.csv",
    "predictive_summary.csv",
    "representative_profile.csv",
    "summary.json",
    "verification.json",
    "review.md",
)
VISUAL_FILES = (
    "joint_profile_surface.svg",
    "recovery_calibration.svg",
    "bank_predictive_comparison.svg",
)
EXPECTED_FILE_COUNT = 14
METHOD = "site-history simulated composite likelihood"
BETWEEN_SITE_LIMITATION = "omitted"

type CsvValue = str | int | float | bool | None
type CsvRow = Mapping[str, CsvValue]


def write_review_bundle(
    result: Goal007Result,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, ...]:
    """Write and reconcile the exact ignored 14-file Goal 007 review pack."""
    if result.outcome == "implementation_blocked":
        raise ValueError("an implementation-blocked result has no review bundle")
    target = Path(output_dir)
    expected = {*ROOT_FILES, *(f"visuals/{name}" for name in VISUAL_FILES)}
    if target.exists():
        stale = {
            path.relative_to(target).as_posix()
            for path in target.rglob("*")
            if path.is_file() and path.relative_to(target).as_posix() not in expected
        }
        if stale:
            raise RuntimeError(f"stale artifact files are not permitted: {sorted(stale)}")
    target.mkdir(parents=True, exist_ok=True)
    visuals = target / "visuals"
    visuals.mkdir(exist_ok=True)
    paths = {name: target / name for name in ROOT_FILES}
    visual_paths = {name: visuals / name for name in VISUAL_FILES}
    paths["verification.json"].unlink(missing_ok=True)

    _write_json(paths["config.json"], _config_payload(result))
    _write_csv(paths["seed_manifest.csv"], _seed_rows(result))
    _write_csv(paths["observation_signal_summary.csv"], _observation_rows(result))
    _write_csv(paths["calibration_results.csv"], _calibration_rows(result))
    _write_csv(paths["validation_results.csv"], _validation_rows(result))
    _write_csv(paths["bank_summary.csv"], _bank_rows(result))
    _write_csv(paths["predictive_summary.csv"], _predictive_rows(result))
    _write_csv(paths["representative_profile.csv"], _representative_rows(result))
    _write_json(paths["summary.json"], _summary_payload(result))
    paths["review.md"].write_text(_render_review(result), encoding="utf-8")
    _write_svg(
        visual_paths["joint_profile_surface.svg"],
        _joint_profile_surface_figure(result),
    )
    _write_svg(
        visual_paths["recovery_calibration.svg"],
        _recovery_calibration_figure(result),
    )
    _write_svg(
        visual_paths["bank_predictive_comparison.svg"],
        _bank_predictive_figure(result),
    )

    observed_without_verification = {
        path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()
    }
    if observed_without_verification != expected - {"verification.json"}:
        raise RuntimeError(
            "artifact contract mismatch before verification: "
            f"{sorted(observed_without_verification)}"
        )
    hashes = {
        relative: hashlib.sha256((target / relative).read_bytes()).hexdigest()
        for relative in sorted(observed_without_verification)
    }
    _write_json(
        paths["verification.json"],
        {
            "all_invariants_pass": all(result.invariants.values()),
            "expected_artifact_file_count": EXPECTED_FILE_COUNT,
            "observed_artifact_file_count": EXPECTED_FILE_COUNT,
            "invariants": result.invariants,
            "outcome": result.outcome,
            "source_identity": SOURCE_IDENTITY,
            "file_sha256_excluding_verification": hashes,
            "perfect_detection_positive_control": True,
            "duplicate_visits_collapsed": True,
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
            "conditional_scope": "one landscape and one central truth",
        },
    )
    observed = {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()}
    if observed != expected:
        raise RuntimeError(f"artifact contract mismatch: {sorted(observed)}")
    _validate_serialized_bundle(target, observed)
    return tuple(paths[name] for name in ROOT_FILES) + tuple(
        visual_paths[name] for name in VISUAL_FILES
    )


def _config_payload(result: Goal007Result) -> dict[str, object]:
    config = result.config
    return {
        "goal": "007-joint-rho-eta-perfect-detection-positive-control",
        "method": METHOD,
        "is_full_joint_spatial_likelihood": False,
        "perfect_detection_positive_control": True,
        "false_positive_probability": 0.0,
        "detection_random_stream": False,
        "duplicate_same_time_visits": 2,
        "duplicate_visits_collapsed_for_inference": True,
        "analyst_records_per_dataset": 1920,
        "distinct_site_time_outcomes_per_dataset": 960,
        "training_outcomes_per_dataset": 720,
        "holdout_outcomes_per_dataset": 240,
        "survey_times": [10, 20, 30, 40, 50, 60],
        "master_seed": config.master_seed,
        "bit_generator": "PCG64",
        "phase_root_order": ["integration_bank", "calibration", "validation"],
        "bank_size": config.bank_size,
        "half_bank_size": config.half_bank_size,
        "calibration_replicates": config.calibration_replicates,
        "validation_replicates": config.validation_replicates,
        "calibration_rank_one_based": config.calibration_rank_one_based,
        "rhos": list(config.rhos),
        "etas": list(config.etas),
        "truth": {"rho": 1.0, "eta": 1.0},
        "truth_indices": {
            "rho_index": config.truth_rho_index,
            "eta_index": config.truth_eta_index,
        },
        "grid_cell_count": len(config.rhos) * len(config.etas),
        "eta_resolution": 0.25 if config.is_production else None,
        "jeffreys_half_count": 0.5,
        "category_count": 7,
        "support_adjacency": "four-neighbour rook",
        "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        "source_identity": SOURCE_IDENTITY,
        "production_configuration": config.is_production,
        "conditional_scope": "one landscape and one central truth",
    }


def _seed_rows(result: Goal007Result) -> list[CsvRow]:
    return [
        {
            "phase": record.phase,
            "index": record.index,
            "stream_role": record.stream_role,
            "entropy": record.entropy,
            "spawn_key": _compact_json(record.spawn_key),
            "state_words": _compact_json(record.state_words),
            "pool_size": record.pool_size,
            "bit_generator": "PCG64",
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for record in result.seed_manifest.stream_records
    ]


def _observation_rows(result: Goal007Result) -> list[CsvRow]:
    return [
        {
            "survey_time": row.survey_time,
            "occupied_fraction_mean": row.occupied_fraction_mean,
            "occupied_fraction_lower": row.occupied_fraction_lower,
            "occupied_fraction_upper": row.occupied_fraction_upper,
            "detected_fraction_mean": row.detected_fraction_mean,
            "detected_fraction_lower": row.detected_fraction_lower,
            "detected_fraction_upper": row.detected_fraction_upper,
            "perfect_detection": True,
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for row in result.observation_signal_summary
    ]


def _calibration_rows(result: Goal007Result) -> list[CsvRow]:
    return [
        {
            "dataset_index": row.dataset_index,
            "bank_variant": row.bank_variant,
            "analyst_record_count": row.analyst_record_count,
            "distinct_outcome_count": row.distinct_outcome_count,
            "duplicate_visits_agree": row.duplicate_visits_agree,
            "truth_eta_index": row.truth_eta_index,
            "truth_rho_index": row.truth_rho_index,
            "lr_at_truth": row.lr_at_truth,
            "truth_log_likelihood": row.truth_log_likelihood,
            "maximum_log_likelihood": row.maximum_log_likelihood,
            "mle_indices": _compact_json(row.mle_indices),
            "mle_cells_rho_eta": _compact_json(row.mle_cells),
            "mle_set_size": len(row.mle_indices),
            "profile_scope": "full_data_160_sites",
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for row in result.calibration_results
    ]


def _validation_rows(result: Goal007Result) -> list[CsvRow]:
    return [
        {
            "dataset_index": row.dataset_index,
            "bank_variant": row.bank_variant,
            "analyst_record_count": row.analyst_record_count,
            "distinct_outcome_count": row.distinct_outcome_count,
            "training_outcome_count": row.training_outcome_count,
            "holdout_outcome_count": row.holdout_outcome_count,
            "split_isolated": row.split_isolated,
            "perfect_truth_mapping": row.perfect_truth_mapping,
            "truth_eta_index": row.truth_eta_index,
            "truth_rho_index": row.truth_rho_index,
            "lr_at_truth": row.lr_at_truth,
            "truth_log_likelihood": row.truth_log_likelihood,
            "maximum_log_likelihood": row.maximum_log_likelihood,
            "truth_included": row.truth_included,
            "support_cell_count": row.support_cell_count,
            "support_component_count": row.support_component_count,
            "support_boundary_contact": row.support_boundary_contact,
            "projected_log_rho_width": row.projected_log_rho_width,
            "projected_eta_width": row.projected_eta_width,
            "support_indices": _compact_json(row.support_indices),
            "support_correlation": row.support_correlation,
            "support_correlation_reason": row.support_correlation_reason,
            "mle_indices": _compact_json(row.mle_indices),
            "mle_cells_rho_eta": _compact_json(row.mle_cells),
            "mle_set_size": len(row.mle_indices),
            "minimum_absolute_log_rho_error": row.minimum_absolute_log_rho_error,
            "minimum_absolute_eta_error": row.minimum_absolute_eta_error,
            "training_mle_indices": _compact_json(row.training_mle_indices),
            "training_mle_cells_rho_eta": _compact_json(row.training_mle_cells),
            "training_mle_set_size": len(row.training_mle_indices),
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
            "support_profile_scope": "full_data_160_sites",
            "prediction_fit_scope": "training_only_120_sites",
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for row in result.validation_results
    ]


def _bank_rows(result: Goal007Result) -> list[CsvRow]:
    return [
        {
            "bank_variant": row.bank_variant,
            "draw_count": row.draw_count,
            "calibrated_cutoff": row.cutoff.cutoff,
            "cutoff_rank_one_based": row.cutoff.rank_one_based,
            "cutoff_sample_size": row.cutoff.sample_size,
            "coverage_success_count": row.coverage_success_count,
            "coverage_estimate": row.calibrated_coverage.estimate,
            "coverage_lower": row.calibrated_coverage.lower,
            "coverage_upper": row.calibrated_coverage.upper,
            "topology_success_count": row.topology_success_count,
            "topology_success_proportion": row.topology_success_proportion,
            "boundary_contact_count": row.boundary_contact_count,
            "median_minimum_absolute_log_rho_error": (row.median_minimum_absolute_log_rho_error),
            "median_minimum_absolute_eta_error": row.median_minimum_absolute_eta_error,
            "median_projected_log_rho_width": row.median_projected_log_rho_width,
            "median_projected_eta_width": row.median_projected_eta_width,
            "median_support_cell_count": row.median_support_cell_count,
            "mean_mle_set_size": row.mean_mle_set_size,
            "paired_brier_estimate": row.paired_brier_interval.estimate,
            "paired_brier_lower": row.paired_brier_interval.lower,
            "paired_brier_upper": row.paired_brier_interval.upper,
            "downstream_class": row.downstream_class,
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for row in result.bank_summaries
    ]


def _predictive_rows(result: Goal007Result) -> list[CsvRow]:
    return [
        {
            "bank_variant": row.bank_variant,
            "validation_dataset_count": result.config.validation_replicates,
            "worst_tied_process_mle_rule": True,
            "mean_stochastic_brier_worst_mle": row.mean_stochastic_brier_worst_mle,
            "mean_neutral_brier": row.mean_neutral_brier,
            "paired_brier_estimate": row.paired_brier_interval.estimate,
            "paired_brier_lower": row.paired_brier_interval.lower,
            "paired_brier_upper": row.paired_brier_interval.upper,
            "finite_log_score_count": row.finite_log_score_count,
            "training_outcome_count_per_dataset": 720,
            "holdout_outcome_count_per_dataset": 240,
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for row in result.bank_summaries
    ]


def _representative_rows(result: Goal007Result) -> list[CsvRow]:
    rows: list[CsvRow] = []
    for representative in result.representative_profiles:
        profile = representative.profile
        support = set(representative.summary.support_indices)
        mles = set(profile.mle_indices)
        for eta_index, eta in enumerate(profile.etas):
            for rho_index, rho in enumerate(profile.rhos):
                log_likelihood = float(profile.log_likelihoods[eta_index, rho_index])
                rows.append(
                    {
                        "dataset_index": representative.dataset_index,
                        "bank_variant": representative.bank_variant,
                        "eta_index": eta_index,
                        "rho_index": rho_index,
                        "eta": float(eta),
                        "rho": float(rho),
                        "log_likelihood": log_likelihood,
                        "likelihood_ratio": max(
                            0.0,
                            2.0 * (profile.maximum_log_likelihood - log_likelihood),
                        ),
                        "in_calibrated_support": (eta_index, rho_index) in support,
                        "is_tied_mle": (eta_index, rho_index) in mles,
                        "is_truth_cell": (
                            eta_index == result.config.truth_eta_index
                            and rho_index == result.config.truth_rho_index
                        ),
                        "calibrated_cutoff": representative.cutoff,
                        "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
                    }
                )
    return rows


def _summary_payload(result: Goal007Result) -> dict[str, object]:
    return {
        "goal": "007-joint-rho-eta-perfect-detection-positive-control",
        "outcome": result.outcome,
        "conditional_scope": "one landscape and one central truth",
        "perfect_detection_positive_control": True,
        "method": METHOD,
        "is_full_joint_spatial_likelihood": False,
        "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        "eta_resolution": 0.25 if result.config.is_production else None,
        "bank_summaries": {
            row.bank_variant: {
                "draw_count": row.draw_count,
                "cutoff": row.cutoff.cutoff,
                "coverage": _interval_payload(row.calibrated_coverage),
                "topology_success_count": row.topology_success_count,
                "median_minimum_absolute_log_rho_error": (
                    row.median_minimum_absolute_log_rho_error
                ),
                "median_minimum_absolute_eta_error": row.median_minimum_absolute_eta_error,
                "median_projected_log_rho_width": row.median_projected_log_rho_width,
                "median_projected_eta_width": row.median_projected_eta_width,
                "paired_brier": _interval_payload(row.paired_brier_interval),
                "downstream_class": row.downstream_class,
            }
            for row in result.bank_summaries
        },
        "bank_classes_stable": len({row.downstream_class for row in result.bank_summaries}) == 1,
        "invariants_pass": all(result.invariants.values()),
    }


def _render_review(result: Goal007Result) -> str:
    bank_lines = "\n".join(
        f"- `{row.bank_variant}`: cutoff {row.cutoff.cutoff:.6g}, "
        f"coverage {row.coverage_success_count}/{result.config.validation_replicates}, "
        f"topology {row.topology_success_count}/{result.config.validation_replicates}, "
        f"class `{row.downstream_class}`."
        for row in result.bank_summaries
    )
    return f"""# Goal 007 Joint Rho-Eta Perfect-Detection Positive-Control Review

## Outcome

`{result.outcome}`

This benchmark is a deliberately favourable perfect detection positive control.
Its result is conditional on one landscape and one central truth,
`(rho, eta) = (1, 1)`.

## Generated Observations

Each generated dataset contains 1,920 analyst-facing records. The two nominal
same-time visits agree exactly under perfect detection and are collapsed to 960
distinct site-time outcomes before fitting or scoring. There is no detection
random-number stream and no false-positive process.

## Scientific Inference

Inference uses a {METHOD} on the frozen eta-by-rho grid. Calibration statistics
and calibrated support use the full 160-site profile. Training profiles are
used only to choose tied process MLE cells for prediction on the 40 held-out
sites. Every tied training MLE is scored and the worst process Brier score
enters the paired comparison.

{bank_lines}

## Uncertainty And Bank Stability

The 95% cutoff is the prespecified empirical order statistic, calculated
separately for the full bank and each disjoint half. Validation truth inclusion
uses a Wilson interval; the paired Brier contrast uses a normal Monte Carlo
interval. Two-dimensional support uses four-neighbour rook adjacency. Eta
precision is limited by the frozen 0.25 grid in production.

## Limitations

This composite construction omits between-site dependence induced by the
shared edge field and is not a full joint spatial likelihood. Support-cell
rho-eta correlation is only a descriptive ridge diagnostic. The benchmark does
not establish cross-truth recovery, robustness to imperfect detection, or
operational uncertainty calibration when the truth is unknown. A negative
scientific class is a completed result and does not authorize retuning.
"""


def _joint_profile_surface_figure(result: Goal007Result) -> Figure:
    representative = next(
        row for row in result.representative_profiles if row.bank_variant == "full"
    )
    profile = representative.profile
    lr = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
    with _svg_style():
        figure, axis = plt.subplots(figsize=(8.0, 5.0))
        image = axis.imshow(
            lr,
            origin="lower",
            aspect="auto",
            interpolation="nearest",
            extent=(
                float(np.log(profile.rhos[0])),
                float(np.log(profile.rhos[-1])),
                float(profile.etas[0]),
                float(profile.etas[-1]),
            ),
            cmap="viridis_r",
        )
        axis.scatter(
            [
                float(np.log(profile.rhos[rho_index]))
                for _, rho_index in representative.summary.support_indices
            ],
            [
                float(profile.etas[eta_index])
                for eta_index, _ in representative.summary.support_indices
            ],
            s=12,
            facecolors="none",
            edgecolors="#d1495b",
            linewidths=0.6,
            label="calibrated support",
        )
        axis.scatter(
            [0.0],
            [1.0],
            marker="*",
            s=90,
            color="white",
            edgecolor="black",
            label="truth",
        )
        axis.set(
            xlabel="Natural log rho",
            ylabel="Eta",
            title="Joint profile surface: validation dataset 0, full bank",
        )
        figure.colorbar(image, ax=axis, label="Likelihood-ratio statistic")
        axis.legend(loc="upper right")
        figure.text(
            0.5,
            0.01,
            "site-history simulated composite likelihood; perfect-detection positive control",
            ha="center",
        )
        figure.tight_layout(rect=(0, 0.04, 1, 1))
    return figure


def _recovery_calibration_figure(result: Goal007Result) -> Figure:
    rows = result.bank_summaries
    labels = [row.bank_variant.replace("_", " ") for row in rows]
    x = np.arange(len(rows))
    with _svg_style():
        figure, axes = plt.subplots(1, 2, figsize=(10.0, 4.8))
        coverage = [row.calibrated_coverage.estimate for row in rows]
        lower = [
            value - row.calibrated_coverage.lower for value, row in zip(coverage, rows, strict=True)
        ]
        upper = [
            row.calibrated_coverage.upper - value for value, row in zip(coverage, rows, strict=True)
        ]
        axes[0].errorbar(x, coverage, yerr=(lower, upper), fmt="o", capsize=4)
        axes[0].axhline(0.95, color="#d1495b", linestyle="--", linewidth=1)
        axes[0].set(
            xticks=x,
            xticklabels=labels,
            ylim=(0.0, 1.05),
            ylabel="Validation truth-inclusion proportion",
            title="Local recovery calibration",
        )
        topology = [row.topology_success_proportion for row in rows]
        axes[1].bar(x, topology, color=("#2364aa", "#73bfb8", "#f2a541"))
        axes[1].axhline(0.95, color="#d1495b", linestyle="--", linewidth=1)
        axes[1].set(
            xticks=x,
            xticklabels=labels,
            ylim=(0.0, 1.05),
            ylabel="Connected and interior support proportion",
            title="Two-dimensional support topology",
        )
        figure.suptitle("Recovery and calibration across integration banks")
        figure.text(
            0.5,
            0.01,
            "full-data 160-site profiles; four-neighbour rook support",
            ha="center",
        )
        figure.tight_layout(rect=(0, 0.05, 1, 0.95))
    return figure


def _bank_predictive_figure(result: Goal007Result) -> Figure:
    rows = result.bank_summaries
    labels = [row.bank_variant.replace("_", " ") for row in rows]
    estimates = [row.paired_brier_interval.estimate for row in rows]
    lower = [
        value - row.paired_brier_interval.lower for value, row in zip(estimates, rows, strict=True)
    ]
    upper = [
        row.paired_brier_interval.upper - value for value, row in zip(estimates, rows, strict=True)
    ]
    with _svg_style():
        figure, axis = plt.subplots(figsize=(8.0, 4.8))
        x = np.arange(len(rows))
        axis.errorbar(x, estimates, yerr=(lower, upper), fmt="o", capsize=5)
        axis.axhline(0.0, color="#d1495b", linestyle="--", linewidth=1)
        axis.set(
            xticks=x,
            xticklabels=labels,
            ylabel="Worst tied-process-MLE Brier minus neutral Brier",
            title="Held-out predictive comparison across banks",
        )
        figure.text(
            0.5,
            0.01,
            "training-only fits; 40 held-out sites; lower favours the process",
            ha="center",
        )
        figure.tight_layout(rect=(0, 0.05, 1, 1))
    return figure


def _interval_payload(interval: Any) -> dict[str, float]:
    return {
        "estimate": float(interval.estimate),
        "lower": float(interval.lower),
        "upper": float(interval.upper),
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: Sequence[CsvRow]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path.name}")
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            if list(row.keys()) != fields:
                raise ValueError(f"CSV schema changed within {path.name}")
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


def _csv_value(value: CsvValue) -> str | int:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("CSV values must be finite")
        return format(value, ".17g")
    return value


def _compact_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), allow_nan=False)


def _write_svg(path: Path, figure: Figure) -> None:
    buffer = io.StringIO()
    figure.savefig(buffer, format="svg", metadata={"Date": None})
    plt.close(figure)
    path.write_text(_normalize_svg_ids(buffer.getvalue()), encoding="utf-8")


def _normalize_svg_ids(text: str) -> str:
    token_pattern = r"(?:image|m|p)[0-9a-f]{10}|C\d+_\d+_[0-9a-f]{10}"
    tokens = list(dict.fromkeys(re.findall(token_pattern, text)))
    replacements: dict[str, str] = {}
    for index, token in enumerate(tokens):
        if token.startswith("image"):
            prefix = "image"
        elif token.startswith("C"):
            prefix = f"{token.rsplit('_', 1)[0]}_"
        else:
            prefix = token[0]
        replacements[token] = f"{prefix}{index:010d}"
    return re.sub(token_pattern, lambda match: replacements[match.group(0)], text)


@contextmanager
def _svg_style() -> Any:
    with mpl.rc_context(
        {
            "svg.hashsalt": "latent-landscapes-goal007",
            "font.family": "DejaVu Sans",
            "axes.grid": True,
            "grid.alpha": 0.2,
            "figure.dpi": 100,
        }
    ):
        yield


def _validate_serialized_bundle(target: Path, relative_paths: set[str]) -> None:
    forbidden = (b"/Users/", b"/tmp/", b"NaN", b"Infinity")
    for relative in relative_paths:
        contents = (target / relative).read_bytes()
        if any(token in contents for token in forbidden):
            raise RuntimeError(f"nonportable or non-finite content in {relative}")
