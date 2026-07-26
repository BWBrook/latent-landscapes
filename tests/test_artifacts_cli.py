from __future__ import annotations

import csv
import importlib
import json
import runpy
import subprocess
import sys
from dataclasses import replace
from math import isfinite
from pathlib import Path
from typing import Any

import pytest


def load_module(name: str) -> Any:
    return importlib.import_module(f"latent_landscapes.goal001.{name}")


def read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle))


def expected_relative_files() -> set[str]:
    return {
        "design.csv",
        "observations.csv",
        "likelihood_profile.csv",
        "holdout_predictions.csv",
        "summary.json",
        "review.md",
        "visuals/landscape_design.svg",
        "visuals/spread_observations.svg",
        "visuals/likelihood_holdout.svg",
    }


def build_finite_neutral_result() -> Any:
    benchmark_module = load_module("benchmark")
    likelihood_module = load_module("likelihood")
    observations_module = load_module("observations")
    canonical = benchmark_module.build_benchmark()
    training = tuple(record for record in canonical.observations if record.split == "training")
    holdout = tuple(record for record in canonical.observations if record.split == "holdout")
    neutral_distances = dict(canonical.habitat_distances)
    neutral_training = likelihood_module.profile_likelihood(
        model="neutral",
        scope="training",
        distances=neutral_distances,
        records=training,
        detection_probability=observations_module.DETECTION_PROBABILITY,
    )
    neutral_holdout = likelihood_module.evaluate_holdout_mle(
        model="neutral",
        training_profile=neutral_training,
        distances=neutral_distances,
        records=holdout,
        detection_probability=observations_module.DETECTION_PROBABILITY,
    )
    return replace(
        canonical,
        neutral_distances=neutral_distances,
        neutral_training=neutral_training,
        neutral_holdout=neutral_holdout,
        comparison="inconclusive",
        outcome="rate_recoverable_mechanism_inconclusive",
    )


def test_exact_review_bundle_contract_and_scientific_summary(tmp_path: Path) -> None:
    benchmark_module = load_module("benchmark")
    artifacts_module = load_module("artifacts")
    result = benchmark_module.build_benchmark()
    output_dir = tmp_path / "bundle"

    written = artifacts_module.write_review_bundle(result, output_dir)

    relative_files = {
        path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file()
    }
    assert relative_files == expected_relative_files()
    assert {path.relative_to(output_dir).as_posix() for path in written} == relative_files
    for path in output_dir.rglob("*"):
        if path.is_file():
            contents = path.read_bytes()
            assert b"/Users/" not in contents
            assert b"/tmp/" not in contents

    design_rows = read_csv(output_dir / "design.csv")
    observation_rows = read_csv(output_dir / "observations.csv")
    likelihood_rows = read_csv(output_dir / "likelihood_profile.csv")
    holdout_rows = read_csv(output_dir / "holdout_predictions.csv")
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    review = (output_dir / "review.md").read_text(encoding="utf-8")

    assert len(design_rows) == 160
    assert len(observation_rows) == 1920
    assert not {
        "true_arrival",
        "arrival",
        "occupied",
        "latent_occupancy",
        "source_zone",
    } & set(observation_rows[0])
    assert len(likelihood_rows) == 471 + 481 + 632
    assert {(row["model"], row["scope"]) for row in likelihood_rows} == {
        ("habitat", "training"),
        ("neutral", "training"),
        ("habitat", "all"),
    }
    assert all(float(row["upper_rate"]) >= float(row["lower_rate"]) for row in likelihood_rows)
    assert len(holdout_rows) == 2
    assert {row["model"] for row in holdout_rows} == {"habitat", "neutral"}
    assert summary["outcome"] == "advance_goal002"
    assert summary["one_realization_only"] is True
    assert summary["ideal_process_identifiability"]["scope"] == (
        "algebraic and conditional on the exact full-landscape path-cost vector and model; "
        "distinct from practical observation identification"
    )
    assert summary["nominal_lr_support"]["calibrated_confidence_interval"] is False
    assert summary["nominal_lr_support"]["likelihood_shape"] == "discontinuous_stepwise"
    assert summary["nominal_lr_support"]["wilks_calibrated"] is False
    assert summary["nominal_lr_support"]["width_used_for_automatic_classification"] is False
    assert summary["nominal_lr_support"]["components"][0]["width"] == (0.0005727512720217209)
    assert summary["holdout_comparison"]["primary_metric"] == ("total Bernoulli log score")
    assert summary["holdout_comparison"]["neutral_comparator"] == (
        "geometry-only hard-front comparator"
    )
    assert summary["holdout_comparison"]["neutral"]["log_score_range"] == [
        "-Infinity",
        "-Infinity",
    ]
    zero_probability = summary["holdout_comparison"]["neutral"]["zero_probability_detections"]
    assert zero_probability["record_count"] == 4
    assert zero_probability["site_time_count"] == 3
    assert zero_probability["site_times"] == [
        {"detection_records": 1, "site_id": "cluster_22_site_1", "time": 50},
        {"detection_records": 2, "site_id": "cluster_22_site_3", "time": 50},
        {"detection_records": 1, "site_id": "cluster_26_site_1", "time": 90},
    ]
    assert "every neutral training-MLE partition" in zero_probability["observation"]
    assert "-Infinity" in zero_probability["inference"]
    assert "structural support violation" in zero_probability["inference"]
    assert "not an optimizer failure" in zero_probability["inference"]
    assert "not a calibrated magnitude of model superiority" in zero_probability["inference"]
    assert "known zero false positives" in zero_probability["assumption"]
    assert "full-support predictive neutral baseline" in zero_probability["limitation"]
    assert "finite corroborating evidence" in review
    assert "geometry-only hard-front comparator" in review
    assert "full-support neutral" in review
    assert any(
        "future full-support predictive neutral baseline" in item for item in summary["limitations"]
    )
    assert "advance_goal002" in review
    assert "0.0005727512720217209" in review
    assert "not a calibrated confidence interval" in review
    assert "algebraic and conditional on the exact full-landscape path-cost vector" in review
    assert "distinct from practical observation-based identification" in review
    assert "discontinuous stepwise likelihood" in review
    assert "not a Wilks-calibrated interval" in review
    assert "**Observation:** Four held-out detection records at three site-times" in review
    assert "`cluster_22_site_1` at `t=50` (one detection record)" in review
    assert "`cluster_22_site_3` at `t=50` (two replicate detection records)" in review
    assert "`cluster_26_site_1` at `t=90` (one detection record)" in review
    assert "**Inference:** Under known zero false positives" in review
    assert "**Assumption:** The false-positive probability is known to be zero" in review
    assert "**Limitation:** Allowing false positives or softened occupancy" in review
    assert "single canonical realization" in review
    assert "sorted cluster IDs" in review
    assert "permuted" in review

    for filename in (
        "landscape_design.svg",
        "spread_observations.svg",
        "likelihood_holdout.svg",
    ):
        svg = (output_dir / "visuals" / filename).read_text(encoding="utf-8")
        assert svg.lstrip().startswith("<?xml")
        assert "<svg" in svg
        assert len(svg) > 20_000
        assert "dc:date" not in svg
        assert "/Users/" not in svg

    spread_svg = (output_dir / "visuals" / "spread_observations.svg").read_text(encoding="utf-8")
    likelihood_svg = (output_dir / "visuals" / "likelihood_holdout.svg").read_text(encoding="utf-8")
    assert "Detection count encoded by marker size" in spread_svg
    assert "Display window rho=0.94 to 1.25; full domain in CSV" in likelihood_svg
    assert "Comparator zero-probability: 4 records / 3 site-times" in likelihood_svg
    assert "Hard zero-FP comparator support violation; details in review.md" in likelihood_svg
    assert "LR support: descriptive, non-Wilks" in likelihood_svg
    assert "cluster_22_site_1" not in likelihood_svg


def test_review_bundle_is_byte_identical_across_repeated_runs(tmp_path: Path) -> None:
    benchmark_module = load_module("benchmark")
    artifacts_module = load_module("artifacts")
    first = tmp_path / "first"
    second = tmp_path / "second"

    artifacts_module.write_review_bundle(benchmark_module.build_benchmark(), first)
    artifacts_module.write_review_bundle(benchmark_module.build_benchmark(), second)

    assert {
        path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()
    } == expected_relative_files()
    assert {
        path.relative_to(second).as_posix() for path in second.rglob("*") if path.is_file()
    } == expected_relative_files()
    for relative_path in sorted(expected_relative_files()):
        assert (first / relative_path).read_bytes() == (second / relative_path).read_bytes()


def test_cli_accepts_output_dir_and_writes_exact_bundle(tmp_path: Path) -> None:
    output_dir = tmp_path / "cli-bundle"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_goal001.py",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Goal 001 deterministic spread benchmark complete" in completed.stdout
    assert "Outcome: advance_goal002" in completed.stdout
    assert "Wrote 9 files" in completed.stdout
    assert {
        path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file()
    } == expected_relative_files()


def test_cli_exits_nonzero_without_writing_for_implementation_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    benchmark_module = load_module("benchmark")
    blocked = replace(benchmark_module.build_benchmark(), outcome="implementation_blocked")
    output_dir = tmp_path / "blocked-bundle"
    monkeypatch.setattr(benchmark_module, "build_benchmark", lambda: blocked)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scripts/run_goal001.py", "--output-dir", str(output_dir)],
    )

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("scripts/run_goal001.py", run_name="__main__")

    captured = capsys.readouterr()
    assert raised.value.code != 0
    assert captured.out == ""
    assert "implementation_blocked" in captured.err
    assert "review bundle was not written" in captured.err
    assert not output_dir.exists()


@pytest.mark.parametrize(
    ("outcome", "comparison", "expected_decision"),
    [
        (
            "implementation_blocked",
            "habitat_robustly_better",
            "No scientific outcome is reported",
        ),
        ("recovery_failure", "habitat_robustly_better", "excludes `rho = 1`"),
        (
            "design_limited",
            "habitat_robustly_better",
            "is disconnected or touches the frozen rate-domain boundary",
        ),
        (
            "mechanism_not_supported",
            "neutral_robustly_better",
            "geometry-only hard-front comparator robustly beats habitat spread",
        ),
        (
            "rate_recoverable_mechanism_inconclusive",
            "inconclusive",
            "neither model robustly wins",
        ),
    ],
)
def test_negative_review_decision_matches_outcome_and_comparison(
    outcome: str, comparison: str, expected_decision: str
) -> None:
    benchmark_module = load_module("benchmark")
    artifacts_module = load_module("artifacts")
    result = replace(
        benchmark_module.build_benchmark(),
        outcome=outcome,
        comparison=comparison,
    )

    review = artifacts_module._render_review(result)

    assert expected_decision in review
    assert (
        "habitat spread robustly beats the geometry-only hard-front comparator on the "
        "frozen holdout" not in review
    )


def test_finite_negative_result_reports_actual_neutral_evidence(tmp_path: Path) -> None:
    artifacts_module = load_module("artifacts")
    result = build_finite_neutral_result()
    output_dir = tmp_path / "finite-negative"

    artifacts_module.write_review_bundle(result, output_dir)

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    review = (output_dir / "review.md").read_text(encoding="utf-8")
    svg = (output_dir / "visuals" / "likelihood_holdout.svg").read_text(encoding="utf-8")
    zero_probability = summary["holdout_comparison"]["neutral"]["zero_probability_detections"]
    neutral_scores = result.neutral_holdout.log_score_range

    assert isfinite(neutral_scores.minimum)
    assert isfinite(neutral_scores.maximum)
    assert zero_probability["record_count"] == 0
    assert zero_probability["site_time_count"] == 0
    assert zero_probability["site_times"] == []
    assert zero_probability["observation"] == (
        "No held-out detection record is assigned zero probability by every neutral "
        "training-MLE partition."
    )
    assert "finite across all neutral training-MLE partitions" in zero_probability["inference"]
    assert "-Infinity" not in json.dumps(zero_probability)
    assert "**Observation:** No held-out detection record" in review
    assert "finite across all neutral training-MLE partitions" in review
    assert "Four held-out detection records" not in review
    assert "cluster_22_site_1" not in review
    assert "-Infinity" not in review
    assert "Decision: mechanism inconclusive" in svg
    assert "Comparator zero-probability: none" in svg
    assert "Comparator scores finite; details in review.md" in svg
    assert "LR support: descriptive, non-Wilks" in svg
    assert "4 records / 3 site-times" not in svg
    assert "cluster_22_site_1" not in svg
    assert "Decision: habitat robustly better" not in svg
