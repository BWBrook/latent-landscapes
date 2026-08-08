"""Cross-truth joint rho-eta recovery under perfect detection."""

from __future__ import annotations

import hashlib
import json
import os
import resource
import sys
import time
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, fields, is_dataclass, replace
from math import isfinite
from statistics import fmean, median
from typing import Any

import numpy as np

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
from latent_landscapes.goal006.spread import (
    ContrastSpreadTruth,
    compute_contrast_spread,
    sample_edge_shock_vector,
)
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal007.likelihood import (
    CATEGORY_COUNT,
    JointGridProfile,
    JointProfileSummary,
    joint_profile,
    record_occupancy_probabilities,
    score_predictions,
    summarize_joint_profile,
)
from latent_landscapes.goal007.observations import (
    SURVEY_TIMES,
    CollapsedObservation,
    collapse_duplicate_visits,
    generate_perfect_observations,
    site_onset_categories,
)

MASTER_SEED = goal007.MASTER_SEED
INTEGRATION_BANK_SIZE = goal007.INTEGRATION_BANK_SIZE
CALIBRATION_BLOCKS = goal007.CALIBRATION_REPLICATES
VALIDATION_BLOCKS = goal007.VALIDATION_REPLICATES
CALIBRATION_RANK_ONE_BASED = goal007.CALIBRATION_RANK_ONE_BASED
BANK_VARIANT_NAMES = goal007.BANK_VARIANT_NAMES
FROZEN_RHO_GRID = goal007.FROZEN_RHO_GRID
FROZEN_ETA_GRID = goal007.FROZEN_ETA_GRID
THREAD_LIMIT_NAMES = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)

SOURCE_IDENTITY = {
    "repository_commit": "8602f6ba0f55353252730c1fb68994bd37f90802",
    "goal007_benchmark_blob": "f1b68e7f9ae4efef87be81a4df6beb24d9d11bec",
    "goal007_likelihood_blob": "00aa5d329dc0f500ace0305c0ca1bf6a3e046847",
    "goal007_observation_blob": "77bc13adf83317f3c2402e15a885e1032eeff941",
    "goal007_artifact_blob": "2769d24959607a6e5b54f3c4e4fe0d58d7722a9e",
    "accepted_goal007_log_blob": "d3fe2e6a73ef0031c5ce3de46eb7cd8a1204d27b",
    "lockfile_blob": "56ac1fe55b4c1182e4f89448a95d1864745261dc",
}
CENTRAL_HISTORICAL_RAW_HASHES = {
    "calibration": "60b541649ad8fffa7bef0810c5246358c50dacf01027c2a6fa5bf6cbb5523f24",
    "validation": "ac559b76981b9962db4e537f725dd8c87b8348866e4c28000c7316348bb08439",
    "bank": "76168e5525ddf86f50c702c88ffff04206875de19acba12801c0d548dd788e3d",
}
CENTRAL_STRUCTURAL_HASHES = {
    "calibration": "2da6de6fd746892c72e4ba7b2eff5174c494f33912f4b097c2d7ed3c64d916d7",
    "validation": "9edab67ef228a0e8ec634caae235e9f858f1fd461e5886dc0e113d5aa0acb173",
    "bank": "ef9510ad0bab11c6bc1f2b6281be485499343b66aac3ae7b98d4525d95af8971",
}
CENTRAL_CANONICAL_HASHES = {
    "calibration": "b2d157ce2ab0c2303f6a9cc9455c9c64f89275581eb9805ba745b0f03f9955b9",
    "validation": "bce714706ccf2ecdb9377d213ed54f17d37c3b0c30bb4b9ae11fada0351452f4",
    "bank": "5c5c97e2b3ab273f7976a0fda1285cb56c94d25a3a06803a2b835eb87c7cb5ce",
}
CENTRAL_REFERENCE: dict[str, object] = {
    "historical_raw_hashes": CENTRAL_HISTORICAL_RAW_HASHES,
    "structural_hashes": CENTRAL_STRUCTURAL_HASHES,
    "canonical_hashes": CENTRAL_CANONICAL_HASHES,
    "seed_manifest_sha256": ("2b57f1eb90db41201d5a1311db168c7012953e4f6683bd5c37845ac7a0113aae"),
    "source_identity_sha256": ("e4ff4b3a9db477b39137b85c44e9c2714abbdf1e338fe7b0a71d1b69c65850aa"),
    "outcome": "advance_to_joint_cross_truth_perfect_detection",
}
CANONICALIZATION_RULE = {
    "finite_float_decimal_places": 9,
    "negative_zero": "normalized_to_positive_zero",
    "nonfinite": "rejected_before_canonicalization",
    "representation": "json_number_rounded_to_decimal_places",
}
NONFINITE_TAGS = {
    "nan": "__nonfinite_float__:nan",
    "positive_infinity": "__nonfinite_float__:positive_infinity",
    "negative_infinity": "__nonfinite_float__:negative_infinity",
}


@dataclass(frozen=True, slots=True)
class TruthCell:
    cell_id: str
    rho: float
    eta: float
    rho_index: int
    eta_index: int

    def __post_init__(self) -> None:
        if not self.cell_id:
            raise ValueError("truth cell identifier must not be empty")
        if not isfinite(self.rho) or self.rho <= 0.0:
            raise ValueError("truth rho must be finite and positive")
        if not isfinite(self.eta) or self.eta < 0.0:
            raise ValueError("truth eta must be finite and nonnegative")
        if self.rho_index < 0 or self.eta_index < 0:
            raise ValueError("truth indices must be nonnegative")


TRUTH_CELLS = (
    TruthCell("cell-00", 0.5, 0.5, 150, 2),
    TruthCell("cell-01", 1.0, 0.5, 300, 2),
    TruthCell("cell-02", 2.0, 0.5, 450, 2),
    TruthCell("cell-03", 0.5, 1.0, 150, 4),
    TruthCell("cell-04", 1.0, 1.0, 300, 4),
    TruthCell("cell-05", 2.0, 1.0, 450, 4),
    TruthCell("cell-06", 0.5, 1.5, 150, 6),
    TruthCell("cell-07", 1.0, 1.5, 300, 6),
    TruthCell("cell-08", 2.0, 1.5, 450, 6),
)


@dataclass(frozen=True, slots=True)
class Goal008Config:
    master_seed: int = MASTER_SEED
    bank_size: int = INTEGRATION_BANK_SIZE
    calibration_blocks: int = CALIBRATION_BLOCKS
    validation_blocks: int = VALIDATION_BLOCKS
    calibration_rank_one_based: int = CALIBRATION_RANK_ONE_BASED
    rhos: tuple[float, ...] = FROZEN_RHO_GRID
    etas: tuple[float, ...] = FROZEN_ETA_GRID
    truth_cells: tuple[TruthCell, ...] = TRUTH_CELLS

    def __post_init__(self) -> None:
        if self.bank_size < 2 or self.bank_size % 2:
            raise ValueError("integration bank size must be positive and even")
        if self.calibration_blocks <= 0 or self.validation_blocks <= 0:
            raise ValueError("shock-block counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_blocks:
            raise ValueError("calibration rank must lie within the calibration blocks")
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
        cell_ids = tuple(cell.cell_id for cell in self.truth_cells)
        coordinates = tuple((cell.rho, cell.eta) for cell in self.truth_cells)
        if len(self.truth_cells) != 9:
            raise ValueError("Goal 008 requires exactly nine truth cells")
        if len(set(cell_ids)) != 9 or len(set(coordinates)) != 9:
            raise ValueError("truth cell identifiers and coordinates must be unique")
        if cell_ids != tuple(f"cell-{index:02d}" for index in range(9)):
            raise ValueError("truth cells must use the frozen row-major cell order")
        if any(
            cell.rho_index >= len(self.rhos)
            or cell.eta_index >= len(self.etas)
            or self.rhos[cell.rho_index] != cell.rho
            or self.etas[cell.eta_index] != cell.eta
            for cell in self.truth_cells
        ):
            raise ValueError("truth coordinates must match their candidate-grid indices")
        if tuple((cell.eta, cell.rho) for cell in self.truth_cells) != tuple(
            (eta, rho)
            for eta in sorted({cell.eta for cell in self.truth_cells})
            for rho in sorted({cell.rho for cell in self.truth_cells})
        ):
            raise ValueError("truth cells must be a complete eta-row/rho-column grid")

    @property
    def is_production(self) -> bool:
        return self == DEFAULT_CONFIG


DEFAULT_CONFIG = Goal008Config()


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
    analyst_record_count: int
    distinct_outcome_count: int
    duplicate_visits_agree: bool
    lr_at_truth: float
    truth_log_likelihood: float
    maximum_log_likelihood: float
    mle_indices: tuple[tuple[int, int], ...]
    mle_cells: tuple[tuple[float, float], ...]


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
    analyst_record_count: int
    distinct_outcome_count: int
    training_outcome_count: int
    holdout_outcome_count: int
    split_isolated: bool
    perfect_truth_mapping: bool
    lr_at_truth: float
    truth_log_likelihood: float
    maximum_log_likelihood: float
    truth_included: bool
    support_cell_count: int
    support_component_count: int
    support_boundary_contact: bool
    support_boundary_faces: tuple[str, ...]
    projected_log_rho_width: float
    projected_eta_width: float
    support_indices: tuple[tuple[int, int], ...]
    support_correlation: float | None
    support_correlation_reason: str | None
    mle_indices: tuple[tuple[int, int], ...]
    mle_cells: tuple[tuple[float, float], ...]
    minimum_absolute_log_rho_error: float
    minimum_absolute_eta_error: float
    training_mle_indices: tuple[tuple[int, int], ...]
    training_mle_cells: tuple[tuple[float, float], ...]
    stochastic_log_score_minimum: float
    stochastic_log_score_maximum: float
    stochastic_brier_minimum: float
    stochastic_brier_maximum: float
    stochastic_probability_minimum: float
    stochastic_probability_maximum: float
    neutral_log_score: float
    neutral_brier_score: float
    neutral_probability_minimum: float
    neutral_probability_maximum: float
    paired_brier_difference: float


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
    cutoff: float
    profile: JointGridProfile
    summary: JointProfileSummary


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
    coverage_success_count: int
    calibrated_coverage: EstimateInterval
    topology_success_count: int
    topology_success_proportion: float
    boundary_contact_count: int
    rho_min_contact_count: int
    rho_max_contact_count: int
    eta_min_contact_count: int
    eta_max_contact_count: int
    median_minimum_absolute_log_rho_error: float
    median_minimum_absolute_eta_error: float
    median_projected_log_rho_width: float
    median_projected_eta_width: float
    median_support_cell_count: float
    mean_mle_set_size: float
    paired_brier_interval: EstimateInterval
    mean_stochastic_brier_worst_mle: float
    mean_neutral_brier: float
    finite_log_score_count: int
    downstream_class: str


@dataclass(frozen=True, slots=True)
class CellResult:
    truth_cell: TruthCell
    calibration_results: tuple[CalibrationResult, ...]
    validation_results: tuple[ValidationResult, ...]
    representative_profiles: tuple[RepresentativeProfile, ...]
    bank_summaries: tuple[CellBankSummary, ...]
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
class ProjectionHashes:
    raw_sha256: str
    structural_sha256: str
    canonical_sha256: str


@dataclass(frozen=True, slots=True)
class CentralProjection:
    truth_cell: str
    calibration_rows: tuple[CalibrationResult, ...]
    validation_rows: tuple[ValidationResult, ...]
    bank_summaries: tuple[CellBankSummary, ...]
    production_reference_checked: bool
    production_reference_match: bool | None
    checks: dict[str, bool]
    observed: dict[str, object]
    expected: dict[str, object]
    raw_hashes: dict[str, str | None]
    historical_raw_hashes: dict[str, str]
    structural_hashes: dict[str, str | None]
    canonical_hashes: dict[str, str | None]
    canonicalization_rule: dict[str, object]
    nonfinite_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Goal008Result:
    config: Goal008Config
    seed_manifest: goal007.SeedManifest
    calibration_results: tuple[CalibrationResult, ...]
    validation_results: tuple[ValidationResult, ...]
    representative_profiles: tuple[RepresentativeProfile, ...]
    cell_bank_summaries: tuple[CellBankSummary, ...]
    cell_invariants: dict[str, dict[str, bool]]
    central_reconciliation: CentralProjection
    execution_telemetry: CampaignExecutionTelemetry
    invariants: dict[str, bool]
    outcome: str


def goal007_config(config: Goal008Config) -> goal007.Goal007Config:
    """Project Goal 008's inherited settings onto the Goal 007 core."""
    return goal007.Goal007Config(
        master_seed=config.master_seed,
        bank_size=config.bank_size,
        calibration_replicates=config.calibration_blocks,
        validation_replicates=config.validation_blocks,
        calibration_rank_one_based=config.calibration_rank_one_based,
        rhos=config.rhos,
        etas=config.etas,
    )


def spawn_seed_manifest(config: Goal008Config = DEFAULT_CONFIG) -> goal007.SeedManifest:
    """Replay the exact Goal 007 three-root SeedSequence tree."""
    return goal007.spawn_seed_manifest(goal007_config(config))


def support_boundary_faces(
    support_indices: tuple[tuple[int, int], ...],
    *,
    eta_count: int,
    rho_count: int,
) -> tuple[str, ...]:
    """Return every contacted candidate-domain face in deterministic order."""
    if eta_count <= 0 or rho_count <= 0 or not support_indices:
        raise ValueError("support and positive candidate-grid dimensions are required")
    if any(
        eta_index < 0 or eta_index >= eta_count or rho_index < 0 or rho_index >= rho_count
        for eta_index, rho_index in support_indices
    ):
        raise ValueError("support index lies outside the candidate grid")
    contacted = (
        ("rho_min", any(rho_index == 0 for _, rho_index in support_indices)),
        (
            "rho_max",
            any(rho_index == rho_count - 1 for _, rho_index in support_indices),
        ),
        ("eta_min", any(eta_index == 0 for eta_index, _ in support_indices)),
        (
            "eta_max",
            any(eta_index == eta_count - 1 for eta_index, _ in support_indices),
        ),
    )
    return tuple(name for name, is_contacted in contacted if is_contacted)


def generate_truth_block(
    fixed: goal007.FixedInputs,
    seed: goal007.StreamSeedRecord,
    truth_cells: tuple[TruthCell, ...] = TRUTH_CELLS,
) -> tuple[tuple[TruthCell, ContrastSpreadTruth], ...]:
    """Generate all paired truth cells from one complete edge-shock block."""
    shocks = sample_edge_shock_vector(
        fixed.landscape,
        goal007.generator_from_seed_record(seed),
    )
    eta_truths = {
        eta: compute_contrast_spread(
            fixed.landscape,
            eta,
            edge_shocks=shocks,
            rho=1.0,
        )
        for eta in dict.fromkeys(cell.eta for cell in truth_cells)
    }
    return tuple(
        (
            cell,
            replace(
                eta_truths[cell.eta],
                arrival=eta_truths[cell.eta].arrival / cell.rho,
                rho=cell.rho,
            ),
        )
        for cell in truth_cells
    )


def generate_cell_observations(
    fixed: goal007.FixedInputs,
    truth: ContrastSpreadTruth,
) -> tuple[tuple[Any, ...], tuple[CollapsedObservation, ...]]:
    """Generate and collapse Goal 007's perfect duplicate-visit observations."""
    analyst = generate_perfect_observations(fixed.design.sites, truth)
    return analyst, collapse_duplicate_visits(analyst)


def classify_cell(
    *,
    topology_success_count: int,
    validation_count: int,
    calibrated_coverage: EstimateInterval,
    median_absolute_log_rho_error: float,
    median_absolute_eta_error: float,
    median_projected_log_rho_width: float,
    median_projected_eta_width: float,
    paired_brier_interval: EstimateInterval,
) -> str:
    """Apply Goal 007's thresholds with Goal 008 cell-class names."""
    inherited = goal007.classify_downstream(
        topology_success_count=topology_success_count,
        validation_count=validation_count,
        calibrated_coverage=calibrated_coverage,
        median_absolute_log_rho_error=median_absolute_log_rho_error,
        median_absolute_eta_error=median_absolute_eta_error,
        median_projected_log_rho_width=median_projected_log_rho_width,
        median_projected_eta_width=median_projected_eta_width,
        paired_brier_interval=paired_brier_interval,
    )
    return {
        "joint_design_limited": "cell_joint_design_limited",
        "joint_local_calibration_not_ready": "cell_joint_local_calibration_not_ready",
        "joint_recovery_imprecise": "cell_joint_recovery_imprecise",
        "joint_recoverable_neutral_better": "cell_joint_neutral_better",
        "advance_to_joint_cross_truth_perfect_detection": "cell_joint_recoverable",
        "joint_recoverable_mechanism_inconclusive": "cell_joint_mechanism_inconclusive",
    }[inherited]


def classify_overall(
    invariants: Mapping[str, bool],
    cell_bank_classes: Mapping[str, Mapping[str, str]],
) -> str:
    """Apply implementation, bank-stability, and worst-full-cell precedence."""
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
        ("cell_joint_design_limited", "joint_cross_truth_design_limited"),
        (
            "cell_joint_local_calibration_not_ready",
            "joint_cross_truth_local_calibration_not_ready",
        ),
        ("cell_joint_recovery_imprecise", "joint_cross_truth_recovery_imprecise"),
        ("cell_joint_neutral_better", "joint_cross_truth_neutral_better"),
        (
            "cell_joint_mechanism_inconclusive",
            "joint_cross_truth_mechanism_inconclusive",
        ),
    )
    for cell_class, outcome in precedence:
        if cell_class in full_classes:
            return outcome
    if full_classes == {"cell_joint_recoverable"}:
        return "advance_to_joint_imperfect_detection"
    return "implementation_blocked"


def run_truth_cell(
    cell: TruthCell,
    config: Goal008Config = DEFAULT_CONFIG,
) -> CellResult:
    """Run one literal truth-cell task without writing campaign artifacts."""
    if cell not in config.truth_cells:
        raise ValueError("truth cell is not part of this Goal 008 configuration")
    fixed = goal007.build_fixed_inputs()
    manifest = spawn_seed_manifest(config)
    inherited_config = goal007_config(config)
    bank = goal007.build_integration_bank(
        fixed,
        manifest.integration_bank,
        config.etas,
    )
    variants = goal007.build_bank_variants(inherited_config, bank)
    calibration = _run_cell_calibration(
        cell,
        config,
        fixed,
        manifest.calibration,
        bank.site_ids,
        variants,
    )
    cutoffs = {
        bank_name: order_statistic_cutoff(
            tuple(row.lr_at_truth for row in calibration if row.bank_variant == bank_name),
            rank_one_based=config.calibration_rank_one_based,
        )
        for bank_name in BANK_VARIANT_NAMES
    }
    validation, representatives = _run_cell_validation(
        cell,
        config,
        fixed,
        manifest.validation,
        bank.site_ids,
        variants,
        cutoffs,
    )
    summaries = _aggregate_cell_banks(cell, config, variants, cutoffs, validation)
    seed_digest = _seed_manifest_digest(manifest)
    invariants = {
        **fixed.invariants,
        "truth_cell_membership": cell in config.truth_cells,
        "seed_manifest_replay": all(
            goal007.generator_from_seed_record(record) is not None
            for record in manifest.stream_records
        ),
        "integration_bank_shape": bank.arrivals.shape
        == (config.bank_size, len(config.etas), len(fixed.design.sites)),
        "integration_bank_finite": bool(
            np.isfinite(bank.arrivals).all() and (bank.arrivals >= 0.0).all()
        ),
        "bank_variants": tuple(variant.name for variant in variants) == BANK_VARIANT_NAMES,
        "category_weight_support": all(
            variant.weights.shape
            == (len(config.etas), len(config.rhos), len(fixed.design.sites), CATEGORY_COUNT)
            and np.isfinite(variant.weights).all()
            and (variant.weights > 0.0).all()
            for variant in variants
        ),
        "calibration_result_count": len(calibration)
        == len(BANK_VARIANT_NAMES) * config.calibration_blocks,
        "validation_result_count": len(validation)
        == len(BANK_VARIANT_NAMES) * config.validation_blocks,
        "local_cutoffs": all(
            row.cutoff_source_cell == row.truth_cell == cell.cell_id
            and row.cutoff_source_rho == row.truth_rho == cell.rho
            and row.cutoff_source_eta == row.truth_eta == cell.eta
            for row in calibration
        )
        and all(
            row.cutoff_source_cell == row.truth_cell == cell.cell_id
            and row.cutoff_source_rho == row.truth_rho == cell.rho
            and row.cutoff_source_eta == row.truth_eta == cell.eta
            for row in validation
        ),
        "perfect_observation_counts": all(
            row.analyst_record_count == 1920
            and row.distinct_outcome_count == 960
            and row.duplicate_visits_agree
            for row in calibration
        )
        and all(
            row.analyst_record_count == 1920
            and row.distinct_outcome_count == 960
            and row.training_outcome_count == 720
            and row.holdout_outcome_count == 240
            for row in validation
        ),
        "perfect_truth_mapping": all(row.perfect_truth_mapping for row in validation),
        "train_holdout_isolation": all(row.split_isolated for row in validation),
        "finite_likelihoods_and_scores": all(
            isfinite(row.lr_at_truth)
            and isfinite(row.truth_log_likelihood)
            and isfinite(row.maximum_log_likelihood)
            for row in calibration
        )
        and all(
            isfinite(row.lr_at_truth)
            and isfinite(row.truth_log_likelihood)
            and isfinite(row.maximum_log_likelihood)
            and isfinite(row.stochastic_log_score_minimum)
            and isfinite(row.stochastic_log_score_maximum)
            and isfinite(row.neutral_log_score)
            and isfinite(row.paired_brier_difference)
            for row in validation
        ),
        "mle_sets_preserved": all(row.mle_indices and row.mle_cells for row in calibration)
        and all(
            row.mle_indices
            and row.mle_cells
            and row.training_mle_indices
            and row.training_mle_cells
            for row in validation
        ),
        "calibrated_supports_preserved": all(
            row.support_indices
            and row.support_cell_count == len(row.support_indices)
            and row.support_component_count >= 1
            for row in validation
        ),
        "boundary_faces_reconciled": all(
            row.support_boundary_faces
            == support_boundary_faces(
                row.support_indices,
                eta_count=len(config.etas),
                rho_count=len(config.rhos),
            )
            and row.support_boundary_contact is bool(row.support_boundary_faces)
            for row in validation
        ),
        "representative_validation_zero": len(representatives) == 3
        and tuple(row.bank_variant for row in representatives) == BANK_VARIANT_NAMES
        and all(row.block_index == 0 for row in representatives),
        "separate_local_cutoffs": len(summaries) == 3
        and all(
            summary.cutoff.sample_size == config.calibration_blocks
            and summary.cutoff.rank_one_based == config.calibration_rank_one_based
            for summary in summaries
        ),
    }
    return CellResult(
        truth_cell=cell,
        calibration_results=calibration,
        validation_results=validation,
        representative_profiles=representatives,
        bank_summaries=summaries,
        seed_manifest_digest=seed_digest,
        invariants=invariants,
    )


def run_campaign(
    config: Goal008Config = DEFAULT_CONFIG,
    *,
    workers: int = 1,
) -> Goal008Result:
    """Run nine deterministic cell tasks and aggregate in frozen row-major order."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    _validate_production_runtime(config, workers)
    tasks = tuple((cell, config) for cell in config.truth_cells)
    if workers == 1:
        task_outputs = tuple(_run_truth_cell_task(task) for task in tasks)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            task_outputs = tuple(executor.map(_run_truth_cell_task, tasks))
    cell_results = tuple(output[0] for output in task_outputs)
    cell_telemetry = tuple(output[1] for output in task_outputs)
    execution_telemetry = CampaignExecutionTelemetry(
        worker_count=workers,
        thread_limits=_current_thread_limits(),
        campaign_exit_status=0,
        cell_telemetry=cell_telemetry,
    )
    manifest = spawn_seed_manifest(config)
    calibration = tuple(
        row for cell_result in cell_results for row in cell_result.calibration_results
    )
    validation = tuple(
        row for cell_result in cell_results for row in cell_result.validation_results
    )
    representatives = tuple(
        row for cell_result in cell_results for row in cell_result.representative_profiles
    )
    summaries = tuple(row for cell_result in cell_results for row in cell_result.bank_summaries)
    expected_seed_digest = _seed_manifest_digest(manifest)
    runtime_invariants = _runtime_invariants(config)
    central = _central_projection(
        config,
        calibration,
        validation,
        summaries,
        manifest,
        runtime_invariants,
    )
    cell_invariants = {
        result.truth_cell.cell_id: dict(result.invariants) for result in cell_results
    }
    invariants = {
        **runtime_invariants,
        "cell_result_order": tuple(result.truth_cell for result in cell_results)
        == config.truth_cells,
        "cell_invariants": all(
            all(cell_result.invariants.values()) for cell_result in cell_results
        ),
        "schedule_independent_seeds": all(
            cell_result.seed_manifest_digest == expected_seed_digest for cell_result in cell_results
        ),
        "complete_calibration_campaign": len(calibration)
        == 9 * len(BANK_VARIANT_NAMES) * config.calibration_blocks,
        "complete_validation_campaign": len(validation)
        == 9 * len(BANK_VARIANT_NAMES) * config.validation_blocks,
        "complete_summary_surface": len(summaries) == 9 * len(BANK_VARIANT_NAMES),
        "complete_representative_surface": len(representatives) == 9 * len(BANK_VARIANT_NAMES),
        "cell_processes_succeeded": len(cell_telemetry) == 9
        and all(row.exit_status == 0 for row in cell_telemetry),
        "stable_row_identity": len(
            {(row.phase, row.block_index, row.truth_cell, row.bank_variant) for row in calibration}
        )
        == len(calibration)
        and len(
            {(row.phase, row.block_index, row.truth_cell, row.bank_variant) for row in validation}
        )
        == len(validation),
        "central_reconciliation": not config.is_production
        or central.production_reference_match is True,
    }
    classes = {
        cell.cell_id: {
            summary.bank_variant: summary.downstream_class
            for summary in summaries
            if summary.truth_cell == cell.cell_id
        }
        for cell in config.truth_cells
    }
    outcome = classify_overall(invariants, classes)
    return Goal008Result(
        config=config,
        seed_manifest=manifest,
        calibration_results=calibration,
        validation_results=validation,
        representative_profiles=representatives,
        cell_bank_summaries=summaries,
        cell_invariants=cell_invariants,
        central_reconciliation=central,
        execution_telemetry=execution_telemetry,
        invariants=invariants,
        outcome=outcome,
    )


def central_projection(result: Goal008Result) -> CentralProjection:
    """Return the independently referenced central compatibility projection."""
    return result.central_reconciliation


def campaign_digest(result: Goal008Result) -> str:
    """Hash scientific content while intentionally excluding execution telemetry."""
    scientific_content = {
        field.name: getattr(result, field.name)
        for field in fields(result)
        if field.name != "execution_telemetry"
    }
    serializable, _ = diagnostic_json_value(scientific_content)
    payload = json.dumps(
        serializable,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _run_truth_cell_task(
    task: tuple[TruthCell, Goal008Config],
) -> tuple[CellResult, CellExecutionTelemetry]:
    cell, config = task
    started = time.perf_counter()
    result = run_truth_cell(cell, config)
    telemetry = CellExecutionTelemetry(
        truth_cell=cell.cell_id,
        exit_status=0,
        wall_time_seconds=time.perf_counter() - started,
        maximum_rss_bytes=_maximum_rss_bytes(),
    )
    return result, telemetry


def _generate_cell_truth(
    fixed: goal007.FixedInputs,
    seed: goal007.StreamSeedRecord,
    cell: TruthCell,
) -> ContrastSpreadTruth:
    shocks = sample_edge_shock_vector(
        fixed.landscape,
        goal007.generator_from_seed_record(seed),
    )
    base = compute_contrast_spread(
        fixed.landscape,
        cell.eta,
        edge_shocks=shocks,
        rho=1.0,
    )
    return replace(base, arrival=base.arrival / cell.rho, rho=cell.rho)


def _run_cell_calibration(
    cell: TruthCell,
    config: Goal008Config,
    fixed: goal007.FixedInputs,
    seeds: tuple[goal007.StreamSeedRecord, ...],
    site_ids: tuple[str, ...],
    variants: tuple[goal007.BankVariant, ...],
) -> tuple[CalibrationResult, ...]:
    rhos = np.asarray(config.rhos, dtype=np.float64)
    etas = np.asarray(config.etas, dtype=np.float64)
    rows: list[CalibrationResult] = []
    for seed in seeds:
        truth = _generate_cell_truth(fixed, seed, cell)
        analyst, collapsed = generate_cell_observations(fixed, truth)
        selected, categories = site_onset_categories(site_ids=site_ids, records=collapsed)
        for variant in variants:
            profile = joint_profile(
                weights=variant.weights,
                rhos=rhos,
                etas=etas,
                bank_site_ids=site_ids,
                history_site_ids=selected,
                onset_categories=categories,
                scope="all",
            )
            truth_log = float(profile.log_likelihoods[cell.eta_index, cell.rho_index])
            rows.append(
                CalibrationResult(
                    phase="calibration",
                    block_index=seed.index,
                    pairing_group=_pairing_group("calibration", seed.index),
                    truth_cell=cell.cell_id,
                    truth_rho=cell.rho,
                    truth_eta=cell.eta,
                    truth_rho_index=cell.rho_index,
                    truth_eta_index=cell.eta_index,
                    bank_variant=variant.name,
                    cutoff_source_cell=cell.cell_id,
                    cutoff_source_rho=cell.rho,
                    cutoff_source_eta=cell.eta,
                    analyst_record_count=len(analyst),
                    distinct_outcome_count=len(collapsed),
                    duplicate_visits_agree=len(analyst) == 2 * len(collapsed),
                    lr_at_truth=max(
                        0.0,
                        2.0 * (profile.maximum_log_likelihood - truth_log),
                    ),
                    truth_log_likelihood=truth_log,
                    maximum_log_likelihood=profile.maximum_log_likelihood,
                    mle_indices=profile.mle_indices,
                    mle_cells=profile.mle_cells,
                )
            )
    return tuple(rows)


def _run_cell_validation(
    cell: TruthCell,
    config: Goal008Config,
    fixed: goal007.FixedInputs,
    seeds: tuple[goal007.StreamSeedRecord, ...],
    site_ids: tuple[str, ...],
    variants: tuple[goal007.BankVariant, ...],
    cutoffs: dict[str, CutoffResult],
) -> tuple[tuple[ValidationResult, ...], tuple[RepresentativeProfile, ...]]:
    rhos = np.asarray(config.rhos, dtype=np.float64)
    etas = np.asarray(config.etas, dtype=np.float64)
    rows: list[ValidationResult] = []
    representatives: list[RepresentativeProfile] = []
    for seed in seeds:
        truth = _generate_cell_truth(fixed, seed, cell)
        analyst, collapsed = generate_cell_observations(fixed, truth)
        training = tuple(record for record in collapsed if record.split == "training")
        holdout = tuple(record for record in collapsed if record.split == "holdout")
        full_sites, full_categories = site_onset_categories(
            site_ids=site_ids,
            records=collapsed,
        )
        training_sites, training_categories = site_onset_categories(
            site_ids=site_ids,
            records=training,
        )
        neutral = fit_time_stratified_baseline(training, survey_times=SURVEY_TIMES)
        neutral_score = score_time_stratified_baseline(neutral, holdout)
        neutral_probabilities = tuple(value for _, value in neutral.probabilities)
        split_isolated = {record.cluster_id for record in training}.isdisjoint(
            {record.cluster_id for record in holdout}
        )
        perfect_mapping = all(
            record.detected == int(truth.arrival[record.row, record.col] <= record.time)
            for record in collapsed
        )
        for variant in variants:
            full_profile = joint_profile(
                weights=variant.weights,
                rhos=rhos,
                etas=etas,
                bank_site_ids=site_ids,
                history_site_ids=full_sites,
                onset_categories=full_categories,
                scope="all",
            )
            support = summarize_joint_profile(
                full_profile,
                cutoff=cutoffs[variant.name].cutoff,
                truth_rho=cell.rho,
                truth_eta=cell.eta,
            )
            boundary_faces = support_boundary_faces(
                support.support_indices,
                eta_count=len(config.etas),
                rho_count=len(config.rhos),
            )
            if support.support_boundary_contact is not bool(boundary_faces):
                raise RuntimeError("support boundary boolean and face set disagree")
            training_profile = joint_profile(
                weights=variant.weights,
                rhos=rhos,
                etas=etas,
                bank_site_ids=site_ids,
                history_site_ids=training_sites,
                onset_categories=training_categories,
                scope="training",
            )
            process_scores = tuple(
                score_predictions(
                    record_occupancy_probabilities(
                        weights=variant.weights[eta_index, rho_index],
                        site_ids=site_ids,
                        records=holdout,
                    ),
                    holdout,
                )
                for eta_index, rho_index in training_profile.mle_indices
            )
            predictive = goal007.summarize_predictive_comparison(
                process_scores,
                neutral_score,
                neutral_probability_minimum=min(neutral_probabilities),
                neutral_probability_maximum=max(neutral_probabilities),
            )
            truth_log = float(full_profile.log_likelihoods[cell.eta_index, cell.rho_index])
            rows.append(
                ValidationResult(
                    phase="validation",
                    block_index=seed.index,
                    pairing_group=_pairing_group("validation", seed.index),
                    truth_cell=cell.cell_id,
                    truth_rho=cell.rho,
                    truth_eta=cell.eta,
                    truth_rho_index=cell.rho_index,
                    truth_eta_index=cell.eta_index,
                    bank_variant=variant.name,
                    cutoff_source_cell=cell.cell_id,
                    cutoff_source_rho=cell.rho,
                    cutoff_source_eta=cell.eta,
                    analyst_record_count=len(analyst),
                    distinct_outcome_count=len(collapsed),
                    training_outcome_count=len(training),
                    holdout_outcome_count=len(holdout),
                    split_isolated=split_isolated,
                    perfect_truth_mapping=perfect_mapping,
                    lr_at_truth=max(
                        0.0,
                        2.0 * (full_profile.maximum_log_likelihood - truth_log),
                    ),
                    truth_log_likelihood=truth_log,
                    maximum_log_likelihood=full_profile.maximum_log_likelihood,
                    truth_included=support.truth_included,
                    support_cell_count=support.support_cell_count,
                    support_component_count=support.support_component_count,
                    support_boundary_contact=support.support_boundary_contact,
                    support_boundary_faces=boundary_faces,
                    projected_log_rho_width=support.projected_log_rho_width,
                    projected_eta_width=support.projected_eta_width,
                    support_indices=support.support_indices,
                    support_correlation=support.support_correlation,
                    support_correlation_reason=support.support_correlation_reason,
                    mle_indices=support.mle_indices,
                    mle_cells=support.mle_cells,
                    minimum_absolute_log_rho_error=support.minimum_absolute_log_rho_error,
                    minimum_absolute_eta_error=support.minimum_absolute_eta_error,
                    training_mle_indices=training_profile.mle_indices,
                    training_mle_cells=training_profile.mle_cells,
                    stochastic_log_score_minimum=predictive.stochastic_log_score_minimum,
                    stochastic_log_score_maximum=predictive.stochastic_log_score_maximum,
                    stochastic_brier_minimum=predictive.stochastic_brier_minimum,
                    stochastic_brier_maximum=predictive.stochastic_brier_maximum,
                    stochastic_probability_minimum=(predictive.stochastic_probability_minimum),
                    stochastic_probability_maximum=(predictive.stochastic_probability_maximum),
                    neutral_log_score=predictive.neutral_log_score,
                    neutral_brier_score=predictive.neutral_brier_score,
                    neutral_probability_minimum=predictive.neutral_probability_minimum,
                    neutral_probability_maximum=predictive.neutral_probability_maximum,
                    paired_brier_difference=predictive.paired_brier_difference,
                )
            )
            if seed.index == 0:
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
                        cutoff=cutoffs[variant.name].cutoff,
                        profile=full_profile,
                        summary=support,
                    )
                )
    return tuple(rows), tuple(representatives)


def _aggregate_cell_banks(
    cell: TruthCell,
    config: Goal008Config,
    variants: tuple[goal007.BankVariant, ...],
    cutoffs: dict[str, CutoffResult],
    validation: tuple[ValidationResult, ...],
) -> tuple[CellBankSummary, ...]:
    summaries: list[CellBankSummary] = []
    for variant in variants:
        rows = tuple(row for row in validation if row.bank_variant == variant.name)
        coverage_count = sum(row.truth_included for row in rows)
        topology_count = sum(
            row.support_component_count == 1 and not row.support_boundary_contact for row in rows
        )
        coverage = wilson_interval(coverage_count, len(rows))
        brier = normal_mean_interval(tuple(row.paired_brier_difference for row in rows))
        rho_error = float(median(row.minimum_absolute_log_rho_error for row in rows))
        eta_error = float(median(row.minimum_absolute_eta_error for row in rows))
        rho_width = float(median(row.projected_log_rho_width for row in rows))
        eta_width = float(median(row.projected_eta_width for row in rows))
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
                cutoff=cutoffs[variant.name],
                coverage_success_count=coverage_count,
                calibrated_coverage=coverage,
                topology_success_count=topology_count,
                topology_success_proportion=topology_count / len(rows),
                boundary_contact_count=sum(row.support_boundary_contact for row in rows),
                rho_min_contact_count=sum("rho_min" in row.support_boundary_faces for row in rows),
                rho_max_contact_count=sum("rho_max" in row.support_boundary_faces for row in rows),
                eta_min_contact_count=sum("eta_min" in row.support_boundary_faces for row in rows),
                eta_max_contact_count=sum("eta_max" in row.support_boundary_faces for row in rows),
                median_minimum_absolute_log_rho_error=rho_error,
                median_minimum_absolute_eta_error=eta_error,
                median_projected_log_rho_width=rho_width,
                median_projected_eta_width=eta_width,
                median_support_cell_count=float(median(row.support_cell_count for row in rows)),
                mean_mle_set_size=fmean(len(row.mle_indices) for row in rows),
                paired_brier_interval=brier,
                mean_stochastic_brier_worst_mle=fmean(row.stochastic_brier_maximum for row in rows),
                mean_neutral_brier=fmean(row.neutral_brier_score for row in rows),
                finite_log_score_count=sum(
                    isfinite(row.stochastic_log_score_minimum)
                    and isfinite(row.stochastic_log_score_maximum)
                    and isfinite(row.neutral_log_score)
                    for row in rows
                ),
                downstream_class=classify_cell(
                    topology_success_count=topology_count,
                    validation_count=len(rows),
                    calibrated_coverage=coverage,
                    median_absolute_log_rho_error=rho_error,
                    median_absolute_eta_error=eta_error,
                    median_projected_log_rho_width=rho_width,
                    median_projected_eta_width=eta_width,
                    paired_brier_interval=brier,
                ),
            )
        )
    return tuple(summaries)


def _central_projection(
    config: Goal008Config,
    calibration: tuple[CalibrationResult, ...],
    validation: tuple[ValidationResult, ...],
    summaries: tuple[CellBankSummary, ...],
    manifest: goal007.SeedManifest,
    runtime_invariants: Mapping[str, bool],
) -> CentralProjection:
    central_calibration = tuple(row for row in calibration if row.truth_cell == "cell-04")
    central_validation = tuple(row for row in validation if row.truth_cell == "cell-04")
    central_summaries = tuple(row for row in summaries if row.truth_cell == "cell-04")
    projection_payloads = {
        "calibration": [_central_calibration_payload(row) for row in central_calibration],
        "validation": [_central_validation_payload(row) for row in central_validation],
        "bank": [_central_bank_payload(row) for row in central_summaries],
    }
    raw_hashes: dict[str, str | None] = {}
    structural_hashes: dict[str, str | None] = {}
    canonical_hashes: dict[str, str | None] = {}
    nonfinite_paths: list[str] = []
    for label, payload in projection_payloads.items():
        try:
            hashes = projection_hashes(payload)
        except ValueError:
            raw_hashes[label] = None
            structural_hashes[label] = None
            canonical_hashes[label] = None
            nonfinite_paths.extend(_nonfinite_paths(payload, path=f"$.{label}"))
        else:
            raw_hashes[label] = hashes.raw_sha256
            structural_hashes[label] = hashes.structural_sha256
            canonical_hashes[label] = hashes.canonical_sha256

    seed_manifest_sha256 = _projection_digest(_central_seed_payload(manifest))
    source_identity_sha256 = _projection_digest(SOURCE_IDENTITY)
    central_outcome = _central_outcome(central_summaries)
    observed: dict[str, object] = {
        "raw_hashes": raw_hashes,
        "structural_hashes": structural_hashes,
        "canonical_hashes": canonical_hashes,
        "seed_manifest_sha256": seed_manifest_sha256,
        "source_identity_sha256": source_identity_sha256,
        "source_identity": dict(SOURCE_IDENTITY),
        "outcome": central_outcome,
        "nonfinite_paths": tuple(nonfinite_paths),
    }
    if config.is_production:
        checks: dict[str, bool] = {
            "central_projection_finite": not nonfinite_paths,
            "seed_manifest_identity": (
                seed_manifest_sha256 == CENTRAL_REFERENCE["seed_manifest_sha256"]
            ),
            "source_identity": (
                source_identity_sha256 == CENTRAL_REFERENCE["source_identity_sha256"]
            ),
            "central_outcome": central_outcome == CENTRAL_REFERENCE["outcome"],
        }
        checks.update(
            {
                f"{label}_structure": (structural_hashes[label] == CENTRAL_STRUCTURAL_HASHES[label])
                for label in projection_payloads
            }
        )
        checks.update(
            {
                f"{label}_canonical": (canonical_hashes[label] == CENTRAL_CANONICAL_HASHES[label])
                for label in projection_payloads
            }
        )
        matched: bool | None = all(checks.values())
    else:
        checks = {}
        matched = None
    return CentralProjection(
        truth_cell="cell-04",
        calibration_rows=central_calibration,
        validation_rows=central_validation,
        bank_summaries=central_summaries,
        production_reference_checked=config.is_production,
        production_reference_match=matched,
        checks=checks,
        observed=observed,
        expected=dict(CENTRAL_REFERENCE),
        raw_hashes=raw_hashes,
        historical_raw_hashes=dict(CENTRAL_HISTORICAL_RAW_HASHES),
        structural_hashes=structural_hashes,
        canonical_hashes=canonical_hashes,
        canonicalization_rule=dict(CANONICALIZATION_RULE),
        nonfinite_paths=tuple(nonfinite_paths),
    )


def _central_calibration_payload(row: CalibrationResult) -> dict[str, object]:
    return {
        "phase": row.phase,
        "dataset_index": row.block_index,
        "bank_variant": row.bank_variant,
        "analyst_record_count": row.analyst_record_count,
        "distinct_outcome_count": row.distinct_outcome_count,
        "duplicate_visits_agree": row.duplicate_visits_agree,
        "truth_eta_index": row.truth_eta_index,
        "truth_rho_index": row.truth_rho_index,
        "lr_at_truth": row.lr_at_truth,
        "truth_log_likelihood": row.truth_log_likelihood,
        "maximum_log_likelihood": row.maximum_log_likelihood,
        "mle_indices": row.mle_indices,
        "mle_cells": row.mle_cells,
    }


def _central_validation_payload(row: ValidationResult) -> dict[str, object]:
    return {
        "phase": row.phase,
        "dataset_index": row.block_index,
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
        "support_indices": row.support_indices,
        "support_correlation": row.support_correlation,
        "support_correlation_reason": row.support_correlation_reason,
        "mle_indices": row.mle_indices,
        "mle_cells_rho_eta": row.mle_cells,
        "minimum_absolute_log_rho_error": row.minimum_absolute_log_rho_error,
        "minimum_absolute_eta_error": row.minimum_absolute_eta_error,
        "training_mle_indices": row.training_mle_indices,
        "training_mle_cells_rho_eta": row.training_mle_cells,
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
    }


def _central_bank_payload(row: CellBankSummary) -> dict[str, object]:
    return {
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
        "mean_stochastic_brier_worst_mle": row.mean_stochastic_brier_worst_mle,
        "mean_neutral_brier": row.mean_neutral_brier,
        "finite_log_score_count": row.finite_log_score_count,
        "downstream_class": {
            "cell_joint_recoverable": ("advance_to_joint_cross_truth_perfect_detection")
        }.get(row.downstream_class, row.downstream_class),
    }


def _central_seed_payload(
    manifest: goal007.SeedManifest,
) -> list[dict[str, object]]:
    return [
        {
            "phase": record.phase,
            "index": record.index,
            "stream_role": record.stream_role,
            "entropy": record.entropy,
            "spawn_key": record.spawn_key,
            "state_words": record.state_words,
            "pool_size": record.pool_size,
            "bit_generator": "PCG64",
            "between_site_process_dependence": "omitted",
        }
        for record in manifest.stream_records
    ]


def _central_outcome(rows: tuple[CellBankSummary, ...]) -> str:
    classes = tuple(row.downstream_class for row in rows)
    if classes == ("cell_joint_recoverable",) * 3:
        return "advance_to_joint_cross_truth_perfect_detection"
    if len(classes) != 3 or len(set(classes)) != 1:
        return "likelihood_approximation_unstable"
    return classes[0] if classes else "implementation_blocked"


def projection_hashes(payload: object) -> ProjectionHashes:
    """Return raw, exact-structure, and nine-decimal projection hashes."""
    canonical = _canonical_projection_value(payload)
    return ProjectionHashes(
        raw_sha256=_projection_digest(payload),
        structural_sha256=_projection_digest(_structural_projection_value(payload)),
        canonical_sha256=_projection_digest(canonical),
    )


def _projection_digest(payload: object) -> str:
    encoded = json.dumps(
        _canonical_value(payload),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _seed_manifest_digest(manifest: goal007.SeedManifest) -> str:
    return _projection_digest(manifest)


def _pairing_group(phase: str, block_index: int) -> str:
    return f"{phase}-block-{block_index:03d}"


def _current_thread_limits() -> dict[str, str]:
    return {name: os.environ.get(name, "") for name in THREAD_LIMIT_NAMES}


def _validate_production_runtime(config: Goal008Config, workers: int) -> None:
    if not config.is_production:
        return
    if workers != 9:
        raise ValueError("production campaign requires exactly 9 workers")
    expected = {name: "1" for name in THREAD_LIMIT_NAMES}
    if _current_thread_limits() != expected:
        raise ValueError("production campaign requires all four thread limits set to 1")


def _maximum_rss_bytes() -> int:
    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    multiplier = 1 if sys.platform == "darwin" else 1024
    return max(1, int(maximum * multiplier))


def _runtime_invariants(config: Goal008Config) -> dict[str, bool]:
    return {
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
    }


def _canonical_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _canonical_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, np.ndarray):
        return _canonical_value(value.tolist())
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def _canonical_projection_value(value: object, *, path: str = "$") -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical_projection_value(
                getattr(value, field.name),
                path=_mapping_path(path, field.name),
            )
            for field in fields(value)
        }
    if isinstance(value, np.ndarray):
        return _canonical_projection_value(value.tolist(), path=path)
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_projection_value(
                item,
                path=_mapping_path(path, str(key)),
            )
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [
            _canonical_projection_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"non-finite projection value at {path}")
        rounded = round(value, 9)
        return 0.0 if rounded == 0.0 else rounded
    return value


def _structural_projection_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _structural_projection_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, np.ndarray):
        return _structural_projection_value(value.tolist())
    if isinstance(value, Mapping):
        return {
            str(key): _structural_projection_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_structural_projection_value(item) for item in value]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return {"__finite_float__": True}
    return value


def diagnostic_json_value(
    value: object,
) -> tuple[object, tuple[dict[str, str], ...]]:
    """Convert a result payload to strict JSON and enumerate tagged non-finites."""
    nonfinite_values: list[dict[str, str]] = []

    def convert(item: object, path: str) -> object:
        if is_dataclass(item) and not isinstance(item, type):
            return {
                field.name: convert(
                    getattr(item, field.name),
                    _mapping_path(path, field.name),
                )
                for field in fields(item)
            }
        if isinstance(item, np.ndarray):
            return convert(item.tolist(), path)
        if isinstance(item, Mapping):
            return {
                str(key): convert(value, _mapping_path(path, str(key)))
                for key, value in sorted(item.items(), key=lambda pair: str(pair[0]))
            }
        if isinstance(item, (tuple, list)):
            return [convert(value, f"{path}[{index}]") for index, value in enumerate(item)]
        if isinstance(item, np.bool_):
            return bool(item)
        if isinstance(item, np.integer):
            return int(item)
        if isinstance(item, np.floating):
            item = float(item)
        if isinstance(item, float) and not isfinite(item):
            if np.isnan(item):
                tag = NONFINITE_TAGS["nan"]
            elif item > 0.0:
                tag = NONFINITE_TAGS["positive_infinity"]
            else:
                tag = NONFINITE_TAGS["negative_infinity"]
            nonfinite_values.append({"path": path, "tag": tag})
            return tag
        return item

    return convert(value, "$"), tuple(nonfinite_values)


def _nonfinite_paths(value: object, *, path: str = "$") -> tuple[str, ...]:
    return tuple(row["path"] for row in nonfinite_value_evidence(value, path=path))


def nonfinite_value_evidence(
    value: object,
    *,
    path: str = "$",
) -> tuple[dict[str, str], ...]:
    """Return tagged paths for non-finite float leaves without copying the payload."""
    rows: list[dict[str, str]] = []

    def scan(item: object, item_path: str) -> None:
        if is_dataclass(item) and not isinstance(item, type):
            for field in fields(item):
                scan(
                    getattr(item, field.name),
                    _mapping_path(item_path, field.name),
                )
            return
        if isinstance(item, np.ndarray):
            scan(item.tolist(), item_path)
            return
        if isinstance(item, Mapping):
            for key, nested in sorted(item.items(), key=lambda pair: str(pair[0])):
                scan(nested, _mapping_path(item_path, str(key)))
            return
        if isinstance(item, (tuple, list)):
            for index, nested in enumerate(item):
                scan(nested, f"{item_path}[{index}]")
            return
        if isinstance(item, np.floating):
            item = float(item)
        if isinstance(item, float) and not isfinite(item):
            if np.isnan(item):
                tag = NONFINITE_TAGS["nan"]
            elif item > 0.0:
                tag = NONFINITE_TAGS["positive_infinity"]
            else:
                tag = NONFINITE_TAGS["negative_infinity"]
            rows.append({"path": item_path, "tag": tag})

    scan(value, path)
    return tuple(rows)


def _mapping_path(path: str, key: str) -> str:
    if key.isidentifier():
        return f"{path}.{key}"
    return f"{path}[{json.dumps(key)}]"
