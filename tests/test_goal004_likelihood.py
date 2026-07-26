from __future__ import annotations

from dataclasses import dataclass
from math import log

import numpy as np
import pytest

from latent_landscapes.goal004 import likelihood


@dataclass(frozen=True)
class Record:
    site_id: str
    time: int
    replicate: int
    detected: int


def history(
    site_id: str,
    detected: dict[tuple[int, int], int] | None = None,
) -> tuple[Record, ...]:
    outcomes = detected or {}
    return tuple(
        Record(site_id, time, replicate, outcomes.get((time, replicate), 0))
        for time in likelihood.SURVEY_TIMES
        for replicate in (1, 2)
    )


def test_rate_grid_is_exact_and_frozen() -> None:
    rates = likelihood.rate_grid()

    assert rates.shape == (601,)
    assert rates[0] == 0.25
    assert rates[300] == 1.0
    assert rates[-1] == 4.0
    assert np.array_equal(
        rates,
        np.asarray([2.0 ** (-2.0 + 4.0 * j / 600.0) for j in range(601)]),
    )


def test_category_weights_use_hand_calculated_jeffreys_smoothing() -> None:
    bank = np.asarray([[5.0], [15.0], [25.0], [70.0]])

    weights = likelihood.category_weights(bank, np.asarray([1.0]))

    assert weights.shape == (1, 1, 7)
    assert weights[0, 0] == pytest.approx(np.asarray([1.5, 1.5, 1.5, 0.5, 0.5, 0.5, 1.5]) / 7.5)
    assert weights.sum(axis=2) == pytest.approx(np.ones((1, 1)))
    assert (weights > 0.0).all()


def test_site_history_is_marginalized_before_sites_are_multiplied() -> None:
    bank = np.asarray([[5.0], [15.0], [25.0], [70.0]])
    rates = np.asarray([1.0])
    weights = likelihood.category_weights(bank, rates)
    records = history("site_a")

    profile = likelihood.composite_profile(
        weights=weights,
        rates=rates,
        site_ids=("site_a",),
        records=records,
        detection_probability=0.5,
        scope="all",
    )

    category_history = np.asarray([0.5**12, 0.5**10, 0.5**8, 0.5**6, 0.5**4, 0.5**2, 1.0])
    expected = float(np.log(weights[0, 0] @ category_history))
    marginal_detection = np.asarray(
        [
            0.5 * weights[0, 0, : survey_index + 1].sum()
            for survey_index in range(6)
            for _ in range(2)
        ]
    )
    incorrect_recordwise_product = float(np.log1p(-marginal_detection).sum())

    assert profile.log_likelihoods[0] == pytest.approx(expected)
    assert profile.log_likelihoods[0] != pytest.approx(incorrect_recordwise_product)


def test_profile_preserves_tied_mle_set_with_absolute_tolerance() -> None:
    rates = np.asarray([0.5, 1.0, 2.0])
    weights = np.full((3, 1, 7), 1.0 / 7.0)
    records = history("site_a", {(20, 1): 1})

    profile = likelihood.composite_profile(
        weights=weights,
        rates=rates,
        site_ids=("site_a",),
        records=records,
        detection_probability=0.65,
        scope="all",
    )

    assert profile.mle_indices == (0, 1, 2)
    assert profile.mle_rates == (0.5, 1.0, 2.0)


def test_calibrated_support_components_and_set_valued_errors_reconcile() -> None:
    rates = np.asarray([0.25, 0.5, 1.0, 2.0, 4.0])
    profile = likelihood.GridProfile(
        scope="all",
        rates=rates,
        log_likelihoods=np.asarray([-2.0, 0.0, -5e-13, -0.4, -2.0]),
        maximum_log_likelihood=0.0,
        mle_indices=(1, 2),
        mle_rates=(0.5, 1.0),
    )

    summary = likelihood.summarize_profile(profile, cutoff=0.8, truth_rate=1.0)

    assert summary.support_indices == (1, 2, 3)
    assert len(summary.support_components) == 1
    assert summary.support_components[0].start_index == 1
    assert summary.support_components[0].end_index == 3
    assert summary.support_components[0].lower == 0.5
    assert summary.support_components[0].upper == 2.0
    assert summary.truth_included is True
    assert summary.support_boundary_contact is False
    assert summary.support_arithmetic_width == pytest.approx(1.5)
    assert summary.support_log_rate_width == pytest.approx(log(4.0))
    assert summary.truth_to_mle_set_distance == 0.0
    assert summary.absolute_log_rate_error == 0.0


def test_category_marginal_predictions_are_coherent_and_full_support() -> None:
    bank = np.asarray([[5.0], [15.0], [25.0], [70.0]])
    weights = likelihood.category_weights(bank, np.asarray([1.0]))[0]
    records = history("site_a")

    predictions = likelihood.record_detection_probabilities(
        weights=weights,
        site_ids=("site_a",),
        records=records,
        detection_probability=0.65,
    )

    expected_by_time = tuple(
        0.65 * float(weights[0, : survey_index + 1].sum()) for survey_index in range(6)
    )
    assert predictions == pytest.approx(
        tuple(value for value in expected_by_time for _ in range(2))
    )
    assert all(0.0 < value < 1.0 for value in predictions)
    score = likelihood.score_predictions(predictions, records)
    assert np.isfinite(score.total_log_score)
    assert score.mean_brier_score == pytest.approx(np.mean(np.square(np.asarray(predictions))))


@pytest.mark.parametrize(
    ("bank", "rates", "message"),
    [
        (np.asarray([1.0, 2.0]), np.asarray([1.0]), "two-dimensional"),
        (np.asarray([[1.0], [np.inf]]), np.asarray([1.0]), "finite"),
        (np.asarray([[1.0], [-1.0]]), np.asarray([1.0]), "nonnegative"),
        (np.asarray([[1.0]]), np.asarray([1.0, 0.5]), "strictly increasing"),
        (np.asarray([[1.0]]), np.asarray([0.0]), "positive"),
    ],
)
def test_category_weights_reject_invalid_inputs(
    bank: np.ndarray,
    rates: np.ndarray,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        likelihood.category_weights(bank, rates)


def test_likelihood_rejects_invalid_calendar_probability_and_history() -> None:
    bank = np.asarray([[1.0]])

    with pytest.raises(ValueError, match="strictly increasing"):
        likelihood.category_weights(
            bank,
            np.asarray([1.0]),
            survey_times=(10, 20, 20),
        )
    with pytest.raises(ValueError, match="probability"):
        likelihood.composite_profile(
            weights=np.full((1, 1, 7), 1.0 / 7.0),
            rates=np.asarray([1.0]),
            site_ids=("site_a",),
            records=history("site_a"),
            detection_probability=1.0,
            scope="all",
        )
    with pytest.raises(ValueError, match="complete 12-record"):
        likelihood.composite_profile(
            weights=np.full((1, 1, 7), 1.0 / 7.0),
            rates=np.asarray([1.0]),
            site_ids=("site_a",),
            records=history("site_a")[:-1],
            detection_probability=0.65,
            scope="all",
        )
