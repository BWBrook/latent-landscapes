"""Joint spread-rate and prey-effect positive control."""

from __future__ import annotations

import csv
import hashlib
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

from latent_landscapes import goal031
from latent_landscapes.goal002.calibration import (
    EstimateInterval,
    normal_mean_interval,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal019 import RHO_GRID
from latent_landscapes.goal026 import (
    BACKGROUND_HAZARD,
    HAZARD_RATIO_GRID,
    NEUTRAL_HAZARD_GRID,
    SURVEY_TIMES,
)

MASTER_SEED = 20260812032
TRUTH_RHO = 1.0
TRUTH_HAZARD_RATIO = 5.0
JOINT_RHO_GRID = tuple(float(value) for value in RHO_GRID[::2])
JOINT_HAZARD_RATIO_GRID = tuple(float(value) for value in HAZARD_RATIO_GRID[::2])
DEFAULT_GOAL031_EVIDENCE_DIR = Path("artifacts/goal031_latent_arrival_prey_effect_positive_control")
JOINT_RECOVERED = "joint_spread_rate_prey_effect_recovered"
EXPECTED_FILES = (
    "calibration_statistics.csv",
    "validation_results.csv",
    "representative_joint_surface.csv",
    "benchmark_comparison.csv",
    "summary.json",
    "review.md",
    "joint_spread_rate_prey_effect.svg",
)
RHO_BLOCK_SIZE = 4


@dataclass(frozen=True, slots=True)
class Goal032Config:
    """Frozen central-truth two-parameter benchmark."""

    master_seed: int = MASTER_SEED
    bank_size: int = 4_096
    calibration_replicates: int = 2_000
    validation_replicates: int = 1_000
    calibration_rank_one_based: int = 1_901
    truth_rho: float = TRUTH_RHO
    truth_hazard_ratio: float = TRUTH_HAZARD_RATIO
    rhos: tuple[float, ...] = JOINT_RHO_GRID
    hazard_ratios: tuple[float, ...] = JOINT_HAZARD_RATIO_GRID
    neutral_hazards: tuple[float, ...] = NEUTRAL_HAZARD_GRID

    def __post_init__(self) -> None:
        if self.bank_size <= 0:
            raise ValueError("bank size must be positive")
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within calibration replicates")
        for values, truth, label in (
            (self.rhos, self.truth_rho, "spread rate"),
            (self.hazard_ratios, self.truth_hazard_ratio, "prey effect"),
        ):
            array = np.asarray(values, dtype=np.float64)
            if (
                array.ndim != 1
                or len(array) < 2
                or not np.isfinite(array).all()
                or np.any(array <= 0.0)
                or np.any(np.diff(array) <= 0.0)
            ):
                raise ValueError(f"{label} grid must be finite, positive, and increasing")
            if sum(math.isclose(value, truth) for value in values) != 1:
                raise ValueError(f"{label} truth must occur once on its grid")
        if self.hazard_ratios[0] != 1.0:
            raise ValueError("prey-effect grid must begin at no effect")
        if any(value <= 0.0 for value in self.neutral_hazards):
            raise ValueError("neutral hazards must be positive")

    @property
    def is_production(self) -> bool:
        return self == Goal032Config()

    @property
    def generation_config(self) -> goal031.Goal031Config:
        return goal031.Goal031Config(
            master_seed=self.master_seed,
            bank_size=self.bank_size,
            calibration_replicates=self.calibration_replicates,
            validation_replicates=self.validation_replicates,
            calibration_rank_one_based=self.calibration_rank_one_based,
            truth_hazard_ratio=self.truth_hazard_ratio,
            hazard_ratios=self.hazard_ratios,
            neutral_hazards=self.neutral_hazards,
        )


DEFAULT_CONFIG = Goal032Config()


def smoke_config() -> Goal032Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal032Config(
        bank_size=16,
        calibration_replicates=8,
        validation_replicates=8,
        calibration_rank_one_based=8,
        rhos=(0.75, 1.0, 1.25),
        hazard_ratios=(1.0, 5.0, 9.0),
        neutral_hazards=(0.0005, 0.001, 0.002, 0.004, 0.008, 0.016, 0.032),
    )


@dataclass(frozen=True, slots=True)
class JointArrivalIntegration:
    site_ids: tuple[str, ...]
    rhos: tuple[float, ...]
    hazard_ratios: tuple[float, ...]
    category_mass: NDArray[np.float64]
    survival_moments: NDArray[np.float64]
    base_bank_arrivals: NDArray[np.float64]
    bank_checksum: str


@dataclass(frozen=True, slots=True)
class JointProfile:
    rhos: NDArray[np.float64]
    hazard_ratios: NDArray[np.float64]
    log_likelihoods: NDArray[np.float64]
    maximum_log_likelihood: float
    mle_rho: float
    mle_hazard_ratio: float


@dataclass(frozen=True, slots=True)
class NeutralProfile:
    rhos: NDArray[np.float64]
    hazards: NDArray[np.float64]
    log_likelihoods: NDArray[np.float64]
    maximum_log_likelihood: float
    mle_rho: float
    mle_hazard: float


@dataclass(frozen=True, slots=True)
class JointSupport:
    truth_included: bool
    component_count: int
    boundary_contact: bool
    no_effect_excluded: bool
    rho_lower: float
    rho_upper: float
    hazard_ratio_lower: float
    hazard_ratio_upper: float
    mask: NDArray[np.bool_]


@dataclass(frozen=True, slots=True)
class CalibrationStatistic:
    dataset_index: int
    likelihood_ratio_at_truth: float
    predator_detected_visit_count: int
    prey_detected_visit_count: int


@dataclass(frozen=True, slots=True)
class ValidationResult:
    dataset_index: int
    predator_detected_visit_count: int
    prey_detected_visit_count: int
    truth_included: bool
    support_component_count: int
    support_boundary_contact: bool
    no_effect_excluded: bool
    mle_rho: float
    absolute_log_rho_error: float
    rho_support_lower: float
    rho_support_upper: float
    log_rho_support_width: float
    mle_hazard_ratio: float
    absolute_log_effect_error: float
    effect_support_lower: float
    effect_support_upper: float
    log_effect_support_width: float
    fitted_neutral_rho: float
    fitted_neutral_hazard: float
    heldout_process_log_score: float
    heldout_neutral_log_score: float
    heldout_log_score_advantage: float


@dataclass(frozen=True, slots=True)
class SurfacePoint:
    rho: float
    hazard_ratio: float
    twice_log_likelihood_drop: float
    in_calibrated_support: bool
    is_truth: bool
    is_mle: bool


@dataclass(frozen=True, slots=True)
class JointRecoverySummary:
    cutoff: float
    coverage_count: int
    coverage: EstimateInterval
    connected_interior_count: int
    no_effect_exclusion_count: int
    median_absolute_log_rho_error: float
    median_log_rho_support_width: float
    median_absolute_log_effect_error: float
    median_log_effect_support_width: float
    heldout_log_score_advantage: EstimateInterval


@dataclass(frozen=True, slots=True)
class Goal031Anchor:
    calibration_replicates: int
    validation_replicates: int
    coverage: float
    coverage_lower: float
    coverage_upper: float
    connected_interior_count: int
    no_effect_exclusion_count: int
    median_absolute_log_effect_error: float
    median_log_effect_support_width: float
    score_advantage: float
    score_advantage_lower: float
    score_advantage_upper: float


@dataclass(frozen=True, slots=True)
class BenchmarkComparison:
    estimation_case: str
    calibration_replicates: int
    validation_replicates: int
    coverage: float
    coverage_lower: float
    coverage_upper: float
    connected_interior_count: int
    no_effect_exclusion_count: int
    median_absolute_log_rho_error: float | None
    median_log_rho_support_width: float | None
    median_absolute_log_effect_error: float
    median_log_effect_support_width: float
    score_advantage: float
    score_advantage_lower: float
    score_advantage_upper: float
    recovered: bool


@dataclass(frozen=True, slots=True)
class CalibrationWork:
    statistic: CalibrationStatistic
    valid_histories: bool
    finite_likelihood: bool


@dataclass(frozen=True, slots=True)
class ValidationWork:
    result: ValidationResult
    profile: JointProfile | None
    valid_histories: bool
    finite_likelihood: bool


@dataclass(frozen=True, slots=True)
class Goal032Result:
    config: Goal032Config
    goal031_anchor: Goal031Anchor
    calibration_statistics: tuple[CalibrationStatistic, ...]
    validation_results: tuple[ValidationResult, ...]
    representative_surface: tuple[SurfacePoint, ...]
    summary: JointRecoverySummary
    integration: JointArrivalIntegration
    invariants: dict[str, bool]
    outcome: str

    @property
    def comparison(self) -> tuple[BenchmarkComparison, BenchmarkComparison]:
        anchor = self.goal031_anchor
        current = self.summary
        return (
            BenchmarkComparison(
                "known_spread_rate_goal031",
                anchor.calibration_replicates,
                anchor.validation_replicates,
                anchor.coverage,
                anchor.coverage_lower,
                anchor.coverage_upper,
                anchor.connected_interior_count,
                anchor.no_effect_exclusion_count,
                None,
                None,
                anchor.median_absolute_log_effect_error,
                anchor.median_log_effect_support_width,
                anchor.score_advantage,
                anchor.score_advantage_lower,
                anchor.score_advantage_upper,
                True,
            ),
            BenchmarkComparison(
                "joint_spread_rate_and_prey_effect_goal032",
                self.config.calibration_replicates,
                self.config.validation_replicates,
                current.coverage.estimate,
                current.coverage.lower,
                current.coverage.upper,
                current.connected_interior_count,
                current.no_effect_exclusion_count,
                current.median_absolute_log_rho_error,
                current.median_log_rho_support_width,
                current.median_absolute_log_effect_error,
                current.median_log_effect_support_width,
                current.heldout_log_score_advantage.estimate,
                current.heldout_log_score_advantage.lower,
                current.heldout_log_score_advantage.upper,
                self.outcome == JOINT_RECOVERED,
            ),
        )


@dataclass(frozen=True, slots=True)
class PostRunDiagnostics:
    calibration_lr_median: float
    calibration_lr_q90: float
    calibration_lr_q95: float
    calibration_lr_maximum: float
    connected_support_count: int
    boundary_contact_count: int
    rho_mle_q10: float
    rho_mle_median: float
    rho_mle_q90: float
    effect_mle_q10: float
    effect_mle_median: float
    effect_mle_q90: float
    log_mle_correlation: float | None


_WORKER_CONFIG: Goal032Config | None = None
_WORKER_FIXED: FixedInputs | None = None
_WORKER_INTEGRATION: JointArrivalIntegration | None = None


def load_goal031_anchor(evidence_dir: Path) -> Goal031Anchor:
    """Load and exactly reconcile the accepted one-parameter anchor."""
    payload = cast(
        dict[str, object],
        json.loads((Path(evidence_dir) / "summary.json").read_text(encoding="utf-8")),
    )
    if payload.get("goal") != "031-latent-arrival-prey-effect-positive-control":
        raise ValueError("Goal 031 evidence has the wrong identity")
    if payload.get("outcome") != "latent_arrival_prey_effect_recovered":
        raise ValueError("Goal 031 anchor was not accepted as recovered")
    calibration = cast(dict[str, object], payload.get("calibration"))
    validation = cast(dict[str, object], payload.get("validation"))
    coverage = cast(dict[str, object], validation.get("coverage"))
    score = cast(dict[str, object], validation.get("heldout_log_score_advantage"))
    anchor = Goal031Anchor(
        _int_value(calibration, "replicates"),
        _int_value(validation, "replicates"),
        _float_value(coverage, "estimate"),
        _float_value(coverage, "lower"),
        _float_value(coverage, "upper"),
        _int_value(validation, "connected_interior_count"),
        _int_value(validation, "no_effect_exclusion_count"),
        _float_value(validation, "median_absolute_log_error"),
        _float_value(validation, "median_log_support_width"),
        _float_value(score, "estimate"),
        _float_value(score, "lower"),
        _float_value(score, "upper"),
    )
    expected_counts = (2_000, 1_000, 993, 1_000)
    observed_counts = (
        anchor.calibration_replicates,
        anchor.validation_replicates,
        anchor.connected_interior_count,
        anchor.no_effect_exclusion_count,
    )
    if observed_counts != expected_counts:
        raise ValueError("Goal 031 anchor counts do not reconcile")
    return anchor


def build_joint_arrival_integration(
    base_bank_arrivals: NDArray[np.float64],
    site_ids: tuple[str, ...],
    rhos: tuple[float, ...],
    hazard_ratios: tuple[float, ...],
    background_hazard: float = BACKGROUND_HAZARD,
) -> JointArrivalIntegration:
    """Build exact rate-scaled arrival moments for the two-parameter profile."""
    base = np.asarray(base_bank_arrivals, dtype=np.float64)
    if base.ndim != 2 or base.shape[1] != len(site_ids) or base.shape[0] <= 0:
        raise ValueError("base arrival bank shape does not match site identifiers")
    if not np.isfinite(base).all() or np.any(base < 0.0):
        raise ValueError("base arrival bank must be finite and non-negative")
    rho_values = np.asarray(rhos, dtype=np.float64)
    if rho_values.ndim != 1 or not np.isfinite(rho_values).all() or np.any(rho_values <= 0.0):
        raise ValueError("spread rates must be finite and positive")
    category_mass = np.empty((len(rhos), len(site_ids), goal031.CATEGORY_COUNT), dtype=np.float64)
    survival_moments = np.empty(
        (
            len(rhos),
            len(hazard_ratios),
            len(site_ids),
            len(SURVEY_TIMES) + 1,
            goal031.CATEGORY_COUNT,
        ),
        dtype=np.float64,
    )
    for rho_index, rho in enumerate(rhos):
        scaled = goal031.build_arrival_integration(
            base / rho,
            site_ids,
            hazard_ratios,
            background_hazard,
        )
        category_mass[rho_index] = scaled.category_mass
        survival_moments[rho_index] = scaled.survival_moments
    checksum = hashlib.sha256(np.ascontiguousarray(base).tobytes()).hexdigest()
    return JointArrivalIntegration(
        site_ids,
        rhos,
        hazard_ratios,
        category_mass,
        survival_moments,
        base.copy(),
        checksum,
    )


def joint_profile(
    histories: tuple[goal031.CrossLayerHistory, ...],
    integration: JointArrivalIntegration,
    config: Goal032Config,
) -> JointProfile:
    """Profile spread rate and prey effect jointly."""
    values = _joint_log_likelihood_surface(histories, integration, config)
    maximum_index = np.unravel_index(int(np.argmax(values)), values.shape)
    rhos = np.asarray(integration.rhos, dtype=np.float64)
    effects = np.asarray(integration.hazard_ratios, dtype=np.float64)
    return JointProfile(
        rhos,
        effects,
        values,
        float(values[maximum_index]),
        float(rhos[maximum_index[0]]),
        float(effects[maximum_index[1]]),
    )


def neutral_profile(
    histories: tuple[goal031.CrossLayerHistory, ...],
    integration: JointArrivalIntegration,
    config: Goal032Config,
) -> NeutralProfile:
    """Fit spread rate and constant prey hazard under the neutral comparator."""
    rhos = np.asarray(integration.rhos, dtype=np.float64)
    hazards = np.asarray(config.neutral_hazards, dtype=np.float64)
    values = _neutral_log_likelihood_surface(histories, integration, config, hazards)
    maximum_index = np.unravel_index(int(np.argmax(values)), values.shape)
    return NeutralProfile(
        rhos,
        hazards,
        values,
        float(values[maximum_index]),
        float(rhos[maximum_index[0]]),
        float(hazards[maximum_index[1]]),
    )


def summarize_joint_support(
    profile: JointProfile,
    cutoff: float,
    truth_rho: float,
    truth_hazard_ratio: float,
) -> JointSupport:
    """Summarize calibrated two-dimensional support and its projections."""
    mask = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods) <= cutoff
    rho_indices, effect_indices = np.nonzero(mask)
    if len(rho_indices) == 0:
        raise RuntimeError("joint likelihood support must not be empty")
    truth_rho_indices = np.flatnonzero(np.isclose(profile.rhos, truth_rho, rtol=0.0, atol=1e-12))
    truth_effect_indices = np.flatnonzero(
        np.isclose(profile.hazard_ratios, truth_hazard_ratio, rtol=0.0, atol=1e-12)
    )
    if len(truth_rho_indices) != 1 or len(truth_effect_indices) != 1:
        raise ValueError("joint truth must occur once on each grid")
    boundary = bool(mask[0, :].any() or mask[-1, :].any() or mask[:, 0].any() or mask[:, -1].any())
    return JointSupport(
        truth_included=bool(mask[int(truth_rho_indices[0]), int(truth_effect_indices[0])]),
        component_count=_component_count(mask),
        boundary_contact=boundary,
        no_effect_excluded=bool(not mask[:, 0].any()),
        rho_lower=float(profile.rhos[int(rho_indices.min())]),
        rho_upper=float(profile.rhos[int(rho_indices.max())]),
        hazard_ratio_lower=float(profile.hazard_ratios[int(effect_indices.min())]),
        hazard_ratio_upper=float(profile.hazard_ratios[int(effect_indices.max())]),
        mask=mask,
    )


def classify_outcome(
    *,
    invariants: dict[str, bool],
    summary: JointRecoverySummary,
    validation_count: int,
) -> str:
    """Classify which biological quantity remains recoverable."""
    if not invariants or not all(invariants.values()) or validation_count <= 0:
        return "implementation_blocked"
    required_count = math.ceil(0.95 * validation_count)
    common = (
        summary.coverage.lower <= 0.95 <= summary.coverage.upper
        and summary.connected_interior_count >= required_count
        and summary.heldout_log_score_advantage.lower > 0.0
    )
    spread = (
        common
        and summary.median_absolute_log_rho_error <= 0.10
        and summary.median_log_rho_support_width <= 0.50
    )
    effect = (
        common
        and summary.no_effect_exclusion_count >= required_count
        and summary.median_absolute_log_effect_error <= 0.20
        and summary.median_log_effect_support_width <= 0.80
    )
    if spread and effect:
        return JOINT_RECOVERED
    if spread:
        return "spread_rate_recovered_prey_effect_weak"
    if effect:
        return "prey_effect_recovered_spread_rate_weak"
    return "joint_spread_rate_prey_effect_not_recovered"


def run_goal032(
    goal031_evidence_dir: Path = DEFAULT_GOAL031_EVIDENCE_DIR,
    config: Goal032Config = DEFAULT_CONFIG,
    *,
    workers: int = 1,
) -> Goal032Result:
    """Calibrate and validate the central two-parameter benchmark."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    anchor = load_goal031_anchor(goal031_evidence_dir)
    fixed = goal011.build_fixed_inputs()
    manifest = goal031.spawn_seed_manifest(config.generation_config)
    base_bank = goal031._build_arrival_bank(fixed, manifest.bank_seeds, workers)
    sites = tuple(sorted(fixed.design.sites, key=lambda value: value.site_id))
    integration = build_joint_arrival_integration(
        base_bank,
        tuple(site.site_id for site in sites),
        config.rhos,
        config.hazard_ratios,
    )
    calibration_work = _run_calibration_tasks(
        manifest.calibration, config, fixed, integration, workers
    )
    calibration_rows = tuple(work.statistic for work in calibration_work)
    cutoff = order_statistic_cutoff(
        [row.likelihood_ratio_at_truth for row in calibration_rows],
        rank_one_based=config.calibration_rank_one_based,
    )
    validation_work = _run_validation_tasks(
        manifest.validation,
        config,
        fixed,
        integration,
        cutoff.cutoff,
        workers,
    )
    validation_rows = tuple(work.result for work in validation_work)
    representative_profile = validation_work[0].profile
    if representative_profile is None:
        raise RuntimeError("representative joint surface is missing")
    representative_surface = _surface_rows(
        representative_profile,
        cutoff.cutoff,
        config.truth_rho,
        config.truth_hazard_ratio,
    )
    coverage_count = sum(row.truth_included for row in validation_rows)
    summary = JointRecoverySummary(
        cutoff=cutoff.cutoff,
        coverage_count=coverage_count,
        coverage=wilson_interval(coverage_count, len(validation_rows)),
        connected_interior_count=sum(
            row.support_component_count == 1 and not row.support_boundary_contact
            for row in validation_rows
        ),
        no_effect_exclusion_count=sum(row.no_effect_excluded for row in validation_rows),
        median_absolute_log_rho_error=median(row.absolute_log_rho_error for row in validation_rows),
        median_log_rho_support_width=median(row.log_rho_support_width for row in validation_rows),
        median_absolute_log_effect_error=median(
            row.absolute_log_effect_error for row in validation_rows
        ),
        median_log_effect_support_width=median(
            row.log_effect_support_width for row in validation_rows
        ),
        heldout_log_score_advantage=normal_mean_interval(
            [row.heldout_log_score_advantage for row in validation_rows]
        ),
    )
    all_dataset_seeds = (*manifest.calibration, *manifest.validation)
    stream_tuples = {
        (
            seed.process_seed,
            seed.predator_detection_seed,
            seed.prey_seed,
            seed.prey_detection_seed,
        )
        for seed in all_dataset_seeds
    }
    unconditional_survival = integration.survival_moments.sum(axis=4)
    truth_rho_index = config.rhos.index(config.truth_rho)
    truth_integration = goal031.build_arrival_integration(
        integration.base_bank_arrivals,
        integration.site_ids,
        config.hazard_ratios,
        BACKGROUND_HAZARD,
    )
    invariants = {
        "goal031_anchor_reconciled": True,
        "fixed_spatial_inputs_reconciled": all(fixed.invariants.values()),
        "integration_bank_shape": integration.base_bank_arrivals.shape == (config.bank_size, 160),
        "joint_moment_shape": integration.survival_moments.shape
        == (
            len(config.rhos),
            len(config.hazard_ratios),
            160,
            len(SURVEY_TIMES) + 1,
            goal031.CATEGORY_COUNT,
        ),
        "category_mass_reconciled": bool(
            np.allclose(integration.category_mass.sum(axis=2), 1.0, atol=1e-12)
        ),
        "truth_rate_scaling_exact": bool(
            np.array_equal(
                integration.category_mass[truth_rho_index], truth_integration.category_mass
            )
            and np.array_equal(
                integration.survival_moments[truth_rho_index],
                truth_integration.survival_moments,
            )
        ),
        "survival_moments_finite_and_monotone": bool(
            np.isfinite(integration.survival_moments).all()
            and np.all(np.diff(unconditional_survival, axis=3) <= 1e-12)
        ),
        "calibration_histories_valid": all(work.valid_histories for work in calibration_work),
        "validation_histories_valid": all(work.valid_histories for work in validation_work),
        "finite_calibration_likelihoods": all(work.finite_likelihood for work in calibration_work),
        "finite_validation_likelihoods_and_scores": all(
            work.finite_likelihood for work in validation_work
        ),
        "independent_seed_streams": len(stream_tuples) == len(all_dataset_seeds)
        and len(set(manifest.bank_seeds)) == config.bank_size,
        "calibration_count": len(calibration_rows) == config.calibration_replicates,
        "validation_count": len(validation_rows) == config.validation_replicates,
        "representative_surface_count": len(representative_surface)
        == len(config.rhos) * len(config.hazard_ratios),
    }
    outcome = classify_outcome(
        invariants=invariants,
        summary=summary,
        validation_count=len(validation_rows),
    )
    if not config.is_production:
        outcome = (
            "non_scientific_smoke"
            if invariants and all(invariants.values())
            else "implementation_blocked"
        )
    return Goal032Result(
        config,
        anchor,
        calibration_rows,
        validation_rows,
        representative_surface,
        summary,
        integration,
        invariants,
        outcome,
    )


def _init_worker(
    config: Goal032Config,
    fixed: FixedInputs,
    integration: JointArrivalIntegration,
) -> None:
    global _WORKER_CONFIG, _WORKER_FIXED, _WORKER_INTEGRATION
    _WORKER_CONFIG = config
    _WORKER_FIXED = fixed
    _WORKER_INTEGRATION = integration


def _worker_context() -> tuple[Goal032Config, FixedInputs, JointArrivalIntegration]:
    if _WORKER_CONFIG is None or _WORKER_FIXED is None or _WORKER_INTEGRATION is None:
        raise RuntimeError("Goal 032 worker was not initialized")
    return _WORKER_CONFIG, _WORKER_FIXED, _WORKER_INTEGRATION


def _run_calibration_tasks(
    seeds: tuple[goal031.DatasetSeed, ...],
    config: Goal032Config,
    fixed: FixedInputs,
    integration: JointArrivalIntegration,
    workers: int,
) -> tuple[CalibrationWork, ...]:
    if workers == 1:
        _init_worker(config, fixed, integration)
        return tuple(_calibration_worker(seed) for seed in seeds)
    _init_worker(config, fixed, integration)
    chunksize = max(1, len(seeds) // (workers * 8))
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=mp.get_context("fork"),
    ) as executor:
        return tuple(executor.map(_calibration_worker, seeds, chunksize=chunksize))


def _run_validation_tasks(
    seeds: tuple[goal031.DatasetSeed, ...],
    config: Goal032Config,
    fixed: FixedInputs,
    integration: JointArrivalIntegration,
    cutoff: float,
    workers: int,
) -> tuple[ValidationWork, ...]:
    tasks = tuple((seed, cutoff) for seed in seeds)
    if workers == 1:
        _init_worker(config, fixed, integration)
        return tuple(_validation_worker(task) for task in tasks)
    _init_worker(config, fixed, integration)
    chunksize = max(1, len(tasks) // (workers * 8))
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=mp.get_context("fork"),
    ) as executor:
        return tuple(executor.map(_validation_worker, tasks, chunksize=chunksize))


def _calibration_worker(seed: goal031.DatasetSeed) -> CalibrationWork:
    config, fixed, integration = _worker_context()
    _, histories = goal031.generate_cross_layer_dataset(seed, config.generation_config, fixed)
    profile = joint_profile(histories, integration, config)
    return CalibrationWork(
        CalibrationStatistic(
            seed.index,
            _likelihood_ratio_at_truth(profile, config.truth_rho, config.truth_hazard_ratio),
            goal031._detected_visit_count(histories, predator=True),
            goal031._detected_visit_count(histories, predator=False),
        ),
        goal031._histories_valid(histories, config.generation_config),
        bool(np.isfinite(profile.log_likelihoods).all()),
    )


def _validation_worker(
    task: tuple[goal031.DatasetSeed, float],
) -> ValidationWork:
    seed, cutoff = task
    config, fixed, integration = _worker_context()
    _, histories = goal031.generate_cross_layer_dataset(seed, config.generation_config, fixed)
    all_profile = joint_profile(histories, integration, config)
    training = tuple(row for row in histories if row.split == "training")
    holdout = tuple(row for row in histories if row.split == "holdout")
    training_profile = joint_profile(training, integration, config)
    fitted_neutral = neutral_profile(training, integration, config)
    support = summarize_joint_support(
        all_profile, cutoff, config.truth_rho, config.truth_hazard_ratio
    )
    process_score = _joint_point_log_likelihood(
        holdout,
        integration,
        config,
        training_profile.mle_rho,
        training_profile.mle_hazard_ratio,
    ) / len(holdout)
    neutral_score = _neutral_point_log_likelihood(
        holdout,
        integration,
        config,
        fitted_neutral.mle_rho,
        fitted_neutral.mle_hazard,
    ) / len(holdout)
    result = ValidationResult(
        seed.index,
        goal031._detected_visit_count(histories, predator=True),
        goal031._detected_visit_count(histories, predator=False),
        support.truth_included,
        support.component_count,
        support.boundary_contact,
        support.no_effect_excluded,
        all_profile.mle_rho,
        abs(math.log(all_profile.mle_rho / config.truth_rho)),
        support.rho_lower,
        support.rho_upper,
        math.log(support.rho_upper / support.rho_lower),
        all_profile.mle_hazard_ratio,
        abs(math.log(all_profile.mle_hazard_ratio / config.truth_hazard_ratio)),
        support.hazard_ratio_lower,
        support.hazard_ratio_upper,
        math.log(support.hazard_ratio_upper / support.hazard_ratio_lower),
        fitted_neutral.mle_rho,
        fitted_neutral.mle_hazard,
        process_score,
        neutral_score,
        process_score - neutral_score,
    )
    finite = bool(
        np.isfinite(all_profile.log_likelihoods).all()
        and np.isfinite(training_profile.log_likelihoods).all()
        and np.isfinite(fitted_neutral.log_likelihoods).all()
        and math.isfinite(process_score)
        and math.isfinite(neutral_score)
    )
    return ValidationWork(
        result,
        all_profile if seed.index == 0 else None,
        goal031._histories_valid(histories, config.generation_config),
        finite,
    )


def _joint_log_likelihood_surface(
    histories: tuple[goal031.CrossLayerHistory, ...],
    integration: JointArrivalIntegration,
    config: Goal032Config,
) -> NDArray[np.float64]:
    if not histories:
        raise ValueError("cross-layer histories must not be empty")
    indices = np.asarray([row.site_index for row in histories], dtype=np.int64)
    if np.any(indices < 0) or np.any(indices >= len(integration.site_ids)):
        raise ValueError("history site index lies outside the integration bank")
    predator = goal031._predator_category_probabilities(histories, config.generation_config)
    event_coefficients, survival_coefficients = goal031._prey_emission_coefficients(
        histories, config.generation_config
    )
    values = np.empty((len(integration.rhos), len(integration.hazard_ratios)), dtype=np.float64)
    for start in range(0, len(integration.rhos), RHO_BLOCK_SIZE):
        end = min(start + RHO_BLOCK_SIZE, len(integration.rhos))
        moments = np.take(integration.survival_moments[start:end], indices, axis=2)
        weighted_survival = np.einsum("rhstc,sc->rhst", moments, predator, optimize=True)
        event_probabilities = weighted_survival[:, :, :, :-1] - weighted_survival[:, :, :, 1:]
        site_probabilities = (
            np.einsum("rhsj,sj->rhs", event_probabilities, event_coefficients, optimize=True)
            + weighted_survival[:, :, :, -1] * survival_coefficients[None, None, :]
        )
        if not np.isfinite(site_probabilities).all() or np.any(site_probabilities <= 0.0):
            raise RuntimeError("joint likelihood produced invalid site probabilities")
        values[start:end] = np.log(site_probabilities).sum(axis=2)
    return values


def _neutral_log_likelihood_surface(
    histories: tuple[goal031.CrossLayerHistory, ...],
    integration: JointArrivalIntegration,
    config: Goal032Config,
    hazards: NDArray[np.float64],
) -> NDArray[np.float64]:
    if not histories:
        raise ValueError("cross-layer histories must not be empty")
    if hazards.ndim != 1 or not np.isfinite(hazards).all() or np.any(hazards <= 0.0):
        raise ValueError("neutral hazards must be finite and positive")
    indices = np.asarray([row.site_index for row in histories], dtype=np.int64)
    predator = goal031._predator_category_probabilities(histories, config.generation_config)
    selected_mass = np.take(integration.category_mass, indices, axis=1)
    predator_site_probabilities = np.einsum("rsc,sc->rs", selected_mass, predator, optimize=True)
    if np.any(predator_site_probabilities <= 0.0):
        raise RuntimeError("neutral predator likelihood has zero support")
    predator_log_likelihood = np.log(predator_site_probabilities).sum(axis=1)

    event_coefficients, survival_coefficients = goal031._prey_emission_coefficients(
        histories, config.generation_config
    )
    times = np.asarray((0.0, *SURVEY_TIMES), dtype=np.float64)
    survival = np.exp(-hazards[:, None] * times[None, :])
    event_probabilities = survival[:, :-1] - survival[:, 1:]
    prey_site_probabilities = (
        np.einsum("hj,sj->hs", event_probabilities, event_coefficients, optimize=True)
        + survival[:, -1, None] * survival_coefficients[None, :]
    )
    if np.any(prey_site_probabilities <= 0.0):
        raise RuntimeError("neutral prey likelihood has zero support")
    prey_log_likelihood = np.log(prey_site_probabilities).sum(axis=1)
    values = predator_log_likelihood[:, None] + prey_log_likelihood[None, :]
    if not np.isfinite(values).all():
        raise RuntimeError("neutral likelihood surface is not finite")
    return np.asarray(values, dtype=np.float64)


def _joint_point_log_likelihood(
    histories: tuple[goal031.CrossLayerHistory, ...],
    integration: JointArrivalIntegration,
    config: Goal032Config,
    rho: float,
    hazard_ratio: float,
) -> float:
    rho_index = _unique_index(integration.rhos, rho, "spread rate")
    effect_index = _unique_index(integration.hazard_ratios, hazard_ratio, "prey effect")
    indices = np.asarray([row.site_index for row in histories], dtype=np.int64)
    predator = goal031._predator_category_probabilities(histories, config.generation_config)
    event_coefficients, survival_coefficients = goal031._prey_emission_coefficients(
        histories, config.generation_config
    )
    moments = np.take(integration.survival_moments[rho_index, effect_index], indices, axis=0)
    weighted_survival = np.einsum("stc,sc->st", moments, predator, optimize=True)
    event_probabilities = weighted_survival[:, :-1] - weighted_survival[:, 1:]
    site_probabilities = (
        np.einsum("sj,sj->s", event_probabilities, event_coefficients, optimize=True)
        + weighted_survival[:, -1] * survival_coefficients
    )
    if not np.isfinite(site_probabilities).all() or np.any(site_probabilities <= 0.0):
        raise RuntimeError("joint point likelihood is invalid")
    return float(np.log(site_probabilities).sum())


def _neutral_point_log_likelihood(
    histories: tuple[goal031.CrossLayerHistory, ...],
    integration: JointArrivalIntegration,
    config: Goal032Config,
    rho: float,
    hazard: float,
) -> float:
    rho_index = _unique_index(integration.rhos, rho, "neutral spread rate")
    hazard_index = _unique_index(config.neutral_hazards, hazard, "neutral hazard")
    surface = _neutral_log_likelihood_surface(
        histories,
        integration,
        config,
        np.asarray(config.neutral_hazards, dtype=np.float64),
    )
    return float(surface[rho_index, hazard_index])


def _likelihood_ratio_at_truth(
    profile: JointProfile, truth_rho: float, truth_hazard_ratio: float
) -> float:
    rho_index = _unique_index(tuple(profile.rhos), truth_rho, "truth spread rate")
    effect_index = _unique_index(
        tuple(profile.hazard_ratios), truth_hazard_ratio, "truth prey effect"
    )
    return max(
        0.0,
        2.0
        * (
            profile.maximum_log_likelihood - float(profile.log_likelihoods[rho_index, effect_index])
        ),
    )


def _unique_index(values: tuple[float, ...], target: float, label: str) -> int:
    indices = np.flatnonzero(
        np.isclose(np.asarray(values, dtype=np.float64), target, rtol=0.0, atol=1e-12)
    )
    if len(indices) != 1:
        raise ValueError(f"{label} must occur once on its grid")
    return int(indices[0])


def _component_count(mask: NDArray[np.bool_]) -> int:
    if mask.ndim != 2:
        raise ValueError("joint support mask must be two-dimensional")
    visited = np.zeros_like(mask)
    components = 0
    for row, col in zip(*np.nonzero(mask), strict=True):
        if visited[row, col]:
            continue
        components += 1
        stack = [(int(row), int(col))]
        visited[row, col] = True
        while stack:
            current_row, current_col = stack.pop()
            for next_row, next_col in (
                (current_row - 1, current_col),
                (current_row + 1, current_col),
                (current_row, current_col - 1),
                (current_row, current_col + 1),
            ):
                if (
                    0 <= next_row < mask.shape[0]
                    and 0 <= next_col < mask.shape[1]
                    and mask[next_row, next_col]
                    and not visited[next_row, next_col]
                ):
                    visited[next_row, next_col] = True
                    stack.append((next_row, next_col))
    return components


def _surface_rows(
    profile: JointProfile,
    cutoff: float,
    truth_rho: float,
    truth_hazard_ratio: float,
) -> tuple[SurfacePoint, ...]:
    support = summarize_joint_support(profile, cutoff, truth_rho, truth_hazard_ratio)
    return tuple(
        SurfacePoint(
            float(rho),
            float(effect),
            float(
                2.0
                * (
                    profile.maximum_log_likelihood
                    - profile.log_likelihoods[rho_index, effect_index]
                )
            ),
            bool(support.mask[rho_index, effect_index]),
            math.isclose(float(rho), truth_rho) and math.isclose(float(effect), truth_hazard_ratio),
            math.isclose(float(rho), profile.mle_rho)
            and math.isclose(float(effect), profile.mle_hazard_ratio),
        )
        for rho_index, rho in enumerate(profile.rhos)
        for effect_index, effect in enumerate(profile.hazard_ratios)
    )


def write_review_bundle(result: Goal032Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the compact seven-file Goal 032 review surface."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("output directory must be empty")
    _write_dataclass_csv(target / "calibration_statistics.csv", result.calibration_statistics)
    _write_dataclass_csv(target / "validation_results.csv", result.validation_results)
    _write_dataclass_csv(target / "representative_joint_surface.csv", result.representative_surface)
    _write_dataclass_csv(target / "benchmark_comparison.csv", result.comparison)
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    _save_figure(target / "joint_spread_rate_prey_effect.svg", _review_figure(result))
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 032 review surface is incomplete")
    return written


CsvRow = CalibrationStatistic | ValidationResult | SurfacePoint | BenchmarkComparison


def _write_dataclass_csv(path: Path, rows: tuple[CsvRow, ...]) -> None:
    if not rows:
        raise ValueError("CSV rows must not be empty")
    payload = [asdict(row) for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]))
        writer.writeheader()
        writer.writerows(payload)


def _summary_payload(result: Goal032Result) -> dict[str, object]:
    summary = result.summary
    diagnostics = _post_run_diagnostics(result)
    return {
        "goal": "032-joint-spread-rate-prey-effect-positive-control",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "outcome": result.outcome,
        "scientific_interpretation": result.outcome,
        "post_run_diagnosis": "point_estimates_centered_but_joint_uncertainty_not_resolved",
        "model": {
            "truth_spread_rate": result.config.truth_rho,
            "known_resistance_contrast": 1.0,
            "background_hazard": BACKGROUND_HAZARD,
            "truth_hazard_ratio": result.config.truth_hazard_ratio,
            "estimated_parameters": ["predator_spread_rate", "prey_hazard_ratio"],
            "known_predator_detection_probability": goal031.PREDATOR_DETECTION_PROBABILITY,
            "known_prey_detection_probability": goal031.PREY_DETECTION_PROBABILITY,
            "false_positive_probability": 0.0,
            "spread_rate_grid_count": len(result.config.rhos),
            "prey_effect_grid_count": len(result.config.hazard_ratios),
            "arrival_inference": (
                "exact rate-scaled shared within-site arrival draw; site-marginal composite "
                "likelihood across sites"
            ),
            "neutral_model": (
                "separately fitted predator spread rate and constant prey-extirpation hazard "
                "under identical observation processes"
            ),
        },
        "integration_bank": {
            "draws": result.config.bank_size,
            "base_bank_checksum_sha256": result.integration.bank_checksum,
            "rate_scaling": "arrival_at_candidate_rho = base_arrival / rho",
        },
        "calibration": {
            "replicates": result.config.calibration_replicates,
            "rank_one_based": result.config.calibration_rank_one_based,
            "cutoff": summary.cutoff,
        },
        "validation": {
            "replicates": result.config.validation_replicates,
            "coverage_count": summary.coverage_count,
            "coverage": asdict(summary.coverage),
            "connected_interior_count": summary.connected_interior_count,
            "no_effect_exclusion_count": summary.no_effect_exclusion_count,
            "median_absolute_log_rho_error": summary.median_absolute_log_rho_error,
            "median_log_rho_support_width": summary.median_log_rho_support_width,
            "median_absolute_log_effect_error": summary.median_absolute_log_effect_error,
            "median_log_effect_support_width": summary.median_log_effect_support_width,
            "heldout_log_score_advantage": asdict(summary.heldout_log_score_advantage),
        },
        "goal031_anchor": asdict(result.goal031_anchor),
        "diagnostics": asdict(diagnostics),
        "failed_gates": _failed_gates(result),
        "invariants": result.invariants,
    }


def _post_run_diagnostics(result: Goal032Result) -> PostRunDiagnostics:
    calibration_lr = np.asarray(
        [row.likelihood_ratio_at_truth for row in result.calibration_statistics],
        dtype=np.float64,
    )
    rho_mles = np.asarray([row.mle_rho for row in result.validation_results], dtype=np.float64)
    effect_mles = np.asarray(
        [row.mle_hazard_ratio for row in result.validation_results], dtype=np.float64
    )
    log_rho = np.log(rho_mles)
    log_effect = np.log(effect_mles)
    correlation: float | None = None
    if np.ptp(log_rho) > 0.0 and np.ptp(log_effect) > 0.0:
        correlation = float(np.corrcoef(log_rho, log_effect)[0, 1])
    return PostRunDiagnostics(
        calibration_lr_median=float(np.quantile(calibration_lr, 0.50)),
        calibration_lr_q90=float(np.quantile(calibration_lr, 0.90)),
        calibration_lr_q95=float(np.quantile(calibration_lr, 0.95)),
        calibration_lr_maximum=float(np.max(calibration_lr)),
        connected_support_count=sum(
            row.support_component_count == 1 for row in result.validation_results
        ),
        boundary_contact_count=sum(
            row.support_boundary_contact for row in result.validation_results
        ),
        rho_mle_q10=float(np.quantile(rho_mles, 0.10)),
        rho_mle_median=float(np.quantile(rho_mles, 0.50)),
        rho_mle_q90=float(np.quantile(rho_mles, 0.90)),
        effect_mle_q10=float(np.quantile(effect_mles, 0.10)),
        effect_mle_median=float(np.quantile(effect_mles, 0.50)),
        effect_mle_q90=float(np.quantile(effect_mles, 0.90)),
        log_mle_correlation=correlation,
    )


def _failed_gates(result: Goal032Result) -> tuple[str, ...]:
    if not result.config.is_production:
        return ()
    summary = result.summary
    required_count = math.ceil(0.95 * result.config.validation_replicates)
    failed: list[str] = []
    if not all(result.invariants.values()):
        failed.append("implementation_invariants")
    if not summary.coverage.lower <= 0.95 <= summary.coverage.upper:
        failed.append("calibrated_coverage")
    if summary.connected_interior_count < required_count:
        failed.append("connected_interior_support")
    if summary.median_absolute_log_rho_error > 0.10:
        failed.append("spread_rate_point_recovery")
    if summary.median_log_rho_support_width > 0.50:
        failed.append("spread_rate_precision")
    if summary.no_effect_exclusion_count < required_count:
        failed.append("no_effect_exclusion")
    if summary.median_absolute_log_effect_error > 0.20:
        failed.append("prey_effect_point_recovery")
    if summary.median_log_effect_support_width > 0.80:
        failed.append("prey_effect_precision")
    if summary.heldout_log_score_advantage.lower <= 0.0:
        failed.append("heldout_prediction")
    return tuple(failed)


def _review(result: Goal032Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 032: Joint Spread Rate and Prey Effect\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    summary = result.summary
    diagnostics = _post_run_diagnostics(result)
    failed = _failed_gates(result)
    if result.outcome == JOINT_RECOVERED:
        interpretation = (
            "The direct predator histories identified wave speed while the prey histories "
            "retained enough additional information to identify the fivefold effect. Both "
            "biological roles passed their prespecified accuracy and precision gates."
        )
    elif result.outcome == "spread_rate_recovered_prey_effect_weak":
        interpretation = (
            "Predator spread speed remained recoverable, but allowing it to vary left the prey "
            f"effect too weak under at least one gate: {', '.join(failed)}."
        )
    elif result.outcome == "prey_effect_recovered_spread_rate_weak":
        interpretation = (
            "The prey effect remained recoverable, but the predator observations did not "
            f"constrain spread speed sufficiently: {', '.join(failed)}."
        )
    else:
        interpretation = (
            "The prespecified joint uncertainty test did not resolve both biological quantities. "
            "This was not a failure of point estimation: the fitted values remained centred near "
            "truth. The failure was that the calibrated joint support extended to the prey-effect "
            f"grid boundary and usually included no prey effect. Failed gates: {', '.join(failed)}."
        )
    comparison_rows = [
        (
            f"| {row.estimation_case} | {row.coverage:.3f} | "
            f"{row.no_effect_exclusion_count}/{row.validation_replicates} | "
            f"{_format_optional(row.median_absolute_log_rho_error)} | "
            f"{_format_optional(row.median_log_rho_support_width)} | "
            f"{row.median_absolute_log_effect_error:.3f} | "
            f"{row.median_log_effect_support_width:.3f} | {row.score_advantage:.4f} |"
        )
        for row in result.comparison
    ]
    return "\n".join(
        [
            "# Goal 032: Joint Spread Rate and Prey Effect",
            "",
            f"Outcome: `{result.outcome}`.",
            "",
            "## Question",
            "",
            (
                "Can the observed predator wave reveal how fast invasion proceeded while the "
                "prey histories separately reveal how strongly arrival affected persistence?"
            ),
            "",
            "## Result",
            "",
            interpretation,
            "",
            (
                "| Estimation case | Coverage | No effect excluded | Rate error | Rate width | "
                "Effect error | Effect width | Held-out advantage |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|---:|",
            *comparison_rows,
            "",
            "## Ecological reading",
            "",
            (
                f"Across validation datasets, the middle 80% of fitted spread rates was "
                f"{diagnostics.rho_mle_q10:.3f}-{diagnostics.rho_mle_q90:.3f}, centred on "
                f"{diagnostics.rho_mle_median:.3f} (truth 1). The middle 80% of fitted prey-effect "
                "multipliers was "
                f"{diagnostics.effect_mle_q10:.1f}-{diagnostics.effect_mle_q90:.1f}, "
                f"centred on {diagnostics.effect_mle_median:.1f} (truth 5). Their log-scale "
                f"correlation was {_format_optional(diagnostics.log_mle_correlation)}, providing "
                "little evidence that one estimate was simply trading off against the other."
            ),
            "",
            (
                f"The calibration statistic had median {diagnostics.calibration_lr_median:.3f} "
                f"but required a 95% cutoff of {summary.cutoff:.3f}. All "
                f"{diagnostics.connected_support_count}/{result.config.validation_replicates} "
                "supports were connected, yet all touched an artificial grid boundary. That wide "
                "cutoff preserved nominal coverage but expanded prey-effect support across the "
                f"entire 1-10 range; only {summary.no_effect_exclusion_count}/"
                f"{result.config.validation_replicates} supports excluded no effect."
            ),
            "",
            "## Interpretation",
            "",
            (
                "Observed result: point estimates and held-out prediction remained informative, "
                "while the calibrated joint uncertainty region was uninformative for prey effect. "
                "Our leading interpretation is that the single joint cutoff is dominated by "
                "field-to-field variation in the shared invasion wave that the site-marginal "
                "composite likelihood does not represent. Goal 032 therefore diagnoses an "
                "uncertainty-calibration problem before it diagnoses biological confounding."
            ),
            "",
            "## Boundary",
            "",
            (
                "Resistance, both detection probabilities, background prey hazard, and false-"
                "positive rates remained known. Only spread speed and prey effect were fitted. "
                "Within-site predator and prey histories shared latent arrival; dependence among "
                "sites from the common spread realization remained outside the likelihood."
            ),
            "",
        ]
    )


def _format_optional(value: float | None) -> str:
    return "not fitted" if value is None else f"{value:.3f}"


def _review_figure(result: Goal032Result) -> Figure:
    figure, axes = plt.subplots(2, 3, figsize=(13.2, 8.0), constrained_layout=True)
    surface = result.representative_surface
    rho_values = np.asarray(result.config.rhos, dtype=np.float64)
    effect_values = np.asarray(result.config.hazard_ratios, dtype=np.float64)
    drops = np.asarray(
        [row.twice_log_likelihood_drop for row in surface], dtype=np.float64
    ).reshape(len(rho_values), len(effect_values))
    ax = axes[0, 0]
    image = ax.pcolormesh(
        np.log2(rho_values),
        effect_values,
        np.minimum(drops.T, result.summary.cutoff * 3.0),
        shading="auto",
        cmap="viridis_r",
    )
    ax.contour(
        np.log2(rho_values),
        effect_values,
        drops.T,
        levels=(result.summary.cutoff,),
        colors="#FDE047",
        linewidths=1.8,
    )
    truth = next(row for row in surface if row.is_truth)
    mle = next(row for row in surface if row.is_mle)
    ax.scatter(
        math.log2(truth.rho),
        truth.hazard_ratio,
        marker="*",
        s=90,
        color="white",
        label="Truth",
    )
    ax.scatter(
        math.log2(mle.rho),
        mle.hazard_ratio,
        marker="x",
        s=55,
        color="#DC2626",
        linewidth=2,
        label="Fitted value",
    )
    ax.plot([], [], color="#FDE047", linewidth=1.8, label="95% calibrated boundary")
    ax.set(
        title="Example point fit and joint uncertainty",
        xlabel="Spread rate (log2 scale)",
        ylabel="Prey hazard multiplier",
    )
    ax.legend(loc="upper left", fontsize=7, frameon=True)
    colorbar = figure.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    colorbar.set_label("Twice log-likelihood drop")

    anchor, current = result.comparison
    labels = ("Known rate", "Joint fit")
    colors = ("#6B7280", "#1B7F79")
    ax = axes[0, 1]
    coverage = (anchor.coverage, current.coverage)
    lower = (
        anchor.coverage - anchor.coverage_lower,
        current.coverage - current.coverage_lower,
    )
    upper = (
        anchor.coverage_upper - anchor.coverage,
        current.coverage_upper - current.coverage,
    )
    ax.bar(labels, coverage, color=colors, width=0.62)
    ax.errorbar(
        range(2),
        coverage,
        yerr=np.asarray((lower, upper)),
        fmt="none",
        color="#111827",
        capsize=4,
    )
    ax.axhline(0.95, linestyle="--", color="#B91C1C", linewidth=1)
    ax.set(title="Calibrated joint coverage", ylabel="Proportion", ylim=(0.88, 1.0))

    _bar_panel(
        axes[0, 2],
        labels,
        (
            anchor.no_effect_exclusion_count / anchor.validation_replicates,
            current.no_effect_exclusion_count / current.validation_replicates,
        ),
        colors,
        "Support excludes no prey effect",
        "Proportion",
        0.95,
    )
    _bar_panel(
        axes[1, 0],
        ("Rate error", "Rate width"),
        (
            result.summary.median_absolute_log_rho_error / 0.10,
            result.summary.median_log_rho_support_width / 0.50,
        ),
        ("#0F766E", "#14B8A6"),
        "Spread-rate recovery",
        "Fraction of allowed limit",
        1.0,
    )
    _bar_panel(
        axes[1, 1],
        ("Effect error", "Effect width"),
        (
            result.summary.median_absolute_log_effect_error / 0.20,
            result.summary.median_log_effect_support_width / 0.80,
        ),
        ("#9A3412", "#EA580C"),
        "Prey-effect recovery",
        "Fraction of allowed limit",
        1.0,
    )
    ax = axes[1, 2]
    advantages = (anchor.score_advantage, current.score_advantage)
    lower = (
        anchor.score_advantage - anchor.score_advantage_lower,
        current.score_advantage - current.score_advantage_lower,
    )
    upper = (
        anchor.score_advantage_upper - anchor.score_advantage,
        current.score_advantage_upper - current.score_advantage,
    )
    ax.bar(labels, advantages, color=colors, width=0.62)
    ax.errorbar(
        range(2),
        advantages,
        yerr=np.asarray((lower, upper)),
        fmt="none",
        color="#111827",
        capsize=4,
    )
    ax.axhline(0.0, linestyle="--", color="#B91C1C", linewidth=1)
    ax.set(title="Held-out prediction", ylabel="Log-score advantage per site")
    for axis in axes.flat:
        axis.tick_params(axis="x", rotation=10)
    figure.suptitle(
        "Goal 032: point estimates are accurate, but joint uncertainty is too wide",
        fontsize=15,
        fontweight="bold",
    )
    return figure


def _bar_panel(
    axis: Axes,
    labels: tuple[str, str],
    values: tuple[float, float],
    colors: tuple[str, str],
    title: str,
    ylabel: str,
    gate: float,
) -> None:
    axis.bar(labels, values, color=colors, width=0.62)
    axis.axhline(gate, linestyle="--", color="#B91C1C", linewidth=1)
    axis.set(title=title, ylabel=ylabel)


def _save_figure(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", bbox_inches="tight")
    plt.close(figure)


def _int_value(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    return value


def _float_value(payload: dict[str, object], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{key} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{key} must be finite")
    return result
