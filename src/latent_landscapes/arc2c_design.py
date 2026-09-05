"""Approved six-case spread-speed and prey-effect bridge."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MASTER_SEED = 20260905
BACKGROUND_HAZARD = 0.002
BACKGROUND_RISK = float(-np.expm1(-60.0 * BACKGROUND_HAZARD))
DETECTION_PROBABILITY = 0.65
LANES = ("known_speed", "estimated_speed")
RHO_GRID = tuple(float(value) for value in np.exp2(np.linspace(-2.0, 2.0, 201)))
EFFECT_GRID = tuple(float(value) for value in np.linspace(1.0, 10.0, 181))


@dataclass(frozen=True, slots=True)
class BridgeTruth:
    condition_id: str
    rho: float
    effect: float
    role: str


TRUTHS = tuple(
    BridgeTruth(f"{wave}_{int(effect)}", rho, effect, role)
    for wave, rho in (("usual", 1.0), ("slow", 0.5))
    for effect, role in ((1.0, "null"), (3.0, "transition_candidate"), (5.0, "strong"))
)


@dataclass(frozen=True, slots=True)
class BridgeConfig:
    master_seed: int = MASTER_SEED
    bank_size: int = 4096
    calibration_replicates: int = 250
    validation_replicates: int = 250
    calibration_rank: int = 239
    rhos: tuple[float, ...] = RHO_GRID
    effects: tuple[float, ...] = EFFECT_GRID

    def __post_init__(self) -> None:
        if min(self.bank_size, self.calibration_replicates, self.validation_replicates) <= 0:
            raise ValueError("bank and replicate counts must be positive")
        if not 1 <= self.calibration_rank <= self.calibration_replicates:
            raise ValueError("calibration rank is outside the ensemble")
        for values, required in ((self.rhos, (0.5, 1.0)), (self.effects, (1.0, 3.0, 5.0))):
            array = np.asarray(values)
            if (
                not np.isfinite(array).all()
                or (array <= 0).any()
                or (np.diff(array) <= 0).any()
                or not all(value in values for value in required)
            ):
                raise ValueError("candidate grids must be ordered and contain generating values")

    @property
    def is_production(self) -> bool:
        return self == BridgeConfig()


def smoke_config() -> BridgeConfig:
    return BridgeConfig(
        bank_size=16,
        calibration_replicates=4,
        validation_replicates=4,
        calibration_rank=4,
        rhos=(0.25, 0.5, 1.0, 2.0, 4.0),
        effects=(1.0, 2.0, 3.0, 5.0, 7.0, 10.0),
    )


def timing_config() -> BridgeConfig:
    return BridgeConfig(calibration_replicates=2, validation_replicates=2, calibration_rank=2)
