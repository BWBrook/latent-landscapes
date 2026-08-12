"""Known-arrival prey-effect benchmark with known imperfect detection."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from numpy.typing import NDArray

from latent_landscapes.goal002.calibration import (
    normal_mean_interval,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal006.spread import compute_paired_spreads
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
from latent_landscapes.goal028 import EffectSummary, load_goal027_anchor

MASTER_SEED = 20260811029
TRUTH_HAZARD_RATIO = 5.0
PREY_DETECTION_PROBABILITY = 0.65
VISITS_PER_SURVEY = 2
DEFAULT_GOAL027_EVIDENCE_DIR = Path(
    "artifacts/goal027_known_arrival_support_calibration_confirmation"
)
RECOVERED = "known_imperfect_prey_detection_recovered"
NOT_RECOVERED = "known_imperfect_prey_detection_not_recovered"
EXPECTED_FILES = (
    "calibration_statistics.csv",
    "validation_results.csv",
    "representative_prey_observations.csv",
    "benchmark_comparison.csv",
    "summary.json",
    "review.md",
    "known_imperfect_prey_detection.svg",
)


@dataclass(frozen=True, slots=True)
class Goal029Config:
    """Frozen known-detection positive control."""

    master_seed: int = MASTER_SEED
    calibration_replicates: int = 2_000
    validation_replicates: int = 1_000
    calibration_rank_one_based: int = 1_901
    background_hazard: float = BACKGROUND_HAZARD
    truth_hazard_ratio: float = TRUTH_HAZARD_RATIO
    detection_probability: float = PREY_DETECTION_PROBABILITY
    visits_per_survey: int = VISITS_PER_SURVEY
    hazard_ratios: tuple[float, ...] = HAZARD_RATIO_GRID
    neutral_hazards: tuple[float, ...] = NEUTRAL_HAZARD_GRID

    def __post_init__(self) -> None:
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within calibration replicates")
        if not 0.0 < self.detection_probability < 1.0:
            raise ValueError("detection probability must lie strictly between zero and one")
        if self.visits_per_survey != 2:
            raise ValueError("Goal 029 requires exactly two visits per survey")
        if self.background_hazard <= 0.0:
            raise ValueError("background hazard must be positive")
        if sum(math.isclose(value, self.truth_hazard_ratio) for value in self.hazard_ratios) != 1:
            raise ValueError("truth hazard ratio must occur once on its grid")
        if not self.hazard_ratios or self.hazard_ratios[0] != 1.0:
            raise ValueError("hazard-ratio grid must begin at no effect")
        if any(value <= 0.0 for value in (*self.hazard_ratios, *self.neutral_hazards)):
            raise ValueError("candidate hazards must be positive")

    @property
    def is_production(self) -> bool:
        return self == Goal029Config()


DEFAULT_CONFIG = Goal029Config()


def smoke_config() -> Goal029Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal029Config(
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
    prey_seed: int
    detection_seed: int


@dataclass(frozen=True, slots=True)
class DetectionHistory:
    dataset_phase: str
    dataset_index: int
    site_id: str
    cluster_id: str
    split: str
    row: int
    col: int
    predator_arrival_time: float
    true_extirpation_time: float
    detection_counts: tuple[int, ...]
    true_alive: tuple[bool, ...]


@dataclass(frozen=True, slots=True)
class SurveyObservation:
    site_id: str
    split: str
    row: int
    col: int
    predator_arrival_time: float
    true_extirpation_time: float
    survey_time: float
    true_alive: bool
    detected_visits: int


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
    null_excluded: bool
    mle_hazard_ratio: float
    absolute_log_hazard_ratio_error: float
    support_lower: float
    support_upper: float
    log_support_width: float
    fitted_neutral_hazard: float
    heldout_predator_log_score: float
    heldout_neutral_log_score: float
    heldout_log_score_advantage: float


@dataclass(frozen=True, slots=True)
class BenchmarkComparison:
    observation_model: str
    calibration_replicates: int
    validation_replicates: int
    coverage_count: int
    coverage: float
    coverage_lower: float
    coverage_upper: float
    connected_interior_count: int
    null_exclusion_count: int
    median_absolute_log_error: float
    median_log_support_width: float
    score_advantage: float
    score_advantage_lower: float
    score_advantage_upper: float
    recovered: bool


@dataclass(frozen=True, slots=True)
class Goal029Result:
    config: Goal029Config
    perfect_observation_anchor: EffectSummary
    calibration_statistics: tuple[CalibrationStatistic, ...]
    validation_results: tuple[ValidationResult, ...]
    representative_observations: tuple[SurveyObservation, ...]
    summary: RecoverySummary
    invariants: dict[str, bool]
    outcome: str

    @property
    def comparison(self) -> tuple[BenchmarkComparison, BenchmarkComparison]:
        anchor = self.perfect_observation_anchor
        current = self.summary
        return (
            BenchmarkComparison(
                "perfect_prey_observation_goal027",
                anchor.calibration_replicates,
                anchor.validation_replicates,
                anchor.coverage_count,
                anchor.coverage,
                anchor.coverage_lower,
                anchor.coverage_upper,
                anchor.connected_interior_count,
                anchor.null_exclusion_count,
                anchor.median_absolute_log_error,
                anchor.median_log_support_width,
                anchor.score_advantage,
                anchor.score_advantage_lower,
                anchor.score_advantage_upper,
                True,
            ),
            BenchmarkComparison(
                "known_imperfect_prey_detection_goal029",
                self.config.calibration_replicates,
                self.config.validation_replicates,
                current.coverage_count,
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


def spawn_seed_manifest(
    config: Goal029Config,
) -> tuple[tuple[DatasetSeed, ...], tuple[DatasetSeed, ...]]:
    """Create independent process, prey, and detection streams."""
    roots = np.random.SeedSequence(config.master_seed).spawn(6)
    calibration = _phase_seeds(
        "calibration", config.calibration_replicates, roots[0], roots[1], roots[2]
    )
    validation = _phase_seeds(
        "validation", config.validation_replicates, roots[3], roots[4], roots[5]
    )
    return calibration, validation


def generate_detection_dataset(
    seed: DatasetSeed,
    config: Goal029Config = DEFAULT_CONFIG,
) -> tuple[NDArray[np.float64], tuple[DetectionHistory, ...]]:
    """Generate one predator wave, prey process, and imperfect observations."""
    fixed = goal011.build_fixed_inputs()
    _, spread = compute_paired_spreads(
        fixed.landscape,
        rng=np.random.default_rng(seed.process_seed),
        etas=(1.0,),
        rho=1.0,
    )
    arrival = spread[0].arrival
    prey_rng = np.random.default_rng(seed.prey_seed)
    detection_rng = np.random.default_rng(seed.detection_seed)
    histories: list[DetectionHistory] = []
    for site in sorted(fixed.design.sites, key=lambda value: value.site_id):
        site_arrival = float(arrival[site.row, site.col])
        extirpation = sample_extirpation_time(
            predator_arrival=site_arrival,
            background_hazard=config.background_hazard,
            hazard_ratio=config.truth_hazard_ratio,
            exponential_threshold=float(prey_rng.exponential()),
        )
        alive = tuple(extirpation > survey_time for survey_time in SURVEY_TIMES)
        counts = tuple(
            int(
                detection_rng.binomial(
                    config.visits_per_survey,
                    config.detection_probability,
                )
            )
            if is_alive
            else 0
            for is_alive in alive
        )
        histories.append(
            DetectionHistory(
                seed.phase,
                seed.index,
                site.site_id,
                site.cluster_id,
                site.split,
                site.row,
                site.col,
                site_arrival,
                extirpation,
                counts,
                alive,
            )
        )
    return arrival, tuple(histories)


def hazard_ratio_profile(
    histories: tuple[DetectionHistory, ...],
    hazard_ratios: tuple[float, ...] = HAZARD_RATIO_GRID,
    background_hazard: float = BACKGROUND_HAZARD,
    detection_probability: float = PREY_DETECTION_PROBABILITY,
    visits_per_survey: int = VISITS_PER_SURVEY,
) -> LikelihoodProfile:
    """Profile the known-arrival hidden-state observation likelihood."""
    candidates = np.asarray(hazard_ratios, dtype=np.float64)
    values = _observation_log_likelihoods(
        histories,
        candidates,
        background_hazard=background_hazard,
        detection_probability=detection_probability,
        visits_per_survey=visits_per_survey,
        use_arrival=True,
    )
    maximum_index = int(np.argmax(values))
    return LikelihoodProfile(
        candidates, values, float(values[maximum_index]), float(candidates[maximum_index])
    )


def neutral_hazard_profile(
    histories: tuple[DetectionHistory, ...],
    hazards: tuple[float, ...] = NEUTRAL_HAZARD_GRID,
    detection_probability: float = PREY_DETECTION_PROBABILITY,
    visits_per_survey: int = VISITS_PER_SURVEY,
) -> LikelihoodProfile:
    """Profile the observation-aware constant-hazard neutral likelihood."""
    candidates = np.asarray(hazards, dtype=np.float64)
    values = _observation_log_likelihoods(
        histories,
        candidates,
        background_hazard=1.0,
        detection_probability=detection_probability,
        visits_per_survey=visits_per_survey,
        use_arrival=False,
    )
    maximum_index = int(np.argmax(values))
    return LikelihoodProfile(
        candidates, values, float(values[maximum_index]), float(candidates[maximum_index])
    )


def log_likelihood_hazard_ratio(
    histories: tuple[DetectionHistory, ...],
    hazard_ratio: float,
    config: Goal029Config,
) -> float:
    return float(
        _observation_log_likelihoods(
            histories,
            np.asarray((hazard_ratio,), dtype=np.float64),
            background_hazard=config.background_hazard,
            detection_probability=config.detection_probability,
            visits_per_survey=config.visits_per_survey,
            use_arrival=True,
        )[0]
    )


def log_likelihood_neutral(
    histories: tuple[DetectionHistory, ...],
    hazard: float,
    config: Goal029Config,
) -> float:
    return float(
        _observation_log_likelihoods(
            histories,
            np.asarray((hazard,), dtype=np.float64),
            background_hazard=1.0,
            detection_probability=config.detection_probability,
            visits_per_survey=config.visits_per_survey,
            use_arrival=False,
        )[0]
    )


def classify_outcome(
    *,
    invariants: dict[str, bool],
    summary: RecoverySummary,
    validation_count: int,
) -> str:
    """Apply the inherited Goal 027 recovery gates."""
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


def run_goal029(
    goal027_evidence_dir: Path = DEFAULT_GOAL027_EVIDENCE_DIR,
    config: Goal029Config = DEFAULT_CONFIG,
) -> Goal029Result:
    """Calibrate and validate the known-imperfect-detection benchmark."""
    anchor = load_goal027_anchor(goal027_evidence_dir)
    calibration_seeds, validation_seeds = spawn_seed_manifest(config)
    calibration_rows: list[CalibrationStatistic] = []
    valid_histories = True
    finite_likelihoods = True
    for seed in calibration_seeds:
        _, histories = generate_detection_dataset(seed, config)
        profile = hazard_ratio_profile(
            histories,
            config.hazard_ratios,
            config.background_hazard,
            config.detection_probability,
            config.visits_per_survey,
        )
        calibration_rows.append(
            CalibrationStatistic(
                seed.index,
                _likelihood_ratio_at_truth(profile, config.truth_hazard_ratio),
                _detected_visit_count(histories),
                _detected_site_count(histories),
            )
        )
        valid_histories &= _histories_valid(histories, config)
        finite_likelihoods &= bool(np.isfinite(profile.log_likelihoods).all())

    cutoff = order_statistic_cutoff(
        [row.likelihood_ratio_at_truth for row in calibration_rows],
        rank_one_based=config.calibration_rank_one_based,
    )
    validation_rows: list[ValidationResult] = []
    representative: tuple[SurveyObservation, ...] = ()
    for seed in validation_seeds:
        _, histories = generate_detection_dataset(seed, config)
        if seed.index == 0:
            representative = _flatten_observations(histories)
        all_profile = hazard_ratio_profile(
            histories,
            config.hazard_ratios,
            config.background_hazard,
            config.detection_probability,
            config.visits_per_survey,
        )
        training = tuple(row for row in histories if row.split == "training")
        holdout = tuple(row for row in histories if row.split == "holdout")
        training_profile = hazard_ratio_profile(
            training,
            config.hazard_ratios,
            config.background_hazard,
            config.detection_probability,
            config.visits_per_survey,
        )
        neutral_profile = neutral_hazard_profile(
            training,
            config.neutral_hazards,
            config.detection_probability,
            config.visits_per_survey,
        )
        support = _summarize_support(all_profile, cutoff.cutoff, config.truth_hazard_ratio)
        predator_score = log_likelihood_hazard_ratio(holdout, training_profile.mle, config) / len(
            holdout
        )
        neutral_score = log_likelihood_neutral(holdout, neutral_profile.mle, config) / len(holdout)
        validation_rows.append(
            ValidationResult(
                seed.index,
                _detected_visit_count(histories),
                _detected_site_count(histories),
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
                predator_score,
                neutral_score,
                predator_score - neutral_score,
            )
        )
        valid_histories &= _histories_valid(histories, config)
        finite_likelihoods &= bool(
            np.isfinite(all_profile.log_likelihoods).all()
            and np.isfinite(training_profile.log_likelihoods).all()
            and np.isfinite(neutral_profile.log_likelihoods).all()
            and math.isfinite(predator_score)
            and math.isfinite(neutral_score)
        )

    coverage_count = sum(row.truth_included for row in validation_rows)
    coverage = wilson_interval(coverage_count, len(validation_rows))
    connected = sum(
        row.support_component_count == 1 and not row.support_boundary_contact
        for row in validation_rows
    )
    null_exclusion = sum(row.null_excluded for row in validation_rows)
    score_advantage = normal_mean_interval(
        [row.heldout_log_score_advantage for row in validation_rows]
    )
    summary = RecoverySummary(
        cutoff=cutoff.cutoff,
        coverage_count=coverage_count,
        coverage=coverage,
        connected_interior_count=connected,
        null_exclusion_count=null_exclusion,
        median_absolute_log_error=median(
            row.absolute_log_hazard_ratio_error for row in validation_rows
        ),
        median_log_support_width=median(row.log_support_width for row in validation_rows),
        heldout_log_score_advantage=score_advantage,
    )
    all_seeds = (*calibration_seeds, *validation_seeds)
    invariants = {
        "goal027_anchor_reconciled": anchor.recovered,
        "history_count_split_and_observations": valid_histories,
        "finite_likelihoods_and_scores": finite_likelihoods,
        "independent_seed_streams": len(
            {(seed.process_seed, seed.prey_seed, seed.detection_seed) for seed in all_seeds}
        )
        == len(all_seeds),
        "calibration_count": len(calibration_rows) == config.calibration_replicates,
        "validation_count": len(validation_rows) == config.validation_replicates,
        "representative_observation_count": len(representative) == 160 * len(SURVEY_TIMES),
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
    return Goal029Result(
        config,
        anchor,
        tuple(calibration_rows),
        tuple(validation_rows),
        representative,
        summary,
        invariants,
        outcome,
    )


def write_review_bundle(result: Goal029Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the compact seven-file Goal 029 review surface."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("output directory must be empty")
    _write_dataclass_csv(target / "calibration_statistics.csv", result.calibration_statistics)
    _write_dataclass_csv(target / "validation_results.csv", result.validation_results)
    _write_dataclass_csv(
        target / "representative_prey_observations.csv", result.representative_observations
    )
    _write_dataclass_csv(target / "benchmark_comparison.csv", result.comparison)
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    _save_figure(target / "known_imperfect_prey_detection.svg", _review_figure(result))
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 029 review surface is incomplete")
    return written


def _phase_seeds(
    phase: str,
    count: int,
    process_root: np.random.SeedSequence,
    prey_root: np.random.SeedSequence,
    detection_root: np.random.SeedSequence,
) -> tuple[DatasetSeed, ...]:
    process_children = process_root.spawn(count)
    prey_children = prey_root.spawn(count)
    detection_children = detection_root.spawn(count)
    return tuple(
        DatasetSeed(
            phase,
            index,
            int(process.generate_state(1, dtype=np.uint64)[0]),
            int(prey.generate_state(1, dtype=np.uint64)[0]),
            int(detection.generate_state(1, dtype=np.uint64)[0]),
        )
        for index, (process, prey, detection) in enumerate(
            zip(process_children, prey_children, detection_children, strict=True)
        )
    )


def _observation_log_likelihoods(
    histories: tuple[DetectionHistory, ...],
    candidates: NDArray[np.float64],
    *,
    background_hazard: float,
    detection_probability: float,
    visits_per_survey: int,
    use_arrival: bool,
) -> NDArray[np.float64]:
    if not histories:
        raise ValueError("detection histories must not be empty")
    if (
        candidates.ndim != 1
        or not np.isfinite(candidates).all()
        or np.any(candidates <= 0.0)
        or not math.isfinite(background_hazard)
        or background_hazard <= 0.0
        or not 0.0 < detection_probability < 1.0
        or visits_per_survey <= 0
    ):
        raise ValueError("likelihood inputs must be finite and valid")
    arrivals = np.asarray([row.predator_arrival_time for row in histories], dtype=np.float64)
    counts = np.asarray([row.detection_counts for row in histories], dtype=np.int64)
    alive_probability = np.ones((len(candidates), len(histories)), dtype=np.float64)
    dead_probability = np.zeros_like(alive_probability)
    previous_time = 0.0
    for survey_index, survey_time in enumerate(SURVEY_TIMES):
        if use_arrival:
            pre_duration = np.minimum(survey_time, arrivals) - np.minimum(previous_time, arrivals)
            post_duration = np.maximum(survey_time - arrivals, 0.0) - np.maximum(
                previous_time - arrivals, 0.0
            )
            cumulative_increment = background_hazard * (
                pre_duration[None, :] + candidates[:, None] * post_duration[None, :]
            )
        else:
            cumulative_increment = candidates[:, None] * (survey_time - previous_time)
        survival = np.exp(-cumulative_increment)
        predicted_alive = alive_probability * survival
        predicted_dead = dead_probability + alive_probability * (1.0 - survival)
        survey_counts = counts[:, survey_index]
        alive_emission = np.asarray(
            [
                math.comb(visits_per_survey, int(count))
                * detection_probability ** int(count)
                * (1.0 - detection_probability) ** (visits_per_survey - int(count))
                for count in survey_counts
            ],
            dtype=np.float64,
        )
        dead_emission = (survey_counts == 0).astype(np.float64)
        alive_probability = predicted_alive * alive_emission[None, :]
        dead_probability = predicted_dead * dead_emission[None, :]
        previous_time = survey_time
    site_probability = alive_probability + dead_probability
    if np.any(site_probability <= 0.0) or not np.isfinite(site_probability).all():
        raise RuntimeError("observation likelihood produced invalid site probabilities")
    return np.log(site_probability).sum(axis=1)


def _likelihood_ratio_at_truth(profile: LikelihoodProfile, truth: float) -> float:
    indices = np.flatnonzero(np.isclose(profile.candidates, truth, rtol=0.0, atol=1e-12))
    if len(indices) != 1:
        raise ValueError("truth must occur once on the likelihood grid")
    statistic = 2.0 * (
        profile.maximum_log_likelihood - float(profile.log_likelihoods[int(indices[0])])
    )
    return max(0.0, statistic)


def _summarize_support(
    profile: LikelihoodProfile, cutoff: float, truth: float
) -> tuple[bool, int, bool, bool, float, float]:
    mask = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods) <= cutoff
    indices = np.flatnonzero(mask)
    if len(indices) == 0:
        raise RuntimeError("likelihood support must not be empty")
    truth_index = np.flatnonzero(np.isclose(profile.candidates, truth, rtol=0.0, atol=1e-12))
    if len(truth_index) != 1:
        raise ValueError("truth must occur once on the likelihood grid")
    components = int(mask[0]) + int(np.sum(mask[1:] & ~mask[:-1]))
    return (
        bool(mask[int(truth_index[0])]),
        components,
        bool(mask[0] or mask[-1]),
        bool(not mask[0]),
        float(profile.candidates[int(indices[0])]),
        float(profile.candidates[int(indices[-1])]),
    )


def _histories_valid(histories: tuple[DetectionHistory, ...], config: Goal029Config) -> bool:
    if len(histories) != 160:
        return False
    if sum(row.split == "training" for row in histories) != 120:
        return False
    if sum(row.split == "holdout" for row in histories) != 40:
        return False
    for row in histories:
        if not (
            math.isfinite(row.predator_arrival_time)
            and math.isfinite(row.true_extirpation_time)
            and len(row.detection_counts) == len(SURVEY_TIMES)
            and len(row.true_alive) == len(SURVEY_TIMES)
            and all(0 <= count <= config.visits_per_survey for count in row.detection_counts)
            and all(
                count == 0
                for count, is_alive in zip(row.detection_counts, row.true_alive, strict=True)
                if not is_alive
            )
            and row.true_alive == tuple(row.true_extirpation_time > time for time in SURVEY_TIMES)
        ):
            return False
    return True


def _detected_visit_count(histories: tuple[DetectionHistory, ...]) -> int:
    return sum(sum(row.detection_counts) for row in histories)


def _detected_site_count(histories: tuple[DetectionHistory, ...]) -> int:
    return sum(any(row.detection_counts) for row in histories)


def _flatten_observations(
    histories: tuple[DetectionHistory, ...],
) -> tuple[SurveyObservation, ...]:
    return tuple(
        SurveyObservation(
            row.site_id,
            row.split,
            row.row,
            row.col,
            row.predator_arrival_time,
            row.true_extirpation_time,
            survey_time,
            is_alive,
            count,
        )
        for row in histories
        for survey_time, is_alive, count in zip(
            SURVEY_TIMES, row.true_alive, row.detection_counts, strict=True
        )
    )


CsvRow = CalibrationStatistic | ValidationResult | SurveyObservation | BenchmarkComparison


def _write_dataclass_csv(path: Path, rows: tuple[CsvRow, ...]) -> None:
    if not rows:
        raise ValueError("CSV rows must not be empty")
    payload = [asdict(row) for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]))
        writer.writeheader()
        writer.writerows(payload)


def _summary_payload(result: Goal029Result) -> dict[str, object]:
    summary = result.summary
    return {
        "goal": "029-known-arrival-known-imperfect-prey-detection",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "outcome": result.outcome,
        "scientific_interpretation": result.outcome,
        "model": {
            "background_hazard": result.config.background_hazard,
            "truth_hazard_ratio": result.config.truth_hazard_ratio,
            "survey_times": SURVEY_TIMES,
            "visits_per_survey": result.config.visits_per_survey,
            "known_detection_probability": result.config.detection_probability,
            "false_positive_probability": 0.0,
            "predator_arrival": "known realized central stochastic truth",
            "prey_likelihood": "two-state absorbing hidden process marginalized exactly",
            "neutral_model": "fitted constant hazard with identical observation process",
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
            "null_exclusion_count": summary.null_exclusion_count,
            "median_absolute_log_error": summary.median_absolute_log_error,
            "median_log_support_width": summary.median_log_support_width,
            "heldout_log_score_advantage": asdict(summary.heldout_log_score_advantage),
        },
        "perfect_observation_anchor": asdict(result.perfect_observation_anchor),
        "failed_gates": _failed_gates(result),
        "invariants": result.invariants,
    }


def _failed_gates(result: Goal029Result) -> tuple[str, ...]:
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


def _review(result: Goal029Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 029: Known Imperfect Prey Detection\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    failed = _failed_gates(result)
    if result.outcome == RECOVERED:
        interpretation = (
            "The fivefold prey effect remained recoverable after introducing known imperfect "
            "prey detection. Explicitly marginalizing missed detections retained calibrated, "
            "precise parameter support and predictive advantage over neutral."
        )
    else:
        interpretation = (
            "Known imperfect prey detection removed enough information that the fivefold effect "
            "did not pass every inherited recovery gate. This is a scientific information-loss "
            f"result, not a reconstruction failure. Failed gates: {', '.join(failed)}."
        )
    comparison_rows = [
        (
            f"| {row.observation_model} | {row.coverage:.3f} | "
            f"{row.null_exclusion_count}/{row.validation_replicates} | "
            f"{row.median_absolute_log_error:.3f} | {row.median_log_support_width:.3f} | "
            f"{row.score_advantage:.4f} | {'yes' if row.recovered else 'no'} |"
        )
        for row in result.comparison
    ]
    return "\n".join(
        [
            "# Goal 029: Known Imperfect Prey Detection",
            "",
            f"Outcome: `{result.outcome}`.",
            "",
            "## What changed",
            "",
            (
                "Predator arrival remained known and the ecological process was unchanged. At "
                "each survey, two independent visits detected a persisting prey population with "
                "known probability 0.65 per visit. The likelihood summed over latent alive/dead "
                "histories, so zero detections were allowed to be either missed presence or true "
                "extirpation."
            ),
            "",
            "## Result",
            "",
            interpretation,
            "",
            (
                "| Observation model | Coverage | No effect excluded | Median log error | "
                "Median support width | Held-out advantage | Recovered |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|",
            *comparison_rows,
            "",
            "## Boundary",
            "",
            (
                "Detection probability was known, false positives were absent, survey timing was "
                "fixed, and only the prey-effect multiplier was estimated. The neutral comparator "
                "used the same imperfect-detection process. No predator parameter or detection "
                "parameter was fitted."
            ),
            "",
        ]
    )


def _review_figure(result: Goal029Result) -> Figure:
    rows = result.comparison
    labels = ("Perfect", "Known p = 0.65")
    colors = ("#6B7280", "#1B7F79")
    x_positions = np.arange(len(rows))
    figure, axes = plt.subplots(1, 4, figsize=(13.2, 4.0), constrained_layout=True)

    coverage = [row.coverage for row in rows]
    lower = [row.coverage - row.coverage_lower for row in rows]
    upper = [row.coverage_upper - row.coverage for row in rows]
    for index, (value, low, high, color) in enumerate(
        zip(coverage, lower, upper, colors, strict=True)
    ):
        axes[0].errorbar(
            index,
            value,
            yerr=np.asarray(((low,), (high,))),
            fmt="o",
            color=color,
            elinewidth=2,
            capsize=4,
            markersize=7,
            zorder=3 + index,
        )
    axes[0].axhline(0.95, color="#B91C1C", linestyle="--", linewidth=1)
    axes[0].set_title("Calibrated coverage", pad=10)
    axes[0].set_ylim(0.88, 1.0)

    exclusion = [row.null_exclusion_count / row.validation_replicates for row in rows]
    axes[1].bar(x_positions, exclusion, color=colors)
    axes[1].axhline(0.95, color="#B91C1C", linestyle="--", linewidth=1)
    axes[1].set_title("No effect excluded", pad=10)
    axes[1].set_ylim(0.0, 1.05)

    widths = [row.median_log_support_width for row in rows]
    axes[2].bar(x_positions, widths, color=colors)
    axes[2].axhline(0.80, color="#B91C1C", linestyle="--", linewidth=1)
    axes[2].set_title("Median log-support width", pad=10)

    advantages = [row.score_advantage for row in rows]
    advantage_lower = [row.score_advantage - row.score_advantage_lower for row in rows]
    advantage_upper = [row.score_advantage_upper - row.score_advantage for row in rows]
    for index, (value, low, high, color) in enumerate(
        zip(advantages, advantage_lower, advantage_upper, colors, strict=True)
    ):
        axes[3].errorbar(
            index,
            value,
            yerr=np.asarray(((low,), (high,))),
            fmt="o",
            color=color,
            elinewidth=2,
            capsize=4,
            markersize=7,
            zorder=3 + index,
        )
    axes[3].axhline(0.0, color="#B91C1C", linestyle="--", linewidth=1)
    axes[3].set_title("Held-out advantage vs neutral", pad=10)

    for axis in axes:
        axis.set_xticks(x_positions, labels)
        axis.grid(axis="y", color="#D1D5DB", linewidth=0.6, alpha=0.8)
        axis.set_axisbelow(True)
    figure.suptitle(
        "Fivefold prey effect under known imperfect detection",
        fontsize=14,
    )
    return figure


def _save_figure(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", bbox_inches="tight")
    plt.close(figure)
