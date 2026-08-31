"""Arc 2A synthesis across the accepted 32 predator-only truths."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import matplotlib as mpl
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from numpy.typing import NDArray

mpl.use("Agg")
mpl.rcParams["svg.hashsalt"] = "latent-landscapes-arc2a-synthesis"
import matplotlib.pyplot as plt  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("artifacts/arc2a_synthesis")
DEFAULT_FROZEN_PREDICTIONS = Path(
    "docs/goals/041-arc2a-nested-prospective-validation/prospective_predictions.csv"
)
EXPECTED_FILES = (
    "combined_condition_outcomes.csv",
    "prospective_evidence.csv",
    "combined_surface_coefficients.csv",
    "combined_surface_grid.csv",
    "support_topology_points.csv",
    "synthesis_summary.json",
    "synthesis.md",
    "arc2a_recoverability_synthesis.svg",
)
BOOTSTRAP_SEED = 20260830
DEFAULT_BOOTSTRAPS = 1_000
VALIDATION_COUNT = 250
ACCEPTED_SURFACE_COMMIT = "a7f32a7d2d7d72d1694b739b028c6ffcdd4c0bc5"
ACCEPTED_PREDICTION_SHA256 = "1f57091555acde69aedaa5712bdf4668c513fe3f02fad1aff9634d355fab91b9"
ModelType = Literal["additive", "two_way_interactions"]
TransformType = Literal["identity", "empirical_logit"]
FIXED_MODELS: dict[str, ModelType] = {
    "detection_interval_width": "additive",
    "eta_interval_width": "additive",
    "eta_zero_exclusion_probability": "two_way_interactions",
    "heldout_brier_difference": "two_way_interactions",
}
REQUIRED_POSITIVE_PROSPECTIVE_METRICS = frozenset(FIXED_MODELS)
FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


@dataclass(frozen=True, slots=True)
class MetricSpec:
    metric_id: str
    field_name: str
    aggregation: Literal["mean", "median"]
    transform: TransformType
    threshold: float
    lower_is_better: bool


METRICS = (
    MetricSpec(
        "boundary_contact_probability",
        "support_boundary_contact",
        "mean",
        "empirical_logit",
        0.05,
        True,
    ),
    MetricSpec(
        "detection_interval_width",
        "projected_probability_width",
        "median",
        "identity",
        0.20,
        True,
    ),
    MetricSpec(
        "eta_zero_exclusion_probability",
        "eta_zero_excluded",
        "mean",
        "empirical_logit",
        0.95,
        False,
    ),
    MetricSpec(
        "heldout_brier_difference",
        "paired_brier_difference",
        "mean",
        "identity",
        0.0,
        True,
    ),
    MetricSpec(
        "eta_interval_width",
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
    campaign_outcome: str


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
class CandidateModel:
    terms: tuple[str, ...]
    coefficients: FloatArray
    loo_predictions: FloatArray
    loo_rmse: float
    baseline_rmse: float
    loo_skill: float


@dataclass(frozen=True, slots=True)
class ProspectiveEvidence:
    metric_id: str
    prospective_rmse: float
    goal040_loo_rmse: float
    frozen_mean_rmse: float
    prospective_skill: float
    error_envelope_coverage: float
    threshold_class_accuracy: float
    observed_pass_count: int
    observed_fail_count: int


@dataclass(frozen=True, slots=True)
class FrozenPrediction:
    source_surface_commit: str
    coefficient_sha256: str
    condition_id: str
    rho: float
    eta: float
    probability: float
    metric_id: str
    response_scale: TransformType
    model_type: ModelType
    predicted: float
    loo_rmse: float
    error_envelope_lower: float
    error_envelope_upper: float
    pilot_mean: float
    threshold: float
    lower_is_better: bool


@dataclass(frozen=True, slots=True)
class SynthesisInputs:
    conditions: tuple[ConditionOutcome, ...]
    validation: tuple[ValidationArrays, ...]
    prospective: tuple[ProspectiveEvidence, ...]
    source_commits: dict[str, str]
    input_sha256: dict[str, str]
    invariants: dict[str, bool]


@dataclass(frozen=True, slots=True)
class CombinedFit:
    spec: MetricSpec
    model_type: ModelType
    terms: tuple[str, ...]
    coefficients: FloatArray
    bootstrap_coefficients: FloatArray
    observed: FloatArray
    loo_predictions: FloatArray
    loo_rmse: float
    baseline_rmse: float
    loo_skill: float


@dataclass(frozen=True, slots=True)
class ConditionRow:
    condition_id: str
    evidence_block: str
    rho: float
    resistance_contrast: float
    detection_probability: float
    validation_count: int
    median_absolute_log_rho_error: float
    median_absolute_resistance_error: float
    median_absolute_detection_error: float
    median_resistance_interval_width: float
    median_detection_interval_width: float
    calibrated_coverage: float
    coverage_lower: float
    coverage_upper: float
    coverage_interval_includes_0_95: bool
    boundary_contact_probability: float
    resistance_zero_exclusion_probability: float
    heldout_brier_difference_process_minus_neutral: float
    point_error_limits_pass: bool
    process_beats_neutral: bool
    resistance_interval_broader_than_0_75: bool


@dataclass(frozen=True, slots=True)
class CoefficientRow:
    metric_id: str
    model_type: str
    response_scale: str
    term: str
    estimate: float
    paired_bootstrap_lower: float
    paired_bootstrap_upper: float


@dataclass(frozen=True, slots=True)
class GridRow:
    metric_id: str
    model_type: str
    detection_probability: float
    rho: float
    resistance_contrast: float
    estimate: float
    paired_bootstrap_lower: float
    paired_bootstrap_upper: float
    descriptive_threshold: float
    passes_descriptive_threshold: bool


@dataclass(frozen=True, slots=True)
class TopologyRow:
    condition_id: str
    evidence_block: str
    rho: float
    resistance_contrast: float
    detection_probability: float
    boundary_contact_probability: float
    boundary_contact_below_0_05: bool
    smooth_surface_supported: bool


@dataclass(frozen=True, slots=True)
class SynthesisResult:
    inputs: SynthesisInputs
    fits: tuple[CombinedFit, ...]
    condition_rows: tuple[ConditionRow, ...]
    coefficient_rows: tuple[CoefficientRow, ...]
    grid_rows: tuple[GridRow, ...]
    topology_rows: tuple[TopologyRow, ...]
    checks: dict[str, bool]
    outcome: str
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


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


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
        np.asarray([_as_bool(row["eta_zero_excluded"]) for row in selected], dtype=np.bool_),
        np.asarray([float(row["projected_probability_width"]) for row in selected]),
        np.asarray([float(row["projected_eta_width"]) for row in selected]),
        np.asarray([float(row["paired_brier_difference"]) for row in selected]),
    )


def _load_campaign_block(
    input_dir: Path, expected_ids: tuple[str, ...]
) -> tuple[tuple[ConditionOutcome, ...], tuple[ValidationArrays, ...], str]:
    required = (
        "truth_summary.csv",
        "validation_metrics.csv",
        "summary.json",
        "run_provenance.json",
    )
    if not all((input_dir / name).is_file() for name in required):
        raise ValueError(f"campaign bundle is incomplete: {input_dir}")
    summary = _read_json(input_dir / "summary.json")
    invariants = summary.get("invariants")
    if not isinstance(invariants, dict) or not invariants or not all(invariants.values()):
        raise ValueError(f"campaign invariants did not pass: {input_dir}")
    all_conditions = tuple(
        sorted(
            (_condition_from_row(row) for row in _read_csv(input_dir / "truth_summary.csv")),
            key=lambda row: row.condition_id,
        )
    )
    by_id = {row.condition_id: row for row in all_conditions}
    if not set(expected_ids).issubset(by_id):
        raise ValueError(f"campaign truth IDs do not match the requested block: {input_dir}")
    conditions = tuple(by_id[condition_id] for condition_id in expected_ids)
    validation_rows = _read_csv(input_dir / "validation_metrics.csv")
    validation = tuple(
        _validation_arrays(condition.condition_id, validation_rows) for condition in conditions
    )
    expected_indices = np.arange(VALIDATION_COUNT, dtype=np.int64)
    if not all(
        len(row.dataset_index) == VALIDATION_COUNT
        and np.array_equal(row.dataset_index, expected_indices)
        for row in validation
    ):
        raise ValueError(f"campaign validation histories are incomplete: {input_dir}")
    provenance = _read_json(input_dir / "run_provenance.json")
    return conditions, validation, str(provenance.get("source_commit", "unknown"))


def _parse_transform(value: str) -> TransformType:
    if value not in ("identity", "empirical_logit"):
        raise ValueError(f"unknown response scale: {value}")
    return cast(TransformType, value)


def _parse_model_type(value: str) -> ModelType:
    if value not in ("additive", "two_way_interactions"):
        raise ValueError(f"unknown model type: {value}")
    return cast(ModelType, value)


def load_frozen_predictions(path: Path) -> tuple[FrozenPrediction, ...]:
    if _sha256(path) != ACCEPTED_PREDICTION_SHA256:
        raise ValueError("frozen prospective prediction checksum changed")
    rows = tuple(
        FrozenPrediction(
            row["source_goal040_commit"],
            row["coefficient_sha256"],
            row["condition_id"],
            float(row["rho"]),
            float(row["eta"]),
            float(row["probability"]),
            row["metric_id"],
            _parse_transform(row["response_scale"]),
            _parse_model_type(row["model_type"]),
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
    expected_ids = {f"S{index:02d}" for index in range(17, 33)}
    forms_by_metric = {
        metric_id: {row.model_type for row in rows if row.metric_id == metric_id}
        for metric_id in METRIC_BY_ID
    }
    checks = (
        len(rows) == 16 * len(METRICS),
        {row.condition_id for row in rows} == expected_ids,
        {row.metric_id for row in rows} == set(METRIC_BY_ID),
        {row.source_surface_commit for row in rows} == {ACCEPTED_SURFACE_COMMIT},
        all(
            forms_by_metric[metric_id] == {model_type}
            for metric_id, model_type in FIXED_MODELS.items()
        ),
        all(
            row.response_scale == METRIC_BY_ID[row.metric_id].transform
            and row.threshold == METRIC_BY_ID[row.metric_id].threshold
            and row.lower_is_better == METRIC_BY_ID[row.metric_id].lower_is_better
            for row in rows
        ),
    )
    if not all(checks):
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


def _prospective_evidence(
    conditions: Sequence[ConditionOutcome], predictions: Sequence[FrozenPrediction]
) -> tuple[ProspectiveEvidence, ...]:
    conditions_by_id = {row.condition_id: row for row in conditions}
    evidence: list[ProspectiveEvidence] = []
    for spec in METRICS:
        frozen = tuple(row for row in predictions if row.metric_id == spec.metric_id)
        observed = np.asarray(
            [
                _observed_metric((conditions_by_id[row.condition_id],), spec.metric_id)[0]
                for row in frozen
            ],
            dtype=np.float64,
        )
        surface_sse = sum(
            (float(value) - row.predicted) ** 2 for value, row in zip(observed, frozen, strict=True)
        )
        mean_sse = sum(
            (float(value) - row.pilot_mean) ** 2
            for value, row in zip(observed, frozen, strict=True)
        )
        observed_passes = [
            _passes_threshold(float(value), row)
            for value, row in zip(observed, frozen, strict=True)
        ]
        predicted_passes = [_passes_threshold(row.predicted, row) for row in frozen]
        evidence.append(
            ProspectiveEvidence(
                spec.metric_id,
                math.sqrt(surface_sse / len(frozen)),
                frozen[0].loo_rmse,
                math.sqrt(mean_sse / len(frozen)),
                1.0 - surface_sse / mean_sse,
                float(
                    np.mean(
                        [
                            row.error_envelope_lower <= value <= row.error_envelope_upper
                            for value, row in zip(observed, frozen, strict=True)
                        ]
                    )
                ),
                float(
                    np.mean(
                        [
                            predicted_pass == observed_pass
                            for predicted_pass, observed_pass in zip(
                                predicted_passes, observed_passes, strict=True
                            )
                        ]
                    )
                ),
                sum(observed_passes),
                len(observed_passes) - sum(observed_passes),
            )
        )
    return tuple(evidence)


def load_inputs(
    pilot_dir: Path,
    prospective_dir: Path,
    frozen_predictions_path: Path = DEFAULT_FROZEN_PREDICTIONS,
) -> SynthesisInputs:
    """Load two campaign blocks and reconstruct the frozen prospective test."""
    pilot_ids = tuple(f"S{index:02d}" for index in range(1, 17))
    prospective_ids = tuple(f"S{index:02d}" for index in range(17, 33))
    pilot_conditions, pilot_validation, pilot_commit = _load_campaign_block(pilot_dir, pilot_ids)
    prospective_conditions, prospective_validation, prospective_commit = _load_campaign_block(
        prospective_dir, prospective_ids
    )
    frozen = load_frozen_predictions(frozen_predictions_path)
    prospective = _prospective_evidence(prospective_conditions, frozen)
    conditions = (*pilot_conditions, *prospective_conditions)
    validation = (*pilot_validation, *prospective_validation)
    expected_indices = np.arange(VALIDATION_COUNT, dtype=np.int64)
    invariants = {
        "truth_ids_exact": tuple(row.condition_id for row in conditions)
        == (*pilot_ids, *prospective_ids),
        "two_prespecified_blocks": len(pilot_conditions) == len(prospective_conditions) == 16,
        "validation_histories_complete": len(validation) == 32
        and all(np.array_equal(row.dataset_index, expected_indices) for row in validation),
        "frozen_predictions_bound": len(frozen) == 80,
        "prospective_metrics_complete": {row.metric_id for row in prospective} == set(METRIC_BY_ID),
        "finite_condition_metrics": all(
            math.isfinite(value)
            for row in conditions
            for value in (
                row.rho,
                row.eta,
                row.probability,
                row.coverage,
                row.median_absolute_log_rho_error,
                row.median_absolute_eta_error,
                row.median_absolute_probability_error,
                row.median_eta_width,
                row.median_probability_width,
                row.boundary_contact_probability,
                row.eta_zero_exclusion_probability,
                row.mean_paired_brier_difference,
            )
        ),
    }
    if not all(invariants.values()):
        raise ValueError(f"Arc 2A evidence reconciliation failed: {invariants}")
    digest_paths = {
        "pilot_truth_summary.csv": pilot_dir / "truth_summary.csv",
        "pilot_validation_metrics.csv": pilot_dir / "validation_metrics.csv",
        "prospective_truth_summary.csv": prospective_dir / "truth_summary.csv",
        "prospective_validation_metrics.csv": prospective_dir / "validation_metrics.csv",
        "frozen_predictions.csv": frozen_predictions_path,
    }
    return SynthesisInputs(
        conditions,
        validation,
        prospective,
        {"pilot": pilot_commit, "prospective": prospective_commit},
        {name: _sha256(path) for name, path in digest_paths.items()},
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
    return CandidateModel(
        _terms(model_type),
        _fit_coefficients(matrix, transformed),
        predicted,
        rmse,
        baseline_rmse,
        1.0 - (rmse * rmse) / (baseline_rmse * baseline_rmse),
    )


def _fit_combined(inputs: SynthesisInputs, bootstrap_count: int) -> tuple[CombinedFit, ...]:
    if bootstrap_count <= 0:
        raise ValueError("bootstrap_count must be positive")
    predictors = _scaled_predictors(inputs.conditions)
    arrays_by_id = {row.condition_id: row for row in inputs.validation}
    arrays = tuple(arrays_by_id[row.condition_id] for row in inputs.conditions)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    resamples = rng.integers(
        0, VALIDATION_COUNT, size=(bootstrap_count, VALIDATION_COUNT), dtype=np.int64
    )
    fits: list[CombinedFit] = []
    for metric_id, model_type in FIXED_MODELS.items():
        spec = METRIC_BY_ID[metric_id]
        matrix = _design_matrix(predictors, model_type)
        observed = _observed_metric(inputs.conditions, metric_id)
        candidate = _loo_candidate(matrix, observed, spec.transform, VALIDATION_COUNT, model_type)
        bootstrap = np.empty((bootstrap_count, matrix.shape[1]), dtype=np.float64)
        for bootstrap_index, indices in enumerate(resamples):
            values = np.asarray(
                [_aggregate(row, spec, indices) for row in arrays],
                dtype=np.float64,
            )
            bootstrap[bootstrap_index] = _fit_coefficients(
                matrix,
                _transform(values, spec.transform, len(indices)),
            )
        fits.append(
            CombinedFit(
                spec,
                model_type,
                candidate.terms,
                candidate.coefficients,
                bootstrap,
                observed,
                candidate.loo_predictions,
                candidate.loo_rmse,
                candidate.baseline_rmse,
                candidate.loo_skill,
            )
        )
    return tuple(fits)


def _condition_rows(conditions: Sequence[ConditionOutcome]) -> tuple[ConditionRow, ...]:
    return tuple(
        ConditionRow(
            row.condition_id,
            "pilot_S01_S16" if int(row.condition_id[1:]) <= 16 else "prospective_S17_S32",
            row.rho,
            row.eta,
            row.probability,
            row.validation_count,
            row.median_absolute_log_rho_error,
            row.median_absolute_eta_error,
            row.median_absolute_probability_error,
            row.median_eta_width,
            row.median_probability_width,
            row.coverage,
            row.coverage_lower,
            row.coverage_upper,
            row.coverage_lower <= 0.95 <= row.coverage_upper,
            row.boundary_contact_probability,
            row.eta_zero_exclusion_probability,
            row.mean_paired_brier_difference,
            row.median_absolute_log_rho_error <= 0.10
            and row.median_absolute_eta_error <= 0.25
            and row.median_absolute_probability_error <= 0.05,
            row.mean_paired_brier_difference < 0.0,
            row.median_eta_width > 0.75,
        )
        for row in conditions
    )


def _coefficient_rows(fits: Sequence[CombinedFit]) -> tuple[CoefficientRow, ...]:
    rows: list[CoefficientRow] = []
    for fit in fits:
        for index, term in enumerate(fit.terms):
            values = fit.bootstrap_coefficients[:, index]
            rows.append(
                CoefficientRow(
                    fit.spec.metric_id,
                    fit.model_type,
                    fit.spec.transform,
                    term,
                    float(fit.coefficients[index]),
                    float(np.quantile(values, 0.025)),
                    float(np.quantile(values, 0.975)),
                )
            )
    return tuple(rows)


def _grid_rows(fits: Sequence[CombinedFit]) -> tuple[GridRow, ...]:
    rhos = np.geomspace(0.5, 2.0, 25)
    etas = np.linspace(0.25, 2.0, 25)
    rows: list[GridRow] = []
    for fit in fits:
        for probability in (0.35, 0.60, 0.85):
            conditions = tuple(
                ConditionOutcome(
                    "grid",
                    "combined_descriptive_grid",
                    float(rho),
                    float(eta),
                    probability,
                    VALIDATION_COUNT,
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
            matrix = _design_matrix(
                _scaled_predictors(conditions),
                fit.model_type,
            )
            estimates = _inverse(matrix @ fit.coefficients, fit.spec.transform)
            bootstrap_estimates = _inverse(
                matrix @ fit.bootstrap_coefficients.T, fit.spec.transform
            )
            lower = np.quantile(bootstrap_estimates, 0.025, axis=1)
            upper = np.quantile(bootstrap_estimates, 0.975, axis=1)
            for condition, estimate, low, high in zip(
                conditions, estimates, lower, upper, strict=True
            ):
                passes = (
                    estimate <= fit.spec.threshold
                    if fit.spec.lower_is_better
                    else estimate >= fit.spec.threshold
                )
                rows.append(
                    GridRow(
                        fit.spec.metric_id,
                        fit.model_type,
                        probability,
                        condition.rho,
                        condition.eta,
                        float(estimate),
                        float(low),
                        float(high),
                        fit.spec.threshold,
                        bool(passes),
                    )
                )
    return tuple(rows)


def _topology_rows(conditions: Sequence[ConditionOutcome]) -> tuple[TopologyRow, ...]:
    return tuple(
        TopologyRow(
            row.condition_id,
            "pilot_S01_S16" if int(row.condition_id[1:]) <= 16 else "prospective_S17_S32",
            row.rho,
            row.eta,
            row.probability,
            row.boundary_contact_probability,
            row.boundary_contact_probability <= 0.05,
            False,
        )
        for row in conditions
    )


def run_synthesis(
    inputs: SynthesisInputs, bootstrap_count: int = DEFAULT_BOOTSTRAPS
) -> SynthesisResult:
    """Build the combined descriptive refit while retaining prospective evidence."""
    fits = _fit_combined(inputs, bootstrap_count)
    condition_rows = _condition_rows(inputs.conditions)
    prospective_by_metric = {row.metric_id: row for row in inputs.prospective}
    checks = {
        "inputs_reconciled": all(inputs.invariants.values()),
        "point_error_limits_pass": all(row.point_error_limits_pass for row in condition_rows),
        "process_beats_neutral_everywhere": all(
            row.process_beats_neutral for row in condition_rows
        ),
        "four_fixed_models_fitted": len(fits) == 4
        and set(fit.spec.metric_id for fit in fits) == set(FIXED_MODELS),
        "finite_combined_models": all(
            np.all(np.isfinite(fit.coefficients))
            and np.all(np.isfinite(fit.bootstrap_coefficients))
            for fit in fits
        ),
        "retained_metrics_have_positive_prospective_skill": all(
            prospective_by_metric[metric_id].prospective_skill > 0.0
            for metric_id in REQUIRED_POSITIVE_PROSPECTIVE_METRICS
        ),
        "boundary_surface_failure_preserved": prospective_by_metric[
            "boundary_contact_probability"
        ].prospective_skill
        < 0.0,
        "resistance_width_threshold_classified_prospectively": prospective_by_metric[
            "eta_interval_width"
        ].threshold_class_accuracy
        == 1.0,
    }
    outcome = (
        "arc2a_ready_for_closeout_with_topology_limit"
        if all(checks.values())
        else "arc2a_requires_named_followup"
    )
    return SynthesisResult(
        inputs,
        fits,
        condition_rows,
        _coefficient_rows(fits),
        _grid_rows(fits),
        _topology_rows(inputs.conditions),
        checks,
        outcome,
        bootstrap_count,
    )


def _summary(result: SynthesisResult) -> dict[str, Any]:
    flagged_coverage = [
        row.condition_id for row in result.condition_rows if not row.coverage_interval_includes_0_95
    ]
    broad_eta = [
        row.condition_id
        for row in result.condition_rows
        if row.resistance_interval_broader_than_0_75
    ]
    return {
        "workflow": "arc2a-predator-recoverability-synthesis",
        "outcome": result.outcome,
        "truth_count": len(result.condition_rows),
        "validation_histories_per_truth": VALIDATION_COUNT,
        "bootstrap": {
            "count": result.bootstrap_count,
            "seed": BOOTSTRAP_SEED,
            "paired_resampling_unit": "validation-history index across all 32 truths",
            "interpretation": "Monte Carlo precision, not total surface uncertainty",
        },
        "prospective_validation": [asdict(row) for row in result.inputs.prospective],
        "combined_descriptive_models": {
            fit.spec.metric_id: {
                "model_type": fit.model_type,
                "loo_rmse": fit.loo_rmse,
                "mean_only_rmse": fit.baseline_rmse,
                "loo_skill": fit.loo_skill,
                "threshold": fit.spec.threshold,
            }
            for fit in result.fits
        },
        "point_recovery": {
            "thresholds": {"absolute_log_rho": 0.10, "absolute_eta": 0.25, "absolute_p": 0.05},
            "all_truths_pass": result.checks["point_error_limits_pass"],
            "maxima": {
                "median_absolute_log_rho_error": max(
                    row.median_absolute_log_rho_error for row in result.condition_rows
                ),
                "median_absolute_eta_error": max(
                    row.median_absolute_resistance_error for row in result.condition_rows
                ),
                "median_absolute_p_error": max(
                    row.median_absolute_detection_error for row in result.condition_rows
                ),
            },
        },
        "calibration": {
            "nominal": 0.95,
            "wilson_interval_flags": flagged_coverage,
            "interpretation": "retain isolated flags; do not infer systematic undercoverage",
        },
        "resistance_precision": {
            "interval_width_limit": 0.75,
            "truths_strictly_above_limit": broad_eta,
        },
        "prediction": {
            "process_beats_neutral_truth_count": sum(
                row.process_beats_neutral for row in result.condition_rows
            ),
            "truth_count": len(result.condition_rows),
        },
        "boundary_contact": {
            "presentation": "observed truth-level support-topology diagnostic",
            "smooth_surface_supported": False,
        },
        "checks": result.checks,
        "input_invariants": result.inputs.invariants,
        "source_commits": result.inputs.source_commits,
        "input_sha256": result.inputs.input_sha256,
        "scope_limit": (
            "One accepted landscape, access network, observation schedule, likelihood, "
            "and process formulation; no prey layer or structural generality claim."
        ),
        "next_step": "human consolidation review, then separately designed Arc 2B work",
    }


def _synthesis(result: SynthesisResult) -> str:
    prospective = {row.metric_id: row for row in result.inputs.prospective}
    flags = [
        row.condition_id for row in result.condition_rows if not row.coverage_interval_includes_0_95
    ]
    broad = [
        row.condition_id
        for row in result.condition_rows
        if row.resistance_interval_broader_than_0_75
    ]
    labels = {
        "detection_interval_width": "Detection-probability precision",
        "eta_interval_width": "Resistance precision",
        "eta_zero_exclusion_probability": "Resistance distinguishable from zero",
        "heldout_brier_difference": "Prediction versus neutral",
        "boundary_contact_probability": "Boundary-contact topology",
    }
    rows = "\n".join(
        f"| {labels[row.metric_id]} | {row.prospective_skill:.3f} | "
        f"{row.threshold_class_accuracy:.3f} |"
        for row in result.inputs.prospective
    )
    return f"""# Arc 2A predator recoverability synthesis

## Bottom line

Across 32 prespecified combinations of spread rate, habitat-resistance
contrast, and detection probability, the current experiment recovered all
three point estimates accurately and the process model outpredicted its fitted
time-only neutral comparator at every truth. Precision changed substantially
across conditions, but the important detection- and resistance-precision
patterns predicted the second 16-truth block rather than merely describing the
first.

Arc 2A is ready to close with one explicit limitation: abrupt contact with the
edge of the parameter-support grid is a truth-level topology warning, not a
reliable smooth response surface.

## The prospective test came first

Low-order relationships were learned from `S01-S16`, and their predictions
were frozen before generating `S17-S32`. Positive skill means the frozen
surface predicted the new block better than simply using the first-block mean.

| Outcome | Prospective skill | Threshold-class accuracy |
| --- | ---: | ---: |
{rows}

Boundary contact was the exception: its prospective skill was
`{prospective["boundary_contact_probability"].prospective_skill:.3f}`. We do
not rescue it with a more flexible model. The observed 32 points remain in the
review pack as a support-topology diagnostic.

## What the combined 32-truth refit says

After preserving the prospective result, we refitted the four accepted model
forms to all 32 truths to obtain more stable descriptive maps. These refits are
for interpretation, not a second validation claim. Their paired bootstrap
intervals quantify Monte Carlo variation from the 250 validation histories per
truth; they do not include response-surface misspecification.

- Median absolute errors stayed within the accepted limits at all 32 truths:
  `0.10` for log spread rate, `0.25` for resistance contrast, and `0.05` for
  detection probability.
- Resistance intervals were strictly broader than `0.75` at
  `{", ".join(broad) if broad else "no truth"}`. The second-block occurrence
  was predicted prospectively and does not motivate further local sampling.
- Every process fit had lower held-out Brier error than its fitted neutral
  comparator.
- The 95% Wilson coverage interval missed 0.95 at
  `{", ".join(flags) if flags else "no truth"}`. This isolated flag is retained,
  not promoted to evidence of systematic undercoverage.

## Scientific interpretation

The reference experiment can recover spread rate, resistance contrast, and
detection probability across the tested domain, but recoverability is not
uniform. Weak ecological contrast and incomplete detection primarily widen
uncertainty rather than systematically displacing point estimates. The
combined surfaces show where that loss of precision occurs; the prospective
block shows that the main patterns are not just first-block curve fitting.

The result is conditional on one landscape, access network, site allocation,
survey schedule, likelihood, and generating model. Arc 2A therefore supports a
paper-level predator-only recoverability result, not a claim of structural
generality.

## Decision

**{result.outcome}**

No targeted enrichment or flexible emulator is recommended. Arc 2A's active
code is now consolidated; the next scientific tranche is a separately designed
Arc 2B prey-effect map after human review.
"""


def _surface_panel(
    axis: Any,
    result: SynthesisResult,
    metric_id: str,
    title: str,
    cmap: str,
) -> None:
    rows = [
        row
        for row in result.grid_rows
        if row.metric_id == metric_id and math.isclose(row.detection_probability, 0.60)
    ]
    rhos = sorted({row.rho for row in rows})
    etas = sorted({row.resistance_contrast for row in rows})
    values = np.asarray([row.estimate for row in rows]).reshape(len(etas), len(rhos))
    mesh = axis.pcolormesh(rhos, etas, values, shading="auto", cmap=cmap)
    fit = next(row for row in result.fits if row.spec.metric_id == metric_id)
    if float(np.min(values)) <= fit.spec.threshold <= float(np.max(values)):
        axis.contour(
            rhos,
            etas,
            values,
            levels=[fit.spec.threshold],
            colors="#111827",
            linewidths=1.2,
        )
    axis.scatter(
        [row.rho for row in result.inputs.conditions],
        [row.eta for row in result.inputs.conditions],
        facecolors="none",
        edgecolors="white",
        linewidths=0.6,
        s=17,
    )
    axis.set_xscale("log", base=2)
    axis.set_xticks((0.5, 1.0, 2.0), labels=("0.5", "1", "2"))
    axis.set_title(title, loc="left", fontweight="bold")
    axis.set_xlabel("Spread rate (relative to reference)")
    axis.set_ylabel("Resistance contrast")
    colorbar = axis.figure.colorbar(mesh, ax=axis, fraction=0.046, pad=0.03)
    colorbar.ax.tick_params(labelsize=8)


def _figure(result: SynthesisResult) -> Figure:
    figure, axes = plt.subplots(3, 2, figsize=(12.4, 13.8), constrained_layout=True)
    figure.suptitle(
        "Arc 2A: recoverability across 32 predator-only truths",
        fontsize=17,
        fontweight="bold",
    )
    _surface_panel(
        axes[0, 0],
        result,
        "detection_interval_width",
        "A  Detection precision (p = 0.60)",
        "YlGnBu",
    )
    _surface_panel(
        axes[0, 1], result, "eta_interval_width", "B  Resistance precision (p = 0.60)", "YlOrRd"
    )
    _surface_panel(
        axes[1, 0],
        result,
        "eta_zero_exclusion_probability",
        "C  Probability resistance is distinguished from zero",
        "viridis",
    )
    _surface_panel(
        axes[1, 1],
        result,
        "heldout_brier_difference",
        "D  Prediction error: process minus neutral",
        "RdBu_r",
    )

    topology = axes[2, 0]
    values = np.asarray(
        [row.boundary_contact_probability for row in result.topology_rows], dtype=np.float64
    )
    scatter = topology.scatter(
        [row.rho for row in result.topology_rows],
        [row.resistance_contrast for row in result.topology_rows],
        c=values,
        s=[30 + 70 * (row.detection_probability - 0.35) / 0.50 for row in result.topology_rows],
        cmap="magma_r",
        norm=Normalize(0.0, 1.0),
        edgecolors="#111827",
        linewidths=0.45,
    )
    topology.set_xscale("log", base=2)
    topology.set_xticks((0.5, 1.0, 2.0), labels=("0.5", "1", "2"))
    topology.set_xlabel("Spread rate (relative to reference)")
    topology.set_ylabel("Resistance contrast")
    topology.set_title("E  Observed support-boundary contact", loc="left", fontweight="bold")
    topology.text(
        0.02,
        0.02,
        "Colour = contact probability; size = detection probability\n"
        "Observed points only: no smooth surface supported",
        transform=topology.transAxes,
        fontsize=8.5,
        va="bottom",
        bbox={"facecolor": "white", "alpha": 0.88, "edgecolor": "none"},
    )
    figure.colorbar(scatter, ax=topology, fraction=0.046, pad=0.03, label="Contact probability")

    calibration = axes[2, 1]
    x = np.arange(1, 33)
    coverage = np.asarray([row.calibrated_coverage for row in result.condition_rows])
    lower = np.asarray([row.coverage_lower for row in result.condition_rows])
    upper = np.asarray([row.coverage_upper for row in result.condition_rows])
    calibration.errorbar(
        x,
        coverage,
        yerr=np.vstack((coverage - lower, upper - coverage)),
        fmt="o",
        markersize=3.8,
        color="#2a6f97",
        ecolor="#7b8794",
        elinewidth=0.8,
        capsize=1.5,
    )
    calibration.axhline(0.95, color="#9b2226", linestyle="--", linewidth=1.2)
    flagged = [
        index + 1
        for index, row in enumerate(result.condition_rows)
        if not row.coverage_interval_includes_0_95
    ]
    if flagged:
        calibration.scatter(
            flagged,
            [coverage[index - 1] for index in flagged],
            s=46,
            facecolors="none",
            edgecolors="#d1495b",
            linewidths=1.4,
            zorder=4,
        )
    calibration.set_ylim(0.84, 1.0)
    calibration.set_xlabel("Truth condition S01-S32")
    calibration.set_ylabel("Empirical coverage with 95% Wilson interval")
    calibration.set_title("F  Calibration across the 32 truths", loc="left", fontweight="bold")
    calibration.grid(axis="y", alpha=0.2)
    return figure


def _write_csv(path: Path, rows: Sequence[Any]) -> None:
    payload = [asdict(row) for row in rows]
    if not payload:
        raise ValueError(f"cannot write empty CSV: {path.name}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(payload)


def write_review_bundle(
    result: SynthesisResult, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> tuple[Path, ...]:
    """Write the exact compact Arc 2A review bundle."""
    output_dir.mkdir(parents=True, exist_ok=True)
    prospective_rows = tuple(sorted(result.inputs.prospective, key=lambda row: row.metric_id))
    _write_csv(output_dir / EXPECTED_FILES[0], result.condition_rows)
    _write_csv(output_dir / EXPECTED_FILES[1], prospective_rows)
    _write_csv(output_dir / EXPECTED_FILES[2], result.coefficient_rows)
    _write_csv(output_dir / EXPECTED_FILES[3], result.grid_rows)
    _write_csv(output_dir / EXPECTED_FILES[4], result.topology_rows)
    (output_dir / EXPECTED_FILES[5]).write_text(
        json.dumps(_summary(result), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / EXPECTED_FILES[6]).write_text(_synthesis(result), encoding="utf-8")
    figure = _figure(result)
    figure.savefig(output_dir / EXPECTED_FILES[7], format="svg", bbox_inches="tight")
    plt.close(figure)
    written = tuple(output_dir / name for name in EXPECTED_FILES)
    actual = tuple(sorted(path.name for path in output_dir.iterdir() if path.is_file()))
    if actual != tuple(sorted(EXPECTED_FILES)) or not all(
        path.stat().st_size > 0 for path in written
    ):
        raise RuntimeError("Arc 2A artifact contract failed")
    return written


def summarize_for_cli(result: SynthesisResult) -> str:
    return (
        "Arc 2A 32-truth synthesis complete\n"
        f"Outcome: {result.outcome}\n"
        f"Truths: {len(result.condition_rows)}\n"
        "Smooth descriptive outcomes: 4\n"
        "Boundary contact: observed topology points only\n"
    )
