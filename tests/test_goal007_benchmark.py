from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal004.likelihood import PredictiveScore
from latent_landscapes.goal006.spread import (
    compute_paired_spreads,
    sample_edge_shock_vector,
)
from latent_landscapes.goal007 import benchmark


def _config() -> benchmark.Goal007Config:
    return benchmark.Goal007Config(
        master_seed=73,
        bank_size=4,
        calibration_replicates=3,
        validation_replicates=2,
        calibration_rank_one_based=3,
        rhos=(0.5, 1.0, 2.0),
        etas=(0.0, 1.0, 2.0),
    )


def test_seed_manifest_has_three_disjoint_process_only_phases() -> None:
    config = _config()

    manifest = benchmark.spawn_seed_manifest(config)

    assert len(manifest.integration_bank) == 4
    assert len(manifest.calibration) == 3
    assert len(manifest.validation) == 2
    assert [record.phase for record in manifest.stream_records] == [
        *(["integration_bank"] * 4),
        *(["calibration"] * 3),
        *(["validation"] * 2),
    ]
    assert {record.stream_role for record in manifest.stream_records} == {
        "paired_eta_process",
        "central_truth_process",
    }
    assert all("detection" not in record.stream_role for record in manifest.stream_records)
    assert len({record.spawn_key for record in manifest.stream_records}) == 9
    for record in manifest.stream_records:
        first = benchmark.generator_from_seed_record(record).random(4)
        second = benchmark.generator_from_seed_record(record).random(4)
        assert np.array_equal(first, second)


def test_integration_bank_reuses_one_shock_vector_across_eta() -> None:
    config = _config()
    fixed = benchmark.build_fixed_inputs()
    manifest = benchmark.spawn_seed_manifest(config)

    bank = benchmark.build_integration_bank(fixed, manifest.integration_bank, config.etas)

    assert bank.arrivals.shape == (4, 3, 160)
    rng = benchmark.generator_from_seed_record(manifest.integration_bank[0])
    shocks = sample_edge_shock_vector(fixed.landscape, rng)
    _, truths = compute_paired_spreads(
        fixed.landscape,
        edge_shocks=shocks,
        etas=config.etas,
        rho=1.0,
    )
    rows = np.asarray([site.row for site in fixed.design.sites])
    cols = np.asarray([site.col for site in fixed.design.sites])
    replay = np.stack([truth.arrival[rows, cols] for truth in truths])
    assert np.array_equal(bank.arrivals[0], replay)
    assert not np.array_equal(bank.arrivals[0, 0], bank.arrivals[0, 1])


def test_downstream_gate_precedence_and_overall_bank_stability() -> None:
    contains_095 = EstimateInterval(0.95, 0.92, 0.97)
    misses_095 = EstimateInterval(0.80, 0.75, 0.84)
    below_zero = EstimateInterval(-0.02, -0.03, -0.01)

    assert (
        benchmark.classify_downstream(
            topology_success_count=474,
            validation_count=500,
            calibrated_coverage=contains_095,
            median_absolute_log_rho_error=0.0,
            median_absolute_eta_error=0.0,
            median_projected_log_rho_width=0.0,
            median_projected_eta_width=0.0,
            paired_brier_interval=below_zero,
        )
        == "joint_design_limited"
    )
    assert (
        benchmark.classify_downstream(
            topology_success_count=500,
            validation_count=500,
            calibrated_coverage=misses_095,
            median_absolute_log_rho_error=0.0,
            median_absolute_eta_error=0.0,
            median_projected_log_rho_width=0.0,
            median_projected_eta_width=0.0,
            paired_brier_interval=below_zero,
        )
        == "joint_local_calibration_not_ready"
    )
    assert (
        benchmark.classify_downstream(
            topology_success_count=500,
            validation_count=500,
            calibrated_coverage=contains_095,
            median_absolute_log_rho_error=0.11,
            median_absolute_eta_error=0.0,
            median_projected_log_rho_width=0.0,
            median_projected_eta_width=0.0,
            paired_brier_interval=below_zero,
        )
        == "joint_recovery_imprecise"
    )
    assert (
        benchmark.classify_downstream(
            topology_success_count=500,
            validation_count=500,
            calibrated_coverage=contains_095,
            median_absolute_log_rho_error=0.0,
            median_absolute_eta_error=0.0,
            median_projected_log_rho_width=0.0,
            median_projected_eta_width=0.0,
            paired_brier_interval=below_zero,
        )
        == "advance_to_joint_cross_truth_perfect_detection"
    )
    assert (
        benchmark.classify_outcome(
            invariants={"all": True},
            downstream_classes=("a", "a", "a"),
        )
        == "a"
    )
    assert (
        benchmark.classify_outcome(
            invariants={"all": True},
            downstream_classes=("a", "b", "a"),
        )
        == "likelihood_approximation_unstable"
    )
    assert (
        benchmark.classify_outcome(
            invariants={"all": False},
            downstream_classes=("a", "a", "a"),
        )
        == "implementation_blocked"
    )


def test_predictive_summary_uses_worst_tied_mle_brier() -> None:
    scores = (
        PredictiveScore(-3.0, 0.10, 4, 0.1, 0.8),
        PredictiveScore(-4.0, 0.20, 4, 0.2, 0.9),
    )
    neutral = benchmark.BaselineScore(-5.0, 0.15, 4)

    summary = benchmark.summarize_predictive_comparison(scores, neutral)

    assert summary.stochastic_brier_maximum == 0.20
    assert summary.paired_brier_difference == pytest.approx(0.05)


def test_small_end_to_end_run_preserves_scientifically_negative_outcomes() -> None:
    result = benchmark.run_goal007(_config())

    assert result.outcome != "implementation_blocked"
    assert len(result.calibration_results) == 3 * 3
    assert len(result.validation_results) == 2 * 3
    assert len(result.bank_summaries) == 3
    assert len(result.representative_profiles) == 3
    assert all(result.invariants.values())
    assert all(row.analyst_record_count == 1920 for row in result.calibration_results)
    assert all(row.distinct_outcome_count == 960 for row in result.calibration_results)
    assert all(row.training_outcome_count == 720 for row in result.validation_results)
    assert all(row.holdout_outcome_count == 240 for row in result.validation_results)
    assert (
        benchmark.classify_outcome(
            invariants=result.invariants,
            downstream_classes=tuple(
                replace(summary, downstream_class="joint_design_limited").downstream_class
                for summary in result.bank_summaries
            ),
        )
        == "joint_design_limited"
    )
