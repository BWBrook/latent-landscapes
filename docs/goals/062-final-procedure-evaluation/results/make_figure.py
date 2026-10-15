"""Render the reviewed Goal 062 probability summaries without recalculating them."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

directory = Path(__file__).resolve().parent
summary = json.loads((directory / "summary.json").read_text())
plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "pdf.fonttype": 42})
figure, axes = plt.subplots(2, 2, figsize=(8.8, 6.4), sharex=True, sharey=True)
styles = {"exact": ("#2367A0", "o", -0.07, "Exact exposure gradient"),
          "B100-A": ("#B85232", "s", 0.07, "B100-A residual field")}
metrics = [("outcomes", "declaration", "Declaration probability"),
           ("h_recovery", "within_1_5_fold", "Within-1.5-fold recovery")]
for column, mu in enumerate((0.001, 0.004)):
    axes[0, column].set_title(f"Mean background hazard = {mu:.3f}/day", pad=12)
    for row, (section, metric, label) in enumerate(metrics):
        axis = axes[row, column]
        for background, (colour, marker, offset, legend) in styles.items():
            cells = sorted((cell for cell in summary["cells"]
                            if cell["background"] == background
                            and cell["truth"]["mean_hazard_mu"] == mu),
                           key=lambda cell: cell["truth"]["effect_h"])
            x = [cell["truth"]["effect_h"] + offset for cell in cells]
            estimates = [cell[section][metric]["estimate"] for cell in cells]
            lower = [estimate-cell[section][metric]["interval"]["lower"]
                     for estimate, cell in zip(estimates, cells, strict=True)]
            upper = [cell[section][metric]["interval"]["upper"]-estimate
                     for estimate, cell in zip(estimates, cells, strict=True)]
            axis.errorbar(x, estimates, yerr=[lower, upper], linestyle="none",
                          marker=marker, color=colour, markersize=5, capsize=3,
                          linewidth=1.2, label=legend)
        axis.set(xlim=(0.6, 5.4), ylim=(-0.015, 1.035), xticks=(1, 3, 5))
        axis.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        axis.grid(axis="y", color="#D9D9D9", linewidth=0.5)
        axis.set_axisbelow(True)
        if column == 0:
            axis.set_ylabel(label)
        if row == 1:
            axis.set_xlabel("Generating effect multiplier h (h=1 is null)")
handles, labels = axes[0, 0].get_legend_handles_labels()
figure.legend(handles, labels, loc="upper center", ncol=2, frameon=False,
              bbox_to_anchor=(0.5, 0.995))
figure.tight_layout(rect=(0, 0.015, 1, 0.93), h_pad=2, w_pad=2)
figure.savefig(directory / "operating_probabilities.png", dpi=220)
figure.savefig(directory / "operating_probabilities.pdf")
plt.close(figure)
