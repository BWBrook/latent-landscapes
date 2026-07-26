from __future__ import annotations

import csv
import importlib
import json
import runpy
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest


def load_goal002(name: str) -> Any:
    return importlib.import_module(f"latent_landscapes.goal002.{name}")


def expected_relative_files() -> set[str]:
    return {
        "seed_manifest.csv",
        "replicate_results.csv",
        "calibration_summary.csv",
        "predictive_summary.csv",
        "summary.json",
        "verification.json",
        "review.md",
        "visuals/coverage_support.svg",
        "visuals/mle_recovery.svg",
        "visuals/predictive_scores.svg",
    }


def read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle))


@pytest.fixture(scope="module")
def small_result() -> Any:
    benchmark = load_goal002("benchmark")
    return benchmark.run_goal002(
        benchmark.Goal002Config(
            calibration_replicates=3,
            validation_replicates=3,
            calibration_rank_one_based=3,
        )
    )


@pytest.mark.parametrize(
    (
        "invariants",
        "topology_count",
        "coverage",
        "brier",
        "expected",
    ),
    [
        (
            {"ok": False},
            100,
            (0.94, 0.96),
            (-0.2, -0.1),
            "implementation_blocked",
        ),
        (
            {"ok": True},
            94,
            (0.94, 0.96),
            (-0.2, -0.1),
            "design_limited",
        ),
        (
            {"ok": True},
            95,
            (0.90, 0.94),
            (-0.2, -0.1),
            "calibration_not_ready",
        ),
        (
            {"ok": True},
            95,
            (0.94, 0.96),
            (-0.1, 0.0),
            "mechanism_inconclusive",
        ),
        (
            {"ok": True},
            95,
            (0.94, 0.96),
            (-0.2, -0.01),
            "advance_stochastic_spread",
        ),
    ],
)
def test_decision_classes_follow_frozen_precedence(
    invariants: dict[str, bool],
    topology_count: int,
    coverage: tuple[float, float],
    brier: tuple[float, float],
    expected: str,
) -> None:
    benchmark = load_goal002("benchmark")
    interval = load_goal002("calibration").EstimateInterval

    outcome = benchmark.classify_outcome(
        invariants=invariants,
        topology_success_count=topology_count,
        validation_count=100,
        calibrated_coverage=interval(0.95, *coverage),
        paired_brier_interval=interval(-0.1, *brier),
    )

    assert outcome == expected


def test_exact_review_bundle_contract_and_scientific_content(
    tmp_path: Path,
    small_result: Any,
) -> None:
    artifacts = load_goal002("artifacts")
    output_dir = tmp_path / "bundle"

    written = artifacts.write_review_bundle(small_result, output_dir)

    relative_files = {
        path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file()
    }
    assert relative_files == expected_relative_files()
    assert {path.relative_to(output_dir).as_posix() for path in written} == relative_files
    assert len(written) == 10
    for path in output_dir.rglob("*"):
        if path.is_file():
            contents = path.read_bytes()
            assert b"/Users/" not in contents
            assert b"/tmp/" not in contents

    seeds = read_csv(output_dir / "seed_manifest.csv")
    replicates = read_csv(output_dir / "replicate_results.csv")
    calibration_summary = read_csv(output_dir / "calibration_summary.csv")
    predictive_summary = read_csv(output_dir / "predictive_summary.csv")
    summary_text = (output_dir / "summary.json").read_text(encoding="utf-8")
    summary = json.loads(summary_text)
    verification = json.loads((output_dir / "verification.json").read_text(encoding="utf-8"))
    review = (output_dir / "review.md").read_text(encoding="utf-8")

    assert len(seeds) == 6
    assert [row["phase"] for row in seeds] == ["calibration"] * 3 + ["validation"] * 3
    assert {"entropy", "spawn_key", "pool_size", "state_words"} <= set(seeds[0])
    assert len(replicates) == 6
    assert [row["phase"] for row in replicates] == [
        "calibration",
        "calibration",
        "calibration",
        "validation",
        "validation",
        "validation",
    ]
    assert all(row["neutral_log_score"] == "" for row in replicates[:3])
    assert all(row["neutral_log_score"] != "" for row in replicates[3:])
    assert all(row["mle_set"] for row in replicates[3:])
    assert len(calibration_summary) == 1
    assert calibration_summary[0]["rank_one_based"] == "3"
    assert calibration_summary[0]["rank_zero_based"] == "2"
    assert len(predictive_summary) == 1
    assert predictive_summary[0]["validation_replicates"] == "3"
    assert summary["outcome"] == small_result.outcome
    assert summary["calibration"]["cutoff"]["rank_one_based"] == 3
    assert summary["validation"]["neutral_baseline"]["full_support"] is True
    assert summary["validation"]["paired_brier"]["habitat_uses_worst_mle_partition"] is True
    assert summary["validation"]["hard_front"]["role"] == "diagnostic only"
    assert verification["expected_artifact_file_count"] == 10
    assert verification["observed_artifact_file_count"] == 10
    assert all(verification["invariants"].values())
    assert ": -Infinity" not in summary_text
    assert ": Infinity" not in summary_text
    assert "NaN" not in summary_text
    assert "# Goal 002 Detection-Noise Calibration Review" in review
    assert "## Observation" in review
    assert "## Inference" in review
    assert "## Assumptions" in review
    assert "## Limitations" in review
    assert "Monte Carlo uncertainty" in review
    assert "inferential uncertainty" in review
    assert "training records only" in review
    assert "Jeffreys-smoothed" in review
    assert "full support" in review
    assert "geometry-only hard-front comparator" in review
    assert "diagnostic" in review

    figure_labels = {
        "coverage_support.svg": ("Validation truth coverage", "Wilson"),
        "mle_recovery.svg": ("MLE-set recovery", "rho = 1"),
        "predictive_scores.svg": ("Paired predictive scores", "Brier"),
    }
    for filename, labels in figure_labels.items():
        svg = (output_dir / "visuals" / filename).read_text(encoding="utf-8")
        assert svg.lstrip().startswith("<?xml")
        assert "<svg" in svg
        assert len(svg) > 10_000
        assert "dc:date" not in svg
        assert "/Users/" not in svg
        assert all(label in svg for label in labels)


def test_small_review_bundles_are_byte_identical(
    tmp_path: Path,
    small_result: Any,
) -> None:
    artifacts = load_goal002("artifacts")
    first = tmp_path / "first"
    second = tmp_path / "second"

    artifacts.write_review_bundle(small_result, first)
    artifacts.write_review_bundle(small_result, second)

    for relative_path in sorted(expected_relative_files()):
        assert (first / relative_path).read_bytes() == (second / relative_path).read_bytes()


def test_cli_writes_negative_scientific_result_and_exits_zero(
    tmp_path: Path,
    small_result: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    benchmark = load_goal002("benchmark")
    result = replace(small_result, outcome="mechanism_inconclusive")
    output_dir = tmp_path / "negative"
    monkeypatch.setattr(benchmark, "run_goal002", lambda: result)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scripts/run_goal002.py", "--output-dir", str(output_dir)],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal002.py", run_name="__main__")

    captured = capsys.readouterr()
    assert raised.value.code == 0
    assert "mechanism_inconclusive" in captured.out
    assert "Wrote 10 files" in captured.out
    assert captured.err == ""
    assert {
        path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file()
    } == expected_relative_files()


def test_cli_exits_nonzero_without_bundle_only_for_implementation_blocked(
    tmp_path: Path,
    small_result: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    benchmark = load_goal002("benchmark")
    result = replace(
        small_result,
        invariants={**small_result.invariants, "forced_failure": False},
        outcome="implementation_blocked",
    )
    output_dir = tmp_path / "blocked"
    monkeypatch.setattr(benchmark, "run_goal002", lambda: result)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scripts/run_goal002.py", "--output-dir", str(output_dir)],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal002.py", run_name="__main__")

    captured = capsys.readouterr()
    assert raised.value.code != 0
    assert captured.out == ""
    assert "implementation_blocked" in captured.err
    assert "review bundle was not written" in captured.err
    assert not output_dir.exists()
