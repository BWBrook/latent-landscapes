"""Exact site-varying background likelihood on the fixed empirical arrival bank.

Arrival categories retain one pseudo-arrival each (alpha=1).  Category transforms
are shared across survey times and observation histories; no quadrature or
interpolation replaces an empirical arrival.  The oracle entry point is separate
and returns prey observation likelihoods conditional on supplied true arrivals.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes.arc2c_design import BACKGROUND_HAZARD, DETECTION_PROBABILITY
from latent_landscapes.arc2c_likelihood import BridgeIntegration
from latent_landscapes.goal004.observations import SURVEY_TIMES

FloatArray = NDArray[np.float64]


class PreyHistory(Protocol):
    """Observation-only fields used by the explicitly oracle calculation."""

    @property
    def site_id(self) -> str: ...

    @property
    def cluster_id(self) -> str: ...

    @property
    def split(self) -> str: ...

    @property
    def prey_detection_counts(self) -> tuple[int, ...]: ...

    @property
    def prey_detection_probability(self) -> float: ...


@dataclass(frozen=True, slots=True)
class PreparedBank:
    """Bank quantities reusable for every background coefficient and history.

    All arrays are read-only.  ``arrival_offsets[site][category]`` contains each
    empirical arrival minus its category's upper survey edge.  Only categories
    zero through five need transforms; the final category contributes counts.
    Site-valued arguments to ``build_integration`` follow ``site_ids`` exactly.
    """

    site_ids: tuple[str, ...]
    bank_size: int
    category_counts: NDArray[np.int64]
    category_mass: FloatArray
    arrival_offsets: tuple[tuple[FloatArray, ...], ...]
    bank_checksum: str


def _site_identifiers(site_ids: Sequence[str]) -> tuple[str, ...]:
    identifiers = tuple(site_ids)
    if (
        not identifiers
        or any(not isinstance(value, str) or not value for value in identifiers)
        or len(set(identifiers)) != len(identifiers)
    ):
        raise ValueError("site identifiers must be nonempty and unique")
    return identifiers


def _effects(effects: Sequence[float]) -> FloatArray:
    values = np.asarray(effects, dtype=np.float64)
    if (
        values.ndim != 1
        or not values.size
        or not np.isfinite(values).all()
        or (values < 1.0).any()
        or (np.diff(values) <= 0.0).any()
    ):
        raise ValueError("effects must be finite, strictly increasing and at least one")
    return values


def _site_hazards(site_hazards: FloatArray, site_count: int) -> FloatArray:
    hazards = np.asarray(site_hazards, dtype=np.float64)
    if hazards.shape != (site_count,) or not np.isfinite(hazards).all() or (hazards <= 0.0).any():
        raise ValueError("site hazards must be finite, positive and match site identifiers")
    return hazards


def prepare_bank(bank: FloatArray, site_ids: Sequence[str]) -> PreparedBank:
    """Group the rho=1 bank once, preserving its empirical-plus-seven-pseudo law."""
    identifiers = _site_identifiers(site_ids)
    arrivals = np.asarray(bank, dtype=np.float64)
    if (
        arrivals.ndim != 2
        or arrivals.shape[1] != len(identifiers)
        or not arrivals.shape[0]
        or not np.isfinite(arrivals).all()
        or (arrivals < 0.0).any()
    ):
        raise ValueError("arrival bank must be finite, nonnegative and match site identifiers")
    counts = np.empty((len(identifiers), arc2b.CATEGORY_COUNT), dtype=np.int64)
    groups: list[tuple[FloatArray, ...]] = []
    survey_times = np.asarray(SURVEY_TIMES, dtype=np.float64)
    for site_index in range(len(identifiers)):
        site_arrivals = arrivals[:, site_index]
        categories = np.searchsorted(survey_times, site_arrivals, side="left")
        counts[site_index] = np.bincount(categories, minlength=arc2b.CATEGORY_COUNT)
        site_groups: list[FloatArray] = []
        for category, upper_edge in enumerate(survey_times):
            offsets = site_arrivals[categories == category] - upper_edge
            offsets.setflags(write=False)
            site_groups.append(offsets)
        groups.append(tuple(site_groups))
    masses = (counts + 1.0) / (arrivals.shape[0] + arc2b.CATEGORY_COUNT)
    counts.setflags(write=False)
    masses.setflags(write=False)
    checksum = hashlib.sha256(np.ascontiguousarray(arrivals).view(np.uint8)).hexdigest()
    return PreparedBank(identifiers, arrivals.shape[0], counts, masses, tuple(groups), checksum)


def normalized_hazards(
    beta: float,
    all_map_A: FloatArray,
    site_A: FloatArray,
    mean_hazard: float = BACKGROUND_HAZARD,
) -> FloatArray:
    """Normalize exp(beta*A) over all map cells, then evaluate sampled sites.

    ``all_map_A`` may be a vector or a two-dimensional map.  It must include the
    complete map, including cells outside both the training and holdout sets.
    ``site_A`` follows the bank's site order.  A common shift avoids overflow.
    """
    whole_map = np.asarray(all_map_A, dtype=np.float64)
    sites = np.asarray(site_A, dtype=np.float64)
    if (
        not math.isfinite(beta)
        or not math.isfinite(mean_hazard)
        or mean_hazard <= 0.0
        or whole_map.ndim not in (1, 2)
        or not whole_map.size
        or not np.isfinite(whole_map).all()
        or sites.ndim != 1
        or not sites.size
        or not np.isfinite(sites).all()
    ):
        raise ValueError("beta, mean hazard and complete-map/site covariates must be valid")
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            scaled_map = beta * whole_map
            shift = float(scaled_map.max())
            denominator = float(np.exp(scaled_map - shift).mean())
            hazards = mean_hazard * np.exp(beta * sites - shift) / denominator
    except FloatingPointError as error:
        raise ValueError("normalized hazards exceed finite floating-point range") from error
    return _site_hazards(hazards, len(sites))


def build_integration(
    prepared: PreparedBank, effects: Sequence[float], site_hazards: FloatArray
) -> BridgeIntegration:
    """Construct one beta row of exact alpha=1 moments for all requested effects.

    Each empirical arrival enters one exponential sum per effect.  Centering at
    the category upper edge keeps every exponent nonpositive for h >= 1 and
    permits reuse of that sum at every subsequent survey.  The resulting object
    uses the unchanged shared-arrival scorer and its fixed training/holdout split.
    """
    candidates = _effects(effects)
    hazards = _site_hazards(site_hazards, len(prepared.site_ids))
    times = np.asarray((0.0, *SURVEY_TIMES), dtype=np.float64)
    denominator = prepared.bank_size + arc2b.CATEGORY_COUNT
    moments = np.empty(
        (len(candidates), len(prepared.site_ids), len(times), arc2b.CATEGORY_COUNT),
        dtype=np.float64,
    )
    for site_index, hazard in enumerate(hazards):
        q = hazard * (candidates - 1.0)
        if not np.isfinite(q).all():
            raise ValueError("hazard times effect must remain finite")
        background_survival = np.exp(-hazard * times)
        for category in range(arc2b.CATEGORY_COUNT):
            mass = prepared.category_mass[site_index, category]
            moments[:, site_index, : category + 1, category] = (
                mass * background_survival[: category + 1]
            )
            if category == len(SURVEY_TIMES):
                continue
            upper_edge = float(SURVEY_TIMES[category])
            offsets = prepared.arrival_offsets[site_index][category]
            # In-place exp avoids retaining both an h-by-arrival product and exp.
            transformed = q[:, None] * offsets[None, :]
            np.exp(transformed, out=transformed)
            transform_sum = transformed.sum(axis=1)
            del transformed
            transform_sum += np.exp(q * (arc2b.PSEUDO_ARRIVALS[category] - upper_edge))
            later_times = times[category + 1 :]
            moments[:, site_index, category + 1 :, category] = (
                np.exp(-hazard * later_times[None, :] - q[:, None] * (later_times - upper_edge))
                * (transform_sum / denominator)[:, None]
            )
    if not np.isfinite(moments).all() or (moments < 0.0).any():
        raise RuntimeError("adjusted-background integration produced invalid moments")
    return BridgeIntegration(
        (1.0,),
        tuple(float(value) for value in candidates),
        prepared.site_ids,
        prepared.category_mass[None, :, :],
        (moments,),
        prepared.bank_checksum,
    )


def oracle_evaluate_dataset(
    histories: Sequence[PreyHistory],
    true_arrivals: FloatArray,
    effects: Sequence[float],
    site_hazards: FloatArray,
    *,
    site_ids: Sequence[str],
) -> tuple[FloatArray, FloatArray]:
    """Return training/holdout prey log likelihoods conditional on true arrivals.

    This is an explicitly oracle diagnostic, not an analyst fit.  ``true_arrivals``
    and ``site_hazards`` both follow the supplied ``site_ids``; histories are joined
    by their identifiers.  Predator observations contribute no h/beta information
    once arrivals are supplied and are absent from these conditional prey scores.
    """
    identifiers = _site_identifiers(site_ids)
    candidates = _effects(effects)
    hazards = _site_hazards(site_hazards, len(identifiers))
    arrivals = np.asarray(true_arrivals, dtype=np.float64)
    if (
        arrivals.shape != (len(identifiers),)
        or not np.isfinite(arrivals).all()
        or (arrivals < 0.0).any()
    ):
        raise ValueError("true arrivals must be finite, nonnegative and match site identifiers")
    if len(histories) != len(identifiers) or {row.site_id for row in histories} != set(identifiers):
        raise ValueError("oracle histories must match every site identifier exactly once")
    positions = {identifier: index for index, identifier in enumerate(identifiers)}
    ordered = tuple(sorted(histories, key=lambda row: positions[row.site_id]))
    if any(
        row.prey_detection_probability != DETECTION_PROBABILITY
        or len(row.prey_detection_counts) != len(SURVEY_TIMES)
        or any(count not in (0, 1, 2) for count in row.prey_detection_counts)
        for row in ordered
    ):
        raise ValueError("oracle histories must use the known two-visit prey observation model")
    training = np.asarray([row.split == "training" for row in ordered])
    holdout = np.asarray([row.split == "holdout" for row in ordered])
    if (
        len(ordered) != 160
        or int(training.sum()) != 120
        or int(holdout.sum()) != 40
        or {row.cluster_id for row in ordered if row.split == "training"}.intersection(
            row.cluster_id for row in ordered if row.split == "holdout"
        )
    ):
        raise ValueError("oracle evaluation requires the cluster-isolated 120/40 site split")
    times = np.asarray((0.0, *SURVEY_TIMES), dtype=np.float64)
    post_arrival = np.maximum(times[None, :] - arrivals[:, None], 0.0)
    survival = np.exp(
        -hazards[None, :, None]
        * (times[None, None, :] + (candidates[:, None, None] - 1.0) * post_arrival)
    )
    events, alive = arc2b._prey_emission_coefficients(cast(Any, ordered))
    prey = np.einsum("hsj,sj->hs", survival[:, :, :-1] - survival[:, :, 1:], events)
    prey += survival[:, :, -1] * alive[None, :]
    if not np.isfinite(prey).all() or (prey <= 0.0).any():
        raise RuntimeError("oracle prey likelihood produced invalid probabilities")
    log_prey = np.log(prey)
    return log_prey[:, training].sum(axis=1), log_prey[:, holdout].sum(axis=1)
