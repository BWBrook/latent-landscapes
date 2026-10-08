from __future__ import annotations

from dataclasses import replace
from itertools import combinations

import numpy as np
import pytest

from latent_landscapes.arc3_design import build_sampling_pair
from latent_landscapes.goal001.landscape import build_landscape


def test_sampling_pair_has_common_geographic_holdout_and_equal_stratified_effort() -> None:
    landscape = build_landscape()
    pair = build_sampling_pair(landscape, 2026090801)
    common = []
    for design in pair:
        train = [site for site in design.sites if site.split == "training"]
        test = [site for site in design.sites if site.split == "holdout"]
        assert len(train) == 120 and len(test) == 40
        assert len({(site.row, site.col) for site in design.sites}) == 160
        assert [sum(site.stratum_index == s for site in train) for s in range(4)] == [30] * 4
        assert [sum(site.stratum_index == s for site in test) for s in range(4)] == [10] * 4
        assert {site.cluster_id for site in train}.isdisjoint(site.cluster_id for site in test)
        assert all(
            (a.center_row - b.center_row) ** 2 + (a.center_col - b.center_col) ** 2 >= 64
            for a, b in combinations(design.clusters, 2)
        )
        common.append(sorted(test, key=lambda site: site.site_id))
    assert common[0] == common[1]
    assert all(
        pair[0].network[cluster.center_row, cluster.center_col]
        for cluster in pair[0].clusters
        if cluster.split == "training"
    )
    assert {(s.row, s.col) for s in pair[0].sites} != {(s.row, s.col) for s in pair[1].sites}
    replay = build_sampling_pair(landscape, 2026090801)
    assert all(a.sites == b.sites for a, b in zip(pair, replay, strict=True))


def test_infeasible_map_is_reported_without_seed_replacement() -> None:
    landscape = build_landscape()
    passable = landscape.passable.copy()
    passable[:, 20:] = False
    constrained = replace(landscape, passable=passable, source_reachable=passable)
    with pytest.raises(RuntimeError, match="infeasible"):
        build_sampling_pair(constrained, 2026090801)


def test_selection_uses_geometry_not_cosmetic_quality() -> None:
    landscape = build_landscape()
    changed = replace(landscape, quality=np.ones(landscape.shape))
    a = build_sampling_pair(landscape, 2026090801)
    b = build_sampling_pair(changed, 2026090801)
    assert all(x.sites == y.sites for x, y in zip(a, b, strict=True))
