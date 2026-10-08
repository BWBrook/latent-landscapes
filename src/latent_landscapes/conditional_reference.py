"""Small-graph exponential first-passage references for method development.

These dense finite-state calculations are deliberately limited to eight nodes.
They preserve the existing exponential-edge law and site-marginal likelihood;
they are not a production integration replacement.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
from scipy.linalg import expm

from latent_landscapes.arc2c_likelihood import BridgeIntegration
from latent_landscapes.goal004.observations import SURVEY_TIMES


def infection_rates(node_count, edges, infected):
    rates = np.zeros(node_count)
    for u, v, cost in edges:
        if u in infected and v not in infected:
            rates[v] += 1.0 / cost
        elif v in infected and u not in infected:
            rates[u] += 1.0 / cost
    return rates


def validate_graph(node_count, edges, sources):
    if not 2 <= node_count <= 8 or not sources or not set(sources) < set(range(node_count)):
        raise ValueError("Reference requires 2..8 nodes and a proper nonempty source set")
    pairs = set()
    for u, v, cost in edges:
        if u == v or u not in range(node_count) or v not in range(node_count):
            raise ValueError("Invalid edge endpoint")
        if not np.isfinite(cost) or cost <= 0 or tuple(sorted((u, v))) in pairs:
            raise ValueError("Edges must be unique with positive finite costs")
        pairs.add(tuple(sorted((u, v))))
    reached = set(sources)
    while True:
        more = {v for u, v, _ in edges if u in reached} | {u for u, v, _ in edges if v in reached}
        if more <= reached:
            break
        reached |= more
    if len(reached) != node_count:
        raise ValueError("Graph must be source-reachable")


def target_generator(node_count, edges, sources, target):
    """Transient infected-set generator, absorbing when target is first reached."""
    validate_graph(node_count, edges, sources)
    if target in sources or target not in range(node_count):
        raise ValueError("Target must be a non-source node")
    optional = sorted(set(range(node_count)) - set(sources) - {target})
    states = [
        frozenset(sources) | frozenset(subset)
        for count in range(len(optional) + 1)
        for subset in combinations(optional, count)
    ]
    lookup = {s: i for i, s in enumerate(states)}
    Q = np.zeros((len(states), len(states)))
    absorption = np.zeros(len(states))
    for i, infected in enumerate(states):
        rates = infection_rates(node_count, edges, infected)
        Q[i, i] = -rates.sum()
        absorption[i] = rates[target]
        for node in np.flatnonzero(rates):
            if node != target:
                Q[i, lookup[infected | {int(node)}]] = rates[node]
    return Q, absorption


def phase_generator(rates):
    rates = np.asarray(rates, dtype=float)
    if rates.ndim != 1 or len(rates) == 0 or not np.isfinite(rates).all() or (rates <= 0).any():
        raise ValueError("Holding rates must be positive and finite")
    Q = -np.diag(rates)
    if len(rates) > 1:
        Q += np.diag(rates[:-1], 1)
    absorption = np.zeros(len(rates))
    absorption[-1] = rates[-1]
    return Q, absorption


def interval_moment(Q, absorption, lower, upper, tilt=0.0):
    """E[exp(tilt*T) 1(lower<T<=upper)] without subtracting two CDFs."""
    if not 0 <= lower < upper or not np.isfinite(upper) or not np.isfinite(tilt):
        raise ValueError("Finite ordered interval and tilt required")
    size = len(absorption)
    tilted = Q + tilt * np.eye(size)
    augmented = np.zeros((size + 1, size + 1))
    augmented[:size, :size] = tilted
    augmented[:size, size] = absorption
    # Integrate only over this interval to retain very small positive tail masses.
    at_lower = expm(tilted * lower)[0]
    integral = expm(augmented * (upper - lower))[:size, size]
    return float(at_lower @ integral)


def integrate_reference(generators, site_ids, rhos, effects, background_hazard=0.002):
    """Build accepted likelihood inputs from exact phase-type arrival laws.

    A None generator represents a source node with arrival time exactly zero.
    Non-source generators are (transient Q, absorption rate) pairs at rho=1.
    """
    times = np.asarray((0.0, *SURVEY_TIMES))
    edges = [(times[c], times[c + 1]) for c in range(6)]
    masses = np.empty((len(rhos), len(generators), 7))
    moments = []
    for ri, rho in enumerate(rhos):
        current = np.zeros((len(effects), len(generators), 7, 7))
        for si, generator in enumerate(generators):
            if generator is None:
                masses[ri, si] = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
                current[:, si, :, 0] = np.exp(
                    -background_hazard * np.asarray(effects)[:, None] * times
                )
                continue
            Q, absorption = (rho * value for value in generator)
            for c, (lower, upper) in enumerate(edges):
                masses[ri, si, c] = interval_moment(Q, absorption, lower, upper)
            masses[ri, si, -1] = expm(Q * times[-1])[0].sum()
            for ei, effect in enumerate(effects):
                tilt = background_hazard * (effect - 1)
                weighted = [
                    interval_moment(Q, absorption, lower, upper, tilt) for lower, upper in edges
                ]
                for ti, time in enumerate(times):
                    for c in range(7):
                        current[ei, si, ti, c] = (
                            masses[ri, si, c] * np.exp(-background_hazard * time)
                            if c >= ti
                            else weighted[c] * np.exp(-background_hazard * effect * time)
                        )
        moments.append(current)
    return BridgeIntegration(
        tuple(rhos),
        tuple(effects),
        tuple(site_ids),
        masses,
        tuple(moments),
        "finite-state-reference",
    )


def enumerate_jump_chains(node_count, edges, sources):
    """Return all positive-probability infection orders and their holding rates."""
    validate_graph(node_count, edges, sources)

    def visit(infected, order, rates, weight):
        if len(infected) == node_count:
            yield order, rates, weight
            return
        outgoing = infection_rates(node_count, edges, infected)
        total = outgoing.sum()
        for node in np.flatnonzero(outgoing):
            yield from visit(
                infected | {int(node)},
                (*order, int(node)),
                (*rates, float(total)),
                weight * outgoing[node] / total,
            )

    return tuple(visit(frozenset(sources), (), (), 1.0))
