from __future__ import annotations

import numpy as np

from latent_landscapes.goal001.landscape import build_landscape
from latent_landscapes.goal001.spread import build_passable_edges
from latent_landscapes.goal003.spread import compute_stochastic_spread, sample_edge_transit_times


def test_frozen_graph_and_stochastic_invariants() -> None:
    landscape = build_landscape()
    assert len(build_passable_edges(landscape)) == 10_120
    truth = compute_stochastic_spread(landscape, np.random.default_rng(7))
    assert int(truth.reachable.sum()) == 5_225
    assert np.isfinite(truth.arrival[landscape.passable]).all()
    assert np.isinf(truth.arrival[~landscape.passable]).all()
    assert (truth.arrival[landscape.source_zone != ""] == 0.0).all()


def test_same_shocks_scale_exactly_with_rate() -> None:
    landscape = build_landscape()
    one = sample_edge_transit_times(landscape, np.random.default_rng(11), rho=1.0)
    two = sample_edge_transit_times(landscape, np.random.default_rng(11), rho=2.0)
    assert [edge[:2] for edge in one] == [edge[:2] for edge in two]
    assert np.allclose([edge[2] for edge in two], np.asarray([edge[2] for edge in one]) / 2.0)
