"""Paired Arc 2B campaign for latent-arrival prey-effect recovery."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean, median
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.arc2b_design import (
    Block,
    TruthCondition,
    campaign_truths,
    truths_for_block,
)
from latent_landscapes.goal002.calibration import (
    normal_mean_interval,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal004.observations import SURVEY_TIMES
from latent_landscapes.goal006.spread import (
    ContrastSpreadTruth,
    compute_contrast_spread,
    sample_edge_shock_vector,
)
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal011 import benchmark as goal011

DEFAULT_OUTPUT_DIR = Path("artifacts/arc2b_campaign")
EXPECTED_FILES = (
    "truth_design.csv",
    "calibration_statistics.csv",
    "calibration_condition_summaries.csv",
    "validation_metrics.csv",
    "validation_condition_summaries.csv",
    "summary.json",
    "seed_provenance.json",
    "review.md",
)
MASTER_SEED = 20260831
INTEGRATION_BANK_SIZE = 4096
CALIBRATION_REPLICATES = 250
VALIDATION_REPLICATES = 250
CALIBRATION_RANK_ONE_BASED = 239
PSEUDO_ARRIVALS = (5.0, 15.0, 25.0, 35.0, 45.0, 55.0, 70.0)
CATEGORY_COUNT = len(SURVEY_TIMES) + 1
EFFECT_GRID = tuple(float(value) for value in np.linspace(1.0, 10.0, 181))
NEUTRAL_HAZARD_GRID = tuple(float(value) for value in np.geomspace(0.0001, 0.05, 241))


@dataclass(frozen=True, slots=True)
class CampaignConfig:
    master_seed: int = MASTER_SEED
    bank_size: int = INTEGRATION_BANK_SIZE
    calibration_replicates: int = CALIBRATION_REPLICATES
    validation_replicates: int = VALIDATION_REPLICATES
    calibration_rank_one_based: int = CALIBRATION_RANK_ONE_BASED
    effect_grid: tuple[float, ...] = EFFECT_GRID
    neutral_hazard_grid: tuple[float, ...] = NEUTRAL_HAZARD_GRID
    truths: tuple[TruthCondition, ...] = campaign_truths("pilot")
    predator_detection_probability: float = 0.65
    visits_per_survey: int = 2

    def __post_init__(self) -> None:
        if (
            self.bank_size <= 0
            or self.calibration_replicates <= 0
            or self.validation_replicates <= 0
        ):
            raise ValueError("bank and replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within the calibration ensemble")
        for values, name in (
            (self.effect_grid, "effect"),
            (self.neutral_hazard_grid, "neutral hazard"),
        ):
            array = np.asarray(values, dtype=np.float64)
            if (
                array.ndim != 1
                or not len(array)
                or not np.isfinite(array).all()
                or (array <= 0).any()
            ):
                raise ValueError(f"{name} grid is invalid")
            if np.any(np.diff(array) <= 0):
                raise ValueError(f"{name} grid must be strictly increasing")
        if self.effect_grid[0] != 1.0:
            raise ValueError("effect grid must begin at the no-effect value")
        if not 0.0 < self.predator_detection_probability < 1.0 or self.visits_per_survey != 2:
            raise ValueError("predator observation settings are invalid")
        if not self.truths or len({row.condition_id for row in self.truths}) != len(self.truths):
            raise ValueError("truth conditions must have unique identifiers")
        if any(
            not all(
                math.isfinite(value)
                for value in (
                    row.effect_multiplier,
                    row.background_risk,
                    row.prey_detection_probability,
                )
            )
            or not 1.0 <= row.effect_multiplier <= 10.0
            or not 0.0 < row.background_risk < 1.0
            or not 0.0 < row.prey_detection_probability < 1.0
            for row in self.truths
        ):
            raise ValueError("truth coordinates are invalid")

    @property
    def production_block(self) -> Block | None:
        standard = (
            self.master_seed == MASTER_SEED
            and self.bank_size == INTEGRATION_BANK_SIZE
            and self.calibration_replicates == CALIBRATION_REPLICATES
            and self.validation_replicates == VALIDATION_REPLICATES
            and self.calibration_rank_one_based == CALIBRATION_RANK_ONE_BASED
            and self.effect_grid == EFFECT_GRID
            and self.neutral_hazard_grid == NEUTRAL_HAZARD_GRID
        )
        if standard and self.truths == campaign_truths("pilot"):
            return "pilot"
        if standard and self.truths == campaign_truths("prospective"):
            return "prospective"
        return None


DEFAULT_CONFIG = CampaignConfig()
PILOT_CONFIG = DEFAULT_CONFIG


def prospective_config() -> CampaignConfig:
    return CampaignConfig(truths=campaign_truths("prospective"))


def smoke_config(block: Block = "pilot") -> CampaignConfig:
    truths = (
        truths_for_block(block)[:2]
        if block == "prospective"
        else (*truths_for_block(block)[:2], *campaign_truths("pilot")[-2:])
    )
    return CampaignConfig(
        bank_size=8,
        calibration_replicates=4,
        validation_replicates=4,
        calibration_rank_one_based=4,
        effect_grid=(1.0, 3.0, 5.0, 7.0, 9.0),
        neutral_hazard_grid=(0.0005, 0.001, 0.002, 0.004, 0.008, 0.016, 0.032),
        truths=truths,
    )


def timing_config(block: Block = "pilot") -> CampaignConfig:
    return CampaignConfig(
        bank_size=64,
        calibration_replicates=2,
        validation_replicates=2,
        calibration_rank_one_based=2,
        truths=campaign_truths(block),
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
    prey_detection_probability: float = 0.65


@dataclass(frozen=True, slots=True)
class GeneratedDataset:
    truth: ContrastSpreadTruth
    records: tuple[CrossLayerHistory, ...]


@dataclass(frozen=True, slots=True)
class ArrivalIntegration:
    site_ids: tuple[str, ...]
    effect_multipliers: tuple[float, ...]
    category_mass: NDArray[np.float64]
    survival_moments: NDArray[np.float64]
    bank_arrivals: NDArray[np.float64]
    bank_checksum: str


@dataclass(frozen=True, slots=True)
class LikelihoodProfile:
    candidates: NDArray[np.float64]
    log_likelihoods: NDArray[np.float64]
    maximum_log_likelihood: float
    mle: float


@dataclass(frozen=True, slots=True)
class CalibrationStatistic:
    condition_id: str
    dataset_index: int
    likelihood_ratio_at_truth: float
    true_extirpations_by_day60: int
    predator_detected_visit_count: int
    prey_detected_visit_count: int


@dataclass(frozen=True, slots=True)
class CalibrationSummary:
    condition_id: str
    calibration_count: int
    cutoff: float
    median_likelihood_ratio_at_truth: float
    mean_true_extirpations_by_day60: float
    mean_predator_detected_visit_count: float
    mean_prey_detected_visit_count: float


@dataclass(frozen=True, slots=True)
class ValidationMetric:
    condition_id: str
    dataset_index: int
    truth_included: bool
    support_component_count: int
    support_boundary_contact: bool
    no_effect_excluded: bool
    mle_effect_multiplier: float
    absolute_log_effect_error: float
    log_support_width: float
    heldout_known_background_no_effect_advantage_per_record: float
    heldout_fitted_neutral_advantage_per_record: float
    true_extirpations_by_day60: int
    pre_arrival_true_extirpations: int
    post_arrival_true_extirpations: int
    true_extirpation_censoring: int
    post_arrival_at_risk_exposure: float
    prey_observation_support: int


@dataclass(frozen=True, slots=True)
class TruthSummary:
    condition_id: str
    design_role: str
    truth_effect_multiplier: float
    truth_background_risk: float
    truth_prey_detection_probability: float
    cutoff: float
    validation_count: int
    coverage: float
    coverage_lower: float
    coverage_upper: float
    connected_interior_frequency: float
    no_effect_exclusion_probability: float
    median_absolute_log_effect_error: float
    median_log_support_width: float
    mean_heldout_known_background_no_effect_advantage_per_record: float
    heldout_known_background_no_effect_advantage_lower: float
    heldout_known_background_no_effect_advantage_upper: float
    mean_heldout_fitted_neutral_advantage_per_record: float
    heldout_fitted_neutral_advantage_lower: float
    heldout_fitted_neutral_advantage_upper: float
    mean_true_extirpations_by_day60: float
    mean_pre_arrival_true_extirpations: float
    mean_post_arrival_true_extirpations: float
    mean_true_extirpation_censoring: float
    mean_post_arrival_at_risk_exposure: float
    mean_prey_observation_support: float
    failure_classification: str


@dataclass(frozen=True, slots=True)
class CampaignResult:
    config: CampaignConfig
    seed_manifest: SeedManifest
    calibration_statistics: tuple[CalibrationStatistic, ...]
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
    bank_checksum: str
    frozen_predictions_sha256: str | None = None


def _seed_int(child: np.random.SeedSequence) -> int:
    return int(child.generate_state(1, dtype=np.uint64)[0])


def spawn_seed_manifest(config: CampaignConfig = DEFAULT_CONFIG) -> SeedManifest:
    roots = np.random.SeedSequence(config.master_seed).spawn(9)
    bank = tuple(_seed_int(child) for child in roots[0].spawn(config.bank_size))

    def phase(
        name: str, count: int, phase_roots: tuple[np.random.SeedSequence, ...]
    ) -> tuple[DatasetSeed, ...]:
        streams = [tuple(_seed_int(child) for child in root.spawn(count)) for root in phase_roots]
        return tuple(DatasetSeed(name, i, *(stream[i] for stream in streams)) for i in range(count))

    return SeedManifest(
        bank,
        phase("calibration", config.calibration_replicates, tuple(roots[1:5])),
        phase("validation", config.validation_replicates, tuple(roots[5:9])),
    )


def sample_extirpation_time(
    *,
    predator_arrival: float,
    background_hazard: float,
    effect_multiplier: float,
    exponential_threshold: float,
) -> float:
    """Invert cumulative background plus post-arrival hazard for one site."""
    if (
        not all(
            math.isfinite(value)
            for value in (background_hazard, effect_multiplier, exponential_threshold)
        )
        or background_hazard <= 0
        or effect_multiplier <= 0
        or exponential_threshold < 0
    ):
        raise ValueError("hazards and threshold must be finite and positive")
    if not math.isfinite(predator_arrival):
        return exponential_threshold / background_hazard
    if predator_arrival < 0:
        raise ValueError("predator arrival must be non-negative")
    before = background_hazard * predator_arrival
    if exponential_threshold <= before:
        return exponential_threshold / background_hazard
    return predator_arrival + (exponential_threshold - before) / (
        background_hazard * effect_multiplier
    )


def generate_paired_datasets(
    fixed: goal007.FixedInputs,
    seed: DatasetSeed,
    truths: tuple[TruthCondition, ...],
    config: CampaignConfig = DEFAULT_CONFIG,
) -> tuple[GeneratedDataset, ...]:
    """Generate all conditions from shared process, detection, and prey streams."""
    shocks = sample_edge_shock_vector(fixed.landscape, np.random.default_rng(seed.process_seed))
    arrival_truth = compute_contrast_spread(fixed.landscape, 1.0, edge_shocks=shocks, rho=1.0)
    sites = tuple(sorted(fixed.design.sites, key=lambda value: value.site_id))
    predator_rng = np.random.default_rng(seed.predator_detection_seed)
    prey_rng = np.random.default_rng(seed.prey_seed)
    prey_detection_rng = np.random.default_rng(seed.prey_detection_seed)
    uniforms_pred = predator_rng.random((len(sites), len(SURVEY_TIMES), config.visits_per_survey))
    thresholds = prey_rng.exponential(size=len(sites))
    uniforms_prey = prey_detection_rng.random(
        (len(sites), len(SURVEY_TIMES), config.visits_per_survey)
    )
    output: list[GeneratedDataset] = []
    for condition in truths:
        histories: list[CrossLayerHistory] = []
        extirpations = tuple(
            sample_extirpation_time(
                predator_arrival=float(arrival_truth.arrival[site.row, site.col]),
                background_hazard=condition.background_hazard,
                effect_multiplier=condition.effect_multiplier,
                exponential_threshold=float(thresholds[i]),
            )
            for i, site in enumerate(sites)
        )
        for i, (site, extirpation) in enumerate(zip(sites, extirpations, strict=True)):
            arrival = float(arrival_truth.arrival[site.row, site.col])
            present = tuple(arrival <= time for time in SURVEY_TIMES)
            alive = tuple(extirpation > time for time in SURVEY_TIMES)
            predator_counts = tuple(
                int(np.sum(uniforms_pred[i, j] < config.predator_detection_probability))
                if present[j]
                else 0
                for j in range(len(SURVEY_TIMES))
            )
            prey_counts = tuple(
                int(np.sum(uniforms_prey[i, j] < condition.prey_detection_probability))
                if alive[j]
                else 0
                for j in range(len(SURVEY_TIMES))
            )
            histories.append(
                CrossLayerHistory(
                    seed.phase,
                    seed.index,
                    i,
                    site.site_id,
                    site.cluster_id,
                    site.split,
                    site.row,
                    site.col,
                    arrival,
                    extirpation,
                    predator_counts,
                    prey_counts,
                    present,
                    alive,
                    condition.prey_detection_probability,
                )
            )
        output.append(GeneratedDataset(arrival_truth, tuple(histories)))
    return tuple(output)


def build_arrival_integration(
    bank_arrivals: NDArray[np.float64],
    site_ids: tuple[str, ...],
    effect_multipliers: tuple[float, ...],
    background_hazard: float,
) -> ArrivalIntegration:
    bank = np.asarray(bank_arrivals, dtype=np.float64)
    effects = np.asarray(effect_multipliers, dtype=np.float64)
    if (
        bank.ndim != 2
        or bank.shape[1] != len(site_ids)
        or bank.shape[0] <= 0
        or not np.isfinite(bank).all()
        or (bank < 0).any()
    ):
        raise ValueError("arrival bank shape or values are invalid")
    if (
        effects.ndim != 1
        or not len(effects)
        or not np.isfinite(effects).all()
        or (effects <= 0).any()
    ):
        raise ValueError("effect grid is invalid")
    categories = np.searchsorted(np.asarray(SURVEY_TIMES), bank, side="left")
    denominator = bank.shape[0] + 0.5 * CATEGORY_COUNT
    masses = np.empty((len(site_ids), CATEGORY_COUNT), dtype=np.float64)
    moments = np.empty(
        (len(effects), len(site_ids), len(SURVEY_TIMES) + 1, CATEGORY_COUNT), dtype=np.float64
    )
    for site_index in range(len(site_ids)):
        for category in range(CATEGORY_COUNT):
            values = bank[categories[:, site_index] == category, site_index]
            mass = (len(values) + 0.5) / denominator
            masses[site_index, category] = mass
            moments[:, site_index, 0, category] = mass
            pseudo = PSEUDO_ARRIVALS[category]
            for time_index, survey_time in enumerate(SURVEY_TIMES, start=1):
                if category >= time_index:
                    moments[:, site_index, time_index, category] = mass * math.exp(
                        -background_hazard * survey_time
                    )
                else:
                    observed = (
                        np.exp(
                            -background_hazard
                            * (
                                effects[:, None] * survey_time
                                + (1 - effects[:, None]) * values[None, :]
                            )
                        ).sum(axis=1)
                        if len(values)
                        else np.zeros(len(effects))
                    )
                    pseudo_survival = np.exp(
                        -background_hazard * (effects * survey_time + (1 - effects) * pseudo)
                    )
                    moments[:, site_index, time_index, category] = (
                        observed + 0.5 * pseudo_survival
                    ) / denominator
    return ArrivalIntegration(
        tuple(site_ids),
        tuple(float(x) for x in effects),
        masses,
        moments,
        bank,
        hashlib.sha256(np.ascontiguousarray(bank).tobytes()).hexdigest(),
    )


def _binomial_probability(count: int, probability: float, visits: int = 2) -> float:
    return math.comb(visits, count) * probability**count * (1 - probability) ** (visits - count)


def _predator_category_probabilities(
    histories: tuple[CrossLayerHistory, ...], p: float = 0.65
) -> NDArray[np.float64]:
    result = np.ones((len(histories), CATEGORY_COUNT), dtype=np.float64)
    for i, row in enumerate(histories):
        for category in range(CATEGORY_COUNT):
            value = 1.0
            for j, count in enumerate(row.predator_detection_counts):
                if category > j:
                    if count:
                        value = 0.0
                        break
                else:
                    value *= _binomial_probability(count, p)
            result[i, category] = value
    return result


def _prey_emission_coefficients(
    histories: tuple[CrossLayerHistory, ...],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    events = np.empty((len(histories), len(SURVEY_TIMES)), dtype=np.float64)
    alive_all = np.empty(len(histories), dtype=np.float64)
    for i, row in enumerate(histories):
        alive = np.asarray(
            [
                _binomial_probability(count, row.prey_detection_probability)
                for count in row.prey_detection_counts
            ]
        )
        dead = np.asarray([count == 0 for count in row.prey_detection_counts], dtype=np.float64)
        for event_index in range(len(SURVEY_TIMES)):
            events[i, event_index] = (
                np.prod(alive[:event_index]) if event_index else 1.0
            ) * np.prod(dead[event_index:])
        alive_all[i] = np.prod(alive)
    return events, alive_all


def latent_arrival_profile(
    histories: tuple[CrossLayerHistory, ...],
    integration: ArrivalIntegration,
    config: CampaignConfig,
) -> LikelihoodProfile:
    if not histories:
        raise ValueError("histories must not be empty")
    indices = np.asarray([row.site_index for row in histories], dtype=np.int64)
    predator = _predator_category_probabilities(histories, config.predator_detection_probability)
    events, alive = _prey_emission_coefficients(histories)
    moments = integration.survival_moments[:, indices]
    weighted = np.einsum("hstc,sc->hst", moments, predator, optimize=True)
    event_probs = weighted[:, :, :-1] - weighted[:, :, 1:]
    probabilities = (
        np.einsum("hsj,sj->hs", event_probs, events, optimize=True)
        + weighted[:, :, -1] * alive[None, :]
    )
    if not np.isfinite(probabilities).all() or np.any(probabilities <= 0):
        raise RuntimeError("shared-arrival likelihood produced invalid probabilities")
    values = np.log(probabilities).sum(axis=1)
    maximum = int(np.argmax(values))
    return LikelihoodProfile(
        np.asarray(integration.effect_multipliers),
        values,
        float(values[maximum]),
        float(integration.effect_multipliers[maximum]),
    )


def neutral_hazard_profile(
    histories: tuple[CrossLayerHistory, ...],
    config: CampaignConfig,
    integration: ArrivalIntegration,
) -> LikelihoodProfile:
    """Profile the observation-matched constant-hazard neutral comparator."""
    return _neutral_profile(histories, integration, config.neutral_hazard_grid, config)


def _neutral_profile(
    histories: tuple[CrossLayerHistory, ...],
    integration: ArrivalIntegration,
    hazards: tuple[float, ...],
    config: CampaignConfig,
) -> LikelihoodProfile:
    indices = np.asarray([row.site_index for row in histories], dtype=np.int64)
    predator = _predator_category_probabilities(histories, config.predator_detection_probability)
    predator_marginal = np.einsum("sc,sc->s", integration.category_mass[indices], predator)
    events, alive = _prey_emission_coefficients(histories)
    h = np.asarray(hazards, dtype=np.float64)
    times = np.asarray((0.0, *SURVEY_TIMES))
    survival = np.exp(-h[:, None] * times[None, :])
    event_probs = survival[:, :-1] - survival[:, 1:]
    prey = np.einsum("hj,sj->hs", event_probs, events) + survival[:, -1, None] * alive[None, :]
    values = np.log(prey * predator_marginal[None, :]).sum(axis=1)
    maximum = int(np.argmax(values))
    return LikelihoodProfile(h, values, float(values[maximum]), float(h[maximum]))


def _likelihood_ratio_at_truth(profile: LikelihoodProfile, truth: float) -> float:
    indices = np.flatnonzero(np.isclose(profile.candidates, truth, rtol=0, atol=1e-12))
    if len(indices) != 1:
        raise ValueError("effect truth must occur once on grid")
    return max(
        0.0,
        2.0 * (profile.maximum_log_likelihood - float(profile.log_likelihoods[int(indices[0])])),
    )


def _support(
    profile: LikelihoodProfile, cutoff: float, truth: float
) -> tuple[bool, int, bool, bool, float, float]:
    mask = 2 * (profile.maximum_log_likelihood - profile.log_likelihoods) <= cutoff
    ids = np.flatnonzero(mask)
    truth_ids = np.flatnonzero(np.isclose(profile.candidates, truth, rtol=0, atol=1e-12))
    if not len(ids) or len(truth_ids) != 1:
        raise ValueError("support or truth is missing")
    components = int(mask[0]) + int(np.sum(mask[1:] & ~mask[:-1]))
    return (
        bool(mask[int(truth_ids[0])]),
        components,
        bool(mask[0] or mask[-1]),
        bool(not mask[0]),
        float(profile.candidates[ids[0]]),
        float(profile.candidates[ids[-1]]),
    )


def _extirpation_metrics(
    histories: tuple[CrossLayerHistory, ...],
) -> tuple[int, int, int, int, float, int]:
    observed = [row.true_prey_extirpation <= SURVEY_TIMES[-1] for row in histories]
    pre = sum(
        event and row.true_prey_extirpation <= row.true_predator_arrival
        for event, row in zip(observed, histories, strict=True)
    )
    post = sum(
        event and row.true_prey_extirpation > row.true_predator_arrival
        for event, row in zip(observed, histories, strict=True)
    )
    exposure = sum(
        max(0.0, min(60.0, row.true_prey_extirpation) - min(60.0, row.true_predator_arrival))
        for row in histories
    )
    support = sum(sum(row.prey_detection_counts) for row in histories)
    return sum(observed), pre, post, len(histories) - sum(observed), exposure, support


def _histories_valid(histories: tuple[CrossLayerHistory, ...]) -> bool:
    if len(histories) != 160 or sum(row.split == "training" for row in histories) != 120:
        return False
    if sum(row.split == "holdout" for row in histories) != 40:
        return False
    if len({row.site_index for row in histories}) != 160:
        return False
    return all(
        math.isfinite(row.true_predator_arrival)
        and math.isfinite(row.true_prey_extirpation)
        and len(row.predator_detection_counts) == len(SURVEY_TIMES)
        and len(row.prey_detection_counts) == len(SURVEY_TIMES)
        and row.true_predator_present
        == tuple(row.true_predator_arrival <= time for time in SURVEY_TIMES)
        and row.true_prey_alive == tuple(row.true_prey_extirpation > time for time in SURVEY_TIMES)
        and all(0 <= count <= 2 for count in row.predator_detection_counts)
        and all(0 <= count <= 2 for count in row.prey_detection_counts)
        and all(
            count == 0 or present
            for count, present in zip(
                row.predator_detection_counts, row.true_predator_present, strict=True
            )
        )
        and all(
            count == 0 or alive
            for count, alive in zip(row.prey_detection_counts, row.true_prey_alive, strict=True)
        )
        for row in histories
    )


def _generate_bank(fixed: goal007.FixedInputs, seeds: tuple[int, ...]) -> NDArray[np.float64]:
    sites = tuple(sorted(fixed.design.sites, key=lambda value: value.site_id))
    rows = []
    for seed in seeds:
        shocks = sample_edge_shock_vector(fixed.landscape, np.random.default_rng(seed))
        truth = compute_contrast_spread(fixed.landscape, 1.0, edge_shocks=shocks, rho=1.0)
        rows.append([truth.arrival[site.row, site.col] for site in sites])
    return np.asarray(rows, dtype=np.float64)


def _classify_truth(
    truth: TruthCondition,
    *,
    coverage: Any,
    connected: int,
    null_count: int,
    count: int,
    error: float,
    width: float,
    score_interval: Any,
) -> str:
    """Apply the frozen truth and control gates to one condition summary."""
    if truth.design_role == "neutral_control":
        valid = (
            coverage.lower <= 0.95 <= coverage.upper
            and connected >= math.ceil(0.952 * count)
            and null_count <= math.floor(0.076 * count)
            and score_interval.lower <= 0.0
        )
        return "neutral_control_valid" if valid else "control_review_required"
    valid = (
        coverage.lower <= 0.95 <= coverage.upper
        and connected >= math.ceil(0.952 * count)
        and null_count >= math.ceil(0.952 * count)
        and error <= 0.20
        and (truth.design_role == "reference_control" or width <= 0.80)
        and score_interval.lower > 0.0
    )
    if truth.design_role == "reference_control":
        return "reference_control_valid" if valid else "control_review_required"
    exclusion_and_prediction = null_count >= math.ceil(0.952 * count) and score_interval.lower > 0.0
    if valid:
        return "fully_recovered"
    if exclusion_and_prediction:
        return "detected_but_not_fully_recovered"
    return "not_reliably_detected"


def _calibration_task(
    task: tuple[
        goal007.FixedInputs,
        DatasetSeed,
        tuple[TruthCondition, ...],
        tuple[tuple[TruthCondition, ArrivalIntegration], ...],
        CampaignConfig,
    ],
) -> tuple[CalibrationStatistic, ...]:
    fixed, seed, truths, models, config = task
    datasets = generate_paired_datasets(fixed, seed, truths, config)
    rows: list[CalibrationStatistic] = []
    for truth, dataset, (_, integration) in zip(truths, datasets, models, strict=True):
        histories = dataset.records
        profile = latent_arrival_profile(histories, integration, config)
        metrics = _extirpation_metrics(histories)
        rows.append(
            CalibrationStatistic(
                truth.condition_id,
                seed.index,
                _likelihood_ratio_at_truth(profile, truth.effect_multiplier),
                metrics[0],
                sum(sum(row.predator_detection_counts) for row in histories),
                metrics[5],
            )
        )
    return tuple(rows)


def _validation_task(
    task: tuple[
        goal007.FixedInputs,
        DatasetSeed,
        tuple[TruthCondition, ...],
        tuple[tuple[TruthCondition, ArrivalIntegration], ...],
        CampaignConfig,
        dict[str, float],
    ],
) -> tuple[ValidationMetric, ...]:
    fixed, seed, truths, models, config, cutoffs = task
    datasets = generate_paired_datasets(fixed, seed, truths, config)
    rows: list[ValidationMetric] = []
    for truth, dataset, (_, integration) in zip(truths, datasets, models, strict=True):
        histories = dataset.records
        profile = latent_arrival_profile(histories, integration, config)
        included, components, boundary, null_excluded, lower, upper = _support(
            profile, cutoffs[truth.condition_id], truth.effect_multiplier
        )
        training = tuple(row for row in histories if row.split == "training")
        holdout = tuple(row for row in histories if row.split == "holdout")
        train_profile = latent_arrival_profile(training, integration, config)
        fitted_neutral = neutral_hazard_profile(training, config, integration)
        process_score = latent_arrival_profile(holdout, integration, config).log_likelihoods[
            np.argmax(train_profile.log_likelihoods)
        ] / len(holdout)
        known_background_score = _neutral_profile(
            holdout, integration, (truth.background_hazard,), config
        ).maximum_log_likelihood / len(holdout)
        fitted_neutral_score = _neutral_profile(
            holdout, integration, (fitted_neutral.mle,), config
        ).maximum_log_likelihood / len(holdout)
        rows.append(
            ValidationMetric(
                truth.condition_id,
                seed.index,
                included,
                components,
                boundary,
                null_excluded,
                profile.mle,
                abs(math.log(profile.mle / truth.effect_multiplier)),
                math.log(upper / lower),
                process_score - known_background_score,
                process_score - fitted_neutral_score,
                *_extirpation_metrics(histories),
            )
        )
    return tuple(rows)


def run_campaign(
    config: CampaignConfig = DEFAULT_CONFIG,
    *,
    workers: int = 1,
    source_commit: str = "unknown",
    frozen_predictions_sha256: str | None = None,
) -> CampaignResult:
    if workers <= 0:
        raise ValueError("workers must be positive")
    started = time.perf_counter()
    fixed = goal011.build_fixed_inputs()
    manifest = spawn_seed_manifest(config)
    bank_start = time.perf_counter()
    bank_arrivals = _generate_bank(fixed, manifest.bank_seeds)
    bank_runtime = time.perf_counter() - bank_start
    sites = tuple(sorted(fixed.design.sites, key=lambda value: value.site_id))
    models = tuple(
        (
            truth,
            build_arrival_integration(
                bank_arrivals,
                tuple(site.site_id for site in sites),
                tuple(sorted(set((*config.effect_grid, truth.effect_multiplier)))),
                truth.background_hazard,
            ),
        )
        for truth in config.truths
    )
    calibration_start = time.perf_counter()
    calibration_tasks = tuple(
        (fixed, seed, config.truths, models, config) for seed in manifest.calibration
    )
    if workers == 1:
        calibration_blocks = tuple(_calibration_task(task) for task in calibration_tasks)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            calibration_blocks = tuple(executor.map(_calibration_task, calibration_tasks))
    calibration_rows = tuple(row for block in calibration_blocks for row in block)
    calibration_runtime = time.perf_counter() - calibration_start
    cutoffs = {
        truth.condition_id: order_statistic_cutoff(
            [
                row.likelihood_ratio_at_truth
                for row in calibration_rows
                if row.condition_id == truth.condition_id
            ],
            rank_one_based=config.calibration_rank_one_based,
        ).cutoff
        for truth in config.truths
    }
    validation_start = time.perf_counter()
    validation_tasks = tuple(
        (fixed, seed, config.truths, models, config, cutoffs) for seed in manifest.validation
    )
    if workers == 1:
        validation_blocks = tuple(_validation_task(task) for task in validation_tasks)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            validation_blocks = tuple(executor.map(_validation_task, validation_tasks))
    validation_rows = tuple(row for block in validation_blocks for row in block)
    validation_runtime = time.perf_counter() - validation_start
    summaries: list[TruthSummary] = []
    for truth in config.truths:
        selected = tuple(row for row in validation_rows if row.condition_id == truth.condition_id)
        covered = sum(row.truth_included for row in selected)
        coverage = wilson_interval(covered, len(selected))
        connected = sum(
            row.support_component_count == 1
            and (truth.design_role == "neutral_control" or not row.support_boundary_contact)
            for row in selected
        )
        null_count = sum(row.no_effect_excluded for row in selected)
        known_background_score_interval = normal_mean_interval(
            [row.heldout_known_background_no_effect_advantage_per_record for row in selected]
        )
        fitted_neutral_score_interval = normal_mean_interval(
            [row.heldout_fitted_neutral_advantage_per_record for row in selected]
        )
        median_error = median(row.absolute_log_effect_error for row in selected)
        median_width = median(row.log_support_width for row in selected)
        diagnostics = tuple(
            fmean(getattr(row, field) for row in selected)
            for field in (
                "true_extirpations_by_day60",
                "pre_arrival_true_extirpations",
                "post_arrival_true_extirpations",
                "true_extirpation_censoring",
                "post_arrival_at_risk_exposure",
                "prey_observation_support",
            )
        )
        summaries.append(
            TruthSummary(
                condition_id=truth.condition_id,
                design_role=truth.design_role,
                truth_effect_multiplier=truth.effect_multiplier,
                truth_background_risk=truth.background_risk,
                truth_prey_detection_probability=truth.prey_detection_probability,
                cutoff=cutoffs[truth.condition_id],
                validation_count=len(selected),
                coverage=coverage.estimate,
                coverage_lower=coverage.lower,
                coverage_upper=coverage.upper,
                connected_interior_frequency=connected / len(selected),
                no_effect_exclusion_probability=null_count / len(selected),
                median_absolute_log_effect_error=median_error,
                median_log_support_width=median_width,
                mean_heldout_known_background_no_effect_advantage_per_record=fmean(
                    row.heldout_known_background_no_effect_advantage_per_record for row in selected
                ),
                heldout_known_background_no_effect_advantage_lower=known_background_score_interval.lower,
                heldout_known_background_no_effect_advantage_upper=known_background_score_interval.upper,
                mean_heldout_fitted_neutral_advantage_per_record=fmean(
                    row.heldout_fitted_neutral_advantage_per_record for row in selected
                ),
                heldout_fitted_neutral_advantage_lower=fitted_neutral_score_interval.lower,
                heldout_fitted_neutral_advantage_upper=fitted_neutral_score_interval.upper,
                mean_true_extirpations_by_day60=diagnostics[0],
                mean_pre_arrival_true_extirpations=diagnostics[1],
                mean_post_arrival_true_extirpations=diagnostics[2],
                mean_true_extirpation_censoring=diagnostics[3],
                mean_post_arrival_at_risk_exposure=diagnostics[4],
                mean_prey_observation_support=diagnostics[5],
                failure_classification=_classify_truth(
                    truth,
                    coverage=coverage,
                    connected=connected,
                    null_count=null_count,
                    count=len(selected),
                    error=median_error,
                    width=median_width,
                    score_interval=known_background_score_interval,
                ),
            )
        )
    invariants = {
        "fixed_inputs_reconciled": all(fixed.invariants.values()),
        "truth_count": len(config.truths)
        == (
            18
            if config.production_block == "pilot"
            else 16
            if config.production_block == "prospective"
            else len(config.truths)
        ),
        "shared_bank_shape": bank_arrivals.shape == (config.bank_size, len(sites)),
        "paired_calibration_count": len(calibration_rows)
        == len(config.truths) * config.calibration_replicates,
        "paired_validation_count": len(validation_rows)
        == len(config.truths) * config.validation_replicates,
        "phase_roots_disjoint": not (
            {
                (s.process_seed, s.predator_detection_seed, s.prey_seed, s.prey_detection_seed)
                for s in manifest.calibration
            }
            & {
                (s.process_seed, s.predator_detection_seed, s.prey_seed, s.prey_detection_seed)
                for s in manifest.validation
            }
        ),
        "finite_metrics": all(
            math.isfinite(value)
            for row in validation_rows
            for value in (
                row.mle_effect_multiplier,
                row.absolute_log_effect_error,
                row.log_support_width,
                row.heldout_known_background_no_effect_advantage_per_record,
                row.heldout_fitted_neutral_advantage_per_record,
            )
        ),
        "history_shape": all(
            _histories_valid(
                generate_paired_datasets(fixed, manifest.validation[0], (truth,), config)[0].records
            )
            for truth in config.truths[:1]
        ),
    }
    controls_valid = all(
        row.failure_classification in {"reference_control_valid", "neutral_control_valid"}
        for row in summaries
        if row.design_role in {"reference_control", "neutral_control"}
    )
    outcome = (
        "control_review_required"
        if all(invariants.values()) and config.production_block == "pilot" and not controls_valid
        else "ready_for_arc2b_synthesis"
        if all(invariants.values()) and config.production_block
        else "non_scientific_smoke"
        if all(invariants.values())
        else "implementation_blocked"
    )
    return CampaignResult(
        config,
        manifest,
        tuple(calibration_rows),
        tuple(validation_rows),
        tuple(summaries),
        invariants,
        outcome,
        workers,
        time.perf_counter() - started,
        bank_runtime,
        calibration_runtime,
        validation_runtime,
        source_commit,
        hashlib.sha256(np.ascontiguousarray(bank_arrivals).tobytes()).hexdigest(),
        frozen_predictions_sha256,
    )


def current_git_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, check=True, text=True
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip()


def _write_csv(path: Path, rows: tuple[Any, ...]) -> None:
    if not rows:
        raise ValueError("rows must not be empty")
    payload = [asdict(row) for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]))
        writer.writeheader()
        writer.writerows(payload)


def _calibration_summaries(result: CampaignResult) -> tuple[CalibrationSummary, ...]:
    rows: list[CalibrationSummary] = []
    for truth in result.config.truths:
        selected = tuple(
            row for row in result.calibration_statistics if row.condition_id == truth.condition_id
        )
        values = [row.likelihood_ratio_at_truth for row in selected]
        cutoff = order_statistic_cutoff(
            values, rank_one_based=result.config.calibration_rank_one_based
        ).cutoff
        rows.append(
            CalibrationSummary(
                truth.condition_id,
                len(selected),
                cutoff,
                median(values),
                fmean(row.true_extirpations_by_day60 for row in selected),
                fmean(row.predator_detected_visit_count for row in selected),
                fmean(row.prey_detected_visit_count for row in selected),
            )
        )
    return tuple(rows)


def write_review_bundle(result: CampaignResult, output_dir: Path) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "truth_design.csv", tuple(result.config.truths))
    _write_csv(output_dir / "calibration_statistics.csv", result.calibration_statistics)
    _write_csv(output_dir / "calibration_condition_summaries.csv", _calibration_summaries(result))
    _write_csv(output_dir / "validation_metrics.csv", result.validation_metrics)
    _write_csv(output_dir / "validation_condition_summaries.csv", result.truth_summaries)
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "workflow": "arc2b-prey-effect-recoverability-campaign",
                "outcome": result.outcome,
                "run_mode": result.config.production_block or "reduced_smoke",
                "truth_summaries": [asdict(row) for row in result.truth_summaries],
                "invariants": result.invariants,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "seed_provenance.json").write_text(
        json.dumps(
            {
                "master_seed": result.config.master_seed,
                "bank_size": result.config.bank_size,
                "bank_checksum": result.bank_checksum,
                "frozen_predictions_sha256": result.frozen_predictions_sha256,
                "calibration_validation_roots_disjoint": True,
                "calibration_seeds": [asdict(row) for row in result.seed_manifest.calibration],
                "validation_seeds": [asdict(row) for row in result.seed_manifest.validation],
                "source_commit": result.source_commit,
                "completed_utc": datetime.now(UTC).isoformat(),
                "runtime_seconds": result.runtime_seconds,
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "review.md").write_text(
        "# Arc 2B campaign\n\n"
        + (
            "Implementation check only; no scientific interpretation.\n"
            if not result.config.production_block
            else (
                f"Completed {len(result.config.truths)} conditions with paired "
                "calibration and validation histories.\n"
            )
        ),
        encoding="utf-8",
    )
    return tuple(output_dir / name for name in EXPECTED_FILES)
