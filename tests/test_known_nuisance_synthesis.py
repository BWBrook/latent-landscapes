from __future__ import annotations

import numpy as np
from scipy.stats import binom

from latent_landscapes.known_nuisance_synthesis import (
    VARIANTS,
    evaluate_sets,
    paired_bootstrap,
    quantile_bands,
)


def test_disconnected_membership_and_oracle_identity() -> None:
    effects = np.array([1.0, 2.0, 3.0])
    drops = np.array([[[[0.0, 4.0, 1.0], [3.0, 0.0, 1.0]], [[4.0, 0.0, 2.0], [0.0, 4.0, 2.0]]]])
    cutoff = np.array([[1.0, 2.0, 3.0]])
    result = evaluate_sets(drops, cutoff, effects, np.array([1.0, 3.0]))
    np.testing.assert_array_equal(result[:, 0, ..., 0], result[:, 1, ..., 0])
    # First candidate set {1,3}; hull and cardinality must not fill its hole.
    assert result[0, 0, 0, 0, 2] == np.log(3.0)
    assert result[0, 0, 0, 0, 3] == 2
    assert result[0, 0, 0, 0, 4] == 2
    assert result[0, 0, 0, 0, 6] == 1
    # At true h=3, candidate and oracle null tests can differ.
    assert result[0, 0, 1, 0, 1] == result[0, 1, 1, 0, 1] == 1
    np.testing.assert_array_equal(result[:, 0, ..., -1], result[:, 3, ..., -1])


def test_identical_variants_have_exactly_zero_paired_bootstrap_difference() -> None:
    rng = np.random.default_rng(91)
    calibration = np.repeat(rng.exponential(size=(1, 3, 19)), 2, axis=0)
    drops = rng.exponential(size=(1, 2, 7, 3))
    drops -= drops.min(axis=-1, keepdims=True)
    evaluation = np.repeat(drops, 2, axis=0)
    first, _ = paired_bootstrap(
        calibration,
        evaluation,
        np.array([1.0, 2.0, 3.0]),
        np.array([1.0, 3.0]),
        18,
        draws=8,
        seed=42,
    )
    second, _ = paired_bootstrap(
        calibration,
        evaluation,
        np.array([1.0, 2.0, 3.0]),
        np.array([1.0, 3.0]),
        18,
        draws=8,
        seed=42,
    )
    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(first[:, 0], first[:, 1])
    np.testing.assert_array_equal(first[:, :, 0, :, 0], first[:, :, 1, :, 0])


def test_quantile_band_rank_coverage_and_lr_units() -> None:
    n = 999
    samples = np.arange(1, n + 1, dtype=float)[None, :] * 10
    band = quantile_bands(samples)[0]
    lower = int(band[0] / 10)
    upper = int(band[1] / 10)
    assert binom.cdf(upper - 1, n, 0.95) - binom.cdf(lower - 1, n, 0.95) >= 0.95
    assert lower < 950 < upper
    assert band[0] > 9000  # LR units, not Beta probability content.


def test_review_bundle_reports_zero_bank_sensitivity(tmp_path) -> None:
    from latent_landscapes.known_nuisance_synthesis import write_synthesis

    rng = np.random.default_rng(78)
    calibration = np.repeat(rng.exponential(size=(1, 3, 99)), 4, axis=0)
    evaluation = rng.exponential(size=(1, 2, 8, 3))
    evaluation -= evaluation.min(axis=-1, keepdims=True)
    evaluation = np.repeat(evaluation, 4, axis=0)
    summary = write_synthesis(
        tmp_path / "review",
        calibration,
        evaluation,
        np.array([1.0, 2.0, 3.0]),
        np.array([1.0, 3.0]),
        list(VARIANTS),
        95,
        holdout=-evaluation,
        paired_across_truths=True,
        draws=8,
    )
    assert summary["primary_tolerance_failures"] == []
    assert (tmp_path / "review" / "candidate_membership.csv").is_file()
    assert (tmp_path / "review" / "calibration_resolution.png").is_file()
