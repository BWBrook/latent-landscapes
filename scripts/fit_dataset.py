"""Production analysis entry point: three model families, cutoff-indexed sets, failure class.

One dataset in, one ``receipt.json`` out.  The spatial envelope is searched by the
development ``PanelSearch`` (adaptive mesh, peak refinement, family-switch and
topology discovery, envelope closure and the tight same-h replay) on the cutoff
grid below.  The exposure-linked (sigma = 0) and constant (sigma = 0, beta = 0)
families have no latent solve, so their free fits, h = 1 fits, profile statistics
and cutoff sets are computed here on the union of the search nodes and a 35-node
geometric mesh on [1, 30].

The tight replay is part of ``PanelSearch.run`` and cannot be skipped without
editing it; the receipt records the time spent before it starts.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import importlib.util
import json
import math
import os
import platform
import resource
import sys
import time
import traceback
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import benchmark_spatial_profile as adapter
import numpy as np
from profile_level_sets import refine_level_set
from qualify_spatial_profiles import (
    DEFAULTS,
    FAMILIES,
    LOG_MAX,
    ROOT,
    bound_contacts,
    parameters,
    write_json,
)
from run_development_profile import PanelSearch, load_panel_data
from scipy.optimize import minimize_scalar  # type: ignore[import-untyped]

from latent_landscapes.spatial_profile import (
    CurveDomainError,
    FitCandidate,
    SpatialProfileCriterion,
    _floored_eigenvalues,
)

SCHEMA = "fit-dataset-v1"
CUTOFF_GRID = (2.71, 3.84, 5.02, 6.63, 7.88, 9.55, 12.0, 15.0)
TIE_TOLERANCE = 1e-4
MODE_AUDIT_SIGMA_MIN = 1e-3
# Production audits skip locations whose envelope LR exceeds the largest cutoff by
# this margin: a missed mode there would need a criterion gain above 5 to change
# any level set. The margin is empirical; qualification measures it by auditing a
# predeclared subset with no limit (--exhaustive-audit).
MODE_AUDIT_LR_MARGIN = 10.0
EXECUTION_ERRORS = (MemoryError, OSError)
FAILURE_CLASSES = (
    "resolved",
    "search_unresolved",
    "multimodal_latent",
    "family_fit_failed",
    "numerical_error",
    "execution_error",
)
MODE_DIAGNOSIS = ROOT / "docs/evidence/paper1-sprint1-2026-11-05/mode_diagnosis.py"
THREAD_ENVIRONMENT = ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_NUM_THREADS")


class FitSearch(PanelSearch):
    cutoffs = CUTOFF_GRID  # type: ignore[assignment]


def geometric_mesh() -> list[float]:
    return [float(x) for x in np.linspace(0.0, LOG_MAX, 35)]


def summarise_level(level: dict[str, Any]) -> dict[str, Any]:
    available = level["status"] == "available"
    components = [
        {
            key: component[key]
            for key in (
                "lower_h",
                "upper_h",
                "lower_log_h",
                "upper_log_h",
                "lower_domain_contact",
                "upper_domain_contact",
                "singleton",
            )
        }
        for component in (level.get("components") or [])
    ]
    return {
        "cutoff": level["cutoff"],
        "status": level["status"],
        "set_class": level.get("set_class"),
        "roots_h": [root["h"] for root in level["roots"]],
        "roots_log_h": [root["log_h"] for root in level["roots"]],
        "components": components,
        "touches_h1": any(c["lower_domain_contact"] for c in components) if available else None,
        "touches_h30": any(c["upper_domain_contact"] for c in components) if available else None,
        "empty": not components if available else None,
        "failure": level.get("failure"),
    }


def tie_adjusted(fit: dict[str, Any]) -> tuple[bool, dict[str, list[str]]]:
    """Return the tie flag and nuisance contacts with the redundant lower contact removed."""
    tied = abs(fit["positive_sigma"]["criterion"] - fit["sigma_zero"]["criterion"]) <= TIE_TOLERANCE
    positive = [
        contact
        for contact in fit["positive_sigma"]["nuisance_bound_contacts"]
        if not (tied and contact == "log_sigma:lower")
    ]
    return tied, {
        "positive_sigma": positive,
        "sigma_zero": list(fit["sigma_zero"]["nuisance_bound_contacts"]),
    }


def owner_contacts(fit: dict[str, Any]) -> dict[str, Any]:
    tied, adjusted = tie_adjusted(fit)
    owners = [f for f in FAMILIES if fit["criterion"] - fit[f]["criterion"] <= TIE_TOLERANCE]
    return {
        "tied": tied,
        "owners": owners,
        "nuisance_contacts_raw": {f: fit[f]["nuisance_bound_contacts"] for f in owners},
        "nuisance_contacts": {f: adjusted[f] for f in owners},
        "h_domain_contacts": {f: fit[f]["h_domain_contacts"] for f in owners},
    }


def family_row(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "family",
        "h",
        "criterion",
        "parameters",
        "eligible",
        "bound_contacts",
        "nuisance_bound_contacts",
        "h_domain_contacts",
        "projected_gradient_inf",
        "optimizer_success",
        "optimizer_message",
        "source",
    )
    return {key: row[key] for key in keys if key in row}


def with_contacts(row: dict[str, Any], *, free: bool) -> dict[str, Any]:
    if "nuisance_bound_contacts" not in row:
        contacts = bound_contacts(row, free=free)
        row = {
            **row,
            "bound_contacts": contacts,
            "nuisance_bound_contacts": [c for c in contacts if not c.startswith("log_h:")],
            "h_domain_contacts": ["lower"]
            if row["h"] == 1.0
            else ["upper"]
            if row["h"] == 30.0
            else [],
        }
    return row


class ReducedFamily:
    """sigma = 0 families without a latent solve: exposure-linked or constant (beta = 0)."""

    def __init__(
        self,
        name: str,
        criterion: SpatialProfileCriterion,
        *,
        beta_free: bool,
        seed_rows: dict[float, dict[str, Any]] | None = None,
        free_seeds: list[dict[str, Any]] | None = None,
    ):
        self.name = name
        self.criterion = criterion
        self.beta_free = beta_free
        self.seed_rows = seed_rows or {}
        self.free_seeds = free_seeds or []
        self.points: dict[float, dict[str, Any]] = {}
        self.free: dict[str, Any] | None = None
        self.fit_count = 0
        self.peak_refinements: list[dict[str, Any]] = []
        self.closure_history: list[dict[str, Any]] = []

    def _fit_constant(
        self,
        fixed_h: float | None,
        starts: list[np.ndarray],
        prefix: str,
        kkt: float,
        maxiter: int,
    ) -> list[FitCandidate]:
        criterion = self.criterion
        bounds_full = criterion._bounds(fixed_h, True)
        keep = [i for i in range(len(bounds_full)) if i != 1]
        bounds = [bounds_full[i] for i in keep]

        def evaluate(reduced: np.ndarray) -> Any:
            full = np.insert(reduced, 1, 0.0)
            try:
                result = criterion.evaluate_sigma_zero(full, fixed_h=fixed_h, nuisance_fd=True)
            except (CurveDomainError, FloatingPointError, ValueError) as exc:
                h = math.nan if fixed_h is None else float(fixed_h)
                result = criterion._invalid(
                    full, sigma_zero=True, h=h, detection_sd=float(full[-1]), message=str(exc)
                )
            return dataclasses.replace(
                result,
                parameters=np.asarray(reduced, dtype=np.float64).copy(),
                criterion_gradient=result.criterion_gradient[keep],
                objective_gradient=result.objective_gradient[keep],
            )

        rows = []
        for index, start in enumerate(starts):
            reduced_start = np.delete(np.asarray(start, dtype=np.float64), 1)
            x, evaluation, result = criterion._trust_region(
                evaluate, reduced_start, bounds, maxiter=maxiter, gradient_tolerance=0.1 * kkt
            )
            projected = (
                criterion._projected_gradient_inf(evaluation.objective_gradient, x, bounds)
                if evaluation.success
                else math.inf
            )
            rows.append(
                FitCandidate(
                    "sigma_zero",
                    f"{prefix}_fit_{index}",
                    np.insert(x, 1, 0.0),
                    evaluation,
                    bool(result.success),
                    str(result.message),
                    int(result.nit),
                    int(result.nfev),
                    projected,
                    bool(evaluation.success and projected <= kkt),
                )
            )
        return rows

    def _fit(self, fixed_h: float | None, starts: list[np.ndarray], prefix: str) -> dict[str, Any]:
        self.fit_count += 1
        unique: list[np.ndarray] = []
        for start in starts:
            if not any(np.array_equal(start, old) for old in unique):
                unique.append(start)
        if self.beta_free:
            candidates = self.criterion._fit_family(
                fixed_h=fixed_h,
                sigma_zero=True,
                starts=unique,
                kkt_tolerance=1e-4,
                maxiter=120,
                source_prefix=prefix,
            )
        else:
            candidates = self._fit_constant(fixed_h, unique, prefix, 1e-4, 120)
        rows = [
            adapter._candidate_summary(row, family_max=0.0, global_max=0.0) for row in candidates
        ]
        eligible = [r for r in rows if r["eligible"] and math.isfinite(r["criterion"])]
        if not eligible:
            raise RuntimeError(f"unresolved {self.name} family fit")
        best = max(eligible, key=lambda r: r["criterion"])
        if any(
            not r["eligible"]
            and math.isfinite(r["criterion"])
            and r["criterion"] > best["criterion"] + 1e-4
            for r in rows
        ):
            raise RuntimeError(f"unresolved {self.name} candidate exceeds the family envelope")
        return with_contacts(dict(best), free=fixed_h is None)

    def _starts(self, x: float, *, free: bool) -> list[np.ndarray]:
        default = DEFAULTS["sigma_zero"]
        starts: list[np.ndarray] = []
        if free:
            starts.extend(np.insert(default, -1, v) for v in (0.0, LOG_MAX / 2, LOG_MAX))
            starts.extend(parameters(row, free=True) for row in self.free_seeds)
            if self.free is not None:
                starts.append(parameters(self.free, free=True))
            ranked = sorted(self.points.items(), key=lambda kv: -kv[1]["criterion"])[:3]
            starts.extend(np.insert(parameters(row), -1, nx) for nx, row in ranked)
            return starts
        known = sorted(self.points)
        left = [k for k in known if k < x]
        right = [k for k in known if k > x]
        near = ([max(left)] if left else []) + ([min(right)] if right else [])
        starts.extend(parameters(self.points[k]) for k in near)
        if x in self.seed_rows:
            starts.insert(0, parameters(self.seed_rows[x]))
        starts.append(default)
        return starts

    def point(self, log_h: float) -> dict[str, Any]:
        x = float(log_h)
        if x in self.points:
            return self.points[x]
        seed = self.seed_rows.get(x)
        if seed is not None and seed.get("tight_converged"):
            row = with_contacts(dict(seed), free=False)
        else:
            row = self._fit(
                min(30.0, math.exp(x)), self._starts(x, free=False), f"{self.name}_{x.hex()}"
            )
        self.points[x] = row
        return row

    def fit_free(self) -> None:
        best = self._fit(None, self._starts(0.0, free=True), f"{self.name}_free")
        if self.free is None or best["criterion"] > self.free["criterion"]:
            self.free = best

    def w(self, log_h: float) -> float:
        assert self.free is not None
        return float(2.0 * (self.free["criterion"] - self.point(log_h)["criterion"]))

    def refine_peaks(self) -> None:
        nodes = sorted(self.points)
        brackets = {
            (nodes[i - 1], nodes[i + 1])
            for i in range(1, len(nodes) - 1)
            if self.points[nodes[i]]["criterion"]
            > max(self.points[nodes[i - 1]]["criterion"], self.points[nodes[i + 1]]["criterion"])
            + 1e-4
        }
        for left, right in sorted(brackets):
            optimized = minimize_scalar(
                lambda x: -self.point(float(x))["criterion"],
                bounds=(left, right),
                method="bounded",
                options={"xatol": 1e-4, "maxiter": 80},
            )
            self.peak_refinements.append(
                {
                    "bracket_log_h": [left, right],
                    "success": bool(optimized.success),
                    "log_h": float(optimized.x),
                }
            )
            if not optimized.success:
                raise RuntimeError(f"bounded {self.name} peak refinement failed")

    def violations(self) -> list[float]:
        assert self.free is not None
        return [
            x for x, row in self.points.items() if row["criterion"] > self.free["criterion"] + 1e-4
        ]

    def run(self, nodes: list[float], cutoffs: tuple[float, ...]) -> list[dict[str, Any]]:
        for x in nodes:
            self.point(x)
        self.fit_free()
        self.refine_peaks()
        self.fit_free()
        for iteration in range(4):
            mesh = sorted(self.points)
            levels = [refine_level_set(self.w, mesh, c, xtol=1e-4) for c in cutoffs]
            before = self.free["criterion"] if self.free else math.nan
            self.fit_free()
            assert self.free is not None
            shift = self.free["criterion"] - before
            bad = self.violations()
            self.closure_history.append(
                {"iteration": iteration, "free_shift": shift, "envelope_violations_log_h": bad}
            )
            if abs(shift) <= 1e-6 and not bad:
                return [summarise_level(level) for level in levels]
        raise RuntimeError(f"{self.name} free maximum or level sets did not stabilise")

    def result(self, levels: list[dict[str, Any]]) -> dict[str, Any]:
        assert self.free is not None
        null = self.point(0.0)
        return {
            "status": "available",
            "free": family_row(self.free),
            "null": family_row(null),
            "lr1": 2.0 * (self.free["criterion"] - null["criterion"]),
            "profile": [
                {
                    "log_h": x,
                    "h": row["h"],
                    "criterion": row["criterion"],
                    "w": self.w(x),
                    "eligible": row["eligible"],
                    "nuisance_bound_contacts": row["nuisance_bound_contacts"],
                }
                for x, row in sorted(self.points.items())
            ],
            "level_sets": levels,
            "peak_refinements": self.peak_refinements,
            "closure_history": self.closure_history,
            "fit_count": self.fit_count,
        }


def spatial_family_result(search: PanelSearch) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "unavailable"}
    for key, tight in (("standard", False), ("tight", True)):
        if tight not in search.free or 0.0 not in search.points[tight]:
            continue
        free, null = search.free[tight], search.points[tight][0.0]
        selected = max(FAMILIES, key=lambda f: free[f]["criterion"])
        result[key] = {
            "free": {
                "criterion": free["criterion"],
                "selected_family": selected,
                "h": free[selected]["h"],
                "positive_sigma": family_row(free["positive_sigma"]),
                "sigma_zero": family_row(free["sigma_zero"]),
                **owner_contacts(free),
            },
            "null": {
                "criterion": null["criterion"],
                "positive_sigma": family_row(null["positive_sigma"]),
                "sigma_zero": family_row(null["sigma_zero"]),
                **owner_contacts(null),
            },
            "lr1": 2.0 * (free["criterion"] - null["criterion"]),
            "profile": [
                {
                    "log_h": x,
                    "h": fit["h"],
                    "criterion": fit["criterion"],
                    "w": search.lr(x, tight=tight),
                    "criterion_positive": fit["positive_sigma"]["criterion"],
                    "criterion_zero": fit["sigma_zero"]["criterion"],
                    **owner_contacts(fit),
                }
                for x, fit in sorted(search.points[tight].items())
            ],
        }
        levels = search.result.get("tight_level_sets" if tight else "level_sets")
        if levels:
            summaries = [summarise_level(level) for level in levels]
            result[key]["level_sets"] = summaries
            result[key]["level_set_contacts"] = [
                {
                    "cutoff": level["cutoff"],
                    "roots": [
                        {
                            "log_h": root["log_h"],
                            **owner_contacts(search.point(root["log_h"], tight=tight)),
                        }
                        for root in level["roots"]
                    ],
                    "inside": sorted(
                        {
                            (f, c)
                            for x, fit in search.points[tight].items()
                            if search.lr(x, tight=tight) <= level["cutoff"]
                            for f, cs in owner_contacts(fit)["nuisance_contacts"].items()
                            for c in cs
                        }
                    ),
                }
                for level in levels
            ]
        result["status"] = "available"
    return result


def load_mode_diagnosis() -> Any:
    spec = importlib.util.spec_from_file_location("sprint1_mode_diagnosis", MODE_DIAGNOSIS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def floored_laplace(
    criterion: SpatialProfileCriterion,
    eta0: np.ndarray,
    precision: np.ndarray,
    curves: Any,
    sigma: float,
    u: np.ndarray,
) -> float:
    """The production criterion (joint minus half the floored log-determinant) at u."""
    ell, _, curvature, _ = curves.evaluate(eta0 + u)
    c_cholesky = sigma * criterion._k_cholesky
    combined = criterion._identity - c_cholesky.T @ (curvature[:, None] * c_cholesky)
    eigenvalues = np.linalg.eigvalsh(combined)
    if float(eigenvalues.min()) <= 0.0:
        return -math.inf
    floored, _ = _floored_eigenvalues(eigenvalues)
    joint = float(np.sum(ell) - 0.5 * u @ precision @ u)
    return joint - 0.5 * float(np.log(floored).sum())


def latent_audit(
    criterion: SpatialProfileCriterion, row: dict[str, Any], diagnosis: Any
) -> dict[str, Any]:
    params, h = row["parameters"], float(row["h"])
    sigma = math.exp(params["log_sigma"])
    if sigma <= MODE_AUDIT_SIGMA_MIN:
        return {"performed": False, "sigma": sigma, "multimodal_latent": False}
    curves = criterion.curves(h, params["detection_sd"])
    eta0 = params["alpha"] + params["beta"] * criterion.data.exposure
    precision = criterion._k_inverse / sigma**2
    starts = diagnosis.starts_for(criterion, eta0, precision, curves, sigma, params, h)
    reference = criterion._mode_branch(eta0, precision, curves, np.zeros(criterion.site_count))
    if reference is None:
        raise RuntimeError("reported fit has no strictly converged zero-start latent mode")
    u_ref, joint_ref = reference[0], reference[1]
    laplace_ref = floored_laplace(criterion, eta0, precision, curves, sigma, u_ref)
    rows = []
    flagged = False
    for name, start in starts.items():
        branch = criterion._mode_branch(eta0, precision, curves, start)
        if branch is None:
            rows.append({"start": name, "converged": False})
            continue
        du = float(np.max(np.abs(branch[0] - u_ref)))
        delta = float(branch[1] - joint_ref)
        delta_laplace = floored_laplace(criterion, eta0, precision, curves, sigma, branch[0])
        higher = delta > 1e-6 and du > 1e-3
        flagged |= higher
        rows.append(
            {
                "start": name,
                "converged": True,
                "joint_minus_reported": delta,
                "criterion_minus_reported": delta_laplace - laplace_ref,
                "max_abs_du": du,
                "higher_distinct_mode": higher,
            }
        )
    return {
        "performed": True,
        "sigma": sigma,
        "h": h,
        "reported_joint": joint_ref,
        "starts": rows,
        "multimodal_latent": flagged,
    }


def audit_all(search: PanelSearch, diagnosis: Any, *, exhaustive: bool = False) -> dict[str, Any]:
    """Audit the positive-sigma fit at every retained point, free fit and cutoff root."""
    root_x = {
        (key == "tight_level_sets", root["log_h"])
        for key in ("level_sets", "tight_level_sets")
        for level in search.result.get(key, [])
        for root in level["roots"]
    }
    locations: list[tuple[str, bool, float | None, dict[str, Any]]] = []
    for tight, free in search.free.items():
        locations.append(("free", tight, None, free["positive_sigma"]))
    for tight, points in search.points.items():
        for x, fit in sorted(points.items()):
            locations.append(
                ("root" if (tight, x) in root_x else "point", tight, x, fit["positive_sigma"])
            )
    lr_limit = math.inf if exhaustive else max(CUTOFF_GRID) + MODE_AUDIT_LR_MARGIN
    started, cpu = time.perf_counter(), time.process_time()
    rows = []
    for kind, regime, loc, row in locations:
        free = search.free[regime]
        fit = free if loc is None else search.points[regime][loc]
        top = max(free[f]["criterion"] for f in ("positive_sigma", "sigma_zero"))
        lr = 2.0 * (top - max(fit[f]["criterion"] for f in ("positive_sigma", "sigma_zero")))
        sigma = math.exp(row["parameters"]["log_sigma"])
        location_started = time.perf_counter()
        if kind == "free" or lr <= lr_limit:
            audit = latent_audit(search.criterion, row, diagnosis)
        else:
            audit = {"performed": False, "sigma": sigma, "multimodal_latent": False}
        record: dict[str, Any] = {
            "kind": kind,
            "tight": regime,
            "log_h": loc if loc is not None else math.log(row["h"]),
            "envelope_lr": lr,
            "beyond_lr_limit": kind != "free" and lr > max(CUTOFF_GRID) + MODE_AUDIT_LR_MARGIN,
            "performed": audit["performed"],
            "sigma": audit["sigma"],
            "seconds": time.perf_counter() - location_started,
            "multimodal_latent": audit["multimodal_latent"],
        }
        if audit["performed"]:
            converged = [r for r in audit["starts"] if r["converged"]]
            record["max_joint_gain"] = max(r["joint_minus_reported"] for r in converged)
            record["max_criterion_gain"] = max(r["criterion_minus_reported"] for r in converged)
        if audit["multimodal_latent"]:
            record["starts"] = audit["starts"]
        rows.append(record)
    return {
        "lr_limit": lr_limit,
        "exhaustive": exhaustive,
        "audit_count": sum(r["performed"] for r in rows),
        "skipped_beyond_lr_limit": sum(r["beyond_lr_limit"] for r in rows),
        "locations": len(rows),
        "wall_seconds": time.perf_counter() - started,
        "cpu_seconds": time.process_time() - cpu,
        "multimodal_latent": any(r["multimodal_latent"] for r in rows),
        "flagged": [r for r in rows if r["multimodal_latent"]],
        "rows": rows,
    }


def classify(
    *,
    search_status: str | None,
    search_failure: dict[str, Any] | None,
    family_failures: list[str],
    multimodal: bool,
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    flags: list[str] = []
    messages: dict[str, str] = {}
    for kind, group in (
        ("execution_error", [e for e in errors if e.get("execution")]),
        ("numerical_error", [e for e in errors if not e.get("execution")]),
    ):
        if group:
            flags.append(kind)
            messages[kind] = "; ".join(f"{e['stage']}: {e['message']}" for e in group)
    family_flag = bool(family_failures)
    if search_failure and search_failure["message"].startswith("unresolved variance family"):
        family_flag = True
        family_failures = [*family_failures, f"spatial: {search_failure['message']}"]
    if family_flag:
        flags.append("family_fit_failed")
        messages["family_fit_failed"] = "; ".join(family_failures)
    if search_status != "profile_numerically_resolved" and not (
        search_failure and search_failure["message"].startswith("unresolved variance family")
    ):
        flags.append("search_unresolved")
        messages["search_unresolved"] = (
            f"status {search_status}: {search_failure['message']}"
            if search_failure
            else f"status {search_status}"
        )
    if multimodal:
        flags.append("multimodal_latent")
        messages["multimodal_latent"] = (
            "a strictly converged latent mode has higher joint objective"
        )
    order = (
        "execution_error",
        "numerical_error",
        "family_fit_failed",
        "search_unresolved",
        "multimodal_latent",
    )
    chosen = next((c for c in order if c in flags), "resolved")
    return {
        "failure_class": chosen,
        "message": messages.get(chosen),
        "all_triggered": flags,
        "messages": messages,
    }


def tight_phase_seconds(events: Path) -> float | None:
    if not events.exists():
        return None
    with events.open() as handle:
        for line in handle:
            if '"tight": true' in line:
                return float(json.loads(line)["elapsed_seconds"])
    return None


class Run:
    def __init__(self) -> None:
        self.receipt: dict[str, Any] = {"schema": SCHEMA}
        self.errors: list[dict[str, Any]] = []
        self.stages: dict[str, dict[str, float]] = {}

    @contextlib.contextmanager
    def stage(self, name: str, *, guard: bool = True) -> Iterator[None]:
        wall, cpu = time.perf_counter(), time.process_time()
        try:
            yield
        except Exception as error:
            if not guard:
                raise
            self.errors.append(
                {
                    "stage": name,
                    "execution": isinstance(error, EXECUTION_ERRORS),
                    "type": type(error).__name__,
                    "message": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
        finally:
            self.stages[name] = {
                "wall_seconds": time.perf_counter() - wall,
                "cpu_seconds": time.process_time() - cpu,
            }


def input_hashes(args: argparse.Namespace) -> dict[str, str]:
    paths = [
        args.input_dir / "public_inputs.npz",
        args.input_dir / "exposure.npz",
        args.observations,
        args.arrival_bank,
        args.compressed_bank,
        Path(__file__),
        MODE_DIAGNOSIS,
    ]
    return {str(p.resolve()): adapter.sha256_file(p) for p in paths}


def fit_dataset(args: argparse.Namespace) -> dict[str, Any]:
    run = Run()
    receipt = run.receipt
    started = time.perf_counter()
    receipt.update(
        cutoffs=list(CUTOFF_GRID),
        host=platform.node(),
        platform=platform.platform(),
        python=sys.version,
        source=adapter._git_identity(ROOT),
        search_mode=args.search,
        tight_replay="always_on_inside_PanelSearch.run",
        threads={n: os.environ.get(n) for n in THREAD_ENVIRONMENT},
    )
    search: FitSearch | None = None
    families: dict[str, Any] = {}
    family_failures: list[str] = []
    audits: dict[str, Any] = {}
    receipt["families"] = families
    receipt["latent_audit"] = audits
    with run.stage("input_hashes"):
        receipt["input_sha256"] = input_hashes(args)
    data = None
    with run.stage("load"):
        data, receipt["data_identity"] = load_panel_data(args)
    if data is not None:
        search_dir = args.output_dir / "search"
        search_dir.mkdir()
        with run.stage("search_setup"):
            search = FitSearch(data, args.search, search_dir)
    if search is not None:
        with run.stage("search"):
            search.run()
            search_receipt = args.output_dir / "search_receipt.json"
            write_json(search_receipt, search.receipt())
            receipt["search"] = {
                "status": search.result["status"],
                "failure": search.result.get("failure"),
                "receipt": str(search_receipt.resolve()),
                "receipt_sha256": adapter.sha256_file(search_receipt),
                "cost": search.search_cost,
                "seconds_before_tight_phase": tight_phase_seconds(search.events),
                "family_switches": search.result.get("family_switches"),
                "numerical_checks": search.result.get("numerical_checks"),
                "family_switch_replay_passed": search.result.get("family_switch_replay_passed"),
            }
        with run.stage("spatial_report"):
            families["spatial"] = spatial_family_result(search)
        nodes = sorted(set(geometric_mesh()) | set(search.points[False]))
        seed_rows = {
            x: {**fit["sigma_zero"], "tight_converged": True}
            for x, fit in search.points[True].items()
        }
        free_seeds = [search.free[t]["sigma_zero"] for t in (False, True) if t in search.free]
        for name, beta_free in (("exposure", True), ("constant", False)):
            family = ReducedFamily(
                name,
                search.criterion,
                beta_free=beta_free,
                seed_rows=seed_rows if beta_free else None,
                free_seeds=free_seeds,
            )
            try:
                with run.stage(f"family_{name}", guard=False):
                    families[name] = family.result(family.run(nodes, CUTOFF_GRID))
            except Exception as error:
                family_failures.append(f"{name}: {error}")
                families[name] = {
                    "status": "failed",
                    "failure": {"type": type(error).__name__, "message": str(error)},
                    "profile_nodes": len(family.points),
                    "fit_count": family.fit_count,
                }
    multimodal = False
    if search is not None and search.free:
        with run.stage("latent_audit"):
            audits.update(
                audit_all(search, load_mode_diagnosis(), exhaustive=args.exhaustive_audit)
            )
            multimodal = audits["multimodal_latent"]
    if search is not None:
        receipt["cost"] = {
            "criterion_stats": dict(search.criterion.stats),
            "backend_diagnostics": dict(search.stats),
            "fixed_fit_events": search.fixed_fit_events,
            "reduced_family_fits": {
                k: v.get("fit_count") for k, v in families.items() if k != "spatial"
            },
        }
    classification = classify(
        search_status=receipt.get("search", {}).get("status"),
        search_failure=receipt.get("search", {}).get("failure"),
        family_failures=family_failures,
        multimodal=multimodal,
        errors=run.errors,
    )
    receipt.update(classification)
    receipt["errors"] = run.errors
    receipt.setdefault("cost", {}).update(
        stages=run.stages,
        total_wall_seconds=time.perf_counter() - started,
        total_cpu_seconds=time.process_time(),
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        * (1 if sys.platform == "darwin" else 1024),
    )
    write_json(args.output_dir / "receipt.json", receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input-dir", "observations", "arrival-bank", "compressed-bank", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--search", choices=("lean", "dense"), default="lean")
    parser.add_argument(
        "--exhaustive-audit",
        action="store_true",
        help="audit every location regardless of LR (qualification margin check)",
    )
    args = parser.parse_args()
    if any(os.environ.get(n) != "1" for n in THREAD_ENVIRONMENT):
        raise ValueError("set all numerical thread environment variables to 1")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    receipt = fit_dataset(args)
    print(json.dumps({"failure_class": receipt["failure_class"], "message": receipt["message"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
