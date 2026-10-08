from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

from latent_landscapes.arc2c_design import BridgeConfig
from latent_landscapes.arc3_campaign import run_campaign, write_campaign_bundle
from latent_landscapes.arc3_design import MASTER_SEED, PILOT_MAP_SEED, build_sampling_pair
from latent_landscapes.arc3_landscapes import ARCHETYPES, build_landscape, describe_landscape


def _checker() -> ModuleType:
    path = Path(__file__).parents[1] / "scripts" / "check_arc3_numerics.py"
    spec = importlib.util.spec_from_file_location("check_arc3_numerics", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_small_pilot(directory: Path, *, bank_size: int = 4) -> None:
    archetype = "connected"
    landscape = build_landscape(archetype, PILOT_MAP_SEED)
    sampling_seed = int(
        np.random.SeedSequence([MASTER_SEED, PILOT_MAP_SEED, 1]).generate_state(1)[0]
    )
    campaign_seed = int(
        np.random.SeedSequence(
            [MASTER_SEED, PILOT_MAP_SEED, ARCHETYPES.index(archetype), 2]
        ).generate_state(1)[0]
    )
    access, balanced = build_sampling_pair(landscape, sampling_seed)
    config = BridgeConfig(
        master_seed=campaign_seed,
        bank_size=bank_size,
        calibration_replicates=2,
        validation_replicates=2,
        calibration_rank=2,
        rhos=(0.5, 1.0, 2.0),
        effects=(1.0, 3.0, 5.0),
    )
    result = run_campaign(
        landscape,
        access,
        balanced,
        config,
        source_commit="test",
        scene_metadata={
            "archetype": archetype,
            "map_seed": PILOT_MAP_SEED,
            "sampling_seed": sampling_seed,
            "purpose": "test numerical replay",
            "landscape_descriptors": describe_landscape(landscape),
        },
    )
    write_campaign_bundle(result, directory)


def test_profile_change_centres_each_profile_and_uses_union() -> None:
    checker = _checker()
    old = np.asarray((0.0, -1.0, -8.0))
    new = np.asarray((-0.25, 0.0, -7.5))

    # The last point is outside LR<=10 in both profiles and is excluded.  The
    # first two are compared after each profile is centred on its own maximum.
    assert checker.profile_change(old, new) == pytest.approx(2.0)


@pytest.mark.parametrize("bank_only", [True, False])
def test_checker_reconstructs_and_replays_small_arc3_pilot(tmp_path: Path, bank_only: bool) -> None:
    checker = _checker()
    pilot = tmp_path / "pilot"
    _write_small_pilot(pilot)
    serial_output = tmp_path / "serial-review.json"
    parallel_output = tmp_path / "parallel-review.json"

    serial = checker.run_check(pilot, serial_output, bank_only=bank_only, workers=1)
    progress: list[str] = []
    payload = checker.run_check(
        pilot,
        parallel_output,
        bank_only=bank_only,
        workers=2,
        progress=progress.append,
    )

    assert payload["status"] == "incomplete_numerical_review"
    assert payload["bank_only"] is bank_only
    assert payload["workers"] == 2
    assert payload["bank_sizes"] == [4, 8]
    assert len(payload["conditions"]) == 24
    assert payload["full_ensemble_review_required"] is True
    assert serial["conditions"] == payload["conditions"]
    assert serial["all_within_pilot_limits"] == payload["all_within_pilot_limits"]
    assert progress[0] == "replay passed"
    assert "extra-bank ready draws=4" in progress
    assert "doubled-integration passed" in progress
    if bank_only:
        assert "refinement skipped bank-only" in progress
    else:
        assert "rho-refinement and effect-refinement passed" in progress
    assert progress[-1].startswith("numerical review completed total_seconds=")
    assert set(payload["runtimes_seconds"]) == {
        "replay_integration",
        "replay",
        "extra_bank",
        "doubled_integration",
        "doubled_evaluation",
        "rho_refinement",
        "effect_refinement",
        "refinement",
        "total",
    }
    with np.load(parallel_output.with_suffix(".npz"), allow_pickle=False) as saved:
        np.testing.assert_array_equal(saved["current_joint"], saved["replay_joint"])
        assert saved["doubled_joint"].shape == saved["current_joint"].shape
        if bank_only:
            assert saved["rho_refinement_subset"].size == 0
            assert saved["effect_refinement_subset"].size == 0
        else:
            assert saved["rho_refinement_subset"].size > 0
            assert saved["effect_refinement_subset"].size > 0
    with (
        np.load(serial_output.with_suffix(".npz"), allow_pickle=False) as serial_saved,
        np.load(parallel_output.with_suffix(".npz"), allow_pickle=False) as parallel_saved,
    ):
        assert serial_saved.files == parallel_saved.files
        for name in serial_saved.files:
            np.testing.assert_array_equal(serial_saved[name], parallel_saved[name])

    with (pilot / "profiles.npz").open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(ValueError, match="profile hash"):
        checker.run_check(pilot, tmp_path / "tampered.json", bank_only=True, workers=2)


def test_checker_requires_positive_workers() -> None:
    checker = _checker()
    with pytest.raises(ValueError, match="workers must be positive"):
        checker.run_check(Path("missing"), Path("output"), workers=0)
    with pytest.raises(checker.argparse.ArgumentTypeError, match="must be positive"):
        checker._positive_int("0")


def test_checker_rejects_unadmitted_production_summary(tmp_path: Path) -> None:
    checker = _checker()
    pilot = tmp_path / "pilot"
    _write_small_pilot(pilot)
    summary_path = pilot / "run_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary.update(
        mode="production",
        is_production=True,
        outcome="production_pending_numerical_review",
    )
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    with pytest.raises(ValueError, match="production freeze"):
        checker.run_check(pilot, tmp_path / "review.json")


def test_checker_reuses_and_reconciles_saved_doubled_bundle(tmp_path: Path) -> None:
    checker = _checker()
    selected_dir = tmp_path / "selected"
    reference_dir = tmp_path / "reference"
    _write_small_pilot(selected_dir, bank_size=4)
    _write_small_pilot(reference_dir, bank_size=8)

    regenerated = checker.run_check(selected_dir, tmp_path / "regenerated.json", workers=1)
    reused = checker.run_check(
        selected_dir,
        tmp_path / "reused.json",
        workers=2,
        reference_dir=reference_dir,
    )
    assert reused["reference_bundle"]["directory"] == str(reference_dir)
    assert regenerated["conditions"] == reused["conditions"]
    with (
        np.load((tmp_path / "regenerated.npz"), allow_pickle=False) as generated,
        np.load((tmp_path / "reused.npz"), allow_pickle=False) as saved,
    ):
        assert generated.files == saved.files
        for name in generated.files:
            np.testing.assert_array_equal(generated[name], saved[name])

    selected_bundle = checker._load_bundle(selected_dir)
    reference_bundle = checker._load_bundle(reference_dir)
    bad_bank = reference_bundle[2].copy()
    bad_bank[0, 0] += 1.0
    bad_reference = (*reference_bundle[:2], bad_bank, *reference_bundle[3:])
    with pytest.raises(ValueError, match="selected prefix"):
        checker._validate_reference_bundle(selected_bundle, bad_reference)

    reference_summary = reference_dir / "run_summary.json"
    summary = json.loads(reference_summary.read_text(encoding="utf-8"))
    summary["source_commit"] = "different"
    reference_summary.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match=r"profile hash|seed provenance|source_commit"):
        checker.run_check(
            selected_dir,
            tmp_path / "mismatched.json",
            reference_dir=reference_dir,
        )
