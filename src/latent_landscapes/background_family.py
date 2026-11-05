"""Background-hazard families and prey-loss histories for the Sprint 1 experiment.

Every background shares one biological-history address: the spread shocks, prey
thresholds, detection, visit uniforms and the G field are keyed by the history's
streams only, so backgrounds differ solely in the hazard they apply.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal001.landscape import Landscape
from latent_landscapes.goal001.spread import passable_edges
from latent_landscapes.goal006.spread import compute_contrast_spread, sample_edge_shock_vector
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.misspecification_generator import GeneratorSetup
from latent_landscapes.preinvasion_campaign import (
    PREDATOR_TIMES,
    PREY_TIMES,
    STREAM_NAMES,
    OpenTruth,
)

FloatArray = NDArray[np.float64]

FAMILY_STREAM_NAMES = (*STREAM_NAMES, "background_field")
COHORT_START = -60.0
WINDOW_DAYS = 60.0
Z_WEIGHT_A = 0.7
Z_WEIGHT_RESIDUAL = math.sqrt(0.51)
LOG_SCALE = math.sqrt(math.log(2.0))
AMPLITUDE = 1.0
TREND_GAMMA = math.log(1.5) / 120.0

# name -> (s, kappa); `constant` is flat and `temporal_trend` uses b100_anchor's.
BACKGROUNDS: dict[str, tuple[float, float]] = {
    "constant": (0.0, 0.0),
    "matched_exposure": (0.0, 0.0),
    "b100_anchor": (0.0, 1.0),
    "increased_heterogeneity": (0.0, math.sqrt(2.0)),
    "window_low": (-1.0, 1.0),
    "window_high": (1.0, 1.0),
    "temporal_trend": (0.0, 1.0),
}


def family_stream_seeds(address: tuple[int, ...]) -> dict[str, int]:
    """Streams for one history address; background never enters the key."""
    return {
        name: int(np.random.SeedSequence([*address, index]).generate_state(1, dtype=np.uint64)[0])
        for index, name in enumerate(FAMILY_STREAM_NAMES)
    }


@dataclass(frozen=True)
class FamilySurfaces:
    """Map-level planning surfaces shared by all histories on one map."""

    signal: FloatArray
    window: FloatArray
    diagnostics: dict[str, Any]


def signal_window_surface(landscape: Landscape, setup: GeneratorSetup) -> FamilySurfaces:
    """T: planning arrival-window indicator, residualised on [1, A] and unit-scaled."""
    shocks = np.ones(len(passable_edges(landscape)))
    arrival = np.asarray(
        compute_contrast_spread(landscape, 1.0, edge_shocks=shocks, rho=1.0).arrival,
        dtype=np.float64,
    )
    with np.errstate(invalid="ignore"):
        window = (np.isfinite(arrival) & (arrival > 0.0) & (arrival <= WINDOW_DAYS)).astype(
            np.float64
        )
    accepted = setup.accepted_mask
    a = setup.exposure_score[accepted]
    w = window[accepted]
    design = np.column_stack([np.ones_like(a), a])
    coefficients, *_ = np.linalg.lstsq(design, w, rcond=None)
    residual = w - design @ coefficients
    sd = float(residual.std(ddof=0))
    if not sd > 1e-12:
        raise ValueError("signal-window indicator is degenerate on this map")
    signal = np.zeros(setup.accepted_mask.shape)
    signal[accepted] = residual / sd
    diagnostics = {
        "window_prevalence": float(w.mean()),
        "sd_before_rescaling": sd,
        "corr_T_A": float(np.corrcoef(signal[accepted], a)[0, 1]),
        "corr_W_A": float(np.corrcoef(w, a)[0, 1]),
        "planning_arrival_finite_fraction": float(np.isfinite(arrival[accepted]).mean()),
    }
    return FamilySurfaces(signal, window, diagnostics)


def log_hazard_index(
    setup: GeneratorSetup, surfaces: FamilySurfaces, background: str, g_field: FloatArray
) -> FloatArray:
    """z(s, kappa) over the whole map."""
    s, kappa = BACKGROUNDS[background]
    return np.asarray(
        Z_WEIGHT_A * setup.exposure_score
        + Z_WEIGHT_RESIDUAL * (s * AMPLITUDE * surfaces.signal + kappa * g_field),
        dtype=np.float64,
    )


def background_hazard_map(
    setup: GeneratorSetup,
    surfaces: FamilySurfaces,
    background: str,
    g_field: FloatArray,
    mean_hazard: float,
) -> FloatArray:
    """lambda = mu exp(sqrt(log 2) z) / map-mean(exp(sqrt(log 2) z)); flat for `constant`."""
    if background not in BACKGROUNDS:
        raise ValueError(f"unknown background {background!r}")
    if background == "constant":
        return np.full(setup.accepted_mask.shape, float(mean_hazard))
    z = log_hazard_index(setup, surfaces, background, g_field)
    exponent = LOG_SCALE * z
    exponent = exponent - float(exponent[setup.accepted_mask].max())
    weight = np.exp(exponent)
    return np.asarray(mean_hazard * weight / float(weight[setup.accepted_mask].mean()))


def loss_times_trend(
    arrivals: FloatArray,
    hazards: FloatArray,
    effect: float,
    thresholds: FloatArray,
    gamma: float,
) -> FloatArray:
    """Invert the piecewise cumulative hazard of a cohort started at day -60.

    The hazard is lambda_i exp(gamma t) before arrival and effect times that after.
    Arrivals before day -60 act from the start; infinite arrivals never occur.
    Returns inf where the cumulative hazard never reaches the threshold (gamma < 0).
    """
    if arrivals.shape != hazards.shape or hazards.shape != thresholds.shape:
        raise ValueError("arrival, hazard and threshold arrays must have equal shapes")
    if (
        not np.isfinite(hazards).all()
        or not (hazards > 0).all()
        or not np.isfinite(thresholds).all()
        or not (thresholds >= 0).all()
        or not math.isfinite(effect)
        or effect <= 0
        or not math.isfinite(gamma)
    ):
        raise ValueError("hazards, effect and thresholds must be finite and positive")
    start = COHORT_START
    tau = np.maximum(arrivals, start)

    def cumulative(t: FloatArray) -> FloatArray:
        if gamma == 0.0:
            return t - start
        return np.asarray((np.exp(gamma * t) - math.exp(gamma * start)) / gamma)

    def invert(y: FloatArray) -> FloatArray:
        if gamma == 0.0:
            return start + y
        argument = gamma * y + math.exp(gamma * start)
        with np.errstate(invalid="ignore", divide="ignore"):
            t = np.where(
                argument > 0, np.log(np.where(argument > 0, argument, 1.0)) / gamma, np.inf
            )
        return np.asarray(t)

    finite_tau = np.where(np.isfinite(tau), tau, 0.0)
    before = hazards * cumulative(finite_tau)
    early = (thresholds <= before) | ~np.isfinite(tau)
    y = np.where(
        early,
        thresholds / hazards,
        cumulative(finite_tau) + (thresholds - before) / (hazards * effect),
    )
    return invert(y)


@dataclass(frozen=True)
class FamilyDraws:
    arrival: FloatArray
    thresholds: FloatArray
    g_field: FloatArray
    detection: FloatArray
    predator_uniform: FloatArray
    prey_uniform: FloatArray


def history_draws(
    fixed: FixedInputs, setup: GeneratorSetup, truth: OpenTruth, seeds: dict[str, Any]
) -> FamilyDraws:
    """Everything random in a history, independent of the background."""
    streams = seeds["streams"]
    n = len(setup.site_rows)
    shocks = sample_edge_shock_vector(fixed.landscape, np.random.default_rng(streams["spread"]))
    spread = compute_contrast_spread(fixed.landscape, 1.0, edge_shocks=shocks, rho=1.0)
    arrival = np.asarray(spread.arrival[setup.site_rows, setup.site_cols], dtype=np.float64)
    thresholds = np.random.default_rng(streams["prey_loss"]).exponential(size=n)
    g_field = setup.field_sampler.sample(np.random.default_rng(streams["background_field"]))
    if truth.detection_sd == 0:
        detection = np.full(n, 0.65)
    else:
        concentration = 0.65 * 0.35 / truth.detection_sd**2 - 1.0
        if concentration <= 0:
            raise ValueError("detection dispersion is outside the Beta domain")
        detection = np.random.default_rng(streams["site_detection"]).beta(
            0.65 * concentration, 0.35 * concentration, size=n
        )
    predator_uniform = np.random.default_rng(streams["predator_visits"]).random(
        (n, len(PREDATOR_TIMES), 2)
    )
    prey_uniform = np.random.default_rng(streams["prey_visits"]).random((n, len(PREY_TIMES), 2))
    return FamilyDraws(arrival, thresholds, g_field, detection, predator_uniform, prey_uniform)


def generate_family_history(
    fixed: FixedInputs,
    setup: GeneratorSetup,
    truth: OpenTruth,
    seeds: dict[str, Any],
    background: str,
    surfaces: FamilySurfaces,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Observation-only arrays and an evaluator bundle for one background."""
    if background not in BACKGROUNDS:
        raise ValueError(f"unknown background {background!r}")
    draws = history_draws(fixed, setup, truth, seeds)
    hazard_map = background_hazard_map(
        setup, surfaces, background, draws.g_field, truth.mean_hazard
    )
    hazards = hazard_map[setup.site_rows, setup.site_cols]
    gamma = TREND_GAMMA if background == "temporal_trend" else 0.0
    losses = loss_times_trend(draws.arrival, hazards, truth.effect, draws.thresholds, gamma)
    predator_alive = draws.arrival[:, None] <= PREDATOR_TIMES[None, :]
    prey_alive = losses[:, None] > PREY_TIMES[None, :]
    predator = ((draws.predator_uniform < 0.65).sum(axis=2) * predator_alive).astype(np.int8)
    prey = ((draws.prey_uniform < draws.detection[:, None, None]).sum(axis=2) * prey_alive).astype(
        np.int8
    )
    identity = hashlib.sha256(predator.tobytes() + prey.tobytes()).hexdigest()
    observations = {
        "index": truth.index,
        "opaque_id": identity,
        "predator_counts": predator,
        "prey_counts": prey,
    }
    evaluator = {
        "truth": asdict(truth),
        "seeds": seeds,
        "background": background,
        "trend_gamma": gamma,
        "arrival": draws.arrival,
        "loss": losses,
        "site_hazard": hazards,
        "g_sites": draws.g_field[setup.site_rows, setup.site_cols],
        "site_detection": draws.detection,
        "prey_alive": prey_alive,
    }
    return observations, evaluator
