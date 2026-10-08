#!/usr/bin/env python3
"""Synthesize the completed Goal 057 public screening-retention pilot.

The script is deliberately downstream-only: it consumes the runner's saved
surfaces, union table, and 792 diagnostic rows.  It performs no fitting or
simulation.  All summaries are descriptive summaries of the registered
sixteen-history panel and its overlapping four-case unions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from scipy.stats import t as student_t

GRID_SHAPE = (81, 9, 5)
GRID_SIZE = math.prod(GRID_SHAPE)
SCREEN_REFERENCE_COUNT = 99
EFFECT_REFERENCE_COUNT = 999
REFERENCE_COUNT = SCREEN_REFERENCE_COUNT
CASE_COUNT = 16
UNION_COUNT = math.comb(CASE_COUNT, 4)
SCREEN_CUTOFF = 0.01
R_CUTOFF = 10.0
MU_GRID = np.asarray((0.0005, 0.001, 0.0016, 0.002, 0.0025, 0.0032, 0.004, 0.005, 0.006))
BETA_GRID = np.linspace(-2.0, 2.0, GRID_SHAPE[0])
SD_GRID = np.asarray((0.0, 0.1, 0.2, 0.3, 0.4))
MU_BOUNDS = (0.0005, 0.006)
BETA_BOUNDS = (-2.0, 2.0)
SD_BOUNDS = (0.0, 0.4)
WORKER_MARGIN = 1.5
DEFAULT_COST_SOURCE = Path("artifacts/goal056_execution/synthesis/report.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_jsonable(value), indent=2, sort_keys=True, allow_nan=False) + "\n")


def _float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _require_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _input_paths(run: Path) -> tuple[Path, Path, Path]:
    screening = run / "screening"
    return (
        _require_file(screening / "screening.npz"),
        _require_file(screening / "four_case_unions.csv"),
        _require_file(run / "diagnostic_fit_rows.json"),
    )


def _load_inputs(run: Path) -> tuple[dict[str, np.ndarray], list[dict[str, Any]], dict[str, str]]:
    screening_path, union_path, diagnostic_path = _input_paths(run)
    with np.load(screening_path, allow_pickle=False) as loaded:
        required = {
            "observed_surface",
            "observed_contrasts",
            "reference_contrasts",
            "q_values",
            "candidate_mask",
            "true_nodes",
            "true_retained",
            "global_r",
        }
        missing = required.difference(loaded.files)
        if missing:
            raise ValueError(f"screening.npz is missing {sorted(missing)}")
        arrays = {key: np.asarray(loaded[key]) for key in required}

    expected_shapes = {
        "observed_surface": (CASE_COUNT, GRID_SIZE),
        "observed_contrasts": (CASE_COUNT, GRID_SIZE),
        "reference_contrasts": (REFERENCE_COUNT, GRID_SIZE),
        "q_values": (CASE_COUNT, GRID_SIZE),
        "candidate_mask": (CASE_COUNT, GRID_SIZE),
        "true_nodes": (CASE_COUNT,),
        "true_retained": (CASE_COUNT,),
        "global_r": (CASE_COUNT, GRID_SIZE),
    }
    for key, shape in expected_shapes.items():
        if arrays[key].shape != shape:
            raise ValueError(f"{key} has shape {arrays[key].shape}; expected {shape}")
    for key in (
        "observed_surface",
        "observed_contrasts",
        "reference_contrasts",
        "q_values",
        "global_r",
    ):
        if not np.isfinite(arrays[key]).all():
            raise ValueError(f"{key} contains non-finite values")
    if arrays["candidate_mask"].dtype.kind not in "biu":
        raise ValueError("candidate_mask must be a boolean or integer mask")
    arrays["candidate_mask"] = arrays["candidate_mask"].astype(bool, copy=False)
    if (
        not np.isfinite(arrays["true_nodes"]).all()
        or not np.isfinite(arrays["true_retained"]).all()
    ):
        raise ValueError("true node labels must be finite")

    # R is recomputed from the observed log-likelihood surface itself.  It is
    # intentionally independent of the local-contrast table.
    derived_r = 2.0 * (
        arrays["observed_surface"].max(axis=1, keepdims=True) - arrays["observed_surface"]
    )
    if not np.allclose(arrays["global_r"], derived_r, rtol=0.0, atol=1e-10):
        difference = float(np.max(np.abs(arrays["global_r"] - derived_r)))
        raise ValueError(f"stored global_r disagrees with observed_surface (max {difference:.3g})")
    if not np.array_equal(arrays["candidate_mask"], arrays["q_values"] > SCREEN_CUTOFF):
        raise ValueError("candidate_mask disagrees with q_values > 0.01")
    true_nodes = arrays["true_nodes"].astype(np.int64)
    if np.any((true_nodes < 0) | (true_nodes >= GRID_SIZE)):
        raise ValueError("true_nodes contains an out-of-grid index")
    if not np.array_equal(
        arrays["true_retained"].astype(bool),
        arrays["candidate_mask"][np.arange(CASE_COUNT), true_nodes],
    ):
        raise ValueError("true_retained disagrees with candidate_mask at true_nodes")

    with union_path.open(newline="") as handle:
        union_rows = list(csv.DictReader(handle))
    if len(union_rows) != UNION_COUNT:
        raise ValueError(f"expected {UNION_COUNT} four-case unions, found {len(union_rows)}")
    for row in union_rows:
        case_ids = _parse_case_ids(row.get("case_ids", ""))
        if len(case_ids) != 4 or any(case < 0 or case >= CASE_COUNT for case in case_ids):
            raise ValueError(f"invalid union case_ids: {row.get('case_ids')!r}")
        stored = int(row.get("candidate_count", "-1"))
        derived = int(np.any(arrays["candidate_mask"][list(case_ids)], axis=0).sum())
        if stored != derived:
            raise ValueError(
                f"union {row.get('case_ids')} has candidate_count {stored}; expected {derived}"
            )
        row["case_ids"] = "-".join(str(case) for case in case_ids)
        row["case_count"] = "4"
        row["candidate_count"] = str(stored)
        row["empty"] = str(bool(derived == 0)).lower()

    rows = json.loads(diagnostic_path.read_text())
    if not isinstance(rows, list) or len(rows) != 8 * REFERENCE_COUNT:
        found = len(rows) if isinstance(rows, list) else "non-list"
        raise ValueError(f"expected exactly 792 diagnostic rows, found {found}")
    required_row_fields = {
        "node_index",
        "reference_index",
        "truth_beta",
        "truth_mu",
        "truth_detection_sd",
        "fitted_beta",
        "fitted_mu",
        "fitted_detection_sd",
        "truth_loglikelihood",
        "fitted_loglikelihood",
        "objective_gap_fitted_minus_truth",
        "fit_status",
        "boundary_flags",
        "independent_error_true",
        "independent_error_fitted",
        "independent_failure",
    }
    aliases = {
        "nfev": ("nfev", "fit_nfev"),
        "elapsed_seconds": ("elapsed_seconds", "fit_elapsed_seconds"),
    }
    for row in rows:
        missing = required_row_fields.difference(row)
        if missing:
            raise ValueError(f"diagnostic row is missing {sorted(missing)}")
        for target, choices in aliases.items():
            if not any(choice in row for choice in choices):
                raise ValueError(f"diagnostic row is missing {target} (accepted aliases {choices})")
    node_ref = {(int(row["node_index"]), int(row["reference_index"])) for row in rows}
    if len(node_ref) != len(rows):
        raise ValueError("diagnostic rows do not have unique node/reference addresses")
    grouped = defaultdict(list)
    for row in rows:
        grouped[int(row["node_index"])].append(row)
    if sorted(len(group) for group in grouped.values()) != [REFERENCE_COUNT] * 8:
        raise ValueError("diagnostic rows must contain eight nodes with 99 references each")

    hashes = {
        "screening/screening.npz": sha256(screening_path),
        "screening/four_case_unions.csv": sha256(union_path),
        "diagnostic_fit_rows.json": sha256(diagnostic_path),
    }
    return arrays, rows, hashes


def _parse_case_ids(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in str(value).split("-") if part != "")
    except ValueError as error:
        raise ValueError(f"invalid case_ids {value!r}") from error


def _grid_node(index: int) -> tuple[float, float, float]:
    if index < 0 or index >= GRID_SIZE:
        raise ValueError(f"node index outside grid: {index}")
    beta_i, mu_i, sd_i = np.unravel_index(index, GRID_SHAPE)
    return float(BETA_GRID[beta_i]), float(MU_GRID[mu_i]), float(SD_GRID[sd_i])


def _quantiles(values: np.ndarray) -> dict[str, float | None]:
    if values.size == 0:
        return {"median": None, "p90": None, "p95": None, "max": None}
    return {
        "median": float(np.quantile(values, 0.5)),
        "p90": float(np.quantile(values, 0.9)),
        "p95": float(np.quantile(values, 0.95)),
        "max": float(np.max(values)),
    }


def _case_summary(arrays: dict[str, np.ndarray]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates = arrays["candidate_mask"]
    true_nodes = arrays["true_nodes"].astype(np.int64)
    rows: list[dict[str, Any]] = []
    for case in range(CASE_COUNT):
        retained_r = arrays["global_r"][case, candidates[case]]
        rows.append(
            {
                "case_id": case,
                "candidate_count": int(candidates[case].sum()),
                "true_node": int(true_nodes[case]),
                "true_q": float(arrays["q_values"][case, true_nodes[case]]),
                "true_retained": bool(arrays["true_retained"][case]),
                "retained_r_median": _quantiles(retained_r)["median"],
                "retained_r_p90": _quantiles(retained_r)["p90"],
                "retained_r_p95": _quantiles(retained_r)["p95"],
                "retained_r_max": _quantiles(retained_r)["max"],
                "retained_r_gt_10_count": int(np.sum(retained_r > R_CUTOFF)),
                "retained_r_gt_10_fraction": float(np.mean(retained_r > R_CUTOFF))
                if retained_r.size
                else None,
                "grid_r_le_10_count": int(np.sum(arrays["global_r"][case] <= R_CUTOFF)),
            }
        )
    return rows, {
        "cases": rows,
        "r_definition": "2*(max observed_surface ELL - observed_surface ELL)",
        "r_cutoff": R_CUTOFF,
    }


def _union_summary(union_rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = np.asarray([int(row["candidate_count"]) for row in union_rows], dtype=np.int64)
    return {
        "count": int(counts.size),
        "minimum": int(np.min(counts)),
        "p10": float(np.quantile(counts, 0.1)),
        "median": float(np.quantile(counts, 0.5)),
        "p90": float(np.quantile(counts, 0.9)),
        "maximum": int(np.max(counts)),
        "interpretation": (
            "The 1,820 unions overlap because they reuse the fixed sixteen-history "
            "panel; they are not independent calibration replicates."
        ),
    }


def _boundary_flags(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value] if value else []
        return [str(item) for item in parsed] if isinstance(parsed, list) else []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return []


def _estimate_summary(rows: list[dict[str, Any]], mask: np.ndarray) -> dict[str, Any]:
    parameters = ("log_mu_ratio", "beta_error", "detection_sd_error")
    out: dict[str, Any] = {"row_count": int(mask.size), "selected_row_count": int(mask.sum())}
    estimates: dict[str, Any] = {}
    errors = []
    for parameter in parameters:
        values = np.asarray(
            [_float(row[parameter]) for row, keep in zip(rows, mask, strict=True) if keep],
            dtype=object,
        )
        finite = np.asarray([value for value in values if value is not None], dtype=np.float64)
        n = int(finite.size)
        failure_count = int(mask.sum()) - n
        mean = float(np.mean(finite)) if n else None
        median = float(np.median(finite)) if n else None
        sd = float(np.std(finite, ddof=1)) if n >= 2 else None
        mcse = float(sd / math.sqrt(n)) if sd is not None else None
        tcrit = float(student_t.ppf(0.975, n - 1)) if n >= 2 else None
        estimates[parameter] = {
            "finite_count": n,
            "nonfinite_or_missing_count": failure_count,
            "mean": mean,
            "median": median,
            "sample_sd": sd,
            "mcse_mean": mcse,
            "approx_95_percent_mc_interval": [mean - tcrit * mcse, mean + tcrit * mcse]
            if mean is not None and mcse is not None and tcrit is not None
            else None,
        }
        if n:
            errors.append(finite)
    out["error_summaries"] = estimates

    finite_rows = []
    for row, keep in zip(rows, mask, strict=True):
        if not keep:
            continue
        values = [
            _float(row[name]) for name in ("log_mu_ratio", "beta_error", "detection_sd_error")
        ]
        if all(value is not None for value in values):
            finite_rows.append(values)
    if len(finite_rows) >= 2:
        out["covariance_3x3"] = np.cov(
            np.asarray(finite_rows, dtype=np.float64), rowvar=False, ddof=1
        )
    else:
        out["covariance_3x3"] = None
    out["covariance_complete_case_count"] = len(finite_rows)
    return out


def _diagnostic_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    output_rows: list[dict[str, Any]] = []
    by_node: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for source in rows:
        truth_mu = _float(source["truth_mu"])
        fitted_mu = _float(source["fitted_mu"])
        truth_beta = _float(source["truth_beta"])
        fitted_beta = _float(source["fitted_beta"])
        truth_sd = _float(source["truth_detection_sd"])
        fitted_sd = _float(source["fitted_detection_sd"])
        derived = dict(source)
        derived.update(
            {
                "log_mu_ratio": math.log(fitted_mu / truth_mu)
                if fitted_mu is not None and fitted_mu > 0 and truth_mu is not None and truth_mu > 0
                else None,
                "beta_error": fitted_beta - truth_beta
                if fitted_beta is not None and truth_beta is not None
                else None,
                "detection_sd_error": fitted_sd - truth_sd
                if fitted_sd is not None and truth_sd is not None
                else None,
                "nfev": source.get("nfev", source.get("fit_nfev")),
                "elapsed_seconds": source.get("elapsed_seconds", source.get("fit_elapsed_seconds")),
                "boundary_flags": json.dumps(
                    _boundary_flags(source.get("boundary_flags")), sort_keys=True
                ),
            }
        )
        output_rows.append(derived)
        by_node[int(source["node_index"])].append(derived)

    node_summaries: list[dict[str, Any]] = []
    for node in sorted(by_node):
        group = by_node[node]
        beta, mu, sd = _grid_node(node)
        primary_mask = np.ones(len(group), dtype=bool)
        success_mask = np.asarray(
            [str(row.get("fit_status")) == "converged" for row in group], dtype=bool
        )
        primary = _estimate_summary(group, primary_mask)
        finite_parameter_counts = {
            key: int(value["finite_count"]) for key, value in primary["error_summaries"].items()
        }
        boundaries = {}
        for label, estimate_name, bounds in (
            ("beta", "fitted_beta", BETA_BOUNDS),
            ("mu", "fitted_mu", MU_BOUNDS),
            ("detection_sd", "fitted_detection_sd", SD_BOUNDS),
        ):
            finite = np.asarray([_float(row.get(estimate_name)) for row in group], dtype=object)
            finite_values = np.asarray(
                [value for value in finite if value is not None], dtype=np.float64
            )
            at_lower = int(np.sum(np.isclose(finite_values, bounds[0], rtol=0.0, atol=1e-10)))
            at_upper = int(np.sum(np.isclose(finite_values, bounds[1], rtol=0.0, atol=1e-10)))
            boundaries[label] = {
                "finite_count": int(finite_values.size),
                "lower_count": at_lower,
                "upper_count": at_upper,
                "lower_fraction": at_lower / finite_values.size if finite_values.size else None,
                "upper_fraction": at_upper / finite_values.size if finite_values.size else None,
            }
        node_summaries.append(
            {
                "node_index": node,
                "beta": beta,
                "mu": mu,
                "detection_sd": sd,
                "fit_failure_count": int(np.sum(~success_mask)),
                "independent_failure_count": int(
                    sum(bool(row.get("independent_failure", False)) for row in group)
                ),
                "objective_gap_below_minus_1e-6_count": int(
                    sum(
                        (_float(row.get("objective_gap_fitted_minus_truth")) or 0.0) < -1e-6
                        for row in group
                    )
                ),
                "finite_parameter_counts": finite_parameter_counts,
                "boundary_fractions_at_frozen_bounds": boundaries,
                "primary_all_finite_returned_estimates": primary,
                "success_only_sensitivity": _estimate_summary(group, success_mask)
                if not success_mask.all()
                else None,
            }
        )

    all_mask = np.ones(len(output_rows), dtype=bool)
    pooled_raw = _estimate_summary(output_rows, all_mask)
    means = []
    for parameter in ("log_mu_ratio", "beta_error", "detection_sd_error"):
        node_means = [
            node["primary_all_finite_returned_estimates"]["error_summaries"][parameter]["mean"]
            for node in node_summaries
        ]
        node_mcse = [
            node["primary_all_finite_returned_estimates"]["error_summaries"][parameter]["mcse_mean"]
            for node in node_summaries
        ]
        node_counts = [
            node["primary_all_finite_returned_estimates"]["error_summaries"][parameter][
                "finite_count"
            ]
            for node in node_summaries
        ]
        missing_mcse_nodes = [
            node["node_index"]
            for node, value, count in zip(node_summaries, node_mcse, node_counts, strict=True)
            if value is None or count < 2
        ]
        if all(value is not None for value in node_means):
            mean = float(np.mean(np.asarray(node_means, dtype=float)))
            if not missing_mcse_nodes:
                variances = np.asarray([float(value) ** 2 for value in node_mcse])
                stratified_mcse = float(math.sqrt(float(np.sum(variances))) / len(node_summaries))
                denominator = float(
                    sum(
                        variance**2 / (count - 1)
                        for variance, count in zip(variances, node_counts, strict=True)
                    )
                )
                welch_df = (
                    float(np.sum(variances)) ** 2 / denominator if denominator > 0.0 else math.inf
                )
                if stratified_mcse == 0.0:
                    interval = [mean, mean]
                else:
                    tcrit = 1.96 if math.isinf(welch_df) else float(student_t.ppf(0.975, welch_df))
                    interval = [
                        mean - tcrit * stratified_mcse,
                        mean + tcrit * stratified_mcse,
                    ]
                means.append(
                    (
                        parameter,
                        mean,
                        stratified_mcse,
                        interval,
                        welch_df,
                        [],
                    )
                )
            else:
                means.append((parameter, mean, None, None, None, missing_mcse_nodes))
        else:
            means.append((parameter, None, None, None, None, missing_mcse_nodes))
    balanced = {
        "description": (
            "Equally weighted mixture of the eight registered nuisance nodes; no common-bias claim."
        ),
        "node_count": len(node_summaries),
        "mean_and_stratified_mcse": {
            key: {
                "mean": mean,
                "mcse_mean": mcse,
                "approx_95_percent_mc_interval": interval,
                "welch_satterthwaite_df": df,
                "missing_mcse_node_indices": missing_nodes,
            }
            for key, mean, mcse, interval, df, missing_nodes in means
        },
        "interval_method": (
            "Welch-Satterthwaite t interval from eight node variances; "
            "missing node MCSEs leave the pooled MCSE and interval missing."
        ),
        "pooled_median_raw_792_rows": {
            key: pooled_raw["error_summaries"][key]["median"]
            for key in ("log_mu_ratio", "beta_error", "detection_sd_error")
        },
    }

    def _max_abs_and_missing(field: str) -> tuple[float | None, int]:
        finite_values = []
        missing = 0
        for row in output_rows:
            value = _float(row.get(field))
            if value is None:
                missing += 1
            else:
                finite_values.append(abs(value))
        return (max(finite_values) if finite_values else None), missing

    independent_true_max, independent_true_missing = _max_abs_and_missing("independent_error_true")
    independent_fitted_max, independent_fitted_missing = _max_abs_and_missing(
        "independent_error_fitted"
    )
    checks = {
        "rows": len(output_rows),
        "nodes": len(node_summaries),
        "independent_error_max_abs": independent_true_max,
        "independent_error_missing_count": independent_true_missing,
        "independent_fitted_error_max_abs": independent_fitted_max,
        "independent_fitted_error_missing_count": independent_fitted_missing,
        "independent_failure_count": int(
            sum(bool(row.get("independent_failure", False)) for row in output_rows)
        ),
        "objective_gap_below_minus_1e-6_count": int(
            sum(
                (_float(row.get("objective_gap_fitted_minus_truth")) or 0.0) < -1e-6
                for row in output_rows
            )
        ),
        "fit_status_counts": dict(
            sorted(Counter(str(row.get("fit_status")) for row in output_rows).items())
        ),
    }
    if checks["independent_failure_count"] == 0 and (
        independent_true_missing > 0 or independent_fitted_missing > 0
    ):
        raise ValueError(
            "successful diagnostic rows must have finite independent errors; "
            "missing values were not converted to zero"
        )
    return (
        output_rows,
        node_summaries,
        {
            "nodes": node_summaries,
            "balanced_eight_node_pooled": balanced,
            "raw_792_row_summary": pooled_raw,
            "checks": checks,
        },
    )


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: Iterable[str] | None = None) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV {path}")
    fieldnames = list(fields) if fields is not None else list(rows[0])
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _jsonable(row.get(field)) for field in fieldnames})


def _cost_report(cost_source: Path, union_summary: dict[str, Any]) -> dict[str, Any]:
    source = cost_source / "report.json" if cost_source.is_dir() else cost_source
    _require_file(source)
    payload = json.loads(source.read_text())
    proposal = payload.get("cost_proposal", payload)
    median_workload = _float(proposal.get("median_wall_workload_seconds"))
    maximum_workload = _float(proposal.get("maximum_wall_workload_seconds"))
    if median_workload is None or maximum_workload is None:
        raise ValueError(
            "cost source must provide median_wall_workload_seconds and "
            "maximum_wall_workload_seconds"
        )
    nodes = {
        "panel_union_minimum": int(union_summary["minimum"]),
        "panel_union_median": float(union_summary["median"]),
        "panel_union_maximum": int(union_summary["maximum"]),
        "worst_grid_3645": GRID_SIZE,
    }
    rows = []
    for label, count in nodes.items():
        for workload_label, workload in (
            ("median", median_workload),
            ("maximum", maximum_workload),
        ):
            row = {
                "scenario": label,
                "union_nodes": count,
                "workload": workload_label,
                "workload_seconds": workload,
            }
            for workers in (16, 64):
                row[f"workers_{workers}_hours"] = float(
                    count * EFFECT_REFERENCE_COUNT * workload * WORKER_MARGIN / workers / 3600.0
                )
            rows.append(row)
    return {
        "source": str(source),
        "source_sha256": sha256(source),
        "screen_references_per_node": SCREEN_REFERENCE_COUNT,
        "effect_references_per_node": EFFECT_REFERENCE_COUNT,
        "worker_margin": WORKER_MARGIN,
        "workloads": {
            "median_wall_workload_seconds": median_workload,
            "maximum_wall_workload_seconds": maximum_workload,
        },
        "scenarios": rows,
        "projection_label": (
            "Ideal parallel projection from summed wall workloads; not measured "
            "CPU time and not a Kunanyi speedup."
        ),
        "final_resource_cap_selected": False,
    }


def _save_retention_figure(
    path_pdf: Path,
    path_png: Path,
    case_rows: list[dict[str, Any]],
    union_rows: list[dict[str, Any]],
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    fig.subplots_adjust(left=0.08, right=0.97, bottom=0.22, top=0.84, wspace=0.28)
    counts = [row["candidate_count"] for row in case_rows]
    axes[0].bar(np.arange(CASE_COUNT), counts, color="#4477aa")
    axes[0].set(
        xlabel="Fixture case",
        ylabel="Retained candidate nodes",
        title="Registered screening retention",
    )
    axes[0].set_xticks(np.arange(CASE_COUNT), [str(i) for i in range(CASE_COUNT)])
    axes[0].grid(axis="y", alpha=0.25)
    union_counts = np.sort(np.asarray([int(row["candidate_count"]) for row in union_rows]))
    axes[1].plot(
        union_counts, (np.arange(len(union_counts)) + 0.5) / len(union_counts), color="#cc6677"
    )
    axes[1].set(
        xlabel="Union candidate nodes",
        ylabel="Empirical cumulative fraction",
        title="Four-case union sizes",
    )
    axes[1].grid(alpha=0.25)
    fig.suptitle("Goal 057 screening retention", fontsize=14)
    fig.text(
        0.5,
        0.005,
        "The 1,820 four-case unions overlap within this fixed panel and are "
        "descriptive, not independent calibration replicates.",
        ha="center",
        fontsize=8,
    )
    fig.savefig(
        path_pdf, metadata={"Title": "Goal 057 screening retention", "Creator": "latent-landscapes"}
    )
    fig.savefig(
        path_png,
        dpi=180,
        metadata={"Title": "Goal 057 screening retention", "Creator": "latent-landscapes"},
    )
    plt.close(fig)


def _save_diagnostic_figure(
    path_pdf: Path, path_png: Path, node_rows: list[dict[str, Any]]
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 6.4))
    fig.subplots_adjust(left=0.08, right=0.97, bottom=0.28, top=0.84, wspace=0.28)
    x = np.arange(len(node_rows))
    labels = [f"{row['node_index']}\nSD={row['detection_sd']:g}" for row in node_rows]
    parameters = ("log_mu_ratio", "beta_error", "detection_sd_error")
    names = ("log(mu-hat / mu)", "beta-hat - beta", "SD-hat - SD")
    for axis, parameter, name in zip(axes, parameters, names, strict=True):
        means = []
        lower = []
        upper = []
        for row in node_rows:
            summary = row["primary_all_finite_returned_estimates"]["error_summaries"][parameter]
            mean = summary["mean"]
            interval = summary["approx_95_percent_mc_interval"]
            means.append(np.nan if mean is None else mean)
            lower.append(np.nan if interval is None else mean - interval[0])
            upper.append(np.nan if interval is None else interval[1] - mean)
        axis.errorbar(
            x, means, yerr=np.asarray([lower, upper]), fmt="o", color="#4477aa", capsize=3
        )
        axis.axhline(0.0, color="black", linewidth=0.8)
        axis.set(
            title=name,
            xticks=x,
            xticklabels=labels,
            ylabel="Mean error with approximate 95% MC interval",
        )
        axis.tick_params(axis="x", labelsize=7, pad=3)
        for tick in axis.get_xticklabels():
            tick.set_rotation(35)
            tick.set_ha("right")
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle("Goal 057 reused-reference nuisance diagnostic", fontsize=14)
    fig.text(
        0.5,
        0.005,
        "Primary summaries use every finite returned estimate; SD=0 nodes are "
        "labelled explicitly. Intervals describe Monte Carlo uncertainty in mean "
        "errors.",
        ha="center",
        fontsize=8,
    )
    fig.savefig(
        path_pdf, metadata={"Title": "Goal 057 nuisance diagnostic", "Creator": "latent-landscapes"}
    )
    fig.savefig(
        path_png,
        dpi=180,
        metadata={"Title": "Goal 057 nuisance diagnostic", "Creator": "latent-landscapes"},
    )
    plt.close(fig)


def _surface_page(
    case: int, arrays: dict[str, np.ndarray], vmax: float, pdf: PdfPages, png_path: Path | None
) -> None:
    values = arrays["global_r"][case].reshape(GRID_SHAPE)
    mask = arrays["candidate_mask"][case].reshape(GRID_SHAPE)
    true_node = int(arrays["true_nodes"][case])
    true_bi, true_mi, true_si = np.unravel_index(true_node, GRID_SHAPE)
    if values.shape != GRID_SHAPE or mask.shape != GRID_SHAPE:
        raise ValueError("global surface and candidate mask must match the registered grid shape")
    fig, axes = plt.subplots(1, 5, figsize=(18, 5.6), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.055, right=0.91, bottom=0.30, top=0.84, wspace=0.16)
    image = None
    for sd_i, axis in enumerate(axes):
        image = axis.pcolormesh(
            MU_GRID,
            BETA_GRID,
            values[:, :, sd_i],
            shading="nearest",
            vmin=0.0,
            vmax=vmax,
            cmap="viridis",
        )
        if np.nanmax(values[:, :, sd_i]) >= R_CUTOFF:
            axis.contour(
                MU_GRID,
                BETA_GRID,
                values[:, :, sd_i],
                levels=[R_CUTOFF],
                colors="white",
                linewidths=0.6,
                linestyles="--",
            )
        retained = np.argwhere(mask[:, :, sd_i])
        if retained.size:
            axis.scatter(
                MU_GRID[retained[:, 1]],
                BETA_GRID[retained[:, 0]],
                facecolors="none",
                edgecolors="white",
                s=12,
                linewidths=0.45,
                alpha=0.8,
                zorder=3,
            )
        if sd_i == true_si:
            axis.scatter(
                [MU_GRID[true_mi]],
                [BETA_GRID[true_bi]],
                marker="*",
                s=75,
                facecolors="none",
                edgecolors="red",
                linewidths=1.2,
                zorder=4,
            )
        axis.set_title(f"SD={SD_GRID[sd_i]:g}")
        axis.set_xticks(MU_GRID)
        axis.set_xticklabels(
            [f"{value:g}" for value in MU_GRID], rotation=45, ha="right", fontsize=7
        )
        axis.tick_params(axis="y", labelsize=8)
        axis.grid(False)
    axes[0].set_ylabel("beta")
    axes[0].tick_params(axis="y", labelleft=True)
    for axis in axes:
        axis.set_xlabel("mu")
    if image is not None:
        fig.colorbar(
            image,
            ax=axes,
            label="R = 2(max observed ELL - observed ELL)",
            shrink=0.88,
            pad=0.02,
        )
    fig.suptitle(f"Goal 057 global surface, fixture case {case:02d}", fontsize=14)
    fig.text(
        0.5,
        0.005,
        "Open circles: retained nodes. Red star: known true node. Dashed contour: "
        "descriptive R=10 marker; no chi-square interpretation.",
        ha="center",
        fontsize=8,
    )
    pdf.savefig(
        fig,
        metadata={
            "Title": f"Goal 057 global surface case {case:02d}",
            "Creator": "latent-landscapes",
        },
    )
    if png_path is not None:
        fig.savefig(
            png_path,
            dpi=160,
            metadata={
                "Title": f"Goal 057 global surface case {case:02d}",
                "Creator": "latent-landscapes",
            },
        )
    plt.close(fig)


def _save_surface_figures(output: Path, arrays: dict[str, np.ndarray]) -> None:
    vmax = float(np.max(arrays["global_r"]))
    with PdfPages(output / "global_surfaces.pdf") as pdf:
        for case in range(CASE_COUNT):
            preview = output / f"global_surface_case_{case:02d}.png" if case in (0, 7) else None
            _surface_page(case, arrays, vmax, pdf, preview)


def synthesize(run: Path, output: Path, cost_source: Path = DEFAULT_COST_SOURCE) -> dict[str, Any]:
    """Create a deterministic Goal 057 synthesis directory."""
    run = Path(run)
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"preserve existing synthesis output: {output}")
    arrays, diagnostic_source_rows, input_hashes = _load_inputs(run)
    case_rows, screening_report = _case_summary(arrays)
    _, union_path, _ = _input_paths(run)
    with union_path.open(newline="") as handle:
        union_rows = list(csv.DictReader(handle))
    union_report = _union_summary(union_rows)
    diagnostic_rows, node_rows, diagnostic_report = _diagnostic_rows(diagnostic_source_rows)
    cost_report = _cost_report(cost_source, union_report)

    output.mkdir(parents=True)
    _write_csv(output / "case_summary.csv", case_rows)
    _write_csv(output / "four_case_unions.csv", union_rows)
    diagnostic_fields = [
        "node_index",
        "reference_index",
        "truth_beta",
        "truth_mu",
        "truth_detection_sd",
        "fitted_beta",
        "fitted_mu",
        "fitted_detection_sd",
        "truth_loglikelihood",
        "fitted_loglikelihood",
        "objective_gap_fitted_minus_truth",
        "fit_status",
        "nfev",
        "elapsed_seconds",
        "boundary_flags",
        "log_mu_ratio",
        "beta_error",
        "detection_sd_error",
    ]
    _write_csv(output / "diagnostic_fit_rows.csv", diagnostic_rows, diagnostic_fields)
    node_csv_rows = []
    for node in node_rows:
        for parameter, summary in node["primary_all_finite_returned_estimates"][
            "error_summaries"
        ].items():
            node_csv_rows.append(
                {
                    "node_index": node["node_index"],
                    "beta": node["beta"],
                    "mu": node["mu"],
                    "detection_sd": node["detection_sd"],
                    "parameter": parameter,
                    **summary,
                }
            )
    _write_csv(output / "diagnostic_node_summary.csv", node_csv_rows)
    _save_retention_figure(
        output / "retention_and_union_ecdf.pdf",
        output / "retention_and_union_ecdf.png",
        case_rows,
        union_rows,
    )
    _save_diagnostic_figure(
        output / "diagnostic_mean_errors.pdf", output / "diagnostic_mean_errors.png", node_rows
    )
    _save_surface_figures(output, arrays)

    report: dict[str, Any] = {
        "status": "descriptive_goal057_screening_synthesis",
        "run": str(run),
        "input_shapes": {key: list(value.shape) for key, value in arrays.items()},
        "input_sha256": input_hashes,
        "screening": screening_report,
        "four_case_unions": union_report,
        "diagnostic": diagnostic_report,
        "cost_proposal": cost_report,
        "interpretation_limits": [
            "The sixteen fixtures are a fixed descriptive panel; their overlapping "
            "unions are not independent calibration replicates.",
            "R=10 is a descriptive contour and threshold with no chi-square interpretation.",
            "Cost values are ideal projections from summed wall workloads, not "
            "measured CPU time or Kunanyi speedup.",
        ],
        "final_resource_cap_selected": False,
    }
    _write_json(output / "report.json", report)
    output_hashes = {
        str(path.relative_to(output)): sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "status": "complete",
        "script_sha256": sha256(Path(__file__)),
        "input_sha256": input_hashes,
        "output_sha256": output_hashes,
        "output_files": sorted(output_hashes),
    }
    _write_json(output / "manifest.json", manifest)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run", type=Path, required=True, help="completed Goal 057 runner directory"
    )
    parser.add_argument("--output", type=Path, required=True, help="new synthesis directory")
    parser.add_argument(
        "--cost-source",
        type=Path,
        default=DEFAULT_COST_SOURCE,
        help="Goal 056 synthesis report.json",
    )
    args = parser.parse_args()
    result = synthesize(args.run, args.output, args.cost_source)
    print(json.dumps(_jsonable(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
