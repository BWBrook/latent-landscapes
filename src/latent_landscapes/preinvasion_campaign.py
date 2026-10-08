"""Open, reproducible development histories for the observed-nuisance study.

This module never generates a sealed capstone.  Its observation arrays and
evaluator truth are deliberately stored separately, with public fixed seeds.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import adjusted_background_likelihood as adjusted
from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes.goal006.spread import compute_contrast_spread, sample_edge_shock_vector
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.goal011 import benchmark
from latent_landscapes.misspecification_generator import GeneratorSetup, build_generator_setup

FloatArray = NDArray[np.float64]
PREY_TIMES = np.arange(-60.0, 61.0, 10.0)
PREDATOR_TIMES = np.arange(10.0, 61.0, 10.0)
PANEL_ROOT = 2026100301
STREAM_NAMES = ("spread", "prey_loss", "predator_visits", "site_detection", "prey_visits")


@dataclass(frozen=True)
class OpenTruth:
    """Evaluator-only truth for one openly labelled development cell."""

    index: int
    effect: float
    mean_hazard: float
    beta: float
    detection_sd: float


def panel_truths() -> tuple[OpenTruth, ...]:
    return tuple(
        OpenTruth(i, h, mu, beta, sd)
        for i, (h, mu, beta, sd) in enumerate(
            itertools.product((1.0, 3.0), (0.0016, 0.0025), (0.0, 0.6), (0.0, 0.2))
        )
    )


def seed_records(root: int = PANEL_ROOT) -> tuple[dict[str, Any], ...]:
    """A stable public stream hierarchy; creating this ledger draws no histories."""
    return tuple(
        {
            "index": i,
            "root": root,
            "spawn_key": list(child.spawn_key),
            "streams": {
                name: int(stream.generate_state(1, dtype=np.uint64)[0])
                for name, stream in zip(STREAM_NAMES, child.spawn(5), strict=True)
            },
        }
        for i, child in enumerate(np.random.SeedSequence(root).spawn(16))
    )


def public_inputs() -> tuple[FixedInputs, GeneratorSetup]:
    return_fixed = benchmark.build_fixed_inputs()
    return return_fixed, build_generator_setup(return_fixed)


def loss_times(
    arrivals: FloatArray, hazards: FloatArray, effect: float, thresholds: FloatArray
) -> FloatArray:
    """Invert one cohort's hazard from day -60; there is no reset at invasion."""
    if arrivals.shape != hazards.shape or hazards.shape != thresholds.shape:
        raise ValueError("arrival, hazard and threshold arrays must have equal shapes")
    return np.asarray(
        [
            arc2b.sample_extirpation_time(
                predator_arrival=float(arrival + 60.0),
                background_hazard=float(hazard),
                effect_multiplier=effect,
                exponential_threshold=float(threshold),
            )
            - 60.0
            for arrival, hazard, threshold in zip(arrivals, hazards, thresholds, strict=True)
        ],
        dtype=np.float64,
    )


def generate_open_history(
    fixed: FixedInputs, setup: GeneratorSetup, truth: OpenTruth, seeds: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return observation-only arrays and a separate public evaluator bundle."""
    streams = seeds["streams"]
    shocks = sample_edge_shock_vector(fixed.landscape, np.random.default_rng(streams["spread"]))
    spread = compute_contrast_spread(fixed.landscape, 1.0, edge_shocks=shocks, rho=1.0)
    arrivals = np.asarray(spread.arrival[setup.site_rows, setup.site_cols], dtype=np.float64)
    site_a = setup.exposure_score[setup.site_rows, setup.site_cols]
    hazards = adjusted.normalized_hazards(
        truth.beta, setup.exposure_score, site_a, truth.mean_hazard
    )
    thresholds = np.random.default_rng(streams["prey_loss"]).exponential(size=len(site_a))
    losses = loss_times(arrivals, hazards, truth.effect, thresholds)
    if truth.detection_sd == 0:
        detection = np.full(len(site_a), 0.65)
    else:
        concentration = 0.65 * 0.35 / truth.detection_sd**2 - 1.0
        if concentration <= 0:
            raise ValueError("detection dispersion is outside the Beta domain")
        detection = np.random.default_rng(streams["site_detection"]).beta(
            0.65 * concentration, 0.35 * concentration, size=len(site_a)
        )
    predator_alive = arrivals[:, None] <= PREDATOR_TIMES[None, :]
    prey_alive = losses[:, None] > PREY_TIMES[None, :]
    predator_uniform = np.random.default_rng(streams["predator_visits"]).random(
        (len(site_a), len(PREDATOR_TIMES), 2)
    )
    prey_uniform = np.random.default_rng(streams["prey_visits"]).random(
        (len(site_a), len(PREY_TIMES), 2)
    )
    predator = ((predator_uniform < 0.65).sum(axis=2) * predator_alive).astype(np.int8)
    prey = ((prey_uniform < detection[:, None, None]).sum(axis=2) * prey_alive).astype(np.int8)
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
        "arrival": arrivals,
        "loss": losses,
        "site_hazard": hazards,
        "site_detection": detection,
        "prey_alive": prey_alive,
    }
    return observations, evaluator


def hazard_box_certificate(
    all_map_a: FloatArray,
    site_a: FloatArray,
    *,
    max_mu: float = 0.006,
    max_h: float = 10.0,
    beta_edges: FloatArray | None = None,
) -> dict[str, Any]:
    """Conservative continuous-beta bound, not a maximum over fitted nodes.

    On each beta interval, each numerator is bounded above by its endpoint
    maximum and every denominator term below by its endpoint minimum.  Summing
    these lower bounds preserves the whole-map normalizer.  A small outward
    margin covers the floating-point evaluation of the bound itself.
    """
    edges = np.linspace(-2.0, 2.0, 81) if beta_edges is None else beta_edges
    whole = np.asarray(all_map_a).ravel()
    if (
        len(edges) < 2
        or not np.isfinite(edges).all()
        or not np.isfinite(whole).all()
        or not np.isfinite(site_a).all()
        or not (np.diff(edges) > 0).all()
        or not max_mu > 0
        or not max_h >= 1
    ):
        raise ValueError("invalid public hazard box")
    bounds = []
    for lower, upper in itertools.pairwise(edges):
        denominator_lower = np.minimum(np.exp(lower * whole), np.exp(upper * whole)).mean()
        numerator_upper = np.maximum(np.exp(lower * site_a), np.exp(upper * site_a))
        bounds.append(float(max_mu * np.max(numerator_upper / denominator_lower)))
    maximum = float(np.nextafter(max(bounds) * (1.0 + 1e-12), np.inf))
    return {
        "method": "interval_numerator_upper_whole_map_denominator_lower",
        "beta_interval": [float(edges[0]), float(edges[-1])],
        "interval_count": len(edges) - 1,
        "mu_upper": max_mu,
        "h_upper": max_h,
        "site_hazard_upper": maximum,
        "transform_x_upper": 10.0 * maximum * (max_h - 1.0),
        "required_transform_domain_upper": 5.0,
        "passes": bool(10.0 * maximum * (max_h - 1.0) <= 5.0),
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def generate_panel(output: Path) -> dict[str, Any]:
    """Write the registered open panel once; never overwrite a previous panel."""
    if output.exists():
        raise FileExistsError("preserve existing panel; do not redraw it")
    output.mkdir(parents=True)
    fixed, setup = public_inputs()
    site_a = setup.exposure_score[setup.site_rows, setup.site_cols]
    certificate = hazard_box_certificate(setup.exposure_score, site_a)
    if not certificate["passes"]:
        raise RuntimeError("public map exceeds the certified integration domain")
    rows = [
        generate_open_history(fixed, setup, truth, seeds)
        for truth, seeds in zip(panel_truths(), seed_records(), strict=True)
    ]
    observations = output / "observations.npz"
    evaluator = output / "evaluator.npz"
    np.savez_compressed(
        observations,
        predator_counts=np.stack([row[0]["predator_counts"] for row in rows]),
        prey_counts=np.stack([row[0]["prey_counts"] for row in rows]),
        opaque_ids=np.asarray([row[0]["opaque_id"] for row in rows]),
        site_ids=np.asarray(setup.site_ids),
        site_splits=np.asarray(setup.site_splits),
        site_cluster_ids=np.asarray(setup.site_cluster_ids),
        site_rows=setup.site_rows,
        site_cols=setup.site_cols,
        prey_times=PREY_TIMES,
        predator_times=PREDATOR_TIMES,
        map_a=setup.exposure_score,
        site_a=site_a,
    )
    np.savez_compressed(
        evaluator,
        arrival=np.stack([row[1]["arrival"] for row in rows]),
        loss=np.stack([row[1]["loss"] for row in rows]),
        site_hazard=np.stack([row[1]["site_hazard"] for row in rows]),
        site_detection=np.stack([row[1]["site_detection"] for row in rows]),
        prey_alive=np.stack([row[1]["prey_alive"] for row in rows]),
    )
    manifest = {
        "status": "open_development_panel",
        "truths": [asdict(truth) for truth in panel_truths()],
        "seeds": seed_records(),
        "observation_sha256": file_sha256(observations),
        "evaluator_sha256": file_sha256(evaluator),
        "hazard_box_certificate": certificate,
        "number_of_histories": 16,
        "prey_cohort_start": -60,
        "prey_visits_per_occasion": 2,
        "unreachable_map_ties": setup.unreachable_tie_count,
    }
    write_json(output / "manifest.json", manifest)
    return manifest
