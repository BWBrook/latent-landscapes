"""Checkpointed materialization of the capstone's already frozen references.

The scientific generators, fits and ranks remain in the qualified modules.
Each open effect history is committed before fitting; a completed numerical
failure is retained, while interrupted work resumes at its original address.
"""

from __future__ import annotations

import hashlib
import io
import json
import multiprocessing as mp
import sqlite3
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import capstone_calibration as calibration
from latent_landscapes import capstone_public as public_api
from latent_landscapes import capstone_qualification as qualification
from latent_landscapes import preinvasion_effect_reference as effect
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.preinvasion_effect_gate import EffectFitBatch

MECHANICAL_ROOT = 987654321
SCHEMA = "goal061-capstone-reference-v1"
QUALIFIED_READY_SHA256 = "e42501fcb5cc438c1706d6e32352f17b22969b89811d3f3114809bd2802b64a2"


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path: Path, value: Any) -> None:
    """Atomically publish status; immutable scientific records use SQLite."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(qualification.jsonable(value), sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


@dataclass(frozen=True)
class ReferenceContext:
    public: public_api.PublicInputs
    bank: likelihood.CompressedBank

    @property
    def site_ids(self) -> tuple[str, ...]:
        return tuple(str(x) for x in self.public.setup.site_ids)

    @property
    def training_mask(self) -> NDArray[np.bool_]:
        return np.asarray(np.asarray(self.public.setup.site_splits) == "training", dtype=np.bool_)

    @property
    def map_a(self) -> NDArray[np.float64]:
        return np.asarray(self.public.setup.exposure_score, dtype=np.float64)

    @property
    def site_a(self) -> NDArray[np.float64]:
        return np.asarray(
            self.map_a[self.public.setup.site_rows, self.public.setup.site_cols], dtype=np.float64
        )


def load_context(package: Path, *, verify: bool = True) -> ReferenceContext:
    ready_path = package / "public-ready.json"
    if sha256(ready_path) != QUALIFIED_READY_SHA256:
        raise ValueError("qualified readiness receipt changed")
    ready = json.loads(ready_path.read_text())
    if ready.get("public_ready") is not True:
        raise ValueError("public package is not qualified")
    if verify:
        for name, expected in ready["files"].items():
            if sha256(package / name) != expected:
                raise ValueError(f"qualified input changed: {name}")
    public = public_api.load_public_inputs(package / "public_inputs")
    arrivals = np.load(package / "arrival_bank/arrivals.npy", mmap_mode="r", allow_pickle=False)
    if arrivals.shape != (131072, 160):
        raise ValueError("qualified bank dimensions changed")
    bank = likelihood.compress_bank(arrivals, tuple(str(x) for x in public.setup.site_ids))
    return ReferenceContext(public, bank)


def make_observations(context: ReferenceContext, prey: Any, predator: Any) -> Any:
    prey_array = np.asarray(prey, dtype=np.int64)
    predator_array = np.asarray(predator, dtype=np.int64)
    if prey_array.ndim == predator_array.ndim == 2:
        prey_array = prey_array[None, ...]
        predator_array = predator_array[None, ...]
    return likelihood.prepare_observations(
        prey_array,
        predator_array,
        context.site_ids,
        context.training_mask,
    )


def validate_reference_request(kind: str, root: int, references: int) -> None:
    expected = 99 if kind == "screen" else 999
    if kind not in ("screen", "effect") or root not in (calibration.ROOT_SEED, MECHANICAL_ROOT):
        raise ValueError("only the frozen or mechanical reference root is permitted")
    if not 1 <= references <= expected:
        raise ValueError("invalid reference count")
    if root == calibration.ROOT_SEED and references != expected:
        raise ValueError("registered reference counts cannot be reduced")


def _metadata(kind: str, binding: str, node: int, root: int, references: int) -> dict[str, Any]:
    calibration.grid_coordinates(node)
    validate_reference_request(kind, root, references)
    return {
        "schema": SCHEMA,
        "kind": kind,
        "binding_sha256": binding,
        "node": node,
        "root": root,
        "namespace": 59,
        "domain": calibration.DOMAINS[kind],
        "references": references,
    }


class EffectStore:
    """One node, atomic per-reference checkpoints and verified immutable rows."""

    def __init__(self, path: Path, metadata: Mapping[str, Any], *, readonly: bool = False) -> None:
        self.readonly = readonly
        if readonly:
            if not path.is_file():
                raise calibration.CalibrationPendingError("effect node is absent")
            self.connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(path, timeout=60)
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY, value TEXT)"
            )
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS results (reference INTEGER PRIMARY KEY, "
                "observations BLOB NOT NULL, observations_sha256 TEXT NOT NULL, "
                "payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL, complete INTEGER NOT NULL)"
            )
        encoded = json.dumps(dict(metadata), sort_keys=True, allow_nan=False)
        row = self.connection.execute("SELECT value FROM metadata WHERE id=1").fetchone()
        if row is None and not readonly:
            self.connection.execute("INSERT INTO metadata VALUES (1, ?)", (encoded,))
            self.connection.commit()
        elif row is None or row[0] != encoded:
            self.connection.close()
            raise ValueError("reference checkpoint belongs to a different frozen run")

    def get(self, reference: int) -> tuple[bytes, dict[str, Any], bool] | None:
        row = self.connection.execute(
            "SELECT observations,observations_sha256,payload,payload_sha256,complete "
            "FROM results WHERE reference=?",
            (reference,),
        ).fetchone()
        if row is None:
            return None
        if hashlib.sha256(row[0]).hexdigest() != row[1]:
            raise ValueError("reference observation checkpoint hash mismatch")
        if hashlib.sha256(row[2].encode()).hexdigest() != row[3]:
            raise ValueError("reference fit checkpoint hash mismatch")
        return bytes(row[0]), json.loads(row[2]), bool(row[4])

    def generated(self, reference: int, observations: bytes, payload: Mapping[str, Any]) -> None:
        encoded = json.dumps(qualification.jsonable(payload), sort_keys=True, allow_nan=False)
        with self.connection:
            self.connection.execute(
                "INSERT INTO results VALUES (?, ?, ?, ?, ?, 0)",
                (
                    reference,
                    observations,
                    hashlib.sha256(observations).hexdigest(),
                    encoded,
                    hashlib.sha256(encoded.encode()).hexdigest(),
                ),
            )

    def completed(self, reference: int, payload: Mapping[str, Any]) -> None:
        encoded = json.dumps(qualification.jsonable(payload), sort_keys=True, allow_nan=False)
        with self.connection:
            cursor = self.connection.execute(
                "UPDATE results SET payload=?,payload_sha256=?,complete=1 "
                "WHERE reference=? AND complete=0",
                (encoded, hashlib.sha256(encoded.encode()).hexdigest(), reference),
            )
            if cursor.rowcount != 1:
                raise ValueError("cannot replace a completed reference or fit an absent history")

    def close(self) -> None:
        if not self.readonly:
            self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.connection.close()


def reference_blob(raw: Mapping[str, Any], evaluator: Mapping[str, Any]) -> bytes:
    arrays: dict[str, Any] = {
        "prey_counts": np.asarray(raw["prey_counts"], dtype=np.int8),
        "predator_counts": np.asarray(raw["predator_counts"], dtype=np.int8),
    }
    arrays.update(
        {
            f"evaluator_{name}": value
            for name, value in evaluator.items()
            if isinstance(value, np.ndarray)
        }
    )
    stream = io.BytesIO()
    np.savez_compressed(stream, **arrays)
    return stream.getvalue()


def run_effect_node(
    context: ReferenceContext,
    directory: Path,
    node: int,
    *,
    binding: str,
    root: int = calibration.ROOT_SEED,
    references: int = 999,
) -> dict[str, Any]:
    metadata = _metadata("effect", binding, node, root, references)
    directory.mkdir(parents=True, exist_ok=True)
    complete_path = directory / f"node-{node:04d}-complete.json"
    if complete_path.exists():
        complete = json.loads(complete_path.read_text())
        if any(complete.get(key) != value for key, value in metadata.items()):
            raise ValueError("effect completion belongs to another frozen run")
        if (
            complete.get("completed") != references
            or sha256(directory / f"node-{node:04d}.sqlite") != complete["database_sha256"]
        ):
            raise ValueError("completed effect database changed")
        return dict(complete)
    store = EffectStore(directory / f"node-{node:04d}.sqlite", metadata)
    point = calibration.NUISANCE_GRID[node]
    truth = {"h": 1.0, "beta": point.beta, "mu": point.mu, "detection_sd": point.detection_sd}
    started = time.perf_counter()
    reused = 0
    invalid = 0
    try:
        for reference in range(references):
            saved = store.get(reference)
            if saved is None:
                before = time.perf_counter()
                raw, evaluator = calibration.generate_effect_reference(
                    context.public,
                    node,
                    reference,
                    root=root,
                )
                blob = reference_blob(raw, evaluator)
                payload: dict[str, Any] = {
                    "node": node,
                    "reference": reference,
                    "truth": truth,
                    "seeds": calibration.reference_seeds("effect", node, reference, root=root),
                    "generation_seconds": time.perf_counter() - before,
                }
                store.generated(reference, blob, payload)
            else:
                blob, payload, complete = saved
                if complete:
                    reused += 1
                    invalid += not bool(payload["statistics"]["valid"])
                    continue
            with np.load(io.BytesIO(blob), allow_pickle=False) as values:
                observed = make_observations(
                    context, values["prey_counts"], values["predator_counts"]
                )
            data = qualification.make_fit_data(context.public, context.bank, observed)
            before = time.perf_counter()
            pair = effect.fit_effect_pair_with_truth(data, qualification.fit_loglikelihood, truth)
            payload.update(
                {
                    "null_fit": effect.serialize_fit(pair.null_fit),
                    "free_fit": effect.serialize_fit(pair.free_fit),
                    "statistics": dict(pair.statistics),
                    "fit_seconds": time.perf_counter() - before,
                }
            )
            store.completed(reference, payload)
            invalid += not bool(pair.statistics["valid"])
            if (reference + 1) % 25 == 0 or reference + 1 == references:
                write_json(
                    directory / f"node-{node:04d}-progress.json",
                    {
                        **metadata,
                        "completed": reference + 1,
                        "invalid": invalid,
                        "elapsed_seconds": time.perf_counter() - started,
                        "reused": reused,
                    },
                )
    finally:
        store.close()
    result = {
        **metadata,
        "completed": references,
        "invalid": invalid,
        "reused": reused,
        "elapsed_seconds": time.perf_counter() - started,
        "database_sha256": sha256(directory / f"node-{node:04d}.sqlite"),
    }
    write_json(directory / f"node-{node:04d}-complete.json", result)
    return result


def run_screen_node(
    context: ReferenceContext,
    directory: Path,
    node: int,
    *,
    binding: str,
    root: int = calibration.ROOT_SEED,
    references: int = 99,
) -> dict[str, Any]:
    metadata = _metadata("screen", binding, node, root, references)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"node-{node:04d}.npz"
    receipt_path = directory / f"node-{node:04d}.json"
    if receipt_path.exists():
        receipt: dict[str, Any] = json.loads(receipt_path.read_text())
        if any(receipt.get(key) != value for key, value in metadata.items()):
            raise ValueError("screen checkpoint belongs to another frozen run")
        if sha256(path) != receipt["sha256"]:
            raise ValueError("screen checkpoint hash mismatch")
        return receipt
    if path.exists():
        raise ValueError("unreceipted screen checkpoint requires diagnosis")
    started = time.perf_counter()
    prey = []
    predator = []
    for reference in range(references):
        y, z = calibration.generate_screen_reference(
            context.map_a,
            context.site_a,
            node,
            reference,
            root=root,
        )
        prey.append(y)
        predator.append(z)
    observed = make_observations(context, np.stack(prey), np.stack(predator))
    neighbours = calibration.axis_adjacent_indices(node)
    scores = np.stack(
        [
            calibration.pre_score(observed, context.map_a, context.site_a, neighbour)
            for neighbour in neighbours
        ],
        axis=1,
    )
    contrasts = 2 * np.maximum(0.0, scores.max(axis=1) - scores[:, 0])
    np.savez_compressed(
        path,
        prey_counts=np.asarray(prey, dtype=np.int8),
        predator_counts=np.asarray(predator, dtype=np.int8),
        neighbour_indices=np.asarray(neighbours, dtype=np.int64),
        local_scores=scores,
        contrasts=contrasts,
        seeds=np.asarray(
            [
                [
                    calibration.stage_seed("screen", node, reference, stage, root=root)
                    for stage in calibration.SCREEN_STAGES
                ]
                for reference in range(references)
            ],
            dtype=np.uint64,
        ),
    )
    receipt = {**metadata, "sha256": sha256(path), "elapsed_seconds": time.perf_counter() - started}
    write_json(receipt_path, receipt)
    return receipt


_CONTEXT: ReferenceContext | None = None


def _initialize(package: str) -> None:
    global _CONTEXT
    _CONTEXT = load_context(Path(package), verify=False)


def _worker(task: tuple[str, str, int, str, int, int]) -> dict[str, Any]:
    if _CONTEXT is None:
        raise RuntimeError("reference worker was not initialized")
    kind, directory, node, binding, root, references = task
    callback = run_screen_node if kind == "screen" else run_effect_node
    return callback(
        _CONTEXT, Path(directory), node, binding=binding, root=root, references=references
    )


def run_nodes(
    kind: str,
    package: Path,
    directory: Path,
    nodes: Sequence[int],
    *,
    binding: str,
    workers: int,
    root: int = calibration.ROOT_SEED,
    references: int | None = None,
) -> list[dict[str, Any]]:
    count = (99 if kind == "screen" else 999) if references is None else references
    validate_reference_request(kind, root, count)
    indices = tuple(int(x) for x in nodes)
    if tuple(sorted(set(indices))) != indices or not 1 <= workers <= 64:
        raise ValueError("nodes must be sorted and unique; workers must be 1..64")
    for node in indices:
        calibration.grid_coordinates(node)
    directory.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results = []
    # Spawn avoids carrying accidental mutable state into the fixed-seed workers.
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=mp.get_context("spawn"),
        initializer=_initialize,
        initargs=(str(package),),
    ) as pool:
        futures = {
            pool.submit(_worker, (kind, str(directory), node, binding, root, count)): node
            for node in indices
        }
        try:
            for future in as_completed(futures):
                results.append(future.result())
                write_json(
                    directory / "progress.json",
                    {
                        "kind": kind,
                        "nodes_completed": len(results),
                        "nodes_required": len(indices),
                        "references_per_node": count,
                        "workers": workers,
                        "elapsed_seconds": time.perf_counter() - started,
                    },
                )
        except BaseException:
            # The locked Python 3.14 executor supports immediate termination.
            # SQLite retains every committed row; pending rows keep their seeds.
            terminate = getattr(pool, "terminate_workers", None)
            if terminate is not None:
                terminate()
            else:
                for future in futures:
                    future.cancel()
            raise
    results.sort(key=lambda row: int(row["node"]))
    return results


def load_screen_table(directory: Path, *, binding: str) -> NDArray[np.float64]:
    values = np.empty((99, calibration.GRID_SIZE), dtype=np.float64)
    for node in range(calibration.GRID_SIZE):
        metadata = _metadata("screen", binding, node, calibration.ROOT_SEED, 99)
        receipt = json.loads((directory / f"node-{node:04d}.json").read_text())
        path = directory / f"node-{node:04d}.npz"
        if any(receipt.get(key) != value for key, value in metadata.items()):
            raise ValueError("screen binding mismatch")
        if sha256(path) != receipt["sha256"]:
            raise ValueError("screen checksum mismatch")
        with np.load(path, allow_pickle=False) as row:
            values[:, node] = row["contrasts"]
    return values


def load_effect_batch(path: Path, *, metadata: Mapping[str, Any]) -> EffectFitBatch:
    store = EffectStore(path, metadata, readonly=True)
    null, free, null_status, free_status = [], [], [], []
    try:
        present = [
            row[0]
            for row in store.connection.execute("SELECT reference FROM results ORDER BY reference")
        ]
        if present != list(range(int(metadata["references"]))):
            raise calibration.CalibrationPendingError("effect node is incomplete")
        for reference in present:
            saved = store.get(reference)
            if saved is None or not saved[2]:
                raise calibration.CalibrationPendingError("effect fit is incomplete")
            payload = saved[1]
            valid = bool(payload["statistics"]["valid"])
            null.append(payload["null_fit"]["raw_logjoint"])
            free.append(payload["free_fit"]["raw_logjoint"])
            null_status.append(payload["null_fit"]["numerical_status"] if valid else "invalid")
            free_status.append(payload["free_fit"]["numerical_status"] if valid else "invalid")
    finally:
        store.close()
    return EffectFitBatch(null, free, null_status, free_status)
