from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from collections import Counter, defaultdict
from itertools import combinations
from math import hypot
from typing import Any

import numpy as np


def load_module(name: str) -> Any:
    return importlib.import_module(f"latent_landscapes.goal001.{name}")


def test_access_network_is_fixed_before_landscape_exclusions() -> None:
    landscape_module = load_module("landscape")
    design_module = load_module("design")
    landscape = landscape_module.build_landscape()

    network = design_module.build_access_network(landscape.shape)

    assert design_module.ROAD_COLUMNS == (6, 20, 34, 48, 62, 76)
    assert design_module.TRANSECT_ROWS == (5, 17, 29, 41, 53, 65)
    for row in range(landscape.rows):
        for col in range(landscape.cols):
            assert bool(network[row, col]) is (
                col in design_module.ROAD_COLUMNS or row in design_module.TRANSECT_ROWS
            )
    assert bool((network & ~landscape.passable).any())


def test_eligible_centres_and_frozen_cluster_selection_meet_invariants() -> None:
    landscape_module = load_module("landscape")
    design_module = load_module("design")
    landscape = landscape_module.build_landscape()
    centre_rng, holdout_rng, _ = design_module.spawn_generators()

    design = design_module.build_design(landscape, centre_rng, holdout_rng)

    assert design_module.MASTER_SEED == 20260716
    assert "truth" not in inspect.signature(design_module.build_design).parameters
    assert design_module.SITE_OFFSETS == ((0, 0), (-2, 0), (2, 0), (0, -2), (0, 2))
    assert Counter(candidate.stratum_index for candidate in design.eligible_centres) == {
        0: 202,
        1: 122,
        2: 154,
        3: 157,
    }
    assert Counter(cluster.stratum_index for cluster in design.clusters) == {
        0: 8,
        1: 8,
        2: 8,
        3: 8,
    }
    assert Counter(cluster.split for cluster in design.clusters) == {
        "training": 24,
        "holdout": 8,
    }
    assert {cluster.cluster_id for cluster in design.clusters if cluster.split == "holdout"} == {
        "cluster_01",
        "cluster_05",
        "cluster_09",
        "cluster_10",
        "cluster_18",
        "cluster_22",
        "cluster_26",
        "cluster_30",
    }
    assert all(
        hypot(left.center_row - right.center_row, left.center_col - right.center_col) >= 8.0
        for left, right in combinations(design.clusters, 2)
    )
    assert len(design.sites) == 160
    assert all(landscape.passable[site.row, site.col] for site in design.sites)
    assert all(landscape.source_reachable[site.row, site.col] for site in design.sites)

    rows = [
        [
            cluster.cluster_id,
            cluster.center_row,
            cluster.center_col,
            cluster.stratum_index,
            cluster.euclidean_source_distance,
            cluster.split,
        ]
        for cluster in design.clusters
    ]
    payload = json.dumps(rows, separators=(",", ":")).encode()
    assert hashlib.sha256(payload).hexdigest() == (
        "050a963a54cfee0dfaba5ea5e9bf81b8da38d2fc988f8c9da432a9ed3dd4484e"
    )


def test_split_has_no_cluster_leakage() -> None:
    landscape_module = load_module("landscape")
    design_module = load_module("design")
    landscape = landscape_module.build_landscape()
    centre_rng, holdout_rng, _ = design_module.spawn_generators()

    design = design_module.build_design(landscape, centre_rng, holdout_rng)

    splits: dict[str, set[str]] = defaultdict(set)
    for site in design.sites:
        splits[site.cluster_id].add(site.split)
    assert all(len(values) == 1 for values in splits.values())
    assert len(splits) == 32


def test_observation_contract_and_deterministic_detection_stream() -> None:
    landscape_module = load_module("landscape")
    spread_module = load_module("spread")
    design_module = load_module("design")
    observations_module = load_module("observations")
    landscape = landscape_module.build_landscape()
    truth = spread_module.compute_spread(landscape)
    centre_rng, holdout_rng, detection_rng = design_module.spawn_generators()
    design = design_module.build_design(landscape, centre_rng, holdout_rng)

    records = observations_module.generate_observations(design.sites, truth, detection_rng)

    assert observations_module.SURVEY_TIMES == (10, 30, 50, 70, 90, 110)
    assert observations_module.REPLICATES == (1, 2)
    assert observations_module.DETECTION_PROBABILITY == 0.65
    assert len(records) == 1920
    assert sum(record.detected for record in records) == 563
    assert list(records) == sorted(
        records,
        key=lambda record: (
            record.cluster_id,
            record.site_offset_index,
            record.time,
            record.replicate,
        ),
    )
    assert all(
        not record.detected or truth.arrival[record.row, record.col] <= record.time
        for record in records
    )
    assert not {
        "true_arrival",
        "arrival",
        "occupied",
        "latent_occupancy",
        "source_zone",
    } & set(records[0].to_csv_row())

    rows = [
        [
            record.cluster_id,
            record.split,
            record.site_offset_index,
            record.row,
            record.col,
            record.time,
            record.replicate,
            record.detected,
        ]
        for record in records
    ]
    payload = json.dumps(rows, separators=(",", ":")).encode()
    assert hashlib.sha256(payload).hexdigest() == (
        "a540a0254e7ef379dbcbef21a255590816dd323e233efbcb8fa2f445d85c47a8"
    )

    centre_rng_2, holdout_rng_2, detection_rng_2 = design_module.spawn_generators()
    design_2 = design_module.build_design(landscape, centre_rng_2, holdout_rng_2)
    records_2 = observations_module.generate_observations(design_2.sites, truth, detection_rng_2)
    assert records == records_2
    assert isinstance(design.network, np.ndarray)
