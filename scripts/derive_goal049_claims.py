"""Derive Goal 049's retrospective Arc 2B classification amendment.

This script reads the frozen Arc 2B condition table and writes a side-by-side
interpretation.  It does not alter the historical classifier or source table.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from pathlib import Path

DEFAULT_INPUT = Path("artifacts/arc2b_synthesis/condition_outcomes.csv")
DEFAULT_OUTPUT = Path("artifacts/goal049_claims/arc2b_classification_side_by_side.csv")
EXPECTED_HISTORICAL = {
    "fully_recovered": 3,
    "detected_but_not_fully_recovered": 10,
    "not_reliably_detected": 19,
}
EXPECTED_AMENDED = {
    "fully_recovered": 4,
    "detected_but_not_fully_recovered": 9,
    "not_reliably_detected": 19,
}


def _gate_results(row: dict[str, str]) -> dict[str, bool]:
    return {
        "coverage": float(row["coverage_lower"]) <= 0.95 <= float(row["coverage_upper"]),
        "connected_interior": float(row["connected_interior_frequency"]) >= 238 / 250,
        "excludes_no_effect": float(row["no_effect_exclusion_probability"]) >= 238 / 250,
        "point_error": float(row["median_absolute_log_effect_error"]) <= 0.20,
        "support_width": float(row["median_log_support_width"]) <= 0.80,
        "predictive_advantage": (
            float(row["heldout_known_background_no_effect_advantage_lower"]) > 0.0
        ),
        "production_count": int(row["validation_count"]) == 250,
    }


def _classify(passes: dict[str, bool], *, include_coverage: bool) -> tuple[str, str]:
    active = {
        gate: passed for gate, passed in passes.items() if include_coverage or gate != "coverage"
    }
    failed = tuple(gate for gate, passed in active.items() if not passed)
    if all(active.values()):
        return "fully_recovered", ""
    if passes["excludes_no_effect"] and passes["predictive_advantage"]:
        return "detected_but_not_fully_recovered", ";".join(failed)
    return "not_reliably_detected", ";".join(failed)


def derive(input_path: Path, output_path: Path) -> None:
    with input_path.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["condition_id"].startswith("S")]
    if len(rows) != 32:
        raise ValueError(f"expected 32 Arc 2B scientific truths, found {len(rows)}")

    output_rows: list[dict[str, str]] = []
    historical_counts: Counter[str] = Counter()
    amended_counts: Counter[str] = Counter()
    for row in rows:
        passes = _gate_results(row)
        historical_class, historical_failed = _classify(passes, include_coverage=True)
        amended_class, amended_failed = _classify(passes, include_coverage=False)
        if (historical_class, historical_failed) != (
            row["recovery_classification"],
            row["failed_gates"],
        ):
            raise ValueError(
                f"stored historical classification does not reproduce: {row['condition_id']}"
            )
        historical_counts[historical_class] += 1
        amended_counts[amended_class] += 1
        output_rows.append(
            {
                "condition_id": row["condition_id"],
                "historical_classification": historical_class,
                "historical_failed_gates": historical_failed,
                "amended_classification": amended_class,
                "amended_failed_gates": amended_failed,
                "classification_changed": str(historical_class != amended_class),
            }
        )

    if dict(historical_counts) != EXPECTED_HISTORICAL:
        raise ValueError(f"unexpected historical counts: {dict(historical_counts)}")
    if dict(amended_counts) != EXPECTED_AMENDED:
        raise ValueError(f"unexpected amended counts: {dict(amended_counts)}")
    changed = [
        row["condition_id"] for row in output_rows if row["classification_changed"] == "True"
    ]
    if changed != ["S08"]:
        raise ValueError(f"expected only S08 to change, found {changed}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)

    digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    print(f"input_sha256={digest}")
    print(f"historical={dict(historical_counts)}")
    print(f"amended={dict(amended_counts)}")
    print(f"changed={changed}")
    print(f"wrote={output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    derive(args.input, args.output)


if __name__ == "__main__":
    main()
