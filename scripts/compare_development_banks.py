"""Cross-evaluate frozen development profiles under independent arrival banks."""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, cast

import benchmark_spatial_profile as adapter
import run_development_profile as profile
from qualify_spatial_profiles import FAMILIES, ROOT, topology, write_json

from latent_landscapes.spatial_profile import SpatialProfileData

THRESHOLDS = {"same_h_w": 0.10, "log_root": 0.05, "criterion_tie": 1e-4}


def compare_levels(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    numerical = all(
        level["status"] == "available"
        and all(
            math.isfinite(root["residual"])
            and abs(root["residual"]) <= level["residual_tolerance"]
            and root["verification_bracket_width_log_h"] <= 0.005
            for root in level["roots"]
        )
        for level in (left, right)
    )
    result: dict[str, Any] = {
        "cutoff": left["cutoff"],
        "passed": False,
        "numerically_resolved": numerical,
    }
    if not numerical:
        return {**result, "reason": "level-set numerical evidence is unresolved"}
    if (
        left["cutoff"] != right["cutoff"]
        or topology(left) is None
        or topology(left) != topology(right)
        or left["set_class"] != right["set_class"]
    ):
        return {**result, "reason": "components or domain contacts differ"}
    deltas = [
        b[key] - a[key]
        for a, b in zip(left["components"], right["components"], strict=True)
        for key in ("lower_log_h", "upper_log_h")
    ]
    return {
        **result,
        "component_endpoint_log_h_deltas": deltas,
        "same_components_and_domain_contacts": True,
        "passed": numerical and max(map(abs, deltas), default=0.0) <= THRESHOLDS["log_root"],
    }


def fit_agreement(left: dict[str, Any], right: dict[str, Any], *, free: bool) -> dict[str, Any]:
    a, b = profile.owners(left), profile.owners(right)
    common = set(a) & set(b)
    keys = (
        ("nuisance_bound_contacts", "h_domain_contacts") if free else ("nuisance_bound_contacts",)
    )
    return {
        "owners_B0": a,
        "owners_A": b,
        "ownership_agreement": bool(common),
        "boundary_contact_agreement": bool(common)
        and all(left[family][key] == right[family][key] for family in common for key in keys),
        "contacts_B0": {f: {key: left[f][key] for key in keys} for f in a},
        "contacts_A": {f: {key: right[f][key] for key in keys} for f in b},
    }


def cross_evaluate(search: profile.PanelSearch, locations: list[float]) -> dict[str, Any]:
    before = search.fixed_fit_events
    began = time.perf_counter()
    rows: list[dict[str, Any]] = []
    result: dict[str, Any] = {"status": "unavailable"}
    try:
        for x in locations:
            search.point(x, refresh=True)
            search.point(x, tight=True, refresh=True)
            diagnostic = search.post_search_points([x])
            rows.extend(diagnostic.get("points", []))
            if diagnostic["status"] != "available":
                result.update(failure=diagnostic.get("failure"), reason=diagnostic.get("reason"))
                break
        else:
            result["status"] = "available"
    except Exception as error:
        search.result["status"] = "indeterminate"
        result["failure"] = {"type": type(error).__name__, "message": str(error)}
    result.update(
        points=rows,
        retained_topology_checks=search.result.get("post_search_retained_topology_checks"),
        cost={
            "elapsed_seconds": time.perf_counter() - began,
            "fixed_fit_events": search.fixed_fit_events - before,
            "family_fit_batches": 2 * (search.fixed_fit_events - before),
            "requested_unique_h": len(locations),
            "completed_unique_h": len(rows),
        },
    )
    return result


def compare_banks(
    b0: profile.PanelSearch, independent: profile.PanelSearch, report_h: list[float]
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "development-bank-comparison-v1",
        "status": "indeterminate",
        "development_only": True,
        "calibration_claim": False,
        "thresholds": dict(THRESHOLDS),
        "original_search_cost": {
            "B0": copy.deepcopy(b0.search_cost),
            "A": copy.deepcopy(independent.search_cost),
        },
    }
    if b0.mode != independent.mode:
        return {**result, "reason": "banks used different search procedures"}
    if any(q.result["status"] != "profile_numerically_resolved" for q in (b0, independent)):
        return {**result, "reason": "one or both bank profiles are numerically unresolved"}
    locations = profile.comparison_locations([b0, independent], report_h)
    result["locations_log_h"] = locations
    evaluations = {"B0": cross_evaluate(b0, locations), "A": cross_evaluate(independent, locations)}
    result["cross_evaluations"] = evaluations
    if any(row["status"] != "available" for row in evaluations.values()):
        return {**result, "reason": "fresh own-bank evaluations invalidate a frozen search"}
    rows = []
    for a, b in zip(evaluations["B0"]["points"], evaluations["A"]["points"], strict=True):
        agreement = fit_agreement(a["tight_fit"], b["tight_fit"], free=False)
        relevant = min(a["tight_w"], b["tight_w"]) <= 3.84
        rows.append(
            {
                "log_h": a["log_h"],
                "h": a["h"],
                "w_B0": a["tight_w"],
                "w_A": b["tight_w"],
                "delta_w": b["tight_w"] - a["tight_w"],
                "inside_either_diagnostic_set": relevant,
                **agreement,
            }
        )
    left, right = b0.result["tight_level_sets"], independent.result["tight_level_sets"]
    if [x["cutoff"] for x in left] != [3.84] or [x["cutoff"] for x in right] != [3.84]:
        return {**result, "reason": "frozen diagnostic cutoff differs"}
    level_checks = [compare_levels(a, b) for a, b in zip(left, right, strict=True)]
    if not all(check["numerically_resolved"] for check in level_checks):
        return {
            **result,
            "reason": "frozen level-set numerics are unresolved",
            "level_set_checks": level_checks,
            "points": rows,
        }
    free = fit_agreement(b0.free[True], independent.free[True], free=True)
    contacts = {"B0": profile.inside_contacts(b0), "A": profile.inside_contacts(independent)}
    passed = (
        all(row["passed"] for row in level_checks)
        and contacts["B0"] == contacts["A"]
        and free["ownership_agreement"]
        and free["boundary_contact_agreement"]
        and all(
            math.isfinite(row["delta_w"])
            and abs(row["delta_w"]) <= THRESHOLDS["same_h_w"]
            and row["ownership_agreement"]
            and (not row["inside_either_diagnostic_set"] or row["boundary_contact_agreement"])
            for row in rows
        )
    )
    return {
        **result,
        "status": "within_prespecified_gates" if passed else "failed",
        "points": rows,
        "level_set_checks": level_checks,
        "free_fit_agreement": free,
        "inside_nuisance_contacts": contacts,
        "free_criterion_difference_descriptive_only": independent.free[True]["criterion"]
        - b0.free[True]["criterion"],
        "free_locations_descriptive_only": {
            role: {f: q.free[True][f]["h"] for f in FAMILIES}
            for role, q in (("B0", b0), ("A", independent))
        },
    }


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, Any], value)


def restore_fit(fit: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(fit)
    for family in FAMILIES:
        row = result[family]
        if not row["eligible"] or not math.isfinite(row["criterion"]):
            raise ValueError("receipt contains an unresolved selected fit")
    if result["criterion"] != max(result[f]["criterion"] for f in FAMILIES):
        raise ValueError("receipt envelope differs from its selected families")
    result["candidates"] = [copy.deepcopy(result[f]) for f in FAMILIES]
    return result


def restore_search(
    data: SpatialProfileData, receipt: dict[str, Any], directory: Path
) -> profile.PanelSearch:
    if receipt.get("schema") != "development-profile-search-v1":
        raise ValueError("unsupported search receipt schema")
    search = profile.PanelSearch(data, receipt["mode"], directory)
    search.result = copy.deepcopy(receipt)
    search.free = {key == "True": restore_fit(fit) for key, fit in receipt["free"].items()}
    search.points = {
        key == "True": {row["log_h"]: restore_fit(row) for row in rows}
        for key, rows in receipt["points"].items()
    }
    if set(search.free) != {False, True} or set(search.points) != {False, True}:
        raise ValueError("receipt lacks both numerical regimes")
    search.mesh = list(receipt["mesh_log_h"])
    search.tight_mesh = list(receipt["tight_mesh_log_h"])
    search.search_cost = copy.deepcopy(receipt["cost"]["search"])
    return search


def source_key(path: str) -> str:
    for marker in ("/src/latent_landscapes/", "/scripts/"):
        if marker in path:
            return marker[1:] + path.rsplit(marker, 1)[1]
    raise ValueError(f"unrecognized bound Python source path: {path}")


def verify_run(
    directory: Path, mode: str, actual_inputs: dict[str, Path]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    run = read_json(directory / "receipt.json")
    if run.get("schema") != "development-profile-run-v1":
        raise ValueError("unsupported parent run receipt schema")
    search_path = directory / mode / "receipt.json"
    if adapter.sha256_file(search_path) != run["searches"][mode]["sha256"]:
        raise ValueError("search receipt hash differs from parent run")
    search = read_json(search_path)
    if search.get("mode") != mode:
        raise ValueError("search mode differs from requested procedure")
    bindings = run["source_input_sha256"]
    sources = {source_key(p): h for p, h in bindings.items() if p.endswith(".py")}
    required = {
        "scripts/run_development_profile.py",
        "scripts/qualify_spatial_profiles.py",
        "scripts/profile_level_sets.py",
        "scripts/benchmark_spatial_profile.py",
    }
    if not required <= sources.keys() or not any(p.startswith("src/") for p in sources):
        raise ValueError("run lacks scientific source bindings")
    for relative, digest in sources.items():
        if adapter.sha256_file(ROOT / relative) != digest:
            raise ValueError(f"executing source differs from frozen search: {relative}")
    for role, path in actual_inputs.items():
        if adapter.sha256_file(path) not in bindings.values():
            raise ValueError(f"supplied {role} is not bound by original run")
    return run, search, sources


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "b0-run-dir",
        "a-run-dir",
        "input-dir",
        "observations",
        "b0-arrival-bank",
        "b0-compressed-bank",
        "a-arrival-bank",
        "a-compressed-bank",
        "output-dir",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--mode", choices=("dense", "lean"), required=True)
    parser.add_argument("--report-h", type=float, action="append", default=[])
    args = parser.parse_args()
    if any(not 1 <= h <= 30 for h in args.report_h):
        raise ValueError("report h outside [1,30]")
    threads = {
        name: os.environ.get(name)
        for name in ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OMP_NUM_THREADS")
    }
    if any(value != "1" for value in threads.values()):
        raise ValueError("set all numerical thread environment variables to 1")
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    identities: dict[str, str] = {}
    try:
        searches = []
        common_identity = None
        common_sources = None
        input_roles: dict[str, Any] = {}
        files = [
            Path(__file__),
            Path(profile.__file__),
            ROOT / "scripts/qualify_spatial_profiles.py",
            ROOT / "scripts/profile_level_sets.py",
            Path(adapter.__file__),
            *sorted((ROOT / "src/latent_landscapes").rglob("*.py")),
            args.observations,
            args.input_dir / "public_inputs.npz",
            args.input_dir / "exposure.npz",
        ]
        for prefix in ("b0", "a"):
            run_dir = getattr(args, f"{prefix}_run_dir")
            files.extend(
                [
                    run_dir / "receipt.json",
                    run_dir / args.mode / "receipt.json",
                    getattr(args, f"{prefix}_arrival_bank"),
                    getattr(args, f"{prefix}_compressed_bank"),
                ]
            )
        identities = {str(path.resolve()): adapter.sha256_file(path) for path in files}
        if (
            identities[str(args.b0_arrival_bank.resolve())]
            == identities[str(args.a_arrival_bank.resolve())]
        ):
            raise ValueError("B0 and A must not be the same raw bank")
        for role, prefix in (("B0", "b0"), ("A", "a")):
            inputs = {
                "observations": args.observations,
                "public_inputs": args.input_dir / "public_inputs.npz",
                "exposure": args.input_dir / "exposure.npz",
                "arrival_bank": getattr(args, f"{prefix}_arrival_bank"),
                "compressed_bank": getattr(args, f"{prefix}_compressed_bank"),
            }
            run_dir = getattr(args, f"{prefix}_run_dir")
            run, receipt, sources = verify_run(run_dir, args.mode, inputs)
            input_roles[role] = {
                name: {"path": str(path.resolve()), "sha256": identities[str(path.resolve())]}
                for name, path in {
                    **inputs,
                    "parent_run_receipt": run_dir / "receipt.json",
                    "search_receipt": run_dir / args.mode / "receipt.json",
                }.items()
            }
            if common_sources is not None and sources != common_sources:
                raise ValueError("bank searches used different scientific source")
            common_sources = sources
            namespace = argparse.Namespace(
                input_dir=args.input_dir,
                observations=args.observations,
                arrival_bank=inputs["arrival_bank"],
                compressed_bank=inputs["compressed_bank"],
            )
            data, identity = profile.load_panel_data(namespace)
            if identity != run["data_identity"] or (
                common_identity is not None and identity != common_identity
            ):
                raise ValueError("bank data identity differs from original or common history")
            common_identity = identity
            output = args.output_dir / role
            output.mkdir()
            searches.append(restore_search(data, receipt, output))
        started = {
            "source_input_sha256": identities,
            "input_roles": input_roles,
            "data_identity": common_identity,
            "mode": args.mode,
            "report_h": args.report_h,
            "runtime": {"python": sys.version, "platform": platform.platform(), "threads": threads},
            "restored_candidates": "own-bank eligible family winners",
            "original_search_receipts_unchanged": True,
        }
        write_json(args.output_dir / "started.json", started)
        result = compare_banks(searches[0], searches[1], args.report_h)
        for role, search in zip(("B0", "A"), searches, strict=True):
            result.setdefault("cross_check_runtime", {})[role] = {
                "backend_diagnostics": search.stats,
                "criterion_stats": search.criterion.stats,
                "events_sha256": adapter.sha256_file(search.events)
                if search.events.exists()
                else None,
                "events_path": str(search.events.resolve()),
            }
        for path, digest in identities.items():
            if adapter.sha256_file(Path(path)) != digest:
                raise RuntimeError(f"source/input drift during cross-check: {path}")
        write_json(args.output_dir / "receipt.json", {**result, **started})
        print(json.dumps({"status": result["status"]}))
    except Exception as error:
        write_json(
            args.output_dir / "receipt.json",
            {
                "schema": "development-bank-comparison-v1",
                "status": "indeterminate",
                "source_input_sha256": identities,
                "failure": {"type": type(error).__name__, "message": str(error)},
            },
        )
        raise


if __name__ == "__main__":
    main()
