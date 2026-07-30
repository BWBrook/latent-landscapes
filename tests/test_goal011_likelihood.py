from __future__ import annotations

from dataclasses import dataclass
from math import log

import numpy as np
import pytest

from latent_landscapes.goal004.likelihood import site_history_probabilities
from latent_landscapes.goal011 import likelihood


@dataclass(frozen=True)
class Record:
    site_id: str
    time: int
    replicate: int
    detected: int


def _history(
    site_id: str,
    outcomes: dict[tuple[int, int], int] | None = None,
) -> tuple[Record, ...]:
    observed = outcomes or {}
    return tuple(
        Record(site_id, time, replicate, observed.get((time, replicate), 0))
        for time in (10, 20, 30, 40, 50, 60)
        for replicate in (1, 2)
    )


def test_joint_history_marginalization_matches_hand_calculation_and_preserves_ties() -> None:
    rhos = np.asarray([0.5, 1.0])
    etas = np.asarray([0.0, 1.0])
    histories = np.asarray([[0.5, 0.25, 0.125, 0.0625, 0.03, 0.02, 0.01]])
    weights = np.asarray(
        [
            [
                [[0.40, 0.20, 0.10, 0.10, 0.10, 0.05, 0.05]],
                [[0.10, 0.10, 0.10, 0.10, 0.20, 0.20, 0.20]],
            ],
            [
                [[0.10, 0.10, 0.10, 0.10, 0.20, 0.20, 0.20]],
                [[0.40, 0.20, 0.10, 0.10, 0.10, 0.05, 0.05]],
            ],
        ]
    )

    profile = likelihood.joint_profile_from_history_probabilities(
        weights=weights,
        rhos=rhos,
        etas=etas,
        bank_site_ids=("site_a",),
        history_site_ids=("site_a",),
        history_probabilities=histories,
        scope="all",
    )

    expected = np.log(np.einsum("ersc,sc->ers", weights, histories).sum(axis=2))
    assert np.array_equal(profile.log_likelihoods, expected)
    assert profile.maximum_log_likelihood == pytest.approx(
        log(float(np.dot(weights[0, 0, 0], histories[0])))
    )
    assert profile.mle_indices == ((0, 0), (1, 1))
    assert profile.mle_cells == ((0.5, 0.0), (1.0, 1.0))


def test_complete_disagreeing_visits_are_retained_in_joint_profile() -> None:
    records = _history(
        "site_a",
        {
            (10, 1): 1,
            (10, 2): 0,
            (20, 1): 0,
            (20, 2): 1,
        },
    )
    weights = np.full((2, 3, 1, 7), 1.0 / 7.0)

    profile = likelihood.joint_history_profile(
        weights=weights,
        rhos=np.asarray([0.5, 1.0, 2.0]),
        etas=np.asarray([0.0, 1.0]),
        site_ids=("site_a",),
        records=records,
        detection_probability=0.65,
        scope="all",
    )

    selected, histories = site_history_probabilities(
        site_ids=("site_a",),
        records=records,
        detection_probability=0.65,
    )
    assert selected == ("site_a",)
    assert histories.shape == (1, 7)
    assert profile.log_likelihoods.shape == (2, 3)
    assert profile.mle_indices == tuple(
        (eta_index, rho_index) for eta_index in range(2) for rho_index in range(3)
    )
    with pytest.raises(ValueError, match="complete 12-record"):
        likelihood.joint_history_profile(
            weights=weights,
            rhos=np.asarray([0.5, 1.0, 2.0]),
            etas=np.asarray([0.0, 1.0]),
            site_ids=("site_a",),
            records=records[:-1],
            scope="all",
        )


def test_primary_eta_grid_and_old_domain_projection_are_exact() -> None:
    etas = likelihood.eta_grid()
    rhos = likelihood.rho_grid()
    weights = np.full((len(etas), len(rhos), 1, 7), 1.0 / 7.0)

    profile = likelihood.joint_profile_from_history_probabilities(
        weights=weights,
        rhos=rhos,
        etas=etas,
        bank_site_ids=("site_a",),
        history_site_ids=("site_a",),
        history_probabilities=np.ones((1, 7)),
        scope="all",
    )
    projected = likelihood.project_eta_domain(profile, maximum_eta=2.0)

    assert etas.tolist() == [index / 4 for index in range(11)]
    assert rhos.shape == (601,)
    assert profile.log_likelihoods.shape == (11, 601)
    assert projected.etas.tolist() == [index / 4 for index in range(9)]
    assert projected.log_likelihoods.shape == (9, 601)
    assert projected.mle_indices == tuple(
        (eta_index, rho_index) for eta_index in range(9) for rho_index in range(601)
    )


def test_visit_predictions_are_p_times_marginal_occupancy() -> None:
    weights = np.full((1, 7), 1.0 / 7.0)
    records = _history("site_a")

    predictions = likelihood.record_detection_probabilities(
        weights=weights,
        site_ids=("site_a",),
        records=records,
        detection_probability=0.65,
    )

    expected_by_time = tuple(0.65 * (index + 1) / 7.0 for index in range(6))
    assert predictions == pytest.approx(
        tuple(value for value in expected_by_time for _ in range(2))
    )
    assert predictions[0] == predictions[1]
