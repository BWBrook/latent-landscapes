from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from latent_landscapes.goal002.calibration import wilson_interval
from latent_landscapes.goal023 import TruthSummary
from latent_landscapes.goal024 import (
    EXPECTED_FILES,
    classify_transition,
    load_goal023_anchors,
    run_goal024,
    smoke_config,
    write_review_bundle,
)


def _anchor_summaries() -> tuple[TruthSummary, TruthSummary]:
    weak = TruthSummary(
        "weaker_resistance",
        1.0,
        0.5,
        0.65,
        65.54367270286775,
        235,
        0.94,
        0.9033771072831173,
        0.9633055891608914,
        166,
        84,
        0.027725887222397844,
        0.125,
        0.020000000000000018,
        0.27725887222397827,
        0.625,
        0.24,
        "three_parameter_support_design_limited",
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
    return weak, central


def _write_anchor_evidence(path: Path) -> None:
    path.mkdir()
    weak, central = _anchor_summaries()
    rows = (central, weak)
    with (path / "truth_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        payload = [asdict(row) for row in rows]
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


def test_goal023_anchor_evidence_reconciles(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "goal023"
    _write_anchor_evidence(evidence_dir)

    evidence = load_goal023_anchors(evidence_dir)

    assert evidence.weaker_resistance.truth_eta == 0.5
    assert evidence.weaker_resistance.connected_interior_count == 166
    assert evidence.central.truth_eta == 1.0
    assert evidence.central.connected_interior_count == 250


def test_transition_decision_uses_resistance_topology_gate() -> None:
    calibrated = wilson_interval(235, 250)

    assert (
        classify_transition(
            invariants={"valid": True},
            coverage=calibrated,
            connected_interior_count=238,
            validation_count=250,
        )
        == "resistance_transition_between_0_5_and_0_75"
    )
    assert (
        classify_transition(
            invariants={"valid": True},
            coverage=calibrated,
            connected_interior_count=237,
            validation_count=250,
        )
        == "resistance_transition_between_0_75_and_1_0"
    )
    assert (
        classify_transition(
            invariants={"valid": False},
            coverage=calibrated,
            connected_interior_count=250,
            validation_count=250,
        )
        == "resistance_transition_unresolved"
    )


def test_goal024_smoke_writes_compact_review_surface(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "goal023"
    output_dir = tmp_path / "goal024"
    _write_anchor_evidence(evidence_dir)

    result = run_goal024(evidence_dir, smoke_config())
    written = write_review_bundle(result, output_dir)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["scientific_interpretation"] == "non_scientific_smoke"
    assert "implementation check only" in (output_dir / "review.md").read_text(encoding="utf-8")
