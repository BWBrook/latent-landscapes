"""Runner checks use mechanical arrays, not the registered open panel seeds."""

from dataclasses import replace

import numpy as np
import pytest

from latent_landscapes import preinvasion_execution as execution
from latent_landscapes import preinvasion_likelihood as likelihood


def _data() -> execution.FitData:
    ids = ("a", "b", "c")
    observed = likelihood.prepare_observations(
        np.ones((2, 3, 13), dtype=int),
        np.ones((2, 3, 6), dtype=int),
        ids,
        np.asarray([True, True, False]),
    )
    bank = likelihood.compress_bank(np.asarray([[5.0, 15.0, 25.0], [45.0, 55.0, 65.0]]), ids)
    return execution.FitData(
        observed, bank, np.asarray([-1.0, 0.0, 1.0]), np.asarray([-1.0, 0.0, 1.0])
    )


def test_training_wrappers_exclude_changed_holdout() -> None:
    data = _data()
    counts = data.observations.prey_counts.copy()
    counts[:, 2] = 0
    changed = replace(
        data,
        observations=likelihood.prepare_observations(
            counts,
            data.observations.predator_counts,
            data.observations.site_ids,
            data.observations.training_mask,
        ),
    )
    parameters = dict(h=3.0, beta=0.6, mu=0.0016, detection_sd=0.2)
    assert execution.fit_loglikelihood(data, **parameters) == execution.fit_loglikelihood(
        changed, **parameters
    )
    parameters.pop("h")
    assert execution.pre_loglikelihood(data, **parameters) == execution.pre_loglikelihood(
        changed, **parameters
    )


def test_subsets_align_bank_and_observations_and_grid_bounds() -> None:
    data = _data()
    mask = data.observations.training_mask
    selected = execution.FitData(
        execution.subset_observations(data.observations, mask),
        execution.subset_bank(data.bank, mask),
        data.map_a,
        data.site_a[mask],
    )
    assert selected.observations.site_ids == selected.bank.site_ids == ("a", "b")
    grid = execution.coarse_grid_audit(selected)
    for model, points in grid["parameters"].items():
        for index, parameters in enumerate(points):
            single = replace(
                selected,
                observations=execution.subset_observations(
                    selected.observations, np.ones(2, bool), history=index
                ),
            )
            assert grid["max_logjoint"][model][index] == pytest.approx(
                execution.fit_loglikelihood(single, **parameters), abs=1e-12
            )
            if model.endswith("h1"):
                assert parameters["h"] == 1
            if model.startswith("constant"):
                assert parameters["beta"] == 0
