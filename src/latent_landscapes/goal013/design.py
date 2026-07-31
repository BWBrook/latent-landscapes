"""Deterministic contrast-balanced sampling design for Goal 013."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, replace
from functools import lru_cache
from math import hypot, isfinite
from typing import Any

import numpy as np

from latent_landscapes.goal001.design import (
    MINIMUM_CENTRE_SEPARATION,
    SITE_OFFSETS,
    STRATUM_LABELS,
    Cluster,
    SamplingDesign,
    build_access_network,
    expand_sites,
    find_eligible_centres,
)
from latent_landscapes.goal001.landscape import Landscape, build_landscape
from latent_landscapes.goal001.spread import (
    multi_source_dijkstra,
    passable_edges,
    source_labels,
)
from latent_landscapes.goal006.spread import geometric_mean_cost, transform_edge_costs

SELECTOR_SEED = 20260731
SEARCH_ATTEMPTS = 10_000
MAXIMUM_ABSOLUTE_CORRELATION = 0.60
EXPECTED_DESIGN_DIGEST = "ba887b460d8a8dff1b731086de77dd2d00edce1c00d37c8550fa161558092410"
TAIL_ORDER = ("low", "high")


@dataclass(frozen=True, slots=True)
class DesignCandidate:
    row: int
    col: int
    stratum_index: int
    euclidean_source_distance: float
    retained: bool
    source_overlap_cells: tuple[tuple[int, int], ...]
    u: float | None
    z: float | None
    lower_tertile: float | None
    upper_tertile: float | None
    tail: str | None
    selected: bool = False
    cluster_id: str | None = None
    split: str | None = None

    @property
    def stratum(self) -> str:
        return STRATUM_LABELS[self.stratum_index]


@dataclass(frozen=True, slots=True)
class SelectedCluster:
    cluster_id: str
    center_row: int
    center_col: int
    stratum_index: int
    euclidean_source_distance: float
    split: str
    tail: str
    u: float
    z: float

    @property
    def stratum(self) -> str:
        return STRATUM_LABELS[self.stratum_index]


@dataclass(frozen=True, slots=True)
class StratumQuantiles:
    stratum_index: int
    lower_tertile: float
    upper_tertile: float
    interquartile_range: float
    retained_count: int
    low_count: int
    high_count: int


@dataclass(frozen=True, slots=True)
class DesignScore:
    minimum_standardized_contrast: float
    maximum_absolute_u_z_correlation: float
    sum_squared_centered_z: float
    minimum_pairwise_distance: float
    standardized_contrast_by_stratum: tuple[float, ...]
    absolute_u_z_correlation_by_stratum: tuple[float, ...]


@dataclass(frozen=True, slots=True, eq=False)
class DesignSelection:
    sampling_design: SamplingDesign
    candidates: tuple[DesignCandidate, ...]
    selected_clusters: tuple[SelectedCluster, ...]
    quantiles: tuple[StratumQuantiles, ...]
    geometric_mean_edge_cost: float
    complete_attempt_count: int
    unique_design_count: int
    score: DesignScore
    design_digest: str
    invariants: dict[str, bool]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DesignSelection):
            return NotImplemented
        return (
            self.candidates == other.candidates
            and self.selected_clusters == other.selected_clusters
            and self.quantiles == other.quantiles
            and self.geometric_mean_edge_cost == other.geometric_mean_edge_cost
            and self.complete_attempt_count == other.complete_attempt_count
            and self.unique_design_count == other.unique_design_count
            and self.score == other.score
            and self.design_digest == other.design_digest
            and self.invariants == other.invariants
            and self.sampling_design.eligible_centres == other.sampling_design.eligible_centres
            and self.sampling_design.clusters == other.sampling_design.clusters
            and self.sampling_design.sites == other.sampling_design.sites
            and np.array_equal(
                self.sampling_design.network,
                other.sampling_design.network,
            )
        )


def build_contrast_balanced_design(
    landscape: Landscape | None = None,
) -> DesignSelection:
    """Replay the frozen 10,000-attempt selector without stochastic inputs."""
    if landscape is None:
        return _build_default_design(SEARCH_ATTEMPTS, MAXIMUM_ABSOLUTE_CORRELATION)
    return _build_design(
        landscape,
        attempts=SEARCH_ATTEMPTS,
        maximum_absolute_correlation=MAXIMUM_ABSOLUTE_CORRELATION,
    )


@lru_cache(maxsize=8)
def _build_default_design(
    attempts: int,
    maximum_absolute_correlation: float,
) -> DesignSelection:
    return _build_design(
        build_landscape(),
        attempts=attempts,
        maximum_absolute_correlation=maximum_absolute_correlation,
    )


def _build_design(
    landscape: Landscape,
    *,
    attempts: int,
    maximum_absolute_correlation: float,
) -> DesignSelection:
    network = build_access_network(landscape.shape)
    eligible = find_eligible_centres(landscape, network)
    candidates, quantiles, geometric_cost = _candidate_metrics(landscape, eligible)
    retained = tuple(candidate for candidate in candidates if candidate.retained)
    pools = {
        (stratum_index, tail): tuple(
            sorted(
                (
                    candidate
                    for candidate in retained
                    if candidate.stratum_index == stratum_index and candidate.tail == tail
                ),
                key=lambda value: (value.row, value.col),
            )
        )
        for stratum_index in range(4)
        for tail in TAIL_ORDER
    }
    slots = tuple(
        (stratum_index, tail) for stratum_index in range(4) for tail in TAIL_ORDER for _ in range(4)
    )
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(SELECTOR_SEED)))
    complete_count = 0
    unique: dict[
        tuple[tuple[int, int, int], ...],
        tuple[DesignCandidate, ...],
    ] = {}
    for _ in range(attempts):
        attempt_selection: list[DesignCandidate] = []
        for slot_index in rng.permutation(32):
            slot = slots[int(slot_index)]
            feasible = tuple(
                candidate
                for candidate in pools[slot]
                if all(
                    hypot(candidate.row - prior.row, candidate.col - prior.col)
                    >= MINIMUM_CENTRE_SEPARATION
                    for prior in attempt_selection
                )
            )
            if not feasible:
                break
            attempt_selection.append(feasible[int(rng.integers(len(feasible)))])
        if len(attempt_selection) != 32:
            continue
        complete_count += 1
        coordinates = tuple(
            sorted(
                (candidate.stratum_index, candidate.row, candidate.col)
                for candidate in attempt_selection
            )
        )
        unique.setdefault(coordinates, tuple(attempt_selection))
    if not unique:
        raise RuntimeError("selector found no complete design")

    scored: list[tuple[tuple[object, ...], tuple[DesignCandidate, ...]]] = []
    for complete_design in unique.values():
        try:
            key = _ranking_key(complete_design, retained)
        except RuntimeError as error:
            if "zero-variance stratum" not in str(error):
                raise
            continue
        scored.append((key, complete_design))
    if not scored:
        raise RuntimeError("selector found no valid complete design")
    _, winner = min(scored, key=lambda item: item[0])
    score = _score_design(winner, retained)
    if score.maximum_absolute_u_z_correlation > maximum_absolute_correlation:
        raise RuntimeError("winning design fails the correlation gate")

    selected_clusters = _assign_clusters(winner)
    clusters = tuple(
        Cluster(
            cluster_id=row.cluster_id,
            center_row=row.center_row,
            center_col=row.center_col,
            stratum_index=row.stratum_index,
            euclidean_source_distance=row.euclidean_source_distance,
            split=row.split,
        )
        for row in selected_clusters
    )
    sites = expand_sites(clusters)
    sampling_design = SamplingDesign(
        network=network,
        eligible_centres=tuple(eligible),
        clusters=clusters,
        sites=sites,
    )
    selected_by_coordinate = {
        (row.stratum_index, row.center_row, row.center_col): row for row in selected_clusters
    }
    annotated_candidates = tuple(
        replace(
            candidate,
            selected=(
                candidate.stratum_index,
                candidate.row,
                candidate.col,
            )
            in selected_by_coordinate,
            cluster_id=(
                selected_by_coordinate[
                    (candidate.stratum_index, candidate.row, candidate.col)
                ].cluster_id
                if (candidate.stratum_index, candidate.row, candidate.col) in selected_by_coordinate
                else None
            ),
            split=(
                selected_by_coordinate[
                    (candidate.stratum_index, candidate.row, candidate.col)
                ].split
                if (candidate.stratum_index, candidate.row, candidate.col) in selected_by_coordinate
                else None
            ),
        )
        for candidate in candidates
    )
    digest = _design_digest(selected_clusters, sites)
    split_counts = Counter(row.split for row in selected_clusters)
    quotas = Counter((row.stratum_index, row.tail) for row in selected_clusters)
    retained_counts = Counter(row.stratum_index for row in annotated_candidates if row.retained)
    invariants = {
        "eligible_centre_count": len(eligible) == 635,
        "source_overlap_exclusion_count": sum(not row.retained for row in annotated_candidates)
        == 6,
        "retained_candidate_count": sum(row.retained for row in annotated_candidates) == 629,
        "retained_stratum_counts": retained_counts == {0: 196, 1: 122, 2: 154, 3: 157},
        "selector_found_complete_design": complete_count > 0 and bool(unique),
        "stratum_tail_quotas": all(
            quotas[(stratum_index, tail)] == 4 for stratum_index in range(4) for tail in TAIL_ORDER
        ),
        "minimum_centre_separation": score.minimum_pairwise_distance >= MINIMUM_CENTRE_SEPARATION,
        "correlation_gate": score.maximum_absolute_u_z_correlation <= maximum_absolute_correlation,
        "cluster_and_site_counts": len(clusters) == 32 and len(sites) == 160,
        "training_holdout_counts": split_counts == {"training": 24, "holdout": 8},
        "design_digest": digest == EXPECTED_DESIGN_DIGEST,
    }
    if not all(invariants.values()):
        raise RuntimeError("selector failed a frozen implementation invariant")
    return DesignSelection(
        sampling_design=sampling_design,
        candidates=annotated_candidates,
        selected_clusters=selected_clusters,
        quantiles=quantiles,
        geometric_mean_edge_cost=geometric_cost,
        complete_attempt_count=complete_count,
        unique_design_count=len(unique),
        score=score,
        design_digest=digest,
        invariants=invariants,
    )


def _candidate_metrics(
    landscape: Landscape,
    eligible: tuple[Any, ...],
) -> tuple[
    tuple[DesignCandidate, ...],
    tuple[StratumQuantiles, ...],
    float,
]:
    edges = passable_edges(landscape)
    geometric_cost = geometric_mean_cost(edges)
    uniform_edges = transform_edge_costs(edges, 0.0)
    accepted_edges = transform_edge_costs(edges, 1.0)
    labels = source_labels(landscape)
    d0_values, _ = multi_source_dijkstra(
        node_count=landscape.cell_count,
        weighted_edges=uniform_edges,
        source_labels=labels,
    )
    d1_values, _ = multi_source_dijkstra(
        node_count=landscape.cell_count,
        weighted_edges=accepted_edges,
        source_labels=labels,
    )
    d0 = np.asarray(d0_values, dtype=np.float64).reshape(landscape.shape)
    d1 = np.asarray(d1_values, dtype=np.float64).reshape(landscape.shape)
    initial: list[DesignCandidate] = []
    for centre in eligible:
        cells = tuple(
            (centre.row + delta_row, centre.col + delta_col)
            for delta_row, delta_col in SITE_OFFSETS
        )
        d0_sites = np.asarray([d0[cell] for cell in cells], dtype=np.float64)
        overlap = tuple(cell for cell, value in zip(cells, d0_sites, strict=True) if value == 0.0)
        if overlap:
            initial.append(
                DesignCandidate(
                    row=centre.row,
                    col=centre.col,
                    stratum_index=centre.stratum_index,
                    euclidean_source_distance=centre.euclidean_source_distance,
                    retained=False,
                    source_overlap_cells=overlap,
                    u=None,
                    z=None,
                    lower_tertile=None,
                    upper_tertile=None,
                    tail=None,
                )
            )
            continue
        d1_sites = np.asarray([d1[cell] for cell in cells], dtype=np.float64)
        u = float(np.mean(np.log(d0_sites), dtype=np.float64))
        z = float(np.mean(np.log(d1_sites / d0_sites), dtype=np.float64))
        if not isfinite(u) or not isfinite(z):
            raise RuntimeError("selector candidate metrics must be finite")
        initial.append(
            DesignCandidate(
                row=centre.row,
                col=centre.col,
                stratum_index=centre.stratum_index,
                euclidean_source_distance=centre.euclidean_source_distance,
                retained=True,
                source_overlap_cells=(),
                u=u,
                z=z,
                lower_tertile=None,
                upper_tertile=None,
                tail=None,
            )
        )

    quantiles: list[StratumQuantiles] = []
    by_stratum: dict[int, tuple[float, float]] = {}
    for stratum_index in range(4):
        z_values = np.asarray(
            [
                candidate.z
                for candidate in initial
                if candidate.retained and candidate.stratum_index == stratum_index
            ],
            dtype=np.float64,
        )
        lower, upper = np.quantile(z_values, [1.0 / 3.0, 2.0 / 3.0])
        iqr = float(np.quantile(z_values, 0.75) - np.quantile(z_values, 0.25))
        if iqr <= 0.0:
            raise RuntimeError("selector stratum has zero z variance")
        by_stratum[stratum_index] = (float(lower), float(upper))
        quantiles.append(
            StratumQuantiles(
                stratum_index=stratum_index,
                lower_tertile=float(lower),
                upper_tertile=float(upper),
                interquartile_range=iqr,
                retained_count=len(z_values),
                low_count=int(np.sum(z_values <= lower)),
                high_count=int(np.sum(z_values >= upper)),
            )
        )
    candidates = tuple(
        replace(
            candidate,
            lower_tertile=(by_stratum[candidate.stratum_index][0] if candidate.retained else None),
            upper_tertile=(by_stratum[candidate.stratum_index][1] if candidate.retained else None),
            tail=(
                _tail(
                    candidate.z,
                    *by_stratum[candidate.stratum_index],
                )
                if candidate.retained and candidate.z is not None
                else None
            ),
        )
        for candidate in initial
    )
    return candidates, tuple(quantiles), geometric_cost


def _tail(z: float, lower: float, upper: float) -> str:
    if z <= lower:
        return "low"
    if z >= upper:
        return "high"
    return "middle"


def _score_design(
    selected: tuple[DesignCandidate, ...],
    retained: tuple[DesignCandidate, ...],
) -> DesignScore:
    standardized: list[float] = []
    correlations: list[float] = []
    centered_sum = np.float64(0.0)
    for stratum_index in range(4):
        rows = tuple(row for row in selected if row.stratum_index == stratum_index)
        low = np.asarray(
            [row.z for row in rows if row.tail == "low"],
            dtype=np.float64,
        )
        high = np.asarray(
            [row.z for row in rows if row.tail == "high"],
            dtype=np.float64,
        )
        population = np.asarray(
            [row.z for row in retained if row.stratum_index == stratum_index],
            dtype=np.float64,
        )
        iqr = np.quantile(population, 0.75) - np.quantile(population, 0.25)
        standardized.append(float((np.mean(high) - np.mean(low)) / iqr))
        u_values = np.asarray([row.u for row in rows], dtype=np.float64)
        z_values = np.asarray([row.z for row in rows], dtype=np.float64)
        if np.var(u_values) == 0.0 or np.var(z_values) == 0.0:
            raise RuntimeError("selected design contains a zero-variance stratum")
        correlations.append(abs(float(np.corrcoef(u_values, z_values)[0, 1])))
        centered_sum += np.sum(
            np.square(z_values - np.mean(z_values)),
            dtype=np.float64,
        )
    minimum_distance = min(
        hypot(first.row - second.row, first.col - second.col)
        for index, first in enumerate(selected)
        for second in selected[index + 1 :]
    )
    return DesignScore(
        minimum_standardized_contrast=_round12(min(standardized)),
        maximum_absolute_u_z_correlation=_round12(max(correlations)),
        sum_squared_centered_z=_round12(float(centered_sum)),
        minimum_pairwise_distance=_round12(minimum_distance),
        standardized_contrast_by_stratum=tuple(standardized),
        absolute_u_z_correlation_by_stratum=tuple(correlations),
    )


def _ranking_key(
    selected: tuple[DesignCandidate, ...],
    retained: tuple[DesignCandidate, ...],
) -> tuple[object, ...]:
    score = _score_design(selected, retained)
    coordinates = tuple(sorted((row.stratum_index, row.row, row.col) for row in selected))
    return (
        -score.minimum_standardized_contrast,
        score.maximum_absolute_u_z_correlation,
        -score.sum_squared_centered_z,
        -score.minimum_pairwise_distance,
        coordinates,
    )


def _assign_clusters(
    selected: tuple[DesignCandidate, ...],
) -> tuple[SelectedCluster, ...]:
    holdouts: set[tuple[int, str, int, int]] = set()
    for stratum_index in range(4):
        for tail in TAIL_ORDER:
            group = tuple(
                sorted(
                    (
                        row
                        for row in selected
                        if row.stratum_index == stratum_index and row.tail == tail
                    ),
                    key=lambda value: (value.row, value.col),
                )
            )
            z_values = np.asarray([row.z for row in group], dtype=np.float64)
            group_mean = float(np.mean(z_values))
            holdout = min(
                group,
                key=lambda value: (
                    abs(_required_metric(value.z) - group_mean),
                    value.row,
                    value.col,
                ),
            )
            holdouts.add((stratum_index, tail, holdout.row, holdout.col))
    ordered = tuple(
        sorted(
            selected,
            key=lambda value: (
                value.stratum_index,
                TAIL_ORDER.index(str(value.tail)),
                value.row,
                value.col,
            ),
        )
    )
    return tuple(
        SelectedCluster(
            cluster_id=f"cluster_{index:02d}",
            center_row=row.row,
            center_col=row.col,
            stratum_index=row.stratum_index,
            euclidean_source_distance=row.euclidean_source_distance,
            split=(
                "holdout"
                if (row.stratum_index, row.tail, row.row, row.col) in holdouts
                else "training"
            ),
            tail=str(row.tail),
            u=_required_metric(row.u),
            z=_required_metric(row.z),
        )
        for index, row in enumerate(ordered, start=1)
    )


def _design_digest(
    clusters: tuple[SelectedCluster, ...],
    sites: tuple[Any, ...],
) -> str:
    by_cluster = {row.cluster_id: row for row in clusters}
    cluster_rows = [
        {
            "cluster_id": row.cluster_id,
            "split": row.split,
            "stratum_index": row.stratum_index,
            "tail": row.tail,
            "center_row": row.center_row,
            "center_col": row.center_col,
            "euclidean_source_distance": row.euclidean_source_distance,
            "u": row.u,
            "z": row.z,
        }
        for row in clusters
    ]
    site_rows = [
        {
            "cluster_id": row.cluster_id,
            "split": row.split,
            "stratum_index": row.stratum_index,
            "tail": by_cluster[row.cluster_id].tail,
            "center_row": row.center_row,
            "center_col": row.center_col,
            "euclidean_source_distance": row.euclidean_source_distance,
            "site_id": row.site_id,
            "site_offset_index": row.site_offset_index,
            "offset_row": row.offset_row,
            "offset_col": row.offset_col,
            "row": row.row,
            "col": row.col,
            "u": by_cluster[row.cluster_id].u,
            "z": by_cluster[row.cluster_id].z,
        }
        for row in sites
    ]
    payload = _canonical12(
        {
            "selected_clusters": cluster_rows,
            "design_sites": site_rows,
        }
    )
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _canonical12(value: object) -> object:
    if isinstance(value, float):
        return _round12(value)
    if isinstance(value, list):
        return [_canonical12(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical12(item) for key, item in value.items()}
    return value


def _round12(value: float) -> float:
    rounded = float(np.round(np.float64(value), 12))
    return 0.0 if rounded == 0.0 else rounded


def _required_metric(value: float | None) -> float:
    if value is None:
        raise RuntimeError("selected candidate is missing a finite design metric")
    return value


__all__ = [
    "EXPECTED_DESIGN_DIGEST",
    "MAXIMUM_ABSOLUTE_CORRELATION",
    "SEARCH_ATTEMPTS",
    "SELECTOR_SEED",
    "DesignCandidate",
    "DesignScore",
    "DesignSelection",
    "SelectedCluster",
    "StratumQuantiles",
    "build_contrast_balanced_design",
]
