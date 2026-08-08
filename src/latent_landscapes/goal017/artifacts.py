"""Compact review artifacts for the Goal 017 reconciliation."""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from .reconciliation import (
    DecisionTargetSummary,
    Goal017Result,
    PairedDisagreement,
    ProfileMechanics,
)

DEFAULT_OUTPUT_DIR = Path("artifacts/goal017_weak_contrast_decision_target_reconciliation")
EXPECTED_FILES = (
    "decision_target_summary.csv",
    "paired_disagreement.csv",
    "representative_profile_mechanics.csv",
    "summary.json",
    "review.md",
    "visuals/decision_target_comparison.svg",
    "visuals/representative_profiles.svg",
)


def write_review_bundle(result: Goal017Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the seven-file human decision surface."""
    target = Path(output_dir)
    if target.exists() and any(target.iterdir()):
        raise RuntimeError("refusing to overwrite a nonempty output directory")
    visuals = target / "visuals"
    visuals.mkdir(parents=True, exist_ok=True)
    _write_csv(target / "decision_target_summary.csv", result.decision_summaries)
    _write_csv(target / "paired_disagreement.csv", result.paired_disagreements)
    _write_csv(target / "representative_profile_mechanics.csv", result.profile_mechanics)
    (target / "summary.json").write_text(
        json.dumps(_summary(result), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    _save_figure(visuals / "decision_target_comparison.svg", _decision_figure(result))
    _save_figure(visuals / "representative_profiles.svg", _profile_figure(result))
    written = tuple(target / relative for relative in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 017 review bundle is incomplete")
    return written


type CsvRecord = DecisionTargetSummary | PairedDisagreement | ProfileMechanics


def _write_csv(path: Path, rows: Sequence[CsvRecord]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty table: {path.name}")
    serialized = [asdict(row) for row in rows]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(serialized[0]))
        writer.writeheader()
        writer.writerows(serialized)


def _summary(result: Goal017Result) -> dict[str, object]:
    full = [row for row in result.decision_summaries if row.bank_variant == "full"]
    return {
        "goal": "017-weak-contrast-decision-target-reconciliation",
        "outcome": result.outcome,
        "goal016_outcome": result.goal016_outcome,
        "campaigns_are_wave_paired": False,
        "weak_truth_count": len(full),
        "mean_mle_exact_rate": float(np.mean([row.mle_exact_rate for row in full])),
        "mean_mle_nonzero_rate": float(np.mean([row.mle_nonzero_rate for row in full])),
        "mean_support_excludes_zero_rate": float(
            np.mean([row.support_excludes_zero_rate for row in full])
        ),
        "mean_binary_power": float(np.mean([row.binary_power for row in full])),
        "half_bank_maximum_rate_difference": result.half_bank_maximum_rate_difference,
        "representative_profiles_are_illustrative": True,
    }


def _review(result: Goal017Result) -> str:
    full = [row for row in result.decision_summaries if row.bank_variant == "full"]
    lines = [
        "# Goal 017: Weak-Contrast Decision-Target Reconciliation",
        "",
        "## Bottom line",
        "",
        f"Outcome: `{result.outcome}`.",
        "",
        (
            "The apparent contradiction is not a failure of the data or of the current "
            "sitewise statistic. The three summaries answer different scientific questions."
        ),
        "",
        (
            "Goal 012 and Goal 016 are independent campaigns. Their rates can be compared "
            "at the same generating rho values, but their individual waves cannot be "
            "cross-tabulated."
        ),
        "",
        "## What the evidence says",
        "",
        (
            "| Generating rho | MLE exactly 0.5 | MLE nonzero | 95% support excludes "
            "zero | Binary power | Binary false-positive rate |"
        ),
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in full:
        lines.append(
            f"| {row.truth_rho:g} | {row.mle_exact_rate:.3f} | {row.mle_nonzero_rate:.3f} "
            f"| {row.support_excludes_zero_rate:.3f} | {row.binary_power:.3f} "
            f"| {row.binary_false_positive_rate:.3f} |"
        )
    lines.extend(
        [
            "",
            (
                "A nonzero contrast is the best-fitting explanation for nearly every Goal 012 "
                "history, even when the fitted grid value is 0.25 or 0.75 rather than exactly 0.5."
            ),
            (
                "The Goal 016 binary test asks only whether the evidence crosses a calibrated "
                "eta=0 versus eta=0.5 decision threshold. The continuous support region asks the "
                "harder question of which values remain plausible after rho and intermediate eta "
                "values are allowed and a joint empirical coverage cutoff is applied."
            ),
            "",
            "## Why the continuous region is wider",
            "",
            (
                "| Generating rho | Fitted eta | log score: eta 0.5 minus eta 0 | LR "
                "against zero, rho profiled | LR against zero, rho fixed* | Calibrated "
                "95% cutoff |"
            ),
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for profile_row in result.profile_mechanics:
        lines.append(
            f"| {profile_row.truth_rho:g} | {profile_row.fitted_eta:g} | "
            f"{profile_row.profile_log_score_eta_0_5_minus_eta_0:.2f} | "
            f"{profile_row.profiled_zero_lr:.2f} | {profile_row.rho_fixed_zero_lr:.2f} | "
            f"{profile_row.calibrated_cutoff:.2f} |"
        )
    lines.extend(
        [
            "",
            (
                "The cutoffs are empirical Goal 012 calibration cutoffs, not a standard textbook "
                "chi-square threshold. They are 27 to 62 likelihood-ratio units in these cells. "
                "That protects the intended coverage under the sitewise composite criterion, but "
                "it also makes the resulting regions deliberately broad."
            ),
            (
                "In two representative histories, allowing rho to vary substantially reduces the "
                "likelihood-ratio distance from zero. Two profiles also fit eta=0.25 rather than "
                "the exact generating eta=0.5. Thus rho-eta trade-off and intermediate contrast "
                "values both widen the continuous question; neither implies that contrast is "
                "absent."
            ),
            (
                "* The fixed-rho column is descriptive only. A formal known-rho support procedure "
                "would need its own calibration cutoff."
            ),
            "",
            (
                "Those three profiles are illustrative single histories, not estimates of how "
                "often the mechanism occurs. The paired Goal 012 table supplies the frequency "
                "evidence."
            ),
            "",
            "## Decision",
            "",
            (
                "For this benchmark, resistance contrast is detectably present but only moderately "
                "precise as a continuous parameter. We should henceforth name binary contrast "
                "detection and continuous parameter precision separately. There is no current "
                "evidence-based reason to replace the likelihood before deciding which inferential "
                "target the paper actually requires."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _decision_figure(result: Goal017Result) -> Figure:
    rows = [row for row in result.decision_summaries if row.bank_variant == "full"]
    x = np.arange(len(rows), dtype=float)
    width = 0.2
    figure, axis = plt.subplots(figsize=(9.2, 4.8), constrained_layout=True)
    series = (
        ("MLE exactly 0.5", [row.mle_exact_rate for row in rows], "#3B6FB6"),
        ("MLE nonzero", [row.mle_nonzero_rate for row in rows], "#2A9D8F"),
        ("95% support excludes zero", [row.support_excludes_zero_rate for row in rows], "#E9C46A"),
        ("Binary-test power*", [row.binary_power for row in rows], "#E76F51"),
    )
    for index, (label, values, colour) in enumerate(series):
        axis.bar(x + (index - 1.5) * width, values, width, label=label, color=colour)
    axis.set_xticks(x, [f"rho = {row.truth_rho:g}" for row in rows])
    axis.set_ylim(0.0, 1.05)
    axis.set_ylabel("Fraction of independent histories")
    axis.set_title("Weak contrast: three inferential targets")
    axis.legend(frameon=False, ncols=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    axis.text(
        0.0,
        -0.28,
        (
            "* Binary power is from an independent Goal 016 campaign; the other bars share "
            "Goal 012 waves."
        ),
        transform=axis.transAxes,
        fontsize=8.5,
    )
    return figure


def _profile_figure(result: Goal017Result) -> Figure:
    figure, axes = plt.subplots(1, 3, figsize=(11.4, 3.8), sharey=True, constrained_layout=True)
    for axis, curve in zip(axes, result.profile_curves, strict=True):
        axis.plot(curve.eta_values, curve.likelihood_ratio_values, color="#3B6FB6", marker="o")
        axis.axhline(curve.calibrated_cutoff, color="#C44E52", linestyle="--", label="95% cutoff")
        axis.axvline(0.5, color="#2A9D8F", linestyle=":", label="generating eta")
        axis.scatter([0.0], [curve.likelihood_ratio_values[0]], color="#222222", zorder=3)
        axis.set_title(f"Generating rho = {curve.truth_rho:g}\nMLE eta = {curve.fitted_eta:g}")
        axis.set_xlabel("Resistance contrast eta")
        axis.set_ylim(0.0, max(item.calibrated_cutoff for item in result.profile_curves) * 1.25)
    axes[0].set_ylabel("Likelihood-ratio distance from fitted maximum")
    axes[-1].legend(frameon=False, fontsize=8)
    return figure


def _save_figure(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", metadata={"Date": None})
    plt.close(figure)
