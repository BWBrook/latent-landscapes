"""Separate empirical-bank doubling from its change in seven-pseudo mass."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import benchmark_spatial_profile as adapter
import numpy as np
from qualify_spatial_profiles import (
    FAMILIES,
    ROOT,
    load_data,
    parameters,
    validate_bank_identity,
    write_json,
)

from latent_landscapes.differentiable_likelihood import prepare_site_likelihood
from latent_landscapes.preinvasion_likelihood import compress_bank
from latent_landscapes.spatial_profile import SpatialProfileCriterion


def duplicate_bank(parent_manifest: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads(parent_manifest.read_text())
    product = manifest["products"]["A"]
    if (
        manifest.get("state") != "complete"
        or product["row_start"] != 131072
        or product["row_stop_exclusive"] != 262144
    ):
        raise ValueError("A must be the completed prespecified independent seed block")
    raw_path = Path(product["raw_path"])
    source = np.load(raw_path, mmap_mode="r", allow_pickle=False)
    if source.shape != (131072, len(product["site_ids"])):
        raise ValueError("A must have K=131072 rows")
    if adapter.sha256_file(raw_path) != product["raw_sha256"]:
        raise ValueError("source A file identity mismatch")
    if (
        hashlib.sha256(np.ascontiguousarray(source).view(np.uint8)).hexdigest()
        != product["bank_checksum"]
    ):
        raise ValueError("source A array checksum mismatch")
    values = np.concatenate((source, source), axis=0)
    bank = compress_bank(values, product["site_ids"], series_order=192)
    output.mkdir(parents=True)
    np.save(output / "arrivals.npy", values)
    np.savez_compressed(
        output / "compressed.npz",
        site_ids=np.array(bank.site_ids),
        bank_size=bank.bank_size,
        category_counts=bank.category_counts,
        category_mass=bank.category_mass,
        power_moments=bank.power_moments,
        bank_checksum=bank.bank_checksum,
        series_order=192,
        max_x=40.0,
    )
    result = {
        "schema": "profile-pseudo-mass-duplication-v1",
        "bank_role": "Adup",
        "bank_size": bank.bank_size,
        "site_ids": list(bank.site_ids),
        "bank_checksum": bank.bank_checksum,
        "raw_path": str((output / "arrivals.npy").resolve()),
        "raw_sha256": adapter.sha256_file(output / "arrivals.npy"),
        "compressed_path": str((output / "compressed.npz").resolve()),
        "compressed_sha256": adapter.sha256_file(output / "compressed.npz"),
        "duplication_factor": 2,
        "root": 2026100403,
        "namespace": 59,
        "stage": 3,
        "row_start": 131072,
        "row_stop_exclusive": 262144,
        "duplication_of_A": {
            "raw_path": str(raw_path.resolve()),
            "raw_sha256": adapter.sha256_file(raw_path),
            "bank_checksum": product["bank_checksum"],
            "bank_size": 131072,
            "manifest_path": str(parent_manifest.resolve()),
            "manifest_sha256": adapter.sha256_file(parent_manifest),
        },
        "normalisation": "2K+7; K distinct draws repeated twice, seven pseudo-arrivals",
        "source_sha256": {
            str(Path(__file__).resolve()): adapter.sha256_file(Path(__file__)),
            str(ROOT / "src/latent_landscapes/preinvasion_likelihood.py"): adapter.sha256_file(
                ROOT / "src/latent_landscapes/preinvasion_likelihood.py"
            ),
        },
    }
    write_json(output / "manifest.json", result)
    return result


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    receipt = json.loads(args.a_receipt.read_text())
    if receipt["status"] != "profile_numerically_resolved":
        raise ValueError("A profile must pass numerical qualification first")
    base_args = argparse.Namespace(**vars(args))
    base_args.arrival_bank = args.a_dir / "arrivals.npy"
    base_args.compressed_bank = args.a_dir / "compressed.npz"
    base_args.bank_role = "A"
    base_args.bank_manifest = args.a_dir.parent / "manifest.json"
    base_args.dense_baseline = False
    dup_args = argparse.Namespace(**vars(args))
    dup_args.arrival_bank = args.dup_dir / "arrivals.npy"
    dup_args.compressed_bank = args.dup_dir / "compressed.npz"
    dup_args.bank_role = "Adup"
    dup_args.bank_manifest = args.dup_dir / "manifest.json"
    dup_args.dense_baseline = False
    reference = json.loads(args.reference.read_text())
    if (
        adapter.sha256_file(args.observations)
        != reference["source_identity"]["observations"]["sha256"]
    ):
        raise ValueError("pseudo-mass replay observation identity differs from reference")
    base_identity = validate_bank_identity(base_args, reference)
    duplicate_identity = validate_bank_identity(dup_args, reference)
    duplication = json.loads(dup_args.bank_manifest.read_text())["duplication_of_A"]
    if (
        duplication["raw_sha256"] != base_identity["raw_sha256"]
        or duplication["bank_checksum"] != base_identity["bank_checksum"]
        or Path(duplication["raw_path"]).resolve() != base_args.arrival_bank.resolve()
        or Path(duplication["manifest_path"]).resolve() != base_args.bank_manifest.resolve()
        or duplication["manifest_sha256"] != adapter.sha256_file(base_args.bank_manifest)
    ):
        raise ValueError("Adup is not a duplicate of the supplied fitted A bank")
    for name, digest in receipt["source_input_sha256"].items():
        if (name.endswith(".py") or name.endswith("/public_inputs.json")) and adapter.sha256_file(
            Path(name)
        ) != digest:
            raise ValueError(f"scientific source changed since the A profile: {name}")
    for name, key in (
        ("public_inputs.npz", "public_npz_sha256"),
        ("exposure.npz", "exposure_sha256"),
    ):
        if adapter.sha256_file(args.input_dir / name) != receipt["data_identity"][key]:
            raise ValueError("pseudo-mass replay public input differs from the A profile")
    if receipt["data_identity"]["observations_sha256"] != adapter.sha256_file(args.observations):
        raise ValueError("A fitted receipt belongs to a different observation history")
    if any(
        receipt["bank_identity"][key] != base_identity[key]
        for key in ("raw_sha256", "compressed_sha256", "bank_checksum")
    ):
        raise ValueError("A fitted receipt bank differs from the pseudo-mass input")
    base_data, dup_data = load_data(base_args), load_data(dup_args)

    def base_factory(h: float, detection_sd: float) -> Any:
        return prepare_site_likelihood(
            base_data.observed, base_data.bank, h, detection_sd=detection_sd
        )

    def dup_factory(h: float, detection_sd: float) -> Any:
        return prepare_site_likelihood(
            dup_data.observed, dup_data.bank, h, detection_sd=detection_sd
        )

    base = SpatialProfileCriterion(base_data, evaluator_factory=base_factory)
    duplicate = SpatialProfileCriterion(dup_data, evaluator_factory=dup_factory)
    requested = {("standard_anchor", row["log_h"]) for row in receipt["anchors"]}
    requested.update(
        ("tight_root", root["log_h"])
        for level in receipt["tight_level_sets"]
        for root in level["roots"]
    )
    points = {("standard_anchor", row["log_h"]): row for row in receipt["points"]}
    points.update({("tight_root", row["log_h"]): row for row in receipt["tight_points"]})
    if not requested.issubset(points):
        raise ValueError("A receipt lacks selected anchor/root fits")
    records = []

    def replay(row: dict[str, Any], *, free: bool) -> dict[str, Any]:
        zero = row["family"] == "sigma_zero"
        point = parameters(row, free=free)
        h = None if free else row["h"]
        old = (
            base.evaluate_sigma_zero(point, fixed_h=h, nuisance_fd=True)
            if zero
            else base.evaluate_positive(point, fixed_h=h, nuisance_fd=True)
        )
        new = (
            duplicate.evaluate_sigma_zero(point, fixed_h=h, nuisance_fd=True)
            if zero
            else duplicate.evaluate_positive(
                point,
                fixed_h=h,
                nuisance_fd=True,
            )
        )
        if not old.success or not new.success:
            raise RuntimeError("fixed-fit pseudo-mass replay unresolved")
        if abs(old.criterion - row["criterion"]) > 1e-6:
            raise RuntimeError("A fixed-parameter replay disagrees with its receipt")
        pg = duplicate._projected_gradient_inf(
            new.objective_gradient, point, duplicate._bounds(h, zero)
        )
        result = {
            "family": row["family"],
            "h": row["h"],
            "free": free,
            "a_criterion": old.criterion,
            "adup_criterion": new.criterion,
            "criterion_shift": new.criterion - old.criterion,
            "adup_projected_gradient_inf": pg,
            "latent_modes_reoptimised": True,
            "outer_parameters_reoptimised": False,
        }
        records.append(result)
        return result

    free_rows = [replay(receipt["tight_free"][f], free=True) for f in FAMILIES]
    base_max = max(row["a_criterion"] for row in free_rows)
    dup_max = max(row["adup_criterion"] for row in free_rows)
    shifts = []
    ownership_changes = []

    def ownership_change(rows: list[dict[str, Any]], log_h: float | None) -> None:
        old = rows[0]["a_criterion"] - rows[1]["a_criterion"]
        new = rows[0]["adup_criterion"] - rows[1]["adup_criterion"]
        if old * new < 0 and min(abs(old), abs(new)) > 1e-4:
            ownership_changes.append({"log_h": log_h, "a_contrast": old, "adup_contrast": new})

    ownership_change(free_rows, None)
    for kind, x in sorted(requested):
        rows = [replay(points[kind, x][f], free=False) for f in FAMILIES]
        ownership_change(rows, x)
        old_w = 2 * (base_max - max(row["a_criterion"] for row in rows))
        new_w = 2 * (dup_max - max(row["adup_criterion"] for row in rows))
        shifts.append(
            {
                "h": min(30.0, math.exp(x)),
                "log_h": x,
                "point_source": kind,
                "a_w": old_w,
                "adup_fixed_fit_w": new_w,
                "delta_w": new_w - old_w,
            }
        )
    maximum = max(abs(row["delta_w"]) for row in shifts)
    max_pg = max(row["adup_projected_gradient_inf"] for row in records)
    return {
        "schema": "profile-pseudo-mass-fixed-fit-v1",
        "status": "evaluated",
        "requires_full_refit": maximum > 0.05 or max_pg > 1e-3 or bool(ownership_changes),
        "maximum_abs_centered_lr_shift": maximum,
        "maximum_projected_gradient": max_pg,
        "material_family_ownership_changes": ownership_changes,
        "thresholds": {"centered_lr_shift": 0.05, "projected_gradient": 1e-3},
        "fixed_fit_only": True,
        "centering": "tight A free fits; standard anchors and tight final roots",
        "points": shifts,
        "family_replays": records,
        "A_pseudo_mass": 7 / (131072 + 7),
        "Adup_pseudo_mass": 7 / (262144 + 7),
        "bank_identities": {"A": base_identity, "Adup": duplicate_identity},
        "a_receipt_sha256": adapter.sha256_file(args.a_receipt),
        "observations_sha256": adapter.sha256_file(args.observations),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    duplicate = sub.add_parser("duplicate")
    duplicate.add_argument("--parent-manifest", type=Path, required=True)
    duplicate.add_argument("--output-dir", type=Path, required=True)
    assess = sub.add_parser("assess")
    for name in (
        "input-dir",
        "observations",
        "a-receipt",
        "a-dir",
        "dup-dir",
        "reference",
        "output",
    ):
        assess.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "duplicate":
        result = duplicate_bank(args.parent_manifest, args.output_dir)
        print(json.dumps({"bank_size": result["bank_size"]}))
        return
    if args.output.exists():
        raise FileExistsError(args.output)
    paths = [
        args.a_receipt,
        args.reference,
        args.a_dir.parent / "manifest.json",
        args.a_dir / "arrivals.npy",
        args.a_dir / "compressed.npz",
        args.dup_dir / "arrivals.npy",
        args.dup_dir / "compressed.npz",
        args.dup_dir / "manifest.json",
        args.observations,
        args.input_dir / "public_inputs.npz",
        args.input_dir / "public_inputs.json",
        args.input_dir / "exposure.npz",
        Path(__file__),
        ROOT / "scripts/qualify_spatial_profiles.py",
        ROOT / "scripts/profile_level_sets.py",
        ROOT / "scripts/benchmark_spatial_profile.py",
        *sorted((ROOT / "src/latent_landscapes").rglob("*.py")),
    ]
    identities = {str(p.resolve()): adapter.sha256_file(p) for p in paths}
    result = evaluate(args)
    if any(adapter.sha256_file(Path(p)) != value for p, value in identities.items()):
        raise RuntimeError("source/input drift in pseudo-mass replay")
    result["source_input_sha256"] = identities
    write_json(args.output, result)
    print(
        json.dumps(
            {
                "requires_full_refit": result["requires_full_refit"],
                "maximum_abs_centered_lr_shift": result["maximum_abs_centered_lr_shift"],
            }
        )
    )


if __name__ == "__main__":
    main()
