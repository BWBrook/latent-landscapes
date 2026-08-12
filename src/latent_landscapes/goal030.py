"""Joint prey-effect and detection-probability positive control."""

from __future__ import annotations

import csv
import json
import math
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import cast

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from numpy.typing import NDArray

from latent_landscapes.goal002.calibration import (
    EstimateInterval,
    normal_mean_interval,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal026 import (
    BACKGROUND_HAZARD,
    HAZARD_RATIO_GRID,
    NEUTRAL_HAZARD_GRID,
    SURVEY_TIMES,
)
from latent_landscapes.goal029 import (
    PREY_DETECTION_PROBABILITY,
    DatasetSeed,
    DetectionHistory,
    Goal029Config,
    SurveyObservation,
    _flatten_observations,
    _histories_valid,
    generate_detection_dataset,
    spawn_seed_manifest,
)

MASTER_SEED = 20260812030
TRUTH_HAZARD_RATIO = 5.0
DETECTION_PROBABILITY_GRID = tuple(float(value) for value in np.linspace(0.35, 0.90, 23))
DEFAULT_GOAL029_EVIDENCE_DIR = Path(
    "artifacts/goal029_known_arrival_known_imperfect_prey_detection"
)
JOINT_RECOVERED = "joint_prey_effect_detection_recovered"
EXPECTED_FILES = (
    "calibration_statistics.csv",
    "validation_results.csv",
    "representative_prey_observations.csv",
    "representative_joint_likelihood.csv",
    "benchmark_comparison.csv",
    "summary.json",
    "review.md",
    "joint_prey_effect_detection.svg",
)


@dataclass(frozen=True, slots=True)
class Goal030Config:
    """Frozen two-parameter positive control."""

    master_seed: int = MASTER_SEED
    calibration_replicates: int = 2_000
    validation_replicates: int = 1_000
    calibration_rank_one_based: int = 1_901
    background_hazard: float = BACKGROUND_HAZARD
    truth_hazard_ratio: float = TRUTH_HAZARD_RATIO
    truth_detection_probability: float = PREY_DETECTION_PROBABILITY
    visits_per_survey: int = 2
    hazard_ratios: tuple[float, ...] = HAZARD_RATIO_GRID
    detection_probabilities: tuple[float, ...] = DETECTION_PROBABILITY_GRID
    neutral_hazards: tuple[float, ...] = NEUTRAL_HAZARD_GRID

    def __post_init__(self) -> None:
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within calibration replicates")
        if self.visits_per_survey != 2:
            raise ValueError("Goal 030 requires exactly two visits per survey")
        if self.background_hazard <= 0.0:
            raise ValueError("background hazard must be positive")
        if sum(math.isclose(value, self.truth_hazard_ratio) for value in self.hazard_ratios) != 1:
            raise ValueError("effect truth must occur once on its grid")
        if (
            sum(
                math.isclose(value, self.truth_detection_probability)
                for value in self.detection_probabilities
            )
            != 1
        ):
            raise ValueError("detection truth must occur once on its grid")
        if not self.hazard_ratios or self.hazard_ratios[0] != 1.0:
            raise ValueError("effect grid must begin at no effect")
        if any(value <= 0.0 for value in (*self.hazard_ratios, *self.neutral_hazards)):
            raise ValueError("hazards must be positive")
        if any(not 0.0 < value < 1.0 for value in self.detection_probabilities):
            raise ValueError("detection candidates must lie strictly between zero and one")

    @property
    def is_production(self) -> bool:
        return self == Goal030Config()

    @property
    def generation_config(self) -> Goal029Config:
        return Goal029Config(
            master_seed=self.master_seed,
            calibration_replicates=self.calibration_replicates,
            validation_replicates=self.validation_replicates,
            calibration_rank_one_based=self.calibration_rank_one_based,
            background_hazard=self.background_hazard,
            truth_hazard_ratio=self.truth_hazard_ratio,
            detection_probability=self.truth_detection_probability,
            visits_per_survey=self.visits_per_survey,
            hazard_ratios=self.hazard_ratios,
            neutral_hazards=self.neutral_hazards,
        )


DEFAULT_CONFIG = Goal030Config()


def smoke_config() -> Goal030Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal030Config(
        calibration_replicates=6,
        validation_replicates=6,
        calibration_rank_one_based=6,
        hazard_ratios=(1.0, 3.0, 5.0, 7.0, 9.0),
        detection_probabilities=(0.40, 0.55, 0.65, 0.75, 0.90),
        neutral_hazards=(0.0005, 0.001, 0.002, 0.004, 0.008, 0.016, 0.032),
    )


@dataclass(frozen=True, slots=True)
class KnownDetectionAnchor:
    calibration_replicates: int
    validation_replicates: int
    coverage_count: int
    coverage: float
    coverage_lower: float
    coverage_upper: float
    connected_interior_count: int
    null_exclusion_count: int
    median_absolute_log_effect_error: float
    median_log_effect_support_width: float
    score_advantage: float
    score_advantage_lower: float
    score_advantage_upper: float


@dataclass(frozen=True, slots=True)
class JointLikelihoodProfile:
    process_candidates: NDArray[np.float64]
    detection_candidates: NDArray[np.float64]
    log_likelihoods: NDArray[np.float64]
    maximum_log_likelihood: float
    mle_process: float
    mle_detection_probability: float


@dataclass(frozen=True, slots=True)
class JointSupport:
    truth_included: bool
    component_count: int
    boundary_contact: bool
    no_effect_excluded: bool
    effect_lower: float
    effect_upper: float
    detection_lower: float
    detection_upper: float


@dataclass(frozen=True, slots=True)
class CalibrationStatistic:
    dataset_index: int
    likelihood_ratio_at_truth: float
    detected_visit_count: int
    detected_site_count: int


@dataclass(frozen=True, slots=True)
class ValidationResult:
    dataset_index: int
    detected_visit_count: int
    detected_site_count: int
    truth_included: bool
    support_component_count: int
    support_boundary_contact: bool
    no_effect_excluded: bool
    mle_hazard_ratio: float
    mle_detection_probability: float
    absolute_log_effect_error: float
    absolute_detection_probability_error: float
    effect_support_lower: float
    effect_support_upper: float
    log_effect_support_width: float
    detection_support_lower: float
    detection_support_upper: float
    detection_support_width: float
    fitted_neutral_hazard: float
    fitted_neutral_detection_probability: float
    heldout_predator_log_score: float
    heldout_neutral_log_score: float
    heldout_log_score_advantage: float


@dataclass(frozen=True, slots=True)
class JointRecoverySummary:
    cutoff: float
    coverage_count: int
    coverage: EstimateInterval
    connected_interior_count: int
    no_effect_exclusion_count: int
    median_absolute_log_effect_error: float
    median_log_effect_support_width: float
    median_absolute_detection_probability_error: float
    median_detection_probability_support_width: float
    heldout_log_score_advantage: EstimateInterval


@dataclass(frozen=True, slots=True)
class LikelihoodSurfacePoint:
    hazard_ratio: float
    detection_probability: float
    likelihood_ratio: float
    within_support: bool
    is_truth: bool
    is_mle: bool


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
    median_absolute_log_effect_error: float
    median_log_effect_support_width: float
    median_absolute_detection_probability_error: float | None
    median_detection_probability_support_width: float | None
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
    profile: JointLikelihoodProfile | None
    observations: tuple[SurveyObservation, ...]
    valid_histories: bool
    finite_likelihood: bool


@dataclass(frozen=True, slots=True)
class Goal030Result:
    config: Goal030Config
    known_detection_anchor: KnownDetectionAnchor
    calibration_statistics: tuple[CalibrationStatistic, ...]
    validation_results: tuple[ValidationResult, ...]
    representative_observations: tuple[SurveyObservation, ...]
    representative_surface: tuple[LikelihoodSurfacePoint, ...]
    summary: JointRecoverySummary
    invariants: dict[str, bool]
    outcome: str

    @property
    def comparison(self) -> tuple[BenchmarkComparison, BenchmarkComparison]:
        anchor = self.known_detection_anchor
        current = self.summary
        return (
            BenchmarkComparison(
                "known_detection_probability_goal029",
                anchor.calibration_replicates,
                anchor.validation_replicates,
                anchor.coverage,
                anchor.coverage_lower,
                anchor.coverage_upper,
                anchor.connected_interior_count,
                anchor.null_exclusion_count,
                anchor.median_absolute_log_effect_error,
                anchor.median_log_effect_support_width,
                None,
                None,
                anchor.score_advantage,
                anchor.score_advantage_lower,
                anchor.score_advantage_upper,
                True,
            ),
            BenchmarkComparison(
                "joint_effect_and_detection_goal030",
                self.config.calibration_replicates,
                self.config.validation_replicates,
                current.coverage.estimate,
                current.coverage.lower,
                current.coverage.upper,
                current.connected_interior_count,
                current.no_effect_exclusion_count,
                current.median_absolute_log_effect_error,
                current.median_log_effect_support_width,
                current.median_absolute_detection_probability_error,
                current.median_detection_probability_support_width,
                current.heldout_log_score_advantage.estimate,
                current.heldout_log_score_advantage.lower,
                current.heldout_log_score_advantage.upper,
                self.outcome == JOINT_RECOVERED,
            ),
        )


def load_goal029_anchor(evidence_dir: Path) -> KnownDetectionAnchor:
    """Load and exactly reconcile the accepted known-detection benchmark."""
    payload = cast(
        dict[str, object],
        json.loads((Path(evidence_dir) / "summary.json").read_text(encoding="utf-8")),
    )
    calibration = cast(dict[str, object], payload.get("calibration"))
    validation = cast(dict[str, object], payload.get("validation"))
    coverage = cast(dict[str, object], validation.get("coverage"))
    score = cast(dict[str, object], validation.get("heldout_log_score_advantage"))
    anchor = KnownDetectionAnchor(
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
    if not (
        payload.get("goal") == "029-known-arrival-known-imperfect-prey-detection"
        and payload.get("run_mode") == "production"
        and payload.get("outcome") == "known_imperfect_prey_detection_recovered"
        and anchor.calibration_replicates == 2_000
        and anchor.validation_replicates == 1_000
        and anchor.coverage_count == 956
        and anchor.connected_interior_count == 994
        and anchor.null_exclusion_count == 1_000
        and anchor.score_advantage_lower > 0.0
    ):
        raise ValueError("published Goal 029 evidence changed")
    return anchor


def joint_profile(
    histories: tuple[DetectionHistory, ...],
    process_candidates: tuple[float, ...],
    detection_candidates: tuple[float, ...],
    *,
    background_hazard: float,
    use_arrival: bool,
    visits_per_survey: int = 2,
) -> JointLikelihoodProfile:
    """Profile a process parameter jointly with detection probability."""
    process = np.asarray(process_candidates, dtype=np.float64)
    detection = np.asarray(detection_candidates, dtype=np.float64)
    values = _joint_log_likelihoods(
        histories,
        process,
        detection,
        background_hazard=background_hazard,
        use_arrival=use_arrival,
        visits_per_survey=visits_per_survey,
    )
    flat_index = int(np.argmax(values))
    process_index, detection_index = np.unravel_index(flat_index, values.shape)
    return JointLikelihoodProfile(
        process,
        detection,
        values,
        float(values[process_index, detection_index]),
        float(process[process_index]),
        float(detection[detection_index]),
    )


def classify_outcome(
    *,
    invariants: dict[str, bool],
    summary: JointRecoverySummary,
    validation_count: int,
) -> str:
    """Separate common, effect, and detection recovery."""
    if not invariants or not all(invariants.values()) or validation_count <= 0:
        return "implementation_blocked"
    required_count = math.ceil(0.95 * validation_count)
    common = (
        summary.coverage.lower <= 0.95 <= summary.coverage.upper
        and summary.connected_interior_count >= required_count
        and summary.heldout_log_score_advantage.lower > 0.0
    )
    effect = (
        common
        and summary.no_effect_exclusion_count >= required_count
        and summary.median_absolute_log_effect_error <= 0.20
        and summary.median_log_effect_support_width <= 0.80
    )
    detection = (
        common
        and summary.median_absolute_detection_probability_error <= 0.05
        and summary.median_detection_probability_support_width <= 0.15
    )
    if effect and detection:
        return JOINT_RECOVERED
    if effect:
        return "prey_effect_recovered_detection_weak"
    if detection:
        return "detection_recovered_prey_effect_weak"
    return "joint_prey_effect_detection_not_recovered"


def run_goal030(
    goal029_evidence_dir: Path = DEFAULT_GOAL029_EVIDENCE_DIR,
    config: Goal030Config = DEFAULT_CONFIG,
    *,
    workers: int = 1,
) -> Goal030Result:
    """Run the calibrated joint positive control."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    anchor = load_goal029_anchor(goal029_evidence_dir)
    calibration_seeds, validation_seeds = spawn_seed_manifest(config.generation_config)
    calibration_work = _run_calibration_tasks(calibration_seeds, config, workers)
    calibration_rows = tuple(work.statistic for work in calibration_work)
    cutoff = order_statistic_cutoff(
        [row.likelihood_ratio_at_truth for row in calibration_rows],
        rank_one_based=config.calibration_rank_one_based,
    )
    validation_work = _run_validation_tasks(validation_seeds, config, cutoff.cutoff, workers)
    validation_rows = tuple(work.result for work in validation_work)
    representative_work = validation_work[0]
    if representative_work.profile is None or not representative_work.observations:
        raise RuntimeError("representative validation evidence is missing")
    representative_surface = _surface_rows(
        representative_work.profile,
        cutoff.cutoff,
        config.truth_hazard_ratio,
        config.truth_detection_probability,
    )

    coverage_count = sum(row.truth_included for row in validation_rows)
    coverage = wilson_interval(coverage_count, len(validation_rows))
    connected = sum(
        row.support_component_count == 1 and not row.support_boundary_contact
        for row in validation_rows
    )
    no_effect_exclusion = sum(row.no_effect_excluded for row in validation_rows)
    score_advantage = normal_mean_interval(
        [row.heldout_log_score_advantage for row in validation_rows]
    )
    summary = JointRecoverySummary(
        cutoff.cutoff,
        coverage_count,
        coverage,
        connected,
        no_effect_exclusion,
        median(row.absolute_log_effect_error for row in validation_rows),
        median(row.log_effect_support_width for row in validation_rows),
        median(row.absolute_detection_probability_error for row in validation_rows),
        median(row.detection_support_width for row in validation_rows),
        score_advantage,
    )
    all_seeds = (*calibration_seeds, *validation_seeds)
    invariants = {
        "goal029_anchor_reconciled": True,
        "calibration_histories_valid": all(work.valid_histories for work in calibration_work),
        "validation_histories_valid": all(work.valid_histories for work in validation_work),
        "finite_calibration_likelihoods": all(work.finite_likelihood for work in calibration_work),
        "finite_validation_likelihoods_and_scores": all(
            work.finite_likelihood for work in validation_work
        ),
        "independent_seed_streams": len(
            {(seed.process_seed, seed.prey_seed, seed.detection_seed) for seed in all_seeds}
        )
        == len(all_seeds),
        "calibration_count": len(calibration_rows) == config.calibration_replicates,
        "validation_count": len(validation_rows) == config.validation_replicates,
        "representative_observation_count": len(representative_work.observations)
        == 160 * len(SURVEY_TIMES),
        "representative_surface_count": len(representative_surface)
        == len(config.hazard_ratios) * len(config.detection_probabilities),
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
    return Goal030Result(
        config,
        anchor,
        calibration_rows,
        validation_rows,
        representative_work.observations,
        representative_surface,
        summary,
        invariants,
        outcome,
    )


def write_review_bundle(result: Goal030Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the compact eight-file Goal 030 review surface."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("output directory must be empty")
    _write_dataclass_csv(target / "calibration_statistics.csv", result.calibration_statistics)
    _write_dataclass_csv(target / "validation_results.csv", result.validation_results)
    _write_dataclass_csv(
        target / "representative_prey_observations.csv", result.representative_observations
    )
    _write_dataclass_csv(
        target / "representative_joint_likelihood.csv", result.representative_surface
    )
    _write_dataclass_csv(target / "benchmark_comparison.csv", result.comparison)
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    _save_figure(target / "joint_prey_effect_detection.svg", _review_figure(result))
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 030 review surface is incomplete")
    return written


def _run_calibration_tasks(
    seeds: tuple[DatasetSeed, ...], config: Goal030Config, workers: int
) -> tuple[CalibrationWork, ...]:
    tasks = tuple((seed, config) for seed in seeds)
    if workers == 1:
        return tuple(_calibration_worker(task) for task in tasks)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        return tuple(executor.map(_calibration_worker, tasks, chunksize=1))


def _run_validation_tasks(
    seeds: tuple[DatasetSeed, ...], config: Goal030Config, cutoff: float, workers: int
) -> tuple[ValidationWork, ...]:
    tasks = tuple((seed, config, cutoff) for seed in seeds)
    if workers == 1:
        return tuple(_validation_worker(task) for task in tasks)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        return tuple(executor.map(_validation_worker, tasks, chunksize=1))


def _calibration_worker(task: tuple[DatasetSeed, Goal030Config]) -> CalibrationWork:
    seed, config = task
    _, histories = generate_detection_dataset(seed, config.generation_config)
    profile = joint_profile(
        histories,
        config.hazard_ratios,
        config.detection_probabilities,
        background_hazard=config.background_hazard,
        use_arrival=True,
        visits_per_survey=config.visits_per_survey,
    )
    statistic = CalibrationStatistic(
        seed.index,
        _likelihood_ratio_at_truth(
            profile,
            config.truth_hazard_ratio,
            config.truth_detection_probability,
        ),
        _detected_visit_count(histories),
        _detected_site_count(histories),
    )
    return CalibrationWork(
        statistic,
        _histories_valid(histories, config.generation_config),
        bool(np.isfinite(profile.log_likelihoods).all()),
    )


def _validation_worker(
    task: tuple[DatasetSeed, Goal030Config, float],
) -> ValidationWork:
    seed, config, cutoff = task
    _, histories = generate_detection_dataset(seed, config.generation_config)
    all_profile = joint_profile(
        histories,
        config.hazard_ratios,
        config.detection_probabilities,
        background_hazard=config.background_hazard,
        use_arrival=True,
        visits_per_survey=config.visits_per_survey,
    )
    training = tuple(row for row in histories if row.split == "training")
    holdout = tuple(row for row in histories if row.split == "holdout")
    training_profile = joint_profile(
        training,
        config.hazard_ratios,
        config.detection_probabilities,
        background_hazard=config.background_hazard,
        use_arrival=True,
        visits_per_survey=config.visits_per_survey,
    )
    neutral_profile = joint_profile(
        training,
        config.neutral_hazards,
        config.detection_probabilities,
        background_hazard=1.0,
        use_arrival=False,
        visits_per_survey=config.visits_per_survey,
    )
    support = _summarize_support(
        all_profile,
        cutoff,
        config.truth_hazard_ratio,
        config.truth_detection_probability,
    )
    predator_score = _point_log_likelihood(
        holdout,
        training_profile.mle_process,
        training_profile.mle_detection_probability,
        background_hazard=config.background_hazard,
        use_arrival=True,
        visits_per_survey=config.visits_per_survey,
    ) / len(holdout)
    neutral_score = _point_log_likelihood(
        holdout,
        neutral_profile.mle_process,
        neutral_profile.mle_detection_probability,
        background_hazard=1.0,
        use_arrival=False,
        visits_per_survey=config.visits_per_survey,
    ) / len(holdout)
    result = ValidationResult(
        seed.index,
        _detected_visit_count(histories),
        _detected_site_count(histories),
        support.truth_included,
        support.component_count,
        support.boundary_contact,
        support.no_effect_excluded,
        all_profile.mle_process,
        all_profile.mle_detection_probability,
        abs(math.log(all_profile.mle_process / config.truth_hazard_ratio)),
        abs(all_profile.mle_detection_probability - config.truth_detection_probability),
        support.effect_lower,
        support.effect_upper,
        math.log(support.effect_upper / support.effect_lower),
        support.detection_lower,
        support.detection_upper,
        support.detection_upper - support.detection_lower,
        neutral_profile.mle_process,
        neutral_profile.mle_detection_probability,
        predator_score,
        neutral_score,
        predator_score - neutral_score,
    )
    finite = bool(
        np.isfinite(all_profile.log_likelihoods).all()
        and np.isfinite(training_profile.log_likelihoods).all()
        and np.isfinite(neutral_profile.log_likelihoods).all()
        and math.isfinite(predator_score)
        and math.isfinite(neutral_score)
    )
    return ValidationWork(
        result,
        all_profile if seed.index == 0 else None,
        _flatten_observations(histories) if seed.index == 0 else (),
        _histories_valid(histories, config.generation_config),
        finite,
    )


def _joint_log_likelihoods(
    histories: tuple[DetectionHistory, ...],
    process_candidates: NDArray[np.float64],
    detection_candidates: NDArray[np.float64],
    *,
    background_hazard: float,
    use_arrival: bool,
    visits_per_survey: int,
) -> NDArray[np.float64]:
    if not histories:
        raise ValueError("detection histories must not be empty")
    if (
        process_candidates.ndim != 1
        or detection_candidates.ndim != 1
        or not np.isfinite(process_candidates).all()
        or not np.isfinite(detection_candidates).all()
        or np.any(process_candidates <= 0.0)
        or np.any((detection_candidates <= 0.0) | (detection_candidates >= 1.0))
        or not math.isfinite(background_hazard)
        or background_hazard <= 0.0
        or visits_per_survey <= 0
    ):
        raise ValueError("joint likelihood inputs must be finite and valid")
    arrivals = np.asarray([row.predator_arrival_time for row in histories], dtype=np.float64)
    counts = np.asarray([row.detection_counts for row in histories], dtype=np.int64)
    shape = (len(process_candidates), len(detection_candidates), len(histories))
    alive_probability = np.ones(shape, dtype=np.float64)
    dead_probability = np.zeros(shape, dtype=np.float64)
    previous_time = 0.0
    for survey_index, survey_time in enumerate(SURVEY_TIMES):
        if use_arrival:
            pre_duration = np.minimum(survey_time, arrivals) - np.minimum(previous_time, arrivals)
            post_duration = np.maximum(survey_time - arrivals, 0.0) - np.maximum(
                previous_time - arrivals, 0.0
            )
            increment = background_hazard * (
                pre_duration[None, :] + process_candidates[:, None] * post_duration[None, :]
            )
        else:
            increment = process_candidates[:, None] * (survey_time - previous_time)
        survival = np.exp(-increment)[:, None, :]
        predicted_alive = alive_probability * survival
        predicted_dead = dead_probability + alive_probability * (1.0 - survival)
        survey_counts = counts[:, survey_index]
        probabilities = detection_candidates[:, None]
        alive_emission = (
            np.asarray(
                [math.comb(visits_per_survey, int(count)) for count in survey_counts],
                dtype=np.float64,
            )[None, :]
            * probabilities ** survey_counts[None, :]
            * (1.0 - probabilities) ** (visits_per_survey - survey_counts[None, :])
        )
        dead_emission = (survey_counts == 0).astype(np.float64)[None, None, :]
        alive_probability = predicted_alive * alive_emission[None, :, :]
        dead_probability = predicted_dead * dead_emission
        previous_time = survey_time
    site_probability = alive_probability + dead_probability
    if np.any(site_probability <= 0.0) or not np.isfinite(site_probability).all():
        raise RuntimeError("joint likelihood produced invalid site probabilities")
    return np.log(site_probability).sum(axis=2)


def _point_log_likelihood(
    histories: tuple[DetectionHistory, ...],
    process: float,
    detection_probability: float,
    *,
    background_hazard: float,
    use_arrival: bool,
    visits_per_survey: int,
) -> float:
    values = _joint_log_likelihoods(
        histories,
        np.asarray((process,), dtype=np.float64),
        np.asarray((detection_probability,), dtype=np.float64),
        background_hazard=background_hazard,
        use_arrival=use_arrival,
        visits_per_survey=visits_per_survey,
    )
    return float(values[0, 0])


def _likelihood_ratio_at_truth(
    profile: JointLikelihoodProfile, truth_process: float, truth_detection: float
) -> float:
    process_index = np.flatnonzero(
        np.isclose(profile.process_candidates, truth_process, rtol=0.0, atol=1e-12)
    )
    detection_index = np.flatnonzero(
        np.isclose(profile.detection_candidates, truth_detection, rtol=0.0, atol=1e-12)
    )
    if len(process_index) != 1 or len(detection_index) != 1:
        raise ValueError("joint truth must occur once on both grids")
    statistic = 2.0 * (
        profile.maximum_log_likelihood
        - float(profile.log_likelihoods[int(process_index[0]), int(detection_index[0])])
    )
    return max(0.0, statistic)


def _summarize_support(
    profile: JointLikelihoodProfile,
    cutoff: float,
    truth_process: float,
    truth_detection: float,
) -> JointSupport:
    mask = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods) <= cutoff
    if not mask.any():
        raise RuntimeError("joint support must not be empty")
    process_truth_index = np.flatnonzero(
        np.isclose(profile.process_candidates, truth_process, rtol=0.0, atol=1e-12)
    )
    detection_truth_index = np.flatnonzero(
        np.isclose(profile.detection_candidates, truth_detection, rtol=0.0, atol=1e-12)
    )
    if len(process_truth_index) != 1 or len(detection_truth_index) != 1:
        raise ValueError("joint truth must occur once on both grids")
    component_count = _component_count(mask)
    boundary_contact = bool(
        mask[0, :].any() or mask[-1, :].any() or mask[:, 0].any() or mask[:, -1].any()
    )
    process_indices = np.flatnonzero(mask.any(axis=1))
    detection_indices = np.flatnonzero(mask.any(axis=0))
    return JointSupport(
        bool(mask[int(process_truth_index[0]), int(detection_truth_index[0])]),
        component_count,
        boundary_contact,
        bool(not mask[0, :].any()),
        float(profile.process_candidates[int(process_indices[0])]),
        float(profile.process_candidates[int(process_indices[-1])]),
        float(profile.detection_candidates[int(detection_indices[0])]),
        float(profile.detection_candidates[int(detection_indices[-1])]),
    )


def _component_count(mask: NDArray[np.bool]) -> int:
    """Count four-neighbour components in a small two-dimensional support mask."""
    visited = np.zeros_like(mask, dtype=np.bool)
    components = 0
    rows, cols = mask.shape
    for row in range(rows):
        for col in range(cols):
            if not mask[row, col] or visited[row, col]:
                continue
            components += 1
            stack = [(row, col)]
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
                        0 <= next_row < rows
                        and 0 <= next_col < cols
                        and mask[next_row, next_col]
                        and not visited[next_row, next_col]
                    ):
                        visited[next_row, next_col] = True
                        stack.append((next_row, next_col))
    return components


def _surface_rows(
    profile: JointLikelihoodProfile,
    cutoff: float,
    truth_process: float,
    truth_detection: float,
) -> tuple[LikelihoodSurfacePoint, ...]:
    likelihood_ratio = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
    return tuple(
        LikelihoodSurfacePoint(
            float(process),
            float(detection),
            float(likelihood_ratio[process_index, detection_index]),
            bool(likelihood_ratio[process_index, detection_index] <= cutoff),
            bool(
                math.isclose(process, truth_process, rel_tol=0.0, abs_tol=1e-12)
                and math.isclose(detection, truth_detection, rel_tol=0.0, abs_tol=1e-12)
            ),
            bool(
                math.isclose(process, profile.mle_process, rel_tol=0.0, abs_tol=1e-12)
                and math.isclose(
                    detection,
                    profile.mle_detection_probability,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            ),
        )
        for process_index, process in enumerate(profile.process_candidates)
        for detection_index, detection in enumerate(profile.detection_candidates)
    )


def _detected_visit_count(histories: tuple[DetectionHistory, ...]) -> int:
    return sum(sum(row.detection_counts) for row in histories)


def _detected_site_count(histories: tuple[DetectionHistory, ...]) -> int:
    return sum(any(row.detection_counts) for row in histories)


CsvRow = (
    CalibrationStatistic
    | ValidationResult
    | SurveyObservation
    | LikelihoodSurfacePoint
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


def _summary_payload(result: Goal030Result) -> dict[str, object]:
    summary = result.summary
    return {
        "goal": "030-joint-prey-effect-detection-positive-control",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "outcome": result.outcome,
        "scientific_interpretation": result.outcome,
        "truth": {
            "hazard_ratio": result.config.truth_hazard_ratio,
            "detection_probability": result.config.truth_detection_probability,
            "background_hazard": result.config.background_hazard,
            "visits_per_survey": result.config.visits_per_survey,
            "survey_times": SURVEY_TIMES,
            "predator_arrival": "known realized central stochastic truth",
        },
        "fitted_model": {
            "parameters": ["post_arrival_hazard_ratio", "detection_probability"],
            "neutral_parameters": ["constant_extirpation_hazard", "detection_probability"],
            "latent_state_likelihood": "absorbing alive-dead process marginalized exactly",
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
            "median_absolute_log_effect_error": summary.median_absolute_log_effect_error,
            "median_log_effect_support_width": summary.median_log_effect_support_width,
            "median_absolute_detection_probability_error": (
                summary.median_absolute_detection_probability_error
            ),
            "median_detection_probability_support_width": (
                summary.median_detection_probability_support_width
            ),
            "heldout_log_score_advantage": asdict(summary.heldout_log_score_advantage),
        },
        "known_detection_anchor": asdict(result.known_detection_anchor),
        "failed_gates": _failed_gates(result),
        "invariants": result.invariants,
    }


def _failed_gates(result: Goal030Result) -> tuple[str, ...]:
    if not result.config.is_production:
        return ()
    summary = result.summary
    required = math.ceil(0.95 * result.config.validation_replicates)
    failed: list[str] = []
    if not all(result.invariants.values()):
        failed.append("implementation_invariants")
    if not summary.coverage.lower <= 0.95 <= summary.coverage.upper:
        failed.append("joint_calibrated_coverage")
    if summary.connected_interior_count < required:
        failed.append("joint_connected_interior_support")
    if summary.no_effect_exclusion_count < required:
        failed.append("no_effect_exclusion")
    if summary.median_absolute_log_effect_error > 0.20:
        failed.append("effect_point_recovery")
    if summary.median_log_effect_support_width > 0.80:
        failed.append("effect_support_precision")
    if summary.median_absolute_detection_probability_error > 0.05:
        failed.append("detection_point_recovery")
    if summary.median_detection_probability_support_width > 0.15:
        failed.append("detection_support_precision")
    if summary.heldout_log_score_advantage.lower <= 0.0:
        failed.append("heldout_prediction")
    return tuple(failed)


def _review(result: Goal030Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 030: Joint Prey Effect and Detection\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    if result.outcome == JOINT_RECOVERED:
        interpretation = (
            "Repeated visits separated missed prey detection from predator-driven prey loss: "
            "the effect and detection probability both passed their prespecified recovery gates."
        )
    else:
        interpretation = (
            "The two-parameter model did not satisfy every prespecified joint recovery gate. "
            f"Failed gates: {', '.join(_failed_gates(result))}."
        )
    rows: list[str] = []
    for row in result.comparison:
        detection_error = (
            "n/a"
            if row.median_absolute_detection_probability_error is None
            else f"{row.median_absolute_detection_probability_error:.3f}"
        )
        detection_width = (
            "n/a"
            if row.median_detection_probability_support_width is None
            else f"{row.median_detection_probability_support_width:.3f}"
        )
        rows.append(
            f"| {row.estimation_case} | {row.coverage:.3f} | "
            f"{row.no_effect_exclusion_count}/{row.validation_replicates} | "
            f"{row.median_absolute_log_effect_error:.3f} | "
            f"{row.median_log_effect_support_width:.3f} | {detection_error} | "
            f"{detection_width} | {row.score_advantage:.4f} | "
            f"{'yes' if row.recovered else 'no'} |"
        )
    median_detection = median(row.mle_detection_probability for row in result.validation_results)
    return "\n".join(
        [
            "# Goal 030: Joint Prey Effect and Detection",
            "",
            f"Outcome: `{result.outcome}`.",
            "",
            "## Question",
            "",
            (
                "Predator arrival was known, but the prey-effect multiplier and per-visit "
                "detection probability were estimated jointly from two visits at each survey. "
                "The likelihood retained uncertainty about whether zero detections represented "
                "missed presence or true prey extirpation."
            ),
            "",
            "## Result",
            "",
            interpretation,
            "",
            (
                "| Estimation case | Coverage | No effect excluded | Effect error | Effect "
                "width | Detection error | Detection width | Held-out advantage | Recovered |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            *rows,
            "",
            "## Boundary",
            "",
            (
                "The result concerns one fivefold effect, one detection truth, exact predator "
                "arrival, zero false positives, and the fixed two-visit design. It does not yet "
                "address uncertain arrival or joint predator-process estimation."
            ),
            "",
            f"Median fitted detection probability: {median_detection:.3f}.",
            "",
        ]
    )


def _review_figure(result: Goal030Result) -> Figure:
    profile_rows = result.representative_surface
    process = np.asarray(sorted({row.hazard_ratio for row in profile_rows}))
    detection = np.asarray(sorted({row.detection_probability for row in profile_rows}))
    likelihood_ratio = np.asarray([row.likelihood_ratio for row in profile_rows]).reshape(
        len(process), len(detection)
    )
    comparison = result.comparison
    labels = ("Known p", "Estimated p")
    colors = ("#6B7280", "#1B7F79")
    x = np.arange(2)
    figure, axes = plt.subplots(2, 3, figsize=(12.4, 7.2), constrained_layout=True)

    surface_axis = axes[0, 0]
    clipped = np.minimum(likelihood_ratio.T, result.summary.cutoff * 2.0)
    surface = surface_axis.pcolormesh(process, detection, clipped, shading="auto", cmap="viridis_r")
    surface_axis.contour(
        process,
        detection,
        likelihood_ratio.T,
        levels=(result.summary.cutoff,),
        colors=("#FFFFFF",),
        linewidths=1.6,
    )
    truth = next(row for row in profile_rows if row.is_truth)
    mle = next(row for row in profile_rows if row.is_mle)
    surface_axis.scatter(
        truth.hazard_ratio,
        truth.detection_probability,
        marker="*",
        s=130,
        color="#DC2626",
        label="Truth",
    )
    surface_axis.scatter(
        mle.hazard_ratio,
        mle.detection_probability,
        marker="x",
        s=80,
        color="#111827",
        linewidths=2,
        label="MLE",
    )
    surface_axis.set_title("Representative joint support")
    surface_axis.set_xlabel("Prey-effect hazard ratio")
    surface_axis.set_ylabel("Detection probability")
    surface_axis.legend(frameon=False, loc="upper right")
    figure.colorbar(surface, ax=surface_axis, label="Likelihood-ratio statistic")

    coverage = [row.coverage for row in comparison]
    coverage_lower = [row.coverage - row.coverage_lower for row in comparison]
    coverage_upper = [row.coverage_upper - row.coverage for row in comparison]
    for index, (value, low, high, color) in enumerate(
        zip(coverage, coverage_lower, coverage_upper, colors, strict=True)
    ):
        axes[0, 1].errorbar(
            index,
            value,
            yerr=np.asarray(((low,), (high,))),
            fmt="o",
            color=color,
            capsize=4,
        )
    axes[0, 1].axhline(0.95, color="#B91C1C", linestyle="--", linewidth=1)
    axes[0, 1].set_title("Joint calibrated coverage")
    axes[0, 1].set_ylim(0.88, 1.0)

    effect_width = [row.median_log_effect_support_width for row in comparison]
    axes[0, 2].bar(x, effect_width, color=colors)
    axes[0, 2].axhline(0.80, color="#B91C1C", linestyle="--", linewidth=1)
    axes[0, 2].set_title("Effect support width")

    fitted_detection = np.asarray(
        [row.mle_detection_probability for row in result.validation_results]
    )
    detection_quantiles = np.quantile(fitted_detection, (0.10, 0.50, 0.90))
    axes[1, 0].errorbar(
        0,
        detection_quantiles[1],
        yerr=np.asarray(
            (
                (detection_quantiles[1] - detection_quantiles[0],),
                (detection_quantiles[2] - detection_quantiles[1],),
            )
        ),
        fmt="o",
        color=colors[1],
        capsize=5,
    )
    axes[1, 0].axhline(
        result.config.truth_detection_probability,
        color="#B91C1C",
        linestyle="--",
        linewidth=1,
    )
    axes[1, 0].set_ylim(0.58, 0.72)
    axes[1, 0].set_title("Detection estimate (10th-90th percentile)")
    axes[1, 0].set_xticks((0,), ("Estimated p",))

    detection_width = result.summary.median_detection_probability_support_width
    axes[1, 1].bar((0,), (detection_width,), color=colors[1], width=0.6)
    axes[1, 1].axhline(0.15, color="#B91C1C", linestyle="--", linewidth=1)
    axes[1, 1].set_title("Detection support width")
    axes[1, 1].set_xticks((0,), ("Estimated p",))

    advantage = [row.score_advantage for row in comparison]
    advantage_lower = [row.score_advantage - row.score_advantage_lower for row in comparison]
    advantage_upper = [row.score_advantage_upper - row.score_advantage for row in comparison]
    for index, (value, low, high, color) in enumerate(
        zip(advantage, advantage_lower, advantage_upper, colors, strict=True)
    ):
        axes[1, 2].errorbar(
            index,
            value,
            yerr=np.asarray(((low,), (high,))),
            fmt="o",
            color=color,
            capsize=4,
        )
    axes[1, 2].axhline(0.0, color="#B91C1C", linestyle="--", linewidth=1)
    axes[1, 2].set_title("Held-out advantage vs neutral")

    for axis in (axes[0, 1], axes[0, 2], axes[1, 2]):
        axis.set_xticks(x, labels)
    for axis in axes.flat:
        axis.grid(axis="y", color="#D1D5DB", linewidth=0.6, alpha=0.8)
        axis.set_axisbelow(True)
    figure.suptitle("Joint recovery of prey effect and detection probability", fontsize=14)
    return figure


def _save_figure(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", bbox_inches="tight")
    plt.close(figure)


def _int_value(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric")
    return int(value)


def _float_value(payload: dict[str, object], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{key} must be finite")
    return converted
