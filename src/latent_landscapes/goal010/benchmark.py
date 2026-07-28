"""Boundary-aware joint rho-eta identifiability diagnosis."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import resource
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from math import ceil, isfinite
from pathlib import Path
from typing import Any

import numpy as np

from latent_landscapes.goal002.calibration import EstimateInterval, normal_mean_interval
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal008 import benchmark as goal008

THREAD_LIMIT_NAMES = goal008.THREAD_LIMIT_NAMES
BANK_VARIANT_NAMES = goal008.BANK_VARIANT_NAMES
SELECTED_CELL_IDS = ("cell-06", "cell-07", "cell-08")
EXPANDED_ETA_VALUES = (2.25, 2.5)
PUBLISHED_GOAL009_RUN_ID = "goal009-20260727T093142Z-9cb53de"
PUBLISHED_GOAL009_SOURCE_COMMIT = "9cb53dea4fc671cf22d52404b6845a6388000874"
PUBLISHED_GOAL009_OUTCOME = "joint_cross_truth_design_limited"
PUBLISHED_GOAL009_VERIFICATION_SHA256 = (
    "ca7a7b2f95688d91243509b148d20ef07fd1ebe30509245231af6e2c43d7ea9a"
)

GOAL009_FILES = (
    "config.json",
    "compute_provenance.json",
    "seed_manifest.csv",
    "truth_cell_summary.csv",
    "calibration_results.csv",
    "validation_results.csv",
    "predictive_summary.csv",
    "representative_profiles.csv",
    "central_reconciliation.json",
    "summary.json",
    "verification.json",
    "review.md",
    "visuals/truth_grid_recovery.svg",
    "visuals/truth_grid_calibration.svg",
    "visuals/truth_grid_ridge.svg",
    "visuals/truth_grid_predictive.svg",
)

SEED_FIELDS = (
    "phase",
    "block_index",
    "pairing_group",
    "stream_role",
    "entropy",
    "spawn_key",
    "state_words",
    "pool_size",
    "truth_cells_reusing_stream",
)
SUMMARY_FIELDS = (
    "truth_cell",
    "truth_rho",
    "truth_eta",
    "truth_rho_index",
    "truth_eta_index",
    "bank_variant",
    "cutoff_source_cell",
    "cutoff_source_rho",
    "cutoff_source_eta",
    "draw_count",
    "calibrated_cutoff",
    "cutoff_rank_one_based",
    "cutoff_sample_size",
    "coverage_success_count",
    "coverage_estimate",
    "coverage_lower",
    "coverage_upper",
    "topology_success_count",
    "topology_success_proportion",
    "boundary_contact_count",
    "rho_min_contact_count",
    "rho_max_contact_count",
    "eta_min_contact_count",
    "eta_max_contact_count",
    "median_minimum_absolute_log_rho_error",
    "median_minimum_absolute_eta_error",
    "median_projected_log_rho_width",
    "median_projected_eta_width",
    "median_support_cell_count",
    "mean_mle_set_size",
    "paired_brier_estimate",
    "paired_brier_lower",
    "paired_brier_upper",
    "downstream_class",
)
CALIBRATION_FIELDS = (
    "phase",
    "block_index",
    "pairing_group",
    "truth_cell",
    "truth_rho",
    "truth_eta",
    "truth_rho_index",
    "truth_eta_index",
    "bank_variant",
    "cutoff_source_cell",
    "cutoff_source_rho",
    "cutoff_source_eta",
    "analyst_record_count",
    "distinct_outcome_count",
    "duplicate_visits_agree",
    "lr_at_truth",
    "truth_log_likelihood",
    "maximum_log_likelihood",
    "mle_indices",
    "mle_cells_rho_eta",
    "mle_set_size",
)
VALIDATION_FIELDS = (
    "phase",
    "block_index",
    "pairing_group",
    "truth_cell",
    "truth_rho",
    "truth_eta",
    "truth_rho_index",
    "truth_eta_index",
    "bank_variant",
    "cutoff_source_cell",
    "cutoff_source_rho",
    "cutoff_source_eta",
    "analyst_record_count",
    "distinct_outcome_count",
    "training_outcome_count",
    "holdout_outcome_count",
    "split_isolated",
    "perfect_truth_mapping",
    "lr_at_truth",
    "truth_log_likelihood",
    "maximum_log_likelihood",
    "truth_included",
    "support_cell_count",
    "support_component_count",
    "support_boundary_contact",
    "support_boundary_faces",
    "projected_log_rho_width",
    "projected_eta_width",
    "support_indices",
    "support_correlation",
    "support_correlation_reason",
    "mle_indices",
    "mle_cells_rho_eta",
    "mle_set_size",
    "minimum_absolute_log_rho_error",
    "minimum_absolute_eta_error",
    "training_mle_indices",
    "training_mle_cells_rho_eta",
    "training_mle_set_size",
    "stochastic_log_score_minimum",
    "stochastic_log_score_maximum",
    "stochastic_brier_minimum",
    "stochastic_brier_maximum",
    "stochastic_probability_minimum",
    "stochastic_probability_maximum",
    "neutral_log_score",
    "neutral_brier_score",
    "neutral_probability_minimum",
    "neutral_probability_maximum",
    "paired_brier_difference",
)
PREDICTIVE_FIELDS = (
    "truth_cell",
    "truth_rho",
    "truth_eta",
    "truth_rho_index",
    "truth_eta_index",
    "bank_variant",
    "validation_block_count",
    "worst_tied_process_mle_rule",
    "mean_stochastic_brier_worst_mle",
    "mean_neutral_brier",
    "paired_brier_estimate",
    "paired_brier_lower",
    "paired_brier_upper",
    "finite_log_score_count",
    "training_outcome_count_per_dataset",
    "holdout_outcome_count_per_dataset",
)
PROFILE_FIELDS = (
    "truth_cell",
    "truth_rho",
    "truth_eta",
    "truth_rho_index",
    "truth_eta_index",
    "cutoff_source_cell",
    "cutoff_source_rho",
    "cutoff_source_eta",
    "block_index",
    "bank_variant",
    "candidate_rho",
    "candidate_eta",
    "candidate_rho_index",
    "candidate_eta_index",
    "likelihood_ratio",
    "in_support",
    "is_mle",
    "is_truth",
)


@dataclass(frozen=True, slots=True)
class Goal010Config:
    """The one deliberate candidate-domain change and its execution scale."""

    master_seed: int = goal008.MASTER_SEED
    bank_size: int = goal008.INTEGRATION_BANK_SIZE
    calibration_blocks: int = goal008.CALIBRATION_BLOCKS
    validation_blocks: int = goal008.VALIDATION_BLOCKS
    calibration_rank_one_based: int = goal008.CALIBRATION_RANK_ONE_BASED
    rhos: tuple[float, ...] = goal008.FROZEN_RHO_GRID
    original_etas: tuple[float, ...] = goal008.FROZEN_ETA_GRID
    expanded_etas: tuple[float, ...] = (*goal008.FROZEN_ETA_GRID, *EXPANDED_ETA_VALUES)
    all_truth_cells: tuple[goal008.TruthCell, ...] = goal008.TRUTH_CELLS
    selected_cell_ids: tuple[str, ...] = SELECTED_CELL_IDS

    def __post_init__(self) -> None:
        if self.bank_size < 2 or self.bank_size % 2:
            raise ValueError("integration bank size must be positive and even")
        if self.calibration_blocks <= 0 or self.validation_blocks <= 0:
            raise ValueError("block counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_blocks:
            raise ValueError("calibration rank must lie within calibration blocks")
        if self.expanded_etas != (*self.original_etas, *EXPANDED_ETA_VALUES):
            raise ValueError("expanded eta grid must append only 2.25 and 2.5")
        if self.selected_cell_ids != SELECTED_CELL_IDS:
            raise ValueError("Goal 010 requires cells 06-08 in frozen order")
        if tuple(cell.cell_id for cell in self.all_truth_cells) != tuple(
            f"cell-{index:02d}" for index in range(9)
        ):
            raise ValueError("all truth cells must retain the frozen row-major identity")
        selected = self.selected_cells
        if tuple((cell.rho, cell.eta) for cell in selected) != (
            (0.5, 1.5),
            (1.0, 1.5),
            (2.0, 1.5),
        ):
            raise ValueError("selected cells must retain the three high-eta truths")
        goal008.Goal008Config(
            master_seed=self.master_seed,
            bank_size=self.bank_size,
            calibration_blocks=self.calibration_blocks,
            validation_blocks=self.validation_blocks,
            calibration_rank_one_based=self.calibration_rank_one_based,
            rhos=self.rhos,
            etas=self.original_etas,
            truth_cells=self.all_truth_cells,
        )
        goal008.Goal008Config(
            master_seed=self.master_seed,
            bank_size=self.bank_size,
            calibration_blocks=self.calibration_blocks,
            validation_blocks=self.validation_blocks,
            calibration_rank_one_based=self.calibration_rank_one_based,
            rhos=self.rhos,
            etas=self.expanded_etas,
            truth_cells=self.all_truth_cells,
        )

    @property
    def selected_cells(self) -> tuple[goal008.TruthCell, ...]:
        by_id = {cell.cell_id: cell for cell in self.all_truth_cells}
        try:
            return tuple(by_id[cell_id] for cell_id in self.selected_cell_ids)
        except KeyError as error:
            raise ValueError("selected truth cell is absent") from error

    @property
    def is_production(self) -> bool:
        return self == DEFAULT_CONFIG


DEFAULT_CONFIG = Goal010Config()


@dataclass(frozen=True, slots=True)
class Goal009Pack:
    """Strictly authenticated Goal 009 scientific-pack evidence."""

    config: dict[str, object]
    compute_provenance: dict[str, object]
    summary: dict[str, object]
    verification: dict[str, object]
    seed_rows: tuple[dict[str, str], ...]
    summary_rows: tuple[dict[str, str], ...]
    calibration_rows: tuple[dict[str, str], ...]
    validation_rows: tuple[dict[str, str], ...]
    predictive_rows: tuple[dict[str, str], ...]
    profile_rows: tuple[dict[str, str], ...]
    truth_cell_order: tuple[str, ...]
    bank_order: tuple[str, ...]
    outcome: str
    verification_sha256: str
    all_invariants_pass: bool
    is_published_goal009: bool


@dataclass(frozen=True, slots=True)
class BaselineBoundaryAnatomy:
    truth_cell: str
    truth_rho: float
    truth_eta: float
    bank_variant: str
    calibrated_cutoff: float
    coverage_success_count: int
    coverage_estimate: float
    coverage_lower: float
    coverage_upper: float
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
    paired_brier_estimate: float
    paired_brier_lower: float
    paired_brier_upper: float
    downstream_class: str


@dataclass(frozen=True, slots=True)
class IntegrationBankReplay:
    old_slices_equal: bool
    seed_manifest_equal: bool
    site_ids_equal: bool
    new_slices_finite_nonnegative: bool
    fixed_process_invariants_pass: bool
    old_bank_sha256: str
    expanded_old_slices_sha256: str
    expanded_new_slices_sha256: str

    @property
    def all_pass(self) -> bool:
        return (
            self.old_slices_equal
            and self.seed_manifest_equal
            and self.site_ids_equal
            and self.new_slices_finite_nonnegative
            and self.fixed_process_invariants_pass
        )


@dataclass(frozen=True, slots=True)
class PairedBoundaryTransition:
    block_index: int
    truth_cell: str
    bank_variant: str
    original_cutoff: float
    expanded_cutoff: float
    original_truth_included: bool
    expanded_truth_included: bool
    original_support_component_count: int
    expanded_support_component_count: int
    original_support_boundary_faces: tuple[str, ...]
    expanded_support_boundary_faces: tuple[str, ...]
    original_connected_interior: bool
    expanded_connected_interior: bool
    original_projected_log_rho_width: float
    expanded_projected_log_rho_width: float
    original_projected_eta_width: float
    expanded_projected_eta_width: float
    original_minimum_absolute_log_rho_error: float
    expanded_minimum_absolute_log_rho_error: float
    original_minimum_absolute_eta_error: float
    expanded_minimum_absolute_eta_error: float
    original_support_indices: tuple[tuple[int, int], ...]
    expanded_support_indices: tuple[tuple[int, int], ...]
    original_support_correlation: float | None
    expanded_support_correlation: float | None
    original_mle_cells: tuple[tuple[float, float], ...]
    expanded_mle_cells: tuple[tuple[float, float], ...]
    original_training_mle_cells: tuple[tuple[float, float], ...]
    expanded_training_mle_cells: tuple[tuple[float, float], ...]
    original_paired_brier_difference: float
    expanded_paired_brier_difference: float

    @property
    def originally_contacted_eta_max(self) -> bool:
        return "eta_max" in self.original_support_boundary_faces

    @property
    def expanded_contacted_eta_max(self) -> bool:
        return "eta_max" in self.expanded_support_boundary_faces

    @property
    def expanded_eta_max_mle(self) -> bool:
        return any(eta == EXPANDED_ETA_VALUES[-1] for _, eta in self.expanded_mle_cells)


@dataclass(frozen=True, slots=True)
class DomainComparison:
    truth_cell: str
    bank_variant: str
    original_cutoff: float
    expanded_cutoff: float
    cutoff_difference: float
    original_topology_success_count: int
    expanded_topology_success_count: int
    topology_success_change: int
    paired_topology_change: EstimateInterval
    original_eta_max_contact_count: int
    expanded_eta_max_contact_count: int
    eta_max_contact_change: int
    expanded_eta_max_mle_count: int
    original_downstream_class: str
    expanded_downstream_class: str


@dataclass(frozen=True, slots=True)
class PrimaryBankDecisionEvidence:
    bank_variant: str
    original_eta_max_contact_count: int
    expanded_eta_max_contact_count: int
    topology_success_count: int
    downstream_class: str


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
class Goal010Result:
    config: Goal010Config
    baseline_pack: Goal009Pack
    baseline_anatomy: tuple[BaselineBoundaryAnatomy, ...]
    bank_replay: IntegrationBankReplay
    calibration_results: tuple[goal008.CalibrationResult, ...]
    validation_results: tuple[goal008.ValidationResult, ...]
    representative_profiles: tuple[goal008.RepresentativeProfile, ...]
    cell_bank_summaries: tuple[goal008.CellBankSummary, ...]
    paired_transitions: tuple[PairedBoundaryTransition, ...]
    domain_comparisons: tuple[DomainComparison, ...]
    execution_telemetry: CampaignExecutionTelemetry
    invariants: dict[str, bool]
    outcome: str


def smoke_config() -> Goal010Config:
    """Return a reduced configuration that still exercises the full eta append."""
    rhos = (0.5, 1.0, 2.0)
    original_etas = goal008.FROZEN_ETA_GRID
    cells = tuple(
        goal008.TruthCell(
            cell_id=f"cell-{eta_row * 3 + rho_column:02d}",
            rho=rho,
            eta=eta,
            rho_index=rhos.index(rho),
            eta_index=original_etas.index(eta),
        )
        for eta_row, eta in enumerate((0.5, 1.0, 1.5))
        for rho_column, rho in enumerate((0.5, 1.0, 2.0))
    )
    return Goal010Config(
        master_seed=goal008.MASTER_SEED,
        bank_size=2,
        calibration_blocks=2,
        validation_blocks=2,
        calibration_rank_one_based=2,
        rhos=rhos,
        original_etas=original_etas,
        expanded_etas=(*original_etas, *EXPANDED_ETA_VALUES),
        all_truth_cells=cells,
    )


def expanded_goal008_config(config: Goal010Config) -> goal008.Goal008Config:
    """Project Goal 010 onto Goal 008 without changing any frozen core API."""
    return goal008.Goal008Config(
        master_seed=config.master_seed,
        bank_size=config.bank_size,
        calibration_blocks=config.calibration_blocks,
        validation_blocks=config.validation_blocks,
        calibration_rank_one_based=config.calibration_rank_one_based,
        rhos=config.rhos,
        etas=config.expanded_etas,
        truth_cells=config.all_truth_cells,
    )


def read_goal009_pack(
    path: Path,
    *,
    require_published: bool = True,
) -> Goal009Pack:
    """Authenticate and reconcile a complete Goal 009 scientific pack."""
    if not path.is_dir():
        raise ValueError("Goal009 pack directory does not exist")
    observed = {item.relative_to(path).as_posix() for item in path.rglob("*") if item.is_file()}
    if any(item.is_symlink() for item in path.rglob("*")):
        raise ValueError("Goal009 pack must not contain symbolic links")
    if observed != set(GOAL009_FILES):
        raise ValueError("Goal009 pack does not match the exact 16-file contract")

    verification = _read_json_object(path / "verification.json")
    config = _read_json_object(path / "config.json")
    compute = _read_json_object(path / "compute_provenance.json")
    summary = _read_json_object(path / "summary.json")
    _read_json_object(path / "central_reconciliation.json")
    expected_hashes = verification.get("sha256")
    expected_hash_paths = set(GOAL009_FILES) - {"verification.json"}
    if not isinstance(expected_hashes, dict) or set(expected_hashes) != expected_hash_paths:
        raise ValueError("Goal009 verification hash surface is incomplete")
    for relative in sorted(expected_hash_paths):
        expected_hash = expected_hashes.get(relative)
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise ValueError("Goal009 verification contains an invalid hash")
        observed_hash = hashlib.sha256((path / relative).read_bytes()).hexdigest()
        if observed_hash != expected_hash:
            raise ValueError(f"Goal009 pack hash mismatch for {relative}")

    seed_rows = _read_csv(path / "seed_manifest.csv", SEED_FIELDS)
    summary_rows = _read_csv(path / "truth_cell_summary.csv", SUMMARY_FIELDS)
    calibration_rows = _read_csv(path / "calibration_results.csv", CALIBRATION_FIELDS)
    validation_rows = _read_csv(path / "validation_results.csv", VALIDATION_FIELDS)
    predictive_rows = _read_csv(path / "predictive_summary.csv", PREDICTIVE_FIELDS)
    profile_rows = _read_csv(path / "representative_profiles.csv", PROFILE_FIELDS)

    truth_cell_order, bank_order = _validate_goal009_tables(
        config=config,
        compute=compute,
        summary=summary,
        verification=verification,
        seed_rows=seed_rows,
        summary_rows=summary_rows,
        calibration_rows=calibration_rows,
        validation_rows=validation_rows,
        predictive_rows=predictive_rows,
        profile_rows=profile_rows,
    )
    outcome = _require_str(verification, "outcome")
    verification_sha256 = hashlib.sha256((path / "verification.json").read_bytes()).hexdigest()
    is_published = _is_published_goal009(
        config=config,
        compute=compute,
        verification=verification,
        verification_sha256=verification_sha256,
        summary_rows=summary_rows,
    )
    if require_published and not is_published:
        raise ValueError("pack does not match the published Goal009 identity")
    verification_invariants = verification.get("invariants")
    all_invariants = bool(
        summary.get("all_invariants_pass") is True
        and verification.get("all_invariants_pass") is True
        and verification.get("compute_provenance_validated") is True
        and isinstance(verification_invariants, dict)
        and all(value is True for value in verification_invariants.values())
    )
    if not all_invariants:
        raise ValueError("Goal009 pack declares failed invariants")
    return Goal009Pack(
        config=config,
        compute_provenance=compute,
        summary=summary,
        verification=verification,
        seed_rows=seed_rows,
        summary_rows=summary_rows,
        calibration_rows=calibration_rows,
        validation_rows=validation_rows,
        predictive_rows=predictive_rows,
        profile_rows=profile_rows,
        truth_cell_order=truth_cell_order,
        bank_order=bank_order,
        outcome=outcome,
        verification_sha256=verification_sha256,
        all_invariants_pass=True,
        is_published_goal009=is_published,
    )


def baseline_boundary_anatomy(
    pack: Goal009Pack,
) -> tuple[BaselineBoundaryAnatomy, ...]:
    """Summarize all 27 authenticated Goal 009 cell-bank rows."""
    return tuple(
        BaselineBoundaryAnatomy(
            truth_cell=row["truth_cell"],
            truth_rho=_finite_float(row["truth_rho"], "truth_rho"),
            truth_eta=_finite_float(row["truth_eta"], "truth_eta"),
            bank_variant=row["bank_variant"],
            calibrated_cutoff=_finite_float(row["calibrated_cutoff"], "calibrated_cutoff"),
            coverage_success_count=_integer(
                row["coverage_success_count"],
                "coverage_success_count",
            ),
            coverage_estimate=_finite_float(row["coverage_estimate"], "coverage_estimate"),
            coverage_lower=_finite_float(row["coverage_lower"], "coverage_lower"),
            coverage_upper=_finite_float(row["coverage_upper"], "coverage_upper"),
            topology_success_count=_integer(
                row["topology_success_count"], "topology_success_count"
            ),
            topology_success_proportion=_finite_float(
                row["topology_success_proportion"], "topology_success_proportion"
            ),
            boundary_contact_count=_integer(
                row["boundary_contact_count"], "boundary_contact_count"
            ),
            rho_min_contact_count=_integer(row["rho_min_contact_count"], "rho_min_contact_count"),
            rho_max_contact_count=_integer(row["rho_max_contact_count"], "rho_max_contact_count"),
            eta_min_contact_count=_integer(row["eta_min_contact_count"], "eta_min_contact_count"),
            eta_max_contact_count=_integer(row["eta_max_contact_count"], "eta_max_contact_count"),
            median_minimum_absolute_log_rho_error=_finite_float(
                row["median_minimum_absolute_log_rho_error"],
                "median_minimum_absolute_log_rho_error",
            ),
            median_minimum_absolute_eta_error=_finite_float(
                row["median_minimum_absolute_eta_error"],
                "median_minimum_absolute_eta_error",
            ),
            median_projected_log_rho_width=_finite_float(
                row["median_projected_log_rho_width"],
                "median_projected_log_rho_width",
            ),
            median_projected_eta_width=_finite_float(
                row["median_projected_eta_width"],
                "median_projected_eta_width",
            ),
            median_support_cell_count=_finite_float(
                row["median_support_cell_count"], "median_support_cell_count"
            ),
            mean_mle_set_size=_finite_float(row["mean_mle_set_size"], "mean_mle_set_size"),
            paired_brier_estimate=_finite_float(
                row["paired_brier_estimate"], "paired_brier_estimate"
            ),
            paired_brier_lower=_finite_float(row["paired_brier_lower"], "paired_brier_lower"),
            paired_brier_upper=_finite_float(row["paired_brier_upper"], "paired_brier_upper"),
            downstream_class=row["downstream_class"],
        )
        for row in pack.summary_rows
    )


def verify_integration_bank_extension(config: Goal010Config) -> IntegrationBankReplay:
    """Build old and expanded banks separately and compare inherited slices exactly."""
    old_config = goal008.Goal008Config(
        master_seed=config.master_seed,
        bank_size=config.bank_size,
        calibration_blocks=config.calibration_blocks,
        validation_blocks=config.validation_blocks,
        calibration_rank_one_based=config.calibration_rank_one_based,
        rhos=config.rhos,
        etas=config.original_etas,
        truth_cells=config.all_truth_cells,
    )
    expanded_config = expanded_goal008_config(config)
    old_manifest = goal008.spawn_seed_manifest(old_config)
    expanded_manifest = goal008.spawn_seed_manifest(expanded_config)
    fixed = goal007.build_fixed_inputs()
    old_bank = goal007.build_integration_bank(
        fixed,
        old_manifest.integration_bank,
        config.original_etas,
    )
    expanded_bank = goal007.build_integration_bank(
        fixed,
        expanded_manifest.integration_bank,
        config.expanded_etas,
    )
    old_slice_count = len(config.original_etas)
    expanded_old = expanded_bank.arrivals[:, :old_slice_count, :]
    expanded_new = expanded_bank.arrivals[:, old_slice_count:, :]
    return IntegrationBankReplay(
        old_slices_equal=np.array_equal(old_bank.arrivals, expanded_old),
        seed_manifest_equal=old_manifest == expanded_manifest,
        site_ids_equal=old_bank.site_ids == expanded_bank.site_ids,
        new_slices_finite_nonnegative=bool(
            expanded_new.shape[1] == 2
            and np.isfinite(expanded_new).all()
            and (expanded_new >= 0.0).all()
        ),
        fixed_process_invariants_pass=bool(fixed.invariants and all(fixed.invariants.values())),
        old_bank_sha256=_array_sha256(old_bank.arrivals),
        expanded_old_slices_sha256=_array_sha256(expanded_old),
        expanded_new_slices_sha256=_array_sha256(expanded_new),
    )


def classify_decision(
    invariants: Mapping[str, bool],
    primary_banks: Mapping[str, PrimaryBankDecisionEvidence],
    *,
    validation_count: int,
) -> str:
    """Apply the fixed Goal 010 primary-cell decision precedence."""
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if tuple(primary_banks) != BANK_VARIANT_NAMES:
        return "implementation_blocked"
    minimum_topology_success = ceil(0.95 * validation_count)
    allowed_topology_failures = validation_count - minimum_topology_success
    rows = tuple(primary_banks.values())
    if any(row.expanded_eta_max_contact_count > allowed_topology_failures for row in rows):
        return "bounded_upper_expansion_domain_not_closed"
    classes = {row.downstream_class for row in rows}
    if len(classes) != 1:
        return "likelihood_approximation_unstable"
    if all(
        row.topology_success_count >= minimum_topology_success
        and row.downstream_class == "cell_joint_recoverable"
        for row in rows
    ):
        return "bounded_upper_expansion_resolves_primary_decision_limit"
    if all(
        row.expanded_eta_max_contact_count <= allowed_topology_failures
        and row.expanded_eta_max_contact_count < row.original_eta_max_contact_count
        for row in rows
    ):
        return "bounded_upper_expansion_contributes_primary_still_limited"
    return "bounded_upper_expansion_domain_not_closed"


def run_campaign(
    baseline: Goal009Pack,
    config: Goal010Config = DEFAULT_CONFIG,
    *,
    workers: int,
) -> Goal010Result:
    """Run the three prespecified expanded-domain cells and pair disk evidence."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    _validate_runtime(config, workers)
    expanded = expanded_goal008_config(config)
    replay = verify_integration_bank_extension(config)
    tasks = tuple((cell, expanded) for cell in config.selected_cells)
    if workers == 1:
        task_outputs = tuple(_run_cell_task(task) for task in tasks)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            task_outputs = tuple(executor.map(_run_cell_task, tasks))
    cell_results = tuple(row[0] for row in task_outputs)
    telemetry_rows = tuple(row[1] for row in task_outputs)
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
    anatomy = baseline_boundary_anatomy(baseline)
    paired = _pair_validation_rows(
        baseline,
        validation,
        summaries,
        config=config,
    )
    comparisons = _domain_comparisons(
        anatomy,
        summaries,
        paired,
        config=config,
    )
    expected_pair_keys = tuple(
        (block, cell.cell_id, bank)
        for cell in config.selected_cells
        for block in range(config.validation_blocks)
        for bank in BANK_VARIANT_NAMES
    )
    observed_pair_keys = tuple(
        (row.block_index, row.truth_cell, row.bank_variant) for row in paired
    )
    baseline_config = baseline.config
    invariants = {
        "baseline_pack_validated": baseline.all_invariants_pass,
        "published_goal009_required_for_production": (
            not config.is_production or baseline.is_published_goal009
        ),
        "baseline_outcome_preserved": baseline.outcome == PUBLISHED_GOAL009_OUTCOME,
        "master_seed_unchanged": baseline_config.get("master_seed") == config.master_seed,
        "candidate_rhos_unchanged": _grids_equal_9(
            _float_sequence(baseline_config.get("candidate_rhos"), "candidate_rhos"),
            config.rhos,
        ),
        "old_candidate_etas_unchanged": tuple(
            _float_sequence(baseline_config.get("candidate_etas"), "candidate_etas")
        )
        == config.original_etas,
        "selected_cell_order": tuple(row.truth_cell.cell_id for row in cell_results)
        == config.selected_cell_ids,
        "bank_replay": replay.all_pass,
        "cell_invariants": all(
            cell_result.invariants and all(cell_result.invariants.values())
            for cell_result in cell_results
        ),
        "schedule_independent_seeds": len(
            {cell_result.seed_manifest_digest for cell_result in cell_results}
        )
        == 1,
        "expanded_calibration_complete": len(calibration)
        == len(config.selected_cells) * len(BANK_VARIANT_NAMES) * config.calibration_blocks,
        "expanded_validation_complete": len(validation)
        == len(config.selected_cells) * len(BANK_VARIANT_NAMES) * config.validation_blocks,
        "expanded_summary_complete": len(summaries)
        == len(config.selected_cells) * len(BANK_VARIANT_NAMES),
        "representative_surface_complete": len(representatives)
        == len(config.selected_cells) * len(BANK_VARIANT_NAMES),
        "paired_row_identity": observed_pair_keys == expected_pair_keys,
        "domain_comparison_complete": len(comparisons)
        == len(config.selected_cells) * len(BANK_VARIANT_NAMES),
        "finite_expanded_evidence": _expanded_evidence_finite(
            calibration,
            validation,
            summaries,
        ),
        "worker_processes_succeeded": len(telemetry_rows) == len(config.selected_cells)
        and all(row.exit_status == 0 for row in telemetry_rows),
    }
    primary = {
        row.bank_variant: PrimaryBankDecisionEvidence(
            bank_variant=row.bank_variant,
            original_eta_max_contact_count=row.original_eta_max_contact_count,
            expanded_eta_max_contact_count=row.expanded_eta_max_contact_count,
            topology_success_count=row.expanded_topology_success_count,
            downstream_class=row.expanded_downstream_class,
        )
        for row in comparisons
        if row.truth_cell == "cell-06"
    }
    outcome = classify_decision(
        invariants,
        primary,
        validation_count=config.validation_blocks,
    )
    telemetry = CampaignExecutionTelemetry(
        worker_count=workers,
        thread_limits={name: os.environ.get(name, "") for name in THREAD_LIMIT_NAMES},
        campaign_exit_status=0,
        cell_telemetry=telemetry_rows,
    )
    return Goal010Result(
        config=config,
        baseline_pack=baseline,
        baseline_anatomy=anatomy,
        bank_replay=replay,
        calibration_results=calibration,
        validation_results=validation,
        representative_profiles=representatives,
        cell_bank_summaries=summaries,
        paired_transitions=paired,
        domain_comparisons=comparisons,
        execution_telemetry=telemetry,
        invariants=invariants,
        outcome=outcome,
    )


def _run_cell_task(
    task: tuple[goal008.TruthCell, goal008.Goal008Config],
) -> tuple[goal008.CellResult, CellExecutionTelemetry]:
    cell, config = task
    started = time.perf_counter()
    result = goal008.run_truth_cell(cell, config)
    return result, CellExecutionTelemetry(
        truth_cell=cell.cell_id,
        exit_status=0,
        wall_time_seconds=time.perf_counter() - started,
        maximum_rss_bytes=_maximum_rss_bytes(),
    )


def _pair_validation_rows(
    baseline: Goal009Pack,
    expanded_rows: tuple[goal008.ValidationResult, ...],
    summaries: tuple[goal008.CellBankSummary, ...],
    *,
    config: Goal010Config,
) -> tuple[PairedBoundaryTransition, ...]:
    original_rows = {
        (_integer(row["block_index"], "block_index"), row["truth_cell"], row["bank_variant"]): row
        for row in baseline.validation_rows
        if row["truth_cell"] in config.selected_cell_ids
        and _integer(row["block_index"], "block_index") < config.validation_blocks
    }
    expanded_by_key = {
        (row.block_index, row.truth_cell, row.bank_variant): row for row in expanded_rows
    }
    original_cutoffs = {
        (row.truth_cell, row.bank_variant): row.calibrated_cutoff
        for row in baseline_boundary_anatomy(baseline)
    }
    expanded_cutoffs = {(row.truth_cell, row.bank_variant): row.cutoff.cutoff for row in summaries}
    expected_keys = tuple(
        (block, cell.cell_id, bank)
        for cell in config.selected_cells
        for block in range(config.validation_blocks)
        for bank in BANK_VARIANT_NAMES
    )
    if set(original_rows) != set(expected_keys) or set(expanded_by_key) != set(expected_keys):
        raise ValueError("original and expanded validation rows do not pair exactly")
    rows: list[PairedBoundaryTransition] = []
    for key in expected_keys:
        original = original_rows[key]
        expanded = expanded_by_key[key]
        original_faces = _string_tuple_json(
            original["support_boundary_faces"], "support_boundary_faces"
        )
        original_components = _integer(
            original["support_component_count"], "support_component_count"
        )
        rows.append(
            PairedBoundaryTransition(
                block_index=key[0],
                truth_cell=key[1],
                bank_variant=key[2],
                original_cutoff=original_cutoffs[(key[1], key[2])],
                expanded_cutoff=expanded_cutoffs[(key[1], key[2])],
                original_truth_included=_boolean(original["truth_included"], "truth_included"),
                expanded_truth_included=expanded.truth_included,
                original_support_component_count=original_components,
                expanded_support_component_count=expanded.support_component_count,
                original_support_boundary_faces=original_faces,
                expanded_support_boundary_faces=expanded.support_boundary_faces,
                original_connected_interior=original_components == 1 and not original_faces,
                expanded_connected_interior=expanded.support_component_count == 1
                and not expanded.support_boundary_faces,
                original_projected_log_rho_width=_finite_float(
                    original["projected_log_rho_width"], "projected_log_rho_width"
                ),
                expanded_projected_log_rho_width=expanded.projected_log_rho_width,
                original_projected_eta_width=_finite_float(
                    original["projected_eta_width"], "projected_eta_width"
                ),
                expanded_projected_eta_width=expanded.projected_eta_width,
                original_minimum_absolute_log_rho_error=_finite_float(
                    original["minimum_absolute_log_rho_error"],
                    "minimum_absolute_log_rho_error",
                ),
                expanded_minimum_absolute_log_rho_error=(expanded.minimum_absolute_log_rho_error),
                original_minimum_absolute_eta_error=_finite_float(
                    original["minimum_absolute_eta_error"],
                    "minimum_absolute_eta_error",
                ),
                expanded_minimum_absolute_eta_error=expanded.minimum_absolute_eta_error,
                original_support_indices=_index_tuple_json(
                    original["support_indices"], "support_indices"
                ),
                expanded_support_indices=expanded.support_indices,
                original_support_correlation=_optional_float(
                    original["support_correlation"], "support_correlation"
                ),
                expanded_support_correlation=expanded.support_correlation,
                original_mle_cells=_cell_tuple_json(
                    original["mle_cells_rho_eta"], "mle_cells_rho_eta"
                ),
                expanded_mle_cells=expanded.mle_cells,
                original_training_mle_cells=_cell_tuple_json(
                    original["training_mle_cells_rho_eta"],
                    "training_mle_cells_rho_eta",
                ),
                expanded_training_mle_cells=expanded.training_mle_cells,
                original_paired_brier_difference=_finite_float(
                    original["paired_brier_difference"], "paired_brier_difference"
                ),
                expanded_paired_brier_difference=expanded.paired_brier_difference,
            )
        )
    return tuple(rows)


def _domain_comparisons(
    anatomy: tuple[BaselineBoundaryAnatomy, ...],
    expanded: tuple[goal008.CellBankSummary, ...],
    transitions: tuple[PairedBoundaryTransition, ...],
    *,
    config: Goal010Config,
) -> tuple[DomainComparison, ...]:
    original_by_key = {
        (row.truth_cell, row.bank_variant): row
        for row in anatomy
        if row.truth_cell in config.selected_cell_ids
    }
    expanded_by_key = {(row.truth_cell, row.bank_variant): row for row in expanded}
    expected = tuple(
        (cell.cell_id, bank) for cell in config.selected_cells for bank in BANK_VARIANT_NAMES
    )
    if set(original_by_key) != set(expected) or set(expanded_by_key) != set(expected):
        raise ValueError("domain summaries are incomplete")
    rows: list[DomainComparison] = []
    for key in expected:
        original = original_by_key[key]
        new = expanded_by_key[key]
        paired = tuple(row for row in transitions if (row.truth_cell, row.bank_variant) == key)
        changes = tuple(
            int(row.expanded_connected_interior) - int(row.original_connected_interior)
            for row in paired
        )
        interval = normal_mean_interval(changes)
        expanded_eta_max_count = sum(row.expanded_contacted_eta_max for row in paired)
        rows.append(
            DomainComparison(
                truth_cell=key[0],
                bank_variant=key[1],
                original_cutoff=original.calibrated_cutoff,
                expanded_cutoff=new.cutoff.cutoff,
                cutoff_difference=new.cutoff.cutoff - original.calibrated_cutoff,
                original_topology_success_count=original.topology_success_count,
                expanded_topology_success_count=new.topology_success_count,
                topology_success_change=(
                    new.topology_success_count - original.topology_success_count
                ),
                paired_topology_change=interval,
                original_eta_max_contact_count=original.eta_max_contact_count,
                expanded_eta_max_contact_count=expanded_eta_max_count,
                eta_max_contact_change=(expanded_eta_max_count - original.eta_max_contact_count),
                expanded_eta_max_mle_count=sum(row.expanded_eta_max_mle for row in paired),
                original_downstream_class=original.downstream_class,
                expanded_downstream_class=new.downstream_class,
            )
        )
    return tuple(rows)


def _validate_goal009_tables(
    *,
    config: dict[str, object],
    compute: dict[str, object],
    summary: dict[str, object],
    verification: dict[str, object],
    seed_rows: tuple[dict[str, str], ...],
    summary_rows: tuple[dict[str, str], ...],
    calibration_rows: tuple[dict[str, str], ...],
    validation_rows: tuple[dict[str, str], ...],
    predictive_rows: tuple[dict[str, str], ...],
    profile_rows: tuple[dict[str, str], ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    truth_order = tuple(_string_sequence(config.get("truth_cell_order"), "truth_cell_order"))
    bank_order = tuple(_string_sequence(config.get("bank_variants"), "bank_variants"))
    if truth_order != tuple(f"cell-{index:02d}" for index in range(9)):
        raise ValueError("Goal009 truth-cell order is not frozen")
    if bank_order != BANK_VARIANT_NAMES:
        raise ValueError("Goal009 bank order is not frozen")
    cells = config.get("truth_cells")
    if not isinstance(cells, list) or len(cells) != 9:
        raise ValueError("Goal009 truth-cell configuration is incomplete")
    rhos = tuple(_float_sequence(config.get("candidate_rhos"), "candidate_rhos"))
    etas = tuple(_float_sequence(config.get("candidate_etas"), "candidate_etas"))
    if not rhos or not etas:
        raise ValueError("Goal009 candidate grids are empty")
    parsed_cells = _truth_cells_from_config(cells, rhos, etas)
    goal008_config = goal008.Goal008Config(
        master_seed=_object_integer(config.get("master_seed"), "master_seed"),
        bank_size=_object_integer(config.get("integration_bank_size"), "integration_bank_size"),
        calibration_blocks=_object_integer(
            config.get("calibration_block_count"), "calibration_block_count"
        ),
        validation_blocks=_object_integer(
            config.get("validation_block_count"), "validation_block_count"
        ),
        calibration_rank_one_based=_object_integer(
            config.get("calibration_rank_one_based"),
            "calibration_rank_one_based",
        ),
        rhos=rhos,
        etas=etas,
        truth_cells=parsed_cells,
    )
    calibration_count = goal008_config.calibration_blocks
    validation_count = goal008_config.validation_blocks
    expected_summary_keys = tuple((cell, bank) for cell in truth_order for bank in bank_order)
    if len(summary_rows) != len(expected_summary_keys):
        raise ValueError("Goal009 summary row count is wrong")
    if tuple((row["truth_cell"], row["bank_variant"]) for row in summary_rows) != (
        expected_summary_keys
    ):
        raise ValueError("Goal009 summary row order is wrong")
    expected_calibration_keys = tuple(
        (block, cell, bank)
        for cell in truth_order
        for block in range(calibration_count)
        for bank in bank_order
    )
    expected_validation_keys = tuple(
        (block, cell, bank)
        for cell in truth_order
        for block in range(validation_count)
        for bank in bank_order
    )
    observed_calibration_keys = tuple(
        (_integer(row["block_index"], "block_index"), row["truth_cell"], row["bank_variant"])
        for row in calibration_rows
    )
    observed_validation_keys = tuple(
        (_integer(row["block_index"], "block_index"), row["truth_cell"], row["bank_variant"])
        for row in validation_rows
    )
    if observed_calibration_keys != expected_calibration_keys:
        raise ValueError("Goal009 calibration row identity or order is wrong")
    if observed_validation_keys != expected_validation_keys:
        raise ValueError("Goal009 validation row identity or order is wrong")
    if tuple((row["truth_cell"], row["bank_variant"]) for row in predictive_rows) != (
        expected_summary_keys
    ):
        raise ValueError("Goal009 predictive row identity or order is wrong")
    expected_profile_keys = tuple(
        (cell, bank, eta_index, rho_index)
        for cell in truth_order
        for bank in bank_order
        for eta_index in range(len(etas))
        for rho_index in range(len(rhos))
    )
    observed_profile_keys = tuple(
        (
            row["truth_cell"],
            row["bank_variant"],
            _integer(row["candidate_eta_index"], "candidate_eta_index"),
            _integer(row["candidate_rho_index"], "candidate_rho_index"),
        )
        for row in profile_rows
    )
    if observed_profile_keys != expected_profile_keys:
        raise ValueError("Goal009 representative profile surface is incomplete or reordered")
    _validate_seed_rows(goal008_config, seed_rows)
    _validate_numeric_rows(summary_rows, SUMMARY_FIELDS)
    _validate_numeric_rows(calibration_rows, CALIBRATION_FIELDS)
    _validate_numeric_rows(validation_rows, VALIDATION_FIELDS)
    _validate_numeric_rows(predictive_rows, PREDICTIVE_FIELDS)
    _validate_numeric_rows(profile_rows, PROFILE_FIELDS)
    summary_surface = summary.get("cell_bank_surface")
    if not isinstance(summary_surface, list) or len(summary_surface) != len(summary_rows):
        raise ValueError("Goal009 summary JSON surface is incomplete")
    for csv_row, json_row in zip(summary_rows, summary_surface, strict=True):
        if not isinstance(json_row, dict) or any(
            key not in json_row or not _csv_matches_json(csv_row[key], json_row[key])
            for key in SUMMARY_FIELDS
        ):
            raise ValueError("Goal009 summary CSV and JSON disagree")
    outcome = _require_str(verification, "outcome")
    if outcome != summary.get("outcome") or outcome != PUBLISHED_GOAL009_OUTCOME:
        raise ValueError("Goal009 outcome is not the accepted published result")
    if verification.get("expected_artifact_file_count") != 16:
        raise ValueError("Goal009 expected artifact count is wrong")
    if verification.get("observed_artifact_file_count") != 16:
        raise ValueError("Goal009 observed artifact count is wrong")
    if compute.get("campaign_exit_success") is not True:
        raise ValueError("Goal009 compute provenance reports campaign failure")
    return truth_order, bank_order


def _validate_seed_rows(
    config: goal008.Goal008Config,
    rows: tuple[dict[str, str], ...],
) -> None:
    manifest = goal008.spawn_seed_manifest(config)
    records = manifest.stream_records
    if len(rows) != len(records):
        raise ValueError("Goal009 seed-manifest row count is wrong")
    for row, record in zip(rows, records, strict=True):
        if (
            row["phase"] != record.phase
            or _integer(row["block_index"], "block_index") != record.index
            or row["stream_role"] != record.stream_role
            or _integer(row["entropy"], "entropy") != record.entropy
            or _integer_tuple_json(row["spawn_key"], "spawn_key") != record.spawn_key
            or _integer_tuple_json(row["state_words"], "state_words") != record.state_words
            or _integer(row["pool_size"], "pool_size") != record.pool_size
        ):
            raise ValueError("Goal009 seed-manifest row does not replay")
        expected_pairing = (
            f"integration-bank-draw-{record.index:04d}"
            if record.phase == "integration_bank"
            else f"{record.phase}-block-{record.index:03d}"
        )
        if row["pairing_group"] != expected_pairing:
            raise ValueError("Goal009 seed pairing identity is wrong")


def _is_published_goal009(
    *,
    config: Mapping[str, object],
    compute: Mapping[str, object],
    verification: Mapping[str, object],
    verification_sha256: str,
    summary_rows: tuple[dict[str, str], ...],
) -> bool:
    expected_classes = {
        f"cell-{index:02d}": (
            "cell_joint_design_limited" if index in {0, 1, 2, 6, 7} else "cell_joint_recoverable"
        )
        for index in range(9)
    }
    return bool(
        config.get("master_seed") == goal008.MASTER_SEED
        and config.get("integration_bank_size") == goal008.INTEGRATION_BANK_SIZE
        and config.get("calibration_block_count") == goal008.CALIBRATION_BLOCKS
        and config.get("validation_block_count") == goal008.VALIDATION_BLOCKS
        and config.get("calibration_rank_one_based") == goal008.CALIBRATION_RANK_ONE_BASED
        and _grids_equal_9(
            _float_sequence(config.get("candidate_rhos"), "candidate_rhos"),
            goal008.FROZEN_RHO_GRID,
        )
        and tuple(_float_sequence(config.get("candidate_etas"), "candidate_etas"))
        == goal008.FROZEN_ETA_GRID
        and compute.get("provenance_mode") == "production"
        and compute.get("run_id") == PUBLISHED_GOAL009_RUN_ID
        and compute.get("host_id") == "deep-server"
        and compute.get("source_commit") == PUBLISHED_GOAL009_SOURCE_COMMIT
        and compute.get("worker_count") == 9
        and compute.get("thread_limits") == {name: "1" for name in THREAD_LIMIT_NAMES}
        and verification.get("outcome") == PUBLISHED_GOAL009_OUTCOME
        and verification_sha256 == PUBLISHED_GOAL009_VERIFICATION_SHA256
        and all(
            row["downstream_class"] == expected_classes[row["truth_cell"]] for row in summary_rows
        )
    )


def _validate_numeric_rows(
    rows: tuple[dict[str, str], ...],
    fields: tuple[str, ...],
) -> None:
    nonnumeric = {
        "phase",
        "pairing_group",
        "truth_cell",
        "bank_variant",
        "cutoff_source_cell",
        "stream_role",
        "support_correlation_reason",
        "downstream_class",
    }
    booleans = {
        "duplicate_visits_agree",
        "split_isolated",
        "perfect_truth_mapping",
        "truth_included",
        "support_boundary_contact",
        "worst_tied_process_mle_rule",
        "in_support",
        "is_mle",
        "is_truth",
    }
    nested = {
        "spawn_key",
        "state_words",
        "mle_indices",
        "mle_cells_rho_eta",
        "support_boundary_faces",
        "support_indices",
        "training_mle_indices",
        "training_mle_cells_rho_eta",
    }
    for row in rows:
        for field in fields:
            value = row[field]
            if field in nonnumeric:
                continue
            if field in booleans:
                _boolean(value, field)
            elif field in nested:
                _json_value(value, field)
            elif field == "support_correlation" and not value:
                continue
            else:
                _finite_float(value, field)


def _truth_cells_from_config(
    values: list[object],
    rhos: tuple[float, ...],
    etas: tuple[float, ...],
) -> tuple[goal008.TruthCell, ...]:
    rows: list[goal008.TruthCell] = []
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("Goal009 truth-cell entry must be an object")
        rows.append(
            goal008.TruthCell(
                cell_id=_require_str(value, "truth_cell"),
                rho=_object_float(value.get("rho"), "rho"),
                eta=_object_float(value.get("eta"), "eta"),
                rho_index=_object_integer(value.get("rho_index"), "rho_index"),
                eta_index=_object_integer(value.get("eta_index"), "eta_index"),
            )
        )
    parsed = tuple(rows)
    if any(rhos[cell.rho_index] != cell.rho or etas[cell.eta_index] != cell.eta for cell in parsed):
        raise ValueError("Goal009 truth-cell coordinates do not match candidate grids")
    return parsed


def _expanded_evidence_finite(
    calibration: tuple[goal008.CalibrationResult, ...],
    validation: tuple[goal008.ValidationResult, ...],
    summaries: tuple[goal008.CellBankSummary, ...],
) -> bool:
    return (
        all(
            isfinite(row.lr_at_truth)
            and isfinite(row.truth_log_likelihood)
            and isfinite(row.maximum_log_likelihood)
            for row in calibration
        )
        and all(
            isfinite(row.lr_at_truth)
            and isfinite(row.truth_log_likelihood)
            and isfinite(row.maximum_log_likelihood)
            and isfinite(row.paired_brier_difference)
            for row in validation
        )
        and all(
            isfinite(row.cutoff.cutoff)
            and isfinite(row.paired_brier_interval.estimate)
            and isfinite(row.paired_brier_interval.lower)
            and isfinite(row.paired_brier_interval.upper)
            for row in summaries
        )
    )


def _validate_runtime(config: Goal010Config, workers: int) -> None:
    if config.is_production:
        if workers != 3:
            raise ValueError("Goal010 production requires exactly three workers")
        expected = {name: "1" for name in THREAD_LIMIT_NAMES}
        observed = {name: os.environ.get(name, "") for name in THREAD_LIMIT_NAMES}
        if observed != expected:
            raise ValueError("Goal010 production requires all thread limits set to 1")


def _maximum_rss_bytes() -> int:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(usage if os.uname().sysname == "Darwin" else usage * 1024)


def _array_sha256(array: np.ndarray[Any, Any]) -> str:
    contiguous = np.ascontiguousarray(array)
    payload = (
        json.dumps(
            {"dtype": contiguous.dtype.str, "shape": contiguous.shape},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + contiguous.tobytes()
    )
    return hashlib.sha256(payload).hexdigest()


def _read_json_object(path: Path) -> dict[str, object]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON token {value} in {path.name}")

    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {path.name}")
            result[key] = value
        return result

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid strict JSON in {path.name}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def _read_csv(path: Path, fields: tuple[str, ...]) -> tuple[dict[str, str], ...]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or tuple(reader.fieldnames) != fields:
                raise ValueError(f"{path.name} schema does not match the published contract")
            rows = tuple(dict(row) for row in reader)
    except (OSError, UnicodeError, csv.Error) as error:
        raise ValueError(f"invalid CSV in {path.name}") from error
    if not rows or any(set(row) != set(fields) or None in row.values() for row in rows):
        raise ValueError(f"{path.name} contains missing or malformed rows")
    return rows


def _json_value(text: str, field: str) -> object:
    try:
        return json.loads(
            text,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"{field} contains non-finite JSON token {value}")
            ),
        )
    except json.JSONDecodeError as error:
        raise ValueError(f"{field} must contain strict compact JSON") from error


def _integer_tuple_json(text: str, field: str) -> tuple[int, ...]:
    value = _json_value(text, field)
    if not isinstance(value, list) or any(
        not isinstance(item, int) or isinstance(item, bool) for item in value
    ):
        raise ValueError(f"{field} must be a JSON integer list")
    return tuple(value)


def _index_tuple_json(text: str, field: str) -> tuple[tuple[int, int], ...]:
    value = _json_value(text, field)
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a JSON index list")
    result: list[tuple[int, int]] = []
    for item in value:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or any(not isinstance(part, int) or isinstance(part, bool) for part in item)
        ):
            raise ValueError(f"{field} must contain integer index pairs")
        result.append((item[0], item[1]))
    return tuple(result)


def _cell_tuple_json(text: str, field: str) -> tuple[tuple[float, float], ...]:
    value = _json_value(text, field)
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a JSON cell list")
    result: list[tuple[float, float]] = []
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError(f"{field} must contain coordinate pairs")
        result.append(
            (
                _object_float(item[0], field),
                _object_float(item[1], field),
            )
        )
    return tuple(result)


def _string_tuple_json(text: str, field: str) -> tuple[str, ...]:
    value = _json_value(text, field)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a JSON string list")
    return tuple(value)


def _boolean(text: str, field: str) -> bool:
    if text == "true":
        return True
    if text == "false":
        return False
    raise ValueError(f"{field} must be true or false")


def _integer(text: str, field: str) -> int:
    try:
        value = int(text)
    except ValueError as error:
        raise ValueError(f"{field} must be an integer") from error
    if str(value) != text:
        raise ValueError(f"{field} must use canonical integer formatting")
    return value


def _finite_float(text: str, field: str) -> float:
    try:
        value = float(text)
    except ValueError as error:
        raise ValueError(f"{field} must be numeric") from error
    if not isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def _optional_float(text: str, field: str) -> float | None:
    return None if text == "" else _finite_float(text, field)


def _object_integer(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    return value


def _object_float(value: object, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _require_str(mapping: Mapping[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _float_sequence(value: object, field: str) -> tuple[float, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return tuple(_object_float(item, field) for item in value)


def _string_sequence(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a string list")
    return tuple(value)


def _csv_matches_json(csv_value: str, json_value: object) -> bool:
    if isinstance(json_value, bool):
        return csv_value == ("true" if json_value else "false")
    if isinstance(json_value, int):
        return csv_value == str(json_value)
    if isinstance(json_value, float):
        return isfinite(json_value) and _finite_float(csv_value, "summary value") == json_value
    if json_value is None:
        return csv_value == ""
    return isinstance(json_value, str) and csv_value == json_value


def _grids_equal_9(
    left: Sequence[float],
    right: Sequence[float],
) -> bool:
    """Apply Goal 009's accepted cross-platform finite-value continuity rule."""
    return len(left) == len(right) and all(
        round(float(first), 9) == round(float(second), 9)
        for first, second in zip(left, right, strict=True)
    )
