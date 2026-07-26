from __future__ import annotations

import numpy as np

from latent_landscapes.goal003.benchmark import Goal003Config, build_ensemble, spawn_seed_records


def test_canonical_seed_manifest_and_representative_ranks() -> None:
    seeds = spawn_seed_records()
    assert len(seeds) == 100
    assert len({(seed.entropy, seed.spawn_key) for seed in seeds}) == 100
    assert [seed.replicate_index for seed in seeds] == list(range(100))
    result = build_ensemble()
    assert result.outcome == "time_scale_review_required"
    assert [row["rank_one_based"] for row in result.representatives] == [10, 25, 50, 75, 90]
    assert result.invariants and all(result.invariants.values())


def test_small_fixture_preserves_replayable_seed_order() -> None:
    result = build_ensemble(Goal003Config(master_seed=9, replicates=3))
    assert len(result.replicate_summaries) == 3
    assert np.std([summary.time_to_50 for summary in result.replicate_summaries]) > 0
