"""Screen fixed-outer Laplace contrasts; this does not reoptimise a profile."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import benchmark_spatial_profile as adapter
import numpy as np
from qualify_spatial_profiles import PARAMETERS, write_json
from run_development_profile import load_panel_data
from scipy.stats import t  # type: ignore[import-untyped]

from latent_landscapes.importance_reference import (
    Estimate,
    fixed_outer_contrast,
    integrate,
    paired_interval,
)
from latent_landscapes.spatial_importance_reference import direct_criterion, prepare_target

ROOT = Path(__file__).resolve().parents[1]


def coordinates(row: dict[str, Any]) -> np.ndarray:
    return np.array([row["parameters"][n] for n in PARAMETERS[row["family"]]], dtype=float)


def exact_estimate(value: float) -> Estimate:
    return Estimate(
        value, np.full(16, value), 0, {"weight_gates_passed": True, "exact_zero_family": True}
    )


def envelope(
    positive: Estimate, zero: float, *, comparisons: int = 1
) -> tuple[Estimate, dict[str, Any]]:
    gap = paired_interval(
        positive.batch_log_integrals - zero, estimate=positive.log_integral - zero
    )
    owner = "positive_sigma" if positive.log_integral >= zero else "sigma_zero"
    radius = (
        float(t.ppf(1 - 0.025 / comparisons, len(positive.batch_log_integrals) - 1))
        * gap["standard_error"]
    )
    gap.update(lower=gap["estimate"] - radius, upper=gap["estimate"] + radius, half_width=radius)
    stable = gap["lower"] > 1e-4 or gap["upper"] < -1e-4
    return (positive if owner == "positive_sigma" else exact_estimate(zero)), {
        "owner": owner,
        "ownership_gap": gap,
        "ownership_resolved": stable,
        "lower": max(positive.log_integral - radius, zero),
        "upper": max(positive.log_integral + radius, zero),
        "simultaneous_positive_integrals": comparisons,
        "positive": positive.summary(),
        "zero": zero,
    }


def summarize(estimates: dict[str, Estimate], fits: dict[str, dict[str, Any]]) -> dict[str, Any]:
    selected, envelopes = {}, {}
    for key, fit in fits.items():
        selected[key], envelopes[key] = envelope(
            estimates[key], fit["sigma_zero"]["criterion"], comparisons=len(fits) * 2 * 5
        )
        laplace_gap = fit["positive_sigma"]["criterion"] - fit["sigma_zero"]["criterion"]
        envelopes[key]["laplace_ownership_gap"] = laplace_gap
        gap = envelopes[key]["ownership_gap"]
        envelopes[key]["material_ownership_reversal"] = (
            laplace_gap > 1e-4 and gap["upper"] < -1e-4
        ) or (laplace_gap < -1e-4 and gap["lower"] > 1e-4)
    contrasts = {}
    for key in fits:
        if key == "free":
            continue
        paired = fixed_outer_contrast(
            selected["free"],
            selected[key],
            laplace_free=fits["free"]["criterion"],
            laplace_point=fits[key]["criterion"],
        )
        reference = 2 * (fits["free"]["criterion"] - fits[key]["criterion"])
        lower = 2 * (envelopes["free"]["lower"] - envelopes[key]["upper"]) - reference
        upper = 2 * (envelopes["free"]["upper"] - envelopes[key]["lower"]) - reference
        contrasts[key] = {
            "estimate": paired["estimate"],
            "lower": lower,
            "upper": upper,
            "half_width": max(paired["estimate"] - lower, upper - paired["estimate"]),
            "paired_interval": paired,
            "decision_interval": "simultaneous_positive_integral_bounds_through_maximum",
        }
    return {
        "envelopes": envelopes,
        "contrasts": contrasts,
        "weight_gates_passed": all(
            e.diagnostics["weight_gates_passed"] for e in estimates.values()
        ),
        "ownership_resolved": all(e["ownership_resolved"] for e in envelopes.values()),
        "contrast_precision_passed": all(c["half_width"] <= 0.01 for c in contrasts.values()),
    }


def stable_comparison(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return all(
        abs(c["estimate"] - second["contrasts"][k]["estimate"]) <= 0.01
        and max(c["lower"], second["contrasts"][k]["lower"])
        <= min(c["upper"], second["contrasts"][k]["upper"])
        for k, c in first["contrasts"].items()
    )


def decision(primary: dict[str, Any], confirmation: dict[str, Any], stable: bool) -> str:
    qualified = (
        stable
        and stable_comparison(primary, confirmation)
        and all(
            row["weight_gates_passed"] and row["contrast_precision_passed"]
            for row in (primary, confirmation)
        )
    )
    if not qualified:
        return "indeterminate"
    discrepant = any(
        (c["lower"] > 0.10 and confirmation["contrasts"][key]["lower"] > 0.10)
        or (c["upper"] < -0.10 and confirmation["contrasts"][key]["upper"] < -0.10)
        for key, c in primary["contrasts"].items()
    )
    reversal = any(
        row["material_ownership_reversal"]
        and confirmation["envelopes"][key]["material_ownership_reversal"]
        for key, row in primary.get("envelopes", {}).items()
    )
    if discrepant or reversal:
        return "repair_required"
    contained = all(
        c["lower"] >= -0.10 and c["upper"] <= 0.10
        for row in (primary, confirmation)
        for c in row["contrasts"].values()
    )
    return "pointwise_screen_passed" if contained else "indeterminate"


def selected_fits(
    receipt: dict[str, Any], report_h: float
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if receipt["status"] != "profile_numerically_resolved":
        raise ValueError("profile unresolved; fixed-outer screen unavailable")
    diagnostics = receipt["post_search_diagnostics"]
    if diagnostics["status"] != "available":
        raise ValueError("post-search reporting unresolved")
    if not math.isfinite(report_h) or not 1 <= report_h <= 30:
        raise ValueError("reporting h outside the frozen domain")
    fits = {"free": receipt["free"]["True"]}
    anchors: dict[float, list[str]] = {}

    def add(x: float, role: str) -> None:
        same = next((old for old in anchors if abs(old - x) <= 1e-12), x)
        anchors.setdefault(same, []).append(role)

    add(0.0, "null")
    add(math.log(report_h), "generating_h_reported_after_search")
    for family in ("positive_sigma", "sigma_zero"):
        add(math.log(fits["free"][family]["h"]), f"dense_free_{family}")
    levels = [level for level in receipt["tight_level_sets"] if level["cutoff"] == 3.84]
    if len(levels) != 1 or levels[0]["status"] != "available":
        raise ValueError("dense diagnostic roots unavailable")
    for index, root in enumerate(levels[0]["roots"]):
        add(root["log_h"], f"dense_tight_root_{index}")
    retained = []
    for x, roles in sorted(anchors.items()):
        matching = [row for row in diagnostics["points"] if abs(row["log_h"] - x) <= 1e-10]
        if not matching:
            raise ValueError(f"required fixed-outer anchor missing: {roles}")
        row = min(matching, key=lambda point: abs(point["log_h"] - x))
        key = format(row["h"], ".17g")
        fits[key] = row["tight_fit"]
        retained.append({"key": key, "log_h": row["log_h"], "h": row["h"], "roles": roles})
    return fits, retained


def verify_profile_binding(args: argparse.Namespace) -> dict[str, str]:
    parent_path = args.profile.parent.parent / "receipt.json"
    started_path = parent_path.with_name("started.json")
    parent = json.loads(parent_path.read_text())
    started = json.loads(started_path.read_text())
    if parent.get("schema") != "development-profile-run-v1":
        raise ValueError("invalid profile parent receipt")
    search = parent["searches"].get(args.profile.parent.name)
    if search is None or search["sha256"] != adapter.sha256_file(args.profile):
        raise ValueError("profile child receipt binding failed")
    identities = parent["source_input_sha256"]
    if (
        started["source_input_sha256"] != identities
        or args.report_h not in started["report_h_used_only_after_search"]
    ):
        raise ValueError("screen reporting h or inputs differ from the original run")
    required = [
        args.observations,
        args.arrival_bank,
        args.compressed_bank,
        args.input_dir / "public_inputs.npz",
        args.input_dir / "exposure.npz",
    ]
    for path in required:
        if identities.get(str(path.resolve())) != adapter.sha256_file(path):
            raise ValueError("profile and integration inputs differ")
    for name, expected in identities.items():
        if adapter.sha256_file(Path(name)) != expected:
            raise ValueError(f"profile source/input binding changed: {name}")
    return {str(path.resolve()): adapter.sha256_file(path) for path in (parent_path, started_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "input-dir",
        "observations",
        "arrival-bank",
        "compressed-bank",
        "profile",
        "output-dir",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--identity", required=True)
    parser.add_argument("--report-h", type=float, required=True)
    parser.add_argument("--maximum-draws", type=int, default=262144)
    args = parser.parse_args()
    if args.maximum_draws not in (16384, 32768, 65536, 131072, 262144):
        raise ValueError("maximum draws outside frozen doubling schedule")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    sources = [
        Path(__file__),
        Path(adapter.__file__),
        ROOT / "scripts/run_development_profile.py",
        ROOT / "scripts/qualify_spatial_profiles.py",
        ROOT / "scripts/profile_level_sets.py",
        *sorted((ROOT / "src/latent_landscapes").rglob("*.py")),
        args.profile,
        args.observations,
        args.arrival_bank,
        args.compressed_bank,
        args.input_dir / "public_inputs.npz",
        args.input_dir / "exposure.npz",
    ]
    identities = {str(p.resolve()): adapter.sha256_file(p) for p in sources}
    write_json(
        args.output_dir / "started.json",
        {"identity": args.identity, "source_input_sha256": identities},
    )
    try:
        identities.update(verify_profile_binding(args))
        fits, anchors = selected_fits(json.loads(args.profile.read_text()), args.report_h)
        data, data_identity = load_panel_data(args)
        criterion = direct_criterion(data)
        targets = {}
        warm = None
        for key, fit in fits.items():
            row = fit["positive_sigma"]
            targets[key] = prepare_target(
                criterion,
                coordinates(row),
                h=row["h"],
                warm=warm,
                expected_laplace=row["criterion"],
            )
            warm = targets[key].selected_mode
            zero = fit["sigma_zero"]
            replay = criterion.evaluate_sigma_zero(coordinates(zero), fixed_h=zero["h"])
            if not replay.success or abs(replay.criterion - zero["criterion"]) > 1e-4:
                raise RuntimeError("zero-family replay failed")
        history, previous = [], None
        status = "indeterminate"
        draws = 16384
        while draws <= args.maximum_draws:
            streams = []
            for stream in (0, 1):
                estimates = {}
                for key, target in targets.items():
                    estimates[key] = integrate(
                        target, target.proposal, identity=args.identity, stream=stream, draws=draws
                    )
                    write_json(
                        args.output_dir
                        / f"point-{list(targets).index(key):03d}-s{stream}-n{draws}.json",
                        {
                            "key": key,
                            "estimate": estimates[key].summary(),
                            "mode_diagnostics": target.mode_diagnostics,
                        },
                    )
                summary = summarize(estimates, fits)
                streams.append(summary)
            stable = previous is not None and all(
                stable_comparison(a, b) for a, b in zip(previous, streams, strict=True)
            )
            status = decision(streams[0], streams[1], stable)
            level = {
                "draws_per_point_per_stream": draws,
                "streams": streams,
                "doubling_stable": stable,
                "status": status,
            }
            history.append(level)
            write_json(args.output_dir / f"level-{draws}.json", level)
            if status != "indeterminate":
                break
            previous = streams
            draws *= 2
        for path, expected in identities.items():
            if adapter.sha256_file(Path(path)) != expected:
                raise RuntimeError(f"source/input drift: {path}")
        write_json(
            args.output_dir / "receipt.json",
            {
                "schema": "fixed-outer-importance-screen-v1",
                "status": status,
                "reoptimised_profile": False,
                "optimized_root_movement_quantified": False,
                "identity": args.identity,
                "report_h": args.report_h,
                "selected_anchors": anchors,
                "source_input_sha256": identities,
                "data_identity": data_identity,
                "history": history,
                "elapsed_seconds": time.perf_counter() - started,
            },
        )
        print(json.dumps({"status": status, "elapsed_seconds": time.perf_counter() - started}))
    except Exception as error:
        write_json(
            args.output_dir / "failure.json",
            {"status": "indeterminate", "type": type(error).__name__, "message": str(error)},
        )
        raise


if __name__ == "__main__":
    main()
