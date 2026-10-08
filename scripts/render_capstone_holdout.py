#!/usr/bin/env python3
"""Render the released holdout comparison from saved, full-precision scores."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

MODELS = ("constant_free_h", "adjusted_free_h", "constant_h1", "adjusted_h1")
LABELS = ("Constant, free h", "Adjusted, free h", "Constant, h = 1", "Adjusted, h = 1")
COLORS = ("#A86A27", "#247B89", "#A86A27", "#247B89")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--totals", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with args.totals.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = {(f"case-{case:02d}", model) for case in range(4) for model in MODELS}
    assert len(rows) == 16 and {(r["case_id"], r["model"]) for r in rows} == expected
    assert all(r["status"] == "available" for r in rows)
    scores = {(r["case_id"], r["model"]): float(r["total_nats"]) for r in rows}
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.3))
    for case, ax in enumerate(axes.flat):
        case_id = f"case-{case:02d}"
        totals = [scores[case_id, model] for model in MODELS]
        differences = [value - max(totals) for value in totals]
        span = max(abs(min(differences)), 0.01)
        for y, (difference, color) in enumerate(zip(differences, COLORS, strict=True)):
            ax.plot([difference, 0], [y, y], color=color, linewidth=2, alpha=0.65)
            ax.scatter(difference, y, color=color, s=42, marker="o" if y < 2 else "s", zorder=3)
            label = "0 (best)" if difference == 0 else f"{difference:.8g}"
            ax.text(0.025 * span, y, label, ha="left", va="center", fontsize=9)
        ax.axvline(0, color="#67727A", linewidth=0.8, zorder=0)
        ax.set_yticks(range(4), LABELS)
        ax.set_ylim(3.6, -0.6)
        ax.set_xlim(-1.12 * span, 0.43 * span)
        ax.set_title(case_id, loc="left", fontweight="bold")
        ax.set_xlabel("Difference from best total log score (nats)")
        ax.set_xticks([tick for tick in ax.get_xticks() if -1.12 * span <= tick <= 0])
        ax.grid(axis="x", color="#E5E9EC", linewidth=0.7)
        ax.set_axisbelow(True)
    fig.suptitle("Held-out prediction from the frozen training fits", fontsize=15, y=0.99)
    fig.text(
        0.5,
        0.025,
        "40 sites in eight reserved clusters per case. Panel scales differ. "
        "Labels retain small score differences.\n"
        "The same case-level spatial process links training and holdout; no independent-site "
        "uncertainty interval is implied.",
        ha="center",
        va="bottom",
        fontsize=9,
        color="#45515B",
    )
    fig.tight_layout(rect=(0, 0.105, 1, 0.95), h_pad=2, w_pad=2)
    outputs = []
    for suffix in ("png", "pdf"):
        target = args.output / f"holdout_score_comparison.{suffix}"
        fig.savefig(target, dpi=180, facecolor="white")
        outputs.append(target)
    plt.close(fig)
    provenance = {
        "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "totals_sha256": hashlib.sha256(args.totals.read_bytes()).hexdigest(),
        "matplotlib_version": matplotlib.__version__,
        "outputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs},
    }
    (args.output / "figure-provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    main()
