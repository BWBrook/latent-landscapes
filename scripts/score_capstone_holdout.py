#!/usr/bin/env python3
"""Score the released capstone holdout against the four frozen fits.

This is a deliberately small adapter around the qualified capstone modules.  It
loads no truth material, never refits, and writes a new result directory.  The
production invocation is expected to run with ``PYTHONPATH`` pointing at the
frozen source checkout.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import itertools
import json
import platform
import resource
import sys
import tarfile
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np

from latent_landscapes import capstone_qualification as qualification
from latent_landscapes import capstone_references as references
from latent_landscapes import capstone_training as training
from latent_landscapes import preinvasion_fitting as fitting
from latent_landscapes import preinvasion_likelihood as likelihood

MODEL_NAMES = tuple(qualification.MODEL_NAMES)
CASE_IDS = tuple(f"case-{index:02d}" for index in range(4))
SITE_COUNT = 160
TRAINING_COUNT = 120
HOLDOUT_COUNT = 40
PREY_VISITS = 13
PREDATOR_VISITS = 6
HOLDOUT_SHA256 = "53903e56b0b86d8d713bf643d9c3062e8ce918fa8b84afa48f9b8ace6859fe6a"
PREDICTED_PAIRS = {
    "case-00": ("adjusted_free_h", "adjusted_h1"),
    "case-01": ("adjusted_free_h", "adjusted_h1"),
    "case-02": ("constant_free_h", "adjusted_free_h"),
    "case-03": ("adjusted_free_h", "adjusted_h1"),
}


@dataclass(frozen=True, slots=True)
class HoldoutArrays:
    case_ids: tuple[str, ...]
    site_ids: tuple[str, ...]
    prey_counts: np.ndarray
    predator_counts: np.ndarray


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _count_array(value: Any, *, shape: tuple[int, int, int], name: str) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != shape or not np.issubdtype(array.dtype, np.integer):
        raise ValueError(f"{name} must have integer shape {shape}")
    if not np.isin(array, (0, 1, 2)).all():
        raise ValueError(f"{name} must contain only two-visit counts 0, 1 or 2")
    return np.asarray(array, dtype=np.int64)


def load_holdout_archive(
    archive_path: Path, *, expected_sha256: str = HOLDOUT_SHA256
) -> HoldoutArrays:
    """Read and validate only the released salted holdout archive."""
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    actual = sha256(archive_path)
    if actual != expected_sha256:
        raise ValueError(f"holdout archive hash mismatch: {actual}")
    with tarfile.open(archive_path, mode="r") as archive:
        names = tuple(member.name for member in archive.getmembers())
        if set(names) != {"holdout.npz", "padding.bin", "salt.bin"}:
            raise ValueError("holdout archive members do not match the released schema")
        salt = archive.extractfile("salt.bin")
        payload = archive.extractfile("holdout.npz")
        if salt is None or payload is None or len(salt.read()) != 32:
            raise ValueError("holdout archive salt or payload is malformed")
        with np.load(BytesIO(payload.read()), allow_pickle=False) as values:
            required = {"case_ids", "site_ids", "prey_counts", "predator_counts"}
            if set(values.files) != required:
                raise ValueError("holdout.npz contains undocumented or missing arrays")
            case_ids = tuple(str(value) for value in np.asarray(values["case_ids"]).reshape(-1))
            site_ids = tuple(str(value) for value in np.asarray(values["site_ids"]).reshape(-1))
            prey = _count_array(
                values["prey_counts"],
                shape=(4, HOLDOUT_COUNT, PREY_VISITS),
                name="holdout prey_counts",
            )
            predator = _count_array(
                values["predator_counts"],
                shape=(4, HOLDOUT_COUNT, PREDATOR_VISITS),
                name="holdout predator_counts",
            )
    if case_ids != CASE_IDS:
        raise ValueError("holdout case identifiers are not the four registered cases")
    if len(site_ids) != HOLDOUT_COUNT or len(set(site_ids)) != HOLDOUT_COUNT:
        raise ValueError("holdout site identifiers are not unique 40-site IDs")
    return HoldoutArrays(case_ids, site_ids, prey, predator)


def _training_inputs(training_root: Path) -> tuple[Path, Path, str]:
    directory = training_root / "training-inputs"
    npz = directory / "training_observations.npz"
    manifest = directory / "training_manifest.json"
    if not npz.is_file() or not manifest.is_file():
        raise FileNotFoundError(
            "training-inputs/training_observations.npz and training_manifest.json"
        )
    return npz, manifest, sha256(npz)


def merge_observations(
    public: Any, training_cases: training.TrainingCases, holdout: HoldoutArrays
) -> likelihood.PreInvasionObservations:
    """Place training and holdout arrays into the frozen public site order."""
    public_ids = tuple(str(value) for value in public.setup.site_ids)
    splits = tuple(str(value) for value in public.setup.site_splits)
    if len(public_ids) != SITE_COUNT or public_ids != tuple(sorted(public_ids)):
        raise ValueError("public inputs do not contain the canonical 160-site order")
    if splits.count("training") != TRAINING_COUNT or splits.count("holdout") != HOLDOUT_COUNT:
        raise ValueError("public split is not the registered 120/40 design")
    if training_cases.case_ids != CASE_IDS or holdout.case_ids != CASE_IDS:
        raise ValueError("training and holdout case order differs")
    training_ids = tuple(
        site for site, split in zip(public_ids, splits, strict=True) if split == "training"
    )
    holdout_ids = tuple(
        site for site, split in zip(public_ids, splits, strict=True) if split == "holdout"
    )
    if training_cases.observations.site_ids != training_ids:
        raise ValueError("training site IDs do not match the public split")
    if holdout.site_ids != holdout_ids:
        raise ValueError("holdout site IDs do not match the public split or order")
    prey = np.empty((4, SITE_COUNT, PREY_VISITS), dtype=np.int64)
    predator = np.empty((4, SITE_COUNT, PREDATOR_VISITS), dtype=np.int64)
    training_mask = np.asarray(splits, dtype="U16") == "training"
    prey[:, training_mask] = training_cases.observations.prey_counts
    prey[:, ~training_mask] = holdout.prey_counts
    predator[:, training_mask] = training_cases.observations.predator_counts
    predator[:, ~training_mask] = holdout.predator_counts
    return likelihood.prepare_observations(prey, predator, public_ids, training_mask)


def _fit_result(model: str, payload: dict[str, Any]) -> fitting.FitResult:
    required = {"model", "h", "beta", "mu", "detection_sd", "raw_logjoint", "numerical_status"}
    if not required <= payload.keys() or payload.get("model") != model:
        raise ValueError(f"fit payload for {model} is incomplete or misbound")

    def number(value: Any) -> float:
        return float(value) if value is not None else float("nan")

    return fitting.FitResult(
        model=model,
        h=number(payload["h"]),
        beta=number(payload["beta"]),
        mu=number(payload["mu"]),
        detection_sd=number(payload["detection_sd"]),
        raw_logjoint=number(payload["raw_logjoint"]),
        numerical_status=str(payload["numerical_status"]),
        nfev=int(payload.get("nfev", 0)),
        elapsed_seconds=float(payload.get("elapsed_seconds", 0.0)),
        objective_gap=number(payload.get("objective_gap", np.nan)),
        boundary_flags=tuple(str(value) for value in payload.get("boundary_flags", ())),
        warnings=tuple(str(value) for value in payload.get("warnings", ())),
    )


def load_frozen_panel(training_root: Path, history: int) -> dict[str, Any]:
    if type(history) is not int or not 0 <= history < 4:
        raise ValueError("history must be one of the four registered histories")
    fit_directory = training_root / "analysis" / "fit" / "fits"
    audit_path = training_root / "analysis" / "audits" / "training" / f"history-{history:02d}.json"
    main_path = fit_directory / f"history-{history:02d}-full-main.json"
    full_path = fit_directory / f"history-{history:02d}-full.json"
    main = _load_json(main_path)
    full = _load_json(full_path)
    audit = _load_json(audit_path)
    if (
        main.get("history") != history
        or full.get("history") != history
        or audit.get("history") != history
    ):
        raise ValueError("fit and audit history binding differs")
    if main.get("representation") != "full" or full.get("representation") != "full":
        raise ValueError("holdout scoring requires the full frozen bank fit")
    if set(main.get("fits", {})) != set(MODEL_NAMES) or set(full.get("fits", {})) != set(
        MODEL_NAMES
    ):
        raise ValueError("frozen fit panel does not contain exactly four models")
    if full["fits"] != main["fits"]:
        raise ValueError("full fit and main fit parameter records differ")
    input_files = audit.get("input_files", {})
    expected_full = input_files.get(f"analysis/fit/fits/history-{history:02d}-full.json")
    if expected_full is not None and sha256(full_path) != expected_full:
        raise ValueError("full fit hash differs from its training audit")
    if audit.get("case_id") != f"case-{history:02d}" or audit.get("kind") != "training_case":
        raise ValueError("training audit case binding is invalid")
    fits = {model: _fit_result(model, main["fits"][model]) for model in MODEL_NAMES}
    return {
        "history": history,
        "main": main,
        "full": full,
        "audit": audit,
        "fits": fits,
        "paths": {"main": main_path, "full": full_path, "audit": audit_path},
    }


def _source_hashes(training_root: Path) -> dict[str, str]:
    manifest_path = training_root / "source-manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = _load_json(manifest_path)
    source_root = training_root / "source"
    expected = manifest.get("source_hashes", {})
    if not isinstance(expected, dict):
        raise ValueError("source manifest has no source hash mapping")
    actual: dict[str, str] = {}
    for module_name in (
        "capstone_references",
        "capstone_qualification",
        "capstone_training",
        "preinvasion_fitting",
        "preinvasion_likelihood",
    ):
        module = importlib.import_module(f"latent_landscapes.{module_name}")
        source = Path(str(module.__file__)).resolve()
        try:
            relative = source.relative_to(source_root.resolve())
        except ValueError:
            relative = Path("src") / "latent_landscapes" / source.name
        key = str(relative)
        digest = sha256(source)
        actual[key] = digest
        if key not in expected or expected[key] != digest:
            raise ValueError(f"frozen module hash mismatch: {key}")
    if not isinstance(manifest.get("frozen_input_hashes"), dict):
        raise ValueError("source manifest has no frozen input hash mapping")
    actual["source-manifest.json"] = sha256(manifest_path)
    return actual


def _verify_computation_manifest(training_root: Path, panels: list[dict[str, Any]]) -> str:
    """Check only the small set of fit/audit files used by this adapter."""
    path = training_root / "analysis" / "computation-complete.json"
    manifest = _load_json(path)
    if manifest.get("schema") != "goal061-blinded-training-computation-v1":
        raise ValueError("completed computation manifest has an unexpected schema")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("completed computation manifest has no file hash mapping")
    for panel in panels:
        for _kind, file_path in panel["paths"].items():
            relative = file_path.relative_to(training_root)
            expected = files.get(str(relative))
            if expected is None or sha256(file_path) != expected:
                raise ValueError(f"fit or audit hash differs from completed manifest: {relative}")
    return sha256(path)


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def score_holdout(
    public_root: Path,
    training_root: Path,
    holdout_archive: Path,
    output: Path,
    *,
    training_lock: Path,
) -> dict[str, Any]:
    """Score all cases and publish JSON plus tidy CSVs to a new directory."""
    started = time.perf_counter()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    context = references.load_context(public_root, verify=True)
    holdout = load_holdout_archive(holdout_archive)
    training_npz, training_manifest, training_sha = _training_inputs(training_root)
    lock = _load_json(training_lock)
    source_manifest_path = training_root / "source-manifest.json"
    expected_source = lock.get("source_manifest_sha256")
    if expected_source is None or sha256(source_manifest_path) != expected_source:
        raise ValueError("source manifest hash differs from the training lock")
    source_manifest = _load_json(source_manifest_path)
    frozen_inputs = source_manifest.get("frozen_input_hashes")
    if not isinstance(frozen_inputs, dict):
        raise ValueError("source manifest has no frozen input hash mapping")
    expected_inputs = {
        "training-inputs/training_observations.npz": training_sha,
        "training-inputs/training_manifest.json": sha256(training_manifest),
    }
    for relative, actual in expected_inputs.items():
        if frozen_inputs.get(relative) != actual:
            raise ValueError(f"frozen training input hash mismatch: {relative}")
    fit_summary = _load_json(training_root / "analysis" / "fit" / "fit.json")
    expected_training_sha = fit_summary.get("training_npz_sha256")
    if expected_training_sha is not None and training_sha != expected_training_sha:
        raise ValueError("training observations hash differs from the frozen fit summary")
    cases = training.load_training(context.public, training_npz, training_manifest, training_sha)
    observed = merge_observations(context.public, cases, holdout)
    panels = [load_frozen_panel(training_root, history) for history in range(4)]
    source_hashes = _source_hashes(training_root)
    computation_manifest_hash = _verify_computation_manifest(training_root, panels)
    expected_computation = next(
        (
            child.get("manifest_sha256")
            for child in lock.get("child_manifests", [])
            if child.get("role") == "completed_training_analysis"
        ),
        None,
    )
    if expected_computation is None or computation_manifest_hash != expected_computation:
        raise ValueError("completed computation manifest hash differs from the training lock")
    lock_hash = sha256(training_lock)

    totals: list[dict[str, Any]] = []
    site_rows: list[dict[str, Any]] = []
    cluster_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    forecast_rows: list[dict[str, Any]] = []
    case_results: list[dict[str, Any]] = []
    holdout_ids = holdout.site_ids
    for history, panel in enumerate(panels):
        case_id = f"case-{history:02d}"
        model_results: dict[str, Any] = {}
        for model in MODEL_NAMES:
            fit = panel["fits"][model]
            fit_payload = panel["main"]["fits"][model]
            valid = bool(
                fit.converged
                and np.isfinite([fit.h, fit.beta, fit.mu, fit.detection_sd, fit.raw_logjoint]).all()
                and panel["full"].get("main_statuses_converged", {}).get(model) is True
            )
            score = None
            if valid:
                score = qualification._heldout_row(
                    context.public, context.bank, observed, fit, history=history
                )
            row: dict[str, Any] = {
                "status": "available" if score is not None else "unavailable",
                "fit_status": fit.numerical_status,
                "fit": fit_payload,
                "diagnostic_flags": {
                    "main_statuses_converged": panel["full"]
                    .get("main_statuses_converged", {})
                    .get(model),
                    "audit_passed": panel["audit"].get("passed"),
                    "diagnostic_passed": panel["audit"].get("diagnostic_passed"),
                    "diagnostics_change_declaration": panel["audit"].get(
                        "diagnostics_change_declaration"
                    ),
                },
            }
            if score is not None:
                row.update(
                    total_nats=float(score["conditional_prey_total_nats"]),
                    mean_nats_per_site=float(score["conditional_prey_nats_per_site"]),
                    site_nats=[float(value) for value in score["conditional_prey_site_nats"]],
                    cluster_nats={
                        str(k): float(v) for k, v in score["cluster_contributions_nats"].items()
                    },
                )
                totals.append(
                    {
                        "case_id": case_id,
                        "model": model,
                        "status": row["status"],
                        "fit_status": fit.numerical_status,
                        "total_nats": row["total_nats"],
                        "mean_nats_per_site": row["mean_nats_per_site"],
                    }
                )
                cluster_by_site = dict(
                    zip(
                        tuple(str(value) for value in context.public.setup.site_ids),
                        tuple(str(value) for value in context.public.setup.site_cluster_ids),
                        strict=True,
                    )
                )
                for site_id, value in zip(holdout_ids, row["site_nats"], strict=True):
                    site_rows.append(
                        {
                            "case_id": case_id,
                            "model": model,
                            "site_id": site_id,
                            "cluster_id": cluster_by_site[site_id],
                            "nats": value,
                        }
                    )
                for cluster, value in row["cluster_nats"].items():
                    cluster_rows.append(
                        {
                            "case_id": case_id,
                            "model": model,
                            "cluster_id": cluster,
                            "nats": value,
                        }
                    )
            else:
                totals.append(
                    {
                        "case_id": case_id,
                        "model": model,
                        "status": row["status"],
                        "fit_status": fit.numerical_status,
                        "total_nats": None,
                        "mean_nats_per_site": None,
                    }
                )
            model_results[model] = row
        available = {
            model: result.get("total_nats")
            for model, result in model_results.items()
            if result.get("total_nats") is not None
        }
        winner_set = (
            [
                model
                for model in MODEL_NAMES
                if model in available
                and available[model] == max(available.values(), default=-np.inf)
            ]
            if len(available) == len(MODEL_NAMES)
            else None
        )
        predicted = PREDICTED_PAIRS[case_id]
        pair_hit = bool(set(predicted).intersection(winner_set)) if winner_set is not None else None
        margin = None
        if winner_set is not None:
            ordered = sorted(available.values(), reverse=True)
            margin = float(ordered[0] - ordered[1])
        co_winners_outside = (
            [model for model in winner_set if model not in predicted]
            if winner_set is not None
            else None
        )
        forecast_rows.append(
            {
                "case_id": case_id,
                "predicted_left": predicted[0],
                "predicted_right": predicted[1],
                "winner_set": ";".join(winner_set) if winner_set is not None else None,
                "pair_hit": pair_hit,
                "winning_margin_nats": margin,
                "co_winners_outside_predicted_pair": (
                    ";".join(co_winners_outside) if co_winners_outside is not None else None
                ),
                "named_two_of_four": True,
            }
        )
        case_pair_rows = []
        for left, right in itertools.combinations(MODEL_NAMES, 2):
            difference = (
                available[left] - available[right]
                if left in available and right in available
                else None
            )
            case_pair_rows.append(
                {"left": left, "right": right, "left_minus_right_nats": difference}
            )
            pair_rows.append(
                {
                    "case_id": case_id,
                    "left_model": left,
                    "right_model": right,
                    "left_minus_right_nats": difference,
                }
            )
        case_results.append(
            {
                "case_id": case_id,
                "history": history,
                "fits": model_results,
                "winner_set": winner_set,
                "predicted_pair": predicted,
                "pair_hit": pair_hit,
                "winning_margin_nats": margin,
                "co_winners_outside_predicted_pair": co_winners_outside,
                "named_two_of_four": True,
                "pair_differences": case_pair_rows,
            }
        )

    result = {
        "schema": "goal061-capstone-holdout-score-v1",
        "holdout_archive_sha256": sha256(holdout_archive),
        "training_observations_sha256": training_sha,
        "computation_manifest_sha256": computation_manifest_hash,
        "training_lock_sha256": lock_hash,
        "public_root": str(public_root),
        "training_root": str(training_root),
        "source_hashes": source_hashes,
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": importlib.import_module("scipy").__version__,
            "elapsed_seconds": time.perf_counter() - started,
            "max_rss_bytes": int(
                resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                * (1 if sys.platform == "darwin" else 1024)
            ),
            "adapter_script_sha256": sha256(Path(__file__).resolve()),
            "modules": {
                name: sha256(
                    Path(str(importlib.import_module(f"latent_landscapes.{name}").__file__))
                )
                for name in (
                    "capstone_references",
                    "capstone_qualification",
                    "preinvasion_fitting",
                    "preinvasion_likelihood",
                )
            },
        },
        "models": list(MODEL_NAMES),
        "cases": case_results,
    }
    (output / "scores.json").write_text(
        json.dumps(_jsonable(result), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        output / "totals.csv",
        totals,
        ("case_id", "model", "status", "fit_status", "total_nats", "mean_nats_per_site"),
    )
    _write_csv(
        output / "site_contributions.csv",
        site_rows,
        ("case_id", "model", "site_id", "cluster_id", "nats"),
    )
    _write_csv(
        output / "cluster_contributions.csv",
        cluster_rows,
        ("case_id", "model", "cluster_id", "nats"),
    )
    _write_csv(
        output / "pair_differences.csv",
        pair_rows,
        ("case_id", "left_model", "right_model", "left_minus_right_nats"),
    )
    _write_csv(
        output / "forecast_records.csv",
        forecast_rows,
        (
            "case_id",
            "predicted_left",
            "predicted_right",
            "winner_set",
            "pair_hit",
            "winning_margin_nats",
            "co_winners_outside_predicted_pair",
            "named_two_of_four",
        ),
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-root", type=Path, required=True)
    parser.add_argument("--training-root", type=Path, required=True)
    parser.add_argument("--holdout-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--training-lock", type=Path, required=True)
    args = parser.parse_args(argv)
    score_holdout(
        args.public_root,
        args.training_root,
        args.holdout_archive,
        args.output,
        training_lock=args.training_lock,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
