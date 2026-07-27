"""Two-dimensional site-history simulated composite likelihood for Goal 007."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite, log
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal004.likelihood import (
    CATEGORY_COUNT,
    MLE_TOLERANCE,
    PredictiveScore,
    category_weights,
)

from .observations import SURVEY_TIMES

RHO_GRID_SIZE = 601
ETA_GRID_SIZE = 9
TRUTH_RHO = 1.0
TRUTH_ETA = 1.0
TRUTH_RHO_INDEX = 300
TRUTH_ETA_INDEX = 4


class OutcomeRecordLike(Protocol):
    @property
    def site_id(self) -> str: ...

    @property
    def time(self) -> int: ...

    @property
    def detected(self) -> int: ...


@dataclass(frozen=True, slots=True)
class JointGridProfile:
    scope: str
    rhos: NDArray[np.float64]
    etas: NDArray[np.float64]
    log_likelihoods: NDArray[np.float64]
    maximum_log_likelihood: float
    mle_indices: tuple[tuple[int, int], ...]
    mle_cells: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class JointProfileSummary:
    truth_included: bool
    support_indices: tuple[tuple[int, int], ...]
    support_cell_count: int
    support_component_count: int
    support_boundary_contact: bool
    projected_log_rho_width: float
    projected_eta_width: float
    mle_indices: tuple[tuple[int, int], ...]
    mle_cells: tuple[tuple[float, float], ...]
    minimum_absolute_log_rho_error: float
    minimum_absolute_eta_error: float
    support_correlation: float | None
    support_correlation_reason: str | None


def rho_grid() -> NDArray[np.float64]:
    """Return the exact prespecified 601-point base-two rate grid."""
    return np.asarray(
        [2.0 ** (-2.0 + 4.0 * index / 600.0) for index in range(RHO_GRID_SIZE)],
        dtype=np.float64,
    )


def eta_grid() -> NDArray[np.float64]:
    """Return the exact prespecified nine-point resistance-contrast grid."""
    return np.asarray([index / 4.0 for index in range(ETA_GRID_SIZE)], dtype=np.float64)


def joint_category_weights(
    bank_arrivals: NDArray[np.float64],
    rhos: NDArray[np.float64],
    *,
    survey_times: tuple[int, ...] = SURVEY_TIMES,
) -> NDArray[np.float64]:
    """Calculate eta-specific category weights with exact rho scaling."""
    bank = np.asarray(bank_arrivals, dtype=np.float64)
    rates = np.asarray(rhos, dtype=np.float64)
    if bank.ndim != 3 or any(size == 0 for size in bank.shape):
        raise ValueError("joint integration bank must have shape (draw, eta, site)")
    if not np.isfinite(bank).all() or (bank < 0.0).any():
        raise ValueError("joint integration-bank arrivals must be finite and nonnegative")
    return np.stack(
        [
            category_weights(bank[:, eta_index, :], rates, survey_times=survey_times)
            for eta_index in range(bank.shape[1])
        ],
        axis=0,
    )


def joint_profile(
    *,
    weights: NDArray[np.float64],
    rhos: NDArray[np.float64],
    etas: NDArray[np.float64],
    bank_site_ids: tuple[str, ...],
    history_site_ids: tuple[str, ...],
    onset_categories: NDArray[np.int64],
    scope: str,
) -> JointGridProfile:
    """Build a two-dimensional composite profile from one category per site."""
    values = np.asarray(weights, dtype=np.float64)
    rate_values = np.asarray(rhos, dtype=np.float64)
    eta_values = np.asarray(etas, dtype=np.float64)
    categories = np.asarray(onset_categories, dtype=np.int64)
    _validate_axes(rate_values, eta_values)
    if not scope:
        raise ValueError("profile scope must not be empty")
    if len(set(bank_site_ids)) != len(bank_site_ids):
        raise ValueError("bank site identifiers must be unique")
    if len(set(history_site_ids)) != len(history_site_ids):
        raise ValueError("history site identifiers must be unique")
    expected_shape = (len(eta_values), len(rate_values), len(bank_site_ids), CATEGORY_COUNT)
    if values.shape != expected_shape:
        raise ValueError("joint category weights have an invalid shape")
    if (
        not np.isfinite(values).all()
        or (values <= 0.0).any()
        or not np.allclose(values.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("joint category weights must be positive finite probabilities")
    if categories.shape != (len(history_site_ids),):
        raise ValueError("onset categories have an invalid shape")
    if (categories < 0).any() or (categories >= CATEGORY_COUNT).any():
        raise ValueError("onset categories must lie in the seven-category support")
    bank_index = {site_id: index for index, site_id in enumerate(bank_site_ids)}
    try:
        indices = np.asarray([bank_index[site_id] for site_id in history_site_ids])
    except KeyError as error:
        raise ValueError("history contains an unknown bank site") from error
    if len(indices) == 0:
        raise ValueError("profile requires at least one site history")

    site_probabilities = values[:, :, indices, categories]
    if site_probabilities.shape != (len(eta_values), len(rate_values), len(indices)):
        raise RuntimeError("advanced category indexing produced an invalid profile shape")
    log_likelihoods = np.log(site_probabilities).sum(axis=2)
    maximum = float(log_likelihoods.max())
    mle_mask = np.isclose(log_likelihoods, maximum, rtol=0.0, atol=MLE_TOLERANCE)
    mle_indices = tuple(
        (int(eta_index), int(rho_index)) for eta_index, rho_index in np.argwhere(mle_mask)
    )
    mle_cells = tuple(
        (float(rate_values[rho_index]), float(eta_values[eta_index]))
        for eta_index, rho_index in mle_indices
    )
    return JointGridProfile(
        scope=scope,
        rhos=rate_values.copy(),
        etas=eta_values.copy(),
        log_likelihoods=log_likelihoods,
        maximum_log_likelihood=maximum,
        mle_indices=mle_indices,
        mle_cells=mle_cells,
    )


def summarize_joint_profile(
    profile: JointGridProfile,
    *,
    cutoff: float,
    truth_rho: float = TRUTH_RHO,
    truth_eta: float = TRUTH_ETA,
) -> JointProfileSummary:
    """Summarize calibrated support using four-neighbour eta-by-rho adjacency."""
    if not isfinite(cutoff) or cutoff < 0.0:
        raise ValueError("support cutoff must be finite and nonnegative")
    if not isfinite(truth_rho) or truth_rho <= 0.0 or not isfinite(truth_eta):
        raise ValueError("truth coordinates must be finite and rho positive")
    _validate_profile(profile)
    statistics = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
    support = tuple(
        (int(eta_index), int(rho_index))
        for eta_index, rho_index in np.argwhere(statistics <= cutoff)
    )
    if not support:
        raise ValueError("calibrated support must not be empty")
    components = _rook_component_count(
        support,
        eta_count=len(profile.etas),
        rho_count=len(profile.rhos),
    )
    rho_values = np.asarray([profile.rhos[rho_index] for _, rho_index in support])
    eta_values = np.asarray([profile.etas[eta_index] for eta_index, _ in support])
    correlation, reason = _support_correlation(rho_values, eta_values)
    return JointProfileSummary(
        truth_included=any(
            profile.rhos[rho_index] == truth_rho and profile.etas[eta_index] == truth_eta
            for eta_index, rho_index in support
        ),
        support_indices=support,
        support_cell_count=len(support),
        support_component_count=components,
        support_boundary_contact=any(
            eta_index in (0, len(profile.etas) - 1) or rho_index in (0, len(profile.rhos) - 1)
            for eta_index, rho_index in support
        ),
        projected_log_rho_width=float(log(float(rho_values.max())) - log(float(rho_values.min()))),
        projected_eta_width=float(eta_values.max() - eta_values.min()),
        mle_indices=profile.mle_indices,
        mle_cells=profile.mle_cells,
        minimum_absolute_log_rho_error=min(
            abs(log(rho) - log(truth_rho)) for rho, _ in profile.mle_cells
        ),
        minimum_absolute_eta_error=min(abs(eta - truth_eta) for _, eta in profile.mle_cells),
        support_correlation=correlation,
        support_correlation_reason=reason,
    )


def record_occupancy_probabilities(
    *,
    weights: NDArray[np.float64],
    site_ids: tuple[str, ...],
    records: Sequence[OutcomeRecordLike],
    survey_times: tuple[int, ...] = SURVEY_TIMES,
) -> tuple[float, ...]:
    """Predict perfect-detection occupancy from one fitted joint grid cell."""
    values = np.asarray(weights, dtype=np.float64)
    if values.shape != (len(site_ids), CATEGORY_COUNT):
        raise ValueError("prediction weights have an invalid shape")
    if len(set(site_ids)) != len(site_ids):
        raise ValueError("site identifiers must be unique")
    if (
        not np.isfinite(values).all()
        or (values <= 0.0).any()
        or not np.allclose(values.sum(axis=1), 1.0, rtol=0.0, atol=1e-12)
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
        predictions.append(float(values[site, : survey + 1].sum()))
    if not predictions or not all(0.0 < value < 1.0 for value in predictions):
        raise ValueError("record predictions must have full support")
    return tuple(predictions)


def score_predictions(
    probabilities: Sequence[float],
    records: Sequence[OutcomeRecordLike],
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


def _validate_axes(rhos: NDArray[np.float64], etas: NDArray[np.float64]) -> None:
    if rhos.ndim != 1 or len(rhos) == 0:
        raise ValueError("rhos must be a nonempty one-dimensional array")
    if etas.ndim != 1 or len(etas) == 0:
        raise ValueError("etas must be a nonempty one-dimensional array")
    if not np.isfinite(rhos).all() or (rhos <= 0.0).any() or (np.diff(rhos) <= 0.0).any():
        raise ValueError("rhos must be finite, positive, and strictly increasing")
    if not np.isfinite(etas).all() or (etas < 0.0).any() or (np.diff(etas) <= 0.0).any():
        raise ValueError("etas must be finite, nonnegative, and strictly increasing")


def _validate_profile(profile: JointGridProfile) -> None:
    _validate_axes(profile.rhos, profile.etas)
    if profile.log_likelihoods.shape != (len(profile.etas), len(profile.rhos)):
        raise ValueError("joint profile likelihood surface has an invalid shape")
    if not np.isfinite(profile.log_likelihoods).all():
        raise ValueError("joint profile likelihoods must be finite")
    if not profile.mle_indices or not profile.mle_cells:
        raise ValueError("joint profile MLE set must not be empty")
    if len(profile.mle_indices) != len(profile.mle_cells):
        raise ValueError("joint profile MLE indices and cells must reconcile")


def _rook_component_count(
    support: tuple[tuple[int, int], ...],
    *,
    eta_count: int,
    rho_count: int,
) -> int:
    remaining = set(support)
    components = 0
    while remaining:
        components += 1
        queue = deque((remaining.pop(),))
        while queue:
            eta_index, rho_index = queue.popleft()
            candidates = (
                (eta_index - 1, rho_index),
                (eta_index + 1, rho_index),
                (eta_index, rho_index - 1),
                (eta_index, rho_index + 1),
            )
            for candidate in candidates:
                if (
                    0 <= candidate[0] < eta_count
                    and 0 <= candidate[1] < rho_count
                    and candidate in remaining
                ):
                    remaining.remove(candidate)
                    queue.append(candidate)
    return components


def _support_correlation(
    rhos: NDArray[np.float64],
    etas: NDArray[np.float64],
) -> tuple[float | None, str | None]:
    if len(rhos) == 1:
        return None, "one_cell"
    if np.ptp(rhos) == 0.0:
        return None, "constant_rho"
    if np.ptp(etas) == 0.0:
        return None, "constant_eta"
    return float(np.corrcoef(rhos, etas)[0, 1]), None


__all__ = [
    "CATEGORY_COUNT",
    "JointGridProfile",
    "JointProfileSummary",
    "PredictiveScore",
    "eta_grid",
    "joint_category_weights",
    "joint_profile",
    "record_occupancy_probabilities",
    "rho_grid",
    "score_predictions",
    "summarize_joint_profile",
]
