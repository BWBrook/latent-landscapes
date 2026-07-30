from __future__ import annotations

import numpy as np

from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal011 import benchmark


def _tiny_config() -> benchmark.Goal011Config:
    return benchmark.Goal011Config(
        master_seed=20260730,
        bank_size=2,
        calibration_replicates=2,
        validation_replicates=2,
        calibration_rank_one_based=2,
        rhos=(0.5, 1.0, 2.0),
        etas=tuple(index / 4 for index in range(11)),
    )


def test_five_root_manifest_preserves_goal007_process_streams_exactly() -> None:
    config = _tiny_config()
    manifest = benchmark.spawn_seed_manifest(config)
    reference = goal007.spawn_seed_manifest(config.goal007_config)

    assert manifest.integration_bank == reference.integration_bank
    assert tuple(row.process for row in manifest.calibration) == reference.calibration
    assert tuple(row.process for row in manifest.validation) == reference.validation
    assert all(row.detection.stream_role == "detection" for row in manifest.calibration)
    assert all(row.detection.stream_role == "detection" for row in manifest.validation)
    streams = manifest.stream_records
    assert len({(row.entropy, row.spawn_key) for row in streams}) == len(streams)
    assert {
        row.spawn_key[0]
        for row in (*manifest.integration_bank, *(item.process for item in manifest.calibration))
    } <= {0, 1}
    assert {row.detection.spawn_key[0] for row in manifest.calibration} == {3}
    assert {row.detection.spawn_key[0] for row in manifest.validation} == {4}


def test_expanded_bank_replays_every_old_eta_slice_exactly() -> None:
    config = _tiny_config()
    fixed = benchmark.build_fixed_inputs()
    manifest = benchmark.spawn_seed_manifest(config)

    expanded, variants, replay = benchmark.build_integration_banks(
        config,
        fixed,
        manifest.integration_bank,
    )

    assert expanded.arrivals.shape == (2, 11, 160)
    assert replay.old_slices_equal is True
    assert replay.added_slices_finite is True
    assert tuple(variant.name for variant in variants) == goal007.BANK_VARIANT_NAMES
    assert tuple(variant.weights.shape for variant in variants) == (
        (11, 3, 160, 7),
        (11, 3, 160, 7),
        (11, 3, 160, 7),
    )


def test_dataset_retains_complete_disagreeing_visits_and_zero_false_positives() -> None:
    config = _tiny_config()
    fixed = benchmark.build_fixed_inputs()
    seed = benchmark.spawn_seed_manifest(config).calibration[0]

    truth, records = benchmark.generate_dataset(fixed, seed)

    assert len(records) == 1920
    assert sum(row.split == "training" for row in records) == 1440
    assert sum(row.split == "holdout" for row in records) == 480
    by_key = {(row.site_id, row.time, row.replicate): row.detected for row in records}
    assert len(by_key) == 1920
    assert any(
        by_key[(row.site_id, row.time, 1)] != by_key[(row.site_id, row.time, 2)]
        for row in records[::12]
        for _ in (0,)
    )
    assert benchmark.no_false_positives(records, truth)


def test_reduced_campaign_has_fresh_domain_cutoffs_and_non_gating_projection() -> None:
    result = benchmark.run_goal011(_tiny_config())

    assert len(result.calibration_results) == 2 * 3
    assert len(result.validation_results) == 2 * 3
    assert len(result.bank_summaries) == len(result.domain_comparisons) == 3
    assert all(row.record_count == 1920 for row in result.calibration_results)
    assert all(
        row.record_count == 1920
        and row.training_record_count == 1440
        and row.holdout_record_count == 480
        for row in result.validation_results
    )
    assert all(row.cutoff.sample_size == 2 for row in result.bank_summaries)
    assert all(row.old_domain_cutoff.sample_size == 2 for row in result.bank_summaries)
    assert all(
        row.expanded_downstream_class.startswith("joint_imperfect_detection_")
        or row.expanded_downstream_class == "advance_to_cross_truth_joint_imperfect_detection"
        for row in result.bank_summaries
    )
    assert result.outcome == benchmark.classify_outcome(
        invariants=result.invariants,
        downstream_classes=tuple(row.expanded_downstream_class for row in result.bank_summaries),
    )
    assert all(np.isfinite(row.expanded_cutoff) for row in result.domain_comparisons)
    assert all(np.isfinite(row.old_domain_cutoff) for row in result.domain_comparisons)
    assert all(result.invariants.values())


def test_goal011_decision_precedence_and_labels_are_frozen() -> None:
    interval = EstimateInterval(0.95, 0.93, 0.97)
    negative = EstimateInterval(-0.1, -0.2, -0.01)

    assert (
        benchmark.classify_downstream(
            topology_success_count=474,
            validation_count=500,
            calibrated_coverage=interval,
            median_absolute_log_rho_error=0.0,
            median_absolute_eta_error=0.0,
            median_projected_log_rho_width=0.0,
            median_projected_eta_width=0.0,
            paired_brier_interval=negative,
        )
        == "joint_imperfect_detection_design_limited"
    )
    assert (
        benchmark.classify_downstream(
            topology_success_count=500,
            validation_count=500,
            calibrated_coverage=interval,
            median_absolute_log_rho_error=0.0,
            median_absolute_eta_error=0.0,
            median_projected_log_rho_width=0.0,
            median_projected_eta_width=0.0,
            paired_brier_interval=negative,
        )
        == "advance_to_cross_truth_joint_imperfect_detection"
    )
    assert (
        benchmark.classify_outcome(
            invariants={"seed_replay": False},
            downstream_classes=("advance_to_cross_truth_joint_imperfect_detection",) * 3,
        )
        == "implementation_blocked"
    )
    assert (
        benchmark.classify_outcome(
            invariants={"seed_replay": True},
            downstream_classes=(
                "joint_imperfect_detection_design_limited",
                "joint_imperfect_detection_recovery_imprecise",
                "joint_imperfect_detection_design_limited",
            ),
        )
        == "likelihood_approximation_unstable"
    )
