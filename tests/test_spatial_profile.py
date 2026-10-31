from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import replace
from types import SimpleNamespace
from typing import cast

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


class _RoutingEvaluator:
    numerical_domain = (-math.inf, math.inf)

    def __init__(self, route: str) -> None:
        self.route = route

    def evaluate(
        self, eta: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        if self.route == "non_pd":
            curvature = np.where(np.abs(eta) < 0.5, 2.0, -1.0)
            ell = eta.copy()
        elif self.route == "line_search":
            curvature = np.full_like(eta, -1.0)
            ell = np.zeros_like(eta)
        elif self.route == "exhausted":
            curvature = np.full_like(eta, -99.0)
            ell = eta.copy()
        else:
            raise AssertionError(self.route)
        return ell, np.ones_like(eta), curvature, np.zeros_like(eta)


class _QuadraticEvaluator:
    numerical_domain = (-math.inf, math.inf)

    def __init__(self, optimum: float) -> None:
        self.optimum = optimum
        self.points: list[np.ndarray] = []

    def evaluate(
        self, eta: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        self.points.append(eta.copy())
        linear = 2.0 * self.optimum
        ell = linear * eta - 0.5 * eta**2
        return ell, linear - eta, -np.ones_like(eta), np.zeros_like(eta)


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


def test_exact_cache_keys_and_warm_mode_branch_preserve_best_mode() -> None:
    criterion = _criterion()
    first = criterion.curves(3.0, 0.18)
    assert criterion.curves(3.0, 0.18) is first
    assert criterion.curves(np.nextafter(3.0, 4.0), 0.18) is not first

    point = np.array([-1.35, 0.22, math.log(0.45), 0.18])
    cold = criterion.evaluate_positive(point, fixed_h=3.0)
    assert cold.success and cold.mode is not None
    deliberately_bad = np.full(criterion.site_count, 3.0)
    warm = criterion.evaluate_positive(point, fixed_h=3.0, mode_start=deliberately_bad)
    assert warm.success and warm.mode is not None
    assert warm.mode.branch_count == 2
    assert warm.criterion >= cold.criterion - 1e-11
    np.testing.assert_allclose(warm.mode.u, cold.mode.u, rtol=1e-8, atol=1e-9)


def test_newton_first_converges_without_lbfgs_on_concave_site_curves() -> None:
    criterion = _criterion(3)
    point = np.array([-1.35, 0.22, math.log(0.45), 0.18])

    result = criterion.evaluate_positive(point, fixed_h=3.0)

    assert result.success and result.mode is not None
    assert result.mode.message.startswith("Newton-first")
    assert criterion.stats["mode_newton_first_successes"] == 1
    assert criterion.stats["mode_newton_first_fallbacks"] == 0
    assert criterion.stats["mode_lbfgs_fallback_evaluations"] == 0
    assert int(criterion.stats["mode_newton_first_evaluations"]) < 20


def test_newton_first_caps_extreme_trial_direction_without_changing_stationarity() -> None:
    criterion = _criterion(1)
    evaluator = _QuadraticEvaluator(optimum=3.5)

    branch = criterion._mode_branch(
        np.zeros(1),
        np.eye(1),
        evaluator,
        np.zeros(1),
    )

    assert branch is not None
    np.testing.assert_allclose(branch[0], [3.5], rtol=0.0, atol=1e-14)
    trials = np.array([point[0] for point in evaluator.points])
    assert np.max(np.abs(np.diff(trials))) <= 1.0
    assert criterion.stats["mode_newton_first_bounded_steps"] == 3
    assert criterion.stats["mode_newton_first_fallbacks"] == 0
    assert branch[3] == pytest.approx(0.0, abs=1e-14)


def test_newton_first_accepts_one_guarded_polish_when_residual_improves() -> None:
    criterion = _criterion(1)
    evaluator = _QuadraticEvaluator(optimum=1.0)
    start = np.array([1.0 + 4e-9])

    branch = criterion._mode_branch(
        np.zeros(1),
        np.eye(1),
        evaluator,
        start,
    )

    assert branch is not None
    np.testing.assert_allclose(branch[0], [1.0], rtol=0.0, atol=0.0)
    assert branch[2] == pytest.approx(0.0, abs=0.0)
    assert "guarded polish accepted" in branch[-1]
    assert criterion.stats["mode_newton_first_polish_attempts"] == 1
    assert criterion.stats["mode_newton_first_polish_acceptances"] == 1
    assert len(evaluator.points) == 2


def test_newton_first_retains_valid_incumbent_when_polish_does_not_improve() -> None:
    criterion = _criterion(1)
    evaluator = _QuadraticEvaluator(optimum=1.0)
    start = np.array([1.0])

    branch = criterion._mode_branch(
        np.zeros(1),
        np.eye(1),
        evaluator,
        start,
    )

    assert branch is not None
    np.testing.assert_array_equal(branch[0], start)
    assert "valid incumbent retained" in branch[-1]
    assert criterion.stats["mode_newton_first_polish_attempts"] == 1
    assert criterion.stats["mode_newton_first_polish_acceptances"] == 0
    assert len(evaluator.points) == 2


@pytest.mark.parametrize(
    ("route", "reason", "start"),
    [
        ("non_pd", "non_pd", np.array([0.2, -0.2])),
        ("line_search", "line_search", np.zeros(2)),
        ("exhausted", "exhausted", np.zeros(2)),
    ],
)
def test_newton_first_failures_route_to_lbfgs_from_original_start(
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    reason: str,
    start: np.ndarray,
) -> None:
    criterion = _criterion(2)
    seen_starts: list[np.ndarray] = []

    def fake_minimize(
        function: object,
        x0: np.ndarray,
        **kwargs: object,
    ) -> object:
        del function, kwargs
        seen_starts.append(np.asarray(x0).copy())
        return SimpleNamespace(x=np.ones_like(x0), nit=1, nfev=0, message="fake fallback")

    monkeypatch.setattr(spatial_profile, "minimize", fake_minimize)
    branch = criterion._mode_branch(
        np.zeros(2),
        np.eye(2),
        _RoutingEvaluator(route),
        start,
    )

    assert branch is not None
    np.testing.assert_array_equal(seen_starts, [start])
    np.testing.assert_allclose(branch[0], np.ones(2), rtol=0.0, atol=0.0)
    assert branch[-1] == "fake fallback"
    assert criterion.stats["mode_newton_first_successes"] == 0
    assert criterion.stats["mode_newton_first_fallbacks"] == 1
    assert criterion.stats[f"mode_newton_first_fallback_{reason}"] == 1
    assert int(criterion.stats["mode_lbfgs_fallback_evaluations"]) >= 2


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
