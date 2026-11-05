"""Reproduce the post-outcome cross-tabs and paired estimate observations."""

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--datasets", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
rows = list(csv.DictReader(args.datasets.open()))
result = {
    "schema": "procedure-review-descriptives-v1",
    "post_outcome": True,
    "validation_claim": False,
    "datasets_sha256": hashlib.sha256(args.datasets.read_bytes()).hexdigest(),
    "cross_tabs": {},
    "paired_estimates": {},
}
for key in ("dense_lean_status", "bank_status", "integration_status"):
    result["cross_tabs"][key] = [
        {"free_sigma_status": sigma, "status": status or "not_requested", "count": count}
        for (sigma, status), count in sorted(
            Counter((row["free_sigma_status"], row[key]) for row in rows).items()
        )
    ]
for truth in (1, 3):
    pairs = {}
    for row in rows:
        if row["arm"] in ("A", "B") and float(row["generating_h"]) == truth:
            key = row["dataset_id"].rsplit("-arm-", 1)[0]
            pairs.setdefault(key, {})[row["arm"]] = row
    paired = []
    for history, pair in pairs.items():
        a, b = pair["A"]["free_h"], pair["B"]["free_h"]
        paired.append(
            {
                "history": history,
                "h_A": float(a) if a else None,
                "h_B": float(b) if b else None,
                "log_error_A": math.log(float(a) / truth) if a else None,
                "log_error_B": math.log(float(b) / truth) if b else None,
                "available_pair": bool(a and b),
            }
        )
    available = [pair for pair in paired if pair["available_pair"]]
    result["paired_estimates"][str(truth)] = {
        "histories": paired,
        "available_pairs": len(available),
        "unavailable_pairs": len(paired) - len(available),
        "B_below_A": sum(p["h_B"] < p["h_A"] for p in available),
        "B_equal_A_exactly": sum(p["h_B"] == p["h_A"] for p in available),
        "mean_log_error_A_complete_pairs": sum(p["log_error_A"] for p in available)
        / len(available),
        "mean_log_error_B_complete_pairs": sum(p["log_error_B"] for p in available)
        / len(available),
    }
args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
