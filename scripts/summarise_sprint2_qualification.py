"""Reduce the frozen 207-case Sprint 2 qualification panel; never launch fits.

Index: {schema: sprint2-qualification-index-v1, panel_sha256, source_commit,
cases: {dataset_id: {observation_sha256, dense, lean, gradient, [independent_bank,
bank_identity], [exhaustive], anchors: {dense_lean, [bank]}}}}. Every evidence
reference is {path, sha256}; relative paths resolve beside the index. Missing,
malformed or hash-mismatched required evidence is indeterminate, never success.

Fit receipts retain fit-dataset-v1. Compare spatial.standard, spatial.tight,
exposure and constant. Recompute W from each receipt's own free criterion. Exact
shared log-h nodes must include 0 and log(30) and number at least five. When
nodes differ, the common-anchor sidecar must cover their exact union, including
free locations, all roots and component endpoints; no interpolation is allowed.
An anchor sidecar has schema sprint2-common-anchors-v1, status=available,
left_receipt_sha256,
right_receipt_sha256 and views: {view: {rows: [{log_h, left: {criterion,
nuisance_contacts}, right: {...}}]}}. Contacts are lists of [family, contact]
pairs after the existing tie rule. Anchor evaluations must retain eligible=true.
Original nodes cannot be silently overwritten by sidecar values.

All eight cutoff sets must be available, with matching class, component count,
domain flags and singletons. Sorted roots/component endpoints differ by at most
.005 log-h for dense/lean, .05 for independent banks; W limits are .01/.10.
Free, null, root and inside-set nuisance contacts must agree after the tie rule.
There is no tangency waiver. Unavailable sets and topology differences do not
pass. Sidecar points above the recorded maximum by >1e-4 invalidate closure.

Gradient sidecar: schema sprint2-free-gradient-v1, status=available, dense_receipt_sha256,
lean_receipt_sha256, checks covering each search/regime/step_scale combination
(dense/lean, standard/tight, 1e-4/3e-5). Each row has family, coordinates,
parameters (mapping), analytic, finite_difference, steps, stencils, reoptimized.
Check the selected free branch, with raw derivatives, not projected gradients.
Steps are scale*max(1,abs(theta)); central differences inside the domain and
inward second-order differences at a boundary. Both steps must satisfy
abs(error)<=1e-5+1e-4*max(abs(analytic),abs(finite_difference)).

Integration evidence: selected rows require integration: {path,sha256} referencing
sprint2-integration-screen-v1 directly. It binds fit_receipt_sha256 and the
verified source/input hashes, maximum_draws=262144, selected anchors and draw
history. A free-only screen is no_root_contrasts, never an LR-screen pass.
Indeterminate or a recorded numerical preparation failure is a completed
descriptive outcome; a missing/unrun screen prevents packet completion, not a
scientific pass. Scientifically failed fits need explicit unavailable_scientific_fit.

Bank sidecar: schema sprint2-bank-identity-v1, primary_receipt_sha256,
independent_receipt_sha256, primary_manifest and independent_manifest references.
The actual manifests/payloads are checked by generate_history's verifier;
replicates must be 0/1, both K=131072. Exhaustive evidence is an actual fit
receipt with every retained positive-sigma location accounted for, not a boolean
pass assertion. Any skipped production location's score gain >5 fails the audit.

The base gate retains mean(map failure fraction)+t(.95,8)*sd/3 <= .05 and
max(map fraction)<=.25 solely as a finite-panel acceptance score, with no
population confidence interpretation. A/B continuation is limited to C-only
base failures. Nonbase failures require diagnosis before training; missing
required evidence prevents completion. This reducer never authorises training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import t  # type: ignore[import-untyped]

CUTOFFS = (2.71, 3.84, 5.02, 6.63, 7.88, 9.55, 12.0, 15.0)
VIEWS = ("spatial.standard", "spatial.tight", "exposure", "constant")
LOG_MAX = math.log(30.0)
COUNTS = {"base": 162, "boundary": 18, "enriched": 18, "trend": 9}
Json = dict[str, Any]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(value: Any) -> float:
    if isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError("nonfinite or boolean numerical evidence")
    return float(value)


def view_of(receipt: Json, view: str) -> Json:
    family, _, regime = view.partition(".")
    result = receipt["families"][family]
    if result["status"] != "available":
        raise ValueError(f"{family} unavailable")
    selected: Json = result[regime] if regime else result
    return selected


def contacts(row: Json, view: str) -> frozenset[tuple[str, str]]:
    if view.startswith("spatial"):
        mapping = row["nuisance_contacts"]
        if not isinstance(mapping, dict):
            raise ValueError("missing spatial contact mapping")
        return frozenset(
            (family, contact)
            for family, values in mapping.items()
            for contact in values
            if not (row["tied"] and family == "positive_sigma" and contact == "log_sigma:lower")
        )
    return frozenset((view, contact) for contact in row["nuisance_bound_contacts"])


def levels_of(view: Json) -> dict[float, Json]:
    rows = view["level_sets"]
    levels = {finite(row["cutoff"]): row for row in rows}
    if len(rows) != len(CUTOFFS) or set(levels) != set(CUTOFFS):
        raise ValueError("cutoff grid missing, duplicated or changed")
    return levels


def profile_of(view: Json) -> dict[float, Json]:
    rows = view["profile"]
    points = {finite(row["log_h"]): row for row in rows}
    if len(points) != len(rows) or not {0.0, LOG_MAX} <= points.keys():
        raise ValueError("duplicate profile nodes or missing domain endpoints")
    maximum = finite(view["free"]["criterion"])
    for row in rows:
        value = finite(row["criterion"])
        if abs(finite(row["w"]) - 2 * (maximum - value)) > 1e-8:
            raise ValueError("stored W disagrees with own-free normalisation")
        if value > maximum + 1e-4:
            raise ValueError("profile exceeds recorded free maximum")
        if "eligible" in row and row["eligible"] is not True:
            raise ValueError("profile contains ineligible candidate")
    return points


def required_nodes(view: Json, points: dict[float, Json]) -> set[float]:
    nodes = set(points) | {math.log(finite(view["free"]["h"]))}
    for level in levels_of(view).values():
        nodes.update(finite(x) for x in level["roots_log_h"])
        for component in level["components"]:
            nodes.update(finite(component[key]) for key in ("lower_log_h", "upper_log_h"))
    return nodes


def anchor_contacts(row: Json) -> frozenset[tuple[str, str]]:
    values = row["nuisance_contacts"]
    if not isinstance(values, list) or any(
        not isinstance(pair, list) or len(pair) != 2 for pair in values
    ):
        raise ValueError("anchor contacts must be explicit family/contact pairs")
    return frozenset((str(a), str(b)) for a, b in values)


def comparison_nodes(
    left: Json, right: Json, view: str, sidecar: Json | None
) -> tuple[list[float], dict[float, Json], dict[float, Json], int]:
    lp, rp = profile_of(left), profile_of(right)
    shared = lp.keys() & rp.keys()
    if len(shared) < 5 or not {0.0, LOG_MAX} <= shared:
        raise ValueError("fewer than five exact shared nodes or shared endpoints absent")
    wanted = required_nodes(left, lp) | required_nodes(right, rp)
    output: list[dict[float, Json]] = []
    if sidecar is None:
        if set(lp) != set(rp) or not wanted <= lp.keys():
            raise ValueError("union common-anchor evidence required")
        for points in (lp, rp):
            output.append(
                {
                    x: {"criterion": finite(row["criterion"]), "contacts": contacts(row, view)}
                    for x, row in points.items()
                }
            )
    else:
        rows = sidecar["views"][view]["rows"]
        by_x = {finite(row["log_h"]): row for row in rows}
        if len(by_x) != len(rows) or set(by_x) != wanted:
            raise ValueError("common anchors must be the exact union, with no duplicates")
        for label, original, full in (("left", lp, left), ("right", rp, right)):
            values: dict[float, Json] = {}
            for x, row in by_x.items():
                point = row[label]
                if point["eligible"] is not True:
                    raise ValueError("ineligible common-anchor evaluation")
                value = finite(point["criterion"])
                cs = anchor_contacts(point)
                if value > finite(full["free"]["criterion"]) + 1e-4:
                    raise ValueError("common anchor exceeds recorded maximum")
                if x in original and (
                    abs(value - finite(original[x]["criterion"])) > 1e-8
                    or cs != contacts(original[x], view)
                ):
                    raise ValueError("common anchor overwrites original profile evidence")
                values[x] = {"criterion": value, "contacts": cs}
            output.append(values)
    return sorted(wanted), output[0], output[1], len(shared)


def compare_receipts(
    left: Json, right: Json, *, bank: bool = False, anchors: Json | None = None
) -> Json:
    reasons: list[str] = []
    unavailable: list[str] = []
    metrics: Json = {}
    if anchors is not None:
        if anchors.get("status") == "scientific_failure":
            return outcome(["common-anchor audit reported a scientific failure"], [], audit=anchors)
        if anchors.get("status") != "available":
            return outcome([], ["common-anchor audit is unavailable"], audit=anchors)
    w_tolerance, root_tolerance = (0.10, 0.05) if bank else (0.01, 0.005)
    for label, receipt in (("left", left), ("right", right)):
        if receipt.get("schema") != "fit-dataset-v1":
            unavailable.append(f"{label}: missing fit receipt schema")
        if receipt.get("failure_class") != "resolved":
            reasons.append(f"{label}: failure class {receipt.get('failure_class')}")
        if tuple(receipt.get("cutoffs", ())) != CUTOFFS:
            unavailable.append(f"{label}: changed cutoff grid")
        if receipt.get("tight_replay") != "always_on_inside_PanelSearch.run":
            unavailable.append(f"{label}: tight replay not evidenced")
    if anchors is not None and anchors.get("schema") != "sprint2-common-anchors-v1":
        unavailable.append("invalid common-anchor schema")
        anchors = None
    for name in VIEWS:
        try:
            lv, rv = view_of(left, name), view_of(right, name)
            xs, lp, rp, shared = comparison_nodes(lv, rv, name, anchors)
            lf, rf = finite(lv["free"]["criterion"]), finite(rv["free"]["criterion"])
            lw = {x: 2 * (lf - lp[x]["criterion"]) for x in xs}
            rw = {x: 2 * (rf - rp[x]["criterion"]) for x in xs}
            delta = max(abs(lw[x] - rw[x]) for x in xs)
            metrics[name] = {
                "shared_nodes": shared,
                "union_nodes": len(xs),
                "max_abs_delta_w": delta,
            }
            if delta > w_tolerance:
                reasons.append(f"{name}: W difference {delta} exceeds {w_tolerance}")
            for location in ("free", "null"):
                if contacts(lv[location], name) != contacts(rv[location], name):
                    reasons.append(f"{name}: {location} contacts differ")
            ll, rl = levels_of(lv), levels_of(rv)
            for cutoff in CUTOFFS:
                a, b = ll[cutoff], rl[cutoff]
                prefix = f"{name}: cutoff {cutoff:g}"
                if a["status"] != "available" or b["status"] != "available":
                    reasons.append(f"{prefix}: unavailable set")
                    continue
                for key in ("set_class", "touches_h1", "touches_h30", "empty"):
                    if key not in a or key not in b:
                        raise ValueError(f"missing {key} set evidence")
                    if a[key] != b[key]:
                        reasons.append(f"{prefix}: {key} differs")
                ac = sorted(a["components"], key=lambda c: c["lower_log_h"])
                bc = sorted(b["components"], key=lambda c: c["lower_log_h"])
                ar, br = (
                    sorted(map(finite, a["roots_log_h"])),
                    sorted(map(finite, b["roots_log_h"])),
                )
                if len(ac) != len(bc) or len(ar) != len(br):
                    reasons.append(f"{prefix}: topology differs (no tangency waiver)")
                    continue
                for ca, cb in zip(ac, bc, strict=True):
                    for key in ("lower_domain_contact", "upper_domain_contact", "singleton"):
                        if ca[key] != cb[key]:
                            reasons.append(f"{prefix}: component {key} differs")
                    for key in ("lower_log_h", "upper_log_h"):
                        if abs(finite(ca[key]) - finite(cb[key])) > root_tolerance:
                            reasons.append(f"{prefix}: component {key} moved")
                for aroot, broot in zip(ar, br, strict=True):
                    if abs(aroot - broot) > root_tolerance:
                        reasons.append(f"{prefix}: root moved")
                    if lp[aroot]["contacts"] != rp[broot]["contacts"]:
                        reasons.append(f"{prefix}: root contacts differ")
                lc = frozenset(c for x in xs if lw[x] <= cutoff for c in lp[x]["contacts"])
                rc = frozenset(c for x in xs if rw[x] <= cutoff for c in rp[x]["contacts"])
                if lc != rc:
                    reasons.append(f"{prefix}: inside-set contacts differ")
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            unavailable.append(f"{name}: {error}")
    return outcome(reasons, unavailable, metrics=metrics)


def outcome(reasons: list[str], unavailable: list[str], **extra: Any) -> Json:
    return {
        "status": "indeterminate" if unavailable else "failed" if reasons else "passed",
        "passed": not reasons and not unavailable,
        "failures": reasons,
        "unavailable": unavailable,
        **extra,
    }


def gradient_check(sidecar: Json, dense: Json, lean: Json) -> Json:
    from latent_landscapes.spatial_profile import SpatialProfileCriterion

    failures: list[str] = []
    unavailable: list[str] = []
    if sidecar.get("status") == "scientific_failure":
        return outcome(["gradient audit reported a scientific failure"], [], audit=sidecar)
    if sidecar.get("status") != "available":
        return outcome([], ["gradient audit is unavailable"], audit=sidecar)
    try:
        if sidecar["schema"] != "sprint2-free-gradient-v1":
            raise ValueError("wrong gradient schema")
        checks = sidecar["checks"]
        keys = [(row["search"], row["regime"], finite(row["step_scale"])) for row in checks]
        expected = {
            (s, r, d)
            for s in ("dense", "lean")
            for r in ("standard", "tight")
            for d in (1e-4, 3e-5)
        }
        if len(keys) != len(expected) or set(keys) != expected:
            raise ValueError("gradient evidence must cover both searches/regimes and step sizes")
        for row in checks:
            label = f"{row['search']}/{row['regime']}/{row['step_scale']}"
            free = view_of(dense if row["search"] == "dense" else lean, f"spatial.{row['regime']}")[
                "free"
            ]
            family = free["selected_family"]
            names = [
                "alpha",
                "beta",
                *(["log_sigma"] if family == "positive_sigma" else []),
                "log_h",
                "detection_sd",
            ]
            theta = free[family]["parameters"]
            if (
                row["family"] != family
                or row["coordinates"] != names
                or row["reoptimized"] is not True
            ):
                raise ValueError(f"{label}: wrong branch/coordinates or no reoptimisation")
            if row["parameters"] != theta:
                raise ValueError(f"{label}: wrong parameter point")
            arrays = [row[k] for k in ("analytic", "finite_difference", "steps", "stencils")]
            if any(len(v) != len(names) for v in arrays):
                raise ValueError(f"{label}: missing gradient components")
            bounds = SpatialProfileCriterion._bounds(None, family == "sigma_zero")
            for i, (name, (lower, upper)) in enumerate(zip(names, bounds, strict=True)):
                value = finite(theta[name])
                step = finite(row["steps"][i])
                expected_step = finite(row["step_scale"]) * max(1.0, abs(value))
                if not math.isclose(step, expected_step, rel_tol=1e-12, abs_tol=1e-15):
                    raise ValueError(f"{label}: unexpected finite-difference step")
                stencil = (
                    "forward_second_order"
                    if value - step < lower
                    else "backward_second_order"
                    if value + step > upper
                    else "central"
                )
                if row["stencils"][i] != stencil:
                    raise ValueError(f"{label}: invalid boundary stencil")
                if not lower <= value <= upper:
                    raise ValueError(f"{label}: parameter outside bounds")
                a, b = finite(row["analytic"][i]), finite(row["finite_difference"][i])
                if abs(a - b) > 1e-5 + 1e-4 * max(abs(a), abs(b)):
                    failures.append(f"{label}: {name} raw derivative disagrees")
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        unavailable.append(str(error))
    return outcome(failures, unavailable)


def exhaustive_check(receipt: Json) -> Json:
    failures: list[str] = []
    unavailable: list[str] = []
    try:
        audit = receipt["latent_audit"]
        if audit["exhaustive"] is not True or receipt["failure_class"] != "resolved":
            failures.append("exhaustive fit/audit is not resolved")
        rows = audit["rows"]
        if audit["multimodal_latent"] is True:
            failures.append("exhaustive audit reports multimodality")
        if audit["audit_count"] != sum(row["performed"] is True for row in rows):
            raise ValueError("exhaustive performed-count metadata is inconsistent")
        expected = set()
        for regime in ("standard", "tight"):
            view = view_of(receipt, f"spatial.{regime}")
            tight = regime == "tight"
            expected.add((tight, "free", math.log(finite(view["free"]["positive_sigma"]["h"]))))
            expected.update((tight, "profile", finite(row["log_h"])) for row in view["profile"])
        actual = [
            (row["tight"], "free" if row["kind"] == "free" else "profile", finite(row["log_h"]))
            for row in rows
        ]
        if (
            len(actual) != len(expected)
            or set(actual) != expected
            or audit["locations"] != len(rows)
        ):
            raise ValueError("exhaustive audit does not cover all retained locations")
        for row in rows:
            beyond = row["kind"] != "free" and finite(row["envelope_lr"]) > 25.0
            if row["beyond_lr_limit"] != beyond:
                raise ValueError("exhaustive production-skip metadata disagrees with LR")
            if finite(row["sigma"]) > 1e-3 and row["performed"] is not True:
                raise ValueError("exhaustive audit skips an eligible sigma location")
            if row["multimodal_latent"] is True:
                failures.append("exhaustive audit found a higher joint mode")
            if row["performed"]:
                finite(row["max_joint_gain"])
                gain = finite(row["max_criterion_gain"])
                if beyond and gain > 5.0:
                    failures.append("production-skipped location has score gain above five")
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        unavailable.append(str(error))
    return outcome(failures, unavailable)


class Evidence:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.cache: dict[str, Json] = {}
        self.verified_banks: set[tuple[str, str]] = set()
        self.guard_cache: dict[str, Json] = {}

    def path(self, reference: Json) -> Path:
        path = Path(reference["path"])
        return path if path.is_absolute() else self.root / path

    def load(self, reference: Json) -> Json:
        path = self.path(reference)
        checksum = reference["sha256"]
        if digest(path) != checksum:
            raise ValueError(f"evidence checksum mismatch: {path}")
        if checksum not in self.cache:
            self.cache[checksum] = json.loads(path.read_text())
        return self.cache[checksum]

    def anchor_guards(self, fit: Json) -> Json:
        try:
            search = fit["search"]
            child_ref = {"path": search["receipt"], "sha256": search["receipt_sha256"]}
            child = self.load(child_ref)
            reference = child["evaluation_stream"]
            path = self.path(reference)
            if digest(path) != reference["sha256"]:
                raise ValueError("evaluation-stream checksum mismatch")
            if reference["sha256"] in self.guard_cache:
                return self.guard_cache[reference["sha256"]]
            counts = {
                "unresolved_fit_events": 0,
                "no_eligible_family_events": 0,
                "high_sigma_anchor_offending_candidates": 0,
                "other_offending_candidates": 0,
            }
            sources: Counter[str] = Counter()
            with path.open() as handle:
                for line in handle:
                    event = json.loads(line)
                    if event["kind"] != "unresolved_fit":
                        continue
                    counts["unresolved_fit_events"] += 1
                    candidates = event["candidates"]
                    maxima = {}
                    for family in ("positive_sigma", "sigma_zero"):
                        eligible = [
                            float(c["criterion"])
                            for c in candidates
                            if c["family"] == family
                            and c["eligible"]
                            and c["criterion"] is not None
                            and math.isfinite(float(c["criterion"]))
                        ]
                        if eligible:
                            maxima[family] = max(eligible)
                    if len(maxima) < 2:
                        counts["no_eligible_family_events"] += 1
                    for candidate in candidates:
                        value = candidate["criterion"]
                        family = candidate["family"]
                        if (
                            candidate["eligible"]
                            or family not in maxima
                            or value is None
                            or not math.isfinite(float(value))
                            or float(value) <= maxima[family] + 1e-4
                        ):
                            continue
                        source = candidate["source"]
                        sources[source] += 1
                        label = (
                            "high_sigma_anchor_offending_candidates"
                            if "high_sigma_anchor" in source
                            else "other_offending_candidates"
                        )
                        counts[label] += 1
            result = {
                "status": "available",
                **counts,
                "candidate_sources": dict(sources),
                "evaluation_stream_sha256": reference["sha256"],
            }
            self.guard_cache[reference["sha256"]] = result
            return result
        except (KeyError, TypeError, ValueError, OSError) as error:
            return {"status": "unavailable", "reason": str(error)}

    def banks(self, sidecar: Json, primary: Json, independent: Json) -> Json:
        from generate_history import verify_independent_banks

        failures: list[str] = []
        unavailable: list[str] = []
        try:
            if sidecar["schema"] != "sprint2-bank-identity-v1":
                raise ValueError("wrong bank identity schema")
            left_ref, right_ref = sidecar["primary_manifest"], sidecar["independent_manifest"]
            left, right = self.load(left_ref), self.load(right_ref)
            if (left["bank_replicate"], right["bank_replicate"]) != (0, 1):
                raise ValueError("frozen bank replicate IDs must be 0/1")
            if left["bank_size"] != 131072 or right["bank_size"] != 131072:
                raise ValueError("frozen bank sizes must both be 131072")
            for manifest, fit in ((left, primary), (right, independent)):
                with np.load(Path(manifest["compressed"]), allow_pickle=False) as compressed:
                    if int(compressed["series_order"]) != 192:
                        raise ValueError("frozen compression order must be 192")
                values = set(fit["input_sha256"].values())
                if not {manifest["raw_sha256"], manifest["compressed_sha256"]} <= values:
                    raise ValueError("fit receipt does not use the declared bank")
            key = (left_ref["sha256"], right_ref["sha256"])
            if key not in self.verified_banks:
                verify_independent_banks(self.path(left_ref), self.path(right_ref))
                self.verified_banks.add(key)
        except (KeyError, TypeError, ValueError, OSError) as error:
            unavailable.append(str(error))
        return outcome(failures, unavailable)


def integration_check(sidecar: Json, fit: Json, fit_hash: str) -> Json:
    try:
        if sidecar["schema"] != "sprint2-integration-screen-v1":
            raise ValueError("wrong integration evidence schema")
        bind(sidecar, fit_receipt_sha256=fit_hash)
        if sidecar["maximum_draws"] != 262144 or sidecar["descriptive_only"] is not True:
            raise ValueError("integration cap/scope differs from the specification")
        status = sidecar["status"]
        if status == "unavailable_scientific_fit":
            if fit["failure_class"] not in SCIENTIFIC_FAILURES or not sidecar["reason"]:
                raise ValueError("unavailable integration lacks a scientific-failure parent")
        else:
            identities = sidecar["source_input_sha256"]
            if not all(
                identities.get(path) == value for path, value in fit["input_sha256"].items()
            ):
                raise ValueError("integration input/source bindings differ from the fit")
            if fit_hash not in identities.values():
                raise ValueError("integration source bindings omit the fit receipt")
            if status == "unavailable":
                if not sidecar["reason"]:
                    raise ValueError("unavailable integration has no failure reason")
            elif status in (
                "pointwise_screen_passed",
                "repair_required",
                "indeterminate",
                "no_root_contrasts",
            ):
                history = sidecar["history"]
                if not history:
                    raise ValueError("screen outcome lacks attempted integration evidence")
                draws = [int(level["draws_per_point_per_stream"]) for level in history]
                if any(n <= 0 or n > 262144 for n in draws) or draws != sorted(set(draws)):
                    raise ValueError("invalid capped integration draw history")
                if history[-1]["status"] != status:
                    raise ValueError("screen outcome differs from final history level")
                if not sidecar["selected_anchors"]:
                    raise ValueError("screen outcome has no selected anchors")
                roots = levels_of(view_of(fit, "spatial.tight"))[3.84]["roots_log_h"]
                if status == "no_root_contrasts":
                    if roots or [anchor["key"] for anchor in sidecar["selected_anchors"]] != [
                        "free"
                    ]:
                        raise ValueError(
                            "no-root screen must have an empty root set and only the free anchor"
                        )
                elif status == "pointwise_screen_passed" and not roots:
                    raise ValueError("free-only integration cannot pass an LR contrast screen")
            else:
                raise ValueError("unknown integration completion status")
        return {
            "complete": True,
            "status": status,
            "descriptive_only": True,
            "lr_screen_passed": status == "pointwise_screen_passed",
        }
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        return {"complete": False, "status": "missing_or_invalid", "reason": str(error)}


SCIENTIFIC_FAILURES = {
    "numerical_error",
    "family_fit_failed",
    "search_unresolved",
    "multimodal_latent",
}


def bind(sidecar: Json, **hashes: str) -> None:
    if any(sidecar[key] != value for key, value in hashes.items()):
        raise ValueError("sidecar is bound to different fit receipts")


def assess_case(row: Json, entry: Json, evidence: Evidence, source_commit: str) -> Json:
    checks: Json = {}
    receipts: dict[str, Json] = {}
    needed = (
        ["dense", "lean"]
        + (["independent_bank"] if row["independent_bank"] else [])
        + (["exhaustive"] if row["exhaustive_audit"] else [])
    )
    for key in needed:
        try:
            fit = evidence.load(entry[key])
            if fit["source"]["commit"] != source_commit or fit["source"]["working_tree_changes"]:
                raise ValueError("fit source differs from frozen clean commit")
            obs = [
                value
                for name, value in fit["input_sha256"].items()
                if Path(name).name == "observations.npz"
            ]
            if obs != [entry["observation_sha256"]]:
                raise ValueError("fit observations do not match indexed dataset")
            wanted_mode = "dense" if key == "dense" else "lean"
            if fit["search_mode"] != wanted_mode:
                raise ValueError("wrong search mode")
            if fit["schema"] != "fit-dataset-v1":
                raise ValueError("wrong fit receipt schema")
            classification = fit["failure_class"]
            receipts[key] = fit
            if classification in SCIENTIFIC_FAILURES:
                checks[key] = outcome([f"terminal scientific failure: {classification}"], [])
            elif classification != "resolved":
                checks[key] = outcome([], [f"nonterminal or unknown fit class: {classification}"])
        except (KeyError, TypeError, ValueError, OSError) as error:
            checks[key] = outcome([], [str(error)])
    guards = {key: evidence.anchor_guards(fit) for key, fit in receipts.items()}
    integration: Json = {"complete": True, "status": "not_selected", "descriptive_only": True}
    if row.get("integration_screen", False):
        try:
            integration = integration_check(
                evidence.load(entry["integration"]), receipts["lean"], entry["lean"]["sha256"]
            )
        except (KeyError, TypeError, ValueError, OSError) as error:
            integration = {"complete": False, "status": "missing_or_invalid", "reason": str(error)}
    scientific_failure = any(
        fit["failure_class"] in SCIENTIFIC_FAILURES for fit in receipts.values()
    )
    if scientific_failure:
        checks["dependent_audits"] = {
            "status": "not_applicable_due_to_scientific_failure",
            "passed": True,
            "reason": "a required terminal fit already fails this dataset",
        }
        return case_result(row, checks, guards, integration)
    for label, lkey, rkey in (
        ("dense_lean", "dense", "lean"),
        ("bank", "lean", "independent_bank"),
    ):
        if label == "bank" and not row["independent_bank"]:
            continue
        if lkey not in receipts or rkey not in receipts:
            checks[label] = outcome([], ["comparison fit receipt missing"])
            continue
        try:
            reference = entry.get("anchors", {}).get(label)
            anchors = evidence.load(reference) if reference else None
            if anchors is not None:
                bind(
                    anchors,
                    left_receipt_sha256=entry[lkey]["sha256"],
                    right_receipt_sha256=entry[rkey]["sha256"],
                )
            checks[label] = compare_receipts(
                receipts[lkey], receipts[rkey], bank=label == "bank", anchors=anchors
            )
        except (KeyError, TypeError, ValueError, OSError) as error:
            checks[label] = outcome([], [str(error)])
    for label in ("gradient", "bank_identity", "exhaustive"):
        if label == "bank_identity" and not row["independent_bank"]:
            continue
        if label == "exhaustive" and not row["exhaustive_audit"]:
            continue
        try:
            sidecar = (
                receipts["exhaustive"] if label == "exhaustive" else evidence.load(entry[label])
            )
            if label == "gradient":
                bind(
                    sidecar,
                    dense_receipt_sha256=entry["dense"]["sha256"],
                    lean_receipt_sha256=entry["lean"]["sha256"],
                )
                checks[label] = gradient_check(sidecar, receipts["dense"], receipts["lean"])
            elif label == "bank_identity":
                bind(
                    sidecar,
                    primary_receipt_sha256=entry["lean"]["sha256"],
                    independent_receipt_sha256=entry["independent_bank"]["sha256"],
                )
                checks[label] = evidence.banks(
                    sidecar, receipts["lean"], receipts["independent_bank"]
                )
            else:
                checks[label] = exhaustive_check(sidecar)
        except (KeyError, TypeError, ValueError, OSError) as error:
            checks[label] = outcome([], [str(error)])
    return case_result(row, checks, guards, integration)


def case_result(row: Json, checks: Json, guards: Json, integration: Json) -> Json:
    return {
        **{key: row[key] for key in ("dataset_id", "map", "archetype", "arm", "stratum")},
        "passed": all(value["passed"] for value in checks.values()),
        "complete": all(value["status"] != "indeterminate" for value in checks.values()),
        "checks": checks,
        "anchor_guard_evidence": guards,
        "integration": integration,
    }


def finite_panel_gate(rows: list[Json], *, arms: tuple[str, ...] = ("A", "B", "C")) -> Json:
    groups: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        if row["stratum"] == "base" and row["arm"] in arms:
            groups[row["map"]].append(row["passed"])
    expected_n = 6 * len(arms)
    if len(groups) != 9 or any(len(values) != expected_n for values in groups.values()):
        return {"passed": False, "reason": "base map denominator differs from frozen panel"}
    rates = {name: 1 - sum(values) / len(values) for name, values in sorted(groups.items())}
    values = np.asarray(list(rates.values()))
    score = float(values.mean() + t.ppf(0.95, 8) * values.std(ddof=1) / 3)
    return {
        "passed": score <= 0.05 and float(values.max()) <= 0.25,
        "map_failure_fractions": rates,
        "empirical_acceptance_score": score,
        "maximum_map_failure_fraction": float(values.max()),
        "population_confidence_bound": False,
    }


def summarise(panel: Json, index: Json, evidence: Evidence) -> Json:
    rows = panel["datasets"]
    if Counter(row["stratum"] for row in rows) != Counter(COUNTS):
        raise ValueError("panel is not the frozen 207-case design")
    for flag, count in (
        ("independent_bank", 54),
        ("exhaustive_audit", 18),
        ("integration_screen", 9),
    ):
        if sum(row.get(flag, False) is True for row in rows) != count:
            raise ValueError(f"frozen {flag} subset count differs")
    ids = {row["dataset_id"] for row in rows}
    if len(ids) != 207 or set(index["cases"]) - ids:
        raise ValueError("duplicate panel IDs or unregistered indexed cases")
    if index["schema"] != "sprint2-qualification-index-v1" or not index["source_commit"]:
        raise ValueError("missing frozen index/source identity")
    assessed = [
        assess_case(
            row, index["cases"].get(row["dataset_id"], {}), evidence, index["source_commit"]
        )
        for row in rows
    ]
    gate = finite_panel_gate(assessed)
    ab = finite_panel_gate(assessed, arms=("A", "B"))
    base_failures = [row for row in assessed if row["stratum"] == "base" and not row["passed"]]
    ab_only = (
        all(row["complete"] for row in assessed if row["stratum"] == "base")
        and bool(base_failures)
        and all(row["arm"] == "C" for row in base_failures)
        and ab["passed"]
    )
    nonbase_failures = [
        row["dataset_id"] for row in assessed if row["stratum"] != "base" and not row["passed"]
    ]
    complete = all(row["complete"] for row in assessed)
    status = (
        "incomplete"
        if not complete
        else "repair_required"
        if nonbase_failures
        else "qualified_finite_panel"
        if gate["passed"]
        else "qualified_ab_only"
        if ab_only
        else "repair_required"
    )
    integration_ids = {row["dataset_id"] for row in rows if row["integration_screen"]}
    integration_rows = [
        row["integration"] for row in assessed if row["dataset_id"] in integration_ids
    ]
    integration_statuses = Counter(row["status"] for row in integration_rows)
    integration_complete = all(
        row["complete"] and row["status"] != "not_selected" for row in integration_rows
    )
    guard_rows = [value for row in assessed for value in row["anchor_guard_evidence"].values()]
    expected_streams = sum(
        2 + int(row["independent_bank"]) + int(row["exhaustive_audit"]) for row in rows
    )
    guard_summary = {
        "expected_fit_streams": expected_streams,
        "available_fit_streams": sum(value["status"] == "available" for value in guard_rows),
        "unavailable_fit_streams": expected_streams
        - sum(value["status"] == "available" for value in guard_rows),
        "high_sigma_anchor_guard_datasets": [
            row["dataset_id"]
            for row in assessed
            if any(
                value.get("high_sigma_anchor_offending_candidates", 0) > 0
                for value in row["anchor_guard_evidence"].values()
            )
        ],
        "offending_candidate_records": sum(
            value.get("high_sigma_anchor_offending_candidates", 0) for value in guard_rows
        ),
        "scope": (
            "Verified unresolved-fit event records only; unavailable streams are not zero counts."
        ),
    }
    packet_complete = complete and integration_complete
    numerical_status = status
    if not integration_complete and status in ("qualified_finite_panel", "qualified_ab_only"):
        status = "numerically_qualified_packet_incomplete"
    denominators = {
        stratum: {
            "total": sum(row["stratum"] == stratum for row in assessed),
            "passed": sum(row["stratum"] == stratum and row["passed"] for row in assessed),
        }
        for stratum in COUNTS
    }
    return {
        "schema": "sprint2-qualification-summary-v1",
        "status": status,
        "source_commit": index["source_commit"],
        "numerical_status": numerical_status,
        "packet_complete": packet_complete,
        "integration": {
            "expected_screens": len(integration_ids),
            "complete": integration_complete,
            "statuses": dict(integration_statuses),
        },
        "anchor_guard_summary": guard_summary,
        "finite_panel_only": True,
        "training_authorised": False,
        "base_gate": gate,
        "ab_gate": ab,
        "ab_continuation_eligible": ab_only,
        "nonbase_repair_required": nonbase_failures,
        "denominators": denominators,
        "cases": assessed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    panel, index = (json.loads(path.read_text()) for path in (args.panel, args.index))
    if digest(args.panel) != index["panel_sha256"]:
        raise ValueError("panel hash differs from frozen index")
    result = summarise(panel, index, Evidence(args.index.parent))
    result.update(panel_sha256=digest(args.panel), index_sha256=digest(args.index))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(
        json.dumps({key: result[key] for key in ("status", "denominators", "training_authorised")})
    )
    return 0 if result["status"] in ("qualified_finite_panel", "qualified_ab_only") else 1


if __name__ == "__main__":
    raise SystemExit(main())
