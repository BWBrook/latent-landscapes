#!/usr/bin/env python3
"""Run the registered Goal 047 Stage A integration sensitivity screen.

The runner only evaluates the two immutable Goal 046 bank bundles.  It never
generates a bank, changes source or reference bundles, or makes the Stage A
scientific decision.  The evaluator consumes the arrays and report written by
this command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

HALF_SIZE = 65_536
FULL_SIZE = 131_072
MAPS = ("connected-2026090812", "corridor-2026090812")
ALPHAS = (0.25, 0.5, 1.0)
ALPHA_LABELS = {0.25: "025", 0.5: "050", 1.0: "100"}
RHO_WINDOW = (
    1.0,
    1.0570180405613805,
    1.0717734625362931,
    1.0867348625260582,
    1.1019051158766109,
    1.11728713807222,
    1.1328838852957988,
    1.148698354997035,
)
ABS_TOL = 1e-9


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def expected_hashes(path: Path) -> dict[str, str]:
    value = load_json(path)
    files = value.get("files")
    if value.get("schema_version") != 1 or not isinstance(files, dict):
        raise ValueError("input hash manifest requires schema_version=1 and a files object")
    if not all(isinstance(key, str) and isinstance(digest, str) for key, digest in files.items()):
        raise ValueError("input hash manifest files must map relative paths to SHA256 strings")
    return dict(files)


def check_hash(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"{label}: {path}")
    if len(expected) != 64:
        raise ValueError(f"{label}: malformed SHA256")
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"{label}: SHA256 mismatch: expected {expected}, got {actual}")
    return actual


def import_frozen_source(source_root: Path) -> None:
    source_root = source_root.resolve()
    if not (source_root / "latent_landscapes" / "arc3_campaign.py").is_file():
        raise ValueError(f"frozen source root is missing latent_landscapes: {source_root}")
    sys.path.insert(0, str(source_root))


def _snapshot_key(source_root: Path, module_path: Path) -> str:
    return str(module_path.resolve().relative_to(source_root.resolve().parent)).replace("\\", "/")


def verify_frozen_modules(
    source_root: Path, snapshot: Mapping[str, Any], modules: tuple[Any, ...]
) -> dict[str, str]:
    """Verify accepted source modules against the immutable source snapshot."""
    recorded = snapshot.get("sha256")
    if not isinstance(recorded, dict):
        raise ValueError("source snapshot lacks its SHA256 file map")
    hashes: dict[str, str] = {}
    for module in modules:
        module_path = Path(module.__file__).resolve()
        key = _snapshot_key(source_root, module_path)
        expected = recorded.get(key)
        if not isinstance(expected, str):
            raise ValueError(f"source snapshot lacks imported module {key}")
        hashes[key] = check_hash(module_path, expected, key)
    return hashes


def _required_input_names() -> tuple[str, ...]:
    return (
        "reference/base_arrivals.npy",
        "reference/profiles.npz",
        "reference/run_summary.json",
        "reference/seed_provenance.json",
        "adoption-receipt.json",
    )


def load_inputs(root: Path, label: str, map_id: str, hashes: Mapping[str, str]) -> dict[str, Any]:
    """Load one immutable bank/reference bundle and check every bound file."""
    map_dir = root / map_id
    paths = {name: map_dir / name for name in _required_input_names()}
    for name, path in paths.items():
        key = f"{label}/{map_id}/{name}"
        if key not in hashes:
            raise ValueError(f"input hash manifest lacks {key}")
        check_hash(path, hashes[key], key)

    bank = np.ascontiguousarray(
        np.load(paths["reference/base_arrivals.npy"], allow_pickle=False), dtype=np.float64
    )
    if bank.ndim != 2 or not np.isfinite(bank).all() or (bank < 0.0).any():
        raise ValueError(f"{map_id} {label}: invalid arrival bank")
    summary = load_json(paths["reference/run_summary.json"])
    seeds = load_json(paths["reference/seed_provenance.json"])
    adoption = load_json(paths["adoption-receipt.json"])
    if summary.get("scene_metadata", {}).get("archetype") not in ("connected", "corridor"):
        raise ValueError(f"{map_id} {label}: unexpected archetype")
    if summary.get("scene_metadata", {}).get("map_seed") != 2026090812:
        raise ValueError(f"{map_id} {label}: unexpected map seed")
    receipt_files = adoption.get("files", {}).get("reference", {})
    reference = map_dir / "reference"
    for name in ("base_arrivals.npy", "profiles.npz", "run_summary.json", "seed_provenance.json"):
        if receipt_files.get(name) != sha256(reference / name):
            raise ValueError(f"{map_id} {label}: adoption receipt does not bind {name}")
    with np.load(paths["reference/profiles.npz"], allow_pickle=False) as bundle:
        profile_arrays = {name: np.asarray(bundle[name]).copy() for name in bundle.files}
    return {
        "root": root,
        "map_dir": map_dir,
        "paths": paths,
        "bank": bank,
        "summary": summary,
        "seeds": seeds,
        "adoption": adoption,
        "profile_arrays": profile_arrays,
    }


def _config(summary: Mapping[str, Any], BridgeConfig: Any) -> Any:
    config = dict(summary["config"])
    config["rhos"] = tuple(float(value) for value in config["rhos"])
    config["effects"] = tuple(float(value) for value in config["effects"])
    return BridgeConfig(**config)


def reconstruct_context(
    new: Mapping[str, Any],
    BridgeConfig: Any,
    arc3: Any,
    arc2c: Any,
    goal007: Any,
    design_module: Any,
    landscapes_module: Any,
) -> dict[str, Any]:
    """Rebuild the frozen map, designs, histories and seed schedule."""
    summary = new["summary"]
    seeds = new["seeds"]
    config = _config(summary, BridgeConfig)
    scene = summary["scene_metadata"]
    freeze = scene.get("production_freeze")
    if not isinstance(freeze, dict):
        raise ValueError("production summary lacks its freeze")
    arc3.validate_production_freeze(config, scene, freeze)
    landscape = landscapes_module.build_landscape(scene["archetype"], int(scene["map_seed"]))
    if scene.get("landscape_descriptors") != landscapes_module.describe_landscape(landscape):
        raise ValueError("reconstructed landscape descriptors differ from receipt")
    access, balanced = design_module.build_sampling_pair(landscape, int(scene["sampling_seed"]))
    access_coords, access_ordered = arc3._validate_design(access, landscape)
    balanced_coords, balanced_ordered = arc3._validate_design(balanced, landscape)
    access = arc3._canonical_design(access, access_ordered)
    balanced = arc3._canonical_design(balanced, balanced_ordered)
    union = arc3._union_design(access, access_coords, balanced_coords)
    site_ids = tuple(site.site_id for site in union.sites)
    union_fixed = goal007.FixedInputs(landscape, union, {"design_valid": True})
    designs = (
        ("access", goal007.FixedInputs(landscape, access, {"design_valid": True})),
        ("balanced", goal007.FixedInputs(landscape, balanced, {"design_valid": True})),
    )
    manifest = arc2c.spawn_seed_manifest(config)
    if seeds.get("site_ids") != list(site_ids):
        raise ValueError("seed manifest site IDs differ from reconstructed design")
    if seeds.get("calibration_seeds") != [asdict(value) for value in manifest.calibration]:
        raise ValueError("calibration seed schedule differs from frozen source")
    if seeds.get("validation_seeds") != [asdict(value) for value in manifest.validation]:
        raise ValueError("validation seed schedule differs from frozen source")
    if seeds.get("bank_seeds") != list(manifest.bank_seeds):
        raise ValueError("bank seed schedule differs from frozen source")
    return {
        "config": config,
        "union_fixed": union_fixed,
        "designs": designs,
        "site_ids": site_ids,
        "manifest": manifest,
        "truths": arc3._truths(),
    }


def build_integration_for_sites(
    bank: np.ndarray,
    site_ids: tuple[str, ...],
    rhos: tuple[float, ...],
    effects: tuple[float, ...],
    workers: int,
    arc3: Any,
    likelihood: Any,
) -> Any:
    if workers == 1:
        return likelihood.build_joint_integration(bank, site_ids, rhos, effects)
    return arc3._build_joint_integration(
        bank, site_ids, rhos, effects, background_hazard=0.002, workers=workers
    )


def combine_integrations(left: Any, right: Any, bank_checksum: str, half_size: int) -> Any:
    """Combine two alpha=.5 integrations before any likelihood logarithms."""
    if half_size <= 0 or left.rhos != right.rhos or left.effects != right.effects:
        raise ValueError("incompatible half integrations")
    if left.site_ids != right.site_ids:
        raise ValueError("half integrations do not share site IDs")
    from latent_landscapes.integration_weights import reweight_integration

    averaged = type(left)(
        left.rhos,
        left.effects,
        left.site_ids,
        (np.asarray(left.category_mass) + np.asarray(right.category_mass)) / 2.0,
        tuple(
            (np.asarray(a) + np.asarray(b)) / 2.0
            for a, b in zip(left.survival_moments, right.survival_moments, strict=True)
        ),
        bank_checksum,
    )
    # Averaging two K half-banks with alpha=.5 has effective alpha=1 for 2K.
    return reweight_integration(
        averaged,
        2 * half_size,
        from_pseudocount=1.0,
        to_pseudocount=0.5,
    )


def alpha_views(integration: Any, bank_size: int) -> dict[str, Any]:
    from latent_landscapes.integration_weights import reweight_integration

    return {
        ALPHA_LABELS[alpha]: reweight_integration(
            integration,
            bank_size,
            from_pseudocount=0.5,
            to_pseudocount=alpha,
        )
        for alpha in ALPHAS
    }


def paired_mapped_histories(
    context: Mapping[str, Any], seed: Any, arc3: Any, likelihood: Any
) -> tuple[tuple[tuple[Any, ...], ...], ...]:
    """Generate one paired history realization and map it to both designs."""
    union_histories = likelihood.paired_histories(context["union_fixed"], seed)[:3]
    return tuple(
        tuple(arc3._map_histories(rows, fixed.design.sites) for rows in union_histories)
        for _, fixed in context["designs"]
    )


def _training(records: tuple[Any, ...]) -> tuple[Any, ...]:
    selected = tuple(row for row in records if row.split == "training")
    if not selected:
        raise ValueError("mapped history has no training records")
    return selected


def _surface(records: tuple[Any, ...], integration: Any, likelihood: Any) -> np.ndarray:
    values = np.asarray(
        likelihood.joint_log_likelihood(_training(records), integration), dtype=np.float64
    )
    if (
        values.shape != (len(integration.rhos), len(integration.effects))
        or not np.isfinite(values).all()
    ):
        raise RuntimeError("training likelihood surface is invalid")
    return values


def connected_arrays(
    context: Mapping[str, Any],
    integrations: Mapping[str, Mapping[str, Any]],
    workers: int,
    arc3: Any,
    likelihood: Any,
) -> dict[str, np.ndarray]:
    del workers
    effects = np.asarray(context["config"].effects, dtype=np.float64)
    calibration_seeds = context["manifest"].calibration
    validation_seeds = context["manifest"].validation
    if len(effects) != 181 or len(calibration_seeds) != 250 or len(validation_seeds) != 250:
        raise ValueError("connected Stage A requires H181 and 250+250 histories")
    arrays: dict[str, np.ndarray] = {}
    labels = tuple(integrations["half0"].keys())
    for label in labels:
        for prefix, _seeds, count in (
            ("calibration", calibration_seeds, 250),
            ("validation", validation_seeds, 250),
        ):
            shape = (2, count, 1, len(effects))
            arrays[f"connected_half0_alpha{label}_{prefix}_training_joint"] = np.empty(shape)
            arrays[f"connected_half1_alpha{label}_{prefix}_training_joint"] = np.empty(shape)
            arrays[f"connected_combined_alpha{label}_{prefix}_training_joint"] = np.empty(shape)
        for bank_label in ("half0", "half1", "combined"):
            arrays[f"connected_{bank_label}_alpha{label}_calibration_effect_lr"] = np.empty(
                (2, 250)
            )
            arrays[f"connected_{bank_label}_alpha{label}_validation_effect_drops"] = np.empty(
                (2, 250, len(effects))
            )
    for seed_index, seed in enumerate((*calibration_seeds, *validation_seeds)):
        mapped = paired_mapped_histories(context, seed, arc3, likelihood)
        phase = "calibration" if seed.phase == "calibration" else "validation"
        index = seed_index if phase == "calibration" else seed_index - len(calibration_seeds)
        for label in labels:
            for bank_label in ("half0", "half1", "combined"):
                surface_by_design = tuple(
                    _surface(mapped[design_index][0], integrations[bank_label][label], likelihood)
                    for design_index in range(2)
                )
                for design_index, surface in enumerate(surface_by_design):
                    key = f"connected_{bank_label}_alpha{label}_{phase}_training_joint"
                    arrays[key][design_index, index] = surface
                    if phase == "calibration":
                        key = f"connected_{bank_label}_alpha{label}_calibration_effect_lr"
                        arrays[key][design_index, index] = 2.0 * (
                            surface[0].max() - surface[0, 0]
                        )
                    else:
                        key = f"connected_{bank_label}_alpha{label}_validation_effect_drops"
                        arrays[key][design_index, index] = 2.0 * (
                            surface[0].max() - surface[0]
                        )
    # The evaluator needs only the reduced arrays; retain raw training likelihoods
    # for independent reconstruction and audit.
    for key in list(arrays):
        if key.endswith("_training_joint"):
            arrays[key] = np.asarray(arrays[key])
    return {
        key: value
        for key, value in arrays.items()
        if key.endswith(("calibration_effect_lr", "validation_effect_drops", "training_joint"))
    }


def corridor_arrays(
    context: Mapping[str, Any],
    integrations: Mapping[str, Mapping[str, Any]],
    arc3: Any,
    likelihood: Any,
) -> dict[str, np.ndarray]:
    effects = np.asarray(context["config"].effects, dtype=np.float64)
    if len(effects) != 181 or len(context["manifest"].validation) != 250:
        raise ValueError("corridor Stage A requires H181 and the frozen validation ensemble")
    mapped = paired_mapped_histories(context, context["manifest"].validation[0], arc3, likelihood)
    arrays: dict[str, np.ndarray] = {}
    for label in integrations["half0"]:
        for bank_label in ("half0", "half1", "combined"):
            surfaces = np.stack(
                [
                    _surface(mapped[0][effect_index], integrations[bank_label][label], likelihood)
                    for effect_index in range(3)
                ]
            )
            arrays[f"corridor_{bank_label}_alpha{label}_training_joint"] = surfaces
    return arrays


def _saved_reproduction(
    arrays: Mapping[str, np.ndarray],
    connected_old: Mapping[str, Any],
    connected_new: Mapping[str, Any],
    corridor_old: Mapping[str, Any],
    corridor_new: Mapping[str, Any],
) -> tuple[dict[str, float], dict[str, float]]:
    expected_connected = {
        "half0": (
            connected_old["profile_arrays"]["calibration_effect_lr"][[0, 3], 0],
            connected_old["profile_arrays"]["validation_effect_drops"][[0, 3], 0],
        ),
        "combined": (
            connected_new["profile_arrays"]["calibration_effect_lr"][[0, 3], 0],
            connected_new["profile_arrays"]["validation_effect_drops"][[0, 3], 0],
        ),
    }
    connected: dict[str, float] = {}
    for bank_label, (cal, drops) in expected_connected.items():
        label = f"{bank_label}_alpha050"
        connected[bank_label] = max(
            float(np.max(np.abs(arrays[f"connected_{label}_calibration_effect_lr"] - cal))),
            float(np.max(np.abs(arrays[f"connected_{label}_validation_effect_drops"] - drops))),
        )
    rhos = np.asarray(RHO_WINDOW)
    corridor: dict[str, float] = {}
    for bank_label, bundle in (("half0", corridor_old), ("combined", corridor_new)):
        profile = bundle["profile_arrays"]["validation_train_joint"][:3, 0]
        full_rhos = np.asarray(bundle["profile_arrays"]["rhos"])
        indices = np.asarray(
            [
                int(np.flatnonzero(np.isclose(full_rhos, rho, rtol=0, atol=1e-12))[0])
                for rho in rhos
            ]
        )
        expected = profile[:, indices, :]
        actual = arrays[f"corridor_{bank_label}_alpha050_training_joint"]
        corridor[bank_label] = float(np.max(np.abs(actual - expected)))
    return connected, corridor


def write_output(output: Path, arrays: Mapping[str, np.ndarray], report: dict[str, Any]) -> None:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    if any(
        not isinstance(value, np.ndarray) or value.dtype.kind == "O"
        for value in arrays.values()
    ):
        raise TypeError("output arrays must be concrete non-object NumPy arrays")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=str(output.parent)))
    try:
        array_path = temporary / "diagnostic-arrays.npz"
        np.savez_compressed(array_path, **dict(arrays))
        report["arrays_sha256"] = sha256(array_path)
        report["array_keys"] = sorted(arrays)
        report["completion_status"] = "complete"
        report["completed_utc"] = datetime.now(UTC).isoformat()
        (temporary / "diagnostic-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temporary, output)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-root", type=Path, required=True)
    parser.add_argument("--new-root", type=Path, required=True)
    parser.add_argument("--input-hashes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.workers <= 4:
        raise SystemExit("--workers must be between 1 and 4")
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {args.output}")
    hashes = expected_hashes(args.input_hashes)
    source_root = (Path(__file__).resolve().parents[1] / "src").resolve()
    for label, root in (("old", args.old_root), ("new", args.new_root)):
        key = f"{label}/source/SOURCE_SNAPSHOT.json"
        if key not in hashes:
            raise SystemExit(f"input hash manifest lacks {key}")
        check_hash(root / "source" / "SOURCE_SNAPSHOT.json", hashes[key], key)
    import_frozen_source(source_root)
    from latent_landscapes import arc2b_campaign as arc2b
    from latent_landscapes import arc2c_campaign as arc2c
    from latent_landscapes import arc2c_likelihood as likelihood
    from latent_landscapes import arc3_campaign as arc3
    from latent_landscapes import arc3_design, arc3_landscapes
    from latent_landscapes.goal007 import benchmark as goal007

    source_snapshot = load_json(args.new_root / "source" / "SOURCE_SNAPSHOT.json")
    source_hashes = verify_frozen_modules(
        source_root,
        source_snapshot,
        (arc2b, arc2c, likelihood, arc3, arc3_design, arc3_landscapes, goal007),
    )
    started = time.perf_counter()
    started_utc = datetime.now(UTC).isoformat()
    old = {map_id: load_inputs(args.old_root, "old", map_id, hashes) for map_id in MAPS}
    new = {map_id: load_inputs(args.new_root, "new", map_id, hashes) for map_id in MAPS}
    arrays: dict[str, np.ndarray] = {
        "effects": np.asarray(np.linspace(1.0, 10.0, 181), dtype=np.float64),
        "corridor_rhos": np.asarray(RHO_WINDOW, dtype=np.float64),
    }
    technical: dict[str, float] = {}
    map_reports: dict[str, Any] = {}
    for map_id in MAPS:
        print(f"{datetime.now(UTC).isoformat()} Stage A map={map_id} starting", flush=True)
        old_bank = old[map_id]["bank"]
        new_bank = new[map_id]["bank"]
        if old_bank.shape != (HALF_SIZE, new_bank.shape[1]) or new_bank.shape != (
            FULL_SIZE,
            new_bank.shape[1],
        ):
            raise ValueError(f"{map_id}: expected nested (65536,131072) bank shapes")
        if not np.array_equal(old_bank, new_bank[:HALF_SIZE]):
            raise ValueError(f"{map_id}: old bank is not the exact new-bank prefix")
        context = reconstruct_context(
            new[map_id],
            arc2c.BridgeConfig,
            arc3,
            arc2c,
            goal007,
            arc3_design,
            arc3_landscapes,
        )
        if tuple(context["config"].effects) != tuple(arrays["effects"]):
            raise ValueError(f"{map_id}: frozen effect grid is not H181")
        rhos = (1.0,) if map_id.startswith("connected") else RHO_WINDOW
        half_banks = (new_bank[:HALF_SIZE], new_bank[HALF_SIZE:])
        half_integrations = {
            f"half{index}": build_integration_for_sites(
                bank,
                context["site_ids"],
                rhos,
                tuple(arrays["effects"]),
                args.workers,
                arc3,
                likelihood,
            )
            for index, bank in enumerate(half_banks)
        }
        print(f"{datetime.now(UTC).isoformat()} Stage A map={map_id} halves integrated", flush=True)
        combined = combine_integrations(
            half_integrations["half0"],
            half_integrations["half1"],
            hashlib.sha256(np.ascontiguousarray(new_bank).tobytes()).hexdigest(),
            HALF_SIZE,
        )
        integrations = {
            "half0": alpha_views(half_integrations["half0"], HALF_SIZE),
            "half1": alpha_views(half_integrations["half1"], HALF_SIZE),
            "combined": alpha_views(combined, FULL_SIZE),
        }
        if map_id.startswith("connected"):
            arrays.update(connected_arrays(context, integrations, args.workers, arc3, likelihood))
        else:
            arrays.update(corridor_arrays(context, integrations, arc3, likelihood))
        print(
            f"{datetime.now(UTC).isoformat()} Stage A map={map_id} histories evaluated",
            flush=True,
        )
        map_reports[map_id] = {
            "bank_checksum": hashlib.sha256(np.ascontiguousarray(new_bank).tobytes()).hexdigest(),
            "half_checksums": {
                key: value.bank_checksum for key, value in half_integrations.items()
            },
        }
    connected_replay, corridor_replay = _saved_reproduction(
        arrays,
        old["connected-2026090812"],
        new["connected-2026090812"],
        old["corridor-2026090812"],
        new["corridor-2026090812"],
    )
    technical = {
        "connected_half0": connected_replay["half0"],
        "connected_combined": connected_replay["combined"],
        "corridor_half0": corridor_replay["half0"],
        "corridor_combined": corridor_replay["combined"],
    }
    if any(value > ABS_TOL for value in technical.values()):
        raise RuntimeError(f"saved Stage A replay exceeds {ABS_TOL}: {technical}")
    report = {
        "schema_version": 1,
        "goal": "047",
        "stage": "A",
        "scientific_acceptance": False,
        "completion_status": "pending",
        "started_utc": started_utc,
        "runtime_seconds": time.perf_counter() - started,
        "workers": args.workers,
        "input_hashes": hashes,
        "source_root": str(source_root),
        "source_hashes": source_hashes,
        "maps": map_reports,
        "technical_replay_max_abs": technical,
        "method_admission": "runner_only; scientific evaluation is external",
    }
    write_output(args.output, arrays, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
