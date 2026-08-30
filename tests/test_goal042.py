from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from latent_landscapes import goal040, goal042


def _validation_arrays(
    condition_id: str,
    boundary_probability: float,
    exclusion_probability: float,
    detection_width: float,
    eta_width: float,
    brier_difference: float,
) -> goal040.ValidationArrays:
    indices = np.arange(250, dtype=np.int64)
    wave = 0.004 * np.sin(indices * 0.17)
    return goal040.ValidationArrays(
        condition_id,
        indices,
        indices < round(boundary_probability * 250),
        indices < round(exclusion_probability * 250),
        np.asarray(detection_width + wave, dtype=np.float64),
        np.asarray(eta_width + wave, dtype=np.float64),
        np.asarray(brier_difference + 0.2 * wave, dtype=np.float64),
    )


def _inputs() -> goal042.Goal042Inputs:
    conditions: list[goal040.ConditionOutcome] = []
    validation: list[goal040.ValidationArrays] = []
    for zero_index in range(32):
        index = zero_index + 1
        u_rho = (zero_index + 0.5) / 32
        u_eta = ((zero_index * 11) % 32 + 0.5) / 32
        u_probability = ((zero_index * 7) % 32 + 0.5) / 32
        rho = 2.0 ** (-1.0 + 2.0 * u_rho)
        eta = 0.25 + 1.75 * u_eta
        probability = 0.35 + 0.50 * u_probability
        x_rho = math.log2(rho)
        x_eta = (eta - 1.125) / 0.875
        x_probability = (probability - 0.60) / 0.25
        boundary = 1.0 / (1.0 + math.exp(3.0 + 1.8 * x_eta))
        exclusion = 1.0 / (1.0 + math.exp(-2.2 - 1.7 * x_eta))
        detection_width = 0.18 - 0.055 * x_rho + 0.012 * x_probability
        eta_width = 0.68 + 0.025 * x_rho + 0.035 * x_eta
        brier = -0.04 + 0.012 * x_rho - 0.01 * x_eta * x_probability
        arrays = _validation_arrays(
            f"S{index:02d}", boundary, exclusion, detection_width, eta_width, brier
        )
        validation.append(arrays)
        coverage = 0.916 if index == 20 else 0.95
        coverage_lower = 0.875 if index == 20 else 0.915
        coverage_upper = 0.944 if index == 20 else 0.972
        conditions.append(
            goal040.ConditionOutcome(
                f"S{index:02d}",
                "sobol_pilot" if index <= 16 else "sobol_nested_validation",
                rho,
                eta,
                probability,
                250,
                coverage,
                coverage_lower,
                coverage_upper,
                0.04,
                0.10,
                0.015,
                0.30,
                float(np.median(arrays.projected_eta_width)),
                float(np.median(arrays.projected_probability_width)),
                float(np.mean(arrays.support_boundary_contact)),
                float(np.mean(arrays.eta_zero_excluded)),
                float(np.mean(arrays.paired_brier_difference)),
                "test",
            )
        )
    prospective = (
        goal042.ProspectiveEvidence(
            "boundary_contact_probability", 0.24, 0.14, 0.21, -0.2, 0.75, 0.5, 10, 6
        ),
        goal042.ProspectiveEvidence(
            "detection_interval_width", 0.02, 0.04, 0.05, 0.8, 1.0, 1.0, 9, 7
        ),
        goal042.ProspectiveEvidence("eta_interval_width", 0.07, 0.09, 0.09, 0.3, 1.0, 1.0, 15, 1),
        goal042.ProspectiveEvidence(
            "eta_zero_exclusion_probability", 0.19, 0.17, 0.22, 0.2, 0.88, 0.81, 12, 4
        ),
        goal042.ProspectiveEvidence(
            "heldout_brier_difference", 0.008, 0.006, 0.024, 0.88, 0.88, 1.0, 16, 0
        ),
    )
    return goal042.Goal042Inputs(
        tuple(conditions),
        tuple(validation),
        prospective,
        {"goal039": "test-039", "goal041": "test-041"},
        {"test": "digest"},
        {"synthetic_fixture": True},
    )


def test_run_goal042_closes_arc2a_without_smoothing_topology() -> None:
    result = goal042.run_goal042(_inputs(), bootstrap_count=8)

    assert result.outcome == "arc2a_ready_for_closeout_with_topology_limit"
    assert len(result.fits) == 4
    assert len(result.condition_rows) == 32
    assert len(result.grid_rows) == 4 * 3 * 25 * 25
    assert all(not row.smooth_surface_supported for row in result.topology_rows)
    assert result.checks["retained_metrics_have_positive_prospective_skill"]
    assert result.checks["boundary_surface_failure_preserved"]


def test_goal042_writes_exact_compact_bundle(tmp_path: Path) -> None:
    result = goal042.run_goal042(_inputs(), bootstrap_count=8)
    written = goal042.write_review_bundle(result, tmp_path)

    assert tuple(path.name for path in written) == goal042.EXPECTED_FILES
    assert {path.name for path in tmp_path.iterdir()} == set(goal042.EXPECTED_FILES)
    summary = json.loads((tmp_path / "synthesis_summary.json").read_text())
    assert summary["truth_count"] == 32
    assert summary["boundary_contact"]["smooth_surface_supported"] is False
    assert summary["outcome"] == "arc2a_ready_for_closeout_with_topology_limit"
    synthesis = (tmp_path / "synthesis.md").read_text()
    assert "The prospective test came first" in synthesis
    assert "No targeted enrichment or flexible emulator is recommended" in synthesis
