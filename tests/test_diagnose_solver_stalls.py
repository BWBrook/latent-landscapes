import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from diagnose_solver_stalls import curvature_at, derivative_sweep, trace_trust_region

from latent_landscapes.spatial_profile import CriterionEvaluation, SpatialProfileCriterion


def quadratic(x):
    x = np.asarray(x)
    criterion = -0.5 * float(x @ x)
    return CriterionEvaluation(
        criterion, -criterion, -x, x, True, "ok", True, None, x.copy(), 1.0, 0.2
    )


def test_observer_preserves_actual_solver_trajectory_and_captures_rejected_steps(tmp_path):
    solver = object.__new__(SpatialProfileCriterion)
    bounds = [(-10.0, 10.0)] * 2

    def inconsistent(x):
        return replace(quadratic(x), criterion_gradient=np.array([1.0, 0.0]))

    start = np.array([0.0, 0.0])
    plain = solver._trust_region(inconsistent, start, bounds, maxiter=30, gradient_tolerance=1e-4)
    before = sys.gettrace()
    traced = trace_trust_region(
        solver,
        inconsistent,
        start,
        bounds,
        maxiter=30,
        gradient_tolerance=1e-4,
        trace_path=tmp_path / "trace.jsonl",
    )
    assert sys.gettrace() is before
    np.testing.assert_array_equal(plain[0], traced[0])
    assert plain[1].criterion == traced[1].criterion
    np.testing.assert_array_equal(plain[2].x, traced[2].x)
    for key in ("success", "message", "nit", "nfev"):
        assert plain[2][key] == traced[2][key]
    trials = [r for r in traced[3] if r["event"] == "trial"]
    assert trials and all(r["ratio"] < 0 for r in trials)
    assert traced[2].message == "trust region collapsed"
    assert any(r["event"] == "curvature" for r in traced[3])
    assert len((tmp_path / "trace.jsonl").read_text().splitlines()) == len(traced[3])


def test_free_curvature_gain_uses_unshifted_free_set():
    solver = object.__new__(SpatialProfileCriterion)
    report = curvature_at(solver, quadratic, np.array([1.0, 2.0]), [(-10, 10)] * 2)
    np.testing.assert_allclose(report["curvature"], np.eye(2), atol=1e-9)
    assert report["predicted_remaining_gain"] == pytest.approx(2.5)
    assert report["gain_status"] == "local_quadratic_prediction"

    def saddle(x):
        return replace(quadratic(x), criterion_gradient=np.asarray(x))

    assert (
        curvature_at(solver, saddle, np.ones(2), [(-10, 10)] * 2)["gain_status"]
        == "infinite_unavailable"
    )


def test_sweep_marks_bound_crossings_unavailable_without_clipping():
    solver = object.__new__(SpatialProfileCriterion)
    report = derivative_sweep(
        solver,
        quadratic,
        np.array([0.0, 0.3]),
        [(0, 1), (0, 1)],
        last_rejected_step=np.array([3e-10, 4e-10]),
    )
    first = report["rows"][0]
    assert first["minus"]["status"] == "out_of_bounds"
    assert "central_difference" not in first
    assert first["plus"]["one_sided"] == pytest.approx(-0.05)
    vector = next(
        r["vector"] for r in report["rows"] if r["direction"] == "last_rejected_step_unit"
    )
    np.testing.assert_allclose(vector, [0.6, 0.8])
    assert len(report["rows"]) == 27


def test_sweep_reports_gradient_mismatch_and_actual_mode_jump():
    solver = object.__new__(SpatialProfileCriterion)

    def switched(x):
        value = quadratic(x)
        mode = SimpleNamespace(u=np.array([float(x[0] > 0)]), score_inf=0, success=True)
        return replace(value, criterion_gradient=-np.asarray(x) + 1, mode=mode)

    report = derivative_sweep(solver, switched, np.zeros(1), [(-1, 1)])
    assert report["rows"][0]["central_minus_gradient"] == pytest.approx(-1)
    assert report["rows"][0]["plus"]["mode_jump_l2"] == 1
    assert report["rows"][0]["minus"]["mode_jump_l2"] == 0
