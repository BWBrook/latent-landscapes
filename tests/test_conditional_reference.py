"""Independent analytic and exhaustive controls for exponential-edge integration."""

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import gammainc

from latent_landscapes.conditional_reference import (
    enumerate_jump_chains,
    integrate_reference,
    interval_moment,
    phase_generator,
    target_generator,
)


def test_erlang_cdf_and_tilted_interval_against_analytic_and_quadrature():
    Q, absorption = phase_generator((0.1, 0.1, 0.1))
    for upper in (0.01, 1.0, 20.0, 60.0):
        assert interval_moment(Q, absorption, 0.0, upper) == pytest.approx(
            gammainc(3, 0.1 * upper), rel=1e-11, abs=1e-15
        )
    for lo, hi in ((0.0, 10.0), (10.0, 20.0), (40.0, 60.0), (500.0, 510.0)):
        expected = quad(
            lambda t: np.exp(0.018 * t) * 0.1**3 * t * t * np.exp(-0.1 * t) / 2,
            lo,
            hi,
            epsabs=1e-28,
            epsrel=1e-12,
        )[0]
        assert interval_moment(Q, absorption, lo, hi, 0.018) == pytest.approx(
            expected, rel=1e-11, abs=1e-28
        )


def test_diamond_target_matches_minimum_of_independent_erlang_paths():
    edges = ((0, 1, 10.0), (1, 3, 10.0), (0, 2, 10.0), (2, 3, 10.0))
    Q, absorption = target_generator(4, edges, (0,), 3)
    for t in (0.1, 1.0, 10.0, 60.0):
        one_cdf = gammainc(2, t / 10.0)
        expected = one_cdf * (2 - one_cdf)
        assert interval_moment(Q, absorption, 0.0, t) == pytest.approx(expected, rel=1e-11)


def test_exhaustive_jump_chain_mixture_matches_full_infected_set_reference():
    edges = ((0, 1, 7.0), (1, 2, 12.0), (2, 3, 8.0), (3, 0, 17.0), (1, 3, 9.0))
    sources = (0,)
    site_ids = tuple(f"v{x}" for x in range(4))
    rhos = (0.5, 1.0, 2.0)
    effects = (1.0, 3.0, 5.0)
    generators = [None, *(target_generator(4, edges, sources, t) for t in range(1, 4))]
    exact = integrate_reference(generators, site_ids, rhos, effects)
    chains = enumerate_jump_chains(4, edges, sources)
    assert sum(w for _, _, w in chains) == pytest.approx(1.0)
    mass = np.zeros_like(exact.category_mass)
    moments = [np.zeros_like(m) for m in exact.survival_moments]
    for order, rates, weight in chains:
        conditional = [None, *(phase_generator(rates[: order.index(t) + 1]) for t in range(1, 4))]
        value = integrate_reference(conditional, site_ids, rhos, effects)
        mass += weight * value.category_mass
        for i in range(len(rhos)):
            moments[i] += weight * value.survival_moments[i]
    np.testing.assert_allclose(mass, exact.category_mass, rtol=1e-10, atol=1e-13)
    np.testing.assert_allclose(mass.sum(axis=2), 1.0, rtol=0, atol=1e-13)
    for a, b in zip(moments, exact.survival_moments, strict=True):
        np.testing.assert_allclose(a, b, rtol=1e-10, atol=1e-13)
    # Source arrivals are a point mass at zero, without artificial late categories.
    np.testing.assert_allclose(
        mass[:, 0], np.tile([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], (3, 1)), rtol=0, atol=3e-16
    )


def test_repeated_rate_and_tiny_tail_stay_positive_without_pseudocounts():
    Q, absorption = phase_generator((1.0, 1.0))
    tail = interval_moment(Q, absorption, 50.0, 60.0)
    expected = 51 * np.exp(-50) - 61 * np.exp(-60)
    assert tail > 0
    assert tail == pytest.approx(expected, rel=1e-12, abs=1e-30)
