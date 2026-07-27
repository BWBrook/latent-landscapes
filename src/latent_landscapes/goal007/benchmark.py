"""Joint rho-eta calibration, validation, and bank-stability benchmark."""

from __future__ import annotations

import hashlib
import subprocess
from collections import Counter
from dataclasses import dataclass
from math import ceil, isfinite
from pathlib import Path
from statistics import fmean, median
from typing import cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal001.design import SamplingDesign, build_design, spawn_generators
from latent_landscapes.goal001.landscape import Landscape, build_landscape
from latent_landscapes.goal001.observations import Observation
from latent_landscapes.goal001.spread import passable_edges
from latent_landscapes.goal002.baseline import (
    BaselineScore as BaselineScore,
)
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
from latent_landscapes.goal004.likelihood import PredictiveScore
from latent_landscapes.goal006.spread import (
    compute_contrast_spread,
    compute_paired_spreads,
    sample_edge_shock_vector,
)

from .likelihood import (
    CATEGORY_COUNT,
    TRUTH_ETA,
    TRUTH_RHO,
    JointGridProfile,
    JointProfileSummary,
    eta_grid,
    joint_category_weights,
    joint_profile,
    record_occupancy_probabilities,
    rho_grid,
    score_predictions,
    summarize_joint_profile,
)
from .observations import (
    SURVEY_TIMES,
    CollapsedObservation,
    collapse_duplicate_visits,
    generate_perfect_observations,
    site_onset_categories,
)

MASTER_SEED = 20260730
INTEGRATION_BANK_SIZE = 4096
HALF_BANK_SIZE = 2048
CALIBRATION_REPLICATES = 500
VALIDATION_REPLICATES = 500
CALIBRATION_RANK_ONE_BASED = 476
STATE_WORD_COUNT = 4
BANK_VARIANT_NAMES = ("full", "first_half", "second_half")
FROZEN_RHO_GRID = tuple(float(value) for value in rho_grid())
FROZEN_ETA_GRID = tuple(float(value) for value in eta_grid())

SOURCE_IDENTITY = {
    "repository_commit": "559e38b4455fc8a2d2958e6e5ef0c4d59b4e4291",
    "goal001_landscape_blob": "a376df359e09b2357a0b5262479bcebaeee2ff25",
    "goal001_design_blob": "ca9c60d3f113fcde48985395652974337421dfa7",
    "goal002_neutral_baseline_blob": "f4aec0393fbba8b70b5ac6321898cde09256fd75",
    "goal003_stochastic_spread_blob": "d20440415ea33cee0f64f41427ae81197ca8fd9e",
    "goal004_observation_blob": "c97938ab640700a6584e84cc2ed8be164b582b3c",
    "goal004_likelihood_blob": "b427bdfd25e2747ca69e2272e1be2df93aa6f49e",
    "goal004_benchmark_blob": "92b5f91d7f47882c2da4b44f00f82448c44fa826",
    "goal006_contrast_spread_blob": "da0ae999dcdcfaf3b721a4f0204acc110e6560e7",
}
PINNED_SOURCE_PATHS = {
    "goal001_landscape_blob": "src/latent_landscapes/goal001/landscape.py",
    "goal001_design_blob": "src/latent_landscapes/goal001/design.py",
    "goal002_neutral_baseline_blob": "src/latent_landscapes/goal002/baseline.py",
    "goal003_stochastic_spread_blob": "src/latent_landscapes/goal003/spread.py",
    "goal004_observation_blob": "src/latent_landscapes/goal004/observations.py",
    "goal004_likelihood_blob": "src/latent_landscapes/goal004/likelihood.py",
    "goal004_benchmark_blob": "src/latent_landscapes/goal004/benchmark.py",
    "goal006_contrast_spread_blob": "src/latent_landscapes/goal006/spread.py",
}


@dataclass(frozen=True, slots=True)
class Goal007Config:
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
    def is_production(self) -> bool:
        return self == Goal007Config()


DEFAULT_CONFIG = Goal007Config()


@dataclass(frozen=True, slots=True)
class StreamSeedRecord:
    phase: str
    index: int
    stream_role: str
    entropy: int
    spawn_key: tuple[int, ...]
    state_words: tuple[int, ...]
    pool_size: int


@dataclass(frozen=True, slots=True)
class SeedManifest:
    integration_bank: tuple[StreamSeedRecord, ...]
    calibration: tuple[StreamSeedRecord, ...]
    validation: tuple[StreamSeedRecord, ...]

    @property
    def stream_records(self) -> tuple[StreamSeedRecord, ...]:
        return (*self.integration_bank, *self.calibration, *self.validation)


@dataclass(frozen=True, slots=True)
class FixedInputs:
    landscape: Landscape
    design: SamplingDesign
    invariants: dict[str, bool]


@dataclass(frozen=True, slots=True)
class IntegrationBank:
    site_ids: tuple[str, ...]
    etas: tuple[float, ...]
    arrivals: NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class BankVariant:
    name: str
    draw_start: int
    draw_end: int
    weights: NDArray[np.float64]

    @property
    def draw_count(self) -> int:
        return self.draw_end - self.draw_start


@dataclass(frozen=True, slots=True)
class PredictiveComparison:
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
class CalibrationResult:
    dataset_index: int
    bank_variant: str
    analyst_record_count: int
    distinct_outcome_count: int
    duplicate_visits_agree: bool
    truth_eta_index: int
    truth_rho_index: int
    lr_at_truth: float
    truth_log_likelihood: float
    maximum_log_likelihood: float
    mle_indices: tuple[tuple[int, int], ...]
    mle_cells: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    dataset_index: int
    bank_variant: str
    analyst_record_count: int
    distinct_outcome_count: int
    training_outcome_count: int
    holdout_outcome_count: int
    split_isolated: bool
    perfect_truth_mapping: bool
    truth_eta_index: int
    truth_rho_index: int
    lr_at_truth: float
    truth_log_likelihood: float
    maximum_log_likelihood: float
    truth_included: bool
    support_cell_count: int
    support_component_count: int
    support_boundary_contact: bool
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
    cutoff: float
    profile: JointGridProfile
    summary: JointProfileSummary


@dataclass(frozen=True, slots=True)
class BankSummary:
    bank_variant: str
    draw_count: int
    cutoff: CutoffResult
    coverage_success_count: int
    calibrated_coverage: EstimateInterval
    topology_success_count: int
    topology_success_proportion: float
    boundary_contact_count: int
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
class Goal007Result:
    config: Goal007Config
    fixed_inputs: FixedInputs
    seed_manifest: SeedManifest
    integration_bank: IntegrationBank
    bank_variants: tuple[BankVariant, ...]
    calibration_results: tuple[CalibrationResult, ...]
    validation_results: tuple[ValidationResult, ...]
    observation_signal_summary: tuple[ObservationSignalSummary, ...]
    representative_profiles: tuple[RepresentativeProfile, ...]
    bank_summaries: tuple[BankSummary, ...]
    invariants: dict[str, bool]
    outcome: str


def spawn_seed_manifest(config: Goal007Config = DEFAULT_CONFIG) -> SeedManifest:
    """Spawn exactly three phase roots and direct indexed process children."""
    phase_roots = np.random.SeedSequence(config.master_seed).spawn(3)
    integration = tuple(
        _stream_record("integration_bank", index, "paired_eta_process", child)
        for index, child in enumerate(phase_roots[0].spawn(config.bank_size))
    )
    calibration = tuple(
        _stream_record("calibration", index, "central_truth_process", child)
        for index, child in enumerate(phase_roots[1].spawn(config.calibration_replicates))
    )
    validation = tuple(
        _stream_record("validation", index, "central_truth_process", child)
        for index, child in enumerate(phase_roots[2].spawn(config.validation_replicates))
    )
    return SeedManifest(integration, calibration, validation)


def generator_from_seed_record(record: StreamSeedRecord) -> np.random.Generator:
    """Reconstruct and verify one retained PCG64 process stream."""
    expected_roles = {
        "integration_bank": "paired_eta_process",
        "calibration": "central_truth_process",
        "validation": "central_truth_process",
    }
    if expected_roles.get(record.phase) != record.stream_role:
        raise ValueError("unknown seed phase or stream role")
    sequence = np.random.SeedSequence(
        record.entropy,
        spawn_key=record.spawn_key,
        pool_size=record.pool_size,
    )
    replay = tuple(int(value) for value in sequence.generate_state(len(record.state_words)))
    if replay != record.state_words:
        raise ValueError("seed record state does not match replay metadata")
    return np.random.Generator(np.random.PCG64(sequence))


def build_fixed_inputs() -> FixedInputs:
    """Rebuild and reconcile the frozen landscape, graph, and sampling design."""
    landscape = build_landscape()
    centre_rng, holdout_rng, _ = spawn_generators()
    design = build_design(landscape, centre_rng, holdout_rng)
    cluster_counts = Counter(cluster.split for cluster in design.clusters)
    package_root = Path(__file__).resolve().parents[1]
    repository_root = package_root.parents[1]
    pinned_commit = SOURCE_IDENTITY["repository_commit"]
    commit_reconciled = _git_commit_is_ancestor(repository_root, pinned_commit)
    parent_blobs_reconciled = all(
        _git_commit_blob_sha(repository_root, pinned_commit, path) == SOURCE_IDENTITY[key]
        for key, path in PINNED_SOURCE_PATHS.items()
    )
    runtime_blobs_reconciled = all(
        _git_blob_sha(repository_root / path) == SOURCE_IDENTITY[key]
        for key, path in PINNED_SOURCE_PATHS.items()
    )
    invariants = {
        "frozen_repository_commit_reconciled": commit_reconciled,
        "frozen_parent_source_blobs_reconciled": parent_blobs_reconciled,
        "frozen_runtime_source_blobs_reconciled": runtime_blobs_reconciled,
        "frozen_source_blobs_reconciled": (
            commit_reconciled and parent_blobs_reconciled and runtime_blobs_reconciled
        ),
        "landscape_counts": landscape.shape == (72, 84)
        and int(landscape.passable.sum()) == 5225
        and int((~landscape.passable).sum()) == 823
        and int((landscape.source_zone != "").sum()) == 81,
        "graph_edge_count": len(passable_edges(landscape)) == 10120,
        "design_counts": len(design.clusters) == 32
        and len(design.sites) == 160
        and cluster_counts == {"training": 24, "holdout": 8}
        and sum(site.split == "training" for site in design.sites) == 120
        and sum(site.split == "holdout" for site in design.sites) == 40,
        "cluster_isolation": all(
            len({site.split for site in design.sites if site.cluster_id == cluster.cluster_id}) == 1
            for cluster in design.clusters
        ),
        "survey_calendar": SURVEY_TIMES == (10, 20, 30, 40, 50, 60),
        "perfect_detection": True,
        "no_detection_stream": True,
    }
    return FixedInputs(landscape, design, invariants)


def build_integration_bank(
    fixed: FixedInputs,
    records: tuple[StreamSeedRecord, ...],
    etas: tuple[float, ...] = FROZEN_ETA_GRID,
) -> IntegrationBank:
    """Retain only eta-specific arrivals at the 160 frozen survey sites."""
    sites = fixed.design.sites
    arrivals = np.empty((len(records), len(etas), len(sites)), dtype=np.float64)
    rows = np.asarray([site.row for site in sites], dtype=np.int64)
    cols = np.asarray([site.col for site in sites], dtype=np.int64)
    for record in records:
        _, truths = compute_paired_spreads(
            fixed.landscape,
            rng=generator_from_seed_record(record),
            etas=etas,
            rho=TRUTH_RHO,
        )
        arrivals[record.index] = np.stack([truth.arrival[rows, cols] for truth in truths])
    return IntegrationBank(tuple(site.site_id for site in sites), etas, arrivals)


def build_bank_variants(
    config: Goal007Config,
    bank: IntegrationBank,
) -> tuple[BankVariant, ...]:
    """Construct independently smoothed full- and disjoint half-bank weights."""
    ranges = (
        ("full", 0, config.bank_size),
        ("first_half", 0, config.half_bank_size),
        ("second_half", config.half_bank_size, config.bank_size),
    )
    rates = np.asarray(config.rhos, dtype=np.float64)
    return tuple(
        BankVariant(
            name=name,
            draw_start=start,
            draw_end=end,
            weights=joint_category_weights(bank.arrivals[start:end], rates),
        )
        for name, start, end in ranges
    )


def run_goal007(
    config: Goal007Config = DEFAULT_CONFIG,
    fixed_inputs: FixedInputs | None = None,
) -> Goal007Result:
    """Run the complete local joint positive-control benchmark."""
    fixed = fixed_inputs if fixed_inputs is not None else build_fixed_inputs()
    manifest = spawn_seed_manifest(config)
    bank = build_integration_bank(fixed, manifest.integration_bank, config.etas)
    variants = build_bank_variants(config, bank)
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
    bank_summaries = _aggregate_banks(config, variants, cutoffs, validation)
    invariants = _evaluate_invariants(
        config,
        fixed,
        manifest,
        bank,
        variants,
        calibration,
        validation,
        representatives,
        bank_summaries,
    )
    outcome = classify_outcome(
        invariants=invariants,
        downstream_classes=tuple(summary.downstream_class for summary in bank_summaries),
    )
    return Goal007Result(
        config=config,
        fixed_inputs=fixed,
        seed_manifest=manifest,
        integration_bank=bank,
        bank_variants=variants,
        calibration_results=calibration,
        validation_results=validation,
        observation_signal_summary=signals,
        representative_profiles=representatives,
        bank_summaries=bank_summaries,
        invariants=invariants,
        outcome=outcome,
    )


def summarize_predictive_comparison(
    stochastic_scores: tuple[PredictiveScore, ...],
    neutral_score: BaselineScore,
    *,
    neutral_probability_minimum: float | None = None,
    neutral_probability_maximum: float | None = None,
) -> PredictiveComparison:
    """Use the worst tied-process-MLE Brier score for the paired contrast."""
    if not stochastic_scores:
        raise ValueError("at least one process MLE score is required")
    briers = tuple(score.mean_brier_score for score in stochastic_scores)
    logs = tuple(score.total_log_score for score in stochastic_scores)
    neutral_minimum = (
        neutral_probability_minimum if neutral_probability_minimum is not None else float("nan")
    )
    neutral_maximum = (
        neutral_probability_maximum if neutral_probability_maximum is not None else float("nan")
    )
    return PredictiveComparison(
        stochastic_log_score_minimum=min(logs),
        stochastic_log_score_maximum=max(logs),
        stochastic_brier_minimum=min(briers),
        stochastic_brier_maximum=max(briers),
        stochastic_probability_minimum=min(
            score.probability_minimum for score in stochastic_scores
        ),
        stochastic_probability_maximum=max(
            score.probability_maximum for score in stochastic_scores
        ),
        neutral_log_score=neutral_score.total_log_score,
        neutral_brier_score=neutral_score.mean_brier_score,
        neutral_probability_minimum=neutral_minimum,
        neutral_probability_maximum=neutral_maximum,
        paired_brier_difference=max(briers) - neutral_score.mean_brier_score,
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
    """Apply the frozen first-matching joint scientific decision sequence."""
    if validation_count <= 0 or topology_success_count < ceil(0.95 * validation_count):
        return "joint_design_limited"
    if not calibrated_coverage.lower <= 0.95 <= calibrated_coverage.upper:
        return "joint_local_calibration_not_ready"
    if (
        median_absolute_log_rho_error > 0.10
        or median_absolute_eta_error > 0.25
        or median_projected_log_rho_width > 0.50
        or median_projected_eta_width > 0.75
    ):
        return "joint_recovery_imprecise"
    if paired_brier_interval.lower > 0.0:
        return "joint_recoverable_neutral_better"
    if paired_brier_interval.upper < 0.0:
        return "advance_to_joint_cross_truth_perfect_detection"
    return "joint_recoverable_mechanism_inconclusive"


def classify_outcome(
    *,
    invariants: dict[str, bool],
    downstream_classes: tuple[str, ...],
) -> str:
    """Apply implementation and bank-stability precedence."""
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if len(downstream_classes) != 3 or len(set(downstream_classes)) != 1:
        return "likelihood_approximation_unstable"
    return downstream_classes[0]


def _run_calibration(
    config: Goal007Config,
    fixed: FixedInputs,
    seeds: tuple[StreamSeedRecord, ...],
    site_ids: tuple[str, ...],
    variants: tuple[BankVariant, ...],
) -> tuple[CalibrationResult, ...]:
    rhos = np.asarray(config.rhos, dtype=np.float64)
    etas = np.asarray(config.etas, dtype=np.float64)
    rows: list[CalibrationResult] = []
    for seed in seeds:
        _, analyst, collapsed = _generate_dataset(fixed, seed)
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
            truth_log = float(
                profile.log_likelihoods[config.truth_eta_index, config.truth_rho_index]
            )
            rows.append(
                CalibrationResult(
                    dataset_index=seed.index,
                    bank_variant=variant.name,
                    analyst_record_count=len(analyst),
                    distinct_outcome_count=len(collapsed),
                    duplicate_visits_agree=len(analyst) == 2 * len(collapsed),
                    truth_eta_index=config.truth_eta_index,
                    truth_rho_index=config.truth_rho_index,
                    lr_at_truth=max(0.0, 2.0 * (profile.maximum_log_likelihood - truth_log)),
                    truth_log_likelihood=truth_log,
                    maximum_log_likelihood=profile.maximum_log_likelihood,
                    mle_indices=profile.mle_indices,
                    mle_cells=profile.mle_cells,
                )
            )
    return tuple(rows)


def _calibration_cutoffs(
    config: Goal007Config,
    rows: tuple[CalibrationResult, ...],
) -> dict[str, CutoffResult]:
    return {
        name: order_statistic_cutoff(
            tuple(row.lr_at_truth for row in rows if row.bank_variant == name),
            rank_one_based=config.calibration_rank_one_based,
        )
        for name in BANK_VARIANT_NAMES
    }


def _run_validation(
    config: Goal007Config,
    fixed: FixedInputs,
    seeds: tuple[StreamSeedRecord, ...],
    site_ids: tuple[str, ...],
    variants: tuple[BankVariant, ...],
    cutoffs: dict[str, CutoffResult],
) -> tuple[
    tuple[ValidationResult, ...],
    tuple[RepresentativeProfile, ...],
    tuple[ObservationSignalSummary, ...],
]:
    rhos = np.asarray(config.rhos, dtype=np.float64)
    etas = np.asarray(config.etas, dtype=np.float64)
    rows: list[ValidationResult] = []
    representatives: list[RepresentativeProfile] = []
    signals: dict[int, list[float]] = {time: [] for time in SURVEY_TIMES}
    for seed in seeds:
        truth, analyst, collapsed = _generate_dataset(fixed, seed)
        training = tuple(record for record in collapsed if record.split == "training")
        holdout = tuple(record for record in collapsed if record.split == "holdout")
        full_sites, full_categories = site_onset_categories(site_ids=site_ids, records=collapsed)
        training_sites, training_categories = site_onset_categories(
            site_ids=site_ids,
            records=training,
        )
        neutral = fit_time_stratified_baseline(training, survey_times=SURVEY_TIMES)
        neutral_score = score_time_stratified_baseline(neutral, holdout)
        neutral_probabilities = tuple(value for _, value in neutral.probabilities)
        perfect_mapping = _perfect_truth_mapping(collapsed, truth)
        split_isolated = {record.cluster_id for record in training}.isdisjoint(
            {record.cluster_id for record in holdout}
        )
        for time in SURVEY_TIMES:
            values = [record.detected for record in collapsed if record.time == time]
            signals[time].append(float(np.mean(values)))
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
            )
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
            predictive = summarize_predictive_comparison(
                process_scores,
                neutral_score,
                neutral_probability_minimum=min(neutral_probabilities),
                neutral_probability_maximum=max(neutral_probabilities),
            )
            truth_log = float(
                full_profile.log_likelihoods[config.truth_eta_index, config.truth_rho_index]
            )
            rows.append(
                ValidationResult(
                    dataset_index=seed.index,
                    bank_variant=variant.name,
                    analyst_record_count=len(analyst),
                    distinct_outcome_count=len(collapsed),
                    training_outcome_count=len(training),
                    holdout_outcome_count=len(holdout),
                    split_isolated=split_isolated,
                    perfect_truth_mapping=perfect_mapping,
                    truth_eta_index=config.truth_eta_index,
                    truth_rho_index=config.truth_rho_index,
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
                    stochastic_probability_minimum=predictive.stochastic_probability_minimum,
                    stochastic_probability_maximum=predictive.stochastic_probability_maximum,
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
                        dataset_index=0,
                        bank_variant=variant.name,
                        cutoff=cutoffs[variant.name].cutoff,
                        profile=full_profile,
                        summary=support,
                    )
                )
    signal_rows = tuple(
        ObservationSignalSummary(
            survey_time=time,
            occupied_fraction_mean=float(np.mean(values)),
            occupied_fraction_lower=float(np.quantile(values, 0.05)),
            occupied_fraction_upper=float(np.quantile(values, 0.95)),
            detected_fraction_mean=float(np.mean(values)),
            detected_fraction_lower=float(np.quantile(values, 0.05)),
            detected_fraction_upper=float(np.quantile(values, 0.95)),
        )
        for time, values in signals.items()
    )
    return tuple(rows), tuple(representatives), signal_rows


def _aggregate_banks(
    config: Goal007Config,
    variants: tuple[BankVariant, ...],
    cutoffs: dict[str, CutoffResult],
    validation: tuple[ValidationResult, ...],
) -> tuple[BankSummary, ...]:
    summaries: list[BankSummary] = []
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
        downstream = classify_downstream(
            topology_success_count=topology_count,
            validation_count=len(rows),
            calibrated_coverage=coverage,
            median_absolute_log_rho_error=rho_error,
            median_absolute_eta_error=eta_error,
            median_projected_log_rho_width=rho_width,
            median_projected_eta_width=eta_width,
            paired_brier_interval=brier,
        )
        summaries.append(
            BankSummary(
                bank_variant=variant.name,
                draw_count=variant.draw_count,
                cutoff=cutoffs[variant.name],
                coverage_success_count=coverage_count,
                calibrated_coverage=coverage,
                topology_success_count=topology_count,
                topology_success_proportion=topology_count / len(rows),
                boundary_contact_count=sum(row.support_boundary_contact for row in rows),
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
                downstream_class=downstream,
            )
        )
    return tuple(summaries)


def _evaluate_invariants(
    config: Goal007Config,
    fixed: FixedInputs,
    manifest: SeedManifest,
    bank: IntegrationBank,
    variants: tuple[BankVariant, ...],
    calibration: tuple[CalibrationResult, ...],
    validation: tuple[ValidationResult, ...],
    representatives: tuple[RepresentativeProfile, ...],
    bank_summaries: tuple[BankSummary, ...],
) -> dict[str, bool]:
    streams = manifest.stream_records
    first_rng = generator_from_seed_record(manifest.integration_bank[0])
    shocks = sample_edge_shock_vector(fixed.landscape, first_rng)
    _, replay_truths = compute_paired_spreads(
        fixed.landscape,
        edge_shocks=shocks,
        etas=config.etas,
        rho=TRUTH_RHO,
    )
    site_rows = np.asarray([site.row for site in fixed.design.sites], dtype=np.int64)
    site_cols = np.asarray([site.col for site in fixed.design.sites], dtype=np.int64)
    replay = np.stack([truth.arrival[site_rows, site_cols] for truth in replay_truths])
    truth_one = replay_truths[config.truth_eta_index]
    truth_two = compute_contrast_spread(
        fixed.landscape,
        TRUTH_ETA,
        edge_shocks=shocks,
        rho=2.0,
    )
    return {
        **fixed.invariants,
        "production_grid_contract": not config.is_production
        or (
            config.rhos == FROZEN_RHO_GRID
            and config.etas == FROZEN_ETA_GRID
            and config.truth_rho_index == 300
            and config.truth_eta_index == 4
        ),
        "phase_stream_counts": len(manifest.integration_bank) == config.bank_size
        and len(manifest.calibration) == config.calibration_replicates
        and len(manifest.validation) == config.validation_replicates
        and len(streams)
        == config.bank_size + config.calibration_replicates + config.validation_replicates,
        "stream_order_and_roles": all(
            record.phase == "integration_bank"
            and record.index == index
            and record.stream_role == "paired_eta_process"
            for index, record in enumerate(manifest.integration_bank)
        )
        and all(
            record.phase == phase
            and record.index == index
            and record.stream_role == "central_truth_process"
            for phase, records in (
                ("calibration", manifest.calibration),
                ("validation", manifest.validation),
            )
            for index, record in enumerate(records)
        ),
        "stream_uniqueness": len({(record.entropy, record.spawn_key) for record in streams})
        == len(streams)
        and len({record.state_words for record in streams}) == len(streams),
        "stream_replay": all(generator_from_seed_record(record) is not None for record in streams),
        "no_detection_stream": all("detection" not in record.stream_role for record in streams),
        "integration_bank_shape": bank.arrivals.shape == (config.bank_size, len(config.etas), 160)
        and bank.site_ids == tuple(site.site_id for site in fixed.design.sites)
        and bank.etas == config.etas,
        "integration_bank_finite": bool(
            np.isfinite(bank.arrivals).all() and (bank.arrivals >= 0.0).all()
        ),
        "integration_seed_replay": bool(np.array_equal(replay, bank.arrivals[0])),
        "paired_eta_fields_distinct": len(config.etas) == 1
        or any(
            not np.array_equal(bank.arrivals[0, 0], bank.arrivals[0, eta_index])
            for eta_index in range(1, len(config.etas))
        ),
        "eta_one_process_replay": bool(
            np.array_equal(
                truth_one.arrival[site_rows, site_cols],
                bank.arrivals[0, config.truth_eta_index],
            )
        ),
        "same_field_rate_scaling": bool(
            np.array_equal(
                truth_two.arrival[site_rows, site_cols],
                truth_one.arrival[site_rows, site_cols] / 2.0,
            )
        ),
        "bank_variants": tuple(variant.name for variant in variants) == BANK_VARIANT_NAMES
        and tuple(variant.draw_count for variant in variants)
        == (config.bank_size, config.half_bank_size, config.half_bank_size),
        "category_weight_support": all(
            variant.weights.shape == (len(config.etas), len(config.rhos), 160, CATEGORY_COUNT)
            and np.isfinite(variant.weights).all()
            and (variant.weights > 0.0).all()
            and np.allclose(variant.weights.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)
            for variant in variants
        ),
        "outer_result_counts": len(calibration) == 3 * config.calibration_replicates
        and len(validation) == 3 * config.validation_replicates,
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
        "truth_grid_exact": config.rhos[config.truth_rho_index] == TRUTH_RHO
        and config.etas[config.truth_eta_index] == TRUTH_ETA
        and all(
            row.truth_rho_index == config.truth_rho_index
            and row.truth_eta_index == config.truth_eta_index
            for row in calibration
        )
        and all(
            row.truth_rho_index == config.truth_rho_index
            and row.truth_eta_index == config.truth_eta_index
            for row in validation
        ),
        "finite_composite_likelihoods": all(
            isfinite(row.lr_at_truth)
            and isfinite(row.truth_log_likelihood)
            and isfinite(row.maximum_log_likelihood)
            for row in calibration
        )
        and all(
            isfinite(row.lr_at_truth)
            and isfinite(row.truth_log_likelihood)
            and isfinite(row.maximum_log_likelihood)
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
        "ridge_diagnostics_valid": all(
            (row.support_correlation is None and row.support_correlation_reason is not None)
            or (
                row.support_correlation is not None
                and isfinite(row.support_correlation)
                and row.support_correlation_reason is None
            )
            for row in validation
        ),
        "prediction_full_support": all(
            0.0 < row.stochastic_probability_minimum <= row.stochastic_probability_maximum < 1.0
            and 0.0 < row.neutral_probability_minimum <= row.neutral_probability_maximum < 1.0
            for row in validation
        ),
        "prediction_scores_finite": all(
            isfinite(row.stochastic_log_score_minimum)
            and isfinite(row.stochastic_log_score_maximum)
            and isfinite(row.neutral_log_score)
            and isfinite(row.paired_brier_difference)
            for row in validation
        ),
        "separate_cutoffs": len(bank_summaries) == 3
        and all(
            summary.cutoff.sample_size == config.calibration_replicates
            and summary.cutoff.rank_one_based == config.calibration_rank_one_based
            and isfinite(summary.cutoff.cutoff)
            for summary in bank_summaries
        ),
        "representative_validation_zero": len(representatives) == 3
        and tuple(row.bank_variant for row in representatives) == BANK_VARIANT_NAMES
        and all(row.dataset_index == 0 for row in representatives),
    }


def _generate_dataset(
    fixed: FixedInputs,
    seed: StreamSeedRecord,
) -> tuple[
    StochasticSpreadTruth,
    tuple[Observation, ...],
    tuple[CollapsedObservation, ...],
]:
    truth = compute_stochastic_spread(
        fixed.landscape,
        generator_from_seed_record(seed),
        rho=TRUTH_RHO,
    )
    analyst = generate_perfect_observations(fixed.design.sites, truth)
    collapsed = collapse_duplicate_visits(analyst)
    return truth, analyst, collapsed


def _perfect_truth_mapping(
    records: tuple[CollapsedObservation, ...],
    truth: StochasticSpreadTruth,
) -> bool:
    return all(
        record.detected == int(truth.arrival[record.row, record.col] <= record.time)
        for record in records
    )


def _stream_record(
    phase: str,
    index: int,
    role: str,
    sequence: np.random.SeedSequence,
) -> StreamSeedRecord:
    return StreamSeedRecord(
        phase=phase,
        index=index,
        stream_role=role,
        entropy=int(cast(int, sequence.entropy)),
        spawn_key=tuple(int(value) for value in sequence.spawn_key),
        state_words=tuple(int(value) for value in sequence.generate_state(STATE_WORD_COUNT)),
        pool_size=sequence.pool_size,
    )


def _git_blob_sha(path: Path) -> str:
    contents = path.read_bytes()
    return hashlib.sha1(f"blob {len(contents)}\0".encode() + contents).hexdigest()


def _git_commit_is_ancestor(repository_root: Path, commit: str) -> bool:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository_root), "merge-base", "--is-ancestor", commit, "HEAD"],
            check=False,
            capture_output=True,
        )
    except OSError:
        return False
    return completed.returncode == 0


def _git_commit_blob_sha(repository_root: Path, commit: str, path: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository_root), "rev-parse", f"{commit}:{path}"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


run_joint_recovery = run_goal007
