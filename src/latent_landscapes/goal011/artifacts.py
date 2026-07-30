"""Deterministic review-pack writer for Goal 011."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from .benchmark import (
    HISTORICAL_GOAL007_REFERENCE,
    SOURCE_IDENTITY,
    Goal011Result,
)

DEFAULT_OUTPUT_DIR = Path("artifacts/goal011_joint_known_imperfect_detection")
ROOT_FILES = (
    "config.json",
    "seed_manifest.csv",
    "observation_signal_summary.csv",
    "calibration_results.csv",
    "validation_results.csv",
    "bank_summary.csv",
    "predictive_summary.csv",
    "domain_comparison.csv",
    "representative_profile.csv",
    "summary.json",
    "verification.json",
    "review.md",
)
VISUAL_FILES = (
    "joint_profile_surface.svg",
    "recovery_calibration.svg",
    "domain_and_bank_comparison.svg",
)
EXPECTED_FILE_COUNT = 15
METHOD = "site-history simulated composite likelihood"

type CsvValue = str | int | float | bool | None
type CsvRow = Mapping[str, CsvValue]


def write_review_bundle(
    result: Goal011Result,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, ...]:
    """Write and reconcile the exact ignored 15-file review pack."""
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
    _write_csv(paths["domain_comparison.csv"], _domain_rows(result))
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
        visual_paths["domain_and_bank_comparison.svg"],
        _domain_and_bank_comparison_figure(result),
    )

    observed_without_verification = {
        path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()
    }
    if observed_without_verification != expected - {"verification.json"}:
        raise RuntimeError("artifact contract mismatch before verification")
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
            "known_detection_probability": 0.65,
            "false_positive_probability": 0.0,
            "replicate_visits_retained": True,
            "old_domain_projection_is_gating": False,
        },
    )
    observed = {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()}
    if observed != expected:
        raise RuntimeError("final artifact contract mismatch")
    return tuple(target / relative for relative in sorted(expected))


def _config_payload(result: Goal011Result) -> dict[str, object]:
    config = result.config
    return {
        "goal": "011",
        "method": METHOD,
        "truth": {"rho": 1.0, "eta": 1.0},
        "known_detection_probability": 0.65,
        "false_positive_probability": 0.0,
        "replicate_visits": [1, 2],
        "replicate_visits_retained": True,
        "records_per_dataset": 1920,
        "training_records_per_dataset": 1440,
        "holdout_records_per_dataset": 480,
        "survey_times": [10, 20, 30, 40, 50, 60],
        "master_seed": config.master_seed,
        "bank_size": config.bank_size,
        "half_bank_size": config.half_bank_size,
        "calibration_replicates": config.calibration_replicates,
        "validation_replicates": config.validation_replicates,
        "calibration_rank_one_based": config.calibration_rank_one_based,
        "candidate_rhos": list(config.rhos),
        "candidate_etas": list(config.etas),
        "old_domain_maximum_eta": 2.0,
        "old_domain_projection_is_gating": False,
        "bank_variants": list(row.name for row in result.bank_variants),
        "between_site_process_dependence": "omitted",
        "is_full_joint_spatial_likelihood": False,
        "historical_goal007_reference": HISTORICAL_GOAL007_REFERENCE,
    }


def _seed_rows(result: Goal011Result) -> list[CsvRow]:
    rows: list[CsvRow] = []
    groups = (
        (0, "integration_bank", result.seed_manifest.integration_bank),
        (
            1,
            "calibration_process",
            tuple(row.process for row in result.seed_manifest.calibration),
        ),
        (
            2,
            "validation_process",
            tuple(row.process for row in result.seed_manifest.validation),
        ),
        (
            3,
            "calibration_detection",
            tuple(row.detection for row in result.seed_manifest.calibration),
        ),
        (
            4,
            "validation_detection",
            tuple(row.detection for row in result.seed_manifest.validation),
        ),
    )
    for root_index, phase_root, records in groups:
        for row in records:
            rows.append(
                {
                    "phase_root_index": root_index,
                    "phase_root": phase_root,
                    "phase": row.phase,
                    "index": row.index,
                    "stream_role": row.stream_role,
                    "entropy": row.entropy,
                    "spawn_key": _compact_json(row.spawn_key),
                    "state_words": _compact_json(row.state_words),
                    "pool_size": row.pool_size,
                }
            )
    return rows


def _observation_rows(result: Goal011Result) -> list[CsvRow]:
    return [
        {
            "survey_time": row.survey_time,
            "occupied_fraction_mean": row.occupied_fraction_mean,
            "occupied_fraction_lower": row.occupied_fraction_lower,
            "occupied_fraction_upper": row.occupied_fraction_upper,
            "detected_fraction_mean": row.detected_fraction_mean,
            "detected_fraction_lower": row.detected_fraction_lower,
            "detected_fraction_upper": row.detected_fraction_upper,
        }
        for row in result.observation_signal_summary
    ]


def _calibration_rows(result: Goal011Result) -> list[CsvRow]:
    return [
        {
            "dataset_index": row.dataset_index,
            "bank_variant": row.bank_variant,
            "record_count": row.record_count,
            "no_false_positives": row.no_false_positives,
            "truth_eta_index": row.truth_eta_index,
            "truth_rho_index": row.truth_rho_index,
            "expanded_lr_at_truth": row.expanded_lr_at_truth,
            "old_domain_lr_at_truth": row.old_domain_lr_at_truth,
            "expanded_truth_log_likelihood": row.expanded_truth_log_likelihood,
            "old_domain_truth_log_likelihood": row.old_domain_truth_log_likelihood,
            "expanded_maximum_log_likelihood": row.expanded_maximum_log_likelihood,
            "old_domain_maximum_log_likelihood": row.old_domain_maximum_log_likelihood,
            "expanded_mle_cells": _compact_json(row.expanded_mle_cells),
            "old_domain_mle_cells": _compact_json(row.old_domain_mle_cells),
        }
        for row in result.calibration_results
    ]


def _validation_rows(result: Goal011Result) -> list[CsvRow]:
    return [
        {
            "dataset_index": row.dataset_index,
            "bank_variant": row.bank_variant,
            "record_count": row.record_count,
            "training_record_count": row.training_record_count,
            "holdout_record_count": row.holdout_record_count,
            "split_isolated": row.split_isolated,
            "no_false_positives": row.no_false_positives,
            "expanded_lr_at_truth": row.expanded_lr_at_truth,
            "old_domain_lr_at_truth": row.old_domain_lr_at_truth,
            "expanded_truth_included": row.expanded_truth_included,
            "expanded_support_cell_count": row.expanded_support_cell_count,
            "expanded_support_component_count": row.expanded_support_component_count,
            "expanded_support_boundary_contact": row.expanded_support_boundary_contact,
            "expanded_support_boundary_faces": _compact_json(row.expanded_support_boundary_faces),
            "expanded_projected_log_rho_width": row.expanded_projected_log_rho_width,
            "expanded_projected_eta_width": row.expanded_projected_eta_width,
            "expanded_support_indices": _compact_json(row.expanded_support_indices),
            "expanded_support_correlation": row.expanded_support_correlation,
            "expanded_support_correlation_reason": row.expanded_support_correlation_reason,
            "expanded_mle_indices": _compact_json(row.expanded_mle_indices),
            "expanded_mle_cells": _compact_json(row.expanded_mle_cells),
            "expanded_minimum_absolute_log_rho_error": (
                row.expanded_minimum_absolute_log_rho_error
            ),
            "expanded_minimum_absolute_eta_error": (row.expanded_minimum_absolute_eta_error),
            "expanded_training_mle_cells": _compact_json(row.expanded_training_mle_cells),
            "expanded_support_uses_appended_eta": row.expanded_support_uses_appended_eta,
            "expanded_mle_uses_appended_eta": row.expanded_mle_uses_appended_eta,
            "expanded_paired_brier_difference": row.expanded_paired_brier_difference,
            "old_domain_truth_included": row.old_domain_truth_included,
            "old_domain_support_cell_count": row.old_domain_support_cell_count,
            "old_domain_support_component_count": row.old_domain_support_component_count,
            "old_domain_support_boundary_contact": row.old_domain_support_boundary_contact,
            "old_domain_support_boundary_faces": _compact_json(
                row.old_domain_support_boundary_faces
            ),
            "old_domain_projected_log_rho_width": row.old_domain_projected_log_rho_width,
            "old_domain_projected_eta_width": row.old_domain_projected_eta_width,
            "old_domain_support_indices": _compact_json(row.old_domain_support_indices),
            "old_domain_mle_cells": _compact_json(row.old_domain_mle_cells),
            "old_domain_minimum_absolute_log_rho_error": (
                row.old_domain_minimum_absolute_log_rho_error
            ),
            "old_domain_minimum_absolute_eta_error": (row.old_domain_minimum_absolute_eta_error),
            "old_domain_training_mle_cells": _compact_json(row.old_domain_training_mle_cells),
            "old_domain_paired_brier_difference": row.old_domain_paired_brier_difference,
        }
        for row in result.validation_results
    ]


def _bank_rows(result: Goal011Result) -> list[CsvRow]:
    return [
        {
            "bank_variant": row.bank_variant,
            "draw_count": row.draw_count,
            "expanded_cutoff": row.cutoff.cutoff,
            "old_domain_cutoff": row.old_domain_cutoff.cutoff,
            "expanded_coverage_success_count": row.expanded_coverage_success_count,
            "expanded_coverage_estimate": row.expanded_calibrated_coverage.estimate,
            "expanded_coverage_lower": row.expanded_calibrated_coverage.lower,
            "expanded_coverage_upper": row.expanded_calibrated_coverage.upper,
            "expanded_topology_success_count": row.expanded_topology_success_count,
            "expanded_boundary_contact_count": row.expanded_boundary_contact_count,
            "expanded_median_minimum_absolute_log_rho_error": (
                row.expanded_median_minimum_absolute_log_rho_error
            ),
            "expanded_median_minimum_absolute_eta_error": (
                row.expanded_median_minimum_absolute_eta_error
            ),
            "expanded_median_projected_log_rho_width": (
                row.expanded_median_projected_log_rho_width
            ),
            "expanded_median_projected_eta_width": (row.expanded_median_projected_eta_width),
            "expanded_downstream_class": row.expanded_downstream_class,
            "old_domain_coverage_success_count": row.old_domain_coverage_success_count,
            "old_domain_coverage_estimate": row.old_domain_calibrated_coverage.estimate,
            "old_domain_coverage_lower": row.old_domain_calibrated_coverage.lower,
            "old_domain_coverage_upper": row.old_domain_calibrated_coverage.upper,
            "old_domain_topology_success_count": row.old_domain_topology_success_count,
            "old_domain_boundary_contact_count": row.old_domain_boundary_contact_count,
            "old_domain_median_minimum_absolute_log_rho_error": (
                row.old_domain_median_minimum_absolute_log_rho_error
            ),
            "old_domain_median_minimum_absolute_eta_error": (
                row.old_domain_median_minimum_absolute_eta_error
            ),
            "old_domain_median_projected_log_rho_width": (
                row.old_domain_median_projected_log_rho_width
            ),
            "old_domain_median_projected_eta_width": (row.old_domain_median_projected_eta_width),
            "old_domain_downstream_class": row.old_domain_downstream_class,
        }
        for row in result.bank_summaries
    ]


def _predictive_rows(result: Goal011Result) -> list[CsvRow]:
    return [
        {
            "bank_variant": row.bank_variant,
            "expanded_paired_brier_estimate": row.expanded_paired_brier_interval.estimate,
            "expanded_paired_brier_lower": row.expanded_paired_brier_interval.lower,
            "expanded_paired_brier_upper": row.expanded_paired_brier_interval.upper,
            "old_domain_paired_brier_estimate": row.old_domain_paired_brier_interval.estimate,
            "old_domain_paired_brier_lower": row.old_domain_paired_brier_interval.lower,
            "old_domain_paired_brier_upper": row.old_domain_paired_brier_interval.upper,
            "expanded_mean_stochastic_brier_worst_mle": (
                row.expanded_mean_stochastic_brier_worst_mle
            ),
            "mean_neutral_brier": row.mean_neutral_brier,
            "prediction_target": "0.65 * marginal occupancy probability",
            "neutral_training_record_count": 1440,
            "holdout_record_count": 480,
        }
        for row in result.bank_summaries
    ]


def _domain_rows(result: Goal011Result) -> list[CsvRow]:
    return [
        {
            "bank_variant": row.bank_variant,
            "expanded_cutoff": row.expanded_cutoff,
            "old_domain_cutoff": row.old_domain_cutoff,
            "cutoff_difference": row.cutoff_difference,
            "expanded_downstream_class": row.expanded_downstream_class,
            "old_domain_downstream_class": row.old_domain_downstream_class,
            "appended_support_use_count": row.appended_support_use_count,
            "appended_mle_use_count": row.appended_mle_use_count,
            "expanded_boundary_contact_count": row.expanded_boundary_contact_count,
            "old_domain_boundary_contact_count": row.old_domain_boundary_contact_count,
            "old_domain_projection_is_gating": False,
        }
        for row in result.domain_comparisons
    ]


def _representative_rows(result: Goal011Result) -> list[CsvRow]:
    rows: list[CsvRow] = []
    for representative in result.representative_profiles:
        expanded = representative.expanded_profile
        old = representative.old_domain_profile
        expanded_support = set(representative.expanded_summary.support_indices)
        old_support = set(representative.old_domain_summary.support_indices)
        expanded_mles = set(expanded.mle_indices)
        old_mles = set(old.mle_indices)
        for eta_index, eta in enumerate(expanded.etas):
            for rho_index, rho in enumerate(expanded.rhos):
                in_old = eta_index < len(old.etas)
                rows.append(
                    {
                        "dataset_index": representative.dataset_index,
                        "bank_variant": representative.bank_variant,
                        "eta_index": eta_index,
                        "rho_index": rho_index,
                        "eta": float(eta),
                        "rho": float(rho),
                        "expanded_log_likelihood": float(
                            expanded.log_likelihoods[eta_index, rho_index]
                        ),
                        "expanded_in_support": (eta_index, rho_index) in expanded_support,
                        "expanded_is_mle": (eta_index, rho_index) in expanded_mles,
                        "expanded_cutoff": representative.expanded_cutoff,
                        "old_domain_log_likelihood": (
                            float(old.log_likelihoods[eta_index, rho_index]) if in_old else None
                        ),
                        "old_domain_in_support": (
                            (eta_index, rho_index) in old_support if in_old else None
                        ),
                        "old_domain_is_mle": (
                            (eta_index, rho_index) in old_mles if in_old else None
                        ),
                        "old_domain_cutoff": representative.old_domain_cutoff,
                    }
                )
    return rows


def _summary_payload(result: Goal011Result) -> dict[str, object]:
    return {
        "outcome": result.outcome,
        "primary_domain": {"eta_minimum": 0.0, "eta_maximum": 2.5},
        "old_domain_projection": {"eta_minimum": 0.0, "eta_maximum": 2.0},
        "old_domain_projection_is_gating": False,
        "known_detection_probability": 0.65,
        "replicate_visits_retained": True,
        "bank_classes": {
            row.bank_variant: {
                "expanded": row.expanded_downstream_class,
                "old_domain": row.old_domain_downstream_class,
            }
            for row in result.bank_summaries
        },
        "historical_goal007_reference": HISTORICAL_GOAL007_REFERENCE,
        "historical_comparison_is_strict_causal_estimate": False,
        "conditional_scope": "one landscape and one central truth",
    }


def _render_review(result: Goal011Result) -> str:
    rows = "\n".join(
        (
            f"| {row.bank_variant} | {row.cutoff.cutoff:.6f} | "
            f"{row.old_domain_cutoff.cutoff:.6f} | "
            f"{row.expanded_downstream_class} | {row.old_domain_downstream_class} |"
        )
        for row in result.bank_summaries
    )
    return f"""# Goal 011 Scientific Review

## Generated Observations

Each central-truth dataset retains all 1,920 visit records: two conditionally
independent visits at six survey times for 160 sites. Detection uses known p = 0.65;
false-positive probability is zero, and detection is not estimated.

## Scientific Inference

The primary expanded-domain outcome is `{result.outcome}`.

| Bank | Expanded cutoff | Eta <= 2 cutoff | Expanded class | Eta <= 2 class |
|---|---:|---:|---|---|
{rows}

The primary decision uses `eta <= 2.5`. The separately recalibrated
`eta <= 2` projection is descriptive and non-gating. Goal 007's
perfect-detection result is historical context. It is not a strict causal estimate
of imperfect detection because its candidate eta ceiling also
differed.

Held-out process predictions target known `p * Pr(occupied)` for each visit.
The neutral comparator is fitted only to the 1,440 training visit records and
scores the same 480 holdout visits.

## Limitation

This site-history simulated composite likelihood is not a full joint spatial likelihood.
It preserves within-site repeated-observation dependence through
the latent onset category but omits between-site dependence from the shared
stochastic edge field. Conclusions remain conditional on one landscape, one
sampling design, and one central truth.
"""


def _joint_profile_surface_figure(result: Goal011Result) -> Figure:
    representative = next(
        row for row in result.representative_profiles if row.bank_variant == "full"
    )
    profile = representative.expanded_profile
    relative = profile.log_likelihoods - profile.maximum_log_likelihood
    with _svg_style():
        figure, axis = plt.subplots(figsize=(8.2, 4.8))
        image = axis.imshow(
            relative,
            aspect="auto",
            origin="lower",
            extent=(
                float(np.log2(profile.rhos[0])),
                float(np.log2(profile.rhos[-1])),
                float(profile.etas[0]),
                float(profile.etas[-1]),
            ),
            cmap="viridis",
        )
        axis.set_xlabel("log2 rho")
        axis.set_ylabel("eta")
        axis.set_title("Validation dataset 0: full-bank joint profile")
        figure.colorbar(image, ax=axis, label="log likelihood relative to maximum")
        figure.tight_layout()
    return figure


def _recovery_calibration_figure(result: Goal011Result) -> Figure:
    with _svg_style():
        figure, axes = plt.subplots(1, 3, figsize=(10.2, 3.8), sharey=True)
        for axis, summary in zip(axes, result.bank_summaries, strict=True):
            values = [
                row.expanded_lr_at_truth
                for row in result.calibration_results
                if row.bank_variant == summary.bank_variant
            ]
            axis.hist(values, bins=min(20, max(2, len(values))), color="#2a6f97")
            axis.axvline(summary.cutoff.cutoff, color="#c23b22", linewidth=1.8)
            axis.set_title(summary.bank_variant.replace("_", " "))
            axis.set_xlabel("LR at truth")
        axes[0].set_ylabel("Calibration datasets")
        figure.suptitle("Fresh Goal 011 calibration by bank")
        figure.tight_layout()
    return figure


def _domain_and_bank_comparison_figure(result: Goal011Result) -> Figure:
    labels = [row.bank_variant.replace("_", " ") for row in result.domain_comparisons]
    expanded = [row.expanded_cutoff for row in result.domain_comparisons]
    old = [row.old_domain_cutoff for row in result.domain_comparisons]
    x = np.arange(len(labels))
    with _svg_style():
        figure, axis = plt.subplots(figsize=(8.0, 4.4))
        axis.bar(x - 0.18, expanded, width=0.36, label="eta <= 2.5", color="#2a6f97")
        axis.bar(x + 0.18, old, width=0.36, label="eta <= 2", color="#d08c32")
        axis.set_xticks(x, labels)
        axis.set_ylabel("Calibrated LR cutoff")
        axis.set_title("Primary and non-gating domain cutoffs")
        axis.legend()
        figure.tight_layout()
    return figure


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: Sequence[CsvRow]) -> None:
    if not rows:
        raise ValueError(f"CSV rows must not be empty: {path.name}")
    buffer = io.StringIO(newline="")
    fieldnames = list(rows[0])
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if list(row) != fieldnames:
            raise ValueError(f"CSV row schema mismatch: {path.name}")
        writer.writerow({key: _csv_value(value) for key, value in row.items()})
    path.write_text(buffer.getvalue(), encoding="utf-8")


def _csv_value(value: CsvValue) -> str | int | float:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _compact_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), allow_nan=False)


def _write_svg(path: Path, figure: Figure) -> None:
    buffer = io.StringIO()
    figure.savefig(buffer, format="svg", metadata={"Date": None})
    plt.close(figure)
    text = _normalize_svg_ids(buffer.getvalue())
    text = re.sub(r"<dc:date>.*?</dc:date>", "", text)
    path.write_text(text, encoding="utf-8")


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
def _svg_style() -> Iterator[None]:
    with mpl.rc_context(
        {
            "svg.hashsalt": "latent-landscapes-goal011",
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    ):
        yield


__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "EXPECTED_FILE_COUNT",
    "write_review_bundle",
]
