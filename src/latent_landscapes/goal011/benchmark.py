"""Central joint recovery benchmark under known imperfect detection."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
from statistics import fmean, median
from typing import cast

import numpy as np
from numpy.typing import NDArray

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
from latent_landscapes.goal003.spread import StochasticSpreadTruth, compute_stochastic_spread
from latent_landscapes.goal004 import benchmark as goal004
from latent_landscapes.goal004.likelihood import (
    PredictiveScore,
    record_detection_probabilities,
    score_predictions,
    site_history_probabilities,
)
from latent_landscapes.goal004.observations import (
    DETECTION_PROBABILITY,
    REPLICATES,
    SURVEY_TIMES,
    generate_observations,
)
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal007.likelihood import (
    CATEGORY_COUNT,
    TRUTH_ETA,
    TRUTH_RHO,
    JointGridProfile,
    JointProfileSummary,
    summarize_joint_profile,
)
from latent_landscapes.goal008.benchmark import support_boundary_faces

from .likelihood import (
    EXPANDED_ETA_GRID,
    OLD_DOMAIN_MAXIMUM_ETA,
    joint_profile_from_history_probabilities,
    project_eta_domain,
    rho_grid,
)

MASTER_SEED = goal007.MASTER_SEED
INTEGRATION_BANK_SIZE = goal007.INTEGRATION_BANK_SIZE
CALIBRATION_REPLICATES = goal007.CALIBRATION_REPLICATES
VALIDATION_REPLICATES = goal007.VALIDATION_REPLICATES
CALIBRATION_RANK_ONE_BASED = goal007.CALIBRATION_RANK_ONE_BASED
BANK_VARIANT_NAMES = goal007.BANK_VARIANT_NAMES
FROZEN_RHO_GRID = tuple(float(value) for value in rho_grid())
FROZEN_ETA_GRID = EXPANDED_ETA_GRID
OLD_ETA_GRID = tuple(value for value in FROZEN_ETA_GRID if value <= OLD_DOMAIN_MAXIMUM_ETA)
STATE_WORD_COUNT = goal007.STATE_WORD_COUNT

SOURCE_IDENTITY = {
    "goal007_repository_commit": goal007.SOURCE_IDENTITY["repository_commit"],
    "goal007_process_reference": "Goal 007 process roots and old eta slices",
    "goal010_eta_extension": [2.25, 2.5],
}

HISTORICAL_GOAL007_REFERENCE = {
    "comparison_type": "historical_noncausal",
    "candidate_eta_maximum": 2.0,
    "detection_probability": 1.0,
    "outcome": "advance_to_joint_cross_truth_perfect_detection",
    "bank_cutoffs": {
        "full": 90.524248,
        "first_half": 91.985528,
        "second_half": 87.520852,
    },
}


@dataclass(frozen=True, slots=True)
class Goal011Config:
    master_seed: int = MASTER_SEED
    bank_size: int = INTEGRATION_BANK_SIZE
    calibration_replicates: int = CALIBRATION_REPLICATES
    validation_replicates: int = VALIDATION_REPLICATES
    calibration_rank_one_based: int = CALIBRATION_RANK_ONE_BASED
    rhos: tuple[float, ...] = FROZEN_RHO_GRID
    etas: tuple[float, ...] = FROZEN_ETA_GRID

    def __post_init__(self) -> None:
        if self.bank_size < 2 or self.bank_size % 2:
            raise ValueError("integration bank size must be positive and even")
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("outer replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
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
        if sum(value == TRUTH_RHO for value in self.rhos) != 1:
            raise ValueError("rho grid must contain truth rho = 1 exactly once")
        if sum(value == TRUTH_ETA for value in self.etas) != 1:
            raise ValueError("eta grid must contain truth eta = 1 exactly once")
        if tuple(value for value in self.etas if value <= OLD_DOMAIN_MAXIMUM_ETA) != tuple(
            value for value in self.etas if value <= 2.0
        ):
            raise ValueError("old eta projection must be a leading domain ending at 2")

    @property
    def half_bank_size(self) -> int:
        return self.bank_size // 2

    @property
    def truth_rho_index(self) -> int:
        return self.rhos.index(TRUTH_RHO)

    @property
    def truth_eta_index(self) -> int:
        return self.etas.index(TRUTH_ETA)

    @property
    def old_etas(self) -> tuple[float, ...]:
        return tuple(value for value in self.etas if value <= OLD_DOMAIN_MAXIMUM_ETA)

    @property
    def goal007_config(self) -> goal007.Goal007Config:
        return goal007.Goal007Config(
            master_seed=self.master_seed,
            bank_size=self.bank_size,
            calibration_replicates=self.calibration_replicates,
            validation_replicates=self.validation_replicates,
            calibration_rank_one_based=self.calibration_rank_one_based,
            rhos=self.rhos,
            etas=self.etas,
        )

    @property
    def is_production(self) -> bool:
        return self == DEFAULT_CONFIG


DEFAULT_CONFIG = Goal011Config()


def smoke_config() -> Goal011Config:
    """Return the explicit reduced smoke while retaining the full candidate grid."""
    return Goal011Config(
        bank_size=2,
        calibration_replicates=2,
        validation_replicates=2,
        calibration_rank_one_based=2,
    )


@dataclass(frozen=True, slots=True)
class DatasetSeedRecord:
    phase: str
    index: int
    process: goal007.StreamSeedRecord
    detection: goal004.StreamSeedRecord


SeedRecord = goal007.StreamSeedRecord | goal004.StreamSeedRecord


@dataclass(frozen=True, slots=True)
class SeedManifest:
    integration_bank: tuple[goal007.StreamSeedRecord, ...]
    calibration: tuple[DatasetSeedRecord, ...]
    validation: tuple[DatasetSeedRecord, ...]

    @property
    def stream_records(self) -> tuple[SeedRecord, ...]:
        outer: tuple[SeedRecord, ...] = tuple(
            stream
            for dataset in (*self.calibration, *self.validation)
            for stream in (dataset.process, dataset.detection)
        )
        return (*self.integration_bank, *outer)


@dataclass(frozen=True, slots=True)
class BankReplay:
    old_slices_equal: bool
    old_site_ids_equal: bool
    old_seed_manifest_equal: bool
    added_slices_finite: bool

    @property
    def all_pass(self) -> bool:
        return (
            self.old_slices_equal
            and self.old_site_ids_equal
            and self.old_seed_manifest_equal
            and self.added_slices_finite
        )


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    dataset_index: int
    bank_variant: str
    record_count: int
    no_false_positives: bool
    truth_eta_index: int
    truth_rho_index: int
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
    dataset_index: int
    bank_variant: str
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
    survey_time: int
    occupied_fraction_mean: float
    occupied_fraction_lower: float
    occupied_fraction_upper: float
    detected_fraction_mean: float
    detected_fraction_lower: float
    detected_fraction_upper: float


@dataclass(frozen=True, slots=True)
class RepresentativeProfile:
    dataset_index: int
    bank_variant: str
    expanded_cutoff: float
    old_domain_cutoff: float
    expanded_profile: JointGridProfile
    old_domain_profile: JointGridProfile
    expanded_summary: JointProfileSummary
    old_domain_summary: JointProfileSummary


@dataclass(frozen=True, slots=True)
class BankSummary:
    bank_variant: str
    draw_count: int
    cutoff: CutoffResult
    old_domain_cutoff: CutoffResult
    expanded_coverage_success_count: int
    expanded_calibrated_coverage: EstimateInterval
    expanded_topology_success_count: int
    expanded_boundary_contact_count: int
    expanded_median_minimum_absolute_log_rho_error: float
    expanded_median_minimum_absolute_eta_error: float
    expanded_median_projected_log_rho_width: float
    expanded_median_projected_eta_width: float
    expanded_paired_brier_interval: EstimateInterval
    expanded_mean_stochastic_brier_worst_mle: float
    mean_neutral_brier: float
    expanded_downstream_class: str
    old_domain_coverage_success_count: int
    old_domain_calibrated_coverage: EstimateInterval
    old_domain_topology_success_count: int
    old_domain_boundary_contact_count: int
    old_domain_median_minimum_absolute_log_rho_error: float
    old_domain_median_minimum_absolute_eta_error: float
    old_domain_median_projected_log_rho_width: float
    old_domain_median_projected_eta_width: float
    old_domain_paired_brier_interval: EstimateInterval
    old_domain_downstream_class: str


@dataclass(frozen=True, slots=True)
class DomainComparison:
    bank_variant: str
    expanded_cutoff: float
    old_domain_cutoff: float
    cutoff_difference: float
    expanded_downstream_class: str
    old_domain_downstream_class: str
    appended_support_use_count: int
    appended_mle_use_count: int
    expanded_boundary_contact_count: int
    old_domain_boundary_contact_count: int


@dataclass(frozen=True, slots=True)
class Goal011Result:
    config: Goal011Config
    fixed_inputs: goal007.FixedInputs
    seed_manifest: SeedManifest
    integration_bank: goal007.IntegrationBank
    bank_replay: BankReplay
    bank_variants: tuple[goal007.BankVariant, ...]
    calibration_results: tuple[CalibrationResult, ...]
    validation_results: tuple[ValidationResult, ...]
    observation_signal_summary: tuple[ObservationSignalSummary, ...]
    representative_profiles: tuple[RepresentativeProfile, ...]
    bank_summaries: tuple[BankSummary, ...]
    domain_comparisons: tuple[DomainComparison, ...]
    invariants: dict[str, bool]
    outcome: str


@dataclass(frozen=True, slots=True)
class _Cutoffs:
    expanded: dict[str, CutoffResult]
    old_domain: dict[str, CutoffResult]


@dataclass(frozen=True, slots=True)
class _DomainSummary:
    coverage_count: int
    coverage: EstimateInterval
    topology_count: int
    boundary_count: int
    rho_error: float
    eta_error: float
    rho_width: float
    eta_width: float
    brier: EstimateInterval


def spawn_seed_manifest(config: Goal011Config = DEFAULT_CONFIG) -> SeedManifest:
    """Spawn five roots while preserving the first three Goal 007 roots exactly."""
    roots = np.random.SeedSequence(config.master_seed).spawn(5)
    integration = tuple(
        _process_record("integration_bank", index, "paired_eta_process", child)
        for index, child in enumerate(roots[0].spawn(config.bank_size))
    )
    calibration_process = tuple(
        _process_record("calibration", index, "central_truth_process", child)
        for index, child in enumerate(roots[1].spawn(config.calibration_replicates))
    )
    validation_process = tuple(
        _process_record("validation", index, "central_truth_process", child)
        for index, child in enumerate(roots[2].spawn(config.validation_replicates))
    )
    calibration_detection = tuple(
        _detection_record("calibration", index, child)
        for index, child in enumerate(roots[3].spawn(config.calibration_replicates))
    )
    validation_detection = tuple(
        _detection_record("validation", index, child)
        for index, child in enumerate(roots[4].spawn(config.validation_replicates))
    )
    return SeedManifest(
        integration_bank=integration,
        calibration=tuple(
            DatasetSeedRecord("calibration", index, process, detection)
            for index, (process, detection) in enumerate(
                zip(calibration_process, calibration_detection, strict=True)
            )
        ),
        validation=tuple(
            DatasetSeedRecord("validation", index, process, detection)
            for index, (process, detection) in enumerate(
                zip(validation_process, validation_detection, strict=True)
            )
        ),
    )


def build_fixed_inputs() -> goal007.FixedInputs:
    """Reuse Goal 007 spatial inputs while replacing perfect-observation invariants."""
    base = goal007.build_fixed_inputs()
    invariants = {
        key: value
        for key, value in base.invariants.items()
        if key not in {"perfect_detection", "no_detection_stream"}
    }
    invariants.update(
        {
            "known_detection_probability": DETECTION_PROBABILITY == 0.65,
            "two_replicate_visits": REPLICATES == (1, 2),
            "zero_false_positive_model": True,
        }
    )
    return goal007.FixedInputs(base.landscape, base.design, invariants)


def build_integration_banks(
    config: Goal011Config,
    fixed: goal007.FixedInputs,
    records: tuple[goal007.StreamSeedRecord, ...],
) -> tuple[goal007.IntegrationBank, tuple[goal007.BankVariant, ...], BankReplay]:
    """Build the primary bank and independently replay every old-domain slice."""
    expanded = goal007.build_integration_bank(fixed, records, config.etas)
    old = goal007.build_integration_bank(fixed, records, config.old_etas)
    variants = goal007.build_bank_variants(config.goal007_config, expanded)
    reference = goal007.spawn_seed_manifest(config.goal007_config)
    appended = expanded.arrivals[:, len(config.old_etas) :, :]
    replay = BankReplay(
        old_slices_equal=bool(
            np.array_equal(old.arrivals, expanded.arrivals[:, : len(config.old_etas), :])
        ),
        old_site_ids_equal=old.site_ids == expanded.site_ids,
        old_seed_manifest_equal=records == reference.integration_bank,
        added_slices_finite=bool(
            appended.size > 0 and np.isfinite(appended).all() and (appended >= 0.0).all()
        ),
    )
    return expanded, variants, replay


def generate_dataset(
    fixed: goal007.FixedInputs,
    seed: DatasetSeedRecord,
) -> tuple[StochasticSpreadTruth, tuple[Observation, ...]]:
    """Generate one central truth and its complete known-detection history."""
    truth = compute_stochastic_spread(
        fixed.landscape,
        goal007.generator_from_seed_record(seed.process),
        rho=TRUTH_RHO,
    )
    records = generate_observations(
        fixed.design.sites,
        truth,
        goal004.generator_from_seed_record(seed.detection),
    )
    return truth, records


def no_false_positives(
    records: tuple[Observation, ...],
    truth: StochasticSpreadTruth,
) -> bool:
    return all(
        not record.detected or truth.arrival[record.row, record.col] <= record.time
        for record in records
    )


def run_goal011(
    config: Goal011Config = DEFAULT_CONFIG,
    fixed_inputs: goal007.FixedInputs | None = None,
) -> Goal011Result:
    """Run the central expanded-domain and non-gating old-domain benchmark."""
    fixed = fixed_inputs if fixed_inputs is not None else build_fixed_inputs()
    manifest = spawn_seed_manifest(config)
    bank, variants, bank_replay = build_integration_banks(
        config,
        fixed,
        manifest.integration_bank,
    )
    calibration = _run_calibration(config, fixed, manifest.calibration, bank.site_ids, variants)
    cutoffs = _calibration_cutoffs(config, calibration)
    validation, representatives, signals = _run_validation(
        config,
        fixed,
        manifest.validation,
        bank.site_ids,
        variants,
        cutoffs,
    )
    summaries, comparisons = _aggregate_banks(config, variants, cutoffs, validation)
    invariants = _evaluate_invariants(
        config,
        fixed,
        manifest,
        bank,
        bank_replay,
        variants,
        calibration,
        validation,
        representatives,
        summaries,
    )
    outcome = classify_outcome(
        invariants=invariants,
        downstream_classes=tuple(row.expanded_downstream_class for row in summaries),
    )
    return Goal011Result(
        config=config,
        fixed_inputs=fixed,
        seed_manifest=manifest,
        integration_bank=bank,
        bank_replay=bank_replay,
        bank_variants=variants,
        calibration_results=calibration,
        validation_results=validation,
        observation_signal_summary=signals,
        representative_profiles=representatives,
        bank_summaries=summaries,
        domain_comparisons=comparisons,
        invariants=invariants,
        outcome=outcome,
    )


def classify_downstream(
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
    """Apply the frozen Goal 007 numbers with Goal 011-specific labels."""
    if validation_count <= 0 or topology_success_count < ceil(0.95 * validation_count):
        return "joint_imperfect_detection_design_limited"
    if not calibrated_coverage.lower <= 0.95 <= calibrated_coverage.upper:
        return "joint_imperfect_detection_local_calibration_not_ready"
    if (
        median_absolute_log_rho_error > 0.10
        or median_absolute_eta_error > 0.25
        or median_projected_log_rho_width > 0.50
        or median_projected_eta_width > 0.75
    ):
        return "joint_imperfect_detection_recovery_imprecise"
    if paired_brier_interval.lower > 0.0:
        return "joint_imperfect_detection_neutral_better"
    if paired_brier_interval.upper < 0.0:
        return "advance_to_cross_truth_joint_imperfect_detection"
    return "joint_imperfect_detection_mechanism_inconclusive"


def classify_outcome(
    *,
    invariants: dict[str, bool],
    downstream_classes: tuple[str, ...],
) -> str:
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if len(downstream_classes) != 3 or len(set(downstream_classes)) != 1:
        return "likelihood_approximation_unstable"
    return downstream_classes[0]


def _run_calibration(
    config: Goal011Config,
    fixed: goal007.FixedInputs,
    seeds: tuple[DatasetSeedRecord, ...],
    site_ids: tuple[str, ...],
    variants: tuple[goal007.BankVariant, ...],
) -> tuple[CalibrationResult, ...]:
    rhos = np.asarray(config.rhos, dtype=np.float64)
    etas = np.asarray(config.etas, dtype=np.float64)
    rows: list[CalibrationResult] = []
    for seed in seeds:
        truth, records = generate_dataset(fixed, seed)
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
            expanded_truth = float(
                expanded.log_likelihoods[config.truth_eta_index, config.truth_rho_index]
            )
            old_truth = float(old.log_likelihoods[config.truth_eta_index, config.truth_rho_index])
            rows.append(
                CalibrationResult(
                    dataset_index=seed.index,
                    bank_variant=variant.name,
                    record_count=len(records),
                    no_false_positives=no_false_positives(records, truth),
                    truth_eta_index=config.truth_eta_index,
                    truth_rho_index=config.truth_rho_index,
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
    config: Goal011Config,
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


def _run_validation(
    config: Goal011Config,
    fixed: goal007.FixedInputs,
    seeds: tuple[DatasetSeedRecord, ...],
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
    occupied_signals: dict[int, list[float]] = {time: [] for time in SURVEY_TIMES}
    detected_signals: dict[int, list[float]] = {time: [] for time in SURVEY_TIMES}
    for seed in seeds:
        truth, records = generate_dataset(fixed, seed)
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
        for time in SURVEY_TIMES:
            occupied_signals[time].append(
                float(
                    np.mean(
                        [truth.arrival[site.row, site.col] <= time for site in fixed.design.sites]
                    )
                )
            )
            detected_signals[time].append(
                float(np.mean([record.detected for record in records if record.time == time]))
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
            )
            old_support = summarize_joint_profile(
                old,
                cutoff=cutoffs.old_domain[variant.name].cutoff,
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
            expanded_faces = support_boundary_faces(
                expanded_support.support_indices,
                eta_count=len(config.etas),
                rho_count=len(config.rhos),
            )
            old_faces = support_boundary_faces(
                old_support.support_indices,
                eta_count=len(config.old_etas),
                rho_count=len(config.rhos),
            )
            expanded_truth = float(
                expanded.log_likelihoods[config.truth_eta_index, config.truth_rho_index]
            )
            old_truth = float(old.log_likelihoods[config.truth_eta_index, config.truth_rho_index])
            rows.append(
                ValidationResult(
                    dataset_index=seed.index,
                    bank_variant=variant.name,
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
                    expanded_support_boundary_contact=expanded_support.support_boundary_contact,
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
                    old_domain_support_boundary_contact=old_support.support_boundary_contact,
                    old_domain_support_boundary_faces=old_faces,
                    old_domain_projected_log_rho_width=old_support.projected_log_rho_width,
                    old_domain_projected_eta_width=old_support.projected_eta_width,
                    old_domain_support_indices=old_support.support_indices,
                    old_domain_mle_cells=old_support.mle_cells,
                    old_domain_minimum_absolute_log_rho_error=(
                        old_support.minimum_absolute_log_rho_error
                    ),
                    old_domain_minimum_absolute_eta_error=(old_support.minimum_absolute_eta_error),
                    old_domain_training_mle_cells=old_training.mle_cells,
                    old_domain_paired_brier_difference=old_predictive.paired_brier_difference,
                )
            )
            if seed.index == 0:
                representatives.append(
                    RepresentativeProfile(
                        dataset_index=0,
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
            survey_time=time,
            occupied_fraction_mean=float(np.mean(occupied_signals[time])),
            occupied_fraction_lower=float(np.quantile(occupied_signals[time], 0.05)),
            occupied_fraction_upper=float(np.quantile(occupied_signals[time], 0.95)),
            detected_fraction_mean=float(np.mean(detected_signals[time])),
            detected_fraction_lower=float(np.quantile(detected_signals[time], 0.05)),
            detected_fraction_upper=float(np.quantile(detected_signals[time], 0.95)),
        )
        for time in SURVEY_TIMES
    )
    return tuple(rows), tuple(representatives), signals


def _process_scores(
    profile: JointGridProfile,
    weights: NDArray[np.float64],
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


def _aggregate_banks(
    config: Goal011Config,
    variants: tuple[goal007.BankVariant, ...],
    cutoffs: _Cutoffs,
    validation: tuple[ValidationResult, ...],
) -> tuple[tuple[BankSummary, ...], tuple[DomainComparison, ...]]:
    summaries: list[BankSummary] = []
    comparisons: list[DomainComparison] = []
    for variant in variants:
        rows = tuple(row for row in validation if row.bank_variant == variant.name)
        expanded = _domain_summary(rows, old=False)
        old = _domain_summary(rows, old=True)
        expanded_class = classify_downstream(
            topology_success_count=expanded.topology_count,
            validation_count=len(rows),
            calibrated_coverage=expanded.coverage,
            median_absolute_log_rho_error=expanded.rho_error,
            median_absolute_eta_error=expanded.eta_error,
            median_projected_log_rho_width=expanded.rho_width,
            median_projected_eta_width=expanded.eta_width,
            paired_brier_interval=expanded.brier,
        )
        old_class = classify_downstream(
            topology_success_count=old.topology_count,
            validation_count=len(rows),
            calibrated_coverage=old.coverage,
            median_absolute_log_rho_error=old.rho_error,
            median_absolute_eta_error=old.eta_error,
            median_projected_log_rho_width=old.rho_width,
            median_projected_eta_width=old.eta_width,
            paired_brier_interval=old.brier,
        )
        summary = BankSummary(
            bank_variant=variant.name,
            draw_count=variant.draw_count,
            cutoff=cutoffs.expanded[variant.name],
            old_domain_cutoff=cutoffs.old_domain[variant.name],
            expanded_coverage_success_count=expanded.coverage_count,
            expanded_calibrated_coverage=expanded.coverage,
            expanded_topology_success_count=expanded.topology_count,
            expanded_boundary_contact_count=expanded.boundary_count,
            expanded_median_minimum_absolute_log_rho_error=expanded.rho_error,
            expanded_median_minimum_absolute_eta_error=expanded.eta_error,
            expanded_median_projected_log_rho_width=expanded.rho_width,
            expanded_median_projected_eta_width=expanded.eta_width,
            expanded_paired_brier_interval=expanded.brier,
            expanded_mean_stochastic_brier_worst_mle=fmean(
                row.expanded_stochastic_brier_maximum for row in rows
            ),
            mean_neutral_brier=fmean(row.neutral_brier_score for row in rows),
            expanded_downstream_class=expanded_class,
            old_domain_coverage_success_count=old.coverage_count,
            old_domain_calibrated_coverage=old.coverage,
            old_domain_topology_success_count=old.topology_count,
            old_domain_boundary_contact_count=old.boundary_count,
            old_domain_median_minimum_absolute_log_rho_error=old.rho_error,
            old_domain_median_minimum_absolute_eta_error=old.eta_error,
            old_domain_median_projected_log_rho_width=old.rho_width,
            old_domain_median_projected_eta_width=old.eta_width,
            old_domain_paired_brier_interval=old.brier,
            old_domain_downstream_class=old_class,
        )
        summaries.append(summary)
        comparisons.append(
            DomainComparison(
                bank_variant=variant.name,
                expanded_cutoff=summary.cutoff.cutoff,
                old_domain_cutoff=summary.old_domain_cutoff.cutoff,
                cutoff_difference=summary.cutoff.cutoff - summary.old_domain_cutoff.cutoff,
                expanded_downstream_class=expanded_class,
                old_domain_downstream_class=old_class,
                appended_support_use_count=sum(
                    row.expanded_support_uses_appended_eta for row in rows
                ),
                appended_mle_use_count=sum(row.expanded_mle_uses_appended_eta for row in rows),
                expanded_boundary_contact_count=expanded.boundary_count,
                old_domain_boundary_contact_count=old.boundary_count,
            )
        )
    return tuple(summaries), tuple(comparisons)


def _domain_summary(
    rows: tuple[ValidationResult, ...],
    *,
    old: bool,
) -> _DomainSummary:
    if old:
        coverage_flags = tuple(row.old_domain_truth_included for row in rows)
        topology_flags = tuple(
            row.old_domain_support_component_count == 1
            and not row.old_domain_support_boundary_contact
            for row in rows
        )
        boundary_flags = tuple(row.old_domain_support_boundary_contact for row in rows)
        rho_errors = tuple(row.old_domain_minimum_absolute_log_rho_error for row in rows)
        eta_errors = tuple(row.old_domain_minimum_absolute_eta_error for row in rows)
        rho_widths = tuple(row.old_domain_projected_log_rho_width for row in rows)
        eta_widths = tuple(row.old_domain_projected_eta_width for row in rows)
        brier_values = tuple(row.old_domain_paired_brier_difference for row in rows)
    else:
        coverage_flags = tuple(row.expanded_truth_included for row in rows)
        topology_flags = tuple(
            row.expanded_support_component_count == 1 and not row.expanded_support_boundary_contact
            for row in rows
        )
        boundary_flags = tuple(row.expanded_support_boundary_contact for row in rows)
        rho_errors = tuple(row.expanded_minimum_absolute_log_rho_error for row in rows)
        eta_errors = tuple(row.expanded_minimum_absolute_eta_error for row in rows)
        rho_widths = tuple(row.expanded_projected_log_rho_width for row in rows)
        eta_widths = tuple(row.expanded_projected_eta_width for row in rows)
        brier_values = tuple(row.expanded_paired_brier_difference for row in rows)
    coverage_count = sum(coverage_flags)
    return _DomainSummary(
        coverage_count=coverage_count,
        coverage=wilson_interval(coverage_count, len(rows)),
        topology_count=sum(topology_flags),
        boundary_count=sum(boundary_flags),
        rho_error=float(median(rho_errors)),
        eta_error=float(median(eta_errors)),
        rho_width=float(median(rho_widths)),
        eta_width=float(median(eta_widths)),
        brier=normal_mean_interval(brier_values),
    )


def _evaluate_invariants(
    config: Goal011Config,
    fixed: goal007.FixedInputs,
    manifest: SeedManifest,
    bank: goal007.IntegrationBank,
    bank_replay: BankReplay,
    variants: tuple[goal007.BankVariant, ...],
    calibration: tuple[CalibrationResult, ...],
    validation: tuple[ValidationResult, ...],
    representatives: tuple[RepresentativeProfile, ...],
    summaries: tuple[BankSummary, ...],
) -> dict[str, bool]:
    streams = manifest.stream_records
    reference = goal007.spawn_seed_manifest(config.goal007_config)
    return {
        **fixed.invariants,
        "production_grid_contract": not config.is_production
        or (
            config.rhos == FROZEN_RHO_GRID
            and config.etas == FROZEN_ETA_GRID
            and config.truth_rho_index == 300
            and config.truth_eta_index == 4
        ),
        "five_phase_root_contract": all(
            record.spawn_key[0] == phase_index
            for phase_index, records in (
                (0, manifest.integration_bank),
                (1, tuple(row.process for row in manifest.calibration)),
                (2, tuple(row.process for row in manifest.validation)),
                (3, tuple(row.detection for row in manifest.calibration)),
                (4, tuple(row.detection for row in manifest.validation)),
            )
            for record in records
        ),
        "goal007_process_seed_identity": manifest.integration_bank == reference.integration_bank
        and tuple(row.process for row in manifest.calibration) == reference.calibration
        and tuple(row.process for row in manifest.validation) == reference.validation,
        "stream_counts": len(streams)
        == config.bank_size + 2 * config.calibration_replicates + 2 * config.validation_replicates,
        "stream_uniqueness": len({(row.entropy, row.spawn_key) for row in streams}) == len(streams)
        and len({row.state_words for row in streams}) == len(streams),
        "detection_stream_independence": all(
            row.detection.spawn_key[0] == 3 for row in manifest.calibration
        )
        and all(row.detection.spawn_key[0] == 4 for row in manifest.validation),
        "bank_replay": bank_replay.all_pass,
        "integration_bank_shape": bank.arrivals.shape == (config.bank_size, len(config.etas), 160),
        "bank_variants": tuple(row.name for row in variants) == BANK_VARIANT_NAMES
        and tuple(row.draw_count for row in variants)
        == (config.bank_size, config.half_bank_size, config.half_bank_size),
        "category_weight_support": all(
            row.weights.shape == (len(config.etas), len(config.rhos), 160, CATEGORY_COUNT)
            and np.isfinite(row.weights).all()
            and (row.weights > 0.0).all()
            and np.allclose(row.weights.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)
            for row in variants
        ),
        "outer_result_counts": len(calibration) == 3 * config.calibration_replicates
        and len(validation) == 3 * config.validation_replicates,
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
        "finite_likelihoods": all(
            isfinite(row.expanded_lr_at_truth)
            and isfinite(row.old_domain_lr_at_truth)
            and row.expanded_mle_cells
            and row.old_domain_mle_cells
            for row in calibration
        )
        and all(
            isfinite(row.expanded_lr_at_truth)
            and isfinite(row.old_domain_lr_at_truth)
            and row.expanded_mle_cells
            and row.old_domain_mle_cells
            for row in validation
        ),
        "separate_boundary_faces": all(
            row.expanded_support_boundary_contact == bool(row.expanded_support_boundary_faces)
            and row.old_domain_support_boundary_contact
            == bool(row.old_domain_support_boundary_faces)
            for row in validation
        ),
        "prediction_full_support": all(
            0.0
            < row.expanded_stochastic_probability_minimum
            <= row.expanded_stochastic_probability_maximum
            < 1.0
            and 0.0 < row.neutral_probability_minimum <= row.neutral_probability_maximum < 1.0
            for row in validation
        ),
        "fresh_domain_cutoffs": len(summaries) == 3
        and all(
            row.cutoff.sample_size == config.calibration_replicates
            and row.old_domain_cutoff.sample_size == config.calibration_replicates
            and row.cutoff.rank_one_based == config.calibration_rank_one_based
            and row.old_domain_cutoff.rank_one_based == config.calibration_rank_one_based
            for row in summaries
        ),
        "representative_validation_zero": len(representatives) == 3
        and tuple(row.bank_variant for row in representatives) == BANK_VARIANT_NAMES
        and all(row.dataset_index == 0 for row in representatives),
    }


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


__all__ = [
    "BANK_VARIANT_NAMES",
    "DEFAULT_CONFIG",
    "DETECTION_PROBABILITY",
    "FROZEN_ETA_GRID",
    "FROZEN_RHO_GRID",
    "HISTORICAL_GOAL007_REFERENCE",
    "OLD_ETA_GRID",
    "SOURCE_IDENTITY",
    "BankReplay",
    "BankSummary",
    "CalibrationResult",
    "DatasetSeedRecord",
    "DomainComparison",
    "Goal011Config",
    "Goal011Result",
    "ObservationSignalSummary",
    "RepresentativeProfile",
    "SeedManifest",
    "ValidationResult",
    "build_fixed_inputs",
    "build_integration_banks",
    "classify_downstream",
    "classify_outcome",
    "generate_dataset",
    "no_false_positives",
    "run_goal011",
    "smoke_config",
    "spawn_seed_manifest",
]
