from __future__ import annotations

from collections import Counter

import pytest

from latent_landscapes.goal004 import observations as goal004_observations
from latent_landscapes.goal006 import spread as goal006_spread
from latent_landscapes.goal008 import benchmark as goal008
from latent_landscapes.goal013 import design

EXPECTED_COORDINATES = (
    (0, "low", 5, 14),
    (0, "low", 10, 6),
    (0, "low", 17, 10),
    (0, "low", 57, 6),
    (0, "high", 25, 6),
    (0, "high", 29, 15),
    (0, "high", 42, 6),
    (0, "high", 69, 6),
    (1, "low", 17, 43),
    (1, "low", 41, 27),
    (1, "low", 41, 36),
    (1, "low", 50, 34),
    (1, "high", 5, 38),
    (1, "high", 28, 34),
    (1, "high", 29, 25),
    (1, "high", 69, 34),
    (2, "low", 41, 61),
    (2, "low", 53, 48),
    (2, "low", 53, 56),
    (2, "low", 53, 64),
    (2, "high", 5, 47),
    (2, "high", 5, 55),
    (2, "high", 5, 64),
    (2, "high", 69, 48),
    (3, "low", 37, 76),
    (3, "low", 41, 69),
    (3, "low", 53, 79),
    (3, "low", 61, 76),
    (3, "high", 2, 76),
    (3, "high", 17, 72),
    (3, "high", 17, 81),
    (3, "high", 25, 76),
)
EXPECTED_HOLDOUTS = {
    (0, "low", 17, 10),
    (0, "high", 25, 6),
    (1, "low", 41, 36),
    (1, "high", 69, 34),
    (2, "low", 53, 64),
    (2, "high", 5, 47),
    (3, "low", 61, 76),
    (3, "high", 17, 81),
}


def _forbidden(*args: object, **kwargs: object) -> None:
    raise AssertionError("the deterministic selector accessed stochastic or observation inputs")


def test_frozen_selector_replays_exact_candidates_winner_split_and_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(goal006_spread, "sample_edge_shock_vector", _forbidden)
    monkeypatch.setattr(goal008, "generate_truth_block", _forbidden)
    monkeypatch.setattr(goal004_observations, "generate_observations", _forbidden)

    first = design.build_contrast_balanced_design()
    second = design.build_contrast_balanced_design()

    assert first == second
    assert len(first.candidates) == 635
    assert sum(candidate.retained for candidate in first.candidates) == 629
    assert Counter(
        candidate.stratum_index for candidate in first.candidates if candidate.retained
    ) == {0: 196, 1: 122, 2: 154, 3: 157}
    excluded = tuple(candidate for candidate in first.candidates if not candidate.retained)
    assert tuple((row.row, row.col) for row in excluded) == (
        (5, 2),
        (29, 2),
        (41, 2),
        (65, 2),
        (65, 3),
        (65, 4),
    )
    assert all(row.source_overlap_cells for row in excluded)
    assert first.complete_attempt_count == 1511
    assert first.unique_design_count == 1511
    assert first.score.minimum_standardized_contrast == 1.333848482928
    assert first.score.maximum_absolute_u_z_correlation == 0.570746495042
    assert first.score.sum_squared_centered_z == 3.641492184069
    assert first.score.minimum_pairwise_distance == 8.0
    assert first.score.maximum_absolute_u_z_correlation <= 0.60
    assert (
        tuple(
            (row.stratum_index, row.tail, row.center_row, row.center_col)
            for row in first.selected_clusters
        )
        == EXPECTED_COORDINATES
    )
    assert {
        (row.stratum_index, row.tail, row.center_row, row.center_col)
        for row in first.selected_clusters
        if row.split == "holdout"
    } == EXPECTED_HOLDOUTS
    assert Counter(row.split for row in first.selected_clusters) == {
        "training": 24,
        "holdout": 8,
    }
    assert len(first.sampling_design.sites) == 160
    assert first.design_digest == "ba887b460d8a8dff1b731086de77dd2d00edce1c00d37c8550fa161558092410"


def test_selector_fails_closed_when_search_or_correlation_gate_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(design, "SEARCH_ATTEMPTS", 0)
    with pytest.raises(RuntimeError, match="complete design"):
        design.build_contrast_balanced_design()

    monkeypatch.setattr(design, "SEARCH_ATTEMPTS", 10_000)
    monkeypatch.setattr(design, "MAXIMUM_ABSOLUTE_CORRELATION", 0.0)
    with pytest.raises(RuntimeError, match="correlation gate"):
        design.build_contrast_balanced_design()
