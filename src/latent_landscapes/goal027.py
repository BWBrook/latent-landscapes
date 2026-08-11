"""Higher-resolution confirmation of Goal 026 support calibration."""

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

from latent_landscapes.goal026 import (
    Goal026Config,
    Goal026Result,
    RecoverySummary,
    run_goal026,
)

MASTER_SEED = 20260811027
DEFAULT_GOAL026_EVIDENCE_DIR = Path(
    "artifacts/goal026_known_arrival_prey_persistence_positive_control"
)
EXPECTED_FILES = (
    "calibration_statistics.csv",
    "validation_results.csv",
    "coverage_comparison.csv",
    "summary.json",
    "review.md",
    "support_calibration_confirmation.svg",
)


@dataclass(frozen=True, slots=True)
class Goal027Config:
    """One prespecified higher-resolution calibration confirmation."""

    master_seed: int = MASTER_SEED
    calibration_replicates: int = 2_000
    validation_replicates: int = 1_000
    calibration_rank_one_based: int = 1_901

    def __post_init__(self) -> None:
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("replicate counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within calibration replicates")

    @property
    def is_production(self) -> bool:
        return self == Goal027Config()

    @property
    def goal026_config(self) -> Goal026Config:
        return Goal026Config(
            master_seed=self.master_seed,
            calibration_replicates=self.calibration_replicates,
            validation_replicates=self.validation_replicates,
            calibration_rank_one_based=self.calibration_rank_one_based,
        )


DEFAULT_CONFIG = Goal027Config()


def smoke_config() -> Goal027Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal027Config(
        calibration_replicates=8,
        validation_replicates=8,
        calibration_rank_one_based=8,
    )


@dataclass(frozen=True, slots=True)
class Goal026Anchor:
    cutoff: float
    validation_replicates: int
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


@dataclass(frozen=True, slots=True)
class CoverageComparison:
    evidence: str
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


@dataclass(frozen=True, slots=True)
class Goal027Result:
    config: Goal027Config
    anchor: Goal026Anchor
    confirmation: Goal026Result
    invariants: dict[str, bool]
    outcome: str

    @property
    def comparison(self) -> tuple[CoverageComparison, CoverageComparison]:
        summary = self.confirmation.summary
        return (
            CoverageComparison(
                "published_goal026",
                250,
                self.anchor.validation_replicates,
                self.anchor.cutoff,
                self.anchor.coverage_count,
                self.anchor.coverage,
                self.anchor.coverage_lower,
                self.anchor.coverage_upper,
                self.anchor.connected_interior_count,
                self.anchor.null_exclusion_count,
                self.anchor.median_absolute_log_error,
                self.anchor.median_log_support_width,
                self.anchor.score_advantage,
                self.anchor.score_advantage_lower,
                self.anchor.score_advantage_upper,
            ),
            CoverageComparison(
                "goal027_high_resolution",
                self.config.calibration_replicates,
                self.config.validation_replicates,
                summary.cutoff,
                summary.coverage_count,
                summary.coverage.estimate,
                summary.coverage.lower,
                summary.coverage.upper,
                summary.connected_interior_count,
                summary.null_exclusion_count,
                summary.median_absolute_log_error,
                summary.median_log_support_width,
                summary.heldout_log_score_advantage.estimate,
                summary.heldout_log_score_advantage.lower,
                summary.heldout_log_score_advantage.upper,
            ),
        )


def load_goal026_anchor(evidence_dir: Path) -> Goal026Anchor:
    """Load and exactly reconcile the published Goal 026 decision surface."""
    path = Path(evidence_dir) / "summary.json"
    payload = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    validation = cast(dict[str, object], payload.get("validation"))
    coverage = cast(dict[str, object], validation.get("coverage"))
    score = cast(dict[str, object], validation.get("heldout_log_score_advantage"))
    failed = tuple(cast(list[str], payload.get("failed_gates")))
    anchor = Goal026Anchor(
        cutoff=_float_value(cast(dict[str, object], payload.get("calibration")), "cutoff"),
        validation_replicates=_int_value(validation, "replicates"),
        coverage_count=_int_value(validation, "coverage_count"),
        coverage=_float_value(coverage, "estimate"),
        coverage_lower=_float_value(coverage, "lower"),
        coverage_upper=_float_value(coverage, "upper"),
        connected_interior_count=_int_value(validation, "connected_interior_count"),
        null_exclusion_count=_int_value(validation, "null_exclusion_count"),
        median_absolute_log_error=_float_value(validation, "median_absolute_log_error"),
        median_log_support_width=_float_value(validation, "median_log_support_width"),
        score_advantage=_float_value(score, "estimate"),
        score_advantage_lower=_float_value(score, "lower"),
        score_advantage_upper=_float_value(score, "upper"),
    )
    if not (
        payload.get("goal") == "026-known-arrival-prey-persistence-positive-control"
        and payload.get("run_mode") == "production"
        and payload.get("outcome") == "known_arrival_prey_effect_not_recovered"
        and failed == ("calibrated_coverage",)
        and anchor.validation_replicates == 250
        and anchor.coverage_count == 230
        and math.isclose(anchor.coverage, 0.92, rel_tol=0.0, abs_tol=1e-12)
        and anchor.connected_interior_count == 250
        and anchor.null_exclusion_count == 250
        and anchor.score_advantage_lower > 0.0
    ):
        raise ValueError("published Goal 026 evidence changed")
    return anchor


def classify_confirmation(
    *,
    invariants: dict[str, bool],
    summary: RecoverySummary,
    validation_count: int,
) -> str:
    """Separate calibration confirmation from inherited effect-information gates."""
    if not invariants or not all(invariants.values()) or validation_count <= 0:
        return "implementation_blocked"
    required_count = math.ceil(0.95 * validation_count)
    effect_recovered = (
        summary.connected_interior_count >= required_count
        and summary.null_exclusion_count >= required_count
        and summary.median_absolute_log_error <= 0.20
        and summary.median_log_support_width <= 0.80
        and summary.heldout_log_score_advantage.lower > 0.0
    )
    if not effect_recovered:
        return "effect_recovery_changed"
    if summary.coverage.lower <= 0.95 <= summary.coverage.upper:
        return "support_calibration_confirmed"
    if summary.coverage.upper < 0.95:
        return "persistent_support_undercoverage"
    return "support_calibration_inconclusive"


def run_goal027(
    goal026_evidence_dir: Path = DEFAULT_GOAL026_EVIDENCE_DIR,
    config: Goal027Config = DEFAULT_CONFIG,
) -> Goal027Result:
    """Run the single higher-resolution calibration confirmation."""
    anchor = load_goal026_anchor(goal026_evidence_dir)
    confirmation = run_goal026(config.goal026_config)
    invariants = {
        **confirmation.invariants,
        "goal026_anchor_reconciled": True,
        "independent_master_seed": config.master_seed != 20260811,
        "prespecified_production_rank": (
            not config.is_production or config.calibration_rank_one_based == 1_901
        ),
    }
    outcome = classify_confirmation(
        invariants=invariants,
        summary=confirmation.summary,
        validation_count=config.validation_replicates,
    )
    if not config.is_production:
        outcome = (
            "non_scientific_smoke"
            if invariants and all(invariants.values())
            else "implementation_blocked"
        )
    return Goal027Result(config, anchor, confirmation, invariants, outcome)


def write_review_bundle(result: Goal027Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the compact six-file calibration-confirmation surface."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("output directory must be empty")
    _write_rows(
        target / "calibration_statistics.csv",
        [asdict(row) for row in result.confirmation.calibration_statistics],
    )
    _write_rows(
        target / "validation_results.csv",
        [asdict(row) for row in result.confirmation.validation_results],
    )
    _write_rows(
        target / "coverage_comparison.csv",
        [asdict(row) for row in result.comparison],
    )
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    figure = _review_figure(result)
    figure.savefig(
        target / "support_calibration_confirmation.svg",
        format="svg",
        metadata={"Date": None},
    )
    plt.close(figure)
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 027 review surface is incomplete")
    return written


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


def _summary_payload(result: Goal027Result) -> dict[str, object]:
    return {
        "goal": "027-known-arrival-support-calibration-confirmation",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "outcome": result.outcome,
        "scientific_interpretation": result.outcome,
        "config": asdict(result.config),
        "coverage_comparison": [asdict(row) for row in result.comparison],
        "invariants": result.invariants,
    }


def _review(result: Goal027Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 027: Support-Calibration Confirmation\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    current = result.comparison[1]
    interpretations = {
        "support_calibration_confirmed": (
            "The larger independent ensemble places nominal 0.95 inside the validation "
            "coverage interval. Goal 026's miss is consistent with finite calibration noise."
        ),
        "persistent_support_undercoverage": (
            "The larger independent ensemble still under-covers. Effect information remains "
            "recoverable, but the support-interval construction needs a separate method decision."
        ),
        "support_calibration_inconclusive": (
            "The larger independent ensemble did not give a directional calibration decision."
        ),
        "effect_recovery_changed": (
            "At least one inherited effect-information gate changed in the confirmation run."
        ),
        "implementation_blocked": "An implementation or evidence invariant failed.",
    }
    rows = [
        "# Goal 027: Support-Calibration Confirmation",
        "",
        f"Outcome: `{result.outcome}`.",
        "",
        interpretations[result.outcome],
        "",
        "| Evidence | Calibration n | Validation n | Coverage | 95% interval | Cutoff |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in result.comparison:
        rows.append(
            f"| {row.evidence} | {row.calibration_replicates} | "
            f"{row.validation_replicates} | {row.coverage:.3f} | "
            f"{row.coverage_lower:.3f}-{row.coverage_upper:.3f} | {row.cutoff:.3f} |"
        )
    rows.extend(
        [
            "",
            "## Effect-information checks",
            "",
            (
                f"The confirmation produced {current.connected_interior_count}/"
                f"{current.validation_replicates} connected interior supports and "
                f"{current.null_exclusion_count}/{current.validation_replicates} exclusions "
                "of no predator effect."
            ),
            "",
            (
                f"Median absolute log-effect error was {current.median_absolute_log_error:.3f}; "
                f"median log support width was {current.median_log_support_width:.3f}."
            ),
            "",
            (
                f"Mean held-out log-score advantage over neutral was "
                f"{current.score_advantage:.4f} ({current.score_advantage_lower:.4f} to "
                f"{current.score_advantage_upper:.4f})."
            ),
            "",
            "No alternative seed, rank, cutoff, interval method, or biological model was tested.",
            "",
        ]
    )
    return "\n".join(rows)


def _review_figure(result: Goal027Result) -> Figure:
    figure, axes = plt.subplots(1, 2, figsize=(11.8, 4.8))
    comparison = result.comparison
    estimates = [row.coverage for row in comparison]
    lower = [row.coverage - row.coverage_lower for row in comparison]
    upper = [row.coverage_upper - row.coverage for row in comparison]
    axes[0].errorbar(
        (0, 1),
        estimates,
        yerr=(lower, upper),
        fmt="o",
        color="#4C78A8",
        capsize=5,
    )
    axes[0].axhline(0.95, color="#B2182B", linestyle="--", label="nominal 0.95")
    axes[0].set(
        title="Support coverage",
        xticks=(0, 1),
        xticklabels=("Goal 026\n250 validation", "Goal 027\n1,000 validation"),
        ylabel="Truth inside calibrated support",
        ylim=(0.87, 0.98),
    )
    axes[0].legend(frameon=False)

    values = [row.mle_hazard_ratio for row in result.confirmation.validation_results]
    axes[1].hist(values, bins=24, color="#59A14F", alpha=0.82)
    axes[1].axvline(1.0, color="#777777", linestyle=":", label="no effect")
    axes[1].axvline(5.0, color="#B2182B", linestyle="--", label="true fivefold effect")
    axes[1].set(
        title="Effect recovery in the confirmation ensemble",
        xlabel="Estimated post-arrival hazard multiplier",
        ylabel="Validation datasets",
    )
    axes[1].legend(frameon=False)
    figure.tight_layout(pad=1.4, w_pad=2.5)
    return figure
