"""Fresh paired six-cell generators for the Goal053 comparison.

The observation boundary and evaluator-only records are inherited from the
Goal051 generator.  This module changes only the registered generator cells:
two constant-background controls, two exact spatial-background controls, and
the two original aligned-background cells.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Literal, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import misspecification_generator as legacy
from latent_landscapes.goal001.design import DesignSite
from latent_landscapes.goal004.observations import SURVEY_TIMES
from latent_landscapes.goal006.spread import compute_contrast_spread, sample_edge_shock_vector
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.known_nuisance_calibration import (
    DETECTION_PROBABILITY,
    AnalystDataset,
    AnalystHistory,
)

FloatArray = NDArray[np.float64]
GeneratorPhase = Literal["production", "timing", "smoke", "bootstrap"]

PRODUCTION_ROOT = 2026092701
TIMING_ROOT = 2026092702
BOOTSTRAP_ROOT = 2026092703
SMOKE_ROOT = 2026092704

PRODUCTION_COUNT = 1_000
TIMING_COUNT = 20
BOOTSTRAP_COUNT = 2_000
SMOKE_COUNT = 2
# Naming aliases follow the existing campaign/replay modules.
PRODUCTION_REPLICATES = PRODUCTION_COUNT
TIMING_REPLICATES = TIMING_COUNT
BOOTSTRAP_REPLICATES = BOOTSTRAP_COUNT
SMOKE_REPLICATES = SMOKE_COUNT

EXACT_BACKGROUND_HAZARD = 0.002
EXPOSURE_BETA = 0.60
VISITS_PER_SURVEY = legacy.VISITS_PER_SURVEY

CELL_IDS = (
    "E0_h1",
    "E0_h3",
    "E06_h1",
    "E06_h3",
    "B100-A_h1",
    "B100-A_h3",
)
TRUTH_H = (1.0, 3.0, 1.0, 3.0, 1.0, 3.0)
TRUTH_BETA = (0.0, 0.0, EXPOSURE_BETA, EXPOSURE_BETA, math.nan, math.nan)

if len({PRODUCTION_ROOT, TIMING_ROOT, BOOTSTRAP_ROOT, SMOKE_ROOT}) != 4:
    raise RuntimeError("Goal053 seed roots must be distinct")


@dataclass(frozen=True, slots=True)
class CellSpec:
    """One of the six fixed Goal053 generator cells."""

    cell_id: str
    truth_h: float
    truth_beta: float = math.nan
    background_cv: float = 0.0
    exposure_mixing: float = 0.0

    @property
    def is_exact_background(self) -> bool:
        return math.isfinite(self.truth_beta)

    @property
    def is_background(self) -> bool:
        return self.background_cv > 0.0


CELL_SPECS = (
    CellSpec(CELL_IDS[0], TRUTH_H[0], TRUTH_BETA[0]),
    CellSpec(CELL_IDS[1], TRUTH_H[1], TRUTH_BETA[1]),
    CellSpec(CELL_IDS[2], TRUTH_H[2], TRUTH_BETA[2]),
    CellSpec(CELL_IDS[3], TRUTH_H[3], TRUTH_BETA[3]),
    CellSpec(CELL_IDS[4], TRUTH_H[4], TRUTH_BETA[4], 1.0, 0.70),
    CellSpec(CELL_IDS[5], TRUTH_H[5], TRUTH_BETA[5], 1.0, 0.70),
)

# The Goal051 dataclass is intentionally reused so downstream scoring and
# evaluator code cannot accidentally acquire a second truth representation.
GeneratorSeed = legacy.GeneratorSeed
GeneratorSetup = legacy.GeneratorSetup
FieldSampler = legacy.FieldSampler
LatentTruth = legacy.LatentTruth
GeneratorDiagnostics = legacy.GeneratorDiagnostics


@dataclass(frozen=True, slots=True)
class GeneratedCell:
    """A Goal053 cell with the unchanged analyst/evaluator boundary."""

    cell: CellSpec
    dataset: AnalystDataset
    latent_truth: LatentTruth
    diagnostics: GeneratorDiagnostics


def _seed_int(sequence: np.random.SeedSequence) -> int:
    return int(sequence.generate_state(1, dtype=np.uint64)[0])


def spawn_generator_seeds(
    root: int, phase: GeneratorPhase, count: int
) -> tuple[GeneratorSeed, ...]:
    """Create seven disjoint full-width streams for one Goal053 phase.

    This follows the Goal051 seed construction exactly, while allowing the
    registered bootstrap phase in addition to production, timing, and smoke.
    """

    if root < 0 or count <= 0 or phase not in {"production", "timing", "smoke", "bootstrap"}:
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
        GeneratorSeed(
            root,
            cast(legacy.GeneratorPhase, phase),
            index,
            *(stream[index] for stream in streams),
        )
        for index in range(count)
    )


# Setup construction remains exactly the fixed 160-site Goal051 design.
build_generator_setup = legacy.build_generator_setup
build_field_sampler = legacy.build_field_sampler
background_hazard_field = legacy.background_hazard_field


def _exact_hazard_field(setup: GeneratorSetup, beta: float) -> FloatArray:
    """Return the registered exact map hazard, normalised over the whole map."""

    if not math.isfinite(beta):
        raise ValueError("exact background beta must be finite")
    output = np.full(setup.accepted_mask.shape, np.nan, dtype=np.float64)
    all_a = np.asarray(setup.exposure_score[setup.accepted_mask], dtype=np.float64)
    if beta == 0.0:
        output[setup.accepted_mask] = EXACT_BACKGROUND_HAZARD
        return output
    scaled = beta * all_a
    shift = float(scaled.max())
    weights = np.exp(scaled - shift)
    output[setup.accepted_mask] = EXACT_BACKGROUND_HAZARD * weights / float(weights.mean())
    if not np.isfinite(output[setup.accepted_mask]).all() or (
        output[setup.accepted_mask] <= 0.0
    ).any():
        raise RuntimeError("exact background hazard field is invalid")
    return output


def exact_hazard_field(setup: GeneratorSetup, beta: float) -> FloatArray:
    """Public control helper for the exact constant/spatial cells."""

    return _exact_hazard_field(setup, beta)


def _opaque_id(seed: GeneratorSeed, ordinal: int) -> str:
    payload = f"goal053|{seed.root}|{seed.phase}|{seed.index}|{ordinal}".encode()
    return hashlib.sha256(payload).hexdigest()[:32]


def _validate_inputs(
    fixed: FixedInputs, setup: GeneratorSetup, seed: GeneratorSeed
) -> tuple[DesignSite, ...]:
    if fixed.landscape.shape != setup.accepted_mask.shape:
        raise ValueError("generator setup does not match the supplied fixed landscape")
    sites = tuple(sorted(fixed.design.sites, key=lambda site: site.site_id))
    if tuple(site.site_id for site in sites) != setup.site_ids:
        raise ValueError("generator setup does not match the supplied sampling design")
    if len(set(seed.stream_seeds)) != 7:
        raise ValueError("all seven generator streams must be distinct")
    return sites


def generate_replicate(
    fixed: FixedInputs,
    setup: GeneratorSetup,
    seed: GeneratorSeed,
) -> tuple[GeneratedCell, ...]:
    """Generate one paired six-cell block from shared process and observations."""

    sites = _validate_inputs(fixed, setup, seed)
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
    # Consume the same two field streams as Goal051.  Goal053 has no detection
    # heterogeneity, so the resulting uniforms are deliberately unused.
    prey_field_uniforms = np.random.default_rng(seed.prey_detection_field_seed).random(len(sites))
    predator_field_uniforms = np.random.default_rng(seed.predator_detection_field_seed).random(
        len(sites)
    )
    del prey_field_uniforms, predator_field_uniforms
    gaussian = setup.field_sampler.sample(np.random.default_rng(seed.background_field_seed))

    hazard_fields: dict[str, FloatArray] = {
        "E0": _exact_hazard_field(setup, 0.0),
        "E06": _exact_hazard_field(setup, EXPOSURE_BETA),
        "B100-A": legacy.background_hazard_field(
            setup, gaussian, nominal_cv=1.0, exposure_mixing=0.70
        ),
    }
    probability = legacy._detection_probabilities(
        np.zeros(len(sites), dtype=np.float64), 0.0
    )

    output: list[GeneratedCell] = []
    for ordinal, spec in enumerate(CELL_SPECS):
        if spec.is_exact_background:
            hazard_map = hazard_fields["E0" if spec.truth_beta == 0.0 else "E06"]
        else:
            hazard_map = hazard_fields["B100-A"]
        site_hazards = np.asarray(hazard_map[setup.site_rows, setup.site_cols], dtype=np.float64)
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
                int(np.sum(predator_uniforms[index, survey] < probability[index]))
                if predator_present[survey]
                else 0
                for survey in range(len(SURVEY_TIMES))
            )
            prey_counts = tuple(
                int(np.sum(prey_uniforms[index, survey] < probability[index]))
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
                    probability.copy(),
                    probability.copy(),
                ),
                legacy._diagnostics(
                    setup,
                    hazard_map,
                    spread.arrival,
                    probability,
                    probability,
                ),
            )
        )
    return tuple(output)


__all__ = [
    "BOOTSTRAP_COUNT",
    "BOOTSTRAP_REPLICATES",
    "BOOTSTRAP_ROOT",
    "CELL_IDS",
    "CELL_SPECS",
    "EXACT_BACKGROUND_HAZARD",
    "PRODUCTION_COUNT",
    "PRODUCTION_REPLICATES",
    "PRODUCTION_ROOT",
    "SMOKE_COUNT",
    "SMOKE_REPLICATES",
    "SMOKE_ROOT",
    "TIMING_COUNT",
    "TIMING_REPLICATES",
    "TIMING_ROOT",
    "TRUTH_BETA",
    "TRUTH_H",
    "CellSpec",
    "GeneratedCell",
    "GeneratorDiagnostics",
    "GeneratorSeed",
    "GeneratorSetup",
    "LatentTruth",
    "background_hazard_field",
    "build_field_sampler",
    "build_generator_setup",
    "exact_hazard_field",
    "generate_replicate",
    "spawn_generator_seeds",
]
