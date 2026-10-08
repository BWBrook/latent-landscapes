#!/usr/bin/env python3
"""Validate immutable Arc 3 bank-escalation adoption receipts.

Adoption lets a completed reference bundle from one frozen bank ladder become
the selected input for the next ladder.  This module only validates the
receipt and its evidence; it never rewrites either campaign bundle.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from latent_landscapes import arc3_campaign as arc3
from latent_landscapes.arc3_synthesis import load_map_bundle

RECEIPT_SCHEMA_VERSION = 1
BUNDLE_FILES = ("profiles.npz", "base_arrivals.npy", "run_summary.json", "seed_provenance.json")
SOURCE_SNAPSHOT_FIELD = "source_snapshot_sha256"


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _hex_digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"adoption receipt {name} must be a SHA256 digest")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(f"adoption receipt {name} must be a SHA256 digest") from error
    return value


def _bundle_hashes(directory: Path) -> dict[str, str]:
    return {name: _sha256(directory / name) for name in BUNDLE_FILES}


def _without_freeze(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.pop("production_freeze", None)
    result.pop("production_freeze_sha256", None)
    return result


def _normalise_source(
    provenance: Mapping[str, Any], root: Path, *, label: str
) -> tuple[dict[str, str], dict[str, Any]]:
    saved = provenance.get("active_source_sha256")
    if not isinstance(saved, Mapping) or not saved:
        raise ValueError(f"{label} source provenance lacks active source hashes")
    root = root.expanduser().resolve()
    normalised: dict[str, str] = {}
    for raw_path, digest in saved.items():
        if not isinstance(raw_path, str):
            raise ValueError(f"{label} source provenance has a non-string path")
        digest = _hex_digest(digest, f"{label} source hash")
        path = Path(raw_path).expanduser().resolve()
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError as error:
            raise ValueError(
                f"{label} source path is outside its verified source root: {raw_path}"
            ) from error
        if not relative or relative == "." or relative in normalised:
            raise ValueError(f"{label} source provenance has an invalid relative path")
        if not path.is_file() or _sha256(path) != digest:
            raise ValueError(f"{label} source hash does not match its source file: {raw_path}")
        normalised[relative] = digest
    # Keep all provenance fields other than the path-bound hash map.  This
    # catches changes to requested commit, dirty state, or other metadata.
    metadata = {key: value for key, value in provenance.items() if key != "active_source_sha256"}
    metadata.pop("production_freeze", None)
    metadata.pop("production_freeze_sha256", None)
    return dict(sorted(normalised.items())), metadata


def _freeze_record(bundle: Any, role: str, label: str) -> tuple[dict[str, Any], str]:
    summary = bundle.run_summary
    if summary.get("mode") != "production" or summary.get("is_production") is not True:
        raise ValueError(f"{label} bundle is not an admitted production bundle")
    scene = summary.get("scene_metadata")
    source = summary.get("source_provenance")
    if not isinstance(scene, dict) or not isinstance(source, dict):
        raise ValueError(f"{label} bundle lacks scene or source provenance")
    freeze = scene.get("production_freeze")
    recorded = scene.get("production_freeze_sha256")
    if not isinstance(freeze, dict) or not isinstance(recorded, str):
        raise ValueError(f"{label} bundle lacks its recorded production freeze")
    if (
        source.get("production_freeze") != freeze
        or source.get("production_freeze_sha256") != recorded
    ):
        raise ValueError(f"{label} bundle has unreconciled production freeze provenance")
    try:
        canonical, canonical_sha = arc3.validate_production_freeze(bundle.config, scene, freeze)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} bundle has an invalid production freeze: {error}") from error
    expected = (
        freeze["reference_bank_size"] if role == "reference" else freeze["selected_bank_size"]
    )
    if bundle.config.bank_size != expected:
        raise ValueError(f"{label} bundle is not recorded for the {role} bank role")
    if recorded != canonical_sha:
        raise ValueError(f"{label} bundle production freeze hash is not canonical")
    return canonical, canonical_sha


def validate_adoption(
    old_reference_dir: Path,
    new_reference_dir: Path,
    receipt: Path | Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one old-reference to new-reference immutable adoption.

    The returned evidence is suitable for embedding in a numerical-review
    report.  The input bundles and receipt are read-only.
    """
    if isinstance(receipt, Path):
        receipt_path: Path | None = receipt
        payload = _json(receipt)
    else:
        receipt_path = None
        payload = dict(receipt)
    entry = payload
    if "maps" in entry:
        raise ValueError("adoption receipt must be a per-map receipt")
    if entry.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise ValueError("adoption receipt schema version is not supported")
    old_freeze_sha = _hex_digest(entry.get("old_freeze_sha256"), "old_freeze_sha256")
    new_freeze_sha = _hex_digest(entry.get("new_freeze_sha256"), "new_freeze_sha256")
    snapshot_sha = _hex_digest(entry.get(SOURCE_SNAPSHOT_FIELD), SOURCE_SNAPSHOT_FIELD)
    old_root = Path(entry.get("old_source_root", ""))
    new_root = Path(entry.get("new_source_root", ""))
    if not str(old_root) or not str(new_root):
        raise ValueError("adoption receipt must identify both source roots")
    old_reference_dir = old_reference_dir.expanduser().resolve()
    new_reference_dir = new_reference_dir.expanduser().resolve()
    for name, expected_path in (
        ("old_reference_dir", old_reference_dir),
        ("new_reference_dir", new_reference_dir),
    ):
        value = entry.get(name)
        if not isinstance(value, str) or Path(value).expanduser().resolve() != expected_path:
            raise ValueError(f"adoption receipt {name} does not match the supplied bundle")
    map_id = entry.get("map_id")
    if not isinstance(map_id, Mapping):
        raise ValueError("adoption receipt must identify the map")
    old_bundle = load_map_bundle(old_reference_dir)
    new_bundle = load_map_bundle(new_reference_dir)
    for label, bundle in (("old reference", old_bundle), ("new reference", new_bundle)):
        scene = bundle.run_summary.get("scene_metadata")
        if not isinstance(scene, dict) or {
            "archetype": scene.get("archetype"),
            "map_seed": scene.get("map_seed"),
        } != {"archetype": map_id.get("archetype"), "map_seed": map_id.get("map_seed")}:
            raise ValueError(f"{label} map identity does not match the adoption receipt")
    old_freeze, old_canonical_sha = _freeze_record(old_bundle, "reference", "old reference")
    new_freeze, new_canonical_sha = _freeze_record(new_bundle, "reference", "new reference")
    if (old_canonical_sha, new_canonical_sha) != (old_freeze_sha, new_freeze_sha):
        raise ValueError("adoption receipt freeze hashes do not match canonical bundle freezes")
    if (
        old_freeze.get(SOURCE_SNAPSHOT_FIELD) != snapshot_sha
        or new_freeze.get(SOURCE_SNAPSHOT_FIELD) != snapshot_sha
    ):
        raise ValueError("adoption receipt source snapshot does not match both freezes")
    for label, root in (("old", old_root), ("new", new_root)):
        snapshot_manifest = root.expanduser().resolve() / "SOURCE_SNAPSHOT.json"
        if not snapshot_manifest.is_file() or _sha256(snapshot_manifest) != snapshot_sha:
            raise ValueError(f"{label} source root does not contain the bound SOURCE_SNAPSHOT.json")
    old_settings = dict(old_freeze)
    new_settings = dict(new_freeze)
    for settings in (old_settings, new_settings):
        settings.pop("selected_bank_size", None)
        settings.pop("reference_bank_size", None)
    if old_settings != new_settings:
        raise ValueError("old and new production freezes differ beyond bank sizes")

    old_summary, new_summary = old_bundle.run_summary, new_bundle.run_summary
    if old_bundle.truths != new_bundle.truths:
        raise ValueError("old and new bundles differ in truths")
    old_config, new_config = old_bundle.config, new_bundle.config
    for name in (
        "master_seed",
        "calibration_replicates",
        "validation_replicates",
        "calibration_rank",
        "rhos",
        "effects",
    ):
        if getattr(old_config, name) != getattr(new_config, name):
            raise ValueError(f"old and new bundles differ in {name}")
    if new_config.bank_size != 2 * old_config.bank_size:
        raise ValueError("new reference bank is not twice the old reference bank")
    old_scene = _without_freeze(old_summary.get("scene_metadata", {}))
    new_scene = _without_freeze(new_summary.get("scene_metadata", {}))
    if old_scene != new_scene:
        raise ValueError("old and new scene metadata differ beyond their freezes")
    old_source = old_summary.get("source_provenance")
    new_source = new_summary.get("source_provenance")
    if not isinstance(old_source, Mapping) or not isinstance(new_source, Mapping):
        raise ValueError("old or new bundle lacks source provenance")
    old_source_paths, old_source_meta = _normalise_source(old_source, old_root, label="old")
    new_source_paths, new_source_meta = _normalise_source(new_source, new_root, label="new")
    if old_source_paths != new_source_paths or old_source_meta != new_source_meta:
        raise ValueError("old and new source provenance differ after root normalization")
    for key in (
        "workflow",
        "schema_version",
        "mode",
        "is_production",
        "designs",
        "lanes",
        "truths",
        "invariants",
        "source_commit",
        "outcome",
        "notes",
        "hostname",
        "workers",
    ):
        if old_summary.get(key) != new_summary.get(key):
            raise ValueError(f"old and new campaign summaries differ in {key}")
    old_counts, new_counts = old_summary.get("counts"), new_summary.get("counts")
    if not isinstance(old_counts, Mapping) or not isinstance(new_counts, Mapping):
        raise ValueError("old or new campaign summary lacks counts")
    if (set(old_counts) - {"bank_draws"}) != (set(new_counts) - {"bank_draws"}):
        raise ValueError("old and new campaign count fields differ")
    for key in set(old_counts) - {"bank_draws"}:
        if old_counts.get(key) != new_counts.get(key):
            raise ValueError(f"old and new campaign counts differ in {key}")
    old_seeds = _json(old_reference_dir / "seed_provenance.json")
    new_seeds = _json(new_reference_dir / "seed_provenance.json")
    for key in (
        "master_seed",
        "calibration_seeds",
        "validation_seeds",
        "site_ids",
        "scene_metadata",
        "source_commit",
    ):
        left = (
            _without_freeze(old_seeds[key])
            if key in ("scene_metadata", "source_provenance")
            and isinstance(old_seeds.get(key), Mapping)
            else old_seeds.get(key)
        )
        right = (
            _without_freeze(new_seeds[key])
            if key in ("scene_metadata", "source_provenance")
            and isinstance(new_seeds.get(key), Mapping)
            else new_seeds.get(key)
        )
        if left != right:
            raise ValueError(f"old and new seed provenance differ in {key}")
    if (
        old_seeds.get("source_provenance") != old_source
        or new_seeds.get("source_provenance") != new_source
    ):
        raise ValueError("seed and summary source provenance differ")
    if old_seeds.get("scene_metadata") != old_summary.get("scene_metadata") or new_seeds.get(
        "scene_metadata"
    ) != new_summary.get("scene_metadata"):
        raise ValueError("seed and summary scene metadata differ")
    old_bank = np.asarray(np.load(old_reference_dir / "base_arrivals.npy", allow_pickle=False))
    new_bank = np.asarray(np.load(new_reference_dir / "base_arrivals.npy", allow_pickle=False))
    if (
        len(old_seeds.get("bank_seeds", [])) != old_config.bank_size
        or len(new_seeds.get("bank_seeds", [])) != new_config.bank_size
        or old_bank.shape != (old_config.bank_size, len(old_seeds.get("site_ids", [])))
        or new_bank.shape != (new_config.bank_size, len(new_seeds.get("site_ids", [])))
        or not np.array_equal(new_bank[: old_bank.shape[0]], old_bank)
    ):
        raise ValueError("new reference bank does not preserve the old reference prefix")
    if new_seeds.get("bank_seeds", [])[: old_config.bank_size] != old_seeds.get("bank_seeds"):
        raise ValueError("new reference bank seeds do not preserve the old reference prefix")
    with (
        np.load(old_reference_dir / "profiles.npz", allow_pickle=False) as old_profiles,
        np.load(new_reference_dir / "profiles.npz", allow_pickle=False) as new_profiles,
    ):
        for key in (
            "rhos",
            "effects",
            "condition_ids",
            "design_ids",
            "truth_effects",
            "truth_rhos",
        ):
            if (
                key not in old_profiles
                or key not in new_profiles
                or not np.array_equal(old_profiles[key], new_profiles[key])
            ):
                raise ValueError(f"old and new profile grids or labels differ in {key}")
        if ("truth_roles" in old_profiles) != ("truth_roles" in new_profiles) or (
            "truth_roles" in old_profiles
            and not np.array_equal(old_profiles["truth_roles"], new_profiles["truth_roles"])
        ):
            raise ValueError("old and new profile truth roles differ")
    files = entry.get("files")
    if not isinstance(files, Mapping):
        raise ValueError("adoption receipt must bind old and new bundle files")
    old_files = files.get("selected")
    new_files = files.get("reference")
    if not isinstance(old_files, Mapping) or not isinstance(new_files, Mapping):
        raise ValueError("adoption receipt file bindings are incomplete")
    expected_old, expected_new = (
        _bundle_hashes(old_reference_dir),
        _bundle_hashes(new_reference_dir),
    )
    for label, advertised, expected_files in (
        ("old", old_files, expected_old),
        ("new", new_files, expected_new),
    ):
        if set(advertised) != set(BUNDLE_FILES) or any(
            _hex_digest(advertised.get(name), f"{label} {name}") != digest
            for name, digest in expected_files.items()
        ):
            raise ValueError(f"adoption receipt {label} bundle hashes do not reconcile")
    result = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "old_freeze_sha256": old_canonical_sha,
        "new_freeze_sha256": new_canonical_sha,
        "source_snapshot_sha256": snapshot_sha,
        "old_freeze": old_freeze,
        "new_freeze": new_freeze,
        "old_source_root": str(old_root),
        "new_source_root": str(new_root),
        "map_id": dict(map_id),
        "old_reference_dir": str(old_reference_dir),
        "new_reference_dir": str(new_reference_dir),
        "files": {"selected": dict(old_files), "reference": dict(new_files)},
    }
    if receipt_path is not None:
        result["receipt_path"] = str(receipt_path)
        result["receipt_sha256"] = _sha256(receipt_path)
    return result


__all__ = ["BUNDLE_FILES", "validate_adoption"]
