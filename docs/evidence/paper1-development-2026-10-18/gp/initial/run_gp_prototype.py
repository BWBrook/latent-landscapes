#!/usr/bin/env python3
"""Bounded development prototype for the Paper 1 sampled-site GP criterion.

This script is intentionally an ordinary diagnostic.  It uses the released
arrival bank and observation packages, and writes only diagnostic JSON below
``artifacts/paper1_planning_20261018/gp-prototype``.  It is not a production
fit or a qualification gate.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize
from scipy.special import logsumexp

from latent_landscapes import capstone_qualification as qualification
from latent_landscapes import preinvasion_likelihood as likelihood


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PUBLIC = ROOT / "artifacts/goal060_execution/audit-repair/public_inputs"
BANK_PATH = ROOT / "artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy"
OBS_ROOT = ROOT / "artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation"
COMPRESSED_PATH = ROOT / "artifacts/goal060_execution/audit-repair/mechanical/compressed-bank.npz"
GRID = np.linspace(-12.0, -3.0, 61)
MEAN_DETECTION = 0.65
SD_MAX = math.sqrt(MEAN_DETECTION * (1.0 - MEAN_DETECTION))
SEED = 20261018


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(v) for v in value]
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(jsonable(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


class CurveDomainError(RuntimeError):
    """Raised when a mode or importance draw leaves the interpolation grid."""


@dataclass
class Curves:
    grid: np.ndarray
    values: np.ndarray
    first: list[CubicSpline]
    second: list[CubicSpline]
    h: float
    detection_sd: float
    exact_nodes: list[int]
    series_bounds: list[float]
    build_seconds: float
    direct_check: dict[str, Any] = field(default_factory=dict)

    def evaluate(self, eta: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if eta.shape != (self.values.shape[0],):
            raise ValueError("eta must have one value per training site")
        lo, hi = float(self.grid[0]), float(self.grid[-1])
        if np.any(eta < lo) or np.any(eta > hi):
            raise CurveDomainError(
                f"mode touched interpolation bounds: [{float(eta.min()):g}, {float(eta.max()):g}] "
                f"outside [{lo:g}, {hi:g}]"
            )
        ell = np.asarray([s(eta[i]) for i, s in enumerate(self.first)], dtype=float)
        der = np.asarray([s(eta[i], 1) for i, s in enumerate(self.first)], dtype=float)
        curv = np.asarray([s(eta[i], 2) for i, s in enumerate(self.first)], dtype=float)
        return ell, der, curv


@dataclass
class GPData:
    bank: likelihood.CompressedBank
    observed: likelihood.PreInvasionObservations
    A: np.ndarray
    coords: np.ndarray
    K: np.ndarray
    case: str
    site_count: int


@dataclass
class ModeResult:
    u: np.ndarray
    value: float
    gradient_inf: float
    iterations: int
    evaluations: int
    success: bool
    message: str
    pd_ok: bool
    logdet_C: float
    logdet_H: float
    H: np.ndarray | None
    Cinv: np.ndarray | None
    eta_min: float = math.nan
    eta_max: float = math.nan
    curve_bound_touch: bool = False


class Criterion:
    def __init__(self, data: GPData):
        self.data = data
        self.curve_cache: dict[tuple[float, float], Curves] = {}
        self.stats = {"curve_builds": 0, "curve_seconds": 0.0, "mode_calls": 0, "pd_failures": 0}
        self.failures: list[str] = []

    def curves(self, h: float, detection_sd: float) -> Curves:
        key = (round(float(h), 8), round(float(detection_sd), 8))
        if key in self.curve_cache:
            return self.curve_cache[key]
        started = time.perf_counter()
        values = np.empty((self.data.site_count, len(GRID)), dtype=float)
        exact_nodes: list[int] = []
        bounds: list[float] = []
        for j, loglambda in enumerate(GRID):
            hazards = np.full(self.data.site_count, math.exp(float(loglambda)))
            x_max = float(np.max(10.0 * hazards * (h - 1.0)))
            exact = x_max > likelihood.SERIES_DOMAIN * (1.0 + 1e-14)
            if exact:
                exact_nodes.append(j)
            integration = likelihood.build_integration(
                self.data.bank,
                [h],
                hazards,
                prey_times=self.data.observed.prey_times,
                cohort_start=self.data.observed.cohort_start,
                exact=exact,
                enforce_domain=not exact,
            )
            scores = likelihood.score_observations(
                self.data.observed, integration, detection_sd=detection_sd
            )
            values[:, j] = scores.joint_loglikelihood[0, 0]
            bounds.append(float(integration.series_bound))
        first = [
            CubicSpline(GRID, values[i], bc_type="natural")
            for i in range(self.data.site_count)
        ]
        second = [s.derivative(2) for s in first]
        curves = Curves(
            GRID.copy(), values, first, second, h, detection_sd, exact_nodes, bounds,
            time.perf_counter() - started,
        )
        self.stats["curve_builds"] += 1
        self.stats["curve_seconds"] += curves.build_seconds
        self.curve_cache[key] = curves
        return curves

    def check_curves(self, curves: Curves, count: int = 6) -> dict[str, Any]:
        mids = (curves.grid[:-1] + curves.grid[1:]) / 2.0
        chosen = np.linspace(0, len(mids) - 1, count, dtype=int)
        errors: list[float] = []
        for j in chosen:
            loglambda = float(mids[j])
            hazards = np.full(self.data.site_count, math.exp(loglambda))
            x_max = float(np.max(10.0 * hazards * (curves.h - 1.0)))
            exact = x_max > likelihood.SERIES_DOMAIN * (1.0 + 1e-14)
            integration = likelihood.build_integration(
                self.data.bank, [curves.h], hazards,
                prey_times=self.data.observed.prey_times,
                cohort_start=self.data.observed.cohort_start,
                exact=exact, enforce_domain=not exact,
            )
            direct = likelihood.score_observations(
                self.data.observed, integration, detection_sd=curves.detection_sd
            ).joint_loglikelihood[0, 0]
            interp = np.asarray([s(loglambda) for s in curves.first])
            errors.append(float(np.max(np.abs(interp - direct))))
        result = {
            "midpoint_count": len(chosen),
            "max_abs_loglik_error": max(errors) if errors else 0.0,
            "errors": errors,
            "exact_grid_nodes": curves.exact_nodes,
            "max_series_remainder_bound": max(curves.series_bounds),
        }
        curves.direct_check = result
        return result

    def mode(
        self, alpha: float, beta: float, sigma: float, h: float, detection_sd: float
    ) -> ModeResult:
        self.stats["mode_calls"] += 1
        n = self.data.site_count
        curves = self.curves(h, detection_sd)
        eta0 = np.full(n, alpha) + beta * self.data.A
        if sigma == 0.0:
            ell, der, curv = curves.evaluate(eta0)
            # The latent field is absent; the Hessian is only diagnostic here.
            value = float(np.sum(ell))
            return ModeResult(
                np.zeros(n), value, float(np.max(np.abs(der))), 0, 1, True,
                "sigma=0 analytic limit", True, 0.0,
                float(-np.sum(np.log(np.maximum(-curv, 1e-300)))), None, None,
                float(np.min(eta0)), float(np.max(eta0)),
                bool(np.any((eta0 <= curves.grid[0] + 1e-8) | (eta0 >= curves.grid[-1] - 1e-8))),
            )
        C = (sigma * sigma) * self.data.K
        try:
            cfac = cho_factor(C, lower=True, check_finite=True)
            Cinv = cho_solve(cfac, np.eye(n), check_finite=True)
            logdet_C = float(2.0 * np.sum(np.log(np.diag(cfac[0]))))
        except np.linalg.LinAlgError as exc:
            self.stats["pd_failures"] += 1
            return ModeResult(np.zeros(n), -math.inf, math.inf, 0, 0, False, f"C not PD: {exc}", False, math.nan, math.nan, None, None)

        def objective(u: np.ndarray) -> tuple[float, np.ndarray]:
            ell, der, _ = curves.evaluate(eta0 + u)
            grad = der - Cinv @ u
            return float(-(np.sum(ell) - 0.5 * u @ Cinv @ u)), -grad

        try:
            # Trial steps are kept inside the explicitly evaluated curve domain;
            # interpolation is never silently extrapolated.
            inner_bounds = [
                (float(curves.grid[0] - eta0[i] + 1e-10),
                 float(curves.grid[-1] - eta0[i] - 1e-10))
                for i in range(n)
            ]
            fit = minimize(objective, np.zeros(n), jac=True, method="L-BFGS-B",
                           bounds=inner_bounds,
                           options={"maxiter": 160, "ftol": 1e-10, "gtol": 1e-7, "maxls": 30})
            u = np.asarray(fit.x, dtype=float)
            ell, der, curv = curves.evaluate(eta0 + u)
            H = Cinv - np.diag(curv)
            hfac = cho_factor(H, lower=True, check_finite=True)
            logdet_H = float(2.0 * np.sum(np.log(np.diag(hfac[0]))))
            mode_value = float(np.sum(ell) - 0.5 * u @ Cinv @ u)
            grad_inf = float(np.max(np.abs(der - Cinv @ u)))
            pd_ok = bool(np.all(np.isfinite(H)))
            if not pd_ok:
                raise np.linalg.LinAlgError("nonfinite Laplace precision")
            return ModeResult(
                u, mode_value, grad_inf, int(fit.nit), int(fit.nfev), bool(fit.success),
                str(fit.message), True, logdet_C, logdet_H, H, Cinv,
                float(np.min(eta0 + u)), float(np.max(eta0 + u)),
                bool(np.any(np.isclose(eta0 + u, curves.grid[0], atol=1e-7)
                            | np.isclose(eta0 + u, curves.grid[-1], atol=1e-7))),
            )
        except (CurveDomainError, np.linalg.LinAlgError, FloatingPointError) as exc:
            self.stats["pd_failures"] += 1
            self.failures.append(str(exc))
            return ModeResult(np.zeros(n), -math.inf, math.inf, int(getattr(locals().get("fit", None), "nit", 0)),
                              int(getattr(locals().get("fit", None), "nfev", 0)), False, str(exc), False,
                              logdet_C, math.nan, None, Cinv)

    def logcriterion(self, params: np.ndarray, fixed_h: float | None = None) -> tuple[float, ModeResult | None]:
        if fixed_h is None:
            alpha, beta, log_sigma, log_h, detection_sd = params
            h = float(math.exp(log_h))
        else:
            alpha, beta, log_sigma, detection_sd = params
            h = fixed_h
        sigma = float(math.exp(log_sigma))
        if h < 1.0 or h > 30.0 or not 0.0 <= detection_sd < SD_MAX:
            return math.inf, None
        try:
            mode = self.mode(float(alpha), float(beta), sigma, h, float(detection_sd))
            if not mode.success or not mode.pd_ok or not math.isfinite(mode.value):
                return math.inf, mode
            value = mode.value - 0.5 * mode.logdet_C
            if sigma > 0.0:
                value -= 0.5 * mode.logdet_H
            return -value, mode
        except CurveDomainError as exc:
            self.failures.append(str(exc))
            return math.inf, None


def load_data(case: str) -> GPData:
    with np.load(PUBLIC / "exposure.npz", allow_pickle=False) as exposure, np.load(
        PUBLIC / "public_inputs.npz", allow_pickle=False
    ) as public:
        ids = tuple(str(v) for v in public["site_ids"])
        site_rows, site_cols = public["site_rows"], public["site_cols"]
        site_a = np.asarray(exposure["site_a"], dtype=float)
        coords = np.column_stack((site_rows, site_cols)).astype(float)
        split = np.asarray(public["site_splits"]).astype(str) == "training"
    panel = OBS_ROOT / ("cell-09" if case == "B_H3" else "cell-04") / "rep-000"
    with np.load(panel / "observations.npz", allow_pickle=False) as obs:
        observed = likelihood.prepare_observations(
            obs["prey_counts"][None, ...], obs["predator_counts"][None, ...],
            obs["site_ids"], split, initial_alive=True,
        )
    bank = likelihood.compress_bank(np.load(BANK_PATH, mmap_mode="r"), ids)
    # Use the requested capstone helpers to preserve their site-subsetting contract.
    bank = qualification.subset_bank(bank, observed.training_mask)
    observed = qualification.subset_observations(observed, observed.training_mask)
    site_a = site_a[split]
    coords = coords[split]
    distances = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(axis=2))
    K = np.exp(-distances / 10.0)
    return GPData(bank, observed, site_a, coords, K, case, int(split.sum()))


def fit_case(data: GPData, fixed_h: float | None) -> dict[str, Any]:
    criterion = Criterion(data)
    if fixed_h is None:
        x0 = np.array([-5.5, 0.4, math.log(0.35), math.log(3.0), 0.2])
        bounds = [(-12.0, -3.0), (-2.0, 2.0), (math.log(1e-4), math.log(2.0)), (0.0, math.log(30.0)), (0.0, SD_MAX * (1 - 1e-10))]
    else:
        x0 = np.array([-5.5, 0.4, math.log(0.35), 0.2])
        bounds = [(-12.0, -3.0), (-2.0, 2.0), (math.log(1e-4), math.log(2.0)), (0.0, SD_MAX * (1 - 1e-10))]
    starts = [x0]
    if fixed_h is None:
        starts.append(np.array([-5.5, 0.0, math.log(0.2), math.log(1.2), 0.1]))
    else:
        starts.append(np.array([-5.5, 0.0, math.log(0.2), 0.1]))
    rows = []
    started = time.perf_counter()
    for start in starts:
        def fun(x: np.ndarray) -> float:
            value, _ = criterion.logcriterion(x, fixed_h=fixed_h)
            return float(value)
        fit = minimize(fun, start, method="L-BFGS-B", bounds=bounds,
                       options={"maxiter": 32, "ftol": 1e-7, "gtol": 2e-5, "maxls": 20})
        value, mode = criterion.logcriterion(np.asarray(fit.x), fixed_h=fixed_h)
        rows.append({
            "start": start,
            "final": fit.x,
            "success": bool(fit.success),
            "message": str(fit.message),
            "nfev": int(fit.nfev),
            "nit": int(fit.nit),
            "objective": float(value),
            "mode": mode,
        })
    valid = [r for r in rows if math.isfinite(r["objective"]) and r["mode"] is not None]
    best = min(valid, key=lambda r: r["objective"]) if valid else None
    def unpack(x: np.ndarray) -> dict[str, float]:
        if fixed_h is None:
            return {"alpha": float(x[0]), "beta": float(x[1]), "sigma": float(math.exp(x[2])), "h": float(math.exp(x[3])), "detection_sd": float(x[4])}
        return {"alpha": float(x[0]), "beta": float(x[1]), "sigma": float(math.exp(x[2])), "h": float(fixed_h), "detection_sd": float(x[3])}
    result: dict[str, Any] = {
        "fixed_h": fixed_h,
        "elapsed_seconds": time.perf_counter() - started,
        "starts": [{k: (v if k not in {"mode", "start", "final"} else jsonable(v)) for k, v in r.items() if k != "mode"} | ({"parameters": unpack(np.asarray(r["final"]))} if True else {}) for r in rows],
        "best": None,
        "curve_cache": {"count": len(criterion.curve_cache), "seconds": criterion.stats["curve_seconds"]},
        "mode_calls": criterion.stats["mode_calls"],
        "pd_failures": criterion.stats["pd_failures"],
        "failures": criterion.failures[:20],
    }
    if best is not None:
        mode: ModeResult = best["mode"]
        result["best"] = {
            "parameters": unpack(np.asarray(best["final"])),
            "criterion": float(-best["objective"]),
            "mode_value": mode.value,
            "mode_gradient_inf": mode.gradient_inf,
            "mode_iterations": mode.iterations,
            "mode_evaluations": mode.evaluations,
            "mode_success": mode.success,
            "mode_message": mode.message,
            "laplace_pd": mode.pd_ok,
            "mode_eta_min": mode.eta_min,
            "mode_eta_max": mode.eta_max,
            "mode_curve_bound_touch": mode.curve_bound_touch,
        }
        curve = criterion.curves(result["best"]["parameters"]["h"], result["best"]["parameters"]["detection_sd"])
        result["best"]["curve_check"] = criterion.check_curves(curve)
    return result


def importance_check(
    data: GPData,
    h: float = 3.0,
    detection_sd: float = 0.2,
    draws: int = 4096,
    allow_refine: bool = True,
) -> dict[str, Any]:
    criterion = Criterion(data)
    alpha, beta, sigma = -5.5, 0.5, 0.4
    mode = criterion.mode(alpha, beta, sigma, h, detection_sd)
    if not mode.success or mode.H is None or mode.Cinv is None:
        return {"status": "blocked", "reason": mode.message}
    curve = criterion.curves(h, detection_sd)
    criterion.check_curves(curve)
    hfac = cho_factor(mode.H, lower=True)
    covariance = cho_solve(hfac, np.eye(data.site_count))
    rng = np.random.default_rng(SEED)
    samples = rng.multivariate_normal(mode.u, covariance, size=draws, method="cholesky")
    eta0 = alpha + beta * data.A
    logw = np.empty(draws)
    for i, u in enumerate(samples):
        ell, _, _ = curve.evaluate(eta0 + u)
        logw[i] = float(np.sum(ell) - 0.5 * u @ mode.Cinv @ u - 0.5 * mode.logdet_C + 0.5 * mode.logdet_H + 0.5 * (u - mode.u) @ mode.H @ (u - mode.u))
    estimate = float(logsumexp(logw) - math.log(draws))
    laplace = float(mode.value - 0.5 * mode.logdet_C + 0.5 * mode.logdet_H)
    weights = np.exp(logw - logsumexp(logw))
    ess = float(1.0 / np.sum(weights * weights))
    result = {"status": "ok", "h": h, "detection_sd": detection_sd, "alpha": alpha, "beta": beta, "sigma": sigma,
            "draws": draws, "seed": SEED, "laplace_logcriterion": laplace, "importance_logmean": estimate,
            "difference_importance_minus_laplace": estimate - laplace, "ess": ess,
            "max_log_weight_minus_mean": float(np.max(logw) - np.mean(logw)), "curve_check": curve.direct_check}
    if allow_refine and abs(estimate - laplace) > 0.03:
        result["refinement"] = importance_check(
            data, h=h, detection_sd=detection_sd, draws=16384, allow_refine=False
        )
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "script_sha256": sha256(Path(__file__)),
        "inputs": {str(p.relative_to(ROOT)): sha256(p) for p in [BANK_PATH, COMPRESSED_PATH, PUBLIC / "public_inputs.npz", PUBLIC / "exposure.npz",
            OBS_ROOT / "cell-09/rep-000/observations.npz", OBS_ROOT / "cell-04/rep-000/observations.npz"]},
        "runtime": {"python": sys.version, "platform": platform.platform(), "machine": platform.machine(), "numpy": np.__version__},
        "grid": GRID, "series_domain": likelihood.SERIES_DOMAIN, "series_order": likelihood.SERIES_ORDER,
        "seed": SEED, "thread_policy": "single-process; BLAS thread count inherited",
    }
    write_json(OUT / "manifest.json", manifest)
    results: dict[str, Any] = {"manifest": manifest, "cases": {}, "importance": {}}
    for case in ("B_H3", "H3"):
        case_started = time.perf_counter()
        data = load_data(case)
        case_result: dict[str, Any] = {"site_count": data.site_count, "training_site_ids": list(data.observed.site_ids), "fits": {}}
        for fixed_h, label in ((1.0, "h1"), (None, "free_h")):
            print(f"{case} {label}: starting", flush=True)
            case_result["fits"][label] = fit_case(data, fixed_h)
            print(f"{case} {label}: done", flush=True)
        stress = Criterion(data)
        stress_curves = stress.curves(30.0, 0.2)
        case_result["h30_domain_stress"] = stress.check_curves(stress_curves)
        case_result["pair_elapsed_seconds"] = time.perf_counter() - case_started
        results["cases"][case] = case_result
        print(f"{case}: importance check", flush=True)
        results["importance"][case] = importance_check(data)
        print(f"{case}: complete", flush=True)
        write_json(OUT / f"{case.lower()}-results.json", case_result | {"importance": results["importance"][case]})
    write_json(OUT / "results.json", results)


if __name__ == "__main__":
    main()
