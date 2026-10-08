"""Frozen 765-node capstone screen, random addresses and casewise decisions.

This adapter preserves the older pilot's generic rank arithmetic while keeping
its 3,645-node stencil and random streams out of the capstone.  It creates no
campaign on import.  Reference materialization is a later, checkpointed task.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import adjusted_background_likelihood as adjusted
from latent_landscapes import capstone_public as public
from latent_landscapes import preinvasion_calibration as ranks
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.preinvasion_effect_gate import EffectFitBatch

FloatArray = NDArray[np.float64]
ROOT_SEED = 2026100404
NAMESPACE = 59
BETA_GRID = tuple(float(x) for x in np.linspace(-2.0, 2.0, 17))
MU_GRID = ranks.MU_GRID
DETECTION_SD_GRID = ranks.DETECTION_SD_GRID
GRID_SHAPE = (17, 9, 5)
GRID_SIZE = math.prod(GRID_SHAPE)
NUISANCE_GRID = tuple(
    ranks.NuisanceNode(beta, mu, sd)
    for beta in BETA_GRID
    for mu in MU_GRID
    for sd in DETECTION_SD_GRID
)
SCREEN_REFERENCE_COUNT = 99
EFFECT_REFERENCE_COUNT = 999
DOMAINS = {"screen": 5, "effect": 6}
STAGES = {"spread": 1, "prey_loss": 2, "predator_visits": 3, "site_detection": 4, "prey_visits": 5}
SCREEN_STAGES = ("prey_loss", "site_detection", "prey_visits")
ReferenceKind = Literal["screen", "effect"]


class CalibrationPendingError(RuntimeError):
    """Computation is pending; no final decisions or partial ranks are issued."""


def grid_index(beta_index: int, mu_index: int, sd_index: int) -> int:
    coordinates = (beta_index, mu_index, sd_index)
    if any(
        type(x) is not int or not 0 <= x < size
        for x, size in zip(coordinates, GRID_SHAPE, strict=True)
    ):
        raise IndexError("invalid capstone grid coordinate")
    return beta_index * 45 + mu_index * 5 + sd_index


def grid_coordinates(index: int) -> tuple[int, int, int]:
    if type(index) is not int or not 0 <= index < GRID_SIZE:
        raise IndexError("invalid capstone node index")
    return index // 45, index % 45 // 5, index % 5


def axis_adjacent_indices(index: int) -> tuple[int, ...]:
    coordinates = grid_coordinates(index)
    result = [index]
    for axis, size in enumerate(GRID_SHAPE):
        for step in (-1, 1):
            neighbour = list(coordinates)
            neighbour[axis] += step
            if 0 <= neighbour[axis] < size:
                result.append(grid_index(*neighbour))
    return tuple(result)


def local_contrasts(pre_loglikelihoods: Any) -> FloatArray:
    """Centre-plus-immediate-axis stencil; do not propagate neighbouring maxima."""
    values = np.asarray(pre_loglikelihoods, dtype=np.float64)
    if values.ndim < 1 or values.shape[-1] != GRID_SIZE or not np.isfinite(values).all():
        raise ValueError("finite surfaces must end in 765 nodes")
    result = np.empty_like(values)
    for index in range(GRID_SIZE):
        neighbours = axis_adjacent_indices(index)
        result[..., index] = 2 * np.maximum(
            values[..., neighbours].max(axis=-1) - values[..., index], 0.0
        )
    return result


def stage_seed(
    kind: ReferenceKind, node: int, reference: int, stage: str, *, root: int = ROOT_SEED
) -> int:
    grid_coordinates(node)
    if kind not in DOMAINS or type(root) is not int or root < 0:
        raise ValueError("invalid reference kind or root")
    count = SCREEN_REFERENCE_COUNT if kind == "screen" else EFFECT_REFERENCE_COUNT
    names = SCREEN_STAGES if kind == "screen" else tuple(STAGES)
    if type(reference) is not int or not 0 <= reference < count or stage not in names:
        raise ValueError("invalid reference or stage address")
    address = [root, NAMESPACE, DOMAINS[kind], node, reference, STAGES[stage]]
    return int(np.random.SeedSequence(address).generate_state(1, dtype=np.uint64)[0])


def reference_seeds(
    kind: ReferenceKind, node: int, reference: int, *, root: int = ROOT_SEED
) -> dict[str, Any]:
    names = SCREEN_STAGES if kind == "screen" else tuple(STAGES)
    return {
        "root": root,
        "namespace": NAMESPACE,
        "domain": DOMAINS[kind],
        "node": node,
        "reference": reference,
        "streams": {name: stage_seed(kind, node, reference, name, root=root) for name in names},
    }


def address_contract(*, root: int = ROOT_SEED) -> dict[str, Any]:
    """Return the complete derivation contract; no random histories are drawn."""
    nodes = [{"index": index, **asdict(node)} for index, node in enumerate(NUISANCE_GRID)]
    node_bytes = json.dumps(nodes, sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema": "goal059-capstone-address-v1",
        "root": root,
        "namespace": NAMESPACE,
        "numpy_version": np.__version__,
        "seed_algorithm": "SeedSequence(address).generate_state(1,dtype=uint64)[0]",
        "generator": "numpy.random.default_rng/PCG64",
        "address_order": ["root", "namespace", "domain", "node", "reference", "stage"],
        "domains": DOMAINS,
        "stages": STAGES,
        "screen_stages": SCREEN_STAGES,
        "screen_references": SCREEN_REFERENCE_COUNT,
        "effect_references": EFFECT_REFERENCE_COUNT,
        "node_count": GRID_SIZE,
        "nodes": nodes,
        "nodes_sha256": hashlib.sha256(node_bytes).hexdigest(),
        "screen_histories": GRID_SIZE * SCREEN_REFERENCE_COUNT,
        "maximum_effect_histories": GRID_SIZE * EFFECT_REFERENCE_COUNT,
        "screen_seed_count": GRID_SIZE * SCREEN_REFERENCE_COUNT * 3,
        "effect_seed_count": GRID_SIZE * EFFECT_REFERENCE_COUNT * 5,
        "rule": "complete retained union; lazy materialization at fixed addresses",
    }


def pre_score(
    observations: likelihood.PreInvasionObservations,
    map_a: FloatArray,
    site_a: FloatArray,
    node_index: int,
) -> FloatArray:
    grid_coordinates(node_index)
    node = NUISANCE_GRID[node_index]
    hazard = adjusted.normalized_hazards(node.beta, map_a, site_a, node.mu)
    result = np.asarray(
        likelihood.pre_only_log_likelihood(
            observations, hazard, detection_sd=node.detection_sd, return_site=False
        ),
        dtype=np.float64,
    ).reshape(-1)
    if not np.isfinite(result).all():
        raise ValueError("nonfinite pre-invasion likelihood")
    return result


def local_contrast_at_node(
    observations: likelihood.PreInvasionObservations,
    map_a: FloatArray,
    site_a: FloatArray,
    node_index: int,
) -> FloatArray:
    scores = np.stack(
        [
            pre_score(observations, map_a, site_a, neighbour)
            for neighbour in axis_adjacent_indices(node_index)
        ],
        axis=-1,
    )
    return 2 * np.maximum(0.0, scores.max(axis=-1) - scores[..., 0])


def generate_screen_reference(
    map_a: FloatArray, site_a: FloatArray, node_index: int, reference: int, *, root: int = ROOT_SEED
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Pre-only marginal with one persistent detection draw and loss threshold/site."""
    seeds = reference_seeds("screen", node_index, reference, root=root)["streams"]
    node = NUISANCE_GRID[node_index]
    n = len(site_a)
    hazards = adjusted.normalized_hazards(node.beta, map_a, site_a, node.mu)
    loss = -60.0 + np.random.default_rng(seeds["prey_loss"]).exponential(size=n) / hazards
    if node.detection_sd == 0:
        detection = np.full(n, 0.65)
    else:
        concentration = 0.65 * 0.35 / node.detection_sd**2 - 1
        detection = np.random.default_rng(seeds["site_detection"]).beta(
            0.65 * concentration, 0.35 * concentration, size=n
        )
    visits = np.random.default_rng(seeds["prey_visits"]).random((n, 7, 2))
    alive = loss[:, None] > np.arange(-60, 1, 10)[None, :]
    prey = np.zeros((n, 13), dtype=np.int64)
    prey[:, :7] = (visits < detection[:, None, None]).sum(axis=2) * alive
    return prey, np.zeros((n, 6), dtype=np.int64)


def generate_effect_reference(
    inputs: public.PublicInputs, node_index: int, reference: int, *, root: int = ROOT_SEED
) -> tuple[dict[str, Any], dict[str, Any]]:
    seeds = reference_seeds("effect", node_index, reference, root=root)
    node = NUISANCE_GRID[node_index]
    truth = public.GeneralTruth(
        index=reference,
        beta=node.beta,
        mean_hazard=node.mu,
        detection_sd=node.detection_sd,
        effect=1.0,
    )
    return public.generate_exact_history(inputs.fixed, inputs.setup, truth, seeds)


def screen_cases(
    case_ids: Sequence[str], observed_contrasts: Any, reference_contrasts: Any | None
) -> tuple[ranks.ScreenResult, ...]:
    ids = tuple(str(value) for value in case_ids)
    if not ids or any(not value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("unique nonempty case identifiers required")
    observed = np.asarray(observed_contrasts, dtype=np.float64)
    if observed.shape != (len(ids), GRID_SIZE):
        raise ValueError("observed contrasts must have one 765-node row per case")
    reference = (
        None if reference_contrasts is None else np.asarray(reference_contrasts, dtype=np.float64)
    )
    if (
        reference is None
        or reference.shape != (99, GRID_SIZE)
        or (not np.isfinite(reference).all() or (reference < -ranks.TIE_ATOL).any())
    ):
        return tuple(
            ranks.ScreenResult(
                case,
                "missing_screen_table",
                (),
                None,
                "shared screen table absent, incomplete or invalid",
            )
            for case in ids
        )
    output = []
    for case, row in zip(ids, observed, strict=True):
        if not np.isfinite(row).all() or (row < -ranks.TIE_ATOL).any():
            output.append(
                ranks.ScreenResult(case, "no_fit", (), None, "nonfinite or invalid observed screen")
            )
            continue
        tolerance = ranks.TIE_ATOL + ranks.TIE_RTOL * np.maximum(1.0, np.abs(row))
        q = (1 + np.sum(reference >= row[None, :] - tolerance[None, :], axis=0)) / 100
        q.setflags(write=False)
        candidates = tuple(int(index) for index in np.flatnonzero(q > ranks.GAMMA))
        status: ranks.ScreenStatus = "ready" if candidates else "empty"
        output.append(
            ranks.ScreenResult(
                case, status, candidates, q, None if candidates else "empty nuisance set"
            )
        )
    return tuple(output)


def required_effect_nodes(screens: Sequence[ranks.ScreenResult]) -> tuple[int, ...]:
    records = tuple(screens)
    if not records or len({s.case_id for s in records}) != len(records):
        raise ValueError("unique nonempty case records required")
    for screen in records:
        if not screen.case_id or len(set(screen.candidate_indices)) != len(
            screen.candidate_indices
        ):
            raise ValueError("empty case id or duplicate candidate")
        for index in screen.candidate_indices:
            grid_coordinates(index)
    return ranks.required_effect_nodes(records, max_candidates=GRID_SIZE)


def combine_effect_tests(
    screens: Sequence[ranks.ScreenResult],
    observed_fits: EffectFitBatch,
    reference_fits: Mapping[int, EffectFitBatch],
    *,
    computation_complete: bool,
) -> ranks.CasewiseCalibration:
    """Require terminal computation; invalid complete tables cause scoped abstention.

    The caller may mark computation complete only after scheduled work has
    finished or a numerical failure is final. Scheduler/resource interruption
    must leave it false, preserving pending work at the same random addresses.
    """
    records = tuple(screens)
    needed = required_effect_nodes(records)
    if not computation_complete:
        raise CalibrationPendingError("reference computation remains pending")
    return ranks.combine_casewise_effect_tests(
        records,
        observed_fits.statistics().tolist(),
        {index: reference_fits[index].statistics() for index in needed if index in reference_fits},
        max_candidates=GRID_SIZE,
    )
