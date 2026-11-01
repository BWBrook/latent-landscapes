"""Stratified defensive importance integration with independently replicated errors."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import solve_triangular  # type: ignore[import-untyped]
from scipy.special import gammaln, logsumexp  # type: ignore[import-untyped]
from scipy.stats import genpareto, t  # type: ignore[import-untyped]

Array = NDArray[np.float64]
LogTarget = Callable[[Array], Array]


def stream_seed(identity: str, stream: int, batch: int, component: int, variate: int) -> int:
    digest = hashlib.sha256(identity.encode()).digest()
    words = np.frombuffer(digest, dtype="<u4").tolist()
    seed = np.random.SeedSequence([2026110109, 713, *words, stream, batch, component, variate])
    return int(seed.generate_state(1, dtype=np.uint64)[0])


@dataclass(frozen=True)
class Component:
    mean: Array
    cholesky: Array
    weight: float
    degrees_of_freedom: float | None = None

    def __post_init__(self) -> None:
        n = len(self.mean)
        if self.mean.shape != (n,) or self.cholesky.shape != (n, n):
            raise ValueError("proposal dimensions do not match")
        if not np.all(np.isfinite(self.mean)) or not np.all(np.isfinite(self.cholesky)):
            raise ValueError("nonfinite proposal")
        if not np.allclose(self.cholesky, np.tril(self.cholesky), rtol=0, atol=0):
            raise ValueError("proposal Cholesky factor must be lower triangular")
        if np.any(np.diag(self.cholesky) <= 0) or not 0 < self.weight <= 1:
            raise ValueError("invalid proposal scale or weight")
        if self.degrees_of_freedom is not None and self.degrees_of_freedom <= 0:
            raise ValueError("invalid proposal degrees of freedom")

    def logpdf(self, values: Array) -> Array:
        z = solve_triangular(self.cholesky, (values - self.mean).T, lower=True).T
        squared = np.sum(z * z, axis=1)
        dimension = len(self.mean)
        logdet = float(np.log(np.diag(self.cholesky)).sum())
        if self.degrees_of_freedom is None:
            return np.asarray(-0.5 * (dimension * math.log(2 * math.pi) + squared) - logdet)
        df = self.degrees_of_freedom
        normalizer = (
            gammaln((df + dimension) / 2)
            - gammaln(df / 2)
            - dimension / 2 * math.log(df * math.pi)
            - logdet
        )
        return np.asarray(normalizer - (df + dimension) / 2 * np.log1p(squared / df))

    def draw(self, n: int, *, identity: str, stream: int, batch: int, component: int) -> Array:
        rng = np.random.default_rng(stream_seed(identity, stream, batch, component, 0))
        z = rng.standard_normal((n, len(self.mean)))
        if self.degrees_of_freedom is not None:
            scales = np.random.default_rng(stream_seed(identity, stream, batch, component, 1))
            z /= np.sqrt(scales.chisquare(self.degrees_of_freedom, n) / self.degrees_of_freedom)[
                :, None
            ]
        return np.asarray(self.mean + z @ self.cholesky.T)


@dataclass(frozen=True)
class Proposal:
    components: tuple[Component, ...]

    def __post_init__(self) -> None:
        if not self.components or not math.isclose(
            sum(c.weight for c in self.components), 1.0, rel_tol=0, abs_tol=1e-12
        ):
            raise ValueError("proposal weights must sum to one")
        if len({len(c.mean) for c in self.components}) != 1:
            raise ValueError("proposal component dimensions differ")

    def logpdf(self, values: Array) -> Array:
        return np.asarray(
            logsumexp([math.log(c.weight) + c.logpdf(values) for c in self.components], axis=0)
        )

    def counts(self, n: int) -> NDArray[np.int64]:
        if n < len(self.components):
            raise ValueError("at least one draw per component is required")
        weights = np.array([c.weight for c in self.components])
        counts = np.maximum(1, np.floor(n * weights).astype(np.int64))
        while int(counts.sum()) > n:
            eligible = np.where(counts > 1, counts - n * weights, -np.inf)
            counts[int(np.argmax(eligible))] -= 1
        while int(counts.sum()) < n:
            counts[int(np.argmax(n * weights - counts))] += 1
        return counts


def defensive_proposal(modes: Sequence[tuple[Array, Array, float]]) -> Proposal:
    """Each mode supplies its mean, inverse Hessian, and log Laplace mass."""
    if not modes:
        raise ValueError("no qualified proposal mode")
    log_masses = np.array([m[2] for m in modes])
    masses = np.exp(log_masses - logsumexp(log_masses))
    if np.any(masses == 0):
        raise ValueError("mode weight underflow; proposal is indeterminate")
    components = []
    for (mean, covariance, _), mass in zip(modes, masses, strict=True):
        chol = np.linalg.cholesky(covariance)
        for weight, scale, df in ((0.80, 1.0, None), (0.15, 4.0, None), (0.05, 0.6, 5.0)):
            components.append(Component(mean, chol * math.sqrt(scale), float(mass * weight), df))
    return Proposal(tuple(components))


def pareto_tail(log_weights: Array) -> dict[str, Any]:
    if len(log_weights) < 250 or not np.all(np.isfinite(log_weights)):
        return {"status": "unavailable", "reason": "insufficient or nonfinite weights"}
    ordered = np.sort(log_weights)
    tail_size = min(len(ordered) // 5, int(3 * math.sqrt(len(ordered))))
    threshold = float(ordered[-tail_size - 1])
    scale = float(ordered[-1])
    excess = np.exp(ordered[-tail_size:] - scale) - math.exp(threshold - scale)
    if np.count_nonzero(excess > 0) < 50:
        return {"status": "unavailable", "reason": "insufficient positive tail excesses"}
    try:
        shape, _, fitted_scale = genpareto.fit(excess, floc=0)
    except (ValueError, FloatingPointError, RuntimeError) as error:
        return {"status": "unavailable", "reason": str(error)}
    if not math.isfinite(shape) or not math.isfinite(fitted_scale) or fitted_scale <= 0:
        return {"status": "unavailable", "reason": "invalid Pareto fit"}
    return {
        "status": "available",
        "k": float(shape),
        "tail_size": tail_size,
        "log_threshold": threshold,
        "log_weight_scale": scale,
        "excess_scale": float(fitted_scale),
    }


@dataclass(frozen=True)
class Estimate:
    log_integral: float
    batch_log_integrals: Array
    draws: int
    diagnostics: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        return {
            "log_integral": self.log_integral,
            "batch_log_integrals": self.batch_log_integrals.tolist(),
            "draws": self.draws,
            "diagnostics": self.diagnostics,
        }


def integrate(
    log_target: LogTarget,
    proposal: Proposal,
    *,
    identity: str,
    stream: int,
    draws: int,
    batches: int = 16,
    chunk_size: int = 32,
) -> Estimate:
    if batches < 2 or draws % batches or chunk_size < 1:
        raise ValueError("draws must be divisible by at least two batches")
    per_batch = draws // batches
    counts = proposal.counts(per_batch)
    batch_logs, raw_weights, contributions, tails = [], [], [], []
    for batch in range(batches):
        component_logs, batch_weights = [], []
        for index, (component, count) in enumerate(zip(proposal.components, counts, strict=True)):
            samples = component.draw(
                int(count), identity=identity, stream=stream, batch=batch, component=index
            )
            values = []
            for start in range(0, int(count), chunk_size):
                sample = samples[start : start + chunk_size]
                target = np.asarray(log_target(sample), dtype=float)
                if target.shape != (len(sample),) or not np.all(np.isfinite(target)):
                    raise ValueError("invalid importance target evaluation")
                values.append(target - proposal.logpdf(sample))
            weights = np.concatenate(values)
            batch_weights.append(weights)
            raw_weights.append(weights)
            weighted = weights + math.log(component.weight) - math.log(int(count))
            contributions.append(weighted - math.log(batches))
            component_logs.append(float(logsumexp(weighted)))
        batch_logs.append(float(logsumexp(component_logs)))
        tails.append(pareto_tail(np.concatenate(batch_weights)))
    logs = np.asarray(batch_logs)
    all_raw = np.concatenate(raw_weights)
    all_contributions = np.concatenate(contributions)
    log_total = float(logsumexp(logs) - math.log(batches))
    normalized = np.exp(all_contributions - logsumexp(all_contributions))
    ess = float(1 / np.dot(normalized, normalized))
    maximum = float(normalized.max())
    pooled = pareto_tail(all_raw)
    ks = [x["k"] for x in tails if x["status"] == "available"]
    tail_ok = pooled["status"] == "available" and pooled["k"] < 0.5 and len(ks) == batches
    diagnostics = {
        "batches": batches,
        "component_draws_per_batch": counts.tolist(),
        "ess": ess,
        "relative_ess": ess / draws,
        "maximum_normalized_weight": maximum,
        "pareto_tail": pooled,
        "batch_pareto": tails,
        "batch_pareto_median": float(np.median(ks)) if ks else None,
        "batch_pareto_maximum": max(ks) if ks else None,
        "weight_gates_passed": bool(
            tail_ok and ess >= 1000 and ess / draws >= 0.01 and maximum <= 0.01
        ),
        "ordinary_unnormalized_importance": True,
        "stratified_component_variance": "independent_batch_replication",
        "identity": identity,
        "stream": stream,
    }
    return Estimate(log_total, logs, draws, diagnostics)


def paired_interval(values: Array, *, estimate: float | None = None) -> dict[str, float]:
    if len(values) < 2 or not np.all(np.isfinite(values)):
        raise ValueError("paired batches must be finite")
    center = float(np.mean(values)) if estimate is None else float(estimate)
    standard_error = float(np.std(values, ddof=1) / math.sqrt(len(values)))
    half_width = float(t.ppf(0.975, len(values) - 1) * standard_error)
    return {
        "estimate": center,
        "standard_error": standard_error,
        "half_width": half_width,
        "lower": center - half_width,
        "upper": center + half_width,
    }


def fixed_outer_contrast(
    free: Estimate, point: Estimate, *, laplace_free: float, laplace_point: float
) -> dict[str, float]:
    if free.batch_log_integrals.shape != point.batch_log_integrals.shape:
        raise ValueError("paired batch counts differ")
    shift = 2 * ((free.log_integral - laplace_free) - (point.log_integral - laplace_point))
    batch_shifts = 2 * (
        (free.batch_log_integrals - laplace_free) - (point.batch_log_integrals - laplace_point)
    )
    return paired_interval(batch_shifts, estimate=shift)
