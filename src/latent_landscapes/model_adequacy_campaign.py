"""Goal 050 model-adequacy replay, detector, and crossed-null runner.

The runner consumes the immutable Goal 049 production output and its matching
arrival bank.  Original histories are regenerated from their registered seed
streams and checked against the saved training profiles before their
conditional held-out scores are used.  Fresh phases use only the registered
null roots.  No Goal 049 file is modified.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import socket
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import arc2c_likelihood as arc2c
from latent_landscapes import known_nuisance_calibration as legacy
from latent_landscapes.arc2c_likelihood import build_joint_integration
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.integration_weights import reweight_integration
from latent_landscapes.known_nuisance_calibration import EFFECT_GRID, EVALUATION_TRUTHS

RunMode = Literal["smoke", "timing", "production"]
Progress = Callable[[str], None]
FloatArray = NDArray[np.float64]

ORIGINAL_CALIBRATION_ROOT = 2026092001
ORIGINAL_EVALUATION_ROOT = 2026092002
FRESH_CALIBRATION_ROOT = 2026092004
FRESH_EVALUATION_ROOT = 2026092005
SYNTHESIS_ROOT = 2026092006
ARCHIVED_BANK_ROOT = 20260905
PRIMARY_VARIANT_ID = "high_k131072_alpha100"
CALIBRATION_REPLICATES = 999
EVALUATION_REPLICATES = 1000
CALIBRATION_RANK = 950
IDENTITY_TOLERANCE = 1e-10
DEFAULT_OUTPUT_DIR = Path("artifacts/goal050_model_adequacy")
DEFAULT_ORIGINAL_OUTPUT_DIR = Path("artifacts/goal049_execution/production/output")
DEFAULT_REGISTRATION_PATH = Path("docs/goals/050-model-adequacy/registration-2026-09-20.md")
REMOTE_ORIGINAL_OUTPUT_DIR = Path(
    "/data/codex/scratch/goal049-known-nuisance-20260920/production/output"
)


@dataclass(frozen=True, slots=True)
class CampaignConfig:
    mode: RunMode
    effects: tuple[float, ...]
    evaluation_truths: tuple[float, ...]
    original_calibration_replicates: int
    original_evaluation_replicates: int
    fresh_calibration_replicates: int
    fresh_evaluation_replicates: int
    low_bank_size: int = 65_536
    high_bank_size: int = 131_072
    original_calibration_root: int = ORIGINAL_CALIBRATION_ROOT
    original_evaluation_root: int = ORIGINAL_EVALUATION_ROOT
    fresh_calibration_root: int = FRESH_CALIBRATION_ROOT
    fresh_evaluation_root: int = FRESH_EVALUATION_ROOT
    bank_root: int = ARCHIVED_BANK_ROOT
    synthesis_root: int = SYNTHESIS_ROOT

    def __post_init__(self) -> None:
        effects = np.asarray(self.effects, dtype=np.float64)
        truths = np.asarray(self.evaluation_truths, dtype=np.float64)
        if effects.ndim != 1 or not len(effects) or not np.isfinite(effects).all():
            raise ValueError("effects must be finite and one-dimensional")
        if np.any(np.diff(effects) <= 0) or effects[0] != 1.0:
            raise ValueError("effects must be strictly increasing and start at 1")
        if truths.ndim != 1 or not len(truths) or not np.isfinite(truths).all():
            raise ValueError("evaluation truths must be finite and one-dimensional")
        if any(not np.any(np.isclose(effects, value, rtol=0, atol=1e-12)) for value in truths):
            raise ValueError("every evaluation truth must be on the effect grid")
        counts = (
            self.original_calibration_replicates,
            self.original_evaluation_replicates,
            self.fresh_calibration_replicates,
            self.fresh_evaluation_replicates,
        )
        if any(value <= 0 for value in counts):
            raise ValueError("all phase replicate counts must be positive")
        roots = (
            self.bank_root,
            self.original_calibration_root,
            self.original_evaluation_root,
            self.fresh_calibration_root,
            self.fresh_evaluation_root,
            self.synthesis_root,
        )
        if len(set(roots)) != len(roots):
            raise ValueError("registered roots must be distinct")
        if self.mode != "smoke":
            expected = (
                EFFECT_GRID,
                EVALUATION_TRUTHS,
                2 if self.mode == "timing" else CALIBRATION_REPLICATES,
                2 if self.mode == "timing" else EVALUATION_REPLICATES,
                2 if self.mode == "timing" else CALIBRATION_REPLICATES,
                2 if self.mode == "timing" else EVALUATION_REPLICATES,
            )
            actual = (
                self.effects,
                self.evaluation_truths,
                self.original_calibration_replicates,
                self.original_evaluation_replicates,
                self.fresh_calibration_replicates,
                self.fresh_evaluation_replicates,
            )
            if actual != expected or (self.low_bank_size, self.high_bank_size) != (65_536, 131_072):
                raise ValueError("timing and production require the registered full-grid contract")


def production_config(mode: RunMode = "production") -> CampaignConfig:
    if mode not in ("timing", "production"):
        raise ValueError("full configuration mode must be timing or production")
    return CampaignConfig(
        mode=mode,
        effects=EFFECT_GRID,
        evaluation_truths=EVALUATION_TRUTHS,
        original_calibration_replicates=2 if mode == "timing" else CALIBRATION_REPLICATES,
        original_evaluation_replicates=2 if mode == "timing" else EVALUATION_REPLICATES,
        fresh_calibration_replicates=2 if mode == "timing" else CALIBRATION_REPLICATES,
        fresh_evaluation_replicates=2 if mode == "timing" else EVALUATION_REPLICATES,
    )


def smoke_config(
    *, calibration_replicates: int = 2, evaluation_replicates: int = 2
) -> CampaignConfig:
    return CampaignConfig(
        mode="smoke",
        effects=(1.0, 3.0, 10.0),
        evaluation_truths=(1.0, 3.0, 10.0),
        original_calibration_replicates=calibration_replicates,
        original_evaluation_replicates=evaluation_replicates,
        fresh_calibration_replicates=calibration_replicates,
        fresh_evaluation_replicates=evaluation_replicates,
        low_bank_size=8,
        high_bank_size=16,
    )


@dataclass(frozen=True, slots=True)
class OriginalInputs:
    output_dir: Path
    manifest: dict[str, Any]
    file_hashes: dict[str, str]
    calibration_profiles: FloatArray
    evaluation_profiles: FloatArray
    evaluation_holdout_joint: FloatArray
    calibration_ids: NDArray[np.str_]
    evaluation_ids: NDArray[np.str_]


def _file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _array_sha256(array: NDArray[Any]) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _json_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_array(path: Path, shape: tuple[int, ...], dtype: np.dtype[Any]) -> NDArray[Any]:
    if not path.is_file():
        raise ValueError(f"missing required original artifact: {path}")
    array = np.load(path, allow_pickle=False)
    if array.shape != shape or array.dtype != dtype:
        raise ValueError(f"original artifact has wrong schema: {path}")
    if array.dtype.kind in "fc" and not np.isfinite(array).all():
        raise ValueError(f"original artifact contains non-finite values: {path}")
    return cast(NDArray[Any], array)


def load_original_inputs(
    output_dir: Path = DEFAULT_ORIGINAL_OUTPUT_DIR,
    *,
    config: CampaignConfig | None = None,
) -> OriginalInputs:
    """Validate and load the immutable Goal 049 primary artifacts."""
    _ = config or production_config("production")
    summary_path = output_dir / "run_summary.json"
    contract_path = output_dir / "run_contract.json"
    frozen_path = output_dir / "frozen_scores.json"
    if not all(path.is_file() for path in (summary_path, contract_path, frozen_path)):
        raise ValueError("original Goal 049 manifest/contract is incomplete")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    original_config = contract.get("config", {})
    if (
        contract.get("workflow") != "goal049-known-nuisance-calibration"
        or original_config.get("effects") != list(EFFECT_GRID)
        or original_config.get("evaluation_truths") != list(EVALUATION_TRUTHS)
        or original_config.get("calibration_replicates") != CALIBRATION_REPLICATES
        or original_config.get("evaluation_replicates") != EVALUATION_REPLICATES
        or original_config.get("high_bank_size") != 131_072
        or original_config.get("bank_root") != ARCHIVED_BANK_ROOT
        or summary.get("run_fingerprint") != contract.get("run_fingerprint")
        or summary.get("outcome") != "production_scores_complete"
        or set(summary.get("identity_controls", {}))
        != {
            "candidate_oracle_true_node",
            "finite_nonnegative_evaluation_scores",
            "full_grid_maximizer_in_candidate_set",
            "null_truth_false_exclusion",
        }
        or any(value is not True for value in summary.get("identity_controls", {}).values())
        or frozen.get("truth_joined") is not False
    ):
        raise ValueError("original Goal 049 input contract differs from the registered source")
    files = frozen.get("files", {})
    required = {
        f"calibration_profiles_{PRIMARY_VARIANT_ID}.npy": (181, 999, 181),
        f"evaluation_profiles_{PRIMARY_VARIANT_ID}.npy": (6, 1000, 181),
        f"evaluation_holdout_loglikelihood_{PRIMARY_VARIANT_ID}.npy": (6, 1000, 181),
        "calibration_opaque_ids.npy": (181, 999),
        "evaluation_opaque_ids.npy": (6, 1000),
    }
    file_hashes: dict[str, str] = {}
    for name, _shape in required.items():
        path = output_dir / name
        digest = _file_sha256(path)
        if files.get(name) != digest:
            raise ValueError(f"original artifact hash mismatch: {name}")
        file_hashes[name] = digest
    summary_hashes = summary.get("score_file_sha256", {})
    if any(summary_hashes.get(name) != digest for name, digest in file_hashes.items()):
        raise ValueError("original summary score hashes do not match frozen artifacts")
    # Load with strict shape/type checks.  Profiles and scores must be finite.
    calibration_profiles = cast(
        FloatArray,
        _load_array(
            output_dir / f"calibration_profiles_{PRIMARY_VARIANT_ID}.npy",
            (181, 999, 181),
            np.dtype("float64"),
        ),
    )
    evaluation_profiles = cast(
        FloatArray,
        _load_array(
            output_dir / f"evaluation_profiles_{PRIMARY_VARIANT_ID}.npy",
            (6, 1000, 181),
            np.dtype("float64"),
        ),
    )
    evaluation_holdout_joint = cast(
        FloatArray,
        _load_array(
            output_dir / f"evaluation_holdout_loglikelihood_{PRIMARY_VARIANT_ID}.npy",
            (6, 1000, 181),
            np.dtype("float64"),
        ),
    )
    calibration_ids = cast(
        NDArray[np.str_], np.load(output_dir / "calibration_opaque_ids.npy", allow_pickle=False)
    )
    evaluation_ids = cast(
        NDArray[np.str_], np.load(output_dir / "evaluation_opaque_ids.npy", allow_pickle=False)
    )
    if calibration_ids.dtype.kind != "U" or evaluation_ids.dtype.kind != "U":
        raise ValueError("original opaque IDs must be Unicode arrays")
    source = summary.get("source_and_registration_sha256")
    if not isinstance(source, dict) or not source:
        raise ValueError("original source/registration manifest is missing")
    manifest = {
        "run_contract": contract,
        "run_summary": summary,
        "frozen_scores": frozen,
        "source_and_registration_sha256": source,
        "file_hashes": file_hashes,
    }
    return OriginalInputs(
        output_dir,
        manifest,
        file_hashes,
        calibration_profiles,
        evaluation_profiles,
        evaluation_holdout_joint,
        calibration_ids,
        evaluation_ids,
    )


def spawn_phase_seeds(root: int, phase: str, count: int) -> tuple[arc2b.DatasetSeed, ...]:
    """Use Goal 049's four-stream spawning convention exactly."""
    if count <= 0 or phase not in {"calibration", "evaluation"}:
        raise ValueError("phase and count are invalid")
    return legacy.spawn_phase_seeds(root, phase, count).records


def _legacy_config(
    config: CampaignConfig, phase: str, root_override: int | None = None
) -> legacy.CampaignConfig:
    root = (
        root_override
        if root_override is not None
        else (
            config.original_calibration_root
            if phase == "calibration" and config.mode != "smoke"
            else config.original_evaluation_root
            if phase == "evaluation" and config.mode != "smoke"
            else config.fresh_calibration_root
            if phase == "calibration"
            else config.fresh_evaluation_root
        )
    )
    return legacy.CampaignConfig(
        mode=config.mode,
        effects=config.effects,
        evaluation_truths=config.evaluation_truths,
        calibration_replicates=config.original_calibration_replicates,
        evaluation_replicates=config.original_evaluation_replicates,
        calibration_rank=min(CALIBRATION_RANK, config.original_calibration_replicates),
        low_bank_size=config.low_bank_size,
        high_bank_size=config.high_bank_size,
        calibration_root=root if phase == "calibration" else root - 1,
        evaluation_root=root + 1 if phase == "calibration" else root,
        bootstrap_root=SYNTHESIS_ROOT,
        bank_root=config.bank_root if config.mode != "smoke" else legacy.SMOKE_BANK_ROOT,
    )


def _build_primary_integration(
    bank: NDArray[np.float64], config: CampaignConfig, site_ids: tuple[str, ...]
) -> arc2c.BridgeIntegration:
    base = build_joint_integration(
        np.asarray(bank[: config.high_bank_size]), site_ids, (1.0,), config.effects
    )
    return reweight_integration(
        base,
        config.high_bank_size,
        from_pseudocount=0.5,
        to_pseudocount=1.0,
        background_hazard=legacy.BACKGROUND_HAZARD,
    )


def _seed_controls(config: CampaignConfig, bank_provenance: dict[str, Any]) -> dict[str, bool]:
    roots = (
        config.bank_root,
        config.original_calibration_root,
        config.original_evaluation_root,
        config.fresh_calibration_root,
        config.fresh_evaluation_root,
        config.synthesis_root,
    )
    counts = (
        (
            config.original_calibration_replicates,
            config.original_evaluation_replicates,
            config.fresh_calibration_replicates,
            config.fresh_evaluation_replicates,
        )
        if config.mode == "smoke"
        else (999, 1000, 999, 1000)
    )
    streams = {
        root: {
            value
            for seed in spawn_phase_seeds(
                root,
                "calibration"
                if root in (config.original_calibration_root, config.fresh_calibration_root)
                else "evaluation",
                count,
            )
            for value in (
                seed.process_seed,
                seed.predator_detection_seed,
                seed.prey_seed,
                seed.prey_detection_seed,
            )
        }
        for root, count in zip(roots[1:5], counts, strict=True)
    }
    disjoint = all(
        streams[first].isdisjoint(streams[second])
        for index, first in enumerate(streams)
        for second in list(streams)[index + 1 :]
    )
    bank_disjoint = True
    if config.mode != "smoke":
        bank_seeds = set(legacy._expected_archived_bank_seeds(config.high_bank_size))
        bank_disjoint = all(bank_seeds.isdisjoint(values) for values in streams.values())
    controls = {
        "root_identifiers_distinct": len(set(roots)) == len(roots),
        "phase_streams_pairwise_disjoint": disjoint,
        "within_phase_streams_unique": all(
            len(streams[root]) == 4 * count for root, count in zip(roots[1:5], counts, strict=True)
        ),
        "bank_streams_disjoint": bank_disjoint,
        "bank_provenance_present": bool(bank_provenance.get("bank_checksum")),
        "synthesis_root_reserved": config.synthesis_root not in roots[:5],
    }
    if not all(controls.values()):
        raise RuntimeError(f"registered seed separation failed: {controls}")
    return controls


def _load_bank(
    config: CampaignConfig,
    bank_cache_dir: Path | None,
    site_ids: tuple[str, ...],
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    if config.mode == "smoke":
        bank, provenance = legacy.load_verified_bank(
            Path("."), legacy.smoke_config(high_bank_size=config.high_bank_size), site_ids
        )
        return bank, provenance
    if bank_cache_dir is None:
        raise ValueError("timing and production require the verified primary bank cache")
    legacy_config = legacy.production_config("timing")
    bank, provenance = legacy.load_verified_bank(bank_cache_dir, legacy_config, site_ids)
    return bank, provenance


def _score_dataset(
    dataset: legacy.AnalystDataset, integration: arc2c.BridgeIntegration
) -> tuple[float, float, int, FloatArray, FloatArray]:
    histories = cast(Any, dataset.histories)
    training, holdout_joint, holdout_predator = arc2c.evaluate_dataset(histories, integration)
    ordered, indices = arc2c._prepare_histories(histories, integration)
    train_mask = np.asarray([row.split == "training" for row in ordered])
    predator_categories = arc2b._predator_category_probabilities(
        ordered, legacy.DETECTION_PROBABILITY
    )
    predator_marginal = np.einsum(
        "sc,sc->s", integration.category_mass[0, indices], predator_categories
    )
    train_predator = float(np.log(predator_marginal[train_mask]).sum())
    if training.shape != (1, len(integration.effects)):
        raise RuntimeError("primary scoring returned an invalid training profile")
    profile = np.asarray(2.0 * (float(training[0].max()) - training[0]), dtype=np.float64)
    if not np.isfinite(profile).all() or profile.min() != 0.0:
        raise RuntimeError("primary training LR profile is non-finite or not normalized")
    mle_index = int(np.argmin(profile))
    prey = float(holdout_joint[0, mle_index] - holdout_predator[0])
    if not math.isfinite(prey) or not math.isfinite(train_predator):
        raise RuntimeError("conditional or predator score is non-finite")
    return prey, train_predator, mle_index, profile, np.asarray(holdout_joint[0], dtype=np.float64)


def _generate_and_score(
    fixed: goal007.FixedInputs,
    seed: arc2b.DatasetSeed,
    effects: tuple[float, ...],
    config: CampaignConfig,
    integration: arc2c.BridgeIntegration,
    root: int,
) -> tuple[FloatArray, FloatArray, NDArray[np.int64], FloatArray, FloatArray, NDArray[np.str_]]:
    legacy_config = _legacy_config(config, seed.phase, root)
    observations = legacy.generate_observations(fixed, seed, effects, legacy_config)
    prey = np.empty(len(observations), dtype=np.float64)
    predator = np.empty_like(prey)
    mle = np.empty(len(observations), dtype=np.int64)
    profiles = np.empty((len(observations), len(config.effects)), dtype=np.float64)
    joint = np.empty_like(profiles)
    opaque_ids = np.empty(len(observations), dtype="<U32")
    for index, dataset in enumerate(observations):
        prey[index], predator[index], mle[index], profiles[index], joint[index] = _score_dataset(
            dataset, integration
        )
        opaque_ids[index] = dataset.opaque_id
    return prey, predator, mle, profiles, joint, opaque_ids


def _source_hashes(registration_path: Path) -> dict[str, str]:
    repository = Path(__file__).resolve().parents[2]
    paths = (
        *sorted((repository / "src").rglob("*.py")),
        repository / "scripts" / "run_model_adequacy.py",
        repository / "scripts" / "synthesize_model_adequacy.py",
        repository / "pyproject.toml",
        repository / "uv.lock",
        registration_path.resolve(),
    )
    return {
        str(path.resolve().relative_to(repository)): _file_sha256(path)
        for path in paths
        if path.is_file()
    }


def _phase_shard_path(output_dir: Path, phase: str, index: int) -> Path:
    return output_dir / "shards" / phase / f"{index:04d}.npz"


def _shard_fingerprint(payload: dict[str, Any]) -> str:
    return _json_sha256(payload)


def _shard_data_digest(values: dict[str, NDArray[Any]]) -> str:
    digest = hashlib.sha256()
    for name in (
        "prey_score",
        "predator_score",
        "mle_index",
        "profiles",
        "holdout_joint",
        "opaque_id",
    ):
        if name in values:
            digest.update(name.encode())
            digest.update(np.ascontiguousarray(values[name]).tobytes())
    return digest.hexdigest()


def _phase(
    *,
    phase: str,
    seed_root: int,
    count: int,
    generating_effects: tuple[float, ...],
    config: CampaignConfig,
    fixed: goal007.FixedInputs,
    integration: arc2c.BridgeIntegration,
    output_dir: Path,
    workers: int,
    source_fingerprint: str,
    expected_profiles: FloatArray | None = None,
    expected_joint: FloatArray | None = None,
    expected_ids: NDArray[np.str_] | None = None,
    progress: Progress | None = None,
) -> tuple[
    FloatArray,
    FloatArray,
    NDArray[np.int64],
    FloatArray,
    FloatArray,
    NDArray[np.str_],
    dict[str, Any],
]:
    seeds = spawn_phase_seeds(
        seed_root, "calibration" if "calibration" in phase else "evaluation", count
    )
    n_truth = len(generating_effects)
    prey = np.empty((n_truth, count), dtype=np.float64)
    predator = np.empty_like(prey)
    mle = np.empty((n_truth, count), dtype=np.int64)
    profiles = np.empty((n_truth, count, len(config.effects)), dtype=np.float64)
    joint = np.empty_like(profiles)
    opaque_ids = np.empty((n_truth, count), dtype="<U32")
    phase_dir = output_dir / "shards" / phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    pending: list[arc2b.DatasetSeed] = []
    for seed in seeds:
        path = _phase_shard_path(output_dir, phase, seed.index)
        if path.exists():
            with np.load(path, allow_pickle=False) as shard:
                if (
                    shard.get("source_fingerprint") is None
                    or str(shard["source_fingerprint"]) != source_fingerprint
                ):
                    raise ValueError(
                        f"existing {phase} shard has a different source contract: {path}"
                    )
                if str(shard.get("seed_fingerprint", "")) != legacy._seed_fingerprint(seed):
                    raise ValueError(
                        f"existing {phase} shard has a different registered seed: {path}"
                    )
                for key, shape2 in (
                    ("prey_score", (n_truth,)),
                    ("predator_score", (n_truth,)),
                    ("mle_index", (n_truth,)),
                ):
                    if key not in shard or shard[key].shape != shape2:
                        raise ValueError(f"existing {phase} shard has wrong schema: {path}")
                prey[:, seed.index] = shard["prey_score"]
                predator[:, seed.index] = shard["predator_score"]
                mle[:, seed.index] = shard["mle_index"]
                for key, shape in (
                    ("profiles", (n_truth, len(config.effects))),
                    ("holdout_joint", (n_truth, len(config.effects))),
                    ("opaque_id", (n_truth,)),
                ):
                    if key not in shard or shard[key].shape != shape:
                        raise ValueError(f"existing {phase} shard has wrong {key} schema: {path}")
                profiles[:, seed.index] = shard["profiles"]
                joint[:, seed.index] = shard["holdout_joint"]
                opaque_ids[:, seed.index] = shard["opaque_id"]
                shard_values = {
                    name: shard[name]
                    for name in (
                        "prey_score",
                        "predator_score",
                        "mle_index",
                        "profiles",
                        "holdout_joint",
                        "opaque_id",
                    )
                }
                if str(shard.get("data_digest", "")) != _shard_data_digest(shard_values):
                    raise ValueError(f"existing {phase} shard has a corrupt payload: {path}")
                continue
        pending.append(seed)

    def run(
        seed: arc2b.DatasetSeed,
    ) -> tuple[
        arc2b.DatasetSeed,
        FloatArray,
        FloatArray,
        NDArray[np.int64],
        FloatArray,
        FloatArray,
        NDArray[np.str_],
    ]:
        values = _generate_and_score(
            fixed, seed, generating_effects, config, integration, seed_root
        )
        return seed, *values

    def store(
        result: tuple[
            arc2b.DatasetSeed,
            FloatArray,
            FloatArray,
            NDArray[np.int64],
            FloatArray,
            FloatArray,
            NDArray[np.str_],
        ],
    ) -> None:
        seed, row_prey, row_pred, row_mle, row_profiles, row_joint, row_ids = result
        path = _phase_shard_path(output_dir, phase, seed.index)
        if path.exists():
            raise ValueError(f"refusing to overwrite an existing completed shard: {path}")
        payload: dict[str, Any] = {
            "prey_score": row_prey,
            "predator_score": row_pred,
            "mle_index": row_mle,
            "profiles": row_profiles,
            "holdout_joint": row_joint,
            "opaque_id": row_ids,
            "source_fingerprint": np.asarray(source_fingerprint),
            "seed_fingerprint": np.asarray(legacy._seed_fingerprint(seed)),
        }
        payload["data_digest"] = np.asarray(
            _shard_data_digest(
                {
                    "prey_score": row_prey,
                    "predator_score": row_pred,
                    "mle_index": row_mle,
                    "profiles": row_profiles,
                    "holdout_joint": row_joint,
                    "opaque_id": row_ids,
                }
            )
        )
        np.savez_compressed(path, **payload)
        prey[:, seed.index] = row_prey
        predator[:, seed.index] = row_pred
        mle[:, seed.index] = row_mle
        profiles[:, seed.index] = row_profiles
        joint[:, seed.index] = row_joint
        opaque_ids[:, seed.index] = row_ids

    started = time.perf_counter()
    if workers == 1:
        for result in map(run, pending):
            store(result)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for result in executor.map(run, pending):
                store(result)
    if not np.isfinite(prey).all() or not np.isfinite(predator).all() or not np.isfinite(mle).all():
        raise RuntimeError(f"{phase} produced non-finite outputs")
    replay_maxdiff = 0.0
    replay_identity = True
    if expected_profiles is not None:
        if expected_profiles.shape != (n_truth, count, len(config.effects)):
            raise ValueError(f"{phase} expected profile schema differs")
        replay_maxdiff = float(np.max(np.abs(profiles - expected_profiles)))
    if expected_joint is not None and expected_joint.shape != (n_truth, count, len(config.effects)):
        # expected_joint is checked by the caller, while this phase hook carries timing metadata.
        raise ValueError(f"{phase} expected holdout schema differs")
    return (
        prey,
        predator,
        mle,
        profiles,
        joint,
        opaque_ids,
        {
            "seconds": time.perf_counter() - started,
            "replicates": count,
            "truths": list(generating_effects),
            "replay_max_abs_profile_diff": replay_maxdiff,
            "replay_identity": replay_identity,
        },
    )


def _write_phase_npz(
    output_dir: Path,
    phase: str,
    *,
    prey: FloatArray,
    predator: FloatArray,
    mle: NDArray[np.int64],
    profiles: FloatArray | None,
    source_fingerprint: str,
) -> str:
    path = output_dir / f"{phase}.npz"
    payload: dict[str, Any] = {"prey_score": prey, "predator_score": predator, "mle_index": mle}
    if profiles is not None:
        payload["profiles"] = profiles
    if path.exists():
        with np.load(path, allow_pickle=False) as existing:
            if (
                existing.get("source_fingerprint") is None
                or str(existing["source_fingerprint"]) != source_fingerprint
            ):
                raise ValueError(f"existing {phase}.npz belongs to a different source contract")
            for key, value in payload.items():
                if (
                    key not in existing
                    or existing[key].shape != value.shape
                    or not np.array_equal(existing[key], value)
                ):
                    raise ValueError(f"existing {phase}.npz differs from the completed phase")
        return _file_sha256(path)
    payload["source_fingerprint"] = np.asarray(source_fingerprint)
    np.savez_compressed(path, **payload)
    return _file_sha256(path)


def _validate_original_replay(
    phase: str,
    replay_profiles: FloatArray,
    replay_joint: FloatArray,
    replay_ids: NDArray[np.str_],
    original: OriginalInputs,
    *,
    expected_profiles: FloatArray | None = None,
    expected_joint: FloatArray | None = None,
    expected_ids: NDArray[np.str_] | None = None,
) -> dict[str, Any]:
    expected_profiles = (
        expected_profiles
        if expected_profiles is not None
        else original.calibration_profiles
        if phase == "calibration"
        else original.evaluation_profiles
    )
    expected_joint = (
        expected_joint
        if expected_joint is not None
        else None
        if phase == "calibration"
        else original.evaluation_holdout_joint
    )
    profile_diff = float(np.max(np.abs(replay_profiles - expected_profiles)))
    fitted_equal = np.array_equal(
        np.argmin(replay_profiles, axis=-1), np.argmin(expected_profiles, axis=-1)
    )
    joint_diff = (
        0.0 if expected_joint is None else float(np.max(np.abs(replay_joint - expected_joint)))
    )
    expected_ids = (
        expected_ids
        if expected_ids is not None
        else original.calibration_ids
        if phase == "calibration"
        else original.evaluation_ids
    )
    ids_equal = np.array_equal(replay_ids, expected_ids)
    controls = {
        "profile_finite": bool(np.isfinite(replay_profiles).all()),
        "profile_max_abs_diff_le_1e-10": profile_diff <= IDENTITY_TOLERANCE,
        "fitted_index_identical": bool(fitted_equal),
        "evaluation_holdout_joint_max_abs_diff_le_1e-10": joint_diff <= IDENTITY_TOLERANCE,
        "opaque_ids_identical": bool(ids_equal),
    }
    if not all(controls.values()):
        raise RuntimeError(f"{phase} original replay identity failed: {controls}")
    return {
        "max_abs_profile_diff": profile_diff,
        "max_abs_evaluation_holdout_joint_diff": joint_diff,
        "controls": controls,
    }


def validate_production_budget(
    budget_receipt_path: Path,
    *,
    config: CampaignConfig,
    source_hashes: dict[str, str],
    original_manifest_hash: str,
) -> dict[str, Any]:
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
    prior = float(receipt.get("prior_computation_allowance_seconds", math.nan))
    timing_seconds = float(receipt.get("timing_seconds_measured", math.nan))
    projected = float(receipt.get("total_projected_seconds", math.nan))
    production_projected = float(receipt.get("production_workload_seconds", math.nan))
    reserve = float(receipt.get("synthesis_seconds_reserved", math.nan))
    remaining = float(receipt.get("remaining_budget_seconds", math.nan))
    timeout = float(receipt.get("production_timeout_seconds", math.nan))
    expected_production = float(
        projection.get("production_workload_seconds_conservative", math.nan)
    )
    measured_total = float(timing.get("runtime_seconds", {}).get("total", math.nan))
    if (
        timing.get("source_and_registration_sha256") != source_hashes
        or timing.get("original_manifest_sha256") != original_manifest_hash
        or timing.get("outcome") != "timing_complete"
        or not timing.get("replay_controls", {}).get("calibration", {}).get("controls")
        or not timing.get("replay_controls", {}).get("evaluation", {}).get("controls")
        or not all(
            bool(control)
            for phase in ("calibration", "evaluation")
            for control in timing.get("replay_controls", {})
            .get(phase, {})
            .get("controls", {})
            .values()
        )
        or timing.get("config") != json.loads(json.dumps(asdict(production_config("timing"))))
        or float(projection.get("scoring_projection_factor", 0.0)) < 1.5
        or not math.isfinite(prior)
        or prior != 1_800.0
        or not math.isfinite(timing_seconds)
        or not math.isfinite(measured_total)
        or timing_seconds < measured_total
        or not math.isfinite(projected)
        or not math.isfinite(production_projected)
        or not math.isfinite(expected_production)
        or abs(production_projected - expected_production) > 1e-9 * max(1.0, expected_production)
        or not math.isfinite(reserve)
        or not math.isfinite(remaining)
        or not math.isfinite(timeout)
        or projected < production_projected + reserve
        or production_projected < 0
        or reserve < 3_600
        or remaining <= 0
        or projected != prior + timing_seconds + production_projected + reserve
        or projected > 43_200
        or remaining != 43_200.0 - prior - timing_seconds
        or production_projected + reserve > remaining
        or timeout <= production_projected
        or timeout > remaining - reserve - 30.0
        or receipt.get("within_12h") is not True
    ):
        raise ValueError(
            "timing/source/input/registration evidence does not support the 12-hour ceiling"
        )
    return receipt


def run_campaign(
    config: CampaignConfig,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    original_output_dir: Path = DEFAULT_ORIGINAL_OUTPUT_DIR,
    bank_cache_dir: Path | None = None,
    registration_path: Path = DEFAULT_REGISTRATION_PATH,
    budget_receipt_path: Path | None = None,
    workers: int = 1,
    progress: Progress | None = print,
) -> dict[str, Any]:
    run_started = time.perf_counter()
    if not 1 <= workers <= 8:
        raise ValueError("workers must lie between 1 and 8")
    if not registration_path.is_file():
        raise ValueError(f"registration file is missing: {registration_path}")
    source_hashes = _source_hashes(registration_path)
    original = (
        load_original_inputs(original_output_dir, config=config) if config.mode != "smoke" else None
    )
    original_manifest_hash = _json_sha256(original.manifest) if original else "smoke"
    budget = None
    if config.mode == "production":
        if budget_receipt_path is None:
            raise ValueError("production requires a measured budget receipt")
        budget = validate_production_budget(
            budget_receipt_path,
            config=config,
            source_hashes=source_hashes,
            original_manifest_hash=original_manifest_hash,
        )
    elif budget_receipt_path is not None:
        raise ValueError("a budget receipt may only be supplied in production mode")
    output_dir.mkdir(parents=True, exist_ok=True)
    fixed = goal011.build_fixed_inputs()
    site_ids = tuple(
        site.site_id for site in sorted(fixed.design.sites, key=lambda site: site.site_id)
    )
    bank, bank_provenance = _load_bank(config, bank_cache_dir, site_ids)
    seed_controls = _seed_controls(config, bank_provenance)
    integration_started = time.perf_counter()
    integration = _build_primary_integration(bank, config, site_ids)
    integration_seconds = time.perf_counter() - integration_started
    contract = {
        "schema_version": 1,
        "workflow": "goal050-model-adequacy",
        "config": asdict(config),
        "phase_roots": {
            "calibration": config.original_calibration_root,
            "evaluation": config.original_evaluation_root,
            "new_calibration": config.fresh_calibration_root,
            "new_evaluation": config.fresh_evaluation_root,
        },
        "primary_variant": PRIMARY_VARIANT_ID,
        "bank_provenance": bank_provenance,
        "seed_controls": seed_controls,
        "source_and_registration_sha256": source_hashes,
        "original_manifest_sha256": original_manifest_hash,
        "pairing": {"truths_within_replicate": True, "seed_spawning": "goal049-four-stream"},
    }
    fingerprint = _json_sha256(contract)
    contract["run_fingerprint"] = fingerprint
    contract_path = output_dir / "run_contract.json"
    if contract_path.exists():
        existing = json.loads(contract_path.read_text(encoding="utf-8"))
        if existing.get("run_fingerprint") != fingerprint:
            raise ValueError("output directory contains a different frozen run contract")
    else:
        _write_json(contract_path, contract)

    phase_specs = (
        (
            "calibration",
            config.original_calibration_root,
            config.original_calibration_replicates,
            config.effects,
            False,
        ),
        (
            "evaluation",
            config.original_evaluation_root,
            config.original_evaluation_replicates,
            config.evaluation_truths,
            False,
        ),
        (
            "new_calibration",
            config.fresh_calibration_root,
            config.fresh_calibration_replicates,
            (1.0,),
            True,
        ),
        (
            "new_evaluation",
            config.fresh_evaluation_root,
            config.fresh_evaluation_replicates,
            (1.0,),
            True,
        ),
    )
    timings: dict[str, Any] = {}
    replay_controls: dict[str, Any] = {}
    output_hashes: dict[str, Any] = {}
    for phase, root, count, truths, fresh in phase_specs:
        # The first two timing blocks use exactly the prefix of registered streams.
        expected_profiles = None
        expected_joint = None
        if original is not None and not fresh:
            expected_profiles = (
                original.calibration_profiles
                if phase == "calibration"
                else original.evaluation_profiles
            )
            expected_joint = None if phase == "calibration" else original.evaluation_holdout_joint
        expected_profile_slice = (
            expected_profiles[: len(truths), :count] if expected_profiles is not None else None
        )
        started = time.perf_counter()
        prey, predator, mle, profiles, replay_joint, replay_ids, phase_meta = _phase(
            phase=phase,
            seed_root=root,
            count=count,
            generating_effects=truths,
            config=config,
            fixed=fixed,
            integration=integration,
            output_dir=output_dir,
            workers=workers,
            source_fingerprint=fingerprint,
            expected_profiles=expected_profile_slice,
            expected_joint=expected_joint[: len(truths), :count]
            if expected_joint is not None
            else None,
            progress=progress,
        )
        if original is not None and not fresh:
            replay_controls[phase] = _validate_original_replay(
                phase,
                profiles,
                replay_joint,
                replay_ids,
                original,
                expected_profiles=expected_profile_slice,
                expected_joint=expected_joint[: len(truths), :count]
                if expected_joint is not None
                else None,
                expected_ids=(
                    original.calibration_ids if phase == "calibration" else original.evaluation_ids
                )[: len(truths), :count],
            )
        hashes = _write_phase_npz(
            output_dir,
            phase,
            prey=prey,
            predator=predator,
            mle=mle,
            profiles=profiles if fresh else None,
            source_fingerprint=fingerprint,
        )
        timings[phase] = {**phase_meta, "wall_seconds": time.perf_counter() - started}
        output_hashes[f"{phase}.npz"] = hashes
        if progress is not None:
            progress(f"{phase} complete: {count} replicate blocks")
    measured_phase_seconds = sum(float(row["wall_seconds"]) for row in timings.values())
    if config.mode == "timing":
        production_counts = {
            "calibration": CALIBRATION_REPLICATES,
            "evaluation": EVALUATION_REPLICATES,
            "new_calibration": CALIBRATION_REPLICATES,
            "new_evaluation": EVALUATION_REPLICATES,
        }
        phase_scales = {
            phase: production_counts[phase] / float(timings[phase]["replicates"])
            for phase in production_counts
        }
    else:
        phase_scales = {phase: 1.0 for phase in timings}
    projected_phase_seconds = sum(
        float(timings[phase]["wall_seconds"]) * phase_scales[phase] for phase in timings
    )
    measured_overhead_seconds = max(
        0.0,
        (time.perf_counter() - run_started) - integration_seconds - measured_phase_seconds,
    )
    projection = {
        "scoring_projection_factor": 1.5,
        "measured_phase_scoring_seconds": measured_phase_seconds,
        "measured_integration_seconds": integration_seconds,
        "measured_fixed_validation_hash_seconds": measured_overhead_seconds,
        "phase_scales_to_production": phase_scales,
        "production_phase_scoring_seconds": projected_phase_seconds,
        "production_workload_seconds_conservative": integration_seconds
        + 1.5 * projected_phase_seconds
        + measured_overhead_seconds,
    }
    summary = {
        **contract,
        "original_manifest": original.manifest if original is not None else None,
        "original_manifest_sha256": original_manifest_hash,
        "phase_timing": timings,
        "runtime_seconds": {
            "total": time.perf_counter() - run_started,
            "integration": integration_seconds,
        },
        "replay_controls": replay_controls,
        "output_hashes": output_hashes,
        "timing_projection": projection,
        "budget_receipt": budget,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "completed_utc": datetime.now(UTC).isoformat(),
        "outcome": "non_scientific_smoke"
        if config.mode == "smoke"
        else "timing_complete"
        if config.mode == "timing"
        else "production_complete",
    }
    _write_json(output_dir / "run_summary.json", summary)
    return summary
