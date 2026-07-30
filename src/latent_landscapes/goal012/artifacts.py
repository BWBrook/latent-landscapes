"""Deterministic review artifacts for Goal 012."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import platform
import re
import subprocess
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from latent_landscapes.goal004.benchmark import (
    StreamSeedRecord as DetectionSeedRecord,
)
from latent_landscapes.goal007.benchmark import (
    StreamSeedRecord as ProcessSeedRecord,
)
from latent_landscapes.goal008 import artifacts as goal008_artifacts

from .benchmark import (
    BANK_VARIANT_NAMES,
    SOURCE_IDENTITY,
    CalibrationResult,
    CellBankSummary,
    Goal012Result,
    ValidationResult,
)

DEFAULT_OUTPUT_DIR = Path("artifacts/goal012_cross_truth_joint_known_imperfect_detection")
EXPECTED_FILES = (
    "config.json",
    "compute_provenance.json",
    "seed_manifest.csv",
    "observation_signal_summary.csv",
    "calibration_results.csv",
    "validation_results.csv",
    "truth_cell_summary.csv",
    "representative_profiles.csv",
    "central_reconciliation.json",
    "summary.json",
    "verification.json",
    "review.md",
    "visuals/truth_grid_recovery_calibration.svg",
    "visuals/truth_grid_prediction.svg",
    "visuals/truth_grid_domain_and_ridge.svg",
)
PORTABLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CsvValue = str | int | float | bool | None
CsvRow = dict[str, CsvValue]


def validate_pre_campaign_provenance(
    declared: Mapping[str, object],
    *,
    workers: int,
) -> None:
    """Validate portable smoke metadata or the strict production declaration."""
    provenance = dict(declared)
    _validate_portable_provenance(provenance)
    _validate_portable_identifiers(provenance)
    mode = provenance.get("provenance_mode")
    if mode == "production":
        goal008_artifacts.validate_pre_campaign_provenance(
            provenance,
            workers=workers,
        )
    elif mode != "test":
        raise ValueError("compute provenance mode must be 'test' or 'production'")


def write_review_bundle(
    result: Goal012Result,
    output_dir: Path,
    compute_provenance: Mapping[str, object],
) -> tuple[Path, ...]:
    """Write the exact deterministic 15-file Goal 012 review pack."""
    if result.outcome == "implementation_blocked":
        raise ValueError("cannot serialize an implementation-blocked result")
    if not result.invariants or not all(result.invariants.values()):
        raise ValueError("cannot serialize a result with failed implementation invariants")
    provenance = _validated_compute_provenance(result, compute_provenance)
    target = Path(output_dir)
    if target.exists() and any(target.rglob("*")):
        raise RuntimeError("refusing to overwrite stale review-pack content")
    target.mkdir(parents=True, exist_ok=True)
    (target / "visuals").mkdir(exist_ok=True)

    _write_json(target / "config.json", _config_payload(result))
    _write_json(target / "compute_provenance.json", provenance)
    _write_csv(target / "seed_manifest.csv", _seed_rows(result))
    _write_csv(
        target / "observation_signal_summary.csv",
        _observation_rows(result),
    )
    _write_csv(target / "calibration_results.csv", _calibration_rows(result))
    _write_csv(target / "validation_results.csv", _validation_rows(result))
    _write_csv(target / "truth_cell_summary.csv", _summary_rows(result))
    _write_csv(
        target / "representative_profiles.csv",
        _representative_rows(result),
    )
    _write_json(
        target / "central_reconciliation.json",
        _central_payload(result),
    )
    _write_json(target / "summary.json", _summary_payload(result))
    (target / "review.md").write_text(_render_review(result), encoding="utf-8")
    _write_svg(
        target / "visuals/truth_grid_recovery_calibration.svg",
        _truth_grid_recovery_calibration_figure(result),
    )
    _write_svg(
        target / "visuals/truth_grid_prediction.svg",
        _truth_grid_prediction_figure(result),
    )
    _write_svg(
        target / "visuals/truth_grid_domain_and_ridge.svg",
        _truth_grid_domain_and_ridge_figure(result),
    )

    hashes = {
        relative: hashlib.sha256((target / relative).read_bytes()).hexdigest()
        for relative in EXPECTED_FILES
        if relative != "verification.json"
    }
    _write_json(
        target / "verification.json",
        {
            "goal": "012-cross-truth-joint-known-imperfect-detection",
            "outcome": result.outcome,
            "expected_artifact_file_count": 15,
            "observed_artifact_file_count": 15,
            "all_invariants_pass": all(result.invariants.values()),
            "invariants": result.invariants,
            "sha256": hashes,
            "source_identity": SOURCE_IDENTITY,
            "central_reference_checked": (
                result.central_reconciliation.production_reference_checked
            ),
            "central_reference_match": (result.central_reconciliation.production_reference_match),
            "pointwise_not_familywise": True,
            "old_domain_projection_is_gating": False,
            "compute_provenance_validated": True,
        },
    )
    observed = {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()}
    if observed != set(EXPECTED_FILES):
        raise RuntimeError("review pack does not match the exact 15-file contract")
    _validate_serialized_bundle(target, observed)
    return tuple(target / relative for relative in EXPECTED_FILES)


def _config_payload(result: Goal012Result) -> dict[str, object]:
    config = result.config
    return {
        "goal": "012",
        "method": "site-history simulated composite likelihood",
        "truth_cell_order": [cell.cell_id for cell in config.resolved_truth_cells],
        "truth_grid": [
            {
                "truth_cell": cell.cell_id,
                "rho": cell.rho,
                "eta": cell.eta,
                "rho_index": cell.rho_index,
                "eta_index": cell.eta_index,
            }
            for cell in config.resolved_truth_cells
        ],
        "known_detection_probability": 0.65,
        "false_positive_probability": 0.0,
        "replicate_visits": [1, 2],
        "replicate_visits_retained": True,
        "records_per_dataset": 1920,
        "training_records_per_dataset": 1440,
        "holdout_records_per_dataset": 480,
        "survey_times": [10, 20, 30, 40, 50, 60],
        "master_seed": config.master_seed,
        "seed_root_count": 7,
        "bank_size": config.bank_size,
        "half_bank_size": config.half_bank_size,
        "calibration_blocks": config.calibration_blocks,
        "validation_blocks": config.validation_blocks,
        "calibration_rank_one_based": config.calibration_rank_one_based,
        "candidate_rhos": list(config.rhos),
        "candidate_etas": list(config.etas),
        "old_domain_eta_maximum": 2.0,
        "old_domain_projection_is_gating": False,
        "bank_variants": list(BANK_VARIANT_NAMES),
        "independent_unit": "process block",
        "cross_truth_process_pairing": True,
        "cross_truth_observation_noise_pairing": False,
        "between_site_process_dependence": "omitted",
        "is_full_joint_spatial_likelihood": False,
    }


def _seed_rows(result: Goal012Result) -> list[CsvRow]:
    rows: list[CsvRow] = []
    for row in result.seed_manifest.integration_bank:
        rows.append(_seed_row(0, "integration_bank", None, row))
    groups = (
        (1, "calibration_process", result.seed_manifest.calibration, "process"),
        (2, "validation_process", result.seed_manifest.validation, "process"),
    )
    for root_index, phase_root, blocks, _ in groups:
        for block in blocks:
            rows.append(
                _seed_row(
                    root_index,
                    phase_root,
                    None,
                    block.process,
                )
            )
    detection_groups = (
        (3, "calibration_central_detection", result.seed_manifest.calibration),
        (4, "validation_central_detection", result.seed_manifest.validation),
    )
    for root_index, phase_root, blocks in detection_groups:
        for block in blocks:
            rows.append(
                _seed_row(
                    root_index,
                    phase_root,
                    "cell-04",
                    block.detection_for("cell-04"),
                )
            )
    appended_groups = (
        (5, "calibration_noncentral_detection", result.seed_manifest.calibration),
        (6, "validation_noncentral_detection", result.seed_manifest.validation),
    )
    for root_index, phase_root, blocks in appended_groups:
        for block in blocks:
            for item in block.cell_detection:
                if item.truth_cell != "cell-04":
                    rows.append(
                        _seed_row(
                            root_index,
                            phase_root,
                            item.truth_cell,
                            item.detection,
                        )
                    )
    return rows


def _seed_row(
    root_index: int,
    phase_root: str,
    truth_cell: str | None,
    row: ProcessSeedRecord | DetectionSeedRecord,
) -> CsvRow:
    return {
        "phase_root_index": root_index,
        "phase_root": phase_root,
        "truth_cell": truth_cell,
        "phase": row.phase,
        "index": row.index,
        "stream_role": row.stream_role,
        "entropy": row.entropy,
        "spawn_key": _compact_json(row.spawn_key),
        "state_words": _compact_json(row.state_words),
        "pool_size": row.pool_size,
    }


def _observation_rows(result: Goal012Result) -> list[CsvRow]:
    return [
        {
            "truth_cell": row.truth_cell,
            "truth_rho": row.truth_rho,
            "truth_eta": row.truth_eta,
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


def _identity_row(row: CalibrationResult | ValidationResult) -> CsvRow:
    return {
        "phase": row.phase,
        "block_index": row.block_index,
        "pairing_group": row.pairing_group,
        "truth_cell": row.truth_cell,
        "truth_rho": row.truth_rho,
        "truth_eta": row.truth_eta,
        "truth_rho_index": row.truth_rho_index,
        "truth_eta_index": row.truth_eta_index,
        "bank_variant": row.bank_variant,
        "cutoff_source_cell": row.cutoff_source_cell,
        "cutoff_source_rho": row.cutoff_source_rho,
        "cutoff_source_eta": row.cutoff_source_eta,
    }


def _calibration_rows(result: Goal012Result) -> list[CsvRow]:
    return [
        _identity_row(row)
        | {
            "record_count": row.record_count,
            "no_false_positives": row.no_false_positives,
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


def _validation_rows(result: Goal012Result) -> list[CsvRow]:
    return [
        _identity_row(row)
        | {
            "record_count": row.record_count,
            "training_record_count": row.training_record_count,
            "holdout_record_count": row.holdout_record_count,
            "split_isolated": row.split_isolated,
            "no_false_positives": row.no_false_positives,
            "expanded_lr_at_truth": row.expanded_lr_at_truth,
            "old_domain_lr_at_truth": row.old_domain_lr_at_truth,
            "expanded_truth_included": row.expanded_truth_included,
            "expanded_support_cell_count": row.expanded_support_cell_count,
            "expanded_support_component_count": (row.expanded_support_component_count),
            "expanded_support_boundary_contact": (row.expanded_support_boundary_contact),
            "expanded_support_boundary_faces": _compact_json(row.expanded_support_boundary_faces),
            "expanded_projected_log_rho_width": (row.expanded_projected_log_rho_width),
            "expanded_projected_eta_width": row.expanded_projected_eta_width,
            "expanded_support_indices": _compact_json(row.expanded_support_indices),
            "expanded_support_correlation": row.expanded_support_correlation,
            "expanded_support_correlation_reason": (row.expanded_support_correlation_reason),
            "expanded_mle_indices": _compact_json(row.expanded_mle_indices),
            "expanded_mle_cells": _compact_json(row.expanded_mle_cells),
            "expanded_minimum_absolute_log_rho_error": (
                row.expanded_minimum_absolute_log_rho_error
            ),
            "expanded_minimum_absolute_eta_error": (row.expanded_minimum_absolute_eta_error),
            "expanded_training_mle_cells": _compact_json(row.expanded_training_mle_cells),
            "expanded_support_uses_appended_eta": (row.expanded_support_uses_appended_eta),
            "expanded_mle_uses_appended_eta": row.expanded_mle_uses_appended_eta,
            "expanded_stochastic_log_score_minimum": (row.expanded_stochastic_log_score_minimum),
            "expanded_stochastic_log_score_maximum": (row.expanded_stochastic_log_score_maximum),
            "expanded_stochastic_brier_minimum": (row.expanded_stochastic_brier_minimum),
            "expanded_stochastic_brier_maximum": (row.expanded_stochastic_brier_maximum),
            "expanded_stochastic_probability_minimum": (
                row.expanded_stochastic_probability_minimum
            ),
            "expanded_stochastic_probability_maximum": (
                row.expanded_stochastic_probability_maximum
            ),
            "neutral_log_score": row.neutral_log_score,
            "neutral_brier_score": row.neutral_brier_score,
            "neutral_probability_minimum": row.neutral_probability_minimum,
            "neutral_probability_maximum": row.neutral_probability_maximum,
            "expanded_paired_brier_difference": (row.expanded_paired_brier_difference),
            "old_domain_truth_included": row.old_domain_truth_included,
            "old_domain_support_cell_count": row.old_domain_support_cell_count,
            "old_domain_support_component_count": (row.old_domain_support_component_count),
            "old_domain_support_boundary_contact": (row.old_domain_support_boundary_contact),
            "old_domain_support_boundary_faces": _compact_json(
                row.old_domain_support_boundary_faces
            ),
            "old_domain_projected_log_rho_width": (row.old_domain_projected_log_rho_width),
            "old_domain_projected_eta_width": row.old_domain_projected_eta_width,
            "old_domain_support_indices": _compact_json(row.old_domain_support_indices),
            "old_domain_mle_cells": _compact_json(row.old_domain_mle_cells),
            "old_domain_minimum_absolute_log_rho_error": (
                row.old_domain_minimum_absolute_log_rho_error
            ),
            "old_domain_minimum_absolute_eta_error": (row.old_domain_minimum_absolute_eta_error),
            "old_domain_training_mle_cells": _compact_json(row.old_domain_training_mle_cells),
            "old_domain_paired_brier_difference": (row.old_domain_paired_brier_difference),
        }
        for row in result.validation_results
    ]


def _summary_rows(result: Goal012Result) -> list[CsvRow]:
    return [_summary_row(row) for row in result.truth_cell_summaries]


def _summary_row(row: CellBankSummary) -> CsvRow:
    return {
        "truth_cell": row.truth_cell,
        "truth_rho": row.truth_rho,
        "truth_eta": row.truth_eta,
        "truth_rho_index": row.truth_rho_index,
        "truth_eta_index": row.truth_eta_index,
        "bank_variant": row.bank_variant,
        "cutoff_source_cell": row.cutoff_source_cell,
        "cutoff_source_rho": row.cutoff_source_rho,
        "cutoff_source_eta": row.cutoff_source_eta,
        "draw_count": row.draw_count,
        "expanded_cutoff": row.cutoff.cutoff,
        "expanded_cutoff_rank_one_based": row.cutoff.rank_one_based,
        "expanded_cutoff_sample_size": row.cutoff.sample_size,
        "old_domain_cutoff": row.old_domain_cutoff.cutoff,
        "old_domain_cutoff_rank_one_based": row.old_domain_cutoff.rank_one_based,
        "old_domain_cutoff_sample_size": row.old_domain_cutoff.sample_size,
        "expanded_coverage_success_count": row.expanded_coverage_success_count,
        "expanded_coverage_estimate": row.expanded_calibrated_coverage.estimate,
        "expanded_coverage_lower": row.expanded_calibrated_coverage.lower,
        "expanded_coverage_upper": row.expanded_calibrated_coverage.upper,
        "expanded_topology_success_count": row.expanded_topology_success_count,
        "expanded_physical_topology_success_count": (row.expanded_physical_topology_success_count),
        "expanded_boundary_contact_count": row.expanded_boundary_contact_count,
        "artificial_face_contact_count": row.artificial_face_contact_count,
        "rho_min_contact_count": row.rho_min_contact_count,
        "rho_max_contact_count": row.rho_max_contact_count,
        "eta_min_contact_count": row.eta_min_contact_count,
        "eta_max_contact_count": row.eta_max_contact_count,
        "expanded_median_minimum_absolute_log_rho_error": (
            row.expanded_median_minimum_absolute_log_rho_error
        ),
        "expanded_median_minimum_absolute_eta_error": (
            row.expanded_median_minimum_absolute_eta_error
        ),
        "expanded_median_projected_log_rho_width": (row.expanded_median_projected_log_rho_width),
        "expanded_median_projected_eta_width": (row.expanded_median_projected_eta_width),
        "expanded_median_support_cell_count": (row.expanded_median_support_cell_count),
        "expanded_mean_mle_set_size": row.expanded_mean_mle_set_size,
        "expanded_paired_brier_estimate": (row.expanded_paired_brier_interval.estimate),
        "expanded_paired_brier_lower": row.expanded_paired_brier_interval.lower,
        "expanded_paired_brier_upper": row.expanded_paired_brier_interval.upper,
        "expanded_mean_stochastic_brier_worst_mle": (row.expanded_mean_stochastic_brier_worst_mle),
        "mean_neutral_brier": row.mean_neutral_brier,
        "finite_log_score_count": row.finite_log_score_count,
        "expanded_candidate_domain_unclosed": (row.expanded_candidate_domain_unclosed),
        "expanded_design_limited": row.expanded_design_limited,
        "expanded_local_calibration_not_ready": (row.expanded_local_calibration_not_ready),
        "expanded_recovery_imprecise": row.expanded_recovery_imprecise,
        "expanded_neutral_better": row.expanded_neutral_better,
        "expanded_recoverable": row.expanded_recoverable,
        "expanded_mechanism_inconclusive": (row.expanded_mechanism_inconclusive),
        "expanded_class": row.expanded_class,
        "old_domain_coverage_success_count": row.old_domain_coverage_success_count,
        "old_domain_coverage_estimate": row.old_domain_calibrated_coverage.estimate,
        "old_domain_coverage_lower": row.old_domain_calibrated_coverage.lower,
        "old_domain_coverage_upper": row.old_domain_calibrated_coverage.upper,
        "old_domain_topology_success_count": row.old_domain_topology_success_count,
        "old_domain_physical_topology_success_count": (
            row.old_domain_physical_topology_success_count
        ),
        "old_domain_boundary_contact_count": (row.old_domain_boundary_contact_count),
        "old_domain_artificial_face_contact_count": (row.old_domain_artificial_face_contact_count),
        "old_domain_rho_min_contact_count": row.old_domain_rho_min_contact_count,
        "old_domain_rho_max_contact_count": row.old_domain_rho_max_contact_count,
        "old_domain_eta_min_contact_count": row.old_domain_eta_min_contact_count,
        "old_domain_eta_max_contact_count": row.old_domain_eta_max_contact_count,
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
        "old_domain_median_support_cell_count": (row.old_domain_median_support_cell_count),
        "old_domain_mean_mle_set_size": row.old_domain_mean_mle_set_size,
        "old_domain_paired_brier_estimate": (row.old_domain_paired_brier_interval.estimate),
        "old_domain_paired_brier_lower": row.old_domain_paired_brier_interval.lower,
        "old_domain_paired_brier_upper": row.old_domain_paired_brier_interval.upper,
        "old_domain_candidate_domain_unclosed": (row.old_domain_candidate_domain_unclosed),
        "old_domain_design_limited": row.old_domain_design_limited,
        "old_domain_local_calibration_not_ready": (row.old_domain_local_calibration_not_ready),
        "old_domain_recovery_imprecise": row.old_domain_recovery_imprecise,
        "old_domain_neutral_better": row.old_domain_neutral_better,
        "old_domain_recoverable": row.old_domain_recoverable,
        "old_domain_mechanism_inconclusive": (row.old_domain_mechanism_inconclusive),
        "old_domain_class": row.old_domain_class,
    }


def _representative_rows(result: Goal012Result) -> list[CsvRow]:
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
                        "truth_cell": representative.truth_cell,
                        "truth_rho": representative.truth_rho,
                        "truth_eta": representative.truth_eta,
                        "truth_rho_index": representative.truth_rho_index,
                        "truth_eta_index": representative.truth_eta_index,
                        "cutoff_source_cell": representative.cutoff_source_cell,
                        "block_index": representative.block_index,
                        "bank_variant": representative.bank_variant,
                        "eta_index": eta_index,
                        "rho_index": rho_index,
                        "eta": float(eta),
                        "rho": float(rho),
                        "expanded_log_likelihood": float(
                            expanded.log_likelihoods[eta_index, rho_index]
                        ),
                        "expanded_in_support": ((eta_index, rho_index) in expanded_support),
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


def _central_payload(result: Goal012Result) -> dict[str, object]:
    central = result.central_reconciliation
    return {
        "truth_cell": central.truth_cell,
        "source_commit": central.source_commit,
        "goal011_outcome": central.goal011_outcome,
        "production_reference_checked": central.production_reference_checked,
        "production_reference_match": central.production_reference_match,
        "checks": central.checks,
        "observed_hashes": central.observed_hashes,
        "expected_hashes": central.expected_hashes,
        "projection_float_precision_decimal_places": 9,
        "comparison_path": "Goal 011 public contract projection",
    }


def _summary_payload(result: Goal012Result) -> dict[str, object]:
    return {
        "outcome": result.outcome,
        "truth_cell_count": len(result.config.resolved_truth_cells),
        "truth_cell_bank_count": len(result.truth_cell_summaries),
        "primary_domain": {"eta_minimum": 0.0, "eta_maximum": 2.5},
        "old_domain_projection": {"eta_minimum": 0.0, "eta_maximum": 2.0},
        "old_domain_projection_is_gating": False,
        "known_detection_probability": 0.65,
        "replicate_visits_retained": True,
        "pointwise_not_familywise": True,
        "process_paired_across_truth_cells": True,
        "observation_noise_distinct_across_truth_cells": True,
        "full_bank_classes": {
            row.truth_cell: row.expanded_class
            for row in result.truth_cell_summaries
            if row.bank_variant == "full"
        },
        "bank_stable_by_cell": {
            cell.cell_id: len(
                {
                    row.expanded_class
                    for row in result.truth_cell_summaries
                    if row.truth_cell == cell.cell_id
                }
            )
            == 1
            for cell in result.config.resolved_truth_cells
        },
        "conditional_scope": "one landscape and one sampling design",
    }


def _render_review(result: Goal012Result) -> str:
    rows = "\n".join(
        (
            f"| {row.truth_cell} | {row.truth_rho:g} | {row.truth_eta:g} | "
            f"{row.cutoff.cutoff:.6f} | {row.expanded_coverage_success_count}/"
            f"{row.cutoff.sample_size} | {row.expanded_class} |"
        )
        for row in result.truth_cell_summaries
        if row.bank_variant == "full"
    )
    return f"""# Goal 012 Scientific Review

## Outcome

`{result.outcome}`

## Full-Bank Surface

| Truth cell | Rho | Eta | Local cutoff | Coverage | Class |
| --- | ---: | ---: | ---: | ---: | --- |
{rows}

## Interpretation Boundary

The nine truth cells are process-paired within each block and
observation-noise-distinct. Cell 04 reuses the exact Goal 011 process and
detection streams. Every dataset retains all 1,920 visits under known p = 0.65
and zero false positives.

The `eta <= 2.5` result is primary. The separately recalibrated `eta <= 2`
projection is descriptive and non-gating. Contact with the artificial
`eta_max`, `rho_min`, or `rho_max` faces is kept separate from contact with the
physical `eta = 0` uniform-resistance null. The 95% calibration statements are
pointwise, not familywise.

This is a complete-history simulated composite likelihood, not a full joint spatial likelihood.
It conditions on one landscape and sampling design, treats known homogeneous
detection as fixed, and does not estimate detection.
Cross-cell contrasts are correlated descriptions, not paired
observation-error effects. Negative or mixed outcomes are valid completed
scientific results.
"""


def _truth_grid_recovery_calibration_figure(result: Goal012Result) -> Figure:
    rows = _full_bank_rows(result)
    with _svg_style():
        figure, axes = plt.subplots(1, 2, figsize=(10.8, 4.6), constrained_layout=True)
        _heatmap(
            axes[0],
            _grid(rows, "expanded_calibrated_coverage", "estimate"),
            title="Local coverage estimate",
            value_format=".2f",
            cmap="viridis",
        )
        _heatmap(
            axes[1],
            _grid(rows, "expanded_median_minimum_absolute_log_rho_error"),
            title="Median absolute log-rho error",
            value_format=".3f",
            cmap="magma_r",
        )
        figure.suptitle("Goal 012 recovery and calibration", fontweight="bold")
    return figure


def _truth_grid_prediction_figure(result: Goal012Result) -> Figure:
    rows = _full_bank_rows(result)
    with _svg_style():
        figure, axes = plt.subplots(1, 2, figsize=(10.8, 4.6), constrained_layout=True)
        _heatmap(
            axes[0],
            _grid(rows, "expanded_paired_brier_interval", "estimate"),
            title="Paired Brier difference",
            value_format=".3f",
            cmap="coolwarm",
        )
        _heatmap(
            axes[1],
            _grid(rows, "expanded_mean_stochastic_brier_worst_mle"),
            title="Process Brier score",
            value_format=".3f",
            cmap="cividis_r",
        )
        figure.suptitle("Goal 012 held-out prediction", fontweight="bold")
    return figure


def _truth_grid_domain_and_ridge_figure(result: Goal012Result) -> Figure:
    rows = _full_bank_rows(result)
    with _svg_style():
        figure, axes = plt.subplots(1, 2, figsize=(10.8, 4.6), constrained_layout=True)
        _heatmap(
            axes[0],
            _grid(rows, "artificial_face_contact_count"),
            title="Artificial-face contacts",
            value_format=".0f",
            cmap="Oranges",
        )
        _heatmap(
            axes[1],
            _grid(rows, "expanded_median_projected_eta_width"),
            title="Median projected eta width",
            value_format=".2f",
            cmap="plasma_r",
        )
        figure.suptitle("Goal 012 domain and ridge diagnostics", fontweight="bold")
    return figure


def _full_bank_rows(result: Goal012Result) -> tuple[CellBankSummary, ...]:
    return tuple(row for row in result.truth_cell_summaries if row.bank_variant == "full")


def _grid(
    rows: tuple[CellBankSummary, ...],
    attribute: str,
    nested: str | None = None,
) -> np.ndarray:
    values: list[float] = []
    for row in rows:
        value = getattr(row, attribute)
        if nested is not None:
            value = getattr(value, nested)
        values.append(float(value))
    return np.asarray(values, dtype=np.float64).reshape(3, 3)


def _heatmap(
    axis: Axes,
    values: np.ndarray,
    *,
    title: str,
    value_format: str,
    cmap: str,
) -> None:
    image = axis.imshow(values, cmap=cmap, aspect="equal")
    axis.set_title(title, fontweight="bold")
    axis.set_xticks(range(3), labels=("0.5", "1", "2"))
    axis.set_yticks(range(3), labels=("0.5", "1", "1.5"))
    axis.set_xlabel("Truth rho")
    axis.set_ylabel("Truth eta")
    midpoint = float(np.nanmean(values))
    for eta_index in range(3):
        for rho_index in range(3):
            value = values[eta_index, rho_index]
            axis.text(
                rho_index,
                eta_index,
                format(value, value_format),
                ha="center",
                va="center",
                color="white" if value > midpoint else "black",
                fontsize=9,
                fontweight="bold",
            )
    plt.colorbar(image, ax=axis, fraction=0.046, pad=0.04)


def _validated_compute_provenance(
    result: Goal012Result,
    declared: Mapping[str, object],
) -> dict[str, object]:
    provenance = dict(declared)
    validate_pre_campaign_provenance(
        provenance,
        workers=result.execution_telemetry.worker_count,
    )
    if result.config.is_production and provenance.get("provenance_mode") != "production":
        raise ValueError("production result requires production provenance")
    if not result.config.is_production and provenance.get("provenance_mode") != "test":
        raise ValueError("nonproduction result requires test provenance")
    telemetry = result.execution_telemetry
    runtime = _runtime_identifiers()
    enriched = {
        **provenance,
        **runtime,
        "worker_count": telemetry.worker_count,
        "thread_limits": telemetry.thread_limits,
        "campaign_exit_success": telemetry.campaign_exit_status == 0
        and all(row.exit_status == 0 for row in telemetry.cell_telemetry),
        "cell_telemetry": [
            {
                "truth_cell": row.truth_cell,
                "exit_status": row.exit_status,
                "wall_time_seconds": row.wall_time_seconds,
                "maximum_rss_bytes": row.maximum_rss_bytes,
            }
            for row in telemetry.cell_telemetry
        ],
        "provenance_validation_passed": True,
    }
    _validate_portable_provenance(enriched)
    return enriched


def _validate_portable_provenance(provenance: Mapping[str, object]) -> None:
    serialized = json.dumps(provenance, sort_keys=True, allow_nan=False)
    if any(token in serialized for token in ("/Users/", "/tmp/", "/data/")):
        raise ValueError("compute provenance must use portable identifiers")


def _validate_portable_identifiers(provenance: Mapping[str, object]) -> None:
    for key in ("run_id", "host_id"):
        value = provenance.get(key)
        if not isinstance(value, str) or PORTABLE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError(f"{key} must be a portable identifier")


def _runtime_identifiers() -> dict[str, str]:
    completed = subprocess.run(
        ["uv", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "python_version": platform.python_version(),
        "uv_version": completed.stdout.strip(),
        "numpy_version": np.__version__,
        "os_identifier": platform.platform(),
    }


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
    path.write_text(_normalize_svg_ids(buffer.getvalue()), encoding="utf-8")


def _normalize_svg_ids(text: str) -> str:
    matches = tuple(dict.fromkeys(re.findall(r'\bid="([^"]+)"', text)))
    replacements = {old: f"goal012-{index:04d}" for index, old in enumerate(matches)}
    normalized = text
    for old, new in replacements.items():
        normalized = normalized.replace(f'id="{old}"', f'id="{new}"')
        normalized = normalized.replace(f'href="#{old}"', f'href="#{new}"')
        normalized = normalized.replace(f"url(#{old})", f"url(#{new})")
    return normalized


@contextmanager
def _svg_style() -> Iterator[None]:
    with mpl.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.hashsalt": "goal012-cross-truth-known-detection",
        }
    ):
        yield


def _validate_serialized_bundle(target: Path, relative_paths: set[str]) -> None:
    forbidden = (b"/Users/", b"/tmp/", b"/data/", b"NaN", b"Infinity")
    for relative in relative_paths:
        contents = (target / relative).read_bytes()
        if any(token in contents for token in forbidden):
            raise RuntimeError(f"nonportable or nonfinite content in {relative}")


__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "EXPECTED_FILES",
    "validate_pre_campaign_provenance",
    "write_review_bundle",
]
