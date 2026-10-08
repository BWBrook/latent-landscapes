"""Bounded replay helpers for the adjusted-background Goal 052 pilot.

The pilot reuses six fixed Goal 051 production histories in four generator
cells.  This module owns only the archive-bound replay and identity controls;
integration-bank construction and adjusted likelihoods remain caller-owned.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Integral
from pathlib import Path
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import misspecification_generator as generator
from latent_landscapes import model_adequacy_campaign as adequacy
from latent_landscapes.goal007.benchmark import FixedInputs

FloatArray = NDArray[np.float64]

PRODUCTION_ROOT = generator.PRODUCTION_ROOT
PRODUCTION_PHASE: Literal["production"] = "production"
PRODUCTION_REPLICATES = 1_000
REPLAY_REPLICATE_INDICES = tuple(range(6))
REPLAY_CELL_IDS = ("B_h1", "B_h3", "B100-A_h1", "B100-A_h3")
ARCHIVE_SHA256 = "6d98c61d8ecee7b53335dec13de536bfbead700fee6d97a48644efafba11e381"
DEFAULT_ARCHIVE_PATH = Path("artifacts/goal051_execution/production/output/campaign_arrays.npz")

_ARCHIVE_KEYS = (
    "profiles",
    "holdout_joint",
    "prey_score",
    "predator_score",
    "mle_index",
    "opaque_ids",
    "cell_ids",
    "truths",
)
_FULL_CELL_IDS = tuple(spec.cell_id for spec in generator.CELL_SPECS)
_CELL_POSITIONS = {cell_id: index for index, cell_id in enumerate(_FULL_CELL_IDS)}


@dataclass(frozen=True, slots=True)
class ProductionArchive:
    """Loaded score arrays and their file identity."""

    arrays: Mapping[str, NDArray[Any]]
    sha256: str
    path: Path

    def __getitem__(self, key: str) -> NDArray[Any]:
        return self.arrays[key]


@dataclass(frozen=True, slots=True)
class ReplayVerification:
    """Compact identity receipt for one selected production replicate."""

    replicate_index: int
    cell_ids: tuple[str, ...]
    archive_sha256: str | None
    profile_max_abs_diff: float
    holdout_joint_max_abs_diff: float
    prey_score_max_abs_diff: float
    predator_score_max_abs_diff: float
    mle_index_equal: bool
    opaque_ids_equal: bool
    controls: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return all(self.controls.values())


def _validate_replicate_index(replicate_index: int) -> int:
    if isinstance(replicate_index, bool) or not isinstance(replicate_index, Integral):
        raise ValueError("replicate index must be an integer")
    index = int(replicate_index)
    if not 0 <= index < PRODUCTION_REPLICATES:
        raise ValueError("replicate index must lie in the Goal 051 production range")
    return index


def production_replicate_seed(replicate_index: int) -> generator.GeneratorSeed:
    """Return the exact Goal 051 seed at one production replicate index."""

    index = _validate_replicate_index(replicate_index)
    # Spawning the complete registered block makes the prefix contract
    # explicit: this is the same stream manifest used by Goal 051 production.
    return generator.spawn_generator_seeds(
        PRODUCTION_ROOT, PRODUCTION_PHASE, PRODUCTION_REPLICATES
    )[index]


def replay_production_replicate(
    fixed: FixedInputs,
    setup: generator.GeneratorSetup,
    replicate_index: int,
) -> tuple[generator.GeneratedCell, ...]:
    """Regenerate all 17 cells for one fixed Goal 051 production replicate."""

    seed = production_replicate_seed(replicate_index)
    generated = tuple(generator.generate_replicate(fixed, setup, seed))
    if tuple(cell.cell.cell_id for cell in generated) != _FULL_CELL_IDS:
        raise ValueError("Goal 051 replay changed the frozen generator cell order")
    return generated


def select_replay_cells(
    generated: Sequence[generator.GeneratedCell],
    cell_ids: Sequence[str] = REPLAY_CELL_IDS,
) -> tuple[generator.GeneratedCell, ...]:
    """Select the fixed four-cell panel while retaining generator order and IDs."""

    if tuple(cell.cell.cell_id for cell in generated) != _FULL_CELL_IDS:
        raise ValueError("generated cells must contain the complete frozen Goal 051 order")
    requested = tuple(cell_ids)
    if requested != REPLAY_CELL_IDS:
        raise ValueError("the adjusted-background replay panel is fixed and cannot be changed")
    by_id = {cell.cell.cell_id: cell for cell in generated}
    return tuple(by_id[cell_id] for cell_id in REPLAY_CELL_IDS)


def _selected_cells(
    generated: Sequence[generator.GeneratedCell],
    cell_ids: Sequence[str],
) -> tuple[generator.GeneratedCell, ...]:
    """Accept either a complete generator result or an already selected panel."""

    identifiers = tuple(cell.cell.cell_id for cell in generated)
    if identifiers == _FULL_CELL_IDS:
        return select_replay_cells(generated, cell_ids)
    if identifiers == tuple(cell_ids) == REPLAY_CELL_IDS:
        return tuple(generated)
    raise ValueError("generated cells must contain the complete or fixed selected Goal 051 order")


def replay_selected_cells(
    fixed: FixedInputs,
    setup: generator.GeneratorSetup,
    replicate_index: int,
) -> tuple[generator.GeneratedCell, ...]:
    """Regenerate one production replicate and return only the fixed panel."""

    return select_replay_cells(replay_production_replicate(fixed, setup, replicate_index))


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _validate_archive_arrays(
    arrays: Mapping[str, NDArray[Any]], *, full_schema: bool = True, minimum_replicate: int = 0
) -> None:
    missing = [key for key in _ARCHIVE_KEYS if key not in arrays]
    if missing:
        raise ValueError(f"production archive is missing required arrays: {missing}")
    expected_shapes = {
        "profiles": (17, PRODUCTION_REPLICATES, 181),
        "holdout_joint": (17, PRODUCTION_REPLICATES, 181),
        "prey_score": (17, PRODUCTION_REPLICATES),
        "predator_score": (17, PRODUCTION_REPLICATES),
        "mle_index": (17, PRODUCTION_REPLICATES),
        "opaque_ids": (17, PRODUCTION_REPLICATES),
        "cell_ids": (17,),
        "truths": (17,),
    }
    for key, shape in expected_shapes.items():
        actual = arrays[key].shape
        if full_schema or key in {"cell_ids", "truths"}:
            valid = actual == shape
        else:
            valid = (
                len(actual) == len(shape)
                and actual[0] == shape[0]
                and actual[1] > minimum_replicate
                and all(size > 0 for size in actual[2:])
            )
        if not valid:
            raise ValueError(f"production archive array has wrong shape: {key}")
    if tuple(str(value) for value in arrays["cell_ids"]) != _FULL_CELL_IDS:
        raise ValueError("production archive cell IDs differ from frozen generator order")
    if not all(
        np.isfinite(np.asarray(arrays[key], dtype=np.float64)).all()
        for key in ("profiles", "holdout_joint", "prey_score", "predator_score", "truths")
    ):
        raise ValueError("production archive contains non-finite numeric values")


def load_production_archive(
    path: Path = DEFAULT_ARCHIVE_PATH,
    *,
    expected_sha256: str = ARCHIVE_SHA256,
) -> ProductionArchive:
    """Load and authenticate the immutable Goal 051 production score archive."""

    path = Path(path)
    if not path.is_file():
        raise ValueError(f"missing Goal 051 production archive: {path}")
    digest = _sha256(path)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("Goal 051 production archive SHA256 does not match the frozen archive")
    with np.load(path, allow_pickle=False) as values:
        arrays = {key: np.asarray(values[key]).copy() for key in _ARCHIVE_KEYS if key in values}
    _validate_archive_arrays(arrays)
    return ProductionArchive(arrays, digest, path)


def _archive_arrays(
    archive: ProductionArchive | Mapping[str, NDArray[Any]] | Path,
) -> tuple[Mapping[str, NDArray[Any]], str | None]:
    if isinstance(archive, Path):
        loaded = load_production_archive(archive)
        return loaded.arrays, loaded.sha256
    if isinstance(archive, ProductionArchive):
        _validate_archive_arrays(archive.arrays)
        return archive.arrays, archive.sha256
    return archive, None


def _max_abs_difference(observed: NDArray[Any], expected: NDArray[Any]) -> float:
    if observed.shape != expected.shape:
        return float("inf")
    return float(np.max(np.abs(np.asarray(observed) - np.asarray(expected))))


def verify_original_replay(
    generated: Sequence[generator.GeneratedCell],
    integration: Any,
    replicate_index: int,
    *,
    archive: ProductionArchive | Mapping[str, NDArray[Any]] | Path = DEFAULT_ARCHIVE_PATH,
    cell_ids: Sequence[str] = REPLAY_CELL_IDS,
) -> ReplayVerification:
    """Score selected analyst datasets and require exact archive identity.

    ``integration`` is supplied by the caller.  The scorer receives only each
    analyst dataset, so evaluator-only latent truths attached to ``GeneratedCell``
    cannot enter this verification path.
    """

    index = _validate_replicate_index(replicate_index)
    selected = _selected_cells(generated, cell_ids)
    arrays, archive_sha256 = _archive_arrays(archive)
    if archive_sha256 is None:
        _validate_archive_arrays(arrays, full_schema=False, minimum_replicate=index)
    positions = tuple(_CELL_POSITIONS[cell_id] for cell_id in REPLAY_CELL_IDS)
    scored: list[tuple[float, float, int, FloatArray, FloatArray]] = []
    opaque_ids: list[str] = []
    for cell in selected:
        scored.append(adequacy._score_dataset(cell.dataset, integration))
        opaque_ids.append(cell.dataset.opaque_id)
    profiles = np.stack([row[3] for row in scored])
    holdout_joint = np.stack([row[4] for row in scored])
    prey_score = np.asarray([row[0] for row in scored], dtype=np.float64)
    predator_score = np.asarray([row[1] for row in scored], dtype=np.float64)
    mle_index = np.asarray([row[2] for row in scored], dtype=np.int64)
    observed_ids = np.asarray(opaque_ids, dtype="<U64")

    expected = {
        "profiles": np.asarray(arrays["profiles"])[list(positions), index],
        "holdout_joint": np.asarray(arrays["holdout_joint"])[list(positions), index],
        "prey_score": np.asarray(arrays["prey_score"])[list(positions), index],
        "predator_score": np.asarray(arrays["predator_score"])[list(positions), index],
        "mle_index": np.asarray(arrays["mle_index"])[list(positions), index],
        "opaque_ids": np.asarray(arrays["opaque_ids"])[list(positions), index],
    }
    controls = {
        "profiles_exact": bool(np.array_equal(profiles, expected["profiles"])),
        "holdout_joint_exact": bool(np.array_equal(holdout_joint, expected["holdout_joint"])),
        "prey_score_exact": bool(np.array_equal(prey_score, expected["prey_score"])),
        "predator_score_exact": bool(np.array_equal(predator_score, expected["predator_score"])),
        "mle_index_exact": bool(np.array_equal(mle_index, expected["mle_index"])),
        "opaque_ids_exact": bool(np.array_equal(observed_ids, expected["opaque_ids"])),
    }
    receipt = ReplayVerification(
        index,
        tuple(REPLAY_CELL_IDS),
        archive_sha256,
        _max_abs_difference(profiles, expected["profiles"]),
        _max_abs_difference(holdout_joint, expected["holdout_joint"]),
        _max_abs_difference(prey_score, expected["prey_score"]),
        _max_abs_difference(predator_score, expected["predator_score"]),
        controls["mle_index_exact"],
        controls["opaque_ids_exact"],
        controls,
    )
    if not receipt.passed:
        raise ValueError(f"Goal 051 replay identity failed: {dict(receipt.controls)}")
    return receipt


__all__ = [
    "ARCHIVE_SHA256",
    "DEFAULT_ARCHIVE_PATH",
    "PRODUCTION_REPLICATES",
    "PRODUCTION_ROOT",
    "REPLAY_CELL_IDS",
    "REPLAY_REPLICATE_INDICES",
    "ProductionArchive",
    "ReplayVerification",
    "load_production_archive",
    "production_replicate_seed",
    "replay_production_replicate",
    "replay_selected_cells",
    "select_replay_cells",
    "verify_original_replay",
]
