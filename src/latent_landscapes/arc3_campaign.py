"""Paired Arc 3 landscape and sampling campaign adapter.

Arc 3 changes the sampling design while reusing the accepted Arc 2C
simulation and likelihood kernels.  The adapter builds one physical-site
union, simulates that union once per dataset, and evaluates each design on its
own 120/40 subset of the same realised histories.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import arc2c_campaign as arc2c
from latent_landscapes import arc2c_likelihood as likelihood
from latent_landscapes import arc3_design
from latent_landscapes.arc2c_design import (
    BACKGROUND_HAZARD,
    EFFECT_GRID,
    LANES,
    RHO_GRID,
    TRUTHS,
    BridgeConfig,
    BridgeTruth,
)
from latent_landscapes.arc3_design import PRODUCTION_MAP_SEEDS
from latent_landscapes.arc3_landscapes import ARCHETYPES
from latent_landscapes.goal001.design import SamplingDesign
from latent_landscapes.goal001.landscape import Landscape
from latent_landscapes.goal007 import benchmark as goal007

DEFAULT_OUTPUT_DIR = Path("artifacts/arc3_campaign")
DEFAULT_CONFIG = BridgeConfig(
    master_seed=arc3_design.MASTER_SEED,
    bank_size=32,
    calibration_replicates=2,
    validation_replicates=2,
    calibration_rank=2,
    rhos=(0.5, 1.0, 2.0),
    effects=(1.0, 3.0, 5.0),
)
EXPECTED_FILES = ("profiles.npz", "run_summary.json", "seed_provenance.json")
BANK_FILENAME = "base_arrivals.npy"
DESIGN_IDS = arc3_design.DESIGN_IDS
ARC3_EFFECT_TRUTHS = TRUTHS[:3]
EVENT_DIAGNOSTICS = arc2c.EVENT_DIAGNOSTICS
RunMode = Literal["pilot", "production"]
Progress = Callable[[str], None]
ProfileBundle = dict[str, NDArray[Any]]
PRODUCTION_GOAL = "046"
PRODUCTION_SCHEMA_VERSION = 1
PRODUCTION_SELECTED_BANK_SIZES = (16384, 32768, 65536)
PRODUCTION_CALIBRATION_REPLICATES = 250
PRODUCTION_VALIDATION_REPLICATES = 250
PRODUCTION_CALIBRATION_RANK = 239


def _build_joint_integration(
    bank: NDArray[np.float64],
    site_ids: tuple[str, ...],
    rhos: tuple[float, ...],
    effects: tuple[float, ...],
    *,
    background_hazard: float,
    workers: int,
) -> likelihood.BridgeIntegration:
    """Build rho slices with a bounded pool while preserving serial bytes."""

    if workers <= 0:
        raise ValueError("workers must be positive")
    if workers == 1:
        return likelihood.build_joint_integration(
            bank, site_ids, rhos, effects, background_hazard=background_hazard
        )

    def build_rho_slice(rho: float) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        integrated = arc2b.build_arrival_integration(
            bank / rho,
            site_ids,
            effects,
            background_hazard,
        )
        # Do not return the integration object: it retains the scaled bank.
        return integrated.category_mass, integrated.survival_moments

    masses = np.empty((len(rhos), len(site_ids), arc2b.CATEGORY_COUNT), dtype=np.float64)
    moments: list[NDArray[np.float64] | None] = [None] * len(rhos)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # executor.map preserves candidate order, so serial and parallel
        # assembly use identical rho indices and byte values.
        for rho_index, (category_mass, survival_moments) in enumerate(
            executor.map(build_rho_slice, rhos)
        ):
            masses[rho_index] = category_mass
            moments[rho_index] = survival_moments
    if any(value is None for value in moments):
        raise RuntimeError("rho integration did not return every candidate slice")
    checksum = hashlib.sha256(bank.tobytes(order="C")).hexdigest()
    return likelihood.BridgeIntegration(
        tuple(float(value) for value in rhos),
        tuple(float(value) for value in effects),
        tuple(site_ids),
        masses,
        tuple(value for value in moments if value is not None),
        checksum,
    )


@dataclass(frozen=True, slots=True)
class CampaignResult:
    config: BridgeConfig
    mode: RunMode
    seed_manifest: arc2b.SeedManifest
    truths: tuple[BridgeTruth, ...]
    profiles: ProfileBundle
    invariants: dict[str, bool]
    workers: int
    runtime_seconds: float
    bank_runtime_seconds: float
    integration_runtime_seconds: float
    calibration_runtime_seconds: float
    validation_runtime_seconds: float
    source_commit: str
    source_provenance: dict[str, Any]
    scene_metadata: dict[str, Any]
    bank_checksum: str
    site_ids: tuple[str, ...]
    base_arrivals: NDArray[np.float64]

    @property
    def outcome(self) -> str:
        if not all(self.invariants.values()):
            return "implementation_blocked"
        if self.mode == "production":
            return "production_pending_numerical_review"
        return "non_scientific_pilot"


def _canonical_id(row: int, col: int) -> str:
    return arc3_design.coordinate_id(row, col)


def _site_coordinates(design: SamplingDesign, landscape: Landscape) -> dict[tuple[int, int], Any]:
    if len(design.sites) != 160:
        raise ValueError("each Arc 3 design must contain exactly 160 sites")
    coordinates: dict[tuple[int, int], Any] = {}
    for site in design.sites:
        coordinate = (int(site.row), int(site.col))
        if coordinate in coordinates:
            raise ValueError("sampling design contains duplicate physical coordinates")
        row, col = coordinate
        if not (0 <= row < landscape.rows and 0 <= col < landscape.cols):
            raise ValueError("sampling site lies outside the landscape")
        if not landscape.passable[row, col]:
            raise ValueError("sampling design contains an impassable site")
        if not landscape.source_reachable[row, col]:
            raise ValueError("sampling design contains a source-unreachable site")
        coordinates[coordinate] = site
    return coordinates


def _validate_design(
    design: SamplingDesign, landscape: Landscape
) -> tuple[dict[tuple[int, int], Any], tuple[Any, ...]]:
    coordinates = _site_coordinates(design, landscape)
    training = [site for site in design.sites if site.split == "training"]
    holdout = [site for site in design.sites if site.split == "holdout"]
    if len(training) != 120 or len(holdout) != 40:
        raise ValueError("each Arc 3 design must contain 120 training and 40 holdout sites")
    if {site.cluster_id for site in training}.intersection(site.cluster_id for site in holdout):
        raise ValueError("training and holdout clusters must be disjoint")
    for cluster_id in {site.cluster_id for site in design.sites}:
        splits = {site.split for site in design.sites if site.cluster_id == cluster_id}
        if splits != {"training"} and splits != {"holdout"}:
            raise ValueError("a sampling cluster cannot cross the training/holdout split")
    ordered = tuple(sorted(design.sites, key=lambda site: _canonical_id(site.row, site.col)))
    if tuple(_canonical_id(site.row, site.col) for site in ordered) != tuple(
        _canonical_id(row, col) for row, col in sorted(coordinates)
    ):
        raise RuntimeError("canonical site ordering could not be established")
    return coordinates, ordered


def _canonical_design(design: SamplingDesign, ordered_sites: Sequence[Any]) -> SamplingDesign:
    return replace(
        design,
        sites=tuple(
            replace(site, site_id=_canonical_id(int(site.row), int(site.col)))
            for site in ordered_sites
        ),
    )


def _union_design(
    access: SamplingDesign,
    access_sites: Mapping[tuple[int, int], Any],
    balanced_sites: Mapping[tuple[int, int], Any],
) -> SamplingDesign:
    coordinates = set(access_sites) | set(balanced_sites)
    site_lookup = dict(access_sites)
    site_lookup.update(balanced_sites)
    union_sites = [
        replace(
            site_lookup[coordinate],
            site_id=_canonical_id(*coordinate),
            split=(
                "holdout"
                if coordinate in access_sites and access_sites[coordinate].split == "holdout"
                else "training"
            ),
        )
        for coordinate in sorted(coordinates)
    ]
    # The union is only used to generate physical histories.  Its metadata is
    # replaced back to the requested design before likelihood evaluation.
    return replace(access, sites=tuple(union_sites))


def _truths() -> tuple[BridgeTruth, ...]:
    return tuple(
        BridgeTruth(f"{design}_{int(truth.effect)}", 1.0, truth.effect, truth.role)
        for design in DESIGN_IDS
        for truth in ARC3_EFFECT_TRUTHS
    )


def _map_histories(
    histories: tuple[arc2b.CrossLayerHistory, ...],
    sites: Sequence[Any],
) -> tuple[arc2b.CrossLayerHistory, ...]:
    by_coordinate = {(row.row, row.col): row for row in histories}
    mapped: list[arc2b.CrossLayerHistory] = []
    ordered_sites = sorted(sites, key=lambda value: _canonical_id(value.row, value.col))
    for index, site in enumerate(ordered_sites):
        key = (int(site.row), int(site.col))
        row = by_coordinate.get(key)
        if row is None:
            raise ValueError("design site is absent from the union history")
        mapped.append(
            replace(
                row,
                site_index=index,
                site_id=_canonical_id(*key),
                cluster_id=site.cluster_id,
                split=site.split,
                row=key[0],
                col=key[1],
            )
        )
    if len(mapped) != 160:
        raise RuntimeError("mapped history does not contain 160 sites")
    return tuple(mapped)


def _observations_equal(left: Any, right: Any) -> bool:
    return bool(
        left.site_id == right.site_id
        and left.true_predator_arrival == right.true_predator_arrival
        and left.true_prey_extirpation == right.true_prey_extirpation
        and left.predator_detection_counts == right.predator_detection_counts
        and left.prey_detection_counts == right.prey_detection_counts
        and left.true_predator_present == right.true_predator_present
        and left.true_prey_alive == right.true_prey_alive
    )


def _pairing_valid(
    histories_by_design: tuple[tuple[tuple[arc2b.CrossLayerHistory, ...], ...], ...],
    access_coordinates: Mapping[tuple[int, int], Any],
    balanced_coordinates: Mapping[tuple[int, int], Any],
) -> bool:
    if len(histories_by_design) != 2 or any(len(rows) != 3 for rows in histories_by_design):
        return False
    for design_histories in histories_by_design:
        if any(not arc2b._histories_valid(rows) for rows in design_histories):
            return False
    common = set(access_coordinates).intersection(balanced_coordinates)
    holdout = {
        coordinate for coordinate, site in access_coordinates.items() if site.split == "holdout"
    }
    if holdout != {
        coordinate for coordinate, site in balanced_coordinates.items() if site.split == "holdout"
    }:
        return False
    for effect_index in range(3):
        access = {(row.row, row.col): row for row in histories_by_design[0][effect_index]}
        balanced = {(row.row, row.col): row for row in histories_by_design[1][effect_index]}
        if any(not _observations_equal(access[key], balanced[key]) for key in common):
            return False
        if any(not _observations_equal(access[key], balanced[key]) for key in holdout):
            return False
    for histories in histories_by_design:
        reference = histories[0]
        for rows in histories[1:]:
            if any(
                left.true_predator_arrival != right.true_predator_arrival
                or left.predator_detection_counts != right.predator_detection_counts
                for left, right in zip(reference, rows, strict=True)
            ):
                return False
    return True


def _dataset_task(
    union_fixed: goal007.FixedInputs,
    designs: tuple[tuple[str, goal007.FixedInputs], ...],
    seed: arc2b.DatasetSeed,
    integration: likelihood.BridgeIntegration,
    truths: tuple[BridgeTruth, ...],
) -> arc2c.DatasetBlock:
    union_histories = likelihood.paired_histories(union_fixed, seed)[:3]
    mapped = tuple(
        tuple(_map_histories(rows, fixed.design.sites) for rows in union_histories)
        for _, fixed in designs
    )
    profiles: list[arc2c.DatasetProfiles] = []
    diagnostics: list[tuple[int, int, int, int, float, int]] = []
    saved_training: list[NDArray[np.float64]] = []
    truth_index = 0
    for design_index, _ in enumerate(designs):
        for _effect_index, records in enumerate(mapped[design_index]):
            training_joint, holdout_joint, holdout_predator = likelihood.evaluate_dataset(
                records, integration
            )
            profiles.append(
                arc2c.profile_dataset(
                    training_joint,
                    holdout_joint,
                    holdout_predator,
                    rhos=np.asarray(integration.rhos),
                    effects=np.asarray(integration.effects),
                    truth=truths[truth_index],
                )
            )
            diagnostics.append(
                arc2b._extirpation_metrics(tuple(row for row in records if row.split == "training"))
            )
            if seed.index < 2:
                saved_training.append(training_joint)
            truth_index += 1
    pairing = _pairing_valid(
        mapped,
        {(site.row, site.col): site for site in designs[0][1].design.sites},
        {(site.row, site.col): site for site in designs[1][1].design.sites},
    )
    return arc2c.DatasetBlock(
        tuple(profiles),
        np.asarray(diagnostics, dtype=np.float64),
        np.stack(saved_training) if seed.index < 2 else None,
        all(arc2b._histories_valid(rows) for history in mapped for rows in history),
        pairing,
    )


def _run_phase(
    union_fixed: goal007.FixedInputs,
    designs: tuple[tuple[str, goal007.FixedInputs], ...],
    seeds: tuple[arc2b.DatasetSeed, ...],
    integration: likelihood.BridgeIntegration,
    truths: tuple[BridgeTruth, ...],
    *,
    workers: int,
    progress: Progress | None,
) -> tuple[arc2c.DatasetBlock, ...]:
    started = time.perf_counter()
    blocks: list[arc2c.DatasetBlock] = []

    def tasks() -> Iterator[arc2c.DatasetBlock]:
        if workers == 1:
            yield from (
                _dataset_task(union_fixed, designs, seed, integration, truths) for seed in seeds
            )
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                yield from executor.map(
                    lambda seed: _dataset_task(union_fixed, designs, seed, integration, truths),
                    seeds,
                )

    for index, block in enumerate(tasks(), start=1):
        blocks.append(block)
        if progress is not None and (index == len(seeds) or index % max(1, len(seeds) // 10) == 0):
            progress(
                f"{seeds[0].phase} completed={index}/{len(seeds)} "
                f"elapsed_seconds={time.perf_counter() - started:.3f}"
            )
    return tuple(blocks)


def _source_provenance(source_commit: str) -> dict[str, Any]:
    paths = (
        Path(__file__),
        Path(arc2b.__file__),
        Path(arc2c.__file__),
        Path(likelihood.__file__),
        Path(__file__).with_name("arc2c_design.py"),
        Path(arc3_design.__file__),
        Path(__file__).with_name("arc3_landscapes.py"),
    )
    hashes = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path.exists()
    }
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", *(str(path) for path in paths)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        head, status = "unknown", ""
    return {
        "head": head,
        "requested_source_commit": source_commit,
        "dirty": bool(status.strip()),
        "active_source_sha256": hashes,
    }


def _validate_supplied_bank(
    bank: NDArray[np.float64],
    manifest: arc2b.SeedManifest,
    site_ids: tuple[str, ...],
    advertised: Mapping[str, Any] | None,
) -> NDArray[np.float64]:
    supplied = np.asarray(bank, dtype=np.float64)
    expected_seeds = list(manifest.bank_seeds)
    expected_checksum = hashlib.sha256(np.ascontiguousarray(supplied).tobytes()).hexdigest()
    if (
        supplied.shape != (len(expected_seeds), len(site_ids))
        or not np.isfinite(supplied).all()
        or (supplied < 0).any()
        or advertised is None
        or advertised.get("bank_seeds") != expected_seeds
        or advertised.get("site_ids") != list(site_ids)
        or advertised.get("bank_checksum") != expected_checksum
    ):
        raise ValueError("supplied arrival bank differs from requested seeds, sites, or checksum")
    return np.ascontiguousarray(supplied)


def _freeze_sha256(production_freeze: Mapping[str, Any]) -> str:
    payload = json.dumps(
        production_freeze, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_production_freeze(
    config: BridgeConfig,
    scene_metadata: Mapping[str, Any] | None,
    production_freeze: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    """Validate the small, parent-issued Goal 046 production admission receipt."""
    if production_freeze is None:
        raise ValueError("production mode requires a valid Goal 046 production freeze")
    freeze = dict(production_freeze)
    if freeze.get("schema_version") != PRODUCTION_SCHEMA_VERSION:
        raise ValueError("production freeze schema version is not supported")
    if freeze.get("goal") != PRODUCTION_GOAL:
        raise ValueError("production freeze is not for Goal 046")
    if freeze.get("master_seed") != arc3_design.MASTER_SEED:
        raise ValueError("production freeze master seed does not match Arc 3")
    if tuple(freeze.get("archetypes", ())) != ARCHETYPES:
        raise ValueError("production freeze archetypes differ from the declared Arc 3 set")
    if tuple(freeze.get("production_map_seeds", ())) != PRODUCTION_MAP_SEEDS:
        raise ValueError("production freeze map seeds differ from the reserved Arc 3 set")
    if freeze.get("selected_bank_size") not in PRODUCTION_SELECTED_BANK_SIZES:
        raise ValueError("production freeze selected bank size is not admitted")
    if freeze.get("reference_bank_size") != 2 * freeze["selected_bank_size"]:
        raise ValueError("production freeze reference bank is not twice the selected bank")
    if tuple(float(value) for value in freeze.get("rhos", ())) != tuple(RHO_GRID):
        raise ValueError("production freeze rho grid differs from G201")
    if tuple(float(value) for value in freeze.get("effects", ())) != tuple(EFFECT_GRID):
        raise ValueError("production freeze effect grid differs from H181")
    if freeze.get("calibration_replicates") != PRODUCTION_CALIBRATION_REPLICATES:
        raise ValueError("production freeze calibration count is not 250")
    if freeze.get("validation_replicates") != PRODUCTION_VALIDATION_REPLICATES:
        raise ValueError("production freeze validation count is not 250")
    if freeze.get("calibration_rank") != PRODUCTION_CALIBRATION_RANK:
        raise ValueError("production freeze calibration rank is not 239")
    qualification = freeze.get("qualification_receipt")
    snapshot_hash = freeze.get("source_snapshot_sha256")
    if not isinstance(qualification, Mapping) or not qualification:
        raise ValueError("production freeze lacks qualification receipt provenance")
    if not isinstance(snapshot_hash, str) or len(snapshot_hash) != 64:
        raise ValueError("production freeze lacks a source snapshot hash")
    try:
        int(snapshot_hash, 16)
        freeze_sha = _freeze_sha256(freeze)
        json.dumps(freeze, sort_keys=True)
    except (TypeError, ValueError) as error:
        raise ValueError("production freeze is not JSON-serializable") from error
    scene = dict(scene_metadata or {})
    archetype = scene.get("archetype")
    map_seed = scene.get("map_seed")
    sampling_seed = scene.get("sampling_seed")
    if archetype not in ARCHETYPES or map_seed not in PRODUCTION_MAP_SEEDS:
        raise ValueError("production scene must use a reserved Arc 3 archetype and map seed")
    if not all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in (map_seed, sampling_seed)
    ):
        raise ValueError("production scene seeds must be integers")
    expected_sampling_seed = int(
        np.random.SeedSequence([arc3_design.MASTER_SEED, map_seed, 1]).generate_state(1)[0]
    )
    expected_campaign_seed = int(
        np.random.SeedSequence(
            [arc3_design.MASTER_SEED, map_seed, ARCHETYPES.index(archetype), 2]
        ).generate_state(1)[0]
    )
    if sampling_seed != expected_sampling_seed or config.master_seed != expected_campaign_seed:
        raise ValueError("production scene or campaign seed is not the frozen Arc 3 branch")
    if config.bank_size not in (
        freeze["selected_bank_size"],
        freeze["reference_bank_size"],
    ):
        raise ValueError("production config bank size is not selected or reference size")
    if (
        config.calibration_replicates != freeze["calibration_replicates"]
        or config.validation_replicates != freeze["validation_replicates"]
        or config.calibration_rank != freeze["calibration_rank"]
        or tuple(config.rhos) != tuple(RHO_GRID)
        or tuple(config.effects) != tuple(EFFECT_GRID)
    ):
        raise ValueError("production config differs from the frozen Arc 3 settings")
    return freeze, freeze_sha


def run_campaign(
    landscape: Landscape,
    access_design: SamplingDesign,
    balanced_design: SamplingDesign,
    config: BridgeConfig | None = None,
    *,
    mode: RunMode = "pilot",
    workers: int = 1,
    source_commit: str = "unknown",
    progress: Progress | None = None,
    supplied_bank: NDArray[np.float64] | None = None,
    supplied_bank_manifest: Mapping[str, Any] | None = None,
    scene_metadata: Mapping[str, Any] | None = None,
    production_freeze: Mapping[str, Any] | None = None,
) -> CampaignResult:
    """Run one Arc 3 pilot or an explicitly admitted production map."""
    config = DEFAULT_CONFIG if config is None else config
    if mode not in ("pilot", "production") or workers <= 0:
        raise ValueError("mode must be pilot or admitted production, with positive workers")
    freeze: dict[str, Any] | None = None
    freeze_sha: str | None = None
    if mode == "production":
        freeze, freeze_sha = validate_production_freeze(config, scene_metadata, production_freeze)
    elif production_freeze is not None:
        raise ValueError("production freeze is only valid with production mode")
    if config.calibration_replicates < 2 or config.validation_replicates < 2:
        raise ValueError("Arc 3 profile assembly requires at least two datasets per phase")
    started = time.perf_counter()
    access_coordinates, access_ordered = _validate_design(access_design, landscape)
    balanced_coordinates, balanced_ordered = _validate_design(balanced_design, landscape)
    access_holdout = {
        coordinate for coordinate, site in access_coordinates.items() if site.split == "holdout"
    }
    balanced_holdout = {
        coordinate for coordinate, site in balanced_coordinates.items() if site.split == "holdout"
    }
    if access_holdout != balanced_holdout:
        raise ValueError("the two Arc 3 designs must use identical holdout coordinates")
    access_canonical = _canonical_design(access_design, access_ordered)
    balanced_canonical = _canonical_design(balanced_design, balanced_ordered)
    union = _union_design(access_canonical, access_coordinates, balanced_coordinates)
    union_site_ids = tuple(site.site_id for site in union.sites)
    if len(union_site_ids) != len(set(union_site_ids)):
        raise RuntimeError("union physical coordinates do not have unique canonical IDs")
    fixed_access = goal007.FixedInputs(landscape, access_canonical, {"design_valid": True})
    fixed_balanced = goal007.FixedInputs(landscape, balanced_canonical, {"design_valid": True})
    union_fixed = goal007.FixedInputs(landscape, union, {"design_valid": True})
    designs = (("access", fixed_access), ("balanced", fixed_balanced))
    manifest = arc2c.spawn_seed_manifest(config)
    if progress is not None:
        progress(f"run started mode={mode} source_commit={source_commit}")
    bank_started = time.perf_counter()
    if supplied_bank is None:
        bank = arc2b._generate_bank(union_fixed, manifest.bank_seeds)
    else:
        bank = _validate_supplied_bank(
            supplied_bank, manifest, union_site_ids, supplied_bank_manifest
        )
    bank = np.ascontiguousarray(np.asarray(bank, dtype=np.float64))
    bank_runtime = time.perf_counter() - bank_started
    integration_started = time.perf_counter()
    integration = _build_joint_integration(
        bank,
        union_site_ids,
        config.rhos,
        config.effects,
        background_hazard=BACKGROUND_HAZARD,
        workers=workers,
    )
    integration_runtime = time.perf_counter() - integration_started
    truths = _truths()
    calibration = _run_phase(
        union_fixed,
        designs,
        manifest.calibration,
        integration,
        truths,
        workers=workers,
        progress=progress,
    )
    calibration_runtime = time.perf_counter() - integration_started - integration_runtime
    validation_started = time.perf_counter()
    validation = _run_phase(
        union_fixed,
        designs,
        manifest.validation,
        integration,
        truths,
        workers=workers,
        progress=progress,
    )
    validation_runtime = time.perf_counter() - validation_started
    profiles = arc2c._assemble_profiles(config, calibration, validation, truths=truths)
    profiles.update(
        {
            "design_ids": np.asarray([truth.condition_id.rsplit("_", 1)[0] for truth in truths]),
            "truth_effects": np.asarray([truth.effect for truth in truths], dtype=np.float64),
            "truth_rhos": np.asarray([truth.rho for truth in truths], dtype=np.float64),
            "truth_roles": np.asarray([truth.role for truth in truths]),
        }
    )
    all_blocks = (*calibration, *validation)
    invariants = {
        "pair_structure": all(block.shared_random_numbers_valid for block in all_blocks),
        "no_training_holdout_leakage": (
            all(
                {site.cluster_id for site in design.sites if site.split == "training"}.isdisjoint(
                    {site.cluster_id for site in design.sites if site.split == "holdout"}
                )
                for _, fixed in designs
                for design in (fixed.design,)
            )
        ),
        "union_coordinates_unique": len(union_site_ids) == len(set(union_site_ids)),
        "pair_holdout_coordinates": access_holdout == balanced_holdout,
        "pair_overlap_training_observations": all(
            block.shared_random_numbers_valid for block in all_blocks
        ),
        "seed_disjointness": arc2c._seeds_disjoint(manifest),
        "shared_bank_shape": bank.shape == (config.bank_size, len(union_site_ids)),
        "bank_checksum_reconciled": integration.bank_checksum
        == hashlib.sha256(bank.tobytes(order="C")).hexdigest(),
        "histories_valid": all(block.histories_valid for block in all_blocks),
        "finite_profiles": all(
            np.isfinite(values).all() for values in profiles.values() if values.dtype.kind in "fiu"
        ),
        "nonnegative_profile_drops": all(
            (profiles[name] >= 0).all()
            for name in (
                "calibration_effect_lr",
                "calibration_spread_lr",
                "validation_effect_drops",
                "validation_spread_drops",
            )
        ),
        "conditional_null_rho_independent": all(
            row.conditional_null_rho_independent for block in all_blocks for row in block.profiles
        ),
    }
    recorded_scene_metadata = dict(scene_metadata or {})
    recorded_source_provenance = _source_provenance(source_commit)
    if freeze is not None and freeze_sha is not None:
        recorded_scene_metadata.update(
            {"production_freeze_sha256": freeze_sha, "production_freeze": freeze}
        )
        recorded_source_provenance.update(
            {"production_freeze_sha256": freeze_sha, "production_freeze": freeze}
        )
    result = CampaignResult(
        config=config,
        mode=mode,
        seed_manifest=manifest,
        truths=truths,
        profiles=profiles,
        invariants=invariants,
        workers=workers,
        runtime_seconds=time.perf_counter() - started,
        bank_runtime_seconds=bank_runtime,
        integration_runtime_seconds=integration_runtime,
        calibration_runtime_seconds=calibration_runtime,
        validation_runtime_seconds=validation_runtime,
        source_commit=source_commit,
        source_provenance=recorded_source_provenance,
        scene_metadata=recorded_scene_metadata,
        bank_checksum=integration.bank_checksum,
        site_ids=union_site_ids,
        base_arrivals=bank,
    )
    if progress is not None:
        progress(
            f"run complete outcome={result.outcome} elapsed_seconds={result.runtime_seconds:.3f}"
        )
    return result


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_campaign_bundle(result: CampaignResult, output_dir: Path) -> tuple[Path, ...]:
    """Write a replayable Arc 3 pilot bundle without object arrays."""
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_path = output_dir / "profiles.npz"
    np.savez_compressed(profile_path, **result.profiles)  # type: ignore[arg-type]
    bank_path = output_dir / BANK_FILENAME
    np.save(bank_path, result.base_arrivals, allow_pickle=False)
    completed = datetime.now(UTC).isoformat()
    _write_json(
        output_dir / "run_summary.json",
        {
            "workflow": "arc3-landscape-sampling-campaign",
            "schema_version": 1,
            "outcome": result.outcome,
            "mode": result.mode,
            "is_production": result.mode == "production",
            "config": asdict(result.config),
            "truths": [asdict(truth) for truth in result.truths],
            "designs": DESIGN_IDS,
            "lanes": LANES,
            "source_commit": result.source_commit,
            "source_provenance": result.source_provenance,
            "scene_metadata": result.scene_metadata,
            "bank_checksum": result.bank_checksum,
            "profile_bundle_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
            "invariants": {name: bool(value) for name, value in result.invariants.items()},
            "counts": {
                "conditions": len(result.truths),
                "designs": len(DESIGN_IDS),
                "effects_per_design": len(ARC3_EFFECT_TRUTHS),
                "lanes": len(LANES),
                "union_sites": int(result.base_arrivals.shape[1]),
                "sites_per_design": 160,
                "training_sites": 120,
                "holdout_sites": 40,
                "bank_draws": result.config.bank_size,
                "calibration_datasets_per_condition": result.config.calibration_replicates,
                "validation_datasets_per_condition": result.config.validation_replicates,
            },
            "workers": result.workers,
            "runtimes_seconds": {
                "total": result.runtime_seconds,
                "bank": result.bank_runtime_seconds,
                "integration": result.integration_runtime_seconds,
                "calibration": result.calibration_runtime_seconds,
                "validation": result.validation_runtime_seconds,
            },
            "completed_utc": completed,
            "hostname": platform.node(),
            "notes": {
                "inference": "Each fit uses only its design's 120 training sites.",
                "pairing": (
                    "One union history and one observation stream are mapped to both designs."
                ),
                "effect_truths": "rho=1 with effects 1, 3 and 5; slow Arc 2C truths are omitted.",
                "event_diagnostics_order": EVENT_DIAGNOSTICS,
                "event_diagnostics_role": (
                    "Training-site truth-assisted diagnostics; not inference inputs."
                ),
                "saved_bank": BANK_FILENAME,
            },
        },
    )
    _write_json(
        output_dir / "seed_provenance.json",
        {
            "master_seed": result.config.master_seed,
            "schedule": "Arc 2C seed schedule shared across the two designs",
            "bank_size": result.config.bank_size,
            "bank_checksum": result.bank_checksum,
            "bank_seeds": list(result.seed_manifest.bank_seeds),
            "calibration_seeds": [asdict(seed) for seed in result.seed_manifest.calibration],
            "validation_seeds": [asdict(seed) for seed in result.seed_manifest.validation],
            "phase_roots_disjoint": result.invariants["seed_disjointness"],
            "site_ids": list(result.site_ids),
            "pairing": (
                "The same union process, prey thresholds, predator observations and prey "
                "observations are reused."
            ),
            "source_commit": result.source_commit,
            "source_provenance": result.source_provenance,
            "scene_metadata": result.scene_metadata,
            "completed_utc": completed,
        },
    )
    return (*[output_dir / name for name in EXPECTED_FILES], bank_path)
