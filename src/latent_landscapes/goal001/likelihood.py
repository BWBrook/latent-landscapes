"""Exact breakpoint likelihood and held-out scoring for Goal 001."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import inf, isclose, log
from typing import Protocol

RATE_DOMAIN = (0.25, 4.0)
LR_THRESHOLD = 3.841458820694124


class RecordLike(Protocol):
    @property
    def site_id(self) -> str: ...

    @property
    def time(self) -> float: ...

    @property
    def detected(self) -> int: ...


@dataclass(frozen=True, slots=True)
class Interval:
    lower: float
    upper: float
    lower_closed: bool
    upper_closed: bool

    @property
    def width(self) -> float:
        return self.upper - self.lower

    def contains(self, value: float) -> bool:
        above_lower = value > self.lower or (self.lower_closed and value == self.lower)
        below_upper = value < self.upper or (self.upper_closed and value == self.upper)
        return above_lower and below_upper


@dataclass(frozen=True, slots=True)
class LikelihoodClass:
    model: str
    scope: str
    lower: float
    upper: float
    lower_closed: bool
    upper_closed: bool
    representative_rate: float
    log_likelihood: float
    prediction_signature: tuple[bool, ...]

    @property
    def width(self) -> float:
        return self.upper - self.lower

    def as_interval(self) -> Interval:
        return Interval(self.lower, self.upper, self.lower_closed, self.upper_closed)


@dataclass(frozen=True, slots=True)
class LikelihoodProfile:
    model: str
    scope: str
    classes: tuple[LikelihoodClass, ...]
    mle_classes: tuple[LikelihoodClass, ...]
    support_classes: tuple[LikelihoodClass, ...]
    support_components: tuple[Interval, ...]
    maximum_log_likelihood: float
    raw_breakpoint_count: int
    clipped_unique_breakpoints: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class ScoreRange:
    minimum: float
    maximum: float


@dataclass(frozen=True, slots=True)
class HoldoutPartition:
    model: str
    lower: float
    upper: float
    lower_closed: bool
    upper_closed: bool
    representative_rate: float
    log_score: float
    brier_score: float
    impossible_positive_count: int

    @property
    def width(self) -> float:
        return self.upper - self.lower


@dataclass(frozen=True, slots=True)
class HoldoutEvaluation:
    model: str
    partitions: tuple[HoldoutPartition, ...]
    log_score_range: ScoreRange
    brier_score_range: ScoreRange
    impossible_positive_range: ScoreRange


@dataclass(frozen=True, slots=True)
class _Region:
    lower: float
    upper: float
    lower_closed: bool
    upper_closed: bool
    signature: tuple[bool, ...]

    @property
    def representative(self) -> float:
        if self.lower == self.upper:
            return self.lower
        return (self.lower + self.upper) / 2.0


def log_likelihood(
    rate: float,
    distances: Mapping[str, float],
    records: Sequence[RecordLike],
    detection_probability: float,
) -> float:
    _validate_probability(detection_probability)
    if rate <= 0.0:
        raise ValueError("rate must be positive")
    total = 0.0
    for record in records:
        occupied = distances[record.site_id] / rate <= record.time
        if not occupied:
            if record.detected:
                return -inf
            continue
        total += log(detection_probability if record.detected else 1.0 - detection_probability)
    return total


def profile_likelihood(
    *,
    model: str,
    scope: str,
    distances: Mapping[str, float],
    records: Sequence[RecordLike],
    detection_probability: float,
    rate_domain: tuple[float, float] = RATE_DOMAIN,
) -> LikelihoodProfile:
    _validate_domain(rate_domain)
    raw_breakpoints = tuple(distances[record.site_id] / record.time for record in records)
    clipped_breakpoints = tuple(
        sorted({min(max(value, rate_domain[0]), rate_domain[1]) for value in raw_breakpoints})
    )
    regions = _equivalence_regions(distances, records, rate_domain)
    classes = tuple(
        LikelihoodClass(
            model=model,
            scope=scope,
            lower=region.lower,
            upper=region.upper,
            lower_closed=region.lower_closed,
            upper_closed=region.upper_closed,
            representative_rate=region.representative,
            log_likelihood=log_likelihood(
                region.representative, distances, records, detection_probability
            ),
            prediction_signature=region.signature,
        )
        for region in regions
    )
    maximum = max(value.log_likelihood for value in classes)
    mle_classes = tuple(value for value in classes if _same_score(value.log_likelihood, maximum))
    support_classes = tuple(
        value
        for value in classes
        if value.log_likelihood != -inf and 2.0 * (maximum - value.log_likelihood) <= LR_THRESHOLD
    )
    support_components = _union_intervals(tuple(value.as_interval() for value in support_classes))
    return LikelihoodProfile(
        model=model,
        scope=scope,
        classes=classes,
        mle_classes=mle_classes,
        support_classes=support_classes,
        support_components=support_components,
        maximum_log_likelihood=maximum,
        raw_breakpoint_count=len(raw_breakpoints),
        clipped_unique_breakpoints=clipped_breakpoints,
    )


def evaluate_holdout_mle(
    *,
    model: str,
    training_profile: LikelihoodProfile,
    distances: Mapping[str, float],
    records: Sequence[RecordLike],
    detection_probability: float,
) -> HoldoutEvaluation:
    holdout_regions = _equivalence_regions(distances, records, RATE_DOMAIN)
    partitions: list[HoldoutPartition] = []
    for mle_class in training_profile.mle_classes:
        mle_interval = mle_class.as_interval()
        for region in holdout_regions:
            intersection = _intersection(
                mle_interval,
                Interval(
                    region.lower,
                    region.upper,
                    region.lower_closed,
                    region.upper_closed,
                ),
            )
            if intersection is None:
                continue
            representative = (
                intersection.lower
                if intersection.lower == intersection.upper
                else (intersection.lower + intersection.upper) / 2.0
            )
            log_score, brier, impossible = holdout_scores(
                representative,
                distances,
                records,
                detection_probability,
            )
            partitions.append(
                HoldoutPartition(
                    model=model,
                    lower=intersection.lower,
                    upper=intersection.upper,
                    lower_closed=intersection.lower_closed,
                    upper_closed=intersection.upper_closed,
                    representative_rate=representative,
                    log_score=log_score,
                    brier_score=brier,
                    impossible_positive_count=impossible,
                )
            )
    partitions.sort(key=lambda value: (value.lower, value.upper, value.representative_rate))
    log_scores = [value.log_score for value in partitions]
    brier_scores = [value.brier_score for value in partitions]
    impossible_counts = [value.impossible_positive_count for value in partitions]
    return HoldoutEvaluation(
        model=model,
        partitions=tuple(partitions),
        log_score_range=ScoreRange(min(log_scores), max(log_scores)),
        brier_score_range=ScoreRange(min(brier_scores), max(brier_scores)),
        impossible_positive_range=ScoreRange(
            float(min(impossible_counts)), float(max(impossible_counts))
        ),
    )


def holdout_scores(
    rate: float,
    distances: Mapping[str, float],
    records: Sequence[RecordLike],
    detection_probability: float,
) -> tuple[float, float, int]:
    log_score = log_likelihood(rate, distances, records, detection_probability)
    squared_errors = 0.0
    impossible = 0
    for record in records:
        occupied = distances[record.site_id] / rate <= record.time
        prediction = detection_probability if occupied else 0.0
        squared_errors += (record.detected - prediction) ** 2
        impossible += int(bool(record.detected) and not occupied)
    brier = squared_errors / len(records) if records else 0.0
    return log_score, brier, impossible


def compare_holdout_log_scores(habitat: ScoreRange, neutral: ScoreRange) -> str:
    if habitat.minimum > neutral.maximum:
        return "habitat_robustly_better"
    if neutral.minimum > habitat.maximum:
        return "neutral_robustly_better"
    return "inconclusive"


def ideal_process_identifiable(
    full_landscape_distances: Sequence[float],
    rate_domain: tuple[float, float] = RATE_DOMAIN,
) -> bool:
    _validate_domain(rate_domain)
    return any(value > 0.0 for value in full_landscape_distances)


def _equivalence_regions(
    distances: Mapping[str, float],
    records: Sequence[RecordLike],
    rate_domain: tuple[float, float],
) -> tuple[_Region, ...]:
    lower, upper = rate_domain
    in_domain_breakpoints = {
        distances[record.site_id] / record.time
        for record in records
        if lower <= distances[record.site_id] / record.time <= upper
    }
    points = sorted({lower, upper, *in_domain_breakpoints})
    atomic: list[_Region] = []
    for index, point in enumerate(points):
        atomic.append(
            _Region(point, point, True, True, _prediction_signature(point, distances, records))
        )
        if index == len(points) - 1:
            continue
        next_point = points[index + 1]
        if point < next_point:
            representative = (point + next_point) / 2.0
            atomic.append(
                _Region(
                    point,
                    next_point,
                    False,
                    False,
                    _prediction_signature(representative, distances, records),
                )
            )
    return _merge_signature_regions(tuple(atomic))


def _prediction_signature(
    rate: float,
    distances: Mapping[str, float],
    records: Sequence[RecordLike],
) -> tuple[bool, ...]:
    return tuple(distances[record.site_id] / rate <= record.time for record in records)


def _merge_signature_regions(regions: tuple[_Region, ...]) -> tuple[_Region, ...]:
    merged: list[_Region] = []
    for region in regions:
        if (
            merged
            and merged[-1].signature == region.signature
            and merged[-1].upper == region.lower
            and (merged[-1].upper_closed or region.lower_closed)
        ):
            prior = merged[-1]
            merged[-1] = _Region(
                lower=prior.lower,
                upper=region.upper,
                lower_closed=prior.lower_closed,
                upper_closed=region.upper_closed,
                signature=prior.signature,
            )
        else:
            merged.append(region)
    return tuple(merged)


def _union_intervals(intervals: tuple[Interval, ...]) -> tuple[Interval, ...]:
    merged: list[Interval] = []
    for interval in intervals:
        if (
            merged
            and merged[-1].upper == interval.lower
            and (merged[-1].upper_closed or interval.lower_closed)
        ):
            prior = merged[-1]
            merged[-1] = Interval(
                prior.lower,
                interval.upper,
                prior.lower_closed,
                interval.upper_closed,
            )
        else:
            merged.append(interval)
    return tuple(merged)


def _intersection(left: Interval, right: Interval) -> Interval | None:
    lower = max(left.lower, right.lower)
    upper = min(left.upper, right.upper)
    if left.lower > right.lower:
        lower_closed = left.lower_closed
    elif right.lower > left.lower:
        lower_closed = right.lower_closed
    else:
        lower_closed = left.lower_closed and right.lower_closed
    if left.upper < right.upper:
        upper_closed = left.upper_closed
    elif right.upper < left.upper:
        upper_closed = right.upper_closed
    else:
        upper_closed = left.upper_closed and right.upper_closed
    if lower < upper or (lower == upper and lower_closed and upper_closed):
        return Interval(lower, upper, lower_closed, upper_closed)
    return None


def _same_score(left: float, right: float) -> bool:
    return left == right or isclose(left, right, rel_tol=0.0, abs_tol=1e-12)


def _validate_domain(rate_domain: tuple[float, float]) -> None:
    if not 0.0 < rate_domain[0] < rate_domain[1]:
        raise ValueError("rate domain must be positive and increasing")


def _validate_probability(value: float) -> None:
    if not 0.0 < value < 1.0:
        raise ValueError("detection probability must lie in (0, 1)")
