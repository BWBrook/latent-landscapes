# Spatial solver diagnostic: partial independent assessment

12 November 2026 · Codex (GPT-6.1 Sol).

**Partial result: one spatial checkpoint is complete; the three enriched
endpoint diagnostics are pending.** This assessment covers only the archived
corridor-1 window-low B dense positive-variance candidate at
`h=22.222198691728167`, and its new unchanged-solver start. It does not
characterize the other 16 archived positive-variance exceptions or select a
repair. These are development diagnostics on the rejected panel, not new
qualification evidence. Training and validation remain closed.

The checkpoint manifest names this endpoint `corridor-envelope-1`. Its
archived source is
`standard_fixed_0x1.8cf092e5d9e06p+1_high_sigma_anchor_2_fit_0`, with parameters
`(-11.07104748591036, 1.0123992521128973, 0.3548629025709948,
0.24109235481774388)` in `(alpha,beta,log_sigma,detection_sd)` coordinates.
The archived evaluation-stream SHA-256 is
`7342ac67435930ee7284630a22e447be1b52eee17e9ff510e7bf315720f62e71`.
The observed archive and fresh baseline agree exactly in criterion and
reported gradient.

## Archived endpoint sweep

The criterion is `-1113.7343896488865`; the projected gradient norm is
`4.912651861812314`. The latent mode passes its unchanged checks, with score
norm `1.20e-13`. All three repeated baseline summaries, including the complete
mode vectors, are exactly equal to the baseline summary.

At fine steps the central differences approach all four reported gradients.
The full nine-step sweep is retained; the common fine steps below show the
agreement without making a new acceptance threshold.

| Coordinate | Reported gradient | Central difference, t=1e-7 | Central difference, t=1e-8 |
| --- | ---: | ---: | ---: |
| alpha | -0.1680161253 | -0.1680177775 | -0.1680064088 |
| beta | 0.0533913517 | 0.0533930233 | 0.0533873390 |
| log sigma | -0.6587171577 | -0.6587174539 | -0.6587015378 |
| detection SD | 4.9126518618 | 4.9127470447 | 4.9126470003 |

Coarse detection-SD probes are strongly nonlinear: the central difference at
`t=1e-4` is `333.3268`, falling to `5.91105` at `1e-5`, `4.92256` at `1e-6`
and the values above. This coarse discrepancy is not evidence that the
reported detection-SD gradient is wrong at this endpoint. In particular, the
outer criterion difference solves a new latent mode on each side; it is not
the same calculation as the internal fixed-mode site derivative.

Both one-sided slopes approach the same fine-scale derivative. Mode
displacement norms also decrease approximately in proportion to `t`: for
`t=1e-6` through `1e-9`, displacement divided by `t` stabilizes near 130.20,
21.877, 558.95 and 4110.78 along the four coordinates respectively. The large
detection-SD response is steep but shrinks with the step; no nonvanishing
mode-jump signature is observed. The positive log-sigma probe at `t=0.1`
crosses its bound and is explicitly unavailable, without clipping.

Some central-difference errors grow again at the smallest steps, consistent
with subtraction/finite-precision effects. The sweep supports local derivative
consistency and a steep smooth mode response at the sampled fine scales. It
does not establish that the historical iteration-cap failure was caused by a
noise floor, or rule out other branches elsewhere.

The complete finite-difference curvature estimate has eigenvalues
`(-17.6781, 3.76481, 66.5550, 2568943.7632)`. Its indefiniteness makes the
local quadratic gain unavailable under the registered rule. Because this is
a numerical curvature estimate on a very steep response, its negative
eigenvalue is not by itself proof that the exact criterion Hessian is
indefinite.

## New prescribed start and unchanged solver trace

Starting a new unchanged solve at the archived vector reaches the
80-iteration limit again. This is not an exact replay of the historical
trajectory. The trace contains 80 curvature events, 80 trial events and one
return, accounting for 401 evaluations. Direct reconstruction of the
acceptance rule reproduces every subsequent state and the return: 67 trials
are accepted and 13 rejected. All trial evaluations and their latent modes
are valid; every recorded curvature estimate is complete and indefinite.

The criterion increases by `0.0001751021238760586`, exactly the sum of the
accepted trial gains, to `-1113.7342145467626`. The projected gradient norm
falls from `4.91265` to `1.97048`, still far above the frozen `0.001`
eligibility threshold and the run's internal `0.0001` target. The solver does
not claim convergence. The last trial is accepted with ratio `0.2443`;
the run ends because of its iteration budget, not a collapsed radius. Its
smallest recorded radius is `6.1035e-5`.

At the final point, the coordinate sweep again approaches the reported
gradient and mode displacements decrease with step size. The complete final
curvature remains indefinite, with minimum eigenvalue `-26.6367`, so the
predicted gain remains unavailable. The last rejected trial occurred at
iteration 56, before later accepted steps. Its origin differs from the final
endpoint; the output records that provenance and correctly omits it as a
rejected-step direction at this endpoint.

**This candidate remains unresolved and no repair is demonstrated.** Neither
the fine-scale sweep nor this new trace supplies the registered persistent
gradient-mismatch or nonvanishing mode-jump signature. The small-step
precision pattern does not establish a noise-floor cause for the observed
budget exhaustion. The pending enriched endpoints are required before
assessing the mechanism of the archived trust-region collapses or choosing a
mechanism-specific repair. Frozen failures and the candidate rejection remain
unchanged.

## Retained outputs

The following files are under the ignored local directory
`artifacts/sprint2/diagnostics-20261112/results/spatial-3/`; hashes identify the
exact completed outputs independently inspected here. No additional numerical
runs or source edits were made during this assessment.

| File | SHA-256 |
| --- | --- |
| corridor-envelope-1-archived-sweep.json | 074490e47d6f80c9b2d211c4b06e2837a75e59d6309e4a7aace78925850303e9 |
| corridor-envelope-1-new-start-sweep.json | 58be876074dd77ec5fa059bb2f5f1424f4c36af8da0dbdfde8ffb53af8f9c255 |
| corridor-envelope-1-trace.jsonl | 40f3d171b18d177d844eea5fe62693e29e27729f284334d1f2c4a27694752603 |

Next: Codex — reconcile the three pending enriched diagnostics after completion.
