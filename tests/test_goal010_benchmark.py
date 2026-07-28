from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest

from latent_landscapes.goal002.calibration import order_statistic_cutoff
from latent_landscapes.goal008 import (
    artifacts as goal008_artifacts,
)
from latent_landscapes.goal008 import (
    benchmark as goal008,
)
from latent_landscapes.goal010 import benchmark

PUBLISHED_GOAL009_PACK = Path(
    "artifacts/goal009_remote_runs/goal009-20260727T093142Z-9cb53de/scientific-pack"
)


def _small_cells(rhos: tuple[float, ...], etas: tuple[float, ...]) -> tuple[goal008.TruthCell, ...]:
    return tuple(
        goal008.TruthCell(
            cell_id=f"cell-{eta_row * 3 + rho_column:02d}",
            rho=rho,
            eta=eta,
            rho_index=rhos.index(rho),
            eta_index=etas.index(eta),
        )
        for eta_row, eta in enumerate((0.5, 1.0, 1.5))
        for rho_column, rho in enumerate((0.5, 1.0, 2.0))
    )


def _small_goal008_config() -> goal008.Goal008Config:
    rhos = (0.5, 1.0, 2.0)
    etas = tuple(float(value) for value in goal008.FROZEN_ETA_GRID)
    return goal008.Goal008Config(
        master_seed=goal008.MASTER_SEED,
        bank_size=2,
        calibration_blocks=2,
        validation_blocks=2,
        calibration_rank_one_based=2,
        rhos=rhos,
        etas=etas,
        truth_cells=_small_cells(rhos, etas),
    )


def _write_small_goal009_pack(target: Path) -> Path:
    result = goal008.run_campaign(_small_goal008_config(), workers=1)
    published_outcome = replace(result, outcome="joint_cross_truth_design_limited")
    goal008_artifacts.write_review_bundle(
        published_outcome,
        target,
        {
            "provenance_mode": "test",
            "run_id": "goal009-small-test",
            "host_id": "local-test-host",
        },
    )
    return target


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle))


def test_strict_goal009_reader_reconciles_hashes_rows_and_boundary_anatomy(
    tmp_path: Path,
) -> None:
    pack_path = _write_small_goal009_pack(tmp_path / "goal009")
    pack = benchmark.read_goal009_pack(pack_path, require_published=False)

    assert pack.outcome == "joint_cross_truth_design_limited"
    assert pack.truth_cell_order == tuple(f"cell-{index:02d}" for index in range(9))
    assert pack.bank_order == goal008.BANK_VARIANT_NAMES
    assert len(pack.calibration_rows) == 9 * 3 * 2
    assert len(pack.validation_rows) == 9 * 3 * 2
    assert len(pack.summary_rows) == 9 * 3
    assert pack.all_invariants_pass

    anatomy = benchmark.baseline_boundary_anatomy(pack)
    assert len(anatomy) == 27
    assert tuple((row.truth_cell, row.bank_variant) for row in anatomy) == tuple(
        (f"cell-{cell:02d}", bank) for cell in range(9) for bank in goal008.BANK_VARIANT_NAMES
    )
    assert tuple(row.truth_cell for row in anatomy[-9::3]) == (
        "cell-06",
        "cell-07",
        "cell-08",
    )

    validation_keys = tuple(
        (row["block_index"], row["truth_cell"], row["bank_variant"]) for row in pack.validation_rows
    )
    assert len(validation_keys) == len(set(validation_keys))

    (pack_path / "validation_results.csv").write_text(
        "tampered\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="hash"):
        benchmark.read_goal009_pack(pack_path, require_published=False)


def test_published_goal009_pack_passes_the_full_contract_when_available() -> None:
    if not PUBLISHED_GOAL009_PACK.is_dir():
        pytest.skip("ignored published Goal009 pack is not present")

    pack = benchmark.read_goal009_pack(PUBLISHED_GOAL009_PACK)

    assert pack.is_published_goal009
    assert pack.verification_sha256 == benchmark.PUBLISHED_GOAL009_VERIFICATION_SHA256
    assert len(pack.calibration_rows) == len(pack.validation_rows) == 13_500
    assert len(pack.summary_rows) == 27
    assert pack.config["master_seed"] == goal008.MASTER_SEED
    assert pack.config["candidate_etas"] == list(goal008.FROZEN_ETA_GRID)
    candidate_rhos = pack.config["candidate_rhos"]
    assert isinstance(candidate_rhos, list)
    assert all(
        round(float(observed), 9) == round(expected, 9)
        for observed, expected in zip(
            candidate_rhos,
            goal008.FROZEN_RHO_GRID,
            strict=True,
        )
    )


def test_goal010_config_extends_only_eta_and_replays_old_bank_slices_exactly() -> None:
    config = benchmark.smoke_config()
    inherited = benchmark.expanded_goal008_config(config)

    assert config.selected_cell_ids == ("cell-06", "cell-07", "cell-08")
    assert inherited.rhos == config.rhos
    assert inherited.etas == (*config.original_etas, 2.25, 2.5)
    assert inherited.master_seed == config.master_seed
    assert inherited.calibration_blocks == config.calibration_blocks
    assert inherited.validation_blocks == config.validation_blocks

    replay = benchmark.verify_integration_bank_extension(config)
    assert replay.old_slices_equal
    assert replay.seed_manifest_equal
    assert replay.site_ids_equal
    assert replay.new_slices_finite_nonnegative
    assert replay.fixed_process_invariants_pass
    assert replay.all_pass
    assert len(replay.old_bank_sha256) == len(replay.expanded_old_slices_sha256) == 64
    assert replay.old_bank_sha256 == replay.expanded_old_slices_sha256


def test_three_cell_campaign_pairs_rows_recomputes_cutoffs_and_keeps_audit_rows(
    tmp_path: Path,
) -> None:
    pack = benchmark.read_goal009_pack(
        _write_small_goal009_pack(tmp_path / "goal009"),
        require_published=False,
    )
    config = benchmark.smoke_config()

    result = benchmark.run_campaign(pack, config=config, workers=1)

    assert tuple(cell.cell_id for cell in result.config.selected_cells) == (
        "cell-06",
        "cell-07",
        "cell-08",
    )
    assert len(result.calibration_results) == 3 * 3 * 2
    assert len(result.validation_results) == 3 * 3 * 2
    assert len(result.cell_bank_summaries) == 3 * 3
    assert len(result.paired_transitions) == 3 * 3 * 2
    assert len(result.domain_comparisons) == 3 * 3
    assert result.outcome != "implementation_blocked"
    assert all(result.invariants.values())

    paired_keys = tuple(
        (row.block_index, row.truth_cell, row.bank_variant) for row in result.paired_transitions
    )
    expected_keys = tuple(
        (block, f"cell-{cell:02d}", bank)
        for cell in range(6, 9)
        for block in range(2)
        for bank in goal008.BANK_VARIANT_NAMES
    )
    assert paired_keys == expected_keys

    for summary in result.cell_bank_summaries:
        expected = order_statistic_cutoff(
            tuple(
                row.lr_at_truth
                for row in result.calibration_results
                if row.truth_cell == summary.truth_cell and row.bank_variant == summary.bank_variant
            ),
            rank_one_based=2,
        )
        assert summary.cutoff == expected

    transition = result.paired_transitions[0]
    assert transition.original_support_indices
    assert transition.expanded_support_indices
    assert transition.original_mle_cells
    assert transition.expanded_mle_cells
    assert transition.original_training_mle_cells
    assert transition.expanded_training_mle_cells


def test_decision_precedence_is_conservative_and_bank_aware() -> None:
    recoverable = {
        bank: benchmark.PrimaryBankDecisionEvidence(
            bank_variant=bank,
            original_eta_max_contact_count=count,
            expanded_eta_max_contact_count=0,
            topology_success_count=500,
            downstream_class="cell_joint_recoverable",
        )
        for bank, count in zip(goal008.BANK_VARIANT_NAMES, (152, 150, 156), strict=True)
    }
    assert (
        benchmark.classify_decision(
            {"complete": True},
            recoverable,
            validation_count=500,
        )
        == "bounded_upper_expansion_resolves_primary_decision_limit"
    )
    assert (
        benchmark.classify_decision(
            {"complete": False},
            recoverable,
            validation_count=500,
        )
        == "implementation_blocked"
    )

    unstable = dict(recoverable)
    unstable["second_half"] = replace(
        unstable["second_half"],
        downstream_class="cell_joint_recovery_imprecise",
    )
    assert (
        benchmark.classify_decision(
            {"complete": True},
            unstable,
            validation_count=500,
        )
        == "likelihood_approximation_unstable"
    )

    open_domain = {
        bank: replace(
            row,
            expanded_eta_max_contact_count=26,
            topology_success_count=474,
            downstream_class="cell_joint_design_limited",
        )
        for bank, row in recoverable.items()
    }
    assert (
        benchmark.classify_decision(
            {"complete": True},
            open_domain,
            validation_count=500,
        )
        == "bounded_upper_expansion_domain_not_closed"
    )

    contributed = {
        bank: replace(
            row,
            expanded_eta_max_contact_count=1,
            topology_success_count=470,
            downstream_class="cell_joint_recovery_imprecise",
        )
        for bank, row in recoverable.items()
    }
    assert (
        benchmark.classify_decision(
            {"complete": True},
            contributed,
            validation_count=500,
        )
        == "bounded_upper_expansion_contributes_primary_still_limited"
    )


def test_open_domain_precedes_downstream_class_disagreement() -> None:
    primary_banks = {
        bank: benchmark.PrimaryBankDecisionEvidence(
            bank_variant=bank,
            original_eta_max_contact_count=150,
            expanded_eta_max_contact_count=0,
            topology_success_count=500,
            downstream_class="cell_joint_recoverable",
        )
        for bank in goal008.BANK_VARIANT_NAMES
    }
    first_bank = goal008.BANK_VARIANT_NAMES[0]
    primary_banks[first_bank] = replace(
        primary_banks[first_bank],
        expanded_eta_max_contact_count=26,
        topology_success_count=474,
        downstream_class="cell_joint_design_limited",
    )

    assert (
        benchmark.classify_decision(
            {"complete": True},
            primary_banks,
            validation_count=500,
        )
        == "bounded_upper_expansion_domain_not_closed"
    )


def test_reader_rejects_wrong_published_identity_even_with_valid_internal_hashes(
    tmp_path: Path,
) -> None:
    pack_path = _write_small_goal009_pack(tmp_path / "goal009")

    with pytest.raises(ValueError, match="published Goal009"):
        benchmark.read_goal009_pack(pack_path)

    verification = json.loads((pack_path / "verification.json").read_text(encoding="utf-8"))
    assert verification["compute_provenance_validated"] is True
    assert _read_csv(pack_path / "seed_manifest.csv")
