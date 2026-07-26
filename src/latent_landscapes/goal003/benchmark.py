"""Canonical 100-replicate stochastic spread ensemble and compact summaries."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
from typing import cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.goal001.landscape import Landscape, build_landscape
from latent_landscapes.goal001.spread import SpreadTruth, compute_spread, passable_edges

from .spread import MASTER_SEED, StochasticSpreadTruth, compute_stochastic_spread

REVIEW_TIMES = (10.0, 20.0, 30.0, 40.0, 50.0, 60.0)
REFERENCE_TIMES = (70.0, 90.0, 110.0)
ALL_REVIEW_TIMES = REVIEW_TIMES + REFERENCE_TIMES
QUANTILE_LEVELS = (0.10, 0.25, 0.50, 0.75, 0.90)
THRESHOLDS = (0.25, 0.50, 0.75, 0.90)
REQUIRED_REPLICATES = 100


@dataclass(frozen=True, slots=True)
class Goal003Config:
    master_seed: int = MASTER_SEED
    replicates: int = REQUIRED_REPLICATES
    rho: float = 1.0

    def __post_init__(self) -> None:
        if self.replicates <= 0:
            raise ValueError("replicates must be positive")
        if not isfinite(self.rho) or self.rho <= 0.0:
            raise ValueError("rho must be finite and positive")

    @property
    def is_production(self) -> bool:
        return self == Goal003Config()


DEFAULT_CONFIG = Goal003Config()


@dataclass(frozen=True, slots=True)
class SeedRecord:
    replicate_index: int
    entropy: int
    spawn_key: tuple[int, ...]
    state_words: tuple[int, ...]

    def generator(self) -> np.random.Generator:
        sequence = np.random.SeedSequence(self.entropy, spawn_key=self.spawn_key)
        return np.random.Generator(np.random.PCG64(sequence))


@dataclass(frozen=True, slots=True)
class ReplicateSummary:
    replicate_index: int
    occupancy: tuple[float, ...]
    threshold_times: tuple[float, ...]
    maximum_arrival: float
    source_counts: tuple[tuple[str, int], ...]
    time_to_50: float


@dataclass(frozen=True, slots=True)
class CellQuantiles:
    q10: NDArray[np.float64]
    q25: NDArray[np.float64]
    q50: NDArray[np.float64]
    q75: NDArray[np.float64]
    q90: NDArray[np.float64]
    deterministic: NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class Goal003Result:
    config: Goal003Config
    landscape: Landscape
    deterministic: SpreadTruth
    seeds: tuple[SeedRecord, ...]
    replicate_summaries: tuple[ReplicateSummary, ...]
    arrivals: NDArray[np.float64]
    source_labels: tuple[NDArray[np.str_], ...]
    cell_quantiles: CellQuantiles
    habitat_summary: tuple[dict[str, object], ...]
    representatives: tuple[dict[str, object], ...]
    invariants: dict[str, bool]
    diagnostics: dict[str, object]
    outcome: str


def spawn_seed_records(config: Goal003Config = DEFAULT_CONFIG) -> tuple[SeedRecord, ...]:
    root = np.random.SeedSequence(config.master_seed)
    children = root.spawn(config.replicates)
    return tuple(
        SeedRecord(
            replicate_index=index,
            entropy=int(cast(int, child.entropy)),
            spawn_key=tuple(int(value) for value in child.spawn_key),
            state_words=tuple(int(value) for value in child.generate_state(4)),
        )
        for index, child in enumerate(children)
    )


def _summary(
    index: int,
    truth: StochasticSpreadTruth,
    landscape: Landscape,
) -> ReplicateSummary:
    values = truth.arrival[landscape.passable]
    occupancy = tuple(float(np.mean(values <= time)) for time in ALL_REVIEW_TIMES)
    thresholds = tuple(
        float(np.quantile(values, threshold, method="higher")) for threshold in THRESHOLDS
    )
    source_counts = tuple(
        (label, int(np.sum(truth.source_zone[landscape.passable] == label)))
        for label in sorted(set(str(x) for x in truth.source_zone[landscape.passable]))
    )
    return ReplicateSummary(
        replicate_index=index,
        occupancy=occupancy,
        threshold_times=thresholds,
        maximum_arrival=float(values.max()),
        source_counts=source_counts,
        time_to_50=thresholds[1],
    )


def _habitat_summary(
    landscape: Landscape, arrivals: NDArray[np.float64]
) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for habitat in sorted(str(x) for x in np.unique(landscape.habitat_class[landscape.passable])):
        mask = landscape.passable & (landscape.habitat_class == habitat)
        values = arrivals[:, mask]
        rows.append(
            {
                "habitat_class": habitat,
                "cells": int(mask.sum()),
                "arrival_q10": float(np.quantile(values, 0.10)),
                "arrival_q50": float(np.quantile(values, 0.50)),
                "arrival_q90": float(np.quantile(values, 0.90)),
                "ensemble_sd_mean": float(np.mean(np.std(values, axis=0))),
            }
        )
    return tuple(rows)


def _representatives(
    summaries: tuple[ReplicateSummary, ...], arrivals: NDArray[np.float64]
) -> tuple[dict[str, object], ...]:
    ordered = sorted(summaries, key=lambda x: (x.time_to_50, x.replicate_index))
    rows: list[dict[str, object]] = []
    for percentile in QUANTILE_LEVELS:
        rank = max(1, ceil(percentile * len(ordered)))
        selected = ordered[rank - 1]
        rows.append(
            {
                "selection_label": f"t50_rank_{int(percentile * 100):02d}",
                "percentile": percentile,
                "rank_one_based": rank,
                "replicate_index": selected.replicate_index,
                "time_to_50": selected.time_to_50,
                "arrival": arrivals[selected.replicate_index],
            }
        )
    return tuple(rows)


def build_ensemble(
    config: Goal003Config = DEFAULT_CONFIG,
    *,
    landscape: Landscape | None = None,
    deterministic: SpreadTruth | None = None,
) -> Goal003Result:
    landscape_value = landscape if landscape is not None else build_landscape()
    deterministic_value = (
        deterministic if deterministic is not None else compute_spread(landscape_value)
    )
    seeds = spawn_seed_records(config)
    replicate_truths: list[StochasticSpreadTruth] = []
    summaries: list[ReplicateSummary] = []
    for seed in seeds:
        truth = compute_stochastic_spread(landscape_value, seed.generator(), rho=config.rho)
        replicate_truths.append(truth)
        summaries.append(_summary(seed.replicate_index, truth, landscape_value))
    arrivals = np.stack([truth.arrival for truth in replicate_truths])
    source_labels = tuple(truth.source_zone for truth in replicate_truths)
    passable_arrivals = arrivals[:, landscape_value.passable]

    def grid_quantile(level: float) -> NDArray[np.float64]:
        grid = np.full(landscape_value.shape, np.nan, dtype=np.float64)
        grid[landscape_value.passable] = np.quantile(passable_arrivals, level, axis=0)
        return grid

    q = CellQuantiles(
        q10=grid_quantile(0.10),
        q25=grid_quantile(0.25),
        q50=grid_quantile(0.50),
        q75=grid_quantile(0.75),
        q90=grid_quantile(0.90),
        deterministic=np.where(landscape_value.passable, deterministic_value.arrival, np.nan),
    )
    passable = landscape_value.passable
    deterministic_values = deterministic_value.arrival[passable]
    stochastic_median = q.q50[passable]
    association = float(np.corrcoef(deterministic_values, stochastic_median)[0, 1])
    ratios = np.divide(
        stochastic_median,
        deterministic_values,
        out=np.full_like(stochastic_median, np.nan),
        where=deterministic_values > 0,
    )
    finite_ratios = ratios[np.isfinite(ratios)]
    deterministic_t50 = float(np.quantile(deterministic_values, 0.50, method="higher"))
    stochastic_t50 = float(np.quantile(stochastic_median, 0.50, method="higher"))
    diagnostics: dict[str, object] = {
        "deterministic_median_arrival": deterministic_t50,
        "stochastic_median_median_arrival": stochastic_t50,
        "temporal_scale_ratio": stochastic_t50 / deterministic_t50,
        "temporal_scale_ratio_q10": float(np.quantile(finite_ratios, 0.10)),
        "temporal_scale_ratio_q50": float(np.quantile(finite_ratios, 0.50)),
        "temporal_scale_ratio_q90": float(np.quantile(finite_ratios, 0.90)),
        "deterministic_stochastic_median_correlation": association,
        "variation_sd_t50": float(np.std([s.time_to_50 for s in summaries], ddof=1)),
        "old_horizon_saturated": bool(all(s.occupancy[-1] >= 0.999 for s in summaries)),
        "source_zone_counts": {
            label: int(np.sum(deterministic_value.source_zone[passable] == label))
            for label in sorted(set(str(x) for x in deterministic_value.source_zone[passable]))
        },
    }
    invariants = _invariants(
        landscape_value, deterministic_value, seeds, summaries, arrivals, source_labels
    )
    outcome = classify_outcome(invariants, diagnostics)
    return Goal003Result(
        config=config,
        landscape=landscape_value,
        deterministic=deterministic_value,
        seeds=seeds,
        replicate_summaries=tuple(summaries),
        arrivals=arrivals,
        source_labels=source_labels,
        cell_quantiles=q,
        habitat_summary=_habitat_summary(landscape_value, arrivals),
        representatives=_representatives(tuple(summaries), arrivals),
        invariants=invariants,
        diagnostics=diagnostics,
        outcome=outcome,
    )


def _invariants(
    landscape: Landscape,
    deterministic: SpreadTruth,
    seeds: tuple[SeedRecord, ...],
    summaries: list[ReplicateSummary],
    arrivals: NDArray[np.float64],
    source_labels: tuple[NDArray[np.str_], ...],
) -> dict[str, bool]:
    source_mask = landscape.source_zone != ""
    water_mask = ~landscape.passable
    return {
        "landscape_counts": int(landscape.passable.sum()) == 5225
        and int(water_mask.sum()) == 823
        and int(source_mask.sum()) == 81,
        "graph_edge_count": len(passable_edges(landscape)) == 10120,
        "deterministic_reachable": int(deterministic.reachable.sum()) == 5225,
        "replicate_count": len(summaries) == len(seeds),
        "seed_unique_ordered": len({(x.entropy, x.spawn_key) for x in seeds}) == len(seeds)
        and tuple(x.replicate_index for x in seeds) == tuple(range(len(seeds))),
        "finite_passable_arrivals": bool(np.isfinite(arrivals[:, landscape.passable]).all()),
        "water_infinite": bool(np.isinf(arrivals[:, water_mask]).all()),
        "source_zero": bool((arrivals[:, source_mask] == 0.0).all()),
        "nonzero_variation": bool(np.std(arrivals[:, landscape.passable], axis=0).max() > 0.0),
        "source_provenance": bool(
            all(np.all(labels[landscape.passable] != "") for labels in source_labels)
        ),
        "occupancy_nondecreasing": bool(
            all(
                all(
                    left <= right
                    for left, right in zip(summary.occupancy, summary.occupancy[1:], strict=False)
                )
                for summary in summaries
            )
        ),
        "source_contributions_sum": bool(
            all(sum(count for _, count in summary.source_counts) == 5225 for summary in summaries)
        ),
        "rho_scaling": bool(
            np.array_equal(
                compute_stochastic_spread(landscape, seeds[0].generator(), rho=2.0).arrival,
                arrivals[0] / 2.0,
            )
        ),
        "seed_replay": bool(
            np.array_equal(
                compute_stochastic_spread(landscape, seeds[0].generator()).arrival,
                arrivals[0],
            )
        ),
    }


def classify_outcome(invariants: dict[str, bool], diagnostics: dict[str, object]) -> str:
    if not all(invariants.values()):
        return "implementation_blocked"
    if float(cast(float, diagnostics["deterministic_stochastic_median_correlation"])) < 0.5:
        return "reject_process_formulation"
    if (
        bool(diagnostics["old_horizon_saturated"])
        or float(cast(float, diagnostics["temporal_scale_ratio"])) < 0.8
    ):
        return "time_scale_review_required"
    return "approve_stochastic_process_for_inference"


run_goal003 = build_ensemble
