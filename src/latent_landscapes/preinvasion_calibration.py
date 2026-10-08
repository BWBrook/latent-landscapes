"""Finite-grid nuisance screening and exact Monte Carlo rank decisions.

This module contains no simulator and constructs no reference campaign.  It
freezes the proposed Goal 056 nuisance grid, the local pre-invasion screening
statistic, and the decision arithmetic that a future calibration campaign may
use.  Likelihood evaluation remains a caller-supplied operation.

The screen inverts nodewise Monte Carlo tests.  The subsequent effect test is
the Berger--Boos union-bound construction: a true on-grid nuisance is excluded
with probability at most ``GAMMA`` and, while retained, its inclusive plus-one
effect p-value is tested at ``ALPHA - GAMMA``.  Empty, incomplete, numerically
failed, or over-budget calculations abstain conservatively.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol, cast

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]

BETA_GRID = tuple(float(value) for value in np.linspace(-2.0, 2.0, 81))
MU_GRID = (0.0005, 0.001, 0.0016, 0.002, 0.0025, 0.0032, 0.004, 0.005, 0.006)
DETECTION_SD_GRID = (0.0, 0.1, 0.2, 0.3, 0.4)
GRID_SHAPE = (len(BETA_GRID), len(MU_GRID), len(DETECTION_SD_GRID))
GRID_SIZE = math.prod(GRID_SHAPE)

SCREEN_REFERENCE_COUNT = 99
EFFECT_REFERENCE_COUNT = 999
GAMMA = 0.01
ALPHA = 0.05

# Subtracting this fixed, scale-aware tolerance from the observed statistic can
# only add reference exceedances relative to an exact >= comparison.  It is
# therefore conservative for both screening and effect ranks.
TIE_ATOL = 1e-10
TIE_RTOL = 1e-12

ScreenStatus = Literal["ready", "empty", "missing_screen_table", "no_fit"]
DecisionStatus = Literal[
    "declared",
    "not_declared",
    "abstain_empty",
    "abstain_over_cap",
    "abstain_missing_screen_table",
    "abstain_missing_effect_table",
    "abstain_no_fit",
]


@dataclass(frozen=True, slots=True)
class NuisanceNode:
    beta: float
    mu: float
    detection_sd: float


NUISANCE_GRID = tuple(
    NuisanceNode(beta, mu, detection_sd)
    for beta in BETA_GRID
    for mu in MU_GRID
    for detection_sd in DETECTION_SD_GRID
)


class PreLogLikelihood(Protocol):
    """One pre-invasion point log likelihood supplied by the caller."""

    def __call__(
        self,
        data: Any,
        *,
        beta: float,
        mu: float,
        detection_sd: float,
    ) -> float: ...


@dataclass(frozen=True, slots=True)
class ScreenResult:
    case_id: str
    status: ScreenStatus
    candidate_indices: tuple[int, ...]
    q_values: FloatArray | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class CaseDecision:
    case_id: str
    status: DecisionStatus
    p_value: float
    declared: bool
    candidate_indices: tuple[int, ...]
    node_pvalues: tuple[tuple[int, float], ...]
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class CasewiseCalibration:
    """Casewise results sharing one effect-reference table per nuisance node."""

    decisions: tuple[CaseDecision, ...]
    required_effect_nodes: tuple[int, ...]
    available_effect_nodes: tuple[int, ...]


def grid_index(beta_index: int, mu_index: int, detection_sd_index: int) -> int:
    """Return the stable beta-major flattened grid index."""
    indices = (beta_index, mu_index, detection_sd_index)
    if any(index < 0 or index >= size for index, size in zip(indices, GRID_SHAPE, strict=True)):
        raise IndexError("nuisance-grid coordinate is outside the registered domain")
    return int(np.ravel_multi_index(indices, GRID_SHAPE))


def grid_coordinates(index: int) -> tuple[int, int, int]:
    if index < 0 or index >= GRID_SIZE:
        raise IndexError("nuisance-grid index is outside the registered domain")
    coordinates = tuple(int(value) for value in np.unravel_index(index, GRID_SHAPE))
    return cast(tuple[int, int, int], coordinates)


def axis_adjacent_indices(index: int) -> tuple[int, ...]:
    """Return the node itself and its immediate axis-adjacent grid nodes."""
    coordinates = list(grid_coordinates(index))
    output = [index]
    for axis, size in enumerate(GRID_SHAPE):
        for step in (-1, 1):
            neighbour = coordinates.copy()
            neighbour[axis] += step
            if 0 <= neighbour[axis] < size:
                output.append(grid_index(*neighbour))
    return tuple(output)


def evaluate_preloglikelihood_surface(data: Any, likelihood: PreLogLikelihood) -> FloatArray:
    """Evaluate the complete public nuisance grid in its frozen order."""
    values = np.empty(GRID_SIZE, dtype=np.float64)
    for index, node in enumerate(NUISANCE_GRID):
        values[index] = float(
            likelihood(
                data,
                beta=node.beta,
                mu=node.mu,
                detection_sd=node.detection_sd,
            )
        )
    if not np.isfinite(values).all():
        raise ValueError("pre-invasion likelihood surface contains a non-finite value")
    return values


def local_contrast_at_node(data: Any, index: int, likelihood: PreLogLikelihood) -> float:
    """Evaluate one local screen statistic without fitting the full grid."""
    neighbours = axis_adjacent_indices(index)
    values = []
    for neighbour in neighbours:
        node = NUISANCE_GRID[neighbour]
        values.append(
            float(
                likelihood(
                    data,
                    beta=node.beta,
                    mu=node.mu,
                    detection_sd=node.detection_sd,
                )
            )
        )
    array = np.asarray(values, dtype=np.float64)
    if not np.isfinite(array).all():
        raise ValueError("local pre-invasion likelihood contains a non-finite value")
    return float(2.0 * max(0.0, float(array.max() - array[0])))


def local_contrasts(pre_loglikelihoods: Any) -> FloatArray:
    """Return local contrasts for one or more flattened grid surfaces.

    The final input dimension is the registered 3,645-node grid.  Leading
    dimensions are arbitrary history or batch dimensions.  Only the centre and
    its immediate predecessor/successor on each of the three axes enter a node's
    contrast; maxima do not propagate beyond one grid step.
    """
    values = np.asarray(pre_loglikelihoods, dtype=np.float64)
    if values.ndim < 1 or values.shape[-1] != GRID_SIZE:
        raise ValueError(f"pre-invasion surfaces must end in {GRID_SIZE} grid nodes")
    if not np.isfinite(values).all():
        raise ValueError("pre-invasion surfaces must be finite")
    shaped = values.reshape((*values.shape[:-1], *GRID_SHAPE))
    best = shaped.copy()
    best[..., 1:, :, :] = np.maximum(best[..., 1:, :, :], shaped[..., :-1, :, :])
    best[..., :-1, :, :] = np.maximum(best[..., :-1, :, :], shaped[..., 1:, :, :])
    best[..., :, 1:, :] = np.maximum(best[..., :, 1:, :], shaped[..., :, :-1, :])
    best[..., :, :-1, :] = np.maximum(best[..., :, :-1, :], shaped[..., :, 1:, :])
    best[..., :, :, 1:] = np.maximum(best[..., :, :, 1:], shaped[..., :, :, :-1])
    best[..., :, :, :-1] = np.maximum(best[..., :, :, :-1], shaped[..., :, :, 1:])
    result: FloatArray = (2.0 * np.maximum(best - shaped, 0.0)).reshape(values.shape)
    return result


def _tolerance(observed: Any) -> FloatArray:
    values = np.asarray(observed, dtype=np.float64)
    return TIE_ATOL + TIE_RTOL * np.maximum(1.0, np.abs(values))


def inclusive_plus_one_pvalue(observed: float, reference: Any) -> float:
    """Return an inclusive, conservatively tie-tolerant upper-tail p-value."""
    obs = float(observed)
    refs = np.asarray(reference, dtype=np.float64)
    if not math.isfinite(obs) or refs.ndim != 1 or not refs.size or not np.isfinite(refs).all():
        raise ValueError("observed and reference statistics must be finite and nonempty")
    count = int(np.sum(refs >= obs - float(_tolerance(obs))))
    return (count + 1.0) / (len(refs) + 1.0)


def clamped_effect_statistic(unrestricted_loglikelihood: float, null_loglikelihood: float) -> float:
    """Freeze a nonnegative statistic when numerical maximizations are nonnested.

    Scientifically the unrestricted domain contains the null.  The numerical
    optimizer can nevertheless return a slightly lower unrestricted maximum.
    Taking the maximum with the fitted null is a deterministic part of the
    statistic and must be applied to observed and reference histories alike.
    """
    unrestricted = float(unrestricted_loglikelihood)
    null = float(null_loglikelihood)
    if not math.isfinite(unrestricted) or not math.isfinite(null):
        raise ValueError("effect-statistic likelihoods must be finite")
    return 2.0 * max(0.0, unrestricted - null)


def screen_cases(
    case_ids: Sequence[str],
    observed_contrasts: Any,
    reference_contrasts: Any | None,
) -> tuple[ScreenResult, ...]:
    """Invert the 99-reference nodewise tests for each observed case."""
    identifiers = tuple(str(value) for value in case_ids)
    if not identifiers or len(set(identifiers)) != len(identifiers):
        raise ValueError("case identifiers must be nonempty and unique")
    observed = np.asarray(observed_contrasts, dtype=np.float64)
    if observed.shape != (len(identifiers), GRID_SIZE):
        raise ValueError("observed contrasts do not match cases and nuisance grid")
    if reference_contrasts is None:
        return tuple(
            ScreenResult(identifier, "missing_screen_table", (), None, "screen table is absent")
            for identifier in identifiers
        )
    reference = np.asarray(reference_contrasts, dtype=np.float64)
    if reference.shape != (SCREEN_REFERENCE_COUNT, GRID_SIZE):
        raise ValueError("screen table must contain exactly 99 rows at every nuisance node")
    if not np.isfinite(reference).all() or (reference < -TIE_ATOL).any():
        return tuple(
            ScreenResult(identifier, "no_fit", (), None, "screen table contains a failed fit")
            for identifier in identifiers
        )

    output = []
    for case, row in zip(identifiers, observed, strict=True):
        if not np.isfinite(row).all() or (row < -TIE_ATOL).any():
            output.append(ScreenResult(case, "no_fit", (), None, "observed screen fit failed"))
            continue
        threshold = row[None, :] - _tolerance(row)[None, :]
        q_values = (1.0 + np.sum(reference >= threshold, axis=0)) / (
            SCREEN_REFERENCE_COUNT + 1.0
        )
        q_values.setflags(write=False)
        candidates = tuple(int(index) for index in np.flatnonzero(q_values > GAMMA))
        status: ScreenStatus = "ready" if candidates else "empty"
        reason = None if candidates else "the nuisance confidence set is empty"
        output.append(ScreenResult(case, status, candidates, q_values, reason))
    return tuple(output)


def required_effect_nodes(
    screens: Sequence[ScreenResult], *, max_candidates: int
) -> tuple[int, ...]:
    """Return the union of nodes needed by casewise screens within the cost cap."""
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    if any(
        index < 0 or index >= GRID_SIZE
        for screen in screens
        for index in screen.candidate_indices
    ):
        raise ValueError("screen contains an invalid nuisance-grid index")
    nodes = {
        index
        for screen in screens
        if screen.status == "ready" and len(screen.candidate_indices) <= max_candidates
        for index in screen.candidate_indices
    }
    return tuple(sorted(nodes))


def combine_casewise_effect_tests(
    screens: Sequence[ScreenResult],
    observed_effect_statistics: Sequence[float],
    effect_reference_tables: Mapping[int, Any],
    *,
    max_candidates: int,
) -> CasewiseCalibration:
    """Apply casewise effect tests while reusing node tables over their union.

    The returned p-values are casewise.  Reusing a reference table at a node
    shared by several cases induces dependence but does not create a joint or
    familywise 5% claim.
    """
    records = tuple(screens)
    observed = np.asarray(observed_effect_statistics, dtype=np.float64)
    if observed.shape != (len(records),):
        raise ValueError("one observed effect statistic is required per screen")
    needed = required_effect_nodes(records, max_candidates=max_candidates)

    validated: dict[int, FloatArray] = {}
    invalid_nodes: set[int] = set()
    for index in needed:
        if index not in effect_reference_tables:
            continue
        values = np.asarray(effect_reference_tables[index], dtype=np.float64)
        if values.shape != (EFFECT_REFERENCE_COUNT,):
            continue
        if not np.isfinite(values).all() or (values < -TIE_ATOL).any():
            invalid_nodes.add(index)
            continue
        validated[index] = values

    decisions = []
    for screen, statistic in zip(records, observed, strict=True):
        candidates = screen.candidate_indices
        if screen.status == "missing_screen_table":
            decisions.append(_abstention(screen, "abstain_missing_screen_table", screen.reason))
            continue
        if (
            screen.status == "no_fit"
            or not math.isfinite(float(statistic))
            or statistic < -TIE_ATOL
        ):
            decisions.append(_abstention(screen, "abstain_no_fit", "a required fit failed"))
            continue
        if screen.status == "empty" or (screen.status == "ready" and not candidates):
            reason = screen.reason or "the nuisance confidence set is empty"
            decisions.append(_abstention(screen, "abstain_empty", reason))
            continue
        if len(candidates) > max_candidates:
            decisions.append(
                _abstention(
                    screen,
                    "abstain_over_cap",
                    f"{len(candidates)} candidates exceed the registered cap {max_candidates}",
                )
            )
            continue
        if any(index in invalid_nodes for index in candidates):
            decisions.append(
                _abstention(screen, "abstain_no_fit", "an effect reference fit failed")
            )
            continue
        missing = tuple(index for index in candidates if index not in validated)
        if missing:
            decisions.append(
                _abstention(
                    screen,
                    "abstain_missing_effect_table",
                    f"effect reference table is missing at {len(missing)} candidate nodes",
                )
            )
            continue

        node_values = tuple(
            (index, inclusive_plus_one_pvalue(float(statistic), validated[index]))
            for index in candidates
        )
        p_value = min(1.0, GAMMA + max(value for _, value in node_values))
        declared = p_value <= ALPHA
        decisions.append(
            CaseDecision(
                screen.case_id,
                "declared" if declared else "not_declared",
                p_value,
                declared,
                candidates,
                node_values,
            )
        )
    return CasewiseCalibration(tuple(decisions), needed, tuple(sorted(validated)))


def _abstention(
    screen: ScreenResult, status: DecisionStatus, reason: str | None
) -> CaseDecision:
    return CaseDecision(screen.case_id, status, 1.0, False, screen.candidate_indices, (), reason)
