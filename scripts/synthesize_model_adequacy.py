#!/usr/bin/env python3
"""Verify Goal 049/050 identities, then synthesize the registered detector."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.model_adequacy_synthesis import (
    BOOTSTRAP_DRAWS,
    BOOTSTRAP_SEED,
    CALIBRATION_REPLICATES,
    EVALUATION_REPLICATES,
    write_synthesis,
)

PRIMARY_VARIANT = "high_k131072_alpha100"
PHASES = ("calibration", "evaluation", "new_calibration", "new_evaluation")


def _file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _json_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _verify_goal049(
    original: Path,
) -> tuple[dict[str, Any], NDArray[np.float64], NDArray[np.float64]]:
    summary_path = original / "run_summary.json"
    contract_path = original / "run_contract.json"
    frozen_path = original / "frozen_scores.json"
    summary = _load_json(summary_path)
    contract = _load_json(contract_path)
    frozen = _load_json(frozen_path)
    config = contract.get("config", {})
    if (
        summary.get("outcome") != "production_scores_complete"
        or contract.get("workflow") != "goal049-known-nuisance-calibration"
        or config.get("calibration_replicates") != CALIBRATION_REPLICATES
        or config.get("evaluation_replicates") != EVALUATION_REPLICATES
        or config.get("calibration_rank") != 950
        or frozen.get("truth_joined") is not False
        or frozen.get("files") != summary.get("score_file_sha256")
        or not summary.get("identity_controls")
        or not all(value is True for value in summary["identity_controls"].values())
    ):
        raise ValueError("Goal 049 production contract is not the registered source")
    names = (
        f"calibration_profiles_{PRIMARY_VARIANT}.npy",
        f"evaluation_profiles_{PRIMARY_VARIANT}.npy",
        f"evaluation_holdout_loglikelihood_{PRIMARY_VARIANT}.npy",
        "calibration_opaque_ids.npy",
        "evaluation_opaque_ids.npy",
    )
    file_hashes: dict[str, str] = {}
    for name in names:
        digest = _file_sha256(original / name)
        if frozen["files"].get(name) != digest:
            raise ValueError(f"Goal 049 frozen input changed: {name}")
        file_hashes[name] = digest
    calibration = np.load(original / names[0], allow_pickle=False)
    evaluation = np.load(original / names[1], allow_pickle=False)
    if calibration.shape != (181, 999, 181) or evaluation.shape != (6, 1000, 181):
        raise ValueError("Goal 049 primary profiles differ from the full-grid contract")
    if (
        calibration.dtype != np.dtype("float64")
        or evaluation.dtype != np.dtype("float64")
        or not np.isfinite(calibration).all()
        or not np.isfinite(evaluation).all()
        or (calibration < 0).any()
        or (evaluation < 0).any()
    ):
        raise ValueError("Goal 049 profiles are not finite nonnegative float64 LR values")
    manifest = {
        "run_contract": contract,
        "run_summary": summary,
        "frozen_scores": frozen,
        "source_and_registration_sha256": summary.get("source_and_registration_sha256"),
        "file_hashes": file_hashes,
    }
    return manifest, calibration, evaluation


def _load_goal050(
    input_dir: Path, original_manifest: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, dict[str, NDArray[Any]]]]:
    summary_path = input_dir / "run_summary.json"
    summary = _load_json(summary_path)
    contract = _load_json(input_dir / "run_contract.json")
    config = summary.get("config", {})
    expected_counts = (
        config.get("original_calibration_replicates"),
        config.get("original_evaluation_replicates"),
        config.get("fresh_calibration_replicates"),
        config.get("fresh_evaluation_replicates"),
    )
    if (
        summary.get("outcome") != "production_complete"
        or summary.get("workflow") != "goal050-model-adequacy"
        or config.get("mode") != "production"
        or expected_counts != (999, 1000, 999, 1000)
        or config.get("synthesis_root") != BOOTSTRAP_SEED
        or summary.get("pairing", {}).get("truths_within_replicate") is not True
        or summary.get("original_manifest_sha256") != _json_sha256(original_manifest)
        or summary.get("original_manifest") != original_manifest
        or summary.get("run_fingerprint") != contract.get("run_fingerprint")
        or _json_sha256({key: value for key, value in contract.items() if key != "run_fingerprint"})
        != contract.get("run_fingerprint")
    ):
        raise ValueError("Goal 050 run summary differs from the registered production contract")
    for key in (
        "schema_version",
        "workflow",
        "config",
        "phase_roots",
        "primary_variant",
        "bank_provenance",
        "source_and_registration_sha256",
        "original_manifest_sha256",
        "pairing",
    ):
        if summary.get(key) != contract.get(key):
            raise ValueError(f"Goal 050 run summary and contract disagree: {key}")
    repository = Path(__file__).resolve().parents[1]
    declared_sources = summary.get("source_and_registration_sha256", {})
    synthesis_name = "src/latent_landscapes/model_adequacy_synthesis.py"
    script_name = "scripts/synthesize_model_adequacy.py"
    registration_name = "docs/goals/050-model-adequacy/registration-2026-09-20.md"
    for name in (synthesis_name, script_name, registration_name):
        if declared_sources.get(name) != _file_sha256(repository / name):
            raise ValueError(f"Goal 050 registered source changed after production: {name}")
    replay = summary.get("replay_controls", {})
    for phase in ("calibration", "evaluation"):
        controls = replay.get(phase, {}).get("controls", {})
        if not controls or not all(value is True for value in controls.values()):
            raise ValueError(f"Goal 050 replay identity did not pass: {phase}")

    result: dict[str, dict[str, NDArray[Any]]] = {}
    expected_keys = {
        "calibration": {"prey_score", "predator_score", "mle_index"},
        "evaluation": {"prey_score", "predator_score", "mle_index"},
        "new_calibration": {"prey_score", "predator_score", "mle_index", "profiles"},
        "new_evaluation": {"prey_score", "predator_score", "mle_index", "profiles"},
    }
    fingerprint = str(summary.get("run_fingerprint", ""))
    for phase in PHASES:
        path = input_dir / f"{phase}.npz"
        with np.load(path, allow_pickle=False) as loaded:
            if str(loaded.get("source_fingerprint", "")) != fingerprint:
                raise ValueError(f"{phase}.npz is not bound to the completed run")
            keys = set(loaded.files) - {"source_fingerprint"}
            if keys != expected_keys[phase]:
                raise ValueError(f"{phase}.npz has wrong keys: {sorted(keys)}")
            arrays = {name: np.asarray(loaded[name]) for name in expected_keys[phase]}
        declared = summary.get("output_hashes", {}).get(f"{phase}.npz")
        if declared != _file_sha256(path):
            raise ValueError(f"{phase}.npz does not match its run_summary hash")
        result[phase] = arrays
    return summary, result


def _require_mle_identity(
    phase: str, mle: NDArray[Any], profiles: NDArray[np.float64]
) -> None:
    if mle.shape != profiles.shape[:-1] or not np.array_equal(mle, np.argmin(profiles, axis=-1)):
        raise ValueError(f"{phase} fitted indices do not match first/lowest profile maximizers")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True, help="Goal 050 production output")
    parser.add_argument(
        "--original-output-dir", type=Path, required=True, help="Goal 049 production output"
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="new synthesis directory")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    original_manifest, original_calibration_profiles, original_evaluation_profiles = (
        _verify_goal049(args.original_output_dir)
    )
    run_summary, phases = _load_goal050(args.input_dir, original_manifest)
    _require_mle_identity(
        "calibration", phases["calibration"]["mle_index"], original_calibration_profiles
    )
    _require_mle_identity(
        "evaluation", phases["evaluation"]["mle_index"], original_evaluation_profiles
    )
    _require_mle_identity(
        "new_calibration",
        phases["new_calibration"]["mle_index"],
        phases["new_calibration"]["profiles"],
    )
    _require_mle_identity(
        "new_evaluation",
        phases["new_evaluation"]["mle_index"],
        phases["new_evaluation"]["profiles"],
    )
    effects = np.asarray(run_summary["config"]["effects"], dtype=np.float64)
    truths = np.asarray(run_summary["config"]["evaluation_truths"], dtype=np.float64)
    result = write_synthesis(
        args.output_dir,
        effects,
        truths,
        original_calibration_profiles,
        original_evaluation_profiles,
        phases["calibration"]["prey_score"],
        phases["evaluation"]["prey_score"],
        phases["calibration"]["predator_score"],
        phases["evaluation"]["predator_score"],
        phases["new_calibration"]["profiles"],
        phases["new_evaluation"]["profiles"],
        phases["new_calibration"]["prey_score"],
        phases["new_evaluation"]["prey_score"],
        phases["new_calibration"]["predator_score"],
        phases["new_evaluation"]["predator_score"],
        draws=BOOTSTRAP_DRAWS,
        seed=BOOTSTRAP_SEED,
    )
    source = (
        Path(__file__).resolve().parents[1]
        / "src/latent_landscapes/model_adequacy_synthesis.py"
    )
    receipt = {
        "scope": "Goal 050 registered finite-grid detector and crossed-null synthesis",
        "input_run_summary_sha256": _file_sha256(args.input_dir / "run_summary.json"),
        "input_run_contract_sha256": _file_sha256(args.input_dir / "run_contract.json"),
        "input_phase_file_sha256": {
            f"{phase}.npz": _file_sha256(args.input_dir / f"{phase}.npz") for phase in PHASES
        },
        "original_run_summary_sha256": _file_sha256(
            args.original_output_dir / "run_summary.json"
        ),
        "original_frozen_scores_sha256": _file_sha256(
            args.original_output_dir / "frozen_scores.json"
        ),
        "script_sha256": _file_sha256(Path(__file__)),
        "synthesis_source_sha256": _file_sha256(source),
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "outputs": {
            path.name: _file_sha256(path)
            for path in sorted(args.output_dir.iterdir())
            if path.is_file()
        },
    }
    (args.output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result.summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
