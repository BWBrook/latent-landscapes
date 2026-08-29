"""Ecological parameterization and pilot design for Arc 2A."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from math import log2, sqrt
from pathlib import Path
from statistics import median
from typing import Any

import matplotlib as mpl
import numpy as np
from numpy.typing import NDArray
from scipy.stats import qmc  # type: ignore[import-untyped]

from latent_landscapes.goal001.landscape import Landscape, build_landscape
from latent_landscapes.goal001.spread import passable_edges
from latent_landscapes.goal002.calibration import wilson_interval
from latent_landscapes.goal006.spread import geometric_mean_cost, transform_edge_costs

mpl.use("Agg")
mpl.rcParams["svg.hashsalt"] = "latent-landscapes-goal038"
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("artifacts/goal038_arc2a_design_freeze")
EXPECTED_FILES = (
    "eta_ecological_translation.csv",
    "arc2a_pilot_truths.csv",
    "arc1_reference_points.csv",
    "compute_budget.csv",
    "summary.json",
    "review.md",
    "eta_cost_contrasts.svg",
    "eta_cost_maps.svg",
    "arc2a_pilot_design.svg",
)
ETA_REVIEW_VALUES = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
ETA_MAP_VALUES = (0.25, 0.75, 1.0, 2.0)
SOBOL_SCRAMBLE_SEED = 20260829
SOBOL_POINT_COUNT = 16
CALIBRATION_HISTORIES_PER_TRUTH = 250
VALIDATION_HISTORIES_PER_TRUTH = 250
GOAL023_TRUTH_COUNT = 4
GOAL023_WALL_MINUTES = 27.0 + 20.0 / 60.0
PLANNING_UPLIFT = 1.25


@dataclass(frozen=True, slots=True)
class EtaTranslation:
    eta: float
    geometric_mean_cost: float
    dry_corridor_cost: float
    dry_patch_cost: float
    dry_medium_cost: float
    dry_matrix_cost: float
    water_adjacent_matrix_cost: float
    patch_to_corridor_ratio: float
    medium_to_corridor_ratio: float
    matrix_to_corridor_ratio: float
    water_adjacent_to_dry_matrix_ratio: float
    global_max_to_min_ratio: float


@dataclass(frozen=True, slots=True)
class PilotTruth:
    point_id: str
    design_role: str
    unit_rho: float | None
    unit_eta: float | None
    unit_p: float | None
    log2_rho: float
    rho: float
    eta: float
    p: float


@dataclass(frozen=True, slots=True)
class ReferencePoint:
    point_id: str
    rho: float
    eta: float
    p: float
    direct_result: str
    source_goal: str


@dataclass(frozen=True, slots=True)
class ComputeBudget:
    stage: str
    sobol_truth_count: int
    diagnostic_truth_count: int
    enrichment_truth_count: int
    total_new_truth_count: int
    calibration_history_count: int
    validation_history_count: int
    total_history_count: int
    history_scaled_mac_minutes: float
    planning_upper_mac_minutes: float
    estimate_scope: str


@dataclass(frozen=True, slots=True)
class Goal038Result:
    landscape: Landscape
    eta_translation: tuple[EtaTranslation, ...]
    pilot_truths: tuple[PilotTruth, ...]
    diagnostic_truth: PilotTruth
    reference_points: tuple[ReferencePoint, ...]
    compute_budget: tuple[ComputeBudget, ...]
    invariants: dict[str, bool]
    outcome: str


def _edge_context(landscape: Landscape, source: int, target: int) -> tuple[tuple[str, str], int]:
    source_row, source_col = divmod(source, landscape.cols)
    target_row, target_col = divmod(target, landscape.cols)
    habitats = tuple(
        sorted(
            (
                str(landscape.habitat_class[source_row, source_col]),
                str(landscape.habitat_class[target_row, target_col]),
            )
        )
    )
    water_neighbors = int(landscape.water_neighbor_count[source_row, source_col]) + int(
        landscape.water_neighbor_count[target_row, target_col]
    )
    return (habitats[0], habitats[1]), water_neighbors


def _edge_category(landscape: Landscape, source: int, target: int) -> str | None:
    habitats, water_neighbors = _edge_context(landscape, source, target)
    if habitats == ("corridor", "corridor") and water_neighbors == 0:
        return "dry_corridor"
    if habitats == ("high_quality_patch", "high_quality_patch") and water_neighbors == 0:
        return "dry_patch"
    if habitats == ("medium_quality", "medium_quality") and water_neighbors == 0:
        return "dry_medium"
    if habitats == ("low_quality_matrix", "low_quality_matrix"):
        return "water_adjacent_matrix" if water_neighbors > 0 else "dry_matrix"
    return None


def build_eta_translation(
    landscape: Landscape, etas: tuple[float, ...] = ETA_REVIEW_VALUES
) -> tuple[EtaTranslation, ...]:
    """Express eta as movement-cost contrasts on the reference graph."""
    edges = passable_edges(landscape)
    rows: list[EtaTranslation] = []
    for eta in etas:
        transformed = transform_edge_costs(edges, eta)
        categories: dict[str, list[float]] = {
            "dry_corridor": [],
            "dry_patch": [],
            "dry_medium": [],
            "dry_matrix": [],
            "water_adjacent_matrix": [],
        }
        for source, target, cost in transformed:
            category = _edge_category(landscape, source, target)
            if category is not None:
                categories[category].append(cost)
        if any(not values for values in categories.values()):
            raise ValueError("reference landscape lacks a required ecological edge category")
        corridor = float(median(categories["dry_corridor"]))
        patch = float(median(categories["dry_patch"]))
        medium = float(median(categories["dry_medium"]))
        matrix = float(median(categories["dry_matrix"]))
        water_matrix = float(median(categories["water_adjacent_matrix"]))
        all_costs = [cost for _, _, cost in transformed]
        rows.append(
            EtaTranslation(
                eta=eta,
                geometric_mean_cost=geometric_mean_cost(transformed),
                dry_corridor_cost=corridor,
                dry_patch_cost=patch,
                dry_medium_cost=medium,
                dry_matrix_cost=matrix,
                water_adjacent_matrix_cost=water_matrix,
                patch_to_corridor_ratio=patch / corridor,
                medium_to_corridor_ratio=medium / corridor,
                matrix_to_corridor_ratio=matrix / corridor,
                water_adjacent_to_dry_matrix_ratio=water_matrix / matrix,
                global_max_to_min_ratio=max(all_costs) / min(all_costs),
            )
        )
    return tuple(rows)


def build_local_cost_map(landscape: Landscape, eta: float) -> NDArray[np.float64]:
    """Return median incident edge cost relative to a dry corridor edge."""
    edges = passable_edges(landscape)
    transformed = transform_edge_costs(edges, eta)
    incident: list[list[float]] = [[] for _ in range(landscape.cell_count)]
    corridor_costs: list[float] = []
    for source, target, cost in transformed:
        incident[source].append(cost)
        incident[target].append(cost)
        if _edge_category(landscape, source, target) == "dry_corridor":
            corridor_costs.append(cost)
    if not corridor_costs:
        raise ValueError("reference landscape lacks dry corridor edges")
    corridor = float(median(corridor_costs))
    values = np.full(landscape.cell_count, np.nan, dtype=np.float64)
    for node, costs in enumerate(incident):
        if costs:
            values[node] = float(median(costs)) / corridor
    return values.reshape(landscape.shape)


def generate_pilot_truths(seed: int = SOBOL_SCRAMBLE_SEED) -> tuple[PilotTruth, ...]:
    """Generate the reproducible 16-point continuous Arc 2A pilot."""
    engine = qmc.Sobol(d=3, scramble=True, seed=seed)
    unit = np.asarray(engine.random_base2(m=4), dtype=np.float64)
    rows: list[PilotTruth] = []
    for index, (unit_rho, unit_eta, unit_p) in enumerate(unit, start=1):
        transformed_log_rho = -1.0 + 2.0 * float(unit_rho)
        rows.append(
            PilotTruth(
                point_id=f"S{index:02d}",
                design_role="sobol_pilot",
                unit_rho=float(unit_rho),
                unit_eta=float(unit_eta),
                unit_p=float(unit_p),
                log2_rho=transformed_log_rho,
                rho=float(2.0**transformed_log_rho),
                eta=0.25 + 1.75 * float(unit_eta),
                p=0.35 + 0.50 * float(unit_p),
            )
        )
    return tuple(rows)


def no_resistance_diagnostic() -> PilotTruth:
    return PilotTruth(
        point_id="D00",
        design_role="no_resistance_diagnostic",
        unit_rho=None,
        unit_eta=None,
        unit_p=None,
        log2_rho=0.0,
        rho=1.0,
        eta=0.0,
        p=0.65,
    )


def arc1_reference_points() -> tuple[ReferencePoint, ...]:
    """Return accepted anchors to overlay, not rerun."""
    return (
        ReferencePoint(
            "central_joint",
            1.0,
            1.0,
            0.65,
            "central three-parameter positive control passed after topology refinement",
            "Goal 022",
        ),
        ReferencePoint(
            "slower_spread",
            0.7578582832551991,
            1.0,
            0.65,
            "point recovery retained but detection precision was inadequate",
            "Goal 023",
        ),
        ReferencePoint(
            "spread_detection_transition",
            0.8705505632961241,
            1.0,
            0.65,
            "spread-detection precision transition remained below the central case",
            "Goal 025",
        ),
        ReferencePoint(
            "weaker_resistance",
            1.0,
            0.5,
            0.65,
            "weak resistance could not be reliably distinguished from zero",
            "Goal 023",
        ),
        ReferencePoint(
            "resistance_transition",
            1.0,
            0.75,
            0.65,
            "resistance was distinguished from zero under the reference design",
            "Goal 024",
        ),
        ReferencePoint(
            "poorer_detection",
            1.0,
            1.0,
            0.45,
            "joint recovery retained acceptable precision",
            "Goal 023",
        ),
    )


def build_compute_budget() -> tuple[ComputeBudget, ...]:
    """Return cumulative workload counts and a transparent timing proxy."""
    histories_per_truth = CALIBRATION_HISTORIES_PER_TRUTH + VALIDATION_HISTORIES_PER_TRUTH
    stages = (
        ("initial_16_plus_diagnostic", 16, 1, 0),
        ("nested_32_plus_diagnostic", 32, 1, 0),
        ("maximum_32_plus_diagnostic_plus_8_enrichment", 32, 1, 8),
    )
    history_minutes = GOAL023_WALL_MINUTES / (GOAL023_TRUTH_COUNT * histories_per_truth)
    rows: list[ComputeBudget] = []
    for stage, sobol_count, diagnostic_count, enrichment_count in stages:
        truth_count = sobol_count + diagnostic_count + enrichment_count
        calibration_count = truth_count * CALIBRATION_HISTORIES_PER_TRUTH
        validation_count = truth_count * VALIDATION_HISTORIES_PER_TRUTH
        total_histories = calibration_count + validation_count
        scaled_minutes = history_minutes * total_histories
        rows.append(
            ComputeBudget(
                stage=stage,
                sobol_truth_count=sobol_count,
                diagnostic_truth_count=diagnostic_count,
                enrichment_truth_count=enrichment_count,
                total_new_truth_count=truth_count,
                calibration_history_count=calibration_count,
                validation_history_count=validation_count,
                total_history_count=total_histories,
                history_scaled_mac_minutes=scaled_minutes,
                planning_upper_mac_minutes=scaled_minutes * PLANNING_UPLIFT,
                estimate_scope=(
                    "workload-scaled from Goal 023's measured 4-truth, 27m20s Mac run; "
                    "not a benchmark of the future Arc 2A runner"
                ),
            )
        )
    return tuple(rows)


def _sobol_strata_complete(points: tuple[PilotTruth, ...], field: str) -> bool:
    values = [getattr(point, field) for point in points]
    if any(value is None for value in values):
        return False
    strata = sorted(min(15, int(float(value) * 16.0)) for value in values)
    return strata == list(range(16))


def run_goal038() -> Goal038Result:
    landscape = build_landscape()
    eta_rows = build_eta_translation(landscape)
    pilot = generate_pilot_truths()
    diagnostic = no_resistance_diagnostic()
    references = arc1_reference_points()
    budget = build_compute_budget()
    geometric_means = np.asarray([row.geometric_mean_cost for row in eta_rows])
    matrix_ratios = np.asarray([row.matrix_to_corridor_ratio for row in eta_rows])
    ids = {row.point_id for row in pilot}
    invariants = {
        "reference_landscape_reconciled": landscape.shape == (72, 84)
        and int(landscape.passable.sum()) == 5225
        and len(passable_edges(landscape)) == 10120,
        "eta_zero_removes_contrast": all(
            abs(value - 1.0) < 1e-12
            for value in (
                eta_rows[0].patch_to_corridor_ratio,
                eta_rows[0].medium_to_corridor_ratio,
                eta_rows[0].matrix_to_corridor_ratio,
                eta_rows[0].water_adjacent_to_dry_matrix_ratio,
                eta_rows[0].global_max_to_min_ratio,
            )
        ),
        "geometric_mean_preserved": bool(
            np.allclose(geometric_means, geometric_means[0], rtol=0.0, atol=1e-12)
        ),
        "matrix_contrast_increases": bool(np.all(np.diff(matrix_ratios) > 0.0)),
        "sobol_count_and_ids": len(pilot) == SOBOL_POINT_COUNT and len(ids) == len(pilot),
        "sobol_marginal_strata_complete": all(
            _sobol_strata_complete(pilot, field) for field in ("unit_rho", "unit_eta", "unit_p")
        ),
        "factor_bounds": all(
            0.5 <= row.rho <= 2.0 and 0.25 <= row.eta <= 2.0 and 0.35 <= row.p <= 0.85
            for row in pilot
        ),
        "diagnostic_separate": diagnostic.eta == 0.0 and all(row.eta > 0.0 for row in pilot),
        "reference_points_are_external": all(
            row.point_id not in ids and row.source_goal.startswith("Goal ") for row in references
        ),
        "initial_history_accounting": budget[0].total_new_truth_count == 17
        and budget[0].total_history_count == 8500,
    }
    outcome = (
        "ready_for_human_arc2a_design_review"
        if all(invariants.values())
        else "arc2a_design_pack_invalid"
    )
    return Goal038Result(
        landscape=landscape,
        eta_translation=eta_rows,
        pilot_truths=pilot,
        diagnostic_truth=diagnostic,
        reference_points=references,
        compute_budget=budget,
        invariants=invariants,
        outcome=outcome,
    )


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _save_figure(figure: Figure, path: Path) -> None:
    figure.savefig(path, format="svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(figure)


def _eta_contrast_figure(result: Goal038Result) -> Figure:
    rows = result.eta_translation
    etas = [row.eta for row in rows]
    figure, axes = plt.subplots(1, 3, figsize=(14.5, 4.2))
    axes[0].plot(etas, [row.patch_to_corridor_ratio for row in rows], marker="o", label="Patch")
    axes[0].plot(etas, [row.medium_to_corridor_ratio for row in rows], marker="o", label="Medium")
    axes[0].plot(etas, [row.matrix_to_corridor_ratio for row in rows], marker="o", label="Matrix")
    axes[0].set_yscale("log", base=2)
    axes[0].set_xlabel("Resistance contrast eta")
    axes[0].set_ylabel("Expected edge cost / dry corridor cost")
    axes[0].set_title("Habitat movement contrast")
    axes[0].legend(frameon=False)

    axes[1].plot(
        etas,
        [row.water_adjacent_to_dry_matrix_ratio for row in rows],
        color="#007f5f",
        marker="o",
    )
    axes[1].set_xlabel("Resistance contrast eta")
    axes[1].set_ylabel("Water-adjacent matrix / dry matrix cost")
    axes[1].set_title("Additional water-edge penalty")

    axes[2].plot(
        etas,
        [row.global_max_to_min_ratio for row in rows],
        color="#b23a48",
        marker="o",
    )
    axes[2].set_yscale("log", base=2)
    axes[2].set_xlabel("Resistance contrast eta")
    axes[2].set_ylabel("Highest / lowest edge cost")
    axes[2].set_title("Whole-landscape cost range")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.axvline(1.0, color="0.35", linestyle="--", linewidth=1)
    figure.suptitle(
        "Ecological meaning of eta: expected traversal-time weights before stochastic shocks",
        fontsize=13,
    )
    figure.tight_layout()
    return figure


def _eta_map_figure(result: Goal038Result) -> Figure:
    maps = [build_local_cost_map(result.landscape, eta) for eta in ETA_MAP_VALUES]
    finite = np.concatenate([values[np.isfinite(values)] for values in maps])
    norm = LogNorm(vmin=float(finite.min()), vmax=float(finite.max()))
    cmap = mpl.colormaps["viridis"].with_extremes(bad="#b7c4c8")
    figure, axes = plt.subplots(2, 2, figsize=(11.5, 8.4), constrained_layout=True)
    image = None
    by_eta = {row.eta: row for row in result.eta_translation}
    for axis, eta, values in zip(axes.flat, ETA_MAP_VALUES, maps, strict=True):
        image = axis.imshow(
            np.ma.masked_invalid(values), cmap=cmap, norm=norm, interpolation="none"
        )
        axis.set_title(
            f"eta={eta:g}: dry matrix {by_eta[eta].matrix_to_corridor_ratio:.2f}x corridor"
        )
        axis.set_xticks([])
        axis.set_yticks([])
    if image is None:
        raise RuntimeError("eta map figure has no panels")
    colorbar = figure.colorbar(image, ax=list(axes.flat), shrink=0.82)
    colorbar.set_label("Median incident edge cost / dry corridor edge cost")
    figure.suptitle(
        "How eta changes the spatial movement-cost surface (water shown grey)", fontsize=14
    )
    return figure


def _pilot_design_figure(result: Goal038Result) -> Figure:
    points = result.pilot_truths
    log_rho = np.asarray([row.log2_rho for row in points])
    eta = np.asarray([row.eta for row in points])
    detection = np.asarray([row.p for row in points])
    reference_log_rho = np.asarray([log2(row.rho) for row in result.reference_points])
    reference_eta = np.asarray([row.eta for row in result.reference_points])
    reference_detection = np.asarray([row.p for row in result.reference_points])
    figure, axes = plt.subplots(1, 3, figsize=(15.2, 4.7), constrained_layout=True)
    scatter0 = axes[0].scatter(log_rho, eta, c=detection, cmap="viridis", s=58, edgecolor="white")
    axes[0].scatter(
        reference_log_rho,
        reference_eta,
        marker="D",
        s=64,
        facecolors="none",
        edgecolors="#202020",
        linewidths=1.3,
        label="Accepted Arc 1 anchor",
    )
    axes[0].scatter(0.0, 0.0, marker="*", s=170, color="#d1495b", label="eta=0 diagnostic")
    axes[0].set_xlabel("log2 spread rate (rho)")
    axes[0].set_ylabel("Resistance contrast (eta)")
    axes[0].set_title("Spread x resistance")
    axes[0].legend(frameon=False, loc="upper left")
    figure.colorbar(scatter0, ax=axes[0], label="Per-visit detection p")

    scatter1 = axes[1].scatter(log_rho, detection, c=eta, cmap="plasma", s=58, edgecolor="white")
    axes[1].scatter(
        reference_log_rho,
        reference_detection,
        marker="D",
        s=64,
        facecolors="none",
        edgecolors="#202020",
        linewidths=1.3,
    )
    axes[1].set_xlabel("log2 spread rate (rho)")
    axes[1].set_ylabel("Per-visit detection p")
    axes[1].set_title("Spread x detection")
    figure.colorbar(scatter1, ax=axes[1], label="Resistance contrast eta")

    scatter2 = axes[2].scatter(eta, detection, c=log_rho, cmap="coolwarm", s=58, edgecolor="white")
    axes[2].scatter(
        reference_eta,
        reference_detection,
        marker="D",
        s=64,
        facecolors="none",
        edgecolors="#202020",
        linewidths=1.3,
    )
    axes[2].scatter(0.0, 0.65, marker="*", s=170, color="#d1495b")
    axes[2].set_xlabel("Resistance contrast (eta)")
    axes[2].set_ylabel("Per-visit detection p")
    axes[2].set_title("Resistance x detection")
    figure.colorbar(scatter2, ax=axes[2], label="log2 spread rate")
    for axis in axes:
        axis.grid(alpha=0.2)
    figure.suptitle(
        "Arc 2A initial design: 16 Sobol points, accepted anchors, and one diagnostic boundary",
        fontsize=14,
    )
    return figure


def _summary_payload(result: Goal038Result) -> dict[str, Any]:
    nominal_successes = round(0.95 * VALIDATION_HISTORIES_PER_TRUTH)
    coverage = wilson_interval(nominal_successes, VALIDATION_HISTORIES_PER_TRUTH)
    eta_by_value = {row.eta: row for row in result.eta_translation}
    return {
        "goal": "038-arc2a-ecological-parameterization-and-pilot-design",
        "outcome": result.outcome,
        "sobol_scramble_seed": SOBOL_SCRAMBLE_SEED,
        "continuous_pilot_truth_count": len(result.pilot_truths),
        "diagnostic_truth_count": 1,
        "factor_domains": {
            "log2_rho": [-1.0, 1.0],
            "rho": [0.5, 2.0],
            "eta": [0.25, 2.0],
            "p": [0.35, 0.85],
        },
        "factor_interpretation": {
            "rho": "0.5x to 2x the reference global spread-rate multiplier",
            "p_two_visit_detection": {
                "p_0.35": 1.0 - (1.0 - 0.35) ** 2,
                "p_0.65": 1.0 - (1.0 - 0.65) ** 2,
                "p_0.85": 1.0 - (1.0 - 0.85) ** 2,
            },
        },
        "eta_translation_highlights": {
            str(value): {
                "matrix_to_corridor_ratio": eta_by_value[value].matrix_to_corridor_ratio,
                "water_adjacent_to_dry_matrix_ratio": (
                    eta_by_value[value].water_adjacent_to_dry_matrix_ratio
                ),
                "global_max_to_min_ratio": eta_by_value[value].global_max_to_min_ratio,
            }
            for value in (0.25, 0.75, 1.0, 2.0)
        },
        "exploratory_monte_carlo": {
            "calibration_histories_per_truth": CALIBRATION_HISTORIES_PER_TRUTH,
            "validation_histories_per_truth": VALIDATION_HISTORIES_PER_TRUTH,
            "coverage_estimate_resolution": 1.0 / VALIDATION_HISTORIES_PER_TRUTH,
            "nominal_coverage_count": nominal_successes,
            "wilson_interval_at_nominal_count": [coverage.lower, coverage.upper],
            "binomial_standard_error_at_0_95": sqrt(0.95 * 0.05 / VALIDATION_HISTORIES_PER_TRUTH),
            "interpretation": (
                "adequate for exploratory operating-performance surfaces; selected final "
                "conditions may need larger ensembles"
            ),
        },
        "initial_compute_budget": asdict(result.compute_budget[0]),
        "invariants": result.invariants,
    }


def _review_markdown(result: Goal038Result) -> str:
    by_eta = {row.eta: row for row in result.eta_translation}
    initial = result.compute_budget[0]
    nominal_successes = round(0.95 * VALIDATION_HISTORIES_PER_TRUTH)
    coverage = wilson_interval(nominal_successes, VALIDATION_HISTORIES_PER_TRUTH)
    return f"""# Arc 2A ecological parameterization and pilot design review

## Decision

Outcome: `{result.outcome}`. No spread history, observation history, likelihood,
or inference ensemble was run. This pack asks whether the proposed design is
ecologically credible and proportionate enough to authorize production.

## What eta means here

`Eta` preserves the geometric mean edge cost but changes contrast. Relative to
a dry corridor edge, expected dry-matrix traversal cost is approximately:

- `{by_eta[0.25].matrix_to_corridor_ratio:.2f}x` at `eta = 0.25`;
- `{by_eta[0.75].matrix_to_corridor_ratio:.2f}x` at `eta = 0.75`;
- `{by_eta[1.0].matrix_to_corridor_ratio:.2f}x` at `eta = 1`; and
- `{by_eta[2.0].matrix_to_corridor_ratio:.2f}x` at `eta = 2`.

The `eta = 2` upper proposal also creates a
`{by_eta[2.0].global_max_to_min_ratio:.1f}x` ratio between the least and most
costly passable edges. Barry should decide whether that remains an ecologically
useful stress condition or is unnecessarily extreme. The separate `eta = 0`
cell removes all resistance contrast and remains a diagnostic boundary, not
part of the continuous surface.

`Rho = 0.5-2` spans half to twice the reference global spread rate. With two
visits per survey, `p = 0.35`, `0.65`, and `0.85` imply probabilities of at
least one detection, conditional on presence, of approximately `0.58`, `0.88`,
and `0.98`, respectively.

## Pilot design

The continuous pilot contains 16 unique scrambled Sobol points. Each factor
occupies all 16 one-dimensional strata exactly once. `Rho` is sampled uniformly
on its log2 scale; `eta` and `p` are sampled linearly. Six accepted Arc 1 points
are shown as open-diamond overlays and are not scheduled for full reruns.

## Workload and Monte Carlo precision

The first review stage contains 16 continuous truths plus one diagnostic truth,
or `{initial.total_history_count}` condition histories: 250 calibration and 250
independent validation histories at each truth. Scaling the accepted Goal 023
Mac timing by history count gives `{initial.history_scaled_mac_minutes:.0f}`
minutes; a deliberately conservative planning uplift gives
`{initial.planning_upper_mac_minutes:.0f}` minutes. These are workload proxies,
not a benchmark of the future runner. A timing probe remains mandatory, and
the shared integration bank should be constructed once across conditions.

With 250 validation histories, an observed nominal count of
`{nominal_successes}/250` has a Wilson interval of approximately
`{coverage.lower:.3f}-{coverage.upper:.3f}`. This is suitable for deciding
whether broad surfaces and transitions are worth pursuing, but selected final
conditions may need more replication for manuscript-level precision.

## Human decisions

1. Is the proposed `eta = 0.25-2` domain ecologically defensible after seeing
   the induced cost ratios and maps?
2. Retain `rho = 0.5-2` and `p = 0.35-0.85`?
3. Retain the existing 160 sites, six surveys, two visits, and zero false
   positives for this first map?
4. Authorize 16 Sobol truths plus the central no-resistance diagnostic, with a
   hard review before any extension to 32?
5. Build the runner for `deep-server`, subject to a reduced local timing probe?
"""


def write_review_bundle(
    result: Goal038Result, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {name: output_dir / name for name in EXPECTED_FILES}
    eta_rows = [asdict(row) for row in result.eta_translation]
    pilot_rows = [asdict(row) for row in (*result.pilot_truths, result.diagnostic_truth)]
    reference_rows = [asdict(row) for row in result.reference_points]
    budget_rows = [asdict(row) for row in result.compute_budget]
    _write_csv(paths["eta_ecological_translation.csv"], eta_rows, list(eta_rows[0]))
    _write_csv(paths["arc2a_pilot_truths.csv"], pilot_rows, list(pilot_rows[0]))
    _write_csv(paths["arc1_reference_points.csv"], reference_rows, list(reference_rows[0]))
    _write_csv(paths["compute_budget.csv"], budget_rows, list(budget_rows[0]))
    paths["summary.json"].write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["review.md"].write_text(_review_markdown(result), encoding="utf-8")
    _save_figure(_eta_contrast_figure(result), paths["eta_cost_contrasts.svg"])
    _save_figure(_eta_map_figure(result), paths["eta_cost_maps.svg"])
    _save_figure(_pilot_design_figure(result), paths["arc2a_pilot_design.svg"])
    unexpected = {path.name for path in output_dir.iterdir()} - set(EXPECTED_FILES)
    if unexpected:
        raise RuntimeError(f"unexpected Goal 038 artifact files: {sorted(unexpected)}")
    return tuple(paths[name] for name in EXPECTED_FILES)
