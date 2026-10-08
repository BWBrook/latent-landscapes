"""Known-nuisance, finite-grid calibration for Goal 049.

The module deliberately separates three roles.  The generator may know an
effect in order to simulate a calibration row.  The analyst sees only opaque
observation datasets and fixed nuisance inputs.  The evaluator joins effect
truths only after all score arrays have been flushed and hashed.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import platform
import socket
import time
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
from numpy.lib.format import open_memmap
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes.arc2b_design import REFERENCE_BACKGROUND_RISK, TruthCondition
from latent_landscapes.arc2c_design import BridgeConfig
from latent_landscapes.arc2c_likelihood import BridgeIntegration, build_joint_integration
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.integration_weights import reweight_integration

RunMode = Literal["smoke", "timing", "production"]
Progress = Callable[[str], None]
FloatArray = NDArray[np.float64]

EFFECT_GRID = tuple(float(value) for value in np.linspace(1.0, 10.0, 181))
EVALUATION_TRUTHS = (1.0, 2.0, 3.0, 4.0, 5.0, 10.0)
VARIANT_IDS = (
    "low_k65536_alpha050",
    "high_k131072_alpha100",
    "high_k131072_alpha050",
    "high_k131072_alpha025",
)
VARIANT_SPECS = (
    (65_536, 0.5),
    (131_072, 1.0),
    (131_072, 0.5),
    (131_072, 0.25),
)
CALIBRATION_ROOT = 2026092001
EVALUATION_ROOT = 2026092002
BOOTSTRAP_ROOT = 2026092003
ARCHIVED_BANK_ROOT = 20260905
SMOKE_BANK_ROOT = 2026092000
CALIBRATION_REPLICATES = 999
EVALUATION_REPLICATES = 1_000
CALIBRATION_RANK = 950
BACKGROUND_HAZARD = 0.002
DETECTION_PROBABILITY = 0.65
REGISTRATION_SHA256 = "be4b6b35ebf3d3808d1b658c90a8c22c78b0dad3dc4e1ab8993d0c7a8a7aebbc"
HIGH_BANK_FILE_SHA256 = "d4f564030cf1ece2b56d3f735e4c2e12d3ec76eeba3c85f43a425bdeb5841dd9"
HIGH_BANK_ARRAY_SHA256 = "9232bcd19f67817b802fe75a8c24fa61a143d17f3a1f950c0dffc9f0d6560e73"
LOW_BANK_ARRAY_SHA256 = "6e5ca1d19c1f825f608453c5692cfb8e327b11ed19208e232f5309658b2cb833"
CHI_SQUARE_95 = 3.84146
DEFAULT_OUTPUT_DIR = Path("artifacts/goal049_known_nuisance")


@dataclass(frozen=True, slots=True)
class CampaignConfig:
    """A complete scoring contract; only smoke counts and bank sizes are tunable."""

    mode: RunMode
    effects: tuple[float, ...]
    evaluation_truths: tuple[float, ...]
    calibration_replicates: int
    evaluation_replicates: int
    calibration_rank: int
    low_bank_size: int
    high_bank_size: int
    calibration_root: int = CALIBRATION_ROOT
    evaluation_root: int = EVALUATION_ROOT
    bootstrap_root: int = BOOTSTRAP_ROOT
    bank_root: int = ARCHIVED_BANK_ROOT

    def __post_init__(self) -> None:
        effects = np.asarray(self.effects, dtype=np.float64)
        truths = np.asarray(self.evaluation_truths, dtype=np.float64)
        if (
            effects.ndim != 1
            or not len(effects)
            or not np.isfinite(effects).all()
            or np.any(np.diff(effects) <= 0)
            or effects[0] != 1.0
            or effects[-1] != 10.0
        ):
            raise ValueError("effects must be a finite increasing grid from 1 to 10")
        if (
            truths.ndim != 1
            or not len(truths)
            or not np.isfinite(truths).all()
            or any(not np.any(np.isclose(effects, value, rtol=0, atol=1e-12)) for value in truths)
        ):
            raise ValueError("every evaluation truth must occur exactly on the effect grid")
        if (
            self.calibration_replicates <= 0
            or self.evaluation_replicates <= 0
            or not 1 <= self.calibration_rank <= self.calibration_replicates
            or self.low_bank_size <= 0
            or self.high_bank_size < self.low_bank_size
        ):
            raise ValueError("replicate, rank, and nested bank sizes are invalid")
        roots = (self.calibration_root, self.evaluation_root, self.bootstrap_root, self.bank_root)
        if len(set(roots)) != len(roots):
            raise ValueError("bank, calibration, evaluation, and bootstrap roots must be distinct")
        if self.mode != "smoke":
            expected_counts = (
                (2, 2, 2)
                if self.mode == "timing"
                else (CALIBRATION_REPLICATES, EVALUATION_REPLICATES, CALIBRATION_RANK)
            )
            actual_counts = (
                self.calibration_replicates,
                self.evaluation_replicates,
                self.calibration_rank,
            )
            if (
                self.effects != EFFECT_GRID
                or self.evaluation_truths != EVALUATION_TRUTHS
                or actual_counts != expected_counts
                or (self.low_bank_size, self.high_bank_size) != (65_536, 131_072)
                or self.bank_root != ARCHIVED_BANK_ROOT
            ):
                raise ValueError("timing and production use the registered full-grid contract")

    @property
    def is_full_grid(self) -> bool:
        return self.effects == EFFECT_GRID


def production_config(mode: RunMode = "production") -> CampaignConfig:
    if mode not in ("timing", "production"):
        raise ValueError("full configuration mode must be timing or production")
    return CampaignConfig(
        mode=mode,
        effects=EFFECT_GRID,
        evaluation_truths=EVALUATION_TRUTHS,
        calibration_replicates=2 if mode == "timing" else CALIBRATION_REPLICATES,
        evaluation_replicates=2 if mode == "timing" else EVALUATION_REPLICATES,
        calibration_rank=2 if mode == "timing" else CALIBRATION_RANK,
        low_bank_size=65_536,
        high_bank_size=131_072,
    )


def smoke_config(
    *,
    calibration_replicates: int = 2,
    evaluation_replicates: int = 2,
    low_bank_size: int = 8,
    high_bank_size: int = 16,
) -> CampaignConfig:
    return CampaignConfig(
        mode="smoke",
        effects=(1.0, 3.0, 10.0),
        evaluation_truths=(1.0, 3.0, 10.0),
        calibration_replicates=calibration_replicates,
        evaluation_replicates=evaluation_replicates,
        calibration_rank=min(
            calibration_replicates, max(1, math.ceil(0.95 * calibration_replicates))
        ),
        low_bank_size=low_bank_size,
        high_bank_size=high_bank_size,
        bank_root=SMOKE_BANK_ROOT,
    )


@dataclass(frozen=True, slots=True)
class AnalystHistory:
    """Observation-only site history exposed to the scoring interface."""

    site_id: str
    cluster_id: str
    split: str
    predator_detection_counts: tuple[int, ...]
    prey_detection_counts: tuple[int, ...]
    prey_detection_probability: float = DETECTION_PROBABILITY


@dataclass(frozen=True, slots=True)
class AnalystDataset:
    opaque_id: str
    histories: tuple[AnalystHistory, ...]


@dataclass(frozen=True, slots=True)
class AnalystScore:
    likelihood_ratio_profile: FloatArray
    holdout_log_likelihood: FloatArray


@dataclass(frozen=True, slots=True)
class PhaseSeeds:
    root: int
    phase: str
    records: tuple[arc2b.DatasetSeed, ...]


@dataclass(frozen=True, slots=True)
class ScoringVariants:
    ids: tuple[str, ...]
    integrations: tuple[BridgeIntegration, ...]
    construction_seconds: dict[str, float]


@dataclass(frozen=True, slots=True)
class CampaignResult:
    output_dir: Path
    config: CampaignConfig
    run_summary: dict[str, Any]


def _seed_int(sequence: np.random.SeedSequence) -> int:
    return int(sequence.generate_state(1, dtype=np.uint64)[0])


def spawn_phase_seeds(root: int, phase: str, count: int) -> PhaseSeeds:
    """Spawn four independent streams, shared across truths within each replicate."""
    if count <= 0 or phase not in {"calibration", "evaluation"}:
        raise ValueError("phase and count are invalid")
    stream_roots = np.random.SeedSequence(root).spawn(4)
    streams = [tuple(_seed_int(child) for child in parent.spawn(count)) for parent in stream_roots]
    records = tuple(
        arc2b.DatasetSeed(phase, index, *(stream[index] for stream in streams))
        for index in range(count)
    )
    return PhaseSeeds(root, phase, records)


def _seed_fingerprint(seed: arc2b.DatasetSeed) -> str:
    return hashlib.sha256(
        json.dumps(asdict(seed), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _opaque_ids(config: CampaignConfig, seed: arc2b.DatasetSeed, count: int) -> tuple[str, ...]:
    """Draw labels from a distinct deterministic stream without embedding a truth value."""
    root = config.calibration_root if seed.phase == "calibration" else config.evaluation_root
    generator = np.random.default_rng(np.random.SeedSequence([root, seed.index, 0x4944]))
    words = generator.integers(0, 2**64, size=(count, 2), dtype=np.uint64)
    return tuple(f"{int(first):016x}{int(second):016x}" for first, second in words)


def _truths(effects: Sequence[float]) -> tuple[TruthCondition, ...]:
    return tuple(
        TruthCondition(
            f"generator_{index:03d}",
            "generator_only",
            float(effect),
            float(REFERENCE_BACKGROUND_RISK),
            DETECTION_PROBABILITY,
        )
        for index, effect in enumerate(effects)
    )


def _generator_config(
    config: CampaignConfig, truths: tuple[TruthCondition, ...], phase: str
) -> arc2b.CampaignConfig:
    return arc2b.CampaignConfig(
        master_seed=(config.calibration_root if phase == "calibration" else config.evaluation_root),
        bank_size=config.high_bank_size,
        calibration_replicates=config.calibration_replicates,
        validation_replicates=config.evaluation_replicates,
        calibration_rank_one_based=config.calibration_rank,
        effect_grid=config.effects,
        truths=truths,
    )


def generate_observations(
    fixed: FixedInputs,
    seed: arc2b.DatasetSeed,
    effects: Sequence[float],
    config: CampaignConfig,
) -> tuple[AnalystDataset, ...]:
    """Generate complete original-process histories and immediately strip truth state."""
    truths = _truths(effects)
    generated = arc2b.generate_paired_datasets(
        fixed, seed, truths, _generator_config(config, truths, seed.phase)
    )
    opaque_ids = _opaque_ids(config, seed, len(generated))
    observations: list[AnalystDataset] = []
    for truth_ordinal, dataset in enumerate(generated):
        histories = tuple(
            AnalystHistory(
                row.site_id,
                row.cluster_id,
                row.split,
                row.predator_detection_counts,
                row.prey_detection_counts,
                row.prey_detection_probability,
            )
            for row in dataset.records
        )
        observations.append(AnalystDataset(opaque_ids[truth_ordinal], histories))
    return tuple(observations)


def score_observations(dataset: AnalystDataset, integration: BridgeIntegration) -> AnalystScore:
    """Score observations without accepting any generating truth or latent process state."""
    training, holdout, _ = __import__(
        "latent_landscapes.arc2c_likelihood", fromlist=["evaluate_dataset"]
    ).evaluate_dataset(cast(Any, dataset.histories), integration)
    if training.shape[0] != 1 or holdout.shape != training.shape:
        raise ValueError("known-nuisance scoring requires exactly the supplied rho=1 slice")
    profile = np.asarray(training[0], dtype=np.float64)
    drops = np.maximum(0.0, 2.0 * (float(profile.max()) - profile))
    heldout = np.asarray(holdout[0], dtype=np.float64)
    if not np.isfinite(drops).all() or not np.isfinite(heldout).all() or drops.min() != 0.0:
        raise RuntimeError("analyst scoring produced an invalid profile")
    return AnalystScore(drops, heldout)


def _file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _array_sha256(array: NDArray[Any]) -> str:
    digest = hashlib.sha256()
    contiguous = np.ascontiguousarray(array)
    digest.update(memoryview(contiguous).cast("B"))
    return digest.hexdigest()


def _json_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _expected_archived_bank_seeds(size: int) -> tuple[int, ...]:
    config = BridgeConfig(master_seed=ARCHIVED_BANK_ROOT, bank_size=size)
    values = (
        __import__("latent_landscapes.arc2c_campaign", fromlist=["spawn_seed_manifest"])
        .spawn_seed_manifest(config)
        .bank_seeds
    )
    return cast(tuple[int, ...], values)


def load_verified_bank(
    cache_dir: Path, config: CampaignConfig, site_ids: tuple[str, ...]
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    """Load the exact nested Goal 045 high bank, or make a bounded smoke bank."""
    if config.mode == "smoke":
        seeds = tuple(
            _seed_int(child)
            for child in np.random.SeedSequence(config.bank_root).spawn(config.high_bank_size)
        )
        fixed = goal011.build_fixed_inputs()
        bank = np.asarray(arc2b._generate_bank(fixed, seeds), dtype=np.float64)
        return bank, {
            "kind": "generated_smoke_bank",
            "bank_root": config.bank_root,
            "bank_seeds_sha256": _json_sha256(seeds),
            "bank_checksum": _array_sha256(bank),
            "bank_shape": list(bank.shape),
        }

    bank_path = cache_dir / "base_arrivals.npy"
    receipt_path = cache_dir / "bank_cache.json"
    bank = np.load(bank_path, mmap_mode="r", allow_pickle=False)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected_seeds = _expected_archived_bank_seeds(config.high_bank_size)
    low = np.asarray(bank[: config.low_bank_size])
    if (
        bank.shape != (config.high_bank_size, len(site_ids))
        or bank.dtype != np.float64
        or not np.isfinite(bank).all()
        or (bank < 0).any()
        or receipt.get("bank_seeds") != list(expected_seeds)
        or receipt.get("site_ids") != list(site_ids)
        or receipt.get("bank_checksum") != HIGH_BANK_ARRAY_SHA256
        or receipt.get("bank_file_sha256") != HIGH_BANK_FILE_SHA256
        or _file_sha256(bank_path) != HIGH_BANK_FILE_SHA256
        or _array_sha256(bank) != HIGH_BANK_ARRAY_SHA256
        or _array_sha256(low) != LOW_BANK_ARRAY_SHA256
    ):
        raise ValueError("arrival bank does not match the registered nested Goal 045 bank")
    return bank, {
        "kind": "verified_goal045_nested_bank",
        "bank_root": ARCHIVED_BANK_ROOT,
        "bank_path": str(bank_path.resolve()),
        "bank_file_sha256": HIGH_BANK_FILE_SHA256,
        "bank_checksum": HIGH_BANK_ARRAY_SHA256,
        "low_prefix_checksum": LOW_BANK_ARRAY_SHA256,
        "bank_seeds_sha256": _json_sha256(expected_seeds),
        "bank_shape": list(bank.shape),
    }


def build_scoring_variants(
    bank: NDArray[np.float64], config: CampaignConfig, site_ids: tuple[str, ...]
) -> ScoringVariants:
    """Build only rho=1 sufficient statistics, then reweight the high bank."""
    started = time.perf_counter()
    low = build_joint_integration(
        np.asarray(bank[: config.low_bank_size]),
        site_ids,
        (1.0,),
        config.effects,
        BACKGROUND_HAZARD,
    )
    low_seconds = time.perf_counter() - started
    started = time.perf_counter()
    high_alpha050 = build_joint_integration(
        np.asarray(bank[: config.high_bank_size]),
        site_ids,
        (1.0,),
        config.effects,
        BACKGROUND_HAZARD,
    )
    high_seconds = time.perf_counter() - started
    started = time.perf_counter()
    high_alpha100 = reweight_integration(
        high_alpha050,
        config.high_bank_size,
        from_pseudocount=0.5,
        to_pseudocount=1.0,
        background_hazard=BACKGROUND_HAZARD,
    )
    high_alpha025 = reweight_integration(
        high_alpha050,
        config.high_bank_size,
        from_pseudocount=0.5,
        to_pseudocount=0.25,
        background_hazard=BACKGROUND_HAZARD,
    )
    reweight_seconds = time.perf_counter() - started
    return ScoringVariants(
        VARIANT_IDS,
        (low, high_alpha100, high_alpha050, high_alpha025),
        {
            "low_k_alpha050": low_seconds,
            "high_k_alpha050": high_seconds,
            "high_k_reweight_alpha100_alpha025": reweight_seconds,
            "total": low_seconds + high_seconds + reweight_seconds,
        },
    )


def verify_seed_separation(
    config: CampaignConfig,
    calibration: PhaseSeeds,
    evaluation: PhaseSeeds,
    bank_provenance: dict[str, Any],
) -> dict[str, bool]:
    calibration_values = {
        value
        for row in calibration.records
        for value in (
            row.process_seed,
            row.predator_detection_seed,
            row.prey_seed,
            row.prey_detection_seed,
        )
    }
    evaluation_values = {
        value
        for row in evaluation.records
        for value in (
            row.process_seed,
            row.predator_detection_seed,
            row.prey_seed,
            row.prey_detection_seed,
        )
    }
    bank_values: set[int] = set()
    if config.mode != "smoke":
        bank_values = set(_expected_archived_bank_seeds(config.high_bank_size))
    return {
        "root_identifiers_distinct": len(
            {
                config.bank_root,
                config.calibration_root,
                config.evaluation_root,
                config.bootstrap_root,
            }
        )
        == 4,
        "calibration_iid_stream_tuples_unique": len(calibration_values)
        == 4 * config.calibration_replicates,
        "evaluation_iid_stream_tuples_unique": len(evaluation_values)
        == 4 * config.evaluation_replicates,
        "calibration_evaluation_streams_disjoint": calibration_values.isdisjoint(evaluation_values),
        "bank_history_streams_disjoint": (
            config.mode == "smoke"
            or (
                bank_values.isdisjoint(calibration_values)
                and bank_values.isdisjoint(evaluation_values)
            )
        ),
        "bank_provenance_present": bool(bank_provenance.get("bank_checksum")),
    }


def _profile_path(output_dir: Path, phase: str, variant_id: str) -> Path:
    return output_dir / f"{phase}_profiles_{variant_id}.npy"


def _holdout_path(output_dir: Path, variant_id: str) -> Path:
    return output_dir / f"evaluation_holdout_loglikelihood_{variant_id}.npy"


def _open_array(path: Path, shape: tuple[int, ...], dtype: np.dtype[Any]) -> np.memmap:
    if path.exists():
        array = np.load(path, mmap_mode="r+", allow_pickle=False)
        if array.shape != shape or array.dtype != dtype:
            raise ValueError(f"existing array has wrong schema: {path}")
        return cast(np.memmap, array)
    array = open_memmap(path, mode="w+", dtype=dtype, shape=shape)
    if np.issubdtype(dtype, np.floating):
        array.fill(np.nan)
    else:
        array.fill("")
    array.flush()
    return array


def _load_journal(path: Path, fingerprint: str) -> dict[tuple[str, int], dict[str, Any]]:
    if not path.exists():
        return {}
    completed: dict[tuple[str, int], dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("run_fingerprint") != fingerprint:
            raise ValueError("shard journal belongs to a different frozen run")
        completed[(str(row["phase"]), int(row["replicate_index"]))] = row
    return completed


def _append_journal(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()


def _score_replicate(
    fixed: FixedInputs,
    seed: arc2b.DatasetSeed,
    effects: tuple[float, ...],
    config: CampaignConfig,
    integrations: tuple[BridgeIntegration, ...],
) -> tuple[FloatArray, FloatArray, NDArray[np.str_]]:
    observations = generate_observations(fixed, seed, effects, config)
    profiles = np.empty((len(integrations), len(effects), len(config.effects)), dtype=np.float64)
    holdout = np.empty_like(profiles)
    opaque_ids = np.empty(len(effects), dtype="<U32")
    for truth_index, dataset in enumerate(observations):
        opaque_ids[truth_index] = dataset.opaque_id
        for variant_index, integration in enumerate(integrations):
            score = score_observations(dataset, integration)
            profiles[variant_index, truth_index] = score.likelihood_ratio_profile
            holdout[variant_index, truth_index] = score.holdout_log_likelihood
    return profiles, holdout, opaque_ids


def _canary_indices(values: tuple[float, ...]) -> tuple[int, ...]:
    result = []
    for target in (1.0, 3.0, 10.0):
        matches = np.flatnonzero(np.isclose(values, target, rtol=0, atol=1e-12))
        if len(matches) != 1:
            raise ValueError("canary effects 1, 3, and 10 must each occur once")
        result.append(int(matches[0]))
    return tuple(result)


def _check_canary(
    profiles: FloatArray, holdout: FloatArray, truth_values: tuple[float, ...]
) -> None:
    indices = _canary_indices(truth_values)
    selected = profiles[:, indices]
    if (
        not np.isfinite(selected).all()
        or not np.isfinite(holdout[:, indices]).all()
        or (selected < 0).any()
        or not np.all(selected.min(axis=-1) == 0.0)
    ):
        raise RuntimeError("fixed h=1,3,10 canary failed score invariants")


def _run_phase(
    *,
    phase: str,
    fixed: FixedInputs,
    seeds: PhaseSeeds,
    generating_effects: tuple[float, ...],
    config: CampaignConfig,
    variants: ScoringVariants,
    output_dir: Path,
    workers: int,
    fingerprint: str,
    progress: Progress | None,
) -> float:
    n_truths = len(generating_effects)
    n_replicates = len(seeds.records)
    n_nodes = len(config.effects)
    profile_arrays = tuple(
        _open_array(
            _profile_path(output_dir, phase, variant_id),
            (n_truths, n_replicates, n_nodes),
            np.dtype(np.float64),
        )
        for variant_id in variants.ids
    )
    holdout_arrays = (
        tuple(
            _open_array(
                _holdout_path(output_dir, variant_id),
                (n_truths, n_replicates, n_nodes),
                np.dtype(np.float64),
            )
            for variant_id in variants.ids
        )
        if phase == "evaluation"
        else ()
    )
    opaque = _open_array(
        output_dir / f"{phase}_opaque_ids.npy",
        (n_truths, n_replicates),
        np.dtype("<U32"),
    )
    journal_path = output_dir / "completed_shards.jsonl"
    journal = _load_journal(journal_path, fingerprint)

    def shard_hash(index: int) -> str:
        digest = hashlib.sha256()
        for array in profile_arrays:
            digest.update(memoryview(np.ascontiguousarray(array[:, index])).cast("B"))
        for array in holdout_arrays:
            digest.update(memoryview(np.ascontiguousarray(array[:, index])).cast("B"))
        digest.update(memoryview(np.ascontiguousarray(opaque[:, index])).cast("B"))
        return digest.hexdigest()

    pending: list[arc2b.DatasetSeed] = []
    for seed in seeds.records:
        row = journal.get((phase, seed.index))
        if (
            row is not None
            and row.get("seed_sha256") == _seed_fingerprint(seed)
            and row.get("slice_sha256") == shard_hash(seed.index)
        ):
            continue
        pending.append(seed)

    started = time.perf_counter()

    def run_one(
        seed: arc2b.DatasetSeed,
    ) -> tuple[arc2b.DatasetSeed, FloatArray, FloatArray, NDArray[np.str_]]:
        profiles, holdout, ids = _score_replicate(
            fixed, seed, generating_effects, config, variants.integrations
        )
        return seed, profiles, holdout, ids

    def store(result: tuple[arc2b.DatasetSeed, FloatArray, FloatArray, NDArray[np.str_]]) -> None:
        seed, profiles, holdout, ids = result
        for variant_index, array in enumerate(profile_arrays):
            array[:, seed.index] = profiles[variant_index]
            array.flush()
        for variant_index, array in enumerate(holdout_arrays):
            array[:, seed.index] = holdout[variant_index]
            array.flush()
        opaque[:, seed.index] = ids
        opaque.flush()
        payload = {
            "run_fingerprint": fingerprint,
            "phase": phase,
            "replicate_index": seed.index,
            "seed_sha256": _seed_fingerprint(seed),
            "slice_sha256": shard_hash(seed.index),
        }
        _append_journal(journal_path, payload)

    canary = [seed for seed in pending if seed.index < min(2, n_replicates)]
    remainder = [seed for seed in pending if seed.index >= min(2, n_replicates)]
    if canary:
        if workers > 1 and len(canary) > 1:
            with ThreadPoolExecutor(max_workers=min(workers, len(canary))) as executor:
                for result in executor.map(run_one, canary):
                    _check_canary(result[1], result[2], generating_effects)
                    store(result)
        else:
            for result in map(run_one, canary):
                _check_canary(result[1], result[2], generating_effects)
                store(result)
        if progress is not None:
            progress(f"{phase} fixed canaries h=1,3,10 passed first={len(canary)} replicates")

    if remainder:
        if workers == 1:
            iterator: Iterator[
                tuple[arc2b.DatasetSeed, FloatArray, FloatArray, NDArray[np.str_]]
            ] = map(run_one, remainder)
            for completed, result in enumerate(iterator, start=1):
                store(result)
                if progress is not None and (completed % max(1, len(remainder) // 10) == 0):
                    progress(f"{phase} completed remaining={completed}/{len(remainder)}")
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                for completed, result in enumerate(executor.map(run_one, remainder), start=1):
                    store(result)
                    if progress is not None and (completed % max(1, len(remainder) // 10) == 0):
                        progress(f"{phase} completed remaining={completed}/{len(remainder)}")
    return time.perf_counter() - started


def _source_hashes(registration_path: Path) -> dict[str, str]:
    repository = Path(__file__).resolve().parents[2]
    paths = (
        *sorted((repository / "src").rglob("*.py")),
        repository / "scripts" / "run_known_nuisance_calibration.py",
        repository / "pyproject.toml",
        repository / "uv.lock",
        registration_path.resolve(),
    )
    return {str(path.resolve().relative_to(repository)): _file_sha256(path) for path in paths}


def validate_production_budget(
    budget_receipt_path: Path,
    *,
    config: CampaignConfig,
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    """Validate the measured timing plus bootstrap ceiling before production work."""
    if config.mode != "production":
        raise ValueError("a production budget receipt only applies to production mode")
    receipt = json.loads(budget_receipt_path.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        raise ValueError("production budget receipt must be a JSON object")
    timing_path = Path(str(receipt.get("timing_summary_path", "")))
    if not timing_path.is_file() or _file_sha256(timing_path) != receipt.get(
        "timing_summary_sha256"
    ):
        raise ValueError("production budget receipt does not bind the timing summary")
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    projection = timing.get("timing_projection", {})
    bootstrap = float(receipt.get("bootstrap_seconds_reserved", math.nan))
    total = float(receipt.get("total_projected_seconds", math.nan))
    campaign = float(projection.get("campaign_excluding_bootstrap_seconds_conservative", math.nan))
    timing_config = production_config("timing")
    measured_controls = timing.get("identity_controls", {})
    if (
        timing.get("config") != json.loads(json.dumps(asdict(timing_config)))
        or timing.get("source_and_registration_sha256") != source_hashes
        or REGISTRATION_SHA256 not in source_hashes.values()
        or not measured_controls
        or not all(bool(value) for value in measured_controls.values())
        or not all(math.isfinite(value) and value >= 0 for value in (campaign, bootstrap, total))
        or total < campaign + bootstrap
        or total > 24 * 60 * 60
        or receipt.get("within_24h") is not True
    ):
        raise ValueError("timing and bootstrap evidence do not support the production ceiling")
    return cast(dict[str, Any], receipt)


def _freeze_score_files(output_dir: Path, config: CampaignConfig) -> dict[str, str]:
    names = [
        *(f"calibration_profiles_{variant}.npy" for variant in VARIANT_IDS),
        *(f"evaluation_profiles_{variant}.npy" for variant in VARIANT_IDS),
        *(f"evaluation_holdout_loglikelihood_{variant}.npy" for variant in VARIANT_IDS),
        "calibration_opaque_ids.npy",
        "evaluation_opaque_ids.npy",
    ]
    hashes = {name: _file_sha256(output_dir / name) for name in names}
    _write_json(
        output_dir / "frozen_scores.json",
        {
            "schema_version": 1,
            "completed_utc": datetime.now(UTC).isoformat(),
            "config_sha256": _json_sha256(asdict(config)),
            "files": hashes,
            "truth_joined": False,
        },
    )
    return hashes


def _components(mask: NDArray[np.bool_]) -> NDArray[np.int64]:
    return mask[:, 0].astype(np.int64) + np.sum(mask[:, 1:] & ~mask[:, :-1], axis=1)


def _method_metrics(
    membership: NDArray[np.bool_], profiles: FloatArray, effects: FloatArray, truth: float
) -> dict[str, float | int]:
    truth_index = int(np.flatnonzero(np.isclose(effects, truth, rtol=0, atol=1e-12))[0])
    ids = np.arange(len(membership))
    cardinality = membership.sum(axis=1)
    lower = np.argmax(membership, axis=1)
    upper = membership.shape[1] - 1 - np.argmax(membership[:, ::-1], axis=1)
    component_count = _components(membership)
    mle = np.argmin(profiles, axis=1)
    return {
        "n": len(membership),
        "coverage": float(np.mean(membership[:, truth_index])),
        "null_exclusion": float(np.mean(~membership[:, 0])),
        "mean_cardinality": float(np.mean(cardinality)),
        "mean_log_hull_span": float(np.mean(np.log(effects[upper] / effects[lower]))),
        "boundary_contact_frequency": float(np.mean(membership[:, 0] | membership[:, -1])),
        "disconnected_frequency": float(np.mean(component_count > 1)),
        "mean_absolute_log_point_error": float(np.mean(np.abs(np.log(effects[mle] / truth)))),
        "truth_inclusion_count": int(np.sum(membership[ids, truth_index])),
    }


def evaluate_frozen_scores(output_dir: Path, config: CampaignConfig) -> dict[str, Any]:
    """Join evaluator truths only after the score-file freeze and verify identities."""
    frozen = json.loads((output_dir / "frozen_scores.json").read_text(encoding="utf-8"))
    for name, expected in frozen["files"].items():
        if _file_sha256(output_dir / name) != expected:
            raise ValueError("a score file changed after the analyst freeze")
    effects = np.asarray(config.effects, dtype=np.float64)
    truth_indices = np.asarray(
        [
            int(np.flatnonzero(np.isclose(effects, truth, rtol=0, atol=1e-12))[0])
            for truth in config.evaluation_truths
        ],
        dtype=np.int64,
    )
    cutoffs = np.empty((len(VARIANT_IDS), len(effects)), dtype=np.float64)
    evaluation = []
    for variant_index, variant_id in enumerate(VARIANT_IDS):
        calibration = np.load(
            _profile_path(output_dir, "calibration", variant_id), mmap_mode="r", allow_pickle=False
        )
        diagonal = np.stack(
            [np.asarray(calibration[node, :, node]) for node in range(len(effects))]
        )
        cutoffs[variant_index] = np.partition(diagonal, config.calibration_rank - 1, axis=1)[
            :, config.calibration_rank - 1
        ]
        evaluation.append(
            np.load(
                _profile_path(output_dir, "evaluation", variant_id),
                mmap_mode="r",
                allow_pickle=False,
            )
        )
    np.save(output_dir / "cutoffs.npy", cutoffs, allow_pickle=False)

    shape = (
        len(VARIANT_IDS),
        len(config.evaluation_truths),
        config.evaluation_replicates,
        len(effects),
    )
    methods = {
        "candidate": open_memmap(
            output_dir / "membership_candidate.npy", mode="w+", dtype=bool, shape=shape
        ),
        "oracle": open_memmap(
            output_dir / "membership_oracle.npy", mode="w+", dtype=bool, shape=shape
        ),
        "c1": open_memmap(output_dir / "membership_c1.npy", mode="w+", dtype=bool, shape=shape),
        "chi_square_95": open_memmap(
            output_dir / "membership_chi_square_95.npy", mode="w+", dtype=bool, shape=shape
        ),
    }
    mle_indices = np.empty(shape[:-1], dtype=np.int16)
    identity = {
        "candidate_oracle_true_node": True,
        "null_truth_false_exclusion": True,
        "full_grid_maximizer_in_candidate_set": True,
        "finite_nonnegative_evaluation_scores": True,
    }
    construction_controls = {
        "point_estimation_uses_one_frozen_profile_for_all_support_methods": True,
        "prediction_uses_one_frozen_holdout_profile_for_all_support_methods": True,
        "membership_comparison_is_inclusive": True,
    }
    endpoint: dict[str, Any] = {}
    for variant_index, variant_id in enumerate(VARIANT_IDS):
        profiles = np.asarray(evaluation[variant_index])
        identity["finite_nonnegative_evaluation_scores"] &= bool(
            np.isfinite(profiles).all() and (profiles >= 0).all()
        )
        mle_indices[variant_index] = np.argmin(profiles, axis=-1)
        candidate = profiles <= cutoffs[variant_index][None, None, :]
        oracle = profiles <= cutoffs[variant_index, truth_indices][:, None, None]
        c1 = profiles <= cutoffs[variant_index, 0]
        chi = profiles <= CHI_SQUARE_95
        for name, values in (
            ("candidate", candidate),
            ("oracle", oracle),
            ("c1", c1),
            ("chi_square_95", chi),
        ):
            methods[name][variant_index] = values
        true_candidate = np.stack(
            [candidate[index, :, truth_index] for index, truth_index in enumerate(truth_indices)]
        )
        true_oracle = np.stack(
            [oracle[index, :, truth_index] for index, truth_index in enumerate(truth_indices)]
        )
        identity["candidate_oracle_true_node"] &= bool(np.array_equal(true_candidate, true_oracle))
        null_truth = int(np.flatnonzero(truth_indices == 0)[0])
        identity["null_truth_false_exclusion"] &= bool(
            np.array_equal(candidate[null_truth, :, 0], oracle[null_truth, :, 0])
        )
        identity["full_grid_maximizer_in_candidate_set"] &= bool(
            np.all(np.take_along_axis(candidate, mle_indices[variant_index, :, :, None], axis=-1))
        )
        endpoint[variant_id] = {
            str(truth): {
                name: _method_metrics(values[truth_number], profiles[truth_number], effects, truth)
                for name, values in (
                    ("candidate", candidate),
                    ("oracle", oracle),
                    ("c1", c1),
                    ("chi_square_95", chi),
                )
            }
            for truth_number, truth in enumerate(config.evaluation_truths)
        }
    for array in methods.values():
        array.flush()
    np.save(output_dir / "evaluation_mle_indices.npy", mle_indices, allow_pickle=False)

    _write_json(
        output_dir / "identity_controls.json",
        {
            "measured": identity,
            "construction": construction_controls,
        },
    )
    if not all(identity.values()):
        raise RuntimeError(f"required frozen-score identity failed: {identity}")

    opaque = np.load(output_dir / "evaluation_opaque_ids.npy", allow_pickle=False)
    sidecar = {
        str(opaque[truth_index, replicate]): float(truth)
        for truth_index, truth in enumerate(config.evaluation_truths)
        for replicate in range(config.evaluation_replicates)
    }
    _write_json(output_dir / "evaluation_truth_sidecar.json", sidecar)
    _write_json(output_dir / "endpoint_metrics.json", endpoint)
    return {
        "identity_controls": identity,
        "construction_controls": construction_controls,
        "endpoint_metrics": endpoint,
    }


def _timing_projection(
    config: CampaignConfig,
    integration_seconds: float,
    calibration_seconds: float,
    evaluation_seconds: float,
) -> dict[str, Any]:
    if config.mode != "timing":
        return {}
    calibration_scale = (CALIBRATION_REPLICATES * len(EFFECT_GRID)) / (
        config.calibration_replicates * len(config.effects)
    )
    evaluation_scale = (EVALUATION_REPLICATES * len(EVALUATION_TRUTHS)) / (
        config.evaluation_replicates * len(config.evaluation_truths)
    )
    scoring_projection = (
        calibration_seconds * calibration_scale + evaluation_seconds * evaluation_scale
    )
    conservative = integration_seconds + 1.25 * scoring_projection
    return {
        "integration_construction_seconds_measured": integration_seconds,
        "all_four_variants_scoring_seconds_projected": scoring_projection,
        "campaign_excluding_bootstrap_seconds_conservative": conservative,
        "bootstrap_2000_seconds": None,
        "bootstrap_note": (
            "Measured separately by known_nuisance_synthesis before a production go decision."
        ),
        "total_with_bootstrap_seconds": None,
        "within_24h_ceiling": None,
    }


def run_campaign(
    config: CampaignConfig,
    *,
    output_dir: Path,
    registration_path: Path,
    bank_cache_dir: Path | None = None,
    budget_receipt_path: Path | None = None,
    workers: int = 1,
    progress: Progress | None = print,
) -> CampaignResult:
    """Run smoke/timing or the explicitly registered resumable production campaign."""
    if not 1 <= workers <= 8:
        raise ValueError("workers must lie between 1 and 8")
    if _file_sha256(registration_path) != REGISTRATION_SHA256:
        raise ValueError("registration file differs from the reviewed Goal 049 contract")
    if config.mode != "smoke" and bank_cache_dir is None:
        raise ValueError("timing and production require the verified Goal 045 high-bank cache")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    source_hashes = _source_hashes(registration_path)
    budget_receipt = None
    if config.mode == "production":
        if budget_receipt_path is None:
            raise ValueError("production requires a timing and bootstrap budget receipt")
        budget_receipt = validate_production_budget(
            budget_receipt_path,
            config=config,
            source_hashes=source_hashes,
        )
    elif budget_receipt_path is not None:
        raise ValueError("a budget receipt may only be supplied in production mode")
    fixed = goal011.build_fixed_inputs()
    sites = tuple(sorted(fixed.design.sites, key=lambda site: site.site_id))
    site_ids = tuple(site.site_id for site in sites)
    bank, bank_provenance = load_verified_bank(bank_cache_dir or output_dir, config, site_ids)
    calibration = spawn_phase_seeds(
        config.calibration_root, "calibration", config.calibration_replicates
    )
    evaluation = spawn_phase_seeds(
        config.evaluation_root, "evaluation", config.evaluation_replicates
    )
    seed_checks = verify_seed_separation(config, calibration, evaluation, bank_provenance)
    if not all(seed_checks.values()):
        raise RuntimeError(f"seed separation failed: {seed_checks}")
    variants = build_scoring_variants(bank, config, site_ids)
    config_payload = json.loads(json.dumps(asdict(config)))
    contract = {
        "schema_version": 1,
        "workflow": "goal049-known-nuisance-calibration",
        "config": config_payload,
        "variant_ids": list(VARIANT_IDS),
        "variant_specs": [
            {"id": identifier, "bank_size": size, "pseudocount_alpha": alpha}
            for identifier, (size, alpha) in zip(VARIANT_IDS, VARIANT_SPECS, strict=True)
        ],
        "bank_provenance": bank_provenance,
        "source_and_registration_sha256": source_hashes,
        "production_budget_receipt": budget_receipt,
        "seed_checks": seed_checks,
        "paired_across_truths": True,
        "common_random_numbers": {
            "paired_across_all_calibration_truths_within_replicate": True,
            "paired_across_all_evaluation_truths_within_replicate": True,
            "generator": "arc2b_campaign.generate_paired_datasets",
            "replicate_stream_tuples_iid_by_phase": True,
        },
        "calibration_seed_sha256": _json_sha256([asdict(row) for row in calibration.records]),
        "evaluation_seed_sha256": _json_sha256([asdict(row) for row in evaluation.records]),
        "bootstrap_root": config.bootstrap_root,
        "analyst_signature": str(inspect.signature(score_observations)),
    }
    fingerprint = _json_sha256(contract)
    contract["run_fingerprint"] = fingerprint
    contract["created_utc"] = datetime.now(UTC).isoformat()
    contract_path = output_dir / "run_contract.json"
    if contract_path.exists():
        existing = json.loads(contract_path.read_text(encoding="utf-8"))
        if existing.get("run_fingerprint") != fingerprint:
            raise ValueError("output directory contains a different frozen run contract")
    else:
        _write_json(contract_path, contract)
    if progress is not None:
        progress(f"integration complete variants={len(VARIANT_IDS)}")
    calibration_seconds = _run_phase(
        phase="calibration",
        fixed=fixed,
        seeds=calibration,
        generating_effects=config.effects,
        config=config,
        variants=variants,
        output_dir=output_dir,
        workers=workers,
        fingerprint=fingerprint,
        progress=progress,
    )
    evaluation_seconds = _run_phase(
        phase="evaluation",
        fixed=fixed,
        seeds=evaluation,
        generating_effects=config.evaluation_truths,
        config=config,
        variants=variants,
        output_dir=output_dir,
        workers=workers,
        fingerprint=fingerprint,
        progress=progress,
    )
    score_hashes = _freeze_score_files(output_dir, config)
    evaluator = evaluate_frozen_scores(output_dir, config)
    elapsed = time.perf_counter() - started
    summary = {
        **contract,
        "completed_utc": datetime.now(UTC).isoformat(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "workers": workers,
        "runtimes_seconds": {
            "total": elapsed,
            "integration": variants.construction_seconds,
            "calibration_scoring": calibration_seconds,
            "evaluation_scoring": evaluation_seconds,
        },
        "timing_projection": _timing_projection(
            config,
            variants.construction_seconds["total"],
            calibration_seconds,
            evaluation_seconds,
        ),
        "score_file_sha256": score_hashes,
        "identity_controls": evaluator["identity_controls"],
        "construction_controls": evaluator["construction_controls"],
        "outcome": (
            "non_scientific_smoke"
            if config.mode == "smoke"
            else "timing_requires_separate_bootstrap_estimate"
            if config.mode == "timing"
            else "production_scores_complete"
        ),
    }
    _write_json(output_dir / "run_summary.json", summary)
    return CampaignResult(output_dir, config, summary)
