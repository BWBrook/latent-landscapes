"""Resistance-contrast transition benchmark."""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import cast

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

DEFAULT_GOAL023_EVIDENCE_DIR = Path(
    "artifacts/goal023_one_axis_cross_truth_three_parameter_benchmark"
)
MIDPOINT_TRUTH = TruthCell("midpoint_resistance", 1.0, 0.75, 0.65)
EXPECTED_FILES = (
    "transition_summary.csv",
    "midpoint_validation.csv",
    "summary.json",
    "review.md",
    "resistance_transition.svg",
)


@dataclass(frozen=True, slots=True)
class Goal024Config:
    """Frozen single-midpoint campaign."""

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
            raise ValueError("midpoint truth must occur once on every parameter grid")

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


DEFAULT_CONFIG = Goal024Config()


def smoke_config() -> Goal024Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal024Config(
        bank_size=8,
        calibration_replicates=4,
        validation_replicates=4,
        calibration_rank_one_based=4,
        rhos=(0.5, 1.0, 2.0),
        etas=(0.5, 0.75, 1.0),
        probabilities=(0.45, 0.65, 0.85),
    )


@dataclass(frozen=True, slots=True)
class Goal023Anchors:
    weaker_resistance: TruthSummary
    central: TruthSummary


@dataclass(frozen=True, slots=True)
class Goal024Result:
    config: Goal024Config
    anchors: Goal023Anchors
    midpoint_summary: TruthSummary
    midpoint_validation: tuple[ValidationResult, ...]
    invariants: dict[str, bool]
    midpoint_joint_outcome: str
    outcome: str

    @property
    def transition_summaries(self) -> tuple[TruthSummary, ...]:
        return (
            self.anchors.weaker_resistance,
            self.midpoint_summary,
            self.anchors.central,
        )


def load_goal023_anchors(evidence_dir: Path) -> Goal023Anchors:
    """Load and reconcile the two accepted Goal 023 resistance anchors."""
    summaries = load_goal023_summaries(evidence_dir)
    weak = one_summary(summaries, "weaker_resistance")
    central = one_summary(summaries, "central")
    if not (
        weak.truth_rho == 1.0
        and weak.truth_eta == 0.5
        and weak.truth_probability == 0.65
        and weak.connected_interior_count == 166
        and weak.boundary_contact_count == 84
        and weak.outcome == "three_parameter_support_design_limited"
        and central.truth_rho == 1.0
        and central.truth_eta == 1.0
        and central.truth_probability == 0.65
        and central.connected_interior_count == 250
        and central.boundary_contact_count == 0
        and central.outcome == ADVANCE
    ):
        raise ValueError("Goal 023 resistance anchors changed")
    return Goal023Anchors(weaker_resistance=weak, central=central)


def load_goal023_summaries(evidence_dir: Path) -> tuple[TruthSummary, ...]:
    """Load the accepted production truth summaries and verify their CSV mirror."""
    target = Path(evidence_dir)
    summary_path = target / "summary.json"
    table_path = target / "truth_summary.csv"
    if not summary_path.is_file() or not table_path.is_file():
        raise ValueError("Goal 023 summary.json and truth_summary.csv are required")
    raw: object = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Goal 023 summary must be a JSON object")
    payload = cast(dict[str, object], raw)
    invariants = payload.get("invariants")
    if (
        payload.get("run_mode") != "production"
        or payload.get("outcome") != "one_axis_identifiability_limit_found"
        or payload.get("central_reconciled") is not True
        or not isinstance(invariants, dict)
        or not invariants
        or not all(value is True for value in invariants.values())
    ):
        raise ValueError("Goal 023 production evidence did not reconcile")
    raw_summaries = payload.get("truth_summaries")
    if not isinstance(raw_summaries, list):
        raise ValueError("Goal 023 truth summaries are missing")
    summaries = tuple(
        _truth_summary_from_mapping(cast(Mapping[str, object], row))
        for row in raw_summaries
        if isinstance(row, dict)
    )
    with table_path.open(encoding="utf-8", newline="") as handle:
        csv_ids = {row.get("truth_id") for row in csv.DictReader(handle)}
    summary_ids = {summary.truth_id for summary in summaries}
    if not summaries or len(summary_ids) != len(summaries) or csv_ids != summary_ids:
        raise ValueError("Goal 023 truth table did not reconcile")
    return summaries


def classify_transition(
    *,
    invariants: dict[str, bool],
    coverage: EstimateInterval,
    connected_interior_count: int,
    validation_count: int,
) -> str:
    """Bracket the resistance transition using the prespecified topology gate."""
    if (
        not invariants
        or not all(invariants.values())
        or validation_count <= 0
        or not 0 <= connected_interior_count <= validation_count
        or not coverage.lower <= 0.95 <= coverage.upper
    ):
        return "resistance_transition_unresolved"
    if connected_interior_count >= math.ceil(0.95 * validation_count):
        return "resistance_transition_between_0_5_and_0_75"
    return "resistance_transition_between_0_75_and_1_0"


def run_goal024(
    goal023_evidence_dir: Path = DEFAULT_GOAL023_EVIDENCE_DIR,
    config: Goal024Config = DEFAULT_CONFIG,
) -> Goal024Result:
    """Calibrate and validate the single resistance midpoint."""
    anchors = load_goal023_anchors(goal023_evidence_dir)
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
        "goal023_anchors_reconciled": True,
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
    outcome = classify_transition(
        invariants=invariants,
        coverage=coverage,
        connected_interior_count=midpoint.connected_interior_count,
        validation_count=config.validation_replicates,
    )
    if not config.is_production:
        outcome = (
            "non_scientific_smoke"
            if invariants and all(invariants.values())
            else "resistance_transition_unresolved"
        )
    return Goal024Result(
        config=config,
        anchors=anchors,
        midpoint_summary=midpoint,
        midpoint_validation=tuple(validation),
        invariants=invariants,
        midpoint_joint_outcome=midpoint_joint_outcome,
        outcome=outcome,
    )


def write_review_bundle(result: Goal024Result, output_dir: Path) -> tuple[Path, ...]:
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
    _save_figure(target / "resistance_transition.svg", _review_figure(result))
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 024 review surface is incomplete")
    return written


def _summarize_midpoint(
    config: Goal024Config,
    cutoff: CutoffResult,
    rows: list[ValidationResult],
) -> TruthSummary:
    if len(rows) != config.validation_replicates:
        raise ValueError("midpoint validation count is incomplete")
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


def _truth_summary_from_mapping(row: Mapping[str, object]) -> TruthSummary:
    return TruthSummary(
        truth_id=_string(row, "truth_id"),
        truth_rho=_number(row, "truth_rho"),
        truth_eta=_number(row, "truth_eta"),
        truth_probability=_number(row, "truth_probability"),
        cutoff=_number(row, "cutoff"),
        coverage_success_count=_integer(row, "coverage_success_count"),
        coverage=_number(row, "coverage"),
        coverage_lower=_number(row, "coverage_lower"),
        coverage_upper=_number(row, "coverage_upper"),
        connected_interior_count=_integer(row, "connected_interior_count"),
        boundary_contact_count=_integer(row, "boundary_contact_count"),
        median_log_rho_error=_number(row, "median_log_rho_error"),
        median_eta_error=_number(row, "median_eta_error"),
        median_probability_error=_number(row, "median_probability_error"),
        median_log_rho_width=_number(row, "median_log_rho_width"),
        median_eta_width=_number(row, "median_eta_width"),
        median_probability_width=_number(row, "median_probability_width"),
        outcome=_string(row, "outcome"),
    )


def _string(row: Mapping[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Goal 023 field {key} is invalid")
    return value


def _number(row: Mapping[str, object], key: str) -> float:
    value = row.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"Goal 023 field {key} is invalid")
    return float(value)


def _integer(row: Mapping[str, object], key: str) -> int:
    value = _number(row, key)
    if not value.is_integer():
        raise ValueError(f"Goal 023 field {key} is not an integer")
    return int(value)


def one_summary(summaries: tuple[TruthSummary, ...], truth_id: str) -> TruthSummary:
    matches = [summary for summary in summaries if summary.truth_id == truth_id]
    if len(matches) != 1:
        raise ValueError("Goal 023 truth summary is missing or duplicated")
    return matches[0]


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


def _summary_payload(result: Goal024Result) -> dict[str, object]:
    return {
        "goal": "024-resistance-contrast-transition-benchmark",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "scientific_interpretation": result.outcome,
        "outcome": result.outcome,
        "midpoint_joint_outcome": result.midpoint_joint_outcome,
        "transition_summaries": [asdict(row) for row in result.transition_summaries],
        "invariants": result.invariants,
    }


def _review(result: Goal024Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 024: Resistance-Contrast Transition\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    midpoint = result.midpoint_summary
    rows = [
        "# Goal 024: Resistance-Contrast Transition",
        "",
        f"Outcome: `{result.outcome}`.",
        "",
        (
            "| Resistance eta | Role | Connected interior / 250 | Boundary contacts "
            "| Coverage | Joint decision |"
        ),
        "|---:|---|---:|---:|---:|---|",
    ]
    roles = {0.5: "accepted weak anchor", 0.75: "new midpoint", 1.0: "accepted strong anchor"}
    for summary in result.transition_summaries:
        rows.append(
            f"| {summary.truth_eta:.2f} | {roles[summary.truth_eta]} | "
            f"{summary.connected_interior_count} | {summary.boundary_contact_count} | "
            f"{summary.coverage:.3f} | `{summary.outcome}` |"
        )
    if result.outcome == "resistance_transition_between_0_5_and_0_75":
        interpretation = (
            f"At eta = 0.75, {midpoint.connected_interior_count}/250 supports stayed "
            "connected and away from the no-resistance boundary. The practical transition "
            "is therefore bracketed between eta = 0.5 and 0.75."
        )
    else:
        interpretation = (
            f"At eta = 0.75, only {midpoint.connected_interior_count}/250 supports stayed "
            "connected and away from the no-resistance boundary. The practical transition "
            "is therefore bracketed between eta = 0.75 and 1.0."
        )
    rows.extend(
        [
            "",
            "## Plain-language interpretation",
            "",
            interpretation,
            "",
            (
                f"The midpoint's broader three-parameter decision was "
                f"`{result.midpoint_joint_outcome}`. This is reported separately so "
                "detection-interval width cannot be mistaken for failure to distinguish "
                "habitat resistance from zero."
            ),
            "",
            (
                f"Specifically, the median detection-probability width was "
                f"{midpoint.median_probability_width:.2f}, compared with the 0.20 joint "
                "precision limit. All midpoint point-error, spread-width, resistance-width, "
                "coverage, connectivity, and boundary criteria passed."
            ),
            "",
            "No finer threshold search or observation-design change was attempted.",
            "",
        ]
    )
    return "\n".join(rows)


def _review_figure(result: Goal024Result) -> Figure:
    figure, axes = plt.subplots(2, 2, figsize=(11.8, 8.2), constrained_layout=True)
    summaries = result.transition_summaries
    etas = np.asarray([summary.truth_eta for summary in summaries])
    threshold = math.ceil(0.95 * result.config.validation_replicates)
    axes[0, 0].plot(
        etas,
        [summary.connected_interior_count for summary in summaries],
        marker="o",
        color="#3B6FB6",
    )
    axes[0, 0].axhline(threshold, color="#C44E52", linestyle="--")
    axes[0, 0].set(
        xlabel="Resistance contrast (eta)",
        ylabel="Connected interior supports",
        xticks=etas,
        title="Can the data exclude no resistance?",
    )
    axes[0, 1].bar(
        etas,
        [summary.boundary_contact_count for summary in summaries],
        width=0.12,
        color="#C44E52",
    )
    axes[0, 1].set(
        xlabel="Resistance contrast (eta)",
        ylabel="Boundary-contact histories",
        xticks=etas,
        title="Support reaching eta = 0",
    )
    coverage = np.asarray([summary.coverage for summary in summaries])
    lower = np.maximum(
        0.0,
        coverage - np.asarray([summary.coverage_lower for summary in summaries]),
    )
    upper = np.maximum(
        0.0,
        np.asarray([summary.coverage_upper for summary in summaries]) - coverage,
    )
    axes[1, 0].errorbar(
        etas,
        coverage,
        yerr=np.vstack((lower, upper)),
        marker="o",
        color="#3B6FB6",
    )
    axes[1, 0].axhline(0.95, color="#C44E52", linestyle="--")
    axes[1, 0].set(
        xlabel="Resistance contrast (eta)",
        ylabel="Validation coverage",
        xticks=etas,
        ylim=(0.85, 1.0),
        title="Calibrated coverage",
    )
    _precision_panel(axes[1, 1], etas, summaries)
    return figure


def _precision_panel(
    axis: Axes,
    etas: NDArray[np.float64],
    summaries: tuple[TruthSummary, ...],
) -> None:
    width = 0.06
    series = (
        ("log-rho", [row.median_log_rho_width / 0.50 for row in summaries]),
        ("eta", [row.median_eta_width / 0.75 for row in summaries]),
        ("p", [row.median_probability_width / 0.20 for row in summaries]),
    )
    for offset, (label, values) in enumerate(series):
        axis.bar(etas + (offset - 1) * width, values, width=width, label=label)
    axis.axhline(1.0, color="#C44E52", linestyle="--")
    axis.set(
        xlabel="Resistance contrast (eta)",
        ylabel="Median width / allowed maximum",
        xticks=etas,
        title="Joint parameter precision",
    )
    axis.legend(frameon=False)


def _save_figure(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", metadata={"Date": None})
    plt.close(figure)
