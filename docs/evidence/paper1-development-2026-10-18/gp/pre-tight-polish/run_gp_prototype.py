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
# The original 61-node grid is retained in ``initial/``.  This denser grid is
# still a bounded diagnostic, but materially reduces interior interpolation
# error without permitting extrapolation.
GRID = np.linspace(-12.0, -2.0, 161)
MEAN_DETECTION = 0.65
SD_MAX = math.sqrt(MEAN_DETECTION * (1.0 - MEAN_DETECTION))
SEED = 20261018
KKT_THRESHOLD = 1e-3
LEGACY_STARTS = {
    "B_H3": {
        "free_h": np.array([-5.891168849651824, 0.5928625884694861, math.log(0.6012722789291436), math.log(4.18900957676729), 0.19722001165208683]),
        "h1": np.array([-5.522294957771277, 0.7029353517539787, math.log(0.2670941664360785), 0.19827443215494037]),
    },
    "H3": {
        "free_h": np.array([-5.894856300558282, 0.5558264966017219, math.log(0.37586623301808036), math.log(2.356901892406757), 0.2053027834150842]),
        "h1": np.array([-5.728056229619878, 0.6643779499678889, math.log(0.22023641356667592), 0.20523494652879626]),
    },
}


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
        # Do not alias distinct outer finite-difference points in the cache.
        key = (float(h), float(detection_sd))
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
        chosen = np.linspace(0, len(mids) - 1, max(count, 12), dtype=int)
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
                np.zeros(n), value, math.nan, 0, 1, True,
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
            # Finish with deterministic Newton steps using the analytic mode
            # Hessian.  This tightens the mode score independently of the
            # optimizer's stopping flag.
            newton_steps = 0
            for _ in range(12):
                ell, der, curv = curves.evaluate(eta0 + u)
                gradient = der - Cinv @ u
                if float(np.max(np.abs(gradient))) <= 1e-8:
                    break
                H_current = Cinv - np.diag(curv)
                step = np.linalg.solve(H_current, gradient)
                current_f = float(np.sum(ell) - 0.5 * u @ Cinv @ u)
                scale = 1.0
                while scale >= 2.0**-12:
                    candidate = u + scale * step
                    if np.all(candidate > np.asarray([b[0] for b in inner_bounds])) and np.all(
                        candidate < np.asarray([b[1] for b in inner_bounds])
                    ):
                        cand_ell, _, _ = curves.evaluate(eta0 + candidate)
                        cand_f = float(np.sum(cand_ell) - 0.5 * candidate @ Cinv @ candidate)
                        if cand_f >= current_f:
                            u = candidate
                            break
                    scale *= 0.5
                else:
                    raise FloatingPointError("Newton line search failed")
                newton_steps += 1
            ell, der, curv = curves.evaluate(eta0 + u)
            H = Cinv - np.diag(curv)
            hfac = cho_factor(H, lower=True, check_finite=True)
            logdet_H = float(2.0 * np.sum(np.log(np.diag(hfac[0]))))
            mode_value = float(np.sum(ell) - 0.5 * u @ Cinv @ u)
            grad_inf = float(np.max(np.abs(der - Cinv @ u)))
            pd_ok = bool(np.all(np.isfinite(H)))
            if not pd_ok:
                raise np.linalg.LinAlgError("nonfinite Laplace precision")
            bound_touch = bool(
                np.any(np.isclose(eta0 + u, curves.grid[0], atol=1e-7))
                or np.any(np.isclose(eta0 + u, curves.grid[-1], atol=1e-7))
            )
            return ModeResult(
                u, mode_value, grad_inf, int(fit.nit) + newton_steps, int(fit.nfev),
                bool(fit.success) and grad_inf <= 1e-7 and not bound_touch,
                str(fit.message), True, logdet_C, logdet_H, H, Cinv,
                float(np.min(eta0 + u)), float(np.max(eta0 + u)),
                bound_touch,
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
            if log_h < -1e-10 or log_h > math.log(30.0) + 1e-10:
                return math.inf, None
            h = float(np.clip(math.exp(log_h), 1.0, 30.0))
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

    def logcriterion_sigma_zero(
        self, params: np.ndarray, fixed_h: float | None = None
    ) -> tuple[float, ModeResult | None]:
        """Exact lower-dimensional criterion for the sigma=0 boundary."""
        if fixed_h is None:
            alpha, beta, log_h, detection_sd = params
            if log_h < -1e-10 or log_h > math.log(30.0) + 1e-10:
                return math.inf, None
            h = float(np.clip(math.exp(log_h), 1.0, 30.0))
        else:
            alpha, beta, detection_sd = params
            h = float(fixed_h)
        if h < 1.0 or h > 30.0 or not 0.0 <= detection_sd < SD_MAX:
            return math.inf, None
        try:
            mode = self.mode(float(alpha), float(beta), 0.0, h, float(detection_sd))
            if not mode.success:
                return math.inf, mode
            return -mode.value, mode
        except CurveDomainError as exc:
            self.failures.append(str(exc))
            return math.inf, None

    def outer_fd_gradient(
        self, params: np.ndarray, fixed_h: float | None, sigma_zero: bool,
        bounds: list[tuple[float, float]],
        step: float = 1e-4,
    ) -> dict[str, Any]:
        """Return a bound-aware finite-difference and projected KKT score."""
        evaluator = self.logcriterion_sigma_zero if sigma_zero else self.logcriterion
        point = np.asarray(params, dtype=float)
        base, _ = evaluator(point, fixed_h=fixed_h)
        if not math.isfinite(base):
            return {
                "step": step,
                "gradient": [math.nan] * len(point),
                "projected_gradient": [math.nan] * len(point),
                "gradient_inf": math.nan,
                "projected_gradient_inf": math.nan,
                "schemes": ["failed_base"] * len(point),
                "status": "failed_base",
            }
        values: list[float] = []
        schemes: list[str] = []
        for index, (lower, upper) in enumerate(bounds):
            delta = step * max(1.0, abs(float(point[index])))
            can_minus = point[index] - delta >= lower
            can_plus = point[index] + delta <= upper
            if can_minus and can_plus:
                plus = point.copy()
                minus = point.copy()
                plus[index] += delta
                minus[index] -= delta
                vp, _ = evaluator(plus, fixed_h=fixed_h)
                vm, _ = evaluator(minus, fixed_h=fixed_h)
                value = (vp - vm) / (2.0 * delta)
                scheme = "central"
            elif can_plus:
                plus = point.copy()
                plus[index] += delta
                vp, _ = evaluator(plus, fixed_h=fixed_h)
                if point[index] + 2.0 * delta <= upper:
                    plus2 = point.copy()
                    plus2[index] += 2.0 * delta
                    vp2, _ = evaluator(plus2, fixed_h=fixed_h)
                    value = (-3.0 * base + 4.0 * vp - vp2) / (2.0 * delta)
                    scheme = "forward_second_order"
                else:
                    value = (vp - base) / delta
                    scheme = "forward_first_order"
            elif can_minus:
                minus = point.copy()
                minus[index] -= delta
                vm, _ = evaluator(minus, fixed_h=fixed_h)
                if point[index] - 2.0 * delta >= lower:
                    minus2 = point.copy()
                    minus2[index] -= 2.0 * delta
                    vm2, _ = evaluator(minus2, fixed_h=fixed_h)
                    value = (3.0 * base - 4.0 * vm + vm2) / (2.0 * delta)
                    scheme = "backward_second_order"
                else:
                    value = (base - vm) / delta
                    scheme = "backward_first_order"
            else:
                value = math.nan
                scheme = "failed_support"
            values.append(float(value) if math.isfinite(value) else math.nan)
            schemes.append(scheme)
        finite = np.isfinite(values)
        projected: list[float] = []
        for value, coordinate, (lower, upper) in zip(values, point, bounds, strict=True):
            if not math.isfinite(value):
                projected.append(math.nan)
                continue
            tolerance = 1e-8 * max(1.0, abs(lower), abs(upper))
            if coordinate <= lower + tolerance:
                projected.append(float(min(value, 0.0)))
            elif coordinate >= upper - tolerance:
                projected.append(float(max(value, 0.0)))
            else:
                projected.append(float(value))
        projected_finite = np.isfinite(projected)
        return {
            "step": step,
            "gradient": values,
            "projected_gradient": projected,
            "gradient_inf": float(np.max(np.abs(np.asarray(values)[finite])))
            if np.any(finite) else math.nan,
            "projected_gradient_inf": float(
                np.max(np.abs(np.asarray(projected)[projected_finite]))
            ) if np.any(projected_finite) else math.nan,
            "schemes": schemes,
            "status": "ok" if np.all(finite) and np.all(projected_finite) else "failed_support",
        }


def load_data(case: str) -> GPData:
    with np.load(PUBLIC / "exposure.npz", allow_pickle=False) as exposure, np.load(
        PUBLIC / "public_inputs.npz", allow_pickle=False
    ) as public:
        ids = tuple(str(v) for v in public["site_ids"])
        site_rows, site_cols = public["site_rows"], public["site_cols"]
        site_a = np.asarray(exposure["site_a"], dtype=float)
        coords = np.column_stack((site_rows, site_cols)).astype(float)
        split = np.asarray(public["site_splits"]).astype(str) == "training"
        if site_a.shape != (len(ids),):
            raise ValueError("exposure site_a length does not match public site_ids")
        if not np.array_equal(site_a, np.asarray(exposure["map_a"])[site_rows, site_cols]):
            raise ValueError("exposure site_a does not match map_a at public site coordinates")
    panel = OBS_ROOT / ("cell-09" if case == "B_H3" else "cell-04") / "rep-000"
    with np.load(panel / "observations.npz", allow_pickle=False) as obs:
        obs_ids = tuple(str(v) for v in obs["site_ids"])
        if obs_ids != ids:
            raise ValueError("observation site_ids do not match public site_ids")
        if "training_mask" in obs and not np.array_equal(obs["training_mask"], split):
            raise ValueError("observation training_mask does not match public site_splits")
        observed = likelihood.prepare_observations(
            obs["prey_counts"][None, ...], obs["predator_counts"][None, ...],
            obs_ids, split, initial_alive=True,
        )
    bank = likelihood.compress_bank(np.load(BANK_PATH, mmap_mode="r"), ids)
    if bank.site_ids != ids:
        raise ValueError("arrival bank site_ids do not match public site_ids")
    # Use the requested capstone helpers to preserve their site-subsetting contract.
    bank = qualification.subset_bank(bank, observed.training_mask)
    observed = qualification.subset_observations(observed, observed.training_mask)
    if bank.site_ids != observed.site_ids:
        raise ValueError("training bank and observation site identifiers diverged")
    site_a = site_a[split]
    coords = coords[split]
    distances = np.sqrt(((coords[:, None, :] - coords[None, :, :]) ** 2).sum(axis=2))
    K = np.exp(-distances / 10.0)
    return GPData(bank, observed, site_a, coords, K, case, int(split.sum()))


def fit_case(data: GPData, fixed_h: float | None) -> dict[str, Any]:
    criterion = Criterion(data)
    if fixed_h is None:
        x0 = np.array([-5.5, 0.4, math.log(0.35), math.log(3.0), 0.2])
        positive_bounds = [
            (-12.0, -3.0), (-2.0, 2.0), (math.log(1e-4), math.log(2.0)),
            (0.0, math.log(30.0)), (0.0, SD_MAX * (1 - 1e-10)),
        ]
        sigma_zero_bounds = [
            (-12.0, -3.0), (-2.0, 2.0), (0.0, math.log(30.0)),
            (0.0, SD_MAX * (1 - 1e-10)),
        ]
        sigma_zero_start = np.array([-5.5, 0.4, math.log(3.0), 0.2])
    else:
        x0 = np.array([-5.5, 0.4, math.log(0.35), 0.2])
        positive_bounds = [
            (-12.0, -3.0), (-2.0, 2.0), (math.log(1e-4), math.log(2.0)),
            (0.0, SD_MAX * (1 - 1e-10)),
        ]
        sigma_zero_bounds = [
            (-12.0, -3.0), (-2.0, 2.0),
            (0.0, SD_MAX * (1 - 1e-10)),
        ]
        sigma_zero_start = np.array([-5.5, 0.4, 0.2])
    starts = [x0]
    if fixed_h is None:
        starts.append(np.array([-5.5, 0.0, math.log(0.2), math.log(1.2), 0.1]))
    else:
        starts.append(np.array([-5.5, 0.0, math.log(0.2), 0.1]))
    label = "free_h" if fixed_h is None else "h1"
    starts.append(LEGACY_STARTS[data.case][label])
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()

    def unpack(x: np.ndarray, sigma_zero: bool = False) -> dict[str, float]:
        if sigma_zero:
            if fixed_h is None:
                return {
                    "alpha": float(x[0]), "beta": float(x[1]),
                    "sigma": 0.0, "h": float(np.clip(math.exp(x[2]), 1.0, 30.0)),
                    "detection_sd": float(x[3]),
                }
            return {
                "alpha": float(x[0]), "beta": float(x[1]), "sigma": 0.0,
                "h": float(fixed_h), "detection_sd": float(x[2]),
            }
        if fixed_h is None:
            return {
                "alpha": float(x[0]), "beta": float(x[1]),
                "sigma": float(math.exp(x[2])),
                "h": float(np.clip(math.exp(x[3]), 1.0, 30.0)),
                "detection_sd": float(x[4]),
            }
        return {
            "alpha": float(x[0]), "beta": float(x[1]),
            "sigma": float(math.exp(x[2])), "h": float(fixed_h),
            "detection_sd": float(x[3]),
        }

    def evaluator(sigma_zero: bool) -> Any:
        return criterion.logcriterion_sigma_zero if sigma_zero else criterion.logcriterion

    def candidate_bounds(sigma_zero: bool) -> list[tuple[float, float]]:
        return sigma_zero_bounds if sigma_zero else positive_bounds

    def append_candidate(
        point: np.ndarray,
        start: np.ndarray,
        sigma_zero: bool,
        kind: str,
        optimizer: str,
        optimizer_success: bool,
        message: str,
        nfev: int,
        nit: int,
        start_id: str,
    ) -> None:
        value, mode = evaluator(sigma_zero)(np.asarray(point), fixed_h=fixed_h)
        rows.append({
            "kind": kind,
            "optimizer": optimizer,
            "sigma_zero": sigma_zero,
            "start_id": start_id,
            "start": np.asarray(start, dtype=float),
            "final": np.asarray(point, dtype=float),
            "success": bool(optimizer_success),
            "message": message,
            "nfev": int(nfev),
            "nit": int(nit),
            "objective": float(value),
            "mode": mode,
            "outer_fd": None,
            "eligible": False,
            "rejection_reasons": [],
        })

    def run_start(
        start: np.ndarray, sigma_zero: bool, kind: str, start_id: str
    ) -> None:
        def fun(x: np.ndarray) -> float:
            value, _ = evaluator(sigma_zero)(x, fixed_h=fixed_h)
            return float(value)
        use_bounds = candidate_bounds(sigma_zero)
        append_candidate(
            start, start, sigma_zero, kind, "incumbent", True,
            "retained incumbent", 1, 0, start_id,
        )
        fit = minimize(
            fun, start, method="L-BFGS-B", jac="3-point", bounds=use_bounds,
            options={
                "maxiter": 64, "ftol": 1e-9, "gtol": 2e-5, "maxls": 20,
                "finite_diff_rel_step": 1e-4,
            },
        )
        append_candidate(
            fit.x, start, sigma_zero, kind, "lbfgsb", bool(fit.success),
            str(fit.message), int(fit.nfev), int(fit.nit), start_id,
        )

    def run_powell_polish(source: dict[str, Any]) -> None:
        start = np.asarray(source["final"], dtype=float)
        sigma_zero = bool(source["sigma_zero"])
        start_id = str(source["start_id"])
        def fun(x: np.ndarray) -> float:
            value, _ = evaluator(sigma_zero)(x, fixed_h=fixed_h)
            return float(value)
        use_bounds = candidate_bounds(sigma_zero)
        powell = minimize(
            fun, start, method="Powell", bounds=use_bounds,
            options={"maxiter": 48, "xtol": 1e-6, "ftol": 1e-8},
        )
        append_candidate(
            powell.x, start, sigma_zero, str(source["kind"]), "powell",
            bool(powell.success), str(powell.message), int(powell.nfev),
            int(powell.nit), start_id,
        )
        polish = minimize(
            fun, powell.x, method="L-BFGS-B", jac="3-point", bounds=use_bounds,
            options={
                "maxiter": 64, "ftol": 1e-10, "gtol": 2e-5, "maxls": 20,
                "finite_diff_rel_step": 1e-4,
            },
        )
        append_candidate(
            polish.x, powell.x, sigma_zero, str(source["kind"]),
            "powell_lbfgsb_polish", bool(polish.success), str(polish.message),
            int(polish.nfev), int(polish.nit), start_id,
        )

    for index, start in enumerate(starts):
        kind = "legacy_warmstart" if index == len(starts) - 1 else "positive_sigma"
        run_start(start, False, kind, f"positive_{index}")
    run_start(sigma_zero_start, True, "sigma_zero", "sigma_zero_0")

    def assess_candidates() -> None:
        for row in rows:
            if row["outer_fd"] is not None:
                continue
            reasons: list[str] = []
            if not math.isfinite(row["objective"]):
                reasons.append("nonfinite_objective")
            mode = row["mode"]
            if mode is None:
                reasons.append("missing_inner_mode")
            elif not mode.success:
                reasons.append("invalid_inner_mode")
            elif not mode.pd_ok:
                reasons.append("non_pd_laplace_hessian")
            if not reasons:
                row["outer_fd"] = criterion.outer_fd_gradient(
                    np.asarray(row["final"]), fixed_h, bool(row["sigma_zero"]),
                    candidate_bounds(bool(row["sigma_zero"])),
                )
                if row["outer_fd"]["status"] != "ok":
                    reasons.append("outer_fd_failed")
                elif row["outer_fd"]["projected_gradient_inf"] > KKT_THRESHOLD:
                    reasons.append("outer_kkt_failed")
            row["rejection_reasons"] = reasons
            row["eligible"] = not reasons

    def valid_inner(row: dict[str, Any]) -> bool:
        mode = row["mode"]
        return bool(
            math.isfinite(row["objective"]) and mode is not None
            and mode.success and mode.pd_ok
        )

    assess_candidates()
    fallback_triggered = {"positive_sigma": False, "sigma_zero": False}
    for sigma_zero, family in ((False, "positive_sigma"), (True, "sigma_zero")):
        family_rows = [r for r in rows if bool(r["sigma_zero"]) == sigma_zero]
        inner_rows = [r for r in family_rows if valid_inner(r)]
        eligible_rows = [r for r in family_rows if r["eligible"]]
        best_inner = min(inner_rows, key=lambda r: r["objective"]) if inner_rows else None
        best_eligible = (
            min(eligible_rows, key=lambda r: r["objective"]) if eligible_rows else None
        )
        lower_unqualified = bool(
            best_inner is not None and not best_inner["eligible"]
            and (best_eligible is None or best_inner["objective"] < best_eligible["objective"] - 1e-6)
        )
        if best_inner is not None and (best_eligible is None or lower_unqualified):
            fallback_triggered[family] = True
            run_powell_polish(best_inner)
    assess_candidates()

    family_resolution: dict[str, Any] = {}
    family_best: dict[str, dict[str, Any] | None] = {}
    for sigma_zero, family in ((False, "positive_sigma"), (True, "sigma_zero")):
        family_rows = [r for r in rows if bool(r["sigma_zero"]) == sigma_zero]
        inner_rows = [r for r in family_rows if valid_inner(r)]
        eligible_rows = [r for r in family_rows if r["eligible"]]
        best_eligible = (
            min(eligible_rows, key=lambda r: r["objective"]) if eligible_rows else None
        )
        lower_unqualified = [
            r for r in inner_rows
            if not r["eligible"] and (
                best_eligible is None
                or r["objective"] < best_eligible["objective"] - 1e-6
            )
        ]
        resolved = best_eligible is not None and not lower_unqualified
        family_best[family] = best_eligible if resolved else None
        family_resolution[family] = {
            "resolved": resolved,
            "eligible_candidate_count": len(eligible_rows),
            "rejected_candidate_count": len(family_rows) - len(eligible_rows),
            "fallback_triggered": fallback_triggered[family],
            "lower_unqualified_candidate_count": len(lower_unqualified),
        }

    resolved = bool(
        family_resolution["positive_sigma"]["resolved"]
        and family_resolution["sigma_zero"]["resolved"]
    )
    eligible = [r for r in rows if r["eligible"]]
    best_positive = family_best["positive_sigma"]
    best_sigma_zero = family_best["sigma_zero"]
    best = (
        min([best_positive, best_sigma_zero], key=lambda r: r["objective"])
        if resolved and best_positive is not None and best_sigma_zero is not None else None
    )
    start_ids = sorted({str(row["start_id"]) for row in rows})
    eligible_start_ids = sorted({str(row["start_id"]) for row in eligible})
    result: dict[str, Any] = {
        "status": "resolved" if resolved else "unresolved",
        "fixed_h": fixed_h,
        "elapsed_seconds": time.perf_counter() - started,
        "starts": [
            {k: (v if k not in {"mode", "start", "final"} else jsonable(v))
             for k, v in r.items() if k != "mode"}
            | {"parameters": unpack(np.asarray(r["final"]), bool(r["sigma_zero"]))}
            for r in rows
        ],
        "best": None,
        "best_positive": None,
        "best_sigma_zero": None,
        "start_count": len(start_ids),
        "eligible_start_count": len(eligible_start_ids),
        "rejected_start_count": len(start_ids) - len(eligible_start_ids),
        "candidate_count": len(rows),
        "eligible_candidate_count": len(eligible),
        "rejected_candidate_count": len(rows) - len(eligible),
        "accepted_start_count": len(eligible),
        "family_resolution": family_resolution,
        "kkt_threshold": KKT_THRESHOLD,
        "curve_cache": {"count": len(criterion.curve_cache), "seconds": criterion.stats["curve_seconds"]},
        "mode_calls": criterion.stats["mode_calls"],
        "pd_failures": criterion.stats["pd_failures"],
        "failures": criterion.failures[:20],
    }
    if best is not None:
        mode: ModeResult = best["mode"]
        result["best"] = {
            "kind": best["kind"],
            "optimizer": best["optimizer"],
            "sigma_zero": bool(best["sigma_zero"]),
            "parameters": unpack(np.asarray(best["final"]), bool(best["sigma_zero"])),
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
            "outer_fd": best["outer_fd"],
        }
        curve = criterion.curves(result["best"]["parameters"]["h"], result["best"]["parameters"]["detection_sd"])
        result["best"]["curve_check"] = criterion.check_curves(curve)
    if best_positive is not None:
        mode_positive: ModeResult = best_positive["mode"]
        result["best_positive"] = {
            "kind": best_positive["kind"],
            "optimizer": best_positive["optimizer"],
            "parameters": unpack(np.asarray(best_positive["final"])),
            "criterion": float(-best_positive["objective"]),
            "mode_gradient_inf": mode_positive.gradient_inf,
            "mode_iterations": mode_positive.iterations,
            "mode_evaluations": mode_positive.evaluations,
            "mode_success": mode_positive.success,
            "laplace_pd": mode_positive.pd_ok,
            "outer_fd": best_positive["outer_fd"],
        }
    if best_sigma_zero is not None:
        mode_zero: ModeResult = best_sigma_zero["mode"]
        result["best_sigma_zero"] = {
            "kind": best_sigma_zero["kind"],
            "optimizer": best_sigma_zero["optimizer"],
            "parameters": unpack(np.asarray(best_sigma_zero["final"]), True),
            "criterion": float(-best_sigma_zero["objective"]),
            "mode_success": mode_zero.success,
            "laplace_pd": mode_zero.pd_ok,
            "outer_fd": best_sigma_zero["outer_fd"],
        }
    return result


def importance_check(
    data: GPData,
    params: dict[str, float],
    draws: int = 4096,
    allow_refine: bool = True,
) -> dict[str, Any]:
    criterion = Criterion(data)
    alpha = float(params["alpha"])
    beta = float(params["beta"])
    sigma = float(params["sigma"])
    h = float(params["h"])
    detection_sd = float(params["detection_sd"])
    if sigma <= 0.0:
        return {"status": "blocked", "reason": "sigma=0 has no Gaussian proposal", "parameters": params}
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
    invalid_draws = 0
    for i, u in enumerate(samples):
        try:
            ell, _, _ = curve.evaluate(eta0 + u)
        except CurveDomainError:
            invalid_draws += 1
            continue
        logw[i] = float(
            np.sum(ell) - 0.5 * u @ mode.Cinv @ u - 0.5 * mode.logdet_C
            - 0.5 * mode.logdet_H + 0.5 * (u - mode.u) @ mode.H @ (u - mode.u)
        )
    if invalid_draws:
        return {
            "status": "failed_curve_domain", "parameters": params, "draws": draws,
            "invalid_draws": invalid_draws, "curve_check": curve.direct_check,
        }
    estimate = float(logsumexp(logw) - math.log(draws))
    laplace = float(mode.value - 0.5 * mode.logdet_C - 0.5 * mode.logdet_H)
    weights = np.exp(logw - logsumexp(logw))
    ess = float(1.0 / np.sum(weights * weights))
    centered = np.exp(logw - float(np.max(logw)))
    mcse_log = float(np.sqrt(np.var(centered, ddof=1) / (draws * np.mean(centered) ** 2)))
    result = {"status": "ok", "parameters": params,
            "draws": draws, "seed": SEED, "laplace_logcriterion": laplace, "importance_logmean": estimate,
            "difference_importance_minus_laplace": estimate - laplace, "mcse_log_importance": mcse_log, "ess": ess,
            "max_log_weight_minus_mean": float(np.max(logw) - np.mean(logw)), "curve_check": curve.direct_check}
    if allow_refine and abs(estimate - laplace) > 0.03:
        result["refinement"] = importance_check(
            data, params=params, draws=16384, allow_refine=False
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
        "optimizer_protocol": {
            "outer_primary": "L-BFGS-B with three-point relative finite differences",
            "outer_fallback": "bounded Powell followed by L-BFGS-B polish",
            "kkt_threshold": KKT_THRESHOLD,
            "eligibility": "finite criterion, valid inner mode, positive-definite Laplace Hessian, projected KKT pass",
            "sigma_zero": "separate exact lower-dimensional fit required for each endpoint",
        },
    }
    write_json(OUT / "manifest.json", manifest)
    results: dict[str, Any] = {"manifest": manifest, "cases": {}, "importance": {}}
    for case in ("B_H3", "H3"):
        case_started = time.perf_counter()
        load_started = time.perf_counter()
        data = load_data(case)
        load_elapsed = time.perf_counter() - load_started
        case_result: dict[str, Any] = {
            "site_count": data.site_count,
            "training_site_ids": list(data.observed.site_ids),
            "fits": {},
            "timing": {"load_seconds": load_elapsed},
        }
        fit_started = time.perf_counter()
        for fixed_h, label in ((1.0, "h1"), (None, "free_h")):
            print(f"{case} {label}: starting", flush=True)
            case_result["fits"][label] = fit_case(data, fixed_h)
            print(f"{case} {label}: done", flush=True)
        case_result["timing"]["pure_fit_seconds"] = time.perf_counter() - fit_started
        stress_started = time.perf_counter()
        stress = Criterion(data)
        stress_curves = stress.curves(30.0, 0.2)
        case_result["h30_domain_stress"] = stress.check_curves(stress_curves)
        case_result["timing"]["h30_stress_seconds"] = time.perf_counter() - stress_started
        case_result["pair_elapsed_seconds"] = time.perf_counter() - case_started
        results["cases"][case] = case_result
        print(f"{case}: importance check", flush=True)
        selected: dict[str, Any] = {}
        for label in ("free_h", "h1"):
            fit_result = case_result["fits"][label]
            candidate = fit_result.get("best")
            if fit_result.get("status") != "resolved" or candidate is None:
                selected[label] = {
                    "status": "blocked",
                    "reason": "outer optimization or sigma-zero comparison unresolved",
                }
            elif candidate.get("sigma_zero"):
                selected[label] = {
                    "status": "not_required_sigma_zero",
                    "reason": "selected endpoint is the exact sigma=0 boundary",
                    "parameters": candidate["parameters"],
                }
            else:
                selected[label] = importance_check(data, candidate["parameters"])
        results["importance"][case] = selected
        h1_fit = case_result["fits"]["h1"]
        free_fit = case_result["fits"]["free_h"]
        if (
            h1_fit.get("status") == "resolved" and free_fit.get("status") == "resolved"
            and h1_fit.get("best") is not None and free_fit.get("best") is not None
        ):
            laplace_lr = float(
                2.0 * (free_fit["best"]["criterion"] - h1_fit["best"]["criterion"])
            )
            profile: dict[str, Any] = {
                "status": "resolved_development_diagnostic",
                "laplace_profile_lr": laplace_lr,
                "free_endpoint_kind": free_fit["best"]["kind"],
                "h1_endpoint_kind": h1_fit["best"]["kind"],
            }
            if selected["free_h"].get("status") == "ok" and selected["h1"].get("status") == "ok":
                free_is = selected["free_h"].get("refinement", selected["free_h"])
                h1_is = selected["h1"].get("refinement", selected["h1"])
                free_difference = float(free_is["difference_importance_minus_laplace"])
                h1_difference = float(h1_is["difference_importance_minus_laplace"])
                profile["importance_at_laplace_optima"] = {
                    "free_difference": free_difference,
                    "h1_difference": h1_difference,
                    "free_draws": int(free_is["draws"]),
                    "h1_draws": int(h1_is["draws"]),
                    "free_mcse": float(free_is["mcse_log_importance"]),
                    "h1_mcse": float(h1_is["mcse_log_importance"]),
                    "fixed_endpoint_adjusted_lr": float(
                        laplace_lr + 2.0 * (free_difference - h1_difference)
                    ),
                    "interpretation": "Fixed-point importance checks at the Laplace optima; not an importance-reoptimized likelihood ratio. Endpoint MCSEs are reported separately because common random numbers couple them.",
                }
            case_result["profile"] = profile
        else:
            case_result["profile"] = {
                "status": "unresolved",
                "reason": "one or both endpoint optimizations failed the complete positive-sigma and sigma-zero comparison",
            }
        print(f"{case}: complete", flush=True)
        write_json(OUT / f"{case.lower()}-results.json", case_result | {"importance": results["importance"][case]})
    write_json(OUT / "results.json", results)


if __name__ == "__main__":
    main()
