"""The fixed thirteen-start latent audit, separated from its historical CLI.

Start design transplanted without numerical changes from
``docs/evidence/paper1-sprint1-2026-11-05/mode_diagnosis.py:121-148``.
The archived script remains immutable; only structured solver-result access
changes here. Audit thresholds and mode comparisons live in fit_dataset.py.
"""

from __future__ import annotations

import math

import numpy as np


def starts_for(criterion, eta0, precision, curves, sigma, params, h):
    n = criterion.site_count
    L = criterion._k_cholesky
    out = {"S00": np.zeros(n)}
    for k in range(1, 5):
        z = np.random.default_rng(20261105 + k).standard_normal(n)
        out[f"S{k:02d}"] = sigma * L @ z
        out[f"S{k + 4:02d}"] = 0.5 * sigma * L @ z
    out["S09"] = np.full(n, sigma)
    out["S10"] = np.full(n, -sigma)
    lo, hi = curves.numerical_domain
    grid = np.linspace(-6 * sigma, 6 * sigma, 121)
    kdiag = np.diag(criterion.data.covariance)
    best = np.full(n, -np.inf)
    arg = np.zeros(n)
    for v in grid:
        eta = np.clip(eta0 + v, lo + 1e-9, hi - 1e-9)
        ell, _, _, _ = curves.evaluate(eta)
        val = ell - v * v / (2 * sigma * sigma * kdiag)
        better = val > best
        best[better] = val[better]
        arg[better] = (eta - eta0)[better]
    out["S11"] = arg
    alt_sigma = math.exp(params["log_sigma"] - 0.05)
    alt_precision = criterion._k_inverse / (alt_sigma * alt_sigma)
    branch = criterion._mode_branch(eta0, alt_precision, curves, np.zeros(n))
    out["S12"] = branch.u if branch.success else np.zeros(n)
    return out
