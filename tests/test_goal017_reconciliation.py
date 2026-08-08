from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from latent_landscapes.goal017.artifacts import EXPECTED_FILES, write_review_bundle
from latent_landscapes.goal017.reconciliation import analyze_evidence


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_evidence(root: Path) -> tuple[Path, Path]:
    goal012 = root / "goal012"
    goal016 = root / "goal016"
    validation_rows: list[dict[str, object]] = []
    profile_rows: list[dict[str, object]] = []
    cell_summary_rows: list[dict[str, object]] = []
    funnel_rows: list[dict[str, object]] = []
    for cell, rho in (("cell-00", 0.5), ("cell-01", 1.0), ("cell-02", 2.0)):
        for bank in ("full", "first_half", "second_half"):
            validation_rows.extend(
                [
                    {
                        "truth_cell": cell,
                        "truth_rho": rho,
                        "truth_eta": 0.5,
                        "bank_variant": bank,
                        "block_index": 0,
                        "expanded_minimum_absolute_eta_error": 0.0,
                        "expanded_mle_cells": json.dumps([[rho, 0.5]]),
                        "expanded_support_boundary_faces": json.dumps(["eta_min"]),
                        "expanded_truth_included": True,
                    },
                    {
                        "truth_cell": cell,
                        "truth_rho": rho,
                        "truth_eta": 0.5,
                        "bank_variant": bank,
                        "block_index": 1,
                        "expanded_minimum_absolute_eta_error": 0.25,
                        "expanded_mle_cells": json.dumps([[rho, 0.25]]),
                        "expanded_support_boundary_faces": json.dumps([]),
                        "expanded_truth_included": True,
                    },
                ]
            )
            cell_summary_rows.append(
                {
                    "truth_cell": cell,
                    "truth_rho": rho,
                    "truth_eta": 0.5,
                    "bank_variant": bank,
                    "draw_count": 8,
                    "expanded_cutoff": 6.0,
                    "expanded_cutoff_sample_size": 2,
                }
            )
        for eta, log_likelihood in ((0.0, -5.0), (0.25, -2.0), (0.5, -1.0)):
            for profile_rho in (rho / 2.0, rho):
                profile_rows.append(
                    {
                        "truth_cell": cell,
                        "truth_rho": rho,
                        "truth_eta": 0.5,
                        "block_index": 0,
                        "bank_variant": "full",
                        "eta": eta,
                        "rho": profile_rho,
                        "expanded_log_likelihood": (
                            log_likelihood if profile_rho == rho else log_likelihood - 1.0
                        ),
                        "expanded_cutoff": 6.0,
                    }
                )
        funnel_rows.append(
            {
                "representation": "current_composite_statistic",
                "method": "profiled_sitewise_composite",
                "rho": rho,
                "final_auc": 0.95,
                "false_positive_rate": 0.05,
                "power": 0.9,
                "power_lower": 0.85,
                "practically_useful": True,
                "null_count": 100,
                "alternative_count": 100,
            }
        )
    _write_csv(goal012 / "validation_results.csv", validation_rows)
    _write_csv(goal012 / "truth_cell_summary.csv", cell_summary_rows)
    _write_csv(goal012 / "representative_profiles.csv", profile_rows)
    _write_csv(goal016 / "funnel_performance.csv", funnel_rows)
    goal016.mkdir(parents=True, exist_ok=True)
    (goal016 / "summary.json").write_text(
        json.dumps({"outcome": "information_retained_support_target_limited"}),
        encoding="utf-8",
    )
    return goal012, goal016


def test_reconciliation_keeps_paired_and_independent_decisions_distinct(tmp_path: Path) -> None:
    goal012, goal016 = _write_evidence(tmp_path)

    result = analyze_evidence(goal012, goal016)

    full = [row for row in result.decision_summaries if row.bank_variant == "full"]
    assert len(full) == 3
    assert full[0].validation_count == 2
    assert full[0].mle_exact_rate == 0.5
    assert full[0].mle_nonzero_rate == 1.0
    assert full[0].support_excludes_zero_rate == 0.5
    assert full[0].binary_power == 0.9
    assert full[0].campaign_relationship == "independent_campaign_level_comparison"
    paired = [row for row in result.paired_disagreements if row.bank_variant == "full"]
    assert paired[0].mle_exact_support_includes_zero_count == 1
    assert paired[0].mle_inexact_support_excludes_zero_count == 1
    assert result.outcome == "continuous_support_conservative_relative_to_detection"


def test_representative_profile_reports_why_zero_remains_supported(tmp_path: Path) -> None:
    goal012, goal016 = _write_evidence(tmp_path)

    result = analyze_evidence(goal012, goal016)

    profile = result.profile_mechanics[0]
    assert profile.fitted_eta == 0.5
    assert profile.profiled_zero_lr == 8.0
    assert profile.calibrated_cutoff == 6.0
    assert profile.zero_exclusion_margin == 2.0
    assert profile.zero_in_support is False
    assert profile.profile_log_score_eta_0_5_minus_eta_0 == 4.0
    assert profile.rho_fixed_minus_profiled_zero_lr == 0.0


def test_reconciliation_rejects_missing_scientific_columns(tmp_path: Path) -> None:
    goal012, goal016 = _write_evidence(tmp_path)
    (goal016 / "funnel_performance.csv").write_text("rho,power\n0.5,0.9\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"funnel_performance.csv.*missing columns"):
        analyze_evidence(goal012, goal016)


def test_goal017_writes_the_compact_review_surface(tmp_path: Path) -> None:
    goal012, goal016 = _write_evidence(tmp_path)
    result = analyze_evidence(goal012, goal016)
    output = tmp_path / "review"

    written = write_review_bundle(result, output)

    assert {path.relative_to(output).as_posix() for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["outcome"] == "continuous_support_conservative_relative_to_detection"
    assert summary["campaigns_are_wave_paired"] is False
    review = (output / "review.md").read_text(encoding="utf-8")
    assert "independent campaigns" in review
    assert "different scientific questions" in review
