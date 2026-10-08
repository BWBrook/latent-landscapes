"""Recover interrupted Goal 056 profile diagnostics from saved main fits.

This command deliberately does not generate observations or fit a main or
pre-only model.  It validates an interrupted panel, copies its immutable
inputs and saved fits, profiles only the requested incomplete cells, and then
runs the diagnostic coarse grid once on the complete training panel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
import shutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

from latent_landscapes import preinvasion_campaign as campaign
from latent_landscapes import preinvasion_execution as execution
from latent_landscapes import preinvasion_fitting as fitting
from latent_landscapes import preinvasion_likelihood as likelihood

HISTORY_COUNT = 16
MODEL_NAMES = (
    "constant_free_h",
    "adjusted_free_h",
    "constant_h1",
    "adjusted_h1",
)
PROFILE_MODELS = {
    "constant_h": "constant_free_h",
    "adjusted_h": "adjusted_free_h",
    "adjusted_beta": "adjusted_free_h",
}
SOURCE_CHANGE_ALLOWLIST = {
    "src/latent_landscapes/preinvasion_fitting.py",
    "tests/test_preinvasion_fitting.py",
}


def _jsonable(value: Any) -> Any:
    """Encode numpy values and unavailable floating diagnostics as JSON."""
    return execution.jsonable(value)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def _sha256(path: Path) -> str:
    return campaign.file_sha256(path)


def _mapping_hash(values: dict[str, str]) -> str:
    payload = json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_tree(source: Path, destination: Path) -> None:
    if source.exists():
        shutil.copytree(source, destination, copy_function=shutil.copy2)


def _parse_expected(values: list[str]) -> tuple[int, ...]:
    numbers: list[int] = []
    for value in values:
        for token in value.split(","):
            try:
                index = int(token)
            except ValueError as error:
                raise argparse.ArgumentTypeError(f"invalid cell index {token!r}") from error
            if index < 0 or index >= HISTORY_COUNT:
                raise argparse.ArgumentTypeError(f"cell index must lie in [0, {HISTORY_COUNT})")
            numbers.append(index)
    if len(set(numbers)) != len(numbers):
        raise argparse.ArgumentTypeError("--expected-missing contains duplicate cells")
    return tuple(sorted(numbers))


def _fit_from_json(payload: dict[str, Any]) -> fitting.FitResult:
    """Reconstruct a saved FitResult, including its audit start records."""
    fields = {
        "model",
        "h",
        "beta",
        "mu",
        "detection_sd",
        "raw_logjoint",
        "numerical_status",
        "nfev",
        "elapsed_seconds",
        "objective_gap",
        "boundary_flags",
        "warnings",
    }
    values = {key: payload[key] for key in fields if key in payload}
    starts = []
    for start in payload.get("starts", []):
        starts.append(fitting.StartRecord(**start))
    values["starts"] = tuple(starts)
    values["boundary_flags"] = tuple(values.get("boundary_flags", ()))
    values["warnings"] = tuple(values.get("warnings", ()))
    return fitting.FitResult(**values)


def _failed_profile(error: Exception) -> dict[str, Any]:
    return {
        "status": "failed",
        "error_type": type(error).__name__,
        "error": str(error),
        "coordinate": None,
        "grid": [],
        "values": [],
        "parameters": [],
        "statuses": [],
        "nfev": 0,
        "elapsed_seconds": 0.0,
        "better_than_main": None,
        "curvature": None,
        "warnings": [],
        "curvature_coordinate": None,
    }


def _recover_cell(index: int, main: dict[str, Any]) -> dict[str, Any]:
    """Profile one saved cell in a spawned worker.

    The worker receives the already persisted main-fit payload.  In
    particular, this function intentionally has no call to ``paired_fit``,
    ``fit_model`` or ``fit_pre_only_nuisance``.
    """
    if execution._WORKER_DATA is None:  # pragma: no cover - initializer guard
        raise RuntimeError("recovery worker was not initialized")
    started = time.perf_counter()
    full_train, full_holdout = execution._WORKER_DATA
    all_train = np.ones(len(full_train.site_a), dtype=bool)
    all_holdout = np.ones(len(full_holdout.site_a), dtype=bool)
    train = replace(
        full_train,
        observations=execution.subset_observations(
            full_train.observations, all_train, history=index
        ),
    )
    holdout = replace(
        full_holdout,
        observations=execution.subset_observations(
            full_holdout.observations, all_holdout, history=index
        ),
    )
    fits = {
        name: _fit_from_json(payload)
        for name, payload in main["paired"]["fits"].items()
    }
    profiles: dict[str, Any] = {}
    failed_profiles: list[str] = []
    profile_calls = {
        "constant_h": lambda: fitting.profile_h(
            train, execution.fit_loglikelihood, fits["constant_free_h"]
        ),
        "adjusted_h": lambda: fitting.profile_h(
            train, execution.fit_loglikelihood, fits["adjusted_free_h"]
        ),
        "adjusted_beta": lambda: fitting.profile_beta(
            train, execution.fit_loglikelihood, fits["adjusted_free_h"]
        ),
    }
    for name, call in profile_calls.items():
        try:
            profiles[name] = asdict(call())  # type: ignore[no-untyped-call]
        except Exception as error:  # retain the failure as a qualification diagnostic
            profiles[name] = _failed_profile(error)
            failed_profiles.append(name)

    heldout_scores: dict[str, Any] = {}
    replays: dict[str, float] = {}
    for name, fit in fits.items():
        try:
            scored = likelihood.point_score(
                holdout.observations,
                holdout.bank,
                fit.h,
                fit.beta,
                fit.mu,
                holdout.map_a,
                holdout.site_a,
                detection_sd=fit.detection_sd,
            )
            conditional = scored.conditional_prey_site_loglikelihood[0]
            heldout_scores[name] = {
                "conditional_prey_total_nats": float(conditional.sum()),
                "conditional_prey_nats_per_site": float(conditional.mean()),
                "conditional_prey_site_nats": conditional,
            }
            replays[name] = execution.fit_loglikelihood(train, **fit.parameters) - fit.raw_logjoint
        except Exception as error:
            heldout_scores[name] = {
                "status": "failed",
                "error_type": type(error).__name__,
                "error": str(error),
            }
            replays[name] = math.nan

    result = {
        # These two values are read from the saved main result and are not
        # reconstructed through a JSON round trip or refit.
        "index": index,
        "paired": main["paired"],
        "pre_only": main["pre_only"],
        "profiles": profiles,
        "holdout_scores": heldout_scores,
        "main_replay_logjoint_differences": replays,
        "profile_source_id": "recovered-v1",
        "failed_profiles": failed_profiles,
        "elapsed_seconds": time.perf_counter() - started,
    }
    return cast(dict[str, Any], _jsonable(result))


def _verify_panel(input_root: Path) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    panel = input_root / "panel"
    results = input_root / "results"
    failed = input_root / "failed.json"
    if not failed.is_file():
        raise FileNotFoundError("interrupted input must contain failed.json")
    if not panel.is_dir() or not results.is_dir():
        raise FileNotFoundError("input must contain panel/ and results/")
    manifest = _read_json(panel / "manifest.json")
    observation = panel / "observations.npz"
    evaluator = panel / "evaluator.npz"
    if not observation.is_file() or not evaluator.is_file():
        raise FileNotFoundError("panel observations.npz and evaluator.npz are required")
    if _sha256(observation) != manifest.get("observation_sha256"):
        raise ValueError("panel observation hash does not match manifest")
    if _sha256(evaluator) != manifest.get("evaluator_sha256"):
        raise ValueError("panel evaluator hash does not match manifest")
    main_files = [results / f"cell-{index:02d}-main.json" for index in range(HISTORY_COUNT)]
    missing_main = [path.name for path in main_files if not path.is_file()]
    if missing_main:
        raise FileNotFoundError(f"missing saved main fits: {missing_main}")
    for index, path in enumerate(main_files):
        payload = _read_json(path)
        if payload.get("index") != index or "paired" not in payload or "pre_only" not in payload:
            raise ValueError(f"invalid saved main result for cell {index}")
    return panel, results, manifest, _read_json(failed)


def _verify_qualification(qualification: Path, repository: Path) -> dict[str, Any]:
    receipt_path = qualification / "qualification.json"
    compressed = qualification / "compressed-bank.npz"
    if not receipt_path.is_file() or not compressed.is_file():
        raise FileNotFoundError("qualification.json and compressed-bank.npz are required")
    receipt = _read_json(receipt_path)
    if not receipt.get("passed"):
        raise ValueError("original qualification did not pass")
    if _sha256(compressed) != receipt.get("compressed_bank_sha256"):
        raise ValueError("qualified compressed bank changed")
    bank = receipt.get("bank_receipt", {})
    bank_path = Path(str(bank.get("bank_path", "")))
    if not bank_path.is_file():
        raise FileNotFoundError(f"qualified raw bank is unavailable: {bank_path}")
    if bank.get("bank_file_sha256") and _sha256(bank_path) != bank["bank_file_sha256"]:
        raise ValueError("qualified raw bank changed")
    current = execution.source_hashes(repository)
    original = receipt.get("source_hashes", {})
    differences = sorted(
        path for path in set(current) | set(original) if current.get(path) != original.get(path)
    )
    disallowed = [path for path in differences if path not in SOURCE_CHANGE_ALLOWLIST]
    if disallowed:
        raise ValueError(f"qualified source changed outside fitting allowlist: {disallowed}")
    return {
        "receipt": receipt,
        "receipt_sha256": _sha256(receipt_path),
        "compressed_path": compressed,
        "bank_path": bank_path,
        "qualified_source_hashes": original,
        "current_source_hashes": current,
        "source_hash_differences": differences,
    }


def _generation_timing(
    input_root: Path, context_path: Path | None
) -> tuple[float | None, str, dict[str, Any]]:
    if context_path is not None:
        context = _read_json(context_path)
        source = str(context.get("generation_timing_source", "context"))
        details = context.get("generation_timing_details")
        if not isinstance(details, dict):
            details = {
                key: context[key]
                for key in (
                    "started_mtime_ns",
                    "manifest_mtime_ns",
                    "generation_start_file_mtime_ns",
                    "generation_end_file_mtime_ns",
                )
                if key in context
            }
        if "generation_seconds" in context and context["generation_seconds"] is not None:
            return float(context["generation_seconds"]), source, details
        if "generation_seconds_proxy" in context:
            return float(context["generation_seconds_proxy"]), source, details
    started = input_root / "started.json"
    manifest = input_root / "panel" / "manifest.json"
    if started.is_file() and manifest.is_file():
        started_ns = started.stat().st_mtime_ns
        manifest_ns = manifest.stat().st_mtime_ns
        return max(0.0, (manifest_ns - started_ns) / 1e9), "filesystem_timestamp_proxy", {
            "started_mtime_ns": started_ns,
            "manifest_mtime_ns": manifest_ns,
        }
    return None, "unavailable", {}


def _stray_result_names(results: Path) -> list[str]:
    allowed = {
        *(f"cell-{i:02d}.json" for i in range(HISTORY_COUNT)),
        *(f"cell-{i:02d}-main.json" for i in range(HISTORY_COUNT)),
    }
    return sorted(
        path.name for path in results.glob("cell-*.json") if path.name not in allowed
    )


def _audit_rows(output: Path, grid: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(HISTORY_COUNT):
        cell = _read_json(output / "results" / f"cell-{index:02d}.json")
        for model in MODEL_NAMES:
            fit = cell["paired"]["fits"][model]
            main = fit.get("raw_logjoint")
            grid_gap = None if main is None else grid["max_logjoint"][model][index] - main
            profile_gaps: dict[str, float | None] = {}
            failed_nodes: dict[str, int] = {}
            for profile_name, profile_model in PROFILE_MODELS.items():
                if profile_model != model:
                    continue
                profile = cell["profiles"].get(profile_name, {})
                values = profile.get("values", [])
                statuses = profile.get("statuses", [])
                qualified = [
                    value
                    for value, status in zip(values, statuses, strict=False)
                    if value is not None and status == "converged"
                ]
                profile_gaps[profile_name] = (
                    max(qualified) - main if qualified and main is not None else None
                )
                failed_nodes[profile_name] = sum(status != "converged" for status in statuses)
                if profile.get("status") == "failed":
                    failed_nodes[profile_name] = max(1, failed_nodes[profile_name])
            passed = bool(
                fit.get("numerical_status") == "converged"
                and grid_gap is not None
                and grid_gap <= 1e-6
                and all(gap is not None and gap <= 1e-6 for gap in profile_gaps.values())
            )
            rows.append(
                {
                    "index": index,
                    "model": model,
                    "passed": passed,
                    "grid_minus_main_logjoint": grid_gap,
                    "profile_minus_main_logjoint": profile_gaps,
                    "profile_failed_nodes": failed_nodes,
                    "main_replay_difference": cell["main_replay_logjoint_differences"].get(model),
                    "profile_source_id": cell.get("profile_source_id", "original"),
                }
            )
    return rows


def recover(
    repository: Path,
    input_root: Path,
    qualification: Path,
    output: Path,
    expected_missing: tuple[int, ...],
    workers: int,
    original_context: Path | None = None,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("preserve earlier recovery attempts")
    if not 1 <= workers <= 16:
        raise ValueError("workers must lie in [1, 16]")
    input_root = input_root.resolve()
    panel, results, manifest, failed = _verify_panel(input_root)
    qualified = _verify_qualification(qualification.resolve(), repository.resolve())
    actual_missing = tuple(
        index
        for index in range(HISTORY_COUNT)
        if not (results / f"cell-{index:02d}.json").is_file()
    )
    if actual_missing != expected_missing:
        raise ValueError(
            "expected missing cells "
            f"{expected_missing}, observed {actual_missing}; refusing ambiguity"
        )
    complete_indices = tuple(index for index in range(HISTORY_COUNT) if index not in actual_missing)
    # Reject stray complete-cell names: the recovery receipt must describe one
    # exact 16-cell panel, with missingness supplied explicitly by the caller.
    stray = _stray_result_names(results)
    if stray:
        raise ValueError(f"unexpected result files in input: {stray}")

    output.mkdir(parents=True)
    _copy_tree(panel, output / "panel")
    for directory in ("data",):
        source = input_root / directory
        if source.exists():
            _copy_tree(source, output / directory)
    failed_source = input_root / "failed.json"
    _copy_file(failed_source, output / "original-failed.json")
    for name in ("started.json", "original-context.json"):
        source = input_root / name
        if source.is_file():
            _copy_file(source, output / name)
    if original_context is not None and original_context.is_file():
        _copy_file(original_context, output / "original-context.json")
    # Retain any additional input receipts byte-for-byte.  The interrupted
    # attempt remains inspectable even when a launcher supplied a custom
    # resource or progress receipt beside the standard files.
    for source in input_root.iterdir():
        if source.is_file() and source.name not in {"completed.json", "failed.json"}:
            destination = output / source.name
            if not destination.exists():
                _copy_file(source, destination)
    output_results = output / "results"
    output_results.mkdir()
    for index in range(HISTORY_COUNT):
        _copy_file(
            results / f"cell-{index:02d}-main.json",
            output_results / f"cell-{index:02d}-main.json",
        )
    for index in complete_indices:
        _copy_file(results / f"cell-{index:02d}.json", output_results / f"cell-{index:02d}.json")

    # Spawn only diagnostic workers. Their initializer loads observations and
    # the qualified bank; no worker has access to any main-fitting entry point.
    started = time.perf_counter()
    recovery_results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=execution._worker_initialize,
        initargs=(
            str(panel),
            str(qualified["compressed_path"]),
            str(qualified["bank_path"]),
        ),
    ) as pool:
        futures = {
            pool.submit(
                _recover_cell,
                index,
                _read_json(results / f"cell-{index:02d}-main.json"),
            ): index
            for index in actual_missing
        }
        for future in as_completed(futures):
            index = futures[future]
            result = future.result()
            campaign.write_json(output_results / f"cell-{index:02d}.json", result)
            recovery_results.append(
                {
                    "index": index,
                    "elapsed_seconds": result["elapsed_seconds"],
                    "failed_profiles": result["failed_profiles"],
                }
            )

    # The grid is deliberately evaluated once, after all missing cells have
    # been recovered, and only over the complete training split.
    execution._worker_initialize(
        str(panel), str(qualified["compressed_path"]), str(qualified["bank_path"])
    )
    if execution._WORKER_DATA is None:
        raise RuntimeError("recovery training data was not initialized")
    grid = execution.coarse_grid_audit(execution._WORKER_DATA[0])
    campaign.write_json(output / "coarse-grid-audit.json", grid)
    rows = _audit_rows(output, grid)
    profile_sources = {
        str(index): ("recovered-v1" if index in actual_missing else "original")
        for index in range(HISTORY_COUNT)
    }
    numerical_audit = {
        "passed": all(row["passed"] for row in rows),
        "rows": rows,
        "loglikelihood_gap_tolerance": 1e-6,
        "profile_source_ids": profile_sources,
        "source_end_hash": _mapping_hash(qualified["current_source_hashes"]),
    }
    campaign.write_json(output / "numerical-audit.json", numerical_audit)
    generation_seconds, timing_source, timing_details = _generation_timing(
        input_root, original_context
    )
    context = _read_json(original_context) if original_context is not None else {}
    original_attempt = context.get("original_attempt", {})
    if not isinstance(original_attempt, dict):
        original_attempt = {}
    original_attempt_elapsed = next(
        (
            float(context[key])
            for key in (
                "original_wrapper_elapsed_seconds",
                "wrapper_elapsed_seconds",
                "original_attempt_elapsed_seconds",
            )
            if context.get(key) is not None
        ),
        float(original_attempt["elapsed_seconds"])
        if original_attempt.get("elapsed_seconds") is not None
        else None,
    )
    recovery_elapsed = time.perf_counter() - started
    total_execution_seconds = (
        original_attempt_elapsed + recovery_elapsed
        if original_attempt_elapsed is not None
        else None
    )
    end_hashes = execution.source_hashes(repository)
    if end_hashes != qualified["current_source_hashes"]:
        raise RuntimeError("source changed during recovery")
    file_paths = sorted(path for path in output.rglob("*") if path.is_file())
    receipt = {
        "status": (
            "panel_recovered_pending_scientific_audit"
            if numerical_audit["passed"]
            else "panel_recovered_with_numerical_failure"
        ),
        "created_utc": datetime.now(UTC).isoformat(),
        "histories": HISTORY_COUNT,
        "workers": workers,
        "expected_missing": list(expected_missing),
        "recovered_cells": list(actual_missing),
        "copied_complete_cells": list(complete_indices),
        "generation_seconds": generation_seconds,
        "generation_timing_source": timing_source,
        "generation_timing_details": timing_details,
        "recovery_elapsed_seconds": recovery_elapsed,
        "total_execution_seconds": total_execution_seconds,
        "original_attempt": context if context else {"failed_receipt": failed},
        "original_failed_sha256": _sha256(input_root / "failed.json"),
        "original_failed_receipt": failed,
        "panel_manifest": manifest,
        "qualification_sha256": qualified["receipt_sha256"],
        "source_hashes": end_hashes,
        "source_end_hash": _mapping_hash(end_hashes),
        "qualified_source_hashes": qualified["qualified_source_hashes"],
        "source_hash_differences_allowed": qualified["source_hash_differences"],
        "profile_source_ids": profile_sources,
        "numerical_audit_passed": numerical_audit["passed"],
        # completed.json is the receipt itself and is intentionally excluded
        # from this non-circular content hash map.
        "files": {str(path.relative_to(output)): _sha256(path) for path in file_paths},
    }
    campaign.write_json(output / "completed.json", _jsonable(receipt))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--expected-missing",
        nargs="+",
        required=True,
        metavar="CELL",
        help="missing cell indices, as separate integers or comma-separated values",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--original-context", type=Path)
    args = parser.parse_args()
    expected = _parse_expected(args.expected_missing)
    try:
        receipt = recover(
            args.repository,
            args.input,
            args.qualification,
            args.output,
            expected,
            args.workers,
            args.original_context,
        )
    except Exception as error:
        # A recovery attempt may have copied immutable inputs before a
        # diagnostic worker failed. Preserve that partial output and record an
        # active recovery failure, while never touching an already completed
        # or pre-existing output directory.
        if not isinstance(error, FileExistsError) and not (args.output / "completed.json").exists():
            args.output.mkdir(parents=True, exist_ok=True)
            campaign.write_json(
                args.output / "failed.json",
                {
                    "phase": "recovery",
                    "created_utc": datetime.now(UTC).isoformat(),
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            )
        raise
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "recovered_cells": receipt["recovered_cells"],
                "numerical_audit_passed": receipt["numerical_audit_passed"],
            }
        )
    )
    if not receipt["numerical_audit_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
