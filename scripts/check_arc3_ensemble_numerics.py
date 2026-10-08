#!/usr/bin/env python3
"""Compare selected and doubled-bank Arc 3 campaign bundles.

The comparison is conditional on the saved maps, histories, grids, and seed
schedule.  It checks the prospective numerical limits; it does not rerun a
campaign or turn a reduced pilot into scientific evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import arc2c_campaign as arc2c
from latent_landscapes import arc3_campaign as arc3
from latent_landscapes.arc3_synthesis import load_map_bundle

try:
    from arc3_bank_adoption import validate_adoption
except ModuleNotFoundError:  # importlib-loaded focused tests do not add scripts/ to sys.path
    _adoption_spec = importlib.util.spec_from_file_location(
        "arc3_bank_adoption", Path(__file__).with_name("arc3_bank_adoption.py")
    )
    if _adoption_spec is None or _adoption_spec.loader is None:
        raise
    _adoption_module = importlib.util.module_from_spec(_adoption_spec)
    sys.modules[_adoption_spec.name] = _adoption_module
    _adoption_spec.loader.exec_module(_adoption_module)
    validate_adoption = _adoption_module.validate_adoption

FloatArray = NDArray[np.float64]

EFFECT_CUTOFF_LIMIT = 0.5
ENDPOINT_CELL_LIMIT = 1
EFFECT_MLE_CELL_LIMIT = 1
RHO_MLE_CELL_LIMIT = 2
PROFILE_LR_LIMIT = 0.5
TRUTH_LR_LIMIT = 0.5
MEAN_ABS_LOG_ERROR_LIMIT = 0.005
MEAN_LOG_WIDTH_LIMIT = 0.01
CONDITIONAL_ADVANTAGE_LIMIT = 0.0001
COUNT_LIMIT = 1
PRODUCTION_REPLICATES = 250
PRODUCTION_RHO_POINTS = 201
PRODUCTION_EFFECT_POINTS = 181
PRODUCTION_RHOS = np.exp2(np.linspace(-2.0, 2.0, PRODUCTION_RHO_POINTS))
PRODUCTION_EFFECTS = np.linspace(1.0, 10.0, PRODUCTION_EFFECT_POINTS)


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _seed_rows(value: Any, name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError(f"seed provenance has invalid {name}")
    return value


def _load_checked(directory: Path) -> dict[str, Any]:
    """Load a campaign bundle and independently reconcile its receipts."""
    bundle = load_map_bundle(directory)
    summary = _json(directory / "run_summary.json")
    seeds = _json(directory / "seed_provenance.json")
    profile_path = directory / "profiles.npz"
    if summary.get("profile_bundle_sha256") != _sha256(profile_path):
        raise ValueError(f"{directory}: profile receipt does not reconcile")
    bank_path = directory / arc3.BANK_FILENAME
    bank = np.ascontiguousarray(np.load(bank_path, allow_pickle=False), dtype=np.float64)
    manifest = arc2c.spawn_seed_manifest(bundle.config)
    expected_bank_seeds = list(manifest.bank_seeds)
    expected_calibration = [asdict(row) for row in manifest.calibration]
    expected_validation = [asdict(row) for row in manifest.validation]
    digest = hashlib.sha256(bank.tobytes(order="C")).hexdigest()
    if bank.shape != (bundle.config.bank_size, len(seeds.get("site_ids", []))):
        raise ValueError(f"{directory}: arrival bank shape disagrees with site receipt")
    if not np.isfinite(bank).all() or (bank < 0).any():
        raise ValueError(f"{directory}: arrival bank contains invalid values")
    counts = summary.get("counts")
    expected_counts = {
        "conditions": 6,
        "designs": 2,
        "effects_per_design": 3,
        "lanes": 2,
        "union_sites": len(seeds.get("site_ids", [])),
        "sites_per_design": 160,
        "training_sites": 120,
        "holdout_sites": 40,
        "bank_draws": bundle.config.bank_size,
        "calibration_datasets_per_condition": bundle.config.calibration_replicates,
        "validation_datasets_per_condition": bundle.config.validation_replicates,
    }
    if not isinstance(counts, dict) or any(
        counts.get(name) != value for name, value in expected_counts.items()
    ):
        raise ValueError(f"{directory}: campaign counts do not reconcile")
    if (
        seeds.get("master_seed") != bundle.config.master_seed
        or seeds.get("bank_size") != bundle.config.bank_size
        or seeds.get("bank_seeds") != expected_bank_seeds
        or _seed_rows(seeds.get("calibration_seeds"), "calibration_seeds") != expected_calibration
        or _seed_rows(seeds.get("validation_seeds"), "validation_seeds") != expected_validation
        or seeds.get("bank_checksum") != digest
        or summary.get("bank_checksum") != digest
    ):
        raise ValueError(f"{directory}: seed or bank receipt does not reconcile")
    if summary.get("scene_metadata") != seeds.get("scene_metadata"):
        raise ValueError(f"{directory}: scene metadata differs between receipts")
    if summary.get("source_commit") != seeds.get("source_commit"):
        raise ValueError(f"{directory}: source commit differs between receipts")
    if summary.get("source_provenance") != seeds.get("source_provenance"):
        raise ValueError(f"{directory}: source provenance differs between receipts")
    return {
        "directory": directory,
        "bundle": bundle,
        "summary": summary,
        "seeds": seeds,
        "bank": bank,
    }


def _same_fixed_inputs(selected: dict[str, Any], doubled: dict[str, Any]) -> None:
    left, right = selected["bundle"], doubled["bundle"]
    fields = ("master_seed", "calibration_replicates", "validation_replicates", "calibration_rank")
    if any(getattr(left.config, field) != getattr(right.config, field) for field in fields):
        raise ValueError("selected and doubled bundles do not share the campaign configuration")
    if left.config.rhos != right.config.rhos or left.config.effects != right.config.effects:
        raise ValueError("selected and doubled bundles do not share candidate grids")
    if right.config.bank_size != 2 * left.config.bank_size:
        raise ValueError("doubled bundle bank size is not twice the selected bank size")
    if left.truths != right.truths:
        raise ValueError("selected and doubled bundles do not share ordered truths")
    for name in ("scene_metadata", "source_commit", "source_provenance"):
        if selected["summary"].get(name) != doubled["summary"].get(name):
            raise ValueError(f"selected and doubled bundles differ in {name}")
    if selected["seeds"].get("site_ids") != doubled["seeds"].get("site_ids"):
        raise ValueError("selected and doubled bundles differ in site IDs")
    left_counts = selected["summary"]["counts"]
    right_counts = doubled["summary"]["counts"]
    for name in left_counts:
        if name != "bank_draws" and left_counts.get(name) != right_counts.get(name):
            raise ValueError(f"selected and doubled bundles differ in {name} count")
    for name in ("calibration_seeds", "validation_seeds"):
        if selected["seeds"].get(name) != doubled["seeds"].get(name):
            raise ValueError(f"selected and doubled bundles differ in {name}")
    left_bank, right_bank = selected["bank"], doubled["bank"]
    if right_bank.shape[1] != left_bank.shape[1] or not np.array_equal(
        right_bank[: left_bank.shape[0]], left_bank
    ):
        raise ValueError("doubled arrival bank does not preserve the selected prefix")
    if doubled["seeds"].get("bank_seeds", [])[: left.config.bank_size] != selected["seeds"].get(
        "bank_seeds"
    ):
        raise ValueError("doubled bank seed schedule does not preserve the selected prefix")


def _cutoffs(bundle: Any) -> FloatArray:
    profiles = bundle.profiles
    rank = bundle.config.calibration_rank - 1
    values = np.asarray(profiles["calibration_effect_lr"], dtype=np.float64)
    return np.asarray(np.partition(values, rank, axis=-1)[..., rank], dtype=np.float64)


def _support(bundle: Any, cutoffs: FloatArray) -> dict[str, Any]:
    profiles = bundle.profiles
    grid = np.asarray(profiles["effects"], dtype=np.float64)
    truths = np.asarray([truth.effect for truth in bundle.truths], dtype=np.float64)
    drops = np.asarray(profiles["validation_effect_drops"], dtype=np.float64)
    mask = drops <= cutoffs[:, :, None, None]
    if not mask.any(axis=-1).all():
        raise ValueError("a calibrated effect support is empty")
    truth_indices = np.asarray(
        [np.flatnonzero(np.isclose(grid, value, atol=1e-12, rtol=0))[0] for value in truths]
    )
    first = np.argmax(mask, axis=-1)
    last = grid.size - 1 - np.argmax(mask[..., ::-1], axis=-1)
    components = mask[..., 0].astype(np.int64) + np.sum(mask[..., 1:] & ~mask[..., :-1], axis=-1)
    truth_present = np.take_along_axis(mask, truth_indices[:, None, None, None], axis=-1)[..., 0]
    lower, upper = mask[..., 0], mask[..., -1]
    return {
        "mask": mask,
        "first": first,
        "last": last,
        "components": components,
        "lower": lower,
        "upper": upper,
        "boundary": lower | upper,
        "truth_present": truth_present,
        "coverage_count": truth_present.sum(axis=-1),
        "exclusion_count": (~lower).sum(axis=-1),
        "log_width": np.log(grid[last] / grid[first]),
    }


def _profile_change(old: FloatArray, new: FloatArray, radius: float) -> float:
    old_drop = 2.0 * (float(np.max(old)) - old)
    new_drop = 2.0 * (float(np.max(new)) - new)
    near = (old_drop <= radius) | (new_drop <= radius)
    if not np.any(near):
        raise ValueError("stored profiles have no finite comparison region")
    return float(np.max(np.abs(old_drop[near] - new_drop[near])))


def _truth_lrs(joint: FloatArray, rho: int, effect: int) -> FloatArray:
    return np.asarray(
        (
            2.0 * (joint[rho].max() - joint[rho, effect]),
            2.0 * (joint.max() - joint[:, effect].max()),
            2.0 * (joint.max() - joint[rho].max()),
        ),
        dtype=np.float64,
    )


def _surface_review(
    selected: Any, doubled: Any, effect_radius: float, rho_radius: float = 10.0
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    rhos = np.asarray(selected.config.rhos)
    effects = np.asarray(selected.config.effects)
    for phase, key in (
        ("calibration", "calibration_train_joint"),
        ("evaluation", "validation_train_joint"),
    ):
        left = selected.profiles[key]
        right = doubled.profiles[key]
        if left.shape[1] < 2 or right.shape[1] < 2:
            raise ValueError("saved joint surfaces do not retain two histories per phase")
        for history in range(2):
            for condition, truth in enumerate(selected.truths):
                old, new = left[condition, history], right[condition, history]
                true_rho = int(np.flatnonzero(np.isclose(rhos, truth.rho, atol=1e-12, rtol=0))[0])
                true_effect = int(
                    np.flatnonzero(np.isclose(effects, truth.effect, atol=1e-12, rtol=0))[0]
                )
                old_rho_raw, old_effect_raw = np.unravel_index(np.argmax(old), old.shape)
                new_rho_raw, new_effect_raw = np.unravel_index(np.argmax(new), new.shape)
                old_rho, old_effect = int(old_rho_raw), int(old_effect_raw)
                new_rho, new_effect = int(new_rho_raw), int(new_effect_raw)
                old_known = int(np.argmax(old[true_rho]))
                new_known = int(np.argmax(new[true_rho]))
                old_rho_profile, new_rho_profile = old.max(axis=1), new.max(axis=1)
                rows.append(
                    {
                        "phase": phase,
                        "history": history,
                        "condition_id": truth.condition_id,
                        "effect_mle_cells": int(
                            max(abs(new_effect - old_effect), abs(new_known - old_known))
                        ),
                        "rho_mle_cells": int(abs(new_rho - old_rho)),
                        "profile_lr_change_known_effect": _profile_change(
                            old[true_rho], new[true_rho], effect_radius
                        ),
                        "profile_lr_change_estimated_effect": _profile_change(
                            old.max(axis=0), new.max(axis=0), effect_radius
                        ),
                        "profile_lr_change_rho": _profile_change(
                            old_rho_profile, new_rho_profile, rho_radius
                        ),
                        "truth_lr_changes": np.abs(
                            _truth_lrs(old, true_rho, true_effect)
                            - _truth_lrs(new, true_rho, true_effect)
                        ).tolist(),
                    }
                )
    for row in rows:
        row["truth_lr_max_change"] = float(max(row["truth_lr_changes"]))
        row["within_limits"] = bool(
            row["effect_mle_cells"] <= EFFECT_MLE_CELL_LIMIT
            and row["rho_mle_cells"] <= RHO_MLE_CELL_LIMIT
            and max(
                row["profile_lr_change_known_effect"],
                row["profile_lr_change_estimated_effect"],
                row["profile_lr_change_rho"],
            )
            <= PROFILE_LR_LIMIT
            and row["truth_lr_max_change"] <= TRUTH_LR_LIMIT
        )
    return {"rows": rows, "all_within_limits": all(row["within_limits"] for row in rows)}


def _support_review_rows(
    selected_support: dict[str, Any],
    doubled_support: dict[str, Any],
    endpoint_delta: NDArray[Any],
    truths: Any,
) -> list[dict[str, Any]]:
    rows = []
    for condition, truth in enumerate(truths):
        for lane, lane_name in enumerate(("known_speed", "estimated_speed")):
            rows.append(
                {
                    "condition_id": truth.condition_id,
                    "lane": lane_name,
                    "support_components_unchanged": bool(
                        np.array_equal(
                            selected_support["components"][condition, lane],
                            doubled_support["components"][condition, lane],
                        )
                    ),
                    "lower_boundary_unchanged": bool(
                        np.array_equal(
                            selected_support["lower"][condition, lane],
                            doubled_support["lower"][condition, lane],
                        )
                    ),
                    "upper_boundary_unchanged": bool(
                        np.array_equal(
                            selected_support["upper"][condition, lane],
                            doubled_support["upper"][condition, lane],
                        )
                    ),
                    "boundary_classification_unchanged": bool(
                        np.array_equal(
                            selected_support["boundary"][condition, lane],
                            doubled_support["boundary"][condition, lane],
                        )
                    ),
                    "max_endpoint_cell_change": int(endpoint_delta[condition, lane].max()),
                    "coverage_count_delta": int(
                        np.max(
                            np.abs(
                                doubled_support["coverage_count"][condition, lane]
                                - selected_support["coverage_count"][condition, lane]
                            )
                        )
                    ),
                    "exclusion_count_delta": int(
                        np.max(
                            np.abs(
                                doubled_support["exclusion_count"][condition, lane]
                                - selected_support["exclusion_count"][condition, lane]
                            )
                        )
                    ),
                }
            )
    return rows


def _production_eligible(
    selected: dict[str, Any], doubled: dict[str, Any], adoption: dict[str, Any] | None = None
) -> bool:
    def frozen_scene(record: dict[str, Any], role: str) -> bool:
        summary = record["summary"]
        scene = summary.get("scene_metadata")
        source = summary.get("source_provenance")
        if (
            summary.get("mode") != "production"
            or summary.get("is_production") is not True
            or not isinstance(scene, dict)
            or not isinstance(source, dict)
        ):
            return False
        freeze = scene.get("production_freeze")
        freeze_sha = scene.get("production_freeze_sha256")
        if not isinstance(freeze, dict) or not isinstance(freeze_sha, str):
            return False
        if (
            source.get("production_freeze_sha256") != freeze_sha
            or source.get("production_freeze") != freeze
        ):
            return False
        try:
            _, canonical_sha = arc3.validate_production_freeze(
                record["bundle"].config, scene, freeze
            )
        except (TypeError, ValueError):
            return False
        expected_bank_size = freeze.get(
            "selected_bank_size" if role == "selected" else "reference_bank_size"
        )
        return (
            canonical_sha == freeze_sha and record["bundle"].config.bank_size == expected_bank_size
        )

    selected_role = "reference" if adoption is not None else "selected"
    return frozen_scene(selected, selected_role) and frozen_scene(doubled, "reference")


def _paired_contrast_review(
    selected: dict[str, FloatArray], doubled: dict[str, FloatArray]
) -> tuple[dict[str, float], dict[str, int], bool]:
    delta = {name: float(np.max(np.abs(doubled[name] - selected[name]))) for name in selected}
    count_delta = {
        name: int(np.max(np.abs(doubled[name] - selected[name])))
        for name in ("coverage_count", "exclusion_count")
    }
    within = (
        delta["mean_absolute_log_error"] <= MEAN_ABS_LOG_ERROR_LIMIT
        and delta["mean_log_width"] <= MEAN_LOG_WIDTH_LIMIT
        and delta["conditional_advantage"] <= CONDITIONAL_ADVANTAGE_LIMIT
        and count_delta["coverage_count"] <= COUNT_LIMIT
        and count_delta["exclusion_count"] <= COUNT_LIMIT
    )
    return delta, count_delta, within


def _contrast_metrics(bundle: Any, support: dict[str, Any]) -> dict[str, FloatArray]:
    profiles = bundle.profiles
    effects = np.asarray([truth.effect for truth in bundle.truths])
    error = np.abs(np.log(profiles["validation_effect_mle"] / effects[:, None, None])).mean(axis=-1)
    width = support["log_width"].mean(axis=-1)
    conditional = profiles["conditional_advantage"].mean(axis=-1)
    coverage = support["coverage_count"] / bundle.config.validation_replicates
    exclusion = support["exclusion_count"] / bundle.config.validation_replicates

    def paired(values: FloatArray) -> FloatArray:
        return values[3:6] - values[:3]

    return {
        "mean_absolute_log_error": paired(error),
        "mean_log_width": paired(width),
        "conditional_advantage": paired(conditional),
        "coverage": paired(coverage),
        "exclusion": paired(exclusion),
        "coverage_count": paired(support["coverage_count"]),
        "exclusion_count": paired(support["exclusion_count"]),
    }


def _write_csv(path: Path, report: dict[str, Any]) -> None:
    rows = []
    for row in report["surface_review"]["rows"]:
        rows.append(
            {"section": "surface", **row, "truth_lr_changes": json.dumps(row["truth_lr_changes"])}
        )
    for row in report["support_review"]["rows"]:
        rows.append({"section": "support", **row})
    if not rows:
        return
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_check(
    selected_dir: Path,
    reference_dir: Path,
    output: Path,
    adoption_receipt: Path | None = None,
) -> dict[str, Any]:
    """Compare a selected-bank bundle with its nested doubled-bank bundle."""
    adoption = (
        validate_adoption(selected_dir, reference_dir, adoption_receipt)
        if adoption_receipt is not None
        else None
    )
    selected = _load_checked(selected_dir)
    doubled = _load_checked(reference_dir)
    if adoption is None:
        _same_fixed_inputs(selected, doubled)
    left, right = selected["bundle"], doubled["bundle"]
    selected_cutoffs = _cutoffs(left)
    doubled_cutoffs = _cutoffs(right)
    cutoff_delta = np.abs(doubled_cutoffs - selected_cutoffs)
    selected_support = _support(left, selected_cutoffs)
    doubled_support = _support(right, doubled_cutoffs)
    endpoint_delta = np.maximum(
        np.abs(doubled_support["first"] - selected_support["first"]),
        np.abs(doubled_support["last"] - selected_support["last"]),
    )
    support_rows = _support_review_rows(
        selected_support, doubled_support, endpoint_delta, left.truths
    )
    support_pass = all(
        row["support_components_unchanged"]
        and row["lower_boundary_unchanged"]
        and row["upper_boundary_unchanged"]
        and row["max_endpoint_cell_change"] <= ENDPOINT_CELL_LIMIT
        and row["coverage_count_delta"] <= COUNT_LIMIT
        and row["exclusion_count_delta"] <= COUNT_LIMIT
        for row in support_rows
    )
    selected_contrasts = _contrast_metrics(left, selected_support)
    doubled_contrasts = _contrast_metrics(right, doubled_support)
    contrast_delta, contrast_count_delta, contrast_pass = _paired_contrast_review(
        selected_contrasts, doubled_contrasts
    )
    validation_count = left.config.validation_replicates
    max_cutoff = float(max(selected_cutoffs.max(), doubled_cutoffs.max()))
    effect_core_radius = max(10.0, max_cutoff)
    surface_review = _surface_review(left, right, effect_core_radius)
    production_eligible = _production_eligible(selected, doubled, adoption)
    checks = {
        "effect_cutoff_movement": float(cutoff_delta.max()) <= EFFECT_CUTOFF_LIMIT,
        "support_and_count_stability": support_pass,
        "paired_sampling_contrasts": contrast_pass,
        "stored_joint_surface_review": surface_review["all_within_limits"],
    }
    all_pass = all(checks.values())
    status = (
        "ensemble_numerical_checks_passed"
        if production_eligible and all_pass
        else ("diagnostic_only" if all_pass else "numerical_review_failed")
    )
    report: dict[str, Any] = {
        "workflow": "arc3-ensemble-numerical-review",
        "status": status,
        "production_eligible": production_eligible,
        "diagnostic_only": not production_eligible,
        "scientific_acceptance_authorized": False,
        "selected_dir": str(selected_dir),
        "reference_dir": str(reference_dir),
        "adoption": adoption,
        "receipts": {
            "selected": {
                "profile_bundle_sha256": selected["summary"]["profile_bundle_sha256"],
                "bank_checksum": selected["summary"]["bank_checksum"],
                "scene_metadata": selected["summary"]["scene_metadata"],
                "source_commit": selected["summary"]["source_commit"],
                "source_provenance": selected["summary"]["source_provenance"],
            },
            "reference": {
                "profile_bundle_sha256": doubled["summary"]["profile_bundle_sha256"],
                "bank_checksum": doubled["summary"]["bank_checksum"],
                "scene_metadata": doubled["summary"]["scene_metadata"],
                "source_commit": doubled["summary"]["source_commit"],
                "source_provenance": doubled["summary"]["source_provenance"],
            },
        },
        "bank_sizes": [left.config.bank_size, right.config.bank_size],
        "core_lr_radius": effect_core_radius,
        "effect_profile_lr_radius": effect_core_radius,
        "rho_profile_lr_radius": 10.0,
        "extended_core_review": max_cutoff > 10.0,
        "half_grid_review_required": True,
        "limits": {
            "effect_cutoff_lr": EFFECT_CUTOFF_LIMIT,
            "support_endpoint_cells": ENDPOINT_CELL_LIMIT,
            "effect_mle_cells": EFFECT_MLE_CELL_LIMIT,
            "rho_mle_cells": RHO_MLE_CELL_LIMIT,
            "profile_lr": PROFILE_LR_LIMIT,
            "truth_lr": TRUTH_LR_LIMIT,
            "paired_mean_absolute_log_error": MEAN_ABS_LOG_ERROR_LIMIT,
            "paired_mean_log_width": MEAN_LOG_WIDTH_LIMIT,
            "paired_conditional_advantage": CONDITIONAL_ADVANTAGE_LIMIT,
            "paired_count_contrast_max_delta": COUNT_LIMIT,
            "paired_count_contrast_proportion": 1.0 / validation_count,
        },
        "checks": checks,
        "all_checks_pass": all_pass,
        "effect_cutoff_review": {
            "max_absolute_lr_change": float(cutoff_delta.max()),
            "selected": selected_cutoffs.tolist(),
            "doubled": doubled_cutoffs.tolist(),
        },
        "support_review": {"rows": support_rows, "all_within_limits": support_pass},
        "paired_contrast_review": {
            "max_absolute_change": contrast_delta,
            "max_count_change": contrast_count_delta,
            "selected": {name: values.tolist() for name, values in selected_contrasts.items()},
            "doubled": {name: values.tolist() for name, values in doubled_contrasts.items()},
            "within_limits": contrast_pass,
        },
        "surface_review": surface_review,
        "full_ensemble_review_required": not production_eligible,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_csv(output.with_suffix(".csv"), report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected-dir", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument(
        "--adoption-receipt",
        type=Path,
        default=None,
        help="explicit immutable old-reference to new-reference adoption receipt",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run_check(
            args.selected_dir,
            args.reference_dir,
            args.output,
            adoption_receipt=args.adoption_receipt,
        )
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(1, f"Arc 3 ensemble numerical review failed: {error}\n")
    print(
        json.dumps(
            {
                "status": report["status"],
                "all_checks_pass": report["all_checks_pass"],
                "output": str(args.output),
            }
        )
    )
    return 0 if report["all_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
