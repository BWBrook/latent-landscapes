# Infection-order integration feasibility

**Status:** bounded Goal 048 implementation and numerical feasibility evidence.
This note does not adopt the method or qualify any ecological result.

## Scientific target and exact representation

The target is the same site-marginal composite likelihood used by Goal 046:
arrival-category probabilities and arrival-restricted prey-survival moments for
the fixed G201 rho grid, H181 effect grid, six survey times and background
hazard 0.002. The biological generator, observation process, sampling designs,
calibration rule and inferential contrasts remain unchanged.

For the accepted undirected exponential-edge first-passage generator, let
`A_k` be the infected set after `k` non-source infections and let

```text
Lambda_k = sum_{e in boundary(A_k)} 1 / c_e.
```

Exponential memorylessness gives an equivalent susceptible-infected CTMC. The
next vertex is selected in proportion to the total boundary rate incident on
it. Conditional on the resulting vertex order `O`, the holding times are
independent:

```text
H_k | O ~ Exponential(rho Lambda_k),
T_s | O = sum_{k < m_s} H_k.
```

Thus one sampled order supplies exact conditional arrival distributions for
all sites and every rho. Averaging those conditional quantities over iid
orders is unbiased for the original generator. It removes holding-time Monte
Carlo variance but retains finite-order sampling error.

The order is determined by the normalized exponential-edge direction, so its
sigma-field is coarser than the direction used by global-Gamma conditioning.
For every square-integrable linear category or survival-moment integrand `Y`,

```text
Var(E[Y | O]) <= Var(E[Y | direction]) <= Var(Y).
```

This ordering does not extend automatically through likelihood logarithms,
profiling, calibrated order statistics or support endpoints. Replicated-bank
pipeline comparisons remain necessary.

## Numerical implementation and controls

`src/latent_landscapes/jump_chain_integration.py` propagates the conditional
pure-birth chain by positive uniformization. It retains seven local polynomial
moments per mesh interval and site, plus final survival probabilities. The
common mesh contains every rho-times-survey endpoint; compact quantities are
averaged with compensated summation before expansion over effects.

The fixed numerical domain is `1 <= effect <= 10` and background hazard 0.002.
Within the full G201 grid, `rho >= 0.25`, so the largest exponential tilt is
0.072. At mesh width 0.25 and polynomial degree six, the pointwise Taylor
remainder bound is `1.24e-16`. The implementation separately records Poisson
tail loss, propagated probability-mass error, local-moment error bounds,
tilted-integral error bounds, category reconciliation and conditional
floating-point zeros. Source sites are exact category-zero atoms; no
pseudocount, clipping, flooring or renormalization is used.

The exact tests compare fixed-order integration with an independent dense
phase-type calculation and compare an exhaustive weighted mixture of embedded
orders with the full infected-set CTMC. They cover category masses, tilted
survival moments, source atoms, unreachable nodes and unequal hierarchical
aggregation. The deterministic acceptance tolerance is `1e-10`.

## Full-map feasibility receipts

The pre-registered one-order refinement smokes used the actual 5,144-phase,
278-site connected and corridor stress maps. The coarse calculation used mesh
width 0.25 and degree six; the independent refinement used width 0.125 and
degree eight.

| Map | Coarse seconds | Max absolute coarse/fine difference | Coarse category-sum error | Coarse tilted-error bound | Result |
|---|---:|---:|---:|---:|---|
| connected-2026090812 | 0.384 | 2.614e-12 | 1.319e-12 | 3.224e-14 | pass |
| corridor-2026090812 | 0.498 | 1.991e-12 | 1.300e-12 | 1.555e-14 | pass |

The detailed receipts are
`artifacts/goal048_execution/local-connected-smoke/report.json` and
`artifacts/goal048_execution/local-corridor-smoke/report.json`. These timings
and refinement agreements establish local feasibility and arithmetic
plausibility. They do not establish the number of orders required, accuracy of
nonlinear likelihood summaries or generality across maps.

Conditional category zeros remain for extremely remote sites and very early
intervals because probabilities can fall below the finite Poisson truncation
or floating-point range in a single order. They are counted explicitly. The
pilot must reject any averaged configuration that leaves a required observed
history with non-positive marginal probability; adding artificial support is
not an admissible repair.

## Recommendation and residual risk

Proceed with the frozen three-replicate K256/K1024 jump-chain pilot. Compare
equal-K independent banks and nested prefixes on the unchanged connected-width
and corridor-tail diagnostics. This is the evidence needed to distinguish a
computationally feasible conditional identity from a useful estimator for the
nonlinear pipeline.

Do not adopt the method if exact controls fail, observed-history support is
non-positive, replicated banks remain unstable, or the registered numerical
movement limits fail. A successful retrospective pilot supports only a frozen
prospective validation design. It does not repair composite-likelihood spatial
dependence, map pseudoreplication, observation-model misspecification,
identifiability between rho and effect, or extrapolation beyond the synthetic
programme. Independent scientific review would materially improve confidence
before prospective validation and is required before production adoption.
