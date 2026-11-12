from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.spatial_profile import (
    DETECTION_SD_MAX,
    CriterionEvaluation,
    CurveDomainError,
    SpatialProfileCriterion,
    SpatialProfileData,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmark_spatial_profile as adapter


def bare_criterion(maxiter: int = 200) -> SpatialProfileCriterion:
    criterion = object.__new__(SpatialProfileCriterion)
    criterion._identity = np.eye(1)
    criterion.mode_tolerance = 1e-8
    criterion.decrement_tolerance = 1e-7
    criterion.mode_max_iterations = maxiter
    criterion.stats = {"mode_branch_calls": 0, "mode_branch_invalid_trial_rejections": 0}
    return criterion


class OversizedTrial:
    numerical_domain = (-math.inf, math.inf)

    def __init__(self, error_type: type[Exception] = FloatingPointError):
        self.error_type = error_type
        self.calls: list[np.ndarray] = []

    def evaluate(self, eta: np.ndarray) -> tuple[np.ndarray, ...]:
        self.calls.append(eta.copy())
        if np.any(np.abs(eta) > 2):
            raise self.error_type("invalid proposed trial")
        return (
            0.495 * eta**2 + 0.25 * eta - 0.25 * eta**4,
            0.99 * eta + 0.25 - eta**3,
            0.99 - 3 * eta**2,
            -6 * eta,
        )


@pytest.mark.parametrize("error_type", [CurveDomainError, FloatingPointError, ValueError])
def test_invalid_inner_trial_is_damped_then_strictly_converges(error_type):
    criterion = bare_criterion()
    evaluator = OversizedTrial(error_type)
    result = criterion._mode_branch(np.zeros(1), np.eye(1), evaluator, np.zeros(1))
    assert result.success and result.terminal_reason == "converged"
    assert result.invalid_trial_rejections > 0
    assert (
        criterion.stats["mode_branch_invalid_trial_rejections"] == result.invalid_trial_rejections
    )
    assert result.evaluations == len(evaluator.calls)
    assert result.iterations < criterion.mode_max_iterations
    assert result.score_inf <= 10 * criterion.mode_tolerance
    assert result.decrement <= criterion.decrement_tolerance
    assert criterion.stats["mode_eta_min"] == float(np.min(result.u))
    assert criterion.stats["mode_eta_max"] == float(np.max(result.u))
    assert any(np.max(np.abs(call)) > 2 for call in evaluator.calls)
    np.testing.assert_allclose(result.u**3 + 0.01 * result.u, [0.25], rtol=0, atol=1e-7)


class InvalidInitial:
    numerical_domain = (-math.inf, math.inf)

    def evaluate(self, eta):
        raise FloatingPointError("initial state unavailable")


def test_out_of_domain_inner_trials_count_as_invalid_without_evaluation():
    criterion = bare_criterion()
    evaluator = OversizedTrial()
    evaluator.numerical_domain = (-2.0, 2.0)
    result = criterion._mode_branch(np.zeros(1), np.eye(1), evaluator, np.zeros(1))
    assert result.success
    assert result.invalid_trial_rejections > 0
    assert all(np.max(np.abs(call)) < 2 for call in evaluator.calls)
    assert result.evaluations == len(evaluator.calls)
    assert result.evaluations + result.invalid_trial_rejections == result.iterations + 1
    assert (
        criterion.stats["mode_branch_invalid_trial_rejections"] == result.invalid_trial_rejections
    )


class InvalidEveryTrial:
    numerical_domain = (-math.inf, math.inf)

    def evaluate(self, eta):
        if np.any(eta != 0):
            raise FloatingPointError("all nonzero trials unavailable")
        return np.zeros(1), np.ones(1), np.zeros(1), np.zeros(1)


def test_terminal_reasons_and_invalid_trial_budget_are_distinct():
    solver = bare_criterion()
    initial = solver._mode_branch(np.zeros(1), np.eye(1), InvalidInitial(), np.zeros(1))
    assert initial.terminal_reason == "initial-invalid"
    assert initial.evaluations == 1 and initial.iterations == 0
    assert initial.invalid_trial_rejections == 0
    assert "mode_eta_min" not in solver.stats
    damping = solver._mode_branch(np.zeros(1), np.eye(1), InvalidEveryTrial(), np.zeros(1))
    assert damping.terminal_reason == "damping-limit"
    assert damping.invalid_trial_rejections > 1
    assert damping.iterations <= solver.mode_max_iterations
    assert "mode_eta_max" not in solver.stats
    limited = bare_criterion(1)._mode_branch(np.zeros(1), np.eye(1), OversizedTrial(), np.zeros(1))
    assert limited.terminal_reason == "iteration-limit"
    assert limited.iterations == limited.invalid_trial_rejections == 1
    assert not initial.success and not damping.success and not limited.success


def toy_evaluation(value, gradient):
    gradient = np.asarray(gradient, dtype=float)
    return CriterionEvaluation(
        float(value),
        -float(value),
        gradient,
        -gradient,
        True,
        "ok",
        True,
        None,
        np.zeros(len(gradient)),
        1.0,
        0.2,
    )


@pytest.mark.parametrize(
    "shape, residual, eligible", [(1, 5e-5, True), (-1, 5e-5, False), (1, 2e-4, False)]
)
def test_returned_stall_point_requires_gradient_and_unchanged_second_order(
    shape, residual, eligible
):
    def evaluate(x):
        return toy_evaluation(
            -0.5 * shape * x[0] ** 2 + residual * x[0], [-shape * x[0] + residual]
        )

    point, evaluation, result = bare_criterion()._trust_region(
        evaluate, np.zeros(1), [(-1, 1)], maxiter=0, gradient_tolerance=1e-4
    )
    assert evaluation.success
    assert bool(result.success) is eligible
    assert bool(result.second_order_passed) is eligible
    np.testing.assert_array_equal(point, [0])


def test_returned_point_is_certified_after_final_allowed_optimization_step():
    def evaluate(x):
        return toy_evaluation(-((x[0] - 0.5) ** 2), [-2 * (x[0] - 0.5)])

    _, _, result = bare_criterion()._trust_region(
        evaluate, np.zeros(1), [(-1, 1)], maxiter=1, gradient_tolerance=1e-4
    )
    assert result.success and result.second_order_passed
    assert "iteration limit" in result.message


def nuisance_criterion():
    criterion = bare_criterion()
    criterion.stats = dict(
        nuisance_site_evaluations=0,
        nuisance_site_seconds=0.0,
        nuisance_richardson_central=0,
        nuisance_richardson_one_sided=0,
    )
    calls = []

    def curves(h, detection_sd):
        assert 1 <= h <= 30
        assert 0 <= detection_sd < DETECTION_SD_MAX
        calls.append((h, detection_sd))

        class Polynomial:
            def evaluate(self, eta):
                value = np.full_like(eta, math.log(h) ** 3 + detection_sd**4)
                return value, 2 * value, -3 * value, np.zeros_like(value)

        return Polynomial()

    criterion.curves = curves
    return criterion, calls


def test_richardson_cancels_central_bias_in_both_nuisance_coordinates():
    criterion, calls = nuisance_criterion()
    point = np.array([-5.5, 0.1, math.log(0.5), 0.7, 0.2])
    rows = criterion._site_nuisance_derivatives(point, None, np.zeros(1), 1e-3, sigma_zero=False)
    for row, expected in zip(rows, (3 * 0.7**2, 4 * 0.2**3), strict=True):
        for values, multiple in zip(row[1:], (1, 2, -3), strict=True):
            np.testing.assert_allclose(values, [multiple * expected], atol=2e-12)
    assert len(calls) == criterion.stats["nuisance_site_evaluations"] == 8
    assert criterion.stats["nuisance_richardson_central"] == 2
    assert criterion.stats["nuisance_site_seconds"] >= 0


@pytest.mark.parametrize("at_upper", [False, True])
def test_boundary_richardson_uses_legal_second_order_base_stencils(at_upper):
    criterion, calls = nuisance_criterion()
    sd = DETECTION_SD_MAX * (1 - 1e-10) if at_upper else 0.0
    point = np.array([-5.5, 0.1, sd])
    row = criterion._site_nuisance_derivatives(point, 1.0, np.zeros(1), 1e-3, sigma_zero=True)[0]
    expected = 4 * sd**3 + (-1 if at_upper else 1) * 1e-9
    np.testing.assert_allclose(row[1], [expected], atol=1e-12)
    assert len(calls) == 4
    assert criterion.stats["nuisance_richardson_one_sided"] == 1


def test_near_boundary_keeps_coarse_stencil_orientation_at_the_half_step():
    criterion, calls = nuisance_criterion()
    point = np.array([-5.5, 0.1, math.log(0.5), 0.00075, 0.00075])
    rows = criterion._site_nuisance_derivatives(point, None, np.zeros(1), 1e-3, sigma_zero=False)
    np.testing.assert_allclose(rows[0][1], [3 * point[-2] ** 2], atol=1e-14)
    np.testing.assert_allclose(rows[1][1], [4 * point[-1] ** 3 + 1e-9], atol=1e-15)
    assert all(math.log(h) >= point[-2] - 1e-15 and sd >= point[-1] for h, sd in calls)
    assert criterion.stats["nuisance_richardson_one_sided"] == 2


def test_mode_call_diagnostics_and_histogram_are_serializable():
    ids = ("s0",)
    bank = likelihood.compress_bank(np.zeros((3, 1)), ids)
    observed = likelihood.prepare_observations(
        np.zeros((1, 1, 13), dtype=np.int64),
        np.zeros((1, 1, 6), dtype=np.int64),
        ids,
        np.ones(1, dtype=bool),
    )
    data = SpatialProfileData(bank, observed, np.zeros(1), np.eye(1))

    def builder(h: float, detection_sd: float, grid: np.ndarray) -> np.ndarray:
        return -np.exp(grid)[None, :]

    criterion = SpatialProfileCriterion(data, curve_builder=builder)
    evaluation = criterion.evaluate_positive(np.array([-5.5, 0, math.log(0.5), 0.2]), fixed_h=1)
    assert evaluation.success and evaluation.mode is not None
    assert evaluation.mode.inner_terminal_reason == "converged"
    assert criterion.stats["mode_termination_converged"] == 1
    assert criterion.stats["mode_branch_termination_converged"] == 1
    assert criterion.stats[f"mode_converged_iterations_{evaluation.mode.iterations}"] == 1
    assert criterion.stats["mode_invalid_trial_rejections"] == 0
    import json

    json.dumps(criterion.stats)
    candidate = adapter.FitCandidate(
        "positive_sigma", "test", evaluation.parameters, evaluation, True, "ok", 1, 1, 0.0, True
    )
    summary = adapter._candidate_summary(candidate, family_max=0, global_max=0)
    assert summary["mode"]["inner_terminal_reason"] == "converged"
    assert summary["mode"]["invalid_trial_rejections"] == 0
