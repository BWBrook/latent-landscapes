"""Bounded numerical fitting for the pre-invasion feasibility likelihood.

The module deliberately knows nothing about the observation likelihood.  A
caller supplies a callback returning a scalar log likelihood for an
observation-only data object.  The callback is invoked directly with the
fitted parameters as keyword arguments.  This keeps fitting, prediction and
the likelihood implementation independently testable.

The production statistic is defined by the main fits.  Profile calculations
are diagnostics: a profile that finds a higher value is reported, but never
used to edit the main fit or its likelihood-ratio statistic.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import OptimizeResult, minimize  # type: ignore[import-untyped]

FloatArray = NDArray[np.float64]
ModelName = Literal["constant_free_h", "adjusted_free_h", "constant_h1", "adjusted_h1"]

H_BOUNDS = (1.0, 10.0)
BETA_BOUNDS = (-2.0, 2.0)
MU_BOUNDS = (0.0005, 0.006)
DETECTION_SD_BOUNDS = (0.0, 0.4)
KNOWN_DETECTION_MEAN = 0.65
_VARIANCE_SCALE = DETECTION_SD_BOUNDS[1] ** 2
_LOG_MU_BOUNDS = (math.log(MU_BOUNDS[0]), math.log(MU_BOUNDS[1]))
_LOG_H_BOUNDS = (math.log(H_BOUNDS[0]), math.log(H_BOUNDS[1]))
_OPT_OPTIONS = {"ftol": 1e-12, "gtol": 1e-9, "maxiter": 2_000, "maxls": 50}
_POWELL_OPTIONS = {"xtol": 1e-10, "ftol": 1e-12, "maxiter": 2_000, "maxfev": 20_000}
_BOUND_EPS = 1e-7
_SUCCESS_TIE_TOL = 1e-8


class LikelihoodCallback(Protocol):
    """Observation-only likelihood callback.

    The callback signature is ``callback(data, *, h, beta, mu,
    detection_sd) -> float``.
    """

    def __call__(
        self,
        data: Any,
        *,
        h: float,
        beta: float,
        mu: float,
        detection_sd: float,
    ) -> float: ...


class PreOnlyLikelihoodCallback(Protocol):
    """Callback for the pre-only nuisance likelihood (no arrival or h)."""

    def __call__(self, data: Any, *, beta: float, mu: float, detection_sd: float) -> float: ...


@dataclass(frozen=True, slots=True)
class StartRecord:
    """One deterministic multistart attempt, retained for auditability."""

    initial_parameters: dict[str, float]
    final_parameters: dict[str, float]
    raw_logjoint: float
    objective: float
    success: bool
    status: int | str
    message: str
    nfev: int
    method: str


@dataclass(frozen=True, slots=True)
class FitResult:
    """One bounded fit and its numerical diagnostics."""

    model: str
    h: float
    beta: float
    mu: float
    detection_sd: float
    raw_logjoint: float
    numerical_status: str
    nfev: int
    elapsed_seconds: float
    starts: tuple[StartRecord, ...] = ()
    objective_gap: float = math.nan
    boundary_flags: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def parameters(self) -> dict[str, float]:
        return {
            "h": self.h,
            "beta": self.beta,
            "mu": self.mu,
            "detection_sd": self.detection_sd,
        }

    @property
    def known_detection_mean(self) -> float:
        return KNOWN_DETECTION_MEAN

    @property
    def converged(self) -> bool:
        return self.numerical_status == "converged"


@dataclass(frozen=True, slots=True)
class NuisanceFitResult:
    """Pre-invasion-only nuisance fit over ``beta``, ``mu`` and SD."""

    beta: float
    mu: float
    detection_sd: float
    raw_logjoint: float
    numerical_status: str
    nfev: int
    elapsed_seconds: float
    starts: tuple[StartRecord, ...] = ()
    objective_gap: float = math.nan
    boundary_flags: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def parameters(self) -> dict[str, float]:
        return {"beta": self.beta, "mu": self.mu, "detection_sd": self.detection_sd}

    @property
    def converged(self) -> bool:
        return self.numerical_status == "converged"


@dataclass(frozen=True, slots=True)
class HeldoutScore:
    """Score from a fixed training fit, evaluated on separately supplied data."""

    model: str
    raw_logjoint: float
    score_per_site: float | None
    numerical_status: str
    nfev: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CostSummary:
    """Measured fitting and diagnostic cost for one paired fit."""

    main_nfev: int
    diagnostic_nfev: int
    total_nfev: int
    main_seconds: float
    diagnostic_seconds: float
    total_seconds: float


@dataclass(frozen=True, slots=True)
class PairedFitResult:
    """The four training fits and nested effect statistics."""

    T: float
    fits: dict[str, FitResult]
    statistics: dict[str, float]
    cost: CostSummary

    @property
    def all_fits(self) -> dict[str, FitResult]:
        return self.fits

    @property
    def adjusted_T(self) -> float:
        return self.statistics["adjusted"]

    @property
    def constant_T(self) -> float:
        return self.statistics["constant"]


@dataclass(frozen=True, slots=True)
class ProfileResult:
    """A raw one-dimensional profile and retained conditional fit records.

    For an ``h`` profile, ``curvature`` is the three-point second derivative
    of log likelihood with respect to ``log(h)``.  It is raw support
    information and does not imply a confidence interval.
    """

    coordinate: str
    grid: FloatArray
    values: FloatArray
    parameters: tuple[dict[str, float], ...]
    statuses: tuple[str, ...]
    nfev: int
    elapsed_seconds: float
    better_than_main: bool
    curvature: float | None
    warnings: tuple[str, ...] = ()
    curvature_coordinate: str | None = None


@dataclass(frozen=True, slots=True)
class _FreeSpec:
    names: tuple[str, ...]
    fixed: dict[str, float]


def _model_spec(model: str) -> _FreeSpec:
    if model == "constant_free_h":
        return _FreeSpec(("logh", "logmu", "v"), {"beta": 0.0})
    if model == "adjusted_free_h":
        return _FreeSpec(("logh", "beta", "logmu", "v"), {})
    if model == "constant_h1":
        return _FreeSpec(("logmu", "v"), {"h": 1.0, "beta": 0.0})
    if model == "adjusted_h1":
        return _FreeSpec(("beta", "logmu", "v"), {"h": 1.0})
    raise ValueError(f"unknown model {model!r}")


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("likelihood callback must return one finite scalar") from error


def _invoke_callback(
    callback: Callable[..., Any], data: Any, parameters: Mapping[str, float]
) -> float:
    """Invoke the documented keyword-only callback without hot-path introspection."""

    return _as_float(callback(data, **parameters))


def _invoke_pre_callback(
    callback: Callable[..., Any], data: Any, parameters: Mapping[str, float]
) -> float:
    """Invoke the documented pre-only keyword-only callback."""

    return _as_float(callback(data, **parameters))


def _decode(vector: Sequence[float] | np.ndarray[Any, Any], spec: _FreeSpec) -> dict[str, float]:
    values = dict(spec.fixed)
    for name, value in zip(spec.names, vector, strict=True):
        values[name] = float(value)
    return {
        "h": values["h"] if "h" in values else math.exp(values.get("logh", 0.0)),
        "beta": values.get("beta", 0.0),
        "mu": values["mu"] if "mu" in values else math.exp(values.get("logmu", math.log(0.002))),
        "detection_sd": (
            values["detection_sd"]
            if "detection_sd" in values
            else math.sqrt(max(values.get("v", 0.0), 0.0) * _VARIANCE_SCALE)
        ),
    }


def _encode(parameters: Mapping[str, float], spec: _FreeSpec) -> NDArray[np.float64]:
    values = {
        "logh": math.log(float(parameters["h"])),
        "beta": float(parameters["beta"]),
        "logmu": math.log(float(parameters["mu"])),
        "v": float(parameters["detection_sd"]) ** 2 / _VARIANCE_SCALE,
    }
    return np.asarray([values[name] for name in spec.names], dtype=np.float64)


def _bounds(spec: _FreeSpec) -> tuple[tuple[float, float], ...]:
    all_bounds: dict[str, tuple[float, float]] = {
        "logh": _LOG_H_BOUNDS,
        "beta": BETA_BOUNDS,
        "logmu": _LOG_MU_BOUNDS,
        "v": (0.0, 1.0),
    }
    return tuple(all_bounds[name] for name in spec.names)


def _domain_starts() -> tuple[dict[str, float], ...]:
    """Nine fixed starts covering both h edges, beta signs and SD edges."""

    return (
        {"h": 1.0, "beta": 0.0, "mu": 0.002, "detection_sd": 0.0},
        {"h": 1.0, "beta": -1.0, "mu": 0.002, "detection_sd": 0.4},
        {"h": 1.0, "beta": 1.0, "mu": 0.002, "detection_sd": 0.4},
        {"h": 3.0, "beta": 0.0, "mu": 0.002, "detection_sd": 0.2},
        {"h": 3.0, "beta": -1.0, "mu": 0.002, "detection_sd": 0.0},
        {"h": 3.0, "beta": 1.0, "mu": 0.002, "detection_sd": 0.4},
        {"h": 10.0, "beta": 0.0, "mu": 0.002, "detection_sd": 0.4},
        {"h": 10.0, "beta": -1.0, "mu": 0.002, "detection_sd": 0.2},
        {"h": 10.0, "beta": 1.0, "mu": 0.002, "detection_sd": 0.0},
    )


def _check_initial(parameters: Mapping[str, float]) -> None:
    for name, (lower, upper) in (
        ("h", H_BOUNDS),
        ("beta", BETA_BOUNDS),
        ("mu", MU_BOUNDS),
        ("detection_sd", DETECTION_SD_BOUNDS),
    ):
        value = float(parameters[name])
        if not math.isfinite(value) or not lower <= value <= upper:
            raise ValueError(f"initial {name} must be finite and within its bounds")


def _boundary_flags(parameters: Mapping[str, float]) -> tuple[str, ...]:
    flags: list[str] = []
    for name, (lower, upper) in (
        ("h", H_BOUNDS),
        ("beta", BETA_BOUNDS),
        ("mu", MU_BOUNDS),
        ("detection_sd", DETECTION_SD_BOUNDS),
    ):
        value = float(parameters[name])
        scale = max(abs(lower), abs(upper), 1.0)
        if abs(value - lower) <= _BOUND_EPS * scale:
            flags.append(f"{name}_lower")
        if abs(value - upper) <= _BOUND_EPS * scale:
            flags.append(f"{name}_upper")
    return tuple(flags)


def _profile_curvature(
    grid: FloatArray,
    values: FloatArray,
    statuses: Sequence[str],
    *,
    log_coordinate: bool = False,
) -> float | None:
    finite = np.isfinite(values)
    if not finite.any():
        return None
    index = int(np.nanargmax(values))
    if index == 0 or index == len(values) - 1:
        return None
    if not all(statuses[index - 1 + offset] == "converged" for offset in range(3)):
        return None
    coordinate = np.log(grid) if log_coordinate else grid
    x0, x1, x2 = (float(coordinate[index + offset]) for offset in (-1, 0, 1))
    if not all(math.isfinite(value) for value in (x0, x1, x2)) or not x0 < x1 < x2:
        return None
    curvature = float(
        2.0
        * (
            values[index - 1] / ((x0 - x1) * (x0 - x2))
            + values[index] / ((x1 - x0) * (x1 - x2))
            + values[index + 1] / ((x2 - x0) * (x2 - x1))
        )
    )
    return curvature if curvature < -1e-12 else None


def _profile_starts(
    main_seed: Mapping[str, float],
    previous_success: Mapping[str, float] | None,
    spec: _FreeSpec,
) -> tuple[dict[str, float], ...]:
    """Return the fixed two-start profile policy, with deterministic deduplication."""

    candidates = (
        (dict(previous_success), dict(main_seed))
        if previous_success is not None
        else (dict(main_seed), dict(_domain_starts()[0]))
    )
    output: list[dict[str, float]] = []
    seen: set[tuple[float, ...]] = set()
    for candidate in candidates:
        candidate.update(spec.fixed)
        candidate.setdefault("h", 1.0)
        candidate.setdefault("beta", 0.0)
        candidate.setdefault("mu", 0.002)
        candidate.setdefault("detection_sd", 0.0)
        # Decoding a bounded optimizer result can spill one or two ulps past a
        # physical bound (for example, exp(log(10)) can be 10.000000000000002).
        # Repair only that representation artefact here; genuine violations
        # remain errors and are checked before a profile fit is launched.
        for name, (lower, upper) in (
            ("h", H_BOUNDS),
            ("beta", BETA_BOUNDS),
            ("mu", MU_BOUNDS),
            ("detection_sd", DETECTION_SD_BOUNDS),
        ):
            value = float(candidate[name])
            if not math.isfinite(value):
                continue
            if abs(value - lower) <= 8.0 * math.ulp(lower):
                candidate[name] = lower
            elif abs(value - upper) <= 8.0 * math.ulp(upper):
                candidate[name] = upper
        _check_initial(candidate)
        key = tuple(float(value) for value in _encode(candidate, spec))
        if key not in seen:
            seen.add(key)
            output.append(candidate)
    return tuple(output)


def _run_fit(
    data: Any,
    callback: Callable[..., Any],
    model: str,
    *,
    extra_candidates: Sequence[Mapping[str, float]] = (),
    extra_candidate_success: Sequence[bool] = (),
    starts: Sequence[Mapping[str, float]] | None = None,
) -> FitResult:
    spec = _model_spec(model)
    base_starts = tuple(_domain_starts() if starts is None else starts)
    candidate_starts = (*base_starts, *extra_candidates)
    for candidate in candidate_starts:
        _check_initial(candidate)
    start_time = time.perf_counter()
    records: list[StartRecord] = []
    warnings: list[str] = []
    outcomes: list[tuple[float, dict[str, float], bool, int | str, str, int, str]] = []
    nfev_total = 0

    def objective(vector: NDArray[np.float64]) -> float:
        parameters = _decode(vector, spec)
        try:
            value = _invoke_callback(callback, data, parameters)
        except (FloatingPointError, OverflowError, ValueError):
            warnings.append("likelihood callback returned an invalid value")
            return 1e300
        if not math.isfinite(value):
            warnings.append("likelihood callback returned NaN or infinity")
            return 1e300
        return -value

    if len(extra_candidate_success) not in (0, len(extra_candidates)):
        raise ValueError("extra candidate status must match extra candidates")
    for initial_index, initial in enumerate(candidate_starts):
        x0 = _encode(initial, spec)
        if initial_index >= len(base_starts):
            objective_value = objective(x0)
            nfev_total += 1
            params = _decode(x0, spec)
            raw = -objective_value if objective_value < 1e299 else math.nan
            extra_index = initial_index - len(base_starts)
            candidate_success = (
                extra_candidate_success[extra_index] if extra_candidate_success else True
            )
            record = StartRecord(
                dict(initial),
                params,
                raw,
                objective_value,
                math.isfinite(raw) and candidate_success,
                "nested_converged" if candidate_success else "nested_unconverged",
                "nested candidate"
                if candidate_success
                else "nested candidate from unconverged fit",
                1,
                "candidate",
            )
            records.append(record)
            outcomes.append(
                (
                    objective_value,
                    params,
                    math.isfinite(raw) and candidate_success,
                    "nested_converged" if candidate_success else "nested_unconverged",
                    "nested candidate",
                    1,
                    "candidate",
                )
            )
            continue
        result: OptimizeResult = minimize(
            objective,
            x0,
            method="L-BFGS-B",
            bounds=_bounds(spec),
            options=_OPT_OPTIONS,
        )
        nfev = int(getattr(result, "nfev", 0))
        nfev_total += nfev
        params = _decode(np.asarray(result.x, dtype=np.float64), spec)
        objective_value = float(result.fun)
        valid = math.isfinite(objective_value) and objective_value < 1e299
        raw = -objective_value if valid else math.nan
        attempt_status = int(getattr(result, "status", -1))
        message = str(getattr(result, "message", ""))
        success = bool(getattr(result, "success", False)) and valid
        records.append(
            StartRecord(
                dict(initial),
                params,
                raw,
                objective_value,
                success,
                attempt_status,
                message,
                nfev,
                "L-BFGS-B",
            )
        )
        outcomes.append(
            (objective_value, params, success, attempt_status, message, nfev, "L-BFGS-B")
        )

    valid_outcomes = [
        outcome for outcome in outcomes if math.isfinite(outcome[0]) and outcome[0] < 1e299
    ]
    if not valid_outcomes:
        elapsed = time.perf_counter() - start_time
        return FitResult(
            model,
            math.nan,
            math.nan,
            math.nan,
            math.nan,
            math.nan,
            "invalid",
            nfev_total,
            elapsed,
            tuple(records),
            math.nan,
            (),
            tuple(dict.fromkeys(warnings)),
        )
    valid_outcomes.sort(key=lambda outcome: (outcome[0], tuple(outcome[1].values())))
    objective_floor = valid_outcomes[0][0]
    converged_outcomes = [outcome for outcome in valid_outcomes if outcome[2]]
    if converged_outcomes and converged_outcomes[0][0] <= objective_floor + _SUCCESS_TIE_TOL:
        best = converged_outcomes[0]
    else:
        best = valid_outcomes[0]
    if not best[2]:
        # A fixed Powell fallback is reserved for a failed best L-BFGS-B run.
        initial_vector = _encode(best[1], spec)
        result = minimize(
            objective,
            initial_vector,
            method="Powell",
            bounds=_bounds(spec),
            options=_POWELL_OPTIONS,
        )
        nfev = int(getattr(result, "nfev", 0))
        nfev_total += nfev
        params = _decode(np.asarray(result.x, dtype=np.float64), spec)
        objective_value = float(result.fun)
        valid = math.isfinite(objective_value) and objective_value < 1e299
        raw = -objective_value if valid else math.nan
        records.append(
            StartRecord(
                dict(best[1]),
                params,
                raw,
                objective_value,
                bool(result.success) and valid,
                int(getattr(result, "status", -1)),
                str(getattr(result, "message", "")),
                nfev,
                "Powell",
            )
        )
        powell_success = bool(result.success) and valid
        if powell_success and objective_value <= best[0] + _SUCCESS_TIE_TOL:
            best = (
                objective_value,
                params,
                powell_success,
                int(getattr(result, "status", -1)),
                str(getattr(result, "message", "")),
                nfev,
                "Powell",
            )
        else:
            warnings.append("Powell refinement did not improve the best L-BFGS-B objective")

    objective_values = sorted(outcome[0] for outcome in valid_outcomes)
    gap = math.nan if len(objective_values) < 2 else float(objective_values[1] - best[0])
    status = "converged" if best[2] else "failed_optimizer"
    elapsed = time.perf_counter() - start_time
    return FitResult(
        model,
        best[1]["h"],
        best[1]["beta"],
        best[1]["mu"],
        best[1]["detection_sd"],
        -best[0],
        status,
        nfev_total,
        elapsed,
        tuple(records),
        gap,
        _boundary_flags(best[1]),
        tuple(dict.fromkeys(warnings)),
    )


def fit_model(
    data: Any,
    likelihood: Callable[..., Any],
    model: ModelName | str,
    *,
    starts: Sequence[Mapping[str, float]] | None = None,
    extra_candidates: Sequence[Mapping[str, float]] = (),
) -> FitResult:
    """Fit one of the four prespecified models with deterministic multistart."""

    return _run_fit(data, likelihood, model, starts=starts, extra_candidates=extra_candidates)


def fit_four_models(data: Any, likelihood: Callable[..., Any]) -> dict[str, FitResult]:
    """Fit all four candidates, evaluating each unrestricted fit at its null."""

    constant_null = _run_fit(data, likelihood, "constant_h1")
    adjusted_null = _run_fit(data, likelihood, "adjusted_h1")
    constant_alt = _run_fit(
        data,
        likelihood,
        "constant_free_h",
        extra_candidates=(constant_null.parameters,),
        extra_candidate_success=(constant_null.converged,),
    )
    adjusted_alt = _run_fit(
        data,
        likelihood,
        "adjusted_free_h",
        extra_candidates=(adjusted_null.parameters,),
        extra_candidate_success=(adjusted_null.converged,),
    )
    return {
        "constant_free_h": constant_alt,
        "adjusted_free_h": adjusted_alt,
        "constant_h1": constant_null,
        "adjusted_h1": adjusted_null,
    }


def paired_fit(data: Any, likelihood: Callable[..., Any]) -> PairedFitResult:
    """Return the adjusted nested statistic and all four training fits.

    ``T`` is the primary adjusted-background statistic.  The analogous
    constant-background statistic is retained in ``statistics`` for diagnosis.
    """

    start = time.perf_counter()
    fits = fit_four_models(data, likelihood)
    adjusted_difference = fits["adjusted_free_h"].raw_logjoint - fits["adjusted_h1"].raw_logjoint
    constant_difference = fits["constant_free_h"].raw_logjoint - fits["constant_h1"].raw_logjoint
    adjusted = (
        max(0.0, 2.0 * adjusted_difference) if math.isfinite(adjusted_difference) else math.nan
    )
    constant = (
        max(0.0, 2.0 * constant_difference) if math.isfinite(constant_difference) else math.nan
    )
    main_seconds = time.perf_counter() - start
    main_nfev = sum(result.nfev for result in fits.values())
    return PairedFitResult(
        adjusted,
        fits,
        {"adjusted": adjusted, "constant": constant},
        CostSummary(main_nfev, 0, main_nfev, main_seconds, 0.0, main_seconds),
    )


def fit_pre_only_nuisance(
    data: Any,
    likelihood: Callable[..., Any],
    *,
    starts: Sequence[Mapping[str, float]] | None = None,
) -> NuisanceFitResult:
    """Fit beta, mean and detection SD using the pre-invasion data only."""

    fixed_starts = (
        (
            {"beta": -2.0, "mu": 0.002, "detection_sd": 0.0},
            {"beta": -1.0, "mu": 0.002, "detection_sd": 0.4},
            {"beta": 0.0, "mu": 0.002, "detection_sd": 0.2},
            {"beta": 1.0, "mu": 0.002, "detection_sd": 0.4},
            {"beta": 2.0, "mu": 0.002, "detection_sd": 0.0},
        )
        if starts is None
        else tuple(starts)
    )
    for candidate in fixed_starts:
        if (
            not BETA_BOUNDS[0] <= candidate["beta"] <= BETA_BOUNDS[1]
            or not MU_BOUNDS[0] <= candidate["mu"] <= MU_BOUNDS[1]
            or not DETECTION_SD_BOUNDS[0] <= candidate["detection_sd"] <= DETECTION_SD_BOUNDS[1]
        ):
            raise ValueError("pre-only starting values must be within bounds")
    start_time = time.perf_counter()
    records: list[StartRecord] = []
    warnings: list[str] = []
    bounds = (BETA_BOUNDS, _LOG_MU_BOUNDS, (0.0, 1.0))

    def decode(vector: Sequence[float] | np.ndarray[Any, Any]) -> dict[str, float]:
        return {
            "beta": float(vector[0]),
            "mu": math.exp(float(vector[1])),
            "detection_sd": math.sqrt(float(vector[2]) * _VARIANCE_SCALE),
        }

    def objective(vector: NDArray[np.float64]) -> float:
        params = decode(vector)
        try:
            value = _invoke_pre_callback(likelihood, data, params)
        except (FloatingPointError, OverflowError, ValueError):
            warnings.append("likelihood callback returned an invalid value")
            return 1e300
        if not math.isfinite(value):
            warnings.append("likelihood callback returned NaN or infinity")
            return 1e300
        return -value

    outcomes: list[tuple[float, dict[str, float], bool, int, str]] = []
    nfev_total = 0
    for initial in fixed_starts:
        x0 = np.asarray(
            (
                initial["beta"],
                math.log(initial["mu"]),
                initial["detection_sd"] ** 2 / _VARIANCE_SCALE,
            )
        )
        result = minimize(objective, x0, method="L-BFGS-B", bounds=bounds, options=_OPT_OPTIONS)
        objective_value = float(result.fun)
        valid = math.isfinite(objective_value) and objective_value < 1e299
        params = decode(result.x)
        nfev = int(getattr(result, "nfev", 0))
        nfev_total += nfev
        records.append(
            StartRecord(
                dict(initial),
                params,
                -objective_value if valid else math.nan,
                objective_value,
                bool(result.success) and valid,
                int(getattr(result, "status", -1)),
                str(getattr(result, "message", "")),
                nfev,
                "L-BFGS-B",
            )
        )
        if valid:
            outcomes.append(
                (
                    objective_value,
                    params,
                    bool(result.success),
                    int(getattr(result, "status", -1)),
                    str(getattr(result, "message", "")),
                )
            )
    if not outcomes:
        elapsed = time.perf_counter() - start_time
        return NuisanceFitResult(
            math.nan,
            math.nan,
            math.nan,
            math.nan,
            "invalid",
            nfev_total,
            elapsed,
            tuple(records),
            math.nan,
            (),
            tuple(dict.fromkeys(warnings)),
        )
    outcomes.sort(key=lambda outcome: (outcome[0], tuple(outcome[1].values())))
    objective_floor = outcomes[0][0]
    converged_outcomes = [outcome for outcome in outcomes if outcome[2]]
    if converged_outcomes and converged_outcomes[0][0] <= objective_floor + _SUCCESS_TIE_TOL:
        best = converged_outcomes[0]
    else:
        best = outcomes[0]
    gap = math.nan if len(outcomes) < 2 else float(outcomes[1][0] - best[0])
    status = "converged" if best[2] else "failed_optimizer"
    elapsed = time.perf_counter() - start_time
    return NuisanceFitResult(
        best[1]["beta"],
        best[1]["mu"],
        best[1]["detection_sd"],
        -best[0],
        status,
        nfev_total,
        elapsed,
        tuple(records),
        gap,
        _boundary_flags({"h": 1.0, **best[1]}),
        tuple(dict.fromkeys(warnings)),
    )


def score_heldout(
    fits: Mapping[str, FitResult],
    heldout_data: Any,
    likelihood: Callable[..., Any],
    *,
    site_count: int | None = None,
) -> dict[str, HeldoutScore]:
    """Score held-out observations at fixed training estimates."""

    output: dict[str, HeldoutScore] = {}
    for model, fit in fits.items():
        try:
            value = _invoke_callback(likelihood, heldout_data, fit.parameters)
        except (FloatingPointError, OverflowError, ValueError, TypeError):
            output[model] = HeldoutScore(
                model, math.nan, None, "invalid", 1, ("invalid heldout likelihood",)
            )
            continue
        if not math.isfinite(value):
            output[model] = HeldoutScore(
                model, math.nan, None, "invalid", 1, ("invalid heldout likelihood",)
            )
            continue
        per_site = value / site_count if site_count is not None else None
        output[model] = HeldoutScore(model, value, per_site, "scored", 1)
    return output


def profile_h(
    data: Any,
    likelihood: Callable[..., Any],
    fit: FitResult,
    *,
    grid: Sequence[float] | np.ndarray[Any, Any] | None = None,
) -> ProfileResult:
    """Profile h over the fixed 181-point [1, 10] grid for a free-h fit."""

    if fit.model not in {"constant_free_h", "adjusted_free_h"}:
        raise ValueError("h profiles require a free-h fit")
    values_grid = (
        np.linspace(*H_BOUNDS, 181) if grid is None else np.asarray(grid, dtype=np.float64)
    )
    if (
        values_grid.ndim != 1
        or len(values_grid) < 2
        or not np.isfinite(values_grid).all()
        or (values_grid < 1).any()
        or (values_grid > 10).any()
        or (np.diff(values_grid) <= 0).any()
    ):
        raise ValueError("h profile grid must be finite, increasing, and lie in [1, 10]")
    spec = _model_spec(fit.model)
    nuisance = {"h": fit.h, "beta": fit.beta, "mu": fit.mu, "detection_sd": fit.detection_sd}
    values = np.full(len(values_grid), math.nan)
    parameters: list[dict[str, float]] = []
    statuses: list[str] = []
    nfev = 0
    warnings: list[str] = []
    start_time = time.perf_counter()
    previous_success: dict[str, float] | None = None
    for index, h in enumerate(values_grid):
        # Fix h through a reduced callback and optimize the remaining nuisance coordinates.
        profile_spec = _FreeSpec(
            tuple(name for name in spec.names if name != "logh"),
            {**_model_spec(fit.model).fixed, "h": float(h)},
        )
        start_candidates = _profile_starts(nuisance, previous_success, profile_spec)
        local = _run_fit_fixed_spec(data, likelihood, fit.model, profile_spec, start_candidates)
        values[index] = local.raw_logjoint
        parameters.append(local.parameters)
        statuses.append(local.numerical_status)
        nfev += local.nfev
        warnings.extend(local.warnings)
        if local.converged:
            previous_success = local.parameters
    finite = np.isfinite(values)
    better = bool(finite.any() and np.nanmax(values) > fit.raw_logjoint + 1e-8)
    return ProfileResult(
        "h",
        values_grid,
        values,
        tuple(parameters),
        tuple(statuses),
        nfev,
        time.perf_counter() - start_time,
        better,
        _profile_curvature(values_grid, values, statuses, log_coordinate=True),
        tuple(dict.fromkeys(warnings)),
        "log_h",
    )


def profile_beta(
    data: Any,
    likelihood: Callable[..., Any],
    fit: FitResult,
    *,
    grid: Sequence[float] | np.ndarray[Any, Any] | None = None,
) -> ProfileResult:
    """Profile beta over the fixed 81-point [-2, 2] grid for adjusted free h."""

    if fit.model != "adjusted_free_h":
        raise ValueError("beta profiles require the adjusted free-h fit")
    values_grid = (
        np.linspace(*BETA_BOUNDS, 81) if grid is None else np.asarray(grid, dtype=np.float64)
    )
    if (
        values_grid.ndim != 1
        or len(values_grid) < 2
        or not np.isfinite(values_grid).all()
        or (values_grid < -2).any()
        or (values_grid > 2).any()
        or (np.diff(values_grid) <= 0).any()
    ):
        raise ValueError("beta profile grid must be finite, increasing, and lie in [-2, 2]")
    nuisance = {"h": fit.h, "beta": fit.beta, "mu": fit.mu, "detection_sd": fit.detection_sd}
    values = np.full(len(values_grid), math.nan)
    parameters: list[dict[str, float]] = []
    statuses: list[str] = []
    nfev = 0
    warnings: list[str] = []
    start_time = time.perf_counter()
    previous_success: dict[str, float] | None = None
    for index, beta in enumerate(values_grid):
        profile_spec = _FreeSpec(("logh", "logmu", "v"), {"beta": float(beta)})
        start_candidates = _profile_starts(nuisance, previous_success, profile_spec)
        local = _run_fit_fixed_spec(
            data, likelihood, "adjusted_free_h", profile_spec, start_candidates
        )
        values[index] = local.raw_logjoint
        parameters.append(local.parameters)
        statuses.append(local.numerical_status)
        nfev += local.nfev
        warnings.extend(local.warnings)
        if local.converged:
            previous_success = local.parameters
    finite = np.isfinite(values)
    better = bool(finite.any() and np.nanmax(values) > fit.raw_logjoint + 1e-8)
    return ProfileResult(
        "beta",
        values_grid,
        values,
        tuple(parameters),
        tuple(statuses),
        nfev,
        time.perf_counter() - start_time,
        better,
        _profile_curvature(values_grid, values, statuses),
        tuple(dict.fromkeys(warnings)),
        "beta",
    )


def _run_fit_fixed_spec(
    data: Any,
    callback: Callable[..., Any],
    model: str,
    spec: _FreeSpec,
    starts: Sequence[Mapping[str, float]],
) -> FitResult:
    """Internal reduced-coordinate fit used by one-dimensional profiles."""

    start_time = time.perf_counter()
    records: list[StartRecord] = []
    warnings: list[str] = []
    bounds = _bounds(spec)

    def objective(vector: NDArray[np.float64]) -> float:
        params = _decode(vector, spec)
        try:
            value = _invoke_callback(callback, data, params)
        except (FloatingPointError, OverflowError, ValueError):
            warnings.append("likelihood callback returned an invalid value")
            return 1e300
        if not math.isfinite(value):
            warnings.append("likelihood callback returned NaN or infinity")
            return 1e300
        return -value

    outcomes: list[tuple[float, dict[str, float], bool, int]] = []
    nfev_total = 0
    for initial in starts:
        candidate = dict(initial)
        candidate.update(spec.fixed)
        candidate.setdefault("h", 1.0)
        candidate.setdefault("beta", 0.0)
        candidate.setdefault("mu", 0.002)
        candidate.setdefault("detection_sd", 0.0)
        _check_initial(candidate)
        result = minimize(
            objective,
            _encode(candidate, spec),
            method="L-BFGS-B",
            bounds=bounds,
            options=_OPT_OPTIONS,
        )
        objective_value = float(result.fun)
        valid = math.isfinite(objective_value) and objective_value < 1e299
        params = _decode(result.x, spec)
        nfev = int(getattr(result, "nfev", 0))
        nfev_total += nfev
        records.append(
            StartRecord(
                candidate,
                params,
                -objective_value if valid else math.nan,
                objective_value,
                bool(result.success) and valid,
                int(getattr(result, "status", -1)),
                str(getattr(result, "message", "")),
                nfev,
                "L-BFGS-B",
            )
        )
        if valid:
            outcomes.append((objective_value, params, bool(result.success), nfev))
    if not outcomes:
        return FitResult(
            model,
            math.nan,
            math.nan,
            math.nan,
            math.nan,
            math.nan,
            "invalid",
            nfev_total,
            time.perf_counter() - start_time,
            tuple(records),
            math.nan,
            (),
            tuple(dict.fromkeys(warnings)),
        )
    outcomes.sort(key=lambda row: (row[0], tuple(row[1].values())))
    objective_floor = outcomes[0][0]
    converged_outcomes = [outcome for outcome in outcomes if outcome[2]]
    if converged_outcomes and converged_outcomes[0][0] <= objective_floor + _SUCCESS_TIE_TOL:
        best = converged_outcomes[0]
    else:
        best = outcomes[0]
    status = "converged" if best[2] else "failed_optimizer"
    gap = math.nan if len(outcomes) < 2 else outcomes[1][0] - best[0]
    return FitResult(
        model,
        best[1]["h"],
        best[1]["beta"],
        best[1]["mu"],
        best[1]["detection_sd"],
        -best[0],
        status,
        nfev_total,
        time.perf_counter() - start_time,
        tuple(records),
        gap,
        _boundary_flags(best[1]),
        tuple(dict.fromkeys(warnings)),
    )


# Stable descriptive alias used by campaign code.
fit_all_models = fit_four_models
