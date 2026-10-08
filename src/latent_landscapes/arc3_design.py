"""Equal-effort sampling pairs with a common, prospectively reserved holdout."""

from __future__ import annotations

from dataclasses import replace
from itertools import combinations

import numpy as np

from latent_landscapes.goal001.design import (
    MINIMUM_CENTRE_SEPARATION,
    Cluster,
    EligibleCentre,
    SamplingDesign,
    build_access_network,
    expand_sites,
    find_eligible_centres,
)
from latent_landscapes.goal001.landscape import Landscape

DESIGN_IDS = ("access", "balanced")
MASTER_SEED = 2026090846
PILOT_MAP_SEED = 2026090801
PRODUCTION_MAP_SEEDS = (2026090811, 2026090812, 2026090813)


def coordinate_id(row: int, col: int) -> str:
    return f"cell_{row:02d}_{col:02d}"


def _select(
    eligible: tuple[EligibleCentre, ...],
    rng: np.random.Generator,
    *,
    per_stratum: int,
    prefix: str,
    split: str,
    balanced: bool,
    reserved: tuple[Cluster, ...] = (),
) -> tuple[Cluster, ...]:
    """Stratified random or randomized greedy maximin cluster selection.

    Maximin uses training-centre distances only; reserved holdout centres impose
    the same exclusion buffer for both designs, not an optimization target.
    """
    coordinates = np.asarray([(x.row, x.col) for x in eligible], dtype=float)
    if not len(coordinates):
        raise ValueError("sampling frame is empty")
    strata = np.asarray([x.stratum_index for x in eligible])
    available = np.ones(len(eligible), dtype=bool)
    minimum_squared = MINIMUM_CENTRE_SEPARATION**2
    for centre in reserved:
        delta = coordinates - (centre.center_row, centre.center_col)
        available &= np.sum(delta**2, axis=1) >= minimum_squared
    selected: list[int] = []
    # Randomize stratum order once; cycle across strata to avoid filling the
    # western stratum completely before the others.
    order = rng.permutation(4)
    tie_break = rng.random(len(eligible))
    for _ in range(per_stratum):
        for stratum in order:
            candidates = np.flatnonzero(available & (strata == stratum))
            if not len(candidates):
                raise RuntimeError(f"infeasible {prefix} allocation in stratum {stratum}")
            if balanced and selected:
                squared = np.sum(
                    (coordinates[candidates, None] - coordinates[np.asarray(selected)][None]) ** 2,
                    axis=2,
                )
                distances = np.min(squared, axis=1)
                # Seeded random tie-break preserves reproducibility without
                # preferring the first row-major cell at equal distance.
                ranked = np.lexsort((tie_break[candidates], distances))
                index = int(candidates[ranked[-1]])
            else:
                index = int(rng.choice(candidates))
            selected.append(index)
            delta = coordinates - coordinates[index]
            available &= np.sum(delta**2, axis=1) >= minimum_squared
    return tuple(
        Cluster(
            f"{prefix}_{number:02d}",
            eligible[index].row,
            eligible[index].col,
            eligible[index].stratum_index,
            eligible[index].euclidean_source_distance,
            split,
        )
        for number, index in enumerate(selected, start=1)
    )


def build_sampling_pair(landscape: Landscape, seed: int) -> tuple[SamplingDesign, SamplingDesign]:
    """Return access and balanced designs with identical 40 holdout sites."""
    holdout_seed, access_seed, balanced_seed = np.random.SeedSequence(seed).spawn(3)
    network = build_access_network(landscape.shape)
    full_frame = find_eligible_centres(landscape, np.ones(landscape.shape, dtype=bool))
    access_frame = find_eligible_centres(landscape, network)
    holdout = _select(
        full_frame,
        np.random.default_rng(holdout_seed),
        per_stratum=2,
        prefix="holdout",
        split="holdout",
        balanced=True,
    )
    output = []
    for name, frame, child in zip(
        DESIGN_IDS, (access_frame, full_frame), (access_seed, balanced_seed), strict=True
    ):
        training = _select(
            frame,
            np.random.default_rng(child),
            per_stratum=6,
            prefix=name,
            split="training",
            balanced=name == "balanced",
            reserved=holdout,
        )
        clusters = training + holdout
        sites = tuple(
            replace(site, site_id=coordinate_id(site.row, site.col))
            for site in expand_sites(clusters)
        )
        output.append(SamplingDesign(network.copy(), frame, clusters, sites))
    pair = (output[0], output[1])
    if not all(sampling_checks(landscape, pair).values()):
        raise RuntimeError("sampling-pair invariants failed")
    return pair


def sampling_checks(
    landscape: Landscape, pair: tuple[SamplingDesign, SamplingDesign]
) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    heldout = []
    for name, design in zip(DESIGN_IDS, pair, strict=True):
        training = tuple(site for site in design.sites if site.split == "training")
        holdout = tuple(site for site in design.sites if site.split == "holdout")
        heldout.append({(site.row, site.col, site.site_id, site.cluster_id) for site in holdout})
        checks[f"{name}_site_counts"] = len(training) == 120 and len(holdout) == 40
        checks[f"{name}_unique_physical_sites"] = (
            len({(site.row, site.col) for site in design.sites}) == 160
        )
        checks[f"{name}_source_reachable"] = all(
            landscape.passable[site.row, site.col]
            and landscape.source_reachable[site.row, site.col]
            for site in design.sites
        )
        checks[f"{name}_stratum_allocation"] = all(
            sum(site.stratum_index == stratum for site in training) == 30
            and sum(site.stratum_index == stratum for site in holdout) == 10
            for stratum in range(4)
        )
        checks[f"{name}_cluster_separation"] = all(
            (a.center_row - b.center_row) ** 2 + (a.center_col - b.center_col) ** 2
            >= MINIMUM_CENTRE_SEPARATION**2
            for a, b in combinations(design.clusters, 2)
        )
        checks[f"{name}_cluster_split_isolation"] = not {
            site.cluster_id for site in training
        }.intersection(site.cluster_id for site in holdout)
    checks["identical_holdout"] = heldout[0] == heldout[1]
    checks["access_centres_on_network"] = all(
        pair[0].network[cluster.center_row, cluster.center_col]
        for cluster in pair[0].clusters
        if cluster.split == "training"
    )
    return {key: bool(value) for key, value in checks.items()}
