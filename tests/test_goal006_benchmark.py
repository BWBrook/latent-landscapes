from __future__ import annotations

from dataclasses import replace

from latent_landscapes.goal006 import benchmark


def tiny_config() -> benchmark.Goal006Config:
    return replace(benchmark.DEFAULT_CONFIG, replicates=4)


def test_seed_manifest_and_tiny_run() -> None:
    manifest = benchmark.spawn_seed_records(tiny_config())
    assert len(manifest) == 4
    assert tuple(s.replicate_index for s in manifest) == (0, 1, 2, 3)
    assert len({(s.entropy, s.spawn_key) for s in manifest}) == 4
    result = benchmark.run_goal006(tiny_config())
    assert len(result.replicate_summaries) == 20
    assert {r.eta for r in result.replicate_summaries} == set(benchmark.ETA_VALUES)
    assert all(result.invariants.values())


def test_decision_class_precedence() -> None:
    assert benchmark.classify_outcome({"ok": False}, {}, (), ()) == "implementation_blocked"
