from __future__ import annotations

import hashlib
import math
from dataclasses import replace

import numpy as np
import pytest
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes.arc2c_design import BACKGROUND_HAZARD, TRUTHS
from latent_landscapes.arc2c_likelihood import (
    BridgeIntegration,
    build_joint_integration,
    evaluate_dataset,
    joint_log_likelihood,
    paired_histories,
)
from latent_landscapes.goal004.observations import SURVEY_TIMES
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal011 import benchmark as goal011


@pytest.fixture(scope="module")
def fixed() -> goal007.FixedInputs:
    return goal011.build_fixed_inputs()


@pytest.fixture(scope="module")
def paired(fixed: goal007.FixedInputs) -> tuple[tuple[arc2b.CrossLayerHistory, ...], ...]:
    return paired_histories(fixed, arc2b.DatasetSeed("test", 0, 250, 251, 252, 253))


@pytest.fixture(scope="module")
def bank(fixed: goal007.FixedInputs) -> NDArray[np.float64]:
    return arc2b._generate_bank(fixed, (100, 101, 102, 103))


@pytest.fixture(scope="module")
def integration(
    paired: tuple[tuple[arc2b.CrossLayerHistory, ...], ...], bank: NDArray[np.float64]
) -> BridgeIntegration:
    return build_joint_integration(
        bank, tuple(row.site_id for row in paired[0]), (0.5, 1.0, 2.0), (1.0, 3.0, 5.0)
    )


def test_restricted_rho_is_the_accepted_arc2b_training_likelihood(
    paired: tuple[tuple[arc2b.CrossLayerHistory, ...], ...],
    bank: NDArray[np.float64],
    integration: BridgeIntegration,
) -> None:
    histories = paired[1]
    training = tuple(row for row in histories if row.split == "training")
    joint, _, _ = evaluate_dataset(histories, integration)
    restricted = joint_log_likelihood(training, integration)
    assert integration.bank_checksum == hashlib.sha256(bank.tobytes(order="C")).hexdigest()
    for index, rho in enumerate(integration.rhos):
        accepted = arc2b.build_arrival_integration(
            bank / rho, integration.site_ids, integration.effects, BACKGROUND_HAZARD
        )
        np.testing.assert_array_equal(
            integration.survival_moments[index], accepted.survival_moments
        )
        np.testing.assert_array_equal(integration.category_mass[index], accepted.category_mass)
        expected = arc2b.latent_arrival_profile(training, accepted, arc2b.DEFAULT_CONFIG)
        np.testing.assert_array_equal(restricted[index], expected.log_likelihoods)
        np.testing.assert_allclose(joint[index], expected.log_likelihoods, rtol=0, atol=2e-12)


def test_each_rho_shares_arrival_before_marginalising_species() -> None:
    history = arc2b.CrossLayerHistory(
        "test",
        0,
        0,
        "site",
        "cluster",
        "training",
        0,
        0,
        25.0,
        45.0,
        (0, 0, 0, 0, 0, 0),
        (2, 1, 1, 0, 0, 0),
        (False, False, True, True, True, True),
        (True, True, True, True, False, False),
    )
    arrivals = np.asarray([[5.0], [25.0], [45.0], [65.0]])
    integrated = build_joint_integration(arrivals, ("site",), (0.5, 1.0), (1.0, 5.0))
    observed = joint_log_likelihood((history,), integrated)
    for rho_index, rho in enumerate(integrated.rhos):
        predator: list[float] = []
        prey: list[float] = []
        augmented = (*map(float, arrivals[:, 0] / rho), *arc2b.PSEUDO_ARRIVALS)
        weights = (1.0,) * 4 + (0.5,) * arc2b.CATEGORY_COUNT
        for arrival in augmented:
            category = int(np.searchsorted(np.asarray(SURVEY_TIMES), arrival, side="left"))
            predator.append(0.35 ** (2 * (len(SURVEY_TIMES) - category)))
            survival = [
                math.exp(-BACKGROUND_HAZARD * (time + 4.0 * max(time - arrival, 0)))
                for time in (0, *SURVEY_TIMES)
            ]
            alive = [
                math.comb(2, count) * 0.65**count * 0.35 ** (2 - count)
                for count in history.prey_detection_counts
            ]
            prey.append(
                sum(
                    (survival[index] - survival[index + 1])
                    * math.prod(alive[:index])
                    * math.prod(count == 0 for count in history.prey_detection_counts[index:])
                    for index in range(len(SURVEY_TIMES))
                )
                + survival[-1] * math.prod(alive)
            )
        denominator = sum(weights)
        shared = (
            sum(
                weight * pred * pre
                for weight, pred, pre in zip(weights, predator, prey, strict=True)
            )
            / denominator
        )
        independent = (
            sum(weight * pred for weight, pred in zip(weights, predator, strict=True))
            * sum(weight * pre for weight, pre in zip(weights, prey, strict=True))
            / denominator**2
        )
        assert math.exp(float(observed[rho_index, 1])) == pytest.approx(shared, rel=1e-12)
        assert not math.isclose(shared, independent, rel_tol=1e-4)


def test_no_effect_conditional_prey_score_is_independent_of_rho(
    paired: tuple[tuple[arc2b.CrossLayerHistory, ...], ...], integration: BridgeIntegration
) -> None:
    _, joint, predator = evaluate_dataset(paired[1], integration)
    holdout = tuple(row for row in paired[1] if row.split == "holdout")
    events, alive = arc2b._prey_emission_coefficients(holdout)
    survival = np.exp(-BACKGROUND_HAZARD * np.asarray((0.0, *SURVEY_TIMES)))
    prey = events @ (survival[:-1] - survival[1:]) + alive * survival[-1]
    expected = float(np.log(prey).sum())
    np.testing.assert_allclose(joint[:, 0] - predator, expected, rtol=0, atol=1e-12)
    assert np.ptp(joint[:, 1] - predator) > 1e-3


def test_truth_only_fields_never_enter_the_likelihood(
    paired: tuple[tuple[arc2b.CrossLayerHistory, ...], ...], integration: BridgeIntegration
) -> None:
    original = paired[1]
    altered = tuple(
        replace(
            row,
            true_predator_arrival=99999.0,
            true_prey_extirpation=math.nan,
            true_predator_present=tuple(not value for value in row.true_predator_present),
            true_prey_alive=tuple(not value for value in row.true_prey_alive),
        )
        for row in reversed(original)
    )
    for before, after in zip(
        evaluate_dataset(original, integration), evaluate_dataset(altered, integration), strict=True
    ):
        np.testing.assert_array_equal(before, after)


def test_six_case_generation_preserves_rate_scaling_and_common_random_numbers(
    paired: tuple[tuple[arc2b.CrossLayerHistory, ...], ...],
) -> None:
    assert len(paired) == len(TRUTHS) == 6
    for effect_index in range(3):
        usual, slow = paired[effect_index], paired[effect_index + 3]
        assert len(usual) == len(slow) == 160
        for fast_row, slow_row in zip(usual, slow, strict=True):
            assert slow_row.true_predator_arrival == 2 * fast_row.true_predator_arrival
            assert slow_row.true_prey_extirpation >= fast_row.true_prey_extirpation - 1e-12
            for present, fast_count, slow_count in zip(
                fast_row.true_predator_present,
                fast_row.predator_detection_counts,
                slow_row.predator_detection_counts,
                strict=True,
            ):
                assert slow_count <= fast_count
                if not present:
                    assert fast_count == slow_count == 0
            if effect_index == 0:
                assert slow_row.true_prey_extirpation == pytest.approx(
                    fast_row.true_prey_extirpation, rel=1e-14
                )
                assert slow_row.prey_detection_counts == fast_row.prey_detection_counts
    for start in (0, 3):
        for rows in zip(*paired[start : start + 3], strict=True):
            assert len({row.true_predator_arrival for row in rows}) == 1
            assert len({row.predator_detection_counts for row in rows}) == 1
            assert rows[0].true_prey_extirpation >= rows[1].true_prey_extirpation
            assert rows[1].true_prey_extirpation >= rows[2].true_prey_extirpation
            for counts in zip(*(row.prey_detection_counts for row in rows), strict=True):
                assert counts[0] >= counts[1] >= counts[2]


def test_holdout_changes_scores_without_changing_training_fit(
    paired: tuple[tuple[arc2b.CrossLayerHistory, ...], ...], integration: BridgeIntegration
) -> None:
    original = paired[1]
    altered = tuple(
        replace(row, prey_detection_counts=(0,) * 6) if row.split == "holdout" else row
        for row in original
    )
    before = evaluate_dataset(original, integration)
    after = evaluate_dataset(altered, integration)
    assert tuple(array.shape for array in before) == ((3, 3), (3, 3), (3,))
    np.testing.assert_array_equal(before[0], after[0])
    np.testing.assert_array_equal(before[2], after[2])
    assert not np.allclose(before[1], after[1])
    training_cluster = next(row.cluster_id for row in original if row.split == "training")
    contaminated = tuple(
        replace(row, cluster_id=training_cluster) if row.split == "holdout" else row
        for row in original
    )
    with pytest.raises(ValueError, match="cluster-isolated 120/40"):
        evaluate_dataset(contaminated, integration)
