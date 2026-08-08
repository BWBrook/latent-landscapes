from __future__ import annotations

import json
from math import log
from pathlib import Path

import numpy as np

from latent_landscapes.goal001.observations import Observation
from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal004.observations import REPLICATES, SURVEY_TIMES
from latent_landscapes.goal018 import (
    EXPECTED_FILES,
    classify_outcome,
    detection_profile,
    run_goal018,
    smoke_config,
    write_review_bundle,
)


def _all_zero_history() -> tuple[Observation, ...]:
    return tuple(
        Observation("cluster", "training", 0, "site", 0, 0, 0, time, replicate, 0)
        for time in SURVEY_TIMES
        for replicate in REPLICATES
    )


def test_detection_profile_matches_hand_calculated_complete_history() -> None:
    probabilities = (0.5, 0.65)
    weights = np.full((1, 7), 1.0 / 7.0)

    profile = detection_profile(
        site_ids=("site",),
        records=_all_zero_history(),
        category_weights=weights,
        probabilities=probabilities,
    )

    expected = tuple(
        log(sum((1.0 - probability) ** exponent for exponent in (12, 10, 8, 6, 4, 2, 0)) / 7.0)
        for probability in probabilities
    )
    assert np.allclose(profile.log_likelihoods, expected, rtol=0.0, atol=1e-12)
    assert profile.mle_probabilities == (0.5,)


def test_detection_progression_requires_calibration_precision_and_interior_support() -> None:
    calibrated = EstimateInterval(0.95, 0.93, 0.97)

    assert (
        classify_outcome(
            invariants={"valid": True},
            connected_interior_count=480,
            validation_count=500,
            coverage=calibrated,
            median_absolute_error=0.03,
            median_support_width=0.12,
        )
        == "advance_to_joint_unknown_detection"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            connected_interior_count=470,
            validation_count=500,
            coverage=calibrated,
            median_absolute_error=0.03,
            median_support_width=0.12,
        )
        == "detection_support_design_limited"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            connected_interior_count=480,
            validation_count=500,
            coverage=calibrated,
            median_absolute_error=0.06,
            median_support_width=0.12,
        )
        == "detection_parameter_imprecise"
    )


def test_goal018_smoke_writes_only_the_compact_review_surface(tmp_path: Path) -> None:
    result = run_goal018(smoke_config())

    written = write_review_bundle(result, tmp_path)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["scientific_interpretation"] == "non_scientific_smoke"
    assert "implementation check only" in (tmp_path / "review.md").read_text(encoding="utf-8")
