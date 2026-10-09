#!/usr/bin/env python3
"""Score the locked Goal 061 forecasts after Barry's explicit truth release."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TRUTH_SHA = "f4145408b52e24e459e751f9fa646a3365fb9d596f8a3da8476853e48c56af8d"
LOCK_SHA = "baa0ec8660321d698e4cb5b2d3ef9f41ef41fec9b3a7e751fe18a00813e835af"
FORECAST_SHA = "ea017c2300214b834ddb28fae577d9c5f9e43ba9f43337a185d448bd7bab1895"
DOCS = Path("docs/goals/061-blinded-capstone-training")

# Literal transcription of the hash-bound prereveal table and its broad SD sets.
# All four primary effect forecasts are null (h=1), with exact-family background.
FORECASTS = (
    {"beta": 0.25, "mu": 0.004, "sd": 0.3, "sd_set": (0.2, 0.3)},
    {"beta": 1.00, "mu": 0.004, "sd": 0.2, "sd_set": (0.1, 0.2, 0.3)},
    {"beta": 0.00, "mu": 0.001, "sd": 0.3, "sd_set": (0.2, 0.3)},
    {"beta": 0.25, "mu": 0.001, "sd": 0.1, "sd_set": (0.0, 0.1, 0.2)},
)


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_bound(path: Path, expected: str) -> dict[str, Any]:
    if sha256(path) != expected:
        raise ValueError(f"Input commitment mismatch: {path}")
    return json.loads(path.read_text())


def load_truth(path: Path) -> tuple[list[dict[str, Any]], str]:
    """Read only the released metadata after verifying the salted archive."""
    if sha256(path) != TRUTH_SHA:
        raise ValueError("Truth archive commitment mismatch")
    expected = {
        "salt.bin",
        "private-root.bin",
        "padding.bin",
        "truth-metadata.json",
        *(f"case-{i:02d}-latent.npz" for i in range(4)),
    }
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        if len(members) != len(expected) or {m.name for m in members} != expected:
            raise ValueError("Unexpected truth archive members")
        if not all(m.isfile() for m in members):
            raise ValueError("Nonregular truth archive member")
        if archive.getmember("salt.bin").size != 32:
            raise ValueError("Incorrect truth salt layout")
        handle = archive.extractfile("truth-metadata.json")
        if handle is None:
            raise ValueError("Missing truth metadata")
        blob = handle.read()
    metadata = json.loads(blob)
    if metadata["schema_version"] != "goal060-truth-v1":
        raise ValueError("Unexpected truth metadata schema")
    rows = metadata["truths"]
    if len(rows) != 4 or [row["index"] for row in rows] != list(range(4)):
        raise ValueError("Incorrect truth case identities")
    fields = ("index", "effect", "h_null", "background", "beta", "mean_hazard", "detection_sd")
    for row in rows:
        h = row["effect"]
        if not (h == 1.0 or 2.0 <= h <= 5.0) or row["h_null"] != (h == 1.0):
            raise ValueError("Truth effect outside registered law")
        if row["background"] not in ("exact", "B100-A"):
            raise ValueError("Unknown truth branch")
        if (row["beta"] is None) != (row["background"] == "B100-A"):
            raise ValueError("Truth beta does not match branch")
    return [{key: row[key] for key in fields} for row in rows], hashlib.sha256(blob).hexdigest()


def score_case(
    truth: dict[str, Any], forecast: dict[str, Any], h_hat: float, p_bb: float
) -> dict[str, Any]:
    """Apply the prereveal rules without tolerance-based hits or reclassification."""
    h = truth["effect"]
    exact = truth["background"] == "exact"
    return {
        "case_id": f"case-{truth['index']:02d}",
        "true_h": h,
        "forecast_h": 1.0,
        "effect_class_hit": truth["h_null"],
        "forecast_abs_log_h_error": abs(math.log(1.0 / h)),
        "adjusted_h_hat": h_hat,
        "adjusted_abs_log_h_error": abs(math.log(h_hat / h)),
        "true_background": truth["background"],
        "forecast_background": "exact",
        "background_hit": exact,
        "true_beta": truth["beta"],
        "forecast_beta_if_exact": forecast["beta"],
        "beta_abs_error_if_exact": abs(forecast["beta"] - truth["beta"]) if exact else None,
        "true_mu_per_day": truth["mean_hazard"],
        "forecast_mu_per_day": forecast["mu"],
        "mu_grid_hit": forecast["mu"] == truth["mean_hazard"],
        "mu_abs_error_per_day": abs(forecast["mu"] - truth["mean_hazard"]),
        "true_detection_sd": truth["detection_sd"],
        "forecast_detection_sd": forecast["sd"],
        "detection_sd_grid_hit": forecast["sd"] == truth["detection_sd"],
        "detection_sd_abs_error": abs(forecast["sd"] - truth["detection_sd"]),
        "forecast_detection_sd_set": "|".join(str(x) for x in forecast["sd_set"]),
        "detection_sd_set_hit": truth["detection_sd"] in forecast["sd_set"],
        "training_p_BB": p_bb,
        "training_effect_declared": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--truth-archive", type=Path, default=Path("artifacts/capstone_sealed/truth.tar")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lock_path = Path("artifacts/goal061_holdout/complete-report-lock.json")
    lock = read_bound(lock_path, LOCK_SHA)
    # The release receipt records Barry's authorization and full closure verification.
    release_path = Path("artifacts/goal061_truth/release-verification.json")
    release = json.loads(release_path.read_text())
    if not (
        release["passed"]
        and release["truth_release_authorized"]
        and release["complete_report_lock_sha256"] == LOCK_SHA
    ):
        raise ValueError("Missing verified truth release")
    forecast_path = DOCS / "prereveal-predictions.md"
    if sha256(forecast_path) != FORECAST_SHA:
        raise ValueError("Prereveal forecast commitment mismatch")
    inherited = lock["inherited_training_lock"]
    training_path = Path(inherited["manifest"])
    training = read_bound(training_path, inherited["manifest_sha256"])
    child = next(
        x for x in training["child_manifests"] if x["role"] == "completed_training_analysis"
    )
    computation_path = Path(child["manifest"])
    computation = read_bound(computation_path, child["manifest_sha256"])
    truths, metadata_sha = load_truth(args.truth_archive)
    if metadata_sha != release["truth_metadata_sha256"]:
        raise ValueError("Released metadata binding mismatch")
    bindings = {
        str(p): sha256(p)
        for p in (
            lock_path,
            training_path,
            computation_path,
            forecast_path,
            release_path,
            args.truth_archive,
            Path(__file__),
        )
    }
    if training["scientific_result"]["valid_nondeclarations"] != 4:
        raise ValueError("Unexpected locked training decisions")
    rows = []
    for i, truth in enumerate(truths):
        relative = f"analysis/fit/fits/history-{i:02d}-full-main.json"
        fit_path = Path(child["base_directory"]) / relative
        fit = read_bound(fit_path, computation["files"][relative])["fits"]["adjusted_free_h"]
        bindings[str(fit_path)] = sha256(fit_path)
        if fit["numerical_status"] != "converged":
            raise ValueError("Frozen adjusted fit was not converged")
        rows.append(
            score_case(truth, FORECASTS[i], fit["h"], training["scientific_result"]["p_BB"][i])
        )
    args.output.mkdir(parents=True, exist_ok=False)
    csv_path = args.output / "forecast_scores.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    result = {
        "schema": "goal061-truth-forecast-scores-v1",
        "created_utc": datetime.now(UTC).isoformat(),
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "input_sha256": bindings,
        "truth_metadata_sha256": metadata_sha,
        "rules": (
            "Locked prereveal rules; natural-log h errors; exact-grid hits; "
            "beta undefined under B100-A; broad SD sets separate from points."
        ),
        "rows": rows,
        "truths": truths,
        "csv_sha256": sha256(csv_path),
        "departures_from_locked_rules": [],
        "models_refitted": False,
    }
    (args.output / "scores.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Scored {len(rows)} released truths under the unchanged prereveal rules.")


if __name__ == "__main__":
    main()
