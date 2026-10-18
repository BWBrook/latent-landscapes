"""Bounded baseline complete-data frailty diagnostic.

This is a post-hoc diagnostic on the archived Goal 062 histories.  It uses
only the full -60..60 complete-data event histories at the 120 fixed training
sites.  Results and all receipts are written beside this script.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln


SCRIPT = Path(__file__).resolve()
OUT = SCRIPT.parent
ROOT = SCRIPT.parents[3]
PUBLIC = ROOT / "artifacts/goal060_execution/audit-repair/public_inputs"
BASE = ROOT / "artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation"
CLAUDE = ROOT / "artifacts/paper1_planning_20261018"

CELL_SPEC = {
    "00": ("L1", 0.5),
    "01": ("L3", 0.5),
    "03": ("H1", 0.5),
    "04": ("H3", 0.5),
    "06": ("B_L1", 0.7 * math.sqrt(math.log(2.0))),
    "07": ("B_L3", 0.7 * math.sqrt(math.log(2.0))),
    "08": ("B_H1", 0.7 * math.sqrt(math.log(2.0))),
    "09": ("B_H3", 0.7 * math.sqrt(math.log(2.0))),
}
CELL_ORDER = tuple(CELL_SPEC)
LOGC_BOUNDS = (-15.0, 2.0)
LOGH_BOUNDS = (0.0, math.log(10.0))
LOGK_BOUNDS = (math.log(0.05), math.log(1.0e4))
K_STARTS = (1.65, 20.0, 1000.0)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def pieces(loss: np.ndarray, arrival: np.ndarray) -> tuple[np.ndarray, ...]:
    """Return loss/event indicators and complete-data pre/post durations."""
    end = np.minimum(loss, 60.0)
    lost = loss <= 60.0
    post_event = lost & (loss > arrival)
    pre = np.clip(np.minimum(end, arrival) + 60.0, 0.0, None)
    post = np.clip(end - np.maximum(arrival, -60.0), 0.0, None)
    return lost, post_event, pre, post


def homogeneous_nll(
    log_c: float,
    log_h: float,
    w: np.ndarray,
    lost: np.ndarray,
    post_event: np.ndarray,
    pre: np.ndarray,
    post: np.ndarray,
) -> float:
    c = math.exp(log_c)
    h = math.exp(log_h)
    exposure = w * (pre + h * post)
    event_log = np.sum(lost * (log_c + np.log(w) + post_event * log_h))
    return float(-(event_log - c * np.sum(exposure)))


def analytic_homogeneous(
    w: np.ndarray,
    lost: np.ndarray,
    post_event: np.ndarray,
    pre: np.ndarray,
    post: np.ndarray,
    h_fixed: float | None,
) -> dict[str, object]:
    """Exact constrained profile MLE, retaining the zero-event convention."""
    dpost = int(post_event.sum())
    dtotal = int(lost.sum())
    dpre = dtotal - dpost
    spre = float(np.sum(w * pre))
    spost = float(np.sum(w * post))
    if dtotal == 0:
        return {
            "status": "nonunique_full_set",
            "success": False,
            "h": None,
            "c": None,
            "objective": None,
            "dtotal": dtotal,
            "dpre": dpre,
            "dpost": dpost,
            "spre": spre,
            "spost": spost,
            "message": "zero events: c tends to zero and every h in [1,10] is a profile maximizer set",
        }
    if h_fixed is None:
        if dpre > 0 and dpost > 0:
            raw_ratio = (dpost / spost) / (dpre / spre)
        elif dpost == 0:
            raw_ratio = 0.0
        else:
            raw_ratio = math.inf
        h = float(np.clip(raw_ratio, 1.0, 10.0))
        profile_source = "analytic_ratio_clipped"
    else:
        h = float(h_fixed)
        raw_ratio = None
        profile_source = "analytic_h_fixed"
    c = dtotal / (spre + h * spost)
    objective = homogeneous_nll(math.log(c), math.log(h), w, lost, post_event, pre, post)
    contacts = []
    if math.isclose(h, 1.0, abs_tol=1e-11):
        contacts.append("h_lower")
    if math.isclose(h, 10.0, abs_tol=1e-11):
        contacts.append("h_upper")
    return {
        "status": "analytic",
        "success": True,
        "h": h,
        "c": c,
        "k": math.inf,
        "log_c": math.log(c),
        "log_h": math.log(h),
        "log_k": None,
        "objective": objective,
        "dtotal": dtotal,
        "dpre": dpre,
        "dpost": dpost,
        "spre": spre,
        "spost": spost,
        "raw_ratio": raw_ratio,
        "profile_source": profile_source,
        "nfev": 0,
        "nit": 0,
        "bound_contacts": contacts,
        "raw_gradient_max_abs": None,
        "message": "exact constrained homogeneous profile candidate",
    }


def stable_integer_loggamma_ratio(k: float, d: int) -> float:
    """log Gamma(k+d)-log Gamma(k), for integer d without high-k cancellation."""
    return float(d * math.log(k) + sum(math.log1p(j / k) for j in range(d)))


def integrated_term(k: float, d: int, L: float) -> float:
    """Gamma-integrated survival/event term after cancellation of D log(k)."""
    return float(sum(math.log1p(j / k) for j in range(d)) - (k + d) * math.log1p(L / k))


def gamma_nll(
    theta: np.ndarray,
    w: np.ndarray,
    lost: np.ndarray,
    post_event: np.ndarray,
    pre: np.ndarray,
    post: np.ndarray,
    clusters: np.ndarray,
    nclusters: int,
) -> float:
    log_c, log_h, log_k = map(float, theta)
    c = math.exp(log_c)
    h = math.exp(log_h)
    k = math.exp(log_k)
    cum = c * w * (pre + h * post)
    event_log = np.sum(lost * (log_c + np.log(w) + post_event * log_h))
    d = np.bincount(clusters, weights=lost.astype(float), minlength=nclusters).astype(int)
    L = np.bincount(clusters, weights=cum, minlength=nclusters)
    integ = sum(integrated_term(k, int(di), float(li)) for di, li in zip(d, L))
    return float(-(event_log + integ))


def gamma_nll_scipy(
    theta: np.ndarray,
    w: np.ndarray,
    lost: np.ndarray,
    post_event: np.ndarray,
    pre: np.ndarray,
    post: np.ndarray,
    clusters: np.ndarray,
    nclusters: int,
) -> float:
    """Reference formula used only for the numerical identity check."""
    log_c, log_h, log_k = map(float, theta)
    c, h, k = math.exp(log_c), math.exp(log_h), math.exp(log_k)
    cum = c * w * (pre + h * post)
    event_log = np.sum(lost * (log_c + np.log(w) + post_event * log_h))
    d = np.bincount(clusters, weights=lost.astype(float), minlength=nclusters)
    L = np.bincount(clusters, weights=cum, minlength=nclusters)
    term = gammaln(k + d) - gammaln(k) + k * math.log(k) - (k + d) * np.log(k + L)
    return float(-(event_log + np.sum(term)))


def contact_flags(x: np.ndarray, bounds: list[tuple[float, float]]) -> list[str]:
    labels = ("c", "h", "k")
    out = []
    for label, value, (lo, hi) in zip(labels, x, bounds):
        if math.isclose(float(value), lo, abs_tol=2e-7, rel_tol=0.0):
            out.append(f"{label}_lower")
        if math.isclose(float(value), hi, abs_tol=2e-7, rel_tol=0.0):
            out.append(f"{label}_upper")
    return out


def serial_float(value: float | np.floating | None) -> float | None:
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def fit_gamma(
    w: np.ndarray,
    lost: np.ndarray,
    post_event: np.ndarray,
    pre: np.ndarray,
    post: np.ndarray,
    clusters: np.ndarray,
    nclusters: int,
    hom: dict[str, object],
    h_fixed: float | None,
    family: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Fit a finite-k family from four fixed starts plus its exact hom limit."""
    dtotal = int(lost.sum())
    c_hom = float(hom["c"] if hom["c"] is not None else max(dtotal, 1) / max(float(np.sum(w * (pre + post))), 1e-12))
    h_hom = float(hom["h"] if hom["h"] is not None else 1.0)
    c_published = max(dtotal, 1) / max(float(np.sum(w * (pre + post))), 1e-12)
    h_published = 1.0 if h_fixed is not None else math.exp(0.5)
    starts = [
        ("published", c_published, h_published, 1.65),
        ("near_homogeneous", c_hom, h_hom if h_fixed is None else 1.0, 1000.0),
        ("intermediate_k20", c_hom, h_hom if h_fixed is None else 1.0, 20.0),
        ("intermediate_k1.65", c_hom, h_hom if h_fixed is None else 1.0, 1.65),
    ]
    bounds = [LOGC_BOUNDS, (0.0, 0.0) if h_fixed is not None else LOGH_BOUNDS, LOGK_BOUNDS]
    receipts: list[dict[str, object]] = []
    qualified: list[dict[str, object]] = []
    for start_name, c0, h0, k0 in starts:
        x0 = np.array([math.log(max(c0, math.exp(LOGC_BOUNDS[0]))), math.log(h0), math.log(k0)], dtype=float)
        try:
            result = minimize(
                gamma_nll,
                x0,
                args=(w, lost, post_event, pre, post, clusters, nclusters),
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": 1000, "ftol": 1e-12, "gtol": 1e-8, "maxls": 50},
            )
            x = np.asarray(result.x, dtype=float)
            objective = serial_float(result.fun)
            jac = np.asarray(getattr(result, "jac", []), dtype=float)
            projected = serial_float(np.nanmax(np.abs(jac))) if jac.size and np.isfinite(jac).any() else None
            receipt = {
                "start": start_name,
                "family": family,
                "h_constraint": "free" if h_fixed is None else "h1",
                "success": bool(result.success),
                "status": int(result.status),
                "message": str(result.message),
                "objective": objective,
                "parameters": {
                    "c": serial_float(math.exp(x[0])) if x.size == 3 else None,
                    "h": serial_float(math.exp(x[1])) if x.size == 3 else None,
                    "k": serial_float(math.exp(x[2])) if x.size == 3 else None,
                    "log_c": serial_float(x[0]) if x.size == 3 else None,
                    "log_h": serial_float(x[1]) if x.size == 3 else None,
                    "log_k": serial_float(x[2]) if x.size == 3 else None,
                },
                "initial_parameters": {"c": c0, "h": h0, "k": k0},
                "nfev": int(getattr(result, "nfev", 0)),
                "nit": int(getattr(result, "nit", 0)),
                "bound_contacts": contact_flags(x, bounds) if x.size == 3 else [],
                "raw_gradient_max_abs": projected,
            }
            receipts.append(receipt)
            if bool(result.success) and objective is not None and np.isfinite(objective):
                candidate = dict(receipt)
                candidate["selected_source"] = "finite_k_optimizer"
                qualified.append(candidate)
        except Exception as exc:  # retain failure receipt and continue the history
            receipts.append(
                {
                    "start": start_name,
                    "family": family,
                    "h_constraint": "free" if h_fixed is None else "h1",
                    "success": False,
                    "status": "exception",
                    "message": repr(exc),
                    "objective": None,
                    "parameters": None,
                    "initial_parameters": {"c": c0, "h": h0, "k": k0},
                    "nfev": None,
                    "nit": None,
                    "bound_contacts": [],
                    "raw_gradient_max_abs": None,
                }
            )
    if bool(hom.get("success")) and hom.get("objective") is not None:
        anchor = {
            "start": "exact_homogeneous_limit",
            "family": family,
            "h_constraint": "free" if h_fixed is None else "h1",
            "success": True,
            "status": "analytic",
            "message": "exact homogeneous candidate included in family selection",
            "objective": float(hom["objective"]),
            "parameters": {"c": hom["c"], "h": hom["h"], "k": math.inf},
            "initial_parameters": None,
            "nfev": 0,
            "nit": 0,
            "bound_contacts": hom.get("bound_contacts", []),
            "raw_gradient_max_abs": None,
            "selected_source": "exact_homogeneous_limit",
        }
        receipts.append(anchor)
        qualified.append(anchor)
    if not qualified:
        selected = {
            "success": False,
            "status": "unresolved",
            "message": "no qualified stationary finite-k candidate or homogeneous anchor",
            "objective": None,
            "parameters": None,
            "selected_source": None,
            "bound_contacts": [],
            "raw_gradient_max_abs": None,
        }
    else:
        selected = min(qualified, key=lambda item: float(item["objective"]))
        selected = dict(selected)
        selected["status"] = "selected"
    return selected, receipts


def verify_inputs() -> tuple[dict[str, object], dict[str, np.ndarray], dict[str, object]]:
    public = np.load(PUBLIC / "public_inputs.npz")
    exposure = np.load(PUBLIC / "exposure.npz")
    train = np.asarray(public["site_splits"] == "training")
    if int(train.sum()) != 120:
        raise AssertionError(f"expected 120 training sites, found {train.sum()}")
    site_ids = np.asarray(public["site_ids"])[train]
    clusters = np.asarray(public["site_clusters"])[train]
    unique, counts = np.unique(clusters, return_counts=True)
    if len(unique) != 24 or not np.all(counts == 5):
        raise AssertionError("public site_clusters are not 24 fixed five-site training clusters")
    cluster_map = {label: i for i, label in enumerate(unique.tolist())}
    cluster_int = np.array([cluster_map[label] for label in clusters], dtype=int)
    meta = {
        "public_inputs": str(PUBLIC / "public_inputs.npz"),
        "exposure": str(PUBLIC / "exposure.npz"),
        "training_sites": int(train.sum()),
        "training_clusters": int(len(unique)),
        "training_cluster_sizes": counts.tolist(),
        "training_site_ids_sha256": hashlib.sha256("\n".join(site_ids.tolist()).encode()).hexdigest(),
        "training_cluster_labels_sha256": hashlib.sha256("\n".join(clusters.tolist()).encode()).hexdigest(),
        "site_order": "public_inputs.npz site order, checked against every observations.npz",
    }
    return meta, {"site_ids": site_ids, "cluster_int": cluster_int, "train_mask": train}, {"public": public, "exposure": exposure}


def data_manifest() -> dict[str, object]:
    digest = hashlib.sha256()
    count = 0
    for cell in CELL_ORDER:
        for rep in sorted((BASE / f"cell-{cell}").glob("rep-*")):
            for name in ("main.json", "evaluator.npz", "observations.npz"):
                path = rep / name
                if not path.exists():
                    raise FileNotFoundError(path)
                rel = path.relative_to(ROOT).as_posix()
                digest.update(rel.encode())
                digest.update(b"\0")
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                digest.update(b"\0")
                count += 1
    return {"files": count, "sha256": digest.hexdigest(), "cells": {c: len(list((BASE / f"cell-{c}").glob("rep-*"))) for c in CELL_ORDER}}


def check_labels_and_site_order(site_ids: np.ndarray, train_mask: np.ndarray) -> dict[str, object]:
    for cell, (expected_label, _) in CELL_SPEC.items():
        reps = sorted((BASE / f"cell-{cell}").glob("rep-*"))
        if len(reps) != 500:
            raise AssertionError(f"cell {cell} has {len(reps)} histories, expected 500")
        for rep in reps:
            main = json.loads((rep / "main.json").read_text())
            if main["cell_label"] != expected_label:
                raise AssertionError(f"cell {cell} label mismatch: {main['cell_label']} != {expected_label}")
            obs = np.load(rep / "observations.npz")
            if not np.array_equal(obs["site_ids"], np.asarray(np.load(PUBLIC / "public_inputs.npz")["site_ids"])):
                raise AssertionError(f"site IDs mismatch in {rep}")
            if not np.array_equal(obs["training_mask"], train_mask):
                raise AssertionError(f"training mask mismatch in {rep}")
    return {"all_cells": True, "histories_per_cell": 500, "total_histories": 4000, "labels_verified": True, "site_ids_verified": True}


def fit_history(
    cell: str,
    history_index: int,
    rep: Path,
    beta: float,
    expected_label: str,
    site_ids: np.ndarray,
    cluster_int: np.ndarray,
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    ev = np.load(rep / "evaluator.npz")
    obs = np.load(rep / "observations.npz")
    if not np.array_equal(obs["site_ids"], np.asarray(np.load(PUBLIC / "public_inputs.npz")["site_ids"])):
        raise AssertionError(f"site IDs mismatch at {rep}")
    idx = np.asarray(obs["training_mask"], dtype=bool)
    loss = np.asarray(ev["loss"])[idx]
    arrival = np.asarray(ev["arrival"])[idx]
    w = np.exp(beta * np.asarray(np.load(PUBLIC / "exposure.npz")["site_a"])[idx])
    lost, post_event, pre, post = pieces(loss, arrival)
    dtotal = int(lost.sum())
    hom_free = analytic_homogeneous(w, lost, post_event, pre, post, None)
    hom_h1 = analytic_homogeneous(w, lost, post_event, pre, post, 1.0)
    fits: dict[str, dict[str, object]] = {
        "homogeneous_free": hom_free,
        "homogeneous_h1": hom_h1,
    }
    all_receipts: list[dict[str, object]] = []
    published_rows: list[dict[str, object]] = []
    family_clusters = {"iid_gamma": np.arange(len(w), dtype=int), "cluster_gamma": cluster_int}
    for family, cl in family_clusters.items():
        ncl = int(cl.max()) + 1
        for constraint, h_fixed, hom in (("free", None, hom_free), ("h1", 1.0, hom_h1)):
            selected, receipts = fit_gamma(w, lost, post_event, pre, post, cl, ncl, hom, h_fixed, family)
            key = f"{family}_{constraint}"
            fits[key] = selected
            for receipt in receipts:
                record = dict(receipt)
                record.update({"cell": cell, "cell_label": expected_label, "history_index": history_index, "replicate_path": str(rep.relative_to(ROOT)), "dtotal": dtotal})
                all_receipts.append(record)
            selected["optimizer_failure_count"] = int(sum(not bool(r.get("success")) for r in receipts if r.get("start") != "exact_homogeneous_limit"))
            selected["optimizer_receipt_count"] = int(sum(1 for r in receipts if r.get("start") != "exact_homogeneous_limit"))
            pub = next((r for r in receipts if r.get("start") == "published"), None)
            if pub is not None:
                published_rows.append({
                    "cell": cell, "cell_label": expected_label, "history_index": history_index,
                    "family": family, "constraint": constraint,
                    "published_success": pub.get("success"), "published_status": pub.get("status"),
                    "published_objective": pub.get("objective"),
                    "published_c": (pub.get("parameters") or {}).get("c"),
                    "published_h": (pub.get("parameters") or {}).get("h"),
                    "published_k": (pub.get("parameters") or {}).get("k"),
                    "best_success": selected.get("success"), "best_status": selected.get("status"),
                    "best_objective": selected.get("objective"),
                    "best_c": (selected.get("parameters") or {}).get("c"),
                    "best_h": (selected.get("parameters") or {}).get("h"),
                    "best_k": (selected.get("parameters") or {}).get("k"),
                    "objective_improvement_published_minus_best": (float(pub["objective"]) - float(selected["objective"])) if pub.get("objective") is not None and selected.get("objective") is not None else None,
                    "log_h_best_minus_published": (math.log(float((selected.get("parameters") or {})["h"])) - math.log(float((pub.get("parameters") or {})["h"]))) if selected.get("parameters") and pub.get("parameters") and selected["parameters"].get("h") and pub["parameters"].get("h") else None,
                })
    truth_h = float(expected_label[-1])
    row: dict[str, object] = {"cell": cell, "cell_label": expected_label, "history_index": history_index, "truth_h": truth_h, "dtotal": dtotal, "dpre": int(lost.sum() - post_event.sum()), "dpost": int(post_event.sum()), "spre": float(np.sum(w * pre)), "spost": float(np.sum(w * post))}
    for key, fit in fits.items():
        params = fit.get("parameters") or fit
        h = params.get("h") if isinstance(params, dict) else fit.get("h")
        objective = fit.get("objective")
        row[f"{key}_status"] = fit.get("status")
        row[f"{key}_success"] = bool(fit.get("success"))
        row[f"{key}_objective"] = objective
        row[f"{key}_h"] = h
        row[f"{key}_c"] = params.get("c") if isinstance(params, dict) else fit.get("c")
        row[f"{key}_k"] = params.get("k") if isinstance(params, dict) else fit.get("k")
        row[f"{key}_selected_source"] = fit.get("selected_source", fit.get("profile_source", "analytic"))
        row[f"{key}_bound_contacts"] = ";".join(fit.get("bound_contacts", []))
        row[f"{key}_raw_gradient_max_abs"] = fit.get("raw_gradient_max_abs")
        row[f"{key}_optimizer_failure_count"] = fit.get("optimizer_failure_count", 0)
        row[f"{key}_optimizer_receipt_count"] = fit.get("optimizer_receipt_count", 0)
    # Per-family raw likelihood-ratio diagnostics.  These are explicitly uncalibrated.
    for family in ("homogeneous", "iid_gamma", "cluster_gamma"):
        free = fits[f"{family}_free"]
        h1 = fits[f"{family}_h1"]
        if free.get("objective") is not None and h1.get("objective") is not None:
            raw_t_unclipped = 2.0 * (float(h1["objective"]) - float(free["objective"]))
            row[f"{family}_raw_T_unclipped"] = raw_t_unclipped
            row[f"{family}_raw_T"] = max(0.0, raw_t_unclipped)
            row[f"{family}_raw_T_numerical_clipped"] = bool(raw_t_unclipped < 0.0)
            row[f"{family}_raw_T_severe_negative_failure"] = bool(raw_t_unclipped < -1.0e-7)
            row[f"{family}_raw_T_gt_2_71_uncalibrated"] = bool(row[f"{family}_raw_T"] > 2.71)
        else:
            row[f"{family}_raw_T_unclipped"] = None
            row[f"{family}_raw_T"] = None
            row[f"{family}_raw_T_numerical_clipped"] = False
            row[f"{family}_raw_T_severe_negative_failure"] = False
            row[f"{family}_raw_T_gt_2_71_uncalibrated"] = None
    return row, all_receipts, published_rows


def check_numerics() -> dict[str, object]:
    rng = np.random.default_rng(20261018)
    max_identity = 0.0
    identity_rows = []
    for k in (0.05, 1.65, 20.0, 1000.0):
        for d in range(0, 7):
            lhs = stable_integer_loggamma_ratio(k, d)
            rhs = float(gammaln(k + d) - gammaln(k))
            err = abs(lhs - rhs)
            max_identity = max(max_identity, err)
            identity_rows.append({"k": k, "D": d, "error": err})
    w = np.exp(rng.normal(size=12))
    lost = rng.random(12) < 0.4
    post_event = lost & (rng.random(12) < 0.4)
    pre = rng.uniform(0.0, 50.0, size=12)
    post = rng.uniform(0.0, 60.0, size=12)
    cl = np.repeat(np.arange(4), 3)
    max_formula = 0.0
    for k in (0.05, 1.65, 20.0, 1000.0):
        theta = np.array([math.log(0.003), math.log(2.0), math.log(k)])
        err = abs(gamma_nll(theta, w, lost, post_event, pre, post, cl, 4) - gamma_nll_scipy(theta, w, lost, post_event, pre, post, cl, 4))
        max_formula = max(max_formula, err)
    # Gamma integrated likelihood converges to homogeneous likelihood at a large k.
    theta_h = np.array([math.log(0.003), math.log(2.0), math.log(1.0e12)])
    hom = homogeneous_nll(theta_h[0], theta_h[1], w, lost, post_event, pre, post)
    lim_err = abs(gamma_nll(theta_h, w, lost, post_event, pre, post, cl, 4) - hom)
    return {
        "stable_loggamma_ratio_max_abs_error": max_identity,
        "stable_vs_scipy_nll_max_abs_error": max_formula,
        "gamma_to_homogeneous_k1e12_abs_error": lim_err,
        "checks_pass": bool(max_identity < 1e-10 and max_formula < 1e-10 and lim_err < 1e-8),
        "identity_examples": identity_rows,
    }


def mean_mcse(values: list[float]) -> dict[str, object]:
    if not values:
        return {"n": 0, "mean": None, "mcse": None}
    arr = np.asarray(values, dtype=float)
    return {"n": int(arr.size), "mean": float(arr.mean()), "mcse": float(arr.std(ddof=1) / math.sqrt(arr.size)) if arr.size > 1 else 0.0}


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    models = ("homogeneous", "iid_gamma", "cluster_gamma")
    summary: dict[str, object] = {"total_histories": len(rows), "cells": {}, "models": {}, "raw_T_threshold": 2.71, "raw_T_label": "uncalibrated diagnostic; not a formal false-positive guarantee"}
    for cell in CELL_ORDER:
        cr = [r for r in rows if r["cell"] == cell]
        cell_summary: dict[str, object] = {"n_histories": len(cr), "models": {}}
        for model in models:
            fitvals = [r for r in cr if r[f"{model}_free_success"] and r[f"{model}_free_h"] is not None]
            errors = [math.log(float(r[f"{model}_free_h"]) / float(r["truth_h"])) for r in fitvals]
            abs_errors = [abs(x) for x in errors]
            hvals = [float(r[f"{model}_free_h"]) for r in fitvals]
            failures = sum(not bool(r[f"{model}_free_success"]) or r[f"{model}_free_h"] is None for r in cr)
            optimizer_failures = sum(int(r.get(f"{model}_free_optimizer_failure_count", 0)) for r in cr)
            optimizer_receipts = sum(int(r.get(f"{model}_free_optimizer_receipt_count", 0)) for r in cr)
            nested = sum(r[f"{model}_free_selected_source"] == "exact_homogeneous_limit" for r in cr)
            boundaries = sum(h <= 1.0 + 1e-8 or h >= 10.0 - 1e-8 for h in hvals)
            ts = [float(r[f"{model}_raw_T"]) for r in cr if r[f"{model}_raw_T"] is not None]
            cell_summary["models"][model] = {
                "denominator": len(cr),
                "selected_finite_estimate_n": len(errors),
                "mean_signed_log_error": float(np.mean(errors)) if errors else None,
                "mean_absolute_log_error": float(np.mean(abs_errors)) if abs_errors else None,
                "mcse_signed_log_error": float(np.std(errors, ddof=1) / math.sqrt(len(errors))) if len(errors) > 1 else (0.0 if errors else None),
                "boundary_rate": boundaries / len(cr),
                "failure_or_unresolved_rate": failures / len(cr),
                "optimizer_failed_start_count": optimizer_failures,
                "optimizer_start_count": optimizer_receipts,
                "optimizer_failed_start_rate": optimizer_failures / optimizer_receipts if optimizer_receipts else None,
                "nested_limit_selection_rate": nested / len(cr),
                "raw_T_gt_2_71_count": int(sum(t > 2.71 for t in ts)),
                "raw_T_gt_2_71_rate": float(sum(t > 2.71 for t in ts) / len(cr)),
                "raw_T_available_n": len(ts),
            }
        summary["cells"][cell] = cell_summary
    for model in models:
        vals = [math.log(float(r[f"{model}_free_h"]) / float(r["truth_h"])) for r in rows if r[f"{model}_free_success"] and r[f"{model}_free_h"] is not None]
        summary["models"][model] = {
            "denominator": len(rows),
            "selected_finite_estimate_n": len(vals),
            "mean_signed_log_error": float(np.mean(vals)) if vals else None,
            "mean_absolute_log_error": float(np.mean(np.abs(vals))) if vals else None,
            "mcse_signed_log_error": float(np.std(vals, ddof=1) / math.sqrt(len(vals))) if len(vals) > 1 else (0.0 if vals else None),
            "failure_or_unresolved_rate": sum(not bool(r[f"{model}_free_success"]) or r[f"{model}_free_h"] is None for r in rows) / len(rows),
            "optimizer_failed_start_count": sum(int(r.get(f"{model}_free_optimizer_failure_count", 0)) for r in rows),
            "optimizer_start_count": sum(int(r.get(f"{model}_free_optimizer_receipt_count", 0)) for r in rows),
            "optimizer_failed_start_rate": (sum(int(r.get(f"{model}_free_optimizer_failure_count", 0)) for r in rows) / sum(int(r.get(f"{model}_free_optimizer_receipt_count", 0)) for r in rows)) if sum(int(r.get(f"{model}_free_optimizer_receipt_count", 0)) for r in rows) else None,
            "selected_candidate_source_counts": dict(__import__("collections").Counter(r[f"{model}_free_selected_source"] for r in rows)),
            "selected_bound_contact_counts": dict(__import__("collections").Counter(r[f"{model}_free_bound_contacts"] for r in rows)),
            "selected_raw_gradient_max_abs_quantiles": ({
                "q50": float(np.quantile([float(r[f"{model}_free_raw_gradient_max_abs"]) for r in rows if r[f"{model}_free_raw_gradient_max_abs"] not in (None, "")], 0.5)),
                "q95": float(np.quantile([float(r[f"{model}_free_raw_gradient_max_abs"]) for r in rows if r[f"{model}_free_raw_gradient_max_abs"] not in (None, "")], 0.95)),
                "n": len([r for r in rows if r[f"{model}_free_raw_gradient_max_abs"] not in (None, "")]),
            } if any(r[f"{model}_free_raw_gradient_max_abs"] not in (None, "") for r in rows) else None),
            "selected_raw_gradient_interior_quantiles": ({
                "q50": float(np.quantile([float(r[f"{model}_free_raw_gradient_max_abs"]) for r in rows if not r[f"{model}_free_bound_contacts"] and r[f"{model}_free_raw_gradient_max_abs"] not in (None, "")], 0.5)),
                "q95": float(np.quantile([float(r[f"{model}_free_raw_gradient_max_abs"]) for r in rows if not r[f"{model}_free_bound_contacts"] and r[f"{model}_free_raw_gradient_max_abs"] not in (None, "")], 0.95)),
                "n": len([r for r in rows if not r[f"{model}_free_bound_contacts"] and r[f"{model}_free_raw_gradient_max_abs"] not in (None, "")]),
            } if any(not r[f"{model}_free_bound_contacts"] and r[f"{model}_free_raw_gradient_max_abs"] not in (None, "") for r in rows) else None),
            "uniqueness_certified": False,
            "uniqueness_note": "multi-start optimizer agreement and stationarity receipts do not certify a unique or global MLE; nonlocal ambiguity remains untested",
            "nested_limit_selection_rate": sum(r[f"{model}_free_selected_source"] == "exact_homogeneous_limit" for r in rows) / len(rows),
            "raw_T_gt_2_71_count": int(sum(bool(r[f"{model}_raw_T_gt_2_71_uncalibrated"]) for r in rows)),
            "raw_T_gt_2_71_rate": float(sum(bool(r[f"{model}_raw_T_gt_2_71_uncalibrated"]) for r in rows) / len(rows)),
        }
    contrasts = {}
    for left, right in (("iid_gamma", "homogeneous"), ("cluster_gamma", "homogeneous"), ("cluster_gamma", "iid_gamma")):
        key = f"{left}_minus_{right}_log_h"
        allv = []
        bycell = {}
        for cell in CELL_ORDER:
            vals = []
            for r in rows:
                if r["cell"] == cell and r[f"{left}_free_h"] is not None and r[f"{right}_free_h"] is not None:
                    vals.append(math.log(float(r[f"{left}_free_h"])) - math.log(float(r[f"{right}_free_h"])))
            allv.extend(vals)
            bycell[cell] = mean_mcse(vals)
        contrasts[key] = {"all_cells": mean_mcse(allv), "by_cell": bycell}
    summary["paired_contrasts"] = contrasts
    all_t = [float(r[f"{model}_raw_T"]) for model in models for r in rows if r[f"{model}_raw_T"] is not None]
    clipped = [r for model in models for r in rows if r[f"{model}_raw_T_numerical_clipped"]]
    unclipped = [float(r[f"{model}_raw_T_unclipped"]) for model in models for r in rows if r[f"{model}_raw_T_unclipped"] is not None]
    severe = [t for t in unclipped if t < -1.0e-7]
    summary["raw_T_checks"] = {"minimum_T": float(min(all_t)), "negative_T_count_after_clipping": int(sum(t < 0 for t in all_t)), "numerical_clipping_count": len(clipped), "unclipped_minimum_T": float(min(unclipped)), "severe_negative_threshold": -1.0e-7, "severe_negative_failure_count": len(severe), "severe_negative_failure": bool(severe), "nonnegative_after_clipping": bool(all(t >= 0 for t in all_t))}
    return summary


def main() -> None:
    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    numerical = check_numerics()
    meta, arrays, sources = verify_inputs()
    labels = check_labels_and_site_order(arrays["site_ids"], arrays["train_mask"])
    manifest = data_manifest()
    protocol_context = CLAUDE / "protocol-at-frailty-run.md"
    if not protocol_context.exists():
        protocol_context = ROOT / "docs/paper1-integrated-tranche-protocol-2026-10-18.md"
    source_files = [SCRIPT, CLAUDE / "claude-frailty-check.py", CLAUDE / "claude-cluster-frailty-check.py", protocol_context]
    source_receipt = {
        "script": str(SCRIPT.relative_to(ROOT)),
        "source_hashes": {str(p.relative_to(ROOT)): sha256_file(p) for p in source_files},
        "input_hashes": {"public_inputs.npz": sha256_file(PUBLIC / "public_inputs.npz"), "exposure.npz": sha256_file(PUBLIC / "exposure.npz")},
        "history_data_manifest": manifest,
        "site_cluster_identity": meta,
        "runtime": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__},
        "design": {"cells": CELL_SPEC, "histories_per_cell": 500, "total_histories": 4000, "window": [-60, 60], "training_sites": 120, "h_bounds": [1, 10], "k_bounds": [0.05, 10000], "families": ["homogeneous", "iid_gamma", "cluster_gamma"], "no_new_histories": True},
    }
    write_json(OUT / "source_input_hashes.json", source_receipt)
    write_json(OUT / "verification.json", {"numerical": numerical, "labels_and_inputs": labels, "source_input_hashes": source_receipt})
    if not numerical["checks_pass"]:
        raise AssertionError(f"numerical identity checks failed: {numerical}")
    rows: list[dict[str, object]] = []
    receipts_path = OUT / "optimizer_receipts.jsonl"
    published: list[dict[str, object]] = []
    with receipts_path.open("w") as receipts_handle:
        for cell, (expected_label, beta) in CELL_SPEC.items():
            reps = sorted((BASE / f"cell-{cell}").glob("rep-*"))
            for history_index, rep in enumerate(reps):
                row, history_receipts, published_rows = fit_history(cell, history_index, rep, beta, expected_label, arrays["site_ids"], arrays["cluster_int"])
                rows.append(row)
                published.extend(published_rows)
                for receipt in history_receipts:
                    receipts_handle.write(json.dumps(receipt, sort_keys=True) + "\n")
            print(f"completed cell {cell} ({expected_label})", flush=True)
    # Stable CSV field order is determined by first row insertion order.
    with (OUT / "per_history.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    with (OUT / "first20_published_comparison.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(published[0]), extrasaction="ignore")
        writer.writeheader()
        writer.writerows([r for r in published if int(r["history_index"]) < 20])
    summary = summarize(rows)
    summary.update({"runtime_seconds": time.time() - started, "numerical_checks": numerical, "input_labels": labels, "source_manifest": manifest})
    write_json(OUT / "summary.json", summary)
    print(json.dumps({"completed": len(rows), "receipts": sum(1 for _ in receipts_path.open()), "runtime_seconds": round(time.time() - started, 2), "output": str(OUT.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
