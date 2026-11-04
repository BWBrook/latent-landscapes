"""Emit compact tables and figures from the frozen challenge summary."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

COLORS = {
    "pass": "#287f71",
    "fail": "#b64247",
    "indeterminate": "#d29430",
    "unavailable": "#969ca3",
    "not requested": "#edf0f2",
}


def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def integration_label(row):
    screen = row["integration_screen"]
    if screen["state"] != "receipt":
        return "unavailable"
    return {
        "pointwise_screen_passed": "pass",
        "repair_required": "fail",
        "indeterminate": "indeterminate",
    }[screen["status"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text())
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    rows = summary["datasets"]
    pairs = summary["paired_descriptives"]
    compact = []
    for row in rows:
        screen = row["integration_screen"]
        cost = row["cost"]
        compact.append(
            {
                "dataset_id": row["dataset_id"],
                "arm": row["arm"],
                "generating_h": row["report_h"],
                "dense_lean_status": row["dense_lean_comparison_status"],
                "dense_status": row["dense_search_status"],
                "bank_status": row["bank_comparison"]["status"],
                "integration_status": integration_label(row),
                "integration_receipt_status": screen["status"],
                "draws_per_point_per_stream": screen.get("final_draws_per_point_per_stream"),
                "free_h": row["free"]["effect_estimate"],
                "free_sigma": row["free"]["sigma"],
                "free_sigma_status": row["free"]["sigma_status"],
                "free_sigma_boundary": row["free"]["sigma_boundary_status"],
                "diagnostic_category": row["diagnostic_level"]["category"],
                "components": json.dumps(row["diagnostic_level"].get("components", [])),
                "actual_reported_roots_log_h": json.dumps(
                    row["diagnostic_level"].get("reported_root_log_h", [])
                ),
                "ridge_category": row["ridge"]["category"],
                "ridge_slope": row["ridge"]["slope"],
                "W1": row["w1"]["value"],
                "Wtruth": row["w_truth"]["value"],
                "dense_search_seconds": (cost.get("dense") or {})
                .get("search", {})
                .get("elapsed_seconds"),
                "lean_search_seconds": (cost.get("lean") or {})
                .get("search", {})
                .get("elapsed_seconds"),
                "dense_search_unique_h": (cost.get("dense") or {})
                .get("search", {})
                .get("standard_unique_h"),
                "lean_search_unique_h": (cost.get("lean") or {})
                .get("search", {})
                .get("standard_unique_h"),
                "parent_sha256": row["receipt_sha256"].get("profile_run"),
                "integration_sha256": screen.get("sha256"),
                "bank_comparison_sha256": row["bank_comparison"].get("sha256"),
            }
        )
    write_csv(out / "final-datasets.csv", compact)
    write_csv(out / "final-paired-descriptives.csv", pairs)
    role_rows = []
    for role in summary["profile_role_evidence"]:
        role_rows.append(
            {
                k: (json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v)
                for k, v in role.items()
            }
        )
    write_csv(out / "final-profile-roles.csv", role_rows)
    counts = {k: v for k, v in summary.items() if k.endswith("_counts") or k.endswith("_count")}
    counts.update(
        {
            "source_summary_sha256": hashlib.sha256(args.summary.read_bytes()).hexdigest(),
            "source_jobs_sha256": summary["jobs_sha256"],
            "source_manifest_sha256": summary["manifest_sha256"],
            "integration_display_counts": dict(Counter(integration_label(row) for row in rows)),
            "expansion_available": sum(p["dL"] is not None for p in pairs),
            "expansion_prediction_true": sum(p["prediction_dU_gt_dL"] is True for p in pairs),
            "ridge_available": sum(p["slope_B_minus_A"] is not None for p in pairs),
            "ridge_prediction_true": sum(
                p["prediction_slope_B_minus_A_ge_0"] is True for p in pairs
            ),
            "scientific_claim": False,
            "optimized_importance_root_movement_quantified": False,
        }
    )
    (out / "final-counts.json").write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n")

    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(11, 10), gridspec_kw={"width_ratios": [1.45, 1]})
    for ax, subset, title in zip(
        axes,
        [[r for r in rows if r["arm"] != "C"], [r for r in rows if r["arm"] == "C"]],
        ["Archived A/B datasets (120 training sites)", "Separate C cases (260 training sites)"],
        strict=True,
    ):
        for y, row in enumerate(subset):
            states = [
                {
                    "within_prespecified_gates": "pass",
                    "failed": "fail",
                    "indeterminate": "indeterminate",
                }[row["dense_lean_comparison_status"]],
                {"within_prespecified_gates": "pass", "failed": "fail", None: "not requested"}[
                    row["bank_comparison"]["status"]
                ],
                integration_label(row),
            ]
            for x, state in enumerate(states):
                ax.scatter(
                    x, y, s=135, marker="s", color=COLORS[state], edgecolors="white", linewidth=0.6
                )
        labels = [
            r["dataset_id"]
            .replace("cell-", "")
            .replace("-rep-", "/")
            .replace("-arm-", " ")
            .replace("C-map-", "map ")
            .replace("-case-", " / case ")
            for r in subset
        ]
        ax.set_yticks(range(len(subset)), labels)
        ax.set_xticks(range(3), ["Dense/lean", "Bank A/B0", "Integration"], rotation=25, ha="right")
        ax.set_xlim(-0.7, 2.7)
        ax.set_ylim(31.6, -0.8)
        ax.set_title(title, loc="left", fontsize=10, pad=12)
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
    axes[1].text(
        -0.6,
        8,
        "38 datasets; 60 profile roles\n\n"
        "Dense/lean: 24 pass, 12 fail,\n2 unresolved\n\n"
        "Banks: 16 pass, 6 fail;\n16 comparisons not requested\n\n"
        "Integration: 13 pointwise passes,\n"
        "2 repair required, 21 indeterminate,\n2 unavailable",
        va="top",
        linespacing=1.7,
    )
    fig.suptitle(
        "Finite development panel: completed execution, unresolved numerical readiness",
        fontsize=12,
        y=0.98,
    )
    fig.legend(
        handles=[Patch(color=c, label=s.capitalize()) for s, c in COLORS.items()],
        loc="lower center",
        ncol=5,
        frameon=False,
    )
    fig.subplots_adjust(left=0.14, right=0.98, top=0.92, bottom=0.10, wspace=0.65)
    fig.savefig(out / "final-status.png", dpi=145)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(13, 7), gridspec_kw={"width_ratios": [1.6, 1, 1]})
    by_id = {r["dataset_id"]: r for r in rows}
    for y, pair in enumerate(pairs):
        for arm, offset, color in [("A", -0.15, "#315f95"), ("B", 0.15, "#c9742a")]:
            row = by_id[pair[f"dataset_{arm}"]]
            for comp in row["diagnostic_level"].get("components", []):
                axes[0].plot(
                    [comp["lower_h"], comp["upper_h"]], [y + offset] * 2, color=color, lw=2
                )
                for side, marker in [("lower", "<"), ("upper", ">")]:
                    axes[0].scatter(
                        comp[f"{side}_h"],
                        y + offset,
                        color=color,
                        marker=marker if comp[f"{side}_domain_contact"] else "|",
                        s=27,
                    )
            if row["free"]["effect_estimate"] is not None:
                axes[0].scatter(row["free"]["effect_estimate"], y + offset, color=color, s=13)
            if not row["numerical_summary_available"]:
                axes[0].text(
                    1.1, y + offset, f"{arm} unresolved", color=color, fontsize=7, va="center"
                )
        if pair["dL"] is not None:
            axes[1].scatter(pair["dL"], y, marker="<", color="#315f95", s=30)
            axes[1].scatter(pair["dU"], y, marker=">", color="#c9742a", s=30)
        if pair["slope_B_minus_A"] is not None:
            axes[2].scatter(pair["slope_B_minus_A"], y, color="#554c7d", s=25)
    labels = [p["biological_history_id"].replace("cell-", "").replace("-rep-", "/") for p in pairs]
    axes[0].set_yticks(range(len(pairs)), labels)
    axes[0].set_xscale("log")
    axes[0].set_xticks([1, 3, 10, 30], ["1", "3", "10", "30"])
    axes[0].set_xlabel("h (log scale); arrows mark domain contacts")
    axes[0].set_title(
        "Dense diagnostic sets, c = 3.84\nA blue; B orange; dots show free h", fontsize=10
    )
    axes[1].set_title("Root expansion\n5/16 pairs available", fontsize=10)
    axes[1].set_xlabel("dL (blue <) and dU (orange >)")
    axes[2].set_title("Ridge-slope difference\n3/16 pairs available", fontsize=10)
    axes[2].set_xlabel("Slope B - slope A")
    for ax in axes:
        ax.set_ylim(15.6, -0.6)
        ax.grid(axis="y", alpha=0.15)
    for ax in axes[1:]:
        ax.set_yticks(range(len(pairs)), [""] * len(pairs))
        ax.axvline(0, color="#999999", lw=0.7)
    fig.suptitle("Paired A/B descriptives: missing contrasts remain unavailable", fontsize=12)
    fig.text(
        0.5,
        0.015,
        "Development diagnostics, not calibrated confidence intervals. "
        "Blank contrasts follow frozen eligibility rules.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=[0, 0.045, 1, 0.95])
    fig.savefig(out / "final-paired.png", dpi=145)
    plt.close(fig)

    available = [
        r
        for r in compact
        if r["dense_status"] == "profile_numerically_resolved"
        and r["dense_search_seconds"] is not None
        and r["lean_search_seconds"] is not None
    ]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
    for arm, color in [("A", "#315f95"), ("B", "#c9742a"), ("C", "#554c7d")]:
        subset = [r for r in available if r["arm"] == arm]
        axes[0].scatter(
            [r["dense_search_unique_h"] for r in subset],
            [r["lean_search_unique_h"] for r in subset],
            color=color,
            label=arm,
            s=27,
        )
        axes[1].scatter(
            [r["dense_search_seconds"] / 3600 for r in subset],
            [r["lean_search_seconds"] / 3600 for r in subset],
            color=color,
            s=27,
        )
    for ax in axes:
        limits = (min(ax.get_xlim()[0], ax.get_ylim()[0]), max(ax.get_xlim()[1], ax.get_ylim()[1]))
        ax.plot(limits, limits, color="#aaaaaa", lw=0.8, zorder=0)
        ax.set_xlim(limits)
        ax.set_ylim(limits)
    axes[0].set(xlabel="Dense unique search h", ylabel="Lean unique search h")
    axes[1].set(xlabel="Dense search wall hours", ylabel="Lean search wall hours")
    axes[0].legend(title="Arm", frameon=False)
    fig.suptitle("Search cost for 36 resolved pairs; comparison failures retained")
    fig.text(
        0.5,
        0.015,
        "Search only; excludes post-search cross-evaluation and integration. "
        "Shared-host wall times are descriptive.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=[0, 0.045, 1, 0.95])
    fig.savefig(out / "final-cost.png", dpi=145)
    plt.close(fig)
    print(
        json.dumps(
            {
                "datasets": len(compact),
                "pairs": len(pairs),
                "cost_pairs": len(available),
                "median_lean_unique_h": float(
                    np.median([r["lean_search_unique_h"] for r in available])
                ),
                "median_dense_unique_h": float(
                    np.median([r["dense_search_unique_h"] for r in available])
                ),
                "median_lean_dense_search_time_ratio": float(
                    np.median(
                        [r["lean_search_seconds"] / r["dense_search_seconds"] for r in available]
                    )
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
