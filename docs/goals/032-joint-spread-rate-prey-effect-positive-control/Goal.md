# Goal 032: Joint Spread-Rate and Prey-Effect Positive Control

## Scientific Question

Can the same imperfect predator and prey observations distinguish how quickly
the predator wave moved from how strongly predator arrival increased prey
extirpation risk?

## Frozen Experiment

Retain the accepted Goal 031 landscape, 160-site access-constrained design,
central stochastic truth, resistance contrast `eta = 1`, background
prey-extirpation hazard `0.002`, true fivefold post-arrival hazard multiplier,
survey days `10, 20, 30, 40, 50, 60`, training/holdout split, two visits per
survey, known per-visit detection probability `0.65` for both species, zero
false positives, and the shared within-site latent-arrival likelihood.

Estimate exactly two parameters:

- predator spread rate `rho`, with truth `1`; and
- post-arrival prey-extirpation hazard ratio, with truth `5`.

Keep resistance, both detection probabilities, background hazard, and
false-positive rates fixed and known. Use a prespecified 51-point log-spaced
spread-rate grid from `0.25` to `4` and a 91-point prey-effect grid from `1` to
`10`; both truths must occur exactly once. These are every second point of the
accepted underlying Goal 019 and Goal 029 grids and retain resolution well
inside the point-recovery gates.

Integrate over the same `4,096` central-process draws. For a candidate spread
rate, scale each base arrival time by `1 / rho`, which is exact for this
first-passage process because `rho` divides every edge traversal time. Within
each site, predator and prey histories must share an arrival draw before
marginalization. Across sites, retain the explicitly limited site-marginal
composite likelihood.

The neutral comparator must fit its own spread rate from predator histories
and a constant prey-extirpation hazard from prey histories under the same
observation model. It must not receive the process model's fitted spread rate.

Run one independent central-truth ensemble:

- master seed `20260812032`;
- `4,096` integration-bank draws;
- `2,000` calibration datasets;
- the 1901st ordered joint likelihood-ratio statistic as the fixed 95% cutoff;
  and
- `1,000` validation datasets.

Use the published Goal 031 result as a read-only prey-effect anchor. Do not
rerun it. Production may use `deep-server` after a local reduced smoke and one
timing probe.

## Prespecified Decision

Common gates:

- all generation, bank-scaling, shared-arrival, observation, split, seed,
  likelihood, anchor, and count invariants pass;
- the 95% Wilson interval for joint-support coverage contains `0.95`;
- at least `950/1000` joint supports are connected and avoid artificial grid
  boundaries; and
- mean held-out log-score advantage over the fitted neutral has a 95% lower
  bound above zero.

Spread-rate gates:

- median absolute log-rate error is at most `0.10`; and
- median marginal log-rate support width is at most `0.50`.

Prey-effect gates:

- at least `950/1000` joint supports exclude hazard ratio `1`;
- median absolute log-effect error is at most `0.20`; and
- median marginal log-effect support width is at most `0.80`.

Return one of:

- `joint_spread_rate_prey_effect_recovered`;
- `spread_rate_recovered_prey_effect_weak`;
- `prey_effect_recovered_spread_rate_weak`;
- `joint_spread_rate_prey_effect_not_recovered`; or
- `implementation_blocked`.

Any valid scientific outcome completes the goal.

## Compact Review Surface

Write exactly seven ignored files:

- `calibration_statistics.csv`;
- `validation_results.csv`;
- `representative_joint_surface.csv`;
- `benchmark_comparison.csv`;
- `summary.json`;
- `review.md`; and
- `joint_spread_rate_prey_effect.svg`.

The figure must show the representative joint likelihood surface and explain
the marginal recovery, precision, calibrated coverage, no-effect exclusion,
and predictive comparison in ordinary ecological language.

## Validation And Stop Rule

- one Goal 032 module and one thin CLI;
- four focused tests for exact rate scaling, two-dimensional support topology,
  decision logic, and the reduced-smoke bundle;
- one reduced local smoke, one timing probe, and one production ensemble;
- one inspection of the joint surface, comparison table, memo, and figure;
- Ruff, strict MyPy, one full test run, package build, and `git diff --check`;
- at most one material repair pass.

Do not estimate resistance, either detection probability, background hazard,
or additional prey parameters. Do not add cross-truth cells, change the survey
design, add false positives or prey abundance, retune grids or gates, fit real
data, or begin rescue work after a negative result. Stop at human review;
commit and publication require later acceptance.

Barry approved proceeding with Goal 032 on 12 August 2026.

## Outcome

The production outcome was `joint_spread_rate_prey_effect_not_recovered`, with
all implementation invariants passing. Joint coverage was calibrated
(`0.944`, Wilson interval `0.928-0.957`) and held-out prediction remained better
than the fitted neutral model. Spread-rate and prey-effect point estimates were
both centred near their truths, and fitted values showed essentially no
log-scale trade-off. However, the simulation-calibrated likelihood-ratio cutoff
was `53.955`: all `1000` joint supports were connected but all reached a grid
boundary, only `130/1000` excluded no prey effect, and the median prey-effect
support spanned the complete `1-10` grid.

The prespecified joint recovery claim is therefore rejected. The leading
post-run diagnosis is narrower: the site-marginal composite likelihood provides
useful point estimates and predictions, but its single joint uncertainty cutoff
does not adequately represent field-to-field variation in the shared invasion
wave. This is an uncertainty-calibration failure before it is evidence that
spread speed and prey effect are biologically confounded. No rescue or retuning
was attempted.
