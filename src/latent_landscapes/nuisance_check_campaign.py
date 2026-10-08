"""Evaluation-only archive checks for Goal 055.

This module binds the two frozen archives to the unchanged likelihood scorer.  It
does not generate new histories: Goal 054 rows are selected from its committed
observation panel and Goal 051 rows are deterministically reconstructed from
the registered production seeds before their opaque identifiers are checked.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import time
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import adjusted_background_likelihood as adjusted
from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import arc2c_likelihood as joint
from latent_landscapes import known_nuisance_calibration as legacy
from latent_landscapes import misspecification_generator as goal051
from latent_landscapes import model_adequacy_campaign as adequacy
from latent_landscapes.goal004.observations import SURVEY_TIMES
from latent_landscapes.goal011 import benchmark

FloatArray = NDArray[np.float64]
AnyArray = NDArray[Any]

EFFECTS = np.linspace(1.0, 10.0, 181, dtype=np.float64)
BETAS = np.linspace(-2.0, 2.0, 81, dtype=np.float64)
BETA_ZERO_INDEX = 40
MEANS = (0.0016, 0.0025)
OLD_GENERATOR_MEAN = 0.0020000000000000005
OLD_SUPPLIED_MEAN = 0.002
GOAL054_CELLS = ("E0_h1", "E0_h3", "E06_h1", "E06_h3")
GOAL051_CELLS = ("B_h1", "B_h3", "D20_h1", "D20_h3")
CELL_IDS = (
    "M080_E0_h1",
    "M080_E0_h3",
    "M080_E06_h1",
    "M080_E06_h3",
    "M125_E0_h1",
    "M125_E0_h3",
    "M125_E06_h1",
    "M125_E06_h3",
    "S051_B_h1",
    "S051_B_h3",
    "S051_D20_h1",
    "S051_D20_h3",
)
SUPPLIED_MEANS = np.asarray(
    (0.0016,) * 4 + (0.0025,) * 4 + (OLD_SUPPLIED_MEAN,) * 4, dtype=np.float64
)
BATCH_SIZE = 64
REPLAY_TOLERANCE = 1e-10
GOAL054_OBSERVATIONS_SHA256 = "e88de8fbac2f9844a3939e6541f3f74a4d9be4a3944bbf7e35548f89e9b86e93"
GOAL054_STATS_SHA256 = "33c94ad6d7bb58701c68b611c70400c0228787e1782026c7df7d9b747aa40900"
GOAL051_ARCHIVE_SHA256 = "6d98c61d8ecee7b53335dec13de536bfbead700fee6d97a48644efafba11e381"
GOAL051_PRODUCTION_ROOT = 2026092301
GOAL051_INDICES = (0, 1, 6, 7)
GOAL053_CORE = "b7a87caa216ea9c229110e225081dfe007cc56d1a0eea100d5756136da6d5b63"
GOAL054_RUN_CONTRACT_SHA256 = "6a7d3ea33b94f0fd5db9ad28938d3a1d682a163236a67cef11ca55d9864606f9"


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _goal053_fingerprint(value: Any) -> str:
    """Reproduce Goal053's default JSON separators for frozen receipts."""

    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _array_checksum(value: AnyArray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).view(np.uint8)).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)
    _fsync_directory(path.parent)


def commit_npz(path: Path, values: Mapping[str, AnyArray], record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    started = time.perf_counter()
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **cast(Any, values))
        handle.flush()
        os.fsync(handle.fileno())
    record["sha256"] = sha256(temporary)
    temporary.replace(path)
    _fsync_directory(path.parent)
    record["serialization_seconds"] = time.perf_counter() - started
    write_json(path.with_suffix(".json"), record)


def read_committed(path: Path, identity: str) -> tuple[dict[str, AnyArray], dict[str, Any]] | None:
    receipt = path.with_suffix(".json")
    if path.exists() != receipt.exists():
        raise ValueError(f"partial committed output must be diagnosed: {path}")
    if not path.exists():
        return None
    try:
        record = json.loads(receipt.read_text(encoding="utf-8"))
        if record.get("identity") != identity or record.get("sha256") != sha256(path):
            raise ValueError(f"cached identity or checksum changed: {path}")
        with np.load(path, allow_pickle=False) as loaded:
            values = {name: np.asarray(loaded[name]) for name in loaded.files}
    except (OSError, ValueError, EOFError, KeyError, json.JSONDecodeError) as error:
        if isinstance(error, ValueError) and str(error).startswith("cached identity"):
            raise
        raise ValueError(f"corrupt committed output: {path}") from error
    return values, record


def source_hashes(repository: Path) -> dict[str, str]:
    """Hash complete Python source plus this runner and its CLI binding."""

    paths = [
        *sorted((repository / "src").rglob("*.py")),
        repository / "scripts/run_nuisance_checks.py",
        repository / "docs/goals/055-arc4-synthesis/registration-2026-10-01.md",
    ]
    return {str(path.relative_to(repository)): sha256(path) for path in paths if path.is_file()}


def _validate_grid(values: Mapping[str, AnyArray]) -> None:
    if not np.array_equal(np.asarray(values["effects"], dtype=np.float64), EFFECTS):
        raise ValueError("effect grid changed")
    if not np.array_equal(np.asarray(values["betas"], dtype=np.float64), BETAS):
        raise ValueError("beta grid changed")


def _observation_values(values: Mapping[str, AnyArray]) -> dict[str, AnyArray]:
    required = {"predator_counts", "prey_counts", "site_ids", "site_cluster_ids", "site_splits"}
    if not required.issubset(values):
        raise ValueError("observation panel is incomplete")
    predator = np.asarray(values["predator_counts"])
    prey = np.asarray(values["prey_counts"])
    if predator.shape != prey.shape or predator.ndim != 3 or predator.shape[2:] != (6,):
        raise ValueError("observation count dimensions changed")
    if not np.isin(predator, (0, 1, 2)).all() or not np.isin(prey, (0, 1, 2)).all():
        raise ValueError("observation counts are outside the registered range")
    return {
        "predator_counts": predator.copy(),
        "prey_counts": prey.copy(),
        "site_ids": np.asarray(values["site_ids"]).copy(),
        "site_cluster_ids": np.asarray(values["site_cluster_ids"]).copy(),
        "site_splits": np.asarray(values["site_splits"]).copy(),
    }


def select_goal054_archive(
    path: Path,
    *,
    expected_sha256: str | None = GOAL054_OBSERVATIONS_SHA256,
    cells: Sequence[str] = GOAL054_CELLS,
    blocks: int | None = None,
) -> dict[str, Any]:
    """Select the four registered Goal054 cells, retaining opaque IDs."""

    if expected_sha256 and sha256(path) != expected_sha256:
        raise ValueError("Goal054 observation archive SHA256 does not match the frozen input")
    with np.load(path, allow_pickle=False) as loaded:
        values = {name: np.asarray(loaded[name]) for name in loaded.files}
    _validate_grid(values)
    required = {"cell_ids", "replicate_indices", "opaque_ids", "truth_h", "truth_beta"}
    if not required.issubset(values):
        raise ValueError("Goal054 observation archive lacks identity arrays")
    ids = np.asarray(values["cell_ids"]).astype(str)
    requested = tuple(cells)
    if requested != GOAL054_CELLS:
        raise ValueError("Goal054 archive selection is fixed")
    n = 1000 if blocks is None else int(blocks)
    if n <= 0 or n > 1000:
        raise ValueError("Goal054 block count must lie in 1..1000")
    positions: list[int] = []
    for replicate in range(n):
        for cell in requested:
            matches = np.flatnonzero((ids == cell) & (values["replicate_indices"] == replicate))
            if len(matches) != 1:
                raise ValueError("Goal054 archive has missing or duplicate selected rows")
            positions.append(int(matches[0]))
    selected = _observation_values(values)
    for key in ("predator_counts", "prey_counts"):
        selected[key] = selected[key][positions]
    selected.update(
        {
            "archive_ids": np.asarray(values["opaque_ids"])[positions].astype(str),
            "cell_ids": ids[positions],
            "truth_h": np.asarray(values["truth_h"], dtype=np.float64)[positions],
            "truth_beta": np.asarray(values["truth_beta"], dtype=np.float64)[positions],
            "replicate_indices": np.asarray(values["replicate_indices"], dtype=np.int64)[positions],
            "effects": EFFECTS.copy(),
            "betas": BETAS.copy(),
        }
    )
    if len(np.unique(selected["archive_ids"])) != len(selected["archive_ids"]):
        raise ValueError("Goal054 archive contains duplicate opaque IDs")
    return selected


def load_goal054_controls(
    path: Path, *, expected_sha256: str | None = GOAL054_STATS_SHA256
) -> dict[str, AnyArray]:
    if expected_sha256 and sha256(path) != expected_sha256:
        raise ValueError("Goal054 statistics archive SHA256 does not match the frozen input")
    with np.load(path, allow_pickle=False) as loaded:
        values = {name: np.asarray(loaded[name]) for name in loaded.files}
    _validate_grid(values)
    required = {
        "evaluation_t_adj",
        "evaluation_t_constant",
        "evaluation_d_beta",
        "evaluation_h_hat_adj",
        "evaluation_beta_hat_adj",
        "evaluation_h_hat_constant",
        "evaluation_beta_hat_null",
        "evaluation_delta_holdout_adj_constant",
        "evaluation_delta_holdout_adj_neutral",
        "evaluation_delta_holdout_constant_neutral",
        "cell_ids",
        "truth_h",
    }
    if not required.issubset(values):
        raise ValueError("Goal054 controls are incomplete")
    expected_shapes = {
        "evaluation_t_adj": (1000, 8),
        "evaluation_t_constant": (1000, 8),
        "evaluation_d_beta": (1000, 8, 81),
        "evaluation_h_hat_adj": (1000, 8),
        "evaluation_beta_hat_adj": (1000, 8),
        "evaluation_h_hat_constant": (1000, 8),
        "evaluation_beta_hat_null": (1000, 8),
        "evaluation_delta_holdout_adj_constant": (1000, 8),
        "evaluation_delta_holdout_adj_neutral": (1000, 8),
        "evaluation_delta_holdout_constant_neutral": (1000, 8),
    }
    if any(values[name].shape != shape for name, shape in expected_shapes.items()):
        raise ValueError("Goal054 control dimensions changed")
    if tuple(values["cell_ids"].astype(str)) != (
        "E0_h1",
        "E0_h3",
        "E06_h1",
        "E06_h3",
        "B100-A_h1",
        "B100-A_h3",
        "N100-A_h1",
        "N100-A_h3",
    ):
        raise ValueError("Goal054 control cell order changed")
    return values


def load_goal051_archive(
    path: Path, *, expected_sha256: str | None = GOAL051_ARCHIVE_SHA256
) -> dict[str, AnyArray]:
    if expected_sha256 and sha256(path) != expected_sha256:
        raise ValueError("Goal051 archive SHA256 does not match the frozen input")
    with np.load(path, allow_pickle=False) as loaded:
        values = {name: np.asarray(loaded[name]) for name in loaded.files}
    required = {
        "profiles",
        "holdout_joint",
        "prey_score",
        "predator_score",
        "mle_index",
        "opaque_ids",
        "cell_ids",
        "truths",
    }
    if not required.issubset(values):
        raise ValueError("Goal051 archive is incomplete")
    if tuple(values["cell_ids"].astype(str)) != tuple(spec.cell_id for spec in goal051.CELL_SPECS):
        raise ValueError("Goal051 cell order changed")
    if values["profiles"].shape != (17, 1000, 181) or values["holdout_joint"].shape != (
        17,
        1000,
        181,
    ):
        raise ValueError("Goal051 archive dimensions changed")
    if values["opaque_ids"].shape != (17, 1000):
        raise ValueError("Goal051 opaque ID dimensions changed")
    if not np.isfinite(values["profiles"]).all() or not np.isfinite(values["holdout_joint"]).all():
        raise ValueError("Goal051 archive contains non-finite scores")
    return values


def histories_from_arrays(
    values: Mapping[str, AnyArray], *, start: int = 0, stop: int | None = None
) -> tuple[tuple[Any, ...], ...]:
    """Construct analyst histories from observation-only arrays."""

    predator = np.asarray(values["predator_counts"])
    prey = np.asarray(values["prey_counts"])
    site_ids = tuple(str(v) for v in values["site_ids"])
    clusters = tuple(str(v) for v in values["site_cluster_ids"])
    splits = tuple(str(v) for v in values["site_splits"])
    if (
        predator.shape != prey.shape
        or predator.ndim != 3
        or predator.shape[1:] != (len(site_ids), 6)
    ):
        raise ValueError("observation arrays have incompatible dimensions")
    if len(clusters) != len(site_ids) or len(splits) != len(site_ids):
        raise ValueError("site metadata dimensions changed")
    begin = int(start)
    end = predator.shape[0] if stop is None else min(int(stop), predator.shape[0])
    if begin < 0 or begin > end:
        raise ValueError("history bounds are invalid")
    return tuple(
        tuple(
            legacy.AnalystHistory(
                site_ids[site],
                clusters[site],
                splits[site],
                tuple(int(v) for v in predator[row, site]),
                tuple(int(v) for v in prey[row, site]),
                0.65,
            )
            for site in range(len(site_ids))
        )
        for row in range(begin, end)
    )


def _score_panel(
    panel: Path | Mapping[str, AnyArray],
    integration: joint.BridgeIntegration,
    batch_size: int = BATCH_SIZE,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Score observation-only panels; evaluator truth arrays are never read."""

    if isinstance(panel, Path):
        with np.load(panel, allow_pickle=False) as loaded:
            values = {name: np.asarray(loaded[name]) for name in loaded.files}
    else:
        values = dict(panel)
    values = _observation_values(values)
    if batch_size <= 0:
        raise ValueError("batch size must be positive")
    if tuple(str(v) for v in values["site_ids"]) != integration.site_ids:
        raise ValueError("observation and integration site order changed")
    count = int(values["predator_counts"].shape[0])
    training = np.empty((count, len(EFFECTS)), dtype=np.float64)
    heldout = np.empty_like(training)
    predator = np.empty(count, dtype=np.float64)
    for start in range(0, count, batch_size):
        histories = histories_from_arrays(values, start=start, stop=min(count, start + batch_size))
        for offset, history in enumerate(histories, start):
            train, held, pred = joint.evaluate_dataset(cast(Any, history), integration)
            training[offset] = train[0]
            heldout[offset] = held[0]
            predator[offset] = pred[0]
    if (
        not np.isfinite(training).all()
        or not np.isfinite(heldout).all()
        or not np.isfinite(predator).all()
    ):
        raise RuntimeError("likelihood scorer produced non-finite scores")
    return training, heldout, predator


def _cell_blocks(
    values: Mapping[str, AnyArray], cells: Sequence[str]
) -> dict[str, dict[str, AnyArray]]:
    identifiers = np.asarray(values["cell_ids"]).astype(str)
    result: dict[str, dict[str, AnyArray]] = {}
    for cell in cells:
        positions = np.flatnonzero(identifiers == cell)
        if len(positions) == 0 or len(positions) != len(
            np.unique(values["replicate_indices"][positions])
        ):
            raise ValueError(f"archive selection is incomplete for {cell}")
        order = positions[np.argsort(values["replicate_indices"][positions])]
        row_keys = (
            "predator_counts",
            "prey_counts",
            "archive_ids",
            "replicate_indices",
            "truth_h",
            "truth_beta",
        )
        site_keys = ("site_ids", "site_cluster_ids", "site_splits")
        result[cell] = {
            **{key: np.asarray(values[key])[order] for key in row_keys if key in values},
            **{key: np.asarray(values[key]).copy() for key in site_keys if key in values},
        }
    return result


def panel_archive_ids(
    goal054_panel: Mapping[str, AnyArray], goal051_panel: Mapping[str, AnyArray]
) -> NDArray[np.str_]:
    g054 = _cell_blocks(goal054_panel, GOAL054_CELLS)
    g051 = _cell_blocks(goal051_panel, GOAL051_CELLS)
    columns = [g054[cell]["archive_ids"] for cell in GOAL054_CELLS] * 2 + [
        g051[cell]["archive_ids"] for cell in GOAL051_CELLS
    ]
    return np.column_stack(columns).astype(str)


def reconstruct_goal051_panel(
    archive: Mapping[str, AnyArray],
    fixed: Any,
    setup: Any,
    *,
    blocks: int = 1000,
    replay_integration: Any | None = None,
) -> dict[str, Any]:
    """Reconstruct selected Goal051 observations and authenticate opaque IDs."""

    if blocks <= 0 or blocks > 1000:
        raise ValueError("Goal051 block count must lie in 1..1000")
    seeds = goal051.spawn_generator_seeds(GOAL051_PRODUCTION_ROOT, "production", 1000)
    selected: list[Any] = []
    replay_results: list[dict[str, Any]] = []
    for index in range(blocks):
        generated = goal051.generate_replicate(fixed, setup, seeds[index])
        selected_generated = tuple(generated[cell] for cell in GOAL051_INDICES)
        if replay_integration is not None:
            replay_results.append(
                verify_goal051_replay(selected_generated, archive, replay_integration, index)
            )
        selected.extend(selected_generated)
    n = blocks * len(GOAL051_CELLS)
    sites = len(setup.site_ids)
    predator = np.empty((n, sites, 6), dtype=np.uint8)
    prey = np.empty_like(predator)
    ids: list[str] = []
    for row, cell in enumerate(selected):
        ids.append(cell.dataset.opaque_id)
        for site, history in enumerate(cell.dataset.histories):
            predator[row, site] = history.predator_detection_counts
            prey[row, site] = history.prey_detection_counts
    expected = np.asarray(archive["opaque_ids"])[list(GOAL051_INDICES), :blocks].T.reshape(-1)
    if not np.array_equal(np.asarray(ids), expected.astype(str)):
        raise ValueError("Goal051 replay opaque IDs do not match the frozen archive")
    result: dict[str, Any] = {
        "predator_counts": predator,
        "prey_counts": prey,
        "site_ids": np.asarray(setup.site_ids),
        "site_cluster_ids": np.asarray(setup.site_cluster_ids),
        "site_splits": np.asarray(setup.site_splits),
        "archive_ids": np.asarray(ids),
        "cell_ids": np.asarray([cell.cell.cell_id for cell in selected]),
        "truth_h": np.asarray([cell.cell.truth_h for cell in selected], dtype=np.float64),
        "truth_beta": np.full(n, np.nan, dtype=np.float64),
        "replicate_indices": np.repeat(np.arange(blocks), len(GOAL051_CELLS)),
        "effects": EFFECTS.copy(),
        "betas": BETAS.copy(),
    }
    if replay_integration is not None:
        result["replay_diagnostics"] = _aggregate_replay_results(replay_results)
    return result


def _aggregate_replay_results(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "histories": 0,
            "mle_matches": 0,
            "opaque_id_matches": 0,
            "max_profile_abs_error": 0.0,
            "max_holdout_abs_error": 0.0,
            "max_prey_abs_error": 0.0,
            "max_predator_abs_error": 0.0,
            "max_h1_factorization_abs_error": 0.0,
        }
    return {
        "histories": int(sum(int(row["histories"]) for row in results)),
        "mle_matches": int(sum(int(row["mle_matches"]) for row in results)),
        "opaque_id_matches": int(sum(int(row["opaque_id_matches"]) for row in results)),
        "max_profile_abs_error": float(max(row["max_profile_abs_error"] for row in results)),
        "max_holdout_abs_error": float(max(row["max_holdout_abs_error"] for row in results)),
        "max_prey_abs_error": float(max(row["max_prey_abs_error"] for row in results)),
        "max_predator_abs_error": float(max(row["max_predator_abs_error"] for row in results)),
        "max_h1_factorization_abs_error": float(
            max(row["max_h1_factorization_abs_error"] for row in results)
        ),
    }


def verify_goal051_replay(
    generated: Sequence[Any],
    archive: Mapping[str, AnyArray],
    integration: Any,
    replicate_index: int,
) -> dict[str, Any]:
    """Verify selected full profiles through the frozen adequacy scorer."""

    if not 0 <= replicate_index < 1000 or len(generated) != 4:
        raise ValueError("Goal051 replay selection is invalid")
    profile_error = holdout_error = prey_error = predator_error = h1_error = 0.0
    mle_matches = opaque_matches = 0
    for ordinal, cell_index in enumerate(GOAL051_INDICES):
        prey, predator, mle, profile, holdout = adequacy._score_dataset(
            generated[ordinal].dataset, integration
        )
        expected_profile = np.asarray(archive["profiles"])[cell_index, replicate_index]
        expected_holdout = np.asarray(archive["holdout_joint"])[cell_index, replicate_index]
        if not np.array_equal(profile, expected_profile):
            raise ValueError("Goal051 full training profile replay failed")
        profile_error = max(profile_error, float(np.max(np.abs(profile - expected_profile))))
        if not np.array_equal(holdout, expected_holdout):
            raise ValueError("Goal051 full held-out replay failed")
        holdout_error = max(holdout_error, float(np.max(np.abs(holdout - expected_holdout))))
        histories = cast(Any, generated[ordinal].dataset.histories)
        ordered, indices = joint._prepare_histories(histories, integration)
        predator_categories = arc2b._predator_category_probabilities(
            ordered, legacy.DETECTION_PROBABILITY
        )
        marginal = np.einsum("sc,sc->s", integration.category_mass[0, indices], predator_categories)
        events, alive = arc2b._prey_emission_coefficients(ordered)
        survival = np.exp(-legacy.BACKGROUND_HAZARD * np.asarray((0.0, *SURVEY_TIMES)))
        prey_marginal = events @ (survival[:-1] - survival[1:]) + alive * survival[-1]
        holdout_mask = np.asarray([row.split == "holdout" for row in ordered])
        independent_h1_joint = float((np.log(marginal) + np.log(prey_marginal))[holdout_mask].sum())
        h1_error = max(h1_error, abs(float(holdout[0]) - independent_h1_joint))
        for observed, key in ((prey, "prey_score"), (predator, "predator_score")):
            difference = abs(float(observed) - float(archive[key][cell_index, replicate_index]))
            if key == "prey_score":
                prey_error = max(prey_error, difference)
            else:
                predator_error = max(predator_error, difference)
            if float(observed) != float(archive[key][cell_index, replicate_index]):
                raise ValueError("Goal051 scalar replay failed")
        if mle != int(archive["mle_index"][cell_index, replicate_index]):
            raise ValueError("Goal051 MLE replay failed")
        mle_matches += 1
        if generated[ordinal].dataset.opaque_id != str(
            archive["opaque_ids"][cell_index, replicate_index]
        ):
            raise ValueError("Goal051 opaque ID replay failed")
        opaque_matches += 1
    if h1_error > REPLAY_TOLERANCE:
        raise ValueError("Goal051 h1 factorization replay failed")
    return {
        "histories": len(generated),
        "mle_matches": mle_matches,
        "opaque_id_matches": opaque_matches,
        "max_profile_abs_error": profile_error,
        "max_holdout_abs_error": holdout_error,
        "max_prey_abs_error": prey_error,
        "max_predator_abs_error": predator_error,
        "max_h1_factorization_abs_error": h1_error,
    }


def verify_goal051_archive_replay(
    archive: Mapping[str, AnyArray],
    fixed: Any,
    setup: Any,
    integration: Any,
    *,
    blocks: int = 1000,
) -> dict[str, Any]:
    """Replay every selected history through the original constant scorer."""

    if blocks <= 0 or blocks > 1000:
        raise ValueError("Goal051 replay block count must lie in 1..1000")
    seeds = goal051.spawn_generator_seeds(GOAL051_PRODUCTION_ROOT, "production", 1000)
    results: list[dict[str, Any]] = []
    for replicate in range(blocks):
        generated = goal051.generate_replicate(fixed, setup, seeds[replicate])
        selected = tuple(generated[index] for index in GOAL051_INDICES)
        results.append(verify_goal051_replay(selected, archive, integration, replicate))
    return _aggregate_replay_results(results)


def integration_identity(
    *,
    core: str,
    beta: float,
    mean_hazard: float,
    bank_checksum: str,
    map_A: AnyArray,
    site_A: AnyArray,
) -> str:
    if not math.isfinite(mean_hazard) or mean_hazard <= 0.0:
        raise ValueError("mean hazard must be finite and positive")
    return fingerprint(
        {
            "core": core,
            "beta": float(beta),
            "mean_hazard": float(mean_hazard),
            "bank_checksum": bank_checksum,
            "map_A_checksum": _array_checksum(np.asarray(map_A, dtype=np.float64)),
            "site_A_checksum": _array_checksum(np.asarray(site_A, dtype=np.float64)),
            "effects": EFFECTS.tolist(),
            "betas": BETAS.tolist(),
            "alpha": 1.0,
        }
    )


def build_new_integration(
    prepared: Any, *, beta: float, map_A: AnyArray, site_A: AnyArray, mean_hazard: float
) -> joint.BridgeIntegration:
    """Build one explicit-mean integration; callers must identify its cache."""

    hazards = adjusted.normalized_hazards(beta, map_A, site_A, mean_hazard=mean_hazard)
    return adjusted.build_integration(prepared, tuple(float(value) for value in EFFECTS), hazards)


def verify_goal054_correct_level_replay(
    panel: Mapping[str, AnyArray],
    controls: Mapping[str, AnyArray],
    *,
    old_root: Path,
    site_ids: tuple[str, ...],
    bank_checksum: str,
    old_hashes: Mapping[int, Mapping[str, str]],
    blocks: int,
    batch_size: int = BATCH_SIZE,
) -> dict[str, Any]:
    """Replay the saved Goal054 first four cells at the registered mean.

    The saved controls contain eight cells.  The four selected cells are tiled
    across the three lanes solely to exercise the production reducer's exact
    twelve-cell layout; no histories are generated by this check.
    """

    if blocks <= 0 or blocks > 1000:
        raise ValueError("Goal054 control block count is invalid")
    expected = {
        name: np.asarray(controls[name])[:blocks, :4]
        for name in (
            "evaluation_t_adj",
            "evaluation_t_constant",
            "evaluation_h_hat_adj",
            "evaluation_beta_hat_adj",
            "evaluation_h_hat_constant",
            "evaluation_beta_hat_null",
            "evaluation_delta_holdout_adj_constant",
            "evaluation_delta_holdout_adj_neutral",
            "evaluation_delta_holdout_constant_neutral",
        )
    }
    expected_d = np.asarray(controls["evaluation_d_beta"])[:blocks, :4]
    rows: list[tuple[int, Mapping[str, AnyArray]]] = []
    for index, _beta in enumerate(BETAS):
        integration = _load_old_integration(
            old_root,
            index,
            site_ids,
            bank_checksum,
            expected_sha256=old_hashes[index]["npz"],
            expected_receipt_sha256=old_hashes[index]["json"],
        )
        training, heldout, predator = _score_panel(panel, integration, batch_size)
        train4 = training.reshape(blocks, 4, len(EFFECTS))
        held4 = heldout.reshape(blocks, 4, len(EFFECTS))
        pred4 = predator.reshape(blocks, 4)
        rows.append(
            (
                index,
                {
                    "latent_training": np.tile(train4, (1, 3, 1)),
                    "latent_holdout_joint": np.tile(held4, (1, 3, 1)),
                    "latent_holdout_predator": np.tile(pred4, (1, 3)),
                },
            )
        )
    replay = reduce_rows(rows, blocks=blocks)
    errors = {
        name: float(np.max(np.abs(np.asarray(replay[name])[:, :4] - expected[name])))
        for name in expected
    }
    errors["evaluation_d_beta"] = float(
        np.max(np.abs(np.asarray(replay["evaluation_d_beta"])[:, :4] - expected_d))
    )
    maximum = max(errors.values())
    if maximum > REPLAY_TOLERANCE:
        raise ValueError(f"Goal054 correct-level replay failed: max error {maximum:.3g}")
    return {
        "blocks": blocks,
        "cells": list(GOAL054_CELLS),
        "rows": len(BETAS),
        "max_abs_error": maximum,
        "errors": errors,
        "mean_hazard": OLD_SUPPLIED_MEAN,
    }


def load_or_build_new_integration(
    cache_root: Path,
    prepared: Any,
    *,
    index: int,
    beta: float,
    mean_hazard: float,
    map_A: AnyArray,
    site_A: AnyArray,
    core: str,
    allow_build: bool = True,
) -> tuple[joint.BridgeIntegration, float, dict[str, Any]]:
    """Reuse or commit one authenticated explicit-mean integration."""

    identity = integration_identity(
        core=core,
        beta=beta,
        mean_hazard=mean_hazard,
        bank_checksum=prepared.bank_checksum,
        map_A=map_A,
        site_A=site_A,
    )
    path = cache_root / "integrations" / f"mu-{mean_hazard:.4f}" / f"{index:03d}.npz"
    cached = read_committed(path, identity)
    if cached is not None:
        values, record = cached
        category = np.asarray(values.get("category_mass"))
        moments = np.asarray(values.get("survival_moments"))
        if category.shape != (1, len(prepared.site_ids), 7):
            raise ValueError("new integration category dimensions changed")
        if moments.shape != (181, len(prepared.site_ids), 7, 7):
            raise ValueError("new integration moment dimensions changed")
        return (
            joint.BridgeIntegration(
                (1.0,),
                tuple(float(value) for value in EFFECTS),
                prepared.site_ids,
                category,
                (moments,),
                prepared.bank_checksum,
            ),
            0.0,
            record,
        )
    if not allow_build:
        raise ValueError(f"required authenticated integration cache is missing: {path}")
    started = time.perf_counter()
    integration = build_new_integration(
        prepared,
        beta=beta,
        map_A=map_A,
        site_A=site_A,
        mean_hazard=mean_hazard,
    )
    values = {
        "category_mass": integration.category_mass,
        "survival_moments": integration.survival_moments[0],
    }
    record = {
        "identity": identity,
        "index": index,
        "beta": float(beta),
        "mean_hazard": float(mean_hazard),
        "bank_checksum": prepared.bank_checksum,
    }
    commit_npz(path, values, record)
    return integration, time.perf_counter() - started, record


def _load_old_integration(
    old_root: Path,
    index: int,
    site_ids: tuple[str, ...],
    bank_checksum: str,
    *,
    expected_sha256: str | None = None,
    expected_receipt_sha256: str | None = None,
) -> joint.BridgeIntegration:
    """Load an authenticated existing-mean Goal053 integration cache."""

    path = old_root / "integrations" / f"{index:03d}.npz"
    receipt = path.with_suffix(".json")
    if not path.exists() or not receipt.exists():
        raise ValueError(f"Goal053 integration cache is missing or partial: {path}")
    record = json.loads(receipt.read_text(encoding="utf-8"))
    expected_identity = _goal053_fingerprint(
        {"core": GOAL053_CORE, "beta_index": index, "beta": float(BETAS[index])}
    )
    digest = sha256(path)
    receipt_digest = sha256(receipt)
    if (
        record.get("identity") != expected_identity
        or record.get("sha256") != digest
        or (expected_sha256 is not None and digest != expected_sha256)
        or (expected_receipt_sha256 is not None and receipt_digest != expected_receipt_sha256)
    ):
        raise ValueError(f"Goal053 integration checksum changed: {path}")
    with np.load(path, allow_pickle=False) as loaded:
        values = {name: np.asarray(loaded[name]) for name in loaded.files}
    category = np.asarray(values["category_mass"], dtype=np.float64)
    moments = np.asarray(values["survival_moments"], dtype=np.float64)
    if category.shape != (1, len(site_ids), 7) or moments.shape != (181, len(site_ids), 7, 7):
        raise ValueError("Goal053 integration dimensions changed")
    return joint.BridgeIntegration(
        (1.0,), tuple(float(x) for x in EFFECTS), site_ids, category, (moments,), bank_checksum
    )


def _canonical_row(
    values: Mapping[str, AnyArray], n: int | None = None
) -> tuple[FloatArray, FloatArray, FloatArray]:
    required = {"latent_training", "latent_holdout_joint", "latent_holdout_predator"}
    if set(values) != required:
        raise ValueError("score row schema changed")
    train = np.asarray(values["latent_training"], dtype=np.float64)
    held = np.asarray(values["latent_holdout_joint"], dtype=np.float64)
    pred = np.asarray(values["latent_holdout_predator"], dtype=np.float64)
    if train.ndim == 2 and train.shape[1] == 181 and train.shape[0] % 12 == 0:
        train = train.reshape(-1, 12, 181)
        held = held.reshape(-1, 12, 181)
        if pred.ndim == 1 and pred.shape[0] == train.shape[0] * 12:
            pred = pred.reshape(train.shape[0], 12)
    if (
        train.ndim != 3
        or train.shape[1:] != (12, 181)
        or held.shape != train.shape
        or pred.shape != train.shape[:2]
    ):
        raise ValueError("score row dimensions changed")
    if n is not None and train.shape[0] != n:
        raise ValueError("score row history count changed")
    if not np.isfinite(train).all() or not np.isfinite(held).all() or not np.isfinite(pred).all():
        raise ValueError("score row contains non-finite values")
    return train, held, pred


def reduce_rows(
    rows: Iterable[tuple[int, Mapping[str, AnyArray]]],
    *,
    blocks: int,
    archive_ids: AnyArray | None = None,
    supplied_mean: AnyArray | None = None,
    truth_h: AnyArray | None = None,
) -> dict[str, AnyArray]:
    """Reduce complete beta rows with beta-major/h-minor first ties."""

    if blocks <= 0:
        raise ValueError("block count must be positive")
    best = np.full((blocks, 12), -np.inf)
    null = np.full_like(best, -np.inf)
    best_h = np.zeros((blocks, 12), dtype=np.int64)
    best_beta = np.zeros_like(best_h)
    null_beta = np.zeros_like(best_h)
    held_best = np.empty_like(best)
    held_null = np.empty_like(best)
    constant_h = np.zeros_like(best_h)
    constant_t = np.empty_like(best)
    held_constant = np.empty_like(best)
    held_constant_null = np.empty_like(best)
    null_profiles = np.empty((blocks, 12, 81), dtype=np.float64)
    seen: list[int] = []
    expected_predator: FloatArray | None = None
    for index, values in rows:
        if int(index) != len(seen) or int(index) >= len(BETAS):
            raise ValueError("incomplete, duplicate or unordered beta rows")
        train, held, predator = _canonical_row(values, blocks)
        if expected_predator is not None and not np.array_equal(predator, expected_predator):
            raise ValueError("predator marginal changed across beta")
        expected_predator = predator.copy()
        h = np.argmax(train, axis=2)
        row_best = np.take_along_axis(train, h[:, :, None], axis=2)[:, :, 0]
        better = row_best > best
        best[better] = row_best[better]
        best_h[better] = h[better]
        best_beta[better] = int(index)
        held_best[better] = np.take_along_axis(held, h[:, :, None], axis=2)[:, :, 0][better]
        row_null = train[:, :, 0]
        better_null = row_null > null
        null[better_null] = row_null[better_null]
        null_beta[better_null] = int(index)
        held_null[better_null] = held[:, :, 0][better_null]
        null_profiles[:, :, index] = row_null
        if index == BETA_ZERO_INDEX:
            constant_h = h.copy()
            constant_t = 2.0 * (row_best - row_null)
            held_constant = np.take_along_axis(held, h[:, :, None], axis=2)[:, :, 0]
            held_constant_null = held[:, :, 0]
        seen.append(int(index))
    if seen != list(range(len(BETAS))):
        raise ValueError("incomplete beta-row coverage")
    adjusted_t = 2.0 * (best - null)
    d_beta = 2.0 * (null[:, :, None] - null_profiles)
    for value in (adjusted_t, constant_t, d_beta):
        if not np.isfinite(value).all() or (value < 0.0).any():
            raise ValueError("invalid nonnegative LR statistic")
    if archive_ids is None:
        archive_ids = np.asarray([[f"replicate-{i:04d}"] * 12 for i in range(blocks)])
    archive_ids = np.asarray(archive_ids).astype(str)
    if archive_ids.shape != (blocks, 12):
        raise ValueError("archive ID dimensions changed")
    means = (
        SUPPLIED_MEANS.copy()
        if supplied_mean is None
        else np.asarray(supplied_mean, dtype=np.float64)
    )
    truths = np.full(12, np.nan) if truth_h is None else np.asarray(truth_h, dtype=np.float64)
    if means.shape != (12,) or truths.shape != (12,):
        raise ValueError("condition metadata dimensions changed")
    return {
        "evaluation_t_adj": adjusted_t,
        "evaluation_t_constant": constant_t,
        "evaluation_d_beta": d_beta,
        "evaluation_h_hat_adj": EFFECTS[best_h],
        "evaluation_beta_hat_adj": BETAS[best_beta],
        "evaluation_h_hat_constant": EFFECTS[constant_h],
        "evaluation_beta_hat_null": BETAS[null_beta],
        "evaluation_delta_holdout_adj_constant": held_best - held_constant,
        "evaluation_delta_holdout_adj_neutral": held_best - held_null,
        "evaluation_delta_holdout_constant_neutral": held_constant - held_constant_null,
        "betas": BETAS.copy(),
        "effects": EFFECTS.copy(),
        "cell_ids": np.asarray(CELL_IDS),
        "truth_h": truths,
        "archive_ids": archive_ids,
        "supplied_mean": means,
    }


def worker_identity() -> dict[str, str]:
    return {"host": platform.node(), "python": platform.python_version(), "numpy": np.__version__}


__all__ = [
    "BATCH_SIZE",
    "BETAS",
    "CELL_IDS",
    "EFFECTS",
    "GOAL051_CELLS",
    "GOAL054_CELLS",
    "MEANS",
    "OLD_GENERATOR_MEAN",
    "OLD_SUPPLIED_MEAN",
    "build_new_integration",
    "commit_npz",
    "fingerprint",
    "histories_from_arrays",
    "integration_identity",
    "load_goal051_archive",
    "load_goal054_controls",
    "load_or_build_new_integration",
    "read_committed",
    "reconstruct_goal051_panel",
    "reduce_rows",
    "run_phase",
    "select_goal054_archive",
    "sha256",
    "source_hashes",
    "verify_goal051_archive_replay",
    "verify_goal051_replay",
    "verify_goal054_correct_level_replay",
    "write_json",
]


def run_phase(
    *,
    root: Path,
    phase: str,
    goal054_root: Path,
    goal051_root: Path,
    old_root: Path,
    bank_cache: Path,
    workers: int = 16,
    batch_size: int = BATCH_SIZE,
) -> dict[str, Any]:
    """Run a timing or production archive phase.

    The parent execution wrapper owns process limits, timeout and receipts.  This
    function owns only authenticated inputs, row caches and deterministic
    reduction; a completed phase is never silently resumed or replaced.
    """

    if phase not in {"timing", "production"} or workers <= 0 or batch_size <= 0:
        raise ValueError("phase, workers and batch size are invalid")
    phase_started = time.perf_counter()
    output = root / phase / "output"
    output.mkdir(parents=True, exist_ok=True)
    summary_path = output / "run_summary.json"
    if summary_path.exists():
        raise ValueError("completed phase cannot be restarted")
    timing_summary_path = root / "timing" / "output" / "run_summary.json"
    timing_summary_values: dict[str, Any] | None = None
    if phase == "production":
        if not timing_summary_path.exists():
            raise ValueError("production requires a completed timing phase")
        timing_summary_values = json.loads(timing_summary_path.read_text(encoding="utf-8"))
    g054_output = goal054_root / "production" / "output"
    g051_output = goal051_root / "production" / "output"
    observations_path = g054_output / "observations_evaluation.npz"
    stats_path = g054_output / "stats.npz"
    archive_path = g051_output / "campaign_arrays.npz"
    count = 8 if phase == "timing" else 1000
    goal054_contract_path = goal054_root / "run_contract.json"
    if not goal054_contract_path.is_file():
        raise ValueError("Goal054 run contract is required")
    goal054_contract_digest = sha256(goal054_contract_path)
    if goal054_contract_digest != GOAL054_RUN_CONTRACT_SHA256:
        raise ValueError("Goal054 run contract SHA256 does not match the frozen input")
    goal054_contract = json.loads(goal054_contract_path.read_text(encoding="utf-8"))
    bound = goal054_contract.get("integration_input_sha256")
    if not isinstance(bound, dict) or len(bound) != 162:
        raise ValueError("Goal054 run contract must bind exactly 162 integration files")
    expected_names = {
        f"/data/codex/scratch/goal053-prospective-background-20260927/integrations/{index:03d}.{suffix}"
        for index in range(81)
        for suffix in ("npz", "json")
    }
    if set(str(name) for name in bound) != expected_names:
        raise ValueError("Goal054 integration contract paths changed")
    if any(not isinstance(digest, str) or len(digest) != 64 for digest in bound.values()):
        raise ValueError("Goal054 integration contract contains invalid hashes")
    contract_prefix = "/data/codex/scratch/goal053-prospective-background-20260927/integrations/"
    old_hashes = {
        index: {
            "npz": str(bound[f"{contract_prefix}{index:03d}.npz"]),
            "json": str(bound[f"{contract_prefix}{index:03d}.json"]),
        }
        for index in range(81)
    }
    for index, hashes in old_hashes.items():
        path = old_root / "integrations" / f"{index:03d}.npz"
        receipt = path.with_suffix(".json")
        if not path.is_file() or not receipt.is_file():
            raise ValueError(f"Goal053 integration cache is missing or partial: {path}")
        if sha256(path) != hashes["npz"] or sha256(receipt) != hashes["json"]:
            raise ValueError(f"Goal053 integration input hash changed: {path}")
    fixed = benchmark.build_fixed_inputs()
    setup = goal051.build_generator_setup(fixed)
    site_ids = tuple(setup.site_ids)
    bank, bank_provenance = legacy.load_verified_bank(
        bank_cache, legacy.production_config("timing"), site_ids
    )
    prepared = adjusted.prepare_bank(np.asarray(bank, dtype=np.float64), site_ids)
    original_integration = adequacy._build_primary_integration(
        np.asarray(bank, dtype=np.float64), adequacy.production_config("timing"), site_ids
    )
    setup_seconds = time.perf_counter() - phase_started
    reconstruction_started = time.perf_counter()
    goal054_panel = select_goal054_archive(observations_path, blocks=count)
    goal054_controls = load_goal054_controls(stats_path)
    if tuple(goal054_controls["cell_ids"].astype(str))[:4] != GOAL054_CELLS:
        raise ValueError("Goal054 saved controls changed cell order")
    goal051_archive = load_goal051_archive(archive_path)
    inputs = {
        "goal054_observations": sha256(observations_path),
        "goal054_stats": sha256(stats_path),
        "goal051_archive": sha256(archive_path),
    }
    repository = Path(__file__).resolve().parents[2]
    contract_payload = {
        "schema_version": 1,
        "workflow": "goal055-nuisance-checks-v1",
        "source_hashes": source_hashes(repository),
        "inputs": inputs,
        "goal054_run_contract_sha256": goal054_contract_digest,
        "goal051_generator_mean_literal": OLD_GENERATOR_MEAN,
        "goal053_integration_input_sha256": bound,
        "bank": bank_provenance,
        "bank_checksum": prepared.bank_checksum,
        "effects": EFFECTS.tolist(),
        "betas": BETAS.tolist(),
        "cell_ids": list(CELL_IDS),
        "supplied_mean": SUPPLIED_MEANS.tolist(),
    }
    core = fingerprint(contract_payload)
    if phase == "production":
        if (
            timing_summary_values is None
            or timing_summary_values.get("fingerprint") != core
            or not timing_summary_values.get("controls_passed", False)
        ):
            raise ValueError("production timing core does not match this input contract")
        if timing_summary_values.get("goal054_run_contract_sha256") != goal054_contract_digest:
            raise ValueError("production timing Goal054 contract binding changed")
    contract = {**contract_payload, "fingerprint": core}
    contract_path = root / "run_contract.json"
    if contract_path.exists():
        existing = json.loads(contract_path.read_text(encoding="utf-8"))
        if existing != contract:
            raise ValueError("run contract changed; prior caches are not reusable")
    else:
        write_json(contract_path, contract)
    phase_contract = {
        "phase": phase,
        "blocks": count,
        "workers": workers,
        "batch_size": batch_size,
        "core": core,
    }
    write_json(output / "phase_contract.json", phase_contract)
    map_A = np.asarray(setup.exposure_score, dtype=np.float64)
    site_A = map_A[setup.site_rows, setup.site_cols]
    direct_hazard_checks = 0
    direct_hazard_max_error = 0.0
    direct_hazard_max_relative_error = 0.0
    for mean in MEANS:
        for index in (0, BETA_ZERO_INDEX, len(BETAS) - 1):
            hazards = adjusted.normalized_hazards(
                float(BETAS[index]), map_A, site_A, mean_hazard=float(mean)
            )
            if np.asarray(hazards).shape != site_A.shape or not np.isfinite(hazards).all():
                raise ValueError("direct site-hazard validation failed")
            scaled = float(BETAS[index]) * np.asarray(map_A, dtype=np.float64)
            shift = float(np.max(scaled))
            map_weights = np.exp(scaled - shift)
            expected = (
                float(mean) * np.exp(float(BETAS[index]) * site_A - shift) / map_weights.mean()
            )
            error = float(np.max(np.abs(np.asarray(hazards) - expected)))
            relative = float(
                np.max(
                    np.abs(np.asarray(hazards) - expected) / np.maximum(np.abs(expected), 1e-300)
                )
            )
            direct_hazard_max_error = max(direct_hazard_max_error, error)
            direct_hazard_max_relative_error = max(direct_hazard_max_relative_error, relative)
            if error > REPLAY_TOLERANCE or not math.isclose(
                float(np.mean(float(mean) * map_weights / map_weights.mean())),
                float(mean),
                rel_tol=REPLAY_TOLERANCE,
                abs_tol=REPLAY_TOLERANCE,
            ):
                raise ValueError("direct site-hazard normalization failed")
            if index == BETA_ZERO_INDEX and not np.allclose(
                np.asarray(hazards), float(mean), rtol=0.0, atol=REPLAY_TOLERANCE
            ):
                raise ValueError("beta-zero site hazards do not equal supplied mean")
            direct_hazard_checks += 1
    goal051_panel = reconstruct_goal051_panel(
        goal051_archive,
        fixed,
        setup,
        blocks=count,
        replay_integration=original_integration,
    )
    goal051_replay: dict[str, Any] | None = goal051_panel.pop("replay_diagnostics", None)
    if goal051_replay is None:
        raise ValueError("Goal051 replay diagnostics were not produced")
    reconstruction_seconds = time.perf_counter() - reconstruction_started
    replay_started = time.perf_counter()
    if phase == "timing":
        goal054_replay = verify_goal054_correct_level_replay(
            goal054_panel,
            goal054_controls,
            old_root=old_root,
            site_ids=site_ids,
            bank_checksum=prepared.bank_checksum,
            old_hashes=old_hashes,
            blocks=count,
            batch_size=batch_size,
        )
    else:
        if timing_summary_values is None:
            raise ValueError("production timing summary disappeared")
        timing_goal054_replay = timing_summary_values.get("goal054_replay")
        if (
            not isinstance(timing_goal054_replay, dict)
            or timing_goal054_replay.get("blocks") != 8
            or timing_goal054_replay.get("rows") != len(BETAS)
            or float(timing_goal054_replay.get("max_abs_error", math.inf)) > REPLAY_TOLERANCE
        ):
            raise ValueError("timing summary lacks Goal054 replay proof")
        goal054_replay = cast(dict[str, Any], timing_goal054_replay)
    old_original = _load_old_integration(
        old_root,
        BETA_ZERO_INDEX,
        site_ids,
        prepared.bank_checksum,
        expected_sha256=old_hashes[BETA_ZERO_INDEX]["npz"],
        expected_receipt_sha256=old_hashes[BETA_ZERO_INDEX]["json"],
    )
    beta0_error = max(
        float(np.max(np.abs(original_integration.category_mass - old_original.category_mass))),
        float(
            np.max(
                np.abs(original_integration.survival_moments[0] - old_original.survival_moments[0])
            )
        ),
    )
    if beta0_error > REPLAY_TOLERANCE:
        raise ValueError(f"beta0 original integration mismatch: {beta0_error:.3g}")
    replay_seconds = time.perf_counter() - replay_started
    archive_ids = panel_archive_ids(goal054_panel, goal051_panel)
    truth_h = np.asarray([1.0, 3.0, 1.0, 3.0] * 3, dtype=np.float64)
    phase_id = fingerprint(
        {"core": core, "blocks": count, "archive_ids": _array_checksum(archive_ids)}
    )
    panel_serialization_started = time.perf_counter()
    for name, panel in (("goal054", goal054_panel), ("goal051", goal051_panel)):
        panel_identity = fingerprint(
            {
                "core": core,
                "phase": phase,
                "panel": name,
                "goal054": inputs["goal054_observations"],
                "goal051": inputs["goal051_archive"],
            }
        )
        panel_path = output / f"observations_{name}.npz"
        panel_values = {
            key: value
            for key, value in panel.items()
            if key
            in {
                "predator_counts",
                "prey_counts",
                "site_ids",
                "site_cluster_ids",
                "site_splits",
                "archive_ids",
                "cell_ids",
                "truth_h",
                "truth_beta",
                "replicate_indices",
                "effects",
                "betas",
            }
        }
        cached_panel = read_committed(panel_path, panel_identity)
        if cached_panel is None:
            panel_record: dict[str, Any] = {
                "identity": panel_identity,
                "panel": name,
                "blocks": count,
            }
            commit_npz(panel_path, panel_values, panel_record)
        else:
            _observation_values(cached_panel[0])
    panel_serialization_seconds = time.perf_counter() - panel_serialization_started

    # Integration construction is independent of the number of histories.
    # Complete and time it before the scoring-only worker stage, whose cache
    # reads, likelihood work and row serialization scale conservatively below.
    def prepare_integrations(index: int) -> float:
        elapsed_total = 0.0
        for mean in MEANS:
            _, elapsed, _ = load_or_build_new_integration(
                root,
                prepared,
                index=index,
                beta=float(BETAS[index]),
                mean_hazard=mean,
                map_A=map_A,
                site_A=site_A,
                core=core,
                allow_build=phase == "timing",
            )
            elapsed_total += elapsed
        return elapsed_total

    integration_started = time.perf_counter()
    if workers == 1:
        integration_work = [prepare_integrations(index) for index in range(len(BETAS))]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            integration_work = list(executor.map(prepare_integrations, range(len(BETAS))))
    integration_wall_seconds = time.perf_counter() - integration_started
    integration_seconds = float(sum(integration_work))

    def compute_row(index: int, beta: float) -> dict[str, Any]:
        identity = fingerprint(
            {
                "phase": phase_id,
                "beta_index": index,
                "beta": float(beta),
                "mean_hazards": MEANS,
                "old_mean": OLD_SUPPLIED_MEAN,
            }
        )
        row_path = output / "rows" / f"{index:03d}.npz"
        cached = read_committed(row_path, identity)
        if cached is not None:
            values, record = cached
            _canonical_row(values, count)
            return {
                "index": index,
                "record": record,
                "integration_seconds": 0.0,
                "scoring_seconds": 0.0,
            }
        integrations = []
        row_integration_seconds = 0.0
        for mean in MEANS:
            integration, elapsed, _ = load_or_build_new_integration(
                root,
                prepared,
                index=index,
                beta=float(beta),
                mean_hazard=mean,
                map_A=map_A,
                site_A=site_A,
                core=core,
                allow_build=False,
            )
            integrations.append(integration)
            row_integration_seconds += elapsed
        began = time.perf_counter()
        old = _load_old_integration(
            old_root,
            index,
            site_ids,
            prepared.bank_checksum,
            expected_sha256=old_hashes[index]["npz"],
            expected_receipt_sha256=old_hashes[index]["json"],
        )
        # Goal054 has two mean lanes; Goal051 remains the existing-mean control.
        g054_scores = [
            _score_panel(goal054_panel, integration, batch_size) for integration in integrations
        ]
        g051_score = _score_panel(goal051_panel, old, batch_size)
        train = np.empty((count, 12, 181), dtype=np.float64)
        held = np.empty_like(train)
        pred = np.empty((count, 12), dtype=np.float64)
        for lane, score in enumerate(g054_scores):
            train[:, lane * 4 : lane * 4 + 4] = score[0].reshape(count, 4, 181)
            held[:, lane * 4 : lane * 4 + 4] = score[1].reshape(count, 4, 181)
            pred[:, lane * 4 : lane * 4 + 4] = score[2].reshape(count, 4)
        train[:, 8:12] = g051_score[0].reshape(count, 4, 181)
        held[:, 8:12] = g051_score[1].reshape(count, 4, 181)
        pred[:, 8:12] = g051_score[2].reshape(count, 4)
        row_scoring_seconds = time.perf_counter() - began
        values = {
            "latent_training": train,
            "latent_holdout_joint": held,
            "latent_holdout_predator": pred,
        }
        _canonical_row(values, count)
        record = {
            "identity": identity,
            "phase_fingerprint": phase_id,
            "index": index,
            "beta": float(beta),
            "scoring_seconds": row_scoring_seconds,
        }
        commit_npz(row_path, values, record)
        return {
            "index": index,
            "record": record,
            "integration_seconds": row_integration_seconds,
            "scoring_seconds": row_scoring_seconds,
        }

    records: list[dict[str, Any]] = []
    scoring_wall_started = time.perf_counter()
    if workers == 1:
        records = [compute_row(index, float(beta)) for index, beta in enumerate(BETAS)]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(compute_row, index, float(beta)) for index, beta in enumerate(BETAS)
            ]
            for future in as_completed(futures):
                records.append(future.result())
    records.sort(key=lambda value: int(value["index"]))
    scoring_wall_seconds = time.perf_counter() - scoring_wall_started
    cache_read_worker_seconds = float(sum(float(value["integration_seconds"]) for value in records))
    scoring_seconds = float(sum(float(value["scoring_seconds"]) for value in records))
    row_serialization_worker_seconds = float(
        sum(float(value["record"].get("serialization_seconds", 0.0)) for value in records)
    )

    def iter_rows() -> Iterable[tuple[int, Mapping[str, AnyArray]]]:
        for index, beta in enumerate(BETAS):
            identity = fingerprint(
                {
                    "phase": phase_id,
                    "beta_index": index,
                    "beta": float(beta),
                    "mean_hazards": MEANS,
                    "old_mean": OLD_SUPPLIED_MEAN,
                }
            )
            cached = read_committed(output / "rows" / f"{index:03d}.npz", identity)
            if cached is None:
                raise ValueError("row disappeared before reduction")
            values, _ = cached
            yield index, values

    reduction_started = time.perf_counter()
    stats = reduce_rows(
        iter_rows(),
        blocks=count,
        archive_ids=archive_ids,
        supplied_mean=SUPPLIED_MEANS,
        truth_h=truth_h,
    )
    reduction_seconds = time.perf_counter() - reduction_started
    stats_serialization_started = time.perf_counter()
    stats_record: dict[str, Any] = {
        "identity": fingerprint({"phase": phase_id, "kind": "stats"}),
        "phase_fingerprint": phase_id,
        "blocks": count,
    }
    commit_npz(output / "stats.npz", stats, stats_record)
    stats_serialization_seconds = time.perf_counter() - stats_serialization_started
    finalization_started = time.perf_counter()
    integration_hashes: dict[str, str] = {}
    for path in sorted((root / "integrations").rglob("*")):
        if path.is_file() and path.suffix in {".npz", ".json"}:
            integration_hashes[str(path.relative_to(root))] = sha256(path)
    expected_integration_names = {
        f"integrations/mu-{mean:.4f}/{index:03d}.{suffix}"
        for mean in MEANS
        for index in range(len(BETAS))
        for suffix in ("npz", "json")
    }
    if set(integration_hashes) != expected_integration_names:
        raise ValueError("new-mean integration cache inventory is incomplete")
    if phase == "production" and (
        timing_summary_values is None
        or timing_summary_values.get("new_integration_hashes") != integration_hashes
    ):
        raise ValueError("production new-mean integration cache hashes changed")
    source_unchanged = source_hashes(repository) == contract["source_hashes"]
    proof_blocks = count
    goal051_controls_passed = bool(
        isinstance(goal051_replay, dict)
        and goal051_replay.get("histories") == proof_blocks * len(GOAL051_CELLS)
        and goal051_replay.get("mle_matches") == proof_blocks * len(GOAL051_CELLS)
        and goal051_replay.get("opaque_id_matches") == proof_blocks * len(GOAL051_CELLS)
        and float(goal051_replay.get("max_profile_abs_error", math.inf)) <= REPLAY_TOLERANCE
        and float(goal051_replay.get("max_holdout_abs_error", math.inf)) <= REPLAY_TOLERANCE
        and float(goal051_replay.get("max_prey_abs_error", math.inf)) <= REPLAY_TOLERANCE
        and float(goal051_replay.get("max_predator_abs_error", math.inf)) <= REPLAY_TOLERANCE
        and float(goal051_replay.get("max_h1_factorization_abs_error", math.inf))
        <= REPLAY_TOLERANCE
    )
    goal054_controls_passed = (
        float(goal054_replay.get("max_abs_error", math.inf)) <= REPLAY_TOLERANCE
    )
    controls_passed = bool(
        source_unchanged
        and goal051_controls_passed
        and goal054_controls_passed
        and beta0_error <= REPLAY_TOLERANCE
        and direct_hazard_checks == 6
        and len(old_hashes) == 81
    )
    output_hashes = {
        str(path.relative_to(output)): sha256(path)
        for path in output.rglob("*")
        if path.is_file() and path.name != "run_summary.json" and ".tmp" not in path.name
    }
    finalization_seconds = time.perf_counter() - finalization_started
    phase_wall_seconds = time.perf_counter() - phase_started
    summary = {
        "phase": phase,
        "fingerprint": core,
        "phase_fingerprint": phase_id,
        "blocks": count,
        "rows": len(records),
        "workers": workers,
        "batch_size": batch_size,
        "worker_identity": worker_identity(),
        "source_identity_unchanged": source_unchanged,
        "controls_passed": controls_passed,
        "goal054_run_contract_sha256": goal054_contract_digest,
        "goal054_integration_hashes": bound,
        "new_integration_hashes": integration_hashes,
        "goal054_replay": goal054_replay,
        "goal051_replay": goal051_replay,
        "beta0_original_route_max_abs_error": beta0_error,
        "direct_site_hazard_checks": direct_hazard_checks,
        "direct_site_hazard_max_abs_error": direct_hazard_max_error,
        "direct_site_hazard_max_relative_error": direct_hazard_max_relative_error,
        "h1_factorization_passed": bool(
            isinstance(goal051_replay, dict)
            and float(goal051_replay.get("max_h1_factorization_abs_error", math.inf))
            <= REPLAY_TOLERANCE
        ),
        "phase_wall_seconds": phase_wall_seconds,
        "setup_seconds": setup_seconds,
        "reconstruction_seconds": reconstruction_seconds,
        "replay_seconds": replay_seconds,
        "panel_serialization_seconds": panel_serialization_seconds,
        "stats_serialization_seconds": stats_serialization_seconds,
        "row_serialization_worker_seconds": row_serialization_worker_seconds,
        "cache_read_worker_seconds": cache_read_worker_seconds,
        "reduction_seconds": reduction_seconds,
        "finalization_seconds": finalization_seconds,
        "integration_seconds": integration_seconds,
        "integration_wall_seconds": integration_wall_seconds,
        "scoring_seconds": scoring_seconds,
        "scoring_wall_seconds": scoring_wall_seconds,
        "worker_waves": math.ceil(len(BETAS) / workers),
        "output_sha256": output_hashes,
    }
    if phase == "timing":
        scale = 1000 / count
        scalable = (
            reconstruction_seconds
            + panel_serialization_seconds
            + scoring_wall_seconds
            + reduction_seconds
            + stats_serialization_seconds
            + finalization_seconds
        ) * scale
        # The fixed allowance retains the complete measured integration stage
        # even though production only authenticates/loads those same caches.
        # Row serialization is already inside scoring_wall_seconds, and is not
        # added again. All worker-sum times above are descriptive, not wall time.
        fixed_seconds = setup_seconds + integration_wall_seconds + replay_seconds
        summary["projection"] = {
            "fixed_seconds": fixed_seconds,
            "scalable_seconds": scalable,
            "fixed_control_seconds": replay_seconds,
            "synthesis_review_reserve_seconds": 3600.0,
            "complete_production_seconds": 1.5 * (fixed_seconds + scalable) + 3600.0,
            "margin_multiplier": 1.5,
            "integration_wall_seconds": integration_wall_seconds,
            "scoring_seconds": scoring_seconds * scale,
            "scoring_wall_seconds": scoring_wall_seconds * scale,
            "construction_is_not_history_scaled": True,
            "workers": workers,
        }
    else:
        summary["complete_production_seconds"] = phase_wall_seconds
    write_json(summary_path, summary)
    return summary
