"""Close the reference prey layer across effect strength and background risk."""

from __future__ import annotations

import csv
import json
import math
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

from latent_landscapes.goal026 import Goal026Config, Goal026Result, run_goal026

HORIZON_DAYS = 60.0
REFERENCE_BACKGROUND_HAZARD = 0.002
DEFAULT_GOAL027_EVIDENCE_DIR = Path(
    "artifacts/goal027_known_arrival_support_calibration_confirmation"
)
DEFAULT_GOAL028_EVIDENCE_DIR = Path(
    "artifacts/goal028_known_arrival_prey_effect_strength_transition"
)
EXPECTED_FILES = (
    "calibration_statistics.csv",
    "validation_results.csv",
    "condition_decision_summary.csv",
    "summary.json",
    "review.md",
    "prey_reference_closure.svg",
)


def daily_hazard_from_cumulative_risk(risk: float, horizon_days: float = HORIZON_DAYS) -> float:
    """Convert an absorbing-event risk over a horizon to a constant daily hazard."""
    if not 0.0 < risk < 1.0 or not math.isfinite(horizon_days) or horizon_days <= 0.0:
        raise ValueError("risk must lie in (0, 1) and horizon must be positive")
    return -math.log1p(-risk) / horizon_days


def cumulative_risk_from_daily_hazard(hazard: float, horizon_days: float = HORIZON_DAYS) -> float:
    """Convert a constant daily hazard to absorbing-event risk over a horizon."""
    if not math.isfinite(hazard) or hazard <= 0.0:
        raise ValueError("hazard must be finite and positive")
    if not math.isfinite(horizon_days) or horizon_days <= 0.0:
        raise ValueError("horizon must be finite and positive")
    return -math.expm1(-hazard * horizon_days)


@dataclass(frozen=True, slots=True)
class ConditionSpec:
    condition_id: str
    hazard_ratio: float
    background_hazard: float
    master_seed: int

    @property
    def background_risk_60d(self) -> float:
        return cumulative_risk_from_daily_hazard(self.background_hazard)


DEFAULT_NEW_CONDITIONS = (
    ConditionSpec("fourfold_reference_risk", 4.0, REFERENCE_BACKGROUND_HAZARD, 202608290364),
    ConditionSpec(
        "fivefold_low_background_risk",
        5.0,
        daily_hazard_from_cumulative_risk(0.05),
        20260811027,
    ),
    ConditionSpec(
        "fivefold_high_background_risk",
        5.0,
        daily_hazard_from_cumulative_risk(0.20),
        20260811027,
    ),
)


@dataclass(frozen=True, slots=True)
class Goal036Config:
    calibration_replicates: int = 2_000
    validation_replicates: int = 1_000
    calibration_rank_one_based: int = 1_901
    conditions: tuple[ConditionSpec, ...] = DEFAULT_NEW_CONDITIONS

    def __post_init__(self) -> None:
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within calibration replicates")
        if tuple(condition.condition_id for condition in self.conditions) != tuple(
            condition.condition_id for condition in DEFAULT_NEW_CONDITIONS
        ):
            raise ValueError("Goal 036 requires the three frozen condition identifiers")
        for observed, expected in zip(self.conditions, DEFAULT_NEW_CONDITIONS, strict=True):
            if (
                observed.hazard_ratio != expected.hazard_ratio
                or observed.master_seed != expected.master_seed
                or not math.isclose(
                    observed.background_hazard,
                    expected.background_hazard,
                    rel_tol=0.0,
                    abs_tol=1e-15,
                )
            ):
                raise ValueError("Goal 036 conditions must match the frozen experiment")

    @property
    def is_production(self) -> bool:
        return self == Goal036Config()

    def goal026_config(self, condition: ConditionSpec) -> Goal026Config:
        return Goal026Config(
            master_seed=condition.master_seed,
            calibration_replicates=self.calibration_replicates,
            validation_replicates=self.validation_replicates,
            calibration_rank_one_based=self.calibration_rank_one_based,
            background_hazard=condition.background_hazard,
            truth_hazard_ratio=condition.hazard_ratio,
        )


DEFAULT_CONFIG = Goal036Config()


def smoke_config() -> Goal036Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal036Config(
        calibration_replicates=8,
        validation_replicates=8,
        calibration_rank_one_based=8,
    )


@dataclass(frozen=True, slots=True)
class ConditionSummary:
    condition_id: str
    evidence_source: str
    hazard_ratio: float
    counterfactual_background_risk_60d: float
    background_daily_hazard: float
    post_arrival_daily_hazard: float
    counterfactual_immediate_arrival_risk_60d: float
    calibration_replicates: int
    validation_replicates: int
    cutoff: float
    coverage_count: int
    coverage: float
    coverage_lower: float
    coverage_upper: float
    connected_interior_count: int
    null_exclusion_count: int
    median_absolute_log_error: float
    median_log_support_width: float
    score_advantage: float
    score_advantage_lower: float
    score_advantage_upper: float
    status: str
    failed_gates: str
    observed_event_count_p10: float | None
    median_observed_event_count: float | None
    observed_event_count_p90: float | None
    median_training_event_count: float | None
    median_holdout_event_count: float | None
    median_censored_count: float | None
    median_pre_arrival_observed_event_count: float | None
    median_post_arrival_observed_event_count: float | None
    median_arrived_by_day60_count: float | None
    median_post_arrival_at_risk_exposure_days: float | None


@dataclass(frozen=True, slots=True)
class ConditionScale:
    condition_id: str
    evidence_source: str
    hazard_ratio: float
    counterfactual_background_risk_60d: float
    background_daily_hazard: float
    post_arrival_daily_hazard: float
    counterfactual_immediate_arrival_risk_60d: float


@dataclass(frozen=True, slots=True)
class ConditionRun:
    spec: ConditionSpec
    result: Goal026Result
    summary: ConditionSummary


@dataclass(frozen=True, slots=True)
class Goal036Result:
    config: Goal036Config
    threefold_anchor: ConditionSummary
    new_runs: tuple[ConditionRun, ...]
    fivefold_anchor: ConditionSummary
    invariants: dict[str, bool]
    effect_transition: str
    background_risk_conclusion: str
    outcome: str

    @property
    def conditions(self) -> tuple[ConditionSummary, ...]:
        fourfold, low_risk, high_risk = self.new_runs
        return (
            self.threefold_anchor,
            fourfold.summary,
            low_risk.summary,
            self.fivefold_anchor,
            high_risk.summary,
        )


def classify_cell(
    *,
    invariants: dict[str, bool],
    validation_count: int,
    null_exclusion_count: int,
    score_advantage_lower: float,
    failed_gates: tuple[str, ...],
) -> str:
    """Separate strict recovery from reliable effect detection."""
    if not invariants or not all(invariants.values()) or validation_count <= 0:
        return "implementation_blocked"
    if not failed_gates:
        return "fully_recovered"
    required = math.ceil(0.95 * validation_count)
    if null_exclusion_count >= required and score_advantage_lower > 0.0:
        return "detected_but_not_fully_recovered"
    return "not_reliably_detected"


def classify_effect_transition(
    *, threefold_status: str, fourfold_status: str, fivefold_status: str
) -> str:
    """Use the accepted 3x and 5x anchors to bracket strict recovery."""
    statuses = (threefold_status, fourfold_status, fivefold_status)
    if "implementation_blocked" in statuses or fivefold_status != "fully_recovered":
        return "implementation_blocked"
    if fourfold_status == "fully_recovered":
        return "strict_transition_between_threefold_and_fourfold"
    if fourfold_status == "detected_but_not_fully_recovered":
        return "strict_transition_between_fourfold_and_fivefold"
    if threefold_status == "detected_but_not_fully_recovered":
        return "nonmonotonic_detection_requires_human_review"
    return "strict_transition_between_fourfold_and_fivefold"


def classify_background_risk(low_status: str, high_status: str) -> str:
    """Classify HR5 recovery over the prespecified 5%-20% risk bracket."""
    if "implementation_blocked" in (low_status, high_status):
        return "implementation_blocked"
    if low_status == high_status == "fully_recovered":
        return "fivefold_recovery_robust_across_5_to_20_percent_background_risk"
    conditional = []
    if low_status != "fully_recovered":
        conditional.append("low_risk")
    if high_status != "fully_recovered":
        conditional.append("high_risk")
    return "fivefold_recovery_conditional_at_" + "_and_".join(conditional)


def run_goal036(
    goal027_evidence_dir: Path = DEFAULT_GOAL027_EVIDENCE_DIR,
    goal028_evidence_dir: Path = DEFAULT_GOAL028_EVIDENCE_DIR,
    config: Goal036Config = DEFAULT_CONFIG,
) -> Goal036Result:
    """Run three new cells and combine them with two accepted anchors."""
    threefold = _load_threefold_anchor(goal028_evidence_dir)
    fivefold = _load_fivefold_anchor(goal027_evidence_dir)
    runs: list[ConditionRun] = []
    invariants: dict[str, bool] = {
        "goal028_threefold_anchor_reconciled": True,
        "goal027_fivefold_anchor_reconciled": True,
        "matched_fivefold_master_seed": (
            config.conditions[1].master_seed == config.conditions[2].master_seed == 20260811027
        ),
        "independent_fourfold_master_seed": config.conditions[0].master_seed != 20260811027,
    }
    for condition in config.conditions:
        result = run_goal026(config.goal026_config(condition))
        summary = _new_condition_summary(condition, result, config)
        runs.append(ConditionRun(condition, result, summary))
        invariants.update(
            {f"{condition.condition_id}_{key}": value for key, value in result.invariants.items()}
        )
        invariants[f"{condition.condition_id}_diagnostic_count"] = (
            len(result.validation_diagnostics) == config.validation_replicates
        )
    effect_transition = classify_effect_transition(
        threefold_status=threefold.status,
        fourfold_status=runs[0].summary.status,
        fivefold_status=fivefold.status,
    )
    background_risk = classify_background_risk(
        runs[1].summary.status,
        runs[2].summary.status,
    )
    if not invariants or not all(invariants.values()):
        outcome = "implementation_blocked"
    else:
        outcome = "arc1_prey_reference_closure_complete"
    if not config.is_production:
        outcome = "non_scientific_smoke" if all(invariants.values()) else "implementation_blocked"
    return Goal036Result(
        config,
        threefold,
        tuple(runs),
        fivefold,
        invariants,
        effect_transition,
        background_risk,
        outcome,
    )


def write_review_bundle(result: Goal036Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the compact six-file reference-closure review surface."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("output directory must be empty")
    calibration_rows: list[dict[str, object]] = []
    validation_rows: list[dict[str, object]] = []
    for run in result.new_runs:
        base = _condition_identity(run.spec)
        calibration_rows.extend(
            {**base, **asdict(row)} for row in run.result.calibration_statistics
        )
        for row, diagnostic in zip(
            run.result.validation_results,
            run.result.validation_diagnostics,
            strict=True,
        ):
            diagnostic_payload = asdict(diagnostic)
            diagnostic_payload.pop("dataset_index")
            validation_rows.append({**base, **asdict(row), **diagnostic_payload})
    _write_rows(target / "calibration_statistics.csv", calibration_rows)
    _write_rows(target / "validation_results.csv", validation_rows)
    summary_rows = []
    for condition in result.conditions:
        summary_rows.append(
            {
                **asdict(condition),
                "effect_transition": result.effect_transition,
                "background_risk_conclusion": result.background_risk_conclusion,
                "overall_outcome": result.outcome,
            }
        )
    _write_rows(target / "condition_decision_summary.csv", summary_rows)
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    figure = _review_figure(result)
    figure.savefig(
        target / "prey_reference_closure.svg",
        format="svg",
        metadata={"Date": None},
    )
    plt.close(figure)
    written = tuple(target / name for name in EXPECTED_FILES)
    if {path.name for path in written} != set(EXPECTED_FILES) or not all(
        path.is_file() and path.stat().st_size > 0 for path in written
    ):
        raise RuntimeError("Goal 036 review surface is incomplete")
    return written


def _condition_identity(condition: ConditionSpec) -> dict[str, object]:
    return {
        "condition_id": condition.condition_id,
        "hazard_ratio": condition.hazard_ratio,
        "counterfactual_background_risk_60d": condition.background_risk_60d,
        "background_daily_hazard": condition.background_hazard,
    }


def _new_condition_summary(
    condition: ConditionSpec,
    result: Goal026Result,
    config: Goal036Config,
) -> ConditionSummary:
    failed = _failed_gates(result, config.validation_replicates)
    status = classify_cell(
        invariants=result.invariants,
        validation_count=config.validation_replicates,
        null_exclusion_count=result.summary.null_exclusion_count,
        score_advantage_lower=result.summary.heldout_log_score_advantage.lower,
        failed_gates=failed,
    )
    observed = [row.observed_event_count for row in result.validation_results]
    training = [row.training_event_count for row in result.validation_results]
    holdout = [row.holdout_event_count for row in result.validation_results]
    diagnostics = result.validation_diagnostics
    summary = result.summary
    scale = _condition_scale(condition, "goal036_new_ensemble")
    return ConditionSummary(
        condition_id=scale.condition_id,
        evidence_source=scale.evidence_source,
        hazard_ratio=scale.hazard_ratio,
        counterfactual_background_risk_60d=scale.counterfactual_background_risk_60d,
        background_daily_hazard=scale.background_daily_hazard,
        post_arrival_daily_hazard=scale.post_arrival_daily_hazard,
        counterfactual_immediate_arrival_risk_60d=(scale.counterfactual_immediate_arrival_risk_60d),
        calibration_replicates=config.calibration_replicates,
        validation_replicates=config.validation_replicates,
        cutoff=summary.cutoff,
        coverage_count=summary.coverage_count,
        coverage=summary.coverage.estimate,
        coverage_lower=summary.coverage.lower,
        coverage_upper=summary.coverage.upper,
        connected_interior_count=summary.connected_interior_count,
        null_exclusion_count=summary.null_exclusion_count,
        median_absolute_log_error=summary.median_absolute_log_error,
        median_log_support_width=summary.median_log_support_width,
        score_advantage=summary.heldout_log_score_advantage.estimate,
        score_advantage_lower=summary.heldout_log_score_advantage.lower,
        score_advantage_upper=summary.heldout_log_score_advantage.upper,
        status=status,
        failed_gates=";".join(failed),
        observed_event_count_p10=_quantile(observed, 0.10),
        median_observed_event_count=median(observed),
        observed_event_count_p90=_quantile(observed, 0.90),
        median_training_event_count=median(training),
        median_holdout_event_count=median(holdout),
        median_censored_count=median(row.censored_count for row in diagnostics),
        median_pre_arrival_observed_event_count=median(
            row.pre_arrival_observed_event_count for row in diagnostics
        ),
        median_post_arrival_observed_event_count=median(
            row.post_arrival_observed_event_count for row in diagnostics
        ),
        median_arrived_by_day60_count=median(row.arrived_by_day60_count for row in diagnostics),
        median_post_arrival_at_risk_exposure_days=median(
            row.post_arrival_at_risk_exposure_days for row in diagnostics
        ),
    )


def _condition_scale(condition: ConditionSpec, evidence_source: str) -> ConditionScale:
    post_arrival_hazard = condition.background_hazard * condition.hazard_ratio
    return ConditionScale(
        condition_id=condition.condition_id,
        evidence_source=evidence_source,
        hazard_ratio=condition.hazard_ratio,
        counterfactual_background_risk_60d=condition.background_risk_60d,
        background_daily_hazard=condition.background_hazard,
        post_arrival_daily_hazard=post_arrival_hazard,
        counterfactual_immediate_arrival_risk_60d=cumulative_risk_from_daily_hazard(
            post_arrival_hazard
        ),
    )


def _anchor_summary(
    *,
    condition_id: str,
    evidence_source: str,
    hazard_ratio: float,
    row: dict[str, object],
    event_summary: dict[str, float],
) -> ConditionSummary:
    condition = ConditionSpec(condition_id, hazard_ratio, REFERENCE_BACKGROUND_HAZARD, 0)
    failed_text = _str_value(row, "failed_gates")
    failed = tuple(value for value in failed_text.split(";") if value)
    validation_count = _int_value(row, "validation_replicates")
    null_exclusion = _int_value(row, "null_exclusion_count")
    score_lower = _float_value(row, "score_advantage_lower")
    status = classify_cell(
        invariants={"anchor_reconciled": True},
        validation_count=validation_count,
        null_exclusion_count=null_exclusion,
        score_advantage_lower=score_lower,
        failed_gates=failed,
    )
    scale = _condition_scale(condition, evidence_source)
    return ConditionSummary(
        condition_id=scale.condition_id,
        evidence_source=scale.evidence_source,
        hazard_ratio=scale.hazard_ratio,
        counterfactual_background_risk_60d=scale.counterfactual_background_risk_60d,
        background_daily_hazard=scale.background_daily_hazard,
        post_arrival_daily_hazard=scale.post_arrival_daily_hazard,
        counterfactual_immediate_arrival_risk_60d=(scale.counterfactual_immediate_arrival_risk_60d),
        calibration_replicates=_int_value(row, "calibration_replicates"),
        validation_replicates=validation_count,
        cutoff=_float_value(row, "cutoff"),
        coverage_count=_int_value(row, "coverage_count"),
        coverage=_float_value(row, "coverage"),
        coverage_lower=_float_value(row, "coverage_lower"),
        coverage_upper=_float_value(row, "coverage_upper"),
        connected_interior_count=_int_value(row, "connected_interior_count"),
        null_exclusion_count=null_exclusion,
        median_absolute_log_error=_float_value(row, "median_absolute_log_error"),
        median_log_support_width=_float_value(row, "median_log_support_width"),
        score_advantage=_float_value(row, "score_advantage"),
        score_advantage_lower=score_lower,
        score_advantage_upper=_float_value(row, "score_advantage_upper"),
        status=status,
        failed_gates=failed_text,
        observed_event_count_p10=event_summary["p10"],
        median_observed_event_count=event_summary["median"],
        observed_event_count_p90=event_summary["p90"],
        median_training_event_count=event_summary["training_median"],
        median_holdout_event_count=event_summary["holdout_median"],
        median_censored_count=event_summary["censored_median"],
        median_pre_arrival_observed_event_count=None,
        median_post_arrival_observed_event_count=None,
        median_arrived_by_day60_count=None,
        median_post_arrival_at_risk_exposure_days=None,
    )


def _load_threefold_anchor(evidence_dir: Path) -> ConditionSummary:
    root = Path(evidence_dir)
    payload = _read_json(root / "summary.json")
    rows = cast(list[dict[str, object]], payload.get("truth_summaries"))
    matches = [row for row in rows if row.get("truth_id") == "threefold_effect"]
    if len(matches) != 1:
        raise ValueError("Goal 028 threefold anchor missing")
    row = matches[0]
    if not (
        payload.get("goal") == "028-known-arrival-prey-effect-strength-transition"
        and payload.get("run_mode") == "production"
        and payload.get("outcome") == "prey_effect_transition_between_threefold_and_fivefold"
        and _float_value(row, "hazard_ratio") == 3.0
        and _int_value(row, "calibration_replicates") == 2_000
        and _int_value(row, "validation_replicates") == 1_000
        and _int_value(row, "coverage_count") == 973
        and _int_value(row, "null_exclusion_count") == 986
        and _str_value(row, "failed_gates") == "calibrated_coverage;support_precision"
        and not _bool_value(row, "recovered")
        and _float_value(row, "score_advantage_lower") > 0.0
    ):
        raise ValueError("published Goal 028 threefold evidence changed")
    events = _load_anchor_events(root / "validation_results.csv", truth_id="threefold_effect")
    return _anchor_summary(
        condition_id="threefold_reference_risk",
        evidence_source="published_goal028",
        hazard_ratio=3.0,
        row=row,
        event_summary=events,
    )


def _load_fivefold_anchor(evidence_dir: Path) -> ConditionSummary:
    root = Path(evidence_dir)
    payload = _read_json(root / "summary.json")
    config = cast(dict[str, object], payload.get("config"))
    rows = cast(list[dict[str, object]], payload.get("coverage_comparison"))
    if len(rows) != 2:
        raise ValueError("Goal 027 comparison must contain two rows")
    row = rows[1]
    normalized = {**row, "failed_gates": ""}
    if not (
        payload.get("goal") == "027-known-arrival-support-calibration-confirmation"
        and payload.get("run_mode") == "production"
        and payload.get("outcome") == "support_calibration_confirmed"
        and _int_value(config, "master_seed") == 20260811027
        and row.get("evidence") == "goal027_high_resolution"
        and _int_value(row, "calibration_replicates") == 2_000
        and _int_value(row, "validation_replicates") == 1_000
        and _int_value(row, "coverage_count") == 954
        and _int_value(row, "connected_interior_count") == 997
        and _int_value(row, "null_exclusion_count") == 1_000
        and _float_value(row, "score_advantage_lower") > 0.0
    ):
        raise ValueError("published Goal 027 fivefold evidence changed")
    events = _load_anchor_events(root / "validation_results.csv")
    return _anchor_summary(
        condition_id="fivefold_reference_risk",
        evidence_source="published_goal027",
        hazard_ratio=5.0,
        row=normalized,
        event_summary=events,
    )


def _load_anchor_events(path: Path, truth_id: str | None = None) -> dict[str, float]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if truth_id is not None:
        rows = [row for row in rows if row.get("truth_id") == truth_id]
    if len(rows) != 1_000:
        raise ValueError("accepted anchor validation evidence must contain 1000 rows")
    total = [_csv_int(row, "observed_event_count") for row in rows]
    training = [_csv_int(row, "training_event_count") for row in rows]
    holdout = [_csv_int(row, "holdout_event_count") for row in rows]
    if any(
        all_count != train + test
        for all_count, train, test in zip(total, training, holdout, strict=True)
    ):
        raise ValueError("accepted anchor event counts do not reconcile")
    return {
        "p10": _quantile(total, 0.10),
        "median": median(total),
        "p90": _quantile(total, 0.90),
        "training_median": median(training),
        "holdout_median": median(holdout),
        "censored_median": median(160 - value for value in total),
    }


def _failed_gates(result: Goal026Result, validation_count: int) -> tuple[str, ...]:
    summary = result.summary
    required = math.ceil(0.95 * validation_count)
    failed: list[str] = []
    if not all(result.invariants.values()):
        failed.append("implementation_invariants")
    if not summary.coverage.lower <= 0.95 <= summary.coverage.upper:
        failed.append("calibrated_coverage")
    if summary.connected_interior_count < required:
        failed.append("connected_interior_support")
    if summary.null_exclusion_count < required:
        failed.append("no_effect_exclusion")
    if summary.median_absolute_log_error > 0.20:
        failed.append("point_recovery")
    if summary.median_log_support_width > 0.80:
        failed.append("support_precision")
    if summary.heldout_log_score_advantage.lower <= 0.0:
        failed.append("neutral_predictive_comparison")
    return tuple(failed)


def _summary_payload(result: Goal036Result) -> dict[str, object]:
    return {
        "goal": "036-prey-effect-background-risk-reference-closure",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "outcome": result.outcome,
        "effect_transition": result.effect_transition,
        "background_risk_conclusion": result.background_risk_conclusion,
        "model_scope": {
            "predator_arrival": "known realized truth",
            "prey_observation": "perfect absorbing extirpation state at days 10..60",
            "background_hazard": "known in generator and likelihood",
            "background_risk_term": "counterfactual 60-day background extirpation risk",
            "risk_interpretation": (
                "risk if predator never arrived; not an annual turnover rate or causal effect"
            ),
        },
        "conditions": [asdict(row) for row in result.conditions],
        "invariants": result.invariants,
    }


def _review(result: Goal036Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 036: Prey Reference Closure\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    rows = [
        "# Goal 036: Prey Effect And Background-Risk Reference Closure",
        "",
        f"Outcome: `{result.outcome}`.",
        "",
        "## Questions answered",
        "",
        (
            "At the accepted reference background risk, does a fourfold predator effect close "
            "the strict-recovery gap between the detected threefold and recovered fivefold "
            "anchors? At a fivefold effect, is strict recovery retained across prespecified "
            "5%-20% counterfactual background extirpation risk by day 60?"
        ),
        "",
        "## Ecological scale and decisions",
        "",
        (
            "| Condition | Effect multiplier | Background risk by day 60 | Daily background "
            "hazard | Daily post-arrival hazard | Immediate-arrival risk by day 60 | Status |"
        ),
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for condition in result.conditions:
        rows.append(
            f"| {condition.condition_id} | {condition.hazard_ratio:.1f}x | "
            f"{100 * condition.counterfactual_background_risk_60d:.1f}% | "
            f"{condition.background_daily_hazard:.6f} | "
            f"{condition.post_arrival_daily_hazard:.6f} | "
            f"{100 * condition.counterfactual_immediate_arrival_risk_60d:.1f}% | "
            f"{condition.status} |"
        )
    rows.extend(
        [
            "",
            "## Recovery evidence",
            "",
            (
                "| Condition | Coverage | Excludes no effect | Median log error | Median support "
                "width | Held-out advantage (lower 95%) | Failed full-recovery gates |"
            ),
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for condition in result.conditions:
        rows.append(
            f"| {condition.condition_id} | {condition.coverage_count}/"
            f"{condition.validation_replicates} ({condition.coverage:.3f}) | "
            f"{condition.null_exclusion_count}/{condition.validation_replicates} | "
            f"{condition.median_absolute_log_error:.3f} | "
            f"{condition.median_log_support_width:.3f} | "
            f"{condition.score_advantage:.4f} ({condition.score_advantage_lower:.4f}) | "
            f"{condition.failed_gates or 'none'} |"
        )
    rows.extend(
        [
            "",
            "## Event-information audit",
            "",
            (
                "New-cell event counts use the known simulated truth only for diagnosis; they "
                "are not supplied as extra observations to the likelihood."
            ),
            "",
            (
                "| New condition | Observed events p10 / median / p90 | Training / holdout "
                "median | Censored median | Pre- / post-arrival event median | Arrived by day "
                "60 median | Post-arrival at-risk exposure-days median |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for run in result.new_runs:
        condition = run.summary
        rows.append(
            f"| {condition.condition_id} | {condition.observed_event_count_p10:.0f} / "
            f"{condition.median_observed_event_count:.0f} / "
            f"{condition.observed_event_count_p90:.0f} | "
            f"{condition.median_training_event_count:.0f} / "
            f"{condition.median_holdout_event_count:.0f} | "
            f"{condition.median_censored_count:.0f} | "
            f"{condition.median_pre_arrival_observed_event_count:.0f} / "
            f"{condition.median_post_arrival_observed_event_count:.0f} | "
            f"{condition.median_arrived_by_day60_count:.0f} | "
            f"{condition.median_post_arrival_at_risk_exposure_days:.1f} |"
        )
    rows.extend(
        [
            "",
            "## Prespecified interpretation",
            "",
            f"- Effect-strength result: `{result.effect_transition}`.",
            f"- Background-risk result: `{result.background_risk_conclusion}`.",
            "",
            (
                "The background-risk comparison is conditional, not causal. Holding the hazard "
                "ratio fixed changes the absolute post-arrival hazard, pre-arrival losses, event "
                "yield, and censoring. The background hazard is known in both generator and "
                "likelihood; it is not jointly estimated here."
            ),
            "",
            (
                "Any valid positive or negative result completes this reference-case closure. "
                "No extra midpoint, risk level, seed, replication, or retuning was added after "
                "seeing the evidence."
            ),
            "",
        ]
    )
    return "\n".join(rows)


def _review_figure(result: Goal036Result) -> Figure:
    conditions = {row.condition_id: row for row in result.conditions}
    effect = [
        conditions["threefold_reference_risk"],
        conditions["fourfold_reference_risk"],
        conditions["fivefold_reference_risk"],
    ]
    risk = [
        conditions["fivefold_low_background_risk"],
        conditions["fivefold_reference_risk"],
        conditions["fivefold_high_background_risk"],
    ]
    figure, axes = plt.subplots(2, 2, figsize=(11.8, 8.2))
    _plot_detection(
        axes[0, 0],
        [row.hazard_ratio for row in effect],
        effect,
        "Predator-effect strength at 11.3% background risk",
        "True predator-effect multiplier",
    )
    _plot_width(
        axes[1, 0],
        [row.hazard_ratio for row in effect],
        effect,
        "Estimate precision at reference risk",
        "True predator-effect multiplier",
    )
    risk_x = [100 * row.counterfactual_background_risk_60d for row in risk]
    _plot_detection(
        axes[0, 1],
        risk_x,
        risk,
        "Fivefold effect across background risk",
        "Background extirpation risk by day 60 (%)",
    )
    _plot_width(
        axes[1, 1],
        risk_x,
        risk,
        "Estimate precision across background risk",
        "Background extirpation risk by day 60 (%)",
    )
    figure.suptitle("Known-arrival prey reference closure", fontsize=14, fontweight="bold")
    figure.text(
        0.5,
        0.01,
        (
            "Background risk is the counterfactual 60-day risk if predator never arrived. "
            "The likelihood knows the background hazard."
        ),
        ha="center",
        fontsize=9,
    )
    figure.tight_layout(rect=(0.02, 0.05, 0.98, 0.95), h_pad=2.4, w_pad=2.2)
    return figure


def _plot_detection(
    axis: Axes,
    x: list[float],
    rows: list[ConditionSummary],
    title: str,
    xlabel: str,
) -> None:
    values = [100 * row.null_exclusion_count / row.validation_replicates for row in rows]
    axis.plot(x, values, marker="o", linewidth=2, color="#2A6F97")
    axis.axhline(95.0, color="#B2182B", linestyle="--", label="detection gate (95%)")
    axis.set(title=title, xlabel=xlabel, ylabel="Datasets excluding no effect (%)", xticks=x)
    axis.set_ylim(max(0.0, min(values) - 5.0), 101.0)
    axis.legend(frameon=False, fontsize=8)
    for x_value, value, row in zip(x, values, rows, strict=True):
        axis.annotate(
            _short_status(row.status),
            (x_value, value),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )


def _plot_width(
    axis: Axes,
    x: list[float],
    rows: list[ConditionSummary],
    title: str,
    xlabel: str,
) -> None:
    values = [row.median_log_support_width for row in rows]
    axis.plot(x, values, marker="o", linewidth=2, color="#D97706")
    axis.axhline(0.80, color="#B2182B", linestyle="--", label="precision gate (<= 0.80)")
    axis.set(title=title, xlabel=xlabel, ylabel="Median log support width", xticks=x)
    axis.legend(frameon=False, fontsize=8)


def _short_status(status: str) -> str:
    return {
        "fully_recovered": "fully recovered",
        "detected_but_not_fully_recovered": "detected",
        "not_reliably_detected": "not reliable",
        "implementation_blocked": "blocked",
    }[status]


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("CSV rows must not be empty")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _quantile(values: list[int], probability: float) -> float:
    return float(np.quantile(np.asarray(values, dtype=np.float64), probability))


def _csv_int(row: dict[str, str], key: str) -> int:
    value = row.get(key)
    if value is None:
        raise ValueError(f"{key} is missing")
    return int(value)


def _float_value(mapping: dict[str, object], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric")
    return float(value)


def _int_value(mapping: dict[str, object], key: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _str_value(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be text")
    return value


def _bool_value(mapping: dict[str, object], key: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be Boolean")
    return value
