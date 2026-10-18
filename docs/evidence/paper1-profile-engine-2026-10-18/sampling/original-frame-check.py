"""Outcome-free capacity diagnostic; this does not select a production design."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.ndimage import distance_transform_edt
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csc_matrix, lil_matrix

from latent_landscapes.arc3_design import _select
from latent_landscapes.arc3_landscapes import build_landscape
from latent_landscapes.goal001.design import build_access_network, find_eligible_centres


def capacity(archetype, index, width, fixed_holdout):
    map_seed, sampling_seed = 2026101801 + index, 2026101811 + index
    landscape = build_landscape(archetype, map_seed)
    access = build_access_network(landscape.shape)
    frame_mask = distance_transform_edt(~access) <= width
    frame = find_eligible_centres(landscape, frame_mask)
    coordinates = np.array([(x.row, x.col) for x in frame])
    strata = np.array([x.stratum_index for x in frame])
    holdout_indices = []
    keep = np.ones(len(frame), dtype=bool)
    if fixed_holdout:
        holdout_seed, _, _ = np.random.SeedSequence(sampling_seed).spawn(3)
        holdout = _select(frame, np.random.default_rng(holdout_seed), per_stratum=2,
                          prefix="holdout", split="holdout", balanced=False)
        hxy = np.array([(x.center_row, x.center_col) for x in holdout])
        keep = np.all(np.sum((coordinates[:, None] - hxy[None, :]) ** 2, axis=2) >= 64,
                      axis=1)
        holdout_indices = [next(j for j, xy in enumerate(coordinates)
                                if np.array_equal(xy, h)) for h in hxy]
    indices = np.flatnonzero(keep)
    xy, stratum = coordinates[keep], strata[keep]
    pairs = np.transpose(np.nonzero(np.triu(
        np.sum((xy[:, None] - xy[None, :]) ** 2, axis=2) < 64, k=1)))
    matrix = lil_matrix((4 + len(pairs), len(xy)))
    count = 13 if fixed_holdout else 15
    for s in range(4):
        matrix[s, np.flatnonzero(stratum == s)] = 1
    for j, (left, right) in enumerate(pairs):
        matrix[4 + j, left] = matrix[4 + j, right] = 1
    lower = np.r_[np.full(4, count), np.full(len(pairs), -np.inf)]
    upper = np.r_[np.full(4, count), np.ones(len(pairs))]
    started = time.perf_counter()
    result = milp(np.zeros(len(xy)), integrality=np.ones(len(xy)), bounds=Bounds(0, 1),
                  constraints=LinearConstraint(csc_matrix(matrix), lower, upper),
                  options={"time_limit": 30, "mip_rel_gap": 0})
    selected = [] if result.x is None else indices[np.flatnonzero(result.x > .5)].tolist()
    if selected:
        assert len(selected) == 4 * count
        assert all(sum(strata[j] == s for j in selected) == count for s in range(4))
        all_indices = selected + holdout_indices
        all_xy = coordinates[all_indices]
        distances = np.sum((all_xy[:, None] - all_xy[None, :]) ** 2, axis=2)
        assert np.all(distances[np.triu_indices(len(all_xy), 1)] >= 64)
        footprints = [(int(r + dr), int(c + dc)) for r, c in all_xy
                      for dr, dc in ((0, 0), (-2, 0), (2, 0), (0, -2), (0, 2))]
        assert len(set(footprints)) == len(footprints)
        assert all(landscape.passable[r, c] and landscape.source_reachable[r, c]
                   for r, c in footprints)
    return {"archetype": archetype, "map_seed": map_seed, "sampling_seed": sampling_seed,
            "access_buffer_cells": width, "fixed_holdout": fixed_holdout,
            "minimum_centre_separation": 8, "requested_clusters_per_stratum": count,
            "frame_centres_by_stratum": [int(sum(strata == s)) for s in range(4)],
            "remaining_centres_by_stratum": [int(sum(stratum == s)) for s in range(4)],
            "status": int(result.status), "message": result.message,
            "elapsed_seconds": time.perf_counter() - started,
            "selected_frame_indices": selected, "holdout_frame_indices": holdout_indices,
            "frame_sha256": hashlib.sha256(coordinates.tobytes()).hexdigest(),
            "objective": "zero; feasibility diagnostic only, not a sampling distribution"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--buffer", type=int, required=True)
    parser.add_argument("--joint", action="store_true")
    args = parser.parse_args()
    assert args.buffer in (0, 1, 2)
    rows = []
    for i, name in enumerate(("connected", "corridor", "barrier")):
        row = capacity(name, i, args.buffer, not args.joint)
        rows.append(row)
        print(json.dumps(row), flush=True)
    receipt = {"rows": rows, "scipy": scipy.__version__, "numpy": np.__version__,
               "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    suffix = "joint" if args.joint else "fixed-holdout"
    destination = Path(__file__).with_name(f"sampling-buffer{args.buffer}-{suffix}.json")
    if destination.exists():
        raise FileExistsError(destination)
    destination.write_text(json.dumps(receipt, indent=2) + "\n")
