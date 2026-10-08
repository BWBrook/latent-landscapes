#!/usr/bin/env python3
"""Summarize the complete open Goal 056 panel without changing its outcomes.

The script consumes a completed panel attempt and writes a fresh report
directory.  It refuses incomplete panels, but preserves numerical or coarse
grid failures as report fields rather than repairing or silently dropping them.
No calibration table is constructed here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

MODELS = ("constant_free_h", "adjusted_free_h", "constant_h1", "adjusted_h1")
PROFILE_TO_MODEL = {
    "constant_h": "constant_free_h",
    "adjusted_h": "adjusted_free_h",
    "adjusted_beta": "adjusted_free_h",
}
SCENARIOS = (1, 5, 10, 25, 50, 100, 250, 500, 3645)
RETAINED_NODE_COUNT = 3645
REFERENCE_COUNT = 999
WORKER_MARGIN = 1.5


def sha256(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _finite(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _json_path(path: Path) -> Path:
    if path.is_dir():
        candidates = (
            path / "qualification.json",
            path / "completed.json",
            path / "panel-attempt.json",
        )
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"no expected JSON receipt under {path}")
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _resolve_input(root: Path) -> tuple[Path, Path, Path | None, Path]:
    panel = root / "panel" if (root / "panel").is_dir() else root
    results = root / "results"
    if not results.is_dir() and panel.parent.joinpath("results").is_dir():
        results = panel.parent / "results"
    manifest = panel / "manifest.json"
    if not manifest.exists() or not results.is_dir():
        raise FileNotFoundError("input must contain panel/manifest.json and results/")
    completed = panel.parent / "completed.json"
    if not completed.exists():
        raise FileNotFoundError(f"completed.json is required beside {panel}")
    return (
        panel,
        results,
        root / "numerical-audit.json" if (root / "numerical-audit.json").exists() else None,
        completed,
    )


def _qualification_attempt_path(qualification: Path) -> Path | None:
    """Find the wrapper receipt when qualification was run beside the artifact."""

    candidates = (
        qualification.parent / "qualification-attempt.json",
        qualification.parent.parent / "qualification-attempt.json",
        qualification.parent.parent / "qualify-attempt.json",
    )
    return next((candidate for candidate in candidates if candidate.exists()), None)


def _truth_rows(manifest: dict[str, Any]) -> dict[int, dict[str, float]]:
    truths = manifest.get("truths")
    if not isinstance(truths, list) or len(truths) != 16:
        raise ValueError("panel manifest must contain exactly 16 truth rows")
    result: dict[int, dict[str, float]] = {}
    for truth in truths:
        index = int(truth["index"])
        result[index] = {
            "true_h": float(truth["effect"]),
            "true_mu": float(truth["mean_hazard"]),
            "true_beta": float(truth["beta"]),
            "true_detection_sd": float(truth["detection_sd"]),
        }
    if set(result) != set(range(16)):
        raise ValueError("panel truth indices must be 0..15")
    return result


def _cell_paths(results: Path) -> list[Path]:
    paths = sorted(results.glob("cell-[0-9][0-9].json"))
    if len(paths) != 16:
        raise ValueError(f"expected 16 complete cell JSON files, found {len(paths)}")
    return paths


def _read_cells(results: Path, truths: dict[int, dict[str, float]]) -> list[dict[str, Any]]:
    cells = []
    for path in _cell_paths(results):
        cell = json.loads(path.read_text())
        index = int(cell["index"])
        if index not in truths or set(cell["paired"]["fits"]) != set(MODELS):
            raise ValueError(f"cell {path.name} has an incomplete or unknown schema")
        cell["_path"] = path
        cell["_truth"] = truths[index]
        cells.append(cell)
    if {int(cell["index"]) for cell in cells} != set(range(16)):
        raise ValueError("cell indices must be exactly 0..15")
    return sorted(cells, key=lambda cell: int(cell["index"]))


def _model_rows(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cell in cells:
        truth = cell["_truth"]
        paired = cell["paired"]
        for model in MODELS:
            fit = paired["fits"][model]
            holdout = cell.get("holdout_scores", {}).get(model, {})
            row: dict[str, Any] = {"index": int(cell["index"]), "model": model, **truth}
            for parameter in ("h", "beta", "mu", "detection_sd"):
                estimate = _finite(fit.get(parameter))
                row[parameter] = estimate
                row[f"{parameter}_error"] = (
                    estimate - truth[f"true_{parameter}"] if estimate is not None else None
                )
            row.update(
                {
                    "numerical_status": fit.get("numerical_status"),
                    "boundary_flags": json.dumps(fit.get("boundary_flags", []), sort_keys=True),
                    "raw_train_logjoint": _finite(fit.get("raw_logjoint")),
                    "T_adjusted": _finite(paired.get("T")),
                    "T_constant": _finite(paired.get("statistics", {}).get("constant")),
                    "heldout_conditional_prey_total_nats": _finite(
                        holdout.get("conditional_prey_total_nats")
                    ),
                    "heldout_conditional_prey_nats_per_site": _finite(
                        holdout.get("conditional_prey_nats_per_site")
                    ),
                    "main_nfev": fit.get("nfev"),
                    "main_time_seconds": _finite(fit.get("elapsed_seconds")),
                }
            )
            rows.append(row)
    return rows


def _pre_rows(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for cell in cells:
        truth = cell["_truth"]
        fit = cell["pre_only"]
        row: dict[str, Any] = {"index": int(cell["index"]), **truth}
        for parameter in ("beta", "mu", "detection_sd"):
            estimate = _finite(fit.get(parameter))
            row[parameter] = estimate
            row[f"{parameter}_error"] = (
                estimate - truth[f"true_{parameter}"] if estimate is not None else None
            )
        row.update(
            {
                "numerical_status": fit.get("numerical_status"),
                "boundary_flags": json.dumps(fit.get("boundary_flags", []), sort_keys=True),
                "raw_train_logjoint": _finite(fit.get("raw_logjoint")),
                "nfev": fit.get("nfev"),
                "time_seconds": _finite(fit.get("elapsed_seconds")),
            }
        )
        rows.append(row)
    return rows


def _profile_rows(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for cell in cells:
        for profile_name, profile in cell.get("profiles", {}).items():
            model = PROFILE_TO_MODEL.get(profile_name)
            if model is None:
                continue
            main = _finite(cell["paired"]["fits"][model].get("raw_logjoint"))
            values = [_finite(value) for value in profile.get("values", [])]
            statuses = list(profile.get("statuses", []))
            converged = [
                value
                for value, status in zip(values, statuses, strict=True)
                if value is not None and status == "converged"
            ]
            maxgap = max(converged) - main if converged and main is not None else None
            curvature = _finite(profile.get("curvature")) if profile_name.endswith("_h") else None
            se = 1.0 / math.sqrt(-curvature) if curvature is not None and curvature < 0.0 else None
            status_counts: dict[str, int] = {}
            for status in statuses:
                status_counts[status] = status_counts.get(status, 0) + 1
            rows.append(
                {
                    "index": int(cell["index"]),
                    "profile": profile_name,
                    "model": model,
                    "grid_count": len(profile.get("grid", [])),
                    "max_profile_minus_main_logjoint": maxgap,
                    "better_than_main": bool(profile.get("better_than_main", False)),
                    "status_count": json.dumps(status_counts, sort_keys=True),
                    "status_count_converged": status_counts.get("converged", 0),
                    "status_count_failed_optimizer": status_counts.get("failed_optimizer", 0),
                    "logh_curvature": curvature,
                    "SElogh": se,
                    "curvature_coordinate": profile.get("curvature_coordinate"),
                }
            )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path.name}")
    fields = list(rows[0])
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _copy_raw_inputs(
    output: Path,
    panel: Path,
    results: Path,
    qualification: Path,
    qualification_attempt: Path | None,
    attempt: Path,
    completed: Path,
) -> dict[str, str]:
    raw = output / "raw_inputs"
    raw.mkdir()
    sources = [
        panel / "manifest.json",
        qualification,
        attempt,
        completed,
        *_cell_paths(results),
    ]
    if qualification_attempt is not None:
        sources.append(qualification_attempt)
    hashes: dict[str, str] = {}
    for source in sources:
        target = raw / source.name
        shutil.copy2(source, target)
        hashes[str(target.relative_to(output))] = sha256(target)
    return hashes


def _audit_payload(input_root: Path, audit_path: Path | None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if audit_path is not None:
        payload["numerical_audit"] = json.loads(audit_path.read_text())
    coarse = input_root / "coarse-grid-audit.json"
    if coarse.exists():
        payload["coarse_grid_audit"] = json.loads(coarse.read_text())
    return payload


def _cost_report(
    cells: list[dict[str, Any]],
    qualification: dict[str, Any],
    qualification_attempt: dict[str, Any] | None,
    completed: dict[str, Any],
    recovery_attempt: dict[str, Any],
) -> dict[str, Any]:
    fit_seconds = []
    for cell in cells:
        fits = cell["paired"]["fits"]
        fit_seconds.append(
            float(fits["adjusted_h1"]["elapsed_seconds"])
            + float(fits["adjusted_free_h"]["elapsed_seconds"])
        )
    generation = _finite(completed.get("generation_seconds"))
    generation_share = generation / 16.0 if generation is not None else None
    workload = (
        [value + generation_share for value in fit_seconds]
        if generation_share is not None
        else fit_seconds
    )
    med = median(workload)
    maximum = max(workload)
    scenarios = {}
    for retained in SCENARIOS:
        median_serial_seconds = REFERENCE_COUNT * retained * med
        maximum_serial_seconds = REFERENCE_COUNT * retained * maximum
        scenarios[str(retained)] = {
            "retained_nodes": retained,
            "references_per_node": REFERENCE_COUNT,
            "median_based": {
                "serial_wall_fit_surrogate_seconds": median_serial_seconds,
                "workers_16_seconds_with_margin": WORKER_MARGIN * median_serial_seconds / 16.0,
                "workers_64_seconds_with_margin": WORKER_MARGIN * median_serial_seconds / 64.0,
            },
            "maximum_observed_based": {
                "serial_wall_fit_surrogate_seconds": maximum_serial_seconds,
                "workers_16_seconds_with_margin": WORKER_MARGIN * maximum_serial_seconds / 16.0,
                "workers_64_seconds_with_margin": WORKER_MARGIN * maximum_serial_seconds / 64.0,
            },
            "measured_retention": False,
        }
    scalar = _finite(qualification.get("scalar_pre_only_seconds"))
    cheap = None
    if scalar is not None:
        cheap = {
            "histories": 360_855,
            "maximum_scalar_pre_point_evaluations_per_history": 7,
            "point_seconds_each": scalar,
            "point_only_seconds_proxy": 360_855 * 7 * scalar,
            "generation_and_preparation_overhead_measured": False,
            "seven_evaluations_is_a_known_count_upper_bound": True,
            "not_a_hard_runtime_bound": True,
        }
    original_context = completed.get("original_attempt")
    original_attempt = (
        original_context.get("original_attempt")
        if isinstance(original_context, dict)
        and isinstance(original_context.get("original_attempt"), dict)
        else original_context
    )
    original_seconds = (
        _finite(original_attempt.get("elapsed_seconds"))
        if isinstance(original_attempt, dict)
        else None
    )
    recovery_seconds = _finite(recovery_attempt.get("elapsed_seconds"))
    total_execution = (
        original_seconds + recovery_seconds
        if original_seconds is not None and recovery_seconds is not None
        else None
    )
    qualification_seconds = (
        _finite(qualification_attempt.get("elapsed_seconds"))
        if qualification_attempt is not None
        else _finite(qualification.get("elapsed_seconds"))
    )
    return {
        "source": (
            "measured adjusted_h1 + adjusted_free_h elapsed seconds per cell "
            "plus generation_seconds/16"
        ),
        "per_cell_fit_seconds": fit_seconds,
        "generation_seconds": generation,
        "median_wall_workload_seconds": med,
        "maximum_wall_workload_seconds": maximum,
        "serial_cpu_surrogate": "sum of wall fit workloads; no CPU-time measurement",
        "qualification_elapsed_seconds": qualification_seconds,
        "qualification_artifact_elapsed_seconds": _finite(qualification.get("elapsed_seconds")),
        "original_panel_elapsed_seconds": original_seconds,
        "recovery_elapsed_seconds": recovery_seconds,
        "total_execution_seconds": total_execution,
        "generation_timing_source": completed.get("generation_timing_source"),
        "generation_timing_details": completed.get("generation_timing_details"),
        "future_calibration_grid_nodes": RETAINED_NODE_COUNT,
        "future_calibration_run": False,
        "scenarios": scenarios,
        "cheap_pre_only_screen": cheap,
    }


def _figure_profiles(output: Path, cells: list[dict[str, Any]]) -> None:
    figure, axes = plt.subplots(
        4, 4, figsize=(12, 10), sharex=True, sharey=True, constrained_layout=True
    )
    for axis, cell in zip(axes.flat, cells, strict=True):
        truth = cell["_truth"]["true_h"]
        for profile_name, colour in (("constant_h", "tab:orange"), ("adjusted_h", "tab:blue")):
            profile = cell["profiles"][profile_name]
            grid = np.asarray(profile["grid"], dtype=float)
            values = np.asarray([np.nan if value is None else value for value in profile["values"]])
            finite = np.isfinite(values)
            if finite.any():
                axis.plot(
                    grid[finite],
                    values[finite] - np.nanmax(values),
                    color=colour,
                    label=profile_name.replace("_", " "),
                )
        axis.axvline(truth, color="black", linestyle="--", linewidth=0.8)
        axis.set_title(f"cell {cell['index']}: h={truth:g}")
        axis.set_ylim(bottom=-10)
    axes[-1, 0].set_xlabel("h")
    axes[0, 0].set_ylabel("relative training log joint")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    if handles:
        figure.legend(handles, labels, loc="outside upper center", ncol=2)
    figure.savefig(output / "h_profiles.png", dpi=180)
    figure.savefig(output / "h_profiles.pdf")
    plt.close(figure)


def _figure_estimates(output: Path, rows: list[dict[str, Any]]) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    specs = (
        ("h", "true_h", "h"),
        ("beta", "true_beta", "beta"),
        ("mu", "true_mu", "mu"),
        ("detection_sd", "true_detection_sd", "detection SD"),
    )
    for axis, (parameter, truth_key, label) in zip(axes.flat, specs, strict=True):
        for model, colour in (("constant_free_h", "tab:orange"), ("adjusted_free_h", "tab:blue")):
            selected = [row for row in rows if row["model"] == model]
            x = np.asarray([row[truth_key] for row in selected], dtype=float)
            y = np.asarray(
                [np.nan if row[parameter] is None else row[parameter] for row in selected],
                dtype=float,
            )
            axis.scatter(x, y, label=model.replace("_", " "), color=colour, s=20)
        low, high = (
            float(np.nanmin([row[truth_key] for row in rows])),
            float(np.nanmax([row[truth_key] for row in rows])),
        )
        axis.plot((low, high), (low, high), color="black", linestyle="--", linewidth=0.8)
        axis.set_xlabel(f"true {label}")
        axis.set_ylabel(f"estimated {label}")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside upper center", ncol=2)
    figure.savefig(output / "estimates_errors.png", dpi=180)
    figure.savefig(output / "estimates_errors.pdf")
    plt.close(figure)


def synthesize(
    input_root: Path, qualification_path: Path, attempt_path: Path, output: Path
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("refuse to overwrite an existing report directory")
    panel, results, audit_path, completed_file = _resolve_input(input_root)
    qualification_file = _json_path(qualification_path)
    qualification_attempt_file = _qualification_attempt_path(qualification_file)
    attempt_file = _json_path(attempt_path)
    manifest = json.loads((panel / "manifest.json").read_text())
    truths = _truth_rows(manifest)
    cells = _read_cells(results, truths)
    qualification = json.loads(qualification_file.read_text())
    qualification_attempt = (
        json.loads(qualification_attempt_file.read_text())
        if qualification_attempt_file is not None
        else None
    )
    attempt = json.loads(attempt_file.read_text())
    completed = json.loads(completed_file.read_text())
    output.mkdir(parents=True)
    raw_hashes = _copy_raw_inputs(
        output,
        panel,
        results,
        qualification_file,
        qualification_attempt_file,
        attempt_file,
        completed_file,
    )
    model_rows = _model_rows(cells)
    pre_rows = _pre_rows(cells)
    profile_rows = _profile_rows(cells)
    _write_csv(output / "all64_model_rows.csv", model_rows)
    _write_csv(output / "preonly16.csv", pre_rows)
    _write_csv(output / "profile_diagnostics.csv", profile_rows)
    _figure_profiles(output, cells)
    _figure_estimates(output, model_rows)
    h3 = [row for row in model_rows if row["model"] == "adjusted_free_h" and row["true_h"] == 3.0]
    h3_se = [
        row["SElogh"]
        for row in profile_rows
        if row["profile"] == "adjusted_h" and row["index"] in {row["index"] for row in h3}
    ]
    sd2 = [
        row
        for row in model_rows
        if row["model"] == "adjusted_free_h" and row["true_detection_sd"] == 0.2
    ]
    h3_indices = {int(row["index"]) for row in h3}
    h3_profiles = {
        str(int(row["index"])): row
        for row in profile_rows
        if row["profile"] == "adjusted_h" and int(row["index"]) in h3_indices
    }
    profile_status_counts: Counter[str] = Counter()
    for row in profile_rows:
        profile_status_counts.update(json.loads(row["status_count"]))
    boundary_counts: Counter[str] = Counter()
    for row in model_rows:
        boundary_counts.update(json.loads(row["boundary_flags"]))
    profile_failure_rows = sum(int(row["status_count_failed_optimizer"]) for row in profile_rows)
    original_context = completed.get("original_attempt")
    original_attempt = (
        original_context.get("original_attempt")
        if isinstance(original_context, dict)
        and isinstance(original_context.get("original_attempt"), dict)
        else original_context
    )
    original_seconds = (
        _finite(original_attempt.get("elapsed_seconds"))
        if isinstance(original_attempt, dict)
        else None
    )
    recovery_seconds = _finite(attempt.get("elapsed_seconds"))
    total_execution = (
        original_seconds + recovery_seconds
        if original_seconds is not None and recovery_seconds is not None
        else None
    )
    summary = {
        "status": "descriptive_open_16_fixture",
        "histories": 16,
        "models": 4,
        "model_rows": len(model_rows),
        "preonly_rows": len(pre_rows),
        "profile_rows": len(profile_rows),
        "wrapper_state": attempt.get("state"),
        "wrapper_exit_code": attempt.get("exit_code"),
        "wrapper_elapsed_seconds": _finite(attempt.get("elapsed_seconds")),
        "wrapper_peak_group_rss_bytes": attempt.get("peak_group_rss_bytes"),
        "recovery_elapsed_seconds": recovery_seconds,
        "original_attempt": original_context,
        "original_panel_elapsed_seconds": original_seconds,
        "total_execution_seconds": total_execution,
        "qualification_attempt": qualification_attempt,
        "qualification_elapsed_seconds": (
            _finite(qualification_attempt.get("elapsed_seconds"))
            if qualification_attempt is not None
            else _finite(qualification.get("elapsed_seconds"))
        ),
        "scientific_status": completed.get("status"),
        "generation_seconds": _finite(completed.get("generation_seconds")),
        "generation_timing_source": completed.get("generation_timing_source"),
        "generation_timing_details": completed.get("generation_timing_details"),
        "generation_timing_note": completed.get("original_attempt", {}).get("note")
        if isinstance(completed.get("original_attempt"), dict)
        else None,
        "adjusted_h3_SElogh_in_0.4_0.6": sum(
            value is not None and 0.4 <= value <= 0.6 for value in h3_se
        ),
        "adjusted_h3_SElogh_missing": sum(value is None for value in h3_se),
        "adjusted_h3_logh_curvature": {
            index: _finite(row["logh_curvature"]) for index, row in sorted(h3_profiles.items())
        },
        "adjusted_h3_SElogh": {
            index: _finite(row["SElogh"]) for index, row in sorted(h3_profiles.items())
        },
        "true_detection_sd_0.2_cases": len(sd2),
        "true_detection_sd_0.2_abs_sd_error_le_0.03": sum(
            row["detection_sd_error"] is not None and abs(row["detection_sd_error"]) <= 0.03
            for row in sd2
        ),
        "forecasts_are_descriptive_not_gates": True,
        "no_operating_rates_or_calibration_claim": True,
        "profile_status_counts": dict(sorted(profile_status_counts.items())),
        "profile_failed_nodes": profile_failure_rows,
        "model_boundary_counts": dict(sorted(boundary_counts.items())),
        "audit": _audit_payload(input_root, audit_path),
        "cost_proposal": _cost_report(
            cells, qualification, qualification_attempt, completed, attempt
        ),
    }
    write_json(output / "report.json", summary)
    output_hashes = {
        str(path.relative_to(output)): sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    report_manifest = {
        "status": summary["status"],
        "input_root": str(input_root),
        "runner_input_sha256": {
            "panel_manifest": sha256(panel / "manifest.json"),
            "qualification": sha256(qualification_file),
            "qualification_attempt": (
                sha256(qualification_attempt_file)
                if qualification_attempt_file is not None
                else None
            ),
            "wrapper_attempt": sha256(attempt_file),
            "scientific_completed": sha256(completed_file),
            "panel_files": {
                str(path.relative_to(panel)): sha256(path)
                for path in sorted(panel.iterdir())
                if path.is_file()
            },
            "result_files": {
                str(path.relative_to(results)): sha256(path) for path in _cell_paths(results)
            },
        },
        "synthesizer_sha256": sha256(Path(__file__).resolve()),
        "raw_input_hashes": raw_hashes,
        "output_sha256": output_hashes,
        "calibration_grid_nodes": RETAINED_NODE_COUNT,
        "calibration_run": False,
        "truths_are_open_development_fixture": True,
    }
    write_json(output / "manifest.json", report_manifest)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, required=True, help="completed panel attempt or panel directory"
    )
    parser.add_argument(
        "--qualification", type=Path, required=True, help="qualification.json or its directory"
    )
    parser.add_argument(
        "--attempt", type=Path, required=True, help="panel-attempt.json/completed.json receipt"
    )
    parser.add_argument("--output", type=Path, required=True, help="fresh report directory")
    args = parser.parse_args()
    print(
        json.dumps(
            synthesize(args.input, args.qualification, args.attempt, args.output),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
