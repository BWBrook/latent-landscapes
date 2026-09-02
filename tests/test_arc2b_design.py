from __future__ import annotations

import math

from latent_landscapes.arc2b_design import (
    CONTINUOUS_TRUTHS,
    NEUTRAL_CONTROL,
    REFERENCE_CONTROL,
    SOBOL_SCRAMBLE_SEED,
    campaign_truths,
    truths_for_block,
)


def test_arc2b_design_is_nested_and_in_domain() -> None:
    assert SOBOL_SCRAMBLE_SEED == 20260831
    truths = (*truths_for_block("pilot"), *truths_for_block("prospective"))
    assert tuple(row.condition_id for row in truths) == tuple(f"S{i:02d}" for i in range(1, 33))
    assert len(CONTINUOUS_TRUTHS) == 32
    assert all(1.5 <= row.effect_multiplier <= 6.0 for row in truths)
    assert all(0.05 <= row.background_risk <= 0.20 for row in truths)
    assert all(0.35 <= row.prey_detection_probability <= 0.85 for row in truths)
    assert truths[0].effect_multiplier == 4.450357467448053


def test_controls_are_outside_surface_and_reference_hazard_reconciles() -> None:
    assert tuple(row.condition_id for row in campaign_truths("pilot")[-2:]) == ("R00", "N00")
    assert campaign_truths("prospective") == truths_for_block("prospective")
    assert REFERENCE_CONTROL.effect_multiplier == 5.0
    assert NEUTRAL_CONTROL.effect_multiplier == 1.0
    assert math.isclose(REFERENCE_CONTROL.background_hazard, 0.002)
    assert REFERENCE_CONTROL.background_risk == NEUTRAL_CONTROL.background_risk
