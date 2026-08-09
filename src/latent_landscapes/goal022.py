"""Diagnose split rho-eta support under grid and integration-bank changes."""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from numpy.typing import NDArray

from latent_landscapes.goal002.calibration import (
    CutoffResult,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal004.likelihood import MLE_TOLERANCE, HistoryRecordLike
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal007.likelihood import joint_category_weights
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal019 import PROBABILITY_GRID, RHO_GRID
from latent_landscapes.goal021 import (
    DEFAULT_CONFIG as GOAL021_CONFIG,
)
from latent_landscapes.goal021 import (
    TRUTH_ETA,
    TRUTH_PROBABILITY,
    TRUTH_RHO,
    ThreeParameterProfile,
    summarize_support,
    three_parameter_profile,
)
from latent_landscapes.goal021 import (
    classify_outcome as classify_condition,
)

COARSE_ETA_GRID = GOAL021_CONFIG.etas
REFINED_ETA_GRID = tuple(float(value / 8) for value in range(21))
BANK_VARIANTS = ("full", "first_half", "second_half")
GRID_VARIANTS = ("coarse", "refined")
ADVANCE = "advance_to_cross_truth_three_parameter_benchmark"
SUPPORT_LIMITED = "three_parameter_support_design_limited"
GOAL021_CUTOFF = 57.041556096360864
EXPECTED_FILES = (
    "condition_summary.csv",
    "validation_topology.csv",
    "summary.json",
    "review.md",
    "rho_eta_topology.svg",
)


def _validate_grid(
    values: tuple[float, ...],
    *,
    positive: bool,
    interior: bool,
    name: str,
) -> None:
    array = np.asarray(values, dtype=np.float64)
    invalid_lower = (array <= 0.0).any() if positive else (array < 0.0).any()
    if (
        array.ndim != 1
        or len(array) == 0
        or not np.isfinite(array).all()
        or invalid_lower
        or (interior and (array >= 1.0).any())
        or (np.diff(array) <= 0.0).any()
    ):
        raise ValueError(f"{name} grid is invalid")


@dataclass(frozen=True, slots=True)
class Goal022Config:
    """Frozen topology diagnostic configuration."""

    master_seed: int = GOAL021_CONFIG.master_seed
    bank_size: int = GOAL021_CONFIG.bank_size
    calibration_replicates: int = GOAL021_CONFIG.calibration_replicates
    validation_replicates: int = GOAL021_CONFIG.validation_replicates
    calibration_rank_one_based: int = GOAL021_CONFIG.calibration_rank_one_based
    rhos: tuple[float, ...] = RHO_GRID
    coarse_etas: tuple[float, ...] = COARSE_ETA_GRID
    refined_etas: tuple[float, ...] = REFINED_ETA_GRID
    probabilities: tuple[float, ...] = PROBABILITY_GRID

    def __post_init__(self) -> None:
        if self.bank_size <= 0 or self.bank_size % 2:
            raise ValueError("integration bank size must be positive and even")
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("calibration and validation counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within calibration replicates")
        _validate_grid(self.rhos, positive=True, interior=False, name="rho")
        _validate_grid(self.coarse_etas, positive=False, interior=False, name="coarse eta")
        _validate_grid(self.refined_etas, positive=False, interior=False, name="refined eta")
        _validate_grid(
            self.probabilities,
            positive=True,
            interior=True,
            name="probability",
        )
        if not set(self.coarse_etas).issubset(self.refined_etas):
            raise ValueError("refined eta grid must embed every coarse eta exactly")
        for truth, values, label in (
            (TRUTH_RHO, self.rhos, "rho"),
            (TRUTH_ETA, self.coarse_etas, "coarse eta"),
            (TRUTH_ETA, self.refined_etas, "refined eta"),
            (TRUTH_PROBABILITY, self.probabilities, "probability"),
        ):
            if sum(value == truth for value in values) != 1:
                raise ValueError(f"{label} grid must contain its generating value once")

    @property
    def is_production(self) -> bool:
        return (
            self.master_seed == GOAL021_CONFIG.master_seed
            and self.bank_size == GOAL021_CONFIG.bank_size
            and self.calibration_replicates == 250
            and self.validation_replicates == 250
            and self.calibration_rank_one_based == 239
            and self.rhos == RHO_GRID
            and self.coarse_etas == COARSE_ETA_GRID
            and self.refined_etas == REFINED_ETA_GRID
            and self.probabilities == PROBABILITY_GRID
        )

    @property
    def goal011_config(self) -> goal011.Goal011Config:
        return goal011.Goal011Config(
            master_seed=self.master_seed,
            bank_size=self.bank_size,
            calibration_replicates=self.calibration_replicates,
            validation_replicates=self.validation_replicates,
            calibration_rank_one_based=self.calibration_rank_one_based,
        )


DEFAULT_CONFIG = Goal022Config()


def smoke_config() -> Goal022Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal022Config(
        bank_size=8,
        calibration_replicates=4,
        validation_replicates=4,
        calibration_rank_one_based=4,
        rhos=(0.5, 1.0, 2.0),
        coarse_etas=(0.5, 1.0, 1.5),
        refined_etas=(0.5, 0.75, 1.0, 1.25, 1.5),
        probabilities=(0.45, 0.65, 0.85),
    )


@dataclass(frozen=True, slots=True)
class ConditionSummary:
    condition_id: str
    bank_variant: str
    bank_draw_count: int
    grid_variant: str
    eta_grid_size: int
    cutoff: float
    coverage_success_count: int
    coverage: float
    coverage_lower: float
    coverage_upper: float
    connected_interior_count: int
    boundary_contact_count: int
    median_log_rho_error: float
    median_eta_error: float
    median_probability_error: float
    median_log_rho_width: float
    median_eta_width: float
    median_probability_width: float
    outcome: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    condition_id: str
    dataset_index: int
    truth_included: bool
    support_cell_count: int
    support_component_count: int
    support_boundary_contact: bool
    minimum_log_rho_error: float
    minimum_eta_error: float
    minimum_probability_error: float
    projected_log_rho_width: float
    projected_eta_width: float
    projected_probability_width: float


@dataclass(frozen=True, slots=True)
class TopologyRow:
    dataset_index: int
    full_coarse_components: int
    full_refined_components: int
    first_half_coarse_components: int
    first_half_refined_components: int
    second_half_coarse_components: int
    second_half_refined_components: int
    full_coarse_truth_included: bool
    full_refined_truth_included: bool
    full_coarse_support_cells: int
    full_refined_support_cells: int


@dataclass(frozen=True, slots=True)
class Goal022Result:
    config: Goal022Config
    conditions: tuple[ConditionSummary, ...]
    validation_topology: tuple[TopologyRow, ...]
    representative_dataset_index: int
    representative_coarse: ThreeParameterProfile
    representative_refined: ThreeParameterProfile
    representative_was_split: bool
    invariants: dict[str, bool]
    goal021_reconciled: bool
    outcome: str


def coarse_profile_from_refined(
    profile: ThreeParameterProfile,
    coarse_etas: Sequence[float],
) -> ThreeParameterProfile:
    """Extract an exact coarse-eta likelihood profile from a refined profile."""
    indices: list[int] = []
    for eta in coarse_etas:
        matches = np.flatnonzero(profile.etas == eta)
        if len(matches) != 1:
            raise ValueError("each coarse eta must occur exactly once in the refined profile")
        indices.append(int(matches[0]))
    etas = profile.etas[indices].copy()
    log_likelihoods = profile.log_likelihoods[indices].copy()
    maximum = float(log_likelihoods.max())
    mle_indices = tuple(
        (int(eta_index), int(rho_index), int(p_index))
        for eta_index, rho_index, p_index in np.argwhere(
            np.isclose(log_likelihoods, maximum, rtol=0.0, atol=MLE_TOLERANCE)
        )
    )
    return ThreeParameterProfile(
        etas=etas,
        rhos=profile.rhos.copy(),
        probabilities=profile.probabilities.copy(),
        log_likelihoods=log_likelihoods,
        maximum_log_likelihood=maximum,
        mle_indices=mle_indices,
        mle_cells=tuple(
            (
                float(profile.rhos[rho_index]),
                float(etas[eta_index]),
                float(profile.probabilities[p_index]),
            )
            for eta_index, rho_index, p_index in mle_indices
        ),
    )


def classify_outcome(
    *,
    invariants: dict[str, bool],
    goal021_reconciled: bool,
    refined_outcomes: tuple[str, str, str],
) -> str:
    """Classify the prespecified grid and bank-stability diagnosis."""
    if not goal021_reconciled:
        return "goal021_reconciliation_failed"
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if all(outcome == ADVANCE for outcome in refined_outcomes):
        return "coarse_eta_resolution_explains_split_supports"
    if all(outcome == SUPPORT_LIMITED for outcome in refined_outcomes):
        return "rho_eta_ambiguity_persists_after_refinement"
    return "integration_bank_sensitivity_unresolved"


def run_goal022(config: Goal022Config = DEFAULT_CONFIG) -> Goal022Result:
    """Run the calibrated topology diagnostic."""
    fixed = goal011.build_fixed_inputs()
    manifest = goal011.spawn_seed_manifest(config.goal011_config)
    bank = goal007.build_integration_bank(fixed, manifest.integration_bank, config.refined_etas)
    weights = _bank_weights(bank.arrivals, config)
    calibration_statistics: dict[str, list[float]] = {
        condition_id(bank_name, grid_name): []
        for bank_name in BANK_VARIANTS
        for grid_name in GRID_VARIANTS
    }
    all_record_counts_valid = True
    all_no_false_positives = True

    for seed in manifest.calibration:
        truth, records = goal011.generate_dataset(fixed, seed)
        all_record_counts_valid &= len(records) == 1920
        all_no_false_positives &= goal011.no_false_positives(records, truth)
        for bank_name in BANK_VARIANTS:
            refined = _profile(records, bank.site_ids, weights[bank_name], config)
            coarse = coarse_profile_from_refined(refined, config.coarse_etas)
            for grid_name, profile in (("coarse", coarse), ("refined", refined)):
                calibration_statistics[condition_id(bank_name, grid_name)].append(
                    _lr_at_truth(profile)
                )

    cutoffs = {
        key: order_statistic_cutoff(
            values,
            rank_one_based=config.calibration_rank_one_based,
        )
        for key, values in calibration_statistics.items()
    }
    validation: list[ValidationResult] = []
    representative_coarse: ThreeParameterProfile | None = None
    representative_refined: ThreeParameterProfile | None = None
    representative_index = -1
    representative_was_split = False

    for seed in manifest.validation:
        truth, records = goal011.generate_dataset(fixed, seed)
        all_record_counts_valid &= len(records) == 1920
        all_no_false_positives &= goal011.no_false_positives(records, truth)
        for bank_name in BANK_VARIANTS:
            refined = _profile(records, bank.site_ids, weights[bank_name], config)
            coarse = coarse_profile_from_refined(refined, config.coarse_etas)
            supports = {}
            for grid_name, profile in (("coarse", coarse), ("refined", refined)):
                key = condition_id(bank_name, grid_name)
                support = summarize_support(profile, cutoff=cutoffs[key].cutoff)
                supports[grid_name] = support
                validation.append(
                    ValidationResult(
                        condition_id=key,
                        dataset_index=seed.index,
                        truth_included=support.truth_included,
                        support_cell_count=support.cell_count,
                        support_component_count=support.component_count,
                        support_boundary_contact=support.boundary_contact,
                        minimum_log_rho_error=support.minimum_log_rho_error,
                        minimum_eta_error=support.minimum_eta_error,
                        minimum_probability_error=support.minimum_probability_error,
                        projected_log_rho_width=support.projected_log_rho_width,
                        projected_eta_width=support.projected_eta_width,
                        projected_probability_width=support.projected_probability_width,
                    )
                )
            if bank_name == "full" and (
                representative_coarse is None
                or (not representative_was_split and supports["coarse"].component_count > 1)
            ):
                representative_coarse = coarse
                representative_refined = refined
                representative_index = seed.index
                representative_was_split = supports["coarse"].component_count > 1

    if representative_coarse is None or representative_refined is None:
        raise RuntimeError("validation produced no representative profiles")
    conditions = tuple(
        _summarize_condition(
            config,
            bank_name,
            grid_name,
            cutoffs[condition_id(bank_name, grid_name)],
            validation,
        )
        for bank_name in BANK_VARIANTS
        for grid_name in GRID_VARIANTS
    )
    topology = _topology_rows(validation, config.validation_replicates)
    full_coarse = _condition(conditions, "full_coarse")
    reconciled = _goal021_reconciled(full_coarse) if config.is_production else True
    fixed_invariants = {
        key: value
        for key, value in fixed.invariants.items()
        if key != "known_detection_probability"
    }
    invariants = {
        **fixed_invariants,
        "goal011_seed_replay": config.master_seed == goal011.MASTER_SEED,
        "coarse_eta_exactly_embedded": all(
            eta in config.refined_etas for eta in config.coarse_etas
        ),
        "bank_shape": bank.arrivals.shape == (config.bank_size, len(config.refined_etas), 160),
        "bank_variant_shapes": all(
            variant.shape == (len(config.refined_etas), len(config.rhos), 160, 7)
            for variant in weights.values()
        ),
        "complete_record_counts": all_record_counts_valid,
        "zero_false_positives": all_no_false_positives,
        "condition_count": len(conditions) == 6,
        "validation_topology_count": len(topology) == config.validation_replicates,
        "goal021_reconciliation": reconciled,
    }
    refined_outcomes = tuple(
        _condition(conditions, f"{bank_name}_refined").outcome for bank_name in BANK_VARIANTS
    )
    if len(refined_outcomes) != 3:
        raise RuntimeError("refined condition outcome count is invalid")
    outcome = classify_outcome(
        invariants=invariants,
        goal021_reconciled=reconciled,
        refined_outcomes=(
            refined_outcomes[0],
            refined_outcomes[1],
            refined_outcomes[2],
        ),
    )
    if not config.is_production and outcome != "implementation_blocked":
        outcome = "non_scientific_smoke"
    return Goal022Result(
        config=config,
        conditions=conditions,
        validation_topology=topology,
        representative_dataset_index=representative_index,
        representative_coarse=representative_coarse,
        representative_refined=representative_refined,
        representative_was_split=representative_was_split,
        invariants=invariants,
        goal021_reconciled=reconciled,
        outcome=outcome,
    )


def write_review_bundle(result: Goal022Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the compact five-file review surface."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("output directory must be empty")
    _write_dataclass_csv(target / "condition_summary.csv", result.conditions)
    _write_dataclass_csv(target / "validation_topology.csv", result.validation_topology)
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    _save_figure(target / "rho_eta_topology.svg", _review_figure(result))
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 022 review surface is incomplete")
    return written


def condition_id(bank_variant: str, grid_variant: str) -> str:
    return f"{bank_variant}_{grid_variant}"


def _bank_weights(
    arrivals: NDArray[np.float64],
    config: Goal022Config,
) -> dict[str, NDArray[np.float64]]:
    midpoint = config.bank_size // 2
    ranges = {
        "full": (0, config.bank_size),
        "first_half": (0, midpoint),
        "second_half": (midpoint, config.bank_size),
    }
    rhos = np.asarray(config.rhos, dtype=np.float64)
    return {
        name: joint_category_weights(arrivals[start:stop], rhos)
        for name, (start, stop) in ranges.items()
    }


def _profile(
    records: Sequence[HistoryRecordLike],
    site_ids: tuple[str, ...],
    weights: NDArray[np.float64],
    config: Goal022Config,
) -> ThreeParameterProfile:
    return three_parameter_profile(
        site_ids=site_ids,
        records=records,
        category_weights=weights,
        rhos=config.rhos,
        etas=config.refined_etas,
        probabilities=config.probabilities,
    )


def _lr_at_truth(profile: ThreeParameterProfile) -> float:
    eta_index = int(np.flatnonzero(profile.etas == TRUTH_ETA)[0])
    rho_index = int(np.flatnonzero(profile.rhos == TRUTH_RHO)[0])
    p_index = int(np.flatnonzero(profile.probabilities == TRUTH_PROBABILITY)[0])
    return float(
        2.0
        * (profile.maximum_log_likelihood - profile.log_likelihoods[eta_index, rho_index, p_index])
    )


def _summarize_condition(
    config: Goal022Config,
    bank_variant: str,
    grid_variant: str,
    cutoff: CutoffResult,
    all_rows: list[ValidationResult],
) -> ConditionSummary:
    key = condition_id(bank_variant, grid_variant)
    rows = [row for row in all_rows if row.condition_id == key]
    if len(rows) != config.validation_replicates:
        raise ValueError("condition validation count is incomplete")
    coverage_count = sum(row.truth_included for row in rows)
    coverage = wilson_interval(coverage_count, len(rows))
    connected = sum(
        row.support_component_count == 1 and not row.support_boundary_contact for row in rows
    )
    boundary = sum(row.support_boundary_contact for row in rows)
    log_rho_error = median(row.minimum_log_rho_error for row in rows)
    eta_error = median(row.minimum_eta_error for row in rows)
    p_error = median(row.minimum_probability_error for row in rows)
    log_rho_width = median(row.projected_log_rho_width for row in rows)
    eta_width = median(row.projected_eta_width for row in rows)
    p_width = median(row.projected_probability_width for row in rows)
    outcome = classify_condition(
        invariants={"condition_valid": True},
        connected_interior_count=connected,
        validation_count=len(rows),
        coverage=coverage,
        median_log_rho_error=log_rho_error,
        median_eta_error=eta_error,
        median_probability_error=p_error,
        median_log_rho_width=log_rho_width,
        median_eta_width=eta_width,
        median_probability_width=p_width,
    )
    return ConditionSummary(
        condition_id=key,
        bank_variant=bank_variant,
        bank_draw_count=config.bank_size if bank_variant == "full" else config.bank_size // 2,
        grid_variant=grid_variant,
        eta_grid_size=(
            len(config.coarse_etas) if grid_variant == "coarse" else len(config.refined_etas)
        ),
        cutoff=cutoff.cutoff,
        coverage_success_count=coverage_count,
        coverage=coverage.estimate,
        coverage_lower=coverage.lower,
        coverage_upper=coverage.upper,
        connected_interior_count=connected,
        boundary_contact_count=boundary,
        median_log_rho_error=log_rho_error,
        median_eta_error=eta_error,
        median_probability_error=p_error,
        median_log_rho_width=log_rho_width,
        median_eta_width=eta_width,
        median_probability_width=p_width,
        outcome=outcome,
    )


def _topology_rows(
    rows: list[ValidationResult],
    expected_count: int,
) -> tuple[TopologyRow, ...]:
    indexed = {(row.dataset_index, row.condition_id): row for row in rows}
    topology = tuple(
        TopologyRow(
            dataset_index=index,
            full_coarse_components=indexed[(index, "full_coarse")].support_component_count,
            full_refined_components=indexed[(index, "full_refined")].support_component_count,
            first_half_coarse_components=indexed[
                (index, "first_half_coarse")
            ].support_component_count,
            first_half_refined_components=indexed[
                (index, "first_half_refined")
            ].support_component_count,
            second_half_coarse_components=indexed[
                (index, "second_half_coarse")
            ].support_component_count,
            second_half_refined_components=indexed[
                (index, "second_half_refined")
            ].support_component_count,
            full_coarse_truth_included=indexed[(index, "full_coarse")].truth_included,
            full_refined_truth_included=indexed[(index, "full_refined")].truth_included,
            full_coarse_support_cells=indexed[(index, "full_coarse")].support_cell_count,
            full_refined_support_cells=indexed[(index, "full_refined")].support_cell_count,
        )
        for index in range(expected_count)
    )
    return topology


def _condition(
    conditions: tuple[ConditionSummary, ...],
    key: str,
) -> ConditionSummary:
    matches = [condition for condition in conditions if condition.condition_id == key]
    if len(matches) != 1:
        raise ValueError("condition summary is missing or duplicated")
    return matches[0]


def _goal021_reconciled(condition: ConditionSummary) -> bool:
    return (
        math.isclose(condition.cutoff, GOAL021_CUTOFF, rel_tol=0.0, abs_tol=1e-9)
        and condition.coverage_success_count == 234
        and condition.connected_interior_count == 229
        and condition.boundary_contact_count == 0
    )


def _write_dataclass_csv(
    path: Path,
    rows: Sequence[ConditionSummary] | Sequence[TopologyRow],
) -> None:
    if not rows:
        raise ValueError("CSV rows must not be empty")
    payload = [asdict(row) for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]))
        writer.writeheader()
        writer.writerows(payload)


def _summary_payload(result: Goal022Result) -> dict[str, object]:
    return {
        "goal": "022-rho-eta-support-topology-diagnostic",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "scientific_interpretation": result.outcome,
        "outcome": result.outcome,
        "goal021_reconciled": result.goal021_reconciled,
        "representative_dataset_index": result.representative_dataset_index,
        "representative_was_split": result.representative_was_split,
        "conditions": [asdict(condition) for condition in result.conditions],
        "invariants": result.invariants,
    }


def _review(result: Goal022Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 022: Spread-Rate / Resistance Support Topology\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    rows = [
        "# Goal 022: Spread-Rate / Resistance Support Topology",
        "",
        f"Outcome: `{result.outcome}`.",
        "",
        "| Bank | Eta grid | Connected / 250 | Coverage | Decision |",
        "|---|---:|---:|---:|---|",
    ]
    for condition in result.conditions:
        rows.append(
            f"| {condition.bank_variant} | {condition.grid_variant} "
            f"| {condition.connected_interior_count} | {condition.coverage:.3f} "
            f"| `{condition.outcome}` |"
        )
    rows.extend(
        [
            "",
            (
                f"The full/coarse condition reproduced Goal 021: "
                f"`{result.goal021_reconciled}`. The paired likelihood slices use validation "
                f"history {result.representative_dataset_index}."
            ),
            "",
            (
                "This diagnostic changes numerical resolution and bank composition only. "
                "It does not revise the Goal 021 result or establish cross-truth robustness."
            ),
            "",
        ]
    )
    return "\n".join(rows)


def _review_figure(result: Goal022Result) -> Figure:
    figure, axes = plt.subplots(2, 2, figsize=(12.5, 8.4), constrained_layout=True)
    labels = [
        f"{condition.bank_variant.replace('_', ' ')}\n{condition.grid_variant}"
        for condition in result.conditions
    ]
    counts = [condition.connected_interior_count for condition in result.conditions]
    axes[0, 0].bar(np.arange(len(counts)), counts, color="#3B6FB6")
    axes[0, 0].axhline(
        math.ceil(0.95 * result.config.validation_replicates),
        color="#C44E52",
        linestyle="--",
        label="Progression threshold",
    )
    axes[0, 0].set(
        xticks=np.arange(len(labels)),
        xticklabels=labels,
        ylabel="Connected interior supports",
        title="Connectivity by grid and bank",
    )
    axes[0, 0].tick_params(axis="x", labelrotation=25)
    axes[0, 0].legend(frameon=False)

    transitions = np.zeros((3, 3), dtype=np.int64)
    for row in result.validation_topology:
        coarse = min(row.full_coarse_components, 3) - 1
        refined = min(row.full_refined_components, 3) - 1
        transitions[coarse, refined] += 1
    axes[0, 1].imshow(transitions, cmap="Blues", vmin=0)
    for row_index in range(3):
        for column_index in range(3):
            axes[0, 1].text(
                column_index,
                row_index,
                str(transitions[row_index, column_index]),
                ha="center",
                va="center",
            )
    axes[0, 1].set(
        xticks=np.arange(3),
        yticks=np.arange(3),
        xticklabels=("1", "2", "3+"),
        yticklabels=("1", "2", "3+"),
        xlabel="Refined-grid components",
        ylabel="Coarse-grid components",
        title="Full-bank topology transitions",
    )

    coarse_condition = _condition(result.conditions, "full_coarse")
    refined_condition = _condition(result.conditions, "full_refined")
    ceiling = max(8.0, 1.5 * coarse_condition.cutoff, 1.5 * refined_condition.cutoff)
    _rho_eta_contour(
        axes[1, 0],
        result.representative_coarse,
        coarse_condition.cutoff,
        ceiling,
        "Coarse eta grid",
    )
    filled = _rho_eta_contour(
        axes[1, 1],
        result.representative_refined,
        refined_condition.cutoff,
        ceiling,
        "Refined eta grid",
    )
    figure.colorbar(filled, ax=axes[1, :].tolist(), label="Likelihood-ratio distance")
    return figure


def _rho_eta_contour(
    axis: Axes,
    profile: ThreeParameterProfile,
    cutoff: float,
    ceiling: float,
    title: str,
) -> mpl.contour.QuadContourSet:
    probability_index = int(np.flatnonzero(profile.probabilities == TRUTH_PROBABILITY)[0])
    statistic = 2.0 * (
        profile.maximum_log_likelihood - profile.log_likelihoods[:, :, probability_index]
    )
    x, y = np.meshgrid(np.log2(profile.rhos), profile.etas)
    filled = axis.contourf(
        x,
        y,
        np.minimum(statistic, ceiling),
        levels=np.linspace(0.0, ceiling, 15),
        cmap="viridis_r",
    )
    if float(statistic.min()) <= cutoff <= float(statistic.max()):
        axis.contour(x, y, statistic, levels=[cutoff], colors=["#C44E52"])
    axis.scatter([0.0], [TRUTH_ETA], marker="x", s=70, color="white")
    axis.set(
        xlabel="log2 spread rate",
        ylabel="Resistance contrast",
        title=title,
    )
    return filled


def _save_figure(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", metadata={"Date": None})
    plt.close(figure)
