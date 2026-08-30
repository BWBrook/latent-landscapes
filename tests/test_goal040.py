from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

from latent_landscapes import goal040

TRUTHS = (
    (0.857, 1.752, 0.466),
    (1.648, 0.412, 0.631),
    (1.208, 1.367, 0.563),
    (0.587, 1.011, 0.775),
    (0.641, 1.208, 0.700),
    (1.106, 0.689, 0.365),
    (1.799, 1.924, 0.798),
    (0.784, 0.639, 0.510),
    (0.749, 1.544, 0.835),
    (1.894, 1.024, 0.500),
    (1.062, 1.602, 0.690),
    (0.664, 0.317, 0.402),
    (0.512, 1.855, 0.569),
    (1.380, 0.515, 0.734),
    (1.459, 1.250, 0.425),
    (0.973, 0.894, 0.637),
)


def _probability(logit: float) -> float:
    return 1.0 / (1.0 + math.exp(-logit))


def _arrays(
    condition_id: str,
    boundary_probability: float,
    exclusion_probability: float,
    probability_width: float,
    eta_width: float,
    brier_difference: float,
) -> goal040.ValidationArrays:
    index = np.arange(250, dtype=np.int64)
    wave = np.sin(index * 0.17)
    return goal040.ValidationArrays(
        condition_id,
        index,
        index < round(boundary_probability * 250),
        index < round(exclusion_probability * 250),
        np.asarray(probability_width + 0.004 * wave, dtype=np.float64),
        np.asarray(eta_width + 0.004 * wave, dtype=np.float64),
        np.asarray(brier_difference + 0.001 * wave, dtype=np.float64),
    )


def _test_inputs() -> goal040.Goal039Inputs:
    conditions: list[goal040.ConditionOutcome] = []
    arrays: list[goal040.ValidationArrays] = []
    for index, (rho, eta, probability) in enumerate(TRUTHS, start=1):
        x_rho = math.log2(rho)
        x_eta = (eta - 1.125) / 0.875
        x_probability = (probability - 0.60) / 0.25
        boundary = _probability(-3.8 - 2.4 * x_eta + 1.2 * x_rho * x_probability)
        exclusion = _probability(3.2 + 2.0 * x_eta - 0.8 * x_rho * x_probability)
        probability_width = 0.19 - 0.045 * x_rho + 0.008 * x_probability
        eta_width = 0.85 if index == 10 else 0.65
        brier = -0.04 + 0.012 * x_rho - 0.014 * x_eta * x_probability
        condition_arrays = _arrays(
            f"S{index:02d}",
            boundary,
            exclusion,
            probability_width,
            eta_width,
            brier,
        )
        arrays.append(condition_arrays)
        conditions.append(
            goal040.ConditionOutcome(
                f"S{index:02d}",
                "sobol_pilot",
                rho,
                eta,
                probability,
                250,
                0.95,
                0.92,
                0.97,
                0.03,
                0.10,
                0.01,
                0.30,
                float(np.median(condition_arrays.projected_eta_width)),
                float(np.median(condition_arrays.projected_probability_width)),
                float(np.mean(condition_arrays.support_boundary_contact)),
                float(np.mean(condition_arrays.eta_zero_excluded)),
                float(np.mean(condition_arrays.paired_brier_difference)),
                "test",
            )
        )
    diagnostic_arrays = _arrays("D00", 0.996, 0.004, 0.20, 0.25, -0.07)
    diagnostic = goal040.ConditionOutcome(
        "D00",
        "no_resistance_diagnostic",
        1.0,
        0.0,
        0.65,
        250,
        0.95,
        0.92,
        0.97,
        0.03,
        0.0,
        0.02,
        0.14,
        float(np.median(diagnostic_arrays.projected_eta_width)),
        float(np.median(diagnostic_arrays.projected_probability_width)),
        float(np.mean(diagnostic_arrays.support_boundary_contact)),
        float(np.mean(diagnostic_arrays.eta_zero_excluded)),
        float(np.mean(diagnostic_arrays.paired_brier_difference)),
        "no_resistance_diagnostic",
    )
    arrays.append(diagnostic_arrays)
    return goal040.Goal039Inputs(
        (diagnostic, *conditions),
        tuple(conditions),
        diagnostic,
        tuple(arrays),
        "test-commit",
        {"truth_summary.csv": "test"},
        {"test_inputs": True},
    )


def _write_goal039_fixture(root: Path, inputs: goal040.Goal039Inputs) -> None:
    root.mkdir()
    with (root / "truth_summary.csv").open("w", encoding="utf-8", newline="") as handle:
        truth_fields = (
            "condition_id",
            "design_role",
            "truth_rho",
            "truth_eta",
            "truth_probability",
            "validation_count",
            "coverage",
            "coverage_lower",
            "coverage_upper",
            "median_absolute_log_rho_error",
            "median_absolute_eta_error",
            "median_absolute_probability_error",
            "median_projected_log_rho_width",
            "median_projected_eta_width",
            "median_projected_probability_width",
            "boundary_contact_count",
            "eta_zero_exclusion_probability",
            "mean_paired_brier_difference",
            "outcome",
        )
        writer = csv.DictWriter(handle, fieldnames=truth_fields)
        writer.writeheader()
        for row in inputs.conditions:
            writer.writerow(
                {
                    "condition_id": row.condition_id,
                    "design_role": row.design_role,
                    "truth_rho": row.rho,
                    "truth_eta": row.eta,
                    "truth_probability": row.probability,
                    "validation_count": row.validation_count,
                    "coverage": row.coverage,
                    "coverage_lower": row.coverage_lower,
                    "coverage_upper": row.coverage_upper,
                    "median_absolute_log_rho_error": row.median_absolute_log_rho_error,
                    "median_absolute_eta_error": row.median_absolute_eta_error,
                    "median_absolute_probability_error": row.median_absolute_probability_error,
                    "median_projected_log_rho_width": row.median_log_rho_width,
                    "median_projected_eta_width": row.median_eta_width,
                    "median_projected_probability_width": row.median_probability_width,
                    "boundary_contact_count": round(
                        row.boundary_contact_probability * row.validation_count
                    ),
                    "eta_zero_exclusion_probability": row.eta_zero_exclusion_probability,
                    "mean_paired_brier_difference": row.mean_paired_brier_difference,
                    "outcome": row.goal039_outcome,
                }
            )
    with (root / "validation_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        validation_fields = (
            "condition_id",
            "dataset_index",
            "support_boundary_contact",
            "eta_zero_excluded",
            "projected_probability_width",
            "projected_eta_width",
            "paired_brier_difference",
        )
        writer = csv.DictWriter(handle, fieldnames=validation_fields)
        writer.writeheader()
        for validation in inputs.validation:
            for index in range(250):
                writer.writerow(
                    {
                        "condition_id": validation.condition_id,
                        "dataset_index": index,
                        "support_boundary_contact": bool(
                            validation.support_boundary_contact[index]
                        ),
                        "eta_zero_excluded": bool(validation.eta_zero_excluded[index]),
                        "projected_probability_width": (
                            validation.projected_probability_width[index]
                        ),
                        "projected_eta_width": validation.projected_eta_width[index],
                        "paired_brier_difference": validation.paired_brier_difference[index],
                    }
                )
    (root / "summary.json").write_text(
        json.dumps(
            {
                "outcome": "ready_for_arc2a_response_surface_review",
                "invariants": {"goal039": True},
            }
        ),
        encoding="utf-8",
    )
    (root / "run_provenance.json").write_text(
        json.dumps({"source_commit": inputs.source_commit}), encoding="utf-8"
    )


def test_loader_reconciles_paired_goal039_bundle(tmp_path: Path) -> None:
    source = _test_inputs()
    input_dir = tmp_path / "goal039"
    _write_goal039_fixture(input_dir, source)
    loaded = goal040.load_goal039_inputs(input_dir)
    assert all(loaded.invariants.values())
    assert len(loaded.continuous) == 16
    assert loaded.diagnostic.condition_id == "D00"
    assert loaded.source_commit == "test-commit"


def test_surface_selection_and_extension_decision_are_reproducible() -> None:
    result = goal040.run_goal040(_test_inputs(), bootstrap_count=24)
    fits = {fit.spec.metric_id: fit for fit in result.fits}
    assert fits["boundary_contact_probability"].selected_model_type == "two_way_interactions"
    assert fits["detection_interval_width"].selected_model_type == "additive"
    assert fits["eta_interval_width"].selected.loo_skill <= 0.20
    assert result.recommendation == "extend_to_nested_32_for_eta_precision_validation"
    assert result.unresolved_decision is not None
    assert all(result.invariants.values())


def test_review_bundle_is_exact_and_nonempty(tmp_path: Path) -> None:
    result = goal040.run_goal040(_test_inputs(), bootstrap_count=16)
    written = goal040.write_review_bundle(result, tmp_path)
    assert tuple(path.name for path in written) == goal040.EXPECTED_FILES
    assert {path.name for path in tmp_path.iterdir()} == set(goal040.EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    summary = json.loads((tmp_path / "analysis_summary.json").read_text(encoding="utf-8"))
    assert summary["recommendation"] == result.recommendation
    assert summary["bootstrap"]["paired_resampling_unit"].startswith("validation")
    with (tmp_path / "condition_outcomes.csv").open(encoding="utf-8") as handle:
        assert len(tuple(csv.DictReader(handle))) == 17
