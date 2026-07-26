"""Accepted deterministic synth-medium landscape, rebuilt in memory.

The geometry is adapted from SpatExt at the provenance identifiers below. This
module deliberately has no import-time or runtime dependency on that repository.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import pairwise
from math import exp, hypot, sin

import numpy as np
from numpy.typing import NDArray

LEGACY_COMMIT = "53462d0365babf2c8070714a930f69b4071af276"
LEGACY_LANDSCAPE_PATH = "src/spatext/synth/medium/landscape.py"
LEGACY_LANDSCAPE_BLOB_SHA1 = "f2f5fc24e64274e443f8eec8c314e212e2a6889f"

ROWS = 72
COLS = 84


@dataclass(frozen=True, slots=True)
class Patch:
    patch_id: str
    center_row: float
    center_col: float
    row_radius: float
    col_radius: float


@dataclass(frozen=True, slots=True)
class Corridor:
    corridor_id: str
    waypoints: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class SourceZone:
    source_zone_id: str
    row_start: int
    row_end: int
    col_start: int = 0
    col_end: int = 2


@dataclass(frozen=True, slots=True)
class Landscape:
    passable: NDArray[np.bool]
    source_reachable: NDArray[np.bool]
    habitat_class: NDArray[np.str_]
    quality: NDArray[np.float64]
    patch_id: NDArray[np.str_]
    corridor_id: NDArray[np.str_]
    source_zone: NDArray[np.str_]
    water_neighbor_count: NDArray[np.int16]

    @property
    def shape(self) -> tuple[int, int]:
        return self.passable.shape

    @property
    def rows(self) -> int:
        return self.shape[0]

    @property
    def cols(self) -> int:
        return self.shape[1]

    @property
    def cell_count(self) -> int:
        return self.rows * self.cols


def build_landscape() -> Landscape:
    water = _build_water_mask()
    patches = _build_patch_ids(water)
    medium = _build_medium_mask(water, patches)
    sources = _build_source_zones(water)
    corridors = _build_corridors(water, patches, sources)

    habitat = np.full((ROWS, COLS), "low_quality_matrix", dtype="U24")
    habitat[medium] = "medium_quality"
    habitat[patches != ""] = "high_quality_patch"
    habitat[corridors != ""] = "corridor"
    habitat[sources != ""] = "source_zone"
    habitat[water] = "water"

    quality = np.zeros((ROWS, COLS), dtype=np.float64)
    water_neighbors = np.zeros((ROWS, COLS), dtype=np.int16)
    for row in range(ROWS):
        for col in range(COLS):
            quality[row, col] = _quality(row, col, str(habitat[row, col]), patches[row, col])
            water_neighbors[row, col] = sum(water[r, c] for r, c in rook_neighbors(row, col))

    return Landscape(
        passable=~water,
        source_reachable=_source_reachability(~water, sources),
        habitat_class=habitat,
        quality=quality,
        patch_id=np.where(habitat == "high_quality_patch", patches, ""),
        corridor_id=np.where(habitat == "corridor", corridors, ""),
        source_zone=sources,
        water_neighbor_count=water_neighbors,
    )


def _source_reachability(
    passable: NDArray[np.bool], source_zones: NDArray[np.str_]
) -> NDArray[np.bool]:
    reachable = np.zeros((ROWS, COLS), dtype=np.bool)
    queue: deque[tuple[int, int]] = deque()
    for row, col in np.argwhere(source_zones != ""):
        coordinate = int(row), int(col)
        reachable[coordinate] = True
        queue.append(coordinate)
    while queue:
        row, col = queue.popleft()
        for target_row, target_col in rook_neighbors(row, col):
            if passable[target_row, target_col] and not reachable[target_row, target_col]:
                reachable[target_row, target_col] = True
                queue.append((target_row, target_col))
    return reachable


def patch_definitions() -> tuple[Patch, ...]:
    return (
        Patch("patch_northwest", 0.18, 0.18, 0.070, 0.085),
        Patch("patch_north_central", 0.23, 0.46, 0.075, 0.090),
        Patch("patch_mid_east", 0.45, 0.72, 0.090, 0.085),
        Patch("patch_southwest", 0.75, 0.18, 0.085, 0.095),
        Patch("patch_south_central", 0.67, 0.51, 0.085, 0.100),
        Patch("patch_southeast", 0.80, 0.77, 0.080, 0.100),
    )


def source_zone_definitions() -> tuple[SourceZone, ...]:
    return (
        SourceZone("source_west_north", 6, 13),
        SourceZone("source_west_mid", 31, 39),
        SourceZone("source_west_south", 56, 65),
    )


def corridor_definitions() -> tuple[Corridor, ...]:
    return (
        Corridor(
            "corridor_north_source_to_central",
            ((10, 3), (12, 12), (16, 26), (17, 37)),
        ),
        Corridor(
            "corridor_mid_source_to_south_central",
            ((35, 3), (42, 15), (47, 29), (49, 41)),
        ),
        Corridor(
            "corridor_south_source_to_southwest",
            ((61, 3), (58, 10), (54, 16)),
        ),
        Corridor(
            "corridor_central_to_mid_east",
            ((49, 45), (42, 53), (34, 61)),
        ),
        Corridor(
            "corridor_south_central_to_southeast",
            ((54, 49), (58, 59), (62, 70)),
        ),
    )


def rook_neighbors(row: int, col: int) -> tuple[tuple[int, int], ...]:
    candidates = ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
    return tuple((r, c) for r, c in candidates if 0 <= r < ROWS and 0 <= c < COLS)


def _build_water_mask() -> NDArray[np.bool]:
    water = np.zeros((ROWS, COLS), dtype=np.bool)
    lakes = (
        (0.18, 0.30, 0.095, 0.135),
        (0.49, 0.53, 0.095, 0.090),
        (0.78, 0.30, 0.085, 0.130),
        (0.25, 0.74, 0.070, 0.095),
    )
    for row in range(ROWS):
        row_fraction = _normalized(row, ROWS)
        channel_col = round((0.59 + 0.035 * sin(row / 5.0)) * (COLS - 1))
        channel_band = 12 <= row <= ROWS - 12 and not (28 <= row <= 34 or 50 <= row <= 55)
        for col in range(COLS):
            col_fraction = _normalized(col, COLS)
            in_lake = any(
                _ellipse_distance(
                    row_fraction,
                    col_fraction,
                    center_row,
                    center_col,
                    row_radius,
                    col_radius,
                )
                <= 1.0
                for center_row, center_col, row_radius, col_radius in lakes
            )
            water[row, col] = in_lake or (channel_band and abs(col - channel_col) <= 1)
    return water


def _build_patch_ids(water: NDArray[np.bool]) -> NDArray[np.str_]:
    result = np.full((ROWS, COLS), "", dtype="U28")
    for patch in patch_definitions():
        for row in range(ROWS):
            row_fraction = _normalized(row, ROWS)
            for col in range(COLS):
                if water[row, col] or result[row, col]:
                    continue
                if (
                    _ellipse_distance(
                        row_fraction,
                        _normalized(col, COLS),
                        patch.center_row,
                        patch.center_col,
                        patch.row_radius,
                        patch.col_radius,
                    )
                    <= 1.0
                ):
                    result[row, col] = patch.patch_id
    return result


def _build_medium_mask(water: NDArray[np.bool], patch_ids: NDArray[np.str_]) -> NDArray[np.bool]:
    result = np.zeros((ROWS, COLS), dtype=np.bool)
    for patch in patch_definitions():
        for row in range(ROWS):
            row_fraction = _normalized(row, ROWS)
            for col in range(COLS):
                if water[row, col] or patch_ids[row, col]:
                    continue
                if (
                    _ellipse_distance(
                        row_fraction,
                        _normalized(col, COLS),
                        patch.center_row,
                        patch.center_col,
                        patch.row_radius,
                        patch.col_radius,
                    )
                    <= 1.55
                ):
                    result[row, col] = True
    return result


def _build_source_zones(water: NDArray[np.bool]) -> NDArray[np.str_]:
    result = np.full((ROWS, COLS), "", dtype="U24")
    for source in source_zone_definitions():
        for row in range(source.row_start, source.row_end + 1):
            for col in range(source.col_start, source.col_end + 1):
                if not water[row, col]:
                    result[row, col] = source.source_zone_id
    return result


def _build_corridors(
    water: NDArray[np.bool],
    patch_ids: NDArray[np.str_],
    source_zones: NDArray[np.str_],
) -> NDArray[np.str_]:
    result = np.full((ROWS, COLS), "", dtype="U48")
    for corridor in corridor_definitions():
        for row, col in _cells_along_polyline(corridor.waypoints, thickness=1):
            if water[row, col] or patch_ids[row, col] or source_zones[row, col]:
                continue
            result[row, col] = corridor.corridor_id
    return result


def _cells_along_polyline(
    waypoints: tuple[tuple[int, int], ...], *, thickness: int
) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for start, end in pairwise(waypoints):
        for row, col in _cells_along_line(start, end):
            for delta_row in range(-thickness, thickness + 1):
                for delta_col in range(-thickness, thickness + 1):
                    target = row + delta_row, col + delta_col
                    if (
                        0 <= target[0] < ROWS
                        and 0 <= target[1] < COLS
                        and abs(delta_row) + abs(delta_col) <= thickness
                    ):
                        cells.add(target)
    return cells


def _cells_along_line(start: tuple[int, int], end: tuple[int, int]) -> tuple[tuple[int, int], ...]:
    steps = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
    if steps == 0:
        return (start,)
    cells = []
    for step in range(steps + 1):
        fraction = step / steps
        cells.append(
            (
                round(start[0] + (end[0] - start[0]) * fraction),
                round(start[1] + (end[1] - start[1]) * fraction),
            )
        )
    return tuple(dict.fromkeys(cells))


def _quality(row: int, col: int, habitat_class: str, patch_id: str) -> float:
    row_fraction = _normalized(row, ROWS)
    col_fraction = _normalized(col, COLS)
    broad_gradient = 0.03 * (1.0 - col_fraction) + 0.02 * sin(row_fraction * 10.0)
    if habitat_class == "water":
        return 0.0
    if habitat_class == "source_zone":
        return _round(0.88 + 0.04 * (1.0 - abs(row_fraction - 0.5)))
    if habitat_class == "corridor":
        return _round(0.68 + 0.03 * sin((row + col) / 9.0))
    if habitat_class == "high_quality_patch":
        patch = next(value for value in patch_definitions() if value.patch_id == patch_id)
        distance = _ellipse_distance(
            row_fraction,
            col_fraction,
            patch.center_row,
            patch.center_col,
            patch.row_radius,
            patch.col_radius,
        )
        return _round(0.80 + 0.13 * max(0.0, 1.0 - distance))
    if habitat_class == "medium_quality":
        return _round(0.52 + 0.06 * _gaussian_bump(row_fraction, col_fraction, 0.58, 0.55, 0.35))
    low_quality = (
        0.22 + broad_gradient + 0.035 * _gaussian_bump(row_fraction, col_fraction, 0.42, 0.68, 0.22)
    )
    return _round(min(max(low_quality, 0.15), 0.39))


def _normalized(index: int, count: int) -> float:
    return index / max(count - 1, 1)


def _ellipse_distance(
    row_fraction: float,
    col_fraction: float,
    center_row: float,
    center_col: float,
    row_radius: float,
    col_radius: float,
) -> float:
    return hypot(
        (row_fraction - center_row) / row_radius,
        (col_fraction - center_col) / col_radius,
    )


def _gaussian_bump(
    row_fraction: float,
    col_fraction: float,
    center_row: float,
    center_col: float,
    sigma: float,
) -> float:
    squared_distance = (row_fraction - center_row) ** 2 + (col_fraction - center_col) ** 2
    return exp(-squared_distance / (2.0 * sigma**2))


def _round(value: float) -> float:
    return round(float(value), 12)
