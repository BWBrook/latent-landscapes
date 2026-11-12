#!/usr/bin/env python3
"""Observe the frozen solver and run the development sweep accepted in board 3288."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import benchmark_spatial_profile as adapter
import numpy as np
from run_development_profile import load_panel_data

from latent_landscapes.differentiable_likelihood import prepare_site_likelihood
from latent_landscapes.spatial_profile import CurveDomainError, SpatialProfileCriterion

FROZEN_COMMIT = "99af5206b6a4e53f5b8e9d71cbf348f95e9ae574"


def verify_frozen_source() -> dict:
    root = Path(adapter.__file__).resolve().parents[1]
    files = [
        *sorted((root / "src/latent_landscapes").rglob("*.py")),
        *(
            root / "scripts" / name
            for name in (
                "benchmark_spatial_profile.py",
                "fit_dataset.py",
                "qualify_spatial_profiles.py",
                "run_development_profile.py",
                "profile_level_sets.py",
            )
        ),
    ]
    hashes = {}
    for path in files:
        relative = str(path.relative_to(root))
        frozen = subprocess.check_output(["git", "show", f"{FROZEN_COMMIT}:{relative}"], cwd=root)
        expected = hashlib.sha256(frozen).hexdigest()
        if adapter.sha256_file(path) != expected:
            raise ValueError(f"imported source differs from frozen candidate: {relative}")
        hashes[relative] = expected
    return {"frozen_commit": FROZEN_COMMIT, "source_sha256": hashes}


def jsonable(value: Any) -> Any:
    return adapter._jsonable(value)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(jsonable(value), indent=2, allow_nan=False) + "\n")


def evaluation_summary(value: Any) -> dict[str, Any]:
    mode = value.mode
    return {
        "criterion": value.criterion,
        "gradient": value.criterion_gradient,
        "parameters": value.parameters,
        "success": value.success,
        "message": value.message,
        "mode_u": None if mode is None else mode.u,
        "mode_score_inf": None if mode is None else mode.score_inf,
        "mode_success": None if mode is None else mode.success,
    }


def _free_set(x: Any, gradient: Any, bounds: Any) -> np.ndarray:
    lower, upper = np.asarray(bounds, dtype=float).T
    tol = 1e-8 * np.maximum(1.0, np.maximum(np.abs(lower), np.abs(upper)))
    active = ((x <= lower + tol) & (gradient < 0)) | ((x >= upper - tol) & (gradient > 0))
    return np.flatnonzero(~active)


def _curvature_summary(curvature: Any, free: Any, gradient: Any, complete: bool) -> dict:
    b = np.asarray(curvature, dtype=float)
    g = np.asarray(gradient, dtype=float)[free]
    finite = bool(np.isfinite(b).all() and np.isfinite(g).all())
    eigenvalues = np.linalg.eigvalsh(b) if finite else np.array([math.nan])
    pd = bool(complete and finite and (len(eigenvalues) == 0 or eigenvalues.min() > 0))
    gain = float(0.5 * g @ np.linalg.solve(b, g)) if pd and len(g) else 0.0 if pd else None
    return {
        "curvature": b,
        "free": free,
        "eigenvalues": eigenvalues,
        "complete": bool(complete),
        "gain_status": "local_quadratic_prediction" if pd else "infinite_unavailable",
        "predicted_remaining_gain": gain,
    }


def curvature_at(criterion: Any, evaluate: Any, x: Any, bounds: Any) -> dict:
    x = np.asarray(x, dtype=float)
    current = evaluate(x)
    gradient = current.criterion_gradient
    free = _free_set(x, gradient, bounds)
    hessian = np.zeros((len(x), len(x)))
    failed = []
    for index in free:
        delta = 1e-5 * max(1.0, abs(float(x[index])))
        for signed in (delta, -delta):
            trial = x.copy()
            trial[index] += signed
            if not bounds[index][0] <= trial[index] <= bounds[index][1]:
                continue
            other = evaluate(trial)
            if other.success:
                hessian[:, index] = (other.criterion_gradient - gradient) / signed
                break
        else:
            failed.append(int(index))
    b = -0.5 * (hessian + hessian.T)
    if failed:
        scale = max([1.0, *(abs(float(b[i, i])) for i in free if i not in failed)])
        for index in failed:
            b[index, :] = b[:, index] = 0
            b[index, index] = scale
    return jsonable(
        {
            **_curvature_summary(b[np.ix_(free, free)], free, gradient, not failed),
            "evaluation": evaluation_summary(current),
            "projected_gradient_inf": criterion._projected_gradient_inf(-gradient, x, bounds),
            "failed_columns": failed,
        }
    )


def trace_trust_region(
    criterion: Any,
    evaluate: Any,
    start: Any,
    bounds: Any,
    *,
    maxiter: int,
    gradient_tolerance: float,
    trace_path: Path | None = None,
) -> tuple[Any, Any, Any, list[dict]]:
    """Record locals without replacing any numerical operation in the optimiser."""
    method = criterion._trust_region
    lines, first = inspect.getsourcelines(method)
    curvature_line = next(
        first + i
        for i, line in enumerate(lines)
        if line.lstrip().startswith("if self._projected_gradient_inf(")
    )
    trial_line = next(
        first + i for i, line in enumerate(lines) if line.lstrip().startswith("if ratio > 0.1:")
    )
    records: list[dict] = []
    handle = trace_path.open("x") if trace_path else None

    def append(row: dict) -> None:
        row = jsonable(row)
        records.append(row)
        if handle:
            handle.write(json.dumps(row, allow_nan=False) + "\n")
            handle.flush()

    def observe(frame: Any, event: str, arg: Any) -> Any:
        if frame.f_code is not method.__func__.__code__:
            return None
        v = frame.f_locals
        if event == "line" and frame.f_lineno in (curvature_line, trial_line):
            row = {
                "event": "curvature" if frame.f_lineno == curvature_line else "trial",
                "iteration": v["iterations"],
                "x": v["x"],
                "radius": v["radius"],
                "evaluation": evaluation_summary(v["current"]),
                **_curvature_summary(
                    v["curvature"], v["free"], v["gradient"], v["curvature_complete"]
                ),
            }
            if frame.f_lineno == trial_line:
                row.update(
                    trial=v["trial"],
                    step=v["step"],
                    shift=v["shift"],
                    proposed_step_free=v["step_free"],
                    predicted_gain=v["predicted"],
                    actual_gain=v["candidate"].criterion - v["current"].criterion,
                    ratio=v["ratio"],
                    candidate=evaluation_summary(v["candidate"]),
                )
            append(row)
        elif event == "return" and arg is not None:
            x, evaluation, result = arg
            append(
                {
                    "event": "return",
                    "x": x,
                    "evaluation": evaluation_summary(evaluation),
                    "success": bool(result.success),
                    "message": str(result.message),
                    "iterations": int(result.nit),
                    "evaluations": int(result.nfev),
                }
            )
        return observe

    previous = sys.gettrace()
    try:
        sys.settrace(observe)
        result = method(
            evaluate,
            np.asarray(start, dtype=float),
            bounds,
            maxiter=maxiter,
            gradient_tolerance=gradient_tolerance,
        )
    finally:
        sys.settrace(previous)
        if handle:
            handle.close()
    return (*result, records)


def derivative_sweep(
    criterion: Any,
    evaluate: Any,
    x: Any,
    bounds: Any,
    *,
    last_rejected_step: Any = None,
) -> dict:
    x = np.asarray(x, dtype=float)
    baseline = evaluate(x)
    directions = [(f"coordinate_{i}", np.eye(len(x))[i]) for i in range(len(x))]
    raw_step = None
    if last_rejected_step is not None:
        raw_step = np.asarray(last_rejected_step, dtype=float)
        length = np.linalg.norm(raw_step)
        if length > 0 and np.isfinite(length):
            directions.append(("last_rejected_step_unit", raw_step / length))
    lower, upper = np.asarray(bounds, dtype=float).T
    rows = []
    for name, direction in directions:
        dot = float(baseline.criterion_gradient @ direction)
        for exponent in range(1, 10):
            t = 10.0**-exponent
            row: dict = {
                "direction": name,
                "vector": direction,
                "t": t,
                "gradient_dot_direction": dot,
            }
            sides = {}
            for sign, label in ((1, "plus"), (-1, "minus")):
                point = x + sign * t * direction
                if np.any(point < lower) or np.any(point > upper):
                    row[label] = {"status": "out_of_bounds"}
                    continue
                value = evaluate(point)
                sides[label] = value
                jump = None
                if baseline.mode is not None and value.mode is not None:
                    jump = float(np.linalg.norm(value.mode.u - baseline.mode.u))
                row[label] = {
                    **evaluation_summary(value),
                    "mode_jump_l2": jump,
                    "one_sided": (value.criterion - baseline.criterion) / (sign * t)
                    if value.success and baseline.success
                    else None,
                }
                if row[label]["one_sided"] is not None:
                    row[label]["one_sided_minus_gradient"] = row[label]["one_sided"] - dot
            if len(sides) == 2 and baseline.success and all(v.success for v in sides.values()):
                central = (sides["plus"].criterion - sides["minus"].criterion) / (2 * t)
                row.update(central_difference=central, central_minus_gradient=central - dot)
            rows.append(row)
    repeats = [evaluation_summary(evaluate(x)) for _ in range(3)]
    return jsonable(
        {
            "baseline": evaluation_summary(baseline),
            "bounds": bounds,
            "raw_last_rejected_step": raw_step,
            "step_provenance": "new_unchanged_solver_trace"
            if raw_step is not None
            else "historical_rejected_step_unavailable",
            "repeated_baseline": repeats,
            "rows": rows,
        }
    )


def load_task_criterion(task_record: Path) -> tuple[Any, dict]:
    record = json.loads(task_record.read_text())
    task = record["task"]
    if task["source_commit"] != FROZEN_COMMIT:
        raise ValueError("task does not bind frozen candidate")
    argv = task["argv"]
    args = argparse.Namespace(
        **{
            name.replace("-", "_"): Path(argv[argv.index("--" + name) + 1])
            for name in ("input-dir", "observations", "arrival-bank", "compressed-bank")
        }
    )
    for path, expected in task["input_sha256"].items():
        if adapter.sha256_file(Path(path)) != expected:
            raise ValueError(f"input hash differs: {Path(path).name}")
    data, identity = load_panel_data(args)
    criterion = SpatialProfileCriterion(
        data,
        evaluator_factory=lambda h, sd: prepare_site_likelihood(
            data.observed, data.bank, h, detection_sd=sd
        ),
    )
    return criterion, {
        "task_id": task["task_id"],
        "source_commit": task["source_commit"],
        "task_record_sha256": adapter.sha256_file(task_record),
        "data_identity": identity,
        "input_hashes_verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--task-root", type=Path, default=Path("."))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    source_identity = verify_frozen_source()
    for case in json.loads(args.manifest.read_text())["checkpoints"]:
        criterion, identity = load_task_criterion(args.task_root / case["task_record"])
        identity["imported_source"] = source_identity
        h, x = case["h"], np.asarray(case["parameters"], dtype=float)
        bounds = criterion._bounds(h, False)

        def evaluate(point: Any, criterion: Any = criterion, h: float = h) -> Any:
            try:
                return criterion.evaluate_positive(point, fixed_h=h, nuisance_fd=True)
            except (CurveDomainError, FloatingPointError, ValueError) as exc:
                return criterion._invalid(
                    np.asarray(point),
                    sigma_zero=False,
                    h=h,
                    detection_sd=float(point[-1]),
                    message=str(exc),
                )

        name = case["name"]
        write_json(
            args.output_dir / f"{name}-archived-sweep.json",
            {
                "identity": identity,
                "checkpoint": case,
                "curvature": curvature_at(criterion, evaluate, x, bounds),
                "sweep": derivative_sweep(criterion, evaluate, x, bounds),
            },
        )
        final_x, _evaluation, result, trace = trace_trust_region(
            criterion,
            evaluate,
            x,
            bounds,
            maxiter=80,
            gradient_tolerance=1e-4,
            trace_path=args.output_dir / f"{name}-trace.jsonl",
        )
        rejected = [r for r in trace if r["event"] == "trial" and r["ratio"] <= 0.1]
        last = rejected[-1] if rejected else None
        same_endpoint = last is not None and np.array_equal(last["x"], final_x)
        step = last["step"] if same_endpoint else None
        write_json(
            args.output_dir / f"{name}-new-start-sweep.json",
            {
                "identity": identity,
                "checkpoint": case,
                "origin": "new prescribed start at archived final vector",
                "result": {"success": bool(result.success), "message": str(result.message)},
                "last_rejected_origin": None
                if last is None
                else {
                    "x": last["x"],
                    "iteration": last["iteration"],
                    "same_as_swept_endpoint": same_endpoint,
                    "direction_used": same_endpoint,
                },
                "curvature": curvature_at(criterion, evaluate, final_x, bounds),
                "sweep": derivative_sweep(
                    criterion, evaluate, final_x, bounds, last_rejected_step=step
                ),
            },
        )


if __name__ == "__main__":
    main()
