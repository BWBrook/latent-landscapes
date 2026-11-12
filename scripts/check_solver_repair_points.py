#!/usr/bin/env python3
"""Run the frozen endpoint and witness checks for the accepted numerical repair."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import benchmark_spatial_profile as adapter
import numpy as np
from run_development_profile import load_panel_data

from latent_landscapes.differentiable_likelihood import prepare_site_likelihood
from latent_landscapes.spatial_profile import SpatialProfileCriterion


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(adapter._jsonable(value), indent=2, allow_nan=False) + "\n")


def candidate_identity(expected: str) -> dict:
    root = Path(__file__).resolve().parents[1]
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, text=True
    ).strip()
    if actual != expected or dirty:
        raise ValueError("candidate source identity differs or has tracked changes")
    for module in (adapter, __import__("latent_landscapes.spatial_profile", fromlist=["x"])):
        if not Path(module.__file__).resolve().is_relative_to(root):
            raise ValueError("imported production module is outside candidate checkout")
    return {
        "commit": actual,
        "tracked_changes": [],
        "source_sha256": {
            str(p.relative_to(root)): adapter.sha256_file(p)
            for p in [*sorted((root / "src/latent_landscapes").rglob("*.py")), Path(__file__)]
        },
    }


def frozen_fixtures(root: Path, paths: list[Path]) -> dict[str, str]:
    hashes = {}
    for path in paths:
        path = path.resolve()
        if not path.is_relative_to(root):
            raise ValueError("point fixture is outside candidate checkout")
        relative = str(path.relative_to(root))
        subprocess.check_output(["git", "ls-files", "--error-unmatch", relative], cwd=root)
        hashes[relative] = adapter.sha256_file(path)
    return hashes


def load_criterion(original_root: Path, task_id: str, expected_record_sha: str) -> tuple[Any, dict]:
    path = original_root / "work/qualification-results" / task_id / "_task.json"
    if adapter.sha256_file(path) != expected_record_sha:
        raise ValueError("original task digest differs from frozen selection")
    record = json.loads(path.read_text())
    task = record["task"]
    if task["task_id"] != task_id or task["source_commit"] != (
        "99af5206b6a4e53f5b8e9d71cbf348f95e9ae574"
    ):
        raise ValueError("original task binding differs")
    argv = task["argv"]
    args = argparse.Namespace(
        **{
            flag.replace("-", "_"): Path(argv[argv.index("--" + flag) + 1])
            for flag in ("input-dir", "observations", "arrival-bank", "compressed-bank")
        }
    )
    hashes = {}
    for name, expected in task["input_sha256"].items():
        actual = adapter.sha256_file(Path(name))
        if actual != expected:
            raise ValueError(f"original input changed: {Path(name).name}")
        hashes[name] = actual
    data, identity = load_panel_data(args)
    criterion = SpatialProfileCriterion(
        data,
        evaluator_factory=lambda h, sd: prepare_site_likelihood(
            data.observed, data.bank, h, detection_sd=sd
        ),
    )
    return criterion, {
        "task_id": task_id,
        "task_record_sha256": adapter.sha256_file(path),
        "data_identity": identity,
        "input_sha256": hashes,
    }


def evaluation_row(value: Any) -> dict:
    mode = value.mode
    return {
        "success": bool(value.success),
        "criterion": value.criterion,
        "gradient": value.criterion_gradient,
        "message": value.message,
        "mode_success": None if mode is None else bool(mode.success),
        "mode_terminal_reason": None if mode is None else mode.inner_terminal_reason,
        "invalid_trial_rejections": None if mode is None else mode.invalid_trial_rejections,
        "mode_iterations": None if mode is None else mode.iterations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--original-root", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--constant-points", type=Path, required=True)
    parser.add_argument("--spatial-points", type=Path, required=True)
    parser.add_argument("--inner-witness", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if any(os.environ.get(key) != "1" for key in adapter.THREAD_ENVIRONMENT):
        raise ValueError("numerical thread environment must be fixed to one")
    source = candidate_identity(args.candidate_commit)
    fixtures = [args.selection, args.constant_points, args.spatial_points, args.inner_witness]
    fixture_hashes = frozen_fixtures(Path(__file__).resolve().parents[1], fixtures)
    selection = json.loads(args.selection.read_text())
    expected_records = {
        row["task_id"]: row["original_task_record_sha256"]
        for row in selection["nonregression"] + selection["development_failed"]
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    results = {
        "schema": "solver-repair-point-check-v1",
        "source": source,
        "fixture_sha256": fixture_hashes,
        "constant": [],
        "spatial": [],
        "witness": None,
        "replaces_qualification_attempt": False,
    }
    for row in json.loads(args.constant_points.read_text())["points"]:
        criterion, identity = load_criterion(
            args.original_root, row["task_id"], expected_records[row["task_id"]]
        )
        if identity["task_record_sha256"] != row["task_record_sha256"]:
            raise ValueError("constant checkpoint task hash differs")
        value = criterion.evaluate_sigma_zero(
            np.asarray(row["parameters_full"]), fixed_h=1.0, nuisance_fd=True
        )
        error = abs(value.criterion_gradient[-1] - row["reference_detection_sd_derivative"])
        results["constant"].append(
            {
                "dataset": row["dataset"],
                "identity": identity,
                "evaluation": evaluation_row(value),
                "derivative_absolute_error": error,
                "tolerance": row["tolerance"],
                "passed": bool(value.success and error <= row["tolerance"]),
                "criterion_stats": dict(criterion.stats),
            }
        )
        write_json(args.output_dir / "receipt.json", results)
    for row in json.loads(args.spatial_points.read_text())["checkpoints"]:
        task_id = Path(row["task_record"]).parent.name
        criterion, identity = load_criterion(args.original_root, task_id, expected_records[task_id])
        candidates = criterion._fit_family(
            fixed_h=row["h"],
            sigma_zero=False,
            starts=[np.asarray(row["parameters"])],
            kkt_tolerance=1e-3,
            maxiter=80,
            source_prefix="repair_development_checkpoint",
        )
        results["spatial"].append(
            {
                "name": row["name"],
                "identity": identity,
                "candidate": adapter._candidate_summary(candidates[0], family_max=0, global_max=0),
                "criterion_stats": dict(criterion.stats),
            }
        )
        write_json(args.output_dir / "receipt.json", results)
    row = json.loads(args.inner_witness.read_text())
    task_id = Path(row["task_record"]).parent.name
    criterion, identity = load_criterion(args.original_root, task_id, expected_records[task_id])
    value = criterion.evaluate_positive(
        np.asarray(row["parameters"]), fixed_h=row["h"], nuisance_fd=True
    )
    results["witness"] = {
        "identity": identity,
        "evaluation": evaluation_row(value),
        "criterion_stats": dict(criterion.stats),
    }
    results["complete_execution"] = True
    results["constant_derivative_check_passed"] = all(r["passed"] for r in results["constant"])
    results["witness_evaluation_succeeded"] = bool(value.success)
    write_json(args.output_dir / "receipt.json", results)
    candidate_identity(args.candidate_commit)
    if frozen_fixtures(Path(__file__).resolve().parents[1], fixtures) != fixture_hashes:
        raise ValueError("point fixtures changed during candidate checks")
    raise SystemExit(0 if results["constant_derivative_check_passed"] and value.success else 1)


if __name__ == "__main__":
    main()
