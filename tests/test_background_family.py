from __future__ import annotations

import math

import numpy as np
import pytest

from latent_landscapes import background_family as bf
from latent_landscapes.arc3_landscapes import build_landscape
from latent_landscapes.development_challenge_data import build_general_site_setup
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.monitoring_design import build_master_monitoring_design
from latent_landscapes.preinvasion_campaign import OpenTruth, loss_times


@pytest.fixture(scope="module")
def world() -> tuple[FixedInputs, object, bf.FamilySurfaces]:
    landscape = build_landscape("connected", 12345)
    master = build_master_monitoring_design(
        landscape,
        sampling_seed=1,
        holdout_seed=2,
        arm_seed=3,
        map_seed=12345,
        solver_time_limit=30,
    )
    fixed = FixedInputs(landscape, master.sampling, {})
    setup = build_general_site_setup(fixed)
    return fixed, setup, bf.signal_window_surface(landscape, setup)


def test_map_mean_hazard_equals_mu(world: tuple[FixedInputs, object, bf.FamilySurfaces]) -> None:
    _, setup, surfaces = world
    g = setup.field_sampler.sample(np.random.default_rng(5))  # type: ignore[attr-defined]
    for name in bf.BACKGROUNDS:
        lam = bf.background_hazard_map(setup, surfaces, name, g, 0.004)  # type: ignore[arg-type]
        assert lam[setup.accepted_mask].mean() == pytest.approx(0.004, rel=1e-12)  # type: ignore[attr-defined]
    flat = bf.background_hazard_map(setup, surfaces, "constant", g, 0.004)  # type: ignore[arg-type]
    assert np.ptp(flat) == 0.0


def test_matched_exposure_is_exposure_only(
    world: tuple[FixedInputs, object, bf.FamilySurfaces],
) -> None:
    _, setup, surfaces = world
    g = setup.field_sampler.sample(np.random.default_rng(6))  # type: ignore[attr-defined]
    a = setup.exposure_score  # type: ignore[attr-defined]
    lam = bf.background_hazard_map(setup, surfaces, "matched_exposure", g, 0.001)  # type: ignore[arg-type]
    expected = np.exp(bf.LOG_SCALE * 0.7 * a)
    expected = 0.001 * expected / expected.mean()
    assert np.allclose(lam, expected, rtol=1e-12)


def test_signal_surface_orthogonal_unit_sd(
    world: tuple[FixedInputs, object, bf.FamilySurfaces],
) -> None:
    _, setup, surfaces = world
    mask = setup.accepted_mask  # type: ignore[attr-defined]
    t = surfaces.signal[mask]
    assert abs(t.mean()) < 1e-10
    assert t.std(ddof=0) == pytest.approx(1.0, abs=1e-12)
    assert abs(np.mean(t * setup.exposure_score[mask])) < 1e-10  # type: ignore[attr-defined]
    assert 0.0 < surfaces.diagnostics["window_prevalence"] < 1.0


@pytest.mark.parametrize("effect", [1.0, 3.0, 10.0])
def test_trend_with_zero_gamma_equals_loss_times(effect: float) -> None:
    rng = np.random.default_rng(0)
    n = 400
    arrivals = rng.uniform(0, 120, n)
    arrivals[:20] = 0.0
    arrivals[20:40] = np.inf
    hazards = rng.uniform(5e-4, 8e-3, n)
    thresholds = rng.exponential(size=n)
    expected = loss_times(arrivals, hazards, effect, thresholds)
    got = bf.loss_times_trend(arrivals, hazards, effect, thresholds, 0.0)
    assert np.allclose(got, expected, rtol=0, atol=1e-9)
    # an arrival before day -60 acts from the start (the legacy function rejects it)
    early = np.array([-100.0, -60.0])
    pair = bf.loss_times_trend(early, np.full(2, 0.002), effect, np.ones(2), 0.0)
    assert pair[0] == pytest.approx(pair[1], abs=1e-12)
    assert pair[0] == pytest.approx(-60.0 + 1.0 / (0.002 * effect), abs=1e-9)


def test_trend_matches_numerical_cumulative_hazard() -> None:
    gamma = bf.TREND_GAMMA
    assert math.exp(gamma * 120) == pytest.approx(1.5)
    arrival, lam, h = 10.0, 0.003, 3.0
    for threshold in (0.05, 0.3, 1.0, 4.0):
        t = bf.loss_times_trend(
            np.array([arrival]), np.array([lam]), h, np.array([threshold]), gamma
        )[0]
        grid = np.linspace(-60.0, t, 400001)
        rate = lam * np.exp(gamma * grid) * np.where(grid >= arrival, h, 1.0)
        cumulative = float(np.sum((rate[1:] + rate[:-1]) / 2 * np.diff(grid)))
        assert cumulative == pytest.approx(threshold, rel=1e-4)


def test_pairing_and_reproducibility(
    world: tuple[FixedInputs, object, bf.FamilySurfaces],
) -> None:
    fixed, setup, surfaces = world
    seeds = {"streams": bf.family_stream_seeds((2026110501, 9, 1, 0))}
    truth = OpenTruth(0, 3.0, 0.004, 0.0, 0.2)
    results = {
        name: bf.generate_family_history(fixed, setup, truth, seeds, name, surfaces)  # type: ignore[arg-type]
        for name in ("constant", "b100_anchor", "window_high", "temporal_trend")
    }
    base_obs, base_ev = results["b100_anchor"]
    for name, (obs, ev) in results.items():
        assert np.array_equal(ev["arrival"], base_ev["arrival"])
        assert np.array_equal(ev["g_sites"], base_ev["g_sites"])
        assert np.array_equal(ev["site_detection"], base_ev["site_detection"])
        assert ev["background"] == name
        assert obs["prey_counts"].shape == base_obs["prey_counts"].shape
    assert results["temporal_trend"][1]["trend_gamma"] == bf.TREND_GAMMA
    assert np.array_equal(results["temporal_trend"][1]["site_hazard"], base_ev["site_hazard"])
    assert not np.array_equal(base_ev["site_hazard"], results["window_high"][1]["site_hazard"])
    again = bf.generate_family_history(fixed, setup, truth, seeds, "b100_anchor", surfaces)  # type: ignore[arg-type]
    assert again[0]["opaque_id"] == base_obs["opaque_id"]
    other = {"streams": bf.family_stream_seeds((2026110501, 9, 1, 1))}
    assert (
        bf.generate_family_history(fixed, setup, truth, other, "b100_anchor", surfaces)[  # type: ignore[arg-type]
            0
        ]["opaque_id"]
        != base_obs["opaque_id"]
    )
