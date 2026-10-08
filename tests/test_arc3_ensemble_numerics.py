from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from latent_landscapes.arc2c_design import BridgeConfig
from latent_landscapes.arc3_campaign import run_campaign, write_campaign_bundle
from latent_landscapes.arc3_design import MASTER_SEED, PILOT_MAP_SEED, build_sampling_pair
from latent_landscapes.arc3_landscapes import ARCHETYPES, build_landscape, describe_landscape


def _checker():
    path = Path(__file__).parents[1] / "scripts" / "check_arc3_ensemble_numerics.py"
    spec = importlib.util.spec_from_file_location("check_arc3_ensemble_numerics", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _campaign(directory: Path, bank_size: int) -> None:
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
            "purpose": "test ensemble numerical review",
            "landscape_descriptors": describe_landscape(landscape),
        },
    )
    write_campaign_bundle(result, directory)


def test_nested_saved_bundles_reconcile_and_report_diagnostic_only(tmp_path: Path) -> None:
    checker = _checker()
    selected = tmp_path / "selected"
    doubled = tmp_path / "doubled"
    _campaign(selected, 4)
    _campaign(doubled, 8)

    # Keep the numerical values identical so this test isolates receipt and
    # comparison plumbing; the real doubled campaign supplies its own values.
    with np.load(selected / "profiles.npz", allow_pickle=False) as archive:
        profiles = {name: archive[name] for name in archive.files}
    np.savez_compressed(doubled / "profiles.npz", **profiles)
    summary_path = doubled / "run_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["profile_bundle_sha256"] = hashlib.sha256(
        (doubled / "profiles.npz").read_bytes()
    ).hexdigest()
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    output = tmp_path / "review.json"
    report = checker.run_check(selected, doubled, output)
    assert report["status"] == "diagnostic_only"
    assert report["all_checks_pass"] is True
    assert report["diagnostic_only"] is True
    assert output.with_suffix(".csv").exists()


def test_bank_receipt_tampering_is_rejected(tmp_path: Path) -> None:
    checker = _checker()
    selected = tmp_path / "selected"
    doubled = tmp_path / "doubled"
    _campaign(selected, 4)
    _campaign(doubled, 8)
    bank = np.load(selected / "base_arrivals.npy", allow_pickle=False).copy()
    bank[0, 0] += 1.0
    np.save(selected / "base_arrivals.npy", bank, allow_pickle=False)
    with pytest.raises(ValueError, match="seed or bank receipt"):
        checker.run_check(selected, doubled, tmp_path / "review.json")


def test_boundary_swap_is_detected_even_when_or_classification_is_unchanged() -> None:
    checker = _checker()
    shape = (6, 2, 1)
    selected = {
        "components": np.ones(shape, dtype=int),
        "lower": np.ones(shape, dtype=bool),
        "upper": np.zeros(shape, dtype=bool),
        "boundary": np.ones(shape, dtype=bool),
        "coverage_count": np.ones(shape, dtype=int),
        "exclusion_count": np.ones(shape, dtype=int),
    }
    doubled = {name: value.copy() for name, value in selected.items()}
    doubled["lower"][:] = False
    doubled["upper"][:] = True
    truths = tuple(SimpleNamespace(condition_id=f"condition_{index}") for index in range(6))
    rows = checker._support_review_rows(selected, doubled, np.zeros(shape, dtype=int), truths)
    assert rows[0]["boundary_classification_unchanged"] is True
    assert rows[0]["lower_boundary_unchanged"] is False
    assert rows[0]["upper_boundary_unchanged"] is False


def test_production_eligibility_requires_exact_grids_and_rank() -> None:
    checker = _checker()
    config = SimpleNamespace(
        bank_size=16384,
        calibration_replicates=250,
        validation_replicates=250,
        calibration_rank=239,
        rhos=checker.PRODUCTION_RHOS,
        effects=checker.PRODUCTION_EFFECTS,
    )
    summary = {
        "mode": "production",
        "is_production": True,
        "scene_metadata": {
            "archetype": "connected",
            "map_seed": 2026090811,
            "sampling_seed": int(
                np.random.SeedSequence(
                    [checker.arc3.arc3_design.MASTER_SEED, 2026090811, 1]
                ).generate_state(1)[0]
            ),
        },
    }
    freeze = {
        "schema_version": 1,
        "goal": "046",
        "selected_bank_size": 16384,
        "reference_bank_size": 32768,
        "master_seed": checker.arc3.arc3_design.MASTER_SEED,
        "archetypes": list(checker.arc3.ARCHETYPES),
        "production_map_seeds": list(checker.arc3.PRODUCTION_MAP_SEEDS),
        "rhos": checker.PRODUCTION_RHOS.tolist(),
        "effects": checker.PRODUCTION_EFFECTS.tolist(),
        "calibration_replicates": 250,
        "validation_replicates": 250,
        "calibration_rank": 239,
        "qualification_receipt": {"sha256": "a" * 64},
        "source_snapshot_sha256": "b" * 64,
    }
    freeze_sha = checker.arc3._freeze_sha256(freeze)
    summary["scene_metadata"]["production_freeze"] = freeze
    summary["scene_metadata"]["production_freeze_sha256"] = freeze_sha
    summary["source_provenance"] = {
        "production_freeze": freeze,
        "production_freeze_sha256": freeze_sha,
    }
    campaign_seed = int(
        np.random.SeedSequence(
            [
                checker.arc3.arc3_design.MASTER_SEED,
                2026090811,
                checker.arc3.ARCHETYPES.index("connected"),
                2,
            ]
        ).generate_state(1)[0]
    )
    config.master_seed = campaign_seed
    bundle = SimpleNamespace(config=config)
    reference_config = SimpleNamespace(**{**vars(config), "bank_size": 32768})
    record = {"bundle": bundle, "summary": summary}
    reference_record = {"bundle": SimpleNamespace(config=reference_config), "summary": summary}
    assert checker._production_eligible(record, reference_record) is True
    altered = SimpleNamespace(
        config=SimpleNamespace(**{**vars(config), "rhos": config.rhos.copy()})
    )
    altered.config.rhos[100] += 1e-9
    altered_record = {"bundle": altered, "summary": summary}
    assert checker._production_eligible(record, altered_record) is False


def test_full_size_pilot_is_not_production_eligible() -> None:
    checker = _checker()
    config = SimpleNamespace(
        master_seed=0,
        calibration_replicates=250,
        validation_replicates=250,
        calibration_rank=239,
        rhos=checker.PRODUCTION_RHOS,
        effects=checker.PRODUCTION_EFFECTS,
    )
    record = {
        "bundle": SimpleNamespace(config=config),
        "summary": {
            "mode": "pilot",
            "is_production": False,
            "scene_metadata": {
                "archetype": "connected",
                "map_seed": 2026090811,
                "sampling_seed": 0,
            },
        },
    }
    assert checker._production_eligible(record, record) is False


def test_production_eligibility_rejects_missing_or_wrong_recorded_freeze() -> None:
    checker = _checker()
    config = SimpleNamespace(
        bank_size=16384,
        calibration_replicates=250,
        validation_replicates=250,
        calibration_rank=239,
        rhos=checker.PRODUCTION_RHOS,
        effects=checker.PRODUCTION_EFFECTS,
        master_seed=0,
    )
    scene = {
        "archetype": "connected",
        "map_seed": 2026090811,
        "sampling_seed": 0,
    }
    summary = {
        "mode": "production",
        "is_production": True,
        "scene_metadata": scene,
        "source_provenance": {},
    }
    record = {"bundle": SimpleNamespace(config=config), "summary": summary}
    assert checker._production_eligible(record, record) is False


def test_paired_count_contrast_allows_one_history_and_rejects_two() -> None:
    checker = _checker()
    base = {
        "mean_absolute_log_error": np.zeros(1),
        "mean_log_width": np.zeros(1),
        "conditional_advantage": np.zeros(1),
        "coverage_count": np.zeros(1),
        "exclusion_count": np.zeros(1),
    }
    one = {name: value.copy() for name, value in base.items()}
    one["coverage_count"][0] = 1
    _, counts, passes = checker._paired_contrast_review(base, one)
    assert counts["coverage_count"] == 1
    assert passes is True
    two = {name: value.copy() for name, value in base.items()}
    two["coverage_count"][0] = 2
    _, counts, passes = checker._paired_contrast_review(base, two)
    assert counts["coverage_count"] == 2
    assert passes is False
