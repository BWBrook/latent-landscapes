# Goal 027: Known-Arrival Support-Calibration Confirmation

## Scientific Question

Was Goal 026's `230/250 = 0.920` support coverage a finite-calibration
fluctuation, or does the known-arrival prey likelihood persistently
under-cover its true fivefold predator effect?

## Frozen Confirmation

Reuse the published Goal 026 engine without changing its landscape, 160-site
design, central stochastic predator truth, known realized arrival times,
background prey hazard `0.002`, true post-arrival hazard ratio `5.0`, perfect
prey observation, survey calendar, interval-censored likelihood, candidate
grid, neutral comparator, training/holdout split, or scientific recovery gates.

Run one independent higher-resolution ensemble only:

- master seed `20260811027`;
- `2,000` calibration histories;
- the 1901st ordered likelihood-ratio statistic as the fixed 95% cutoff; and
- `1,000` validation histories.

The larger calibration phase reduces noise in the estimated 95th percentile.
It is not permission to choose among seeds, ranks, cutoffs, or interval methods
after seeing the result.

## Decision

First require the published Goal 026 anchor to reconcile exactly and every
Goal 026 effect-information gate to remain satisfied: connected interior
support, exclusion of no effect, point recovery, support precision, and
held-out prediction against neutral.

Then return:

- `support_calibration_confirmed` when the 95% Wilson interval for validation
  coverage contains `0.95`;
- `persistent_support_undercoverage` when its upper bound remains below
  `0.95`;
- `support_calibration_inconclusive` for overcoverage or another non-directional
  calibration result; or
- `effect_recovery_changed` / `implementation_blocked` if the inherited
  scientific or implementation gates no longer hold.

Any scientifically valid outcome completes the goal. Do not run another seed,
increase the ensemble again, change the rank, or compare alternative interval
constructions within Goal 027.

## Compact Review Surface

Write exactly six ignored files:

- `calibration_statistics.csv`;
- `validation_results.csv`;
- `coverage_comparison.csv`;
- `summary.json`;
- `review.md`; and
- `support_calibration_confirmation.svg`.

## Validation And Stop Rule

- one thin Goal 027 module and one CLI;
- three focused tests for anchor reconciliation, decision logic, and the exact
  reduced-smoke bundle;
- one reduced smoke and one production run;
- one inspection of the comparison table, memo, and figure;
- Ruff, strict MyPy, one full test run, package build, and `git diff --check`;
- at most one material repair pass.

Do not add prey biology, imperfect detection, uncertain arrival, joint fitting,
new truths, or alternative calibration machinery. Stop at human review; commit
and publication require later acceptance.

Barry approved proceeding with Goal 027 on 11 August 2026.

## Outcome

The independent higher-resolution ensemble returned
`support_calibration_confirmed`. The 1901st ordered calibration statistic gave
a cutoff of `4.029`. Validation coverage was `954/1000 = 0.954`, with a 95%
Wilson interval of `0.939` to `0.965` containing the nominal `0.95` target.
Goal 026's `230/250 = 0.920` result is therefore consistent with noise in its
smaller empirical calibration cutoff rather than persistent undercoverage.

The inherited effect-information evidence remained stable: `997/1000`
supports were connected and interior, `1000/1000` excluded no predator effect,
median absolute log-effect error was `0.117`, and median log support width was
`0.663`. Mean held-out log-score advantage over the constant-hazard neutral was
`0.0688` per site (95% interval `0.0654` to `0.0723`).

No alternative seed, rank, cutoff, interval method, truth, observation process,
or biological model was tested. This closes the calibration question and
supports advancing beyond the known-arrival/perfect-prey-observation foundation
stone after collaborator review.

## Validation

The reduced smoke, one production ensemble, exact six-file artifact contract,
coverage comparison, review memo, validation table, and rendered figure were
inspected. The production run completed locally in 3 minutes 30 seconds. Final
repository checks comprised the focused Goal 027 tests, full test suite, Ruff
formatting and linting, strict MyPy, package build, and `git diff --check`.
Generated artifacts and build outputs remained ignored and unstaged. Goal 027
stops at human review; no Goal 028 work was started.
