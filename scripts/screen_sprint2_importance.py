"""Describe capped fixed-outer integration at a frozen fit's free point and 3.84 roots."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import benchmark_spatial_profile as adapter
import screen_spatial_importance as screen_helpers
from qualify_spatial_profiles import write_json
from run_development_profile import load_panel_data
from screen_spatial_importance import coordinates, decision, stable_comparison, summarize

from latent_landscapes.importance_reference import integrate
from latent_landscapes.spatial_importance_reference import direct_criterion, prepare_target

SCHEMA = "sprint2-integration-screen-v1"
MAXIMUM_DRAWS = 262144


def selected_fits(search: dict[str, Any]) -> dict[str, Any]:
    if search["status"] != "profile_numerically_resolved":
        raise ValueError("unresolved spatial search")
    level = next(v for v in search["tight_level_sets"] if v["cutoff"] == 3.84)
    if level["status"] != "available":
        raise ValueError("unavailable 3.84 set")
    points = {row["log_h"]: row for row in search["points"]["True"]}
    return {
        "free": search["free"]["True"],
        **{f"root-{i}": points[root["log_h"]] for i, root in enumerate(level["roots"])},
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    parent = json.loads(args.receipt.read_text())
    parent_hash = adapter.sha256_file(args.receipt)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "fit_receipt_sha256": parent_hash,
        "identity": args.identity,
        "descriptive_only": True,
        "reoptimised_profile": False,
        "optimized_root_movement_quantified": False,
        "maximum_draws": MAXIMUM_DRAWS,
        "status": "unavailable",
        "history": [],
        "criterion": "normalised_eigenvalue_floor_Laplace_composite",
    }
    if parent.get("schema") != "fit-dataset-v1":
        raise ValueError("wrong parent fit schema")
    if parent.get("failure_class") == "execution_error":
        raise OSError("parent fit has an unreconciled execution error")
    if parent.get("failure_class") not in {
        "resolved",
        "numerical_error",
        "family_fit_failed",
        "search_unresolved",
        "multimodal_latent",
    }:
        raise ValueError("unknown parent failure class")
    if parent.get("failure_class") != "resolved":
        result["status"] = "unavailable_scientific_fit"
        result["reason"] = f"parent scientific failure: {parent.get('failure_class')}"
        write_json(args.output_dir / "receipt.json", result)
        return result
    identities = dict(parent["input_sha256"])
    search_path = Path(parent["search"]["receipt"])
    identities[str(search_path)] = parent["search"]["receipt_sha256"]
    identities[str(args.receipt.resolve())] = parent_hash
    identities[str(Path(__file__).resolve())] = adapter.sha256_file(Path(__file__))
    helper = Path(screen_helpers.__file__).resolve()
    identities[str(helper)] = adapter.sha256_file(helper)
    for path, expected in identities.items():
        if adapter.sha256_file(Path(path)) != expected:
            raise ValueError(f"source/input drift: {path}")
    source = parent["source"]
    if not source.get("commit") or source.get("working_tree_changes") != []:
        raise ValueError("integration requires a clean committed parent source")
    if source != adapter._git_identity(Path(__file__).resolve().parents[1]):
        raise ValueError("integration source differs from the frozen fit")
    result["source_input_sha256"] = identities
    inputs = argparse.Namespace(**{k: Path(v) for k, v in parent["inputs"].items()})
    data, result["data_identity"] = load_panel_data(inputs)
    if result["data_identity"] != parent["data_identity"]:
        raise ValueError("integration data identity differs from the frozen fit")
    try:
        fits = selected_fits(json.loads(search_path.read_text()))
        result["selected_anchors"] = [
            {"key": key, "positive_h": fit["positive_sigma"]["h"], "zero_h": fit["sigma_zero"]["h"]}
            for key, fit in fits.items()
        ]
        criterion = direct_criterion(data)
        targets = {}
        for key, fit in fits.items():
            positive, zero = fit["positive_sigma"], fit["sigma_zero"]
            targets[key] = prepare_target(
                criterion,
                coordinates(positive),
                h=positive["h"],
                expected_laplace=positive["criterion"],
            )
            replay = criterion.evaluate_sigma_zero(coordinates(zero), fixed_h=zero["h"])
            if not replay.success or abs(replay.criterion - zero["criterion"]) > 1e-4:
                raise RuntimeError("zero-family replay failed")
        previous = None
        draws = 16384
        while draws <= MAXIMUM_DRAWS:
            streams = []
            for stream in (0, 1):
                estimates = {}
                for number, (key, target) in enumerate(targets.items()):
                    estimates[key] = integrate(
                        target,
                        target.proposal,
                        identity=args.identity,
                        stream=stream,
                        draws=draws,
                    )
                    write_json(
                        args.output_dir / f"point-{number:03d}-s{stream}-n{draws}.json",
                        {
                            "key": key,
                            "estimate": estimates[key].summary(),
                            "mode_diagnostics": target.mode_diagnostics,
                        },
                    )
                streams.append(summarize(estimates, fits))
            stable = previous is not None and all(
                stable_comparison(a, b) for a, b in zip(previous, streams, strict=True)
            )
            status = (
                "no_root_contrasts" if len(fits) == 1 else decision(streams[0], streams[1], stable)
            )
            level = {
                "draws_per_point_per_stream": draws,
                "streams": streams,
                "doubling_stable": stable,
                "status": status,
            }
            result["history"].append(level)
            write_json(args.output_dir / f"level-{draws}.json", level)
            result["status"] = status
            if status != "indeterminate":
                break
            previous = streams
            draws *= 2
    except (MemoryError, OSError):
        raise
    except (ValueError, RuntimeError, FloatingPointError, KeyError) as error:
        result.update(status="unavailable", reason=f"{type(error).__name__}: {error}")
    for path, expected in identities.items():
        if adapter.sha256_file(Path(path)) != expected:
            raise ValueError(f"source/input drift: {path}")
    result["elapsed_seconds"] = time.perf_counter() - started
    write_json(args.output_dir / "receipt.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--identity", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps({"status": result["status"], "descriptive_only": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
