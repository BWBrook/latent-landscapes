"""Complete-history predator likelihood and calibrated support for Arc 2A."""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal004.likelihood import CATEGORY_COUNT, MLE_TOLERANCE, HistoryRecordLike
from latent_landscapes.goal004.observations import REPLICATES, SURVEY_TIMES

TRUTH_RHO = 1.0
TRUTH_ETA = 1.0
TRUTH_PROBABILITY = 0.65


@dataclass(frozen=True, slots=True)
class ThreeParameterProfile:
    etas: NDArray[np.float64]
    rhos: NDArray[np.float64]
    probabilities: NDArray[np.float64]
    log_likelihoods: NDArray[np.float64]
    maximum_log_likelihood: float
    mle_indices: tuple[tuple[int, int, int], ...]
    mle_cells: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True, slots=True)
class SupportSummary:
    truth_included: bool
    cell_count: int
    component_count: int
    boundary_contact: bool
    projected_log_rho_width: float
    projected_eta_width: float
    projected_probability_width: float
    minimum_log_rho_error: float
    minimum_eta_error: float
    minimum_probability_error: float
    rho_eta_correlation: float | None
    rho_probability_correlation: float | None
    eta_probability_correlation: float | None


def history_exponents(
    site_ids: tuple[str, ...],
    records: Sequence[HistoryRecordLike],
) -> tuple[tuple[str, ...], NDArray[np.int64], NDArray[np.int64], NDArray[np.bool_]]:
    if not records or len(set(site_ids)) != len(site_ids):
        raise ValueError("site identifiers must be unique and records nonempty")
    expected = {(time, replicate) for time in SURVEY_TIMES for replicate in REPLICATES}
    histories: dict[str, dict[tuple[int, int], int]] = {}
    for record in records:
        if record.site_id not in site_ids or record.detected not in (0, 1):
            raise ValueError("record has an unknown site or nonbinary detection")
        key = (record.time, record.replicate)
        if key not in expected:
            raise ValueError("record has an unknown survey time or replicate")
        site_history = histories.setdefault(record.site_id, {})
        if key in site_history:
            raise ValueError("site history contains a duplicate record")
        site_history[key] = record.detected
    selected = tuple(site_id for site_id in site_ids if site_id in histories)
    if any(set(histories[site_id]) != expected for site_id in selected):
        raise ValueError("each observed site must have a complete history")

    detections = np.zeros((len(selected), CATEGORY_COUNT), dtype=np.int64)
    nondetections = np.zeros_like(detections)
    valid = np.ones((len(selected), CATEGORY_COUNT), dtype=np.bool_)
    for site_index, site_id in enumerate(selected):
        for survey_index, time in enumerate(SURVEY_TIMES):
            for replicate in REPLICATES:
                detected = histories[site_id][(time, replicate)]
                for category in range(CATEGORY_COUNT):
                    if category <= survey_index:
                        if detected:
                            detections[site_index, category] += 1
                        else:
                            nondetections[site_index, category] += 1
                    elif detected:
                        valid[site_index, category] = False
    return selected, detections, nondetections, valid


def parameter_detection_log_likelihoods(
    *,
    site_ids: tuple[str, ...],
    records: Sequence[HistoryRecordLike],
    category_weights: NDArray[np.float64],
    probabilities: Sequence[float] | NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Calculate a generic parameter-by-detection complete-history surface."""
    weights = np.asarray(category_weights, dtype=np.float64)
    p_values = np.asarray(tuple(probabilities), dtype=np.float64)
    if weights.ndim != 3 or weights.shape[1:] != (len(site_ids), CATEGORY_COUNT):
        raise ValueError("category weights have an invalid shape")
    if (
        p_values.ndim != 1
        or len(p_values) == 0
        or not np.isfinite(p_values).all()
        or (p_values <= 0.0).any()
        or (p_values >= 1.0).any()
        or (np.diff(p_values) <= 0.0).any()
    ):
        raise ValueError("probability grid must be finite, interior, and increasing")
    if (
        not np.isfinite(weights).all()
        or (weights <= 0.0).any()
        or not np.allclose(weights.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("category weights must be positive finite probabilities")
    selected, detections, nondetections, valid = history_exponents(site_ids, records)
    site_index = {site_id: index for index, site_id in enumerate(site_ids)}
    selected_weights = weights[:, [site_index[site_id] for site_id in selected], :]
    p = p_values[:, None, None]
    histories = np.where(
        valid[None, :, :],
        np.power(p, detections[None, :, :]) * np.power(1.0 - p, nondetections[None, :, :]),
        0.0,
    )
    site_probabilities = np.einsum("rsc,psc->rps", selected_weights, histories, optimize=True)
    if not np.isfinite(site_probabilities).all() or (site_probabilities <= 0.0).any():
        raise ValueError("site-history probabilities must be finite and positive")
    log_likelihoods = np.log(site_probabilities).sum(axis=2)
    return p_values.copy(), log_likelihoods


def three_parameter_profile(
    *,
    site_ids: tuple[str, ...],
    records: Sequence[HistoryRecordLike],
    category_weights: NDArray[np.float64],
    rhos: Sequence[float] | NDArray[np.float64],
    etas: Sequence[float] | NDArray[np.float64],
    probabilities: Sequence[float] | NDArray[np.float64],
) -> ThreeParameterProfile:
    """Profile rho, eta, and p jointly."""
    rho_values = np.asarray(tuple(rhos), dtype=np.float64)
    eta_values = np.asarray(tuple(etas), dtype=np.float64)
    weights = np.asarray(category_weights, dtype=np.float64)
    expected_shape = (len(eta_values), len(rho_values), len(site_ids), CATEGORY_COUNT)
    if weights.shape != expected_shape:
        raise ValueError("category weights have an invalid shape")
    flat_weights = weights.reshape(len(eta_values) * len(rho_values), len(site_ids), CATEGORY_COUNT)
    p_values, flat_log_likelihoods = parameter_detection_log_likelihoods(
        site_ids=site_ids,
        records=records,
        category_weights=flat_weights,
        probabilities=probabilities,
    )
    log_likelihoods = flat_log_likelihoods.reshape(len(eta_values), len(rho_values), len(p_values))
    maximum = float(log_likelihoods.max())
    mle_indices = tuple(
        (int(eta_index), int(rho_index), int(p_index))
        for eta_index, rho_index, p_index in np.argwhere(
            np.isclose(log_likelihoods, maximum, rtol=0.0, atol=MLE_TOLERANCE)
        )
    )
    return ThreeParameterProfile(
        etas=eta_values.copy(),
        rhos=rho_values.copy(),
        probabilities=p_values,
        log_likelihoods=log_likelihoods,
        maximum_log_likelihood=maximum,
        mle_indices=mle_indices,
        mle_cells=tuple(
            (
                float(rho_values[rho_index]),
                float(eta_values[eta_index]),
                float(p_values[p_index]),
            )
            for eta_index, rho_index, p_index in mle_indices
        ),
    )


def summarize_support(
    profile: ThreeParameterProfile,
    *,
    cutoff: float,
    truth_rho: float = TRUTH_RHO,
    truth_eta: float = TRUTH_ETA,
    truth_probability: float = TRUTH_PROBABILITY,
) -> SupportSummary:
    """Summarize a calibrated six-neighbour three-dimensional support."""
    if not math.isfinite(cutoff) or cutoff < 0.0:
        raise ValueError("support cutoff must be finite and nonnegative")
    if (
        not math.isfinite(truth_rho)
        or truth_rho <= 0.0
        or not math.isfinite(truth_eta)
        or not math.isfinite(truth_probability)
        or sum(value == truth_rho for value in profile.rhos) != 1
        or sum(value == truth_eta for value in profile.etas) != 1
        or sum(value == truth_probability for value in profile.probabilities) != 1
    ):
        raise ValueError("truth coordinates must be finite and occur once on the profile")
    statistic = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
    support = tuple(
        (int(eta_index), int(rho_index), int(p_index))
        for eta_index, rho_index, p_index in np.argwhere(statistic <= cutoff)
    )
    if not support:
        raise ValueError("calibrated support must not be empty")
    eta_values = np.asarray([profile.etas[eta_index] for eta_index, _, _ in support])
    rho_values = np.asarray([profile.rhos[rho_index] for _, rho_index, _ in support])
    p_values = np.asarray([profile.probabilities[p_index] for _, _, p_index in support])
    log_rhos = np.log(rho_values)
    return SupportSummary(
        truth_included=any(
            profile.etas[eta_index] == truth_eta
            and profile.rhos[rho_index] == truth_rho
            and profile.probabilities[p_index] == truth_probability
            for eta_index, rho_index, p_index in support
        ),
        cell_count=len(support),
        component_count=_component_count(support),
        boundary_contact=any(
            eta_index in (0, len(profile.etas) - 1)
            or rho_index in (0, len(profile.rhos) - 1)
            or p_index in (0, len(profile.probabilities) - 1)
            for eta_index, rho_index, p_index in support
        ),
        projected_log_rho_width=float(log_rhos.max() - log_rhos.min()),
        projected_eta_width=float(eta_values.max() - eta_values.min()),
        projected_probability_width=float(p_values.max() - p_values.min()),
        minimum_log_rho_error=min(
            abs(math.log(rho / truth_rho)) for rho, _, _ in profile.mle_cells
        ),
        minimum_eta_error=min(abs(eta - truth_eta) for _, eta, _ in profile.mle_cells),
        minimum_probability_error=min(
            abs(probability - truth_probability) for _, _, probability in profile.mle_cells
        ),
        rho_eta_correlation=_correlation(log_rhos, eta_values),
        rho_probability_correlation=_correlation(log_rhos, p_values),
        eta_probability_correlation=_correlation(eta_values, p_values),
    )


def classify_outcome(
    *,
    invariants: dict[str, bool],
    connected_interior_count: int,
    validation_count: int,
    coverage: EstimateInterval,
    median_log_rho_error: float,
    median_eta_error: float,
    median_probability_error: float,
    median_log_rho_width: float,
    median_eta_width: float,
    median_probability_width: float,
) -> str:
    """Apply the prespecified full-joint progression rules."""
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if validation_count <= 0 or connected_interior_count < math.ceil(0.95 * validation_count):
        return "three_parameter_support_design_limited"
    if not coverage.lower <= 0.95 <= coverage.upper:
        return "three_parameter_calibration_not_ready"
    if any(
        _materially_exceeds(value, threshold)
        for value, threshold in (
            (median_log_rho_error, 0.10),
            (median_eta_error, 0.25),
            (median_probability_error, 0.05),
            (median_log_rho_width, 0.50),
            (median_eta_width, 0.75),
            (median_probability_width, 0.20),
        )
    ):
        return "three_parameter_recovery_imprecise"
    return "advance_to_cross_truth_three_parameter_benchmark"


def _materially_exceeds(value: float, threshold: float) -> bool:
    return value > threshold and not math.isclose(
        value,
        threshold,
        rel_tol=0.0,
        abs_tol=1e-12,
    )


def _component_count(indices: tuple[tuple[int, int, int], ...]) -> int:
    remaining = set(indices)
    components = 0
    while remaining:
        components += 1
        queue = deque([remaining.pop()])
        while queue:
            first, second, third = queue.popleft()
            for neighbour in (
                (first - 1, second, third),
                (first + 1, second, third),
                (first, second - 1, third),
                (first, second + 1, third),
                (first, second, third - 1),
                (first, second, third + 1),
            ):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    queue.append(neighbour)
    return components


def _correlation(first: NDArray[np.float64], second: NDArray[np.float64]) -> float | None:
    if len(first) <= 1 or np.ptp(first) == 0.0 or np.ptp(second) == 0.0:
        return None
    return float(np.corrcoef(first, second)[0, 1])
