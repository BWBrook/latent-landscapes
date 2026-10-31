from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path.cwd()
ARCHIVE = ROOT / "docs/evidence/paper1-direct-profile-2026-10-31"
CASES = [
    ("BH3-trust-full35-order192", "B_H3: archived cell 09"),
    ("H3-trust-full35-order192", "H3: archived cell 04"),
]
COLORS = {"positive_sigma": "#007c91", "sigma_zero": "#ba4a22"}
LABELS = {"positive_sigma": "Positive spatial variance", "sigma_zero": "Zero spatial variance"}


def main():
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for ax, (name, title) in zip(axes, CASES, strict=True):
        receipt = json.loads((ARCHIVE / "benchmark" / f"{name}.json").read_text())
        profile = receipt["profile"]
        for family in COLORS:
            rows = [row for row in profile["grid_statuses"] if row["family"] == family]
            accepted = sorted(
                (row for row in rows if row["status"] == "resolved"), key=lambda row: row["h"]
            )
            ax.plot(
                [row["h"] for row in accepted],
                [row["profile_lr_from_global_max"] for row in accepted],
                ".-",
                color=COLORS[family],
                lw=1.2,
                ms=4,
                label=f"{LABELS[family]} ({len(accepted)}/{len(rows)})",
            )
        ax.scatter(
            [profile["best"]["h"]],
            [0],
            marker="D",
            s=30,
            color="#242424",
            zorder=4,
            label="Free-effect optimum",
        )
        ax.set(
            xscale="log",
            xlabel="Effect multiplier h",
            ylabel="Profile LR (uncalibrated)",
            title=title,
        )
        ax.set_xticks([1, 2, 3, 5, 10, 20, 30], ["1", "2", "3", "5", "10", "20", "30"])
        ax.set_xlim(1, 30)
        ax.grid(alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle("Direct likelihood: 35-node development profiles", fontsize=13)
    fig.savefig(ARCHIVE / "profile-meshes.png", dpi=200)
    fig.savefig(ARCHIVE / "profile-meshes.pdf")
    plt.close(fig)


if __name__ == "__main__":
    main()
