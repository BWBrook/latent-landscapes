from __future__ import annotations

from dataclasses import fields

import numpy as np
import pytest
from scipy.special import ndtri  # type: ignore[import-untyped]
from scipy.stats import beta as beta_distribution  # type: ignore[import-untyped]
from scipy.stats import rankdata

from latent_landscapes import arc2b_campaign as arc2b
from latent_landscapes import known_nuisance_calibration as original_generator
from latent_landscapes.goal001.spread import (
    multi_source_dijkstra,
    passable_edges,
    source_labels,
)
from latent_landscapes.goal007.benchmark import FixedInputs
from latent_landscapes.goal011.benchmark import build_fixed_inputs
from latent_landscapes.known_nuisance_calibration import AnalystDataset, AnalystHistory
from latent_landscapes.misspecification_generator import (
    BASELINE_BACKGROUND_HAZARD,
    BOOTSTRAP_ROOT,
    CELL_SPECS,
    PRODUCTION_ROOT,
    SMOKE_ROOT,
    TIMING_ROOT,
    GeneratedCell,
    GeneratorSeed,
    GeneratorSetup,
    _detection_probabilities,
    background_hazard_field,
    build_generator_setup,
    generate_replicate,
    spawn_generator_seeds,
)

GeneratorInputs = tuple[FixedInputs, GeneratorSetup, GeneratorSeed, tuple[GeneratedCell, ...]]


@pytest.fixture(scope="module")
def generator_inputs() -> GeneratorInputs:
    fixed = build_fixed_inputs()
    setup = build_generator_setup(fixed)
    seed = spawn_generator_seeds(SMOKE_ROOT, "smoke", 1)[0]
    return fixed, setup, seed, generate_replicate(fixed, setup, seed)


def test_fixed_cell_design_is_exactly_the_approved_17_cells() -> None:
    assert tuple(cell.cell_id for cell in CELL_SPECS) == (
        "B_h1",
        "B_h3",
        "B_h5",
        "D10_h1",
        "D10_h3",
        "D10_h5",
        "D20_h1",
        "D20_h3",
        "D20_h5",
        "PD10_h1",
        "PD10_h3",
        "PD10_h5",
        "B50-I_h1",
        "B100-I_h1",
        "B50-A_h1",
        "B100-A_h1",
        "B100-A_h3",
    )
    assert len({cell.cell_id for cell in CELL_SPECS}) == 17
    assert sum(cell.prey_detection_sd > 0 for cell in CELL_SPECS) == 6
    assert sum(cell.predator_detection_sd > 0 for cell in CELL_SPECS) == 3
    assert sum(cell.background_cv > 0 for cell in CELL_SPECS) == 5


def test_seed_manifest_uses_all_seven_disjoint_full_width_streams() -> None:
    assert len({PRODUCTION_ROOT, TIMING_ROOT, SMOKE_ROOT, BOOTSTRAP_ROOT}) == 4
    first = spawn_generator_seeds(PRODUCTION_ROOT, "production", 8)
    replay = spawn_generator_seeds(PRODUCTION_ROOT, "production", 8)
    assert first == replay
    all_streams = [value for record in first for value in record.stream_seeds]
    assert len(all_streams) == 56
    assert len(set(all_streams)) == 56
    assert all(0 <= value < 2**64 for value in all_streams)
    changed = spawn_generator_seeds(TIMING_ROOT, "timing", 8)
    assert {value for record in first for value in record.stream_seeds}.isdisjoint(
        value for record in changed for value in record.stream_seeds
    )


def test_exposure_score_is_the_registered_full_map_midrank_transform(
    generator_inputs: GeneratorInputs,
) -> None:
    fixed, setup, _, _ = generator_inputs
    landscape = fixed.landscape
    distances, _ = multi_source_dijkstra(
        node_count=landscape.cell_count,
        weighted_edges=passable_edges(landscape),
        source_labels=source_labels(landscape),
    )
    negative_distance = -np.asarray(distances, dtype=np.float64)
    expected = ndtri((rankdata(negative_distance, method="average") - 0.5) / len(distances))
    expected = (expected - expected.mean()) / expected.std(ddof=0)
    assert setup.accepted_mask.shape == (72, 84)
    assert setup.accepted_mask.all()
    assert setup.unreachable_tie_count == 823
    assert np.unique(setup.exposure_score[~landscape.passable]).shape == (1,)
    assert setup.unreachable_tie_exposure_score == pytest.approx(
        setup.exposure_score[~landscape.passable][0]
    )
    assert np.array_equal(setup.exposure_score.ravel(), expected)
    assert setup.exposure_score.mean() == pytest.approx(0.0, abs=1e-15)
    assert setup.exposure_score.std(ddof=0) == pytest.approx(1.0, abs=1e-15)


def test_exact_circulant_embedding_and_bounded_stochastic_covariance(
    generator_inputs: GeneratorInputs,
) -> None:
    _, setup, _, _ = generator_inputs
    sampler = setup.field_sampler
    assert sampler.field_shape == (72, 84)
    assert sampler.embedding_shape == (142, 166)
    assert sampler.minimum_eigenvalue > 0.0
    assert sampler.reconstruction_max_abs_error <= 1e-12

    rng = np.random.default_rng(2026092399)
    draws = np.asarray(
        [
            (
                (field := sampler.sample(rng))[10, 10],
                field[10, 11],
                field[10, 20],
            )
            for _ in range(600)
        ]
    )
    empirical = np.corrcoef(draws, rowvar=False)
    assert empirical[0, 1] == pytest.approx(np.exp(-1.0 / 10.0), abs=0.05)
    assert empirical[0, 2] == pytest.approx(np.exp(-10.0 / 10.0), abs=0.08)


def test_gaussian_field_is_not_recentered_or_rescaled_per_realisation(
    generator_inputs: GeneratorInputs,
) -> None:
    _, setup, seed, _ = generator_inputs
    field = setup.field_sampler.sample(np.random.default_rng(seed.background_field_seed))
    assert abs(float(field.mean())) > 1e-3
    assert abs(float(field.std(ddof=0)) - 1.0) > 1e-3


def test_registered_beta_laws_have_exact_mean_and_sd() -> None:
    uniforms = (np.arange(200_000, dtype=np.float64) + 0.5) / 200_000
    expected_parameters = {
        0.10: (14.1375, 7.6125),
        0.20: (3.046875, 1.640625),
    }
    for sd, (alpha, beta) in expected_parameters.items():
        values = _detection_probabilities(uniforms, sd)
        assert np.array_equal(values, beta_distribution.ppf(uniforms, alpha, beta))
        assert float(values.mean()) == pytest.approx(0.65, abs=2e-5)
        assert float(values.std(ddof=0)) == pytest.approx(sd, abs=2e-5)


def test_zero_heterogeneity_returns_constant_baseline_exactly(
    generator_inputs: GeneratorInputs,
) -> None:
    _, setup, seed, cells = generator_inputs
    gaussian = setup.field_sampler.sample(np.random.default_rng(seed.background_field_seed))
    hazards = background_hazard_field(setup, gaussian, nominal_cv=0.0, exposure_mixing=0.0)
    assert np.array_equal(hazards, np.full((72, 84), BASELINE_BACKGROUND_HAZARD))
    for cell_id in ("B_h1", "B_h3", "B_h5"):
        cell = next(value for value in cells if value.cell.cell_id == cell_id)
        assert np.array_equal(
            cell.latent_truth.background_hazard,
            np.full(160, BASELINE_BACKGROUND_HAZARD),
        )
        assert cell.diagnostics.map_hazard_cv == 0.0
        assert cell.diagnostics.map_hazard_a_correlation is None
        assert cell.diagnostics.map_hazard_exposure_correlation is None


def test_baseline_cells_are_bitwise_identical_to_original_generator(
    generator_inputs: GeneratorInputs,
) -> None:
    fixed, _, seed, cells = generator_inputs
    effects = (1.0, 3.0, 5.0)
    truths = original_generator._truths(effects)
    old_seed = arc2b.DatasetSeed(
        seed.phase,
        seed.index,
        seed.process_seed,
        seed.predator_detection_seed,
        seed.prey_event_seed,
        seed.prey_detection_seed,
    )
    old_config = original_generator._generator_config(
        original_generator.smoke_config(), truths, "evaluation"
    )
    old_datasets = arc2b.generate_paired_datasets(fixed, old_seed, truths, old_config)
    new_by_id = {cell.cell.cell_id: cell for cell in cells}
    for effect, old in zip(effects, old_datasets, strict=True):
        new = new_by_id[f"B_h{int(effect)}"]
        assert np.array_equal(
            new.latent_truth.arrival,
            np.asarray([row.true_predator_arrival for row in old.records]),
        )
        assert np.array_equal(
            new.latent_truth.prey_extirpation,
            np.asarray([row.true_prey_extirpation for row in old.records]),
        )
        assert tuple(
            (
                row.site_id,
                row.cluster_id,
                row.split,
                row.predator_detection_counts,
                row.prey_detection_counts,
                row.prey_detection_probability,
            )
            for row in old.records
        ) == tuple(
            (
                row.site_id,
                row.cluster_id,
                row.split,
                row.predator_detection_counts,
                row.prey_detection_counts,
                row.prey_detection_probability,
            )
            for row in new.dataset.histories
        )


def test_generation_couples_all_mechanisms_but_keeps_analyst_boundary_unchanged(
    generator_inputs: GeneratorInputs,
) -> None:
    _, _, _, cells = generator_inputs
    by_id = {cell.cell.cell_id: cell for cell in cells}
    assert len(cells) == 17
    reference = by_id["B_h1"].latent_truth
    assert all(np.array_equal(cell.latent_truth.arrival, reference.arrival) for cell in cells)
    assert all(
        np.array_equal(cell.latent_truth.prey_event_threshold, reference.prey_event_threshold)
        for cell in cells
    )

    for truth in (1, 3, 5):
        baseline = by_id[f"B_h{truth}"].latent_truth
        for prefix in ("D10", "D20", "PD10"):
            departure = by_id[f"{prefix}_h{truth}"].latent_truth
            assert np.array_equal(departure.prey_extirpation, baseline.prey_extirpation)
            assert np.array_equal(departure.background_hazard, baseline.background_hazard)
    assert np.array_equal(
        by_id["B100-A_h1"].latent_truth.background_hazard,
        by_id["B100-A_h3"].latent_truth.background_hazard,
    )
    assert np.array_equal(
        by_id["D10_h1"].latent_truth.prey_detection_probability,
        by_id["D10_h5"].latent_truth.prey_detection_probability,
    )
    assert np.array_equal(
        by_id["PD10_h1"].latent_truth.predator_detection_probability,
        by_id["PD10_h5"].latent_truth.predator_detection_probability,
    )
    assert by_id["D10_h1"].diagnostics.prey_detection_sd > 0.0
    assert by_id["D10_h1"].diagnostics.predator_detection_sd == 0.0
    assert by_id["PD10_h1"].diagnostics.predator_detection_sd > 0.0
    assert by_id["PD10_h1"].diagnostics.prey_detection_sd == 0.0

    analyst_fields = {field.name for field in fields(AnalystHistory)}
    assert "background_hazard" not in analyst_fields
    assert "true_predator_arrival" not in analyst_fields
    assert "predator_detection_probability" not in analyst_fields
    for cell in cells:
        assert isinstance(cell.dataset, AnalystDataset)
        assert len(cell.dataset.histories) == 160
        assert len(cell.dataset.opaque_id) == 32
        assert all(row.prey_detection_probability == 0.65 for row in cell.dataset.histories)


def test_detection_event_uniforms_are_shared_across_cells(
    generator_inputs: GeneratorInputs,
) -> None:
    _, _, _, cells = generator_inputs
    by_id = {cell.cell.cell_id: cell for cell in cells}
    baseline_h3 = by_id["B_h3"].dataset.histories
    pd_h3 = by_id["PD10_h3"].dataset.histories
    d10_h3 = by_id["D10_h3"].dataset.histories
    d20_h3 = by_id["D20_h3"].dataset.histories
    assert tuple(row.prey_detection_counts for row in baseline_h3) == tuple(
        row.prey_detection_counts for row in pd_h3
    )
    assert tuple(row.predator_detection_counts for row in baseline_h3) == tuple(
        row.predator_detection_counts for row in d10_h3
    )
    assert tuple(row.predator_detection_counts for row in baseline_h3) == tuple(
        row.predator_detection_counts for row in d20_h3
    )


def test_field_scaling_and_diagnostics_cover_map_sample_and_splits(
    generator_inputs: GeneratorInputs,
) -> None:
    _, setup, _, cells = generator_inputs
    by_id = {cell.cell.cell_id: cell for cell in cells}
    aligned_h1 = by_id["B100-A_h1"]
    aligned_h3 = by_id["B100-A_h3"]
    independent = by_id["B100-I_h1"]
    assert aligned_h1.diagnostics == aligned_h3.diagnostics
    assert aligned_h1.diagnostics.map_hazard_mean == pytest.approx(0.002, abs=1e-18)
    assert independent.diagnostics.map_hazard_mean == pytest.approx(0.002, abs=1e-18)
    assert aligned_h1.diagnostics.map_hazard_cv > 0.0
    assert aligned_h1.diagnostics.map_hazard_a_correlation is not None
    assert aligned_h1.diagnostics.map_hazard_a_correlation > 0.5

    hazards = background_hazard_field(
        setup,
        setup.field_sampler.sample(np.random.default_rng(123)),
        nominal_cv=1.0,
        exposure_mixing=0.7,
    )
    assert hazards.shape == (72, 84)
    assert np.isfinite(hazards).all()
    assert hazards.mean() == pytest.approx(0.002, abs=1e-18)

    diagnostics = aligned_h1.diagnostics
    assert diagnostics.sampled_arrived_count + diagnostics.sampled_arrival_censored_count == 160
    assert diagnostics.training_arrived_count + diagnostics.training_arrival_censored_count == 120
    assert diagnostics.holdout_arrived_count + diagnostics.holdout_arrival_censored_count == 40
    assert diagnostics.map_arrival_censored_count >= setup.unreachable_tie_count
    assert 0.0 <= diagnostics.map_arrival_censored_fraction <= 1.0


def test_generation_is_deterministic(generator_inputs: GeneratorInputs) -> None:
    fixed, setup, seed, cells = generator_inputs
    replay = generate_replicate(fixed, setup, seed)
    for first, second in zip(cells, replay, strict=True):
        assert first.cell == second.cell
        assert first.dataset == second.dataset
        assert first.diagnostics == second.diagnostics
        assert np.array_equal(first.latent_truth.arrival, second.latent_truth.arrival)
        assert np.array_equal(
            first.latent_truth.prey_extirpation, second.latent_truth.prey_extirpation
        )
        assert np.array_equal(
            first.latent_truth.background_hazard, second.latent_truth.background_hazard
        )


def test_setup_rejects_mismatched_design(generator_inputs: GeneratorInputs) -> None:
    fixed, setup, seed, _ = generator_inputs
    bad_setup = GeneratorSetup(
        tuple(reversed(setup.site_ids)),
        setup.site_rows,
        setup.site_cols,
        setup.site_splits,
        setup.site_cluster_ids,
        setup.accepted_mask,
        setup.exposure_score,
        setup.unreachable_tie_count,
        setup.unreachable_tie_exposure_score,
        setup.field_sampler,
    )
    with pytest.raises(ValueError, match="sampling design"):
        generate_replicate(fixed, bad_setup, seed)
