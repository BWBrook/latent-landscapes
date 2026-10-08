"""Observed-data likelihood for the pre-invasion calendar.

This module is deliberately array based.  It keeps the analyst boundary small:
the caller supplies site identifiers, observation counts and a training mask;
latent arrivals are integrated over the unchanged alpha=1 bank law.  The
post-invasion part is compatible with :mod:`arc2c_likelihood`, while the
pre-invasion extension carries the same cohort through day zero.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.special import gammainc  # type: ignore[import-untyped]

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes.adjusted_background_likelihood import normalized_hazards
from latent_landscapes.arc2c_design import DETECTION_PROBABILITY
from latent_landscapes.goal004.observations import SURVEY_TIMES

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
DEFAULT_PREY_TIMES = tuple(float(-60 + 10 * i) for i in range(13))
DEFAULT_PREDATOR_TIMES = tuple(float(value) for value in SURVEY_TIMES)
SERIES_ORDER = 48
SERIES_DOMAIN = 5.0


def _as_counts(value: Any, name: str, shape_tail: tuple[int, ...]) -> NDArray[np.int64]:
    array = np.asarray(value)
    if array.ndim != 3 or array.shape[2:] != shape_tail:
        raise ValueError(f"{name} must have shape (history, site, occasion)")
    if not np.issubdtype(array.dtype, np.integer) or not np.isin(array, (0, 1, 2)).all():
        raise ValueError(f"{name} must contain integer two-visit counts 0, 1 or 2")
    return np.asarray(array, dtype=np.int64)


def _times(value: Sequence[float], name: str, *, expected: int | None = None) -> tuple[float, ...]:
    values = tuple(float(x) for x in value)
    if expected is not None and len(values) != expected:
        raise ValueError(f"{name} must contain {expected} occasions")
    if not values or not np.isfinite(values).all() or any(b <= a for a, b in pairwise(values)):
        raise ValueError(f"{name} must be finite and strictly increasing")
    return values


@dataclass(frozen=True, slots=True)
class PreInvasionObservations:
    """Sorted observation-only arrays and the declared initial state."""

    site_ids: tuple[str, ...]
    prey_counts: IntArray  # history x site x prey occasion
    predator_counts: IntArray  # history x site x post-invasion occasion
    training_mask: NDArray[np.bool_]  # site-valued, kept separate from counts
    initial_alive: NDArray[np.bool_]
    prey_times: tuple[float, ...] = DEFAULT_PREY_TIMES
    predator_times: tuple[float, ...] = DEFAULT_PREDATOR_TIMES
    cohort_start: float = -60.0
    predator_emissions: FloatArray | None = None

    def __post_init__(self) -> None:
        if self.prey_counts.shape[:2] != self.predator_counts.shape[:2]:
            raise ValueError("prey and predator history/site dimensions must agree")
        if self.prey_counts.shape[2] != len(self.prey_times) or self.predator_counts.shape[
            2
        ] != len(self.predator_times):
            raise ValueError("count arrays and occasion calendars must agree")
        if self.training_mask.shape != (self.prey_counts.shape[1],):
            raise ValueError("training_mask must have one value per site")
        if self.initial_alive.shape != (self.prey_counts.shape[1],):
            raise ValueError("initial_alive must be site-valued")
        if self.predator_emissions is not None and self.predator_emissions.shape != (
            self.prey_counts.shape[0],
            self.prey_counts.shape[1],
            arc2b.CATEGORY_COUNT,
        ):
            raise ValueError("predator_emissions shape does not match observations")


def prepare_observations(
    prey_counts: NDArray[Any],
    predator_counts: NDArray[Any],
    site_ids: Sequence[str],
    training_mask: NDArray[Any] | Sequence[bool],
    *,
    initial_alive: NDArray[Any] | Sequence[bool] | bool = True,
    prey_times: Sequence[float] = DEFAULT_PREY_TIMES,
    predator_times: Sequence[float] = DEFAULT_PREDATOR_TIMES,
    cohort_start: float = -60.0,
) -> PreInvasionObservations:
    """Validate and return counts with sites in deterministic identifier order."""
    prey = _as_counts(prey_counts, "prey_counts", (len(tuple(prey_times)),))
    predator = _as_counts(predator_counts, "predator_counts", (len(tuple(predator_times)),))
    ids = tuple(str(value) for value in site_ids)
    if len(ids) != prey.shape[1] or len(set(ids)) != len(ids) or any(not value for value in ids):
        raise ValueError("site_ids must be unique nonempty identifiers matching the arrays")
    order = np.argsort(np.asarray(ids), kind="stable")
    sorted_ids = tuple(ids[index] for index in order)
    mask = np.asarray(training_mask, dtype=bool)
    if mask.shape == prey.shape[:2]:
        if not np.all(mask == mask[0]):
            raise ValueError("training_mask must be site-valued, not history-varying")
        mask = mask[0]
    if mask.shape != (prey.shape[1],):
        raise ValueError("training_mask must have one value per site")
    mask = mask[order]
    initial = np.asarray(initial_alive, dtype=bool)
    if initial.ndim == 0:
        initial = np.full(prey.shape[1], bool(initial), dtype=bool)
    elif initial.shape == (prey.shape[1],):
        initial = initial[order]
    else:
        raise ValueError("initial_alive must be scalar or site-valued")
    prey_times_tuple = _times(prey_times, "prey_times")
    predator_times_tuple = _times(predator_times, "predator_times", expected=6)
    if not math.isfinite(cohort_start):
        raise ValueError("cohort_start must be finite")
    if prey_times_tuple[0] < cohort_start:
        raise ValueError("prey_times cannot precede cohort_start")
    predator_emissions = _predator_emissions(predator)
    predator_emissions.setflags(write=False)
    result = PreInvasionObservations(
        sorted_ids,
        np.ascontiguousarray(prey[:, order]),
        np.ascontiguousarray(predator[:, order]),
        np.ascontiguousarray(mask),
        np.ascontiguousarray(initial),
        prey_times_tuple,
        predator_times_tuple,
        float(cohort_start),
        predator_emissions,
    )
    for array in (
        result.prey_counts,
        result.predator_counts,
        result.training_mask,
        result.initial_alive,
    ):
        array.setflags(write=False)
    return result


@dataclass(frozen=True, slots=True)
class CompressedBank:
    """Alpha=1 arrival bank with exact finite-category power sums."""

    site_ids: tuple[str, ...]
    bank_size: int
    category_counts: NDArray[np.int64]
    category_mass: FloatArray
    power_moments: FloatArray  # site x six finite categories x (SERIES_ORDER + 1)
    bank_arrivals: FloatArray
    bank_checksum: str
    series_order: int = SERIES_ORDER
    max_x: float = SERIES_DOMAIN


def _validate_sites(site_ids: Sequence[str], count: int) -> tuple[str, ...]:
    ids = tuple(str(value) for value in site_ids)
    if len(ids) != count or len(set(ids)) != count or any(not value for value in ids):
        raise ValueError("site_ids must be unique nonempty identifiers matching the bank")
    return ids


def compress_bank(
    bank: NDArray[Any], site_ids: Sequence[str], *, series_order: int = SERIES_ORDER
) -> CompressedBank:
    """Compress each finite category without averaging arrival times.

    The returned moments include all empirical arrivals and one pseudo-arrival
    in each of the seven categories, divided by ``K + 7``.  Category six is
    intentionally represented only by its mass: it remains background-only for
    every planned post-invasion occasion.
    """
    arrivals = np.asarray(bank, dtype=np.float64)
    if (
        arrivals.ndim != 2
        or not arrivals.shape[0]
        or not np.isfinite(arrivals).all()
        or (arrivals < 0).any()
    ):
        raise ValueError("bank must be a nonempty finite nonnegative matrix")
    if series_order < 0:
        raise ValueError("series_order must be nonnegative")
    ids = _validate_sites(site_ids, arrivals.shape[1])
    categories = np.searchsorted(np.asarray(SURVEY_TIMES), arrivals, side="left")
    counts = np.empty((len(ids), arc2b.CATEGORY_COUNT), dtype=np.int64)
    denominator = arrivals.shape[0] + arc2b.CATEGORY_COUNT
    masses = np.empty_like(counts, dtype=np.float64)
    moments = np.zeros((len(ids), len(SURVEY_TIMES), series_order + 1), dtype=np.float64)
    for site, _ in enumerate(ids):
        counts[site] = np.bincount(categories[:, site], minlength=arc2b.CATEGORY_COUNT)
        masses[site] = (counts[site] + 1.0) / denominator
        for category in range(len(SURVEY_TIMES)):
            lower = 10.0 * category
            values = arrivals[categories[:, site] == category, site]
            pseudo = float(arc2b.PSEUDO_ARRIVALS[category])
            u = np.concatenate(((values - lower) / 10.0, np.asarray([(pseudo - lower) / 10.0])))
            moments[site, category] = np.asarray(
                [
                    float(np.sum(np.power(u, k), dtype=np.float64)) / denominator
                    for k in range(series_order + 1)
                ]
            )
    for array in (counts, masses, moments):
        array.setflags(write=False)
    copy = np.ascontiguousarray(arrivals)
    copy.setflags(write=False)
    return CompressedBank(
        ids,
        arrivals.shape[0],
        counts,
        masses,
        moments,
        copy,
        hashlib.sha256(copy.view(np.uint8)).hexdigest(),
        series_order,
    )


def prepare_bank(bank: NDArray[Any], site_ids: Sequence[str]) -> CompressedBank:
    """Alias for :func:`compress_bank`."""
    return compress_bank(bank, site_ids)


def _poisson_tail(order: int, x: float) -> float:
    return float(gammainc(order + 1, x))


def series_remainder_bound(x: float, *, order: int = SERIES_ORDER) -> float:
    """Return the requested absolute bound ``exp(x) * PoissonSF(order, x)``."""
    if not math.isfinite(x) or x < 0:
        raise ValueError("x must be finite and nonnegative")
    return math.exp(x) * _poisson_tail(order, x)


@dataclass(frozen=True, slots=True)
class PreInvasionIntegration:
    effects: tuple[float, ...]
    site_ids: tuple[str, ...]
    category_mass: FloatArray
    survival_moments: FloatArray  # effect x site x (1 + prey occasion) x category
    prey_times: tuple[float, ...]
    cohort_start: float
    bank: CompressedBank
    hazards: FloatArray
    exact: bool = False
    series_bound: float = 0.0


def build_integration(
    bank: CompressedBank | NDArray[Any],
    effects: Sequence[float],
    site_hazards: NDArray[Any],
    *,
    site_ids: Sequence[str] | None = None,
    prey_times: Sequence[float] = DEFAULT_PREY_TIMES,
    cohort_start: float = -60.0,
    exact: bool = False,
    enforce_domain: bool = True,
) -> PreInvasionIntegration:
    """Build exact calendar moments for candidate effect multipliers."""
    prepared = bank if isinstance(bank, CompressedBank) else compress_bank(bank, site_ids or ())
    if site_ids is not None and tuple(site_ids) != prepared.site_ids:
        raise ValueError("site_ids do not match the prepared bank")
    times = _times(prey_times, "prey_times")
    if times[0] < cohort_start:
        raise ValueError("prey_times cannot precede cohort_start")
    candidates = tuple(float(value) for value in effects)
    if (
        not candidates
        or not np.isfinite(candidates).all()
        or any(value < 1.0 for value in candidates)
    ):
        raise ValueError("effects must be finite and at least one")
    hazards = np.asarray(site_hazards, dtype=np.float64)
    if (
        hazards.shape != (len(prepared.site_ids),)
        or not np.isfinite(hazards).all()
        or (hazards <= 0).any()
    ):
        raise ValueError("site hazards must be finite, positive and match site identifiers")
    knots = (float(cohort_start), *times)
    knot_array = np.asarray(knots, dtype=np.float64)
    moments = np.empty(
        (len(candidates), len(prepared.site_ids), len(knots), arc2b.CATEGORY_COUNT)
    )
    max_bound = 0.0
    if not exact:
        lower_edges = 10.0 * np.arange(len(SURVEY_TIMES), dtype=np.float64)
        upper_edges = lower_edges + 10.0
        interior = (knot_array[:, None] > lower_edges) & (knot_array[:, None] < upper_edges)
        if np.any(interior):
            raise ValueError("compressed integration requires knots on the arrival-category edges")
    else:
        category_values: tuple[tuple[FloatArray, ...], ...] = tuple(
            tuple(
                np.concatenate(
                    (
                        prepared.bank_arrivals[
                            np.searchsorted(
                                SURVEY_TIMES, prepared.bank_arrivals[:, site], side="left"
                            )
                            == category,
                            site,
                        ],
                        np.asarray([arc2b.PSEUDO_ARRIVALS[category]], dtype=np.float64),
                    )
                )
                for category in range(len(SURVEY_TIMES) + 1)
            )
            for site in range(len(prepared.site_ids))
        )
    for hi, effect in enumerate(candidates):
        x_values = 10.0 * hazards * (effect - 1.0)
        if not exact:
            x_max = float(np.max(x_values))
            if enforce_domain and x_max > prepared.max_x * (1.0 + 1e-14):
                raise ValueError(
                    f"compressed series domain exceeded: x={x_max:g} > {prepared.max_x:g}"
                )
            max_bound = max(max_bound, series_remainder_bound(x_max, order=prepared.series_order))
            # Evaluate the truncated exponential series iteratively without a
            # bank-sized operation or per-site Python loop.
            transformed = np.zeros((len(hazards), len(SURVEY_TIMES)), dtype=np.float64)
            term = np.ones_like(x_values)
            transformed += prepared.power_moments[:, :, 0] * term[:, None]
            for degree in range(1, prepared.series_order + 1):
                term *= x_values / degree
                transformed += prepared.power_moments[:, :, degree] * term[:, None]
            transformed *= np.exp(-x_values)[:, None]
            base = np.exp(-hazards[None, :, None] * (knot_array[None, None, :] - cohort_start))
            edge = np.exp(
                -hazards[None, :, None, None]
                * (knot_array[None, None, :, None] - cohort_start)
                - (effect - 1.0)
                * hazards[None, :, None, None]
                * (knot_array[None, None, :, None] - upper_edges[None, None, None, :])
            )
            after = knot_array[None, None, :, None] > lower_edges[None, None, None, :]
            moments[hi, :, :, : len(SURVEY_TIMES)] = np.where(
                after,
                edge * transformed[None, :, None, :],
                base[:, :, :, None] * prepared.category_mass[None, :, None, : len(SURVEY_TIMES)],
            )[0]
            moments[hi, :, :, -1] = base[0] * prepared.category_mass[:, -1, None]
            continue
        for site, hazard in enumerate(hazards):
            if exact:
                base = np.exp(-float(hazard) * (knot_array - cohort_start))
                moments[hi, site] = base[:, None] * prepared.category_mass[site][None, :]
                for category in range(len(SURVEY_TIMES)):
                    lower = 10.0 * category
                    upper = lower + 10.0
                    after_lower = knot_array > lower
                    interior = after_lower & (knot_array < upper)
                    if np.any(interior):
                        values = category_values[site][category]
                        for ti_value in np.flatnonzero(interior):
                            ti = int(ti_value)
                            survival = np.exp(
                                -float(hazard)
                                * (
                                    knot_array[ti]
                                    - cohort_start
                                    + (effect - 1.0)
                                    * np.maximum(knot_array[ti] - values, 0.0)
                                )
                            )
                            moments[hi, site, ti, category] = float(
                                np.sum(survival) / (prepared.bank_size + arc2b.CATEGORY_COUNT)
                            )
                        after_lower &= ~interior
                    if np.any(after_lower):
                        values = category_values[site][category]
                        transform = float(
                            np.sum(
                                np.exp(-float(hazard) * (effect - 1.0) * (upper - values))
                            )
                            / (prepared.bank_size + arc2b.CATEGORY_COUNT)
                        )
                        edge = np.exp(
                            -float(hazard) * (knot_array - cohort_start)
                            - float(hazard) * (effect - 1.0) * (knot_array - upper)
                        )
                        moments[hi, site, after_lower, category] = edge[after_lower] * transform
                continue
            base = np.exp(-float(hazard) * (knot_array - cohort_start))
            moments[hi, site] = base[:, None] * prepared.category_mass[site][None, :]
            for category in range(len(SURVEY_TIMES)):
                lower = 10.0 * category
                upper = lower + 10.0
                after_lower = knot_array > lower
                interior = after_lower & (knot_array < upper)
                if np.any(interior):
                    # This is outside the registered calendar, but retaining
                    # the direct fallback keeps the helper correct for audits.
                    for ti_value in np.flatnonzero(interior):
                        ti = int(ti_value)
                        survival = np.exp(
                            -float(hazard)
                            * (
                                knot_array[ti]
                                - cohort_start
                                + (effect - 1.0)
                                * np.maximum(knot_array[ti] - category_values[site][category], 0.0)
                            )
                        )
                        moments[hi, site, ti, category] = float(
                            np.sum(survival) / (prepared.bank_size + arc2b.CATEGORY_COUNT)
                        )
                    after_lower = after_lower & ~interior
                if np.any(after_lower):
                    values = category_values[site][category]
                    transformed = float(
                        np.sum(
                            np.exp(-float(hazard) * (effect - 1.0) * (upper - values))
                        )
                        / (prepared.bank_size + arc2b.CATEGORY_COUNT)
                    )
                    edge = np.exp(
                        -float(hazard) * (knot_array - cohort_start)
                        - float(hazard) * (effect - 1.0) * (knot_array - upper)
                    )
                    moments[hi, site, after_lower, category] = edge[after_lower] * transformed
    if not np.isfinite(moments).all() or (moments < 0).any():
        raise RuntimeError("pre-invasion survival moments are invalid")
    return PreInvasionIntegration(
        candidates,
        prepared.site_ids,
        prepared.category_mass,
        moments,
        times,
        float(cohort_start),
        prepared,
        hazards.copy(),
        exact,
        max_bound,
    )


def build_exact_integration(*args: Any, **kwargs: Any) -> PreInvasionIntegration:
    kwargs["exact"] = True
    kwargs["enforce_domain"] = False
    return build_integration(*args, **kwargs)


def _shared_probability(counts: NDArray[np.int64], p: float, sd: float, visits: int) -> float:
    total = int(np.sum(counts))
    n = visits * len(counts)
    if sd == 0.0:
        return float(
            np.prod(
                [
                    math.comb(visits, int(k)) * p ** int(k) * (1.0 - p) ** (visits - int(k))
                    for k in counts
                ]
            )
        )
    inv_kappa = sd * sd / (p * (1.0 - p) - sd * sd)
    log_value = total * math.log(p) + (n - total) * math.log1p(-p)
    log_value += math.fsum(math.log(math.comb(visits, int(k))) for k in counts)
    log_value += math.fsum(math.log1p(i * inv_kappa / p) for i in range(total))
    log_value += math.fsum(math.log1p(i * inv_kappa / (1.0 - p)) for i in range(n - total))
    log_value -= math.fsum(math.log1p(i * inv_kappa) for i in range(n))
    return float(math.exp(log_value))


def one_probability_shared_all_visits(
    counts: NDArray[Any], p: float = DETECTION_PROBABILITY, sd: float = 0.0
) -> float:
    """Probability of one site's complete prey count sequence under shared Beta detection."""
    values = np.asarray(counts, dtype=np.int64)
    if values.ndim != 1 or not np.isin(values, (0, 1, 2)).all():
        raise ValueError("counts must be a one-dimensional two-visit sequence")
    if not 0 < p < 1 or not 0 <= sd < math.sqrt(p * (1 - p)):
        raise ValueError("detection mean and SD are outside the Beta domain")
    return _shared_probability(values, float(p), float(sd), 2)


def _prey_emissions(counts: IntArray, p: float, sd: float) -> tuple[FloatArray, FloatArray]:
    n, sites, occasions = counts.shape
    log_comb = np.log(np.asarray((1.0, 2.0, 1.0), dtype=np.float64))[counts]
    cumulative_comb = np.cumsum(log_comb, axis=2)
    cumulative_total = np.cumsum(counts, axis=2, dtype=np.int64)
    total = cumulative_total[:, :, -1]
    if sd == 0.0:
        log_p = np.log(p)
        log_q = math.log1p(-p)
        alive = np.exp(
            cumulative_comb[:, :, -1]
                + total * log_p
                + (2 * occasions - total) * log_q
        )
        events = np.zeros((n, sites, occasions), dtype=np.float64)
        for prefix in range(occasions):
            valid = np.all(counts[:, :, prefix:] == 0, axis=2)
            if prefix:
                events[:, :, prefix] = np.exp(
                    cumulative_comb[:, :, prefix - 1]
                    + cumulative_total[:, :, prefix - 1] * log_p
                    + (2 * prefix - cumulative_total[:, :, prefix - 1]) * log_q
                ) * valid
            else:
                events[:, :, prefix] = valid
        return events, alive
    inv_kappa = sd * sd / (p * (1.0 - p) - sd * sd)
    max_count = 2 * occasions
    rising_a = np.asarray(
        [math.fsum(math.log1p(i * inv_kappa / p) for i in range(k)) for k in range(max_count + 1)]
    )
    rising_b = np.asarray(
        [
            math.fsum(math.log1p(i * inv_kappa / (1.0 - p)) for i in range(k))
            for k in range(max_count + 1)
        ]
    )
    rising_d = np.asarray(
        [math.fsum(math.log1p(i * inv_kappa) for i in range(k)) for k in range(max_count + 1)]
    )
    total_all = total
    alive_log = (
        cumulative_comb[:, :, -1]
        + total_all * math.log(p)
        + (max_count - total_all) * math.log1p(-p)
        + rising_a[total_all]
        + rising_b[max_count - total_all]
        - rising_d[max_count]
    )
    alive = np.exp(alive_log)
    events = np.zeros((n, sites, occasions), dtype=np.float64)
    for prefix in range(occasions):
        valid = np.all(counts[:, :, prefix:] == 0, axis=2)
        if prefix:
            prefix_total = cumulative_total[:, :, prefix - 1]
            events[:, :, prefix] = np.exp(
                cumulative_comb[:, :, prefix - 1]
                + prefix_total * math.log(p)
                + (2 * prefix - prefix_total) * math.log1p(-p)
                + rising_a[prefix_total]
                + rising_b[2 * prefix - prefix_total]
                - rising_d[2 * prefix]
            ) * valid
        else:
            events[:, :, prefix] = valid
    return events, alive


def _apply_initial_state(
    events: FloatArray, alive: FloatArray, counts: IntArray, initial_alive: NDArray[np.bool_]
) -> None:
    """Apply the supplied known state at cohort start in place."""
    state = np.broadcast_to(initial_alive[None, :], counts.shape[:2])
    dead = ~state
    all_zero = np.all(counts == 0, axis=2)
    alive[dead] = all_zero[dead].astype(np.float64)
    events[dead, :] = all_zero[dead, None].astype(np.float64)


def _predator_emissions(counts: IntArray, p: float = DETECTION_PROBABILITY) -> FloatArray:
    n, sites, occasions = counts.shape
    log_prob = np.log(np.asarray([(1.0 - p) ** 2, p * (1.0 - p) * 2.0, p**2]))
    occasion_log = log_prob[counts]
    cumulative = np.cumsum(occasion_log, axis=2)
    result = np.empty((n, sites, arc2b.CATEGORY_COUNT), dtype=np.float64)
    for category in range(arc2b.CATEGORY_COUNT):
        occupied = cumulative[:, :, -1] if category == 0 else cumulative[:, :, category:]
        if category == 0:
            result[:, :, category] = np.exp(occupied)
        else:
            valid = np.all(counts[:, :, : min(category, occasions)] == 0, axis=2)
            result[:, :, category] = (
                np.exp(cumulative[:, :, -1] - cumulative[:, :, category - 1]) * valid
            )
    return result


@dataclass(frozen=True, slots=True)
class LikelihoodScores:
    joint_loglikelihood: FloatArray  # history x effect x site
    predator_loglikelihood: FloatArray  # history x site
    conditional_prey_loglikelihood: FloatArray  # history x effect x site
    training_logjoint: FloatArray  # history x effect
    holdout_logjoint: FloatArray  # history x effect
    holdout_predator: FloatArray  # history
    series_bound: float

    def __iter__(self) -> Any:
        """Allow the familiar ``training, holdout, predator`` unpacking."""
        yield self.training_logjoint
        yield self.holdout_logjoint
        yield self.holdout_predator


@dataclass(frozen=True, slots=True)
class PointScore:
    """Scalar fitting result plus sitewise arrays for diagnostics."""

    training_logjoint: float
    training_site_logjoint: FloatArray
    holdout_site_logjoint: FloatArray
    conditional_prey_site_loglikelihood: FloatArray
    predator_site_loglikelihood: FloatArray
    integration: PreInvasionIntegration


def build_parameter_integration(
    bank: CompressedBank | NDArray[Any],
    effect: float,
    beta: float,
    mean_hazard: float,
    all_map_A: NDArray[Any],
    site_A: NDArray[Any],
    *,
    site_ids: Sequence[str] | None = None,
    prey_times: Sequence[float] = DEFAULT_PREY_TIMES,
    cohort_start: float = -60.0,
    exact: bool = False,
) -> PreInvasionIntegration:
    """Construct one fitting point after whole-map hazard normalization."""
    prepared = bank if isinstance(bank, CompressedBank) else compress_bank(bank, site_ids or ())
    hazards = normalized_hazards(beta, np.asarray(all_map_A), np.asarray(site_A), mean_hazard)
    return build_integration(
        prepared,
        (float(effect),),
        hazards,
        prey_times=prey_times,
        cohort_start=cohort_start,
        exact=exact,
    )


def point_score(
    observations: PreInvasionObservations,
    bank: CompressedBank | NDArray[Any],
    effect: float,
    beta: float,
    mean_hazard: float,
    all_map_A: NDArray[Any],
    site_A: NDArray[Any],
    *,
    detection_probability: float = DETECTION_PROBABILITY,
    detection_sd: float = 0.0,
    exact: bool = False,
) -> PointScore:
    """Score one ``(h, beta, mean, SD)`` point with a scalar fit target."""
    integration = build_parameter_integration(
        bank,
        effect,
        beta,
        mean_hazard,
        all_map_A,
        site_A,
        site_ids=observations.site_ids,
        prey_times=observations.prey_times,
        cohort_start=observations.cohort_start,
        exact=exact,
    )
    scores = score_observations(
        observations,
        integration,
        detection_probability=detection_probability,
        detection_sd=detection_sd,
    )
    train_site = scores.joint_loglikelihood[:, 0] * observations.training_mask
    holdout_site = scores.joint_loglikelihood[:, 0] * ~observations.training_mask
    return PointScore(
        float(scores.training_logjoint[0, 0]),
        train_site,
        holdout_site,
        scores.conditional_prey_loglikelihood[:, 0],
        scores.predator_loglikelihood,
        integration,
    )


def score_observations(
    observations: PreInvasionObservations,
    integration: PreInvasionIntegration,
    *,
    detection_probability: float = DETECTION_PROBABILITY,
    detection_sd: float = 0.0,
) -> LikelihoodScores:
    """Evaluate joint, predator and conditional-prey scores for every site."""
    if observations.site_ids != integration.site_ids:
        raise ValueError("observation and integration site identifiers must agree")
    if (
        observations.prey_times != integration.prey_times
        or observations.cohort_start != integration.cohort_start
    ):
        raise ValueError("observation and integration calendars must agree")
    if not 0 < detection_probability < 1 or not 0 <= detection_sd < math.sqrt(
        detection_probability * (1 - detection_probability)
    ):
        raise ValueError("detection parameters are outside the Beta domain")
    pred = (
        observations.predator_emissions
        if detection_probability == DETECTION_PROBABILITY
        and observations.predator_emissions is not None
        else _predator_emissions(observations.predator_counts, detection_probability)
    )
    events, alive = _prey_emissions(observations.prey_counts, detection_probability, detection_sd)
    _apply_initial_state(events, alive, observations.prey_counts, observations.initial_alive)
    n, sites = observations.prey_counts.shape[:2]
    effects = len(integration.effects)
    joint = np.empty((n, effects, sites), dtype=np.float64)
    pred_prob = np.einsum("sc,nsc->ns", integration.category_mass, pred, optimize=True)
    for h in range(effects):
        weighted = np.einsum("stc,nsc->nst", integration.survival_moments[h], pred, optimize=True)
        event_prob = np.einsum(
            "nst,nst->ns",
            weighted[:, :, :-1] - weighted[:, :, 1:],
            events,
            optimize=True,
        )
        event_prob += weighted[:, :, -1] * alive
        if not np.isfinite(event_prob).all() or (event_prob <= 0).any():
            raise RuntimeError("pre-invasion likelihood produced invalid probabilities")
        joint[:, h] = np.log(event_prob)
    pred_log = np.log(pred_prob)
    conditional = joint - pred_log[:, None, :]
    training = np.broadcast_to(
        observations.training_mask[None, :], observations.prey_counts.shape[:2]
    )
    training_joint = np.einsum("nhs,ns->nh", joint, training, optimize=True)
    holdout_joint = np.einsum("nhs,ns->nh", joint, ~training, optimize=True)
    holdout_predator = np.einsum("ns,ns->n", pred_log, ~training, optimize=True)
    return LikelihoodScores(
        joint,
        pred_log,
        conditional,
        training_joint,
        holdout_joint,
        holdout_predator,
        integration.series_bound,
    )


def evaluate_dataset(*args: Any, **kwargs: Any) -> LikelihoodScores:
    return score_observations(*args, **kwargs)


def joint_log_likelihood(
    observations: PreInvasionObservations,
    integration: PreInvasionIntegration,
    **kwargs: Any,
) -> FloatArray:
    """Return the scalar training joint log likelihood per history/effect."""
    return score_observations(observations, integration, **kwargs).training_logjoint


def pre_only_log_likelihood(
    observations: PreInvasionObservations,
    hazards: NDArray[Any] | None = None,
    *,
    detection_probability: float = DETECTION_PROBABILITY,
    detection_sd: float = 0.0,
    return_site: bool = True,
) -> FloatArray:
    """Analytic no-arrival scorer for the first seven prey occasions."""
    required_times = tuple(float(-60 + 10 * i) for i in range(7))
    if (
        observations.cohort_start != -60.0
        or len(observations.prey_times) < 7
        or observations.prey_times[:7] != required_times
    ):
        raise ValueError("pre-only scoring requires prey times -60 through 0 and cohort_start=-60")
    if hazards is None:
        raise ValueError("hazards are required for pre-only scoring")
    rates = np.asarray(hazards, dtype=np.float64)
    if (
        rates.shape != (len(observations.site_ids),)
        or not np.isfinite(rates).all()
        or (rates <= 0).any()
    ):
        raise ValueError("hazards must match the observation sites")
    events, alive = _prey_emissions(
        observations.prey_counts[:, :, :7], detection_probability, detection_sd
    )
    _apply_initial_state(
        events,
        alive,
        observations.prey_counts[:, :, :7],
        observations.initial_alive,
    )
    start = observations.cohort_start
    times = observations.prey_times[:7]
    survival = np.exp(-rates[None, :, None] * (np.asarray(times)[None, None, :] - start))
    event_slice = events[:, :, 1:7] if times[0] == start else events[:, :, :6]
    terms = np.einsum(
        "nsj,nsj->ns",
        survival[:, :, :-1] - survival[:, :, 1:],
        event_slice,
        optimize=True,
    )
    terms += survival[:, :, -1] * alive
    result = np.asarray(np.log(terms), dtype=np.float64)
    if return_site:
        return result
    return np.asarray(
        (result * observations.training_mask[None, :]).sum(axis=1), dtype=np.float64
    )


def oracle_arrival_scores(
    observations: PreInvasionObservations,
    arrivals: NDArray[Any],
    effects: Sequence[float],
    hazards: NDArray[Any],
    *,
    detection_probability: float = DETECTION_PROBABILITY,
    detection_sd: float = 0.0,
) -> LikelihoodScores:
    """Evaluate scores conditional on supplied site arrivals for diagnostics."""
    arrival = np.asarray(arrivals, dtype=np.float64)
    if arrival.ndim == 1:
        arrival = np.broadcast_to(
            arrival[None, :], (observations.prey_counts.shape[0], len(observations.site_ids))
        )
    if (
        arrival.shape != observations.prey_counts.shape[:2]
        or not np.isfinite(arrival).all()
        or (arrival < 0).any()
    ):
        raise ValueError("arrivals must be nonnegative and history-by-site")
    rates = np.asarray(hazards, dtype=np.float64)
    if rates.shape != (len(observations.site_ids),):
        raise ValueError("hazards must match observation sites")
    candidates = tuple(float(value) for value in effects)
    knots = (observations.cohort_start, *observations.prey_times)
    events, alive = _prey_emissions(observations.prey_counts, detection_probability, detection_sd)
    _apply_initial_state(events, alive, observations.prey_counts, observations.initial_alive)
    joint = np.empty(
        (observations.prey_counts.shape[0], len(candidates), len(observations.site_ids))
    )
    for h, effect in enumerate(candidates):
        event_probability = np.empty(
            (observations.prey_counts.shape[0], len(observations.site_ids))
        )
        for site, rate in enumerate(rates):
            survival = np.exp(
                -rate
                * (
                    np.asarray(knots)[None, :]
                    - observations.cohort_start
                    + (effect - 1.0)
                    * np.maximum(np.asarray(knots)[None, :] - arrival[:, site, None], 0.0)
                )
            )
            event_probability[:, site] = (
                np.einsum(
                    "nj,nj->n", survival[:, :-1] - survival[:, 1:], events[:, site], optimize=True
                )
                + survival[:, -1] * alive[:, site]
            )
        pred_prob = np.empty_like(event_probability)
        for i in range(pred_prob.shape[0]):
            for site, time_arrival in enumerate(arrival[i]):
                pred_prob[i, site] = np.prod(
                    [
                        (
                            math.comb(2, int(count))
                            * detection_probability ** int(count)
                            * (1.0 - detection_probability) ** (2 - int(count))
                            if time_arrival <= time
                            else float(count == 0)
                        )
                        for time, count in zip(
                            observations.predator_times,
                            observations.predator_counts[i, site],
                            strict=True,
                        )
                    ]
                )
        joint[:, h] = np.log(event_probability * pred_prob)
    pred_log = np.log(pred_prob)
    conditional = joint - pred_log[:, None, :]
    train = np.broadcast_to(
        observations.training_mask[None, :], observations.prey_counts.shape[:2]
    )
    return LikelihoodScores(
        joint,
        pred_log,
        conditional,
        np.einsum("nhs,ns->nh", joint, train),
        np.einsum("nhs,ns->nh", joint, ~train),
        np.einsum("ns,ns->n", pred_log, ~train),
        0.0,
    )


oracle_arrivals = oracle_arrival_scores


__all__ = [
    "DEFAULT_PREY_TIMES",
    "SERIES_DOMAIN",
    "SERIES_ORDER",
    "CompressedBank",
    "LikelihoodScores",
    "PointScore",
    "PreInvasionIntegration",
    "PreInvasionObservations",
    "build_exact_integration",
    "build_integration",
    "build_parameter_integration",
    "compress_bank",
    "evaluate_dataset",
    "joint_log_likelihood",
    "normalized_hazards",
    "one_probability_shared_all_visits",
    "oracle_arrival_scores",
    "oracle_arrivals",
    "point_score",
    "pre_only_log_likelihood",
    "prepare_bank",
    "prepare_observations",
    "score_observations",
    "series_remainder_bound",
]
