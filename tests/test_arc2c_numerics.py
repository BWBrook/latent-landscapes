from __future__ import annotations

import hashlib
import json
import runpy
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes.arc2c_campaign import run_campaign, write_campaign_bundle
from latent_landscapes.arc2c_design import TRUTHS, smoke_config

CANARY = runpy.run_path(str(Path(__file__).parents[1] / "scripts/check_arc2c_numerics.py"))


def test_profile_change_includes_new_support_and_refined_global_maximum() -> None:
    # The last node enters support only under the new calculation.
    old = np.asarray([0.0, -4.0, -20.0])
    new = np.asarray([0.0, -4.0, -1.0])
    assert CANARY["profile_change"](old, new) == 38.0
    # A midpoint improves the global maximum but is absent from the common nodes.
    assert CANARY["profile_change"](old, old, new_maximum=0.2) == pytest.approx(0.4)


def test_rho_refinement_keeps_separate_windows_and_all_original_rows() -> None:
    grid = np.exp2(np.arange(10, dtype=np.float64))
    old = np.full((2, 1, 10, 2), -100.0)
    doubled = old.copy()
    old[0, 0, 1] = 0.0
    old[1, 0, 8] = 0.0
    doubled[:] = old
    doubled[0, 0, 2] = 0.0
    fine = np.asarray(CANARY["refined_rho_grid"](grid, old, doubled, (float(grid[5]),)))
    # Support neighbours yield 0..3 and 7..9, plus the isolated generating node 5.
    original_indices = (0, 1, 2, 3, 5, 7, 8, 9)
    midpoint_left_indices = (0, 1, 2, 7, 8)
    expected = sorted(
        [float(grid[index]) for index in original_indices]
        + [float(np.sqrt(grid[index] * grid[index + 1])) for index in midpoint_left_indices]
    )
    np.testing.assert_array_equal(fine, expected)
    evaluated = np.full((2, 1, len(fine), 2), 5.0)
    merged_rhos, merged = CANARY["merge_midpoints"](grid, old, fine, evaluated)
    np.testing.assert_array_equal(merged[..., np.searchsorted(merged_rhos, grid), :], old)
    assert np.all(merged[..., ~np.isin(merged_rhos, grid), :] == 5.0)
    assert CANARY["rho_mle_within_original_interval"](grid, 1, grid[2])
    assert not CANARY["rho_mle_within_original_interval"](grid, 1, grid[3])


def test_reduced_canary_roundtrips_all_four_histories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = replace(
        smoke_config(), calibration_replicates=2, validation_replicates=2, calibration_rank=2
    )
    result = run_campaign(config, progress=None)
    source = tmp_path / "timing"
    write_campaign_bundle(replace(result, mode="timing"), source)
    output = tmp_path / "canary.json"
    main = CANARY["main"]
    monkeypatch.setitem(main.__globals__, "timing_config", lambda: config)
    monkeypatch.setattr(
        sys, "argv", ["canary", "--timing-dir", str(source), "--output", str(output)]
    )
    main()
    report = json.loads(output.read_text())
    assert len(report["conditions"]) == 24
    assert [
        (row["phase"], row["dataset_index"], row["condition_id"]) for row in report["conditions"]
    ] == [
        (phase, index, truth.condition_id)
        for phase in ("calibration", "validation")
        for index in range(2)
        for truth in TRUTHS
    ]
    path = output.with_suffix(".npz")
    assert report["canary_profile_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    with np.load(path, allow_pickle=False) as saved:
        np.testing.assert_array_equal(
            saved["phases"], ("calibration", "calibration", "validation", "validation")
        )
        np.testing.assert_array_equal(saved["dataset_indices"], (0, 1, 0, 1))
        for start, phase in ((0, "calibration"), (2, "validation")):
            np.testing.assert_array_equal(
                saved["current_joint"][start : start + 2],
                result.profiles[f"{phase}_train_joint"].swapaxes(0, 1),
            )
        assert saved["doubled_joint"].shape == saved["current_joint"].shape
        common = np.searchsorted(saved["refined_rhos"], saved["rhos"])
        np.testing.assert_array_equal(
            saved["refined_joint"][..., common, :], saved["current_joint"]
        )
