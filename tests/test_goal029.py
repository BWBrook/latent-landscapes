from __future__ import annotations

import json
import math
from pathlib import Path

from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal026 import RecoverySummary
from latent_landscapes.goal029 import (
    EXPECTED_FILES,
    DatasetSeed,
    DetectionHistory,
    classify_outcome,
    generate_detection_dataset,
    hazard_ratio_profile,
    run_goal029,
    smoke_config,
    write_review_bundle,
)


def _history(*, arrival: float, counts: tuple[int, ...]) -> DetectionHistory:
    return DetectionHistory(
        dataset_phase="test",
        dataset_index=0,
        site_id="site",
        cluster_id="cluster",
        split="training",
        row=0,
        col=0,
        predator_arrival_time=arrival,
        true_extirpation_time=70.0,
        detection_counts=counts,
        true_alive=(True,) * 6,
    )


def _write_goal027_anchor(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    published_goal026 = {
        "evidence": "published_goal026",
        "calibration_replicates": 250,
        "validation_replicates": 250,
        "cutoff": 3.5902465377401427,
        "coverage_count": 230,
        "coverage": 0.92,
        "coverage_lower": 0.8796703567961583,
        "coverage_upper": 0.9476176716276683,
        "connected_interior_count": 250,
        "null_exclusion_count": 250,
        "median_absolute_log_error": 0.1149312507814774,
        "median_log_support_width": 0.622195444587661,
        "score_advantage": 0.06921492712831596,
        "score_advantage_lower": 0.06219341234770491,
        "score_advantage_upper": 0.07623644190892702,
    }
    confirmation = {
        "evidence": "goal027_high_resolution",
        "calibration_replicates": 2_000,
        "validation_replicates": 1_000,
        "cutoff": 4.029414195600793,
        "coverage_count": 954,
        "coverage": 0.954,
        "coverage_lower": 0.9391877960583809,
        "coverage_upper": 0.9653375072367351,
        "connected_interior_count": 997,
        "null_exclusion_count": 1_000,
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
        "coverage_comparison": [published_goal026, confirmation],
    }
    (path / "summary.json").write_text(json.dumps(payload), encoding="utf-8")


def _summary(*, width: float = 0.70, null_count: int = 1_000) -> RecoverySummary:
    return RecoverySummary(
        cutoff=4.0,
        coverage_count=950,
        coverage=EstimateInterval(0.95, 0.935, 0.962),
        connected_interior_count=1_000,
        null_exclusion_count=null_count,
        median_absolute_log_error=0.12,
        median_log_support_width=width,
        heldout_log_score_advantage=EstimateInterval(0.05, 0.04, 0.06),
    )


def test_hidden_state_likelihood_allows_detection_after_zero() -> None:
    counts = (0, 1, 0, 0, 0, 0)
    arrived = hazard_ratio_profile((_history(arrival=0.0, counts=counts),), (1.0, 5.0, 9.0))
    not_arrived = hazard_ratio_profile((_history(arrival=100.0, counts=counts),), (1.0, 5.0, 9.0))

    assert all(math.isfinite(value) for value in arrived.log_likelihoods)
    assert len(set(round(float(value), 12) for value in arrived.log_likelihoods)) > 1
    assert len(set(round(float(value), 12) for value in not_arrived.log_likelihoods)) == 1


def test_generated_observations_include_misses_but_no_false_positives() -> None:
    config = smoke_config()
    _, histories = generate_detection_dataset(DatasetSeed("validation", 0, 101, 202, 303), config)

    assert len(histories) == 160
    assert sum(row.split == "training" for row in histories) == 120
    assert sum(row.split == "holdout" for row in histories) == 40
    assert any(
        is_alive and count == 0
        for row in histories
        for is_alive, count in zip(row.true_alive, row.detection_counts, strict=True)
    )
    assert all(
        count == 0
        for row in histories
        for is_alive, count in zip(row.true_alive, row.detection_counts, strict=True)
        if not is_alive
    )


def test_decision_requires_every_inherited_recovery_gate() -> None:
    assert (
        classify_outcome(invariants={"valid": True}, summary=_summary(), validation_count=1_000)
        == "known_imperfect_prey_detection_recovered"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            summary=_summary(null_count=949),
            validation_count=1_000,
        )
        == "known_imperfect_prey_detection_not_recovered"
    )
    assert (
        classify_outcome(
            invariants={"valid": True}, summary=_summary(width=0.81), validation_count=1_000
        )
        == "known_imperfect_prey_detection_not_recovered"
    )


def test_goal029_smoke_writes_exact_compact_review_surface(tmp_path: Path) -> None:
    anchor_dir = tmp_path / "goal027"
    output_dir = tmp_path / "goal029"
    _write_goal027_anchor(anchor_dir)

    result = run_goal029(anchor_dir, smoke_config())
    written = write_review_bundle(result, output_dir)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    payload = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert payload["run_mode"] == "reduced_smoke"
    assert "implementation check only" in (output_dir / "review.md").read_text(encoding="utf-8")
