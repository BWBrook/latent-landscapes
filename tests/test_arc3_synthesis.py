from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes.arc2c_design import BridgeConfig
from latent_landscapes.arc3_campaign import run_campaign, write_campaign_bundle
from latent_landscapes.arc3_design import build_sampling_pair
from latent_landscapes.arc3_synthesis import (
    MapBundle,
    evaluate_map,
    load_map_bundle,
    summarize_maps,
    validate_bundle,
    write_review_bundle,
)
from latent_landscapes.goal001.landscape import build_landscape


def _config() -> BridgeConfig:
    return BridgeConfig(
        bank_size=4,
        calibration_replicates=2,
        validation_replicates=2,
        calibration_rank=2,
        rhos=(0.5, 1.0, 2.0),
        effects=(1.0, 3.0, 5.0),
    )


@pytest.fixture(scope="module")
def bundle(tmp_path_factory: pytest.TempPathFactory) -> MapBundle:
    landscape = build_landscape()
    access, balanced = build_sampling_pair(landscape, 2026090801)
    result = run_campaign(
        landscape,
        access,
        balanced,
        _config(),
        scene_metadata={"archetype": "connected", "map_seed": 1},
        progress=None,
    )
    directory = tmp_path_factory.mktemp("arc3-map")
    write_campaign_bundle(result, directory)
    return load_map_bundle(directory)


def _paired_clone(bundle: MapBundle, *, map_seed: int, identical: bool = False) -> MapBundle:
    profiles = {name: values.copy() for name, values in bundle.profiles.items()}
    if identical:
        for _name, values in profiles.items():
            if _name in {
                "condition_ids",
                "design_ids",
                "truth_effects",
                "truth_rhos",
                "truth_roles",
            }:
                continue
            if values.ndim and values.shape[0] == 6:
                values[3:] = values[:3]
    summary = {
        **bundle.run_summary,
        "scene_metadata": {"archetype": "connected", "map_seed": map_seed},
    }
    return MapBundle(bundle.config, bundle.truths, profiles, summary, bundle.profile_sha256)


def test_fixed_map_synthesis_reports_zero_identical_design_contrast(bundle: MapBundle) -> None:
    result = summarize_maps([_paired_clone(bundle, map_seed=10, identical=True)], bootstrap_count=8)
    assert result.outcome == "non_scientific_pilot"
    assert all(row["equal_map_mean_change"] == 0.0 for row in result.archetype_summary)
    assert all(row["map_min"] == 0.0 and row["map_max"] == 0.0 for row in result.archetype_summary)


def test_archetype_summary_uses_equal_map_weights_and_paired_resampling(
    bundle: MapBundle,
) -> None:
    second = _paired_clone(bundle, map_seed=2)
    second = replace(
        second, config=replace(bundle.config, master_seed=bundle.config.master_seed + 1)
    )
    result = summarize_maps([bundle, second], bootstrap_count=8, bootstrap_seed=12)
    first_metric = result.archetype_summary[0]
    matching = [
        row
        for row in result.map_paired_metrics
        if row["effect"] == first_metric["effect"]
        and row["analysis"] == first_metric["analysis"]
        and row["metric"] == first_metric["metric"]
    ]
    np.testing.assert_allclose(
        first_metric["equal_map_mean_change"],
        np.mean([row["balanced_minus_access"] for row in matching]),
    )
    repeat = summarize_maps([bundle, second], bootstrap_count=8, bootstrap_seed=12)
    np.testing.assert_array_equal(
        result.bootstrap_samples["mean_log_width"], repeat.bootstrap_samples["mean_log_width"]
    )

    mismatched = replace(
        second, config=replace(bundle.config, bank_size=bundle.config.bank_size + 1)
    )
    with pytest.raises(ValueError, match="same grids and replicate design"):
        summarize_maps([bundle, mismatched], bootstrap_count=4)


def test_evaluate_map_reuses_selected_indices_and_recalibrates(bundle: MapBundle) -> None:
    zeros = np.zeros(bundle.config.calibration_replicates, dtype=np.int64)
    ones = np.ones(bundle.config.calibration_replicates, dtype=np.int64)
    evaluations = np.zeros(bundle.config.validation_replicates, dtype=np.int64)
    first = evaluate_map(bundle, zeros, evaluations)
    repeat = evaluate_map(bundle, zeros, evaluations)
    np.testing.assert_array_equal(first.effect_cutoffs, repeat.effect_cutoffs)
    changed = evaluate_map(bundle, ones, evaluations)
    assert changed.effect_cutoffs.shape == (6, 2)
    assert changed.rho["mean_absolute_log_rho_error"].shape == (6,)


def test_null_false_exclusion_counts_match_no_effect_support(bundle: MapBundle) -> None:
    result = summarize_maps([bundle], bootstrap_count=4)
    rows = [
        row
        for row in result.map_conditions
        if row["condition_id"] == "access_1" and row["analysis"] == "known_speed"
    ]
    assert len(rows) == 1
    row = rows[0]
    count = bundle.config.validation_replicates
    assert row["null_false_exclusion_count"] == count - row["coverage_count"]
    assert row["null_false_exclusion_count"] / count == row["no_effect_exclusion"]


def test_loader_rejects_hash_shape_and_duplicate_metadata(
    bundle: MapBundle, tmp_path: Path
) -> None:
    bad_profiles = {name: values.copy() for name, values in bundle.profiles.items()}
    bad_profiles["validation_effect_drops"] = bad_profiles["validation_effect_drops"][..., :-1]
    with pytest.raises(ValueError, match="invalid shape"):
        validate_bundle(replace(bundle, profiles=bad_profiles))

    directory = tmp_path / "saved"
    directory.mkdir()
    np.savez_compressed(directory / "profiles.npz", **bundle.profiles)
    summary = {**bundle.run_summary, "profile_bundle_sha256": "wrong"}
    (directory / "run_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        load_map_bundle(directory)

    with pytest.raises(ValueError, match="unique"):
        summarize_maps([bundle, _paired_clone(bundle, map_seed=1)], bootstrap_count=4)


def test_review_writer_emits_json_csv_and_scope_note(bundle: MapBundle, tmp_path: Path) -> None:
    result = summarize_maps([bundle], bootstrap_count=4)
    written = write_review_bundle(result, tmp_path)
    assert {path.name for path in written} == {
        "summary.json",
        "map_conditions.csv",
        "map_paired_metrics.csv",
        "archetype_summary.csv",
        "review.md",
    }
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["bootstrap"]["maps_resampled"] is False
    assert summary["source_maps"][0]["profile_sha256"] == bundle.profile_sha256
    assert "rho interval acceptance claim" in (tmp_path / "review.md").read_text()


def test_production_summary_requires_review_and_cannot_pool_pilots(bundle: MapBundle) -> None:
    production = replace(bundle, run_summary={**bundle.run_summary, "mode": "production"})
    result = summarize_maps([production], bootstrap_count=4)
    assert result.outcome == "production_pending_review"
    with pytest.raises(ValueError, match="pilot and production"):
        summarize_maps([production, _paired_clone(bundle, map_seed=2)], bootstrap_count=4)
