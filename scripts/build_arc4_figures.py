"""Build the two registered Arc 4 synthesis figures from frozen summaries.

This script is reporting-only.  It reads the existing Goal 051--054 CSV
summaries, performs no fitting or resampling, writes the exact rows plotted to
one compact CSV, and records input/output SHA-256 hashes in a manifest.
"""

from __future__ import annotations

import csv
import hashlib
import importlib
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
plt = importlib.import_module("matplotlib.pyplot")


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "goal055_execution" / "report"

GOAL051_METRICS = ROOT / "artifacts" / "goal051_execution" / "synthesis" / "cell_metrics.csv"
GOAL053_BOOTSTRAP = ROOT / "artifacts" / "goal053_execution" / "synthesis" / "bootstrap_summary.csv"
GOAL054_RATES = ROOT / "artifacts" / "goal054_execution" / "synthesis" / "rule_rates.csv"
GOAL054_ERRORS = ROOT / "artifacts" / "goal054_execution" / "synthesis" / "error_metrics.csv"

SOURCE_FILES = {
    "goal051_cell_metrics": GOAL051_METRICS,
    "goal053_bootstrap_summary": GOAL053_BOOTSTRAP,
    "goal054_rule_rates": GOAL054_RATES,
    "goal054_error_metrics": GOAL054_ERRORS,
}

CONDITIONS = ["E0", "E06", "B100-A", "N100-A"]
CONDITION_LABELS = {
    "E0": "E0",
    "E06": "E06",
    "B100-A": "B100-A",
    "N100-A": "N100-A",
}

FIGURE1_METRIC_LABELS = {
    "primary_rejection": "Adequacy rejection\n(primary detector)",
    "H_primary": "Hidden failure H\n(primary detector)",
    "strict_false_effect": "Strict false effect\n(unconditional)",
}

PALETTE = {
    "adjusted": "#0072B2",
    "constant": "#D55E00",
    "neutral": "#4C566A",
    "neutral_light": "#8793A3",
    "grid": "#D9DEE5",
    "reference": "#555555",
}


def digest(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def select_one(rows: list[dict[str, str]], **keys: str) -> dict[str, str]:
    selected = [row for row in rows if all(row.get(key) == value for key, value in keys.items())]
    if len(selected) != 1:
        raise ValueError(f"expected one row for {keys}, found {len(selected)}")
    return selected[0]


def plotted_row(
    *,
    figure: str,
    panel: str,
    condition: str,
    condition_label: str,
    metric: str,
    estimate: str,
    lower: str,
    upper: str,
    n: str,
    interval_kind: str,
    source_name: str,
    source_key: str,
    source_sha256: str,
    truth_h: str = "",
    method: str = "",
    rule: str = "",
    bootstrap_draws: str = "",
    bootstrap_seed: str = "",
) -> dict[str, str]:
    return {
        "figure": figure,
        "panel": panel,
        "condition": condition,
        "condition_label": condition_label,
        "truth_h": truth_h,
        "metric": metric,
        "method": method,
        "rule": rule,
        "estimate": estimate,
        "interval_low": lower,
        "interval_high": upper,
        "n": n,
        "interval_kind": interval_kind,
        "bootstrap_draws": bootstrap_draws,
        "bootstrap_seed": bootstrap_seed,
        "source_file": source_name,
        "source_key": source_key,
        "source_sha256": source_sha256,
    }


def load_plotted_rows() -> list[dict[str, str]]:
    metrics = read_csv(GOAL051_METRICS)
    bootstrap = read_csv(GOAL053_BOOTSTRAP)
    rates = read_csv(GOAL054_RATES)
    errors = read_csv(GOAL054_ERRORS)
    input_hashes = {name: digest(path) for name, path in SOURCE_FILES.items()}
    rows: list[dict[str, str]] = []

    # Figure 1A: all three endpoints are unconditional rates over the 1,000
    # complete Goal051 histories in each selected cell.  The source table's
    # conditional_wilson_95 bounds are carried through without recomputation.
    for metric in ["primary_rejection", "H_primary", "strict_false_effect"]:
        for cell_id in ["B_h1", "D20_h1", "B100-A_h1"]:
            source = select_one(metrics, cell_id=cell_id, metric=metric)
            assert source["n"] == "1000"
            assert source["interval_kind"] == "conditional_wilson_95"
            rows.append(
                plotted_row(
                    figure="figure1",
                    panel="A",
                    condition=cell_id,
                    condition_label={
                        "B_h1": "B h=1",
                        "D20_h1": "D20 h=1",
                        "B100-A_h1": "B100-A h=1",
                    }[cell_id],
                    metric=metric,
                    estimate=source["estimate"],
                    lower=source["interval_low"],
                    upper=source["interval_high"],
                    n=source["n"],
                    interval_kind=source["interval_kind"],
                    source_name="artifacts/goal051_execution/synthesis/cell_metrics.csv",
                    source_key=f"cell_id={cell_id};metric={metric}",
                    source_sha256=input_hashes["goal051_cell_metrics"],
                    truth_h=source["truth_h"],
                )
            )

    # Figure 1B: Goal053's signed adjusted-minus-constant change in mean
    # absolute log-h error.  These are the archived paired whole-block
    # percentile bounds from the six-cell, 2,000-draw summary.
    for cell_id in ["E0_h1", "E0_h3", "E06_h1", "E06_h3", "B100-A_h1", "B100-A_h3"]:
        source = select_one(bootstrap, cell_id=cell_id, metric="mean_abs_log_h_error_change")
        assert source["bootstrap_draws"] == "2000"
        assert source["bootstrap_seed"] == "2026092703"
        rows.append(
            plotted_row(
                figure="figure1",
                panel="B",
                condition=cell_id,
                condition_label=f"{cell_id.rsplit('_', 1)[0]} h={cell_id.rsplit('_', 1)[1][1:]}",
                metric="mean_abs_log_h_error_change",
                estimate=source["estimate"],
                lower=source["bootstrap_p2_5"],
                upper=source["bootstrap_p97_5"],
                n="1000",
                interval_kind="paired_whole_block_percentile_95",
                source_name="artifacts/goal053_execution/synthesis/bootstrap_summary.csv",
                source_key=f"cell_id={cell_id};metric=mean_abs_log_h_error_change",
                source_sha256=input_hashes["goal053_bootstrap_summary"],
                truth_h=cell_id.rsplit("_", 1)[1][1:],
                method="adjusted_minus_constant",
                bootstrap_draws=source["bootstrap_draws"],
                bootstrap_seed=source["bootstrap_seed"],
            )
        )

    # Figure 2A: the two registered Goal054 rules, preserving their
    # calibration-aware uncertainty (reference-table plus evaluation blocks).
    for cell_id in [f"{condition}_h{h}" for condition in CONDITIONS for h in [1, 3]]:
        for rule, method in [("adjusted_fullsup", "adjusted"), ("constant_beta0", "constant")]:
            source = select_one(rates, cell_id=cell_id, rule=rule)
            assert source["n"] == "1000"
            rows.append(
                plotted_row(
                    figure="figure2",
                    panel="A",
                    condition=cell_id.rsplit("_", 1)[0],
                    condition_label=CONDITION_LABELS[cell_id.rsplit("_", 1)[0]],
                    metric="declaration_rate",
                    estimate=source["rate"],
                    lower=source["calibration_aware_low"],
                    upper=source["calibration_aware_high"],
                    n=source["n"],
                    interval_kind="calibration_aware_percentile_95",
                    source_name="artifacts/goal054_execution/synthesis/rule_rates.csv",
                    source_key=f"cell_id={cell_id};rule={rule}",
                    source_sha256=input_hashes["goal054_rule_rates"],
                    truth_h=cell_id.rsplit("_", 1)[1][1:],
                    method=method,
                    rule=rule,
                    bootstrap_draws="2000",
                    bootstrap_seed="2026092905",
                )
            )

    # Figure 2B: each rule is paired with its matching estimator.  These are
    # unconditional point-error probabilities over all 1,000 histories; no
    # declared-subset or cross-estimator rows are eligible here.
    for cell_id in [f"{condition}_h{h}" for condition in CONDITIONS for h in [1, 3]]:
        for method in ["adjusted", "constant"]:
            source = select_one(errors, cell_id=cell_id, method=method, subset="unconditional")
            assert source["n"] == "1000"
            rows.append(
                plotted_row(
                    figure="figure2",
                    panel="B",
                    condition=cell_id.rsplit("_", 1)[0],
                    condition_label=CONDITION_LABELS[cell_id.rsplit("_", 1)[0]],
                    metric="one_point_five_error_rate",
                    estimate=source["one_point_five_error_rate"],
                    lower=source["one_calibration_aware_low"],
                    upper=source["one_calibration_aware_high"],
                    n=source["n"],
                    interval_kind="calibration_aware_percentile_95",
                    source_name="artifacts/goal054_execution/synthesis/error_metrics.csv",
                    source_key=f"cell_id={cell_id};method={method};subset=unconditional",
                    source_sha256=input_hashes["goal054_error_metrics"],
                    truth_h=cell_id.rsplit("_", 1)[1][1:],
                    method=method,
                    bootstrap_draws="2000",
                    bootstrap_seed="2026092905",
                )
            )

    assert len(rows) == 47
    return rows


def setup_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#6E7781")
    ax.spines["bottom"].set_color("#6E7781")
    ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)


def plot_figure1(rows: list[dict[str, str]]) -> None:
    fig = plt.figure(figsize=(11, 8.2))
    grid = fig.add_gridspec(2, 1, height_ratios=[1.18, 1.0], hspace=0.42)
    top = grid[0].subgridspec(1, 3, wspace=0.34)
    top_axes = [fig.add_subplot(top[0, i]) for i in range(3)]
    metric_order = ["primary_rejection", "H_primary", "strict_false_effect"]
    condition_order = ["B_h1", "D20_h1", "B100-A_h1"]
    metric_rows = {
        (r["metric"], r["condition"]): r
        for r in rows
        if r["figure"] == "figure1" and r["panel"] == "A"
    }
    for ax, metric in zip(top_axes, metric_order, strict=True):
        values = [metric_rows[metric, cell] for cell in condition_order]
        estimate = np.array([float(r["estimate"]) * 100 for r in values])
        lower = np.array([float(r["interval_low"]) * 100 for r in values])
        upper = np.array([float(r["interval_high"]) * 100 for r in values])
        x = np.arange(len(values))
        ax.errorbar(
            x,
            estimate,
            yerr=[estimate - lower, upper - estimate],
            fmt="o",
            color=PALETTE["neutral"],
            ecolor=PALETTE["neutral"],
            capsize=3,
            markersize=5.5,
            linewidth=1.25,
        )
        ax.set_xticks(x, ["B\nh=1", "D20\nh=1", "B100-A\nh=1"])
        ax.set_ylim(0, 50)
        ax.set_title(FIGURE1_METRIC_LABELS[metric], fontsize=10, loc="left", pad=8)
        ax.set_ylabel("Histories (%)")
        setup_axes(ax)
        for tick in ax.get_xticklabels():
            tick.set_fontsize(8.8)
    top_axes[0].set_title(
        "A  Adequacy rejection\n(primary detector)", fontsize=10, loc="left", pad=8
    )

    bottom = grid[1].subgridspec(1, 1)
    ax = fig.add_subplot(bottom[0, 0])
    bottom_rows = [r for r in rows if r["figure"] == "figure1" and r["panel"] == "B"]
    order = ["E0_h1", "E0_h3", "E06_h1", "E06_h3", "B100-A_h1", "B100-A_h3"]
    selected = {r["condition"]: r for r in bottom_rows}
    x = np.arange(len(order))
    y = np.array([float(selected[c]["estimate"]) for c in order])
    low = np.array([float(selected[c]["interval_low"]) for c in order])
    high = np.array([float(selected[c]["interval_high"]) for c in order])
    colors = [PALETTE["neutral"] if c.endswith("h1") else PALETTE["neutral_light"] for c in order]
    for idx, color in enumerate(colors):
        ax.errorbar(
            x[idx],
            y[idx],
            yerr=[[y[idx] - low[idx]], [high[idx] - y[idx]]],
            fmt="o",
            color=color,
            ecolor=color,
            capsize=3,
            markersize=5.5,
            linewidth=1.25,
        )
    ax.axhline(0, color=PALETTE["reference"], linewidth=0.9)
    ax.set_xticks(
        x,
        ["E0\nh=1", "E0\nh=3", "E06\nh=1", "E06\nh=3", "B100-A\nh=1", "B100-A\nh=3"],
    )
    ax.set_ylabel("Adjusted - constant\nchange in mean absolute log-h error")
    ax.set_ylim(-0.24, 0.24)
    ax.set_title(
        "B  Goal 053 adjustment change in mean absolute log-h error",
        loc="left",
        fontsize=10.5,
        pad=8,
    )
    setup_axes(ax)
    ax.text(
        0.005,
        0.98,
        "negative values favour adjustment",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.6,
        color="0.35",
    )
    for tick in ax.get_xticklabels():
        tick.set_fontsize(8.8)
    fig.suptitle(
        "Arc 4 evidence: detectability, hidden failure and estimation change", fontsize=13, y=0.985
    )
    fig.text(
        0.01,
        0.012,
        "A: Goal 051 h=1 cells; Wilson 95% intervals. B: Goal 053 paired whole-block 95% "
        "intervals.",
        fontsize=8.5,
        color="0.35",
    )
    fig.savefig(OUT / "arc4_hidden_error_and_estimation.png", dpi=220, bbox_inches="tight")
    fig.savefig(OUT / "arc4_hidden_error_and_estimation.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_figure2(rows: list[dict[str, str]]) -> None:
    fig = plt.figure(figsize=(11, 8.0))
    grid = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.0], hspace=0.42)
    upper = grid[0].subgridspec(1, 2, wspace=0.18)
    lower = grid[1].subgridspec(1, 2, wspace=0.18)
    upper_axes = [fig.add_subplot(upper[0, i]) for i in range(2)]
    lower_axes = [fig.add_subplot(lower[0, i]) for i in range(2)]

    def draw_method_panel(
        ax: plt.Axes,
        panel: str,
        h: int,
        metric: str,
        ylim: tuple[float, float],
        ylabel: str,
    ) -> None:
        selected = [
            r
            for r in rows
            if r["figure"] == "figure2"
            and r["panel"] == panel
            and r["metric"] == metric
            and r["truth_h"] == str(h)
        ]
        x = np.arange(len(CONDITIONS))
        for offset, method in [(-0.16, "adjusted"), (0.16, "constant")]:
            method_rows = {r["condition"]: r for r in selected if r["method"] == method}
            values = np.array([float(method_rows[c]["estimate"]) * 100 for c in CONDITIONS])
            low = np.array([float(method_rows[c]["interval_low"]) * 100 for c in CONDITIONS])
            high = np.array([float(method_rows[c]["interval_high"]) * 100 for c in CONDITIONS])
            ax.errorbar(
                x + offset,
                values,
                yerr=[values - low, high - values],
                fmt="o",
                color=PALETTE[method],
                ecolor=PALETTE[method],
                capsize=3,
                markersize=5,
                linewidth=1.2,
                label="Adjusted full-supremum rule"
                if method == "adjusted"
                else "Constant β=0 rule",
            )
        ax.set_xticks(x, [CONDITION_LABELS[c] for c in CONDITIONS])
        ax.set_ylim(*ylim)
        ax.set_ylabel(ylabel)
        panel_label = (
            "a"
            if h == 1 and panel == "A"
            else "b"
            if panel == "A"
            else "c"
            if h == 1
            else "d"
        )
        ax.set_title(
            f"{panel_label}  h={h}",
            loc="left",
            fontsize=10.5,
            pad=8,
        )
        setup_axes(ax)
        for tick in ax.get_xticklabels():
            tick.set_fontsize(8.8)

    draw_method_panel(
        upper_axes[0], "A", 1, "declaration_rate", (0, 27), "Histories declaring h>1 (%)"
    )
    draw_method_panel(
        upper_axes[1], "A", 3, "declaration_rate", (60, 102), "Histories declaring h>1 (%)"
    )
    upper_axes[0].axhline(5, color=PALETTE["reference"], linestyle="--", linewidth=0.9)
    upper_axes[0].text(
        0.02,
        5.8,
        "5% nominal null",
        transform=upper_axes[0].get_yaxis_transform(),
        fontsize=8.2,
        color=PALETTE["reference"],
    )
    upper_axes[0].legend(loc="upper left", fontsize=8.3, frameon=False)

    draw_method_panel(
        lower_axes[0],
        "B",
        1,
        "one_point_five_error_rate",
        (0, 55),
        "At least 1.5-fold point error (%)",
    )
    draw_method_panel(
        lower_axes[1],
        "B",
        3,
        "one_point_five_error_rate",
        (0, 55),
        "At least 1.5-fold point error (%)",
    )
    fig.suptitle(
        "Arc 4 evidence: calibrated declaration versus magnitude error", fontsize=13, y=0.985
    )
    fig.text(
        0.01,
        0.012,
        "Upper: Goal 054 calibration-aware 95% intervals. Lower: unconditional "
        "matching-estimator error rates with archived intervals; h=1 is a null "
        "stress, h=3 an effect condition.",
        fontsize=8.2,
        color="0.35",
    )
    fig.savefig(OUT / "arc4_decision_and_magnitude.png", dpi=220, bbox_inches="tight")
    fig.savefig(OUT / "arc4_decision_and_magnitude.pdf", bbox_inches="tight")
    plt.close(fig)


def write_source_csv(rows: list[dict[str, str]]) -> Path:
    path = OUT / "arc4_figure_source_data.csv"
    fields = list(rows[0])
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_plotted_rows()
    source_csv = write_source_csv(rows)
    plot_figure1(rows)
    plot_figure2(rows)
    outputs = [
        OUT / "arc4_hidden_error_and_estimation.png",
        OUT / "arc4_hidden_error_and_estimation.pdf",
        OUT / "arc4_decision_and_magnitude.png",
        OUT / "arc4_decision_and_magnitude.pdf",
        source_csv,
    ]
    manifest = {
        "purpose": "Goal055 Arc4 reporting from frozen Goal051--054 summaries; no "
        "new fits, histories, calibration, or resampling",
        "script": "scripts/build_arc4_figures.py",
        "script_sha256": digest(Path(__file__).resolve()),
        "input_sha256": {name: digest(path) for name, path in SOURCE_FILES.items()},
        "source_rows": len(rows),
        "outputs": {path.name: digest(path) for path in outputs},
        "figure_inputs": {
            "figure1_panelA": "Goal051 cell_metrics.csv: B_h1, D20_h1, B100-A_h1; "
            "primary_rejection, H_primary, strict_false_effect",
            "figure1_panelB": "Goal053 bootstrap_summary.csv: "
            "mean_abs_log_h_error_change for E0/E06/B100-A h1/h3",
            "figure2_panelA": "Goal054 rule_rates.csv: adjusted_fullsup and "
            "constant_beta0 for E0/E06/B100-A/N100-A h1/h3",
            "figure2_panelB": "Goal054 error_metrics.csv: adjusted and constant "
            "unconditional one_point_five_error_rate for E0/E06/B100-A/N100-A h1/h3",
        },
        "uncertainty": {
            "goal051": "conditional Wilson 95% intervals from archived cell metrics",
            "goal053": "paired whole-block percentile 95% intervals, 2,000 draws, seed 2026092703",
            "goal054": "calibration-aware percentile 95% intervals, 2,000 draws, seed 2026092905",
        },
    }
    (OUT / "arc4_figures_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({"source_rows": len(rows), "outputs": [path.name for path in outputs]}))


if __name__ == "__main__":
    main()
