from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from latent_landscapes.prospective_background_synthesis import (
    BETAS,
    CELL_IDS,
    EFFECTS,
    _bootstrap,
    _testing_metadata,
    expected_score_shapes,
    synthesize,
    validate_metadata,
)


def _fixture(directory: Path, blocks: int = 3) -> dict[str, np.ndarray]:
    metadata = _testing_metadata(blocks=blocks)
    n = blocks * 6
    oracle_n = blocks * 4
    beta_mesh, h_mesh = np.meshgrid(BETAS, EFFECTS, indexing="ij")
    latent_training = np.empty((n, len(BETAS), len(EFFECTS)))
    latent_holdout = np.empty_like(latent_training)
    oracle_training = np.empty((oracle_n, len(BETAS), len(EFFECTS)))
    oracle_holdout = np.empty_like(oracle_training)
    for history in range(n):
        target_beta = (
            float(metadata["truth_beta"][history])
            if np.isfinite(metadata["truth_beta"][history])
            else 0.0
        )
        target_h = 2.0 + (history % 3)
        surface = -((beta_mesh - target_beta) ** 2 + ((h_mesh - target_h) / 2.0) ** 2)
        latent_training[history] = surface
        latent_holdout[history] = surface
    # Make the first exact-null history a known-beta lookup and a non-zero error.
    latent_training[0] = -((beta_mesh - 0.0) ** 2 + ((h_mesh - 2.0) / 2.0) ** 2)
    # The first direct contrast is an exact tie; the second is an adjusted win.
    latent_holdout[0] = 0.0
    latent_holdout[1, 40, 100] = 2.0
    latent_holdout[1, 40, 0] = 1.0
    oracle_indices = metadata["oracle_history_indices"]
    oracle_training[:] = latent_training[oracle_indices]
    oracle_holdout[:] = latent_holdout[oracle_indices]
    directory.mkdir()
    np.savez(directory / "evidence.npz", **cast(dict[str, Any], metadata))
    np.save(directory / "latent_training.npy", latent_training)
    np.save(directory / "latent_holdout_joint.npy", latent_holdout)
    np.save(directory / "oracle_training.npy", oracle_training)
    np.save(directory / "oracle_holdout.npy", oracle_holdout)
    return metadata


def test_small_metadata_helper_validates_without_production_count() -> None:
    metadata = _testing_metadata(blocks=2)
    assert validate_metadata(metadata, strict=False)["history_count"] == 12
    with pytest.raises(ValueError, match="6,000"):
        validate_metadata(metadata, strict=True)
    assert expected_score_shapes(12)["oracle_training"] == (8, len(BETAS), len(EFFECTS))
    assert metadata["truth_h"][4] == 1.0
    assert np.isnan(metadata["truth_beta"][4])
    larger = _testing_metadata(blocks=251)
    assert validate_metadata(larger, strict=False)["oracle_count"] == 1000


def test_bootstrap_is_deterministic_and_keeps_ties_separate() -> None:
    rows = []
    for block in range(3):
        for cell in CELL_IDS:
            rows.append(
                {
                    "lane": "latent",
                    "block_index": block,
                    "cell_id": cell,
                    "abs_log_h_error_change_adjusted_minus_constant": float(block),
                    "direct_holdout_score_adjusted_minus_constant_per_site": 0.0,
                    "signed_log_h_error_adjusted": float(block),
                    "signed_log_h_error_constant": 0.0,
                    "point_error_1_5fold_adjusted": False,
                    "direct_score_preference": "tie",
                }
            )
    first, lookup_first = _bootstrap(rows, seed=17, draws=8)
    second, lookup_second = _bootstrap(rows, seed=17, draws=8)
    assert first == second
    assert lookup_first["E0_h1", "model_preference_tie"]["estimate"] == pytest.approx(1.0)
    for key in lookup_first:
        assert lookup_first[key].keys() == lookup_second[key].keys()
        for field in lookup_first[key]:
            if field == "_draws":
                np.testing.assert_array_equal(lookup_first[key][field], lookup_second[key][field])
            else:
                assert lookup_first[key][field] == lookup_second[key][field]


def test_synthesis_reports_known_beta_nonzero_error_truth_limit_and_outputs(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    metadata = _fixture(evidence)
    output = tmp_path / "synthesis"
    summary = synthesize(evidence, output, strict=False)
    assert summary["history_count"] == 18
    assert summary["oracle_history_count"] == 12
    assert (
        summary["fable_forecasts"]["exact_h3_free_vs_known_beta"]["E06_h3"]["forecast_target_ratio"]
        == 1.05
    )
    assert (
        "adjusted_h_gt_1_beta_below_truth_rate"
        in summary["fable_forecasts"]["exact_null_beta_balance"]["E06_h1"]
    )
    assert (
        "distance_from_forecast_mean_lower_bound"
        in summary["fable_forecasts"]["exact_E06_direct_score"]["E06_h1"]
    )
    assert summary["elapsed_seconds"] >= 0
    assert (output / "metrics.csv").is_file()
    assert (output / "oracle_metrics.csv").is_file()
    assert (output / "paired_contrasts.csv").is_file()
    assert (output / "model_preference.png").is_file()
    loaded = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert loaded["config_sha256"] == summary["config_sha256"]
    with (output / "metrics.csv").open(encoding="utf-8") as handle:
        header = handle.readline()
        first = handle.readline().strip().split(",")
    assert "known_beta_fit_h" in header
    assert len(first) > 10
    assert metadata["truth_h"][0] == 1.0


def test_completed_synthesis_refuses_overwrite(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    _fixture(evidence, blocks=1)
    output = tmp_path / "synthesis"
    synthesize(evidence, output, strict=False)
    with pytest.raises(ValueError, match="overwrite"):
        synthesize(evidence, output, strict=False)
