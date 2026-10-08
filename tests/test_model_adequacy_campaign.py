from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes.model_adequacy_campaign import (
    FRESH_CALIBRATION_ROOT,
    FRESH_EVALUATION_ROOT,
    ORIGINAL_CALIBRATION_ROOT,
    ORIGINAL_EVALUATION_ROOT,
    production_config,
    run_campaign,
    smoke_config,
    spawn_phase_seeds,
    validate_production_budget,
)

ROOT = Path(__file__).parents[1]
REGISTRATION = ROOT / "docs/goals/050-model-adequacy/registration-2026-09-20.md"


def test_registered_seed_roots_are_disjoint_and_reproducible() -> None:
    roots = (
        ORIGINAL_CALIBRATION_ROOT,
        ORIGINAL_EVALUATION_ROOT,
        FRESH_CALIBRATION_ROOT,
        FRESH_EVALUATION_ROOT,
    )
    assert len(set(roots)) == 4
    first = spawn_phase_seeds(FRESH_CALIBRATION_ROOT, "calibration", 4)
    second = spawn_phase_seeds(FRESH_CALIBRATION_ROOT, "calibration", 4)
    assert first == second
    assert (
        len(
            {
                (
                    row.process_seed,
                    row.predator_detection_seed,
                    row.prey_seed,
                    row.prey_detection_seed,
                )
                for row in first
            }
        )
        == 4
    )


def test_smoke_outputs_have_registered_phase_schema(tmp_path: Path) -> None:
    result = run_campaign(
        smoke_config(),
        output_dir=tmp_path,
        registration_path=REGISTRATION,
        workers=2,
        progress=None,
    )
    assert result["outcome"] == "non_scientific_smoke"
    for phase in ("calibration", "evaluation", "new_calibration", "new_evaluation"):
        with np.load(tmp_path / f"{phase}.npz", allow_pickle=False) as values:
            expected_shape = (1, 2) if phase.startswith("new_") else (3, 2)
            assert values["prey_score"].shape == expected_shape
            assert values["predator_score"].shape == expected_shape
            assert values["mle_index"].shape == expected_shape
            if phase.startswith("new_"):
                assert values["profiles"].shape == (1, 2, 3)
            else:
                assert "profiles" not in values
    summary = json.loads((tmp_path / "run_summary.json").read_text())
    assert summary["pairing"]["truths_within_replicate"]
    assert set(summary["output_hashes"]) == {
        "calibration.npz",
        "evaluation.npz",
        "new_calibration.npz",
        "new_evaluation.npz",
    }


def test_cli_help_and_worker_bound() -> None:
    script = ROOT / "scripts/run_model_adequacy.py"
    help_result = subprocess.run(
        [sys.executable, str(script), "--help"], capture_output=True, text=True, check=False
    )
    assert help_result.returncode == 0
    result = subprocess.run(
        [sys.executable, str(script), "--mode", "smoke", "--workers", "9"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "between 1 and 8" in result.stderr


def test_budget_receipt_binds_exact_arithmetic_and_rejects_tampering(tmp_path: Path) -> None:
    config = production_config()
    source = {"source.py": "abc"}
    timing = {
        "config": __import__("dataclasses").asdict(production_config("timing")),
        "source_and_registration_sha256": source,
        "original_manifest_sha256": "manifest",
        "outcome": "timing_complete",
        "runtime_seconds": {"total": 100.0},
        "replay_controls": {
            "calibration": {"controls": {"ok": True}},
            "evaluation": {"controls": {"ok": True}},
        },
        "timing_projection": {
            "scoring_projection_factor": 1.5,
            "production_workload_seconds_conservative": 200.0,
        },
    }
    timing_path = tmp_path / "timing.json"
    timing_path.write_text(json.dumps(timing))
    import hashlib

    receipt = {
        "timing_summary_path": str(timing_path),
        "timing_summary_sha256": hashlib.sha256(timing_path.read_bytes()).hexdigest(),
        "prior_computation_allowance_seconds": 1800,
        "timing_seconds_measured": 100,
        "production_workload_seconds": 200,
        "synthesis_seconds_reserved": 3600,
        "total_projected_seconds": 5700,
        "remaining_budget_seconds": 41300,
        "production_timeout_seconds": 37670,
        "within_12h": True,
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt))
    assert (
        validate_production_budget(
            receipt_path,
            config=config,
            source_hashes=source,
            original_manifest_hash="manifest",
        )
        == receipt
    )
    for key, bad in (
        ("production_workload_seconds", 199.0),
        ("production_timeout_seconds", float("nan")),
    ):
        altered = dict(receipt)
        altered[key] = bad
        altered_path = tmp_path / f"bad-{key}.json"
        altered_path.write_text(json.dumps(altered, allow_nan=True))
        with pytest.raises(ValueError):
            validate_production_budget(
                altered_path,
                config=config,
                source_hashes=source,
                original_manifest_hash="manifest",
            )


def test_resume_rejects_corrupt_completed_shard(tmp_path: Path) -> None:
    run_campaign(
        smoke_config(),
        output_dir=tmp_path,
        registration_path=REGISTRATION,
        workers=1,
        progress=None,
    )
    shard = tmp_path / "shards" / "calibration" / "0000.npz"
    with np.load(shard, allow_pickle=False) as values:
        payload = {name: values[name] for name in values.files}
    payload["prey_score"] = np.asarray(payload["prey_score"]).copy()
    payload["prey_score"][0] += 1.0
    np.savez_compressed(shard, **payload)
    with pytest.raises(ValueError, match="corrupt payload"):
        run_campaign(
            smoke_config(),
            output_dir=tmp_path,
            registration_path=REGISTRATION,
            workers=1,
            progress=None,
        )


def test_timing_legacy_config_and_opaque_roots_match_contract() -> None:
    from latent_landscapes import known_nuisance_calibration as old
    from latent_landscapes import model_adequacy_campaign as campaign

    config = production_config("timing")
    for phase, root in (
        ("calibration", ORIGINAL_CALIBRATION_ROOT),
        ("evaluation", ORIGINAL_EVALUATION_ROOT),
    ):
        cfg = campaign._legacy_config(config, phase, root)
        assert cfg.mode == "timing"
        seed = spawn_phase_seeds(root, phase, 1)[0]
        assert old._opaque_ids(cfg, seed, 6) == old._opaque_ids(old.production_config(), seed, 6)
    fresh = campaign._legacy_config(config, "calibration", FRESH_CALIBRATION_ROOT)
    seed = spawn_phase_seeds(FRESH_CALIBRATION_ROOT, "calibration", 1)[0]
    assert old._opaque_ids(fresh, seed, 1) != old._opaque_ids(old.production_config(), seed, 1)


def test_timing_checks_entire_registered_seed_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    from latent_landscapes import model_adequacy_campaign as campaign

    counts: list[int] = []
    original_spawn = campaign.spawn_phase_seeds

    def capture(root: int, phase: str, count: int):  # type: ignore[no-untyped-def]
        counts.append(count)
        return original_spawn(root, phase, count)

    monkeypatch.setattr(campaign, "spawn_phase_seeds", capture)
    from latent_landscapes import known_nuisance_calibration as old

    monkeypatch.setattr(old, "_expected_archived_bank_seeds", lambda _: ())
    controls = campaign._seed_controls(production_config("timing"), {"bank_checksum": "test"})
    assert counts == [999, 1000, 999, 1000]
    assert all(controls.values())


def test_missing_original_controls_are_rejected_before_array_access(tmp_path: Path) -> None:
    from dataclasses import asdict

    from latent_landscapes import known_nuisance_calibration as old
    from latent_landscapes import model_adequacy_campaign as campaign

    contract = {
        "workflow": "goal049-known-nuisance-calibration",
        "config": asdict(old.production_config()),
        "run_fingerprint": "fixture",
    }
    summary = {
        "run_fingerprint": "fixture",
        "outcome": "production_scores_complete",
        "identity_controls": {},
    }
    for name, payload in (
        ("run_contract.json", contract),
        ("run_summary.json", summary),
        ("frozen_scores.json", {"truth_joined": False}),
    ):
        (tmp_path / name).write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="input contract"):
        campaign.load_original_inputs(tmp_path, config=production_config("timing"))
