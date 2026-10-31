from __future__ import annotations

import math
from decimal import Decimal, localcontext
from itertools import pairwise

import numpy as np
import pytest

from latent_landscapes import log_domain_likelihood as log_likelihood
from latent_landscapes import preinvasion_likelihood as probability_likelihood


def _decimal_rising(value: Decimal, count: int) -> Decimal:
    result = Decimal(1)
    for offset in range(count):
        result *= value + offset
    return result


def _decimal_shared_probability(
    counts: np.ndarray, alpha: Decimal, beta: Decimal
) -> Decimal:
    total = int(counts.sum())
    trials = 2 * len(counts)
    combinations = math.prod(math.comb(2, int(value)) for value in counts)
    return (
        Decimal(combinations)
        * _decimal_rising(alpha, total)
        * _decimal_rising(beta, trials - total)
        / _decimal_rising(alpha + beta, trials)
    )


def _safe_case() -> tuple[
    probability_likelihood.CompressedBank,
    probability_likelihood.PreInvasionObservations,
    np.ndarray,
]:
    rng = np.random.default_rng(31102026)
    ids = ("site-c", "site-a", "site-b")
    arrivals = rng.uniform(0.0, 85.0, size=(257, len(ids)))
    prey = rng.integers(0, 3, size=(2, len(ids), 13), dtype=np.int64)
    predator = rng.integers(0, 3, size=(2, len(ids), 6), dtype=np.int64)
    observed = np.ones_like(predator, dtype=bool)
    observed[0, 0, 1::2] = False
    observed[1, 2, ::2] = False
    observations = probability_likelihood.prepare_observations(
        prey,
        predator,
        ids,
        [True, False, True],
        predator_observed=observed,
    )
    order = np.argsort(np.asarray(ids), kind="stable")
    bank = probability_likelihood.compress_bank(arrivals[:, order], observations.site_ids)
    hazards = np.asarray([0.002, 0.006, 0.011], dtype=np.float64)
    return bank, observations, hazards


@pytest.mark.parametrize("effect", [1.0, 3.0, 30.0])
def test_well_scaled_scores_match_existing_exact_raw_criterion(effect: float) -> None:
    bank, observations, hazards = _safe_case()
    direct_integration = probability_likelihood.build_integration(
        bank,
        [effect],
        hazards,
        prey_times=observations.prey_times,
        cohort_start=observations.cohort_start,
        exact=True,
    )
    direct = probability_likelihood.score_observations(
        observations, direct_integration, detection_sd=0.17
    )
    stable = log_likelihood.exact_log_scores(
        observations, bank, [effect], hazards, detection_sd=0.17
    )

    np.testing.assert_allclose(
        stable.joint_loglikelihood,
        direct.joint_loglikelihood,
        rtol=0.0,
        atol=4e-13,
    )
    np.testing.assert_allclose(
        stable.predator_loglikelihood,
        direct.predator_loglikelihood,
        rtol=0.0,
        atol=4e-14,
    )
    np.testing.assert_allclose(
        stable.conditional_prey_loglikelihood,
        direct.conditional_prey_loglikelihood,
        rtol=0.0,
        atol=5e-13,
    )
    np.testing.assert_allclose(
        stable.training_logjoint, direct.training_logjoint, rtol=0.0, atol=7e-13
    )
    np.testing.assert_allclose(
        stable.holdout_logjoint, direct.holdout_logjoint, rtol=0.0, atol=4e-13
    )


def test_general_event_mixture_matches_independent_raw_arrival_enumeration() -> None:
    raw_arrivals = np.asarray([[10.0], [20.0], [60.0], [61.0]])
    bank = probability_likelihood.compress_bank(raw_arrivals, ("site",))
    prey_counts = np.asarray([[[2, 1, 2, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]]])
    predator_counts = np.zeros((1, 1, 6), dtype=np.int64)
    observations = probability_likelihood.prepare_observations(
        prey_counts, predator_counts, ("site",), [True]
    )
    p = 0.65
    concentration = 10.0
    detection_sd = math.sqrt(p * (1.0 - p) / (concentration + 1.0))
    hazard = 0.003
    effect = 4.0
    actual = log_likelihood.exact_log_scores(
        observations,
        bank,
        [effect],
        np.asarray([hazard]),
        detection_sd=detection_sd,
    )

    with localcontext() as context:
        context.prec = 80
        decimal_p = Decimal("0.65")
        alpha = decimal_p * Decimal(10)
        beta = (Decimal(1) - decimal_p) * Decimal(10)
        decimal_hazard = Decimal("0.003")
        decimal_effect = Decimal(4)
        cohort_start = Decimal(-60)
        prey_times = tuple(Decimal(-60 + 10 * index) for index in range(13))
        knots = (cohort_start, *prey_times)
        survey_times = tuple(Decimal(10 * index) for index in range(1, 7))
        arrivals = tuple(
            Decimal(value)
            for value in (10, 20, 60, 61, 5, 15, 25, 35, 45, 55, 70)
        )

        event_emissions = []
        flat_prey = prey_counts[0, 0]
        for prefix in range(len(flat_prey)):
            if np.any(flat_prey[prefix:] != 0):
                event_emissions.append(Decimal(0))
            else:
                event_emissions.append(
                    _decimal_shared_probability(flat_prey[:prefix], alpha, beta)
                )
        alive_emission = _decimal_shared_probability(flat_prey, alpha, beta)
        event_total = Decimal(0)
        terminal_total = Decimal(0)
        for arrival in arrivals:
            category = sum(time < arrival for time in survey_times)
            predator_emission = (Decimal(1) - decimal_p) ** (2 * (6 - category))

            survivals = tuple(
                (
                    -decimal_hazard
                    * (
                        time
                        - cohort_start
                        + (decimal_effect - Decimal(1))
                        * max(time - arrival, Decimal(0))
                    )
                ).exp()
                for time in knots
            )
            prey_event = sum(
                (left - right) * emission
                for (left, right), emission in zip(
                    pairwise(survivals), event_emissions, strict=True
                )
            )
            prey_terminal = survivals[-1] * alive_emission
            event_total += predator_emission * prey_event
            terminal_total += predator_emission * prey_terminal
        expected = (event_total + terminal_total) / Decimal(len(arrivals))
        expected_log = float(expected.ln())

    assert event_total > 0
    assert terminal_total > 0
    assert actual.joint_loglikelihood[0, 0, 0] == pytest.approx(expected_log, abs=3e-13)


def test_extreme_hazard_score_is_finite_and_matches_independent_terminal_formula() -> None:
    bank_size = 31
    arrivals = np.zeros((bank_size, 1), dtype=np.float64)
    bank = probability_likelihood.compress_bank(arrivals, ("site",))
    prey = np.full((1, 1, 13), 2, dtype=np.int64)
    predator = np.zeros((1, 1, 6), dtype=np.int64)
    predator[0, 0, 0] = 1
    observations = probability_likelihood.prepare_observations(
        prey, predator, ("site",), [True]
    )
    hazard = 2.0
    effect = 100.0

    stable = log_likelihood.exact_log_scores(
        observations,
        bank,
        [effect],
        np.asarray([hazard]),
    )
    category_zero_empirical = -hazard * (120.0 + (effect - 1.0) * 60.0)
    category_zero_pseudo = -hazard * (120.0 + (effect - 1.0) * 55.0)
    log_survival = (
        np.logaddexp(
            math.log(bank_size) + category_zero_empirical,
            category_zero_pseudo,
        )
        - math.log(bank_size + 7)
    )
    p = 0.65
    prey_log_emission = 26.0 * math.log(p)
    predator_log_emission = (
        math.log(2.0 * p * (1.0 - p)) + 10.0 * math.log1p(-p)
    )
    expected = log_survival + prey_log_emission + predator_log_emission

    assert math.isfinite(float(stable.joint_loglikelihood[0, 0, 0]))
    assert stable.joint_loglikelihood[0, 0, 0] == pytest.approx(expected, abs=2e-12)
    with np.errstate(over="ignore", under="ignore"):
        direct = probability_likelihood.build_integration(
            bank, [effect], np.asarray([hazard]), exact=True
        )
    with pytest.raises(RuntimeError, match="invalid probabilities"):
        probability_likelihood.score_observations(observations, direct)


def test_missing_predator_visits_are_neutral_and_initial_state_and_calendar_are_preserved() -> None:
    ids = ("site-z", "site-a")
    arrivals = np.asarray([[0.0, 10.0], [25.0, 70.0], [55.0, 5.0]])
    prey = np.zeros((1, 2, 13), dtype=np.int64)
    predator = np.asarray([[[2, 1, 0, 2, 1, 0], [0, 2, 1, 0, 2, 1]]])
    missing = np.zeros_like(predator, dtype=bool)
    times = tuple(float(-60 + 10 * index) for index in range(13))
    first = probability_likelihood.prepare_observations(
        prey,
        predator,
        ids,
        [True, False],
        initial_alive=[False, True],
        prey_times=times,
        cohort_start=-70.0,
        predator_observed=missing,
    )
    changed = probability_likelihood.prepare_observations(
        prey,
        2 - predator,
        ids,
        [True, False],
        initial_alive=[False, True],
        prey_times=times,
        cohort_start=-70.0,
        predator_observed=missing,
    )
    order = np.argsort(np.asarray(ids), kind="stable")
    bank = probability_likelihood.compress_bank(arrivals[:, order], first.site_ids)
    hazards = np.asarray([0.004, 0.009])
    first_scores = log_likelihood.exact_log_scores(first, bank, [3.0], hazards)
    changed_scores = log_likelihood.exact_log_scores(changed, bank, [3.0], hazards)

    np.testing.assert_allclose(
        first_scores.predator_loglikelihood, np.zeros((1, 2)), rtol=0.0, atol=3e-16
    )
    np.testing.assert_allclose(
        first_scores.joint_loglikelihood,
        changed_scores.joint_loglikelihood,
        rtol=0.0,
        atol=0.0,
    )
    assert first_scores.training_logjoint[0, 0] == first_scores.joint_loglikelihood[0, 0, 1]
    assert first_scores.holdout_logjoint[0, 0] == first_scores.joint_loglikelihood[0, 0, 0]

    mismatched = probability_likelihood.compress_bank(arrivals[:, order], ("other-a", "other-z"))
    with pytest.raises(ValueError, match="site identifiers"):
        log_likelihood.score_observations(
            first,
            log_likelihood.build_log_quadrature(
                mismatched, [3.0], hazards, prey_times=times, cohort_start=-70.0
            ),
        )


def test_quadrature_rejects_missing_raw_draws_and_nonpositive_hazards() -> None:
    bank, _, hazards = _safe_case()
    no_raw = probability_likelihood.CompressedBank(
        bank.site_ids,
        bank.bank_size,
        bank.category_counts,
        bank.category_mass,
        bank.power_moments,
        np.empty((0, len(bank.site_ids))),
        bank.bank_checksum,
    )
    with pytest.raises(ValueError, match="every raw arrival draw"):
        log_likelihood.build_log_quadrature(no_raw, [3.0], hazards)
    with pytest.raises(ValueError, match="finite, positive"):
        log_likelihood.build_log_quadrature(bank, [3.0], np.asarray([0.0, 0.2, 0.3]))
    with pytest.raises(ValueError, match="at least one"):
        log_likelihood.build_log_quadrature(bank, [0.999], hazards)
