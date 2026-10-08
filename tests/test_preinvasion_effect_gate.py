from __future__ import annotations

from collections.abc import Iterator, Mapping

import numpy as np
import pytest

from latent_landscapes.preinvasion_calibration import GRID_SIZE, ScreenResult
from latent_landscapes.preinvasion_effect_gate import (
    EffectFitBatch,
    combine_union_capped_effect_tests,
    plan_effect_references,
)


def ready(name: str, nodes: tuple[int, ...]) -> ScreenResult:
    return ScreenResult(name, "ready", nodes, np.ones(GRID_SIZE))


def fits(n: int, *, delta: float = 0.0, failed: int | None = None) -> EffectFitBatch:
    statuses = ["converged"] * n
    if failed is not None:
        statuses[failed] = "failed_optimizer"
    return EffectFitBatch(np.zeros(n), np.full(n, delta), ["converged"] * n, statuses)


def test_union_cap_precedes_table_access_and_never_selects_a_subset() -> None:
    screens = tuple(ready(str(i), (i, i + 1)) for i in range(4))
    plan = plan_effect_references(screens, max_union_candidates=4)
    assert plan.status == "abstain_over_cap"
    assert plan.union_indices == (0, 1, 2, 3, 4)
    assert plan.requested_indices == ()

    class UnavailableTables(Mapping[int, EffectFitBatch]):
        def __getitem__(self, key: int) -> EffectFitBatch:
            raise AssertionError("an over-cap experiment must not access a table")

        def __iter__(self) -> Iterator[int]:
            raise AssertionError("an over-cap experiment must not enumerate tables")

        def __len__(self) -> int:
            raise AssertionError("an over-cap experiment must not inspect tables")

    result = combine_union_capped_effect_tests(
        screens, fits(4), UnavailableTables(), max_union_candidates=4
    )
    assert all(item.p_value == 1.0 and not item.declared for item in result.decisions)
    assert all(item.status == "abstain_over_cap" for item in result.decisions)
    assert result.available_effect_nodes == ()
    assert plan_effect_references(screens, max_union_candidates=5).requested_indices == (
        0, 1, 2, 3, 4,
    )


def test_finite_failed_observed_or_reference_fits_cannot_declare() -> None:
    screens = (ready("failed-observation", (0,)), ready("failed-reference", (1,)))
    observed = fits(2, delta=100.0, failed=0)
    result = combine_union_capped_effect_tests(
        screens, observed, {0: fits(999), 1: fits(999, failed=998)}, max_union_candidates=2
    )
    assert np.isnan(observed.statistics()[0])
    assert [item.status for item in result.decisions] == ["abstain_no_fit"] * 2
    assert all(item.p_value == 1.0 for item in result.decisions)


def test_both_statuses_and_nonfinite_scores_are_required() -> None:
    batch = EffectFitBatch(
        [0, 0, 0, np.nan, 2], [5, 5, np.inf, 5, 1],
        ["failed_optimizer", "converged", "converged", "converged", "converged"],
        ["converged", "invalid", "converged", "converged", "converged"],
    )
    assert np.isnan(batch.statistics()[:4]).all()
    assert batch.statistics()[4] == 0.0
    with pytest.raises(ValueError, match="matching row shapes"):
        EffectFitBatch([0], [0], [], ["converged"]).statistics()


def test_union_gate_preserves_rank_boundary_and_missing_or_empty_abstention() -> None:
    refs = np.zeros(999)
    refs[:39] = 1.0
    table = EffectFitBatch(np.zeros(999), refs / 2, ["converged"] * 999,
                           ["converged"] * 999)
    screens = (ready("A", (0,)), ready("B", (0,)), ready("missing", (1,)),
               ScreenResult("empty", "empty", (), None))
    result = combine_union_capped_effect_tests(
        screens, fits(4, delta=0.5), {0: table}, max_union_candidates=2
    )
    assert [item.status for item in result.decisions] == [
        "declared", "declared", "abstain_missing_effect_table", "abstain_empty",
    ]
    assert result.decisions[0].p_value == pytest.approx(0.05)
    assert result.required_effect_nodes == (0, 1)


def test_union_planning_rejects_ambiguous_inputs() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        plan_effect_references((ready("A", (1,)),), max_union_candidates=0)
    with pytest.raises(ValueError, match="unique"):
        plan_effect_references((ready("A", (1,)), ready("A", (2,))), max_union_candidates=5)
    with pytest.raises(ValueError, match="nonempty"):
        plan_effect_references((ready("", (1,)),), max_union_candidates=5)
    with pytest.raises(ValueError, match="positive integer"):
        plan_effect_references((ready("A", (1,)),), max_union_candidates=True)
    with pytest.raises(ValueError, match="invalid nuisance"):
        plan_effect_references((ready("A", (GRID_SIZE,)),), max_union_candidates=5)
