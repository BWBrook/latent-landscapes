from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from latent_landscapes.goal004.likelihood import category_weights
from latent_landscapes.goal007.likelihood import (
    CATEGORY_COUNT,
    JointGridProfile,
    eta_grid,
    joint_category_weights,
    joint_profile,
    record_occupancy_probabilities,
    rho_grid,
    summarize_joint_profile,
)
from latent_landscapes.goal007.observations import CollapsedObservation


def _record(site_id: str, time: int, detected: int) -> CollapsedObservation:
    return CollapsedObservation(
        cluster_id=f"cluster_{site_id}",
        split="holdout",
        stratum_index=0,
        site_id=site_id,
        site_offset_index=0,
        row=0,
        col=0,
        time=time,
        detected=detected,
    )


def test_frozen_joint_grid_contains_truth_at_exact_indices() -> None:
    rhos = rho_grid()
    etas = eta_grid()

    assert rhos.shape == (601,)
    assert etas.tolist() == [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
    assert rhos[0] == 0.25
    assert rhos[300] == 1.0
    assert rhos[-1] == 4.0
    assert etas[4] == 1.0


def test_eta_specific_weights_use_exact_rho_scaling() -> None:
    bank = np.asarray(
        [
            [[5.0], [8.0]],
            [[10.0], [12.0]],
            [[15.0], [16.0]],
            [[20.0], [24.0]],
        ]
    )
    rhos = np.asarray([0.5, 1.0, 2.0])

    weights = joint_category_weights(bank, rhos)

    assert weights.shape == (2, 3, 1, CATEGORY_COUNT)
    assert np.array_equal(weights[0], category_weights(bank[:, 0, :], rhos))
    assert np.array_equal(weights[1], category_weights(bank[:, 1, :], rhos))
    assert np.all(weights > 0.0)
    assert np.allclose(weights.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)


def test_joint_profile_preserves_all_tied_two_dimensional_mles() -> None:
    rhos = np.asarray([0.5, 1.0, 2.0])
    etas = np.asarray([0.0, 1.0])
    weights = np.full((2, 3, 2, CATEGORY_COUNT), 0.01)
    weights[..., 0] = 0.47
    weights[..., 6] = 0.47
    weights /= weights.sum(axis=-1, keepdims=True)
    weights[0, 1, 0, 0] = weights[1, 2, 0, 0] = 0.8
    weights[0, 1, 0, 1:] = weights[1, 2, 0, 1:] = 0.2 / 6
    weights[0, 1, 1, 6] = weights[1, 2, 1, 6] = 0.8
    weights[0, 1, 1, :6] = weights[1, 2, 1, :6] = 0.2 / 6

    profile = joint_profile(
        weights=weights,
        rhos=rhos,
        etas=etas,
        bank_site_ids=("a", "b"),
        history_site_ids=("a", "b"),
        onset_categories=np.asarray([0, 6], dtype=np.int64),
        scope="all",
    )

    assert profile.log_likelihoods.shape == (2, 3)
    assert profile.mle_indices == ((0, 1), (1, 2))
    assert profile.mle_cells == ((1.0, 0.0), (2.0, 1.0))


def test_rook_support_does_not_connect_diagonal_cells() -> None:
    rhos = np.asarray([0.5, 1.0, 2.0])
    etas = np.asarray([0.0, 1.0, 2.0])
    values = np.full((3, 3), -10.0)
    values[0, 0] = 0.0
    values[1, 1] = 0.0
    profile = JointGridProfile(
        scope="all",
        rhos=rhos,
        etas=etas,
        log_likelihoods=values,
        maximum_log_likelihood=0.0,
        mle_indices=((0, 0), (1, 1)),
        mle_cells=((0.5, 0.0), (1.0, 1.0)),
    )

    summary = summarize_joint_profile(profile, cutoff=0.0)

    assert summary.support_component_count == 2
    assert summary.support_boundary_contact is True
    assert summary.truth_included is True
    assert summary.support_correlation == pytest.approx(1.0)
    assert summary.support_correlation_reason is None


def test_connected_interior_support_widths_and_degenerate_correlation() -> None:
    rhos = np.asarray([0.25, 0.5, 1.0, 2.0, 4.0])
    etas = np.asarray([0.0, 0.5, 1.0, 1.5, 2.0])
    values = np.full((5, 5), -10.0)
    values[1:4, 2] = 0.0
    profile = JointGridProfile(
        scope="all",
        rhos=rhos,
        etas=etas,
        log_likelihoods=values,
        maximum_log_likelihood=0.0,
        mle_indices=((1, 2), (2, 2), (3, 2)),
        mle_cells=((1.0, 0.5), (1.0, 1.0), (1.0, 1.5)),
    )

    summary = summarize_joint_profile(profile, cutoff=0.0)

    assert summary.support_component_count == 1
    assert summary.support_boundary_contact is False
    assert summary.projected_log_rho_width == 0.0
    assert summary.projected_eta_width == 1.0
    assert summary.support_correlation is None
    assert summary.support_correlation_reason == "constant_rho"
    assert summary.minimum_absolute_log_rho_error == 0.0
    assert summary.minimum_absolute_eta_error == 0.0


def test_perfect_detection_predictions_have_full_support() -> None:
    weights = np.full((2, CATEGORY_COUNT), 1.0 / CATEGORY_COUNT)
    records = (_record("a", 10, 0), _record("b", 60, 1))

    predictions = record_occupancy_probabilities(
        weights=weights,
        site_ids=("a", "b"),
        records=records,
    )

    assert predictions == pytest.approx((1.0 / 7.0, 6.0 / 7.0))
    assert all(0.0 < value < 1.0 for value in predictions)
    with pytest.raises(ValueError, match="shape"):
        record_occupancy_probabilities(
            weights=np.ones((2, 6)),
            site_ids=("a", "b"),
            records=records,
        )
    with pytest.raises(ValueError, match="unknown"):
        record_occupancy_probabilities(
            weights=weights,
            site_ids=("a", "b"),
            records=(replace(records[0], site_id="missing"),),
        )
