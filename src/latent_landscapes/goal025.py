"""Spread-duration and detection transition benchmark."""

from __future__ import annotations

import csv
import json
import math
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

from latent_landscapes.goal001.observations import Observation
from latent_landscapes.goal002.calibration import (
    CutoffResult,
    EstimateInterval,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal006.spread import ContrastSpreadTruth
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal007.likelihood import joint_category_weights
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal019 import PROBABILITY_GRID, RHO_GRID
from latent_landscapes.goal021 import (
    ThreeParameterProfile,
    summarize_support,
    three_parameter_profile,
)
from latent_landscapes.goal021 import (
    classify_outcome as classify_joint_recovery,
)
from latent_landscapes.goal022 import REFINED_ETA_GRID
from latent_landscapes.goal023 import (
    ADVANCE,
    TruthCell,
    TruthSummary,
    ValidationResult,
    generate_truth_dataset,
)
from latent_landscapes.goal024 import (
    DEFAULT_GOAL023_EVIDENCE_DIR,
    load_goal023_summaries,
    one_summary,
)

MIDPOINT_RHO = RHO_GRID[45]
MIDPOINT_TRUTH = TruthCell("midpoint_spread", MIDPOINT_RHO, 1.0, 0.65)
EXPECTED_FILES = (
    "transition_summary.csv",
    "midpoint_validation.csv",
    "summary.json",
    "review.md",
    "spread_detection_transition.svg",
)


@dataclass(frozen=True, slots=True)
class Goal025Config:
    """Frozen single-midpoint spread campaign."""

    master_seed: int = goal011.MASTER_SEED
    bank_size: int = goal011.INTEGRATION_BANK_SIZE
    calibration_replicates: int = 250
    validation_replicates: int = 250
    calibration_rank_one_based: int = 239
    rhos: tuple[float, ...] = RHO_GRID
    etas: tuple[float, ...] = REFINED_ETA_GRID
    probabilities: tuple[float, ...] = PROBABILITY_GRID
    truth: TruthCell = MIDPOINT_TRUTH

    def __post_init__(self) -> None:
        if self.bank_size <= 0:
            raise ValueError("integration bank size must be positive")
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("calibration and validation counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within calibration replicates")
        if (
            sum(value == self.truth.rho for value in self.rhos) != 1
            or sum(value == self.truth.eta for value in self.etas) != 1
            or sum(value == self.truth.probability for value in self.probabilities) != 1
        ):
            raise ValueError("spread midpoint truth must occur once on every parameter grid")

    @property
    def is_production(self) -> bool:
        return (
            self.master_seed == goal011.MASTER_SEED
            and self.bank_size == goal011.INTEGRATION_BANK_SIZE
            and self.calibration_replicates == 250
            and self.validation_replicates == 250
            and self.calibration_rank_one_based == 239
            and self.rhos == RHO_GRID
            and self.etas == REFINED_ETA_GRID
            and self.probabilities == PROBABILITY_GRID
            and self.truth == MIDPOINT_TRUTH
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


DEFAULT_CONFIG = Goal025Config()


def smoke_config() -> Goal025Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal025Config(
        bank_size=8,
        calibration_replicates=4,
        validation_replicates=4,
        calibration_rank_one_based=4,
        rhos=(0.7578582832551991, MIDPOINT_RHO, 1.0),
        etas=(0.5, 1.0, 1.5),
        probabilities=(0.45, 0.65, 0.85),
    )


@dataclass(frozen=True, slots=True)
class Goal023SpreadAnchors:
    slower_spread: TruthSummary
    central: TruthSummary


@dataclass(frozen=True, slots=True)
class Goal025Result:
    config: Goal025Config
    anchors: Goal023SpreadAnchors
    midpoint_summary: TruthSummary
    midpoint_validation: tuple[ValidationResult, ...]
    invariants: dict[str, bool]
    midpoint_joint_outcome: str
    outcome: str

    @property
    def transition_summaries(self) -> tuple[TruthSummary, ...]:
        return (
            self.anchors.slower_spread,
            self.midpoint_summary,
            self.anchors.central,
        )


def load_goal023_spread_anchors(evidence_dir: Path) -> Goal023SpreadAnchors:
    """Load and reconcile the accepted Goal 023 spread-rate anchors."""
    summaries = load_goal023_summaries(evidence_dir)
    slower = one_summary(summaries, "slower_spread")
    central = one_summary(summaries, "central")
    if not (
        slower.truth_rho == 0.7578582832551991
        and slower.truth_eta == 1.0
        and slower.truth_probability == 0.65
        and slower.connected_interior_count == 250
        and slower.boundary_contact_count == 0
        and slower.median_probability_width == 0.26
        and slower.outcome == "three_parameter_recovery_imprecise"
        and central.truth_rho == 1.0
        and central.truth_eta == 1.0
        and central.truth_probability == 0.65
        and central.connected_interior_count == 250
        and central.boundary_contact_count == 0
        and math.isclose(
            central.median_probability_width,
            0.20,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and central.outcome == ADVANCE
    ):
        raise ValueError("Goal 023 spread anchors changed")
    return Goal023SpreadAnchors(slower_spread=slower, central=central)


def classify_spread_detection_transition(
    *,
    invariants: dict[str, bool],
    coverage: EstimateInterval,
    connected_interior_count: int,
    validation_count: int,
    median_log_rho_error: float,
    median_probability_error: float,
    median_log_rho_width: float,
    median_probability_width: float,
) -> str:
    """Bracket spread/detection separation using prespecified midpoint gates."""
    if (
        not invariants
        or not all(invariants.values())
        or validation_count <= 0
        or connected_interior_count < math.ceil(0.95 * validation_count)
        or not coverage.lower <= 0.95 <= coverage.upper
    ):
        return "spread_detection_transition_unresolved"
    if any(
        _materially_exceeds(value, threshold)
        for value, threshold in (
            (median_log_rho_error, 0.10),
            (median_probability_error, 0.05),
            (median_log_rho_width, 0.50),
            (median_probability_width, 0.20),
        )
    ):
        return "spread_detection_transition_between_0_871_and_1_0"
    return "spread_detection_transition_between_0_758_and_0_871"


def run_goal025(
    goal023_evidence_dir: Path = DEFAULT_GOAL023_EVIDENCE_DIR,
    config: Goal025Config = DEFAULT_CONFIG,
) -> Goal025Result:
    """Calibrate and validate the single spread-rate midpoint."""
    anchors = load_goal023_spread_anchors(goal023_evidence_dir)
    fixed = goal011.build_fixed_inputs()
    manifest = goal011.spawn_seed_manifest(config.goal011_config)
    bank = goal007.build_integration_bank(fixed, manifest.integration_bank, config.etas)
    weights = joint_category_weights(bank.arrivals, np.asarray(config.rhos, dtype=np.float64))
    calibration_statistics: list[float] = []
    all_record_counts_valid = True
    all_no_false_positives = True

    for seed in manifest.calibration:
        truth, records = generate_truth_dataset(fixed, seed, config.truth)
        profile = three_parameter_profile(
            site_ids=bank.site_ids,
            records=records,
            category_weights=weights,
            rhos=config.rhos,
            etas=config.etas,
            probabilities=config.probabilities,
        )
        calibration_statistics.append(_lr_at_truth(profile, config.truth))
        all_record_counts_valid &= len(records) == 1920
        all_no_false_positives &= _no_false_positives(records, truth)

    cutoff = order_statistic_cutoff(
        calibration_statistics,
        rank_one_based=config.calibration_rank_one_based,
    )
    validation: list[ValidationResult] = []
    for seed in manifest.validation:
        truth, records = generate_truth_dataset(fixed, seed, config.truth)
        profile = three_parameter_profile(
            site_ids=bank.site_ids,
            records=records,
            category_weights=weights,
            rhos=config.rhos,
            etas=config.etas,
            probabilities=config.probabilities,
        )
        support = summarize_support(
            profile,
            cutoff=cutoff.cutoff,
            truth_rho=config.truth.rho,
            truth_eta=config.truth.eta,
            truth_probability=config.truth.probability,
        )
        validation.append(
            ValidationResult(
                truth_id=config.truth.truth_id,
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
        all_record_counts_valid &= len(records) == 1920
        all_no_false_positives &= _no_false_positives(records, truth)

    midpoint = _summarize_midpoint(config, cutoff, validation)
    fixed_invariants = {
        key: value
        for key, value in fixed.invariants.items()
        if key != "known_detection_probability"
    }
    invariants = {
        **fixed_invariants,
        "goal023_spread_anchors_reconciled": True,
        "goal011_seed_replay": config.master_seed == goal011.MASTER_SEED,
        "integration_bank_shape": bank.arrivals.shape == (config.bank_size, len(config.etas), 160),
        "integration_weights_valid": bool(
            weights.shape == (len(config.etas), len(config.rhos), 160, 7)
            and np.isfinite(weights).all()
            and np.allclose(weights.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)
        ),
        "validation_result_count": len(validation) == config.validation_replicates,
        "complete_record_counts": all_record_counts_valid,
        "zero_false_positives": all_no_false_positives,
    }
    coverage = wilson_interval(
        midpoint.coverage_success_count,
        config.validation_replicates,
    )
    midpoint_joint_outcome = classify_joint_recovery(
        invariants=invariants,
        connected_interior_count=midpoint.connected_interior_count,
        validation_count=config.validation_replicates,
        coverage=coverage,
        median_log_rho_error=midpoint.median_log_rho_error,
        median_eta_error=midpoint.median_eta_error,
        median_probability_error=midpoint.median_probability_error,
        median_log_rho_width=midpoint.median_log_rho_width,
        median_eta_width=midpoint.median_eta_width,
        median_probability_width=midpoint.median_probability_width,
    )
    outcome = classify_spread_detection_transition(
        invariants=invariants,
        coverage=coverage,
        connected_interior_count=midpoint.connected_interior_count,
        validation_count=config.validation_replicates,
        median_log_rho_error=midpoint.median_log_rho_error,
        median_probability_error=midpoint.median_probability_error,
        median_log_rho_width=midpoint.median_log_rho_width,
        median_probability_width=midpoint.median_probability_width,
    )
    if not config.is_production:
        outcome = (
            "non_scientific_smoke"
            if invariants and all(invariants.values())
            else "spread_detection_transition_unresolved"
        )
    return Goal025Result(
        config=config,
        anchors=anchors,
        midpoint_summary=midpoint,
        midpoint_validation=tuple(validation),
        invariants=invariants,
        midpoint_joint_outcome=midpoint_joint_outcome,
        outcome=outcome,
    )


def write_review_bundle(result: Goal025Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the compact five-file review surface."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("output directory must be empty")
    _write_dataclass_csv(target / "transition_summary.csv", result.transition_summaries)
    _write_dataclass_csv(target / "midpoint_validation.csv", result.midpoint_validation)
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    _save_figure(target / "spread_detection_transition.svg", _review_figure(result))
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 025 review surface is incomplete")
    return written


def _summarize_midpoint(
    config: Goal025Config,
    cutoff: CutoffResult,
    rows: list[ValidationResult],
) -> TruthSummary:
    if len(rows) != config.validation_replicates:
        raise ValueError("spread midpoint validation count is incomplete")
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
    outcome = classify_joint_recovery(
        invariants={"midpoint_valid": True},
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
    return TruthSummary(
        truth_id=config.truth.truth_id,
        truth_rho=config.truth.rho,
        truth_eta=config.truth.eta,
        truth_probability=config.truth.probability,
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


def _materially_exceeds(value: float, threshold: float) -> bool:
    return value > threshold and not math.isclose(
        value,
        threshold,
        rel_tol=0.0,
        abs_tol=1e-12,
    )


def _lr_at_truth(profile: ThreeParameterProfile, truth: TruthCell) -> float:
    eta_index = int(np.flatnonzero(profile.etas == truth.eta)[0])
    rho_index = int(np.flatnonzero(profile.rhos == truth.rho)[0])
    p_index = int(np.flatnonzero(profile.probabilities == truth.probability)[0])
    return float(
        2.0
        * (profile.maximum_log_likelihood - profile.log_likelihoods[eta_index, rho_index, p_index])
    )


def _no_false_positives(
    records: tuple[Observation, ...],
    truth: ContrastSpreadTruth,
) -> bool:
    return all(
        not record.detected or truth.arrival[record.row, record.col] <= record.time
        for record in records
    )


def _write_dataclass_csv(
    path: Path,
    rows: tuple[TruthSummary, ...] | tuple[ValidationResult, ...],
) -> None:
    if not rows:
        raise ValueError("CSV rows must not be empty")
    payload = [asdict(row) for row in rows]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]))
        writer.writeheader()
        writer.writerows(payload)


def _summary_payload(result: Goal025Result) -> dict[str, object]:
    return {
        "goal": "025-spread-detection-transition-benchmark",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "scientific_interpretation": result.outcome,
        "outcome": result.outcome,
        "midpoint_joint_outcome": result.midpoint_joint_outcome,
        "transition_summaries": [asdict(row) for row in result.transition_summaries],
        "invariants": result.invariants,
    }


def _review(result: Goal025Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 025: Spread-Detection Transition\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    midpoint = result.midpoint_summary
    rows = [
        "# Goal 025: Spread-Detection Transition",
        "",
        f"Outcome: `{result.outcome}`.",
        "",
        (
            "| Spread rho | log2(rho) | Role | Connected interior / 250 | Coverage "
            "| Detection width | Joint decision |"
        ),
        "|---:|---:|---|---:|---:|---:|---|",
    ]
    roles = {
        0.7578582832551991: "accepted slower anchor",
        MIDPOINT_RHO: "new midpoint",
        1.0: "accepted central anchor",
    }
    for summary in result.transition_summaries:
        rows.append(
            f"| {summary.truth_rho:.3f} | {math.log2(summary.truth_rho):.1f} | "
            f"{roles[summary.truth_rho]} | {summary.connected_interior_count} | "
            f"{summary.coverage:.3f} | {summary.median_probability_width:.2f} | "
            f"`{summary.outcome}` |"
        )
    if result.outcome == "spread_detection_transition_between_0_758_and_0_871":
        interpretation = (
            "The midpoint passed the spread-detection gates. Under this survey calendar, "
            "the practical transition is bracketed between rho = 0.758 and 0.871."
        )
    else:
        interpretation = (
            "The midpoint did not pass every spread-detection gate. Under this survey "
            "calendar, the practical transition is bracketed between rho = 0.871 and 1.0."
        )
    rows.extend(
        [
            "",
            "## Plain-language interpretation",
            "",
            interpretation,
            "",
            (
                f"At the midpoint, median detection-probability width was "
                f"{midpoint.median_probability_width:.2f} against the 0.20 limit; median "
                f"log-rho width was {midpoint.median_log_rho_width:.3f} against the 0.50 "
                "limit."
            ),
            "",
            (
                "All midpoint coverage, topology, point-error, and spread-width gates "
                "passed. Detection-probability width was the sole reason the midpoint did "
                "not pass spread-detection separation."
            ),
            "",
            (
                f"The inherited full three-parameter decision was "
                f"`{result.midpoint_joint_outcome}` and is retained as secondary context."
            ),
            "",
            "No survey extension, finer midpoint, or interaction truth was attempted.",
            "",
        ]
    )
    return "\n".join(rows)


def _review_figure(result: Goal025Result) -> Figure:
    figure, axes = plt.subplots(2, 2, figsize=(11.8, 8.2), constrained_layout=True)
    summaries = result.transition_summaries
    log_rhos = np.asarray([math.log2(row.truth_rho) for row in summaries])
    threshold = math.ceil(0.95 * result.config.validation_replicates)
    axes[0, 0].plot(
        log_rhos,
        [row.connected_interior_count for row in summaries],
        marker="o",
        color="#3B6FB6",
    )
    axes[0, 0].axhline(threshold, color="#C44E52", linestyle="--")
    axes[0, 0].set(
        xlabel="log2 spread rate",
        ylabel="Connected interior supports",
        xticks=log_rhos,
        title="Support topology",
    )
    coverage = np.asarray([row.coverage for row in summaries])
    lower = np.maximum(
        0.0,
        coverage - np.asarray([row.coverage_lower for row in summaries]),
    )
    upper = np.maximum(
        0.0,
        np.asarray([row.coverage_upper for row in summaries]) - coverage,
    )
    axes[0, 1].errorbar(
        log_rhos,
        coverage,
        yerr=np.vstack((lower, upper)),
        marker="o",
        color="#3B6FB6",
    )
    axes[0, 1].axhline(0.95, color="#C44E52", linestyle="--")
    axes[0, 1].set(
        xlabel="log2 spread rate",
        ylabel="Validation coverage",
        xticks=log_rhos,
        ylim=(0.85, 1.0),
        title="Calibrated coverage",
    )
    _two_parameter_panel(
        axes[1, 0],
        log_rhos,
        (
            ("log-rho", [row.median_log_rho_error / 0.10 for row in summaries]),
            ("p", [row.median_probability_error / 0.05 for row in summaries]),
        ),
        "Median error / allowed maximum",
        "Point recovery",
    )
    _two_parameter_panel(
        axes[1, 1],
        log_rhos,
        (
            ("log-rho", [row.median_log_rho_width / 0.50 for row in summaries]),
            ("p", [row.median_probability_width / 0.20 for row in summaries]),
        ),
        "Median width / allowed maximum",
        "Spread-detection precision",
    )
    return figure


def _two_parameter_panel(
    axis: Axes,
    x_values: NDArray[np.float64],
    series: tuple[tuple[str, list[float]], ...],
    ylabel: str,
    title: str,
) -> None:
    width = 0.07
    for offset, (label, values) in enumerate(series):
        axis.bar(x_values + (offset - 0.5) * width, values, width=width, label=label)
    axis.axhline(1.0, color="#C44E52", linestyle="--")
    axis.set(
        xlabel="log2 spread rate",
        ylabel=ylabel,
        xticks=x_values,
        title=title,
    )
    axis.legend(frameon=False)


def _save_figure(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", metadata={"Date": None})
    plt.close(figure)
