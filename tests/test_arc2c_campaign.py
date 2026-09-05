from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes.arc2c_campaign import (
    EVENT_DIAGNOSTICS,
    EXPECTED_FILES,
    TIMING_BANK_FILENAME,
    profile_dataset,
    run_campaign,
    spawn_seed_manifest,
    write_campaign_bundle,
)
from latent_landscapes.arc2c_design import LANES, TRUTHS, smoke_config


def test_seed_manifest_reuses_independent_arc2b_root_schedule() -> None:
    config = smoke_config()
    manifest = spawn_seed_manifest(config)
    expected = arc2b.spawn_seed_manifest(
        arc2b.CampaignConfig(
            master_seed=config.master_seed,
            bank_size=config.bank_size,
            calibration_replicates=config.calibration_replicates,
            validation_replicates=config.validation_replicates,
            calibration_rank_one_based=config.calibration_rank,
        )
    )
    assert manifest == expected
    seeds = [
        *manifest.bank_seeds,
        *(
            seed
            for row in (*manifest.calibration, *manifest.validation)
            for seed in (
                row.process_seed,
                row.predator_detection_seed,
                row.prey_seed,
                row.prey_detection_seed,
            )
        ),
    ]
    assert len(set(seeds)) == len(seeds)
    assert config.master_seed != arc2b.MASTER_SEED


def test_profiles_use_training_only_and_matched_conditional_null() -> None:
    rhos = np.asarray((0.5, 1.0, 2.0))
    effects = np.asarray((1.0, 3.0, 5.0))
    train = np.asarray(((-14.0, -9.0, -10.0), (-13.0, -8.0, -6.0), (-15.0, -4.0, -7.0)))
    predator = np.asarray((-7.0, -8.0, -5.0))
    heldout = np.asarray(((-17.0, -13.0, -11.0), (-18.0, -10.0, -12.0), (-15.0, -8.0, -6.0)))
    profile = profile_dataset(train, heldout, predator, rhos=rhos, effects=effects, truth=TRUTHS[1])
    np.testing.assert_allclose(profile.effect_drops, ((14.0, 4.0, 0.0), (18.0, 0.0, 4.0)))
    np.testing.assert_allclose(profile.spread_drops, (10.0, 4.0, 0.0))
    np.testing.assert_allclose(profile.effect_truth_lr, (4.0, 0.0))
    assert profile.spread_truth_lr == 4.0
    np.testing.assert_array_equal(profile.effect_mle, (5.0, 3.0))
    assert profile.spread_mle == 2.0
    assert profile.conditional_null_rho_independent
    np.testing.assert_allclose(profile.conditional_advantage, (6.0 / 40, 7.0 / 40))
    np.testing.assert_allclose(profile.joint_advantage, (6.0 / 40, 10.0 / 40))

    rescored = profile_dataset(
        train,
        heldout + np.asarray((0.0, 1000.0, 2000.0))[None, :],
        predator,
        rhos=rhos,
        effects=effects,
        truth=TRUTHS[1],
    )
    np.testing.assert_array_equal(rescored.effect_mle, profile.effect_mle)
    np.testing.assert_array_equal(rescored.effect_drops, profile.effect_drops)
    np.testing.assert_array_equal(rescored.spread_drops, profile.spread_drops)
    assert rescored.spread_mle == profile.spread_mle
    assert not np.array_equal(rescored.conditional_advantage, profile.conditional_advantage)


def test_smoke_campaign_has_complete_profiles_and_roundtrips(tmp_path: Path) -> None:
    config = smoke_config()
    progress: list[str] = []
    result = run_campaign(config, workers=2, source_commit="test", progress=progress.append)
    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values()), result.invariants
    assert progress[0].startswith("run started mode=smoke")
    assert any("validation completed=4/4" in message for message in progress)
    expected_shapes = {
        "rhos": (5,),
        "effects": (6,),
        "condition_ids": (6,),
        "lanes": (2,),
        "calibration_effect_lr": (6, 2, 4),
        "calibration_spread_lr": (6, 4),
        "validation_effect_drops": (6, 2, 4, 6),
        "validation_spread_drops": (6, 4, 5),
        "validation_effect_mle": (6, 2, 4),
        "validation_spread_mle": (6, 4),
        "conditional_advantage": (6, 2, 4),
        "joint_advantage": (6, 2, 4),
        "representative_train_joint": (6, 5, 6),
        "event_diagnostics": (6, 4, 6),
    }
    assert {name: values.shape for name, values in result.profiles.items()} == expected_shapes
    for condition_index, truth in enumerate(TRUTHS):
        joint = result.profiles["representative_train_joint"][condition_index]
        rho_index = config.rhos.index(truth.rho)
        known = joint[rho_index]
        estimated = joint.max(axis=0)
        np.testing.assert_allclose(
            result.profiles["validation_effect_drops"][condition_index, :, 0],
            np.stack((2 * (known.max() - known), 2 * (estimated.max() - estimated))),
        )
        spread = joint.max(axis=1)
        np.testing.assert_allclose(
            result.profiles["validation_spread_drops"][condition_index, 0],
            2 * (spread.max() - spread),
        )
    written = write_campaign_bundle(result, tmp_path)
    assert tuple(path.name for path in written) == EXPECTED_FILES
    assert {path.name for path in tmp_path.iterdir()} == set(EXPECTED_FILES)
    with np.load(tmp_path / "profiles.npz", allow_pickle=False) as saved:
        assert set(saved.files) == set(result.profiles)
        for name in saved.files:
            np.testing.assert_array_equal(saved[name], result.profiles[name])
        assert tuple(saved["condition_ids"]) == tuple(truth.condition_id for truth in TRUTHS)
        assert tuple(saved["lanes"]) == LANES
    summary = json.loads((tmp_path / "run_summary.json").read_text())
    assert summary["mode"] == "smoke"
    assert not summary["is_production"]
    assert summary["source_commit"] == "test"
    assert summary["config"]["calibration_rank"] == config.calibration_rank
    assert summary["counts"]["validation_condition_datasets"] == 24
    assert summary["notes"]["event_diagnostics_sites"] == 120
    np.testing.assert_array_equal(
        result.profiles["event_diagnostics"][:, :, 0]
        + result.profiles["event_diagnostics"][:, :, 3],
        np.full((6, 4), 120),
    )
    assert tuple(summary["notes"]["event_diagnostics_order"]) == EVENT_DIAGNOSTICS
    assert (
        summary["profile_bundle_sha256"]
        == hashlib.sha256((tmp_path / "profiles.npz").read_bytes()).hexdigest()
    )
    seeds = json.loads((tmp_path / "seed_provenance.json").read_text())
    assert seeds["bank_checksum"] == result.bank_checksum
    assert seeds["bank_seeds"] == list(result.seed_manifest.bank_seeds)
    assert seeds["phase_roots_disjoint"]
    timing_dir = tmp_path / "timing"
    timing_written = write_campaign_bundle(replace(result, mode="timing"), timing_dir)
    assert tuple(path.name for path in timing_written) == (*EXPECTED_FILES, TIMING_BANK_FILENAME)
    np.testing.assert_array_equal(
        np.load(timing_dir / TIMING_BANK_FILENAME, allow_pickle=False), result.base_arrivals
    )


def test_cli_requires_explicit_mode_and_rejects_invalid_worker_count() -> None:
    script = Path(__file__).parents[1] / "scripts" / "run_arc2c_campaign.py"
    cases = (((), "--mode"), (("--mode", "smoke", "--workers", "0"), "positive"))
    for arguments, expected in cases:
        completed = subprocess.run(
            [sys.executable, str(script), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode != 0
        assert expected in completed.stderr
    with pytest.raises(ValueError, match="exact frozen production"):
        run_campaign(smoke_config(), mode="production", progress=None)
