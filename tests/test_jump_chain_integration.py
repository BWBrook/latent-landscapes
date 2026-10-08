"""Controls for jump-chain holding-time integration."""

from __future__ import annotations

import numpy as np
import pytest

from latent_landscapes.conditional_reference import (
    enumerate_jump_chains,
    integrate_reference,
    phase_generator,
    target_generator,
)
from latent_landscapes.jump_chain_integration import (
    average_jump_curves,
    build_jump_curves,
    build_jump_integration,
    curves_to_integration,
    sample_jump_chain,
)


def test_sampler_stops_at_source_reachable_component_and_replays() -> None:
    # Nodes 3--4 form an unseeded component and node 5 is isolated, matching
    # the production convention that water identifiers have no graph edges.
    edges = ((0, 1, 2.0), (1, 2, 4.0), (3, 4, 1.0))
    first = sample_jump_chain(6, edges, (0,), np.random.default_rng(91))
    second = sample_jump_chain(6, edges, (0,), np.random.default_rng(91))
    assert first == second
    assert first == ((1, 2), (0.5, 0.25))


def test_one_order_matches_dense_phase_reference_for_all_masses_and_moments() -> None:
    order = (1, 2, 3)
    rates = (1.9, 2.4, 1.3)
    sites = (0, 1, 2, 3)
    site_ids = tuple(f"v{node}" for node in sites)
    rhos = (0.5, 1.0, 2.0)
    effects = (1.0, 3.0, 5.0)
    observed = build_jump_integration(
        order,
        rates,
        sites,
        site_ids,
        rhos,
        effects,
        source_nodes=(0,),
    )
    expected = integrate_reference(
        [None, *(phase_generator(rates[:index]) for index in range(1, 4))],
        site_ids,
        rhos,
        effects,
    )
    np.testing.assert_allclose(
        observed.category_mass, expected.category_mass, rtol=2e-11, atol=2e-13
    )
    for actual, reference in zip(observed.survival_moments, expected.survival_moments, strict=True):
        np.testing.assert_allclose(actual, reference, rtol=2e-11, atol=2e-13)


def test_exhaustive_order_mixture_matches_full_infected_set_ctmc() -> None:
    edges = ((0, 1, 7.0), (1, 2, 12.0), (2, 3, 8.0), (3, 0, 17.0), (1, 3, 9.0))
    sources = (0,)
    sites = tuple(range(4))
    site_ids = tuple(f"v{node}" for node in sites)
    rhos = (0.5, 1.0, 2.0)
    effects = (1.0, 3.0, 5.0)
    chains = enumerate_jump_chains(4, edges, sources)
    curves = [
        build_jump_curves(
            order,
            rates,
            sites,
            site_ids,
            rhos,
            source_nodes=sources,
        )
        for order, rates, _ in chains
    ]
    averaged = average_jump_curves(curves, (weight for _, _, weight in chains))
    observed = curves_to_integration(averaged, effects)
    expected = integrate_reference(
        [None, *(target_generator(4, edges, sources, target) for target in range(1, 4))],
        site_ids,
        rhos,
        effects,
    )
    np.testing.assert_allclose(
        observed.category_mass, expected.category_mass, rtol=1e-10, atol=2e-13
    )
    for actual, reference in zip(observed.survival_moments, expected.survival_moments, strict=True):
        np.testing.assert_allclose(actual, reference, rtol=1e-10, atol=2e-13)
    assert averaged.diagnostics.draw_count == len(chains)
    assert averaged.diagnostics.total_weight == pytest.approx(1.0)


def test_unequal_hierarchical_average_and_diagnostics_preserve_source_atoms() -> None:
    sites = (0, 1, 2)
    ids = ("source", "near", "far")
    rhos = (1.0,)
    curves = (
        build_jump_curves((1, 2), (1.0, 1.0), sites, ids, rhos, source_nodes=(0,)),
        build_jump_curves((2, 1), (1.3, 0.8), sites, ids, rhos, source_nodes=(0,)),
        build_jump_curves((1, 2), (0.7, 1.6), sites, ids, rhos, source_nodes=(0,)),
    )
    direct = average_jump_curves(curves)
    pair = average_jump_curves(curves[:2])
    hierarchical = average_jump_curves((pair, curves[2]))
    np.testing.assert_allclose(hierarchical.local_moments, direct.local_moments, rtol=0, atol=1e-16)
    np.testing.assert_allclose(
        hierarchical.final_survival, direct.final_survival, rtol=0, atol=1e-16
    )
    assert hierarchical.diagnostics.draw_count == 3
    assert hierarchical.diagnostics.total_weight == pytest.approx(3.0)
    assert hierarchical.diagnostics.category_sum_error_max < 1e-11
    assert hierarchical.diagnostics.local_taylor_relative_remainder_bound < 2e-16
    assert hierarchical.diagnostics.local_moment_tail_bound_max >= 0.0
    assert hierarchical.diagnostics.tilted_uniformization_error_bound_sum >= 0.0
    integration = curves_to_integration(hierarchical, (1.0, 10.0))
    np.testing.assert_array_equal(integration.category_mass[0, 0], (1.0, 0, 0, 0, 0, 0, 0))
    assert integration.category_mass[0, 2, 5] > 0.0


def test_absent_site_cannot_be_silently_reclassified_as_a_source() -> None:
    with pytest.raises(ValueError, match="exactly the supplied sources"):
        build_jump_curves(
            (1, 2),
            (1.0, 1.0),
            (0, 1, 3),
            ("source", "reached", "unreachable"),
            (1.0,),
            source_nodes=(0,),
        )
    with pytest.raises(ValueError, match="equal length"):
        average_jump_curves(
            [
                build_jump_curves(
                    (1,), (1.0,), (0, 1), ("source", "site"), (1.0,), source_nodes=(0,)
                )
            ],
            (0.5, 0.5),
        )


def test_effect_expansion_rejects_values_outside_diagnostic_domain() -> None:
    curves = build_jump_curves((1,), (1.0,), (0, 1), ("source", "site"), (1.0,), source_nodes=(0,))
    for effects in ((0.5, 1.0), (1.0, 10.1)):
        with pytest.raises(ValueError, match=r"interval \[1, 10\]"):
            curves_to_integration(curves, effects)
    with pytest.raises(ValueError, match="accepted Goal 048 value"):
        curves_to_integration(curves, (1.0, 10.0), background_hazard=0.003)

    accepted = curves_to_integration(curves, (1.0, 10.0))
    assert accepted.effects == (1.0, 10.0)
