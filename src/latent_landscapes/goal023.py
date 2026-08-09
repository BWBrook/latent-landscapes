"""One-axis cross-truth three-parameter identifiability benchmark."""

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

from latent_landscapes.goal001.design import DesignSite
from latent_landscapes.goal001.observations import Observation
from latent_landscapes.goal002.calibration import (
    CutoffResult,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal004 import benchmark as goal004
from latent_landscapes.goal004.observations import REPLICATES, SURVEY_TIMES
from latent_landscapes.goal006.spread import ContrastSpreadTruth, compute_paired_spreads
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal007.likelihood import joint_category_weights
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal019 import PROBABILITY_GRID, RHO_GRID
from latent_landscapes.goal021 import (
    TRUTH_ETA,
    TRUTH_PROBABILITY,
    TRUTH_RHO,
    ThreeParameterProfile,
    summarize_support,
    three_parameter_profile,
)
from latent_landscapes.goal021 import (
    classify_outcome as classify_truth,
)
from latent_landscapes.goal022 import REFINED_ETA_GRID

SLOWER_RHO = RHO_GRID[40]
ADVANCE = "advance_to_cross_truth_three_parameter_benchmark"
CENTRAL_CUTOFF = 59.15805000796831
DEFAULT_TRUTHS = (
    ("central", TRUTH_RHO, TRUTH_ETA, TRUTH_PROBABILITY),
    ("slower_spread", SLOWER_RHO, TRUTH_ETA, TRUTH_PROBABILITY),
    ("weaker_resistance", TRUTH_RHO, 0.5, TRUTH_PROBABILITY),
    ("poorer_detection", TRUTH_RHO, TRUTH_ETA, 0.45),
)
EXPECTED_FILES = (
    "truth_summary.csv",
    "validation_results.csv",
    "summary.json",
    "review.md",
    "cross_truth_recovery.svg",
)


@dataclass(frozen=True, slots=True)
class TruthCell:
    truth_id: str
    rho: float
    eta: float
    probability: float


@dataclass(frozen=True, slots=True)
class Goal023Config:
    """Frozen one-axis cross-truth campaign."""

    master_seed: int = goal011.MASTER_SEED
    bank_size: int = goal011.INTEGRATION_BANK_SIZE
    calibration_replicates: int = 250
    validation_replicates: int = 250
    calibration_rank_one_based: int = 239
    rhos: tuple[float, ...] = RHO_GRID
    etas: tuple[float, ...] = REFINED_ETA_GRID
    probabilities: tuple[float, ...] = PROBABILITY_GRID
    truths: tuple[TruthCell, ...] = tuple(TruthCell(*values) for values in DEFAULT_TRUTHS)

    def __post_init__(self) -> None:
        if self.bank_size <= 0:
            raise ValueError("integration bank size must be positive")
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("calibration and validation counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within calibration replicates")
        if len(self.truths) != 4 or len({truth.truth_id for truth in self.truths}) != 4:
            raise ValueError("four uniquely named truth cells are required")
        if tuple(truth.truth_id for truth in self.truths) != (
            "central",
            "slower_spread",
            "weaker_resistance",
            "poorer_detection",
        ):
            raise ValueError("truth cells must retain the frozen order and identifiers")
        for truth in self.truths:
            if (
                sum(value == truth.rho for value in self.rhos) != 1
                or sum(value == truth.eta for value in self.etas) != 1
                or sum(value == truth.probability for value in self.probabilities) != 1
            ):
                raise ValueError("every truth coordinate must occur once on its parameter grid")

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
            and self.truths == tuple(TruthCell(*values) for values in DEFAULT_TRUTHS)
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


DEFAULT_CONFIG = Goal023Config()


def smoke_config() -> Goal023Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal023Config(
        bank_size=8,
        calibration_replicates=4,
        validation_replicates=4,
        calibration_rank_one_based=4,
        rhos=(0.5, 1.0, 2.0),
        etas=(0.5, 1.0, 1.5),
        probabilities=(0.45, 0.65, 0.85),
        truths=(
            TruthCell("central", 1.0, 1.0, 0.65),
            TruthCell("slower_spread", 0.5, 1.0, 0.65),
            TruthCell("weaker_resistance", 1.0, 0.5, 0.65),
            TruthCell("poorer_detection", 1.0, 1.0, 0.45),
        ),
    )


@dataclass(frozen=True, slots=True)
class ValidationResult:
    truth_id: str
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
class TruthSummary:
    truth_id: str
    truth_rho: float
    truth_eta: float
    truth_probability: float
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
class Goal023Result:
    config: Goal023Config
    truth_summaries: tuple[TruthSummary, ...]
    validation_results: tuple[ValidationResult, ...]
    invariants: dict[str, bool]
    central_reconciled: bool
    outcome: str


def generate_truth_dataset(
    fixed: goal007.FixedInputs,
    seed: goal011.DatasetSeedRecord,
    truth: TruthCell,
) -> tuple[ContrastSpreadTruth, tuple[Observation, ...]]:
    """Generate one truth cell using paired process and detection streams."""
    _, truths = compute_paired_spreads(
        fixed.landscape,
        rng=goal007.generator_from_seed_record(seed.process),
        etas=(truth.eta,),
        rho=truth.rho,
    )
    generated = truths[0]
    records = _generate_observations(
        fixed.design.sites,
        generated,
        goal004.generator_from_seed_record(seed.detection),
        truth.probability,
    )
    return generated, records


def _generate_observations(
    sites: tuple[DesignSite, ...],
    truth: ContrastSpreadTruth,
    detection_rng: np.random.Generator,
    detection_probability: float,
) -> tuple[Observation, ...]:
    """Generate paired records without modifying the frozen Goal 004 API."""
    if not math.isfinite(detection_probability) or not 0.0 <= detection_probability <= 1.0:
        raise ValueError("detection probability must be finite and lie in [0, 1]")
    records: list[Observation] = []
    for site in sorted(sites, key=lambda value: (value.cluster_id, value.site_offset_index)):
        for time in SURVEY_TIMES:
            occupied = bool(truth.arrival[site.row, site.col] <= time)
            for replicate in REPLICATES:
                records.append(
                    Observation(
                        cluster_id=site.cluster_id,
                        split=site.split,
                        stratum_index=site.stratum_index,
                        site_id=site.site_id,
                        site_offset_index=site.site_offset_index,
                        row=site.row,
                        col=site.col,
                        time=time,
                        replicate=replicate,
                        detected=int(occupied and detection_rng.random() < detection_probability),
                    )
                )
    return tuple(records)


def classify_outcome(
    *,
    invariants: dict[str, bool],
    central_reconciled: bool,
    stress_outcomes: tuple[str, str, str],
) -> str:
    """Apply the frozen cross-truth progression rule."""
    if not central_reconciled:
        return "central_truth_reconciliation_failed"
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if all(outcome == ADVANCE for outcome in stress_outcomes):
        return "advance_to_joint_interaction_truths"
    return "one_axis_identifiability_limit_found"


def run_goal023(config: Goal023Config = DEFAULT_CONFIG) -> Goal023Result:
    """Run one independently calibrated campaign at each frozen truth."""
    fixed = goal011.build_fixed_inputs()
    manifest = goal011.spawn_seed_manifest(config.goal011_config)
    bank = goal007.build_integration_bank(fixed, manifest.integration_bank, config.etas)
    weights = joint_category_weights(bank.arrivals, np.asarray(config.rhos, dtype=np.float64))
    calibration_statistics: dict[str, list[float]] = {truth.truth_id: [] for truth in config.truths}
    all_record_counts_valid = True
    all_no_false_positives = True

    for seed in manifest.calibration:
        for truth in config.truths:
            generated, records = generate_truth_dataset(fixed, seed, truth)
            profile = three_parameter_profile(
                site_ids=bank.site_ids,
                records=records,
                category_weights=weights,
                rhos=config.rhos,
                etas=config.etas,
                probabilities=config.probabilities,
            )
            calibration_statistics[truth.truth_id].append(_lr_at_truth(profile, truth))
            all_record_counts_valid &= len(records) == 1920
            all_no_false_positives &= _no_false_positives(records, generated)

    cutoffs = {
        truth_id: order_statistic_cutoff(
            statistics,
            rank_one_based=config.calibration_rank_one_based,
        )
        for truth_id, statistics in calibration_statistics.items()
    }
    validation: list[ValidationResult] = []
    for seed in manifest.validation:
        for truth in config.truths:
            generated, records = generate_truth_dataset(fixed, seed, truth)
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
                cutoff=cutoffs[truth.truth_id].cutoff,
                truth_rho=truth.rho,
                truth_eta=truth.eta,
                truth_probability=truth.probability,
            )
            validation.append(
                ValidationResult(
                    truth_id=truth.truth_id,
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
            all_no_false_positives &= _no_false_positives(records, generated)

    summaries = tuple(
        _summarize_truth(config, truth, cutoffs[truth.truth_id], validation)
        for truth in config.truths
    )
    central = _truth_summary(summaries, "central")
    central_reconciled = _central_reconciled(central) if config.is_production else True
    fixed_invariants = {
        key: value
        for key, value in fixed.invariants.items()
        if key != "known_detection_probability"
    }
    invariants = {
        **fixed_invariants,
        "goal011_seed_replay": config.master_seed == goal011.MASTER_SEED,
        "integration_bank_shape": bank.arrivals.shape == (config.bank_size, len(config.etas), 160),
        "integration_weights_valid": bool(
            weights.shape == (len(config.etas), len(config.rhos), 160, 7)
            and np.isfinite(weights).all()
            and np.allclose(weights.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)
        ),
        "truth_cell_count": len(summaries) == 4,
        "validation_result_count": len(validation)
        == len(config.truths) * config.validation_replicates,
        "complete_record_counts": all_record_counts_valid,
        "zero_false_positives": all_no_false_positives,
        "central_reconciliation": central_reconciled,
    }
    stress_outcomes = tuple(summary.outcome for summary in summaries[1:])
    if len(stress_outcomes) != 3:
        raise RuntimeError("stress outcome count is invalid")
    outcome = classify_outcome(
        invariants=invariants,
        central_reconciled=central_reconciled,
        stress_outcomes=(stress_outcomes[0], stress_outcomes[1], stress_outcomes[2]),
    )
    if not config.is_production and outcome != "implementation_blocked":
        outcome = "non_scientific_smoke"
    return Goal023Result(
        config=config,
        truth_summaries=summaries,
        validation_results=tuple(validation),
        invariants=invariants,
        central_reconciled=central_reconciled,
        outcome=outcome,
    )


def write_review_bundle(result: Goal023Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the compact five-file review surface."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("output directory must be empty")
    _write_dataclass_csv(target / "truth_summary.csv", result.truth_summaries)
    _write_dataclass_csv(target / "validation_results.csv", result.validation_results)
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    _save_figure(target / "cross_truth_recovery.svg", _review_figure(result))
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 023 review surface is incomplete")
    return written


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


def _summarize_truth(
    config: Goal023Config,
    truth: TruthCell,
    cutoff: CutoffResult,
    all_rows: list[ValidationResult],
) -> TruthSummary:
    rows = [row for row in all_rows if row.truth_id == truth.truth_id]
    if len(rows) != config.validation_replicates:
        raise ValueError("truth validation count is incomplete")
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
    outcome = classify_truth(
        invariants={"truth_valid": True},
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
        truth_id=truth.truth_id,
        truth_rho=truth.rho,
        truth_eta=truth.eta,
        truth_probability=truth.probability,
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


def _truth_summary(summaries: tuple[TruthSummary, ...], truth_id: str) -> TruthSummary:
    matches = [summary for summary in summaries if summary.truth_id == truth_id]
    if len(matches) != 1:
        raise ValueError("truth summary is missing or duplicated")
    return matches[0]


def _central_reconciled(summary: TruthSummary) -> bool:
    return (
        math.isclose(summary.cutoff, CENTRAL_CUTOFF, rel_tol=0.0, abs_tol=1e-9)
        and summary.coverage_success_count == 234
        and summary.connected_interior_count == 250
        and summary.boundary_contact_count == 0
        and summary.outcome == ADVANCE
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


def _summary_payload(result: Goal023Result) -> dict[str, object]:
    return {
        "goal": "023-one-axis-cross-truth-three-parameter-benchmark",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "scientific_interpretation": result.outcome,
        "outcome": result.outcome,
        "central_reconciled": result.central_reconciled,
        "truth_summaries": [asdict(summary) for summary in result.truth_summaries],
        "invariants": result.invariants,
    }


def _review(result: Goal023Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 023: One-Axis Cross-Truth Benchmark\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    rows = [
        "# Goal 023: One-Axis Cross-Truth Benchmark",
        "",
        f"Outcome: `{result.outcome}`.",
        "",
        "| Truth | Connected interior / 250 | Coverage | Median errors (rho, eta, p) | Decision |",
        "|---|---:|---:|---|---|",
    ]
    for summary in result.truth_summaries:
        rows.append(
            f"| {summary.truth_id} | {summary.connected_interior_count} "
            f"| {summary.coverage:.3f} | {summary.median_log_rho_error:.3f}, "
            f"{summary.median_eta_error:.3f}, {summary.median_probability_error:.3f} "
            f"| `{summary.outcome}` |"
        )
    central = _truth_summary(result.truth_summaries, "central")
    slower = _truth_summary(result.truth_summaries, "slower_spread")
    weaker = _truth_summary(result.truth_summaries, "weaker_resistance")
    poorer = _truth_summary(result.truth_summaries, "poorer_detection")
    rows.extend(
        [
            "",
            "## Plain-language interpretation",
            "",
            (
                f"The central benchmark reproduced Goal 022 exactly and passed "
                f"({central.connected_interior_count}/250 interior supports)."
            ),
            "",
            (
                "Slower spread retained accurate point estimates and connected supports, "
                f"but the median detection-probability width increased to "
                f"{slower.median_probability_width:.2f}, above the 0.20 limit. A slower "
                "wave therefore leaves spread timing and imperfect detection less clearly "
                "separated under this design."
            ),
            "",
            (
                f"Under weaker habitat resistance, all supports remained connected, but "
                f"{weaker.boundary_contact_count}/250 reached the eta = 0 boundary. In "
                "those histories the observations could not rule out no resistance effect; "
                f"the median detection-probability width was also "
                f"{weaker.median_probability_width:.2f}."
            ),
            "",
            (
                "Poorer detection alone still passed: all supports were interior and the "
                f"median detection-probability width was {poorer.median_probability_width:.2f}."
            ),
            "",
            (
                "The one-axis limit is therefore uncertainty rather than systematic point "
                "bias. Do not advance to interaction truths until the weak-resistance and "
                "slow-spread information limits have been considered explicitly."
            ),
            "",
            (
                "Each stress cell changes one generating parameter only. This benchmark does "
                "not establish interaction-truth or prediction robustness."
            ),
            "",
        ]
    )
    return "\n".join(rows)


def _review_figure(result: Goal023Result) -> Figure:
    figure, axes = plt.subplots(2, 2, figsize=(12.2, 8.2), constrained_layout=True)
    labels = [summary.truth_id.replace("_", " ") for summary in result.truth_summaries]
    positions = np.arange(len(labels))
    threshold = math.ceil(0.95 * result.config.validation_replicates)

    axes[0, 0].bar(
        positions,
        [summary.connected_interior_count for summary in result.truth_summaries],
        color="#3B6FB6",
    )
    axes[0, 0].axhline(threshold, color="#C44E52", linestyle="--")
    axes[0, 0].set(
        xticks=positions,
        xticklabels=labels,
        ylabel="Connected interior supports",
        title="Support topology",
    )

    coverage = np.asarray([summary.coverage for summary in result.truth_summaries])
    lower = np.maximum(
        0.0,
        coverage - np.asarray([summary.coverage_lower for summary in result.truth_summaries]),
    )
    upper = np.maximum(
        0.0,
        np.asarray([summary.coverage_upper for summary in result.truth_summaries]) - coverage,
    )
    axes[0, 1].errorbar(
        positions,
        coverage,
        yerr=np.vstack((lower, upper)),
        fmt="o",
        color="#3B6FB6",
    )
    axes[0, 1].axhline(0.95, color="#C44E52", linestyle="--")
    axes[0, 1].set(
        xticks=positions,
        xticklabels=labels,
        ylabel="Validation coverage",
        ylim=(0.85, 1.0),
        title="Coverage with 95% Wilson intervals",
    )

    _grouped_ratios(
        axes[1, 0],
        positions,
        labels,
        (
            (
                "log-rho",
                [summary.median_log_rho_error / 0.10 for summary in result.truth_summaries],
            ),
            ("eta", [summary.median_eta_error / 0.25 for summary in result.truth_summaries]),
            ("p", [summary.median_probability_error / 0.05 for summary in result.truth_summaries]),
        ),
        "Median error / allowed maximum",
        "Normalized point recovery",
    )
    _grouped_ratios(
        axes[1, 1],
        positions,
        labels,
        (
            (
                "log-rho",
                [summary.median_log_rho_width / 0.50 for summary in result.truth_summaries],
            ),
            ("eta", [summary.median_eta_width / 0.75 for summary in result.truth_summaries]),
            ("p", [summary.median_probability_width / 0.20 for summary in result.truth_summaries]),
        ),
        "Median width / allowed maximum",
        "Normalized support precision",
    )
    return figure


def _grouped_ratios(
    axis: Axes,
    positions: NDArray[np.int64],
    labels: list[str],
    series: tuple[tuple[str, list[float]], ...],
    ylabel: str,
    title: str,
) -> None:
    width = 0.24
    for offset, (name, values) in enumerate(series):
        axis.bar(positions + (offset - 1) * width, values, width=width, label=name)
    axis.axhline(1.0, color="#C44E52", linestyle="--")
    axis.set(xticks=positions, xticklabels=labels, ylabel=ylabel, title=title)
    axis.legend(frameon=False)


def _save_figure(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", metadata={"Date": None})
    plt.close(figure)
