"""Jump-chain Rao--Blackwellization for exponential-edge first passage.

The full infected-set process is reduced to its embedded vertex order and
independent exponential holding times.  Conditional quantities are kept as
compact, linear interval moments so that many orders can be averaged before
the rho-by-effect likelihood arrays are expanded.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace

import numpy as np
from numpy.typing import NDArray
from scipy.special import gammainc  # type: ignore[import-untyped]
from scipy.stats import poisson  # type: ignore[import-untyped]

from latent_landscapes.arc2c_design import BACKGROUND_HAZARD
from latent_landscapes.arc2c_likelihood import BridgeIntegration
from latent_landscapes.goal004.observations import SURVEY_TIMES

FloatArray = NDArray[np.float64]
Edge = tuple[int, int, float]


@dataclass(frozen=True, slots=True)
class JumpChainDiagnostics:
    """Numerical diagnostics for one order or an averaged set of orders."""

    draw_count: int
    total_weight: float
    phase_count: int
    site_count: int
    source_site_count: int
    mesh_interval_count: int
    internal_subinterval_count: int
    moment_order: int
    uniformization_rate_max: float
    holding_rate_min: float
    maximum_mesh_width: float
    maximum_poisson_mean: float
    poisson_tail_bound_sum: float
    local_moment_tail_bound_max: float
    tilted_uniformization_error_bound_sum: float
    final_probability_mass_error_max: float
    category_sum_error_max: float
    conditional_zero_category_count: int
    local_taylor_relative_remainder_bound: float


@dataclass(frozen=True, slots=True)
class JumpChainCurves:
    """Linear conditional sufficient quantities on a common physical-time mesh.

    ``local_moments[i, j, s]`` is the integral of
    ``u**j / j! * f_s(a_i + u)`` over mesh interval ``i``, where ``a_i`` is
    its start and ``f_s`` is the rho=1 arrival density.  This local basis is
    positive and makes exponential tilting accurate with a low polynomial
    order.  All arrays can be averaged directly over infection orders.
    """

    site_ids: tuple[str, ...]
    rhos: tuple[float, ...]
    survey_times: tuple[float, ...]
    interval_starts: FloatArray
    interval_ends: FloatArray
    local_moments: FloatArray
    final_survival: FloatArray
    source_sites: NDArray[np.bool_]
    chain_checksum: str
    diagnostics: JumpChainDiagnostics


def _validated_edges(node_count: int, edges: Sequence[Edge]) -> tuple[list[tuple[int, float]], ...]:
    if node_count <= 0:
        raise ValueError("node_count must be positive")
    adjacency: list[list[tuple[int, float]]] = [[] for _ in range(node_count)]
    pairs: set[tuple[int, int]] = set()
    for source, target, cost in edges:
        if (
            source == target
            or not 0 <= source < node_count
            or not 0 <= target < node_count
            or not math.isfinite(cost)
            or cost <= 0.0
        ):
            raise ValueError("edges require distinct valid endpoints and positive finite costs")
        pair = (min(source, target), max(source, target))
        if pair in pairs:
            raise ValueError("undirected edges must be unique")
        pairs.add(pair)
        rate = 1.0 / cost
        adjacency[source].append((target, rate))
        adjacency[target].append((source, rate))
    return tuple(adjacency)


def sample_jump_chain(
    node_count: int,
    edges: Sequence[Edge],
    sources: Sequence[int],
    rng: np.random.Generator,
) -> tuple[tuple[int, ...], tuple[float, ...]]:
    """Sample the embedded infection order and its rho=1 cut rates.

    Isolated or source-unreachable node identifiers are allowed (the landscape
    uses them for water).  Sampling stops when the source-reachable component
    has been exhausted.
    """

    adjacency = _validated_edges(node_count, edges)
    source_set = set(sources)
    if not source_set or any(node not in range(node_count) for node in source_set):
        raise ValueError("sources must be nonempty valid node identifiers")
    infected = np.zeros(node_count, dtype=np.bool_)
    infected[np.asarray(sorted(source_set), dtype=np.int64)] = True
    boundary_rates = np.zeros(node_count, dtype=np.float64)
    for source in source_set:
        for target, rate in adjacency[source]:
            if not infected[target]:
                boundary_rates[target] += rate

    order: list[int] = []
    holding_rates: list[float] = []
    while True:
        candidates = np.flatnonzero(boundary_rates > 0.0)
        if not len(candidates):
            break
        rates = boundary_rates[candidates]
        total = float(rates.sum())
        if not math.isfinite(total) or total <= 0.0:
            raise RuntimeError("infection boundary has an invalid total rate")
        target = int(rng.choice(candidates, p=rates / total))
        order.append(target)
        holding_rates.append(total)
        infected[target] = True
        boundary_rates[target] = 0.0
        for neighbor, rate in adjacency[target]:
            if not infected[neighbor]:
                boundary_rates[neighbor] += rate
    return tuple(order), tuple(holding_rates)


def _validate_candidates(values: Sequence[float], name: str) -> FloatArray:
    result = np.asarray(values, dtype=np.float64)
    if (
        result.ndim != 1
        or not len(result)
        or not np.isfinite(result).all()
        or np.any(result <= 0.0)
        or np.any(np.diff(result) <= 0.0)
    ):
        raise ValueError(f"{name} values must be positive, finite, and strictly increasing")
    return result


def _common_mesh(
    rhos: FloatArray, times: FloatArray, maximum_width: float
) -> tuple[FloatArray, FloatArray]:
    endpoints = np.unique(np.concatenate(([0.0], (rhos[:, None] * times[None, :]).ravel())))
    starts: list[float] = []
    ends: list[float] = []
    left = 0.0
    for right_value in endpoints[1:]:
        right = float(right_value)
        count = max(1, math.ceil((right - left) / maximum_width))
        for index in range(count):
            starts.append(left + (right - left) * index / count)
            ends.append(
                right if index + 1 == count else left + (right - left) * (index + 1) / count
            )
        left = right
    return np.asarray(starts, dtype=np.float64), np.asarray(ends, dtype=np.float64)


def _phase_step(probabilities: FloatArray, transition: FloatArray) -> FloatArray:
    phase_count = len(transition)
    result = np.empty_like(probabilities)
    result[0] = probabilities[0] * (1.0 - transition[0])
    if phase_count > 1:
        result[1:phase_count] = (
            probabilities[1:phase_count] * (1.0 - transition[1:])
            + probabilities[: phase_count - 1] * transition[: phase_count - 1]
        )
    result[phase_count] = (
        probabilities[phase_count] + probabilities[phase_count - 1] * transition[-1]
    )
    return result


def _uniformized_subinterval(
    probabilities: FloatArray,
    holding_rates: FloatArray,
    density_indices: NDArray[np.int64],
    duration: float,
    moment_order: int,
    tail_tolerance: float,
) -> tuple[FloatArray, FloatArray, float]:
    uniformization_rate = float(holding_rates.max())
    transition = holding_rates / uniformization_rate
    poisson_mean = uniformization_rate * duration
    quantile = poisson.ppf(1.0 - tail_tolerance, poisson_mean)
    if not np.isfinite(quantile):
        raise RuntimeError("Poisson truncation quantile is not finite")
    final_term = int(quantile) + 2 * moment_order + 2
    terms = np.arange(final_term + 1)
    poisson_weights = np.asarray(poisson.pmf(terms, poisson_mean), dtype=np.float64)
    integral_weights = np.empty((final_term + 1, moment_order + 1), dtype=np.float64)
    for degree in range(moment_order + 1):
        combinations = np.ones(final_term + 1, dtype=np.float64)
        for factor in range(1, degree + 1):
            combinations *= (terms + factor) / factor
        integral_weights[:, degree] = (
            combinations
            * gammainc(terms + degree + 1, poisson_mean)
            / uniformization_rate ** (degree + 1)
        )

    final_probabilities = np.zeros_like(probabilities)
    local_moments = np.zeros((moment_order + 1, len(density_indices)), dtype=np.float64)
    iterate = probabilities.copy()
    target_rates = holding_rates[density_indices]
    for term in range(final_term + 1):
        final_probabilities += poisson_weights[term] * iterate
        density = target_rates * iterate[density_indices]
        local_moments += integral_weights[term, :, None] * density[None, :]
        iterate = _phase_step(iterate, transition)
    return final_probabilities, local_moments, float(poisson.sf(final_term, poisson_mean))


def _shift_local_moments(local: FloatArray, offset: float) -> FloatArray:
    """Move a subinterval's local polynomial origin by a nonnegative offset."""

    result = np.zeros_like(local)
    for degree in range(local.shape[0]):
        for inner in range(degree + 1):
            result[degree] += (
                offset ** (degree - inner) / math.factorial(degree - inner) * local[inner]
            )
    return result


def _boundary_index(ends: FloatArray, value: float) -> int:
    if value == 0.0:
        return 0
    insertion = int(np.searchsorted(ends, value))
    candidates = [index for index in (insertion - 1, insertion) if 0 <= index < len(ends)]
    closest = min(candidates, key=lambda index: abs(float(ends[index]) - value))
    tolerance = 2e-12 * max(1.0, abs(value))
    if abs(float(ends[closest]) - value) > tolerance:
        raise RuntimeError("requested endpoint is absent from the common mesh")
    return closest + 1


def _category_masses(curves: JumpChainCurves) -> FloatArray:
    site_count = len(curves.site_ids)
    masses = np.zeros((len(curves.rhos), site_count, len(curves.survey_times) + 1))
    for rho_index, rho in enumerate(curves.rhos):
        lower = 0.0
        for category, time in enumerate(curves.survey_times):
            upper = rho * time
            start = _boundary_index(curves.interval_ends, lower)
            stop = _boundary_index(curves.interval_ends, upper)
            masses[rho_index, :, category] = curves.local_moments[start:stop, 0].sum(axis=0)
            lower = upper
        masses[rho_index, :, -1] = curves.final_survival[rho_index]
    masses[:, curves.source_sites, :] = 0.0
    masses[:, curves.source_sites, 0] = 1.0
    return masses


def build_jump_curves(
    order: Sequence[int],
    holding_rates: Sequence[float],
    site_nodes: Sequence[int],
    site_ids: Sequence[str],
    rhos: Sequence[float],
    *,
    source_nodes: Sequence[int],
    survey_times: Sequence[float] = SURVEY_TIMES,
    maximum_mesh_width: float = 0.25,
    maximum_poisson_mean: float = 50.0,
    moment_order: int = 6,
    poisson_tail_tolerance: float = 1e-14,
) -> JumpChainCurves:
    """Integrate holding times for one order into compact linear curves."""

    order_values = tuple(int(node) for node in order)
    rates = np.asarray(holding_rates, dtype=np.float64)
    nodes = tuple(int(node) for node in site_nodes)
    ids = tuple(site_ids)
    rho_values = _validate_candidates(rhos, "rho")
    times = np.asarray(survey_times, dtype=np.float64)
    if (
        len(order_values) != len(rates)
        or len(set(order_values)) != len(order_values)
        or rates.ndim != 1
        or not len(rates)
        or not np.isfinite(rates).all()
        or np.any(rates <= 0.0)
    ):
        raise ValueError("order and positive finite holding rates must agree")
    if (
        len(nodes) != len(ids)
        or not nodes
        or len(set(nodes)) != len(nodes)
        or len(set(ids)) != len(ids)
        or any(node < 0 for node in nodes)
    ):
        raise ValueError("site nodes and unique identifiers must agree")
    if (
        times.ndim != 1
        or not len(times)
        or not np.isfinite(times).all()
        or np.any(times <= 0.0)
        or np.any(np.diff(times) <= 0.0)
    ):
        raise ValueError("survey times must be positive, finite, and strictly increasing")
    if (
        not math.isfinite(maximum_mesh_width)
        or maximum_mesh_width <= 0.0
        or not math.isfinite(maximum_poisson_mean)
        or maximum_poisson_mean <= 0.0
        or not 0 < poisson_tail_tolerance < 1e-3
        or not 0 <= moment_order <= 12
    ):
        raise ValueError("uniformization and moment controls are invalid")

    supplied_sources = tuple(int(node) for node in source_nodes)
    if (
        not supplied_sources
        or len(set(supplied_sources)) != len(supplied_sources)
        or any(node < 0 for node in supplied_sources)
        or set(supplied_sources).intersection(order_values)
    ):
        raise ValueError("source nodes must be unique, nonnegative, and absent from the order")
    source_set = set(supplied_sources)
    positions = {node: index + 1 for index, node in enumerate(order_values)}
    absent_sites = {node for node in nodes if node not in positions}
    if absent_sites != ({node for node in nodes if node in source_set}):
        raise ValueError(
            "sites absent from the infection order must be exactly the supplied sources"
        )
    site_positions = np.asarray([positions.get(node, 0) for node in nodes], dtype=np.int64)
    source_sites = site_positions == 0
    non_source_sites = np.flatnonzero(~source_sites)
    density_indices = site_positions[non_source_sites] - 1
    starts, ends = _common_mesh(rho_values, times, maximum_mesh_width)
    local = np.zeros((len(starts), moment_order + 1, len(nodes)), dtype=np.float64)
    final_survival = np.full((len(rho_values), len(nodes)), np.nan, dtype=np.float64)
    final_survival[:, source_sites] = 0.0
    final_requests: dict[float, list[int]] = {}
    for rho_index, rho in enumerate(rho_values):
        final_requests.setdefault(float(rho * times[-1]), []).append(rho_index)

    probabilities = np.zeros(len(rates) + 1, dtype=np.float64)
    probabilities[0] = 1.0
    uniformization_rate = float(rates.max())
    internal_count = 0
    tail_bound = 0.0
    cumulative_tail_bound = 0.0
    local_moment_tail_bound = 0.0
    tilted_uniformization_bounds = np.zeros(len(rho_values), dtype=np.float64)
    mass_error = 0.0
    observed_maximum_mean = 0.0
    for interval, (start, end) in enumerate(zip(starts, ends, strict=True)):
        duration = float(end - start)
        split_count = max(1, math.ceil(uniformization_rate * duration / maximum_poisson_mean))
        sub_duration = duration / split_count
        combined = np.zeros((moment_order + 1, len(non_source_sites)), dtype=np.float64)
        combined_moment_error = np.zeros(moment_order + 1, dtype=np.float64)
        for subinterval in range(split_count):
            probabilities, moments, omitted = _uniformized_subinterval(
                probabilities,
                rates,
                density_indices,
                sub_duration,
                moment_order,
                poisson_tail_tolerance,
            )
            combined += _shift_local_moments(moments, subinterval * sub_duration)
            internal_count += 1
            tail_bound += omitted
            cumulative_tail_bound += omitted
            subinterval_moment_error = np.asarray(
                [
                    uniformization_rate
                    * sub_duration ** (degree + 1)
                    / math.factorial(degree)
                    * cumulative_tail_bound
                    for degree in range(moment_order + 1)
                ],
                dtype=np.float64,
            )
            offset = subinterval * sub_duration
            for degree in range(moment_order + 1):
                combined_moment_error[degree] += sum(
                    offset ** (degree - inner)
                    / math.factorial(degree - inner)
                    * subinterval_moment_error[inner]
                    for inner in range(degree + 1)
                )
            subinterval_end = float(start + (subinterval + 1) * sub_duration)
            active = subinterval_end <= rho_values * times[-1] + 2e-12
            tilts = BACKGROUND_HAZARD * 9.0 / rho_values[active]
            tilted_uniformization_bounds[active] += (
                np.exp(tilts * subinterval_end)
                * uniformization_rate
                * sub_duration
                * cumulative_tail_bound
            )
            observed_maximum_mean = max(observed_maximum_mean, uniformization_rate * sub_duration)
        local_moment_tail_bound = max(local_moment_tail_bound, float(combined_moment_error.max()))
        # Advanced indexing moves the site dimension before the moment dimension.
        local[interval, :, non_source_sites] = combined.T
        mass_error = max(mass_error, abs(float(probabilities.sum()) - 1.0))
        request_indices = final_requests.get(float(end), ())
        if request_indices:
            survival = np.cumsum(probabilities)[density_indices]
            for rho_index in request_indices:
                final_survival[rho_index, non_source_sites] = survival
    if np.isnan(final_survival).any():
        raise RuntimeError("not every rho-specific final survival was evaluated")

    digest = hashlib.sha256()
    digest.update(np.asarray(order_values, dtype=np.int64).tobytes())
    digest.update(rates.tobytes())
    digest.update(np.asarray(nodes, dtype=np.int64).tobytes())
    provisional = JumpChainCurves(
        ids,
        tuple(float(value) for value in rho_values),
        tuple(float(value) for value in times),
        starts,
        ends,
        local,
        final_survival,
        source_sites,
        digest.hexdigest(),
        JumpChainDiagnostics(
            draw_count=1,
            total_weight=1.0,
            phase_count=len(rates),
            site_count=len(nodes),
            source_site_count=int(source_sites.sum()),
            mesh_interval_count=len(starts),
            internal_subinterval_count=internal_count,
            moment_order=moment_order,
            uniformization_rate_max=uniformization_rate,
            holding_rate_min=float(rates.min()),
            maximum_mesh_width=float(np.max(ends - starts)),
            maximum_poisson_mean=observed_maximum_mean,
            poisson_tail_bound_sum=tail_bound,
            local_moment_tail_bound_max=local_moment_tail_bound,
            tilted_uniformization_error_bound_sum=float(tilted_uniformization_bounds.max()),
            final_probability_mass_error_max=mass_error,
            category_sum_error_max=math.nan,
            conditional_zero_category_count=0,
            local_taylor_relative_remainder_bound=math.nan,
        ),
    )
    masses = _category_masses(provisional)
    category_error = float(np.max(np.abs(masses.sum(axis=2) - 1.0)))
    zero_count = int(np.count_nonzero((masses == 0.0) & ~source_sites[None, :, None]))
    maximum_tilt = BACKGROUND_HAZARD * 9.0 / float(rho_values.min())
    local_argument = maximum_tilt * provisional.diagnostics.maximum_mesh_width
    taylor_bound = (
        math.exp(local_argument)
        * local_argument ** (moment_order + 1)
        / math.factorial(moment_order + 1)
    )
    return replace(
        provisional,
        diagnostics=replace(
            provisional.diagnostics,
            category_sum_error_max=category_error,
            conditional_zero_category_count=zero_count,
            local_taylor_relative_remainder_bound=taylor_bound,
        ),
    )


def _same_curve_contract(first: JumpChainCurves, other: JumpChainCurves) -> bool:
    return (
        first.site_ids == other.site_ids
        and first.rhos == other.rhos
        and first.survey_times == other.survey_times
        and first.diagnostics.moment_order == other.diagnostics.moment_order
        and np.array_equal(first.interval_starts, other.interval_starts)
        and np.array_equal(first.interval_ends, other.interval_ends)
        and np.array_equal(first.source_sites, other.source_sites)
    )


def average_jump_curves(
    curves: Iterable[JumpChainCurves], weights: Iterable[float] | None = None
) -> JumpChainCurves:
    """Average compact curves with compensated summation.

    Without explicit weights, an already averaged chunk receives its
    ``draw_count`` as weight, allowing hierarchical aggregation without moving
    one expanded likelihood object per order between workers.
    """

    first: JumpChainCurves | None = None
    total_local: FloatArray | None = None
    local_compensation: FloatArray | None = None
    total_survival: FloatArray | None = None
    survival_compensation: FloatArray | None = None
    total_weight = 0.0
    component_count = 0
    draw_count = 0
    checksums: list[str] = []
    diagnostic_rows: list[JumpChainDiagnostics] = []

    curve_iterator = iter(curves)
    weight_iterator = iter(weights) if weights is not None else None
    while True:
        try:
            curve = next(curve_iterator)
        except StopIteration:
            if weight_iterator is not None:
                try:
                    next(weight_iterator)
                except StopIteration:
                    pass
                else:
                    raise ValueError("curve and weight iterables must have equal length")
            break
        if weight_iterator is None:
            raw_weight = float(curve.diagnostics.draw_count)
        else:
            try:
                raw_weight = next(weight_iterator)
            except StopIteration as error:
                raise ValueError("curve and weight iterables must have equal length") from error
        weight = float(raw_weight)
        if not math.isfinite(weight) or weight < 0.0:
            raise ValueError("curve weights must be finite and nonnegative")
        if first is None:
            first = curve
            total_local = np.zeros_like(curve.local_moments)
            local_compensation = np.zeros_like(curve.local_moments)
            total_survival = np.zeros_like(curve.final_survival)
            survival_compensation = np.zeros_like(curve.final_survival)
        elif not _same_curve_contract(first, curve):
            raise ValueError("all jump curves must share one mesh and candidate contract")
        assert total_local is not None and local_compensation is not None
        assert total_survival is not None and survival_compensation is not None
        local_value = curve.local_moments * weight - local_compensation
        local_updated = total_local + local_value
        local_compensation = (local_updated - total_local) - local_value
        total_local = local_updated
        survival_value = curve.final_survival * weight - survival_compensation
        survival_updated = total_survival + survival_value
        survival_compensation = (survival_updated - total_survival) - survival_value
        total_survival = survival_updated
        total_weight += weight
        component_count += 1
        draw_count += curve.diagnostics.draw_count
        checksums.append(curve.chain_checksum)
        diagnostic_rows.append(curve.diagnostics)
    if first is None or total_weight <= 0.0:
        raise ValueError("at least one positive-weight jump curve is required")
    assert total_local is not None and total_survival is not None
    digest = hashlib.sha256("".join(checksums).encode()).hexdigest()
    combined = replace(
        first,
        local_moments=total_local / total_weight,
        final_survival=total_survival / total_weight,
        chain_checksum=digest,
        diagnostics=replace(
            first.diagnostics,
            draw_count=draw_count,
            total_weight=total_weight,
            internal_subinterval_count=sum(
                row.internal_subinterval_count for row in diagnostic_rows
            ),
            uniformization_rate_max=max(row.uniformization_rate_max for row in diagnostic_rows),
            holding_rate_min=min(row.holding_rate_min for row in diagnostic_rows),
            maximum_poisson_mean=max(row.maximum_poisson_mean for row in diagnostic_rows),
            poisson_tail_bound_sum=sum(row.poisson_tail_bound_sum for row in diagnostic_rows),
            local_moment_tail_bound_max=max(
                row.local_moment_tail_bound_max for row in diagnostic_rows
            ),
            tilted_uniformization_error_bound_sum=sum(
                row.tilted_uniformization_error_bound_sum for row in diagnostic_rows
            ),
            final_probability_mass_error_max=max(
                row.final_probability_mass_error_max for row in diagnostic_rows
            ),
        ),
    )
    masses = _category_masses(combined)
    category_error = float(np.max(np.abs(masses.sum(axis=2) - 1.0)))
    zero_count = int(np.count_nonzero((masses == 0.0) & ~combined.source_sites[None, :, None]))
    return replace(
        combined,
        diagnostics=replace(
            combined.diagnostics,
            category_sum_error_max=category_error,
            conditional_zero_category_count=zero_count,
        ),
    )


def curves_to_integration(
    curves: JumpChainCurves,
    effects: Sequence[float],
    *,
    background_hazard: float = BACKGROUND_HAZARD,
) -> BridgeIntegration:
    """Expand averaged curves within the fixed Goal 048 likelihood domain."""

    effect_values = _validate_candidates(effects, "effect")
    if effect_values[0] < 1.0 or effect_values[-1] > 10.0:
        raise ValueError("effects must remain within the accepted Goal 048 interval [1, 10]")
    if background_hazard != BACKGROUND_HAZARD:
        raise ValueError("background_hazard must equal the accepted Goal 048 value")
    if curves.diagnostics.category_sum_error_max > 1e-9:
        raise RuntimeError("jump-chain category masses do not sum to one")
    masses = _category_masses(curves)
    degree = np.arange(curves.diagnostics.moment_order + 1)
    moments: list[FloatArray] = []
    for rho_index, rho in enumerate(curves.rhos):
        current = np.empty(
            (
                len(effect_values),
                len(curves.site_ids),
                len(curves.survey_times) + 1,
                len(curves.survey_times) + 1,
            ),
            dtype=np.float64,
        )
        current[:, :, 0, :] = masses[rho_index][None, :, :]
        tilted_categories: list[FloatArray] = []
        lower = 0.0
        theta = background_hazard * (effect_values - 1.0) / rho
        for category, time in enumerate(curves.survey_times):
            upper = rho * time
            start = _boundary_index(curves.interval_ends, lower)
            stop = _boundary_index(curves.interval_ends, upper)
            segment_starts = curves.interval_starts[start:stop]
            coefficients = (
                np.exp(theta[:, None] * segment_starts[None, :])[:, :, None]
                * theta[:, None, None] ** degree[None, None, :]
            )
            tilted = np.einsum(
                "eij,ijs->es",
                coefficients,
                curves.local_moments[start:stop],
                optimize=True,
            )
            if category == 0:
                tilted[:, curves.source_sites] = 1.0
            tilted_categories.append(tilted)
            lower = upper
        for time_index, time in enumerate(curves.survey_times, start=1):
            for category in range(len(curves.survey_times) + 1):
                if category >= time_index:
                    current[:, :, time_index, category] = masses[rho_index, :, category][
                        None, :
                    ] * math.exp(-background_hazard * time)
                else:
                    current[:, :, time_index, category] = tilted_categories[category] * np.exp(
                        -background_hazard * effect_values[:, None] * time
                    )
        if not np.isfinite(current).all() or np.any(current < 0.0):
            raise RuntimeError("jump-chain survival moments are invalid")
        moments.append(current)
    return BridgeIntegration(
        curves.rhos,
        tuple(float(value) for value in effect_values),
        curves.site_ids,
        masses,
        tuple(moments),
        f"jump-chain:{curves.chain_checksum}",
    )


def build_jump_integration(
    order: Sequence[int],
    holding_rates: Sequence[float],
    site_nodes: Sequence[int],
    site_ids: Sequence[str],
    rhos: Sequence[float],
    effects: Sequence[float],
    *,
    source_nodes: Sequence[int],
    background_hazard: float = BACKGROUND_HAZARD,
    survey_times: Sequence[float] = SURVEY_TIMES,
    maximum_mesh_width: float = 0.25,
    maximum_poisson_mean: float = 50.0,
    moment_order: int = 6,
    poisson_tail_tolerance: float = 1e-14,
) -> BridgeIntegration:
    """Convenience wrapper for exact holding-time integration of one order."""

    curves = build_jump_curves(
        order,
        holding_rates,
        site_nodes,
        site_ids,
        rhos,
        source_nodes=source_nodes,
        survey_times=survey_times,
        maximum_mesh_width=maximum_mesh_width,
        maximum_poisson_mean=maximum_poisson_mean,
        moment_order=moment_order,
        poisson_tail_tolerance=poisson_tail_tolerance,
    )
    return curves_to_integration(curves, effects, background_hazard=background_hazard)
