"""Qualify diagnostic spatial-profile level sets on one fixed history and bank."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from itertools import pairwise
from pathlib import Path
from typing import Any

import benchmark_spatial_profile as adapter
import numpy as np
import scipy  # type: ignore[import-untyped]
from profile_level_sets import refine_level_set
from scipy.optimize import brentq  # type: ignore[import-untyped]

from latent_landscapes.capstone_qualification import subset_bank, subset_observations
from latent_landscapes.differentiable_likelihood import prepare_site_likelihood
from latent_landscapes.spatial_profile import (
    FitCandidate,
    SpatialProfileCriterion,
    SpatialProfileData,
)

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ("positive_sigma", "sigma_zero")
CUTOFFS = (1.0, 3.84, 6.63)
LOG_MAX = math.log(30.0)
PARAMETERS = {
    "positive_sigma": ("alpha", "beta", "log_sigma", "detection_sd"),
    "sigma_zero": ("alpha", "beta", "detection_sd"),
}
DEFAULTS = {
    "positive_sigma": np.array([-5.5, 0.4, math.log(0.35), 0.2]),
    "sigma_zero": np.array([-5.5, 0.4, 0.2]),
}


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(adapter._jsonable(data), indent=2, allow_nan=False) + "\n")


def parameters(row: dict[str, Any], *, free: bool = False) -> np.ndarray:
    names = list(PARAMETERS[row["family"]])
    if free:
        names.insert(-1, "log_h")
    return np.array([row["parameters"][name] for name in names], dtype=float)


def bound_contacts(row: dict[str, Any], *, free: bool = False) -> list[str]:
    names = list(PARAMETERS[row["family"]])
    if free:
        names.insert(-1, "log_h")
    bounds = SpatialProfileCriterion._bounds(
        None if free else row["h"], row["family"] == "sigma_zero"
    )
    result = []
    for name, (lower, upper) in zip(names, bounds, strict=True):
        value = row["parameters"][name]
        tolerance = 1e-8 * max(1.0, abs(lower), abs(upper))
        if abs(value - lower) <= tolerance:
            result.append(f"{name}:lower")
        if abs(value - upper) <= tolerance:
            result.append(f"{name}:upper")
    return result


def topology(level: dict[str, Any]) -> Any:
    if level["status"] != "available":
        return None
    return [
        (row["lower_domain_contact"], row["upper_domain_contact"], row["singleton"])
        for row in level["components"]
    ]


def select_candidate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected = {}
    for family in FAMILIES:
        eligible = [
            r
            for r in rows
            if r["family"] == family and r["eligible"] and math.isfinite(r["criterion"])
        ]
        if not eligible:
            raise RuntimeError(f"unresolved variance family: {family}")
        selected[family] = dict(max(eligible, key=lambda r: r["criterion"]))
    maxima = {f: selected[f]["criterion"] for f in FAMILIES}
    unresolved = [
        r
        for r in rows
        if not r["eligible"]
        and math.isfinite(r["criterion"])
        and r["criterion"] > maxima[r["family"]] + 1e-4
    ]
    if unresolved:
        raise RuntimeError("unresolved candidate exceeds selected family envelope")
    for row in rows:
        row["profile_lr_from_family_max"] = 2 * (maxima[row["family"]] - row["criterion"])
        row["profile_lr_from_global_max"] = 2 * (max(maxima.values()) - row["criterion"])
    for row in selected.values():
        row["profile_lr_from_family_max"] = 0.0
        row["profile_lr_from_global_max"] = 2 * (max(maxima.values()) - row["criterion"])
        contacts = bound_contacts(row, free="log_h" in row["parameters"])
        row["bound_contacts"] = contacts
        row["nuisance_bound_contacts"] = [c for c in contacts if not c.startswith("log_h:")]
        row["h_domain_contacts"] = (
            ["lower"] if row["h"] == 1.0 else ["upper"] if row["h"] == 30.0 else []
        )
    return {
        **selected,
        "criterion": max(maxima.values()),
        "candidates": rows,
        "unresolved_above_envelope": unresolved,
    }


def envelope_violations(free: dict[str, Any], fits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "family": row["family"],
            "h": row["h"],
            "source": row["source"],
            "eligible": row["eligible"],
            "excess": row["criterion"] - free[row["family"]]["criterion"],
        }
        for fit in fits
        for row in fit["candidates"]
        if math.isfinite(row["criterion"])
        and row["criterion"] > free[row["family"]]["criterion"] + 1e-4
    ]


def compare_level_sets(standard: dict[str, Any], tight: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "cutoff": standard["cutoff"],
        "passed": False,
        "log_root_deltas": None,
        "component_endpoint_deltas": None,
    }
    if topology(standard) != topology(tight) or topology(tight) is None:
        return result
    roots, tighter = standard["roots"], tight["roots"]

    def boundary_roots(level: dict[str, Any]) -> list[float]:
        return sorted(
            {
                component[f"{side}_log_h"]
                for component in level["components"]
                for side in ("lower", "upper")
                if not component[f"{side}_domain_contact"]
            }
        )

    standard_boundaries, tight_boundaries = boundary_roots(standard), boundary_roots(tight)
    if len(standard_boundaries) != len(tight_boundaries):
        return result
    root_deltas = [b - a for a, b in zip(standard_boundaries, tight_boundaries, strict=True)]
    endpoint_deltas = [
        [b[k] - a[k] for k in ("lower_log_h", "upper_log_h")]
        for a, b in zip(standard["components"], tight["components"], strict=True)
    ]
    residual_ok = all(
        abs(r["residual"]) <= 0.01 and r["verification_bracket_width_log_h"] <= 0.005
        for r in roots + tighter
    )
    result.update(
        log_root_deltas=root_deltas,
        component_endpoint_deltas=endpoint_deltas,
        passed=residual_ok
        and max(map(abs, root_deltas), default=0.0) <= 0.005
        and max((abs(v) for row in endpoint_deltas for v in row), default=0.0) <= 0.005,
    )
    return result


def hessian_diagnostic(hessian: np.ndarray, gradient: np.ndarray) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "unavailable",
        "relative_asymmetry_limit": 0.01,
        "condition_number_limit": 1e10,
    }
    if not np.isfinite(hessian).all() or not np.isfinite(gradient).all():
        return {**result, "reason": "nonfinite Hessian or gradient"}
    scale = max(float(np.max(np.abs(hessian))), np.finfo(float).tiny)
    asymmetry = float(np.max(np.abs(hessian - hessian.T))) / scale
    result["relative_asymmetry"] = asymmetry
    if asymmetry > 0.01:
        return {**result, "reason": "Hessian asymmetry exceeds limit"}
    symmetric = (hessian + hessian.T) / 2
    eigen = np.linalg.eigvalsh(symmetric)
    result["eigenvalues"] = eigen.tolist()
    if eigen[0] <= 0 or eigen[-1] / eigen[0] > 1e10:
        return {**result, "reason": "Hessian is nonpositive or ill-conditioned"}
    q = float(gradient @ np.linalg.solve(symmetric, gradient))
    if not math.isfinite(q):
        return {**result, "reason": "nonfinite quadratic diagnostic"}
    return {
        **result,
        "status": "available",
        "criterion_deficit": q / 2,
        "one_fit_lr_scale": q,
        "condition_number": float(eigen[-1] / eigen[0]),
    }


def _verify_files(identities: dict[str, str]) -> None:
    for name, digest in identities.items():
        if adapter.sha256_file(Path(name)) != digest:
            raise ValueError(f"bank provenance identity mismatch: {name}")


def validate_bank_identity(args: argparse.Namespace, reference: dict[str, Any]) -> dict[str, Any]:
    provenance: dict[str, str] = {}

    def verify(identities: dict[str, str]) -> None:
        _verify_files(identities)
        provenance.update(identities)

    role = args.bank_role
    k = int(reference["inputs"]["bank_size"])
    if k != 131072:
        raise ValueError("qualification reference must use K=131072")
    if bool(args.dense_baseline) != (role == "B0"):
        raise ValueError("dense baseline is required exactly for bank role B0")
    raw_sha = adapter.sha256_file(args.arrival_bank)
    compressed_sha = adapter.sha256_file(args.compressed_bank)
    bank = adapter.load_compressed_bank(args.compressed_bank)
    raw = np.load(args.arrival_bank, mmap_mode="r", allow_pickle=False)
    raw_checksum = hashlib.sha256(np.ascontiguousarray(raw).view(np.uint8)).hexdigest()
    if raw.shape != (bank.bank_size, len(bank.site_ids)) or bank.bank_checksum != raw_checksum:
        raise ValueError("raw/compressed shape or array identity mismatch")
    expected_size = 2 * k if role in ("AB", "Adup") else k
    if bank.bank_size != expected_size or bank.series_order != 192 or bank.max_x != 40.0:
        raise ValueError("bank size or compressed representation mismatch")
    result = {
        "role": role,
        "bank_size": bank.bank_size,
        "bank_checksum": raw_checksum,
        "site_ids": list(bank.site_ids),
        "raw_sha256": raw_sha,
        "compressed_sha256": compressed_sha,
        "independent_rows": role != "Adup",
    }
    if role == "B0":
        identities = reference["source_identity"]
        if (
            raw_sha != identities["raw_arrival_bank"]["sha256"]
            or compressed_sha != identities["arrival_bank"]["sha256"]
        ):
            raise ValueError("B0 must match archived reference raw and compressed bank identities")
        return {**result, "verified_provenance_sha256": provenance}
    if args.bank_manifest is None:
        raise ValueError("fresh and duplicated banks require --bank-manifest")
    manifest = json.loads(args.bank_manifest.read_text())
    if role == "Adup":
        product = manifest
        if product.get("bank_role") != "Adup" or product.get("duplication_factor") != 2:
            raise ValueError("invalid Adup duplication manifest")
        source = product["duplication_of_A"]
        verify(
            {
                source["raw_path"]: source["raw_sha256"],
                source["manifest_path"]: source["manifest_sha256"],
            }
        )
        a = np.load(source["raw_path"], mmap_mode="r", allow_pickle=False)
        source_manifest = json.loads(Path(source["manifest_path"]).read_text())
        source_product = source_manifest.get("products", {}).get("A", source_manifest)
        a_checksum = hashlib.sha256(np.ascontiguousarray(a).view(np.uint8)).hexdigest()
        if (
            source["bank_size"] != k
            or source["bank_checksum"] != a_checksum
            or source_product["bank_checksum"] != a_checksum
            or source_product["bank_size"] != k
            or source_product["site_ids"] != list(bank.site_ids)
            or source_product["raw_sha256"] != source["raw_sha256"]
            or (source_product["row_start"], source_product["row_stop_exclusive"]) != (k, 2 * k)
        ):
            raise ValueError("Adup source does not match its A manifest")
        if (
            a.shape != (k, len(bank.site_ids))
            or not np.array_equal(raw[:k], a)
            or not np.array_equal(raw[k:], a)
        ):
            raise ValueError("Adup is not two exact copies of A")
        addresses = product
        expected_range = (k, 2 * k)
    else:
        if (
            manifest.get("schema") != "profile-sensitivity-derived-banks-v1"
            or manifest.get("state") != "complete"
        ):
            raise ValueError("fresh bank requires completed top-level derivation manifest")
        verify(manifest["input_sha256"])
        verify(manifest["source_sha256"])
        product = manifest["products"][role]
        generations = []
        for name in manifest["input_sha256"]:
            if Path(name).name == "manifest.json":
                candidate = json.loads(Path(name).read_text())
                if candidate.get("schema") == "profile-sensitivity-bank-v1":
                    generations.append((Path(name).parent, candidate))
        if len(generations) != 1:
            raise ValueError("derivation must bind one generating bank manifest")
        directory, generation = generations[0]
        verify(generation["source_sha256"])
        verify(generation["input_sha256"])
        if (
            generation.get("state") != "complete"
            or generation["row_start"] != k
            or generation["row_stop_exclusive"] != 3 * k
            or generation["bank_size"] != 2 * k
        ):
            raise ValueError("fresh generation row range or completeness mismatch")
        verify({str(directory / "seed_ledger.npz"): generation["ledger_sha256"]})
        with np.load(directory / "seed_ledger.npz", allow_pickle=False) as ledger:
            root = int(generation["root"])
            rows = np.arange(k, 3 * k, dtype=np.uint64)
            if (
                int(ledger["root"]) != root
                or int(ledger["namespace"]) != 59
                or int(ledger["stage"]) != 3
                or not np.array_equal(ledger["row_addresses"], rows)
            ):
                raise ValueError("fresh seed ledger namespace or addresses mismatch")
            expected = np.asarray(
                [
                    np.random.SeedSequence([root, 59, 3, int(r)]).generate_state(
                        1, dtype=np.uint64
                    )[0]
                    for r in rows
                ]
            )
            if not np.array_equal(ledger["seeds"], expected):
                raise ValueError("fresh seed ledger violates the seed rule")
        addresses = {**product, "root": root, "namespace": 59, "stage": 3}
        expected_range = {"A": (k, 2 * k), "B": (2 * k, 3 * k), "AB": (k, 3 * k)}[role]
    if (
        product["bank_size"] != expected_size
        or product["bank_checksum"] != raw_checksum
        or product["site_ids"] != list(bank.site_ids)
        or product["raw_sha256"] != raw_sha
        or product["compressed_sha256"] != compressed_sha
    ):
        raise ValueError("requested bank does not match its product manifest")
    if (
        (addresses["row_start"], addresses["row_stop_exclusive"]) != expected_range
        or addresses["namespace"] != 59
        or addresses["stage"] != 3
    ):
        raise ValueError("bank row range or namespace mismatch")
    public_meta = json.loads((args.input_dir / "public_inputs.json").read_text())
    if addresses["root"] != public_meta["root"]:
        raise ValueError("bank root differs from frozen public root")
    return {
        **result,
        "manifest_sha256": adapter.sha256_file(args.bank_manifest),
        "verified_provenance_sha256": provenance,
        "root": addresses["root"],
        "namespace": 59,
        "stage": 3,
        "row_start": expected_range[0],
        "row_stop_exclusive": expected_range[1],
    }


def load_data(args: argparse.Namespace) -> SpatialProfileData:
    public, exposure = adapter.load_public_arrays(args.input_dir)
    ids = adapter._as_site_ids(public["site_ids"], name="public sites")
    observed, _ = adapter.load_observations(args.observations, public=public, history=0)
    bank, _, _ = adapter.load_bank(
        raw_path=args.arrival_bank,
        compressed_path=args.compressed_bank,
        public_ids=ids,
        selected_ids=observed.site_ids,
    )
    a, rows, cols = adapter._exposure_for_sites(public, exposure, observed.site_ids)
    mask = np.asarray(observed.training_mask, dtype=bool)
    if int(mask.sum()) != 120 or len(mask) != 160:
        raise ValueError("this bounded qualification requires 120 training and 40 holdout sites")
    bank = subset_bank(bank, mask)
    observed = subset_observations(observed, mask)
    covariance = adapter.build_covariance(
        rows[mask], cols[mask], site_ids=observed.site_ids, range_cells=10.0, covariance_path=None
    )
    return SpatialProfileData(bank, observed, a[mask], covariance)


class Qualification:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.reference = json.loads(args.reference.read_text())
        reference_observations = self.reference["source_identity"]["observations"]["sha256"]
        if adapter.sha256_file(args.observations) != reference_observations:
            raise ValueError("reference and requested observation identities differ")
        for name, path in (
            ("public_inputs", args.input_dir / "public_inputs.npz"),
            ("exposure", args.input_dir / "exposure.npz"),
        ):
            if adapter.sha256_file(path) != self.reference["source_identity"][name]["sha256"]:
                raise ValueError("reference and requested public/exposure identities differ")
        self.bank_identity = validate_bank_identity(args, self.reference)
        self.data = load_data(args)
        self.data_identity = {
            "observations_sha256": adapter.sha256_file(args.observations),
            "public_npz_sha256": adapter.sha256_file(args.input_dir / "public_inputs.npz"),
            "exposure_sha256": adapter.sha256_file(args.input_dir / "exposure.npz"),
            "training_site_ids_sha256": hashlib.sha256(
                "\n".join(self.data.observed.site_ids).encode()
            ).hexdigest(),
            "training_site_count": len(self.data.observed.site_ids),
            "covariance_range": 10.0,
            "prey_times": list(self.data.observed.prey_times),
            "predator_times": list(self.data.observed.predator_times),
            "cohort_start": self.data.observed.cohort_start,
        }
        self.stats = adapter._direct_diagnostics()

        def factory(h: float, detection_sd: float) -> Any:
            self.stats["evaluator_instances"] += 1
            return adapter._CountingDirectEvaluator(
                prepare_site_likelihood(
                    self.data.observed, self.data.bank, h, detection_sd=detection_sd
                ),
                self.stats,
            )

        self.criterion = SpatialProfileCriterion(self.data, evaluator_factory=factory)
        self.points: dict[bool, dict[float, dict[str, Any]]] = {False: {}, True: {}}
        self.free: dict[bool, dict[str, Any]] = {}
        self.directional: dict[float, dict[str, Any]] = {}
        self.midpoint_triggers: list[dict[str, Any]] = []
        self.closure_history: list[dict[str, Any]] = []
        self.reference_points: dict[float, dict[str, Any]] = {}
        canonical_mesh = [float(x) for x in np.linspace(0.0, LOG_MAX, 35)]
        for row in self.reference["profile"]["grid_statuses"]:
            if row["family"] not in FAMILIES:
                continue
            if row["status"] != "resolved":
                raise ValueError("reference mesh contains unresolved points")
            log_h = math.log(row["h"])
            key = min(canonical_mesh, key=lambda x: abs(x - log_h))
            if abs(key - log_h) > 1e-12:
                raise ValueError("reference mesh differs from the fixed 35-node qualification mesh")
            self.reference_points.setdefault(key, {})[row["family"]] = row
        if len(self.reference_points) != 35 or any(
            set(v) != set(FAMILIES) for v in self.reference_points.values()
        ):
            raise ValueError("reference requires both families at all 35 mesh nodes")
        self.started = time.perf_counter()
        self.events = args.output_dir / "evaluations.jsonl"

    def record(self, event: dict[str, Any]) -> None:
        event["elapsed_seconds"] = time.perf_counter() - self.started
        with self.events.open("a") as handle:
            handle.write(json.dumps(adapter._jsonable(event), allow_nan=False) + "\n")

    def summarise(
        self, candidates: list[FitCandidate], previous: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        rows = [
            adapter._candidate_summary(row, family_max=0.0, global_max=0.0) for row in candidates
        ]
        if previous is not None:
            rows = previous["candidates"] + rows
        try:
            return select_candidate_rows(rows)
        except RuntimeError:
            self.record({"kind": "unresolved_fit", "candidates": rows})
            raise

    def neighbours(self, log_h: float, family: str, tight: bool) -> list[np.ndarray]:
        available = {**self.reference_points, **self.points[False], **self.points[tight]}
        left = [x for x in available if x < log_h]
        right = [x for x in available if x > log_h]
        choices = [log_h] if log_h in available else []
        choices += ([max(left)] if left else []) + ([min(right)] if right else [])
        starts = [parameters(available[x][family]) for x in choices]
        starts.append(DEFAULTS[family])
        unique: list[np.ndarray] = []
        for row in starts:
            if not any(np.array_equal(row, old) for old in unique):
                unique.append(row)
        return unique

    def point(
        self,
        log_h: float,
        *,
        tight: bool = False,
        refresh: bool = False,
        direction: str | None = None,
    ) -> dict[str, Any]:
        x = float(log_h)
        if x in self.points[tight] and not refresh:
            return self.points[tight][x]
        if x not in self.points[tight] and len(self.points[tight]) >= 160:
            raise RuntimeError("prespecified unique-point limit exhausted")
        h = min(30.0, math.exp(x))
        if not 0.0 <= x <= LOG_MAX:
            raise ValueError("log h outside qualification domain")
        candidates = []
        for family in FAMILIES:
            candidates.extend(
                self.criterion._fit_family(
                    fixed_h=h,
                    sigma_zero=family == "sigma_zero",
                    starts=self.neighbours(x, family, tight),
                    kkt_tolerance=1e-4 if tight else 1e-3,
                    maxiter=120 if tight else 80,
                    source_prefix=f"{'tight' if tight else 'standard'}_fixed_{x.hex()}",
                )
            )
        previous = self.points[tight].get(x)
        if direction is not None:
            rows = [
                adapter._candidate_summary(row, family_max=0.0, global_max=0.0)
                for row in candidates
            ]
            selected = {
                f: max(
                    (r for r in rows if r["family"] == f and r["eligible"]),
                    key=lambda r: r["criterion"],
                    default=None,
                )
                for f in FAMILIES
            }
            self.directional.setdefault(x, {})[direction] = {
                "selected": selected,
                "candidates": rows,
            }
        fit = self.summarise(candidates, previous)
        fit.update(log_h=x, h=h, tight=tight)
        self.points[tight][x] = fit
        self.record({"kind": "fixed_fit", "fit": fit})
        return fit

    def fit_free(self, *, tight: bool = False) -> None:
        candidates = []
        available = dict(self.points[False])
        for x, fit in self.points[True].items():
            available[x] = (
                select_candidate_rows(available[x]["candidates"] + fit["candidates"])
                if x in available
                else fit
            )
        for family in FAMILIES:
            ref_key = "best_positive" if family == "positive_sigma" else "best_sigma_zero"
            starts = [
                parameters(self.reference["profile"][ref_key], free=True),
                np.insert(DEFAULTS[family], -1, math.log(3.0)),
            ]
            for regime in (False, True):
                if regime in self.free:
                    starts.append(parameters(self.free[regime][family], free=True))
            points = sorted(available)
            incumbent = self.free.get(tight, {}).get(family, {}).get("criterion", math.inf)
            for i, x in enumerate(points):
                fit = available[x]
                row = fit[family]
                left = available[points[i - 1]][family]["criterion"] if i else -math.inf
                right = (
                    available[points[i + 1]][family]["criterion"]
                    if i + 1 < len(points)
                    else -math.inf
                )
                if row["criterion"] >= max(left, right) or row["criterion"] > incumbent - 1e-6:
                    starts.append(np.insert(parameters(row), -1, x))
                for failed in fit["candidates"]:
                    if (
                        failed["family"] == family
                        and math.isfinite(failed["criterion"])
                        and failed["criterion"] > incumbent
                    ):
                        starts.append(np.insert(parameters(failed), -1, x))
            unique: list[np.ndarray] = []
            for start in starts:
                if not any(np.array_equal(start, old) for old in unique):
                    unique.append(start)
            candidates.extend(
                self.criterion._fit_family(
                    fixed_h=None,
                    sigma_zero=family == "sigma_zero",
                    starts=unique,
                    kkt_tolerance=1e-4 if tight else 1e-3,
                    maxiter=120 if tight else 80,
                    source_prefix="tight_free" if tight else "standard_free",
                )
            )
        self.free[tight] = self.summarise(candidates, self.free.get(tight))
        self.record({"kind": "free_fit", "tight": tight, "fit": self.free[tight]})

    def lr(self, log_h: float, *, tight: bool = False) -> float:
        point = self.point(log_h, tight=tight)
        return float(2 * (self.free[tight]["criterion"] - point["criterion"]))

    def direction_difference(self, x: float) -> dict[str, float | None]:
        branches = self.directional.get(x, {})
        return {
            f: (
                branches["down"]["selected"][f]["criterion"]
                - branches["up"]["selected"][f]["criterion"]
                if all(
                    d in branches and branches[d]["selected"][f] is not None for d in ("up", "down")
                )
                else None
            )
            for f in FAMILIES
        }

    def midpoint_mesh(self, mesh: list[float]) -> list[float]:
        pending = []
        reference_max = max(
            self.reference["profile"][k]["criterion"] for k in ("best_positive", "best_sigma_zero")
        )
        w = {x: self.lr(x) for x in mesh}
        for i, (a, b) in enumerate(pairwise(mesh)):
            pa, pb = self.points[False][a], self.points[False][b]
            da = pa[FAMILIES[0]]["criterion"] - pa[FAMILIES[1]]["criterion"]
            db = pb[FAMILIES[0]]["criterion"] - pb[FAMILIES[1]]["criterion"]
            reasons = []
            if self.args.dense_baseline:
                reasons.append("dense_B0_69_node_check")
            if da * db < 0 or min(abs(da), abs(db)) <= 1e-4:
                reasons.append("family_switch_or_tie")
            if any(
                pa[f]["nuisance_bound_contacts"] != pb[f]["nuisance_bound_contacts"]
                for f in FAMILIES
            ):
                reasons.append("nuisance_bound_transition")
            if any(
                (w[a] - c) * (w[b] - c) <= 0 or min(abs(w[a] - c), abs(w[b] - c)) <= 0.25
                for c in CUTOFFS
            ):
                reasons.append("cutoff_crossing_or_proximity")
            if (i > 0 and w[a] <= w[mesh[i - 1]] and w[a] <= w[b]) or (
                i + 2 < len(mesh) and w[b] <= w[a] and w[b] <= w[mesh[i + 2]]
            ):
                reasons.append("local_peak")
            if any(
                v is None or abs(v) > 1e-4
                for x in (a, b)
                for v in self.direction_difference(x).values()
            ):
                reasons.append("direction_disagreement")
            for x in (a, b):
                if x in self.reference_points:
                    ref_w = 2 * (
                        reference_max
                        - max(self.reference_points[x][f]["criterion"] for f in FAMILIES)
                    )
                    if any((ref_w <= c) != (w[x] <= c) for c in CUTOFFS):
                        reasons.append("topology_sign_changed_vs_B0")
                        break
            if reasons:
                pending.append((a, b, sorted(set(reasons))))
        additions = []
        for depth in range(3):
            next_pending = []
            for a, b, reasons in pending:
                x = (a + b) / 2
                self.midpoint_triggers.append(
                    {
                        "bracket_log_h": [a, b],
                        "midpoint_log_h": x,
                        "depth": depth,
                        "reasons": reasons,
                    }
                )
                mid = self.point(x)
                additions.append(x)
                pa, pb = self.points[False][a], self.points[False][b]
                new_features = []
                if any(
                    mid[f]["criterion"] > max(pa[f]["criterion"], pb[f]["criterion"]) + 1e-4
                    for f in FAMILIES
                ):
                    new_features.append("new_interior_peak")
                for f in FAMILIES:
                    contacts = mid[f]["nuisance_bound_contacts"]
                    if (
                        contacts != pa[f]["nuisance_bound_contacts"]
                        and contacts != pb[f]["nuisance_bound_contacts"]
                    ):
                        new_features.append("new_interior_bound_contact")
                contrasts = [
                    p[FAMILIES[0]]["criterion"] - p[FAMILIES[1]]["criterion"] for p in (pa, mid, pb)
                ]
                if (
                    contrasts[0] * contrasts[2] > 0
                    and abs(contrasts[1]) > 1e-4
                    and contrasts[0] * contrasts[1] < 0
                ):
                    new_features.append("new_pair_of_family_switches")
                wx = self.lr(x)
                if any(
                    (w_a - c) * (w_b - c) > 0 and (w_a - c) * (wx - c) < 0
                    for c in CUTOFFS
                    for w_a, w_b in [(self.lr(a), self.lr(b))]
                ):
                    new_features.append("new_pair_of_cutoff_crossings")
                if b - a > LOG_MAX / 34 + 1e-12:
                    new_features.append("spacing_not_yet_69_grid")
                if new_features:
                    next_pending.extend([(a, x, new_features), (x, b, new_features)])
            if not next_pending:
                return sorted(set(mesh + additions))
            pending = next_pending
        self.record({"kind": "midpoint_refinement_cap", "pending": pending})
        raise RuntimeError("new profile features remain at the bounded midpoint-refinement cap")

    def switches(self, mesh: list[float], *, tight: bool = False) -> dict[str, Any]:
        switches, ties = [], []

        def contrast(x: float) -> float:
            row = self.point(x, tight=tight)
            return float(row[FAMILIES[0]]["criterion"] - row[FAMILIES[1]]["criterion"])

        for a, b in pairwise(mesh):
            da, db = contrast(a), contrast(b)
            if min(abs(da), abs(db)) <= 1e-4:
                ties.append(
                    {
                        "bracket_log_h": [a, b],
                        "endpoint_contrasts": [da, db],
                        "criterion_tie_tolerance": 1e-4,
                    }
                )
            elif da * db < 0:
                x = float(brentq(contrast, a, b, xtol=1e-5 if tight else 1e-4))
                residual = contrast(x)
                if abs(residual) > 1e-4:
                    raise RuntimeError("isolated family-switch residual exceeds tolerance")
                switches.append(
                    {
                        "log_h": x,
                        "h": min(30.0, math.exp(x)),
                        "contrast": residual,
                        "bracket_log_h": [a, b],
                    }
                )
        return {"isolated": switches, "tie_intervals": ties}

    def close_profiles(
        self, mesh: list[float], *, tight: bool = False
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        for iteration in range(3):
            before = {f: self.free[tight][f]["criterion"] for f in FAMILIES}
            levels = [
                refine_level_set(
                    lambda x: self.lr(x, tight=tight), mesh, c, xtol=1e-5 if tight else 1e-4
                )
                for c in CUTOFFS
            ]
            switches = self.switches(mesh, tight=tight)
            self.fit_free(tight=tight)
            relevant = list(self.points[False].values()) + list(self.points[True].values())
            violations = envelope_violations(self.free[tight], [*relevant, self.free[tight]])
            shifts = {f: self.free[tight][f]["criterion"] - before[f] for f in FAMILIES}
            self.closure_history.append(
                {
                    "tight": tight,
                    "iteration": iteration,
                    "family_maximum_shifts": shifts,
                    "violations": violations,
                }
            )
            moved = max(map(abs, shifts.values())) > 1e-6
            if moved or violations:
                continue
            valid = all(level["status"] == "available" for level in levels)
            for level in levels:
                for root in level["roots"]:
                    root["residual"] = self.lr(root["log_h"], tight=tight) - level["cutoff"]
                    endpoint = [
                        self.lr(x, tight=tight) - level["cutoff"]
                        for x in root["verification_bracket_log_h"]
                    ]
                    root["verification_endpoint_residuals"] = endpoint
                    valid &= abs(root["residual"]) <= 0.01 and (
                        endpoint[0] <= 0 <= endpoint[1] or endpoint[1] <= 0 <= endpoint[0]
                    )
            if valid:
                return levels, switches
        raise RuntimeError(
            "free maximum or level-set verification did not stabilize within three passes"
        )

    def outer_diagnostic(self, row: dict[str, Any], *, step: float) -> dict[str, Any]:
        point = parameters(row, free=True)
        zero = row["family"] == "sigma_zero"
        evaluate = self.criterion.evaluate_sigma_zero if zero else self.criterion.evaluate_positive
        bounds = self.criterion._bounds(None, zero)
        names = list(PARAMETERS[row["family"]])
        names.insert(-1, "log_h")
        active = [
            i
            for i, (v, (lo, hi)) in enumerate(zip(point, bounds, strict=True))
            if min(v - lo, hi - v) <= 1e-7 * max(1.0, abs(lo), abs(hi))
        ]
        indices = [i for i in range(len(point)) if i not in active]
        result: dict[str, Any] = {
            "step": step,
            "active_coordinates": [names[i] for i in active],
            "coordinate_names": [names[i] for i in indices],
            "status": "unavailable",
            "local_approximation_only": True,
        }
        try:
            base = evaluate(point, nuisance_fd=True)
            if not base.success or not indices:
                return {**result, "reason": "base evaluation unresolved or no free coordinates"}
            g = np.asarray(base.objective_gradient[indices])
            result["gradient"] = g.tolist() if np.isfinite(g).all() else None
            columns = []
            for i in indices:
                delta = step * max(1.0, abs(point[i]))
                minus, plus = point.copy(), point.copy()
                minus[i] -= delta
                plus[i] += delta
                if minus[i] <= bounds[i][0] or plus[i] >= bounds[i][1]:
                    return {**result, "reason": "central-difference stencil crosses a bound"}
                em, ep = evaluate(minus, nuisance_fd=True), evaluate(plus, nuisance_fd=True)
                if not em.success or not ep.success:
                    return {**result, "reason": "perturbed evaluation unresolved"}
                columns.append(
                    (ep.objective_gradient[indices] - em.objective_gradient[indices]) / (2 * delta)
                )
            return {**result, **hessian_diagnostic(np.column_stack(columns), g)}
        except Exception as error:
            return {**result, "reason": str(error)}

    def contact_summary(self, levels: list[dict[str, Any]]) -> dict[str, Any]:
        def contacts(fit: dict[str, Any]) -> dict[str, Any]:
            owners = [f for f in FAMILIES if fit["criterion"] - fit[f]["criterion"] <= 1e-4]
            return {
                "envelope_families": owners,
                "nuisance_contacts": {f: fit[f]["nuisance_bound_contacts"] for f in owners},
                "h_domain_contacts": {f: fit[f]["h_domain_contacts"] for f in owners},
            }

        root_contacts = []
        inside = []
        for level in levels:
            for root in level["roots"]:
                item = {
                    "cutoff": level["cutoff"],
                    "log_h": root["log_h"],
                    **contacts(self.point(root["log_h"])),
                }
                root["envelope_contacts"] = item
                root_contacts.append(item)
            inside.append(
                {
                    "cutoff": level["cutoff"],
                    "sampled_contacts": [
                        {"log_h": x, **contacts(fit)}
                        for x, fit in sorted(self.points[False].items())
                        if self.lr(x) <= level["cutoff"]
                        and any(contacts(fit)["nuisance_contacts"].values())
                    ],
                }
            )
        return {
            "interpretation": "coordinate contact, not causal bound determination",
            "free": contacts(self.free[False]),
            "roots": root_contacts,
            "inside_diagnostic_sets": inside,
        }

    def archived_replay(self) -> dict[str, Any]:
        if self.args.bank_role != "B0":
            return {"applicable": False}
        rows = []
        old_global = max(
            self.reference["profile"][k]["criterion"] for k in ("best_positive", "best_sigma_zero")
        )
        new_global = self.free[False]["criterion"]
        for x, families in self.reference_points.items():
            current = self.point(x)
            old_w = 2 * (old_global - max(row["criterion"] for row in families.values()))
            new_w = 2 * (new_global - current["criterion"])
            for family, row in families.items():
                evaluate = (
                    self.criterion.evaluate_sigma_zero
                    if family == "sigma_zero"
                    else self.criterion.evaluate_positive
                )
                replay = evaluate(parameters(row), fixed_h=row["h"])
                rows.append(
                    {
                        "family": family,
                        "h": row["h"],
                        "free": False,
                        "exact_parameter_delta": replay.criterion - row["criterion"],
                        "refit_improvement": current[family]["criterion"] - row["criterion"],
                        "delta_w": new_w - old_w,
                        "evaluation_success": replay.success,
                    }
                )
        for family in FAMILIES:
            key = "best_positive" if family == "positive_sigma" else "best_sigma_zero"
            row = self.reference["profile"][key]
            evaluate = (
                self.criterion.evaluate_sigma_zero
                if family == "sigma_zero"
                else self.criterion.evaluate_positive
            )
            replay = evaluate(parameters(row, free=True))
            improvement = self.free[False][family]["criterion"] - row["criterion"]
            rows.append(
                {
                    "family": family,
                    "h": row["h"],
                    "free": True,
                    "exact_parameter_delta": replay.criterion - row["criterion"],
                    "refit_improvement": improvement,
                    "delta_w": 2
                    * (new_global - self.point(math.log(row["h"]))[family]["criterion"])
                    - 2 * (old_global - row["criterion"]),
                    "w_comparator": "same_h_family_specific",
                    "current_combined_w": self.lr(math.log(row["h"])),
                    "archived_combined_w_available": False,
                    "evaluation_success": replay.success,
                }
            )
        return {
            "applicable": True,
            "comparisons": rows,
            "exact_parameter_tolerance": 1e-8,
            "passed": all(
                r["evaluation_success"]
                and abs(r["exact_parameter_delta"]) <= 1e-8
                and r["refit_improvement"] >= -1e-8
                and abs(r["delta_w"]) <= 0.01
                for r in rows
            ),
        }

    def run(self) -> dict[str, Any]:
        mesh = [float(x) for x in np.linspace(0, LOG_MAX, 35)]
        result: dict[str, Any] = {
            "schema": "spatial-profile-qualification-v1",
            "development_only": True,
            "profile_certified": False,
            "calibration_claim": False,
            "status": "indeterminate",
            "bank_qualification": "external_cross_bank_gate_pending",
            "cutoffs": CUTOFFS,
        }
        try:
            for name, direction in (("up", mesh), ("down", list(reversed(mesh)))):
                for x in direction:
                    self.point(x, refresh=x in self.points[False], direction=name)
            self.point(math.log(3.0))
            for key in ("best_positive", "best_sigma_zero"):
                self.point(math.log(self.reference["profile"][key]["h"]))
            self.fit_free()
            mesh = self.midpoint_mesh(mesh)
            self.fit_free()
            levels, switches = self.close_profiles(mesh)
            tight_nodes = set(mesh)
            for level in levels:
                for root in level["roots"]:
                    tight_nodes.update(
                        [root["log_h"], *root["bracket_log_h"], *root["verification_bracket_log_h"]]
                    )
            for switch in switches["isolated"]:
                tight_nodes.update([switch["log_h"], *switch["bracket_log_h"]])
            for tie in switches["tie_intervals"]:
                tight_nodes.update(tie["bracket_log_h"])
            tight_nodes.update(
                [math.log(3.0), *(math.log(self.free[False][f]["h"]) for f in FAMILIES)]
            )
            tight_mesh = sorted(tight_nodes)
            for x in tight_mesh:
                self.point(x, tight=True)
            self.fit_free(tight=True)
            for replay_pass in range(3):
                levels, switches = self.close_profiles(mesh)
                tight_levels, tight_switches = self.close_profiles(tight_mesh, tight=True)
                checks = []
                for standard, tighter in zip(levels, tight_levels, strict=True):
                    check = compare_level_sets(standard, tighter)
                    locations = sorted({r["log_h"] for r in standard["roots"] + tighter["roots"]})
                    same = [
                        {"log_h": x, "delta_w": self.lr(x, tight=True) - self.lr(x)}
                        for x in locations
                    ]
                    check.update(same_point_lr=same)
                    check["passed"] &= max((abs(r["delta_w"]) for r in same), default=0.0) <= 0.01
                    checks.append(check)
                switch_deltas = (
                    [
                        b["log_h"] - a["log_h"]
                        for a, b in zip(
                            switches["isolated"], tight_switches["isolated"], strict=True
                        )
                    ]
                    if len(switches["isolated"]) == len(tight_switches["isolated"])
                    else None
                )
                switch_check = {
                    "log_h_deltas": switch_deltas,
                    "ties_exempt": True,
                    "passed": switch_deltas is not None
                    and max(map(abs, switch_deltas), default=0.0) <= 0.005,
                }
                before_replay_refit = {
                    t: {f: self.free[t][f]["criterion"] for f in FAMILIES} for t in (False, True)
                }
                self.fit_free()
                self.fit_free(tight=True)
                shifts = {
                    str(t): {
                        f: self.free[t][f]["criterion"] - before_replay_refit[t][f]
                        for f in FAMILIES
                    }
                    for t in (False, True)
                }
                free_checks = []
                for regime in (False, True):
                    for family in FAMILIES:
                        x = math.log(self.free[regime][family]["h"])
                        standard, tighter = self.point(x), self.point(x, tight=True)
                        free_checks.append(
                            {
                                "family": family,
                                "free_source_tight": regime,
                                "log_h": x,
                                "delta_w": self.lr(x, tight=True) - self.lr(x),
                                "delta_criterion": tighter[family]["criterion"]
                                - standard[family]["criterion"],
                            }
                        )
                final_violations = {
                    str(t): envelope_violations(
                        self.free[t],
                        list(self.points[False].values())
                        + list(self.points[True].values())
                        + [self.free[t]],
                    )
                    for t in (False, True)
                }
                self.closure_history.append(
                    {
                        "same_h_replay_pass": replay_pass,
                        "family_maximum_shifts": shifts,
                        "violations": final_violations,
                    }
                )
                if max(
                    abs(v) for family_shifts in shifts.values() for v in family_shifts.values()
                ) <= 1e-6 and not any(final_violations.values()):
                    break
            else:
                raise RuntimeError(
                    "same-h replay changed the free envelope beyond the three-pass cap"
                )
            for tight_flag, level_collection in ((False, levels), (True, tight_levels)):
                for level in level_collection:
                    for root in level["roots"]:
                        root["residual"] = (
                            self.lr(root["log_h"], tight=tight_flag) - level["cutoff"]
                        )
                        endpoint = [
                            self.lr(x, tight=tight_flag) - level["cutoff"]
                            for x in root["verification_bracket_log_h"]
                        ]
                        root["verification_endpoint_residuals"] = endpoint
                        if not (endpoint[0] <= 0 <= endpoint[1] or endpoint[1] <= 0 <= endpoint[0]):
                            raise RuntimeError(
                                "final free refit invalidated a verified root bracket"
                            )
            for check, standard, tighter in zip(checks, levels, tight_levels, strict=True):
                for row in check["same_point_lr"]:
                    row["delta_w"] = self.lr(row["log_h"], tight=True) - self.lr(row["log_h"])
                check["passed"] = (
                    compare_level_sets(standard, tighter)["passed"]
                    and max((abs(r["delta_w"]) for r in check["same_point_lr"]), default=0.0)
                    <= 0.01
                )
            for row in free_checks:
                row["delta_w"] = self.lr(row["log_h"], tight=True) - self.lr(row["log_h"])
            before_report_counts = {t: len(self.points[t]) for t in (False, True)}
            replay = self.archived_replay()
            result.update(
                free=self.free[False],
                tight_free=self.free[True],
                mesh_log_h=mesh,
                tight_mesh_log_h=tight_mesh,
                level_sets=levels,
                tight_level_sets=tight_levels,
                numerical_checks=checks,
                free_same_point_checks=free_checks,
                family_switches=switches["isolated"],
                family_tie_intervals=switches["tie_intervals"],
                tight_family_switches=tight_switches["isolated"],
                tight_family_tie_intervals=tight_switches["tie_intervals"],
                family_switch_check=switch_check,
                final_envelope_violations=final_violations,
                archived_B0_replay=replay,
                contacts=self.contact_summary(levels),
                anchors=[
                    {"h": min(30.0, math.exp(x)), "log_h": x, "w": self.lr(x)}
                    for x in np.linspace(0, LOG_MAX, 35)
                ],
                diagnostic_w={
                    str(h): {
                        "standard": self.lr(math.log(h)),
                        "tight": self.lr(math.log(h), tight=True),
                    }
                    for h in (1, 3)
                },
            )
            if before_report_counts != {t: len(self.points[t]) for t in (False, True)}:
                raise RuntimeError("report extraction introduced an unclosed fixed point")
            all_pass = (
                all(r["passed"] for r in checks)
                and switch_check["passed"]
                and max((abs(r["delta_w"]) for r in free_checks), default=0.0) <= 0.01
                and not any(final_violations.values())
                and replay.get("passed", True)
            )
            result["status"] = "profile_numerically_resolved" if all_pass else "indeterminate"
            outer = {
                f: [self.outer_diagnostic(self.free[False][f], step=s) for s in (1e-4, 3e-5)]
                for f in FAMILIES
            }
            result["outer_diagnostics"] = outer
            result["outer_diagnostic_step_comparison"] = {
                f: {
                    "available_both": all(r["status"] == "available" for r in values),
                    "delta_q": values[1]["one_fit_lr_scale"] - values[0]["one_fit_lr_scale"]
                    if all(r["status"] == "available" for r in values)
                    else None,
                }
                for f, values in outer.items()
            }
        except RuntimeError as error:
            result["failure"] = {"type": type(error).__name__, "message": str(error)}
        result.update(
            bank_identity=self.bank_identity,
            data_identity=self.data_identity,
            directional_fits=[
                {"log_h": x, "branches": v, "criterion_differences": self.direction_difference(x)}
                for x, v in sorted(self.directional.items())
            ],
            midpoint_triggers=self.midpoint_triggers,
            closure_history=self.closure_history,
            points=[self.points[False][x] for x in sorted(self.points[False])],
            tight_points=[self.points[True][x] for x in sorted(self.points[True])],
            backend_diagnostics=self.stats,
            criterion_stats=self.criterion.stats,
            elapsed_seconds=time.perf_counter() - self.started,
        )
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "input-dir",
        "observations",
        "arrival-bank",
        "compressed-bank",
        "reference",
        "output-dir",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--dense-baseline", action="store_true")
    parser.add_argument("--bank-role", choices=("B0", "A", "B", "AB", "Adup"), required=True)
    parser.add_argument("--bank-manifest", type=Path)
    args = parser.parse_args()
    thread_env = {
        name: os.environ.get(name)
        for name in ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_NUM_THREADS")
    }
    if any(value != "1" for value in thread_env.values()):
        raise ValueError("qualification requires all BLAS/OpenMP thread environment values equal 1")
    runtime = {
        "python": sys.version,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "platform": platform.platform(),
        "thread_environment": thread_env,
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True),
    }
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    files = [
        Path(__file__),
        Path(adapter.__file__),
        ROOT / "scripts/profile_level_sets.py",
        *sorted((ROOT / "src/latent_landscapes").rglob("*.py")),
        args.observations,
        args.arrival_bank,
        args.compressed_bank,
        args.reference,
        args.input_dir / "public_inputs.json",
        args.input_dir / "public_inputs.npz",
        args.input_dir / "exposure.npz",
    ]
    if args.bank_manifest is not None:
        files.append(args.bank_manifest)
    identities = {str(p.resolve()): adapter.sha256_file(p) for p in files}
    write_json(
        args.output_dir / "started.json",
        {
            "source_input_sha256": identities,
            "runtime": runtime,
            "arguments": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
            "truth_accessed": False,
            "training_sites": 120,
            "holdout_sites_excluded": 40,
        },
    )
    try:
        qualification = Qualification(args)
        result = qualification.run()
        _verify_files(qualification.bank_identity["verified_provenance_sha256"])
        for name, expected in identities.items():
            if adapter.sha256_file(Path(name)) != expected:
                raise RuntimeError(f"source/input drift during qualification: {name}")
        result["source_input_sha256"] = identities
        result["runtime"] = runtime
        write_json(args.output_dir / "receipt.json", result)
        print(
            json.dumps({"status": result["status"], "elapsed_seconds": result["elapsed_seconds"]})
        )
    except Exception as error:
        write_json(
            args.output_dir / "failure.json", {"type": type(error).__name__, "error": str(error)}
        )
        raise


if __name__ == "__main__":
    main()
