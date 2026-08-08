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
from latent_landscapes.goal013 import artifacts, benchmark


def _expected_files() -> set[str]:
    return {
        "config.json",
        "compute_provenance.json",
        "design_candidates.csv",
        "selected_clusters.csv",
        "design_sites.csv",
        "seed_manifest.csv",
        "existing_evidence_reconciliation.csv",
        "calibration_results.csv",
        "validation_results.csv",
        "cell_bank_summary.csv",
        "baseline_intervention_comparison.csv",
        "observation_signal_summary.csv",
        "representative_profiles.csv",
        "summary.json",
        "verification.json",
        "review.md",
        "visuals/design_comparison.svg",
        "visuals/recovery_comparison.svg",
    }


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle))


def _provenance() -> dict[str, object]:
    return {
        "provenance_mode": "test",
        "run_id": "goal013-test",
        "host_id": "test-host",
    }


@pytest.fixture(scope="module")
def small_result() -> benchmark.Goal013Result:
    return benchmark.run_campaign(
        benchmark.Goal013Config(
            cross_truth_config=cross_truth.CrossTruthConfig(
                master_seed=20260730,
                bank_size=2,
                calibration_blocks=2,
                validation_blocks=2,
                calibration_rank_one_based=2,
                rhos=(0.5, 1.0, 2.0),
            )
        ),
        workers=1,
    )


def test_exact_deterministic_18_file_review_pack_contract(
    tmp_path: Path,
    small_result: benchmark.Goal013Result,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    written = artifacts.write_review_bundle(small_result, first, _provenance())
    artifacts.write_review_bundle(small_result, second, _provenance())

    assert {path.relative_to(first).as_posix() for path in written} == _expected_files()
    assert {
        path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()
    } == _expected_files()
    for relative in _expected_files():
        assert (first / relative).read_bytes() == (second / relative).read_bytes()
        contents = (first / relative).read_bytes()
        assert not any(
            token in contents for token in (b"/Users/", b"/tmp/", b"/data/", b"NaN", b"Infinity")
        )

    config = json.loads((first / "config.json").read_text(encoding="utf-8"))
    summary = json.loads((first / "summary.json").read_text(encoding="utf-8"))
    verification = json.loads((first / "verification.json").read_text(encoding="utf-8"))
    candidates = _read_csv(first / "design_candidates.csv")
    clusters = _read_csv(first / "selected_clusters.csv")
    sites = _read_csv(first / "design_sites.csv")
    seeds = _read_csv(first / "seed_manifest.csv")
    evidence = _read_csv(first / "existing_evidence_reconciliation.csv")
    calibration = _read_csv(first / "calibration_results.csv")
    validation = _read_csv(first / "validation_results.csv")
    summaries = _read_csv(first / "cell_bank_summary.csv")
    comparisons = _read_csv(first / "baseline_intervention_comparison.csv")
    signals = _read_csv(first / "observation_signal_summary.csv")
    profiles = _read_csv(first / "representative_profiles.csv")
    review = (first / "review.md").read_text(encoding="utf-8").lower()

    assert config["target_truth_cells"] == ["cell-00", "cell-01", "cell-02", "cell-04"]
    assert config["known_detection_probability"] == 0.65
    assert config["records_per_dataset"] == 1920
    assert config["training_records_per_dataset"] == 1440
    assert config["holdout_records_per_dataset"] == 480
    assert config["selector_attempts"] == 10_000
    assert config["selector_seed"] == 20_260_731
    assert config["design_digest"] == (
        "ba887b460d8a8dff1b731086de77dd2d00edce1c00d37c8550fa161558092410"
    )
    assert len(candidates) == 635
    assert len(clusters) == 32
    assert len(sites) == 160
    assert len(seeds) == 58
    assert len(evidence) == 6
    assert len(calibration) == len(validation) == 4 * 3 * 2
    assert len(summaries) == 12
    assert len(comparisons) == 9
    assert len(signals) == 24
    assert len(profiles) == 4 * 3 * 11 * 3
    assert summary["outcome"] == small_result.outcome
    assert summary["baseline_reused_not_rerun"] is True
    assert summary["record_level_detection_noise_paired"] is False
    assert verification["expected_artifact_file_count"] == 18
    assert verification["observed_artifact_file_count"] == 18
    assert all(verification["invariants"].values())
    for relative, expected_hash in verification["sha256"].items():
        assert relative != "verification.json"
        assert hashlib.sha256((first / relative).read_bytes()).hexdigest() == expected_hash
    assert "design-specific operating-performance" in review
    assert "not a matched causal estimate" in review
    assert "not a full joint spatial likelihood" in review

    for filename in ("design_comparison.svg", "recovery_comparison.svg"):
        svg = (first / "visuals" / filename).read_text(encoding="utf-8")
        assert svg.lstrip().startswith("<?xml")
        assert "<svg" in svg
        assert len(svg) > 5_000
        assert "dc:date" not in svg


def test_writer_refuses_blocked_failed_or_stale_results(
    tmp_path: Path,
    small_result: benchmark.Goal013Result,
) -> None:
    with pytest.raises(ValueError, match="implementation-blocked"):
        artifacts.write_review_bundle(
            replace(small_result, outcome="implementation_blocked"),
            tmp_path / "blocked",
            _provenance(),
        )
    failed = replace(small_result, invariants=small_result.invariants | {"forced": False})
    with pytest.raises(ValueError, match="failed implementation invariants"):
        artifacts.write_review_bundle(failed, tmp_path / "failed", _provenance())
    stale = tmp_path / "stale"
    stale.mkdir()
    (stale / "old.txt").write_text("old", encoding="utf-8")
    with pytest.raises(RuntimeError, match="stale"):
        artifacts.write_review_bundle(small_result, stale, _provenance())
    assert (
        subprocess.run(
            [
                "git",
                "check-ignore",
                "-q",
                "artifacts/goal013_weak_contrast_sampling_design_intervention",
            ],
            check=False,
        ).returncode
        == 0
    )


def test_reduced_smoke_cli_writes_completed_negative_and_rejects_tuning(
    tmp_path: Path,
    small_result: benchmark.Goal013Result,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    negative = replace(small_result, outcome="contrast_balancing_not_supported")
    output = tmp_path / "negative"
    monkeypatch.setattr(benchmark, "run_campaign", lambda config, *, workers: negative)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scripts/run_goal013.py",
            "--output-dir",
            str(output),
            "--reduced-smoke",
        ],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal013.py", run_name="__main__")

    assert raised.value.code == 0
    assert "contrast_balancing_not_supported" in capsys.readouterr().out
    assert {
        path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()
    } == _expected_files()

    for option in (
        "--bank-size",
        "--selector-seed",
        "--truth-rho",
        "--calibration-blocks",
        "--eta-grid",
    ):
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/run_goal013.py",
                "--reduced-smoke",
                option,
                "2",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 2
        assert "unrecognized arguments" in completed.stderr
