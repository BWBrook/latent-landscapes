"""Replay the paired arrival-position Laplace diagnostic and production series check."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_name] = "1"

import numpy as np
from scipy.special import logsumexp

from latent_landscapes.arc2b_campaign import PSEUDO_ARRIVALS


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ARRIVALS_PATH = ROOT / "artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy"
ORDER192_PATH = ROOT / "artifacts/paper1_profile_development_20261018/arrival-bank-order192.npz"
ORDER816_PATH = ROOT / "artifacts/paper1_profile_development_20261018/arrival-bank-order816-max290.npz"
PRODUCTION_SOURCE = ROOT / "src/latent_landscapes/preinvasion_likelihood.py"
PSEUDO_SOURCE = ROOT / "src/latent_landscapes/arc2b_campaign.py"
CLAUDE_REFERENCE_SOURCE = ROOT / "docs/evidence/paper1-claude-bank-representation-2026-10-31/binned_laplace_check.py"

SEED = 0
SITE_COUNT = 16
CATEGORY_COUNT = 6
MIN_CATEGORY_COUNT = 200
BIN_COUNTS = (64, 256)
XS = np.geomspace(1e-2, 200.0, 40)
PRODUCTION_XS = (5.0, 20.0, 40.0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).view(np.uint8)).hexdigest()


def log_empirical(values: np.ndarray, x: float) -> float:
    return float(logsumexp(-x * values) - np.log(values.size))


def log_binned(values: np.ndarray, x: float, bins: int) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    counts = np.histogram(values, edges)[0]
    weights = counts / values.size
    width = 1.0 / bins
    lower = edges[:-1]
    log_integrals = (
        -x * lower
        + np.log(-np.expm1(-x * width))
        - np.log(x * width)
    )
    occupied = counts > 0
    return float(logsumexp(log_integrals[occupied], b=weights[occupied]))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def production_series_rows(
    arrivals: np.ndarray,
    selected_sites: np.ndarray,
    banks: dict[int, dict[str, np.ndarray | int | float]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for site_index in selected_sites:
        site = int(site_index)
        values = np.asarray(arrivals[:, site], dtype=np.float64)
        categories = np.searchsorted(np.asarray((10, 20, 30, 40, 50, 60)), values, side="left")
        for category in range(CATEGORY_COUNT):
            lower = 10.0 * category
            empirical = values[categories == category]
            u = np.concatenate(
                ((empirical - lower) / 10.0, np.asarray([(PSEUDO_ARRIVALS[category] - lower) / 10.0]))
            )
            v = 1.0 - u
            denominator = values.size + len(PSEUDO_ARRIVALS)
            for x in PRODUCTION_XS:
                direct = float(np.exp(-x * v).sum(dtype=np.float64) / denominator)
                for order, bank in banks.items():
                    max_x = float(bank["max_x"])
                    if x > max_x:
                        continue
                    moments = np.asarray(bank["power_moments"])[site, category]
                    term = 1.0
                    positive_series = float(moments[0])
                    for degree in range(1, order + 1):
                        term *= x / degree
                        positive_series += float(moments[degree]) * term
                    series = float(np.exp(-x) * positive_series)
                    rows.append(
                        {
                            "site_index": site,
                            "category": category,
                            "category_count": int(empirical.size),
                            "pseudocount": 1,
                            "denominator": denominator,
                            "x": x,
                            "order": order,
                            "direct_positive": direct,
                            "series_positive": series,
                            "absolute_error": abs(series - direct),
                            "relative_error": abs(series - direct) / max(abs(direct), np.finfo(float).tiny),
                        }
                    )
    return rows


def main() -> None:
    arrivals = np.load(ARRIVALS_PATH, mmap_mode="r")
    if arrivals.shape != (131_072, 160):
        raise ValueError(f"unexpected arrival-bank shape: {arrivals.shape}")
    rng = np.random.default_rng(SEED)
    selected_sites = rng.choice(arrivals.shape[1], SITE_COUNT, replace=False)

    orientation_rows: list[dict[str, object]] = []
    counts: dict[str, dict[str, int]] = {}
    split_checksums: dict[str, str] = {}
    membership_checks: dict[str, dict[str, dict[str, int | bool]]] = {}
    boundary_draw_counts: dict[str, int] = {}
    for site_index in selected_sites:
        site = int(site_index)
        values = np.asarray(arrivals[:, site], dtype=np.float64)
        production_categories = np.searchsorted(
            np.asarray((10, 20, 30, 40, 50, 60)), values, side="left"
        )
        counts[str(site)] = {}
        membership_checks[str(site)] = {}
        boundary_draw_counts[str(site)] = int(np.isin(values, (10, 20, 30, 40, 50, 60)).sum())
        for category in range(CATEGORY_COUNT + 1):
            if category < CATEGORY_COUNT:
                claude_membership = (values >= 10.0 * category) & (values < 10.0 * (category + 1))
            else:
                claude_membership = values >= 60.0
            production_membership = production_categories == category
            differences = int(np.count_nonzero(claude_membership != production_membership))
            membership_checks[str(site)][str(category)] = {
                "claude_count": int(claude_membership.sum()),
                "production_side_left_count": int(production_membership.sum()),
                "difference_count": differences,
                "identical_membership": differences == 0,
            }
        for category in range(CATEGORY_COUNT):
            lower = 10.0 * category
            selected = (values >= lower) & (values < lower + 10.0)
            category_values = (values[selected] - lower) / 10.0
            count = int(category_values.size)
            counts[str(site)][str(category)] = count
            if count < MIN_CATEGORY_COUNT:
                continue
            split = rng.permutation(count) < count // 2
            split_checksums[f"{site}:{category}"] = hashlib.sha256(split.tobytes()).hexdigest()
            orientations = {"u": category_values, "v": 1.0 - category_values}
            for orientation, transformed in orientations.items():
                for x in XS:
                    full = log_empirical(transformed, float(x))
                    half_a = log_empirical(transformed[split], float(x))
                    half_b = log_empirical(transformed[~split], float(x))
                    row: dict[str, object] = {
                        "orientation": orientation,
                        "site_index": site,
                        "category": category,
                        "category_count": count,
                        "half_a_count": int(split.sum()),
                        "half_b_count": int((~split).sum()),
                        "x": float(x),
                        "full_log_laplace": full,
                        "half_a_log_laplace": half_a,
                        "half_b_log_laplace": half_b,
                        "half_split_abs_delta_over_2": abs(half_a - half_b) / 2.0,
                    }
                    for bins in BIN_COUNTS:
                        binned = log_binned(transformed, float(x), bins)
                        row[f"bin{bins}_log_laplace"] = binned
                        row[f"bin{bins}_absolute_error"] = abs(binned - full)
                    orientation_rows.append(row)

    order_banks: dict[int, dict[str, np.ndarray | int | float]] = {}
    arrival_array_checksum = array_sha256(arrivals)
    for path in (ORDER192_PATH, ORDER816_PATH):
        with np.load(path, allow_pickle=False) as bank:
            order = int(bank["series_order"])
            bank_checksum = str(bank["bank_checksum"])
            if bank_checksum != arrival_array_checksum:
                raise ValueError(f"{path} does not describe the supplied arrival array")
            if int(bank["bank_size"]) != arrivals.shape[0]:
                raise ValueError(f"{path} has an unexpected bank size")
            order_banks[order] = {
                "power_moments": bank["power_moments"],
                "max_x": float(bank["max_x"]),
                "bank_checksum": bank_checksum,
            }
    production_rows = production_series_rows(arrivals, selected_sites, order_banks)

    orientation_fields = [
        "orientation", "site_index", "category", "category_count", "half_a_count", "half_b_count", "x",
        "full_log_laplace", "half_a_log_laplace", "half_b_log_laplace", "half_split_abs_delta_over_2",
        "bin64_log_laplace", "bin64_absolute_error", "bin256_log_laplace", "bin256_absolute_error",
    ]
    production_fields = [
        "site_index", "category", "category_count", "pseudocount", "denominator", "x", "order",
        "direct_positive", "series_positive", "absolute_error", "relative_error",
    ]
    orientation_path = OUT / "orientation_rows.csv"
    production_path = OUT / "production_series_rows.csv"
    write_csv(orientation_path, orientation_rows, orientation_fields)
    write_csv(production_path, production_rows, production_fields)

    included = sum(count >= MIN_CATEGORY_COUNT for site in counts.values() for count in site.values())
    excluded = sum(count < MIN_CATEGORY_COUNT for site in counts.values() for count in site.values())
    by_orientation: dict[str, dict[str, float | int]] = {}
    for orientation in ("u", "v"):
        subset = [row for row in orientation_rows if row["orientation"] == orientation]
        values = np.asarray([row["half_split_abs_delta_over_2"] for row in subset])
        by_orientation[orientation] = {
            "row_count": len(subset),
            "half_split_median": float(np.median(values)),
            "half_split_p95": float(np.quantile(values, 0.95)),
        }
        for lo, hi, label in ((0.0, 5.0, "0_5"), (5.0, 20.0, "5_20"), (20.0, 50.0, "20_50"), (50.0, 200.0, "50_200")):
            block = [row for row in subset if lo < float(row["x"]) <= hi]
            half_values = np.asarray([row["half_split_abs_delta_over_2"] for row in block])
            b64 = np.asarray([row["bin64_absolute_error"] for row in block])
            b256 = np.asarray([row["bin256_absolute_error"] for row in block])
            by_orientation[orientation][label] = {
                "row_count": len(block),
                "half_split_median": float(np.median(half_values)),
                "half_split_p95": float(np.quantile(half_values, 0.95)),
                "bin64_median": float(np.median(b64)),
                "bin64_p95": float(np.quantile(b64, 0.95)),
                "bin256_median": float(np.median(b256)),
                "bin256_p95": float(np.quantile(b256, 0.95)),
            }

    summary = {
        "design": {
            "seed": SEED,
            "selected_site_count": SITE_COUNT,
            "selected_site_indices": [int(x) for x in selected_sites],
            "x_count": len(XS),
            "x_min": float(XS[0]),
            "x_max": float(XS[-1]),
            "bins": list(BIN_COUNTS),
            "category_count": CATEGORY_COUNT,
            "minimum_category_count": MIN_CATEGORY_COUNT,
            "split_rule": "rng.permutation(n) < n//2, same split reused for u and v",
            "orientations": {"u": "(arrival-lower)/10", "v": "1-u"},
            "single_thread_environment": {name: os.environ[name] for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")},
        },
        "selection": {
            "site_category_counts": counts,
            "production_side_left_membership_check": membership_checks,
            "exact_boundary_draw_count_by_site": boundary_draw_counts,
            "total_exact_boundary_draw_count": sum(boundary_draw_counts.values()),
            "membership_difference_count": sum(
                int(entry["difference_count"])
                for site in membership_checks.values()
                for entry in site.values()
            ),
            "membership_check_passed": all(
                bool(entry["identical_membership"])
                for site in membership_checks.values()
                for entry in site.values()
            ),
            "included_site_category_count": included,
            "excluded_site_category_count": excluded,
            "excluded_categories": [
                {"site_index": int(site), "category": int(category), "count": count}
                for site, site_counts in counts.items()
                for category, count in site_counts.items()
                if count < MIN_CATEGORY_COUNT
            ],
        },
        "orientation_summary": by_orientation,
        "production_positive_series": {
            "x_values": list(PRODUCTION_XS),
            "pseudocount_convention": "one pseudo-arrival in each of seven categories; denominator K+7",
            "rows": len(production_rows),
            "max_absolute_error_by_order": {
                str(order): max(float(row["absolute_error"]) for row in production_rows if int(row["order"]) == order)
                for order in order_banks
            },
            "max_relative_error_by_order": {
                str(order): max(float(row["relative_error"]) for row in production_rows if int(row["order"]) == order)
                for order in order_banks
            },
            "error_by_order_x": {
                str(order): {
                    str(x): {
                        "max_absolute_error": max(
                            float(row["absolute_error"])
                            for row in production_rows
                            if int(row["order"]) == order and float(row["x"]) == x
                        ),
                        "max_relative_error": max(
                            float(row["relative_error"])
                            for row in production_rows
                            if int(row["order"]) == order and float(row["x"]) == x
                        ),
                    }
                    for x in PRODUCTION_XS
                }
                for order in order_banks
            },
            "bank_checksums": {str(order): str(bank["bank_checksum"]) for order, bank in order_banks.items()},
        },
        "rows": {"orientation": len(orientation_rows), "production": len(production_rows)},
        "hashes": {
            "inputs": {
                str(path.relative_to(ROOT)): sha256(path)
                for path in (ARRIVALS_PATH, ORDER192_PATH, ORDER816_PATH)
            },
            "arrival_array_sha256": arrival_array_checksum,
            "sources": {
                str(path.relative_to(ROOT)): sha256(path)
                for path in (PRODUCTION_SOURCE, PSEUDO_SOURCE, CLAUDE_REFERENCE_SOURCE, Path(__file__))
            },
            "outputs": {
                str(orientation_path.relative_to(ROOT)): sha256(orientation_path),
                str(production_path.relative_to(ROOT)): sha256(production_path),
            },
        },
        "runtime": {
            "python": sys.version,
            "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
            "platform": platform.platform(),
            "executable": sys.executable,
            "cwd": str(Path.cwd()),
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        },
        "split_checksums": split_checksums,
    }
    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    lines = [
        "Paired arrival-position Laplace replay (same16sites, seed 0)",
        f"selected sites: {summary['design']['selected_site_indices']}",
        f"included site/category pairs: {included}; excluded (<200): {excluded}",
        f"orientation rows: {len(orientation_rows)}; production-series rows: {len(production_rows)}",
    ]
    for orientation in ("u", "v"):
        lines.append(f"{orientation} orientation:")
        for label in ("0_5", "5_20", "20_50", "50_200"):
            block = by_orientation[orientation][label]
            lines.append(
                f"  x {label.replace('_', '–')}: half median {block['half_split_median']:.6g}, "
                f"p95 {block['half_split_p95']:.6g}; 64-bin median/p95 "
                f"{block['bin64_median']:.6g}/{block['bin64_p95']:.6g}; "
                f"256-bin median/p95 {block['bin256_median']:.6g}/{block['bin256_p95']:.6g}"
            )
    for order in sorted(order_banks):
        lines.append(
            f"production order {order}: max abs error {summary['production_positive_series']['max_absolute_error_by_order'][str(order)]:.6g}; "
            f"max relative error {summary['production_positive_series']['max_relative_error_by_order'][str(order)]:.6g}"
        )
    (OUT / "summary.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
