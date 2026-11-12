#!/usr/bin/env python3
"""Trace the four prescribed first constant fits without changing the solver."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import benchmark_spatial_profile as adapter
import diagnose_solver_stalls as observer
import numpy as np
from fit_dataset import DEFAULTS, ReducedFamily
from run_development_profile import PanelSearch, load_panel_data

from latent_landscapes.spatial_profile import SpatialProfileCriterion

FROZEN_COMMIT = "99af5206b6a4e53f5b8e9d71cbf348f95e9ae574"
DATASETS = (
    "q-base-connected-2-window_high-mu0.004-h1-A",
    "q-trend-connected-2-temporal_trend-mu0.004-h3-A",
    "q-base-corridor-1-b100_anchor-mu0.004-h3-A",
    "q-trend-barrier-1-temporal_trend-mu0.004-h3-A",
)
GRID_NODES = 13


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(adapter._jsonable(value), indent=2, sort_keys=True) + "\n")


def criterion_grid(
    evaluate: Any,
    bounds: list[tuple[float, float]],
    *,
    nodes: int = GRID_NODES,
) -> dict[str, Any]:
    if len(bounds) != 2 or nodes < 2:
        raise ValueError("constant grid needs two coordinates and at least two nodes")
    axes = [np.linspace(lo, hi, nodes) for lo, hi in bounds]
    rows = []
    for alpha in axes[0]:
        for detection_sd in axes[1]:
            point = np.array([alpha, detection_sd], dtype=float)
            try:
                result = evaluate(point)
                valid = bool(result.success and math.isfinite(result.criterion))
                rows.append(
                    {
                        "parameters": point,
                        "valid": valid,
                        "criterion": result.criterion if valid else None,
                        "gradient": result.criterion_gradient,
                        "message": result.message,
                    }
                )
            except (FloatingPointError, ValueError) as error:
                rows.append(
                    {
                        "parameters": point,
                        "valid": False,
                        "criterion": None,
                        "gradient": None,
                        "message": f"{type(error).__name__}: {error}",
                    }
                )
    valid_rows = [row for row in rows if row["valid"]]
    best = max(valid_rows, key=lambda row: row["criterion"], default=None)
    return {
        "coordinate_names": ["alpha", "detection_sd"],
        "axes": axes,
        "nodes_per_axis": nodes,
        "scope": "coarse diagnostic grid; not an optimized or certified fit",
        "valid_count": len(valid_rows),
        "invalid_count": len(rows) - len(valid_rows),
        "best_grid_point": best,
        "points": rows,
    }


def trace_first_constant_fit(
    criterion: SpatialProfileCriterion,
    *,
    trace_path: Path,
) -> dict[str, Any]:
    original = criterion._trust_region
    captured: dict[str, Any] = {}

    def traced(
        evaluate: Any,
        start: np.ndarray,
        bounds: list[tuple[float, float]],
        *,
        maxiter: int,
        gradient_tolerance: float,
    ) -> Any:
        captured.update(evaluate=evaluate, start=start.copy(), bounds=list(bounds))
        criterion._trust_region = original  # type: ignore[method-assign]
        try:
            x, evaluation, result, trace = observer.trace_trust_region(
                criterion,
                evaluate,
                start,
                bounds,
                maxiter=maxiter,
                gradient_tolerance=gradient_tolerance,
                trace_path=trace_path,
            )
        finally:
            criterion._trust_region = traced  # type: ignore[method-assign]
        captured.update(x=x.copy(), evaluation=evaluation, result=result, trace=trace)
        return x, evaluation, result

    criterion._trust_region = traced  # type: ignore[method-assign]
    try:
        family = ReducedFamily("constant", criterion, beta_free=False)
        candidates = family._fit_constant(
            1.0,
            [DEFAULTS["sigma_zero"].copy()],
            "diagnostic_constant_first_h1",
            1e-4,
            120,
        )
    finally:
        criterion._trust_region = original  # type: ignore[method-assign]
    candidate = candidates[0]
    evaluate = captured["evaluate"]
    point, bounds = captured["x"], captured["bounds"]
    curvature = observer.curvature_at(criterion, evaluate, point, bounds)
    rejected = [
        row
        for row in captured["trace"]
        if row.get("event") == "trial" and row.get("ratio", -1.0) <= 0.1
    ]
    last = rejected[-1] if rejected else None
    same_endpoint = last is not None and np.array_equal(last["x"], point)
    last_step = last["step"] if same_endpoint else None
    sweep = observer.derivative_sweep(
        criterion,
        evaluate,
        point,
        bounds,
        last_rejected_step=None if last_step is None else np.asarray(last_step, dtype=float),
    )
    return {
        "fixed_h": 1.0,
        "start_reduced": captured["start"],
        "start_full": DEFAULTS["sigma_zero"].copy(),
        "start_provenance": "prescribed first-fit default; no historical step trace was retained",
        "maxiter": 120,
        "internal_gradient_tolerance": 1e-5,
        "eligibility_gradient_tolerance": 1e-4,
        "candidate": adapter._candidate_summary(candidate, family_max=0.0, global_max=0.0),
        "final_reduced": point,
        "final_curvature": curvature,
        "last_rejected_origin": None
        if last is None
        else {
            "x": last["x"],
            "iteration": last["iteration"],
            "same_as_swept_endpoint": same_endpoint,
            "direction_used": same_endpoint,
            "status": "attached_final_endpoint" if same_endpoint else "omitted_endpoint_moved",
        },
        "trace": captured["trace"],
        "derivative_sweep": sweep,
        "grid": criterion_grid(evaluate, bounds),
    }


def task_inputs(record: dict[str, Any]) -> tuple[str, argparse.Namespace, dict[str, str]]:
    task = record["task"]
    task_id = task["task_id"]
    dataset = next((name for name in DATASETS if task_id == f"fit-{name}-dense"), None)
    if dataset is None:
        raise ValueError("only the four prescribed dense-task constant diagnostics are supported")
    if task["source_commit"] != FROZEN_COMMIT:
        raise ValueError("task does not bind the frozen rejected candidate")
    argv = task["argv"]
    inputs: dict[str, Path] = {}
    for name in ("input-dir", "observations", "arrival-bank", "compressed-bank"):
        inputs[name.replace("-", "_")] = Path(argv[argv.index(f"--{name}") + 1])
    files = [
        inputs["input_dir"] / "public_inputs.npz",
        inputs["input_dir"] / "exposure.npz",
        inputs["observations"],
        inputs["arrival_bank"],
        inputs["compressed_bank"],
    ]
    hashes = {}
    for path in files:
        actual = adapter.sha256_file(path)
        if actual != task["input_sha256"][str(path)]:
            raise ValueError(f"input hash mismatch: {path}")
        hashes[str(path)] = actual
    return dataset, argparse.Namespace(**inputs), hashes


def run_task(task_record: Path, output: Path) -> dict[str, Any]:
    source_identity = observer.verify_frozen_source()
    record = json.loads(task_record.read_text())
    dataset, args, hashes = task_inputs(record)
    output.mkdir(parents=True, exist_ok=False)
    data, identity = load_panel_data(args)
    search = PanelSearch(data, "dense", output)
    result = trace_first_constant_fit(search.criterion, trace_path=output / "trace.jsonl")
    source_files = {
        "diagnose_constant_stalls.py": Path(__file__),
        "diagnose_solver_stalls.py": Path(observer.__file__),
        "fit_dataset.py": Path(__import__("fit_dataset").__file__),
        "spatial_profile.py": Path(__import__(
            "latent_landscapes.spatial_profile", fromlist=["__file__"]
        ).__file__),
    }
    result.update(
        schema="constant-stall-development-diagnostic-v1",
        dataset=dataset,
        task_id=record["task"]["task_id"],
        task_record_sha256=hashlib.sha256(task_record.read_bytes()).hexdigest(),
        source_commit=FROZEN_COMMIT,
        frozen_source_identity=source_identity,
        source_sha256={name: adapter.sha256_file(path) for name, path in source_files.items()},
        input_sha256=hashes,
        data_identity=identity,
        scientific_claim=False,
        replaces_qualification_attempt=False,
        repaired_acceptance=False,
    )
    for path, expected in hashes.items():
        if adapter.sha256_file(Path(path)) != expected:
            raise ValueError(f"input changed during diagnostic: {path}")
    write_json(output / "receipt.json", result)
    return {
        "dataset": dataset,
        "receipt_sha256": adapter.sha256_file(output / "receipt.json"),
        "candidate": result["candidate"],
        "final_curvature": result["final_curvature"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-record", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if any(os.environ.get(key) != "1" for key in adapter.THREAD_ENVIRONMENT):
        raise ValueError("all numerical thread environment variables must be 1")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    rows = []
    for index, task_record in enumerate(args.task_record):
        rows.append(run_task(task_record, args.output_dir / f"case-{index + 1:02d}"))
        write_json(args.output_dir / "summary.json", {"diagnostics": rows})
    print(json.dumps({"constant_datasets_diagnosed": len(rows)}))


if __name__ == "__main__":
    main()
