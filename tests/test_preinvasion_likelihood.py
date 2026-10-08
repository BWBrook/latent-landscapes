from __future__ import annotations

import math
from itertools import product
from typing import Any, cast

import numpy as np
import pytest
from scipy.special import betaln  # type: ignore[import-untyped]

from latent_landscapes.adjusted_background_likelihood import (
    build_integration as build_old_integration,
)
from latent_landscapes.adjusted_background_likelihood import (
    prepare_bank as prepare_old_bank,
)
from latent_landscapes.arc2c_likelihood import joint_log_likelihood as old_joint_log_likelihood
from latent_landscapes.known_nuisance_calibration import AnalystHistory
from latent_landscapes.preinvasion_likelihood import (
    DEFAULT_PREDATOR_TIMES,
    DEFAULT_PREY_TIMES,
    PreInvasionObservations,
    build_exact_integration,
    build_integration,
    one_probability_shared_all_visits,
    oracle_arrivals,
    pre_only_log_likelihood,
    prepare_bank,
    prepare_observations,
    score_observations,
)


def _observations(site_count: int = 3) -> PreInvasionObservations:
    prey = np.zeros((2, site_count, 13), dtype=np.int64)
    predator = np.zeros((2, site_count, 6), dtype=np.int64)
    prey[0, 0, :3] = (2, 1, 0)
    predator[0, 0, 0] = 1
    return prepare_observations(
        prey,
        predator,
        tuple(f"site-{i}" for i in reversed(range(site_count))),
        np.asarray([True] * site_count),
    )


def test_preparation_sorts_sites_and_keeps_calendar() -> None:
    observed = _observations()
    assert observed.site_ids == ("site-0", "site-1", "site-2")
    assert observed.prey_times == DEFAULT_PREY_TIMES
    assert observed.prey_counts.shape == (2, 3, 13)
    assert observed.predator_counts.shape == (2, 3, 6)


def test_extended_calendar_has_continuous_day_zero_survival() -> None:
    bank = np.asarray([[0.0], [10.0], [60.0], [70.0]])
    prepared = prepare_bank(bank, ("site-0",))
    integration = build_exact_integration(prepared, (1.0, 3.0), np.asarray([0.002]))
    # The first seven observations carry the background survival from -60 to 0.
    expected = math.exp(-0.002 * 60.0)
    observed = integration.survival_moments[0, 0, 7].sum()
    assert observed == expected


def test_compressed_and_exact_moments_agree() -> None:
    bank = np.asarray([[0.0, 10.0], [10.0, 20.0], [60.0, 70.0], [5.0, 55.0]])
    prepared = prepare_bank(bank, ("a", "b"))
    compressed = build_integration(prepared, (1.0, 3.0, 10.0), np.asarray([0.002, 0.003]))
    exact = build_exact_integration(prepared, (1.0, 3.0, 10.0), np.asarray([0.002, 0.003]))
    np.testing.assert_allclose(
        compressed.survival_moments,
        exact.survival_moments,
        atol=1e-8,
        rtol=0,
    )


def test_shared_beta_probability_reduces_to_fixed_detection() -> None:
    counts = np.asarray([2, 1, 0])
    fixed = one_probability_shared_all_visits(counts, sd=0.0)
    expected = math.prod(
        math.comb(2, int(k)) * 0.65 ** int(k) * 0.35 ** (2 - int(k)) for k in counts
    )
    assert fixed == expected
    assert one_probability_shared_all_visits(counts, sd=1e-10) == pytest.approx(fixed, abs=1e-9)


def test_pre_only_score_matches_conditional_full_score() -> None:
    observed = _observations()
    observed = prepare_observations(
        observed.prey_counts[:, :, :7],
        observed.predator_counts,
        observed.site_ids,
        observed.training_mask,
        initial_alive=observed.initial_alive,
        prey_times=observed.prey_times[:7],
    )
    bank = prepare_bank(np.asarray([[70.0, 70.0, 70.0]]), observed.site_ids)
    integration = build_exact_integration(
        bank,
        (1.0,),
        np.full(3, 0.002),
        prey_times=observed.prey_times,
    )
    scores = score_observations(observed, integration)
    pre = pre_only_log_likelihood(observed, np.full(3, 0.002))
    np.testing.assert_allclose(scores.conditional_prey_loglikelihood[:, 0], pre, atol=1e-12)


@pytest.mark.parametrize("sd", (0.0, 0.2, 0.4))
@pytest.mark.parametrize(
    "counts",
    tuple(product((0, 1, 2), repeat=2)) + tuple(product((0, 1, 2), repeat=3)),
)
def test_shared_beta_probability_matches_beta_function(sd: float, counts: tuple[int, ...]) -> None:
    p = 0.65
    observed = one_probability_shared_all_visits(np.asarray(counts), p=p, sd=sd)
    if sd == 0.0:
        expected = math.prod(
            math.comb(2, count) * p**count * (1.0 - p) ** (2 - count) for count in counts
        )
    else:
        kappa = p * (1.0 - p) / sd**2 - 1.0
        expected = math.prod(math.comb(2, count) for count in counts) * math.exp(
            betaln(p * kappa + sum(counts), (1.0 - p) * kappa + 2 * len(counts) - sum(counts))
            - betaln(p * kappa, (1.0 - p) * kappa)
        )
    assert observed == pytest.approx(expected, rel=2e-14, abs=2e-15)


def test_oracle_matches_explicit_beta_loss_interval_sum() -> None:
    counts = np.asarray([[[2, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]]])
    predator = np.asarray([[[0, 1, 0, 0, 0, 0]]])
    observed = prepare_observations(counts, predator, ("site",), [True])
    arrival = 10.0
    hazard = 0.002
    effect = 3.0
    p = 0.65
    sd = 0.2
    score = oracle_arrivals(
        observed,
        np.asarray([arrival]),
        (effect,),
        np.asarray([hazard]),
        detection_sd=sd,
    )
    survival = np.exp(
        -hazard
        * (
            np.asarray((-60.0, *DEFAULT_PREY_TIMES)) + 60.0
            + (effect - 1.0) * np.maximum(np.asarray((-60.0, *DEFAULT_PREY_TIMES)) - arrival, 0.0)
        )
    )
    prey_probability = 0.0
    for interval in range(13):
        if interval == 0:
            emission = 1.0
        else:
            emission = one_probability_shared_all_visits(counts[0, 0, :interval], p=p, sd=sd)
        if np.all(counts[0, 0, interval:] == 0):
            prey_probability += (survival[interval] - survival[interval + 1]) * emission
    prey_probability += survival[-1] * one_probability_shared_all_visits(counts[0, 0], p=p, sd=sd)
    predator_probability = math.prod(
        math.comb(2, int(count)) * p**int(count) * (1.0 - p) ** (2 - int(count))
        if arrival <= time
        else float(count == 0)
        for time, count in zip(DEFAULT_PREDATOR_TIMES, predator[0, 0], strict=True)
    )
    assert score.joint_loglikelihood[0, 0, 0] == pytest.approx(
        math.log(prey_probability * predator_probability), abs=2e-13
    )


def test_predator_marginal_is_invariant_to_effect_hazard_and_detection_sd() -> None:
    observed = _observations()
    bank = prepare_bank(np.asarray([[0.0, 10.0, 70.0], [20.0, 40.0, 80.0]]), observed.site_ids)
    first = build_integration(bank, (1.0,), np.full(3, 0.001))
    second = build_integration(bank, (10.0,), np.full(3, 0.006))
    left = score_observations(observed, first, detection_sd=0.0)
    right = score_observations(observed, second, detection_sd=0.4)
    np.testing.assert_array_equal(left.predator_loglikelihood, right.predator_loglikelihood)


def test_six_occasion_full_score_matches_frozen_kernel() -> None:
    bank = np.asarray([[0.0, 60.0], [10.0, 10.0], [20.0, 30.0], [70.0, 80.0]])
    histories = (
        AnalystHistory("a", "cluster", "training", (0, 0, 1, 0, 0, 0), (2, 1, 0, 0, 0, 0)),
        AnalystHistory("b", "cluster", "training", (0, 0, 0, 0, 1, 0), (0, 0, 0, 0, 0, 0)),
    )
    observed = prepare_observations(
        np.asarray([[row.prey_detection_counts for row in histories]]),
        np.asarray([[row.predator_detection_counts for row in histories]]),
        ("a", "b"),
        [True, True],
        prey_times=(10, 20, 30, 40, 50, 60),
        cohort_start=0.0,
    )
    old = build_old_integration(prepare_old_bank(bank, ("a", "b")), (1.0, 3.0), np.full(2, 0.002))
    new = build_exact_integration(
        bank,
        (1.0, 3.0),
        np.full(2, 0.002),
        site_ids=("a", "b"),
        prey_times=(10.0, 20.0, 30.0, 40.0, 50.0, 60.0),
        cohort_start=0.0,
    )
    np.testing.assert_allclose(
        score_observations(observed, new).training_logjoint[0],
        old_joint_log_likelihood(cast(Any, histories), old)[0],
        rtol=0,
        atol=2e-12,
    )


def test_holdout_count_changes_do_not_change_training_or_pre_only_target() -> None:
    observed = _observations()
    changed_prey = observed.prey_counts.copy()
    changed_predator = observed.predator_counts.copy()
    changed_prey[:, ~observed.training_mask] = 2
    changed_predator[:, ~observed.training_mask] = 2
    changed = prepare_observations(
        changed_prey,
        changed_predator,
        observed.site_ids,
        observed.training_mask,
        initial_alive=observed.initial_alive,
    )
    bank = prepare_bank(np.full((4, 3), 70.0), observed.site_ids)
    integration = build_exact_integration(bank, (1.0,), np.full(3, 0.002))
    np.testing.assert_allclose(
        score_observations(observed, integration).training_logjoint,
        score_observations(changed, integration).training_logjoint,
        rtol=0,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        pre_only_log_likelihood(observed, np.full(3, 0.002), return_site=False),
        pre_only_log_likelihood(changed, np.full(3, 0.002), return_site=False),
        rtol=0,
        atol=1e-12,
    )
