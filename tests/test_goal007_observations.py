from __future__ import annotations

import inspect
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from latent_landscapes.goal001.design import DesignSite
from latent_landscapes.goal007.observations import (
    REPLICATES,
    SURVEY_TIMES,
    collapse_duplicate_visits,
    generate_perfect_observations,
    site_onset_categories,
)


def _sites() -> tuple[DesignSite, ...]:
    return (
        DesignSite(
            cluster_id="cluster_02",
            split="holdout",
            stratum_index=1,
            center_row=1,
            center_col=1,
            euclidean_source_distance=2.0,
            site_id="site_b",
            site_offset_index=0,
            offset_row=0,
            offset_col=0,
            row=1,
            col=1,
        ),
        DesignSite(
            cluster_id="cluster_01",
            split="training",
            stratum_index=0,
            center_row=0,
            center_col=0,
            euclidean_source_distance=1.0,
            site_id="site_a",
            site_offset_index=0,
            offset_row=0,
            offset_col=0,
            row=0,
            col=0,
        ),
    )


def test_perfect_observations_retain_two_equal_visits_in_frozen_order() -> None:
    truth = SimpleNamespace(arrival=np.asarray([[20.0, 99.0], [99.0, 45.0]]))

    records = generate_perfect_observations(_sites(), truth)

    assert len(records) == 2 * len(SURVEY_TIMES) * len(REPLICATES)
    assert [(row.site_id, row.time, row.replicate) for row in records[:4]] == [
        ("site_a", 10, 1),
        ("site_a", 10, 2),
        ("site_a", 20, 1),
        ("site_a", 20, 2),
    ]
    for first, second in zip(records[::2], records[1::2], strict=True):
        assert (first.site_id, first.time, first.detected) == (
            second.site_id,
            second.time,
            second.detected,
        )
    assert [row.detected for row in records if row.site_id == "site_a"] == [
        0,
        0,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        1,
    ]
    assert [row.detected for row in records if row.site_id == "site_b"] == [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        1,
        1,
        1,
    ]


def test_perfect_observation_api_has_no_detection_rng() -> None:
    parameters = inspect.signature(generate_perfect_observations).parameters

    assert tuple(parameters) == ("sites", "truth")
    assert all("rng" not in name and "probability" not in name for name in parameters)


def test_duplicate_collapse_preserves_split_and_yields_one_onset_per_site() -> None:
    truth = SimpleNamespace(arrival=np.asarray([[20.0, 99.0], [99.0, 45.0]]))
    records = generate_perfect_observations(_sites(), truth)

    collapsed = collapse_duplicate_visits(records)
    site_ids, categories = site_onset_categories(
        site_ids=("site_a", "site_b"),
        records=collapsed,
    )

    assert len(collapsed) == 2 * len(SURVEY_TIMES)
    assert {row.split for row in collapsed if row.site_id == "site_a"} == {"training"}
    assert {row.split for row in collapsed if row.site_id == "site_b"} == {"holdout"}
    assert site_ids == ("site_a", "site_b")
    assert categories.tolist() == [1, 4]


def test_duplicate_collapse_rejects_disagreement_and_incomplete_histories() -> None:
    truth = SimpleNamespace(arrival=np.asarray([[20.0, 99.0], [99.0, 45.0]]))
    records = generate_perfect_observations(_sites(), truth)
    inconsistent = (*records[:1], replace(records[1], detected=1), *records[2:])

    with pytest.raises(ValueError, match="duplicate visits disagree"):
        collapse_duplicate_visits(inconsistent)
    with pytest.raises(ValueError, match="complete"):
        collapse_duplicate_visits(records[:-1])
