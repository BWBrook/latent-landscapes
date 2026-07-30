from __future__ import annotations

import csv
import json
import runpy
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from latent_landscapes.goal011 import artifacts, benchmark


def _expected_files() -> set[str]:
    return {
        "config.json",
        "seed_manifest.csv",
        "observation_signal_summary.csv",
        "calibration_results.csv",
        "validation_results.csv",
        "bank_summary.csv",
        "predictive_summary.csv",
        "domain_comparison.csv",
        "representative_profile.csv",
        "summary.json",
        "verification.json",
        "review.md",
        "visuals/joint_profile_surface.svg",
        "visuals/recovery_calibration.svg",
        "visuals/domain_and_bank_comparison.svg",
    }


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle))


@pytest.fixture(scope="module")
def small_result() -> benchmark.Goal011Result:
    return benchmark.run_goal011(
        benchmark.Goal011Config(
            master_seed=119,
            bank_size=2,
            calibration_replicates=2,
            validation_replicates=2,
            calibration_rank_one_based=2,
            rhos=(0.5, 1.0, 2.0),
            etas=tuple(index / 4 for index in range(11)),
        )
    )


def test_exact_deterministic_15_file_bundle_reconciles(
    tmp_path: Path,
    small_result: benchmark.Goal011Result,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    written = artifacts.write_review_bundle(small_result, first)
    artifacts.write_review_bundle(small_result, second)

    observed = {path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()}
    assert observed == _expected_files()
    assert len(written) == 15
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
    domains = _read_csv(first / "domain_comparison.csv")
    summary = json.loads((first / "summary.json").read_text(encoding="utf-8"))
    verification = json.loads((first / "verification.json").read_text(encoding="utf-8"))
    review = (first / "review.md").read_text(encoding="utf-8").lower()

    assert config["known_detection_probability"] == 0.65
    assert config["false_positive_probability"] == 0.0
    assert config["replicate_visits_retained"] is True
    assert config["records_per_dataset"] == 1920
    assert config["training_records_per_dataset"] == 1440
    assert config["holdout_records_per_dataset"] == 480
    assert config["candidate_etas"][-2:] == [2.25, 2.5]
    assert len(seeds) == 2 + 2 * 2 + 2 * 2
    assert len(calibration) == len(validation) == 2 * 3
    assert len(domains) == 3
    assert summary["outcome"] == small_result.outcome
    assert summary["old_domain_projection_is_gating"] is False
    assert verification["expected_artifact_file_count"] == 15
    assert verification["observed_artifact_file_count"] == 15
    assert all(verification["invariants"].values())
    assert "known p = 0.65" in review
    assert "not a full joint spatial likelihood" in review
    assert "historical" in review
    assert "not a strict causal" in review

    for filename in (
        "joint_profile_surface.svg",
        "recovery_calibration.svg",
        "domain_and_bank_comparison.svg",
    ):
        svg = (first / "visuals" / filename).read_text(encoding="utf-8")
        assert svg.lstrip().startswith("<?xml")
        assert "<svg" in svg
        assert "dc:date" not in svg


def test_writer_rejects_blocked_result_and_artifact_destination_is_ignored(
    tmp_path: Path,
    small_result: benchmark.Goal011Result,
) -> None:
    with pytest.raises(ValueError, match="implementation-blocked"):
        artifacts.write_review_bundle(
            replace(small_result, outcome="implementation_blocked"),
            tmp_path / "blocked",
        )
    assert not (tmp_path / "blocked").exists()
    assert (
        subprocess.run(
            [
                "git",
                "check-ignore",
                "-q",
                "artifacts/goal011_joint_known_imperfect_detection",
            ],
            check=False,
        ).returncode
        == 0
    )


def test_reduced_cli_writes_completed_negative_bundle(
    tmp_path: Path,
    small_result: benchmark.Goal011Result,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    negative = replace(
        small_result,
        outcome="joint_imperfect_detection_recovery_imprecise",
    )
    output = tmp_path / "cli"
    monkeypatch.setattr(benchmark, "run_goal011", lambda config: negative)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scripts/run_goal011.py",
            "--output-dir",
            str(output),
            "--reduced-smoke",
        ],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal011.py", run_name="__main__")

    assert raised.value.code == 0
    assert "joint_imperfect_detection_recovery_imprecise" in capsys.readouterr().out
    assert {
        path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()
    } == _expected_files()

    completed = subprocess.run(
        [sys.executable, "scripts/run_goal011.py", "--detection-probability", "0.8"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    assert "unrecognized arguments" in completed.stderr
