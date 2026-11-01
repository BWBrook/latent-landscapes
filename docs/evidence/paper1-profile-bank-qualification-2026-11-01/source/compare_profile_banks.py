"""Compare qualified diagnostic profiles without making coverage claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

PAIRS = (("B0", "A"), ("B0", "B"), ("A", "B"), ("A", "AB"), ("B", "AB"))
DATA_KEYS = {
    "observations_sha256",
    "public_npz_sha256",
    "exposure_sha256",
    "training_site_ids_sha256",
    "training_site_count",
    "covariance_range",
    "prey_times",
    "predator_times",
    "cohort_start",
}


def require_comparable(receipts: dict[str, dict[str, Any]]) -> None:
    reference = receipts["B0"]
    identity = reference["data_identity"]
    if not DATA_KEYS.issubset(identity) or identity["training_site_count"] != 120:
        raise ValueError("missing or wrong common data identity")
    sources = {p: h for p, h in reference["source_input_sha256"].items() if p.endswith(".py")}
    if not sources:
        raise ValueError("scientific source bindings are missing")
    for role, receipt in receipts.items():
        if receipt["bank_identity"]["role"] != role:
            raise ValueError("receipt bank role mismatch")
        if receipt["data_identity"] != identity:
            raise ValueError("histories, training sites, public inputs or model settings differ")
        other = {p: h for p, h in receipt["source_input_sha256"].items() if p.endswith(".py")}
        if other != sources:
            raise ValueError("scientific source bindings differ across bank profiles")


def free_effects(receipt: dict[str, Any]) -> dict[str, Any]:
    families = ("positive_sigma", "sigma_zero")
    free = receipt["tight_free"]
    owner = max(families, key=lambda family: free[family]["criterion"])
    return {
        "by_family": {family: free[family]["h"] for family in families},
        "envelope_owner": owner,
        "envelope_h": free[owner]["h"],
    }


def pseudo_refit_required(pseudo: dict[str, Any]) -> bool:
    if (
        pseudo.get("schema") != "profile-pseudo-mass-fixed-fit-v1"
        or pseudo.get("status") != "evaluated"
        or pseudo.get("fixed_fit_only") is not True
        or pseudo.get("thresholds") != {"centered_lr_shift": 0.05, "projected_gradient": 1e-3}
    ):
        raise ValueError("pseudo-mass schema or threshold contract differs")
    shifts = pseudo["points"]
    branches = pseudo["family_replays"]
    if not shifts or not branches or len(branches) % 2:
        raise ValueError("pseudo-mass evidence is incomplete")
    if not all(
        math.isfinite(row[key])
        for row in branches
        for key in ("a_criterion", "adup_criterion", "adup_projected_gradient_inf")
    ):
        raise ValueError("pseudo-mass branch evidence is nonfinite")
    if not all(math.isfinite(row["delta_w"]) for row in shifts):
        raise ValueError("pseudo-mass LR evidence is nonfinite")
    maximum = max(abs(row["delta_w"]) for row in shifts)
    max_pg = max(row["adup_projected_gradient_inf"] for row in branches)
    if not math.isfinite(maximum) or not math.isfinite(max_pg):
        raise ValueError("pseudo-mass evidence is nonfinite")
    switched = False
    for i in range(0, len(branches), 2):
        pair = {row["family"]: row for row in branches[i : i + 2]}
        if set(pair) != {"positive_sigma", "sigma_zero"}:
            raise ValueError("pseudo-mass replay omits a variance family")
        p, z = pair["positive_sigma"], pair["sigma_zero"]
        a = p["a_criterion"] - z["a_criterion"]
        d = p["adup_criterion"] - z["adup_criterion"]
        switched |= a * d < 0 and min(abs(a), abs(d)) > 1e-4
    if (
        not math.isclose(
            maximum, pseudo["maximum_abs_centered_lr_shift"], rel_tol=1e-10, abs_tol=1e-12
        )
        or not math.isclose(
            max_pg, pseudo["maximum_projected_gradient"], rel_tol=1e-10, abs_tol=1e-12
        )
        or switched != bool(pseudo["material_family_ownership_changes"])
    ):
        raise ValueError("pseudo-mass summary disagrees with retained evidence")
    required = maximum > 0.05 or max_pg > 1e-3 or switched
    if required != pseudo["requires_full_refit"]:
        raise ValueError("pseudo-mass refit flag disagrees with the prespecified rule")
    return required


def topology(level: dict[str, Any]) -> Any:
    if level.get("status") != "available":
        return None
    return [
        (row["lower_domain_contact"], row["upper_domain_contact"], row["singleton"])
        for row in level["components"]
    ]


def compare(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    a = {row["log_h"]: row for row in left["anchors"]}
    b = {row["log_h"]: row for row in right["anchors"]}
    if a.keys() != b.keys() or len(a) != 35:
        raise ValueError("bank profiles require the same 35 diagnostic anchors")
    rows = []
    for x in sorted(a):
        if not all(math.isfinite(row["w"]) for row in (a[x], b[x])):
            raise ValueError("anchor LR is nonfinite")
        rows.append(
            {
                "h": a[x]["h"],
                "log_h": x,
                "left_w": a[x]["w"],
                "right_w": b[x]["w"],
                "delta_w": b[x]["w"] - a[x]["w"],
            }
        )
    levels_a = {row["cutoff"]: row for row in left["tight_level_sets"]}
    levels_b = {row["cutoff"]: row for row in right["tight_level_sets"]}
    if levels_a.keys() != levels_b.keys() or set(levels_a) != {1.0, 3.84, 6.63}:
        raise ValueError("diagnostic cutoffs differ or are incomplete")
    checks = []
    for cutoff in sorted(levels_a):
        la, lb = levels_a[cutoff], levels_b[cutoff]
        same_topology = topology(la) is not None and topology(la) == topology(lb)
        delta_roots = (
            [rb["log_h"] - ra["log_h"] for ra, rb in zip(la["roots"], lb["roots"], strict=True)]
            if len(la["roots"]) == len(lb["roots"])
            else None
        )
        maximum = max(map(abs, delta_roots), default=0.0) if delta_roots is not None else None
        null_agreement = (rows[0]["left_w"] <= cutoff) == (rows[0]["right_w"] <= cutoff)
        checks.append(
            {
                "cutoff": cutoff,
                "same_components_and_domain_contacts": same_topology,
                "log_root_deltas": delta_roots,
                "maximum_abs_log_root_delta": maximum,
                "h1_inclusion_agreement": null_agreement,
                "passed": same_topology
                and maximum is not None
                and maximum <= 0.05
                and null_agreement,
            }
        )
    maximum_row = max(rows, key=lambda row: abs(row["delta_w"]))
    numerics = all(row["status"] == "profile_numerically_resolved" for row in (left, right))
    return {
        "passed": numerics
        and abs(maximum_row["delta_w"]) <= 0.10
        and all(row["passed"] for row in checks),
        "both_profiles_numerically_resolved": numerics,
        "anchors": rows,
        "largest_anchor_difference": maximum_row,
        "level_set_checks": checks,
        "free_effects_left": free_effects(left),
        "free_effects_right": free_effects(right),
        "free_h_movement_is_descriptive": True,
    }


def aggregate(
    receipts: dict[str, dict[str, Any]], pseudo: dict[str, Any], receipt_hashes: dict[str, str]
) -> dict[str, Any]:
    if not {"B0", "A", "B", "AB"}.issubset(receipts):
        raise ValueError("B0/A/B/AB receipts are all required")
    require_comparable(receipts)
    if pseudo["a_receipt_sha256"] != receipt_hashes["A"]:
        raise ValueError("pseudo-mass assessment does not bind the supplied A receipt")
    if pseudo["observations_sha256"] != receipts["A"]["data_identity"]["observations_sha256"]:
        raise ValueError("pseudo-mass assessment uses a different observation history")
    for role in ("A", "Adup"):
        if role not in receipts:
            continue
        if any(
            pseudo["bank_identities"][role][key] != receipts[role]["bank_identity"][key]
            for key in ("raw_sha256", "compressed_sha256", "bank_checksum")
        ):
            raise ValueError("pseudo-mass assessment bank identities differ from profiles")
    comparisons = [{"left": a, "right": b, **compare(receipts[a], receipts[b])} for a, b in PAIRS]
    pseudo_complete = pseudo.get("status") == "evaluated"
    requires_refit = pseudo_refit_required(pseudo)
    if requires_refit:
        pseudo_complete &= "Adup" in receipts
        if "Adup" in receipts:
            comparisons.append(
                {"left": "Adup", "right": "AB", **compare(receipts["Adup"], receipts["AB"])}
            )
            comparisons.append(
                {"left": "A", "right": "Adup", **compare(receipts["A"], receipts["Adup"])}
            )
            pseudo_complete &= receipts["Adup"]["status"] == "profile_numerically_resolved"
    passed = pseudo_complete and all(row["passed"] for row in comparisons)
    numerical = all(row["status"] == "profile_numerically_resolved" for row in receipts.values())
    return {
        "schema": "profile-bank-sensitivity-comparison-v1",
        "status": "within_prespecified_gates"
        if passed
        else "sensitive"
        if numerical and pseudo_complete
        else "indeterminate",
        "comparisons": comparisons,
        "pseudo_mass_assessment_complete": pseudo_complete,
        "pseudo_mass_requires_refit": requires_refit,
        "pseudo_mass": pseudo,
        "data_identity": receipts["B0"]["data_identity"],
        "calibrated_confidence_claim": False,
        "globality_proven": False,
        "scope": "one fixed development history; numerical and empirical-bank sensitivity",
        "pseudo_mass_caveat": "A/B versus AB changes both sampled arrivals and pseudo mass",
        "thresholds": {
            "max_abs_common_anchor_lr": 0.10,
            "max_abs_log_root": 0.05,
            "same_components_and_domain_contacts": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", action="append", required=True, help="ROLE=receipt.json")
    parser.add_argument("--pseudo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    paths = dict(item.split("=", 1) for item in args.receipt)
    receipts = {role: json.loads(Path(path).read_text()) for role, path in paths.items()}
    receipt_hashes = {
        role: hashlib.sha256(Path(path).read_bytes()).hexdigest() for role, path in paths.items()
    }
    result = aggregate(receipts, json.loads(args.pseudo.read_text()), receipt_hashes)
    all_paths = [Path(path) for path in paths.values()] + [args.pseudo, Path(__file__)]
    result["source_input_sha256"] = {
        str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in all_paths
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"]}))


if __name__ == "__main__":
    main()
