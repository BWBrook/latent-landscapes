from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from typing import Any, cast

import numpy as np
import pytest
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes.adjusted_background_likelihood import (
    build_integration,
    normalized_hazards,
    oracle_evaluate_dataset,
    prepare_bank,
)
from latent_landscapes.arc2c_likelihood import (
    build_joint_integration,
    evaluate_dataset,
    joint_log_likelihood,
)
from latent_landscapes.goal004.observations import SURVEY_TIMES
from latent_landscapes.integration_weights import reweight_integration
from latent_landscapes.known_nuisance_calibration import AnalystHistory

FloatArray = NDArray[np.float64]


def _emission(count: int) -> float:
    return math.comb(2, count) * 0.65**count * 0.35 ** (2 - count)


def _enumerated_prey(
    counts: tuple[int, ...], arrival: float, hazard: float, effect: float
) -> float:
    """Independently enumerate six death intervals and survival through day 60."""
    times = (0.0, *SURVEY_TIMES)
    survival = [
        math.exp(-hazard * (time + (effect - 1.0) * max(time - arrival, 0.0))) for time in times
    ]
    probability = survival[-1] * math.prod(_emission(count) for count in counts)
    for death_interval in range(len(SURVEY_TIMES)):
        observation = math.prod(_emission(count) for count in counts[:death_interval])
        observation *= math.prod(count == 0 for count in counts[death_interval:])
        probability += (survival[death_interval] - survival[death_interval + 1]) * observation
    return probability


def _forward_prey(counts: tuple[int, ...], arrival: float, hazard: float, effect: float) -> float:
    """Independent two-state forward recursion for the oracle control."""
    alive, dead, previous = 1.0, 0.0, 0.0
    for time, count in zip(SURVEY_TIMES, counts, strict=True):
        pre_time = min(time, arrival) - min(previous, arrival)
        post_time = max(time - arrival, 0.0) - max(previous - arrival, 0.0)
        cumulative = hazard * (pre_time + effect * post_time)
        predicted_alive = alive * math.exp(-cumulative)
        predicted_dead = dead + alive * -math.expm1(-cumulative)
        alive = predicted_alive * _emission(count)
        dead = predicted_dead * (count == 0)
        previous = float(time)
    return alive + dead


@pytest.fixture
def histories() -> tuple[AnalystHistory, ...]:
    prey_patterns = (
        (2, 1, 0, 1, 0, 0),
        (0, 0, 0, 0, 0, 0),
        (2, 2, 2, 2, 2, 2),
        (1, 0, 0, 0, 0, 0),
    )
    return tuple(
        AnalystHistory(
            site_id=f"site-{index:03d}",
            cluster_id=f"cluster-{index // 5:02d}",
            split="training" if index < 120 else "holdout",
            predator_detection_counts=tuple(
                0 if survey < index % 8 else 1 + (index + survey) % 2 for survey in range(6)
            ),
            prey_detection_counts=prey_patterns[index % len(prey_patterns)],
        )
        for index in range(160)
    )


def _bank(site_count: int) -> FloatArray:
    return np.asarray(
        (np.arange(9)[:, None] * 11.0 + np.arange(site_count)[None, :] * 0.7) % 85.0,
        dtype=np.float64,
    )


@pytest.mark.parametrize("beta", [-2.0, 1.2, 2.0])
def test_exact_mixture_matches_independent_enumeration_with_survey_boundaries(beta: float) -> None:
    bank = np.asarray(
        [
            [0.0, 60.0],
            [10.0, 10.0],
            [np.nextafter(10.0, math.inf), 20.0],
            [20.0, 30.0],
            [30.0, 40.0],
            [40.0, 50.0],
            [50.0, 60.0],
            [60.0, 70.0],
            [70.0, 80.0],
        ]
    )
    site_ids = ("second-alphabetically", "first-alphabetically")
    prepared = prepare_bank(bank, site_ids)
    effects = (1.0, 3.0, 10.0)
    hazards = normalized_hazards(beta, np.asarray([-2.0, 0.0, 0.5, 2.0]), np.asarray([-2.0, 0.5]))
    integration = build_integration(prepared, effects, hazards)
    observations = (
        AnalystHistory(site_ids[0], "train", "training", (0,) * 6, (2, 1, 1, 0, 0, 0)),
        AnalystHistory(site_ids[1], "test", "holdout", (0, 0, 1, 0, 1, 0), (0,) * 6),
    )
    expected_moments = np.zeros_like(integration.survival_moments[0])
    expected_joint = np.zeros((len(effects), len(site_ids)))
    predator_marginal = np.zeros(len(site_ids))
    denominator = len(bank) + 7
    times = (0.0, *SURVEY_TIMES)
    for site, row in enumerate(observations):
        for arrival in (*bank[:, site], *arc2b.PSEUDO_ARRIVALS):
            category = next(
                (index for index, time in enumerate(SURVEY_TIMES) if arrival <= time), 6
            )
            predator = math.prod(
                _emission(count) if arrival <= time else float(count == 0)
                for time, count in zip(SURVEY_TIMES, row.predator_detection_counts, strict=True)
            )
            predator_marginal[site] += predator / denominator
            for effect_index, effect in enumerate(effects):
                for time_index, time in enumerate(times):
                    expected_moments[effect_index, site, time_index, category] += (
                        math.exp(-hazards[site] * (time + (effect - 1) * max(time - arrival, 0)))
                        / denominator
                    )
                expected_joint[effect_index, site] += (
                    predator
                    * _enumerated_prey(row.prey_detection_counts, arrival, hazards[site], effect)
                    / denominator
                )
    np.testing.assert_allclose(
        integration.survival_moments[0], expected_moments, rtol=0, atol=2e-16
    )
    observed = joint_log_likelihood(cast(Any, observations), integration)
    np.testing.assert_allclose(observed[0], np.log(expected_joint).sum(axis=1), rtol=0, atol=5e-13)
    for site, row in enumerate(observations):
        actual = joint_log_likelihood(cast(Any, (row,)), integration)[0]
        np.testing.assert_allclose(
            actual - math.log(predator_marginal[site]),
            np.log(expected_joint[:, site] / predator_marginal[site]),
            rtol=0,
            atol=5e-13,
        )
    np.testing.assert_array_equal(prepared.category_counts[0], (2, 2, 1, 1, 1, 1, 1))
    assert prepared.bank_checksum == hashlib.sha256(bank.tobytes(order="C")).hexdigest()
    assert not prepared.category_mass.flags.writeable
    assert not prepared.category_counts.flags.writeable
    assert all(not values.flags.writeable for group in prepared.arrival_offsets for values in group)


def test_beta_zero_matches_unchanged_full_effect_profile_and_holdout(
    histories: tuple[AnalystHistory, ...],
) -> None:
    site_ids = tuple(row.site_id for row in histories)
    bank = _bank(len(histories))
    effects = tuple(float(value) for value in np.linspace(1.0, 10.0, 181))
    hazards = normalized_hazards(0.0, np.asarray([-2.0, 0.0, 1.0]), np.arange(160.0))
    np.testing.assert_array_equal(hazards, np.full(160, 0.002))
    adjusted = build_integration(prepare_bank(bank, site_ids), effects, hazards)
    original = reweight_integration(
        build_joint_integration(bank, site_ids, (1.0,), effects),
        len(bank),
        from_pseudocount=0.5,
        to_pseudocount=1.0,
    )
    np.testing.assert_allclose(adjusted.category_mass, original.category_mass, rtol=0, atol=1e-16)
    np.testing.assert_allclose(
        adjusted.survival_moments[0], original.survival_moments[0], rtol=0, atol=2e-16
    )
    for observed, expected in zip(
        evaluate_dataset(cast(Any, histories), adjusted),
        evaluate_dataset(cast(Any, histories), original),
        strict=True,
    ):
        np.testing.assert_allclose(observed, expected, rtol=0, atol=2e-12)


@pytest.mark.parametrize("beta", [-2.0, 0.0, 2.0])
def test_hazards_normalize_over_whole_map_and_are_finite(beta: float) -> None:
    whole_map = np.linspace(-4.0, 4.0, 1600).reshape(40, 40)
    all_hazards = normalized_hazards(beta, whole_map, whole_map.ravel())
    assert np.isfinite(all_hazards).all() and (all_hazards > 0).all()
    assert float(all_hazards.mean()) == pytest.approx(0.002, rel=2e-15)
    sites = whole_map.ravel()[[0, 1, 7, 110, 800]]
    expected = 0.002 * np.exp(beta * sites) / np.exp(beta * whole_map).mean()
    observed = normalized_hazards(beta, whole_map, sites)
    np.testing.assert_allclose(observed, expected, rtol=2e-15, atol=0)
    np.testing.assert_allclose(
        normalized_hazards(beta, whole_map + 500.0, sites + 500.0), observed, rtol=3e-13, atol=0
    )
    if beta:
        assert not np.isclose(observed.mean(), 0.002, rtol=1e-3)


def test_oracle_matches_independent_forward_recursion_and_explicit_site_order(
    histories: tuple[AnalystHistory, ...],
) -> None:
    site_ids = tuple(row.site_id for row in histories)
    arrivals = np.asarray(([0.0, 10.0, 20.0, 30.0, 60.0, 70.0] * 27)[:160])
    whole_map = np.linspace(-3.0, 3.0, 240)
    hazards = normalized_hazards(-2.0, whole_map, whole_map[:160])
    effects = (1.0, 3.0, 10.0)
    train, holdout = oracle_evaluate_dataset(
        histories, arrivals, effects, hazards, site_ids=site_ids
    )
    direct = np.asarray(
        [
            [
                math.log(_forward_prey(row.prey_detection_counts, arrival, hazard, effect))
                for row, arrival, hazard in zip(histories, arrivals, hazards, strict=True)
            ]
            for effect in effects
        ]
    )
    np.testing.assert_allclose(train, direct[:, :120].sum(axis=1), rtol=0, atol=5e-12)
    np.testing.assert_allclose(holdout, direct[:, 120:].sum(axis=1), rtol=0, atol=2e-12)
    reversed_history_result = oracle_evaluate_dataset(
        tuple(reversed(histories)), arrivals, effects, hazards, site_ids=site_ids
    )
    np.testing.assert_array_equal(reversed_history_result[0], train)
    np.testing.assert_array_equal(reversed_history_result[1], holdout)
    reordered = oracle_evaluate_dataset(
        histories, arrivals[::-1], effects, hazards[::-1], site_ids=site_ids[::-1]
    )
    np.testing.assert_allclose(reordered[0], train, rtol=0, atol=2e-12)
    np.testing.assert_allclose(reordered[1], holdout, rtol=0, atol=2e-12)


def test_no_effect_conditional_prey_likelihood_is_arrival_invariant(
    histories: tuple[AnalystHistory, ...],
) -> None:
    site_ids = tuple(row.site_id for row in histories)
    all_map = np.linspace(-3.0, 3.0, 400)
    hazards = normalized_hazards(2.0, all_map, all_map[::2][:160])
    effects = (1.0, 3.0)
    first = build_integration(prepare_bank(_bank(160), site_ids), effects, hazards)
    second = build_integration(prepare_bank(np.full((9, 160), 100.0), site_ids), effects, hazards)
    _, first_joint, first_predator = evaluate_dataset(cast(Any, histories), first)
    _, second_joint, second_predator = evaluate_dataset(cast(Any, histories), second)
    first_oracle = oracle_evaluate_dataset(
        histories, np.zeros(160), effects, hazards, site_ids=site_ids
    )
    second_oracle = oracle_evaluate_dataset(
        histories, np.full(160, 100.0), effects, hazards, site_ids=site_ids
    )
    np.testing.assert_allclose(
        first_joint[0, 0] - first_predator[0],
        second_joint[0, 0] - second_predator[0],
        rtol=0,
        atol=2e-12,
    )
    assert first_joint[0, 0] - first_predator[0] == pytest.approx(first_oracle[1][0], abs=2e-12)
    for first_scores, second_scores in zip(first_oracle, second_oracle, strict=True):
        assert first_scores[0] == pytest.approx(second_scores[0], abs=2e-12)
        assert not math.isclose(first_scores[1], second_scores[1], rel_tol=1e-4)


def test_holdout_changes_cannot_change_training_scores(
    histories: tuple[AnalystHistory, ...],
) -> None:
    site_ids = tuple(row.site_id for row in histories)
    hazards = normalized_hazards(1.0, np.linspace(-2.0, 2.0, 400), np.linspace(-1.0, 1.0, 160))
    effects = (1.0, 3.0, 10.0)
    integration = build_integration(prepare_bank(_bank(160), site_ids), effects, hazards)
    altered = tuple(
        replace(row, prey_detection_counts=(0,) * 6) if row.split == "holdout" else row
        for row in histories
    )
    before = evaluate_dataset(cast(Any, histories), integration)
    after = evaluate_dataset(cast(Any, altered), integration)
    np.testing.assert_array_equal(before[0], after[0])
    assert not np.array_equal(before[1], after[1])
    oracle_before = oracle_evaluate_dataset(
        histories, np.linspace(0.0, 80.0, 160), effects, hazards, site_ids=site_ids
    )
    oracle_after = oracle_evaluate_dataset(
        altered, np.linspace(0.0, 80.0, 160), effects, hazards, site_ids=site_ids
    )
    np.testing.assert_array_equal(oracle_before[0], oracle_after[0])
    assert not np.array_equal(oracle_before[1], oracle_after[1])


@pytest.mark.parametrize(
    ("bank", "site_ids"),
    [
        (np.ones((2, 2)), ("same", "same")),
        (np.ones((2, 2)), ("only",)),
        (np.ones((0, 1)), ("site",)),
        (np.asarray([[math.nan]]), ("site",)),
        (np.asarray([[-1.0]]), ("site",)),
        (np.asarray([[math.inf]]), ("site",)),
        (np.ones((2, 1)), ("",)),
    ],
)
def test_invalid_bank_inputs_fail(bank: FloatArray, site_ids: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        prepare_bank(bank, site_ids)


@pytest.mark.parametrize("effects", [(), (0.5,), (1.0, 1.0), (3.0, 1.0), (math.nan,)])
def test_invalid_effects_fail(effects: tuple[float, ...]) -> None:
    with pytest.raises(ValueError, match="effects"):
        build_integration(prepare_bank(np.ones((2, 1)), ("site",)), effects, np.asarray([0.002]))


@pytest.mark.parametrize("hazards", [[], [0.0], [-0.1], [math.inf], [0.002, 0.003]])
def test_invalid_site_hazards_fail(hazards: list[float]) -> None:
    with pytest.raises(ValueError, match="site hazards"):
        build_integration(prepare_bank(np.ones((2, 1)), ("site",)), (1.0, 3.0), np.asarray(hazards))


@pytest.mark.parametrize(
    ("beta", "whole_map", "sites", "mean_hazard"),
    [
        (math.nan, [0.0], [0.0], 0.002),
        (0.0, [], [0.0], 0.002),
        (0.0, [math.inf], [0.0], 0.002),
        (0.0, [0.0], [math.nan], 0.002),
        (0.0, [0.0], [], 0.002),
        (0.0, [0.0], [0.0], 0.0),
    ],
)
def test_invalid_normalization_inputs_fail(
    beta: float, whole_map: list[float], sites: list[float], mean_hazard: float
) -> None:
    with pytest.raises(ValueError):
        normalized_hazards(beta, np.asarray(whole_map), np.asarray(sites), mean_hazard)


def test_oracle_rejects_wrong_shapes_site_ids_observations_and_split(
    histories: tuple[AnalystHistory, ...],
) -> None:
    identifiers = tuple(row.site_id for row in histories)
    arrivals, hazards = np.ones(160), np.full(160, 0.002)
    with pytest.raises(ValueError, match="true arrivals"):
        oracle_evaluate_dataset(histories, arrivals[:-1], (1.0,), hazards, site_ids=identifiers)
    with pytest.raises(ValueError, match="true arrivals"):
        oracle_evaluate_dataset(histories, -arrivals, (1.0,), hazards, site_ids=identifiers)
    with pytest.raises(ValueError, match="every site"):
        oracle_evaluate_dataset(histories[:-1], arrivals, (1.0,), hazards, site_ids=identifiers)
    with pytest.raises(ValueError, match="every site"):
        oracle_evaluate_dataset(
            (*histories[:-1], histories[0]), arrivals, (1.0,), hazards, site_ids=identifiers
        )
    invalid_observations = (replace(histories[0], prey_detection_counts=(3,) * 6), *histories[1:])
    with pytest.raises(ValueError, match="two-visit"):
        oracle_evaluate_dataset(
            invalid_observations, arrivals, (1.0,), hazards, site_ids=identifiers
        )
    contaminated = (*histories[:-1], replace(histories[-1], cluster_id=histories[0].cluster_id))
    with pytest.raises(ValueError, match="cluster-isolated"):
        oracle_evaluate_dataset(contaminated, arrivals, (1.0,), hazards, site_ids=identifiers)
