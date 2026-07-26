"""Deterministic habitat-weighted predator spread for Goal 001."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from heapq import heappop, heappush
from math import inf

import numpy as np
from numpy.typing import NDArray

from .landscape import Landscape

LEGACY_SPREAD_PATH = "src/spatext/synth/medium/spread_impact.py"
LEGACY_SPREAD_BLOB_SHA1 = "cb15f2178ff9e2f359f06fdac34a9b551e163cd5"

TRUE_RATE = 1.0
CONDUCTANCE = {
    "low_quality_matrix": 0.33,
    "medium_quality": 0.64,
    "high_quality_patch": 0.90,
    "corridor": 1.12,
    "source_zone": 1.36,
}


@dataclass(frozen=True, slots=True)
class SpreadTruth:
    arrival: NDArray[np.float64]
    source_zone: NDArray[np.str_]
    reachable: NDArray[np.bool]
    rate: float = TRUE_RATE


def edge_cost(
    *,
    source_conductance: float,
    target_conductance: float,
    source_water_neighbors: int,
    target_water_neighbors: int,
) -> float:
    mean_conductance = (source_conductance + target_conductance) / 2.0
    combined_water_neighbors = source_water_neighbors + target_water_neighbors
    return 0.88 / mean_conductance + 0.46 * combined_water_neighbors / 4.0


def multi_source_dijkstra(
    *,
    node_count: int,
    weighted_edges: Iterable[tuple[int, int, float]],
    source_labels: Mapping[int, str],
) -> tuple[tuple[float, ...], tuple[str, ...]]:
    neighbors: list[list[tuple[int, float]]] = [[] for _ in range(node_count)]
    for source, target, cost in weighted_edges:
        neighbors[source].append((target, cost))
        neighbors[target].append((source, cost))
    for values in neighbors:
        values.sort(key=lambda item: item[0])

    distances = [inf] * node_count
    labels = [""] * node_count
    heap: list[tuple[float, str, int]] = []
    for node, label in sorted(source_labels.items()):
        distances[node] = 0.0
        labels[node] = label
        heappush(heap, (0.0, label, node))

    while heap:
        distance, label, node = heappop(heap)
        if distance > distances[node] + 1e-12 or label != labels[node]:
            continue
        for target, cost in neighbors[node]:
            candidate = distance + cost
            prior = distances[target]
            if candidate < prior - 1e-12 or (
                abs(candidate - prior) <= 1e-12 and label < labels[target]
            ):
                distances[target] = candidate
                labels[target] = label
                heappush(heap, (candidate, label, target))
    return tuple(distances), tuple(labels)


def compute_spread(landscape: Landscape) -> SpreadTruth:
    weighted_edges: list[tuple[int, int, float]] = []
    for row in range(landscape.rows):
        for col in range(landscape.cols):
            if not landscape.passable[row, col]:
                continue
            source_id = row * landscape.cols + col
            for target_row, target_col in ((row + 1, col), (row, col + 1)):
                if target_row >= landscape.rows or target_col >= landscape.cols:
                    continue
                if not landscape.passable[target_row, target_col]:
                    continue
                target_id = target_row * landscape.cols + target_col
                weighted_edges.append(
                    (
                        source_id,
                        target_id,
                        edge_cost(
                            source_conductance=CONDUCTANCE[str(landscape.habitat_class[row, col])],
                            target_conductance=CONDUCTANCE[
                                str(landscape.habitat_class[target_row, target_col])
                            ],
                            source_water_neighbors=int(landscape.water_neighbor_count[row, col]),
                            target_water_neighbors=int(
                                landscape.water_neighbor_count[target_row, target_col]
                            ),
                        ),
                    )
                )

    source_labels = {
        row * landscape.cols + col: str(landscape.source_zone[row, col])
        for row in range(landscape.rows)
        for col in range(landscape.cols)
        if landscape.source_zone[row, col]
    }
    distance_values, label_values = multi_source_dijkstra(
        node_count=landscape.cell_count,
        weighted_edges=weighted_edges,
        source_labels=source_labels,
    )
    arrival = np.asarray(distance_values, dtype=np.float64).reshape(landscape.shape)
    source_zone = np.asarray(label_values, dtype="U24").reshape(landscape.shape)
    reachable = np.isfinite(arrival) & landscape.passable
    return SpreadTruth(arrival=arrival, source_zone=source_zone, reachable=reachable)
