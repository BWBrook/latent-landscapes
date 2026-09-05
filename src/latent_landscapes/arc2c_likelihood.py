"""Shared-arrival likelihood and paired simulation for the spread-speed bridge."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes.arc2c_design import BACKGROUND_HAZARD, DETECTION_PROBABILITY, TRUTHS
from latent_landscapes.goal004.observations import SURVEY_TIMES
from latent_landscapes.goal006.spread import compute_contrast_spread, sample_edge_shock_vector
from latent_landscapes.goal007 import benchmark as goal007


@dataclass(frozen=True, slots=True)
class BridgeIntegration:
    rhos: tuple[float, ...]
    effects: tuple[float, ...]
    site_ids: tuple[str, ...]
    category_mass: NDArray[np.float64]
    survival_moments: tuple[NDArray[np.float64], ...]
    bank_checksum: str


def build_joint_integration(
    base_arrivals: NDArray[np.float64],
    site_ids: tuple[str, ...],
    rhos: tuple[float, ...],
    effects: tuple[float, ...],
    background_hazard: float = BACKGROUND_HAZARD,
) -> BridgeIntegration:
    """Apply the accepted Arc 2B integration separately to each scaled bank."""
    bank = np.asarray(base_arrivals, dtype=np.float64)
    if (
        bank.ndim != 2
        or bank.shape[1] != len(site_ids)
        or not bank.shape[0]
        or not site_ids
        or len(set(site_ids)) != len(site_ids)
        or not np.isfinite(bank).all()
        or (bank < 0).any()
    ):
        raise ValueError("arrival bank and unique site identifiers must agree")
    for values, name in ((rhos, "rho"), (effects, "effect")):
        candidates = np.asarray(values, dtype=np.float64)
        if (
            candidates.ndim != 1
            or not len(candidates)
            or not np.isfinite(candidates).all()
            or (candidates <= 0).any()
            or (np.diff(candidates) <= 0).any()
        ):
            raise ValueError(f"{name} candidates must be positive and strictly increasing")
    if not math.isfinite(background_hazard) or background_hazard <= 0:
        raise ValueError("background hazard must be finite and positive")

    masses = np.empty((len(rhos), len(site_ids), arc2b.CATEGORY_COUNT), dtype=np.float64)
    moments: list[NDArray[np.float64]] = []
    for rho_index, rho in enumerate(rhos):
        integrated = arc2b.build_arrival_integration(
            bank / rho, site_ids, effects, background_hazard
        )
        masses[rho_index] = integrated.category_mass
        moments.append(integrated.survival_moments)
    return BridgeIntegration(
        tuple(float(value) for value in rhos),
        tuple(float(value) for value in effects),
        tuple(site_ids),
        masses,
        tuple(moments),
        hashlib.sha256(bank.tobytes(order="C")).hexdigest(),
    )


def paired_histories(
    fixed: goal007.FixedInputs, seed: arc2b.DatasetSeed
) -> tuple[tuple[arc2b.CrossLayerHistory, ...], ...]:
    """Generate the six truths using one base spread and shared random variates."""
    shocks = sample_edge_shock_vector(fixed.landscape, np.random.default_rng(seed.process_seed))
    base = compute_contrast_spread(fixed.landscape, 1.0, edge_shocks=shocks, rho=1.0)
    sites = tuple(sorted(fixed.design.sites, key=lambda site: site.site_id))
    shape = (len(sites), len(SURVEY_TIMES), 2)
    predator_uniforms = np.random.default_rng(seed.predator_detection_seed).random(shape)
    thresholds = np.random.default_rng(seed.prey_seed).exponential(size=len(sites))
    prey_uniforms = np.random.default_rng(seed.prey_detection_seed).random(shape)
    detected_predator = np.sum(predator_uniforms < DETECTION_PROBABILITY, axis=2)
    detected_prey = np.sum(prey_uniforms < DETECTION_PROBABILITY, axis=2)
    output: list[tuple[arc2b.CrossLayerHistory, ...]] = []
    for truth in TRUTHS:
        records: list[arc2b.CrossLayerHistory] = []
        for index, site in enumerate(sites):
            arrival = float(base.arrival[site.row, site.col]) / truth.rho
            extirpation = arc2b.sample_extirpation_time(
                predator_arrival=arrival,
                background_hazard=BACKGROUND_HAZARD,
                effect_multiplier=truth.effect,
                exponential_threshold=float(thresholds[index]),
            )
            present = tuple(arrival <= time for time in SURVEY_TIMES)
            alive = tuple(extirpation > time for time in SURVEY_TIMES)
            records.append(
                arc2b.CrossLayerHistory(
                    seed.phase,
                    seed.index,
                    index,
                    site.site_id,
                    site.cluster_id,
                    site.split,
                    site.row,
                    site.col,
                    arrival,
                    extirpation,
                    tuple(
                        int(detected_predator[index, survey]) if occupied else 0
                        for survey, occupied in enumerate(present)
                    ),
                    tuple(
                        int(detected_prey[index, survey]) if occupied else 0
                        for survey, occupied in enumerate(alive)
                    ),
                    present,
                    alive,
                    DETECTION_PROBABILITY,
                )
            )
        output.append(tuple(records))
    return tuple(output)


def _prepare_histories(
    histories: tuple[arc2b.CrossLayerHistory, ...], integration: BridgeIntegration
) -> tuple[tuple[arc2b.CrossLayerHistory, ...], slice | NDArray[np.int64]]:
    if not histories or len({row.site_id for row in histories}) != len(histories):
        raise ValueError("histories must contain unique sites and must not be empty")
    positions = {site_id: index for index, site_id in enumerate(integration.site_ids)}
    if any(row.site_id not in positions for row in histories):
        raise ValueError("history site is absent from the integration bank")
    if any(
        row.prey_detection_probability != DETECTION_PROBABILITY
        or len(row.predator_detection_counts) != len(SURVEY_TIMES)
        or len(row.prey_detection_counts) != len(SURVEY_TIMES)
        or any(count not in (0, 1, 2) for count in row.predator_detection_counts)
        or any(count not in (0, 1, 2) for count in row.prey_detection_counts)
        for row in histories
    ):
        raise ValueError("histories must use the known two-visit observation model")
    ordered = tuple(sorted(histories, key=lambda row: positions[row.site_id]))
    indices: slice | NDArray[np.int64] = (
        slice(None)
        if len(ordered) == len(integration.site_ids)
        else np.asarray([positions[row.site_id] for row in ordered], dtype=np.int64)
    )
    return ordered, indices


def _log_probabilities(
    histories: tuple[arc2b.CrossLayerHistory, ...],
    indices: slice | NDArray[np.int64],
    integration: BridgeIntegration,
) -> Iterator[tuple[NDArray[np.float64], NDArray[np.float64]]]:
    predator = arc2b._predator_category_probabilities(histories, DETECTION_PROBABILITY)
    events, alive = arc2b._prey_emission_coefficients(histories)
    for rho_index, all_moments in enumerate(integration.survival_moments):
        # Process one rho row: broadcasting over the full bank would copy about 0.6 GB.
        moments = all_moments[:, indices]
        weighted = np.einsum("hstc,sc->hst", moments, predator, optimize=True)
        event_probabilities = weighted[:, :, :-1] - weighted[:, :, 1:]
        joint = (
            np.einsum("hsj,sj->hs", event_probabilities, events, optimize=True)
            + weighted[:, :, -1] * alive[None, :]
        )
        predator_marginal = np.einsum(
            "sc,sc->s", integration.category_mass[rho_index, indices], predator
        )
        if (
            not np.isfinite(joint).all()
            or (joint <= 0).any()
            or not np.isfinite(predator_marginal).all()
            or (predator_marginal <= 0).any()
        ):
            raise RuntimeError("shared-arrival likelihood produced invalid probabilities")
        yield np.log(joint), np.log(predator_marginal)


def joint_log_likelihood(
    histories: tuple[arc2b.CrossLayerHistory, ...], integration: BridgeIntegration
) -> NDArray[np.float64]:
    """Return summed joint log likelihood on any unique subset of bank sites."""
    ordered, indices = _prepare_histories(histories, integration)
    result = np.empty((len(integration.rhos), len(integration.effects)), dtype=np.float64)
    for rho_index, (joint, _) in enumerate(_log_probabilities(ordered, indices, integration)):
        result[rho_index] = joint.sum(axis=1)
    return result


def evaluate_dataset(
    histories: tuple[arc2b.CrossLayerHistory, ...], integration: BridgeIntegration
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Keep the fixed training fit and held-out joint/predator scores separate."""
    ordered, indices = _prepare_histories(histories, integration)
    training = np.asarray([row.split == "training" for row in ordered])
    holdout = np.asarray([row.split == "holdout" for row in ordered])
    if (
        len(ordered) != len(integration.site_ids)
        or int(training.sum()) != 120
        or int(holdout.sum()) != 40
        or {row.cluster_id for row in ordered if row.split == "training"}.intersection(
            row.cluster_id for row in ordered if row.split == "holdout"
        )
    ):
        raise ValueError("evaluation requires the cluster-isolated 120/40 site split")
    shape = (len(integration.rhos), len(integration.effects))
    training_joint = np.empty(shape, dtype=np.float64)
    holdout_joint = np.empty(shape, dtype=np.float64)
    holdout_predator = np.empty(len(integration.rhos), dtype=np.float64)
    for rho_index, (joint, predator) in enumerate(
        _log_probabilities(ordered, indices, integration)
    ):
        training_joint[rho_index] = joint[:, training].sum(axis=1)
        holdout_joint[rho_index] = joint[:, holdout].sum(axis=1)
        holdout_predator[rho_index] = predator[holdout].sum()
    return training_joint, holdout_joint, holdout_predator
