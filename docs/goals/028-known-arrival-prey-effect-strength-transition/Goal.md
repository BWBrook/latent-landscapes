# Goal 028: Known-Arrival Prey-Effect Strength Transition

## Scientific Question

With predator arrival known and prey state observed perfectly, how strong must
the predator effect be before the existing sampling design can recover it
reliably and outperform a time-only neutral model?

## Frozen Three-Point Ladder

Retain every accepted Goal 026-027 element: landscape, 160-site design, central
stochastic predator process, known realized arrival times, background prey
hazard `0.002`, perfect prey observation at days `10, 20, 30, 40, 50, 60`,
absorbing interval-censored extirpation, hazard-ratio grid, constant-hazard
neutral comparator, training/holdout split, recovery gates, and calibrated
likelihood-support construction.

Use the published Goal 027 fivefold effect as the strong anchor. Evaluate
exactly two new truths:

- `twofold_effect`: hazard ratio `2.0`, master seed `202608110282`; and
- `threefold_effect`: hazard ratio `3.0`, master seed `202608110283`.

Calibrate each new truth independently with `2,000` calibration histories, the
1901st ordered likelihood-ratio statistic, and `1,000` validation histories.
Do not rerun or recompute the accepted fivefold anchor.

## Per-Truth Recovery Gate

A truth is recovered only when:

- all generation, censoring, split, and finite-likelihood invariants pass;
- its 95% Wilson coverage interval contains `0.95`;
- at least `950/1000` supports are connected and interior;
- at least `950/1000` supports exclude hazard ratio `1`;
- median absolute log-effect error is at most `0.20`;
- median log support width is at most `0.80`; and
- mean held-out log-score advantage over the neutral model has a 95% lower
  bound above zero.

## Transition Decision

After exact Goal 027 anchor reconciliation, return:

- `prey_effect_transition_below_twofold` if both new truths are recovered;
- `prey_effect_transition_between_twofold_and_threefold` if threefold is
  recovered but twofold is not;
- `prey_effect_transition_between_threefold_and_fivefold` if neither new truth
  is recovered; or
- `prey_effect_transition_nonmonotonic` if twofold is recovered but threefold
  is not.

Invariant or anchor failures return `implementation_blocked`. Any valid
transition outcome completes the goal. Do not add another midpoint or alter a
gate after seeing the result.

## Compact Review Surface

Write exactly six ignored files:

- `calibration_statistics.csv`;
- `validation_results.csv`;
- `effect_transition_summary.csv`;
- `summary.json`;
- `review.md`; and
- `prey_effect_strength_transition.svg`.

## Validation And Stop Rule

- one thin Goal 028 module and one CLI;
- three focused tests for anchor reconciliation, transition logic, and the
  exact reduced-smoke bundle;
- one reduced smoke and one production run;
- one inspection of the transition table, memo, and figure;
- Ruff, strict MyPy, one full test run, package build, and `git diff --check`;
- at most one material repair pass.

Do not introduce imperfect prey detection, uncertain predator arrival,
alternative background hazards, habitat effects, abundance dynamics, joint
fitting, further effect truths, or real data. Stop at human review; commit and
publication require later acceptance.

Barry approved proceeding with Goal 028 on 11 August 2026.

## Outcome

The production ladder returned
`prey_effect_transition_between_threefold_and_fivefold` under the strict full
recovery definition.

The twofold effect was genuinely weakly identified. Coverage was
`941/1000 = 0.941` with its Wilson interval containing `0.95`, and held-out
prediction still beat neutral. However, only `653/1000` supports excluded no
effect, the same number were connected and interior, and median log support
width was `0.924` against the `0.800` precision gate.

The threefold effect occupied an informative intermediate state. It excluded
no effect in `986/1000` validation datasets, had median absolute log-effect
error `0.143`, and beat neutral by `0.0248` log-score units per held-out site.
It was nevertheless not fully recovered because median log support width was
`0.830`, narrowly above the precision gate, while conservative coverage was
`973/1000 = 0.973` with its Wilson interval lying above nominal `0.95`.

The accepted fivefold anchor remained fully recovered: coverage `0.954`,
`1000/1000` exclusions of no effect, median log support width `0.663`, and
held-out advantage `0.0688` per site. Thus the strict precision transition lies
between threefold and fivefold, while reliable detection of a nonzero predator
effect is already achieved at threefold. No additional midpoint was attempted.

## Validation

The reduced smoke, two independent production ensembles, accepted Goal 027
anchor, exact six-file artifact contract, transition table, memo, and rendered
four-panel figure were inspected. The production run completed locally in
7 minutes 10 seconds. The single review pass added the prespecified support
width to the figure and clarified the distinction between detection and full
precision; no simulation was rerun and no numerical outcome changed. Final
repository checks comprised the focused Goal 028 tests, full test suite, Ruff,
strict MyPy, package build, and `git diff --check`. Generated artifacts and
build outputs remained ignored and unstaged. Goal 028 stops at human review;
no Goal 029 work was started.
