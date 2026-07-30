from __future__ import annotations

from dataclasses import replace

import numpy as np

from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal004.observations import DETECTION_PROBABILITY
from latent_landscapes.goal008 import benchmark as goal008
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal012 import benchmark


def tiny_config() -> benchmark.Goal012Config:
    return benchmark.Goal012Config(
        master_seed=20260730,
        bank_size=2,
        calibration_blocks=2,
        validation_blocks=2,
        calibration_rank_one_based=2,
        rhos=(0.5, 1.0, 2.0),
    )


def _interval(estimate: float, lower: float, upper: float) -> EstimateInterval:
    return EstimateInterval(estimate=estimate, lower=lower, upper=upper)


def _stable_classes(
    full_class: str = "cell_recoverable",
) -> dict[str, dict[str, str]]:
    return {
        cell.cell_id: {bank: full_class for bank in benchmark.BANK_VARIANT_NAMES}
        for cell in benchmark.TRUTH_CELLS
    }


def _cell_decision(
    *,
    artificial_face_contact_count: int = 0,
    physical_topology_success_count: int = 500,
    calibrated_coverage: EstimateInterval,
    median_absolute_eta_error: float = 0.0,
    paired_brier_interval: EstimateInterval,
) -> benchmark.CellDecision:
    return benchmark.classify_cell(
        artificial_face_contact_count=artificial_face_contact_count,
        physical_topology_success_count=physical_topology_success_count,
        validation_count=500,
        calibrated_coverage=calibrated_coverage,
        median_absolute_log_rho_error=0.0,
        median_absolute_eta_error=median_absolute_eta_error,
        median_projected_log_rho_width=0.0,
        median_projected_eta_width=0.0,
        paired_brier_interval=paired_brier_interval,
    )


def test_truth_grid_and_seven_root_seed_identity_are_exact() -> None:
    config = tiny_config()
    manifest = benchmark.spawn_seed_manifest(config)
    central = goal011.spawn_seed_manifest(config.goal011_config)

    assert tuple(
        (cell.cell_id, cell.rho, cell.eta, cell.rho_index, cell.eta_index)
        for cell in benchmark.TRUTH_CELLS
    ) == (
        ("cell-00", 0.5, 0.5, 150, 2),
        ("cell-01", 1.0, 0.5, 300, 2),
        ("cell-02", 2.0, 0.5, 450, 2),
        ("cell-03", 0.5, 1.0, 150, 4),
        ("cell-04", 1.0, 1.0, 300, 4),
        ("cell-05", 2.0, 1.0, 450, 4),
        ("cell-06", 0.5, 1.5, 150, 6),
        ("cell-07", 1.0, 1.5, 300, 6),
        ("cell-08", 2.0, 1.5, 450, 6),
    )
    assert manifest.integration_bank == central.integration_bank
    assert tuple(row.process for row in manifest.calibration) == tuple(
        row.process for row in central.calibration
    )
    assert tuple(row.process for row in manifest.validation) == tuple(
        row.process for row in central.validation
    )
    assert tuple(row.detection_for("cell-04") for row in manifest.calibration) == tuple(
        row.detection for row in central.calibration
    )
    assert tuple(row.detection_for("cell-04") for row in manifest.validation) == tuple(
        row.detection for row in central.validation
    )
    assert {record.spawn_key[0] for record in manifest.integration_bank} == {0}
    assert {row.process.spawn_key[0] for row in manifest.calibration} == {1}
    assert {row.process.spawn_key[0] for row in manifest.validation} == {2}
    assert {row.detection_for("cell-04").spawn_key[0] for row in manifest.calibration} == {3}
    assert {row.detection_for("cell-04").spawn_key[0] for row in manifest.validation} == {4}
    assert {
        item.detection.spawn_key[0]
        for row in manifest.calibration
        for item in row.cell_detection
        if item.truth_cell != "cell-04"
    } == {5}
    assert {
        item.detection.spawn_key[0]
        for row in manifest.validation
        for item in row.cell_detection
        if item.truth_cell != "cell-04"
    } == {6}
    streams = manifest.stream_records
    assert len({(row.entropy, row.spawn_key) for row in streams}) == len(streams)
    assert len({row.state_words for row in streams}) == len(streams)


def test_process_block_scaling_and_cell04_process_detection_replay() -> None:
    config = tiny_config()
    fixed = benchmark.build_fixed_inputs()
    block = benchmark.spawn_seed_manifest(config).calibration[0]
    truths = benchmark.generate_truth_block(fixed, block.process)
    by_cell = {cell.cell_id: truth for cell, truth in truths}

    assert all(
        np.array_equal(truth.edge_shocks, by_cell["cell-00"].edge_shocks)
        for truth in by_cell.values()
    )
    assert np.array_equal(by_cell["cell-01"].arrival, by_cell["cell-00"].arrival / 2.0)
    assert np.array_equal(by_cell["cell-02"].arrival, by_cell["cell-00"].arrival / 4.0)
    assert not np.array_equal(by_cell["cell-00"].arrival, by_cell["cell-03"].arrival)

    central_seed = goal011.spawn_seed_manifest(config.goal011_config).calibration[0]
    expected_truth, expected_records = goal011.generate_dataset(fixed, central_seed)
    observed_records = benchmark.generate_cell_observations(
        fixed,
        by_cell["cell-04"],
        block.detection_for("cell-04"),
    )
    assert np.array_equal(by_cell["cell-04"].arrival, expected_truth.arrival)
    assert observed_records == expected_records


def test_noncentral_detection_streams_are_unique_and_visits_are_complete() -> None:
    config = tiny_config()
    fixed = benchmark.build_fixed_inputs()
    block = benchmark.spawn_seed_manifest(config).validation[0]
    truths = benchmark.generate_truth_block(fixed, block.process)

    detections = tuple(item.detection for item in block.cell_detection)
    assert len(detections) == 9
    assert len({(row.entropy, row.spawn_key) for row in detections}) == 9
    signatures: list[tuple[int, ...]] = []
    for cell, truth in truths:
        records = benchmark.generate_cell_observations(
            fixed,
            truth,
            block.detection_for(cell.cell_id),
        )
        assert len(records) == 1920
        assert sum(row.split == "training" for row in records) == 1440
        assert sum(row.split == "holdout" for row in records) == 480
        assert benchmark.no_false_positives(records, truth)
        signatures.append(tuple(row.detected for row in records))
    assert len(set(signatures)) > 1


def test_reduced_campaign_uses_local_dual_domain_cutoffs_and_truth_coordinates() -> None:
    result = benchmark.run_campaign(tiny_config(), workers=1)

    assert len(result.calibration_results) == 9 * 3 * 2
    assert len(result.validation_results) == 9 * 3 * 2
    assert len(result.truth_cell_summaries) == 9 * 3
    assert len(result.representative_profiles) == 9 * 3
    assert len(result.observation_signal_summary) == 9 * 6
    assert result.outcome != "implementation_blocked"
    assert all(result.invariants.values())
    for summary in result.truth_cell_summaries:
        assert summary.cutoff_source_cell == summary.truth_cell
        assert summary.cutoff.sample_size == 2
        assert summary.old_domain_cutoff.sample_size == 2
        assert summary.cutoff.rank_one_based == 2
        assert summary.old_domain_cutoff.rank_one_based == 2
        assert summary.expanded_candidate_domain_unclosed is (
            summary.artificial_face_contact_count > 25
        )
        assert summary.expanded_design_limited is (
            summary.expanded_physical_topology_success_count < 2
        )
    for representative in result.representative_profiles:
        assert representative.expanded_summary.truth_included is (
            (
                representative.truth_eta_index,
                representative.truth_rho_index,
            )
            in representative.expanded_summary.support_indices
        )
        assert representative.old_domain_summary.truth_included is (
            (
                representative.truth_eta_index,
                representative.truth_rho_index,
            )
            in representative.old_domain_summary.support_indices
        )


def test_cell_and_overall_precedence_separate_artificial_and_physical_limits() -> None:
    contains_095 = _interval(0.95, 0.92, 0.97)
    misses_095 = _interval(0.80, 0.75, 0.84)
    below_zero = _interval(-0.02, -0.03, -0.01)
    above_zero = _interval(0.02, 0.01, 0.03)
    overlaps_zero = _interval(0.0, -0.01, 0.01)

    artificial = _cell_decision(
        artificial_face_contact_count=26,
        calibrated_coverage=contains_095,
        paired_brier_interval=below_zero,
    )
    assert artificial.outcome == "cell_candidate_domain_unclosed"
    assert artificial.candidate_domain_unclosed is True
    assert artificial.design_limited is False
    physical = _cell_decision(
        physical_topology_success_count=474,
        calibrated_coverage=contains_095,
        paired_brier_interval=below_zero,
    )
    assert physical.outcome == "cell_design_limited"
    assert physical.candidate_domain_unclosed is False
    assert physical.design_limited is True
    assert (
        _cell_decision(
            calibrated_coverage=misses_095,
            paired_brier_interval=below_zero,
        ).outcome
        == "cell_local_calibration_not_ready"
    )
    assert (
        _cell_decision(
            calibrated_coverage=contains_095,
            median_absolute_eta_error=0.26,
            paired_brier_interval=below_zero,
        ).outcome
        == "cell_recovery_imprecise"
    )
    assert (
        _cell_decision(
            calibrated_coverage=contains_095,
            paired_brier_interval=above_zero,
        ).outcome
        == "cell_neutral_better"
    )
    assert (
        _cell_decision(
            calibrated_coverage=contains_095,
            paired_brier_interval=overlaps_zero,
        ).outcome
        == "cell_mechanism_inconclusive"
    )
    assert (
        _cell_decision(
            calibrated_coverage=contains_095,
            paired_brier_interval=below_zero,
        ).outcome
        == "cell_recoverable"
    )

    stable = _stable_classes()
    assert benchmark.classify_overall({"all": False}, stable) == "implementation_blocked"
    unstable = {cell: banks.copy() for cell, banks in stable.items()}
    unstable["cell-00"]["second_half"] = "cell_recovery_imprecise"
    assert (
        benchmark.classify_overall({"all": True}, unstable) == "likelihood_approximation_unstable"
    )
    expected = (
        ("cell_candidate_domain_unclosed", "cross_truth_candidate_domain_unclosed"),
        ("cell_design_limited", "cross_truth_design_limited"),
        ("cell_local_calibration_not_ready", "cross_truth_local_calibration_not_ready"),
        ("cell_recovery_imprecise", "cross_truth_recovery_imprecise"),
        ("cell_neutral_better", "cross_truth_neutral_better"),
        ("cell_mechanism_inconclusive", "cross_truth_mechanism_inconclusive"),
    )
    for cell_class, overall in expected:
        classes = _stable_classes()
        classes["cell-08"] = {bank: cell_class for bank in benchmark.BANK_VARIANT_NAMES}
        assert benchmark.classify_overall({"all": True}, classes) == overall
    assert benchmark.classify_overall({"all": True}, stable) == (
        "cross_truth_joint_known_detection_recoverable"
    )


def test_worker_count_does_not_change_scientific_order_or_digest() -> None:
    sequential = benchmark.run_campaign(tiny_config(), workers=1)
    parallel = benchmark.run_campaign(tiny_config(), workers=2)

    expected_order = tuple(cell.cell_id for cell in benchmark.TRUTH_CELLS)
    assert tuple(sequential.cell_invariants) == expected_order
    assert tuple(row.truth_cell for row in sequential.execution_telemetry.cell_telemetry) == (
        expected_order
    )
    assert benchmark.campaign_digest(sequential) == benchmark.campaign_digest(parallel)
    altered = replace(
        sequential,
        execution_telemetry=replace(
            sequential.execution_telemetry,
            worker_count=99,
        ),
    )
    assert benchmark.campaign_digest(sequential) == benchmark.campaign_digest(altered)


def test_cell04_result_reconciles_independent_goal011_public_path() -> None:
    config = tiny_config()
    result = benchmark.run_campaign(config, workers=1)
    reference = goal011.run_goal011(config.goal011_config)
    central = result.central_reconciliation

    assert central.truth_cell == "cell-04"
    assert central.production_reference_checked is False
    assert central.production_reference_match is None
    assert all(central.checks.values())
    assert central.goal011_outcome == reference.outcome
    central_calibration = tuple(
        row for row in result.calibration_results if row.truth_cell == "cell-04"
    )
    central_validation = tuple(
        row for row in result.validation_results if row.truth_cell == "cell-04"
    )
    assert benchmark.goal011_calibration_projection(central_calibration) == (
        reference.calibration_results
    )
    assert benchmark.goal011_validation_projection(central_validation) == (
        reference.validation_results
    )
    assert tuple(
        row.expanded_downstream_class
        for row in benchmark.goal011_summary_projection(
            tuple(row for row in result.truth_cell_summaries if row.truth_cell == "cell-04")
        )
    ) == tuple(row.expanded_downstream_class for row in reference.bank_summaries)
    assert DETECTION_PROBABILITY == benchmark.DETECTION_PROBABILITY == 0.65
    assert goal008.TRUTH_CELLS == benchmark.TRUTH_CELLS
