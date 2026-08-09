from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from latent_landscapes.goal021 import ThreeParameterProfile
from latent_landscapes.goal022 import (
    EXPECTED_FILES,
    classify_outcome,
    coarse_profile_from_refined,
    run_goal022,
    smoke_config,
    write_review_bundle,
)


def test_coarse_profile_is_exact_refined_eta_subset() -> None:
    etas = np.asarray([0.5, 0.75, 1.0, 1.25, 1.5])
    rhos = np.asarray([0.5, 1.0])
    probabilities = np.asarray([0.45, 0.65])
    values = np.arange(20, dtype=np.float64).reshape(5, 2, 2)
    refined = ThreeParameterProfile(
        etas=etas,
        rhos=rhos,
        probabilities=probabilities,
        log_likelihoods=values,
        maximum_log_likelihood=19.0,
        mle_indices=((4, 1, 1),),
        mle_cells=((1.0, 1.5, 0.65),),
    )

    coarse = coarse_profile_from_refined(refined, (0.5, 1.0, 1.5))

    assert np.array_equal(coarse.etas, np.asarray([0.5, 1.0, 1.5]))
    assert np.array_equal(coarse.log_likelihoods, values[[0, 2, 4]])
    assert coarse.maximum_log_likelihood == 19.0
    assert coarse.mle_cells == ((1.0, 1.5, 0.65),)


def test_goal022_decision_classes_are_prespecified() -> None:
    advance = "advance_to_cross_truth_three_parameter_benchmark"
    limited = "three_parameter_support_design_limited"

    assert (
        classify_outcome(
            invariants={"valid": True},
            goal021_reconciled=True,
            refined_outcomes=(advance, advance, advance),
        )
        == "coarse_eta_resolution_explains_split_supports"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            goal021_reconciled=True,
            refined_outcomes=(limited, limited, limited),
        )
        == "rho_eta_ambiguity_persists_after_refinement"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            goal021_reconciled=True,
            refined_outcomes=(advance, limited, advance),
        )
        == "integration_bank_sensitivity_unresolved"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            goal021_reconciled=False,
            refined_outcomes=(advance, advance, advance),
        )
        == "goal021_reconciliation_failed"
    )


def test_goal022_smoke_writes_only_compact_review_surface(tmp_path: Path) -> None:
    result = run_goal022(smoke_config())

    written = write_review_bundle(result, tmp_path)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["scientific_interpretation"] == "non_scientific_smoke"
    assert "implementation check only" in (tmp_path / "review.md").read_text(encoding="utf-8")
