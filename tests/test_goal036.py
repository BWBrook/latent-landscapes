from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

from latent_landscapes.goal036 import (
    EXPECTED_FILES,
    classify_background_risk,
    classify_cell,
    classify_effect_transition,
    cumulative_risk_from_daily_hazard,
    daily_hazard_from_cumulative_risk,
    run_goal036,
    smoke_config,
    write_review_bundle,
)


def _write_validation(path: Path, *, truth_id: str | None = None) -> None:
    fieldnames = [
        "dataset_index",
        "observed_event_count",
        "training_event_count",
        "holdout_event_count",
    ]
    if truth_id is not None:
        fieldnames.insert(0, "truth_id")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index in range(1_000):
            total = 50 + index % 21
            training = total - 12
            row: dict[str, object] = {
                "dataset_index": index,
                "observed_event_count": total,
                "training_event_count": training,
                "holdout_event_count": 12,
            }
            if truth_id is not None:
                row["truth_id"] = truth_id
            writer.writerow(row)


def _write_anchors(root: Path) -> tuple[Path, Path]:
    goal027 = root / "goal027"
    goal028 = root / "goal028"
    goal027.mkdir()
    goal028.mkdir()
    row5 = {
        "evidence": "goal027_high_resolution",
        "calibration_replicates": 2000,
        "validation_replicates": 1000,
        "cutoff": 4.029414195600793,
        "coverage_count": 954,
        "coverage": 0.954,
        "coverage_lower": 0.9391877960583809,
        "coverage_upper": 0.9653375072367351,
        "connected_interior_count": 997,
        "null_exclusion_count": 1000,
        "median_absolute_log_error": 0.11653381625595151,
        "median_log_support_width": 0.6632942174102642,
        "score_advantage": 0.06883405396926956,
        "score_advantage_lower": 0.06536394815978021,
        "score_advantage_upper": 0.07230415977875891,
    }
    (goal027 / "summary.json").write_text(
        json.dumps(
            {
                "goal": "027-known-arrival-support-calibration-confirmation",
                "run_mode": "production",
                "outcome": "support_calibration_confirmed",
                "config": {
                    "master_seed": 20260811027,
                    "calibration_replicates": 2000,
                    "validation_replicates": 1000,
                    "calibration_rank_one_based": 1901,
                },
                "coverage_comparison": [{"evidence": "published_goal026"}, row5],
            }
        ),
        encoding="utf-8",
    )
    _write_validation(goal027 / "validation_results.csv")

    row3 = {
        "truth_id": "threefold_effect",
        "hazard_ratio": 3.0,
        "evidence_source": "goal028_new_ensemble",
        "calibration_replicates": 2000,
        "validation_replicates": 1000,
        "cutoff": 4.0433616240632375,
        "coverage_count": 973,
        "coverage": 0.973,
        "coverage_lower": 0.9610012692469598,
        "coverage_upper": 0.9813786172257051,
        "connected_interior_count": 986,
        "null_exclusion_count": 986,
        "median_absolute_log_error": 0.1431008436406733,
        "median_log_support_width": 0.8303483020734302,
        "score_advantage": 0.024800897110231115,
        "score_advantage_lower": 0.022659445273521074,
        "score_advantage_upper": 0.026942348946941155,
        "recovered": False,
        "failed_gates": "calibrated_coverage;support_precision",
    }
    (goal028 / "summary.json").write_text(
        json.dumps(
            {
                "goal": "028-known-arrival-prey-effect-strength-transition",
                "run_mode": "production",
                "outcome": "prey_effect_transition_between_threefold_and_fivefold",
                "truth_summaries": [row3],
            }
        ),
        encoding="utf-8",
    )
    _write_validation(
        goal028 / "validation_results.csv",
        truth_id="threefold_effect",
    )
    return goal027, goal028


def test_background_risk_and_daily_hazard_round_trip() -> None:
    for risk in (0.05, 1.0 - math.exp(-0.002 * 60.0), 0.20):
        hazard = daily_hazard_from_cumulative_risk(risk)
        assert cumulative_risk_from_daily_hazard(hazard) == pytest.approx(risk)
    assert daily_hazard_from_cumulative_risk(0.05) == pytest.approx(-math.log(0.95) / 60.0)


def test_decision_layers_separate_detection_recovery_and_risk_robustness() -> None:
    assert (
        classify_cell(
            invariants={"valid": True},
            validation_count=1_000,
            null_exclusion_count=986,
            score_advantage_lower=0.02,
            failed_gates=("support_precision",),
        )
        == "detected_but_not_fully_recovered"
    )
    assert (
        classify_effect_transition(
            threefold_status="detected_but_not_fully_recovered",
            fourfold_status="fully_recovered",
            fivefold_status="fully_recovered",
        )
        == "strict_transition_between_threefold_and_fourfold"
    )
    assert (
        classify_effect_transition(
            threefold_status="detected_but_not_fully_recovered",
            fourfold_status="not_reliably_detected",
            fivefold_status="fully_recovered",
        )
        == "nonmonotonic_detection_requires_human_review"
    )
    assert (
        classify_background_risk("fully_recovered", "fully_recovered")
        == "fivefold_recovery_robust_across_5_to_20_percent_background_risk"
    )


def test_anchor_reconciliation_fails_closed(tmp_path: Path) -> None:
    goal027, goal028 = _write_anchors(tmp_path)
    result = run_goal036(goal027, goal028, smoke_config())
    assert result.threefold_anchor.status == "detected_but_not_fully_recovered"
    assert result.fivefold_anchor.status == "fully_recovered"

    payload = json.loads((goal028 / "summary.json").read_text(encoding="utf-8"))
    payload["truth_summaries"][0]["coverage_count"] = 972
    (goal028 / "summary.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="threefold evidence changed"):
        run_goal036(goal027, goal028, smoke_config())


def test_reduced_smoke_writes_exact_bundle_and_reconciles_event_accounting(
    tmp_path: Path,
) -> None:
    goal027, goal028 = _write_anchors(tmp_path)
    output = tmp_path / "output"
    result = run_goal036(goal027, goal028, smoke_config())
    written = write_review_bundle(result, output)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)

    with (output / "validation_results.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 24
    assert all(int(row["observed_event_count"]) + int(row["censored_count"]) == 160 for row in rows)
    assert all(
        int(row["pre_arrival_observed_event_count"]) + int(row["post_arrival_observed_event_count"])
        == int(row["observed_event_count"])
        for row in rows
    )
    assert "implementation check only" in (output / "review.md").read_text(encoding="utf-8")
