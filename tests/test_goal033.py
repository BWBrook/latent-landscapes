from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes import goal032
from latent_landscapes.goal033 import (
    EXPECTED_FILES,
    PREY_EFFECT_RECOVERED,
    PREY_EFFECT_WEAK,
    ParameterSummary,
    classify_outcome,
    load_goal032_anchor,
    profile_likelihood_drops,
    run_goal033,
    smoke_config,
    summarize_marginal_support,
    write_review_bundle,
)


def test_profile_statistics_and_marginal_support_are_parameter_specific() -> None:
    profile = goal032.JointProfile(
        np.asarray((0.5, 1.0, 2.0)),
        np.asarray((1.0, 5.0, 9.0)),
        np.asarray(
            (
                (-10.0, -3.0, -8.0),
                (-8.0, 0.0, -5.0),
                (-9.0, -2.0, -7.0),
            )
        ),
        0.0,
        1.0,
        5.0,
    )

    spread_drops, effect_drops = profile_likelihood_drops(profile)
    spread = summarize_marginal_support(profile.rhos, spread_drops, 4.1, 1.0)
    effect = summarize_marginal_support(profile.hazard_ratios, effect_drops, 10.1, 5.0)

    assert np.array_equal(spread_drops, np.asarray((6.0, 0.0, 4.0)))
    assert np.array_equal(effect_drops, np.asarray((16.0, 0.0, 10.0)))
    assert spread.truth_included and spread.component_count == 1
    assert spread.boundary_contact and (spread.lower, spread.upper) == (1.0, 2.0)
    assert effect.truth_included and effect.component_count == 1
    assert effect.boundary_contact and (effect.lower, effect.upper) == (5.0, 9.0)
    disconnected = summarize_marginal_support(
        np.asarray((1.0, 2.0, 3.0)),
        np.asarray((0.0, 5.0, 0.0)),
        0.1,
        1.0,
    )
    assert disconnected.component_count == 2


def _effect_summary(*, width: float = 0.7) -> ParameterSummary:
    return ParameterSummary(
        "prey_effect",
        4.0,
        950,
        0.95,
        0.935,
        0.962,
        1_000,
        0,
        0.12,
        width,
        1_000,
        width <= 0.8,
    )


def test_decision_distinguishes_recovery_weakness_and_invalid_run() -> None:
    assert (
        classify_outcome(
            invariants={"valid": True},
            effect_summary=_effect_summary(),
            validation_count=1_000,
        )
        == PREY_EFFECT_RECOVERED
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            effect_summary=_effect_summary(width=0.81),
            validation_count=1_000,
        )
        == PREY_EFFECT_WEAK
    )
    assert (
        classify_outcome(
            invariants={"valid": False},
            effect_summary=_effect_summary(),
            validation_count=1_000,
        )
        == "implementation_blocked"
    )


def test_goal032_anchor_rejects_wrong_identity(tmp_path: Path) -> None:
    (tmp_path / "summary.json").write_text(json.dumps({"goal": "not-goal-032"}), encoding="utf-8")
    with pytest.raises(ValueError, match="wrong identity"):
        load_goal032_anchor(tmp_path, smoke_config())


def test_goal033_smoke_replays_anchor_and_writes_compact_bundle(tmp_path: Path) -> None:
    goal031_dir = tmp_path / "goal031"
    goal032_dir = tmp_path / "goal032"
    goal033_dir = tmp_path / "goal033"
    _write_goal031_anchor(goal031_dir)
    config = smoke_config()
    anchor_result = goal032.run_goal032(goal031_dir, config, workers=1)
    goal032.write_review_bundle(anchor_result, goal032_dir)

    result = run_goal033(goal032_dir, config, workers=2)
    written = write_review_bundle(result, goal033_dir)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    payload = json.loads((goal033_dir / "summary.json").read_text(encoding="utf-8"))
    assert payload["run_mode"] == "reduced_smoke"
    assert "not simultaneous joint coverage" in payload["claim_scope"]
    assert "implementation check only" in (goal033_dir / "review.md").read_text(encoding="utf-8")


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
