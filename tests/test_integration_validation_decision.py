"""Decision-scale tests independent of arrival integration computations."""

import importlib.util
from pathlib import Path

import numpy as np

SPEC = importlib.util.spec_from_file_location(
    "integration_decision", Path(__file__).parents[1] / "scripts/check_integration_validation.py"
)
assert SPEC is not None and SPEC.loader is not None
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def test_calibration_rank_and_disconnected_support_are_preserved():
    effects = np.linspace(1, 10, 181)
    cal = np.tile(np.arange(250), (2, 1))
    drops = np.full((2, 250, 181), 300.0)
    drops[:, :, :4] = 0
    drops[:, :, 10:12] = 0
    result = checker.width_summary(cal, drops, effects)
    np.testing.assert_array_equal(result["cutoff"], [238, 238])
    np.testing.assert_array_equal(result["components"], np.full((2, 250), 2))
    assert result["mean_width_contrast"] == 0
    changed = drops.copy()
    changed[0, 0, 4:10] = 0
    comparison = checker.compare_width(result, checker.width_summary(cal, changed, effects))
    assert comparison["failed"] == ["component_changes"]


def test_coverage_contrast_cannot_hide_opposing_design_changes():
    effects = np.linspace(1, 10, 181)
    cal = np.ones((2, 250))
    drops = np.zeros((2, 250, 181))
    drops[1, 0, 0] = 2
    changed = drops.copy()
    changed[0, 0, 0] = 2
    changed[1, 0, 0] = 0
    result = checker.compare_width(
        checker.width_summary(cal, drops, effects), checker.width_summary(cal, changed, effects)
    )
    assert result["movement"]["coverage_count"] == 1
    assert result["movement"]["coverage_contrast_count"] == 2
    assert "coverage_contrast_count" in result["failed"]


def test_generating_rho_tail_has_its_own_gate_outside_core():
    rhos = np.array([1.0, 1.05, 1.07, 1.09, 1.11, 1.13, 1.15, 1.17])
    effects = np.array([1.0, 1.05, 1.10])
    surface = np.tile(
        np.array([-100.0, -9.0, -3.0, -1.0, 0.0, -1.0, -3.0, -9.0])[None, :, None], (3, 1, 3)
    )
    surface[:, :, 0] -= 1
    surface[:, :, 2] -= 1
    changed = surface.copy()
    changed[:, 0] -= 0.3
    left = checker.tail_summary(surface, rhos, effects)
    right = checker.tail_summary(changed, rhos, effects)
    assert not left["window_inconclusive"].any()
    result = checker.compare_tail(left, right)
    for case in result["cases"]:
        assert case["failed"] == ["generating_rho_lr"]
        assert np.isclose(case["movement"]["generating_rho_lr"], 0.6)
        assert case["movement"]["rho_core_lr"] == 0


def test_each_profile_is_centred_at_its_own_maximum():
    rhos = np.array([1.0, 1.05, 1.07, 1.09, 1.11, 1.13, 1.15, 1.17])
    effects = np.array([1.0, 1.05])
    surface = np.tile(
        np.array([-100.0, -9.0, -3.0, -1.0, 0.0, -1.0, -3.0, -9.0])[None, :, None], (3, 1, 2)
    )
    result = checker.compare_tail(
        checker.tail_summary(surface, rhos, effects),
        checker.tail_summary(surface + 1234.0, rhos, effects),
    )
    assert result["passed"]


def test_tied_window_edge_is_inconclusive_even_if_argmax_is_interior():
    rhos = np.arange(8, dtype=float) + 1
    surface = np.full((3, 8, 2), -10.0)
    surface[:, 4, 0] = 0
    surface[:, 7, 0] = 0
    result = checker.tail_summary(surface, rhos, np.array([1.0, 1.05]))
    assert result["window_inconclusive"].all()


def test_decision_refuses_failed_replay_or_unbound_arrays(tmp_path):
    import hashlib
    import json

    import pytest

    arrays = tmp_path / "arrays.npz"
    np.savez(arrays, sentinel=np.arange(3))
    report = tmp_path / "report.json"
    receipt = dict(
        completion_status="complete",
        technical_replay_max_abs={
            f"{kind}_{bank}": 0.0
            for kind in ("connected", "corridor")
            for bank in ("half0", "combined")
        },
        arrays_sha256=hashlib.sha256(arrays.read_bytes()).hexdigest(),
        array_keys=["sentinel"],
    )
    report.write_text(json.dumps(receipt))
    checker.verify_run(arrays, report)
    receipt["technical_replay_max_abs"]["connected_half0"] = 1e-8
    report.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="replay"):
        checker.verify_run(arrays, report)
    receipt["technical_replay_max_abs"]["connected_half0"] = 0.0
    receipt["arrays_sha256"] = "0" * 64
    report.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="bind"):
        checker.verify_run(arrays, report)
