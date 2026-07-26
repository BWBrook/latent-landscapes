"""Frozen stochastic first-passage spread process for Goal 003."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal001.landscape import Landscape
from latent_landscapes.goal001.spread import (
    TRUE_RATE,
    multi_source_dijkstra,
    passable_edges,
    source_labels,
)

MASTER_SEED = 20260727


@dataclass(frozen=True, slots=True)
class StochasticSpreadTruth:
    arrival: NDArray[np.float64]
    source_zone: NDArray[np.str_]
    reachable: NDArray[np.bool]
    rate: float = TRUE_RATE


def sample_edge_transit_times(
    landscape: Landscape,
    rng: np.random.Generator,
    *,
    rho: float = TRUE_RATE,
) -> tuple[tuple[int, int, float], ...]:
    """Sample one exponential transit time per edge in frozen graph order."""
    if not np.isfinite(rho) or rho <= 0.0:
        raise ValueError("rho must be finite and positive")
    edges = passable_edges(landscape)
    shocks = rng.exponential(scale=1.0, size=len(edges))
    return tuple(
        (source, target, float(cost * shock / rho))
        for (source, target, cost), shock in zip(edges, shocks, strict=True)
    )


def compute_stochastic_spread(
    landscape: Landscape,
    rng: np.random.Generator,
    *,
    rho: float = TRUE_RATE,
) -> StochasticSpreadTruth:
    """Compute multi-source stochastic arrivals from one sampled edge field."""
    weighted_edges = sample_edge_transit_times(landscape, rng, rho=rho)
    distances, labels = multi_source_dijkstra(
        node_count=landscape.cell_count,
        weighted_edges=weighted_edges,
        source_labels=source_labels(landscape),
    )
    arrival = np.asarray(distances, dtype=np.float64).reshape(landscape.shape)
    source_zone = np.asarray(labels, dtype="U24").reshape(landscape.shape)
    # Water is outside the graph and therefore remains explicitly unreachable.
    arrival = np.where(landscape.passable, arrival, inf)
    source_zone = np.where(landscape.passable, source_zone, "")
    reachable = np.isfinite(arrival) & landscape.passable
    return StochasticSpreadTruth(
        arrival=arrival,
        source_zone=source_zone,
        reachable=reachable,
        rate=rho,
    )


# Friendly aliases used by review code and downstream tests.
stochastic_spread = compute_stochastic_spread
sample_transit_times = sample_edge_transit_times
