from __future__ import annotations

import errno
import os
import pickle
import shutil
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes import cross_truth
from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal013 import benchmark


def _hardlink_or_copy(source: str, destination: str) -> None:
    try:
        os.link(source, destination)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        shutil.copy2(source, destination)


def tiny_config() -> benchmark.Goal013Config:
    return benchmark.Goal013Config(
        cross_truth_config=cross_truth.CrossTruthConfig(
            master_seed=20260730,
            bank_size=2,
            calibration_blocks=2,
            validation_blocks=2,
            calibration_rank_one_based=2,
            rhos=(0.5, 1.0, 2.0),
        )
    )


def _interval(estimate: float, lower: float, upper: float) -> EstimateInterval:
    return EstimateInterval(estimate=estimate, lower=lower, upper=upper)


def _classes(value: str = "cell_recoverable") -> dict[str, dict[str, str]]:
    return {
        cell: {bank: value for bank in benchmark.BANK_VARIANT_NAMES}
        for cell in benchmark.TARGET_CELL_IDS
    }


def _comparisons(
    *,
    baseline: int = 100,
    intervention: int = 70,
    interval: EstimateInterval | None = None,
) -> dict[str, benchmark.BaselineInterventionComparison]:
    difference = interval or _interval(-0.06, -0.10, -0.02)
    return {
        cell: benchmark.BaselineInterventionComparison(
            truth_cell=cell,
            truth_rho={"cell-00": 0.5, "cell-01": 1.0, "cell-02": 2.0}[cell],
            truth_eta=0.5,
            bank_variant="full",
            validation_blocks=500,
            baseline_eta_zero_contact_count=baseline,
            intervention_eta_zero_contact_count=intervention,
            contact_count_difference=intervention - baseline,
            block_indicator_difference=difference,
        )
        for cell in benchmark.WEAK_CELL_IDS
    }


def test_authenticates_and_recomputes_both_accepted_weak_contrast_packs(
    tmp_path: Path,
) -> None:
    evidence = benchmark.authenticate_existing_evidence()

    assert len(evidence.rows) == 6
    assert all(evidence.invariants.values())
    assert evidence.goal009.truth_cell_summary_sha256 == (
        "bc4fce39bd3e2e0ca034089d0a800623e278783c4e88d7d6b75dacdd44599096"
    )
    assert evidence.goal012.truth_cell_summary_sha256 == (
        "40b1481af552b94573de4379d727fc1223ed08c6b6d8f1214117cfd9e01f34c9"
    )
    assert {
        (row.source_goal, row.truth_cell): row.full_bank_eta_zero_contact_count
        for row in evidence.rows
    } == {
        ("009", "cell-00"): 222,
        ("009", "cell-01"): 144,
        ("009", "cell-02"): 109,
        ("012", "cell-00"): 249,
        ("012", "cell-01"): 155,
        ("012", "cell-02"): 171,
    }
    assert {
        row.observation_representation for row in evidence.rows if row.source_goal == "009"
    } == {"perfect_detection_collapsed_site_time_outcomes"}
    assert {
        row.observation_representation for row in evidence.rows if row.source_goal == "012"
    } == {"complete_two_visit_histories_known_p_0.65"}
    assert all(len(row.bank_classes) == 3 for row in evidence.rows)

    tampered = tmp_path / "goal012-tampered"
    shutil.copytree(
        benchmark.DEFAULT_GOAL012_EVIDENCE_DIR,
        tampered,
        copy_function=_hardlink_or_copy,
    )
    summary = tampered / "truth_cell_summary.csv"
    original = summary.read_text(encoding="utf-8")
    summary.unlink()
    summary.write_text(original.replace("cell_design_limited", "cell_recoverable", 1))
    with pytest.raises(ValueError, match=r"hash mismatch|published Goal012 identity"):
        benchmark.authenticate_existing_evidence(goal012_evidence_dir=tampered)


def test_nine_root_manifest_preserves_goal012_and_appends_disjoint_detection() -> None:
    config = tiny_config().cross_truth_config
    observed = benchmark.spawn_seed_manifest(config)
    baseline = cross_truth.spawn_seed_manifest(config)

    assert observed.baseline == baseline
    assert observed.intervention.integration_bank == baseline.integration_bank
    assert tuple(row.process for row in observed.intervention.calibration) == tuple(
        row.process for row in baseline.calibration
    )
    assert tuple(row.process for row in observed.intervention.validation) == tuple(
        row.process for row in baseline.validation
    )
    assert all(
        tuple(item.truth_cell for item in block.cell_detection) == benchmark.TARGET_CELL_IDS
        for block in (*observed.intervention.calibration, *observed.intervention.validation)
    )
    assert {
        item.detection.spawn_key[0]
        for block in observed.intervention.calibration
        for item in block.cell_detection
    } == {7}
    assert {
        item.detection.spawn_key[0]
        for block in observed.intervention.validation
        for item in block.cell_detection
    } == {8}
    assert len({(row.entropy, row.spawn_key) for row in observed.all_stream_records}) == len(
        observed.all_stream_records
    )
    assert len({row.state_words for row in observed.all_stream_records}) == len(
        observed.all_stream_records
    )


def test_reduced_campaign_runs_only_four_cells_with_local_cutoffs_and_comparisons() -> None:
    result = benchmark.run_campaign(tiny_config(), workers=1)
    parallel = benchmark.run_campaign(tiny_config(), workers=2)

    assert tuple(result.cell_invariants) == benchmark.TARGET_CELL_IDS
    assert tuple(parallel.cell_invariants) == benchmark.TARGET_CELL_IDS
    assert (
        tuple(row.truth_cell for row in parallel.execution_telemetry.cell_telemetry)
        == benchmark.TARGET_CELL_IDS
    )
    assert benchmark.campaign_digest(result) == benchmark.campaign_digest(parallel)
    assert len(result.calibration_results) == 4 * 3 * 2
    assert len(result.validation_results) == 4 * 3 * 2
    assert len(result.truth_cell_summaries) == 4 * 3
    assert len(result.observation_signal_summary) == 4 * 6
    assert len(result.representative_profiles) == 4 * 3
    assert len(result.baseline_intervention_comparisons) == 3 * 3
    assert result.outcome != "implementation_blocked"
    assert all(result.invariants.values())
    assert not any(key.startswith("frozen_") for key in result.invariants)
    assert "accepted_goal012_commit_is_ancestor" not in result.invariants
    assert "goal012_predecessor_sources_reconciled" not in result.invariants
    assert all(
        row.cutoff_source_cell == row.truth_cell
        and row.cutoff.sample_size == 2
        and row.old_domain_cutoff.sample_size == 2
        for row in result.truth_cell_summaries
    )
    assert all(row.validation_blocks == 2 for row in result.baseline_intervention_comparisons)
    assert {row.truth_cell for row in result.baseline_intervention_comparisons} == set(
        benchmark.WEAK_CELL_IDS
    )


def test_first_match_decision_precedence_is_frozen() -> None:
    classes = _classes()
    artificial = {
        (cell, bank): 0
        for cell in benchmark.TARGET_CELL_IDS
        for bank in benchmark.BANK_VARIANT_NAMES
    }
    comparisons = _comparisons()

    assert (
        benchmark.classify_outcome({"all": False}, classes, artificial, comparisons)
        == "implementation_blocked"
    )
    unstable = {cell: banks.copy() for cell, banks in classes.items()}
    unstable["cell-00"]["second_half"] = "cell_design_limited"
    assert (
        benchmark.classify_outcome({"all": True}, unstable, artificial, comparisons)
        == "likelihood_approximation_unstable"
    )
    artificial[("cell-00", "full")] = 26
    assert (
        benchmark.classify_outcome({"all": True}, classes, artificial, comparisons)
        == "intervention_candidate_domain_unclosed"
    )
    artificial[("cell-00", "full")] = 0
    invalid_central = {cell: banks.copy() for cell, banks in classes.items()}
    invalid_central["cell-04"] = {
        bank: "cell_design_limited" for bank in benchmark.BANK_VARIANT_NAMES
    }
    assert (
        benchmark.classify_outcome({"all": True}, invalid_central, artificial, comparisons)
        == "intervention_invalidates_central_positive_control"
    )
    assert (
        benchmark.classify_outcome({"all": True}, classes, artificial, comparisons)
        == "contrast_balanced_design_restores_low_eta_recovery"
    )
    contributing = {cell: banks.copy() for cell, banks in classes.items()}
    contributing["cell-01"] = {bank: "cell_design_limited" for bank in benchmark.BANK_VARIANT_NAMES}
    assert (
        benchmark.classify_outcome({"all": True}, contributing, artificial, comparisons)
        == "contrast_balancing_contributes_not_resolves"
    )
    weak_difference = _comparisons(intervention=76)
    assert (
        benchmark.classify_outcome({"all": True}, contributing, artificial, weak_difference)
        == "contrast_balancing_not_supported"
    )


def test_cross_truth_default_runner_matches_injected_inputs_and_singleton_truth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = tiny_config().cross_truth_config
    cell = next(row for row in config.resolved_truth_cells if row.cell_id == "cell-04")
    fixed = cross_truth.build_fixed_inputs()
    manifest = cross_truth.spawn_seed_manifest(config)

    default = cross_truth.run_truth_cell(cell, config)

    def fail_default_builder(*args: object, **kwargs: object) -> None:
        raise AssertionError("explicit cross-truth inputs fell through to a default builder")

    monkeypatch.setattr(cross_truth, "build_fixed_inputs", fail_default_builder)
    monkeypatch.setattr(cross_truth, "spawn_seed_manifest", fail_default_builder)
    injected = cross_truth.run_truth_cell(
        cell,
        config,
        fixed_inputs=fixed,
        seed_manifest=manifest,
    )
    assert pickle.dumps(default, protocol=5) == pickle.dumps(injected, protocol=5)

    block = manifest.calibration[0]
    all_truth = dict(
        cross_truth.generate_truth_block(fixed, block.process, config.resolved_truth_cells)
    )[cell]
    singleton_truth = dict(cross_truth.generate_truth_block(fixed, block.process, (cell,)))[cell]
    assert np.array_equal(all_truth.arrival, singleton_truth.arrival)
    assert np.array_equal(all_truth.edge_shocks, singleton_truth.edge_shocks)
