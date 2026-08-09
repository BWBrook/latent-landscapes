from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal021 import ThreeParameterProfile, summarize_support
from latent_landscapes.goal023 import (
    EXPECTED_FILES,
    TruthCell,
    classify_outcome,
    generate_truth_dataset,
    run_goal023,
    smoke_config,
    write_review_bundle,
)


def test_truth_generation_pairs_process_and_detection_random_numbers() -> None:
    config = smoke_config()
    fixed = goal011.build_fixed_inputs()
    seed = goal011.spawn_seed_manifest(config.goal011_config).calibration[0]
    central = TruthCell("central", 1.0, 1.0, 0.65)
    low_detection = TruthCell("low_detection", 1.0, 1.0, 0.45)

    central_truth, central_records = generate_truth_dataset(fixed, seed, central)
    low_truth, low_records = generate_truth_dataset(fixed, seed, low_detection)
    frozen_central_truth, frozen_central_records = goal011.generate_dataset(fixed, seed)

    assert np.array_equal(central_truth.arrival, low_truth.arrival)
    assert np.array_equal(central_truth.arrival, frozen_central_truth.arrival)
    assert central_records == frozen_central_records
    assert len(central_records) == len(low_records) == 1920
    assert all(
        low.detected <= central_record.detected
        for central_record, low in zip(central_records, low_records, strict=True)
    )


def test_arbitrary_truth_support_and_goal_decision() -> None:
    values = np.full((3, 3, 3), -10.0)
    values[0, 0, 0] = 0.0
    profile = ThreeParameterProfile(
        etas=np.asarray([0.5, 1.0, 1.5]),
        rhos=np.asarray([0.5, 1.0, 2.0]),
        probabilities=np.asarray([0.45, 0.65, 0.85]),
        log_likelihoods=values,
        maximum_log_likelihood=0.0,
        mle_indices=((0, 0, 0),),
        mle_cells=((0.5, 0.5, 0.45),),
    )

    support = summarize_support(
        profile,
        cutoff=1.0,
        truth_rho=0.5,
        truth_eta=0.5,
        truth_probability=0.45,
    )

    assert support.truth_included
    assert support.minimum_log_rho_error == 0.0
    assert support.minimum_eta_error == 0.0
    assert support.minimum_probability_error == 0.0
    advance = "advance_to_cross_truth_three_parameter_benchmark"
    assert (
        classify_outcome(
            invariants={"valid": True},
            central_reconciled=True,
            stress_outcomes=(advance, advance, advance),
        )
        == "advance_to_joint_interaction_truths"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            central_reconciled=True,
            stress_outcomes=(advance, "three_parameter_recovery_imprecise", advance),
        )
        == "one_axis_identifiability_limit_found"
    )


def test_goal023_smoke_writes_only_compact_review_surface(tmp_path: Path) -> None:
    result = run_goal023(smoke_config())

    written = write_review_bundle(result, tmp_path)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["scientific_interpretation"] == "non_scientific_smoke"
    assert "implementation check only" in (tmp_path / "review.md").read_text(encoding="utf-8")
