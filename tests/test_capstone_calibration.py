"""Mechanical-only checks: no registered map or history is drawn."""

import numpy as np
import pytest

from latent_landscapes import capstone_calibration as c
from latent_landscapes.preinvasion_calibration import ScreenResult
from latent_landscapes.preinvasion_effect_gate import EffectFitBatch

TEST_ROOT = 987654321


def batch(values: np.ndarray, *, failed: int | None = None) -> EffectFitBatch:
    status = ["converged"] * len(values)
    if failed is not None:
        status[failed] = "no_fit"
    return EffectFitBatch(np.zeros_like(values), values / 2, ["converged"] * len(values), status)


def test_grid_and_stencil_use_coarse_neighbours_without_propagation() -> None:
    assert len(c.NUISANCE_GRID) == 765
    assert c.NUISANCE_GRID[382].beta == 0
    assert c.NUISANCE_GRID[382].mu == 0.0025
    assert c.NUISANCE_GRID[382].detection_sd == 0.2
    assert {c.NUISANCE_GRID[i].beta for i in c.axis_adjacent_indices(382)} == {-0.25, 0, 0.25}
    surface = np.random.default_rng(TEST_ROOT).normal(size=(2, 765))
    actual = c.local_contrasts(surface)
    for index in range(765):
        expected = 2 * (surface[:, c.axis_adjacent_indices(index)].max(axis=1) - surface[:, index])
        np.testing.assert_array_equal(actual[:, index], expected)
        assert c.grid_index(*c.grid_coordinates(index)) == index
    spike = np.zeros(765)
    spike[c.grid_index(2, 0, 0)] = 1
    assert c.local_contrasts(spike)[0] == 0


def test_reference_addresses_are_domain_separated_and_bounded() -> None:
    for kind, domain, count in (("screen", 5, 99), ("effect", 6, 999)):
        for node in (0, 382, 764):
            for ref in (0, count - 1):
                result = c.reference_seeds(kind, node, ref, root=TEST_ROOT)  # type: ignore[arg-type]
                for name, seed in result["streams"].items():
                    expected = int(
                        np.random.SeedSequence(
                            [TEST_ROOT, 59, domain, node, ref, c.STAGES[name]]
                        ).generate_state(1, dtype=np.uint64)[0]
                    )
                    assert seed == expected
    assert c.stage_seed("screen", 0, 0, "prey_loss", root=TEST_ROOT) != c.stage_seed(
        "effect", 0, 0, "prey_loss", root=TEST_ROOT
    )
    with pytest.raises(ValueError):
        c.stage_seed("screen", 0, 99, "prey_loss", root=TEST_ROOT)
    with pytest.raises(IndexError):
        c.stage_seed("effect", 765, 0, "prey_loss", root=TEST_ROOT)
    assert c.address_contract(root=TEST_ROOT)["maximum_effect_histories"] == 764235


def test_inclusive_screen_ties_and_shared_invalid_reference_abstention() -> None:
    refs = np.zeros((99, 765))
    observed = np.zeros((2, 765))
    observed[1] = 1
    result = c.screen_cases(["a", "b"], observed, refs)
    assert len(result[0].candidate_indices) == 765
    assert result[1].candidate_indices == ()
    assert result[1].q_values is not None
    assert result[1].q_values[0] == 0.01
    refs[0, 0] = np.nan
    assert all(
        s.status == "missing_screen_table" for s in c.screen_cases(["a", "b"], observed, refs)
    )
    assert all(
        s.status == "missing_screen_table" for s in c.screen_cases(["a", "b"], observed, refs[:98])
    )


def test_complete_union_pending_gate_and_failed_fit_propagation() -> None:
    screens = (
        ScreenResult("a", "ready", (0, 1), None),
        ScreenResult("b", "ready", (1, 764), None),
        ScreenResult("c", "ready", (2,), None),
    )
    assert c.required_effect_nodes(screens) == (0, 1, 2, 764)
    observed = batch(np.array([1.0, 1.0, 1.0]))
    references = {index: batch(np.zeros(999)) for index in (0, 1, 2, 764)}
    with pytest.raises(c.CalibrationPendingError):
        c.combine_effect_tests(screens, observed, references, computation_complete=False)
    result = c.combine_effect_tests(screens, observed, references, computation_complete=True)
    assert all(d.declared and d.p_value == 0.011 for d in result.decisions)
    references[1] = batch(np.zeros(999), failed=17)
    result = c.combine_effect_tests(screens, observed, references, computation_complete=True)
    assert [d.declared for d in result.decisions] == [False, False, True]
    assert [d.p_value for d in result.decisions[:2]] == [1, 1]
    del references[2]
    result = c.combine_effect_tests(screens, observed, references, computation_complete=True)
    assert not any(d.declared for d in result.decisions)


def test_preonly_generator_preserves_survival_and_persistent_detection() -> None:
    a = np.linspace(-2, 2, 160)
    prey, predator = c.generate_screen_reference(a, a, 0, 0, root=TEST_ROOT)
    seeds = c.reference_seeds("screen", 0, 0, root=TEST_ROOT)["streams"]
    hazard = 0.0005 * np.exp(-2 * a) / np.exp(-2 * a).mean()
    loss = -60 + np.random.default_rng(seeds["prey_loss"]).exponential(size=160) / hazard
    visits = np.random.default_rng(seeds["prey_visits"]).random((160, 7, 2))
    expected = (visits < 0.65).sum(axis=2) * (loss[:, None] > np.arange(-60, 1, 10))
    np.testing.assert_array_equal(prey[:, :7], expected)
    assert np.all(prey[:, 7:] == 0) and np.all(predator == 0)
