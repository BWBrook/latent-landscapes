from __future__ import annotations

import math
from dataclasses import replace
from typing import cast

import numpy as np
import pytest
from scipy.optimize import OptimizeResult  # type: ignore[import-untyped]

import latent_landscapes.preinvasion_fitting as fitting
from latent_landscapes.preinvasion_fitting import (
    BETA_BOUNDS,
    DETECTION_SD_BOUNDS,
    H_BOUNDS,
    MU_BOUNDS,
    fit_four_models,
    fit_pre_only_nuisance,
    paired_fit,
    profile_beta,
    profile_h,
    score_heldout,
)


def _quadratic(data: object, *, h: float, beta: float, mu: float, detection_sd: float) -> float:
    target = data if isinstance(data, dict) else {}
    target_h = cast(float, target.get("h", 3.0))
    target_beta = cast(float, target.get("beta", 0.4))
    target_mu = cast(float, target.get("mu", 0.003))
    target_sd = cast(float, target.get("detection_sd", 0.1))
    deviations = (
        (h - target_h) / 2.0,
        beta - target_beta,
        (mu - target_mu) / 0.001,
        (detection_sd - target_sd) / 0.1,
    )
    return -sum(value**2 for value in deviations)


def _boundary_quadratic(
    data: object, *, h: float, beta: float, mu: float, detection_sd: float
) -> float:
    del data, beta, mu, detection_sd
    return -((h - H_BOUNDS[1]) ** 2)


def _zero_sd_quadratic(
    data: object, *, h: float, beta: float, mu: float, detection_sd: float
) -> float:
    del data, h, beta, mu
    return -((detection_sd / 0.1) ** 2)


def _two_mode_quadratic(
    data: object, *, h: float, beta: float, mu: float, detection_sd: float
) -> float:
    del data
    return (
        -min((h - 2.0) ** 2, (h - 8.0) ** 2)
        - beta**2
        - ((mu - 0.002) / 0.001) ** 2
        - detection_sd**2
    )


def test_four_fits_recover_interior_and_nested_statistics_are_nonnegative() -> None:
    fits = fit_four_models({}, _quadratic)

    assert fits["adjusted_free_h"].h == pytest.approx(3.0, abs=2e-5)
    assert fits["adjusted_free_h"].beta == pytest.approx(0.4, abs=2e-5)
    assert fits["adjusted_free_h"].mu == pytest.approx(0.003, abs=2e-8)
    assert fits["adjusted_free_h"].detection_sd == pytest.approx(0.1, abs=2e-6)
    assert fits["constant_free_h"].beta == 0.0
    assert fits["constant_h1"].h == 1.0
    assert fits["adjusted_h1"].h == 1.0
    assert fits["adjusted_free_h"].raw_logjoint >= fits["adjusted_h1"].raw_logjoint
    assert fits["constant_free_h"].raw_logjoint >= fits["constant_h1"].raw_logjoint

    result = paired_fit({}, _quadratic)
    assert result.T >= 0.0
    assert result.constant_T >= 0.0
    assert set(result.fits) == {
        "constant_free_h",
        "adjusted_free_h",
        "constant_h1",
        "adjusted_h1",
    }


def test_boundary_and_zero_sd_are_explicitly_retained() -> None:
    boundary = fit_four_models({}, _boundary_quadratic)["adjusted_free_h"]
    zero_sd = fit_four_models({}, _zero_sd_quadratic)["adjusted_free_h"]

    assert boundary.h == pytest.approx(H_BOUNDS[1], abs=1e-5)
    assert "h_upper" in boundary.boundary_flags
    assert zero_sd.detection_sd == pytest.approx(DETECTION_SD_BOUNDS[0], abs=1e-8)
    assert "detection_sd_lower" in zero_sd.boundary_flags


def test_fit_and_profiles_are_reproducible_and_profiles_keep_analytic_values() -> None:
    first = fit_four_models({}, _quadratic)
    second = fit_four_models({}, _quadratic)
    assert [
        (key, first[key].parameters, first[key].raw_logjoint) for key in first
    ] == pytest.approx([(key, second[key].parameters, second[key].raw_logjoint) for key in second])

    h_profile = profile_h({}, _quadratic, first["adjusted_free_h"], grid=np.linspace(1, 5, 9))
    assert h_profile.values[4] == pytest.approx(0.0, abs=2e-8)
    assert h_profile.parameters[4]["h"] == pytest.approx(3.0)
    assert h_profile.curvature is not None and h_profile.curvature < 0.0

    beta_profile = profile_beta(
        {}, _quadratic, first["adjusted_free_h"], grid=np.linspace(-2, 2, 21)
    )
    assert beta_profile.values[12] == pytest.approx(0.0, abs=2e-8)
    assert beta_profile.parameters[12]["beta"] == pytest.approx(0.4, abs=1e-12)


def test_pre_only_fit_and_callback_never_receive_holdout_or_truth() -> None:
    seen: list[object] = []

    def training(data: object, **parameters: float) -> float:
        seen.append(data)
        assert "truth" not in parameters
        return -(
            (parameters["beta"] - 0.5) ** 2
            + ((parameters["mu"] - 0.0025) / 0.001) ** 2
            + ((parameters["detection_sd"] - 0.0) / 0.1) ** 2
        )

    pre = fit_pre_only_nuisance({"pre": True}, training)
    assert pre.beta == pytest.approx(0.5, abs=2e-5)
    assert pre.mu == pytest.approx(0.0025, abs=2e-8)
    assert pre.detection_sd == pytest.approx(0.0, abs=1e-8)
    assert all(value == {"pre": True} for value in seen)

    fits = fit_four_models({"training": True}, _quadratic)
    holdout_seen: list[object] = []

    def heldout(data: object, **parameters: float) -> float:
        holdout_seen.append(data)
        assert math.isfinite(parameters["h"])
        return -1.0

    scores = score_heldout(fits, {"holdout": True}, heldout, site_count=2)
    assert set(scores) == set(fits)
    assert all(score.score_per_site == pytest.approx(-0.5) for score in scores.values())
    assert holdout_seen and all(value == {"holdout": True} for value in holdout_seen)


def test_parameter_bounds_are_the_documented_domains() -> None:
    assert H_BOUNDS == (1.0, 10.0)
    assert BETA_BOUNDS == (-2.0, 2.0)
    assert MU_BOUNDS == (0.0005, 0.006)
    assert DETECTION_SD_BOUNDS == (0.0, 0.4)


def test_failed_best_optimizer_is_not_reported_as_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_minimize(objective: object, x0: object, **kwargs: object) -> OptimizeResult:
        del objective, kwargs
        return OptimizeResult(
            x=np.asarray(x0, dtype=float),
            fun=-1.0,
            success=False,
            status=1,
            message="forced failure",
            nfev=1,
        )

    monkeypatch.setattr(fitting, "minimize", failed_minimize)
    result = fitting.fit_model({}, _quadratic, "adjusted_free_h")

    assert result.numerical_status == "failed_optimizer"
    assert not result.converged
    assert any(not start.success for start in result.starts)


def test_multimodal_starts_are_retained_and_reproducible() -> None:
    first = fitting.fit_model({}, _two_mode_quadratic, "adjusted_free_h")
    second = fitting.fit_model({}, _two_mode_quadratic, "adjusted_free_h")
    local_h = {round(start.final_parameters["h"], 6) for start in first.starts}

    assert {2.0, 8.0}.issubset(local_h)
    assert first.parameters == pytest.approx(second.parameters)
    assert first.raw_logjoint == pytest.approx(second.raw_logjoint)
    assert first.objective_gap >= 0.0


def test_profile_seed_repairs_one_ulp_bound_spill_and_rejects_real_violation() -> None:
    seed = {
        "h": math.nextafter(H_BOUNDS[1], math.inf),
        "beta": 0.0,
        "mu": 0.002,
        "detection_sd": 0.1,
    }
    spec = fitting._FreeSpec(("logh", "logmu", "v"), {"beta": 0.0})

    starts = fitting._profile_starts(seed, None, spec)
    assert starts[0]["h"] == H_BOUNDS[1]
    continuation_fit = replace(
        fitting.fit_model({}, _quadratic, "adjusted_free_h"),
        h=seed["h"],
    )
    continuation = profile_beta({}, _quadratic, continuation_fit, grid=np.asarray([-2.0, 2.0]))
    assert len(continuation.statuses) == 2

    with pytest.raises(ValueError, match="initial h"):
        fitting._profile_starts({**seed, "h": H_BOUNDS[1] + 1e-5}, None, spec)
