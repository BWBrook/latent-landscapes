# Scalar log-loss derivative stress check

12 November 2026. This development diagnostic compares the frozen
`_log_loss_derivatives` algebra with an overflow-safe rearrangement and an
independent high-precision Decimal reference. Production source is unchanged;
no fit or dataset was opened, and no causal attribution to archived stalls is
made.

For `f(z) = log(1-exp(-z))`, `z > 0`, derivatives are with respect to
`log(z)`: `D = z d/dz`. With `a = z/(exp(z)-1)`, they are `a`,
`a(1-z-a)` and `a(1-3z+z²)-3a²(1-z)+2a³`. The rearrangement avoids
forming huge polynomials before multiplying by a vanishing reciprocal.
Its small-z series matches the frozen series; Decimal independently evaluates
the identities with adaptive precision. For `z >= 1000`, the decreasing bound
`12 z³ exp(-z)` is already below half the smallest binary64 subnormal,
justifying correctly rounded zeros for all four outputs.

The fixed grid contains **54 points**, from the smallest positive float64
(`4.9406564584124654e-324`, displayed as `5e-324`) through `1e308`.
It includes the immediate floating-point neighbours of `1e-3` and the
exponential-overflow region. These are sampled limits, not a search for exact
failure thresholds.

| Observation | Result and scale |
| --- | --- |
| Polynomial overflow | Frozen third derivative is NaN at sampled `1e103`, `1e150`, `1e154`, `1e155`, `1e200`, `1e300`, `1e308`, with overflow/invalid warnings. The reference answer is zero. All sampled points through `1e102` have finite frozen outputs. |
| Premature derivative zeros | At sampled `710, 720, 730, 740, 745, 746, 750`, the first derivative is zero although representable. The second remains representable through sampled `755`, the third through `760`. At `z=710`, the reference derivatives are approximately `3.18e-306`, `-2.25e-303`, `1.60e-300`. These are large relative errors but tiny absolute errors. |
| Log-loss cancellation | Frozen log-loss is zero at sampled `40, 50, 100, 500, 700, 709, 709.782712893384, 710, 720, 730, 740, 745` although the negative reference is representable. At `40`, its magnitude is only `4.25e-18`. |
| Smallest subnormal | All outputs are finite and match the rounded reference: log-loss `-744.4400719213812`, first derivative `1`, second/third derivatives zero. Zero signs differ, with no numerical error. |
| Series switch | At the three points immediately below, at and above `1e-3`, frozen outputs remain finite. Maximum absolute reference discrepancies are `8.89e-16` for log-loss, zero for the first derivative, `1.32e-17` for the second and `3.25e-16` for the third. |

The rearranged diagnostic algebra stays finite at every point. Its maximum
absolute discrepancies from Decimal are respectively `8.89e-16`, `1.12e-16`,
`1.12e-16` and `5.64e-16`. It is a diagnostic comparison, not an adopted
production repair. This check establishes scalar arithmetic weaknesses;
their occurrence or relevance at the archived optimizer stalls remains
unestablished.

Reproduce from the repository root:

```sh
.venv/bin/python scripts/diagnose_loss_derivatives.py --output artifacts/sprint2/diagnostics-20261112/scalar/scalar-stress.json
.venv/bin/python -m pytest tests/test_diagnose_loss_derivatives.py -q
```

Ten tests passed, including log-coordinate derivative identities, finite
differences, the switch neighbours, subnormal rounding, array shapes and
warning/nonfinite retention; Ruff passed. Runtime was Python 3.12.13,
NumPy 2.5.1. The runner verifies production source matches frozen candidate
`99af5206b6a4e53f5b8e9d71cbf348f95e9ae574` before executing.

SHA-256 provenance:

- `src/latent_landscapes/differentiable_likelihood.py`: `22e66eede1d0f98188a2dd6c9fb92bf148ffcbac61a361aeaa537378b1cea5b6`
- `scripts/diagnose_loss_derivatives.py`: `4c10b425ff60e7d7157ee0b62b1a9def73933700bd6df05b9fc202ce550ec369`
- `tests/test_diagnose_loss_derivatives.py`: `3919f4eb9dd2cf1e7a0a0e9ed6071da040f855941fe7b76cbd77f6a2878dcf2e`
- Ignored `artifacts/sprint2/diagnostics-20261112/scalar/scalar-stress.json`: `94ee22fb1cc0a24ac905fef119043ec885312af54ce1224744adbe3a73f9ec5d`
