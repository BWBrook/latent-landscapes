"""Latent-arrival prey-effect positive control."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections.abc import Sequence
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

from latent_landscapes.goal002.calibration import (
    normal_mean_interval,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal006.spread import compute_paired_spreads
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal026 import (
    BACKGROUND_HAZARD,
    HAZARD_RATIO_GRID,
    NEUTRAL_HAZARD_GRID,
    SURVEY_TIMES,
    LikelihoodProfile,
    RecoverySummary,
    sample_extirpation_time,
)

MASTER_SEED = 20260812031
TRUTH_HAZARD_RATIO = 5.0
PREDATOR_DETECTION_PROBABILITY = 0.65
PREY_DETECTION_PROBABILITY = 0.65
VISITS_PER_SURVEY = 2
CATEGORY_COUNT = len(SURVEY_TIMES) + 1
PSEUDO_ARRIVALS = (5.0, 15.0, 25.0, 35.0, 45.0, 55.0, 70.0)
DEFAULT_GOAL029_EVIDENCE_DIR = Path(
    "artifacts/goal029_known_arrival_known_imperfect_prey_detection"
)
RECOVERED = "latent_arrival_prey_effect_recovered"
NOT_RECOVERED = "latent_arrival_prey_effect_not_recovered"
EXPECTED_FILES = (
    "calibration_statistics.csv",
    "validation_results.csv",
    "representative_cross_layer_histories.csv",
    "arrival_conditioning_summary.csv",
    "benchmark_comparison.csv",
    "summary.json",
    "review.md",
    "latent_arrival_prey_effect.svg",
)


@dataclass(frozen=True, slots=True)
class Goal031Config:
    """Frozen one-parameter latent-arrival benchmark."""

    master_seed: int = MASTER_SEED
    bank_size: int = 4_096
    calibration_replicates: int = 2_000
    validation_replicates: int = 1_000
    calibration_rank_one_based: int = 1_901
    background_hazard: float = BACKGROUND_HAZARD
    truth_hazard_ratio: float = TRUTH_HAZARD_RATIO
    predator_detection_probability: float = PREDATOR_DETECTION_PROBABILITY
    prey_detection_probability: float = PREY_DETECTION_PROBABILITY
    visits_per_survey: int = VISITS_PER_SURVEY
    hazard_ratios: tuple[float, ...] = HAZARD_RATIO_GRID
    neutral_hazards: tuple[float, ...] = NEUTRAL_HAZARD_GRID

    def __post_init__(self) -> None:
        if self.bank_size <= 0:
            raise ValueError("bank size must be positive")
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within calibration replicates")
        if self.visits_per_survey != 2:
            raise ValueError("Goal 031 requires exactly two visits per survey")
        if not 0.0 < self.predator_detection_probability < 1.0:
            raise ValueError("predator detection probability must be between zero and one")
        if not 0.0 < self.prey_detection_probability < 1.0:
            raise ValueError("prey detection probability must be between zero and one")
        if self.background_hazard <= 0.0 or not math.isfinite(self.background_hazard):
            raise ValueError("background hazard must be finite and positive")
        if sum(math.isclose(value, self.truth_hazard_ratio) for value in self.hazard_ratios) != 1:
            raise ValueError("truth hazard ratio must occur once on its grid")
        if not self.hazard_ratios or self.hazard_ratios[0] != 1.0:
            raise ValueError("hazard-ratio grid must begin at no effect")
        if any(value <= 0.0 for value in (*self.hazard_ratios, *self.neutral_hazards)):
            raise ValueError("candidate hazards must be positive")

    @property
    def is_production(self) -> bool:
        return self == Goal031Config()


DEFAULT_CONFIG = Goal031Config()


def smoke_config() -> Goal031Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal031Config(
        bank_size=16,
        calibration_replicates=8,
        validation_replicates=8,
        calibration_rank_one_based=8,
        hazard_ratios=(1.0, 3.0, 5.0, 7.0, 9.0),
        neutral_hazards=(0.0005, 0.001, 0.002, 0.004, 0.008, 0.016, 0.032),
    )


@dataclass(frozen=True, slots=True)
class DatasetSeed:
    phase: str
    index: int
    process_seed: int
    predator_detection_seed: int
    prey_seed: int
    prey_detection_seed: int


@dataclass(frozen=True, slots=True)
class SeedManifest:
    bank_seeds: tuple[int, ...]
    calibration: tuple[DatasetSeed, ...]
    validation: tuple[DatasetSeed, ...]


@dataclass(frozen=True, slots=True)
class CrossLayerHistory:
    dataset_phase: str
    dataset_index: int
    site_index: int
    site_id: str
    cluster_id: str
    split: str
    row: int
    col: int
    true_predator_arrival: float
    true_prey_extirpation: float
    predator_detection_counts: tuple[int, ...]
    prey_detection_counts: tuple[int, ...]
    true_predator_present: tuple[bool, ...]
    true_prey_alive: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class SurveyHistoryRow:
    site_id: str
    split: str
    row: int
    col: int
    survey_time: float
    true_predator_arrival: float
    true_predator_present: bool
    predator_detection_count: int
    true_prey_extirpation: float
    true_prey_alive: bool
    prey_detection_count: int


@dataclass(frozen=True, slots=True)
class ArrivalIntegration:
    site_ids: tuple[str, ...]
    hazard_ratios: tuple[float, ...]
    category_mass: NDArray[np.float64]
    survival_moments: NDArray[np.float64]
    bank_arrivals: NDArray[np.float64]
    bank_checksum: str


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
    mle_hazard_ratio: float
    absolute_log_hazard_ratio_error: float
    support_lower: float
    support_upper: float
    log_support_width: float
    fitted_neutral_hazard: float
    heldout_predator_prey_log_score: float
    heldout_neutral_log_score: float
    heldout_log_score_advantage: float


@dataclass(frozen=True, slots=True)
class ArrivalConditioningRow:
    site_id: str
    split: str
    row: int
    col: int
    predator_detection_total: int
    first_predator_detection_time: float | None
    true_arrival: float
    prior_arrival_mean: float
    conditioned_arrival_mean: float
    conditioned_arrival_p10: float
    conditioned_arrival_p90: float
    prior_absolute_error: float
    conditioned_absolute_error: float


@dataclass(frozen=True, slots=True)
class KnownArrivalAnchor:
    calibration_replicates: int
    validation_replicates: int
    coverage_count: int
    coverage: float
    coverage_lower: float
    coverage_upper: float
    connected_interior_count: int
    no_effect_exclusion_count: int
    median_absolute_log_error: float
    median_log_support_width: float
    score_advantage: float
    score_advantage_lower: float
    score_advantage_upper: float


@dataclass(frozen=True, slots=True)
class BenchmarkComparison:
    arrival_information: str
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
    recovered: bool


@dataclass(frozen=True, slots=True)
class CalibrationWork:
    statistic: CalibrationStatistic
    valid_histories: bool
    finite_likelihood: bool


@dataclass(frozen=True, slots=True)
class ValidationWork:
    result: ValidationResult
    histories: tuple[CrossLayerHistory, ...]
    valid_histories: bool
    finite_likelihood: bool


@dataclass(frozen=True, slots=True)
class Goal031Result:
    config: Goal031Config
    known_arrival_anchor: KnownArrivalAnchor
    calibration_statistics: tuple[CalibrationStatistic, ...]
    validation_results: tuple[ValidationResult, ...]
    representative_histories: tuple[SurveyHistoryRow, ...]
    arrival_conditioning: tuple[ArrivalConditioningRow, ...]
    summary: RecoverySummary
    integration: ArrivalIntegration
    invariants: dict[str, bool]
    outcome: str

    @property
    def comparison(self) -> tuple[BenchmarkComparison, BenchmarkComparison]:
        anchor = self.known_arrival_anchor
        current = self.summary
        return (
            BenchmarkComparison(
                "exact_realized_arrival_goal029",
                anchor.calibration_replicates,
                anchor.validation_replicates,
                anchor.coverage,
                anchor.coverage_lower,
                anchor.coverage_upper,
                anchor.connected_interior_count,
                anchor.no_effect_exclusion_count,
                anchor.median_absolute_log_error,
                anchor.median_log_support_width,
                anchor.score_advantage,
                anchor.score_advantage_lower,
                anchor.score_advantage_upper,
                True,
            ),
            BenchmarkComparison(
                "latent_arrival_from_predator_detections_goal031",
                self.config.calibration_replicates,
                self.config.validation_replicates,
                current.coverage.estimate,
                current.coverage.lower,
                current.coverage.upper,
                current.connected_interior_count,
                current.null_exclusion_count,
                current.median_absolute_log_error,
                current.median_log_support_width,
                current.heldout_log_score_advantage.estimate,
                current.heldout_log_score_advantage.lower,
                current.heldout_log_score_advantage.upper,
                self.outcome == RECOVERED,
            ),
        )


_BANK_FIXED: FixedInputs | None = None
_WORKER_CONFIG: Goal031Config | None = None
_WORKER_FIXED: FixedInputs | None = None
_WORKER_INTEGRATION: ArrivalIntegration | None = None


def load_goal029_anchor(evidence_dir: Path) -> KnownArrivalAnchor:
    """Load and reconcile the accepted exact-arrival benchmark."""
    payload = cast(
        dict[str, object],
        json.loads((Path(evidence_dir) / "summary.json").read_text(encoding="utf-8")),
    )
    if payload.get("goal") != "029-known-arrival-known-imperfect-prey-detection":
        raise ValueError("Goal 029 evidence has the wrong identity")
    if payload.get("outcome") != "known_imperfect_prey_detection_recovered":
        raise ValueError("Goal 029 anchor was not accepted as recovered")
    calibration = cast(dict[str, object], payload.get("calibration"))
    validation = cast(dict[str, object], payload.get("validation"))
    coverage = cast(dict[str, object], validation.get("coverage"))
    score = cast(dict[str, object], validation.get("heldout_log_score_advantage"))
    anchor = KnownArrivalAnchor(
        _int_value(calibration, "replicates"),
        _int_value(validation, "replicates"),
        _int_value(validation, "coverage_count"),
        _float_value(coverage, "estimate"),
        _float_value(coverage, "lower"),
        _float_value(coverage, "upper"),
        _int_value(validation, "connected_interior_count"),
        _int_value(validation, "null_exclusion_count"),
        _float_value(validation, "median_absolute_log_error"),
        _float_value(validation, "median_log_support_width"),
        _float_value(score, "estimate"),
        _float_value(score, "lower"),
        _float_value(score, "upper"),
    )
    expected = (2_000, 1_000, 956, 994, 1_000)
    observed = (
        anchor.calibration_replicates,
        anchor.validation_replicates,
        anchor.coverage_count,
        anchor.connected_interior_count,
        anchor.no_effect_exclusion_count,
    )
    if observed != expected:
        raise ValueError("Goal 029 anchor counts do not reconcile")
    return anchor


def spawn_seed_manifest(config: Goal031Config) -> SeedManifest:
    """Create independent bank, process, predator, prey, and prey-detection streams."""
    roots = np.random.SeedSequence(config.master_seed).spawn(9)
    bank = tuple(_seed_int(child) for child in roots[0].spawn(config.bank_size))
    calibration = _phase_seeds("calibration", config.calibration_replicates, tuple(roots[1:5]))
    validation = _phase_seeds("validation", config.validation_replicates, tuple(roots[5:9]))
    return SeedManifest(bank, calibration, validation)


def generate_cross_layer_dataset(
    seed: DatasetSeed,
    config: Goal031Config = DEFAULT_CONFIG,
    fixed_inputs: FixedInputs | None = None,
) -> tuple[NDArray[np.float64], tuple[CrossLayerHistory, ...]]:
    """Generate one shared predator-arrival, predator-history, and prey-history dataset."""
    fixed = fixed_inputs if fixed_inputs is not None else goal011.build_fixed_inputs()
    _, spreads = compute_paired_spreads(
        fixed.landscape,
        rng=np.random.default_rng(seed.process_seed),
        etas=(1.0,),
        rho=1.0,
    )
    arrival = spreads[0].arrival
    predator_rng = np.random.default_rng(seed.predator_detection_seed)
    prey_rng = np.random.default_rng(seed.prey_seed)
    prey_detection_rng = np.random.default_rng(seed.prey_detection_seed)
    histories: list[CrossLayerHistory] = []
    sites = tuple(sorted(fixed.design.sites, key=lambda value: value.site_id))
    for site_index, site in enumerate(sites):
        site_arrival = float(arrival[site.row, site.col])
        predator_present = tuple(site_arrival <= time for time in SURVEY_TIMES)
        predator_counts = tuple(
            int(
                predator_rng.binomial(
                    config.visits_per_survey,
                    config.predator_detection_probability,
                )
            )
            if present
            else 0
            for present in predator_present
        )
        extirpation = sample_extirpation_time(
            predator_arrival=site_arrival,
            background_hazard=config.background_hazard,
            hazard_ratio=config.truth_hazard_ratio,
            exponential_threshold=float(prey_rng.exponential()),
        )
        prey_alive = tuple(extirpation > time for time in SURVEY_TIMES)
        prey_counts = tuple(
            int(
                prey_detection_rng.binomial(
                    config.visits_per_survey,
                    config.prey_detection_probability,
                )
            )
            if alive
            else 0
            for alive in prey_alive
        )
        histories.append(
            CrossLayerHistory(
                seed.phase,
                seed.index,
                site_index,
                site.site_id,
                site.cluster_id,
                site.split,
                site.row,
                site.col,
                site_arrival,
                extirpation,
                predator_counts,
                prey_counts,
                predator_present,
                prey_alive,
            )
        )
    return arrival, tuple(histories)


def build_arrival_integration(
    bank_arrivals: NDArray[np.float64],
    site_ids: tuple[str, ...],
    hazard_ratios: tuple[float, ...],
    background_hazard: float,
) -> ArrivalIntegration:
    """Collapse the raw arrival bank into shared-arrival survival moments."""
    bank = np.asarray(bank_arrivals, dtype=np.float64)
    ratios = np.asarray(hazard_ratios, dtype=np.float64)
    if bank.ndim != 2 or bank.shape[1] != len(site_ids) or bank.shape[0] <= 0:
        raise ValueError("arrival bank shape does not match site identifiers")
    if not np.isfinite(bank).all() or (bank < 0.0).any():
        raise ValueError("arrival bank must be finite and non-negative")
    if ratios.ndim != 1 or not np.isfinite(ratios).all() or (ratios <= 0.0).any():
        raise ValueError("hazard ratios must be finite and positive")
    categories = np.searchsorted(np.asarray(SURVEY_TIMES), bank, side="left")
    denominator = bank.shape[0] + 0.5 * CATEGORY_COUNT
    moments = np.empty(
        (len(ratios), len(site_ids), len(SURVEY_TIMES) + 1, CATEGORY_COUNT),
        dtype=np.float64,
    )
    masses = np.empty((len(site_ids), CATEGORY_COUNT), dtype=np.float64)
    for site_index in range(len(site_ids)):
        for category in range(CATEGORY_COUNT):
            values = bank[categories[:, site_index] == category, site_index]
            mass = (len(values) + 0.5) / denominator
            masses[site_index, category] = mass
            moments[:, site_index, 0, category] = mass
            pseudo_arrival = PSEUDO_ARRIVALS[category]
            for time_index, survey_time in enumerate(SURVEY_TIMES, start=1):
                if category >= time_index:
                    total = (len(values) + 0.5) * math.exp(-background_hazard * survey_time)
                    moments[:, site_index, time_index, category] = total / denominator
                    continue
                if len(values):
                    survival = np.exp(
                        -background_hazard
                        * (
                            ratios[:, None] * survey_time
                            + (1.0 - ratios[:, None]) * values[None, :]
                        )
                    ).sum(axis=1)
                else:
                    survival = np.zeros(len(ratios), dtype=np.float64)
                pseudo_survival = np.exp(
                    -background_hazard * (ratios * survey_time + (1.0 - ratios) * pseudo_arrival)
                )
                moments[:, site_index, time_index, category] = (
                    survival + 0.5 * pseudo_survival
                ) / denominator
    checksum = hashlib.sha256(np.ascontiguousarray(bank).tobytes()).hexdigest()
    return ArrivalIntegration(
        site_ids,
        hazard_ratios,
        masses,
        moments,
        bank.copy(),
        checksum,
    )


def latent_arrival_profile(
    histories: tuple[CrossLayerHistory, ...],
    integration: ArrivalIntegration,
    config: Goal031Config,
) -> LikelihoodProfile:
    """Profile prey effect while sharing latent arrival within each site."""
    values = _joint_log_likelihoods(histories, integration, config)
    candidates = np.asarray(integration.hazard_ratios, dtype=np.float64)
    maximum_index = int(np.argmax(values))
    return LikelihoodProfile(
        candidates,
        values,
        float(values[maximum_index]),
        float(candidates[maximum_index]),
    )


def neutral_hazard_profile(
    histories: tuple[CrossLayerHistory, ...],
    config: Goal031Config,
    integration: ArrivalIntegration,
) -> LikelihoodProfile:
    """Profile a constant prey hazard with the same predator observations."""
    candidates = np.asarray(config.neutral_hazards, dtype=np.float64)
    values = _neutral_log_likelihoods(histories, candidates, integration, config)
    maximum_index = int(np.argmax(values))
    return LikelihoodProfile(
        candidates,
        values,
        float(values[maximum_index]),
        float(candidates[maximum_index]),
    )


def classify_outcome(
    *, invariants: dict[str, bool], summary: RecoverySummary, validation_count: int
) -> str:
    """Apply the unchanged Goal 029 one-parameter recovery gates."""
    if not invariants or not all(invariants.values()) or validation_count <= 0:
        return "implementation_blocked"
    required_count = math.ceil(0.95 * validation_count)
    if (
        summary.coverage.lower <= 0.95 <= summary.coverage.upper
        and summary.connected_interior_count >= required_count
        and summary.null_exclusion_count >= required_count
        and summary.median_absolute_log_error <= 0.20
        and summary.median_log_support_width <= 0.80
        and summary.heldout_log_score_advantage.lower > 0.0
    ):
        return RECOVERED
    return NOT_RECOVERED


def run_goal031(
    goal029_evidence_dir: Path = DEFAULT_GOAL029_EVIDENCE_DIR,
    config: Goal031Config = DEFAULT_CONFIG,
    *,
    workers: int = 1,
) -> Goal031Result:
    """Calibrate and validate the latent-arrival prey-effect benchmark."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    anchor = load_goal029_anchor(goal029_evidence_dir)
    fixed = goal011.build_fixed_inputs()
    manifest = spawn_seed_manifest(config)
    bank_arrivals = _build_arrival_bank(fixed, manifest.bank_seeds, workers)
    sites = tuple(sorted(fixed.design.sites, key=lambda value: value.site_id))
    integration = build_arrival_integration(
        bank_arrivals,
        tuple(site.site_id for site in sites),
        config.hazard_ratios,
        config.background_hazard,
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
        manifest.validation, config, fixed, integration, cutoff.cutoff, workers
    )
    validation_rows = tuple(work.result for work in validation_work)
    representative = validation_work[0].histories
    if not representative:
        raise RuntimeError("representative validation histories are missing")
    flattened = _flatten_histories(representative)
    conditioning = _arrival_conditioning(representative, integration, config)

    coverage_count = sum(row.truth_included for row in validation_rows)
    score_advantage = normal_mean_interval(
        [row.heldout_log_score_advantage for row in validation_rows]
    )
    summary = RecoverySummary(
        cutoff=cutoff.cutoff,
        coverage_count=coverage_count,
        coverage=wilson_interval(coverage_count, len(validation_rows)),
        connected_interior_count=sum(
            row.support_component_count == 1 and not row.support_boundary_contact
            for row in validation_rows
        ),
        null_exclusion_count=sum(row.no_effect_excluded for row in validation_rows),
        median_absolute_log_error=median(
            row.absolute_log_hazard_ratio_error for row in validation_rows
        ),
        median_log_support_width=median(row.log_support_width for row in validation_rows),
        heldout_log_score_advantage=score_advantage,
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
    unconditional_survival = integration.survival_moments.sum(axis=3)
    invariants = {
        "goal029_anchor_reconciled": True,
        "fixed_spatial_inputs_reconciled": all(fixed.invariants.values()),
        "integration_bank_shape": integration.bank_arrivals.shape == (config.bank_size, 160),
        "category_mass_reconciled": bool(
            np.allclose(integration.category_mass.sum(axis=1), 1.0, atol=1e-12)
        ),
        "survival_moments_finite_and_monotone": bool(
            np.isfinite(integration.survival_moments).all()
            and np.all(np.diff(unconditional_survival, axis=2) <= 1e-12)
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
        "representative_history_count": len(flattened) == 160 * len(SURVEY_TIMES),
        "arrival_conditioning_count": len(conditioning) == 160,
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
    return Goal031Result(
        config,
        anchor,
        calibration_rows,
        validation_rows,
        flattened,
        conditioning,
        summary,
        integration,
        invariants,
        outcome,
    )


def write_review_bundle(result: Goal031Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the compact eight-file review surface."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("output directory must be empty")
    _write_dataclass_csv(target / "calibration_statistics.csv", result.calibration_statistics)
    _write_dataclass_csv(target / "validation_results.csv", result.validation_results)
    _write_dataclass_csv(
        target / "representative_cross_layer_histories.csv",
        result.representative_histories,
    )
    _write_dataclass_csv(target / "arrival_conditioning_summary.csv", result.arrival_conditioning)
    _write_dataclass_csv(target / "benchmark_comparison.csv", result.comparison)
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    _save_figure(target / "latent_arrival_prey_effect.svg", _review_figure(result))
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 031 review surface is incomplete")
    return written


def _phase_seeds(
    phase: str,
    count: int,
    roots: tuple[np.random.SeedSequence, ...],
) -> tuple[DatasetSeed, ...]:
    children = tuple(root.spawn(count) for root in roots)
    return tuple(
        DatasetSeed(
            phase,
            index,
            _seed_int(children[0][index]),
            _seed_int(children[1][index]),
            _seed_int(children[2][index]),
            _seed_int(children[3][index]),
        )
        for index in range(count)
    )


def _seed_int(sequence: np.random.SeedSequence) -> int:
    return int(sequence.generate_state(1, dtype=np.uint64)[0])


def _init_bank_worker(fixed: FixedInputs) -> None:
    global _BANK_FIXED
    _BANK_FIXED = fixed


def _bank_row_worker(seed: int) -> NDArray[np.float64]:
    if _BANK_FIXED is None:
        raise RuntimeError("bank worker was not initialized")
    _, spreads = compute_paired_spreads(
        _BANK_FIXED.landscape,
        rng=np.random.default_rng(seed),
        etas=(1.0,),
        rho=1.0,
    )
    sites = tuple(sorted(_BANK_FIXED.design.sites, key=lambda value: value.site_id))
    return np.asarray(
        [spreads[0].arrival[site.row, site.col] for site in sites],
        dtype=np.float64,
    )


def _build_arrival_bank(
    fixed: FixedInputs, seeds: tuple[int, ...], workers: int
) -> NDArray[np.float64]:
    if workers == 1:
        _init_bank_worker(fixed)
        rows = tuple(_bank_row_worker(seed) for seed in seeds)
    else:
        chunksize = max(1, len(seeds) // (workers * 8))
        with ProcessPoolExecutor(
            max_workers=workers,
            initializer=_init_bank_worker,
            initargs=(fixed,),
        ) as executor:
            rows = tuple(executor.map(_bank_row_worker, seeds, chunksize=chunksize))
    return np.asarray(rows, dtype=np.float64)


def _init_outer_worker(
    config: Goal031Config,
    fixed: FixedInputs,
    integration: ArrivalIntegration,
) -> None:
    global _WORKER_CONFIG, _WORKER_FIXED, _WORKER_INTEGRATION
    _WORKER_CONFIG = config
    _WORKER_FIXED = fixed
    _WORKER_INTEGRATION = integration


def _run_calibration_tasks(
    seeds: tuple[DatasetSeed, ...],
    config: Goal031Config,
    fixed: FixedInputs,
    integration: ArrivalIntegration,
    workers: int,
) -> tuple[CalibrationWork, ...]:
    if workers == 1:
        _init_outer_worker(config, fixed, integration)
        return tuple(_calibration_worker(seed) for seed in seeds)
    chunksize = max(1, len(seeds) // (workers * 8))
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_init_outer_worker,
        initargs=(config, fixed, integration),
    ) as executor:
        return tuple(executor.map(_calibration_worker, seeds, chunksize=chunksize))


def _run_validation_tasks(
    seeds: tuple[DatasetSeed, ...],
    config: Goal031Config,
    fixed: FixedInputs,
    integration: ArrivalIntegration,
    cutoff: float,
    workers: int,
) -> tuple[ValidationWork, ...]:
    tasks = tuple((seed, cutoff) for seed in seeds)
    if workers == 1:
        _init_outer_worker(config, fixed, integration)
        return tuple(_validation_worker(task) for task in tasks)
    chunksize = max(1, len(tasks) // (workers * 8))
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_init_outer_worker,
        initargs=(config, fixed, integration),
    ) as executor:
        return tuple(executor.map(_validation_worker, tasks, chunksize=chunksize))


def _worker_context() -> tuple[Goal031Config, FixedInputs, ArrivalIntegration]:
    if _WORKER_CONFIG is None or _WORKER_FIXED is None or _WORKER_INTEGRATION is None:
        raise RuntimeError("outer worker was not initialized")
    return _WORKER_CONFIG, _WORKER_FIXED, _WORKER_INTEGRATION


def _calibration_worker(seed: DatasetSeed) -> CalibrationWork:
    config, fixed, integration = _worker_context()
    _, histories = generate_cross_layer_dataset(seed, config, fixed)
    profile = latent_arrival_profile(histories, integration, config)
    return CalibrationWork(
        CalibrationStatistic(
            seed.index,
            _likelihood_ratio_at_truth(profile, config.truth_hazard_ratio),
            _detected_visit_count(histories, predator=True),
            _detected_visit_count(histories, predator=False),
        ),
        _histories_valid(histories, config),
        bool(np.isfinite(profile.log_likelihoods).all()),
    )


def _validation_worker(task: tuple[DatasetSeed, float]) -> ValidationWork:
    seed, cutoff = task
    config, fixed, integration = _worker_context()
    _, histories = generate_cross_layer_dataset(seed, config, fixed)
    all_profile = latent_arrival_profile(histories, integration, config)
    training = tuple(row for row in histories if row.split == "training")
    holdout = tuple(row for row in histories if row.split == "holdout")
    training_profile = latent_arrival_profile(training, integration, config)
    neutral_profile = neutral_hazard_profile(training, config, integration)
    support = _summarize_support(all_profile, cutoff, config.truth_hazard_ratio)
    predator_prey_score = _log_likelihood_at_ratio(
        holdout, training_profile.mle, integration, config
    ) / len(holdout)
    neutral_score = _log_likelihood_at_neutral(
        holdout, neutral_profile.mle, integration, config
    ) / len(holdout)
    result = ValidationResult(
        seed.index,
        _detected_visit_count(histories, predator=True),
        _detected_visit_count(histories, predator=False),
        support[0],
        support[1],
        support[2],
        support[3],
        all_profile.mle,
        abs(math.log(all_profile.mle / config.truth_hazard_ratio)),
        support[4],
        support[5],
        math.log(support[5] / support[4]),
        neutral_profile.mle,
        predator_prey_score,
        neutral_score,
        predator_prey_score - neutral_score,
    )
    finite = bool(
        np.isfinite(all_profile.log_likelihoods).all()
        and np.isfinite(training_profile.log_likelihoods).all()
        and np.isfinite(neutral_profile.log_likelihoods).all()
        and math.isfinite(predator_prey_score)
        and math.isfinite(neutral_score)
    )
    return ValidationWork(
        result,
        histories if seed.index == 0 else (),
        _histories_valid(histories, config),
        finite,
    )


def _joint_log_likelihoods(
    histories: tuple[CrossLayerHistory, ...],
    integration: ArrivalIntegration,
    config: Goal031Config,
) -> NDArray[np.float64]:
    if not histories:
        raise ValueError("cross-layer histories must not be empty")
    indices = np.asarray([row.site_index for row in histories], dtype=np.int64)
    if np.any(indices < 0) or np.any(indices >= len(integration.site_ids)):
        raise ValueError("history site index lies outside the integration bank")
    predator_probabilities = _predator_category_probabilities(histories, config)
    event_coefficients, survival_coefficients = _prey_emission_coefficients(histories, config)
    selected_moments = integration.survival_moments[:, indices, :, :]
    weighted_survival = np.einsum(
        "hstc,sc->hst",
        selected_moments,
        predator_probabilities,
        optimize=True,
    )
    event_probabilities = weighted_survival[:, :, :-1] - weighted_survival[:, :, 1:]
    site_probabilities = (
        np.einsum("hsj,sj->hs", event_probabilities, event_coefficients, optimize=True)
        + weighted_survival[:, :, -1] * survival_coefficients[None, :]
    )
    if not np.isfinite(site_probabilities).all() or np.any(site_probabilities <= 0.0):
        raise RuntimeError("shared-arrival likelihood produced invalid site probabilities")
    return np.asarray(np.log(site_probabilities).sum(axis=1), dtype=np.float64)


def _neutral_log_likelihoods(
    histories: tuple[CrossLayerHistory, ...],
    hazards: NDArray[np.float64],
    integration: ArrivalIntegration,
    config: Goal031Config,
) -> NDArray[np.float64]:
    if not histories:
        raise ValueError("cross-layer histories must not be empty")
    if hazards.ndim != 1 or not np.isfinite(hazards).all() or np.any(hazards <= 0.0):
        raise ValueError("neutral hazards must be finite and positive")
    indices = np.asarray([row.site_index for row in histories], dtype=np.int64)
    predator_probabilities = _predator_category_probabilities(histories, config)
    predator_marginals = np.einsum(
        "sc,sc->s",
        integration.category_mass[indices],
        predator_probabilities,
        optimize=True,
    )
    event_coefficients, survival_coefficients = _prey_emission_coefficients(histories, config)
    times = np.asarray((0.0, *SURVEY_TIMES), dtype=np.float64)
    survival = np.exp(-hazards[:, None] * times[None, :])
    event_probabilities = survival[:, :-1] - survival[:, 1:]
    prey_probabilities = (
        np.einsum("hj,sj->hs", event_probabilities, event_coefficients, optimize=True)
        + survival[:, -1, None] * survival_coefficients[None, :]
    )
    site_probabilities = prey_probabilities * predator_marginals[None, :]
    if not np.isfinite(site_probabilities).all() or np.any(site_probabilities <= 0.0):
        raise RuntimeError("neutral likelihood produced invalid site probabilities")
    return np.asarray(np.log(site_probabilities).sum(axis=1), dtype=np.float64)


def _predator_category_probabilities(
    histories: tuple[CrossLayerHistory, ...], config: Goal031Config
) -> NDArray[np.float64]:
    result = np.ones((len(histories), CATEGORY_COUNT), dtype=np.float64)
    p = config.predator_detection_probability
    n = config.visits_per_survey
    for site_index, history in enumerate(histories):
        for category in range(CATEGORY_COUNT):
            probability = 1.0
            for survey_index, count in enumerate(history.predator_detection_counts):
                if category > survey_index:
                    if count:
                        probability = 0.0
                        break
                else:
                    probability *= math.comb(n, count) * p**count * (1.0 - p) ** (n - count)
            result[site_index, category] = probability
    return result


def _prey_emission_coefficients(
    histories: tuple[CrossLayerHistory, ...], config: Goal031Config
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    p = config.prey_detection_probability
    n = config.visits_per_survey
    alive = np.asarray(
        [
            [
                math.comb(n, count) * p**count * (1.0 - p) ** (n - count)
                for count in row.prey_detection_counts
            ]
            for row in histories
        ],
        dtype=np.float64,
    )
    dead = np.asarray(
        [[count == 0 for count in row.prey_detection_counts] for row in histories],
        dtype=np.float64,
    )
    events = np.empty_like(alive)
    for event_index in range(len(SURVEY_TIMES)):
        before = alive[:, :event_index].prod(axis=1) if event_index else 1.0
        after = dead[:, event_index:].prod(axis=1)
        events[:, event_index] = before * after
    return events, alive.prod(axis=1)


def _log_likelihood_at_ratio(
    histories: tuple[CrossLayerHistory, ...],
    ratio: float,
    integration: ArrivalIntegration,
    config: Goal031Config,
) -> float:
    indices = np.flatnonzero(
        np.isclose(np.asarray(integration.hazard_ratios), ratio, rtol=0.0, atol=1e-12)
    )
    if len(indices) != 1:
        raise ValueError("fitted hazard ratio must occur once on the integration grid")
    return float(_joint_log_likelihoods(histories, integration, config)[int(indices[0])])


def _log_likelihood_at_neutral(
    histories: tuple[CrossLayerHistory, ...],
    hazard: float,
    integration: ArrivalIntegration,
    config: Goal031Config,
) -> float:
    return float(
        _neutral_log_likelihoods(
            histories,
            np.asarray((hazard,), dtype=np.float64),
            integration,
            config,
        )[0]
    )


def _likelihood_ratio_at_truth(profile: LikelihoodProfile, truth: float) -> float:
    indices = np.flatnonzero(np.isclose(profile.candidates, truth, rtol=0.0, atol=1e-12))
    if len(indices) != 1:
        raise ValueError("truth must occur once on the likelihood grid")
    return max(
        0.0,
        2.0 * (profile.maximum_log_likelihood - float(profile.log_likelihoods[int(indices[0])])),
    )


def _summarize_support(
    profile: LikelihoodProfile, cutoff: float, truth: float
) -> tuple[bool, int, bool, bool, float, float]:
    mask = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods) <= cutoff
    indices = np.flatnonzero(mask)
    if len(indices) == 0:
        raise RuntimeError("likelihood support must not be empty")
    truth_indices = np.flatnonzero(np.isclose(profile.candidates, truth, rtol=0.0, atol=1e-12))
    if len(truth_indices) != 1:
        raise ValueError("truth must occur once on the likelihood grid")
    components = int(mask[0]) + int(np.sum(mask[1:] & ~mask[:-1]))
    return (
        bool(mask[int(truth_indices[0])]),
        components,
        bool(mask[0] or mask[-1]),
        bool(not mask[0]),
        float(profile.candidates[int(indices[0])]),
        float(profile.candidates[int(indices[-1])]),
    )


def _histories_valid(histories: tuple[CrossLayerHistory, ...], config: Goal031Config) -> bool:
    if len(histories) != 160:
        return False
    if sum(row.split == "training" for row in histories) != 120:
        return False
    if sum(row.split == "holdout" for row in histories) != 40:
        return False
    if len({row.site_index for row in histories}) != 160:
        return False
    for row in histories:
        if not (
            math.isfinite(row.true_predator_arrival)
            and math.isfinite(row.true_prey_extirpation)
            and len(row.predator_detection_counts) == len(SURVEY_TIMES)
            and len(row.prey_detection_counts) == len(SURVEY_TIMES)
            and row.true_predator_present
            == tuple(row.true_predator_arrival <= time for time in SURVEY_TIMES)
            and row.true_prey_alive
            == tuple(row.true_prey_extirpation > time for time in SURVEY_TIMES)
        ):
            return False
        if not all(
            0 <= count <= config.visits_per_survey
            for count in (*row.predator_detection_counts, *row.prey_detection_counts)
        ):
            return False
        if any(
            count
            for count, present in zip(
                row.predator_detection_counts, row.true_predator_present, strict=True
            )
            if not present
        ):
            return False
        if any(
            count
            for count, alive in zip(row.prey_detection_counts, row.true_prey_alive, strict=True)
            if not alive
        ):
            return False
    return True


def _detected_visit_count(histories: tuple[CrossLayerHistory, ...], *, predator: bool) -> int:
    if predator:
        return sum(sum(row.predator_detection_counts) for row in histories)
    return sum(sum(row.prey_detection_counts) for row in histories)


def _flatten_histories(
    histories: tuple[CrossLayerHistory, ...],
) -> tuple[SurveyHistoryRow, ...]:
    return tuple(
        SurveyHistoryRow(
            history.site_id,
            history.split,
            history.row,
            history.col,
            survey_time,
            history.true_predator_arrival,
            predator_present,
            predator_count,
            history.true_prey_extirpation,
            prey_alive,
            prey_count,
        )
        for history in histories
        for survey_time, predator_present, predator_count, prey_alive, prey_count in zip(
            SURVEY_TIMES,
            history.true_predator_present,
            history.predator_detection_counts,
            history.true_prey_alive,
            history.prey_detection_counts,
            strict=True,
        )
    )


def _arrival_conditioning(
    histories: tuple[CrossLayerHistory, ...],
    integration: ArrivalIntegration,
    config: Goal031Config,
) -> tuple[ArrivalConditioningRow, ...]:
    predator_probabilities = _predator_category_probabilities(histories, config)
    rows: list[ArrivalConditioningRow] = []
    pseudo_values = np.asarray(PSEUDO_ARRIVALS, dtype=np.float64)
    for history_index, history in enumerate(histories):
        arrivals = integration.bank_arrivals[:, history.site_index]
        categories = np.searchsorted(np.asarray(SURVEY_TIMES), arrivals, side="left")
        values = np.concatenate((arrivals, pseudo_values))
        base_weights = np.concatenate(
            (np.ones(len(arrivals), dtype=np.float64), np.full(CATEGORY_COUNT, 0.5))
        )
        likelihood = np.concatenate(
            (
                predator_probabilities[history_index, categories],
                predator_probabilities[history_index],
            )
        )
        posterior_weights = base_weights * likelihood
        if posterior_weights.sum() <= 0.0:
            raise RuntimeError("predator history has no arrival-bank support")
        prior_mean = float(np.average(values, weights=base_weights))
        conditioned_mean = float(np.average(values, weights=posterior_weights))
        first_detection = next(
            (
                survey_time
                for survey_time, count in zip(
                    SURVEY_TIMES, history.predator_detection_counts, strict=True
                )
                if count > 0
            ),
            None,
        )
        rows.append(
            ArrivalConditioningRow(
                history.site_id,
                history.split,
                history.row,
                history.col,
                sum(history.predator_detection_counts),
                first_detection,
                history.true_predator_arrival,
                prior_mean,
                conditioned_mean,
                _weighted_quantile(values, posterior_weights, 0.10),
                _weighted_quantile(values, posterior_weights, 0.90),
                abs(prior_mean - history.true_predator_arrival),
                abs(conditioned_mean - history.true_predator_arrival),
            )
        )
    return tuple(rows)


def _weighted_quantile(
    values: NDArray[np.float64], weights: NDArray[np.float64], probability: float
) -> float:
    if not 0.0 <= probability <= 1.0:
        raise ValueError("quantile probability must lie between zero and one")
    order = np.argsort(values)
    sorted_values = values[order]
    cumulative = np.cumsum(weights[order])
    target = probability * cumulative[-1]
    index = min(int(np.searchsorted(cumulative, target, side="left")), len(values) - 1)
    return float(sorted_values[index])


CsvRow = (
    CalibrationStatistic
    | ValidationResult
    | SurveyHistoryRow
    | ArrivalConditioningRow
    | BenchmarkComparison
)


def _write_dataclass_csv(path: Path, rows: tuple[CsvRow, ...]) -> None:
    if not rows:
        raise ValueError("CSV rows must not be empty")
    payload = [asdict(row) for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]))
        writer.writeheader()
        writer.writerows(payload)


def _summary_payload(result: Goal031Result) -> dict[str, object]:
    summary = result.summary
    conditioning = result.arrival_conditioning
    return {
        "goal": "031-latent-arrival-prey-effect-positive-control",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "outcome": result.outcome,
        "scientific_interpretation": result.outcome,
        "model": {
            "known_spread_rate": 1.0,
            "known_resistance_contrast": 1.0,
            "background_hazard": result.config.background_hazard,
            "truth_hazard_ratio": result.config.truth_hazard_ratio,
            "estimated_parameters": ["post_arrival_prey_hazard_ratio"],
            "survey_times": SURVEY_TIMES,
            "visits_per_survey": result.config.visits_per_survey,
            "known_predator_detection_probability": result.config.predator_detection_probability,
            "known_prey_detection_probability": result.config.prey_detection_probability,
            "false_positive_probability": 0.0,
            "arrival_inference": (
                "shared within-site predator/prey arrival draw; site-marginal composite "
                "likelihood across sites"
            ),
            "neutral_model": (
                "fitted constant prey-extirpation hazard with identical predator and prey "
                "observation processes"
            ),
        },
        "integration_bank": {
            "draws": result.config.bank_size,
            "arrival_categories": CATEGORY_COUNT,
            "jeffreys_pseudoweight_per_category": 0.5,
            "checksum_sha256": result.integration.bank_checksum,
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
            "no_effect_exclusion_count": summary.null_exclusion_count,
            "median_absolute_log_error": summary.median_absolute_log_error,
            "median_log_support_width": summary.median_log_support_width,
            "heldout_log_score_advantage": asdict(summary.heldout_log_score_advantage),
        },
        "representative_arrival_conditioning": {
            "median_prior_absolute_error": median(row.prior_absolute_error for row in conditioning),
            "median_conditioned_absolute_error": median(
                row.conditioned_absolute_error for row in conditioning
            ),
            "sites_improved_by_conditioning": sum(
                row.conditioned_absolute_error < row.prior_absolute_error for row in conditioning
            ),
            "sites_with_predator_detection": sum(
                row.predator_detection_total > 0 for row in conditioning
            ),
        },
        "known_arrival_anchor": asdict(result.known_arrival_anchor),
        "failed_gates": _failed_gates(result),
        "invariants": result.invariants,
    }


def _failed_gates(result: Goal031Result) -> tuple[str, ...]:
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
    if summary.null_exclusion_count < required_count:
        failed.append("no_effect_exclusion")
    if summary.median_absolute_log_error > 0.20:
        failed.append("point_recovery")
    if summary.median_log_support_width > 0.80:
        failed.append("support_precision")
    if summary.heldout_log_score_advantage.lower <= 0.0:
        failed.append("heldout_prediction")
    return tuple(failed)


def _review(result: Goal031Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 031: Latent Arrival and Prey Effect\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    summary = result.summary
    failed = _failed_gates(result)
    if result.outcome == RECOVERED:
        interpretation = (
            "Direct predator detections carried enough timing information for the fivefold prey "
            "effect to remain calibrated, precise, distinguishable from no effect, and more "
            "predictive than the neutral prey model even though realized arrival was hidden."
        )
    else:
        interpretation = (
            "Hiding the realized predator-arrival map removed enough information that the prey "
            "effect did not pass every prespecified one-parameter recovery gate. This is a valid "
            f"information-loss result. Failed gates: {', '.join(failed)}."
        )
    comparison_rows = [
        (
            f"| {row.arrival_information} | {row.coverage:.3f} | "
            f"{row.no_effect_exclusion_count}/{row.validation_replicates} | "
            f"{row.median_absolute_log_effect_error:.3f} | "
            f"{row.median_log_effect_support_width:.3f} | {row.score_advantage:.4f} | "
            f"{'yes' if row.recovered else 'no'} |"
        )
        for row in result.comparison
    ]
    conditioning = result.arrival_conditioning
    return "\n".join(
        [
            "# Goal 031: Latent Arrival and Prey Effect",
            "",
            f"Outcome: `{result.outcome}`.",
            "",
            "## Question",
            "",
            (
                "Can direct imperfect predator detections replace the exact realized arrival map "
                "well enough to recover one prey-effect parameter?"
            ),
            "",
            "## Result",
            "",
            interpretation,
            "",
            (
                "| Arrival information | Coverage | No effect excluded | Median log error | "
                "Median support width | Held-out advantage | Recovered |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|",
            *comparison_rows,
            "",
            "## What the predator data contributed",
            "",
            (
                f"In the representative validation dataset, predator detections occurred at "
                f"{sum(row.predator_detection_total > 0 for row in conditioning)}/160 sites. "
                f"Conditioning on those histories reduced median absolute arrival error from "
                f"{median(row.prior_absolute_error for row in conditioning):.2f} to "
                f"{median(row.conditioned_absolute_error for row in conditioning):.2f} time "
                "units. This diagnostic uses predator data only."
            ),
            "",
            "## Boundary",
            "",
            (
                "Spread rate, resistance, both detection probabilities, background hazard, and "
                "false-positive rates were known. Only the prey-effect multiplier was fitted. "
                "Predator and prey histories shared an arrival draw within site, but dependence "
                "among sites from the common spread field was deliberately omitted."
            ),
            "",
            "## Decision",
            "",
            (
                f"Coverage was {summary.coverage.estimate:.3f}; median log-effect error was "
                f"{summary.median_absolute_log_error:.3f}; median support width was "
                f"{summary.median_log_support_width:.3f}; and held-out advantage was "
                f"{summary.heldout_log_score_advantage.estimate:.4f}."
            ),
            "",
        ]
    )


def _review_figure(result: Goal031Result) -> Figure:
    comparisons = result.comparison
    labels = ("Exact arrival", "Latent arrival")
    colors = ("#6B7280", "#1B7F79")
    figure, axes = plt.subplots(2, 3, figsize=(13.2, 8.0), constrained_layout=True)
    conditioned = result.arrival_conditioning
    ax = axes[0, 0]
    true = np.asarray([row.true_arrival for row in conditioned])
    prior = np.asarray([row.prior_arrival_mean for row in conditioned])
    posterior = np.asarray([row.conditioned_arrival_mean for row in conditioned])
    ax.scatter(true, prior, s=15, alpha=0.35, color="#9CA3AF", label="Process prior")
    ax.scatter(true, posterior, s=18, alpha=0.7, color="#1B7F79", label="After predator data")
    limits = (0.0, max(float(true.max()), float(prior.max()), float(posterior.max())) * 1.03)
    ax.plot(limits, limits, linestyle="--", color="#111827", linewidth=1)
    ax.set(xlabel="True arrival", ylabel="Estimated mean arrival", title="Arrival diagnostic")
    ax.legend(frameon=False, fontsize=8)

    def bars(
        axis: Axes,
        values: Sequence[float],
        title: str,
        ylabel: str,
        gate: float | None = None,
    ) -> None:
        axis.bar(labels, values, color=colors, width=0.62)
        axis.set(title=title, ylabel=ylabel)
        axis.tick_params(axis="x", rotation=12)
        if gate is not None:
            axis.axhline(gate, linestyle="--", color="#B91C1C", linewidth=1)

    ax = axes[0, 1]
    coverage = tuple(row.coverage for row in comparisons)
    lower = tuple(row.coverage - row.coverage_lower for row in comparisons)
    upper = tuple(row.coverage_upper - row.coverage for row in comparisons)
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
    ax.set(title="Calibrated support coverage", ylabel="Proportion", ylim=(0.88, 1.0))
    ax.tick_params(axis="x", rotation=12)

    bars(
        axes[0, 2],
        tuple(row.no_effect_exclusion_count / row.validation_replicates for row in comparisons),
        "No-effect exclusion",
        "Proportion",
        0.95,
    )
    bars(
        axes[1, 0],
        tuple(row.median_absolute_log_effect_error for row in comparisons),
        "Point recovery",
        "Median absolute log error",
        0.20,
    )
    bars(
        axes[1, 1],
        tuple(row.median_log_effect_support_width for row in comparisons),
        "Effect precision",
        "Median log-support width",
        0.80,
    )
    ax = axes[1, 2]
    advantages = tuple(row.score_advantage for row in comparisons)
    lower = tuple(row.score_advantage - row.score_advantage_lower for row in comparisons)
    upper = tuple(row.score_advantage_upper - row.score_advantage for row in comparisons)
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
    ax.tick_params(axis="x", rotation=12)
    figure.suptitle(
        "Goal 031: cost of hiding the realized predator-arrival map",
        fontsize=15,
        fontweight="bold",
    )
    return figure


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
