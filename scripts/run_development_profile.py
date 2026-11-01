"""Compare independent dense and lean spatial searches on development data."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import resource
import sys
import time
from itertools import pairwise
from pathlib import Path
from typing import Any

import benchmark_spatial_profile as adapter
import numpy as np
from qualify_spatial_profiles import (
    DEFAULTS,
    FAMILIES,
    LOG_MAX,
    ROOT,
    Qualification,
    compare_level_sets,
    envelope_violations,
    write_json,
)
from scipy.optimize import minimize_scalar  # type: ignore[import-untyped]

from latent_landscapes.capstone_qualification import subset_bank, subset_observations
from latent_landscapes.differentiable_likelihood import prepare_site_likelihood
from latent_landscapes.spatial_profile import SpatialProfileCriterion, SpatialProfileData


def compact_fit(fit: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in fit.items() if key != "candidates"}


def owners(fit: dict[str, Any]) -> list[str]:
    return [f for f in FAMILIES if fit["criterion"] - fit[f]["criterion"] <= 1e-4]


def fit_contacts(fit: dict[str, Any]) -> dict[str, Any]:
    return {f: fit[f]["nuisance_bound_contacts"] for f in owners(fit)}


def frozen_membership_check(level: dict[str, Any], x: float, w: float) -> dict[str, Any]:
    inside = any(
        component["lower_log_h"] <= x <= component["upper_log_h"]
        for component in level["components"]
    )
    residual = w - level["cutoff"]
    tolerance = level["residual_tolerance"]
    near_root = any(
        root["verification_bracket_log_h"][0] <= x <= root["verification_bracket_log_h"][1]
        for root in level["roots"]
    )
    return {
        "cutoff": level["cutoff"],
        "inside_frozen_components": inside,
        "residual": residual,
        "residual_tolerance": tolerance,
        "inside_verified_root_bracket": near_root,
        "passed": math.isfinite(residual)
        and ((near_root and abs(residual) <= tolerance) or inside == (residual <= 0.0)),
    }


def frozen_ownership_checks(
    points: dict[float, dict[str, Any]], switches: dict[str, Any]
) -> list[dict[str, Any]]:
    anchors = [root["log_h"] for root in switches["isolated"]]
    anchors.extend(
        x
        for tie in switches["tie_intervals"]
        for x, contrast in zip(tie["bracket_log_h"], tie["endpoint_contrasts"], strict=True)
        if abs(contrast) <= tie["criterion_tie_tolerance"]
    )
    anchor_checks = [
        {"frozen_tie_log_h": x, "passed": x in points and len(owners(points[x])) == 2}
        for x in sorted(set(anchors))
    ]
    non_tied = [(x, owners(fit)[0]) for x, fit in sorted(points.items()) if len(owners(fit)) == 1]
    return anchor_checks + [
        {
            "bracket_log_h": [a, b],
            "owners": [left, right],
            "passed": any(a <= root <= b for root in anchors),
        }
        for (a, left), (b, right) in pairwise(non_tied)
        if left != right
    ]


def maximum_summary(free: dict[str, Any], points: list[dict[str, Any]]) -> dict[str, Any]:
    maximum = free["criterion"]
    selected = max((free[f] for f in FAMILIES), key=lambda row: row["criterion"])
    flat = bool(points) and all(abs(p["criterion"] - maximum) <= 1e-8 for p in points)
    locations = sorted(
        {
            math.log(row["h"])
            for row in free["candidates"]
            if row["eligible"] and abs(row["criterion"] - maximum) <= 1e-8
        }
    )
    separated = len(locations) > 1 and locations[-1] - locations[0] > 0.005
    state = (
        "flat_on_evaluated_domain"
        if flat
        else "multiple_numerically_tied_maxima"
        if separated
        else "selected_maximum"
    )
    return {
        "status": state,
        "effect_estimate": None if flat or separated else selected["h"],
        "selected_computational_h": selected["h"],
        "near_maximum_log_h": locations,
        "criterion_tie_tolerance": 1e-8,
        "global_uniqueness_proven": False,
    }


class PanelSearch(Qualification):
    cutoffs = (3.84,)

    def __init__(self, data: SpatialProfileData, mode: str, output_dir: Path):
        if mode not in {"dense", "lean"}:
            raise ValueError("mode must be dense or lean")
        self.mode = mode
        self.args = argparse.Namespace(dense_baseline=mode == "dense")
        self.data = data
        self.refine_numerical_ties = mode == "dense"
        self.midpoint_spacing = LOG_MAX / 34 if mode == "dense" else LOG_MAX
        self.reference_points = {}
        self.stats = adapter._direct_diagnostics()

        def factory(h: float, detection_sd: float) -> Any:
            self.stats["evaluator_instances"] += 1
            return adapter._CountingDirectEvaluator(
                prepare_site_likelihood(data.observed, data.bank, h, detection_sd=detection_sd),
                self.stats,
            )

        self.criterion = SpatialProfileCriterion(data, evaluator_factory=factory)
        self.points = {False: {}, True: {}}
        self.free = {}
        self.directional = {}
        self.midpoint_triggers = []
        self.closure_history = []
        self.started = time.perf_counter()
        self.events = output_dir / "evaluations.jsonl"
        self.mesh: list[float] = []
        self.tight_mesh: list[float] = []
        self.result: dict[str, Any] = {}
        self.search_cost: dict[str, Any] = {}
        self.post_search_seconds = 0.0
        self.fixed_fit_events = 0

    def record(self, event: dict[str, Any]) -> None:
        if event["kind"] == "fixed_fit":
            self.fixed_fit_events += 1
        super().record(event)

    def initial_free_starts(self, family: str) -> list[np.ndarray]:
        return [np.insert(DEFAULTS[family], -1, x) for x in (0.0, LOG_MAX / 2, LOG_MAX)]

    def closure_mesh(self, mesh: list[float], *, tight: bool) -> list[float]:
        nodes = set(mesh) | set(self.points[tight])
        nodes.update(math.log(self.free[tight][f]["h"]) for f in FAMILIES)
        closed = sorted(nodes)
        if tight:
            self.tight_mesh = closed
        else:
            self.mesh = closed
        return closed

    def refine_lean_peaks(self, mesh: list[float]) -> None:
        brackets = set()
        for family in FAMILIES:
            for i, x in enumerate(mesh[1:-1], 1):
                value = self.points[False][x][family]["criterion"]
                if (
                    value
                    > max(self.points[False][mesh[j]][family]["criterion"] for j in (i - 1, i + 1))
                    + 1e-4
                ):
                    brackets.add((mesh[i - 1], mesh[i + 1]))
        for left, right in sorted(brackets):
            optimized = minimize_scalar(
                lambda x: -self.point(float(x))["criterion"],
                bounds=(left, right),
                method="bounded",
                options={"xatol": 1e-4, "maxiter": 80},
            )
            self.record(
                {
                    "kind": "lean_peak_refinement",
                    "bracket_log_h": [left, right],
                    "success": bool(optimized.success),
                    "log_h": float(optimized.x),
                }
            )
            if not optimized.success:
                raise RuntimeError("bounded lean peak refinement failed")

    def retained_topology_checks(self) -> dict[str, Any]:
        failures = []
        ownership = {}
        for tight, level_key, switch_key in (
            (False, "level_sets", "family_switches"),
            (True, "tight_level_sets", "tight_family_switches"),
        ):
            for x in sorted(self.points[tight]):
                for level in self.result[level_key]:
                    check = frozen_membership_check(level, x, self.lr(x, tight=tight))
                    if not check["passed"]:
                        failures.append({"tight": tight, "log_h": x, **check})
            ownership[str(tight)] = frozen_ownership_checks(
                self.points[tight], self.result[switch_key]
            )
        return {
            "passed": not failures
            and all(c["passed"] for checks in ownership.values() for c in checks),
            "membership_failures": failures,
            "ownership_transitions": ownership,
        }

    def run(self) -> dict[str, Any]:
        self.result = {
            "schema": "development-profile-search-v1",
            "mode": self.mode,
            "status": "indeterminate",
            "development_only": True,
            "calibration_claim": False,
            "globality_proven": False,
            "cutoffs": self.cutoffs,
            "truth_used_in_search": False,
        }
        try:
            mesh = np.linspace(0.0, LOG_MAX, 35 if self.mode == "dense" else 5).tolist()
            for label, sequence in (("up", mesh), ("down", list(reversed(mesh)))):
                for x in sequence:
                    self.point(x, refresh=x in self.points[False], direction=label)
            self.fit_free()
            if self.mode == "dense":
                for left, right in pairwise(mesh):
                    self.point((left + right) / 2)
                self.fit_free()
            if self.mode == "lean":
                self.refine_lean_peaks(mesh)
                self.fit_free()
            mesh = sorted(set(mesh) | {math.log(self.free[False][f]["h"]) for f in FAMILIES})
            for x in mesh:
                self.point(x)
            mesh = self.midpoint_mesh(mesh)
            self.fit_free()
            levels, switches = self.close_profiles(mesh)
            tight_mesh = sorted(set(self.mesh) | set(self.points[False]))
            for x in tight_mesh:
                self.point(x, tight=True)
            self.fit_free(tight=True)
            for replay_pass in range(3):
                levels, switches = self.close_profiles(self.mesh)
                tight_levels, tight_switches = self.close_profiles(tight_mesh, tight=True)
                locations = set(self.points[False]) | set(self.points[True])
                locations.update(
                    math.log(self.free[t][f]["h"]) for t in (False, True) for f in FAMILIES
                )
                for x in sorted(locations):
                    self.point(x)
                    self.point(x, tight=True)
                before = {
                    t: {f: self.free[t][f]["criterion"] for f in FAMILIES} for t in (False, True)
                }
                self.fit_free()
                self.fit_free(tight=True)
                shifts = [
                    abs(self.free[t][f]["criterion"] - before[t][f])
                    for t in (False, True)
                    for f in FAMILIES
                ]
                violations = {
                    str(t): envelope_violations(
                        self.free[t],
                        [*self.points[False].values(), *self.points[True].values(), self.free[t]],
                    )
                    for t in (False, True)
                }
                self.closure_history.append(
                    {
                        "same_h_replay_pass": replay_pass,
                        "maximum_free_shift": max(shifts),
                        "violations": violations,
                    }
                )
                if max(shifts) <= 1e-6 and not any(violations.values()):
                    break
            else:
                raise RuntimeError("same-h replay failed free-envelope closure")
            checks = []
            for standard, tight in zip(levels, tight_levels, strict=True):
                for regime, level in ((False, standard), (True, tight)):
                    for root in level["roots"]:
                        root["residual"] = self.lr(root["log_h"], tight=regime) - level["cutoff"]
                        residuals = [
                            self.lr(x, tight=regime) - level["cutoff"]
                            for x in root["verification_bracket_log_h"]
                        ]
                        root["verification_endpoint_residuals"] = residuals
                        if not (min(residuals) <= 0 <= max(residuals)):
                            raise RuntimeError("final free refit invalidated a root bracket")
                checks.append(compare_level_sets(standard, tight))
            shared = sorted(set(self.points[False]) & set(self.points[True]))
            deltas = [{"log_h": x, "delta_w": self.lr(x, tight=True) - self.lr(x)} for x in shared]
            switches_pass = len(switches["isolated"]) == len(tight_switches["isolated"]) and all(
                abs(a["log_h"] - b["log_h"]) <= 0.005
                for a, b in zip(switches["isolated"], tight_switches["isolated"], strict=False)
            )
            passed = (
                all(c["passed"] for c in checks)
                and switches_pass
                and max((abs(d["delta_w"]) for d in deltas), default=0) <= 0.01
            )
            self.result.update(
                status="profile_numerically_resolved" if passed else "indeterminate",
                level_sets=levels,
                tight_level_sets=tight_levels,
                numerical_checks=checks,
                same_point_replay=deltas,
                family_switches=switches,
                tight_family_switches=tight_switches,
                family_switch_replay_passed=switches_pass,
            )
            consistency = self.retained_topology_checks()
            self.result["final_retained_topology_checks"] = consistency
            if not consistency["passed"]:
                raise RuntimeError("final retained points contradict frozen profile topology")
        except Exception as error:
            self.result["status"] = "indeterminate"
            self.result["failure"] = {"type": type(error).__name__, "message": str(error)}
        self.search_cost = {
            "elapsed_seconds": time.perf_counter() - self.started,
            "standard_unique_h": len(self.points[False]),
            "tight_unique_h": len(self.points[True]),
            "fixed_fit_events": self.fixed_fit_events,
        }
        return self.receipt()

    def post_search_points(self, locations: list[float]) -> dict[str, Any]:
        if self.result["status"] != "profile_numerically_resolved":
            return {"status": "unavailable", "reason": "search indeterminate"}
        rows = []
        started = time.perf_counter()
        try:
            for x in sorted(set(locations)):
                fit = self.point(x)
                tighter = self.point(x, tight=True)
                for t in (False, True):
                    if envelope_violations(self.free[t], [fit, tighter]):
                        raise RuntimeError(
                            "post-search diagnostic exposed a superior free-envelope candidate"
                        )
                delta = self.lr(x, tight=True) - self.lr(x)
                if abs(delta) > 0.01:
                    raise RuntimeError("post-search same-h replay exceeds 0.01")
                topology_checks = {
                    key: [
                        frozen_membership_check(level, x, self.lr(x, tight=tight))
                        for level in self.result[key]
                    ]
                    for key, tight in (("level_sets", False), ("tight_level_sets", True))
                }
                rows.append(
                    {
                        "log_h": x,
                        "h": min(30.0, math.exp(x)),
                        "w": self.lr(x),
                        "tight_w": self.lr(x, tight=True),
                        "fit": compact_fit(fit),
                        "tight_fit": compact_fit(tighter),
                        "frozen_membership_checks": topology_checks,
                    }
                )
                if not all(c["passed"] for checks in topology_checks.values() for c in checks):
                    raise RuntimeError(
                        "post-search evaluation contradicts frozen level-set membership"
                    )
            consistency = self.retained_topology_checks()
            self.result["post_search_retained_topology_checks"] = consistency
            if not consistency["passed"]:
                raise RuntimeError(
                    "post-search points contradict frozen family ownership or topology"
                )
            return {"status": "available", "points": rows}
        except Exception as error:
            self.result["status"] = "indeterminate"
            self.result["post_search_failure"] = {
                "type": type(error).__name__,
                "message": str(error),
            }
            return {
                "status": "unavailable",
                "points": rows,
                "failure": self.result["post_search_failure"],
            }
        finally:
            self.post_search_seconds += time.perf_counter() - started

    def receipt(self) -> dict[str, Any]:
        result = dict(self.result)
        result.update(
            free={str(t): compact_fit(fit) for t, fit in self.free.items()},
            points={
                str(t): [compact_fit(fit) for _, fit in sorted(points.items())]
                for t, points in self.points.items()
            },
            maximum={
                str(t): maximum_summary(fit, list(self.points[t].values()))
                for t, fit in self.free.items()
            },
            mesh_log_h=self.mesh,
            tight_mesh_log_h=self.tight_mesh,
            midpoint_triggers=self.midpoint_triggers,
            closure_history=self.closure_history,
            backend_diagnostics=self.stats,
            criterion_stats=self.criterion.stats,
            cost={
                "search": self.search_cost,
                "post_search_seconds": self.post_search_seconds,
                "total_standard_unique_h": len(self.points[False]),
                "total_tight_unique_h": len(self.points[True]),
                "total_fixed_fit_events": self.fixed_fit_events,
                "process_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                * (1 if sys.platform == "darwin" else 1024),
                "peak_rss_scope": "process_lifetime_includes_prior_search_if_paired",
            },
        )
        if self.events.exists():
            result["evaluation_stream"] = {
                "path": str(self.events.resolve()),
                "sha256": adapter.sha256_file(self.events),
            }
        return result


def comparison_locations(searches: list[PanelSearch], report_h: list[float]) -> list[float]:
    locations = {0.0, *(math.log(h) for h in report_h)}
    for search in searches:
        for fit in search.free.values():
            locations.update(math.log(fit[f]["h"]) for f in FAMILIES)
        for key in ("level_sets", "tight_level_sets"):
            for level in search.result.get(key, []):
                locations.update(root["log_h"] for root in level["roots"])
        for key in ("family_switches", "tight_family_switches"):
            switches = search.result.get(key, {})
            for root in switches.get("isolated", []):
                locations.add(root["log_h"])
                locations.update(root["bracket_log_h"])
            for interval in switches.get("tie_intervals", []):
                locations.update(interval["bracket_log_h"])
        for key in ("final_retained_topology_checks", "post_search_retained_topology_checks"):
            checks = search.result.get(key, {})
            for transitions in checks.get("ownership_transitions", {}).values():
                for transition in transitions:
                    locations.update(transition.get("bracket_log_h", []))
    return sorted(locations)


def inside_contacts(search: PanelSearch) -> list[tuple[str, str]]:
    return sorted(
        {
            (family, contact)
            for x, fit in search.points[True].items()
            if search.lr(x, tight=True) <= 3.84
            for family in owners(fit)
            for contact in fit[family]["nuisance_bound_contacts"]
        }
    )


def compare_searches(
    dense: PanelSearch, lean: PanelSearch, report_h: list[float]
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "development-search-comparison-v1",
        "status": "indeterminate",
        "thresholds": {"same_h_w": 0.01, "log_root": 0.005, "criterion_tie": 1e-4},
    }
    if any(s.result["status"] != "profile_numerically_resolved" for s in (dense, lean)):
        return {**result, "reason": "one or both independent searches are unresolved"}
    locations = comparison_locations([dense, lean], report_h)
    dense_points, lean_points = (
        dense.post_search_points(locations),
        lean.post_search_points(locations),
    )
    dense.result["post_search_diagnostics"] = dense_points
    lean.result["post_search_diagnostics"] = lean_points
    result["locations_log_h"] = locations
    if dense_points["status"] != "available" or lean_points["status"] != "available":
        return {
            **result,
            "reason": "post-search evaluation invalidated qualification",
            "dense": dense_points,
            "lean": lean_points,
        }
    level_checks = [
        compare_level_sets(a, b)
        for a, b in zip(
            dense.result["tight_level_sets"], lean.result["tight_level_sets"], strict=True
        )
    ]
    comparisons = []
    for a, b in zip(dense_points["points"], lean_points["points"], strict=True):
        oa, ob = owners(a["tight_fit"]), owners(b["tight_fit"])
        owner_agreement = bool(set(oa) & set(ob))
        contact_agreement = all(
            a["tight_fit"][f]["nuisance_bound_contacts"]
            == b["tight_fit"][f]["nuisance_bound_contacts"]
            for f in set(oa) & set(ob)
        )
        comparisons.append(
            {
                "log_h": a["log_h"],
                "h": a["h"],
                "delta_w": b["tight_w"] - a["tight_w"],
                "owners_dense": oa,
                "owners_lean": ob,
                "ownership_agreement": owner_agreement,
                "nuisance_contact_agreement": contact_agreement,
            }
        )
    maximum_difference = 2 * (lean.free[True]["criterion"] - dense.free[True]["criterion"])
    dense_contacts, lean_contacts = inside_contacts(dense), inside_contacts(lean)
    classes_match = [x["set_class"] for x in dense.result["tight_level_sets"]] == [
        x["set_class"] for x in lean.result["tight_level_sets"]
    ]
    passed = (
        classes_match
        and dense_contacts == lean_contacts
        and all(c["passed"] for c in level_checks)
        and abs(maximum_difference) <= 0.01
        and all(
            abs(row["delta_w"]) <= 0.01
            and row["ownership_agreement"]
            and row["nuisance_contact_agreement"]
            for row in comparisons
        )
    )
    result.update(
        status="within_prespecified_gates" if passed else "failed",
        level_set_checks=level_checks,
        points=comparisons,
        twice_free_criterion_difference=maximum_difference,
        set_classes_agree=classes_match,
        inside_nuisance_contacts={"dense": dense_contacts, "lean": lean_contacts},
    )
    return result


def load_panel_data(args: argparse.Namespace) -> tuple[SpatialProfileData, dict[str, Any]]:
    public, exposure = adapter.load_public_arrays(args.input_dir)
    public_ids = adapter._as_site_ids(public["site_ids"], name="public sites")
    observed, _ = adapter.load_observations(args.observations, public=public, history=0)
    bank, _, _ = adapter.load_bank(
        raw_path=args.arrival_bank,
        compressed_path=args.compressed_bank,
        public_ids=public_ids,
        selected_ids=observed.site_ids,
    )
    a, rows, cols = adapter._exposure_for_sites(public, exposure, observed.site_ids)
    training = np.asarray(observed.training_mask, dtype=bool)
    if not training.any():
        raise ValueError("no training sites")
    observed, bank = subset_observations(observed, training), subset_bank(bank, training)
    covariance = adapter.build_covariance(
        rows[training],
        cols[training],
        site_ids=observed.site_ids,
        range_cells=10.0,
        covariance_path=None,
    )
    identity = {
        "site_count": len(observed.site_ids),
        "site_ids_sha256": hashlib.sha256("\n".join(observed.site_ids).encode()).hexdigest(),
        "prey_times": list(observed.prey_times),
        "cohort_start": observed.cohort_start,
        "covariance_range": 10.0,
        "bank_size": int(bank.bank_size),
    }
    return SpatialProfileData(bank, observed, a[training], covariance), identity


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input-dir", "observations", "arrival-bank", "compressed-bank", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--mode", choices=("dense", "lean", "paired"), required=True)
    parser.add_argument("--report-h", type=float, action="append", default=[])
    args = parser.parse_args()
    if any(not 1 <= h <= 30 for h in args.report_h):
        raise ValueError("report h outside [1,30]")
    thread_names = ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_NUM_THREADS")
    if any(os.environ.get(n) != "1" for n in thread_names):
        raise ValueError("set all numerical thread environment variables to 1")
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    files = [
        Path(__file__),
        ROOT / "scripts/qualify_spatial_profiles.py",
        ROOT / "scripts/profile_level_sets.py",
        Path(adapter.__file__),
        *sorted((ROOT / "src/latent_landscapes").rglob("*.py")),
        args.observations,
        args.arrival_bank,
        args.compressed_bank,
        args.input_dir / "public_inputs.npz",
        args.input_dir / "exposure.npz",
    ]
    identities = {str(p.resolve()): adapter.sha256_file(p) for p in files}
    runtime = {
        "python": sys.version,
        "platform": platform.platform(),
        "threads": {n: os.environ[n] for n in thread_names},
    }
    write_json(
        args.output_dir / "started.json",
        {
            "source_input_sha256": identities,
            "runtime": runtime,
            "mode": args.mode,
            "report_h_used_only_after_search": args.report_h,
        },
    )
    searches = []
    try:
        data, data_identity = load_panel_data(args)
        modes = ("dense", "lean") if args.mode == "paired" else (args.mode,)
        for mode in modes:
            directory = args.output_dir / mode
            directory.mkdir()
            search = PanelSearch(data, mode, directory)
            searches.append(search)
            search.run()
            write_json(directory / "receipt.json", search.receipt())
        comparison = (
            compare_searches(searches[0], searches[1], args.report_h)
            if len(searches) == 2
            else None
        )
        if len(searches) == 1:
            searches[0].result["post_search_diagnostics"] = searches[0].post_search_points(
                comparison_locations(searches, args.report_h)
            )
        for search in searches:
            write_json(args.output_dir / search.mode / "receipt.json", search.receipt())
        for name, expected in identities.items():
            if adapter.sha256_file(Path(name)) != expected:
                raise RuntimeError(f"source/input drift: {name}")
        status = comparison["status"] if comparison is not None else searches[0].result["status"]
        write_json(
            args.output_dir / "receipt.json",
            {
                "schema": "development-profile-run-v1",
                "status": status,
                "source_input_sha256": identities,
                "data_identity": data_identity,
                "runtime": runtime,
                "comparison": comparison,
                "searches": {
                    s.mode: {
                        "path": str((args.output_dir / s.mode / "receipt.json").resolve()),
                        "sha256": adapter.sha256_file(args.output_dir / s.mode / "receipt.json"),
                    }
                    for s in searches
                },
            },
        )
        print(json.dumps({"status": status}))
    except Exception as error:
        write_json(
            args.output_dir / "failure.json", {"type": type(error).__name__, "message": str(error)}
        )
        raise


if __name__ == "__main__":
    main()
