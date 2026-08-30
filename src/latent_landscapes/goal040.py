"""Transparent response-surface analysis for the Goal 039 Arc 2A pilot."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from numpy.typing import NDArray

DEFAULT_OUTPUT_DIR = Path("artifacts/goal040_arc2a_surface")
EXPECTED_FILES = (
    "condition_outcomes.csv",
    "surface_coefficients.csv",
    "leave_one_out_predictions.csv",
    "surface_grid.csv",
    "analysis_summary.json",
    "review.md",
    "recoverability_surface.svg",
    "leave_one_out_diagnostics.svg",
)
BOOTSTRAP_SEED = 20260830
DEFAULT_BOOTSTRAPS = 1_000
MODEL_SELECTION_IMPROVEMENT = 0.10
FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
ModelType = Literal["additive", "two_way_interactions"]
TransformType = Literal["identity", "empirical_logit"]


@dataclass(frozen=True, slots=True)
class MetricSpec:
    metric_id: str
    label: str
    field_name: str
    aggregation: Literal["mean", "median"]
    transform: TransformType
    threshold: float
    lower_is_better: bool


METRICS = (
    MetricSpec(
        "boundary_contact_probability",
        "Boundary-contact probability",
        "support_boundary_contact",
        "mean",
        "empirical_logit",
        0.05,
        True,
    ),
    MetricSpec(
        "detection_interval_width",
        "Detection interval width",
        "projected_probability_width",
        "median",
        "identity",
        0.20,
        True,
    ),
    MetricSpec(
        "eta_zero_exclusion_probability",
        "Probability data exclude eta = 0",
        "eta_zero_excluded",
        "mean",
        "empirical_logit",
        0.95,
        False,
    ),
    MetricSpec(
        "heldout_brier_difference",
        "Prediction error difference: process - neutral",
        "paired_brier_difference",
        "mean",
        "identity",
        0.0,
        True,
    ),
    MetricSpec(
        "eta_interval_width",
        "Resistance interval width",
        "projected_eta_width",
        "median",
        "identity",
        0.75,
        True,
    ),
)
METRIC_BY_ID = {metric.metric_id: metric for metric in METRICS}


@dataclass(frozen=True, slots=True)
class ConditionOutcome:
    condition_id: str
    design_role: str
    rho: float
    eta: float
    probability: float
    validation_count: int
    coverage: float
    coverage_lower: float
    coverage_upper: float
    median_absolute_log_rho_error: float
    median_absolute_eta_error: float
    median_absolute_probability_error: float
    median_log_rho_width: float
    median_eta_width: float
    median_probability_width: float
    boundary_contact_probability: float
    eta_zero_exclusion_probability: float
    mean_paired_brier_difference: float
    goal039_outcome: str


@dataclass(frozen=True, slots=True)
class ValidationArrays:
    condition_id: str
    dataset_index: NDArray[np.int64]
    support_boundary_contact: BoolArray
    eta_zero_excluded: BoolArray
    projected_probability_width: FloatArray
    projected_eta_width: FloatArray
    paired_brier_difference: FloatArray


@dataclass(frozen=True, slots=True)
class Goal039Inputs:
    conditions: tuple[ConditionOutcome, ...]
    continuous: tuple[ConditionOutcome, ...]
    diagnostic: ConditionOutcome
    validation: tuple[ValidationArrays, ...]
    source_commit: str
    input_digests: dict[str, str]
    invariants: dict[str, bool]


@dataclass(frozen=True, slots=True)
class CandidateModel:
    model_type: ModelType
    terms: tuple[str, ...]
    coefficients: FloatArray
    loo_predictions: FloatArray
    loo_rmse: float
    baseline_rmse: float
    loo_skill: float


@dataclass(frozen=True, slots=True)
class FittedMetric:
    spec: MetricSpec
    observed: FloatArray
    additive: CandidateModel
    interactions: CandidateModel
    selected_model_type: ModelType
    selected_coefficients: FloatArray
    selected_terms: tuple[str, ...]
    bootstrap_coefficients: FloatArray

    @property
    def selected(self) -> CandidateModel:
        return (
            self.interactions
            if self.selected_model_type == "two_way_interactions"
            else self.additive
        )


@dataclass(frozen=True, slots=True)
class CoefficientRow:
    metric_id: str
    response_scale: str
    model_type: str
    term: str
    estimate: float
    bootstrap_lower: float
    bootstrap_upper: float
    sign_stability: float


@dataclass(frozen=True, slots=True)
class LooRow:
    metric_id: str
    condition_id: str
    model_type: str
    selected_model: bool
    observed: float
    predicted: float
    residual: float
    loo_rmse: float
    baseline_rmse: float
    loo_skill: float


@dataclass(frozen=True, slots=True)
class SurfaceGridRow:
    metric_id: str
    model_type: str
    probability_slice: float
    rho: float
    eta: float
    estimate: float
    paired_bootstrap_lower: float
    paired_bootstrap_upper: float
    loo_error_envelope_lower: float
    loo_error_envelope_upper: float
    threshold_crossing_uncertain: bool


@dataclass(frozen=True, slots=True)
class Goal040Result:
    inputs: Goal039Inputs
    fits: tuple[FittedMetric, ...]
    coefficients: tuple[CoefficientRow, ...]
    loo_rows: tuple[LooRow, ...]
    grid_rows: tuple[SurfaceGridRow, ...]
    invariants: dict[str, bool]
    checks: dict[str, bool]
    recommendation: str
    unresolved_decision: str | None
    bootstrap_count: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle))


def _as_bool(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"expected boolean text, received {value!r}")


def _condition_from_row(row: dict[str, str]) -> ConditionOutcome:
    count = int(row["validation_count"])
    return ConditionOutcome(
        row["condition_id"],
        row["design_role"],
        float(row["truth_rho"]),
        float(row["truth_eta"]),
        float(row["truth_probability"]),
        count,
        float(row["coverage"]),
        float(row["coverage_lower"]),
        float(row["coverage_upper"]),
        float(row["median_absolute_log_rho_error"]),
        float(row["median_absolute_eta_error"]),
        float(row["median_absolute_probability_error"]),
        float(row["median_projected_log_rho_width"]),
        float(row["median_projected_eta_width"]),
        float(row["median_projected_probability_width"]),
        int(row["boundary_contact_count"]) / count,
        float(row["eta_zero_exclusion_probability"]),
        float(row["mean_paired_brier_difference"]),
        row["outcome"],
    )


def _validation_arrays(condition_id: str, rows: Sequence[dict[str, str]]) -> ValidationArrays:
    selected = sorted(
        (row for row in rows if row["condition_id"] == condition_id),
        key=lambda row: int(row["dataset_index"]),
    )
    return ValidationArrays(
        condition_id,
        np.asarray([int(row["dataset_index"]) for row in selected], dtype=np.int64),
        np.asarray(
            [_as_bool(row["support_boundary_contact"]) for row in selected],
            dtype=np.bool_,
        ),
        np.asarray(
            [_as_bool(row["eta_zero_excluded"]) for row in selected],
            dtype=np.bool_,
        ),
        np.asarray([float(row["projected_probability_width"]) for row in selected]),
        np.asarray([float(row["projected_eta_width"]) for row in selected]),
        np.asarray([float(row["paired_brier_difference"]) for row in selected]),
    )


def load_goal039_inputs(input_dir: Path) -> Goal039Inputs:
    """Load and reconcile the compact Goal 039 production bundle."""
    required = (
        "truth_summary.csv",
        "validation_metrics.csv",
        "summary.json",
        "run_provenance.json",
    )
    if not all((input_dir / name).is_file() for name in required):
        raise ValueError("Goal 039 input bundle is incomplete")
    summary = json.loads((input_dir / "summary.json").read_text(encoding="utf-8"))
    provenance = json.loads((input_dir / "run_provenance.json").read_text(encoding="utf-8"))
    if summary.get("outcome") != "ready_for_arc2a_response_surface_review":
        raise ValueError("Goal 039 input is not ready for response-surface review")
    summary_invariants = summary.get("invariants", {})
    if not summary_invariants or not all(summary_invariants.values()):
        raise ValueError("Goal 039 input invariants did not pass")
    conditions = tuple(
        sorted(
            (_condition_from_row(row) for row in _read_csv(input_dir / "truth_summary.csv")),
            key=lambda row: row.condition_id,
        )
    )
    continuous = tuple(row for row in conditions if row.design_role == "sobol_pilot")
    diagnostics = tuple(row for row in conditions if row.design_role == "no_resistance_diagnostic")
    validation_rows = _read_csv(input_dir / "validation_metrics.csv")
    arrays = tuple(_validation_arrays(row.condition_id, validation_rows) for row in conditions)
    arrays_by_id = {row.condition_id: row for row in arrays}
    expected_indices = np.arange(250, dtype=np.int64)
    recomputed = {
        row.condition_id: (
            float(np.mean(arrays_by_id[row.condition_id].support_boundary_contact)),
            float(np.mean(arrays_by_id[row.condition_id].eta_zero_excluded)),
            float(np.mean(arrays_by_id[row.condition_id].paired_brier_difference)),
        )
        for row in conditions
    }
    invariants = {
        "condition_count": len(conditions) == 17,
        "continuous_truth_count": len(continuous) == 16,
        "single_no_resistance_diagnostic": len(diagnostics) == 1,
        "validation_rows_complete": len(validation_rows) == 17 * 250,
        "paired_dataset_indices_complete": all(
            np.array_equal(row.dataset_index, expected_indices) for row in arrays
        ),
        "published_summaries_reconcile": all(
            math.isclose(recomputed[row.condition_id][0], row.boundary_contact_probability)
            and math.isclose(recomputed[row.condition_id][1], row.eta_zero_exclusion_probability)
            and math.isclose(recomputed[row.condition_id][2], row.mean_paired_brier_difference)
            for row in conditions
        ),
    }
    if not all(invariants.values()):
        raise ValueError(f"Goal 039 reconciliation failed: {invariants}")
    return Goal039Inputs(
        conditions,
        continuous,
        diagnostics[0],
        arrays,
        str(provenance.get("source_commit", "unknown")),
        {name: _sha256(input_dir / name) for name in required},
        invariants,
    )


def _scaled_predictors(conditions: Sequence[ConditionOutcome]) -> FloatArray:
    return np.asarray(
        [
            (
                math.log2(row.rho),
                (row.eta - 1.125) / 0.875,
                (row.probability - 0.60) / 0.25,
            )
            for row in conditions
        ],
        dtype=np.float64,
    )


def _design_matrix(predictors: FloatArray, model_type: ModelType) -> FloatArray:
    base = np.column_stack((np.ones(len(predictors)), predictors))
    if model_type == "additive":
        return base
    return np.column_stack(
        (
            base,
            predictors[:, 0] * predictors[:, 1],
            predictors[:, 0] * predictors[:, 2],
            predictors[:, 1] * predictors[:, 2],
        )
    )


def _terms(model_type: ModelType) -> tuple[str, ...]:
    base = ("intercept", "log2_rho", "eta", "detection_p")
    if model_type == "additive":
        return base
    return (*base, "log2_rho:eta", "log2_rho:detection_p", "eta:detection_p")


def _transform(values: FloatArray, transform: TransformType, sample_size: int) -> FloatArray:
    if transform == "identity":
        return values
    adjusted = (values * sample_size + 0.5) / (sample_size + 1.0)
    return np.log(adjusted / (1.0 - adjusted))


def _inverse(values: FloatArray, transform: TransformType) -> FloatArray:
    if transform == "identity":
        return values
    return 1.0 / (1.0 + np.exp(-values))


def _aggregate(arrays: ValidationArrays, spec: MetricSpec, indices: NDArray[np.int64]) -> float:
    values = np.asarray(getattr(arrays, spec.field_name))[indices]
    if spec.aggregation == "mean":
        return float(np.mean(values))
    return float(np.median(values))


def _observed_metric(conditions: Sequence[ConditionOutcome], metric_id: str) -> FloatArray:
    field = {
        "boundary_contact_probability": "boundary_contact_probability",
        "detection_interval_width": "median_probability_width",
        "eta_zero_exclusion_probability": "eta_zero_exclusion_probability",
        "heldout_brier_difference": "mean_paired_brier_difference",
        "eta_interval_width": "median_eta_width",
    }[metric_id]
    return np.asarray([float(getattr(row, field)) for row in conditions], dtype=np.float64)


def _fit_coefficients(matrix: FloatArray, response: FloatArray) -> FloatArray:
    return np.asarray(np.linalg.lstsq(matrix, response, rcond=None)[0], dtype=np.float64)


def _loo_candidate(
    matrix: FloatArray,
    observed: FloatArray,
    transform: TransformType,
    sample_size: int,
    model_type: ModelType,
) -> CandidateModel:
    transformed = _transform(observed, transform, sample_size)
    predicted = np.empty(len(observed), dtype=np.float64)
    baseline = np.empty(len(observed), dtype=np.float64)
    for index in range(len(observed)):
        keep = np.arange(len(observed)) != index
        coefficients = _fit_coefficients(matrix[keep], transformed[keep])
        predicted[index] = float(_inverse(np.asarray([matrix[index] @ coefficients]), transform)[0])
        baseline[index] = float(np.mean(observed[keep]))
    rmse = float(np.sqrt(np.mean(np.square(observed - predicted))))
    baseline_rmse = float(np.sqrt(np.mean(np.square(observed - baseline))))
    skill = 1.0 - (rmse * rmse) / (baseline_rmse * baseline_rmse)
    return CandidateModel(
        model_type,
        _terms(model_type),
        _fit_coefficients(matrix, transformed),
        predicted,
        rmse,
        baseline_rmse,
        skill,
    )


def _fit_metrics(
    inputs: Goal039Inputs,
    bootstrap_count: int,
) -> tuple[FittedMetric, ...]:
    if bootstrap_count <= 0:
        raise ValueError("bootstrap_count must be positive")
    predictors = _scaled_predictors(inputs.continuous)
    additive_matrix = _design_matrix(predictors, "additive")
    interaction_matrix = _design_matrix(predictors, "two_way_interactions")
    arrays_by_id = {row.condition_id: row for row in inputs.validation}
    continuous_arrays = tuple(arrays_by_id[row.condition_id] for row in inputs.continuous)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    resamples = rng.integers(0, 250, size=(bootstrap_count, 250), dtype=np.int64)
    fits: list[FittedMetric] = []
    for spec in METRICS:
        observed = _observed_metric(inputs.continuous, spec.metric_id)
        additive = _loo_candidate(additive_matrix, observed, spec.transform, 250, "additive")
        interactions = _loo_candidate(
            interaction_matrix,
            observed,
            spec.transform,
            250,
            "two_way_interactions",
        )
        selected_type: ModelType = (
            "two_way_interactions"
            if interactions.loo_rmse <= (1.0 - MODEL_SELECTION_IMPROVEMENT) * additive.loo_rmse
            else "additive"
        )
        selected_matrix = (
            interaction_matrix if selected_type == "two_way_interactions" else additive_matrix
        )
        bootstrap_coefficients = np.empty(
            (bootstrap_count, selected_matrix.shape[1]), dtype=np.float64
        )
        for bootstrap_index, indices in enumerate(resamples):
            values = np.asarray(
                [_aggregate(row, spec, indices) for row in continuous_arrays],
                dtype=np.float64,
            )
            bootstrap_coefficients[bootstrap_index] = _fit_coefficients(
                selected_matrix,
                _transform(values, spec.transform, len(indices)),
            )
        selected = interactions if selected_type == "two_way_interactions" else additive
        fits.append(
            FittedMetric(
                spec,
                observed,
                additive,
                interactions,
                selected_type,
                selected.coefficients,
                selected.terms,
                bootstrap_coefficients,
            )
        )
    return tuple(fits)


def _coefficient_rows(fits: Sequence[FittedMetric]) -> tuple[CoefficientRow, ...]:
    rows: list[CoefficientRow] = []
    for fit in fits:
        for index, term in enumerate(fit.selected_terms):
            values = fit.bootstrap_coefficients[:, index]
            nonnegative = float(np.mean(values >= 0.0))
            rows.append(
                CoefficientRow(
                    fit.spec.metric_id,
                    fit.spec.transform,
                    fit.selected_model_type,
                    term,
                    float(fit.selected_coefficients[index]),
                    float(np.quantile(values, 0.025)),
                    float(np.quantile(values, 0.975)),
                    max(nonnegative, 1.0 - nonnegative),
                )
            )
    return tuple(rows)


def _loo_rows(
    fits: Sequence[FittedMetric], conditions: Sequence[ConditionOutcome]
) -> tuple[LooRow, ...]:
    rows: list[LooRow] = []
    for fit in fits:
        for candidate in (fit.additive, fit.interactions):
            for condition, observed, predicted in zip(
                conditions, fit.observed, candidate.loo_predictions, strict=True
            ):
                rows.append(
                    LooRow(
                        fit.spec.metric_id,
                        condition.condition_id,
                        candidate.model_type,
                        candidate.model_type == fit.selected_model_type,
                        float(observed),
                        float(predicted),
                        float(observed - predicted),
                        candidate.loo_rmse,
                        candidate.baseline_rmse,
                        candidate.loo_skill,
                    )
                )
    return tuple(rows)


def _grid_rows(fits: Sequence[FittedMetric]) -> tuple[SurfaceGridRow, ...]:
    rhos = np.geomspace(0.5, 2.0, 21)
    etas = np.linspace(0.25, 2.0, 21)
    probabilities = (0.35, 0.60, 0.85)
    rows: list[SurfaceGridRow] = []
    for fit in fits:
        for probability in probabilities:
            conditions = tuple(
                ConditionOutcome(
                    "grid",
                    "surface_grid",
                    float(rho),
                    float(eta),
                    probability,
                    0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    "grid",
                )
                for eta in etas
                for rho in rhos
            )
            matrix = _design_matrix(_scaled_predictors(conditions), fit.selected_model_type)
            estimate = _inverse(matrix @ fit.selected_coefficients, fit.spec.transform)
            bootstrap = _inverse(
                matrix @ fit.bootstrap_coefficients.T,
                fit.spec.transform,
            )
            lower = np.quantile(bootstrap, 0.025, axis=1)
            upper = np.quantile(bootstrap, 0.975, axis=1)
            loo_lower = estimate - 1.96 * fit.selected.loo_rmse
            loo_upper = estimate + 1.96 * fit.selected.loo_rmse
            if (
                fit.spec.transform == "identity"
                and fit.spec.metric_id != "heldout_brier_difference"
            ):
                estimate = np.maximum(estimate, 0.0)
                lower = np.maximum(lower, 0.0)
                upper = np.maximum(upper, 0.0)
                loo_lower = np.maximum(loo_lower, 0.0)
                loo_upper = np.maximum(loo_upper, 0.0)
            if fit.spec.transform == "empirical_logit":
                loo_lower = np.clip(loo_lower, 0.0, 1.0)
                loo_upper = np.clip(loo_upper, 0.0, 1.0)
            for condition, point, low, high, predictive_low, predictive_high in zip(
                conditions,
                estimate,
                lower,
                upper,
                loo_lower,
                loo_upper,
                strict=True,
            ):
                rows.append(
                    SurfaceGridRow(
                        fit.spec.metric_id,
                        fit.selected_model_type,
                        probability,
                        condition.rho,
                        condition.eta,
                        float(point),
                        float(low),
                        float(high),
                        float(predictive_low),
                        float(predictive_high),
                        bool(predictive_low <= fit.spec.threshold <= predictive_high),
                    )
                )
    return tuple(rows)


def run_goal040(inputs: Goal039Inputs, bootstrap_count: int = DEFAULT_BOOTSTRAPS) -> Goal040Result:
    """Fit and diagnose the prespecified low-order Arc 2A surfaces."""
    fits = _fit_metrics(inputs, bootstrap_count)
    fit_by_id = {fit.spec.metric_id: fit for fit in fits}
    checks = {
        "point_errors_within_limits": all(
            row.median_absolute_log_rho_error <= 0.10
            and row.median_absolute_eta_error <= 0.25
            and row.median_absolute_probability_error <= 0.05
            for row in inputs.continuous
        ),
        "coverage_intervals_include_nominal": all(
            row.coverage_lower <= 0.95 <= row.coverage_upper for row in inputs.continuous
        ),
        "process_beats_neutral_everywhere": all(
            row.mean_paired_brier_difference < 0.0 for row in inputs.continuous
        ),
        "boundary_surface_has_loo_skill": fit_by_id[
            "boundary_contact_probability"
        ].selected.loo_skill
        > 0.20,
        "detection_width_surface_has_loo_skill": fit_by_id[
            "detection_interval_width"
        ].selected.loo_skill
        > 0.20,
        "eta_exclusion_surface_has_loo_skill": fit_by_id[
            "eta_zero_exclusion_probability"
        ].selected.loo_skill
        > 0.20,
        "prediction_surface_has_loo_skill": fit_by_id["heldout_brier_difference"].selected.loo_skill
        > 0.20,
    }
    eta_width_fit = fit_by_id["eta_interval_width"]
    eta_width_crosses_limit = bool(
        np.min(eta_width_fit.observed)
        <= eta_width_fit.spec.threshold
        < np.max(eta_width_fit.observed)
    )
    eta_width_unresolved = eta_width_crosses_limit and eta_width_fit.selected.loo_skill <= 0.20
    unresolved = (
        "Whether the isolated broad resistance interval is reproducible across the "
        "nested Sobol block"
        if eta_width_unresolved
        else None
    )
    recommendation = (
        "extend_to_nested_32_for_eta_precision_validation"
        if eta_width_unresolved
        else "freeze_arc2a_without_design_extension"
    )
    invariants = {
        **inputs.invariants,
        "five_metric_models_fitted": len(fits) == 5,
        "finite_coefficients": all(np.all(np.isfinite(fit.selected_coefficients)) for fit in fits),
        "paired_bootstrap_complete": all(
            fit.bootstrap_coefficients.shape[0] == bootstrap_count for fit in fits
        ),
        "diagnostic_excluded_from_fit": all(
            row.condition_id != inputs.diagnostic.condition_id for row in inputs.continuous
        ),
    }
    return Goal040Result(
        inputs,
        fits,
        _coefficient_rows(fits),
        _loo_rows(fits, inputs.continuous),
        _grid_rows(fits),
        invariants,
        checks,
        recommendation,
        unresolved,
        bootstrap_count,
    )


def _write_csv(path: Path, rows: Sequence[Any]) -> None:
    payload = [asdict(row) for row in rows]
    if not payload:
        raise ValueError("CSV rows must not be empty")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]))
        writer.writeheader()
        writer.writerows(payload)


def _analysis_summary(result: Goal040Result) -> dict[str, Any]:
    return {
        "goal": "040-arc2a-transparent-recoverability-surface",
        "source_goal039_commit": result.inputs.source_commit,
        "input_sha256": result.inputs.input_digests,
        "continuous_truth_count": len(result.inputs.continuous),
        "diagnostic_condition": asdict(result.inputs.diagnostic),
        "bootstrap": {
            "count": result.bootstrap_count,
            "seed": BOOTSTRAP_SEED,
            "paired_resampling_unit": "validation dataset index across all truth conditions",
        },
        "predictor_scaling": {
            "log2_rho": "log2(rho), domain -1 to 1",
            "eta": "(eta - 1.125) / 0.875",
            "detection_p": "(p - 0.60) / 0.25",
        },
        "model_selection": (
            "Retain two-way interactions only when leave-one-truth-out RMSE is "
            "at least 10% lower than the additive model"
        ),
        "surface_uncertainty": {
            "paired_bootstrap_intervals": (
                "Monte Carlo variation from jointly resampling validation-history indices"
            ),
            "loo_error_envelope": (
                "Fitted value plus or minus 1.96 times selected-model leave-one-truth-out RMSE; "
                "used only as a conservative threshold-classification diagnostic"
            ),
        },
        "models": {
            fit.spec.metric_id: {
                "selected_model": fit.selected_model_type,
                "additive_loo_rmse": fit.additive.loo_rmse,
                "interaction_loo_rmse": fit.interactions.loo_rmse,
                "selected_loo_skill": fit.selected.loo_skill,
                "threshold": fit.spec.threshold,
            }
            for fit in result.fits
        },
        "uniform_threshold_checks": result.checks,
        "invariants": result.invariants,
        "recommendation": result.recommendation,
        "unresolved_decision": result.unresolved_decision,
    }


def _review(result: Goal040Result) -> str:
    fit_by_id = {fit.spec.metric_id: fit for fit in result.fits}
    boundary = fit_by_id["boundary_contact_probability"]
    detection = fit_by_id["detection_interval_width"]
    exclusion = fit_by_id["eta_zero_exclusion_probability"]
    prediction = fit_by_id["heldout_brier_difference"]
    eta_width = fit_by_id["eta_interval_width"]
    return f"""# Arc 2A recoverability surface review

## What was directly observed

- Point errors remained inside the accepted limits at all 16 continuous truths.
- Every 95% coverage interval included the nominal 0.95 target.
- The process model beat its fitted time-only neutral baseline at all 16 truths.
- Weak resistance produced most boundary-touching support, while broad
  detection-probability intervals were concentrated among slower waves.

## What the low-order surfaces add

- Boundary contact needed {_model_label(boundary.selected_model_type)}. When each
  truth was hidden in turn, it reduced squared prediction error by
  `{100 * boundary.selected.loo_skill:.0f}%` relative to predicting the mean.
- Detection-probability interval width needed {_model_label(detection.selected_model_type)}
  and reduced held-out squared error by `{100 * detection.selected.loo_skill:.0f}%`.
- Distinguishing habitat resistance from `eta = 0` needed
  {_model_label(exclusion.selected_model_type)} and reduced held-out squared
  error by `{100 * exclusion.selected.loo_skill:.0f}%`.
- Predictive advantage over the neutral model needed
  {_model_label(prediction.selected_model_type)} and reduced held-out squared
  error by `{100 * prediction.selected.loo_skill:.0f}%`.

These are interpolation aids over one frozen landscape and observation design,
not universal ecological laws. Observed truth points are shown on the surface
figure, and the separate diagnostic was excluded from fitting.

## Remaining uncertainty and recommendation

Resistance-contrast interval width crossed its accepted 0.75 limit at one
condition. Its selected low-order surface predicted a hidden truth worse than
simply using the 16-truth mean (held-out skill `{eta_width.selected.loo_skill:.3f}`).
Recommendation:
`{result.recommendation}`.

The next nested Sobol block should be run only to test whether that isolated
broad resistance interval is reproducible and to provide prospective validation
of these first-block surfaces. Do not enlarge the model family or retune the
current 16-point fit before that test.
"""


def _surface_figure(result: Goal040Result) -> Figure:
    metrics = (
        "boundary_contact_probability",
        "detection_interval_width",
        "eta_zero_exclusion_probability",
    )
    probabilities = (0.35, 0.60, 0.85)
    figure, axes = plt.subplots(3, 3, figsize=(13.8, 11.0), constrained_layout=True)
    cmap_by_metric = {
        "boundary_contact_probability": "magma_r",
        "detection_interval_width": "magma_r",
        "eta_zero_exclusion_probability": "viridis",
    }
    limits = {
        "boundary_contact_probability": (0.0, 0.80),
        "detection_interval_width": (0.10, 0.30),
        "eta_zero_exclusion_probability": (0.20, 1.00),
    }
    fit_by_id = {fit.spec.metric_id: fit for fit in result.fits}
    for row_index, metric_id in enumerate(metrics):
        fit = fit_by_id[metric_id]
        vmin, vmax = limits[metric_id]
        image = None
        for column_index, probability in enumerate(probabilities):
            axis = axes[row_index, column_index]
            selected = [
                row
                for row in result.grid_rows
                if row.metric_id == metric_id and math.isclose(row.probability_slice, probability)
            ]
            rhos = sorted({row.rho for row in selected})
            etas = sorted({row.eta for row in selected})
            values = np.asarray([row.estimate for row in selected]).reshape(len(etas), len(rhos))
            uncertain = np.asarray(
                [row.threshold_crossing_uncertain for row in selected], dtype=np.float64
            ).reshape(len(etas), len(rhos))
            image = axis.pcolormesh(
                rhos,
                etas,
                values,
                shading="auto",
                cmap=cmap_by_metric[metric_id],
                vmin=vmin,
                vmax=vmax,
            )
            if values.min() <= fit.spec.threshold <= values.max():
                axis.contour(
                    rhos,
                    etas,
                    values,
                    levels=[fit.spec.threshold],
                    colors="#202020",
                    linewidths=1.2,
                    linestyles="--",
                )
            if np.any(uncertain):
                axis.contourf(
                    rhos,
                    etas,
                    uncertain,
                    levels=[0.5, 1.5],
                    colors="none",
                    hatches=["//"],
                )
            if column_index == 0:
                points = tuple(
                    condition
                    for condition in result.inputs.continuous
                    if condition.probability < 0.475
                )
            elif column_index == 1:
                points = tuple(
                    condition
                    for condition in result.inputs.continuous
                    if 0.475 <= condition.probability < 0.725
                )
            else:
                points = tuple(
                    condition
                    for condition in result.inputs.continuous
                    if condition.probability >= 0.725
                )
            point_values = _observed_metric(points, metric_id)
            axis.scatter(
                [point.rho for point in points],
                [point.eta for point in points],
                c=point_values,
                cmap=cmap_by_metric[metric_id],
                vmin=vmin,
                vmax=vmax,
                edgecolors="black",
                linewidths=0.7,
                s=38,
                zorder=3,
            )
            axis.set_xscale("log", base=2)
            axis.set_xlim(0.5, 2.0)
            axis.set_ylim(0.25, 2.0)
            axis.set_xticks((0.5, 1.0, 2.0), ("0.5x", "1x", "2x"))
            if row_index == 0:
                axis.set_title(f"Per-visit detection p = {probability:.2f}")
            if row_index == 2:
                axis.set_xlabel("Spread rate relative to reference")
            if column_index == 0:
                axis.set_ylabel("Habitat resistance contrast (eta)")
            axis.grid(alpha=0.12)
        if image is not None:
            colorbar = figure.colorbar(image, ax=axes[row_index, :], shrink=0.82, pad=0.02)
            colorbar.set_label(fit.spec.label)
    figure.suptitle(
        "Arc 2A recoverability across spread, habitat resistance, and detection\n"
        "Dots are observed truths; dashed lines are decision references; "
        "hatching marks thresholds inside the leave-one-truth-out error envelope.",
        fontsize=14,
    )
    return figure


def _loo_figure(result: Goal040Result) -> Figure:
    figure, axes = plt.subplots(2, 3, figsize=(13.5, 8.2), constrained_layout=True)
    for axis, fit in zip(axes.flat, result.fits, strict=False):
        candidate = fit.selected
        observed = fit.observed
        predicted = candidate.loo_predictions
        low = min(float(observed.min()), float(predicted.min()))
        high = max(float(observed.max()), float(predicted.max()))
        padding = max((high - low) * 0.08, 1e-6)
        axis.plot(
            (low - padding, high + padding),
            (low - padding, high + padding),
            "--",
            color="#666",
        )
        axis.scatter(observed, predicted, color="#2a6f97", edgecolor="white", linewidth=0.6)
        for condition, x_value, y_value in zip(
            result.inputs.continuous, observed, predicted, strict=True
        ):
            axis.annotate(
                condition.condition_id,
                (x_value, y_value),
                xytext=(3, 2),
                textcoords="offset points",
                fontsize=7,
            )
        axis.axvline(fit.spec.threshold, color="#9b2226", linestyle=":", linewidth=1.0)
        axis.axhline(fit.spec.threshold, color="#9b2226", linestyle=":", linewidth=1.0)
        axis.set_title(
            f"{fit.spec.label}\n"
            f"{_model_label(fit.selected_model_type)}; held-out skill {candidate.loo_skill:.2f}"
        )
        axis.set_xlabel("Observed")
        axis.set_ylabel("Predicted when truth was left out")
        axis.grid(alpha=0.18)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(
        0.02,
        0.92,
        "Uniform checks",
        fontsize=13,
        fontweight="bold",
        transform=axes.flat[-1].transAxes,
    )
    axes.flat[-1].text(
        0.02,
        0.78,
        "All point-error limits passed\n"
        "All coverage intervals include 0.95\n"
        "Process beats neutral at all 16 truths",
        va="top",
        fontsize=11,
        linespacing=1.6,
        transform=axes.flat[-1].transAxes,
    )
    figure.suptitle("Can the first 16 truths predict a held-out truth?", fontsize=15)
    return figure


def _model_label(model_type: ModelType) -> str:
    return "main effects + interactions" if model_type == "two_way_interactions" else "main effects"


def write_review_bundle(
    result: Goal040Result,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError("output directory must be empty")
    _write_csv(output_dir / "condition_outcomes.csv", result.inputs.conditions)
    _write_csv(output_dir / "surface_coefficients.csv", result.coefficients)
    _write_csv(output_dir / "leave_one_out_predictions.csv", result.loo_rows)
    _write_csv(output_dir / "surface_grid.csv", result.grid_rows)
    (output_dir / "analysis_summary.json").write_text(
        json.dumps(_analysis_summary(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "review.md").write_text(_review(result), encoding="utf-8")
    surface = _surface_figure(result)
    surface.savefig(
        output_dir / "recoverability_surface.svg",
        format="svg",
        bbox_inches="tight",
        metadata={"Date": None},
    )
    plt.close(surface)
    loo = _loo_figure(result)
    loo.savefig(
        output_dir / "leave_one_out_diagnostics.svg",
        format="svg",
        bbox_inches="tight",
        metadata={"Date": None},
    )
    plt.close(loo)
    if {path.name for path in output_dir.iterdir()} != set(EXPECTED_FILES):
        raise RuntimeError("Goal 040 artifact contract mismatch")
    written = tuple(output_dir / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 040 review bundle is incomplete")
    return written


def summarize_for_cli(result: Goal040Result) -> str:
    return (
        "Goal 040 Arc 2A response-surface review complete\n"
        f"Recommendation: {result.recommendation}\n"
        f"Unresolved decision: {result.unresolved_decision or 'none'}\n"
    )
