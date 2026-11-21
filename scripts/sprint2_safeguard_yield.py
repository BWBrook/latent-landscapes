"""Reduce two registered Sprint 2 safeguard diagnostics from existing receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any

import summarise_sprint2_qualification as qualification
from fit_checkpoints import decode, digest
from qualify_spatial_profiles import compare_level_sets
from run_development_profile import compact_fit
from scipy.stats import t

Json = dict[str, Any]
FAMILIES = ("positive_sigma", "sigma_zero")
LR_THRESHOLD = 1e-3
ACCEPTANCE_SOURCE = "432bb6e56e672f9e57f2f7bc369546023b07662e"
ACCEPTANCE_SUMMARY = "bb195b4e6d29705168db904c503ff88741f1f7606f09e312856f893ee5ba71d5"
EVIDENCE_ERRORS = (KeyError, TypeError, ValueError, OSError, OverflowError)


def verified_bytes(paths: list[Path], sha256: str) -> bytes:
    for path in dict.fromkeys(paths):
        if path.is_file():
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != sha256:
                raise ValueError(f"receipt or stream checksum mismatch: {path}")
            return data
    raise FileNotFoundError(str(paths[-1]))


def fit_identity(fit: Json, source: str, role: str, observation_sha256: str) -> None:
    observations = [
        sha for path, sha in fit["input_sha256"].items() if Path(path).name == "observations.npz"
    ]
    if (
        fit["schema"] != "fit-dataset-v1"
        or fit["source"]["commit"] != source
        or fit["source"]["working_tree_changes"] != []
        or fit["search_mode"] != ("dense" if role == "dense" else "lean")
        or observations != [observation_sha256]
        or tuple(fit["cutoffs"]) != qualification.CUTOFFS
        or fit["tight_replay"] != "always_on_inside_PanelSearch.run"
    ):
        raise ValueError("fit identity differs from the frozen case")


def candidate_eligibility(fit: Json) -> dict[str, bool]:
    values = {family: fit[family]["eligible"] for family in FAMILIES}
    if any(type(value) is not bool for value in values.values()):
        raise ValueError("invalid raw eligibility evidence")
    return values


def winner(fit: Json) -> tuple[float, dict[str, bool]]:
    return qualification.finite(fit["criterion"]), candidate_eligibility(fit)


def w_comparison(
    free: Json, points: dict[float, Json], comparator_free: Json, comparator: dict[float, Json]
) -> Json:
    top, eligible = winner(free)
    comparator_top, comparator_eligibility = winner(comparator_free)
    eligibility_changes = [
        {"location": "free", "family": family}
        for family in FAMILIES
        if eligible[family] != comparator_eligibility[family]
    ]
    shared = sorted(points.keys() & comparator.keys())
    changes = []
    max_delta = None
    null_delta = None
    for x in shared:
        point, left = winner(points[x])
        other, right = winner(comparator[x])
        eligibility_changes.extend(
            {"location": x, "family": family}
            for family in FAMILIES
            if left[family] != right[family]
        )
        a, b = 2 * (top - point), 2 * (comparator_top - other)
        delta = b - a
        max_delta = max(max_delta or 0.0, abs(delta))
        if x == 0.0:
            null_delta = delta
        if abs(delta) > LR_THRESHOLD:
            changes.append({"log_h": x, "prefix_w": a, "comparator_w": b, "delta_w": delta})
    return {
        "prefix_free_criterion": top,
        "comparator_free_criterion": comparator_top,
        "prefix_h1_lr": 2 * (top - winner(points[0.0])[0]) if 0.0 in points else None,
        "comparator_h1_lr": (
            2 * (comparator_top - winner(comparator[0.0])[0]) if 0.0 in comparator else None
        ),
        "h1_delta_w": null_delta,
        "prefix_nodes": len(points),
        "comparator_nodes": len(comparator),
        "shared_exact_nodes": len(shared),
        "prefix_only_nodes": len(points.keys() - comparator.keys()),
        "comparator_only_nodes": len(comparator.keys() - points.keys()),
        "eligibility_comparisons": len(FAMILIES) * (len(shared) + 1),
        "eligibility_changes": eligibility_changes,
        "lr_changes_above_threshold": changes,
        "max_abs_delta_w": max_delta,
    }


def prefix_fit(fit: Json, search: Json, stream: bytes, topology: Json | None = None) -> Json:
    prefix: dict[float, Json] = {}
    free = None
    marker = None
    marker_kind = None
    post_marker_standard = 0
    prefix_operations = 0
    last = None
    ordinal = -1
    for ordinal, line in enumerate(stream.splitlines()):
        event = json.loads(line)
        last = event
        kind = event["kind"]
        if kind == "unresolved_fit":
            sources = [row["source"] for row in event["candidates"]]
            if marker is None and any(source.startswith("tight_") for source in sources):
                marker, marker_kind = ordinal, "first_tight_unresolved_fit"
            continue
        if kind not in ("fixed_fit", "free_fit"):
            continue
        value = event["fit"]
        tight = value["tight"] if kind == "fixed_fit" else event["tight"]
        if type(tight) is not bool:
            raise ValueError("invalid search-event regime")
        if tight and marker is None:
            marker, marker_kind = ordinal, kind
        if tight:
            continue
        if marker is not None:
            post_marker_standard += 1
        else:
            prefix_operations += 1
            if kind == "fixed_fit":
                prefix[qualification.finite(value["log_h"])] = value
            else:
                free = value
    if topology is not None:
        if prefix_operations != topology["operation_count"]:
            raise ValueError("prefix fit events disagree with the topology checkpoint boundary")
        if free is None or topology["spatial_sha256"] != digest(
            {
                "free": compact_fit(free),
                "points": [compact_fit(point) for _, point in sorted(prefix.items())],
            }
        ):
            raise ValueError("prefix search winners disagree with the topology checkpoint")
        if marker is None:
            marker, marker_kind = ordinal + 1, "checkpoint_before_unrecorded_tight"
    diagnostic: Json = {
        "marker_zero_based_event": marker,
        "marker_kind": marker_kind,
        "prefix_retained_nodes": len(prefix),
        "prefix_free_observed": free is not None,
        "post_marker_standard_fit_events": post_marker_standard,
        "comparisons": {},
    }
    if marker is None:
        candidates = last.get("candidates", []) if last else []
        sources = [row["source"] for row in candidates]
        failure = search.get("failure") or {}
        forced_failure = (
            last is not None
            and last["kind"] == "unresolved_fit"
            and bool(sources)
            and all(source.startswith("standard_") for source in sources)
            and fit["failure_class"] in qualification.SCIENTIFIC_FAILURES
            and failure.get("type") == "RuntimeError"
            and (
                failure["message"] == "unresolved candidate exceeds selected family envelope"
                or failure["message"].startswith("unresolved variance family:")
            )
            and search["status"] == "indeterminate"
        )
        return {
            **diagnostic,
            "status": "known_standard_failure" if forced_failure else "prefix_unavailable",
            "search_failure": failure or None,
        }
    if free is None or 0.0 not in prefix or qualification.LOG_MAX not in prefix:
        raise ValueError("tight marker has no complete standard free/endpoints")
    for name, tight in (("primary_tight", "True"), ("post_replay_standard", "False")):
        reference = search["free"].get(tight)
        if reference is None:
            continue
        rows = search["points"][tight]
        points = {qualification.finite(row["log_h"]): row for row in rows}
        if len(points) != len(rows):
            raise ValueError("duplicate retained search coordinates")
        diagnostic["comparisons"][name] = w_comparison(free, prefix, reference, points)
    if topology is not None:
        diagnostic["spatial_topology"] = topology
        if "tight_level_sets" in search:
            diagnostic["spatial_topology_vs_primary"] = {
                "cutoff_checks": [
                    compare_level_sets(standard, tight)
                    for standard, tight in zip(
                        topology["level_sets"], search["tight_level_sets"], strict=True
                    )
                ],
                "isolated_switch_counts": [
                    len(topology["family_switches"]["isolated"]),
                    len(search["tight_family_switches"]["isolated"]),
                ],
            }
    return {**diagnostic, "status": "prefix_available"}


def load_topology(fit: Json, receipt_path: Path) -> Json | None:
    checkpoints = receipt_path.parents[2] / "checkpoints"
    path = checkpoints / "search/standard_prefix_topology.json"
    if not path.is_file():
        return None
    header = decode(json.loads((checkpoints / "identity.json").read_text()))
    saved = decode(json.loads(path.read_text()))
    identity = header["identity"]
    topology = saved["payload"]
    if (
        header["schema"] != "fit-checkpoint-identity-v1"
        or header["header_sha256"]
        != digest({key: value for key, value in header.items() if key != "header_sha256"})
        or header["identity_sha256"] != digest(identity)
        or saved["identity_sha256"] != header["identity_sha256"]
        or any(
            identity[name] != fit[name]
            for name in ("source", "inputs", "input_sha256", "search_mode")
        )
        or saved["payload_sha256"] != digest(topology)
        or tuple(level["cutoff"] for level in topology["level_sets"]) != qualification.CUTOFFS
        or any(level["status"] != "available" for level in topology["level_sets"])
    ):
        raise ValueError("pre-tight topology checkpoint binding differs")
    return topology


def load_prefix(fit: Json, receipt_path: Path) -> Json:
    nested = fit["search"]
    search_sha = nested["receipt_sha256"]
    search = json.loads(
        verified_bytes(
            [receipt_path.parent / "search_receipt.json", Path(nested["receipt"])], search_sha
        )
    )
    if search["status"] != nested["status"] or search.get("failure") != nested.get("failure"):
        raise ValueError("root and nested search receipts disagree")
    reference = search["evaluation_stream"]
    stream = verified_bytes(
        [receipt_path.parent / "search/evaluations.jsonl", Path(reference["path"])],
        reference["sha256"],
    )
    topology, topology_error, report = None, None, None
    try:
        topology = load_topology(fit, receipt_path)
        if topology is not None:
            report = prefix_fit(fit, search, stream, topology)
    except EVIDENCE_ERRORS as error:
        topology, topology_error = None, str(error)
    return {
        **(report if report is not None else prefix_fit(fit, search, stream)),
        "spatial_topology_checkpoint_error": topology_error,
        "spatial_topology_checkpoint_sha256": digest(topology) if topology is not None else None,
        "search_sha256": search_sha,
        "evaluation_stream_sha256": reference["sha256"],
    }


def without_latent_audit(fit: Json) -> Json:
    chosen = fit["failure_class"]
    flags = fit["all_triggered"]
    if (flags[0] if flags else "resolved") != chosen:
        raise ValueError("fit failure class disagrees with the triggering flags")
    errors = fit["errors"]
    numerical = [error for error in errors if not error["execution"]]
    if bool(numerical) != ("numerical_error" in flags):
        raise ValueError("fit numerical errors disagree with the triggering flags")
    if bool(fit["latent_audit"].get("multimodal_latent")) != ("multimodal_latent" in flags):
        raise ValueError("latent audit disagrees with the triggering flags")
    omitted = {"multimodal_latent"}
    if numerical and all(error["stage"] == "latent_audit" for error in numerical):
        omitted.add("numerical_error")
    remaining = [flag for flag in flags if flag not in omitted]
    before = remaining[0] if remaining else "resolved"
    if before == "resolved" and (
        fit["search"]["status"] != "profile_numerically_resolved"
        or any(
            fit["families"][family]["status"] != "available"
            for family in ("spatial", "exposure", "constant")
        )
    ):
        raise ValueError("a resolved pre-audit fit lacks successful search/family output")
    return {
        "primary_failure_class": chosen,
        "pre_audit_failure_class": before,
        "omitted_flags": [flag for flag in flags if flag in omitted],
        "performed_locations": fit["latent_audit"].get("audit_count"),
        "total_locations": fit["latent_audit"].get("locations"),
        "flagged_locations": len(fit["latent_audit"].get("flagged", [])),
    }


def unchanged_report_counts(fit: Json) -> Json:
    lr_points = eligibility_outcomes = view_count = h1_count = 0
    for name in qualification.VIEWS:
        try:
            view = qualification.view_of(fit, name)
        except (KeyError, ValueError):
            continue
        top = qualification.finite(view["free"]["criterion"])
        null = qualification.finite(view["null"]["criterion"])
        if abs(qualification.finite(view["lr1"]) - 2 * (top - null)) > 1e-8:
            raise ValueError("stored h=1 LR disagrees with the original report")
        nodes = set()
        for row in view["profile"]:
            x = qualification.finite(row["log_h"])
            if (
                x in nodes
                or abs(
                    qualification.finite(row["w"])
                    - 2 * (top - qualification.finite(row["criterion"]))
                )
                > 1e-8
            ):
                raise ValueError("stored profile W disagrees with the original report")
            nodes.add(x)
            if name.startswith("spatial."):
                # A retained spatial point stores two selected eligible endpoints.
                qualification.finite(row["criterion_positive"])
                qualification.finite(row["criterion_zero"])
                eligibility_outcomes += len(FAMILIES)
            else:
                if type(row["eligible"]) is not bool:
                    raise ValueError("invalid reduced-family eligibility")
                eligibility_outcomes += 1
        if name.startswith("spatial."):
            candidate_eligibility(view["free"])
            candidate_eligibility(view["null"])
            eligibility_outcomes += len(FAMILIES)
        else:
            if any(type(view[key]["eligible"]) is not bool for key in ("free", "null")):
                raise ValueError("invalid reduced-family eligibility")
            eligibility_outcomes += 1
        if 0.0 not in nodes:
            raise ValueError("saved LR lacks the retained h=1 endpoint")
        view_count += 1
        h1_count += 1
        lr_points += len(nodes)
    return {
        "views": view_count,
        "h1_lrs": h1_count,
        "retained_profile_lrs": lr_points,
        "retained_eligibilities_including_free": eligibility_outcomes,
        "lr_changes_above_threshold": 0,
        "eligibility_changes": 0,
    }


class AuditOmittedEvidence(qualification.Evidence):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.overrides: dict[str, str] = {}

    def load(self, reference: Json) -> Json:
        original = super().load(reference)
        if reference["sha256"] in self.overrides:
            return {**original, "failure_class": self.overrides[reference["sha256"]]}
        return original


def verdict(case: Json) -> str:
    return "passed" if case["passed"] else "failed" if case["complete"] else "indeterminate"


def known_failure(case: Json) -> bool:
    return any(
        check["status"] == "failed" or bool(check.get("failures"))
        for check in case["checks"].values()
    )


def required_roles(row: Json) -> list[str]:
    return (
        ["dense", "lean"]
        + (["independent_bank"] if row["independent_bank"] else [])
        + (["exhaustive"] if row["exhaustive_audit"] else [])
    )


def assess_variants(row: Json, entry: Json, original: Json, root: Path, source: str) -> Json:
    evidence = AuditOmittedEvidence(root)
    fits: Json = {}
    for role in required_roles(row):
        reference = entry.get(role)
        if reference is None:
            fits[role] = {"status": "missing_fit_receipt"}
            continue
        details: Json = {}
        fits[role] = details
        try:
            details["receipt_sha256"] = reference["sha256"]
            fit = evidence.load(reference)
            fit_identity(fit, source, role, entry["observation_sha256"])
        except EVIDENCE_ERRORS as error:
            details.update(status="invalid_fit_receipt", reason=str(error))
            continue
        details["status"] = "valid_fit_receipt"
        try:
            details["standard_prefix"] = load_prefix(fit, evidence.path(reference))
        except EVIDENCE_ERRORS as error:
            details["standard_prefix"] = {
                "status": "invalid_or_missing_prefix",
                "reason": str(error),
            }
        try:
            audit = without_latent_audit(fit)
            details["audit_omitted"] = {**audit, **unchanged_report_counts(fit)}
        except EVIDENCE_ERRORS as error:
            details["audit_omitted"] = {"status": "invalid_prefit_evidence", "reason": str(error)}
            continue
        if audit["primary_failure_class"] != audit["pre_audit_failure_class"]:
            evidence.overrides[reference["sha256"]] = audit["pre_audit_failure_class"]

    early_failures = [
        role
        for role, detail in fits.items()
        if detail.get("standard_prefix", {}).get("status") == "known_standard_failure"
    ]
    prefix_case = qualification.case_result(
        row,
        {
            "standard_prefix": qualification.outcome(
                ["retained pre-tight standard fit failure"] if early_failures else [],
                []
                if early_failures
                else [
                    "counterfactual reduced-family fits and exact common-anchor/gradient "
                    "evidence unavailable"
                ],
                roles=early_failures,
            )
        },
        {},
        {},
    )

    audit_case = (
        qualification.assess_case(row, entry, evidence, source) if evidence.overrides else original
    )
    checks = dict(audit_case["checks"])
    if "exhaustive" in fits:
        exhaustive = fits["exhaustive"].get("audit_omitted", {})
        if exhaustive.get("pre_audit_failure_class") == "resolved":
            checks["exhaustive"] = {
                **qualification.outcome([], []),
                "status": "omitted_numerical_mode_audit",
            }
    for role, detail in fits.items():
        audit = detail.get("audit_omitted", {})
        if "pre_audit_failure_class" not in audit:
            reason = audit.get("reason") or detail.get("reason") or detail["status"]
            checks[f"{role}/pre_audit"] = qualification.outcome([], [reason])
    audit_case = qualification.case_result(
        row, checks, audit_case["anchor_guard_evidence"], original["integration"]
    )
    return {
        "primary": original,
        "standard_prefix": prefix_case,
        "audit_omitted": audit_case,
        "fits": fits,
    }


def bounds(rows: list[Json], arms: tuple[str, ...]) -> Json:
    # For a fixed total failures the score increases with the sum of squared map counts.
    groups: dict[str, list[int]] = {}
    for row in rows:
        if row["stratum"] != "base" or row["arm"] not in arms:
            continue
        lower, upper = groups.setdefault(row["map"], [0, 0])
        groups[row["map"]] = [lower + known_failure(row), upper + (not row["passed"])]
    size = 6 * len(arms)
    limit = size // 4

    def score_extrema(cap: int) -> tuple[float | None, float | None]:
        totals = {0: (0, 0)}
        for lower, upper in groups.values():
            current: dict[int, tuple[int, int]] = {}
            for count in range(lower, min(upper, cap) + 1):
                for total, (q_min, q_max) in totals.items():
                    key = total + count
                    low, high = q_min + count**2, q_max + count**2
                    old_min, old_max = current.get(key, (low, high))
                    current[key] = min(old_min, low), max(old_max, high)
            totals = current
        scale = t.ppf(0.95, 8) / 3

        def score(total: int, squares: int) -> float:
            return float(
                (total / 9 + scale * math.sqrt(max(0.0, (squares - total**2 / 9) / 8))) / size
            )

        if not totals:
            return None, None
        return (
            min(score(s, q[0]) for s, q in totals.items()),
            max(score(s, q[1]) for s, q in totals.items()),
        )

    minimum, maximum = score_extrema(size)
    cap_minimum, _ = score_extrema(limit)
    return {
        "map_failure_count_ranges": dict(sorted(groups.items())),
        "empirical_score_range": [minimum, maximum],
        "base_pass_possible": cap_minimum is not None and cap_minimum <= 0.05,
        "base_pass_guaranteed": maximum is not None
        and maximum <= 0.05
        and all(upper <= limit for _, upper in groups.values()),
    }


def gate_summary(rows: list[Json]) -> Json:
    abc = qualification.finite_panel_gate(rows)
    ab = qualification.finite_panel_gate(rows, arms=("A", "B"))
    failed_base = [row for row in rows if row["stratum"] == "base" and not row["passed"]]
    failed_nonbase = [row for row in rows if row["stratum"] != "base" and not row["passed"]]
    ab_continuation = (
        bool(failed_base) and all(row["arm"] == "C" for row in failed_base) and ab["passed"]
    )
    complete = all(row["complete"] for row in rows)
    status = (
        "incomplete"
        if not complete
        else "repair_required"
        if failed_nonbase
        else "qualified_finite_panel"
        if abc["passed"]
        else "qualified_ab_only"
        if ab_continuation
        else "repair_required"
    )
    return {
        "numerical_status": status,
        "base_gate_if_complete": abc if complete else None,
        "ab_gate_if_complete": ab if complete else None,
        "abc_base_completion_bounds": bounds(rows, ("A", "B", "C")),
        "ab_base_completion_bounds": bounds(rows, ("A", "B")),
        "nonbase_known_failures": [
            row["dataset_id"] for row in failed_nonbase if known_failure(row)
        ],
        "base_known_ab_failures": [
            row["dataset_id"] for row in failed_base if row["arm"] != "C" and known_failure(row)
        ],
        "nonbase_indeterminate": [
            row["dataset_id"] for row in failed_nonbase if not row["complete"]
        ],
        "denominators": {
            stratum: dict(Counter(verdict(row) for row in rows if row["stratum"] == stratum))
            for stratum in qualification.COUNTS
        },
    }


def aggregate_points(fits: list[Json]) -> Json:
    prefix = [fit.get("standard_prefix", {"status": fit["status"]}) for fit in fits]
    audit = [fit.get("audit_omitted", {}) for fit in fits]
    summary: Json = {
        "required_fits": len(fits),
        "prefix_status_counts": dict(Counter(row["status"] for row in prefix)),
        "prefix_topology_fits": sum("spatial_topology" in row for row in prefix),
        "prefix_topology_vs_primary_fits": sum(
            "spatial_topology_vs_primary" in row for row in prefix
        ),
        "prefix_topology_fits_with_cutoff_check_failure": sum(
            any(
                not check["passed"] for check in row["spatial_topology_vs_primary"]["cutoff_checks"]
            )
            for row in prefix
            if "spatial_topology_vs_primary" in row
        ),
        "prefix": {},
        "audit_omitted": {
            "fits_with_numeric_report": sum(bool(row.get("views")) for row in audit),
            "fits_with_valid_pre_audit_class": sum(
                "pre_audit_failure_class" in row for row in audit
            ),
            "fit_class_changes": sum(
                row["primary_failure_class"] != row["pre_audit_failure_class"]
                for row in audit
                if "pre_audit_failure_class" in row
            ),
            **{
                key: sum(row.get(key, 0) for row in audit)
                for key in (
                    "views",
                    "h1_lrs",
                    "retained_profile_lrs",
                    "retained_eligibilities_including_free",
                    "lr_changes_above_threshold",
                    "eligibility_changes",
                )
            },
        },
    }
    for name in ("primary_tight", "post_replay_standard"):
        comparisons = [
            row["comparisons"][name] for row in prefix if name in row.get("comparisons", {})
        ]
        summary["prefix"][name] = {
            "compared_fits": len(comparisons),
            "fits_with_added_nodes": sum(bool(row["comparator_only_nodes"]) for row in comparisons),
            "fits_with_free_score_change": sum(
                row["prefix_free_criterion"] != row["comparator_free_criterion"]
                for row in comparisons
            ),
            "fits_with_lr_change_above_threshold": sum(
                bool(row["lr_changes_above_threshold"]) for row in comparisons
            ),
            "fits_with_eligibility_change": sum(
                bool(row["eligibility_changes"]) for row in comparisons
            ),
            "fits_with_h1_lr": sum(row["h1_delta_w"] is not None for row in comparisons),
            "fits_with_h1_lr_change_above_threshold": sum(
                abs(row["h1_delta_w"]) > LR_THRESHOLD
                for row in comparisons
                if row["h1_delta_w"] is not None
            ),
            "max_abs_delta_w": max(
                (
                    row["max_abs_delta_w"]
                    for row in comparisons
                    if row["max_abs_delta_w"] is not None
                ),
                default=None,
            ),
            "eligibility_changes": sum(len(row["eligibility_changes"]) for row in comparisons),
            "lr_changes_above_threshold": sum(
                len(row["lr_changes_above_threshold"]) for row in comparisons
            ),
            **{
                key: sum(row[key] for row in comparisons)
                for key in (
                    "prefix_nodes",
                    "comparator_nodes",
                    "shared_exact_nodes",
                    "prefix_only_nodes",
                    "comparator_only_nodes",
                    "eligibility_comparisons",
                )
            },
        }
    return summary


def read_fresh(panel_path: Path, index_path: Path, primary_path: Path) -> Json:
    panel, index, primary = map(
        lambda path: json.loads(path.read_text()), (panel_path, index_path, primary_path)
    )
    hashes = {
        "panel_sha256": qualification.digest(panel_path),
        "index_sha256": qualification.digest(index_path),
        "primary_summary_sha256": qualification.digest(primary_path),
    }
    if (
        panel.get("schema") != "paper1-fresh-qualification-panel-v1"
        or primary["schema"] != "sprint2-qualification-summary-v1"
        or index["schema"] != "sprint2-qualification-index-v1"
        or index["source_commit"] != primary["source_commit"]
        or index["panel_sha256"] != hashes["panel_sha256"]
        or any(primary[key] != hashes[key] for key in ("panel_sha256", "index_sha256"))
    ):
        raise ValueError("primary summary, panel and final index identities disagree")
    rows = panel["datasets"]
    ids = {row["dataset_id"] for row in rows}
    primary_by_id = {row["dataset_id"]: row for row in primary["cases"]}
    if (
        len(rows) != len(ids)
        or len(ids) != 207
        or len(primary["cases"]) != len(ids)
        or ids != primary_by_id.keys()
        or set(index["cases"]) - ids
        or Counter(row["stratum"] for row in rows) != Counter(qualification.COUNTS)
    ):
        raise ValueError("primary summary does not cover the registered 207 dataset addresses")
    cases = [
        assess_variants(
            row,
            index["cases"].get(row["dataset_id"], {}),
            primary_by_id[row["dataset_id"]],
            index_path.parent,
            index["source_commit"],
        )
        for row in rows
    ]
    for case in cases:
        case["verdicts"] = {
            name: verdict(case[name]) for name in ("primary", "standard_prefix", "audit_omitted")
        }
    transitions = {}
    for variant in ("standard_prefix", "audit_omitted"):
        counts = Counter((case["verdicts"]["primary"], case["verdicts"][variant]) for case in cases)
        paired = [
            [
                fit.get("standard_prefix", {}).get("comparisons", {}).get("primary_tight", {})
                if variant == "standard_prefix"
                else fit.get("audit_omitted", {})
                for fit in case["fits"].values()
            ]
            for case in cases
        ]
        key = "shared_exact_nodes" if variant == "standard_prefix" else "retained_profile_lrs"
        transitions[variant] = {
            "paired_known_verdicts": sum(
                n for (a, b), n in counts.items() if a != "indeterminate" and b != "indeterminate"
            ),
            "paired_known_verdict_changes": counts["passed", "failed"] + counts["failed", "passed"],
            "transition_counts": {f"{a}_to_{b}": n for (a, b), n in sorted(counts.items())},
            "datasets_with_any_paired_profile_lr": sum(
                any(row.get(key) for row in case) for case in paired
            ),
            "datasets_with_all_roles_paired_profile_lr": sum(
                all(row.get(key) for row in case) for case in paired
            ),
            "datasets_with_profile_lr_change_above_threshold": sum(
                any(row.get("lr_changes_above_threshold") for row in case) for case in paired
            ),
            "datasets_with_eligibility_change": sum(
                any(row.get("eligibility_changes") for row in case) for case in paired
            ),
            "datasets_with_h1_lr_change_above_threshold": sum(
                any(
                    abs(row["h1_delta_w"]) > LR_THRESHOLD
                    for row in case
                    if row.get("h1_delta_w") is not None
                )
                for case in paired
            )
            if variant == "standard_prefix"
            else 0,
        }
    primary_gate = gate_summary([case["primary"] for case in cases])
    if primary_gate["numerical_status"] != primary["numerical_status"]:
        raise ValueError("verified primary cases disagree with the primary numerical status")
    return {
        **hashes,
        "scope": "registered_207_dataset_panel",
        "source_commit": index["source_commit"],
        "primary_packet_status": primary["status"],
        "primary": primary_gate,
        "standard_prefix": gate_summary([case["standard_prefix"] for case in cases]),
        "audit_omitted": gate_summary([case["audit_omitted"] for case in cases]),
        "transitions": transitions,
        "point_summary": aggregate_points([fit for case in cases for fit in case["fits"].values()]),
        "cases": cases,
    }


def development(raw: Path) -> Json:
    summary = json.loads(verified_bytes([raw / "replay-summary.json"], ACCEPTANCE_SUMMARY))
    if summary["source_commit"] != ACCEPTANCE_SOURCE:
        raise ValueError("unexpected development candidate")
    fits = {}
    for file in sorted((raw / "fit-results").glob("*/attempt-*/fit/receipt.json")):
        task = file.parents[2].name
        if task in fits:
            raise ValueError(f"more than one terminal development fit: {task}")
        fits[task] = file
    output = {}
    for row in summary["fit_replays"]:
        task = "repair-" + row["original_task_id"]
        path = fits[task]
        fit = json.loads(verified_bytes([path], row["receipt_sha256"]))
        output[task] = {
            "status": "valid_fit_receipt",
            "receipt_sha256": row["receipt_sha256"],
            "standard_prefix": load_prefix(fit, path),
            "audit_omitted": {**without_latent_audit(fit), **unchanged_report_counts(fit)},
        }
    if len(output) != 51 or output.keys() != fits.keys():
        raise ValueError("development inventory differs from the 51 frozen acceptance tasks")
    return {
        "scope": "selected_development_acceptance_fits",
        "source_commit": ACCEPTANCE_SOURCE,
        "replay_summary_sha256": ACCEPTANCE_SUMMARY,
        "point_summary": aggregate_points(list(output.values())),
        "fits": output,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-raw", type=Path)
    parser.add_argument("--panel", type=Path)
    parser.add_argument("--index", type=Path)
    parser.add_argument("--primary-summary", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.development_raw is not None and not any((args.panel, args.index, args.primary_summary)):
        result = development(args.development_raw)
    elif args.development_raw is None and all((args.panel, args.index, args.primary_summary)):
        result = read_fresh(args.panel, args.index, args.primary_summary)
    else:
        parser.error("supply --development-raw or all of --panel, --index and --primary-summary")
    result.update(
        schema="sprint2-safeguard-yield-v1",
        lr_strict_threshold=LR_THRESHOLD,
        changes_primary_gate=False,
        training_authorised=False,
    )
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    temporary = args.output.with_name(f".{args.output.name}.{os.getpid()}.tmp")
    with temporary.open("x") as stream:
        stream.write(payload)
    temporary.replace(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
