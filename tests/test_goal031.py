from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal026 import SURVEY_TIMES, RecoverySummary
from latent_landscapes.goal031 import (
    EXPECTED_FILES,
    PSEUDO_ARRIVALS,
    CrossLayerHistory,
    Goal031Config,
    build_arrival_integration,
    classify_outcome,
    latent_arrival_profile,
    run_goal031,
    smoke_config,
    write_review_bundle,
)


def _config(*, bank_size: int = 4) -> Goal031Config:
    return Goal031Config(
        bank_size=bank_size,
        calibration_replicates=1,
        validation_replicates=1,
        calibration_rank_one_based=1,
        hazard_ratios=(1.0, 5.0),
        neutral_hazards=(0.001, 0.002, 0.01),
    )


def _history() -> CrossLayerHistory:
    return CrossLayerHistory(
        "test",
        0,
        0,
        "site",
        "cluster",
        "training",
        0,
        0,
        24.0,
        48.0,
        (0, 0, 2, 1, 2, 1),
        (2, 1, 0, 0, 0, 0),
        (False, False, True, True, True, True),
        (True, True, True, True, False, False),
    )


def _binomial_probability(count: int, probability: float = 0.65) -> float:
    return math.comb(2, count) * probability**count * (1.0 - probability) ** (2 - count)


def _conditional_probabilities(arrival: float, hazard_ratio: float) -> tuple[float, float]:
    history = _history()
    category = int(np.searchsorted(np.asarray(SURVEY_TIMES), arrival, side="left"))
    predator = 1.0
    for survey_index, count in enumerate(history.predator_detection_counts):
        if category > survey_index:
            predator *= float(count == 0)
        else:
            predator *= _binomial_probability(count)

    survival = [1.0]
    for time in SURVEY_TIMES:
        post = max(time - arrival, 0.0)
        pre = time - post
        survival.append(math.exp(-0.002 * (pre + hazard_ratio * post)))
    alive = [_binomial_probability(count) for count in history.prey_detection_counts]
    dead = [float(count == 0) for count in history.prey_detection_counts]
    prey = 0.0
    for event_index in range(len(SURVEY_TIMES)):
        prey += (
            (survival[event_index] - survival[event_index + 1])
            * math.prod(alive[:event_index])
            * math.prod(dead[event_index:])
        )
    prey += survival[-1] * math.prod(alive)
    return predator, prey


def test_latent_likelihood_shares_arrival_between_predator_and_prey() -> None:
    bank = np.asarray([[5.0], [25.0], [45.0], [65.0]])
    config = _config()
    integration = build_arrival_integration(bank, ("site",), config.hazard_ratios, 0.002)
    profile = latent_arrival_profile((_history(),), integration, config)

    augmented = tuple(float(value) for value in bank[:, 0]) + PSEUDO_ARRIVALS
    weights = (1.0,) * len(bank) + (0.5,) * len(PSEUDO_ARRIVALS)
    conditional = tuple(_conditional_probabilities(value, 5.0) for value in augmented)
    denominator = sum(weights)
    shared = (
        sum(
            weight * predator * prey
            for weight, (predator, prey) in zip(weights, conditional, strict=True)
        )
        / denominator
    )
    independent = (
        sum(weight * predator for weight, (predator, _) in zip(weights, conditional, strict=True))
        / denominator
    ) * (
        sum(weight * prey for weight, (_, prey) in zip(weights, conditional, strict=True))
        / denominator
    )

    assert math.exp(float(profile.log_likelihoods[1])) == pytest_approx(shared)
    assert not math.isclose(shared, independent, rel_tol=1e-4)


def test_arrival_survival_moment_matches_direct_smoothed_integration() -> None:
    bank = np.asarray([[4.0], [14.0], [24.0], [34.0]])
    integration = build_arrival_integration(bank, ("site",), (1.0, 5.0), 0.002)
    denominator = 4.0 + 3.5
    expected = (
        math.exp(-0.002 * (5.0 * 30.0 + (1.0 - 5.0) * 24.0))
        + 0.5 * math.exp(-0.002 * (5.0 * 30.0 + (1.0 - 5.0) * 25.0))
    ) / denominator

    assert integration.category_mass.sum(axis=1)[0] == pytest_approx(1.0)
    assert integration.survival_moments[1, 0, 3, 2] == pytest_approx(expected)
    assert np.all(np.diff(integration.survival_moments.sum(axis=3), axis=2) <= 1e-12)


def _summary(*, width: float = 0.70, no_effect_count: int = 1_000) -> RecoverySummary:
    return RecoverySummary(
        cutoff=4.0,
        coverage_count=950,
        coverage=EstimateInterval(0.95, 0.935, 0.962),
        connected_interior_count=1_000,
        null_exclusion_count=no_effect_count,
        median_absolute_log_error=0.12,
        median_log_support_width=width,
        heldout_log_score_advantage=EstimateInterval(0.05, 0.04, 0.06),
    )


def test_decision_requires_every_prespecified_recovery_gate() -> None:
    assert (
        classify_outcome(invariants={"valid": True}, summary=_summary(), validation_count=1_000)
        == "latent_arrival_prey_effect_recovered"
    )
    assert (
        classify_outcome(
            invariants={"valid": True},
            summary=_summary(no_effect_count=949),
            validation_count=1_000,
        )
        == "latent_arrival_prey_effect_not_recovered"
    )
    assert (
        classify_outcome(
            invariants={"valid": True}, summary=_summary(width=0.81), validation_count=1_000
        )
        == "latent_arrival_prey_effect_not_recovered"
    )


def test_goal031_smoke_writes_exact_compact_review_surface(tmp_path: Path) -> None:
    anchor_dir = tmp_path / "goal029"
    output_dir = tmp_path / "goal031"
    _write_goal029_anchor(anchor_dir)

    result = run_goal031(anchor_dir, smoke_config(), workers=1)
    written = write_review_bundle(result, output_dir)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    payload = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert payload["run_mode"] == "reduced_smoke"
    assert "implementation check only" in (output_dir / "review.md").read_text(encoding="utf-8")


def _write_goal029_anchor(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    payload = {
        "goal": "029-known-arrival-known-imperfect-prey-detection",
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


def pytest_approx(value: float) -> object:
    import pytest

    return pytest.approx(value, rel=1e-12, abs=1e-14)
