"""Vectorised fresh reference/evaluation blocks for Goal 054.

The six original evaluation cells deliberately use the Goal 053 mechanics.  The
new cells use the same process and observation streams, with a nonlinear
background field based on the accepted-map exposure indicator.  This module
keeps the analyst boundary as arrays: no ``AnalystHistory`` objects are made
for a block.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, replace
from typing import Literal, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import misspecification_generator as legacy
from latent_landscapes import prospective_background_generator as goal053
from latent_landscapes.goal004.observations import SURVEY_TIMES
from latent_landscapes.goal006.spread import compute_contrast_spread, sample_edge_shock_vector
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.known_nuisance_calibration import DETECTION_PROBABILITY

FloatArray = NDArray[np.float64]
GeneratorSetup = legacy.GeneratorSetup
GeneratorSeed = legacy.GeneratorSeed
GeneratorPhase = Literal[
    "reference",
    "evaluation",
    "timing_reference",
    "timing_evaluation",
    "production",
    "timing",
    "bootstrap",
    "smoke",
]
Panel = Literal["reference", "evaluation"]

REFERENCE_ROOT = 2026092901
EVALUATION_ROOT = 2026092902
TIMING_REFERENCE_ROOT = 2026092903
TIMING_EVALUATION_ROOT = 2026092904
BOOTSTRAP_ROOT = 2026092905
SMOKE_ROOT = 2026092906

# Short aliases are useful to campaign code and retain the registration's
# names without making the six roots ambiguous.
REF_ROOT = REFERENCE_ROOT
EVAL_ROOT = EVALUATION_ROOT
TIMING_REF_ROOT = TIMING_REFERENCE_ROOT
TIMING_EVAL_ROOT = TIMING_EVALUATION_ROOT
BOOT_ROOT = BOOTSTRAP_ROOT

REFERENCE_REPLICATES = 999
EVALUATION_REPLICATES = 1_000
TIMING_REFERENCE_REPLICATES = 4
TIMING_EVALUATION_REPLICATES = 8
BOOTSTRAP_REPLICATES = 2_000
SMOKE_REPLICATES = 2

FIELD_MEAN_HAZARD = 0.002
EXPOSURE_MIXING = 0.70
GAUSSIAN_MIXING = math.sqrt(0.51)
FIELD_SIGMA = math.sqrt(math.log(2.0))
VISITS_PER_SURVEY = legacy.VISITS_PER_SURVEY

BETAS = tuple(float(value) for value in np.linspace(-2.0, 2.0, 81))
ORIGINAL_CELL_IDS = goal053.CELL_IDS
ORIGINAL_TRUTH_H = goal053.TRUTH_H
ORIGINAL_TRUTH_BETA = goal053.TRUTH_BETA
EVALUATION_CELL_IDS = (*ORIGINAL_CELL_IDS, "N100-A_h1", "N100-A_h3")
EVALUATION_TRUTH_H = (*ORIGINAL_TRUTH_H, 1.0, 3.0)
EVALUATION_TRUTH_BETA = (*ORIGINAL_TRUTH_BETA, math.nan, math.nan)
REFERENCE_CELL_IDS = tuple(f"N100-E{beta:+.2f}_h1" for beta in BETAS)

# Compatibility names used by the earlier generators.
CELL_IDS = EVALUATION_CELL_IDS
TRUTH_H = EVALUATION_TRUTH_H
TRUTH_BETA = EVALUATION_TRUTH_BETA

if len(
    {
        REFERENCE_ROOT,
        EVALUATION_ROOT,
        TIMING_REFERENCE_ROOT,
        TIMING_EVALUATION_ROOT,
        BOOTSTRAP_ROOT,
        SMOKE_ROOT,
    }
) != 6:
    raise RuntimeError("Goal054 seed roots must be distinct")


def build_generator_setup(fixed: FixedInputs) -> GeneratorSetup:
    """Build the frozen 160-site map/design setup used by Goal 053."""

    return goal053.build_generator_setup(fixed)


build_field_sampler = legacy.build_field_sampler
background_hazard_field = legacy.background_hazard_field
exact_hazard_field = goal053.exact_hazard_field


def _seed_phase(phase: GeneratorPhase) -> tuple[str, str]:
    """Return the old generator phase and the registered Goal054 phase."""

    if phase.startswith("timing_") or phase == "timing":
        old_phase = "timing"
    elif phase == "smoke":
        old_phase = "smoke"
    elif phase == "bootstrap":
        old_phase = "bootstrap"
    else:
        old_phase = "production"
    return old_phase, phase


def spawn_generator_seeds(
    root: int, phase: GeneratorPhase, count: int
) -> tuple[GeneratorSeed, ...]:
    """Reuse the legacy seven-stream construction under Goal054 phase names."""

    if root < 0 or count <= 0 or phase not in {
        "reference",
        "evaluation",
        "timing_reference",
        "timing_evaluation",
        "bootstrap",
        "smoke",
        "production",
        "timing",
    }:
        raise ValueError("root and replicate count are invalid")
    old_phase, registered_phase = _seed_phase(phase)
    records = goal053.spawn_generator_seeds(
        root, cast(legacy.GeneratorPhase, old_phase), count
    )
    return tuple(
        replace(record, phase=cast(legacy.GeneratorPhase, registered_phase))
        for record in records
    )


def _validate_inputs(fixed: FixedInputs, setup: GeneratorSetup, seed: GeneratorSeed) -> None:
    if fixed.landscape.shape != setup.accepted_mask.shape:
        raise ValueError("generator setup does not match the supplied fixed landscape")
    sites = tuple(sorted(fixed.design.sites, key=lambda site: site.site_id))
    if tuple(site.site_id for site in sites) != setup.site_ids:
        raise ValueError("generator setup does not match the supplied sampling design")
    if len(set(seed.stream_seeds)) != 7:
        raise ValueError("all seven generator streams must be distinct")


def _top_third_indicator(setup: GeneratorSetup) -> tuple[FloatArray, dict[str, float | int]]:
    """Return the selected-map indicator and its frozen structural metrics.

    The registered tie policy uses the linear two-thirds quantile and selects
    values strictly above the threshold.  On the frozen map this selects
    2,015 of 6,048 cells; centring and scaling use the selected accepted-map
    indicator values.
    """

    accepted = np.asarray(setup.accepted_mask, dtype=bool)
    values = np.asarray(setup.exposure_score[accepted], dtype=np.float64)
    threshold = float(np.quantile(values, 2.0 / 3.0, method="linear"))
    selected = np.zeros(accepted.shape, dtype=np.float64)
    selected[accepted] = values > threshold
    selected_accepted = selected[accepted]
    raw_mean = float(selected_accepted.mean())
    raw_sd = float(selected_accepted.std(ddof=0))
    if raw_sd <= 0.0 or not math.isfinite(raw_sd):
        raise RuntimeError("top-third indicator has no usable variation")
    centred = np.zeros_like(selected)
    centred[accepted] = (selected_accepted - raw_mean) / raw_sd
    selected_count = int(np.sum(selected_accepted > 0.0))
    centred_accepted = centred[accepted]
    return centred, {
        "top_third_threshold": threshold,
        "top_third_selected_count": selected_count,
        "top_third_map_count": int(np.sum(accepted)),
        "top_third_selected_fraction": selected_count / int(np.sum(accepted)),
        "top_third_indicator_mean": float(centred_accepted.mean()),
        "top_third_indicator_sd": float(centred_accepted.std(ddof=0)),
        "top_third_raw_indicator_mean": raw_mean,
        "top_third_raw_indicator_sd": raw_sd,
    }


def _nonlinear_hazard_field(
    setup: GeneratorSetup, gaussian_field: FloatArray
) -> tuple[FloatArray, dict[str, float | int]]:
    """Transform ``G`` with the registered top-third nonlinear exposure field."""

    if gaussian_field.shape != setup.accepted_mask.shape or not np.isfinite(gaussian_field).all():
        raise ValueError("Gaussian field must be finite and match the accepted map")
    indicator, metrics = _top_third_indicator(setup)
    output = np.full(gaussian_field.shape, np.nan, dtype=np.float64)
    z = EXPOSURE_MIXING * indicator + GAUSSIAN_MIXING * gaussian_field
    raw = np.exp(FIELD_SIGMA * z)
    accepted = setup.accepted_mask
    output[accepted] = raw[accepted] * (
        FIELD_MEAN_HAZARD / float(raw[accepted].mean())
    )
    if not np.isfinite(output[accepted]).all() or np.any(output[accepted] <= 0.0):
        raise RuntimeError("nonlinear background field produced invalid hazards")
    return output, metrics


def nonlinear_hazard_field(setup: GeneratorSetup, gaussian_field: FloatArray) -> FloatArray:
    """Return the registered nonlinear hazard map with whole-map mean 0.002."""

    output, _ = _nonlinear_hazard_field(setup, gaussian_field)
    return output


def _shared_random_state(
    fixed: FixedInputs, setup: GeneratorSetup, seed: GeneratorSeed
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray, FloatArray, FloatArray]:
    shocks = sample_edge_shock_vector(fixed.landscape, np.random.default_rng(seed.process_seed))
    spread = compute_contrast_spread(fixed.landscape, 1.0, edge_shocks=shocks, rho=1.0)
    arrival = np.asarray(spread.arrival[setup.site_rows, setup.site_cols], dtype=np.float64)
    thresholds = np.asarray(
        np.random.default_rng(seed.prey_event_seed).exponential(size=len(setup.site_ids)),
        dtype=np.float64,
    )
    visit_shape = (len(setup.site_ids), len(SURVEY_TIMES), VISITS_PER_SURVEY)
    predator_uniforms = np.random.default_rng(seed.predator_detection_seed).random(visit_shape)
    prey_uniforms = np.random.default_rng(seed.prey_detection_seed).random(visit_shape)
    # Preserve the two legacy streams even though detection heterogeneity is
    # absent from this registered design.
    np.random.default_rng(seed.prey_detection_field_seed).random(len(setup.site_ids))
    np.random.default_rng(seed.predator_detection_field_seed).random(len(setup.site_ids))
    gaussian = setup.field_sampler.sample(np.random.default_rng(seed.background_field_seed))
    return arrival, thresholds, predator_uniforms, prey_uniforms, gaussian, spread.arrival


def _extirpation(
    arrival: FloatArray, hazards: FloatArray, effect: float, thresholds: FloatArray
) -> FloatArray:
    """Vectorised form of ``sample_extirpation_time`` for site rows."""

    finite_arrival = np.isfinite(arrival)
    before = hazards * arrival
    after = arrival + (thresholds - before) / (hazards * effect)
    before_arrival = thresholds / hazards
    return np.where(finite_arrival & (thresholds > before), after, before_arrival)


def _opaque_id(seed: GeneratorSeed, panel: Panel, ordinal: int) -> str:
    payload = f"goal054|{panel}|{seed.root}|{seed.phase}|{seed.index}|{ordinal}".encode()
    return hashlib.sha256(payload).hexdigest()[:32]


def _affine_a_fit_metrics(setup: GeneratorSetup, hazard_map: FloatArray) -> dict[str, float]:
    """Fit log hazard against accepted-map A and retain residual diagnostics."""

    accepted = setup.accepted_mask
    exposure = np.asarray(setup.exposure_score[accepted], dtype=np.float64)
    log_hazard = np.log(np.asarray(hazard_map[accepted], dtype=np.float64))
    design = np.column_stack((np.ones(exposure.shape, dtype=np.float64), exposure))
    intercept, slope = np.linalg.lstsq(design, log_hazard, rcond=None)[0]
    residual = log_hazard - (intercept + slope * exposure)
    return {
        "affine_a_log_intercept": float(intercept),
        "affine_a_log_slope": float(slope),
        "affine_a_log_residual_sd": float(residual.std(ddof=0)),
        "affine_a_log_residual_rmse": float(np.sqrt(np.mean(residual * residual))),
        "affine_a_log_residual_max_abs": float(np.max(np.abs(residual))),
    }


def _diagnostic(
    setup: GeneratorSetup,
    hazard_map: FloatArray,
    arrival_map: FloatArray,
    nonlinear_metrics: dict[str, float | int],
    affine_map: FloatArray | None,
    cell_id: str,
    truth_h: float,
    truth_beta: float,
    seed: GeneratorSeed,
    panel: Panel,
) -> dict[str, object]:
    probability = np.full(len(setup.site_ids), DETECTION_PROBABILITY, dtype=np.float64)
    values = asdict(legacy._diagnostics(setup, hazard_map, arrival_map, probability, probability))
    values.update(nonlinear_metrics)
    values.update(_affine_a_fit_metrics(setup, hazard_map))
    values.update(
        {
            "cell_id": cell_id,
            "truth_h": truth_h,
            "truth_beta": truth_beta,
            "panel": panel,
            "replicate_index": seed.index,
        }
    )
    if affine_map is None:
        values.update(
            paired_field_difference_mean=0.0,
            paired_field_difference_sd=0.0,
            paired_field_difference_rmse=0.0,
            paired_field_difference_max_abs=0.0,
        )
    else:
        residual = hazard_map[setup.accepted_mask] - affine_map[setup.accepted_mask]
        values.update(
            paired_field_difference_mean=float(residual.mean()),
            paired_field_difference_sd=float(residual.std(ddof=0)),
            paired_field_difference_rmse=float(np.sqrt(np.mean(residual * residual))),
            paired_field_difference_max_abs=float(np.max(np.abs(residual))),
        )
    return values


def generate_block(
    fixed: FixedInputs,
    setup: GeneratorSetup,
    seed: GeneratorSeed,
    panel: Panel = "reference",
) -> tuple[dict[str, NDArray[np.generic]], list[dict[str, object]]]:
    """Generate one paired reference or evaluation block.

    The first dimension is 81 for ``reference`` and eight for ``evaluation``.
    The returned tuple is ``(arrays, diagnostics)``; all observation and truth
    values are numpy arrays, while diagnostics are one JSON-friendly dict per
    row.
    """

    if panel not in ("reference", "evaluation"):
        raise ValueError("panel must be 'reference' or 'evaluation'")
    _validate_inputs(fixed, setup, seed)
    n = len(BETAS) if panel == "reference" else len(EVALUATION_CELL_IDS)
    (
        arrival,
        thresholds,
        predator_uniforms,
        prey_uniforms,
        gaussian,
        arrival_map,
    ) = _shared_random_state(fixed, setup, seed)
    nonlinear_map, nonlinear_metrics = _nonlinear_hazard_field(setup, gaussian)
    affine_map = legacy.background_hazard_field(
        setup, gaussian, nominal_cv=1.0, exposure_mixing=EXPOSURE_MIXING
    )

    if panel == "reference":
        cell_ids = REFERENCE_CELL_IDS
        truth_h = np.ones(n, dtype=np.float64)
        truth_beta = np.asarray(BETAS, dtype=np.float64)
        hazard_maps = tuple(exact_hazard_field(setup, beta) for beta in BETAS)
    else:
        cell_ids = EVALUATION_CELL_IDS
        truth_h = np.asarray(EVALUATION_TRUTH_H, dtype=np.float64)
        truth_beta = np.asarray(EVALUATION_TRUTH_BETA, dtype=np.float64)
        hazard_maps = (
            exact_hazard_field(setup, 0.0),
            exact_hazard_field(setup, 0.0),
            exact_hazard_field(setup, 0.6),
            exact_hazard_field(setup, 0.6),
            affine_map,
            affine_map,
            nonlinear_map,
            nonlinear_map,
        )

    site_hazards = np.asarray(
        [hazard_map[setup.site_rows, setup.site_cols] for hazard_map in hazard_maps],
        dtype=np.float64,
    )
    true_extirpation = np.asarray(
        [_extirpation(arrival, site_hazards[i], float(truth_h[i]), thresholds) for i in range(n)],
        dtype=np.float64,
    )
    times = np.asarray(SURVEY_TIMES, dtype=np.float64)
    predator_base = np.sum(predator_uniforms < DETECTION_PROBABILITY, axis=2).astype(
        np.uint8
    )
    predator_present = arrival[:, None] <= times[None, :]
    predator_counts = np.broadcast_to(predator_base, (n, *predator_base.shape)).copy()
    predator_counts *= predator_present[None, :, :]
    prey_base = np.sum(prey_uniforms < DETECTION_PROBABILITY, axis=2).astype(np.uint8)
    prey_alive = true_extirpation[:, :, None] > times[None, None, :]
    prey_counts = np.broadcast_to(prey_base, (n, *prey_base.shape)).copy()
    prey_counts[~prey_alive] = 0

    diagnostics: list[dict[str, object]] = []
    for i, (cell_id, hazard_map) in enumerate(zip(cell_ids, hazard_maps, strict=True)):
        diagnostics.append(
            _diagnostic(
                setup,
                hazard_map,
                arrival_map,
                nonlinear_metrics,
                affine_map if (panel == "evaluation" and i >= 4) else None,
                cell_id,
                float(truth_h[i]),
                float(truth_beta[i]),
                seed,
                panel,
            )
        )
    arrays: dict[str, NDArray[np.generic]] = {
        "cell_ids": np.asarray(cell_ids),
        "truth_h": truth_h,
        "truth_beta": truth_beta,
        "predator_counts": np.asarray(predator_counts, dtype=np.uint8),
        "prey_counts": np.asarray(prey_counts, dtype=np.uint8),
        "true_arrival": np.broadcast_to(arrival, (n, len(arrival))).copy(),
        "true_extirpation": true_extirpation,
        "true_hazards": site_hazards,
        "opaque_ids": np.asarray([_opaque_id(seed, panel, i) for i in range(n)]),
        "replicate_indices": np.full(n, seed.index, dtype=np.int64),
    }
    return arrays, diagnostics


__all__ = [
    "BETAS",
    "BOOTSTRAP_REPLICATES",
    "BOOTSTRAP_ROOT",
    "BOOT_ROOT",
    "CELL_IDS",
    "EVALUATION_CELL_IDS",
    "EVALUATION_REPLICATES",
    "EVALUATION_ROOT",
    "EVALUATION_TRUTH_BETA",
    "EVALUATION_TRUTH_H",
    "EVAL_ROOT",
    "EXPOSURE_MIXING",
    "FIELD_MEAN_HAZARD",
    "FIELD_SIGMA",
    "ORIGINAL_CELL_IDS",
    "ORIGINAL_TRUTH_BETA",
    "ORIGINAL_TRUTH_H",
    "REFERENCE_CELL_IDS",
    "REFERENCE_REPLICATES",
    "REFERENCE_ROOT",
    "REF_ROOT",
    "SMOKE_REPLICATES",
    "SMOKE_ROOT",
    "TIMING_EVALUATION_REPLICATES",
    "TIMING_EVALUATION_ROOT",
    "TIMING_REFERENCE_REPLICATES",
    "TIMING_REFERENCE_ROOT",
    "TIMING_REF_ROOT",
    "TRUTH_BETA",
    "TRUTH_H",
    "GeneratorPhase",
    "GeneratorSeed",
    "GeneratorSetup",
    "background_hazard_field",
    "build_field_sampler",
    "build_generator_setup",
    "exact_hazard_field",
    "generate_block",
    "nonlinear_hazard_field",
    "spawn_generator_seeds",
]
