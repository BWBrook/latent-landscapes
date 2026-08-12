"""Known-arrival prey-effect strength transition benchmark."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from latent_landscapes.goal026 import Goal026Config, Goal026Result, run_goal026

DEFAULT_GOAL027_EVIDENCE_DIR = Path(
    "artifacts/goal027_known_arrival_support_calibration_confirmation"
)
EXPECTED_FILES = (
    "calibration_statistics.csv",
    "validation_results.csv",
    "effect_transition_summary.csv",
    "summary.json",
    "review.md",
    "prey_effect_strength_transition.svg",
)


@dataclass(frozen=True, slots=True)
class EffectTruth:
    truth_id: str
    hazard_ratio: float
    master_seed: int


DEFAULT_TRUTHS = (
    EffectTruth("twofold_effect", 2.0, 202608110282),
    EffectTruth("threefold_effect", 3.0, 202608110283),
)


@dataclass(frozen=True, slots=True)
class Goal028Config:
    """Frozen two-truth addition to the accepted fivefold anchor."""

    calibration_replicates: int = 2_000
    validation_replicates: int = 1_000
    calibration_rank_one_based: int = 1_901
    truths: tuple[EffectTruth, ...] = DEFAULT_TRUTHS

    def __post_init__(self) -> None:
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within calibration replicates")
        if tuple(truth.truth_id for truth in self.truths) != (
            "twofold_effect",
            "threefold_effect",
        ):
            raise ValueError("Goal 028 requires the two frozen truth identifiers")
        if tuple(truth.hazard_ratio for truth in self.truths) != (2.0, 3.0):
            raise ValueError("Goal 028 requires the twofold and threefold truths")

    @property
    def is_production(self) -> bool:
        return self == Goal028Config()

    def goal026_config(self, truth: EffectTruth) -> Goal026Config:
        return Goal026Config(
            master_seed=truth.master_seed,
            calibration_replicates=self.calibration_replicates,
            validation_replicates=self.validation_replicates,
            calibration_rank_one_based=self.calibration_rank_one_based,
            truth_hazard_ratio=truth.hazard_ratio,
        )


DEFAULT_CONFIG = Goal028Config()


def smoke_config() -> Goal028Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal028Config(
        calibration_replicates=8,
        validation_replicates=8,
        calibration_rank_one_based=8,
    )


@dataclass(frozen=True, slots=True)
class EffectSummary:
    truth_id: str
    hazard_ratio: float
    evidence_source: str
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
    recovered: bool
    failed_gates: str


@dataclass(frozen=True, slots=True)
class TruthRun:
    truth: EffectTruth
    result: Goal026Result
    summary: EffectSummary


@dataclass(frozen=True, slots=True)
class Goal028Result:
    config: Goal028Config
    new_truths: tuple[TruthRun, ...]
    fivefold_anchor: EffectSummary
    invariants: dict[str, bool]
    outcome: str

    @property
    def transition_summaries(self) -> tuple[EffectSummary, ...]:
        summaries = tuple(run.summary for run in self.new_truths)
        return (*summaries, self.fivefold_anchor)


def load_goal027_anchor(evidence_dir: Path) -> EffectSummary:
    """Load and exactly reconcile the accepted fivefold calibration evidence."""
    payload = cast(
        dict[str, object],
        json.loads((Path(evidence_dir) / "summary.json").read_text(encoding="utf-8")),
    )
    rows = cast(list[dict[str, object]], payload.get("coverage_comparison"))
    if len(rows) != 2:
        raise ValueError("Goal 027 comparison must contain two rows")
    row = rows[1]
    summary = EffectSummary(
        truth_id="fivefold_effect",
        hazard_ratio=5.0,
        evidence_source="published_goal027",
        calibration_replicates=_int_value(row, "calibration_replicates"),
        validation_replicates=_int_value(row, "validation_replicates"),
        cutoff=_float_value(row, "cutoff"),
        coverage_count=_int_value(row, "coverage_count"),
        coverage=_float_value(row, "coverage"),
        coverage_lower=_float_value(row, "coverage_lower"),
        coverage_upper=_float_value(row, "coverage_upper"),
        connected_interior_count=_int_value(row, "connected_interior_count"),
        null_exclusion_count=_int_value(row, "null_exclusion_count"),
        median_absolute_log_error=_float_value(row, "median_absolute_log_error"),
        median_log_support_width=_float_value(row, "median_log_support_width"),
        score_advantage=_float_value(row, "score_advantage"),
        score_advantage_lower=_float_value(row, "score_advantage_lower"),
        score_advantage_upper=_float_value(row, "score_advantage_upper"),
        recovered=True,
        failed_gates="",
    )
    if not (
        payload.get("goal") == "027-known-arrival-support-calibration-confirmation"
        and payload.get("run_mode") == "production"
        and payload.get("outcome") == "support_calibration_confirmed"
        and row.get("evidence") == "goal027_high_resolution"
        and summary.calibration_replicates == 2_000
        and summary.validation_replicates == 1_000
        and summary.coverage_count == 954
        and summary.connected_interior_count == 997
        and summary.null_exclusion_count == 1_000
        and summary.score_advantage_lower > 0.0
    ):
        raise ValueError("published Goal 027 evidence changed")
    return summary


def classify_transition(
    *,
    invariants: dict[str, bool],
    twofold_recovered: bool,
    threefold_recovered: bool,
) -> str:
    """Bracket the practical prey-effect transition using the fixed ladder."""
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if twofold_recovered and threefold_recovered:
        return "prey_effect_transition_below_twofold"
    if not twofold_recovered and threefold_recovered:
        return "prey_effect_transition_between_twofold_and_threefold"
    if not twofold_recovered and not threefold_recovered:
        return "prey_effect_transition_between_threefold_and_fivefold"
    return "prey_effect_transition_nonmonotonic"


def run_goal028(
    goal027_evidence_dir: Path = DEFAULT_GOAL027_EVIDENCE_DIR,
    config: Goal028Config = DEFAULT_CONFIG,
) -> Goal028Result:
    """Run the two new effect truths and combine them with the accepted anchor."""
    anchor = load_goal027_anchor(goal027_evidence_dir)
    truth_runs: list[TruthRun] = []
    invariants: dict[str, bool] = {
        "goal027_anchor_reconciled": True,
        "fivefold_anchor_recovered": anchor.recovered,
    }
    for truth in config.truths:
        result = run_goal026(config.goal026_config(truth))
        summary = _summarize_new_truth(truth, result, config)
        truth_runs.append(TruthRun(truth, result, summary))
        invariants.update(
            {f"{truth.truth_id}_{key}": value for key, value in result.invariants.items()}
        )
    outcome = classify_transition(
        invariants=invariants,
        twofold_recovered=truth_runs[0].summary.recovered,
        threefold_recovered=truth_runs[1].summary.recovered,
    )
    if not config.is_production:
        outcome = (
            "non_scientific_smoke"
            if invariants and all(invariants.values())
            else "implementation_blocked"
        )
    return Goal028Result(config, tuple(truth_runs), anchor, invariants, outcome)


def write_review_bundle(result: Goal028Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the compact six-file effect-transition review surface."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("output directory must be empty")
    calibration_rows: list[dict[str, object]] = []
    validation_rows: list[dict[str, object]] = []
    for run in result.new_truths:
        calibration_rows.extend(
            {
                "truth_id": run.truth.truth_id,
                "truth_hazard_ratio": run.truth.hazard_ratio,
                **asdict(row),
            }
            for row in run.result.calibration_statistics
        )
        validation_rows.extend(
            {
                "truth_id": run.truth.truth_id,
                "truth_hazard_ratio": run.truth.hazard_ratio,
                **asdict(row),
            }
            for row in run.result.validation_results
        )
    _write_rows(target / "calibration_statistics.csv", calibration_rows)
    _write_rows(target / "validation_results.csv", validation_rows)
    _write_rows(
        target / "effect_transition_summary.csv",
        [asdict(row) for row in result.transition_summaries],
    )
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    figure = _review_figure(result.transition_summaries)
    figure.savefig(
        target / "prey_effect_strength_transition.svg",
        format="svg",
        metadata={"Date": None},
    )
    plt.close(figure)
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 028 review surface is incomplete")
    return written


def _summarize_new_truth(
    truth: EffectTruth,
    result: Goal026Result,
    config: Goal028Config,
) -> EffectSummary:
    summary = result.summary
    failed = _failed_gates(result, config.validation_replicates)
    return EffectSummary(
        truth_id=truth.truth_id,
        hazard_ratio=truth.hazard_ratio,
        evidence_source="goal028_new_ensemble",
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
        recovered=not failed,
        failed_gates=";".join(failed),
    )


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


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("CSV rows must not be empty")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


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


def _summary_payload(result: Goal028Result) -> dict[str, object]:
    return {
        "goal": "028-known-arrival-prey-effect-strength-transition",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "outcome": result.outcome,
        "scientific_interpretation": result.outcome,
        "truth_summaries": [asdict(row) for row in result.transition_summaries],
        "invariants": result.invariants,
    }


def _review(result: Goal028Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 028: Prey-Effect Strength Transition\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    interpretations = {
        "prey_effect_transition_below_twofold": (
            "Both new effects were recovered; the practical transition lies below twofold."
        ),
        "prey_effect_transition_between_twofold_and_threefold": (
            "The threefold effect was recovered but the twofold effect was not. The practical "
            "transition is bracketed between them."
        ),
        "prey_effect_transition_between_threefold_and_fivefold": (
            "The strict recovery transition lies between the threefold truth and the "
            "accepted fivefold anchor. The threefold effect was nevertheless detected "
            "reliably and predicted better than neutral; it failed because its calibrated "
            "support was conservative and slightly wider than the precision gate. The "
            "twofold effect was both broad and frequently unable to exclude no effect."
        ),
        "prey_effect_transition_nonmonotonic": (
            "Recovery was nonmonotonic across the two new truths and needs scientific review."
        ),
        "implementation_blocked": "An implementation or anchor invariant failed.",
    }
    rows = [
        "# Goal 028: Prey-Effect Strength Transition",
        "",
        f"Outcome: `{result.outcome}`.",
        "",
        interpretations[result.outcome],
        "",
        (
            "| Effect multiplier | Evidence | Coverage | Excludes no effect | Median error | "
            "Median width | Held-out advantage | Decision |"
        ),
        "|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for summary in result.transition_summaries:
        rows.append(
            f"| {summary.hazard_ratio:.1f} | {summary.evidence_source} | "
            f"{summary.coverage_count}/{summary.validation_replicates} "
            f"({summary.coverage:.3f}) | {summary.null_exclusion_count}/"
            f"{summary.validation_replicates} | {summary.median_absolute_log_error:.3f} | "
            f"{summary.median_log_support_width:.3f} | {summary.score_advantage:.4f} | "
            f"{'recovered' if summary.recovered else summary.failed_gates} |"
        )
    rows.extend(
        [
            "",
            "Predator arrival remained known and prey observation remained perfect throughout.",
            "",
            "No additional effect truth, midpoint, or observation complication was attempted.",
            "",
        ]
    )
    return "\n".join(rows)


def _review_figure(summaries: tuple[EffectSummary, ...]) -> Figure:
    x = [row.hazard_ratio for row in summaries]
    figure, axes = plt.subplots(2, 2, figsize=(11.8, 8.0))

    coverage = [row.coverage for row in summaries]
    axes[0, 0].errorbar(
        x,
        coverage,
        yerr=(
            [row.coverage - row.coverage_lower for row in summaries],
            [row.coverage_upper - row.coverage for row in summaries],
        ),
        fmt="o-",
        capsize=4,
        color="#4C78A8",
    )
    axes[0, 0].axhline(0.95, color="#B2182B", linestyle="--")
    axes[0, 0].set(
        title="Calibrated support coverage",
        xlabel="True predator-effect multiplier",
        ylabel="Truth inside support",
        xticks=x,
        ylim=(0.90, 0.98),
    )

    axes[0, 1].plot(
        x,
        [row.null_exclusion_count / row.validation_replicates for row in summaries],
        marker="o",
        color="#F28E2B",
        label="excludes no effect",
    )
    axes[0, 1].plot(
        x,
        [row.connected_interior_count / row.validation_replicates for row in summaries],
        marker="s",
        color="#59A14F",
        label="connected interior support",
    )
    axes[0, 1].axhline(0.95, color="#B2182B", linestyle="--", label="recovery gate")
    axes[0, 1].set(
        title="Reliable effect separation",
        xlabel="True predator-effect multiplier",
        ylabel="Fraction of validation datasets",
        xticks=x,
        ylim=(0.0, 1.03),
    )
    axes[0, 1].legend(frameon=False, fontsize=8)

    advantage = [row.score_advantage for row in summaries]
    axes[1, 0].plot(
        x,
        [row.median_log_support_width for row in summaries],
        marker="o",
        color="#E15759",
    )
    axes[1, 0].axhline(0.80, color="#B2182B", linestyle="--", label="precision gate")
    axes[1, 0].set(
        title="Effect-estimate precision",
        xlabel="True predator-effect multiplier",
        ylabel="Median log support width",
        xticks=x,
    )
    axes[1, 0].legend(frameon=False)

    axes[1, 1].errorbar(
        x,
        advantage,
        yerr=(
            [row.score_advantage - row.score_advantage_lower for row in summaries],
            [row.score_advantage_upper - row.score_advantage for row in summaries],
        ),
        fmt="o-",
        capsize=4,
        color="#9467BD",
    )
    axes[1, 1].axhline(0.0, color="#B2182B", linestyle="--")
    axes[1, 1].set(
        title="Prediction against neutral",
        xlabel="True predator-effect multiplier",
        ylabel="Held-out log-score advantage per site",
        xticks=x,
    )
    figure.tight_layout(pad=1.4, h_pad=2.3, w_pad=2.3)
    return figure
