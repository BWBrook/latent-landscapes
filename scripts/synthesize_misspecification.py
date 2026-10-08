#!/usr/bin/env python3
"""Verify Goal 051 production and frozen Goal 050 references, then synthesize."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from latent_landscapes.misspecification_campaign import (
    ARCHIVED_BANK_ROOT,
    GOAL050_CALIBRATION_SHA256,
    GOAL050_DETECTOR_SHA256,
    PRODUCTION_ROOT,
)
from latent_landscapes.misspecification_synthesis import (
    BOOTSTRAP_DRAWS,
    BOOTSTRAP_SEED,
    CELL_IDS,
    TRUTHS,
    write_synthesis,
)


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _json_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _reference_paths(root: Path) -> tuple[Path, Path, dict[str, str]]:
    detector = root / "synthesis" / "detector_values.npz"
    calibration = root / "production" / "output" / "calibration.npz"
    if not detector.is_file() or not calibration.is_file():
        raise ValueError(
            "reference root must contain synthesis/detector_values.npz and "
            "production/output/calibration.npz"
        )
    if _sha256(detector) != GOAL050_DETECTOR_SHA256:
        raise ValueError("frozen Goal 050 detector_values.npz hash changed")
    if _sha256(calibration) != GOAL050_CALIBRATION_SHA256:
        raise ValueError("frozen Goal 050 calibration.npz hash changed")
    synthesis_receipt_path = root / "synthesis" / "receipt.json"
    production_summary_path = root / "production" / "output" / "run_summary.json"
    synthesis_receipt = _json(synthesis_receipt_path)
    production_summary = _json(production_summary_path)
    original_manifest = production_summary.get("original_manifest")
    if (
        synthesis_receipt.get("outputs", {}).get("detector_values.npz")
        != GOAL050_DETECTOR_SHA256
        or production_summary.get("output_hashes", {}).get("calibration.npz")
        != GOAL050_CALIBRATION_SHA256
        or production_summary.get("workflow") != "goal050-model-adequacy"
        or production_summary.get("outcome") != "production_complete"
        or not isinstance(original_manifest, dict)
        or not original_manifest
        or production_summary.get("original_manifest_sha256")
        != _json_sha256(original_manifest)
    ):
        raise ValueError("Goal 050 provenance does not bind the frozen reference artifacts")
    provenance = {
        "goal050_synthesis_receipt_sha256": _sha256(synthesis_receipt_path),
        "goal050_production_summary_sha256": _sha256(production_summary_path),
        "goal049_original_manifest_sha256": production_summary["original_manifest_sha256"],
    }
    return detector, calibration, provenance


def _verify_production(input_dir: Path) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    summary_path = input_dir / "run_summary.json"
    contract_path = input_dir / "run_contract.json"
    frozen_path = input_dir / "frozen_scores.json"
    summary, contract, frozen = _json(summary_path), _json(contract_path), _json(frozen_path)
    config = summary.get("config", {})
    fingerprint = contract.get("run_fingerprint")
    seed_controls = summary.get("seed_controls")
    validation = summary.get("validation")
    source_hashes = summary.get("source_hashes")
    output_hashes = summary.get("output_hashes")
    expected_sources = {
        "src/latent_landscapes/misspecification_generator.py",
        "src/latent_landscapes/misspecification_campaign.py",
        "src/latent_landscapes/misspecification_synthesis.py",
        "scripts/run_misspecification.py",
        "scripts/synthesize_misspecification.py",
        "docs/goals/051-misspecification-screen/registration-2026-09-23.md",
    }
    required_validation = {
        "profiles_shape",
        "holdout_shape",
        "score_shapes",
        "all_main_arrays_finite",
        "profile_minimum_zero",
        "mle_matches_lowest_index",
        "grid_is_registered",
        "cell_ids_in_registered_order",
        "truths_in_registered_order",
        "opaque_ids_nonempty_unique",
    }
    if (
        summary.get("workflow") != "goal051-misspecification-screen"
        or summary.get("outcome") != "production_complete"
        or config.get("mode") != "production"
        or config.get("replicates") != 1000
        or config.get("campaign_root") != PRODUCTION_ROOT
        or config.get("bank_root") != ARCHIVED_BANK_ROOT
        or config.get("bank_size") != 131_072
        or config.get("bootstrap_root") != BOOTSTRAP_SEED
        or not np.array_equal(
            np.asarray(config.get("effects"), dtype=np.float64),
            1.0 + 0.05 * np.arange(181),
        )
        or summary.get("workers") != 8
        or tuple(summary.get("cell_ids", ())) != CELL_IDS
        or not np.array_equal(np.asarray(summary.get("cell_truths"), dtype=float), TRUTHS)
        or summary.get("pairing")
        != {"complete_replicate_unit": True, "cells_per_replicate": 17}
        or not isinstance(seed_controls, dict)
        or not seed_controls
        or not all(value is True for value in seed_controls.values())
        or not isinstance(validation, dict)
        or not required_validation.issubset(validation)
        or not all(validation[name] is True for name in required_validation)
        or validation.get("seed_controls") != seed_controls
        or not isinstance(source_hashes, dict)
        or not expected_sources.issubset(source_hashes)
        or not isinstance(output_hashes, dict)
        or "campaign_arrays.npz" not in output_hashes
        or summary.get("run_fingerprint") != fingerprint
        or _json_sha256({key: value for key, value in contract.items() if key != "run_fingerprint"})
        != fingerprint
    ):
        raise ValueError("input is not the complete registered Goal 051 production run")
    for key in (
        "schema_version", "workflow", "config", "cell_ids", "cell_truths",
        "source_hashes", "reference_manifest", "bank_provenance", "seed_controls",
        "workers", "pairing", "run_fingerprint",
    ):
        if summary.get(key) != contract.get(key):
            raise ValueError(f"run summary and contract disagree: {key}")
    if (
        frozen.get("metadata_joined") is not True
        or frozen.get("endpoints_evaluated") is not False
        or frozen.get("run_fingerprint") != fingerprint
        or tuple(frozen.get("cell_ids", ())) != CELL_IDS
        or frozen.get("files") != summary.get("output_hashes")
        or _sha256(frozen_path) != summary.get("frozen_scores_sha256")
    ):
        raise ValueError("frozen analyst score manifest is not bound to the production run")
    for name, digest in output_hashes.items():
        if _sha256(input_dir / name) != digest:
            raise ValueError(f"production output hash changed: {name}")

    repository = Path(__file__).resolve().parents[1]
    for name, digest in source_hashes.items():
        path = Path(name) if Path(name).is_absolute() else repository / name
        if not path.is_file() or _sha256(path) != digest:
            raise ValueError(f"source-bound input changed after production: {name}")

    arrays_path = input_dir / "campaign_arrays.npz"
    with np.load(arrays_path, allow_pickle=False) as archive:
        arrays = {name: np.asarray(archive[name]) for name in archive.files}
    required = {
        "profiles", "holdout_joint", "prey_score", "predator_score", "mle_index",
        "opaque_ids", "cell_ids", "truths",
    }
    if not required.issubset(arrays):
        raise ValueError(f"campaign_arrays.npz lacks {sorted(required - arrays.keys())}")
    if tuple(arrays["cell_ids"].tolist()) != CELL_IDS or not np.array_equal(
        arrays["truths"], TRUTHS
    ):
        raise ValueError("campaign array cell identities differ from the frozen contract")
    expected_shapes = {
        "profiles": (17, 1000, 181),
        "holdout_joint": (17, 1000, 181),
        "prey_score": (17, 1000),
        "predator_score": (17, 1000),
        "mle_index": (17, 1000),
        "opaque_ids": (17, 1000),
    }
    for name, shape in expected_shapes.items():
        if arrays[name].shape != shape:
            raise ValueError(f"{name} must have complete production shape {shape}")
    return summary, arrays


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.output_dir.exists():
        raise ValueError(f"refusing to overwrite existing synthesis: {args.output_dir}")
    summary, arrays = _verify_production(args.input_dir)
    detector_path, calibration_path, reference_provenance = _reference_paths(args.reference_dir)
    reference_manifest = summary.get("reference_manifest", {})
    if (
        reference_manifest.get("detector_sha256") != GOAL050_DETECTOR_SHA256
        or reference_manifest.get("calibration_sha256") != GOAL050_CALIBRATION_SHA256
    ):
        raise ValueError("production was not bound to the registered Goal 050 references")
    with np.load(detector_path, allow_pickle=False) as detector:
        effect_cutoffs = np.asarray(detector["original_effect_cutoffs"])
        c99_cutoffs = np.asarray(detector["original_c99_cutoffs"])
    with np.load(calibration_path, allow_pickle=False) as calibration:
        reference_scores = np.asarray(calibration["prey_score"])
    diagnostics = {
        name.removeprefix("diagnostic_"): value
        for name, value in arrays.items()
        if name.startswith("diagnostic_")
    }
    result = write_synthesis(
        args.output_dir,
        np.asarray(summary["config"]["effects"], dtype=np.float64),
        arrays["cell_ids"],
        arrays["truths"],
        arrays["profiles"],
        arrays["prey_score"],
        arrays["predator_score"],
        arrays["mle_index"],
        arrays["holdout_joint"],
        arrays["opaque_ids"],
        reference_scores,
        effect_cutoffs,
        c99_cutoffs,
        draws=BOOTSTRAP_DRAWS,
        seed=BOOTSTRAP_SEED,
        metadata={
            "production_run_fingerprint": summary["run_fingerprint"],
            "production_arrays_sha256": _sha256(args.input_dir / "campaign_arrays.npz"),
            "goal050_detector_sha256": GOAL050_DETECTOR_SHA256,
            "goal050_calibration_sha256": GOAL050_CALIBRATION_SHA256,
        },
        diagnostics=diagnostics,
    )
    source = (
        Path(__file__).resolve().parents[1]
        / "src/latent_landscapes/misspecification_synthesis.py"
    )
    receipt = {
        "scope": "Goal 051 registered 17-cell paired misspecification synthesis",
        "input_run_summary_sha256": _sha256(args.input_dir / "run_summary.json"),
        "input_run_contract_sha256": _sha256(args.input_dir / "run_contract.json"),
        "input_frozen_scores_sha256": _sha256(args.input_dir / "frozen_scores.json"),
        "input_campaign_arrays_sha256": _sha256(args.input_dir / "campaign_arrays.npz"),
        "goal050_detector_sha256": _sha256(detector_path),
        "goal050_calibration_sha256": _sha256(calibration_path),
        **reference_provenance,
        "script_sha256": _sha256(Path(__file__)),
        "synthesis_source_sha256": _sha256(source),
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "outputs": {
            path.name: _sha256(path)
            for path in sorted(args.output_dir.iterdir())
            if path.is_file()
        },
    }
    (args.output_dir / "verification_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result.summary["nomination"], indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Goal 051 synthesis failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
