from __future__ import annotations

import importlib
from dataclasses import dataclass
from math import inf, log
from typing import Any

import numpy as np
import pytest


@dataclass(frozen=True)
class Record:
    site_id: str
    time: float
    detected: int


def load_calibration() -> Any:
    return importlib.import_module("latent_landscapes.goal002.calibration")


def load_likelihood() -> Any:
    return importlib.import_module("latent_landscapes.goal001.likelihood")


def test_frozen_calibration_cutoff_uses_rank_476_without_interpolation() -> None:
    calibration = load_calibration()
    statistics = tuple(float(index // 2) for index in range(500))

    result = calibration.calibrated_lr_cutoff(statistics)

    assert result.rank_one_based == 476
    assert result.sample_size == 500
    assert result.probability == 0.95
    assert result.cutoff == 237.0


def test_calibrated_cutoff_rejects_wrong_or_nonfinite_ensemble() -> None:
    calibration = load_calibration()

    with pytest.raises(ValueError, match="exactly 500"):
        calibration.calibrated_lr_cutoff((1.0, 2.0))
    with pytest.raises(ValueError, match="finite"):
        calibration.calibrated_lr_cutoff(tuple([0.0] * 499 + [inf]))


def test_phase_children_are_separate_and_exactly_replayable() -> None:
    calibration = load_calibration()

    calibration_records, validation_records = calibration.spawn_phase_seed_records(
        calibration_count=3,
        validation_count=2,
    )

    assert [record.phase for record in calibration_records] == ["calibration"] * 3
    assert [record.phase for record in validation_records] == ["validation"] * 2
    assert [record.replicate_index for record in calibration_records] == [0, 1, 2]
    assert [record.replicate_index for record in validation_records] == [0, 1]
    assert [record.spawn_key for record in calibration_records] == [(0, 0), (0, 1), (0, 2)]
    assert [record.spawn_key for record in validation_records] == [(1, 0), (1, 1)]
    assert {record.state for record in calibration_records}.isdisjoint(
        {record.state for record in validation_records}
    )

    first_draws = calibration.generator_from_seed_record(calibration_records[1]).random(5)
    replay_draws = calibration.generator_from_seed_record(calibration_records[1]).random(5)
    assert np.array_equal(first_draws, replay_draws)


def test_seed_record_state_tampering_is_detected() -> None:
    calibration = load_calibration()
    calibration_records, _ = calibration.spawn_phase_seed_records(
        calibration_count=1,
        validation_count=1,
    )
    record = calibration_records[0]
    tampered = calibration.SeedRecord(
        phase=record.phase,
        replicate_index=record.replicate_index,
        entropy=record.entropy,
        spawn_key=record.spawn_key,
        state=(record.state[0] + 1, *record.state[1:]),
    )

    with pytest.raises(ValueError, match="state"):
        calibration.generator_from_seed_record(tampered)


@pytest.mark.parametrize(
    ("successes", "total", "expected_lower", "expected_upper"),
    [
        (0, 10, 0.0, 0.2775327998628892),
        (10, 10, 0.7224672001371107, 1.0),
        (5, 10, 0.236593090512564, 0.7634069094874361),
    ],
)
def test_wilson_interval_edge_cases(
    successes: int,
    total: int,
    expected_lower: float,
    expected_upper: float,
) -> None:
    calibration = load_calibration()

    result = calibration.wilson_interval(successes, total)

    assert result.estimate == successes / total
    assert result.lower == pytest.approx(expected_lower)
    assert result.upper == pytest.approx(expected_upper)


@pytest.mark.parametrize(("successes", "total"), [(-1, 10), (11, 10), (0, 0)])
def test_wilson_interval_rejects_invalid_counts(successes: int, total: int) -> None:
    calibration = load_calibration()

    with pytest.raises(ValueError):
        calibration.wilson_interval(successes, total)


def test_normal_mean_interval_is_hand_calculated_and_rejects_empty_samples() -> None:
    calibration = load_calibration()

    result = calibration.normal_mean_interval((-1.0, -2.0, -3.0, -4.0))

    assert result.estimate == -2.5
    assert result.lower == pytest.approx(-3.7651513118813195)
    assert result.upper == pytest.approx(-1.2348486881186805)
    with pytest.raises(ValueError, match="empty"):
        calibration.normal_mean_interval(())


def test_lr_statistic_evaluates_exact_truth_not_class_midpoint() -> None:
    calibration = load_calibration()
    likelihood = load_likelihood()
    records = (
        Record("A", 1.0, 1),
        Record("A", 1.01, 0),
        Record("A", 2.0, 0),
    )
    distances = {"A": 1.0}
    profile = likelihood.profile_likelihood(
        model="habitat",
        scope="all",
        distances=distances,
        records=records,
        detection_probability=0.5,
    )

    result = calibration.likelihood_ratio_at_truth(
        profile=profile,
        distances=distances,
        records=records,
        detection_probability=0.5,
        truth_rate=1.0,
    )

    exact_truth_ll = -3.0 * log(2.0)
    containing_class = next(value for value in profile.classes if value.as_interval().contains(1.0))
    assert containing_class.representative_rate != 1.0
    assert containing_class.log_likelihood == pytest.approx(exact_truth_ll)
    assert result.truth_log_likelihood == pytest.approx(exact_truth_ll)
    assert result.statistic == pytest.approx(
        2.0 * (profile.maximum_log_likelihood - exact_truth_ll)
    )


def test_profile_summary_preserves_mle_set_and_support_topology() -> None:
    calibration = load_calibration()
    likelihood = load_likelihood()
    records = (
        Record("A", 1.0, 1),
        Record("B", 1.0, 0),
    )
    profile = likelihood.profile_likelihood(
        model="habitat",
        scope="all",
        distances={"A": 1.0, "B": 2.0},
        records=records,
        detection_probability=0.5,
        lr_threshold=0.0,
    )

    result = calibration.summarize_profile(profile, truth_rate=1.0)

    assert result.truth_included is True
    assert result.support_component_count == 1
    assert result.support_boundary_contact is False
    assert result.support_total_width == 1.0
    assert result.mle_intervals == ((1.0, 2.0, True, False),)
    assert result.mle_total_width == 1.0
    assert result.truth_to_mle_distance == 0.0
