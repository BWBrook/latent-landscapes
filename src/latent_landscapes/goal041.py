"""Prospective validation of the nested Arc 2A Sobol block."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import socket
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any

import matplotlib as mpl
import numpy as np
from scipy.stats import qmc  # type: ignore[import-untyped]

from latent_landscapes import goal038, goal039, goal040

mpl.use("Agg")
mpl.rcParams["svg.hashsalt"] = "latent-landscapes-goal041"
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("artifacts/goal041_arc2a_nested_validation")
DEFAULT_FROZEN_PREDICTIONS = Path(
    "docs/goals/041-arc2a-nested-prospective-validation/prospective_predictions.csv"
)
EXPECTED_FILES = (
    "new_truth_design.csv",
    "frozen_predictions.csv",
    "calibration_statistics.csv",
    "validation_metrics.csv",
    "truth_summary.csv",
    "prospective_scores.csv",
    "metric_validation_summary.csv",
    "summary.json",
    "run_provenance.json",
    "review.md",
    "prospective_validation.svg",
)
ACCEPTED_GOAL040_COMMIT = "a7f32a7d2d7d72d1694b739b028c6ffcdd4c0bc5"
NEW_TRUTH_COUNT = 16
LEARNABLE_METRICS = (
    "boundary_contact_probability",
    "detection_interval_width",
    "eta_zero_exclusion_probability",
    "heldout_brier_difference",
)


@dataclass(frozen=True, slots=True)
class NestedTruth:
    condition_id: str
    design_role: str
    unit_rho: float
    unit_eta: float
    unit_probability: float
    log2_rho: float
    rho: float
    eta: float
    probability: float

    @property
    def condition(self) -> goal039.TruthCondition:
        return goal039.TruthCondition(
            self.condition_id,
            self.design_role,
            self.rho,
            self.eta,
            self.probability,
        )


@dataclass(frozen=True, slots=True)
class FrozenPrediction:
    source_goal040_commit: str
    coefficient_sha256: str
    condition_id: str
    rho: float
    eta: float
    probability: float
    metric_id: str
    response_scale: str
    model_type: str
    predicted: float
    loo_rmse: float
    error_envelope_lower: float
    error_envelope_upper: float
    first_block_mean: float
    threshold: float
    lower_is_better: bool


@dataclass(frozen=True, slots=True)
class ProspectiveScore:
    condition_id: str
    metric_id: str
    predicted: float
    observed: float
    residual: float
    absolute_error: float
    squared_error: float
    inside_frozen_error_envelope: bool
    predicted_passes_threshold: bool
    observed_passes_threshold: bool
    threshold_class_correct: bool


@dataclass(frozen=True, slots=True)
class MetricValidationSummary:
    metric_id: str
    new_truth_count: int
    prospective_rmse: float
    goal040_loo_rmse: float
    frozen_mean_rmse: float
    prospective_skill: float
    error_envelope_coverage: float
    threshold_class_accuracy: float
    observed_pass_count: int
    observed_fail_count: int


@dataclass(frozen=True, slots=True)
class Goal041Result:
    config: goal039.Goal039Config
    nested_truths: tuple[NestedTruth, ...]
    campaign: goal039.Goal039Result
    frozen_predictions: tuple[FrozenPrediction, ...]
    scores: tuple[ProspectiveScore, ...]
    metric_summaries: tuple[MetricValidationSummary, ...]
    invariants: dict[str, bool]
    outcome: str
    source_commit: str


def generate_nested_truths() -> tuple[NestedTruth, ...]:
    """Return S17-S32 from the accepted nested scrambled Sobol sequence."""
    engine = qmc.Sobol(d=3, scramble=True, seed=goal038.SOBOL_SCRAMBLE_SEED)
    unit = np.asarray(engine.random_base2(m=5), dtype=np.float64)
    first_block = goal038.generate_pilot_truths()
    if not all(
        np.array_equal(
            unit[index],
            np.asarray((truth.unit_rho, truth.unit_eta, truth.unit_p), dtype=np.float64),
        )
        for index, truth in enumerate(first_block)
    ):
        raise RuntimeError("nested Sobol sequence does not reproduce the accepted first block")
    rows: list[NestedTruth] = []
    for index, (unit_rho, unit_eta, unit_probability) in enumerate(unit[16:], start=17):
        log2_rho = -1.0 + 2.0 * float(unit_rho)
        rows.append(
            NestedTruth(
                f"S{index:02d}",
                "sobol_nested_validation",
                float(unit_rho),
                float(unit_eta),
                float(unit_probability),
                log2_rho,
                float(2.0**log2_rho),
                0.25 + 1.75 * float(unit_eta),
                0.35 + 0.50 * float(unit_probability),
            )
        )
    return tuple(rows)


def production_config() -> goal039.Goal039Config:
    return goal039.Goal039Config(
        truths=tuple(row.condition for row in generate_nested_truths()),
    )


def smoke_config() -> goal039.Goal039Config:
    return goal039.Goal039Config(
        bank_size=8,
        calibration_replicates=4,
        validation_replicates=4,
        calibration_rank_one_based=4,
        base_rhos=(0.5, 1.0, 2.0),
        base_etas=(0.0, 0.5, 1.0, 1.5, 2.0),
        base_probabilities=(0.35, 0.65, 0.85),
        truths=tuple(row.condition for row in generate_nested_truths()[:2]),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle))


def _write_csv(path: Path, rows: Sequence[Any]) -> None:
    payload = [asdict(row) for row in rows]
    if not payload:
        raise ValueError("CSV rows must not be empty")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]))
        writer.writeheader()
        writer.writerows(payload)


def _as_bool(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"expected boolean text, received {value!r}")


def _feature_values(truth: NestedTruth) -> dict[str, float]:
    scaled_eta = (truth.eta - 1.125) / 0.875
    scaled_probability = (truth.probability - 0.60) / 0.25
    return {
        "intercept": 1.0,
        "log2_rho": truth.log2_rho,
        "eta": scaled_eta,
        "detection_p": scaled_probability,
        "log2_rho:eta": truth.log2_rho * scaled_eta,
        "log2_rho:detection_p": truth.log2_rho * scaled_probability,
        "eta:detection_p": scaled_eta * scaled_probability,
    }


def _metric_observed_field(metric_id: str) -> str:
    return {
        "boundary_contact_probability": "boundary_contact_probability",
        "detection_interval_width": "median_probability_width",
        "eta_zero_exclusion_probability": "eta_zero_exclusion_probability",
        "heldout_brier_difference": "mean_paired_brier_difference",
        "eta_interval_width": "median_eta_width",
    }[metric_id]


def _condition_metric_value(summary: goal039.TruthSummary, metric_id: str) -> float:
    if metric_id == "boundary_contact_probability":
        return summary.boundary_contact_count / summary.validation_count
    field = {
        "detection_interval_width": "median_projected_probability_width",
        "eta_zero_exclusion_probability": "eta_zero_exclusion_probability",
        "heldout_brier_difference": "mean_paired_brier_difference",
        "eta_interval_width": "median_projected_eta_width",
    }[metric_id]
    return float(getattr(summary, field))


def _inverse_response(value: float, response_scale: str) -> float:
    if response_scale == "identity":
        return value
    if response_scale == "empirical_logit":
        return 1.0 / (1.0 + math.exp(-value))
    raise ValueError(f"unknown response scale: {response_scale}")


def freeze_prospective_predictions(
    goal040_dir: Path,
    output_path: Path = DEFAULT_FROZEN_PREDICTIONS,
    *,
    source_goal040_commit: str = ACCEPTED_GOAL040_COMMIT,
) -> tuple[FrozenPrediction, ...]:
    """Freeze Goal 040 predictions before any nested simulation is run."""
    required = (
        goal040_dir / "surface_coefficients.csv",
        goal040_dir / "condition_outcomes.csv",
        goal040_dir / "analysis_summary.json",
    )
    if not all(path.is_file() for path in required):
        raise ValueError("Goal 040 prediction inputs are incomplete")
    coefficient_rows = _read_csv(required[0])
    condition_rows = tuple(
        row for row in _read_csv(required[1]) if row["design_role"] == "sobol_pilot"
    )
    summary = json.loads(required[2].read_text(encoding="utf-8"))
    models = summary.get("models", {})
    if len(condition_rows) != 16 or set(models) != set(goal040.METRIC_BY_ID):
        raise ValueError("Goal 040 prediction inputs do not match the accepted surface")
    coefficient_digest = _sha256(required[0])
    predictions: list[FrozenPrediction] = []
    for metric in goal040.METRICS:
        selected_model = str(models[metric.metric_id]["selected_model"])
        selected_rows = tuple(
            row
            for row in coefficient_rows
            if row["metric_id"] == metric.metric_id and row["model_type"] == selected_model
        )
        if not selected_rows:
            raise ValueError(f"coefficients missing for {metric.metric_id}")
        response_scale = selected_rows[0]["response_scale"]
        coefficients = {row["term"]: float(row["estimate"]) for row in selected_rows}
        first_block_mean = fmean(
            float(row[_metric_observed_field(metric.metric_id)]) for row in condition_rows
        )
        loo_key = (
            "interaction_loo_rmse"
            if selected_model == "two_way_interactions"
            else "additive_loo_rmse"
        )
        loo_rmse = float(models[metric.metric_id][loo_key])
        for truth in generate_nested_truths():
            features = _feature_values(truth)
            linear = sum(features[term] * estimate for term, estimate in coefficients.items())
            predicted = _inverse_response(linear, response_scale)
            lower = predicted - 1.96 * loo_rmse
            upper = predicted + 1.96 * loo_rmse
            if response_scale == "empirical_logit":
                lower, upper = max(0.0, lower), min(1.0, upper)
            elif metric.metric_id != "heldout_brier_difference":
                lower = max(0.0, lower)
                predicted = max(0.0, predicted)
            predictions.append(
                FrozenPrediction(
                    source_goal040_commit,
                    coefficient_digest,
                    truth.condition_id,
                    truth.rho,
                    truth.eta,
                    truth.probability,
                    metric.metric_id,
                    response_scale,
                    selected_model,
                    predicted,
                    loo_rmse,
                    lower,
                    upper,
                    first_block_mean,
                    metric.threshold,
                    metric.lower_is_better,
                )
            )
    if output_path.exists():
        raise ValueError("prospective prediction file already exists")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(output_path, predictions)
    return tuple(predictions)


def load_frozen_predictions(path: Path) -> tuple[FrozenPrediction, ...]:
    rows = tuple(
        FrozenPrediction(
            row["source_goal040_commit"],
            row["coefficient_sha256"],
            row["condition_id"],
            float(row["rho"]),
            float(row["eta"]),
            float(row["probability"]),
            row["metric_id"],
            row["response_scale"],
            row["model_type"],
            float(row["predicted"]),
            float(row["loo_rmse"]),
            float(row["error_envelope_lower"]),
            float(row["error_envelope_upper"]),
            float(row["first_block_mean"]),
            float(row["threshold"]),
            _as_bool(row["lower_is_better"]),
        )
        for row in _read_csv(path)
    )
    expected_ids = {truth.condition_id for truth in generate_nested_truths()}
    if (
        len(rows) != NEW_TRUTH_COUNT * len(goal040.METRICS)
        or {row.condition_id for row in rows} != expected_ids
        or {row.metric_id for row in rows} != set(goal040.METRIC_BY_ID)
        or {row.source_goal040_commit for row in rows} != {ACCEPTED_GOAL040_COMMIT}
    ):
        raise ValueError("frozen prospective predictions are incomplete or inconsistent")
    return rows


def _passes_threshold(value: float, prediction: FrozenPrediction) -> bool:
    if prediction.metric_id == "heldout_brier_difference":
        return value < prediction.threshold
    return (
        value <= prediction.threshold
        if prediction.lower_is_better
        else value >= prediction.threshold
    )


def _score_predictions(
    campaign: goal039.Goal039Result,
    predictions: Sequence[FrozenPrediction],
) -> tuple[ProspectiveScore, ...]:
    summaries = {row.condition_id: row for row in campaign.truth_summaries}
    rows: list[ProspectiveScore] = []
    for prediction in predictions:
        summary = summaries[prediction.condition_id]
        observed = _condition_metric_value(summary, prediction.metric_id)
        residual = observed - prediction.predicted
        predicted_pass = _passes_threshold(prediction.predicted, prediction)
        observed_pass = _passes_threshold(observed, prediction)
        rows.append(
            ProspectiveScore(
                prediction.condition_id,
                prediction.metric_id,
                prediction.predicted,
                observed,
                residual,
                abs(residual),
                residual * residual,
                prediction.error_envelope_lower <= observed <= prediction.error_envelope_upper,
                predicted_pass,
                observed_pass,
                predicted_pass == observed_pass,
            )
        )
    return tuple(rows)


def _summarize_scores(
    scores: Sequence[ProspectiveScore],
    predictions: Sequence[FrozenPrediction],
) -> tuple[MetricValidationSummary, ...]:
    rows: list[MetricValidationSummary] = []
    for metric in goal040.METRICS:
        selected = tuple(row for row in scores if row.metric_id == metric.metric_id)
        frozen = tuple(row for row in predictions if row.metric_id == metric.metric_id)
        mean_prediction = frozen[0].first_block_mean
        surface_sse = sum(row.squared_error for row in selected)
        mean_sse = sum((row.observed - mean_prediction) ** 2 for row in selected)
        skill = 1.0 - surface_sse / mean_sse if mean_sse > 0.0 else float("nan")
        rows.append(
            MetricValidationSummary(
                metric.metric_id,
                len(selected),
                math.sqrt(surface_sse / len(selected)),
                frozen[0].loo_rmse,
                math.sqrt(mean_sse / len(selected)),
                skill,
                fmean(row.inside_frozen_error_envelope for row in selected),
                fmean(row.threshold_class_correct for row in selected),
                sum(row.observed_passes_threshold for row in selected),
                sum(not row.observed_passes_threshold for row in selected),
            )
        )
    return tuple(rows)


def run_goal041(
    config: goal039.Goal039Config,
    frozen_predictions: Sequence[FrozenPrediction],
    *,
    workers: int = 1,
    source_commit: str = "unknown",
) -> Goal041Result:
    """Run and prospectively score the nested Arc 2A validation block."""
    all_truths = generate_nested_truths()
    ids = {truth.condition_id for truth in config.truths}
    nested_truths = tuple(row for row in all_truths if row.condition_id in ids)
    selected_predictions = tuple(row for row in frozen_predictions if row.condition_id in ids)
    campaign = goal039.run_goal039(config, workers=workers, source_commit=source_commit)
    scores = _score_predictions(campaign, selected_predictions)
    metric_summaries = _summarize_scores(scores, selected_predictions)
    is_production = config == production_config()
    summary_by_id = {row.metric_id: row for row in metric_summaries}
    eta_failures = summary_by_id["eta_interval_width"].observed_fail_count
    learned_surfaces_validate = all(
        summary_by_id[metric_id].prospective_skill > 0.0 for metric_id in LEARNABLE_METRICS
    )
    invariants = {
        **campaign.invariants,
        "nested_truth_count": len(nested_truths) == (NEW_TRUTH_COUNT if is_production else 2),
        "nested_truth_ids_exact": len(nested_truths) == len(ids),
        "frozen_prediction_count": len(selected_predictions)
        == len(nested_truths) * len(goal040.METRICS),
        "prospective_score_count": len(scores) == len(nested_truths) * len(goal040.METRICS),
        "five_metrics_scored": len(metric_summaries) == len(goal040.METRICS),
        "frozen_goal040_commit": {row.source_goal040_commit for row in selected_predictions}
        == {ACCEPTED_GOAL040_COMMIT},
        "finite_prospective_metrics": all(
            math.isfinite(value)
            for row in metric_summaries
            for value in (
                row.prospective_rmse,
                row.goal040_loo_rmse,
                row.frozen_mean_rmse,
                row.prospective_skill,
                row.error_envelope_coverage,
                row.threshold_class_accuracy,
            )
        ),
    }
    if not all(invariants.values()):
        outcome = "implementation_blocked"
    elif not is_production:
        outcome = "non_scientific_smoke"
    elif eta_failures > 0:
        outcome = "review_bounded_eta_precision_followup"
    elif learned_surfaces_validate:
        outcome = "freeze_arc2a_validated"
    else:
        outcome = "freeze_arc2a_with_surface_limits"
    return Goal041Result(
        config,
        nested_truths,
        campaign,
        selected_predictions,
        scores,
        metric_summaries,
        invariants,
        outcome,
        source_commit,
    )


def _summary_payload(result: Goal041Result) -> dict[str, Any]:
    campaign_summaries = result.campaign.truth_summaries
    return {
        "goal": "041-arc2a-nested-prospective-validation",
        "outcome": result.outcome,
        "new_truth_count": len(result.nested_truths),
        "calibration_replicates_per_truth": result.config.calibration_replicates,
        "validation_replicates_per_truth": result.config.validation_replicates,
        "source_goal040_commit": ACCEPTED_GOAL040_COMMIT,
        "metric_validation": [asdict(row) for row in result.metric_summaries],
        "supporting_checks": {
            "point_errors_within_limits": all(
                row.median_absolute_log_rho_error <= 0.10
                and row.median_absolute_eta_error <= 0.25
                and row.median_absolute_probability_error <= 0.05
                for row in campaign_summaries
            ),
            "coverage_intervals_include_nominal": all(
                row.coverage_lower <= 0.95 <= row.coverage_upper for row in campaign_summaries
            ),
            "process_beats_neutral_everywhere": all(
                row.mean_paired_brier_difference < 0.0 for row in campaign_summaries
            ),
        },
        "invariants": result.invariants,
    }


def _provenance_payload(result: Goal041Result) -> dict[str, Any]:
    return {
        "completed_utc": datetime.now(UTC).isoformat(),
        "source_commit": result.source_commit,
        "source_goal040_commit": ACCEPTED_GOAL040_COMMIT,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "worker_count": result.campaign.worker_count,
        "runtime_seconds": result.campaign.runtime_seconds,
        "stage_runtime_seconds": {
            "shared_bank": result.campaign.bank_runtime_seconds,
            "calibration": result.campaign.calibration_runtime_seconds,
            "validation_and_prediction": result.campaign.validation_runtime_seconds,
        },
        "master_seed": result.config.master_seed,
        "integration_bank_size": result.config.bank_size,
        "thread_limits": {
            name: os.environ.get(name, "")
            for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        },
    }


def _review(result: Goal041Result) -> str:
    if result.outcome == "non_scientific_smoke":
        return "# Goal 041 reduced smoke\n\nImplementation check only.\n"
    by_id = {row.metric_id: row for row in result.metric_summaries}
    validated = [
        metric_id for metric_id in LEARNABLE_METRICS if by_id[metric_id].prospective_skill > 0.0
    ]
    eta = by_id["eta_interval_width"]
    return f"""# Arc 2A nested prospective validation

## Result

Outcome: `{result.outcome}`.

Goal 040's predictions were frozen before these 16 conditions were simulated.
`{len(validated)}` of the four previously learnable surfaces predicted the new
block better than the frozen first-block mean. The detailed skill values are in
`metric_validation_summary.csv`; positive values favour the surface.

The resistance interval was broader than the accepted `0.75` limit at
`{eta.observed_fail_count}` of 16 new truths. This count answers the one question
that justified extending the Sobol design.

## Interpretation boundary

This is a prospective test on one fixed landscape and observation design. It
tests interpolation across spread rate, resistance contrast, and detection
probability; it does not establish landscape or sampling-design generality.
No surface was refitted and no new design points were selected after seeing the
outcomes.
"""


def _review_figure(result: Goal041Result) -> Figure:
    figure, axes = plt.subplots(2, 3, figsize=(14.5, 8.8), constrained_layout=True)
    colors = {
        True: "#2a6f97",
        False: "#d1495b",
    }
    by_metric = {row.metric_id: row for row in result.metric_summaries}
    for axis, metric in zip(axes.flat, goal040.METRICS, strict=False):
        rows = [row for row in result.scores if row.metric_id == metric.metric_id]
        values = [*map(lambda row: row.predicted, rows), *map(lambda row: row.observed, rows)]
        low, high = min(values), max(values)
        padding = max((high - low) * 0.08, 0.01)
        axis.plot(
            [low - padding, high + padding],
            [low - padding, high + padding],
            color="#555555",
            linestyle="--",
            linewidth=1.0,
        )
        axis.scatter(
            [row.predicted for row in rows],
            [row.observed for row in rows],
            c=[colors[row.inside_frozen_error_envelope] for row in rows],
            s=32,
            edgecolor="white",
            linewidth=0.4,
        )
        for row in rows:
            axis.annotate(
                row.condition_id,
                (row.predicted, row.observed),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=6.5,
            )
        summary = by_metric[metric.metric_id]
        axis.set_title(f"{metric.label}\nprospective skill = {summary.prospective_skill:.2f}")
        axis.set_xlabel("Frozen Goal 040 prediction")
        axis.set_ylabel("Observed in new block")
        axis.grid(alpha=0.18)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(
        0.02,
        0.95,
        "Blue: inside frozen error envelope\nRed: outside frozen error envelope\n"
        "Diagonal: exact prospective prediction",
        va="top",
        fontsize=11,
    )
    figure.suptitle("Prospective validation on Sobol truths S17-S32", fontsize=15)
    return figure


def write_review_bundle(
    result: Goal041Result,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, ...]:
    if result.outcome == "implementation_blocked":
        raise ValueError("cannot write a blocked Goal 041 result")
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError("output directory must be empty")
    _write_csv(output_dir / "new_truth_design.csv", result.nested_truths)
    _write_csv(output_dir / "frozen_predictions.csv", result.frozen_predictions)
    _write_csv(output_dir / "calibration_statistics.csv", result.campaign.calibration_metrics)
    _write_csv(output_dir / "validation_metrics.csv", result.campaign.validation_metrics)
    _write_csv(output_dir / "truth_summary.csv", result.campaign.truth_summaries)
    _write_csv(output_dir / "prospective_scores.csv", result.scores)
    _write_csv(output_dir / "metric_validation_summary.csv", result.metric_summaries)
    (output_dir / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "run_provenance.json").write_text(
        json.dumps(_provenance_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "review.md").write_text(_review(result), encoding="utf-8")
    figure = _review_figure(result)
    figure.savefig(
        output_dir / "prospective_validation.svg",
        format="svg",
        bbox_inches="tight",
        metadata={"Date": None},
    )
    plt.close(figure)
    unexpected = {path.name for path in output_dir.iterdir()} - set(EXPECTED_FILES)
    if unexpected:
        raise RuntimeError(f"unexpected Goal 041 artifact files: {sorted(unexpected)}")
    written = tuple(output_dir / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 041 review bundle is incomplete")
    return written


def summarize_for_cli(result: Goal041Result) -> str:
    eta = next(row for row in result.metric_summaries if row.metric_id == "eta_interval_width")
    validated = sum(
        row.metric_id in LEARNABLE_METRICS and row.prospective_skill > 0.0
        for row in result.metric_summaries
    )
    return (
        "Goal 041 nested Arc 2A prospective validation complete\n"
        f"Outcome: {result.outcome}\n"
        f"Previously learnable surfaces validated: {validated}/4\n"
        f"New broad resistance intervals: {eta.observed_fail_count}\n"
    )
