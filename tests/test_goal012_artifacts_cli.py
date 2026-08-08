from __future__ import annotations

import csv
import hashlib
import json
import runpy
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from latent_landscapes import cross_truth
from latent_landscapes.goal012 import artifacts, benchmark


def _expected_files() -> set[str]:
    return {
        "config.json",
        "compute_provenance.json",
        "seed_manifest.csv",
        "observation_signal_summary.csv",
        "calibration_results.csv",
        "validation_results.csv",
        "truth_cell_summary.csv",
        "representative_profiles.csv",
        "central_reconciliation.json",
        "summary.json",
        "verification.json",
        "review.md",
        "visuals/truth_grid_recovery_calibration.svg",
        "visuals/truth_grid_prediction.svg",
        "visuals/truth_grid_domain_and_ridge.svg",
    }


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle))


def _provenance() -> dict[str, object]:
    return {
        "provenance_mode": "test",
        "run_id": "goal012-tiny-test",
        "host_id": "local-test-host",
    }


@pytest.fixture(scope="module")
def small_result() -> benchmark.Goal012Result:
    return benchmark.run_campaign(
        cross_truth.CrossTruthConfig(
            bank_size=2,
            calibration_blocks=2,
            validation_blocks=2,
            calibration_rank_one_based=2,
            rhos=(0.5, 1.0, 2.0),
        ),
        workers=1,
    )


def test_exact_deterministic_15_file_review_pack_contract(
    tmp_path: Path,
    small_result: benchmark.Goal012Result,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    written = artifacts.write_review_bundle(small_result, first, _provenance())
    artifacts.write_review_bundle(small_result, second, _provenance())

    observed = {path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()}
    assert observed == _expected_files()
    assert len(written) == 15
    assert {path.relative_to(first).as_posix() for path in written} == observed
    for relative in observed:
        assert (first / relative).read_bytes() == (second / relative).read_bytes()
        contents = (first / relative).read_bytes()
        assert b"/Users/" not in contents
        assert b"/tmp/" not in contents
        assert b"NaN" not in contents
        assert b"Infinity" not in contents

    config = json.loads((first / "config.json").read_text(encoding="utf-8"))
    compute = json.loads((first / "compute_provenance.json").read_text(encoding="utf-8"))
    seeds = _read_csv(first / "seed_manifest.csv")
    signals = _read_csv(first / "observation_signal_summary.csv")
    calibration = _read_csv(first / "calibration_results.csv")
    validation = _read_csv(first / "validation_results.csv")
    summaries = _read_csv(first / "truth_cell_summary.csv")
    representatives = _read_csv(first / "representative_profiles.csv")
    central = json.loads((first / "central_reconciliation.json").read_text(encoding="utf-8"))
    summary = json.loads((first / "summary.json").read_text(encoding="utf-8"))
    verification = json.loads((first / "verification.json").read_text(encoding="utf-8"))
    review = (first / "review.md").read_text(encoding="utf-8").lower()

    assert config["known_detection_probability"] == 0.65
    assert config["false_positive_probability"] == 0.0
    assert config["records_per_dataset"] == 1920
    assert config["training_records_per_dataset"] == 1440
    assert config["holdout_records_per_dataset"] == 480
    assert config["candidate_etas"][-2:] == [2.25, 2.5]
    assert config["old_domain_eta_maximum"] == 2.0
    assert config["truth_cell_order"] == [cell.cell_id for cell in cross_truth.TRUTH_CELLS]
    assert compute["worker_count"] == 1
    assert compute["campaign_exit_success"] is True
    assert len(compute["cell_telemetry"]) == 9
    assert len(seeds) == 42
    assert len(signals) == 9 * 6
    assert len(calibration) == len(validation) == 9 * 3 * 2
    assert len(summaries) == 27
    assert len(representatives) == 9 * 3 * 11 * 3
    assert all(row["truth_cell"] == row["cutoff_source_cell"] for row in summaries)
    assert {
        "expanded_cutoff",
        "old_domain_cutoff",
        "rho_min_contact_count",
        "rho_max_contact_count",
        "eta_min_contact_count",
        "eta_max_contact_count",
        "expanded_candidate_domain_unclosed",
        "expanded_design_limited",
        "expanded_local_calibration_not_ready",
        "expanded_recovery_imprecise",
        "expanded_neutral_better",
        "expanded_recoverable",
        "expanded_mechanism_inconclusive",
        "expanded_class",
        "old_domain_class",
    } <= summaries[0].keys()
    assert central["truth_cell"] == "cell-04"
    assert all(central["checks"].values())
    assert summary["outcome"] == small_result.outcome
    assert summary["truth_cell_bank_count"] == 27
    assert summary["old_domain_projection_is_gating"] is False
    assert summary["pointwise_not_familywise"] is True
    assert verification["expected_artifact_file_count"] == 15
    assert verification["observed_artifact_file_count"] == 15
    assert all(verification["invariants"].values())
    for relative, expected_hash in verification["sha256"].items():
        assert relative != "verification.json"
        assert hashlib.sha256((first / relative).read_bytes()).hexdigest() == expected_hash
    assert "known p = 0.65" in review
    assert "process-paired" in review
    assert "observation-noise-distinct" in review
    assert "not familywise" in review
    assert "not a full joint spatial likelihood" in review
    assert "negative or mixed" in review

    for filename in (
        "truth_grid_recovery_calibration.svg",
        "truth_grid_prediction.svg",
        "truth_grid_domain_and_ridge.svg",
    ):
        svg = (first / "visuals" / filename).read_text(encoding="utf-8")
        assert svg.lstrip().startswith("<?xml")
        assert "<svg" in svg
        assert len(svg) > 5_000
        assert "dc:date" not in svg


def test_writer_refuses_blocked_result_and_destination_is_ignored(
    tmp_path: Path,
    small_result: benchmark.Goal012Result,
) -> None:
    with pytest.raises(ValueError, match="implementation-blocked"):
        artifacts.write_review_bundle(
            replace(small_result, outcome="implementation_blocked"),
            tmp_path / "blocked",
            _provenance(),
        )
    assert not (tmp_path / "blocked").exists()
    assert (
        subprocess.run(
            [
                "git",
                "check-ignore",
                "-q",
                "artifacts/goal012_cross_truth_joint_known_imperfect_detection",
            ],
            check=False,
        ).returncode
        == 0
    )


def test_cli_writes_completed_negative_and_rejects_scientific_tuning(
    tmp_path: Path,
    small_result: benchmark.Goal012Result,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    negative = replace(small_result, outcome="cross_truth_recovery_imprecise")
    output = tmp_path / "negative"
    provenance_path = tmp_path / "compute.json"
    provenance_path.write_text(json.dumps(_provenance()), encoding="utf-8")
    monkeypatch.setattr(benchmark, "run_campaign", lambda config, *, workers: negative)
    monkeypatch.setattr(
        artifacts,
        "validate_pre_campaign_provenance",
        lambda declared, *, workers: None,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scripts/run_goal012.py",
            "--output-dir",
            str(output),
            "--workers",
            "2",
            "--compute-provenance-json",
            str(provenance_path),
            "--reduced-smoke",
        ],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal012.py", run_name="__main__")

    assert raised.value.code == 0
    assert "cross_truth_recovery_imprecise" in capsys.readouterr().out
    assert {
        path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()
    } == _expected_files()

    for option in ("--bank-size", "--truth-rho", "--calibration-blocks", "--eta-grid"):
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/run_goal012.py",
                "--compute-provenance-json",
                str(provenance_path),
                option,
                "2",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 2
        assert "unrecognized arguments" in completed.stderr
