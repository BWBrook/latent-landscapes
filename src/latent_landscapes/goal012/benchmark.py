"""Cross-truth joint recovery under known imperfect detection."""

from __future__ import annotations

import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, fields, is_dataclass, replace
from math import ceil, isfinite
from pathlib import Path
from statistics import fmean, median
from typing import Any, cast

import numpy as np

from latent_landscapes.goal001.observations import Observation
from latent_landscapes.goal002.baseline import (
    fit_time_stratified_baseline,
    score_time_stratified_baseline,
)
from latent_landscapes.goal002.calibration import (
    CutoffResult,
    EstimateInterval,
    normal_mean_interval,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal003.spread import StochasticSpreadTruth
from latent_landscapes.goal004 import benchmark as goal004
from latent_landscapes.goal004.likelihood import (
    PredictiveScore,
    record_detection_probabilities,
    score_predictions,
    site_history_probabilities,
)
from latent_landscapes.goal004.observations import (
    DETECTION_PROBABILITY,
    SURVEY_TIMES,
)
from latent_landscapes.goal006.spread import ContrastSpreadTruth
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal007.likelihood import (
    CATEGORY_COUNT,
    JointGridProfile,
    JointProfileSummary,
    summarize_joint_profile,
)
from latent_landscapes.goal008 import benchmark as goal008
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal011.likelihood import (
    OLD_DOMAIN_MAXIMUM_ETA,
    joint_profile_from_history_probabilities,
    project_eta_domain,
)

MASTER_SEED = goal011.MASTER_SEED
INTEGRATION_BANK_SIZE = goal011.INTEGRATION_BANK_SIZE
CALIBRATION_BLOCKS = goal011.CALIBRATION_REPLICATES
VALIDATION_BLOCKS = goal011.VALIDATION_REPLICATES
CALIBRATION_RANK_ONE_BASED = goal011.CALIBRATION_RANK_ONE_BASED
BANK_VARIANT_NAMES = goal011.BANK_VARIANT_NAMES
FROZEN_RHO_GRID = goal011.FROZEN_RHO_GRID
FROZEN_ETA_GRID = goal011.FROZEN_ETA_GRID
OLD_ETA_GRID = goal011.OLD_ETA_GRID
TRUTH_CELLS = goal008.TRUTH_CELLS
STATE_WORD_COUNT = goal007.STATE_WORD_COUNT
THREAD_LIMIT_NAMES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)

SOURCE_IDENTITY = {
    "repository_commit": "2182172d207049105955c9f1acc0e1501096d920",
    "goal008_benchmark_blob": "399cf13020d1366e7ccd421b4260ffbe8ad2f955",
    "goal011_benchmark_blob": "ac7d9ba1ba43d622a545a3cacc119e24ab27d4c2",
    "goal011_likelihood_blob": "c3a3cd2683967aa3d975036bc83d39eaa4978c31",
    "goal004_observation_blob": "c97938ab640700a6584e84cc2ed8be164b582b3c",
    "goal004_likelihood_blob": "b427bdfd25e2747ca69e2272e1be2df93aa6f49e",
    "lockfile_blob": "56ac1fe55b4c1182e4f89448a95d1864745261dc",
}
PINNED_SOURCE_PATHS = {
    "goal008_benchmark_blob": "src/latent_landscapes/goal008/benchmark.py",
    "goal011_benchmark_blob": "src/latent_landscapes/goal011/benchmark.py",
    "goal011_likelihood_blob": "src/latent_landscapes/goal011/likelihood.py",
    "goal004_observation_blob": "src/latent_landscapes/goal004/observations.py",
    "goal004_likelihood_blob": "src/latent_landscapes/goal004/likelihood.py",
    "lockfile_blob": "uv.lock",
}
ACCEPTED_GOAL011_REFERENCE = {
    "seed_manifest_sha256": "dc6e5135b61bcdebd8b85726c131af29b64e2d69ef6358110e24677d0c0c1ceb",
    "calibration_sha256": "267d14085c652c0ea891befc91b38b52a169155d84ddae35cd43735df5b647ed",
    "validation_sha256": "0a90e1a35bb78b6d12afa8d483e90b27cf56a332002bb38e46f4c8b3128d6eca",
    "summary_sha256": "52e18b886565b3fa27fe7ad29ee2cfffd465c75315576e5745f69b6c06eadc70",
    "outcome": "advance_to_cross_truth_joint_imperfect_detection",
}


@dataclass(frozen=True, slots=True)
class Goal012Config:
    master_seed: int = MASTER_SEED
    bank_size: int = INTEGRATION_BANK_SIZE
    calibration_blocks: int = CALIBRATION_BLOCKS
    validation_blocks: int = VALIDATION_BLOCKS
    calibration_rank_one_based: int = CALIBRATION_RANK_ONE_BASED
    rhos: tuple[float, ...] = FROZEN_RHO_GRID
    etas: tuple[float, ...] = FROZEN_ETA_GRID
    truth_cells: tuple[goal008.TruthCell, ...] = TRUTH_CELLS

    def __post_init__(self) -> None:
        if self.bank_size < 2 or self.bank_size % 2:
            raise ValueError("integration bank size must be positive and even")
        if self.calibration_blocks <= 0 or self.validation_blocks <= 0:
            raise ValueError("process-block counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_blocks:
            raise ValueError("calibration rank must lie within the calibration ensemble")
        rho_values = np.asarray(self.rhos, dtype=np.float64)
        eta_values = np.asarray(self.etas, dtype=np.float64)
        if (
            rho_values.ndim != 1
            or len(rho_values) == 0
            or not np.isfinite(rho_values).all()
            or (rho_values <= 0.0).any()
            or (np.diff(rho_values) <= 0.0).any()
        ):
            raise ValueError("rhos must be finite, positive, and strictly increasing")
        if (
            eta_values.ndim != 1
            or len(eta_values) == 0
            or not np.isfinite(eta_values).all()
            or (eta_values < 0.0).any()
            or (np.diff(eta_values) <= 0.0).any()
        ):
            raise ValueError("etas must be finite, nonnegative, and strictly increasing")
        if tuple(value for value in self.etas if value <= OLD_DOMAIN_MAXIMUM_ETA) != tuple(
            value for value in self.etas if value <= 2.0
        ):
            raise ValueError("old eta projection must be a leading domain ending at 2")
        cell_ids = tuple(cell.cell_id for cell in self.truth_cells)
        coordinates = tuple((cell.rho, cell.eta) for cell in self.truth_cells)
        if len(self.truth_cells) != 9 or len(set(cell_ids)) != 9 or len(set(coordinates)) != 9:
            raise ValueError("Goal 012 requires nine unique truth cells")
        if cell_ids != tuple(f"cell-{index:02d}" for index in range(9)):
            raise ValueError("truth cells must use the frozen row-major order")
        if any(cell.rho not in self.rhos or cell.eta not in self.etas for cell in self.truth_cells):
            raise ValueError("every truth coordinate must lie on the candidate grid")

    @property
    def half_bank_size(self) -> int:
        return self.bank_size // 2

    @property
    def old_etas(self) -> tuple[float, ...]:
        return tuple(value for value in self.etas if value <= OLD_DOMAIN_MAXIMUM_ETA)

    @property
    def resolved_truth_cells(self) -> tuple[goal008.TruthCell, ...]:
        return tuple(
            replace(
                cell,
                rho_index=self.rhos.index(cell.rho),
                eta_index=self.etas.index(cell.eta),
            )
            for cell in self.truth_cells
        )

    @property
    def goal011_config(self) -> goal011.Goal011Config:
        return goal011.Goal011Config(
            master_seed=self.master_seed,
            bank_size=self.bank_size,
            calibration_replicates=self.calibration_blocks,
            validation_replicates=self.validation_blocks,
            calibration_rank_one_based=self.calibration_rank_one_based,
            rhos=self.rhos,
            etas=self.etas,
        )

    @property
    def is_production(self) -> bool:
        return self == DEFAULT_CONFIG


DEFAULT_CONFIG = Goal012Config()


def smoke_config() -> Goal012Config:
    """Return the explicit reduced smoke with the full candidate grid."""
    return Goal012Config(
        bank_size=2,
        calibration_blocks=2,
        validation_blocks=2,
        calibration_rank_one_based=2,
    )


@dataclass(frozen=True, slots=True)
class CellDetectionSeed:
    truth_cell: str
    detection: goal004.StreamSeedRecord


@dataclass(frozen=True, slots=True)
class BlockSeedRecord:
    phase: str
    index: int
    process: goal007.StreamSeedRecord
    cell_detection: tuple[CellDetectionSeed, ...]

    def detection_for(self, truth_cell: str) -> goal004.StreamSeedRecord:
        matches = tuple(
            item.detection for item in self.cell_detection if item.truth_cell == truth_cell
        )
        if len(matches) != 1:
            raise ValueError("truth cell must have exactly one detection stream per block")
        return matches[0]


SeedRecord = goal007.StreamSeedRecord | goal004.StreamSeedRecord


@dataclass(frozen=True, slots=True)
class SeedManifest:
    integration_bank: tuple[goal007.StreamSeedRecord, ...]
    calibration: tuple[BlockSeedRecord, ...]
    validation: tuple[BlockSeedRecord, ...]

    @property
    def stream_records(self) -> tuple[SeedRecord, ...]:
        outer: list[SeedRecord] = []
        for block in (*self.calibration, *self.validation):
            outer.append(block.process)
            outer.extend(item.detection for item in block.cell_detection)
        return (*self.integration_bank, *outer)


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    phase: str
    block_index: int
    pairing_group: str
    truth_cell: str
    truth_rho: float
    truth_eta: float
    truth_rho_index: int
    truth_eta_index: int
    bank_variant: str
    cutoff_source_cell: str
    cutoff_source_rho: float
    cutoff_source_eta: float
    record_count: int
    no_false_positives: bool
    expanded_lr_at_truth: float
    old_domain_lr_at_truth: float
    expanded_truth_log_likelihood: float
    old_domain_truth_log_likelihood: float
    expanded_maximum_log_likelihood: float
    old_domain_maximum_log_likelihood: float
    expanded_mle_cells: tuple[tuple[float, float], ...]
    old_domain_mle_cells: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    phase: str
    block_index: int
    pairing_group: str
    truth_cell: str
    truth_rho: float
    truth_eta: float
    truth_rho_index: int
    truth_eta_index: int
    bank_variant: str
    cutoff_source_cell: str
    cutoff_source_rho: float
    cutoff_source_eta: float
    record_count: int
    training_record_count: int
    holdout_record_count: int
    split_isolated: bool
    no_false_positives: bool
    expanded_lr_at_truth: float
    old_domain_lr_at_truth: float
    expanded_truth_included: bool
    expanded_support_cell_count: int
    expanded_support_component_count: int
    expanded_support_boundary_contact: bool
    expanded_support_boundary_faces: tuple[str, ...]
    expanded_projected_log_rho_width: float
    expanded_projected_eta_width: float
    expanded_support_indices: tuple[tuple[int, int], ...]
    expanded_support_correlation: float | None
    expanded_support_correlation_reason: str | None
    expanded_mle_indices: tuple[tuple[int, int], ...]
    expanded_mle_cells: tuple[tuple[float, float], ...]
    expanded_minimum_absolute_log_rho_error: float
    expanded_minimum_absolute_eta_error: float
    expanded_training_mle_cells: tuple[tuple[float, float], ...]
    expanded_support_uses_appended_eta: bool
    expanded_mle_uses_appended_eta: bool
    expanded_stochastic_log_score_minimum: float
    expanded_stochastic_log_score_maximum: float
    expanded_stochastic_brier_minimum: float
    expanded_stochastic_brier_maximum: float
    expanded_stochastic_probability_minimum: float
    expanded_stochastic_probability_maximum: float
    neutral_log_score: float
    neutral_brier_score: float
    neutral_probability_minimum: float
    neutral_probability_maximum: float
    expanded_paired_brier_difference: float
    old_domain_truth_included: bool
    old_domain_support_cell_count: int
    old_domain_support_component_count: int
    old_domain_support_boundary_contact: bool
    old_domain_support_boundary_faces: tuple[str, ...]
    old_domain_projected_log_rho_width: float
    old_domain_projected_eta_width: float
    old_domain_support_indices: tuple[tuple[int, int], ...]
    old_domain_mle_cells: tuple[tuple[float, float], ...]
    old_domain_minimum_absolute_log_rho_error: float
    old_domain_minimum_absolute_eta_error: float
    old_domain_training_mle_cells: tuple[tuple[float, float], ...]
    old_domain_paired_brier_difference: float


@dataclass(frozen=True, slots=True)
class ObservationSignalSummary:
    truth_cell: str
    truth_rho: float
    truth_eta: float
    survey_time: int
    occupied_fraction_mean: float
    occupied_fraction_lower: float
    occupied_fraction_upper: float
    detected_fraction_mean: float
    detected_fraction_lower: float
    detected_fraction_upper: float


@dataclass(frozen=True, slots=True)
class RepresentativeProfile:
    truth_cell: str
    truth_rho: float
    truth_eta: float
    truth_rho_index: int
    truth_eta_index: int
    cutoff_source_cell: str
    cutoff_source_rho: float
    cutoff_source_eta: float
    block_index: int
    bank_variant: str
    expanded_cutoff: float
    old_domain_cutoff: float
    expanded_profile: JointGridProfile
    old_domain_profile: JointGridProfile
    expanded_summary: JointProfileSummary
    old_domain_summary: JointProfileSummary


@dataclass(frozen=True, slots=True)
class CellDecision:
    candidate_domain_unclosed: bool
    design_limited: bool
    local_calibration_not_ready: bool
    recovery_imprecise: bool
    neutral_better: bool
    recoverable: bool
    mechanism_inconclusive: bool
    outcome: str


@dataclass(frozen=True, slots=True)
class CellBankSummary:
    truth_cell: str
    truth_rho: float
    truth_eta: float
    truth_rho_index: int
    truth_eta_index: int
    bank_variant: str
    cutoff_source_cell: str
    cutoff_source_rho: float
    cutoff_source_eta: float
    draw_count: int
    cutoff: CutoffResult
    old_domain_cutoff: CutoffResult
    expanded_coverage_success_count: int
    expanded_calibrated_coverage: EstimateInterval
    expanded_topology_success_count: int
    expanded_physical_topology_success_count: int
    expanded_boundary_contact_count: int
    artificial_face_contact_count: int
    rho_min_contact_count: int
    rho_max_contact_count: int
    eta_min_contact_count: int
    eta_max_contact_count: int
    expanded_median_minimum_absolute_log_rho_error: float
    expanded_median_minimum_absolute_eta_error: float
    expanded_median_projected_log_rho_width: float
    expanded_median_projected_eta_width: float
    expanded_median_support_cell_count: float
    expanded_mean_mle_set_size: float
    expanded_paired_brier_interval: EstimateInterval
    expanded_mean_stochastic_brier_worst_mle: float
    mean_neutral_brier: float
    finite_log_score_count: int
    expanded_candidate_domain_unclosed: bool
    expanded_design_limited: bool
    expanded_local_calibration_not_ready: bool
    expanded_recovery_imprecise: bool
    expanded_neutral_better: bool
    expanded_recoverable: bool
    expanded_mechanism_inconclusive: bool
    expanded_class: str
    old_domain_coverage_success_count: int
    old_domain_calibrated_coverage: EstimateInterval
    old_domain_topology_success_count: int
    old_domain_physical_topology_success_count: int
    old_domain_boundary_contact_count: int
    old_domain_artificial_face_contact_count: int
    old_domain_rho_min_contact_count: int
    old_domain_rho_max_contact_count: int
    old_domain_eta_min_contact_count: int
    old_domain_eta_max_contact_count: int
    old_domain_median_minimum_absolute_log_rho_error: float
    old_domain_median_minimum_absolute_eta_error: float
    old_domain_median_projected_log_rho_width: float
    old_domain_median_projected_eta_width: float
    old_domain_median_support_cell_count: float
    old_domain_mean_mle_set_size: float
    old_domain_paired_brier_interval: EstimateInterval
    old_domain_candidate_domain_unclosed: bool
    old_domain_design_limited: bool
    old_domain_local_calibration_not_ready: bool
    old_domain_recovery_imprecise: bool
    old_domain_neutral_better: bool
    old_domain_recoverable: bool
    old_domain_mechanism_inconclusive: bool
    old_domain_class: str


@dataclass(frozen=True, slots=True)
class CellResult:
    truth_cell: goal008.TruthCell
    calibration_results: tuple[CalibrationResult, ...]
    validation_results: tuple[ValidationResult, ...]
    observation_signal_summary: tuple[ObservationSignalSummary, ...]
    representative_profiles: tuple[RepresentativeProfile, ...]
    summaries: tuple[CellBankSummary, ...]
    seed_manifest_digest: str
    invariants: dict[str, bool]


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
    config: Goal012Config
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


@dataclass(frozen=True, slots=True)
class _Cutoffs:
    expanded: dict[str, CutoffResult]
    old_domain: dict[str, CutoffResult]


@dataclass(frozen=True, slots=True)
class _DomainAggregate:
    coverage_count: int
    coverage: EstimateInterval
    topology_count: int
    physical_topology_count: int
    boundary_count: int
    artificial_face_count: int
    rho_min_count: int
    rho_max_count: int
    eta_min_count: int
    eta_max_count: int
    rho_error: float
    eta_error: float
    rho_width: float
    eta_width: float
    support_cells: float
    mle_size: float
    brier: EstimateInterval


def spawn_seed_manifest(config: Goal012Config = DEFAULT_CONFIG) -> SeedManifest:
    """Spawn seven roots while preserving Goal 011's first five exactly."""
    roots = np.random.SeedSequence(config.master_seed).spawn(7)
    integration = tuple(
        _process_record("integration_bank", index, "paired_eta_process", child)
        for index, child in enumerate(roots[0].spawn(config.bank_size))
    )
    calibration_process = tuple(
        _process_record("calibration", index, "central_truth_process", child)
        for index, child in enumerate(roots[1].spawn(config.calibration_blocks))
    )
    validation_process = tuple(
        _process_record("validation", index, "central_truth_process", child)
        for index, child in enumerate(roots[2].spawn(config.validation_blocks))
    )
    calibration_central = tuple(
        _detection_record("calibration", index, child)
        for index, child in enumerate(roots[3].spawn(config.calibration_blocks))
    )
    validation_central = tuple(
        _detection_record("validation", index, child)
        for index, child in enumerate(roots[4].spawn(config.validation_blocks))
    )
    calibration_noncentral = _noncentral_detection_blocks(
        roots[5],
        phase="calibration",
        count=config.calibration_blocks,
    )
    validation_noncentral = _noncentral_detection_blocks(
        roots[6],
        phase="validation",
        count=config.validation_blocks,
    )
    return SeedManifest(
        integration_bank=integration,
        calibration=tuple(
            _block_seed_record(
                phase="calibration",
                index=index,
                process=calibration_process[index],
                central=calibration_central[index],
                noncentral=calibration_noncentral[index],
            )
            for index in range(config.calibration_blocks)
        ),
        validation=tuple(
            _block_seed_record(
                phase="validation",
                index=index,
                process=validation_process[index],
                central=validation_central[index],
                noncentral=validation_noncentral[index],
            )
            for index in range(config.validation_blocks)
        ),
    )


def build_fixed_inputs() -> goal007.FixedInputs:
    """Reuse Goal 011's frozen known-detection spatial inputs."""
    return goal011.build_fixed_inputs()


def generate_truth_block(
    fixed: goal007.FixedInputs,
    process_seed: goal007.StreamSeedRecord,
    truth_cells: tuple[goal008.TruthCell, ...] = TRUTH_CELLS,
) -> tuple[tuple[goal008.TruthCell, ContrastSpreadTruth], ...]:
    """Generate one process-paired block with exact rho scaling."""
    return goal008.generate_truth_block(fixed, process_seed, truth_cells)


def generate_cell_observations(
    fixed: goal007.FixedInputs,
    truth: ContrastSpreadTruth,
    detection_seed: goal004.StreamSeedRecord,
) -> tuple[Observation, ...]:
    """Retain all two-visit records using one cell-specific detection stream."""
    observation_truth = StochasticSpreadTruth(
        arrival=truth.arrival,
        source_zone=truth.source_zone,
        reachable=truth.reachable,
        rate=truth.rho,
    )
    return goal004.generate_observations(
        fixed.design.sites,
        observation_truth,
        goal004.generator_from_seed_record(detection_seed),
    )


def no_false_positives(
    records: tuple[Observation, ...],
    truth: ContrastSpreadTruth,
) -> bool:
    return all(
        not record.detected or truth.arrival[record.row, record.col] <= record.time
        for record in records
    )


def classify_cell(
    *,
    artificial_face_contact_count: int,
    physical_topology_success_count: int,
    validation_count: int,
    calibrated_coverage: EstimateInterval,
    median_absolute_log_rho_error: float,
    median_absolute_eta_error: float,
    median_projected_log_rho_width: float,
    median_projected_eta_width: float,
    paired_brier_interval: EstimateInterval,
) -> CellDecision:
    """Record every gate and apply the frozen first-match cell precedence."""
    if validation_count <= 0:
        raise ValueError("validation count must be positive")
    candidate_domain_unclosed = artificial_face_contact_count > 25
    design_limited = physical_topology_success_count < ceil(0.95 * validation_count)
    local_calibration_not_ready = not (
        calibrated_coverage.lower <= 0.95 <= calibrated_coverage.upper
    )
    recovery_imprecise = (
        median_absolute_log_rho_error > 0.10
        or median_absolute_eta_error > 0.25
        or median_projected_log_rho_width > 0.50
        or median_projected_eta_width > 0.75
    )
    neutral_better = paired_brier_interval.lower > 0.0
    recoverable = paired_brier_interval.upper < 0.0
    mechanism_inconclusive = not neutral_better and not recoverable
    precedence = (
        (candidate_domain_unclosed, "cell_candidate_domain_unclosed"),
        (design_limited, "cell_design_limited"),
        (local_calibration_not_ready, "cell_local_calibration_not_ready"),
        (recovery_imprecise, "cell_recovery_imprecise"),
        (neutral_better, "cell_neutral_better"),
        (recoverable, "cell_recoverable"),
        (mechanism_inconclusive, "cell_mechanism_inconclusive"),
    )
    outcome = next(label for gate, label in precedence if gate)
    return CellDecision(
        candidate_domain_unclosed=candidate_domain_unclosed,
        design_limited=design_limited,
        local_calibration_not_ready=local_calibration_not_ready,
        recovery_imprecise=recovery_imprecise,
        neutral_better=neutral_better,
        recoverable=recoverable,
        mechanism_inconclusive=mechanism_inconclusive,
        outcome=outcome,
    )


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


def run_truth_cell(
    cell: goal008.TruthCell,
    config: Goal012Config = DEFAULT_CONFIG,
    *,
    fixed_inputs: goal007.FixedInputs | None = None,
    seed_manifest: SeedManifest | None = None,
) -> CellResult:
    """Run one deterministic truth-cell analysis without writing artifacts."""
    cells = config.resolved_truth_cells
    matches = tuple(item for item in cells if item.cell_id == cell.cell_id)
    if len(matches) != 1:
        raise ValueError("truth cell is not part of this Goal 012 configuration")
    cell = matches[0]
    fixed = fixed_inputs if fixed_inputs is not None else build_fixed_inputs()
    manifest = seed_manifest if seed_manifest is not None else spawn_seed_manifest(config)
    bank, variants, bank_replay = goal011.build_integration_banks(
        config.goal011_config,
        fixed,
        manifest.integration_bank,
    )
    calibration = _run_cell_calibration(
        cell,
        config,
        fixed,
        manifest.calibration,
        bank.site_ids,
        variants,
    )
    cutoffs = _calibration_cutoffs(config, calibration)
    validation, representatives, signals = _run_cell_validation(
        cell,
        config,
        fixed,
        manifest.validation,
        bank.site_ids,
        variants,
        cutoffs,
    )
    summaries = _aggregate_cell_banks(cell, config, variants, cutoffs, validation)
    relevant_streams = (
        *manifest.integration_bank,
        *(
            stream
            for block in (*manifest.calibration, *manifest.validation)
            for stream in (block.process, block.detection_for(cell.cell_id))
        ),
    )
    invariants = {
        **fixed.invariants,
        "truth_cell_membership": cell.cell_id in {item.cell_id for item in cells},
        "bank_replay": bank_replay.all_pass,
        "integration_bank_shape": bank.arrivals.shape
        == (config.bank_size, len(config.etas), len(fixed.design.sites)),
        "bank_variants": tuple(variant.name for variant in variants) == BANK_VARIANT_NAMES,
        "category_weight_support": all(
            variant.weights.shape
            == (len(config.etas), len(config.rhos), len(fixed.design.sites), CATEGORY_COUNT)
            and np.isfinite(variant.weights).all()
            and (variant.weights > 0.0).all()
            and np.allclose(variant.weights.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)
            for variant in variants
        ),
        "cell_stream_uniqueness": len(
            {(stream.entropy, stream.spawn_key) for stream in relevant_streams}
        )
        == len(relevant_streams),
        "calibration_result_count": len(calibration)
        == len(BANK_VARIANT_NAMES) * config.calibration_blocks,
        "validation_result_count": len(validation)
        == len(BANK_VARIANT_NAMES) * config.validation_blocks,
        "complete_visit_histories": all(row.record_count == 1920 for row in calibration)
        and all(
            row.record_count == 1920
            and row.training_record_count == 1440
            and row.holdout_record_count == 480
            for row in validation
        ),
        "zero_false_positives": all(row.no_false_positives for row in calibration)
        and all(row.no_false_positives for row in validation),
        "train_holdout_isolation": all(row.split_isolated for row in validation),
        "finite_likelihoods_and_scores": all(
            isfinite(row.expanded_lr_at_truth)
            and isfinite(row.old_domain_lr_at_truth)
            and row.expanded_mle_cells
            and row.old_domain_mle_cells
            for row in calibration
        )
        and all(
            isfinite(row.expanded_lr_at_truth)
            and isfinite(row.old_domain_lr_at_truth)
            and isfinite(row.expanded_paired_brier_difference)
            and isfinite(row.old_domain_paired_brier_difference)
            and row.expanded_mle_cells
            and row.old_domain_mle_cells
            for row in validation
        ),
        "truth_specific_support_summaries": all(
            row.truth_rho == cell.rho
            and row.truth_eta == cell.eta
            and row.truth_rho_index == cell.rho_index
            and row.truth_eta_index == cell.eta_index
            for row in validation
        ),
        "boundary_faces_reconciled": all(
            row.expanded_support_boundary_faces
            == goal008.support_boundary_faces(
                row.expanded_support_indices,
                eta_count=len(config.etas),
                rho_count=len(config.rhos),
            )
            and row.old_domain_support_boundary_faces
            == goal008.support_boundary_faces(
                row.old_domain_support_indices,
                eta_count=len(config.old_etas),
                rho_count=len(config.rhos),
            )
            for row in validation
        ),
        "local_dual_domain_cutoffs": len(summaries) == 3
        and all(
            row.cutoff_source_cell == row.truth_cell == cell.cell_id
            and row.cutoff.sample_size == config.calibration_blocks
            and row.old_domain_cutoff.sample_size == config.calibration_blocks
            and row.cutoff.rank_one_based == config.calibration_rank_one_based
            and row.old_domain_cutoff.rank_one_based == config.calibration_rank_one_based
            for row in summaries
        ),
        "representative_validation_zero": len(representatives) == 3
        and tuple(row.bank_variant for row in representatives) == BANK_VARIANT_NAMES
        and all(row.block_index == 0 for row in representatives),
        "observation_signal_rows": len(signals) == len(SURVEY_TIMES),
    }
    return CellResult(
        truth_cell=cell,
        calibration_results=calibration,
        validation_results=validation,
        observation_signal_summary=signals,
        representative_profiles=representatives,
        summaries=summaries,
        seed_manifest_digest=_seed_manifest_digest(manifest),
        invariants=invariants,
    )


def run_campaign(
    config: Goal012Config = DEFAULT_CONFIG,
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
    source_invariants = _source_invariants()
    central = _central_reconciliation(
        config,
        manifest,
        calibration,
        validation,
        summaries,
        source_invariants,
    )
    expected_seed_digest = _seed_manifest_digest(manifest)
    cell_invariants = {
        result.truth_cell.cell_id: dict(result.invariants) for result in cell_results
    }
    streams = manifest.stream_records
    invariants = {
        **source_invariants,
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


def _run_cell_calibration(
    cell: goal008.TruthCell,
    config: Goal012Config,
    fixed: goal007.FixedInputs,
    blocks: tuple[BlockSeedRecord, ...],
    site_ids: tuple[str, ...],
    variants: tuple[goal007.BankVariant, ...],
) -> tuple[CalibrationResult, ...]:
    rhos = np.asarray(config.rhos, dtype=np.float64)
    etas = np.asarray(config.etas, dtype=np.float64)
    rows: list[CalibrationResult] = []
    for block in blocks:
        truth = _truth_for_cell(fixed, block.process, cell)
        records = generate_cell_observations(
            fixed,
            truth,
            block.detection_for(cell.cell_id),
        )
        selected, histories = site_history_probabilities(site_ids=site_ids, records=records)
        for variant in variants:
            expanded = joint_profile_from_history_probabilities(
                weights=variant.weights,
                rhos=rhos,
                etas=etas,
                bank_site_ids=site_ids,
                history_site_ids=selected,
                history_probabilities=histories,
                scope="all",
            )
            old = project_eta_domain(expanded)
            expanded_truth = float(expanded.log_likelihoods[cell.eta_index, cell.rho_index])
            old_truth = float(old.log_likelihoods[cell.eta_index, cell.rho_index])
            rows.append(
                CalibrationResult(
                    phase="calibration",
                    block_index=block.index,
                    pairing_group=_pairing_group("calibration", block.index),
                    truth_cell=cell.cell_id,
                    truth_rho=cell.rho,
                    truth_eta=cell.eta,
                    truth_rho_index=cell.rho_index,
                    truth_eta_index=cell.eta_index,
                    bank_variant=variant.name,
                    cutoff_source_cell=cell.cell_id,
                    cutoff_source_rho=cell.rho,
                    cutoff_source_eta=cell.eta,
                    record_count=len(records),
                    no_false_positives=no_false_positives(records, truth),
                    expanded_lr_at_truth=max(
                        0.0,
                        2.0 * (expanded.maximum_log_likelihood - expanded_truth),
                    ),
                    old_domain_lr_at_truth=max(
                        0.0,
                        2.0 * (old.maximum_log_likelihood - old_truth),
                    ),
                    expanded_truth_log_likelihood=expanded_truth,
                    old_domain_truth_log_likelihood=old_truth,
                    expanded_maximum_log_likelihood=expanded.maximum_log_likelihood,
                    old_domain_maximum_log_likelihood=old.maximum_log_likelihood,
                    expanded_mle_cells=expanded.mle_cells,
                    old_domain_mle_cells=old.mle_cells,
                )
            )
    return tuple(rows)


def _calibration_cutoffs(
    config: Goal012Config,
    rows: tuple[CalibrationResult, ...],
) -> _Cutoffs:
    return _Cutoffs(
        expanded={
            name: order_statistic_cutoff(
                tuple(row.expanded_lr_at_truth for row in rows if row.bank_variant == name),
                rank_one_based=config.calibration_rank_one_based,
            )
            for name in BANK_VARIANT_NAMES
        },
        old_domain={
            name: order_statistic_cutoff(
                tuple(row.old_domain_lr_at_truth for row in rows if row.bank_variant == name),
                rank_one_based=config.calibration_rank_one_based,
            )
            for name in BANK_VARIANT_NAMES
        },
    )


def _run_cell_validation(
    cell: goal008.TruthCell,
    config: Goal012Config,
    fixed: goal007.FixedInputs,
    blocks: tuple[BlockSeedRecord, ...],
    site_ids: tuple[str, ...],
    variants: tuple[goal007.BankVariant, ...],
    cutoffs: _Cutoffs,
) -> tuple[
    tuple[ValidationResult, ...],
    tuple[RepresentativeProfile, ...],
    tuple[ObservationSignalSummary, ...],
]:
    rhos = np.asarray(config.rhos, dtype=np.float64)
    etas = np.asarray(config.etas, dtype=np.float64)
    rows: list[ValidationResult] = []
    representatives: list[RepresentativeProfile] = []
    occupied_signals: dict[int, list[float]] = {survey_time: [] for survey_time in SURVEY_TIMES}
    detected_signals: dict[int, list[float]] = {survey_time: [] for survey_time in SURVEY_TIMES}
    for block in blocks:
        truth = _truth_for_cell(fixed, block.process, cell)
        records = generate_cell_observations(
            fixed,
            truth,
            block.detection_for(cell.cell_id),
        )
        training = tuple(record for record in records if record.split == "training")
        holdout = tuple(record for record in records if record.split == "holdout")
        full_sites, full_histories = site_history_probabilities(
            site_ids=site_ids,
            records=records,
        )
        training_sites, training_histories = site_history_probabilities(
            site_ids=site_ids,
            records=training,
        )
        neutral = fit_time_stratified_baseline(training, survey_times=SURVEY_TIMES)
        neutral_score = score_time_stratified_baseline(neutral, holdout)
        neutral_probabilities = tuple(value for _, value in neutral.probabilities)
        split_isolated = {record.cluster_id for record in training}.isdisjoint(
            {record.cluster_id for record in holdout}
        )
        for survey_time in SURVEY_TIMES:
            occupied_signals[survey_time].append(
                float(
                    np.mean(
                        [
                            truth.arrival[site.row, site.col] <= survey_time
                            for site in fixed.design.sites
                        ]
                    )
                )
            )
            detected_signals[survey_time].append(
                float(
                    np.mean([record.detected for record in records if record.time == survey_time])
                )
            )
        for variant in variants:
            expanded = joint_profile_from_history_probabilities(
                weights=variant.weights,
                rhos=rhos,
                etas=etas,
                bank_site_ids=site_ids,
                history_site_ids=full_sites,
                history_probabilities=full_histories,
                scope="all",
            )
            old = project_eta_domain(expanded)
            expanded_support = summarize_joint_profile(
                expanded,
                cutoff=cutoffs.expanded[variant.name].cutoff,
                truth_rho=cell.rho,
                truth_eta=cell.eta,
            )
            old_support = summarize_joint_profile(
                old,
                cutoff=cutoffs.old_domain[variant.name].cutoff,
                truth_rho=cell.rho,
                truth_eta=cell.eta,
            )
            expanded_training = joint_profile_from_history_probabilities(
                weights=variant.weights,
                rhos=rhos,
                etas=etas,
                bank_site_ids=site_ids,
                history_site_ids=training_sites,
                history_probabilities=training_histories,
                scope="training",
            )
            old_training = project_eta_domain(expanded_training)
            expanded_scores = _process_scores(
                expanded_training,
                variant.weights,
                site_ids,
                holdout,
            )
            old_scores = _process_scores(old_training, variant.weights, site_ids, holdout)
            expanded_predictive = goal007.summarize_predictive_comparison(
                expanded_scores,
                neutral_score,
                neutral_probability_minimum=min(neutral_probabilities),
                neutral_probability_maximum=max(neutral_probabilities),
            )
            old_predictive = goal007.summarize_predictive_comparison(
                old_scores,
                neutral_score,
                neutral_probability_minimum=min(neutral_probabilities),
                neutral_probability_maximum=max(neutral_probabilities),
            )
            expanded_faces = goal008.support_boundary_faces(
                expanded_support.support_indices,
                eta_count=len(config.etas),
                rho_count=len(config.rhos),
            )
            old_faces = goal008.support_boundary_faces(
                old_support.support_indices,
                eta_count=len(config.old_etas),
                rho_count=len(config.rhos),
            )
            expanded_truth = float(expanded.log_likelihoods[cell.eta_index, cell.rho_index])
            old_truth = float(old.log_likelihoods[cell.eta_index, cell.rho_index])
            rows.append(
                ValidationResult(
                    phase="validation",
                    block_index=block.index,
                    pairing_group=_pairing_group("validation", block.index),
                    truth_cell=cell.cell_id,
                    truth_rho=cell.rho,
                    truth_eta=cell.eta,
                    truth_rho_index=cell.rho_index,
                    truth_eta_index=cell.eta_index,
                    bank_variant=variant.name,
                    cutoff_source_cell=cell.cell_id,
                    cutoff_source_rho=cell.rho,
                    cutoff_source_eta=cell.eta,
                    record_count=len(records),
                    training_record_count=len(training),
                    holdout_record_count=len(holdout),
                    split_isolated=split_isolated,
                    no_false_positives=no_false_positives(records, truth),
                    expanded_lr_at_truth=max(
                        0.0,
                        2.0 * (expanded.maximum_log_likelihood - expanded_truth),
                    ),
                    old_domain_lr_at_truth=max(
                        0.0,
                        2.0 * (old.maximum_log_likelihood - old_truth),
                    ),
                    expanded_truth_included=expanded_support.truth_included,
                    expanded_support_cell_count=expanded_support.support_cell_count,
                    expanded_support_component_count=expanded_support.support_component_count,
                    expanded_support_boundary_contact=(expanded_support.support_boundary_contact),
                    expanded_support_boundary_faces=expanded_faces,
                    expanded_projected_log_rho_width=(expanded_support.projected_log_rho_width),
                    expanded_projected_eta_width=expanded_support.projected_eta_width,
                    expanded_support_indices=expanded_support.support_indices,
                    expanded_support_correlation=expanded_support.support_correlation,
                    expanded_support_correlation_reason=(
                        expanded_support.support_correlation_reason
                    ),
                    expanded_mle_indices=expanded_support.mle_indices,
                    expanded_mle_cells=expanded_support.mle_cells,
                    expanded_minimum_absolute_log_rho_error=(
                        expanded_support.minimum_absolute_log_rho_error
                    ),
                    expanded_minimum_absolute_eta_error=(
                        expanded_support.minimum_absolute_eta_error
                    ),
                    expanded_training_mle_cells=expanded_training.mle_cells,
                    expanded_support_uses_appended_eta=any(
                        config.etas[eta_index] > OLD_DOMAIN_MAXIMUM_ETA
                        for eta_index, _ in expanded_support.support_indices
                    ),
                    expanded_mle_uses_appended_eta=any(
                        eta > OLD_DOMAIN_MAXIMUM_ETA for _, eta in expanded_support.mle_cells
                    ),
                    expanded_stochastic_log_score_minimum=(
                        expanded_predictive.stochastic_log_score_minimum
                    ),
                    expanded_stochastic_log_score_maximum=(
                        expanded_predictive.stochastic_log_score_maximum
                    ),
                    expanded_stochastic_brier_minimum=(
                        expanded_predictive.stochastic_brier_minimum
                    ),
                    expanded_stochastic_brier_maximum=(
                        expanded_predictive.stochastic_brier_maximum
                    ),
                    expanded_stochastic_probability_minimum=(
                        expanded_predictive.stochastic_probability_minimum
                    ),
                    expanded_stochastic_probability_maximum=(
                        expanded_predictive.stochastic_probability_maximum
                    ),
                    neutral_log_score=neutral_score.total_log_score,
                    neutral_brier_score=neutral_score.mean_brier_score,
                    neutral_probability_minimum=min(neutral_probabilities),
                    neutral_probability_maximum=max(neutral_probabilities),
                    expanded_paired_brier_difference=(expanded_predictive.paired_brier_difference),
                    old_domain_truth_included=old_support.truth_included,
                    old_domain_support_cell_count=old_support.support_cell_count,
                    old_domain_support_component_count=old_support.support_component_count,
                    old_domain_support_boundary_contact=(old_support.support_boundary_contact),
                    old_domain_support_boundary_faces=old_faces,
                    old_domain_projected_log_rho_width=(old_support.projected_log_rho_width),
                    old_domain_projected_eta_width=old_support.projected_eta_width,
                    old_domain_support_indices=old_support.support_indices,
                    old_domain_mle_cells=old_support.mle_cells,
                    old_domain_minimum_absolute_log_rho_error=(
                        old_support.minimum_absolute_log_rho_error
                    ),
                    old_domain_minimum_absolute_eta_error=(old_support.minimum_absolute_eta_error),
                    old_domain_training_mle_cells=old_training.mle_cells,
                    old_domain_paired_brier_difference=(old_predictive.paired_brier_difference),
                )
            )
            if block.index == 0:
                representatives.append(
                    RepresentativeProfile(
                        truth_cell=cell.cell_id,
                        truth_rho=cell.rho,
                        truth_eta=cell.eta,
                        truth_rho_index=cell.rho_index,
                        truth_eta_index=cell.eta_index,
                        cutoff_source_cell=cell.cell_id,
                        cutoff_source_rho=cell.rho,
                        cutoff_source_eta=cell.eta,
                        block_index=0,
                        bank_variant=variant.name,
                        expanded_cutoff=cutoffs.expanded[variant.name].cutoff,
                        old_domain_cutoff=cutoffs.old_domain[variant.name].cutoff,
                        expanded_profile=expanded,
                        old_domain_profile=old,
                        expanded_summary=expanded_support,
                        old_domain_summary=old_support,
                    )
                )
    signals = tuple(
        ObservationSignalSummary(
            truth_cell=cell.cell_id,
            truth_rho=cell.rho,
            truth_eta=cell.eta,
            survey_time=survey_time,
            occupied_fraction_mean=float(np.mean(occupied_signals[survey_time])),
            occupied_fraction_lower=float(np.quantile(occupied_signals[survey_time], 0.05)),
            occupied_fraction_upper=float(np.quantile(occupied_signals[survey_time], 0.95)),
            detected_fraction_mean=float(np.mean(detected_signals[survey_time])),
            detected_fraction_lower=float(np.quantile(detected_signals[survey_time], 0.05)),
            detected_fraction_upper=float(np.quantile(detected_signals[survey_time], 0.95)),
        )
        for survey_time in SURVEY_TIMES
    )
    return tuple(rows), tuple(representatives), signals


def _process_scores(
    profile: JointGridProfile,
    weights: np.ndarray[Any, np.dtype[np.float64]],
    site_ids: tuple[str, ...],
    holdout: tuple[Observation, ...],
) -> tuple[PredictiveScore, ...]:
    return tuple(
        score_predictions(
            record_detection_probabilities(
                weights=weights[eta_index, rho_index],
                site_ids=site_ids,
                records=holdout,
                detection_probability=DETECTION_PROBABILITY,
            ),
            holdout,
        )
        for eta_index, rho_index in profile.mle_indices
    )


def _aggregate_cell_banks(
    cell: goal008.TruthCell,
    config: Goal012Config,
    variants: tuple[goal007.BankVariant, ...],
    cutoffs: _Cutoffs,
    validation: tuple[ValidationResult, ...],
) -> tuple[CellBankSummary, ...]:
    summaries: list[CellBankSummary] = []
    for variant in variants:
        rows = tuple(row for row in validation if row.bank_variant == variant.name)
        expanded = _domain_aggregate(rows, old=False)
        old = _domain_aggregate(rows, old=True)
        expanded_decision = classify_cell(
            artificial_face_contact_count=expanded.artificial_face_count,
            physical_topology_success_count=expanded.physical_topology_count,
            validation_count=len(rows),
            calibrated_coverage=expanded.coverage,
            median_absolute_log_rho_error=expanded.rho_error,
            median_absolute_eta_error=expanded.eta_error,
            median_projected_log_rho_width=expanded.rho_width,
            median_projected_eta_width=expanded.eta_width,
            paired_brier_interval=expanded.brier,
        )
        old_decision = classify_cell(
            artificial_face_contact_count=old.artificial_face_count,
            physical_topology_success_count=old.physical_topology_count,
            validation_count=len(rows),
            calibrated_coverage=old.coverage,
            median_absolute_log_rho_error=old.rho_error,
            median_absolute_eta_error=old.eta_error,
            median_projected_log_rho_width=old.rho_width,
            median_projected_eta_width=old.eta_width,
            paired_brier_interval=old.brier,
        )
        summaries.append(
            CellBankSummary(
                truth_cell=cell.cell_id,
                truth_rho=cell.rho,
                truth_eta=cell.eta,
                truth_rho_index=cell.rho_index,
                truth_eta_index=cell.eta_index,
                bank_variant=variant.name,
                cutoff_source_cell=cell.cell_id,
                cutoff_source_rho=cell.rho,
                cutoff_source_eta=cell.eta,
                draw_count=variant.draw_count,
                cutoff=cutoffs.expanded[variant.name],
                old_domain_cutoff=cutoffs.old_domain[variant.name],
                expanded_coverage_success_count=expanded.coverage_count,
                expanded_calibrated_coverage=expanded.coverage,
                expanded_topology_success_count=expanded.topology_count,
                expanded_physical_topology_success_count=(expanded.physical_topology_count),
                expanded_boundary_contact_count=expanded.boundary_count,
                artificial_face_contact_count=expanded.artificial_face_count,
                rho_min_contact_count=expanded.rho_min_count,
                rho_max_contact_count=expanded.rho_max_count,
                eta_min_contact_count=expanded.eta_min_count,
                eta_max_contact_count=expanded.eta_max_count,
                expanded_median_minimum_absolute_log_rho_error=expanded.rho_error,
                expanded_median_minimum_absolute_eta_error=expanded.eta_error,
                expanded_median_projected_log_rho_width=expanded.rho_width,
                expanded_median_projected_eta_width=expanded.eta_width,
                expanded_median_support_cell_count=expanded.support_cells,
                expanded_mean_mle_set_size=expanded.mle_size,
                expanded_paired_brier_interval=expanded.brier,
                expanded_mean_stochastic_brier_worst_mle=fmean(
                    row.expanded_stochastic_brier_maximum for row in rows
                ),
                mean_neutral_brier=fmean(row.neutral_brier_score for row in rows),
                finite_log_score_count=sum(
                    isfinite(row.expanded_stochastic_log_score_minimum)
                    and isfinite(row.expanded_stochastic_log_score_maximum)
                    and isfinite(row.neutral_log_score)
                    for row in rows
                ),
                expanded_candidate_domain_unclosed=(expanded_decision.candidate_domain_unclosed),
                expanded_design_limited=expanded_decision.design_limited,
                expanded_local_calibration_not_ready=(
                    expanded_decision.local_calibration_not_ready
                ),
                expanded_recovery_imprecise=expanded_decision.recovery_imprecise,
                expanded_neutral_better=expanded_decision.neutral_better,
                expanded_recoverable=expanded_decision.recoverable,
                expanded_mechanism_inconclusive=(expanded_decision.mechanism_inconclusive),
                expanded_class=expanded_decision.outcome,
                old_domain_coverage_success_count=old.coverage_count,
                old_domain_calibrated_coverage=old.coverage,
                old_domain_topology_success_count=old.topology_count,
                old_domain_physical_topology_success_count=old.physical_topology_count,
                old_domain_boundary_contact_count=old.boundary_count,
                old_domain_artificial_face_contact_count=old.artificial_face_count,
                old_domain_rho_min_contact_count=old.rho_min_count,
                old_domain_rho_max_contact_count=old.rho_max_count,
                old_domain_eta_min_contact_count=old.eta_min_count,
                old_domain_eta_max_contact_count=old.eta_max_count,
                old_domain_median_minimum_absolute_log_rho_error=old.rho_error,
                old_domain_median_minimum_absolute_eta_error=old.eta_error,
                old_domain_median_projected_log_rho_width=old.rho_width,
                old_domain_median_projected_eta_width=old.eta_width,
                old_domain_median_support_cell_count=old.support_cells,
                old_domain_mean_mle_set_size=old.mle_size,
                old_domain_paired_brier_interval=old.brier,
                old_domain_candidate_domain_unclosed=(old_decision.candidate_domain_unclosed),
                old_domain_design_limited=old_decision.design_limited,
                old_domain_local_calibration_not_ready=(old_decision.local_calibration_not_ready),
                old_domain_recovery_imprecise=old_decision.recovery_imprecise,
                old_domain_neutral_better=old_decision.neutral_better,
                old_domain_recoverable=old_decision.recoverable,
                old_domain_mechanism_inconclusive=(old_decision.mechanism_inconclusive),
                old_domain_class=old_decision.outcome,
            )
        )
    return tuple(summaries)


def _domain_aggregate(
    rows: tuple[ValidationResult, ...],
    *,
    old: bool,
) -> _DomainAggregate:
    if old:
        included = tuple(row.old_domain_truth_included for row in rows)
        components = tuple(row.old_domain_support_component_count for row in rows)
        faces = tuple(row.old_domain_support_boundary_faces for row in rows)
        boundary = tuple(row.old_domain_support_boundary_contact for row in rows)
        rho_errors = tuple(row.old_domain_minimum_absolute_log_rho_error for row in rows)
        eta_errors = tuple(row.old_domain_minimum_absolute_eta_error for row in rows)
        rho_widths = tuple(row.old_domain_projected_log_rho_width for row in rows)
        eta_widths = tuple(row.old_domain_projected_eta_width for row in rows)
        support_cells = tuple(row.old_domain_support_cell_count for row in rows)
        mle_sizes = tuple(len(row.old_domain_mle_cells) for row in rows)
        brier = tuple(row.old_domain_paired_brier_difference for row in rows)
    else:
        included = tuple(row.expanded_truth_included for row in rows)
        components = tuple(row.expanded_support_component_count for row in rows)
        faces = tuple(row.expanded_support_boundary_faces for row in rows)
        boundary = tuple(row.expanded_support_boundary_contact for row in rows)
        rho_errors = tuple(row.expanded_minimum_absolute_log_rho_error for row in rows)
        eta_errors = tuple(row.expanded_minimum_absolute_eta_error for row in rows)
        rho_widths = tuple(row.expanded_projected_log_rho_width for row in rows)
        eta_widths = tuple(row.expanded_projected_eta_width for row in rows)
        support_cells = tuple(row.expanded_support_cell_count for row in rows)
        mle_sizes = tuple(len(row.expanded_mle_cells) for row in rows)
        brier = tuple(row.expanded_paired_brier_difference for row in rows)
    coverage_count = sum(included)
    artificial = tuple(
        any(face in {"rho_min", "rho_max", "eta_max"} for face in row_faces) for row_faces in faces
    )
    physical_success = tuple(
        component == 1 and "eta_min" not in row_faces
        for component, row_faces in zip(components, faces, strict=True)
    )
    strict_success = tuple(
        component == 1 and not contacted
        for component, contacted in zip(components, boundary, strict=True)
    )
    return _DomainAggregate(
        coverage_count=coverage_count,
        coverage=wilson_interval(coverage_count, len(rows)),
        topology_count=sum(strict_success),
        physical_topology_count=sum(physical_success),
        boundary_count=sum(boundary),
        artificial_face_count=sum(artificial),
        rho_min_count=sum("rho_min" in row_faces for row_faces in faces),
        rho_max_count=sum("rho_max" in row_faces for row_faces in faces),
        eta_min_count=sum("eta_min" in row_faces for row_faces in faces),
        eta_max_count=sum("eta_max" in row_faces for row_faces in faces),
        rho_error=float(median(rho_errors)),
        eta_error=float(median(eta_errors)),
        rho_width=float(median(rho_widths)),
        eta_width=float(median(eta_widths)),
        support_cells=float(median(support_cells)),
        mle_size=fmean(mle_sizes),
        brier=normal_mean_interval(brier),
    )


def _central_reconciliation(
    config: Goal012Config,
    manifest: SeedManifest,
    calibration: tuple[CalibrationResult, ...],
    validation: tuple[ValidationResult, ...],
    summaries: tuple[CellBankSummary, ...],
    source_invariants: Mapping[str, bool],
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
        "source_commit_and_blobs": all(source_invariants.values()),
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


def _goal011_seed_identity(config: Goal012Config, manifest: SeedManifest) -> bool:
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


def _truth_for_cell(
    fixed: goal007.FixedInputs,
    process_seed: goal007.StreamSeedRecord,
    cell: goal008.TruthCell,
) -> ContrastSpreadTruth:
    return next(
        truth
        for truth_cell, truth in generate_truth_block(fixed, process_seed, (cell,))
        if truth_cell.cell_id == cell.cell_id
    )


def _run_truth_cell_task(
    task: tuple[goal008.TruthCell, Goal012Config],
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


def _process_record(
    phase: str,
    index: int,
    role: str,
    sequence: np.random.SeedSequence,
) -> goal007.StreamSeedRecord:
    return goal007.StreamSeedRecord(
        phase=phase,
        index=index,
        stream_role=role,
        entropy=int(cast(int, sequence.entropy)),
        spawn_key=tuple(int(value) for value in sequence.spawn_key),
        state_words=tuple(int(value) for value in sequence.generate_state(STATE_WORD_COUNT)),
        pool_size=sequence.pool_size,
    )


def _detection_record(
    phase: str,
    index: int,
    sequence: np.random.SeedSequence,
) -> goal004.StreamSeedRecord:
    return goal004.StreamSeedRecord(
        phase=phase,
        index=index,
        stream_role="detection",
        entropy=int(cast(int, sequence.entropy)),
        spawn_key=tuple(int(value) for value in sequence.spawn_key),
        state_words=tuple(int(value) for value in sequence.generate_state(STATE_WORD_COUNT)),
        pool_size=sequence.pool_size,
    )


def _noncentral_detection_blocks(
    root: np.random.SeedSequence,
    *,
    phase: str,
    count: int,
) -> tuple[tuple[CellDetectionSeed, ...], ...]:
    noncentral = tuple(cell for cell in TRUTH_CELLS if cell.cell_id != "cell-04")
    return tuple(
        tuple(
            CellDetectionSeed(
                truth_cell=cell.cell_id,
                detection=_detection_record(phase, block_index, child),
            )
            for cell, child in zip(noncentral, block_root.spawn(8), strict=True)
        )
        for block_index, block_root in enumerate(root.spawn(count))
    )


def _block_seed_record(
    *,
    phase: str,
    index: int,
    process: goal007.StreamSeedRecord,
    central: goal004.StreamSeedRecord,
    noncentral: tuple[CellDetectionSeed, ...],
) -> BlockSeedRecord:
    by_cell = {item.truth_cell: item.detection for item in noncentral}
    by_cell["cell-04"] = central
    return BlockSeedRecord(
        phase=phase,
        index=index,
        process=process,
        cell_detection=tuple(
            CellDetectionSeed(cell.cell_id, by_cell[cell.cell_id]) for cell in TRUTH_CELLS
        ),
    )


def _pairing_group(phase: str, block_index: int) -> str:
    return f"{phase}-process-block-{block_index:03d}"


def _seed_manifest_digest(manifest: SeedManifest) -> str:
    return _projection_digest(manifest)


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


def _validate_production_runtime(config: Goal012Config, workers: int) -> None:
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


def _source_invariants() -> dict[str, bool]:
    root = Path(__file__).resolve().parents[3]
    commit = SOURCE_IDENTITY["repository_commit"]
    commit_reconciled = _git_commit_is_ancestor(root, commit)
    parent_reconciled = all(
        _git_commit_blob_sha(root, commit, path) == SOURCE_IDENTITY[key]
        for key, path in PINNED_SOURCE_PATHS.items()
    )
    runtime_reconciled = all(
        _git_blob_sha(root / path) == SOURCE_IDENTITY[key]
        for key, path in PINNED_SOURCE_PATHS.items()
    )
    return {
        "frozen_repository_commit_reconciled": commit_reconciled,
        "frozen_parent_source_blobs_reconciled": parent_reconciled,
        "frozen_runtime_source_blobs_reconciled": runtime_reconciled,
        "frozen_source_blobs_reconciled": (
            commit_reconciled and parent_reconciled and runtime_reconciled
        ),
    }


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload, usedforsecurity=False).hexdigest()


def _git_commit_is_ancestor(repository_root: Path, commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=repository_root,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _git_commit_blob_sha(repository_root: Path, commit: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", f"{commit}:{path}"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


__all__ = [
    "ACCEPTED_GOAL011_REFERENCE",
    "BANK_VARIANT_NAMES",
    "DEFAULT_CONFIG",
    "DETECTION_PROBABILITY",
    "FROZEN_ETA_GRID",
    "FROZEN_RHO_GRID",
    "OLD_ETA_GRID",
    "SOURCE_IDENTITY",
    "TRUTH_CELLS",
    "BlockSeedRecord",
    "CalibrationResult",
    "CampaignExecutionTelemetry",
    "CellBankSummary",
    "CellDecision",
    "CellDetectionSeed",
    "CellExecutionTelemetry",
    "CentralReconciliation",
    "Goal012Config",
    "Goal012Result",
    "ObservationSignalSummary",
    "RepresentativeProfile",
    "SeedManifest",
    "ValidationResult",
    "build_fixed_inputs",
    "campaign_digest",
    "classify_cell",
    "classify_overall",
    "generate_cell_observations",
    "generate_truth_block",
    "goal011_calibration_projection",
    "goal011_summary_projection",
    "goal011_validation_projection",
    "no_false_positives",
    "run_campaign",
    "run_truth_cell",
    "smoke_config",
    "spawn_seed_manifest",
]
