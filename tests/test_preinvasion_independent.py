from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from latent_landscapes import adjusted_background_likelihood as adjusted
from latent_landscapes import preinvasion_likelihood as production
from latent_landscapes.preinvasion_independent import independent_pre_log_likelihood


def _one_site_observations(
    first_seven: tuple[int, ...], *, initial_alive: bool = True
) -> production.PreInvasionObservations:
    prey = np.zeros((1, 1, 13), dtype=np.int64)
    prey[0, 0, :7] = first_seven
    predator = np.zeros((1, 1, 6), dtype=np.int64)
    return production.prepare_observations(
        prey,
        predator,
        ("site",),
        (True,),
        initial_alive=(initial_alive,),
    )


def _score(
    counts: tuple[int, ...],
    *,
    mu: float,
    detection_sd: float = 0.0,
    initial_alive: bool = True,
) -> float:
    result = independent_pre_log_likelihood(
        _one_site_observations(counts, initial_alive=initial_alive),
        np.asarray([0.0]),
        np.asarray([0.0]),
        beta=0.0,
        mu=mu,
        detection_sd=detection_sd,
    )
    return float(result[0])


def test_sd_zero_manual_survival_and_loss_mixture() -> None:
    mu = 0.01
    p = 0.65

    # A detection count of two at every occasion rules out every loss path.
    observed_survival = _score((2, 2, 2, 2, 2, 2, 2), mu=mu)
    expected_survival = -mu * 60.0 + 14.0 * math.log(p)
    assert observed_survival == pytest.approx(expected_survival, abs=1e-13)

    # With all-zero counts, each possible loss interval remains observationally
    # compatible and has its own number of ordinary Bernoulli failures.
    survival = [math.exp(-mu * 10.0 * index) for index in range(7)]
    probability = math.fsum(
        (survival[prefix - 1] - survival[prefix]) * (1.0 - p) ** (2 * prefix)
        for prefix in range(1, 7)
    )
    probability += survival[-1] * (1.0 - p) ** 14
    assert _score((0, 0, 0, 0, 0, 0, 0), mu=mu) == pytest.approx(
        math.log(probability), abs=1e-13
    )


def test_persistent_beta_emission_matches_beta_function_identity() -> None:
    mu = 0.004
    p = 0.65
    sd = 0.2
    concentration = p * (1.0 - p) / sd**2 - 1.0
    alpha = p * concentration
    beta = (1.0 - p) * concentration
    log_moment = (
        math.lgamma(alpha + 14)
        + math.lgamma(alpha + beta)
        - math.lgamma(alpha)
        - math.lgamma(alpha + beta + 14)
    )
    expected = -mu * 60.0 + log_moment
    observed = _score((2, 2, 2, 2, 2, 2, 2), mu=mu, detection_sd=sd)
    assert observed == pytest.approx(expected, abs=1e-13)

    # The same expression must approach, rather than numerically diverge from,
    # fixed detection when the fitted SD is positive but very near its bound.
    near_zero = _score((2, 2, 2, 2, 2, 2, 2), mu=mu, detection_sd=2e-8)
    fixed = _score((2, 2, 2, 2, 2, 2, 2), mu=mu, detection_sd=0.0)
    assert near_zero == pytest.approx(fixed, abs=1e-12)


def test_whole_map_normalization_is_site_specific_and_initial_state_is_respected() -> None:
    counts = np.full((1, 2, 13), 2, dtype=np.int64)
    predator = np.zeros((1, 2, 6), dtype=np.int64)
    observations = production.prepare_observations(
        counts,
        predator,
        ("low", "high"),
        (True, True),
    )
    whole_map = np.asarray([-1.0, 0.0, 1.0])
    site_a = np.asarray([-1.0, 1.0])
    mu = 0.002
    beta = 0.7
    normalizer = float(np.mean(np.exp(beta * whole_map)))
    hazards = mu * np.exp(beta * site_a) / normalizer
    site_scores = independent_pre_log_likelihood(
        observations,
        whole_map,
        site_a,
        beta=beta,
        mu=mu,
        detection_sd=0.0,
        return_site=True,
    )
    np.testing.assert_allclose(
        site_scores[0], -60.0 * hazards + 14.0 * math.log(0.65), rtol=0, atol=2e-13
    )

    assert _score((0, 0, 0, 0, 0, 0, 0), mu=mu, initial_alive=False) == 0.0
    assert math.isinf(_score((1, 0, 0, 0, 0, 0, 0), mu=mu, initial_alive=False))


def test_independent_evaluator_does_not_call_production_scoring_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise AssertionError("production likelihood helper was called")

    monkeypatch.setattr(production, "pre_only_log_likelihood", forbidden)
    monkeypatch.setattr(production, "_prey_emissions", forbidden)
    monkeypatch.setattr(adjusted, "normalized_hazards", forbidden)
    assert math.isfinite(_score((2, 1, 1, 2, 1, 1, 2), mu=0.002, detection_sd=0.2))


def test_frozen_boundary_and_interior_fixtures_match_at_true_and_fitted_points() -> None:
    repository = Path(__file__).resolve().parents[1]
    panel = repository / "artifacts/goal056_execution/panel/panel/observations.npz"
    results = repository / "artifacts/goal056_execution/panel/results"
    with np.load(panel, allow_pickle=False) as values:
        site_ids = values["site_ids"]
        order = np.argsort(site_ids, kind="stable")
        observations = production.prepare_observations(
            values["prey_counts"],
            values["predator_counts"],
            site_ids,
            values["site_splits"] == "training",
        )
        map_a = values["map_a"]
        site_a = values["site_a"][order]

    # Cell 6 has true and fitted SD=0; cell 7 has true and fitted interior SD.
    fixtures = (
        (6, {"beta": 0.6, "mu": 0.0025, "detection_sd": 0.0}, -847.7320835011633),
        (7, {"beta": 0.6, "mu": 0.0025, "detection_sd": 0.2}, -753.5844712187836),
    )
    for index, truth, frozen_true_score in fixtures:
        fitted = json.loads((results / f"cell-{index:02d}-main.json").read_text())["pre_only"]
        fitted_parameters = {
            name: float(fitted[name]) for name in ("beta", "mu", "detection_sd")
        }
        for parameters, frozen_score in (
            (truth, frozen_true_score),
            (fitted_parameters, float(fitted["raw_logjoint"])),
        ):
            independent = independent_pre_log_likelihood(
                observations,
                map_a,
                site_a,
                beta=parameters["beta"],
                mu=parameters["mu"],
                detection_sd=parameters["detection_sd"],
            )[index]
            hazards = adjusted.normalized_hazards(
                parameters["beta"], map_a, site_a, parameters["mu"]
            )
            production_score = production.pre_only_log_likelihood(
                observations,
                hazards,
                detection_sd=parameters["detection_sd"],
                return_site=False,
            )[index]
            assert independent == pytest.approx(production_score, rel=0, abs=1e-8)
            assert independent == pytest.approx(frozen_score, rel=0, abs=1e-8)
