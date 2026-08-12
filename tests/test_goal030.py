from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal029 import DetectionHistory
from latent_landscapes.goal030 import (
    EXPECTED_FILES,
    JointRecoverySummary,
    _component_count,
    classify_outcome,
    joint_profile,
    run_goal030,
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


def _write_goal029_anchor(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    payload = {
        "goal": "029-known-arrival-known-imperfect-prey-detection",
        "run_mode": "production",
        "outcome": "known_imperfect_prey_detection_recovered",
        "calibration": {"replicates": 2_000},
        "validation": {
            "replicates": 1_000,
            "coverage_count": 956,
            "coverage": {
                "estimate": 0.956,
                "lower": 0.9414482108495923,
                "upper": 0.9670617854115815,
            },
            "connected_interior_count": 994,
            "null_exclusion_count": 1_000,
            "median_absolute_log_error": 0.12783337150988477,
            "median_log_support_width": 0.7192935779202623,
            "heldout_log_score_advantage": {
                "estimate": 0.051329190324883894,
                "lower": 0.04798173400659128,
                "upper": 0.05467664664317651,
            },
        },
    }
    (path / "summary.json").write_text(json.dumps(payload), encoding="utf-8")


def _summary(*, effect_width: float = 0.70, detection_width: float = 0.10) -> JointRecoverySummary:
    return JointRecoverySummary(
        cutoff=5.5,
        coverage_count=950,
        coverage=EstimateInterval(0.95, 0.935, 0.962),
        connected_interior_count=1_000,
        no_effect_exclusion_count=1_000,
        median_absolute_log_effect_error=0.12,
        median_log_effect_support_width=effect_width,
        median_absolute_detection_probability_error=0.025,
        median_detection_probability_support_width=detection_width,
        heldout_log_score_advantage=EstimateInterval(0.05, 0.04, 0.06),
    )


def test_joint_likelihood_uses_both_effect_and_detection_dimensions() -> None:
    histories = (
        _history(arrival=0.0, counts=(0, 1, 0, 0, 0, 0)),
        _history(arrival=25.0, counts=(2, 1, 1, 0, 0, 0)),
    )
    profile = joint_profile(
        histories,
        (1.0, 5.0, 9.0),
        (0.40, 0.65, 0.90),
        background_hazard=0.002,
        use_arrival=True,
    )

    assert profile.log_likelihoods.shape == (3, 3)
    assert np.isfinite(profile.log_likelihoods).all()
    assert len({round(float(value), 10) for value in profile.log_likelihoods[:, 1]}) > 1
    assert len({round(float(value), 10) for value in profile.log_likelihoods[1, :]}) > 1


def test_joint_support_component_count_uses_four_neighbours() -> None:
    connected = np.asarray([[True, True, False], [False, True, False]], dtype=np.bool)
    diagonal = np.asarray([[True, False], [False, True]], dtype=np.bool)

    assert _component_count(connected) == 1
    assert _component_count(diagonal) == 2


def test_joint_decision_separates_effect_and_detection_failures() -> None:
    assert (
        classify_outcome(invariants={"valid": True}, summary=_summary(), validation_count=1_000)
        == "joint_prey_effect_detection_recovered"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            summary=_summary(detection_width=0.16),
            validation_count=1_000,
        )
        == "prey_effect_recovered_detection_weak"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            summary=_summary(effect_width=0.81),
            validation_count=1_000,
        )
        == "detection_recovered_prey_effect_weak"
    )


def test_goal030_smoke_writes_exact_compact_review_surface(tmp_path: Path) -> None:
    anchor_dir = tmp_path / "goal029"
    output_dir = tmp_path / "goal030"
    _write_goal029_anchor(anchor_dir)

    result = run_goal030(anchor_dir, smoke_config(), workers=1)
    written = write_review_bundle(result, output_dir)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    payload = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert payload["run_mode"] == "reduced_smoke"
    assert "implementation check only" in (output_dir / "review.md").read_text(encoding="utf-8")
