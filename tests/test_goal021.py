from __future__ import annotations

import json
from math import log
from pathlib import Path

import numpy as np

from latent_landscapes.goal001.observations import Observation
from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal004.observations import REPLICATES, SURVEY_TIMES
from latent_landscapes.goal021 import (
    EXPECTED_FILES,
    ThreeParameterProfile,
    classify_outcome,
    run_goal021,
    smoke_config,
    summarize_support,
    three_parameter_profile,
    write_review_bundle,
)


def _all_zero_history() -> tuple[Observation, ...]:
    return tuple(
        Observation("cluster", "training", 0, "site", 0, 0, 0, time, replicate, 0)
        for time in SURVEY_TIMES
        for replicate in REPLICATES
    )


def test_three_parameter_profile_matches_hand_calculation() -> None:
    rhos = np.asarray([0.5, 1.0])
    etas = np.asarray([0.5, 1.0])
    probabilities = (0.45, 0.65)
    weights = np.asarray(
        [
            [
                [[0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.40]],
                [[0.15, 0.15, 0.15, 0.10, 0.10, 0.10, 0.25]],
            ],
            [
                [[0.20, 0.15, 0.15, 0.10, 0.10, 0.10, 0.20]],
                [[0.25, 0.20, 0.15, 0.10, 0.10, 0.10, 0.10]],
            ],
        ]
    )

    profile = three_parameter_profile(
        site_ids=("site",),
        records=_all_zero_history(),
        category_weights=weights,
        rhos=rhos,
        etas=etas,
        probabilities=probabilities,
    )

    exponents = (12, 10, 8, 6, 4, 2, 0)
    expected = np.asarray(
        [
            [
                [
                    log(
                        sum(
                            weight * (1.0 - probability) ** exponent
                            for weight, exponent in zip(row[0], exponents, strict=True)
                        )
                    )
                    for probability in probabilities
                ]
                for row in eta_rows
            ]
            for eta_rows in weights
        ]
    )
    assert np.allclose(profile.log_likelihoods, expected, rtol=0.0, atol=1e-12)


def test_three_dimensional_support_and_progression() -> None:
    values = np.full((3, 3, 3), -10.0)
    values[1, 1, 1] = 0.0
    profile = ThreeParameterProfile(
        etas=np.asarray([0.5, 1.0, 1.5]),
        rhos=np.asarray([0.5, 1.0, 2.0]),
        probabilities=np.asarray([0.45, 0.65, 0.85]),
        log_likelihoods=values,
        maximum_log_likelihood=0.0,
        mle_indices=((1, 1, 1),),
        mle_cells=((1.0, 1.0, 0.65),),
    )
    support = summarize_support(profile, cutoff=1.0)

    assert support.truth_included
    assert support.component_count == 1
    assert not support.boundary_contact
    calibrated = EstimateInterval(0.95, 0.92, 0.97)
    assert (
        classify_outcome(
            invariants={"valid": True},
            connected_interior_count=240,
            validation_count=250,
            coverage=calibrated,
            median_log_rho_error=0.04,
            median_eta_error=0.20,
            median_probability_error=0.02,
            median_log_rho_width=0.30,
            median_eta_width=0.50,
            median_probability_width=0.10,
        )
        == "advance_to_cross_truth_three_parameter_benchmark"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            connected_interior_count=240,
            validation_count=250,
            coverage=calibrated,
            median_log_rho_error=0.04,
            median_eta_error=0.20,
            median_probability_error=0.02,
            median_log_rho_width=0.60,
            median_eta_width=0.50,
            median_probability_width=0.10,
        )
        == "three_parameter_recovery_imprecise"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            connected_interior_count=240,
            validation_count=250,
            coverage=calibrated,
            median_log_rho_error=0.04,
            median_eta_error=0.20,
            median_probability_error=0.02,
            median_log_rho_width=0.30,
            median_eta_width=0.50,
            median_probability_width=0.20000000000000007,
        )
        == "advance_to_cross_truth_three_parameter_benchmark"
    )


def test_goal021_smoke_writes_only_the_compact_review_surface(tmp_path: Path) -> None:
    result = run_goal021(smoke_config())

    written = write_review_bundle(result, tmp_path)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["scientific_interpretation"] == "non_scientific_smoke"
    assert "implementation check only" in (tmp_path / "review.md").read_text(encoding="utf-8")
