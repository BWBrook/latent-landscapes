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
from dataclasses import dataclass, field, replace
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import CubicSpline  # type: ignore[import-untyped]
from scipy.linalg import cho_factor, cho_solve  # type: ignore[import-untyped]
from scipy.optimize import OptimizeResult  # type: ignore[import-untyped]

from latent_landscapes import preinvasion_likelihood as likelihood

FloatArray = NDArray[np.float64]
DEFAULT_GRID = np.linspace(-12.0, -2.0, 161)
DEFAULT_PROFILE_H_GRID = tuple(float(value) for value in np.geomspace(1.0, 30.0, 35))
MEAN_DETECTION = 0.65
DETECTION_SD_MAX = math.sqrt(MEAN_DETECTION * (1.0 - MEAN_DETECTION))
SIGMA_MAX = 1.5
LAPLACE_FLOOR = 0.1


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
    determinant_diagonal: FloatArray | None = field(default=None, repr=False)
    determinant_trace: float = math.nan
    combined_min_eigenvalue: float = math.nan
    inner_terminal_reason: str = ""
    invalid_trial_rejections: int = 0


@dataclass(frozen=True, slots=True)
class ModeBranchResult:
    """Latent solve state and terminal diagnostics, including unsuccessful solves."""

    u: FloatArray
    value: float
    score_inf: float
    step_inf: float
    decrement: float
    iterations: int
    evaluations: int
    terminal_reason: str
    invalid_trial_rejections: int
    detail: str = ""

    @property
    def success(self) -> bool:
        return self.terminal_reason == "converged"


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


def _floored_eigenvalues(eigenvalues: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Smoothly floor positive eigenvalues: f(x) = (x + tau exp(-x / tau)) / f1.

    f1 = 1 + tau exp(-1 / tau) normalises f(1) = 1, so the criterion tends
    exactly to the sigma = 0 family as sigma -> 0 (an unnormalised floor puts
    the positive family 2.3e-6 per site below it, beyond the tie tolerance at
    120 sites). f(0) ~ tau caps the Laplace determinant inflation at about
    log(1/tau) / 2 per latent direction; at x >= 0.89, the range seen at
    ordinary fits, f differs from x by less than 1.4e-5. Returns f and f'/f;
    the normalisation is a constant and leaves f'/f unchanged.
    """
    decay = np.exp(-eigenvalues / LAPLACE_FLOOR)
    raw = eigenvalues + LAPLACE_FLOOR * decay
    floored = raw / (1.0 + LAPLACE_FLOOR * math.exp(-1.0 / LAPLACE_FLOOR))
    return floored, (1.0 - decay) / raw


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
        decrement_tolerance: float = 1e-7,
        mode_max_iterations: int = 200,
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
        self.decrement_tolerance = float(decrement_tolerance)
        self.mode_max_iterations = int(mode_max_iterations)
        if not math.isfinite(self.decrement_tolerance) or self.decrement_tolerance <= 0.0:
            raise ValueError("decrement_tolerance must be finite and positive")
        if self.mode_max_iterations < 1:
            raise ValueError("mode_max_iterations must be positive")
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
        self._prey_emission_cache: OrderedDict[float, tuple[FloatArray, FloatArray]] = OrderedDict()
        self.curve_cache: OrderedDict[tuple[float, float], SiteEvaluator] = OrderedDict()
        self._integration_cache: OrderedDict[
            float, tuple[likelihood.PreInvasionIntegration, ...]
        ] = OrderedDict()
        self.stats: dict[str, float | int] = {
            "curve_builds": 0,
            "curve_seconds": 0.0,
            "mode_calls": 0,
            "mode_failures": 0,
            "mode_iterations": 0,
            "mode_evaluations": 0,
            "pd_failures": 0,
            "curve_cache_evictions": 0,
            "integration_cache_evictions": 0,
            "mode_invalid_trial_rejections": 0,
            "mode_branch_calls": 0,
            "mode_branch_invalid_trial_rejections": 0,
            "nuisance_site_evaluations": 0,
            "nuisance_site_seconds": 0.0,
            "nuisance_richardson_central": 0,
            "nuisance_richardson_one_sided": 0,
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
            self.data.observed.prey_observed,
        )
        likelihood._apply_initial_state(
            events,
            alive,
            self.data.observed.prey_counts,
            self.data.observed.initial_alive,
            self.data.observed.prey_observed,
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
    ) -> ModeBranchResult:
        """Maximise the joint latent objective with fixed-budget damped Newton.

        Initial-invalid states fail. Invalid trial evaluations retain the valid
        current state and use the same damping increase as other rejected steps.
        Strict gradient, decrement and positive-definiteness checks are unchanged.
        """
        lower = curves.numerical_domain[0] - eta0 + 1e-10
        upper = curves.numerical_domain[1] - eta0 - 1e-10
        u = np.clip(np.asarray(start, dtype=np.float64), lower, upper)
        identity = self._identity
        evaluations, invalid_trials, iterations = 0, 0, 0
        value, score_inf, step_inf, decrement = -math.inf, math.inf, math.inf, math.inf

        def finish(reason: str, detail: str = "") -> ModeBranchResult:
            self.stats["mode_branch_calls"] = int(self.stats["mode_branch_calls"]) + 1
            self.stats["mode_branch_invalid_trial_rejections"] = (
                int(self.stats["mode_branch_invalid_trial_rejections"]) + invalid_trials
            )
            reason_key = f"mode_branch_termination_{reason.replace('-', '_')}"
            self.stats[reason_key] = int(self.stats.get(reason_key, 0)) + 1
            if reason == "converged":
                histogram_key = f"mode_branch_converged_iterations_{iterations}"
                self.stats[histogram_key] = int(self.stats.get(histogram_key, 0)) + 1
                eta = eta0 + u
                if np.isfinite(eta).all():
                    self.stats["mode_eta_min"] = min(
                        float(self.stats.get("mode_eta_min", math.inf)), float(np.min(eta))
                    )
                    self.stats["mode_eta_max"] = max(
                        float(self.stats.get("mode_eta_max", -math.inf)), float(np.max(eta))
                    )
            final_score = score_inf if reason == "converged" else math.inf
            if reason not in {"converged", "initial-invalid"}:
                final_score = float(np.max(np.abs(score - precision @ u)))
            return ModeBranchResult(
                u.copy(),
                value,
                final_score,
                step_inf,
                decrement if reason == "converged" else math.inf,
                iterations,
                evaluations,
                reason,
                invalid_trials,
                detail,
            )

        try:
            evaluations += 1
            ell, score, curvature, _ = curves.evaluate(eta0 + u)
        except (CurveDomainError, FloatingPointError, ValueError) as exc:
            return finish("initial-invalid", str(exc))
        value = float(np.sum(ell) - 0.5 * u @ precision @ u)
        damping = 0.0
        for iteration in range(self.mode_max_iterations):
            iterations = iteration
            gradient = score - precision @ u
            hessian = precision - np.diag(curvature)
            score_inf = float(np.max(np.abs(gradient)))
            try:
                factor = cho_factor(hessian, lower=True, check_finite=True)
                newton = cho_solve(factor, gradient, check_finite=True)
                decrement = math.sqrt(max(float(gradient @ newton), 0.0))
                positive_definite = True
            except np.linalg.LinAlgError:
                newton, decrement, positive_definite = gradient, math.inf, False
            if (
                positive_definite
                and score_inf <= 10.0 * self.mode_tolerance
                and decrement <= self.decrement_tolerance
            ):
                step_inf = float(np.max(np.abs(newton)))
                return finish("converged", "damped Newton converged")
            while True:
                if damping == 0.0 and positive_definite:
                    step = newton
                    break
                try:
                    damped = cho_factor(hessian + damping * identity, lower=True)
                    step = cho_solve(damped, gradient, check_finite=True)
                    break
                except np.linalg.LinAlgError:
                    damping = max(1e-6, 10.0 * damping)
            step_inf = float(np.max(np.abs(step)))
            predicted = float(gradient @ step - 0.5 * step @ hessian @ step)
            candidate = u + step
            ratio = -1.0
            if np.all(candidate > lower) and np.all(candidate < upper):
                try:
                    evaluations += 1
                    c_ell, c_score, c_curvature, _ = curves.evaluate(eta0 + candidate)
                except (CurveDomainError, FloatingPointError, ValueError):
                    invalid_trials += 1
                else:
                    c_value = float(np.sum(c_ell) - 0.5 * candidate @ precision @ candidate)
                    if predicted > 0.0:
                        ratio = (c_value - value) / predicted
                    resolution = 64.0 * np.finfo(np.float64).eps * max(1.0, abs(value))
                    if (
                        damping == 0.0
                        and positive_definite
                        and predicted <= resolution
                        and c_value >= value - resolution
                    ):
                        # Below resolution, take the full Newton step and let
                        # the unchanged strict test decide at the next iterate.
                        ratio = 1.0
            else:
                invalid_trials += 1
            iterations = iteration + 1
            if ratio > 1e-4:
                u, value = candidate, c_value
                ell, score, curvature = c_ell, c_score, c_curvature
                damping = 0.0 if ratio > 0.75 else damping / 3.0
            else:
                scale = float(np.max(np.abs(np.diag(hessian))))
                damping = max(1e-3 * max(scale, 1.0), 10.0 * damping)
                if damping > 1e12 * max(scale, 1.0):
                    return finish("damping-limit")
        return finish("iteration-limit")

    def mode(
        self,
        alpha: float,
        beta: float,
        log_sigma: float,
        h: float,
        detection_sd: float,
    ) -> ModeResult:
        """Solve the latent mode deterministically from the zero start.

        The criterion is a function of the outer parameters, data, bank and
        evaluator settings only: there are no warm starts or path-dependent
        branches. Multimodality is audited separately at reported fits.
        """
        self.stats["mode_calls"] = int(self.stats["mode_calls"]) + 1
        sigma = math.exp(float(log_sigma))
        if not math.isfinite(sigma) or sigma <= 0.0:
            raise ValueError("log_sigma must map to a finite positive variance scale")
        curves = self.curves(h, detection_sd)
        eta0 = float(alpha) + float(beta) * self.data.exposure
        precision = self._k_inverse / (sigma * sigma)
        branch = self._mode_branch(eta0, precision, curves, np.zeros(self.site_count))
        self.stats["mode_iterations"] = int(self.stats["mode_iterations"]) + branch.iterations
        self.stats["mode_evaluations"] = int(self.stats["mode_evaluations"]) + branch.evaluations
        self.stats["mode_invalid_trial_rejections"] = (
            int(self.stats["mode_invalid_trial_rejections"]) + branch.invalid_trial_rejections
        )
        reason_key = f"mode_termination_{branch.terminal_reason.replace('-', '_')}"
        self.stats[reason_key] = int(self.stats.get(reason_key, 0)) + 1
        if branch.success:
            histogram_key = f"mode_converged_iterations_{branch.iterations}"
            self.stats[histogram_key] = int(self.stats.get(histogram_key, 0)) + 1
        if not branch.success:
            self.stats["mode_failures"] = int(self.stats["mode_failures"]) + 1
            return ModeResult(
                np.zeros(self.site_count),
                eta0,
                -math.inf,
                math.inf,
                False,
                f"latent mode failed: {branch.terminal_reason}"
                + (f": {branch.detail}" if branch.detail else ""),
                branch.iterations,
                branch.evaluations,
                1,
                None,
                precision,
                None,
                inner_terminal_reason=branch.terminal_reason,
                invalid_trial_rejections=branch.invalid_trial_rejections,
            )
        u, value, score_inf = branch.u, branch.value, branch.score_inf
        step_inf, decrement = branch.step_inf, branch.decrement
        iterations, evaluations, message = branch.iterations, branch.evaluations, branch.detail
        eta = eta0 + u
        _, _, curvature, _ = curves.evaluate(eta)
        hessian = precision - np.diag(curvature)
        try:
            hessian_factor = cho_factor(hessian, lower=True, check_finite=True)
            hessian_inverse = cho_solve(hessian_factor, self._identity, check_finite=True)
            logdet_h = float(2.0 * np.log(np.diag(hessian_factor[0])).sum())
            c_cholesky = sigma * self._k_cholesky
            combined = self._identity - c_cholesky.T @ (curvature[:, None] * c_cholesky)
            eigenvalues, eigenvectors = np.linalg.eigh(combined)
            if float(eigenvalues.min()) <= 0.0:
                raise np.linalg.LinAlgError("I - C'diag(ell'')C is not positive definite")
            floored, weights = _floored_eigenvalues(eigenvalues)
            logdet_combined = float(np.log(floored).sum())
            projected = c_cholesky @ eigenvectors
            determinant_diagonal = np.einsum("ij,j,ij->i", projected, weights, projected)
            determinant_trace = float(np.dot(weights, eigenvalues - 1.0))
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
                1,
                hessian,
                precision,
                None,
                inner_terminal_reason=branch.terminal_reason,
                invalid_trial_rejections=branch.invalid_trial_rejections,
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
        success = bool(not bound_touch and proposal_grid_supported)
        if bound_touch:
            message = "latent mode touched the evaluated curve-grid boundary"
        elif not proposal_grid_supported:
            message = (
                f"{self.proposal_guard_sd:g}-SD Laplace proposal range "
                f"[{proposal_eta_min:g}, {proposal_eta_max:g}] is outside the fixed curve grid "
                f"[{curves.numerical_domain[0]:g}, {curves.numerical_domain[1]:g}]"
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
            1,
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
            determinant_diagonal,
            determinant_trace,
            float(eigenvalues.min()),
            branch.terminal_reason,
            branch.invalid_trial_rejections,
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
            log_h = float(point[h_index])
            h = min(30.0, math.exp(log_h)) if 0.0 <= log_h <= math.log(30.0) else math.nan
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
        nuisance_fd: bool = False,
        fd_step: float = 1e-3,
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
        # With floored eigenvalues f(lambda_j) of M = I - C'diag(ell'')C, the
        # derivative of sum log f is sum_i dc_i G_ii with G = C V diag(f'/f) V'C';
        # without the floor G = H^-1, recovering standard Laplace.
        determinant_diagonal = mode.determinant_diagonal
        assert determinant_diagonal is not None
        alpha_gradient = float(
            np.sum(score) + 0.5 * np.dot(determinant_diagonal, third * (1.0 + du_alpha))
        )
        beta_gradient = float(
            np.dot(exposure, score)
            + 0.5 * np.dot(determinant_diagonal, third * (exposure + du_beta))
        )
        quadratic = float(mode.u @ precision @ mode.u)
        log_sigma_gradient = float(
            quadratic
            - mode.determinant_trace
            + 0.5 * np.dot(determinant_diagonal, third * du_log_sigma)
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
            try:
                for index, d_ell, d_score, d_curvature in self._site_nuisance_derivatives(
                    point, fixed_h, mode.eta, fd_step, sigma_zero=False
                ):
                    du = cho_solve(hessian_factor, d_score, check_finite=True)
                    gradient[index] = float(
                        np.sum(d_ell) + 0.5 * np.dot(determinant_diagonal, d_curvature + third * du)
                    )
            except (CurveDomainError, FloatingPointError, ValueError) as exc:
                return self._invalid(
                    point,
                    sigma_zero=False,
                    h=h,
                    detection_sd=detection_sd,
                    message=f"nuisance derivative failed: {exc}",
                    mode=mode,
                )
            result = replace(result, criterion_gradient=gradient, objective_gradient=-gradient)
        return result

    def _site_nuisance_derivatives(
        self,
        point: FloatArray,
        fixed_h: float | None,
        eta: FloatArray,
        fd_step: float,
        *,
        sigma_zero: bool,
    ) -> list[tuple[int, FloatArray, FloatArray, FloatArray]]:
        """Richardson site derivatives in log h and detection SD at fixed eta.

        Central base stencils give fourth-order accuracy in the interior.
        Near a bound, second-order one-sided stencils stay in the fitted
        domain; their Richardson remainder is third order, not fourth order.
        The latent mode and Laplace terms are differentiated by the caller.
        """
        if not math.isfinite(fd_step) or fd_step <= 0.0:
            raise ValueError("fd_step must be finite and positive")
        bounds = self._bounds(fixed_h, sigma_zero)
        indices = [len(point) - 1]
        if fixed_h is None:
            indices.insert(0, len(point) - 2)
        rows = []
        for index in indices:
            lower, upper = bounds[index]
            x = float(point[index])
            delta = fd_step * max(1.0, abs(x))
            central = x + delta <= upper and x - delta >= lower
            direction = 1.0 if upper - x >= x - lower else -1.0
            if not central:
                room = upper - x if direction > 0 else x - lower
                delta = min(delta, float(np.nextafter(room / 2.0, 0.0)))
            if delta <= 0.0 or x + direction * delta == x:
                raise ValueError("nuisance coordinate has no admissible difference step")
            cache: dict[float, tuple[FloatArray, FloatArray, FloatArray]] = {}

            def site(
                value: float,
                index: int = index,
                cache: dict[float, tuple[FloatArray, FloatArray, FloatArray]] = cache,
            ) -> tuple[FloatArray, FloatArray, FloatArray]:
                if value in cache:
                    return cache[value]
                candidate = point.copy()
                candidate[index] = value
                _, h, detection_sd = self._unpack(candidate, fixed_h, sigma_zero)
                started = time.perf_counter()
                self.stats["nuisance_site_evaluations"] = (
                    int(self.stats["nuisance_site_evaluations"]) + 1
                )
                try:
                    ell, score, curvature, _ = self.curves(h, detection_sd).evaluate(eta)
                finally:
                    self.stats["nuisance_site_seconds"] = (
                        float(self.stats["nuisance_site_seconds"]) + time.perf_counter() - started
                    )
                cache[value] = ell, score, curvature
                return cache[value]

            def difference(
                width: float,
                central: bool = central,
                x: float = x,
                direction: float = direction,
                site: Any = site,
            ) -> tuple[FloatArray, ...]:
                if central:
                    hi, lo = site(x + width), site(x - width)
                    return tuple(
                        (high - low) / (2.0 * width) for high, low in zip(hi, lo, strict=True)
                    )
                base, one, two = (
                    site(x),
                    site(x + direction * width),
                    site(x + 2 * direction * width),
                )
                return tuple(
                    direction * (-3.0 * f0 + 4.0 * f1 - f2) / (2.0 * width)
                    for f0, f1, f2 in zip(base, one, two, strict=True)
                )

            coarse, fine = difference(delta), difference(delta / 2.0)
            derivatives = tuple(
                (4.0 * half - full) / 3.0 for full, half in zip(coarse, fine, strict=True)
            )
            key = "nuisance_richardson_central" if central else "nuisance_richardson_one_sided"
            self.stats[key] = int(self.stats[key]) + 1
            rows.append((index, derivatives[0], derivatives[1], derivatives[2]))
        return rows

    def evaluate_sigma_zero(
        self,
        parameters: NDArray[Any],
        fixed_h: float | None = None,
        *,
        nuisance_fd: bool = False,
        fd_step: float = 1e-3,
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
            try:
                for index, d_ell, _, _ in self._site_nuisance_derivatives(
                    point, fixed_h, eta, fd_step, sigma_zero=True
                ):
                    gradient[index] = float(np.sum(d_ell))
            except (CurveDomainError, FloatingPointError, ValueError) as exc:
                return self._invalid(
                    point,
                    sigma_zero=True,
                    h=h,
                    detection_sd=detection_sd,
                    message=f"nuisance derivative failed: {exc}",
                )
            result = replace(result, criterion_gradient=gradient, objective_gradient=-gradient)
        return result

    @staticmethod
    def _bounds(fixed_h: float | None, sigma_zero: bool) -> tuple[tuple[float, float], ...]:
        common = [(-12.0, -3.0), (-2.0, 2.0)]
        if not sigma_zero:
            common.append((math.log(1e-4), math.log(SIGMA_MAX)))
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

    def _trust_region(
        self,
        evaluate: Any,
        start: FloatArray,
        bounds: Sequence[tuple[float, float]],
        *,
        maxiter: int,
        gradient_tolerance: float,
    ) -> tuple[FloatArray, CriterionEvaluation, OptimizeResult]:
        """Maximise by projected trust-region Newton with exact gradients.

        The Hessian is a symmetrised forward difference of the analytic
        gradient (retried backwards, then replaced by a diagonal curvature
        if both differences fail). Negative-curvature directions are handled
        by an eigenvalue shift, and a first-order stationary point is accepted
        only after a second-order check finds no ascent direction.
        Returned success certifies that point, independently of whether the
        terminal message records a stall or an exhausted iteration budget.
        """
        lower = np.array([bound[0] for bound in bounds])
        upper = np.array([bound[1] for bound in bounds])
        x = np.clip(np.asarray(start, dtype=np.float64), lower, upper)
        current = evaluate(x)
        evaluations, radius, message = 1, 1.0, "iteration limit reached"
        iterations, escapes = 0, 0
        certified = False
        curvature_point: FloatArray | None = None
        curvature_complete = False
        values = np.array([], dtype=np.float64)
        if not current.success:
            return (
                x,
                current,
                OptimizeResult(
                    x=x,
                    success=False,
                    message="start evaluation failed",
                    nit=0,
                    nfev=1,
                    second_order_passed=False,
                    curvature_complete=False,
                ),
            )

        def free_set(point: FloatArray, gradient: FloatArray) -> NDArray[np.intp]:
            tolerance = 1e-8 * np.maximum(1.0, np.maximum(np.abs(lower), np.abs(upper)))
            active = ((point <= lower + tolerance) & (gradient < 0.0)) | (
                (point >= upper - tolerance) & (gradient > 0.0)
            )
            return np.flatnonzero(~active)

        def curvature_at(
            point: FloatArray, gradient: FloatArray, free: NDArray[np.intp]
        ) -> tuple[FloatArray, int, bool]:
            hessian = np.zeros((len(point), len(point)))
            failed = []
            count = 0
            for index in free:
                delta = 1e-5 * max(1.0, abs(float(point[index])))
                column = None
                for signed in (delta, -delta):
                    trial = point.copy()
                    trial[index] += signed
                    if not lower[index] <= trial[index] <= upper[index]:
                        continue
                    other = evaluate(trial)
                    count += 1
                    if other.success:
                        column = (other.criterion_gradient - gradient) / signed
                        break
                if column is None:
                    failed.append(index)
                else:
                    hessian[:, index] = column
            curvature = -0.5 * (hessian + hessian.T)
            if failed:
                good = [i for i in free if i not in failed]
                scale = max([1.0, *(abs(float(curvature[i, i])) for i in good)])
                for index in failed:
                    curvature[index, :] = 0.0
                    curvature[:, index] = 0.0
                    curvature[index, index] = scale
            return curvature[np.ix_(free, free)], count, not failed

        while iterations < maxiter:
            iterations += 1
            gradient = current.criterion_gradient
            free = free_set(x, gradient)
            curvature, count, curvature_complete = curvature_at(x, gradient, free)
            curvature_point = x.copy()
            evaluations += count
            values, vectors = np.linalg.eigh(curvature)
            if self._projected_gradient_inf(-gradient, x, bounds) <= gradient_tolerance:
                if not curvature_complete:
                    message = "projected gradient below tolerance; second-order check unavailable"
                    break
                scale = max(1.0, float(np.max(np.abs(values)))) if len(values) else 1.0
                if not len(values) or values.min() >= -1e-6 * scale:
                    certified = True
                    message = "projected gradient below tolerance; no ascent direction"
                    break
                if escapes >= 3:
                    message = "projected gradient below tolerance; saddle escape limit reached"
                    break
                escapes += 1
                direction = np.zeros_like(x)
                direction[free] = vectors[:, 0]
                improved = False
                for backtrack in range(13):
                    escape_radius = radius * 0.5**backtrack
                    for signed in (escape_radius, -escape_radius):
                        trial = np.clip(x + signed * direction, lower, upper)
                        candidate = evaluate(trial)
                        evaluations += 1
                        if candidate.success and candidate.criterion > current.criterion + 1e-10:
                            x, current, improved = trial, candidate, True
                            break
                    if improved:
                        break
                if not improved:
                    message = "projected gradient below tolerance; saddle escape failed"
                    break
                continue
            projected_gradient = vectors.T @ gradient[free]
            shift = max(0.0, 1e-8 - float(values.min()))
            while True:
                step_free = vectors @ (projected_gradient / (values + shift))
                if np.linalg.norm(step_free) <= radius:
                    break
                shift = 2.0 * shift + 1e-3
            step = np.zeros_like(x)
            step[free] = step_free
            trial = np.clip(x + step, lower, upper)
            step = trial - x
            predicted = float(
                gradient[free] @ step[free] - 0.5 * step[free] @ curvature @ step[free]
            )
            candidate = evaluate(trial)
            evaluations += 1
            ratio = (
                (candidate.criterion - current.criterion) / predicted
                if candidate.success and predicted > 0.0
                else -1.0
            )
            if ratio > 0.1:
                x, current = trial, candidate
                if ratio > 0.75:
                    radius = min(4.0, 2.0 * radius)
            else:
                radius /= 4.0
                if radius < 1e-10:
                    message = "trust region collapsed"
                    break
        second_order_passed = False
        stationary = self._projected_gradient_inf(-current.criterion_gradient, x, bounds)
        if current.success and stationary <= gradient_tolerance:
            if curvature_point is None or not np.array_equal(curvature_point, x):
                free = free_set(x, current.criterion_gradient)
                curvature, count, curvature_complete = curvature_at(
                    x, current.criterion_gradient, free
                )
                evaluations += count
                values = np.linalg.eigvalsh(curvature)
            scale = max(1.0, float(np.max(np.abs(values)))) if len(values) else 1.0
            second_order_passed = bool(
                curvature_complete and (not len(values) or values.min() >= -1e-6 * scale)
            )
        if second_order_passed and not certified:
            message += "; returned point passes stationarity and second-order check"
        certified = bool(
            current.success and stationary <= gradient_tolerance and second_order_passed
        )
        return (
            x,
            current,
            OptimizeResult(
                x=x,
                success=certified,
                message=message,
                nit=iterations,
                nfev=evaluations,
                second_order_passed=second_order_passed,
                curvature_complete=bool(curvature_complete),
            ),
        )

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

        def evaluate(point: FloatArray) -> CriterionEvaluation:
            try:
                if sigma_zero:
                    return self.evaluate_sigma_zero(point, fixed_h=fixed_h, nuisance_fd=True)
                return self.evaluate_positive(point, fixed_h=fixed_h, nuisance_fd=True)
            except (CurveDomainError, FloatingPointError, ValueError) as exc:
                h = math.nan if fixed_h is None else float(fixed_h)
                return self._invalid(
                    point,
                    sigma_zero=sigma_zero,
                    h=h,
                    detection_sd=float(point[-1]),
                    message=str(exc),
                )

        for start_index, raw_start in enumerate(starts):
            start = np.asarray(raw_start, dtype=np.float64)
            if start.shape != (len(bounds),):
                raise ValueError(f"{family} start has the wrong dimension")
            x, evaluation, result = self._trust_region(
                evaluate,
                start,
                bounds,
                maxiter=maxiter,
                gradient_tolerance=kkt_tolerance,
            )
            projected = (
                self._projected_gradient_inf(evaluation.objective_gradient, x, bounds)
                if evaluation.success
                else math.inf
            )
            candidates.append(
                FitCandidate(
                    family,
                    f"{source_prefix}_fit_{start_index}",
                    x.copy(),
                    evaluation,
                    bool(result.success),
                    str(result.message),
                    int(result.nit),
                    int(result.nfev),
                    projected,
                    bool(result.success and evaluation.success and projected <= kkt_tolerance),
                )
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
