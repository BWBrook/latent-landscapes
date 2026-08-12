# Goal 033: Parameter-Specific Uncertainty Calibration Diagnostic

## Scientific Question

Is the prey effect genuinely weak when predator spread speed is unknown, or did
Goal 032 lose it because one joint uncertainty cutoff had to absorb variation in
both quantities at once?

## Frozen Experiment

Repeat the accepted Goal 032 central-truth experiment without changing its
biology, landscape, sampling, observations, likelihood, grids, simulation bank,
seeds, or replicate counts. In particular, retain:

- true predator spread rate `rho = 1` and resistance contrast `eta = 1`;
- background prey-extirpation hazard `0.002` and true post-arrival hazard ratio
  `5`;
- known predator and prey detection probabilities `0.65`, with zero false
  positives;
- the 160-site access-constrained training/holdout design and survey days
  `10, 20, 30, 40, 50, 60`;
- the exact within-site shared-arrival likelihood and site-marginal treatment
  across sites;
- the 51-point spread-rate and 91-point prey-effect grids;
- the same `4,096` arrival-bank draws, `2,000` calibration datasets, 1901st
  ordered calibration rank, and `1,000` validation datasets; and
- master seed `20260812032`.

Use the published Goal 032 bundle as a read-only anchor and reproduce its joint
likelihood-ratio statistics, fitted values, observation counts, and integration
bank exactly.

## New Diagnostic

For every fitted two-dimensional likelihood surface, derive two one-dimensional
profile curves:

1. spread-rate profile: at each candidate spread rate, retain the best-fitting
   prey effect; and
2. prey-effect profile: at each candidate prey effect, retain the best-fitting
   spread rate.

During calibration, record the likelihood-ratio drop at the true value on each
profile and use the prespecified 1901st ordered value as that parameter's 95%
cutoff. During validation, use those two cutoffs to construct separate marginal
support intervals.

These are parameter-specific 95% intervals. They do not form a simultaneous 95%
joint region and must not replace Goal 032's accepted negative joint result.

## Prespecified Decision

The prey effect is `prey_effect_recoverable_under_parameter_specific_calibration`
only if:

- all source-reconciliation, generation, likelihood, seed, and count invariants
  pass;
- the 95% Wilson interval for marginal prey-effect coverage contains `0.95`;
- at least `950/1000` prey-effect supports are connected and avoid artificial
  grid boundaries;
- at least `950/1000` prey-effect supports exclude hazard ratio `1`;
- median absolute log-effect error is at most `0.20`; and
- median log-effect support width is at most `0.80`.

Otherwise return
`prey_effect_remains_weak_under_parameter_specific_calibration`, provided the
run is valid. Return `implementation_blocked` only if an invariant or required
calculation fails.

Report the corresponding spread-rate marginal coverage, topology, point error,
and width against the existing Goal 032 limits (`0.10` error and `0.50` width),
but do not make spread-rate success an additional gate on the prey-effect
diagnosis.

Any valid scientific outcome completes the goal.

## Compact Review Surface

Write exactly seven ignored files:

- `calibration_profile_statistics.csv`;
- `validation_marginal_intervals.csv`;
- `marginal_summary.csv`;
- `representative_profile_curves.csv`;
- `summary.json`;
- `review.md`; and
- `parameter_specific_calibration.svg`.

The memo and figure must distinguish observed results from interpretation and
explain in ordinary ecological language whether Goal 032's wide prey-effect
region arose mainly from the shared joint cutoff.

## Validation And Stop Rule

- one Goal 033 module and one thin CLI;
- four focused tests covering profile statistics/support, decision logic,
  source-anchor rejection, and the reduced-smoke bundle;
- one reduced local smoke and one production ensemble, using `deep-server` if
  available;
- one inspection of the tables, memo, and figure;
- Ruff, strict MyPy, the full test suite, package build, and `git diff --check`;
- at most one material repair pass.

Do not alter Goal 032, change the model or observation design, add parameters,
retune grids or gates, claim simultaneous joint coverage, add cross-truth cells,
fit real data, or begin a dependence-aware rescue. Stop at human review; commit
and publication require later acceptance.

Barry approved proceeding with Goal 033 on 12 August 2026.

## Outcome

The production outcome was
`prey_effect_recoverable_under_parameter_specific_calibration`, with every
replay and implementation invariant passing. The separate spread-rate profile
retained a large cutoff (`53.019`), whereas the prey-effect profile cutoff was
only `3.574`. Prey-effect coverage was `0.946` (Wilson interval
`0.930-0.958`), `994/1000` supports were connected and interior, all
`1000/1000` excluded no effect, median absolute log error was `0.128`, and
median log width was `0.693`.

This does not reverse Goal 032's negative result for a simultaneous joint
region. It shows, more specifically, that the joint cutoff was dominated by
spread-wave variation: when uncertainty was calibrated separately, the prey
effect remained identifiable and met every prespecified marginal gate. No
biology, design, likelihood, grid, seed, or decision threshold was changed.
