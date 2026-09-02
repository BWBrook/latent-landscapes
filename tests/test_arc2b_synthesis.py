from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from matplotlib import pyplot as plt

from latent_landscapes import arc2b_synthesis
from latent_landscapes.arc2b_design import truths_for_block


def _write_dict_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _condition(
    condition_id: str,
    effect: float,
    background: float,
    detection: float,
    *,
    role: str = "sobol_prospective",
    count: int = 20,
    error: float = 0.10,
    width: float = 0.50,
    score: float = 0.04,
    fitted_score: float = 0.03,
    connected: float = 1.0,
    exclusion: float = 1.0,
    score_lower: float = 0.02,
    fitted_score_lower: float = 0.01,
) -> arc2b_synthesis.ConditionOutcome:
    return arc2b_synthesis.ConditionOutcome(
        condition_id,
        role,
        effect,
        background,
        detection,
        count,
        0.95,
        0.92,
        0.98,
        connected,
        exclusion,
        error,
        width,
        score,
        score_lower,
        0.06,
        fitted_score,
        fitted_score_lower,
        0.05,
        80.0,
        20.0,
        60.0,
        80.0,
        900.0,
        120.0,
        "fully_recovered",
        "",
    )


def _arrays(
    condition_id: str,
    *,
    count: int = 20,
    error: float = 0.10,
    width: float = 0.50,
    score: float = 0.04,
    fitted_score: float = 0.03,
    connected_count: int | None = None,
    exclusion_count: int | None = None,
) -> arc2b_synthesis.ValidationArrays:
    connected_count = count if connected_count is None else connected_count
    exclusion_count = count if exclusion_count is None else exclusion_count
    index = np.arange(count, dtype=np.int64)
    connected = index < connected_count
    return arc2b_synthesis.ValidationArrays(
        condition_id,
        index,
        index < round(0.95 * count),
        connected,
        connected,
        index < exclusion_count,
        np.full(count, error),
        np.full(count, width),
        np.full(count, score),
        np.full(count, fitted_score),
    )


def _pilot_conditions() -> tuple[arc2b_synthesis.ConditionOutcome, ...]:
    output: list[arc2b_synthesis.ConditionOutcome] = []
    for truth in truths_for_block("pilot"):
        base = _condition(
            truth.condition_id,
            truth.effect_multiplier,
            truth.background_risk,
            truth.prey_detection_probability,
            role="sobol_pilot",
            count=250,
        )
        x_effect, x_background, _ = arc2b_synthesis.scaled_predictors((base,))[0]
        output.append(
            replace(
                base,
                median_absolute_log_effect_error=(
                    0.12 + 0.02 * x_effect + 0.01 * x_background + 0.08 * x_effect * x_background
                ),
            )
        )
    return tuple(output)


def _frozen_rows() -> tuple[arc2b_synthesis.FrozenPrediction, ...]:
    rows: list[arc2b_synthesis.FrozenPrediction] = []
    coefficients_by_metric = {
        "median_absolute_log_effect_error": (0.12, 0.02, 0.0, 0.0),
        "median_log_support_width": (0.50, 0.04, 0.0, 0.0),
        "mean_heldout_known_background_no_effect_advantage_per_record": (
            0.04,
            0.01,
            0.0,
            0.0,
        ),
        "connected_interior_frequency": (3.0, 0.4, 0.0, 0.0),
        "no_effect_exclusion_probability": (2.5, 0.7, 0.0, 0.0),
    }
    for spec in arc2b_synthesis.METRICS:
        coefficients = np.asarray(coefficients_by_metric[spec.metric_id])
        for truth in truths_for_block("prospective"):
            base = _condition(
                truth.condition_id,
                truth.effect_multiplier,
                truth.background_risk,
                truth.prey_detection_probability,
            )
            predictors = arc2b_synthesis.scaled_predictors((base,))
            fitting = float(arc2b_synthesis.design_matrix(predictors, "additive")[0] @ coefficients)
            observed = float(
                arc2b_synthesis.inverse_response(np.asarray([fitting]), spec.transform)[0]
            )
            rows.append(
                arc2b_synthesis.FrozenPrediction(
                    "pilot-digest",
                    "pilot-commit",
                    truth.condition_id,
                    truth.effect_multiplier,
                    truth.background_risk,
                    truth.prey_detection_probability,
                    spec.metric_id,
                    spec.transform,
                    "additive",
                    '["intercept","xE","xB","xP"]',
                    json.dumps(coefficients.tolist(), separators=(",", ":")),
                    fitting,
                    observed,
                    0.0,
                    0.05,
                    0.06,
                    0.07,
                    False,
                )
            )
    return tuple(rows)


def test_surface_selection_uses_prespecified_ten_percent_rule() -> None:
    spec = arc2b_synthesis.METRIC_BY_ID["median_absolute_log_effect_error"]
    interaction = arc2b_synthesis.select_surface(_pilot_conditions(), spec)
    invariant = arc2b_synthesis.select_surface(
        tuple(replace(row, median_absolute_log_effect_error=0.2) for row in _pilot_conditions()),
        spec,
    )

    assert interaction.model_type == "two_way_interactions"
    assert interaction.interaction_loto_rmse <= 0.90 * interaction.additive_loto_rmse
    assert invariant.model_type == "invariant"


def test_frozen_prediction_validation_rejects_coordinate_tampering() -> None:
    rows = _frozen_rows()
    arc2b_synthesis.validate_frozen_predictions(rows)

    tampered = (replace(rows[0], effect_multiplier=rows[0].effect_multiplier + 0.1), *rows[1:])
    with pytest.raises(ValueError, match="coordinates changed"):
        arc2b_synthesis.validate_frozen_predictions(tampered)


def test_prospective_score_uses_frozen_predictions_and_mean() -> None:
    frozen = _frozen_rows()
    conditions: list[arc2b_synthesis.ConditionOutcome] = []
    arrays: list[arc2b_synthesis.ValidationArrays] = []
    for truth in truths_for_block("prospective"):
        metric_rows = {
            row.metric_id: row for row in frozen if row.condition_id == truth.condition_id
        }
        conditions.append(
            _condition(
                truth.condition_id,
                truth.effect_multiplier,
                truth.background_risk,
                truth.prey_detection_probability,
                error=metric_rows[
                    "median_absolute_log_effect_error"
                ].frozen_prediction_observed_scale,
                width=metric_rows["median_log_support_width"].frozen_prediction_observed_scale,
                score=metric_rows[
                    "mean_heldout_known_background_no_effect_advantage_per_record"
                ].frozen_prediction_observed_scale,
                connected=metric_rows[
                    "connected_interior_frequency"
                ].frozen_prediction_observed_scale,
                exclusion=metric_rows[
                    "no_effect_exclusion_probability"
                ].frozen_prediction_observed_scale,
            )
        )
        arrays.append(
            _arrays(
                truth.condition_id,
                error=conditions[-1].median_absolute_log_effect_error,
                width=conditions[-1].median_log_support_width,
                score=(conditions[-1].mean_heldout_known_background_no_effect_advantage_per_record),
                connected_count=round(conditions[-1].connected_interior_frequency * 20),
                exclusion_count=round(conditions[-1].no_effect_exclusion_probability * 20),
            )
        )

    scores = arc2b_synthesis.score_prospective(conditions, arrays, frozen, bootstrap_count=8)

    assert len(scores) == 5
    assert all(row.prospective_skill is not None and row.prospective_skill > 0.80 for row in scores)
    assert all(row.decision == "supported" for row in scores)
    assert not any("fitted_neutral" in row.metric_id for row in scores)


def test_control_classification_applies_distinct_reference_and_null_rules() -> None:
    reference = _condition("R00", 5.0, 0.113, 0.65, role="reference_control", count=250, width=1.20)
    neutral = _condition(
        "N00",
        1.0,
        0.113,
        0.65,
        role="neutral_control",
        count=250,
        exclusion=0.04,
        score_lower=-0.01,
    )
    reference_arrays = _arrays("R00", count=250)
    neutral_arrays = _arrays("N00", count=250, exclusion_count=10)

    controls = arc2b_synthesis.classify_controls(
        (reference, neutral), (reference_arrays, neutral_arrays)
    )

    assert [row.decision for row in controls] == [
        "reference_control_valid",
        "neutral_control_valid",
    ]
    assert controls[0].median_log_support_width == 1.20
    failed_reference = replace(reference, no_effect_exclusion_probability=0.80)
    failed = arc2b_synthesis.classify_controls(
        (failed_reference, neutral), (reference_arrays, neutral_arrays)
    )
    assert failed[0].valid is False
    assert "excludes_no_effect" in failed[0].failed_gates


def test_continuous_recovery_classification_retains_width_gate() -> None:
    classification, failed = arc2b_synthesis._classification(
        {
            "validation_count": "250",
            "coverage_lower": "0.92",
            "coverage_upper": "0.98",
            "connected_interior_frequency": "0.96",
            "no_effect_exclusion_probability": "0.96",
            "median_absolute_log_effect_error": "0.10",
            "median_log_support_width": "0.90",
            "heldout_known_background_no_effect_advantage_lower": "0.01",
        }
    )

    assert classification == "detected_but_not_fully_recovered"
    assert failed == "support_width"


def test_campaign_bundle_round_trip_respects_neutral_boundary_exemption(
    tmp_path: Path,
) -> None:
    truth = truths_for_block("pilot")[0]
    conditions = (
        (
            truth.condition_id,
            "sobol_pilot",
            truth.effect_multiplier,
            truth.background_risk,
            truth.prey_detection_probability,
            1.0,
        ),
        ("R00", "reference_control", 5.0, 0.113, 0.65, 1.0),
        ("N00", "neutral_control", 1.0, 0.113, 0.65, 1.0),
    )
    summaries: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    for condition_id, role, effect, background, detection, connected_frequency in conditions:
        exclusion_count = 1 if condition_id == "N00" else 4
        summaries.append(
            {
                "condition_id": condition_id,
                "design_role": role,
                "truth_effect_multiplier": effect,
                "truth_background_risk": background,
                "truth_prey_detection_probability": detection,
                "cutoff": 2.0,
                "validation_count": 4,
                "coverage": 0.75,
                "coverage_lower": 0.30,
                "coverage_upper": 0.95,
                "connected_interior_frequency": connected_frequency,
                "no_effect_exclusion_probability": exclusion_count / 4,
                "median_absolute_log_effect_error": 0.10,
                "median_log_support_width": 0.50,
                "mean_heldout_known_background_no_effect_advantage_per_record": 0.04,
                "heldout_known_background_no_effect_advantage_lower": 0.01,
                "heldout_known_background_no_effect_advantage_upper": 0.07,
                "mean_heldout_fitted_neutral_advantage_per_record": 0.03,
                "heldout_fitted_neutral_advantage_lower": 0.00,
                "heldout_fitted_neutral_advantage_upper": 0.06,
                "mean_true_extirpations_by_day60": 80.0,
                "mean_pre_arrival_true_extirpations": 20.0,
                "mean_post_arrival_true_extirpations": 60.0,
                "mean_true_extirpation_censoring": 80.0,
                "mean_post_arrival_at_risk_exposure": 900.0,
                "mean_prey_observation_support": 120.0,
                "failure_classification": "fixture",
            }
        )
        for index in range(4):
            metrics.append(
                {
                    "condition_id": condition_id,
                    "dataset_index": index,
                    "truth_included": index < 3,
                    "support_component_count": 1,
                    # The null truth may touch the physical lower boundary and remain valid.
                    "support_boundary_contact": condition_id == "N00",
                    "no_effect_excluded": index < exclusion_count,
                    "mle_effect_multiplier": effect,
                    "absolute_log_effect_error": 0.10,
                    "log_support_width": 0.50,
                    "heldout_known_background_no_effect_advantage_per_record": 0.04,
                    "heldout_fitted_neutral_advantage_per_record": 0.03,
                    "true_extirpations_by_day60": 80,
                    "pre_arrival_true_extirpations": 20,
                    "post_arrival_true_extirpations": 60,
                    "true_extirpation_censoring": 80,
                    "post_arrival_at_risk_exposure": 900.0,
                    "prey_observation_support": 120,
                }
            )
    _write_dict_rows(tmp_path / "validation_condition_summaries.csv", summaries)
    _write_dict_rows(tmp_path / "validation_metrics.csv", metrics)
    (tmp_path / "summary.json").write_text(
        json.dumps({"invariants": {"fixture": True}}), encoding="utf-8"
    )
    (tmp_path / "seed_provenance.json").write_text(
        json.dumps(
            {
                "source_commit": "fixture-commit",
                "bank_checksum": "fixture-bank",
                "master_seed": 20260831,
                "validation_seeds": [{"index": index} for index in range(4)],
            }
        ),
        encoding="utf-8",
    )

    block = arc2b_synthesis.load_campaign_block(tmp_path)

    neutral = next(row for row in block.validation if row.condition_id == "N00")
    assert np.all(neutral.connected)
    assert not np.any(neutral.connected_interior)
    loaded_summary = next(row for row in block.conditions if row.condition_id == "N00")
    assert loaded_summary.connected_interior_frequency == 1.0


def test_final_synthesis_writes_compact_review_bundle(tmp_path: Path) -> None:
    frozen = _frozen_rows()
    pilot_continuous = _pilot_conditions()
    reference = _condition("R00", 5.0, 0.113, 0.65, role="reference_control", count=250)
    neutral = _condition(
        "N00",
        1.0,
        0.113,
        0.65,
        role="neutral_control",
        count=250,
        exclusion=0.04,
        score_lower=-0.01,
    )
    pilot_conditions = (*pilot_continuous, reference, neutral)
    pilot_arrays = tuple(
        _arrays(
            row.condition_id,
            count=250,
            error=row.median_absolute_log_effect_error,
            width=row.median_log_support_width,
            score=row.mean_heldout_known_background_no_effect_advantage_per_record,
            fitted_score=row.mean_heldout_fitted_neutral_advantage_per_record,
            connected_count=250,
            exclusion_count=10 if row.condition_id == "N00" else 250,
        )
        for row in pilot_conditions
    )
    prospective_conditions: list[arc2b_synthesis.ConditionOutcome] = []
    prospective_arrays: list[arc2b_synthesis.ValidationArrays] = []
    for truth in truths_for_block("prospective"):
        by_metric = {row.metric_id: row for row in frozen if row.condition_id == truth.condition_id}
        condition = _condition(
            truth.condition_id,
            truth.effect_multiplier,
            truth.background_risk,
            truth.prey_detection_probability,
            count=250,
            error=by_metric["median_absolute_log_effect_error"].frozen_prediction_observed_scale,
            width=by_metric["median_log_support_width"].frozen_prediction_observed_scale,
            score=by_metric[
                "mean_heldout_known_background_no_effect_advantage_per_record"
            ].frozen_prediction_observed_scale,
            connected=by_metric["connected_interior_frequency"].frozen_prediction_observed_scale,
            exclusion=by_metric["no_effect_exclusion_probability"].frozen_prediction_observed_scale,
        )
        prospective_conditions.append(condition)
        prospective_arrays.append(
            _arrays(
                truth.condition_id,
                count=250,
                error=condition.median_absolute_log_effect_error,
                width=condition.median_log_support_width,
                score=(condition.mean_heldout_known_background_no_effect_advantage_per_record),
                fitted_score=condition.mean_heldout_fitted_neutral_advantage_per_record,
                connected_count=round(condition.connected_interior_frequency * 250),
                exclusion_count=round(condition.no_effect_exclusion_probability * 250),
            )
        )
    pilot = arc2b_synthesis.CampaignBlock(
        tuple(pilot_conditions),
        pilot_arrays,
        "pilot-digest",
        "pilot-commit",
        "bank-digest",
        20260831,
        "seed-digest",
        None,
        {"test": True},
    )
    prospective = arc2b_synthesis.CampaignBlock(
        tuple(prospective_conditions),
        tuple(prospective_arrays),
        "prospective-digest",
        "prospective-commit",
        "bank-digest",
        20260831,
        "seed-digest",
        "predictions-digest",
        {"test": True},
    )

    result = arc2b_synthesis.run_synthesis(
        pilot,
        prospective,
        frozen,
        frozen_predictions_sha256="predictions-digest",
        bootstrap_count=4,
    )
    figure = arc2b_synthesis._figure(result)
    plot_axes = figure.axes[:6]
    for axis_indices in ((0, 2, 4), (1, 3, 5)):
        limits = {
            (
                plot_axes[index].collections[0].norm.vmin,
                plot_axes[index].collections[0].norm.vmax,
            )
            for index in axis_indices
        }
        assert len(limits) == 1
    assert {text.get_text() for text in figure.legends[0].get_texts()} == {
        "Fully recovered",
        "Detected, not fully recovered",
        "Not reliably detected",
    }
    plt.close(figure)
    written = arc2b_synthesis.write_review_bundle(result, tmp_path)

    assert tuple(path.name for path in written) == arc2b_synthesis.EXPECTED_FILES
    assert {path.name for path in tmp_path.iterdir()} == set(arc2b_synthesis.EXPECTED_FILES)
    summary = json.loads((tmp_path / "synthesis_summary.json").read_text())
    assert summary["truth_count"] == 32
    assert summary["predictive_comparator"] == {
        "primary": "known_background_no_effect",
        "secondary_descriptive": "fitted_neutral",
        "secondary_surface_fitted": False,
    }
    assert summary["checks"]["prospective_scored_before_combined_refit"] is True
    assert summary["checks"]["prospective_bound_to_frozen_predictions"] is True
    figure_text = (tmp_path / "arc2b_recovery_map.svg").read_text()
    assert "projected across the representative prey-detection slices" in figure_text
    assert "latent true extirpations by day 60" in figure_text
    report = (tmp_path / "synthesis.md").read_text()
    assert "known-background no-effect model" in report
    assert "fitted neutral" in report

    blocked = arc2b_synthesis.run_synthesis(
        pilot,
        replace(prospective, frozen_predictions_sha256="different-digest"),
        frozen,
        frozen_predictions_sha256="predictions-digest",
        bootstrap_count=2,
    )
    assert blocked.outcome == "implementation_blocked"
    assert blocked.checks["prospective_bound_to_frozen_predictions"] is False
