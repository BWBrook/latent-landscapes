from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pytest

from latent_landscapes import log_domain_likelihood
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.differentiable_likelihood import (
    LikelihoodDomainError,
    prepare_site_likelihood,
)


def _fixture() -> tuple[
    likelihood.CompressedBank,
    likelihood.PreInvasionObservations,
]:
    ids = ("site-c", "site-a", "site-b")
    arrivals = np.random.default_rng(20261031).uniform(0.0, 85.0, size=(257, 3))
    arrivals[:5] = np.asarray(
        [
            [0.0, 10.0, 20.0],
            [10.0, 20.0, 60.0],
            [60.0, 61.0, 70.0],
            [5.0, 15.0, 25.0],
            [55.0, 45.0, 35.0],
        ]
    )
    prey = np.zeros((1, 3, 13), dtype=np.int64)
    prey[0, 0, :4] = (2, 1, 2, 1)
    prey[0, 1, :7] = (1, 0, 2, 0, 1, 1, 0)
    prey[0, 2, :10] = (2, 2, 1, 2, 1, 0, 2, 1, 1, 0)
    predator = np.asarray(
        [[[1, 0, 2, 1, 0, 2], [0, 1, 0, 2, 1, 0], [2, 0, 1, 1, 0, 2]]],
        dtype=np.int64,
    )
    observed = np.ones_like(predator, dtype=bool)
    observed[0, 0, (1, 4)] = False
    observed[0, 2, (0, 3, 5)] = False
    observations = likelihood.prepare_observations(
        prey,
        predator,
        ids,
        [True, True, True],
        predator_observed=observed,
    )
    order = np.argsort(np.asarray(ids), kind="stable")
    bank = likelihood.compress_bank(
        arrivals[:, order], observations.site_ids, series_order=48
    )
    return bank, observations


def test_positive_series_matches_raw_reference_and_exact_derivatives() -> None:
    bank, observations = _fixture()
    eta = np.asarray((-6.0, -5.2, -4.7))
    series = prepare_site_likelihood(
        observations, bank, 3.0, detection_sd=0.17
    )
    exact = prepare_site_likelihood(
        observations,
        replace(bank, max_x=0.0),
        3.0,
        detection_sd=0.17,
    )

    series_result = series.evaluate(eta)
    exact_result = exact.evaluate(eta)
    reference = log_domain_likelihood.exact_log_scores(
        observations,
        bank,
        [3.0],
        np.exp(eta),
        detection_sd=0.17,
    ).joint_loglikelihood[0, 0]

    np.testing.assert_allclose(series_result[0], reference, rtol=0.0, atol=2e-13)
    for series_row, exact_row in zip(series_result, exact_result, strict=True):
        np.testing.assert_allclose(series_row, exact_row, rtol=3e-12, atol=3e-12)
    assert series.stats["last_series_site_count"] == 3
    assert series.stats["last_exact_site_count"] == 0
    assert exact.stats["last_series_site_count"] == 0
    assert exact.stats["last_exact_site_count"] == 3
    assert float(series.stats["last_max_relative_tail_bound"]) < 1e-10
    cached = series.evaluate(eta.copy())
    assert cached[0] is series_result[0]
    assert series.stats["cache_hits"] == 1
    assert series.stats["last_series_site_count"] == 0
    assert series.stats["series_site_evaluations"] == 3


def test_effect_one_drops_all_positive_degree_terms_and_matches_exact_oracle() -> None:
    bank, observations = _fixture()
    eta = np.asarray((-2.0, -5.2, -0.875))
    series = prepare_site_likelihood(observations, bank, 1.0, detection_sd=0.17)
    exact_result = tuple(
        np.asarray(row)
        for row in zip(
            *(series._evaluate_raw_site(site, float(eta[site])) for site in range(3)),
            strict=True,
        )
    )

    series_result = series.evaluate(eta)
    reference = log_domain_likelihood.exact_log_scores(
        observations,
        bank,
        [1.0],
        np.exp(eta),
        detection_sd=0.17,
    ).joint_loglikelihood[0, 0]

    np.testing.assert_allclose(series_result[0], reference, rtol=0.0, atol=2e-13)
    for series_row, exact_row in zip(series_result, exact_result, strict=True):
        np.testing.assert_allclose(series_row, exact_row, rtol=2e-12, atol=2e-12)


@pytest.mark.parametrize("force_exact", [False, True])
def test_first_three_derivatives_match_nested_central_differences(force_exact: bool) -> None:
    bank, observations = _fixture()
    if force_exact:
        bank = replace(bank, max_x=0.0)
    evaluator = prepare_site_likelihood(observations, bank, 4.0, detection_sd=0.11)
    eta = np.asarray((-5.1, -5.4, -5.7))
    base = evaluator.evaluate(eta)
    site = 1
    step = 2e-4

    plus = eta.copy()
    plus[site] += step
    minus = eta.copy()
    minus[site] -= step
    plus_result = evaluator.evaluate(plus)
    minus_result = evaluator.evaluate(minus)

    numerical = (
        (plus_result[0][site] - minus_result[0][site]) / (2.0 * step),
        (plus_result[1][site] - minus_result[1][site]) / (2.0 * step),
        (plus_result[2][site] - minus_result[2][site]) / (2.0 * step),
    )
    np.testing.assert_allclose(
        np.asarray(base[1:])[:, site],
        numerical,
        rtol=2e-6,
        atol=2e-7,
    )


def test_high_hazard_raw_branch_is_finite_and_matches_log_domain_reference() -> None:
    bank_size = 31
    arrivals = np.zeros((bank_size, 1), dtype=np.float64)
    bank = likelihood.compress_bank(arrivals, ("site",), series_order=48)
    prey = np.full((1, 1, 13), 2, dtype=np.int64)
    predator = np.zeros((1, 1, 6), dtype=np.int64)
    predator[0, 0, 0] = 1
    observations = likelihood.prepare_observations(
        prey, predator, ("site",), [True]
    )
    evaluator = prepare_site_likelihood(observations, bank, 30.0)
    eta = np.asarray([-0.875])

    result = evaluator.evaluate(eta)
    reference = log_domain_likelihood.exact_log_scores(
        observations, bank, [30.0], np.exp(eta)
    ).joint_loglikelihood[0, 0]

    assert all(math.isfinite(float(row[0])) for row in result)
    assert result[0][0] == pytest.approx(reference[0], abs=2e-12)
    assert evaluator.stats["last_exact_site_ids"] == ("site",)
    assert float(evaluator.stats["max_observed_x"]) > bank.max_x


@pytest.mark.parametrize("x", [150.0, 289.0])
def test_order_816_high_x_derivatives_match_exact_raw_with_roundoff_tolerance(
    x: float,
) -> None:
    arrivals = np.random.default_rng(816).uniform(0.0, 70.0, size=(257, 1))
    bank = replace(
        likelihood.compress_bank(arrivals, ("site",), series_order=816),
        max_x=290.0,
    )
    prey = np.zeros((1, 1, 13), dtype=np.int64)
    prey[0, 0, :6] = (2, 1, 0, 2, 1, 1)
    predator = np.asarray([[[0, 1, 0, 2, 1, 0]]], dtype=np.int64)
    observations = likelihood.prepare_observations(
        prey, predator, ("site",), [True]
    )
    eta = np.asarray([math.log(x / 290.0)])
    series = prepare_site_likelihood(observations, bank, 30.0, detection_sd=0.13)
    exact = prepare_site_likelihood(
        observations, replace(bank, max_x=0.0), 30.0, detection_sd=0.13
    )

    series_result = series.evaluate(eta)
    exact_result = exact.evaluate(eta)

    for derivative in range(3):
        np.testing.assert_allclose(
            series_result[derivative], exact_result[derivative], rtol=0.0, atol=5e-10
        )
    np.testing.assert_allclose(
        series_result[3], exact_result[3], rtol=0.0, atol=2e-9
    )
    assert series.stats["tail_bound_scope"] == (
        "series_truncation_only_excludes_floating_roundoff"
    )


@pytest.mark.parametrize("eta", [-8.0, -0.875])
def test_initial_dead_all_zero_prey_is_hazard_invariant_with_missing_visits(
    eta: float,
) -> None:
    arrivals = np.asarray([[0.0], [10.0], [20.0], [60.0], [61.0]])
    bank = likelihood.compress_bank(arrivals, ("site",), series_order=48)
    prey = np.zeros((1, 1, 13), dtype=np.int64)
    predator = np.asarray([[[2, 1, 0, 2, 1, 0]]], dtype=np.int64)
    missing = np.zeros_like(predator, dtype=bool)
    observations = likelihood.prepare_observations(
        prey,
        predator,
        ("site",),
        [True],
        initial_alive=False,
        predator_observed=missing,
    )
    evaluator = prepare_site_likelihood(observations, bank, 30.0, detection_sd=0.2)

    value, d1, d2, d3 = evaluator.evaluate(np.asarray([eta]))

    assert value[0] == pytest.approx(0.0, abs=2e-13)
    np.testing.assert_allclose((d1[0], d2[0], d3[0]), 0.0, rtol=0.0, atol=3e-10)


def test_custom_cohort_category_edges_and_k_plus_seven_match_reference() -> None:
    arrivals = np.asarray([[0.0], [10.0], [20.0], [60.0], [61.0]])
    bank = likelihood.compress_bank(arrivals, ("site",), series_order=48)
    prey = np.zeros((1, 1, 13), dtype=np.int64)
    prey[0, 0, :3] = (2, 1, 1)
    predator = np.asarray([[[0, 0, 1, 0, 0, 0]]], dtype=np.int64)
    times = tuple(float(-60 + 10 * index) for index in range(13))
    observations = likelihood.prepare_observations(
        prey,
        predator,
        ("site",),
        [True],
        cohort_start=-70.0,
        prey_times=times,
    )
    evaluator = prepare_site_likelihood(observations, bank, 5.0, detection_sd=0.13)
    eta = np.asarray([-4.5])

    actual = evaluator.evaluate(eta)[0]
    reference = log_domain_likelihood.exact_log_scores(
        observations,
        bank,
        [5.0],
        np.exp(eta),
        detection_sd=0.13,
    ).joint_loglikelihood[0, 0]

    np.testing.assert_allclose(actual, reference, rtol=0.0, atol=2e-13)


@pytest.mark.parametrize("effect", [1.0, 3.0])
def test_sparse_calendar_uses_exact_raw_same_law_branch(effect: float) -> None:
    arrivals = np.random.default_rng(73).uniform(0.0, 70.0, size=(73, 1))
    bank = likelihood.compress_bank(arrivals, ("site",), series_order=48)
    times = (-60.0, -40.0, -20.0, 0.0, 20.0, 40.0, 60.0)
    prey = np.asarray([[[2, 1, 0, 2, 1, 0, 0]]], dtype=np.int64)
    predator = np.asarray([[[0, 1, 0, 2, 1, 0]]], dtype=np.int64)
    observations = likelihood.prepare_observations(
        prey, predator, ("site",), [True], prey_times=times
    )
    evaluator = prepare_site_likelihood(observations, bank, effect, detection_sd=0.12)
    eta = np.asarray([-4.0])

    actual = evaluator.evaluate(eta)[0]
    reference = log_domain_likelihood.exact_log_scores(
        observations,
        bank,
        [effect],
        np.exp(eta),
        detection_sd=0.12,
    ).joint_loglikelihood[0, 0]

    np.testing.assert_allclose(actual, reference, rtol=0.0, atol=2e-13)
    assert evaluator.stats["last_series_site_count"] == 0
    assert evaluator.stats["last_exact_site_count"] == 1
    compressed_only = replace(bank, bank_arrivals=np.empty((0, 1), dtype=np.float64))
    with pytest.raises(ValueError, match="unsupported prey calendar"):
        prepare_site_likelihood(observations, compressed_only, effect)


def test_compressed_only_bank_exposes_and_enforces_finite_series_domain() -> None:
    bank, observations = _fixture()
    compressed_only = replace(
        bank, bank_arrivals=np.empty((0, len(bank.site_ids)), dtype=np.float64)
    )
    evaluator = prepare_site_likelihood(observations, compressed_only, 30.0)

    assert evaluator.numerical_domain[0] == -math.inf
    assert math.isfinite(evaluator.numerical_domain[1])
    supported = np.full(3, evaluator.numerical_domain[1] - 0.1)
    assert np.isfinite(evaluator.evaluate(supported)[0]).all()
    unsupported = supported.copy()
    unsupported[1] = evaluator.numerical_domain[1] + 0.1
    with pytest.raises(LikelihoodDomainError, match="without raw arrivals"):
        evaluator.evaluate(unsupported)


def test_factory_rejects_mismatched_sites_multiple_histories_and_invalid_effect() -> None:
    bank, observations = _fixture()
    mismatched = replace(bank, site_ids=("x", "y", "z"))
    with pytest.raises(ValueError, match="site identifiers"):
        prepare_site_likelihood(observations, mismatched, 3.0)
    assert observations.predator_emissions is not None
    assert observations.predator_observed is not None
    multiple = replace(
        observations,
        prey_counts=np.repeat(observations.prey_counts, 2, axis=0),
        predator_counts=np.repeat(observations.predator_counts, 2, axis=0),
        predator_emissions=np.repeat(observations.predator_emissions, 2, axis=0),
        predator_observed=np.repeat(observations.predator_observed, 2, axis=0),
    )
    with pytest.raises(ValueError, match="exactly one history"):
        prepare_site_likelihood(multiple, bank, 3.0)
    with pytest.raises(ValueError, match="at least one"):
        prepare_site_likelihood(observations, bank, 0.99)
