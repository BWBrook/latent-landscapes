"""Union resource planning and fit-status propagation for later effect tables.

This module generates no histories. A caller must obtain a ready plan before
building tables; an over-cap union cannot be replaced by a cheaper subset.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.preinvasion_calibration import (
    GRID_SIZE,
    CaseDecision,
    CasewiseCalibration,
    ScreenResult,
    combine_casewise_effect_tests,
    required_effect_nodes,
)


@dataclass(frozen=True)
class EffectReferencePlan:
    status: Literal["ready", "abstain_over_cap"]
    union_indices: tuple[int, ...]
    requested_indices: tuple[int, ...]
    max_union_candidates: int


def plan_effect_references(
    screens: Sequence[ScreenResult], *, max_union_candidates: int
) -> EffectReferencePlan:
    """Apply one resource cap before any shared effect-table construction."""
    if type(max_union_candidates) is not int or max_union_candidates < 1:
        raise ValueError("max_union_candidates must be a positive integer")
    records = tuple(screens)
    if (
        not records
        or any(not item.case_id for item in records)
        or len({item.case_id for item in records}) != len(records)
    ):
        raise ValueError("screens must contain unique, nonempty case identifiers")
    union = required_effect_nodes(records, max_candidates=GRID_SIZE)
    if len(union) > max_union_candidates:
        return EffectReferencePlan("abstain_over_cap", union, (), max_union_candidates)
    return EffectReferencePlan("ready", union, union, max_union_candidates)


@dataclass(frozen=True)
class EffectFitBatch:
    """Null/free scores and their separate optimizer statuses, in row order."""

    null_loglikelihood: Any
    free_loglikelihood: Any
    null_status: Sequence[str]
    free_status: Sequence[str]

    def statistics(self) -> NDArray[np.float64]:
        null = np.asarray(self.null_loglikelihood, dtype=np.float64)
        free = np.asarray(self.free_loglikelihood, dtype=np.float64)
        null_status = np.asarray(self.null_status, dtype=str)
        free_status = np.asarray(self.free_status, dtype=str)
        if null.ndim != 1 or any(
            item.shape != null.shape for item in (free, null_status, free_status)
        ):
            raise ValueError("scores and both fit statuses must have matching row shapes")
        good = (
            np.isfinite(null)
            & np.isfinite(free)
            & (null_status == "converged")
            & (free_status == "converged")
        )
        result = np.full(null.shape, math.nan, dtype=np.float64)
        result[good] = 2.0 * np.maximum(0.0, free[good] - null[good])
        return result


def combine_union_capped_effect_tests(
    screens: Sequence[ScreenResult],
    observed_fits: EffectFitBatch,
    reference_fits: Mapping[int, EffectFitBatch],
    *,
    max_union_candidates: int,
) -> CasewiseCalibration:
    """Combine casewise ranks only after union and numerical gates pass.

    Failed pairs become NaN before the existing rank combiner sees their
    statistics. One failed required reference therefore abstains for every
    case requiring that node, without dropping or replacing that reference.
    The output still has casewise, not familywise, inferential meaning.
    """
    records = tuple(screens)
    plan = plan_effect_references(records, max_union_candidates=max_union_candidates)
    if plan.status == "abstain_over_cap":
        reason = (
            f"union of {len(plan.union_indices)} nodes exceeds registered cap "
            f"{max_union_candidates}"
        )
        decisions = tuple(
            CaseDecision(
                item.case_id, "abstain_over_cap", 1.0, False,
                item.candidate_indices, (), reason,
            )
            for item in records
        )
        return CasewiseCalibration(decisions, plan.union_indices, ())
    observed = observed_fits.statistics()
    tables = {
        index: reference_fits[index].statistics()
        for index in plan.requested_indices
        if index in reference_fits
    }
    return combine_casewise_effect_tests(
        records, observed.tolist(), tables, max_candidates=GRID_SIZE
    )
