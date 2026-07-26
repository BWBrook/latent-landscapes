from __future__ import annotations

import hashlib
import importlib
import json
from collections import Counter
from typing import Any

import numpy as np
import pytest


def load_module(name: str) -> Any:
    return importlib.import_module(f"latent_landscapes.goal001.{name}")


def digest_rows(rows: list[list[object]]) -> str:
    payload = json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def test_landscape_reconciles_accepted_legacy_truth() -> None:
    landscape_module = load_module("landscape")

    landscape = landscape_module.build_landscape()

    assert landscape_module.LEGACY_COMMIT == "53462d0365babf2c8070714a930f69b4071af276"
    assert landscape_module.LEGACY_LANDSCAPE_BLOB_SHA1 == "f2f5fc24e64274e443f8eec8c314e212e2a6889f"
    assert landscape.shape == (72, 84)
    assert landscape.cell_count == 6048
    assert int(landscape.passable.sum()) == 5225
    assert int((~landscape.passable).sum()) == 823
    assert np.array_equal(landscape.source_reachable, landscape.passable)
    assert Counter(landscape.habitat_class.ravel()) == {
        "corridor": 178,
        "high_quality_patch": 682,
        "low_quality_matrix": 3449,
        "medium_quality": 835,
        "source_zone": 81,
        "water": 823,
    }
    assert Counter(value for value in landscape.source_zone.ravel() if value) == {
        "source_west_mid": 27,
        "source_west_north": 24,
        "source_west_south": 30,
    }

    rows = [
        [
            row * landscape.cols + col,
            row,
            col,
            "passable" if landscape.passable[row, col] else "water",
            str(landscape.habitat_class[row, col]),
            format(float(landscape.quality[row, col]), ".12g"),
            str(landscape.patch_id[row, col]),
            str(landscape.corridor_id[row, col]),
            str(landscape.source_zone[row, col]),
            int(landscape.water_neighbor_count[row, col]),
        ]
        for row in range(landscape.rows)
        for col in range(landscape.cols)
    ]
    assert digest_rows(rows) == "422f007dce3e1f4e8e7269a4bdc70ea2604e4b39658c97161b64e4a7a10b508f"


def test_spread_reconciles_accepted_legacy_truth() -> None:
    landscape_module = load_module("landscape")
    spread_module = load_module("spread")
    landscape = landscape_module.build_landscape()

    truth = spread_module.compute_spread(landscape)

    assert spread_module.LEGACY_SPREAD_BLOB_SHA1 == "cb15f2178ff9e2f359f06fdac34a9b551e163cd5"
    assert truth.rate == 1.0
    assert int(truth.reachable.sum()) == 5225
    assert float(truth.arrival[truth.reachable].min()) == 0.0
    assert float(truth.arrival[truth.reachable].max()) == pytest.approx(205.91031817267887)
    assert Counter(truth.source_zone[truth.reachable]) == {
        "source_west_mid": 3144,
        "source_west_north": 1456,
        "source_west_south": 625,
    }

    rows = [
        [
            row * landscape.cols + col,
            format(float(truth.arrival[row, col]), ".12g"),
            str(truth.source_zone[row, col]),
        ]
        for row in range(landscape.rows)
        for col in range(landscape.cols)
        if landscape.passable[row, col]
    ]
    assert digest_rows(rows) == "041f9c71682bc455a27114512bad1611e754c58596e7259d2b141bf0e26013de"


def test_edge_cost_uses_approved_baseline_equation() -> None:
    spread_module = load_module("spread")

    cost = spread_module.edge_cost(
        source_conductance=0.33,
        target_conductance=0.64,
        source_water_neighbors=2,
        target_water_neighbors=1,
    )

    assert cost == pytest.approx(0.88 / ((0.33 + 0.64) / 2.0) + 0.46 * 3 / 4)


def test_equal_cost_dijkstra_tie_uses_lexicographically_smaller_source() -> None:
    spread_module = load_module("spread")

    distances, labels = spread_module.multi_source_dijkstra(
        node_count=3,
        weighted_edges=((0, 1, 1.0), (1, 2, 1.0)),
        source_labels={0: "source_z", 2: "source_a"},
    )

    assert distances == pytest.approx((0.0, 1.0, 0.0))
    assert labels == ("source_z", "source_a", "source_a")
