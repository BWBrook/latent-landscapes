"""Global-Gamma conditional integration for exponential edge shocks.

For one realised direction of the iid unit-exponential edge proportions, a
non-source arrival is Gamma distributed with a common shape (the number of
edges) and a site-specific scale.  This module integrates those conditional
laws over the supplied direction bank.  It is a prototype kernel: it does not
generate directions or run shortest paths.
"""

from __future__ import annotations

import hashlib
import math
from numbers import Integral, Real

import numpy as np
from numpy.typing import NDArray
from scipy.special import gammainc, gammaincc

from latent_landscapes.arc2c_design import BACKGROUND_HAZARD
from latent_landscapes.arc2c_likelihood import BridgeIntegration
from latent_landscapes.goal004.observations import SURVEY_TIMES

CATEGORY_COUNT = len(SURVEY_TIMES) + 1
DEFAULT_DIRECTION_CHUNK = 128
_LOG_MAX_FLOAT = math.log(np.finfo(np.float64).max)


def _positive_finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be finite and positive")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return numeric


def _validate_interval(lower: object, upper: object) -> tuple[float, float]:
    if isinstance(lower, bool) or isinstance(upper, bool):
        raise ValueError("interval bounds must be numeric")
    try:
        lo = float(lower)
        hi = float(upper)
    except (TypeError, ValueError) as error:
        raise ValueError("interval bounds must be numeric") from error
    if not math.isfinite(lo) or lo < 0 or math.isnan(hi) or hi <= lo:
        raise ValueError("interval must satisfy 0 <= lower < upper")
    if hi != math.inf and not math.isfinite(hi):
        raise ValueError("interval upper bound must be finite or infinity")
    return lo, hi


def _logdiffexp(log_high: np.ndarray, log_low: np.ndarray) -> NDArray[np.float64]:
    """Log(exp(log_high) - exp(log_low)) for ordered non-negative tails."""
    high = np.asarray(log_high, dtype=np.float64)
    low = np.asarray(log_low, dtype=np.float64)
    result = np.full(np.broadcast_shapes(high.shape, low.shape), -np.inf, dtype=np.float64)
    high, low = np.broadcast_arrays(high, low)
    valid = np.isfinite(high) & ((low < high) | np.isneginf(low))
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        # expm1 retains the difference when the two log tails are close;
        # log1p(-exp(delta)) can round exp(delta) to one too early.
        result[valid] = high[valid] + np.log(-np.expm1(low[valid] - high[valid]))
    return result


def _log_gamma_interval_mass(
    shape: float, scales: NDArray[np.float64], lower: float, upper: float
) -> NDArray[np.float64]:
    """Stable log interval probabilities for positive Gamma scales.

    The representation follows the upper-CDF rule in the design: lower-tail
    differences are used when the upper CDF is below one half, otherwise
    survival differences are used.  The difference itself is evaluated on the
    log scale so that a narrow interval remains positive when representable.
    """
    scale_values = np.asarray(scales, dtype=np.float64)
    if scale_values.ndim == 0:
        scale_values = scale_values.reshape(1)
    if not np.isfinite(scale_values).all() or (scale_values <= 0).any():
        raise ValueError("Gamma scales must be finite and positive")
    rates = 1.0 / scale_values
    if not np.isfinite(rates).all():
        raise ValueError("Gamma scale produced a non-finite rate")
    x_lower = rates * lower
    x_upper = rates * upper
    with np.errstate(invalid="ignore", over="ignore"):
        cdf_lower = np.asarray(gammainc(shape, x_lower), dtype=np.float64)
        cdf_upper = np.asarray(gammainc(shape, x_upper), dtype=np.float64)
        sf_lower = np.asarray(gammaincc(shape, x_lower), dtype=np.float64)
        sf_upper = np.asarray(gammaincc(shape, x_upper), dtype=np.float64)
    use_cdf = cdf_upper < 0.5
    with np.errstate(divide="ignore", invalid="ignore"):
        cdf_log = _logdiffexp(np.log(cdf_upper), np.log(cdf_lower))
        sf_log = _logdiffexp(np.log(sf_lower), np.log(sf_upper))
    result = np.where(use_cdf, cdf_log, sf_log)
    if not np.isfinite(result[~np.isneginf(result)]).all():
        raise ValueError("Gamma interval calculation produced a non-finite log mass")
    return result


def _exp_log_value(log_value: float, name: str) -> float:
    if math.isnan(log_value) or log_value > _LOG_MAX_FLOAT:
        raise ValueError(f"{name} is non-finite")
    # A zero is an explicit floating-point tail underflow.  It is not replaced
    # by a floor: the corresponding mathematical probability remains positive.
    if log_value == -math.inf:
        return 0.0
    value = math.exp(log_value)
    if not math.isfinite(value):
        raise ValueError(f"{name} is non-finite")
    return value


def interval_mass(shape: float, scale: float, lower: float, upper: float) -> float:
    """Return ``P(lower < A <= upper)`` for ``A ~ Gamma(shape, scale)``.

    ``upper`` may be infinity.  This helper deliberately returns zero when a
    mathematically positive tail underflows in float64; callers must not add a
    pseudocount or positivity floor.
    """
    shape_value = _positive_finite(shape, "shape")
    scale_value = _positive_finite(scale, "scale")
    lo, hi = _validate_interval(lower, upper)
    log_value = float(_log_gamma_interval_mass(
        shape_value, np.asarray([scale_value]), lo, hi
    )[0])
    return _exp_log_value(log_value, "Gamma interval mass")


def interval_moment(
    shape: float, scale: float, lower: float, upper: float, tilt: float = 0.0
) -> float:
    """Return ``E[exp(tilt*A) 1{lower < A <= upper}]``.

    The tilted Gamma rate must be strictly positive.  The prefactor and
    interval probability are combined on the log scale to avoid the
    ``infinity * zero`` failure in rare intervals.
    """
    shape_value = _positive_finite(shape, "shape")
    scale_value = _positive_finite(scale, "scale")
    lo, hi = _validate_interval(lower, upper)
    if isinstance(tilt, bool) or not isinstance(tilt, Real):
        raise ValueError("tilt must be finite")
    tilt_value = float(tilt)
    if not math.isfinite(tilt_value):
        raise ValueError("tilt must be finite")
    rate = 1.0 / scale_value
    tilted_rate = rate - tilt_value
    if not math.isfinite(tilted_rate) or tilted_rate <= 0:
        raise ValueError("tilted Gamma rate must be finite and positive")
    tilted_scale = 1.0 / tilted_rate
    log_mass = float(_log_gamma_interval_mass(
        shape_value, np.asarray([tilted_scale]), lo, hi
    )[0])
    log_prefactor = -shape_value * math.log1p(-tilt_value / rate)
    return _exp_log_value(log_prefactor + log_mass, "tilted Gamma interval moment")


def _validate_grids(
    site_ids: tuple[str, ...], rhos: tuple[float, ...], effects: tuple[float, ...]
) -> tuple[tuple[str, ...], NDArray[np.float64], NDArray[np.float64]]:
    sites = tuple(site_ids)
    if not sites or len(set(sites)) != len(sites):
        raise ValueError("site identifiers must be non-empty and unique")
    rho_values = np.asarray(rhos, dtype=np.float64)
    effect_values = np.asarray(effects, dtype=np.float64)
    for values, name in ((rho_values, "rho"), (effect_values, "effect")):
        if (
            values.ndim != 1
            or not len(values)
            or not np.isfinite(values).all()
            or (values <= 0).any()
            or (np.diff(values) <= 0).any()
        ):
            raise ValueError(f"{name} candidates must be positive and strictly increasing")
    return sites, rho_values, effect_values


def _check_array_finite(values: NDArray[np.float64], name: str) -> None:
    if not np.isfinite(values).all():
        raise ValueError(f"conditional Gamma integration produced non-finite {name}")


def build_conditional_integration(
    scales: NDArray[np.float64],
    site_ids: tuple[str, ...],
    rhos: tuple[float, ...],
    effects: tuple[float, ...],
    shape: float,
    background_hazard: float = BACKGROUND_HAZARD,
    direction_chunk: int = DEFAULT_DIRECTION_CHUNK,
) -> BridgeIntegration:
    """Integrate a conditional Gamma arrival bank into a bridge object.

    ``scales[n, s]`` is the Gamma scale at ``rho=1`` for direction ``n`` and
    site ``s``.  A site column of all zeros denotes a source point mass at zero;
    every other column must be strictly positive in every row.  The direction
    bank is averaged before any downstream likelihood calculation.
    """
    bank = np.asarray(scales, dtype=np.float64)
    if (
        bank.ndim != 2
        or bank.shape[0] == 0
        or bank.shape[1] == 0
        or not np.isfinite(bank).all()
        or (bank < 0).any()
        or bank.shape[1] != len(site_ids)
    ):
        raise ValueError("scales must be a non-empty finite non-negative (N, site) array")
    sites, rho_values, effect_values = _validate_grids(site_ids, rhos, effects)
    shape_value = _positive_finite(shape, "shape")
    hazard = _positive_finite(background_hazard, "background hazard")
    if isinstance(direction_chunk, bool) or not isinstance(direction_chunk, Integral):
        raise ValueError("direction_chunk must be a positive integer")
    direction_chunk = int(direction_chunk)
    if direction_chunk <= 0:
        raise ValueError("direction_chunk must be a positive integer")

    source = np.all(bank == 0.0, axis=0)
    mixed_zero = np.any(bank == 0.0, axis=0) & ~source
    if mixed_zero.any():
        raise ValueError(
            "each site must be source in every direction or positive in every direction"
        )
    positive = ~source
    if positive.any():
        positive_scales = bank[:, positive]
        if (positive_scales <= 0).any():  # defensive after the mixed-zero check
            raise ValueError("non-source Gamma scales must be positive")
        base_rates = 1.0 / positive_scales
        if not np.isfinite(base_rates).all():
            raise ValueError("non-source Gamma scales produced a non-finite rate")
        for rho in rho_values:
            rates = base_rates * rho
            if not np.isfinite(rates).all() or (rates <= 0).any():
                raise ValueError("rho-scaled Gamma rates are not finite and positive")
            for effect in effect_values:
                tilted = rates - hazard * (effect - 1.0)
                if not np.isfinite(tilted).all() or (tilted <= 0).any():
                    raise ValueError("tilted Gamma rate must be finite and positive")

    direction_count, site_count = bank.shape
    category_mass = np.zeros(
        (len(rho_values), site_count, CATEGORY_COUNT), dtype=np.float64
    )
    moment_values = tuple(
        np.zeros(
            (len(effect_values), site_count, len(SURVEY_TIMES) + 1, CATEGORY_COUNT),
            dtype=np.float64,
        )
        for _ in rho_values
    )
    boundaries = (0.0, *SURVEY_TIMES)
    intervals = tuple(
        (float(boundaries[index]), float(boundaries[index + 1]))
        for index in range(len(SURVEY_TIMES))
    )
    times = np.asarray((0.0, *SURVEY_TIMES), dtype=np.float64)

    # Work one rho at a time and cap the largest direction-dependent temporary
    # at the requested chunk.  This keeps the 1,024 x 278 prototype bank small
    # even when the effect grid has 181 values.
    for rho_index, rho in enumerate(rho_values):
        masses_sum = category_mass[rho_index]
        current_moments = moment_values[rho_index]
        for start in range(0, direction_count, direction_chunk):
            chunk = bank[start : start + direction_chunk]
            chunk_count = chunk.shape[0]
            positive_chunk = chunk[:, positive] / rho
            chunk_mass = np.zeros((chunk_count, site_count, CATEGORY_COUNT), dtype=np.float64)
            if source.any():
                chunk_mass[:, source, 0] = 1.0
            if positive.any():
                positive_indices = np.flatnonzero(positive)
                for category, (lower, upper) in enumerate(intervals):
                    chunk_mass[:, positive_indices, category] = _exp_array(
                        _log_gamma_interval_mass(shape_value, positive_chunk, lower, upper),
                        "Gamma interval mass",
                    )
                chunk_mass[:, positive_indices, -1] = _exp_array(
                    _log_gamma_interval_mass(shape_value, positive_chunk, 60.0, math.inf),
                    "Gamma interval mass",
                )
            _check_array_finite(chunk_mass, "category mass")
            masses_sum += chunk_mass.sum(axis=0)

            for effect_index, effect in enumerate(effect_values):
                q = hazard * (effect - 1.0)
                for time_index, time in enumerate(times):
                    for category in range(CATEGORY_COUNT):
                        if category >= time_index:
                            contribution = chunk_mass[:, :, category] * math.exp(-hazard * time)
                        elif positive.any():
                            lower, upper = intervals[category]
                            contribution = np.zeros((chunk_count, site_count), dtype=np.float64)
                            positive_moment = _exp_array(
                                _log_tilted_interval_mass(
                                    shape_value,
                                    positive_chunk,
                                    lower,
                                    upper,
                                    q,
                                ),
                                "tilted Gamma interval moment",
                            )
                            contribution[:, positive_indices] = (
                                math.exp(-hazard * effect * time) * positive_moment
                            )
                            if source.any() and category == 0:
                                contribution[:, source] = math.exp(-hazard * effect * time)
                        else:
                            contribution = np.zeros((chunk_count, site_count), dtype=np.float64)
                            if source.any() and category == 0:
                                contribution[:, source] = math.exp(-hazard * effect * time)
                        _check_array_finite(contribution, "survival moment")
                        current_moments[effect_index, :, time_index, category] += contribution.sum(
                            axis=0
                        )

        masses_sum /= direction_count
        current_moments /= direction_count
        _check_array_finite(masses_sum, "category mass")
        _check_array_finite(current_moments, "survival moment")

    contiguous_bank = np.ascontiguousarray(bank, dtype=np.float64)
    checksum = hashlib.sha256(contiguous_bank.tobytes(order="C")).hexdigest()
    return BridgeIntegration(
        tuple(float(value) for value in rho_values),
        tuple(float(value) for value in effect_values),
        sites,
        category_mass,
        tuple(moment_values),
        checksum,
    )


def _log_tilted_interval_mass(
    shape: float,
    scales: NDArray[np.float64],
    lower: float,
    upper: float,
    tilt: float,
) -> NDArray[np.float64]:
    rates = 1.0 / np.asarray(scales, dtype=np.float64)
    tilted_rates = rates - tilt
    if not np.isfinite(tilted_rates).all() or (tilted_rates <= 0).any():
        raise ValueError("tilted Gamma rate must be finite and positive")
    tilted_scales = 1.0 / tilted_rates
    log_mass = _log_gamma_interval_mass(shape, tilted_scales, lower, upper)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_prefactor = -shape * np.log1p(-tilt / rates)
    result = log_prefactor + log_mass
    if not np.isfinite(result[~np.isneginf(result)]).all():
        raise ValueError("tilted Gamma interval moment is non-finite")
    return result


def _exp_array(log_values: NDArray[np.float64], name: str) -> NDArray[np.float64]:
    values = np.asarray(log_values, dtype=np.float64)
    if np.isnan(values).any() or (values > _LOG_MAX_FLOAT).any():
        raise ValueError(f"{name} is non-finite")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        result = np.exp(values)
    if not np.isfinite(result).all():
        raise ValueError(f"{name} is non-finite")
    return result


def build_gamma_integration(
    scales: NDArray[np.float64],
    shape: float,
    site_ids: tuple[str, ...],
    rhos: tuple[float, ...],
    effects: tuple[float, ...],
    background_hazard: float = BACKGROUND_HAZARD,
    direction_chunk: int = DEFAULT_DIRECTION_CHUNK,
) -> BridgeIntegration:
    """Build the conditional integration using the public prototype order.

    The shape precedes the grids because it is fixed by the edge count; this
    order also makes the call resemble ``Gamma(shape, scale)`` in the scalar
    helpers.  ``build_conditional_integration`` remains available for callers
    that prefer the bank-and-grids-first order.
    """
    return build_conditional_integration(
        scales,
        site_ids,
        rhos,
        effects,
        shape,
        background_hazard=background_hazard,
        direction_chunk=direction_chunk,
    )


__all__ = [
    "CATEGORY_COUNT",
    "DEFAULT_DIRECTION_CHUNK",
    "SURVEY_TIMES",
    "build_conditional_integration",
    "build_gamma_integration",
    "interval_mass",
    "interval_moment",
]
