from __future__ import annotations

import csv
import json
import runpy
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from latent_landscapes.goal007 import artifacts, benchmark


def _expected_files() -> set[str]:
    return {
        "config.json",
        "seed_manifest.csv",
        "observation_signal_summary.csv",
        "calibration_results.csv",
        "validation_results.csv",
        "bank_summary.csv",
        "predictive_summary.csv",
        "representative_profile.csv",
        "summary.json",
        "verification.json",
        "review.md",
        "visuals/joint_profile_surface.svg",
        "visuals/recovery_calibration.svg",
        "visuals/bank_predictive_comparison.svg",
    }


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle))


@pytest.fixture(scope="module")
def small_result() -> benchmark.Goal007Result:
    return benchmark.run_goal007(
        benchmark.Goal007Config(
            master_seed=91,
            bank_size=4,
            calibration_replicates=3,
            validation_replicates=2,
            calibration_rank_one_based=3,
            rhos=(0.5, 1.0, 2.0),
            etas=(0.0, 1.0, 2.0),
        )
    )


def test_exact_deterministic_review_pack_and_table_reconciliation(
    tmp_path: Path,
    small_result: benchmark.Goal007Result,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    written = artifacts.write_review_bundle(small_result, first)
    artifacts.write_review_bundle(small_result, second)

    observed = {path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()}
    assert observed == _expected_files()
    assert len(written) == 14
    assert {path.relative_to(first).as_posix() for path in written} == observed
    for relative in observed:
        assert (first / relative).read_bytes() == (second / relative).read_bytes()
        contents = (first / relative).read_bytes()
        assert b"/Users/" not in contents
        assert b"/tmp/" not in contents
        assert b"NaN" not in contents
        assert b"Infinity" not in contents

    config = json.loads((first / "config.json").read_text(encoding="utf-8"))
    seeds = _read_csv(first / "seed_manifest.csv")
    calibration = _read_csv(first / "calibration_results.csv")
    validation = _read_csv(first / "validation_results.csv")
    banks = _read_csv(first / "bank_summary.csv")
    predictive = _read_csv(first / "predictive_summary.csv")
    representative = _read_csv(first / "representative_profile.csv")
    summary = json.loads((first / "summary.json").read_text(encoding="utf-8"))
    verification = json.loads((first / "verification.json").read_text(encoding="utf-8"))
    review = (first / "review.md").read_text(encoding="utf-8")

    assert config["method"] == "site-history simulated composite likelihood"
    assert config["perfect_detection_positive_control"] is True
    assert config["is_full_joint_spatial_likelihood"] is False
    assert config["analyst_records_per_dataset"] == 1920
    assert config["distinct_site_time_outcomes_per_dataset"] == 960
    assert len(seeds) == 4 + 3 + 2
    assert {row["stream_role"] for row in seeds} == {
        "paired_eta_process",
        "central_truth_process",
    }
    assert len(calibration) == 3 * 3
    assert len(validation) == 2 * 3
    assert len(banks) == len(predictive) == 3
    assert len(representative) == 3 * 3 * 3
    assert {row["dataset_index"] for row in representative} == {"0"}
    assert summary["outcome"] == small_result.outcome
    assert summary["conditional_scope"] == "one landscape and one central truth"
    assert verification["expected_artifact_file_count"] == 14
    assert verification["observed_artifact_file_count"] == 14
    assert all(verification["invariants"].values())
    assert "perfect detection" in review.lower()
    assert "positive control" in review.lower()
    assert "not a full joint spatial likelihood" in review
    assert "one landscape and one central truth" in review
    assert "generated observations" in review.lower()
    assert "scientific inference" in review.lower()

    for filename in (
        "joint_profile_surface.svg",
        "recovery_calibration.svg",
        "bank_predictive_comparison.svg",
    ):
        svg = (first / "visuals" / filename).read_text(encoding="utf-8")
        assert svg.lstrip().startswith("<?xml")
        assert "<svg" in svg
        assert len(svg) > 8_000
        assert "dc:date" not in svg


def test_review_pack_rejects_stale_files_and_blocked_results(
    tmp_path: Path,
    small_result: benchmark.Goal007Result,
) -> None:
    stale = tmp_path / "stale"
    stale.mkdir()
    (stale / "unexpected.txt").write_text("stale\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="stale"):
        artifacts.write_review_bundle(small_result, stale)
    with pytest.raises(ValueError, match="implementation-blocked"):
        artifacts.write_review_bundle(
            replace(small_result, outcome="implementation_blocked"),
            tmp_path / "blocked",
        )
    assert not (tmp_path / "blocked").exists()


def test_artifact_destinations_are_ignored() -> None:
    for path in (
        "artifacts/goal007_joint_rho_eta_perfect_detection",
        "artifacts/goal007_joint_rho_eta_perfect_detection_repeat",
    ):
        completed = subprocess.run(["git", "check-ignore", "-q", path], check=False)
        assert completed.returncode == 0


def test_svg_path_collection_identifiers_are_process_independent() -> None:
    first = '<path id="C0_0_9c55683775"/><use xlink:href="#C0_0_9c55683775"/>'
    second = '<path id="C0_0_55e6355fe0"/><use xlink:href="#C0_0_55e6355fe0"/>'

    assert artifacts._normalize_svg_ids(first) == artifacts._normalize_svg_ids(second)


def test_cli_writes_negative_completed_class_and_rejects_tuning_options(
    tmp_path: Path,
    small_result: benchmark.Goal007Result,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    negative = replace(small_result, outcome="joint_recovery_imprecise")
    output_dir = tmp_path / "negative"
    monkeypatch.setattr(benchmark, "run_goal007", lambda: negative)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scripts/run_goal007.py", "--output-dir", str(output_dir)],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal007.py", run_name="__main__")

    assert raised.value.code == 0
    assert "joint_recovery_imprecise" in capsys.readouterr().out
    assert {
        path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file()
    } == _expected_files()

    completed = subprocess.run(
        [sys.executable, "scripts/run_goal007.py", "--bank-size", "4"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    assert "unrecognized arguments" in completed.stderr
