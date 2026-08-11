from __future__ import annotations

import json
from pathlib import Path

import pytest

from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal026 import RecoverySummary
from latent_landscapes.goal027 import (
    EXPECTED_FILES,
    classify_confirmation,
    load_goal026_anchor,
    run_goal027,
    smoke_config,
    write_review_bundle,
)


def _write_anchor(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    payload = {
        "goal": "026-known-arrival-prey-persistence-positive-control",
        "run_mode": "production",
        "outcome": "known_arrival_prey_effect_not_recovered",
        "failed_gates": ["calibrated_coverage"],
        "calibration": {"cutoff": 3.5902465377401427},
        "validation": {
            "replicates": 250,
            "coverage_count": 230,
            "coverage": {
                "estimate": 0.92,
                "lower": 0.8796703567961583,
                "upper": 0.9476176716276683,
            },
            "connected_interior_count": 250,
            "null_exclusion_count": 250,
            "median_absolute_log_error": 0.1149312507814774,
            "median_log_support_width": 0.622195444587661,
            "heldout_log_score_advantage": {
                "estimate": 0.06921492712831596,
                "lower": 0.06219341234770491,
                "upper": 0.07623644190892702,
            },
        },
    }
    (path / "summary.json").write_text(json.dumps(payload), encoding="utf-8")


def _summary(coverage: EstimateInterval) -> RecoverySummary:
    return RecoverySummary(
        cutoff=3.8,
        coverage_count=950,
        coverage=coverage,
        connected_interior_count=1_000,
        null_exclusion_count=1_000,
        median_absolute_log_error=0.10,
        median_log_support_width=0.62,
        heldout_log_score_advantage=EstimateInterval(0.07, 0.06, 0.08),
    )


def test_goal026_anchor_reconciles_exactly(tmp_path: Path) -> None:
    _write_anchor(tmp_path)
    anchor = load_goal026_anchor(tmp_path)
    assert anchor.coverage_count == 230
    assert anchor.null_exclusion_count == 250

    payload = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    payload["validation"]["coverage_count"] = 231
    (tmp_path / "summary.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="evidence changed"):
        load_goal026_anchor(tmp_path)


def test_confirmation_decision_separates_persistent_undercoverage() -> None:
    assert (
        classify_confirmation(
            invariants={"valid": True},
            summary=_summary(EstimateInterval(0.95, 0.935, 0.962)),
            validation_count=1_000,
        )
        == "support_calibration_confirmed"
    )
    assert (
        classify_confirmation(
            invariants={"valid": True},
            summary=_summary(EstimateInterval(0.92, 0.902, 0.936)),
            validation_count=1_000,
        )
        == "persistent_support_undercoverage"
    )


def test_goal027_smoke_writes_exact_review_surface(tmp_path: Path) -> None:
    anchor_dir = tmp_path / "goal026"
    output_dir = tmp_path / "goal027"
    _write_anchor(anchor_dir)

    result = run_goal027(anchor_dir, smoke_config())
    written = write_review_bundle(result, output_dir)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    assert "implementation check only" in (output_dir / "review.md").read_text(encoding="utf-8")
