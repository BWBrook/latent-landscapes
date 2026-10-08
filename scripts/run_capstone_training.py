#!/usr/bin/env python3
"""Run the staged, blinded Goal 061 training analysis."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, cast

import numpy as np

from latent_landscapes import capstone_calibration as calibration
from latent_landscapes import capstone_qualification as qualification
from latent_landscapes import capstone_references as references
from latent_landscapes import capstone_training as training
from latent_landscapes import preinvasion_fitting as fitting
from latent_landscapes.preinvasion_calibration import ScreenResult, ScreenStatus
from latent_landscapes.preinvasion_effect_gate import EffectFitBatch

TRAINING_SHA256 = "a884068ab5a2be36e21ba8c2688a5eff620ea436e60078ea200584eaa614b220"
BINDING_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
ANALYSIS_SCHEMA = "goal061-training-analysis-v1"
AUDIT_SCHEMA = "goal061-stage-audit-v1"


def _sha256(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def _write_json(path: Path, value: Any) -> None:
    references.write_json(path, value)


def _binding(value: str) -> str:
    if not BINDING_PATTERN.fullmatch(value):
        raise ValueError("--binding must be a lowercase 64-character SHA256 digest")
    return value


def _stage(output: Path, mode: str, *, allow_resume: bool) -> Path:
    stage = output / mode
    if stage.exists() and not allow_resume:
        raise FileExistsError(f"preserve existing {mode} stage")
    stage.mkdir(parents=True, exist_ok=True)
    if (stage / f"{mode}.json").exists():
        raise FileExistsError(f"preserve completed {mode} stage")
    return stage


def _training_inputs(args: argparse.Namespace) -> tuple[Path, Path, str]:
    directory = args.training_directory
    npz = directory / "training_observations.npz"
    manifest = directory / "training_manifest.json"
    expected = TRAINING_SHA256
    if args.seal_receipt is not None:
        receipt = json.loads(args.seal_receipt.read_text(encoding="utf-8"))
        records = {str(row.get("name")): row for row in receipt.get("files", [])}
        record = records.get("training_observations.npz")
        if not isinstance(record, dict) or record.get("sha256") != TRAINING_SHA256:
            raise ValueError("seal receipt does not bind the registered training NPZ")
        expected = str(record["sha256"])
    if _sha256(npz) != expected:
        raise ValueError("training NPZ does not match the registered sealed package")
    return npz, manifest, expected


def _load_stage_summary(output: Path, stage: str, binding: str) -> dict[str, Any]:
    path = output / stage / f"{stage}.json"
    if not path.is_file():
        raise ValueError(f"{stage} stage must be complete before this stage")
    summary = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if (
        summary.get("schema") != ANALYSIS_SCHEMA
        or summary.get("mode") != stage
        or summary.get("status") != "complete"
        or summary.get("binding_sha256") != binding
    ):
        raise ValueError(f"{stage} stage is not a complete matching binding")
    return summary


def _load_fit_summary(output: Path, binding: str) -> dict[str, Any]:
    return _load_stage_summary(output, "fit", binding)


def _load_screen_summary(output: Path, binding: str) -> dict[str, Any]:
    return _load_stage_summary(output, "screen", binding)


def _require_audit(
    path: Path | None,
    stage: str,
    *,
    binding: str,
    output: Path,
) -> dict[str, Any]:
    if path is None or not path.is_file():
        raise ValueError(f"{stage} stage requires an independent stage-audit receipt")
    receipt = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if receipt.get("schema") != AUDIT_SCHEMA or receipt.get("kind") != stage:
        raise ValueError(f"{stage} audit receipt has the wrong schema or stage")
    if receipt.get("passed") is not True:
        raise ValueError(f"{stage} audit receipt is not passed")
    if receipt.get("binding_sha256") != binding:
        raise ValueError(f"{stage} audit receipt has the wrong source binding")
    summary_path = output / stage / f"{stage}.json"
    if not summary_path.is_file() or receipt.get("stage_sha256") != _sha256(summary_path):
        raise ValueError(f"{stage} audit receipt does not bind the complete stage summary")
    files = receipt.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError(f"{stage} audit receipt does not list complete stage artifacts")
    summary_name = str(Path(stage) / f"{stage}.json")
    if files.get(summary_name) != receipt.get("stage_sha256"):
        raise ValueError(f"{stage} audit receipt omits its stage summary artifact")
    def scientific_checkpoint(candidate: Path) -> bool:
        return not (
            candidate.name.endswith((".tmp", ".wal", ".shm", "-wal", "-shm"))
            or "progress" in candidate.name
        )

    expected_files = {
        str(candidate.relative_to(output))
        for candidate in (output / stage).rglob("*")
        if candidate.is_file() and scientific_checkpoint(candidate)
    }
    missing_files = expected_files.difference(files)
    if missing_files:
        raise ValueError(f"{stage} audit receipt omits complete stage artifacts")
    for name, expected in files.items():
        relative = Path(str(name))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"{stage} audit receipt contains an unsafe artifact path")
        artifact = output / relative
        if (
            not artifact.is_file()
            or not isinstance(expected, str)
            or _sha256(artifact) != expected
        ):
            raise ValueError(f"{stage} audit receipt artifact hash is stale or incomplete")
    return receipt


def _observed_screen_contrasts(observed: Any) -> np.ndarray:
    """Compute the pre-only screen surface casewise, retaining failed rows."""
    values = np.asarray(observed, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != calibration.GRID_SIZE:
        raise ValueError("observed pre-score surface has the wrong shape")
    contrasts = np.full_like(values, np.nan, dtype=np.float64)
    for index, row in enumerate(values):
        if np.isfinite(row).all():
            contrasts[index] = calibration.local_contrasts(row)
    return contrasts


def run_fit(args: argparse.Namespace) -> dict[str, Any]:
    stage = _stage(args.output, "fit", allow_resume=False)
    package = references.load_context(args.package)
    npz, manifest, training_sha = _training_inputs(args)
    cases = training.load_training(package.public, npz, manifest, training_sha)
    observed_pre = training.observed_pre_scores(package.public, cases)
    pre_path = stage / "observed_pre_scores.npy"
    np.save(pre_path, observed_pre)
    def fit_one(item: tuple[int, str]) -> dict[str, Any]:
        history, case_id = item
        fit_path = stage / "fits"
        row = training.fit_training_case(
            package.public,
            package.bank,
            cases,
            history=history,
            representation="full",
            output=fit_path,
        )
        coarse = training.qualified1350coarse_grid(
            package.public, package.bank, cases, history=history
        )
        coarse_path = stage / "fits" / f"history-{history:02d}-full-coarse-grid.json"
        _write_json(coarse_path, coarse)
        return {
            "case_id": case_id,
            "history": history,
            "fit_json": str(Path("fits") / f"history-{history:02d}-full.json"),
            "coarse_grid_json": str(Path("fits") / coarse_path.name),
            "adjusted_T": row["adjusted_T"],
            "adjusted_validity": row["observed_adjusted_validity"],
            "main_statuses_converged": row["main_statuses_converged"],
        }

    items = tuple(enumerate(cases.case_ids))
    with ThreadPoolExecutor(max_workers=min(4, args.workers)) as pool:
        rows = list(pool.map(fit_one, items))
    summary = {
        "schema": ANALYSIS_SCHEMA,
        "mode": "fit",
        "status": "complete",
        "binding_sha256": args.binding,
        "training_npz_sha256": training_sha,
        "observed_pre_scores": str(Path("observed_pre_scores.npy")),
        "cases": rows,
        "scientific_final_ready": False,
    }
    _write_json(stage / "fit.json", summary)
    return summary


def run_screen(args: argparse.Namespace) -> dict[str, Any]:
    fit_summary = _load_fit_summary(args.output, args.binding)
    stage = _stage(args.output, "screen", allow_resume=True)
    package = references.load_context(args.package)
    observed = np.load(args.output / "fit" / fit_summary["observed_pre_scores"])
    if observed.shape != (4, calibration.GRID_SIZE):
        raise ValueError("fit pre-score surface has the wrong shape")
    observed_contrasts = _observed_screen_contrasts(observed)
    np.save(stage / "observed_screen_contrasts.npy", observed_contrasts)
    ref_dir = stage / "references"
    references.run_nodes(
        "screen",
        args.package,
        ref_dir,
        range(calibration.GRID_SIZE),
        binding=args.binding,
        workers=args.workers,
    )
    reference = references.load_screen_table(ref_dir, binding=args.binding)
    screens = calibration.screen_cases(training.TRAINING_CASE_IDS, observed_contrasts, reference)
    union = calibration.required_effect_nodes(screens)
    summary = {
        "schema": ANALYSIS_SCHEMA,
        "mode": "screen",
        "status": "complete",
        "binding_sha256": args.binding,
        "observed_screen_contrasts": str(Path("observed_screen_contrasts.npy")),
        "cases": qualification.jsonable(screens),
        "required_effect_nodes": list(union),
        "reference_directory": str(Path("references")),
        "scientific_final_ready": False,
        "qualified_package_root": str(args.package),
        "site_count": len(package.site_ids),
    }
    _write_json(stage / "screen.json", summary)
    return summary


def run_effect(args: argparse.Namespace) -> dict[str, Any]:
    screen = _load_screen_summary(args.output, args.binding)
    _require_audit(
        args.screen_audit, "screen", binding=args.binding, output=args.output
    )
    references.load_context(args.package)
    stage = _stage(args.output, "effect", allow_resume=True)
    nodes = tuple(int(value) for value in screen["required_effect_nodes"])
    if nodes != tuple(sorted(set(nodes))) or any(
        value < 0 or value >= calibration.GRID_SIZE for value in nodes
    ):
        raise ValueError("screen union is not the complete valid registered node set")
    rows = references.run_nodes(
        "effect",
        args.package,
        stage / "references",
        nodes,
        binding=args.binding,
        workers=args.workers,
    )
    if len(rows) != len(nodes) or any(row.get("completed") != 999 for row in rows):
        raise RuntimeError("effect reference computation remains incomplete")
    summary = {
        "schema": ANALYSIS_SCHEMA,
        "mode": "effect",
        "status": "complete",
        "binding_sha256": args.binding,
        "required_effect_nodes": list(nodes),
        "reference_directory": str(Path("references")),
        "screen_audit": str(args.screen_audit),
        "scientific_final_ready": False,
    }
    _write_json(stage / "effect.json", summary)
    return summary


def _json_float(value: Any) -> float:
    """Decode qualification.jsonable's null representation for nonfinite floats."""
    return math.nan if value is None else float(value)


def _fit_result(payload: dict[str, Any]) -> fitting.FitResult:
    return fitting.FitResult(
        str(payload["model"]),
        _json_float(payload["h"]),
        _json_float(payload["beta"]),
        _json_float(payload["mu"]),
        _json_float(payload["detection_sd"]),
        _json_float(payload["raw_logjoint"]),
        str(payload["numerical_status"]),
        int(payload.get("nfev", 0)),
        _json_float(payload.get("elapsed_seconds", 0.0)),
    )


def _observed_effect_batch(output: Path, fit_summary: dict[str, Any]) -> EffectFitBatch:
    null: list[float] = []
    free: list[float] = []
    null_status: list[str] = []
    free_status: list[str] = []
    for case in fit_summary["cases"]:
        row = cast(
            dict[str, Any],
            json.loads((output / "fit" / case["fit_json"]).read_text(encoding="utf-8")),
        )
        fits = row["fits"]
        pair = fitting.PairedFitResult(
            _json_float(row["adjusted_T"]),
            {
                "adjusted_h1": _fit_result(fits["adjusted_h1"]),
                "adjusted_free_h": _fit_result(fits["adjusted_free_h"]),
            },
            {"adjusted": _json_float(row["adjusted_T"])},
            fitting.CostSummary(0, 0, 0, 0.0, 0.0, 0.0),
        )
        batch = training.observed_adjusted_effect_batch(pair)
        null.extend(batch.null_loglikelihood)
        free.extend(batch.free_loglikelihood)
        null_status.extend(batch.null_status)
        free_status.extend(batch.free_status)
    return EffectFitBatch(null, free, null_status, free_status)


def run_decide(args: argparse.Namespace) -> dict[str, Any]:
    fit_summary = _load_fit_summary(args.output, args.binding)
    screen = _load_screen_summary(args.output, args.binding)
    effect = _load_stage_summary(args.output, "effect", args.binding)
    _require_audit(
        args.screen_audit, "screen", binding=args.binding, output=args.output
    )
    _require_audit(
        args.effect_audit, "effect", binding=args.binding, output=args.output
    )
    references.load_context(args.package)
    stage = _stage(args.output, "decide", allow_resume=True)
    nodes = tuple(int(value) for value in screen["required_effect_nodes"])
    if effect.get("required_effect_nodes") != list(nodes):
        raise ValueError("effect stage node union differs from the completed screen stage")
    effect_dir = args.output / "effect" / "references"
    batches = {}
    for node in nodes:
        metadata = references._metadata("effect", args.binding, node, calibration.ROOT_SEED, 999)
        batches[node] = references.load_effect_batch(
            effect_dir / f"node-{node:04d}.sqlite", metadata=metadata
        )
    screen_rows = []
    for row in screen["cases"]:
        screen_rows.append(
            ScreenResult(
                str(row["case_id"]),
                cast(ScreenStatus, str(row["status"])),
                tuple(int(value) for value in row["candidate_indices"]),
                None if row["q_values"] is None else np.asarray(row["q_values"], dtype=float),
                row.get("reason"),
            )
        )
    decisions = calibration.combine_effect_tests(
        screen_rows,
        _observed_effect_batch(args.output, fit_summary),
        batches,
        computation_complete=True,
    )
    summary = {
        "schema": ANALYSIS_SCHEMA,
        "mode": "decide",
        "status": "complete",
        "binding_sha256": args.binding,
        "decisions": qualification.jsonable(decisions),
        "screen_audit": str(args.screen_audit),
        "effect_audit": str(args.effect_audit),
        "scientific_final_ready": False,
    }
    _write_json(stage / "decide.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("fit", "screen", "effect", "decide"))
    parser.add_argument("--package", "--qualifiedroot", dest="package", type=Path, required=True)
    parser.add_argument("--training-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--binding", type=_binding, required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--seal-receipt", type=Path)
    parser.add_argument("--screen-audit", type=Path)
    parser.add_argument("--effect-audit", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 1 <= args.workers <= 64:
        raise SystemExit("--workers must be between 1 and 64")
    if args.mode == "fit":
        run_fit(args)
    elif args.mode == "screen":
        run_screen(args)
    elif args.mode == "effect":
        run_effect(args)
    else:
        run_decide(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
