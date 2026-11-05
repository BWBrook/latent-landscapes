"""Extract unresolved-profile evidence from hash-bound archived evaluation streams."""

import argparse
import hashlib
import json
import math
from pathlib import Path

DATASETS = ("cell-00-rep-005-arm-B-B0", "cell-06-rep-006-arm-B-B0")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate(row):
    return {
        key: row[key]
        for key in (
            "family",
            "source",
            "h",
            "criterion",
            "parameters",
            "eligible",
            "projected_gradient_inf",
            "optimizer_success",
            "evaluation_success",
            "mode",
        )
    } | {"sigma": math.exp(row["parameters"]["log_sigma"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt-root", type=Path, required=True)
    parser.add_argument("--log-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = []
    witness = None
    for dataset in DATASETS:
        for search in ("dense", "lean"):
            relative = Path(dataset) / search
            receipt_path = args.receipt_root / relative / "receipt.json"
            log_path = args.log_root / relative / "evaluations.jsonl"
            receipt = json.loads(receipt_path.read_text())
            log_hash = digest(log_path)
            assert log_hash == receipt["evaluation_stream"]["sha256"], str(relative)
            assert receipt["status"] == "indeterminate", str(relative)
            assert receipt["failure"]["message"] == (
                "unresolved candidate exceeds selected family envelope"
            ), str(relative)
            events = [json.loads(line) for line in log_path.read_text().splitlines()]
            assert events[-1]["kind"] == "unresolved_fit", str(relative)
            rows = events[-1]["candidates"]
            eligible = {
                family: max(
                    (r for r in rows if r["family"] == family and r["eligible"]),
                    key=lambda r: r["criterion"],
                )
                for family in ("positive_sigma", "sigma_zero")
            }
            unresolved = [
                r
                for r in rows
                if not r["eligible"]
                and math.isfinite(r["criterion"])
                and r["criterion"] > eligible[r["family"]]["criterion"] + 1e-4
            ]
            assert unresolved and all(r["family"] == "positive_sigma" for r in unresolved)
            best = max(unresolved, key=lambda r: r["criterion"])
            completed_maximum = max(e["fit"]["criterion"] for e in events[:-1])
            results.append(
                {
                    "dataset": dataset,
                    "search": search,
                    "receipt_relative_path": str(relative / "receipt.json"),
                    "receipt_sha256": digest(receipt_path),
                    "stream_relative_path": str(relative / "evaluations.jsonl"),
                    "stream_sha256": log_hash,
                    "stream_binding_verified": True,
                    "failure": receipt["failure"]["message"],
                    "failure_h": best["h"],
                    "eligible_positive": candidate(eligible["positive_sigma"]),
                    "eligible_zero_criterion": eligible["sigma_zero"]["criterion"],
                    "highest_unresolved": candidate(best),
                    "unresolved_candidate_count": len(unresolved),
                    "criterion_excess_over_eligible_positive": (
                        best["criterion"] - eligible["positive_sigma"]["criterion"]
                    ),
                    "best_completed_criterion": completed_maximum,
                    "W_relative_to_best_completed": 2 * (completed_maximum - best["criterion"]),
                }
            )
            if dataset == DATASETS[0] and search == "dense":
                cold = next(r for r in rows if r["source"].endswith("_powell_1"))
                warm = next(r for r in rows if r["source"].endswith("_polish_1"))
                assert cold["parameters"] == warm["parameters"]
                witness = {
                    "dataset": dataset,
                    "search": search,
                    "outer_parameters_exactly_equal": True,
                    "cold_fallback": candidate(cold),
                    "warm_polish": candidate(warm),
                    "warm_minus_cold_criterion": warm["criterion"] - cold["criterion"],
                }
    root = Path(__file__).resolve().parents[3]
    source_paths = (
        "scripts/qualify_spatial_profiles.py",
        "src/latent_landscapes/spatial_profile.py",
    )
    result = {
        "schema": "unresolved-profile-readonly-audit-v1",
        "audit_script_sha256": digest(Path(__file__)),
        "source_sha256": {name: digest(root / name) for name in source_paths},
        "new_fits_run": False,
        "method_changed": False,
        "envelope_excess_tolerance": 1e-4,
        "projected_gradient_gate": 0.001,
        "profiles": results,
        "identical_outer_parameter_witness": witness,
        "interpretation": (
            "Unresolved interior-positive-sigma candidates exceed local eligible envelopes. "
            "They are not certified optima. The identical-parameter witness demonstrates "
            "recorded cold/warm latent-start sensitivity, not its fully diagnosed cause. "
            "W relative to completed points is descriptive, not an exclusion bound."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(f"Verified {len(results)} stream bindings and one identical-parameter witness.")


if __name__ == "__main__":
    main()
