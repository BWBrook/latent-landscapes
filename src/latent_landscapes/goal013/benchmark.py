"""Four-cell intervention benchmark using the shared cross-truth engine."""

from __future__ import annotations

import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

from latent_landscapes import cross_truth
from latent_landscapes.goal002.calibration import EstimateInterval, normal_mean_interval
from latent_landscapes.goal004 import benchmark as goal004
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal008 import benchmark as goal008
from latent_landscapes.goal011 import benchmark as goal011

from . import design
from .evidence import (
    BANK_VARIANT_NAMES,
    DEFAULT_GOAL009_EVIDENCE_DIR,
    DEFAULT_GOAL012_EVIDENCE_DIR,
    WEAK_CELL_IDS,
    ExistingEvidence,
    authenticate_existing_evidence,
)

TARGET_CELL_IDS = ("cell-00", "cell-01", "cell-02", "cell-04")
THREAD_LIMIT_NAMES = cross_truth.THREAD_LIMIT_NAMES
STATE_WORD_COUNT = cross_truth.STATE_WORD_COUNT


@dataclass(frozen=True, slots=True)
class Goal013Config:
    cross_truth_config: cross_truth.CrossTruthConfig = cross_truth.DEFAULT_CONFIG

    def __post_init__(self) -> None:
        by_id = {
            cell.cell_id: (cell.rho, cell.eta)
            for cell in self.cross_truth_config.resolved_truth_cells
        }
        expected = {
            "cell-00": (0.5, 0.5),
            "cell-01": (1.0, 0.5),
            "cell-02": (2.0, 0.5),
            "cell-04": (1.0, 1.0),
        }
        if {cell_id: by_id.get(cell_id) for cell_id in TARGET_CELL_IDS} != expected:
            raise ValueError("Goal013 requires the frozen four intervention truths")

    @property
    def target_truth_cells(self) -> tuple[goal008.TruthCell, ...]:
        by_id = {cell.cell_id: cell for cell in self.cross_truth_config.resolved_truth_cells}
        return tuple(by_id[cell_id] for cell_id in TARGET_CELL_IDS)

    @property
    def is_production(self) -> bool:
        return self == DEFAULT_CONFIG


DEFAULT_CONFIG = Goal013Config()


def smoke_config() -> Goal013Config:
    """Return the explicit reduced smoke while preserving the full grids."""
    return Goal013Config(cross_truth_config=cross_truth.smoke_config())


SeedRecord = goal007.StreamSeedRecord | goal004.StreamSeedRecord


@dataclass(frozen=True, slots=True)
class Goal013SeedManifest:
    baseline: cross_truth.SeedManifest
    intervention: cross_truth.SeedManifest

    @property
    def appended_detection_records(self) -> tuple[goal004.StreamSeedRecord, ...]:
        return tuple(
            item.detection
            for block in (
                *self.intervention.calibration,
                *self.intervention.validation,
            )
            for item in block.cell_detection
        )

    @property
    def all_stream_records(self) -> tuple[SeedRecord, ...]:
        return (*self.baseline.stream_records, *self.appended_detection_records)


@dataclass(frozen=True, slots=True)
class BaselineInterventionComparison:
    truth_cell: str
    truth_rho: float
    truth_eta: float
    bank_variant: str
    validation_blocks: int
    baseline_eta_zero_contact_count: int
    intervention_eta_zero_contact_count: int
    contact_count_difference: int
    block_indicator_difference: EstimateInterval


@dataclass(frozen=True, slots=True)
class CellExecutionTelemetry:
    truth_cell: str
    exit_status: int
    wall_time_seconds: float
    maximum_rss_bytes: int


@dataclass(frozen=True, slots=True)
class CampaignExecutionTelemetry:
    worker_count: int
    thread_limits: dict[str, str]
    campaign_exit_status: int
    cell_telemetry: tuple[CellExecutionTelemetry, ...]


@dataclass(frozen=True, slots=True)
class Goal013Result:
    config: Goal013Config
    design: design.DesignSelection
    seed_manifest: Goal013SeedManifest
    evidence: ExistingEvidence
    calibration_results: tuple[cross_truth.CalibrationResult, ...]
    validation_results: tuple[cross_truth.ValidationResult, ...]
    observation_signal_summary: tuple[cross_truth.ObservationSignalSummary, ...]
    representative_profiles: tuple[cross_truth.RepresentativeProfile, ...]
    truth_cell_summaries: tuple[cross_truth.CellBankSummary, ...]
    baseline_intervention_comparisons: tuple[BaselineInterventionComparison, ...]
    cell_invariants: dict[str, dict[str, bool]]
    execution_telemetry: CampaignExecutionTelemetry
    invariants: dict[str, bool]
    outcome: str


def spawn_seed_manifest(
    config: cross_truth.CrossTruthConfig = cross_truth.DEFAULT_CONFIG,
) -> Goal013SeedManifest:
    """Preserve roots zero-to-six and append intervention roots seven and eight."""
    baseline = cross_truth.spawn_seed_manifest(config)
    roots = np.random.SeedSequence(config.master_seed).spawn(9)
    calibration_detection = _intervention_detection_blocks(
        roots[7],
        phase="calibration",
        count=config.calibration_blocks,
    )
    validation_detection = _intervention_detection_blocks(
        roots[8],
        phase="validation",
        count=config.validation_blocks,
    )
    intervention = cross_truth.SeedManifest(
        integration_bank=baseline.integration_bank,
        calibration=tuple(
            cross_truth.BlockSeedRecord(
                phase="calibration",
                index=index,
                process=baseline.calibration[index].process,
                cell_detection=calibration_detection[index],
            )
            for index in range(config.calibration_blocks)
        ),
        validation=tuple(
            cross_truth.BlockSeedRecord(
                phase="validation",
                index=index,
                process=baseline.validation[index].process,
                cell_detection=validation_detection[index],
            )
            for index in range(config.validation_blocks)
        ),
    )
    return Goal013SeedManifest(
        baseline=baseline,
        intervention=intervention,
    )


def build_fixed_inputs(
    selected_design: design.DesignSelection | None = None,
) -> goal007.FixedInputs:
    """Replace only Goal 012's fixed sampling design."""
    baseline = goal011.build_fixed_inputs()
    selected = (
        selected_design
        if selected_design is not None
        else design.build_contrast_balanced_design(baseline.landscape)
    )
    cluster_counts = Counter(cluster.split for cluster in selected.sampling_design.clusters)
    invariants = {
        key: value
        for key, value in baseline.invariants.items()
        if key not in {"design_counts", "cluster_isolation"}
    }
    invariants.update({f"goal013_{key}": value for key, value in selected.invariants.items()})
    invariants.update(
        {
            "design_counts": len(selected.sampling_design.clusters) == 32
            and len(selected.sampling_design.sites) == 160
            and cluster_counts == {"training": 24, "holdout": 8}
            and sum(site.split == "training" for site in selected.sampling_design.sites) == 120
            and sum(site.split == "holdout" for site in selected.sampling_design.sites) == 40,
            "cluster_isolation": all(
                len(
                    {
                        site.split
                        for site in selected.sampling_design.sites
                        if site.cluster_id == cluster.cluster_id
                    }
                )
                == 1
                for cluster in selected.sampling_design.clusters
            ),
            "intervention_design_digest": (selected.design_digest == design.EXPECTED_DESIGN_DIGEST),
        }
    )
    return goal007.FixedInputs(
        landscape=baseline.landscape,
        design=selected.sampling_design,
        invariants=invariants,
    )


def run_campaign(
    config: Goal013Config = DEFAULT_CONFIG,
    *,
    workers: int = 1,
    goal009_evidence_dir: Path = DEFAULT_GOAL009_EVIDENCE_DIR,
    goal012_evidence_dir: Path = DEFAULT_GOAL012_EVIDENCE_DIR,
) -> Goal013Result:
    """Run four locally calibrated intervention cells and reuse accepted baseline evidence."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    _validate_production_runtime(config, workers)
    existing = authenticate_existing_evidence(
        Path(goal009_evidence_dir),
        Path(goal012_evidence_dir),
    )
    selected = design.build_contrast_balanced_design()
    fixed = build_fixed_inputs(selected)
    manifest = spawn_seed_manifest(config.cross_truth_config)
    tasks = tuple(
        (cell, config.cross_truth_config, fixed, manifest.intervention)
        for cell in config.target_truth_cells
    )
    if workers == 1:
        task_outputs = tuple(_run_cell_task(task) for task in tasks)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            task_outputs = tuple(executor.map(_run_cell_task, tasks))
    cell_results = tuple(row[0] for row in task_outputs)
    cell_telemetry = tuple(row[1] for row in task_outputs)
    telemetry = CampaignExecutionTelemetry(
        worker_count=workers,
        thread_limits=_current_thread_limits(),
        campaign_exit_status=0,
        cell_telemetry=cell_telemetry,
    )
    calibration = tuple(row for result in cell_results for row in result.calibration_results)
    validation = tuple(row for result in cell_results for row in result.validation_results)
    signals = tuple(row for result in cell_results for row in result.observation_signal_summary)
    representatives = tuple(
        row for result in cell_results for row in result.representative_profiles
    )
    summaries = tuple(row for result in cell_results for row in result.summaries)
    comparisons = _baseline_intervention_comparisons(
        config,
        existing,
        validation,
    )
    cell_invariants = {
        result.truth_cell.cell_id: dict(result.invariants) for result in cell_results
    }
    all_streams = manifest.all_stream_records
    expected_calibration_count = (
        len(TARGET_CELL_IDS)
        * len(BANK_VARIANT_NAMES)
        * config.cross_truth_config.calibration_blocks
    )
    expected_validation_count = (
        len(TARGET_CELL_IDS) * len(BANK_VARIANT_NAMES) * config.cross_truth_config.validation_blocks
    )
    comparison_ids = {(row.truth_cell, row.bank_variant) for row in comparisons}
    invariants = {
        **{f"design_{key}": value for key, value in selected.invariants.items()},
        **{f"evidence_{key}": value for key, value in existing.invariants.items()},
        "production_contract": not config.is_production
        or (
            config.cross_truth_config == cross_truth.DEFAULT_CONFIG
            and TARGET_CELL_IDS == ("cell-00", "cell-01", "cell-02", "cell-04")
        ),
        "goal012_first_seven_roots_exact": (
            manifest.baseline == cross_truth.spawn_seed_manifest(config.cross_truth_config)
        ),
        "appended_detection_roots": all(
            item.detection.spawn_key[0] == 7
            for block in manifest.intervention.calibration
            for item in block.cell_detection
        )
        and all(
            item.detection.spawn_key[0] == 8
            for block in manifest.intervention.validation
            for item in block.cell_detection
        ),
        "stream_uniqueness": len({(row.entropy, row.spawn_key) for row in all_streams})
        == len(all_streams)
        and len({row.state_words for row in all_streams}) == len(all_streams),
        "target_cell_order": tuple(result.truth_cell.cell_id for result in cell_results)
        == TARGET_CELL_IDS,
        "cell_invariants": all(all(result.invariants.values()) for result in cell_results),
        "complete_calibration_campaign": len(calibration) == expected_calibration_count,
        "complete_validation_campaign": len(validation) == expected_validation_count,
        "complete_summary_surface": len(summaries)
        == len(TARGET_CELL_IDS) * len(BANK_VARIANT_NAMES),
        "complete_representative_surface": len(representatives)
        == len(TARGET_CELL_IDS) * len(BANK_VARIANT_NAMES),
        "complete_signal_surface": len(signals) == len(TARGET_CELL_IDS) * 6,
        "stable_row_identity": len(
            {
                (
                    row.phase,
                    row.block_index,
                    row.truth_cell,
                    row.bank_variant,
                )
                for row in calibration
            }
        )
        == len(calibration)
        and len(
            {
                (
                    row.phase,
                    row.block_index,
                    row.truth_cell,
                    row.bank_variant,
                )
                for row in validation
            }
        )
        == len(validation),
        "baseline_intervention_pairing": comparison_ids
        == {(cell, bank) for cell in WEAK_CELL_IDS for bank in BANK_VARIANT_NAMES}
        and all(
            row.validation_blocks == config.cross_truth_config.validation_blocks
            for row in comparisons
        ),
        "cell_processes_succeeded": len(cell_telemetry) == len(TARGET_CELL_IDS)
        and all(row.exit_status == 0 for row in cell_telemetry),
    }
    classes = {
        cell_id: {
            row.bank_variant: row.expanded_class for row in summaries if row.truth_cell == cell_id
        }
        for cell_id in TARGET_CELL_IDS
    }
    artificial = {
        (row.truth_cell, row.bank_variant): row.artificial_face_contact_count for row in summaries
    }
    full_comparisons = {row.truth_cell: row for row in comparisons if row.bank_variant == "full"}
    outcome = classify_outcome(
        invariants,
        classes,
        artificial,
        full_comparisons,
    )
    return Goal013Result(
        config=config,
        design=selected,
        seed_manifest=manifest,
        evidence=existing,
        calibration_results=calibration,
        validation_results=validation,
        observation_signal_summary=signals,
        representative_profiles=representatives,
        truth_cell_summaries=summaries,
        baseline_intervention_comparisons=comparisons,
        cell_invariants=cell_invariants,
        execution_telemetry=telemetry,
        invariants=invariants,
        outcome=outcome,
    )


def classify_outcome(
    invariants: Mapping[str, bool],
    cell_bank_classes: Mapping[str, Mapping[str, str]],
    artificial_face_counts: Mapping[tuple[str, str], int],
    full_bank_comparisons: Mapping[str, BaselineInterventionComparison],
) -> str:
    """Apply the frozen Goal 013 first-match decision precedence."""
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if set(cell_bank_classes) != set(TARGET_CELL_IDS) or any(
        tuple(banks) != BANK_VARIANT_NAMES for banks in cell_bank_classes.values()
    ):
        return "implementation_blocked"
    if any(len(set(banks.values())) != 1 for banks in cell_bank_classes.values()):
        return "likelihood_approximation_unstable"
    if set(artificial_face_counts) != {
        (cell, bank) for cell in TARGET_CELL_IDS for bank in BANK_VARIANT_NAMES
    }:
        return "implementation_blocked"
    if any(count > 25 for count in artificial_face_counts.values()):
        return "intervention_candidate_domain_unclosed"
    central_classes = cell_bank_classes["cell-04"]
    if any(value != "cell_recoverable" for value in central_classes.values()):
        return "intervention_invalidates_central_positive_control"
    if all(
        all(value == "cell_recoverable" for value in cell_bank_classes[cell].values())
        for cell in WEAK_CELL_IDS
    ):
        return "contrast_balanced_design_restores_low_eta_recovery"
    if set(full_bank_comparisons) != set(WEAK_CELL_IDS):
        return "implementation_blocked"
    has_design_limit = any(
        any(value == "cell_design_limited" for value in cell_bank_classes[cell].values())
        for cell in WEAK_CELL_IDS
    )
    material_all = all(
        comparison.baseline_eta_zero_contact_count - comparison.intervention_eta_zero_contact_count
        >= 25
        and comparison.block_indicator_difference.upper < 0.0
        for comparison in full_bank_comparisons.values()
    )
    if has_design_limit and material_all:
        return "contrast_balancing_contributes_not_resolves"
    return "contrast_balancing_not_supported"


def campaign_digest(result: Goal013Result) -> str:
    """Hash scientific content while excluding execution telemetry."""
    payload = {
        field.name: getattr(result, field.name)
        for field in fields(result)
        if field.name != "execution_telemetry"
    }
    return _projection_digest(payload)


def _baseline_intervention_comparisons(
    config: Goal013Config,
    existing: ExistingEvidence,
    validation: tuple[cross_truth.ValidationResult, ...],
) -> tuple[BaselineInterventionComparison, ...]:
    baseline = {
        (row.truth_cell, row.bank_variant, row.block_index): row.eta_zero_contact
        for row in existing.goal012_contacts
    }
    cells = {cell.cell_id: cell for cell in config.target_truth_cells}
    comparisons: list[BaselineInterventionComparison] = []
    for cell_id in WEAK_CELL_IDS:
        cell = cells[cell_id]
        for bank in BANK_VARIANT_NAMES:
            rows = tuple(
                row for row in validation if row.truth_cell == cell_id and row.bank_variant == bank
            )
            if len(rows) != config.cross_truth_config.validation_blocks:
                raise ValueError("intervention comparison row count is incomplete")
            ordered = tuple(sorted(rows, key=lambda row: row.block_index))
            if tuple(row.block_index for row in ordered) != tuple(range(len(ordered))):
                raise ValueError("intervention comparison block identity is incomplete")
            baseline_indicators = tuple(
                baseline[(cell_id, bank, row.block_index)] for row in ordered
            )
            intervention_indicators = tuple(
                "eta_min" in row.expanded_support_boundary_faces for row in ordered
            )
            differences = tuple(
                int(intervention) - int(reference)
                for intervention, reference in zip(
                    intervention_indicators,
                    baseline_indicators,
                    strict=True,
                )
            )
            interval = normal_mean_interval(differences)
            baseline_count = sum(baseline_indicators)
            intervention_count = sum(intervention_indicators)
            comparisons.append(
                BaselineInterventionComparison(
                    truth_cell=cell_id,
                    truth_rho=cell.rho,
                    truth_eta=cell.eta,
                    bank_variant=bank,
                    validation_blocks=len(rows),
                    baseline_eta_zero_contact_count=baseline_count,
                    intervention_eta_zero_contact_count=intervention_count,
                    contact_count_difference=intervention_count - baseline_count,
                    block_indicator_difference=interval,
                )
            )
    return tuple(comparisons)


def _intervention_detection_blocks(
    root: np.random.SeedSequence,
    *,
    phase: str,
    count: int,
) -> tuple[tuple[cross_truth.CellDetectionSeed, ...], ...]:
    return tuple(
        tuple(
            cross_truth.CellDetectionSeed(
                truth_cell=cell_id,
                detection=_detection_record(phase, block_index, child),
            )
            for cell_id, child in zip(
                TARGET_CELL_IDS,
                block_root.spawn(len(TARGET_CELL_IDS)),
                strict=True,
            )
        )
        for block_index, block_root in enumerate(root.spawn(count))
    )


def _detection_record(
    phase: str,
    index: int,
    sequence: np.random.SeedSequence,
) -> goal004.StreamSeedRecord:
    return goal004.StreamSeedRecord(
        phase=phase,
        index=index,
        stream_role="detection",
        entropy=int(cast(int, sequence.entropy)),
        spawn_key=tuple(int(value) for value in sequence.spawn_key),
        state_words=tuple(int(value) for value in sequence.generate_state(STATE_WORD_COUNT)),
        pool_size=sequence.pool_size,
    )


def _run_cell_task(
    task: tuple[
        goal008.TruthCell,
        cross_truth.CrossTruthConfig,
        goal007.FixedInputs,
        cross_truth.SeedManifest,
    ],
) -> tuple[cross_truth.CellResult, CellExecutionTelemetry]:
    cell, config, fixed, manifest = task
    started = time.perf_counter()
    result = cross_truth.run_truth_cell(
        cell,
        config,
        fixed_inputs=fixed,
        seed_manifest=manifest,
    )
    return result, CellExecutionTelemetry(
        truth_cell=cell.cell_id,
        exit_status=0,
        wall_time_seconds=time.perf_counter() - started,
        maximum_rss_bytes=_maximum_rss_bytes(),
    )


def _current_thread_limits() -> dict[str, str]:
    return {name: os.environ.get(name, "") for name in THREAD_LIMIT_NAMES}


def _validate_production_runtime(
    config: Goal013Config,
    workers: int,
) -> None:
    if not config.is_production:
        return
    if workers != 4:
        raise ValueError("production campaign requires exactly 4 workers")
    if _current_thread_limits() != {name: "1" for name in THREAD_LIMIT_NAMES}:
        raise ValueError("production campaign requires all four thread limits set to 1")
    root = Path(__file__).resolve().parents[3]
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout:
        raise ValueError("production campaign requires a clean source state")


def _maximum_rss_bytes() -> int:
    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    multiplier = 1 if sys.platform == "darwin" else 1024
    return max(1, int(maximum * multiplier))


def _projection_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            _canonical_value(value),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _canonical_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        instance = cast(Any, value)
        return {
            field.name: _canonical_value(getattr(instance, field.name))
            for field in fields(instance)
        }
    if isinstance(value, np.ndarray):
        return _canonical_value(value.tolist())
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


__all__ = [
    "BANK_VARIANT_NAMES",
    "DEFAULT_CONFIG",
    "DEFAULT_GOAL009_EVIDENCE_DIR",
    "DEFAULT_GOAL012_EVIDENCE_DIR",
    "TARGET_CELL_IDS",
    "WEAK_CELL_IDS",
    "BaselineInterventionComparison",
    "CampaignExecutionTelemetry",
    "CellExecutionTelemetry",
    "Goal013Config",
    "Goal013Result",
    "Goal013SeedManifest",
    "authenticate_existing_evidence",
    "build_fixed_inputs",
    "campaign_digest",
    "classify_outcome",
    "run_campaign",
    "smoke_config",
    "spawn_seed_manifest",
]
