"""Paired six-case campaign for the cost of estimating spread speed."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import socket
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import arc2c_likelihood as likelihood
from latent_landscapes.arc2c_design import (
    BACKGROUND_HAZARD,
    DETECTION_PROBABILITY,
    LANES,
    TRUTHS,
    BridgeConfig,
    BridgeTruth,
    timing_config,
)
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal011 import benchmark as goal011

DEFAULT_OUTPUT_DIR = Path("artifacts/arc2c_campaign")
DEFAULT_CONFIG = BridgeConfig()
EXPECTED_FILES = ("profiles.npz", "run_summary.json", "seed_provenance.json")
TIMING_BANK_FILENAME = "base_arrivals.npy"
EVENT_DIAGNOSTICS = (
    "true_extirpations_by_day60",
    "pre_arrival_true_extirpations",
    "post_arrival_true_extirpations",
    "true_extirpation_censoring",
    "post_arrival_at_risk_exposure",
    "prey_observation_support",
)
RunMode = Literal["smoke", "timing", "production"]
ProfileBundle = dict[str, NDArray[Any]]
Progress = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class DatasetProfiles:
    effect_truth_lr: NDArray[np.float64]
    spread_truth_lr: float
    effect_drops: NDArray[np.float64]
    spread_drops: NDArray[np.float64]
    effect_mle: NDArray[np.float64]
    spread_mle: float
    conditional_advantage: NDArray[np.float64]
    joint_advantage: NDArray[np.float64]
    conditional_null_rho_independent: bool


@dataclass(frozen=True, slots=True)
class DatasetBlock:
    profiles: tuple[DatasetProfiles, ...]
    event_diagnostics: NDArray[np.float64]
    training_joint: NDArray[np.float64] | None
    histories_valid: bool
    shared_random_numbers_valid: bool


@dataclass(frozen=True, slots=True)
class CampaignResult:
    config: BridgeConfig
    mode: RunMode
    seed_manifest: arc2b.SeedManifest
    profiles: ProfileBundle
    invariants: dict[str, bool]
    workers: int
    runtime_seconds: float
    bank_runtime_seconds: float
    integration_runtime_seconds: float
    calibration_runtime_seconds: float
    validation_runtime_seconds: float
    source_commit: str
    bank_checksum: str
    base_arrivals: NDArray[np.float64]

    @property
    def outcome(self) -> str:
        if not all(self.invariants.values()):
            return "implementation_blocked"
        if self.config.is_production:
            return "ready_for_arc2c_synthesis"
        return f"non_scientific_{self.mode}"


def spawn_seed_manifest(config: BridgeConfig) -> arc2b.SeedManifest:
    """Reuse the nine-root Arc 2B schedule with the independent Arc 2C seed."""
    adapter = arc2b.CampaignConfig(
        master_seed=config.master_seed,
        bank_size=config.bank_size,
        calibration_replicates=config.calibration_replicates,
        validation_replicates=config.validation_replicates,
        calibration_rank_one_based=config.calibration_rank,
        effect_grid=config.effects,
    )
    return arc2b.spawn_seed_manifest(adapter)


def _grid_index(values: NDArray[np.float64], truth: float) -> int:
    indices = np.flatnonzero(np.isclose(values, truth, rtol=0, atol=1e-12))
    if len(indices) != 1:
        raise ValueError("generating value must occur exactly once on its grid")
    return int(indices[0])


def profile_dataset(
    training_joint: NDArray[np.float64],
    holdout_joint: NDArray[np.float64],
    holdout_predator: NDArray[np.float64],
    *,
    rhos: NDArray[np.float64],
    effects: NDArray[np.float64],
    truth: BridgeTruth,
    holdout_count: int = 40,
) -> DatasetProfiles:
    """Fit on training values, then score the two fits on held-out observations."""
    expected = (len(rhos), len(effects))
    if (
        training_joint.shape != expected
        or holdout_joint.shape != expected
        or holdout_predator.shape != (len(rhos),)
        or holdout_count != 40
        or not all(
            np.isfinite(values).all()
            for values in (training_joint, holdout_joint, holdout_predator)
        )
    ):
        raise ValueError("likelihood arrays or the frozen holdout count are invalid")
    true_rho = _grid_index(rhos, truth.rho)
    true_effect = _grid_index(effects, truth.effect)
    null_effect = _grid_index(effects, 1.0)
    known_effect = int(np.argmax(training_joint[true_rho]))
    fitted_rho, fitted_effect = (
        int(value) for value in np.unravel_index(np.argmax(training_joint), expected)
    )
    fit_indices = ((true_rho, known_effect), (fitted_rho, fitted_effect))
    effect_profiles = np.stack((training_joint[true_rho], training_joint.max(axis=0)))
    spread_profile = training_joint.max(axis=1)
    effect_drops = 2.0 * (effect_profiles.max(axis=1, keepdims=True) - effect_profiles)
    spread_drops = 2.0 * (spread_profile.max() - spread_profile)

    # At HR=1 the prey marginal is independent of spread, even after conditioning.
    conditional_null = holdout_joint[:, null_effect] - holdout_predator
    null_identity = bool(np.allclose(conditional_null, conditional_null[0], rtol=0, atol=1e-9))
    null_rho = int(np.argmax(training_joint[:, null_effect]))
    conditional_advantage = np.asarray(
        [
            (holdout_joint[r, h] - holdout_predator[r] - conditional_null[0]) / holdout_count
            for r, h in fit_indices
        ],
        dtype=np.float64,
    )
    joint_advantage = np.asarray(
        [
            (holdout_joint[r, h] - holdout_joint[null_r, null_effect]) / holdout_count
            for (r, h), null_r in zip(fit_indices, (true_rho, null_rho), strict=True)
        ],
        dtype=np.float64,
    )
    return DatasetProfiles(
        effect_truth_lr=effect_drops[:, true_effect],
        spread_truth_lr=float(spread_drops[true_rho]),
        effect_drops=effect_drops,
        spread_drops=spread_drops,
        effect_mle=np.asarray([effects[h] for _, h in fit_indices], dtype=np.float64),
        spread_mle=float(rhos[fitted_rho]),
        conditional_advantage=conditional_advantage,
        joint_advantage=joint_advantage,
        conditional_null_rho_independent=null_identity,
    )


def _shared_random_numbers_valid(
    histories: tuple[tuple[arc2b.CrossLayerHistory, ...], ...],
) -> bool:
    if len(histories) != len(TRUTHS):
        return False
    for wave_start in (0, 3):
        reference = histories[wave_start]
        if any(
            row.true_predator_arrival != base.true_predator_arrival
            or row.predator_detection_counts != base.predator_detection_counts
            for rows in histories[wave_start + 1 : wave_start + 3]
            for base, row in zip(reference, rows, strict=True)
        ):
            return False
    return all(
        slow.true_predator_arrival == 2.0 * usual.true_predator_arrival
        and math.isclose(
            slow.true_prey_extirpation,
            usual.true_prey_extirpation,
            rel_tol=1e-12,
            abs_tol=1e-12,
        )
        and slow.prey_detection_counts == usual.prey_detection_counts
        for usual, slow in zip(histories[0], histories[3], strict=True)
    )


def _dataset_task(
    fixed: goal007.FixedInputs,
    seed: arc2b.DatasetSeed,
    integration: likelihood.BridgeIntegration,
) -> DatasetBlock:
    histories = likelihood.paired_histories(fixed, seed)
    profiles: list[DatasetProfiles] = []
    diagnostics: list[tuple[int, int, int, int, float, int]] = []
    saved_training: list[NDArray[np.float64]] = []
    save_training = seed.index < 2
    for truth, records in zip(TRUTHS, histories, strict=True):
        training_joint, holdout_joint, holdout_predator = likelihood.evaluate_dataset(
            records, integration
        )
        profiles.append(
            profile_dataset(
                training_joint,
                holdout_joint,
                holdout_predator,
                rhos=np.asarray(integration.rhos),
                effects=np.asarray(integration.effects),
                truth=truth,
            )
        )
        diagnostics.append(
            arc2b._extirpation_metrics(tuple(row for row in records if row.split == "training"))
        )
        if save_training:
            saved_training.append(training_joint)
    return DatasetBlock(
        tuple(profiles),
        np.asarray(diagnostics, dtype=np.float64),
        np.stack(saved_training) if save_training else None,
        all(arc2b._histories_valid(records) for records in histories),
        _shared_random_numbers_valid(histories),
    )


def _print_progress(message: str) -> None:
    print(f"{datetime.now(UTC).isoformat()} Arc2C {message}", flush=True)


def _run_phase(
    fixed: goal007.FixedInputs,
    seeds: tuple[arc2b.DatasetSeed, ...],
    integration: likelihood.BridgeIntegration,
    *,
    workers: int,
    progress: Progress | None,
) -> tuple[DatasetBlock, ...]:
    started = time.perf_counter()
    phase = seeds[0].phase
    count = len(seeds)
    interval = max(1, min(10, count // 10))
    blocks: list[DatasetBlock] = []

    def collect(results: Iterator[DatasetBlock]) -> None:
        for index, block in enumerate(results, start=1):
            blocks.append(block)
            if progress is not None and (index % interval == 0 or index == count):
                progress(
                    f"{phase} completed={index}/{count} paired_cases={len(TRUTHS)} "
                    f"elapsed_seconds={time.perf_counter() - started:.3f}"
                )

    if progress is not None:
        progress(f"{phase} started datasets={count} paired_cases={len(TRUTHS)} workers={workers}")
    if workers == 1:
        collect(_dataset_task(fixed, seed, integration) for seed in seeds)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            collect(executor.map(lambda seed: _dataset_task(fixed, seed, integration), seeds))
    return tuple(blocks)


def _assemble_profiles(
    config: BridgeConfig,
    calibration: tuple[DatasetBlock, ...],
    validation: tuple[DatasetBlock, ...],
    truths: tuple[BridgeTruth, ...] = TRUTHS,
) -> ProfileBundle:
    def training_prefix(blocks: tuple[DatasetBlock, ...]) -> NDArray[np.float64]:
        surfaces = []
        for block in blocks[:2]:
            if block.training_joint is None:
                raise RuntimeError(
                    "first two phase histories must retain their training likelihoods"
                )
            surfaces.append(block.training_joint)
        return np.stack(surfaces, axis=1)

    return {
        "rhos": np.asarray(config.rhos, dtype=np.float64),
        "effects": np.asarray(config.effects, dtype=np.float64),
        "condition_ids": np.asarray([truth.condition_id for truth in truths]),
        "lanes": np.asarray(LANES),
        "calibration_effect_lr": np.stack(
            [np.stack([row.effect_truth_lr for row in block.profiles]) for block in calibration],
            axis=2,
        ),
        "calibration_spread_lr": np.stack(
            [np.asarray([row.spread_truth_lr for row in block.profiles]) for block in calibration],
            axis=1,
        ),
        "validation_effect_drops": np.stack(
            [np.stack([row.effect_drops for row in block.profiles]) for block in validation],
            axis=2,
        ),
        "validation_spread_drops": np.stack(
            [np.stack([row.spread_drops for row in block.profiles]) for block in validation],
            axis=1,
        ),
        "validation_effect_mle": np.stack(
            [np.stack([row.effect_mle for row in block.profiles]) for block in validation],
            axis=2,
        ),
        "validation_spread_mle": np.stack(
            [np.asarray([row.spread_mle for row in block.profiles]) for block in validation],
            axis=1,
        ),
        "conditional_advantage": np.stack(
            [
                np.stack([row.conditional_advantage for row in block.profiles])
                for block in validation
            ],
            axis=2,
        ),
        "joint_advantage": np.stack(
            [np.stack([row.joint_advantage for row in block.profiles]) for block in validation],
            axis=2,
        ),
        "calibration_train_joint": training_prefix(calibration),
        "validation_train_joint": training_prefix(validation),
        "event_diagnostics": np.stack([block.event_diagnostics for block in validation], axis=1),
    }


def _seeds_disjoint(manifest: arc2b.SeedManifest) -> bool:
    values = [
        *manifest.bank_seeds,
        *(
            value
            for row in (*manifest.calibration, *manifest.validation)
            for value in (
                row.process_seed,
                row.predator_detection_seed,
                row.prey_seed,
                row.prey_detection_seed,
            )
        ),
    ]
    return len(values) == len(set(values))


def _load_bank_cache(
    directory: Path, bank_seeds: tuple[int, ...], site_ids: tuple[str, ...]
) -> NDArray[np.float64]:
    bank = np.asarray(
        np.load(directory / "base_arrivals.npy", allow_pickle=False), dtype=np.float64
    )
    receipt = json.loads((directory / "bank_cache.json").read_text(encoding="utf-8"))
    if (
        bank.shape != (len(bank_seeds), len(site_ids))
        or not np.isfinite(bank).all()
        or (bank < 0).any()
        or not isinstance(receipt, dict)
        or receipt.get("bank_checksum") != hashlib.sha256(bank.tobytes(order="C")).hexdigest()
        or receipt.get("bank_seeds") != list(bank_seeds)
        or receipt.get("site_ids") != list(site_ids)
    ):
        raise ValueError("arrival bank cache differs from the requested seeds, sites, or checksum")
    return bank


def run_campaign(
    config: BridgeConfig = DEFAULT_CONFIG,
    *,
    mode: RunMode | None = None,
    workers: int = 1,
    source_commit: str = "unknown",
    progress: Progress | None = _print_progress,
    bank_cache_dir: Path | None = None,
) -> CampaignResult:
    if workers <= 0:
        raise ValueError("workers must be positive")
    selected_mode: RunMode = mode or (
        "production" if config.is_production else "timing" if config == timing_config() else "smoke"
    )
    if (selected_mode == "production") != config.is_production:
        raise ValueError("production mode requires the exact frozen production configuration")
    started = time.perf_counter()
    if progress is not None:
        progress(f"run started mode={selected_mode} source_commit={source_commit}")
    fixed = goal011.build_fixed_inputs()
    manifest = spawn_seed_manifest(config)
    sites = tuple(sorted(fixed.design.sites, key=lambda value: value.site_id))
    bank_started = time.perf_counter()
    if progress is not None:
        progress(f"arrival bank started draws={config.bank_size} sites={len(sites)}")
    bank = (
        arc2b._generate_bank(fixed, manifest.bank_seeds)
        if bank_cache_dir is None
        else _load_bank_cache(
            bank_cache_dir, manifest.bank_seeds, tuple(site.site_id for site in sites)
        )
    )
    bank_runtime = time.perf_counter() - bank_started
    if progress is not None:
        progress(f"arrival bank complete elapsed_seconds={bank_runtime:.3f}")
    integration_started = time.perf_counter()
    integration = likelihood.build_joint_integration(
        bank,
        tuple(site.site_id for site in sites),
        config.rhos,
        config.effects,
        background_hazard=BACKGROUND_HAZARD,
    )
    integration_runtime = time.perf_counter() - integration_started
    if progress is not None:
        progress(
            f"joint integration complete rho_points={len(config.rhos)} "
            f"effect_points={len(config.effects)} elapsed_seconds={integration_runtime:.3f}"
        )
    calibration_started = time.perf_counter()
    calibration = _run_phase(
        fixed, manifest.calibration, integration, workers=workers, progress=progress
    )
    calibration_runtime = time.perf_counter() - calibration_started
    validation_started = time.perf_counter()
    validation = _run_phase(
        fixed, manifest.validation, integration, workers=workers, progress=progress
    )
    validation_runtime = time.perf_counter() - validation_started
    profiles = _assemble_profiles(config, calibration, validation)
    all_blocks = (*calibration, *validation)
    invariants = {
        "fixed_inputs_reconciled": all(fixed.invariants.values()),
        "cluster_isolated_training120_holdout40": (
            sum(site.split == "training" for site in sites) == 120
            and sum(site.split == "holdout" for site in sites) == 40
            and {site.cluster_id for site in sites if site.split == "training"}.isdisjoint(
                {site.cluster_id for site in sites if site.split == "holdout"}
            )
        ),
        "shared_bank_shape": bank.shape == (config.bank_size, len(sites)),
        "bank_checksum_reconciled": integration.bank_checksum
        == hashlib.sha256(np.ascontiguousarray(bank).tobytes()).hexdigest(),
        "paired_calibration_count": len(calibration) == config.calibration_replicates
        and all(len(block.profiles) == len(TRUTHS) for block in calibration),
        "paired_validation_count": len(validation) == config.validation_replicates
        and all(len(block.profiles) == len(TRUTHS) for block in validation),
        "phase_roots_disjoint": _seeds_disjoint(manifest),
        "histories_valid": all(block.histories_valid for block in all_blocks),
        "shared_random_numbers_valid": all(
            block.shared_random_numbers_valid for block in all_blocks
        ),
        "conditional_null_rho_independent": all(
            row.conditional_null_rho_independent for block in all_blocks for row in block.profiles
        ),
        "finite_profiles": all(
            np.isfinite(values).all() for values in profiles.values() if values.dtype.kind in "fiu"
        ),
        "nonnegative_profile_drops": all(
            (profiles[name] >= 0).all()
            for name in (
                "calibration_effect_lr",
                "calibration_spread_lr",
                "validation_effect_drops",
                "validation_spread_drops",
            )
        ),
    }
    result = CampaignResult(
        config=config,
        mode=selected_mode,
        seed_manifest=manifest,
        profiles=profiles,
        invariants=invariants,
        workers=workers,
        runtime_seconds=time.perf_counter() - started,
        bank_runtime_seconds=bank_runtime,
        integration_runtime_seconds=integration_runtime,
        calibration_runtime_seconds=calibration_runtime,
        validation_runtime_seconds=validation_runtime,
        source_commit=source_commit,
        bank_checksum=integration.bank_checksum,
        base_arrivals=bank,
    )
    if progress is not None:
        progress(
            f"run complete outcome={result.outcome} elapsed_seconds={result.runtime_seconds:.3f}"
        )
    return result


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_campaign_bundle(result: CampaignResult, output_dir: Path) -> tuple[Path, ...]:
    """Write compressed replay profiles and compact run/seed provenance."""
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_path = output_dir / "profiles.npz"
    np.savez_compressed(profile_path, allow_pickle=False, **result.profiles)
    if result.mode == "timing":
        np.save(output_dir / TIMING_BANK_FILENAME, result.base_arrivals, allow_pickle=False)
    completed = datetime.now(UTC).isoformat()
    _write_json(
        output_dir / "run_summary.json",
        {
            "workflow": "arc2c-spread-prey-oracle-bridge",
            "schema_version": 1,
            "outcome": result.outcome,
            "mode": result.mode,
            "is_production": result.config.is_production,
            "config": asdict(result.config),
            "truths": [asdict(truth) for truth in TRUTHS],
            "lanes": LANES,
            "source_commit": result.source_commit,
            "bank_checksum": result.bank_checksum,
            "profile_bundle_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
            "invariants": {name: bool(value) for name, value in result.invariants.items()},
            "counts": {
                "conditions": len(TRUTHS),
                "lanes": len(LANES),
                "sites": 160,
                "training_sites": 120,
                "holdout_sites": 40,
                "bank_draws": result.config.bank_size,
                "calibration_datasets_per_condition": result.config.calibration_replicates,
                "validation_datasets_per_condition": result.config.validation_replicates,
                "calibration_condition_datasets": (
                    len(TRUTHS) * result.config.calibration_replicates
                ),
                "validation_condition_datasets": len(TRUTHS) * result.config.validation_replicates,
            },
            "runtimes_seconds": {
                "total": result.runtime_seconds,
                "bank": result.bank_runtime_seconds,
                "integration": result.integration_runtime_seconds,
                "calibration": result.calibration_runtime_seconds,
                "validation": result.validation_runtime_seconds,
            },
            "workers": result.workers,
            "completed_utc": completed,
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "notes": {
                "inference": "All MLE and profile reductions use only the 120 training sites.",
                "drop_convention": "2 * (maximum profile log likelihood - profile log likelihood)",
                "score_units": "Mean heldout log-score advantage per site over matched HR=1 null.",
                "conditional_null": "Same rho-independent conditional prey null for both lanes.",
                "joint_null": (
                    "True rho in known_speed; its own training HR=1 fit in estimated_speed."
                ),
                "mle_ties": "First row-major joint maximum, on ascending rho and effect grids.",
                "representative_dataset": (
                    "First validation dataset (zero-based index 0), preselected."
                ),
                "event_diagnostics_sites": 120,
                "event_diagnostics_role": (
                    "Training-site truth-assisted explanatory diagnostics; not inference inputs."
                ),
                "event_diagnostics_order": EVENT_DIAGNOSTICS,
                "background_hazard": BACKGROUND_HAZARD,
                "predator_detection_probability": DETECTION_PROBABILITY,
                "prey_detection_probability": DETECTION_PROBABILITY,
                "parallelism": "Bounded dataset threads; pin BLAS/OpenMP threads externally.",
                "saved_timing_bank": TIMING_BANK_FILENAME if result.mode == "timing" else None,
            },
        },
    )
    _write_json(
        output_dir / "seed_provenance.json",
        {
            "master_seed": result.config.master_seed,
            "schedule": "Arc 2B nine-root SeedSequence schedule with Arc 2C master seed",
            "root_allocation": {
                "integration": [0],
                "calibration_process_predator_prey_prey_detection": [1, 2, 3, 4],
                "validation_process_predator_prey_prey_detection": [5, 6, 7, 8],
            },
            "bank_size": result.config.bank_size,
            "bank_checksum": result.bank_checksum,
            "bank_seeds": result.seed_manifest.bank_seeds,
            "calibration_seeds": [asdict(seed) for seed in result.seed_manifest.calibration],
            "validation_seeds": [asdict(seed) for seed in result.seed_manifest.validation],
            "phase_roots_disjoint": result.invariants["phase_roots_disjoint"],
            "pairing": (
                "One complete dataset index shares all streams across six cases and two fits."
            ),
            "source_commit": result.source_commit,
            "completed_utc": completed,
        },
    )
    names = (*EXPECTED_FILES, TIMING_BANK_FILENAME) if result.mode == "timing" else EXPECTED_FILES
    return tuple(output_dir / name for name in names)
