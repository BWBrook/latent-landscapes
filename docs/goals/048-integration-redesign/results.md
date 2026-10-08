# Goal 048 retrospective pilot result

The infection-order integrator is mathematically justified and computationally
practical, but **the registered K1024 configuration does not qualify**. The
connected width calculation stabilizes across the three larger banks; corridor
speed-profile tails remain sensitive to the sampled infection orders. This is
a finite-budget numerical result, not rejection of the conditioning identity.
No replacement method or ecological result is adopted.

## Registered comparisons

Each old stress map has three independent 1024-order banks and their nested
256-order prefixes. Connected uses the original 250 calibration and 250
validation null histories, both designs, known rho=1 and H181. Corridor uses the
original validation history 0, access design, all three paired effect truths,
the fixed eight-rho window and H181. All 12 configurations produce finite
observed-history likelihoods. All 18 corridor surfaces have interior maxima.
The registration, seed selection and numerical movement thresholds are unchanged.

| Check | K256 independent bank pairs | K1024 independent bank pairs | K256 to K1024 prefixes |
|---|---:|---:|---:|
| Connected width criteria | 0/3 pass | 3/3 pass | 1/3 pass |
| Corridor tail criteria | 0/3 pass | 0/3 pass | 0/3 pass |

At K1024, the connected maximum between-bank cutoff movement is 0.03175 LR
against 0.5; support endpoints move by at most one H181 cell; coverage,
exclusion, boundary classifications and component counts agree. The maximum
movement in the mean balanced-minus-access log-width contrast is 0.0049905
against 0.01. All five failures involving K256 are changes to one or two
support-boundary classifications. These are retained failures, not waived.

For the corridor, every comparison fails both the generating-rho LR and the
rho-profile core LR criteria for all three effect truths. At K1024, maximum
between-bank generating-rho LR movement is **7.7774**, against **0.5**; maximum
core-profile movement is **3.2048**, against **0.5**. Effect-profile movements
remain below tolerance, effect MLEs differ by at most one grid cell, and rho
MLEs differ by one local grid step at most. Stable locations of the maxima
therefore do not establish stable likelihood tails.

The largest generating-rho disagreement is larger at K1024 than at K256
(7.7774 versus 2.2310). Three banks do not support an empirical convergence rate
or a defensible extrapolation of the bank size needed for acceptance. In
particular, an inverse-square-root sample-size calculation would be a budget
heuristic here, not evidence that a larger run would qualify.

[Comparison figure](../../../artifacts/goal048_execution/pilot-summary.png).
Its corridor panels share one paired predator realization; they are not three
independent tail stress histories. The figure shows numerical sensitivity,
not accepted ecological contrasts or confidence limits.

## What drives the corridor discrepancy

A post hoc, read-only decomposition of the retained K1024 means localizes the
bank-1 versus bank-2 LR difference (zero-based bank labels) to several training
sites. For the fivefold case, `cell_17_69` contributes 2.1374 of the total 7.7774
LR difference, `cell_17_67` contributes 1.4714 and `cell_16_76` contributes
0.8529. These three account for 4.4616 LR. Their contributions are sums of
site-marginal log probabilities evaluated at each bank's profile maximum and
at generating rho; the decomposition reconstructs the aggregate difference.

For `cell_17_69`, the predicted probability of its observed predator history
at rho=1 changes from 8.365e-5 to 3.758e-5 between these banks. For
`cell_17_67`, it changes from 6.290e-4 to 2.317e-4. Both histories include a
predator detection on day 40. The corresponding joint-history probabilities
are positive and of order 1e-8 to 1e-6, well above floating-point underflow.
The repeated pattern across effect truths is consistent with variation in
arrival integration; the predator observations are shared by the paired truths.

This supports residual infection-order sampling variability as the immediate
obstacle. It does not identify the exact rare-order contribution distribution,
effective sample size or absolute integration error: individual-order
contributions were not retained. Some unused conditional categories underflow,
so finite observed support alone is not a universal relative-accuracy claim.

## Verification and cost

Both remote jobs exited zero. The supervisor completed in 2853.68 seconds
(47.56 minutes), with peak sampled aggregate RSS 1.850 GiB. The two-hour cap,
four workers per map, one native thread, 10 GiB per-process address-space limit
and 96 GiB aggregate RSS cap held. Both recorded process groups are absent.

All 83 staged files and 27 output/receipt hashes match locally and remotely.
All 60 accepted Goal 046 source modules remain unchanged; all 64 current
staged source modules and the three staged scripts match the local files.
The 6144 registered order seeds regenerate exactly. The prior local full suite
passed 319 tests; final target controls passed 24 tests.

Re-expanding all 12 saved compact means and replaying 78 representative
likelihood surfaces reproduces the saved raw arrays to at most 6.82e-13,
against 1e-10. This includes both connected designs, calibration histories
0/124/131, validation histories 0/231, and all three corridor truths.
Recomputed category normalization error is below 1.4e-12. These checks verify
implementation and retained arithmetic, not absolute accuracy of the outer
Monte Carlo integral.

The [verification receipt](../../../artifacts/goal048_execution/completed-check.json),
[all comparisons](../../../artifacts/goal048_execution/returned/pilot-comparisons.json),
[site decomposition](../../../artifacts/goal048_execution/corridor-site-decomposition.json)
and raw outputs remain local and on deep-server. The independent terminal
review is recorded separately in [final-review.md](final-review.md).

## Recommendation and stopping boundary

Retain infection-order conditioning as a valid prototype, with the connected
result as encouraging retrospective evidence. Do not adopt K1024, restart the
all-map campaign or replace the existing reference bundles.

The next useful tranche is a bounded diagnosis of per-order contributions at
the few corridor sites driving the tail discrepancy, followed by a reviewed
choice between a larger fixed order bank and a targeted variance-reduction
calculation. Its design should retain individual or batch contribution
summaries, measure concentration and computational cost, and predeclare the
next budget and stopping rule before new outcomes. This would provide evidence
for a prospective accuracy contract rather than assuming that bank enlargement
will work. Such new simulation work has not been launched.

Goal 048's development-and-pilot tranche ends at this demonstrated numerical
obstacle and method recommendation. Goal 046 and Goal 047 failures remain
unchanged. Production qualification, ecological synthesis, commits, pushes and
publication remain outside scope.
