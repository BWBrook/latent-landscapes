from __future__ import annotations

import importlib.util
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from scipy.special import betaln  # type: ignore[import-untyped]

from latent_landscapes import log_domain_likelihood as raw
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.capstone_qualification import subset_observations
from latent_landscapes.differentiable_likelihood import (
    LikelihoodDomainError,
    prepare_site_likelihood,
)
from latent_landscapes.preinvasion_execution import subset_observations as execution_subset
from latent_landscapes.spatial_profile import SpatialProfileCriterion, SpatialProfileData


def fixture() -> tuple[likelihood.PreInvasionObservations, likelihood.CompressedBank]:
    prey = np.asarray(
        [
            [
                [2, 1, 2, 1, 0, 1, 2, 2, 1, 0, 0, 0, 0],
                [0, 2, 1, 2, 1, 2, 1, 1, 0, 1, 0, 0, 0],
                [2, 0, 1, 1, 2, 1, 0, 0, 0, 0, 0, 0, 0],
            ]
        ],
        dtype=np.int64,
    )
    predator = np.asarray(
        [[[0, 1, 0, 2, 1, 0], [1, 0, 2, 1, 0, 2], [0, 0, 1, 0, 0, 1]]],
        dtype=np.int64,
    )
    observed = np.ones_like(prey, dtype=bool)
    observed[:, :, :7] = False
    predator_observed = np.ones_like(predator, dtype=bool)
    predator_observed[:, 1] = False
    data = likelihood.prepare_observations(
        prey,
        predator,
        ("c", "a", "b"),
        [True, True, True],
        prey_observed=observed,
        predator_observed=predator_observed,
    )
    arrivals = np.random.default_rng(906).uniform(0, 80, (83, 3))
    arrivals[:4] = [[0, 10, 20], [10, 60, 70], [60, 0, 10], [5, 25, 55]]
    return data, likelihood.compress_bank(arrivals, data.site_ids)


def sliced(data: likelihood.PreInvasionObservations) -> likelihood.PreInvasionObservations:
    return likelihood.prepare_observations(
        data.prey_counts[:, :, 7:],
        data.predator_counts,
        data.site_ids,
        data.training_mask,
        prey_times=data.prey_times[7:],
        cohort_start=data.cohort_start,
        initial_alive=data.initial_alive,
        predator_observed=data.predator_observed,
    )


@pytest.mark.parametrize("h", [1.0, 3.0, 30.0])
@pytest.mark.parametrize("sd", [0.0, 0.17, 0.35])
@pytest.mark.parametrize("eta", [(-6.0, -5.4, -5.1), (-4.8, -4.5, -4.2)])
def test_masked_calendar_matches_sliced_raw_and_derivatives(
    h: float,
    sd: float,
    eta: tuple[float, ...],
) -> None:
    observed, bank = fixture()
    post_only = sliced(observed)
    point = np.asarray(eta)
    fast = prepare_site_likelihood(observed, bank, h, detection_sd=sd)
    slow = prepare_site_likelihood(post_only, bank, h, detection_sd=sd)
    result = fast.evaluate(point)
    reference = raw.exact_log_scores(
        post_only,
        bank,
        [h],
        np.exp(point),
        detection_sd=sd,
    )
    full_raw = raw.exact_log_scores(
        observed,
        bank,
        [h],
        np.exp(point),
        detection_sd=sd,
    )
    np.testing.assert_allclose(result[0], reference.joint_loglikelihood[0, 0], atol=3e-12)
    np.testing.assert_allclose(
        full_raw.joint_loglikelihood, reference.joint_loglikelihood, rtol=0, atol=3e-12
    )
    for actual, expected in zip(result, slow.evaluate(point), strict=True):
        np.testing.assert_allclose(actual, expected, rtol=2e-11, atol=2e-11)
    assert fast.stats["last_series_site_count"] == 3
    assert slow.stats["last_exact_site_count"] == 3
    integration = likelihood.build_integration(bank, [h], np.exp(point))
    probability = likelihood.score_observations(observed, integration, detection_sd=sd)
    np.testing.assert_allclose(
        probability.joint_loglikelihood, reference.joint_loglikelihood, rtol=0, atol=3e-12
    )


@pytest.mark.parametrize("sd", [0.0, 0.2])
def test_masked_counts_are_irrelevant_and_all_missing_prey_is_neutral(sd: float) -> None:
    observed, bank = fixture()
    changed = observed.prey_counts.copy()
    changed[:, :, :7] = (changed[:, :, :7] + 1) % 3
    altered = replace(observed, prey_counts=changed)
    eta = np.asarray((-5.1, -5.4, -5.7))
    for data in (observed, altered):
        result = prepare_site_likelihood(data, bank, 3, detection_sd=sd).evaluate(eta)
        if data is observed:
            expected = result
        else:
            for actual, reference in zip(result, expected, strict=True):
                np.testing.assert_array_equal(actual, reference)
    unavailable = replace(observed, prey_observed=np.zeros_like(observed.prey_counts, dtype=bool))
    score = raw.exact_log_scores(unavailable, bank, [1, 3, 30], np.exp(eta), detection_sd=sd)
    np.testing.assert_allclose(score.conditional_prey_loglikelihood, 0, rtol=0, atol=2e-15)
    np.testing.assert_allclose(
        likelihood.pre_only_log_likelihood(
            unavailable, np.exp(eta), detection_sd=sd, return_site=True
        ),
        0,
        atol=3e-16,
    )
    dead = replace(unavailable, initial_alive=np.zeros(3, dtype=bool))
    dead_score = raw.exact_log_scores(dead, bank, [3], np.exp(eta), detection_sd=sd)
    np.testing.assert_allclose(dead_score.conditional_prey_loglikelihood, 0, atol=2e-15)


def test_masked_emissions_use_observed_trial_counts_for_shared_beta() -> None:
    counts = np.asarray([[[2, 1, 0, 2, 0], [1, 2, 1, 0, 0]]])
    mask = np.asarray([[[False, True, False, False, True], [True, False, True, False, False]]])
    p, sd = 0.65, 0.2
    kappa = p * (1 - p) / sd**2 - 1
    event, alive = likelihood._prey_emissions(counts, p, sd, mask)
    log_event, log_alive = raw._log_prey_emissions(counts, p, sd, mask)
    for site in range(2):
        for prefix in range(6):
            observed = counts[0, site, :prefix][mask[0, site, :prefix]]
            possible = not np.any(counts[0, site, prefix:][mask[0, site, prefix:]])
            if prefix == 5:
                possible = True
            successes = int(observed.sum())
            trials = 2 * len(observed)
            expected_log = (
                (
                    sum(math.log(math.comb(2, int(k))) for k in observed)
                    + betaln(p * kappa + successes, (1 - p) * kappa + trials - successes)
                    - betaln(p * kappa, (1 - p) * kappa)
                )
                if possible
                else -math.inf
            )
            actual_log = log_alive[0, site] if prefix == 5 else log_event[0, site, prefix]
            actual = alive[0, site] if prefix == 5 else event[0, site, prefix]
            assert actual_log == pytest.approx(expected_log, abs=2e-14)
            assert actual == pytest.approx(math.exp(expected_log), abs=2e-15)


def test_masked_derivatives_match_finite_differences() -> None:
    observed, bank = fixture()
    evaluator = prepare_site_likelihood(observed, bank, 30, detection_sd=0.17)
    eta = np.asarray((-5.1, -5.4, -5.7))
    baseline = evaluator.evaluate(eta)
    step = 2e-4
    for site in range(3):
        plus, minus = eta.copy(), eta.copy()
        plus[site] += step
        minus[site] -= step
        positive, negative = evaluator.evaluate(plus), evaluator.evaluate(minus)
        numerical = [(positive[k][site] - negative[k][site]) / (2 * step) for k in range(3)]
        np.testing.assert_allclose(
            np.asarray(baseline[1:])[:, site], numerical, rtol=2e-6, atol=2e-7
        )


def test_all_observed_default_and_explicit_mask_agree() -> None:
    observed, bank = fixture()
    default = replace(observed, prey_observed=None)
    explicit = replace(observed, prey_observed=np.ones_like(observed.prey_counts, dtype=bool))
    for sd in [0, 0.2]:
        for data in (default, explicit):
            score = raw.exact_log_scores(data, bank, [1, 3, 30], np.full(3, 0.004), detection_sd=sd)
            if data is default:
                expected = score.joint_loglikelihood
            else:
                np.testing.assert_array_equal(score.joint_loglikelihood, expected)


def test_spatial_cached_probability_path_respects_mask() -> None:
    observed, bank = fixture()
    data = SpatialProfileData(bank, observed, np.asarray((-0.5, 0, 0.5)), np.eye(3))
    criterion = SpatialProfileCriterion(data)
    points = np.asarray((-6.0, -5.0, -4.5))
    integrations = [likelihood.build_integration(bank, [3], np.full(3, np.exp(x))) for x in points]
    values = criterion._score_integrations(integrations, 0.17)
    evaluator = prepare_site_likelihood(observed, bank, 3, detection_sd=0.17)
    reference = np.column_stack([evaluator.evaluate(np.full(3, x))[0] for x in points])
    np.testing.assert_allclose(values, reference, rtol=0, atol=3e-12)


def test_masks_sort_subset_load_and_remain_separate(tmp_path: Path) -> None:
    observed, _ = fixture()
    prey = np.concatenate([observed.prey_counts, observed.prey_counts], axis=0)
    predator = np.concatenate([observed.predator_counts, observed.predator_counts], axis=0)
    availability = np.ones_like(prey, dtype=bool)
    availability[0, :, :7] = False
    availability[1, 0, :9] = False
    availability[1, 1, :3] = False
    availability[1, 2, 3:8] = False
    predator_mask = np.ones_like(predator, dtype=bool)
    predator_mask[:, 2] = False
    path = tmp_path / "observations.npz"
    order = np.asarray([2, 0, 1])
    np.savez(
        path,
        site_ids=np.asarray(observed.site_ids)[order],
        prey_counts=prey[:, order],
        predator_counts=predator[:, order],
        prey_observed=availability[:, order],
        predator_observed=predator_mask[:, order],
        training_mask=np.ones(3, dtype=bool),
    )
    script = Path(__file__).resolve().parents[1] / "scripts/benchmark_spatial_profile.py"
    spec = importlib.util.spec_from_file_location("benchmark_mask_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    loaded, _ = module.load_observations(
        path, public={"site_ids": np.asarray(observed.site_ids)}, history=1
    )
    np.testing.assert_array_equal(loaded.prey_observed, availability[1:2])
    np.testing.assert_array_equal(loaded.predator_observed, predator_mask[1:2])
    assert not loaded.prey_observed.flags.writeable
    selected = subset_observations(loaded, [False, True, True], history=0)
    np.testing.assert_array_equal(selected.prey_observed, availability[1:2, 1:])
    np.testing.assert_array_equal(selected.predator_observed, predator_mask[1:2, 1:])
    legacy_subset = execution_subset(loaded, np.asarray([False, True, True], dtype=bool), history=0)
    np.testing.assert_array_equal(legacy_subset.prey_observed, selected.prey_observed)
    np.testing.assert_array_equal(legacy_subset.predator_observed, selected.predator_observed)
    with pytest.raises(ValueError, match="prey_observed"):
        replace(loaded, prey_observed=np.ones_like(loaded.prey_counts, dtype=int))
    with pytest.raises(ValueError, match="prey_observed"):
        replace(loaded, prey_observed=np.ones((1, 3, 2), dtype=bool))


@pytest.mark.parametrize("h", [1.0, 3.0, 30.0])
@pytest.mark.parametrize("sd", [0.0, 0.2])
@pytest.mark.parametrize("chunk_size", [1, 4, 32])
def test_batch_values_match_scalar_and_raw_with_mixed_domains(
    h: float, sd: float, chunk_size: int
) -> None:
    observed, bank = fixture()
    points = np.asarray([[-6, -5, -4], [-3, -2, -1], [-7, -3, -4], [-2, -8, -0.5]])
    evaluator = prepare_site_likelihood(observed, bank, h, detection_sd=sd)
    values = evaluator.log_values(points, chunk_size=chunk_size)
    expected = np.asarray([evaluator.evaluate(point)[0] for point in points])
    np.testing.assert_allclose(values, expected, rtol=0, atol=2e-13)
    for point, value in zip(points, values, strict=True):
        reference = raw.exact_log_scores(
            observed, bank, [h], np.exp(point), detection_sd=sd
        )
        np.testing.assert_allclose(value, reference.joint_loglikelihood[0, 0], atol=2e-13)
    if h == 30:
        assert evaluator.stats["batch_series_site_evaluations"] > 0
        assert evaluator.stats["batch_exact_site_evaluations"] > 0


def test_batch_raw_chunks_sparse_calendar_and_mask_neutrality() -> None:
    observed, _ = fixture()
    arrivals = np.random.default_rng(96).uniform(0, 80, (8200, 3))
    bank = likelihood.compress_bank(arrivals, observed.site_ids)
    post_only = sliced(observed)
    points = np.asarray([[-6, -5, -4], [-3, -2, -1], [-7, -3, -4]])
    masked = prepare_site_likelihood(observed, bank, 30, detection_sd=0.17)
    sparse = prepare_site_likelihood(post_only, bank, 30, detection_sd=0.17)
    np.testing.assert_allclose(
        masked.log_values(points, chunk_size=2),
        sparse.log_values(points, chunk_size=2),
        rtol=0,
        atol=2e-13,
    )
    for point, value in zip(points, sparse.log_values(points), strict=True):
        np.testing.assert_allclose(value, sparse.evaluate(point)[0], rtol=0, atol=2e-13)
    unavailable = replace(observed, prey_observed=np.zeros_like(observed.prey_counts, dtype=bool))
    for alive in [np.ones(3, dtype=bool), np.zeros(3, dtype=bool)]:
        data = replace(unavailable, initial_alive=alive)
        evaluator = prepare_site_likelihood(data, bank, 30, detection_sd=0.17)
        values = evaluator.log_values(points)
        np.testing.assert_allclose(values, np.broadcast_to(values[0], values.shape), atol=3e-14)
        for point in points:
            np.testing.assert_allclose(np.asarray(evaluator.evaluate(point)[1:]), 0, atol=5e-12)


def test_batch_values_preserve_scalar_cache_and_validate_domain() -> None:
    observed, bank = fixture()
    bank = replace(bank, bank_arrivals=np.empty((0, 3), dtype=np.float64))
    evaluator = prepare_site_likelihood(observed, bank, 30)
    point = np.full(3, evaluator.numerical_domain[1] - 0.1)
    expected = evaluator.evaluate(point)
    evaluator.log_values(np.asarray([point + 0.01, point - 0.01]))
    assert evaluator.evaluate(point) is expected
    assert evaluator.log_values(np.empty((0, 3))).shape == (0, 3)
    with pytest.raises(LikelihoodDomainError, match="without raw arrivals"):
        evaluator.log_values(np.asarray([point + 0.2]))
    with pytest.raises(LikelihoodDomainError, match="nonfinite site hazard"):
        evaluator.log_values(np.full((1, 3), 1000.0))
    for invalid in [np.zeros(3), np.zeros((2, 2)), np.full((1, 3), math.nan)]:
        with pytest.raises(ValueError, match="eta_batch"):
            evaluator.log_values(invalid)
    for chunk in [0, -1, True]:
        with pytest.raises(ValueError, match="chunk_size"):
            evaluator.log_values(np.asarray([point]), chunk_size=chunk)
