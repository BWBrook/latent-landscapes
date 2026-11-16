from __future__ import annotations

import copy
import importlib
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.spatial_family_reporting import closed_positive_family
from latent_landscapes.spatial_profile import (
    LAPLACE_FLOOR,
    SpatialProfileCriterion,
    SpatialProfileData,
)


def endpoint(
    family: str,
    value: float,
    *,
    h: float = 3.0,
    free: bool = False,
    eligible: bool = True,
) -> dict[str, Any]:
    parameters = {"alpha": -1.0, "beta": 0.1, "detection_sd": 0.2}
    if family == "positive_sigma":
        parameters["log_sigma"] = math.log(0.01)
    if free:
        parameters["log_h"] = math.log(h)
    return {
        "family": family,
        "criterion": value,
        "eligible": eligible,
        "h": h,
        "parameters": parameters,
        "source": family + "_fit",
    }


@pytest.mark.parametrize("positive,zero,boundary", [(-10.0, -9.0, True), (-8.0, -9.0, False)])
def test_report_closes_boundary_and_preserves_raw_rows(
    positive: float, zero: float, boundary: bool
) -> None:
    rows = endpoint("positive_sigma", positive), endpoint("sigma_zero", zero)
    original = copy.deepcopy(rows)
    report = closed_positive_family(*rows)
    assert rows == original
    assert report["criterion"] == max(positive, zero)
    assert report["boundary_supremum"] == boundary
    assert report["selected_component"] == (
        "sigma_zero_boundary" if boundary else "positive_endpoint"
    )
    assert report["sigma"] == (0.0 if boundary else math.exp(rows[0]["parameters"]["log_sigma"]))
    assert report["parameters"]["sigma"] == report["sigma"]
    assert "log_sigma" not in report["parameters"]
    assert report["eligible"] is True


def test_equal_endpoints_retain_positive_endpoint() -> None:
    report = closed_positive_family(endpoint("positive_sigma", -9.0), endpoint("sigma_zero", -9.0))
    assert not report["boundary_supremum"]
    assert report["sigma"] > 0.0


def test_free_closure_reports_sigma_zero_optimum_at_its_own_h() -> None:
    positive, zero = endpoint("positive_sigma", -10.0, free=True), endpoint(
        "sigma_zero", -9.0, h=5.0, free=True
    )
    with pytest.raises(ValueError, match="identical h"):
        closed_positive_family(positive, zero)
    report = closed_positive_family(positive, zero, free=True)
    assert report["h"] == 5.0
    assert report["parameters"]["log_h"] == math.log(5.0)
    assert report["sigma"] == 0.0


@pytest.mark.parametrize("bad_family", ["positive_sigma", "sigma_zero"])
def test_boundary_does_not_replace_an_ineligible_required_endpoint(bad_family: str) -> None:
    rows = [endpoint("positive_sigma", -10.0), endpoint("sigma_zero", -9.0)]
    next(row for row in rows if row["family"] == bad_family)["eligible"] = False
    with pytest.raises(ValueError, match="both eligible"):
        closed_positive_family(*rows)


def test_selection_retains_raw_guard_and_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    qualification = importlib.import_module("qualify_spatial_profiles")
    rows = [endpoint("positive_sigma", -10.0), endpoint("sigma_zero", -8.0)]
    fit = qualification.select_candidate_rows(rows)
    assert fit["positive_sigma"]["criterion"] == -10.0
    assert fit["sigma_zero"]["criterion"] == -8.0
    assert fit["criterion"] == -8.0
    assert fit["positive_sigma_closed"]["criterion"] == -8.0
    np.testing.assert_array_equal(
        qualification.parameters(fit["positive_sigma"]),
        [-1.0, 0.1, math.log(0.01), 0.2],
    )
    unresolved = endpoint("positive_sigma", -9.0, eligible=False)
    with pytest.raises(RuntimeError, match="unresolved candidate exceeds"):
        qualification.select_candidate_rows([*rows, unresolved])
    with pytest.raises(RuntimeError, match="unresolved variance family"):
        qualification.select_candidate_rows([rows[1]])


def test_positive_criterion_has_sigma_squared_limit_at_zero() -> None:
    count = 3
    ids = tuple(f"site-{i}" for i in range(count))
    bank = likelihood.compress_bank(np.zeros((3, count)), ids)
    observed = likelihood.prepare_observations(
        np.zeros((1, count, 13), dtype=np.int64),
        np.zeros((1, count, 6), dtype=np.int64),
        ids,
        np.ones(count, dtype=bool),
    )
    covariance = np.full((count, count), 0.2) + 0.8 * np.eye(count)
    data = SpatialProfileData(bank, observed, np.arange(count, dtype=float), covariance)
    weights = np.array([1.0, 1.5, 2.0])

    def evaluate(eta: np.ndarray) -> tuple[np.ndarray, ...]:
        difference = eta + 1.0
        return (
            -0.5 * weights * difference**2,
            -weights * difference,
            -weights,
            np.zeros(count),
        )

    evaluator = SimpleNamespace(numerical_domain=(-math.inf, math.inf), evaluate=evaluate)
    criterion = SpatialProfileCriterion(data, evaluator_factory=lambda h, sd: evaluator)
    zero = criterion.evaluate_sigma_zero(np.array([-1.0, 0.0, 0.2]), fixed_h=3.0)
    assert zero.success
    sigmas = np.array([1e-2, 1e-3, 1e-4])
    gaps = []
    for sigma in sigmas:
        positive = criterion.evaluate_positive(
            np.array([-1.0, 0.0, math.log(sigma), 0.2]), fixed_h=3.0
        )
        assert positive.success and positive.mode is not None
        assert positive.mode.success
        gap = zero.criterion - positive.criterion
        root = np.linalg.cholesky(covariance)
        eigenvalues = np.linalg.eigvalsh(
            np.eye(count) + sigma**2 * root.T @ (weights[:, None] * root)
        )
        normalizer = 1 + LAPLACE_FLOOR * math.exp(-1 / LAPLACE_FLOOR)
        floored = (
            eigenvalues + LAPLACE_FLOOR * np.exp(-eigenvalues / LAPLACE_FLOOR)
        ) / normalizer
        expected = 0.5 * np.log(floored).sum()
        assert gap == pytest.approx(expected, abs=2e-15)
        gaps.append(gap)
    assert gaps[0] > gaps[1] > gaps[2] > 0.0
    floor_slope_at_one = (1 - math.exp(-1 / LAPLACE_FLOOR)) / normalizer
    np.testing.assert_allclose(
        np.asarray(gaps) / sigmas**2, floor_slope_at_one * weights.sum() / 2, rtol=1e-4
    )
