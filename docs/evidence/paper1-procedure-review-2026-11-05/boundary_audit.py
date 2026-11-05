"""Describe a contact-only counterfactual without changing frozen fits or verdicts."""

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

FAMILIES = ("positive_sigma", "sigma_zero")
TIE = 1e-4
LOWER = ("positive_sigma", "log_sigma:lower")


def owners(fit):
    return {family for family in FAMILIES if fit["criterion"] - fit[family]["criterion"] <= TIE}


def tied(fit):
    return abs(fit["positive_sigma"]["criterion"] - fit["sigma_zero"]["criterion"]) <= TIE


def contacts(fit, normalize=False):
    result = {
        (family, contact)
        for family in owners(fit)
        for contact in fit[family]["nuisance_bound_contacts"]
    }
    return result - {LOWER} if normalize and tied(fit) else result


def point_agreement(left, right, normalize=False):
    common = owners(left) & owners(right)
    a, b = contacts(left, normalize), contacts(right, normalize)
    return bool(common) and {c for c in a if c[0] in common} == {c for c in b if c[0] in common}


def inside_contacts(child, extra=(), normalize=False):
    points = {fit["log_h"]: fit for fit in child.get("points", {}).get("True", [])}
    points.update({point["log_h"]: point["tight_fit"] for point in extra})
    maximum = child["free"]["True"]["criterion"]
    return set().union(
        *(
            contacts(fit, normalize)
            for fit in points.values()
            if 2 * (maximum - fit["criterion"]) <= 3.84
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.receipt_root.resolve()):
        raise ValueError("Output must be outside the unchanged receipt root")
    hashes, cache = {}, {}

    def read(relative):
        key = str(relative)
        if key not in cache:
            data = (args.receipt_root / relative).read_bytes()
            hashes[key] = hashlib.sha256(data).hexdigest()
            cache[key] = json.loads(data)
        return cache[key]

    summary = read(Path("summary-final/summary.json"))
    parents, children = {}, {}
    for path in sorted((args.receipt_root / "profiles").glob("*/receipt.json")):
        name = path.parent.name
        parents[name] = read(path.relative_to(args.receipt_root))
        for mode, binding in parents[name]["searches"].items():
            relative = Path("profiles") / name / mode / "receipt.json"
            children[(name, mode)] = read(relative)
            assert hashes[str(relative)] == binding["sha256"]
    cross_tabs = {}
    for column in ("dense_lean_comparison_status", "bank_comparison"):
        values = Counter()
        for row in summary["datasets"]:
            status = row[column] if column != "bank_comparison" else row[column]["status"]
            values[(row["free"]["sigma_status"], status or "not_requested")] += 1
            parent_path = f"profiles/{row['dataset_id']}-B0/receipt.json"
            assert hashes[parent_path] == row["receipt_sha256"]["profile_run"]
        cross_tabs[column] = [
            {"free_sigma_status": sigma, "status": status, "count": count}
            for (sigma, status), count in sorted(values.items())
        ]

    inside_occurrences = Counter()
    for child in children.values():
        for fit in child.get("points", {}).get("True", []):
            if 2 * (child["free"]["True"]["criterion"] - fit["criterion"]) <= 3.84:
                for family, contact in contacts(fit):
                    inside_occurrences[(family, contact, tied(fit))] += 1

    results = {}
    for kind in ("dense_lean", "banks"):
        rows, residual_points, residual_inside, passed = [], 0, 0, 0
        unresolved = 0
        if kind == "dense_lean":
            candidates = [
                (name, p["comparison"]) for name, p in parents.items() if name.endswith("-B0")
            ]
        else:
            candidates = [
                (p.parent.name, read(p.relative_to(args.receipt_root)))
                for p in sorted((args.receipt_root / "bank-comparisons").glob("*/receipt.json"))
            ]
        for name, comparison in candidates:
            if not comparison or comparison["status"] == "indeterminate":
                unresolved += 1
                continue
            if kind == "dense_lean":
                pair = [children[(name, mode)] for mode in ("dense", "lean")]
                evaluations = [child["post_search_diagnostics"]["points"] for child in pair]
                flag = "nuisance_contact_agreement"
                other_gates = (
                    comparison["set_classes_agree"]
                    and all(c["passed"] for c in comparison["level_set_checks"])
                    and abs(comparison["twice_free_criterion_difference"]) <= 0.01
                )
                tolerance = 0.01
            else:
                pair = [children[(f"{name}-{bank}", "dense")] for bank in ("B0", "A")]
                evaluations = [
                    comparison["cross_evaluations"][bank]["points"] for bank in ("B0", "A")
                ]
                flag = "boundary_contact_agreement"
                free = comparison["free_fit_agreement"]
                other_gates = (
                    all(c["passed"] for c in comparison["level_set_checks"])
                    and free["ownership_agreement"]
                    and free["boundary_contact_agreement"]
                )
                tolerance = 0.10
            lookups = [{p["log_h"]: p["tight_fit"] for p in group} for group in evaluations]
            bad, both_tied, only_lower, max_gap, sigmas = 0, 0, 0, 0.0, []
            remaining = 0
            for point in comparison["points"]:
                fits = [lookup[point["log_h"]] for lookup in lookups]
                assert point_agreement(*fits) == point[flag]
                relevant = kind == "dense_lean" or point["inside_either_diagnostic_set"]
                if relevant and not point_agreement(*fits, normalize=True):
                    remaining += 1
                other_gates &= (
                    math.isfinite(point["delta_w"])
                    and abs(point["delta_w"]) <= tolerance
                    and point["ownership_agreement"]
                )
                if point[flag]:
                    continue
                bad += 1
                both_tied += all(tied(fit) for fit in fits)
                only_lower += (contacts(fits[0]) ^ contacts(fits[1])) == {LOWER}
                for fit in fits:
                    gap = abs(fit["positive_sigma"]["criterion"] - fit["sigma_zero"]["criterion"])
                    max_gap = max(max_gap, gap)
                    sigmas.append(math.exp(fit["positive_sigma"]["parameters"]["log_sigma"]))
            normalized_inside = [
                inside_contacts(child, extra, normalize=True)
                for child, extra in zip(pair, evaluations, strict=True)
            ]
            inside_match = normalized_inside[0] == normalized_inside[1]
            residual_points += remaining
            residual_inside += not inside_match
            passed += other_gates and remaining == 0 and inside_match
            if bad:
                rows.append(
                    {
                        "dataset_role": name,
                        "original_status": comparison["status"],
                        "failed_points": bad,
                        "both_fits_tied": both_tied,
                        "only_lower_sigma_differs": only_lower,
                        "maximum_absolute_family_gap": max_gap,
                        "positive_sigma_range": [min(sigmas), max(sigmas)],
                        "counterfactual_residual_point_mismatches": remaining,
                        "counterfactual_inside_contacts_agree": inside_match,
                    }
                )
        results[kind] = {
            "failed_point_details": rows,
            "failed_point_count": sum(row["failed_points"] for row in rows),
            "counterfactual_residual_point_mismatches": residual_points,
            "counterfactual_residual_inside_mismatches": residual_inside,
            "counterfactual_passes": passed,
            "unresolved_unchanged": unresolved,
        }
    result = {
        "status": "descriptive_counterfactual_only",
        "original_statuses_modified": False,
        "rule": (
            "At pointwise family ties only, omit positive_sigma/log_sigma:lower contact; "
            "retain raw envelope criterion and all other gates."
        ),
        "tie_tolerance": TIE,
        "parent_count": len(parents),
        "child_count": len(children),
        "cross_tabs": cross_tabs,
        "inside_child_mesh_contact_occurrences": [
            {"family": family, "contact": contact, "tied": tie, "count": count}
            for (family, contact, tie), count in sorted(inside_occurrences.items())
        ],
        "comparisons": results,
        "input_sha256": dict(sorted(hashes.items())),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                kind: {k: v for k, v in value.items() if k != "failed_point_details"}
                for kind, value in results.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
