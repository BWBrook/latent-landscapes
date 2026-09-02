"""Frozen prospective scoring and final synthesis for Arc 2B."""

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
from matplotlib.lines import Line2D
from numpy.typing import NDArray

from latent_landscapes.arc2b_design import truths_for_block

mpl.use("Agg")
mpl.rcParams["svg.hashsalt"] = "latent-landscapes-arc2b-synthesis"
import matplotlib.pyplot as plt  # noqa: E402

DEFAULT_OUTPUT_DIR = Path("artifacts/arc2b_synthesis")
DEFAULT_FROZEN_PREDICTIONS = Path(
    "docs/goals/044-arc2b-prey-effect-recoverability-map/prospective_predictions.csv"
)
EXPECTED_FILES = (
    "condition_outcomes.csv",
    "prospective_score_summary.csv",
    "surface_coefficients.csv",
    "surface_grid.csv",
    "control_summary.csv",
    "event_information_summary.csv",
    "synthesis_summary.json",
    "synthesis.md",
    "arc2b_recovery_map.svg",
)
DEFAULT_BOOTSTRAPS = 1_000
BOOTSTRAP_SEED = 20260902
PRODUCTION_VALIDATION_COUNT = 250
ModelType = Literal["additive", "two_way_interactions", "invariant"]
TransformType = Literal["identity", "jeffreys_logit"]
Aggregation = Literal["mean", "median"]
FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


@dataclass(frozen=True, slots=True)
class MetricSpec:
    metric_id: str
    validation_field: str
    summary_field: str
    aggregation: Aggregation
    transform: TransformType


METRICS = (
    MetricSpec(
        "median_absolute_log_effect_error",
        "absolute_log_effect_error",
        "median_absolute_log_effect_error",
        "median",
        "identity",
    ),
    MetricSpec(
        "median_log_support_width",
        "log_support_width",
        "median_log_support_width",
        "median",
        "identity",
    ),
    MetricSpec(
        "mean_heldout_known_background_no_effect_advantage_per_record",
        "heldout_known_background_no_effect_advantage_per_record",
        "mean_heldout_known_background_no_effect_advantage_per_record",
        "mean",
        "identity",
    ),
    MetricSpec(
        "connected_interior_frequency",
        "connected_interior",
        "connected_interior_frequency",
        "mean",
        "jeffreys_logit",
    ),
    MetricSpec(
        "no_effect_exclusion_probability",
        "no_effect_excluded",
        "no_effect_exclusion_probability",
        "mean",
        "jeffreys_logit",
    ),
)
METRIC_BY_ID = {row.metric_id: row for row in METRICS}


@dataclass(frozen=True, slots=True)
class ConditionOutcome:
    condition_id: str
    design_role: str
    effect_multiplier: float
    background_risk: float
    prey_detection_probability: float
    validation_count: int
    coverage: float
    coverage_lower: float
    coverage_upper: float
    connected_interior_frequency: float
    no_effect_exclusion_probability: float
    median_absolute_log_effect_error: float
    median_log_support_width: float
    mean_heldout_known_background_no_effect_advantage_per_record: float
    heldout_known_background_no_effect_advantage_lower: float
    heldout_known_background_no_effect_advantage_upper: float
    mean_heldout_fitted_neutral_advantage_per_record: float
    heldout_fitted_neutral_advantage_lower: float
    heldout_fitted_neutral_advantage_upper: float
    mean_true_extirpations_by_day60: float
    mean_pre_arrival_true_extirpations: float
    mean_post_arrival_true_extirpations: float
    mean_true_extirpation_censoring: float
    mean_post_arrival_at_risk_exposure: float
    mean_prey_observation_support: float
    recovery_classification: str
    failed_gates: str


@dataclass(frozen=True, slots=True)
class ValidationArrays:
    condition_id: str
    dataset_index: IntArray
    truth_included: BoolArray
    connected: BoolArray
    connected_interior: BoolArray
    no_effect_excluded: BoolArray
    absolute_log_effect_error: FloatArray
    log_support_width: FloatArray
    heldout_known_background_no_effect_advantage_per_record: FloatArray
    heldout_fitted_neutral_advantage_per_record: FloatArray


@dataclass(frozen=True, slots=True)
class CampaignBlock:
    conditions: tuple[ConditionOutcome, ...]
    validation: tuple[ValidationArrays, ...]
    bundle_sha256: str
    source_commit: str
    bank_checksum: str
    master_seed: int
    validation_seeds_sha256: str
    frozen_predictions_sha256: str | None
    invariants: dict[str, bool]


@dataclass(frozen=True, slots=True)
class CandidateFit:
    model_type: ModelType
    terms: tuple[str, ...]
    coefficients: FloatArray
    loto_predictions: FloatArray
    loto_rmse: float


@dataclass(frozen=True, slots=True)
class FrozenSurface:
    metric_id: str
    response_scale: TransformType
    model_type: ModelType
    terms: tuple[str, ...]
    coefficients: FloatArray
    pilot_mean: float
    loto_rmse: float
    additive_loto_rmse: float
    interaction_loto_rmse: float
    invariant_value: float | None


@dataclass(frozen=True, slots=True)
class FrozenPrediction:
    source_bundle_sha256: str
    source_campaign_commit: str
    condition_id: str
    effect_multiplier: float
    background_risk: float
    prey_detection_probability: float
    metric_id: str
    response_scale: TransformType
    model_type: ModelType
    terms_json: str
    coefficients_json: str
    frozen_prediction_fitting_scale: float
    frozen_prediction_observed_scale: float
    frozen_pilot_mean_fitting_scale: float
    frozen_loto_rmse: float
    additive_loto_rmse: float
    interaction_loto_rmse: float
    invariant: bool


@dataclass(frozen=True, slots=True)
class ProspectiveScore:
    metric_id: str
    response_scale: str
    model_type: str
    condition_count: int
    prospective_rmse: float
    prospective_rmse_lower: float
    prospective_rmse_upper: float
    frozen_mean_rmse: float
    prospective_skill: float | None
    prospective_skill_lower: float | None
    prospective_skill_upper: float | None
    within_frozen_loto_rmse_fraction: float
    decision: str


@dataclass(frozen=True, slots=True)
class CombinedFit:
    metric_id: str
    response_scale: TransformType
    model_type: ModelType
    terms: tuple[str, ...]
    coefficients: FloatArray
    bootstrap_coefficients: FloatArray


@dataclass(frozen=True, slots=True)
class CoefficientRow:
    metric_id: str
    response_scale: str
    model_type: str
    term: str
    estimate: float
    paired_bootstrap_lower: float
    paired_bootstrap_upper: float


@dataclass(frozen=True, slots=True)
class GridRow:
    metric_id: str
    response_scale: str
    model_type: str
    prey_detection_probability: float
    effect_multiplier: float
    background_risk: float
    estimate: float
    paired_bootstrap_lower: float
    paired_bootstrap_upper: float


@dataclass(frozen=True, slots=True)
class ControlDecision:
    condition_id: str
    valid: bool
    decision: str
    failed_gates: str
    coverage: float
    connected_frequency: float
    no_effect_exclusion_probability: float
    median_absolute_log_effect_error: float
    median_log_support_width: float
    mean_heldout_known_background_no_effect_advantage_per_record: float
    heldout_known_background_no_effect_advantage_lower: float
    mean_heldout_fitted_neutral_advantage_per_record: float
    heldout_fitted_neutral_advantage_lower: float


@dataclass(frozen=True, slots=True)
class EventInformationRow:
    diagnostic: str
    outcome_metric: str
    pearson_correlation: float


@dataclass(frozen=True, slots=True)
class SynthesisResult:
    conditions: tuple[ConditionOutcome, ...]
    validation: tuple[ValidationArrays, ...]
    prospective_scores: tuple[ProspectiveScore, ...]
    fits: tuple[CombinedFit, ...]
    coefficient_rows: tuple[CoefficientRow, ...]
    grid_rows: tuple[GridRow, ...]
    controls: tuple[ControlDecision, ...]
    event_information: tuple[EventInformationRow, ...]
    source_commits: dict[str, str]
    source_sha256: dict[str, str]
    checks: dict[str, bool]
    outcome: str
    bootstrap_count: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _bundle_sha256(input_dir: Path) -> str:
    files = (
        "validation_condition_summaries.csv",
        "validation_metrics.csv",
        "summary.json",
        "seed_provenance.json",
    )
    digest = hashlib.sha256()
    for name in files:
        path = input_dir / name
        if not path.is_file():
            raise ValueError(f"campaign bundle is incomplete: {input_dir}")
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256(path)))
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
    if value in {"True", "true", "1"}:
        return True
    if value in {"False", "false", "0"}:
        return False
    raise ValueError(f"expected boolean text, received {value!r}")


def _parse_model_type(value: str) -> ModelType:
    if value not in {"additive", "two_way_interactions", "invariant"}:
        raise ValueError(f"unknown model type: {value}")
    return cast(ModelType, value)


def _parse_transform(value: str) -> TransformType:
    if value not in {"identity", "jeffreys_logit"}:
        raise ValueError(f"unknown response scale: {value}")
    return cast(TransformType, value)


def _classification(row: dict[str, str]) -> tuple[str, str]:
    count = int(row["validation_count"])
    passes = {
        "coverage": float(row["coverage_lower"]) <= 0.95 <= float(row["coverage_upper"]),
        "connected_interior": float(row["connected_interior_frequency"]) >= 238 / 250,
        "excludes_no_effect": float(row["no_effect_exclusion_probability"]) >= 238 / 250,
        "point_error": float(row["median_absolute_log_effect_error"]) <= 0.20,
        "support_width": float(row["median_log_support_width"]) <= 0.80,
        "predictive_advantage": (
            float(row["heldout_known_background_no_effect_advantage_lower"]) > 0.0
        ),
        "production_count": count == PRODUCTION_VALIDATION_COUNT,
    }
    failed = tuple(name for name, passed in passes.items() if not passed)
    if all(passes.values()):
        return "fully_recovered", ""
    if passes["excludes_no_effect"] and passes["predictive_advantage"]:
        return "detected_but_not_fully_recovered", ";".join(failed)
    return "not_reliably_detected", ";".join(failed)


def _condition_from_row(row: dict[str, str]) -> ConditionOutcome:
    classification, failed = _classification(row)
    if row["design_role"] in {"reference_control", "neutral_control"}:
        classification, failed = "control", ""
    return ConditionOutcome(
        row["condition_id"],
        row["design_role"],
        float(row["truth_effect_multiplier"]),
        float(row["truth_background_risk"]),
        float(row["truth_prey_detection_probability"]),
        int(row["validation_count"]),
        float(row["coverage"]),
        float(row["coverage_lower"]),
        float(row["coverage_upper"]),
        float(row["connected_interior_frequency"]),
        float(row["no_effect_exclusion_probability"]),
        float(row["median_absolute_log_effect_error"]),
        float(row["median_log_support_width"]),
        float(row["mean_heldout_known_background_no_effect_advantage_per_record"]),
        float(row["heldout_known_background_no_effect_advantage_lower"]),
        float(row["heldout_known_background_no_effect_advantage_upper"]),
        float(row["mean_heldout_fitted_neutral_advantage_per_record"]),
        float(row["heldout_fitted_neutral_advantage_lower"]),
        float(row["heldout_fitted_neutral_advantage_upper"]),
        float(row["mean_true_extirpations_by_day60"]),
        float(row["mean_pre_arrival_true_extirpations"]),
        float(row["mean_post_arrival_true_extirpations"]),
        float(row["mean_true_extirpation_censoring"]),
        float(row["mean_post_arrival_at_risk_exposure"]),
        float(row["mean_prey_observation_support"]),
        classification,
        failed,
    )


def _validation_arrays(condition_id: str, rows: Sequence[dict[str, str]]) -> ValidationArrays:
    selected = sorted(
        (row for row in rows if row["condition_id"] == condition_id),
        key=lambda row: int(row["dataset_index"]),
    )
    components = np.asarray(
        [int(row["support_component_count"]) for row in selected], dtype=np.int64
    )
    boundary = np.asarray(
        [_as_bool(row["support_boundary_contact"]) for row in selected], dtype=np.bool_
    )
    return ValidationArrays(
        condition_id,
        np.asarray([int(row["dataset_index"]) for row in selected], dtype=np.int64),
        np.asarray([_as_bool(row["truth_included"]) for row in selected], dtype=np.bool_),
        components == 1,
        (components == 1) & ~boundary,
        np.asarray([_as_bool(row["no_effect_excluded"]) for row in selected], dtype=np.bool_),
        np.asarray([float(row["absolute_log_effect_error"]) for row in selected]),
        np.asarray([float(row["log_support_width"]) for row in selected]),
        np.asarray(
            [
                float(row["heldout_known_background_no_effect_advantage_per_record"])
                for row in selected
            ]
        ),
        np.asarray([float(row["heldout_fitted_neutral_advantage_per_record"]) for row in selected]),
    )


def load_campaign_block(input_dir: Path) -> CampaignBlock:
    """Load and independently reconcile one compact campaign bundle."""
    bundle_digest = _bundle_sha256(input_dir)
    summary = _read_json(input_dir / "summary.json")
    raw_invariants = summary.get("invariants")
    if not isinstance(raw_invariants, dict) or not raw_invariants:
        raise ValueError(f"campaign invariants missing: {input_dir}")
    invariants = {str(key): bool(value) for key, value in raw_invariants.items()}
    if not all(invariants.values()):
        raise ValueError(f"campaign invariants failed: {input_dir}")
    conditions = tuple(
        sorted(
            (
                _condition_from_row(row)
                for row in _read_csv(input_dir / "validation_condition_summaries.csv")
            ),
            key=lambda row: row.condition_id,
        )
    )
    metric_rows = _read_csv(input_dir / "validation_metrics.csv")
    validation = tuple(_validation_arrays(row.condition_id, metric_rows) for row in conditions)
    by_condition = {row.condition_id: row for row in validation}
    for condition in conditions:
        arrays = by_condition[condition.condition_id]
        expected = np.arange(condition.validation_count, dtype=np.int64)
        if not np.array_equal(arrays.dataset_index, expected):
            raise ValueError(f"validation indices are incomplete for {condition.condition_id}")
        connected_values = (
            arrays.connected
            if condition.design_role == "neutral_control"
            else arrays.connected_interior
        )
        checks = (
            math.isclose(float(np.mean(arrays.truth_included)), condition.coverage, abs_tol=1e-12),
            math.isclose(
                float(np.mean(connected_values)),
                condition.connected_interior_frequency,
                abs_tol=1e-12,
            ),
            math.isclose(
                float(np.mean(arrays.no_effect_excluded)),
                condition.no_effect_exclusion_probability,
                abs_tol=1e-12,
            ),
            math.isclose(
                float(np.median(arrays.absolute_log_effect_error)),
                condition.median_absolute_log_effect_error,
                abs_tol=1e-12,
            ),
            math.isclose(
                float(np.median(arrays.log_support_width)),
                condition.median_log_support_width,
                abs_tol=1e-12,
            ),
            math.isclose(
                float(np.mean(arrays.heldout_known_background_no_effect_advantage_per_record)),
                condition.mean_heldout_known_background_no_effect_advantage_per_record,
                abs_tol=1e-12,
            ),
            math.isclose(
                float(np.mean(arrays.heldout_fitted_neutral_advantage_per_record)),
                condition.mean_heldout_fitted_neutral_advantage_per_record,
                abs_tol=1e-12,
            ),
        )
        if not all(checks):
            raise ValueError(f"condition summary does not reconcile for {condition.condition_id}")
    provenance = _read_json(input_dir / "seed_provenance.json")
    validation_seeds = provenance.get("validation_seeds")
    frozen_predictions_digest = provenance.get("frozen_predictions_sha256")
    return CampaignBlock(
        conditions,
        validation,
        bundle_digest,
        str(provenance.get("source_commit", "unknown")),
        str(provenance.get("bank_checksum", "unknown")),
        int(provenance.get("master_seed", -1)),
        _json_sha256(validation_seeds),
        None if frozen_predictions_digest is None else str(frozen_predictions_digest),
        invariants,
    )


def scaled_predictors(conditions: Sequence[ConditionOutcome]) -> FloatArray:
    return np.asarray(
        [
            (
                2.0 * (math.log(row.effect_multiplier) - math.log(1.5)) / math.log(4.0) - 1.0,
                2.0 * (row.background_risk - 0.05) / 0.15 - 1.0,
                2.0 * (row.prey_detection_probability - 0.35) / 0.50 - 1.0,
            )
            for row in conditions
        ],
        dtype=np.float64,
    )


def _coordinates_predictors(
    coordinates: Sequence[tuple[float, float, float]],
) -> FloatArray:
    return np.asarray(
        [
            (
                2.0 * (math.log(effect) - math.log(1.5)) / math.log(4.0) - 1.0,
                2.0 * (background - 0.05) / 0.15 - 1.0,
                2.0 * (detection - 0.35) / 0.50 - 1.0,
            )
            for effect, background, detection in coordinates
        ],
        dtype=np.float64,
    )


def _terms(model_type: ModelType) -> tuple[str, ...]:
    base = ("intercept", "xE", "xB", "xP")
    if model_type == "additive":
        return base
    if model_type == "two_way_interactions":
        return (*base, "xE:xB", "xE:xP", "xB:xP")
    return ("invariant",)


def design_matrix(predictors: FloatArray, model_type: ModelType) -> FloatArray:
    if model_type == "invariant":
        return np.ones((len(predictors), 1), dtype=np.float64)
    base = np.column_stack((np.ones(len(predictors)), predictors))
    if model_type == "additive":
        return np.asarray(base, dtype=np.float64)
    return np.asarray(
        np.column_stack(
            (
                base,
                predictors[:, 0] * predictors[:, 1],
                predictors[:, 0] * predictors[:, 2],
                predictors[:, 1] * predictors[:, 2],
            )
        ),
        dtype=np.float64,
    )


def transform_response(values: FloatArray, transform: TransformType, count: int) -> FloatArray:
    if transform == "identity":
        return np.asarray(values, dtype=np.float64)
    successes = np.rint(values * count)
    return np.log((successes + 0.5) / (count - successes + 0.5))


def inverse_response(values: FloatArray, transform: TransformType) -> FloatArray:
    if transform == "identity":
        return np.asarray(values, dtype=np.float64)
    return 1.0 / (1.0 + np.exp(-values))


def _fit_coefficients(matrix: FloatArray, response: FloatArray) -> FloatArray:
    return np.asarray(np.linalg.lstsq(matrix, response, rcond=None)[0], dtype=np.float64)


def _candidate_fit(
    predictors: FloatArray, response: FloatArray, model_type: ModelType
) -> CandidateFit:
    matrix = design_matrix(predictors, model_type)
    coefficients = _fit_coefficients(matrix, response)
    predictions = np.empty(len(response), dtype=np.float64)
    for index in range(len(response)):
        keep = np.arange(len(response)) != index
        fold_coefficients = _fit_coefficients(matrix[keep], response[keep])
        predictions[index] = float(matrix[index] @ fold_coefficients)
    return CandidateFit(
        model_type,
        _terms(model_type),
        coefficients,
        predictions,
        float(np.sqrt(np.mean((response - predictions) ** 2))),
    )


def observed_metric(conditions: Sequence[ConditionOutcome], spec: MetricSpec) -> FloatArray:
    return np.asarray([float(getattr(row, spec.summary_field)) for row in conditions])


def _coordinates_match_design(
    conditions: Sequence[ConditionOutcome], block: Literal["pilot", "prospective"]
) -> bool:
    expected = {row.condition_id: row for row in truths_for_block(block)}
    if {row.condition_id for row in conditions} != set(expected):
        return False
    return all(
        all(
            math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12)
            for left, right in (
                (row.effect_multiplier, expected[row.condition_id].effect_multiplier),
                (row.background_risk, expected[row.condition_id].background_risk),
                (
                    row.prey_detection_probability,
                    expected[row.condition_id].prey_detection_probability,
                ),
            )
        )
        for row in conditions
    )


def select_surface(conditions: Sequence[ConditionOutcome], spec: MetricSpec) -> FrozenSurface:
    """Apply the prespecified additive-versus-interaction selection rule."""
    observed = observed_metric(conditions, spec)
    response = transform_response(observed, spec.transform, conditions[0].validation_count)
    pilot_mean = float(np.mean(response))
    if float(np.ptp(response)) <= 1e-12:
        return FrozenSurface(
            spec.metric_id,
            spec.transform,
            "invariant",
            ("invariant",),
            np.asarray([pilot_mean]),
            pilot_mean,
            0.0,
            0.0,
            0.0,
            pilot_mean,
        )
    predictors = scaled_predictors(conditions)
    additive = _candidate_fit(predictors, response, "additive")
    interaction = _candidate_fit(predictors, response, "two_way_interactions")
    selected = interaction if interaction.loto_rmse <= 0.90 * additive.loto_rmse else additive
    return FrozenSurface(
        spec.metric_id,
        spec.transform,
        selected.model_type,
        selected.terms,
        selected.coefficients,
        pilot_mean,
        selected.loto_rmse,
        additive.loto_rmse,
        interaction.loto_rmse,
        None,
    )


def freeze_predictions(pilot_dir: Path) -> tuple[FrozenPrediction, ...]:
    """Fit pilot surfaces and freeze predictions for S17-S32."""
    pilot = load_campaign_block(pilot_dir)
    expected_ids = {f"S{index:02d}" for index in range(1, 17)} | {"R00", "N00"}
    if {row.condition_id for row in pilot.conditions} != expected_ids:
        raise ValueError("pilot bundle must contain S01-S16, R00, and N00")
    continuous = tuple(row for row in pilot.conditions if row.condition_id.startswith("S"))
    if not _coordinates_match_design(continuous, "pilot"):
        raise ValueError("pilot coordinates do not match the frozen Sobol design")
    if any(row.validation_count != PRODUCTION_VALIDATION_COUNT for row in continuous):
        raise ValueError("pilot freeze requires 250 validation histories per truth")
    prospective_truths = truths_for_block("prospective")
    coordinates = tuple(
        (row.effect_multiplier, row.background_risk, row.prey_detection_probability)
        for row in prospective_truths
    )
    predictors = _coordinates_predictors(coordinates)
    rows: list[FrozenPrediction] = []
    for spec in METRICS:
        surface = select_surface(continuous, spec)
        fitting_predictions = design_matrix(predictors, surface.model_type) @ surface.coefficients
        observed_predictions = inverse_response(fitting_predictions, surface.response_scale)
        for truth, fitting, observed in zip(
            prospective_truths, fitting_predictions, observed_predictions, strict=True
        ):
            rows.append(
                FrozenPrediction(
                    pilot.bundle_sha256,
                    pilot.source_commit,
                    truth.condition_id,
                    truth.effect_multiplier,
                    truth.background_risk,
                    truth.prey_detection_probability,
                    spec.metric_id,
                    surface.response_scale,
                    surface.model_type,
                    json.dumps(surface.terms, separators=(",", ":")),
                    json.dumps(surface.coefficients.tolist(), separators=(",", ":")),
                    float(fitting),
                    float(observed),
                    surface.pilot_mean,
                    surface.loto_rmse,
                    surface.additive_loto_rmse,
                    surface.interaction_loto_rmse,
                    surface.model_type == "invariant",
                )
            )
    frozen = tuple(rows)
    validate_frozen_predictions(frozen)
    return frozen


def validate_frozen_predictions(rows: Sequence[FrozenPrediction]) -> None:
    expected_ids = {f"S{index:02d}" for index in range(17, 33)}
    if len(rows) != len(expected_ids) * len(METRICS):
        raise ValueError("frozen prediction row count is incorrect")
    if {row.condition_id for row in rows} != expected_ids:
        raise ValueError("frozen prediction IDs are incorrect")
    if {row.metric_id for row in rows} != set(METRIC_BY_ID):
        raise ValueError("frozen prediction metrics are incomplete")
    if len({row.source_bundle_sha256 for row in rows}) != 1:
        raise ValueError("frozen predictions do not share one source bundle")
    if len({row.source_campaign_commit for row in rows}) != 1:
        raise ValueError("frozen predictions do not share one campaign commit")
    truths = {row.condition_id: row for row in truths_for_block("prospective")}
    for metric_id, spec in METRIC_BY_ID.items():
        selected = tuple(row for row in rows if row.metric_id == metric_id)
        constants = {
            (
                row.response_scale,
                row.model_type,
                row.terms_json,
                row.coefficients_json,
                row.frozen_pilot_mean_fitting_scale,
                row.frozen_loto_rmse,
                row.additive_loto_rmse,
                row.interaction_loto_rmse,
                row.invariant,
            )
            for row in selected
        }
        if (
            len(constants) != 1
            or selected[0].response_scale != spec.transform
            or selected[0].invariant != (selected[0].model_type == "invariant")
        ):
            raise ValueError(f"frozen surface varies within metric {metric_id}")
        terms = tuple(json.loads(selected[0].terms_json))
        coefficients = np.asarray(json.loads(selected[0].coefficients_json), dtype=np.float64)
        if terms != _terms(selected[0].model_type) or len(terms) != len(coefficients):
            raise ValueError(f"frozen coefficient contract failed for {metric_id}")
        for row in selected:
            truth = truths[row.condition_id]
            if not all(
                math.isclose(left, right, abs_tol=1e-12)
                for left, right in (
                    (row.effect_multiplier, truth.effect_multiplier),
                    (row.background_risk, truth.background_risk),
                    (row.prey_detection_probability, truth.prey_detection_probability),
                )
            ):
                raise ValueError(f"frozen coordinates changed for {row.condition_id}")
            predictor = _coordinates_predictors(
                ((row.effect_multiplier, row.background_risk, row.prey_detection_probability),)
            )
            expected = float(design_matrix(predictor, row.model_type)[0] @ coefficients)
            if not math.isclose(
                expected, row.frozen_prediction_fitting_scale, rel_tol=1e-12, abs_tol=1e-12
            ):
                raise ValueError(f"frozen prediction does not reconcile for {row.condition_id}")
            expected_observed = float(
                inverse_response(np.asarray([expected]), row.response_scale)[0]
            )
            if not math.isclose(
                expected_observed,
                row.frozen_prediction_observed_scale,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise ValueError(
                    f"frozen observed-scale prediction does not reconcile for {row.condition_id}"
                )


def write_frozen_predictions(rows: Sequence[FrozenPrediction], path: Path) -> Path:
    validate_frozen_predictions(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(path, rows)
    loaded = load_frozen_predictions(path)
    if tuple(rows) != loaded:
        raise RuntimeError("frozen prediction table did not round-trip")
    return path


def load_frozen_predictions(path: Path) -> tuple[FrozenPrediction, ...]:
    rows = tuple(
        FrozenPrediction(
            row["source_bundle_sha256"],
            row["source_campaign_commit"],
            row["condition_id"],
            float(row["effect_multiplier"]),
            float(row["background_risk"]),
            float(row["prey_detection_probability"]),
            row["metric_id"],
            _parse_transform(row["response_scale"]),
            _parse_model_type(row["model_type"]),
            row["terms_json"],
            row["coefficients_json"],
            float(row["frozen_prediction_fitting_scale"]),
            float(row["frozen_prediction_observed_scale"]),
            float(row["frozen_pilot_mean_fitting_scale"]),
            float(row["frozen_loto_rmse"]),
            float(row["additive_loto_rmse"]),
            float(row["interaction_loto_rmse"]),
            _as_bool(row["invariant"]),
        )
        for row in _read_csv(path)
    )
    validate_frozen_predictions(rows)
    return rows


def _aggregate(arrays: ValidationArrays, spec: MetricSpec, indices: IntArray) -> float:
    values = np.asarray(getattr(arrays, spec.validation_field))[indices]
    return float(np.mean(values) if spec.aggregation == "mean" else np.median(values))


def _quantile_interval(values: Sequence[float]) -> tuple[float, float]:
    finite = np.asarray([value for value in values if math.isfinite(value)], dtype=np.float64)
    if not len(finite):
        return math.nan, math.nan
    lower, upper = np.quantile(finite, (0.025, 0.975))
    return float(lower), float(upper)


def score_prospective(
    conditions: Sequence[ConditionOutcome],
    validation: Sequence[ValidationArrays],
    predictions: Sequence[FrozenPrediction],
    *,
    bootstrap_count: int = DEFAULT_BOOTSTRAPS,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[ProspectiveScore, ...]:
    """Score frozen predictions, with paired Monte Carlo bootstrap intervals."""
    validate_frozen_predictions(predictions)
    if bootstrap_count <= 0:
        raise ValueError("bootstrap count must be positive")
    condition_by_id = {row.condition_id: row for row in conditions}
    arrays_by_id = {row.condition_id: row for row in validation}
    ids = tuple(f"S{index:02d}" for index in range(17, 33))
    if set(condition_by_id) != set(ids) or set(arrays_by_id) != set(ids):
        raise ValueError("prospective evidence must contain exactly S17-S32")
    count = conditions[0].validation_count
    if any(row.validation_count != count for row in conditions):
        raise ValueError("prospective validation counts differ")
    rng = np.random.default_rng(seed)
    resamples = rng.integers(0, count, size=(bootstrap_count, count), dtype=np.int64)
    output: list[ProspectiveScore] = []
    for spec in METRICS:
        frozen = sorted(
            (row for row in predictions if row.metric_id == spec.metric_id),
            key=lambda row: row.condition_id,
        )
        observed_raw = np.asarray(
            [
                float(getattr(condition_by_id[row.condition_id], spec.summary_field))
                for row in frozen
            ]
        )
        observed = transform_response(observed_raw, spec.transform, count)
        predicted = np.asarray([row.frozen_prediction_fitting_scale for row in frozen])
        pilot_mean = float(frozen[0].frozen_pilot_mean_fitting_scale)
        sse = float(np.sum((observed - predicted) ** 2))
        mean_sse = float(np.sum((observed - pilot_mean) ** 2))
        rmse = math.sqrt(sse / len(frozen))
        mean_rmse = math.sqrt(mean_sse / len(frozen))
        invariant = frozen[0].model_type == "invariant" or mean_sse <= 1e-15
        skill = None if invariant else 1.0 - sse / mean_sse
        bootstrap_rmse: list[float] = []
        bootstrap_skill: list[float] = []
        for indices in resamples:
            raw = np.asarray(
                [_aggregate(arrays_by_id[row.condition_id], spec, indices) for row in frozen]
            )
            transformed = transform_response(raw, spec.transform, count)
            boot_sse = float(np.sum((transformed - predicted) ** 2))
            boot_mean_sse = float(np.sum((transformed - pilot_mean) ** 2))
            bootstrap_rmse.append(math.sqrt(boot_sse / len(frozen)))
            if not invariant and boot_mean_sse > 1e-15:
                bootstrap_skill.append(1.0 - boot_sse / boot_mean_sse)
        rmse_lower, rmse_upper = _quantile_interval(bootstrap_rmse)
        skill_lower, skill_upper = _quantile_interval(bootstrap_skill)
        output.append(
            ProspectiveScore(
                spec.metric_id,
                spec.transform,
                frozen[0].model_type,
                len(frozen),
                rmse,
                rmse_lower,
                rmse_upper,
                mean_rmse,
                skill,
                None if skill is None else skill_lower,
                None if skill is None else skill_upper,
                float(np.mean(np.abs(observed - predicted) <= float(frozen[0].frozen_loto_rmse))),
                "invariant" if skill is None else "supported" if skill > 0 else "surface_limited",
            )
        )
    return tuple(output)


def _control_decision(condition: ConditionOutcome, arrays: ValidationArrays) -> ControlDecision:
    coverage_ok = condition.coverage_lower <= 0.95 <= condition.coverage_upper
    if condition.condition_id == "R00":
        checks = {
            "production_count": condition.validation_count == PRODUCTION_VALIDATION_COUNT,
            "coverage": coverage_ok,
            "connected_and_interior": condition.connected_interior_frequency >= 238 / 250,
            "excludes_no_effect": condition.no_effect_exclusion_probability >= 238 / 250,
            "point_error": condition.median_absolute_log_effect_error <= 0.20,
            "predictive_advantage": (
                condition.heldout_known_background_no_effect_advantage_lower > 0.0
            ),
        }
        connected_frequency = condition.connected_interior_frequency
        label = "reference_control_valid"
    elif condition.condition_id == "N00":
        connected_frequency = float(np.mean(arrays.connected))
        checks = {
            "production_count": condition.validation_count == PRODUCTION_VALIDATION_COUNT,
            "coverage": coverage_ok,
            "connected": connected_frequency >= 238 / 250,
            "false_no_effect_exclusion": condition.no_effect_exclusion_probability <= 19 / 250,
            "no_demonstrated_predictive_advantage": (
                condition.heldout_known_background_no_effect_advantage_lower <= 0.0
            ),
        }
        label = "neutral_control_valid"
    else:
        raise ValueError(f"unknown control {condition.condition_id}")
    failed = tuple(key for key, passed in checks.items() if not passed)
    return ControlDecision(
        condition.condition_id,
        not failed,
        label if not failed else "control_failed",
        ";".join(failed),
        condition.coverage,
        connected_frequency,
        condition.no_effect_exclusion_probability,
        condition.median_absolute_log_effect_error,
        condition.median_log_support_width,
        condition.mean_heldout_known_background_no_effect_advantage_per_record,
        condition.heldout_known_background_no_effect_advantage_lower,
        condition.mean_heldout_fitted_neutral_advantage_per_record,
        condition.heldout_fitted_neutral_advantage_lower,
    )


def classify_controls(
    conditions: Sequence[ConditionOutcome], validation: Sequence[ValidationArrays]
) -> tuple[ControlDecision, ...]:
    by_id = {row.condition_id: row for row in conditions}
    arrays_by_id = {row.condition_id: row for row in validation}
    if not {"R00", "N00"}.issubset(by_id) or not {"R00", "N00"}.issubset(arrays_by_id):
        raise ValueError("both Arc 2B controls are required")
    return tuple(_control_decision(by_id[key], arrays_by_id[key]) for key in ("R00", "N00"))


def _fit_combined(
    conditions: Sequence[ConditionOutcome],
    validation: Sequence[ValidationArrays],
    predictions: Sequence[FrozenPrediction],
    bootstrap_count: int,
) -> tuple[CombinedFit, ...]:
    predictors = scaled_predictors(conditions)
    arrays_by_id = {row.condition_id: row for row in validation}
    count = conditions[0].validation_count
    rng = np.random.default_rng(BOOTSTRAP_SEED + 1)
    resamples = rng.integers(0, count, size=(bootstrap_count, count), dtype=np.int64)
    fits: list[CombinedFit] = []
    for spec in METRICS:
        frozen = next(row for row in predictions if row.metric_id == spec.metric_id)
        model_type = frozen.model_type
        raw = observed_metric(conditions, spec)
        response = transform_response(raw, spec.transform, count)
        matrix = design_matrix(predictors, model_type)
        coefficients = _fit_coefficients(matrix, response)
        boot = np.empty((bootstrap_count, len(coefficients)), dtype=np.float64)
        for index, indices in enumerate(resamples):
            boot_raw = np.asarray(
                [_aggregate(arrays_by_id[row.condition_id], spec, indices) for row in conditions]
            )
            boot_response = transform_response(boot_raw, spec.transform, count)
            boot[index] = _fit_coefficients(matrix, boot_response)
        fits.append(
            CombinedFit(
                spec.metric_id,
                spec.transform,
                model_type,
                _terms(model_type),
                coefficients,
                boot,
            )
        )
    return tuple(fits)


def _coefficient_rows(fits: Sequence[CombinedFit]) -> tuple[CoefficientRow, ...]:
    rows: list[CoefficientRow] = []
    for fit in fits:
        for index, term in enumerate(fit.terms):
            lower, upper = np.quantile(fit.bootstrap_coefficients[:, index], (0.025, 0.975))
            rows.append(
                CoefficientRow(
                    fit.metric_id,
                    fit.response_scale,
                    fit.model_type,
                    term,
                    float(fit.coefficients[index]),
                    float(lower),
                    float(upper),
                )
            )
    return tuple(rows)


def _grid_rows(fits: Sequence[CombinedFit]) -> tuple[GridRow, ...]:
    effects = np.exp(np.linspace(math.log(1.5), math.log(6.0), 31))
    backgrounds = np.linspace(0.05, 0.20, 31)
    detections = (0.40, 0.60, 0.80)
    coordinates = tuple(
        (float(effect), float(background), detection)
        for detection in detections
        for background in backgrounds
        for effect in effects
    )
    predictors = _coordinates_predictors(coordinates)
    rows: list[GridRow] = []
    for fit in fits:
        matrix = design_matrix(predictors, fit.model_type)
        estimates = inverse_response(matrix @ fit.coefficients, fit.response_scale)
        bootstrap = inverse_response(matrix @ fit.bootstrap_coefficients.T, fit.response_scale)
        lower, upper = np.quantile(bootstrap, (0.025, 0.975), axis=1)
        for coordinate, estimate, lo, hi in zip(coordinates, estimates, lower, upper, strict=True):
            rows.append(
                GridRow(
                    fit.metric_id,
                    fit.response_scale,
                    fit.model_type,
                    coordinate[2],
                    coordinate[0],
                    coordinate[1],
                    float(estimate),
                    float(lo),
                    float(hi),
                )
            )
    return tuple(rows)


def _event_information(conditions: Sequence[ConditionOutcome]) -> tuple[EventInformationRow, ...]:
    diagnostics = (
        "mean_true_extirpations_by_day60",
        "mean_pre_arrival_true_extirpations",
        "mean_post_arrival_true_extirpations",
        "mean_true_extirpation_censoring",
        "mean_post_arrival_at_risk_exposure",
        "mean_prey_observation_support",
    )
    rows: list[EventInformationRow] = []
    for diagnostic in diagnostics:
        x = np.asarray([float(getattr(row, diagnostic)) for row in conditions])
        for spec in METRICS:
            y = observed_metric(conditions, spec)
            correlation = (
                0.0
                if float(np.std(x)) <= 1e-15 or float(np.std(y)) <= 1e-15
                else float(np.corrcoef(x, y)[0, 1])
            )
            rows.append(EventInformationRow(diagnostic, spec.metric_id, correlation))
    return tuple(rows)


def run_synthesis(
    pilot: CampaignBlock,
    prospective: CampaignBlock,
    predictions: Sequence[FrozenPrediction],
    *,
    frozen_predictions_sha256: str | None,
    bootstrap_count: int = DEFAULT_BOOTSTRAPS,
) -> SynthesisResult:
    """Score the prospective block before descriptive 32-truth refitting."""
    validate_frozen_predictions(predictions)
    if {row.source_bundle_sha256 for row in predictions} != {pilot.bundle_sha256}:
        raise ValueError("frozen predictions are not bound to this pilot bundle")
    pilot_continuous = tuple(row for row in pilot.conditions if row.condition_id.startswith("S"))
    prospective_continuous = tuple(
        row for row in prospective.conditions if row.condition_id.startswith("S")
    )
    pilot_arrays = tuple(row for row in pilot.validation if row.condition_id.startswith("S"))
    prospective_arrays = tuple(
        row for row in prospective.validation if row.condition_id.startswith("S")
    )
    if {row.condition_id for row in pilot_continuous} != {
        f"S{index:02d}" for index in range(1, 17)
    } or {row.condition_id for row in prospective_continuous} != {
        f"S{index:02d}" for index in range(17, 33)
    }:
        raise ValueError("campaign blocks do not contain the prespecified truths")
    if not _coordinates_match_design(pilot_continuous, "pilot") or not _coordinates_match_design(
        prospective_continuous, "prospective"
    ):
        raise ValueError("campaign coordinates do not match the frozen Sobol design")

    # This is intentionally evaluated before any combined fit below.
    prospective_scores = score_prospective(
        prospective_continuous,
        prospective_arrays,
        predictions,
        bootstrap_count=bootstrap_count,
    )
    continuous = tuple(
        sorted((*pilot_continuous, *prospective_continuous), key=lambda x: x.condition_id)
    )
    validation = tuple(sorted((*pilot_arrays, *prospective_arrays), key=lambda x: x.condition_id))
    controls = classify_controls(pilot.conditions, pilot.validation)
    fits = _fit_combined(continuous, validation, predictions, bootstrap_count)
    coefficients = _coefficient_rows(fits)
    grid = _grid_rows(fits)
    event_information = _event_information(continuous)
    recovery_classes = {row.recovery_classification for row in continuous}
    eligible = tuple(row for row in prospective_scores if row.decision != "invariant")
    positive = sum(row.decision == "supported" for row in eligible)
    controls_valid = all(row.valid for row in controls)
    if not controls_valid:
        outcome = "control_review_required"
    elif len(recovery_classes) == 1 or not eligible or positive == 0:
        outcome = "review_arc2b_design_before_arc2c"
    elif positive == len(eligible):
        outcome = "close_arc2b_validated"
    else:
        outcome = "close_arc2b_with_surface_limits"
    checks = {
        "pilot_bundle_invariants_pass": all(pilot.invariants.values()),
        "prospective_bundle_invariants_pass": all(prospective.invariants.values()),
        "frozen_predictions_bound_to_pilot": (
            {row.source_bundle_sha256 for row in predictions} == {pilot.bundle_sha256}
        ),
        "frozen_commit_bound_to_pilot": (
            {row.source_campaign_commit for row in predictions} == {pilot.source_commit}
        ),
        "prospective_bound_to_frozen_predictions": (
            frozen_predictions_sha256 is not None
            and prospective.frozen_predictions_sha256 == frozen_predictions_sha256
        ),
        "truth_ids_complete": len(continuous) == 32,
        "paired_validation_indices_align": all(
            np.array_equal(row.dataset_index, validation[0].dataset_index) for row in validation[1:]
        ),
        "common_random_number_seeds_align": (
            pilot.validation_seeds_sha256 == prospective.validation_seeds_sha256
        ),
        "arrival_bank_aligns": pilot.bank_checksum == prospective.bank_checksum,
        "master_seed_aligns": pilot.master_seed == prospective.master_seed == 20260831,
        "controls_valid": controls_valid,
        "prospective_scored_before_combined_refit": True,
        "fixed_forms_retained": all(
            fit.model_type
            == next(row.model_type for row in predictions if row.metric_id == fit.metric_id)
            for fit in fits
        ),
    }
    if not all(value for key, value in checks.items() if key != "controls_valid"):
        outcome = "implementation_blocked"
    return SynthesisResult(
        continuous,
        validation,
        prospective_scores,
        fits,
        coefficients,
        grid,
        controls,
        event_information,
        {"pilot": pilot.source_commit, "prospective": prospective.source_commit},
        {
            "pilot_bundle": pilot.bundle_sha256,
            "prospective_bundle": prospective.bundle_sha256,
            "frozen_predictions": frozen_predictions_sha256 or "missing",
        },
        checks,
        outcome,
        bootstrap_count,
    )


def load_and_run_synthesis(
    pilot_dir: Path,
    prospective_dir: Path,
    frozen_predictions_path: Path = DEFAULT_FROZEN_PREDICTIONS,
    *,
    bootstrap_count: int = DEFAULT_BOOTSTRAPS,
) -> SynthesisResult:
    pilot = load_campaign_block(pilot_dir)
    prospective = load_campaign_block(prospective_dir)
    predictions = load_frozen_predictions(frozen_predictions_path)
    return run_synthesis(
        pilot,
        prospective,
        predictions,
        frozen_predictions_sha256=_sha256(frozen_predictions_path),
        bootstrap_count=bootstrap_count,
    )


def _summary(result: SynthesisResult) -> dict[str, Any]:
    class_counts = {
        classification: sum(
            row.recovery_classification == classification for row in result.conditions
        )
        for classification in (
            "fully_recovered",
            "detected_but_not_fully_recovered",
            "not_reliably_detected",
        )
    }
    strongest = sorted(
        result.event_information,
        key=lambda row: abs(row.pearson_correlation),
        reverse=True,
    )[:5]
    return {
        "workflow": "arc2b-prey-effect-recoverability-synthesis",
        "outcome": result.outcome,
        "truth_count": len(result.conditions),
        "bootstrap_count": result.bootstrap_count,
        "recovery_class_counts": class_counts,
        "controls": [asdict(row) for row in result.controls],
        "prospective_scores": [asdict(row) for row in result.prospective_scores],
        "predictive_comparator": {
            "primary": "known_background_no_effect",
            "secondary_descriptive": "fitted_neutral",
            "secondary_surface_fitted": False,
        },
        "strongest_descriptive_event_associations": [asdict(row) for row in strongest],
        "source_commits": result.source_commits,
        "source_sha256": result.source_sha256,
        "checks": result.checks,
        "interpretation_limits": [
            "Truth-specific calibration is an oracle operating-performance experiment.",
            "Background risk jointly changes event yield, hazard, exposure, and censoring.",
            "Event associations are descriptive truth-assisted diagnostics, not causal effects.",
            "The predator process, observation parameters, landscape, and likelihood "
            "are known and fixed.",
        ],
    }


def _report(result: SynthesisResult) -> str:
    class_counts = {
        label: sum(row.recovery_classification == label for row in result.conditions)
        for label in (
            "fully_recovered",
            "detected_but_not_fully_recovered",
            "not_reliably_detected",
        )
    }
    score_lines = "\n".join(
        f"- `{row.metric_id}`: {row.decision}; prospective skill "
        + ("invariant" if row.prospective_skill is None else f"{row.prospective_skill:.3f}")
        + f", RMSE {row.prospective_rmse:.3f}."
        for row in result.prospective_scores
    )
    control_lines = "\n".join(
        f"- `{row.condition_id}`: {row.decision}"
        + (f" (failed: {row.failed_gates})" if row.failed_gates else ".")
        for row in result.controls
    )
    reference = next(row for row in result.controls if row.condition_id == "R00")
    return f"""# Arc 2B prey-effect recoverability synthesis

## Plain-language result

Across 32 prespecified combinations of predator effect, background prey loss,
and prey detectability, the experiment asks where a known predator effect can
be estimated accurately and distinguished from no effect. The first 16 truths
selected simple response surfaces; the second 16 tested those frozen predictions
before any combined refit.

The final decision is **`{result.outcome}`**.

Recovery classifications across the 32 truths were:

- fully recovered: {class_counts["fully_recovered"]};
- detected but not fully recovered: {class_counts["detected_but_not_fully_recovered"]}; and
- not reliably detected: {class_counts["not_reliably_detected"]}.

## Prospective test

{score_lines}

Positive skill means the pilot surface predicted the new block better than the
frozen pilot mean. The paired bootstrap intervals quantify Monte Carlo precision
conditional on the realised local cutoffs; they are not total response-surface
uncertainty.

Predictive recovery is defined against the known-background no-effect model.
Advantage over a separately fitted neutral is retained only as a secondary
condition-level description and is not given another response surface.

## Controls

{control_lines}

The reference control is compared descriptively with Goal 031 rather than
required to reproduce its larger independent ensemble exactly. The neutral
control has no positive-control precision gate.

For `R00`, the current values versus Goal 031 are: coverage
{reference.coverage:.3f} versus 0.963; connected-and-interior frequency
{reference.connected_frequency:.3f} versus 0.993; no-effect exclusion
{reference.no_effect_exclusion_probability:.3f} versus 1.000; median absolute
log-effect error {reference.median_absolute_log_effect_error:.3f} versus 0.128;
median log-support width {reference.median_log_support_width:.3f} versus 0.757;
the primary mean held-out advantage over the known-background no-effect model is
{reference.mean_heldout_known_background_no_effect_advantage_per_record:.4f}
(lower bound {reference.heldout_known_background_no_effect_advantage_lower:.4f}).
The secondary mean advantage over a fitted neutral is
{reference.mean_heldout_fitted_neutral_advantage_per_record:.4f}, compared
descriptively with Goal 031's fitted-neutral value of 0.0530.

## Reading the map

The figure shows fixed-form descriptive refits after prospective scoring. Rows
hold prey detection at 0.40, 0.60, and 0.80; columns show the probability of
excluding no effect and median absolute log-effect error across effect strength
and 60-day background risk. All 32 simulated truths are projected onto each
representative detection slice; marker shape encodes recovery class and size
indicates mean latent true-extirpation yield by day 60.

Latent true extirpation yield, pre/post-arrival timing, censoring, exposure, and
observation support are provided as explanatory diagnostics. Their correlations
are descriptive and truth-assisted; background risk is not interpreted as a
causal isolated effect.

## Scope

This is an oracle operating-performance experiment on one landscape with known
predator dynamics, observation parameters, and background prey risk. It does not
establish transfer to unknown spread, misspecified process models, other
landscapes, or between-site dependence. Arc 2C is outside this goal.
"""


def _figure(result: SynthesisResult) -> Figure:
    figure, axes = plt.subplots(3, 2, figsize=(12.6, 14.2), constrained_layout=True)
    figure.suptitle(
        "Arc 2B: where is the predator effect on prey persistence recoverable?",
        fontsize=17,
        fontweight="bold",
    )
    metric_columns = (
        (
            "no_effect_exclusion_probability",
            "Probability of distinguishing predator effect from no effect",
            "viridis",
        ),
        (
            "median_absolute_log_effect_error",
            "Median absolute log-effect error",
            "magma_r",
        ),
    )
    event_values = np.asarray([row.mean_true_extirpations_by_day60 for row in result.conditions])
    event_span = float(np.ptp(event_values))
    event_scale = (
        (event_values - float(np.min(event_values))) / event_span
        if event_span > 0
        else np.full(len(event_values), 0.5, dtype=np.float64)
    )
    sizes = np.asarray(28.0 + 70.0 * event_scale, dtype=np.float64)
    limits = {
        metric_id: (
            min(row.estimate for row in result.grid_rows if row.metric_id == metric_id),
            max(row.estimate for row in result.grid_rows if row.metric_id == metric_id),
        )
        for metric_id, _, _ in metric_columns
    }
    norms = {
        metric_id: Normalize(vmin=lower, vmax=upper) for metric_id, (lower, upper) in limits.items()
    }
    meshes: dict[str, Any] = {}
    class_styles = {
        "fully_recovered": ("o", "#ffffff", "Fully recovered"),
        "detected_but_not_fully_recovered": (
            "^",
            "#38bdf8",
            "Detected, not fully recovered",
        ),
        "not_reliably_detected": ("x", "#ef4444", "Not reliably detected"),
    }
    for row_index, detection in enumerate((0.40, 0.60, 0.80)):
        for column_index, (metric_id, label, cmap) in enumerate(metric_columns):
            axis = axes[row_index, column_index]
            selected = [
                row
                for row in result.grid_rows
                if row.metric_id == metric_id
                and math.isclose(row.prey_detection_probability, detection)
            ]
            effects = sorted({row.effect_multiplier for row in selected})
            backgrounds = sorted({row.background_risk for row in selected})
            values = np.asarray([row.estimate for row in selected]).reshape(
                len(backgrounds), len(effects)
            )
            mesh = axis.pcolormesh(
                effects,
                backgrounds,
                values,
                shading="auto",
                cmap=cmap,
                norm=norms[metric_id],
            )
            meshes[metric_id] = mesh
            for classification, (marker, edge, _) in class_styles.items():
                indices = [
                    index
                    for index, row in enumerate(result.conditions)
                    if row.recovery_classification == classification
                ]
                if indices:
                    axis.scatter(
                        [result.conditions[index].effect_multiplier for index in indices],
                        [result.conditions[index].background_risk for index in indices],
                        s=sizes[indices],
                        marker=marker,
                        facecolors="none",
                        edgecolors=edge,
                        linewidths=0.9,
                    )
            axis.set_xscale("log")
            axis.set_xticks((1.5, 2.0, 3.0, 4.0, 6.0), labels=("1.5", "2", "3", "4", "6"))
            axis.set_xlabel("True predator-effect multiplier")
            axis.set_ylabel("60-day background prey-loss risk")
            axis.set_title(
                f"{chr(65 + row_index * 2 + column_index)}  {label}\n"
                f"Known prey detection = {detection:.2f}",
                loc="left",
                fontsize=10.5,
                fontweight="bold",
            )
    for column_index, (metric_id, label, _) in enumerate(metric_columns):
        figure.colorbar(
            meshes[metric_id],
            ax=axes[:, column_index],
            fraction=0.035,
            pad=0.025,
            label=label,
        )
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker=marker,
            color="none",
            markerfacecolor="none",
            markeredgecolor=edge,
            markeredgewidth=1.2,
            label=label,
        )
        for marker, edge, label in class_styles.values()
    ]
    figure.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=3,
        bbox_to_anchor=(0.5, 0.018),
        frameon=False,
    )
    figure.text(
        0.5,
        0.005,
        "All 32 truth points are projected across the representative prey-detection slices; "
        "larger markers indicate more latent true extirpations by day 60.",
        ha="center",
        fontsize=9,
    )
    return figure


def _write_csv(path: Path, rows: Sequence[Any]) -> None:
    payload = [asdict(row) for row in rows]
    if not payload:
        raise ValueError(f"cannot write empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(payload[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(payload)


def write_review_bundle(
    result: SynthesisResult, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / EXPECTED_FILES[0], result.conditions)
    _write_csv(output_dir / EXPECTED_FILES[1], result.prospective_scores)
    _write_csv(output_dir / EXPECTED_FILES[2], result.coefficient_rows)
    _write_csv(output_dir / EXPECTED_FILES[3], result.grid_rows)
    _write_csv(output_dir / EXPECTED_FILES[4], result.controls)
    _write_csv(output_dir / EXPECTED_FILES[5], result.event_information)
    (output_dir / EXPECTED_FILES[6]).write_text(
        json.dumps(_summary(result), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / EXPECTED_FILES[7]).write_text(_report(result), encoding="utf-8")
    figure = _figure(result)
    figure.savefig(output_dir / EXPECTED_FILES[8], format="svg", bbox_inches="tight")
    plt.close(figure)
    written = tuple(output_dir / name for name in EXPECTED_FILES)
    actual = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual != set(EXPECTED_FILES) or not all(path.stat().st_size > 0 for path in written):
        raise RuntimeError("Arc 2B synthesis artifact contract failed")
    return written


def summarize_for_cli(result: SynthesisResult) -> str:
    skills = ", ".join(
        f"{row.metric_id}="
        + ("invariant" if row.prospective_skill is None else f"{row.prospective_skill:.3f}")
        for row in result.prospective_scores
    )
    return (
        "Arc 2B prey-effect recoverability synthesis complete\n"
        f"Outcome: {result.outcome}\n"
        f"Truths: {len(result.conditions)}\n"
        f"Prospective skills: {skills}\n"
    )
