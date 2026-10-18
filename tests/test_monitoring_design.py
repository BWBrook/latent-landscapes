from __future__ import annotations

from dataclasses import replace
from itertools import combinations
from math import hypot

import numpy as np
import pytest

from latent_landscapes.goal001.design import build_access_network
from latent_landscapes.goal001.landscape import build_landscape
from latent_landscapes.monitoring_design import (
    BASELINE_SITE_COUNT,
    HOLDOUT_SITE_COUNT,
    MASTER_SITE_COUNT,
    MINIMUM_CENTRE_SEPARATION,
    SolverInfeasibleError,
    availability_masks,
    build_master_monitoring_design,
    find_eligible_centres,
    monitoring_checks,
)

SEEDS = dict(sampling_seed=2026101811, holdout_seed=2026101812, arm_seed=2026101813)


def test_two_cell_euclidean_frame_and_footprints() -> None:
    landscape = build_landscape()
    network = build_access_network(landscape.shape)
    eligible = find_eligible_centres(landscape, network)
    network_cells = np.argwhere(network)

    assert eligible
    assert all(
        np.linalg.norm(network_cells - np.asarray((candidate.row, candidate.col)), axis=1).min()
        <= 2.0 + 1e-12
        for candidate in eligible
    )
    assert all(
        landscape.passable[row, col] and landscape.source_reachable[row, col]
        for candidate in eligible
        for row, col in (
            (candidate.row, candidate.col),
            (candidate.row - 2, candidate.col),
            (candidate.row + 2, candidate.col),
            (candidate.row, candidate.col - 2),
            (candidate.row, candidate.col + 2),
        )
    )
    # The widened frame contains off-network centres, which the old exact-line
    # sampler could not represent.
    assert any(not network[candidate.row, candidate.col] for candidate in eligible)


def test_master_panel_is_nested_equal_count_and_replayable() -> None:
    landscape = build_landscape()
    first = build_master_monitoring_design(landscape, **SEEDS)
    second = build_master_monitoring_design(landscape, **SEEDS)

    assert first.baseline_site_ids == second.baseline_site_ids
    assert first.holdout_site_ids == second.holdout_site_ids
    assert first.c_site_ids == second.c_site_ids
    assert first.sampling.clusters == second.sampling.clusters
    assert first.sampling.sites == second.sampling.sites
    assert np.array_equal(first.sampling.network, second.sampling.network)
    assert len(first.sampling.sites) == MASTER_SITE_COUNT
    assert len(first.baseline_site_ids) == BASELINE_SITE_COUNT
    assert len(first.holdout_site_ids) == HOLDOUT_SITE_COUNT
    assert len(first.c_site_ids) == 260
    assert first.solver_receipt.status == "selected_verified"
    assert first.solver_receipt.selected_count == 60
    assert first.solver_receipt.objective_value is not None
    assert first.sampling.network.flags.writeable is False
    assert all(value for value in monitoring_checks(first, landscape).values())

    by_cluster = {cluster.cluster_id: cluster for cluster in first.sampling.clusters}
    assert all(
        hypot(left.center_row - right.center_row, left.center_col - right.center_col)
        >= MINIMUM_CENTRE_SEPARATION
        for left, right in combinations(by_cluster.values(), 2)
    )
    masks = availability_masks(first)
    assert tuple(sorted(masks)) == ("A", "B", "C")
    assert sum(masks["A"]) == BASELINE_SITE_COUNT
    assert sum(masks["B"]) == BASELINE_SITE_COUNT
    assert sum(masks["C"]) == 260
    assert masks["A"] == masks["B"]
    assert all(not a or c for a, c in zip(masks["A"], masks["C"], strict=True))


def test_infeasible_frame_is_reported_without_count_reduction() -> None:
    landscape = build_landscape()
    constrained = replace(
        landscape,
        passable=np.zeros_like(landscape.passable),
        source_reachable=np.zeros_like(landscape.source_reachable),
    )
    with pytest.raises(SolverInfeasibleError, match="eligible-centre frame is empty") as caught:
        build_master_monitoring_design(constrained, **SEEDS)
    assert caught.value.receipt is not None
    assert caught.value.receipt.status == "solver_infeasible"
