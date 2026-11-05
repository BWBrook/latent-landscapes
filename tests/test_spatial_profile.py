from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import replace
from typing import Any, cast

import numpy as np
import pytest
from scipy.interpolate import CubicSpline  # type: ignore[import-untyped]

from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes import spatial_profile
from latent_landscapes.spatial_profile import (
    DETECTION_SD_MAX,
    CurveDomainError,
    SiteCurves,
    SpatialProfileCriterion,
    SpatialProfileData,
)


def _data(site_count: int = 5) -> SpatialProfileData:
    ids = tuple(f"site-{index:02d}" for index in range(site_count))
    bank = likelihood.compress_bank(np.zeros((3, site_count)), ids)
    observations = likelihood.prepare_observations(
        np.zeros((1, site_count, 13), dtype=np.int64),
        np.zeros((1, site_count, 6), dtype=np.int64),
        ids,
        np.ones(site_count, dtype=bool),
    )
    exposure = np.linspace(-0.8, 1.0, site_count)
    distance = np.abs(np.arange(site_count)[:, None] - np.arange(site_count)[None, :])
    covariance = np.exp(-distance / 1.7)
    return SpatialProfileData(bank, observations, exposure, covariance)


def _curve_builder(data: SpatialProfileData) -> spatial_profile.CurveBuilder:
    site = np.arange(len(data.exposure), dtype=float)
    observed = 0.18 + 0.025 * site
    weight = 0.75 + 0.08 * site

    def build(h: float, detection_sd: float, grid: np.ndarray) -> np.ndarray:
        # A Poisson-like concave site likelihood with smooth nuisance effects.
        shifted = grid[None, :] + 0.045 * math.log(h) - 0.12 * detection_sd
        return observed[:, None] * shifted - weight[:, None] * np.exp(shifted)

    return cast(spatial_profile.CurveBuilder, build)


def _criterion(site_count: int = 5) -> SpatialProfileCriterion:
    data = _data(site_count)
    return SpatialProfileCriterion(
        data,
        grid=np.linspace(-8.0, 1.0, 361),
        curve_builder=_curve_builder(data),
    )


def _central_difference(
    function: Callable[[np.ndarray], float], point: np.ndarray, index: int, step: float = 2e-5
) -> float:
    plus = point.copy()
    minus = point.copy()
    plus[index] += step
    minus[index] -= step
    return (function(plus) - function(minus)) / (2.0 * step)


def test_vectorized_spline_derivatives_match_individual_scipy_splines() -> None:
    grid = np.linspace(-4.0, 0.5, 41)
    values = np.vstack(
        [
            0.2 * grid - np.exp(grid),
            0.3 * grid - 1.2 * np.exp(grid),
            0.4 * grid - 0.7 * np.exp(grid),
        ]
    )
    curves = SiteCurves.from_values(grid, values, h=3.0, detection_sd=0.2)
    points = np.array([-3.31, -1.73, -0.22])
    evaluated = curves.evaluate(points)
    references = [CubicSpline(grid, row, bc_type="natural") for row in values]

    for derivative, actual in enumerate(evaluated):
        expected = np.array(
            [spline(points[index], derivative) for index, spline in enumerate(references)]
        )
        np.testing.assert_allclose(actual, expected, rtol=2e-13, atol=2e-13)

    with pytest.raises(CurveDomainError):
        curves.evaluate(np.array([-4.01, -1.0, 0.0]))


@pytest.mark.parametrize("log_sigma", [math.log(0.45), math.log(1e-3)])
def test_positive_laplace_core_gradient_matches_independent_finite_difference(
    log_sigma: float,
) -> None:
    criterion = _criterion()
    point = np.array([-1.35, 0.22, log_sigma, 0.18])
    result = criterion.evaluate_positive(point, fixed_h=3.0)
    assert result.success, result.message

    def value(candidate: np.ndarray) -> float:
        evaluated = criterion.evaluate_positive(candidate, fixed_h=3.0)
        assert evaluated.success, evaluated.message
        return evaluated.criterion

    numerical = np.array([_central_difference(value, point, index) for index in range(3)])
    np.testing.assert_allclose(result.criterion_gradient[:3], numerical, rtol=4e-5, atol=3e-7)


def test_third_derivative_implicit_term_is_required() -> None:
    criterion = _criterion()
    point = np.array([-1.35, 0.22, math.log(0.55), 0.18])
    result = criterion.evaluate_positive(point, fixed_h=3.0)
    assert result.success and result.mode is not None
    curves = criterion.curves(3.0, point[-1])
    _, score, _, _ = curves.evaluate(result.mode.eta)
    envelope_only = np.array([score.sum(), np.dot(criterion.data.exposure, score)])
    numerical = np.array(
        [
            _central_difference(
                lambda candidate: criterion.evaluate_positive(candidate, fixed_h=3.0).criterion,
                point,
                index,
            )
            for index in range(2)
        ]
    )
    full_error = np.max(np.abs(result.criterion_gradient[:2] - numerical))
    envelope_error = np.max(np.abs(envelope_only - numerical))
    assert full_error < 2e-6
    assert envelope_error > 100.0 * full_error


@pytest.mark.parametrize(
    ("fixed_h", "point"),
    [
        (3.0, np.array([-1.35, 0.22, math.log(0.45), 0.18])),
        (None, np.array([-1.35, 0.22, math.log(0.45), math.log(3.2), 0.18])),
        (None, np.array([-1.6, -0.3, math.log(0.6), math.log(30.0), 0.07])),
    ],
)
def test_implicit_nuisance_gradient_matches_full_reoptimised_difference(
    fixed_h: float | None, point: np.ndarray
) -> None:
    criterion = _criterion()
    analytic = criterion.evaluate_positive(point, fixed_h=fixed_h, nuisance_fd=True)
    assert analytic.success, analytic.message
    nuisance = [len(point) - 1] if fixed_h is not None else [len(point) - 2, len(point) - 1]
    for index in nuisance:
        step = 1e-5
        plus, minus = point.copy(), point.copy()
        if fixed_h is None and index == len(point) - 2 and point[index] >= math.log(30.0) - 1e-9:
            minus[index] -= step
            numerical = (
                criterion.evaluate_positive(point, fixed_h=fixed_h).criterion
                - criterion.evaluate_positive(minus, fixed_h=fixed_h).criterion
            ) / step
            tolerance = 1e-4
        else:
            plus[index] += step
            minus[index] -= step
            numerical = (
                criterion.evaluate_positive(plus, fixed_h=fixed_h).criterion
                - criterion.evaluate_positive(minus, fixed_h=fixed_h).criterion
            ) / (2 * step)
            tolerance = 1e-6
        assert analytic.criterion_gradient[index] == pytest.approx(
            numerical, rel=1e-5, abs=tolerance
        )


def test_exact_zero_family_and_nuisance_derivatives() -> None:
    criterion = _criterion()
    point = np.array([-1.35, 0.22, math.log(3.0), 0.18])
    result = criterion.evaluate_sigma_zero(point, nuisance_fd=True)
    assert result.success

    numerical = np.array(
        [
            _central_difference(
                lambda candidate: criterion.evaluate_sigma_zero(candidate).criterion,
                point,
                index,
            )
            for index in range(len(point))
        ]
    )
    np.testing.assert_allclose(result.criterion_gradient, numerical, rtol=2e-5, atol=2e-7)


@pytest.mark.parametrize("sigma_zero", [False, True])
@pytest.mark.parametrize("h", [1.0, 30.0])
def test_free_effect_endpoints_match_fixed_effect_and_keep_finite_gradients(
    sigma_zero: bool, h: float
) -> None:
    criterion = _criterion()
    evaluate = criterion.evaluate_sigma_zero if sigma_zero else criterion.evaluate_positive
    core = [-1.35, 0.22] if sigma_zero else [-1.35, 0.22, math.log(0.45)]
    free_point = np.array([*core, math.log(h), 0.18])
    fixed_point = np.array([*core, 0.18])
    free = evaluate(free_point, nuisance_fd=True)
    fixed = evaluate(fixed_point, fixed_h=h, nuisance_fd=True)

    assert free.success, free.message
    assert fixed.success, fixed.message
    assert free.h == fixed.h == h
    assert free.criterion == fixed.criterion
    np.testing.assert_array_equal(
        free.criterion_gradient[: len(core)], fixed.criterion_gradient[: len(core)]
    )
    assert free.criterion_gradient[-1] == fixed.criterion_gradient[-1]
    assert np.isfinite(free.criterion_gradient).all()
    np.testing.assert_array_equal(free.parameters, free_point)


@pytest.mark.parametrize("sigma_zero", [False, True])
@pytest.mark.parametrize(
    "log_h",
    [
        np.nextafter(0.0, -math.inf),
        np.nextafter(math.log(30.0), math.inf),
        -0.01,
        math.log(30.01),
        1000.0,
    ],
)
def test_free_effect_rejects_outside_log_domain_before_transform(
    sigma_zero: bool, log_h: float
) -> None:
    criterion = _criterion()
    evaluate = criterion.evaluate_sigma_zero if sigma_zero else criterion.evaluate_positive
    core = [-1.35, 0.22] if sigma_zero else [-1.35, 0.22, math.log(0.45)]
    result = evaluate(np.array([*core, log_h, 0.18]), nuisance_fd=True)

    assert not result.success
    assert result.criterion == -math.inf
    assert result.objective == math.inf
    assert result.mode is None
    assert "outside the fitted domain" in result.message


def test_exact_cache_keys_and_mode_is_a_deterministic_function_of_outer_parameters() -> None:
    criterion = _criterion()
    first = criterion.curves(3.0, 0.18)
    assert criterion.curves(3.0, 0.18) is first
    assert criterion.curves(np.nextafter(3.0, 4.0), 0.18) is not first

    point = np.array([-1.35, 0.22, math.log(0.45), 0.18])
    other = np.array([-0.9, -0.4, math.log(1.7), 0.05])
    before = criterion.evaluate_positive(point, fixed_h=3.0)
    criterion.evaluate_positive(other, fixed_h=7.0)
    after = criterion.evaluate_positive(point, fixed_h=3.0)
    fresh = _criterion().evaluate_positive(point, fixed_h=3.0)
    assert before.success and before.mode is not None
    assert before.criterion == after.criterion == fresh.criterion
    np.testing.assert_array_equal(before.mode.u, after.mode.u)
    assert before.mode.branch_count == 1


def test_damped_newton_converges_strictly_on_concave_site_curves() -> None:
    criterion = _criterion(3)
    point = np.array([-1.35, 0.22, math.log(0.45), 0.18])

    result = criterion.evaluate_positive(point, fixed_h=3.0)

    assert result.success and result.mode is not None
    assert result.mode.message.startswith("damped Newton")
    assert result.mode.newton_decrement <= criterion.decrement_tolerance
    assert criterion.stats["mode_failures"] == 0
    assert int(criterion.stats["mode_evaluations"]) < 20


class _NearSingularEvaluator:
    """Joint objective -eps (u - target)^2 / 2 under a unit prior precision."""

    numerical_domain = (-math.inf, math.inf)

    def __init__(self, eps: float, target: float) -> None:
        self.eps, self.target = eps, target

    def evaluate(self, eta: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        a = 1.0 - self.eps
        ell = 0.5 * a * eta**2 + self.eps * self.target * eta
        return ell, a * eta + self.eps * self.target, np.full_like(eta, a), np.zeros_like(eta)


def test_small_gradient_on_near_singular_ridge_is_not_accepted_as_a_mode() -> None:
    # Regression for cell-00-rep-005-arm-B: a near-flat point with gradient
    # below 1e-8 but Newton decrement far above tolerance was accepted, and the
    # near-singular Laplace term inflated the criterion by about 4.5 units.
    criterion = _criterion(1)
    evaluator = _NearSingularEvaluator(eps=1e-10, target=10.0)
    start = np.zeros(1)
    gradient = evaluator.evaluate(start)[1] - start
    assert np.max(np.abs(gradient)) < 1e-8

    branch = criterion._mode_branch(np.zeros(1), np.eye(1), evaluator, start)

    assert branch is not None
    np.testing.assert_allclose(branch[0], [10.0], rtol=0.0, atol=1e-6)
    assert branch[4] <= criterion.decrement_tolerance


class _DoubleWellEvaluator:
    """Joint objective u^2/2 - u^4/4: maxima at +/-1 and a saddle at zero."""

    numerical_domain = (-math.inf, math.inf)

    def evaluate(self, eta: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        ell = eta**2 - 0.25 * eta**4
        return ell, 2.0 * eta - eta**3, 2.0 - 3.0 * eta**2, -6.0 * eta


def test_damped_newton_leaves_indefinite_regions_and_rejects_saddles() -> None:
    criterion = _criterion(1)
    evaluator = _DoubleWellEvaluator()

    branch = criterion._mode_branch(np.zeros(1), np.eye(1), evaluator, np.array([0.1]))
    assert branch is not None
    np.testing.assert_allclose(branch[0], [1.0], rtol=0.0, atol=1e-8)

    assert criterion._mode_branch(np.zeros(1), np.eye(1), evaluator, np.zeros(1)) is None


class _OffsetQuadraticEvaluator:
    """Concave site curve with a large constant, so gains sit at roundoff."""

    numerical_domain = (-math.inf, math.inf)

    def evaluate(self, eta: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        ell = 1500.0 + 2.0 * eta - 0.5 * eta**2
        return ell, 2.0 - eta, -np.ones_like(eta), np.zeros_like(eta)


def test_newton_step_with_gain_below_roundoff_is_accepted_not_damped_into_failure() -> None:
    # Regression: a residual of order 1e-6 whose predicted gain is below
    # floating-point resolution must still be taken, not rejected by the
    # gain-ratio test until damping exhausts the solve.
    criterion = _criterion(1)
    start = np.array([1.0 + 3e-6])
    branch = criterion._mode_branch(np.zeros(1), np.eye(1), _OffsetQuadraticEvaluator(), start)
    assert branch is not None
    np.testing.assert_allclose(branch[0], [1.0], rtol=0.0, atol=1e-12)


def test_floored_laplace_gradient_matches_reoptimised_difference_where_floor_is_active() -> None:
    # Locally convex site terms make I - C'diag(ell'')C nearly singular; the
    # smooth eigenvalue floor must stay finite, continuous and differentiable.
    data = _data(5)
    site = np.arange(5.0)

    def build(h: float, detection_sd: float, grid: np.ndarray) -> np.ndarray:
        shifted = grid[None, :] + 0.045 * math.log(h) - 0.12 * detection_sd
        return (
            (0.18 + 0.025 * site)[:, None] * shifted
            - (0.75 + 0.08 * site)[:, None] * np.exp(shifted)
            + 0.45 * np.log1p(np.exp(3.0 * (shifted + 2.0)))
        )

    criterion = SpatialProfileCriterion(
        data, grid=np.linspace(-12.0, 8.0, 801), curve_builder=cast(Any, build)
    )
    point = np.array([-3.0, 0.2, math.log(0.695), 0.18])
    analytic = criterion.evaluate_positive(point, fixed_h=3.0, nuisance_fd=True)
    assert analytic.success and analytic.mode is not None
    assert analytic.mode.combined_min_eigenvalue < spatial_profile.LAPLACE_FLOOR
    for index in range(4):
        numerical = _central_difference(
            lambda x: criterion.evaluate_positive(x, fixed_h=3.0).criterion, point, index, 1e-6
        )
        assert analytic.criterion_gradient[index] == pytest.approx(numerical, rel=1e-4, abs=1e-5)


def test_eigenvalue_floor_is_negligible_at_ordinary_eigenvalues_and_caps_at_zero() -> None:
    values = np.array([1e-12, 0.05, 0.89, 1.0, 3.0])
    floored, _ = spatial_profile._floored_eigenvalues(values)
    assert floored[0] == pytest.approx(spatial_profile.LAPLACE_FLOOR, rel=1e-5)
    assert floored[3] == 1.0
    np.testing.assert_allclose(floored[2:], values[2:], rtol=2e-5, atol=0.0)
    assert np.all(np.diff(floored) > 0.0)


def _toy_evaluation(value: float, gradient: np.ndarray, success: bool = True) -> Any:
    return spatial_profile.CriterionEvaluation(
        value if success else -math.inf,
        -value if success else math.inf,
        gradient,
        -gradient,
        success,
        "ok" if success else "failed",
        True,
        None,
        np.zeros(len(gradient)),
        1.0,
        0.1,
    )


def test_trust_region_escapes_an_exact_saddle_start() -> None:
    # f = -x^2 + y^2 - y^4/4 has a saddle at the origin and maxima at y = +/-sqrt(2).
    def evaluate(z: np.ndarray) -> Any:
        x, y = z
        value = -(x**2) + y**2 - 0.25 * y**4
        return _toy_evaluation(value, np.array([-2.0 * x, 2.0 * y - y**3]))

    point, result, info = _criterion(1)._trust_region(
        evaluate, np.zeros(2), ((-5.0, 5.0), (-5.0, 5.0)), maxiter=80, gradient_tolerance=1e-8
    )
    assert info.success and result.success
    np.testing.assert_allclose(np.abs(point), [0.0, math.sqrt(2.0)], atol=1e-6)


def test_trust_region_accepts_a_bound_maximum_with_kkt_and_survives_failed_columns() -> None:
    calls = {"n": 0}

    def evaluate(z: np.ndarray) -> Any:
        calls["n"] += 1
        x, y = z
        if 0.3 < y <= 0.30002:
            return _toy_evaluation(0.0, np.zeros(2), success=False)
        value = -((x - 5.0) ** 2) - (y - 0.3) ** 2
        return _toy_evaluation(value, np.array([-2.0 * (x - 5.0), -2.0 * (y - 0.3)]))

    point, result, info = _criterion(1)._trust_region(
        evaluate,
        np.array([0.0, 0.0]),
        ((-2.0, 1.0), (-2.0, 2.0)),
        maxiter=80,
        gradient_tolerance=1e-7,
    )
    assert info.success and result.success
    np.testing.assert_allclose(point, [1.0, 0.3], atol=1e-5)


def test_trust_region_surrounded_by_failures_is_not_successful() -> None:
    def evaluate(z: np.ndarray) -> Any:
        if np.any(z != 0.0):
            return _toy_evaluation(0.0, np.zeros(2), success=False)
        return _toy_evaluation(0.0, np.array([1.0, 1.0]))

    _, _, info = _criterion(1)._trust_region(
        evaluate, np.zeros(2), ((-1.0, 1.0), (-1.0, 1.0)), maxiter=20, gradient_tolerance=1e-6
    )
    assert not info.success


def test_mode_iteration_limit_is_a_deterministic_failure() -> None:
    data = _data(3)
    criterion = SpatialProfileCriterion(
        data,
        grid=np.linspace(-8.0, 1.0, 361),
        curve_builder=_curve_builder(data),
        mode_max_iterations=1,
    )
    point = np.array([-1.35, 0.22, math.log(1.9), 0.18])
    first = criterion.evaluate_positive(point, fixed_h=3.0)
    second = criterion.evaluate_positive(point, fixed_h=3.0)
    assert not first.success and not second.success
    assert first.message == second.message == "latent mode did not strictly converge"
    assert criterion.stats["mode_failures"] == 2


def test_correlated_small_sigma_mode_is_continuous_under_outer_finite_differences() -> None:
    rng = np.random.default_rng(18102026)
    site_count = 6
    ids = tuple(f"s{index}" for index in range(site_count))
    bank = likelihood.compress_bank(np.zeros((3, site_count)), ids)
    observed = likelihood.prepare_observations(
        np.zeros((1, site_count, 13), dtype=np.int64),
        np.zeros((1, site_count, 6), dtype=np.int64),
        ids,
        np.ones(site_count, dtype=bool),
    )
    exposure = np.linspace(-1.1, 0.9, site_count)
    root = rng.normal(size=(site_count, site_count))
    covariance = root @ root.T
    scale = np.sqrt(np.diag(covariance))
    covariance = covariance / scale[:, None] / scale[None, :] + 0.15 * np.eye(site_count)
    weight = np.linspace(0.7, 1.2, site_count)
    observed_rate = np.linspace(0.12, 0.32, site_count)

    def builder(h: float, detection_sd: float, grid: np.ndarray) -> np.ndarray:
        shifted = grid[None, :] + 0.08 * math.log(h) - 0.15 * detection_sd
        return (
            observed_rate[:, None] * shifted
            - weight[:, None] * np.exp(shifted)
            - 0.015 * shifted**2
        )

    criterion = SpatialProfileCriterion(
        SpatialProfileData(bank, observed, exposure, covariance),
        grid=np.linspace(-12.0, 4.0, 801),
        curve_builder=builder,
    )
    point = np.array([-1.6, 0.3, math.log(0.02), math.log(3.4), 0.17])
    points = [point.copy()]
    beta_plus = point.copy()
    beta_plus[1] += 2e-5
    points.append(beta_plus)
    moderate_sigma = point.copy()
    moderate_sigma[2] = math.log(0.25)
    points.append(moderate_sigma)
    sigma_minus = moderate_sigma.copy()
    sigma_minus[2] -= 2e-5 * max(1.0, abs(float(sigma_minus[2])))
    points.append(sigma_minus)

    for candidate in points:
        result = criterion.evaluate_positive(candidate)
        assert result.success, result.message
        assert result.mode is not None
        assert result.mode.score_inf <= 10.0 * criterion.mode_tolerance
        assert result.mode.newton_step_inf <= criterion.mode_tolerance
        assert result.mode.newton_decrement <= criterion.mode_tolerance

    numerical = np.array(
        [
            _central_difference(
                lambda candidate: criterion.evaluate_positive(candidate).criterion,
                point,
                index,
            )
            for index in range(3)
        ]
    )
    analytic = criterion.evaluate_positive(point).criterion_gradient[:3]
    np.testing.assert_allclose(analytic, numerical, rtol=2e-5, atol=1e-6)


def test_high_order_compressed_bank_matches_direct_integration_through_x40() -> None:
    rng = np.random.default_rng(20261018)
    arrivals = rng.uniform(0.0, 70.0, size=(257, 3))
    ids = ("site-00", "site-01", "site-02")
    compressed = likelihood.compress_bank(arrivals, ids, series_order=192)
    compressed = replace(compressed, max_x=40.0)
    for x in (5.0, 20.0, 40.0):
        hazards = np.full(3, x / (10.0 * (30.0 - 1.0)))
        approximate = likelihood.build_integration(
            compressed, [30.0], hazards, exact=False, enforce_domain=True
        )
        direct = likelihood.build_integration(compressed, [30.0], hazards, exact=True)
        np.testing.assert_allclose(
            approximate.survival_moments,
            direct.survival_moments,
            rtol=3e-13,
            atol=3e-15,
        )
        assert approximate.series_bound <= 1e-10


def test_engine_rejects_unsupported_max_x_order_pair() -> None:
    data = _data(3)
    unsupported = replace(data.bank, max_x=40.0)
    with pytest.raises(ValueError, match="unsupported by its series order"):
        SpatialProfileCriterion(
            SpatialProfileData(unsupported, data.observed, data.exposure, data.covariance),
            curve_builder=_curve_builder(data),
        )


def test_exact_fallback_rejects_compressed_bank_without_raw_arrivals() -> None:
    data = _data(3)
    compressed_only = replace(data.bank, bank_arrivals=np.empty((0, 3), dtype=np.float64))
    criterion = SpatialProfileCriterion(
        SpatialProfileData(compressed_only, data.observed, data.exposure, data.covariance),
        grid=np.linspace(-12.0, -2.0, 161),
    )
    with pytest.raises(ValueError, match="requires the raw arrival bank"):
        criterion.curves(30.0, 0.1)


def test_profile_data_requires_preselected_training_sites() -> None:
    data = _data(3)
    mixed = replace(data.observed, training_mask=np.array([True, False, True]))
    with pytest.raises(ValueError, match="preselected to training sites"):
        SpatialProfileData(data.bank, mixed, data.exposure, data.covariance)


def test_vectorized_curve_scoring_matches_scalar_likelihood_with_missing_visits_and_dead_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ids = tuple(f"site-{index:02d}" for index in range(4))
    prey = np.zeros((1, 4, 13), dtype=np.int64)
    prey[0, 0, :3] = (2, 1, 1)
    prey[0, 1, :6] = (1, 0, 2, 0, 1, 0)
    predator = np.array(
        [[[0, 1, 0, 2, 1, 0], [0, 0, 1, 0, 0, 2], [0, 0, 0, 0, 0, 0], [2, 1, 0, 0, 1, 0]]],
        dtype=np.int64,
    )
    predator_observed = np.ones_like(predator, dtype=bool)
    predator_observed[0, 0, (1, 4)] = False
    predator_observed[0, 2, :] = False
    observed = likelihood.prepare_observations(
        prey,
        predator,
        ids,
        np.ones(4, dtype=bool),
        initial_alive=np.array([True, True, False, True]),
        predator_observed=predator_observed,
    )
    # Exercise the uncached-predator path as well as the missing-visit mask.
    observed = replace(observed, predator_emissions=None)
    arrivals = np.random.default_rng(20261018).uniform(0.0, 70.0, size=(97, 4))
    bank = likelihood.compress_bank(arrivals, ids)
    distance = np.abs(np.arange(4)[:, None] - np.arange(4)[None, :])
    data = SpatialProfileData(bank, observed, np.linspace(-1.0, 1.0, 4), np.exp(-distance / 2.0))
    grid = np.linspace(-8.0, -2.0, 25)

    reference_engine = SpatialProfileCriterion(data, grid=grid)
    integrations = reference_engine._integrations(2.0)
    expected = np.column_stack(
        [
            likelihood.score_observations(observed, row, detection_sd=0.12).joint_loglikelihood[
                0, 0
            ]
            for row in integrations
        ]
    )

    original_prey = likelihood._prey_emissions
    original_predator = likelihood._predator_emissions
    calls = {"prey": 0, "predator": 0}

    def counted_prey(*args: object, **kwargs: object) -> tuple[np.ndarray, np.ndarray]:
        calls["prey"] += 1
        return original_prey(*args, **kwargs)  # type: ignore[arg-type]

    def counted_predator(*args: object, **kwargs: object) -> np.ndarray:
        calls["predator"] += 1
        return original_predator(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(likelihood, "_prey_emissions", counted_prey)
    monkeypatch.setattr(likelihood, "_predator_emissions", counted_predator)
    engine = SpatialProfileCriterion(data, grid=grid)
    actual = cast(SiteCurves, engine.curves(2.0, 0.12)).values
    engine.curves(3.0, 0.12)

    np.testing.assert_allclose(actual, expected, rtol=2e-15, atol=2e-15)
    assert calls == {"prey": 1, "predator": 1}


def test_guards_reject_invalid_covariance_domain_and_nuisance() -> None:
    data = _data(3)
    with pytest.raises(ValueError, match="positive definite"):
        SpatialProfileCriterion(
            SpatialProfileData(data.bank, data.observed, data.exposure, np.ones((3, 3))),
            curve_builder=_curve_builder(data),
        )

    criterion = _criterion(3)
    invalid_h = criterion.evaluate_positive(
        np.array([-1.0, 0.0, math.log(0.2), 0.0]), fixed_h=30.01
    )
    assert not invalid_h.success and math.isinf(invalid_h.objective)
    invalid_sd = criterion.evaluate_sigma_zero(np.array([-1.0, 0.0, DETECTION_SD_MAX]), fixed_h=3.0)
    assert not invalid_sd.success
    outside_grid = criterion.evaluate_sigma_zero(np.array([-9.0, 0.0, 0.1]), fixed_h=3.0)
    assert not outside_grid.success
    assert "outside" in outside_grid.message

    narrow = SpatialProfileCriterion(
        data,
        grid=np.linspace(-3.0, -0.5, 101),
        curve_builder=_curve_builder(data),
    )
    unsupported = narrow.evaluate_positive(np.array([-1.4, 0.1, math.log(0.8), 0.15]), fixed_h=3.0)
    assert not unsupported.success
    assert "SD Laplace proposal range" in unsupported.message


def test_fixed_h_fit_always_resolves_both_variance_families() -> None:
    criterion = _criterion(3)
    positive_start = np.array([-1.4, 0.1, math.log(0.3), 0.15])
    zero_start = np.array([-1.4, 0.1, 0.15])
    result = criterion.fit_profile(
        fixed_h=3.0,
        positive_starts=[positive_start],
        sigma_zero_starts=[zero_start],
        kkt_tolerance=2e-3,
        maxiter=40,
    )
    assert result.resolved
    assert result.best is not None
    assert result.best_positive is not None
    assert result.best_sigma_zero is not None
    assert {row.family for row in result.candidates} == {"positive_sigma", "sigma_zero"}


def test_free_profile_sweeps_both_directions_and_both_families() -> None:
    criterion = _criterion(3)
    result = criterion.fit_profile(
        profile_h_grid=(1.0, 3.0, 30.0),
        positive_starts=[np.array([-1.4, 0.1, math.log(0.3), math.log(3.0), 0.15])],
        sigma_zero_starts=[np.array([-1.4, 0.1, math.log(3.0), 0.15])],
        kkt_tolerance=0.1,
        maxiter=20,
    )
    for direction in ("up", "down"):
        for h in (1, 3, 30):
            prefix = f"profile_{direction}_h_{h}"
            rows = [row for row in result.candidates if row.source.startswith(prefix)]
            assert {row.family for row in rows} == {"positive_sigma", "sigma_zero"}
    assert any(row.source.startswith("free") for row in result.candidates)


def test_direct_evaluator_removes_only_interpolation_domain_constraints() -> None:
    data = _data()
    data = replace(data, bank=replace(data.bank, max_x=10000.0))
    observed = 0.18 + 0.025 * np.arange(5)
    weight = 0.75 + 0.08 * np.arange(5)

    class DirectPoisson:
        numerical_domain = (-math.inf, math.inf)

        def evaluate(self, eta: np.ndarray) -> tuple[np.ndarray, ...]:
            rate = weight * np.exp(eta)
            return observed * eta - rate, observed - rate, -rate, -rate

    def factory(h: float, detection_sd: float) -> spatial_profile.SiteEvaluator:
        del h, detection_sd
        return cast(spatial_profile.SiteEvaluator, DirectPoisson())

    criterion = SpatialProfileCriterion(data, evaluator_factory=factory)
    point = np.array([-1.35, 0.22, math.log(0.45), 0.18])
    result = criterion.evaluate_positive(point, fixed_h=3.0)
    assert result.success, result.message
    assert result.mode is not None
    assert result.mode.proposal_eta_max > criterion.grid[-1]
    assert result.mode.proposal_grid_supported
    assert not result.mode.bound_touch

    def value(candidate: np.ndarray) -> float:
        evaluation = criterion.evaluate_positive(candidate, fixed_h=3.0)
        assert evaluation.success, evaluation.message
        return evaluation.criterion

    numerical = np.array([_central_difference(value, point, i) for i in range(3)])
    np.testing.assert_allclose(result.criterion_gradient[:3], numerical, atol=1e-7, rtol=1e-6)
    assert criterion.stats["curve_builds"] == 1
