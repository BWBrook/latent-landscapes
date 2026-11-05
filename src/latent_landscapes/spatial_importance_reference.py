"""Fixed-outer importance targets for the sampled-site spatial criterion."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.linalg import cho_solve  # type: ignore[import-untyped]

from latent_landscapes.differentiable_likelihood import (
    DifferentiableSiteLikelihood,
    prepare_site_likelihood,
)
from latent_landscapes.importance_reference import Array, Proposal, defensive_proposal
from latent_landscapes.spatial_profile import SpatialProfileCriterion, SpatialProfileData


def direct_criterion(data: SpatialProfileData) -> SpatialProfileCriterion:
    return SpatialProfileCriterion(
        data,
        evaluator_factory=lambda h, sd: prepare_site_likelihood(
            data.observed, data.bank, h, detection_sd=sd
        ),
    )


@dataclass(frozen=True)
class SpatialTarget:
    evaluator: DifferentiableSiteLikelihood
    eta0: Array
    precision: Array
    log_normalizer: float
    proposal: Proposal
    laplace_criterion: float
    selected_mode: Array
    mode_diagnostics: tuple[dict[str, Any], ...]

    def __call__(self, u: Array) -> Array:
        ell = self.evaluator.log_values(u + self.eta0).sum(axis=1)
        quadratic = np.einsum("bi,ij,bj->b", u, self.precision, u, optimize=True)
        return np.asarray(ell - 0.5 * quadratic - self.log_normalizer)


def prepare_target(
    criterion: SpatialProfileCriterion,
    parameters: Array,
    *,
    h: float,
    warm: Array | None = None,
    expected_laplace: float | None = None,
) -> SpatialTarget:
    if parameters.shape != (4,) or not np.all(np.isfinite(parameters)):
        raise ValueError("fixed-h positive-family parameters must have four finite coordinates")
    alpha, beta, log_sigma, detection_sd = map(float, parameters)
    mode = criterion.mode(alpha, beta, log_sigma, h, detection_sd)
    if not mode.success or mode.precision is None or mode.hessian_inverse is None:
        raise RuntimeError(f"unresolved importance proposal mode: {mode.message}")
    curves = criterion.curves(h, detection_sd)
    if not isinstance(curves, DifferentiableSiteLikelihood):
        raise TypeError("importance target requires the direct site likelihood")
    eta0 = alpha + beta * criterion.data.exposure
    laplace = float(mode.value - 0.5 * mode.logdet_combined)
    if expected_laplace is not None and abs(laplace - expected_laplace) > 1e-4:
        raise RuntimeError("retained Laplace fit failed latent-mode replay")
    starts = [np.zeros(criterion.site_count)]
    if warm is not None and not np.array_equal(starts[0], warm):
        starts.append(warm)
    modes: list[tuple[Array, Array, float]] = []
    diagnostics = []
    for start in starts:
        branch = criterion._mode_branch(eta0, mode.precision, curves, start)
        if branch is None:
            raise RuntimeError("a deterministic importance proposal branch failed")
        u, value, score, step, decrement, iterations, evaluations, message = branch
        eta = eta0 + u
        _, _, curvature, _ = curves.evaluate(eta)
        hessian = mode.precision - np.diag(curvature)
        chol = np.linalg.cholesky(hessian)
        covariance = cho_solve((chol, True), np.eye(criterion.site_count))
        stationary = score <= criterion.mode_tolerance or (
            score <= 10 * criterion.mode_tolerance
            and step <= criterion.mode_tolerance * max(1.0, float(np.max(np.abs(u))))
            and decrement <= criterion.mode_tolerance
        )
        margin = criterion.proposal_guard_sd * np.sqrt(np.diag(covariance))
        domain = curves.numerical_domain
        supported = bool(np.all(eta - margin >= domain[0]) and np.all(eta + margin <= domain[1]))
        if not stationary or not supported:
            raise RuntimeError("importance proposal branch failed stationarity/support checks")
        duplicate = any(float((u - old[0]) @ hessian @ (u - old[0])) <= 1e-8 for old in modes)
        log_mass = float(value - np.log(np.diag(chol)).sum())
        diagnostics.append(
            {
                "score_inf": score,
                "newton_step_inf": step,
                "newton_decrement": decrement,
                "iterations": iterations,
                "evaluations": evaluations,
                "message": message,
                "duplicate": duplicate,
                "log_laplace_mass_without_common_normalizer": log_mass,
            }
        )
        if not duplicate:
            modes.append((np.asarray(u), np.asarray(covariance), log_mass))
    return SpatialTarget(
        curves,
        np.asarray(eta0),
        mode.precision,
        0.5 * (mode.logdet_c + criterion.site_count * math.log(2 * math.pi)),
        defensive_proposal(modes),
        laplace,
        mode.u,
        tuple(diagnostics),
    )
