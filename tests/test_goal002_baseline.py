from __future__ import annotations

import importlib
from dataclasses import dataclass
from math import isfinite, log
from typing import Any

import pytest


@dataclass(frozen=True)
class Record:
    time: int
    detected: int


def load_baseline() -> Any:
    return importlib.import_module("latent_landscapes.goal002.baseline")


def frozen_training_records() -> tuple[Record, ...]:
    return (
        Record(10, 0),
        Record(10, 0),
        Record(30, 1),
        Record(30, 1),
        Record(50, 0),
        Record(50, 1),
        Record(70, 0),
        Record(70, 1),
        Record(90, 0),
        Record(90, 1),
        Record(110, 0),
        Record(110, 1),
    )


def test_jeffreys_smoothed_probabilities_are_hand_calculated_and_full_support() -> None:
    baseline = load_baseline()

    model = baseline.fit_time_stratified_baseline(frozen_training_records())

    assert model.probabilities == (
        (10, 1.0 / 6.0),
        (30, 5.0 / 6.0),
        (50, 0.5),
        (70, 0.5),
        (90, 0.5),
        (110, 0.5),
    )
    assert all(0.0 < probability < 1.0 for _, probability in model.probabilities)


def test_baseline_score_is_finite_and_hand_calculated() -> None:
    baseline = load_baseline()
    model = baseline.fit_time_stratified_baseline(frozen_training_records())
    holdout = (
        Record(10, 1),
        Record(30, 0),
        Record(50, 1),
        Record(70, 0),
        Record(90, 1),
        Record(110, 0),
    )

    score = baseline.score_time_stratified_baseline(model, holdout)

    expected_log_score = 2.0 * log(1.0 / 6.0) + 4.0 * log(0.5)
    expected_brier = (2.0 * (5.0 / 6.0) ** 2 + 4.0 * 0.5**2) / 6.0
    assert score.total_log_score == pytest.approx(expected_log_score)
    assert score.mean_brier_score == pytest.approx(expected_brier)
    assert score.record_count == 6
    assert isfinite(score.total_log_score)


def test_holdout_outcomes_cannot_change_fitted_probabilities() -> None:
    baseline = load_baseline()
    training = frozen_training_records()
    model_before = baseline.fit_time_stratified_baseline(training)
    baseline.score_time_stratified_baseline(
        model_before,
        tuple(Record(time, 0) for time in (10, 30, 50, 70, 90, 110)),
    )
    baseline.score_time_stratified_baseline(
        model_before,
        tuple(Record(time, 1) for time in (10, 30, 50, 70, 90, 110)),
    )

    assert baseline.fit_time_stratified_baseline(training) == model_before


def test_baseline_rejects_unknown_or_missing_training_times() -> None:
    baseline = load_baseline()

    with pytest.raises(ValueError, match="unknown survey time"):
        baseline.fit_time_stratified_baseline((*frozen_training_records(), Record(20, 1)))
    with pytest.raises(ValueError, match="missing survey time"):
        baseline.fit_time_stratified_baseline(
            tuple(record for record in frozen_training_records() if record.time != 110)
        )


def test_baseline_rejects_unknown_holdout_times_and_empty_holdout() -> None:
    baseline = load_baseline()
    model = baseline.fit_time_stratified_baseline(frozen_training_records())

    with pytest.raises(ValueError, match="unknown survey time"):
        baseline.score_time_stratified_baseline(model, (Record(20, 1),))
    with pytest.raises(ValueError, match="empty"):
        baseline.score_time_stratified_baseline(model, ())
