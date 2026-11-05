"""Audit sprint arithmetic; scenarios are not scheduler forecasts."""

import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--datasets", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
rows = list(csv.DictReader(args.datasets.open()))
biological = 30 * 6 * 2 * 6 * 100
arm_datasets = 3 * biological
cpu_hours = arm_datasets * 8 / 60
result = {
    "schema": "sprint-cost-scenarios-v1",
    "forecast": False,
    "source_datasets_sha256": hashlib.sha256(args.datasets.read_bytes()).hexdigest(),
    "illustrative_inputs": {
        "maps_total": 30,
        "archetypes": 3,
        "backgrounds": 6,
        "mu_values": 2,
        "truths": 6,
        "histories_per_map_cell": 100,
        "paired_arms": 3,
        "hypothetical_spatial_profile_minutes": 8,
    },
    "biological_histories": biological,
    "arm_datasets": arm_datasets,
    "free_null_main_fit_outputs": arm_datasets * 6,
    "hypothetical_profile_cpu_hours": cpu_hours,
    "ideal_days": {str(n): cpu_hours / (n * 24) for n in [40, 1000, 2000]},
    "exclusions": [
        "queue delay",
        "other fits and profiles",
        "qualification",
        "retries",
        "cross_validation_refits",
        "bootstrap",
        "integration_diagnostics",
        "io",
    ],
    "observed_lean_search_only_minutes": {},
    "bernoulli_illustration": {
        "p_0_05_n_100_mcse": (0.05 * 0.95 / 100) ** 0.5,
        "p_0_05_n_for_mcse_0_005": 0.05 * 0.95 / 0.005**2,
        "p_0_5_n_for_mcse_0_005": 0.5 * 0.5 / 0.005**2,
        "note": (
            "Independent-history arithmetic only; "
            "actual planning retains paired covariance and map variation."
        ),
    },
}
for sites, arms in [(120, ["A", "B"]), (260, ["C"])]:
    values = [
        float(r["lean_search_seconds"]) / 60
        for r in rows
        if r["arm"] in arms and r["dense_status"] == "profile_numerically_resolved"
    ]
    result["observed_lean_search_only_minutes"][str(sites)] = {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
        "scope": "Previous shared-host execution; not a PBS-host forecast.",
    }
args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
