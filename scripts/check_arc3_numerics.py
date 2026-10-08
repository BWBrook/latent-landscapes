#!/usr/bin/env python3
"""Check an Arc 3 pilot against a nested doubled bank and half-grid refinements.

This is a bounded numerical diagnostic for the first two calibration and first
two evaluation histories.  It is not a full-ensemble numerical review and does
not accept scientific evidence or authorize production.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import arc3_campaign as arc3
from latent_landscapes.arc2c_campaign import spawn_seed_manifest
from latent_landscapes.arc2c_design import BACKGROUND_HAZARD, BridgeConfig
from latent_landscapes.arc3_design import (
    MASTER_SEED,
    build_sampling_pair,
)
from latent_landscapes.arc3_landscapes import ARCHETYPES, build_landscape, describe_landscape
from latent_landscapes.goal007 import benchmark as goal007

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
Progress = Callable[[str], None]

EFFECT_MLE_LIMIT = 0.05
RHO_LOG_MLE_LIMIT = 0.027726
PROFILE_LR_LIMIT = 0.5
TRUTH_LR_LIMIT = 0.5
REFINEMENT_GAIN_LIMIT = 0.25


def profile_change(old: FloatArray, new: FloatArray, *, new_maximum: float | None = None) -> float:
    """Return centred-LR movement on the union where either profile has LR <= 10."""
    old_drop = 2.0 * (float(np.max(old)) - old)
    maximum = float(np.max(new)) if new_maximum is None else new_maximum
    new_drop = 2.0 * (maximum - new)
    near = (old_drop <= 10.0) | (new_drop <= 10.0)
    if not np.any(near):
        raise ValueError("profiles have no finite LR<=10 comparison region")
    return float(np.max(np.abs(new_drop[near] - old_drop[near])))


def half_grid(
    grid: FloatArray,
    old_profiles: FloatArray,
    new_profiles: FloatArray,
    truths: tuple[float, ...],
    *,
    geometric: bool,
) -> tuple[float, ...]:
    """Refine supported nodes and immediate neighbours without bridging gaps."""
    old_drop = 2.0 * (old_profiles.max(axis=-1, keepdims=True) - old_profiles)
    new_drop = 2.0 * (new_profiles.max(axis=-1, keepdims=True) - new_profiles)
    support = ((old_drop <= 10.0) | (new_drop <= 10.0)).reshape(-1, len(grid)).any(axis=0)
    selected = set(map(int, np.flatnonzero(support)))
    for index in tuple(selected):
        selected.update(
            neighbour for neighbour in (index - 1, index + 1) if 0 <= neighbour < len(grid)
        )
    for truth in truths:
        matches = np.flatnonzero(np.isclose(grid, truth, rtol=0.0, atol=1e-12))
        if len(matches) != 1:
            raise ValueError("each truth must occur exactly once on its candidate grid")
        selected.add(int(matches[0]))
    values = {float(grid[index]) for index in selected}
    for index in selected:
        if index + 1 not in selected:
            continue
        midpoint = (
            float(np.sqrt(grid[index] * grid[index + 1]))
            if geometric
            else float((grid[index] + grid[index + 1]) / 2.0)
        )
        values.add(midpoint)
    return tuple(sorted(values))


def local_effect_half_grid(
    grid: FloatArray, old: FloatArray, new: FloatArray, true_rho: int, truths: tuple[float, ...]
) -> tuple[float, ...]:
    """Return original MLE/truth nodes and the adjacent arithmetic half-steps."""
    centres: set[int] = set()
    for surfaces in (old, new):
        known = surfaces[:, :, true_rho, :]
        joint = surfaces
        centres.update(int(value) for value in np.argmax(known, axis=-1).ravel())
        centres.update(
            int(np.unravel_index(int(value), joint.shape[-2:])[1])
            for value in np.argmax(joint.reshape(*joint.shape[:2], -1), axis=-1).ravel()
        )
    for truth in truths:
        centres.add(_index(grid, truth))
    values = {float(grid[index]) for index in centres}
    for index in centres:
        for neighbour in (index - 1, index + 1):
            if 0 <= neighbour < len(grid):
                values.add(float(grid[neighbour]))
                values.add(float((grid[index] + grid[neighbour]) / 2.0))
    return tuple(sorted(values))


def merge_axis(
    grid: FloatArray,
    baseline: FloatArray,
    fine_grid: FloatArray,
    refined: FloatArray,
    *,
    axis: int,
) -> tuple[FloatArray, FloatArray]:
    """Insert half-grid evaluations while retaining every original grid node."""
    inserted = ~np.isin(fine_grid, grid)
    merged_grid = np.concatenate((grid, fine_grid[inserted]))
    order = np.argsort(merged_grid)
    inserted_values = np.take(refined, np.flatnonzero(inserted), axis=axis)
    merged = np.concatenate((baseline, inserted_values), axis=axis)
    return merged_grid[order], np.take(merged, order, axis=axis)


def truth_lrs(joint: FloatArray, true_rho: int, true_effect: int) -> FloatArray:
    """Known-effect, profiled-effect, and spread LR at their generating values."""
    known = joint[true_rho]
    return np.asarray(
        (
            2.0 * (known.max() - known[true_effect]),
            2.0 * (joint.max() - joint[:, true_effect].max()),
            2.0 * (joint.max() - joint[true_rho].max()),
        ),
        dtype=np.float64,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_review(run: dict[str, Any]) -> dict[str, Any]:
    provenance = run.get("source_provenance")
    saved = provenance.get("active_source_sha256", {}) if isinstance(provenance, dict) else {}
    current = {
        name: _sha256(Path(name))
        for name in saved
        if isinstance(name, str) and Path(name).is_file()
    }
    changed = sorted(name for name, digest in current.items() if saved.get(name) != digest)
    missing = sorted(name for name in saved if isinstance(name, str) and not Path(name).is_file())
    return {
        "saved_active_source_sha256": saved,
        "current_active_source_sha256": current,
        "changed_paths": changed,
        "missing_paths": missing,
        "interpretation": (
            "Recorded provenance drift is not itself a replay failure; bank, map, sampling, "
            "seed and saved-profile replay are checked directly."
        ),
    }


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _config(payload: dict[str, Any]) -> BridgeConfig:
    values = dict(payload)
    values["rhos"] = tuple(float(value) for value in values["rhos"])
    values["effects"] = tuple(float(value) for value in values["effects"])
    return BridgeConfig(**values)


def _reconstruct(
    run: dict[str, Any], seeds: dict[str, Any]
) -> tuple[
    BridgeConfig,
    goal007.FixedInputs,
    tuple[tuple[str, goal007.FixedInputs], ...],
    tuple[str, ...],
]:
    mode = run.get("mode")
    production = mode == "production" and run.get("is_production") is True
    if production:
        if run.get("outcome") != "production_pending_numerical_review":
            raise ValueError("production summary is not pending numerical review")
    elif (
        mode != "pilot"
        or run.get("outcome") != "non_scientific_pilot"
        or run.get("is_production") is not False
    ):
        raise ValueError("summary must be a non-scientific pilot or admitted production review")
    if (
        run.get("workflow") != "arc3-landscape-sampling-campaign"
        or run.get("schema_version") != 1
        or run.get("designs") != ["access", "balanced"]
        or run.get("lanes") != ["known_speed", "estimated_speed"]
        or not isinstance(run.get("invariants"), dict)
        or not all(run["invariants"].values())
    ):
        raise ValueError("campaign summary is incomplete or fails its implementation invariants")
    config = _config(run["config"])
    scene = run.get("scene_metadata")
    if not isinstance(scene, dict):
        raise ValueError("campaign summary lacks scene metadata")
    if production:
        freeze = scene.get("production_freeze")
        provenance = run.get("source_provenance")
        if not isinstance(freeze, dict) or not isinstance(provenance, dict):
            raise ValueError("production summary lacks its production freeze")
        _, freeze_sha = arc3.validate_production_freeze(config, scene, freeze)
        if any(
            holder.get("production_freeze_sha256") != freeze_sha
            or holder.get("production_freeze") != freeze
            for holder in (scene, provenance)
        ):
            raise ValueError("production freeze hash is not reconciled in campaign provenance")
    archetype_value = scene.get("archetype")
    map_seed_value = scene.get("map_seed")
    sampling_seed_value = scene.get("sampling_seed")
    if archetype_value not in ARCHETYPES or not all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in (map_seed_value, sampling_seed_value)
    ):
        raise ValueError("pilot scene has invalid archetype or seeds")
    archetype = str(archetype_value)
    map_seed = cast(int, map_seed_value)
    sampling_seed = cast(int, sampling_seed_value)
    expected_sampling_seed = int(
        np.random.SeedSequence([MASTER_SEED, map_seed, 1]).generate_state(1)[0]
    )
    expected_campaign_seed = int(
        np.random.SeedSequence(
            [MASTER_SEED, map_seed, ARCHETYPES.index(archetype), 2]
        ).generate_state(1)[0]
    )
    if sampling_seed != expected_sampling_seed or config.master_seed != expected_campaign_seed:
        raise ValueError("pilot sampling or campaign seed is not the frozen Arc 3 branch")
    landscape = build_landscape(archetype, map_seed)
    if scene.get("landscape_descriptors") != describe_landscape(landscape):
        raise ValueError("reconstructed landscape descriptors disagree with the pilot")
    access, balanced = build_sampling_pair(landscape, sampling_seed)
    access_coordinates, access_ordered = arc3._validate_design(access, landscape)
    balanced_coordinates, balanced_ordered = arc3._validate_design(balanced, landscape)
    access = arc3._canonical_design(access, access_ordered)
    balanced = arc3._canonical_design(balanced, balanced_ordered)
    union = arc3._union_design(access, access_coordinates, balanced_coordinates)
    site_ids = tuple(site.site_id for site in union.sites)
    union_fixed = goal007.FixedInputs(landscape, union, {"design_valid": True})
    designs = (
        ("access", goal007.FixedInputs(landscape, access, {"design_valid": True})),
        ("balanced", goal007.FixedInputs(landscape, balanced, {"design_valid": True})),
    )
    manifest = spawn_seed_manifest(config)
    expected_truths = [asdict(value) for value in arc3._truths()]
    if (
        run.get("truths") != expected_truths
        or run.get("counts", {}).get("conditions") != len(expected_truths)
        or seeds.get("master_seed") != config.master_seed
        or seeds.get("bank_size") != config.bank_size
        or seeds.get("bank_seeds") != list(manifest.bank_seeds)
        or seeds.get("calibration_seeds") != [asdict(value) for value in manifest.calibration]
        or seeds.get("validation_seeds") != [asdict(value) for value in manifest.validation]
        or seeds.get("site_ids") != list(site_ids)
        or seeds.get("scene_metadata") != scene
        or seeds.get("source_commit") != run.get("source_commit")
        or seeds.get("source_provenance") != run.get("source_provenance")
    ):
        raise ValueError("seed provenance disagrees with the reconstructed Arc 3 campaign")
    return config, union_fixed, designs, site_ids


def _load_bundle(
    pilot_dir: Path,
) -> tuple[
    BridgeConfig,
    dict[str, NDArray[Any]],
    FloatArray,
    dict[str, Any],
    goal007.FixedInputs,
    tuple[tuple[str, goal007.FixedInputs], ...],
    tuple[str, ...],
    dict[str, Any],
]:
    run = _load_json(pilot_dir / "run_summary.json")
    seeds = _load_json(pilot_dir / "seed_provenance.json")
    profile_path = pilot_dir / "profiles.npz"
    bank_path = pilot_dir / arc3.BANK_FILENAME
    config, union_fixed, designs, site_ids = _reconstruct(run, seeds)
    if run.get("profile_bundle_sha256") != _sha256(profile_path):
        raise ValueError("pilot profile hash does not match its run summary")
    with np.load(profile_path, allow_pickle=False) as saved:
        profiles = {name: saved[name].copy() for name in saved.files}
    bank = np.ascontiguousarray(np.load(bank_path, allow_pickle=False), dtype=np.float64)
    bank_checksum = hashlib.sha256(bank.tobytes(order="C")).hexdigest()
    if (
        bank.shape != (config.bank_size, len(site_ids))
        or not np.isfinite(bank).all()
        or (bank < 0).any()
        or run.get("bank_checksum") != bank_checksum
        or seeds.get("bank_checksum") != bank_checksum
        or profiles.get("condition_ids", np.asarray([])).tolist()
        != [truth["condition_id"] for truth in run["truths"]]
        or not np.array_equal(profiles["rhos"], np.asarray(config.rhos))
        or not np.array_equal(profiles["effects"], np.asarray(config.effects))
        or profiles.get("design_ids", np.asarray([])).tolist()
        != [truth.condition_id.rsplit("_", 1)[0] for truth in arc3._truths()]
        or profiles.get("truth_effects", np.asarray([])).tolist()
        != [truth.effect for truth in arc3._truths()]
        or profiles.get("truth_rhos", np.asarray([])).tolist()
        != [truth.rho for truth in arc3._truths()]
    ):
        raise ValueError("pilot bank or profile axes disagree with their receipts")
    return config, profiles, bank, run, union_fixed, designs, site_ids, seeds


def _surface_block(
    profiles: dict[str, NDArray[Any]], *, histories_per_phase: int | None = None
) -> FloatArray:
    calibration = np.asarray(profiles["calibration_train_joint"], dtype=np.float64)
    validation = np.asarray(profiles["validation_train_joint"], dtype=np.float64)
    if histories_per_phase is not None:
        calibration = calibration[:, :histories_per_phase]
        validation = validation[:, :histories_per_phase]
    # Saved axes are condition, history, rho, effect.  Review axes are
    # history (calibration 0/1 then evaluation 0/1), condition, rho, effect.
    return np.concatenate((calibration, validation), axis=1).swapaxes(0, 1)


def _validate_reference_bundle(
    selected: tuple[
        BridgeConfig,
        dict[str, NDArray[Any]],
        FloatArray,
        dict[str, Any],
        goal007.FixedInputs,
        tuple[tuple[str, goal007.FixedInputs], ...],
        tuple[str, ...],
        dict[str, Any],
    ],
    reference: tuple[
        BridgeConfig,
        dict[str, NDArray[Any]],
        FloatArray,
        dict[str, Any],
        goal007.FixedInputs,
        tuple[tuple[str, goal007.FixedInputs], ...],
        tuple[str, ...],
        dict[str, Any],
    ],
    *,
    adoption: dict[str, Any] | None = None,
) -> None:
    """Reconcile a saved doubled bundle before reusing its first two histories."""
    (
        selected_config,
        selected_profiles,
        selected_bank,
        selected_run,
        _,
        _,
        selected_sites,
        selected_seeds,
    ) = selected
    (
        reference_config,
        reference_profiles,
        reference_bank,
        reference_run,
        _,
        _,
        reference_sites,
        reference_seeds,
    ) = reference
    if selected_run.get("mode") != reference_run.get("mode"):
        raise ValueError("selected and reference bundles use different campaign modes")
    for name in (
        "workflow",
        "schema_version",
        "designs",
        "lanes",
        "truths",
        "source_commit",
    ):
        if selected_run.get(name) != reference_run.get(name):
            raise ValueError(f"selected and reference bundles differ in {name}")
    if adoption is None:
        for name in ("scene_metadata", "source_provenance"):
            if selected_run.get(name) != reference_run.get(name):
                raise ValueError(f"selected and reference bundles differ in {name}")
    if selected_sites != reference_sites:
        raise ValueError("selected and reference bundles differ in site IDs")
    for name in (
        "master_seed",
        "calibration_seeds",
        "validation_seeds",
        "site_ids",
    ):
        if selected_seeds.get(name) != reference_seeds.get(name):
            raise ValueError(f"selected and reference seed provenance differs in {name}")
    if adoption is None and selected_seeds.get("scene_metadata") != reference_seeds.get(
        "scene_metadata"
    ):
        raise ValueError("selected and reference seed provenance differs in scene_metadata")
    for name in (
        "master_seed",
        "calibration_replicates",
        "validation_replicates",
        "calibration_rank",
        "rhos",
        "effects",
    ):
        if getattr(selected_config, name) != getattr(reference_config, name):
            raise ValueError(f"selected and reference configs differ in {name}")
    if reference_config.bank_size != 2 * selected_config.bank_size:
        raise ValueError("reference config bank size is not twice the selected bank size")
    if reference_bank.shape[1] != selected_bank.shape[1] or not np.array_equal(
        reference_bank[: selected_bank.shape[0]], selected_bank
    ):
        raise ValueError("reference arrival bank does not preserve the selected prefix")
    if reference_seeds.get("bank_seeds", [])[: selected_config.bank_size] != selected_seeds.get(
        "bank_seeds"
    ):
        raise ValueError("reference bank seed schedule does not preserve the selected prefix")
    for name in (
        "rhos",
        "effects",
        "condition_ids",
        "design_ids",
        "truth_effects",
        "truth_rhos",
    ):
        if not np.array_equal(selected_profiles[name], reference_profiles[name]):
            raise ValueError(f"selected and reference profile axes differ in {name}")
    doubled = _surface_block(reference_profiles, histories_per_phase=2)
    if doubled.shape[:2] != (4, 6):
        raise ValueError("reference bundle lacks two calibration and two evaluation histories")


def _evaluate(
    union_fixed: goal007.FixedInputs,
    designs: tuple[tuple[str, goal007.FixedInputs], ...],
    history_seeds: tuple[arc2b.DatasetSeed, ...],
    integration: Any,
) -> FloatArray:
    truths = arc3._truths()
    surfaces = []
    for seed in history_seeds:
        block = arc3._dataset_task(union_fixed, designs, seed, integration, truths)
        if block.training_joint is None:
            raise RuntimeError("review histories did not retain their training surfaces")
        surfaces.append(block.training_joint)
    return np.stack(surfaces)


def _index(grid: FloatArray, value: float) -> int:
    matches = np.flatnonzero(np.isclose(grid, value, rtol=0.0, atol=1e-12))
    if len(matches) != 1:
        raise ValueError("truth is absent or duplicated on the candidate grid")
    return int(matches[0])


def _build_integration(
    bank: NDArray[np.float64],
    site_ids: tuple[str, ...],
    rhos: tuple[float, ...],
    effects: tuple[float, ...],
    *,
    workers: int,
) -> Any:
    """Build an integration with no more workers than rho slices."""
    return arc3._build_joint_integration(
        bank,
        site_ids,
        rhos,
        effects,
        background_hazard=BACKGROUND_HAZARD,
        workers=min(workers, max(1, len(rhos))),
    )


def _announce(progress: Progress | None, message: str) -> None:
    if progress is not None:
        progress(message)


def run_check(
    pilot_dir: Path,
    output: Path,
    *,
    bank_only: bool = False,
    workers: int = 1,
    progress: Progress | None = None,
    reference_dir: Path | None = None,
    adoption_receipt: Path | None = None,
) -> dict[str, Any]:
    """Run the bounded replay and write JSON plus a profile sidecar."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    started = time.perf_counter()
    runtimes: dict[str, float] = {}
    bundle_dirs = (pilot_dir,) if reference_dir is None else (pilot_dir, reference_dir)
    if adoption_receipt is not None and reference_dir is None:
        raise ValueError("adoption receipt requires an existing reference bundle")
    protected = {
        (directory / name).resolve()
        for directory in bundle_dirs
        for name in (*arc3.EXPECTED_FILES, arc3.BANK_FILENAME)
    }
    profile_path = output.with_suffix(".npz")
    if output.resolve() in protected or profile_path.resolve() in protected:
        raise ValueError("numerical review outputs cannot overwrite pilot evidence")
    selected_bundle = _load_bundle(pilot_dir)
    adoption = (
        validate_adoption(pilot_dir, reference_dir, adoption_receipt)
        if adoption_receipt is not None and reference_dir is not None
        else None
    )
    config, profiles, bank, run, union_fixed, designs, site_ids, _ = selected_bundle
    if run.get("mode") == "production" and bank_only:
        raise ValueError("production numerical review cannot skip half-grid checks")
    manifest = spawn_seed_manifest(config)
    history_seeds = (*manifest.calibration[:2], *manifest.validation[:2])
    reference = _surface_block(profiles, histories_per_phase=2)
    if reference.shape[:2] != (4, 6):
        raise ValueError("pilot must retain two histories per phase for all six conditions")
    phase_started = time.perf_counter()
    current_integration = _build_integration(
        bank, site_ids, config.rhos, config.effects, workers=workers
    )
    runtimes["replay_integration"] = time.perf_counter() - phase_started
    phase_started = time.perf_counter()
    replay = _evaluate(union_fixed, designs, history_seeds, current_integration)
    runtimes["replay"] = time.perf_counter() - phase_started
    del current_integration
    if not np.allclose(replay, reference, rtol=0.0, atol=1e-9):
        raise ValueError("reconstructed map, sampling pair, histories, or bank fails exact replay")
    _announce(progress, "replay passed")

    runtimes["extra_bank"] = 0.0
    runtimes["doubled_integration"] = 0.0
    runtimes["doubled_evaluation"] = 0.0
    if reference_dir is None:
        doubled_config = replace(config, bank_size=2 * config.bank_size)
        doubled_manifest = spawn_seed_manifest(doubled_config)
        if doubled_manifest.bank_seeds[: config.bank_size] != manifest.bank_seeds:
            raise ValueError("doubled bank seed schedule does not preserve the pilot prefix")
        phase_started = time.perf_counter()
        extra = arc2b._generate_bank(union_fixed, doubled_manifest.bank_seeds[config.bank_size :])
        runtimes["extra_bank"] = time.perf_counter() - phase_started
        _announce(progress, f"extra-bank ready draws={len(extra)}")
        doubled_bank = np.ascontiguousarray(np.concatenate((bank, extra)), dtype=np.float64)
        phase_started = time.perf_counter()
        doubled_integration = _build_integration(
            doubled_bank, site_ids, config.rhos, config.effects, workers=workers
        )
        runtimes["doubled_integration"] = time.perf_counter() - phase_started
        phase_started = time.perf_counter()
        doubled = _evaluate(union_fixed, designs, history_seeds, doubled_integration)
        runtimes["doubled_evaluation"] = time.perf_counter() - phase_started
        del doubled_integration, doubled_bank, extra
        _announce(progress, "doubled-integration passed")
        reference_info = None
    else:
        reference_bundle = _load_bundle(reference_dir)
        _validate_reference_bundle(selected_bundle, reference_bundle, adoption=adoption)
        reference_config, reference_profiles, _, _, _, _, _, _ = reference_bundle
        if reference_config.bank_size != 2 * config.bank_size:
            raise ValueError("reference bundle is not the selected bank doubled")
        doubled = _surface_block(reference_profiles, histories_per_phase=2)
        reference_info = {
            "directory": str(reference_dir),
            "profile_sha256": reference_bundle[3].get("profile_bundle_sha256"),
            "bank_sha256": reference_bundle[3].get("bank_checksum"),
        }
        _announce(progress, "doubled-integration loaded reference")
    rhos = np.asarray(config.rhos, dtype=np.float64)
    effects = np.asarray(config.effects, dtype=np.float64)
    truths = arc3._truths()

    rho_profiles_old = reference.max(axis=3)
    rho_profiles_new = doubled.max(axis=3)

    merged_rhos = rhos
    merged_effects = effects
    rho_refined = reference
    effect_refined = reference
    fine_rhos = np.asarray([], dtype=np.float64)
    fine_effects = np.asarray([], dtype=np.float64)
    runtimes["rho_refinement"] = 0.0
    runtimes["effect_refinement"] = 0.0
    if not bank_only:
        fine_rhos = np.asarray(
            half_grid(
                rhos,
                rho_profiles_old,
                rho_profiles_new,
                (1.0,),
                geometric=True,
            )
        )
        phase_started = time.perf_counter()
        rho_integration = _build_integration(
            bank, site_ids, tuple(fine_rhos), config.effects, workers=workers
        )
        rho_subset = _evaluate(union_fixed, designs, history_seeds, rho_integration)
        del rho_integration
        runtimes["rho_refinement"] = time.perf_counter() - phase_started
        retained_rho = np.isin(fine_rhos, rhos)
        if not np.allclose(
            rho_subset[:, :, retained_rho, :],
            reference[:, :, np.searchsorted(rhos, fine_rhos[retained_rho]), :],
            rtol=0.0,
            atol=1e-9,
        ):
            raise ValueError("rho refinement disagrees at retained original nodes")
        merged_rhos, rho_refined = merge_axis(rhos, reference, fine_rhos, rho_subset, axis=2)

        fine_effects = np.asarray(
            local_effect_half_grid(
                effects,
                reference,
                doubled,
                _index(rhos, 1.0),
                tuple(sorted({truth.effect for truth in truths})),
            )
        )
        phase_started = time.perf_counter()
        effect_integration = _build_integration(
            bank, site_ids, config.rhos, tuple(fine_effects), workers=workers
        )
        effect_subset = _evaluate(union_fixed, designs, history_seeds, effect_integration)
        del effect_integration
        runtimes["effect_refinement"] = time.perf_counter() - phase_started
        retained_effect = np.isin(fine_effects, effects)
        if not np.allclose(
            effect_subset[:, :, :, retained_effect],
            reference[:, :, :, np.searchsorted(effects, fine_effects[retained_effect])],
            rtol=0.0,
            atol=1e-9,
        ):
            raise ValueError("effect refinement disagrees at retained original nodes")
        merged_effects, effect_refined = merge_axis(
            effects, reference, fine_effects, effect_subset, axis=3
        )
        _announce(progress, "rho-refinement and effect-refinement passed")
    else:
        _announce(progress, "refinement skipped bank-only")

    rows: list[dict[str, Any]] = []
    phases = ("calibration", "calibration", "evaluation", "evaluation")
    indices = (0, 1, 0, 1)
    for history_index, (phase, dataset_index) in enumerate(zip(phases, indices, strict=True)):
        for condition_index, truth in enumerate(truths):
            baseline = reference[history_index, condition_index]
            nested = doubled[history_index, condition_index]
            true_rho = _index(rhos, truth.rho)
            true_effect = _index(effects, truth.effect)
            old_rho, old_effect = np.unravel_index(np.argmax(baseline), baseline.shape)
            new_rho, new_effect = np.unravel_index(np.argmax(nested), nested.shape)
            old_known_effect = int(np.argmax(baseline[true_rho]))
            new_known_effect = int(np.argmax(nested[true_rho]))
            effect_movement = float(
                max(
                    abs(effects[new_effect] - effects[old_effect]),
                    abs(effects[new_known_effect] - effects[old_known_effect]),
                )
            )
            rho_movement = float(abs(np.log(rhos[new_rho] / rhos[old_rho])))
            profile_movements = {
                "known_effect": profile_change(baseline[true_rho], nested[true_rho]),
                "estimated_effect": profile_change(baseline.max(axis=0), nested.max(axis=0)),
                "rho": profile_change(baseline.max(axis=1), nested.max(axis=1)),
            }
            truth_movements = np.abs(
                truth_lrs(baseline, true_rho, true_effect)
                - truth_lrs(nested, true_rho, true_effect)
            )
            rho_gain = None
            effect_gains = None
            refinement_pass = True
            if not bank_only:
                refined_rho_joint = rho_refined[history_index, condition_index]
                refined_effect_joint = effect_refined[history_index, condition_index]
                rho_gain = float(max(0.0, refined_rho_joint.max() - baseline.max()))
                effect_gains = {
                    "known_speed": float(
                        max(
                            0.0,
                            refined_effect_joint[true_rho].max() - baseline[true_rho].max(),
                        )
                    ),
                    "estimated_speed": float(max(0.0, refined_effect_joint.max() - baseline.max())),
                }
                refinement_pass = max(rho_gain, *effect_gains.values()) <= REFINEMENT_GAIN_LIMIT
            within = bool(
                effect_movement <= EFFECT_MLE_LIMIT + 1e-12
                and rho_movement <= RHO_LOG_MLE_LIMIT + 1e-12
                and max(profile_movements.values()) <= PROFILE_LR_LIMIT
                and float(truth_movements.max()) <= TRUTH_LR_LIMIT
                and refinement_pass
            )
            rows.append(
                {
                    "phase": phase,
                    "dataset_index": dataset_index,
                    "condition_id": truth.condition_id,
                    "design": truth.condition_id.rsplit("_", 1)[0],
                    "effect_truth": truth.effect,
                    "bank_effect_max_absolute_mle_change": effect_movement,
                    "bank_rho_absolute_log_mle_change": rho_movement,
                    "bank_profile_lr_changes_on_union_within_10": profile_movements,
                    "bank_truth_lr_changes": dict(
                        zip(
                            ("known_effect", "estimated_effect", "rho"),
                            truth_movements.tolist(),
                            strict=True,
                        )
                    ),
                    "rho_half_grid_max_log_likelihood_gain": rho_gain,
                    "effect_half_grid_max_log_likelihood_gains": effect_gains,
                    "within_pilot_numerical_limits": within,
                }
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        profile_path,
        rhos=rhos,
        effects=effects,
        refined_rhos=merged_rhos,
        refined_effects=merged_effects,
        rho_refinement_subset=fine_rhos,
        effect_refinement_subset=fine_effects,
        current_joint=reference,
        replay_joint=replay,
        doubled_joint=doubled,
        rho_refined_joint=rho_refined,
        effect_refined_joint=effect_refined,
    )
    runtimes["refinement"] = runtimes["rho_refinement"] + runtimes["effect_refinement"]
    runtimes["total"] = time.perf_counter() - started
    _announce(progress, f"numerical review completed total_seconds={runtimes['total']:.3f}")
    payload = {
        "workflow": "arc3-bounded-numerical-pilot-check",
        "status": "incomplete_numerical_review",
        "scope": (
            "first two calibration and first two evaluation histories across both designs "
            "and all three effects; no full-ensemble cutoff, support, coverage, exclusion, "
            "sampling-contrast, or scientific acceptance"
        ),
        "bank_only": bank_only,
        "workers": workers,
        "runtimes_seconds": runtimes,
        "reference_bundle": reference_info,
        "adoption": adoption,
        "bank_sizes": [config.bank_size, 2 * config.bank_size],
        "review_limits": {
            "effect_mle_absolute_change": EFFECT_MLE_LIMIT,
            "rho_mle_absolute_log_change": RHO_LOG_MLE_LIMIT,
            "profile_lr_change_on_union_within_10": PROFILE_LR_LIMIT,
            "truth_lr_change": TRUTH_LR_LIMIT,
            "separate_half_grid_max_log_likelihood_gain": REFINEMENT_GAIN_LIMIT,
        },
        "conditions": rows,
        "pilot_source_commit": run.get("source_commit"),
        "pilot_profile_sha256": run.get("profile_bundle_sha256"),
        "pilot_bank_sha256": run.get("bank_checksum"),
        "source_provenance_review": _source_review(run),
        "diagnostic_profiles": profile_path.name,
        "diagnostic_profile_sha256": _sha256(profile_path),
        "all_within_pilot_limits": all(row["within_pilot_numerical_limits"] for row in rows),
        "full_ensemble_review_required": True,
        "scientific_acceptance_authorized": False,
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-dir", type=Path, required=True)
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=None,
        help="existing doubled-bank production bundle to reuse instead of rebuilding it",
    )
    parser.add_argument(
        "--adoption-receipt",
        type=Path,
        default=None,
        help="explicit immutable old-reference to new-reference adoption receipt",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=_positive_int, default=1)
    parser.add_argument(
        "--bank-only",
        action="store_true",
        help="skip half-grid refinements while retaining the incomplete-review label",
    )
    args = parser.parse_args()
    try:
        payload = run_check(
            args.pilot_dir,
            args.output,
            bank_only=args.bank_only,
            workers=args.workers,
            progress=lambda message: print(message, flush=True),
            reference_dir=args.reference_dir,
            adoption_receipt=args.adoption_receipt,
        )
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        parser.exit(1, f"Arc 3 numerical pilot check failed: {error}\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "all_within_pilot_limits": payload["all_within_pilot_limits"],
                "output": str(args.output),
            }
        )
    )
    return 0 if payload["all_within_pilot_limits"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
