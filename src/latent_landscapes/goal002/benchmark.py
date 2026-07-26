"""Fixed-design detection ensemble orchestration for Goal 002."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import hypot, isfinite

import numpy as np

from latent_landscapes.goal001.benchmark import compute_neutral_distances
from latent_landscapes.goal001.design import SamplingDesign, build_design, spawn_generators
from latent_landscapes.goal001.landscape import Landscape, build_landscape
from latent_landscapes.goal001.likelihood import (
    LR_THRESHOLD,
    RATE_DOMAIN,
    evaluate_holdout_mle,
    profile_likelihood,
)
from latent_landscapes.goal001.observations import (
    DETECTION_PROBABILITY,
    Observation,
    generate_observations,
)
from latent_landscapes.goal001.spread import TRUE_RATE, SpreadTruth, compute_spread

from .baseline import fit_time_stratified_baseline, score_time_stratified_baseline
from .calibration import (
    CALIBRATION_RANK_ONE_BASED,
    CALIBRATION_REPLICATES,
    MASTER_SEED,
    VALIDATION_REPLICATES,
    CutoffResult,
    EstimateInterval,
    MleInterval,
    SeedRecord,
    generator_from_seed_record,
    likelihood_ratio_at_truth,
    normal_mean_interval,
    order_statistic_cutoff,
    spawn_phase_seed_records,
    summarize_profile,
    wilson_interval,
)


@dataclass(frozen=True, slots=True)
class Goal002Config:
    master_seed: int = MASTER_SEED
    calibration_replicates: int = CALIBRATION_REPLICATES
    validation_replicates: int = VALIDATION_REPLICATES
    calibration_rank_one_based: int = CALIBRATION_RANK_ONE_BASED
    nominal_lr_threshold: float = LR_THRESHOLD
    truth_rate: float = TRUE_RATE

    def __post_init__(self) -> None:
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within the calibration ensemble")
        if not isfinite(self.nominal_lr_threshold) or self.nominal_lr_threshold < 0.0:
            raise ValueError("nominal LR threshold must be finite and nonnegative")
        if not RATE_DOMAIN[0] <= self.truth_rate <= RATE_DOMAIN[1]:
            raise ValueError("truth rate must lie in the frozen rate domain")

    @property
    def is_production(self) -> bool:
        return (
            self.master_seed == MASTER_SEED
            and self.calibration_replicates == CALIBRATION_REPLICATES
            and self.validation_replicates == VALIDATION_REPLICATES
            and self.calibration_rank_one_based == CALIBRATION_RANK_ONE_BASED
            and self.nominal_lr_threshold == LR_THRESHOLD
            and self.truth_rate == TRUE_RATE
        )


DEFAULT_CONFIG = Goal002Config()


@dataclass(frozen=True, slots=True)
class FixedInputs:
    landscape: Landscape
    truth: SpreadTruth
    design: SamplingDesign
    habitat_distances: dict[str, float]
    hard_front_distances: dict[str, float]
    hard_front_dmax: float
    invariants: dict[str, bool]


@dataclass(frozen=True, slots=True)
class CalibrationSummary:
    replicate_index: int
    record_count: int
    no_false_positives: bool
    lr_at_truth: float
    truth_log_likelihood: float
    maximum_log_likelihood: float


@dataclass(frozen=True, slots=True)
class ValidationSummary:
    replicate_index: int
    record_count: int
    training_record_count: int
    holdout_record_count: int
    split_isolated: bool
    no_false_positives: bool
    lr_at_truth: float
    truth_log_likelihood: float
    maximum_log_likelihood: float
    nominal_truth_included: bool
    calibrated_truth_included: bool
    calibrated_support_component_count: int
    calibrated_support_boundary_contact: bool
    calibrated_support_total_width: float
    mle_class_count: int
    mle_intervals: tuple[MleInterval, ...]
    mle_total_width: float
    truth_to_mle_distance: float
    habitat_partition_count: int
    habitat_log_score_minimum: float
    habitat_log_score_maximum: float
    habitat_brier_minimum: float
    habitat_brier_maximum: float
    habitat_impossible_positive_minimum: int
    habitat_impossible_positive_maximum: int
    habitat_any_zero_probability: bool
    habitat_every_zero_probability: bool
    neutral_log_score: float
    neutral_brier_score: float
    neutral_probability_minimum: float
    neutral_probability_maximum: float
    paired_brier_difference: float
    hard_front_partition_count: int
    hard_front_log_score_minimum: float
    hard_front_log_score_maximum: float
    hard_front_brier_minimum: float
    hard_front_brier_maximum: float
    hard_front_impossible_positive_minimum: int
    hard_front_impossible_positive_maximum: int
    hard_front_any_zero_probability: bool
    hard_front_every_zero_probability: bool


@dataclass(frozen=True, slots=True)
class AggregateSummary:
    nominal_coverage: EstimateInterval
    calibrated_coverage: EstimateInterval
    topology_success_count: int
    topology_success_proportion: float
    paired_brier_interval: EstimateInterval
    neutral_finite_count: int
    habitat_finite_all_partitions_count: int
    hard_front_finite_all_partitions_count: int
    habitat_any_zero_probability_count: int
    habitat_every_zero_probability_count: int
    hard_front_any_zero_probability_count: int
    hard_front_every_zero_probability_count: int
    mean_truth_to_mle_distance: float


@dataclass(frozen=True, slots=True)
class Goal002Result:
    config: Goal002Config
    calibration_seeds: tuple[SeedRecord, ...]
    validation_seeds: tuple[SeedRecord, ...]
    calibration_results: tuple[CalibrationSummary, ...]
    validation_results: tuple[ValidationSummary, ...]
    cutoff: CutoffResult
    aggregate: AggregateSummary
    invariants: dict[str, bool]
    outcome: str


def build_fixed_inputs() -> FixedInputs:
    landscape = build_landscape()
    truth = compute_spread(landscape)
    centre_rng, holdout_rng, _ = spawn_generators()
    design = build_design(landscape, centre_rng, holdout_rng)
    habitat_distances = {
        site.site_id: float(truth.arrival[site.row, site.col]) for site in design.sites
    }
    hard_front_distances, hard_front_dmax = compute_neutral_distances(
        landscape,
        design.sites,
    )
    invariants = _evaluate_fixed_invariants(landscape, truth, design)
    return FixedInputs(
        landscape=landscape,
        truth=truth,
        design=design,
        habitat_distances=habitat_distances,
        hard_front_distances=hard_front_distances,
        hard_front_dmax=hard_front_dmax,
        invariants=invariants,
    )


def run_calibration_phase(
    config: Goal002Config,
    fixed_inputs: FixedInputs,
) -> tuple[tuple[CalibrationSummary, ...], CutoffResult]:
    calibration_seeds, _ = spawn_phase_seed_records(
        master_seed=config.master_seed,
        calibration_count=config.calibration_replicates,
        validation_count=config.validation_replicates,
    )
    return _run_calibration_records(config, fixed_inputs, calibration_seeds)


def run_validation_phase(
    config: Goal002Config,
    fixed_inputs: FixedInputs,
    cutoff: CutoffResult,
) -> tuple[ValidationSummary, ...]:
    _, validation_seeds = spawn_phase_seed_records(
        master_seed=config.master_seed,
        calibration_count=config.calibration_replicates,
        validation_count=config.validation_replicates,
    )
    return _run_validation_records(config, fixed_inputs, cutoff, validation_seeds)


def run_goal002(
    config: Goal002Config = DEFAULT_CONFIG,
    fixed_inputs: FixedInputs | None = None,
) -> Goal002Result:
    fixed = fixed_inputs if fixed_inputs is not None else build_fixed_inputs()
    calibration_seeds, validation_seeds = spawn_phase_seed_records(
        master_seed=config.master_seed,
        calibration_count=config.calibration_replicates,
        validation_count=config.validation_replicates,
    )
    calibration_results, cutoff = _run_calibration_records(
        config,
        fixed,
        calibration_seeds,
    )
    validation_results = _run_validation_records(
        config,
        fixed,
        cutoff,
        validation_seeds,
    )
    aggregate = _aggregate_validation(validation_results)
    invariants = _evaluate_run_invariants(
        config,
        fixed,
        calibration_seeds,
        validation_seeds,
        calibration_results,
        validation_results,
        cutoff,
    )
    outcome = classify_outcome(
        invariants=invariants,
        topology_success_count=aggregate.topology_success_count,
        validation_count=len(validation_results),
        calibrated_coverage=aggregate.calibrated_coverage,
        paired_brier_interval=aggregate.paired_brier_interval,
    )
    return Goal002Result(
        config=config,
        calibration_seeds=calibration_seeds,
        validation_seeds=validation_seeds,
        calibration_results=calibration_results,
        validation_results=validation_results,
        cutoff=cutoff,
        aggregate=aggregate,
        invariants=invariants,
        outcome=outcome,
    )


def classify_outcome(
    *,
    invariants: dict[str, bool],
    topology_success_count: int,
    validation_count: int,
    calibrated_coverage: EstimateInterval,
    paired_brier_interval: EstimateInterval,
) -> str:
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if validation_count <= 0 or topology_success_count / validation_count < 0.95:
        return "design_limited"
    if not calibrated_coverage.lower <= 0.95 <= calibrated_coverage.upper:
        return "calibration_not_ready"
    if paired_brier_interval.upper >= 0.0:
        return "mechanism_inconclusive"
    return "advance_stochastic_spread"


def _run_calibration_records(
    config: Goal002Config,
    fixed: FixedInputs,
    seeds: tuple[SeedRecord, ...],
) -> tuple[tuple[CalibrationSummary, ...], CutoffResult]:
    summaries: list[CalibrationSummary] = []
    for seed in seeds:
        observations = generate_observations(
            fixed.design.sites,
            fixed.truth,
            generator_from_seed_record(seed),
        )
        profile = profile_likelihood(
            model="habitat",
            scope="all",
            distances=fixed.habitat_distances,
            records=observations,
            detection_probability=DETECTION_PROBABILITY,
        )
        lr_result = likelihood_ratio_at_truth(
            profile=profile,
            distances=fixed.habitat_distances,
            records=observations,
            detection_probability=DETECTION_PROBABILITY,
            truth_rate=config.truth_rate,
        )
        summaries.append(
            CalibrationSummary(
                replicate_index=seed.replicate_index,
                record_count=len(observations),
                no_false_positives=_no_false_positives(observations, fixed.truth),
                lr_at_truth=lr_result.statistic,
                truth_log_likelihood=lr_result.truth_log_likelihood,
                maximum_log_likelihood=lr_result.maximum_log_likelihood,
            )
        )
    cutoff = order_statistic_cutoff(
        tuple(summary.lr_at_truth for summary in summaries),
        rank_one_based=config.calibration_rank_one_based,
    )
    return tuple(summaries), cutoff


def _run_validation_records(
    config: Goal002Config,
    fixed: FixedInputs,
    cutoff: CutoffResult,
    seeds: tuple[SeedRecord, ...],
) -> tuple[ValidationSummary, ...]:
    summaries: list[ValidationSummary] = []
    for seed in seeds:
        observations = generate_observations(
            fixed.design.sites,
            fixed.truth,
            generator_from_seed_record(seed),
        )
        training = tuple(record for record in observations if record.split == "training")
        holdout = tuple(record for record in observations if record.split == "holdout")
        full_profile = profile_likelihood(
            model="habitat",
            scope="all",
            distances=fixed.habitat_distances,
            records=observations,
            detection_probability=DETECTION_PROBABILITY,
            lr_threshold=cutoff.cutoff,
        )
        lr_result = likelihood_ratio_at_truth(
            profile=full_profile,
            distances=fixed.habitat_distances,
            records=observations,
            detection_probability=DETECTION_PROBABILITY,
            truth_rate=config.truth_rate,
        )
        profile_summary = summarize_profile(full_profile, truth_rate=config.truth_rate)

        habitat_training = profile_likelihood(
            model="habitat",
            scope="training",
            distances=fixed.habitat_distances,
            records=training,
            detection_probability=DETECTION_PROBABILITY,
        )
        habitat_holdout = evaluate_holdout_mle(
            model="habitat",
            training_profile=habitat_training,
            distances=fixed.habitat_distances,
            records=holdout,
            detection_probability=DETECTION_PROBABILITY,
        )
        neutral_model = fit_time_stratified_baseline(training)
        neutral_score = score_time_stratified_baseline(neutral_model, holdout)

        hard_front_training = profile_likelihood(
            model="hard_front",
            scope="training",
            distances=fixed.hard_front_distances,
            records=training,
            detection_probability=DETECTION_PROBABILITY,
        )
        hard_front_holdout = evaluate_holdout_mle(
            model="hard_front",
            training_profile=hard_front_training,
            distances=fixed.hard_front_distances,
            records=holdout,
            detection_probability=DETECTION_PROBABILITY,
        )
        habitat_impossible = tuple(
            partition.impossible_positive_count for partition in habitat_holdout.partitions
        )
        hard_front_impossible = tuple(
            partition.impossible_positive_count for partition in hard_front_holdout.partitions
        )
        neutral_probabilities = tuple(value for _, value in neutral_model.probabilities)
        training_clusters = {record.cluster_id for record in training}
        holdout_clusters = {record.cluster_id for record in holdout}
        summaries.append(
            ValidationSummary(
                replicate_index=seed.replicate_index,
                record_count=len(observations),
                training_record_count=len(training),
                holdout_record_count=len(holdout),
                split_isolated=training_clusters.isdisjoint(holdout_clusters),
                no_false_positives=_no_false_positives(observations, fixed.truth),
                lr_at_truth=lr_result.statistic,
                truth_log_likelihood=lr_result.truth_log_likelihood,
                maximum_log_likelihood=lr_result.maximum_log_likelihood,
                nominal_truth_included=lr_result.statistic <= config.nominal_lr_threshold,
                calibrated_truth_included=profile_summary.truth_included,
                calibrated_support_component_count=profile_summary.support_component_count,
                calibrated_support_boundary_contact=profile_summary.support_boundary_contact,
                calibrated_support_total_width=profile_summary.support_total_width,
                mle_class_count=len(profile_summary.mle_intervals),
                mle_intervals=profile_summary.mle_intervals,
                mle_total_width=profile_summary.mle_total_width,
                truth_to_mle_distance=profile_summary.truth_to_mle_distance,
                habitat_partition_count=len(habitat_holdout.partitions),
                habitat_log_score_minimum=habitat_holdout.log_score_range.minimum,
                habitat_log_score_maximum=habitat_holdout.log_score_range.maximum,
                habitat_brier_minimum=habitat_holdout.brier_score_range.minimum,
                habitat_brier_maximum=habitat_holdout.brier_score_range.maximum,
                habitat_impossible_positive_minimum=int(
                    habitat_holdout.impossible_positive_range.minimum
                ),
                habitat_impossible_positive_maximum=int(
                    habitat_holdout.impossible_positive_range.maximum
                ),
                habitat_any_zero_probability=any(value > 0 for value in habitat_impossible),
                habitat_every_zero_probability=all(value > 0 for value in habitat_impossible),
                neutral_log_score=neutral_score.total_log_score,
                neutral_brier_score=neutral_score.mean_brier_score,
                neutral_probability_minimum=min(neutral_probabilities),
                neutral_probability_maximum=max(neutral_probabilities),
                paired_brier_difference=habitat_holdout.brier_score_range.maximum
                - neutral_score.mean_brier_score,
                hard_front_partition_count=len(hard_front_holdout.partitions),
                hard_front_log_score_minimum=hard_front_holdout.log_score_range.minimum,
                hard_front_log_score_maximum=hard_front_holdout.log_score_range.maximum,
                hard_front_brier_minimum=hard_front_holdout.brier_score_range.minimum,
                hard_front_brier_maximum=hard_front_holdout.brier_score_range.maximum,
                hard_front_impossible_positive_minimum=int(
                    hard_front_holdout.impossible_positive_range.minimum
                ),
                hard_front_impossible_positive_maximum=int(
                    hard_front_holdout.impossible_positive_range.maximum
                ),
                hard_front_any_zero_probability=any(value > 0 for value in hard_front_impossible),
                hard_front_every_zero_probability=all(value > 0 for value in hard_front_impossible),
            )
        )
    return tuple(summaries)


def _aggregate_validation(
    summaries: tuple[ValidationSummary, ...],
) -> AggregateSummary:
    total = len(summaries)
    nominal_count = sum(summary.nominal_truth_included for summary in summaries)
    calibrated_count = sum(summary.calibrated_truth_included for summary in summaries)
    topology_count = sum(
        summary.calibrated_support_component_count == 1
        and not summary.calibrated_support_boundary_contact
        for summary in summaries
    )
    return AggregateSummary(
        nominal_coverage=wilson_interval(nominal_count, total),
        calibrated_coverage=wilson_interval(calibrated_count, total),
        topology_success_count=topology_count,
        topology_success_proportion=topology_count / total,
        paired_brier_interval=normal_mean_interval(
            tuple(summary.paired_brier_difference for summary in summaries)
        ),
        neutral_finite_count=sum(isfinite(summary.neutral_log_score) for summary in summaries),
        habitat_finite_all_partitions_count=sum(
            isfinite(summary.habitat_log_score_minimum)
            and isfinite(summary.habitat_log_score_maximum)
            for summary in summaries
        ),
        hard_front_finite_all_partitions_count=sum(
            isfinite(summary.hard_front_log_score_minimum)
            and isfinite(summary.hard_front_log_score_maximum)
            for summary in summaries
        ),
        habitat_any_zero_probability_count=sum(
            summary.habitat_any_zero_probability for summary in summaries
        ),
        habitat_every_zero_probability_count=sum(
            summary.habitat_every_zero_probability for summary in summaries
        ),
        hard_front_any_zero_probability_count=sum(
            summary.hard_front_any_zero_probability for summary in summaries
        ),
        hard_front_every_zero_probability_count=sum(
            summary.hard_front_every_zero_probability for summary in summaries
        ),
        mean_truth_to_mle_distance=sum(summary.truth_to_mle_distance for summary in summaries)
        / total,
    )


def _evaluate_fixed_invariants(
    landscape: Landscape,
    truth: SpreadTruth,
    design: SamplingDesign,
) -> dict[str, bool]:
    cluster_counts = Counter(cluster.stratum_index for cluster in design.clusters)
    holdout_counts = Counter(
        cluster.stratum_index for cluster in design.clusters if cluster.split == "holdout"
    )
    cluster_splits = {
        cluster_id: {site.split for site in design.sites if site.cluster_id == cluster_id}
        for cluster_id in {site.cluster_id for site in design.sites}
    }
    selected_separation = all(
        hypot(left.center_row - right.center_row, left.center_col - right.center_col) >= 8.0
        for index, left in enumerate(design.clusters)
        for right in design.clusters[index + 1 :]
    )
    return {
        "landscape_reconciled": landscape.cell_count == 6048
        and int(landscape.passable.sum()) == 5225
        and int((~landscape.passable).sum()) == 823,
        "spread_reconciled": int(truth.reachable.sum()) == 5225
        and isfinite(float(truth.arrival[truth.reachable].max())),
        "source_reachability": bool(np.array_equal(landscape.source_reachable, landscape.passable)),
        "eligible_counts": Counter(candidate.stratum_index for candidate in design.eligible_centres)
        == {0: 202, 1: 122, 2: 154, 3: 157},
        "cluster_balance": cluster_counts == {0: 8, 1: 8, 2: 8, 3: 8},
        "holdout_balance": holdout_counts == {0: 2, 1: 2, 2: 2, 3: 2},
        "cluster_separation": selected_separation,
        "no_cluster_leakage": all(len(splits) == 1 for splits in cluster_splits.values()),
        "site_count": len(design.sites) == 160,
        "training_site_count": sum(site.split == "training" for site in design.sites) == 120,
        "holdout_site_count": sum(site.split == "holdout" for site in design.sites) == 40,
    }


def _evaluate_run_invariants(
    config: Goal002Config,
    fixed: FixedInputs,
    calibration_seeds: tuple[SeedRecord, ...],
    validation_seeds: tuple[SeedRecord, ...],
    calibration_results: tuple[CalibrationSummary, ...],
    validation_results: tuple[ValidationSummary, ...],
    cutoff: CutoffResult,
) -> dict[str, bool]:
    seed_states_calibration = {record.state for record in calibration_seeds}
    seed_states_validation = {record.state for record in validation_seeds}
    seed_spawn_keys_calibration = {record.spawn_key for record in calibration_seeds}
    seed_spawn_keys_validation = {record.spawn_key for record in validation_seeds}
    return {
        **fixed.invariants,
        "phase_seed_counts": len(calibration_seeds) == config.calibration_replicates
        and len(validation_seeds) == config.validation_replicates,
        "phase_seed_labels": all(record.phase == "calibration" for record in calibration_seeds)
        and all(record.phase == "validation" for record in validation_seeds),
        "phase_seed_indices": tuple(record.replicate_index for record in calibration_seeds)
        == tuple(range(config.calibration_replicates))
        and tuple(record.replicate_index for record in validation_seeds)
        == tuple(range(config.validation_replicates)),
        "phase_seed_separation": seed_states_calibration.isdisjoint(seed_states_validation)
        and seed_spawn_keys_calibration.isdisjoint(seed_spawn_keys_validation),
        "phase_seed_replay": _all_seeds_replay((*calibration_seeds, *validation_seeds)),
        "calibration_result_count": len(calibration_results) == config.calibration_replicates,
        "validation_result_count": len(validation_results) == config.validation_replicates,
        "complete_observation_generation": all(
            summary.record_count == 1920 for summary in calibration_results
        )
        and all(summary.record_count == 1920 for summary in validation_results),
        "frozen_split_counts": all(
            summary.training_record_count == 1440 and summary.holdout_record_count == 480
            for summary in validation_results
        ),
        "train_holdout_isolation": all(summary.split_isolated for summary in validation_results),
        "zero_generating_false_positives": all(
            summary.no_false_positives for summary in calibration_results
        )
        and all(summary.no_false_positives for summary in validation_results),
        "truth_likelihood_finite": all(
            isfinite(summary.lr_at_truth)
            and isfinite(summary.truth_log_likelihood)
            and isfinite(summary.maximum_log_likelihood)
            for summary in calibration_results
        )
        and all(
            isfinite(summary.lr_at_truth)
            and isfinite(summary.truth_log_likelihood)
            and isfinite(summary.maximum_log_likelihood)
            for summary in validation_results
        ),
        "cutoff_rank_reconciled": cutoff.rank_one_based == config.calibration_rank_one_based
        and cutoff.sample_size == config.calibration_replicates
        and isfinite(cutoff.cutoff),
        "calibrated_support_nonempty": all(
            summary.calibrated_support_component_count >= 1 for summary in validation_results
        ),
        "mle_sets_preserved": all(
            summary.mle_class_count == len(summary.mle_intervals) and summary.mle_class_count >= 1
            for summary in validation_results
        ),
        "neutral_full_support": all(
            isfinite(summary.neutral_log_score)
            and 0.0
            < summary.neutral_probability_minimum
            <= summary.neutral_probability_maximum
            < 1.0
            for summary in validation_results
        ),
        "paired_brier_finite": all(
            isfinite(summary.paired_brier_difference) for summary in validation_results
        ),
    }


def _all_seeds_replay(records: tuple[SeedRecord, ...]) -> bool:
    try:
        for record in records:
            generator_from_seed_record(record)
    except ValueError:
        return False
    return True


def _no_false_positives(
    observations: tuple[Observation, ...],
    truth: SpreadTruth,
) -> bool:
    return all(
        not record.detected or truth.arrival[record.row, record.col] <= record.time
        for record in observations
    )
