from __future__ import annotations

import numpy as np
import pytest

from latent_landscapes.goal001.landscape import build_landscape
from latent_landscapes.goal001.spread import passable_edges
from latent_landscapes.goal006.spread import (
    ETA_VALUES,
    compute_contrast_spread,
    compute_paired_spreads,
    geometric_mean_cost,
    transform_edge_costs,
)


def test_transform_grid_and_exact_eta_one() -> None:
    landscape = build_landscape()
    edges = passable_edges(landscape)
    assert ETA_VALUES == (0.0, 0.5, 1.0, 1.5, 2.0)
    assert transform_edge_costs(edges, 1.0) == edges
    for eta in ETA_VALUES:
        transformed = transform_edge_costs(edges, eta)
        assert len(transformed) == len(edges)
        assert np.isfinite([e[2] for e in transformed]).all()
        assert np.asarray([e[2] for e in transformed]).min() > 0
        assert geometric_mean_cost(transformed) == pytest.approx(geometric_mean_cost(edges))


def test_paired_spreads_reuse_shocks_and_replay() -> None:
    landscape = build_landscape()
    first_shocks, first = compute_paired_spreads(landscape, rng=np.random.default_rng(42))
    second_shocks, second = compute_paired_spreads(landscape, edge_shocks=first_shocks)
    assert np.array_equal(first_shocks, second_shocks)
    assert all(np.array_equal(a.edge_shocks, first_shocks) for a in first)
    assert all(np.array_equal(a.arrival, b.arrival) for a, b in zip(first, second, strict=True))
    assert np.isinf(first[0].arrival[~landscape.passable]).all()
    assert (first[0].arrival[landscape.passable] >= 0).all()


def test_rho_scaling_and_invalid_inputs() -> None:
    landscape = build_landscape()
    shocks, one = compute_paired_spreads(landscape, rng=np.random.default_rng(1))
    two = compute_contrast_spread(landscape, 1.0, edge_shocks=shocks, rho=2.0)
    assert np.array_equal(two.arrival, one[2].arrival / 2.0)
    with pytest.raises(ValueError):
        transform_edge_costs(passable_edges(landscape), -1.0)
    with pytest.raises(ValueError):
        compute_paired_spreads(landscape)
