from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
import pytest

from latent_landscapes.goal002.baseline import BaselineScore
from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal004 import benchmark
from latent_landscapes.goal004.likelihood import PredictiveScore


def tiny_config(**changes: Any) -> benchmark.Goal004Config:
    config = benchmark.Goal004Config(
        master_seed=37,
        bank_size=8,
        calibration_replicates=4,
        validation_replicates=3,
        calibration_rank_one_based=4,
        rates=(0.5, 0.75, 1.0, 1.5, 2.0),
    )
    return replace(config, **changes)


@pytest.fixture(scope="module")
def small_result() -> benchmark.Goal004Result:
    return benchmark.run_goal004(tiny_config())


def test_hierarchical_seed_manifest_is_ordered_disjoint_and_replayable() -> None:
    config = tiny_config()

    manifest = benchmark.spawn_seed_manifest(config)
    streams = manifest.stream_records

    assert [record.phase for record in manifest.integration_bank] == ["integration_bank"] * 8
    assert [record.index for record in manifest.integration_bank] == list(range(8))
    assert [record.stream_role for record in manifest.integration_bank] == ["process"] * 8
    assert [record.phase for record in manifest.calibration] == ["calibration"] * 4
    assert [record.phase for record in manifest.validation] == ["validation"] * 3
    assert all(record.process.spawn_key[-1] == 0 for record in manifest.calibration)
    assert all(record.detection.spawn_key[-1] == 1 for record in manifest.calibration)
    assert all(record.process.spawn_key[-1] == 0 for record in manifest.validation)
    assert all(record.detection.spawn_key[-1] == 1 for record in manifest.validation)
    assert len(streams) == 8 + 2 * 4 + 2 * 3
    assert len({(record.entropy, record.spawn_key) for record in streams}) == len(streams)
    assert len({record.state_words for record in streams}) == len(streams)
    for record in streams:
        replay = benchmark.generator_from_seed_record(record)
        expected = np.random.Generator(
            np.random.PCG64(
                np.random.SeedSequence(
                    record.entropy,
                    spawn_key=record.spawn_key,
                    pool_size=record.pool_size,
                )
            )
        )
        assert np.array_equal(replay.random(4), expected.random(4))


def test_pinned_parent_commit_and_all_source_blobs_are_reconciled() -> None:
    fixed = benchmark.build_fixed_inputs()

    assert fixed.invariants["frozen_repository_commit_reconciled"]
    assert fixed.invariants["frozen_parent_source_blobs_reconciled"]
    assert fixed.invariants["frozen_runtime_source_blobs_reconciled"]
    assert fixed.invariants["frozen_source_blobs_reconciled"]
    assert set(benchmark.PINNED_SOURCE_PATHS) == {
        "goal001_landscape_blob",
        "goal001_design_blob",
        "goal003_stochastic_spread_blob",
        "goal002_neutral_baseline_blob",
    }


def test_tiny_run_retains_only_site_bank_and_compact_outer_results(
    small_result: benchmark.Goal004Result,
) -> None:
    assert small_result.integration_bank.arrivals.shape == (8, 160)
    assert small_result.integration_bank.site_ids == tuple(
        site.site_id for site in small_result.fixed_inputs.design.sites
    )
    assert [variant.name for variant in small_result.bank_variants] == [
        "full",
        "first_half",
        "second_half",
    ]
    assert [variant.draw_count for variant in small_result.bank_variants] == [8, 4, 4]
    assert all(variant.weights.shape == (5, 160, 7) for variant in small_result.bank_variants)
    assert len(small_result.calibration_results) == 4 * 3
    assert len(small_result.validation_results) == 3 * 3
    assert all(row.record_count == 1_920 for row in small_result.calibration_results)
    assert all(row.record_count == 1_920 for row in small_result.validation_results)
    assert all(row.training_record_count == 1_440 for row in small_result.validation_results)
    assert all(row.holdout_record_count == 480 for row in small_result.validation_results)
    assert all(row.split_isolated for row in small_result.validation_results)
    assert all(row.no_false_positives for row in small_result.calibration_results)
    assert all(row.no_false_positives for row in small_result.validation_results)
    assert all(small_result.invariants.values())
    assert not hasattr(small_result, "observations")
    assert not hasattr(small_result, "truths")


def test_truth_criterion_uses_exact_grid_index_and_each_bank_has_own_cutoff(
    small_result: benchmark.Goal004Result,
) -> None:
    assert benchmark.DEFAULT_CONFIG.truth_index == 300
    assert tiny_config().truth_index == 2

    for bank_summary in small_result.bank_summaries:
        statistics = sorted(
            row.lr_at_truth
            for row in small_result.calibration_results
            if row.bank_variant == bank_summary.bank_variant
        )
        assert bank_summary.cutoff.rank_one_based == 4
        assert bank_summary.cutoff.cutoff == statistics[3]
        assert all(
            row.truth_grid_index == 2
            for row in small_result.calibration_results
            if row.bank_variant == bank_summary.bank_variant
        )


def test_outer_datasets_are_generated_once_then_split_for_fitting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_generate = benchmark.generate_observations
    original_fit_neutral = benchmark.fit_time_stratified_baseline
    generated = 0
    neutral_fit_splits: list[set[str]] = []

    def counted_generate(*args: Any, **kwargs: Any) -> Any:
        nonlocal generated
        generated += 1
        assert len(args[0]) == 160
        return original_generate(*args, **kwargs)

    def checked_neutral(records: Any, **kwargs: Any) -> Any:
        neutral_fit_splits.append({record.split for record in records})
        return original_fit_neutral(records, **kwargs)

    monkeypatch.setattr(benchmark, "generate_observations", counted_generate)
    monkeypatch.setattr(benchmark, "fit_time_stratified_baseline", checked_neutral)

    result = benchmark.run_goal004(
        tiny_config(
            bank_size=2,
            calibration_replicates=1,
            validation_replicates=1,
            calibration_rank_one_based=1,
        )
    )

    assert generated == 2
    assert neutral_fit_splits == [{"training"}]
    assert all(row.split_isolated for row in result.validation_results)


def test_worst_mle_predictive_comparison_is_conservative() -> None:
    stochastic = (
        PredictiveScore(-10.0, 0.12, 10, 0.1, 0.8),
        PredictiveScore(-12.0, 0.18, 10, 0.2, 0.7),
    )
    neutral = BaselineScore(-11.0, 0.15, 10)

    comparison = benchmark.summarize_predictive_comparison(stochastic, neutral)

    assert comparison.stochastic_brier_minimum == 0.12
    assert comparison.stochastic_brier_maximum == 0.18
    assert comparison.stochastic_log_score_minimum == -12.0
    assert comparison.stochastic_log_score_maximum == -10.0
    assert comparison.paired_brier_difference == pytest.approx(0.03)


@pytest.mark.parametrize(
    (
        "topology_count",
        "total",
        "coverage",
        "brier",
        "expected",
    ),
    [
        (474, 500, (0.94, 0.96), (-0.2, -0.1), "design_limited"),
        (475, 500, (0.90, 0.94), (-0.2, -0.1), "calibration_not_ready"),
        (475, 500, (0.94, 0.96), (0.01, 0.1), "rate_recoverable_neutral_better"),
        (
            475,
            500,
            (0.94, 0.96),
            (-0.1, 0.0),
            "rate_recoverable_mechanism_inconclusive",
        ),
        (
            475,
            500,
            (0.94, 0.96),
            (-0.1, -0.01),
            "advance_one_rate_stochastic_spread",
        ),
    ],
)
def test_downstream_classes_follow_frozen_precedence(
    topology_count: int,
    total: int,
    coverage: tuple[float, float],
    brier: tuple[float, float],
    expected: str,
) -> None:
    outcome = benchmark.classify_downstream(
        topology_success_count=topology_count,
        validation_count=total,
        calibrated_coverage=EstimateInterval(0.95, *coverage),
        paired_brier_interval=EstimateInterval(-0.05, *brier),
    )

    assert outcome == expected


def test_overall_class_precedence_separates_implementation_and_bank_instability() -> None:
    stable = (
        "advance_one_rate_stochastic_spread",
        "advance_one_rate_stochastic_spread",
        "advance_one_rate_stochastic_spread",
    )
    unstable = (
        "advance_one_rate_stochastic_spread",
        "rate_recoverable_mechanism_inconclusive",
        "advance_one_rate_stochastic_spread",
    )

    assert (
        benchmark.classify_outcome(invariants={"finite": False}, downstream_classes=unstable)
        == "implementation_blocked"
    )
    assert (
        benchmark.classify_outcome(invariants={"finite": True}, downstream_classes=unstable)
        == "likelihood_approximation_unstable"
    )
    assert (
        benchmark.classify_outcome(invariants={"finite": True}, downstream_classes=stable)
        == "advance_one_rate_stochastic_spread"
    )
