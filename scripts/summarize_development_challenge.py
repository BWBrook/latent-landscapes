"""Summarize the complete development challenge without making scientific claims."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from itertools import pairwise
from pathlib import Path
from typing import Any, cast

FAMILIES = ("positive_sigma", "sigma_zero")
OWNER_TOLERANCE = 1e-4
FROZEN_MANIFEST_SHA256 = "f5a80802dc502305f186f7f0a599d20e674d26d7b3e1c917403969b01f2cecfa"


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def owners(fit: Mapping[str, Any]) -> list[str]:
    criterion = float(fit["criterion"])
    return [
        family
        for family in FAMILIES
        if criterion - float(fit[family]["criterion"]) <= OWNER_TOLERANCE
    ]


def uniform_piecewise_linear_slope(nodes: Sequence[tuple[float, float]]) -> float:
    ordered = sorted((float(x), float(y)) for x, y in nodes)
    if len(ordered) < 2 or any(not math.isfinite(v) for row in ordered for v in row):
        raise ValueError("at least two finite ridge nodes are required")
    if any(right[0] <= left[0] for left, right in pairwise(ordered)):
        raise ValueError("ridge nodes must have unique increasing log-h coordinates")
    lower, upper = ordered[0][0], ordered[-1][0]
    midpoint = (lower + upper) / 2.0
    numerator = 0.0
    for (x0, y0), (x1, y1) in pairwise(ordered):
        width = x1 - x0
        segment_slope = (y1 - y0) / width
        integral_y = width * (y0 + y1) / 2.0
        integral_xy = (
            x0 * y0 * width
            + (x0 * segment_slope + y0) * width**2 / 2.0
            + segment_slope * width**3 / 3.0
        )
        numerator += integral_xy - midpoint * integral_y
    denominator = (upper - lower) ** 3 / 12.0
    if denominator <= 0.0:
        raise ValueError("ridge interval must have positive width")
    return numerator / denominator


def _receipt_state(path_value: str | Path | None) -> dict[str, Any]:
    if path_value is None:
        return {"state": "not_requested", "status": None, "path": None, "sha256": None}
    supplied = Path(path_value)
    receipt = supplied / "receipt.json"
    failure = supplied / "failure.json"
    if receipt.exists():
        try:
            value = read_json(receipt)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            return {
                "state": "malformed",
                "status": "indeterminate",
                "path": str(receipt.resolve()),
                "sha256": sha256(receipt),
                "failure": {"type": type(error).__name__, "message": str(error)},
            }
        if not isinstance(value, dict):
            return {
                "state": "malformed",
                "status": "indeterminate",
                "path": str(receipt.resolve()),
                "sha256": sha256(receipt),
                "failure": {"type": "ValueError", "message": "receipt is not a JSON object"},
            }
        return {
            "state": "receipt",
            "status": value.get("status"),
            "schema": value.get("schema"),
            "path": str(receipt.resolve()),
            "sha256": sha256(receipt),
            "failure": value.get("failure"),
            "reason": value.get("reason"),
            "post_search_failure": value.get("post_search_failure"),
            "value": value,
        }
    if failure.exists():
        try:
            value = read_json(failure)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            return {
                "state": "malformed",
                "status": "indeterminate",
                "path": str(failure.resolve()),
                "sha256": sha256(failure),
                "failure": {"type": type(error).__name__, "message": str(error)},
            }
        return {
            "state": "failure",
            "status": (
                value.get("status", "indeterminate")
                if isinstance(value, dict)
                else "indeterminate"
            ),
            "path": str(failure.resolve()),
            "sha256": sha256(failure),
            "failure": value,
        }
    return {
        "state": "missing",
        "status": "indeterminate",
        "path": str(receipt.resolve()),
        "sha256": None,
        "failure": {"type": "FileNotFoundError", "message": "receipt and failure files are absent"},
    }


def _optional_receipt_summary(
    state: dict[str, Any],
    *,
    expected_schema: str,
    required_receipts: Mapping[str, str],
    required_sources: Mapping[str, str],
    expected_data_identity: Mapping[str, Any] | None = None,
    expected_identity: str | None = None,
    evidence_ready: bool = True,
) -> dict[str, Any]:
    result = {key: state.get(key) for key in ("state", "status", "schema", "path", "sha256")}
    for key in ("failure", "reason", "post_search_failure"):
        if state.get(key) is not None:
            result[key] = state[key]
    value = state.get("value")
    if state.get("state") == "receipt" and not evidence_ready:
        return {
            **result,
            "state": "binding_error",
            "status": "indeterminate",
            "reported_status": state.get("status"),
            "failure": {
                "type": "ValueError",
                "message": "optional receipt is unusable because its profile evidence is invalid",
            },
            "reported_failure": state.get("failure"),
        }
    if state.get("state") == "receipt" and state.get("schema") != expected_schema:
        return {
            **result,
            "state": "schema_error",
            "status": "indeterminate",
            "failure": {
                "type": "ValueError",
                "message": f"expected {expected_schema} receipt",
            },
            "reported_failure": state.get("failure"),
        }
    if state.get("state") == "receipt" and isinstance(value, dict):
        raw_sources = value.get("source_input_sha256")
        sources = (
            {_resolved(path): digest for path, digest in raw_sources.items()}
            if isinstance(raw_sources, dict)
            and all(
                isinstance(path, str) and isinstance(digest, str)
                for path, digest in raw_sources.items()
            )
            else {}
        )
        required = {**required_sources, **required_receipts}
        binding_errors = [path for path, digest in required.items() if sources.get(path) != digest]
        if (
            expected_data_identity is not None
            and value.get("data_identity") != expected_data_identity
        ):
            binding_errors.append("data_identity")
        if expected_identity is not None and value.get("identity") != expected_identity:
            binding_errors.append("dataset_identity")
        if binding_errors:
            return {
                **result,
                "state": "binding_error",
                "status": "indeterminate",
                "reported_status": state.get("status"),
                "failure": {
                    "type": "ValueError",
                    "message": "optional receipt does not bind the profile and job inputs",
                    "mismatches": binding_errors,
                },
                "reported_failure": state.get("failure"),
            }
    if isinstance(value, dict):
        raw_history = value.get("history")
        history = (
            cast(list[dict[str, Any]], raw_history)
            if isinstance(raw_history, list) and all(isinstance(row, dict) for row in raw_history)
            else []
        )
        if history:
            final = history[-1]
            result["final_draws_per_point_per_stream"] = final.get("draws_per_point_per_stream")
            result["doubling_stable"] = final.get("doubling_stable")
            result["scheduled_look_statuses"] = [
                {
                    "draws_per_point_per_stream": row.get("draws_per_point_per_stream"),
                    "doubling_stable": row.get("doubling_stable"),
                    "status": row.get("status"),
                }
                for row in history
            ]
        if "comparisons" in value:
            result["comparison_count"] = len(value["comparisons"])
        if value.get("schema") == "development-bank-comparison-v1":
            result["original_search_cost"] = value.get("original_search_cost")
            result["cross_evaluation_cost"] = {
                role: row.get("cost")
                for role, row in value.get("cross_evaluations", {}).items()
                if isinstance(row, dict)
            }
            result["nonpassing_level_checks"] = [
                row for row in value.get("level_set_checks", []) if not row.get("passed", False)
            ]
            result["nonpassing_point_count"] = sum(
                not (
                    math.isfinite(float(row.get("delta_w", math.nan)))
                    and abs(float(row["delta_w"])) <= 0.10
                    and row.get("ownership_agreement") is True
                    and (
                        not row.get("inside_either_diagnostic_set", False)
                        or row.get("boundary_contact_agreement") is True
                    )
                )
                for row in value.get("points", [])
            )
            result["reason"] = value.get("reason")
            result["free_fit_agreement"] = value.get("free_fit_agreement")
        if value.get("schema") == "fixed-outer-importance-screen-v1" and history:
            result["elapsed_seconds"] = value.get("elapsed_seconds")
            result["reoptimised_profile"] = value.get("reoptimised_profile")
            result["optimized_root_movement_quantified"] = value.get(
                "optimized_root_movement_quantified"
            )
            result["final_stream_gates"] = [
                {
                    "weight_gates_passed": stream.get("weight_gates_passed"),
                    "contrast_precision_passed": stream.get("contrast_precision_passed"),
                    "ownership_resolved": stream.get("ownership_resolved"),
                }
                for stream in final.get("streams", [])
            ]
    return result


def _dense_receipts(profile_dir: Path) -> tuple[dict[str, Any], dict[str, Any], bool]:
    parent = _receipt_state(profile_dir)
    dense = _receipt_state(profile_dir / "dense")
    binding = False
    parent_value = parent.get("value")
    if parent.get("state") == "receipt" and dense.get("state") == "receipt":
        searches = parent_value.get("searches") if isinstance(parent_value, dict) else None
        schemas_valid = (
            parent.get("schema") == "development-profile-run-v1"
            and dense.get("schema") == "development-profile-search-v1"
            and dense.get("value", {}).get("mode") == "dense"
        )
        expected = (
            searches.get("dense", {}).get("sha256")
            if isinstance(searches, dict) and isinstance(searches.get("dense"), dict)
            else None
        )
        binding = schemas_valid and isinstance(expected, str) and expected == dense["sha256"]
        if not binding:
            dense = {
                **dense,
                "state": "binding_error",
                "status": "indeterminate",
                "failure": {
                    "type": "ValueError",
                    "message": "dense child schema, mode or hash does not match the parent run",
                },
                "reported_failure": dense.get("failure"),
            }
    return parent, dense, binding


def _resolved(path: str | Path) -> str:
    return str(Path(path).resolve())


def _job_source_bindings(job: Mapping[str, Any]) -> dict[str, str]:
    raw = job.get("input_sha256")
    if not isinstance(raw, dict) or not all(
        isinstance(path, str) and isinstance(digest, str) for path, digest in raw.items()
    ):
        raise ValueError("each job requires a string input_sha256 mapping")
    supplied = {_resolved(path): digest for path, digest in cast(dict[str, str], raw).items()}
    input_dir = Path(str(job["input_dir"]))
    required_paths = (
        Path(str(job["observations"])),
        Path(str(job["arrival_bank"])),
        Path(str(job["compressed_bank"])),
        input_dir / "public_inputs.npz",
        input_dir / "exposure.npz",
    )
    result: dict[str, str] = {}
    for path in required_paths:
        key = _resolved(path)
        digest = supplied.get(key)
        if digest is None:
            raise ValueError(f"job input hashes omit {key}")
        result[key] = digest
    observations_key = _resolved(str(job["observations"]))
    if job.get("observations_sha256") != result[observations_key]:
        raise ValueError("job observation hash differs from its input binding")
    return result


def _profile_evidence(job: Mapping[str, Any]) -> dict[str, Any]:
    profile_dir = Path(str(job["profile_dir"]))
    parent, dense, child_binding = _dense_receipts(profile_dir)
    required_sources = _job_source_bindings(job)
    parent_value = parent.get("value")
    parent_sources = (
        parent_value.get("source_input_sha256") if isinstance(parent_value, dict) else None
    )
    source_binding = isinstance(parent_sources, dict) and all(
        parent_sources.get(path) == digest for path, digest in required_sources.items()
    )
    data_identity = parent_value.get("data_identity") if isinstance(parent_value, dict) else None
    site_count_binding = (
        isinstance(data_identity, dict)
        and data_identity.get("site_count") == int(job["site_count"])
    )
    job_binding = bool(source_binding and site_count_binding)
    binding_failure = None
    if parent.get("state") == "receipt" and not job_binding:
        binding_failure = {
            "type": "ValueError",
            "message": "profile parent does not bind the job inputs or expected site count",
        }
    raw_dense_value = dense.get("value")
    dense_value = cast(dict[str, Any], raw_dense_value) if isinstance(raw_dense_value, dict) else {}
    searches = parent_value.get("searches") if isinstance(parent_value, dict) else None
    lean_spec = searches.get("lean") if isinstance(searches, dict) else None
    if isinstance(lean_spec, dict):
        lean = _receipt_state(profile_dir / "lean")
        lean_binding = bool(
            lean.get("state") == "receipt"
            and lean.get("schema") == "development-profile-search-v1"
            and lean.get("value", {}).get("mode") == "lean"
            and lean.get("sha256") == lean_spec.get("sha256")
        )
        if not lean_binding and lean.get("state") == "receipt":
            lean = {
                **lean,
                "state": "binding_error",
                "status": "indeterminate",
                "failure": {
                    "type": "ValueError",
                    "message": "lean child schema, mode or hash does not match the parent run",
                },
                "reported_failure": lean.get("failure"),
            }
    else:
        lean = {"state": "not_requested", "status": None, "path": None, "sha256": None}
        lean_binding = False
    raw_lean_value = lean.get("value")
    lean_value = cast(dict[str, Any], raw_lean_value) if isinstance(raw_lean_value, dict) else {}
    dense_reference_available = dense.get("status") == "profile_numerically_resolved"
    lean_candidate_available = bool(
        lean_binding and lean.get("status") == "profile_numerically_resolved"
    )
    return {
        "profile_dir": profile_dir,
        "parent": parent,
        "dense": dense,
        "dense_value": dense_value,
        "lean": lean,
        "lean_value": lean_value,
        "lean_binding_verified": lean_binding,
        "child_binding_verified": child_binding,
        "job_binding_verified": job_binding,
        "profile_binding_verified": child_binding and job_binding,
        "dense_reference_available": dense_reference_available,
        "lean_candidate_available": lean_candidate_available,
        "binding_failure": binding_failure,
        "required_sources": required_sources,
        "data_identity": data_identity,
    }


def _bound_receipts(evidence: Mapping[str, Any]) -> dict[str, str]:
    result = {}
    for key in ("parent", "dense"):
        state = evidence[key]
        if isinstance(state.get("path"), str) and isinstance(state.get("sha256"), str):
            result[_resolved(state["path"])] = state["sha256"]
    return result


def _level_summary(receipt: Mapping[str, Any]) -> dict[str, Any]:
    levels = receipt.get("tight_level_sets")
    if not isinstance(levels, list) or len(levels) != 1 or not isinstance(levels[0], dict):
        return {
            "category": "unresolved",
            "cutoff": None,
            "set_class": None,
            "components": [],
            "roots": [],
            "reported_root_log_h": [],
            "actual_root_log_h": [],
            "contacts": [],
        }
    level = cast(dict[str, Any], levels[0])
    raw_components = level.get("components")
    components = (
        cast(list[dict[str, Any]], raw_components)
        if isinstance(raw_components, list) and all(isinstance(row, dict) for row in raw_components)
        else []
    )
    raw_roots = level.get("roots")
    roots = (
        cast(list[dict[str, Any]], raw_roots)
        if isinstance(raw_roots, list) and all(isinstance(row, dict) for row in raw_roots)
        else []
    )
    point_map = receipt.get("points")
    points = point_map.get("True", []) if isinstance(point_map, dict) else []
    contacts: list[dict[str, str]] = []
    if isinstance(points, list):
        for fit in points:
            if not isinstance(fit, dict) or "log_h" not in fit:
                continue
            x = float(fit["log_h"])
            if not any(c["lower_log_h"] <= x <= c["upper_log_h"] for c in components):
                continue
            for family in owners(fit):
                for contact in fit[family].get("nuisance_bound_contacts", []):
                    contacts.append({"family": family, "contact": str(contact)})
    category = "available"
    if (
        receipt.get("status") != "profile_numerically_resolved"
        or level.get("status") != "available"
    ):
        category = "unresolved"
    elif len(components) != 1:
        category = "disconnected" if len(components) > 1 else "empty"
    else:
        component = components[0]
        if level.get("set_class") == "full_domain" or (
            component.get("lower_domain_contact") and component.get("upper_domain_contact")
        ):
            category = "full_domain"
        elif component.get("lower_domain_contact") or component.get("upper_domain_contact"):
            category = "truncated"
        elif component.get("singleton") or len(roots) != 2:
            category = "missing_roots"
        else:
            root_values = sorted(float(root["log_h"]) for root in roots)
            endpoints = [float(component["lower_log_h"]), float(component["upper_log_h"])]
            if any(abs(a - b) > 0.005 for a, b in zip(root_values, endpoints, strict=True)):
                category = "missing_roots"
    return {
        "category": category,
        "cutoff": level.get("cutoff"),
        "set_class": level.get("set_class"),
        "components": components,
        "roots": roots,
        "reported_root_log_h": sorted(float(root["log_h"]) for root in roots),
        "actual_root_log_h": sorted(float(root["log_h"]) for root in roots)
        if category == "available"
        else [],
        "contacts": sorted(contacts, key=lambda row: (row["family"], row["contact"])),
    }


def _free_summary(receipt: Mapping[str, Any]) -> dict[str, Any]:
    fit = receipt.get("free", {}).get("True")
    maximum = receipt.get("maximum", {}).get("True", {})
    if (
        receipt.get("status") != "profile_numerically_resolved"
        or not isinstance(fit, dict)
        or not all(family in fit for family in FAMILIES)
    ):
        return {
            "owners": [],
            "effect_status": "unresolved",
            "effect_estimate": None,
            "selected_computational_h": None,
            "sigma_status": "unavailable",
            "sigma": None,
            "sigma_boundary_status": "unavailable",
            "bound_contacts": {},
        }
    selected = owners(fit)
    contacts = {
        family: list(fit[family].get("nuisance_bound_contacts", [])) for family in FAMILIES
    }
    if selected == ["positive_sigma"]:
        log_sigma = fit["positive_sigma"].get("parameters", {}).get("log_sigma")
        sigma = math.exp(float(log_sigma)) if log_sigma is not None else None
        sigma_contacts = [
            value for value in contacts["positive_sigma"] if value.startswith("log_sigma:")
        ]
        sigma_status = "positive_unique" if sigma is not None else "unavailable"
        boundary = "bound" if sigma_contacts else "interior"
    elif selected == ["sigma_zero"]:
        sigma, sigma_status, boundary = 0.0, "zero_family", "zero_family"
    else:
        sigma, sigma_status, boundary = None, "tied", "tied"
    return {
        "owners": selected,
        "effect_status": maximum.get("status", "unavailable"),
        "effect_estimate": maximum.get("effect_estimate"),
        "selected_computational_h": maximum.get("selected_computational_h"),
        "sigma_status": sigma_status,
        "sigma": sigma,
        "sigma_boundary_status": boundary,
        "bound_contacts": contacts,
    }


def _w_at(receipt: Mapping[str, Any], h: float) -> dict[str, Any]:
    if receipt.get("status") != "profile_numerically_resolved":
        return {"status": "unavailable", "value": None}
    diagnostic = receipt.get("post_search_diagnostics")
    if not isinstance(diagnostic, dict) or diagnostic.get("status") != "available":
        return {"status": "unavailable", "value": None}
    target = math.log(float(h))
    rows = diagnostic.get("points", [])
    matches = [row for row in rows if abs(float(row.get("log_h", math.inf)) - target) <= 1e-8]
    if len(matches) != 1 or not math.isfinite(float(matches[0].get("tight_w", math.nan))):
        return {"status": "unavailable", "value": None}
    return {"status": "available", "value": float(matches[0]["tight_w"])}


def _ridge_summary(receipt: Mapping[str, Any], level: Mapping[str, Any]) -> dict[str, Any]:
    if level.get("category") != "available":
        return {"category": level.get("category", "unresolved"), "slope": None, "nodes": []}
    component = level["components"][0]
    lower, upper = float(component["lower_log_h"]), float(component["upper_log_h"])
    switches = receipt.get("tight_family_switches", {})
    if any(
        lower <= float(row["log_h"]) <= upper for row in switches.get("isolated", [])
    ) or any(
        max(lower, float(row["bracket_log_h"][0]))
        <= min(upper, float(row["bracket_log_h"][1]))
        for row in switches.get("tie_intervals", [])
    ):
        return {"category": "tied", "slope": None, "nodes": []}
    nodes: list[tuple[float, float]] = []
    owner_states: set[str] = set()
    bound = False
    for fit in receipt.get("points", {}).get("True", []):
        x = float(fit.get("log_h", math.nan))
        if not math.isfinite(x) or not lower <= x <= upper:
            continue
        selected = owners(fit)
        owner_states.add("+".join(selected))
        if selected == ["positive_sigma"]:
            contacts = fit["positive_sigma"].get("nuisance_bound_contacts", [])
            bound |= any(str(value).startswith("log_sigma:") for value in contacts)
            log_sigma = fit["positive_sigma"].get("parameters", {}).get("log_sigma")
            if log_sigma is not None:
                nodes.append((x, float(log_sigma)))
    nodes = sorted(set(nodes))
    node_rows = [{"log_h": x, "log_sigma": y} for x, y in nodes]
    if any("+" in state for state in owner_states):
        return {"category": "tied", "slope": None, "nodes": node_rows}
    if owner_states != {"positive_sigma"}:
        category = "zero_family" if owner_states == {"sigma_zero"} else "ownership_transition"
        return {"category": category, "slope": None, "nodes": node_rows}
    if bound:
        return {"category": "sigma_bound_contact", "slope": None, "nodes": node_rows}
    if (
        len(nodes) < 2
        or abs(nodes[0][0] - lower) > 0.005
        or abs(nodes[-1][0] - upper) > 0.005
    ):
        return {"category": "insufficient_nodes", "slope": None, "nodes": node_rows}
    return {
        "category": "available",
        "slope": uniform_piecewise_linear_slope(nodes),
        "nodes": node_rows,
    }


def summarize_dataset(
    job: Mapping[str, Any],
    *,
    evidence: Mapping[str, Any] | None = None,
    independent_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    profile = evidence if evidence is not None else _profile_evidence(job)
    profile_dir = cast(Path, profile["profile_dir"])
    parent = cast(dict[str, Any], profile["parent"])
    dense = cast(dict[str, Any], profile["dense"])
    dense_value = cast(dict[str, Any], profile["dense_value"])
    numerical_available = bool(
        profile["profile_binding_verified"]
        and profile["dense_reference_available"]
    )
    scientific_value = dense_value if numerical_available else {}
    level = _level_summary(scientific_value)
    report_h = float(job["report_h"])
    bank_path = job.get("bank_comparison_dir") if independent_evidence is not None else None
    integration_path = job.get("integration_dir")
    failures = {
        key: value
        for key, value in {
            "profile_run": parent.get("failure"),
            "profile_run_reason": parent.get("reason"),
            "dense_search": dense.get("failure"),
            "dense_reported_failure": dense.get("reported_failure"),
            "dense_search_reason": dense.get("reason"),
            "dense_post_search": dense.get("post_search_failure"),
            "profile_input_binding": profile.get("binding_failure"),
        }.items()
        if value is not None
    }
    return {
        "dataset_id": str(job["dataset_id"]),
        "biological_history_id": str(job["biological_history_id"]),
        "arm": str(job["arm"]),
        "bank_role": str(job["bank_role"]),
        "report_h": report_h,
        "profile_dir": str(profile_dir.resolve()),
        "profile_run_status": parent.get("status"),
        "dense_lean_comparison_status": parent.get("status"),
        "dense_search_status": dense.get("status"),
        "lean_candidate_status": profile["lean"].get("status"),
        "lean_candidate_available": profile["lean_candidate_available"],
        "dense_child_binding_verified": profile["child_binding_verified"],
        "profile_job_binding_verified": profile["job_binding_verified"],
        "numerical_summary_available": numerical_available,
        "failures": failures,
        "free": _free_summary(scientific_value),
        "w1": _w_at(scientific_value, 1.0),
        "w_truth": _w_at(scientific_value, report_h),
        "diagnostic_level": level,
        "ridge": _ridge_summary(scientific_value, level),
        "cost": {
            "scope": "independent_search_and_post_search_costs",
            "dense": dense_value.get(
                "cost", {"search": None, "post_search_seconds": None}
            )
            if profile["profile_binding_verified"]
            else None,
            "lean": profile["lean_value"].get(
                "cost", {"search": None, "post_search_seconds": None}
            )
            if profile["lean_binding_verified"] and profile["job_binding_verified"]
            else None,
        },
        "bank_comparison": _optional_receipt_summary(
            _receipt_state(bank_path),
            expected_schema="development-bank-comparison-v1",
            required_receipts={
                **_bound_receipts(profile),
                **(
                    _bound_receipts(independent_evidence)
                    if independent_evidence is not None
                    else {}
                ),
            },
            required_sources={
                **cast(dict[str, str], profile["required_sources"]),
                **(
                    cast(dict[str, str], independent_evidence["required_sources"])
                    if independent_evidence is not None
                    else {}
                ),
            },
            evidence_ready=bool(
                numerical_available
                and independent_evidence is not None
                and independent_evidence["profile_binding_verified"]
                and independent_evidence["dense_reference_available"]
            ),
        ),
        "integration_screen": _optional_receipt_summary(
            _receipt_state(integration_path),
            expected_schema="fixed-outer-importance-screen-v1",
            required_receipts=_bound_receipts(profile),
            required_sources=cast(dict[str, str], profile["required_sources"]),
            expected_data_identity=(
                cast(dict[str, Any], profile["data_identity"])
                if isinstance(profile["data_identity"], dict)
                else None
            ),
            expected_identity=str(job["dataset_id"]),
            evidence_ready=numerical_available,
        ),
        "receipt_sha256": {"profile_run": parent.get("sha256"), "dense": dense.get("sha256")},
    }


def _manifest_contract(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if manifest.get("schema") != "development-challenge-manifest-v1":
        raise ValueError("manifest has the wrong schema")
    reporting = manifest.get("reporting")
    archived = manifest.get("datasets")
    cases = manifest.get("optional_c_cases")
    if (
        not isinstance(reporting, dict)
        or not isinstance(archived, list)
        or not isinstance(cases, list)
    ):
        raise ValueError("manifest lacks reporting, archived datasets or C cases")
    expected: dict[str, dict[str, Any]] = {}
    for raw in archived:
        if not isinstance(raw, dict):
            raise ValueError("archived manifest rows must be objects")
        history = str(raw["biological_history_id"])
        report = reporting.get(history)
        if not isinstance(report, dict):
            raise ValueError(f"manifest reporting is missing for {history}")
        expected[str(raw["dataset_id"])] = {
            "biological_history_id": history,
            "arm": str(raw["arm"]),
            "bank_roles": set(raw["bank_roles"]),
            "report_h": float(report["h"]),
            "site_count": int(raw["site_count"]),
            "source_observations_sha256": str(raw["source_observations_sha256"]),
        }
    for raw in cases:
        if not isinstance(raw, dict) or not isinstance(raw.get("reporting"), dict):
            raise ValueError("C manifest rows must contain reporting objects")
        dataset_id = str(raw["dataset_id"])
        expected[dataset_id] = {
            "biological_history_id": dataset_id,
            "arm": "C",
            "bank_roles": {"B0", "A"},
            "report_h": float(raw["reporting"]["h"]),
            "site_count": int(raw["site_count"]),
            "source_observations_sha256": None,
        }
    if (
        len(expected) != 38
        or sum("A" in row["bank_roles"] for row in expected.values()) != 22
        or sum(len(row["bank_roles"]) for row in expected.values()) != 60
        or any(
            row["bank_roles"] not in ({"B0"}, {"B0", "A"}) for row in expected.values()
        )
        or Counter(row["arm"] for row in expected.values()) != Counter({"A": 16, "B": 16, "C": 6})
    ):
        raise ValueError("frozen manifest is not the reviewed 38-dataset, 22-A-role panel")
    return expected


def validate_jobs(
    jobs: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    prepared_manifest: Mapping[str, Any],
    c_receipts: Mapping[str, Mapping[str, Any]],
    *,
    frozen_manifest_sha256: str,
) -> dict[tuple[str, str], Mapping[str, Any]]:
    required = {
        "dataset_id",
        "biological_history_id",
        "arm",
        "bank_role",
        "profile_dir",
        "report_h",
        "site_count",
        "input_dir",
        "observations",
        "observations_sha256",
        "arrival_bank",
        "compressed_bank",
        "input_sha256",
    }
    expected = _manifest_contract(manifest)
    prepared_rows = prepared_manifest.get("datasets")
    if (
        prepared_manifest.get("schema") != "development-challenge-manifest-v1"
        or prepared_manifest.get("frozen_manifest_sha256") != frozen_manifest_sha256
        or not isinstance(prepared_rows, list)
    ):
        raise ValueError("prepared archived manifest does not bind the frozen manifest")
    prepared = {
        str(row["dataset_id"]): row for row in prepared_rows if isinstance(row, dict)
    }
    archived_ids = {
        str(row["dataset_id"])
        for row in cast(list[dict[str, Any]], manifest["datasets"])
    }
    if set(prepared) != archived_ids:
        raise ValueError("prepared archived dataset identities differ from the freeze")
    c_ids = {dataset_id for dataset_id, row in expected.items() if row["arm"] == "C"}
    if set(c_receipts) != c_ids:
        raise ValueError("generated C receipt identities differ from the freeze")
    expected_keys = {
        (dataset_id, role)
        for dataset_id, row in expected.items()
        for role in row["bank_roles"]
    }
    if len(jobs) != len(expected_keys) or any(not required <= set(job) for job in jobs):
        raise ValueError("jobs must describe the exact frozen profile-role panel")
    lookup = {(str(job["dataset_id"]), str(job["bank_role"])): job for job in jobs}
    if len(lookup) != len(jobs) or set(lookup) != expected_keys:
        raise ValueError("job dataset and bank-role identities differ from the frozen manifest")
    profile_dirs = [_resolved(str(job["profile_dir"])) for job in jobs]
    if len(set(profile_dirs)) != len(profile_dirs):
        raise ValueError("every dataset-bank profile must have a distinct profile directory")
    observations_by_dataset: dict[str, tuple[str, str]] = {}
    prepared_observations: dict[str, str] = {}
    for dataset_id, row in prepared.items():
        expected_row = expected[dataset_id]
        if (
            not isinstance(row.get("observations_sha256"), str)
            or row.get("biological_history_id") != expected_row["biological_history_id"]
            or row.get("arm") != expected_row["arm"]
            or row.get("site_count") != expected_row["site_count"]
            or row.get("source_observations_sha256")
            != expected_row["source_observations_sha256"]
        ):
            raise ValueError(f"prepared observation metadata differs from freeze: {dataset_id}")
        prepared_observations[dataset_id] = row["observations_sha256"]
    for (dataset_id, _), job in lookup.items():
        row = expected[dataset_id]
        if (
            str(job["biological_history_id"]) != row["biological_history_id"]
            or str(job["arm"]) != row["arm"]
            or int(job["site_count"]) != row["site_count"]
            or not math.isclose(float(job["report_h"]), row["report_h"], abs_tol=1e-12)
        ):
            raise ValueError(f"job metadata differs from the frozen manifest: {dataset_id}")
        if row["source_observations_sha256"] is not None and (
            job.get("source_observations_sha256") != row["source_observations_sha256"]
        ):
            raise ValueError(f"job source observation differs from the freeze: {dataset_id}")
        if row["arm"] == "C":
            generated = c_receipts[dataset_id]
            if (
                generated.get("state") != "generated_development_only"
                or generated.get("dataset_id") != dataset_id
                or generated.get("arm") != "C"
                or generated.get("observations_sha256") != job["observations_sha256"]
                or generated.get("site_count") != row["site_count"]
                or not isinstance(generated.get("reporting"), dict)
                or not math.isclose(
                    float(generated["reporting"].get("h", math.nan)),
                    row["report_h"],
                    abs_tol=1e-12,
                )
                or generated.get("source_input_sha256", {}).get("frozen_manifest")
                != frozen_manifest_sha256
            ):
                raise ValueError(f"C observation receipt differs from the freeze: {dataset_id}")
        elif prepared_observations.get(dataset_id) != job["observations_sha256"]:
            raise ValueError(f"prepared observation differs from the job: {dataset_id}")
        sources = _job_source_bindings(job)
        identity = (_resolved(str(job["observations"])), str(job["observations_sha256"]))
        if (
            dataset_id in observations_by_dataset
            and observations_by_dataset[dataset_id] != identity
        ):
            raise ValueError(f"bank roles use different observations: {dataset_id}")
        observations_by_dataset[dataset_id] = identity
        if sources[identity[0]] != identity[1]:
            raise ValueError(f"job observation identity is not bound: {dataset_id}")
    if len({identity[0] for identity in observations_by_dataset.values()}) != 38:
        raise ValueError("each frozen dataset must use its own observation artifact")
    if any(
        not math.isfinite(float(job["report_h"])) or not 1.0 <= float(job["report_h"]) <= 30.0
        for job in jobs
    ):
        raise ValueError("report_h must be finite and inside [1,30]")
    by_history: dict[str, list[str]] = defaultdict(list)
    for row in expected.values():
        by_history[row["biological_history_id"]].append(row["arm"])
    paired = [history for history, values in by_history.items() if sorted(values) == ["A", "B"]]
    separate_c = [history for history, values in by_history.items() if values == ["C"]]
    if len(paired) != 16 or len(separate_c) != 6 or len(by_history) != 22:
        raise ValueError("A/B histories must be paired and all six C histories separate")
    return lookup


def _pair_summary(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    level_a, level_b = a["diagnostic_level"], b["diagnostic_level"]
    roots_a, roots_b = level_a.get("actual_root_log_h"), level_b.get("actual_root_log_h")
    roots_available = (
        a["numerical_summary_available"]
        and b["numerical_summary_available"]
        and level_a["category"] == level_b["category"] == "available"
        and isinstance(roots_a, list)
        and isinstance(roots_b, list)
        and len(roots_a) == len(roots_b) == 2
    )
    d_lower: float | None
    d_upper: float | None
    if roots_available:
        lower_a, upper_a = cast(list[float], roots_a)
        lower_b, upper_b = cast(list[float], roots_b)
        d_lower = lower_a - lower_b
        d_upper = upper_b - upper_a
        expansion_category = "available"
    else:
        d_lower = d_upper = None
        expansion_category = f"A:{level_a['category']}|B:{level_b['category']}"
    slope_a, slope_b = a["ridge"].get("slope"), b["ridge"].get("slope")
    slopes_available = bool(
        a["numerical_summary_available"]
        and b["numerical_summary_available"]
        and a["ridge"]["category"] == b["ridge"]["category"] == "available"
        and isinstance(slope_a, int | float)
        and isinstance(slope_b, int | float)
        and math.isfinite(float(slope_a))
        and math.isfinite(float(slope_b))
    )
    slope_difference = (
        float(cast(float, slope_b)) - float(cast(float, slope_a))
        if slopes_available
        else None
    )
    return {
        "biological_history_id": a["biological_history_id"],
        "dataset_A": a["dataset_id"],
        "dataset_B": b["dataset_id"],
        "expansion_category": expansion_category,
        "dL": d_lower,
        "dU": d_upper,
        "prediction_dU_gt_dL": (
            d_upper > d_lower if d_upper is not None and d_lower is not None else None
        ),
        "ridge_A_category": a["ridge"]["category"],
        "ridge_B_category": b["ridge"]["category"],
        "slope_A": slope_a,
        "slope_B": slope_b,
        "slope_B_minus_A": slope_difference,
        "prediction_slope_B_minus_A_ge_0": (
            slope_difference >= 0 if slope_difference is not None else None
        ),
        "descriptive_only": True,
        "numerical_acceptance_gate": False,
    }


def summarize_jobs(
    jobs: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    prepared_manifest: Mapping[str, Any],
    c_receipts: Mapping[str, Mapping[str, Any]],
    *,
    frozen_manifest_sha256: str,
) -> dict[str, Any]:
    lookup = validate_jobs(
        jobs,
        manifest,
        prepared_manifest,
        c_receipts,
        frozen_manifest_sha256=frozen_manifest_sha256,
    )
    evidence = {key: _profile_evidence(job) for key, job in lookup.items()}
    datasets = [
        summarize_dataset(
            lookup[(dataset_id, "B0")],
            evidence=evidence[(dataset_id, "B0")],
            independent_evidence=evidence.get((dataset_id, "A")),
        )
        for dataset_id in sorted(_manifest_contract(manifest))
    ]
    by_history: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in datasets:
        by_history[row["biological_history_id"]][row["arm"]] = row
    pairs = [
        _pair_summary(values["A"], values["B"])
        for _, values in sorted(by_history.items())
        if set(values) == {"A", "B"}
    ]
    return {
        "schema": "development-challenge-summary-v1",
        "status": "descriptive_summary_complete",
        "dataset_count": len(datasets),
        "paired_history_count": len(pairs),
        "separate_c_history_count": 6,
        "profile_role_count": len(evidence),
        "profile_role_binding_counts": dict(
            Counter(
                "verified" if row["profile_binding_verified"] else "unverified"
                for row in evidence.values()
            )
        ),
        "profile_role_evidence": [
            {
                "dataset_id": dataset_id,
                "bank_role": bank_role,
                "profile_run_status": row["parent"].get("status"),
                "dense_search_status": row["dense"].get("status"),
                "dense_child_binding_verified": row["child_binding_verified"],
                "profile_job_binding_verified": row["job_binding_verified"],
                "dense_reference_available": row["dense_reference_available"],
                "lean_candidate_available": row["lean_candidate_available"],
                "dense_lean_comparison_status": row["parent"].get("status"),
                "receipt_sha256": {
                    "profile_run": row["parent"].get("sha256"),
                    "dense": row["dense"].get("sha256"),
                },
                "failures": {
                    key: value
                    for key, value in {
                        "profile_run": row["parent"].get("failure"),
                        "dense_search": row["dense"].get("failure"),
                        "dense_reported_failure": row["dense"].get("reported_failure"),
                        "lean_search": row["lean"].get("failure"),
                        "profile_input_binding": row.get("binding_failure"),
                    }.items()
                    if value is not None
                },
            }
            for (dataset_id, bank_role), row in sorted(evidence.items())
        ],
        "profile_status_counts": dict(
            Counter(row["profile_run_status"] or "missing_status" for row in datasets)
        ),
        "dense_lean_comparison_status_counts": dict(
            Counter(row["dense_lean_comparison_status"] or "missing_status" for row in datasets)
        ),
        "dense_status_counts": dict(
            Counter(row["dense_search_status"] or "missing_status" for row in datasets)
        ),
        "lean_candidate_status_counts": dict(
            Counter(
                row["lean_candidate_status"]
                if row["lean_candidate_status"] is not None
                else "not_available"
                for row in datasets
            )
        ),
        "bank_comparison_status_counts": dict(
            Counter(
                row["bank_comparison"]["status"] or row["bank_comparison"]["state"]
                for row in datasets
            )
        ),
        "integration_screen_status_counts": dict(
            Counter(
                row["integration_screen"]["status"] or row["integration_screen"]["state"]
                for row in datasets
            )
        ),
        "datasets": datasets,
        "paired_descriptives": pairs,
        "predictions": {
            "expansion": "dU > dL",
            "ridge": "slope_B - slope_A >= 0",
            "descriptive_only": True,
            "numerical_acceptance_gate": False,
        },
        "scientific_claim": False,
        "figure_generated": False,
    }


def _csv_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, sort_keys=True, allow_nan=False)


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fields})


def write_summary(result: Mapping[str, Any], output: Path) -> None:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    write_json(output / "summary.json", result)
    dataset_rows = [
        {
            **row,
            "free_effect_status": row["free"]["effect_status"],
            "free_effect_estimate": row["free"]["effect_estimate"],
            "free_sigma_status": row["free"]["sigma_status"],
            "free_sigma": row["free"]["sigma"],
            "free_sigma_boundary_status": row["free"]["sigma_boundary_status"],
            "free_owners": row["free"]["owners"],
            "free_bound_contacts": row["free"]["bound_contacts"],
            "diagnostic_category": row["diagnostic_level"]["category"],
            "diagnostic_roots_log_h": row["diagnostic_level"]["reported_root_log_h"],
            "diagnostic_components": row["diagnostic_level"]["components"],
            "diagnostic_bound_contacts": row["diagnostic_level"]["contacts"],
            "ridge_category": row["ridge"]["category"],
            "ridge_slope": row["ridge"]["slope"],
            "w1_status": row["w1"]["status"],
            "w1_value": row["w1"]["value"],
            "wtruth_status": row["w_truth"]["status"],
            "wtruth_value": row["w_truth"]["value"],
            "dense_search_cost": row["cost"]["dense"].get("search")
            if isinstance(row["cost"].get("dense"), dict)
            else None,
            "dense_post_search_seconds": row["cost"]["dense"].get("post_search_seconds")
            if isinstance(row["cost"].get("dense"), dict)
            else None,
            "lean_search_cost": row["cost"]["lean"].get("search")
            if isinstance(row["cost"].get("lean"), dict)
            else None,
            "lean_post_search_seconds": row["cost"]["lean"].get("post_search_seconds")
            if isinstance(row["cost"].get("lean"), dict)
            else None,
            "bank_comparison_state": row["bank_comparison"]["state"],
            "bank_comparison_status": row["bank_comparison"]["status"],
            "bank_comparison_original_search_cost": row["bank_comparison"].get(
                "original_search_cost"
            ),
            "bank_comparison_cross_evaluation_cost": row["bank_comparison"].get(
                "cross_evaluation_cost"
            ),
            "integration_screen_state": row["integration_screen"]["state"],
            "integration_screen_status": row["integration_screen"]["status"],
            "integration_elapsed_seconds": row["integration_screen"].get("elapsed_seconds"),
        }
        for row in result["datasets"]
    ]
    write_csv(
        output / "datasets.csv",
        dataset_rows,
        (
            "dataset_id",
            "biological_history_id",
            "arm",
            "bank_role",
            "report_h",
            "profile_run_status",
            "dense_lean_comparison_status",
            "dense_search_status",
            "lean_candidate_status",
            "lean_candidate_available",
            "numerical_summary_available",
            "free_effect_status",
            "free_effect_estimate",
            "free_sigma_status",
            "free_sigma",
            "free_sigma_boundary_status",
            "free_owners",
            "free_bound_contacts",
            "diagnostic_category",
            "diagnostic_components",
            "diagnostic_bound_contacts",
            "ridge_category",
            "ridge_slope",
            "w1_status",
            "w1_value",
            "wtruth_status",
            "wtruth_value",
            "dense_search_cost",
            "dense_post_search_seconds",
            "lean_search_cost",
            "lean_post_search_seconds",
            "bank_comparison_state",
            "bank_comparison_status",
            "bank_comparison_original_search_cost",
            "bank_comparison_cross_evaluation_cost",
            "integration_screen_state",
            "integration_screen_status",
            "integration_elapsed_seconds",
            "failures",
            "diagnostic_roots_log_h",
        ),
    )
    write_csv(
        output / "paired_descriptives.csv",
        result["paired_descriptives"],
        (
            "biological_history_id",
            "dataset_A",
            "dataset_B",
            "expansion_category",
            "dL",
            "dU",
            "prediction_dU_gt_dL",
            "ridge_A_category",
            "ridge_B_category",
            "slope_A",
            "slope_B",
            "slope_B_minus_A",
            "prediction_slope_B_minus_A_ge_0",
            "descriptive_only",
            "numerical_acceptance_gate",
        ),
    )


def _read_bound_json(specification: Any, *, label: str) -> tuple[dict[str, Any], str]:
    if (
        not isinstance(specification, dict)
        or not isinstance(specification.get("path"), str)
        or not isinstance(specification.get("sha256"), str)
    ):
        raise ValueError(f"{label} preparation binding is malformed")
    path = Path(specification["path"])
    actual = sha256(path)
    if actual != specification["sha256"]:
        raise ValueError(f"{label} preparation receipt hash differs")
    value = read_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"{label} preparation receipt must be an object")
    return cast(dict[str, Any], value), actual


def _load_prepared_inputs(
    jobs_document: Mapping[str, Any], *, frozen_manifest_sha256: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, str]]:
    if jobs_document.get("frozen_panel_sha256") != frozen_manifest_sha256:
        raise ValueError("jobs document does not bind the frozen panel manifest")
    prepared = jobs_document.get("prepared_inputs")
    if not isinstance(prepared, dict):
        raise ValueError("jobs document lacks prepared_inputs")
    archived, archived_hash = _read_bound_json(
        prepared.get("archived"), label="archived panel"
    )
    raw_c = prepared.get("C")
    if not isinstance(raw_c, dict):
        raise ValueError("jobs document lacks generated-C receipt bindings")
    c_receipts: dict[str, dict[str, Any]] = {}
    hashes = {"archived": archived_hash}
    for dataset_id, specification in raw_c.items():
        if not isinstance(dataset_id, str):
            raise ValueError("generated-C receipt identity must be a string")
        receipt, digest = _read_bound_json(specification, label=dataset_id)
        c_receipts[dataset_id] = receipt
        hashes[dataset_id] = digest
    return archived, c_receipts, hashes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    raw = read_json(args.jobs)
    jobs = raw.get("jobs") if isinstance(raw, dict) else None
    if not isinstance(jobs, list) or not all(isinstance(job, dict) for job in jobs):
        raise ValueError("jobs JSON must be an object containing a jobs list")
    manifest = read_json(args.manifest)
    if not isinstance(manifest, dict):
        raise ValueError("manifest JSON must be an object")
    if sha256(args.manifest) != FROZEN_MANIFEST_SHA256:
        raise ValueError("--manifest must be the reviewed frozen panel manifest")
    frozen_manifest_sha256 = sha256(args.manifest)
    prepared_manifest, c_receipts, preparation_hashes = _load_prepared_inputs(
        cast(dict[str, Any], raw), frozen_manifest_sha256=frozen_manifest_sha256
    )
    result = summarize_jobs(
        cast(list[dict[str, Any]], jobs),
        cast(dict[str, Any], manifest),
        prepared_manifest,
        c_receipts,
        frozen_manifest_sha256=frozen_manifest_sha256,
    )
    result["jobs_sha256"] = sha256(args.jobs)
    result["manifest_sha256"] = sha256(args.manifest)
    result["prepared_input_sha256"] = preparation_hashes
    write_summary(result, args.output_dir)
    print(json.dumps({"status": result["status"], "datasets": result["dataset_count"]}))


if __name__ == "__main__":
    main()
