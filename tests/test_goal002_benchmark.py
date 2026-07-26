from __future__ import annotations

import dataclasses
import importlib
from collections.abc import Iterator
from math import isfinite
from typing import Any

import pytest


def load_goal002(name: str) -> Any:
    return importlib.import_module(f"latent_landscapes.goal002.{name}")


def load_goal001(name: str) -> Any:
    return importlib.import_module(f"latent_landscapes.goal001.{name}")


@pytest.fixture(scope="module")
def fixed_inputs() -> Any:
    return load_goal002("benchmark").build_fixed_inputs()


@pytest.fixture(scope="module")
def small_result(fixed_inputs: Any) -> Any:
    benchmark = load_goal002("benchmark")
    config = benchmark.Goal002Config(
        calibration_replicates=4,
        validation_replicates=4,
        calibration_rank_one_based=4,
    )
    return benchmark.run_goal002(config=config, fixed_inputs=fixed_inputs)


def test_production_defaults_are_exactly_500_plus_500_and_rank_476() -> None:
    benchmark = load_goal002("benchmark")

    config = benchmark.Goal002Config()

    assert config.master_seed == 20260726
    assert config.calibration_replicates == 500
    assert config.validation_replicates == 500
    assert config.calibration_rank_one_based == 476
    assert config.truth_rate == 1.0
    assert config.is_production is True


def test_fixed_inputs_reconcile_goal001_without_observations_or_profiles(
    fixed_inputs: Any,
) -> None:
    assert fixed_inputs.landscape.shape == (72, 84)
    assert fixed_inputs.landscape.cell_count == 6048
    assert len(fixed_inputs.design.clusters) == 32
    assert len(fixed_inputs.design.sites) == 160
    assert sum(site.split == "training" for site in fixed_inputs.design.sites) == 120
    assert sum(site.split == "holdout" for site in fixed_inputs.design.sites) == 40
    assert len(fixed_inputs.habitat_distances) == 160
    assert len(fixed_inputs.hard_front_distances) == 160
    assert all(fixed_inputs.invariants.values())
    assert not hasattr(fixed_inputs, "observations")
    assert not hasattr(fixed_inputs, "profile")


def test_small_ensemble_uses_separate_phase_children_and_compact_results(
    small_result: Any,
) -> None:
    assert len(small_result.calibration_seeds) == 4
    assert len(small_result.validation_seeds) == 4
    assert len(small_result.calibration_results) == 4
    assert len(small_result.validation_results) == 4
    assert [record.spawn_key for record in small_result.calibration_seeds] == [
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
    ]
    assert [record.spawn_key for record in small_result.validation_seeds] == [
        (1, 0),
        (1, 1),
        (1, 2),
        (1, 3),
    ]
    assert small_result.cutoff.rank_one_based == 4
    assert small_result.cutoff.sample_size == 4
    assert all(small_result.invariants.values())

    forbidden_names = {
        "Observation",
        "LikelihoodProfile",
        "LikelihoodClass",
        "HoldoutEvaluation",
        "HoldoutPartition",
    }
    for value in walk_values(small_result):
        assert type(value).__name__ not in forbidden_names
        if isinstance(value, tuple):
            assert len(value) != 1920
        if dataclasses.is_dataclass(value):
            assert "prediction_signature" not in {field.name for field in dataclasses.fields(value)}


def test_validation_replay_matches_exact_truth_training_only_and_set_valued_scores(
    fixed_inputs: Any,
    small_result: Any,
) -> None:
    baseline = load_goal002("baseline")
    calibration = load_goal002("calibration")
    likelihood = load_goal001("likelihood")
    observations_module = load_goal001("observations")
    summary = small_result.validation_results[0]
    seed_record = small_result.validation_seeds[0]
    observations = observations_module.generate_observations(
        fixed_inputs.design.sites,
        fixed_inputs.truth,
        calibration.generator_from_seed_record(seed_record),
    )
    training = tuple(record for record in observations if record.split == "training")
    holdout = tuple(record for record in observations if record.split == "holdout")

    assert len(observations) == 1920
    assert len(training) == 1440
    assert len(holdout) == 480
    assert {record.cluster_id for record in training}.isdisjoint(
        {record.cluster_id for record in holdout}
    )

    full_profile = likelihood.profile_likelihood(
        model="habitat",
        scope="all",
        distances=fixed_inputs.habitat_distances,
        records=observations,
        detection_probability=observations_module.DETECTION_PROBABILITY,
        lr_threshold=small_result.cutoff.cutoff,
    )
    exact_lr = calibration.likelihood_ratio_at_truth(
        profile=full_profile,
        distances=fixed_inputs.habitat_distances,
        records=observations,
        detection_probability=observations_module.DETECTION_PROBABILITY,
        truth_rate=1.0,
    )
    habitat_training = likelihood.profile_likelihood(
        model="habitat",
        scope="training",
        distances=fixed_inputs.habitat_distances,
        records=training,
        detection_probability=observations_module.DETECTION_PROBABILITY,
    )
    habitat_holdout = likelihood.evaluate_holdout_mle(
        model="habitat",
        training_profile=habitat_training,
        distances=fixed_inputs.habitat_distances,
        records=holdout,
        detection_probability=observations_module.DETECTION_PROBABILITY,
    )
    neutral_model = baseline.fit_time_stratified_baseline(training)
    neutral_score = baseline.score_time_stratified_baseline(neutral_model, holdout)
    hard_front_training = likelihood.profile_likelihood(
        model="hard_front",
        scope="training",
        distances=fixed_inputs.hard_front_distances,
        records=training,
        detection_probability=observations_module.DETECTION_PROBABILITY,
    )
    hard_front_holdout = likelihood.evaluate_holdout_mle(
        model="hard_front",
        training_profile=hard_front_training,
        distances=fixed_inputs.hard_front_distances,
        records=holdout,
        detection_probability=observations_module.DETECTION_PROBABILITY,
    )

    assert summary.lr_at_truth == exact_lr.statistic
    assert summary.truth_log_likelihood == exact_lr.truth_log_likelihood
    assert summary.maximum_log_likelihood == exact_lr.maximum_log_likelihood
    assert summary.nominal_truth_included is (exact_lr.statistic <= likelihood.LR_THRESHOLD)
    assert summary.habitat_brier_maximum == habitat_holdout.brier_score_range.maximum
    assert summary.habitat_brier_minimum == habitat_holdout.brier_score_range.minimum
    assert summary.neutral_brier_score == neutral_score.mean_brier_score
    assert summary.neutral_log_score == neutral_score.total_log_score
    assert summary.paired_brier_difference == pytest.approx(
        habitat_holdout.brier_score_range.maximum - neutral_score.mean_brier_score
    )
    assert summary.hard_front_any_zero_probability is any(
        partition.impossible_positive_count > 0 for partition in hard_front_holdout.partitions
    )
    assert summary.hard_front_every_zero_probability is all(
        partition.impossible_positive_count > 0 for partition in hard_front_holdout.partitions
    )
    assert isfinite(summary.neutral_log_score)
    assert min(probability for _, probability in neutral_model.probabilities) > 0.0
    assert max(probability for _, probability in neutral_model.probabilities) < 1.0


def test_validation_summaries_preserve_mle_sets_and_calibrated_topology(
    small_result: Any,
) -> None:
    for summary in small_result.validation_results:
        assert summary.mle_intervals
        assert summary.mle_class_count == len(summary.mle_intervals)
        assert summary.mle_total_width >= 0.0
        assert summary.truth_to_mle_distance >= 0.0
        assert summary.calibrated_support_component_count >= 1
        assert summary.calibrated_support_total_width >= 0.0
        assert summary.calibrated_truth_included is (
            summary.lr_at_truth <= small_result.cutoff.cutoff
        )


def walk_values(root: object) -> Iterator[object]:
    stack = [root]
    seen: set[int] = set()
    while stack:
        value = stack.pop()
        identity = id(value)
        if identity in seen:
            continue
        seen.add(identity)
        yield value
        if dataclasses.is_dataclass(value):
            stack.extend(getattr(value, field.name) for field in dataclasses.fields(value))
        elif isinstance(value, dict):
            stack.extend(value.keys())
            stack.extend(value.values())
        elif isinstance(value, (tuple, list)):
            stack.extend(value)
