"""Claude normaliser check (thread 87, message 1903): how strongly the B100 whole-map
normaliser N = mean_map(exp(sqrt(log 2) z)) depends on the residual field at the 160 sites.
Run from the repository root: .venv/bin/python artifacts/paper1_planning_20261018/claude-normaliser-check.py
"""
import json
import math
import sys

import numpy as np

from latent_landscapes.misspecification_generator import build_field_sampler

ROOT = "artifacts/goal060_execution/audit-repair/public_inputs"
SEED = 1
DRAWS = 4000

map_a = np.load(f"{ROOT}/exposure.npz")["map_a"]
pub = np.load(f"{ROOT}/public_inputs.npz")
rows, cols = pub["site_rows"], pub["site_cols"]
sampler = build_field_sampler(map_a.shape)
rng = np.random.default_rng(SEED)
scale = math.sqrt(math.log(2.0))
log_n, site_mean = [], []
for _ in range(DRAWS):
    g = sampler.sample(rng)
    z = 0.7 * map_a + math.sqrt(0.51) * g
    log_n.append(math.log(float(np.exp(scale * z).mean())))
    site_mean.append(float(g[rows, cols].mean()))
log_n, site_mean = np.array(log_n), np.array(site_mean)
r = float(np.corrcoef(log_n, site_mean)[0, 1])
result = {
    "seed": SEED,
    "draws": DRAWS,
    "sd_log_normaliser": float(log_n.std()),
    "corr_log_normaliser_mean_site_field": r,
    "r_squared": r * r,
    "numpy": np.__version__,
    "python": sys.version.split()[0],
}
print(json.dumps(result, indent=1))
