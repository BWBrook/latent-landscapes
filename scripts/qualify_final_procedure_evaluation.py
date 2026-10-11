#!/usr/bin/env python3
"""Non-production qualification for the Goal 062 evaluation procedure.

The qualification uses only the mechanical root and already released public
fixtures.  It deliberately separates numerical qualification from production
runtime approval: a kernel-only runtime change can pass the numerical checks,
but the resulting receipt still blocks production until it is explicitly
reviewed by the supervisor's approval gate.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import multiprocessing as mp
import os
import platform
import re
import resource
import subprocess
import sys
import time
from collections.abc import Iterator, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import scipy  # type: ignore[import-untyped]

SCHEMA = "goal062-final-procedure-qualification-v1"
MECHANICAL_ROOT = 987654321
REGISTERED_REFERENCE_ROOT = 2026100404
EFFECT_REUSE_NODES = (1, 96, 191, 288, 381, 462, 548, 647, 762)
SCREEN_REUSE_NODES = (0, 382, 764)
MECHANICAL_EFFECT_NODES = (0, 382, 764)
MAIN_CASES = tuple((cell, 0) for cell in range(10))
DIAGNOSTIC_CASES = ((1, 0), (7, 0))
MECHANICAL_TEST_FILES = (
    "tests/test_final_procedure_evaluation.py",
    "tests/test_final_procedure_evaluation_audit.py",
    "tests/test_final_procedure_evaluation_qualification.py",
    "tests/test_final_procedure_evaluation_runner.py",
    "tests/test_final_procedure_evaluation_synthesis.py",
)
CORE_RUNTIME_KEYS = (
    "bit_generator",
    "numpy_version",
    "platform",
    "python_version",
    "scipy_version",
    "sys_version",
)
THREAD_VARIABLES = (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)
RSS_CAP_BYTES = 64 * 1024**3
WALL_CAP_SECONDS = 72 * 3600
QUALIFICATION_CAP_SECONDS = 3 * 3600


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items())}
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("qualification receipts cannot contain nonfinite values")
        return value
    return str(value)


def write_new(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    if path.exists() or temporary.exists():
        raise FileExistsError(f"refusing to replace qualification evidence: {path}")
    temporary.write_text(
        json.dumps(_jsonable(dict(value)), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def event(event_name: str, *, stage: str, **fields: Any) -> None:
    """Emit compact progress without serializing scientific payloads."""

    print(
        json.dumps(
            {
                "utc": datetime.now(UTC).isoformat(),
                "event": event_name,
                "stage": stage,
                **fields,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
        flush=True,
    )


@contextmanager
def stage_events(stage: str) -> Iterator[None]:
    """Bracket one qualification stage with compact, failure-aware telemetry."""

    started = time.monotonic()
    event("stage_start", stage=stage)
    try:
        yield
    except Exception as error:
        event(
            "stage_complete",
            stage=stage,
            passed=False,
            elapsed_seconds=time.monotonic() - started,
            error_type=type(error).__name__,
        )
        raise
    else:
        event(
            "stage_complete",
            stage=stage,
            passed=True,
            elapsed_seconds=time.monotonic() - started,
        )


def _module_hash(module_name: str) -> dict[str, Any]:
    module = importlib.import_module(module_name)
    module_file = getattr(module, "__file__", None)
    if not isinstance(module_file, str):
        raise RuntimeError(f"numeric extension has no hashable file: {module_name}")
    path = Path(module_file).resolve()
    if not path.is_file():
        raise RuntimeError(f"numeric extension has no hashable file: {module_name}")
    return {"path": str(path), "sha256": sha256_file(path)}


def _config(module: Any) -> Any:
    try:
        return _jsonable(module.__config__.show(mode="dicts"))
    except TypeError:
        # The frozen versions support ``mode=dicts``.  Keep a transparent
        # sentinel for unit-test or developer environments with older NumPy.
        return {"available": False, "reason": "dict configuration API unavailable"}


def runtime_record() -> dict[str, Any]:
    """Return the full numerical runtime identity used by qualification.

    The six top-level core fields intentionally retain the exact schema of the
    Goal 061 runtime receipt.  Added binary/configuration fields are evidence
    for this run; they are not represented as matches to the old binaries,
    whose hashes were never recorded.
    """

    executable = Path(sys.executable).resolve()
    uname = platform.uname()
    extensions = {
        name: _module_hash(name)
        for name in (
            "numpy._core._multiarray_umath",
            "numpy.linalg._umath_linalg",
            "numpy.random._pcg64",
            "scipy.optimize._lbfgsb",
            "scipy.special._ufuncs",
        )
    }
    return {
        "bit_generator": type(np.random.default_rng(0).bit_generator).__name__,
        "numpy_version": np.__version__,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "scipy_version": scipy.__version__,
        "sys_version": sys.version,
        "platform_components": {
            "system": uname.system,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "libc": list(platform.libc_ver()),
        },
        "thread_environment": {name: os.environ.get(name) for name in THREAD_VARIABLES},
        "numerical_configuration": {"numpy": _config(np), "scipy": _config(scipy)},
        "python_executable": {"path": str(executable), "sha256": sha256_file(executable)},
        "numeric_extensions": extensions,
        "baseline_binary_hashes_available": False,
        "binary_identity_claim": (
            "current binaries hashed; prior receipt has no executable or extension hashes, "
            "so binary identity with Goal 061 is not established"
        ),
    }


_PLATFORM_PATTERN = re.compile(
    r"^(?P<system>[^-]+)-(?P<release>.+)-(?P<machine>[^-]+)-with-(?P<libc>.+)$"
)


def _platform_parts(value: str) -> dict[str, str] | None:
    match = _PLATFORM_PATTERN.match(value)
    return None if match is None else match.groupdict()


def compare_runtime(observed: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, Any]:
    """Compare the frozen six-field runtime while isolating kernel-only drift."""

    missing = [key for key in CORE_RUNTIME_KEYS if key not in observed or key not in baseline]
    exact_fields = {
        key: observed.get(key) == baseline.get(key)
        for key in CORE_RUNTIME_KEYS
        if key != "platform"
    }
    before = _platform_parts(str(baseline.get("platform", "")))
    after = _platform_parts(str(observed.get("platform", "")))
    platform_exact = observed.get("platform") == baseline.get("platform")
    kernel_only = bool(
        not platform_exact
        and before is not None
        and after is not None
        and before["system"] == after["system"]
        and before["machine"] == after["machine"]
        and before["libc"] == after["libc"]
        and before["release"] != after["release"]
    )
    platform_compatible = platform_exact or kernel_only
    threads = observed.get("thread_environment")
    thread_limited = isinstance(threads, Mapping) and all(
        threads.get(name) == "1" for name in THREAD_VARIABLES
    )
    version_compatible = not missing and all(exact_fields.values())
    numerical_compatible = version_compatible and platform_compatible and thread_limited
    runtime_changed = any(observed.get(key) != baseline.get(key) for key in CORE_RUNTIME_KEYS)
    return {
        "passed": numerical_compatible,
        "missing_core_fields": missing,
        "exact_nonplatform_core_fields": exact_fields,
        "platform_exact": platform_exact,
        "kernel_only_difference": kernel_only,
        "platform_compatible": platform_compatible,
        "library_threads_one": thread_limited,
        "runtime_changed": runtime_changed,
        "production_runtime_review_required": runtime_changed,
        "baseline_binary_hashes_available": False,
        "prior_binary_identity_verified": False,
        "baseline_platform": baseline.get("platform"),
        "observed_platform": observed.get("platform"),
    }


def qualify_mechanical_tests(
    root: Path, manifest: Mapping[str, Any], binding: str
) -> dict[str, Any]:
    """Run the frozen fault, resume, audit, and synthesis tests in a subprocess."""

    source = root / "source"
    source_hashes = manifest.get("source_hashes")
    if not isinstance(source_hashes, Mapping):
        raise ValueError("source manifest has no source hashes")
    test_hashes: dict[str, str] = {}
    for relative in MECHANICAL_TEST_FILES:
        expected = source_hashes.get(relative)
        path = source / relative
        if not isinstance(expected, str) or sha256_file(path) != expected:
            raise ValueError(f"frozen mechanical test changed: {relative}")
        test_hashes[relative] = expected

    log_path = root / "benchmark/mechanical-tests.log"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        *MECHANICAL_TEST_FILES,
        "-p",
        "no:cacheprovider",
    ]
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.monotonic()
    with log_path.open("x", encoding="utf-8") as log:
        completed = subprocess.run(
            command,
            cwd=source,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return {
        "passed": completed.returncode == 0,
        "exit_code": completed.returncode,
        "command": command,
        "cwd": str(source),
        "python_executable": str(Path(sys.executable).resolve()),
        "python_executable_sha256": sha256_file(Path(sys.executable).resolve()),
        "pythonpath": environment.get("PYTHONPATH"),
        "source_manifest_sha256": binding,
        "test_source_hashes": test_hashes,
        "test_source_set_sha256": canonical_sha256(test_hashes),
        "log": str(log_path.relative_to(root)),
        "log_sha256": sha256_file(log_path),
        "log_bytes": log_path.stat().st_size,
        "elapsed_seconds": time.monotonic() - started,
    }


def synthetic_reference_cache(path: Path, *, binding_sha256: str) -> dict[str, Any]:
    """Create a conspicuously synthetic, full-shaped cache for rank mechanics."""

    if len(binding_sha256) != 64:
        raise ValueError("binding_sha256 must be a SHA-256 hex digest")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.with_suffix(".json").exists():
        raise FileExistsError("refusing to replace the mechanical synthetic cache")
    # Repeated steps intentionally exercise inclusive ties.  Values vary by
    # node, but carry no scientific or production interpretation.
    screen_base = np.repeat(np.arange(11, dtype=np.float64), 9)[:99]
    screen = np.broadcast_to(screen_base[:, None], (99, 765)).copy()
    effect_base = np.repeat(np.arange(333, dtype=np.float64), 3)[:999] / 100.0
    effect = effect_base[None, :] + (np.arange(765, dtype=np.float64)[:, None] % 7) / 1000.0
    valid = np.ones(765, dtype=bool)
    screen_usable = np.ones(765, dtype=bool)
    np.savez_compressed(
        path,
        screen=screen,
        effect=effect,
        valid=valid,
        screen_usable=screen_usable,
    )
    metadata = {
        "binding_sha256": binding_sha256,
        "scope": "mechanical-synthetic-only",
        "npz_sha256": sha256_file(path),
    }
    write_new(path.with_suffix(".json"), metadata)
    return metadata


def _compact_audit(row: Mapping[str, Any], values_key: str) -> dict[str, Any]:
    values = np.asarray(row.get(values_key), dtype=np.float64)
    return {
        "passed": row.get("passed") is True,
        "status": row.get("status"),
        "numerical_status": row.get("numerical_status"),
        "release_blocked": row.get("release_blocked"),
        "node": row.get("node"),
        "completed": row.get("completed", row.get("references")),
        "generator_replays": row.get("generator_replays"),
        "maximum_score_abs_error": row.get("maximum_score_abs_error"),
        "values_shape": list(values.shape),
        "values_sha256": hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest(),
        "audit_binding": row.get("audit_binding"),
    }


def _reaudit_reused_reference_task(task: tuple[str, str, str, str, int, str]) -> dict[str, Any]:
    package_raw, directory_raw, saved_raw, kind, node, old_binding = task
    audit = importlib.import_module("audit_capstone_training")
    package = Path(package_raw)
    directory = Path(directory_raw)
    saved_path = Path(saved_raw)
    values_key = "statistics" if kind == "effect" else "contrasts"
    callback = audit.audit_effect_node if kind == "effect" else audit.audit_screen_node
    fresh = callback(
        package,
        directory,
        node,
        binding=old_binding,
        root=REGISTERED_REFERENCE_ROOT,
        references=999 if kind == "effect" else 99,
    )
    saved = json.loads(saved_path.read_text(encoding="utf-8"))
    left = np.asarray(fresh[values_key], dtype=np.float64)
    right = np.asarray(saved[values_key], dtype=np.float64)
    maximum_difference = (
        float(np.max(np.abs(left - right))) if left.shape == right.shape else None
    )
    compact = _compact_audit(fresh, values_key)
    compact.update(
        kind=kind,
        accepted_audit_sha256=sha256_file(saved_path),
        accepted_values_sha256=hashlib.sha256(
            np.ascontiguousarray(right).tobytes()
        ).hexdigest(),
        accepted_comparison_max_abs_difference=maximum_difference,
        accepted_comparison_passed=bool(
            maximum_difference is not None and maximum_difference <= 1e-10
        ),
    )
    return compact


def qualify_reused_references(
    root: Path, manifest: Mapping[str, Any], binding: str, *, workers: int
) -> dict[str, Any]:
    """Re-audit selected inherited tables in parallel and compare accepted results."""

    del root, binding  # inherited tables retain the Goal 061 binding
    package = Path(str(manifest["qualified_package"]))
    prior = Path(str(manifest["prior_reference_root"]))
    old_binding = str(manifest["original_binding"])
    analysis = prior / "analysis"
    tasks = [
        (
            str(package),
            str(analysis / f"{kind}/references"),
            str(analysis / "audits" / kind / f"node-{node:04d}.json"),
            kind,
            node,
            old_binding,
        )
        for kind, nodes in (("effect", EFFECT_REUSE_NODES), ("screen", SCREEN_REUSE_NODES))
        for node in nodes
    ]
    process_count = min(workers, len(tasks))
    rows: list[dict[str, Any]] = []
    with ProcessPoolExecutor(
        max_workers=process_count, mp_context=mp.get_context("spawn")
    ) as pool:
        futures = [pool.submit(_reaudit_reused_reference_task, task) for task in tasks]
        for future in as_completed(futures):
            rows.append(future.result())
            event(
                "stage_progress",
                stage="reused_reference_audits",
                completed=len(rows),
                required=len(tasks),
            )
    # Sort explicitly so completion timing can never alter the persisted receipt.
    node_order = {
        (kind, node): index
        for index, (kind, node) in enumerate(
            [("effect", node) for node in EFFECT_REUSE_NODES]
            + [("screen", node) for node in SCREEN_REUSE_NODES]
        )
    }
    rows.sort(key=lambda row: node_order[(str(row["kind"]), int(row["node"]))])
    passed = all(
        row["passed"]
        and row["release_blocked"] is False
        and row["accepted_comparison_passed"]
        and (
            row["completed"] == 999 and row["generator_replays"] >= 3
            if row["kind"] == "effect"
            else row["completed"] == 99 and row["generator_replays"] == 99
        )
        for row in rows
    )
    return {
        "passed": passed,
        "prior_reference_root": str(prior),
        "old_binding_sha256": old_binding,
        "effect_nodes": list(EFFECT_REUSE_NODES),
        "screen_nodes": list(SCREEN_REUSE_NODES),
        "audits": rows,
    }


def qualify_mechanical_effect_references(
    root: Path, manifest: Mapping[str, Any], binding: str
) -> dict[str, Any]:
    """Generate and independently audit 3 x 3 mechanical effect references."""

    references = importlib.import_module("latent_landscapes.capstone_references")
    audit = importlib.import_module("audit_capstone_training")
    package = Path(str(manifest["qualified_package"]))
    context = references.load_context(package)
    directory = root / "benchmark/reference/effect"
    rows = []
    for node in MECHANICAL_EFFECT_NODES:
        started = time.monotonic()
        producer = references.run_effect_node(
            context,
            directory,
            node,
            binding=binding,
            root=MECHANICAL_ROOT,
            references=3,
        )
        independent = audit.audit_effect_node(
            package,
            directory,
            node,
            binding=binding,
            root=MECHANICAL_ROOT,
            references=3,
        )
        compact = _compact_audit(independent, "statistics")
        compact.update(
            elapsed_seconds=time.monotonic() - started,
            producer_elapsed_seconds=float(producer.get("elapsed_seconds", 0.0)),
            references=3,
            database_sha256=producer.get("database_sha256"),
        )
        rows.append(compact)
    return {
        "passed": all(
            row["passed"]
            and row["release_blocked"] is False
            and row["completed"] == 3
            and row["generator_replays"] == 3
            for row in rows
        ),
        "root": MECHANICAL_ROOT,
        "nodes": list(MECHANICAL_EFFECT_NODES),
        "references_per_node": 3,
        "audits": rows,
    }


def qualify_public_refits(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Refit the eight accepted public histories on the full bank and compare."""

    references = importlib.import_module("latent_landscapes.capstone_references")
    qualification = importlib.import_module("latent_landscapes.capstone_qualification")
    fitting = importlib.import_module("latent_landscapes.preinvasion_fitting")
    package = Path(str(manifest["qualified_package"]))
    context = references.load_context(package)
    panel = package / "panel"
    result_directory = package / "panel-results/results"
    observed = qualification.load_panel_observations(context.public, panel)
    rows = []
    for history in range(8):
        stored_path = result_directory / f"history-{history:02d}-full-main.json"
        stored = json.loads(stored_path.read_text(encoding="utf-8"))
        train = qualification.make_fit_data(
            context.public, context.bank, observed, history=history, training=True
        )
        started = time.monotonic()
        paired = fitting.paired_fit(train, qualification.fit_loglikelihood)
        score_errors: dict[str, float] = {}
        parameter_errors: dict[str, float] = {}
        status_matches: dict[str, bool] = {}
        for name, fit in paired.fits.items():
            accepted = stored["fits"][name]
            score_errors[name] = abs(float(fit.raw_logjoint) - float(accepted["raw_logjoint"]))
            status_matches[name] = fit.numerical_status == accepted["numerical_status"]
            for parameter in ("h", "beta", "mu", "detection_sd"):
                parameter_errors[f"{name}.{parameter}"] = abs(
                    float(getattr(fit, parameter)) - float(accepted[parameter])
                )
        row_passed = bool(
            max(score_errors.values(), default=math.inf) <= 1e-8
            and max(parameter_errors.values(), default=math.inf) <= 1e-8
            and all(status_matches.values())
        )
        rows.append(
            {
                "history": history,
                "passed": row_passed,
                "elapsed_seconds": time.monotonic() - started,
                "accepted_main_sha256": sha256_file(stored_path),
                "maximum_score_abs_difference": max(score_errors.values(), default=None),
                "maximum_parameter_abs_difference": max(
                    parameter_errors.values(), default=None
                ),
                "status_matches": status_matches,
            }
        )
    return {
        "passed": all(row["passed"] for row in rows),
        "fixture_available": True,
        "histories_refit": len(rows),
        "score_tolerance": 1e-8,
        "parameter_tolerance": 1e-8,
        "rows": rows,
    }


def _validate_stage_receipts(
    rows: Sequence[Mapping[str, Any]], stage: str, cases: Sequence[tuple[int, int]]
) -> dict[str, Any]:
    expected = set(cases)
    observed = {(row.get("cell"), row.get("replicate")) for row in rows}
    valid = bool(
        len(rows) == len(cases)
        and observed == expected
        and all(
            row.get("stage") == stage
            and row.get("passed") is True
            and isinstance(row.get("elapsed_seconds"), (int, float))
            and math.isfinite(float(row["elapsed_seconds"]))
            and float(row["elapsed_seconds"]) >= 0
            for row in rows
        )
    )
    return {
        "passed": valid,
        "stage": stage,
        "expected_cases": len(cases),
        "observed_cases": len(rows),
        "elapsed_seconds": [float(row["elapsed_seconds"]) for row in rows],
        "receipt_paths": [str(row.get("path")) for row in rows],
    }


def project_budget(
    stage_receipts: Mapping[str, Sequence[Mapping[str, Any]]],
    reference_rows: Sequence[Mapping[str, Any]],
    *,
    workers: int,
) -> dict[str, Any]:
    """Project the fixed 5,000-history, 50-diagnostic, 465,534-ref workload."""

    if workers < 1:
        raise ValueError("workers must be positive")
    ordinary_worker_seconds = sum(
        sum(float(row["elapsed_seconds"]) for row in stage_receipts[stage]) * 500
        for stage in ("main", "decision", "holdout")
    )
    diagnostics = list(stage_receipts["diagnostics"])
    by_cell = {int(row["cell"]): float(row["elapsed_seconds"]) for row in diagnostics}
    if set(by_cell) != {1, 7}:
        raise ValueError("diagnostic benchmark must contain exact cell 1 and B100-A cell 7")
    diagnostic_worker_seconds = by_cell[1] * 30 + by_cell[7] * 20
    evaluation_hours = (ordinary_worker_seconds + diagnostic_worker_seconds) / workers / 3600
    reference_seconds = sum(float(row["producer_elapsed_seconds"]) for row in reference_rows)
    measured_reference_hours = reference_seconds / 9 * 465_534 / workers / 3600
    measured_upper_hours = 1.25 * (evaluation_hours + measured_reference_hours)
    historical_lower_hours = 36.0 + evaluation_hours
    historical_upper_hours = 40.0 + 1.25 * evaluation_hours
    conservative_upper_hours = max(measured_upper_hours, historical_upper_hours)
    return {
        "workers": workers,
        "production_histories": 5_000,
        "diagnostic_histories": 50,
        "new_effect_reference_fits": 465_534,
        "measured_evaluation_hours": evaluation_hours,
        "measured_reference_hours": measured_reference_hours,
        "measured_combined_upper_hours_with_25pct_margin": measured_upper_hours,
        "historical_reference_allowance_hours": [36.0, 40.0],
        "combined_historical_lower_hours": historical_lower_hours,
        "combined_historical_upper_hours_with_evaluation_margin": historical_upper_hours,
        "conservative_upper_hours": conservative_upper_hours,
        "wall_cap_hours": WALL_CAP_SECONDS / 3600,
        "passed": conservative_upper_hours <= WALL_CAP_SECONDS / 3600,
    }


_PROBE_PACKAGE: str | None = None
_PROBE_RELEASE: Any = None
_PROBE_TASK_BARRIER: Any = None
_PROBE_TASK_RELEASE: Any = None
_PROBE_LOADED: tuple[Any, Any] | None = None
_PROBE_WORKING: tuple[Any, ...] | None = None


def _probe_initializer(
    barrier: Any,
    release: Any,
    task_barrier: Any,
    task_release: Any,
    package: str,
) -> None:
    global _PROBE_PACKAGE, _PROBE_RELEASE, _PROBE_TASK_BARRIER, _PROBE_TASK_RELEASE
    global _PROBE_LOADED
    _PROBE_PACKAGE = package
    _PROBE_RELEASE = release
    _PROBE_TASK_BARRIER = task_barrier
    _PROBE_TASK_RELEASE = task_release
    references = importlib.import_module("latent_landscapes.capstone_references")
    audit = importlib.import_module("audit_final_procedure_evaluation")
    # Custody was exhaustively checked once before this probe.  Rehashing the
    # same 97 public files in each of 51 processes would measure redundant I/O,
    # not the resident production resources under qualification.
    producer = references.load_context(Path(package), verify=False)
    independent = audit.load_audit_resources(Path(package))
    _PROBE_LOADED = (producer, independent)
    barrier.wait(timeout=600)
    release.wait(timeout=600)


def _probe_worker(index: int) -> dict[str, Any]:
    global _PROBE_WORKING
    if (
        _PROBE_LOADED is None
        or _PROBE_PACKAGE is None
        or _PROBE_TASK_BARRIER is None
        or _PROBE_TASK_RELEASE is None
    ):
        raise RuntimeError("concurrency worker did not initialize both numerical resources")
    producer, independent = _PROBE_LOADED
    evaluation = importlib.import_module("latent_landscapes.final_procedure_evaluation")
    likelihood = importlib.import_module("latent_landscapes.preinvasion_likelihood")
    audit = importlib.import_module("audit_final_procedure_evaluation")
    raw, _evaluator = evaluation.generate_history(
        producer.public,
        cell=0,
        replicate=499,
        root=MECHANICAL_ROOT,
    )
    data = evaluation.make_observation_data(producer.public, producer.bank, raw).training
    point = {"h": 1.0, "beta": 0.0, "mu": 0.0025, "detection_sd": 0.2}
    producer_score = likelihood.point_score(
        data.observations,
        data.bank,
        point["h"],
        point["beta"],
        point["mu"],
        data.map_a,
        data.site_a,
        detection_sd=point["detection_sd"],
    )
    independent_score = audit.direct_point_score(
        independent.bank,
        independent.context,
        np.asarray(raw["prey_counts"], dtype=np.int64),
        np.asarray(raw["predator_counts"], dtype=np.int64),
        point,
    )
    score_difference = abs(
        float(producer_score.training_logjoint)
        - float(independent_score["training_logjoint"])
    )
    # Retain actual point-score working arrays until the parent samples the
    # process group.  This measures loaded resources plus representative score
    # state rather than an already released high-water estimate.
    _PROBE_WORKING = (raw, data, producer_score, independent_score)
    _PROBE_TASK_BARRIER.wait(timeout=600)
    _PROBE_TASK_RELEASE.wait(timeout=600)
    multiplier = 1 if sys.platform == "darwin" else 1024
    return {
        "task": index,
        "pid": os.getpid(),
        "producer_bank_size": int(producer.bank.bank_size),
        "audit_sites": len(independent.context.site_ids),
        "point_score_abs_difference": score_difference,
        "peak_process_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        * multiplier,
    }


def _process_group_rss(group: int) -> tuple[int, list[int]]:
    if not Path("/proc").is_dir():
        raise RuntimeError("aggregate concurrency RSS qualification requires Linux /proc")
    pages = 0
    members = []
    for entry in Path("/proc").glob("[0-9]*/stat"):
        try:
            raw = entry.read_text(encoding="utf-8")
            fields = raw[raw.rfind(")") + 2 :].split()
            if int(fields[2]) == group and fields[0] != "Z":
                pages += int(fields[21])
                members.append(int(entry.parent.name))
        except (OSError, ValueError, IndexError):
            continue
    return pages * os.sysconf("SC_PAGE_SIZE"), members


def qualify_concurrency(manifest: Mapping[str, Any], workers: int) -> dict[str, Any]:
    """Initialize both producer and auditor resources in every requested process."""

    if not 1 <= workers <= min(51, int(manifest.get("maximum_workers", 51))):
        raise ValueError("requested worker count exceeds the frozen envelope")
    context = mp.get_context("spawn")
    barrier = context.Barrier(workers + 1)
    release = context.Event()
    task_barrier = context.Barrier(workers + 1)
    task_release = context.Event()
    started = time.monotonic()
    observed_rss = 0
    observed_members: list[int] = []
    try:
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=_probe_initializer,
            initargs=(
                barrier,
                release,
                task_barrier,
                task_release,
                str(manifest["qualified_package"]),
            ),
        ) as pool:
            futures = [pool.submit(_probe_worker, index) for index in range(workers)]
            barrier.wait(timeout=600)
            for _ in range(3):
                rss, members = _process_group_rss(os.getpgrp())
                if rss >= observed_rss:
                    observed_rss, observed_members = rss, members
                time.sleep(0.25)
            release.set()
            task_barrier.wait(timeout=600)
            for _ in range(3):
                rss, members = _process_group_rss(os.getpgrp())
                if rss >= observed_rss:
                    observed_rss, observed_members = rss, members
                time.sleep(0.25)
            task_release.set()
            rows = [future.result(timeout=600) for future in futures]
    finally:
        release.set()
        task_release.set()
    distinct = len({int(row["pid"]) for row in rows})
    headroom_rss = math.ceil(observed_rss * 1.25)
    passed = bool(
        distinct == workers
        and all(row["producer_bank_size"] == 131_072 for row in rows)
        and all(row["audit_sites"] == 160 for row in rows)
        and all(row["point_score_abs_difference"] <= 1e-8 for row in rows)
        and headroom_rss <= int(manifest.get("rss_cap_bytes", RSS_CAP_BYTES))
    )
    return {
        "passed": passed,
        "requested_workers": workers,
        "initialized_workers": distinct,
        "peak_group_rss_bytes": observed_rss,
        "peak_group_members": len(observed_members),
        "rss_with_25pct_headroom_bytes": headroom_rss,
        "rss_cap_bytes": int(manifest.get("rss_cap_bytes", RSS_CAP_BYTES)),
        "worker_peak_rss_bytes": [int(row["peak_process_rss_bytes"]) for row in rows],
        "maximum_point_score_abs_difference": max(
            float(row["point_score_abs_difference"]) for row in rows
        ),
        "elapsed_seconds": time.monotonic() - started,
        "producer_and_independent_resources_loaded_per_worker": True,
    }


def _benchmark_files(directory: Path, root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256_file(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file()
        and path.name != "qualification.json"
        and not path.name.endswith((".tmp", "-wal", "-shm"))
        and "progress" not in path.name
    }


def _verify_recorded_files(root: Path, files: Mapping[str, str]) -> None:
    for relative, expected in files.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("qualification receipt contains an unsafe evidence path")
        target = root / path
        if not target.is_file() or sha256_file(target) != expected:
            raise ValueError(f"qualification evidence changed: {relative}")


def qualify(root: Path, workers: int) -> dict[str, Any]:
    """Run and persist the bounded Goal 062 non-production qualification."""

    root = root.resolve()
    output = root / "benchmark"
    receipt_path = output / "qualification.json"
    if receipt_path.exists():
        existing_raw = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not isinstance(existing_raw, dict):
            raise ValueError("existing qualification is not a JSON object")
        existing: dict[str, Any] = existing_raw
        if existing.get("schema") != SCHEMA:
            raise ValueError("existing qualification has an unexpected schema")
        if existing.get("binding_sha256") != sha256_file(root / "source-manifest.json"):
            raise ValueError("existing qualification belongs to another source freeze")
        _verify_recorded_files(root, existing.get("files", {}))
        return existing
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "created_utc": datetime.now(UTC).isoformat(),
        "root": MECHANICAL_ROOT,
        "new_production_histories_generated": 0,
        "new_production_reference_rows_generated": 0,
        "production_seed_ledgers_tested_without_history_generation": True,
        "production_execution": False,
        "requested_workers": workers,
        "passed": False,
        "qualified_workers": 0,
    }
    try:
        runner = importlib.import_module("run_final_procedure_evaluation")
        with stage_events("custody"):
            manifest, binding = runner.verify_custody(root)
            result["binding_sha256"] = binding
            result["custody"] = {"passed": True, "manifest_sha256": binding}
            result["qualification_wall_cap_seconds"] = min(
                QUALIFICATION_CAP_SECONDS,
                int(
                    manifest.get(
                        "qualification_wall_seconds", QUALIFICATION_CAP_SECONDS
                    )
                ),
            )
        with stage_events("mechanical_tests"):
            mechanical_tests = qualify_mechanical_tests(root, manifest, binding)
            result["mechanical_tests"] = mechanical_tests
            if not mechanical_tests["passed"]:
                raise RuntimeError(
                    "frozen mechanical tests failed or pytest is unavailable; "
                    f"see {root / mechanical_tests['log']}"
                )
        with stage_events("runtime"):
            observed_runtime = runtime_record()
            baseline_runtime = json.loads((root / "original-runtime.json").read_text())
            runtime_check = compare_runtime(observed_runtime, baseline_runtime)
            result.update(
                runtime=observed_runtime,
                runtime_sha256=canonical_sha256(observed_runtime),
                runtime_comparison=runtime_check,
                runtime_changed=runtime_check["runtime_changed"],
                production_runtime_review_required=runtime_check[
                    "production_runtime_review_required"
                ],
            )
            if not runtime_check["passed"]:
                raise RuntimeError("frozen numerical runtime is incompatible")

        with stage_events("reused_reference_audits"):
            result["reused_reference_audits"] = qualify_reused_references(
                root, manifest, binding, workers=workers
            )
            if not result["reused_reference_audits"]["passed"]:
                raise RuntimeError("selected inherited reference re-audit failed")
        with stage_events("mechanical_effect_references"):
            mechanical_refs = qualify_mechanical_effect_references(
                root, manifest, binding
            )
            result["mechanical_effect_references"] = mechanical_refs
            if not mechanical_refs["passed"]:
                raise RuntimeError("mechanical effect-reference qualification failed")
        with stage_events("public_fixture_refits"):
            result["public_fixture_refits"] = qualify_public_refits(manifest)
            if not result["public_fixture_refits"]["passed"]:
                raise RuntimeError("accepted public full-bank refits differ")

        cache_path = output / "synthetic-reference-cache.npz"
        result["synthetic_cache"] = synthetic_reference_cache(
            cache_path, binding_sha256=binding
        )
        receipts: dict[str, list[Mapping[str, Any]]] = {}
        checks: dict[str, Any] = {}
        for stage, cases, cache in (
            ("main", MAIN_CASES, None),
            ("decision", MAIN_CASES, cache_path),
            ("holdout", MAIN_CASES, None),
            ("diagnostics", DIAGNOSTIC_CASES, None),
        ):
            with stage_events(f"history_{stage}"):
                rows = runner.run_history_stage(
                    root,
                    phase="benchmark",
                    cases=list(cases),
                    stage=stage,
                    workers=workers,
                    reference_cache_path=cache,
                )
                receipts[stage] = list(rows)
                checks[stage] = _validate_stage_receipts(receipts[stage], stage, cases)
                if not checks[stage]["passed"]:
                    raise RuntimeError(
                        f"{stage} benchmark or independent audit failed"
                    )
        result["history_stage_checks"] = checks
        with stage_events("budget_projection"):
            projection = project_budget(
                receipts, mechanical_refs["audits"], workers=workers
            )
            result["budget_projection"] = projection
            if not projection["passed"]:
                raise RuntimeError(
                    "measured campaign projection exceeds the 72-hour ceiling"
                )
        with stage_events("concurrency_memory"):
            concurrency = qualify_concurrency(manifest, workers)
            result["concurrency_memory"] = concurrency
            if not concurrency["passed"]:
                raise RuntimeError(
                    "requested worker concurrency was not memory-qualified"
                )
        result["qualified_workers"] = workers
        result["passed"] = True
        result["production_authorized"] = not bool(result["runtime_changed"])
        result["state"] = (
            "qualified_pending_runtime_review"
            if result["runtime_changed"]
            else "qualified"
        )
    except Exception as error:
        result["state"] = "qualification_failed"
        result["production_authorized"] = False
        result["failure"] = {"type": type(error).__name__, "message": str(error)}
    result["elapsed_seconds"] = time.monotonic() - started
    result["qualification_wall_cap_seconds"] = int(
        result.get("qualification_wall_cap_seconds", QUALIFICATION_CAP_SECONDS)
    )
    if result["elapsed_seconds"] > result["qualification_wall_cap_seconds"]:
        result["passed"] = False
        result["qualified_workers"] = 0
        result["production_authorized"] = False
        result["state"] = "qualification_failed"
        result["failure"] = {
            "type": "QualificationWallExceeded",
            "message": "qualification exceeded its three-hour wall budget",
        }
    result["files"] = _benchmark_files(output, root)
    write_new(receipt_path, result)
    event(
        "qualification_complete" if result["passed"] else "qualification_failed",
        stage="qualification",
        passed=bool(result["passed"]),
        elapsed_seconds=result["elapsed_seconds"],
        state=result["state"],
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=51)
    args = parser.parse_args(argv)
    result = qualify(args.root, args.workers)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
