from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from latent_landscapes.arc2c_design import EFFECT_GRID, RHO_GRID, BridgeConfig
from latent_landscapes.arc3_campaign import (
    BANK_FILENAME,
    DEFAULT_CONFIG,
    EXPECTED_FILES,
    _build_joint_integration,
    run_campaign,
    validate_production_freeze,
    write_campaign_bundle,
)
from latent_landscapes.arc3_design import MASTER_SEED, PRODUCTION_MAP_SEEDS, build_sampling_pair
from latent_landscapes.arc3_landscapes import ARCHETYPES
from latent_landscapes.goal001.design import SamplingDesign
from latent_landscapes.goal001.landscape import Landscape, build_landscape


def _small_config() -> BridgeConfig:
    return BridgeConfig(
        bank_size=4,
        calibration_replicates=2,
        validation_replicates=2,
        calibration_rank=2,
        rhos=(0.5, 1.0, 2.0),
        effects=(1.0, 3.0, 5.0),
    )


def _designs() -> tuple[Landscape, tuple[SamplingDesign, SamplingDesign]]:
    landscape = build_landscape()
    return landscape, build_sampling_pair(landscape, 2026090801)


def _production_inputs() -> tuple[BridgeConfig, dict[str, Any], dict[str, Any]]:
    map_seed = PRODUCTION_MAP_SEEDS[0]
    archetype = ARCHETYPES[0]
    sampling_seed = int(np.random.SeedSequence([MASTER_SEED, map_seed, 1]).generate_state(1)[0])
    campaign_seed = int(
        np.random.SeedSequence(
            [MASTER_SEED, map_seed, ARCHETYPES.index(archetype), 2]
        ).generate_state(1)[0]
    )
    config = BridgeConfig(
        master_seed=campaign_seed,
        bank_size=16384,
        calibration_replicates=250,
        validation_replicates=250,
        calibration_rank=239,
        rhos=RHO_GRID,
        effects=EFFECT_GRID,
    )
    scene = {
        "archetype": archetype,
        "map_seed": map_seed,
        "sampling_seed": sampling_seed,
    }
    freeze = {
        "schema_version": 1,
        "goal": "046",
        "selected_bank_size": 16384,
        "reference_bank_size": 32768,
        "master_seed": MASTER_SEED,
        "archetypes": list(ARCHETYPES),
        "production_map_seeds": list(PRODUCTION_MAP_SEEDS),
        "rhos": list(RHO_GRID),
        "effects": list(EFFECT_GRID),
        "calibration_replicates": 250,
        "validation_replicates": 250,
        "calibration_rank": 239,
        "qualification_receipt": {"sha256": "a" * 64},
        "source_snapshot_sha256": "b" * 64,
    }
    return config, scene, freeze


def test_campaign_pairs_common_holdout_and_overlap_observations() -> None:
    landscape, (access, balanced) = _designs()
    result = run_campaign(landscape, access, balanced, _small_config(), workers=1)

    assert result.outcome == "non_scientific_pilot"
    assert all(result.invariants.values()), result.invariants
    assert result.profiles["condition_ids"].tolist() == [
        "access_1",
        "access_3",
        "access_5",
        "balanced_1",
        "balanced_3",
        "balanced_5",
    ]
    assert result.profiles["design_ids"].tolist() == [
        "access",
        "access",
        "access",
        "balanced",
        "balanced",
        "balanced",
    ]
    assert result.base_arrivals.shape == (4, len(result.site_ids))
    assert len(result.site_ids) >= 160


def test_parallel_rho_integration_is_bitwise_identical_to_serial() -> None:
    bank = np.asarray(
        [
            [0.0, 4.0, 12.0, 70.0],
            [2.0, 8.0, 18.0, 66.0],
            [5.0, 11.0, 24.0, 62.0],
            [9.0, 15.0, 30.0, 58.0],
        ],
        dtype=np.float64,
    )
    site_ids = ("site_a", "site_b", "site_c", "unused_union_site")
    serial = _build_joint_integration(
        bank,
        site_ids,
        (0.5, 1.0, 2.0),
        (1.0, 3.0, 5.0),
        background_hazard=0.002,
        workers=1,
    )
    parallel = _build_joint_integration(
        bank,
        site_ids,
        (0.5, 1.0, 2.0),
        (1.0, 3.0, 5.0),
        background_hazard=0.002,
        workers=3,
    )
    np.testing.assert_array_equal(serial.category_mass, parallel.category_mass)
    assert len(serial.survival_moments) == len(parallel.survival_moments)
    for serial_moment, parallel_moment in zip(
        serial.survival_moments, parallel.survival_moments, strict=True
    ):
        np.testing.assert_array_equal(serial_moment, parallel_moment)
    assert serial.bank_checksum == parallel.bank_checksum


def test_parallel_campaign_is_bitwise_identical_to_serial() -> None:
    landscape, (access, balanced) = _designs()
    serial = run_campaign(landscape, access, balanced, _small_config(), workers=1)
    parallel = run_campaign(landscape, access, balanced, _small_config(), workers=2)
    assert serial.site_ids == parallel.site_ids
    assert len(serial.site_ids) > len(access.sites)
    np.testing.assert_array_equal(serial.base_arrivals, parallel.base_arrivals)
    assert serial.invariants == parallel.invariants
    assert set(serial.profiles) == set(parallel.profiles)
    for name in serial.profiles:
        np.testing.assert_array_equal(serial.profiles[name], parallel.profiles[name])


def test_identical_design_has_zero_profile_contrast() -> None:
    landscape, (access, _) = _designs()
    result = run_campaign(landscape, access, access, _small_config(), workers=2)

    for name in (
        "calibration_effect_lr",
        "calibration_spread_lr",
        "validation_effect_drops",
        "validation_spread_drops",
        "validation_effect_mle",
        "validation_spread_mle",
        "conditional_advantage",
        "joint_advantage",
        "calibration_train_joint",
        "validation_train_joint",
        "event_diagnostics",
    ):
        first, second = result.profiles[name][:3], result.profiles[name][3:]
        np.testing.assert_array_equal(first, second)


def test_writer_roundtrips_all_profile_arrays_without_pickle(tmp_path: Path) -> None:
    landscape, (access, balanced) = _designs()
    result = run_campaign(landscape, access, balanced, _small_config(), source_commit="test")
    written = write_campaign_bundle(result, tmp_path)

    assert tuple(path.name for path in written) == (*EXPECTED_FILES, BANK_FILENAME)
    with np.load(tmp_path / "profiles.npz", allow_pickle=False) as saved:
        assert "allow_pickle" not in saved.files
        assert set(saved.files) == set(result.profiles)
        for name in saved.files:
            np.testing.assert_array_equal(saved[name], result.profiles[name])
    np.testing.assert_array_equal(
        np.load(tmp_path / BANK_FILENAME, allow_pickle=False), result.base_arrivals
    )
    summary = json.loads((tmp_path / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["workflow"] == "arc3-landscape-sampling-campaign"
    assert summary["designs"] == ["access", "balanced"]
    assert summary["truths"][0]["condition_id"] == "access_1"
    assert summary["source_commit"] == "test"
    assert set(summary["runtimes_seconds"]) == {
        "total",
        "bank",
        "integration",
        "calibration",
        "validation",
    }


def test_default_is_bounded_and_production_mode_is_explicitly_rejected() -> None:
    assert not DEFAULT_CONFIG.is_production
    landscape, (access, balanced) = _designs()
    pilot = run_campaign(landscape, access, balanced, _small_config())
    assert replace(pilot, mode="production").outcome == "production_pending_numerical_review"
    with pytest.raises(ValueError, match="production mode"):
        run_campaign(landscape, access, balanced, _small_config(), mode="production")


def test_valid_production_freeze_admits_exact_config_without_running_histories() -> None:
    config, scene, freeze = _production_inputs()
    validated, digest = validate_production_freeze(config, scene, freeze)

    assert validated == freeze
    assert len(digest) == 64


def test_production_freeze_rejects_wrong_map_branch_and_settings() -> None:
    config, scene, freeze = _production_inputs()
    wrong_scene = dict(scene, map_seed=2026090801)
    with pytest.raises(ValueError, match="reserved Arc 3"):
        validate_production_freeze(config, wrong_scene, freeze)
    wrong_freeze = dict(freeze, selected_bank_size=8192)
    with pytest.raises(ValueError, match="selected bank size"):
        validate_production_freeze(config, scene, wrong_freeze)


def test_mismatched_holdout_and_supplied_bank_are_rejected() -> None:
    landscape, (access, balanced) = _designs()
    altered_site = next(site for site in balanced.sites if site.split == "holdout")
    altered = replace(
        balanced,
        sites=tuple(
            replace(site, split="training") if site is altered_site else site
            for site in balanced.sites
        ),
    )
    with pytest.raises(ValueError, match="120 training and 40 holdout"):
        run_campaign(landscape, access, altered, _small_config())

    result = run_campaign(landscape, access, balanced, _small_config())
    with pytest.raises(ValueError, match="supplied arrival bank"):
        run_campaign(
            landscape,
            access,
            balanced,
            _small_config(),
            supplied_bank=result.base_arrivals,
            supplied_bank_manifest={"bank_seeds": []},
        )
