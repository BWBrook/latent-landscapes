"""Paired resistance-contrast benchmark and compact spatial diagnostics."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from math import ceil, isfinite
from pathlib import Path
from typing import cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal001.landscape import Landscape, build_landscape
from latent_landscapes.goal001.spread import compute_spread, passable_edges

from .spread import (
    ETA_VALUES,
    MASTER_SEED,
    ContrastSpreadTruth,
    compute_paired_spreads,
    transform_edge_costs,
)

__all__ = [
    "DEFAULT_CONFIG",
    "ETA_VALUES",
    "FROZEN_GOAL003",
    "Goal006Config",
    "Goal006Result",
    "classify_outcome",
    "generator_from_seed_record",
    "run_goal006",
    "spawn_seed_records",
]

REPLICATES = 100
OCCUPANCIES = (0.25, 0.50, 0.75)
SOURCE_IDENTITY = {
    "repository_commit": "edbeb8cc15ea5c95acb74272f0a0122a9cee84f0",
    "goal001_landscape_blob": "a376df359e09b2357a0b5262479bcebaeee2ff25",
    "goal001_spread_blob": "ea42352590c8cb3b217ac0b8203a3cb7b3238800",
    "goal003_stochastic_spread_blob": "d20440415ea33cee0f64f41427ae81197ca8fd9e",
    "goal003_benchmark_blob": "92db1fd224a652bcac591d0959c3ac5d28893670",
    "goal003_artifacts_blob": "4d6e6ca6ff98aa8d5c23700b111e6e0fda2d46d4",
}
PINNED_PATHS = {
    "goal001_landscape_blob": "src/latent_landscapes/goal001/landscape.py",
    "goal001_spread_blob": "src/latent_landscapes/goal001/spread.py",
    "goal003_stochastic_spread_blob": "src/latent_landscapes/goal003/spread.py",
    "goal003_benchmark_blob": "src/latent_landscapes/goal003/benchmark.py",
}
FROZEN_GOAL003 = {
    "median_of_cell_stochastic_median": 31.69888227914729,
    "deterministic_stochastic_median_correlation": 0.9937734843350453,
    "temporal_scale_ratio": 0.4626972981816758,
    "t50_sd": 1.6196762763006858,
    "representative_index": 29,
    "representative_t50": 31.29398268570847,
}


@dataclass(frozen=True, slots=True)
class Goal006Config:
    master_seed: int = MASTER_SEED
    replicates: int = REPLICATES
    etas: tuple[float, ...] = ETA_VALUES

    def __post_init__(self) -> None:
        if self.replicates <= 0:
            raise ValueError("replicates must be positive")
        if tuple(self.etas) != ETA_VALUES:
            raise ValueError("Goal 006 eta grid is frozen at 0, 0.5, 1, 1.5, and 2")

    @property
    def is_production(self) -> bool:
        return self == DEFAULT_CONFIG


DEFAULT_CONFIG = Goal006Config()


@dataclass(frozen=True, slots=True)
class SeedRecord:
    replicate_index: int
    entropy: int
    spawn_key: tuple[int, ...]
    state_words: tuple[int, ...]
    pool_size: int


@dataclass(frozen=True, slots=True)
class ReplicateSummary:
    replicate_index: int
    eta: float
    t25: float
    t50: float
    t75: float
    t90: float
    maximum_arrival: float
    alignment_scale: float
    median_abs_aligned_log_residual: float
    p90_abs_aligned_log_residual: float
    front_jaccard_25: float
    front_jaccard_50: float
    front_jaccard_75: float
    arrival_rank_correlation: float
    displaced_fraction: float
    source_reassignment_fraction: float
    source_contribution_fractions: tuple[tuple[str, float], ...]
    A: float
    J: float
    H: float


@dataclass(frozen=True, slots=True)
class SpatialEffectSummary:
    eta: float
    median_A: float
    p05_A: float
    p95_A: float
    median_J: float
    p05_J: float
    p95_J: float
    median_H: float
    p05_H: float
    p95_H: float
    median_abs_residual: float
    median_t50: float
    consistency_count: int
    expected_sign_count: int
    corridor_matrix_contrast: float
    patch_matrix_contrast: float
    water_matrix_contrast: float


@dataclass(frozen=True, slots=True)
class Goal006Result:
    config: Goal006Config
    landscape: Landscape
    edge_costs: tuple[tuple[int, int, float], ...]
    seeds: tuple[SeedRecord, ...]
    edge_cost_summary: tuple[dict[str, object], ...]
    replicate_summaries: tuple[ReplicateSummary, ...]
    spatial_effect_summary: tuple[SpatialEffectSummary, ...]
    cell_summary: tuple[dict[str, object], ...]
    representative_realizations: tuple[dict[str, object], ...]
    invariants: dict[str, bool]
    diagnostics: dict[str, object]
    outcome: str


def generator_from_seed_record(record: SeedRecord) -> np.random.Generator:
    sequence = np.random.SeedSequence(
        record.entropy, spawn_key=record.spawn_key, pool_size=record.pool_size
    )
    if tuple(map(int, sequence.generate_state(len(record.state_words)))) != record.state_words:
        raise ValueError("seed record does not replay")
    return np.random.Generator(np.random.PCG64(sequence))


def spawn_seed_records(config: Goal006Config = DEFAULT_CONFIG) -> tuple[SeedRecord, ...]:
    root = np.random.SeedSequence(config.master_seed)
    children = root.spawn(config.replicates)
    return tuple(
        SeedRecord(
            i,
            int(cast(int, child.entropy)),
            tuple(map(int, child.spawn_key)),
            tuple(map(int, child.generate_state(4))),
            child.pool_size,
        )
        for i, child in enumerate(children)
    )


def _rank(values: NDArray[np.float64]) -> NDArray[np.float64]:
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=np.float64)
    ranks[order] = np.arange(len(values), dtype=np.float64)
    return ranks


def _front(values: NDArray[np.float64], q: float, cell_ids: NDArray[np.int64]) -> set[int]:
    count = ceil(q * len(values))
    order = np.lexsort((cell_ids, values))
    return set(map(int, cell_ids[order[:count]]))


def _jaccard_distance(left: set[int], right: set[int]) -> float:
    union = left | right
    return 0.0 if not union else 1.0 - len(left & right) / len(union)


def _habitat_values(
    landscape: Landscape, residual: NDArray[np.float64], name: str
) -> NDArray[np.float64]:
    return np.asarray(residual[landscape.passable & (landscape.habitat_class == name)])


def _summarize_pair(
    landscape: Landscape,
    eta: float,
    replicate_index: int,
    truth: ContrastSpreadTruth,
    reference: ContrastSpreadTruth,
    edge_count: int,
) -> tuple[ReplicateSummary, dict[str, float]]:
    mask = landscape.passable
    source_mask = landscape.source_zone != ""
    values = truth.arrival[mask]
    reference_values = reference.arrival[mask]
    non_source = mask & ~source_mask
    residual = np.zeros_like(truth.arrival, dtype=np.float64)
    if eta == 1.0:
        scale = 1.0
    else:
        scale = float(
            np.exp(
                np.median(np.log(reference.arrival[non_source]) - np.log(truth.arrival[non_source]))
            )
        )
    residual[non_source] = np.log(scale * truth.arrival[non_source] / reference.arrival[non_source])
    cell_ids = np.flatnonzero(mask).astype(np.int64)
    reference_fronts = {q: _front(reference.arrival[mask], q, cell_ids) for q in OCCUPANCIES}
    fronts = {q: _front(truth.arrival[mask], q, cell_ids) for q in OCCUPANCIES}
    ranks = _rank(values)
    reference_ranks = _rank(reference_values)
    rank_corr = float(np.corrcoef(ranks, reference_ranks)[0, 1]) if len(values) > 1 else 1.0
    contributions = tuple(
        (label, float(np.mean(truth.source_zone[mask] == label)))
        for label in sorted(set(str(x) for x in truth.source_zone[mask]))
    )
    habitat = {
        "corridor": float(np.median(_habitat_values(landscape, residual, "corridor"))),
        "low_quality_matrix": float(
            np.median(_habitat_values(landscape, residual, "low_quality_matrix"))
        ),
        "high_quality_patch": float(
            np.median(_habitat_values(landscape, residual, "high_quality_patch"))
        ),
        "medium_quality": float(np.median(_habitat_values(landscape, residual, "medium_quality"))),
        "water_adjacent_low_quality_matrix": float(
            np.median(
                residual[
                    mask
                    & (landscape.habitat_class == "low_quality_matrix")
                    & (landscape.water_neighbor_count > 0)
                ]
            )
        ),
        "non_water_adjacent_low_quality_matrix": float(
            np.median(
                residual[
                    mask
                    & (landscape.habitat_class == "low_quality_matrix")
                    & (landscape.water_neighbor_count == 0)
                ]
            )
        ),
    }
    a = float(np.median(np.abs(residual[non_source])))
    j = _jaccard_distance(fronts[0.5], reference_fronts[0.5])
    h = habitat["corridor"] - habitat["low_quality_matrix"]
    q25, q50, q75, q90 = tuple(
        float(np.quantile(values, q, method="higher")) for q in (0.25, 0.50, 0.75, 0.90)
    )
    j25, j50, j75 = tuple(_jaccard_distance(fronts[q], reference_fronts[q]) for q in OCCUPANCIES)
    summary = ReplicateSummary(
        replicate_index,
        eta,
        q25,
        q50,
        q75,
        q90,
        float(values.max()),
        scale,
        float(np.median(np.abs(residual[non_source]))),
        float(np.quantile(np.abs(residual[non_source]), 0.90)),
        j25,
        j50,
        j75,
        rank_corr,
        float(np.mean(np.abs(ranks - reference_ranks) >= 0.10 * (len(values) - 1))),
        float(np.mean(truth.source_zone[mask] != reference.source_zone[mask])),
        contributions,
        a,
        j,
        h,
    )
    return summary, habitat


def _fixed_invariants(
    landscape: Landscape, edges: tuple[tuple[int, int, float], ...]
) -> dict[str, bool]:
    root = Path(__file__).resolve().parents[1].parents[1]
    commit_ok = _is_ancestor(root, SOURCE_IDENTITY["repository_commit"])
    parent_blobs = all(
        _git_blob(root, SOURCE_IDENTITY["repository_commit"], path) == SOURCE_IDENTITY[key]
        for key, path in PINNED_PATHS.items()
    )
    runtime_blobs = all(
        _git_blob(root, "HEAD", path) == SOURCE_IDENTITY[key] for key, path in PINNED_PATHS.items()
    )
    return {
        "frozen_repository_commit_reconciled": commit_ok,
        "frozen_parent_source_blobs_reconciled": parent_blobs,
        "frozen_runtime_source_blobs_reconciled": runtime_blobs,
        "landscape_counts": int(landscape.passable.sum()) == 5225
        and int((~landscape.passable).sum()) == 823
        and int((landscape.source_zone != "").sum()) == 81,
        "graph_edge_count": len(edges) == 10120,
        "finite_positive_edges": bool(np.isfinite([e[2] for e in edges]).all())
        and bool(np.all(np.asarray([e[2] for e in edges]) > 0.0)),
    }


def _git_blob(root: Path, ref: str, path: str) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", f"{ref}:{path}"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return ""


def _is_ancestor(root: Path, ref: str) -> bool:
    try:
        return (
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", ref, "HEAD"], cwd=root, check=False
            ).returncode
            == 0
        )
    except OSError:
        return False


def run_goal006(config: Goal006Config = DEFAULT_CONFIG) -> Goal006Result:
    landscape = build_landscape()
    edges = passable_edges(landscape)
    seeds = spawn_seed_records(config)
    invariants = _fixed_invariants(landscape, edges)
    original_costs = np.asarray([edge[2] for edge in edges], dtype=np.float64)
    geom = float(np.exp(np.mean(np.log(original_costs))))
    cost_summary: tuple[dict[str, object], ...] = tuple(
        {
            "eta": eta,
            "geometric_mean": float(np.exp(np.mean(np.log([e[2] for e in transformed])))),
            "minimum": min(e[2] for e in transformed),
            "maximum": max(e[2] for e in transformed),
            "ratio_max_min": max(e[2] for e in transformed) / min(e[2] for e in transformed),
            "exact_eta_one": eta == 1.0 and transformed == edges,
        }
        for eta in config.etas
        for transformed in [transform_edge_costs(edges, eta)]
    )
    summaries: list[ReplicateSummary] = []
    habitat_values: dict[tuple[float, str], list[float]] = {}
    representative: list[dict[str, object]] = []
    eta1_arrivals: list[NDArray[np.float64]] = []
    t50s: list[float] = []
    representative_index = 29 if config.replicates > 29 else config.replicates - 1
    process_reachable = True
    process_water_infinite = True
    process_source_zero = True
    paired_shock_reuse = True
    all_habitat = {"corridor", "low_quality_matrix", "high_quality_patch", "medium_quality"}
    for seed in seeds:
        _, truths = compute_paired_spreads(
            landscape, rng=generator_from_seed_record(seed), etas=config.etas
        )
        by_eta = {truth.eta: truth for truth in truths}
        reference = by_eta[1.0]
        paired_shock_reuse &= all(
            np.array_equal(truth.edge_shocks, reference.edge_shocks) for truth in truths
        )
        process_reachable &= all(
            bool(truth.reachable[landscape.passable].all()) for truth in truths
        )
        process_water_infinite &= all(
            bool(np.isinf(truth.arrival[~landscape.passable]).all()) for truth in truths
        )
        process_source_zero &= all(
            bool((truth.arrival[landscape.source_zone != ""] == 0.0).all()) for truth in truths
        )
        eta1_arrivals.append(reference.arrival)
        t50s.append(
            float(np.quantile(reference.arrival[landscape.passable], 0.50, method="higher"))
        )
        for truth in truths:
            summary, habitat = _summarize_pair(
                landscape, truth.eta, seed.replicate_index, truth, reference, len(edges)
            )
            summaries.append(summary)
            for name, value in habitat.items():
                habitat_values.setdefault((truth.eta, name), []).append(value)
            if seed.replicate_index == representative_index:
                representative.extend(
                    {
                        "replicate_index": seed.replicate_index,
                        "eta": truth.eta,
                        "cell_id": int(row * landscape.cols + col),
                        "row": int(row),
                        "col": int(col),
                        "arrival": float(truth.arrival[row, col]),
                        "reference_arrival": float(reference.arrival[row, col]),
                        "source_zone": str(truth.source_zone[row, col]),
                    }
                    for row, col in np.argwhere(landscape.passable)
                )
    spatial: list[SpatialEffectSummary] = []
    for eta in config.etas:
        rows = tuple(row for row in summaries if row.eta == eta)
        h = habitat_values
        spatial.append(
            SpatialEffectSummary(
                eta,
                *_quantile_triplet([row.A for row in rows]),
                *_quantile_triplet([row.J for row in rows]),
                *_quantile_triplet([row.H for row in rows]),
                float(np.median([row.median_abs_aligned_log_residual for row in rows])),
                float(np.median([row.t50 for row in rows])),
                int(sum(row.A >= 0.05 and row.J >= 0.05 for row in rows)),
                int(sum(row.H >= 0.0 if eta < 1 else row.H <= 0.0 for row in rows)),
                float(np.median(h[(eta, "corridor")]) - np.median(h[(eta, "low_quality_matrix")])),
                float(
                    np.median(h[(eta, "high_quality_patch")])
                    - np.median(h[(eta, "low_quality_matrix")])
                ),
                float(
                    np.median(h[(eta, "water_adjacent_low_quality_matrix")])
                    - np.median(h[(eta, "non_water_adjacent_low_quality_matrix")])
                ),
            )
        )
    deterministic = compute_spread(landscape).arrival[landscape.passable]
    stochastic_median = np.median(np.stack(eta1_arrivals)[:, landscape.passable], axis=0)
    diagnostics: dict[str, object] = {
        "eta_one_median_of_cell_stochastic_median": float(np.median(stochastic_median)),
        "eta_one_deterministic_stochastic_median_correlation": float(
            np.corrcoef(deterministic, stochastic_median)[0, 1]
        ),
        "eta_one_temporal_scale_ratio": float(
            np.quantile(stochastic_median, 0.50, method="higher")
            / np.quantile(deterministic, 0.50, method="higher")
        ),
        "eta_one_t50_sd": float(np.std(t50s, ddof=1)),
        "representative_index": representative_index,
        "representative_t50": t50s[representative_index],
        "original_geometric_mean": geom,
        "max_transformed_cost_ratio": max(
            float(cast(float, row["ratio_max_min"])) for row in cost_summary
        ),
    }
    invariants.update(
        _reconciliation_invariants(
            diagnostics, cost_summary, summaries, seeds, landscape, config.is_production
        )
    )
    invariants.update(
        {
            "paired_shock_reuse": paired_shock_reuse,
            "all_passable_reachable": process_reachable,
            "water_infinite": process_water_infinite,
            "source_zero": process_source_zero,
        }
    )
    outcome = classify_outcome(invariants, diagnostics, tuple(spatial), cost_summary)
    cell_summary = tuple(
        {
            "eta": eta,
            "habitat_class": habitat,
            "median_aligned_log_residual": float(np.median(values)),
            "p05_aligned_log_residual": float(np.quantile(values, 0.05)),
            "p95_aligned_log_residual": float(np.quantile(values, 0.95)),
            "cell_summary_scope": (
                "replicate-level median residual by habitat, not pooled decision data"
            ),
        }
        for (eta, habitat), values in sorted(habitat_values.items())
        if habitat in all_habitat
    )
    return Goal006Result(
        config,
        landscape,
        edges,
        seeds,
        cost_summary,
        tuple(summaries),
        tuple(spatial),
        cell_summary,
        tuple(representative),
        invariants,
        diagnostics,
        outcome,
    )


def _quantile_triplet(values: list[float]) -> tuple[float, float, float]:
    return (
        float(np.median(values)),
        float(np.quantile(values, 0.05)),
        float(np.quantile(values, 0.95)),
    )


def _reconciliation_invariants(
    diagnostics: dict[str, object],
    costs: tuple[dict[str, object], ...],
    summaries: list[ReplicateSummary],
    seeds: tuple[SeedRecord, ...],
    landscape: Landscape,
    production: bool,
) -> dict[str, bool]:
    tol = 1e-10

    def close(diagnostic_name: str, frozen_name: str) -> bool:
        return (not production) or (
            abs(float(cast(float, diagnostics[diagnostic_name])) - FROZEN_GOAL003[frozen_name])
            <= tol
        )

    eta_one = [row for row in summaries if row.eta == 1.0]
    return {
        "eta_grid_complete": {row.eta for row in summaries} == set(ETA_VALUES)
        and len(summaries) == len(seeds) * len(ETA_VALUES),
        "seed_unique_ordered": len({(s.entropy, s.spawn_key) for s in seeds}) == len(seeds)
        and tuple(s.replicate_index for s in seeds) == tuple(range(len(seeds))),
        "seed_state_replayable": all(
            np.array_equal(
                generator_from_seed_record(s).exponential(5),
                generator_from_seed_record(s).exponential(5),
            )
            for s in seeds
        ),
        "eta_one_edge_exact": all(bool(row["exact_eta_one"]) for row in costs if row["eta"] == 1.0),
        "all_reachable_and_finite": all(np.isfinite(row.t50) and row.t50 > 0.0 for row in summaries)
        and int(landscape.passable.sum()) == 5225,
        "eta_one_goal003_median_reconciled": close(
            "eta_one_median_of_cell_stochastic_median", "median_of_cell_stochastic_median"
        ),
        "eta_one_goal003_correlation_reconciled": close(
            "eta_one_deterministic_stochastic_median_correlation",
            "deterministic_stochastic_median_correlation",
        ),
        "eta_one_goal003_scale_reconciled": close(
            "eta_one_temporal_scale_ratio", "temporal_scale_ratio"
        ),
        "eta_one_goal003_t50_sd_reconciled": close("eta_one_t50_sd", "t50_sd"),
        "representative_t50_reconciled": (not production)
        or (
            int(cast(int, diagnostics["representative_index"])) == 29
            and close("representative_t50", "representative_t50")
        ),
        "eta_one_replication_count": len(eta_one) == len(seeds),
    }


def classify_outcome(
    invariants: dict[str, bool],
    diagnostics: dict[str, object],
    spatial: tuple[SpatialEffectSummary, ...],
    costs: tuple[dict[str, object], ...],
) -> str:
    if not all(invariants.values()):
        return "implementation_blocked"
    eta_one_t50 = next(row.median_t50 for row in spatial if row.eta == 1.0)
    t50_pathological = any(
        not isfinite(float(row.median_t50))
        or not (0.25 * eta_one_t50 <= row.median_t50 <= 4.0 * eta_one_t50)
        for row in spatial
    )
    if float(cast(float, diagnostics["max_transformed_cost_ratio"])) > 100.0 or t50_pathological:
        return "resistance_contrast_pathological"
    by_eta = {row.eta: row for row in spatial}
    adjacent = [by_eta[0.5], by_eta[1.5]]
    passes = [row.median_A >= 0.05 and row.median_J >= 0.05 for row in adjacent]
    if not any(passes):
        return "resistance_contrast_effectively_global_rate_only"
    signs = [adjacent[0].median_H >= 0.0, adjacent[1].median_H <= 0.0]
    consistency = [adjacent[0].consistency_count >= 80, adjacent[1].consistency_count >= 80]
    directional = [adjacent[0].expected_sign_count >= 80, adjacent[1].expected_sign_count >= 80]
    if not all(passes) or not all(signs) or not all(consistency) or not all(directional):
        return "resistance_contrast_spatial_signal_asymmetric"
    return "advance_to_joint_rho_eta_recovery"


# Friendly downstream names.
build_ensemble = run_goal006
run_benchmark = run_goal006
