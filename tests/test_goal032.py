from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal032 import (
    EXPECTED_FILES,
    JointProfile,
    JointRecoverySummary,
    build_joint_arrival_integration,
    classify_outcome,
    run_goal032,
    smoke_config,
    summarize_joint_support,
    write_review_bundle,
)


def test_candidate_spread_rate_rescales_arrivals_exactly() -> None:
    bank = np.asarray([[4.0], [14.0], [24.0], [34.0]])
    joint = build_joint_arrival_integration(
        bank,
        ("site",),
        (1.0, 2.0),
        (1.0, 5.0),
    )
    from latent_landscapes.goal031 import build_arrival_integration

    reference_truth = build_arrival_integration(bank, ("site",), (1.0, 5.0), 0.002)
    reference_fast = build_arrival_integration(bank / 2.0, ("site",), (1.0, 5.0), 0.002)

    assert np.array_equal(joint.category_mass[0], reference_truth.category_mass)
    assert np.array_equal(joint.survival_moments[0], reference_truth.survival_moments)
    assert np.array_equal(joint.category_mass[1], reference_fast.category_mass)
    assert np.array_equal(joint.survival_moments[1], reference_fast.survival_moments)
    assert joint.rhos.count(1.0) == 1
    assert joint.hazard_ratios.count(5.0) == 1


def test_joint_support_reports_connected_interior_and_disconnected_cases() -> None:
    rhos = np.asarray((0.5, 0.75, 1.0, 1.25, 1.5))
    effects = np.asarray((1.0, 3.0, 5.0, 7.0, 9.0))
    connected_values = np.full((5, 5), -10.0)
    connected_values[1:4, 1:4] = -1.0
    connected_values[2, 2] = 0.0
    connected = JointProfile(rhos, effects, connected_values, 0.0, 1.0, 5.0)
    support = summarize_joint_support(connected, 2.1, 1.0, 5.0)

    assert support.truth_included
    assert support.component_count == 1
    assert not support.boundary_contact
    assert support.no_effect_excluded

    disconnected_values = np.full((5, 5), -10.0)
    disconnected_values[1, 1] = 0.0
    disconnected_values[3, 3] = 0.0
    disconnected = JointProfile(rhos, effects, disconnected_values, 0.0, 0.75, 3.0)
    assert summarize_joint_support(disconnected, 0.1, 1.0, 5.0).component_count == 2


def _summary(*, rate_width: float = 0.4, effect_width: float = 0.7) -> JointRecoverySummary:
    return JointRecoverySummary(
        cutoff=5.0,
        coverage_count=950,
        coverage=EstimateInterval(0.95, 0.935, 0.962),
        connected_interior_count=1_000,
        no_effect_exclusion_count=1_000,
        median_absolute_log_rho_error=0.05,
        median_log_rho_support_width=rate_width,
        median_absolute_log_effect_error=0.12,
        median_log_effect_support_width=effect_width,
        heldout_log_score_advantage=EstimateInterval(0.05, 0.04, 0.06),
    )


def test_decision_distinguishes_which_biological_quantity_is_weak() -> None:
    assert (
        classify_outcome(invariants={"valid": True}, summary=_summary(), validation_count=1_000)
        == "joint_spread_rate_prey_effect_recovered"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            summary=_summary(effect_width=0.81),
            validation_count=1_000,
        )
        == "spread_rate_recovered_prey_effect_weak"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            summary=_summary(rate_width=0.51),
            validation_count=1_000,
        )
        == "prey_effect_recovered_spread_rate_weak"
    )


def test_goal032_smoke_writes_exact_compact_review_surface(tmp_path: Path) -> None:
    anchor_dir = tmp_path / "goal031"
    output_dir = tmp_path / "goal032"
    _write_goal031_anchor(anchor_dir)

    result = run_goal032(anchor_dir, smoke_config(), workers=2)
    written = write_review_bundle(result, output_dir)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    payload = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert payload["run_mode"] == "reduced_smoke"
    assert payload["post_run_diagnosis"] == (
        "point_estimates_centered_but_joint_uncertainty_not_resolved"
    )
    assert payload["diagnostics"]["connected_support_count"] >= 0
    assert "implementation check only" in (output_dir / "review.md").read_text(encoding="utf-8")


def _write_goal031_anchor(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    payload = {
        "goal": "031-latent-arrival-prey-effect-positive-control",
        "outcome": "latent_arrival_prey_effect_recovered",
        "calibration": {"replicates": 2_000},
        "validation": {
            "replicates": 1_000,
            "coverage_count": 963,
            "coverage": {
                "estimate": 0.963,
                "lower": 0.9494176025179306,
                "upper": 0.9730388191244452,
            },
            "connected_interior_count": 993,
            "no_effect_exclusion_count": 1_000,
            "median_absolute_log_error": 0.12783337150988477,
            "median_log_support_width": 0.7572260372444677,
            "heldout_log_score_advantage": {
                "estimate": 0.052954921839030944,
                "lower": 0.04986285614595211,
                "upper": 0.05604698753210978,
            },
        },
    }
    (path / "summary.json").write_text(json.dumps(payload), encoding="utf-8")
