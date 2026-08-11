# Goal 026: Known-Arrival Prey-Persistence Positive Control

## Scientific Question

When every local predator-arrival time is supplied correctly, can we recover a
single predator effect on local prey persistence and predict held-out prey
histories better than a neutral time-only model?

## Frozen Positive Control

Use the accepted synthetic landscape, 160-site sampling design, and central
stochastic predator truth `(rho, eta) = (1, 1)`. Predator arrival varies among
sites and process realizations, but its realized value is treated as known by
the prey likelihood. Do not estimate predator parameters in this goal.

At every sampled site:

- prey are present at time zero and extirpation is absorbing;
- the background extirpation hazard is known and fixed at `0.002` per time
  unit;
- after predator arrival, the hazard is multiplied by the sole estimand
  `hazard_ratio`, whose truth is `5.0`;
- prey state is observed without error at days `10, 20, 30, 40, 50, 60`; and
- extirpation is therefore observed as an interval between successive surveys,
  or right-censored at day 60.

Profile the hazard ratio over `1.0, 1.05, ..., 10.0`. Calibrate a 95%
likelihood-ratio support cutoff from 250 independent histories using the 239th
ordered statistic, then validate on 250 further histories. The development
check that selected the frozen effect size is not production evidence and must
not be revisited after the production result.

## Neutral Comparator

Fit a one-parameter constant extirpation hazard to the training clusters. This
neutral model ignores predator arrival but assigns finite probability to every
possible interval-censored or right-censored history. Compare its held-out mean
log score with the one-parameter predator-arrival model fitted on the same
training clusters. This is a predictive baseline, not an ecological null truth.

## Decision

Return `known_arrival_prey_effect_recovered` only when:

- all data-generation, censoring, split, and finite-likelihood invariants pass;
- the 95% Wilson interval for validation coverage contains `0.95`;
- at least `238/250` validation supports are connected and interior;
- at least `238/250` validation supports exclude `hazard_ratio = 1`;
- median absolute log-hazard-ratio error is at most `0.20`;
- median log-scale support width is at most `0.80`; and
- the 95% interval for mean held-out log-score advantage over the neutral model
  lies wholly above zero.

Otherwise return `known_arrival_prey_effect_not_recovered`, unless an invariant
failure yields `implementation_blocked`. Do not retune the truth, grids, or
gates after seeing production evidence.

## Compact Review Surface

Write exactly six ignored files:

- `calibration_statistics.csv`;
- `validation_results.csv`;
- `representative_prey_histories.csv`;
- `summary.json`;
- `review.md`; and
- `prey_persistence_positive_control.svg`.

## Validation And Stop Rule

- one Goal 026 scientific module and one CLI;
- four focused tests covering interval likelihood, simulation/censoring,
  decision logic, and the reduced-smoke review surface;
- one reduced non-scientific smoke, one production run, and one visual/table
  inspection;
- Ruff, strict MyPy, one full test run, package build, and `git diff --check`;
- at most one focused repair pass.

Do not add habitat-specific prey effects, abundance dynamics, imperfect prey
detection, uncertain predator arrival, joint predator-prey fitting, alternative
effect truths, broad sweeps, or real data. Stop at human review; commit and
publication require later acceptance.

Barry approved proceeding with Goal 026 on 11 August 2026.

## Outcome

The production ensemble returned
`known_arrival_prey_effect_not_recovered`, but for one narrowly defined reason.
The prey-effect signal itself was strong: all `250/250` validation supports
excluded the no-effect value, all `250/250` supports were connected and
interior, median absolute log-effect error was `0.115`, and median log-scale
support width was `0.622`. The predator-arrival model also beat the fitted
constant-hazard neutral model on held-out sites by `0.0692` log-score units per
site on average (95% interval `0.0622` to `0.0762`).

The sole failed gate was support calibration. The true fivefold effect was
inside `230/250 = 0.920` validation supports; its 95% Wilson interval was
`0.880` to `0.948`, ending just below the prespecified `0.95` target. The strict
overall decision therefore remains negative because the support sets slightly
under-covered, not because the effect was biased, indistinguishable from no
effect, imprecise, or predictively unhelpful.

No effect truth, grid, cutoff rank, threshold, observation process, or model was
retuned after the production result.

## Validation

The reduced smoke, frozen production ensemble, exact six-file artifact
contract, calibration and validation tables, review memo, and rendered figure
were inspected. The figure uses explicit stable spacing, keeps legends outside
the data, depicts the fixed access network, and reports the support-coverage
count alongside effect recovery. Final repository checks comprised the focused
Goal 026 tests, full test suite, Ruff formatting and linting, strict MyPy,
package build, and `git diff --check`. Generated artifacts and build outputs
remained ignored and unstaged. Goal 026 stops at human review; no Goal 027 work
was started.
