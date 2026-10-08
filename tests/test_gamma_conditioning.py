from __future__ import annotations

import hashlib
import math

import numpy as np
import pytest
from scipy.integrate import quad

from latent_landscapes.gamma_conditioning import (
    CATEGORY_COUNT,
    SURVEY_TIMES,
    _logdiffexp,
    build_gamma_integration,
    interval_mass,
    interval_moment,
)


def _gamma_density(shape: float, scale: float, value: float) -> float:
    rate = 1.0 / scale
    return rate**shape * value ** (shape - 1) * math.exp(-rate * value) / math.gamma(shape)


@pytest.mark.parametrize("shape", (1.0, 3.0))
def test_interval_mass_and_tilted_moment_match_independent_quadrature(shape: float) -> None:
    scale, lower, upper, tilt = 2.0, 3.0, 11.0, 0.07
    expected_mass = quad(
        lambda value: _gamma_density(shape, scale, value),
        lower,
        upper,
        epsabs=1e-14,
        epsrel=1e-12,
    )[0]
    expected_moment = quad(
        lambda value: math.exp(tilt * value) * _gamma_density(shape, scale, value),
        lower,
        upper,
        epsabs=1e-14,
        epsrel=1e-12,
    )[0]
    assert interval_mass(shape, scale, lower, upper) == pytest.approx(
        expected_mass, rel=1e-12, abs=1e-14
    )
    assert interval_moment(shape, scale, lower, upper, tilt) == pytest.approx(
        expected_moment, rel=1e-12, abs=1e-14
    )


def test_rare_upper_tail_uses_survival_difference_without_floor() -> None:
    observed = interval_mass(1.0, 1.0, 50.0, 60.0)
    expected = math.exp(-50.0) - math.exp(-60.0)
    assert observed > 0.0
    assert observed == pytest.approx(expected, rel=1e-12)


def test_log_tail_difference_preserves_near_equal_representable_values() -> None:
    log_high = math.log(0.5)
    log_low = float(np.nextafter(log_high, -math.inf))
    expected = log_high + math.log(-math.expm1(log_low - log_high))
    observed = float(_logdiffexp(np.asarray([log_high]), np.asarray([log_low]))[0])
    assert observed == pytest.approx(expected, rel=1e-12)


def test_conditional_integration_averages_repeated_scales_and_handles_sources() -> None:
    scales = np.asarray(
        [
            [0.0, 2.0, 4.0],
            [0.0, 2.0, 4.0],
            [0.0, 1.0, 4.0],
        ],
        dtype=np.float64,
    )
    result = build_gamma_integration(
        scales,
        3.0,
        ("source", "near", "far"),
        (0.5, 1.0, 2.0),
        (1.0, 3.0),
    )
    assert result.rhos == (0.5, 1.0, 2.0)
    assert result.effects == (1.0, 3.0)
    assert result.site_ids == ("source", "near", "far")
    assert result.category_mass.shape == (3, 3, CATEGORY_COUNT)
    np.testing.assert_allclose(
        result.category_mass[:, 0],
        np.tile([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], (3, 1)),
        rtol=0,
        atol=0,
    )
    np.testing.assert_allclose(result.category_mass.sum(axis=2), 1.0, rtol=0, atol=2e-15)
    for rho_index, moments in enumerate(result.survival_moments):
        assert moments.shape == (2, 3, 7, 7)
        np.testing.assert_allclose(
            moments[:, :, 0, :], np.broadcast_to(result.category_mass[rho_index], (2, 3, 7)),
            rtol=0,
            atol=0,
        )
    expected_checksum = hashlib.sha256(np.ascontiguousarray(scales).tobytes(order="C")).hexdigest()
    assert result.bank_checksum == expected_checksum


def test_survival_moment_matches_direct_quadrature_and_time_zero_is_mass() -> None:
    scales = np.asarray([[2.0]], dtype=np.float64)
    result = build_gamma_integration(scales, 3.0, ("x",), (1.0,), (10.0,))
    q = 0.002 * 9.0
    expected = math.exp(-0.002 * 10.0 * 10.0) * quad(
        lambda value: math.exp(q * value) * _gamma_density(3.0, 2.0, value),
        0.0,
        10.0,
        epsabs=1e-14,
        epsrel=1e-12,
    )[0]
    assert result.survival_moments[0][0, 0, 1, 0] == pytest.approx(
        expected, rel=1e-12, abs=1e-14
    )
    np.testing.assert_allclose(
        result.survival_moments[0][:, :, 0, :],
        result.category_mass[0][None, :, :],
        rtol=0,
        atol=0,
    )


@pytest.mark.parametrize(
    "scales",
    (
        np.asarray([[0.0, 1.0], [0.0, 0.0]]),
        np.asarray([[1.0, np.nan]]),
        np.asarray([[1.0, -1.0]]),
    ),
)
def test_invalid_or_mixed_source_scales_are_rejected(scales: np.ndarray) -> None:
    with pytest.raises(ValueError):
        build_gamma_integration(scales, 3.0, ("a", "b"), (1.0,), (1.0,))


def test_tilted_rate_domain_is_rejected() -> None:
    with pytest.raises(ValueError, match="tilted Gamma rate"):
        interval_moment(3.0, 10.0, 0.0, 10.0, tilt=0.1)
    with pytest.raises(ValueError, match="tilted Gamma rate"):
        build_gamma_integration(np.asarray([[1000.0]]), 3.0, ("x",), (1.0,), (2.0,))


@pytest.mark.parametrize(
    ("shape", "scale", "lower", "upper"),
    ((0.0, 1.0, 0.0, 1.0), (1.0, 0.0, 0.0, 1.0), (1.0, 1.0, 2.0, 1.0)),
)
def test_interval_arguments_are_validated(
    shape: float, scale: float, lower: float, upper: float
) -> None:
    with pytest.raises(ValueError):
        interval_mass(shape, scale, lower, upper)


def test_fixed_survey_calendar_is_used() -> None:
    assert SURVEY_TIMES == (10, 20, 30, 40, 50, 60)
