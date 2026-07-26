"""Stochastic one-rate calibration, validation, and bank-stability benchmark."""

from __future__ import annotations

import hashlib
import subprocess
from collections import Counter
from dataclasses import dataclass
from math import ceil, isfinite
from pathlib import Path
from statistics import fmean
from typing import cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal001.design import SamplingDesign, build_design, spawn_generators
from latent_landscapes.goal001.landscape import Landscape, build_landscape
from latent_landscapes.goal001.observations import Observation
from latent_landscapes.goal001.spread import passable_edges
from latent_landscapes.goal002.baseline import (
    BaselineScore,
    score_time_stratified_baseline,
)
from latent_landscapes.goal002.baseline import (
    fit_time_stratified_baseline as _fit_time_stratified_baseline,
)
from latent_landscapes.goal002.calibration import (
    CutoffResult,
    EstimateInterval,
    normal_mean_interval,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal003.spread import StochasticSpreadTruth, compute_stochastic_spread

from .likelihood import (
    CATEGORY_COUNT,
    TRUTH_RATE,
    GridProfile,
    GridProfileSummary,
    PredictiveScore,
    category_weights,
    profile_from_history_probabilities,
    rate_grid,
    record_detection_probabilities,
    score_predictions,
    site_history_probabilities,
    summarize_profile,
)
from .observations import (
    DETECTION_PROBABILITY,
    SURVEY_TIMES,
)
from .observations import (
    generate_observations as _generate_observations,
)

fit_time_stratified_baseline = _fit_time_stratified_baseline
generate_observations = _generate_observations

MASTER_SEED = 20260728
INTEGRATION_BANK_SIZE = 4096
HALF_BANK_SIZE = 2048
CALIBRATION_REPLICATES = 500
VALIDATION_REPLICATES = 500
CALIBRATION_RANK_ONE_BASED = 476
STATE_WORD_COUNT = 4
BANK_VARIANT_NAMES = ("full", "first_half", "second_half")
FROZEN_RATE_GRID = tuple(float(value) for value in rate_grid())
SOURCE_IDENTITY = {
    "repository_commit": "b7b17b611baa2b5abe9093c1f4af421f0672dfa9",
    "goal001_landscape_blob": "a376df359e09b2357a0b5262479bcebaeee2ff25",
    "goal001_design_blob": "ca9c60d3f113fcde48985395652974337421dfa7",
    "goal003_stochastic_spread_blob": "d20440415ea33cee0f64f41427ae81197ca8fd9e",
    "goal002_neutral_baseline_blob": "290cc0b608004ec75cbfa2f922d5c29f56b5271c",
}
PINNED_SOURCE_PATHS = {
    "goal001_landscape_blob": "src/latent_landscapes/goal001/landscape.py",
    "goal001_design_blob": "src/latent_landscapes/goal001/design.py",
    "goal003_stochastic_spread_blob": "src/latent_landscapes/goal003/spread.py",
    "goal002_neutral_baseline_blob": "src/latent_landscapes/goal002/baseline.py",
}


@dataclass(frozen=True, slots=True)
class Goal004Config:
    master_seed: int = MASTER_SEED
    bank_size: int = INTEGRATION_BANK_SIZE
    calibration_replicates: int = CALIBRATION_REPLICATES
    validation_replicates: int = VALIDATION_REPLICATES
    calibration_rank_one_based: int = CALIBRATION_RANK_ONE_BASED
    rates: tuple[float, ...] = FROZEN_RATE_GRID

    def __post_init__(self) -> None:
        if self.bank_size < 2 or self.bank_size % 2:
            raise ValueError("integration bank size must be positive and even")
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("outer replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within the calibration ensemble")
        values = np.asarray(self.rates, dtype=np.float64)
        if (
            values.ndim != 1
            or len(values) == 0
            or not np.isfinite(values).all()
            or (values <= 0.0).any()
            or (np.diff(values) <= 0.0).any()
        ):
            raise ValueError("rates must be finite, positive, and strictly increasing")
        if sum(value == TRUTH_RATE for value in self.rates) != 1:
            raise ValueError("rate grid must contain truth rho = 1 exactly once")

    @property
    def half_bank_size(self) -> int:
        return self.bank_size // 2

    @property
    def truth_index(self) -> int:
        return self.rates.index(TRUTH_RATE)

    @property
    def is_production(self) -> bool:
        return self == Goal004Config()


DEFAULT_CONFIG = Goal004Config()


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
class DatasetSeedRecord:
    phase: str
    index: int
    process: StreamSeedRecord
    detection: StreamSeedRecord


@dataclass(frozen=True, slots=True)
class SeedManifest:
    integration_bank: tuple[StreamSeedRecord, ...]
    calibration: tuple[DatasetSeedRecord, ...]
    validation: tuple[DatasetSeedRecord, ...]

    @property
    def stream_records(self) -> tuple[StreamSeedRecord, ...]:
        outer = tuple(
            stream
            for dataset in (*self.calibration, *self.validation)
            for stream in (dataset.process, dataset.detection)
        )
        return (*self.integration_bank, *outer)


@dataclass(frozen=True, slots=True)
class FixedInputs:
    landscape: Landscape
    design: SamplingDesign
    invariants: dict[str, bool]


@dataclass(frozen=True, slots=True)
class IntegrationBank:
    site_ids: tuple[str, ...]
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
class CalibrationSummary:
    dataset_index: int
    bank_variant: str
    record_count: int
    no_false_positives: bool
    truth_grid_index: int
    lr_at_truth: float
    truth_log_likelihood: float
    maximum_log_likelihood: float
    mle_indices: tuple[int, ...]
    mle_rates: tuple[float, ...]


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
    paired_brier_difference: float


@dataclass(frozen=True, slots=True)
class ValidationSummary:
    dataset_index: int
    bank_variant: str
    record_count: int
    training_record_count: int
    holdout_record_count: int
    split_isolated: bool
    no_false_positives: bool
    truth_grid_index: int
    lr_at_truth: float
    truth_log_likelihood: float
    maximum_log_likelihood: float
    truth_included: bool
    support_component_count: int
    support_boundary_contact: bool
    support_arithmetic_width: float
    support_log_rate_width: float
    support_indices: tuple[int, ...]
    mle_indices: tuple[int, ...]
    mle_rates: tuple[float, ...]
    truth_to_mle_set_distance: float
    absolute_log_rate_error: float
    training_mle_indices: tuple[int, ...]
    training_mle_rates: tuple[float, ...]
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
    dataset_index: int
    bank_variant: str
    cutoff: float
    profile: GridProfile
    summary: GridProfileSummary


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
    mean_support_arithmetic_width: float
    mean_support_log_rate_width: float
    mean_mle_set_size: float
    mean_truth_to_mle_set_distance: float
    mean_absolute_log_rate_error: float
    paired_brier_interval: EstimateInterval
    mean_stochastic_brier_worst_mle: float
    mean_neutral_brier: float
    finite_stochastic_log_score_count: int
    finite_neutral_log_score_count: int
    downstream_class: str


@dataclass(frozen=True, slots=True)
class Goal004Result:
    config: Goal004Config
    fixed_inputs: FixedInputs
    seed_manifest: SeedManifest
    integration_bank: IntegrationBank
    bank_variants: tuple[BankVariant, ...]
    calibration_results: tuple[CalibrationSummary, ...]
    validation_results: tuple[ValidationSummary, ...]
    representative_profiles: tuple[RepresentativeProfile, ...]
    bank_summaries: tuple[BankSummary, ...]
    invariants: dict[str, bool]
    outcome: str


def spawn_seed_manifest(config: Goal004Config = DEFAULT_CONFIG) -> SeedManifest:
    """Spawn the three frozen phase roots and all ordered child streams."""
    phase_roots = np.random.SeedSequence(config.master_seed).spawn(3)
    integration = tuple(
        _stream_record("integration_bank", index, "process", child)
        for index, child in enumerate(phase_roots[0].spawn(config.bank_size))
    )
    calibration = _dataset_records(
        "calibration",
        phase_roots[1],
        config.calibration_replicates,
    )
    validation = _dataset_records(
        "validation",
        phase_roots[2],
        config.validation_replicates,
    )
    return SeedManifest(integration, calibration, validation)


def generator_from_seed_record(record: StreamSeedRecord) -> np.random.Generator:
    """Reconstruct and verify one PCG64 stream from retained provenance."""
    if record.phase not in {"integration_bank", "calibration", "validation"}:
        raise ValueError("unknown seed phase")
    if record.stream_role not in {"process", "detection"}:
        raise ValueError("unknown stream role")
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
    """Rebuild the frozen landscape and access-constrained sampling design."""
    landscape = build_landscape()
    centre_rng, holdout_rng, _ = spawn_generators()
    design = build_design(landscape, centre_rng, holdout_rng)
    cluster_counts = Counter(cluster.split for cluster in design.clusters)
    source_count = int((landscape.source_zone != "").sum())
    package_root = Path(__file__).resolve().parents[1]
    repository_root = package_root.parents[1]
    pinned_commit = SOURCE_IDENTITY["repository_commit"]
    frozen_repository_commit_reconciled = _git_commit_is_ancestor(
        repository_root,
        pinned_commit,
    )
    frozen_parent_source_blobs_reconciled = all(
        _git_commit_blob_sha(repository_root, pinned_commit, path) == SOURCE_IDENTITY[key]
        for key, path in PINNED_SOURCE_PATHS.items()
    )
    frozen_runtime_source_blobs_reconciled = (
        _git_blob_sha(package_root / "goal001" / "landscape.py")
        == SOURCE_IDENTITY["goal001_landscape_blob"]
        and _git_blob_sha(package_root / "goal001" / "design.py")
        == SOURCE_IDENTITY["goal001_design_blob"]
        and _git_blob_sha(package_root / "goal003" / "spread.py")
        == SOURCE_IDENTITY["goal003_stochastic_spread_blob"]
    )
    invariants = {
        "frozen_repository_commit_reconciled": frozen_repository_commit_reconciled,
        "frozen_parent_source_blobs_reconciled": frozen_parent_source_blobs_reconciled,
        "frozen_runtime_source_blobs_reconciled": frozen_runtime_source_blobs_reconciled,
        "frozen_source_blobs_reconciled": frozen_repository_commit_reconciled
        and frozen_parent_source_blobs_reconciled
        and frozen_runtime_source_blobs_reconciled,
        "landscape_counts": landscape.shape == (72, 84)
        and int(landscape.passable.sum()) == 5225
        and int((~landscape.passable).sum()) == 823
        and source_count == 81,
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
        "detection_probability": DETECTION_PROBABILITY == 0.65,
    }
    return FixedInputs(landscape, design, invariants)


def build_integration_bank(
    fixed: FixedInputs,
    records: tuple[StreamSeedRecord, ...],
) -> IntegrationBank:
    """Generate complete edge fields while retaining only 160-site arrivals."""
    sites = fixed.design.sites
    arrivals = np.empty((len(records), len(sites)), dtype=np.float64)
    rows = np.asarray([site.row for site in sites], dtype=np.int64)
    cols = np.asarray([site.col for site in sites], dtype=np.int64)
    for record in records:
        truth = compute_stochastic_spread(
            fixed.landscape,
            generator_from_seed_record(record),
            rho=TRUTH_RATE,
        )
        arrivals[record.index] = truth.arrival[rows, cols]
    return IntegrationBank(tuple(site.site_id for site in sites), arrivals)


def build_bank_variants(
    config: Goal004Config,
    bank: IntegrationBank,
) -> tuple[BankVariant, ...]:
    """Construct independently smoothed full- and half-bank category weights."""
    rates = np.asarray(config.rates, dtype=np.float64)
    ranges = (
        ("full", 0, config.bank_size),
        ("first_half", 0, config.half_bank_size),
        ("second_half", config.half_bank_size, config.bank_size),
    )
    return tuple(
        BankVariant(
            name=name,
            draw_start=start,
            draw_end=end,
            weights=category_weights(bank.arrivals[start:end], rates),
        )
        for name, start, end in ranges
    )


def run_goal004(
    config: Goal004Config = DEFAULT_CONFIG,
    fixed_inputs: FixedInputs | None = None,
) -> Goal004Result:
    """Run the complete stochastic calibration, validation, and stability study."""
    fixed = fixed_inputs if fixed_inputs is not None else build_fixed_inputs()
    manifest = spawn_seed_manifest(config)
    integration_bank = build_integration_bank(fixed, manifest.integration_bank)
    bank_variants = build_bank_variants(config, integration_bank)
    calibration_results = _run_calibration(
        config,
        fixed,
        manifest.calibration,
        integration_bank.site_ids,
        bank_variants,
    )
    cutoffs = _calibration_cutoffs(config, calibration_results)
    validation_results, representative_profiles = _run_validation(
        config,
        fixed,
        manifest.validation,
        integration_bank.site_ids,
        bank_variants,
        cutoffs,
    )
    bank_summaries = _aggregate_banks(
        config,
        bank_variants,
        cutoffs,
        validation_results,
    )
    invariants = _evaluate_invariants(
        config,
        fixed,
        manifest,
        integration_bank,
        bank_variants,
        calibration_results,
        validation_results,
        representative_profiles,
        bank_summaries,
    )
    outcome = classify_outcome(
        invariants=invariants,
        downstream_classes=tuple(summary.downstream_class for summary in bank_summaries),
    )
    return Goal004Result(
        config=config,
        fixed_inputs=fixed,
        seed_manifest=manifest,
        integration_bank=integration_bank,
        bank_variants=bank_variants,
        calibration_results=calibration_results,
        validation_results=validation_results,
        representative_profiles=representative_profiles,
        bank_summaries=bank_summaries,
        invariants=invariants,
        outcome=outcome,
    )


def summarize_predictive_comparison(
    stochastic_scores: tuple[PredictiveScore, ...],
    neutral_score: BaselineScore,
) -> PredictiveComparison:
    """Use the worst stochastic training-MLE Brier score for the paired contrast."""
    if not stochastic_scores:
        raise ValueError("at least one stochastic MLE score is required")
    brier_scores = tuple(score.mean_brier_score for score in stochastic_scores)
    log_scores = tuple(score.total_log_score for score in stochastic_scores)
    return PredictiveComparison(
        stochastic_log_score_minimum=min(log_scores),
        stochastic_log_score_maximum=max(log_scores),
        stochastic_brier_minimum=min(brier_scores),
        stochastic_brier_maximum=max(brier_scores),
        stochastic_probability_minimum=min(
            score.probability_minimum for score in stochastic_scores
        ),
        stochastic_probability_maximum=max(
            score.probability_maximum for score in stochastic_scores
        ),
        neutral_log_score=neutral_score.total_log_score,
        neutral_brier_score=neutral_score.mean_brier_score,
        paired_brier_difference=max(brier_scores) - neutral_score.mean_brier_score,
    )


def classify_downstream(
    *,
    topology_success_count: int,
    validation_count: int,
    calibrated_coverage: EstimateInterval,
    paired_brier_interval: EstimateInterval,
) -> str:
    """Apply the prespecified downstream scientific decision sequence."""
    if validation_count <= 0 or topology_success_count < ceil(0.95 * validation_count):
        return "design_limited"
    if not calibrated_coverage.lower <= 0.95 <= calibrated_coverage.upper:
        return "calibration_not_ready"
    if paired_brier_interval.lower > 0.0:
        return "rate_recoverable_neutral_better"
    if paired_brier_interval.upper < 0.0:
        return "advance_one_rate_stochastic_spread"
    return "rate_recoverable_mechanism_inconclusive"


def classify_outcome(
    *,
    invariants: dict[str, bool],
    downstream_classes: tuple[str, ...],
) -> str:
    """Apply implementation and bank-stability gates before scientific classes."""
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if len(downstream_classes) != 3 or len(set(downstream_classes)) != 1:
        return "likelihood_approximation_unstable"
    return downstream_classes[0]


def _run_calibration(
    config: Goal004Config,
    fixed: FixedInputs,
    seeds: tuple[DatasetSeedRecord, ...],
    site_ids: tuple[str, ...],
    variants: tuple[BankVariant, ...],
) -> tuple[CalibrationSummary, ...]:
    rates = np.asarray(config.rates, dtype=np.float64)
    rows: list[CalibrationSummary] = []
    for seed in seeds:
        truth, observations = _generate_dataset(fixed, seed)
        history_sites, histories = site_history_probabilities(
            site_ids=site_ids,
            records=observations,
        )
        no_false_positives = _no_false_positives(observations, truth)
        for variant in variants:
            profile = profile_from_history_probabilities(
                weights=variant.weights,
                rates=rates,
                bank_site_ids=site_ids,
                history_site_ids=history_sites,
                history_probabilities=histories,
                scope="all",
            )
            truth_log_likelihood = float(profile.log_likelihoods[config.truth_index])
            rows.append(
                CalibrationSummary(
                    dataset_index=seed.index,
                    bank_variant=variant.name,
                    record_count=len(observations),
                    no_false_positives=no_false_positives,
                    truth_grid_index=config.truth_index,
                    lr_at_truth=max(
                        0.0,
                        2.0 * (profile.maximum_log_likelihood - truth_log_likelihood),
                    ),
                    truth_log_likelihood=truth_log_likelihood,
                    maximum_log_likelihood=profile.maximum_log_likelihood,
                    mle_indices=profile.mle_indices,
                    mle_rates=profile.mle_rates,
                )
            )
    return tuple(rows)


def _calibration_cutoffs(
    config: Goal004Config,
    rows: tuple[CalibrationSummary, ...],
) -> dict[str, CutoffResult]:
    return {
        name: order_statistic_cutoff(
            tuple(row.lr_at_truth for row in rows if row.bank_variant == name),
            rank_one_based=config.calibration_rank_one_based,
        )
        for name in BANK_VARIANT_NAMES
    }


def _run_validation(
    config: Goal004Config,
    fixed: FixedInputs,
    seeds: tuple[DatasetSeedRecord, ...],
    site_ids: tuple[str, ...],
    variants: tuple[BankVariant, ...],
    cutoffs: dict[str, CutoffResult],
) -> tuple[tuple[ValidationSummary, ...], tuple[RepresentativeProfile, ...]]:
    rates = np.asarray(config.rates, dtype=np.float64)
    rows: list[ValidationSummary] = []
    representatives: list[RepresentativeProfile] = []
    for seed in seeds:
        truth, observations = _generate_dataset(fixed, seed)
        training = tuple(record for record in observations if record.split == "training")
        holdout = tuple(record for record in observations if record.split == "holdout")
        full_sites, full_histories = site_history_probabilities(
            site_ids=site_ids,
            records=observations,
        )
        training_sites, training_histories = site_history_probabilities(
            site_ids=site_ids,
            records=training,
        )
        neutral_model = fit_time_stratified_baseline(training, survey_times=SURVEY_TIMES)
        neutral_score = score_time_stratified_baseline(neutral_model, holdout)
        neutral_probabilities = tuple(value for _, value in neutral_model.probabilities)
        no_false_positives = _no_false_positives(observations, truth)
        split_isolated = {record.cluster_id for record in training}.isdisjoint(
            {record.cluster_id for record in holdout}
        )
        for variant in variants:
            full_profile = profile_from_history_probabilities(
                weights=variant.weights,
                rates=rates,
                bank_site_ids=site_ids,
                history_site_ids=full_sites,
                history_probabilities=full_histories,
                scope="all",
            )
            summary = summarize_profile(
                full_profile,
                cutoff=cutoffs[variant.name].cutoff,
                truth_rate=TRUTH_RATE,
            )
            training_profile = profile_from_history_probabilities(
                weights=variant.weights,
                rates=rates,
                bank_site_ids=site_ids,
                history_site_ids=training_sites,
                history_probabilities=training_histories,
                scope="training",
            )
            stochastic_scores = tuple(
                score_predictions(
                    record_detection_probabilities(
                        weights=variant.weights[index],
                        site_ids=site_ids,
                        records=holdout,
                    ),
                    holdout,
                )
                for index in training_profile.mle_indices
            )
            predictive = summarize_predictive_comparison(stochastic_scores, neutral_score)
            truth_log_likelihood = float(full_profile.log_likelihoods[config.truth_index])
            rows.append(
                ValidationSummary(
                    dataset_index=seed.index,
                    bank_variant=variant.name,
                    record_count=len(observations),
                    training_record_count=len(training),
                    holdout_record_count=len(holdout),
                    split_isolated=split_isolated,
                    no_false_positives=no_false_positives,
                    truth_grid_index=config.truth_index,
                    lr_at_truth=max(
                        0.0,
                        2.0 * (full_profile.maximum_log_likelihood - truth_log_likelihood),
                    ),
                    truth_log_likelihood=truth_log_likelihood,
                    maximum_log_likelihood=full_profile.maximum_log_likelihood,
                    truth_included=summary.truth_included,
                    support_component_count=len(summary.support_components),
                    support_boundary_contact=summary.support_boundary_contact,
                    support_arithmetic_width=summary.support_arithmetic_width,
                    support_log_rate_width=summary.support_log_rate_width,
                    support_indices=summary.support_indices,
                    mle_indices=summary.mle_indices,
                    mle_rates=summary.mle_rates,
                    truth_to_mle_set_distance=summary.truth_to_mle_set_distance,
                    absolute_log_rate_error=summary.absolute_log_rate_error,
                    training_mle_indices=training_profile.mle_indices,
                    training_mle_rates=training_profile.mle_rates,
                    stochastic_log_score_minimum=predictive.stochastic_log_score_minimum,
                    stochastic_log_score_maximum=predictive.stochastic_log_score_maximum,
                    stochastic_brier_minimum=predictive.stochastic_brier_minimum,
                    stochastic_brier_maximum=predictive.stochastic_brier_maximum,
                    stochastic_probability_minimum=predictive.stochastic_probability_minimum,
                    stochastic_probability_maximum=predictive.stochastic_probability_maximum,
                    neutral_log_score=predictive.neutral_log_score,
                    neutral_brier_score=predictive.neutral_brier_score,
                    neutral_probability_minimum=min(neutral_probabilities),
                    neutral_probability_maximum=max(neutral_probabilities),
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
                        summary=summary,
                    )
                )
    return tuple(rows), tuple(representatives)


def _aggregate_banks(
    config: Goal004Config,
    variants: tuple[BankVariant, ...],
    cutoffs: dict[str, CutoffResult],
    validation: tuple[ValidationSummary, ...],
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
        downstream = classify_downstream(
            topology_success_count=topology_count,
            validation_count=len(rows),
            calibrated_coverage=coverage,
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
                mean_support_arithmetic_width=fmean(row.support_arithmetic_width for row in rows),
                mean_support_log_rate_width=fmean(row.support_log_rate_width for row in rows),
                mean_mle_set_size=fmean(len(row.mle_indices) for row in rows),
                mean_truth_to_mle_set_distance=fmean(row.truth_to_mle_set_distance for row in rows),
                mean_absolute_log_rate_error=fmean(row.absolute_log_rate_error for row in rows),
                paired_brier_interval=brier,
                mean_stochastic_brier_worst_mle=fmean(row.stochastic_brier_maximum for row in rows),
                mean_neutral_brier=fmean(row.neutral_brier_score for row in rows),
                finite_stochastic_log_score_count=sum(
                    isfinite(row.stochastic_log_score_minimum)
                    and isfinite(row.stochastic_log_score_maximum)
                    for row in rows
                ),
                finite_neutral_log_score_count=sum(isfinite(row.neutral_log_score) for row in rows),
                downstream_class=downstream,
            )
        )
    return tuple(summaries)


def _evaluate_invariants(
    config: Goal004Config,
    fixed: FixedInputs,
    manifest: SeedManifest,
    bank: IntegrationBank,
    variants: tuple[BankVariant, ...],
    calibration: tuple[CalibrationSummary, ...],
    validation: tuple[ValidationSummary, ...],
    representatives: tuple[RepresentativeProfile, ...],
    bank_summaries: tuple[BankSummary, ...],
) -> dict[str, bool]:
    streams = manifest.stream_records
    rows = np.asarray([site.row for site in fixed.design.sites], dtype=np.int64)
    cols = np.asarray([site.col for site in fixed.design.sites], dtype=np.int64)
    replay_one = compute_stochastic_spread(
        fixed.landscape,
        generator_from_seed_record(manifest.integration_bank[0]),
        rho=1.0,
    ).arrival[rows, cols]
    replay_two = compute_stochastic_spread(
        fixed.landscape,
        generator_from_seed_record(manifest.integration_bank[0]),
        rho=2.0,
    ).arrival[rows, cols]
    return {
        **fixed.invariants,
        "phase_stream_counts": len(manifest.integration_bank) == config.bank_size
        and len(manifest.calibration) == config.calibration_replicates
        and len(manifest.validation) == config.validation_replicates
        and len(streams)
        == config.bank_size + 2 * config.calibration_replicates + 2 * config.validation_replicates,
        "stream_order_and_roles": all(
            record.phase == "integration_bank"
            and record.index == index
            and record.stream_role == "process"
            for index, record in enumerate(manifest.integration_bank)
        )
        and all(
            dataset.index == index
            and dataset.process.stream_role == "process"
            and dataset.detection.stream_role == "detection"
            and dataset.process.spawn_key[-1] == 0
            and dataset.detection.spawn_key[-1] == 1
            for datasets in (manifest.calibration, manifest.validation)
            for index, dataset in enumerate(datasets)
        ),
        "stream_uniqueness": len({(record.entropy, record.spawn_key) for record in streams})
        == len(streams)
        and len({record.state_words for record in streams}) == len(streams),
        "stream_replay": _all_streams_replay(streams),
        "integration_bank_shape": bank.arrivals.shape == (config.bank_size, 160)
        and bank.site_ids == tuple(site.site_id for site in fixed.design.sites),
        "integration_bank_finite": bool(
            np.isfinite(bank.arrivals).all() and (bank.arrivals >= 0.0).all()
        ),
        "integration_seed_replay": bool(np.array_equal(replay_one, bank.arrivals[0])),
        "same_field_rate_scaling": bool(np.array_equal(replay_two, bank.arrivals[0] / 2.0)),
        "bank_variants": tuple(variant.name for variant in variants) == BANK_VARIANT_NAMES
        and tuple(variant.draw_count for variant in variants)
        == (config.bank_size, config.half_bank_size, config.half_bank_size),
        "category_weight_support": all(
            variant.weights.shape == (len(config.rates), 160, CATEGORY_COUNT)
            and np.isfinite(variant.weights).all()
            and (variant.weights > 0.0).all()
            and np.allclose(variant.weights.sum(axis=2), 1.0, rtol=0.0, atol=1e-12)
            for variant in variants
        ),
        "outer_result_counts": len(calibration) == 3 * config.calibration_replicates
        and len(validation) == 3 * config.validation_replicates,
        "complete_joint_observations": all(row.record_count == 1920 for row in calibration)
        and all(
            row.record_count == 1920
            and row.training_record_count == 1440
            and row.holdout_record_count == 480
            for row in validation
        ),
        "zero_false_positives": all(row.no_false_positives for row in calibration)
        and all(row.no_false_positives for row in validation),
        "train_holdout_isolation": all(row.split_isolated for row in validation),
        "truth_grid_exact": config.rates[config.truth_index] == 1.0
        and all(row.truth_grid_index == config.truth_index for row in calibration)
        and all(row.truth_grid_index == config.truth_index for row in validation),
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
        "mle_sets_preserved": all(row.mle_indices and row.mle_rates for row in calibration)
        and all(
            row.mle_indices
            and row.mle_rates
            and row.training_mle_indices
            and row.training_mle_rates
            for row in validation
        ),
        "calibrated_supports_preserved": all(
            row.support_indices and row.support_component_count >= 1 for row in validation
        ),
        "prediction_full_support": all(
            0.0 < row.stochastic_probability_minimum <= row.stochastic_probability_maximum < 1.0
            and 0.0 < row.neutral_probability_minimum <= row.neutral_probability_maximum < 1.0
            for row in validation
        ),
        "prediction_scores_finite": all(
            isfinite(row.stochastic_log_score_minimum)
            and isfinite(row.stochastic_log_score_maximum)
            and isfinite(row.paired_brier_difference)
            and isfinite(row.neutral_log_score)
            for row in validation
        ),
        "separate_cutoffs": len(bank_summaries) == 3
        and all(
            summary.cutoff.sample_size == config.calibration_replicates
            and summary.cutoff.rank_one_based == config.calibration_rank_one_based
            and isfinite(summary.cutoff.cutoff)
            for summary in bank_summaries
        ),
        "representative_replicate_zero": len(representatives) == 3
        and tuple(value.bank_variant for value in representatives) == BANK_VARIANT_NAMES
        and all(value.dataset_index == 0 for value in representatives),
    }


def _generate_dataset(
    fixed: FixedInputs,
    seed: DatasetSeedRecord,
) -> tuple[StochasticSpreadTruth, tuple[Observation, ...]]:
    truth = compute_stochastic_spread(
        fixed.landscape,
        generator_from_seed_record(seed.process),
        rho=TRUTH_RATE,
    )
    observations = generate_observations(
        fixed.design.sites,
        truth,
        generator_from_seed_record(seed.detection),
    )
    return truth, observations


def _no_false_positives(
    records: tuple[Observation, ...],
    truth: StochasticSpreadTruth,
) -> bool:
    return all(
        not record.detected or truth.arrival[record.row, record.col] <= record.time
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


def _dataset_records(
    phase: str,
    root: np.random.SeedSequence,
    count: int,
) -> tuple[DatasetSeedRecord, ...]:
    records: list[DatasetSeedRecord] = []
    for index, dataset_child in enumerate(root.spawn(count)):
        process, detection = dataset_child.spawn(2)
        records.append(
            DatasetSeedRecord(
                phase=phase,
                index=index,
                process=_stream_record(phase, index, "process", process),
                detection=_stream_record(phase, index, "detection", detection),
            )
        )
    return tuple(records)


def _all_streams_replay(records: tuple[StreamSeedRecord, ...]) -> bool:
    try:
        for record in records:
            generator_from_seed_record(record)
    except ValueError:
        return False
    return True


def _git_blob_sha(path: Path) -> str:
    contents = path.read_bytes()
    payload = f"blob {len(contents)}\0".encode() + contents
    return hashlib.sha1(payload).hexdigest()


def _git_commit_is_ancestor(repository_root: Path, commit: str) -> bool:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository_root), "merge-base", "--is-ancestor", commit, "HEAD"],
            check=False,
            capture_output=True,
            text=True,
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
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


run_stochastic_recovery = run_goal004
