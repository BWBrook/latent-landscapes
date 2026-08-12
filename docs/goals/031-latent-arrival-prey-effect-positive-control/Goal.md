# Goal 031: Latent-Arrival Prey-Effect Positive Control

## Scientific Question

Can the fivefold predator effect on prey persistence still be recovered when
the realized predator-arrival map is hidden and inferred only from direct,
imperfect predator detections?

## Frozen Experiment

Retain the accepted Goal 029 landscape, 160-site access-constrained design,
central stochastic predator process (`rho = 1`, resistance contrast `eta = 1`),
background prey-extirpation hazard `0.002`, true fivefold post-arrival hazard
multiplier, survey days `10, 20, 30, 40, 50, 60`, training/holdout split, two
visits per survey, known per-visit detection probability `0.65`, and zero false
positives for both species.

Change exactly one scientific condition: do not give the likelihood the
realized predator-arrival map. Instead, generate direct predator-detection
histories and integrate over an independent `4,096`-draw arrival bank from the
known central spread process. Within each site, predator and prey histories
must be evaluated against the same arrival draw before marginalization. Across
sites, retain the deliberately simple site-marginal composite likelihood; do
not claim that shared landscape-process dependence has been modelled.

Estimate exactly one parameter: the post-arrival prey-extirpation hazard
ratio. Keep spread rate, resistance contrast, predator detection, prey
detection, background hazard, and false-positive rates fixed and known. Use the
Goal 029 hazard-ratio grid and its observation-aware constant-hazard neutral
comparator. The neutral receives the same predator observations and prey
detection model.

Run one independent ensemble:

- master seed `20260812031`;
- `4,096` integration-bank draws with Jeffreys-smoothed arrival categories;
- `2,000` calibration datasets;
- the 1901st ordered likelihood-ratio statistic as the fixed 95% cutoff; and
- `1,000` validation datasets.

Use the published Goal 029 known-arrival result as a read-only benchmark. Do
not rerun it. Production may use `deep-server` after a reduced local smoke.

## Prespecified Decision

Require:

- all generation, bank, shared-arrival, observation, split, seed, likelihood,
  benchmark, and count invariants to pass;
- the 95% Wilson interval for support coverage to contain `0.95`;
- at least `950/1000` supports to be connected and interior;
- at least `950/1000` supports to exclude hazard ratio `1`;
- median absolute log-effect error at most `0.20`;
- median log-effect support width at most `0.80`; and
- mean held-out log-score advantage over the fitted neutral to have a 95%
  lower bound above zero.

Return one of:

- `latent_arrival_prey_effect_recovered`;
- `latent_arrival_prey_effect_not_recovered`; or
- `implementation_blocked`.

Any valid scientific outcome completes the goal.

## Compact Review Surface

Write exactly eight ignored files:

- `calibration_statistics.csv`;
- `validation_results.csv`;
- `representative_cross_layer_histories.csv`;
- `arrival_conditioning_summary.csv`;
- `benchmark_comparison.csv`;
- `summary.json`;
- `review.md`; and
- `latent_arrival_prey_effect.svg`.

The arrival-conditioning table is diagnostic: it must compare the prior bank
arrival distribution with the distribution conditioned on the representative
predator history, without using prey outcomes or adding a fitted parameter.

## Validation And Stop Rule

- one Goal 031 module and one thin CLI;
- four focused tests for shared-arrival coupling, bank moments, decision logic,
  and the reduced-smoke bundle;
- one local reduced smoke and one production ensemble;
- one inspection of the comparison table, conditioning diagnostic, memo, and
  figure;
- Ruff, strict MyPy, one full test run, package build, and `git diff --check`;
- at most one material repair pass.

Do not estimate predator spread, resistance, either detection probability, or
additional prey parameters. Do not change the observation design, add false
positives, add prey abundance, fit real data, retune the grid or gates, or
progress to joint spread-effect inference. Stop at human review; commit and
publication require later acceptance.

Barry approved proceeding with Goal 031 on 12 August 2026.

## Outcome

The production ensemble returned `latent_arrival_prey_effect_recovered`.
Support coverage was `963/1000 = 0.963` (95% Wilson interval `0.949` to
`0.973`), with `993/1000` connected interior supports. Every support excluded
the no-effect value. Median absolute log-effect error was `0.128`, median
log-support width was `0.757`, and mean held-out advantage over the neutral was
`0.0530` per site (95% interval `0.0499` to `0.0560`). All prespecified gates
passed.

Relative to Goal 029's exact-arrival benchmark, point error was unchanged and
support widened modestly from `0.719` to `0.757`; there was no qualitative
loss of recovery. In the representative validation dataset, direct predator
detections occurred at `147/160` sites. Conditioning on predator histories
reduced median absolute arrival error from `1.28` to `1.23` time units. The
small gain is itself informative: the known central spread process already
constrained sitewise arrival tightly, while detections especially protected
sites whose realized timings departed from that prior.

The result establishes a positive control for one prey-effect parameter under
latent arrival. It does not establish recovery when spread parameters are
unknown, nor does it model between-site dependence induced by the shared
spread field.

## Validation

Four focused tests, a multiprocessing reduced smoke, and one frozen production
ensemble were run. Production completed on `deep-server` with 24 workers under
`/data/codex/scratch/goal031-20260812T030918Z`. One review repair removed a
redundant overlapping figure footer; the repaired run replayed identical seeds
and all numerical outputs were required to remain unchanged. Final checks
comprised the focused tests, full test suite, Ruff, strict MyPy, package build,
and `git diff --check`. Generated artifacts and build outputs remained ignored
and unstaged. Goal 031 stops at human review; no Goal 032 work was started.
