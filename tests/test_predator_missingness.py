from __future__ import annotations

import numpy as np
import pytest

from latent_landscapes import capstone_qualification
from latent_landscapes.preinvasion_likelihood import (
    DEFAULT_PREDATOR_TIMES,
    _predator_emissions,
    prepare_observations,
)


def _arrays() -> tuple[np.ndarray, np.ndarray, tuple[str, ...]]:
    prey = np.zeros((1, 3, 13), dtype=np.int64)
    predator = np.asarray(
        [[[0, 2, 1, 1, 0, 2], [2, 1, 0, 2, 1, 0], [0, 0, 0, 0, 0, 0]]],
        dtype=np.int64,
    )
    return prey, predator, ("site-z", "site-a", "site-m")


def test_default_and_explicit_all_observed_are_identical() -> None:
    prey, predator, ids = _arrays()
    default = prepare_observations(prey, predator, ids, [True, True, True])
    explicit = prepare_observations(
        prey,
        predator,
        ids,
        [True, True, True],
        predator_observed=np.ones_like(predator, dtype=bool),
    )
    np.testing.assert_array_equal(default.predator_counts, explicit.predator_counts)
    np.testing.assert_array_equal(default.predator_emissions, explicit.predator_emissions)
    assert default.predator_observed is None
    assert explicit.predator_observed is not None
    assert not explicit.predator_observed.flags.writeable


def test_all_missing_visits_are_neutral_and_placeholder_counts_do_not_matter() -> None:
    prey, predator, ids = _arrays()
    observed = np.zeros_like(predator, dtype=bool)
    first = prepare_observations(prey, predator, ids, [True] * 3, predator_observed=observed)
    changed_predator = predator.copy()
    changed_predator[~observed] = 2 - changed_predator[~observed]
    second = prepare_observations(
        prey,
        changed_predator,
        ids,
        [True] * 3,
        predator_observed=observed,
    )
    np.testing.assert_array_equal(first.predator_emissions, np.ones((1, 3, 7)))
    np.testing.assert_array_equal(first.predator_emissions, second.predator_emissions)


def test_partial_missingness_matches_manual_category_enumeration() -> None:
    prey = np.zeros((1, 1, 13), dtype=np.int64)
    predator = np.asarray([[[0, 2, 1, 1, 0, 2]]], dtype=np.int64)
    observed = np.asarray([[[True, False, True, False, True, False]]])
    prepared = prepare_observations(prey, predator, ("site",), [True], predator_observed=observed)
    p = 0.65
    probabilities = np.asarray([(1 - p) ** 2, 2 * p * (1 - p), p**2])
    expected = np.asarray(
        [
            probabilities[0] * probabilities[1] * probabilities[0],
            probabilities[1] * probabilities[0],
            probabilities[1] * probabilities[0],
            0.0,
            0.0,
            0.0,
            0.0,
        ]
    )
    np.testing.assert_allclose(prepared.predator_emissions[0, 0], expected, rtol=0, atol=1e-15)


def test_site_sorting_reorders_counts_mask_and_cached_emissions_together() -> None:
    prey, predator, ids = _arrays()
    observed = np.asarray(
        [[[True, False, True, False, True, False], [False] * 6, [True] * 6]], dtype=bool
    )
    unsorted = prepare_observations(prey, predator, ids, [True] * 3, predator_observed=observed)
    order = np.argsort(np.asarray(ids), kind="stable")
    sorted_result = prepare_observations(
        prey[:, order],
        predator[:, order],
        tuple(np.asarray(ids)[order]),
        [True] * 3,
        predator_observed=observed[:, order],
    )
    assert unsorted.site_ids == ("site-a", "site-m", "site-z")
    np.testing.assert_array_equal(unsorted.predator_counts, sorted_result.predator_counts)
    np.testing.assert_array_equal(unsorted.predator_observed, sorted_result.predator_observed)
    np.testing.assert_array_equal(unsorted.predator_emissions, sorted_result.predator_emissions)


def test_missingness_mask_validation_and_immutability() -> None:
    prey, predator, ids = _arrays()
    with pytest.raises(ValueError, match="match predator_counts shape"):
        prepare_observations(
            prey, predator, ids, [True] * 3, predator_observed=np.ones((1, 3, 5), bool)
        )
    with pytest.raises(ValueError, match="must be boolean"):
        prepare_observations(
            prey, predator, ids, [True] * 3, predator_observed=np.ones(predator.shape, int)
        )
    result = prepare_observations(
        prey,
        predator,
        ids,
        [True] * 3,
        predator_observed=np.ones_like(predator, dtype=bool),
    )
    assert result.predator_observed is not None
    with pytest.raises(ValueError):
        result.predator_observed[0, 0, 0] = False


def test_shifted_predator_calendar_is_rejected_before_category_scoring() -> None:
    prey, predator, ids = _arrays()
    with pytest.raises(ValueError, match="canonical arrival-category"):
        prepare_observations(
            prey,
            predator,
            ids,
            [True] * 3,
            predator_times=tuple(time + 10 for time in DEFAULT_PREDATOR_TIMES),
        )


def test_capstone_subset_preserves_predator_missingness() -> None:
    prey, predator, ids = _arrays()
    observed = np.asarray(
        [[[True, False, True, False, True, False], [False] * 6, [True] * 6]], dtype=bool
    )
    source = prepare_observations(prey, predator, ids, [True] * 3, predator_observed=observed)
    subset = capstone_qualification.subset_observations(source, np.asarray([True, False, True]))
    np.testing.assert_array_equal(subset.predator_observed, source.predator_observed[:, [0, 2]])
    np.testing.assert_array_equal(
        subset.predator_emissions,
        _predator_emissions(subset.predator_counts, observed=subset.predator_observed),
    )
    assert subset.predator_times == DEFAULT_PREDATOR_TIMES
