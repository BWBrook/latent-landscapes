"""Review artifacts for the Goal 010 boundary-aware diagnosis."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import platform
import re
import shutil
import subprocess
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict
from math import isfinite
from pathlib import Path
from typing import cast

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from latent_landscapes.goal010.benchmark import (
    BANK_VARIANT_NAMES,
    THREAD_LIMIT_NAMES,
    BaselineBoundaryAnatomy,
    DomainComparison,
    Goal010Result,
    PairedBoundaryTransition,
)

DEFAULT_OUTPUT_DIR = Path("artifacts/goal010_boundary_aware_joint_identifiability")
EXPECTED_FILES = (
    "config.json",
    "compute_provenance.json",
    "baseline_boundary_anatomy.csv",
    "expanded_calibration_results.csv",
    "expanded_validation_results.csv",
    "expanded_truth_cell_summary.csv",
    "paired_boundary_transitions.csv",
    "domain_comparison.csv",
    "representative_profiles.csv",
    "decision.json",
    "verification.json",
    "review.md",
    "visuals/boundary_anatomy.svg",
    "visuals/domain_comparison.svg",
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
PORTABLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

type CsvValue = str | int | float | bool | None
type CsvRow = dict[str, CsvValue]


def write_review_bundle(
    result: Goal010Result,
    target: Path = DEFAULT_OUTPUT_DIR,
    compute_provenance: Mapping[str, object] | None = None,
) -> tuple[Path, ...]:
    """Write the exact accepted 14-file bundle through an atomic directory swap."""
    if result.outcome == "implementation_blocked":
        raise ValueError("implementation_blocked cannot write a scientific review bundle")
    if not result.invariants or not all(result.invariants.values()):
        raise ValueError("scientific review bundle requires every implementation invariant")
    declared = dict(compute_provenance or {})
    provenance = _validated_compute_provenance(result, declared)
    if target.exists():
        raise RuntimeError("refusing stale Goal010 artifact directory")
    temporary = target.parent / f".{target.name}.goal010-writing"
    if temporary.exists():
        raise RuntimeError("refusing stale Goal010 temporary artifact directory")

    config_bytes = _json_bytes(_config_payload(result))
    provenance_bytes = _json_bytes(provenance)
    decision_bytes = _json_bytes(_decision_payload(result))
    review_bytes = _render_review(result).encode()
    temporary.parent.mkdir(parents=True, exist_ok=True)
    try:
        temporary.mkdir()
        (temporary / "visuals").mkdir()
        (temporary / "config.json").write_bytes(config_bytes)
        (temporary / "compute_provenance.json").write_bytes(provenance_bytes)
        _write_csv(
            temporary / "baseline_boundary_anatomy.csv",
            _baseline_rows(result.baseline_anatomy),
        )
        _write_csv(
            temporary / "expanded_calibration_results.csv",
            _calibration_rows(result),
        )
        _write_csv(
            temporary / "expanded_validation_results.csv",
            _validation_rows(result),
        )
        _write_csv(
            temporary / "expanded_truth_cell_summary.csv",
            _summary_rows(result),
        )
        _write_csv(
            temporary / "paired_boundary_transitions.csv",
            _paired_rows(result.paired_transitions),
        )
        _write_csv(
            temporary / "domain_comparison.csv",
            _comparison_rows(result.domain_comparisons),
        )
        _write_csv(
            temporary / "representative_profiles.csv",
            _representative_rows(result),
        )
        (temporary / "decision.json").write_bytes(decision_bytes)
        (temporary / "review.md").write_bytes(review_bytes)
        _write_svg(
            temporary / "visuals" / "boundary_anatomy.svg",
            _boundary_anatomy_figure(result),
        )
        _write_svg(
            temporary / "visuals" / "domain_comparison.svg",
            _domain_comparison_figure(result),
        )
        paths_without_verification = set(EXPECTED_FILES) - {"verification.json"}
        hashes = {
            relative: hashlib.sha256((temporary / relative).read_bytes()).hexdigest()
            for relative in sorted(paths_without_verification)
        }
        verification = {
            "goal": "010-boundary-aware-joint-identifiability-diagnosis",
            "outcome": result.outcome,
            "expected_artifact_file_count": 14,
            "observed_artifact_file_count": 14,
            "baseline_pack_validated": result.baseline_pack.all_invariants_pass,
            "baseline_verification_sha256": result.baseline_pack.verification_sha256,
            "compute_provenance_validated": True,
            "bundle_validated": True,
            "all_invariants_pass": all(result.invariants.values()),
            "invariants": result.invariants,
            "bank_replay": asdict(result.bank_replay) | {"all_pass": result.bank_replay.all_pass},
            "sha256": hashes,
        }
        (temporary / "verification.json").write_bytes(_json_bytes(verification))
        _validate_bundle_directory(temporary)
        os.replace(temporary, target)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return tuple(target / relative for relative in EXPECTED_FILES)


def validate_review_bundle(target: Path) -> dict[str, object]:
    """Validate the exact file set, strict JSON, and every internal payload hash."""
    return _validate_bundle_directory(target)


def validate_pre_campaign_provenance(
    declared: Mapping[str, object],
    *,
    workers: int,
    smoke: bool,
) -> None:
    """Reject incomplete production trust declarations before expensive work."""
    provenance = dict(declared)
    mode = provenance.get("provenance_mode")
    if smoke:
        if mode != "test":
            raise ValueError("smoke provenance must use provenance_mode='test'")
        _validate_identifiers(provenance)
        if workers <= 0:
            raise ValueError("smoke workers must be positive")
        return
    if mode != "production":
        raise ValueError("production provenance must use provenance_mode='production'")
    _validate_identifiers(provenance)
    truth_fields = (
        "bundle_verified",
        "goal009_input_manifest_verified",
        "detached_head",
        "remote_head_clean",
        "focused_tests_passed",
        "smoke_passed",
        "environment_verified",
    )
    if any(provenance.get(field) is not True for field in truth_fields):
        raise ValueError("production provenance trust-gate booleans must all be true")
    source_commit = provenance.get("source_commit")
    if not isinstance(source_commit, str) or COMMIT_PATTERN.fullmatch(source_commit) is None:
        raise ValueError("production provenance source_commit must be 40 lowercase hex digits")
    for field in (
        "bundle_sha256",
        "uv_lock_sha256",
        "goal009_input_manifest_sha256",
    ):
        value = provenance.get(field)
        if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError(f"production provenance {field} must be 64 lowercase hex digits")
    if provenance.get("host_id") != "deep-server":
        raise ValueError("production provenance host_id must be deep-server")
    if platform.node() != provenance.get("host_id"):
        raise ValueError("production provenance runtime host does not match host_id")
    expected_threads = {name: "1" for name in THREAD_LIMIT_NAMES}
    observed_threads = {name: os.environ.get(name, "") for name in THREAD_LIMIT_NAMES}
    if (
        workers != 3
        or provenance.get("worker_count") != 3
        or provenance.get("thread_limits") != expected_threads
        or observed_threads != expected_threads
    ):
        raise ValueError(
            "production provenance requires three workers and all four thread limits set to 1"
        )
    command = provenance.get("production_command")
    if (
        not isinstance(command, str)
        or "scripts/run_goal010.py" not in command
        or "--workers 3" not in command
        or "--goal009-pack" not in command
        or "--output-dir" not in command
        or "--compute-provenance-json" not in command
    ):
        raise ValueError("production provenance must retain the exact production command")

    repository_root = Path(__file__).resolve().parents[3]
    current_commit = _git_output(repository_root, ("rev-parse", "HEAD"))
    current_status = _git_output(repository_root, ("status", "--porcelain"))
    symbolic_head = _git_output(
        repository_root,
        ("symbolic-ref", "-q", "HEAD"),
        allow_failure=True,
    )
    lock_hash = hashlib.sha256((repository_root / "uv.lock").read_bytes()).hexdigest()
    if source_commit != current_commit:
        raise ValueError("production provenance source_commit does not match current HEAD")
    if current_status:
        raise ValueError("production provenance clean flag disagrees with git status")
    if symbolic_head:
        raise ValueError("production provenance detached flag disagrees with git HEAD")
    if provenance.get("uv_lock_sha256") != lock_hash:
        raise ValueError("production provenance uv_lock_sha256 does not match uv.lock")
    runtime = _runtime_identifiers()
    for field, actual in runtime.items():
        if provenance.get(field) != actual:
            raise ValueError(f"production provenance {field} does not match the runtime")


def _validated_compute_provenance(
    result: Goal010Result,
    declared: Mapping[str, object],
) -> dict[str, object]:
    smoke = not result.config.is_production
    validate_pre_campaign_provenance(
        declared,
        workers=result.execution_telemetry.worker_count,
        smoke=smoke,
    )
    telemetry = result.execution_telemetry
    enriched = {
        **declared,
        **_runtime_identifiers(),
        "worker_count": telemetry.worker_count,
        "thread_limits": telemetry.thread_limits,
        "campaign_exit_success": telemetry.campaign_exit_status == 0
        and all(row.exit_status == 0 for row in telemetry.cell_telemetry),
        "cell_telemetry": [
            {
                "truth_cell": row.truth_cell,
                "exit_status": row.exit_status,
                "wall_time_seconds": row.wall_time_seconds,
                "maximum_rss_bytes": row.maximum_rss_bytes,
            }
            for row in telemetry.cell_telemetry
        ],
        "goal009_pack_verification_sha256": result.baseline_pack.verification_sha256,
        "provenance_validation_passed": True,
    }
    json.dumps(enriched, allow_nan=False)
    return enriched


def _config_payload(result: Goal010Result) -> dict[str, object]:
    config = result.config
    return {
        "goal": "010-boundary-aware-joint-identifiability-diagnosis",
        "scientific_parent": "009-platform-stable-cross-truth-recovery",
        "baseline_outcome": result.baseline_pack.outcome,
        "master_seed": config.master_seed,
        "integration_bank_size": config.bank_size,
        "half_bank_size": config.bank_size // 2,
        "calibration_block_count": config.calibration_blocks,
        "validation_block_count": config.validation_blocks,
        "calibration_rank_one_based": config.calibration_rank_one_based,
        "candidate_rhos": list(config.rhos),
        "candidate_rhos_unchanged": True,
        "candidate_etas_original": list(config.original_etas),
        "candidate_etas_expanded": list(config.expanded_etas),
        "eta_values_appended": [2.25, 2.5],
        "selected_cell_order": list(config.selected_cell_ids),
        "selected_truth_cells": [
            {
                "truth_cell": cell.cell_id,
                "rho": cell.rho,
                "eta": cell.eta,
                "rho_index": cell.rho_index,
                "eta_index": cell.eta_index,
            }
            for cell in config.selected_cells
        ],
        "bank_variants": list(BANK_VARIANT_NAMES),
        "production_scale": config.is_production,
        "perfect_detection": True,
        "method": "site-history simulated composite likelihood",
        "between_site_process_dependence": "omitted",
        "is_full_joint_spatial_likelihood": False,
        "numeric_cutoffs_recomputed": True,
        "cutoff_rule_unchanged": True,
        "goal009_reclassified": False,
    }


def _decision_payload(result: Goal010Result) -> dict[str, object]:
    primary = [row for row in result.domain_comparisons if row.truth_cell == "cell-06"]
    minimum_topology = int(np.ceil(0.95 * result.config.validation_blocks))
    return {
        "goal": "010-boundary-aware-joint-identifiability-diagnosis",
        "outcome": result.outcome,
        "primary_truth_cell": "cell-06",
        "comparative_truth_cells": ["cell-07", "cell-08"],
        "goal009_outcome_retained": result.baseline_pack.outcome,
        "goal009_reclassified": False,
        "predictive_role": "guard_not_identifiability_evidence",
        "cellwise_not_global": True,
        "eta_zero_interpretation": "accepted_uniform_resistance_parameter_boundary",
        "eta_2_5_contact_interpretation": (
            "more_than_allowed_contact_means_bounded_domain_not_closed"
        ),
        "decision_thresholds": {
            "minimum_connected_interior_support_count": minimum_topology,
            "maximum_failed_connected_interior_support_count": (
                result.config.validation_blocks - minimum_topology
            ),
            "calibration_rank_one_based": result.config.calibration_rank_one_based,
            "thresholds_retuned": False,
        },
        "primary_bank_evidence": [_comparison_payload(row) for row in primary],
        "cell_bank_evidence": [_comparison_payload(row) for row in result.domain_comparisons],
    }


def _comparison_payload(row: DomainComparison) -> dict[str, object]:
    return {
        "truth_cell": row.truth_cell,
        "bank_variant": row.bank_variant,
        "original_cutoff": row.original_cutoff,
        "expanded_cutoff": row.expanded_cutoff,
        "cutoff_difference": row.cutoff_difference,
        "original_topology_success_count": row.original_topology_success_count,
        "expanded_topology_success_count": row.expanded_topology_success_count,
        "topology_success_change": row.topology_success_change,
        "paired_topology_change_estimate": row.paired_topology_change.estimate,
        "paired_topology_change_lower": row.paired_topology_change.lower,
        "paired_topology_change_upper": row.paired_topology_change.upper,
        "original_eta_max_contact_count": row.original_eta_max_contact_count,
        "expanded_eta_max_contact_count": row.expanded_eta_max_contact_count,
        "expanded_eta_max_mle_count_descriptive": row.expanded_eta_max_mle_count,
        "original_downstream_class": row.original_downstream_class,
        "expanded_downstream_class": row.expanded_downstream_class,
    }


def _baseline_rows(rows: tuple[BaselineBoundaryAnatomy, ...]) -> list[CsvRow]:
    result: list[CsvRow] = []
    for row in rows:
        payload = cast(CsvRow, asdict(row))
        payload["eta_min_interpretation"] = (
            "accepted_uniform_resistance_null_not_excluded"
            if row.eta_min_contact_count
            else "no_eta_min_contact"
        )
        payload["eta_max_interpretation"] = (
            "artificial_original_candidate_ceiling_contact"
            if row.eta_max_contact_count
            else "no_eta_max_contact"
        )
        result.append(payload)
    return result


def _calibration_rows(result: Goal010Result) -> list[CsvRow]:
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


def _validation_rows(result: Goal010Result) -> list[CsvRow]:
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


def _summary_rows(result: Goal010Result) -> list[CsvRow]:
    return [
        {
            "truth_cell": row.truth_cell,
            "truth_rho": row.truth_rho,
            "truth_eta": row.truth_eta,
            "truth_rho_index": row.truth_rho_index,
            "truth_eta_index": row.truth_eta_index,
            "bank_variant": row.bank_variant,
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
            "median_minimum_absolute_eta_error": (row.median_minimum_absolute_eta_error),
            "median_projected_log_rho_width": row.median_projected_log_rho_width,
            "median_projected_eta_width": row.median_projected_eta_width,
            "median_support_cell_count": row.median_support_cell_count,
            "mean_mle_set_size": row.mean_mle_set_size,
            "paired_brier_estimate": row.paired_brier_interval.estimate,
            "paired_brier_lower": row.paired_brier_interval.lower,
            "paired_brier_upper": row.paired_brier_interval.upper,
            "downstream_class": row.downstream_class,
        }
        for row in result.cell_bank_summaries
    ]


def _paired_rows(rows: tuple[PairedBoundaryTransition, ...]) -> list[CsvRow]:
    return [
        {
            "block_index": row.block_index,
            "truth_cell": row.truth_cell,
            "bank_variant": row.bank_variant,
            "original_cutoff": row.original_cutoff,
            "expanded_cutoff": row.expanded_cutoff,
            "original_truth_included": row.original_truth_included,
            "expanded_truth_included": row.expanded_truth_included,
            "original_support_component_count": row.original_support_component_count,
            "expanded_support_component_count": row.expanded_support_component_count,
            "original_support_boundary_faces": _compact_json(row.original_support_boundary_faces),
            "expanded_support_boundary_faces": _compact_json(row.expanded_support_boundary_faces),
            "original_connected_interior": row.original_connected_interior,
            "expanded_connected_interior": row.expanded_connected_interior,
            "connected_interior_change": (
                int(row.expanded_connected_interior) - int(row.original_connected_interior)
            ),
            "original_projected_log_rho_width": row.original_projected_log_rho_width,
            "expanded_projected_log_rho_width": row.expanded_projected_log_rho_width,
            "original_projected_eta_width": row.original_projected_eta_width,
            "expanded_projected_eta_width": row.expanded_projected_eta_width,
            "original_minimum_absolute_log_rho_error": (
                row.original_minimum_absolute_log_rho_error
            ),
            "expanded_minimum_absolute_log_rho_error": (
                row.expanded_minimum_absolute_log_rho_error
            ),
            "original_minimum_absolute_eta_error": (row.original_minimum_absolute_eta_error),
            "expanded_minimum_absolute_eta_error": (row.expanded_minimum_absolute_eta_error),
            "original_support_indices": _compact_json(row.original_support_indices),
            "expanded_support_indices": _compact_json(row.expanded_support_indices),
            "original_support_correlation": row.original_support_correlation,
            "expanded_support_correlation": row.expanded_support_correlation,
            "original_mle_cells_rho_eta": _compact_json(row.original_mle_cells),
            "expanded_mle_cells_rho_eta": _compact_json(row.expanded_mle_cells),
            "original_training_mle_cells_rho_eta": _compact_json(row.original_training_mle_cells),
            "expanded_training_mle_cells_rho_eta": _compact_json(row.expanded_training_mle_cells),
            "original_eta_max_contact": row.originally_contacted_eta_max,
            "expanded_eta_max_contact": row.expanded_contacted_eta_max,
            "expanded_eta_2_5_mle_descriptive": row.expanded_eta_max_mle,
            "original_paired_brier_difference": row.original_paired_brier_difference,
            "expanded_paired_brier_difference": row.expanded_paired_brier_difference,
        }
        for row in rows
    ]


def _comparison_rows(rows: tuple[DomainComparison, ...]) -> list[CsvRow]:
    result: list[CsvRow] = []
    for row in rows:
        payload = cast(CsvRow, _comparison_payload(row))
        payload["eta_max_contact_change"] = row.eta_max_contact_change
        result.append(payload)
    return result


def _representative_rows(result: Goal010Result) -> list[CsvRow]:
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
                        "block_index": representative.block_index,
                        "bank_variant": representative.bank_variant,
                        "cutoff": representative.cutoff,
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


def _render_review(result: Goal010Result) -> str:
    primary = tuple(row for row in result.domain_comparisons if row.truth_cell == "cell-06")
    primary_lines = "\n".join(
        f"- `{row.bank_variant}`: upper contact "
        f"{row.original_eta_max_contact_count} -> "
        f"{row.expanded_eta_max_contact_count}; connected-interior "
        f"{row.original_topology_success_count} -> "
        f"{row.expanded_topology_success_count}; class "
        f"`{row.original_downstream_class}` -> `{row.expanded_downstream_class}`."
        for row in primary
    )
    return f"""# Goal 010 Boundary-Aware Joint Identifiability Diagnosis

## Outcome

`{result.outcome}`

This bounded perfect-detection sensitivity appends only `eta = 2.25, 2.5`.
The candidate rho grid, shock members, seed identities, block order, bank
halves, likelihood, neutral comparator, and decision thresholds are unchanged.
Numeric likelihood-ratio cutoffs were recalibrated locally because the profile
maximum can change when the candidate domain expands.

## Primary Cell

{primary_lines}

The primary conclusion is local to `cell-06`. Cells 07-08 are prespecified
comparators. The authenticated Goal 009 result remains
`{result.baseline_pack.outcome}` and is not reclassified.

## Boundary Interpretation

Contact at `eta = 0` means the design cannot exclude the accepted
uniform-resistance null. More than the allowed connected-interiority failure
count at `eta = 2.5` means this bounded candidate domain remains open; it is
not proof of universal or genuine non-identifiability. Counts of MLEs at
`eta = 2.5` are descriptive and do not gate the decision.

## Prediction And Limitations

Held-out Brier comparisons guard against a broken process comparison; they are
not evidence of parameter identifiability. Results remain conditional on one
landscape, design, calendar, perfect detection, and a site-history simulated
composite likelihood that omits between-site process dependence.
"""


def _boundary_anatomy_figure(result: Goal010Result) -> Figure:
    full = tuple(row for row in result.baseline_anatomy if row.bank_variant == "full")
    labels = [row.truth_cell for row in full]
    eta_min = np.asarray([row.eta_min_contact_count for row in full], dtype=float)
    eta_max = np.asarray([row.eta_max_contact_count for row in full], dtype=float)
    positions = np.arange(len(labels))
    with _svg_style():
        figure, axis = plt.subplots(figsize=(10.2, 5.2))
        width = 0.38
        axis.bar(positions - width / 2, eta_min, width, label="eta = 0 contact", color="#247ba0")
        axis.bar(
            positions + width / 2,
            eta_max,
            width,
            label="eta = 2 contact",
            color="#d1495b",
        )
        axis.set(
            xticks=positions,
            xticklabels=labels,
            ylabel="Validation support count",
            xlabel="Goal 009 truth cell",
            title="Goal 009 full-bank boundary anatomy",
        )
        axis.legend(frameon=False)
        axis.spines[["top", "right"]].set_visible(False)
        figure.tight_layout()
    return figure


def _domain_comparison_figure(result: Goal010Result) -> Figure:
    full = tuple(row for row in result.domain_comparisons if row.bank_variant == "full")
    labels = [row.truth_cell for row in full]
    positions = np.arange(len(labels))
    width = 0.35
    with _svg_style():
        figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.8))
        axes[0].bar(
            positions - width / 2,
            [row.original_eta_max_contact_count for row in full],
            width,
            label="Original eta = 2",
            color="#d1495b",
        )
        axes[0].bar(
            positions + width / 2,
            [row.expanded_eta_max_contact_count for row in full],
            width,
            label="Expanded eta = 2.5",
            color="#2a9d8f",
        )
        axes[0].set(
            xticks=positions,
            xticklabels=labels,
            ylabel="Support-contact count",
            title="Upper-face contact",
        )
        axes[0].legend(frameon=False)
        axes[1].bar(
            positions - width / 2,
            [row.original_topology_success_count for row in full],
            width,
            label="Original",
            color="#577590",
        )
        axes[1].bar(
            positions + width / 2,
            [row.expanded_topology_success_count for row in full],
            width,
            label="Expanded",
            color="#43aa8b",
        )
        axes[1].set(
            xticks=positions,
            xticklabels=labels,
            ylabel="Connected-interior count",
            title="Support topology",
        )
        axes[1].legend(frameon=False)
        for axis in axes:
            axis.spines[["top", "right"]].set_visible(False)
        figure.suptitle("Bounded eta-domain comparison by primary and comparator cell")
        figure.tight_layout(rect=(0, 0, 1, 0.94))
    return figure


def _validate_bundle_directory(target: Path) -> dict[str, object]:
    if not target.is_dir():
        raise ValueError("Goal010 review bundle directory does not exist")
    observed = {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()}
    if observed != set(EXPECTED_FILES):
        raise ValueError("Goal010 review bundle does not match the exact 14-file contract")
    if any(path.is_symlink() for path in target.rglob("*")):
        raise ValueError("Goal010 review bundle must not contain symbolic links")
    for relative in EXPECTED_FILES:
        contents = (target / relative).read_bytes()
        if b"NaN" in contents or b"Infinity" in contents:
            raise ValueError(f"non-finite token in {relative}")
    for relative in (
        "config.json",
        "compute_provenance.json",
        "decision.json",
        "verification.json",
    ):
        _strict_json_object(target / relative)
    verification = _strict_json_object(target / "verification.json")
    hashes = verification.get("sha256")
    expected_hash_paths = set(EXPECTED_FILES) - {"verification.json"}
    if not isinstance(hashes, dict) or set(hashes) != expected_hash_paths:
        raise ValueError("Goal010 verification hash surface is incomplete")
    for relative in sorted(expected_hash_paths):
        expected = hashes.get(relative)
        observed_hash = hashlib.sha256((target / relative).read_bytes()).hexdigest()
        if expected != observed_hash:
            raise ValueError(f"Goal010 bundle hash mismatch for {relative}")
    if (
        verification.get("expected_artifact_file_count") != 14
        or verification.get("observed_artifact_file_count") != 14
        or verification.get("bundle_validated") is not True
        or verification.get("all_invariants_pass") is not True
    ):
        raise ValueError("Goal010 verification metadata is incomplete")
    for relative in (
        "baseline_boundary_anatomy.csv",
        "expanded_calibration_results.csv",
        "expanded_validation_results.csv",
        "expanded_truth_cell_summary.csv",
        "paired_boundary_transitions.csv",
        "domain_comparison.csv",
        "representative_profiles.csv",
    ):
        with (target / relative).open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
            first = next(reader, None)
        if not header or not first or len(header) != len(first):
            raise ValueError(f"Goal010 CSV is empty or malformed: {relative}")
    for relative in (
        "visuals/boundary_anatomy.svg",
        "visuals/domain_comparison.svg",
    ):
        text = (target / relative).read_text(encoding="utf-8")
        if not text.lstrip().startswith("<?xml") or "<svg" not in text:
            raise ValueError(f"Goal010 SVG is malformed: {relative}")
    return verification


def _strict_json_object(path: Path) -> dict[str, object]:
    def reject(value: str) -> None:
        raise ValueError(f"non-finite JSON token {value} in {path.name}")

    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {path.name}")
            result[key] = value
        return result

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject,
            object_pairs_hook=unique,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid strict JSON in {path.name}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def _write_csv(path: Path, rows: Sequence[CsvRow]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path.name}")
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            if list(row) != fields:
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


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


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
            "svg.hashsalt": "latent-landscapes-goal010",
            "font.family": "DejaVu Sans",
            "axes.grid": False,
            "figure.dpi": 100,
        }
    ):
        yield


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


def _validate_identifiers(provenance: Mapping[str, object]) -> None:
    for field in ("run_id", "host_id"):
        value = provenance.get(field)
        if not isinstance(value, str) or PORTABLE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError(f"{field} must be a portable identifier")


def _git_output(
    repository_root: Path,
    arguments: tuple[str, ...],
    *,
    allow_failure: bool = False,
) -> str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repository_root,
            check=not allow_failure,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("unable to verify production git provenance") from error
    return completed.stdout.strip()
