from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import multivariate_normal  # type: ignore[import-untyped]

from latent_landscapes.importance_reference import (
    Component,
    Proposal,
    defensive_proposal,
    fixed_outer_contrast,
    integrate,
    paired_interval,
    pareto_tail,
)


def test_gaussian_density_and_matched_integral() -> None:
    covariance = np.array([[1.3, 0.2], [0.2, 0.7]])
    mean = np.array([0.3, -0.7])
    component = Component(mean, np.linalg.cholesky(covariance), 1.0)
    proposal = Proposal((component,))
    values = np.array([[0.0, 0.0], [1.0, -2.0], [9.0, 7.0]])
    np.testing.assert_allclose(
        component.logpdf(values), multivariate_normal.logpdf(values, mean, covariance)
    )
    estimate = integrate(
        lambda x: component.logpdf(x) + 1000.0,
        proposal,
        identity="matched-gaussian",
        stream=0,
        draws=4096,
    )
    assert estimate.log_integral == pytest.approx(1000.0, abs=2e-12)
    np.testing.assert_allclose(estimate.batch_log_integrals, 1000.0, atol=2e-12)
    assert estimate.diagnostics["ess"] == pytest.approx(4096.0, rel=1e-12)


def test_defensive_mixture_is_normalized_and_stratification_is_unbiased() -> None:
    proposal = defensive_proposal(
        [
            (np.array([-1.0]), np.array([[0.5]]), np.log(0.7)),
            (np.array([2.0]), np.array([[2.0]]), np.log(0.3)),
        ]
    )
    estimate = integrate(
        proposal.logpdf, proposal, identity="mixture-control", stream=0, draws=16400
    )
    assert estimate.log_integral == pytest.approx(0.0, abs=1e-13)
    np.testing.assert_allclose(estimate.batch_log_integrals, 0.0, atol=1e-13)
    assert sum(estimate.diagnostics["component_draws_per_batch"]) == 1025
    assert len(proposal.components) == 6


def test_mixture_integrates_an_analytic_gaussian_with_reported_uncertainty() -> None:
    proposal = defensive_proposal([(np.zeros(2), np.eye(2), 0.0)])
    normal = Component(np.array([0.1, -0.15]), np.eye(2), 1.0)
    estimate = integrate(normal.logpdf, proposal, identity="normal-control", stream=1, draws=16384)
    interval = paired_interval(estimate.batch_log_integrals, estimate=estimate.log_integral)
    assert abs(estimate.log_integral) <= 5 * interval["standard_error"] + 1e-4
    assert estimate.diagnostics["relative_ess"] > 0.7
    assert estimate.diagnostics["maximum_normalized_weight"] < 0.001


def test_common_random_draws_are_nested_and_confirmation_is_independent() -> None:
    proposal = defensive_proposal([(np.zeros(3), np.eye(3), 0.0)])
    for index, component in enumerate(proposal.components):
        small = component.draw(21, identity="nested", stream=0, batch=2, component=index)
        big = component.draw(42, identity="nested", stream=0, batch=2, component=index)
        np.testing.assert_array_equal(small, big[:21])
        independent = component.draw(21, identity="nested", stream=1, batch=2, component=index)
        assert not np.array_equal(small, independent)
    assert np.all(proposal.counts(2048) >= proposal.counts(1024))


def test_paired_constant_correction_cancels_monte_carlo_error() -> None:
    proposal = defensive_proposal([(np.zeros(1), np.eye(1), 0.0)])
    target = Component(np.array([0.1]), np.eye(1), 1.0)
    free = integrate(
        lambda u: target.logpdf(u) + 0.5, proposal, identity="paired", stream=0, draws=4096
    )
    fixed = integrate(
        lambda u: target.logpdf(u) + 0.2, proposal, identity="paired", stream=0, draws=4096
    )
    result = fixed_outer_contrast(free, fixed, laplace_free=0.4, laplace_point=0.1)
    assert result["estimate"] == pytest.approx(0.0, abs=2e-14)
    assert result["half_width"] < 2e-14


def test_invalid_target_is_failure_not_omitted_draws() -> None:
    proposal = Proposal((Component(np.zeros(1), np.eye(1), 1.0),))
    with pytest.raises(ValueError, match="invalid importance target"):
        integrate(
            lambda u: np.full(len(u), np.nan), proposal, identity="invalid", stream=0, draws=4096
        )


def test_tail_diagnostic_reports_unavailable_degenerate_weights() -> None:
    assert pareto_tail(np.zeros(1000))["status"] == "unavailable"
    assert pareto_tail(np.zeros(100))["status"] == "unavailable"


def test_student_proposal_density_has_correct_normalization() -> None:
    from scipy.stats import multivariate_t  # type: ignore[import-untyped]

    covariance = np.array([[0.6, 0.1], [0.1, 0.9]])
    mean = np.array([0.3, -0.1])
    component = Component(mean, np.linalg.cholesky(covariance), 1.0, 5.0)
    values = np.array([[0.0, 0.0], [1.0, 2.0], [19.0, -23.0]])
    np.testing.assert_allclose(
        component.logpdf(values), multivariate_t.logpdf(values, mean, covariance, 5)
    )
