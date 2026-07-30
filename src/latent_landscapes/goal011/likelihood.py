"""Joint site-history likelihood under known imperfect detection."""

from __future__ import annotations

from collections.abc import Sequence
from math import isfinite

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal004.likelihood import (
    CATEGORY_COUNT,
    MLE_TOLERANCE,
    HistoryRecordLike,
    PredictiveScore,
    record_detection_probabilities,
    score_predictions,
    site_history_probabilities,
)
from latent_landscapes.goal004.observations import DETECTION_PROBABILITY
from latent_landscapes.goal007.likelihood import (
    JointGridProfile,
    JointProfileSummary,
    rho_grid,
    summarize_joint_profile,
)
from latent_landscapes.goal010.benchmark import EXPANDED_ETA_VALUES

OLD_DOMAIN_MAXIMUM_ETA = 2.0


def eta_grid() -> NDArray[np.float64]:
    """Return the accepted eleven-point Goal 010 eta domain."""
    return np.asarray(
        [index / 4.0 for index in range(9)] + list(EXPANDED_ETA_VALUES),
        dtype=np.float64,
    )


def joint_profile_from_history_probabilities(
    *,
    weights: NDArray[np.float64],
    rhos: NDArray[np.float64],
    etas: NDArray[np.float64],
    bank_site_ids: tuple[str, ...],
    history_site_ids: tuple[str, ...],
    history_probabilities: NDArray[np.float64],
    scope: str,
) -> JointGridProfile:
    """Marginalize complete site histories over the joint category weights."""
    values = np.asarray(weights, dtype=np.float64)
    rho_values = np.asarray(rhos, dtype=np.float64)
    eta_values = np.asarray(etas, dtype=np.float64)
    histories = np.asarray(history_probabilities, dtype=np.float64)
    _validate_axes(rho_values, eta_values)
    if not scope:
        raise ValueError("profile scope must not be empty")
    if len(set(bank_site_ids)) != len(bank_site_ids):
        raise ValueError("bank site identifiers must be unique")
    if len(set(history_site_ids)) != len(history_site_ids):
        raise ValueError("history site identifiers must be unique")
    expected_shape = (
        len(eta_values),
        len(rho_values),
        len(bank_site_ids),
        CATEGORY_COUNT,
    )
    if values.shape != expected_shape:
        raise ValueError("joint category weights have an invalid shape")
    if (
        not np.isfinite(values).all()
        or (values <= 0.0).any()
        or not np.allclose(values.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("joint category weights must be positive finite probabilities")
    if histories.shape != (len(history_site_ids), CATEGORY_COUNT):
        raise ValueError("history probability array has an invalid shape")
    if not np.isfinite(histories).all() or (histories < 0.0).any():
        raise ValueError("history probabilities must be finite and nonnegative")

    bank_index = {site_id: index for index, site_id in enumerate(bank_site_ids)}
    try:
        indices = tuple(bank_index[site_id] for site_id in history_site_ids)
    except KeyError as error:
        raise ValueError("history contains an unknown bank site") from error
    if not indices:
        raise ValueError("profile requires at least one site history")

    selected_weights = values[:, :, indices, :]
    site_probabilities = np.einsum(
        "ersc,sc->ers",
        selected_weights,
        histories,
        optimize=True,
    )
    if not np.isfinite(site_probabilities).all() or (site_probabilities <= 0.0).any():
        raise ValueError("site-history marginal probability must be finite and positive")
    log_likelihoods = np.log(site_probabilities).sum(axis=2)
    return _joint_profile(
        scope=scope,
        rhos=rho_values,
        etas=eta_values,
        log_likelihoods=log_likelihoods,
    )


def joint_history_profile(
    *,
    weights: NDArray[np.float64],
    rhos: NDArray[np.float64],
    etas: NDArray[np.float64],
    site_ids: tuple[str, ...],
    records: Sequence[HistoryRecordLike],
    detection_probability: float = DETECTION_PROBABILITY,
    scope: str,
) -> JointGridProfile:
    """Build a joint profile from complete two-visit detection histories."""
    selected, histories = site_history_probabilities(
        site_ids=site_ids,
        records=records,
        detection_probability=detection_probability,
    )
    return joint_profile_from_history_probabilities(
        weights=weights,
        rhos=rhos,
        etas=etas,
        bank_site_ids=site_ids,
        history_site_ids=selected,
        history_probabilities=histories,
        scope=scope,
    )


def project_eta_domain(
    profile: JointGridProfile,
    *,
    maximum_eta: float = OLD_DOMAIN_MAXIMUM_ETA,
) -> JointGridProfile:
    """Slice a calculated profile to a non-gating eta domain and refit its maximum."""
    if not isfinite(maximum_eta) or maximum_eta < 0.0:
        raise ValueError("maximum eta must be finite and nonnegative")
    selected = np.flatnonzero(profile.etas <= maximum_eta)
    if len(selected) == 0 or not np.array_equal(selected, np.arange(len(selected))):
        raise ValueError("eta projection must retain a nonempty leading domain")
    return _joint_profile(
        scope=profile.scope,
        rhos=profile.rhos,
        etas=profile.etas[selected],
        log_likelihoods=profile.log_likelihoods[selected],
    )


def _joint_profile(
    *,
    scope: str,
    rhos: NDArray[np.float64],
    etas: NDArray[np.float64],
    log_likelihoods: NDArray[np.float64],
) -> JointGridProfile:
    values = np.asarray(log_likelihoods, dtype=np.float64)
    if values.shape != (len(etas), len(rhos)) or not np.isfinite(values).all():
        raise ValueError("joint profile likelihood surface has an invalid shape or value")
    maximum = float(values.max())
    mle_mask = np.isclose(values, maximum, rtol=0.0, atol=MLE_TOLERANCE)
    mle_indices = tuple(
        (int(eta_index), int(rho_index)) for eta_index, rho_index in np.argwhere(mle_mask)
    )
    mle_cells = tuple(
        (float(rhos[rho_index]), float(etas[eta_index])) for eta_index, rho_index in mle_indices
    )
    return JointGridProfile(
        scope=scope,
        rhos=rhos.copy(),
        etas=etas.copy(),
        log_likelihoods=values.copy(),
        maximum_log_likelihood=maximum,
        mle_indices=mle_indices,
        mle_cells=mle_cells,
    )


def _validate_axes(
    rhos: NDArray[np.float64],
    etas: NDArray[np.float64],
) -> None:
    if (
        rhos.ndim != 1
        or len(rhos) == 0
        or not np.isfinite(rhos).all()
        or (rhos <= 0.0).any()
        or (np.diff(rhos) <= 0.0).any()
    ):
        raise ValueError("rhos must be finite, positive, and strictly increasing")
    if (
        etas.ndim != 1
        or len(etas) == 0
        or not np.isfinite(etas).all()
        or (etas < 0.0).any()
        or (np.diff(etas) <= 0.0).any()
    ):
        raise ValueError("etas must be finite, nonnegative, and strictly increasing")


EXPANDED_ETA_GRID = tuple(float(value) for value in eta_grid())

__all__ = [
    "CATEGORY_COUNT",
    "DETECTION_PROBABILITY",
    "EXPANDED_ETA_GRID",
    "OLD_DOMAIN_MAXIMUM_ETA",
    "JointGridProfile",
    "JointProfileSummary",
    "PredictiveScore",
    "eta_grid",
    "joint_history_profile",
    "joint_profile_from_history_probabilities",
    "project_eta_domain",
    "record_detection_probabilities",
    "rho_grid",
    "score_predictions",
    "summarize_joint_profile",
]
