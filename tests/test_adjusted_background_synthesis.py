from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes.adjusted_background_replay import REPLAY_CELL_IDS
from latent_landscapes.adjusted_background_synthesis import (
    BETAS,
    EFFECTS,
    maximum_on_grid,
    profile_summary,
    synthesize,
)


def test_maximum_ties_choose_lowest_beta_then_h() -> None:
    surface = np.zeros((3, 3), dtype=np.float64)
    betas = np.asarray([-1.0, 0.0, 1.0])
    effects = np.asarray([1.0, 2.0, 3.0])
    fit = maximum_on_grid(surface, betas, effects)
    assert (fit.beta, fit.h, fit.beta_index, fit.h_index) == (-1.0, 1.0, 0, 0)


def test_profile_summary_reports_disconnected_uncalibrated_regions() -> None:
    grid = np.arange(6.0)
    profile = np.asarray([0.0, -0.1, -2.0, -0.2, 0.0, -2.0])
    result = profile_summary(profile, grid, limit=0.25)
    assert result.components == ((0.0, 1.0), (4.0, 4.0))
    assert result.touches_lower
    assert result.touches_upper is False


def _synthetic_evidence(path: Path) -> None:
    shape = (24, len(BETAS), len(EFFECTS))
    latent_training = np.empty(shape, dtype=np.float64)
    oracle_training = np.empty_like(latent_training)
    latent_holdout = np.empty_like(latent_training)
    oracle_holdout = np.empty_like(latent_training)
    beta_mesh, h_mesh = np.meshgrid(BETAS, EFFECTS, indexing="ij")
    for history in range(24):
        target_beta = 0.0 if history == 0 else 0.4
        target_h = 6.0 if history == 0 else 3.0
        surface = -((beta_mesh - target_beta) ** 2 + ((h_mesh - target_h) / 2.0) ** 2)
        if history == 0:
            # Equal maxima test: beta=0,h=6 is preferred to beta=.05,h=6 and
            # h=6.05 because the registered order is beta, then h.
            surface[40, 100] = 0.0
            surface[41, 100] = 0.0
            surface[40, 101] = 0.0
        latent_training[history] = surface
        oracle_training[history] = surface + 0.1
        latent_holdout[history] = surface
        oracle_holdout[history] = surface + 0.2
    # Make the fitted adjusted-vs-null held-out contrast mechanically visible.
    latent_holdout[0, 40, 100] = 3.0
    latent_holdout[0, 40, 0] = 1.0
    oracle_holdout[0, 40, 100] = 4.0
    oracle_holdout[0, 40, 0] = 1.0
    site_a = np.linspace(-1.0, 1.0, 160)
    training_mask = np.zeros(160, dtype=bool)
    training_mask[:120] = True
    arrival = np.full((24, 160), 20.0)
    extirpation = np.full((24, 160), 40.0)
    np.savez(
        path,
        effects=EFFECTS,
        betas=BETAS,
        cell_ids=np.asarray([cell for _ in range(6) for cell in REPLAY_CELL_IDS]),
        replicate_indices=np.repeat(np.arange(6), 4),
        truth_h=np.asarray([1.0, 3.0, 1.0, 3.0] * 6),
        latent_training=latent_training,
        latent_holdout_joint=latent_holdout,
        oracle_training=oracle_training,
        oracle_holdout=oracle_holdout,
        site_A=site_a,
        training_mask=training_mask,
        true_arrival=arrival,
        true_extirpation=extirpation,
    )


def test_synthesize_reports_nested_maxima_holdout_and_geometry(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.npz"
    output = tmp_path / "synthesis"
    _synthetic_evidence(evidence)
    summary = synthesize(evidence, output)
    assert summary["status"] == "complete_descriptive_uncalibrated_geometry"
    assert summary["geometry_included"]
    assert "95% intervals" in summary["uncalibrated_boundary"]
    assert "fit_edge_contact_counts" in summary
    predictions = summary["prediction_descriptives"]
    assert len(predictions["p2_aligned_null_h1_minus_baseline_h3_adjusted_null_lr_by_block"]) == 6
    assert "p3_h_profile_lr_le_2_narrower_oracle_than_latent_count" in predictions

    with (output / "metrics.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    first = rows[0]
    assert first["cell_id"] == "B_h1"
    assert float(first["fit_beta"]) == pytest.approx(0.0)
    assert float(first["fit_h"]) == pytest.approx(6.0)
    assert float(first["holdout_adjusted_minus_fitted_adjustednull_conditional_prey"]) > 0.0
    assert "oracle_fit_h" in first
    assert (output / "primary_paired_comparison.png").is_file()
    assert (output / "joint_contours_latent.pdf").is_file()
    assert (output / "joint_contours_oracle.png").is_file()
    assert (output / "geometry_summary.csv").is_file()

    with (output / "geometry_summary.csv").open(newline="", encoding="utf-8") as handle:
        geometry_rows = list(csv.DictReader(handle))
    assert int(geometry_rows[0]["training_alive_before_arrival_site_count"]) == 120
    assert int(geometry_rows[0]["holdout_alive_before_arrival_site_count"]) == 40

    loaded_summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert loaded_summary["input_sha256"] == summary["input_sha256"]
