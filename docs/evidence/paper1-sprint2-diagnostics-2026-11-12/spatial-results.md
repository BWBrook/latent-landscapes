# Spatial solver diagnostic: independent assessment

12 November 2026 · Codex (GPT-6.1 Sol).

**The three enriched collapses are caused immediately by invalid inner
latent-mode evaluations, not measured failures of the outer gain ratio.**
All 51 new outer trials are rejected because their latent solves fail the
unchanged strict-convergence guard. The apparent large mode jumps on failed
sweep sides are zero-vector sentinels, not alternative converged branches.
The separate corridor checkpoint remains unresolved after 80 iterations,
with a valid and steep locally smooth response. The registered tests do not
justify a branch-continuation or detection-derivative repair, or gain-only
certification, as the solution to these observed failures.

All four prescribed spatial endpoints and their new unchanged-solver starts
are complete: three enriched connected-1 B candidates at `h=sqrt(30)`, and
one corridor-1 window-low B dense candidate at
`h=22.222198691728167`. These are development diagnostics on the rejected
panel, not new qualification evidence or a census of all archived failures.
The frozen candidate remains rejected; training and validation remain closed.
See the [independent execution review](independent-execution-review.md) for
output/source identity checks and their limits.

## Enriched connected-1 B: three collapses

All three archived criteria and gradients reproduce exactly. Each newly
prescribed start remains bitwise at its archived vector through 17 iterations,
then reports `trust region collapsed`. There are no accepted outer steps.
Each trace has 17 curvature events, 17 trial events and one return, with 103
evaluations. The extra curvature evaluations arise from backward differences
when a forward side fails; completeness does not mean both sides are valid.

| Endpoint | Criterion | Projected gradient norm | Local quadratic gain | Invalid archived-sweep sides / admissible sides |
| --- | ---: | ---: | ---: | ---: |
| enriched-collapse-1 | -1084.5401174046976 | 0.00610917 | 1.02864e-5 | 23 / 63 |
| enriched-collapse-2 | -1084.5455089070504 | 5.38420 | 0.00539503 | 21 / 63 |
| enriched-collapse-3 | -1084.5401192127956 | 0.00521201 | 1.20926e-5 | 24 / 63 |

Every one of the 51 outer trial evaluations has `success=false`,
`mode_success=false`, unavailable criterion, and the message
`latent mode did not strictly converge`. Its ratio is the sentinel `-1`.
No actual criterion gain is measured for these trials. Their predicted gains
and `g·step` are positive, including at the final radii. Thus this is not
observed rejection of a valid point with a measured poor gain ratio. The
radius shrinks from 1 to `2.3283e-10` before the last rejection triggers the
`1e-10` floor.

All three endpoints have log sigma exactly at its upper bound, with an
outward gradient. The solver correctly removes that coordinate from the
free set, retaining `(alpha,beta,detection_sd)`, and all trial log-sigma
steps are exactly zero. The free-set curvature is complete and positive
definite on every iteration: its minimum eigenvalue is about 1.80 and largest
about 3261–3282. No nonpositive prediction or clipping defect is needed to
explain these rejections. The recorded local gains above remain quadratic
predictions, not rigorous remaining-gain or LR-error bounds; the second
endpoint would also exceed the proposed `0.001` gain threshold.

The baseline modes succeed, with score norms about `2.6e-9` to `3.2e-9`.
All three repeated baseline summaries per endpoint are exactly equal.
Nearby failures are directional: for example, many negative-alpha,
positive-beta and positive-detection-SD probes fail the inner guard, while
opposite sides provide valid slopes and modes. Log-sigma's positive probes
are all out of bounds and remain explicitly unavailable.

The valid one-sided slopes approach the reported gradients as the stencil
shrinks. For the second endpoint, the valid detection-SD backward slope
approaches `5.38420863` at `t=1e-8`, compared with the reported `5.38420490`.
For the first endpoint, its valid alpha forward slope at `t=1e-6` is
`-0.00611044`, compared with `-0.00610917`. For the third endpoint, its valid
beta backward slope at `t=1e-7` is `0.00406772`, compared with `0.00406781`.
Near-zero detection gradients in endpoints 1 and 3 have less useful relative
precision, and small-step cancellation remains visible. Missing sides prevent
a full central-difference plateau from being established there; they are not
assigned finite slopes.

**The apparent jumps are not branch-switching evidence.** When the frozen
mode solver returns failure, `mode()` fills its unsuccessful `ModeResult`
with `u=zeros(site_count)`. Every invalid archived-sweep side has this exact
sentinel. Its reported displacement therefore equals the baseline mode norm:
9.640487, 9.770024 or 9.641842. Those constant distances do not measure a
second converged mode. The retained valid-side mode displacements decrease
with the stencil. The same validity limitation applies to the normalized
last-rejected-step sweeps: the direction's improving side is generally
unavailable. Their origin is correctly the unchanged new trace, not an
unavailable historical step.

This outcome lies outside message 3288's three clean signatures for a
successfully evaluated criterion. There is no demonstrated persistent
coordinate-derivative defect or jump between valid modes. A finite-precision
pattern in valid slopes does not show that the rejected trials failed because
of objective noise: those trials have no valid objective. The immediate
mechanism is inner-solver evaluability failure. The registered trace does not
retain the failing inner iterate or its exit reason. A separately labelled
post-outcome observation below identifies one concrete failure path.

## Corridor envelope checkpoint

The checkpoint manifest names this endpoint `corridor-envelope-1`. Its
archived source is
`standard_fixed_0x1.8cf092e5d9e06p+1_high_sigma_anchor_2_fit_0`, with parameters
`(-11.07104748591036, 1.0123992521128973, 0.3548629025709948,
0.24109235481774388)` in `(alpha,beta,log_sigma,detection_sd)` coordinates.
The archived evaluation-stream SHA-256 is
`7342ac67435930ee7284630a22e447be1b52eee17e9ff510e7bf315720f62e71`.
The observed archive and fresh baseline agree exactly in criterion and
reported gradient.

### Archived endpoint sweep

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

### New prescribed start and unchanged solver trace

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
budget exhaustion. This is a different immediate failure from the enriched
inner-solver invalidity. Frozen failures and the candidate rejection remain
unchanged.

## Repair implication and remaining limit

The actionable target is the deterministic inner solve and its unsuccessful
return path. After the registered outcomes were available, the parent made
one separately specified observational replay of the first invalid outer
trial from `enriched-collapse-1`, tracing the unchanged frozen `_mode_branch`.
This was a **post-outcome diagnostic extension**, not part of the original
registered test or a qualification retry. The [inner-failure review](inner-failure-review.md)
records its source review and the bounded repair implication.

The retained witness shows a valid finite zero-start state and a positive-
definite inner Newton system at iteration zero. With damping zero, its
proposed latent step has maximum 270.45, taking the largest proposed log
hazard to 261.51. The trial evaluator raises `FloatingPointError` for
nonfinite output; the whole-solve handler immediately returns `None` without
increasing damping. That demonstrates an abort-on-invalid-trial defect for
**one** recorded outer trial. It does not establish that exact exception as
the cause of all 51 failures. The observational receipt's SHA-256 is
`e086168753e4a914c26eb2361ae28e9b41371e10c7b98413eec01b3bc36a399c`.

The supported narrow repair proposal is to reject an invalid inner proposal,
retain the valid current state and try a more damped step under fixed limits,
while keeping the deterministic zero start and every strict convergence and
finite-output guard. Initial-state failure and unresolved final states must
still fail. No such repair was implemented or tested in this assessment;
independent method review remains required.

The archive's stopping/eligibility mismatch remains a separate real defect.
Fixing it alone cannot accept these three points: all projected gradients
exceed `0.001`, and it does not repair invalid evaluations around them. A
path-dependent continuation change is not selected by these results, because
there is no observed switch between valid branches. A replacement
calculus or gain-only stopping rule is likewise not established as sufficient.
The corridor case additionally needs an effective step/curvature strategy
within the same envelope, rather than an assumption that the three clean
mechanisms exhaust possible causes. Any repaired candidate still needs
independent method review and a freshly drawn qualification panel.

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

Next: Claude — review the inner-solver failure mechanism and bounded repair target.
