"""Site-history simulated composite likelihood for Goal 004."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from math import isfinite, log
from typing import Protocol, cast

import numpy as np
from numpy.typing import NDArray

from .observations import (
    DETECTION_PROBABILITY,
    REPLICATES,
)
from .observations import (
    SURVEY_TIMES as FROZEN_SURVEY_TIMES,
)

SURVEY_TIMES = FROZEN_SURVEY_TIMES

RATE_DOMAIN = (0.25, 4.0)
RATE_GRID_SIZE = 601
TRUTH_RATE = 1.0
TRUTH_INDEX = 300
CATEGORY_COUNT = 7
MLE_TOLERANCE = 1e-12


class HistoryRecordLike(Protocol):
    @property
    def site_id(self) -> str: ...

    @property
    def time(self) -> int: ...

    @property
    def replicate(self) -> int: ...

    @property
    def detected(self) -> int: ...


@dataclass(frozen=True, slots=True)
class GridProfile:
    scope: str
    rates: NDArray[np.float64]
    log_likelihoods: NDArray[np.float64]
    maximum_log_likelihood: float
    mle_indices: tuple[int, ...]
    mle_rates: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class SupportComponent:
    start_index: int
    end_index: int
    lower: float
    upper: float

    @property
    def arithmetic_width(self) -> float:
        return self.upper - self.lower

    @property
    def log_rate_width(self) -> float:
        return log(self.upper) - log(self.lower)


@dataclass(frozen=True, slots=True)
class GridProfileSummary:
    truth_included: bool
    support_indices: tuple[int, ...]
    support_components: tuple[SupportComponent, ...]
    support_boundary_contact: bool
    support_arithmetic_width: float
    support_log_rate_width: float
    mle_indices: tuple[int, ...]
    mle_rates: tuple[float, ...]
    truth_to_mle_set_distance: float
    absolute_log_rate_error: float


@dataclass(frozen=True, slots=True)
class PredictiveScore:
    total_log_score: float
    mean_brier_score: float
    record_count: int
    probability_minimum: float
    probability_maximum: float


def rate_grid() -> NDArray[np.float64]:
    """Return the exact prespecified 601-point base-two rate grid."""
    return np.asarray(
        [2.0 ** (-2.0 + 4.0 * index / 600.0) for index in range(RATE_GRID_SIZE)],
        dtype=np.float64,
    )


def category_weights(
    bank_arrivals: NDArray[np.float64],
    rates: NDArray[np.float64],
    *,
    survey_times: tuple[int, ...] = SURVEY_TIMES,
) -> NDArray[np.float64]:
    """Estimate Jeffreys-smoothed onset-category probabilities for each site."""
    bank = np.asarray(bank_arrivals, dtype=np.float64)
    rate_values = np.asarray(rates, dtype=np.float64)
    _validate_bank(bank)
    _validate_rates(rate_values)
    _validate_calendar(survey_times)
    if len(survey_times) + 1 != CATEGORY_COUNT:
        raise ValueError("survey calendar must define exactly seven onset categories")

    bank_size, site_count = bank.shape
    counts = np.empty((len(rate_values), site_count, CATEGORY_COUNT), dtype=np.float64)
    queries = np.multiply.outer(rate_values, np.asarray(survey_times, dtype=np.float64))
    sorted_arrivals = np.sort(bank, axis=0)
    for site_index in range(site_count):
        cumulative = np.searchsorted(sorted_arrivals[:, site_index], queries, side="right")
        counts[:, site_index, 0] = cumulative[:, 0]
        counts[:, site_index, 1:-1] = np.diff(cumulative, axis=1)
        counts[:, site_index, -1] = bank_size - cumulative[:, -1]
    return cast(
        NDArray[np.float64],
        (counts + 0.5) / (bank_size + CATEGORY_COUNT * 0.5),
    )


def site_history_probabilities(
    *,
    site_ids: tuple[str, ...],
    records: Sequence[HistoryRecordLike],
    detection_probability: float = DETECTION_PROBABILITY,
    survey_times: tuple[int, ...] = SURVEY_TIMES,
) -> tuple[tuple[str, ...], NDArray[np.float64]]:
    """Return complete-history probabilities by observed site and onset category."""
    _validate_probability(detection_probability)
    _validate_calendar(survey_times)
    if len(survey_times) + 1 != CATEGORY_COUNT:
        raise ValueError("survey calendar must define exactly seven onset categories")
    if len(set(site_ids)) != len(site_ids):
        raise ValueError("site identifiers must be unique")
    if not records:
        raise ValueError("records must not be empty")

    known = set(site_ids)
    observed = {record.site_id for record in records}
    if not observed <= known:
        raise ValueError("records contain an unknown site identifier")
    selected = tuple(site_id for site_id in site_ids if site_id in observed)
    expected_keys = {(time, replicate) for time in survey_times for replicate in REPLICATES}
    histories: dict[str, dict[tuple[int, int], int]] = {site_id: {} for site_id in selected}
    for record in records:
        if record.detected not in (0, 1):
            raise ValueError("detected outcome must be binary")
        key = (record.time, record.replicate)
        if key not in expected_keys:
            raise ValueError("record has an unknown survey time or replicate")
        if key in histories[record.site_id]:
            raise ValueError("site history contains a duplicate record")
        histories[record.site_id][key] = record.detected
    if any(set(history) != expected_keys for history in histories.values()):
        raise ValueError("each observed site must have a complete 12-record history")

    probabilities = np.ones((len(selected), CATEGORY_COUNT), dtype=np.float64)
    for site_index, site_id in enumerate(selected):
        site_history = histories[site_id]
        for category in range(CATEGORY_COUNT):
            probability = 1.0
            for survey_index, time in enumerate(survey_times):
                occupied = category <= survey_index
                for replicate in REPLICATES:
                    detected = site_history[(time, replicate)]
                    if not occupied:
                        if detected:
                            probability = 0.0
                            break
                    else:
                        probability *= (
                            detection_probability if detected else 1.0 - detection_probability
                        )
                if probability == 0.0:
                    break
            probabilities[site_index, category] = probability
    return selected, probabilities


def profile_from_history_probabilities(
    *,
    weights: NDArray[np.float64],
    rates: NDArray[np.float64],
    bank_site_ids: tuple[str, ...],
    history_site_ids: tuple[str, ...],
    history_probabilities: NDArray[np.float64],
    scope: str,
) -> GridProfile:
    """Build a composite profile from reusable bank and history probabilities."""
    weight_values = np.asarray(weights, dtype=np.float64)
    rate_values = np.asarray(rates, dtype=np.float64)
    histories = np.asarray(history_probabilities, dtype=np.float64)
    _validate_weights(weight_values, rate_values, bank_site_ids)
    if not scope:
        raise ValueError("profile scope must not be empty")
    if len(set(history_site_ids)) != len(history_site_ids):
        raise ValueError("history site identifiers must be unique")
    if histories.shape != (len(history_site_ids), CATEGORY_COUNT):
        raise ValueError("history probability array has an invalid shape")
    if not np.isfinite(histories).all() or (histories < 0.0).any():
        raise ValueError("history probabilities must be finite and nonnegative")

    bank_index = {site_id: index for index, site_id in enumerate(bank_site_ids)}
    try:
        selected_indices = tuple(bank_index[site_id] for site_id in history_site_ids)
    except KeyError as error:
        raise ValueError("history contains an unknown bank site") from error
    selected_weights = weight_values[:, selected_indices, :]
    site_probabilities = np.einsum(
        "rsc,sc->rs",
        selected_weights,
        histories,
        optimize=True,
    )
    if not np.isfinite(site_probabilities).all() or (site_probabilities <= 0.0).any():
        raise ValueError("site-history marginal probability must be finite and positive")
    log_likelihoods = np.log(site_probabilities).sum(axis=1)
    maximum = float(log_likelihoods.max())
    mle_mask = np.isclose(log_likelihoods, maximum, rtol=0.0, atol=MLE_TOLERANCE)
    mle_indices = tuple(int(index) for index in np.flatnonzero(mle_mask))
    return GridProfile(
        scope=scope,
        rates=rate_values.copy(),
        log_likelihoods=log_likelihoods,
        maximum_log_likelihood=maximum,
        mle_indices=mle_indices,
        mle_rates=tuple(float(rate_values[index]) for index in mle_indices),
    )


def composite_profile(
    *,
    weights: NDArray[np.float64],
    rates: NDArray[np.float64],
    site_ids: tuple[str, ...],
    records: Sequence[HistoryRecordLike],
    detection_probability: float = DETECTION_PROBABILITY,
    scope: str,
    survey_times: tuple[int, ...] = SURVEY_TIMES,
) -> GridProfile:
    """Build a site-history simulated composite-likelihood grid profile."""
    selected, histories = site_history_probabilities(
        site_ids=site_ids,
        records=records,
        detection_probability=detection_probability,
        survey_times=survey_times,
    )
    return profile_from_history_probabilities(
        weights=weights,
        rates=rates,
        bank_site_ids=site_ids,
        history_site_ids=selected,
        history_probabilities=histories,
        scope=scope,
    )


def summarize_profile(
    profile: GridProfile,
    *,
    cutoff: float,
    truth_rate: float = TRUTH_RATE,
) -> GridProfileSummary:
    """Summarize the calibrated discrete-grid support without collapsing ties."""
    if not isfinite(cutoff) or cutoff < 0.0:
        raise ValueError("support cutoff must be finite and nonnegative")
    if not isfinite(truth_rate) or truth_rate <= 0.0:
        raise ValueError("truth rate must be finite and positive")
    if not profile.mle_indices:
        raise ValueError("profile MLE set must not be empty")
    statistics = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
    support_indices = tuple(int(index) for index in np.flatnonzero(statistics <= cutoff))
    if not support_indices:
        raise ValueError("calibrated support must not be empty")
    components = _support_components(profile.rates, support_indices)
    return GridProfileSummary(
        truth_included=any(profile.rates[index] == truth_rate for index in support_indices),
        support_indices=support_indices,
        support_components=components,
        support_boundary_contact=(
            support_indices[0] == 0 or support_indices[-1] == len(profile.rates) - 1
        ),
        support_arithmetic_width=sum(component.arithmetic_width for component in components),
        support_log_rate_width=sum(component.log_rate_width for component in components),
        mle_indices=profile.mle_indices,
        mle_rates=profile.mle_rates,
        truth_to_mle_set_distance=min(abs(rate - truth_rate) for rate in profile.mle_rates),
        absolute_log_rate_error=min(abs(log(rate) - log(truth_rate)) for rate in profile.mle_rates),
    )


def record_detection_probabilities(
    *,
    weights: NDArray[np.float64],
    site_ids: tuple[str, ...],
    records: Sequence[HistoryRecordLike],
    detection_probability: float = DETECTION_PROBABILITY,
    survey_times: tuple[int, ...] = SURVEY_TIMES,
) -> tuple[float, ...]:
    """Predict each record from category-marginal occupancy at one fitted rate."""
    _validate_probability(detection_probability)
    _validate_calendar(survey_times)
    weight_values = np.asarray(weights, dtype=np.float64)
    if weight_values.shape != (len(site_ids), CATEGORY_COUNT):
        raise ValueError("prediction weights have an invalid shape")
    if (
        not np.isfinite(weight_values).all()
        or (weight_values <= 0.0).any()
        or not np.allclose(weight_values.sum(axis=1), 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("prediction weights must be positive finite category probabilities")
    site_index = {site_id: index for index, site_id in enumerate(site_ids)}
    time_index = {time: index for index, time in enumerate(survey_times)}
    predictions: list[float] = []
    for record in records:
        try:
            site = site_index[record.site_id]
            survey = time_index[record.time]
        except KeyError as error:
            raise ValueError("prediction record has an unknown site or survey time") from error
        predictions.append(detection_probability * float(weight_values[site, : survey + 1].sum()))
    if not predictions or not all(0.0 < value < 1.0 for value in predictions):
        raise ValueError("record predictions must have full support")
    return tuple(predictions)


def score_predictions(
    probabilities: Sequence[float],
    records: Sequence[HistoryRecordLike],
) -> PredictiveScore:
    """Calculate finite recordwise log and mean Brier scores."""
    values = tuple(float(value) for value in probabilities)
    if not records or len(values) != len(records):
        raise ValueError("predictions and nonempty records must have equal length")
    if any(not isfinite(value) or not 0.0 < value < 1.0 for value in values):
        raise ValueError("prediction probabilities must be finite and lie in (0, 1)")
    outcomes = tuple(record.detected for record in records)
    if any(value not in (0, 1) for value in outcomes):
        raise ValueError("detected outcome must be binary")
    total_log_score = sum(
        log(probability if detected else 1.0 - probability)
        for probability, detected in zip(values, outcomes, strict=True)
    )
    mean_brier = sum(
        (detected - probability) ** 2
        for probability, detected in zip(values, outcomes, strict=True)
    ) / len(values)
    return PredictiveScore(
        total_log_score=total_log_score,
        mean_brier_score=mean_brier,
        record_count=len(values),
        probability_minimum=min(values),
        probability_maximum=max(values),
    )


def _support_components(
    rates: NDArray[np.float64],
    indices: tuple[int, ...],
) -> tuple[SupportComponent, ...]:
    components: list[SupportComponent] = []
    start = previous = indices[0]
    for index in indices[1:]:
        if index != previous + 1:
            components.append(
                SupportComponent(start, previous, float(rates[start]), float(rates[previous]))
            )
            start = index
        previous = index
    components.append(
        SupportComponent(start, previous, float(rates[start]), float(rates[previous]))
    )
    return tuple(components)


def _validate_bank(bank: NDArray[np.float64]) -> None:
    if bank.ndim != 2:
        raise ValueError("integration bank must be two-dimensional")
    if bank.shape[0] == 0 or bank.shape[1] == 0:
        raise ValueError("integration bank dimensions must be nonzero")
    if not np.isfinite(bank).all():
        raise ValueError("integration-bank arrivals must be finite")
    if (bank < 0.0).any():
        raise ValueError("integration-bank arrivals must be nonnegative")


def _validate_rates(rates: NDArray[np.float64]) -> None:
    if rates.ndim != 1 or len(rates) == 0:
        raise ValueError("rates must be a nonempty one-dimensional array")
    if not np.isfinite(rates).all() or (rates <= 0.0).any():
        raise ValueError("rates must be finite and positive")
    if (np.diff(rates) <= 0.0).any():
        raise ValueError("rates must be strictly increasing")


def _validate_calendar(survey_times: tuple[int, ...]) -> None:
    if not survey_times or any(left >= right for left, right in pairwise(survey_times)):
        raise ValueError("survey times must be nonempty and strictly increasing")


def _validate_probability(value: float) -> None:
    if not isfinite(value) or not 0.0 < value < 1.0:
        raise ValueError("detection probability must be finite and lie in (0, 1)")


def _validate_weights(
    weights: NDArray[np.float64],
    rates: NDArray[np.float64],
    site_ids: tuple[str, ...],
) -> None:
    _validate_rates(rates)
    if weights.shape != (len(rates), len(site_ids), CATEGORY_COUNT):
        raise ValueError("category weights have an invalid shape")
    if len(set(site_ids)) != len(site_ids):
        raise ValueError("site identifiers must be unique")
    if (
        not np.isfinite(weights).all()
        or (weights <= 0.0).any()
        or not np.allclose(weights.sum(axis=2), 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("category weights must be positive finite probabilities")
