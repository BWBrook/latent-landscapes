from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from latent_landscapes import misspecification_campaign as campaign

ROOT = Path(__file__).parents[1]


def test_registered_configs_and_cell_contract() -> None:
    assert campaign.production_config().replicates == 1000
    assert campaign.timing_config().replicates == 16
    assert campaign.smoke_config().replicates in (1, 2)
    with pytest.raises(ValueError):
        campaign.CampaignConfig("production", (1.0, 2.0), campaign.TRUTHS, 2, 16)


def test_config_rejects_registered_root_reuse() -> None:
    with pytest.raises(ValueError, match="roots"):
        campaign.CampaignConfig(
            "smoke",
            (1.0, 3.0, 5.0),
            campaign.TRUTHS,
            1,
            16,
            campaign.SMOKE_ROOT,
            campaign.ARCHIVED_BANK_ROOT,
            campaign.ORIGINAL_ROOTS[0],
        )


def test_generator_rows_are_ordered_and_numeric_diagnostics() -> None:
    specs = tuple(SimpleNamespace(cell_id=f"c{i}", truth_h=1.0) for i in range(17))
    rows = tuple(
        SimpleNamespace(
            cell=spec,
            dataset=SimpleNamespace(opaque_id=f"id{i}"),
            diagnostics={"field_mean": float(i)},
        )
        for i, spec in enumerate(specs)
    )
    datasets, diagnostics = campaign._normalise_generated(rows, specs)
    assert len(datasets) == 17
    assert diagnostics["field_mean"].shape == (17,)
    assert diagnostics["field_mean"][3] == 3.0


def test_generator_rows_reject_order_drift() -> None:
    specs = tuple(SimpleNamespace(cell_id=f"c{i}", truth_h=1.0) for i in range(17))
    rows = tuple(
        SimpleNamespace(cell=spec, dataset=SimpleNamespace(opaque_id=f"id{i}"))
        for i, spec in enumerate(reversed(specs))
    )
    with pytest.raises(ValueError, match="order"):
        campaign._normalise_generated(rows, specs)


def test_seed_controls_cover_all_registered_campaign_modes() -> None:
    config = campaign.smoke_config(replicates=1, bank_size=8)
    seeds = campaign._spawn_seeds(config)
    controls = campaign._seed_controls(config, seeds, {"bank_checksum": "fixture"})
    assert controls["all_registered_campaign_modes_disjoint"]
    assert controls["campaign_vs_original_streams_disjoint"]
    assert all(controls.values())


def test_cli_rejects_worker_overflow() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_misspecification.py"),
            "--mode",
            "smoke",
            "--workers",
            "9",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "between 1 and 8" in result.stderr


def test_cli_help_is_available() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_misspecification.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "misspecification" in result.stdout


def test_budget_receipt_binds_components_and_rejects_tampering(tmp_path: Path) -> None:
    helper_contents = {
        "run-bounded.sh": "bounded",
        "run-synthesis.sh": "synthesis",
        "prepare-production-budget.py": "budget",
    }
    helper_hashes = {}
    for name, content in helper_contents.items():
        helper = tmp_path / name
        helper.write_text(content, encoding="utf-8")
        helper_hashes[name] = hashlib.sha256(content.encode()).hexdigest()
    source = {
        "source.py": "abc",
        **{str((tmp_path / name).resolve()): digest for name, digest in helper_hashes.items()},
    }
    input_hash = "input"
    timing = {
        "outcome": "timing_complete",
        "source_hashes": source,
        "input_hash": input_hash,
        "workers": 2,
        "config": asdict(campaign.timing_config()),
        "timings": {"total": 100.0},
        "timing_projection": {
            "scoring_projection_factor": 1.5,
            "production_workload_seconds_conservative": 200.0,
        },
    }
    timing_path = tmp_path / "timing.json"
    timing_path.write_text(json.dumps(timing), encoding="utf-8")
    receipt = {
        "timing_summary_path": str(timing_path),
        "timing_summary_sha256": hashlib.sha256(timing_path.read_bytes()).hexdigest(),
        "preparation_seconds": 1200.0,
        "timing_seconds": 100.0,
        "production_workload_seconds": 200.0,
        "synthesis_seconds_reserved": 1800.0,
        "grace_seconds": 30.0,
        "total_projected_seconds": 3330.0,
        "remaining_budget_seconds": 13100.0,
        "production_timeout_seconds": 11000.0,
        "within_4h": True,
        "bounded_wrapper_sha256": helper_hashes["run-bounded.sh"],
        "synthesis_wrapper_sha256": helper_hashes["run-synthesis.sh"],
        "budget_preparer_sha256": helper_hashes["prepare-production-budget.py"],
    }
    receipt_path = tmp_path / "budget.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert (
        campaign.validate_production_budget(
            receipt_path,
            config=campaign.production_config(),
            source_hashes=source,
            input_hash=input_hash,
            workers=2,
        )
        == receipt
    )
    altered = dict(receipt, total_projected_seconds=3331.0)
    altered_path = tmp_path / "bad-budget.json"
    altered_path.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ValueError, match="timing/source/input"):
        campaign.validate_production_budget(
            altered_path,
            config=campaign.production_config(),
            source_hashes=source,
            input_hash=input_hash,
            workers=2,
        )

    with pytest.raises(ValueError, match="timing/source/input"):
        altered = dict(receipt, within_4h=False)
        altered_path.write_text(json.dumps(altered), encoding="utf-8")
        campaign.validate_production_budget(
            altered_path,
            config=campaign.production_config(),
            source_hashes=source,
            input_hash=input_hash,
            workers=2,
        )

    altered = dict(receipt, production_timeout_seconds=1.0)
    altered_path.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ValueError, match="timing/source/input"):
        campaign.validate_production_budget(
            altered_path,
            config=campaign.production_config(),
            source_hashes=source,
            input_hash=input_hash,
            workers=2,
        )


def test_one_block_small_bank_smoke_is_complete(tmp_path: Path) -> None:
    summary = campaign.run_campaign(
        campaign.smoke_config(replicates=1, bank_size=8),
        output_dir=tmp_path,
        registration_path=ROOT
        / "docs/goals/051-misspecification-screen/registration-2026-09-23.md",
        reference_dir=None,
        workers=1,
        progress=None,
    )
    assert summary["outcome"] == "non_scientific_smoke"
    with np.load(tmp_path / "campaign_arrays.npz", allow_pickle=False) as values:
        assert values["profiles"].shape == (17, 1, 3)
        assert values["holdout_joint"].shape == (17, 1, 3)
        assert values["opaque_ids"].shape == (17, 1)
