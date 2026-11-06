"""Check raw-arrival linear residuals on existing development geometry only."""

import importlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from latent_landscapes.goal001.spread import passable_edges
from latent_landscapes.goal006.spread import compute_contrast_spread

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
load_map = importlib.import_module("generate_history").load_map

rows = []
for archetype in ("connected", "corridor", "barrier"):
    directory = ROOT / "artifacts/sprint1/maps/development" / f"{archetype}-0"
    fixed, setup, _, _, _ = load_map(directory)
    arrival = compute_contrast_spread(
        fixed.landscape,
        1.0,
        edge_shocks=np.ones(len(passable_edges(fixed.landscape))),
        rho=1.0,
    ).arrival
    t = np.asarray(arrival)[setup.site_rows, setup.site_cols]
    a = setup.exposure_score[setup.site_rows, setup.site_cols]
    keep = np.isfinite(t) & np.isfinite(a)
    design = np.column_stack([np.ones(keep.sum()), a[keep]])
    residual = t[keep] - design @ np.linalg.lstsq(design, t[keep], rcond=None)[0]
    rows.append(
        {
            "development_map": f"{archetype}-0",
            "finite_frame_sites": int(keep.sum()),
            "spearman_correlation": float(spearmanr(t[keep], a[keep]).statistic),
            "raw_arrival_sd_days": float(t[keep].std()),
            "linear_residual_sd_days": float(residual.std()),
            "residual_sd_fraction": float(residual.std() / t[keep].std()),
        }
    )
output = {"geometry_only": True, "qualification_outcomes": False, "maps": rows}
Path(__file__).with_suffix(".json").write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps(output, indent=2))
