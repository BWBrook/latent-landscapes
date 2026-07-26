from __future__ import annotations

from dataclasses import replace

import numpy as np

from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal005 import benchmark


def tiny_config() -> benchmark.Goal005Config:
    return replace(
        benchmark.DEFAULT_CONFIG,
        bank_size=8,
        calibration_replicates=4,
        validation_replicates=3,
        calibration_rank_one_based=4,
    )


def test_truth_rates_and_exact_grid_indices() -> None:
    config = benchmark.DEFAULT_CONFIG
    assert config.truth_rates == (0.5, 1.0, 2.0)
    assert config.truth_indices == (150, 300, 450)


def test_seed_manifest_is_disjoint_replayable_and_rate_partitioned() -> None:
    manifest = benchmark.spawn_seed_manifest(tiny_config())
    assert len(manifest.integration_bank) == 8
    assert len(manifest.datasets) == 3 * (4 + 3)
    assert {d.truth_rate for d in manifest.datasets} == {0.5, 1.0, 2.0}
    streams = manifest.stream_records
    assert len({(s.entropy, s.spawn_key) for s in streams}) == len(streams)
    assert len({s.state_words for s in streams}) == len(streams)
    for stream in streams:
        first = benchmark.generator_from_seed_record(stream).random(5)
        second = benchmark.generator_from_seed_record(stream).random(5)
        assert np.array_equal(first, second)


def test_tiny_run_reuses_one_bank_and_separates_local_transport() -> None:
    result = benchmark.run_goal005(tiny_config())
    assert result.integration_bank.arrivals.shape == (8, 160)
    assert len(result.calibration_results) == 36
    assert len(result.validation_results) == 27
    assert len(result.cutoff_summaries) == 15
    assert all(result.invariants.values())
    assert {s.cutoff_source_rate for s in result.cutoff_summaries if s.transported} == {1.0}
    assert {s.truth_rate for s in result.cutoff_summaries if s.transported} == {0.5, 2.0}
    assert {row.cutoff_source_rate for row in result.validation_results} == {0.5, 1.0, 2.0}
    assert all(
        row.detection_fraction_lower <= row.detection_fraction_mean <= row.detection_fraction_upper
        for row in result.observation_signals
    )
    assert result.invariants["same_field_rate_scaling"]
    assert len(result.observation_signals) == 18


def test_class_precedence_includes_transport_failure() -> None:
    local = tuple(
        benchmark.CutoffSummary(
            truth_rate=truth,
            bank_variant=bank,
            cutoff_source_rate=1.0,
            cutoff=1.0,
            coverage_count=480,
            coverage=EstimateInterval(0.96, 0.94, 0.97),
            topology_count=500,
            boundary_contacts=0,
            mean_arithmetic_width=0.1,
            mean_log_rate_width=0.1,
            mean_abs_log_error=0.01,
            paired_brier=EstimateInterval(-0.1, -0.2, -0.01),
            downstream_class="advance_to_second_spread_parameter",
            transported=False,
        )
        for truth in (0.5, 1.0, 2.0)
        for bank in benchmark.BANK_VARIANT_NAMES
    )
    transported = tuple(
        benchmark.CutoffSummary(
            truth_rate=truth,
            bank_variant=bank,
            cutoff_source_rate=1.0,
            cutoff=1.0,
            coverage_count=100,
            coverage=EstimateInterval(0.2, 0.16, 0.25),
            topology_count=500,
            boundary_contacts=0,
            mean_arithmetic_width=0.1,
            mean_log_rate_width=0.1,
            mean_abs_log_error=0.01,
            paired_brier=EstimateInterval(-0.1, -0.2, -0.01),
            downstream_class="advance_to_second_spread_parameter",
            transported=True,
        )
        for truth in (0.5, 2.0)
        for bank in benchmark.BANK_VARIANT_NAMES
    )
    assert (
        benchmark.classify_outcome({"ok": True}, local + transported)
        == "one_rate_recovery_robust_cutoff_nontransportable"
    )
