"""Cross-rate one-rate recovery benchmark built on the frozen Goal 004 core.

This module deliberately keeps the Goal 004 likelihood and observation model
unchanged. It adds only truth-rate orchestration, local versus transported
cutoffs, and compact diagnostics.
"""

from __future__ import annotations

import hashlib
import subprocess
from collections import Counter
from dataclasses import dataclass, replace
from math import ceil, isfinite, log
from pathlib import Path
from statistics import fmean
from typing import cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal001.design import SamplingDesign, build_design, spawn_generators
from latent_landscapes.goal001.landscape import Landscape, build_landscape
from latent_landscapes.goal001.observations import Observation
from latent_landscapes.goal001.spread import passable_edges
from latent_landscapes.goal002.baseline import (
    BaselineScore,
    fit_time_stratified_baseline,
    score_time_stratified_baseline,
)
from latent_landscapes.goal002.calibration import (
    EstimateInterval,
    normal_mean_interval,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal003.spread import StochasticSpreadTruth, compute_stochastic_spread
from latent_landscapes.goal004 import benchmark as g4
from latent_landscapes.goal004.likelihood import (
    GridProfile,
    GridProfileSummary,
    PredictiveScore,
    category_weights,
    profile_from_history_probabilities,
    rate_grid,
    record_detection_probabilities,
    score_predictions,
    site_history_probabilities,
    summarize_profile,
)
from latent_landscapes.goal004.observations import (
    DETECTION_PROBABILITY,
    SURVEY_TIMES,
    generate_observations,
)

MASTER_SEED = 20260729
INTEGRATION_BANK_SIZE = 4096
HALF_BANK_SIZE = 2048
CALIBRATION_REPLICATES = 500
VALIDATION_REPLICATES = 500
CALIBRATION_RANK_ONE_BASED = 476
TRUTH_RATES = (0.5, 1.0, 2.0)
BANK_VARIANT_NAMES = ("full", "first_half", "second_half")
FROZEN_RATE_GRID = tuple(float(value) for value in rate_grid())
STATE_WORD_COUNT = 4
SOURCE_IDENTITY = {
    "repository_commit": "3d4909d063fc3ae39aa96502de4e10d78f98e07c",
    "goal001_landscape_blob": "a376df359e09b2357a0b5262479bcebaeee2ff25",
    "goal001_design_blob": "ca9c60d3f113fcde48985395652974337421dfa7",
    "goal002_neutral_baseline_blob": "f4aec0393fbba8b70b5ac6321898cde09256fd75",
    "goal003_stochastic_spread_blob": "d20440415ea33cee0f64f41427ae81197ca8fd9e",
    "goal004_observations_blob": "c97938ab640700a6584e84cc2ed8be164b582b3c",
    "goal004_likelihood_blob": "b427bdfd25e2747ca69e2272e1be2df93aa6f49e",
    "goal004_benchmark_blob": "92b5f91d7f47882c2da4b44f00f82448c44fa826",
}
PINNED_SOURCE_PATHS = {
    "goal001_landscape_blob": "src/latent_landscapes/goal001/landscape.py",
    "goal001_design_blob": "src/latent_landscapes/goal001/design.py",
    "goal002_neutral_baseline_blob": "src/latent_landscapes/goal002/baseline.py",
    "goal003_stochastic_spread_blob": "src/latent_landscapes/goal003/spread.py",
    "goal004_observations_blob": "src/latent_landscapes/goal004/observations.py",
    "goal004_likelihood_blob": "src/latent_landscapes/goal004/likelihood.py",
    "goal004_benchmark_blob": "src/latent_landscapes/goal004/benchmark.py",
}

FROZEN_CENTRAL = {
    "full": (
        52.43798271483206,
        468,
        0.911047591162316,
        0.9543039839552107,
        -0.04783902279292768,
        -0.04857410235067318,
        -0.047103943235182175,
    ),
    "first_half": (
        51.461724484605156,
        467,
        0.9087605988391466,
        0.9526214736402262,
        -0.047825381384070616,
        -0.048559386695618344,
        -0.04709137607252289,
    ),
    "second_half": (
        53.317375493515556,
        468,
        0.911047591162316,
        0.9543039839552107,
        -0.04784530122207121,
        -0.048580435689708955,
        -0.04711016675443346,
    ),
}


@dataclass(frozen=True, slots=True)
class Goal005Config:
    master_seed: int = MASTER_SEED
    bank_size: int = INTEGRATION_BANK_SIZE
    calibration_replicates: int = CALIBRATION_REPLICATES
    validation_replicates: int = VALIDATION_REPLICATES
    calibration_rank_one_based: int = CALIBRATION_RANK_ONE_BASED
    truth_rates: tuple[float, ...] = TRUTH_RATES
    rates: tuple[float, ...] = FROZEN_RATE_GRID

    def __post_init__(self) -> None:
        if self.bank_size < 2 or self.bank_size % 2:
            raise ValueError("bank size must be positive and even")
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank is outside the ensemble")
        if tuple(self.truth_rates) != TRUTH_RATES:
            raise ValueError("Goal 005 truth rates are frozen at 0.5, 1, and 2")
        values = np.asarray(self.rates, dtype=np.float64)
        if (
            len(values) == 0
            or not np.isfinite(values).all()
            or (values <= 0).any()
            or (np.diff(values) <= 0).any()
        ):
            raise ValueError("rates must be finite, positive, and increasing")
        if tuple(values) != tuple(np.asarray(FROZEN_RATE_GRID)):
            raise ValueError("Goal 004 rate grid is frozen")

    @property
    def half_bank_size(self) -> int:
        return self.bank_size // 2

    @property
    def truth_indices(self) -> tuple[int, ...]:
        return tuple(self.rates.index(rate) for rate in self.truth_rates)

    @property
    def is_production(self) -> bool:
        return self == DEFAULT_CONFIG


DEFAULT_CONFIG = Goal005Config()


@dataclass(frozen=True, slots=True)
class SeedRecord:
    phase: str
    index: int
    stream_role: str
    entropy: int
    spawn_key: tuple[int, ...]
    state_words: tuple[int, ...]
    pool_size: int


@dataclass(frozen=True, slots=True)
class DatasetSeeds:
    phase: str
    truth_rate: float
    index: int
    process: SeedRecord
    detection: SeedRecord


@dataclass(frozen=True, slots=True)
class SeedManifest:
    integration_bank: tuple[SeedRecord, ...]
    datasets: tuple[DatasetSeeds, ...]

    @property
    def stream_records(self) -> tuple[SeedRecord, ...]:
        return (
            *self.integration_bank,
            *(s for d in self.datasets for s in (d.process, d.detection)),
        )


@dataclass(frozen=True, slots=True)
class FixedInputs:
    landscape: Landscape
    design: SamplingDesign
    invariants: dict[str, bool]


@dataclass(frozen=True, slots=True)
class IntegrationBank:
    site_ids: tuple[str, ...]
    arrivals: NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class BankVariant:
    name: str
    draw_start: int
    draw_end: int
    weights_by_truth: dict[float, NDArray[np.float64]]

    @property
    def draw_count(self) -> int:
        return self.draw_end - self.draw_start


@dataclass(frozen=True, slots=True)
class CalibrationRow:
    truth_rate: float
    dataset_index: int
    bank_variant: str
    record_count: int
    truth_grid_index: int
    lr_at_truth: float
    truth_log_likelihood: float
    maximum_log_likelihood: float
    mle_indices: tuple[int, ...]
    mle_rates: tuple[float, ...]
    occupied_fraction_mean: float
    occupied_fraction_lower: float
    occupied_fraction_upper: float
    detection_fraction_mean: float
    detection_fraction_lower: float
    detection_fraction_upper: float
    no_false_positives: bool


@dataclass(frozen=True, slots=True)
class ValidationRow:
    truth_rate: float
    cutoff_source_rate: float
    dataset_index: int
    bank_variant: str
    record_count: int
    training_record_count: int
    holdout_record_count: int
    split_isolated: bool
    truth_grid_index: int
    lr_at_truth: float
    truth_included: bool
    support_component_count: int
    support_boundary_contact: bool
    support_arithmetic_width: float
    support_log_rate_width: float
    support_indices: tuple[int, ...]
    mle_indices: tuple[int, ...]
    mle_rates: tuple[float, ...]
    truth_to_mle_set_distance: float
    absolute_log_rate_error: float
    training_mle_indices: tuple[int, ...]
    training_mle_rates: tuple[float, ...]
    stochastic_brier_maximum: float
    neutral_brier_score: float
    stochastic_log_score_maximum: float
    neutral_log_score: float
    paired_brier_difference: float
    occupied_fraction_mean: float
    occupied_fraction_lower: float
    occupied_fraction_upper: float
    detection_fraction_mean: float
    detection_fraction_lower: float
    detection_fraction_upper: float
    no_false_positives: bool
    transported: bool


@dataclass(frozen=True, slots=True)
class CutoffSummary:
    truth_rate: float
    bank_variant: str
    cutoff_source_rate: float
    cutoff: float
    coverage_count: int
    coverage: EstimateInterval
    topology_count: int
    boundary_contacts: int
    mean_arithmetic_width: float
    mean_log_rate_width: float
    mean_abs_log_error: float
    paired_brier: EstimateInterval
    downstream_class: str
    transported: bool


@dataclass(frozen=True, slots=True)
class RepresentativeProfile:
    truth_rate: float
    bank_variant: str
    cutoff_source_rate: float
    cutoff: float
    profile: GridProfile
    summary: GridProfileSummary


@dataclass(frozen=True, slots=True)
class ObservationSignalSummary:
    truth_rate: float
    survey_time: int
    occupied_fraction_mean: float
    occupied_fraction_lower: float
    occupied_fraction_upper: float
    detection_fraction_mean: float
    detection_fraction_lower: float
    detection_fraction_upper: float


@dataclass(frozen=True, slots=True)
class Goal005Result:
    config: Goal005Config
    fixed_inputs: FixedInputs
    seed_manifest: SeedManifest
    integration_bank: IntegrationBank
    bank_variants: tuple[BankVariant, ...]
    calibration_results: tuple[CalibrationRow, ...]
    validation_results: tuple[ValidationRow, ...]
    cutoff_summaries: tuple[CutoffSummary, ...]
    representative_profiles: tuple[RepresentativeProfile, ...]
    observation_signals: tuple[ObservationSignalSummary, ...]
    invariants: dict[str, bool]
    outcome: str
    central_reconciliation: dict[str, bool]


def _record(phase: str, index: int, role: str, seq: np.random.SeedSequence) -> SeedRecord:
    return SeedRecord(
        phase,
        index,
        role,
        int(cast(int, seq.entropy)),
        tuple(map(int, seq.spawn_key)),
        tuple(map(int, seq.generate_state(STATE_WORD_COUNT))),
        seq.pool_size,
    )


def _generator(record: SeedRecord) -> np.random.Generator:
    seq = np.random.SeedSequence(
        record.entropy, spawn_key=record.spawn_key, pool_size=record.pool_size
    )
    if tuple(map(int, seq.generate_state(len(record.state_words)))) != record.state_words:
        raise ValueError("seed record state does not replay")
    return np.random.Generator(np.random.PCG64(seq))


def spawn_seed_manifest(config: Goal005Config = DEFAULT_CONFIG) -> SeedManifest:
    central_roots = np.random.SeedSequence(g4.MASTER_SEED).spawn(3)
    integration = tuple(
        _record("integration_bank", i, "process", child)
        for i, child in enumerate(central_roots[0].spawn(config.bank_size))
    )
    central = []
    for phase, root, truth in (
        ("calibration", central_roots[1], 1.0),
        ("validation", central_roots[2], 1.0),
    ):
        for i, child in enumerate(
            root.spawn(
                config.calibration_replicates
                if phase == "calibration"
                else config.validation_replicates
            )
        ):
            process, detection = child.spawn(2)
            central.append(
                DatasetSeeds(
                    phase,
                    truth,
                    i,
                    _record(phase, i, "process", process),
                    _record(phase, i, "detection", detection),
                )
            )
    flank_root = np.random.SeedSequence(config.master_seed).spawn(4)
    for phase, truth, root in (
        ("rho_0_5_calibration", 0.5, flank_root[0]),
        ("rho_0_5_validation", 0.5, flank_root[1]),
        ("rho_2_calibration", 2.0, flank_root[2]),
        ("rho_2_validation", 2.0, flank_root[3]),
    ):
        for i, child in enumerate(
            root.spawn(
                config.calibration_replicates
                if "calibration" in phase
                else config.validation_replicates
            )
        ):
            process, detection = child.spawn(2)
            central.append(
                DatasetSeeds(
                    phase,
                    truth,
                    i,
                    _record(phase, i, "process", process),
                    _record(phase, i, "detection", detection),
                )
            )
    return SeedManifest(integration, tuple(central))


def build_fixed_inputs() -> FixedInputs:
    landscape = build_landscape()
    centre_rng, holdout_rng, _ = spawn_generators()
    design = build_design(landscape, centre_rng, holdout_rng)
    clusters = Counter(c.split for c in design.clusters)
    root = Path(__file__).resolve().parents[1].parents[1]
    parent_ok = _git_commit_is_ancestor(root, SOURCE_IDENTITY["repository_commit"])
    parent_blobs = all(
        _git_commit_blob_sha(root, SOURCE_IDENTITY["repository_commit"], p) == SOURCE_IDENTITY[k]
        for k, p in PINNED_SOURCE_PATHS.items()
    )
    runtime_blobs = all(
        _git_blob_sha(
            Path(__file__).resolve().parents[1] / Path(path).relative_to("src/latent_landscapes")
        )
        == SOURCE_IDENTITY[key]
        for key, path in PINNED_SOURCE_PATHS.items()
        if key != "goal004_benchmark_blob"
    )
    invariants = {
        "frozen_repository_commit_reconciled": parent_ok,
        "frozen_parent_source_blobs_reconciled": parent_blobs,
        "frozen_runtime_source_blobs_reconciled": runtime_blobs,
        "landscape_counts": landscape.shape == (72, 84)
        and int(landscape.passable.sum()) == 5225
        and int((~landscape.passable).sum()) == 823,
        "graph_edge_count": len(passable_edges(landscape)) == 10120,
        "design_counts": len(design.clusters) == 32
        and len(design.sites) == 160
        and clusters == {"training": 24, "holdout": 8},
        "survey_calendar": SURVEY_TIMES == (10, 20, 30, 40, 50, 60),
        "detection_probability": DETECTION_PROBABILITY == 0.65,
    }
    invariants["frozen_source_blobs_reconciled"] = parent_ok and parent_blobs and runtime_blobs
    return FixedInputs(landscape, design, invariants)


def build_integration_bank(fixed: FixedInputs, records: tuple[SeedRecord, ...]) -> IntegrationBank:
    sites = fixed.design.sites
    rows = np.asarray([s.row for s in sites], dtype=np.int64)
    cols = np.asarray([s.col for s in sites], dtype=np.int64)
    arrivals = np.empty((len(records), len(sites)), dtype=np.float64)
    for r in records:
        truth = compute_stochastic_spread(fixed.landscape, _generator(r), rho=1.0)
        arrivals[r.index] = truth.arrival[rows, cols]
    return IntegrationBank(tuple(s.site_id for s in sites), arrivals)


def build_bank_variants(config: Goal005Config, bank: IntegrationBank) -> tuple[BankVariant, ...]:
    ranges = (
        ("full", 0, config.bank_size),
        ("first_half", 0, config.half_bank_size),
        ("second_half", config.half_bank_size, config.bank_size),
    )
    # The integration bank stores the rho=1 base fields. Candidate rate
    # scaling is applied inside category_weights through the candidate grid;
    # the same weights therefore serve every generating truth rate.
    return tuple(
        BankVariant(
            n,
            a,
            b,
            {
                truth: category_weights(bank.arrivals[a:b], np.asarray(config.rates))
                for truth in config.truth_rates
            },
        )
        for n, a, b in ranges
    )


def _dataset(
    fixed: FixedInputs, seed: DatasetSeeds
) -> tuple[StochasticSpreadTruth, tuple[Observation, ...]]:
    truth = compute_stochastic_spread(
        fixed.landscape, _generator(seed.process), rho=seed.truth_rate
    )
    return truth, generate_observations(fixed.design.sites, truth, _generator(seed.detection))


def _signal(
    records: tuple[Observation, ...], truth: StochasticSpreadTruth
) -> tuple[float, float, float, float, float, float]:
    occupied = [float(truth.arrival[r.row, r.col] <= r.time) for r in records]
    detected = [float(r.detected) for r in records]

    def bounds(values: list[float]) -> tuple[float, float, float]:
        return (
            float(np.mean(values)),
            float(np.quantile(values, 0.05)),
            float(np.quantile(values, 0.95)),
        )

    o = bounds(occupied)
    d = bounds(detected)
    return (*o, *d)


def _profile(
    variant: BankVariant,
    truth: float,
    config: Goal005Config,
    site_ids: tuple[str, ...],
    records: tuple[Observation, ...],
    scope: str,
) -> GridProfile:
    ids, histories = site_history_probabilities(site_ids=site_ids, records=records)
    return profile_from_history_probabilities(
        weights=variant.weights_by_truth[truth],
        rates=np.asarray(config.rates),
        bank_site_ids=site_ids,
        history_site_ids=ids,
        history_probabilities=histories,
        scope=scope,
    )


def _predictive(
    variant: BankVariant,
    truth: float,
    config: Goal005Config,
    site_ids: tuple[str, ...],
    train: tuple[Observation, ...],
    holdout: tuple[Observation, ...],
) -> tuple[PredictiveScore, BaselineScore]:
    train_profile = _profile(variant, truth, config, site_ids, train, "training")
    scores = tuple(
        score_predictions(
            record_detection_probabilities(
                weights=variant.weights_by_truth[truth][i], site_ids=site_ids, records=holdout
            ),
            holdout,
        )
        for i in train_profile.mle_indices
    )
    neutral = fit_time_stratified_baseline(train, survey_times=SURVEY_TIMES)
    ns = score_time_stratified_baseline(neutral, holdout)
    return max(scores, key=lambda s: s.mean_brier_score), ns


def run_goal005(
    config: Goal005Config = DEFAULT_CONFIG, fixed_inputs: FixedInputs | None = None
) -> Goal005Result:
    fixed = fixed_inputs or build_fixed_inputs()
    manifest = spawn_seed_manifest(config)
    bank = build_integration_bank(fixed, manifest.integration_bank)
    variants = build_bank_variants(config, bank)
    calibration: list[CalibrationRow] = []
    validation: list[ValidationRow] = []
    representatives: list[RepresentativeProfile] = []
    signal_values: dict[tuple[float, int], list[tuple[float, float]]] = {}
    truth_index = dict(zip(config.truth_rates, config.truth_indices, strict=True))
    for seed in manifest.datasets:
        truth_obj, obs = _dataset(fixed, seed)
        signal = _signal(obs, truth_obj)
        if "validation" in seed.phase:
            for survey_time in SURVEY_TIMES:
                sites_at_time = {
                    record.site_id: record for record in obs if record.time == survey_time
                }
                occupied_fraction = float(
                    np.mean(
                        [
                            truth_obj.arrival[record.row, record.col] <= survey_time
                            for record in sites_at_time.values()
                        ]
                    )
                )
                all_records_at_time = [record for record in obs if record.time == survey_time]
                detection_fraction = float(
                    np.mean([record.detected for record in all_records_at_time])
                )
                signal_values.setdefault((seed.truth_rate, survey_time), []).append(
                    (occupied_fraction, detection_fraction)
                )
        for variant in variants:
            profile = _profile(variant, seed.truth_rate, config, bank.site_ids, obs, seed.phase)
            idx = truth_index[seed.truth_rate]
            calibration.append(
                CalibrationRow(
                    seed.truth_rate,
                    seed.index,
                    variant.name,
                    len(obs),
                    idx,
                    max(0.0, 2 * (profile.maximum_log_likelihood - profile.log_likelihoods[idx])),
                    float(profile.log_likelihoods[idx]),
                    profile.maximum_log_likelihood,
                    profile.mle_indices,
                    profile.mle_rates,
                    *signal,
                    True,
                )
            ) if "calibration" in seed.phase else None
            if "validation" in seed.phase:
                train = tuple(r for r in obs if r.split == "training")
                holdout = tuple(r for r in obs if r.split == "holdout")
                # Cutoffs are calculated after all calibration rows below.
                train_profile = _profile(
                    variant, seed.truth_rate, config, bank.site_ids, train, "training"
                )
                neutral = fit_time_stratified_baseline(train, survey_times=SURVEY_TIMES)
                neutral_score = score_time_stratified_baseline(neutral, holdout)
                stochastic_scores = tuple(
                    score_predictions(
                        record_detection_probabilities(
                            weights=variant.weights_by_truth[seed.truth_rate][i],
                            site_ids=bank.site_ids,
                            records=holdout,
                        ),
                        holdout,
                    )
                    for i in train_profile.mle_indices
                )
                # Temporary support is filled after calibration cutoffs are known.
                validation.append(
                    ValidationRow(
                        seed.truth_rate,
                        seed.truth_rate,
                        seed.index,
                        variant.name,
                        len(obs),
                        len(train),
                        len(holdout),
                        {r.cluster_id for r in train}.isdisjoint({r.cluster_id for r in holdout}),
                        idx,
                        max(
                            0.0, 2 * (profile.maximum_log_likelihood - profile.log_likelihoods[idx])
                        ),
                        False,
                        0,
                        False,
                        0.0,
                        0.0,
                        (),
                        profile.mle_indices,
                        profile.mle_rates,
                        min(abs(r - seed.truth_rate) for r in profile.mle_rates),
                        min(abs(log(r) - log(seed.truth_rate)) for r in profile.mle_rates),
                        train_profile.mle_indices,
                        train_profile.mle_rates,
                        max(s.mean_brier_score for s in stochastic_scores),
                        neutral_score.mean_brier_score,
                        max(s.total_log_score for s in stochastic_scores),
                        neutral_score.total_log_score,
                        max(s.mean_brier_score for s in stochastic_scores)
                        - neutral_score.mean_brier_score,
                        *signal,
                        True,
                        False,
                    )
                )
    calibration_by = {
        (r.truth_rate, r.bank_variant): tuple(
            x.lr_at_truth
            for x in calibration
            if x.truth_rate == r.truth_rate and x.bank_variant == r.bank_variant
        )
        for r in calibration
    }
    local_cutoffs = {
        (truth, name): order_statistic_cutoff(
            vals, rank_one_based=config.calibration_rank_one_based
        ).cutoff
        for truth, name, vals in (
            (t, n, calibration_by[(t, n)]) for t in config.truth_rates for n in BANK_VARIANT_NAMES
        )
    }
    transport = {name: local_cutoffs[(1.0, name)] for name in BANK_VARIANT_NAMES}
    updated: list[ValidationRow] = []
    for row in validation:
        truth_obj, obs = _dataset(
            fixed,
            next(
                s
                for s in manifest.datasets
                if s.truth_rate == row.truth_rate
                and s.phase.endswith("validation")
                and s.index == row.dataset_index
            ),
        )
        variant = next(v for v in variants if v.name == row.bank_variant)
        profile = _profile(variant, row.truth_rate, config, bank.site_ids, obs, "all")
        cutoff = local_cutoffs[(row.truth_rate, row.bank_variant)]
        summary = summarize_profile(profile, cutoff=cutoff, truth_rate=row.truth_rate)
        updated.append(
            replace(
                row,
                truth_included=summary.truth_included,
                support_component_count=len(summary.support_components),
                support_boundary_contact=summary.support_boundary_contact,
                support_arithmetic_width=summary.support_arithmetic_width,
                support_log_rate_width=summary.support_log_rate_width,
                support_indices=summary.support_indices,
            )
        )
    validation = updated
    representatives = []
    for truth in config.truth_rates:
        seed0 = next(
            s
            for s in manifest.datasets
            if s.truth_rate == truth and s.phase.endswith("validation") and s.index == 0
        )
        _, obs0 = _dataset(fixed, seed0)
        for variant in variants:
            profile0 = _profile(variant, truth, config, bank.site_ids, obs0, "all")
            cutoff0 = local_cutoffs[(truth, variant.name)]
            summary0 = summarize_profile(profile0, cutoff=cutoff0, truth_rate=truth)
            representatives.append(
                RepresentativeProfile(truth, variant.name, truth, cutoff0, profile0, summary0)
            )
    observation_signals = tuple(
        ObservationSignalSummary(
            truth_rate=truth,
            survey_time=survey_time,
            occupied_fraction_mean=float(np.mean([pair[0] for pair in pairs])),
            occupied_fraction_lower=float(np.quantile([pair[0] for pair in pairs], 0.05)),
            occupied_fraction_upper=float(np.quantile([pair[0] for pair in pairs], 0.95)),
            detection_fraction_mean=float(np.mean([pair[1] for pair in pairs])),
            detection_fraction_lower=float(np.quantile([pair[1] for pair in pairs], 0.05)),
            detection_fraction_upper=float(np.quantile([pair[1] for pair in pairs], 0.95)),
        )
        for (truth, survey_time), pairs in sorted(signal_values.items())
    )
    summaries: list[CutoffSummary] = []
    for truth in config.truth_rates:
        for name in BANK_VARIANT_NAMES:
            rows = tuple(r for r in validation if r.truth_rate == truth and r.bank_variant == name)
            vals = tuple(r.paired_brier_difference for r in rows)
            cov = wilson_interval(sum(r.truth_included for r in rows), len(rows))
            topology = sum(
                r.support_component_count == 1 and not r.support_boundary_contact for r in rows
            )
            summaries.append(
                CutoffSummary(
                    truth,
                    name,
                    truth,
                    local_cutoffs[(truth, name)],
                    sum(r.truth_included for r in rows),
                    cov,
                    topology,
                    sum(r.support_boundary_contact for r in rows),
                    fmean(r.support_arithmetic_width for r in rows),
                    fmean(r.support_log_rate_width for r in rows),
                    fmean(r.absolute_log_rate_error for r in rows),
                    normal_mean_interval(vals),
                    classify_downstream(topology, len(rows), cov, normal_mean_interval(vals)),
                    False,
                )
            )
            if truth != 1.0:
                tr_rows = []
                for row in rows:
                    truth_obj, obs = _dataset(
                        fixed,
                        next(
                            s
                            for s in manifest.datasets
                            if s.truth_rate == row.truth_rate
                            and s.phase.endswith("validation")
                            and s.index == row.dataset_index
                        ),
                    )
                    profile = _profile(
                        next(v for v in variants if v.name == name),
                        truth,
                        config,
                        bank.site_ids,
                        obs,
                        "all",
                    )
                    sm = summarize_profile(profile, cutoff=transport[name], truth_rate=truth)
                    tr_rows.append((row, sm))
                tv = tuple(r for r, s in tr_rows)
                cov2 = wilson_interval(sum(s.truth_included for r, s in tr_rows), len(tv))
                top2 = sum(
                    len(s.support_components) == 1 and not s.support_boundary_contact
                    for r, s in tr_rows
                )
                summaries.append(
                    CutoffSummary(
                        truth,
                        name,
                        1.0,
                        transport[name],
                        sum(s.truth_included for r, s in tr_rows),
                        cov2,
                        top2,
                        sum(s.support_boundary_contact for r, s in tr_rows),
                        fmean(s.support_arithmetic_width for r, s in tr_rows),
                        fmean(s.support_log_rate_width for r, s in tr_rows),
                        fmean(r.absolute_log_rate_error for r, s in tr_rows),
                        normal_mean_interval(tuple(r.paired_brier_difference for r, s in tr_rows)),
                        "transport_diagnostic",
                        True,
                    )
                )
    central = _central_reconciliation(summaries, config)
    invariants = _evaluate_invariants(
        config, fixed, manifest, bank, variants, calibration, validation, central
    )
    outcome = classify_outcome(invariants, tuple(summaries))
    return Goal005Result(
        config,
        fixed,
        manifest,
        bank,
        variants,
        tuple(calibration),
        tuple(validation),
        tuple(summaries),
        tuple(representatives),
        observation_signals,
        invariants,
        outcome,
        central,
    )


def classify_downstream(
    topology_success_count: int,
    validation_count: int,
    calibrated_coverage: EstimateInterval,
    paired_brier_interval: EstimateInterval,
) -> str:
    if validation_count <= 0 or topology_success_count < ceil(0.95 * validation_count):
        return "one_rate_design_limited"
    if not calibrated_coverage.lower <= 0.95 <= calibrated_coverage.upper:
        return "one_rate_local_calibration_not_ready"
    if paired_brier_interval.lower > 0:
        return "one_rate_recoverable_neutral_better"
    if paired_brier_interval.upper < 0:
        return "advance_to_second_spread_parameter"
    return "one_rate_recoverable_mechanism_inconclusive"


def classify_outcome(invariants: dict[str, bool], summaries: tuple[CutoffSummary, ...]) -> str:
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    local = {
        (s.truth_rate, s.bank_variant): s.downstream_class for s in summaries if not s.transported
    }
    if any((t, n) not in local for t in TRUTH_RATES for n in BANK_VARIANT_NAMES):
        return "likelihood_approximation_unstable"
    if any(len({local[(t, n)] for n in BANK_VARIANT_NAMES}) != 1 for t in TRUTH_RATES):
        return "likelihood_approximation_unstable"
    if any(
        s.downstream_class == "one_rate_design_limited"
        for s in summaries
        if not s.transported and s.bank_variant == "full"
    ):
        return "one_rate_design_limited"
    if any(
        s.downstream_class == "one_rate_local_calibration_not_ready"
        for s in summaries
        if not s.transported and s.bank_variant == "full"
    ):
        return "one_rate_local_calibration_not_ready"
    if any(
        s.paired_brier.lower > 0
        for s in summaries
        if not s.transported and s.bank_variant == "full"
    ):
        return "one_rate_recoverable_neutral_better"
    if any(
        s.paired_brier.upper >= 0
        for s in summaries
        if not s.transported and s.bank_variant == "full"
    ):
        return "one_rate_recoverable_mechanism_inconclusive"
    flank_transport = [s for s in summaries if s.transported and s.bank_variant == "full"]
    if any(not s.coverage.lower <= 0.95 <= s.coverage.upper for s in flank_transport):
        return "one_rate_recovery_robust_cutoff_nontransportable"
    return "advance_to_second_spread_parameter"


def _central_reconciliation(
    summaries: list[CutoffSummary], config: Goal005Config
) -> dict[str, bool]:
    if not config.is_production:
        return {f"goal004_{name}_reconciled": True for name in BANK_VARIANT_NAMES}
    result: dict[str, bool] = {}
    for name in BANK_VARIANT_NAMES:
        row = next(
            s
            for s in summaries
            if s.truth_rate == 1 and s.bank_variant == name and not s.transported
        )
        expected = FROZEN_CENTRAL[name]
        result[f"goal004_{name}_cutoff"] = abs(row.cutoff - expected[0]) < 1e-9
        result[f"goal004_{name}_coverage_count"] = row.coverage_count == expected[1]
        result[f"goal004_{name}_coverage_interval"] = (
            abs(row.coverage.lower - expected[2]) < 1e-12
            and abs(row.coverage.upper - expected[3]) < 1e-12
        )
        result[f"goal004_{name}_paired_brier"] = (
            abs(row.paired_brier.estimate - expected[4]) < 1e-12
            and abs(row.paired_brier.lower - expected[5]) < 1e-12
            and abs(row.paired_brier.upper - expected[6]) < 1e-12
        )
        result[f"goal004_{name}_topology"] = row.topology_count == 500
        result[f"goal004_{name}_boundary_contacts"] = row.boundary_contacts == 0
        result[f"goal004_{name}_class"] = (
            row.downstream_class == "advance_to_second_spread_parameter"
        )
    result["goal004_overall_class"] = all(
        result[f"goal004_{name}_class"] for name in BANK_VARIANT_NAMES
    )
    return result


def _evaluate_invariants(
    config: Goal005Config,
    fixed: FixedInputs,
    manifest: SeedManifest,
    bank: IntegrationBank,
    variants: tuple[BankVariant, ...],
    calibration: list[CalibrationRow],
    validation: list[ValidationRow],
    central: dict[str, bool],
) -> dict[str, bool]:
    streams = manifest.stream_records
    rows = np.asarray([site.row for site in fixed.design.sites], dtype=np.int64)
    cols = np.asarray([site.col for site in fixed.design.sites], dtype=np.int64)
    rho_one = compute_stochastic_spread(
        fixed.landscape, _generator(manifest.integration_bank[0]), rho=1.0
    ).arrival[rows, cols]
    rho_two = compute_stochastic_spread(
        fixed.landscape, _generator(manifest.integration_bank[0]), rho=2.0
    ).arrival[rows, cols]
    return {
        **fixed.invariants,
        **central,
        "phase_stream_counts": len(manifest.integration_bank) == config.bank_size
        and len(manifest.datasets)
        == 3 * (config.calibration_replicates + config.validation_replicates),
        "stream_uniqueness": len({(s.entropy, s.spawn_key) for s in streams}) == len(streams)
        and len({s.state_words for s in streams}) == len(streams),
        "stream_replay": all(_generator(s) is not None for s in streams),
        "integration_bank_shape": bank.arrivals.shape == (config.bank_size, 160),
        "integration_bank_finite": bool(np.isfinite(bank.arrivals).all()),
        "same_field_rate_scaling": bool(np.array_equal(rho_two, rho_one / 2.0)),
        "bank_variants": tuple(v.name for v in variants) == BANK_VARIANT_NAMES,
        "outer_result_counts": len(calibration) == 3 * config.calibration_replicates * 3
        and len(validation) == 3 * config.validation_replicates * 3,
        "complete_joint_observations": all(
            r.record_count == 1920 for r in calibration + validation
        ),
        "train_holdout_isolation": all(r.split_isolated for r in validation),
        "finite_composite_likelihoods": all(
            isfinite(r.lr_at_truth) for r in calibration + validation
        ),
        "prediction_scores_finite": all(isfinite(r.paired_brier_difference) for r in validation),
        "truth_grid_exact": all(
            r.truth_grid_index in config.truth_indices for r in calibration + validation
        ),
    }


def generator_from_seed_record(record: SeedRecord) -> np.random.Generator:
    return _generator(record)


def _git_blob_sha(path: Path) -> str:
    contents = path.read_bytes()
    return hashlib.sha1(f"blob {len(contents)}\0".encode() + contents).hexdigest()


def _git_commit_is_ancestor(repository_root: Path, commit: str) -> bool:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository_root), "merge-base", "--is-ancestor", commit, "HEAD"],
            check=False,
            capture_output=True,
        )
    except OSError:
        return False
    return completed.returncode == 0


def _git_commit_blob_sha(repository_root: Path, commit: str, path: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository_root), "rev-parse", f"{commit}:{path}"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None
