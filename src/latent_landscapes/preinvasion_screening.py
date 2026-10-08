"""Goal057 public pre-invasion screening pilot.

The pilot is deliberately a small orchestration layer around the frozen
pre-invasion likelihood and calibration modules.  It generates only the
pre-invasion observations needed for one true nuisance node at a time, scores
the 99 histories at that node and its axis neighbours, and immediately drops
the observation arrays.  The public sixteen-history panel is loaded and
checked, never regenerated.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import time
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import adjusted_background_likelihood as adjusted
from latent_landscapes import preinvasion_calibration as calibration
from latent_landscapes import preinvasion_campaign as campaign
from latent_landscapes import preinvasion_fitting as fitting
from latent_landscapes import preinvasion_likelihood as likelihood

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

ROOT_SEED = 2026100401
SEED_NAMESPACE = 57
STAGE_LOSS = 1
STAGE_SITE_DETECTION = 2
STAGE_VISITS = 3
STAGES = (STAGE_LOSS, STAGE_SITE_DETECTION, STAGE_VISITS)
REFERENCE_COUNT = calibration.SCREEN_REFERENCE_COUNT
GRID_SIZE = calibration.GRID_SIZE
EXPECTED_PANEL_SHA256 = "77dc9688bf8714f76d768d9da3966ebeae9df62e092842da13dec2867e19d45c"
DEFAULT_PANEL = Path("artifacts/goal056_execution/panel/panel")


class ScreeningNumericalError(RuntimeError):
    """A fatal numerical gate; callers must preserve the partial attempt."""


@dataclass(frozen=True, slots=True)
class SeedAddress:
    node_index: int
    reference_index: int
    stage: int
    state_fingerprint: int


@dataclass(frozen=True, slots=True)
class PublicPanel:
    observations: likelihood.PreInvasionObservations
    map_a: FloatArray
    site_a: FloatArray
    panel_sha256: str
    manifest: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ReferenceBatch:
    observations: likelihood.PreInvasionObservations
    node_index: int
    reference_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class NodeResult:
    node_index: int
    reference_statistics: FloatArray
    neighbour_indices: tuple[int, ...]
    generation_seconds: float
    preparation_seconds: float
    scoring_seconds: float
    serialization_seconds: float = 0.0
    training_counts: IntArray | None = None
    predator_counts: IntArray | None = None

    @property
    def prey_counts(self) -> IntArray | None:
        """Alias used by audit consumers for the persisted pre-only counts."""
        return self.training_counts


def file_sha256(path: Path) -> str:
    """Return a file digest without loading the file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _panel_paths(panel: Path) -> tuple[Path, Path]:
    path = panel / "observations.npz" if panel.is_dir() else panel
    if not path.is_file():
        raise FileNotFoundError(f"public observations are absent: {path}")
    manifest = path.with_name("manifest.json")
    if not manifest.is_file():
        raise FileNotFoundError(f"public panel manifest is absent: {manifest}")
    return path, manifest


def load_public_panel(
    panel: Path = DEFAULT_PANEL, *, require_known_hash: bool = True
) -> PublicPanel:
    """Load and validate the existing Goal056 public panel.

    The panel arrays are copied only where the likelihood preparation sorts
    site identifiers.  No raw data are modified or rewritten.
    """
    observation_path, manifest_path = _panel_paths(Path(panel))
    observed_hash = file_sha256(observation_path)
    manifest = json.loads(manifest_path.read_text())
    expected_hash = str(manifest.get("observation_sha256", ""))
    if observed_hash != expected_hash:
        raise ScreeningNumericalError("public panel observation hash disagrees with its manifest")
    if require_known_hash and observed_hash != EXPECTED_PANEL_SHA256:
        raise ScreeningNumericalError("public panel is not the registered Goal056 fixture")
    if int(manifest.get("number_of_histories", -1)) != 16:
        raise ValueError("public panel must contain exactly 16 histories")
    with np.load(observation_path, allow_pickle=False) as values:
        required = {
            "prey_counts",
            "predator_counts",
            "site_ids",
            "site_splits",
            "map_a",
            "site_a",
            "prey_times",
            "predator_times",
        }
        if not required.issubset(values.files):
            raise ValueError(f"public panel is missing {sorted(required.difference(values.files))}")
        ids = tuple(str(item) for item in values["site_ids"])
        splits = np.asarray(values["site_splits"]).astype(str)
        if len(ids) != 160 or len(set(ids)) != 160 or int(np.sum(splits == "training")) != 120:
            raise ValueError("public panel must contain 160 unique sites and 120 training sites")
        observed = likelihood.prepare_observations(
            values["prey_counts"],
            values["predator_counts"],
            ids,
            splits == "training",
            prey_times=values["prey_times"],
            predator_times=values["predator_times"],
        )
        order = np.argsort(np.asarray(ids), kind="stable")
        map_a = np.asarray(values["map_a"], dtype=np.float64).copy()
        site_a = np.asarray(values["site_a"], dtype=np.float64)[order].copy()
    _, setup = campaign.public_inputs()
    setup_ids = tuple(str(value) for value in setup.site_ids)
    setup_splits = np.asarray(setup.site_splits).astype(str)
    setup_site_a = np.asarray(
        setup.exposure_score[setup.site_rows, setup.site_cols], dtype=np.float64
    )
    if ids != setup_ids or not np.array_equal(splits, setup_splits):
        raise ScreeningNumericalError("public panel design does not match campaign.public_inputs()")
    if (
        not np.allclose(site_a, setup_site_a, rtol=0.0, atol=1e-12)
        or map_a.shape != setup.exposure_score.shape
    ):
        raise ScreeningNumericalError("public panel map/design values do not match public_inputs()")
    if observed.site_ids != tuple(sorted(ids)):
        raise ValueError("public panel site ordering is not deterministic")
    if not np.isfinite(map_a).all() or not np.isfinite(site_a).all():
        raise ValueError("public panel map values must be finite")
    return PublicPanel(observed, map_a, site_a, observed_hash, manifest)


def seed_sequence(
    node_index: int,
    reference_index: int,
    stage: int,
    *,
    root: int = ROOT_SEED,
) -> np.random.SeedSequence:
    """Return the registered address-based seed sequence."""
    if not 0 <= node_index < GRID_SIZE:
        raise IndexError("node index is outside the nuisance grid")
    if not 0 <= reference_index < REFERENCE_COUNT:
        raise IndexError("reference index is outside the 99-reference design")
    if stage not in STAGES:
        raise ValueError("unknown screening RNG stage")
    return np.random.SeedSequence([root, SEED_NAMESPACE, node_index, reference_index, stage])


def stage_seed(
    node_index: int,
    reference_index: int,
    stage: int,
    *,
    root: int = ROOT_SEED,
) -> int:
    """Return the uint64 state fingerprint for an exact seed address.

    The fingerprint is audit metadata only.  It is never passed back into a
    second ``SeedSequence``; draws use :func:`rng_for` directly.
    """
    return int(
        seed_sequence(node_index, reference_index, stage, root=root).generate_state(
            1, dtype=np.uint64
        )[0]
    )


def rng_for(
    node_index: int,
    reference_index: int,
    stage: int,
    *,
    root: int = ROOT_SEED,
) -> np.random.Generator:
    return np.random.Generator(
        np.random.PCG64(seed_sequence(node_index, reference_index, stage, root=root))
    )


def seed_ledger() -> NDArray[np.uint64]:
    """Build the complete compact seed ledger before any reference draw."""
    rows = np.empty((GRID_SIZE * REFERENCE_COUNT * len(STAGES), 4), dtype=np.uint64)
    row = 0
    for node in range(GRID_SIZE):
        for reference in range(REFERENCE_COUNT):
            for stage in STAGES:
                rows[row] = (node, reference, stage, stage_seed(node, reference, stage))
                row += 1
    return rows


def write_seed_ledger(path: Path, ledger: NDArray[np.uint64] | None = None) -> Path:
    """Persist the address ledger and its exact RNG contract before draws."""
    path.parent.mkdir(parents=True, exist_ok=True)
    values = seed_ledger() if ledger is None else np.asarray(ledger, dtype=np.uint64)
    if values.shape != (GRID_SIZE * REFERENCE_COUNT * len(STAGES), 4):
        raise ValueError("seed ledger has an unexpected shape")
    np.savez_compressed(
        path,
        node_index=values[:, 0],
        reference_index=values[:, 1],
        stage=values[:, 2],
        state_fingerprint=values[:, 3],
        root=np.uint64(ROOT_SEED),
        namespace=np.uint64(SEED_NAMESPACE),
    )
    return path


def validate_seed_ledger(path: Path, expected_sha256: str) -> None:
    """Validate the frozen address ledger before qualification or draws."""
    if not path.is_file() or file_sha256(path) != expected_sha256:
        raise ScreeningNumericalError("frozen seed ledger is missing or has changed")
    with np.load(path, allow_pickle=False) as values:
        required = {"node_index", "reference_index", "stage", "state_fingerprint"}
        if not required.issubset(values.files):
            raise ScreeningNumericalError("frozen seed ledger is incomplete")
        lengths = {len(values[key]) for key in required}
        expected_length = GRID_SIZE * REFERENCE_COUNT * len(STAGES)
        if lengths != {expected_length}:
            raise ScreeningNumericalError("frozen seed ledger has the wrong number of addresses")
        if (
            int(values.get("root", -1)) != ROOT_SEED
            or int(values.get("namespace", -1)) != SEED_NAMESPACE
        ):
            raise ScreeningNumericalError("frozen seed ledger uses the wrong seed contract")
        expected_nodes = np.repeat(
            np.arange(GRID_SIZE, dtype=np.uint64), REFERENCE_COUNT * len(STAGES)
        )
        expected_refs = np.tile(
            np.repeat(np.arange(REFERENCE_COUNT, dtype=np.uint64), len(STAGES)), GRID_SIZE
        )
        expected_stages = np.tile(np.asarray(STAGES, dtype=np.uint64), GRID_SIZE * REFERENCE_COUNT)
        if not (
            np.array_equal(values["node_index"], expected_nodes)
            and np.array_equal(values["reference_index"], expected_refs)
            and np.array_equal(values["stage"], expected_stages)
        ):
            raise ScreeningNumericalError("frozen seed ledger addresses are out of order")
        expected_fingerprints = np.fromiter(
            (
                stage_seed(int(node), int(reference), int(stage))
                for node, reference, stage in zip(
                    expected_nodes, expected_refs, expected_stages, strict=True
                )
            ),
            dtype=np.uint64,
            count=expected_length,
        )
        if not np.array_equal(values["state_fingerprint"], expected_fingerprints):
            raise ScreeningNumericalError(
                "frozen seed ledger fingerprints disagree with the seed contract"
            )


def _site_detection(rng: np.random.Generator, sd: float, count: int) -> FloatArray:
    if sd == 0.0:
        return np.full(count, 0.65, dtype=np.float64)
    concentration = 0.65 * 0.35 / sd**2 - 1.0
    if concentration <= 0.0 or not math.isfinite(concentration):
        raise ValueError("detection SD is outside the persistent Beta domain")
    return rng.beta(0.65 * concentration, 0.35 * concentration, size=count)


def _reference_arrays(
    panel: PublicPanel,
    node_index: int,
    reference_index: int,
    *,
    root: int = ROOT_SEED,
) -> tuple[IntArray, IntArray]:
    node = calibration.NUISANCE_GRID[node_index]
    hazards = adjusted.normalized_hazards(node.beta, panel.map_a, panel.site_a, node.mu)
    threshold = rng_for(node_index, reference_index, STAGE_LOSS, root=root).exponential(
        size=len(panel.site_a)
    )
    losses = -60.0 + threshold / hazards
    prey_alive = losses[:, None] > np.asarray(likelihood.DEFAULT_PREY_TIMES)[None, :]
    detection = _site_detection(
        rng_for(node_index, reference_index, STAGE_SITE_DETECTION, root=root),
        node.detection_sd,
        len(panel.site_a),
    )
    visits = rng_for(node_index, reference_index, STAGE_VISITS, root=root).random(
        (len(panel.site_a), 7, 2)
    )
    prey = ((visits < detection[:, None, None]).sum(axis=2) * prey_alive[:, :7]).astype(np.int64)
    full_prey = np.zeros((len(panel.site_a), 13), dtype=np.int64)
    full_prey[:, :7] = prey
    predator = np.zeros((len(panel.site_a), 6), dtype=np.int64)
    return full_prey, predator


def make_reference_batch(
    panel: PublicPanel,
    node_index: int,
    reference_indices: Iterable[int],
    *,
    root: int = ROOT_SEED,
) -> ReferenceBatch:
    """Generate one bounded batch of pre-only observations for one node."""
    indices = tuple(int(value) for value in reference_indices)
    if not indices or any(index < 0 or index >= REFERENCE_COUNT for index in indices):
        raise ValueError("reference indices must be a nonempty subset of 0..98")
    prey = np.empty((len(indices), len(panel.site_a), 13), dtype=np.int64)
    predator = np.zeros((len(indices), len(panel.site_a), 6), dtype=np.int64)
    for row, reference in enumerate(indices):
        prey[row], predator[row] = _reference_arrays(panel, node_index, reference, root=root)
    observations = likelihood.prepare_observations(
        prey,
        predator,
        panel.observations.site_ids,
        panel.observations.training_mask,
        prey_times=panel.observations.prey_times,
        predator_times=panel.observations.predator_times,
    )
    return ReferenceBatch(observations, node_index, indices)


def _pre_score(
    observations: likelihood.PreInvasionObservations,
    map_a: FloatArray,
    site_a: FloatArray,
    node_index: int,
) -> FloatArray:
    node = calibration.NUISANCE_GRID[node_index]
    hazards = adjusted.normalized_hazards(node.beta, map_a, site_a, node.mu)
    values = likelihood.pre_only_log_likelihood(
        observations, hazards, detection_sd=node.detection_sd, return_site=False
    )
    result = np.asarray(values, dtype=np.float64).reshape(-1)
    if not np.isfinite(result).all():
        raise ScreeningNumericalError(f"non-finite pre-only likelihood at node {node_index}")
    return result


def _pre_score_parameters(
    observations: likelihood.PreInvasionObservations,
    map_a: FloatArray,
    site_a: FloatArray,
    *,
    beta: float,
    mu: float,
    detection_sd: float,
) -> float:
    hazards = adjusted.normalized_hazards(beta, map_a, site_a, mu)
    values = likelihood.pre_only_log_likelihood(
        observations, hazards, detection_sd=detection_sd, return_site=False
    )
    result = float(np.asarray(values, dtype=np.float64).reshape(-1)[0])
    if not math.isfinite(result):
        raise ScreeningNumericalError("non-finite diagnostic pre-only likelihood")
    return result


def score_node(
    panel: PublicPanel,
    node_index: int,
    *,
    chunk_size: int = 99,
    diagnostic: bool = False,
    root: int = ROOT_SEED,
) -> NodeResult:
    """Generate and score one node, retaining at most one batch in memory."""
    if chunk_size < 1 or chunk_size > REFERENCE_COUNT:
        raise ValueError("chunk_size must be between one and 99")
    neighbours = calibration.axis_adjacent_indices(node_index)
    all_statistics: list[FloatArray] = []
    training_counts: list[IntArray] = []
    predator_counts: list[IntArray] = []
    generation_seconds = preparation_seconds = scoring_seconds = 0.0
    for start in range(0, REFERENCE_COUNT, chunk_size):
        indices = tuple(range(start, min(start + chunk_size, REFERENCE_COUNT)))
        generated = time.perf_counter()
        arrays = [_reference_arrays(panel, node_index, index, root=root) for index in indices]
        generation_seconds += time.perf_counter() - generated
        prepared = time.perf_counter()
        prey = np.stack([row[0] for row in arrays])
        predator = np.stack([row[1] for row in arrays])
        observations = likelihood.prepare_observations(
            prey,
            predator,
            panel.observations.site_ids,
            panel.observations.training_mask,
            prey_times=panel.observations.prey_times,
            predator_times=panel.observations.predator_times,
        )
        preparation_seconds += time.perf_counter() - prepared
        scored = time.perf_counter()
        values = np.stack(
            [
                _pre_score(observations, panel.map_a, panel.site_a, neighbour)
                for neighbour in neighbours
            ],
            axis=1,
        )
        scoring_seconds += time.perf_counter() - scored
        all_statistics.append(2.0 * np.maximum(values.max(axis=1) - values[:, 0], 0.0))
        if diagnostic:
            training_counts.append(
                np.asarray(observations.prey_counts[:, :, :7], dtype=np.int64).copy()
            )
            predator_counts.append(np.asarray(observations.predator_counts, dtype=np.int64).copy())
    statistics = np.concatenate(all_statistics)
    if (
        statistics.shape != (REFERENCE_COUNT,)
        or not np.isfinite(statistics).all()
        or (statistics < 0).any()
    ):
        raise ScreeningNumericalError(f"invalid node statistic at node {node_index}")
    return NodeResult(
        node_index,
        statistics,
        neighbours,
        generation_seconds,
        preparation_seconds,
        scoring_seconds,
        training_counts=np.concatenate(training_counts) if diagnostic else None,
        predator_counts=np.concatenate(predator_counts) if diagnostic else None,
    )


def score_node_individual(
    panel: PublicPanel,
    node_index: int,
    *,
    reference_indices: Sequence[int] = range(REFERENCE_COUNT),
    root: int = ROOT_SEED,
) -> FloatArray:
    """Reference implementation used only for the mechanical equivalence check."""
    values = []
    for reference in reference_indices:
        batch = make_reference_batch(panel, node_index, (int(reference),), root=root)
        point_values = [
            _pre_score(batch.observations, panel.map_a, panel.site_a, neighbour)[0]
            for neighbour in calibration.axis_adjacent_indices(node_index)
        ]
        values.append(2.0 * max(point_values) - 2.0 * point_values[0])
    return np.maximum(np.asarray(values, dtype=np.float64), 0.0)


def vectorized_equivalence(
    panel: PublicPanel, *, node_index: int = 0, count: int = 3
) -> dict[str, Any]:
    """Prove batched and one-history calls agree on deterministic observations."""
    if not 1 <= count <= REFERENCE_COUNT:
        raise ValueError("equivalence count must be between one and 99")
    prey = np.zeros((count, len(panel.site_a), 13), dtype=np.int64)
    predator = np.zeros((count, len(panel.site_a), 6), dtype=np.int64)
    history = np.arange(count)[:, None, None]
    site_index = np.arange(len(panel.site_a))
    occasion = np.arange(7)
    prey[:, :, :7] = ((history + site_index[None, :, None] + occasion[None, None, :]) % 3).astype(
        np.int64
    )
    mechanical = likelihood.prepare_observations(
        prey,
        predator,
        panel.observations.site_ids,
        panel.observations.training_mask,
        prey_times=panel.observations.prey_times,
        predator_times=panel.observations.predator_times,
    )
    neighbours = calibration.axis_adjacent_indices(node_index)
    batched_values = np.stack(
        [_pre_score(mechanical, panel.map_a, panel.site_a, neighbour) for neighbour in neighbours],
        axis=1,
    )
    batched = 2.0 * np.maximum(batched_values.max(axis=1) - batched_values[:, 0], 0.0)
    individual = []
    for row in range(count):
        one = likelihood.prepare_observations(
            prey[row : row + 1],
            predator[row : row + 1],
            panel.observations.site_ids,
            panel.observations.training_mask,
            prey_times=panel.observations.prey_times,
            predator_times=panel.observations.predator_times,
        )
        values = [
            _pre_score(one, panel.map_a, panel.site_a, neighbour)[0] for neighbour in neighbours
        ]
        individual.append(2.0 * max(values) - 2.0 * values[0])
    individual_array = np.maximum(np.asarray(individual, dtype=np.float64), 0.0)
    difference = float(np.max(np.abs(batched - individual_array)))
    return {"passed": bool(difference <= 1e-12), "max_abs_difference": difference, "count": count}


def score_open_surfaces(panel: PublicPanel) -> tuple[FloatArray, FloatArray]:
    """Score all 16 fixtures on the complete frozen grid and derive contrasts."""
    surfaces = np.empty((len(panel.observations.prey_counts), GRID_SIZE), dtype=np.float64)
    started = time.perf_counter()
    for history in range(len(surfaces)):
        observed = likelihood.prepare_observations(
            panel.observations.prey_counts[history : history + 1],
            panel.observations.predator_counts[history : history + 1],
            panel.observations.site_ids,
            panel.observations.training_mask,
            prey_times=panel.observations.prey_times,
            predator_times=panel.observations.predator_times,
        )
        for index, node in enumerate(calibration.NUISANCE_GRID):
            hazards = adjusted.normalized_hazards(node.beta, panel.map_a, panel.site_a, node.mu)
            score = likelihood.pre_only_log_likelihood(
                observed, hazards, detection_sd=node.detection_sd, return_site=False
            )
            surfaces[history, index] = float(np.asarray(score).reshape(-1)[0])
    if not np.isfinite(surfaces).all():
        raise ScreeningNumericalError("open panel surface contains a non-finite value")
    del started
    return surfaces, calibration.local_contrasts(surfaces)


def true_panel_nodes(panel: PublicPanel) -> NDArray[np.int64]:
    truths = panel.manifest.get("truths")
    if not isinstance(truths, list) or len(truths) != len(panel.observations.prey_counts):
        raise ValueError("panel manifest does not contain the 16 public truths")
    output = []
    for row in truths:
        candidates = [
            index
            for index, node in enumerate(calibration.NUISANCE_GRID)
            if np.isclose(node.beta, float(row["beta"]), rtol=0.0, atol=1e-14)
            and np.isclose(node.mu, float(row["mean_hazard"]), rtol=0.0, atol=1e-14)
            and np.isclose(node.detection_sd, float(row["detection_sd"]), rtol=0.0, atol=1e-14)
        ]
        if len(candidates) != 1:
            raise ValueError("panel truth is not represented exactly once on the nuisance grid")
        output.append(candidates[0])
    return np.asarray(output, dtype=np.int64)


def screen_outputs(
    panel: PublicPanel,
    reference_contrasts: FloatArray,
    observed_contrasts: FloatArray,
    observed_surface: FloatArray | None = None,
) -> dict[str, Any]:
    """Compute q values, candidates, support diagnostics and all 1,820 unions."""
    reference = np.asarray(reference_contrasts, dtype=np.float64)
    observed = np.asarray(observed_contrasts, dtype=np.float64)
    if observed_surface is None:
        raise ValueError("the observed log-likelihood surface is required for R diagnostics")
    surface = np.asarray(observed_surface, dtype=np.float64)
    if reference.shape != (REFERENCE_COUNT, GRID_SIZE) or observed.shape != (16, GRID_SIZE):
        raise ValueError("screen surfaces do not have the registered dimensions")
    if surface.shape != (16, GRID_SIZE) or not np.isfinite(surface).all():
        raise ValueError("observed log-likelihood surface has an unexpected shape")
    screens = calibration.screen_cases(tuple(str(i) for i in range(16)), observed, reference)
    q_values = np.stack([np.asarray(row.q_values) for row in screens])
    candidate_mask = q_values > calibration.GAMMA
    true_nodes = true_panel_nodes(panel)
    r_values = 2.0 * (surface.max(axis=1, keepdims=True) - surface)
    candidate_counts = candidate_mask.sum(axis=1).astype(np.int64)
    union_rows: list[dict[str, Any]] = []
    for combo in itertools.combinations(range(16), 4):
        nodes = np.flatnonzero(np.any(candidate_mask[list(combo)], axis=0))
        union_rows.append(
            {
                "case_ids": "-".join(str(i) for i in combo),
                "case_count": 4,
                "candidate_count": int(nodes.size),
                "empty": bool(nodes.size == 0),
            }
        )
    r_summary: list[dict[str, Any]] = []
    for row in r_values:
        in_candidates = row[candidate_mask[len(r_summary)]]
        r_summary.append(
            {
                "r_quantiles": {
                    str(q): float(np.quantile(in_candidates, q)) if in_candidates.size else None
                    for q in (0.5, 0.9, 0.95, 0.99, 1.0)
                },
                "r_gt_10": int(np.sum(in_candidates > 10.0)),
                "r_le_10": int(np.sum(row <= 10.0)),
            }
        )
    return {
        "q_values": q_values,
        "candidate_mask": candidate_mask,
        "candidate_counts": candidate_counts,
        "true_nodes": true_nodes,
        "true_retained": candidate_mask[np.arange(16), true_nodes],
        "global_r": r_values,
        "r_summary": r_summary,
        "union_rows": union_rows,
    }


def write_screen_outputs(
    output: Path,
    reference_contrasts: FloatArray,
    observed_surface: FloatArray,
    observed_contrasts: FloatArray,
    panel: PublicPanel,
) -> dict[str, Any]:
    """Persist compact screening tables and human-readable case/union summaries."""
    output.mkdir(parents=True, exist_ok=False)
    summary = screen_outputs(panel, reference_contrasts, observed_contrasts, observed_surface)
    np.savez_compressed(
        output / "screening.npz",
        reference_contrasts=np.asarray(reference_contrasts, dtype=np.float64),
        observed_surface=np.asarray(observed_surface, dtype=np.float64),
        observed_contrasts=np.asarray(observed_contrasts, dtype=np.float64),
        q_values=summary["q_values"],
        candidate_mask=summary["candidate_mask"],
        case_ids=np.arange(16, dtype=np.int64),
        true_nodes=summary["true_nodes"],
        true_retained=summary["true_retained"],
        global_r=summary["global_r"],
    )
    with (output / "case_summary.csv").open("w", newline="") as handle:
        fields = ["case_id", "candidate_count", "true_node", "true_retained", "r_gt_10", "r_le_10"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(summary["r_summary"]):
            writer.writerow(
                {
                    "case_id": index,
                    "candidate_count": int(summary["candidate_counts"][index]),
                    "true_node": int(summary["true_nodes"][index]),
                    "true_retained": bool(summary["true_retained"][index]),
                    "r_gt_10": row["r_gt_10"],
                    "r_le_10": row["r_le_10"],
                }
            )
    with (output / "four_case_unions.csv").open("w", newline="") as handle:
        fields = ["case_ids", "case_count", "candidate_count", "empty"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summary["union_rows"])
    manifest = {
        "reference_count": REFERENCE_COUNT,
        "grid_size": GRID_SIZE,
        "case_count": 16,
        "union_count": len(summary["union_rows"]),
        "candidate_counts": [int(x) for x in summary["candidate_counts"]],
        "true_retained": [bool(x) for x in summary["true_retained"]],
        "r_summary": summary["r_summary"],
    }
    (output / "screening_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def _worker_score_node(arguments: tuple[PublicPanel, int, int, bool]) -> NodeResult:
    panel, node_index, chunk_size, diagnostic = arguments
    return score_node(panel, node_index, chunk_size=chunk_size, diagnostic=diagnostic)


def run_reference_screen(
    panel: PublicPanel,
    *,
    workers: int = 8,
    chunk_size: int = 99,
    diagnostic_nodes: Sequence[int] = (),
    checkpoint_dir: Path | None = None,
) -> tuple[FloatArray, dict[str, Any], dict[int, NodeResult]]:
    """Run the nodewise screen with at most ``workers`` in-flight tasks.

    A numerical gate cancels unscheduled tasks and raises while completed
    results remain available to the caller for preservation.
    """
    if not 1 <= workers <= 8:
        raise ValueError("the public pilot permits one through eight workers")
    diagnostics = frozenset(int(index) for index in diagnostic_nodes)
    if any(index < 0 or index >= GRID_SIZE for index in diagnostics):
        raise ValueError("diagnostic node is outside the nuisance grid")
    reference = np.full((REFERENCE_COUNT, GRID_SIZE), np.nan, dtype=np.float64)
    results: dict[int, NodeResult] = {}
    timing: dict[str, Any] = {
        "generation_seconds": 0.0,
        "preparation_seconds": 0.0,
        "scoring_seconds": 0.0,
        "serialization_seconds": 0.0,
        "completed_nodes": 0,
        "completed_reference_histories": 0,
    }
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=False)
        (checkpoint_dir / "progress.jsonl").touch()
    next_index = 0
    with ProcessPoolExecutor(max_workers=workers) as executor:
        pending: dict[Any, int] = {}
        while next_index < GRID_SIZE and len(pending) < workers:
            future = executor.submit(
                _worker_score_node, (panel, next_index, chunk_size, next_index in diagnostics)
            )
            pending[future] = next_index
            next_index += 1
        while pending:
            done, _ = wait(tuple(pending), return_when=FIRST_COMPLETED)
            for future in done:
                index = pending.pop(future)
                try:
                    result = future.result()
                except Exception as error:
                    for remaining in pending:
                        remaining.cancel()
                    raise ScreeningNumericalError(
                        f"node {index} failed before completion"
                    ) from error
                assignment_started = time.perf_counter()
                reference[:, index] = result.reference_statistics
                assignment_seconds = time.perf_counter() - assignment_started
                serialization_seconds = 0.0
                if checkpoint_dir is not None:
                    serialization_started = time.perf_counter()
                    checkpoint_values: dict[str, Any] = {
                        "node_index": np.uint64(index),
                        "reference_statistics": result.reference_statistics,
                        "neighbour_indices": np.asarray(result.neighbour_indices, dtype=np.int64),
                    }
                    if result.training_counts is not None and result.predator_counts is not None:
                        checkpoint_values["prey_counts"] = result.training_counts
                        checkpoint_values["predator_counts"] = result.predator_counts
                    np.savez_compressed(
                        checkpoint_dir / f"node-{index:04d}.npz",
                        **checkpoint_values,
                    )
                    serialization_seconds = time.perf_counter() - serialization_started
                result = replace(result, serialization_seconds=serialization_seconds)
                results[index] = result
                if checkpoint_dir is not None:
                    with (checkpoint_dir / "progress.jsonl").open("a") as progress:
                        progress.write(
                            json.dumps(
                                {
                                    "node_index": index,
                                    "reference_count": REFERENCE_COUNT,
                                    "generation_seconds": result.generation_seconds,
                                    "preparation_seconds": result.preparation_seconds,
                                    "scoring_seconds": result.scoring_seconds,
                                    "serialization_seconds": result.serialization_seconds,
                                },
                                sort_keys=True,
                            )
                            + "\n"
                        )
                timing["generation_seconds"] += result.generation_seconds
                timing["preparation_seconds"] += result.preparation_seconds
                timing["scoring_seconds"] += result.scoring_seconds
                timing["reference_assignment_seconds"] = (
                    timing.get("reference_assignment_seconds", 0.0) + assignment_seconds
                )
                timing["serialization_seconds"] += serialization_seconds
                timing["completed_nodes"] += 1
                timing["completed_reference_histories"] += REFERENCE_COUNT
                if next_index < GRID_SIZE:
                    future_next = executor.submit(
                        _worker_score_node,
                        (panel, next_index, chunk_size, next_index in diagnostics),
                    )
                    pending[future_next] = next_index
                    next_index += 1
    if not np.isfinite(reference).all():
        raise ScreeningNumericalError("reference screen table is incomplete")
    return reference, timing, results


def fit_diagnostic_references(
    panel: PublicPanel,
    diagnostic_counts: Mapping[int, tuple[IntArray, IntArray]],
    *,
    independent_module: Any,
    progress_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Fit the exactly 792 persisted references and retain every status."""
    rows: list[dict[str, Any]] = []
    if progress_path is not None:
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        progress_path.touch()
    for node_index in sorted(diagnostic_counts):
        prey_counts, predator_counts = diagnostic_counts[node_index]
        if prey_counts.shape[0] != REFERENCE_COUNT:
            raise ValueError("diagnostic node does not contain exactly 99 references")
        truth = calibration.NUISANCE_GRID[node_index]
        for reference_index in range(REFERENCE_COUNT):
            observed = likelihood.prepare_observations(
                prey_counts[reference_index : reference_index + 1],
                predator_counts[reference_index : reference_index + 1],
                panel.observations.site_ids,
                panel.observations.training_mask,
                prey_times=panel.observations.prey_times[:7],
                predator_times=panel.observations.predator_times,
            )
            data = (observed, panel.map_a, panel.site_a)

            def callback(value: Any, *, beta: float, mu: float, detection_sd: float) -> float:
                return _pre_score_data(value, beta=beta, mu=mu, detection_sd=detection_sd)

            fit = fitting.fit_pre_only_nuisance(data, callback)
            true_ll = _pre_score_data(
                data, beta=truth.beta, mu=truth.mu, detection_sd=truth.detection_sd
            )
            fitted_ll = (
                _pre_score_data(data, beta=fit.beta, mu=fit.mu, detection_sd=fit.detection_sd)
                if math.isfinite(fit.raw_logjoint)
                else math.nan
            )
            independent_check_started = time.perf_counter()
            independent_true = float(
                np.asarray(
                    independent_module.independent_pre_log_likelihood(
                        observed,
                        panel.map_a,
                        panel.site_a,
                        beta=truth.beta,
                        mu=truth.mu,
                        detection_sd=truth.detection_sd,
                    )
                ).reshape(-1)[0]
            )
            independent_fitted = (
                float(
                    np.asarray(
                        independent_module.independent_pre_log_likelihood(
                            observed,
                            panel.map_a,
                            panel.site_a,
                            beta=fit.beta,
                            mu=fit.mu,
                            detection_sd=fit.detection_sd,
                        )
                    ).reshape(-1)[0]
                )
                if math.isfinite(fit.raw_logjoint)
                else math.nan
            )
            independent_check_seconds = time.perf_counter() - independent_check_started
            independent_true_finite = math.isfinite(independent_true)
            independent_fitted_finite = math.isfinite(independent_fitted)
            production_error_true = float(true_ll - independent_true)
            production_error_fitted = float(fitted_ll - independent_fitted)
            independent_failure = (
                not independent_true_finite
                or (math.isfinite(fit.raw_logjoint) and not independent_fitted_finite)
                or abs(production_error_true) > 1e-8
                or (independent_fitted_finite and abs(production_error_fitted) > 1e-8)
            )
            gap = float(fitted_ll - true_ll) if math.isfinite(fitted_ll) else math.nan
            numerical_failure = bool(math.isfinite(gap) and gap < -1e-6)
            row = {
                "node_index": node_index,
                "reference_index": reference_index,
                "truth_beta": truth.beta,
                "truth_mu": truth.mu,
                "truth_detection_sd": truth.detection_sd,
                "fitted_beta": fit.beta,
                "fitted_mu": fit.mu,
                "fitted_detection_sd": fit.detection_sd,
                "truth_loglikelihood": true_ll,
                "fitted_loglikelihood": fitted_ll,
                "objective_gap_fitted_minus_truth": gap,
                "fit_status": fit.numerical_status,
                "fit_nfev": fit.nfev,
                "fit_elapsed_seconds": fit.elapsed_seconds,
                "fit_starts": [asdict(start) for start in fit.starts],
                "boundary_flags": list(fit.boundary_flags),
                "fit_warnings": list(fit.warnings),
                "production_error_true": production_error_true,
                "production_error_fitted": production_error_fitted,
                "independent_error_true": production_error_true,
                "independent_error_fitted": production_error_fitted,
                "independent_true_finite": independent_true_finite,
                "independent_fitted_finite": independent_fitted_finite,
                "independent_check_seconds": independent_check_seconds,
                "independent_failure": independent_failure,
                "numerical_failure": numerical_failure,
            }
            rows.append(row)
            if progress_path is not None:
                with progress_path.open("a") as progress:
                    progress.write(json.dumps(jsonable(row), sort_keys=True) + "\n")
            if independent_failure:
                raise ScreeningNumericalError(
                    f"independent score disagreement at node {node_index}, reference "
                    f"{reference_index}: true production={true_ll:.17g}, "
                    f"independent={independent_true:.17g}, fitted production={fitted_ll:.17g}, "
                    f"independent={independent_fitted:.17g}"
                )
            if numerical_failure:
                raise ScreeningNumericalError(
                    f"fitted objective below truth at node {node_index}, reference "
                    f"{reference_index}: fitted={fitted_ll:.17g}, truth={true_ll:.17g}"
                )
    return rows


def _pre_score_data(
    data: tuple[likelihood.PreInvasionObservations, FloatArray, FloatArray],
    *,
    beta: float,
    mu: float,
    detection_sd: float,
) -> float:
    observed, map_a, site_a = data
    return _pre_score_parameters(
        observed,
        map_a,
        site_a,
        beta=beta,
        mu=mu,
        detection_sd=detection_sd,
    )


def jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, tuple | list):
        return [jsonable(v) for v in value]
    return value
