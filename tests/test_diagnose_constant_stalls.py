from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from latent_landscapes.spatial_profile import CriterionEvaluation, SpatialProfileCriterion


@pytest.fixture
def diagnostic(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("diagnose_constant_stalls")


def quadratic_criterion() -> SpatialProfileCriterion:
    criterion = object.__new__(SpatialProfileCriterion)

    def evaluate(
        parameters: np.ndarray, fixed_h: float, *, nuisance_fd: bool
    ) -> CriterionEvaluation:
        target = np.array([-6.25, 0.0, 0.18])
        weights = np.array([4.0, 0.0, 2.0])
        displacement = parameters - target
        gradient = -weights * displacement
        value = float(-0.5 * np.dot(displacement, weights * displacement))
        return CriterionEvaluation(
            value,
            -value,
            gradient,
            -gradient,
            True,
            "ok",
            True,
            None,
            parameters.copy(),
            fixed_h,
            float(parameters[-1]),
        )

    criterion.evaluate_sigma_zero = evaluate  # type: ignore[method-assign]
    return criterion


def test_observed_constant_fit_preserves_the_actual_solver_result(
    diagnostic: Any, tmp_path: Path
) -> None:
    direct_criterion = quadratic_criterion()
    family = diagnostic.ReducedFamily("constant", direct_criterion, beta_free=False)
    direct = family._fit_constant(
        1.0,
        [diagnostic.DEFAULTS["sigma_zero"].copy()],
        "diagnostic_constant_first_h1",
        1e-4,
        120,
    )[0]
    expected = diagnostic.adapter._candidate_summary(direct, family_max=0.0, global_max=0.0)
    traced_criterion = quadratic_criterion()
    original_method = traced_criterion._trust_region
    result = diagnostic.trace_first_constant_fit(
        traced_criterion, trace_path=tmp_path / "trace.jsonl"
    )
    assert result["candidate"] == expected
    assert traced_criterion._trust_region == original_method
    np.testing.assert_array_equal(result["start_reduced"], [-5.5, 0.2])
    assert result["internal_gradient_tolerance"] == 1e-5
    assert result["eligibility_gradient_tolerance"] == 1e-4
    assert result["trace"][-1]["event"] == "return"
    assert any(row["event"] == "curvature" for row in result["trace"])
    assert len((tmp_path / "trace.jsonl").read_text().splitlines()) == len(result["trace"])
    assert result["grid"]["nodes_per_axis"] == 13


def test_grid_keeps_invalid_evaluations_without_optimizing(diagnostic: Any) -> None:
    calls = []

    def evaluate(point: np.ndarray) -> SimpleNamespace:
        calls.append(point.copy())
        return SimpleNamespace(
            success=point[1] < 1.0,
            criterion=-float(np.dot(point, point)),
            criterion_gradient=-2.0 * point,
            message="ok" if point[1] < 1.0 else "invalid endpoint",
        )

    result = diagnostic.criterion_grid(evaluate, [(-1.0, 1.0), (0.0, 1.0)], nodes=3)
    assert len(calls) == 9
    assert result["valid_count"] == 6
    assert result["invalid_count"] == 3
    np.testing.assert_array_equal(result["best_grid_point"]["parameters"], [0.0, 0.0])
    assert all(row["criterion"] is None for row in result["points"] if not row["valid"])


@pytest.mark.parametrize("endpoint_moved", [False, True])
def test_rejected_direction_is_used_only_at_its_own_endpoint(
    diagnostic: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, endpoint_moved: bool
) -> None:
    original_trace = diagnostic.observer.trace_trust_region
    captured = {}

    def trace(*args: Any, **kwargs: Any) -> Any:
        x, evaluation, result, rows = original_trace(*args, **kwargs)
        origin = x.copy()
        if endpoint_moved:
            origin[0] += 0.1
        rows.insert(
            -1,
            {"event": "trial", "ratio": 0.0, "x": origin, "iteration": 50, "step": [0.1, 0.0]},
        )
        return x, evaluation, result, rows

    def sweep(*args: Any, **kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {}

    monkeypatch.setattr(diagnostic.observer, "trace_trust_region", trace)
    monkeypatch.setattr(diagnostic.observer, "derivative_sweep", sweep)
    result = diagnostic.trace_first_constant_fit(
        quadratic_criterion(), trace_path=tmp_path / "trace.jsonl"
    )
    origin = result["last_rejected_origin"]
    assert origin["iteration"] == 50
    assert origin["same_as_swept_endpoint"] is not endpoint_moved
    assert origin["direction_used"] is not endpoint_moved
    if endpoint_moved:
        assert captured["last_rejected_step"] is None
        assert origin["status"] == "omitted_endpoint_moved"
    else:
        np.testing.assert_array_equal(captured["last_rejected_step"], [0.1, 0.0])
        assert origin["status"] == "attached_final_endpoint"


def test_frozen_source_is_verified_before_any_task_data_is_read(
    diagnostic: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def reject_source() -> None:
        raise ValueError("source differs")

    monkeypatch.setattr(diagnostic.observer, "verify_frozen_source", reject_source)
    with pytest.raises(ValueError, match="source differs"):
        diagnostic.run_task(tmp_path / "absent-task.json", tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_runner_rejects_unregistered_cases_before_opening_data(diagnostic: Any) -> None:
    with pytest.raises(ValueError, match="four prescribed"):
        diagnostic.task_inputs({"task": {"task_id": "fit-unregistered-dense"}})


def test_runner_rejects_a_changed_candidate_before_opening_data(diagnostic: Any) -> None:
    record = {
        "task": {
            "task_id": f"fit-{diagnostic.DATASETS[0]}-dense",
            "source_commit": "changed",
        }
    }
    with pytest.raises(ValueError, match="frozen rejected"):
        diagnostic.task_inputs(record)
