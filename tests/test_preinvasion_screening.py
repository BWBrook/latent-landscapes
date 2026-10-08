from __future__ import annotations

import numpy as np

from latent_landscapes import preinvasion_calibration as calibration
from latent_landscapes import preinvasion_independent as independent
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes import preinvasion_screening as screening


def test_seed_addresses_are_exact_and_worker_order_independent() -> None:
    mechanical_root = 987654321
    sequence = screening.seed_sequence(17, 23, screening.STAGE_LOSS, root=mechanical_root)
    expected = np.random.SeedSequence([mechanical_root, screening.SEED_NAMESPACE, 17, 23, 1])
    assert sequence.entropy == expected.entropy
    assert sequence.spawn_key == expected.spawn_key
    first = screening.rng_for(17, 23, screening.STAGE_LOSS, root=mechanical_root).random(8)
    second = screening.rng_for(17, 23, screening.STAGE_LOSS, root=mechanical_root).random(8)
    np.testing.assert_array_equal(first, second)
    assert screening.stage_seed(17, 23, 1, root=mechanical_root) != screening.stage_seed(
        17, 24, 1, root=mechanical_root
    )
    assert screening.stage_seed(17, 23, 1, root=mechanical_root) != screening.stage_seed(
        17, 23, 2, root=mechanical_root
    )


def test_public_panel_hash_and_training_scope() -> None:
    panel = screening.load_public_panel()
    assert panel.panel_sha256 == screening.EXPECTED_PANEL_SHA256
    assert panel.observations.prey_counts.shape == (16, 160, 13)
    assert int(panel.observations.training_mask.sum()) == 120
    assert len(panel.observations.site_ids) == 160


def test_seed_ledger_has_one_record_per_address() -> None:
    # A small ledger exercises the on-disk schema without allocating the full
    # production ledger in this unit test.
    rows = np.asarray(
        [
            (node, ref, stage, screening.stage_seed(node, ref, stage))
            for node in range(2)
            for ref in range(3)
            for stage in screening.STAGES
        ],
        dtype=np.uint64,
    )
    assert rows.shape == (18, 4)
    assert len({tuple(row[:3]) for row in rows}) == 18
    assert np.all(rows[:, 3] > 0)


def test_mechanical_batched_point_equivalence_does_not_draw_registered_histories() -> None:
    panel = screening.load_public_panel()
    original = screening.rng_for

    def fail_if_called(*args: object, **kwargs: object) -> np.random.Generator:
        raise AssertionError("qualification mechanical control must not draw registered streams")

    screening.rng_for = fail_if_called
    try:
        result = screening.vectorized_equivalence(panel, count=3)
    finally:
        screening.rng_for = original
    assert result["passed"]
    assert result["max_abs_difference"] <= 1e-12


def test_reference_generation_is_deterministic_and_uses_training_only_score() -> None:
    panel = screening.load_public_panel()
    mechanical_root = 987654321
    left = screening.make_reference_batch(panel, 0, (0, 1), root=mechanical_root)
    right = screening.make_reference_batch(panel, 0, (1, 0), root=mechanical_root)
    np.testing.assert_array_equal(
        left.observations.prey_counts, right.observations.prey_counts[[1, 0]]
    )
    score_left = screening._pre_score(left.observations, panel.map_a, panel.site_a, 0)
    changed = left.observations.prey_counts.copy()
    changed[:, ~left.observations.training_mask] = 2
    holdout_changed = likelihood.prepare_observations(
        changed,
        left.observations.predator_counts,
        left.observations.site_ids,
        left.observations.training_mask,
        prey_times=left.observations.prey_times,
        predator_times=left.observations.predator_times,
    )
    score_changed = screening._pre_score(holdout_changed, panel.map_a, panel.site_a, 0)
    np.testing.assert_allclose(score_left, score_changed, rtol=0, atol=1e-12)


def test_screen_outputs_has_all_four_case_unions() -> None:
    panel = screening.load_public_panel()
    reference = np.zeros((screening.REFERENCE_COUNT, screening.GRID_SIZE))
    observed_surface = np.zeros((16, screening.GRID_SIZE))
    observed_contrasts = calibration.local_contrasts(observed_surface)
    result = screening.screen_outputs(panel, reference, observed_contrasts, observed_surface)
    assert result["q_values"].shape == (16, screening.GRID_SIZE)
    assert result["candidate_mask"].shape == (16, screening.GRID_SIZE)
    assert len(result["union_rows"]) == 1820
    assert all(int(row["candidate_count"]) == screening.GRID_SIZE for row in result["union_rows"])


def test_r_support_uses_loglikelihood_surface_separately_from_local_contrasts() -> None:
    panel = screening.load_public_panel()
    reference = np.zeros((screening.REFERENCE_COUNT, screening.GRID_SIZE))
    surface = np.zeros((16, screening.GRID_SIZE))
    surface[:, 0] = np.arange(16, dtype=np.float64)
    contrasts = calibration.local_contrasts(surface)
    result = screening.screen_outputs(panel, reference, contrasts, surface)
    assert result["global_r"][3, 0] == 0.0
    assert result["global_r"][3, 1] == 6.0


def test_diagnostic_fit_preserves_all_99_statuses_and_independent_checks() -> None:
    panel = screening.load_public_panel()
    result = screening.score_node(panel, 0, diagnostic=True, root=987654321)
    assert result.prey_counts is not None
    assert result.predator_counts is not None
    rows = screening.fit_diagnostic_references(
        panel,
        {0: (result.prey_counts, result.predator_counts)},
        independent_module=independent,
    )
    assert len(rows) == screening.REFERENCE_COUNT
    assert all(not row["independent_failure"] for row in rows)
    assert all(not row["numerical_failure"] for row in rows)
