from __future__ import annotations

import itertools

import numpy as np
import pytest

from latent_landscapes.preinvasion_calibration import (
    ALPHA,
    EFFECT_REFERENCE_COUNT,
    GAMMA,
    GRID_SIZE,
    MU_GRID,
    NUISANCE_GRID,
    SCREEN_REFERENCE_COUNT,
    CaseDecision,
    ScreenResult,
    axis_adjacent_indices,
    clamped_effect_statistic,
    combine_casewise_effect_tests,
    evaluate_preloglikelihood_surface,
    grid_index,
    inclusive_plus_one_pvalue,
    local_contrast_at_node,
    local_contrasts,
    required_effect_nodes,
    screen_cases,
)


def _effect_table(exceedances: int, observed: float = 1.0) -> np.ndarray:
    values = np.zeros(EFFECT_REFERENCE_COUNT)
    values[:exceedances] = observed
    return values


def _ready(case: str, candidates: tuple[int, ...]) -> ScreenResult:
    return ScreenResult(case, "ready", candidates, np.ones(GRID_SIZE))


def test_public_grid_and_axis_neighbours_are_fixed_and_local() -> None:
    assert len(NUISANCE_GRID) == GRID_SIZE == 81 * 9 * 5
    assert MU_GRID == (0.0005, 0.001, 0.0016, 0.002, 0.0025, 0.0032, 0.004, 0.005, 0.006)

    centre = grid_index(40, 4, 2)
    neighbours = axis_adjacent_indices(centre)
    assert neighbours[0] == centre
    assert len(neighbours) == 7
    assert len(axis_adjacent_indices(grid_index(0, 0, 0))) == 4

    surface = np.zeros((2, GRID_SIZE))
    one_step = grid_index(41, 4, 2)
    two_steps = grid_index(42, 4, 2)
    surface[0, one_step] = 3.0
    surface[1, two_steps] = 5.0
    result = local_contrasts(surface)
    assert result.shape == surface.shape
    assert result[0, centre] == pytest.approx(6.0)
    assert result[1, centre] == 0.0  # a two-step maximum must not propagate


def test_callback_surface_and_local_contrast_use_the_same_grid_order() -> None:
    def likelihood(
        data: float, *, beta: float, mu: float, detection_sd: float
    ) -> float:
        return data + beta - 100.0 * mu + 2.0 * detection_sd

    surface = evaluate_preloglikelihood_surface(4.0, likelihood)
    assert surface.shape == (GRID_SIZE,)
    for index in (0, grid_index(40, 4, 2), GRID_SIZE - 1):
        node = NUISANCE_GRID[index]
        assert surface[index] == pytest.approx(
            likelihood(4.0, beta=node.beta, mu=node.mu, detection_sd=node.detection_sd)
        )
        assert local_contrast_at_node(4.0, index, likelihood) == pytest.approx(
            local_contrasts(surface)[index]
        )


def test_inclusive_plus_one_pvalue_retains_exact_and_near_ties() -> None:
    reference = np.arange(99.0)
    assert inclusive_plus_one_pvalue(98.0, reference) == pytest.approx(0.02)
    assert inclusive_plus_one_pvalue(98.0 + 5e-11, reference) == pytest.approx(0.02)
    assert inclusive_plus_one_pvalue(99.0, reference) == pytest.approx(0.01)


def test_screen_q_point_zero_one_is_excluded_and_one_node_is_retained() -> None:
    reference = np.zeros((SCREEN_REFERENCE_COUNT, GRID_SIZE))
    observed = np.ones((1, GRID_SIZE))
    retained = grid_index(40, 4, 2)
    observed[0, retained] = 0.0
    (screen,) = screen_cases(("case",), observed, reference)
    assert screen.status == "ready"
    assert screen.candidate_indices == (retained,)
    assert screen.q_values is not None
    assert screen.q_values[0] == pytest.approx(GAMMA)
    assert screen.q_values[retained] == 1.0


def test_effect_exact_point_zero_four_boundary_declares_and_next_rank_does_not() -> None:
    node = grid_index(40, 4, 2)
    screen = _ready("case", (node,))
    declared = combine_casewise_effect_tests(
        (screen,), (1.0,), {node: _effect_table(39)}, max_candidates=10
    ).decisions[0]
    assert isinstance(declared, CaseDecision)
    assert declared.status == "declared"
    assert declared.p_value == pytest.approx(ALPHA)
    assert len(declared.node_pvalues) == 1
    assert declared.node_pvalues[0][0] == node
    assert declared.node_pvalues[0][1] == pytest.approx(0.04)

    retained = combine_casewise_effect_tests(
        (screen,), (1.0,), {node: _effect_table(40)}, max_candidates=10
    ).decisions[0]
    assert retained.status == "not_declared"
    assert retained.p_value == pytest.approx(0.051)


def test_empty_over_cap_missing_and_failed_inputs_all_abstain() -> None:
    node = grid_index(40, 4, 2)
    empty = ScreenResult("empty", "empty", (), np.full(GRID_SIZE, GAMMA))
    inconsistent_ready_empty = ScreenResult(
        "ready-empty", "ready", (), np.full(GRID_SIZE, GAMMA)
    )
    over = _ready("over", (node, node + 1))
    missing = _ready("missing", (node,))
    failed = _ready("failed", (node + 1,))
    result = combine_casewise_effect_tests(
        (empty, inconsistent_ready_empty, over, missing, failed),
        (1.0, 1.0, 1.0, 1.0, np.nan),
        {},
        max_candidates=1,
    )
    assert [decision.status for decision in result.decisions] == [
        "abstain_empty",
        "abstain_empty",
        "abstain_over_cap",
        "abstain_missing_effect_table",
        "abstain_no_fit",
    ]
    assert all(decision.p_value == 1.0 and not decision.declared for decision in result.decisions)

    (missing_screen,) = screen_cases(("missing-screen",), np.zeros((1, GRID_SIZE)), None)
    decision = combine_casewise_effect_tests(
        (missing_screen,), (0.0,), {}, max_candidates=1
    ).decisions[0]
    assert decision.status == "abstain_missing_screen_table"

    bad_reference = {node: np.full(EFFECT_REFERENCE_COUNT, np.nan)}
    no_fit = combine_casewise_effect_tests(
        (_ready("bad-reference", (node,)),),
        (0.0,),
        bad_reference,
        max_candidates=1,
    ).decisions[0]
    assert no_fit.status == "abstain_no_fit"


def test_four_cases_reuse_the_union_of_node_tables_but_remain_casewise() -> None:
    screens = (
        _ready("A", (1, 2)),
        _ready("B", (2, 3)),
        _ready("C", (3,)),
        _ready("D", (1, 3)),
    )
    assert required_effect_nodes(screens, max_candidates=2) == (1, 2, 3)
    tables = {index: _effect_table(0) for index in (1, 2, 3)}
    result = combine_casewise_effect_tests(
        screens, (1.0, 1.0, 1.0, 1.0), tables, max_candidates=2
    )
    assert result.required_effect_nodes == (1, 2, 3)
    assert result.available_effect_nodes == (1, 2, 3)
    assert [decision.case_id for decision in result.decisions] == ["A", "B", "C", "D"]
    assert all(decision.status == "declared" for decision in result.decisions)


def test_clamped_effect_statistic_is_nonnnegative_and_rejects_failed_fits() -> None:
    assert clamped_effect_statistic(-10.0, -9.0) == 0.0
    assert clamped_effect_statistic(-8.0, -9.0) == 2.0
    with pytest.raises(ValueError, match="finite"):
        clamped_effect_statistic(np.nan, -9.0)


def test_all_designations_of_toy_exchangeable_data_are_superuniform() -> None:
    # Conditional on every possible four-value multiset, designate each value
    # once as observed and the other three as references.  Inclusive ties can
    # only reduce the fraction of attainable p-values below a threshold.
    for values in itertools.product((0.0, 1.0, 2.0), repeat=4):
        pvalues = []
        for observed_index in range(4):
            references = values[:observed_index] + values[observed_index + 1 :]
            pvalues.append(inclusive_plus_one_pvalue(values[observed_index], references))
        for threshold in (0.25, 0.5, 0.75, 1.0):
            assert np.mean(np.asarray(pvalues) <= threshold) <= threshold + 1e-12
