"""Meaningful forecast-rule failures, independent of the four realized truths."""

import importlib.util
import math
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "score_capstone_truth", Path(__file__).parents[1] / "scripts/score_capstone_truth.py"
)
assert SPEC is not None and SPEC.loader is not None
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)


def test_positive_truth_is_a_miss_with_log_errors():
    truth = {
        "index": 0,
        "effect": 3.0,
        "h_null": False,
        "background": "exact",
        "beta": 0.0,
        "mean_hazard": 0.004,
        "detection_sd": 0.3,
    }
    row = SCORER.score_case(truth, SCORER.FORECASTS[0], 2.0, 0.4)
    assert not row["effect_class_hit"]
    assert row["forecast_abs_log_h_error"] == pytest.approx(math.log(3))
    assert row["adjusted_abs_log_h_error"] == pytest.approx(math.log(1.5))
    assert row["beta_abs_error_if_exact"] == 0.25


def test_inapplicable_beta_and_separate_sd_set():
    truth = {
        "index": 1,
        "effect": 1.0,
        "h_null": True,
        "background": "B100-A",
        "beta": None,
        "mean_hazard": 0.0016,
        "detection_sd": 0.1,
    }
    row = SCORER.score_case(truth, SCORER.FORECASTS[1], 1.0, 1.0)
    assert not row["background_hit"]
    assert row["beta_abs_error_if_exact"] is None
    assert not row["detection_sd_grid_hit"] and row["detection_sd_set_hit"]
    assert row["detection_sd_abs_error"] == pytest.approx(0.1)
    assert not row["mu_grid_hit"]


def test_archive_commitment_checked_before_parsing(tmp_path):
    path = tmp_path / "wrong.tar"
    path.write_bytes(b"not even an archive")
    with pytest.raises(ValueError, match="commitment mismatch"):
        SCORER.load_truth(path)
