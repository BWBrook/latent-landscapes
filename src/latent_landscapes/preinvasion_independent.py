"""Independent analytic likelihood for the pre-invasion observations.

This audit implementation intentionally does not import the production
pre-invasion likelihood, its emission helpers, or its hazard normalizer.  It
enumerates the possible cohort-loss intervals directly and integrates the
persistent site-level detection probability with the Beta-function identity.
"""

from __future__ import annotations

import math
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
PRE_ONLY_TIMES = tuple(float(-60 + 10 * index) for index in range(7))
DEFAULT_DETECTION_PROBABILITY = 0.65


class PreOnlyObservations(Protocol):
    """Observation fields required by the independent calculation."""

    @property
    def site_ids(self) -> tuple[str, ...]: ...

    @property
    def prey_counts(self) -> IntArray: ...

    @property
    def training_mask(self) -> NDArray[np.bool_]: ...

    @property
    def initial_alive(self) -> NDArray[np.bool_]: ...

    @property
    def prey_times(self) -> tuple[float, ...]: ...

    @property
    def cohort_start(self) -> float: ...


def _logsumexp(values: FloatArray, *, axis: int) -> FloatArray:
    maximum = np.max(values, axis=axis, keepdims=True)
    finite = np.isfinite(maximum)
    shifted = np.where(finite, values - maximum, -np.inf)
    total = np.sum(np.exp(shifted), axis=axis, keepdims=True)
    result = np.where(finite, maximum + np.log(total), -np.inf)
    return np.asarray(np.squeeze(result, axis=axis), dtype=np.float64)


def _site_hazards(
    beta: float,
    mu: float,
    all_map_a: NDArray[Any],
    site_a: NDArray[Any],
) -> FloatArray:
    whole = np.asarray(all_map_a, dtype=np.float64)
    sites = np.asarray(site_a, dtype=np.float64)
    if (
        not math.isfinite(beta)
        or not math.isfinite(mu)
        or mu <= 0.0
        or whole.ndim not in (1, 2)
        or not whole.size
        or not np.isfinite(whole).all()
        or sites.ndim != 1
        or not sites.size
        or not np.isfinite(sites).all()
    ):
        raise ValueError("beta, mu and complete-map/site covariates must be valid")

    scaled = beta * whole
    shift = float(np.max(scaled))
    log_normalizer = shift + math.log(float(np.mean(np.exp(scaled - shift))))
    log_hazards = math.log(mu) + beta * sites - log_normalizer
    hazards = np.exp(log_hazards)
    if not np.isfinite(hazards).all() or (hazards <= 0.0).any():
        raise ValueError("normalized site hazards are non-finite or non-positive")
    return np.asarray(hazards, dtype=np.float64)


def _prefix_log_emissions(
    counts: IntArray,
    detection_probability: float,
    detection_sd: float,
) -> FloatArray:
    """Return log Pr(first m count occasions), for m=1,...,7."""
    cumulative_successes = np.cumsum(counts, axis=2, dtype=np.int64)
    cumulative_log_combinations = np.cumsum(
        np.where(counts == 1, math.log(2.0), 0.0), axis=2
    )
    occasion_count = np.arange(1, counts.shape[2] + 1, dtype=np.int64)
    trials = 2 * occasion_count[None, None, :]
    failures = trials - cumulative_successes

    p = detection_probability
    if detection_sd == 0.0:
        return np.asarray(
            cumulative_log_combinations
            + cumulative_successes * math.log(p)
            + failures * math.log1p(-p),
            dtype=np.float64,
        )

    # The Beta-function ratio B(alpha+k, beta+n-k) / B(alpha, beta)
    # equals a ratio of rising factorials.  Expressing those factors as
    # log1p increments is stable all the way to the SD=0 boundary, unlike
    # subtracting large log-gamma values when the concentration is high.
    variance = detection_sd * detection_sd
    inverse_concentration = variance / (p * (1.0 - p) - variance)
    max_count = 2 * counts.shape[2]
    rising_alpha = np.asarray(
        [
            math.fsum(math.log1p(index * inverse_concentration / p) for index in range(k))
            for k in range(max_count + 1)
        ]
    )
    rising_beta = np.asarray(
        [
            math.fsum(
                math.log1p(index * inverse_concentration / (1.0 - p))
                for index in range(k)
            )
            for k in range(max_count + 1)
        ]
    )
    rising_total = np.asarray(
        [
            math.fsum(math.log1p(index * inverse_concentration) for index in range(k))
            for k in range(max_count + 1)
        ]
    )
    return np.asarray(
        cumulative_log_combinations
        + cumulative_successes * math.log(p)
        + failures * math.log1p(-p)
        + rising_alpha[cumulative_successes]
        + rising_beta[failures]
        - rising_total[trials],
        dtype=np.float64,
    )


def independent_pre_log_likelihood(
    observations: PreOnlyObservations,
    all_map_a: NDArray[Any],
    site_a: NDArray[Any],
    *,
    beta: float,
    mu: float,
    detection_sd: float,
    detection_probability: float = DEFAULT_DETECTION_PROBABILITY,
    return_site: bool = False,
) -> FloatArray:
    """Score the complete pre-only history without production likelihood code.

    The latent cohort is known alive at day -60 unless ``initial_alive`` says
    otherwise.  For an initially alive site, the calculation sums the six
    possible loss intervals (-60,-50] through (-10,0] and survival through day
    0.  Detection probability is fixed when ``detection_sd == 0``; otherwise a
    single site-level Beta draw persists over all visits.

    The result is history by site when ``return_site`` is true and one summed
    training likelihood per history otherwise.
    """
    if (
        not 0.0 < detection_probability < 1.0
        or not math.isfinite(detection_sd)
        or detection_sd < 0.0
        or detection_sd >= math.sqrt(detection_probability * (1.0 - detection_probability))
    ):
        raise ValueError("detection mean and SD are outside the Beta domain")
    if (
        observations.cohort_start != -60.0
        or len(observations.prey_times) < len(PRE_ONLY_TIMES)
        or observations.prey_times[: len(PRE_ONLY_TIMES)] != PRE_ONLY_TIMES
    ):
        raise ValueError("independent pre-only scoring requires prey times -60 through 0")

    counts_raw = np.asarray(observations.prey_counts[:, :, :7])
    if (
        counts_raw.ndim != 3
        or counts_raw.shape[1] != len(observations.site_ids)
        or not np.issubdtype(counts_raw.dtype, np.integer)
        or not np.isin(counts_raw, (0, 1, 2)).all()
    ):
        raise ValueError("prey counts must be history by site by occasion counts 0, 1 or 2")
    counts = np.asarray(counts_raw, dtype=np.int64)
    sites = counts.shape[1]
    training = np.asarray(observations.training_mask, dtype=bool)
    initial_alive = np.asarray(observations.initial_alive, dtype=bool)
    if training.shape != (sites,) or initial_alive.shape != (sites,):
        raise ValueError("training mask and initial state must contain one value per site")

    hazards = _site_hazards(beta, mu, all_map_a, site_a)
    if hazards.shape != (sites,):
        raise ValueError("site covariates must contain one value per observation site")
    prefix_emissions = _prefix_log_emissions(counts, detection_probability, detection_sd)

    # Path m=1,...,6 denotes loss after occasion m-1 and before occasion m.
    # The seventh path denotes survival through the final pre-only occasion.
    path_logs = np.full((*counts.shape[:2], 7), -np.inf, dtype=np.float64)
    interval = PRE_ONLY_TIMES[1] - PRE_ONLY_TIMES[0]
    log_interval_factor = np.log(-np.expm1(-hazards * interval))
    for prefix in range(1, 7):
        suffix_is_zero = np.all(counts[:, :, prefix:] == 0, axis=2)
        elapsed = PRE_ONLY_TIMES[prefix - 1] - observations.cohort_start
        log_weight = -hazards * elapsed + log_interval_factor
        path_logs[:, :, prefix - 1] = np.where(
            suffix_is_zero,
            prefix_emissions[:, :, prefix - 1] + log_weight[None, :],
            -np.inf,
        )
    final_elapsed = PRE_ONLY_TIMES[-1] - observations.cohort_start
    path_logs[:, :, -1] = prefix_emissions[:, :, -1] - hazards[None, :] * final_elapsed
    site_loglikelihood = _logsumexp(path_logs, axis=2)

    initially_dead = ~initial_alive
    if np.any(initially_dead):
        all_zero = np.all(counts[:, initially_dead] == 0, axis=2)
        site_loglikelihood[:, initially_dead] = np.where(all_zero, 0.0, -np.inf)
    if return_site:
        return site_loglikelihood
    return np.asarray(np.sum(site_loglikelihood[:, training], axis=1), dtype=np.float64)


__all__ = ["independent_pre_log_likelihood"]
