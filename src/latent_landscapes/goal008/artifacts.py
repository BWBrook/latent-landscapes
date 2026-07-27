"""Deterministic review-pack writer for Goal 008."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import platform
import re
import subprocess
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from math import isfinite
from pathlib import Path
from statistics import median
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from .benchmark import (
    BANK_VARIANT_NAMES,
    SOURCE_IDENTITY,
    THREAD_LIMIT_NAMES,
    CellBankSummary,
    Goal008Result,
    TruthCell,
    campaign_digest,
    diagnostic_json_value,
    nonfinite_value_evidence,
)

DEFAULT_OUTPUT_DIR = Path("artifacts/goal008_joint_rho_eta_cross_truth_perfect_detection")
DEFAULT_BLOCKED_DIAGNOSTICS_DIR = Path("artifacts/goal009_cross_truth_blocked_diagnostics")
METHOD = "site-history simulated composite likelihood"
EXPECTED_FILES = (
    "config.json",
    "compute_provenance.json",
    "seed_manifest.csv",
    "truth_cell_summary.csv",
    "calibration_results.csv",
    "validation_results.csv",
    "predictive_summary.csv",
    "representative_profiles.csv",
    "central_reconciliation.json",
    "summary.json",
    "review.md",
    "visuals/truth_grid_recovery.svg",
    "visuals/truth_grid_calibration.svg",
    "visuals/truth_grid_ridge.svg",
    "visuals/truth_grid_predictive.svg",
    "verification.json",
)
BLOCKED_DIAGNOSTIC_FILES = (
    "diagnostics.json",
    "compute_provenance.json",
    "verification.json",
)

CsvValue = str | int | float | bool | None
CsvRow = dict[str, CsvValue]
PORTABLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def write_review_bundle(
    result: Goal008Result,
    output_dir: Path,
    compute_provenance: Mapping[str, object],
) -> tuple[Path, ...]:
    """Write the exact deterministic 16-file cross-truth review pack."""
    if result.outcome == "implementation_blocked":
        raise ValueError("cannot serialize an implementation-blocked result")
    provenance = _validated_compute_provenance(result, compute_provenance)
    target = Path(output_dir)
    if target.exists() and any(target.rglob("*")):
        raise RuntimeError("refusing to overwrite stale review-pack content")
    target.mkdir(parents=True, exist_ok=True)
    (target / "visuals").mkdir(exist_ok=True)

    _write_json(target / "config.json", _config_payload(result))
    _write_json(target / "compute_provenance.json", provenance)
    _write_csv(target / "seed_manifest.csv", _seed_rows(result))
    _write_csv(target / "truth_cell_summary.csv", _summary_rows(result))
    _write_csv(target / "calibration_results.csv", _calibration_rows(result))
    _write_csv(target / "validation_results.csv", _validation_rows(result))
    _write_csv(target / "predictive_summary.csv", _predictive_rows(result))
    _write_csv(
        target / "representative_profiles.csv",
        _representative_rows(result),
    )
    _write_json(
        target / "central_reconciliation.json",
        _central_payload(result),
    )
    _write_json(target / "summary.json", _summary_payload(result))
    (target / "review.md").write_text(_render_review(result), encoding="utf-8")
    _write_svg(
        target / "visuals/truth_grid_recovery.svg",
        _truth_grid_recovery_figure(result),
    )
    _write_svg(
        target / "visuals/truth_grid_calibration.svg",
        _truth_grid_calibration_figure(result),
    )
    _write_svg(
        target / "visuals/truth_grid_ridge.svg",
        _truth_grid_ridge_figure(result),
    )
    _write_svg(
        target / "visuals/truth_grid_predictive.svg",
        _truth_grid_predictive_figure(result),
    )

    hashes = {
        relative: hashlib.sha256((target / relative).read_bytes()).hexdigest()
        for relative in EXPECTED_FILES
        if relative != "verification.json"
    }
    _write_json(
        target / "verification.json",
        {
            "goal": "008-joint-rho-eta-cross-truth-perfect-detection",
            "outcome": result.outcome,
            "expected_artifact_file_count": 16,
            "observed_artifact_file_count": 16,
            "all_invariants_pass": all(result.invariants.values()),
            "invariants": result.invariants,
            "sha256": hashes,
            "source_identity": SOURCE_IDENTITY,
            "central_reference_checked": (
                result.central_reconciliation.production_reference_checked
            ),
            "central_reference_match": (result.central_reconciliation.production_reference_match),
            "pointwise_not_familywise": True,
            "compute_provenance_validated": True,
        },
    )
    observed = {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()}
    if observed != set(EXPECTED_FILES):
        raise RuntimeError("review pack does not match the exact 16-file contract")
    _validate_serialized_bundle(target, observed)
    return tuple(target / relative for relative in EXPECTED_FILES)


def write_blocked_diagnostics(
    result: Goal008Result,
    output_dir: Path = DEFAULT_BLOCKED_DIAGNOSTICS_DIR,
    compute_provenance: Mapping[str, object] | None = None,
) -> tuple[Path, ...]:
    """Write the exact trusted three-file quarantine for a completed hard block."""
    if result.outcome != "implementation_blocked":
        raise ValueError("blocked diagnostics require outcome='implementation_blocked'")
    target = Path(output_dir)
    if target.exists():
        raise RuntimeError("refusing to overwrite a stale diagnostic directory")
    if compute_provenance is None:
        raise ValueError("blocked diagnostics require compute provenance")
    _validate_completed_diagnostic_surface(result)
    provenance = _validated_compute_provenance(result, compute_provenance)

    base_payload = _blocked_diagnostics_payload(result)
    diagnostics, serialized_nonfinite = diagnostic_json_value(base_payload)
    if not isinstance(diagnostics, dict):
        raise TypeError("blocked diagnostics payload must be a mapping")
    scientific_nonfinite = nonfinite_value_evidence(
        {
            "calibration_results": result.calibration_results,
            "validation_results": result.validation_results,
            "representative_profiles": result.representative_profiles,
        },
        path="$.result",
    )
    all_nonfinite = {
        (row["path"], row["tag"]): row for row in (*serialized_nonfinite, *scientific_nonfinite)
    }
    diagnostics["nonfinite_values"] = [all_nonfinite[key] for key in sorted(all_nonfinite)]

    diagnostic_bytes = _json_bytes(diagnostics)
    provenance_bytes = _json_bytes(provenance)
    verification = {
        "goal": "009-platform-stable-cross-truth-recovery",
        "outcome": result.outcome,
        "evidence_status": "quarantined_completed_campaign",
        "expected_artifact_file_count": 3,
        "observed_artifact_file_count": 3,
        "scientific_review_pack_accepted": False,
        "compute_provenance_validated": True,
        "sha256": {
            "diagnostics.json": hashlib.sha256(diagnostic_bytes).hexdigest(),
            "compute_provenance.json": hashlib.sha256(provenance_bytes).hexdigest(),
        },
    }
    verification_bytes = _json_bytes(verification)

    target.mkdir(parents=True)
    (target / "diagnostics.json").write_bytes(diagnostic_bytes)
    (target / "compute_provenance.json").write_bytes(provenance_bytes)
    (target / "verification.json").write_bytes(verification_bytes)
    observed = {path.name for path in target.iterdir() if path.is_file()}
    if observed != set(BLOCKED_DIAGNOSTIC_FILES):
        raise RuntimeError("blocked diagnostics do not match the exact three-file contract")
    _validate_serialized_bundle(target, observed)
    return tuple(target / relative for relative in BLOCKED_DIAGNOSTIC_FILES)


def _blocked_diagnostics_payload(result: Goal008Result) -> dict[str, object]:
    cell_invariants = [
        {
            "truth_cell": cell.cell_id,
            "invariants": result.cell_invariants[cell.cell_id],
            "false_invariants": sorted(
                name for name, passed in result.cell_invariants[cell.cell_id].items() if not passed
            ),
        }
        for cell in result.config.truth_cells
    ]
    telemetry = result.execution_telemetry
    return {
        "goal": "009-platform-stable-cross-truth-recovery",
        "scientific_goal": "008-joint-rho-eta-cross-truth-perfect-detection",
        "evidence_status": "quarantined_completed_campaign",
        "outcome": result.outcome,
        "scientific_review_pack_accepted": False,
        "reason_no_scientific_review_pack": ("completed campaign returned implementation_blocked"),
        "campaign_invariants": result.invariants,
        "false_campaign_invariants": sorted(
            name for name, passed in result.invariants.items() if not passed
        ),
        "cell_invariants": cell_invariants,
        "central_reconciliation": _central_payload(result),
        "cell_bank_surface": [_summary_row(row) for row in result.cell_bank_summaries],
        "execution_telemetry": {
            "worker_count": telemetry.worker_count,
            "thread_limits": telemetry.thread_limits,
            "campaign_exit_status": telemetry.campaign_exit_status,
            "cell_telemetry": [
                {
                    "truth_cell": row.truth_cell,
                    "exit_status": row.exit_status,
                    "wall_time_seconds": row.wall_time_seconds,
                    "maximum_rss_bytes": row.maximum_rss_bytes,
                }
                for row in telemetry.cell_telemetry
            ],
        },
        "source_identity": SOURCE_IDENTITY,
        "campaign_digest": campaign_digest(result),
        "nonfinite_encoding": {
            "strategy": "tagged_string",
            "nan": "__nonfinite_float__:nan",
            "positive_infinity": "__nonfinite_float__:positive_infinity",
            "negative_infinity": "__nonfinite_float__:negative_infinity",
            "paths": "JSONPath-like paths rooted at '$'",
        },
    }


def _validate_completed_diagnostic_surface(result: Goal008Result) -> None:
    expected_cells = tuple(cell.cell_id for cell in result.config.truth_cells)
    if tuple(result.cell_invariants) != expected_cells or any(
        not invariants or any(not isinstance(value, bool) for value in invariants.values())
        for invariants in result.cell_invariants.values()
    ):
        raise ValueError("blocked diagnostics require all nine cell invariant maps")
    expected_surface = tuple((cell, bank) for cell in expected_cells for bank in BANK_VARIANT_NAMES)
    observed_surface = tuple(
        (row.truth_cell, row.bank_variant) for row in result.cell_bank_summaries
    )
    if observed_surface != expected_surface:
        raise ValueError("blocked diagnostics require the complete ordered 27-row surface")
    if any(not isinstance(value, bool) for value in result.invariants.values()):
        raise ValueError("campaign invariants must be boolean")
    telemetry = result.execution_telemetry
    if (
        telemetry.campaign_exit_status != 0
        or tuple(row.truth_cell for row in telemetry.cell_telemetry) != expected_cells
        or any(row.exit_status != 0 for row in telemetry.cell_telemetry)
    ):
        raise ValueError("blocked diagnostics require a completed successful worker campaign")


def _config_payload(result: Goal008Result) -> dict[str, object]:
    config = result.config
    return {
        "goal": "008-joint-rho-eta-cross-truth-perfect-detection",
        "master_seed": config.master_seed,
        "bit_generator": "PCG64",
        "integration_bank_size": config.bank_size,
        "half_bank_size": config.bank_size // 2,
        "calibration_block_count": config.calibration_blocks,
        "validation_block_count": config.validation_blocks,
        "calibration_rank_one_based": config.calibration_rank_one_based,
        "bank_variants": list(BANK_VARIANT_NAMES),
        "candidate_rhos": list(config.rhos),
        "candidate_etas": list(config.etas),
        "truth_cell_order": [cell.cell_id for cell in config.truth_cells],
        "truth_cells": [
            {
                "truth_cell": cell.cell_id,
                "rho": cell.rho,
                "eta": cell.eta,
                "rho_index": cell.rho_index,
                "eta_index": cell.eta_index,
            }
            for cell in config.truth_cells
        ],
        "independent_unit": "shock block",
        "within_block_truth_cells": "paired correlated counterfactuals",
        "method": METHOD,
        "between_site_process_dependence": "omitted",
        "is_full_joint_spatial_likelihood": False,
        "perfect_detection": True,
        "detection_random_stream": False,
        "pointwise_not_familywise": True,
        "survey_times": list((10, 20, 30, 40, 50, 60)),
        "analyst_records_per_dataset": 1920,
        "distinct_site_time_outcomes_per_dataset": 960,
    }


def _seed_rows(result: Goal008Result) -> list[CsvRow]:
    return [
        {
            "phase": record.phase,
            "block_index": record.index,
            "pairing_group": (
                f"{record.phase}-block-{record.index:03d}"
                if record.phase != "integration_bank"
                else f"integration-bank-draw-{record.index:04d}"
            ),
            "stream_role": record.stream_role,
            "entropy": record.entropy,
            "spawn_key": _compact_json(record.spawn_key),
            "state_words": _compact_json(record.state_words),
            "pool_size": record.pool_size,
            "truth_cells_reusing_stream": (
                9 if record.phase in {"calibration", "validation"} else 1
            ),
        }
        for record in result.seed_manifest.stream_records
    ]


def _summary_rows(result: Goal008Result) -> list[CsvRow]:
    return [_summary_row(row) for row in result.cell_bank_summaries]


def _summary_row(row: CellBankSummary) -> CsvRow:
    return {
        "truth_cell": row.truth_cell,
        "truth_rho": row.truth_rho,
        "truth_eta": row.truth_eta,
        "truth_rho_index": row.truth_rho_index,
        "truth_eta_index": row.truth_eta_index,
        "bank_variant": row.bank_variant,
        "cutoff_source_cell": row.cutoff_source_cell,
        "cutoff_source_rho": row.cutoff_source_rho,
        "cutoff_source_eta": row.cutoff_source_eta,
        "draw_count": row.draw_count,
        "calibrated_cutoff": row.cutoff.cutoff,
        "cutoff_rank_one_based": row.cutoff.rank_one_based,
        "cutoff_sample_size": row.cutoff.sample_size,
        "coverage_success_count": row.coverage_success_count,
        "coverage_estimate": row.calibrated_coverage.estimate,
        "coverage_lower": row.calibrated_coverage.lower,
        "coverage_upper": row.calibrated_coverage.upper,
        "topology_success_count": row.topology_success_count,
        "topology_success_proportion": row.topology_success_proportion,
        "boundary_contact_count": row.boundary_contact_count,
        "rho_min_contact_count": row.rho_min_contact_count,
        "rho_max_contact_count": row.rho_max_contact_count,
        "eta_min_contact_count": row.eta_min_contact_count,
        "eta_max_contact_count": row.eta_max_contact_count,
        "median_minimum_absolute_log_rho_error": (row.median_minimum_absolute_log_rho_error),
        "median_minimum_absolute_eta_error": row.median_minimum_absolute_eta_error,
        "median_projected_log_rho_width": row.median_projected_log_rho_width,
        "median_projected_eta_width": row.median_projected_eta_width,
        "median_support_cell_count": row.median_support_cell_count,
        "mean_mle_set_size": row.mean_mle_set_size,
        "paired_brier_estimate": row.paired_brier_interval.estimate,
        "paired_brier_lower": row.paired_brier_interval.lower,
        "paired_brier_upper": row.paired_brier_interval.upper,
        "downstream_class": row.downstream_class,
    }


def _calibration_rows(result: Goal008Result) -> list[CsvRow]:
    return [
        {
            "phase": row.phase,
            "block_index": row.block_index,
            "pairing_group": row.pairing_group,
            "truth_cell": row.truth_cell,
            "truth_rho": row.truth_rho,
            "truth_eta": row.truth_eta,
            "truth_rho_index": row.truth_rho_index,
            "truth_eta_index": row.truth_eta_index,
            "bank_variant": row.bank_variant,
            "cutoff_source_cell": row.cutoff_source_cell,
            "cutoff_source_rho": row.cutoff_source_rho,
            "cutoff_source_eta": row.cutoff_source_eta,
            "analyst_record_count": row.analyst_record_count,
            "distinct_outcome_count": row.distinct_outcome_count,
            "duplicate_visits_agree": row.duplicate_visits_agree,
            "lr_at_truth": row.lr_at_truth,
            "truth_log_likelihood": row.truth_log_likelihood,
            "maximum_log_likelihood": row.maximum_log_likelihood,
            "mle_indices": _compact_json(row.mle_indices),
            "mle_cells_rho_eta": _compact_json(row.mle_cells),
            "mle_set_size": len(row.mle_indices),
        }
        for row in result.calibration_results
    ]


def _validation_rows(result: Goal008Result) -> list[CsvRow]:
    return [
        {
            "phase": row.phase,
            "block_index": row.block_index,
            "pairing_group": row.pairing_group,
            "truth_cell": row.truth_cell,
            "truth_rho": row.truth_rho,
            "truth_eta": row.truth_eta,
            "truth_rho_index": row.truth_rho_index,
            "truth_eta_index": row.truth_eta_index,
            "bank_variant": row.bank_variant,
            "cutoff_source_cell": row.cutoff_source_cell,
            "cutoff_source_rho": row.cutoff_source_rho,
            "cutoff_source_eta": row.cutoff_source_eta,
            "analyst_record_count": row.analyst_record_count,
            "distinct_outcome_count": row.distinct_outcome_count,
            "training_outcome_count": row.training_outcome_count,
            "holdout_outcome_count": row.holdout_outcome_count,
            "split_isolated": row.split_isolated,
            "perfect_truth_mapping": row.perfect_truth_mapping,
            "lr_at_truth": row.lr_at_truth,
            "truth_log_likelihood": row.truth_log_likelihood,
            "maximum_log_likelihood": row.maximum_log_likelihood,
            "truth_included": row.truth_included,
            "support_cell_count": row.support_cell_count,
            "support_component_count": row.support_component_count,
            "support_boundary_contact": row.support_boundary_contact,
            "support_boundary_faces": _compact_json(row.support_boundary_faces),
            "projected_log_rho_width": row.projected_log_rho_width,
            "projected_eta_width": row.projected_eta_width,
            "support_indices": _compact_json(row.support_indices),
            "support_correlation": row.support_correlation,
            "support_correlation_reason": row.support_correlation_reason,
            "mle_indices": _compact_json(row.mle_indices),
            "mle_cells_rho_eta": _compact_json(row.mle_cells),
            "mle_set_size": len(row.mle_indices),
            "minimum_absolute_log_rho_error": row.minimum_absolute_log_rho_error,
            "minimum_absolute_eta_error": row.minimum_absolute_eta_error,
            "training_mle_indices": _compact_json(row.training_mle_indices),
            "training_mle_cells_rho_eta": _compact_json(row.training_mle_cells),
            "training_mle_set_size": len(row.training_mle_indices),
            "stochastic_log_score_minimum": row.stochastic_log_score_minimum,
            "stochastic_log_score_maximum": row.stochastic_log_score_maximum,
            "stochastic_brier_minimum": row.stochastic_brier_minimum,
            "stochastic_brier_maximum": row.stochastic_brier_maximum,
            "stochastic_probability_minimum": row.stochastic_probability_minimum,
            "stochastic_probability_maximum": row.stochastic_probability_maximum,
            "neutral_log_score": row.neutral_log_score,
            "neutral_brier_score": row.neutral_brier_score,
            "neutral_probability_minimum": row.neutral_probability_minimum,
            "neutral_probability_maximum": row.neutral_probability_maximum,
            "paired_brier_difference": row.paired_brier_difference,
        }
        for row in result.validation_results
    ]


def _predictive_rows(result: Goal008Result) -> list[CsvRow]:
    return [
        {
            "truth_cell": row.truth_cell,
            "truth_rho": row.truth_rho,
            "truth_eta": row.truth_eta,
            "truth_rho_index": row.truth_rho_index,
            "truth_eta_index": row.truth_eta_index,
            "bank_variant": row.bank_variant,
            "validation_block_count": result.config.validation_blocks,
            "worst_tied_process_mle_rule": True,
            "mean_stochastic_brier_worst_mle": (row.mean_stochastic_brier_worst_mle),
            "mean_neutral_brier": row.mean_neutral_brier,
            "paired_brier_estimate": row.paired_brier_interval.estimate,
            "paired_brier_lower": row.paired_brier_interval.lower,
            "paired_brier_upper": row.paired_brier_interval.upper,
            "finite_log_score_count": row.finite_log_score_count,
            "training_outcome_count_per_dataset": 720,
            "holdout_outcome_count_per_dataset": 240,
        }
        for row in result.cell_bank_summaries
    ]


def _representative_rows(result: Goal008Result) -> list[CsvRow]:
    rows: list[CsvRow] = []
    for representative in result.representative_profiles:
        profile = representative.profile
        support = set(representative.summary.support_indices)
        mle = set(representative.summary.mle_indices)
        for eta_index, eta in enumerate(profile.etas):
            for rho_index, rho in enumerate(profile.rhos):
                rows.append(
                    {
                        "truth_cell": representative.truth_cell,
                        "truth_rho": representative.truth_rho,
                        "truth_eta": representative.truth_eta,
                        "truth_rho_index": representative.truth_rho_index,
                        "truth_eta_index": representative.truth_eta_index,
                        "cutoff_source_cell": representative.cutoff_source_cell,
                        "cutoff_source_rho": representative.cutoff_source_rho,
                        "cutoff_source_eta": representative.cutoff_source_eta,
                        "block_index": representative.block_index,
                        "bank_variant": representative.bank_variant,
                        "candidate_rho": float(rho),
                        "candidate_eta": float(eta),
                        "candidate_rho_index": rho_index,
                        "candidate_eta_index": eta_index,
                        "likelihood_ratio": max(
                            0.0,
                            2.0
                            * (
                                profile.maximum_log_likelihood
                                - float(profile.log_likelihoods[eta_index, rho_index])
                            ),
                        ),
                        "in_support": (eta_index, rho_index) in support,
                        "is_mle": (eta_index, rho_index) in mle,
                        "is_truth": (
                            eta_index == representative.truth_eta_index
                            and rho_index == representative.truth_rho_index
                        ),
                    }
                )
    return rows


def _central_payload(result: Goal008Result) -> dict[str, object]:
    central = result.central_reconciliation
    return {
        "truth_cell": central.truth_cell,
        "truth_rho": 1.0,
        "truth_eta": 1.0,
        "calibration_row_count": len(central.calibration_rows),
        "validation_row_count": len(central.validation_rows),
        "bank_summary_count": len(central.bank_summaries),
        "production_reference_checked": central.production_reference_checked,
        "production_reference_match": central.production_reference_match,
        "checks": central.checks,
        "observed": central.observed,
        "expected": central.expected,
        "raw_hashes": {
            "observed": central.raw_hashes,
            "historical": central.historical_raw_hashes,
            "acceptance_gate": False,
        },
        "structural_hashes": {
            "observed": central.structural_hashes,
            "expected": central.expected["structural_hashes"],
        },
        "canonical_hashes": {
            "observed": central.canonical_hashes,
            "expected": central.expected["canonical_hashes"],
        },
        "canonicalization_rule": central.canonicalization_rule,
        "nonfinite_paths": central.nonfinite_paths,
        "comparison_basis": ("independently derived Goal 007 constants; no second Goal 008 call"),
    }


def _summary_payload(result: Goal008Result) -> dict[str, object]:
    return {
        "goal": "008-joint-rho-eta-cross-truth-perfect-detection",
        "outcome": result.outcome,
        "truth_cell_count": len(result.config.truth_cells),
        "truth_cell_bank_count": len(result.cell_bank_summaries),
        "calibration_independent_block_count": result.config.calibration_blocks,
        "validation_independent_block_count": result.config.validation_blocks,
        "within_block_truth_cells": "paired correlated counterfactuals",
        "pointwise_not_familywise": True,
        "method": METHOD,
        "is_full_joint_spatial_likelihood": False,
        "between_site_process_dependence": "omitted",
        "all_invariants_pass": all(result.invariants.values()),
        "central_reference_checked": (result.central_reconciliation.production_reference_checked),
        "central_reference_match": (result.central_reconciliation.production_reference_match),
        "cell_bank_surface": [_summary_row(row) for row in result.cell_bank_summaries],
    }


def _render_review(result: Goal008Result) -> str:
    full_rows = tuple(row for row in result.cell_bank_summaries if row.bank_variant == "full")
    surface = "\n".join(
        f"- `{row.truth_cell}` at `(rho, eta) = ({row.truth_rho:g}, "
        f"{row.truth_eta:g})`: `{row.downstream_class}`; "
        f"coverage {row.coverage_success_count}/{result.config.validation_blocks}; "
        f"topology {row.topology_success_count}/{result.config.validation_blocks}."
        for row in full_rows
    )
    return f"""# Goal 008 Cross-Truth Joint Rho-Eta Perfect-Detection Review

## Outcome

`{result.outcome}`

## Observed Benchmark Results

The production design contains 500 independent shock blocks in calibration and
500 independent shock blocks in validation. Within a block, the nine truth
cells are paired correlated counterfactuals: one edge-shock vector is reused
across eta and rho is obtained by exact arrival-time scaling.

{surface}

All 27 truth-cell-by-bank analyses are reported. A negative or mixed truth-cell
result is a completed scientific result and is preserved without retuning.

## Inference And Calibration

Each truth cell and each of the full, first-half, and second-half banks receives
its own 476th-of-500 local cutoff. Wilson truth-inclusion intervals and normal
Monte Carlo paired-Brier intervals are pointwise, not familywise. The overall
rule is a prespecified worst-cell benchmark, not a simultaneous 95% statement.

## Interpretation

Support topology, bias, projected widths, boundary contact, descriptive
rho-eta ridge correlation, and held-out prediction are interpreted locally.
Flank boundary contact is evidence of limited recovery and does not authorize
expanding the candidate grid.

## Limitations

The result is conditional on one frozen landscape, sampling design, calendar,
candidate grid, and perfect direct detection. The {METHOD} omits between-site
process dependence and is not a full joint spatial likelihood. Cross-cell
comparisons are paired, and the benchmark does not establish uncertainty
calibration when truth is operationally unknown.
"""


def _truth_grid_recovery_figure(result: Goal008Result) -> Figure:
    rows = _full_bank_rows(result)
    rho_error = _grid(rows, lambda row: row.median_minimum_absolute_log_rho_error)
    eta_error = _grid(rows, lambda row: row.median_minimum_absolute_eta_error)
    with _svg_style():
        figure, axes = plt.subplots(1, 2, figsize=(10.0, 4.8))
        _heatmap(
            axes[0],
            rho_error,
            result.config.truth_cells,
            "Median minimum absolute log-rho error",
            "Log-rho recovery",
        )
        _heatmap(
            axes[1],
            eta_error,
            result.config.truth_cells,
            "Median minimum absolute eta error",
            "Eta recovery",
        )
        figure.suptitle("Pointwise recovery across the truth grid")
        figure.tight_layout(rect=(0, 0, 1, 0.94))
    return figure


def _truth_grid_calibration_figure(result: Goal008Result) -> Figure:
    rows = _full_bank_rows(result)
    coverage = _grid(rows, lambda row: row.calibrated_coverage.estimate)
    topology = _grid(rows, lambda row: row.topology_success_proportion)
    with _svg_style():
        figure, axes = plt.subplots(1, 2, figsize=(10.0, 4.8))
        _heatmap(
            axes[0],
            coverage,
            result.config.truth_cells,
            "Truth-inclusion proportion",
            "Pointwise coverage",
            vmin=0.0,
            vmax=1.0,
        )
        _heatmap(
            axes[1],
            topology,
            result.config.truth_cells,
            "Connected and interior proportion",
            "Support topology",
            vmin=0.0,
            vmax=1.0,
        )
        figure.suptitle("Local calibration and topology across the truth grid")
        figure.tight_layout(rect=(0, 0, 1, 0.94))
    return figure


def _truth_grid_ridge_figure(result: Goal008Result) -> Figure:
    values = {
        cell.cell_id: tuple(
            row.support_correlation
            for row in result.validation_results
            if row.truth_cell == cell.cell_id
            and row.bank_variant == "full"
            and row.support_correlation is not None
        )
        for cell in result.config.truth_cells
    }
    ridge = np.asarray(
        [
            [
                float(median(values[cell.cell_id])) if values[cell.cell_id] else 0.0
                for cell in result.config.truth_cells[row * 3 : row * 3 + 3]
            ]
            for row in range(3)
        ]
    )
    with _svg_style():
        figure, axis = plt.subplots(figsize=(6.4, 5.0))
        _heatmap(
            axis,
            ridge,
            result.config.truth_cells,
            "Median support-cell rho-eta correlation",
            "Descriptive ridge correlation",
            vmin=-1.0,
            vmax=1.0,
        )
        figure.tight_layout()
    return figure


def _truth_grid_predictive_figure(result: Goal008Result) -> Figure:
    rows = _full_bank_rows(result)
    paired = _grid(rows, lambda row: row.paired_brier_interval.estimate)
    with _svg_style():
        figure, axis = plt.subplots(figsize=(6.4, 5.0))
        _heatmap(
            axis,
            paired,
            result.config.truth_cells,
            "Worst tied-process Brier minus neutral Brier",
            "Held-out predictive contrast",
        )
        figure.tight_layout()
    return figure


def _full_bank_rows(result: Goal008Result) -> tuple[CellBankSummary, ...]:
    return tuple(row for row in result.cell_bank_summaries if row.bank_variant == "full")


def _grid(
    rows: tuple[CellBankSummary, ...],
    value: Any,
) -> np.ndarray[Any, np.dtype[np.float64]]:
    by_cell = {row.truth_cell: float(value(row)) for row in rows}
    return np.asarray(
        [[by_cell[f"cell-{row * 3 + column:02d}"] for column in range(3)] for row in range(3)],
        dtype=np.float64,
    )


def _heatmap(
    axis: Any,
    values: np.ndarray[Any, np.dtype[np.float64]],
    cells: tuple[TruthCell, ...],
    colorbar_label: str,
    title: str,
    *,
    vmin: float | None = None,
    vmax: float | None = None,
) -> None:
    image = axis.imshow(
        values,
        origin="upper",
        aspect="equal",
        interpolation="nearest",
        cmap="viridis",
        vmin=vmin,
        vmax=vmax,
    )
    rho_labels = [f"{cell.rho:g}" for cell in cells[:3]]
    eta_labels = [f"{cells[row * 3].eta:g}" for row in range(3)]
    axis.set(
        xticks=np.arange(3),
        xticklabels=rho_labels,
        yticks=np.arange(3),
        yticklabels=eta_labels,
        xlabel="Truth rho",
        ylabel="Truth eta",
        title=title,
    )
    for row in range(3):
        for column in range(3):
            axis.text(
                column,
                row,
                f"{values[row, column]:.3f}",
                ha="center",
                va="center",
                color="white" if values[row, column] < float(np.mean(values)) else "black",
            )
    axis.figure.colorbar(image, ax=axis, label=colorbar_label, shrink=0.82)


def _write_json(path: Path, payload: object) -> None:
    path.write_bytes(_json_bytes(payload))


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _write_csv(path: Path, rows: Sequence[CsvRow]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path.name}")
    fieldnames = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            if list(row) != fieldnames:
                raise ValueError(f"CSV schema changed within {path.name}")
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


def _csv_value(value: CsvValue) -> str | int:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("CSV values must be finite")
        return format(value, ".17g")
    return value


def _compact_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), allow_nan=False)


def _write_svg(path: Path, figure: Figure) -> None:
    buffer = io.StringIO()
    figure.savefig(buffer, format="svg", metadata={"Date": None})
    plt.close(figure)
    path.write_text(_normalize_svg_ids(buffer.getvalue()), encoding="utf-8")


def _normalize_svg_ids(text: str) -> str:
    token_pattern = r"(?:image|m|p)[0-9a-f]{10}|C\d+_\d+_[0-9a-f]{10}"
    tokens = list(dict.fromkeys(re.findall(token_pattern, text)))
    replacements: dict[str, str] = {}
    for index, token in enumerate(tokens):
        if token.startswith("image"):
            prefix = "image"
        elif token.startswith("C"):
            prefix = f"{token.rsplit('_', 1)[0]}_"
        else:
            prefix = token[0]
        replacements[token] = f"{prefix}{index:010d}"
    return re.sub(token_pattern, lambda match: replacements[match.group(0)], text)


@contextmanager
def _svg_style() -> Iterator[None]:
    with mpl.rc_context(
        {
            "svg.hashsalt": "latent-landscapes-goal008",
            "font.family": "DejaVu Sans",
            "axes.grid": False,
            "figure.dpi": 100,
        }
    ):
        yield


def _validate_portable_provenance(provenance: Mapping[str, object]) -> None:
    serialized = json.dumps(provenance, sort_keys=True, allow_nan=False)
    if any(token in serialized for token in ("/Users/", "/tmp/", "/data/")):
        raise ValueError("compute provenance must use portable identifiers, not absolute paths")


def validate_pre_campaign_provenance(
    declared: Mapping[str, object],
    *,
    workers: int,
) -> None:
    """Reject untrusted production declarations before starting the campaign."""
    provenance = dict(declared)
    _validate_portable_provenance(provenance)
    if provenance.get("provenance_mode") != "production":
        raise ValueError("production provenance must use provenance_mode='production'")
    _validate_portable_identifiers(provenance)
    _validate_production_declaration(
        provenance,
        worker_count=workers,
        thread_limits={name: os.environ.get(name, "") for name in THREAD_LIMIT_NAMES},
    )


def _validated_compute_provenance(
    result: Goal008Result,
    declared: Mapping[str, object],
) -> dict[str, object]:
    provenance = dict(declared)
    _validate_portable_provenance(provenance)
    mode = provenance.get("provenance_mode")
    if result.config.is_production:
        if mode != "production":
            raise ValueError("production provenance must use provenance_mode='production'")
        _validate_production_provenance(result, provenance)
    elif mode != "test":
        raise ValueError("nonproduction provenance must be explicitly labelled test")
    _validate_portable_identifiers(provenance)

    runtime = _runtime_identifiers()
    telemetry = result.execution_telemetry
    cell_rows = [
        {
            "truth_cell": row.truth_cell,
            "exit_status": row.exit_status,
            "wall_time_seconds": row.wall_time_seconds,
            "maximum_rss_bytes": row.maximum_rss_bytes,
        }
        for row in telemetry.cell_telemetry
    ]
    enriched = {
        **provenance,
        **runtime,
        "worker_count": telemetry.worker_count,
        "thread_limits": telemetry.thread_limits,
        "campaign_exit_success": telemetry.campaign_exit_status == 0
        and all(row.exit_status == 0 for row in telemetry.cell_telemetry),
        "cell_telemetry": cell_rows,
        "provenance_validation_passed": True,
    }
    _validate_portable_provenance(enriched)
    return enriched


def _validate_production_provenance(
    result: Goal008Result,
    provenance: Mapping[str, object],
) -> None:
    telemetry = result.execution_telemetry
    _validate_production_declaration(
        provenance,
        worker_count=telemetry.worker_count,
        thread_limits=telemetry.thread_limits,
    )
    if (
        telemetry.campaign_exit_status != 0
        or tuple(row.truth_cell for row in telemetry.cell_telemetry)
        != tuple(cell.cell_id for cell in result.config.truth_cells)
        or any(
            row.exit_status != 0
            or not isfinite(row.wall_time_seconds)
            or row.wall_time_seconds < 0.0
            or row.maximum_rss_bytes <= 0
            for row in telemetry.cell_telemetry
        )
    ):
        raise ValueError("production provenance contains failed or invalid cell telemetry")


def _validate_portable_identifiers(provenance: Mapping[str, object]) -> None:
    for key in ("run_id", "host_id"):
        value = provenance.get(key)
        if not isinstance(value, str) or PORTABLE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError(f"{key} must be a portable identifier")


def _validate_production_declaration(
    provenance: Mapping[str, object],
    *,
    worker_count: int,
    thread_limits: Mapping[str, str],
) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    current_commit = _git_output(repository_root, ("rev-parse", "HEAD"))
    current_status = _git_output(repository_root, ("status", "--porcelain"))
    lock_sha256 = hashlib.sha256((repository_root / "uv.lock").read_bytes()).hexdigest()
    runtime = _runtime_identifiers()
    required_truth = {
        "bundle_verified",
        "remote_head_clean",
        "focused_tests_passed",
        "smoke_passed",
    }
    if any(provenance.get(key) is not True for key in required_truth):
        raise ValueError("production provenance trust-gate booleans must all be true")
    source_commit = provenance.get("source_commit")
    if (
        not isinstance(source_commit, str)
        or COMMIT_PATTERN.fullmatch(source_commit) is None
        or source_commit != current_commit
    ):
        raise ValueError("production provenance source_commit does not match current HEAD")
    bundle_sha256 = provenance.get("bundle_sha256")
    if not isinstance(bundle_sha256, str) or SHA256_PATTERN.fullmatch(bundle_sha256) is None:
        raise ValueError("production provenance bundle_sha256 must be 64 lowercase hex digits")
    declared_lock = provenance.get("uv_lock_sha256")
    if (
        not isinstance(declared_lock, str)
        or SHA256_PATTERN.fullmatch(declared_lock) is None
        or declared_lock != lock_sha256
    ):
        raise ValueError("production provenance uv_lock_sha256 does not match current uv.lock")
    if current_status:
        raise ValueError("production provenance remote_head_clean disagrees with git status")
    if provenance.get("host_id") != platform.node():
        raise ValueError("production provenance host_id does not match the runtime host")
    if provenance.get("worker_count") != 9 or worker_count != 9:
        raise ValueError("production provenance requires an actual worker_count of 9")
    expected_threads = {name: "1" for name in THREAD_LIMIT_NAMES}
    if (
        provenance.get("thread_limits") != expected_threads
        or dict(thread_limits) != expected_threads
    ):
        raise ValueError("production provenance requires all four thread limits set to 1")
    for key, actual in runtime.items():
        if provenance.get(key) != actual:
            raise ValueError(f"production provenance {key} does not match the runtime")


def _runtime_identifiers() -> dict[str, str]:
    try:
        uv_version = subprocess.run(
            ["uv", "--version"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("unable to identify the uv runtime") from error
    return {
        "python_version": platform.python_version(),
        "uv_version": uv_version,
        "numpy_version": np.__version__,
        "os_identifier": platform.platform(),
    }


def _git_output(repository_root: Path, arguments: tuple[str, ...]) -> str:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("unable to verify production git provenance") from error


def _validate_serialized_bundle(target: Path, relative_paths: set[str]) -> None:
    forbidden = (b"/Users/", b"/tmp/", b"/data/", b"NaN", b"Infinity")
    for relative in relative_paths:
        contents = (target / relative).read_bytes()
        if any(token in contents for token in forbidden):
            raise RuntimeError(f"nonportable or non-finite content in {relative}")
