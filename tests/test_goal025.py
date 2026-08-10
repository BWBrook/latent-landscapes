from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from latent_landscapes.goal002.calibration import wilson_interval
from latent_landscapes.goal023 import TruthSummary
from latent_landscapes.goal025 import (
    EXPECTED_FILES,
    classify_spread_detection_transition,
    load_goal023_spread_anchors,
    run_goal025,
    smoke_config,
    write_review_bundle,
)


def _anchor_summaries() -> tuple[TruthSummary, TruthSummary]:
    slower = TruthSummary(
        "slower_spread",
        0.7578582832551991,
        1.0,
        0.65,
        65.8768407265286,
        232,
        0.928,
        0.8890714648901645,
        0.953974430741735,
        250,
        0,
        0.027725887222397914,
        0.125,
        0.020000000000000018,
        0.38816242111356936,
        0.75,
        0.26,
        "three_parameter_recovery_imprecise",
    )
    central = TruthSummary(
        "central",
        1.0,
        1.0,
        0.65,
        59.15805000796831,
        234,
        0.936,
        0.8985785081170682,
        0.9602252547229041,
        250,
        0,
        0.027725887222397844,
        0.125,
        0.020000000000000018,
        0.3327106466687738,
        0.625,
        0.20000000000000007,
        "advance_to_cross_truth_three_parameter_benchmark",
    )
    return slower, central


def _write_anchor_evidence(path: Path) -> None:
    path.mkdir()
    rows = _anchor_summaries()
    payload = [asdict(row) for row in rows]
    with (path / "truth_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]))
        writer.writeheader()
        writer.writerows(payload)
    (path / "summary.json").write_text(
        json.dumps(
            {
                "run_mode": "production",
                "outcome": "one_axis_identifiability_limit_found",
                "central_reconciled": True,
                "invariants": {"valid": True},
                "truth_summaries": payload,
            }
        ),
        encoding="utf-8",
    )


def test_goal023_spread_anchors_reconcile(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "goal023"
    _write_anchor_evidence(evidence_dir)

    evidence = load_goal023_spread_anchors(evidence_dir)

    assert evidence.slower_spread.truth_rho == 0.7578582832551991
    assert evidence.slower_spread.median_probability_width == 0.26
    assert evidence.central.truth_rho == 1.0
    assert evidence.central.median_probability_width == 0.20000000000000007


def test_spread_detection_decision_brackets_midpoint() -> None:
    calibrated = wilson_interval(234, 250)

    def decision(probability_width: float, connected: int = 250) -> str:
        return classify_spread_detection_transition(
            invariants={"valid": True},
            coverage=calibrated,
            connected_interior_count=connected,
            validation_count=250,
            median_log_rho_error=0.03,
            median_probability_error=0.02,
            median_log_rho_width=0.35,
            median_probability_width=probability_width,
        )

    assert decision(0.20000000000000007) == "spread_detection_transition_between_0_758_and_0_871"
    assert decision(0.22) == "spread_detection_transition_between_0_871_and_1_0"
    assert decision(0.20, connected=237) == "spread_detection_transition_unresolved"


def test_goal025_smoke_writes_compact_review_surface(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "goal023"
    output_dir = tmp_path / "goal025"
    _write_anchor_evidence(evidence_dir)

    result = run_goal025(evidence_dir, smoke_config())
    written = write_review_bundle(result, output_dir)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["scientific_interpretation"] == "non_scientific_smoke"
    assert "implementation check only" in (output_dir / "review.md").read_text(encoding="utf-8")
