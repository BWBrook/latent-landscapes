# Goal 030: Joint Prey-Effect and Detection-Probability Positive Control

## Scientific Question

With predator arrival known exactly, do two visits per survey contain enough
information to distinguish prey nondetection from predator-driven prey loss
while estimating both processes jointly?

## Frozen Experiment

Retain the accepted Goal 029 landscape, 160-site sampling design, central
stochastic predator truth, exact realized arrival times, background
prey-extirpation hazard `0.002`, true fivefold post-arrival hazard multiplier,
survey days `10, 20, 30, 40, 50, 60`, two visits per survey, true detection
probability `0.65`, zero false positives, and training/holdout split.

Estimate exactly two parameters:

- post-arrival prey-extirpation hazard ratio; and
- per-visit prey-detection probability.

Use the existing hazard-ratio grid and a prespecified detection grid from
`0.35` to `0.90` in increments of `0.025`. The truth must occur exactly once
on both grids. The constant-hazard neutral comparator must estimate both its
extirpation hazard and detection probability under the identical latent-state
observation process.

Run one independent ensemble:

- master seed `20260812030`;
- `2,000` calibration datasets;
- the 1901st ordered joint likelihood-ratio statistic as the fixed 95% cutoff;
  and
- `1,000` validation datasets.

Use the published Goal 029 known-detection result as a read-only anchor. Do not
rerun it. The production ensemble may use `deep-server` with bounded
replicate-level parallelism after a local reduced smoke passes.

## Prespecified Decision

Common gates:

- all generation, observation, split, seed, likelihood, anchor, and count
  invariants pass;
- the 95% Wilson interval for joint-support coverage contains `0.95`;
- at least `950/1000` joint supports are connected and interior; and
- mean held-out log-score advantage over the fitted neutral has a 95% lower
  bound above zero.

Effect-recovery gates:

- at least `950/1000` joint supports exclude hazard ratio `1`;
- median absolute log-effect error is at most `0.20`; and
- median marginal log-effect support width is at most `0.80`.

Detection-recovery gates:

- median absolute detection-probability error is at most `0.05`; and
- median marginal detection-probability support width is at most `0.15`.

Return one of:

- `joint_prey_effect_detection_recovered`;
- `prey_effect_recovered_detection_weak`;
- `detection_recovered_prey_effect_weak`;
- `joint_prey_effect_detection_not_recovered`; or
- `implementation_blocked`.

Any valid scientific outcome completes the goal.

## Compact Review Surface

Write exactly eight ignored files:

- `calibration_statistics.csv`;
- `validation_results.csv`;
- `representative_prey_observations.csv`;
- `representative_joint_likelihood.csv`;
- `benchmark_comparison.csv`;
- `summary.json`;
- `review.md`; and
- `joint_prey_effect_detection.svg`.

## Validation And Stop Rule

- one Goal 030 module and one thin CLI;
- four focused tests for joint likelihood behavior, joint-support topology,
  decision logic, and the reduced-smoke bundle;
- one local reduced smoke and one production ensemble;
- one inspection of the joint surface, comparison table, memo, and figure;
- Ruff, strict MyPy, one full test run, package build, and `git diff --check`;
- at most one material repair pass.

Do not add false positives, uncertain predator arrival, alternative survey
schedules, other effect or detection truths, prey abundance, predator fitting,
real data, or further joint parameters. Do not tune grids or gates after seeing
the result. Stop at human review; commit and publication require later
acceptance.

Barry approved proceeding with Goal 030 on 12 August 2026.

## Outcome

The production ensemble returned
`detection_recovered_prey_effect_weak` under the strict prespecified decision.
Joint-support coverage was `954/1000 = 0.954` (95% Wilson interval `0.939` to
`0.965`), and `982/1000` supports were connected and interior. All `1000/1000`
supports excluded no predator effect. Mean held-out advantage over the neutral
model was `0.0509` per site (95% interval `0.0478` to `0.0541`).

Detection probability was sharply recovered. The median fitted value was the
true `0.65`; the 10th to 90th percentile of fitted values was `0.625` to
`0.675`, and median marginal support width was one grid increment (`0.025`).
The zero median absolute error reflects the prespecified `0.025` grid and
should not be read as literally error-free estimation.

The prey effect was detected and point-estimated well, but missed the strict
precision gate. Median absolute log-effect error remained `0.128`, identical
to the known-detection anchor, while median marginal log-support width widened
from `0.719` to `0.921` against the `0.800` gate. The representative joint
surface was narrow along detection probability and broad mainly along effect
size. Thus severe effect-detection confounding is not supported; the valid
negative outcome is specifically that a simultaneous 95% joint region does
not retain the previous effect-width precision.

## Validation

The four focused tests, multiprocessing reduced smoke, one production
ensemble, exact eight-file artifact contract, two-dimensional likelihood
surface, comparison table, memo, and browser-rendered figure were checked. The
production run completed on `deep-server` in 58 seconds using 24 bounded
replicate workers under
`/data/codex/scratch/goal030-20260812T023948Z`. The one material repair pass
changed only the detection-estimate panel; simulations and numerical outcomes
were not rerun. Final checks comprised the full test suite, Ruff, strict MyPy,
package build, and `git diff --check`. Generated artifacts and build outputs
remained ignored and unstaged. Goal 030 stops at human review; no Goal 031 work
was started.
