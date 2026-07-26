from __future__ import annotations

import csv
import json
import runpy
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from latent_landscapes.goal004 import artifacts, benchmark


def expected_relative_files() -> set[str]:
    return {
        "config.json",
        "seed_manifest.csv",
        "calibration_results.csv",
        "validation_results.csv",
        "bank_stability_summary.csv",
        "predictive_summary.csv",
        "representative_profile.csv",
        "summary.json",
        "verification.json",
        "review.md",
        "visuals/recovery_calibration.svg",
        "visuals/predictive_comparison.svg",
    }


def read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle))


@pytest.fixture(scope="module")
def small_result() -> benchmark.Goal004Result:
    return benchmark.run_goal004(
        benchmark.Goal004Config(
            master_seed=81,
            bank_size=6,
            calibration_replicates=3,
            validation_replicates=2,
            calibration_rank_one_based=3,
            rates=(0.5, 0.75, 1.0, 1.5, 2.0),
        )
    )


def test_exact_review_bundle_contract_and_reconciliation(
    tmp_path: Path,
    small_result: benchmark.Goal004Result,
) -> None:
    output_dir = tmp_path / "bundle"

    written = artifacts.write_review_bundle(small_result, output_dir)

    relative = {
        path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file()
    }
    assert relative == expected_relative_files()
    assert {path.relative_to(output_dir).as_posix() for path in written} == relative
    assert len(written) == 12
    for path in output_dir.rglob("*"):
        if path.is_file():
            contents = path.read_bytes()
            assert b"/Users/" not in contents
            assert b"/tmp/" not in contents
            assert b"NaN" not in contents
            assert b"Infinity" not in contents

    config = json.loads((output_dir / "config.json").read_text(encoding="utf-8"))
    seeds = read_csv(output_dir / "seed_manifest.csv")
    calibration = read_csv(output_dir / "calibration_results.csv")
    validation = read_csv(output_dir / "validation_results.csv")
    stability = read_csv(output_dir / "bank_stability_summary.csv")
    predictive = read_csv(output_dir / "predictive_summary.csv")
    representative = read_csv(output_dir / "representative_profile.csv")
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    verification = json.loads((output_dir / "verification.json").read_text(encoding="utf-8"))
    review = (output_dir / "review.md").read_text(encoding="utf-8")

    assert config["method"] == "site-history simulated composite likelihood"
    assert config["is_full_joint_spatial_likelihood"] is False
    assert config["survey_times"] == [10, 20, 30, 40, 50, 60]
    assert config["detection_probability"] == 0.65
    assert config["false_positive_probability"] == 0.0
    assert config["source_identity"] == benchmark.SOURCE_IDENTITY
    assert len(seeds) == 6 + 2 * 3 + 2 * 2
    assert {"phase", "index", "stream_role", "entropy", "spawn_key", "state_words"} <= set(seeds[0])
    assert len(calibration) == 3 * 3
    assert len(validation) == 2 * 3
    assert len(stability) == 3
    assert len(predictive) == 3
    assert len(representative) == 5 * 3
    for rows in (seeds, calibration, validation, stability, predictive, representative):
        assert {row["between_site_process_dependence"] for row in rows} == {"omitted"}
    assert {row["dataset_index"] for row in representative} == {"0"}
    assert {row["bank_variant"] for row in representative} == {
        "full",
        "first_half",
        "second_half",
    }
    assert summary["outcome"] == small_result.outcome
    assert summary["calibration_scope"] == "rho = 1 under the frozen design only"
    assert summary["between_site_process_dependence"] == "omitted"
    assert verification["expected_artifact_file_count"] == 12
    assert verification["observed_artifact_file_count"] == 12
    assert all(verification["invariants"].values())
    assert "# Goal 004 Stochastic One-Rate Recovery And Calibration Review" in review
    assert "## Observations" in review
    assert "## Inference" in review
    assert "## Assumptions" in review
    assert "## Uncertainty" in review
    assert "## Limitations" in review
    assert "not a full joint spatial likelihood" in review
    assert "training records only" in review
    assert "rho = 1" in review

    labels = {
        "recovery_calibration.svg": (
            "Recovery and calibrated support",
            "site-history simulated composite likelihood",
            "rho = 1",
            "between-site process dependence omitted",
        ),
        "predictive_comparison.svg": (
            "Held-out predictive comparison",
            "Brier",
            "training-only fits",
            "between-site process dependence omitted",
        ),
    }
    for filename, expected_labels in labels.items():
        svg = (output_dir / "visuals" / filename).read_text(encoding="utf-8")
        assert svg.lstrip().startswith("<?xml")
        assert "<svg" in svg
        assert len(svg) > 8_000
        assert "dc:date" not in svg
        assert all(label in svg for label in expected_labels)


def test_artifact_reconciliation_does_not_publish_a_false_observed_count(
    tmp_path: Path,
    small_result: benchmark.Goal004Result,
) -> None:
    output_dir = tmp_path / "stale"
    output_dir.mkdir()
    (output_dir / "unexpected.txt").write_text("stale\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="artifact contract mismatch"):
        artifacts.write_review_bundle(small_result, output_dir)

    assert not (output_dir / "verification.json").exists()


def test_small_review_bundles_are_byte_identical(
    tmp_path: Path,
    small_result: benchmark.Goal004Result,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"

    artifacts.write_review_bundle(small_result, first)
    artifacts.write_review_bundle(small_result, second)

    for relative_path in sorted(expected_relative_files()):
        assert (first / relative_path).read_bytes() == (second / relative_path).read_bytes()


def test_review_bundle_is_idempotent_on_its_valid_target(
    tmp_path: Path,
    small_result: benchmark.Goal004Result,
) -> None:
    output_dir = tmp_path / "same-target"
    artifacts.write_review_bundle(small_result, output_dir)
    before = {
        relative_path: (output_dir / relative_path).read_bytes()
        for relative_path in expected_relative_files()
    }

    written = artifacts.write_review_bundle(small_result, output_dir)

    assert {path.relative_to(output_dir).as_posix() for path in written} == set(before)
    assert {
        relative_path: (output_dir / relative_path).read_bytes()
        for relative_path in expected_relative_files()
    } == before


def test_artifact_destinations_are_ignored() -> None:
    for path in (
        "artifacts/goal004_stochastic_one_rate_recovery",
        "artifacts/goal004_stochastic_one_rate_recovery_repeat",
    ):
        completed = subprocess.run(
            ["git", "check-ignore", "-q", path],
            check=False,
        )
        assert completed.returncode == 0


def test_cli_writes_completed_negative_scientific_class_and_exits_zero(
    tmp_path: Path,
    small_result: benchmark.Goal004Result,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = replace(small_result, outcome="likelihood_approximation_unstable")
    output_dir = tmp_path / "negative"
    monkeypatch.setattr(benchmark, "run_goal004", lambda: result)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scripts/run_goal004.py", "--output-dir", str(output_dir)],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal004.py", run_name="__main__")

    captured = capsys.readouterr()
    assert raised.value.code == 0
    assert "likelihood_approximation_unstable" in captured.out
    assert "Wrote 12 files" in captured.out
    assert captured.err == ""
    assert {
        path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file()
    } == expected_relative_files()


def test_cli_exits_nonzero_without_bundle_only_for_implementation_blocked(
    tmp_path: Path,
    small_result: benchmark.Goal004Result,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = replace(
        small_result,
        invariants={**small_result.invariants, "forced_failure": False},
        outcome="implementation_blocked",
    )
    output_dir = tmp_path / "blocked"
    monkeypatch.setattr(benchmark, "run_goal004", lambda: result)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scripts/run_goal004.py", "--output-dir", str(output_dir)],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal004.py", run_name="__main__")

    captured = capsys.readouterr()
    assert raised.value.code != 0
    assert captured.out == ""
    assert "implementation_blocked" in captured.err
    assert "review bundle was not written" in captured.err
    assert not output_dir.exists()


def test_cli_maps_artifact_writer_failure_to_implementation_blocked(
    tmp_path: Path,
    small_result: benchmark.Goal004Result,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_writer(*args: object, **kwargs: object) -> tuple[Path, ...]:
        raise RuntimeError("artifact contract mismatch")

    output_dir = tmp_path / "writer-failure"
    monkeypatch.setattr(benchmark, "run_goal004", lambda: small_result)
    monkeypatch.setattr(artifacts, "write_review_bundle", fail_writer)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scripts/run_goal004.py", "--output-dir", str(output_dir)],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal004.py", run_name="__main__")

    captured = capsys.readouterr()
    assert raised.value.code != 0
    assert captured.out == ""
    assert "implementation_blocked" in captured.err
    assert "artifact contract mismatch" in captured.err
