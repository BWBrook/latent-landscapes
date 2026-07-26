"""Fixed access network and clustered sampling design for Goal 001."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from math import hypot

import numpy as np
from numpy.typing import NDArray

from .landscape import Landscape

MASTER_SEED = 20260716
ROAD_COLUMNS = (6, 20, 34, 48, 62, 76)
TRANSECT_ROWS = (5, 17, 29, 41, 53, 65)
SITE_OFFSETS = ((0, 0), (-2, 0), (2, 0), (0, -2), (0, 2))
STRATUM_BOUNDS = ((0.0, 21.0), (21.0, 42.0), (42.0, 63.0), (63.0, float("inf")))
STRATUM_LABELS = ("[0,21)", "[21,42)", "[42,63)", "[63,infinity)")
CLUSTERS_PER_STRATUM = 8
HOLDOUT_PER_STRATUM = 2
MINIMUM_CENTRE_SEPARATION = 8.0


@dataclass(frozen=True, slots=True)
class EligibleCentre:
    row: int
    col: int
    stratum_index: int
    euclidean_source_distance: float


@dataclass(frozen=True, slots=True)
class Cluster:
    cluster_id: str
    center_row: int
    center_col: int
    stratum_index: int
    euclidean_source_distance: float
    split: str = "training"

    @property
    def stratum(self) -> str:
        return STRATUM_LABELS[self.stratum_index]


@dataclass(frozen=True, slots=True)
class DesignSite:
    cluster_id: str
    split: str
    stratum_index: int
    center_row: int
    center_col: int
    euclidean_source_distance: float
    site_id: str
    site_offset_index: int
    offset_row: int
    offset_col: int
    row: int
    col: int

    @property
    def stratum(self) -> str:
        return STRATUM_LABELS[self.stratum_index]


@dataclass(frozen=True, slots=True)
class SamplingDesign:
    network: NDArray[np.bool]
    eligible_centres: tuple[EligibleCentre, ...]
    clusters: tuple[Cluster, ...]
    sites: tuple[DesignSite, ...]


def spawn_generators(
    seed: int = MASTER_SEED,
) -> tuple[np.random.Generator, np.random.Generator, np.random.Generator]:
    children = np.random.SeedSequence(seed).spawn(3)
    generators = tuple(np.random.Generator(np.random.PCG64(child)) for child in children)
    return generators[0], generators[1], generators[2]


def build_access_network(shape: tuple[int, int]) -> NDArray[np.bool]:
    rows, cols = shape
    network = np.zeros(shape, dtype=np.bool)
    for col in ROAD_COLUMNS:
        if col < cols:
            network[:, col] = True
    for row in TRANSECT_ROWS:
        if row < rows:
            network[row, :] = True
    return network


def find_eligible_centres(
    landscape: Landscape,
    network: NDArray[np.bool],
) -> tuple[EligibleCentre, ...]:
    source_cells = np.argwhere(landscape.source_zone != "")
    eligible: list[EligibleCentre] = []
    for row in range(2, landscape.rows - 2):
        for col in range(2, landscape.cols - 2):
            if not network[row, col]:
                continue
            sites = tuple(
                (row + delta_row, col + delta_col) for delta_row, delta_col in SITE_OFFSETS
            )
            if not all(
                landscape.passable[site_row, site_col]
                and landscape.source_reachable[site_row, site_col]
                for site_row, site_col in sites
            ):
                continue
            deltas = source_cells - np.asarray((row, col))
            distance = float(np.sqrt(np.square(deltas).sum(axis=1)).min())
            eligible.append(
                EligibleCentre(
                    row=row,
                    col=col,
                    stratum_index=_stratum_index(distance),
                    euclidean_source_distance=distance,
                )
            )
    return tuple(eligible)


def select_clusters(
    eligible: Sequence[EligibleCentre], rng: np.random.Generator
) -> tuple[Cluster, ...]:
    selected: list[EligibleCentre] = []
    for stratum_index in range(len(STRATUM_BOUNDS)):
        candidates = sorted(
            (candidate for candidate in eligible if candidate.stratum_index == stratum_index),
            key=lambda candidate: (candidate.row, candidate.col),
        )
        for candidate_index in rng.permutation(len(candidates)):
            candidate = candidates[int(candidate_index)]
            if all(
                hypot(candidate.row - prior.row, candidate.col - prior.col)
                >= MINIMUM_CENTRE_SEPARATION
                for prior in selected
            ):
                selected.append(candidate)
                if sum(value.stratum_index == stratum_index for value in selected) == (
                    CLUSTERS_PER_STRATUM
                ):
                    break
        if sum(value.stratum_index == stratum_index for value in selected) != (
            CLUSTERS_PER_STRATUM
        ):
            raise RuntimeError(f"insufficient eligible centres in stratum {stratum_index}")

    return tuple(
        Cluster(
            cluster_id=f"cluster_{index:02d}",
            center_row=candidate.row,
            center_col=candidate.col,
            stratum_index=candidate.stratum_index,
            euclidean_source_distance=candidate.euclidean_source_distance,
        )
        for index, candidate in enumerate(selected, start=1)
    )


def assign_holdout(clusters: Sequence[Cluster], rng: np.random.Generator) -> tuple[Cluster, ...]:
    holdout_ids: set[str] = set()
    for stratum_index in range(len(STRATUM_BOUNDS)):
        cluster_ids = sorted(
            cluster.cluster_id for cluster in clusters if cluster.stratum_index == stratum_index
        )
        permuted = rng.permutation(cluster_ids)
        holdout_ids.update(str(value) for value in permuted[:HOLDOUT_PER_STRATUM])
    return tuple(
        replace(cluster, split="holdout" if cluster.cluster_id in holdout_ids else "training")
        for cluster in clusters
    )


def expand_sites(clusters: Sequence[Cluster]) -> tuple[DesignSite, ...]:
    sites: list[DesignSite] = []
    for cluster in sorted(clusters, key=lambda value: value.cluster_id):
        for offset_index, (delta_row, delta_col) in enumerate(SITE_OFFSETS):
            sites.append(
                DesignSite(
                    cluster_id=cluster.cluster_id,
                    split=cluster.split,
                    stratum_index=cluster.stratum_index,
                    center_row=cluster.center_row,
                    center_col=cluster.center_col,
                    euclidean_source_distance=cluster.euclidean_source_distance,
                    site_id=f"{cluster.cluster_id}_site_{offset_index}",
                    site_offset_index=offset_index,
                    offset_row=delta_row,
                    offset_col=delta_col,
                    row=cluster.center_row + delta_row,
                    col=cluster.center_col + delta_col,
                )
            )
    return tuple(sites)


def build_design(
    landscape: Landscape,
    centre_rng: np.random.Generator,
    holdout_rng: np.random.Generator,
) -> SamplingDesign:
    network = build_access_network(landscape.shape)
    eligible = find_eligible_centres(landscape, network)
    clusters = assign_holdout(select_clusters(eligible, centre_rng), holdout_rng)
    sites = expand_sites(clusters)
    return SamplingDesign(
        network=network, eligible_centres=eligible, clusters=clusters, sites=sites
    )


def _stratum_index(distance: float) -> int:
    for index, (lower, upper) in enumerate(STRATUM_BOUNDS):
        if lower <= distance < upper:
            return index
    raise ValueError(f"distance outside strata: {distance}")
