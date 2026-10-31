"""Efficient sampled-site Gaussian-process Laplace profile criterion.

This module implements the bounded Paper 1 development criterion.  It is a
working spatial composite criterion, not a claim that the sampled-site GP is
the map-normalised data-generating likelihood.

For site log likelihoods ``ell_i(eta_i)`` and ``eta = alpha + beta A + u``,
the positive-variance criterion is

``sum(ell) - u' Q u / 2 - log|C| / 2 - log|H| / 2``,

evaluated at the latent mode, where ``C = sigma^2 K``, ``Q = C^-1`` and
``H = Q - diag(ell'')``.  The implementation evaluates the two determinant
terms as ``log|I - L_C' diag(ell'') L_C|`` to avoid cancellation near zero
variance.  Gradients for alpha, beta and log(sigma) include implicit mode
differentiation and the third site derivatives required by the Laplace term.
The exact sigma=0 family is kept as a separate lower-dimensional fit.
"""

from __future__ import annotations

import math
import time
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import CubicSpline  # type: ignore[import-untyped]
from scipy.linalg import cho_factor, cho_solve  # type: ignore[import-untyped]
from scipy.optimize import OptimizeResult, minimize  # type: ignore[import-untyped]

from latent_landscapes import preinvasion_likelihood as likelihood

FloatArray = NDArray[np.float64]
DEFAULT_GRID = np.linspace(-12.0, -2.0, 161)
DEFAULT_PROFILE_H_GRID = tuple(float(value) for value in np.geomspace(1.0, 30.0, 35))
MEAN_DETECTION = 0.65
DETECTION_SD_MAX = math.sqrt(MEAN_DETECTION * (1.0 - MEAN_DETECTION))


class CurveDomainError(RuntimeError):
    """Raised when a requested latent log hazard is outside the spline grid."""


class CurveBuilder(Protocol):
    """Callable used to construct site curves, primarily for focused tests."""

    def __call__(self, h: float, detection_sd: float, grid: FloatArray) -> FloatArray: ...


class SiteEvaluator(Protocol):
    @property
    def numerical_domain(self) -> tuple[float, float]: ...

    def evaluate(
        self, eta: NDArray[Any]
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]: ...


class EvaluatorFactory(Protocol):
    def __call__(self, h: float, detection_sd: float) -> SiteEvaluator: ...


@dataclass(frozen=True, slots=True)
class SpatialProfileData:
    """Inputs for one history already subset to sampled training sites.

    The profile engine has no holdout-scoring role.  Callers must subset the
    bank, observations, exposure and covariance to the training sites before
    constructing this object; a mixed training/holdout mask is rejected.
    """

    bank: likelihood.CompressedBank
    observed: likelihood.PreInvasionObservations
    exposure: FloatArray
    covariance: FloatArray

    def __post_init__(self) -> None:
        n = len(self.bank.site_ids)
        exposure = np.asarray(self.exposure, dtype=np.float64)
        covariance = np.asarray(self.covariance, dtype=np.float64)
        if self.bank.site_ids != self.observed.site_ids:
            raise ValueError("bank and observations must have identical site identifiers")
        if self.observed.prey_counts.shape[0] != 1:
            raise ValueError("the profile criterion requires exactly one observed history")
        if not np.all(self.observed.training_mask):
            raise ValueError("profile inputs must be preselected to training sites")
        if exposure.shape != (n,) or not np.isfinite(exposure).all():
            raise ValueError("exposure must be finite with one value per site")
        if covariance.shape != (n, n) or not np.isfinite(covariance).all():
            raise ValueError("covariance must be a finite square site matrix")
        if not np.allclose(covariance, covariance.T, rtol=1e-12, atol=1e-12):
            raise ValueError("covariance must be symmetric")
        object.__setattr__(self, "exposure", np.ascontiguousarray(exposure))
        object.__setattr__(self, "covariance", np.ascontiguousarray(covariance))


@dataclass(frozen=True, slots=True)
class SiteCurves:
    """Natural cubic site curves with vectorized derivative evaluation."""

    grid: FloatArray
    values: FloatArray
    coefficients: FloatArray  # polynomial order x interval x site
    h: float
    detection_sd: float
    build_seconds: float = 0.0
    exact_nodes: tuple[int, ...] = ()
    max_series_bound: float = 0.0

    @property
    def numerical_domain(self) -> tuple[float, float]:
        return float(self.grid[0]), float(self.grid[-1])

    @classmethod
    def from_values(
        cls,
        grid: NDArray[Any],
        values: NDArray[Any],
        *,
        h: float,
        detection_sd: float,
        build_seconds: float = 0.0,
        exact_nodes: Sequence[int] = (),
        max_series_bound: float = 0.0,
    ) -> SiteCurves:
        x = np.asarray(grid, dtype=np.float64)
        y = np.asarray(values, dtype=np.float64)
        if x.ndim != 1 or len(x) < 4 or not np.isfinite(x).all() or np.any(np.diff(x) <= 0):
            raise ValueError("curve grid must be finite, strictly increasing and have four nodes")
        if y.ndim != 2 or y.shape[1] != len(x) or not np.isfinite(y).all():
            raise ValueError("curve values must be finite with shape (site, grid)")
        spline = CubicSpline(x, y, axis=1, bc_type="natural", extrapolate=False)
        coefficients = np.ascontiguousarray(spline.c)
        # scipy stores the non-interpolation dimensions after the interval axis.
        if coefficients.shape != (4, len(x) - 1, y.shape[0]):
            raise RuntimeError("unexpected CubicSpline coefficient layout")
        return cls(
            np.ascontiguousarray(x),
            np.ascontiguousarray(y),
            coefficients,
            float(h),
            float(detection_sd),
            float(build_seconds),
            tuple(int(value) for value in exact_nodes),
            float(max_series_bound),
        )

    def evaluate(self, eta: NDArray[Any]) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
        """Return site log likelihood and its first three eta derivatives."""
        point = np.asarray(eta, dtype=np.float64)
        site_count = self.values.shape[0]
        if point.shape != (site_count,) or not np.isfinite(point).all():
            raise ValueError("eta must be finite with one value per site")
        lo, hi = float(self.grid[0]), float(self.grid[-1])
        if np.any(point < lo) or np.any(point > hi):
            raise CurveDomainError(
                f"latent log hazard range [{float(point.min()):g}, {float(point.max()):g}] "
                f"is outside [{lo:g}, {hi:g}]"
            )
        interval = np.searchsorted(self.grid, point, side="right") - 1
        interval = np.clip(interval, 0, len(self.grid) - 2)
        site = np.arange(site_count)
        delta = point - self.grid[interval]
        c0 = self.coefficients[0, interval, site]
        c1 = self.coefficients[1, interval, site]
        c2 = self.coefficients[2, interval, site]
        c3 = self.coefficients[3, interval, site]
        value = ((c0 * delta + c1) * delta + c2) * delta + c3
        first = (3.0 * c0 * delta + 2.0 * c1) * delta + c2
        second = 6.0 * c0 * delta + 2.0 * c1
        third = 6.0 * c0
        return value, first, second, third


@dataclass(frozen=True, slots=True)
class ModeResult:
    """Validated latent-mode result for a positive-variance evaluation."""

    u: FloatArray
    eta: FloatArray
    value: float
    score_inf: float
    success: bool
    message: str
    iterations: int
    evaluations: int
    branch_count: int
    hessian: FloatArray | None = field(repr=False)
    precision: FloatArray | None = field(repr=False)
    hessian_inverse: FloatArray | None = field(repr=False)
    logdet_c: float = math.nan
    logdet_h: float = math.nan
    logdet_combined: float = math.nan
    bound_touch: bool = False
    proposal_eta_min: float = math.nan
    proposal_eta_max: float = math.nan
    proposal_grid_supported: bool = False
    newton_step_inf: float = math.nan
    newton_decrement: float = math.nan


@dataclass(frozen=True, slots=True)
class CriterionEvaluation:
    """One maximized-logcriterion evaluation and objective derivatives."""

    criterion: float
    objective: float
    criterion_gradient: FloatArray
    objective_gradient: FloatArray
    success: bool
    message: str
    sigma_zero: bool
    mode: ModeResult | None
    parameters: FloatArray
    h: float
    detection_sd: float


@dataclass(frozen=True, slots=True)
class FitCandidate:
    """One retained outer-optimization candidate."""

    family: str
    source: str
    parameters: FloatArray
    evaluation: CriterionEvaluation
    optimizer_success: bool
    optimizer_message: str
    iterations: int
    evaluations: int
    projected_gradient_inf: float
    eligible: bool


@dataclass(frozen=True, slots=True)
class ProfileFit:
    """Positive-variance and exact-zero fits with all candidate evidence."""

    fixed_h: float | None
    best: FitCandidate | None
    best_positive: FitCandidate | None
    best_sigma_zero: FitCandidate | None
    candidates: tuple[FitCandidate, ...]
    resolved: bool
    elapsed_seconds: float


class SpatialProfileCriterion:
    """Cached, differentiable sampled-site GP Laplace criterion."""

    def __init__(
        self,
        data: SpatialProfileData,
        *,
        grid: NDArray[Any] = DEFAULT_GRID,
        curve_builder: CurveBuilder | None = None,
        evaluator_factory: EvaluatorFactory | None = None,
        mode_tolerance: float = 1e-8,
        curve_cache_size: int = 24,
        integration_cache_size: int = 3,
        proposal_guard_sd: float = 4.0,
        series_error_tolerance: float = 1e-10,
    ) -> None:
        self.data = data
        if curve_builder is not None and evaluator_factory is not None:
            raise ValueError("choose either a curve builder or a direct evaluator")
        self._evaluator_factory = evaluator_factory
        self.grid = np.asarray(grid, dtype=np.float64)
        if (
            self.grid.ndim != 1
            or len(self.grid) < 4
            or not np.isfinite(self.grid).all()
            or np.any(np.diff(self.grid) <= 0)
        ):
            raise ValueError("grid must be finite, one-dimensional and strictly increasing")
        self.mode_tolerance = float(mode_tolerance)
        if not math.isfinite(self.mode_tolerance) or self.mode_tolerance <= 0.0:
            raise ValueError("mode_tolerance must be finite and positive")
        if curve_cache_size < 1 or integration_cache_size < 1:
            raise ValueError("cache sizes must be positive")
        if not math.isfinite(proposal_guard_sd) or proposal_guard_sd <= 0.0:
            raise ValueError("proposal_guard_sd must be finite and positive")
        self.proposal_guard_sd = float(proposal_guard_sd)
        if not math.isfinite(series_error_tolerance) or series_error_tolerance <= 0.0:
            raise ValueError("series_error_tolerance must be finite and positive")
        self.series_error_tolerance = float(series_error_tolerance)
        if evaluator_factory is None:
            bank_bound = likelihood.series_remainder_bound(
                data.bank.max_x, order=data.bank.series_order
            )
            if bank_bound > self.series_error_tolerance:
                raise ValueError(
                    "compressed bank max_x is unsupported by its series order: "
                    f"remainder bound {bank_bound:g} exceeds {self.series_error_tolerance:g}"
                )
        try:
            self._k_factor = cho_factor(data.covariance, lower=True, check_finite=True)
        except np.linalg.LinAlgError as exc:
            raise ValueError(f"covariance is not positive definite: {exc}") from exc
        n = len(data.exposure)
        self._identity = np.eye(n)
        self._k_inverse = cho_solve(self._k_factor, self._identity, check_finite=True)
        self._logdet_k = float(2.0 * np.log(np.diag(self._k_factor[0])).sum())
        self._k_cholesky = np.tril(self._k_factor[0]).copy()
        self._curve_builder = curve_builder
        self._curve_cache_size = int(curve_cache_size)
        self._integration_cache_size = int(integration_cache_size)
        self._predator_emissions = (
            data.observed.predator_emissions
            if data.observed.predator_emissions is not None
            else likelihood._predator_emissions(
                data.observed.predator_counts,
                observed=data.observed.predator_observed,
            )
        )
        self._prey_emission_cache: OrderedDict[float, tuple[FloatArray, FloatArray]] = (
            OrderedDict()
        )
        self.curve_cache: OrderedDict[tuple[float, float], SiteEvaluator] = OrderedDict()
        self._integration_cache: OrderedDict[
            float, tuple[likelihood.PreInvasionIntegration, ...]
        ] = OrderedDict()
        self.stats: dict[str, float | int] = {
            "curve_builds": 0,
            "curve_seconds": 0.0,
            "mode_calls": 0,
            "mode_branches": 0,
            "mode_newton_first_successes": 0,
            "mode_newton_first_fallbacks": 0,
            "mode_newton_first_fallback_non_pd": 0,
            "mode_newton_first_fallback_line_search": 0,
            "mode_newton_first_fallback_exhausted": 0,
            "mode_newton_first_fallback_numerical": 0,
            "mode_newton_first_evaluations": 0,
            "mode_newton_first_accepted_steps": 0,
            "mode_newton_first_bounded_steps": 0,
            "mode_newton_first_polish_attempts": 0,
            "mode_newton_first_polish_acceptances": 0,
            "mode_lbfgs_fallback_evaluations": 0,
            "pd_failures": 0,
            "curve_cache_evictions": 0,
            "integration_cache_evictions": 0,
        }

    @property
    def site_count(self) -> int:
        return len(self.data.exposure)

    def _integrations(self, h: float) -> tuple[likelihood.PreInvasionIntegration, ...]:
        key = float(h)
        cached = self._integration_cache.get(key)
        if cached is not None:
            self._integration_cache.move_to_end(key)
            return cached
        rows: list[likelihood.PreInvasionIntegration] = []
        for log_hazard in self.grid:
            hazards = np.full(self.site_count, math.exp(float(log_hazard)))
            exact = 10.0 * float(hazards.max()) * (h - 1.0) > (self.data.bank.max_x * (1.0 + 1e-14))
            if exact and self.data.bank.bank_arrivals.shape != (
                self.data.bank.bank_size,
                self.site_count,
            ):
                raise ValueError(
                    "exact integration outside compressed-bank support requires the raw "
                    "arrival bank"
                )
            integration = likelihood.build_integration(
                self.data.bank,
                [h],
                hazards,
                prey_times=self.data.observed.prey_times,
                cohort_start=self.data.observed.cohort_start,
                exact=exact,
                enforce_domain=not exact,
            )
            if integration.series_bound > self.series_error_tolerance:
                raise FloatingPointError(
                    f"series remainder bound {integration.series_bound:g} exceeds "
                    f"{self.series_error_tolerance:g}"
                )
            rows.append(integration)
        result = tuple(rows)
        self._integration_cache[key] = result
        if len(self._integration_cache) > self._integration_cache_size:
            self._integration_cache.popitem(last=False)
            self.stats["integration_cache_evictions"] = (
                int(self.stats["integration_cache_evictions"]) + 1
            )
        return result

    def _prey_emissions(self, detection_sd: float) -> tuple[FloatArray, FloatArray]:
        """Return initial-state-adjusted emissions, computed once per exact SD key."""
        key = float(detection_sd)
        cached = self._prey_emission_cache.get(key)
        if cached is not None:
            self._prey_emission_cache.move_to_end(key)
            return cached
        events, alive = likelihood._prey_emissions(
            self.data.observed.prey_counts,
            MEAN_DETECTION,
            key,
        )
        likelihood._apply_initial_state(
            events,
            alive,
            self.data.observed.prey_counts,
            self.data.observed.initial_alive,
        )
        result = (events, alive)
        self._prey_emission_cache[key] = result
        if len(self._prey_emission_cache) > self._curve_cache_size:
            self._prey_emission_cache.popitem(last=False)
        return result

    def _score_integrations(
        self,
        integrations: Sequence[likelihood.PreInvasionIntegration],
        detection_sd: float,
        *,
        chunk_size: int = 32,
    ) -> FloatArray:
        """Score every grid integration in bounded vectorized chunks."""
        if chunk_size < 1:
            raise ValueError("chunk_size must be positive")
        events, alive = self._prey_emissions(detection_sd)
        pred = self._predator_emissions
        values = np.empty((self.site_count, len(integrations)), dtype=np.float64)
        for start in range(0, len(integrations), chunk_size):
            stop = min(start + chunk_size, len(integrations))
            moments = np.stack(
                [row.survival_moments[0] for row in integrations[start:stop]],
                axis=0,
            )
            weighted = np.einsum("gstc,nsc->gnst", moments, pred, optimize=True)
            event_probability = np.einsum(
                "gnst,nst->gns",
                weighted[:, :, :, :-1] - weighted[:, :, :, 1:],
                events,
                optimize=True,
            )
            event_probability += weighted[:, :, :, -1] * alive[None, :, :]
            if not np.isfinite(event_probability).all() or (event_probability <= 0).any():
                raise RuntimeError("pre-invasion likelihood produced invalid probabilities")
            values[:, start:stop] = np.log(event_probability[:, 0, :]).T
        return values

    def curves(self, h: float, detection_sd: float) -> SiteEvaluator:
        """Return exactly-keyed cached site curves for ``(h, detection_sd)``."""
        if not math.isfinite(h) or not 1.0 <= h <= 30.0:
            raise ValueError("h must be finite and in [1, 30]")
        if (
            not math.isfinite(detection_sd)
            or detection_sd < 0.0
            or detection_sd >= DETECTION_SD_MAX
        ):
            raise ValueError("detection_sd must be in its open admissible upper bound")
        key = (float(h), float(detection_sd))
        cached = self.curve_cache.get(key)
        if cached is not None:
            self.curve_cache.move_to_end(key)
            return cached
        started = time.perf_counter()
        if self._evaluator_factory is not None:
            result = self._evaluator_factory(float(h), float(detection_sd))
            lower, upper = result.numerical_domain
            if math.isnan(lower) or math.isnan(upper) or lower >= upper:
                raise ValueError("direct evaluator numerical domain must be increasing")
            self.curve_cache[key] = result
            if len(self.curve_cache) > self._curve_cache_size:
                self.curve_cache.popitem(last=False)
                self.stats["curve_cache_evictions"] = int(self.stats["curve_cache_evictions"]) + 1
            self.stats["curve_builds"] = int(self.stats["curve_builds"]) + 1
            self.stats["curve_seconds"] = (
                float(self.stats["curve_seconds"]) + time.perf_counter() - started
            )
            return result
        if self._curve_builder is not None:
            values = self._curve_builder(float(h), float(detection_sd), self.grid.copy())
            exact_nodes: tuple[int, ...] = ()
            max_bound = 0.0
        else:
            integrations = self._integrations(float(h))
            values = self._score_integrations(integrations, float(detection_sd))
            exact_nodes = tuple(
                index for index, integration in enumerate(integrations) if integration.exact
            )
            max_bound = max(
                (float(integration.series_bound) for integration in integrations), default=0.0
            )
        elapsed = time.perf_counter() - started
        result = SiteCurves.from_values(
            self.grid,
            values,
            h=float(h),
            detection_sd=float(detection_sd),
            build_seconds=elapsed,
            exact_nodes=exact_nodes,
            max_series_bound=max_bound,
        )
        self.curve_cache[key] = result
        if len(self.curve_cache) > self._curve_cache_size:
            self.curve_cache.popitem(last=False)
            self.stats["curve_cache_evictions"] = int(self.stats["curve_cache_evictions"]) + 1
        self.stats["curve_builds"] = int(self.stats["curve_builds"]) + 1
        self.stats["curve_seconds"] = float(self.stats["curve_seconds"]) + elapsed
        return result

    def _mode_branch(
        self,
        eta0: FloatArray,
        precision: FloatArray,
        curves: SiteEvaluator,
        start: FloatArray,
    ) -> tuple[FloatArray, float, float, float, float, int, int, str] | None:
        lower = curves.numerical_domain[0] - eta0 + 1e-10
        upper = curves.numerical_domain[1] - eta0 - 1e-10
        point = np.clip(np.asarray(start, dtype=np.float64), lower, upper)
        evaluation_count = 0

        def evaluate_at(u: FloatArray) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
            nonlocal evaluation_count
            evaluation_count += 1
            return curves.evaluate(eta0 + u)

        def objective(u: FloatArray) -> tuple[float, FloatArray]:
            ell, score, _, _ = evaluate_at(u)
            gradient = score - precision @ u
            value = float(np.sum(ell) - 0.5 * u @ precision @ u)
            return -value, -gradient

        def stationary_metrics(
            u: FloatArray,
            gradient: FloatArray,
            curvature: FloatArray,
        ) -> tuple[FloatArray, float, float, float, bool]:
            hessian = precision - np.diag(curvature)
            factor = cho_factor(hessian, lower=True, check_finite=True)
            step = cho_solve(factor, gradient, check_finite=True)
            score_inf = float(np.max(np.abs(gradient)))
            step_inf = float(np.max(np.abs(step)))
            decrement = math.sqrt(max(float(np.dot(gradient, step)), 0.0))
            numerically_stationary = bool(
                score_inf <= 10.0 * self.mode_tolerance
                and step_inf
                <= self.mode_tolerance * max(1.0, float(np.max(np.abs(u))))
                and decrement <= self.mode_tolerance
            )
            success = bool(score_inf <= self.mode_tolerance or numerically_stationary)
            return step, score_inf, step_inf, decrement, success

        def newton_first(
            initial: FloatArray,
        ) -> tuple[
            tuple[FloatArray, float, float, float, float, int, int, str] | None,
            str | None,
            int,
        ]:
            started_evaluations = evaluation_count
            u = np.array(initial, dtype=np.float64, copy=True)
            accepted_steps = 0

            def converged_result(
                ell: FloatArray,
                step: FloatArray,
                score_inf: float,
                step_inf: float,
                decrement: float,
            ) -> tuple[FloatArray, float, float, float, float, int, int, str]:
                nonlocal accepted_steps
                value = float(np.sum(ell) - 0.5 * u @ precision @ u)
                message = (
                    "Newton-first converged"
                    if score_inf <= self.mode_tolerance
                    else "Newton-first met numerical stationarity"
                )
                self.stats["mode_newton_first_polish_attempts"] = int(
                    self.stats["mode_newton_first_polish_attempts"]
                ) + 1
                direction = step / max(1.0, step_inf)
                if step_inf > 1.0:
                    self.stats["mode_newton_first_bounded_steps"] = int(
                        self.stats["mode_newton_first_bounded_steps"]
                    ) + 1
                candidate = u + direction
                if np.all(candidate > lower) and np.all(candidate < upper):
                    try:
                        candidate_ell, candidate_score, candidate_curvature, _ = evaluate_at(
                            candidate
                        )
                        candidate_gradient = candidate_score - precision @ candidate
                        (
                            _,
                            candidate_score_inf,
                            candidate_step_inf,
                            candidate_decrement,
                            candidate_converged,
                        ) = stationary_metrics(
                            candidate, candidate_gradient, candidate_curvature
                        )
                        candidate_value = float(
                            np.sum(candidate_ell) - 0.5 * candidate @ precision @ candidate
                        )
                        objective_slack = 64.0 * np.finfo(np.float64).eps * max(
                            1.0, abs(value), abs(candidate_value)
                        )
                        if (
                            candidate_value >= value - objective_slack
                            and candidate_score_inf < score_inf
                            and candidate_converged
                        ):
                            accepted_steps += 1
                            self.stats["mode_newton_first_polish_acceptances"] = int(
                                self.stats["mode_newton_first_polish_acceptances"]
                            ) + 1
                            return (
                                candidate,
                                candidate_value,
                                candidate_score_inf,
                                candidate_step_inf,
                                candidate_decrement,
                                accepted_steps,
                                evaluation_count - started_evaluations,
                                f"{message}; guarded polish accepted",
                            )
                    except (
                        CurveDomainError,
                        FloatingPointError,
                        np.linalg.LinAlgError,
                        ValueError,
                    ):
                        pass
                return (
                    u,
                    value,
                    score_inf,
                    step_inf,
                    decrement,
                    accepted_steps,
                    evaluation_count - started_evaluations,
                    f"{message}; valid incumbent retained",
                )

            try:
                for _ in range(12):
                    ell, score, curvature, _ = evaluate_at(u)
                    gradient = score - precision @ u
                    try:
                        step, score_inf, step_inf, decrement, converged = stationary_metrics(
                            u, gradient, curvature
                        )
                    except np.linalg.LinAlgError:
                        return None, "non_pd", accepted_steps
                    if converged:
                        result = converged_result(
                            ell,
                            step,
                            score_inf,
                            step_inf,
                            decrement,
                        )
                        return result, None, accepted_steps
                    current = float(np.sum(ell) - 0.5 * u @ precision @ u)
                    direction = step / max(1.0, step_inf)
                    if step_inf > 1.0:
                        self.stats["mode_newton_first_bounded_steps"] = int(
                            self.stats["mode_newton_first_bounded_steps"]
                        ) + 1
                    scale = 1.0
                    accepted = False
                    while scale >= 2.0**-14:
                        candidate = u + scale * direction
                        if np.all(candidate > lower) and np.all(candidate < upper):
                            candidate_ell, candidate_score, _, _ = evaluate_at(candidate)
                            candidate_value = float(
                                np.sum(candidate_ell)
                                - 0.5 * candidate @ precision @ candidate
                            )
                            candidate_residual = float(
                                np.max(np.abs(candidate_score - precision @ candidate))
                            )
                            objective_slack = 64.0 * np.finfo(np.float64).eps * max(
                                1.0, abs(current), abs(candidate_value)
                            )
                            if candidate_value >= current - objective_slack and (
                                candidate_value >= current or candidate_residual < score_inf
                            ):
                                u = candidate
                                accepted = True
                                accepted_steps += 1
                                break
                        scale *= 0.5
                    if not accepted:
                        return None, "line_search", accepted_steps
                ell, score, curvature, _ = evaluate_at(u)
                gradient = score - precision @ u
                try:
                    step, score_inf, step_inf, decrement, converged = stationary_metrics(
                        u, gradient, curvature
                    )
                except np.linalg.LinAlgError:
                    return None, "non_pd", accepted_steps
                if converged:
                    result = converged_result(
                        ell,
                        step,
                        score_inf,
                        step_inf,
                        decrement,
                    )
                    return result, None, accepted_steps
                return None, "exhausted", accepted_steps
            except (CurveDomainError, FloatingPointError, ValueError):
                return None, "numerical", accepted_steps

        newton_started = evaluation_count
        fast, fallback_reason, accepted_steps = newton_first(point)
        newton_evaluations = evaluation_count - newton_started
        self.stats["mode_newton_first_evaluations"] = int(
            self.stats["mode_newton_first_evaluations"]
        ) + newton_evaluations
        self.stats["mode_newton_first_accepted_steps"] = int(
            self.stats["mode_newton_first_accepted_steps"]
        ) + accepted_steps
        if fast is not None:
            self.stats["mode_newton_first_successes"] = int(
                self.stats["mode_newton_first_successes"]
            ) + 1
            return fast
        assert fallback_reason is not None
        self.stats["mode_newton_first_fallbacks"] = int(
            self.stats["mode_newton_first_fallbacks"]
        ) + 1
        fallback_key = f"mode_newton_first_fallback_{fallback_reason}"
        self.stats[fallback_key] = int(self.stats[fallback_key]) + 1

        fallback_started = evaluation_count
        try:
            fit = minimize(
                objective,
                point,
                jac=True,
                method="L-BFGS-B",
                bounds=list(zip(lower, upper, strict=True)),
                options={"maxiter": 100, "ftol": 1e-12, "gtol": 1e-8, "maxls": 30},
            )
            u = np.asarray(fit.x, dtype=np.float64)
            newton_iterations = 0
            for _ in range(12):
                ell, score, curvature, _ = evaluate_at(u)
                gradient = score - precision @ u
                score_inf = float(np.max(np.abs(gradient)))
                if score_inf <= self.mode_tolerance:
                    break
                hessian = precision - np.diag(curvature)
                factor = cho_factor(hessian, lower=True, check_finite=True)
                step = cho_solve(factor, gradient, check_finite=True)
                step_inf = float(np.max(np.abs(step)))
                decrement = math.sqrt(max(float(np.dot(gradient, step)), 0.0))
                numerically_stationary = bool(
                    score_inf <= 10.0 * self.mode_tolerance
                    and step_inf <= self.mode_tolerance * max(1.0, float(np.max(np.abs(u))))
                    and decrement <= self.mode_tolerance
                )
                current = float(np.sum(ell) - 0.5 * u @ precision @ u)
                scale = 1.0
                accepted = False
                while scale >= 2.0**-14:
                    candidate = u + scale * step
                    if np.all(candidate > lower) and np.all(candidate < upper):
                        candidate_ell, candidate_score, _, _ = evaluate_at(candidate)
                        candidate_value = float(
                            np.sum(candidate_ell) - 0.5 * candidate @ precision @ candidate
                        )
                        candidate_residual = float(
                            np.max(np.abs(candidate_score - precision @ candidate))
                        )
                        objective_slack = 64.0 * np.finfo(np.float64).eps * max(
                            1.0, abs(current), abs(candidate_value)
                        )
                        if candidate_value >= current - objective_slack and (
                            candidate_value >= current or candidate_residual < score_inf
                        ):
                            u = candidate
                            accepted = True
                            break
                    scale *= 0.5
                if not accepted:
                    if numerically_stationary:
                        break
                    return None
                newton_iterations += 1
            ell, score, _, _ = evaluate_at(u)
            gradient = score - precision @ u
            _, _, curvature, _ = evaluate_at(u)
            hessian = precision - np.diag(curvature)
            factor = cho_factor(hessian, lower=True, check_finite=True)
            final_step = cho_solve(factor, gradient, check_finite=True)
            step_inf = float(np.max(np.abs(final_step)))
            decrement = math.sqrt(max(float(np.dot(gradient, final_step)), 0.0))
            value = float(np.sum(ell) - 0.5 * u @ precision @ u)
            return (
                u,
                value,
                float(np.max(np.abs(gradient))),
                step_inf,
                decrement,
                int(fit.nit) + newton_iterations,
                evaluation_count,
                str(fit.message),
            )
        except (CurveDomainError, FloatingPointError, np.linalg.LinAlgError, ValueError):
            return None
        finally:
            self.stats["mode_lbfgs_fallback_evaluations"] = int(
                self.stats["mode_lbfgs_fallback_evaluations"]
            ) + (evaluation_count - fallback_started)

    def mode(
        self,
        alpha: float,
        beta: float,
        log_sigma: float,
        h: float,
        detection_sd: float,
        *,
        mode_start: NDArray[Any] | None = None,
    ) -> ModeResult:
        """Solve the latent mode from a fixed zero branch and any warm branch."""
        self.stats["mode_calls"] = int(self.stats["mode_calls"]) + 1
        sigma = math.exp(float(log_sigma))
        if not math.isfinite(sigma) or sigma <= 0.0:
            raise ValueError("log_sigma must map to a finite positive variance scale")
        curves = self.curves(h, detection_sd)
        eta0 = float(alpha) + float(beta) * self.data.exposure
        precision = self._k_inverse / (sigma * sigma)
        starts = [np.zeros(self.site_count, dtype=np.float64)]
        if mode_start is not None:
            warm = np.asarray(mode_start, dtype=np.float64)
            if warm.shape != (self.site_count,) or not np.isfinite(warm).all():
                raise ValueError("mode_start must be finite with one value per site")
            if not np.array_equal(warm, starts[0]):
                starts.append(warm)
        branches = [
            branch
            for start in starts
            if (branch := self._mode_branch(eta0, precision, curves, start)) is not None
        ]
        self.stats["mode_branches"] = int(self.stats["mode_branches"]) + len(starts)
        if not branches:
            return ModeResult(
                np.zeros(self.site_count),
                eta0,
                -math.inf,
                math.inf,
                False,
                "all deterministic mode branches failed",
                0,
                0,
                len(starts),
                None,
                precision,
                None,
            )
        u, value, score_inf, step_inf, decrement, iterations, evaluations, message = max(
            branches, key=lambda item: item[1]
        )
        eta = eta0 + u
        _, _, curvature, _ = curves.evaluate(eta)
        hessian = precision - np.diag(curvature)
        try:
            hessian_factor = cho_factor(hessian, lower=True, check_finite=True)
            hessian_inverse = cho_solve(hessian_factor, self._identity, check_finite=True)
            logdet_h = float(2.0 * np.log(np.diag(hessian_factor[0])).sum())
            c_cholesky = sigma * self._k_cholesky
            combined = self._identity - c_cholesky.T @ (curvature[:, None] * c_cholesky)
            combined_factor = cho_factor(combined, lower=True, check_finite=True)
            logdet_combined = float(2.0 * np.log(np.diag(combined_factor[0])).sum())
        except np.linalg.LinAlgError as exc:
            self.stats["pd_failures"] = int(self.stats["pd_failures"]) + 1
            return ModeResult(
                u,
                eta,
                value,
                score_inf,
                False,
                f"Laplace Hessian is not positive definite: {exc}",
                iterations,
                evaluations,
                len(starts),
                hessian,
                precision,
                None,
            )
        logdet_c = 2.0 * self.site_count * math.log(sigma) + self._logdet_k
        bound_touch = bool(
            np.any(eta <= curves.numerical_domain[0] + 1e-8)
            or np.any(eta >= curves.numerical_domain[1] - 1e-8)
        )
        marginal_sd = np.sqrt(np.maximum(np.diag(hessian_inverse), 0.0))
        proposal_eta_min = float(np.min(eta - self.proposal_guard_sd * marginal_sd))
        proposal_eta_max = float(np.max(eta + self.proposal_guard_sd * marginal_sd))
        proposal_grid_supported = bool(
            proposal_eta_min >= curves.numerical_domain[0]
            and proposal_eta_max <= curves.numerical_domain[1]
        )
        numerically_stationary = bool(
            score_inf <= 10.0 * self.mode_tolerance
            and step_inf <= self.mode_tolerance * max(1.0, float(np.max(np.abs(u))))
            and decrement <= self.mode_tolerance
        )
        success = bool(
            (score_inf <= self.mode_tolerance or numerically_stationary)
            and not bound_touch
            and proposal_grid_supported
        )
        if bound_touch:
            message = "latent mode touched the evaluated curve-grid boundary"
        elif not proposal_grid_supported:
            message = (
                f"{self.proposal_guard_sd:g}-SD Laplace proposal range "
                f"[{proposal_eta_min:g}, {proposal_eta_max:g}] is outside the fixed curve grid "
                f"[{curves.numerical_domain[0]:g}, {curves.numerical_domain[1]:g}]"
            )
        elif score_inf > self.mode_tolerance and not numerically_stationary:
            message = f"latent mode score {score_inf:g} exceeds tolerance"
        elif score_inf > self.mode_tolerance:
            message = (
                "latent mode met Newton-step stationarity at floating-point precision "
                f"(raw score {score_inf:g})"
            )
        return ModeResult(
            u,
            eta,
            value,
            score_inf,
            success,
            message,
            iterations,
            evaluations,
            len(starts),
            hessian,
            precision,
            hessian_inverse,
            logdet_c,
            logdet_h,
            logdet_combined,
            bound_touch,
            proposal_eta_min,
            proposal_eta_max,
            proposal_grid_supported,
            step_inf,
            decrement,
        )

    @staticmethod
    def _invalid(
        parameters: FloatArray,
        *,
        sigma_zero: bool,
        h: float,
        detection_sd: float,
        message: str,
        mode: ModeResult | None = None,
    ) -> CriterionEvaluation:
        gradient = np.full(len(parameters), np.nan)
        return CriterionEvaluation(
            -math.inf,
            math.inf,
            gradient,
            gradient.copy(),
            False,
            message,
            sigma_zero,
            mode,
            parameters.copy(),
            h,
            detection_sd,
        )

    def _unpack(
        self, parameters: NDArray[Any], fixed_h: float | None, sigma_zero: bool
    ) -> tuple[FloatArray, float, float]:
        point = np.asarray(parameters, dtype=np.float64)
        expected = (4 if sigma_zero else 5) if fixed_h is None else (3 if sigma_zero else 4)
        if point.shape != (expected,) or not np.isfinite(point).all():
            raise ValueError(f"parameters must be a finite vector of length {expected}")
        if fixed_h is None:
            h_index = 2 if sigma_zero else 3
            h = math.exp(float(point[h_index]))
            detection_sd = float(point[-1])
        else:
            h = float(fixed_h)
            detection_sd = float(point[-1])
        return point, h, detection_sd

    def evaluate_positive(
        self,
        parameters: NDArray[Any],
        fixed_h: float | None = None,
        *,
        mode_start: NDArray[Any] | None = None,
        nuisance_fd: bool = False,
        fd_step: float = 1e-4,
    ) -> CriterionEvaluation:
        """Evaluate the positive-variance family and its analytic core gradient."""
        point, h, detection_sd = self._unpack(parameters, fixed_h, False)
        if not 1.0 <= h <= 30.0 or not 0.0 <= detection_sd < DETECTION_SD_MAX:
            return self._invalid(
                point,
                sigma_zero=False,
                h=h,
                detection_sd=detection_sd,
                message="h or detection_sd lies outside the fitted domain",
            )
        mode = self.mode(
            float(point[0]),
            float(point[1]),
            float(point[2]),
            h,
            detection_sd,
            mode_start=mode_start,
        )
        if (
            not mode.success
            or mode.precision is None
            or mode.hessian is None
            or mode.hessian_inverse is None
        ):
            return self._invalid(
                point,
                sigma_zero=False,
                h=h,
                detection_sd=detection_sd,
                message=mode.message,
                mode=mode,
            )
        curves = self.curves(h, detection_sd)
        ell, score, curvature, third = curves.evaluate(mode.eta)
        precision = mode.precision
        hessian = mode.hessian
        hessian_factor = cho_factor(hessian, lower=True, check_finite=True)
        exposure = self.data.exposure
        du_alpha = cho_solve(hessian_factor, curvature, check_finite=True)
        du_beta = cho_solve(hessian_factor, curvature * exposure, check_finite=True)
        du_log_sigma = cho_solve(hessian_factor, 2.0 * (precision @ mode.u), check_finite=True)
        hessian_inverse_diagonal = np.diag(mode.hessian_inverse)
        alpha_gradient = float(
            np.sum(score) + 0.5 * np.dot(hessian_inverse_diagonal, third * (1.0 + du_alpha))
        )
        beta_gradient = float(
            np.dot(exposure, score)
            + 0.5 * np.dot(hessian_inverse_diagonal, third * (exposure + du_beta))
        )
        quadratic = float(mode.u @ precision @ mode.u)
        log_sigma_gradient = float(
            quadratic
            + np.dot(hessian_inverse_diagonal, curvature)
            + 0.5 * np.dot(hessian_inverse_diagonal, third * du_log_sigma)
        )
        criterion = float(np.sum(ell) - 0.5 * quadratic - 0.5 * mode.logdet_combined)
        gradient = np.zeros(len(point), dtype=np.float64)
        gradient[:3] = (alpha_gradient, beta_gradient, log_sigma_gradient)
        result = CriterionEvaluation(
            criterion,
            -criterion,
            gradient,
            -gradient,
            True,
            "ok",
            False,
            mode,
            point.copy(),
            h,
            detection_sd,
        )
        if nuisance_fd:
            result = self._with_nuisance_fd(result, fixed_h=fixed_h, fd_step=fd_step)
        return result

    def evaluate_sigma_zero(
        self,
        parameters: NDArray[Any],
        fixed_h: float | None = None,
        *,
        nuisance_fd: bool = False,
        fd_step: float = 1e-4,
    ) -> CriterionEvaluation:
        """Evaluate the exact lower-dimensional sigma=0 family."""
        point, h, detection_sd = self._unpack(parameters, fixed_h, True)
        if not 1.0 <= h <= 30.0 or not 0.0 <= detection_sd < DETECTION_SD_MAX:
            return self._invalid(
                point,
                sigma_zero=True,
                h=h,
                detection_sd=detection_sd,
                message="h or detection_sd lies outside the fitted domain",
            )
        curves = self.curves(h, detection_sd)
        eta = float(point[0]) + float(point[1]) * self.data.exposure
        try:
            ell, score, _, _ = curves.evaluate(eta)
        except CurveDomainError as exc:
            return self._invalid(
                point,
                sigma_zero=True,
                h=h,
                detection_sd=detection_sd,
                message=str(exc),
            )
        criterion = float(np.sum(ell))
        gradient = np.zeros(len(point), dtype=np.float64)
        gradient[0] = float(np.sum(score))
        gradient[1] = float(np.dot(self.data.exposure, score))
        result = CriterionEvaluation(
            criterion,
            -criterion,
            gradient,
            -gradient,
            True,
            "ok",
            True,
            None,
            point.copy(),
            h,
            detection_sd,
        )
        if nuisance_fd:
            result = self._with_nuisance_fd(result, fixed_h=fixed_h, fd_step=fd_step)
        return result

    def _with_nuisance_fd(
        self,
        base: CriterionEvaluation,
        *,
        fixed_h: float | None,
        fd_step: float,
    ) -> CriterionEvaluation:
        if not math.isfinite(fd_step) or fd_step <= 0.0:
            raise ValueError("fd_step must be finite and positive")
        gradient = base.criterion_gradient.copy()
        indices = [len(gradient) - 1]
        if fixed_h is None:
            indices.insert(0, len(gradient) - 2)

        def evaluate(candidate: FloatArray) -> CriterionEvaluation:
            if base.sigma_zero:
                return self.evaluate_sigma_zero(candidate, fixed_h=fixed_h)
            mode_start = base.mode.u if base.mode is not None else None
            return self.evaluate_positive(candidate, fixed_h=fixed_h, mode_start=mode_start)

        for index in indices:
            delta = fd_step * max(1.0, abs(float(base.parameters[index])))
            lower, upper = self._bounds(fixed_h, base.sigma_zero)[index]
            minus = base.parameters.copy()
            plus = base.parameters.copy()
            can_minus = minus[index] - delta >= lower
            can_plus = plus[index] + delta <= upper
            if can_minus and can_plus:
                minus[index] -= delta
                plus[index] += delta
                vm = evaluate(minus).criterion
                vp = evaluate(plus).criterion
                value = (vp - vm) / (2.0 * delta)
            elif can_plus:
                plus[index] += delta
                vp = evaluate(plus).criterion
                value = (vp - base.criterion) / delta
            elif can_minus:
                minus[index] -= delta
                vm = evaluate(minus).criterion
                value = (base.criterion - vm) / delta
            else:
                value = math.nan
            gradient[index] = value
        success = bool(base.success and np.isfinite(gradient).all())
        return CriterionEvaluation(
            base.criterion,
            base.objective,
            gradient,
            -gradient,
            success,
            "ok" if success else "nuisance finite difference failed",
            base.sigma_zero,
            base.mode,
            base.parameters,
            base.h,
            base.detection_sd,
        )

    @staticmethod
    def _bounds(fixed_h: float | None, sigma_zero: bool) -> tuple[tuple[float, float], ...]:
        common = [(-12.0, -3.0), (-2.0, 2.0)]
        if not sigma_zero:
            common.append((math.log(1e-4), math.log(2.0)))
        if fixed_h is None:
            common.append((0.0, math.log(30.0)))
        common.append((0.0, DETECTION_SD_MAX * (1.0 - 1e-10)))
        return tuple(common)

    @staticmethod
    def _projected_gradient_inf(
        gradient: FloatArray,
        point: FloatArray,
        bounds: Sequence[tuple[float, float]],
    ) -> float:
        projected = gradient.copy()
        for index, (coordinate, (lower, upper)) in enumerate(zip(point, bounds, strict=True)):
            tolerance = 1e-8 * max(1.0, abs(lower), abs(upper))
            if coordinate <= lower + tolerance:
                projected[index] = min(projected[index], 0.0)
            elif coordinate >= upper - tolerance:
                projected[index] = max(projected[index], 0.0)
        return float(np.max(np.abs(projected)))

    def _fit_family(
        self,
        *,
        fixed_h: float | None,
        sigma_zero: bool,
        starts: Sequence[NDArray[Any]],
        kkt_tolerance: float,
        maxiter: int,
        source_prefix: str,
    ) -> list[FitCandidate]:
        bounds = self._bounds(fixed_h, sigma_zero)
        family = "sigma_zero" if sigma_zero else "positive_sigma"
        candidates: list[FitCandidate] = []

        def evaluate(
            point: FloatArray,
            *,
            mode_start: FloatArray | None = None,
            nuisance_fd: bool = True,
        ) -> CriterionEvaluation:
            if sigma_zero:
                return self.evaluate_sigma_zero(point, fixed_h=fixed_h, nuisance_fd=nuisance_fd)
            return self.evaluate_positive(
                point,
                fixed_h=fixed_h,
                mode_start=mode_start,
                nuisance_fd=nuisance_fd,
            )

        def append_candidate(
            point: FloatArray,
            evaluation: CriterionEvaluation,
            *,
            source: str,
            result: OptimizeResult | None = None,
        ) -> FitCandidate:
            projected = (
                self._projected_gradient_inf(evaluation.objective_gradient, point, bounds)
                if evaluation.success
                else math.inf
            )
            row = FitCandidate(
                family,
                source,
                point.copy(),
                evaluation,
                bool(result.success) if result is not None else True,
                str(result.message) if result is not None else "retained incumbent",
                int(result.nit) if result is not None else 0,
                int(result.nfev) if result is not None else 1,
                projected,
                bool(evaluation.success and projected <= kkt_tolerance),
            )
            candidates.append(row)
            return row

        for start_index, raw_start in enumerate(starts):
            start = np.asarray(raw_start, dtype=np.float64)
            if start.shape != (len(bounds),):
                raise ValueError(f"{family} start has the wrong dimension")
            start = np.asarray(
                [
                    np.clip(value, lower, upper)
                    for value, (lower, upper) in zip(start, bounds, strict=True)
                ]
            )
            incumbent = evaluate(start)
            incumbent_row = append_candidate(
                start,
                incumbent,
                source=f"{source_prefix}_start_{start_index}",
            )

            last_mode: FloatArray | None = incumbent.mode.u if incumbent.mode is not None else None

            def fun(point: FloatArray) -> tuple[float, FloatArray]:
                nonlocal last_mode
                if not np.isfinite(point).all():
                    return 1e100, np.zeros_like(point)
                try:
                    value = evaluate(point, mode_start=last_mode)
                except (CurveDomainError, FloatingPointError, ValueError):
                    return 1e100, np.zeros_like(point)
                if (
                    not value.success
                    or not math.isfinite(value.objective)
                    or not np.isfinite(value.objective_gradient).all()
                ):
                    return 1e100, np.zeros_like(point)
                if not sigma_zero and value.mode is not None and value.success:
                    last_mode = value.mode.u
                return value.objective, value.objective_gradient

            fit: OptimizeResult = minimize(
                fun,
                start,
                jac=True,
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": maxiter, "ftol": 1e-12, "gtol": 2e-5, "maxls": 30},
            )
            final = evaluate(np.asarray(fit.x), mode_start=last_mode)
            fit_row = append_candidate(
                np.asarray(fit.x, dtype=np.float64),
                final,
                source=f"{source_prefix}_fit_{start_index}",
                result=fit,
            )
            if incumbent_row.eligible or fit_row.eligible:
                continue

            fallback_start = min(
                (incumbent_row, fit_row), key=lambda row: row.evaluation.objective
            ).parameters
            eligible_rows = [row for row in candidates if row.eligible]
            if eligible_rows:
                best_eligible = max(eligible_rows, key=lambda row: row.evaluation.criterion)
                unresolved_value = max(
                    incumbent_row.evaluation.criterion,
                    fit_row.evaluation.criterion,
                )
                if unresolved_value <= best_eligible.evaluation.criterion + 1e-6:
                    continue

            def scalar_fun(point: FloatArray) -> float:
                try:
                    value = evaluate(point, nuisance_fd=False)
                except (CurveDomainError, FloatingPointError, ValueError):
                    return 1e100
                return value.objective if value.success else 1e100

            fallback: OptimizeResult = minimize(
                scalar_fun,
                fallback_start,
                method="Powell",
                bounds=bounds,
                options={"maxiter": min(maxiter, 40), "xtol": 1e-5, "ftol": 1e-9},
            )
            fallback_evaluation = evaluate(np.asarray(fallback.x))
            fallback_row = append_candidate(
                np.asarray(fallback.x, dtype=np.float64),
                fallback_evaluation,
                source=f"{source_prefix}_powell_{start_index}",
                result=fallback,
            )
            if fallback_row.eligible:
                continue
            polish: OptimizeResult = minimize(
                fun,
                fallback.x,
                jac=True,
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": maxiter, "ftol": 1e-14, "gtol": 2e-5, "maxls": 40},
            )
            polish_evaluation = evaluate(np.asarray(polish.x), mode_start=last_mode)
            append_candidate(
                np.asarray(polish.x, dtype=np.float64),
                polish_evaluation,
                source=f"{source_prefix}_polish_{start_index}",
                result=polish,
            )
        return candidates

    @staticmethod
    def _best(candidates: Sequence[FitCandidate], family: str) -> FitCandidate | None:
        eligible = [row for row in candidates if row.family == family and row.eligible]
        return max(eligible, key=lambda row: row.evaluation.criterion, default=None)

    def fit_profile(
        self,
        *,
        fixed_h: float | None = None,
        profile_h_grid: Sequence[float] = DEFAULT_PROFILE_H_GRID,
        positive_starts: Sequence[NDArray[Any]] | None = None,
        sigma_zero_starts: Sequence[NDArray[Any]] | None = None,
        kkt_tolerance: float = 1e-3,
        maxiter: int = 80,
    ) -> ProfileFit:
        """Fit both families with bidirectional fixed-h sweeps and free-h polishing.

        The default 35-point log-spaced mesh is an initial profile search, not
        an endpoint certificate.  Callers must refine emerging maxima and any
        scientific cutoffs before treating a profile or likelihood ratio as
        numerically qualified.
        """
        started = time.perf_counter()
        if fixed_h is not None and not 1.0 <= fixed_h <= 30.0:
            raise ValueError("fixed_h must be in [1, 30]")
        if not math.isfinite(kkt_tolerance) or kkt_tolerance <= 0.0:
            raise ValueError("kkt_tolerance must be finite and positive")
        if maxiter < 1:
            raise ValueError("maxiter must be positive")
        if fixed_h is None:
            positive_default = np.array([-5.5, 0.4, math.log(0.35), math.log(3.0), 0.2])
            zero_default = np.array([-5.5, 0.4, math.log(3.0), 0.2])
        else:
            positive_default = np.array([-5.5, 0.4, math.log(0.35), 0.2])
            zero_default = np.array([-5.5, 0.4, 0.2])
        positive = list(positive_starts or (positive_default,))
        zero = list(sigma_zero_starts or (zero_default,))
        candidates: list[FitCandidate] = []

        if fixed_h is None:
            grid = tuple(float(value) for value in profile_h_grid)
            if (
                not grid
                or not np.isfinite(grid).all()
                or any(value < 1.0 or value > 30.0 for value in grid)
            ):
                raise ValueError("profile_h_grid must contain finite values in [1, 30]")
            fixed_positive_anchors = [
                np.delete(np.asarray(value, dtype=float), 3) for value in positive
            ]
            fixed_zero_anchors = [np.delete(np.asarray(value, dtype=float), 2) for value in zero]
            grid_positive: list[FitCandidate] = []
            grid_zero: list[FitCandidate] = []

            def unique_starts(rows: Sequence[FloatArray]) -> list[FloatArray]:
                result: list[FloatArray] = []
                for row in rows:
                    point = np.asarray(row, dtype=np.float64)
                    if not any(np.array_equal(point, existing) for existing in result):
                        result.append(point)
                return result

            for direction, sweep in (("up", grid), ("down", tuple(reversed(grid)))):
                propagated_positive: FloatArray | None = None
                propagated_zero: FloatArray | None = None
                for h in sweep:
                    p_starts = unique_starts(
                        [
                            *(() if propagated_positive is None else (propagated_positive,)),
                            *fixed_positive_anchors,
                        ]
                    )
                    z_starts = unique_starts(
                        [
                            *(() if propagated_zero is None else (propagated_zero,)),
                            *fixed_zero_anchors,
                        ]
                    )
                    p_rows = self._fit_family(
                        fixed_h=h,
                        sigma_zero=False,
                        starts=p_starts,
                        kkt_tolerance=kkt_tolerance,
                        maxiter=maxiter,
                        source_prefix=f"profile_{direction}_h_{h:g}",
                    )
                    z_rows = self._fit_family(
                        fixed_h=h,
                        sigma_zero=True,
                        starts=z_starts,
                        kkt_tolerance=kkt_tolerance,
                        maxiter=maxiter,
                        source_prefix=f"profile_{direction}_h_{h:g}",
                    )
                    candidates.extend(p_rows)
                    candidates.extend(z_rows)
                    best_p = self._best(p_rows, "positive_sigma")
                    best_z = self._best(z_rows, "sigma_zero")
                    if best_p is not None:
                        grid_positive.append(best_p)
                        propagated_positive = best_p.parameters
                    if best_z is not None:
                        grid_zero.append(best_z)
                        propagated_zero = best_z.parameters

            def profile_peaks(rows: Sequence[FitCandidate]) -> list[FitCandidate]:
                # Reconcile the two sweep directions at each exact mesh point,
                # then retain local/boundary maxima as free-h starts. Feeding
                # every mesh point to a full free optimization is redundant.
                by_h: dict[float, FitCandidate] = {}
                for row in rows:
                    h = row.evaluation.h
                    current = by_h.get(h)
                    if current is None or row.evaluation.criterion > current.evaluation.criterion:
                        by_h[h] = row
                ordered = [by_h[h] for h in sorted(by_h)]
                peaks: list[FitCandidate] = []
                for index, row in enumerate(ordered):
                    left = ordered[index - 1].evaluation.criterion if index else -math.inf
                    right = (
                        ordered[index + 1].evaluation.criterion
                        if index + 1 < len(ordered)
                        else -math.inf
                    )
                    if row.evaluation.criterion >= left and row.evaluation.criterion >= right:
                        peaks.append(row)
                return peaks

            # Every local or boundary profile maximum is a retained free-h
            # start. Bidirectional warm paths therefore cannot silently discard
            # a superior branch, without launching one free fit per mesh point.
            positive.extend(
                np.insert(row.parameters, 3, math.log(row.evaluation.h))
                for row in profile_peaks(grid_positive)
            )
            zero.extend(
                np.insert(row.parameters, 2, math.log(row.evaluation.h))
                for row in profile_peaks(grid_zero)
            )

        candidates.extend(
            self._fit_family(
                fixed_h=fixed_h,
                sigma_zero=False,
                starts=positive,
                kkt_tolerance=kkt_tolerance,
                maxiter=maxiter,
                source_prefix="free" if fixed_h is None else f"fixed_h_{fixed_h:g}",
            )
        )
        candidates.extend(
            self._fit_family(
                fixed_h=fixed_h,
                sigma_zero=True,
                starts=zero,
                kkt_tolerance=kkt_tolerance,
                maxiter=maxiter,
                source_prefix="free" if fixed_h is None else f"fixed_h_{fixed_h:g}",
            )
        )
        # Final endpoint selection only compares candidates in the requested
        # dimension; fixed-grid rows are evidence and starts, not free-h fits.
        endpoint_rows = [
            row for row in candidates if (fixed_h is not None or row.source.startswith("free"))
        ]
        best_positive = self._best(endpoint_rows, "positive_sigma")
        best_zero = self._best(endpoint_rows, "sigma_zero")
        resolved = best_positive is not None and best_zero is not None
        best = (
            max((best_positive, best_zero), key=lambda row: row.evaluation.criterion)
            if resolved and best_positive is not None and best_zero is not None
            else None
        )
        return ProfileFit(
            fixed_h,
            best,
            best_positive,
            best_zero,
            tuple(candidates),
            resolved,
            time.perf_counter() - started,
        )


__all__ = [
    "DEFAULT_GRID",
    "DEFAULT_PROFILE_H_GRID",
    "DETECTION_SD_MAX",
    "CriterionEvaluation",
    "CurveDomainError",
    "FitCandidate",
    "ModeResult",
    "ProfileFit",
    "SiteCurves",
    "SpatialProfileCriterion",
    "SpatialProfileData",
]
