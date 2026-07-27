from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal003.spread import compute_stochastic_spread
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal008 import benchmark


def _tiny_truth_cells() -> tuple[benchmark.TruthCell, ...]:
    return tuple(
        benchmark.TruthCell(
            cell_id=f"cell-{eta_index * 3 + rho_index:02d}",
            rho=rho,
            eta=eta,
            rho_index=rho_index,
            eta_index=eta_index,
        )
        for eta_index, eta in ((0, 0.5), (1, 1.0), (2, 1.5))
        for rho_index, rho in enumerate((0.5, 1.0, 2.0))
    )


def tiny_config() -> benchmark.Goal008Config:
    return benchmark.Goal008Config(
        master_seed=83,
        bank_size=2,
        calibration_blocks=2,
        validation_blocks=2,
        calibration_rank_one_based=2,
        rhos=(0.5, 1.0, 2.0),
        etas=(0.5, 1.0, 1.5),
        truth_cells=_tiny_truth_cells(),
    )


def _interval(estimate: float, lower: float, upper: float) -> EstimateInterval:
    return EstimateInterval(estimate=estimate, lower=lower, upper=upper)


def _stable_classes(
    full_class: str = "cell_joint_recoverable",
) -> dict[str, dict[str, str]]:
    return {
        cell.cell_id: {bank: full_class for bank in benchmark.BANK_VARIANT_NAMES}
        for cell in benchmark.TRUTH_CELLS
    }


def test_frozen_truth_grid_is_exact_row_major_with_candidate_indices() -> None:
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


def test_seed_tree_replays_goal007_and_keeps_outer_phases_disjoint() -> None:
    config = tiny_config()

    observed = benchmark.spawn_seed_manifest(config)
    expected = goal007.spawn_seed_manifest(benchmark.goal007_config(config))

    assert observed == expected
    assert len(observed.integration_bank) == 2
    assert len(observed.calibration) == 2
    assert len(observed.validation) == 2
    assert {(record.entropy, record.spawn_key) for record in observed.calibration}.isdisjoint(
        {(record.entropy, record.spawn_key) for record in observed.validation}
    )
    for record in observed.stream_records:
        first = goal007.generator_from_seed_record(record).random(4)
        second = goal007.generator_from_seed_record(record).random(4)
        assert np.array_equal(first, second)


def test_truth_block_reuses_shocks_across_eta_and_scales_rho_exactly() -> None:
    config = tiny_config()
    fixed = goal007.build_fixed_inputs()
    seed = benchmark.spawn_seed_manifest(config).calibration[0]

    truths = benchmark.generate_truth_block(fixed, seed, config.truth_cells)
    by_cell = {cell.cell_id: truth for cell, truth in truths}

    assert all(
        np.array_equal(truth.edge_shocks, by_cell["cell-00"].edge_shocks)
        for truth in by_cell.values()
    )
    assert not np.array_equal(by_cell["cell-00"].arrival, by_cell["cell-03"].arrival)
    assert np.array_equal(
        by_cell["cell-01"].arrival,
        by_cell["cell-00"].arrival / 2.0,
    )
    assert np.array_equal(
        by_cell["cell-02"].arrival,
        by_cell["cell-00"].arrival / 4.0,
    )

    central = by_cell["cell-04"]
    replay = compute_stochastic_spread(
        fixed.landscape,
        goal007.generator_from_seed_record(seed),
        rho=1.0,
    )
    assert np.array_equal(central.arrival, replay.arrival)
    analyst, collapsed = benchmark.generate_cell_observations(fixed, central)
    assert len(analyst) == 1920
    assert len(collapsed) == 960
    assert all(
        row.detected == int(central.arrival[row.row, row.col] <= row.time) for row in collapsed
    )


def test_support_boundary_faces_are_deterministic_and_complete() -> None:
    assert benchmark.support_boundary_faces(
        ((0, 0), (0, 2), (1, 1), (2, 0), (2, 2)),
        eta_count=3,
        rho_count=3,
    ) == ("rho_min", "rho_max", "eta_min", "eta_max")
    assert (
        benchmark.support_boundary_faces(
            ((1, 1),),
            eta_count=3,
            rho_count=3,
        )
        == ()
    )


def test_platform_stable_projection_hashes_keep_structure_exact() -> None:
    value = 1.2345678912
    payload = {
        "row": 0,
        "identity": ["validation", "full"],
        "value": value,
        "nested": {"negative_zero": -0.0},
    }

    exact = benchmark.projection_hashes(payload)
    replay = benchmark.projection_hashes(payload)
    one_ulp = benchmark.projection_hashes(payload | {"value": float(np.nextafter(value, np.inf))})
    material = benchmark.projection_hashes(payload | {"value": value + 1e-6})
    structural = benchmark.projection_hashes(payload | {"row": 1})

    assert replay == exact
    assert one_ulp.raw_sha256 != exact.raw_sha256
    assert one_ulp.canonical_sha256 == exact.canonical_sha256
    assert one_ulp.structural_sha256 == exact.structural_sha256
    assert material.canonical_sha256 != exact.canonical_sha256
    assert structural.structural_sha256 != exact.structural_sha256
    assert (
        benchmark.projection_hashes({"value": -0.0}).canonical_sha256
        == benchmark.projection_hashes({"value": 0.0}).canonical_sha256
    )


def test_platform_stable_projection_rejects_nonfinite_values_with_paths() -> None:
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match=r"\$\.nested\[0\]"):
            benchmark.projection_hashes({"nested": [value]})


def test_reviewed_goal007_projection_constants_are_hardcoded() -> None:
    assert benchmark.CENTRAL_REFERENCE == {
        "historical_raw_hashes": {
            "calibration": "60b541649ad8fffa7bef0810c5246358c50dacf01027c2a6fa5bf6cbb5523f24",
            "validation": "ac559b76981b9962db4e537f725dd8c87b8348866e4c28000c7316348bb08439",
            "bank": "76168e5525ddf86f50c702c88ffff04206875de19acba12801c0d548dd788e3d",
        },
        "structural_hashes": {
            "calibration": "2da6de6fd746892c72e4ba7b2eff5174c494f33912f4b097c2d7ed3c64d916d7",
            "validation": "9edab67ef228a0e8ec634caae235e9f858f1fd461e5886dc0e113d5aa0acb173",
            "bank": "ef9510ad0bab11c6bc1f2b6281be485499343b66aac3ae7b98d4525d95af8971",
        },
        "canonical_hashes": {
            "calibration": "b2d157ce2ab0c2303f6a9cc9455c9c64f89275581eb9805ba745b0f03f9955b9",
            "validation": "bce714706ccf2ecdb9377d213ed54f17d37c3b0c30bb4b9ae11fada0351452f4",
            "bank": "5c5c97e2b3ab273f7976a0fda1285cb56c94d25a3a06803a2b835eb87c7cb5ce",
        },
        "seed_manifest_sha256": (
            "2b57f1eb90db41201d5a1311db168c7012953e4f6683bd5c37845ac7a0113aae"
        ),
        "source_identity_sha256": (
            "e4ff4b3a9db477b39137b85c44e9c2714abbdf1e338fe7b0a71d1b69c65850aa"
        ),
        "outcome": "advance_to_joint_cross_truth_perfect_detection",
    }


def test_central_phase_mutation_fails_the_real_reconciliation_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = benchmark.run_campaign(tiny_config(), workers=1)
    central_calibration = tuple(
        row for row in result.calibration_results if row.truth_cell == "cell-04"
    )
    central_validation = tuple(
        row for row in result.validation_results if row.truth_cell == "cell-04"
    )
    central_summaries = tuple(
        row for row in result.cell_bank_summaries if row.truth_cell == "cell-04"
    )
    payloads = {
        "calibration": [benchmark._central_calibration_payload(row) for row in central_calibration],
        "validation": [benchmark._central_validation_payload(row) for row in central_validation],
        "bank": [benchmark._central_bank_payload(row) for row in central_summaries],
    }
    hashes = {label: benchmark.projection_hashes(payload) for label, payload in payloads.items()}
    monkeypatch.setattr(
        benchmark,
        "CENTRAL_STRUCTURAL_HASHES",
        {label: projection.structural_sha256 for label, projection in hashes.items()},
    )
    monkeypatch.setattr(
        benchmark,
        "CENTRAL_CANONICAL_HASHES",
        {label: projection.canonical_sha256 for label, projection in hashes.items()},
    )
    reference = dict(benchmark.CENTRAL_REFERENCE)
    reference["seed_manifest_sha256"] = benchmark._projection_digest(
        benchmark._central_seed_payload(result.seed_manifest)
    )
    reference["source_identity_sha256"] = benchmark._projection_digest(benchmark.SOURCE_IDENTITY)
    reference["outcome"] = benchmark._central_outcome(central_summaries)
    monkeypatch.setattr(benchmark, "CENTRAL_REFERENCE", reference)
    monkeypatch.setattr(
        benchmark.Goal008Config,
        "is_production",
        property(lambda self: True),
    )
    source_invariants = {"frozen_source_blobs_reconciled": True}

    exact = benchmark._central_projection(
        result.config,
        result.calibration_results,
        result.validation_results,
        result.cell_bank_summaries,
        result.seed_manifest,
        source_invariants,
    )
    assert exact.production_reference_match is True

    mutated_calibration = list(result.calibration_results)
    central_index = next(
        index for index, row in enumerate(mutated_calibration) if row.truth_cell == "cell-04"
    )
    mutated_calibration[central_index] = replace(
        mutated_calibration[central_index],
        phase="validation",
    )
    mutated = benchmark._central_projection(
        result.config,
        tuple(mutated_calibration),
        result.validation_results,
        result.cell_bank_summaries,
        result.seed_manifest,
        source_invariants,
    )

    assert mutated.production_reference_match is False
    assert mutated.checks["calibration_structure"] is False
    assert mutated.checks["calibration_canonical"] is False
    assert all(
        passed
        for name, passed in mutated.checks.items()
        if name not in {"calibration_structure", "calibration_canonical"}
    )


def test_config_and_cell_entrypoint_reject_duplicate_or_unknown_cells() -> None:
    cells = _tiny_truth_cells()
    with pytest.raises(ValueError, match="unique"):
        replace(tiny_config(), truth_cells=(*cells[:-1], cells[0]))
    with pytest.raises(ValueError, match="row-major"):
        replace(tiny_config(), truth_cells=tuple(reversed(cells)))

    unknown = replace(cells[0], cell_id="cell-99")
    with pytest.raises(ValueError, match="not part of"):
        benchmark.run_truth_cell(unknown, tiny_config())


def test_cell_and_overall_decision_precedence_including_bank_instability() -> None:
    contains_095 = _interval(0.95, 0.92, 0.97)
    misses_095 = _interval(0.80, 0.75, 0.84)
    below_zero = _interval(-0.02, -0.03, -0.01)
    above_zero = _interval(0.02, 0.01, 0.03)
    overlaps_zero = _interval(0.0, -0.01, 0.01)

    assert benchmark.classify_cell(
        topology_success_count=474,
        validation_count=500,
        calibrated_coverage=contains_095,
        median_absolute_log_rho_error=0.0,
        median_absolute_eta_error=0.0,
        median_projected_log_rho_width=0.0,
        median_projected_eta_width=0.0,
        paired_brier_interval=below_zero,
    ) == ("cell_joint_design_limited")
    assert (
        benchmark.classify_cell(
            topology_success_count=500,
            validation_count=500,
            calibrated_coverage=misses_095,
            median_absolute_log_rho_error=0.0,
            median_absolute_eta_error=0.0,
            median_projected_log_rho_width=0.0,
            median_projected_eta_width=0.0,
            paired_brier_interval=below_zero,
        )
        == "cell_joint_local_calibration_not_ready"
    )
    assert (
        benchmark.classify_cell(
            topology_success_count=500,
            validation_count=500,
            calibrated_coverage=contains_095,
            median_absolute_log_rho_error=0.0,
            median_absolute_eta_error=0.26,
            median_projected_log_rho_width=0.0,
            median_projected_eta_width=0.0,
            paired_brier_interval=below_zero,
        )
        == "cell_joint_recovery_imprecise"
    )
    assert (
        benchmark.classify_cell(
            topology_success_count=500,
            validation_count=500,
            calibrated_coverage=contains_095,
            median_absolute_log_rho_error=0.0,
            median_absolute_eta_error=0.0,
            median_projected_log_rho_width=0.0,
            median_projected_eta_width=0.0,
            paired_brier_interval=above_zero,
        )
        == "cell_joint_neutral_better"
    )
    assert (
        benchmark.classify_cell(
            topology_success_count=500,
            validation_count=500,
            calibrated_coverage=contains_095,
            median_absolute_log_rho_error=0.0,
            median_absolute_eta_error=0.0,
            median_projected_log_rho_width=0.0,
            median_projected_eta_width=0.0,
            paired_brier_interval=overlaps_zero,
        )
        == "cell_joint_mechanism_inconclusive"
    )
    assert benchmark.classify_cell(
        topology_success_count=500,
        validation_count=500,
        calibrated_coverage=contains_095,
        median_absolute_log_rho_error=0.0,
        median_absolute_eta_error=0.0,
        median_projected_log_rho_width=0.0,
        median_projected_eta_width=0.0,
        paired_brier_interval=below_zero,
    ) == ("cell_joint_recoverable")

    stable = _stable_classes()
    assert benchmark.classify_overall({"all": False}, stable) == "implementation_blocked"
    unstable = {cell: banks.copy() for cell, banks in stable.items()}
    unstable["cell-00"]["second_half"] = "cell_joint_recovery_imprecise"
    assert benchmark.classify_overall({"all": True}, unstable) == (
        "likelihood_approximation_unstable"
    )
    expected = (
        ("cell_joint_design_limited", "joint_cross_truth_design_limited"),
        (
            "cell_joint_local_calibration_not_ready",
            "joint_cross_truth_local_calibration_not_ready",
        ),
        ("cell_joint_recovery_imprecise", "joint_cross_truth_recovery_imprecise"),
        ("cell_joint_neutral_better", "joint_cross_truth_neutral_better"),
        (
            "cell_joint_mechanism_inconclusive",
            "joint_cross_truth_mechanism_inconclusive",
        ),
    )
    for cell_class, overall_class in expected:
        classes = _stable_classes()
        classes["cell-08"] = {bank: cell_class for bank in benchmark.BANK_VARIANT_NAMES}
        assert benchmark.classify_overall({"all": True}, classes) == overall_class
    assert benchmark.classify_overall({"all": True}, stable) == (
        "advance_to_joint_imperfect_detection"
    )


def test_tiny_campaign_has_local_cutoffs_central_projection_and_worker_determinism() -> None:
    sequential = benchmark.run_campaign(tiny_config(), workers=1)
    parallel = benchmark.run_campaign(tiny_config(), workers=2)

    assert len(sequential.calibration_results) == 9 * 3 * 2
    assert len(sequential.validation_results) == 9 * 3 * 2
    assert len(sequential.cell_bank_summaries) == 9 * 3
    assert len(sequential.representative_profiles) == 9 * 3
    assert sequential.outcome != "implementation_blocked"
    assert all(sequential.invariants.values())
    assert tuple(sequential.cell_invariants) == tuple(
        cell.cell_id for cell in sequential.config.truth_cells
    )
    assert len(sequential.cell_invariants) == 9
    assert all(all(invariants.values()) for invariants in sequential.cell_invariants.values())
    assert benchmark.campaign_digest(sequential) == benchmark.campaign_digest(parallel)
    changed_telemetry = replace(
        sequential,
        execution_telemetry=replace(
            sequential.execution_telemetry,
            worker_count=99,
            cell_telemetry=tuple(
                replace(row, wall_time_seconds=123.0, maximum_rss_bytes=456)
                for row in sequential.execution_telemetry.cell_telemetry
            ),
        ),
    )
    assert benchmark.campaign_digest(sequential) == benchmark.campaign_digest(changed_telemetry)

    for summary in sequential.cell_bank_summaries:
        assert summary.cutoff_source_cell == summary.truth_cell
        assert summary.cutoff_source_rho == summary.truth_rho
        assert summary.cutoff_source_eta == summary.truth_eta
        assert summary.cutoff.sample_size == 2
        assert summary.cutoff.rank_one_based == 2
        cell_rows = tuple(
            row
            for row in sequential.validation_results
            if row.truth_cell == summary.truth_cell and row.bank_variant == summary.bank_variant
        )
        assert summary.rho_min_contact_count == sum(
            "rho_min" in row.support_boundary_faces for row in cell_rows
        )
        assert summary.rho_max_contact_count == sum(
            "rho_max" in row.support_boundary_faces for row in cell_rows
        )
        assert summary.eta_min_contact_count == sum(
            "eta_min" in row.support_boundary_faces for row in cell_rows
        )
        assert summary.eta_max_contact_count == sum(
            "eta_max" in row.support_boundary_faces for row in cell_rows
        )
    for row in sequential.validation_results:
        assert row.support_boundary_faces == benchmark.support_boundary_faces(
            row.support_indices,
            eta_count=len(sequential.config.etas),
            rho_count=len(sequential.config.rhos),
        )
        assert row.support_boundary_contact is bool(row.support_boundary_faces)
    assert {
        (summary.truth_cell, summary.bank_variant) for summary in sequential.cell_bank_summaries
    } == {
        (cell.cell_id, bank)
        for cell in tiny_config().truth_cells
        for bank in benchmark.BANK_VARIANT_NAMES
    }

    central = benchmark.central_projection(sequential)
    assert central.truth_cell == "cell-04"
    assert len(central.calibration_rows) == 2 * 3
    assert len(central.validation_rows) == 2 * 3
    assert len(central.bank_summaries) == 3
    assert central.production_reference_checked is False
    assert central.production_reference_match is None
    assert central.canonicalization_rule == {
        "finite_float_decimal_places": 9,
        "negative_zero": "normalized_to_positive_zero",
        "nonfinite": "rejected_before_canonicalization",
        "representation": "json_number_rounded_to_decimal_places",
    }
    assert set(central.raw_hashes) == {"calibration", "validation", "bank"}
    assert set(central.canonical_hashes) == {"calibration", "validation", "bank"}
    assert set(central.structural_hashes) == {"calibration", "validation", "bank"}
    assert central.nonfinite_paths == ()
    assert all(row.mle_indices and row.mle_cells for row in sequential.calibration_results)
    assert all(
        row.mle_indices and row.mle_cells and row.training_mle_indices and row.training_mle_cells
        for row in sequential.validation_results
    )
