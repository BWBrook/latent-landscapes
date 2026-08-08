"""Compact human-review artifacts for the Goal 016 information funnel."""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from latent_landscapes.goal004.observations import DETECTION_PROBABILITY, SURVEY_TIMES
from latent_landscapes.goal007 import benchmark as goal007

from .benchmark import FinalWaveScore, FunnelPerformance, Goal016Result

DEFAULT_OUTPUT_DIR = Path("artifacts/goal016_weak_contrast_information_funnel")
EXPECTED_FILES = (
    "config.json",
    "funnel_performance.csv",
    "final_wave_scores.csv",
    "method_comparison.csv",
    "summary.json",
    "review.md",
    "visuals/information_funnel.svg",
    "visuals/score_comparison.svg",
    "visuals/coefficient_maps.svg",
)

type CsvValue = str | int | float | bool | None
type CsvRow = dict[str, CsvValue]


def write_review_bundle(result: Goal016Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the deliberately small Goal 016 decision surface."""
    if result.outcome == "implementation_blocked" or not all(result.invariants.values()):
        raise ValueError("cannot write artifacts for a failed benchmark")
    target = Path(output_dir)
    if target.exists() and any(target.iterdir()):
        raise RuntimeError("refusing to overwrite a nonempty output directory")
    visuals = target / "visuals"
    visuals.mkdir(parents=True, exist_ok=True)

    _write_json(target / "config.json", _config_payload(result))
    _write_csv(target / "funnel_performance.csv", _performance_rows(result))
    _write_csv(target / "final_wave_scores.csv", _score_rows(result.final_wave_scores))
    _write_csv(target / "method_comparison.csv", _comparison_rows(result))
    _write_json(target / "summary.json", _summary_payload(result))
    (target / "review.md").write_text(_render_review(result), encoding="utf-8")
    _write_figure(visuals / "information_funnel.svg", _funnel_figure(result))
    _write_figure(visuals / "score_comparison.svg", _score_figure(result))
    _write_figure(visuals / "coefficient_maps.svg", _coefficient_figure(result))

    written = tuple(target / relative for relative in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 016 review bundle is incomplete")
    return written


def _config_payload(result: Goal016Result) -> dict[str, object]:
    config = result.config
    return {
        "goal": "016-weak-contrast-information-funnel",
        "run_mode": "production" if config.is_production else "reduced_smoke",
        "master_seed": config.master_seed,
        "partition_digest": result.partition_digest,
        "wave_is_independent_unit": True,
        "eta_values": list(config.eta_values),
        "rho_values": list(config.rho_values),
        "survey_times": list(SURVEY_TIMES),
        "visits_per_site_time": 2,
        "known_detection_probability": DETECTION_PROBABILITY,
        "integration_bank_size": config.integration_bank_size,
        "train_per_class": config.train_per_class,
        "validation_per_class": config.validation_per_class,
        "null_calibration_count": config.null_calibration_count,
        "test_per_class": config.test_per_class,
        "ridge_alphas": list(config.alphas),
        "common_threshold": "maximum rho-specific empirical 95th null quantile",
        "practical_use_rule": (
            "power Wilson lower bound > 0.80 and false-positive rate <= 0.06 at every rho"
        ),
        "site_count": len(result.site_ids),
        "positive_cell_count": result.positive_cell_count,
        "invariants": result.invariants,
    }


def _performance_rows(result: Goal016Result) -> list[CsvRow]:
    return [
        {
            "representation": row.representation,
            "method": row.method,
            "rho": row.rho,
            "selected_alpha": row.selected_alpha,
            "validation_auc": row.validation_auc,
            "threshold": row.threshold,
            "final_auc": row.final_auc,
            "balanced_accuracy": row.balanced_accuracy,
            "false_positive_count": row.false_positive_count,
            "false_positive_rate": row.false_positive_rate,
            "false_positive_lower": row.false_positive_interval.lower,
            "false_positive_upper": row.false_positive_interval.upper,
            "power_count": row.power_count,
            "power": row.power,
            "power_lower": row.power_interval.lower,
            "power_upper": row.power_interval.upper,
            "null_count": row.null_count,
            "alternative_count": row.alternative_count,
            "practically_useful": row.practically_useful,
        }
        for row in result.funnel_performance
    ]


def _score_rows(scores: Sequence[FinalWaveScore]) -> list[CsvRow]:
    return [
        {
            "method": row.method,
            "truth_eta": row.truth_eta,
            "truth_rho": row.truth_rho,
            "wave_index": row.wave_index,
            "score": row.score,
            "threshold": row.threshold,
            "score_margin": row.score - row.threshold,
            "claims_nonzero_contrast": row.claims_nonzero_contrast,
        }
        for row in scores
    ]


def _comparison_rows(result: Goal016Result) -> list[CsvRow]:
    classifier = _rows_for(result, "sample_sites_imperfect_detection")
    composite = _rows_for(result, "current_composite_statistic")
    return [
        {
            "rho": rho,
            "classifier_auc": classifier[rho].final_auc,
            "composite_auc": composite[rho].final_auc,
            "auc_difference_classifier_minus_composite": (
                classifier[rho].final_auc - composite[rho].final_auc
            ),
            "classifier_power": classifier[rho].power,
            "composite_power": composite[rho].power,
            "power_difference_classifier_minus_composite": (
                classifier[rho].power - composite[rho].power
            ),
            "classifier_false_positive_rate": classifier[rho].false_positive_rate,
            "composite_false_positive_rate": composite[rho].false_positive_rate,
            "classifier_practically_useful": classifier[rho].practically_useful,
            "composite_practically_useful": composite[rho].practically_useful,
        }
        for rho in result.config.rho_values
    ]


def _rows_for(result: Goal016Result, representation: str) -> dict[float, FunnelPerformance]:
    return {
        row.rho: row for row in result.funnel_performance if row.representation == representation
    }


def _summary_payload(result: Goal016Result) -> dict[str, object]:
    classifier = _rows_for(result, "sample_sites_imperfect_detection")
    composite = _rows_for(result, "current_composite_statistic")
    interpretation = result.outcome if result.config.is_production else "non_scientific_smoke"
    return {
        "goal": "016-weak-contrast-information-funnel",
        "outcome": result.outcome,
        "scientific_interpretation": interpretation,
        "all_invariants_pass": all(result.invariants.values()),
        "classifier_useful_at_every_rho": all(
            classifier[rho].practically_useful for rho in result.config.rho_values
        ),
        "composite_useful_at_every_rho": all(
            composite[rho].practically_useful for rho in result.config.rho_values
        ),
        "classifier_power_by_rho": {
            str(rho): classifier[rho].power for rho in result.config.rho_values
        },
        "composite_power_by_rho": {
            str(rho): composite[rho].power for rho in result.config.rho_values
        },
        "note": (
            "Reduced-smoke metrics are implementation checks only."
            if not result.config.is_production
            else "Final metrics use sealed independent waves."
        ),
    }


def _render_review(result: Goal016Result) -> str:
    mode = "production campaign" if result.config.is_production else "non-scientific reduced smoke"
    lines = [
        "# Goal 016: Weak-Contrast Information Funnel",
        "",
        f"Run mode: **{mode}**",
        "",
        "## Decision",
        "",
        f"Outcome: `{result.outcome}`.",
        "",
        (
            "The reduced smoke checks implementation only; it must not be interpreted "
            "as scientific evidence."
        )
        if not result.config.is_production
        else _plain_interpretation(result.outcome),
        "",
        "## Information funnel",
        "",
        "| Representation | rho | AUC | false-positive rate | power | useful |",
        "| --- | ---: | ---: | ---: | ---: | :---: |",
    ]
    lines.extend(
        "| {representation} | {rho:g} | {auc:.3f} | {fpr:.3f} | {power:.3f} | {useful} |".format(
            representation=row.representation,
            rho=row.rho,
            auc=row.final_auc,
            fpr=row.false_positive_rate,
            power=row.power,
            useful="yes" if row.practically_useful else "no",
        )
        for row in result.funnel_performance
    )
    lines.extend(
        [
            "",
            "## Reading the figures",
            "",
            (
                "The funnel figure shows where discrimination is retained or lost. "
                "The score figure compares"
            ),
            (
                "the ridge wave classifier with the current sitewise statistic on the "
                "same final histories."
            ),
            "Coefficient maps are descriptive linear weights, not causal ecological effects.",
            "",
        ]
    )
    return "\n".join(lines)


def _plain_interpretation(outcome: str) -> str:
    return {
        "intrinsic_weak_contrast_overlap": (
            "Even complete arrival maps do not reliably separate weak contrast."
        ),
        "spatial_sampling_information_loss": (
            "The complete map contains signal, but the 160 sampled sites lose it."
        ),
        "temporal_detection_information_loss": (
            "Exact sampled arrivals contain signal, but scheduled occupancy or detection "
            "histories lose it."
        ),
        "information_lost_in_current_statistic": (
            "Imperfect histories retain useful signal, but the current sitewise statistic "
            "discards it."
        ),
        "information_retained_support_target_limited": (
            "Both imperfect-history methods retain useful class information; the earlier "
            "support target was limiting."
        ),
    }.get(outcome, "The production outcome requires review.")


def _funnel_figure(result: Goal016Result) -> Figure:
    order = (
        "global_time_only",
        "full_map_centered_log",
        "full_map_ranks",
        "sample_sites_centered_log",
        "sample_sites_perfect_occupancy",
        "sample_sites_imperfect_detection",
        "current_composite_statistic",
    )
    labels = (
        "time",
        "full map",
        "map ranks",
        "160 sites",
        "occupancy",
        "detections",
        "current score",
    )
    with _figure_style():
        figure, axes = plt.subplots(2, 1, figsize=(10.5, 7.2), sharex=True, layout="constrained")
        colors = {0.5: "#0072B2", 1.0: "#009E73", 2.0: "#D55E00"}
        for row in result.funnel_performance:
            x = order.index(row.representation)
            axes[0].scatter(x, row.final_auc, color=colors[row.rho], s=45)
            axes[1].scatter(x, row.power, color=colors[row.rho], s=45)
        axes[0].axhline(0.5, color="#777777", linestyle="--", linewidth=1)
        axes[1].axhline(0.8, color="#777777", linestyle="--", linewidth=1)
        axes[0].set_ylabel("Final AUC")
        axes[1].set_ylabel("Power at conservative threshold")
        axes[1].set_xticks(range(len(order)), labels, rotation=25, ha="right")
        axes[0].set_ylim(0.45, 1.02)
        axes[1].set_ylim(-0.02, 1.02)
        axes[0].set_title("Weak-contrast information funnel")
        handles = [
            Line2D([], [], marker="o", linestyle="", color=color, label=f"rho = {rho:g}")
            for rho, color in colors.items()
        ]
        axes[0].legend(handles=handles, loc="lower left", ncols=3)
        return figure


def _score_figure(result: Goal016Result) -> Figure:
    methods = ("ridge_wave_classifier", "profiled_sitewise_composite")
    titles = ("Ridge classifier", "Current sitewise composite score")
    with _figure_style():
        figure, axes_array = plt.subplots(2, 1, figsize=(10.5, 7.5), layout="constrained")
        axes = np.atleast_1d(axes_array)
        for axis, method, title in zip(axes, methods, titles, strict=True):
            positions: list[float] = []
            values: list[list[float]] = []
            colors: list[str] = []
            tick_positions: list[float] = []
            for rho_index, rho in enumerate(result.config.rho_values):
                base = float(rho_index * 3)
                tick_positions.append(base + 0.5)
                for eta, offset, color in ((0.0, 0.0, "#999999"), (0.5, 1.0, "#0072B2")):
                    margins = [
                        row.score - row.threshold
                        for row in result.final_wave_scores
                        if row.method == method and row.truth_rho == rho and row.truth_eta == eta
                    ]
                    positions.append(base + offset)
                    values.append(margins)
                    colors.append(color)
            boxes = axis.boxplot(values, positions=positions, widths=0.7, patch_artist=True)
            for patch, color in zip(boxes["boxes"], colors, strict=True):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            axis.axhline(0.0, color="#222222", linewidth=1)
            axis.set_xticks(tick_positions, [f"rho = {rho:g}" for rho in result.config.rho_values])
            axis.set_ylabel("Score minus threshold")
            axis.set_title(title)
        handles = [
            mpl.patches.Patch(color="#999999", label="eta = 0"),
            mpl.patches.Patch(color="#0072B2", label="eta = 0.5"),
        ]
        axes[0].legend(handles=handles, loc="upper left", ncols=2)
        return figure


def _coefficient_figure(result: Goal016Result) -> Figure:
    fixed = goal007.build_fixed_inputs()
    positive_mask = fixed.landscape.passable & (fixed.landscape.source_zone == "")
    coefficient_map = np.full(fixed.landscape.shape, np.nan, dtype=np.float64)
    coefficient_map[positive_mask] = result.full_map_coefficient
    rows = np.asarray([site.row for site in fixed.design.sites], dtype=np.int64)
    cols = np.asarray([site.col for site in fixed.design.sites], dtype=np.int64)
    site_importance = np.linalg.norm(result.detection_coefficient, axis=1)
    time_weight = result.detection_coefficient.mean(axis=0)
    with _figure_style():
        figure, axes_array = plt.subplots(1, 3, figsize=(14, 4.6), layout="constrained")
        axes = np.atleast_1d(axes_array)
        map_limit = float(np.nanmax(np.abs(coefficient_map)))
        image = axes[0].imshow(
            coefficient_map,
            cmap="RdBu_r",
            vmin=-map_limit,
            vmax=map_limit,
            interpolation="nearest",
        )
        figure.colorbar(image, ax=axes[0], shrink=0.75, label="standardised ridge weight")
        axes[0].set_title("Complete-map spatial weights")
        axes[0].set_axis_off()
        axes[1].imshow(fixed.landscape.quality, cmap="Greys", alpha=0.25, interpolation="nearest")
        points = axes[1].scatter(cols, rows, c=site_importance, cmap="viridis", s=30)
        figure.colorbar(points, ax=axes[1], shrink=0.75, label="weight magnitude")
        axes[1].set_title("Detection-history site importance")
        axes[1].set_axis_off()
        axes[2].bar([str(time) for time in SURVEY_TIMES], time_weight, color="#009E73")
        axes[2].axhline(0.0, color="#222222", linewidth=1)
        axes[2].set_xlabel("Survey time")
        axes[2].set_ylabel("Mean signed ridge weight")
        axes[2].set_title("Detection-history timing weights")
        return figure


def _write_csv(path: Path, rows: Sequence[CsvRow]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty table: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_figure(path: Path, figure: Figure) -> None:
    try:
        figure.savefig(path, format="svg", metadata={"Date": None})
    finally:
        plt.close(figure)


def _figure_style() -> Any:
    return plt.rc_context(
        {
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 10,
            "svg.fonttype": "none",
            "svg.hashsalt": "latent-landscapes-goal016",
        }
    )
