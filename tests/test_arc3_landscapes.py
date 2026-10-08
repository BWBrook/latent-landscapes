from __future__ import annotations

import json
from collections import Counter
from typing import cast

import numpy as np

from latent_landscapes.arc3_landscapes import (
    ARCHETYPES,
    EXPECTED_COUNTS,
    _corridor_skeleton,
    _source_mask,
    build_landscape,
    describe_landscape,
    map_checks,
)
from latent_landscapes.goal001.landscape import COLS, ROWS, source_zone_definitions


def test_all_archetypes_have_the_fixed_inventory_and_sources() -> None:
    expected_sources = np.full((ROWS, COLS), "", dtype="U24")
    for source in source_zone_definitions():
        expected_sources[
            source.row_start : source.row_end + 1,
            source.col_start : source.col_end + 1,
        ] = source.source_zone_id

    for archetype in ARCHETYPES:
        landscape = build_landscape(archetype, 17)
        assert Counter(str(value) for value in landscape.habitat_class.ravel()) == EXPECTED_COUNTS
        assert np.array_equal(landscape.source_zone, expected_sources)
        assert np.array_equal(landscape.source_reachable, landscape.passable)
        assert int(landscape.source_zone.astype(bool).sum()) == EXPECTED_COUNTS["source_zone"]
        assert map_checks(landscape)["single_passable_component"]


def test_seed_reproducibility_and_archetype_geometry_difference() -> None:
    first = build_landscape("corridor", 23)
    second = build_landscape("corridor", 23)
    different = build_landscape("corridor", 24)

    for field in (
        "passable",
        "habitat_class",
        "quality",
        "patch_id",
        "corridor_id",
        "source_zone",
        "water_neighbor_count",
    ):
        assert np.array_equal(getattr(first, field), getattr(second, field))
    assert not np.array_equal(first.passable, different.passable)
    assert not np.array_equal(
        build_landscape("connected", 23).habitat_class,
        build_landscape("corridor", 23).habitat_class,
    )
    assert np.array_equal(
        build_landscape("connected", 23).passable,
        build_landscape("corridor", 23).passable,
    )
    assert not np.array_equal(
        build_landscape("connected", 23).passable,
        build_landscape("barrier", 23).passable,
    )


def test_descriptors_are_json_compatible_and_finite() -> None:
    for archetype in ARCHETYPES:
        descriptor = describe_landscape(build_landscape(archetype, 1))
        json.dumps(descriptor, allow_nan=False)
        assert descriptor["component_count"] == 1
        assert descriptor["source_reachable_fraction"] == 1.0
        assert descriptor["counts"] == EXPECTED_COUNTS


def test_pilot_geometry_has_expected_archetype_directions() -> None:
    connected = describe_landscape(build_landscape("connected", 1))
    corridor = describe_landscape(build_landscape("corridor", 1))
    barrier = describe_landscape(build_landscape("barrier", 1))

    assert cast(float, corridor["corridor_ablation_ratio_median"]) > cast(
        float, connected["corridor_ablation_ratio_median"]
    )
    assert cast(float, barrier["geometric_detour_median"]) > cast(
        float, connected["geometric_detour_median"]
    )
    assert cast(float, barrier["least_cost_arrival_q90"]) > cast(
        float, connected["least_cost_arrival_q90"]
    )


def test_barrier_filler_preserves_declared_six_cell_gaps() -> None:
    for seed in (2026090801, 2026090811, 2026090812, 2026090813):
        rng = np.random.default_rng(seed)
        _corridor_skeleton(rng, _source_mask())
        centres = tuple(int(base + rng.integers(-1, 2)) for base in (26, 46, 66))
        gaps = tuple(int(value) for value in rng.integers((9, 33, 57), (16, 40, 64)))
        landscape = build_landscape("barrier", seed)
        assert all(
            landscape.passable[gap - 3 : gap + 3, centre - 2 : centre + 2].all()
            for centre, gap in zip(centres, gaps, strict=True)
        )
