from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes.known_nuisance_calibration import (
    CALIBRATION_ROOT,
    EVALUATION_ROOT,
    VARIANT_IDS,
    AnalystDataset,
    AnalystHistory,
    evaluate_frozen_scores,
    production_config,
    run_campaign,
    score_observations,
    smoke_config,
    spawn_phase_seeds,
)

ROOT = Path(__file__).parents[1]
REGISTRATION = ROOT / "docs/goals/049-operational-calibration/registration-2026-09-20.md"


def test_phase_streams_are_disjoint_and_replicates_are_iid_tuples() -> None:
    calibration = spawn_phase_seeds(CALIBRATION_ROOT, "calibration", 12)
    evaluation = spawn_phase_seeds(EVALUATION_ROOT, "evaluation", 12)
    cal = {
        (row.process_seed, row.predator_detection_seed, row.prey_seed, row.prey_detection_seed)
        for row in calibration.records
    }
    eva = {
        (row.process_seed, row.predator_detection_seed, row.prey_seed, row.prey_detection_seed)
        for row in evaluation.records
    }
    assert len(cal) == len(eva) == 12
    assert cal.isdisjoint(eva)


def test_analyst_interface_has_no_truth_or_latent_state() -> None:
    forbidden = {"truth", "effect", "role", "arrival", "extirpation", "h"}
    signature = inspect.signature(score_observations)
    assert forbidden.isdisjoint(signature.parameters)
    assert forbidden.isdisjoint(AnalystDataset.__dataclass_fields__)
    assert forbidden.isdisjoint(AnalystHistory.__dataclass_fields__)


def test_smoke_campaign_retains_full_profiles_and_exact_identities(tmp_path: Path) -> None:
    config = smoke_config(calibration_replicates=2, evaluation_replicates=2)
    result = run_campaign(
        config,
        output_dir=tmp_path,
        registration_path=REGISTRATION,
        workers=2,
        progress=None,
    )
    assert result.run_summary["outcome"] == "non_scientific_smoke"
    assert result.run_summary["config"]["effects"] == [1.0, 3.0, 10.0]
    assert result.run_summary["variant_ids"] == list(VARIANT_IDS)
    assert all(result.run_summary["identity_controls"].values())
    assert all(result.run_summary["construction_controls"].values())
    for variant in VARIANT_IDS:
        calibration = np.load(tmp_path / f"calibration_profiles_{variant}.npy")
        evaluation = np.load(tmp_path / f"evaluation_profiles_{variant}.npy")
        holdout = np.load(tmp_path / f"evaluation_holdout_loglikelihood_{variant}.npy")
        assert calibration.shape == (3, 2, 3)
        assert evaluation.shape == holdout.shape == (3, 2, 3)
        assert np.all(calibration >= 0)
        assert np.all(evaluation.min(axis=-1) == 0)
    assert np.load(tmp_path / "cutoffs.npy").shape == (4, 3)
    assert np.load(tmp_path / "membership_candidate.npy").shape == (4, 3, 2, 3)
    frozen = json.loads((tmp_path / "frozen_scores.json").read_text())
    assert not frozen["truth_joined"]
    assert (tmp_path / "evaluation_truth_sidecar.json").is_file()
    resumed = run_campaign(
        config,
        output_dir=tmp_path,
        registration_path=REGISTRATION,
        workers=1,
        progress=None,
    )
    assert resumed.run_summary["run_fingerprint"] == result.run_summary["run_fingerprint"]
    assert resumed.run_summary["paired_across_truths"]


def test_inclusive_rank_and_oracle_identity_from_synthetic_frozen_scores(tmp_path: Path) -> None:
    config = smoke_config(calibration_replicates=2, evaluation_replicates=2)
    opaque = np.asarray([[f"id-{i}-{j}" for j in range(2)] for i in range(3)])
    np.save(tmp_path / "calibration_opaque_ids.npy", opaque)
    np.save(tmp_path / "evaluation_opaque_ids.npy", opaque)
    files: dict[str, str] = {}
    import hashlib

    for variant in VARIANT_IDS:
        calibration = np.asarray(
            [
                [[0.0, 2.0, 4.0], [0.0, 2.0, 4.0]],
                [[3.0, 1.0, 0.0], [3.0, 1.0, 0.0]],
                [[5.0, 2.0, 0.0], [5.0, 2.0, 0.0]],
            ]
        )
        evaluation = calibration.copy()
        holdout = -calibration
        for name, value in (
            (f"calibration_profiles_{variant}.npy", calibration),
            (f"evaluation_profiles_{variant}.npy", evaluation),
            (f"evaluation_holdout_loglikelihood_{variant}.npy", holdout),
        ):
            np.save(tmp_path / name, value)
    for path in tmp_path.glob("*.npy"):
        files[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path / "frozen_scores.json").write_text(
        json.dumps({"files": files, "truth_joined": False}), encoding="utf-8"
    )
    result = evaluate_frozen_scores(tmp_path, config)
    assert all(result["identity_controls"].values())
    candidate = np.load(tmp_path / "membership_candidate.npy")
    cutoffs = np.load(tmp_path / "cutoffs.npy")
    assert np.all(candidate[:, 0, :, 0])
    assert np.allclose(cutoffs[:, 0], 0.0)

    changed = tmp_path / f"calibration_profiles_{VARIANT_IDS[0]}.npy"
    calibration = np.load(changed)
    calibration[0, :, 0] = -1.0
    np.save(changed, calibration)
    frozen = json.loads((tmp_path / "frozen_scores.json").read_text())
    frozen["files"][changed.name] = hashlib.sha256(changed.read_bytes()).hexdigest()
    (tmp_path / "frozen_scores.json").write_text(json.dumps(frozen), encoding="utf-8")
    with pytest.raises(RuntimeError, match="identity failed"):
        evaluate_frozen_scores(tmp_path, config)


def test_production_requires_measured_budget_receipt(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="budget receipt"):
        run_campaign(
            production_config(),
            output_dir=tmp_path,
            registration_path=REGISTRATION,
            bank_cache_dir=tmp_path / "bank",
            progress=None,
        )


def test_cli_bounds_workers_and_smoke_only_counts() -> None:
    script = ROOT / "scripts/run_known_nuisance_calibration.py"
    cases = (
        (["--mode", "smoke", "--workers", "9"], "between 1 and 8"),
        (["--mode", "timing"], "--bank-cache"),
        (
            ["--mode", "production", "--bank-cache", "missing", "--smoke-calibration", "3"],
            "only be changed",
        ),
    )
    for arguments, expected in cases:
        completed = subprocess.run(
            [sys.executable, str(script), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode != 0
        assert expected in completed.stderr
