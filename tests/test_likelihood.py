from __future__ import annotations

import importlib
from dataclasses import dataclass
from math import inf, log
from typing import Any

import pytest


@dataclass(frozen=True)
class Record:
    site_id: str
    time: float
    detected: int


def load_likelihood() -> Any:
    return importlib.import_module("latent_landscapes.goal001.likelihood")


def hand_records() -> tuple[Record, ...]:
    return (
        Record("A", 0.5, 0),
        Record("A", 1.0, 1),
        Record("B", 1.0, 0),
        Record("B", 2.0, 1),
    )


def test_hand_likelihood_fixture_and_arrival_equality() -> None:
    likelihood = load_likelihood()
    distances = {"A": 1.0, "B": 2.0}
    records = hand_records()

    assert likelihood.log_likelihood(0.5, distances, records, 0.5) == -inf
    assert likelihood.log_likelihood(1.0, distances, records, 0.5) == pytest.approx(-2.0 * log(2.0))
    assert likelihood.log_likelihood(2.0, distances, records, 0.5) == pytest.approx(-4.0 * log(2.0))


def test_exact_profile_reports_every_class_mle_and_nominal_support() -> None:
    likelihood = load_likelihood()

    profile = likelihood.profile_likelihood(
        model="habitat",
        scope="training",
        distances={"A": 1.0, "B": 2.0},
        records=hand_records(),
        detection_probability=0.5,
    )

    assert [(value.lower, value.upper) for value in profile.classes] == [
        (0.25, 1.0),
        (1.0, 2.0),
        (2.0, 4.0),
    ]
    assert [(value.lower_closed, value.upper_closed) for value in profile.classes] == [
        (True, False),
        (True, False),
        (True, True),
    ]
    assert profile.classes[0].log_likelihood == -inf
    assert profile.classes[1].log_likelihood == pytest.approx(-2.0 * log(2.0))
    assert profile.classes[2].log_likelihood == pytest.approx(-4.0 * log(2.0))
    assert profile.mle_classes == (profile.classes[1],)
    assert profile.mle_classes[0].width == 1.0
    assert profile.support_classes == (profile.classes[1], profile.classes[2])
    assert len(profile.support_components) == 1
    assert profile.support_components[0].lower == 1.0
    assert profile.support_components[0].upper == 4.0
    assert profile.support_components[0].width == 3.0
    assert profile.support_components[0].upper_closed is True


def test_explicit_lr_threshold_changes_only_support_membership() -> None:
    likelihood = load_likelihood()
    arguments = {
        "model": "habitat",
        "scope": "training",
        "distances": {"A": 1.0, "B": 2.0},
        "records": hand_records(),
        "detection_probability": 0.5,
    }

    default_profile = likelihood.profile_likelihood(**arguments)
    nominal_profile = likelihood.profile_likelihood(
        **arguments, lr_threshold=likelihood.LR_THRESHOLD
    )
    strict_profile = likelihood.profile_likelihood(**arguments, lr_threshold=0.0)

    assert nominal_profile == default_profile
    assert strict_profile.classes == default_profile.classes
    assert strict_profile.mle_classes == default_profile.mle_classes
    assert strict_profile.maximum_log_likelihood == default_profile.maximum_log_likelihood
    assert strict_profile.raw_breakpoint_count == default_profile.raw_breakpoint_count
    assert strict_profile.clipped_unique_breakpoints == default_profile.clipped_unique_breakpoints
    assert strict_profile.support_classes == strict_profile.mle_classes
    assert strict_profile.support_components == (strict_profile.mle_classes[0].as_interval(),)


@pytest.mark.parametrize("threshold", [-1.0, inf])
def test_explicit_lr_threshold_must_be_finite_and_nonnegative(threshold: float) -> None:
    likelihood = load_likelihood()

    with pytest.raises(ValueError, match="LR threshold"):
        likelihood.profile_likelihood(
            model="habitat",
            scope="training",
            distances={"A": 1.0, "B": 2.0},
            records=hand_records(),
            detection_probability=0.5,
            lr_threshold=threshold,
        )


def test_breakpoint_at_upper_domain_bound_is_a_nonempty_singleton_class() -> None:
    likelihood = load_likelihood()
    records = (Record("A", 1.0, 1),)

    profile = likelihood.profile_likelihood(
        model="habitat",
        scope="all",
        distances={"A": 4.0},
        records=records,
        detection_probability=0.5,
    )

    assert [(value.lower, value.upper) for value in profile.classes] == [
        (0.25, 4.0),
        (4.0, 4.0),
    ]
    assert profile.classes[0].upper_closed is False
    assert profile.classes[1].lower_closed is True
    assert profile.classes[1].upper_closed is True
    assert profile.classes[1].representative_rate == 4.0
    assert profile.mle_classes == (profile.classes[1],)


def test_holdout_scores_partition_training_mle_at_holdout_breakpoints() -> None:
    likelihood = load_likelihood()
    training_profile = likelihood.profile_likelihood(
        model="habitat",
        scope="training",
        distances={"A": 1.0, "B": 2.0},
        records=hand_records(),
        detection_probability=0.5,
    )
    holdout_records = (Record("H", 1.0, 0),)

    evaluation = likelihood.evaluate_holdout_mle(
        model="habitat",
        training_profile=training_profile,
        distances={"H": 1.5},
        records=holdout_records,
        detection_probability=0.5,
    )

    assert [(value.lower, value.upper) for value in evaluation.partitions] == [
        (1.0, 1.5),
        (1.5, 2.0),
    ]
    assert [(value.lower_closed, value.upper_closed) for value in evaluation.partitions] == [
        (True, False),
        (True, False),
    ]
    training_mle = training_profile.mle_classes[0]
    assert evaluation.partitions[0].lower == training_mle.lower
    assert evaluation.partitions[0].lower_closed is training_mle.lower_closed
    assert evaluation.partitions[-1].upper == training_mle.upper
    assert evaluation.partitions[-1].upper_closed is training_mle.upper_closed
    assert sum(value.width for value in evaluation.partitions) == pytest.approx(training_mle.width)
    for index in range(len(evaluation.partitions) - 1):
        left = evaluation.partitions[index]
        right = evaluation.partitions[index + 1]
        assert left.upper == right.lower
        assert left.upper_closed is not right.lower_closed
    assert evaluation.partitions[0].log_score == 0.0
    assert evaluation.partitions[0].brier_score == 0.0
    assert evaluation.partitions[1].log_score == pytest.approx(log(0.5))
    assert evaluation.partitions[1].brier_score == 0.25
    assert evaluation.log_score_range.minimum == pytest.approx(log(0.5))
    assert evaluation.log_score_range.maximum == 0.0
    assert evaluation.brier_score_range.minimum == 0.0
    assert evaluation.brier_score_range.maximum == 0.25
    assert evaluation.impossible_positive_range.minimum == 0
    assert evaluation.impossible_positive_range.maximum == 0


def test_neutral_comparison_uses_strict_worst_versus_best_rule() -> None:
    likelihood = load_likelihood()
    score_range = likelihood.ScoreRange

    assert (
        likelihood.compare_holdout_log_scores(score_range(-10.0, -8.0), score_range(-12.0, -11.0))
        == "habitat_robustly_better"
    )
    assert (
        likelihood.compare_holdout_log_scores(score_range(-13.0, -12.0), score_range(-11.0, -10.0))
        == "neutral_robustly_better"
    )
    assert (
        likelihood.compare_holdout_log_scores(score_range(-12.0, -9.0), score_range(-11.0, -8.0))
        == "inconclusive"
    )
