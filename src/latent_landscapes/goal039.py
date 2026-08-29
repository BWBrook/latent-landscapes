"""Arc 2A predator-only recoverability pilot."""

from __future__ import annotations

import csv
import json
import math
import multiprocessing as mp
import os
import platform
import socket
import subprocess
import time
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean, median
from typing import Any

import matplotlib as mpl
import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal001.design import DesignSite
from latent_landscapes.goal001.observations import Observation
from latent_landscapes.goal002.baseline import (
    fit_time_stratified_baseline,
    score_time_stratified_baseline,
)
from latent_landscapes.goal002.calibration import (
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal004 import benchmark as goal004
from latent_landscapes.goal004.likelihood import (
    record_detection_probabilities,
    score_predictions,
)
from latent_landscapes.goal004.observations import REPLICATES, SURVEY_TIMES
from latent_landscapes.goal006.spread import (
    ContrastSpreadTruth,
    compute_contrast_spread,
    compute_paired_spreads,
    sample_edge_shock_vector,
)
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal007.likelihood import joint_category_weights
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal019 import PROBABILITY_GRID, RHO_GRID
from latent_landscapes.goal021 import (
    ThreeParameterProfile,
    classify_outcome,
    summarize_support,
    three_parameter_profile,
)
from latent_landscapes.goal022 import REFINED_ETA_GRID
from latent_landscapes.goal038 import generate_pilot_truths, no_resistance_diagnostic

mpl.use("Agg")
mpl.rcParams["svg.hashsalt"] = "latent-landscapes-goal039"
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("artifacts/goal039_arc2a_pilot")
EXPECTED_FILES = (
    "truth_design.csv",
    "calibration_statistics.csv",
    "validation_metrics.csv",
    "truth_summary.csv",
    "summary.json",
    "run_provenance.json",
    "review.md",
    "truth_level_recovery.svg",
)
MASTER_SEED = goal011.MASTER_SEED
INTEGRATION_BANK_SIZE = goal011.INTEGRATION_BANK_SIZE
CALIBRATION_REPLICATES = 250
VALIDATION_REPLICATES = 250
CALIBRATION_RANK_ONE_BASED = 239


@dataclass(frozen=True, slots=True)
class TruthCondition:
    condition_id: str
    design_role: str
    rho: float
    eta: float
    probability: float


def default_truths() -> tuple[TruthCondition, ...]:
    rows = tuple(
        TruthCondition(point.point_id, point.design_role, point.rho, point.eta, point.p)
        for point in generate_pilot_truths()
    )
    diagnostic = no_resistance_diagnostic()
    return (
        *rows,
        TruthCondition(
            diagnostic.point_id,
            diagnostic.design_role,
            diagnostic.rho,
            diagnostic.eta,
            diagnostic.p,
        ),
    )


@dataclass(frozen=True, slots=True)
class Goal039Config:
    master_seed: int = MASTER_SEED
    bank_size: int = INTEGRATION_BANK_SIZE
    calibration_replicates: int = CALIBRATION_REPLICATES
    validation_replicates: int = VALIDATION_REPLICATES
    calibration_rank_one_based: int = CALIBRATION_RANK_ONE_BASED
    base_rhos: tuple[float, ...] = RHO_GRID
    base_etas: tuple[float, ...] = REFINED_ETA_GRID
    base_probabilities: tuple[float, ...] = PROBABILITY_GRID
    truths: tuple[TruthCondition, ...] = default_truths()

    def __post_init__(self) -> None:
        if self.bank_size <= 0:
            raise ValueError("integration bank size must be positive")
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within the calibration ensemble")
        for name, values in (
            ("rho", self.base_rhos),
            ("eta", self.base_etas),
            ("probability", self.base_probabilities),
        ):
            array = np.asarray(values, dtype=np.float64)
            if (
                array.ndim != 1
                or len(array) == 0
                or not np.isfinite(array).all()
                or (array < 0.0).any()
                or (name != "eta" and (array <= 0.0).any())
                or (name == "probability" and (array >= 1.0).any())
                or (np.diff(array) <= 0.0).any()
            ):
                raise ValueError(f"{name} grid is invalid")
        ids = tuple(truth.condition_id for truth in self.truths)
        coordinates = tuple((truth.rho, truth.eta, truth.probability) for truth in self.truths)
        if (
            not self.truths
            or len(ids) != len(set(ids))
            or len(coordinates) != len(set(coordinates))
        ):
            raise ValueError("truth conditions must have unique identifiers and coordinates")
        if any(
            not math.isfinite(value)
            for truth in self.truths
            for value in (truth.rho, truth.eta, truth.probability)
        ):
            raise ValueError("truth coordinates must be finite")
        if any(
            truth.rho <= 0.0 or truth.eta < 0.0 or not 0.0 < truth.probability < 1.0
            for truth in self.truths
        ):
            raise ValueError("truth coordinates lie outside valid parameter domains")

    @property
    def is_production(self) -> bool:
        return self == Goal039Config()

    @property
    def seed_config(self) -> goal011.Goal011Config:
        return goal011.Goal011Config(
            master_seed=self.master_seed,
            bank_size=self.bank_size,
            calibration_replicates=self.calibration_replicates,
            validation_replicates=self.validation_replicates,
            calibration_rank_one_based=self.calibration_rank_one_based,
        )


DEFAULT_CONFIG = Goal039Config()


def smoke_config() -> Goal039Config:
    """Return a small implementation check without scientific meaning."""
    return Goal039Config(
        bank_size=8,
        calibration_replicates=4,
        validation_replicates=4,
        calibration_rank_one_based=4,
        base_rhos=(0.5, 1.0, 2.0),
        base_etas=(0.0, 0.5, 1.0, 1.5, 2.0),
        base_probabilities=(0.35, 0.65, 0.85),
        truths=(*default_truths()[:2], default_truths()[-1]),
    )


def timing_config() -> Goal039Config:
    """Return a full-grid, full-design timing probe without scientific meaning."""
    return Goal039Config(
        bank_size=64,
        calibration_replicates=2,
        validation_replicates=2,
        calibration_rank_one_based=2,
    )


@dataclass(frozen=True, slots=True)
class ConditionModel:
    truth: TruthCondition
    rhos: tuple[float, ...]
    etas: tuple[float, ...]
    probabilities: tuple[float, ...]
    category_weights: NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class CalibrationMetric:
    condition_id: str
    dataset_index: int
    likelihood_ratio_at_truth: float
    detected_record_count: int
    sampled_sites_arrived_by_day_60: int


@dataclass(frozen=True, slots=True)
class ValidationMetric:
    condition_id: str
    dataset_index: int
    detected_record_count: int
    sampled_sites_arrived_by_day_60: int
    truth_included: bool
    eta_zero_excluded: bool
    support_cell_count: int
    support_component_count: int
    support_boundary_contact: bool
    log_rho_estimate: float
    eta_estimate: float
    probability_estimate: float
    log_rho_error: float
    eta_error: float
    probability_error: float
    absolute_log_rho_error: float
    absolute_eta_error: float
    absolute_probability_error: float
    projected_log_rho_width: float
    projected_eta_width: float
    projected_probability_width: float
    heldout_log_score_advantage_per_record: float
    paired_brier_difference: float


@dataclass(frozen=True, slots=True)
class TruthSummary:
    condition_id: str
    design_role: str
    truth_rho: float
    truth_eta: float
    truth_probability: float
    cutoff: float
    validation_count: int
    coverage_success_count: int
    coverage: float
    coverage_lower: float
    coverage_upper: float
    eta_zero_exclusion_count: int
    eta_zero_exclusion_probability: float
    connected_interior_count: int
    boundary_contact_count: int
    median_sampled_sites_arrived_by_day_60: float
    median_detected_record_count: float
    mean_log_rho_bias: float
    mean_eta_bias: float
    mean_probability_bias: float
    median_absolute_log_rho_error: float
    median_absolute_eta_error: float
    median_absolute_probability_error: float
    median_projected_log_rho_width: float
    median_projected_eta_width: float
    median_projected_probability_width: float
    mean_heldout_log_score_advantage_per_record: float
    mean_paired_brier_difference: float
    outcome: str


@dataclass(frozen=True, slots=True)
class Goal039Result:
    config: Goal039Config
    calibration_metrics: tuple[CalibrationMetric, ...]
    validation_metrics: tuple[ValidationMetric, ...]
    truth_summaries: tuple[TruthSummary, ...]
    invariants: dict[str, bool]
    outcome: str
    worker_count: int
    runtime_seconds: float
    bank_runtime_seconds: float
    calibration_runtime_seconds: float
    validation_runtime_seconds: float
    source_commit: str


@dataclass(frozen=True, slots=True)
class _GeneratedDataset:
    truth: ContrastSpreadTruth
    records: tuple[Observation, ...]


@dataclass(frozen=True, slots=True)
class _WorkerContext:
    config: Goal039Config
    fixed: goal007.FixedInputs
    models: tuple[ConditionModel, ...]


_BANK_FIXED: goal007.FixedInputs | None = None
_BANK_ETAS: tuple[float, ...] = ()
_WORKER_CONTEXT: _WorkerContext | None = None


def _sorted_union(base: Sequence[float], additions: Sequence[float]) -> tuple[float, ...]:
    return tuple(sorted({float(value) for value in (*base, *additions)}))


def candidate_grid(base: Sequence[float], truth: float) -> tuple[float, ...]:
    """Add one exact generating coordinate to an otherwise frozen grid."""
    return _sorted_union(base, (truth,))


def _init_bank_worker(fixed: goal007.FixedInputs, etas: tuple[float, ...]) -> None:
    global _BANK_FIXED, _BANK_ETAS
    _BANK_FIXED = fixed
    _BANK_ETAS = etas


def _bank_worker(record: goal007.StreamSeedRecord) -> tuple[int, NDArray[np.float64]]:
    if _BANK_FIXED is None or not _BANK_ETAS:
        raise RuntimeError("bank worker is not initialized")
    _, truths = compute_paired_spreads(
        _BANK_FIXED.landscape,
        rng=goal007.generator_from_seed_record(record),
        etas=_BANK_ETAS,
        rho=1.0,
    )
    sites = _BANK_FIXED.design.sites
    row = np.stack(
        [
            np.asarray([truth.arrival[site.row, site.col] for site in sites], dtype=np.float64)
            for truth in truths
        ]
    )
    return record.index, row


def build_shared_bank(
    fixed: goal007.FixedInputs,
    records: tuple[goal007.StreamSeedRecord, ...],
    etas: tuple[float, ...],
    workers: int,
) -> goal007.IntegrationBank:
    """Build one paired integration bank for every required eta slice."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    if workers == 1:
        return goal007.build_integration_bank(fixed, records, etas)
    chunksize = max(1, len(records) // (workers * 8))
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=mp.get_context("fork"),
        initializer=_init_bank_worker,
        initargs=(fixed, etas),
    ) as executor:
        indexed = tuple(executor.map(_bank_worker, records, chunksize=chunksize))
    indexed = tuple(sorted(indexed, key=lambda item: item[0]))
    arrivals = np.stack([row for _, row in indexed])
    return goal007.IntegrationBank(
        tuple(site.site_id for site in fixed.design.sites),
        etas,
        arrivals,
    )


def build_condition_models(
    config: Goal039Config,
    bank: goal007.IntegrationBank,
) -> tuple[ConditionModel, ...]:
    """Slice one shared bank into exact-truth condition grids."""
    union_rhos = _sorted_union(config.base_rhos, tuple(truth.rho for truth in config.truths))
    union_weights = joint_category_weights(bank.arrivals, np.asarray(union_rhos, dtype=np.float64))
    eta_lookup = {value: index for index, value in enumerate(bank.etas)}
    rho_lookup = {value: index for index, value in enumerate(union_rhos)}
    models: list[ConditionModel] = []
    for truth in config.truths:
        etas = candidate_grid(config.base_etas, truth.eta)
        rhos = candidate_grid(config.base_rhos, truth.rho)
        probabilities = candidate_grid(config.base_probabilities, truth.probability)
        eta_indices = np.asarray([eta_lookup[value] for value in etas], dtype=np.int64)
        rho_indices = np.asarray([rho_lookup[value] for value in rhos], dtype=np.int64)
        weights = union_weights[eta_indices][:, rho_indices].copy()
        weights.flags.writeable = False
        models.append(ConditionModel(truth, rhos, etas, probabilities, weights))
    return tuple(models)


def _ordered_sites(sites: tuple[DesignSite, ...]) -> tuple[DesignSite, ...]:
    return tuple(sorted(sites, key=lambda site: (site.cluster_id, site.site_offset_index)))


def _records_from_rng(
    sites: tuple[DesignSite, ...],
    truth: ContrastSpreadTruth,
    detection_rng: np.random.Generator,
    probability: float,
) -> tuple[Observation, ...]:
    records: list[Observation] = []
    for site in _ordered_sites(sites):
        for survey_time in SURVEY_TIMES:
            occupied = bool(truth.arrival[site.row, site.col] <= survey_time)
            for replicate in REPLICATES:
                records.append(
                    Observation(
                        cluster_id=site.cluster_id,
                        split=site.split,
                        stratum_index=site.stratum_index,
                        site_id=site.site_id,
                        site_offset_index=site.site_offset_index,
                        row=site.row,
                        col=site.col,
                        time=survey_time,
                        replicate=replicate,
                        detected=int(occupied and detection_rng.random() < probability),
                    )
                )
    return tuple(records)


def generate_paired_datasets(
    fixed: goal007.FixedInputs,
    seed: goal011.DatasetSeedRecord,
    truths: tuple[TruthCondition, ...],
) -> tuple[_GeneratedDataset, ...]:
    """Generate all truth conditions from paired process and detection streams."""
    shocks = sample_edge_shock_vector(
        fixed.landscape,
        goal007.generator_from_seed_record(seed.process),
    )
    rows: list[_GeneratedDataset] = []
    for truth in truths:
        generated = compute_contrast_spread(
            fixed.landscape,
            truth.eta,
            edge_shocks=shocks,
            rho=truth.rho,
        )
        records = _records_from_rng(
            fixed.design.sites,
            generated,
            goal004.generator_from_seed_record(seed.detection),
            truth.probability,
        )
        rows.append(_GeneratedDataset(generated, records))
    return tuple(rows)


def _profile(model: ConditionModel, records: Sequence[Observation]) -> ThreeParameterProfile:
    return three_parameter_profile(
        site_ids=_site_ids(),
        records=records,
        category_weights=model.category_weights,
        rhos=model.rhos,
        etas=model.etas,
        probabilities=model.probabilities,
    )


def _site_ids() -> tuple[str, ...]:
    return tuple(site.site_id for site in _worker_context().fixed.design.sites)


def _lr_at_truth(profile: ThreeParameterProfile, truth: TruthCondition) -> float:
    eta_index = int(np.flatnonzero(profile.etas == truth.eta)[0])
    rho_index = int(np.flatnonzero(profile.rhos == truth.rho)[0])
    p_index = int(np.flatnonzero(profile.probabilities == truth.probability)[0])
    return float(
        2.0
        * (profile.maximum_log_likelihood - profile.log_likelihoods[eta_index, rho_index, p_index])
    )


def _day_60_arrival_count(fixed: goal007.FixedInputs, truth: ContrastSpreadTruth) -> int:
    return int(
        sum(truth.arrival[site.row, site.col] <= SURVEY_TIMES[-1] for site in fixed.design.sites)
    )


def _init_worker(context: _WorkerContext) -> None:
    global _WORKER_CONTEXT
    _WORKER_CONTEXT = context


def _worker_context() -> _WorkerContext:
    if _WORKER_CONTEXT is None:
        raise RuntimeError("campaign worker is not initialized")
    return _WORKER_CONTEXT


def _calibration_worker(seed: goal011.DatasetSeedRecord) -> tuple[CalibrationMetric, ...]:
    context = _worker_context()
    datasets = generate_paired_datasets(context.fixed, seed, context.config.truths)
    rows: list[CalibrationMetric] = []
    for model, dataset in zip(context.models, datasets, strict=True):
        profile = _profile(model, dataset.records)
        rows.append(
            CalibrationMetric(
                model.truth.condition_id,
                seed.index,
                _lr_at_truth(profile, model.truth),
                sum(record.detected for record in dataset.records),
                _day_60_arrival_count(context.fixed, dataset.truth),
            )
        )
    return tuple(rows)


def _point_estimate(profile: ThreeParameterProfile) -> tuple[float, float, float]:
    return (
        fmean(math.log(rho) for rho, _, _ in profile.mle_cells),
        fmean(eta for _, eta, _ in profile.mle_cells),
        fmean(probability for _, _, probability in profile.mle_cells),
    )


def _eta_zero_excluded(profile: ThreeParameterProfile, cutoff: float) -> bool:
    statistic = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
    support = statistic <= cutoff
    eta_zero = np.flatnonzero(profile.etas == 0.0)
    if len(eta_zero) != 1:
        raise ValueError("candidate eta grid must contain eta = 0 exactly once")
    return not bool(support[int(eta_zero[0])].any())


def _predictive_comparison(
    model: ConditionModel,
    records: tuple[Observation, ...],
) -> tuple[float, float]:
    training = tuple(record for record in records if record.split == "training")
    holdout = tuple(record for record in records if record.split == "holdout")
    training_profile = _profile(model, training)
    site_ids = _site_ids()
    process_scores = tuple(
        score_predictions(
            record_detection_probabilities(
                weights=model.category_weights[eta_index, rho_index],
                site_ids=site_ids,
                records=holdout,
                detection_probability=float(training_profile.probabilities[p_index]),
            ),
            holdout,
        )
        for eta_index, rho_index, p_index in training_profile.mle_indices
    )
    neutral = fit_time_stratified_baseline(training, survey_times=SURVEY_TIMES)
    neutral_score = score_time_stratified_baseline(neutral, holdout)
    process_log = min(score.total_log_score for score in process_scores)
    process_brier = max(score.mean_brier_score for score in process_scores)
    return (
        (process_log - neutral_score.total_log_score) / len(holdout),
        process_brier - neutral_score.mean_brier_score,
    )


def _validation_worker(
    task: tuple[goal011.DatasetSeedRecord, tuple[tuple[str, float], ...]],
) -> tuple[ValidationMetric, ...]:
    seed, cutoffs = task
    context = _worker_context()
    cutoff_by_id = dict(cutoffs)
    datasets = generate_paired_datasets(context.fixed, seed, context.config.truths)
    rows: list[ValidationMetric] = []
    for model, dataset in zip(context.models, datasets, strict=True):
        cutoff = cutoff_by_id[model.truth.condition_id]
        profile = _profile(model, dataset.records)
        support = summarize_support(
            profile,
            cutoff=cutoff,
            truth_rho=model.truth.rho,
            truth_eta=model.truth.eta,
            truth_probability=model.truth.probability,
        )
        log_rho_estimate, eta_estimate, probability_estimate = _point_estimate(profile)
        log_rho_error = log_rho_estimate - math.log(model.truth.rho)
        eta_error = eta_estimate - model.truth.eta
        probability_error = probability_estimate - model.truth.probability
        log_score_advantage, brier_difference = _predictive_comparison(model, dataset.records)
        rows.append(
            ValidationMetric(
                model.truth.condition_id,
                seed.index,
                sum(record.detected for record in dataset.records),
                _day_60_arrival_count(context.fixed, dataset.truth),
                support.truth_included,
                _eta_zero_excluded(profile, cutoff),
                support.cell_count,
                support.component_count,
                support.boundary_contact,
                log_rho_estimate,
                eta_estimate,
                probability_estimate,
                log_rho_error,
                eta_error,
                probability_error,
                abs(log_rho_error),
                abs(eta_error),
                abs(probability_error),
                support.projected_log_rho_width,
                support.projected_eta_width,
                support.projected_probability_width,
                log_score_advantage,
                brier_difference,
            )
        )
    return tuple(rows)


def _run_phase(
    worker: Any,
    tasks: Sequence[Any],
    context: _WorkerContext,
    workers: int,
) -> tuple[Any, ...]:
    _init_worker(context)
    if workers == 1:
        return tuple(worker(task) for task in tasks)
    chunksize = max(1, len(tasks) // (workers * 4))
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as executor:
        return tuple(executor.map(worker, tasks, chunksize=chunksize))


def _summarize_truth(
    config: Goal039Config,
    truth: TruthCondition,
    cutoff: float,
    rows: tuple[ValidationMetric, ...],
) -> TruthSummary:
    selected = tuple(row for row in rows if row.condition_id == truth.condition_id)
    if len(selected) != config.validation_replicates:
        raise ValueError("truth validation rows are incomplete")
    coverage_count = sum(row.truth_included for row in selected)
    coverage = wilson_interval(coverage_count, len(selected))
    connected = sum(
        row.support_component_count == 1 and not row.support_boundary_contact for row in selected
    )
    boundary = sum(row.support_boundary_contact for row in selected)
    eta_zero_count = sum(row.eta_zero_excluded for row in selected)
    rho_error = median(row.absolute_log_rho_error for row in selected)
    eta_error = median(row.absolute_eta_error for row in selected)
    probability_error = median(row.absolute_probability_error for row in selected)
    rho_width = median(row.projected_log_rho_width for row in selected)
    eta_width = median(row.projected_eta_width for row in selected)
    probability_width = median(row.projected_probability_width for row in selected)
    outcome = (
        "no_resistance_diagnostic"
        if truth.design_role == "no_resistance_diagnostic"
        else classify_outcome(
            invariants={"truth_metrics_complete": True},
            connected_interior_count=connected,
            validation_count=len(selected),
            coverage=coverage,
            median_log_rho_error=rho_error,
            median_eta_error=eta_error,
            median_probability_error=probability_error,
            median_log_rho_width=rho_width,
            median_eta_width=eta_width,
            median_probability_width=probability_width,
        )
    )
    return TruthSummary(
        truth.condition_id,
        truth.design_role,
        truth.rho,
        truth.eta,
        truth.probability,
        cutoff,
        len(selected),
        coverage_count,
        coverage.estimate,
        coverage.lower,
        coverage.upper,
        eta_zero_count,
        eta_zero_count / len(selected),
        connected,
        boundary,
        median(row.sampled_sites_arrived_by_day_60 for row in selected),
        median(row.detected_record_count for row in selected),
        fmean(row.log_rho_error for row in selected),
        fmean(row.eta_error for row in selected),
        fmean(row.probability_error for row in selected),
        rho_error,
        eta_error,
        probability_error,
        rho_width,
        eta_width,
        probability_width,
        fmean(row.heldout_log_score_advantage_per_record for row in selected),
        fmean(row.paired_brier_difference for row in selected),
        outcome,
    )


def _central_generator_reconciled(
    fixed: goal007.FixedInputs,
    seed: goal011.DatasetSeedRecord,
) -> bool:
    central = TruthCondition("central", "reconciliation", 1.0, 1.0, 0.65)
    generated = generate_paired_datasets(fixed, seed, (central,))[0]
    reference_truth, reference_records = goal011.generate_dataset(fixed, seed)
    return bool(
        np.array_equal(generated.truth.arrival, reference_truth.arrival)
        and generated.records == reference_records
    )


def run_goal039(
    config: Goal039Config = DEFAULT_CONFIG,
    *,
    workers: int = 1,
    source_commit: str = "unknown",
) -> Goal039Result:
    """Run the paired Arc 2A calibration and validation campaign."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    started = time.perf_counter()
    fixed = goal011.build_fixed_inputs()
    manifest = goal011.spawn_seed_manifest(config.seed_config)
    union_etas = _sorted_union(config.base_etas, tuple(truth.eta for truth in config.truths))
    bank_started = time.perf_counter()
    bank = build_shared_bank(fixed, manifest.integration_bank, union_etas, workers)
    models = build_condition_models(config, bank)
    bank_runtime = time.perf_counter() - bank_started
    context = _WorkerContext(config, fixed, models)
    calibration_started = time.perf_counter()
    calibration_blocks = _run_phase(_calibration_worker, manifest.calibration, context, workers)
    calibration = tuple(row for block in calibration_blocks for row in block)
    cutoff_rows = tuple(
        (
            truth.condition_id,
            order_statistic_cutoff(
                [
                    row.likelihood_ratio_at_truth
                    for row in calibration
                    if row.condition_id == truth.condition_id
                ],
                rank_one_based=config.calibration_rank_one_based,
            ).cutoff,
        )
        for truth in config.truths
    )
    calibration_runtime = time.perf_counter() - calibration_started
    validation_tasks = tuple((seed, cutoff_rows) for seed in manifest.validation)
    validation_started = time.perf_counter()
    validation_blocks = _run_phase(_validation_worker, validation_tasks, context, workers)
    validation = tuple(row for block in validation_blocks for row in block)
    validation_runtime = time.perf_counter() - validation_started
    cutoff_by_id = dict(cutoff_rows)
    summaries = tuple(
        _summarize_truth(config, truth, cutoff_by_id[truth.condition_id], validation)
        for truth in config.truths
    )
    expected_records = len(fixed.design.sites) * len(SURVEY_TIMES) * len(REPLICATES)
    fixed_invariants = {
        key: value
        for key, value in fixed.invariants.items()
        if key != "known_detection_probability"
    }
    invariants = {
        "fixed_inputs_reconciled": all(fixed_invariants.values()),
        "condition_detection_probabilities_valid": all(
            0.0 < truth.probability < 1.0 for truth in config.truths
        ),
        "truth_count": len(config.truths) == 17
        if config.is_production
        else len(config.truths) in (3, 17),
        "exact_truth_coordinates": all(
            model.rhos.count(model.truth.rho) == 1
            and model.etas.count(model.truth.eta) == 1
            and model.probabilities.count(model.truth.probability) == 1
            for model in models
        ),
        "shared_bank_shape": bank.arrivals.shape
        == (config.bank_size, len(union_etas), len(fixed.design.sites)),
        "paired_calibration_count": len(calibration)
        == len(config.truths) * config.calibration_replicates,
        "paired_validation_count": len(validation)
        == len(config.truths) * config.validation_replicates,
        "complete_observation_histories": expected_records == 1920,
        "finite_metrics": all(
            math.isfinite(value)
            for row in validation
            for value in (
                row.log_rho_estimate,
                row.eta_estimate,
                row.probability_estimate,
                row.projected_log_rho_width,
                row.projected_eta_width,
                row.projected_probability_width,
                row.heldout_log_score_advantage_per_record,
                row.paired_brier_difference,
            )
        ),
        "arc1_central_generator_reconciled": _central_generator_reconciled(
            fixed, manifest.calibration[0]
        ),
    }
    outcome = (
        "ready_for_arc2a_response_surface_review"
        if all(invariants.values()) and config.is_production
        else "non_scientific_smoke"
        if all(invariants.values())
        else "implementation_blocked"
    )
    return Goal039Result(
        config,
        calibration,
        validation,
        summaries,
        invariants,
        outcome,
        workers,
        time.perf_counter() - started,
        bank_runtime,
        calibration_runtime,
        validation_runtime,
        source_commit,
    )


def _write_csv(path: Path, rows: Sequence[Any]) -> None:
    if not rows:
        raise ValueError("CSV rows must not be empty")
    payload = [asdict(row) for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]))
        writer.writeheader()
        writer.writerows(payload)


def _summary_payload(result: Goal039Result) -> dict[str, Any]:
    return {
        "goal": "039-arc2a-predator-recoverability-pilot",
        "outcome": result.outcome,
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "truth_count": len(result.config.truths),
        "calibration_replicates_per_truth": result.config.calibration_replicates,
        "validation_replicates_per_truth": result.config.validation_replicates,
        "common_random_numbers": {
            "process_shocks_paired_across_truths": True,
            "detection_streams_paired_across_truths": True,
            "calibration_validation_roots_disjoint": True,
        },
        "candidate_grid_policy": (
            "Arc 1 base grids plus the exact generating coordinate for each condition"
        ),
        "truth_summaries": [asdict(row) for row in result.truth_summaries],
        "invariants": result.invariants,
    }


def _provenance_payload(result: Goal039Result) -> dict[str, Any]:
    return {
        "completed_utc": datetime.now(UTC).isoformat(),
        "source_commit": result.source_commit,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "worker_count": result.worker_count,
        "runtime_seconds": result.runtime_seconds,
        "stage_runtime_seconds": {
            "shared_bank": result.bank_runtime_seconds,
            "calibration": result.calibration_runtime_seconds,
            "validation_and_prediction": result.validation_runtime_seconds,
        },
        "master_seed": result.config.master_seed,
        "integration_bank_size": result.config.bank_size,
        "thread_limits": {
            name: os.environ.get(name, "")
            for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        },
    }


def _review(result: Goal039Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 039 reduced smoke\n\nImplementation check only; no scientific interpretation.\n"
        )
    summaries = result.truth_summaries
    continuous_summaries = tuple(
        row for row in summaries if row.design_role == "sobol_pilot"
    )
    recoverable = sum(
        row.outcome == "advance_to_cross_truth_three_parameter_benchmark"
        for row in continuous_summaries
    )
    process_better = sum(
        row.mean_paired_brier_difference < 0.0 for row in continuous_summaries
    )
    return f"""# Arc 2A predator recoverability pilot

## Result

Outcome: `{result.outcome}`. All 16 Sobol conditions and the separate no-resistance
diagnostic completed with paired process and observation noise.

This is the raw truth-level review, not yet a fitted response surface. Of the 16
continuous pilot conditions, `{recoverable}` met the inherited Arc 1 recovery
gate and `{process_better}` had lower mean held-out Brier error than the fitted
time-only neutral baseline. Those counts are orientation aids, not the paper
claim; Goal 040 should model the continuous outcomes and paired uncertainty.

## How to read the evidence

- Positive signed bias means overestimation; absolute error ignores direction.
- Coverage is the fraction of 250 validation histories whose locally calibrated
  support contained the generating truth.
- `Eta = 0` exclusion asks whether the data distinguish habitat resistance from
  spatially uniform movement. It is not a success criterion for the diagnostic
  condition where `eta = 0` is true.
- Negative paired Brier difference means the process model predicted held-out
  detections better than the fitted neutral model.
- Supports touching a candidate-domain boundary remain a warning that their
  width may be truncated.

## Next decision

Fit a transparent low-order response surface only if these raw condition
summaries are complete and scientifically interpretable. Do not extend to 32
Sobol points until the first surface has been reviewed.
"""


def _review_figure(result: Goal039Result) -> Figure:
    summaries = result.truth_summaries
    labels = [row.condition_id for row in summaries]
    x = np.arange(len(labels))
    colors = [
        "#d1495b" if row.design_role == "no_resistance_diagnostic" else "#2a6f97"
        for row in summaries
    ]
    figure, axes = plt.subplots(2, 3, figsize=(15.5, 8.2), sharex=True, constrained_layout=True)
    panels = (
        (
            "Median absolute log-rho error",
            [row.median_absolute_log_rho_error for row in summaries],
            0.10,
        ),
        ("Median absolute eta error", [row.median_absolute_eta_error for row in summaries], 0.25),
        (
            "Median absolute detection-p error",
            [row.median_absolute_probability_error for row in summaries],
            0.05,
        ),
        ("Empirical calibrated coverage", [row.coverage for row in summaries], 0.95),
        (
            "Probability support excludes eta = 0",
            [row.eta_zero_exclusion_probability for row in summaries],
            None,
        ),
        (
            "Held-out Brier difference\n(process - neutral; lower is better)",
            [row.mean_paired_brier_difference for row in summaries],
            0.0,
        ),
    )
    for axis, (title, values, reference) in zip(axes.flat, panels, strict=True):
        axis.bar(x, values, color=colors, width=0.78)
        if reference is not None:
            axis.axhline(reference, color="#9b2226", linestyle="--", linewidth=1.2)
        axis.set_title(title)
        axis.grid(axis="y", alpha=0.2)
        axis.set_xticks(x, labels, rotation=55, ha="right")
    figure.suptitle("Raw Arc 2A truth-level recovery before response-surface fitting", fontsize=14)
    return figure


def write_review_bundle(
    result: Goal039Result,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError("output directory must be empty")
    _write_csv(output_dir / "truth_design.csv", result.config.truths)
    _write_csv(output_dir / "calibration_statistics.csv", result.calibration_metrics)
    _write_csv(output_dir / "validation_metrics.csv", result.validation_metrics)
    _write_csv(output_dir / "truth_summary.csv", result.truth_summaries)
    (output_dir / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "run_provenance.json").write_text(
        json.dumps(_provenance_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "review.md").write_text(_review(result), encoding="utf-8")
    figure = _review_figure(result)
    figure.savefig(
        output_dir / "truth_level_recovery.svg",
        format="svg",
        bbox_inches="tight",
        metadata={"Date": None},
    )
    plt.close(figure)
    unexpected = {path.name for path in output_dir.iterdir()} - set(EXPECTED_FILES)
    if unexpected:
        raise RuntimeError(f"unexpected Goal 039 artifact files: {sorted(unexpected)}")
    written = tuple(output_dir / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 039 review bundle is incomplete")
    return written


def current_git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
