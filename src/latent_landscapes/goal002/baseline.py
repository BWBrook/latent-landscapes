"""Full-support time-stratified neutral detection baseline for Goal 002."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from math import isfinite, log
from typing import Protocol

from latent_landscapes.goal001.observations import SURVEY_TIMES


class TimeRecordLike(Protocol):
    @property
    def time(self) -> int: ...

    @property
    def detected(self) -> int: ...


@dataclass(frozen=True, slots=True)
class TimeStratifiedBaseline:
    probabilities: tuple[tuple[int, float], ...]
    survey_times: tuple[int, ...] = SURVEY_TIMES

    def __post_init__(self) -> None:
        times = tuple(time for time, _ in self.probabilities)
        _validate_calendar(self.survey_times)
        if times != self.survey_times:
            raise ValueError("baseline probabilities must cover the frozen survey times")
        if any(not isfinite(value) or not 0.0 < value < 1.0 for _, value in self.probabilities):
            raise ValueError("baseline probabilities must be finite and lie in (0, 1)")

    def probability(self, time: int) -> float:
        for candidate, value in self.probabilities:
            if candidate == time:
                return value
        raise ValueError(f"unknown survey time: {time}")


@dataclass(frozen=True, slots=True)
class BaselineScore:
    total_log_score: float
    mean_brier_score: float
    record_count: int


def fit_time_stratified_baseline(
    training_records: Sequence[TimeRecordLike],
    *,
    survey_times: tuple[int, ...] = SURVEY_TIMES,
) -> TimeStratifiedBaseline:
    _validate_calendar(survey_times)
    detections: Counter[int] = Counter()
    counts: Counter[int] = Counter()
    for record in training_records:
        _validate_record(record, survey_times)
        counts[record.time] += 1
        detections[record.time] += record.detected
    missing = tuple(time for time in survey_times if counts[time] == 0)
    if missing:
        raise ValueError(f"missing survey time strata: {missing}")
    return TimeStratifiedBaseline(
        tuple((time, (detections[time] + 0.5) / (counts[time] + 1.0)) for time in survey_times),
        survey_times,
    )


def score_time_stratified_baseline(
    model: TimeStratifiedBaseline,
    holdout_records: Sequence[TimeRecordLike],
) -> BaselineScore:
    if not holdout_records:
        raise ValueError("holdout records must not be empty")
    total_log_score = 0.0
    squared_errors = 0.0
    for record in holdout_records:
        _validate_record(record, model.survey_times)
        probability = model.probability(record.time)
        total_log_score += log(probability if record.detected else 1.0 - probability)
        squared_errors += (record.detected - probability) ** 2
    return BaselineScore(
        total_log_score=total_log_score,
        mean_brier_score=squared_errors / len(holdout_records),
        record_count=len(holdout_records),
    )


def _validate_record(record: TimeRecordLike, survey_times: tuple[int, ...]) -> None:
    if record.time not in survey_times:
        raise ValueError(f"unknown survey time: {record.time}")
    if record.detected not in (0, 1):
        raise ValueError("detected outcome must be binary")


def _validate_calendar(survey_times: tuple[int, ...]) -> None:
    if not survey_times or any(left >= right for left, right in pairwise(survey_times)):
        raise ValueError("survey times must be nonempty and strictly increasing")
