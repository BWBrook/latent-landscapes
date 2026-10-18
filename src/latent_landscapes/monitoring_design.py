"""Prospectively fixed Paper 1 monitoring geometry.

This module owns the new 300-site master panel.  The older ``goal001``
samplers remain unchanged: the access frame here is the set of footprint
centres within two Euclidean grid cells of the fixed road/transect network,
and the 60 centres are selected jointly so that separation is enforced across
all distance strata.

The MILP objective is a seed-derived random priority vector.  It is therefore
reproducible, but it is not a uniform draw from the feasible panels.  The
solver receipt records this fact, the input hashes, solver version/status and
the selected IDs so a selected panel can be frozen as an external receipt.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from itertools import combinations
from math import hypot
from typing import Any

import numpy as np
import scipy  # type: ignore[import-untyped]
from numpy.typing import NDArray
from scipy.optimize import Bounds, LinearConstraint, milp  # type: ignore[import-untyped]
from scipy.sparse import coo_matrix  # type: ignore[import-untyped]

from latent_landscapes.goal001.design import (
    SITE_OFFSETS,
    STRATUM_BOUNDS,
    Cluster,
    EligibleCentre,
    SamplingDesign,
    build_access_network,
    expand_sites,
)
from latent_landscapes.goal001.landscape import Landscape

MASTER_CLUSTERS_PER_STRATUM = 15
HOLDOUT_CLUSTERS_PER_STRATUM = 2
BASELINE_CLUSTERS_PER_STRATUM = 6
MINIMUM_CENTRE_SEPARATION = 8.0
NETWORK_BUFFER_CELLS = 2.0
MASTER_SITE_COUNT = 300
HOLDOUT_SITE_COUNT = 40
BASELINE_SITE_COUNT = 120
TRAINING_SITE_COUNT = 260
DEFAULT_SAMPLING_SEED = 2026101811
DEFAULT_HOLDOUT_SEED = 2026101812
DEFAULT_ARM_SEED = 2026101813


class SamplingDesignError(RuntimeError):
    """Base class for failures that prevent a valid master panel."""

    def __init__(self, message: str, receipt: SolverReceipt | None = None) -> None:
        super().__init__(message)
        self.receipt = receipt


class MapGeometryError(SamplingDesignError):
    """The supplied map is malformed or cannot define an eligible frame."""


class SolverInfeasibleError(SamplingDesignError):
    """The requested exact-count, spacing-constrained panel is infeasible."""


class SolverTimeLimitError(SamplingDesignError):
    """The MILP stopped at a time/iteration limit before proving a panel."""


class SolverUnknownError(SamplingDesignError):
    """The MILP returned an unrecognised or unsuccessful solver status."""


@dataclass(frozen=True, slots=True)
class SolverReceipt:
    """Auditable result of the joint master-panel MILP."""

    status: str
    solver_status: int
    solver_message: str
    scipy_version: str
    method: str
    seed: int
    candidate_count: int
    selected_count: int
    objective_value: float | None
    eligible_input_sha256: str
    network_sha256: str
    selected_cluster_ids: tuple[str, ...]
    selected_centre_ids: tuple[str, ...]
    method_checks: tuple[tuple[str, bool], ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly receipt without exposing mutable state."""

        return {
            "status": self.status,
            "solver_status": self.solver_status,
            "solver_message": self.solver_message,
            "scipy_version": self.scipy_version,
            "method": self.method,
            "seed": self.seed,
            "candidate_count": self.candidate_count,
            "selected_count": self.selected_count,
            "objective_value": self.objective_value,
            "eligible_input_sha256": self.eligible_input_sha256,
            "network_sha256": self.network_sha256,
            "selected_cluster_ids": list(self.selected_cluster_ids),
            "selected_centre_ids": list(self.selected_centre_ids),
            "method_checks": dict(self.method_checks),
        }


@dataclass(frozen=True, slots=True, eq=False)
class MasterMonitoringDesign:
    """Immutable master panel and nested monitoring-arm identities."""

    sampling: SamplingDesign
    baseline_site_ids: tuple[str, ...]
    holdout_site_ids: tuple[str, ...]
    c_site_ids: tuple[str, ...]
    sampling_seed: int
    holdout_seed: int
    arm_seed: int
    solver_receipt: SolverReceipt
    map_seed: int | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MasterMonitoringDesign):
            return NotImplemented
        return (
            np.array_equal(self.sampling.network, other.sampling.network)
            and self.sampling.eligible_centres == other.sampling.eligible_centres
            and self.sampling.clusters == other.sampling.clusters
            and self.sampling.sites == other.sampling.sites
            and self.baseline_site_ids == other.baseline_site_ids
            and self.holdout_site_ids == other.holdout_site_ids
            and self.c_site_ids == other.c_site_ids
            and self.seeds == other.seeds
            and self.solver_receipt == other.solver_receipt
            and self.map_seed == other.map_seed
        )

    __hash__ = None  # type: ignore[assignment]

    @property
    def sampling_design(self) -> SamplingDesign:
        """Compatibility alias used by downstream adapters."""

        return self.sampling

    @property
    def master_site_ids(self) -> tuple[str, ...]:
        return tuple(sorted(site.site_id for site in self.sampling.sites))

    @property
    def arm_a_site_ids(self) -> tuple[str, ...]:
        return self.baseline_site_ids

    @property
    def arm_b_site_ids(self) -> tuple[str, ...]:
        return self.baseline_site_ids

    @property
    def holdout_ids(self) -> tuple[str, ...]:
        """Alias for callers that use the shorter holdout terminology."""

        return self.holdout_site_ids

    @property
    def seeds(self) -> tuple[int, int, int]:
        return self.sampling_seed, self.holdout_seed, self.arm_seed

    def availability_masks(self) -> dict[str, tuple[bool, ...]]:
        """Return A/B/C availability in one canonical sorted-site order."""

        ordered = self.master_site_ids
        baseline = set(self.baseline_site_ids)
        c_sites = set(self.c_site_ids)
        return {
            "A": tuple(site_id in baseline for site_id in ordered),
            "B": tuple(site_id in baseline for site_id in ordered),
            "C": tuple(site_id in c_sites for site_id in ordered),
        }

    @property
    def masks(self) -> dict[str, tuple[bool, ...]]:
        return self.availability_masks()

    def availability_by_site(self) -> dict[str, dict[str, bool]]:
        """Return A/B/C availability keyed by each sorted physical site ID."""

        masks = self.availability_masks()
        return {
            site_id: {arm: masks[arm][index] for arm in ("A", "B", "C")}
            for index, site_id in enumerate(self.master_site_ids)
        }

    @property
    def mask_mapping(self) -> dict[str, dict[str, bool]]:
        return self.availability_by_site()


def find_eligible_centres(
    landscape: Landscape,
    network: NDArray[np.bool] | None = None,
    *,
    network_buffer_cells: float = NETWORK_BUFFER_CELLS,
) -> tuple[EligibleCentre, ...]:
    """Build the uniform eligible-centre frame within a Euclidean network buffer.

    Every centre is tested against the complete five-cell footprint.  The
    distance is measured between cell centres and the fixed network cell set;
    for the axis-aligned road/transect lines this is the usual perpendicular
    distance to the nearest line, up to the cell-centre discretisation.
    """

    _validate_landscape(landscape)
    if network is None:
        network = build_access_network(landscape.shape)
    if network.shape != landscape.shape:
        raise MapGeometryError("network and landscape shapes differ")
    if network.dtype != np.bool_:
        network = np.asarray(network, dtype=np.bool)
    network_cells = np.argwhere(network)
    if len(network_cells) == 0:
        raise MapGeometryError("fixed access network is empty")
    source_cells = np.argwhere(landscape.source_zone != "")
    if len(source_cells) == 0:
        raise MapGeometryError("landscape has no source cells")
    if network_buffer_cells < 0 or not np.isfinite(network_buffer_cells):
        raise ValueError("network_buffer_cells must be a finite non-negative number")

    eligible: list[EligibleCentre] = []
    rows, cols = landscape.shape
    for row in range(2, rows - 2):
        for col in range(2, cols - 2):
            centre = np.asarray((row, col), dtype=np.float64)
            network_distance = float(np.linalg.norm(network_cells - centre, axis=1).min())
            if network_distance > network_buffer_cells + 1e-12:
                continue
            sites = tuple((row + dr, col + dc) for dr, dc in SITE_OFFSETS)
            if not all(
                landscape.passable[site_row, site_col]
                and landscape.source_reachable[site_row, site_col]
                for site_row, site_col in sites
            ):
                continue
            source_distance = float(np.linalg.norm(source_cells - centre, axis=1).min())
            eligible.append(
                EligibleCentre(
                    row=row,
                    col=col,
                    stratum_index=_stratum_index(source_distance),
                    euclidean_source_distance=source_distance,
                )
            )
    return tuple(sorted(eligible, key=lambda value: (value.row, value.col)))


def select_master_clusters(
    eligible: Sequence[EligibleCentre],
    seed: int,
    *,
    network: NDArray[np.bool] | None = None,
    solver_time_limit: float | None = None,
) -> tuple[tuple[Cluster, ...], SolverReceipt]:
    """Select 15 separated centres per stratum with one joint MILP.

    The objective maximises independent random priorities generated from
    ``seed``.  This is deliberately documented as a reproducible randomized
    feasible-panel selector, not a uniform sampler over feasible panels.
    """

    ordered = tuple(sorted(eligible, key=lambda value: (value.row, value.col)))
    if not ordered:
        receipt = _failure_receipt(
            "solver_infeasible",
            -1,
            "infeasible: eligible-centre frame is empty",
            seed=seed,
            candidate_count=0,
            selected_count=0,
            eligible_hash=_hash_eligible(ordered),
            network_hash=_hash_array(network),
        )
        raise SolverInfeasibleError(receipt.solver_message, receipt)
    _validate_eligible(ordered)
    candidate_count = len(ordered)
    eligible_hash = _hash_eligible(ordered)
    network_hash = _hash_array(network) if network is not None else ""
    rng = np.random.default_rng(seed)
    priorities = rng.random(candidate_count)
    c = -priorities

    row_indices: list[int] = []
    col_indices: list[int] = []
    data: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    row_number = 0
    for stratum_index in range(len(STRATUM_BOUNDS)):
        indices = [
            index
            for index, candidate in enumerate(ordered)
            if candidate.stratum_index == stratum_index
        ]
        if len(indices) < MASTER_CLUSTERS_PER_STRATUM:
            receipt = _failure_receipt(
                "solver_infeasible",
                -1,
                "fewer eligible centres than the requested stratum count",
                seed=seed,
                candidate_count=candidate_count,
                selected_count=0,
                eligible_hash=eligible_hash,
                network_hash=network_hash,
            )
            raise SolverInfeasibleError(receipt.solver_message, receipt)
        for index in indices:
            row_indices.append(row_number)
            col_indices.append(index)
            data.append(1.0)
        lower.append(float(MASTER_CLUSTERS_PER_STRATUM))
        upper.append(float(MASTER_CLUSTERS_PER_STRATUM))
        row_number += 1

    for left, right in combinations(range(candidate_count), 2):
        if hypot(ordered[left].row - ordered[right].row, ordered[left].col - ordered[right].col) < (
            MINIMUM_CENTRE_SEPARATION - 1e-12
        ):
            row_indices.extend((row_number, row_number))
            col_indices.extend((left, right))
            data.extend((1.0, 1.0))
            lower.append(-np.inf)
            upper.append(1.0)
            row_number += 1

    constraints = LinearConstraint(
        coo_matrix((data, (row_indices, col_indices)), shape=(row_number, candidate_count)).tocsr(),
        np.asarray(lower, dtype=np.float64),
        np.asarray(upper, dtype=np.float64),
    )
    options: dict[str, float] = {}
    if solver_time_limit is not None:
        if solver_time_limit <= 0 or not np.isfinite(solver_time_limit):
            raise ValueError("solver_time_limit must be positive and finite")
        options["time_limit"] = float(solver_time_limit)
    result = milp(
        c=c,
        integrality=np.ones(candidate_count, dtype=np.int8),
        bounds=Bounds(0.0, 1.0),
        constraints=constraints,
        options=options,
    )
    status_name = {0: "selected_verified", 1: "solver_time_limit", 2: "solver_infeasible"}.get(
        int(result.status), "solver_unknown"
    )
    chosen = () if result.x is None else tuple(
        int(index) for index in np.flatnonzero(result.x > 0.5)
    )
    selected_ids = tuple(_centre_id(ordered[index]) for index in chosen)
    receipt = _failure_or_success_receipt(
        status_name,
        int(result.status),
        str(result.message),
        seed=seed,
        candidate_count=candidate_count,
        selected_count=len(chosen),
        objective_value=None if result.fun is None else float(-result.fun),
        eligible_hash=eligible_hash,
        network_hash=network_hash,
        selected_centre_ids=selected_ids,
    )
    if status_name != "selected_verified":
        if status_name == "solver_infeasible":
            raise SolverInfeasibleError(receipt.solver_message, receipt)
        if status_name == "solver_time_limit":
            raise SolverTimeLimitError(receipt.solver_message, receipt)
        raise SolverUnknownError(receipt.solver_message, receipt)
    if len(chosen) != MASTER_CLUSTERS_PER_STRATUM * len(STRATUM_BOUNDS):
        raise SolverUnknownError("solver returned a non-exact selected count", receipt)
    clusters = tuple(
        Cluster(
            cluster_id=f"master_{number:03d}",
            center_row=ordered[index].row,
            center_col=ordered[index].col,
            stratum_index=ordered[index].stratum_index,
            euclidean_source_distance=ordered[index].euclidean_source_distance,
        )
        for number, index in enumerate(chosen, start=1)
    )
    checks = {
        "joint_milp": True,
        "seeded_random_priority_objective": True,
        **_cluster_checks(clusters),
    }
    if not all(checks.values()):
        raise SolverUnknownError("solver selected centres that failed geometry checks", receipt)
    final_receipt = replace(
        receipt,
        selected_count=len(clusters),
        selected_cluster_ids=tuple(cluster.cluster_id for cluster in clusters),
        method_checks=tuple(sorted(checks.items())),
    )
    return clusters, final_receipt


def build_master_monitoring_design(
    landscape: Landscape,
    *,
    sampling_seed: int = DEFAULT_SAMPLING_SEED,
    holdout_seed: int = DEFAULT_HOLDOUT_SEED,
    arm_seed: int = DEFAULT_ARM_SEED,
    map_seed: int | None = None,
    solver_time_limit: float | None = None,
) -> MasterMonitoringDesign:
    """Build the 300-site master panel and nested A/B/C masks."""

    network = build_access_network(landscape.shape)
    eligible = find_eligible_centres(landscape, network)
    clusters, receipt = select_master_clusters(
        eligible,
        sampling_seed,
        network=network,
        solver_time_limit=solver_time_limit,
    )
    holdout_ids = _choose_cluster_ids(clusters, holdout_seed, HOLDOUT_CLUSTERS_PER_STRATUM)
    labelled = tuple(
        replace(cluster, split="holdout" if cluster.cluster_id in holdout_ids else "training")
        for cluster in clusters
    )
    training = tuple(cluster for cluster in labelled if cluster.split == "training")
    baseline_ids = _choose_cluster_ids(training, arm_seed, BASELINE_CLUSTERS_PER_STRATUM)
    sites = expand_sites(labelled)
    network.setflags(write=False)
    sampling = SamplingDesign(network, eligible, labelled, sites)
    result = MasterMonitoringDesign(
        sampling=sampling,
        baseline_site_ids=tuple(
            sorted(site.site_id for site in sites if site.cluster_id in baseline_ids)
        ),
        holdout_site_ids=tuple(
            sorted(site.site_id for site in sites if site.cluster_id in holdout_ids)
        ),
        c_site_ids=tuple(sorted(site.site_id for site in sites if site.split == "training")),
        sampling_seed=int(sampling_seed),
        holdout_seed=int(holdout_seed),
        arm_seed=int(arm_seed),
        solver_receipt=receipt,
        map_seed=map_seed,
    )
    checks = monitoring_checks(result, landscape)
    if not all(checks.values()):
        failed = ", ".join(name for name, passed in checks.items() if not passed)
        raise SolverUnknownError(f"selected panel failed monitoring checks: {failed}", receipt)
    return result


def build_design(
    landscape: Landscape,
    sampling_seed: int = DEFAULT_SAMPLING_SEED,
    holdout_seed: int = DEFAULT_HOLDOUT_SEED,
    arm_seed: int = DEFAULT_ARM_SEED,
) -> MasterMonitoringDesign:
    """Short alias for callers that use the repository's existing design API."""

    return build_master_monitoring_design(
        landscape,
        sampling_seed=sampling_seed,
        holdout_seed=holdout_seed,
        arm_seed=arm_seed,
    )


def monitoring_checks(
    design: MasterMonitoringDesign, landscape: Landscape
) -> dict[str, bool]:
    """Return acceptance checks for panel identity, geometry and nesting."""

    sites = design.sampling.sites
    clusters = design.sampling.clusters
    checks: dict[str, bool] = {}
    checks["master_site_count"] = len(sites) == MASTER_SITE_COUNT
    checks["master_unique_physical_sites"] = (
        len({(site.row, site.col) for site in sites}) == len(sites)
    )
    checks["equal_five_site_clusters"] = all(
        sum(site.cluster_id == cluster.cluster_id for site in sites) == len(SITE_OFFSETS)
        for cluster in clusters
    )
    checks["passable_source_reachable"] = all(
        landscape.passable[site.row, site.col] and landscape.source_reachable[site.row, site.col]
        for site in sites
    )
    checks.update(_cluster_checks(clusters))
    checks["holdout_site_count"] = len(design.holdout_site_ids) == HOLDOUT_SITE_COUNT
    checks["baseline_site_count"] = len(design.baseline_site_ids) == BASELINE_SITE_COUNT
    checks["c_site_count"] = len(design.c_site_ids) == TRAINING_SITE_COUNT
    checks["baseline_subset_of_c"] = set(design.baseline_site_ids) <= set(design.c_site_ids)
    checks["holdout_disjoint_from_c"] = set(design.holdout_site_ids).isdisjoint(design.c_site_ids)
    checks["holdout_disjoint_from_baseline"] = set(design.holdout_site_ids).isdisjoint(
        design.baseline_site_ids
    )
    checks["split_isolation"] = all(
        len({site.split for site in sites if site.cluster_id == cluster.cluster_id}) == 1
        for cluster in clusters
    )
    checks["nested_a_b_equal"] = design.arm_a_site_ids == design.arm_b_site_ids
    checks["sorted_ids"] = (
        tuple(sorted(design.baseline_site_ids)) == design.baseline_site_ids
        and tuple(sorted(design.holdout_site_ids)) == design.holdout_site_ids
        and tuple(sorted(design.c_site_ids)) == design.c_site_ids
    )
    return {name: bool(value) for name, value in checks.items()}


def sampling_checks(
    design: MasterMonitoringDesign, landscape: Landscape
) -> dict[str, bool]:
    """Alias retaining the terminology used by older design tests."""

    return monitoring_checks(design, landscape)


def availability_masks(design: MasterMonitoringDesign) -> Mapping[str, tuple[bool, ...]]:
    """Module-level access to canonical A/B/C masks."""

    return design.availability_masks()


def mask_mapping(design: MasterMonitoringDesign) -> Mapping[str, dict[str, bool]]:
    """Module-level access to site-keyed A/B/C availability."""

    return design.availability_by_site()


def _choose_cluster_ids(
    clusters: Sequence[Cluster], seed: int, per_stratum: int
) -> set[str]:
    rng = np.random.default_rng(seed)
    chosen: set[str] = set()
    for stratum_index in range(len(STRATUM_BOUNDS)):
        candidates = sorted(
            (cluster for cluster in clusters if cluster.stratum_index == stratum_index),
            key=lambda value: value.cluster_id,
        )
        if len(candidates) < per_stratum:
            raise SolverInfeasibleError(f"infeasible cluster allocation in stratum {stratum_index}")
        priorities = rng.random(len(candidates))
        order = np.argsort(-priorities, kind="mergesort")[:per_stratum]
        chosen.update(candidates[int(index)].cluster_id for index in order)
    return chosen


def _validate_landscape(landscape: Landscape) -> None:
    if len(landscape.shape) != 2 or min(landscape.shape) < 5:
        raise MapGeometryError("landscape must be a two-dimensional grid with a five-site margin")
    expected = landscape.shape
    for name in ("passable", "source_reachable", "source_zone"):
        if getattr(landscape, name).shape != expected:
            raise MapGeometryError(f"landscape field {name} has the wrong shape")


def _validate_eligible(eligible: Sequence[EligibleCentre]) -> None:
    if not eligible:
        raise SolverInfeasibleError("infeasible: eligible-centre frame is empty")
    identities = {(candidate.row, candidate.col) for candidate in eligible}
    if len(identities) != len(eligible):
        raise MapGeometryError("eligible-centre frame contains duplicate physical centres")
    if any(candidate.stratum_index not in range(len(STRATUM_BOUNDS)) for candidate in eligible):
        raise MapGeometryError("eligible-centre frame contains an invalid distance stratum")


def _cluster_checks(clusters: Sequence[Cluster]) -> dict[str, bool]:
    return {
        "cluster_count": len(clusters) == MASTER_CLUSTERS_PER_STRATUM * len(STRATUM_BOUNDS),
        "equal_stratum_counts": all(
            sum(cluster.stratum_index == stratum for cluster in clusters)
            == MASTER_CLUSTERS_PER_STRATUM
            for stratum in range(len(STRATUM_BOUNDS))
        ),
        "centre_separation_all_clusters": all(
            hypot(left.center_row - right.center_row, left.center_col - right.center_col)
            >= MINIMUM_CENTRE_SEPARATION
            for left, right in combinations(clusters, 2)
        ),
        "unique_centres": len({(cluster.center_row, cluster.center_col) for cluster in clusters})
        == len(clusters),
    }


def _stratum_index(distance: float) -> int:
    for index, (lower, upper) in enumerate(STRATUM_BOUNDS):
        if lower <= distance < upper:
            return index
    raise MapGeometryError(f"source distance outside strata: {distance}")


def _centre_id(candidate: EligibleCentre) -> str:
    return f"cell_{candidate.row:02d}_{candidate.col:02d}"


def _hash_eligible(eligible: Sequence[EligibleCentre]) -> str:
    import hashlib

    payload = "|".join(
        f"{item.row},{item.col},{item.stratum_index},{item.euclidean_source_distance:.17g}"
        for item in eligible
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _hash_array(array: NDArray[np.bool] | None) -> str:
    import hashlib

    if array is None:
        return ""
    value = np.ascontiguousarray(array, dtype=np.bool)
    return hashlib.sha256(value.tobytes()).hexdigest()


def _failure_receipt(
    status: str,
    solver_status: int,
    message: str,
    *,
    seed: int,
    candidate_count: int,
    selected_count: int,
    eligible_hash: str,
    network_hash: str,
) -> SolverReceipt:
    return _failure_or_success_receipt(
        status,
        solver_status,
        message,
        seed=seed,
        candidate_count=candidate_count,
        selected_count=selected_count,
        objective_value=None,
        eligible_hash=eligible_hash,
        network_hash=network_hash,
    )


def _failure_or_success_receipt(
    status: str,
    solver_status: int,
    message: str,
    *,
    seed: int,
    candidate_count: int,
    selected_count: int,
    objective_value: float | None,
    eligible_hash: str,
    network_hash: str,
    selected_centre_ids: tuple[str, ...] = (),
) -> SolverReceipt:
    return SolverReceipt(
        status=status,
        solver_status=solver_status,
        solver_message=message,
        scipy_version=scipy.__version__,
        method=(
            "joint scipy.optimize.milp; maximize seeded random priorities; exact 15 per "
            "stratum; pairwise centre separation >= 8"
        ),
        seed=int(seed),
        candidate_count=candidate_count,
        selected_count=selected_count,
        objective_value=objective_value,
        eligible_input_sha256=eligible_hash,
        network_sha256=network_hash,
        selected_cluster_ids=(),
        selected_centre_ids=selected_centre_ids,
        method_checks=(),
    )


__all__ = [
    "BASELINE_SITE_COUNT",
    "DEFAULT_ARM_SEED",
    "DEFAULT_HOLDOUT_SEED",
    "DEFAULT_SAMPLING_SEED",
    "HOLDOUT_SITE_COUNT",
    "MASTER_SITE_COUNT",
    "MINIMUM_CENTRE_SEPARATION",
    "NETWORK_BUFFER_CELLS",
    "MapGeometryError",
    "MasterMonitoringDesign",
    "SamplingDesignError",
    "SolverInfeasibleError",
    "SolverReceipt",
    "SolverTimeLimitError",
    "SolverUnknownError",
    "availability_masks",
    "build_design",
    "build_master_monitoring_design",
    "find_eligible_centres",
    "mask_mapping",
    "monitoring_checks",
    "sampling_checks",
    "select_master_clusters",
]
