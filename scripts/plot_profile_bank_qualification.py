"""Plot the observed diagnostic profiles and casewise bank LR differences."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLORS = {"B0": "#222222", "A": "#d55e00", "B": "#009e73", "AB": "#0072b2", "Adup": "#8b56a8"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile", action="append", required=True, help="HISTORY:ROLE=receipt.json"
    )
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    profiles = {}
    for item in args.profile:
        name, path = item.split("=", 1)
        history, role = name.split(":", 1)
        receipt = json.loads(Path(path).read_text())
        if receipt["status"] != "profile_numerically_resolved":
            raise ValueError("plot requires numerically resolved profiles")
        profiles.setdefault(history, {})[role] = receipt
    fig, axes = plt.subplots(2, len(profiles), figsize=(11, 7.5), squeeze=False, sharex="col")
    for column, (history, banks) in enumerate(profiles.items()):
        top, bottom = axes[:, column]
        if "B0" not in banks:
            raise ValueError("each history requires B0")
        baseline = banks["B0"]["anchors"]
        for role, receipt in banks.items():
            points = sorted(receipt["points"], key=lambda row: row["h"])
            maximum = receipt["free"]["criterion"]
            h = np.array([row["h"] for row in points])
            w = np.array([2 * (maximum - row["criterion"]) for row in points])
            style = "--" if role == "Adup" else "-"
            top.plot(h, w, color=COLORS[role], lw=1.5, linestyle=style, label=role)
            if role != "B0":
                anchors = receipt["anchors"]
                if [r["log_h"] for r in anchors] != [r["log_h"] for r in baseline]:
                    raise ValueError("anchor locations differ")
                differences = [r["w"] - b["w"] for r, b in zip(anchors, baseline, strict=True)]
                bottom.plot(
                    [r["h"] for r in anchors],
                    differences,
                    color=COLORS[role],
                    marker=".",
                    markersize=3,
                    lw=1,
                    linestyle=style,
                    label=role,
                )
        for cutoff in (1.0, 3.84, 6.63):
            top.axhline(cutoff, color="#bbbbbb", lw=0.6, zorder=0)
        for threshold in (-0.10, 0.10):
            bottom.axhline(threshold, color="#888888", lw=0.7, linestyle=":")
        bottom.axhline(0, color="#bbbbbb", lw=0.7)
        top.set_title(history.replace("BH3", "B_H3"), loc="left", fontweight="bold")
        top.set_ylabel("Profile LR  W(h)")
        bottom.set_ylabel("LR difference from B0")
        bottom.set_xlabel("Effect multiplier  h")
        top.set_ylim(bottom=0)
        for ax in (top, bottom):
            ax.set_xscale("log")
            ax.set_xlim(1, 30)
            ax.set_xticks([1, 2, 3, 5, 10, 20, 30], labels=["1", "2", "3", "5", "10", "20", "30"])
            ax.spines[["top", "right"]].set_visible(False)
        top.legend(frameon=False, ncol=3, fontsize=9)
    fig.suptitle("Arrival-bank sensitivity on two fixed development histories", fontsize=14)
    fig.text(
        0.5,
        0.015,
        "Uncalibrated diagnostic profiles; lines connect evaluated points. "
        "AB doubles bank size and changes pseudo-arrival mass.\n"
        "Lower panels: common 35-node comparisons; "
        "dotted lines mark the prespecified ±0.10 LR gate.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.065, 1, 0.96))
    for suffix in (".png", ".pdf"):
        path = args.output_prefix.with_suffix(suffix)
        if path.exists():
            raise FileExistsError(path)
        fig.savefig(path, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
