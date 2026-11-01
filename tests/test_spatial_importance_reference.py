from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.integrate import quad  # type: ignore[import-untyped]

from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.importance_reference import integrate, paired_interval
from latent_landscapes.spatial_importance_reference import direct_criterion, prepare_target
from latent_landscapes.spatial_profile import SpatialProfileData


def data() -> SpatialProfileData:
    ids = ("s0",)
    bank = likelihood.compress_bank(np.array([[0.0], [10.0], [70.0]]), ids, series_order=192)
    prey = np.zeros((1, 1, 13), dtype=np.int64)
    prey[:, :, :8] = 2
    predator = np.zeros((1, 1, 6), dtype=np.int64)
    observed = likelihood.prepare_observations(prey, predator, ids, np.array([True]))
    return SpatialProfileData(bank, observed, np.array([0.3]), np.eye(1))


@pytest.mark.parametrize("h", [1.0, 3.0, 30.0])
def test_target_has_prior_normalization_and_matches_quadrature(h: float) -> None:
    criterion = direct_criterion(data())
    parameters = np.array([-5.5, 0.4, math.log(0.6), 0.2])
    target = prepare_target(criterion, parameters, h=h)
    selected = criterion.evaluate_positive(parameters, fixed_h=h)
    assert target.laplace_criterion == pytest.approx(selected.criterion, abs=1e-10)
    sigma = math.exp(parameters[2])
    u = np.array([[-0.4], [0.0], [1.5]])
    ell = target.evaluator.log_values(u + target.eta0).sum(axis=1)
    independent = ell - 0.5 * (u[:, 0] / sigma) ** 2 - math.log(sigma * math.sqrt(2 * math.pi))
    np.testing.assert_allclose(target(u), independent, atol=1e-12)
    center = target.laplace_criterion
    value, error = quad(
        lambda z: math.exp(float(target(np.array([[z]]))[0]) - center),
        -12 * sigma,
        12 * sigma,
        epsabs=1e-11,
        epsrel=1e-10,
    )
    assert error < 1e-8
    exact = center + math.log(value)
    result = integrate(target, target.proposal, identity=f"quad-{h}", stream=0, draws=16384)
    uncertainty = paired_interval(result.batch_log_integrals, estimate=result.log_integral)
    assert abs(result.log_integral - exact) < 5 * uncertainty["standard_error"] + 1e-4


def test_near_zero_spatial_integral_tends_to_exact_zero_family() -> None:
    criterion = direct_criterion(data())
    parameters = np.array([-5.5, 0.4, math.log(1e-5), 0.2])
    target = prepare_target(criterion, parameters, h=3.0)
    zero = criterion.evaluate_sigma_zero(np.array([-5.5, 0.4, 0.2]), fixed_h=3.0)
    assert target.laplace_criterion == pytest.approx(zero.criterion, abs=1e-7)
    assert target.proposal.components[0].cholesky[0, 0] == pytest.approx(1e-5, rel=1e-5)


def test_changed_retained_mode_value_is_not_hidden_as_integration_bias() -> None:
    criterion = direct_criterion(data())
    with pytest.raises(RuntimeError, match="failed latent-mode replay"):
        prepare_target(
            criterion, np.array([-5.5, 0.4, math.log(0.6), 0.2]), h=3.0, expected_laplace=-1.0
        )
