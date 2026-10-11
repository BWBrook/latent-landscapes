#!/usr/bin/env python3
"""Run the registered Goal 062 campaign, with immutable phase checkpoints."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import shutil
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, cast

import audit_capstone_training as reference_audit
import audit_final_procedure_evaluation as audit
import numpy as np
from supervise_final_procedure_evaluation import verify_source

from latent_landscapes import capstone_calibration as calibration
from latent_landscapes import capstone_qualification as qualification
from latent_landscapes import capstone_references as references
from latent_landscapes import final_procedure_evaluation as evaluation

OBSERVATION_KEYS = ("site_ids", "training_mask", "prey_counts", "predator_counts")
EVALUATOR_KEYS = ("arrival", "loss", "site_hazard", "site_detection", "prey_alive", "map_hazard")
STAGES = ("main", "decision", "holdout", "diagnostics")
_CONTEXT: Any = None
_RESOURCES: Any = None
_CACHE: Any = None
_CACHE_AUDIT: Any = None


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    references.write_json(path, value)


def immutable_json(path: Path, value: Any) -> None:
    encoded = qualification.jsonable(value)
    if path.exists():
        if read(path) != encoded:
            raise ValueError(f"immutable JSON changed: {path}")
    else:
        write(path, encoded)


def save_arrays(path: Path, arrays: dict[str, Any]) -> None:
    if path.exists():
        with np.load(path, allow_pickle=False) as old:
            if set(old.files) != set(arrays) or any(
                not np.array_equal(old[key], value, equal_nan=True)
                if np.asarray(value).dtype.kind in "fc"
                else not np.array_equal(old[key], value)
                for key, value in arrays.items()
            ):
                raise ValueError(f"immutable arrays changed: {path}")
        return
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    temporary.replace(path)


def hashes(base: Path, names: list[str]) -> dict[str, str]:
    return {name: references.sha256(base / name) for name in names}


def check_files(base: Path, files: dict[str, str]) -> None:
    for name, expected in files.items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe receipt path")
        if references.sha256(base / relative) != expected:
            raise ValueError(f"artifact checksum changed: {base / relative}")


def verify_custody(root: Path) -> tuple[dict[str, Any], str]:
    manifest, binding = verify_source(root)
    prior = Path(manifest["prior_reference_root"])
    completion = read(root / "original-completion.json")
    if (
        completion["binding_sha256"] != manifest["original_binding"]
        or completion["all_numerical_audits_consistent"] is not True
    ):
        raise ValueError("accepted reference completion is not bound")
    check_files(prior, completion["files"])
    package = Path(manifest["qualified_package"])
    if references.sha256(package / "public-ready.json") != references.QUALIFIED_READY_SHA256:
        raise ValueError("accepted public package changed")
    check_files(package, read(package / "public-ready.json")["files"])
    write(
        root / "custody-check.json",
        {
            "binding_sha256": binding,
            "passed": True,
            "prior_files": len(completion["files"]),
            "public_files": len(read(package / "public-ready.json")["files"]),
            "old_receipts_preserved": True,
        },
    )
    return manifest, binding


def require_production_approval(root: Path) -> dict[str, Any]:
    from qualify_final_procedure_evaluation import runtime_record

    binding = references.sha256(root / "source-manifest.json")
    qualified = read(root / "benchmark/qualification.json")
    if qualified.get("passed") is not True or qualified.get("binding_sha256") != binding:
        raise ValueError("successful unchanged qualification required")
    check_files(root, qualified["files"])
    runtime = runtime_record()
    if audit.canonical_sha256(runtime) != qualified["runtime_sha256"]:
        raise ValueError("runtime differs from the measured qualification")
    if qualified.get("runtime_changed"):
        approval = read(root / "production-runtime-approval.json")
        if (
            approval.get("approved") is not True
            or approval.get("binding_sha256") != binding
            or approval.get("runtime_sha256") != qualified["runtime_sha256"]
            or approval.get("qualification_sha256")
            != references.sha256(root / "benchmark/qualification.json")
        ):
            raise ValueError("explicit runtime-amendment approval required")
    return cast(dict[str, Any], qualified)


def _initialize(package: str, cache_path: str | None) -> None:
    global _CONTEXT, _RESOURCES, _CACHE, _CACHE_AUDIT
    _CONTEXT = references.load_context(Path(package), verify=False)
    _RESOURCES = audit.load_audit_resources(Path(package))
    if cache_path is not None:
        path = Path(cache_path)
        record = read(path.with_suffix(".json"))
        if references.sha256(path) != record["npz_sha256"]:
            raise ValueError("reference cache changed")
        with np.load(path, allow_pickle=False) as stored:
            _CACHE = {name: stored[name] for name in stored.files}
        _CACHE_AUDIT = audit.make_reference_cache(
            _CACHE.get("screen_audit", _CACHE["screen"]),
            _CACHE.get("effect_audit", _CACHE["effect"]),
            screen_usable=_CACHE["screen_usable"],
            effect_usable=_CACHE["valid"],
            binding=record,
        )


def _accepted(receipt: dict[str, Any]) -> None:
    if receipt.get("passed") is not True or receipt.get("release_blocked") is True:
        raise ValueError("independent numerical audit blocked release: " + json.dumps(receipt))


def _existing_stage(directory: Path, stage: str, binding: str) -> dict[str, Any] | None:
    path = directory / f"{stage}-complete.json"
    if not path.exists():
        return None
    record = read(path)
    if (
        record.get("binding_sha256") != binding
        or record.get("passed") is not True
        or record.get("stage") != stage
        or record.get("phase") != directory.parents[2].name
        or record.get("cell") != int(directory.parent.name.removeprefix("cell-"))
        or record.get("replicate") != int(directory.name.removeprefix("rep-"))
    ):
        raise ValueError(f"unaccepted or stale {stage} checkpoint")
    check_files(directory, record["files"])
    return cast(dict[str, Any], record)


def _history_worker(task: tuple[str, str, int, int, str, str]) -> dict[str, Any]:
    root_raw, phase, cell, replicate, stage, binding = task
    root = Path(root_raw)
    directory = root / phase / "evaluation" / f"cell-{cell:02d}" / f"rep-{replicate:03d}"
    directory.mkdir(parents=True, exist_ok=True)
    saved = _existing_stage(directory, stage, binding)
    if saved is not None:
        return saved
    started = time.perf_counter()
    timings: dict[str, float] = {}
    seed_root = evaluation.MECHANICAL_ROOT if phase == "benchmark" else evaluation.EVALUATION_ROOT
    if stage == "main":
        if not (directory / "inputs-complete.json").exists():
            component_started = time.perf_counter()
            observations, evaluator = evaluation.generate_history(
                _CONTEXT.public,
                cell=cell,
                replicate=replicate,
                root=seed_root,
            )
            timings["generation"] = time.perf_counter() - component_started
            save_arrays(
                directory / "observations.npz", {key: observations[key] for key in OBSERVATION_KEYS}
            )
            save_arrays(
                directory / "evaluator.npz", {key: evaluator[key] for key in EVALUATOR_KEYS}
            )
            metadata = {
                "schema": "goal062-history-v1",
                "history_index": cell * 500 + replicate,
                "cell_index": cell,
                "cell_label": evaluation.CELLS[cell].label,
                "replicate": replicate,
                "truth": evaluator["truth"],
                "seeds": evaluator["seeds"],
            }
            immutable_json(directory / "evaluator.json", metadata)
            immutable_json(
                directory / "inputs-complete.json",
                {
                    "binding_sha256": binding,
                    "files": hashes(
                        directory, ["observations.npz", "evaluator.npz", "evaluator.json"]
                    ),
                },
            )
    else:
        if _existing_stage(directory, "main", binding) is None:
            raise ValueError("main fits must be persisted and audited first")
        if (
            stage in {"holdout", "diagnostics"}
            and _existing_stage(directory, "decision", binding) is None
        ):
            raise ValueError("declarations must be persisted and audited first")
    inputs = read(directory / "inputs-complete.json")
    if inputs["binding_sha256"] != binding:
        raise ValueError("history input source binding changed")
    check_files(directory, inputs["files"])
    metadata = read(directory / "evaluator.json")
    if (
        metadata["cell_index"] != cell
        or metadata["replicate"] != replicate
        or metadata["seeds"]["root"] != seed_root
    ):
        raise ValueError("persisted input belongs to a different evaluation address")
    with np.load(directory / "observations.npz", allow_pickle=False) as blob:
        observations = {key: blob[key] for key in blob.files}
    with np.load(directory / "evaluator.npz", allow_pickle=False) as blob:
        arrays = {**observations, **{key: blob[key] for key in blob.files}}
    data = evaluation.make_observation_data(_CONTEXT.public, _CONTEXT.bank, observations)
    artifacts = ["inputs-complete.json", "observations.npz", "evaluator.npz", "evaluator.json"]
    if stage == "main":
        component_started = time.perf_counter()
        input_audit = audit.audit_history_inputs(metadata, arrays, _RESOURCES)
        timings["generator_audit"] = time.perf_counter() - component_started
        immutable_json(directory / "inputs-audit.json", input_audit)
        _accepted(input_audit)
        if not (directory / "main.json").exists():
            component_started = time.perf_counter()
            evaluation.fit_main(
                _CONTEXT.public,
                _CONTEXT.bank,
                observations,
                cell=cell,
                replicate=replicate,
                output=directory / "main.json",
            )
            timings["main_fit"] = time.perf_counter() - component_started
        main = read(directory / "main.json")
        component_started = time.perf_counter()
        main_audit = audit.audit_history_main(metadata, arrays, main, _RESOURCES)
        timings["main_direct_audit"] = time.perf_counter() - component_started
        immutable_json(directory / "main-audit.json", main_audit)
        _accepted(main_audit)
        component_started = time.perf_counter()
        pre = evaluation.pre_surface(data.training)
        timings["observed_screen"] = time.perf_counter() - component_started
        save_arrays(directory / "pre.npz", {"surface": pre})
        artifacts += ["inputs-audit.json", "main.json", "main-audit.json", "pre.npz"]
    else:
        main = read(directory / "main.json")
        main_before = references.sha256(directory / "main.json")
        artifacts += ["main.json", "main-complete.json"]
        existing_result = (
            read(directory / f"{stage}.json") if (directory / f"{stage}.json").exists() else None
        )
        component_started = time.perf_counter()
        if stage == "decision":
            if _CACHE is None or _CACHE_AUDIT is None:
                raise ValueError("audited complete reference cache required")
            with np.load(directory / "pre.npz", allow_pickle=False) as blob:
                pre = blob["surface"]
            observed = main["observed_effect_statistic"]
            result = (
                existing_result
                if existing_result is not None
                else evaluation.decide_cached(
                    [f"history-{cell * 500 + replicate:04d}"],
                    pre[None, :],
                    [float(observed) if observed is not None else float("nan")],
                    _CACHE["screen"] if _CACHE["screen_usable"].all() else None,
                    _CACHE["effect"],
                    _CACHE["valid"],
                    computation_complete=True,
                )
            )
            timings["cached_decision"] = time.perf_counter() - component_started
            component_started = time.perf_counter()
            checked = audit.audit_history_screen_decision(
                metadata,
                arrays,
                pre,
                result,
                read(directory / "main-audit.json"),
                _CACHE_AUDIT,
                _RESOURCES,
            )
            timings["screen_and_rank_audit"] = time.perf_counter() - component_started
        elif stage == "holdout":
            result = (
                existing_result
                if existing_result is not None
                else evaluation.score_holdout(_CONTEXT.public, data.holdout, main)
            )
            timings["heldout_score"] = time.perf_counter() - component_started
            component_started = time.perf_counter()
            checked = audit.audit_history_holdout(metadata, arrays, main, result, _RESOURCES)
            timings["heldout_direct_audit"] = time.perf_counter() - component_started
        else:
            result = (
                existing_result
                if existing_result is not None
                else evaluation.diagnose_main(data.training, main)
            )
            timings["profiles_and_lattice"] = time.perf_counter() - component_started
            component_started = time.perf_counter()
            checked = audit.audit_history_diagnostics(metadata, arrays, main, result, _RESOURCES)
            timings["diagnostics_direct_audit"] = time.perf_counter() - component_started
        immutable_json(directory / f"{stage}.json", result)
        immutable_json(directory / f"{stage}-audit.json", checked)
        _accepted(checked)
        if references.sha256(directory / "main.json") != main_before:
            raise ValueError("main fits changed during a later phase")
        artifacts += [f"{stage}.json", f"{stage}-audit.json"]
    receipt = {
        "schema": "goal062-stage-complete-v1",
        "binding_sha256": binding,
        "phase": phase,
        "cell": cell,
        "replicate": replicate,
        "stage": stage,
        "elapsed_seconds": time.perf_counter() - started,
        "component_seconds": timings,
        "path": str(directory),
        "passed": True,
        "files": hashes(directory, artifacts),
    }
    immutable_json(directory / f"{stage}-complete.json", receipt)
    return receipt


def _pool(
    tasks: list[Any],
    function: Any,
    workers: int,
    initializer: Any = None,
    initargs: tuple[Any, ...] = (),
) -> list[Any]:
    results = []
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=mp.get_context("spawn"),
        initializer=initializer,
        initargs=initargs,
    ) as pool:
        futures = [pool.submit(function, task) for task in tasks]
        try:
            for future in as_completed(futures):
                results.append(future.result())
                if len(results) % 25 == 0:
                    print(
                        json.dumps({"completed": len(results), "required": len(tasks)}), flush=True
                    )
        except BaseException:
            # Production is locked to Python 3.14; local type stubs may be older.
            pool.terminate_workers()  # type: ignore[attr-defined]
            raise
    return results


def run_history_stage(
    root: Path,
    phase: str,
    cases: list[tuple[int, int]],
    stage: str,
    workers: int,
    reference_cache_path: Path | None = None,
) -> list[dict[str, Any]]:
    if phase not in {"benchmark", "production"} or stage not in STAGES:
        raise ValueError("invalid campaign phase or stage")
    if not 1 <= workers <= 51 or len(set(cases)) != len(cases):
        raise ValueError("invalid workers or duplicated cases")
    for cell, replicate in cases:
        if cell not in range(10) or replicate not in range(500):
            raise ValueError("unregistered evaluation address")
    binding = references.sha256(root / "source-manifest.json")
    manifest = read(root / "source-manifest.json")
    if phase == "production":
        require_production_approval(root)
        cache_record = read(root / "reference-cache.json")
        if (
            cache_record.get("scope") != "production-complete-765"
            or cache_record.get("binding_sha256") != binding
        ):
            raise ValueError("all 765 reference tables must finish before evaluation")
        if stage in {"holdout", "diagnostics"}:
            frozen = read(root / "production/declarations-complete.json")
            if frozen.get("binding_sha256") != binding or frozen.get("histories") != 5000:
                raise ValueError("all 5000 declarations must be locked first")
            check_files(root / "production", frozen["files"])
    if reference_cache_path is not None:
        record = read(reference_cache_path.with_suffix(".json"))
        scope = "mechanical-synthetic-only" if phase == "benchmark" else "production-complete-765"
        if record.get("scope") != scope or record.get("binding_sha256") != binding:
            raise ValueError("reference cache scope or source binding changed")
    tasks = [(str(root), phase, cell, replicate, stage, binding) for cell, replicate in cases]
    results = _pool(
        tasks,
        _history_worker,
        workers,
        _initialize,
        (
            manifest["qualified_package"],
            str(reference_cache_path) if reference_cache_path else None,
        ),
    )
    return sorted(results, key=lambda row: (row["cell"], row["replicate"]))


def _reference_worker(task: tuple[str, str, int, str, str]) -> dict[str, Any]:
    package, directory, node, binding, destination = task
    path = Path(destination)
    if path.exists():
        row = read(path)
        _accepted(row)
        if row["audit_binding"]["binding_sha256"] != binding or row[
            "database_sha256"
        ] != references.sha256(Path(directory) / f"node-{node:04d}.sqlite"):
            raise ValueError("reference audit binding changed")
        return {"node": node, "table_usable": row["table_usable"]}
    row = reference_audit.audit_effect_node(Path(package), Path(directory), node, binding=binding)
    immutable_json(path, row)
    _accepted(row)
    return {"node": node, "table_usable": row["table_usable"]}


def prepare_reference_cache(root: Path, workers: int) -> Path:
    require_production_approval(root)
    manifest = read(root / "source-manifest.json")
    binding = references.sha256(root / "source-manifest.json")
    old_binding = manifest["original_binding"]
    prior = Path(manifest["prior_reference_root"])
    package = Path(manifest["qualified_package"])
    old_effect = prior / "analysis/effect/references"
    new_effect = root / "references/effect"
    nodes = read(prior / "analysis/effect/effect.json")["required_effect_nodes"]
    if len(nodes) != 299 or len(set(nodes)) != 299:
        raise ValueError("accepted prior table set changed")
    missing = sorted(set(range(765)) - set(nodes))
    cache_path = root / "reference-cache.npz"
    receipt_path = cache_path.with_suffix(".json")
    if receipt_path.exists():
        receipt = read(receipt_path)
        if (
            receipt.get("binding_sha256") != binding
            or receipt.get("scope") != "production-complete-765"
        ):
            raise ValueError("reference cache binding changed")
        check_files(root, receipt["files"])
        if references.sha256(cache_path) != receipt["npz_sha256"]:
            raise ValueError("reference cache checksum changed")
        return cache_path
    references.run_nodes("effect", package, new_effect, missing, binding=binding, workers=workers)
    tasks = [
        (
            str(package),
            str(new_effect),
            node,
            binding,
            str(root / "references/audits" / f"node-{node:04d}.json"),
        )
        for node in missing
    ]
    _pool(tasks, _reference_worker, workers)
    screen_directory = prior / "analysis/screen/references"
    screen = references.load_screen_table(screen_directory, binding=old_binding)
    effect = np.empty((765, 999))
    effect_audit = np.empty((765, 999))
    screen_direct = np.empty((99, 765))
    valid = np.zeros(765, dtype=bool)
    screen_usable = np.zeros(765, dtype=bool)
    node_bindings = []
    files = []
    for node in range(765):
        screen_audit = read(prior / "analysis/audits/screen" / f"node-{node:04d}.json")
        _accepted(screen_audit)
        screen_usable[node] = not screen_audit["abstain"]
        audited_screen = np.asarray(screen_audit["contrasts"], dtype=float)
        screen_direct[:, node] = audited_screen
        if not np.allclose(screen[:, node], audited_screen, atol=1e-8, rtol=0, equal_nan=True):
            raise ValueError("producer and independent screen tables differ")
        old = node in nodes
        directory = old_effect if old else new_effect
        node_binding = old_binding if old else binding
        audit_path = (
            prior / "analysis/audits/effect" if old else root / "references/audits"
        ) / f"node-{node:04d}.json"
        checked = read(audit_path)
        _accepted(checked)
        batch = references.load_effect_batch(
            directory / f"node-{node:04d}.sqlite",
            metadata={
                "schema": references.SCHEMA,
                "kind": "effect",
                "binding_sha256": node_binding,
                "node": node,
                "root": calibration.ROOT_SEED,
                "namespace": 59,
                "domain": 6,
                "references": 999,
            },
        )
        produced = batch.statistics()
        effect[node] = produced
        effect_audit[node] = np.asarray(checked["statistics"], dtype=float)
        valid[node] = checked["table_usable"]
        if valid[node] != bool(np.isfinite(produced).all()):
            raise ValueError("producer and independent effect usability differ")
        if valid[node] and not np.allclose(produced, effect_audit[node], atol=1e-6, rtol=0):
            raise ValueError("producer and independent effect statistics differ")
        node_bindings.append(
            {
                "node": node,
                "source_binding": node_binding,
                "audit_sha256": references.sha256(audit_path),
                "database_sha256": checked["database_sha256"],
            }
        )
        if not old:
            files += [
                str((directory / f"node-{node:04d}.sqlite").relative_to(root)),
                str((directory / f"node-{node:04d}-complete.json").relative_to(root)),
                str(audit_path.relative_to(root)),
            ]
    save_arrays(
        cache_path,
        {
            "screen": screen,
            "effect": effect,
            "valid": valid,
            "screen_usable": screen_usable,
            "screen_audit": screen_direct,
            "effect_audit": effect_audit,
        },
    )
    immutable_json(
        receipt_path,
        {
            "schema": "goal062-reference-cache-v1",
            "binding_sha256": binding,
            "scope": "production-complete-765",
            "npz_sha256": references.sha256(cache_path),
            "original_tables": 299,
            "new_tables": 466,
            "nodes": node_bindings,
            "files": hashes(root, files),
            "original_completion_sha256": references.sha256(root / "original-completion.json"),
        },
    )
    return cache_path


def production(root: Path, workers: int) -> dict[str, Any]:
    if os.environ.get("GOAL062_SUPERVISOR_PID") != str(os.getppid()):
        raise ValueError("production must run under its memory and wall-time supervisor")
    qualified = require_production_approval(root)
    if workers > qualified["qualified_workers"]:
        raise ValueError("workers exceed measured qualification")
    _, binding = verify_custody(root)
    freeze_seed_ledgers(root, binding)
    cache = prepare_reference_cache(root, workers)
    cases = [(cell, replicate) for cell in range(10) for replicate in range(500)]
    phase_receipts: dict[str, list[dict[str, Any]]] = {}
    for stage in ("main", "decision"):
        phase_receipts[stage] = run_history_stage(root, "production", cases, stage, workers, cache)
    phase = root / "production"
    declarations = [
        str((Path(row["path"]) / "decision-complete.json").relative_to(phase))
        for row in phase_receipts["decision"]
    ]
    immutable_json(
        phase / "declarations-complete.json",
        {
            "binding_sha256": binding,
            "histories": 5000,
            "files": hashes(phase, declarations),
            "main_fit_count": 20000,
            "reference_cache_sha256": references.sha256(cache),
        },
    )
    phase_receipts["holdout"] = run_history_stage(
        root, "production", cases, "holdout", workers, cache
    )
    diagnostics, selection = select_diagnostics(phase_receipts["main"])
    immutable_json(phase / "diagnostic-selection.json", selection)
    phase_receipts["diagnostics"] = run_history_stage(
        root, "production", diagnostics, "diagnostics", workers, cache
    )
    return synthesize(root, binding, phase_receipts)


def freeze_seed_ledgers(root: Path, binding: str) -> dict[str, Any]:
    """Freeze both registered stream sets before any production generator call."""
    from summarize_final_procedure_evaluation import bootstrap_ledger

    ledger = evaluation.seed_ledger()
    ledger_audit = evaluation.validate_seed_ledger(ledger)
    if ledger_audit["passed"] is not True:
        raise ValueError("evaluation seed ledger is not unique or registered")
    bootstrap = bootstrap_ledger()
    if len(bootstrap) != 20000 or {row["seed"] for row in bootstrap} & {
        row["seed"] for row in ledger
    }:
        raise ValueError("bootstrap ledger has the wrong count or overlaps evaluation seeds")
    immutable_json(root / "production/seed-ledger.json", ledger)
    immutable_json(root / "production/bootstrap-seed-ledger.json", bootstrap)
    result = {
        "binding_sha256": binding,
        "passed": True,
        "bootstrap_addresses": 20000,
        "evaluation_addresses": 27000,
        "all_47000_seeds_unique": True,
        "bootstrap_domain": 2,
        "evaluation_domain": 1,
        "evaluation_validation": ledger_audit,
        "files": hashes(root / "production", ["seed-ledger.json", "bootstrap-seed-ledger.json"]),
    }
    immutable_json(root / "production/seed-ledger-audit.json", result)
    return result


def select_diagnostics(
    main_receipts: list[dict[str, Any]],
) -> tuple[list[tuple[int, int]], dict[str, Any]]:
    """Fixed fifty plus the first example of each registered failure per cell."""
    selected = {(cell, replicate) for cell in range(10) for replicate in range(5)}
    examples: dict[str, tuple[int, int]] = {}
    for receipt in sorted(main_receipts, key=lambda row: (row["cell"], row["replicate"])):
        row = read(Path(receipt["path"]) / "main.json")
        failures = {
            "nonfinite_score": any(fit["raw_logjoint"] is None for fit in row["fits"].values()),
            "nonconvergence": not all(row["main_statuses_converged"].values()),
            "nesting_violation": "failed" in row["nesting_status"].values(),
            "score_replay_discrepancy": not row["all_main_replays_passed"],
        }
        for name, failed in failures.items():
            if failed:
                key = f"cell-{receipt['cell']:02d}/{name}"
                examples.setdefault(key, (receipt["cell"], receipt["replicate"]))
    selected.update(examples.values())
    return sorted(selected), {
        "fixed_histories": 50,
        "selected_examples": examples,
        "total_histories": len(selected),
        "selected_not_operating_replicates": True,
    }


def synthesize(root: Path, binding: str, stages: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    from summarize_final_procedure_evaluation import summarize_rows, write_summary

    rows = []
    for item in stages["main"]:
        directory = Path(item["path"])
        metadata, main = read(directory / "evaluator.json"), read(directory / "main.json")
        main_audit = read(directory / "main-audit.json")
        decision = read(directory / "decision.json")
        screen = decision["screens"][0]
        selected = dict(decision["decisions"][0])
        if selected["status"].startswith("abstain"):
            if screen["status"] == "missing_screen_table":
                selected["abstention_reason"] = "shared_table"
            elif screen["status"] == "no_fit":
                selected["abstention_reason"] = "observed_screen"
            elif not main["observed_adjusted_validity"]["valid"]:
                selected["abstention_reason"] = "observed_fit"
            elif selected.get("reason") == "an effect reference fit failed":
                selected["abstention_reason"] = "shared_table"
        candidates = screen["candidate_indices"]
        truth = metadata["truth"]
        true_node = None
        if truth["background"] == "exact":
            for node, nuisance in enumerate(calibration.NUISANCE_GRID):
                beta, mu, sd = nuisance.beta, nuisance.mu, nuisance.detection_sd
                if (beta, mu, sd) == (
                    truth["generating_beta"],
                    truth["mean_hazard"],
                    truth["detection_sd"],
                ):
                    true_node = node
                    break
            if true_node is None:
                raise ValueError("registered exact truth missing from nuisance grid")
        rows.append(
            {
                **truth,
                "cell_index": metadata["cell_index"],
                "cell_label": metadata["cell_label"],
                "replicate": metadata["replicate"],
                "fits": main["fits"],
                "decision": selected,
                "C_size": len(candidates),
                "p_BB": selected["p_value"],
                "true_node_retained": true_node in candidates if true_node is not None else None,
                "free_h_valid": main_audit["effect_recovery_available"],
                **{
                    key: main[key]
                    for key in (
                        "main_statuses_converged",
                        "nesting_status",
                        "nesting_gaps",
                        "compressed_score_replay",
                        "all_main_replays_passed",
                        "observed_adjusted_validity",
                    )
                },
                "holdout": read(directory / "holdout.json"),
                "audit_status": "passed",
            }
        )
    output = root / "production/summary"
    output.mkdir(parents=True, exist_ok=True)
    immutable_json(output / "histories.json", rows)
    result = summarize_rows(rows)
    publish_summary(result, output, write_summary)
    files = [str(path.relative_to(root)) for path in (root / "production").rglob("*-complete.json")]
    files += [str(path.relative_to(root)) for path in output.iterdir() if path.is_file()]
    receipt = {
        "schema": "goal062-computation-complete-v1",
        "binding_sha256": binding,
        "passed": True,
        "histories": 5000,
        "main_fits": 20000,
        "diagnostic_histories": len(stages["diagnostics"]),
        "files": hashes(root, files),
        "scientific_review_pending": True,
    }
    immutable_json(root / "computation-complete.json", receipt)
    return receipt


def publish_summary(result: dict[str, Any], output: Path, writer: Any) -> None:
    """Publish the reporting adapter's new directory without overwriting evidence."""
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".summary-", dir=output.parent) as temporary:
        staged = Path(temporary) / "output"
        writer(result, staged)
        for path in sorted(staged.iterdir()):
            target = output / path.name
            if target.exists():
                if references.sha256(target) != references.sha256(path):
                    raise ValueError("summary output differs from persisted evidence")
            else:
                shutil.copyfile(path, target.with_suffix(target.suffix + ".tmp"))
                target.with_suffix(target.suffix + ".tmp").replace(target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("benchmark", "run"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=51)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.phase == "benchmark":
        from qualify_final_procedure_evaluation import qualify

        result = qualify(root, args.workers)
    else:
        result = production(root, args.workers)
    print(json.dumps({key: value for key, value in result.items() if key != "files"}), flush=True)
    if result.get("passed") is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
