"""Paired stochastic spread fields under landscape-resistance contrast."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, inf, isfinite

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
ETA_VALUES = (0.0, 0.5, 1.0, 1.5, 2.0)


@dataclass(frozen=True, slots=True)
class ContrastSpreadTruth:
    eta: float
    arrival: NDArray[np.float64]
    source_zone: NDArray[np.str_]
    reachable: NDArray[np.bool]
    edge_shocks: NDArray[np.float64]
    rho: float = TRUE_RATE


def geometric_mean_cost(edges: tuple[tuple[int, int, float], ...]) -> float:
    """Return the geometric mean of positive edge costs."""
    if not edges:
        raise ValueError("at least one edge is required")
    costs = np.asarray([edge[2] for edge in edges], dtype=np.float64)
    if not np.isfinite(costs).all() or np.any(costs <= 0.0):
        raise ValueError("edge costs must be finite and positive")
    return float(np.exp(np.mean(np.log(costs))))


def transform_edge_costs(
    edges: tuple[tuple[int, int, float], ...], eta: float
) -> tuple[tuple[int, int, float], ...]:
    """Apply the geometric-mean-preserving resistance contrast transform."""
    if not isfinite(eta) or eta < 0.0:
        raise ValueError("eta must be finite and non-negative")
    g = geometric_mean_cost(edges)
    if eta == 1.0:
        # Keep the accepted baseline values exactly, rather than recomputing.
        return edges
    return tuple(
        (source, target, float(g * exp(eta * np.log(cost / g)))) for source, target, cost in edges
    )


def transformed_edge_costs(
    edges: tuple[tuple[int, int, float], ...], eta: float
) -> tuple[tuple[int, int, float], ...]:
    return transform_edge_costs(edges, eta)


def sample_edge_shocks(edge_count: int, rng: np.random.Generator) -> NDArray[np.float64]:
    if edge_count <= 0:
        raise ValueError("edge_count must be positive")
    shocks = np.asarray(rng.exponential(scale=1.0, size=edge_count), dtype=np.float64)
    if not np.isfinite(shocks).all() or np.any(shocks <= 0.0):
        raise ValueError("edge shocks must be finite and positive")
    return shocks


def sample_edge_shock_vector(landscape: Landscape, rng: np.random.Generator) -> NDArray[np.float64]:
    return sample_edge_shocks(len(passable_edges(landscape)), rng)


def compute_contrast_spread(
    landscape: Landscape,
    eta: float,
    *,
    edge_shocks: NDArray[np.float64],
    rho: float = TRUE_RATE,
) -> ContrastSpreadTruth:
    """Compute one first-passage field from a supplied paired shock vector."""
    if not isfinite(rho) or rho <= 0.0:
        raise ValueError("rho must be finite and positive")
    edges = passable_edges(landscape)
    shocks = np.asarray(edge_shocks, dtype=np.float64)
    if shocks.shape != (len(edges),) or not np.isfinite(shocks).all() or np.any(shocks <= 0.0):
        raise ValueError("edge_shocks must match the positive finite edge count")
    transformed = transform_edge_costs(edges, eta)
    weighted = tuple(
        (source, target, cost * shock / rho)
        for (source, target, cost), shock in zip(transformed, shocks, strict=True)
    )
    distances, labels = multi_source_dijkstra(
        node_count=landscape.cell_count,
        weighted_edges=weighted,
        source_labels=source_labels(landscape),
    )
    arrival = np.asarray(distances, dtype=np.float64).reshape(landscape.shape)
    source_zone = np.asarray(labels, dtype="U24").reshape(landscape.shape)
    arrival = np.where(landscape.passable, arrival, inf)
    source_zone = np.where(landscape.passable, source_zone, "")
    return ContrastSpreadTruth(
        eta=float(eta),
        arrival=arrival,
        source_zone=source_zone,
        reachable=np.isfinite(arrival) & landscape.passable,
        edge_shocks=shocks.copy(),
        rho=float(rho),
    )


def compute_paired_spreads(
    landscape: Landscape,
    *,
    rng: np.random.Generator | None = None,
    edge_shocks: NDArray[np.float64] | None = None,
    etas: tuple[float, ...] = ETA_VALUES,
    rho: float = TRUE_RATE,
) -> tuple[NDArray[np.float64], tuple[ContrastSpreadTruth, ...]]:
    """Draw/reuse one edge-shock vector and compute every requested eta field."""
    if edge_shocks is None:
        if rng is None:
            raise ValueError("provide rng or edge_shocks")
        shocks = sample_edge_shock_vector(landscape, rng)
    else:
        shocks = np.asarray(edge_shocks, dtype=np.float64)
        expected = len(passable_edges(landscape))
        if shocks.shape != (expected,) or not np.isfinite(shocks).all() or np.any(shocks <= 0.0):
            raise ValueError("edge_shocks must match the positive finite edge count")
    truths = tuple(
        compute_contrast_spread(landscape, eta, edge_shocks=shocks, rho=rho) for eta in etas
    )
    return shocks.copy(), truths


# Descriptive aliases retained for downstream review code.
paired_spreads = compute_paired_spreads
build_transformed_edges = transform_edge_costs
