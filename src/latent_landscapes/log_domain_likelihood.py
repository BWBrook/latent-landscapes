"""Exact raw-bank reference likelihood evaluated entirely in log space.

This is a numerical reference kernel, not the production profile engine.  It
preserves the current empirical arrival law: every raw arrival draw and one
pseudo-arrival in each of the seven canonical categories receive mass
``1 / (K + 7)``.  No series approximation, model-domain bound or curve
smoothing is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.special import logsumexp  # type: ignore[import-untyped]

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import preinvasion_likelihood as probability_likelihood
from latent_landscapes.arc2c_design import DETECTION_PROBABILITY

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True, slots=True)
class LogDomainQuadrature:
    """Raw-arrival survival and loss masses under the empirical-plus-pseudo law."""

    effects: tuple[float, ...]
    site_ids: tuple[str, ...]
    log_category_mass: FloatArray  # site x category
    log_survival_moments: FloatArray  # effect x site x knot x category
    log_loss_moments: FloatArray  # effect x site x prey occasion x category
    prey_times: tuple[float, ...]
    cohort_start: float
    hazards: FloatArray
    bank_size: int
    bank_checksum: str


@dataclass(frozen=True, slots=True)
class LogDomainScores:
    """Sitewise and splitwise observed-history log likelihoods."""

    joint_loglikelihood: FloatArray  # history x effect x site
    predator_loglikelihood: FloatArray  # history x site
    conditional_prey_loglikelihood: FloatArray  # history x effect x site
    training_logjoint: FloatArray  # history x effect
    holdout_logjoint: FloatArray  # history x effect
    holdout_predator: FloatArray  # history


def _validated_times(values: tuple[float, ...] | list[float]) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result or not np.isfinite(result).all() or any(b <= a for a, b in pairwise(result)):
        raise ValueError("prey_times must be finite and strictly increasing")
    return result


def _log1mexp_nonpositive(value: FloatArray) -> FloatArray:
    """Return ``log(1 - exp(value))`` for nonpositive log ratios."""
    values = np.asarray(value, dtype=np.float64)
    if np.any(values > 0.0) or np.isnan(values).any():
        raise RuntimeError("survival increased across a loss interval")
    result = np.full(values.shape, -math.inf, dtype=np.float64)
    negative = values < 0.0
    split = -math.log(2.0)
    moderately_negative = negative & (values <= split)
    near_zero = negative & ~moderately_negative
    result[moderately_negative] = np.log1p(-np.exp(values[moderately_negative]))
    result[near_zero] = np.log(-np.expm1(values[near_zero]))
    return result


def build_log_quadrature(
    bank: probability_likelihood.CompressedBank,
    effects: tuple[float, ...] | list[float],
    site_hazards: NDArray[Any],
    *,
    prey_times: tuple[float, ...] | list[float] = probability_likelihood.DEFAULT_PREY_TIMES,
    cohort_start: float = -60.0,
) -> LogDomainQuadrature:
    """Integrate the exact raw arrival bank without probability-scale arithmetic."""
    ids = tuple(bank.site_ids)
    arrivals = np.asarray(bank.bank_arrivals, dtype=np.float64)
    if arrivals.shape != (bank.bank_size, len(ids)):
        raise ValueError("log-domain quadrature requires every raw arrival draw")
    if not np.isfinite(arrivals).all() or np.any(arrivals < 0.0):
        raise ValueError("raw arrivals must be finite and nonnegative")
    candidates = tuple(float(value) for value in effects)
    if (
        not candidates
        or not np.isfinite(candidates).all()
        or any(value < 1.0 for value in candidates)
    ):
        raise ValueError("effects must be finite and at least one")
    hazards = np.asarray(site_hazards, dtype=np.float64)
    if (
        hazards.shape != (len(ids),)
        or not np.isfinite(hazards).all()
        or np.any(hazards <= 0.0)
    ):
        raise ValueError("site hazards must be finite, positive and match site identifiers")
    times = _validated_times(prey_times)
    if not math.isfinite(cohort_start) or times[0] < cohort_start:
        raise ValueError("cohort_start must be finite and no later than the first prey time")

    knots = np.asarray((float(cohort_start), *times), dtype=np.float64)
    categories = np.searchsorted(
        np.asarray(probability_likelihood.DEFAULT_PREDATOR_TIMES), arrivals, side="left"
    )
    denominator = bank.bank_size + arc2b.CATEGORY_COUNT
    log_denominator = math.log(denominator)
    log_mass = np.empty((len(ids), arc2b.CATEGORY_COUNT), dtype=np.float64)
    log_survival = np.empty(
        (len(candidates), len(ids), len(knots), arc2b.CATEGORY_COUNT), dtype=np.float64
    )
    log_loss = np.empty(
        (len(candidates), len(ids), len(times), arc2b.CATEGORY_COUNT), dtype=np.float64
    )

    for site, hazard in enumerate(hazards):
        for category, pseudo in enumerate(arc2b.PSEUDO_ARRIVALS):
            empirical = arrivals[categories[:, site] == category, site]
            category_arrivals = np.concatenate(
                (empirical, np.asarray([pseudo], dtype=np.float64))
            )
            log_mass[site, category] = math.log(len(category_arrivals)) - log_denominator
            post_arrival = np.maximum(
                knots[:, None] - category_arrivals[None, :], 0.0
            )
            for effect_index, effect in enumerate(candidates):
                exposure = (
                    knots[:, None]
                    - float(cohort_start)
                    + (effect - 1.0) * post_arrival
                )
                with np.errstate(over="ignore"):
                    log_draw_survival = -float(hazard) * exposure
                    log_ratio = -float(hazard) * np.diff(exposure, axis=0)
                log_survival[effect_index, site, :, category] = (
                    logsumexp(log_draw_survival, axis=1) - log_denominator
                )
                log_draw_loss = (
                    log_draw_survival[:-1] + _log1mexp_nonpositive(log_ratio)
                )
                log_loss[effect_index, site, :, category] = (
                    logsumexp(log_draw_loss, axis=1) - log_denominator
                )

    for array in (log_mass, log_survival, log_loss):
        array.setflags(write=False)
    hazard_copy = np.ascontiguousarray(hazards)
    hazard_copy.setflags(write=False)
    return LogDomainQuadrature(
        candidates,
        ids,
        log_mass,
        log_survival,
        log_loss,
        times,
        float(cohort_start),
        hazard_copy,
        int(bank.bank_size),
        str(bank.bank_checksum),
    )


def _log_prey_emissions(
    counts: IntArray,
    p: float,
    sd: float,
    observed: NDArray[np.bool_] | None = None,
) -> tuple[FloatArray, FloatArray]:
    n, sites, occasions = counts.shape
    effective, cumulative_comb, cumulative_total, cumulative_trials = (
        probability_likelihood._prey_observation_statistics(counts, observed)
    )
    max_count = 2 * occasions
    total = cumulative_total[:, :, -1]
    trials = cumulative_trials[:, :, -1]
    log_p = math.log(p)
    log_q = math.log1p(-p)

    if sd == 0.0:
        alive = cumulative_comb[:, :, -1] + total * log_p + (trials - total) * log_q
        events = np.full((n, sites, occasions), -math.inf, dtype=np.float64)
        for prefix in range(occasions):
            valid = np.all(effective[:, :, prefix:] == 0, axis=2)
            if prefix:
                prefix_total = cumulative_total[:, :, prefix - 1]
                prefix_trials = cumulative_trials[:, :, prefix - 1]
                value = (
                    cumulative_comb[:, :, prefix - 1]
                    + prefix_total * log_p
                    + (prefix_trials - prefix_total) * log_q
                )
                events[:, :, prefix] = np.where(valid, value, -math.inf)
            else:
                events[:, :, prefix] = np.where(valid, 0.0, -math.inf)
        return events, alive

    inv_kappa = sd * sd / (p * (1.0 - p) - sd * sd)
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
    alive = (
        cumulative_comb[:, :, -1]
        + total * log_p
        + (trials - total) * log_q
        + rising_a[total]
        + rising_b[trials - total]
        - rising_d[trials]
    )
    events = np.full((n, sites, occasions), -math.inf, dtype=np.float64)
    for prefix in range(occasions):
        valid = np.all(effective[:, :, prefix:] == 0, axis=2)
        if prefix:
            prefix_total = cumulative_total[:, :, prefix - 1]
            prefix_trials = cumulative_trials[:, :, prefix - 1]
            value = (
                cumulative_comb[:, :, prefix - 1]
                + prefix_total * log_p
                + (prefix_trials - prefix_total) * log_q
                + rising_a[prefix_total]
                + rising_b[prefix_trials - prefix_total]
                - rising_d[prefix_trials]
            )
            events[:, :, prefix] = np.where(valid, value, -math.inf)
        else:
            events[:, :, prefix] = np.where(valid, 0.0, -math.inf)
    return events, alive


def _apply_initial_state(
    events: FloatArray,
    alive: FloatArray,
    counts: IntArray,
    initial_alive: NDArray[np.bool_],
    observed: NDArray[np.bool_] | None = None,
) -> None:
    dead = ~np.broadcast_to(initial_alive[None, :], counts.shape[:2])
    all_zero = np.all(counts == 0 if observed is None else (~observed) | (counts == 0), axis=2)
    alive[dead] = np.where(all_zero[dead], 0.0, -math.inf)
    events[dead, :] = np.where(all_zero[dead, None], 0.0, -math.inf)


def _log_predator_emissions(
    counts: IntArray,
    p: float,
    observed: NDArray[np.bool_] | None,
) -> FloatArray:
    if observed is None:
        available = np.ones(counts.shape, dtype=bool)
    else:
        available = np.asarray(observed)
        if available.shape != counts.shape or available.dtype != np.dtype(bool):
            raise ValueError("predator_observed must be boolean and match predator_counts shape")
    log_probability = np.log(np.asarray(((1.0 - p) ** 2, 2.0 * p * (1.0 - p), p**2)))
    occasion_log = np.where(available, log_probability[counts], 0.0)
    n, sites, occasions = counts.shape
    result = np.empty((n, sites, arc2b.CATEGORY_COUNT), dtype=np.float64)
    result[:, :, 0] = occasion_log.sum(axis=2)
    for category in range(1, arc2b.CATEGORY_COUNT):
        before = min(category, occasions)
        valid = np.all(
            (~available[:, :, :before]) | (counts[:, :, :before] == 0), axis=2
        )
        after = occasion_log[:, :, category:].sum(axis=2)
        result[:, :, category] = np.where(valid, after, -math.inf)
    return result


def score_observations(
    observations: probability_likelihood.PreInvasionObservations,
    quadrature: LogDomainQuadrature,
    *,
    detection_probability: float = DETECTION_PROBABILITY,
    detection_sd: float = 0.0,
) -> LogDomainScores:
    """Score observed histories using log-domain emission-mixture quadrature."""
    if observations.site_ids != quadrature.site_ids:
        raise ValueError("observation and quadrature site identifiers must agree")
    if (
        observations.prey_times != quadrature.prey_times
        or observations.cohort_start != quadrature.cohort_start
    ):
        raise ValueError("observation and quadrature calendars must agree")
    if not 0.0 < detection_probability < 1.0 or not 0.0 <= detection_sd < math.sqrt(
        detection_probability * (1.0 - detection_probability)
    ):
        raise ValueError("detection parameters are outside the Beta domain")

    log_predator = _log_predator_emissions(
        observations.predator_counts,
        float(detection_probability),
        observations.predator_observed,
    )
    log_events, log_alive = _log_prey_emissions(
        observations.prey_counts,
        float(detection_probability),
        float(detection_sd),
        observations.prey_observed,
    )
    _apply_initial_state(
        log_events,
        log_alive,
        observations.prey_counts,
        observations.initial_alive,
        observations.prey_observed,
    )
    predator_marginal = logsumexp(
        quadrature.log_category_mass[None, :, :] + log_predator, axis=2
    )
    histories, sites = observations.prey_counts.shape[:2]
    joint = np.empty((histories, len(quadrature.effects), sites), dtype=np.float64)
    for effect_index in range(len(quadrature.effects)):
        log_loss = logsumexp(
            quadrature.log_loss_moments[effect_index][None, :, :, :]
            + log_predator[:, :, None, :],
            axis=3,
        )
        log_terminal = logsumexp(
            quadrature.log_survival_moments[effect_index, :, -1, :][None, :, :]
            + log_predator,
            axis=2,
        )
        terms = np.concatenate(
            (
                log_loss + log_events,
                (log_terminal + log_alive)[:, :, None],
            ),
            axis=2,
        )
        joint[:, effect_index, :] = logsumexp(terms, axis=2)
    if np.isnan(joint).any() or np.isposinf(joint).any():
        raise RuntimeError("log-domain likelihood produced invalid log probabilities")

    conditional = joint - predator_marginal[:, None, :]
    training = np.asarray(observations.training_mask, dtype=bool)
    training_joint = joint[:, :, training].sum(axis=2)
    holdout_joint = joint[:, :, ~training].sum(axis=2)
    holdout_predator = predator_marginal[:, ~training].sum(axis=1)
    return LogDomainScores(
        joint,
        predator_marginal,
        conditional,
        training_joint,
        holdout_joint,
        holdout_predator,
    )


def exact_log_scores(
    observations: probability_likelihood.PreInvasionObservations,
    bank: probability_likelihood.CompressedBank,
    effects: tuple[float, ...] | list[float],
    site_hazards: NDArray[Any],
    *,
    detection_probability: float = DETECTION_PROBABILITY,
    detection_sd: float = 0.0,
) -> LogDomainScores:
    """Build raw-bank quadrature and score it in one reference call."""
    quadrature = build_log_quadrature(
        bank,
        effects,
        site_hazards,
        prey_times=observations.prey_times,
        cohort_start=observations.cohort_start,
    )
    return score_observations(
        observations,
        quadrature,
        detection_probability=detection_probability,
        detection_sd=detection_sd,
    )


__all__ = [
    "LogDomainQuadrature",
    "LogDomainScores",
    "build_log_quadrature",
    "exact_log_scores",
    "score_observations",
]
