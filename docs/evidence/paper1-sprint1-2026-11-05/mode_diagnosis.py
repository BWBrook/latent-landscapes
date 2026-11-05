"""Sprint 1 latent-mode diagnosis at the four frozen unresolved outer vectors.

Predeclared before any run (Claude, 5 November 2026; committed before outputs):

Start family, all serialized to the output:
  S00 zero.
  S01-S04 prior draws sigma*L*z, z ~ N(0, I), numpy default_rng(20261105 + k).
  S05-S08 the same draws scaled by 0.5.
  S09/S10 constant shifts +sigma and -sigma.
  S11 site-marginal start: per site, argmax over a 121-point grid on
      [-6 sigma, 6 sigma] of ell_i(eta0_i + v) - v^2 / (2 sigma^2 K_ii).
  S12 continuation start: the zero-start mode at log_sigma - 0.05.
Each start runs the unchanged production branch solver, then up to 20 extra
full Newton steps (backtracking, no cap) to tighten stationarity.

Classes (overlap allowed; none matched means unresolved):
  multimodal: two or more converged stationary points (score_inf <= 1e-8,
      positive-definite Hessian) with max |du| > 1e-3 and joint-objective
      difference > 1e-6.
  selector: the branch with the highest joint objective is not the branch
      with the highest Laplace value, by more than 1e-6.
  nonconvergence: the zero start fails strict stationarity after tightening,
      or its tightened Laplace value moves by more than 1e-6.
  conditioning: any converged mode has a non-positive-definite Hessian or
      condition number above 1e12.
  domain: any converged mode touches the evaluator domain or fails the
      4-SD proposal-support diagnostic.
The script does not change any fit, gate or frozen status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import cho_factor, cho_solve

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from run_development_profile import load_panel_data  # noqa: E402

from latent_landscapes.differentiable_likelihood import prepare_site_likelihood  # noqa: E402
from latent_landscapes.spatial_profile import SpatialProfileCriterion  # noqa: E402

PANEL = ROOT / "artifacts/paper1_development_challenge_20261101"
AUDIT = ROOT / "docs/evidence/paper1-procedure-review-2026-11-05/unresolved-audit.json"


def laplace_at(criterion, eta0, precision, curves, sigma, u):
    ell, score, curvature, _ = curves.evaluate(eta0 + u)
    gradient = score - precision @ u
    hessian = precision - np.diag(curvature)
    out = {
        "joint": float(np.sum(ell) - 0.5 * u @ precision @ u),
        "score_inf": float(np.max(np.abs(gradient))),
        "u_inf": float(np.max(np.abs(u))),
        "u_mean": float(np.mean(u)),
    }
    try:
        factor = cho_factor(hessian, lower=True)
        step = cho_solve(factor, gradient)
        eig = np.linalg.eigvalsh(hessian)
        c_chol = sigma * criterion._k_cholesky
        combined = criterion._identity - c_chol.T @ (curvature[:, None] * c_chol)
        cf = cho_factor(combined, lower=True)
        logdet_combined = float(2 * np.log(np.diag(cf[0])).sum())
        hinv_diag = np.diag(cho_solve(factor, criterion._identity))
        sd = np.sqrt(np.maximum(hinv_diag, 0))
        eta = eta0 + u
        lo, hi = curves.numerical_domain
        out |= {
            "pd": True,
            "cond": float(eig[-1] / eig[0]),
            "newton_step_inf": float(np.max(np.abs(step))),
            "decrement": math.sqrt(max(float(gradient @ step), 0.0)),
            "laplace": out["joint"] - 0.5 * logdet_combined,
            "half_logdet_combined": 0.5 * logdet_combined,
            "proposal_supported": bool(np.min(eta - 4 * sd) >= lo and np.max(eta + 4 * sd) <= hi),
            "bound_touch": bool(np.any(eta <= lo + 1e-8) or np.any(eta >= hi - 1e-8)),
        }
    except np.linalg.LinAlgError:
        out |= {"pd": False, "laplace": -math.inf}
    return out


def tighten(eta0, precision, curves, u, steps=20):
    lo, hi = curves.numerical_domain
    for _ in range(steps):
        ell, score, curvature, _ = curves.evaluate(eta0 + u)
        gradient = score - precision @ u
        if np.max(np.abs(gradient)) <= 1e-11:
            break
        try:
            step = cho_solve(cho_factor(precision - np.diag(curvature), lower=True), gradient)
        except np.linalg.LinAlgError:
            break
        current = float(np.sum(ell) - 0.5 * u @ precision @ u)
        scale = 1.0
        while scale >= 2.0**-20:
            cand = u + scale * step
            eta = eta0 + cand
            if np.all(eta > lo) and np.all(eta < hi):
                ce, cs, _, _ = curves.evaluate(eta)
                cv = float(np.sum(ce) - 0.5 * cand @ precision @ cand)
                if cv >= current - 1e-12 * max(1, abs(current)):
                    u = cand
                    break
            scale *= 0.5
        else:
            break
    return u


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
    out["S12"] = branch[0] if branch is not None else np.zeros(n)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=int, required=True, choices=range(4))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(AUDIT.read_text())
    profile = audit["profiles"][args.index]
    dataset = profile["dataset"].removesuffix("-B0")
    row = profile["highest_unresolved"]
    params, h = row["parameters"], float(row["h"])
    manifest = json.loads((PANEL / "panel-manifest.json").read_text())
    ns = argparse.Namespace(
        input_dir=PANEL / "archived-panel/public/legacy",
        observations=PANEL / f"archived-panel/datasets/{dataset}/observations.npz",
        arrival_bank=Path(manifest["banks"]["B0"]["raw"]),
        compressed_bank=Path(manifest["banks"]["B0"]["compressed"]),
    )
    data, identity = load_panel_data(ns)
    criterion = SpatialProfileCriterion(
        data,
        evaluator_factory=lambda hh, dsd: prepare_site_likelihood(
            data.observed, data.bank, hh, detection_sd=dsd
        ),
    )
    sigma = math.exp(params["log_sigma"])
    curves = criterion.curves(h, params["detection_sd"])
    eta0 = params["alpha"] + params["beta"] * data.exposure
    precision = criterion._k_inverse / sigma**2
    started = time.perf_counter()
    starts = starts_for(criterion, eta0, precision, curves, sigma, params, h)
    rows = []
    for name, start in starts.items():
        t0 = time.perf_counter()
        branch = criterion._mode_branch(eta0, precision, curves, start)
        record = {"start": name, "start_inf": float(np.max(np.abs(start)))}
        if branch is None:
            rows.append(record | {"branch": "failed"})
            continue
        u, value, score_inf, step_inf, dec, it, ev, msg = branch
        record |= {"production": laplace_at(criterion, eta0, precision, curves, sigma, u),
                   "production_message": msg, "production_evaluations": ev}
        ut = tighten(eta0, precision, curves, u.copy())
        record |= {"tight": laplace_at(criterion, eta0, precision, curves, sigma, ut),
                   "seconds": time.perf_counter() - t0, "u_tight": ut.tolist()}
        rows.append(record)
    cold = criterion.evaluate_positive(
        np.array([params["alpha"], params["beta"], params["log_sigma"], params["detection_sd"]]),
        fixed_h=h,
    )
    result = {
        "dataset": profile["dataset"],
        "search": profile["search"],
        "h": h,
        "parameters": params,
        "recorded_criterion": row["criterion"],
        "recorded_mode": row["mode"],
        "replayed_cold_criterion": cold.criterion,
        "replayed_cold_message": cold.message,
        "data_identity": identity,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "starts": {k: v.tolist() for k, v in starts.items()},
        "branches": rows,
        "seconds": time.perf_counter() - started,
    }
    args.output.write_text(json.dumps(result, indent=1) + "\n")


if __name__ == "__main__":
    main()
