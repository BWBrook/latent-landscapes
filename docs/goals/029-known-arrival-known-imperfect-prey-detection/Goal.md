# Goal 029: Known-Arrival, Known-Imperfect-Prey-Detection Positive Control

## Scientific Question

Does the accepted fivefold predator effect remain recoverable when predator
arrival is known exactly but prey persistence is observed imperfectly?

## Frozen Benchmark

Retain the accepted Goal 027 ecological process and design:

- the fixed synthetic landscape and 160 sampled sites;
- the central stochastic predator truth with realized arrival known at every
  site;
- background prey-extirpation hazard `0.002`;
- a true fivefold post-arrival hazard multiplier;
- surveys on days `10, 20, 30, 40, 50, 60`;
- the existing training/holdout split, hazard-ratio grid, constant-hazard
  neutral comparator, calibrated likelihood-support construction, and recovery
  gates.

Replace perfect prey-state observation with exactly two independent visits at
each survey. Conditional on prey persistence, each visit detects prey with
known probability `p = 0.65`; after extirpation, false-positive probability is
zero. Fit only the predator-effect multiplier. The likelihood must integrate
over latent persistence and extirpation histories, so a zero count is not
treated as proof of extirpation. The neutral comparator must use the identical
imperfect-detection observation process.

Use one independent production ensemble:

- master seed `20260811029`;
- `2,000` calibration datasets;
- the 1901st ordered likelihood-ratio statistic as the fixed 95% cutoff; and
- `1,000` validation datasets.

The accepted Goal 027 perfect-observation result is a read-only comparison
anchor and must not be rerun.

## Recovery Decision

Return `known_imperfect_prey_detection_recovered` only when:

- generation, split, observation-process, seed, and finite-likelihood
  invariants pass;
- the 95% Wilson interval for validation coverage contains `0.95`;
- at least `950/1000` supports are connected and interior;
- at least `950/1000` supports exclude hazard ratio `1`;
- median absolute log-effect error is at most `0.20`;
- median log support width is at most `0.80`; and
- mean held-out log-score advantage over the observation-aware neutral has a
  95% lower bound above zero.

Otherwise return `known_imperfect_prey_detection_not_recovered`, unless an
invariant fails, in which case return `implementation_blocked`. Any valid
scientific outcome completes the goal.

## Compact Review Surface

Write exactly seven ignored files:

- `calibration_statistics.csv`;
- `validation_results.csv`;
- `representative_prey_observations.csv`;
- `benchmark_comparison.csv`;
- `summary.json`;
- `review.md`; and
- `known_imperfect_prey_detection.svg`.

## Validation And Stop Rule

- one Goal 029 module and one thin CLI;
- four focused tests covering latent-state likelihood behavior, generation,
  decision logic, and the reduced-smoke bundle;
- one reduced smoke and one production run;
- one inspection of the comparison table, memo, and figure;
- Ruff, strict MyPy, one full test run, package build, and `git diff --check`;
- at most one material repair pass.

Do not estimate detection probability, add false positives, change survey
timing, make predator arrival uncertain, add alternative truths, fit predator
spread, introduce joint predator-prey inference, or run real data. Stop at
human review; commit and publication require later acceptance.

Barry approved proceeding with Goal 029 on 12 August 2026.

## Outcome

The production ensemble returned
`known_imperfect_prey_detection_recovered`. With two visits per survey and
known detection probability `0.65`, calibrated coverage was
`956/1000 = 0.956` (95% Wilson interval `0.941` to `0.967`). All `1000/1000`
supports excluded no predator effect, and `994/1000` were connected and
interior.

Imperfect observation produced a modest, coherent loss of information relative
to the accepted perfect-observation anchor. Median absolute log-effect error
increased from `0.117` to `0.128`, median log support width increased from
`0.663` to `0.719`, and mean held-out advantage over neutral decreased from
`0.0688` to `0.0513` per site. The latter remained unambiguously positive
(95% interval `0.0480` to `0.0547`). Every prespecified recovery gate passed.

This establishes the intended positive control: a known observation process
can be integrated explicitly without first reconstructing an extirpation date,
and a fivefold effect remains identifiable under moderate missed detection.
Detection probability remains known and predator arrival remains exact; the
result does not yet establish joint identifiability.

## Validation

The four focused tests, reduced smoke, one production ensemble, exact
seven-file review bundle, comparison table, review memo, and browser-rendered
figure were checked. The production run completed locally in 3 minutes 36
seconds. The single material repair pass corrected figure layout only; it did
not rerun simulations or alter numerical evidence. Final checks comprised the
full test suite, Ruff, strict MyPy, package build, and `git diff --check`.
Generated artifacts and build outputs remained ignored and unstaged. Goal 029
stops at human review; no Goal 030 work was started.
