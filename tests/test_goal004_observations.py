from __future__ import annotations

import dataclasses
import inspect

import numpy as np

from latent_landscapes.goal001.design import build_design, spawn_generators
from latent_landscapes.goal001.landscape import build_landscape
from latent_landscapes.goal003.spread import compute_stochastic_spread


def test_goal004_observation_contract_and_exact_replay() -> None:
    from latent_landscapes.goal004 import observations

    landscape = build_landscape()
    centre_rng, holdout_rng, _ = spawn_generators()
    design = build_design(landscape, centre_rng, holdout_rng)
    truth = compute_stochastic_spread(landscape, np.random.default_rng(41))

    first = observations.generate_observations(
        design.sites,
        truth,
        np.random.default_rng(73),
    )
    second = observations.generate_observations(
        design.sites,
        truth,
        np.random.default_rng(73),
    )

    assert observations.SURVEY_TIMES == (10, 20, 30, 40, 50, 60)
    assert observations.REPLICATES == (1, 2)
    assert observations.DETECTION_PROBABILITY == 0.65
    assert first == second
    assert len(first) == 1_920
    assert sum(record.split == "training" for record in first) == 1_440
    assert sum(record.split == "holdout" for record in first) == 480
    assert list(first) == sorted(
        first,
        key=lambda record: (
            record.cluster_id,
            record.site_offset_index,
            record.time,
            record.replicate,
        ),
    )
    assert all(
        not record.detected or truth.arrival[record.row, record.col] <= record.time
        for record in first
    )
    assert not {
        "arrival",
        "true_arrival",
        "occupied",
        "latent_occupancy",
        "source_zone",
    } & set(first[0].to_csv_row())
    assert not {
        "arrival",
        "true_arrival",
        "occupied",
        "latent_occupancy",
        "source_zone",
    } & {field.name for field in dataclasses.fields(first[0])}


def test_goal004_observations_use_one_joint_detection_stream() -> None:
    from latent_landscapes.goal004 import observations

    signature = inspect.signature(observations.generate_observations)
    assert tuple(signature.parameters) == ("sites", "truth", "detection_rng")

    landscape = build_landscape()
    centre_rng, holdout_rng, _ = spawn_generators()
    design = build_design(landscape, centre_rng, holdout_rng)
    truth = compute_stochastic_spread(landscape, np.random.default_rng(12))
    rng = np.random.default_rng(99)
    state_before = rng.bit_generator.state

    records = observations.generate_observations(design.sites, truth, rng)

    assert rng.bit_generator.state != state_before
    assert {record.cluster_id for record in records if record.split == "training"}.isdisjoint(
        {record.cluster_id for record in records if record.split == "holdout"}
    )
