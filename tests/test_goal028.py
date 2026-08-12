from __future__ import annotations

import json
from pathlib import Path

import pytest

from latent_landscapes.goal028 import (
    EXPECTED_FILES,
    classify_transition,
    load_goal027_anchor,
    run_goal028,
    smoke_config,
    write_review_bundle,
)


def _write_anchor(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    accepted = {
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
    payload = {
        "goal": "027-known-arrival-support-calibration-confirmation",
        "run_mode": "production",
        "outcome": "support_calibration_confirmed",
        "coverage_comparison": [{"evidence": "published_goal026"}, accepted],
    }
    (path / "summary.json").write_text(json.dumps(payload), encoding="utf-8")


def test_goal027_anchor_reconciles_exactly(tmp_path: Path) -> None:
    _write_anchor(tmp_path)
    anchor = load_goal027_anchor(tmp_path)
    assert anchor.hazard_ratio == 5.0
    assert anchor.recovered
    assert anchor.coverage_count == 954

    payload = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    payload["coverage_comparison"][1]["coverage_count"] = 953
    (tmp_path / "summary.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="evidence changed"):
        load_goal027_anchor(tmp_path)


def test_transition_decision_brackets_monotonic_recovery() -> None:
    valid = {"valid": True}
    assert (
        classify_transition(
            invariants=valid,
            twofold_recovered=True,
            threefold_recovered=True,
        )
        == "prey_effect_transition_below_twofold"
    )
    assert (
        classify_transition(
            invariants=valid,
            twofold_recovered=False,
            threefold_recovered=True,
        )
        == "prey_effect_transition_between_twofold_and_threefold"
    )
    assert (
        classify_transition(
            invariants=valid,
            twofold_recovered=False,
            threefold_recovered=False,
        )
        == "prey_effect_transition_between_threefold_and_fivefold"
    )


def test_goal028_smoke_writes_exact_review_surface(tmp_path: Path) -> None:
    anchor_dir = tmp_path / "goal027"
    output_dir = tmp_path / "goal028"
    _write_anchor(anchor_dir)

    result = run_goal028(anchor_dir, smoke_config())
    written = write_review_bundle(result, output_dir)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    assert "implementation check only" in (output_dir / "review.md").read_text(encoding="utf-8")
