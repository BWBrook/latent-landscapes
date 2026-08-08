"""Historical nine-cell Goal 012 campaign orchestration."""

from __future__ import annotations

import hashlib
import json
import os
import resource
import sys
import time
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, fields, is_dataclass
from math import isfinite
from typing import Any, cast

import numpy as np

from latent_landscapes.cross_truth import (
    BANK_VARIANT_NAMES,
    CALIBRATION_BLOCKS,
    CALIBRATION_RANK_ONE_BASED,
    DEFAULT_CONFIG,
    FROZEN_ETA_GRID,
    FROZEN_RHO_GRID,
    INTEGRATION_BANK_SIZE,
    MASTER_SEED,
    THREAD_LIMIT_NAMES,
    TRUTH_CELLS,
    VALIDATION_BLOCKS,
    CalibrationResult,
    CellBankSummary,
    CellResult,
    CrossTruthConfig,
    ObservationSignalSummary,
    RepresentativeProfile,
    SeedManifest,
    ValidationResult,
    run_truth_cell,
    seed_manifest_digest,
    smoke_config,
    spawn_seed_manifest,
)
from latent_landscapes.goal004.observations import (
    SURVEY_TIMES,
)
from latent_landscapes.goal008 import benchmark as goal008
from latent_landscapes.goal011 import benchmark as goal011

SOURCE_IDENTITY = {
    "repository_commit": "2182172d207049105955c9f1acc0e1501096d920",
    "goal008_benchmark_blob": "399cf13020d1366e7ccd421b4260ffbe8ad2f955",
    "goal011_benchmark_blob": "ac7d9ba1ba43d622a545a3cacc119e24ab27d4c2",
    "goal011_likelihood_blob": "c3a3cd2683967aa3d975036bc83d39eaa4978c31",
    "goal004_observation_blob": "c97938ab640700a6584e84cc2ed8be164b582b3c",
    "goal004_likelihood_blob": "b427bdfd25e2747ca69e2272e1be2df93aa6f49e",
    "lockfile_blob": "56ac1fe55b4c1182e4f89448a95d1864745261dc",
}
ACCEPTED_GOAL011_REFERENCE = {
    "seed_manifest_sha256": "dc6e5135b61bcdebd8b85726c131af29b64e2d69ef6358110e24677d0c0c1ceb",
    "calibration_sha256": "267d14085c652c0ea891befc91b38b52a169155d84ddae35cd43735df5b647ed",
    "validation_sha256": "0a90e1a35bb78b6d12afa8d483e90b27cf56a332002bb38e46f4c8b3128d6eca",
    "summary_sha256": "52e18b886565b3fa27fe7ad29ee2cfffd465c75315576e5745f69b6c06eadc70",
    "outcome": "advance_to_cross_truth_joint_imperfect_detection",
}


@dataclass(frozen=True, slots=True)
class CellExecutionTelemetry:
    truth_cell: str
    exit_status: int
    wall_time_seconds: float
    maximum_rss_bytes: int


@dataclass(frozen=True, slots=True)
class CampaignExecutionTelemetry:
    worker_count: int
    thread_limits: dict[str, str]
    campaign_exit_status: int
    cell_telemetry: tuple[CellExecutionTelemetry, ...]


@dataclass(frozen=True, slots=True)
class CentralReconciliation:
    truth_cell: str
    source_commit: str
    goal011_outcome: str
    production_reference_checked: bool
    production_reference_match: bool | None
    checks: dict[str, bool]
    observed_hashes: dict[str, str]
    expected_hashes: dict[str, str]


@dataclass(frozen=True, slots=True)
class Goal012Result:
    config: CrossTruthConfig
    seed_manifest: SeedManifest
    calibration_results: tuple[CalibrationResult, ...]
    validation_results: tuple[ValidationResult, ...]
    observation_signal_summary: tuple[ObservationSignalSummary, ...]
    representative_profiles: tuple[RepresentativeProfile, ...]
    truth_cell_summaries: tuple[CellBankSummary, ...]
    cell_invariants: dict[str, dict[str, bool]]
    central_reconciliation: CentralReconciliation
    execution_telemetry: CampaignExecutionTelemetry
    invariants: dict[str, bool]
    outcome: str


def classify_overall(
    invariants: Mapping[str, bool],
    cell_bank_classes: Mapping[str, Mapping[str, str]],
) -> str:
    """Apply implementation, bank-stability, then worst-full-cell precedence."""
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if set(cell_bank_classes) != {cell.cell_id for cell in TRUTH_CELLS}:
        return "implementation_blocked"
    if any(
        tuple(banks) != BANK_VARIANT_NAMES or len(set(banks.values())) != 1
        for banks in cell_bank_classes.values()
    ):
        return "likelihood_approximation_unstable"
    full_classes = {banks["full"] for banks in cell_bank_classes.values()}
    precedence = (
        ("cell_candidate_domain_unclosed", "cross_truth_candidate_domain_unclosed"),
        ("cell_design_limited", "cross_truth_design_limited"),
        (
            "cell_local_calibration_not_ready",
            "cross_truth_local_calibration_not_ready",
        ),
        ("cell_recovery_imprecise", "cross_truth_recovery_imprecise"),
        ("cell_neutral_better", "cross_truth_neutral_better"),
        ("cell_mechanism_inconclusive", "cross_truth_mechanism_inconclusive"),
    )
    for cell_class, outcome in precedence:
        if cell_class in full_classes:
            return outcome
    if full_classes == {"cell_recoverable"}:
        return "cross_truth_joint_known_detection_recoverable"
    return "implementation_blocked"


def run_campaign(
    config: CrossTruthConfig = DEFAULT_CONFIG,
    *,
    workers: int = 1,
) -> Goal012Result:
    """Run nine cell tasks and aggregate in frozen row-major order."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    _validate_production_runtime(config, workers)
    tasks = tuple((cell, config) for cell in config.resolved_truth_cells)
    if workers == 1:
        task_outputs = tuple(_run_truth_cell_task(task) for task in tasks)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            task_outputs = tuple(executor.map(_run_truth_cell_task, tasks))
    cell_results = tuple(output[0] for output in task_outputs)
    cell_telemetry = tuple(output[1] for output in task_outputs)
    telemetry = CampaignExecutionTelemetry(
        worker_count=workers,
        thread_limits=_current_thread_limits(),
        campaign_exit_status=0,
        cell_telemetry=cell_telemetry,
    )
    manifest = spawn_seed_manifest(config)
    calibration = tuple(row for result in cell_results for row in result.calibration_results)
    validation = tuple(row for result in cell_results for row in result.validation_results)
    signals = tuple(row for result in cell_results for row in result.observation_signal_summary)
    representatives = tuple(
        row for result in cell_results for row in result.representative_profiles
    )
    summaries = tuple(row for result in cell_results for row in result.summaries)
    central = _central_reconciliation(
        config,
        manifest,
        calibration,
        validation,
        summaries,
    )
    expected_seed_digest = seed_manifest_digest(manifest)
    cell_invariants = {
        result.truth_cell.cell_id: dict(result.invariants) for result in cell_results
    }
    streams = manifest.stream_records
    invariants = {
        "production_contract": not config.is_production
        or (
            config.master_seed == MASTER_SEED
            and config.bank_size == INTEGRATION_BANK_SIZE
            and config.calibration_blocks == CALIBRATION_BLOCKS
            and config.validation_blocks == VALIDATION_BLOCKS
            and config.calibration_rank_one_based == CALIBRATION_RANK_ONE_BASED
            and config.rhos == FROZEN_RHO_GRID
            and config.etas == FROZEN_ETA_GRID
            and config.truth_cells == TRUTH_CELLS
        ),
        "seven_phase_root_contract": all(
            record.spawn_key[0] == root_index
            for root_index, records in (
                (0, manifest.integration_bank),
                (1, tuple(row.process for row in manifest.calibration)),
                (2, tuple(row.process for row in manifest.validation)),
                (
                    3,
                    tuple(row.detection_for("cell-04") for row in manifest.calibration),
                ),
                (
                    4,
                    tuple(row.detection_for("cell-04") for row in manifest.validation),
                ),
                (
                    5,
                    tuple(
                        item.detection
                        for row in manifest.calibration
                        for item in row.cell_detection
                        if item.truth_cell != "cell-04"
                    ),
                ),
                (
                    6,
                    tuple(
                        item.detection
                        for row in manifest.validation
                        for item in row.cell_detection
                        if item.truth_cell != "cell-04"
                    ),
                ),
            )
            for record in records
        ),
        "goal011_first_five_identity": _goal011_seed_identity(config, manifest),
        "stream_uniqueness": len({(row.entropy, row.spawn_key) for row in streams}) == len(streams)
        and len({row.state_words for row in streams}) == len(streams),
        "cell_result_order": tuple(result.truth_cell for result in cell_results)
        == config.resolved_truth_cells,
        "cell_invariants": all(all(result.invariants.values()) for result in cell_results),
        "schedule_independent_seeds": all(
            result.seed_manifest_digest == expected_seed_digest for result in cell_results
        ),
        "complete_calibration_campaign": len(calibration)
        == 9 * len(BANK_VARIANT_NAMES) * config.calibration_blocks,
        "complete_validation_campaign": len(validation)
        == 9 * len(BANK_VARIANT_NAMES) * config.validation_blocks,
        "complete_summary_surface": len(summaries) == 9 * len(BANK_VARIANT_NAMES),
        "complete_representative_surface": len(representatives) == 9 * len(BANK_VARIANT_NAMES),
        "complete_signal_surface": len(signals) == 9 * len(SURVEY_TIMES),
        "stable_row_identity": len(
            {(row.phase, row.block_index, row.truth_cell, row.bank_variant) for row in calibration}
        )
        == len(calibration)
        and len(
            {(row.phase, row.block_index, row.truth_cell, row.bank_variant) for row in validation}
        )
        == len(validation),
        "cell_processes_succeeded": len(cell_telemetry) == 9
        and all(row.exit_status == 0 for row in cell_telemetry),
        "central_reconciliation": all(central.checks.values())
        and (
            not central.production_reference_checked or central.production_reference_match is True
        ),
    }
    classes = {
        cell.cell_id: {
            row.bank_variant: row.expanded_class
            for row in summaries
            if row.truth_cell == cell.cell_id
        }
        for cell in config.resolved_truth_cells
    }
    outcome = classify_overall(invariants, classes)
    return Goal012Result(
        config=config,
        seed_manifest=manifest,
        calibration_results=calibration,
        validation_results=validation,
        observation_signal_summary=signals,
        representative_profiles=representatives,
        truth_cell_summaries=summaries,
        cell_invariants=cell_invariants,
        central_reconciliation=central,
        execution_telemetry=telemetry,
        invariants=invariants,
        outcome=outcome,
    )


def campaign_digest(result: Goal012Result) -> str:
    """Hash scientific content while excluding execution telemetry."""
    content = {
        field.name: getattr(result, field.name)
        for field in fields(result)
        if field.name != "execution_telemetry"
    }
    return _projection_digest(content)


def goal011_calibration_projection(
    rows: tuple[CalibrationResult, ...],
) -> tuple[goal011.CalibrationResult, ...]:
    """Project Goal 012 central rows onto the accepted Goal 011 contract."""
    return tuple(
        goal011.CalibrationResult(
            dataset_index=row.block_index,
            bank_variant=row.bank_variant,
            record_count=row.record_count,
            no_false_positives=row.no_false_positives,
            truth_eta_index=row.truth_eta_index,
            truth_rho_index=row.truth_rho_index,
            expanded_lr_at_truth=row.expanded_lr_at_truth,
            old_domain_lr_at_truth=row.old_domain_lr_at_truth,
            expanded_truth_log_likelihood=row.expanded_truth_log_likelihood,
            old_domain_truth_log_likelihood=row.old_domain_truth_log_likelihood,
            expanded_maximum_log_likelihood=row.expanded_maximum_log_likelihood,
            old_domain_maximum_log_likelihood=row.old_domain_maximum_log_likelihood,
            expanded_mle_cells=row.expanded_mle_cells,
            old_domain_mle_cells=row.old_domain_mle_cells,
        )
        for row in rows
    )


def goal011_validation_projection(
    rows: tuple[ValidationResult, ...],
) -> tuple[goal011.ValidationResult, ...]:
    """Project Goal 012 central validation rows onto Goal 011."""
    return tuple(
        goal011.ValidationResult(
            dataset_index=row.block_index,
            bank_variant=row.bank_variant,
            record_count=row.record_count,
            training_record_count=row.training_record_count,
            holdout_record_count=row.holdout_record_count,
            split_isolated=row.split_isolated,
            no_false_positives=row.no_false_positives,
            expanded_lr_at_truth=row.expanded_lr_at_truth,
            old_domain_lr_at_truth=row.old_domain_lr_at_truth,
            expanded_truth_included=row.expanded_truth_included,
            expanded_support_cell_count=row.expanded_support_cell_count,
            expanded_support_component_count=row.expanded_support_component_count,
            expanded_support_boundary_contact=row.expanded_support_boundary_contact,
            expanded_support_boundary_faces=row.expanded_support_boundary_faces,
            expanded_projected_log_rho_width=row.expanded_projected_log_rho_width,
            expanded_projected_eta_width=row.expanded_projected_eta_width,
            expanded_support_indices=row.expanded_support_indices,
            expanded_support_correlation=row.expanded_support_correlation,
            expanded_support_correlation_reason=row.expanded_support_correlation_reason,
            expanded_mle_indices=row.expanded_mle_indices,
            expanded_mle_cells=row.expanded_mle_cells,
            expanded_minimum_absolute_log_rho_error=(row.expanded_minimum_absolute_log_rho_error),
            expanded_minimum_absolute_eta_error=row.expanded_minimum_absolute_eta_error,
            expanded_training_mle_cells=row.expanded_training_mle_cells,
            expanded_support_uses_appended_eta=row.expanded_support_uses_appended_eta,
            expanded_mle_uses_appended_eta=row.expanded_mle_uses_appended_eta,
            expanded_stochastic_log_score_minimum=(row.expanded_stochastic_log_score_minimum),
            expanded_stochastic_log_score_maximum=(row.expanded_stochastic_log_score_maximum),
            expanded_stochastic_brier_minimum=row.expanded_stochastic_brier_minimum,
            expanded_stochastic_brier_maximum=row.expanded_stochastic_brier_maximum,
            expanded_stochastic_probability_minimum=(row.expanded_stochastic_probability_minimum),
            expanded_stochastic_probability_maximum=(row.expanded_stochastic_probability_maximum),
            neutral_log_score=row.neutral_log_score,
            neutral_brier_score=row.neutral_brier_score,
            neutral_probability_minimum=row.neutral_probability_minimum,
            neutral_probability_maximum=row.neutral_probability_maximum,
            expanded_paired_brier_difference=row.expanded_paired_brier_difference,
            old_domain_truth_included=row.old_domain_truth_included,
            old_domain_support_cell_count=row.old_domain_support_cell_count,
            old_domain_support_component_count=row.old_domain_support_component_count,
            old_domain_support_boundary_contact=row.old_domain_support_boundary_contact,
            old_domain_support_boundary_faces=row.old_domain_support_boundary_faces,
            old_domain_projected_log_rho_width=row.old_domain_projected_log_rho_width,
            old_domain_projected_eta_width=row.old_domain_projected_eta_width,
            old_domain_support_indices=row.old_domain_support_indices,
            old_domain_mle_cells=row.old_domain_mle_cells,
            old_domain_minimum_absolute_log_rho_error=(
                row.old_domain_minimum_absolute_log_rho_error
            ),
            old_domain_minimum_absolute_eta_error=row.old_domain_minimum_absolute_eta_error,
            old_domain_training_mle_cells=row.old_domain_training_mle_cells,
            old_domain_paired_brier_difference=row.old_domain_paired_brier_difference,
        )
        for row in rows
    )


def goal011_summary_projection(
    rows: tuple[CellBankSummary, ...],
) -> tuple[goal011.BankSummary, ...]:
    """Project Goal 012 central summaries onto Goal 011's meanings."""
    return tuple(
        goal011.BankSummary(
            bank_variant=row.bank_variant,
            draw_count=row.draw_count,
            cutoff=row.cutoff,
            old_domain_cutoff=row.old_domain_cutoff,
            expanded_coverage_success_count=row.expanded_coverage_success_count,
            expanded_calibrated_coverage=row.expanded_calibrated_coverage,
            expanded_topology_success_count=row.expanded_topology_success_count,
            expanded_boundary_contact_count=row.expanded_boundary_contact_count,
            expanded_median_minimum_absolute_log_rho_error=(
                row.expanded_median_minimum_absolute_log_rho_error
            ),
            expanded_median_minimum_absolute_eta_error=(
                row.expanded_median_minimum_absolute_eta_error
            ),
            expanded_median_projected_log_rho_width=(row.expanded_median_projected_log_rho_width),
            expanded_median_projected_eta_width=row.expanded_median_projected_eta_width,
            expanded_paired_brier_interval=row.expanded_paired_brier_interval,
            expanded_mean_stochastic_brier_worst_mle=(row.expanded_mean_stochastic_brier_worst_mle),
            mean_neutral_brier=row.mean_neutral_brier,
            expanded_downstream_class=_goal011_class(row.expanded_class),
            old_domain_coverage_success_count=row.old_domain_coverage_success_count,
            old_domain_calibrated_coverage=row.old_domain_calibrated_coverage,
            old_domain_topology_success_count=row.old_domain_topology_success_count,
            old_domain_boundary_contact_count=row.old_domain_boundary_contact_count,
            old_domain_median_minimum_absolute_log_rho_error=(
                row.old_domain_median_minimum_absolute_log_rho_error
            ),
            old_domain_median_minimum_absolute_eta_error=(
                row.old_domain_median_minimum_absolute_eta_error
            ),
            old_domain_median_projected_log_rho_width=(
                row.old_domain_median_projected_log_rho_width
            ),
            old_domain_median_projected_eta_width=row.old_domain_median_projected_eta_width,
            old_domain_paired_brier_interval=row.old_domain_paired_brier_interval,
            old_domain_downstream_class=_goal011_class(row.old_domain_class),
        )
        for row in rows
    )


def _central_reconciliation(
    config: CrossTruthConfig,
    manifest: SeedManifest,
    calibration: tuple[CalibrationResult, ...],
    validation: tuple[ValidationResult, ...],
    summaries: tuple[CellBankSummary, ...],
) -> CentralReconciliation:
    central_calibration = tuple(row for row in calibration if row.truth_cell == "cell-04")
    central_validation = tuple(row for row in validation if row.truth_cell == "cell-04")
    central_summaries = tuple(row for row in summaries if row.truth_cell == "cell-04")
    projected_calibration = goal011_calibration_projection(central_calibration)
    projected_validation = goal011_validation_projection(central_validation)
    projected_summaries = goal011_summary_projection(central_summaries)
    central_manifest = _goal011_manifest_projection(manifest)
    goal011_outcome = goal011.classify_outcome(
        invariants={"central_projection": True},
        downstream_classes=tuple(row.expanded_downstream_class for row in projected_summaries),
    )
    observed_hashes = {
        "seed_manifest_sha256": _projection_digest(_goal011_seed_rows(central_manifest)),
        "calibration_sha256": _projection_digest(_goal011_calibration_rows(projected_calibration)),
        "validation_sha256": _projection_digest(_goal011_validation_rows(projected_validation)),
        "summary_sha256": _projection_digest(_goal011_summary_rows(projected_summaries)),
    }
    expected_hashes = {
        key: str(value)
        for key, value in ACCEPTED_GOAL011_REFERENCE.items()
        if key.endswith("_sha256")
    }
    checks = {
        "seed_identity": _goal011_seed_identity(config, manifest),
        "calibration_projection_complete": len(projected_calibration)
        == len(BANK_VARIANT_NAMES) * config.calibration_blocks,
        "validation_projection_complete": len(projected_validation)
        == len(BANK_VARIANT_NAMES) * config.validation_blocks,
        "summary_projection_complete": len(projected_summaries) == len(BANK_VARIANT_NAMES),
        "complete_visit_counts": all(row.record_count == 1920 for row in projected_calibration)
        and all(
            row.record_count == 1920
            and row.training_record_count == 1440
            and row.holdout_record_count == 480
            for row in projected_validation
        ),
        "truth_indices": all(
            row.truth_rho_index == config.rhos.index(1.0)
            and row.truth_eta_index == config.etas.index(1.0)
            for row in projected_calibration
        ),
        "downstream_meaning": goal011_outcome
        == (
            projected_summaries[0].expanded_downstream_class
            if len({row.expanded_downstream_class for row in projected_summaries}) == 1
            else "likelihood_approximation_unstable"
        ),
    }
    if config.is_production:
        checks["accepted_nine_decimal_projection"] = observed_hashes == expected_hashes
        checks["accepted_goal011_outcome"] = (
            goal011_outcome == ACCEPTED_GOAL011_REFERENCE["outcome"]
        )
        matched: bool | None = all(checks.values())
    else:
        matched = None
    return CentralReconciliation(
        truth_cell="cell-04",
        source_commit=SOURCE_IDENTITY["repository_commit"],
        goal011_outcome=goal011_outcome,
        production_reference_checked=config.is_production,
        production_reference_match=matched,
        checks=checks,
        observed_hashes=observed_hashes,
        expected_hashes=expected_hashes,
    )


def _goal011_seed_identity(config: CrossTruthConfig, manifest: SeedManifest) -> bool:
    reference = goal011.spawn_seed_manifest(config.goal011_config)
    return (
        manifest.integration_bank == reference.integration_bank
        and tuple(row.process for row in manifest.calibration)
        == tuple(row.process for row in reference.calibration)
        and tuple(row.process for row in manifest.validation)
        == tuple(row.process for row in reference.validation)
        and tuple(row.detection_for("cell-04") for row in manifest.calibration)
        == tuple(row.detection for row in reference.calibration)
        and tuple(row.detection_for("cell-04") for row in manifest.validation)
        == tuple(row.detection for row in reference.validation)
    )


def _goal011_manifest_projection(manifest: SeedManifest) -> goal011.SeedManifest:
    return goal011.SeedManifest(
        integration_bank=manifest.integration_bank,
        calibration=tuple(
            goal011.DatasetSeedRecord(
                phase=block.phase,
                index=block.index,
                process=block.process,
                detection=block.detection_for("cell-04"),
            )
            for block in manifest.calibration
        ),
        validation=tuple(
            goal011.DatasetSeedRecord(
                phase=block.phase,
                index=block.index,
                process=block.process,
                detection=block.detection_for("cell-04"),
            )
            for block in manifest.validation
        ),
    )


def _goal011_seed_rows(manifest: goal011.SeedManifest) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    groups = (
        (0, "integration_bank", manifest.integration_bank),
        (1, "calibration_process", tuple(row.process for row in manifest.calibration)),
        (2, "validation_process", tuple(row.process for row in manifest.validation)),
        (
            3,
            "calibration_detection",
            tuple(row.detection for row in manifest.calibration),
        ),
        (
            4,
            "validation_detection",
            tuple(row.detection for row in manifest.validation),
        ),
    )
    for root_index, phase_root, records in groups:
        rows.extend(
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
            for row in records
        )
    return rows


def _goal011_calibration_rows(
    rows: tuple[goal011.CalibrationResult, ...],
) -> list[dict[str, object]]:
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
        for row in rows
    ]


def _goal011_validation_rows(
    rows: tuple[goal011.ValidationResult, ...],
) -> list[dict[str, object]]:
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
            "expanded_support_uses_appended_eta": (row.expanded_support_uses_appended_eta),
            "expanded_mle_uses_appended_eta": row.expanded_mle_uses_appended_eta,
            "expanded_paired_brier_difference": row.expanded_paired_brier_difference,
            "old_domain_truth_included": row.old_domain_truth_included,
            "old_domain_support_cell_count": row.old_domain_support_cell_count,
            "old_domain_support_component_count": row.old_domain_support_component_count,
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
        for row in rows
    ]


def _goal011_summary_rows(
    rows: tuple[goal011.BankSummary, ...],
) -> list[dict[str, object]]:
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
        for row in rows
    ]


def _goal011_class(cell_class: str) -> str:
    return {
        "cell_candidate_domain_unclosed": "joint_imperfect_detection_design_limited",
        "cell_design_limited": "joint_imperfect_detection_design_limited",
        "cell_local_calibration_not_ready": (
            "joint_imperfect_detection_local_calibration_not_ready"
        ),
        "cell_recovery_imprecise": "joint_imperfect_detection_recovery_imprecise",
        "cell_neutral_better": "joint_imperfect_detection_neutral_better",
        "cell_recoverable": "advance_to_cross_truth_joint_imperfect_detection",
        "cell_mechanism_inconclusive": ("joint_imperfect_detection_mechanism_inconclusive"),
    }[cell_class]


def _run_truth_cell_task(
    task: tuple[goal008.TruthCell, CrossTruthConfig],
) -> tuple[CellResult, CellExecutionTelemetry]:
    cell, config = task
    started = time.perf_counter()
    result = run_truth_cell(cell, config)
    return result, CellExecutionTelemetry(
        truth_cell=cell.cell_id,
        exit_status=0,
        wall_time_seconds=time.perf_counter() - started,
        maximum_rss_bytes=_maximum_rss_bytes(),
    )


def _projection_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonical_value(value),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _canonical_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        instance = cast(Any, value)
        return {
            field.name: _canonical_value(getattr(instance, field.name))
            for field in fields(instance)
        }
    if isinstance(value, np.ndarray):
        return _canonical_value(value.tolist())
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("scientific digest rejects nonfinite values")
        return 0.0 if value == 0.0 else round(value, 9)
    return value


def _compact_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), allow_nan=False)


def _current_thread_limits() -> dict[str, str]:
    return {name: os.environ.get(name, "") for name in THREAD_LIMIT_NAMES}


def _validate_production_runtime(config: CrossTruthConfig, workers: int) -> None:
    if not config.is_production:
        return
    if workers != 9:
        raise ValueError("production campaign requires exactly 9 workers")
    if _current_thread_limits() != {name: "1" for name in THREAD_LIMIT_NAMES}:
        raise ValueError("production campaign requires all four thread limits set to 1")


def _maximum_rss_bytes() -> int:
    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    multiplier = 1 if sys.platform == "darwin" else 1024
    return max(1, int(maximum * multiplier))


__all__ = [
    "ACCEPTED_GOAL011_REFERENCE",
    "DEFAULT_CONFIG",
    "SOURCE_IDENTITY",
    "CampaignExecutionTelemetry",
    "CellExecutionTelemetry",
    "CentralReconciliation",
    "Goal012Result",
    "campaign_digest",
    "classify_overall",
    "goal011_calibration_projection",
    "goal011_summary_projection",
    "goal011_validation_projection",
    "run_campaign",
    "smoke_config",
]
