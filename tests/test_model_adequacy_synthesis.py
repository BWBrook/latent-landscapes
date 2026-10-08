from __future__ import annotations

import numpy as np

from latent_landscapes.model_adequacy_synthesis import (
    EFFECT_RANK,
    _bootstrap_fields,
    _weighted_cutoff,
    _weighted_score_pvalues,
    berger_boos_pvalues,
    calibration_aware_bootstrap,
    conservative_lower_tail_pvalues,
    detector_endpoints,
    standardized_change,
)


def test_lower_tail_rank_includes_ties() -> None:
    reference = np.array([[0.0, 1.0, 1.0, 3.0], [2.0, 2.0, 4.0, 5.0]])
    observed = np.array([[1.0, 4.0]])
    result = conservative_lower_tail_pvalues(reference, observed)
    np.testing.assert_array_equal(result, np.array([[[4 / 5, 1 / 5], [1.0, 4 / 5]]]))


def test_weighted_rank_and_pvalues_match_explicit_resampling() -> None:
    scores = np.array([[0.0, 1.0, 1.0, 5.0], [9.0, 4.0, 4.0, 2.0]])
    lr = np.array([[4.0, 1.0, 2.0, 3.0], [0.0, 8.0, 6.0, 7.0]])
    weights = np.array([2, 0, 1, 1])
    score_order = np.argsort(scores, axis=1, kind="stable")
    lr_order = np.argsort(lr, axis=1, kind="stable")
    observed = np.array([[1.0, 4.0]])
    sorted_scores = np.take_along_axis(scores, score_order, axis=1)
    ranks = np.empty((1, 2, 2), dtype=np.int64)
    for node in range(2):
        ranks[..., node] = np.searchsorted(sorted_scores[node], observed, side="right")
    optimized = _weighted_score_pvalues(score_order, weights, ranks)
    explicit = conservative_lower_tail_pvalues(np.repeat(scores, weights, axis=1), observed)
    np.testing.assert_array_equal(optimized, explicit)
    indices = _weighted_cutoff(lr_order, weights, rank=3)
    expanded = np.stack(
        [np.repeat(lr[node], weights) for node in range(2)]
    )
    expected = np.partition(expanded, 2, axis=1)[:, 2]
    np.testing.assert_array_equal(lr[np.arange(2), indices], expected)


def test_c99_uses_rank_990_not_goal049_rank_950() -> None:
    calibration_profiles = np.zeros((1, 999, 1))
    calibration_profiles[0, :, 0] = np.arange(999.0)
    reference_scores = np.arange(999.0)[None, :]
    evaluation_profiles = np.array([[[970.0]]])
    p, p_bb, c99, outcomes = detector_endpoints(
        reference_scores,
        calibration_profiles,
        np.array([[0.0]]),
        evaluation_profiles,
        np.array([0]),
    )
    assert c99[0, 0, 0]  # 970 <= X_(990)=989
    assert evaluation_profiles[0, 0, 0] > 949  # excluded by rank-950 effect set
    assert outcomes[0, 0, 1]
    assert outcomes[0, 0, 2]
    assert p[0, 0, 0] == 2 / 1000
    assert p_bb[0, 0] == 0.012


def test_berger_boos_full_grid_maximum_and_cap_match_brute_force() -> None:
    candidate_p = np.array([[[0.1, 0.995, 0.4], [0.2, 0.3, 1.0]]])
    profiles = np.array([[[0.0, 2.0, 1.0], [3.0, 0.0, 0.0]]])
    cutoffs = np.array([1.0, 1.0, 1.0])
    result, membership = berger_boos_pvalues(candidate_p, profiles, cutoffs)
    brute = np.array(
        [
            min(1.0, max(candidate_p[0, row, membership[0, row]]) + 0.01)
            for row in range(2)
        ]
    )[None, :]
    np.testing.assert_array_equal(result, brute)
    assert np.all(result <= 1.0)
    assert result[0, 1] == 1.0


def test_bootstrap_preserves_paired_truth_and_shared_calibration_weights() -> None:
    rng = np.random.default_rng(114)
    nodes = 3
    ncal = 999
    neval = 17
    reference = rng.normal(size=(nodes, ncal))
    calibration_lr = rng.exponential(size=(nodes, ncal))
    one_score = rng.normal(size=(1, neval))
    old_scores = np.repeat(one_score, 2, axis=0)
    one_profile = rng.exponential(size=(1, neval, nodes))
    one_profile -= one_profile.min(axis=-1, keepdims=True)
    old_profiles = np.repeat(one_profile, 2, axis=0)
    fresh_cal = rng.exponential(size=ncal)
    fresh_scores = rng.normal(size=(1, neval))
    fresh_profiles = rng.exponential(size=(1, neval, nodes))
    fresh_profiles -= fresh_profiles.min(axis=-1, keepdims=True)
    result = calibration_aware_bootstrap(
        reference,
        calibration_lr,
        old_scores,
        old_profiles,
        np.array([0, 0]),
        fresh_cal,
        fresh_scores,
        fresh_profiles,
        draws=5,
        seed=123,
    )
    np.testing.assert_array_equal(result.retrospective[:, 0], result.retrospective[:, 1])
    assert result.null_cells.shape == (5, 2, 2)
    assert result.null_contrasts.shape == (5, 5)


def test_constant_bootstrap_has_zero_se_and_undefined_standardization() -> None:
    fields = _bootstrap_fields(np.repeat(0.25, 1000))
    assert fields["bootstrap_se"] == 0.0
    assert fields["bootstrap_low"] == fields["bootstrap_high"] == 0.25
    assert standardized_change(0.0, 0.0) is None
    assert standardized_change(0.1, 0.0) is None
    assert EFFECT_RANK == 950
