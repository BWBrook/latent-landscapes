"""Differentiable site likelihood for the empirical-plus-pseudo arrival law.

The evaluator writes every observed-history probability as a sum of positive
components.  Within the certified series domain it uses the existing finite-
category power moments; otherwise it evaluates the same sum over the raw
arrival bank.  Both paths return analytic derivatives through third order in
the site log background hazard.
"""

from __future__ import annotations

import math
from itertools import pairwise
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import log_domain_likelihood
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.arc2c_design import DETECTION_PROBABILITY

FloatArray = NDArray[np.float64]


class LikelihoodDomainError(FloatingPointError):
    """Raised when neither a certified series nor the raw bank is available."""


def _log_loss_derivatives(z: FloatArray) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """Return log(1-exp(-z)) and three derivatives with respect to log(z)."""
    value = np.asarray(z, dtype=np.float64)
    if np.any(value <= 0.0) or not np.isfinite(value).all():
        raise FloatingPointError("loss exposure must be finite and positive")
    log_loss = np.log(-np.expm1(-value))
    first = np.empty_like(value)
    second = np.empty_like(value)
    third = np.empty_like(value)
    small = value < 1e-3
    if np.any(small):
        x = value[small]
        x2 = x * x
        x4 = x2 * x2
        x6 = x4 * x2
        x8 = x4 * x4
        x10 = x8 * x2
        first[small] = (
            1.0
            - x / 2.0
            + x2 / 12.0
            - x4 / 720.0
            + x6 / 30240.0
            - x8 / 1209600.0
            + x10 / 47900160.0
        )
        second[small] = (
            -x / 2.0
            + x2 / 6.0
            - x4 / 180.0
            + x6 / 5040.0
            - x8 / 151200.0
            + x10 / 4790016.0
        )
        third[small] = (
            -x / 2.0
            + x2 / 3.0
            - x4 / 45.0
            + x6 / 840.0
            - x8 / 18900.0
            + 10.0 * x10 / 4790016.0
        )
    if np.any(~small):
        x = value[~small]
        with np.errstate(over="ignore"):
            reciprocal = 1.0 / np.expm1(x)
        a = x * reciprocal
        first[~small] = a
        second[~small] = a * (1.0 - x - a)
        third[~small] = (
            x * (1.0 - 3.0 * x + x * x) * reciprocal
            - 3.0 * x * (1.0 - x) * reciprocal * a
            + 2.0 * a * a * a
        )
    return log_loss, first, second, third


def _mixture_summary(
    log_terms: FloatArray,
    first: FloatArray,
    second: FloatArray,
    third: FloatArray,
) -> tuple[float, float, float, float]:
    if not len(log_terms):
        raise FloatingPointError("positive mixture has no components")
    maximum = float(np.max(log_terms))
    weights = np.exp(log_terms - maximum)
    total = float(np.sum(weights))
    mean_first = float(np.dot(weights, first) / total)
    centered = first - mean_first
    return (
        maximum + math.log(total),
        mean_first,
        float(np.dot(weights, second + centered * centered) / total),
        float(
            np.dot(
                weights,
                third + 3.0 * centered * second + centered * centered * centered,
            )
            / total
        ),
    )


def _series_tail_moments(x: float, order: int) -> tuple[float, float, float, float]:
    if x == 0.0:
        return 0.0, 0.0, 0.0, 0.0
    r0 = likelihood.series_remainder_bound(x, order=order)
    r1 = x * likelihood.series_remainder_bound(x, order=order - 1)
    r2 = x * x * likelihood.series_remainder_bound(x, order=order - 2) + r1
    r3 = (
        x**3 * likelihood.series_remainder_bound(x, order=order - 3)
        + 3.0 * x * x * likelihood.series_remainder_bound(x, order=order - 2)
        + r1
    )
    return r0, r1, r2, r3


def _relative_series_tail(bank: likelihood.CompressedBank, x: float) -> float:
    if x == 0.0:
        return 0.0
    if bank.series_order < 3:
        return math.inf
    tail = max(_series_tail_moments(x, bank.series_order))
    term = 1.0
    survival = np.array(bank.power_moments[:, :, 0], copy=True)
    transition = np.zeros_like(survival)
    mass = bank.power_moments[:, :, 0]
    for degree in range(1, bank.series_order + 1):
        term *= x / degree
        moment = bank.power_moments[:, :, degree]
        survival += moment * term
        transition += (mass - moment) * term
    survival_ratio = mass * tail / survival
    transition_ratio = np.divide(
        mass * tail,
        transition,
        out=np.zeros_like(transition),
        where=transition > 0.0,
    )
    return float(max(np.max(survival_ratio), np.max(transition_ratio)))


def _certified_max_x(
    bank: likelihood.CompressedBank, tolerance: float
) -> tuple[float, float]:
    upper = float(bank.max_x)
    upper_bound = _relative_series_tail(bank, upper)
    if upper_bound <= tolerance:
        return upper, upper_bound
    lower = 0.0
    for _ in range(60):
        midpoint = (lower + upper) / 2.0
        if _relative_series_tail(bank, midpoint) <= tolerance:
            lower = midpoint
        else:
            upper = midpoint
    return lower, _relative_series_tail(bank, lower)


def _calendar_is_series_supported(observations: likelihood.PreInvasionObservations) -> bool:
    knots = (observations.cohort_start, *observations.prey_times)
    for value in knots:
        if value > 60.0:
            return False
        if 0.0 < value < 60.0 and not math.isclose(value % 10.0, 0.0, abs_tol=1e-12):
            return False
    for left, right in pairwise(knots):
        if right <= left:
            continue
        for category in range(6):
            lower = 10.0 * category
            upper = lower + 10.0
            if right <= lower or left >= upper:
                continue
            if math.isclose(left, lower, abs_tol=1e-12) and math.isclose(
                right, upper, abs_tol=1e-12
            ):
                continue
            return False
    terminal = knots[-1]
    for category in range(6):
        lower = 10.0 * category
        upper = lower + 10.0
        if terminal <= lower or terminal >= upper:
            continue
        return False
    return True


def _series_transform_summaries(
    coefficients: FloatArray, x: FloatArray
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray, NDArray[np.bool_]]:
    sites, categories, orders = coefficients.shape
    if x.shape != (sites,):
        raise ValueError("series arguments have incompatible site dimensions")
    terms = np.empty((sites, orders), dtype=np.float64)
    terms[:, 0] = 1.0
    for index in range(1, orders):
        terms[:, index] = terms[:, index - 1] * x / index
    weights = coefficients * terms[:, None, :]
    total = np.sum(weights, axis=2)
    valid = (total > 0.0) & np.isfinite(total)
    if np.any((total < 0.0) | np.isposinf(total) | np.isnan(total)):
        raise FloatingPointError("positive arrival series produced an invalid sum")
    degrees = np.arange(orders, dtype=np.float64)
    mean = np.zeros((sites, categories), dtype=np.float64)
    mean[valid] = np.sum(weights * degrees[None, None, :], axis=2)[valid] / total[valid]
    centered = degrees[None, None, :] - mean[:, :, None]
    variance = np.zeros_like(mean)
    third_central = np.zeros_like(mean)
    variance[valid] = np.sum(weights * centered * centered, axis=2)[valid] / total[valid]
    third_central[valid] = (
        np.sum(weights * centered * centered * centered, axis=2)[valid] / total[valid]
    )
    log_value = np.full_like(mean, -math.inf)
    repeated_x = np.broadcast_to(x[:, None], total.shape)
    log_value[valid] = np.log(total[valid]) - repeated_x[valid]
    return (
        log_value,
        mean - x[:, None],
        variance - x[:, None],
        third_central - x[:, None],
        valid,
    )


class DifferentiableSiteLikelihood:
    """Prepared one-history site log likelihood with analytic eta derivatives."""

    def __init__(
        self,
        observations: likelihood.PreInvasionObservations,
        bank: likelihood.CompressedBank,
        effect: float,
        log_predator: FloatArray,
        log_events: FloatArray,
        log_alive: FloatArray,
        series_available: bool,
        certified_max_x: float,
        certified_tail_bound: float,
        series_error_tolerance: float,
    ) -> None:
        self.site_ids = bank.site_ids
        self.effect = float(effect)
        self._observations = observations
        self._bank = bank
        self._log_predator = log_predator
        self._log_events = log_events
        self._log_alive = log_alive
        self._series_available = bool(series_available)
        self._certified_max_x = float(certified_max_x)
        self._has_raw = bank.bank_arrivals.shape == (bank.bank_size, len(bank.site_ids))
        if self._has_raw or effect == 1.0:
            self.numerical_domain = (-math.inf, math.inf)
        elif not series_available or certified_max_x <= 0.0:
            self.numerical_domain = (-math.inf, -math.inf)
        else:
            self.numerical_domain = (
                -math.inf,
                math.log(certified_max_x / (10.0 * (effect - 1.0))),
            )
        self.stats: dict[str, Any] = {
            "evaluations": 0,
            "cache_hits": 0,
            "series_site_evaluations": 0,
            "exact_site_evaluations": 0,
            "last_series_site_count": 0,
            "last_exact_site_count": 0,
            "last_series_site_ids": (),
            "last_exact_site_ids": (),
            "last_max_relative_tail_bound": 0.0,
            "max_observed_x": 0.0,
            "certified_max_x": float(certified_max_x),
            "certified_tail_bound": float(certified_tail_bound),
            "tail_bound_scope": "series_truncation_only_excludes_floating_roundoff",
            "series_error_tolerance": float(series_error_tolerance),
        }
        self._last_eta: FloatArray | None = None
        self._last_result: tuple[FloatArray, FloatArray, FloatArray, FloatArray] | None = None

    def _evaluate_series_site(
        self,
        site: int,
        eta: float,
        transforms: tuple[FloatArray, FloatArray, FloatArray, FloatArray],
        transitions: tuple[FloatArray, FloatArray, FloatArray, FloatArray],
        transition_valid: NDArray[np.bool_],
        losses: dict[float, tuple[float, float, float, float]],
    ) -> tuple[float, float, float, float]:
        lam = math.exp(eta)

        logs: list[float] = []
        firsts: list[float] = []
        seconds: list[float] = []
        thirds: list[float] = []

        def append(
            log_value: float, first: float, second: float, third: float
        ) -> None:
            logs.append(log_value)
            firsts.append(first)
            seconds.append(second)
            thirds.append(third)

        knots = np.asarray(
            (self._observations.cohort_start, *self._observations.prey_times),
            dtype=np.float64,
        )
        for category in range(arc2b.CATEGORY_COUNT):
            predator = float(self._log_predator[site, category])
            if not math.isfinite(predator):
                continue
            mass = float(self._bank.category_mass[site, category])
            lower = 10.0 * category
            upper = lower + 10.0
            for occasion in range(len(self._observations.prey_times)):
                event = float(self._log_events[site, occasion])
                left = float(knots[occasion])
                right = float(knots[occasion + 1])
                delta = right - left
                if not math.isfinite(event) or delta <= 0.0:
                    continue
                constant = predator + event
                if category == 6 or right <= lower:
                    loss_rows = losses[delta]
                    rate = left - self._observations.cohort_start
                    append(
                        constant + math.log(mass) - lam * rate + loss_rows[0],
                        -lam * rate + loss_rows[1],
                        -lam * rate + loss_rows[2],
                        -lam * rate + loss_rows[3],
                    )
                elif left >= upper:
                    transform = tuple(row[category] for row in transforms)
                    rate = (
                        left
                        - self._observations.cohort_start
                        + (self.effect - 1.0) * (left - upper)
                    )
                    loss_rows = losses[self.effect * delta]
                    append(
                        constant + transform[0] - lam * rate + loss_rows[0],
                        transform[1] - lam * rate + loss_rows[1],
                        transform[2] - lam * rate + loss_rows[2],
                        transform[3] - lam * rate + loss_rows[3],
                    )
                elif math.isclose(left, lower, abs_tol=1e-12) and math.isclose(
                    right, upper, abs_tol=1e-12
                ):
                    loss_rows = losses[delta]
                    rate = left - self._observations.cohort_start
                    append(
                        constant + math.log(mass) - lam * rate + loss_rows[0],
                        -lam * rate + loss_rows[1],
                        -lam * rate + loss_rows[2],
                        -lam * rate + loss_rows[3],
                    )
                    if transition_valid[category]:
                        transition = tuple(row[category] for row in transitions)
                        rate = right - self._observations.cohort_start
                        append(
                            constant + transition[0] - lam * rate,
                            transition[1] - lam * rate,
                            transition[2] - lam * rate,
                            transition[3] - lam * rate,
                        )
                else:
                    raise ValueError("prey calendar is not supported by the positive series")

            alive = float(self._log_alive[site])
            if not math.isfinite(alive):
                continue
            terminal = float(knots[-1])
            constant = predator + alive
            if category == 6 or terminal <= lower:
                rate = terminal - self._observations.cohort_start
                append(
                    constant + math.log(mass) - lam * rate,
                    -lam * rate,
                    -lam * rate,
                    -lam * rate,
                )
            elif terminal >= upper:
                transform = tuple(row[category] for row in transforms)
                rate = (
                    terminal
                    - self._observations.cohort_start
                    + (self.effect - 1.0) * (terminal - upper)
                )
                append(
                    constant + transform[0] - lam * rate,
                    transform[1] - lam * rate,
                    transform[2] - lam * rate,
                    transform[3] - lam * rate,
                )
            else:
                raise ValueError("terminal prey time is not supported by the positive series")
        return _mixture_summary(
            np.asarray(logs), np.asarray(firsts), np.asarray(seconds), np.asarray(thirds)
        )

    def _evaluate_series(
        self, eta: FloatArray, selected_sites: NDArray[np.bool_]
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
        selected = np.flatnonzero(selected_sites)
        hazards = np.exp(eta[selected])
        x = 10.0 * hazards * (self.effect - 1.0)
        moments = self._bank.power_moments[selected]
        transform_rows = _series_transform_summaries(moments, x)
        if not np.all(transform_rows[4]):
            raise FloatingPointError("survival arrival transform has zero mass")
        differences = np.maximum(moments[:, :, :1] - moments, 0.0)
        differences[:, :, 0] = 0.0
        transition_rows = _series_transform_summaries(differences, x)
        intervals = np.diff(
            np.asarray(
                (self._observations.cohort_start, *self._observations.prey_times),
                dtype=np.float64,
            )
        )
        exposures = sorted(
            {float(value) for value in intervals if value > 0.0}
            | {float(self.effect * value) for value in intervals if value > 0.0}
        )
        loss_rows = _log_loss_derivatives(hazards[:, None] * np.asarray(exposures)[None, :])
        value = np.full(len(self.site_ids), math.nan)
        d1 = np.full_like(value, math.nan)
        d2 = np.full_like(value, math.nan)
        d3 = np.full_like(value, math.nan)
        for local, site_value in enumerate(selected):
            losses = {
                exposure: (
                    float(loss_rows[0][local, index]),
                    float(loss_rows[1][local, index]),
                    float(loss_rows[2][local, index]),
                    float(loss_rows[3][local, index]),
                )
                for index, exposure in enumerate(exposures)
            }
            result = self._evaluate_series_site(
                int(site_value),
                float(eta[site_value]),
                tuple(row[local] for row in transform_rows[:4]),
                tuple(row[local] for row in transition_rows[:4]),
                transition_rows[4][local],
                losses,
            )
            value[site_value], d1[site_value], d2[site_value], d3[site_value] = result
        return value, d1, d2, d3

    def _evaluate_raw_site(self, site: int, eta: float) -> tuple[float, float, float, float]:
        arrivals = np.concatenate(
            (
                self._bank.bank_arrivals[:, site],
                np.asarray(arc2b.PSEUDO_ARRIVALS, dtype=np.float64),
            )
        )
        categories = np.searchsorted(
            np.asarray(likelihood.DEFAULT_PREDATOR_TIMES), arrivals, side="left"
        )
        predator = self._log_predator[site, categories]
        lam = math.exp(eta)
        knots = np.asarray(
            (self._observations.cohort_start, *self._observations.prey_times),
            dtype=np.float64,
        )
        exposure = (
            knots[:, None]
            - self._observations.cohort_start
            + (self.effect - 1.0) * np.maximum(knots[:, None] - arrivals[None, :], 0.0)
        )
        groups: list[tuple[float, float, float, float]] = []
        for occasion in range(len(self._observations.prey_times)):
            event = float(self._log_events[site, occasion])
            delta = exposure[occasion + 1] - exposure[occasion]
            valid = np.isfinite(predator) & (delta > 0.0)
            if not math.isfinite(event) or not np.any(valid):
                continue
            left = exposure[occasion, valid]
            z = lam * delta[valid]
            loss = _log_loss_derivatives(z)
            log_terms = event + predator[valid] - lam * left + loss[0]
            first = -lam * left + loss[1]
            second = -lam * left + loss[2]
            third = -lam * left + loss[3]
            groups.append(_mixture_summary(log_terms, first, second, third))
        alive = float(self._log_alive[site])
        valid = np.isfinite(predator)
        if math.isfinite(alive) and np.any(valid):
            terminal = exposure[-1, valid]
            groups.append(
                _mixture_summary(
                    alive + predator[valid] - lam * terminal,
                    -lam * terminal,
                    -lam * terminal,
                    -lam * terminal,
                )
            )
        if not groups:
            raise FloatingPointError(
                f"site {self.site_ids[site]} has zero observed-history probability"
            )
        group_array = np.asarray(groups, dtype=np.float64)
        result = _mixture_summary(
            group_array[:, 0],
            group_array[:, 1],
            group_array[:, 2],
            group_array[:, 3],
        )
        return (
            result[0] - math.log(self._bank.bank_size + arc2b.CATEGORY_COUNT),
            result[1],
            result[2],
            result[3],
        )

    def evaluate(
        self, eta: NDArray[Any]
    ) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
        """Return site log likelihood and derivatives one through three."""
        point = np.asarray(eta, dtype=np.float64)
        if point.shape != (len(self.site_ids),) or not np.isfinite(point).all():
            raise ValueError("eta must be finite with one value per site")
        self.stats["evaluations"] = int(self.stats["evaluations"]) + 1
        if self._last_eta is not None and np.array_equal(point, self._last_eta):
            assert self._last_result is not None
            self.stats["cache_hits"] = int(self.stats["cache_hits"]) + 1
            self.stats["last_series_site_count"] = 0
            self.stats["last_exact_site_count"] = 0
            self.stats["last_series_site_ids"] = ()
            self.stats["last_exact_site_ids"] = ()
            self.stats["last_max_relative_tail_bound"] = 0.0
            return self._last_result
        with np.errstate(over="ignore"):
            hazards = np.exp(point)
        if not np.isfinite(hazards).all():
            raise LikelihoodDomainError("eta implies a nonfinite site hazard")
        x = 10.0 * hazards * (self.effect - 1.0)
        if not self._series_available:
            series = np.zeros(len(self.site_ids), dtype=bool)
        elif self.effect == 1.0:
            series = np.ones(len(self.site_ids), dtype=bool)
        else:
            series = np.asarray(x <= self._certified_max_x, dtype=bool)
        exact = ~series
        if np.any(exact) and not self._has_raw:
            ids = tuple(self.site_ids[index] for index in np.flatnonzero(exact))
            raise LikelihoodDomainError(
                "positive-series derivative domain exceeded without raw arrivals: "
                + ", ".join(ids[:5])
            )
        value = np.empty(len(self.site_ids), dtype=np.float64)
        d1 = np.empty_like(value)
        d2 = np.empty_like(value)
        d3 = np.empty_like(value)
        if np.any(series):
            evaluated = self._evaluate_series(point, series)
            value[series], d1[series], d2[series], d3[series] = (
                row[series] for row in evaluated
            )
            max_x = float(np.max(x[series]))
            tail_bound = _relative_series_tail(self._bank, max_x)
        else:
            tail_bound = 0.0
        for site in np.flatnonzero(exact):
            value[site], d1[site], d2[site], d3[site] = self._evaluate_raw_site(
                int(site), float(point[site])
            )
        if not all(np.isfinite(row).all() for row in (value, d1, d2, d3)):
            raise FloatingPointError("differentiable likelihood produced nonfinite output")
        series_ids = tuple(self.site_ids[index] for index in np.flatnonzero(series))
        exact_ids = tuple(self.site_ids[index] for index in np.flatnonzero(exact))
        self.stats["series_site_evaluations"] = int(
            self.stats["series_site_evaluations"]
        ) + len(series_ids)
        self.stats["exact_site_evaluations"] = int(
            self.stats["exact_site_evaluations"]
        ) + len(exact_ids)
        self.stats["last_series_site_count"] = len(series_ids)
        self.stats["last_exact_site_count"] = len(exact_ids)
        self.stats["last_series_site_ids"] = series_ids
        self.stats["last_exact_site_ids"] = exact_ids
        self.stats["last_max_relative_tail_bound"] = tail_bound
        self.stats["max_observed_x"] = max(
            float(self.stats["max_observed_x"]), float(np.max(x))
        )
        result = (
            np.ascontiguousarray(value),
            np.ascontiguousarray(d1),
            np.ascontiguousarray(d2),
            np.ascontiguousarray(d3),
        )
        for row in result:
            row.setflags(write=False)
        self._last_eta = np.array(point, copy=True)
        self._last_eta.setflags(write=False)
        self._last_result = result
        return result


def prepare_site_likelihood(
    observations: likelihood.PreInvasionObservations,
    bank: likelihood.CompressedBank,
    effect: float,
    *,
    detection_probability: float = DETECTION_PROBABILITY,
    detection_sd: float = 0.0,
    series_error_tolerance: float = 1e-10,
) -> DifferentiableSiteLikelihood:
    """Prepare a one-history differentiable likelihood for a fixed effect."""
    if observations.site_ids != bank.site_ids:
        raise ValueError("observation and bank site identifiers must agree")
    if observations.prey_counts.shape[0] != 1:
        raise ValueError("differentiable site likelihood requires exactly one history")
    if not math.isfinite(effect) or effect < 1.0:
        raise ValueError("effect must be finite and at least one")
    if not 0.0 < detection_probability < 1.0 or not 0.0 <= detection_sd < math.sqrt(
        detection_probability * (1.0 - detection_probability)
    ):
        raise ValueError("detection parameters are outside the Beta domain")
    if not math.isfinite(series_error_tolerance) or series_error_tolerance <= 0.0:
        raise ValueError("series_error_tolerance must be finite and positive")
    log_predator = log_domain_likelihood._log_predator_emissions(
        observations.predator_counts,
        float(detection_probability),
        observations.predator_observed,
    )[0]
    log_events_3d, log_alive_2d = log_domain_likelihood._log_prey_emissions(
        observations.prey_counts,
        float(detection_probability),
        float(detection_sd),
    )
    log_domain_likelihood._apply_initial_state(
        log_events_3d,
        log_alive_2d,
        observations.prey_counts,
        observations.initial_alive,
    )
    log_events = log_events_3d[0]
    log_alive = log_alive_2d[0]
    series_available = _calendar_is_series_supported(observations)
    certified_x = 0.0
    certified_bound = math.inf
    if series_available:
        moments = np.asarray(bank.power_moments, dtype=np.float64)
        expected_shape = (len(bank.site_ids), 6, bank.series_order + 1)
        if moments.shape != expected_shape or not np.isfinite(moments).all():
            raise ValueError("arrival power moments have invalid shape or values")
        if np.any(moments < 0.0):
            raise ValueError("arrival power moments must be nonnegative")
        mass = moments[:, :, :1]
        negative = mass - moments
        tolerance = 32.0 * np.finfo(float).eps * np.maximum(mass, 1.0)
        if np.any(negative < -tolerance):
            raise ValueError("arrival power moments violate nonnegative transition weights")
        certified_x, certified_bound = _certified_max_x(bank, series_error_tolerance)
    has_raw = bank.bank_arrivals.shape == (bank.bank_size, len(bank.site_ids))
    if not series_available and not has_raw:
        raise ValueError("unsupported prey calendar requires the raw arrival bank")
    return DifferentiableSiteLikelihood(
        observations,
        bank,
        float(effect),
        log_predator,
        log_events,
        log_alive,
        series_available,
        certified_x,
        certified_bound,
        float(series_error_tolerance),
    )


__all__ = [
    "DifferentiableSiteLikelihood",
    "LikelihoodDomainError",
    "prepare_site_likelihood",
]
