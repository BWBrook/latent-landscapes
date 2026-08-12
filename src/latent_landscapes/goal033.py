"""Parameter-specific uncertainty calibration for the Goal 032 joint fit."""

from __future__ import annotations

import csv
import json
import math
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import cast

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from numpy.typing import NDArray

from latent_landscapes import goal031, goal032
from latent_landscapes.goal002.calibration import order_statistic_cutoff, wilson_interval
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.goal011 import benchmark as goal011

DEFAULT_GOAL032_EVIDENCE_DIR = Path(
    "artifacts/goal032_joint_spread_rate_prey_effect_positive_control"
)
PREY_EFFECT_RECOVERED = "prey_effect_recoverable_under_parameter_specific_calibration"
PREY_EFFECT_WEAK = "prey_effect_remains_weak_under_parameter_specific_calibration"
EXPECTED_FILES = (
    "calibration_profile_statistics.csv",
    "validation_marginal_intervals.csv",
    "marginal_summary.csv",
    "representative_profile_curves.csv",
    "summary.json",
    "review.md",
    "parameter_specific_calibration.svg",
)
DEFAULT_CONFIG = goal032.DEFAULT_CONFIG


def smoke_config() -> goal032.Goal032Config:
    """Return the exact reduced Goal 032 configuration."""
    return goal032.smoke_config()


@dataclass(frozen=True, slots=True)
class AnchorCalibrationRow:
    dataset_index: int
    joint_likelihood_ratio_at_truth: float
    predator_detected_visit_count: int
    prey_detected_visit_count: int


@dataclass(frozen=True, slots=True)
class AnchorValidationRow:
    dataset_index: int
    predator_detected_visit_count: int
    prey_detected_visit_count: int
    joint_truth_included: bool
    joint_component_count: int
    joint_boundary_contact: bool
    joint_no_effect_excluded: bool
    mle_rho: float
    absolute_log_rho_error: float
    mle_hazard_ratio: float
    absolute_log_effect_error: float


@dataclass(frozen=True, slots=True)
class Goal032Anchor:
    run_mode: str
    outcome: str
    bank_checksum: str
    joint_cutoff: float
    joint_coverage: float
    joint_coverage_lower: float
    joint_coverage_upper: float
    joint_connected_interior_count: int
    joint_boundary_contact_count: int
    joint_no_effect_exclusion_count: int
    joint_median_rho_width: float
    joint_median_effect_width: float
    goal031_effect_width: float
    goal031_no_effect_exclusion_count: int
    calibration_rows: tuple[AnchorCalibrationRow, ...]
    validation_rows: tuple[AnchorValidationRow, ...]


@dataclass(frozen=True, slots=True)
class CalibrationProfileStatistic:
    dataset_index: int
    joint_likelihood_ratio_at_truth: float
    spread_profile_likelihood_ratio_at_truth: float
    prey_effect_profile_likelihood_ratio_at_truth: float
    predator_detected_visit_count: int
    prey_detected_visit_count: int


@dataclass(frozen=True, slots=True)
class MarginalSupport:
    truth_included: bool
    component_count: int
    boundary_contact: bool
    lower: float
    upper: float
    mask: NDArray[np.bool_]


@dataclass(frozen=True, slots=True)
class MarginalValidationResult:
    dataset_index: int
    predator_detected_visit_count: int
    prey_detected_visit_count: int
    mle_rho: float
    absolute_log_rho_error: float
    spread_truth_included: bool
    spread_component_count: int
    spread_boundary_contact: bool
    spread_support_lower: float
    spread_support_upper: float
    spread_log_support_width: float
    mle_hazard_ratio: float
    absolute_log_effect_error: float
    effect_truth_included: bool
    effect_component_count: int
    effect_boundary_contact: bool
    no_effect_excluded: bool
    effect_support_lower: float
    effect_support_upper: float
    effect_log_support_width: float


@dataclass(frozen=True, slots=True)
class JointReplay:
    truth_included: bool
    component_count: int
    boundary_contact: bool
    no_effect_excluded: bool


@dataclass(frozen=True, slots=True)
class ParameterSummary:
    parameter: str
    cutoff: float
    coverage_count: int
    coverage: float
    coverage_lower: float
    coverage_upper: float
    connected_interior_count: int
    boundary_contact_count: int
    median_absolute_log_error: float
    median_log_support_width: float
    no_effect_exclusion_count: int | None
    passed_prespecified_gates: bool


@dataclass(frozen=True, slots=True)
class ProfileCurvePoint:
    parameter: str
    value: float
    twice_profile_log_likelihood_drop: float
    in_parameter_specific_support: bool
    is_truth: bool
    is_mle: bool


@dataclass(frozen=True, slots=True)
class CalibrationWork:
    statistic: CalibrationProfileStatistic
    valid_histories: bool
    finite_likelihood: bool


@dataclass(frozen=True, slots=True)
class ValidationWork:
    result: MarginalValidationResult
    joint_replay: JointReplay
    profile: goal032.JointProfile | None
    valid_histories: bool
    finite_likelihood: bool


@dataclass(frozen=True, slots=True)
class Goal033Result:
    config: goal032.Goal032Config
    anchor: Goal032Anchor
    calibration_statistics: tuple[CalibrationProfileStatistic, ...]
    validation_results: tuple[MarginalValidationResult, ...]
    marginal_summaries: tuple[ParameterSummary, ParameterSummary]
    representative_curves: tuple[ProfileCurvePoint, ...]
    invariants: dict[str, bool]
    outcome: str

    @property
    def spread_summary(self) -> ParameterSummary:
        return self.marginal_summaries[0]

    @property
    def effect_summary(self) -> ParameterSummary:
        return self.marginal_summaries[1]


_WORKER_CONFIG: goal032.Goal032Config | None = None
_WORKER_FIXED: FixedInputs | None = None
_WORKER_INTEGRATION: goal032.JointArrivalIntegration | None = None


def load_goal032_anchor(
    evidence_dir: Path,
    config: goal032.Goal032Config,
) -> Goal032Anchor:
    """Load the accepted joint result and its deterministic replay surface."""
    root = Path(evidence_dir)
    payload = cast(
        dict[str, object],
        json.loads((root / "summary.json").read_text(encoding="utf-8")),
    )
    if payload.get("goal") != "032-joint-spread-rate-prey-effect-positive-control":
        raise ValueError("Goal 032 evidence has the wrong identity")
    expected_mode = "production" if config.is_production else "reduced_smoke"
    if payload.get("run_mode") != expected_mode:
        raise ValueError("Goal 032 evidence has the wrong run mode")
    expected_outcome = (
        "joint_spread_rate_prey_effect_not_recovered"
        if config.is_production
        else "non_scientific_smoke"
    )
    if payload.get("outcome") != expected_outcome:
        raise ValueError("Goal 032 evidence has the wrong outcome")

    model = _mapping(payload, "model")
    calibration = _mapping(payload, "calibration")
    validation = _mapping(payload, "validation")
    coverage = _mapping(validation, "coverage")
    integration = _mapping(payload, "integration_bank")
    diagnostics = _mapping(payload, "diagnostics")
    goal031_anchor = _mapping(payload, "goal031_anchor")
    expected_model = (
        _float(model, "truth_spread_rate"),
        _float(model, "truth_hazard_ratio"),
        _int(model, "spread_rate_grid_count"),
        _int(model, "prey_effect_grid_count"),
    )
    observed_model = (
        config.truth_rho,
        config.truth_hazard_ratio,
        len(config.rhos),
        len(config.hazard_ratios),
    )
    if expected_model != observed_model:
        raise ValueError("Goal 032 model does not match the frozen configuration")
    expected_counts = (
        _int(calibration, "replicates"),
        _int(calibration, "rank_one_based"),
        _int(validation, "replicates"),
    )
    observed_counts = (
        config.calibration_replicates,
        config.calibration_rank_one_based,
        config.validation_replicates,
    )
    if expected_counts != observed_counts:
        raise ValueError("Goal 032 replicate counts do not match the frozen configuration")

    calibration_rows = tuple(
        AnchorCalibrationRow(
            _csv_int(row, "dataset_index"),
            _csv_float(row, "likelihood_ratio_at_truth"),
            _csv_int(row, "predator_detected_visit_count"),
            _csv_int(row, "prey_detected_visit_count"),
        )
        for row in _read_csv(root / "calibration_statistics.csv")
    )
    validation_rows = tuple(
        AnchorValidationRow(
            _csv_int(row, "dataset_index"),
            _csv_int(row, "predator_detected_visit_count"),
            _csv_int(row, "prey_detected_visit_count"),
            _csv_bool(row, "truth_included"),
            _csv_int(row, "support_component_count"),
            _csv_bool(row, "support_boundary_contact"),
            _csv_bool(row, "no_effect_excluded"),
            _csv_float(row, "mle_rho"),
            _csv_float(row, "absolute_log_rho_error"),
            _csv_float(row, "mle_hazard_ratio"),
            _csv_float(row, "absolute_log_effect_error"),
        )
        for row in _read_csv(root / "validation_results.csv")
    )
    if tuple(row.dataset_index for row in calibration_rows) != tuple(
        range(config.calibration_replicates)
    ):
        raise ValueError("Goal 032 calibration rows are incomplete or out of order")
    if tuple(row.dataset_index for row in validation_rows) != tuple(
        range(config.validation_replicates)
    ):
        raise ValueError("Goal 032 validation rows are incomplete or out of order")
    checksum = integration.get("base_bank_checksum_sha256")
    if not isinstance(checksum, str) or len(checksum) != 64:
        raise ValueError("Goal 032 integration checksum is invalid")
    return Goal032Anchor(
        expected_mode,
        expected_outcome,
        checksum,
        _float(calibration, "cutoff"),
        _float(coverage, "estimate"),
        _float(coverage, "lower"),
        _float(coverage, "upper"),
        _int(validation, "connected_interior_count"),
        _int(diagnostics, "boundary_contact_count"),
        _int(validation, "no_effect_exclusion_count"),
        _float(validation, "median_log_rho_support_width"),
        _float(validation, "median_log_effect_support_width"),
        _float(goal031_anchor, "median_log_effect_support_width"),
        _int(goal031_anchor, "no_effect_exclusion_count"),
        calibration_rows,
        validation_rows,
    )


def profile_likelihood_drops(
    profile: goal032.JointProfile,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return spread and prey-effect profile likelihood-ratio drops."""
    spread_profile = np.max(profile.log_likelihoods, axis=1)
    effect_profile = np.max(profile.log_likelihoods, axis=0)
    return (
        np.maximum(0.0, 2.0 * (profile.maximum_log_likelihood - spread_profile)),
        np.maximum(0.0, 2.0 * (profile.maximum_log_likelihood - effect_profile)),
    )


def summarize_marginal_support(
    values: NDArray[np.float64],
    drops: NDArray[np.float64],
    cutoff: float,
    truth: float,
) -> MarginalSupport:
    """Summarize a one-dimensional calibrated profile support set."""
    if values.ndim != 1 or drops.shape != values.shape:
        raise ValueError("profile values and drops must be aligned vectors")
    if not np.isfinite(values).all() or not np.isfinite(drops).all() or cutoff < 0.0:
        raise ValueError("profile support inputs must be finite and cutoff non-negative")
    mask = drops <= cutoff
    indices = np.flatnonzero(mask)
    if len(indices) == 0:
        raise RuntimeError("marginal profile support must not be empty")
    truth_index = _unique_index(tuple(float(value) for value in values), truth, "truth")
    starts = mask & ~np.concatenate((np.asarray((False,)), mask[:-1]))
    return MarginalSupport(
        truth_included=bool(mask[truth_index]),
        component_count=int(starts.sum()),
        boundary_contact=bool(mask[0] or mask[-1]),
        lower=float(values[int(indices.min())]),
        upper=float(values[int(indices.max())]),
        mask=mask,
    )


def classify_outcome(
    *,
    invariants: dict[str, bool],
    effect_summary: ParameterSummary,
    validation_count: int,
) -> str:
    """Classify whether the separately calibrated prey effect is recoverable."""
    if not invariants or not all(invariants.values()) or validation_count <= 0:
        return "implementation_blocked"
    required_count = math.ceil(0.95 * validation_count)
    recovered = (
        effect_summary.coverage_lower <= 0.95 <= effect_summary.coverage_upper
        and effect_summary.connected_interior_count >= required_count
        and effect_summary.no_effect_exclusion_count is not None
        and effect_summary.no_effect_exclusion_count >= required_count
        and effect_summary.median_absolute_log_error <= 0.20
        and effect_summary.median_log_support_width <= 0.80
    )
    return PREY_EFFECT_RECOVERED if recovered else PREY_EFFECT_WEAK


def run_goal033(
    goal032_evidence_dir: Path = DEFAULT_GOAL032_EVIDENCE_DIR,
    config: goal032.Goal032Config = DEFAULT_CONFIG,
    *,
    workers: int = 1,
) -> Goal033Result:
    """Run the frozen parameter-specific calibration diagnostic."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    anchor = load_goal032_anchor(goal032_evidence_dir, config)
    fixed = goal011.build_fixed_inputs()
    manifest = goal031.spawn_seed_manifest(config.generation_config)
    base_bank = goal031._build_arrival_bank(fixed, manifest.bank_seeds, workers)
    sites = tuple(sorted(fixed.design.sites, key=lambda value: value.site_id))
    integration = goal032.build_joint_arrival_integration(
        base_bank,
        tuple(site.site_id for site in sites),
        config.rhos,
        config.hazard_ratios,
    )
    calibration_work = _run_calibration_tasks(
        manifest.calibration, config, fixed, integration, workers
    )
    calibration_rows = tuple(work.statistic for work in calibration_work)
    spread_cutoff = order_statistic_cutoff(
        [row.spread_profile_likelihood_ratio_at_truth for row in calibration_rows],
        rank_one_based=config.calibration_rank_one_based,
    ).cutoff
    effect_cutoff = order_statistic_cutoff(
        [row.prey_effect_profile_likelihood_ratio_at_truth for row in calibration_rows],
        rank_one_based=config.calibration_rank_one_based,
    ).cutoff
    validation_work = _run_validation_tasks(
        manifest.validation,
        config,
        fixed,
        integration,
        spread_cutoff,
        effect_cutoff,
        anchor.joint_cutoff,
        workers,
    )
    validation_rows = tuple(work.result for work in validation_work)
    representative_profile = validation_work[0].profile
    if representative_profile is None:
        raise RuntimeError("representative profile is missing")
    representative_curves = _profile_curve_rows(
        representative_profile,
        spread_cutoff,
        effect_cutoff,
        config,
    )
    spread_summary = _parameter_summary(
        "spread_rate", spread_cutoff, validation_rows, config.validation_replicates
    )
    effect_summary = _parameter_summary(
        "prey_effect", effect_cutoff, validation_rows, config.validation_replicates
    )
    all_dataset_seeds = (*manifest.calibration, *manifest.validation)
    seed_streams = {
        (
            seed.process_seed,
            seed.predator_detection_seed,
            seed.prey_seed,
            seed.prey_detection_seed,
        )
        for seed in all_dataset_seeds
    }
    invariants = {
        "goal032_anchor_loaded": True,
        "fixed_spatial_inputs_reconciled": all(fixed.invariants.values()),
        "integration_bank_reconciled": integration.bank_checksum == anchor.bank_checksum,
        "calibration_replay_reconciled": _calibration_reconciled(
            calibration_rows, anchor.calibration_rows
        ),
        "validation_replay_reconciled": _validation_reconciled(
            validation_rows,
            tuple(work.joint_replay for work in validation_work),
            anchor.validation_rows,
        ),
        "profile_statistics_bounded_by_joint_statistic": all(
            row.spread_profile_likelihood_ratio_at_truth
            <= row.joint_likelihood_ratio_at_truth + 1e-10
            and row.prey_effect_profile_likelihood_ratio_at_truth
            <= row.joint_likelihood_ratio_at_truth + 1e-10
            for row in calibration_rows
        ),
        "calibration_histories_valid": all(work.valid_histories for work in calibration_work),
        "validation_histories_valid": all(work.valid_histories for work in validation_work),
        "finite_calibration_likelihoods": all(work.finite_likelihood for work in calibration_work),
        "finite_validation_likelihoods": all(work.finite_likelihood for work in validation_work),
        "separate_cutoffs_finite": math.isfinite(spread_cutoff)
        and spread_cutoff >= 0.0
        and math.isfinite(effect_cutoff)
        and effect_cutoff >= 0.0,
        "independent_seed_streams": len(seed_streams) == len(all_dataset_seeds)
        and len(set(manifest.bank_seeds)) == config.bank_size,
        "calibration_count": len(calibration_rows) == config.calibration_replicates,
        "validation_count": len(validation_rows) == config.validation_replicates,
        "representative_curve_count": len(representative_curves)
        == len(config.rhos) + len(config.hazard_ratios),
    }
    outcome = classify_outcome(
        invariants=invariants,
        effect_summary=effect_summary,
        validation_count=len(validation_rows),
    )
    if not config.is_production:
        outcome = "non_scientific_smoke" if all(invariants.values()) else "implementation_blocked"
    return Goal033Result(
        config,
        anchor,
        calibration_rows,
        validation_rows,
        (spread_summary, effect_summary),
        representative_curves,
        invariants,
        outcome,
    )


def _init_worker(
    config: goal032.Goal032Config,
    fixed: FixedInputs,
    integration: goal032.JointArrivalIntegration,
) -> None:
    global _WORKER_CONFIG, _WORKER_FIXED, _WORKER_INTEGRATION
    _WORKER_CONFIG = config
    _WORKER_FIXED = fixed
    _WORKER_INTEGRATION = integration


def _worker_context() -> tuple[
    goal032.Goal032Config,
    FixedInputs,
    goal032.JointArrivalIntegration,
]:
    if _WORKER_CONFIG is None or _WORKER_FIXED is None or _WORKER_INTEGRATION is None:
        raise RuntimeError("Goal 033 worker was not initialized")
    return _WORKER_CONFIG, _WORKER_FIXED, _WORKER_INTEGRATION


def _run_calibration_tasks(
    seeds: tuple[goal031.DatasetSeed, ...],
    config: goal032.Goal032Config,
    fixed: FixedInputs,
    integration: goal032.JointArrivalIntegration,
    workers: int,
) -> tuple[CalibrationWork, ...]:
    _init_worker(config, fixed, integration)
    if workers == 1:
        return tuple(_calibration_worker(seed) for seed in seeds)
    chunksize = max(1, len(seeds) // (workers * 8))
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as executor:
        return tuple(executor.map(_calibration_worker, seeds, chunksize=chunksize))


def _run_validation_tasks(
    seeds: tuple[goal031.DatasetSeed, ...],
    config: goal032.Goal032Config,
    fixed: FixedInputs,
    integration: goal032.JointArrivalIntegration,
    spread_cutoff: float,
    effect_cutoff: float,
    joint_cutoff: float,
    workers: int,
) -> tuple[ValidationWork, ...]:
    _init_worker(config, fixed, integration)
    tasks = tuple((seed, spread_cutoff, effect_cutoff, joint_cutoff) for seed in seeds)
    if workers == 1:
        return tuple(_validation_worker(task) for task in tasks)
    chunksize = max(1, len(tasks) // (workers * 8))
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as executor:
        return tuple(executor.map(_validation_worker, tasks, chunksize=chunksize))


def _calibration_worker(seed: goal031.DatasetSeed) -> CalibrationWork:
    config, fixed, integration = _worker_context()
    _, histories = goal031.generate_cross_layer_dataset(seed, config.generation_config, fixed)
    profile = goal032.joint_profile(histories, integration, config)
    spread_drops, effect_drops = profile_likelihood_drops(profile)
    rho_index = _unique_index(tuple(profile.rhos), config.truth_rho, "truth spread rate")
    effect_index = _unique_index(
        tuple(profile.hazard_ratios), config.truth_hazard_ratio, "truth prey effect"
    )
    statistic = CalibrationProfileStatistic(
        seed.index,
        goal032._likelihood_ratio_at_truth(profile, config.truth_rho, config.truth_hazard_ratio),
        float(spread_drops[rho_index]),
        float(effect_drops[effect_index]),
        goal031._detected_visit_count(histories, predator=True),
        goal031._detected_visit_count(histories, predator=False),
    )
    return CalibrationWork(
        statistic,
        goal031._histories_valid(histories, config.generation_config),
        bool(np.isfinite(profile.log_likelihoods).all()),
    )


def _validation_worker(
    task: tuple[goal031.DatasetSeed, float, float, float],
) -> ValidationWork:
    seed, spread_cutoff, effect_cutoff, joint_cutoff = task
    config, fixed, integration = _worker_context()
    _, histories = goal031.generate_cross_layer_dataset(seed, config.generation_config, fixed)
    profile = goal032.joint_profile(histories, integration, config)
    spread_drops, effect_drops = profile_likelihood_drops(profile)
    spread = summarize_marginal_support(profile.rhos, spread_drops, spread_cutoff, config.truth_rho)
    effect = summarize_marginal_support(
        profile.hazard_ratios,
        effect_drops,
        effect_cutoff,
        config.truth_hazard_ratio,
    )
    joint = goal032.summarize_joint_support(
        profile, joint_cutoff, config.truth_rho, config.truth_hazard_ratio
    )
    result = MarginalValidationResult(
        seed.index,
        goal031._detected_visit_count(histories, predator=True),
        goal031._detected_visit_count(histories, predator=False),
        profile.mle_rho,
        abs(math.log(profile.mle_rho / config.truth_rho)),
        spread.truth_included,
        spread.component_count,
        spread.boundary_contact,
        spread.lower,
        spread.upper,
        math.log(spread.upper / spread.lower),
        profile.mle_hazard_ratio,
        abs(math.log(profile.mle_hazard_ratio / config.truth_hazard_ratio)),
        effect.truth_included,
        effect.component_count,
        effect.boundary_contact,
        bool(not effect.mask[0]),
        effect.lower,
        effect.upper,
        math.log(effect.upper / effect.lower),
    )
    return ValidationWork(
        result,
        JointReplay(
            joint.truth_included,
            joint.component_count,
            joint.boundary_contact,
            joint.no_effect_excluded,
        ),
        profile if seed.index == 0 else None,
        goal031._histories_valid(histories, config.generation_config),
        bool(np.isfinite(profile.log_likelihoods).all()),
    )


def _parameter_summary(
    parameter: str,
    cutoff: float,
    rows: tuple[MarginalValidationResult, ...],
    validation_count: int,
) -> ParameterSummary:
    if parameter == "spread_rate":
        coverage_count = sum(row.spread_truth_included for row in rows)
        connected_interior = sum(
            row.spread_component_count == 1 and not row.spread_boundary_contact for row in rows
        )
        boundary_count = sum(row.spread_boundary_contact for row in rows)
        errors = [row.absolute_log_rho_error for row in rows]
        widths = [row.spread_log_support_width for row in rows]
        no_effect_count: int | None = None
        error_limit, width_limit = 0.10, 0.50
    elif parameter == "prey_effect":
        coverage_count = sum(row.effect_truth_included for row in rows)
        connected_interior = sum(
            row.effect_component_count == 1 and not row.effect_boundary_contact for row in rows
        )
        boundary_count = sum(row.effect_boundary_contact for row in rows)
        errors = [row.absolute_log_effect_error for row in rows]
        widths = [row.effect_log_support_width for row in rows]
        no_effect_count = sum(row.no_effect_excluded for row in rows)
        error_limit, width_limit = 0.20, 0.80
    else:
        raise ValueError("unknown parameter summary")
    coverage = wilson_interval(coverage_count, validation_count)
    required_count = math.ceil(0.95 * validation_count)
    passed = (
        coverage.lower <= 0.95 <= coverage.upper
        and connected_interior >= required_count
        and median(errors) <= error_limit
        and median(widths) <= width_limit
        and (no_effect_count is None or no_effect_count >= required_count)
    )
    return ParameterSummary(
        parameter,
        cutoff,
        coverage_count,
        coverage.estimate,
        coverage.lower,
        coverage.upper,
        connected_interior,
        boundary_count,
        median(errors),
        median(widths),
        no_effect_count,
        passed,
    )


def _profile_curve_rows(
    profile: goal032.JointProfile,
    spread_cutoff: float,
    effect_cutoff: float,
    config: goal032.Goal032Config,
) -> tuple[ProfileCurvePoint, ...]:
    spread_drops, effect_drops = profile_likelihood_drops(profile)
    spread_support = summarize_marginal_support(
        profile.rhos, spread_drops, spread_cutoff, config.truth_rho
    )
    effect_support = summarize_marginal_support(
        profile.hazard_ratios,
        effect_drops,
        effect_cutoff,
        config.truth_hazard_ratio,
    )
    spread_rows = tuple(
        ProfileCurvePoint(
            "spread_rate",
            float(value),
            float(spread_drops[index]),
            bool(spread_support.mask[index]),
            math.isclose(float(value), config.truth_rho),
            math.isclose(float(value), profile.mle_rho),
        )
        for index, value in enumerate(profile.rhos)
    )
    effect_rows = tuple(
        ProfileCurvePoint(
            "prey_effect",
            float(value),
            float(effect_drops[index]),
            bool(effect_support.mask[index]),
            math.isclose(float(value), config.truth_hazard_ratio),
            math.isclose(float(value), profile.mle_hazard_ratio),
        )
        for index, value in enumerate(profile.hazard_ratios)
    )
    return (*spread_rows, *effect_rows)


def _calibration_reconciled(
    observed: tuple[CalibrationProfileStatistic, ...],
    expected: tuple[AnchorCalibrationRow, ...],
) -> bool:
    return len(observed) == len(expected) and all(
        current.dataset_index == anchor.dataset_index
        and math.isclose(
            current.joint_likelihood_ratio_at_truth,
            anchor.joint_likelihood_ratio_at_truth,
            rel_tol=0.0,
            abs_tol=1e-10,
        )
        and current.predator_detected_visit_count == anchor.predator_detected_visit_count
        and current.prey_detected_visit_count == anchor.prey_detected_visit_count
        for current, anchor in zip(observed, expected, strict=True)
    )


def _validation_reconciled(
    observed: tuple[MarginalValidationResult, ...],
    joint_replays: tuple[JointReplay, ...],
    expected: tuple[AnchorValidationRow, ...],
) -> bool:
    return len(observed) == len(expected) == len(joint_replays) and all(
        current.dataset_index == anchor.dataset_index
        and current.predator_detected_visit_count == anchor.predator_detected_visit_count
        and current.prey_detected_visit_count == anchor.prey_detected_visit_count
        and math.isclose(current.mle_rho, anchor.mle_rho, rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(
            current.absolute_log_rho_error,
            anchor.absolute_log_rho_error,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and math.isclose(
            current.mle_hazard_ratio,
            anchor.mle_hazard_ratio,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and math.isclose(
            current.absolute_log_effect_error,
            anchor.absolute_log_effect_error,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and replay.truth_included == anchor.joint_truth_included
        and replay.component_count == anchor.joint_component_count
        and replay.boundary_contact == anchor.joint_boundary_contact
        and replay.no_effect_excluded == anchor.joint_no_effect_excluded
        for current, replay, anchor in zip(observed, joint_replays, expected, strict=True)
    )


def write_review_bundle(result: Goal033Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the compact seven-file Goal 033 review surface."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("output directory must be empty")
    _write_dataclass_csv(
        target / "calibration_profile_statistics.csv", result.calibration_statistics
    )
    _write_dataclass_csv(target / "validation_marginal_intervals.csv", result.validation_results)
    _write_dataclass_csv(target / "marginal_summary.csv", result.marginal_summaries)
    _write_dataclass_csv(target / "representative_profile_curves.csv", result.representative_curves)
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    _save_figure(target / "parameter_specific_calibration.svg", _review_figure(result))
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 033 review surface is incomplete")
    return written


CsvRow = (
    CalibrationProfileStatistic | MarginalValidationResult | ParameterSummary | ProfileCurvePoint
)


def _write_dataclass_csv(path: Path, rows: tuple[CsvRow, ...]) -> None:
    if not rows:
        raise ValueError("CSV rows must not be empty")
    payload = [asdict(row) for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]))
        writer.writeheader()
        writer.writerows(payload)


def _summary_payload(result: Goal033Result) -> dict[str, object]:
    spread = result.spread_summary
    effect = result.effect_summary
    return {
        "goal": "033-parameter-specific-uncertainty-calibration-diagnostic",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "outcome": result.outcome,
        "claim_scope": ("separate parameter-specific 95% support; not simultaneous joint coverage"),
        "frozen_model": {
            "truth_spread_rate": result.config.truth_rho,
            "truth_prey_hazard_ratio": result.config.truth_hazard_ratio,
            "spread_rate_grid_count": len(result.config.rhos),
            "prey_effect_grid_count": len(result.config.hazard_ratios),
            "bank_draws": result.config.bank_size,
            "calibration_replicates": result.config.calibration_replicates,
            "validation_replicates": result.config.validation_replicates,
            "calibration_rank_one_based": result.config.calibration_rank_one_based,
        },
        "goal032_anchor": {
            "outcome": result.anchor.outcome,
            "joint_cutoff": result.anchor.joint_cutoff,
            "joint_coverage": result.anchor.joint_coverage,
            "joint_connected_interior_count": result.anchor.joint_connected_interior_count,
            "joint_boundary_contact_count": result.anchor.joint_boundary_contact_count,
            "joint_no_effect_exclusion_count": result.anchor.joint_no_effect_exclusion_count,
            "joint_median_rho_width": result.anchor.joint_median_rho_width,
            "joint_median_effect_width": result.anchor.joint_median_effect_width,
        },
        "parameter_specific": {
            "spread_rate": asdict(spread),
            "prey_effect": asdict(effect),
        },
        "calibration_distributions": {
            "spread_profile_likelihood_ratio": _quantile_payload(
                [
                    row.spread_profile_likelihood_ratio_at_truth
                    for row in result.calibration_statistics
                ]
            ),
            "prey_effect_profile_likelihood_ratio": _quantile_payload(
                [
                    row.prey_effect_profile_likelihood_ratio_at_truth
                    for row in result.calibration_statistics
                ]
            ),
        },
        "failed_prey_effect_gates": _failed_effect_gates(result),
        "invariants": result.invariants,
    }


def _quantile_payload(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "median": float(np.quantile(array, 0.50)),
        "q90": float(np.quantile(array, 0.90)),
        "q95": float(np.quantile(array, 0.95)),
        "maximum": float(np.max(array)),
    }


def _failed_effect_gates(result: Goal033Result) -> tuple[str, ...]:
    if not result.config.is_production:
        return ()
    summary = result.effect_summary
    required_count = math.ceil(0.95 * result.config.validation_replicates)
    failed: list[str] = []
    if not all(result.invariants.values()):
        failed.append("implementation_invariants")
    if not summary.coverage_lower <= 0.95 <= summary.coverage_upper:
        failed.append("marginal_coverage")
    if summary.connected_interior_count < required_count:
        failed.append("connected_interior_support")
    if summary.no_effect_exclusion_count is None or (
        summary.no_effect_exclusion_count < required_count
    ):
        failed.append("no_effect_exclusion")
    if summary.median_absolute_log_error > 0.20:
        failed.append("point_recovery")
    if summary.median_log_support_width > 0.80:
        failed.append("precision")
    return tuple(failed)


def _review(result: Goal033Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 033: Parameter-Specific Calibration\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    spread = result.spread_summary
    effect = result.effect_summary
    failed = _failed_effect_gates(result)
    if result.outcome == PREY_EFFECT_RECOVERED:
        result_text = (
            "The prey effect passed every prespecified marginal recovery gate once its uncertainty "
            "was calibrated separately from spread speed. Goal 032's negative joint result remains "
            "valid, but it no longer supports the stronger claim that prey effect itself was weak."
        )
        interpretation = (
            "Observed: fitted prey effects remained centred, their separate intervals achieved "
            "nominal coverage, and they usually excluded no effect without reaching the grid edge. "
            "Interpretation: the wide Goal 032 prey-effect projection arose mainly because its "
            "single joint cutoff absorbed variation associated with the shared invasion wave."
        )
    else:
        result_text = (
            "The prey effect remained weak after parameter-specific calibration. Failed gates: "
            f"{', '.join(failed)}."
        )
        interpretation = (
            "Observed: separating the uncertainty thresholds did not recover a sufficiently "
            "narrow, "
            "well-covered prey-effect interval. Interpretation: the limitation is not explained by "
            "the shared joint cutoff alone and the information model should be reconsidered before "
            "adding biological complexity."
        )
    return "\n".join(
        [
            "# Goal 033: Parameter-Specific Uncertainty Calibration",
            "",
            f"Outcome: `{result.outcome}`.",
            "",
            "## Question",
            "",
            (
                "Was prey effect genuinely weak when spread speed was fitted, or was its "
                "uncertainty "
                "inflated because Goal 032 used one cutoff for both quantities?"
            ),
            "",
            "## Result",
            "",
            result_text,
            "",
            (
                "| Quantity | Cutoff | Coverage | Interior supports | Median error | "
                "Median width | No effect excluded |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|",
            (
                f"| Spread speed | {spread.cutoff:.3f} | {spread.coverage:.3f} | "
                f"{spread.connected_interior_count}/{result.config.validation_replicates} | "
                f"{spread.median_absolute_log_error:.3f} | "
                f"{spread.median_log_support_width:.3f} | not applicable |"
            ),
            (
                f"| Prey effect | {effect.cutoff:.3f} | {effect.coverage:.3f} | "
                f"{effect.connected_interior_count}/{result.config.validation_replicates} | "
                f"{effect.median_absolute_log_error:.3f} | "
                f"{effect.median_log_support_width:.3f} | "
                f"{effect.no_effect_exclusion_count}/{result.config.validation_replicates} |"
            ),
            "",
            "## What changed from Goal 032",
            "",
            (
                f"Goal 032 used a joint cutoff of {result.anchor.joint_cutoff:.3f}; its median "
                f"prey-effect width was {result.anchor.joint_median_effect_width:.3f}, and "
                f"{result.anchor.joint_no_effect_exclusion_count}/"
                f"{result.config.validation_replicates} regions excluded no effect. Goal 033 used "
                f"a prey-effect-specific cutoff of {effect.cutoff:.3f}; the corresponding width "
                "was "
                f"{effect.median_log_support_width:.3f}, with "
                f"{effect.no_effect_exclusion_count}/"
                f"{result.config.validation_replicates} excluding "
                "no effect."
            ),
            "",
            "## Interpretation",
            "",
            interpretation,
            "",
            "## Boundary",
            "",
            (
                "These are separate marginal uncertainty statements, not a simultaneous joint "
                "confidence region. No biology, data, grid, seed, likelihood, or decision "
                "threshold "
                "was retuned, and Goal 032's accepted joint result was not replaced."
            ),
            "",
        ]
    )


def _review_figure(result: Goal033Result) -> Figure:
    figure, axes = plt.subplots(2, 3, figsize=(13.5, 8.0), constrained_layout=True)
    spread_rows = tuple(
        row for row in result.representative_curves if row.parameter == "spread_rate"
    )
    effect_rows = tuple(
        row for row in result.representative_curves if row.parameter == "prey_effect"
    )
    _profile_panel(
        axes[0, 0],
        np.log2([row.value for row in spread_rows]),
        spread_rows,
        result.spread_summary.cutoff,
        "Example spread-speed profile",
        "Spread rate (log2 scale)",
    )
    _profile_panel(
        axes[0, 1],
        np.asarray([row.value for row in effect_rows]),
        effect_rows,
        result.effect_summary.cutoff,
        "Example prey-effect profile",
        "Prey hazard multiplier",
    )
    ax = axes[0, 2]
    summaries = result.marginal_summaries
    estimates = [row.coverage for row in summaries]
    lower = [row.coverage - row.coverage_lower for row in summaries]
    upper = [row.coverage_upper - row.coverage for row in summaries]
    ax.bar(("Spread speed", "Prey effect"), estimates, color=("#0F766E", "#B45309"))
    ax.errorbar(
        range(2),
        estimates,
        yerr=np.asarray((lower, upper)),
        fmt="none",
        color="#111827",
        capsize=4,
    )
    ax.axhline(0.95, linestyle="--", color="#B91C1C", linewidth=1)
    ax.set(title="Separate marginal coverage", ylabel="Proportion", ylim=(0.88, 1.0))

    _comparison_bar(
        axes[1, 0],
        ("Goal 032\njoint", "Goal 033\nseparate"),
        (
            result.anchor.joint_median_rho_width,
            result.spread_summary.median_log_support_width,
        ),
        0.50,
        "Spread-speed interval width",
        "Median log width",
    )
    _comparison_bar(
        axes[1, 1],
        ("Goal 031\nknown speed", "Goal 032\njoint", "Goal 033\nseparate"),
        (
            result.anchor.goal031_effect_width,
            result.anchor.joint_median_effect_width,
            result.effect_summary.median_log_support_width,
        ),
        0.80,
        "Prey-effect interval width",
        "Median log width",
    )
    _comparison_bar(
        axes[1, 2],
        ("Goal 031\nknown speed", "Goal 032\njoint", "Goal 033\nseparate"),
        (
            result.anchor.goal031_no_effect_exclusion_count / result.config.validation_replicates,
            result.anchor.joint_no_effect_exclusion_count / result.config.validation_replicates,
            cast(int, result.effect_summary.no_effect_exclusion_count)
            / result.config.validation_replicates,
        ),
        0.95,
        "Support excludes no prey effect",
        "Proportion",
    )
    for axis in axes.flat:
        axis.tick_params(axis="x", rotation=8)
    figure.suptitle(
        "Goal 033: calibrating spread speed and prey effect separately",
        fontsize=15,
        fontweight="bold",
    )
    return figure


def _profile_panel(
    axis: Axes,
    x_values: NDArray[np.float64],
    rows: tuple[ProfileCurvePoint, ...],
    cutoff: float,
    title: str,
    xlabel: str,
) -> None:
    drops = np.asarray([row.twice_profile_log_likelihood_drop for row in rows])
    axis.plot(x_values, drops, color="#334155", linewidth=1.8)
    axis.axhline(cutoff, color="#B91C1C", linestyle="--", label="95% cutoff")
    truth_index = next(index for index, row in enumerate(rows) if row.is_truth)
    mle_index = next(index for index, row in enumerate(rows) if row.is_mle)
    axis.scatter(
        x_values[truth_index],
        drops[truth_index],
        marker="*",
        s=90,
        color="#2563EB",
        label="Truth",
    )
    axis.scatter(
        x_values[mle_index],
        drops[mle_index],
        marker="x",
        s=55,
        color="#DC2626",
        label="Fitted value",
    )
    axis.set(title=title, xlabel=xlabel, ylabel="Twice profile log-likelihood drop")
    axis.legend(loc="upper right", fontsize=8)


def _comparison_bar(
    axis: Axes,
    labels: tuple[str, ...],
    values: tuple[float, ...],
    gate: float,
    title: str,
    ylabel: str,
) -> None:
    colors = (*("#64748B" for _ in values[:-1]), "#0F766E")
    axis.bar(labels, values, color=colors)
    axis.axhline(gate, linestyle="--", color="#B91C1C", linewidth=1)
    axis.set(title=title, ylabel=ylabel)


def _save_figure(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", bbox_inches="tight")
    plt.close(figure)


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(encoding="utf-8", newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


def _mapping(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return cast(dict[str, object], value)


def _int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    return value


def _float(payload: dict[str, object], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{key} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{key} must be finite")
    return result


def _csv_int(row: dict[str, str], key: str) -> int:
    try:
        return int(row[key])
    except (KeyError, ValueError) as error:
        raise ValueError(f"invalid CSV integer {key}") from error


def _csv_float(row: dict[str, str], key: str) -> float:
    try:
        result = float(row[key])
    except (KeyError, ValueError) as error:
        raise ValueError(f"invalid CSV number {key}") from error
    if not math.isfinite(result):
        raise ValueError(f"CSV number {key} must be finite")
    return result


def _csv_bool(row: dict[str, str], key: str) -> bool:
    value = row.get(key)
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"invalid CSV boolean {key}")


def _unique_index(values: tuple[float, ...], target: float, label: str) -> int:
    indices = np.flatnonzero(
        np.isclose(np.asarray(values, dtype=np.float64), target, rtol=0.0, atol=1e-12)
    )
    if len(indices) != 1:
        raise ValueError(f"{label} must occur once on its grid")
    return int(indices[0])
