"""Prospective paired misspecification generators for Goal 051.

The analyst boundary is deliberately the unchanged ``AnalystDataset`` from
Goal 049.  Generating fields, latent states, and true detection probabilities
remain in evaluator-only records and are never attached to analyst histories.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy.special import ndtri  # type: ignore[import-untyped]
from scipy.stats import beta as beta_distribution  # type: ignore[import-untyped]
from scipy.stats import rankdata

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes.arc2b_design import REFERENCE_BACKGROUND_RISK
from latent_landscapes.goal001.spread import (
    multi_source_dijkstra,
    passable_edges,
    source_labels,
)
from latent_landscapes.goal004.observations import SURVEY_TIMES
from latent_landscapes.goal006.spread import compute_contrast_spread, sample_edge_shock_vector
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.known_nuisance_calibration import (
    DETECTION_PROBABILITY,
    AnalystDataset,
    AnalystHistory,
)

FloatArray = NDArray[np.float64]
GeneratorPhase = Literal["production", "timing", "smoke"]

PRODUCTION_ROOT = 2026092301
TIMING_ROOT = 2026092302
SMOKE_ROOT = 2026092303
BOOTSTRAP_ROOT = 2026092304
FIELD_CORRELATION_LENGTH = 10.0
FIELD_MEAN_HAZARD = 0.002
BASELINE_BACKGROUND_HAZARD = float(-np.log1p(-REFERENCE_BACKGROUND_RISK) / 60.0)
VISITS_PER_SURVEY = 2


@dataclass(frozen=True, slots=True)
class CellSpec:
    """One fixed Goal 051 generator cell."""

    cell_id: str
    truth_h: float
    prey_detection_sd: float = 0.0
    predator_detection_sd: float = 0.0
    background_cv: float = 0.0
    exposure_mixing: float = 0.0

    @property
    def is_background(self) -> bool:
        return self.background_cv > 0.0


CELL_SPECS = (
    CellSpec("B_h1", 1.0),
    CellSpec("B_h3", 3.0),
    CellSpec("B_h5", 5.0),
    CellSpec("D10_h1", 1.0, prey_detection_sd=0.10),
    CellSpec("D10_h3", 3.0, prey_detection_sd=0.10),
    CellSpec("D10_h5", 5.0, prey_detection_sd=0.10),
    CellSpec("D20_h1", 1.0, prey_detection_sd=0.20),
    CellSpec("D20_h3", 3.0, prey_detection_sd=0.20),
    CellSpec("D20_h5", 5.0, prey_detection_sd=0.20),
    CellSpec("PD10_h1", 1.0, predator_detection_sd=0.10),
    CellSpec("PD10_h3", 3.0, predator_detection_sd=0.10),
    CellSpec("PD10_h5", 5.0, predator_detection_sd=0.10),
    CellSpec("B50-I_h1", 1.0, background_cv=0.50),
    CellSpec("B100-I_h1", 1.0, background_cv=1.00),
    CellSpec("B50-A_h1", 1.0, background_cv=0.50, exposure_mixing=0.70),
    CellSpec("B100-A_h1", 1.0, background_cv=1.00, exposure_mixing=0.70),
    CellSpec("B100-A_h3", 3.0, background_cv=1.00, exposure_mixing=0.70),
)


@dataclass(frozen=True, slots=True)
class GeneratorSeed:
    """Seven independent full-width streams for one paired replicate.

    ``spawn_generator_seeds`` creates the streams with
    ``SeedSequence(root).spawn(7)``.  Each stream then spawns one child per
    replicate and that child emits one uint64 seed for ``default_rng``.
    """

    root: int
    phase: GeneratorPhase
    index: int
    process_seed: int
    prey_event_seed: int
    predator_detection_seed: int
    prey_detection_seed: int
    prey_detection_field_seed: int
    predator_detection_field_seed: int
    background_field_seed: int

    @property
    def stream_seeds(self) -> tuple[int, ...]:
        return (
            self.process_seed,
            self.prey_event_seed,
            self.predator_detection_seed,
            self.prey_detection_seed,
            self.prey_detection_field_seed,
            self.predator_detection_field_seed,
            self.background_field_seed,
        )


@dataclass(frozen=True, slots=True)
class FieldSampler:
    """Exact finite-grid Gaussian sampler using circulant embedding."""

    field_shape: tuple[int, int]
    embedding_shape: tuple[int, int]
    square_root_eigenvalues: FloatArray
    reconstruction_max_abs_error: float
    minimum_eigenvalue: float

    def sample(self, rng: np.random.Generator) -> FloatArray:
        """Draw a distributionally mean-zero, unit-variance Gaussian field."""
        white = rng.standard_normal(self.embedding_shape)
        transformed = np.fft.irfftn(
            np.fft.rfftn(white, axes=(0, 1)) * self.square_root_eigenvalues,
            s=self.embedding_shape,
            axes=(0, 1),
        )
        return np.asarray(
            transformed[: self.field_shape[0], : self.field_shape[1]], dtype=np.float64
        )


@dataclass(frozen=True, slots=True)
class GeneratorSetup:
    """Map-derived objects built once and shared by all replicates."""

    site_ids: tuple[str, ...]
    site_rows: NDArray[np.int64]
    site_cols: NDArray[np.int64]
    site_splits: tuple[str, ...]
    site_cluster_ids: tuple[str, ...]
    accepted_mask: NDArray[np.bool_]
    exposure_score: FloatArray
    unreachable_tie_count: int
    unreachable_tie_exposure_score: float
    field_sampler: FieldSampler


@dataclass(frozen=True, slots=True)
class LatentTruth:
    """Evaluator-only generating state; never accepted by analyst scoring."""

    arrival: FloatArray
    prey_event_threshold: FloatArray
    prey_extirpation: FloatArray
    background_hazard: FloatArray
    predator_detection_probability: FloatArray
    prey_detection_probability: FloatArray


@dataclass(frozen=True, slots=True)
class GeneratorDiagnostics:
    """Prespecified map, sample, split, correlation, and censoring diagnostics."""

    map_hazard_mean: float
    sampled_hazard_mean: float
    training_hazard_mean: float
    holdout_hazard_mean: float
    map_hazard_cv: float
    sampled_hazard_cv: float
    training_hazard_cv: float
    holdout_hazard_cv: float
    predator_detection_mean: float
    predator_detection_sd: float
    prey_detection_mean: float
    prey_detection_sd: float
    map_hazard_a_correlation: float | None
    sampled_hazard_a_correlation: float | None
    training_hazard_a_correlation: float | None
    holdout_hazard_a_correlation: float | None
    map_hazard_exposure_correlation: float | None
    sampled_hazard_exposure_correlation: float | None
    training_hazard_exposure_correlation: float | None
    holdout_hazard_exposure_correlation: float | None
    sampled_hazard_arrival_correlation_arrived: float | None
    training_hazard_arrival_correlation_arrived: float | None
    holdout_hazard_arrival_correlation_arrived: float | None
    sampled_arrived_count: int
    training_arrived_count: int
    holdout_arrived_count: int
    map_arrival_censored_count: int
    map_arrival_censored_fraction: float
    sampled_arrival_censored_count: int
    sampled_arrival_censored_fraction: float
    training_arrival_censored_count: int
    training_arrival_censored_fraction: float
    holdout_arrival_censored_count: int
    holdout_arrival_censored_fraction: float


@dataclass(frozen=True, slots=True)
class GeneratedCell:
    cell: CellSpec
    dataset: AnalystDataset
    latent_truth: LatentTruth
    diagnostics: GeneratorDiagnostics


def _seed_int(sequence: np.random.SeedSequence) -> int:
    return int(sequence.generate_state(1, dtype=np.uint64)[0])


def spawn_generator_seeds(
    root: int, phase: GeneratorPhase, count: int
) -> tuple[GeneratorSeed, ...]:
    """Create a complete, non-overlapping seven-stream replicate manifest."""
    if root < 0 or count <= 0 or phase not in {"production", "timing", "smoke"}:
        raise ValueError("root, phase, and replicate count are invalid")
    stream_roots = np.random.SeedSequence(root).spawn(7)
    streams = tuple(
        tuple(_seed_int(child) for child in stream_root.spawn(count))
        for stream_root in stream_roots
    )
    all_seeds = tuple(seed for stream in streams for seed in stream)
    if len(all_seeds) != 7 * count or len(set(all_seeds)) != len(all_seeds):
        raise RuntimeError("generator seed manifest is incomplete or contains a collision")
    return tuple(
        GeneratorSeed(root, phase, index, *(stream[index] for stream in streams))
        for index in range(count)
    )


def build_field_sampler(field_shape: tuple[int, int]) -> FieldSampler:
    """Build the minimal exact circulant embedding for the registered kernel."""
    if len(field_shape) != 2 or min(field_shape) < 2:
        raise ValueError("field shape must contain two dimensions of at least two cells")
    embedding_shape = (2 * (field_shape[0] - 1), 2 * (field_shape[1] - 1))
    row_lag = np.minimum(
        np.arange(embedding_shape[0]),
        embedding_shape[0] - np.arange(embedding_shape[0]),
    )[:, None]
    col_lag = np.minimum(
        np.arange(embedding_shape[1]),
        embedding_shape[1] - np.arange(embedding_shape[1]),
    )[None, :]
    covariance = np.exp(-np.hypot(row_lag, col_lag) / FIELD_CORRELATION_LENGTH)
    eigenvalues = np.asarray(np.fft.rfftn(covariance).real, dtype=np.float64)
    minimum = float(eigenvalues.min())
    if minimum <= 0.0:
        raise RuntimeError(
            "registered circulant embedding is not strictly positive definite; "
            "eigenvalues must not be truncated or retuned"
        )
    reconstruction = np.fft.irfftn(eigenvalues, s=embedding_shape, axes=(0, 1))
    error = float(np.max(np.abs(reconstruction - covariance)))
    if error > 1e-12:
        raise RuntimeError("circulant covariance reconstruction exceeds 1e-12")
    return FieldSampler(
        field_shape,
        embedding_shape,
        np.asarray(np.sqrt(eigenvalues), dtype=np.float64),
        error,
        minimum,
    )


def _exposure_score(
    fixed: FixedInputs,
) -> tuple[NDArray[np.bool_], FloatArray, int, float]:
    """Normal scores of negative deterministic resistance-shortest-path distance."""
    landscape = fixed.landscape
    distances, _ = multi_source_dijkstra(
        node_count=landscape.cell_count,
        weighted_edges=passable_edges(landscape),
        source_labels=source_labels(landscape),
    )
    distance_map = np.asarray(distances, dtype=np.float64).reshape(landscape.shape)
    unreachable = ~np.isfinite(distance_map)
    accepted = np.ones(landscape.shape, dtype=np.bool_)
    values = -distance_map.ravel()
    ranks = np.asarray(rankdata(values, method="average"), dtype=np.float64)
    quantiles = (ranks - 0.5) / len(ranks)
    scores = np.asarray(ndtri(quantiles), dtype=np.float64)
    scores = (scores - float(scores.mean())) / float(scores.std(ddof=0))
    output = scores.reshape(landscape.shape)
    if (
        not np.isfinite(output[accepted]).all()
        or abs(float(output[accepted].mean())) > 1e-12
        or abs(float(output[accepted].std(ddof=0)) - 1.0) > 1e-12
    ):
        raise RuntimeError("exposure normal scores are not finite, centred, and unit variance")
    tied_scores = np.unique(output[unreachable])
    if len(tied_scores) != 1:
        raise RuntimeError("all unreachable cells must retain one average-rank exposure tie")
    return accepted, output, int(unreachable.sum()), float(tied_scores[0])


def build_generator_setup(fixed: FixedInputs) -> GeneratorSetup:
    """Build the fixed exposure and exact covariance objects once per run."""
    sites = tuple(sorted(fixed.design.sites, key=lambda site: site.site_id))
    if len(sites) != 160 or len({site.site_id for site in sites}) != len(sites):
        raise ValueError("Goal 051 requires the frozen unique 160-site design")
    accepted, exposure, unreachable_count, unreachable_score = _exposure_score(fixed)
    rows = np.asarray([site.row for site in sites], dtype=np.int64)
    cols = np.asarray([site.col for site in sites], dtype=np.int64)
    if not accepted[rows, cols].all():
        raise ValueError("every sampled site must belong to the accepted landscape map")
    return GeneratorSetup(
        tuple(site.site_id for site in sites),
        rows,
        cols,
        tuple(site.split for site in sites),
        tuple(site.cluster_id for site in sites),
        accepted,
        exposure,
        unreachable_count,
        unreachable_score,
        build_field_sampler(fixed.landscape.shape),
    )


def _detection_probabilities(uniforms: FloatArray, sd: float) -> FloatArray:
    if sd == 0.0:
        return np.full(uniforms.shape, DETECTION_PROBABILITY, dtype=np.float64)
    parameters = {
        0.10: (14.1375, 7.6125),
        0.20: (3.046875, 1.640625),
    }
    try:
        alpha, beta = parameters[sd]
    except KeyError as error:
        raise ValueError("unregistered detection heterogeneity") from error
    probabilities = np.asarray(beta_distribution.ppf(uniforms, alpha, beta), dtype=np.float64)
    if not np.isfinite(probabilities).all() or np.any((probabilities < 0) | (probabilities > 1)):
        raise RuntimeError("beta detection field produced invalid probabilities")
    return probabilities


def background_hazard_field(
    setup: GeneratorSetup,
    gaussian_field: FloatArray,
    *,
    nominal_cv: float,
    exposure_mixing: float,
) -> FloatArray:
    """Transform one shared G field without realisation-wise centring or scaling G."""
    if gaussian_field.shape != setup.accepted_mask.shape or not np.isfinite(gaussian_field).all():
        raise ValueError("Gaussian field must be finite and match the accepted map")
    if nominal_cv < 0.0 or not math.isfinite(nominal_cv):
        raise ValueError("nominal CV must be finite and non-negative")
    if not math.isfinite(exposure_mixing) or abs(exposure_mixing) > 1.0:
        raise ValueError("exposure mixing must lie in [-1, 1]")
    output = np.full(gaussian_field.shape, np.nan, dtype=np.float64)
    if nominal_cv == 0.0:
        output[setup.accepted_mask] = BASELINE_BACKGROUND_HAZARD
        return output
    sigma = math.sqrt(math.log1p(nominal_cv * nominal_cv))
    z = (
        exposure_mixing * setup.exposure_score[setup.accepted_mask]
        + math.sqrt(1.0 - exposure_mixing * exposure_mixing) * gaussian_field[setup.accepted_mask]
    )
    raw = np.exp(sigma * z)
    if not np.isfinite(raw).all() or np.any(raw <= 0.0):
        raise RuntimeError("background field transformation produced invalid hazards")
    output[setup.accepted_mask] = raw * (FIELD_MEAN_HAZARD / float(raw.mean()))
    return output


def _safe_correlation(first: FloatArray, second: FloatArray) -> float | None:
    if len(first) < 2 or float(np.ptp(first)) == 0.0 or float(np.ptp(second)) == 0.0:
        return None
    return float(np.corrcoef(first, second)[0, 1])


def _cv(values: FloatArray) -> float:
    if float(np.ptp(values)) == 0.0:
        return 0.0
    mean = float(values.mean())
    return float(values.std(ddof=0) / mean)


def _mean(values: FloatArray) -> float:
    return float(values[0]) if float(np.ptp(values)) == 0.0 else float(values.mean())


def _sd(values: FloatArray) -> float:
    return 0.0 if float(np.ptp(values)) == 0.0 else float(values.std(ddof=0))


def _censoring(arrivals: FloatArray) -> tuple[int, float]:
    count = int(np.sum(arrivals > SURVEY_TIMES[-1]))
    return count, count / len(arrivals)


def _diagnostics(
    setup: GeneratorSetup,
    hazards: FloatArray,
    arrival_map: FloatArray,
    predator_detection_probability: FloatArray,
    prey_detection_probability: FloatArray,
) -> GeneratorDiagnostics:
    rows, cols = setup.site_rows, setup.site_cols
    sampled = hazards[rows, cols]
    sampled_a = setup.exposure_score[rows, cols]
    sampled_arrival = arrival_map[rows, cols]
    training = np.asarray([split == "training" for split in setup.site_splits], dtype=np.bool_)
    holdout = ~training
    accepted_hazard = hazards[setup.accepted_mask]
    accepted_a = setup.exposure_score[setup.accepted_mask]
    accepted_arrival = arrival_map[setup.accepted_mask]
    map_exposure = np.maximum(0.0, SURVEY_TIMES[-1] - accepted_arrival)
    sample_exposure = np.maximum(0.0, SURVEY_TIMES[-1] - sampled_arrival)

    def arrived_correlation(mask: NDArray[np.bool_]) -> float | None:
        arrived = mask & (sampled_arrival <= SURVEY_TIMES[-1])
        return _safe_correlation(sampled[arrived], sampled_arrival[arrived])

    map_censored = _censoring(accepted_arrival)
    sampled_censored = _censoring(sampled_arrival)
    training_censored = _censoring(sampled_arrival[training])
    holdout_censored = _censoring(sampled_arrival[holdout])
    return GeneratorDiagnostics(
        _mean(accepted_hazard),
        _mean(sampled),
        _mean(sampled[training]),
        _mean(sampled[holdout]),
        _cv(accepted_hazard),
        _cv(sampled),
        _cv(sampled[training]),
        _cv(sampled[holdout]),
        _mean(predator_detection_probability),
        _sd(predator_detection_probability),
        _mean(prey_detection_probability),
        _sd(prey_detection_probability),
        _safe_correlation(accepted_hazard, accepted_a),
        _safe_correlation(sampled, sampled_a),
        _safe_correlation(sampled[training], sampled_a[training]),
        _safe_correlation(sampled[holdout], sampled_a[holdout]),
        _safe_correlation(accepted_hazard, map_exposure),
        _safe_correlation(sampled, sample_exposure),
        _safe_correlation(sampled[training], sample_exposure[training]),
        _safe_correlation(sampled[holdout], sample_exposure[holdout]),
        arrived_correlation(np.ones(len(sampled), dtype=np.bool_)),
        arrived_correlation(training),
        arrived_correlation(holdout),
        int(np.sum(sampled_arrival <= SURVEY_TIMES[-1])),
        int(np.sum(sampled_arrival[training] <= SURVEY_TIMES[-1])),
        int(np.sum(sampled_arrival[holdout] <= SURVEY_TIMES[-1])),
        map_censored[0],
        map_censored[1],
        sampled_censored[0],
        sampled_censored[1],
        training_censored[0],
        training_censored[1],
        holdout_censored[0],
        holdout_censored[1],
    )


def _opaque_id(seed: GeneratorSeed, ordinal: int) -> str:
    payload = f"goal051|{seed.root}|{seed.phase}|{seed.index}|{ordinal}".encode()
    return hashlib.sha256(payload).hexdigest()[:32]


def generate_replicate(
    fixed: FixedInputs,
    setup: GeneratorSetup,
    seed: GeneratorSeed,
) -> tuple[GeneratedCell, ...]:
    """Generate all 17 cells from one explicitly coupled random-number block."""
    if fixed.landscape.shape != setup.accepted_mask.shape:
        raise ValueError("generator setup does not match the supplied fixed landscape")
    sites = tuple(sorted(fixed.design.sites, key=lambda site: site.site_id))
    if tuple(site.site_id for site in sites) != setup.site_ids:
        raise ValueError("generator setup does not match the supplied sampling design")
    if len(set(seed.stream_seeds)) != 7:
        raise ValueError("all seven generator streams must be distinct")

    shocks = sample_edge_shock_vector(fixed.landscape, np.random.default_rng(seed.process_seed))
    spread = compute_contrast_spread(fixed.landscape, 1.0, edge_shocks=shocks, rho=1.0)
    arrival = np.asarray(spread.arrival[setup.site_rows, setup.site_cols], dtype=np.float64)
    thresholds = np.asarray(
        np.random.default_rng(seed.prey_event_seed).exponential(size=len(sites)),
        dtype=np.float64,
    )
    visit_shape = (len(sites), len(SURVEY_TIMES), VISITS_PER_SURVEY)
    predator_uniforms = np.random.default_rng(seed.predator_detection_seed).random(visit_shape)
    prey_uniforms = np.random.default_rng(seed.prey_detection_seed).random(visit_shape)
    prey_field_uniforms = np.random.default_rng(seed.prey_detection_field_seed).random(len(sites))
    predator_field_uniforms = np.random.default_rng(seed.predator_detection_field_seed).random(
        len(sites)
    )
    gaussian = setup.field_sampler.sample(np.random.default_rng(seed.background_field_seed))
    prey_probabilities = {
        sd: _detection_probabilities(prey_field_uniforms, sd) for sd in (0.0, 0.10, 0.20)
    }
    predator_probabilities = {
        sd: _detection_probabilities(predator_field_uniforms, sd) for sd in (0.0, 0.10)
    }
    hazard_fields: dict[tuple[float, float], FloatArray] = {
        (0.0, 0.0): background_hazard_field(setup, gaussian, nominal_cv=0.0, exposure_mixing=0.0)
    }
    for spec in CELL_SPECS:
        if spec.is_background:
            key = (spec.background_cv, spec.exposure_mixing)
            if key not in hazard_fields:
                hazard_fields[key] = background_hazard_field(
                    setup,
                    gaussian,
                    nominal_cv=spec.background_cv,
                    exposure_mixing=spec.exposure_mixing,
                )

    output: list[GeneratedCell] = []
    for ordinal, spec in enumerate(CELL_SPECS):
        hazard_map = hazard_fields[(spec.background_cv, spec.exposure_mixing)]
        site_hazards = np.asarray(hazard_map[setup.site_rows, setup.site_cols], dtype=np.float64)
        prey_probability = prey_probabilities[spec.prey_detection_sd]
        predator_probability = predator_probabilities[spec.predator_detection_sd]
        extirpation = np.asarray(
            [
                arc2b.sample_extirpation_time(
                    predator_arrival=float(arrival[index]),
                    background_hazard=float(site_hazards[index]),
                    effect_multiplier=spec.truth_h,
                    exponential_threshold=float(thresholds[index]),
                )
                for index in range(len(sites))
            ],
            dtype=np.float64,
        )
        histories: list[AnalystHistory] = []
        for index, site in enumerate(sites):
            predator_present = arrival[index] <= np.asarray(SURVEY_TIMES)
            prey_alive = extirpation[index] > np.asarray(SURVEY_TIMES)
            predator_counts = tuple(
                int(np.sum(predator_uniforms[index, survey] < predator_probability[index]))
                if predator_present[survey]
                else 0
                for survey in range(len(SURVEY_TIMES))
            )
            prey_counts = tuple(
                int(np.sum(prey_uniforms[index, survey] < prey_probability[index]))
                if prey_alive[survey]
                else 0
                for survey in range(len(SURVEY_TIMES))
            )
            histories.append(
                AnalystHistory(
                    site.site_id,
                    site.cluster_id,
                    site.split,
                    predator_counts,
                    prey_counts,
                    DETECTION_PROBABILITY,
                )
            )
        output.append(
            GeneratedCell(
                spec,
                AnalystDataset(_opaque_id(seed, ordinal), tuple(histories)),
                LatentTruth(
                    arrival.copy(),
                    thresholds.copy(),
                    extirpation,
                    site_hazards,
                    predator_probability.copy(),
                    prey_probability.copy(),
                ),
                _diagnostics(
                    setup,
                    hazard_map,
                    spread.arrival,
                    predator_probability,
                    prey_probability,
                ),
            )
        )
    return tuple(output)
