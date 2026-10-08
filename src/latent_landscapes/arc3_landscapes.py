"""Procedural landscape archetypes for the Arc 3 generality experiment.

The generator deliberately returns the existing Goal 001 ``Landscape`` data
structure.  Geometry is stochastic within a fixed, finite design, while the
cell inventory and source geometry are held constant across archetypes.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import replace
from math import hypot
from typing import Final

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal001.landscape import (
    COLS,
    ROWS,
    Landscape,
    rook_neighbors,
    source_zone_definitions,
)
from latent_landscapes.goal001.spread import compute_spread, passable_edges

ARCHETYPES: Final[tuple[str, ...]] = ("connected", "corridor", "barrier")
EXPECTED_COUNTS: Final[dict[str, int]] = {
    "water": 823,
    "low_quality_matrix": 3449,
    "medium_quality": 835,
    "high_quality_patch": 682,
    "corridor": 178,
    "source_zone": 81,
}

_SOURCE_NAMES: Final[tuple[str, ...]] = tuple(
    source.source_zone_id for source in source_zone_definitions()
)


def build_landscape(archetype: str, seed: int) -> Landscape:
    """Build one deterministic realization of an Arc 3 landscape archetype."""

    if archetype not in ARCHETYPES:
        raise ValueError(f"archetype must be one of {ARCHETYPES}, got {archetype!r}")
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise TypeError("seed must be an integer")

    rng = np.random.default_rng(int(seed))
    source_zone = _source_mask()
    skeleton = _corridor_skeleton(rng, source_zone)
    if archetype == "barrier":
        water = _barrier_water(rng, source_zone)
    else:
        water = _dispersed_water(rng, source_zone, skeleton)
    passable = ~water

    if archetype == "corridor":
        corridor_cells = _corridor_cells(skeleton, passable, source_zone, rng)
    else:
        corridor_cells = _sparse_corridor_cells(passable, source_zone, rng)

    high_cells, medium_cells = _quality_cells(
        archetype,
        passable,
        source_zone,
        corridor_cells,
        rng,
    )
    habitat = np.full((ROWS, COLS), "low_quality_matrix", dtype="U24")
    habitat[water] = "water"
    habitat[high_cells] = "high_quality_patch"
    habitat[medium_cells] = "medium_quality"
    corridor_mask = _cells_mask(corridor_cells)
    habitat[corridor_mask] = "corridor"
    habitat[source_zone != ""] = "source_zone"

    patch_id = np.full((ROWS, COLS), "", dtype="U32")
    corridor_id = np.full((ROWS, COLS), "", dtype="U32")
    patch_labels = _patch_labels(high_cells, archetype)
    patch_id[high_cells] = patch_labels[high_cells]
    corridor_id[corridor_mask] = np.asarray("corridor", dtype="U32")

    quality = _quality_metadata(habitat)
    source_reachable = _source_reachability(passable, source_zone)
    water_neighbors = _water_neighbor_count(water)
    landscape = Landscape(
        passable=passable,
        source_reachable=source_reachable,
        habitat_class=habitat,
        quality=quality,
        patch_id=patch_id,
        corridor_id=corridor_id,
        source_zone=source_zone,
        water_neighbor_count=water_neighbors,
    )
    checks = map_checks(landscape)
    if not checks["inventory_exact"] or not checks["source_geometry_exact"]:
        raise RuntimeError("procedural landscape failed its fixed structural inventory")
    if not checks["all_passable_source_reachable"] or not checks["single_passable_component"]:
        raise RuntimeError(
            "procedural landscape is structurally infeasible: passable graph disconnected"
        )
    return landscape


def describe_landscape(landscape: Landscape) -> dict[str, object]:
    """Return JSON-compatible structural and graph descriptors for a landscape."""

    counts = {name: int(np.sum(landscape.habitat_class == name)) for name in EXPECTED_COUNTS}
    spread = compute_spread(landscape)
    source_mask = landscape.source_zone != ""
    non_source = landscape.passable & ~source_mask
    all_arrivals = spread.arrival[landscape.passable]
    arrivals = spread.arrival[non_source]
    if not np.isfinite(all_arrivals).all() or not np.isfinite(arrivals).all():
        raise ValueError("landscape has non-finite arrival times on passable cells")

    component_count = _component_count(landscape.passable)
    geometric_steps = _rook_distances(landscape.passable, source_mask)[non_source]
    nearest_manhattan = _nearest_source_manhattan(non_source)
    detour = geometric_steps / nearest_manhattan

    ablated_habitat = landscape.habitat_class.copy()
    ablated_habitat[ablated_habitat == "corridor"] = "low_quality_matrix"
    ablated = replace(landscape, habitat_class=ablated_habitat)
    ablated_arrival = compute_spread(ablated).arrival[non_source]
    arrival_ratio = ablated_arrival / arrivals

    costs = np.asarray([edge[2] for edge in passable_edges(landscape)], dtype=np.float64)
    mean_cost = float(np.mean(costs))
    cost_sd = float(np.std(costs))
    cost_summary = {
        "minimum": float(np.min(costs)),
        "maximum": float(np.max(costs)),
        "median": float(np.median(costs)),
        "q90": float(np.quantile(costs, 0.90)),
        "mean": mean_cost,
        "sd": cost_sd,
        "coefficient_of_variation": float(cost_sd / mean_cost),
    }
    descriptor: dict[str, object] = {
        "shape": [int(landscape.rows), int(landscape.cols)],
        "counts": counts,
        "habitat_counts": counts.copy(),
        "source_reachable_fraction": float(np.mean(landscape.source_reachable[landscape.passable])),
        "component_count": int(component_count),
        "deterministic_unit_shock": {
            "rho": 1.0,
            "eta": 1.0,
            "arrival_median": float(np.median(all_arrivals)),
            "arrival_q90": float(np.quantile(all_arrivals, 0.90)),
            "non_source_arrival_median": float(np.median(arrivals)),
            "non_source_arrival_q90": float(np.quantile(arrivals, 0.90)),
        },
        "least_cost_arrival_median": float(np.median(all_arrivals)),
        "least_cost_arrival_q90": float(np.quantile(all_arrivals, 0.90)),
        "geometric_detour": {
            "median": float(np.median(detour)),
            "q90": float(np.quantile(detour, 0.90)),
            "source_cells_excluded": True,
        },
        "geometric_detour_median": float(np.median(detour)),
        "geometric_detour_q90": float(np.quantile(detour, 0.90)),
        "corridor_ablation_arrival_ratio": {
            "median": float(np.median(arrival_ratio)),
            "q90": float(np.quantile(arrival_ratio, 0.90)),
            "replacement_class": "low_quality_matrix",
        },
        "corridor_ablation_ratio_median": float(np.median(arrival_ratio)),
        "corridor_ablation_ratio_q90": float(np.quantile(arrival_ratio, 0.90)),
        "cost_heterogeneity": cost_summary,
        "edge_cost_coefficient_of_variation": cost_summary["coefficient_of_variation"],
    }
    return descriptor


def map_checks(landscape: Landscape) -> dict[str, object]:
    """Return finite structural checks without modifying the supplied map."""

    counts = Counter(str(value) for value in landscape.habitat_class.ravel())
    expected_source = _source_mask()
    finite = bool(
        np.isfinite(landscape.quality).all() and np.isfinite(landscape.water_neighbor_count).all()
    )
    passable_component_count = _component_count(landscape.passable)
    return {
        "shape_is_expected": landscape.shape == (ROWS, COLS),
        "inventory_exact": dict(counts) == EXPECTED_COUNTS,
        "source_geometry_exact": bool(np.array_equal(landscape.source_zone, expected_source)),
        "all_sources_passable": bool(np.all(landscape.passable[expected_source != ""])),
        "all_passable_source_reachable": bool(
            np.array_equal(landscape.source_reachable, landscape.passable)
        ),
        "single_passable_component": passable_component_count == 1,
        "component_count": int(passable_component_count),
        "finite_metadata": finite,
    }


def _source_mask() -> NDArray[np.str_]:
    source_zone = np.full((ROWS, COLS), "", dtype="U24")
    for source in source_zone_definitions():
        source_zone[
            source.row_start : source.row_end + 1,
            source.col_start : source.col_end + 1,
        ] = source.source_zone_id
    return source_zone


def _cells_mask(cells: set[tuple[int, int]]) -> NDArray[np.bool]:
    mask = np.zeros((ROWS, COLS), dtype=np.bool)
    for row, col in cells:
        mask[row, col] = True
    return mask


def _corridor_skeleton(
    rng: np.random.Generator, source_zone: NDArray[np.str_]
) -> set[tuple[int, int]]:
    # A two-cell jitter stays inside the approved +/-3 envelope and keeps the
    # route union above the minimum 160-cell construction size.
    north_row = int(10 + rng.integers(-2, 3))
    south_row = int(60 + rng.integers(-2, 3))
    join_col = int(40 + rng.integers(-4, 5))
    cells = _line_cells((north_row, 3), (north_row, 60))
    cells.update(_line_cells((south_row, 3), (south_row, 60)))
    cells.update(_line_cells((north_row, join_col), (south_row, join_col)))
    cells = {cell for cell in cells if not source_zone[cell]}
    if not 160 <= len(cells) <= 172:
        raise RuntimeError(f"corridor skeleton has infeasible size {len(cells)}")
    return cells


def _line_cells(start: tuple[int, int], end: tuple[int, int]) -> set[tuple[int, int]]:
    row_start, col_start = start
    row_end, col_end = end
    steps = max(abs(row_end - row_start), abs(col_end - col_start))
    if steps == 0:
        return {start}
    return {
        (
            round(row_start + (row_end - row_start) * step / steps),
            round(col_start + (col_end - col_start) * step / steps),
        )
        for step in range(steps + 1)
    }


def _dispersed_water(
    rng: np.random.Generator,
    source_zone: NDArray[np.str_],
    protected_skeleton: set[tuple[int, int]],
) -> NDArray[np.bool]:
    centers: list[tuple[float, float, float, float]] = []
    for _index in range(12):
        row = float(rng.uniform(5.0, ROWS - 5.0))
        col = float(rng.uniform(10.0, COLS - 8.0))
        row_radius = float(rng.uniform(3.8, 6.2))
        col_radius = float(rng.uniform(4.0, 7.0))
        centers.append((row, col, row_radius, col_radius))
    protected = source_zone != ""
    for row, col in protected_skeleton:
        protected[row, col] = True
    scores = np.full((ROWS, COLS), -np.inf, dtype=np.float64)
    for row in range(ROWS):
        for col in range(COLS):
            if protected[row, col]:
                continue
            footprint = 0.0
            for center_row, center_col, row_radius, col_radius in centers:
                distance = hypot(
                    (row - center_row) / row_radius,
                    (col - center_col) / col_radius,
                )
                footprint = max(footprint, 1.0 - distance)
            scores[row, col] = footprint + 1e-6 * float(rng.random())
    water = np.zeros((ROWS, COLS), dtype=np.bool)
    _repair_connected_water(water, scores, protected, EXPECTED_COUNTS["water"])
    return water


def _barrier_water(rng: np.random.Generator, source_zone: NDArray[np.str_]) -> NDArray[np.bool]:
    water = np.zeros((ROWS, COLS), dtype=np.bool)
    centers = tuple(int(base + rng.integers(-1, 2)) for base in (26, 46, 66))
    gap_centers = [int(value) for value in rng.integers((9, 33, 57), (16, 40, 64))]
    protected = source_zone != ""
    for center, gap_center in zip(centers, gap_centers, strict=True):
        columns = range(center - 2, center + 2)
        gap_rows = set(range(gap_center - 3, gap_center + 3))
        for row in gap_rows:
            for col in columns:
                protected[row, col] = True
        for row in range(ROWS):
            if row in gap_rows:
                continue
            for col in columns:
                water[row, col] = True
    remaining = EXPECTED_COUNTS["water"] - int(water.sum())
    if remaining < 0:
        raise RuntimeError("barrier bands exceed the fixed water inventory")
    if remaining:
        scores = np.full((ROWS, COLS), -np.inf, dtype=np.float64)
        center_row = float(rng.uniform(20.0, 52.0))
        center_col = float(rng.uniform(10.0, 76.0))
        for row in range(ROWS):
            for col in range(COLS):
                if water[row, col] or protected[row, col]:
                    continue
                distance = hypot((row - center_row) / 4.0, (col - center_col) / 6.0)
                scores[row, col] = 1.0 - distance + 1e-6 * float(rng.random())
        protected = source_zone != ""
        _repair_connected_water(water, scores, protected, EXPECTED_COUNTS["water"])
    if int(water.sum()) != EXPECTED_COUNTS["water"]:
        raise RuntimeError("unable to construct the requested barrier water inventory")
    return water


def _repair_connected_water(
    water: NDArray[np.bool],
    scores: NDArray[np.float64],
    protected: NDArray[np.bool],
    target_count: int,
) -> None:
    """Construct the fixed water inventory and repair only structural disconnection."""

    selected = int(water.sum())
    if selected > target_count:
        raise RuntimeError("initial water mask exceeds the fixed inventory")
    # First take the compact, high-scoring footprint.  Connectivity is checked
    # only after the full candidate geometry is selected, avoiding seed-based
    # retries while keeping the generator inexpensive.
    for flat_index in np.argsort(scores.ravel(), kind="stable")[::-1]:
        row, col = divmod(int(flat_index), COLS)
        if water[row, col] or protected[row, col] or not np.isfinite(scores[row, col]):
            continue
        water[row, col] = True
        selected += 1
        if selected == target_count:
            break
    if selected != target_count:
        raise RuntimeError("unable to construct the requested water inventory")

    # Open shortest deterministic water paths between passable components.
    # This is a structural repair of the prescribed map, not recovery-based
    # seed selection.  Refill any opened cells from low-scoring candidates and
    # retain the one-component invariant for each refill.
    while _component_count(~water) > 1:
        components = _passable_components(~water)
        largest = max(components, key=len)
        for component in sorted(components, key=len):
            if component is largest:
                continue
            _open_path_to_component(water, component, set(largest))
            break
    for flat_index in np.argsort(scores.ravel(), kind="stable"):
        if int(water.sum()) == target_count:
            return
        row, col = divmod(int(flat_index), COLS)
        if water[row, col] or protected[row, col] or not np.isfinite(scores[row, col]):
            continue
        water[row, col] = True
        if _component_count(~water) != 1:
            water[row, col] = False
    if int(water.sum()) != target_count:
        raise RuntimeError("unable to preserve a connected passable graph at fixed water count")


def _corridor_cells(
    skeleton: set[tuple[int, int]],
    passable: NDArray[np.bool],
    source_zone: NDArray[np.str_],
    rng: np.random.Generator,
) -> set[tuple[int, int]]:
    cells = {cell for cell in skeleton if passable[cell] and not source_zone[cell]}
    if len(cells) > EXPECTED_COUNTS["corridor"]:
        raise RuntimeError("protected corridor skeleton exceeds corridor inventory")
    candidates = [
        (row, col)
        for row in range(ROWS)
        for col in range(COLS)
        if passable[row, col] and not source_zone[row, col] and (row, col) not in cells
    ]
    candidates.sort(key=lambda cell: (_distance_to_set(cell, cells), float(rng.random())))
    cells.update(candidates[: EXPECTED_COUNTS["corridor"] - len(cells)])
    if len(cells) != EXPECTED_COUNTS["corridor"]:
        raise RuntimeError("unable to fill the protected corridor inventory")
    return cells


def _sparse_corridor_cells(
    passable: NDArray[np.bool],
    source_zone: NDArray[np.str_],
    rng: np.random.Generator,
) -> set[tuple[int, int]]:
    candidates = [
        (row, col)
        for row in range(ROWS)
        for col in range(COLS)
        if passable[row, col] and not source_zone[row, col]
    ]
    random_order = {cell: float(rng.random()) for cell in candidates}
    candidates.sort(key=lambda cell: random_order[cell], reverse=True)
    cells: set[tuple[int, int]] = set()
    for cell in candidates:
        if any(neighbor in cells for neighbor in rook_neighbors(*cell)):
            continue
        cells.add(cell)
        if len(cells) == EXPECTED_COUNTS["corridor"]:
            return cells
    raise RuntimeError("unable to construct isolated corridor inventory")


def _quality_cells(
    archetype: str,
    passable: NDArray[np.bool],
    source_zone: NDArray[np.str_],
    corridor_cells: set[tuple[int, int]],
    rng: np.random.Generator,
) -> tuple[NDArray[np.bool], NDArray[np.bool]]:
    available = passable.copy()
    available[source_zone != ""] = False
    for row, col in corridor_cells:
        available[row, col] = False
    if archetype == "corridor":
        high_score, medium_score = _patch_scores(rng)
    else:
        high_score, medium_score = _backbone_scores(rng)
    high = _take_highest(high_score, available, EXPECTED_COUNTS["high_quality_patch"])
    available[high] = False
    medium = _take_highest(medium_score, available, EXPECTED_COUNTS["medium_quality"])
    return high, medium


def _patch_scores(rng: np.random.Generator) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    scores = np.zeros((ROWS, COLS), dtype=np.float64)
    halos = np.zeros((ROWS, COLS), dtype=np.float64)
    row_centers = (int(18 + rng.integers(-2, 3)), int(54 + rng.integers(-2, 3)))
    col_centers = tuple(
        int(value) for value in rng.choice(np.arange(16, 69), size=3, replace=False)
    )
    centers = [(row, col) for row in row_centers for col in col_centers]
    jitter = rng.random((ROWS, COLS))
    for row in range(ROWS):
        for col in range(COLS):
            distances = [
                hypot((row - center_row) / 5.0, (col - center_col) / 7.0)
                for center_row, center_col in centers
            ]
            nearest = min(distances)
            scores[row, col] = 1.0 - nearest + 1e-4 * jitter[row, col]
            halos[row, col] = 1.0 - nearest / 1.75 + 1e-4 * jitter[row, col]
    return scores, halos


def _backbone_scores(rng: np.random.Generator) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    row_centers = (15.0, 36.0, 57.0)
    high = np.zeros((ROWS, COLS), dtype=np.float64)
    medium = np.zeros((ROWS, COLS), dtype=np.float64)
    phase = float(rng.uniform(0.0, 2.0 * np.pi))
    for row in range(ROWS):
        for col in range(COLS):
            bands = [np.exp(-0.5 * ((row - center) / 6.5) ** 2) for center in row_centers]
            high[row, col] = max(bands) + 0.08 * np.sin(col / 8.0 + phase)
            medium[row, col] = max(
                np.exp(-0.5 * ((row - center) / 10.0) ** 2) for center in row_centers
            ) + 0.06 * np.cos(col / 7.0 + phase)
    return high, medium


def _take_highest(
    scores: NDArray[np.float64], available: NDArray[np.bool], count: int
) -> NDArray[np.bool]:
    masked = np.where(available, scores, -np.inf)
    order = np.argsort(masked.ravel(), kind="stable")[::-1]
    selected = np.zeros((ROWS, COLS), dtype=np.bool)
    chosen = 0
    for flat_index in order:
        row, col = divmod(int(flat_index), COLS)
        if not np.isfinite(masked[row, col]):
            continue
        selected[row, col] = True
        chosen += 1
        if chosen == count:
            return selected
    raise RuntimeError("unable to allocate exact habitat inventory")


def _patch_labels(cells: NDArray[np.bool], archetype: str) -> NDArray[np.str_]:
    labels = np.full((ROWS, COLS), "", dtype="U32")
    if archetype == "corridor":
        centers = [(row, col) for row in (18, 54) for col in (18, 42, 66)]
    else:
        centers = [(row, 0) for row in (15, 36, 57)]
    for row, col in np.argwhere(cells):
        distances = [hypot(float(row - r), float(col - c)) for r, c in centers]
        labels[row, col] = f"patch_{int(np.argmin(distances))}"
    return labels


def _quality_metadata(habitat: NDArray[np.str_]) -> NDArray[np.float64]:
    values = np.zeros((ROWS, COLS), dtype=np.float64)
    representatives = {
        "water": 0.0,
        "low_quality_matrix": 0.28,
        "medium_quality": 0.58,
        "high_quality_patch": 0.88,
        "corridor": 0.72,
        "source_zone": 0.92,
    }
    for name, value in representatives.items():
        values[habitat == name] = value
    return values


def _source_reachability(
    passable: NDArray[np.bool], source_zone: NDArray[np.str_]
) -> NDArray[np.bool]:
    reachable = np.zeros((ROWS, COLS), dtype=np.bool)
    queue: deque[tuple[int, int]] = deque()
    for row, col in np.argwhere(source_zone != ""):
        coordinate = int(row), int(col)
        if passable[coordinate]:
            reachable[coordinate] = True
            queue.append(coordinate)
    while queue:
        row, col = queue.popleft()
        for target in rook_neighbors(row, col):
            if passable[target] and not reachable[target]:
                reachable[target] = True
                queue.append(target)
    return reachable


def _water_neighbor_count(water: NDArray[np.bool]) -> NDArray[np.int16]:
    counts = np.zeros((ROWS, COLS), dtype=np.int16)
    for row in range(ROWS):
        for col in range(COLS):
            counts[row, col] = sum(water[target] for target in rook_neighbors(row, col))
    return counts


def _component_count(passable: NDArray[np.bool]) -> int:
    return len(_passable_components(passable))


def _passable_components(passable: NDArray[np.bool]) -> list[set[tuple[int, int]]]:
    unseen: set[tuple[int, int]] = {(int(row), int(col)) for row, col in np.argwhere(passable)}
    components: list[set[tuple[int, int]]] = []
    while unseen:
        component = {unseen.pop()}
        queue = deque(component)
        while queue:
            cell = queue.popleft()
            for neighbor in rook_neighbors(*cell):
                if neighbor in unseen and passable[neighbor]:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)
        components.append(component)
    return components


def _open_path_to_component(
    water: NDArray[np.bool],
    component: set[tuple[int, int]],
    target_component: set[tuple[int, int]],
) -> None:
    start = min(component)
    queue: deque[tuple[int, int]] = deque([start])
    previous: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    target: tuple[int, int] | None = None
    while queue:
        cell = queue.popleft()
        if cell in target_component:
            target = cell
            break
        for neighbor in rook_neighbors(*cell):
            if neighbor not in previous:
                previous[neighbor] = cell
                queue.append(neighbor)
    if target is None:
        raise RuntimeError("unable to open a passable path between map components")
    current: tuple[int, int] | None = target
    while current is not None:
        water[current] = False
        current = previous[current]


def _distance_to_set(cell: tuple[int, int], cells: set[tuple[int, int]]) -> int:
    return min(abs(cell[0] - row) + abs(cell[1] - col) for row, col in cells)


def _rook_distances(
    passable: NDArray[np.bool], source_mask: NDArray[np.bool]
) -> NDArray[np.float64]:
    distances = np.full((ROWS, COLS), np.inf, dtype=np.float64)
    queue: deque[tuple[int, int]] = deque()
    for row, col in np.argwhere(source_mask & passable):
        coordinate = int(row), int(col)
        distances[coordinate] = 0.0
        queue.append(coordinate)
    while queue:
        row, col = queue.popleft()
        for neighbor in rook_neighbors(row, col):
            if passable[neighbor] and not np.isfinite(distances[neighbor]):
                distances[neighbor] = distances[row, col] + 1.0
                queue.append(neighbor)
    return distances


def _nearest_source_manhattan(non_source: NDArray[np.bool]) -> NDArray[np.float64]:
    source_coordinates = np.argwhere(_source_mask() != "")
    values = np.empty(int(non_source.sum()), dtype=np.float64)
    for index, (row, col) in enumerate(np.argwhere(non_source)):
        values[index] = np.min(np.abs(source_coordinates - np.asarray((row, col))).sum(axis=1))
    return values


__all__ = [
    "ARCHETYPES",
    "EXPECTED_COUNTS",
    "build_landscape",
    "describe_landscape",
    "map_checks",
]
