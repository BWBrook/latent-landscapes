"""Goal 058 full effect-reference micro pilot.

This module owns the openly auditable reference-bank mechanics.  Production
sampling is available only through the explicit ``run`` command in the companion
script; all random entry points require a root argument.
"""
# ruff: noqa: E501
from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import known_nuisance_calibration as legacy
from latent_landscapes import preinvasion_campaign as campaign
from latent_landscapes import preinvasion_execution as execution
from latent_landscapes import preinvasion_fitting as fitting
from latent_landscapes import preinvasion_likelihood as likelihood

ROOT_SEED = 2026100402
SEED_NAMESPACE = 58
REFERENCE_COUNT = 999
STAGES = {"spread": 1, "prey_loss": 2, "predator_visits": 3, "site_detection": 4, "prey_visits": 5}
STREAM_NAMES = tuple(STAGES)
BETA_GRID = np.linspace(-2.0, 2.0, 17)
# The calibration grids are deliberately copied as values, so this module is
# independent of any mutable calibration execution state.
MU_GRID = np.asarray([0.0005, 0.001, 0.0016, 0.002, 0.0025, 0.0032, 0.004, 0.005, 0.006])
SD_GRID = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4])
NODE_SPECS = ((382, 0.0, 0.0025, 0.2), (0, -2.0, 0.0005, 0.0), (764, 2.0, 0.006, 0.4), (44, -2.0, 0.006, 0.4))
SCHEMA_VERSION = "goal058-effect-reference-v1"
_WORKER_CONTEXT: EffectContext | None = None

FloatArray = NDArray[np.float64]

@dataclass(frozen=True, slots=True)
class EffectReferenceNode:
    coarse_id: int
    beta: float
    mu: float
    detection_sd: float
    h: float = 1.0

@dataclass(frozen=True, slots=True)
class EffectFitBatch:
    null_fit: fitting.FitResult
    free_fit: fitting.FitResult
    truth_logjoint: float | None
    statistics: dict[str, Any]

@dataclass(frozen=True, slots=True)
class EffectContext:
    fixed: Any
    setup: Any
    bank: likelihood.CompressedBank
    bank_receipt: Mapping[str, Any]
    data_template: execution.FitData
    site_ids: tuple[str, ...]
    training_mask: NDArray[np.bool_]
    map_a: FloatArray
    site_a: FloatArray
    context_timings: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class LoadedEffectTables:
    status: str
    tables: Mapping[int, FloatArray]
    reason: str | None = None


def load_effect_reference_tables(
    output: Path, plan: Any, *, expected_references: int = REFERENCE_COUNT
) -> LoadedEffectTables:
    """Load only a ready, valid union planned by ``preinvasion_effect_gate``.

    This performs the cap and status gate before opening any table files.  A
    missing or unusable table abstains only cases that require that node.
    The existing casewise combiner consumes omissions and invalid NaN tables.
    """
    if getattr(plan, "status", None) != "ready":
        return LoadedEffectTables(str(getattr(plan, "status", "invalid_plan")), {}, "reference plan is not ready")
    indices = tuple(int(index) for index in plan.union_indices)
    if len(indices) > int(plan.max_union_candidates):
        return LoadedEffectTables("abstain_over_cap", {}, "union exceeds registered cap")
    tables: dict[int, FloatArray] = {}
    unavailable = []
    for index in indices:
        path = output / f"node-{index:04d}.npz"
        if not path.exists():
            unavailable.append(index)
            continue
        with np.load(path, allow_pickle=False) as saved:
            if "T" not in saved or "valid" not in saved or "usable" not in saved:
                tables[index] = np.full(expected_references, np.nan)
                unavailable.append(index)
                continue
            values = np.asarray(saved["T"], dtype=np.float64)
            valid = np.asarray(saved["valid"], dtype=bool)
            usable = bool(np.asarray(saved["usable"]).reshape(-1)[0])
            if values.shape != (expected_references,) or valid.shape != values.shape or not usable or not np.isfinite(values).all() or not valid.all():
                tables[index] = np.full(expected_references, np.nan)
                unavailable.append(index)
                continue
            tables[index] = values
    return LoadedEffectTables("ready", tables, f"unavailable nodes: {unavailable}" if unavailable else None)


def node_specs() -> tuple[EffectReferenceNode, ...]:
    return tuple(EffectReferenceNode(*x) for x in NODE_SPECS)


def full_grid_metadata() -> list[dict[str, float | int]]:
    return [
        {"coarse_id": beta_index * 45 + mu_index * 5 + sd_index, "beta": float(beta), "mu": float(mu), "detection_sd": float(sd)}
        for beta_index, beta in enumerate(BETA_GRID)
        for mu_index, mu in enumerate(MU_GRID)
        for sd_index, sd in enumerate(SD_GRID)
    ]


def node_from_id(coarse_id: int) -> EffectReferenceNode:
    for node in node_specs():
        if node.coarse_id == coarse_id:
            return node
    raise KeyError(coarse_id)


def seed_sequence(coarse_node: int, reference: int, stage: int, *, root: int) -> np.random.SeedSequence:
    if root is None:
        raise TypeError("root is mandatory")
    if coarse_node < 0 or reference < 0 or not 1 <= stage <= 5:
        raise ValueError("invalid seed address")
    return np.random.SeedSequence([int(root), SEED_NAMESPACE, int(coarse_node), int(reference), int(stage)])


def stage_seed(coarse_node: int, reference: int, stage: int, *, root: int) -> int:
    return int(seed_sequence(coarse_node, reference, stage, root=root).generate_state(1, dtype=np.uint64)[0])


def reference_seeds(coarse_node: int, reference: int, *, root: int) -> dict[str, Any]:
    return {"root": int(root), "namespace": SEED_NAMESPACE, "coarse_node": int(coarse_node), "reference": int(reference), "streams": {name: stage_seed(coarse_node, reference, stage, root=root) for name, stage in STAGES.items()}}


def seed_ledger(*, root: int, nodes: Sequence[EffectReferenceNode] | None = None, references: int = REFERENCE_COUNT) -> NDArray[np.uint64]:
    if references <= 0:
        raise ValueError("references must be positive")
    chosen = tuple(node_specs() if nodes is None else nodes)
    out = np.empty((len(chosen) * references, 5), dtype=np.uint64)
    row = 0
    for node in chosen:
        for ref in range(references):
            out[row] = [stage_seed(node.coarse_id, ref, stage, root=root) for stage in range(1, 6)]
            row += 1
    return out


def ledger_hash(ledger: NDArray[np.uint64]) -> str:
    array = np.ascontiguousarray(ledger, dtype=np.uint64)
    return hashlib.sha256(array.tobytes()).hexdigest()


def validate_seed_ledger(ledger: NDArray[np.uint64], *, root: int, nodes: Sequence[EffectReferenceNode] | None = None, references: int = REFERENCE_COUNT, expected_hash: str | None = None) -> dict[str, Any]:
    chosen = tuple(node_specs() if nodes is None else nodes)
    expected = seed_ledger(root=root, nodes=chosen, references=references)
    actual = np.asarray(ledger, dtype=np.uint64)
    if actual.shape != expected.shape or not np.array_equal(actual, expected):
        raise ValueError("seed ledger does not match the registered address law")
    digest = ledger_hash(actual)
    if expected_hash is not None and digest != expected_hash:
        raise ValueError("seed ledger hash mismatch")
    return {"root": int(root), "namespace": SEED_NAMESPACE, "shape": list(actual.shape), "sha256": digest, "nodes": [asdict(n) for n in chosen], "references": references, "stage_order": list(STAGES)}


def jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def _fitdata(observations: likelihood.PreInvasionObservations, context: EffectContext) -> execution.FitData:
    return execution.FitData(observations, context.bank, context.map_a, context.site_a)


def prepare_context(bank_directory: Path) -> EffectContext:
    fixed, setup = campaign.public_inputs()
    ids = tuple(str(x) for x in setup.site_ids)
    order = np.argsort(np.asarray(ids), kind="stable")
    if tuple(np.asarray(ids)[order]) != ids:
        raise ValueError("public generator site order is not the registered sorted order")
    ids = tuple(np.asarray(ids)[order])
    training = np.asarray(setup.site_splits, dtype=object)[order] == "training"
    if len(ids) != 160 or int(training.sum()) != 120:
        raise ValueError("public 160-site/120-training design changed")
    site_a = np.asarray(setup.exposure_score[setup.site_rows, setup.site_cols], dtype=np.float64)[order]
    map_a = np.asarray(setup.exposure_score, dtype=np.float64)
    bank_started = time.perf_counter()
    raw, receipt = legacy.load_verified_bank(bank_directory, legacy.production_config("timing"), ids)
    bank_load_seconds = time.perf_counter() - bank_started
    compression_started = time.perf_counter()
    bank = likelihood.compress_bank(raw, ids)
    context_timings = {"bank_load_seconds": bank_load_seconds, "bank_compression_seconds": time.perf_counter() - compression_started}
    observations = likelihood.prepare_observations(np.zeros((1, len(ids), 13), dtype=np.int8), np.zeros((1, len(ids), 6), dtype=np.int8), ids, training)
    return EffectContext(fixed, setup, bank, receipt, execution.FitData(observations, bank, map_a, site_a), ids, training, map_a, site_a, context_timings)


def make_observations(raw: Mapping[str, Any], site_ids: Sequence[str], training: NDArray[np.bool_]) -> likelihood.PreInvasionObservations:
    return likelihood.prepare_observations(np.asarray(raw["prey_counts"])[None, ...], np.asarray(raw["predator_counts"])[None, ...], tuple(site_ids), training)


def generate_reference(context: EffectContext, node: EffectReferenceNode, reference: int, *, root: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    seeds = reference_seeds(node.coarse_id, reference, root=root)
    truth = campaign.OpenTruth(reference, 1.0, node.mu, node.beta, node.detection_sd)
    started = time.perf_counter()
    raw, evaluator = campaign.generate_open_history(context.fixed, context.setup, truth, seeds)
    generated = time.perf_counter() - started
    evaluator["seed_ids"] = seeds
    evaluator["truth"] = asdict(truth)
    return raw, evaluator, {"generation_seconds": generated}


def _worker_init(bank_directory: str) -> None:
    global _WORKER_CONTEXT
    _WORKER_CONTEXT = prepare_context(Path(bank_directory))


def _worker_reference(task: tuple[EffectReferenceNode, int, int]) -> tuple[EffectReferenceNode, int, dict[str, Any], dict[str, Any], dict[str, Any]]:
    if _WORKER_CONTEXT is None:
        raise RuntimeError("effect-reference worker was not initialized")
    node, reference, root = task
    started = time.perf_counter()
    raw, evaluator, generation = generate_reference(_WORKER_CONTEXT, node, reference, root=root)
    preparation_started = time.perf_counter()
    observations = make_observations(raw, _WORKER_CONTEXT.site_ids, _WORKER_CONTEXT.training_mask)
    data = _fitdata(observations, _WORKER_CONTEXT)
    preparation = time.perf_counter() - preparation_started
    pair = fit_effect_pair_with_truth(data, execution.fit_loglikelihood, evaluator["truth"])
    timings = {
        **generation,
        "preparation_seconds": preparation,
        "worker_seconds": time.perf_counter() - started,
        "null_fit_seconds": pair.statistics.get("null_seconds"),
        "free_fit_seconds": pair.statistics.get("free_seconds"),
        "score_seconds": pair.statistics.get("truth_score_seconds"),
        "write_seconds": 0.0,
    }
    return node, reference, raw, evaluator, row_payload(node, reference, raw, evaluator, pair, timings)


def _tasks(root: int, references: int) -> list[tuple[EffectReferenceNode, int, int]]:
    return [(node, reference, root) for node in node_specs() for reference in range(references)]


def qualify(output: Path, *, bank_directory: Path, root: int = 987654321) -> dict[str, Any]:
    """Verify the named bank and the adjusted pair using mechanical streams."""
    if output.exists():
        raise FileExistsError("refusing to replace qualification")
    output.mkdir(parents=True)
    started = time.perf_counter()
    context = prepare_context(bank_directory)
    rows: list[dict[str, Any]] = []
    for node in node_specs():
        raw, _evaluator, _ = generate_reference(context, node, 0, root=root)
        obs = make_observations(raw, context.site_ids, context.training_mask)
        data = _fitdata(obs, context)
        pair = fit_effect_pair(data, execution.fit_loglikelihood)
        four = fitting.fit_four_models(data, execution.fit_loglikelihood)
        expected = four["adjusted_h1"]
        expected_free = four["adjusted_free_h"]
        if pair.null_fit.model != expected.model or pair.free_fit.model != expected_free.model:
            raise AssertionError("adjusted fit model mismatch")
        for actual, reference in ((pair.null_fit, expected), (pair.free_fit, expected_free)):
            if actual.parameters != reference.parameters or actual.raw_logjoint != reference.raw_logjoint or actual.numerical_status != reference.numerical_status:
                raise AssertionError("adjusted pair differs from four-model fit")
        rows.append({"node_id": node.coarse_id, "reference": 0, "opaque_id": raw["opaque_id"], "null_status": pair.null_fit.numerical_status, "free_status": pair.free_fit.numerical_status, "null_parameters": pair.null_fit.parameters, "free_parameters": pair.free_fit.parameters, "null_raw_logjoint": pair.null_fit.raw_logjoint, "free_raw_logjoint": pair.free_fit.raw_logjoint})
    smoke = output / "smoke"
    run_reference_micro(smoke, bank_directory=bank_directory, root=root, workers=2, references=2)
    result = {"schema_version": SCHEMA_VERSION, "status": "qualified", "mechanical_root": root, "bank_receipt": jsonable(context.bank_receipt), "context_timings": dict(context.context_timings), "rows": rows, "smoke_path": "smoke", "elapsed_seconds": time.perf_counter() - started}
    (output / "qualification.json").write_text(json.dumps(jsonable(result), sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def fit_effect_pair(data: Any, callback: Callable[..., Any]) -> EffectFitBatch:
    started = time.perf_counter()
    null = fitting._run_fit(data, callback, "adjusted_h1")
    null_seconds = time.perf_counter() - started
    started = time.perf_counter()
    free = fitting._run_fit(data, callback, "adjusted_free_h", extra_candidates=(null.parameters,), extra_candidate_success=(null.converged,))
    free_seconds = time.perf_counter() - started
    truth = callback(data, h=1.0, beta=float(data.truth_beta), mu=float(data.truth_mu), detection_sd=float(data.truth_sd)) if hasattr(data, "truth_beta") else None
    finite = all(math.isfinite(x) for x in (null.raw_logjoint, free.raw_logjoint))
    delta = free.raw_logjoint - null.raw_logjoint if finite else math.nan
    stats: dict[str, Any] = {"T": 2.0 * max(0.0, delta) if finite else None, "raw_T": 2.0 * delta if finite else None, "free_minus_null": delta if finite else None, "null_converged": null.converged, "free_converged": free.converged, "finite_fits": finite, "free_ge_null": bool(finite and delta >= -1e-6), "truth_logjoint": truth, "valid": bool(finite and null.converged and free.converged and delta >= -1e-6 and (truth is None or null.raw_logjoint >= truth - 1e-6)), "null_seconds": null_seconds, "free_seconds": free_seconds}
    return EffectFitBatch(null, free, truth, stats)


def fit_effect_pair_with_truth(data: Any, callback: Callable[..., Any], truth: Mapping[str, float]) -> EffectFitBatch:
    # Avoid changing FitData: attach truth only to the callback's data through a
    # closure, while retaining the production callback unchanged.
    score_started = time.perf_counter()
    mu_value = truth["mu"] if "mu" in truth else truth["mean_hazard"]
    truth_ll = float(callback(data, h=1.0, beta=truth["beta"], mu=mu_value, detection_sd=truth["detection_sd"]))
    if not math.isfinite(truth_ll):
        raise FloatingPointError("nonfinite truth score")
    score_seconds = time.perf_counter() - score_started
    pair = fit_effect_pair(data, callback)
    for result in (pair.null_fit, pair.free_fit):
        parameters_finite = all(
            math.isfinite(float(result.parameters[name]))
            for name in ("h", "beta", "mu", "detection_sd")
        )
        if parameters_finite and not math.isfinite(float(result.raw_logjoint)):
            raise FloatingPointError(f"nonfinite fitted score at finite {result.model} point")
    stats = dict(pair.statistics)
    delta_truth = pair.null_fit.raw_logjoint - truth_ll if math.isfinite(pair.null_fit.raw_logjoint) else math.nan
    stats["truth_logjoint"] = truth_ll
    stats["truth_score_seconds"] = score_seconds
    stats["null_minus_truth"] = delta_truth if math.isfinite(delta_truth) else None
    stats["null_ge_truth"] = bool(math.isfinite(delta_truth) and delta_truth >= -1e-6)
    stats["valid"] = bool(stats["valid"] and stats["null_ge_truth"])
    return EffectFitBatch(pair.null_fit, pair.free_fit, truth_ll, stats)


def serialize_fit(result: fitting.FitResult) -> dict[str, Any]:
    try:
        value: Any = asdict(result)
    except TypeError:
        value = {"model": result.model, "h": result.h, "beta": result.beta, "mu": result.mu, "detection_sd": result.detection_sd, "raw_logjoint": result.raw_logjoint, "numerical_status": result.numerical_status, "nfev": result.nfev, "elapsed_seconds": result.elapsed_seconds}
    return cast(dict[str, Any], jsonable(value))


def row_payload(node: EffectReferenceNode, reference: int, raw: Mapping[str, Any], evaluator: Mapping[str, Any], pair: EffectFitBatch, timings: Mapping[str, float], *, error: str | None = None) -> dict[str, Any]:
    truth = evaluator.get("truth", {})
    return cast(dict[str, Any], jsonable({"schema_version": SCHEMA_VERSION, "node_id": node.coarse_id, "reference": reference, "truth": truth, "seed_ids": evaluator.get("seed_ids"), "observations": {"opaque_id": raw.get("opaque_id"), "prey_shape": list(np.asarray(raw["prey_counts"]).shape), "predator_shape": list(np.asarray(raw["predator_counts"]).shape)}, "null_fit": serialize_fit(pair.null_fit), "free_fit": serialize_fit(pair.free_fit), "statistics": pair.statistics, "timings": dict(timings), "error": error}))


def checkpoint_history(path: Path, raw: Mapping[str, Any], evaluator: Mapping[str, Any], payload: dict[str, Any]) -> float:
    started = time.perf_counter()
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, prey_counts=np.asarray(raw["prey_counts"]), predator_counts=np.asarray(raw["predator_counts"]), arrival=np.asarray(evaluator["arrival"]), loss=np.asarray(evaluator["loss"]), site_hazard=np.asarray(evaluator["site_hazard"]), site_detection=np.asarray(evaluator["site_detection"]), prey_alive=np.asarray(evaluator["prey_alive"]), seed_ids=np.asarray([evaluator["seed_ids"]["streams"][n] for n in STREAM_NAMES], dtype=np.uint64))
    path.with_suffix(".json").write_text(json.dumps(jsonable(payload), sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    elapsed = time.perf_counter() - started
    payload.setdefault("timings", {})["write_seconds"] = elapsed
    path.with_suffix(".json").write_text(json.dumps(jsonable(payload), sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return elapsed


def summarize_node(rows: Sequence[Mapping[str, Any]], node: EffectReferenceNode) -> dict[str, Any]:
    valid = [bool(r.get("statistics", {}).get("valid", False)) for r in rows]
    t = np.asarray([r.get("statistics", {}).get("T") for r in rows], dtype=object)
    numeric = np.asarray([float(x) for x in t if x is not None and math.isfinite(float(x))], dtype=float)
    return {"schema_version": SCHEMA_VERSION, "node_id": node.coarse_id, "beta": node.beta, "mu": node.mu, "detection_sd": node.detection_sd, "attempted": len(rows), "valid": int(sum(valid)), "invalid": int(len(rows) - sum(valid)), "T_finite": int(numeric.size), "T_quantiles": (np.quantile(numeric, [0.05, 0.5, 0.95]).tolist() if numeric.size else [None, None, None])}


def save_context_artifact(output: Path, context: EffectContext) -> str:
    """Persist the small public design needed by an independent auditor."""
    path = output / "context.npz"
    splits = np.asarray(context.setup.site_splits, dtype="U16")
    order = np.argsort(np.asarray(context.setup.site_ids), kind="stable")
    np.savez_compressed(path, site_ids=np.asarray(context.site_ids), site_splits=splits[order], training_mask=context.training_mask, map_a=context.map_a, site_a=context.site_a, prey_times=campaign.PREY_TIMES, predator_times=campaign.PREDATOR_TIMES)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_node_table(output: Path, rows: Sequence[Mapping[str, Any]], node: EffectReferenceNode) -> str:
    t = np.asarray([r.get("statistics", {}).get("T") if r.get("statistics", {}).get("T") is not None else np.nan for r in rows], dtype=np.float64)
    valid = np.asarray([bool(r.get("statistics", {}).get("valid", False)) for r in rows], dtype=np.bool_)
    null_ll = np.asarray([r.get("null_fit", {}).get("raw_logjoint") if r.get("null_fit", {}).get("raw_logjoint") is not None else np.nan for r in rows], dtype=np.float64)
    free_ll = np.asarray([r.get("free_fit", {}).get("raw_logjoint") if r.get("free_fit", {}).get("raw_logjoint") is not None else np.nan for r in rows], dtype=np.float64)
    path = output / f"node-{node.coarse_id:04d}.npz"
    np.savez_compressed(path, node_id=node.coarse_id, reference=np.asarray([r["reference"] for r in rows], dtype=np.int64), T=t, valid=valid, usable=np.asarray(bool(np.all(valid))), null_raw_logjoint=null_ll, free_raw_logjoint=free_ll)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_reference_micro(output: Path, *, bank_directory: Path, root: int, workers: int = 1, references: int = REFERENCE_COUNT, frozen_ledger: NDArray[np.uint64] | None = None, freeze_metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("refusing to resume or replace an existing run")
    if workers < 1 or workers > 16:
        raise ValueError("workers must be between 1 and 16")
    output.mkdir(parents=True)
    ledger = seed_ledger(root=root, references=references) if frozen_ledger is None else np.asarray(frozen_ledger, dtype=np.uint64)
    validate_seed_ledger(ledger, root=root, references=references, expected_hash=None if freeze_metadata is None else str(freeze_metadata["sha256"]))
    np.savez_compressed(output / "seed_ledger.npz", ledger=ledger)
    freeze = validate_seed_ledger(ledger, root=root, references=references)
    freeze["full_grid_size"] = len(full_grid_metadata())
    freeze["full_grid"] = full_grid_metadata()
    (output / "freeze.json").write_text(json.dumps(freeze, sort_keys=True) + "\n", encoding="utf-8")
    context = prepare_context(bank_directory)
    context_hash = save_context_artifact(output, context)
    rows_by_node: dict[int, list[dict[str, Any]]] = {n.coarse_id: [] for n in node_specs()}
    task_iter = iter(_tasks(root, references))
    # Keep at most ``workers`` live futures.  Results are persisted by the
    # parent as they complete, so a numerical failure leaves earlier addresses.
    with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init, initargs=(str(bank_directory),)) as pool:
        pending = {
            pool.submit(_worker_reference, task): task
            for task in [next(task_iter, None) for _ in range(workers)]
            if task is not None
        }
        while pending:
            completed, still_pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                task = pending.pop(future)
                try:
                    node, ref, raw, evaluator, payload = future.result()
                except Exception as error:
                    fatal = {"schema_version": SCHEMA_VERSION, "error": str(error), "node_id": task[0].coarse_id, "reference": task[1], "root": root}
                    (output / "fatal.json").write_text(json.dumps(fatal, sort_keys=True) + "\n", encoding="utf-8")
                    for remaining in still_pending:
                        remaining.cancel()
                    raise
                checkpoint_history(output / "histories" / f"node-{node.coarse_id:04d}" / f"ref-{ref:04d}.npz", raw, evaluator, payload)
                rows_by_node[node.coarse_id].append(payload)
                next_task = next(task_iter, None)
                if next_task is not None:
                    pending[pool.submit(_worker_reference, next_task)] = next_task
    for node in node_specs():
        rows_by_node[node.coarse_id].sort(key=lambda row: int(row["reference"]))
        summary = summarize_node(rows_by_node[node.coarse_id], node)
        summary["table_sha256"] = _write_node_table(output, rows_by_node[node.coarse_id], node)
        summary["table_usable"] = bool(all(row.get("statistics", {}).get("valid", False) for row in rows_by_node[node.coarse_id]))
        (output / f"node-{node.coarse_id:04d}.json").write_text(json.dumps(jsonable(summary), sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    files = sorted(path for path in output.rglob("*") if path.is_file() and path.name != "manifest.json")
    artifact_hashes = {str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    manifest = {"schema_version": SCHEMA_VERSION, "root": root, "namespace": SEED_NAMESPACE, "refs_per_node": references, "ledger_sha256": ledger_hash(ledger), "context_sha256": context_hash, "bank_receipt": jsonable(context.bank_receipt), "context_timings": dict(context.context_timings), "stream_stages": STAGES, "artifact_sha256": artifact_hashes, "nodes": [summarize_node(rows_by_node[n.coarse_id], n) for n in node_specs()]}
    (output / "manifest.json").write_text(json.dumps(jsonable(manifest), sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return manifest
