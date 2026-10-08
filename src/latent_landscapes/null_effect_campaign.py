"""Bounded runner and score reduction for Goal 054.

The runner deliberately keeps the observation boundary array based.  A worker
loads one committed observation panel, constructs at most ``BATCH_SIZE``
``AnalystHistory`` records at a time, and writes one authenticated score row
for each fitted beta.  The numerical likelihood is the unchanged
``arc2c_likelihood.evaluate_dataset`` implementation; this module only binds
the frozen integrations, panels, receipts, and the registered reductions.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import time
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import arc2c_likelihood as joint
from latent_landscapes import known_nuisance_calibration as legacy
from latent_landscapes import misspecification_generator as prior_generator
from latent_landscapes import model_adequacy_campaign as adequacy
from latent_landscapes import null_effect_generator as generator
from latent_landscapes import prospective_background_campaign as old_campaign
from latent_landscapes import prospective_background_generator as old_generator
from latent_landscapes.goal011 import benchmark

EFFECTS = np.linspace(1.0, 10.0, 181, dtype=np.float64)
BETAS = np.asarray(generator.BETAS, dtype=np.float64)
BETA_ZERO_INDEX = int(np.flatnonzero(BETAS == 0.0)[0])
H_ONE_INDEX = 0
REFERENCE_BLOCKS = 999
EVALUATION_BLOCKS = 1_000
TIMING_REFERENCE_BLOCKS = 4
TIMING_EVALUATION_BLOCKS = 8
BATCH_SIZE = 64
TAIL_TOLERANCE = 1e-12
OLD_CORE = "b7a87caa216ea9c229110e225081dfe007cc56d1a0eea100d5756136da6d5b63"
OLD_CONTRACT_SHA256 = "3575e2f64d62aea0100da44fec7ca61df78f304d69be5c18ad43b1dfc3037980"
OLD_PRODUCTION_SUMMARY_SHA256 = "da229bf9cd4663f23c86452b99ffeefaff2d0ba88320f26ab7202bb2df50fcb9"
REFERENCE_REPLICATES = REFERENCE_BLOCKS
EVALUATION_REPLICATES = EVALUATION_BLOCKS
TIMING_REFERENCE_REPLICATES = TIMING_REFERENCE_BLOCKS
TIMING_EVALUATION_REPLICATES = TIMING_EVALUATION_BLOCKS


def sha256(path: Path) -> str:
    """Return the SHA256 digest of a file without loading it into memory."""

    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_json(path: Path, value: Any) -> None:
    """Atomically write a canonical JSON receipt and fsync its directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    _fsync_directory(path.parent)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
    ).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def worker_identity() -> dict[str, str]:
    return {
        "host": platform.node(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "numpy": np.__version__,
    }


def source_hashes(repository: Path) -> dict[str, str]:
    """Hash the complete new scientific source and its execution bindings."""

    paths = [
        *sorted((repository / "src").rglob("*.py")),
        *sorted((repository / "tests").glob("test_null_effect_*.py")),
        repository / "scripts/run_null_effect.py",
        repository / "scripts/synthesize_null_effect.py",
        repository / "docs/goals/054-null-effect-calibration/registration-2026-09-29.md",
        repository / "pyproject.toml",
        repository / "uv.lock",
    ]
    return {str(path.relative_to(repository)): sha256(path) for path in paths}


def read_committed(
    path: Path, identity: str
) -> tuple[dict[str, NDArray[Any]], dict[str, Any]] | None:
    """Read an authenticated NPZ/receipt pair, or return ``None`` if absent."""

    receipt = path.with_suffix(".json")
    if path.exists() != receipt.exists():
        raise ValueError(f"partial committed output must be diagnosed: {path}")
    if not path.exists():
        return None
    record = json.loads(receipt.read_text(encoding="utf-8"))
    if record.get("identity") != identity or record.get("sha256") != sha256(path):
        raise ValueError(f"cached identity or checksum changed: {path}")
    with np.load(path, allow_pickle=False) as loaded:
        return {name: loaded[name] for name in loaded.files}, record


def commit_npz(path: Path, values: Mapping[str, NDArray[Any]], record: dict[str, Any]) -> None:
    """Commit an NPZ and its receipt atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    started = time.perf_counter()
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **cast(Any, values))
        handle.flush()
        os.fsync(handle.fileno())
    record["sha256"] = sha256(temporary)
    temporary.replace(path)
    _fsync_directory(path.parent)
    record["serialization_seconds"] = time.perf_counter() - started
    write_json(path.with_suffix(".json"), record)


def reduce_rows(
    rows: Iterable[tuple[int, Mapping[str, NDArray[Any]]]],
    *,
    reference_blocks: int,
    evaluation_blocks: int,
) -> dict[str, NDArray[Any]]:
    """Reduce each complete coefficient row without mixing or retaining surfaces."""
    r, n = reference_blocks, evaluation_blocks
    if r <= 0 or n <= 0:
        raise ValueError("panel block counts must be positive")
    nr, ne = r * 81, n * 8
    count = nr + ne
    best = np.full(count, -np.inf)
    null = np.full(count, -np.inf)
    h_index = np.zeros(count, dtype=np.int64)
    beta_index = np.zeros(count, dtype=np.int64)
    null_beta = np.zeros(count, dtype=np.int64)
    held_best = np.zeros(count)
    held_null = np.zeros(count)
    true_null = np.full(nr, np.nan)
    eval_null_profile = np.empty((ne, 81))
    constant_t = np.empty(count)
    constant_h = np.zeros(count, dtype=np.int64)
    held_constant = np.empty(count)
    held_constant_null = np.empty(count)
    expected_predator = None
    seen: list[int] = []
    positions = np.arange(count)
    for index, row in rows:
        if index != len(seen) or index >= 81:
            raise ValueError("incomplete, duplicate or unordered beta rows")
        _validate_row_values(row, count)
        train = row["latent_training"]
        held = row["latent_holdout_joint"]
        predator = row["latent_holdout_predator"]
        if expected_predator is None:
            expected_predator = predator.copy()
        elif not np.array_equal(expected_predator, predator):
            raise ValueError("predator marginal changed across beta")
        k = np.argmax(train, axis=1)
        row_best = train[positions, k]
        better = row_best > best
        best[better] = row_best[better]
        h_index[better] = k[better]
        beta_index[better] = index
        held_best[better] = held[positions[better], k[better]]
        better_null = train[:, 0] > null
        null[better_null] = train[better_null, 0]
        null_beta[better_null] = index
        held_null[better_null] = held[better_null, 0]
        true_positions = np.arange(index, nr, 81)
        true_null[true_positions] = train[true_positions, 0]
        eval_null_profile[:, index] = train[nr:, 0]
        if index == BETA_ZERO_INDEX:
            constant_t[:] = 2 * (row_best - train[:, 0])
            constant_h[:] = k
            held_constant[:] = held[positions, k]
            held_constant_null[:] = held[:, 0]
        seen.append(index)
    if seen != list(range(81)) or not np.isfinite(true_null).all():
        raise ValueError("incomplete beta-row coverage")
    adj_t = 2 * (best - null)
    ref_d = 2 * (null[:nr] - true_null)
    eval_d = 2 * (null[nr:, None] - eval_null_profile)
    for values in (adj_t, ref_d, eval_d, constant_t):
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError("invalid nonnegative LR statistic")
    return {
        "reference_t_adj": adj_t[:nr].reshape(r, 81),
        "reference_t_constant": constant_t[BETA_ZERO_INDEX:nr:81],
        "reference_d_beta": ref_d.reshape(r, 81),
        "evaluation_t_adj": adj_t[nr:].reshape(n, 8),
        "evaluation_t_constant": constant_t[nr:].reshape(n, 8),
        "evaluation_d_beta": eval_d.reshape(n, 8, 81),
        "evaluation_h_hat_adj": EFFECTS[h_index[nr:]].reshape(n, 8),
        "evaluation_beta_hat_adj": BETAS[beta_index[nr:]].reshape(n, 8),
        "evaluation_h_hat_constant": EFFECTS[constant_h[nr:]].reshape(n, 8),
        "evaluation_beta_hat_null": BETAS[null_beta[nr:]].reshape(n, 8),
        "evaluation_delta_holdout_adj_constant": (held_best[nr:] - held_constant[nr:]).reshape(
            n, 8
        ),
        "evaluation_delta_holdout_adj_neutral": (held_best[nr:] - held_null[nr:]).reshape(n, 8),
        "evaluation_delta_holdout_constant_neutral": (
            held_constant[nr:] - held_constant_null[nr:]
        ).reshape(n, 8),
        "betas": BETAS.copy(),
        "effects": EFFECTS.copy(),
        "cell_ids": np.asarray(generator.CELL_IDS),
        "truth_h": np.asarray(generator.TRUTH_H),
        "truth_beta": np.asarray(generator.TRUTH_BETA),
    }


def seed_controls() -> dict[str, Any]:
    """Check the registered Goal054 streams against earlier campaigns."""

    phase_specs = {
        "reference": (generator.REFERENCE_ROOT, "reference", REFERENCE_BLOCKS),
        "evaluation": (generator.EVALUATION_ROOT, "evaluation", EVALUATION_BLOCKS),
        "timing_reference": (
            generator.TIMING_REFERENCE_ROOT,
            "timing_reference",
            TIMING_REFERENCE_BLOCKS,
        ),
        "timing_evaluation": (
            generator.TIMING_EVALUATION_ROOT,
            "timing_evaluation",
            TIMING_EVALUATION_BLOCKS,
        ),
        "bootstrap": (generator.BOOTSTRAP_ROOT, "bootstrap", generator.BOOTSTRAP_REPLICATES),
        "smoke": (generator.SMOKE_ROOT, "smoke", generator.SMOKE_REPLICATES),
    }
    streams: dict[str, set[int]] = {}
    for name, (root, phase, count) in phase_specs.items():
        records = generator.spawn_generator_seeds(root, cast(Any, phase), count)
        values = {value for record in records for value in record.stream_seeds}
        if len(values) != 7 * count:
            raise RuntimeError(f"Goal054 seed collision in {name}")
        streams[name] = values
    roots = [spec[0] for spec in phase_specs.values()]
    if len(set(roots)) != len(roots):
        raise RuntimeError("Goal054 seed roots are not distinct")
    all_new = set().union(*streams.values())
    previous: set[int] = set()
    for root, phase, count in (
        (old_generator.PRODUCTION_ROOT, "production", 1_000),
        (old_generator.TIMING_ROOT, "timing", 20),
        (old_generator.SMOKE_ROOT, "smoke", 2),
    ):
        previous.update(
            value
            for record in old_generator.spawn_generator_seeds(root, cast(Any, phase), count)
            for value in record.stream_seeds
        )
    prior = prior_generator
    for root, phase, count in (
        (prior.PRODUCTION_ROOT, "production", 1000),
        (prior.TIMING_ROOT, "timing", 16),
        (prior.SMOKE_ROOT, "smoke", 2),
    ):
        previous.update(
            v
            for record in prior.spawn_generator_seeds(root, cast(Any, phase), count)
            for v in record.stream_seeds
        )
    config = adequacy.production_config("timing")
    for root, phase, count in (
        (config.original_calibration_root, "calibration", 999),
        (config.original_evaluation_root, "evaluation", 1000),
        (config.fresh_calibration_root, "calibration", 999),
        (config.fresh_evaluation_root, "evaluation", 1000),
    ):
        for record in adequacy.spawn_phase_seeds(root, phase, count):
            previous.update(
                (
                    record.process_seed,
                    record.predator_detection_seed,
                    record.prey_seed,
                    record.prey_detection_seed,
                )
            )
    previous.update(legacy._expected_archived_bank_seeds(131_072))
    if not all_new.isdisjoint(previous):
        raise RuntimeError("Goal054 streams overlap an earlier campaign or bank")
    for first, first_values in streams.items():
        for second, second_values in streams.items():
            if first != second and not first_values.isdisjoint(second_values):
                raise RuntimeError(f"Goal054 stream collision: {first}/{second}")
    return {
        "roots": roots,
        "phase_stream_counts": {name: len(values) for name, values in streams.items()},
        "previous_and_bank_stream_count": len(previous),
        "all_disjoint": True,
        "root_identifiers_distinct": len(set(roots)) == len(roots),
    }


def histories_from_arrays(
    predator_counts: NDArray[Any],
    prey_counts: NDArray[Any],
    site_ids: Sequence[str],
    site_cluster_ids: Sequence[str],
    site_splits: Sequence[str],
    *,
    start: int = 0,
    stop: int | None = None,
) -> tuple[tuple[Any, ...], ...]:
    """Construct a bounded batch of observation-only histories."""

    predator = np.asarray(predator_counts)
    prey_counts = np.asarray(prey_counts)
    if predator.shape != prey_counts.shape or predator.ndim != 3:
        raise ValueError("observation count arrays have incompatible shapes")
    if predator.shape[1:] != (len(site_ids), 6):
        raise ValueError("invalid predator observation array")
    if len(site_cluster_ids) != len(site_ids) or len(site_splits) != len(site_ids):
        raise ValueError("site metadata dimensions changed")
    end = predator.shape[0] if stop is None else min(int(stop), predator.shape[0])
    begin = max(0, int(start))
    if begin > end:
        raise ValueError("history bounds are invalid")
    selected_predator = predator[begin:end]
    selected_prey = prey_counts[begin:end]
    if not np.isin(selected_predator, (0, 1, 2)).all():
        raise ValueError("invalid predator observation array")
    if not np.isin(selected_prey, (0, 1, 2)).all():
        raise ValueError("invalid prey observation array")
    return tuple(
        tuple(
            legacy.AnalystHistory(
                str(site_ids[site]),
                str(site_cluster_ids[site]),
                str(site_splits[site]),
                tuple(int(value) for value in predator[row, site]),
                tuple(int(value) for value in prey_counts[row, site]),
                0.65,
            )
            for site in range(len(site_ids))
        )
        for row in range(begin, end)
    )


def _load_old_contract(old_root: Path) -> dict[str, Any]:
    path = old_root / "run_contract.json"
    if not path.exists():
        raise ValueError(f"Goal053 contract is missing: {path}")
    if sha256(path) != OLD_CONTRACT_SHA256:
        raise ValueError("Goal053 contract identity changed")
    contract = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if contract.get("fingerprint") != OLD_CORE:
        raise ValueError("Goal053 core fingerprint changed")
    summary = old_root / "production" / "output" / "run_summary.json"
    if not summary.exists() or sha256(summary) != OLD_PRODUCTION_SUMMARY_SHA256:
        raise ValueError("Goal053 production summary identity changed")
    return contract


def _load_old_integration(
    old_root: Path,
    index: int,
    site_ids: tuple[str, ...],
    bank_checksum: str,
) -> joint.BridgeIntegration:
    path = old_root / "integrations" / f"{index:03d}.npz"
    identity = old_campaign.fingerprint(
        {"core": OLD_CORE, "beta_index": index, "beta": float(BETAS[index])}
    )
    receipt = path.with_suffix(".json")
    if not path.exists() or not receipt.exists():
        raise ValueError(f"Goal053 integration cache is missing or partial: {path}")
    record = json.loads(receipt.read_text(encoding="utf-8"))
    if record.get("identity") != identity or record.get("sha256") != sha256(path):
        raise ValueError(f"Goal053 integration identity or checksum changed: {path}")
    with np.load(path, allow_pickle=False) as loaded:
        values = {name: loaded[name] for name in loaded.files}
    old_campaign.validate_integration_cache(values, record, identity, index)
    if record.get("sha256") != sha256(path):
        raise ValueError(f"Goal053 integration checksum changed: {path}")
    if values["category_mass"].shape != (1, len(site_ids), 7):
        raise ValueError("Goal053 integration site dimensions changed")
    return joint.BridgeIntegration(
        (1.0,),
        tuple(float(value) for value in EFFECTS),
        site_ids,
        np.asarray(values["category_mass"], dtype=np.float64),
        (np.asarray(values["survival_moments"], dtype=np.float64),),
        bank_checksum,
    )


def _score_panel(
    path: Path,
    integration: joint.BridgeIntegration,
    batch_size: int = BATCH_SIZE,
) -> tuple[NDArray[Any], NDArray[Any], NDArray[Any]]:
    with np.load(path, allow_pickle=False) as loaded:
        values = {name: loaded[name] for name in loaded.files}
    required = {"predator_counts", "prey_counts", "site_ids", "site_cluster_ids", "site_splits"}
    if not required.issubset(values):
        raise ValueError("observation panel is incomplete")
    if not np.array_equal(values["effects"], EFFECTS) or not np.array_equal(values["betas"], BETAS):
        raise ValueError("observation panel grid changed")
    if tuple(values["site_ids"]) != integration.site_ids:
        raise ValueError("observation and integration site order changed")
    count = int(values["predator_counts"].shape[0])
    training = np.empty((count, len(EFFECTS)), dtype=np.float64)
    heldout = np.empty_like(training)
    predator = np.empty(count, dtype=np.float64)
    for start in range(0, count, batch_size):
        stop = min(count, start + batch_size)
        histories = histories_from_arrays(
            values["predator_counts"],
            values["prey_counts"],
            values["site_ids"],
            values["site_cluster_ids"],
            values["site_splits"],
            start=start,
            stop=stop,
        )
        for offset, history in enumerate(histories, start):
            train, held, pred = joint.evaluate_dataset(cast(Any, history), integration)
            training[offset] = train[0]
            heldout[offset] = held[0]
            predator[offset] = pred[0]
    if (
        not np.isfinite(training).all()
        or not np.isfinite(heldout).all()
        or not np.isfinite(predator).all()
    ):
        raise RuntimeError("likelihood scorer produced non-finite scores")
    return training, heldout, predator


def _score_row_worker(task: tuple[Any, ...]) -> dict[str, Any]:
    (
        index,
        row_path,
        phase_id,
        old_root,
        reference_path,
        evaluation_path,
        site_ids,
        bank_checksum,
    ) = task
    index = int(index)
    identity = fingerprint({"phase": phase_id, "beta_index": index, "beta": float(BETAS[index])})
    output = Path(row_path)
    cached = read_committed(output, identity)
    if cached is not None:
        values, record = cached
        _validate_row_values(values)
        return record
    started = time.perf_counter()
    integration = _load_old_integration(Path(old_root), index, tuple(site_ids), bank_checksum)
    reference_training, reference_holdout, reference_predator = _score_panel(
        Path(reference_path), integration
    )
    evaluation_training, evaluation_holdout, evaluation_predator = _score_panel(
        Path(evaluation_path), integration
    )
    values = {
        "latent_training": np.concatenate((reference_training, evaluation_training), axis=0),
        "latent_holdout_joint": np.concatenate((reference_holdout, evaluation_holdout), axis=0),
        "latent_holdout_predator": np.concatenate(
            (reference_predator, evaluation_predator), axis=0
        ),
    }
    _validate_row_values(values)
    record = {
        "identity": identity,
        "phase_fingerprint": phase_id,
        "index": index,
        "beta": float(BETAS[index]),
        "scoring_seconds": time.perf_counter() - started,
    }
    commit_npz(output, values, record)
    return record


def _validate_row_values(values: Mapping[str, NDArray[Any]], count: int | None = None) -> None:
    if set(values) != {"latent_training", "latent_holdout_joint", "latent_holdout_predator"}:
        raise ValueError("score row schema changed")
    train = values["latent_training"]
    if train.ndim != 2 or train.shape[1] != 181 or (count is not None and train.shape[0] != count):
        raise ValueError("score row history/grid coverage changed")
    if values["latent_holdout_joint"].shape != train.shape or values[
        "latent_holdout_predator"
    ].shape != (train.shape[0],):
        raise ValueError("holdout score dimensions changed")
    if any(v.dtype != np.float64 or not np.isfinite(v).all() for v in values.values()):
        raise ValueError("score row contains invalid values")


def _panel_paths(output: Path) -> tuple[Path, Path]:
    return output / "observations_reference.npz", output / "observations_evaluation.npz"


def _generate_panel(
    output: Path,
    panel: str,
    fixed: Any,
    setup: Any,
    count: int,
    root: int,
    identity: str,
) -> tuple[Path, dict[str, Any]]:
    """Generate and commit one panel using preallocated numeric arrays."""

    if panel not in {"reference", "evaluation"} or count <= 0:
        raise ValueError("invalid panel or block count")
    cells = len(BETAS) if panel == "reference" else len(generator.EVALUATION_CELL_IDS)
    histories = count * cells
    seeds = generator.spawn_generator_seeds(root, cast(Any, panel), count)
    started = time.perf_counter()
    first, diagnostics = generator.generate_block(fixed, setup, seeds[0], panel=cast(Any, panel))
    keys = {
        "cell_ids": first["cell_ids"],
        "truth_h": first["truth_h"],
        "truth_beta": first["truth_beta"],
        "opaque_ids": first["opaque_ids"],
        "replicate_indices": first["replicate_indices"],
        "predator_counts": first["predator_counts"],
        "prey_counts": first["prey_counts"],
        "true_arrival": first["true_arrival"],
        "true_extirpation": first["true_extirpation"],
        "true_hazards": first["true_hazards"],
    }
    arrays: dict[str, NDArray[Any]] = {}
    for name, value in keys.items():
        shape = (histories, *value.shape[1:])
        arrays[name] = np.empty(shape, dtype=value.dtype)
    arrays["site_ids"] = np.asarray(setup.site_ids)
    arrays["site_cluster_ids"] = np.asarray(setup.site_cluster_ids)
    arrays["site_splits"] = np.asarray(setup.site_splits)
    arrays["effects"] = EFFECTS.copy()
    arrays["betas"] = BETAS.copy()
    all_diagnostics: list[dict[str, object]] = []
    for block, seed in enumerate(seeds):
        if block == 0:
            values, block_diagnostics = first, diagnostics
        else:
            values, block_diagnostics = generator.generate_block(
                fixed, setup, seed, panel=cast(Any, panel)
            )
        begin = block * cells
        end = begin + cells
        for name in keys:
            arrays[name][begin:end] = values[name]
        # Reference diagnostics are deterministic apart from block-level maps;
        # retain block zero plus every evaluation row for compact provenance.
        if panel == "evaluation" or block == 0:
            all_diagnostics.extend(block_diagnostics)
    path = output / (
        "observations_reference.npz" if panel == "reference" else "observations_evaluation.npz"
    )
    record = {
        "identity": identity,
        "panel": panel,
        "blocks": count,
        "histories": histories,
        "cells_per_block": cells,
        "generation_seconds": time.perf_counter() - started,
        "seeds": [asdict(seed) for seed in seeds],
        "diagnostics": _json_safe(all_diagnostics),
    }
    commit_npz(path, arrays, record)
    print(f"{panel}: {histories} histories committed", flush=True)
    return path, record


def _reduce_output(
    output: Path,
    reference_blocks: int,
    evaluation_blocks: int,
    phase_id: str,
) -> tuple[Path, float]:
    started = time.perf_counter()

    def rows() -> Iterable[tuple[int, Mapping[str, NDArray[Any]]]]:
        for index in range(81):
            path = output / "rows" / f"{index:03d}.npz"
            identity = fingerprint(
                {"phase": phase_id, "beta_index": index, "beta": float(BETAS[index])}
            )
            cached = read_committed(path, identity)
            if cached is None or cached[1].get("phase_fingerprint") != phase_id:
                raise ValueError("missing or changed coefficient row")
            yield index, cached[0]

    stats = reduce_rows(
        rows(), reference_blocks=reference_blocks, evaluation_blocks=evaluation_blocks
    )
    path = output / "stats.npz"
    commit_npz(path, stats, {"identity": phase_id, "phase_fingerprint": phase_id})
    return path, time.perf_counter() - started


def _reference_controls(
    old_root: Path,
    pilot_output: Path,
    setup: Any,
    site_ids: tuple[str, ...],
    bank_checksum: str,
) -> float:
    """Replay all 24 Goal052 histories at every new beta row."""

    evidence_path = pilot_output / "evidence.npz"
    if not evidence_path.exists():
        raise ValueError(f"Goal052 evidence is missing: {evidence_path}")
    with np.load(evidence_path, allow_pickle=False) as loaded:
        reference = {name: loaded[name] for name in loaded.files}
    max_error = 0.0
    for index in range(len(BETAS)):
        integration = _load_old_integration(old_root, index, site_ids, bank_checksum)
        max_error = max(
            max_error, old_campaign.reference_check(integration, index, reference, setup)
        )
    if not math.isfinite(max_error) or max_error > 1e-10:
        raise ValueError("non-finite or failed frozen reference replay")
    return max_error


def _validate_production_gate(root: Path, workers: int, core: str) -> dict[str, Any]:
    timing_path = root / "timing" / "output" / "run_summary.json"
    budget_path = root / "production-budget.json"
    if not timing_path.exists() or not budget_path.exists():
        raise ValueError("production requires timing qualification and budget")
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    budget = json.loads(budget_path.read_text(encoding="utf-8"))
    if (
        timing.get("fingerprint") != core
        or budget.get("fingerprint") != core
        or timing.get("workers") != workers
        or budget.get("workers") != workers
        or budget.get("timing_summary_sha256") != sha256(timing_path)
        or not timing.get("controls_passed")
        or not timing.get("source_identity_unchanged")
        or not isinstance(timing.get("output_sha256"), dict)
    ):
        raise ValueError("production lacks current timing qualification")
    output = timing_path.parent
    observed = {
        str(path.relative_to(output)): sha256(path)
        for path in output.rglob("*")
        if path.is_file() and path.name != "run_summary.json" and ".tmp" not in path.name
    }
    if observed != timing["output_sha256"]:
        raise ValueError("timing output hash manifest changed")
    return cast(dict[str, Any], budget)


def run_phase(
    root: Path,
    phase: str,
    old_root: Path,
    pilot_output: Path,
    wrapper: Path,
    workers: int = 16,
) -> dict[str, Any]:
    """Run the bounded Goal054 timing or production phase.

    ``old_root`` and ``pilot_output`` are read-only authenticated Goal053 and
    Goal052 inputs.  The function never rebuilds the empirical bank and refuses
    a completed phase or a changed contract.
    """

    if phase not in {"timing", "production"} or not 1 <= workers <= 32:
        raise ValueError("invalid phase or worker count")
    started = time.perf_counter()
    repository = Path(__file__).resolve().parents[2]
    output = root / phase / "output"
    output.mkdir(parents=True, exist_ok=True)
    if (output / "run_summary.json").exists():
        raise ValueError("completed phase cannot be restarted")
    old_contract = _load_old_contract(old_root)
    if (
        sha256(pilot_output / "run_contract.json") != old_campaign.PILOT_CONTRACT
        or sha256(pilot_output / "evidence.npz") != old_campaign.PILOT_EVIDENCE
    ):
        raise ValueError("frozen Goal052 input identity changed")
    if sha256(Path(old_contract["bank"]["bank_path"])) != old_contract["bank"]["bank_file_sha256"]:
        raise ValueError("frozen analysis bank changed")
    input_files = [
        old_root / "integrations" / f"{j:03d}{suffix}"
        for j in range(81)
        for suffix in (".npz", ".json")
    ]
    input_hashes = {str(path): sha256(path) for path in input_files}

    for name, digest in old_contract.get("source_hashes", {}).items():
        source = repository / name
        if not source.exists() or sha256(source) != digest:
            raise ValueError(f"frozen Goal053 source changed: {name}")
    sources = source_hashes(repository)
    wrapper_hash = sha256(wrapper)
    bank = old_contract.get("bank", {})
    bank_checksum = str(bank.get("bank_checksum", ""))
    if len(bank_checksum) != 64:
        raise ValueError("Goal053 bank checksum is missing")
    fixed = benchmark.build_fixed_inputs()
    setup = generator.build_generator_setup(fixed)
    site_ids = tuple(setup.site_ids)
    controls = seed_controls()
    contract_payload: dict[str, Any] = {
        "workflow": "goal054_null_effect_calibration_v1",
        "source_hashes": sources,
        "wrapper_sha256": wrapper_hash,
        "goal053_core": OLD_CORE,
        "goal053_contract_sha256": OLD_CONTRACT_SHA256,
        "goal053_production_summary_sha256": OLD_PRODUCTION_SUMMARY_SHA256,
        "goal052_pilot_contract_sha256": sha256(pilot_output / "run_contract.json"),
        "bank_checksum": bank_checksum,
        "integration_input_sha256": input_hashes,
        "effects": EFFECTS.tolist(),
        "betas": BETAS.tolist(),
        "reference_blocks": REFERENCE_BLOCKS,
        "evaluation_blocks": EVALUATION_BLOCKS,
        "timing_reference_blocks": TIMING_REFERENCE_BLOCKS,
        "timing_evaluation_blocks": TIMING_EVALUATION_BLOCKS,
        "seed_controls": controls,
        "worker_identity": worker_identity(),
    }
    core = fingerprint(contract_payload)
    contract_payload["fingerprint"] = core
    contract_path = root / "run_contract.json"
    if contract_path.exists():
        existing = json.loads(contract_path.read_text(encoding="utf-8"))
        if existing != contract_payload:
            raise ValueError("Goal054 run contract changed")
    else:
        write_json(contract_path, contract_payload)
    if phase == "production":
        _validate_production_gate(root, workers, core)

    reference_blocks = TIMING_REFERENCE_BLOCKS if phase == "timing" else REFERENCE_BLOCKS
    evaluation_blocks = TIMING_EVALUATION_BLOCKS if phase == "timing" else EVALUATION_BLOCKS
    reference_identity = fingerprint(
        {"core": core, "phase": phase, "panel": "reference", "blocks": reference_blocks}
    )
    evaluation_identity = fingerprint(
        {"core": core, "phase": phase, "panel": "evaluation", "blocks": evaluation_blocks}
    )
    reference_path, evaluation_path = _panel_paths(output)
    reference_record: dict[str, Any]
    # _panel_paths returns canonical paths; use authenticated caches when they
    # exist, otherwise generate exactly the registered block count.
    if reference_path.exists() or reference_path.with_suffix(".json").exists():
        cached = read_committed(reference_path, reference_identity)
        if cached is None or cached[1].get("blocks") != reference_blocks:
            raise ValueError("reference observation cache is incomplete")
        reference_record = cached[1]
    else:
        reference_path, reference_record = _generate_panel(
            output,
            "reference",
            fixed,
            setup,
            reference_blocks,
            generator.TIMING_REFERENCE_ROOT if phase == "timing" else generator.REFERENCE_ROOT,
            reference_identity,
        )
    evaluation_record: dict[str, Any]
    if evaluation_path.exists() or evaluation_path.with_suffix(".json").exists():
        cached = read_committed(evaluation_path, evaluation_identity)
        if cached is None or cached[1].get("blocks") != evaluation_blocks:
            raise ValueError("evaluation observation cache is incomplete")
        evaluation_record = cached[1]
    else:
        evaluation_path, evaluation_record = _generate_panel(
            output,
            "evaluation",
            fixed,
            setup,
            evaluation_blocks,
            generator.TIMING_EVALUATION_ROOT if phase == "timing" else generator.EVALUATION_ROOT,
            evaluation_identity,
        )
    # Every coefficient row performs the full Goal052 replay before scoring.
    replay_started = time.perf_counter()
    reference_error = _reference_controls(old_root, pilot_output, setup, site_ids, bank_checksum)
    reference_seconds = time.perf_counter() - replay_started
    print(f"{phase}: all 81 frozen rows replayed; max error {reference_error:.3g}", flush=True)
    phase_id = fingerprint(
        {
            "core": core,
            "phase": phase,
            "reference_observation_sha256": sha256(reference_path),
            "evaluation_observation_sha256": sha256(evaluation_path),
        }
    )
    rows_started = time.perf_counter()
    tasks = [
        (
            index,
            output / "rows" / f"{index:03d}.npz",
            phase_id,
            old_root,
            reference_path,
            evaluation_path,
            site_ids,
            bank_checksum,
        )
        for index in range(len(BETAS))
    ]
    records: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_score_row_worker, task) for task in tasks]
        for future in as_completed(futures):
            result = future.result()
            records.append(result)
            print(
                f"{phase}: beta {result['beta']:+.2f} complete; "
                f"{result['scoring_seconds']:.1f} scoring seconds",
                flush=True,
            )
    records.sort(key=lambda value: int(value["index"]))
    _stats_path, reduction_seconds = _reduce_output(
        output, reference_blocks, evaluation_blocks, phase_id
    )
    source_unchanged = source_hashes(repository) == sources and sha256(wrapper) == wrapper_hash
    if not source_unchanged:
        raise RuntimeError("source or wrapper changed during Goal054 phase")
    if any(sha256(Path(path)) != value for path, value in input_hashes.items()):
        raise RuntimeError("frozen integration input changed during phase")
    histories = reference_blocks * len(BETAS) + evaluation_blocks * len(
        generator.EVALUATION_CELL_IDS
    )
    elapsed = time.perf_counter() - started
    generation_seconds = float(reference_record.get("generation_seconds", 0.0)) + float(
        evaluation_record.get("generation_seconds", 0.0)
    )
    scoring_seconds = float(sum(record.get("scoring_seconds", 0.0) for record in records))
    serialization_seconds = float(
        reference_record.get("serialization_seconds", 0.0)
        + evaluation_record.get("serialization_seconds", 0.0)
        + sum(record.get("serialization_seconds", 0.0) for record in records)
    )
    summary: dict[str, Any] = {
        "phase": phase,
        "fingerprint": core,
        "phase_fingerprint": phase_id,
        "finished_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": elapsed,
        "histories": histories,
        "reference_blocks": reference_blocks,
        "evaluation_blocks": evaluation_blocks,
        "rows": len(records),
        "workers": workers,
        "worker_identity": worker_identity(),
        "controls_passed": bool(controls["all_disjoint"] and reference_error <= 1e-10),
        "source_identity_unchanged": source_unchanged,
        "reference_replay_error": reference_error,
        "reference_replay_seconds": reference_seconds,
        "generation_seconds": generation_seconds,
        "scoring_seconds": scoring_seconds,
        "serialization_seconds": serialization_seconds,
        "reduction_seconds": reduction_seconds,
        "row_seconds": time.perf_counter() - rows_started,
        "output_sha256": {},
    }
    if phase == "timing":
        reserve = 3_600.0
        scale = (REFERENCE_BLOCKS * 81 + EVALUATION_BLOCKS * 8) / histories
        generation_projection = (
            float(reference_record["generation_seconds"]) * REFERENCE_BLOCKS / reference_blocks
            + float(evaluation_record["generation_seconds"]) * EVALUATION_BLOCKS / evaluation_blocks
        )
        waves = math.ceil(81 / workers)
        scoring_projection = max(float(v["scoring_seconds"]) for v in records) * waves * scale
        # Serialization includes input panels and row writes, treated serially
        # for a conservative complete-workload projection.
        io_projection = (serialization_seconds + reduction_seconds) * scale
        projected = (
            1.5 * (generation_projection + scoring_projection + io_projection + reference_seconds)
            + reserve
        )
        summary["projection"] = {
            "complete_production_seconds": projected,
            "synthesis_verification_reserve_seconds": reserve,
            "safety_factor": 1.5,
            "worker_waves": waves,
            "generation_seconds": generation_projection,
            "scoring_seconds": scoring_projection,
            "serialization_reduction_seconds": io_projection,
            "fixed_replay_seconds": reference_seconds,
            "timing_reference_blocks": reference_blocks,
            "timing_evaluation_blocks": evaluation_blocks,
        }
        summary["complete_production_seconds"] = projected
        summary["synthesis_verification_reserve_seconds"] = reserve
    else:
        summary["complete_production_seconds"] = elapsed
        summary["synthesis_verification_reserve_seconds"] = 3_600.0
    files = [
        path
        for path in output.rglob("*")
        if path.is_file() and path.name != "run_summary.json" and ".tmp" not in path.name
    ]
    summary["output_sha256"] = {str(path.relative_to(output)): sha256(path) for path in files}
    write_json(output / "run_summary.json", summary)
    return summary


__all__ = [
    "BATCH_SIZE",
    "BETAS",
    "EFFECTS",
    "commit_npz",
    "histories_from_arrays",
    "read_committed",
    "reduce_rows",
    "run_phase",
    "seed_controls",
    "sha256",
    "source_hashes",
    "write_json",
]
