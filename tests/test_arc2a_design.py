from __future__ import annotations

import math

from latent_landscapes.arc2a_design import (
    SOBOL_SCRAMBLE_SEED,
    campaign_truths,
    truths_for_block,
)


def test_nested_arc2a_design_is_exact_and_complete() -> None:
    pilot = truths_for_block("pilot")
    prospective = truths_for_block("prospective")

    assert SOBOL_SCRAMBLE_SEED == 20260829
    assert tuple(row.condition_id for row in (*pilot, *prospective)) == tuple(
        f"S{index:02d}" for index in range(1, 33)
    )
    assert math.isclose(pilot[0].rho, 0.8568331330357489)
    assert math.isclose(pilot[0].eta, 1.751764145679772)
    assert math.isclose(pilot[0].probability, 0.46585634341463444)
    assert math.isclose(prospective[0].rho, 0.9541014084363242)
    assert math.isclose(prospective[0].eta, 1.3206970740575343)
    assert math.isclose(prospective[0].probability, 0.476198835670948)
    assert tuple(row.condition_id for row in campaign_truths("pilot"))[-1] == "D00"
    assert len(campaign_truths("prospective")) == 16
