"""Frozen parameter design for the Arc 2A predator-only experiment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.stats import qmc  # type: ignore[import-untyped]

RHO_GRID = tuple(2.0 ** (-2.0 + 4.0 * index / 100.0) for index in range(101))
PROBABILITY_GRID = tuple(round(0.05 + 0.02 * index, 2) for index in range(46))
REFINED_ETA_GRID = tuple(float(value / 8) for value in range(21))

SOBOL_SCRAMBLE_SEED = 20260829
Block = Literal["pilot", "prospective"]


@dataclass(frozen=True, slots=True)
class TruthCondition:
    condition_id: str
    design_role: str
    rho: float
    eta: float
    probability: float


def _continuous_truths() -> tuple[TruthCondition, ...]:
    engine = qmc.Sobol(d=3, scramble=True, seed=SOBOL_SCRAMBLE_SEED)
    unit = np.asarray(engine.random_base2(m=5), dtype=np.float64)
    return tuple(
        TruthCondition(
            f"S{index:02d}",
            "sobol_pilot" if index <= 16 else "sobol_nested_validation",
            float(2.0 ** (-1.0 + 2.0 * float(unit_rho))),
            0.25 + 1.75 * float(unit_eta),
            0.35 + 0.50 * float(unit_probability),
        )
        for index, (unit_rho, unit_eta, unit_probability) in enumerate(unit, start=1)
    )


CONTINUOUS_TRUTHS = _continuous_truths()


def truths_for_block(block: Block) -> tuple[TruthCondition, ...]:
    """Return one nested 16-truth Sobol block."""
    return CONTINUOUS_TRUTHS[:16] if block == "pilot" else CONTINUOUS_TRUTHS[16:]


def no_resistance_diagnostic() -> TruthCondition:
    return TruthCondition("D00", "no_resistance_diagnostic", 1.0, 0.0, 0.65)


def campaign_truths(block: Block) -> tuple[TruthCondition, ...]:
    """Return the production truths for a campaign block."""
    truths = truths_for_block(block)
    return (*truths, no_resistance_diagnostic()) if block == "pilot" else truths
