"""Seed, interval, and likelihood calibration primitives for Goal 002."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import NormalDist, fmean, stdev
from typing import cast

import numpy as np

from latent_landscapes.goal001.likelihood import (
    RATE_DOMAIN,
    LikelihoodProfile,
    RecordLike,
    log_likelihood,
)

MASTER_SEED = 20260726
CALIBRATION_REPLICATES = 500
VALIDATION_REPLICATES = 500
CALIBRATION_RANK_ONE_BASED = 476
CONFIDENCE_LEVEL = 0.95
_SEED_STATE_WORDS = 4


@dataclass(frozen=True, slots=True)
class SeedRecord:
    phase: str
    replicate_index: int
    entropy: int
    spawn_key: tuple[int, ...]
    state: tuple[int, ...]
    pool_size: int = 4


@dataclass(frozen=True, slots=True)
class EstimateInterval:
    estimate: float
    lower: float
    upper: float


@dataclass(frozen=True, slots=True)
class CutoffResult:
    cutoff: float
    rank_one_based: int
    sample_size: int
    probability: float


@dataclass(frozen=True, slots=True)
class LikelihoodRatioResult:
    statistic: float
    truth_log_likelihood: float
    maximum_log_likelihood: float


MleInterval = tuple[float, float, bool, bool]


@dataclass(frozen=True, slots=True)
class ProfileSummary:
    truth_included: bool
    support_component_count: int
    support_boundary_contact: bool
    support_total_width: float
    mle_intervals: tuple[MleInterval, ...]
    mle_total_width: float
    truth_to_mle_distance: float


def spawn_phase_seed_records(
    *,
    master_seed: int = MASTER_SEED,
    calibration_count: int = CALIBRATION_REPLICATES,
    validation_count: int = VALIDATION_REPLICATES,
) -> tuple[tuple[SeedRecord, ...], tuple[SeedRecord, ...]]:
    if calibration_count <= 0 or validation_count <= 0:
        raise ValueError("phase replicate counts must be positive")
    phase_roots = np.random.SeedSequence(master_seed).spawn(2)
    calibration = _spawn_phase_records("calibration", phase_roots[0], calibration_count)
    validation = _spawn_phase_records("validation", phase_roots[1], validation_count)
    return calibration, validation


def generator_from_seed_record(record: SeedRecord) -> np.random.Generator:
    if record.phase not in {"calibration", "validation"}:
        raise ValueError("unknown seed phase")
    sequence = np.random.SeedSequence(
        entropy=record.entropy,
        spawn_key=record.spawn_key,
        pool_size=record.pool_size,
    )
    replay_state = tuple(int(value) for value in sequence.generate_state(len(record.state)))
    if replay_state != record.state:
        raise ValueError("seed record state does not match replay metadata")
    return np.random.Generator(np.random.PCG64(sequence))


def order_statistic_cutoff(
    statistics: Sequence[float],
    *,
    rank_one_based: int,
    probability: float = CONFIDENCE_LEVEL,
) -> CutoffResult:
    values = tuple(float(value) for value in statistics)
    if not values:
        raise ValueError("cutoff sample must not be empty")
    if any(not isfinite(value) for value in values):
        raise ValueError("cutoff statistics must be finite")
    if not 1 <= rank_one_based <= len(values):
        raise ValueError("cutoff rank must lie within the sample")
    _validate_confidence(probability)
    return CutoffResult(
        cutoff=sorted(values)[rank_one_based - 1],
        rank_one_based=rank_one_based,
        sample_size=len(values),
        probability=probability,
    )


def calibrated_lr_cutoff(statistics: Sequence[float]) -> CutoffResult:
    if len(statistics) != CALIBRATION_REPLICATES:
        raise ValueError("calibrated cutoff requires exactly 500 statistics")
    return order_statistic_cutoff(
        statistics,
        rank_one_based=CALIBRATION_RANK_ONE_BASED,
    )


def wilson_interval(
    successes: int,
    total: int,
    confidence: float = CONFIDENCE_LEVEL,
) -> EstimateInterval:
    if total <= 0 or successes < 0 or successes > total:
        raise ValueError("Wilson counts require 0 <= successes <= total and total > 0")
    _validate_confidence(confidence)
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    proportion = successes / total
    z_squared = z * z
    denominator = 1.0 + z_squared / total
    centre = (proportion + z_squared / (2.0 * total)) / denominator
    half_width = (
        z
        * sqrt(proportion * (1.0 - proportion) / total + z_squared / (4.0 * total * total))
        / denominator
    )
    return EstimateInterval(
        estimate=proportion,
        lower=max(0.0, centre - half_width),
        upper=min(1.0, centre + half_width),
    )


def normal_mean_interval(
    values: Sequence[float],
    confidence: float = CONFIDENCE_LEVEL,
) -> EstimateInterval:
    sample = tuple(float(value) for value in values)
    if not sample:
        raise ValueError("mean interval sample must not be empty")
    if any(not isfinite(value) for value in sample):
        raise ValueError("mean interval sample must be finite")
    _validate_confidence(confidence)
    mean = fmean(sample)
    if len(sample) == 1:
        return EstimateInterval(mean, mean, mean)
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    half_width = z * stdev(sample) / sqrt(len(sample))
    return EstimateInterval(mean, mean - half_width, mean + half_width)


def likelihood_ratio_at_truth(
    *,
    profile: LikelihoodProfile,
    distances: Mapping[str, float],
    records: Sequence[RecordLike],
    detection_probability: float,
    truth_rate: float,
) -> LikelihoodRatioResult:
    truth_log_likelihood = log_likelihood(
        truth_rate,
        distances,
        records,
        detection_probability,
    )
    maximum = profile.maximum_log_likelihood
    if not isfinite(truth_log_likelihood) or not isfinite(maximum):
        raise ValueError("truth and maximum log likelihoods must be finite")
    statistic = 2.0 * (maximum - truth_log_likelihood)
    if statistic < -1e-10:
        raise ValueError("truth likelihood exceeds the profile maximum")
    return LikelihoodRatioResult(max(0.0, statistic), truth_log_likelihood, maximum)


def summarize_profile(
    profile: LikelihoodProfile,
    *,
    truth_rate: float,
    rate_domain: tuple[float, float] = RATE_DOMAIN,
) -> ProfileSummary:
    support = profile.support_components
    mle_intervals = tuple(
        (
            value.lower,
            value.upper,
            value.lower_closed,
            value.upper_closed,
        )
        for value in profile.mle_classes
    )
    return ProfileSummary(
        truth_included=any(component.contains(truth_rate) for component in support),
        support_component_count=len(support),
        support_boundary_contact=any(
            component.lower == rate_domain[0] or component.upper == rate_domain[1]
            for component in support
        ),
        support_total_width=sum(component.width for component in support),
        mle_intervals=mle_intervals,
        mle_total_width=sum(value.width for value in profile.mle_classes),
        truth_to_mle_distance=min(
            max(value.lower - truth_rate, 0.0, truth_rate - value.upper)
            for value in profile.mle_classes
        ),
    )


def _spawn_phase_records(
    phase: str,
    root: np.random.SeedSequence,
    count: int,
) -> tuple[SeedRecord, ...]:
    records: list[SeedRecord] = []
    for index, child in enumerate(root.spawn(count)):
        entropy = cast(int, child.entropy)
        records.append(
            SeedRecord(
                phase=phase,
                replicate_index=index,
                entropy=entropy,
                spawn_key=tuple(int(value) for value in child.spawn_key),
                state=tuple(int(value) for value in child.generate_state(_SEED_STATE_WORDS)),
                pool_size=child.pool_size,
            )
        )
    return tuple(records)


def _validate_confidence(value: float) -> None:
    if not 0.0 < value < 1.0:
        raise ValueError("confidence or probability must lie in (0, 1)")
