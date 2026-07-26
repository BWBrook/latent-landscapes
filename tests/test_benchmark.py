from __future__ import annotations

import importlib
from math import inf
from typing import Any

import pytest


def load_module(name: str) -> Any:
    return importlib.import_module(f"latent_landscapes.goal001.{name}")


def test_neutral_geometry_uses_passable_landscape_dmax() -> None:
    landscape_module = load_module("landscape")
    benchmark_module = load_module("benchmark")
    design_module = load_module("design")
    landscape = landscape_module.build_landscape()
    centre_rng, holdout_rng, _ = design_module.spawn_generators()
    design = design_module.build_design(landscape, centre_rng, holdout_rng)

    distances, dmax = benchmark_module.compute_neutral_distances(landscape, design.sites)

    assert dmax == pytest.approx(81.49846624323675)
    assert len(distances) == 160
    assert min(distances.values()) > 0.0
    assert max(distances.values()) <= 120.0


def test_canonical_benchmark_scientific_result() -> None:
    benchmark_module = load_module("benchmark")

    result = benchmark_module.build_benchmark()

    assert result.ideal_process_identifiable is True
    assert result.training_record_count == 1440
    assert result.holdout_record_count == 480
    assert result.full_record_count == 1920
    assert result.habitat_training.maximum_log_likelihood == pytest.approx(-409.4135353149208)
    assert result.neutral_training.maximum_log_likelihood == pytest.approx(-594.1822292266855)
    assert len(result.habitat_training.mle_classes) == 1
    assert len(result.neutral_training.mle_classes) == 1
    assert len(result.habitat_all.mle_classes) == 1
    habitat_mle = result.habitat_all.mle_classes[0]
    assert habitat_mle.lower == pytest.approx(0.9994971078624002)
    assert habitat_mle.upper == pytest.approx(1.000069859134422)
    assert habitat_mle.width == pytest.approx(0.0005727512720217209)
    assert len(result.habitat_all.support_components) == 1
    support = result.habitat_all.support_components[0]
    assert support.lower == pytest.approx(0.9994971078624002)
    assert support.upper == pytest.approx(1.000069859134422)
    assert support.lower_closed is True
    assert support.upper_closed is False
    assert support.contains(1.0)
    assert result.habitat_holdout.log_score_range.minimum == pytest.approx(-130.21690767826243)
    assert result.neutral_holdout.log_score_range.maximum == -inf
    assert result.neutral_holdout.impossible_positive_range.minimum == 4.0
    assert result.comparison == "habitat_robustly_better"
    assert result.outcome == "advance_goal002"
    assert all(result.invariants.values())


def test_outcome_precedence_and_no_automatic_width_threshold() -> None:
    benchmark_module = load_module("benchmark")
    likelihood_module = load_module("likelihood")
    interval = likelihood_module.Interval

    assert (
        benchmark_module.classify_outcome(
            implementation_ok=False,
            ideal_identifiable=True,
            support_components=(interval(0.9, 1.1, True, True),),
            comparison="habitat_robustly_better",
        )
        == "implementation_blocked"
    )
    assert (
        benchmark_module.classify_outcome(
            implementation_ok=True,
            ideal_identifiable=False,
            support_components=(interval(0.9, 1.1, True, True),),
            comparison="habitat_robustly_better",
        )
        == "implementation_blocked"
    )
    assert (
        benchmark_module.classify_outcome(
            implementation_ok=True,
            ideal_identifiable=True,
            support_components=(interval(1.1, 1.2, True, True),),
            comparison="habitat_robustly_better",
        )
        == "recovery_failure"
    )
    assert (
        benchmark_module.classify_outcome(
            implementation_ok=True,
            ideal_identifiable=True,
            support_components=(
                interval(0.8, 0.9, True, False),
                interval(0.95, 1.1, True, True),
            ),
            comparison="habitat_robustly_better",
        )
        == "design_limited"
    )
    assert (
        benchmark_module.classify_outcome(
            implementation_ok=True,
            ideal_identifiable=True,
            support_components=(interval(0.25, 1.1, True, True),),
            comparison="habitat_robustly_better",
        )
        == "design_limited"
    )
    assert (
        benchmark_module.classify_outcome(
            implementation_ok=True,
            ideal_identifiable=True,
            support_components=(interval(0.26, 3.99, True, True),),
            comparison="habitat_robustly_better",
        )
        == "advance_goal002"
    )
    assert (
        benchmark_module.classify_outcome(
            implementation_ok=True,
            ideal_identifiable=True,
            support_components=(interval(0.9, 1.1, True, True),),
            comparison="neutral_robustly_better",
        )
        == "mechanism_not_supported"
    )
    assert (
        benchmark_module.classify_outcome(
            implementation_ok=True,
            ideal_identifiable=True,
            support_components=(interval(0.9, 1.1, True, True),),
            comparison="inconclusive",
        )
        == "rate_recoverable_mechanism_inconclusive"
    )
