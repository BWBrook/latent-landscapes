"""Deterministic review artifacts for Goal 013."""

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
from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import TYPE_CHECKING, cast

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from latent_landscapes import cross_truth
from latent_landscapes.goal001.design import (
    SamplingDesign,
    build_design,
    spawn_generators,
)
from latent_landscapes.goal001.landscape import Landscape, build_landscape
from latent_landscapes.goal012 import artifacts as goal012_artifacts
from latent_landscapes.goal012 import benchmark as goal012_campaign

from .design import SEARCH_ATTEMPTS, SELECTOR_SEED, DesignSelection

if TYPE_CHECKING:
    from .benchmark import Goal013Result

DEFAULT_OUTPUT_DIR = Path("artifacts/goal013_weak_contrast_sampling_design_intervention")
EXPECTED_FILES = (
    "config.json",
    "compute_provenance.json",
    "design_candidates.csv",
    "selected_clusters.csv",
    "design_sites.csv",
    "seed_manifest.csv",
    "existing_evidence_reconciliation.csv",
    "calibration_results.csv",
    "validation_results.csv",
    "cell_bank_summary.csv",
    "baseline_intervention_comparison.csv",
    "observation_signal_summary.csv",
    "representative_profiles.csv",
    "summary.json",
    "verification.json",
    "review.md",
    "visuals/design_comparison.svg",
    "visuals/recovery_comparison.svg",
)
PORTABLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
ROOT_LABELS = {
    0: "integration_bank",
    1: "calibration_process",
    2: "validation_process",
    3: "calibration_central_detection",
    4: "validation_central_detection",
    5: "calibration_noncentral_detection",
    6: "validation_noncentral_detection",
    7: "calibration_intervention_detection",
    8: "validation_intervention_detection",
}

type CsvValue = str | int | float | bool | None
type CsvRow = dict[str, CsvValue]


def validate_pre_campaign_provenance(
    declared: Mapping[str, object],
    *,
    workers: int,
) -> None:
    """Validate portable smoke metadata or the strict four-worker declaration."""
    provenance = dict(declared)
    _validate_portable_provenance(provenance)
    _validate_portable_identifiers(provenance)
    mode = provenance.get("provenance_mode")
    if mode == "test":
        if workers <= 0:
            raise ValueError("test worker count must be positive")
        return
    if mode != "production":
        raise ValueError("compute provenance mode must be 'test' or 'production'")
    _validate_production_declaration(provenance, workers=workers)


def write_review_bundle(
    result: Goal013Result,
    output_dir: Path,
    compute_provenance: Mapping[str, object],
) -> tuple[Path, ...]:
    """Write the exact deterministic 18-file Goal 013 review pack."""
    if result.outcome == "implementation_blocked":
        raise ValueError("cannot serialize an implementation-blocked result")
    if not result.invariants or not all(result.invariants.values()):
        raise ValueError("cannot serialize a result with failed implementation invariants")
    provenance = _validated_compute_provenance(result, compute_provenance)
    target = Path(output_dir)
    if target.exists() and any(target.rglob("*")):
        raise RuntimeError("refusing to overwrite stale review-pack content")
    target.mkdir(parents=True, exist_ok=True)
    (target / "visuals").mkdir(exist_ok=True)

    _write_json(target / "config.json", _config_payload(result))
    _write_json(target / "compute_provenance.json", provenance)
    _write_csv(target / "design_candidates.csv", _candidate_rows(result.design))
    _write_csv(target / "selected_clusters.csv", _cluster_rows(result.design))
    _write_csv(target / "design_sites.csv", _site_rows(result.design))
    _write_csv(target / "seed_manifest.csv", _seed_rows(result))
    _write_csv(
        target / "existing_evidence_reconciliation.csv",
        _evidence_rows(result),
    )
    compatible = cast(goal012_campaign.Goal012Result, result)
    _write_csv(
        target / "calibration_results.csv",
        goal012_artifacts._calibration_rows(compatible),
    )
    _write_csv(
        target / "validation_results.csv",
        goal012_artifacts._validation_rows(compatible),
    )
    _write_csv(
        target / "cell_bank_summary.csv",
        goal012_artifacts._summary_rows(compatible),
    )
    _write_csv(
        target / "baseline_intervention_comparison.csv",
        _comparison_rows(result),
    )
    _write_csv(
        target / "observation_signal_summary.csv",
        goal012_artifacts._observation_rows(compatible),
    )
    _write_csv(
        target / "representative_profiles.csv",
        goal012_artifacts._representative_rows(compatible),
    )
    _write_json(target / "summary.json", _summary_payload(result))
    (target / "review.md").write_text(_render_review(result), encoding="utf-8")
    _write_svg(
        target / "visuals/design_comparison.svg",
        _design_comparison_figure(result),
    )
    _write_svg(
        target / "visuals/recovery_comparison.svg",
        _recovery_comparison_figure(result),
    )

    hashes = {
        relative: hashlib.sha256((target / relative).read_bytes()).hexdigest()
        for relative in EXPECTED_FILES
        if relative != "verification.json"
    }
    _write_json(
        target / "verification.json",
        {
            "goal": "013-weak-contrast-sampling-design-intervention",
            "outcome": result.outcome,
            "expected_artifact_file_count": 18,
            "observed_artifact_file_count": 18,
            "all_invariants_pass": all(result.invariants.values()),
            "invariants": result.invariants,
            "sha256": hashes,
            "compute_provenance_validated": True,
            "design_digest": result.design.design_digest,
            "goal009_truth_cell_summary_sha256": (
                result.evidence.goal009.truth_cell_summary_sha256
            ),
            "goal012_truth_cell_summary_sha256": (
                result.evidence.goal012.truth_cell_summary_sha256
            ),
            "baseline_reused_not_rerun": True,
            "record_level_detection_noise_paired": False,
        },
    )
    observed = {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()}
    if observed != set(EXPECTED_FILES):
        raise RuntimeError("review pack does not match the exact 18-file contract")
    _validate_serialized_bundle(target, observed)
    return tuple(target / relative for relative in EXPECTED_FILES)


def _config_payload(result: Goal013Result) -> dict[str, object]:
    config = result.config.cross_truth_config
    return {
        "goal": "013-weak-contrast-sampling-design-intervention",
        "scientific_parent": "012-cross-truth-joint-known-imperfect-detection",
        "target_truth_cells": ["cell-00", "cell-01", "cell-02", "cell-04"],
        "target_truth_coordinates": [
            {"truth_cell": "cell-00", "rho": 0.5, "eta": 0.5},
            {"truth_cell": "cell-01", "rho": 1.0, "eta": 0.5},
            {"truth_cell": "cell-02", "rho": 2.0, "eta": 0.5},
            {"truth_cell": "cell-04", "rho": 1.0, "eta": 1.0},
        ],
        "method": "site-history simulated composite likelihood",
        "known_detection_probability": 0.65,
        "false_positive_probability": 0.0,
        "replicate_visits": [1, 2],
        "records_per_dataset": 1920,
        "training_records_per_dataset": 1440,
        "holdout_records_per_dataset": 480,
        "survey_times": [10, 20, 30, 40, 50, 60],
        "master_seed": config.master_seed,
        "seed_root_count": 9,
        "bank_size": config.bank_size,
        "half_bank_size": config.half_bank_size,
        "calibration_blocks": config.calibration_blocks,
        "validation_blocks": config.validation_blocks,
        "calibration_rank_one_based": config.calibration_rank_one_based,
        "candidate_rhos": list(config.rhos),
        "candidate_etas": list(config.etas),
        "old_domain_eta_maximum": 2.0,
        "old_domain_projection_is_gating": False,
        "selector_seed": SELECTOR_SEED,
        "selector_attempts": SEARCH_ATTEMPTS,
        "selector_complete_attempt_count": result.design.complete_attempt_count,
        "selector_unique_design_count": result.design.unique_design_count,
        "selector_maximum_absolute_u_z_correlation": (
            result.design.score.maximum_absolute_u_z_correlation
        ),
        "selected_cluster_count": len(result.design.selected_clusters),
        "selected_site_count": len(result.design.sampling_design.sites),
        "design_digest": result.design.design_digest,
        "baseline_reused_not_rerun": True,
        "process_block_paired": True,
        "record_level_detection_noise_paired": False,
        "local_intervention_calibration": True,
        "between_site_process_dependence": "omitted",
        "is_full_joint_spatial_likelihood": False,
    }


def _candidate_rows(selection: DesignSelection) -> list[CsvRow]:
    return [
        {
            "row": row.row,
            "col": row.col,
            "stratum_index": row.stratum_index,
            "stratum": row.stratum,
            "euclidean_source_distance": _round12(row.euclidean_source_distance),
            "retained": row.retained,
            "source_overlap_cells": _compact_json(row.source_overlap_cells),
            "u": _optional_round12(row.u),
            "z": _optional_round12(row.z),
            "lower_tertile": _optional_round12(row.lower_tertile),
            "upper_tertile": _optional_round12(row.upper_tertile),
            "tail": row.tail,
            "selected": row.selected,
            "cluster_id": row.cluster_id,
            "split": row.split,
        }
        for row in selection.candidates
    ]


def _cluster_rows(selection: DesignSelection) -> list[CsvRow]:
    _, baseline = _baseline_spatial_inputs()
    baseline_coordinates = {(row.center_row, row.center_col) for row in baseline.clusters}
    return [
        {
            "cluster_id": row.cluster_id,
            "center_row": row.center_row,
            "center_col": row.center_col,
            "stratum_index": row.stratum_index,
            "stratum": row.stratum,
            "euclidean_source_distance": _round12(row.euclidean_source_distance),
            "split": row.split,
            "tail": row.tail,
            "u": _round12(row.u),
            "z": _round12(row.z),
            "overlaps_goal012_cluster_center": (
                row.center_row,
                row.center_col,
            )
            in baseline_coordinates,
        }
        for row in selection.selected_clusters
    ]


def _site_rows(selection: DesignSelection) -> list[CsvRow]:
    landscape, baseline = _baseline_spatial_inputs()
    selected = {row.cluster_id: row for row in selection.selected_clusters}
    baseline_coordinates = {(row.row, row.col) for row in baseline.sites}
    return [
        {
            "cluster_id": row.cluster_id,
            "split": row.split,
            "stratum_index": row.stratum_index,
            "stratum": row.stratum,
            "tail": selected[row.cluster_id].tail,
            "center_row": row.center_row,
            "center_col": row.center_col,
            "euclidean_source_distance": _round12(row.euclidean_source_distance),
            "site_id": row.site_id,
            "site_offset_index": row.site_offset_index,
            "offset_row": row.offset_row,
            "offset_col": row.offset_col,
            "row": row.row,
            "col": row.col,
            "u": _round12(selected[row.cluster_id].u),
            "z": _round12(selected[row.cluster_id].z),
            "on_access_network": bool(
                selection.sampling_design.network[row.center_row, row.center_col]
            ),
            "passable": bool(landscape.passable[row.row, row.col]),
            "source_reachable": bool(landscape.source_reachable[row.row, row.col]),
            "habitat_class": str(landscape.habitat_class[row.row, row.col]),
            "overlaps_goal012_site": (row.row, row.col) in baseline_coordinates,
        }
        for row in selection.sampling_design.sites
    ]


def _seed_rows(result: Goal013Result) -> list[CsvRow]:
    truth_cells = {
        (item.detection.entropy, item.detection.spawn_key): item.truth_cell
        for manifest in (
            result.seed_manifest.baseline,
            result.seed_manifest.intervention,
        )
        for block in (*manifest.calibration, *manifest.validation)
        for item in block.cell_detection
    }
    rows: list[CsvRow] = []
    for order, row in enumerate(result.seed_manifest.all_stream_records):
        root_index = int(row.spawn_key[0])
        arm = "shared" if root_index <= 2 else "baseline" if root_index <= 6 else "intervention"
        rows.append(
            {
                "manifest_order": order,
                "phase_root_index": root_index,
                "phase_root": ROOT_LABELS[root_index],
                "arm": arm,
                "truth_cell": truth_cells.get((row.entropy, row.spawn_key)),
                "phase": row.phase,
                "index": row.index,
                "stream_role": row.stream_role,
                "entropy": row.entropy,
                "spawn_key": _compact_json(row.spawn_key),
                "state_words": _compact_json(row.state_words),
                "pool_size": row.pool_size,
            }
        )
    return rows


def _evidence_rows(result: Goal013Result) -> list[CsvRow]:
    identities = {
        "009": result.evidence.goal009,
        "012": result.evidence.goal012,
    }
    rows: list[CsvRow] = []
    for row in result.evidence.rows:
        identity = identities[row.source_goal]
        rows.append(
            {
                "source_goal": row.source_goal,
                "source_path_identifier": identity.path_identifier,
                "source_run_id": identity.run_id,
                "source_commit": identity.source_commit,
                "source_outcome": identity.outcome,
                "truth_cell_summary_sha256": (identity.truth_cell_summary_sha256),
                "validation_results_sha256": (identity.validation_results_sha256),
                "verification_sha256": identity.verification_sha256,
                "truth_cell": row.truth_cell,
                "truth_rho": row.truth_rho,
                "truth_eta": row.truth_eta,
                "observation_representation": row.observation_representation,
                "candidate_eta_minimum": row.candidate_eta_minimum,
                "candidate_eta_maximum": row.candidate_eta_maximum,
                "descriptive_eta_maximum": row.descriptive_eta_maximum,
                "bank_variants": _compact_json(row.bank_variants),
                "bank_coverage_success_counts": _compact_json(row.bank_coverage_success_counts),
                "bank_connected_interior_counts": _compact_json(row.bank_connected_interior_counts),
                "bank_physical_connected_interior_counts": _compact_json(
                    row.bank_physical_connected_interior_counts
                ),
                "bank_eta_zero_contact_counts": _compact_json(row.bank_eta_zero_contact_counts),
                "bank_artificial_face_contact_counts": _compact_json(
                    row.bank_artificial_face_contact_counts
                ),
                "bank_classes": _compact_json(row.bank_classes),
                "full_bank_eta_zero_contact_count": (row.full_bank_eta_zero_contact_count),
                "full_bank_median_absolute_log_rho_error": (
                    row.full_bank_median_absolute_log_rho_error
                ),
                "full_bank_median_absolute_eta_error": (row.full_bank_median_absolute_eta_error),
                "full_bank_median_projected_log_rho_width": (
                    row.full_bank_median_projected_log_rho_width
                ),
                "full_bank_median_projected_eta_width": (row.full_bank_median_projected_eta_width),
                "full_bank_paired_brier_estimate": (row.full_bank_paired_brier_estimate),
                "full_bank_paired_brier_lower": (row.full_bank_paired_brier_lower),
                "full_bank_paired_brier_upper": (row.full_bank_paired_brier_upper),
                "full_bank_mean_stochastic_brier_worst_mle": (
                    row.full_bank_mean_stochastic_brier_worst_mle
                ),
                "full_bank_mean_neutral_brier": (row.full_bank_mean_neutral_brier),
                "full_bank_finite_log_score_count": (row.full_bank_finite_log_score_count),
            }
        )
    return rows


def _comparison_rows(result: Goal013Result) -> list[CsvRow]:
    return [
        {
            "truth_cell": row.truth_cell,
            "truth_rho": row.truth_rho,
            "truth_eta": row.truth_eta,
            "bank_variant": row.bank_variant,
            "validation_blocks": row.validation_blocks,
            "baseline_eta_zero_contact_count": (row.baseline_eta_zero_contact_count),
            "intervention_eta_zero_contact_count": (row.intervention_eta_zero_contact_count),
            "contact_count_difference": row.contact_count_difference,
            "block_indicator_difference_estimate": (row.block_indicator_difference.estimate),
            "block_indicator_difference_lower": (row.block_indicator_difference.lower),
            "block_indicator_difference_upper": (row.block_indicator_difference.upper),
            "at_least_25_fewer_contacts": (row.contact_count_difference <= -25),
            "difference_interval_wholly_below_zero": (row.block_indicator_difference.upper < 0.0),
        }
        for row in result.baseline_intervention_comparisons
    ]


def _summary_payload(result: Goal013Result) -> dict[str, object]:
    full_summaries = tuple(row for row in result.truth_cell_summaries if row.bank_variant == "full")
    full_comparisons = tuple(
        row for row in result.baseline_intervention_comparisons if row.bank_variant == "full"
    )
    return {
        "outcome": result.outcome,
        "target_truth_cell_count": 4,
        "truth_cell_bank_count": len(result.truth_cell_summaries),
        "design_digest": result.design.design_digest,
        "baseline_reused_not_rerun": True,
        "process_block_paired": True,
        "record_level_detection_noise_paired": False,
        "design_specific_operating_performance_contrast": True,
        "matched_causal_estimate": False,
        "full_bank_classes": {row.truth_cell: row.expanded_class for row in full_summaries},
        "bank_stable_by_cell": {
            cell: len(
                {
                    row.expanded_class
                    for row in result.truth_cell_summaries
                    if row.truth_cell == cell
                }
            )
            == 1
            for cell in ("cell-00", "cell-01", "cell-02", "cell-04")
        },
        "full_bank_physical_null_comparisons": {
            row.truth_cell: {
                "baseline_eta_zero_contact_count": (row.baseline_eta_zero_contact_count),
                "intervention_eta_zero_contact_count": (row.intervention_eta_zero_contact_count),
                "contact_count_difference": row.contact_count_difference,
                "block_indicator_difference_estimate": (row.block_indicator_difference.estimate),
                "block_indicator_difference_lower": (row.block_indicator_difference.lower),
                "block_indicator_difference_upper": (row.block_indicator_difference.upper),
            }
            for row in full_comparisons
        },
        "goal009_truth_cell_summary_sha256": (result.evidence.goal009.truth_cell_summary_sha256),
        "goal012_truth_cell_summary_sha256": (result.evidence.goal012.truth_cell_summary_sha256),
        "known_detection_probability": 0.65,
        "old_domain_projection_is_gating": False,
        "pointwise_not_familywise": True,
        "conditional_scope": "one landscape and one sampling design intervention",
    }


def _render_review(result: Goal013Result) -> str:
    comparison_rows = "\n".join(
        (
            f"| {row.truth_cell} | {row.baseline_eta_zero_contact_count} | "
            f"{row.intervention_eta_zero_contact_count} | "
            f"{row.contact_count_difference:+d} | "
            f"[{row.block_indicator_difference.lower:.4f}, "
            f"{row.block_indicator_difference.upper:.4f}] |"
        )
        for row in result.baseline_intervention_comparisons
        if row.bank_variant == "full"
    )
    class_rows = "\n".join(
        (f"| {row.truth_cell} | {row.truth_rho:g} | {row.truth_eta:g} | {row.expanded_class} |")
        for row in result.truth_cell_summaries
        if row.bank_variant == "full"
    )
    return f"""# Goal 013 Scientific Review

## Outcome

`{result.outcome}`

## Design Intervention

The frozen selector retained 629 of 635 accessible candidates and selected
32 equal-effort clusters: four low- and four high-contrast centres in each
distance stratum. The selected design digest is
`{result.design.design_digest}`.

## Physical-Null Comparison

| Truth cell | Goal 012 contacts | Intervention contacts | Difference | 95% interval |
| --- | ---: | ---: | ---: | ---: |
{comparison_rows}

These are design-specific operating-performance contrasts. Process blocks are
matched, but detection realizations are distinct, so the comparison is not a
matched causal estimate of a record-level sampling-design effect.

## Intervention Recovery

| Truth cell | Rho | Eta | Full-bank class |
| --- | ---: | ---: | --- |
{class_rows}

## Interpretation Boundary

The accepted Goal 009 and Goal 012 evidence was authenticated and reused, not
rerun. Its recurrence supports a practical weak-contrast limitation, but the
perfect- and imperfect-detection packs use different observation
representations and prediction targets and are not a matched causal estimate
of detection.

The intervention changes cluster locations and training/holdout allocation
only. It retains the process, two visits with known p = 0.65, zero false
positives, effort, likelihood, candidate grid, local calibration, recovery
thresholds, and neutral comparator. The block-indexed contrasts pair process
shocks, not record-level detection noise.

This is a complete-history simulated composite likelihood, not a full joint spatial likelihood.
It conditions on one landscape and one prespecified design intervention,
omits between-site dependence from the shared edge field, and does not support
universal causal claims. Negative and mixed intervention outcomes are valid
completed scientific results.
"""


def _design_comparison_figure(result: Goal013Result) -> Figure:
    _, baseline = _baseline_spatial_inputs()
    intervention = result.design.selected_clusters
    with _svg_style():
        figure, axes = plt.subplots(
            1,
            2,
            figsize=(11.2, 5.4),
        )
        _cluster_map(
            axes[0],
            tuple(
                (
                    row.center_col,
                    row.center_row,
                    row.split,
                    "baseline",
                )
                for row in baseline.clusters
            ),
            "Goal 012 allocation",
        )
        _cluster_map(
            axes[1],
            tuple(
                (
                    row.center_col,
                    row.center_row,
                    row.split,
                    row.tail,
                )
                for row in intervention
            ),
            "Contrast-balanced allocation",
        )
        figure.suptitle(
            "Goal 013 sampling-design comparison",
            fontweight="bold",
            y=0.96,
        )
        figure.subplots_adjust(
            bottom=0.13,
            left=0.07,
            right=0.98,
            top=0.82,
            wspace=0.24,
        )
    return figure


def _cluster_map(
    axis: Axes,
    rows: tuple[tuple[int, int, str, str], ...],
    title: str,
) -> None:
    for split, marker in (("training", "o"), ("holdout", "s")):
        selected = tuple(row for row in rows if row[2] == split)
        axis.scatter(
            [row[0] for row in selected],
            [row[1] for row in selected],
            c=["#2878b5" if row[3] in {"baseline", "low"} else "#d95f02" for row in selected],
            edgecolors="#202020",
            linewidths=0.6,
            marker=marker,
            s=45 if split == "training" else 65,
            label=split,
        )
    axis.set(
        title=title,
        xlabel="Grid column",
        ylabel="Grid row",
        xlim=(0, 83),
        ylim=(71, 0),
    )
    axis.set_aspect("equal")
    axis.legend(frameon=False, loc="lower right")


def _recovery_comparison_figure(result: Goal013Result) -> Figure:
    rows = tuple(
        row for row in result.baseline_intervention_comparisons if row.bank_variant == "full"
    )
    labels = tuple(row.truth_cell for row in rows)
    positions = np.arange(len(rows), dtype=np.float64)
    with _svg_style():
        figure, axes = plt.subplots(
            1,
            2,
            figsize=(10.8, 5.2),
        )
        width = 0.36
        axes[0].bar(
            positions - width / 2.0,
            [row.baseline_eta_zero_contact_count for row in rows],
            width,
            label="Goal 012 baseline",
            color="#7f8c8d",
        )
        axes[0].bar(
            positions + width / 2.0,
            [row.intervention_eta_zero_contact_count for row in rows],
            width,
            label="Intervention",
            color="#2a9d8f",
        )
        axes[0].set(
            title="Physical-null support contacts",
            ylabel="Validation blocks",
            xticks=positions,
            xticklabels=labels,
        )
        axes[0].legend(frameon=False)

        estimates = np.asarray(
            [row.block_indicator_difference.estimate for row in rows],
            dtype=np.float64,
        )
        lower = np.asarray(
            [row.block_indicator_difference.lower for row in rows],
            dtype=np.float64,
        )
        upper = np.asarray(
            [row.block_indicator_difference.upper for row in rows],
            dtype=np.float64,
        )
        axes[1].errorbar(
            positions,
            estimates,
            yerr=np.vstack((estimates - lower, upper - estimates)),
            fmt="o",
            color="#b23a48",
            capsize=5,
            linewidth=1.5,
        )
        axes[1].axhline(0.0, color="#444444", linewidth=1.0, linestyle="--")
        axes[1].set(
            title="Block-indicator difference",
            ylabel="Intervention minus baseline",
            xticks=positions,
            xticklabels=labels,
        )
        figure.suptitle(
            "Goal 013 weak-contrast recovery comparison",
            fontweight="bold",
            y=0.96,
        )
        figure.subplots_adjust(
            bottom=0.13,
            left=0.08,
            right=0.98,
            top=0.82,
            wspace=0.28,
        )
    return figure


def _validated_compute_provenance(
    result: Goal013Result,
    declared: Mapping[str, object],
) -> dict[str, object]:
    provenance = dict(declared)
    telemetry = result.execution_telemetry
    validate_pre_campaign_provenance(
        provenance,
        workers=telemetry.worker_count,
    )
    production = result.config.cross_truth_config.is_production
    if production and provenance.get("provenance_mode") != "production":
        raise ValueError("production result requires production provenance")
    if not production and provenance.get("provenance_mode") != "test":
        raise ValueError("nonproduction result requires test provenance")
    if production:
        expected_cells = ("cell-00", "cell-01", "cell-02", "cell-04")
        if (
            telemetry.campaign_exit_status != 0
            or tuple(row.truth_cell for row in telemetry.cell_telemetry) != expected_cells
            or any(
                row.exit_status != 0
                or not isfinite(row.wall_time_seconds)
                or row.wall_time_seconds < 0.0
                or row.maximum_rss_bytes <= 0
                for row in telemetry.cell_telemetry
            )
        ):
            raise ValueError("production provenance contains invalid cell telemetry")
    enriched = {
        **provenance,
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
        "goal009_input_verification_sha256": (result.evidence.goal009.verification_sha256),
        "goal012_input_verification_sha256": (result.evidence.goal012.verification_sha256),
        "provenance_validation_passed": True,
    }
    _validate_portable_provenance(enriched)
    return enriched


def _validate_production_declaration(
    provenance: Mapping[str, object],
    *,
    workers: int,
) -> None:
    required_truth = (
        "bundle_verified",
        "remote_head_clean",
        "focused_tests_passed",
        "smoke_passed",
    )
    if any(provenance.get(field) is not True for field in required_truth):
        raise ValueError("production provenance trust-gate booleans must all be true")
    source_commit = provenance.get("source_commit")
    if not isinstance(source_commit, str) or COMMIT_PATTERN.fullmatch(source_commit) is None:
        raise ValueError("production source_commit must be 40 lowercase hex digits")
    for field in ("bundle_sha256", "uv_lock_sha256"):
        value = provenance.get(field)
        if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError(f"production {field} must be 64 lowercase hex digits")
    expected_threads = {name: "1" for name in cross_truth.THREAD_LIMIT_NAMES}
    observed_threads = {name: os.environ.get(name, "") for name in cross_truth.THREAD_LIMIT_NAMES}
    if (
        workers != 4
        or provenance.get("worker_count") != 4
        or provenance.get("thread_limits") != expected_threads
        or observed_threads != expected_threads
    ):
        raise ValueError(
            "production provenance requires four workers and all thread limits set to 1"
        )
    command = provenance.get("production_command")
    required_command_tokens = (
        "scripts/run_goal013.py",
        "--goal009-evidence-dir",
        "--goal012-evidence-dir",
        "--output-dir",
        "--workers 4",
        "--compute-provenance-json",
    )
    if not isinstance(command, str) or any(
        token not in command for token in required_command_tokens
    ):
        raise ValueError("production provenance must retain the exact production command")

    repository_root = Path(__file__).resolve().parents[3]
    current_commit = _git_output(repository_root, ("rev-parse", "HEAD"))
    current_status = _git_output(repository_root, ("status", "--porcelain"))
    lock_hash = hashlib.sha256((repository_root / "uv.lock").read_bytes()).hexdigest()
    if source_commit != current_commit:
        raise ValueError("production source_commit does not match current HEAD")
    if current_status:
        raise ValueError("production remote_head_clean disagrees with git status")
    if provenance.get("uv_lock_sha256") != lock_hash:
        raise ValueError("production uv_lock_sha256 does not match uv.lock")
    if provenance.get("host_id") != platform.node():
        raise ValueError("production host_id does not match the runtime")
    for field, actual in _runtime_identifiers().items():
        if provenance.get(field) != actual:
            raise ValueError(f"production {field} does not match the runtime")


def _validate_portable_provenance(provenance: Mapping[str, object]) -> None:
    serialized = json.dumps(provenance, sort_keys=True, allow_nan=False)
    if any(token in serialized for token in ("/Users/", "/tmp/", "/data/")):
        raise ValueError("compute provenance must use portable identifiers")


def _validate_portable_identifiers(provenance: Mapping[str, object]) -> None:
    for key in ("run_id", "host_id"):
        value = provenance.get(key)
        if not isinstance(value, str) or PORTABLE_ID_PATTERN.fullmatch(value) is None:
            raise ValueError(f"{key} must be a portable identifier")


def _runtime_identifiers() -> dict[str, str]:
    completed = subprocess.run(
        ["uv", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "python_version": platform.python_version(),
        "uv_version": completed.stdout.strip(),
        "numpy_version": np.__version__,
        "os_identifier": platform.platform(),
    }


def _git_output(
    root: Path,
    arguments: tuple[str, ...],
) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


@lru_cache(maxsize=1)
def _baseline_spatial_inputs() -> tuple[Landscape, SamplingDesign]:
    landscape = build_landscape()
    centre_rng, holdout_rng, _ = spawn_generators()
    return landscape, build_design(landscape, centre_rng, holdout_rng)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: Sequence[CsvRow]) -> None:
    if not rows:
        raise ValueError(f"CSV rows must not be empty: {path.name}")
    buffer = io.StringIO(newline="")
    fieldnames = list(rows[0])
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if list(row) != fieldnames:
            raise ValueError(f"CSV row schema mismatch: {path.name}")
        writer.writerow({key: _csv_value(value) for key, value in row.items()})
    path.write_text(buffer.getvalue(), encoding="utf-8")


def _csv_value(value: CsvValue) -> str | int | float:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("CSV values must be finite")
    return value


def _compact_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), allow_nan=False)


def _write_svg(path: Path, figure: Figure) -> None:
    buffer = io.StringIO()
    figure.savefig(buffer, format="svg", metadata={"Date": None})
    plt.close(figure)
    path.write_text(_normalize_svg_ids(buffer.getvalue()), encoding="utf-8")


def _normalize_svg_ids(text: str) -> str:
    matches = tuple(dict.fromkeys(re.findall(r'\bid="([^"]+)"', text)))
    replacements = {old: f"goal013-{index:04d}" for index, old in enumerate(matches)}
    normalized = text
    for old, new in replacements.items():
        normalized = normalized.replace(f'id="{old}"', f'id="{new}"')
        normalized = normalized.replace(f'href="#{old}"', f'href="#{new}"')
        normalized = normalized.replace(f"url(#{old})", f"url(#{new})")
    return normalized


@contextmanager
def _svg_style() -> Iterator[None]:
    with mpl.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.hashsalt": "goal013-weak-contrast-design",
        }
    ):
        yield


def _validate_serialized_bundle(
    target: Path,
    relative_paths: set[str],
) -> None:
    forbidden = (b"/Users/", b"/tmp/", b"/data/", b"NaN", b"Infinity")
    for relative in relative_paths:
        contents = (target / relative).read_bytes()
        if any(token in contents for token in forbidden):
            raise RuntimeError(f"nonportable or nonfinite content in {relative}")


def _round12(value: float) -> float:
    rounded = float(np.round(np.float64(value), 12))
    return 0.0 if rounded == 0.0 else rounded


def _optional_round12(value: float | None) -> float | None:
    return None if value is None else _round12(value)


__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "EXPECTED_FILES",
    "validate_pre_campaign_provenance",
    "write_review_bundle",
]
