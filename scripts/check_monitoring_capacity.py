"""Outcome-free 30-map capacity diagnostic for the amended monitoring frame.

This script deliberately uses a zero objective.  It tests whether the exact
60-cluster geometry is feasible on each prescribed map; it is not the
random-priority production selector and its result is not a sampling panel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import scipy  # type: ignore[import-untyped]
from scipy.optimize import Bounds, LinearConstraint, milp  # type: ignore[import-untyped]
from scipy.sparse import coo_matrix  # type: ignore[import-untyped]

from latent_landscapes.arc3_landscapes import ARCHETYPES, build_landscape
from latent_landscapes.goal001.design import (
    SITE_OFFSETS,
    STRATUM_BOUNDS,
    build_access_network,
)
from latent_landscapes.monitoring_design import (
    MASTER_CLUSTERS_PER_STRATUM,
    MINIMUM_CENTRE_SEPARATION,
    find_eligible_centres,
)


def _feasibility(landscape: Any, frame: tuple[Any, ...], seed: int, limit: float) -> dict[str, Any]:
    coordinates = np.asarray([(candidate.row, candidate.col) for candidate in frame], dtype=float)
    strata = np.asarray([candidate.stratum_index for candidate in frame], dtype=np.int8)
    candidate_count = len(frame)
    if candidate_count == 0:
        return {
            "status": "solver_infeasible",
            "solver_status": -1,
            "solver_message": "eligible-centre frame is empty",
            "candidate_count": 0,
            "selected_count": 0,
        }

    row_indices: list[int] = []
    col_indices: list[int] = []
    data: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    row_number = 0
    for stratum in range(len(STRATUM_BOUNDS)):
        indices = np.flatnonzero(strata == stratum)
        for index in indices:
            row_indices.append(row_number)
            col_indices.append(int(index))
            data.append(1.0)
        lower.append(float(MASTER_CLUSTERS_PER_STRATUM))
        upper.append(float(MASTER_CLUSTERS_PER_STRATUM))
        row_number += 1
    for left in range(candidate_count):
        distances = np.sum((coordinates[left + 1 :] - coordinates[left]) ** 2, axis=1)
        for offset in np.flatnonzero(distances < MINIMUM_CENTRE_SEPARATION**2 - 1e-12):
            right = left + 1 + int(offset)
            row_indices.extend((row_number, row_number))
            col_indices.extend((left, right))
            data.extend((1.0, 1.0))
            lower.append(-np.inf)
            upper.append(1.0)
            row_number += 1

    constraints = LinearConstraint(
        coo_matrix((data, (row_indices, col_indices)), shape=(row_number, candidate_count)).tocsr(),
        np.asarray(lower),
        np.asarray(upper),
    )
    started = time.perf_counter()
    result = milp(
        c=np.zeros(candidate_count),
        integrality=np.ones(candidate_count, dtype=np.int8),
        bounds=Bounds(0.0, 1.0),
        constraints=constraints,
        options={"time_limit": limit, "mip_rel_gap": 0.0},
    )
    selected = () if result.x is None else tuple(int(i) for i in np.flatnonzero(result.x > 0.5))
    status = {0: "selected_verified", 1: "solver_time_limit", 2: "solver_infeasible"}.get(
        int(result.status), "solver_unknown"
    )
    checks = {
        "exact_count": len(selected) == 4 * MASTER_CLUSTERS_PER_STRATUM,
        "equal_strata": all(
            sum(strata[i] == s for i in selected) == MASTER_CLUSTERS_PER_STRATUM
            for s in range(4)
        ),
        "centre_spacing": all(
            np.sum((coordinates[left] - coordinates[right]) ** 2)
            >= MINIMUM_CENTRE_SEPARATION**2
            for position, left in enumerate(selected)
            for right in selected[position + 1 :]
        ),
    }
    if selected:
        footprints = tuple(
            (int(frame[index].row + dr), int(frame[index].col + dc))
            for index in selected
            for dr, dc in SITE_OFFSETS
        )
        checks["unique_footprints"] = len(set(footprints)) == len(footprints)
        checks["passable_source_reachable"] = all(
            landscape.passable[row, col] and landscape.source_reachable[row, col]
            for row, col in footprints
        )
    else:
        checks["unique_footprints"] = False
        checks["passable_source_reachable"] = False
    if status == "selected_verified" and not all(checks.values()):
        status = "solver_unknown"
    return {
        "status": status,
        "solver_status": int(result.status),
        "solver_message": str(result.message),
        "candidate_count": candidate_count,
        "selected_count": len(selected),
        "elapsed_seconds": time.perf_counter() - started,
        "method_checks": checks,
        "selected_frame_indices": list(selected),
        "sampling_seed": seed,
    }


def scan(*, repetitions: int = 10, time_limit: float = 30.0) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for repetition in range(repetitions):
        for archetype_index, archetype in enumerate(ARCHETYPES):
            map_seed = 2026101801 + 1000 * repetition + archetype_index
            sampling_seed = 2026101811 + 1000 * repetition + archetype_index
            started = time.perf_counter()
            record: dict[str, Any] = {
                "archetype": archetype,
                "archetype_index": archetype_index,
                "repetition": repetition,
                "map_seed": map_seed,
                "sampling_seed": sampling_seed,
                "access_buffer_cells": 2.0,
                "minimum_centre_separation": MINIMUM_CENTRE_SEPARATION,
                "objective": "zero; feasibility diagnostic only, not a sampling distribution",
            }
            try:
                landscape = build_landscape(archetype, map_seed)
                network = build_access_network(landscape.shape)
                frame = find_eligible_centres(landscape, network)
                record["frame_centres_by_stratum"] = [
                    sum(candidate.stratum_index == stratum for candidate in frame)
                    for stratum in range(len(STRATUM_BOUNDS))
                ]
                record["frame_sha256"] = hashlib.sha256(
                    "|".join(f"{candidate.row},{candidate.col}" for candidate in frame).encode()
                ).hexdigest()
                record.update(_feasibility(landscape, frame, sampling_seed, time_limit))
            except Exception as error:  # map construction failures are a declared outcome
                record.update(
                    {
                        "status": "failed_map_generator",
                        "solver_status": None,
                        "solver_message": f"{type(error).__name__}: {error}",
                    }
                )
            record["elapsed_seconds_total"] = time.perf_counter() - started
            rows.append(record)
            print(json.dumps(record, sort_keys=True), flush=True)
    return {
        "schema": "paper1-monitoring-capacity-diagnostic-v1",
        "repetitions": repetitions,
        "map_count": len(rows),
        "scipy_version": scipy.__version__,
        "numpy_version": np.__version__,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--time-limit", type=float, default=30.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = scan(repetitions=args.repetitions, time_limit=args.time_limit)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
