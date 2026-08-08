from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from latent_landscapes.goal016.discrimination import (
    centered_log_features,
    conservative_null_threshold,
    fit_ridge_discriminator,
    history_probabilities_from_detection_counts,
    profiled_composite_score,
    rank_features,
)


def test_centered_log_features_remove_exact_global_rate_scaling() -> None:
    arrivals = np.asarray(
        [[2.0, 4.0, 8.0, 16.0], [3.0, 6.0, 12.0, 24.0]],
        dtype=np.float64,
    )

    baseline = centered_log_features(arrivals)
    faster = centered_log_features(arrivals / 2.0)
    slower = centered_log_features(arrivals / 0.5)

    assert np.allclose(baseline, faster, rtol=0.0, atol=1e-12)
    assert np.allclose(baseline, slower, rtol=0.0, atol=1e-12)
    assert np.allclose(np.median(baseline, axis=1), 0.0, rtol=0.0, atol=1e-12)


def test_rank_features_are_scale_invariant_and_tie_stable() -> None:
    arrivals = np.asarray(
        [[4.0, 1.0, 2.0, 2.0], [40.0, 10.0, 20.0, 20.0]],
        dtype=np.float64,
    )

    features = rank_features(arrivals)

    assert np.array_equal(features[0], features[1])
    assert features[0].tolist() == pytest.approx([1.0, 0.0, 0.5, 0.5])


def test_history_probabilities_from_counts_match_complete_two_visit_histories() -> None:
    counts = np.zeros((1, 6), dtype=np.int8)

    probabilities = history_probabilities_from_detection_counts(counts, 0.65)

    assert probabilities.shape == (1, 7)
    assert probabilities[0].tolist() == pytest.approx(
        [0.35**12, 0.35**10, 0.35**8, 0.35**6, 0.35**4, 0.35**2, 1.0]
    )

    detected_early = counts.copy()
    detected_early[0, 0] = 1
    early_probabilities = history_probabilities_from_detection_counts(detected_early, 0.65)
    assert early_probabilities[0, 0] == pytest.approx(0.65 * 0.35**11)
    assert np.array_equal(early_probabilities[0, 1:], np.zeros(6))


def test_conservative_null_threshold_controls_every_rho_slice() -> None:
    scores = {
        0.5: np.arange(100, dtype=np.float64),
        1.0: np.arange(100, dtype=np.float64) + 10.0,
        2.0: np.arange(100, dtype=np.float64) - 5.0,
    }

    threshold = conservative_null_threshold(scores, quantile=0.95)

    assert threshold == 105.0
    assert all(float(np.mean(values > threshold)) <= 0.05 for values in scores.values())


def test_profiled_composite_score_compares_eta_slices_after_rho_profiling() -> None:
    weights = np.asarray(
        [
            [
                [[[0.8, 0.2]], [[0.6, 0.4]]],
                [[[0.4, 0.6]], [[0.3, 0.7]]],
            ],
            [
                [[[0.5, 0.5]], [[0.2, 0.8]]],
                [[[0.9, 0.1]], [[0.7, 0.3]]],
            ],
        ],
        dtype=np.float64,
    ).reshape(2, 2, 2, 2)
    histories = np.asarray([[1.0, 0.0], [0.25, 0.75]], dtype=np.float64)

    score = profiled_composite_score(weights, histories)

    eta_zero = np.log(np.einsum("rsc,sc->rs", weights[0], histories)).sum(axis=1)
    eta_half = np.log(np.einsum("rsc,sc->rs", weights[1], histories)).sum(axis=1)
    assert score == pytest.approx(float(eta_half.max() - eta_zero.max()))


def test_ridge_discriminator_selects_on_validation_and_scores_unseen_waves() -> None:
    rng = np.random.default_rng(20260807)
    train_zero = rng.normal(-1.0, 0.25, size=(30, 4))
    train_one = rng.normal(1.0, 0.25, size=(30, 4))
    validation_zero = rng.normal(-1.0, 0.25, size=(15, 4))
    validation_one = rng.normal(1.0, 0.25, size=(15, 4))
    train_x = np.vstack((train_zero, train_one))
    train_y: NDArray[np.int8] = np.concatenate(
        (np.zeros(30, dtype=np.int8), np.ones(30, dtype=np.int8))
    )
    validation_x = np.vstack((validation_zero, validation_one))
    validation_y: NDArray[np.int8] = np.concatenate(
        (np.zeros(15, dtype=np.int8), np.ones(15, dtype=np.int8))
    )

    fitted = fit_ridge_discriminator(
        train_x,
        train_y,
        validation_x,
        validation_y,
        alphas=(0.1, 1.0, 10.0),
    )
    scores = fitted.decision_function(validation_x)

    assert fitted.alpha in (0.1, 1.0, 10.0)
    assert fitted.validation_auc == pytest.approx(1.0)
    assert np.all(scores[:15] < 0.0)
    assert np.all(scores[15:] > 0.0)
