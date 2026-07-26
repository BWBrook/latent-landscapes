"""Canonical end-to-end Goal 001 benchmark orchestration."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from math import hypot, isfinite

import numpy as np

from .design import DesignSite, SamplingDesign, build_design, spawn_generators
from .landscape import Landscape, build_landscape
from .likelihood import (
    RATE_DOMAIN,
    HoldoutEvaluation,
    Interval,
    LikelihoodProfile,
    compare_holdout_log_scores,
    evaluate_holdout_mle,
    ideal_process_identifiable,
    profile_likelihood,
)
from .observations import DETECTION_PROBABILITY, Observation, generate_observations
from .spread import TRUE_RATE, SpreadTruth, compute_spread


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    landscape: Landscape
    truth: SpreadTruth
    design: SamplingDesign
    observations: tuple[Observation, ...]
    habitat_distances: dict[str, float]
    neutral_distances: dict[str, float]
    neutral_dmax: float
    habitat_training: LikelihoodProfile
    neutral_training: LikelihoodProfile
    habitat_all: LikelihoodProfile
    habitat_holdout: HoldoutEvaluation
    neutral_holdout: HoldoutEvaluation
    ideal_process_identifiable: bool
    invariants: dict[str, bool]
    comparison: str
    outcome: str

    @property
    def training_record_count(self) -> int:
        return sum(record.split == "training" for record in self.observations)

    @property
    def holdout_record_count(self) -> int:
        return sum(record.split == "holdout" for record in self.observations)

    @property
    def full_record_count(self) -> int:
        return len(self.observations)


def compute_neutral_distances(
    landscape: Landscape, sites: Sequence[DesignSite]
) -> tuple[dict[str, float], float]:
    source_cells = np.argwhere(landscape.source_zone != "")
    passable_cells = np.argwhere(landscape.passable)
    passable_distances = tuple(
        _nearest_source_distance(int(row), int(col), source_cells) for row, col in passable_cells
    )
    dmax = max(passable_distances)
    distances = {
        site.site_id: 120.0 * _nearest_source_distance(site.row, site.col, source_cells) / dmax
        for site in sites
    }
    return distances, dmax


def build_benchmark() -> BenchmarkResult:
    landscape = build_landscape()
    truth = compute_spread(landscape)
    centre_rng, holdout_rng, detection_rng = spawn_generators()
    design = build_design(landscape, centre_rng, holdout_rng)
    observations = generate_observations(design.sites, truth, detection_rng)
    training = tuple(record for record in observations if record.split == "training")
    holdout = tuple(record for record in observations if record.split == "holdout")

    habitat_distances = {
        site.site_id: float(truth.arrival[site.row, site.col]) for site in design.sites
    }
    neutral_distances, neutral_dmax = compute_neutral_distances(landscape, design.sites)
    habitat_training = profile_likelihood(
        model="habitat",
        scope="training",
        distances=habitat_distances,
        records=training,
        detection_probability=DETECTION_PROBABILITY,
    )
    neutral_training = profile_likelihood(
        model="neutral",
        scope="training",
        distances=neutral_distances,
        records=training,
        detection_probability=DETECTION_PROBABILITY,
    )
    habitat_holdout = evaluate_holdout_mle(
        model="habitat",
        training_profile=habitat_training,
        distances=habitat_distances,
        records=holdout,
        detection_probability=DETECTION_PROBABILITY,
    )
    neutral_holdout = evaluate_holdout_mle(
        model="neutral",
        training_profile=neutral_training,
        distances=neutral_distances,
        records=holdout,
        detection_probability=DETECTION_PROBABILITY,
    )
    comparison = compare_holdout_log_scores(
        habitat_holdout.log_score_range, neutral_holdout.log_score_range
    )

    # Full-data recovery is evaluated only after the frozen holdout comparison.
    habitat_all = profile_likelihood(
        model="habitat",
        scope="all",
        distances=habitat_distances,
        records=observations,
        detection_probability=DETECTION_PROBABILITY,
    )
    ideal = ideal_process_identifiable(
        tuple(float(value) for value in truth.arrival[truth.reachable])
    )
    invariants = _evaluate_invariants(landscape, truth, design, observations, ideal)
    outcome = classify_outcome(
        implementation_ok=all(invariants.values()),
        ideal_identifiable=ideal,
        support_components=habitat_all.support_components,
        comparison=comparison,
    )
    return BenchmarkResult(
        landscape=landscape,
        truth=truth,
        design=design,
        observations=observations,
        habitat_distances=habitat_distances,
        neutral_distances=neutral_distances,
        neutral_dmax=neutral_dmax,
        habitat_training=habitat_training,
        neutral_training=neutral_training,
        habitat_all=habitat_all,
        habitat_holdout=habitat_holdout,
        neutral_holdout=neutral_holdout,
        ideal_process_identifiable=ideal,
        invariants=invariants,
        comparison=comparison,
        outcome=outcome,
    )


def classify_outcome(
    *,
    implementation_ok: bool,
    ideal_identifiable: bool,
    support_components: tuple[Interval, ...],
    comparison: str,
) -> str:
    if not implementation_ok or not ideal_identifiable:
        return "implementation_blocked"
    if not any(component.contains(TRUE_RATE) for component in support_components):
        return "recovery_failure"
    if len(support_components) != 1 or (
        support_components[0].lower == RATE_DOMAIN[0]
        or support_components[0].upper == RATE_DOMAIN[1]
    ):
        return "design_limited"
    if comparison == "neutral_robustly_better":
        return "mechanism_not_supported"
    if comparison == "habitat_robustly_better":
        return "advance_goal002"
    return "rate_recoverable_mechanism_inconclusive"


def _nearest_source_distance(
    row: int, col: int, source_cells: np.ndarray[tuple[int, int], np.dtype[np.int64]]
) -> float:
    deltas = source_cells - np.asarray((row, col))
    return float(np.sqrt(np.square(deltas).sum(axis=1)).min())


def _evaluate_invariants(
    landscape: Landscape,
    truth: SpreadTruth,
    design: SamplingDesign,
    observations: tuple[Observation, ...],
    ideal: bool,
) -> dict[str, bool]:
    cluster_counts = Counter(cluster.stratum_index for cluster in design.clusters)
    holdout_counts = Counter(
        cluster.stratum_index for cluster in design.clusters if cluster.split == "holdout"
    )
    cluster_splits = {
        cluster_id: {site.split for site in design.sites if site.cluster_id == cluster_id}
        for cluster_id in {site.cluster_id for site in design.sites}
    }
    selected_separation = all(
        hypot(left.center_row - right.center_row, left.center_col - right.center_col) >= 8.0
        for index, left in enumerate(design.clusters)
        for right in design.clusters[index + 1 :]
    )
    positive_consistency = all(
        not record.detected or truth.arrival[record.row, record.col] <= record.time
        for record in observations
    )
    return {
        "landscape_reconciled": landscape.cell_count == 6048
        and int(landscape.passable.sum()) == 5225
        and int((~landscape.passable).sum()) == 823,
        "spread_reconciled": int(truth.reachable.sum()) == 5225
        and isfinite(float(truth.arrival[truth.reachable].max())),
        "source_reachability": bool(np.array_equal(landscape.source_reachable, landscape.passable)),
        "eligible_counts": Counter(candidate.stratum_index for candidate in design.eligible_centres)
        == {0: 202, 1: 122, 2: 154, 3: 157},
        "cluster_balance": cluster_counts == {0: 8, 1: 8, 2: 8, 3: 8},
        "holdout_balance": holdout_counts == {0: 2, 1: 2, 2: 2, 3: 2},
        "cluster_separation": selected_separation,
        "no_cluster_leakage": all(len(splits) == 1 for splits in cluster_splits.values()),
        "observation_count": len(observations) == 1920,
        "no_false_positives": positive_consistency,
        "ideal_process_identifiability": ideal,
    }
