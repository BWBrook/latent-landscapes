from __future__ import annotations

from dataclasses import fields

import numpy as np
import pytest

from latent_landscapes import misspecification_generator as legacy
from latent_landscapes import prospective_background_generator as generator
from latent_landscapes.adjusted_background_likelihood import normalized_hazards
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.goal011.benchmark import build_fixed_inputs
from latent_landscapes.known_nuisance_calibration import AnalystHistory


@pytest.fixture(scope="module")
def generator_inputs() -> tuple[
    FixedInputs,
    generator.GeneratorSetup,
    generator.GeneratorSeed,
    tuple[generator.GeneratedCell, ...],
]:
    fixed = build_fixed_inputs()
    setup = generator.build_generator_setup(fixed)
    seed = generator.spawn_generator_seeds(generator.SMOKE_ROOT, "smoke", generator.SMOKE_COUNT)[0]
    return fixed, setup, seed, generator.generate_replicate(fixed, setup, seed)


def test_registered_cells_roots_and_phase_counts() -> None:
    assert generator.CELL_IDS == (
        "E0_h1",
        "E0_h3",
        "E06_h1",
        "E06_h3",
        "B100-A_h1",
        "B100-A_h3",
    )
    assert generator.TRUTH_H == (1.0, 3.0, 1.0, 3.0, 1.0, 3.0)
    assert generator.TRUTH_BETA[:4] == (0.0, 0.0, 0.6, 0.6)
    assert np.isnan(generator.TRUTH_BETA[4:]).all()
    assert (
        len(
            {
                generator.PRODUCTION_ROOT,
                generator.TIMING_ROOT,
                generator.BOOTSTRAP_ROOT,
                generator.SMOKE_ROOT,
            }
        )
        == 4
    )
    assert (
        len(generator.spawn_generator_seeds(generator.PRODUCTION_ROOT, "production", 1_000))
        == 1_000
    )
    assert len(generator.spawn_generator_seeds(generator.TIMING_ROOT, "timing", 20)) == 20
    assert (
        len(generator.spawn_generator_seeds(generator.BOOTSTRAP_ROOT, "bootstrap", 2_000)) == 2_000
    )
    assert len(generator.spawn_generator_seeds(generator.SMOKE_ROOT, "smoke", 2)) == 2


def test_seed_replay_and_phase_roots_are_disjoint() -> None:
    first = generator.spawn_generator_seeds(generator.SMOKE_ROOT, "smoke", 2)
    assert first == generator.spawn_generator_seeds(generator.SMOKE_ROOT, "smoke", 2)
    other = generator.spawn_generator_seeds(generator.TIMING_ROOT, "timing", 2)
    assert {value for record in first for value in record.stream_seeds}.isdisjoint(
        value for record in other for value in record.stream_seeds
    )


def test_exact_beta_six_hazard_is_independent_whole_map_normalisation(
    generator_inputs: tuple[
        FixedInputs,
        generator.GeneratorSetup,
        generator.GeneratorSeed,
        tuple[generator.GeneratedCell, ...],
    ],
) -> None:
    _, setup, _, _ = generator_inputs
    field = generator.exact_hazard_field(setup, 0.6)
    all_a = setup.exposure_score[setup.accepted_mask]
    shifted = 0.6 * all_a
    direct = 0.002 * np.exp(shifted - shifted.max()) / np.exp(shifted - shifted.max()).mean()
    assert np.array_equal(field[setup.accepted_mask], direct)
    observed = normalized_hazards(
        0.6, setup.exposure_score, setup.exposure_score[setup.accepted_mask]
    )
    assert np.allclose(field[setup.accepted_mask], observed, rtol=0.0, atol=2e-18)
    assert field[setup.accepted_mask].mean() == pytest.approx(0.002, abs=2e-18)
    assert not np.array_equal(field[setup.accepted_mask], np.full(all_a.shape, 0.002))


def test_pairing_boundary_truth_split_order_and_visits(
    generator_inputs: tuple[
        FixedInputs,
        generator.GeneratorSetup,
        generator.GeneratorSeed,
        tuple[generator.GeneratedCell, ...],
    ],
) -> None:
    _, setup, seed, cells = generator_inputs
    assert len(cells) == 6
    assert tuple(cell.cell.cell_id for cell in cells) == generator.CELL_IDS
    assert tuple(cell.cell.truth_h for cell in cells) == generator.TRUTH_H
    assert tuple(cell.cell.truth_beta for cell in cells)[:4] == generator.TRUTH_BETA[:4]
    reference = cells[0].latent_truth
    assert all(np.array_equal(cell.latent_truth.arrival, reference.arrival) for cell in cells)
    assert all(
        np.array_equal(cell.latent_truth.prey_event_threshold, reference.prey_event_threshold)
        for cell in cells
    )
    assert all(len(cell.dataset.histories) == 160 for cell in cells)
    assert all(
        len(row.predator_detection_counts) == 6 for cell in cells for row in cell.dataset.histories
    )
    assert all(
        len(row.prey_detection_counts) == 6 for cell in cells for row in cell.dataset.histories
    )
    assert tuple(row.site_id for row in cells[0].dataset.histories) == setup.site_ids
    assert tuple(row.split for row in cells[0].dataset.histories) == setup.site_splits
    assert all(
        row.prey_detection_probability == 0.65 for cell in cells for row in cell.dataset.histories
    )
    assert len({cell.dataset.opaque_id for cell in cells}) == 6
    assert all(len(cell.dataset.opaque_id) == 32 for cell in cells)
    assert "background_hazard" not in {field.name for field in fields(AnalystHistory)}
    assert seed.phase == "smoke"
    replay = generator.generate_replicate(*generator_inputs[:3])
    for first, second in zip(replay, cells, strict=True):
        assert first.cell == second.cell
        assert first.dataset == second.dataset
        assert first.diagnostics == second.diagnostics
        for first_array, second_array in zip(
            (
                first.latent_truth.arrival,
                first.latent_truth.prey_event_threshold,
                first.latent_truth.prey_extirpation,
                first.latent_truth.background_hazard,
                first.latent_truth.predator_detection_probability,
                first.latent_truth.prey_detection_probability,
            ),
            (
                second.latent_truth.arrival,
                second.latent_truth.prey_event_threshold,
                second.latent_truth.prey_extirpation,
                second.latent_truth.background_hazard,
                second.latent_truth.predator_detection_probability,
                second.latent_truth.prey_detection_probability,
            ),
            strict=True,
        ):
            assert np.array_equal(first_array, second_array)


def test_constant_and_aligned_cells_replay_goal051_streams(
    generator_inputs: tuple[
        FixedInputs,
        generator.GeneratorSetup,
        generator.GeneratorSeed,
        tuple[generator.GeneratedCell, ...],
    ],
) -> None:
    fixed, setup, seed, cells = generator_inputs
    old = legacy.generate_replicate(fixed, setup, seed)
    by_id = {cell.cell.cell_id: cell for cell in cells}
    old_by_id = {cell.cell.cell_id: cell for cell in old}
    for new_id, old_id in (("B100-A_h1", "B100-A_h1"), ("B100-A_h3", "B100-A_h3")):
        new, prior = by_id[new_id], old_by_id[old_id]
        assert np.array_equal(new.latent_truth.arrival, prior.latent_truth.arrival)
        assert np.array_equal(
            new.latent_truth.prey_event_threshold, prior.latent_truth.prey_event_threshold
        )
        assert np.array_equal(
            new.latent_truth.prey_extirpation, prior.latent_truth.prey_extirpation
        )
        assert np.array_equal(
            new.latent_truth.background_hazard, prior.latent_truth.background_hazard
        )
        assert tuple(new.dataset.histories) == tuple(prior.dataset.histories)
