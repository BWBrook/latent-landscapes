from __future__ import annotations

import numpy as np
import pytest

from latent_landscapes import null_effect_generator as generator
from latent_landscapes import prospective_background_generator as goal053
from latent_landscapes.goal011.benchmark import build_fixed_inputs


@pytest.fixture(scope="module")
def inputs() -> tuple[object, generator.GeneratorSetup, generator.GeneratorSeed]:
    fixed = build_fixed_inputs()
    setup = generator.build_generator_setup(fixed)
    seed = generator.spawn_generator_seeds(generator.SMOKE_ROOT, "smoke", 1)[0]
    return fixed, setup, seed


def test_registered_roots_and_block_dimensions() -> None:
    roots = {
        generator.REFERENCE_ROOT,
        generator.EVALUATION_ROOT,
        generator.TIMING_REFERENCE_ROOT,
        generator.TIMING_EVALUATION_ROOT,
        generator.BOOTSTRAP_ROOT,
        generator.SMOKE_ROOT,
    }
    assert len(roots) == 6
    assert len(generator.BETAS) == 81
    assert generator.BETAS[0] == -2.0
    assert generator.BETAS[-1] == 2.0
    assert generator.TIMING_REFERENCE_REPLICATES == 4
    assert generator.TIMING_EVALUATION_REPLICATES == 8
    assert (
        len(generator.spawn_generator_seeds(generator.REFERENCE_ROOT, "reference", 999)) == 999
    )
    assert (
        len(generator.spawn_generator_seeds(generator.EVALUATION_ROOT, "evaluation", 1000))
        == 1000
    )
    first = generator.spawn_generator_seeds(generator.SMOKE_ROOT, "smoke", 2)
    second = generator.spawn_generator_seeds(
        generator.TIMING_EVALUATION_ROOT, "timing_evaluation", 2
    )
    assert first == generator.spawn_generator_seeds(generator.SMOKE_ROOT, "smoke", 2)
    assert {value for record in first for value in record.stream_seeds}.isdisjoint(
        value for record in second for value in record.stream_seeds
    )


def test_vectorised_panels_have_registered_schema(
    inputs: tuple[object, generator.GeneratorSetup, generator.GeneratorSeed],
) -> None:
    fixed, setup, seed = inputs
    reference, reference_metadata = generator.generate_block(fixed, setup, seed, "reference")
    evaluation, evaluation_metadata = generator.generate_block(fixed, setup, seed, "evaluation")
    assert set(reference) == {
        "cell_ids",
        "truth_h",
        "truth_beta",
        "predator_counts",
        "prey_counts",
        "true_arrival",
        "true_extirpation",
        "true_hazards",
        "opaque_ids",
        "replicate_indices",
    }
    assert reference["predator_counts"].shape == (81, 160, 6)
    assert reference["prey_counts"].dtype == np.uint8
    assert reference["true_arrival"].shape == (81, 160)
    assert evaluation["predator_counts"].shape == (8, 160, 6)
    assert evaluation["truth_beta"].shape == (8,)
    assert len(reference_metadata) == 81
    assert len(evaluation_metadata) == 8
    assert len(set(map(str, evaluation["opaque_ids"]))) == 8
    assert np.all(reference["replicate_indices"] == seed.index)


def test_original_six_cells_are_bitwise_goal053_replays(
    inputs: tuple[object, generator.GeneratorSetup, generator.GeneratorSeed],
) -> None:
    fixed, setup, seed = inputs
    observed, _ = generator.generate_block(fixed, setup, seed, "evaluation")
    expected = goal053.generate_replicate(fixed, setup, seed)
    for index, cell in enumerate(expected):
        predator = np.asarray(
            [row.predator_detection_counts for row in cell.dataset.histories], dtype=np.uint8
        )
        prey = np.asarray(
            [row.prey_detection_counts for row in cell.dataset.histories], dtype=np.uint8
        )
        assert np.array_equal(observed["predator_counts"][index], predator)
        assert np.array_equal(observed["prey_counts"][index], prey)
        assert np.array_equal(observed["true_arrival"][index], cell.latent_truth.arrival)
        assert np.array_equal(
            observed["true_extirpation"][index], cell.latent_truth.prey_extirpation
        )
        assert np.array_equal(observed["true_hazards"][index], cell.latent_truth.background_hazard)


def test_nonlinear_field_is_positive_normalised_and_non_affine(
    inputs: tuple[object, generator.GeneratorSetup, generator.GeneratorSeed],
) -> None:
    fixed, setup, seed = inputs
    observed, metadata = generator.generate_block(fixed, setup, seed, "evaluation")
    nonlinear_map = generator.nonlinear_hazard_field(
        setup, setup.field_sampler.sample(np.random.default_rng(seed.background_field_seed))
    )
    structure = metadata[6]
    accepted = setup.accepted_mask
    assert structure["top_third_selected_count"] == 2015
    assert structure["top_third_map_count"] == 6048
    assert structure["top_third_indicator_mean"] == pytest.approx(0.0, abs=1e-15)
    assert structure["top_third_indicator_sd"] == pytest.approx(1.0, abs=1e-15)
    assert np.all(nonlinear_map[accepted] > 0.0)
    assert float(nonlinear_map[accepted].mean()) == pytest.approx(0.002, abs=1e-18)
    assert np.array_equal(
        observed["true_hazards"][6], nonlinear_map[setup.site_rows, setup.site_cols]
    )
    assert metadata[4]["affine_a_log_residual_rmse"] > 0.0
    assert metadata[6]["affine_a_log_residual_rmse"] > 0.0
    assert metadata[6]["paired_field_difference_rmse"] > 0.0
    assert metadata[7]["paired_field_difference_max_abs"] > 0.0


def test_affine_a_diagnostics_match_independent_least_squares(
    inputs: tuple[object, generator.GeneratorSetup, generator.GeneratorSeed],
) -> None:
    _fixed, setup, seed = inputs
    observed, metadata = generator.generate_block(_fixed, setup, seed, "evaluation")
    gaussian = setup.field_sampler.sample(np.random.default_rng(seed.background_field_seed))
    nonlinear = generator.nonlinear_hazard_field(setup, gaussian)
    affine = generator.background_hazard_field(
        setup, gaussian, nominal_cv=1.0, exposure_mixing=generator.EXPOSURE_MIXING
    )
    for row, hazard_map in ((4, affine), (6, nonlinear)):
        exposure = setup.exposure_score[setup.accepted_mask]
        log_hazard = np.log(hazard_map[setup.accepted_mask])
        design = np.column_stack((np.ones(exposure.shape), exposure))
        intercept, slope = np.linalg.lstsq(design, log_hazard, rcond=None)[0]
        residual = log_hazard - (intercept + slope * exposure)
        assert metadata[row]["affine_a_log_intercept"] == pytest.approx(intercept)
        assert metadata[row]["affine_a_log_slope"] == pytest.approx(slope)
        assert metadata[row]["affine_a_log_residual_rmse"] == pytest.approx(
            np.sqrt(np.mean(residual * residual))
        )
    assert np.all(observed["true_hazards"][6] > 0.0)


def test_shared_process_and_detection_streams_across_cells(
    inputs: tuple[object, generator.GeneratorSetup, generator.GeneratorSeed],
) -> None:
    fixed, setup, seed = inputs
    observed, _ = generator.generate_block(fixed, setup, seed, "evaluation")
    assert np.all(observed["true_arrival"] == observed["true_arrival"][0])
    assert np.all(observed["predator_counts"] == observed["predator_counts"][0])
    assert np.array_equal(observed["true_hazards"][4], observed["true_hazards"][5])
    assert np.array_equal(observed["true_hazards"][6], observed["true_hazards"][7])
