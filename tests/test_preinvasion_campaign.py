"""Mechanical generator controls use no registered sixteen-history outcomes."""

import numpy as np

from latent_landscapes.preinvasion_campaign import (
    hazard_box_certificate,
    loss_times,
    panel_truths,
    seed_records,
)


def test_cohort_loss_before_at_and_after_invasion() -> None:
    values = loss_times(
        np.array([0.0, 0.0, 10.0, np.inf]),
        np.full(4, 0.002),
        3.0,
        np.array([0.1, 0.12, 0.2, 0.2]),
    )
    np.testing.assert_allclose(values, [-10, 0, 20, 40], atol=1e-12)


def test_null_loss_invariant_to_arrival() -> None:
    values = loss_times(np.array([0, 5, 100, np.inf]), np.full(4, 0.002), 1, np.full(4, 0.2))
    np.testing.assert_allclose(values, 40)


def test_public_seed_ledger_and_crossing() -> None:
    cells = panel_truths()
    assert len(cells) == 16
    assert len({(r.effect, r.mean_hazard, r.beta, r.detection_sd) for r in cells}) == 16
    first = seed_records()
    assert first == seed_records()
    streams = [value for row in first for value in row["streams"].values()]
    assert len(set(streams)) == 80


def test_interval_bound_encloses_dense_off_grid_values() -> None:
    whole = np.array([-1.0, -0.7, 0.2, 1.5])
    sites = np.array([-0.7, 1.5])
    bound = hazard_box_certificate(whole, sites)
    actual = max(
        float(np.max(0.006 * np.exp(b * sites) / np.exp(b * whole).mean()))
        for b in np.linspace(-2, 2, 1003)
    )
    assert bound["site_hazard_upper"] >= actual
