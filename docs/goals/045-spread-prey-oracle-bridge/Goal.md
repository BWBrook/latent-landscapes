# Goal 045: The Cost of Estimating Predator Spread Speed

Status: approved by Barry on 5 September 2026; implementation in progress.
Programme role: Arc 2C, Charter Pillar 2, selected joint-recovery bridge.

## Question and completion condition

How much does estimating predator spread speed, instead of supplying its true
value, change recovery of the predator's effect on prey? Earlier arrival with
a smaller effect can resemble later arrival with a stronger effect. The result
is the paired difference between analyses of identical observations.

Complete the six-case comparison, evaluate the evidence with proportional
checks, produce an intelligible synthesis, review independently, consolidate
the new active path where warranted, and publish. A valid weak or negative
result completes the goal. Successful recovery in every case is not required.

## Frozen scientific design

| Condition | Spread rate rho | Prey hazard multiplier | Role |
| --- | ---: | ---: | --- |
| usual_1 | 1 | 1 | No-effect control |
| usual_3 | 1 | 3 | Transition candidate |
| usual_5 | 1 | 5 | Strong reference |
| slow_1 | 0.5 | 1 | Slow-wave no-effect control |
| slow_3 | 0.5 | 3 | Combined challenge |
| slow_5 | 0.5 | 5 | Slow-wave strong effect |

Retain the reference landscape, resistance eta=1, 160 access-constrained sites,
cluster-isolated 120 training/40 holdout allocation, days 10 through 60 in
10-day steps, two visits, and zero false positives. Both detection probabilities
are known at 0.65. Background prey hazard is known at 0.002/day, equivalent to
11.3% loss over 60 days without predators. Prey extirpation is absorbing.

The `known_speed` analysis estimates only prey effect. The `estimated_speed`
analysis estimates rho and prey effect jointly. All fitting and interval
construction use the same 120 training sites; the 40 holdout sites never fit
parameters. This differs from earlier recovery summaries that used all 160
sites, so historical headline gates are context, not exact replay targets.
Both analyses keep realised predator arrival latent. Within each site both
species share the same candidate arrival before integration. Across sites we
retain the site-marginal composite likelihood, with no spatial dependence claim.

Use the existing broad rho domain 0.25-4 (51 log-spaced points plus exact 0.5)
and effect domain 1-10 (181 linear points), including all generating values.
Rho scales each base arrival by 1/rho exactly under the accepted spread model.
Retain a 4096-draw arrival integration bank. Master seed is 20260905, independent
of Arc 2A/B. Use common random numbers across the six cases and paired analyses,
with separate integration, calibration, and evaluation streams.

Each case has 250 calibration and 250 independent evaluation datasets. The
239th ordered calibration statistic defines each local 95% cutoff. Calibrate
the known-speed effect profile, estimated-speed effect profile, and estimated-
speed rho profile separately. They provide parameter-specific intervals, not a
simultaneous region. Calibration still knows the generating condition; this
is a process-oracle relaxation, not a field-ready calibration method.

## Primary comparisons

Report paired changes in effect absolute log error, log interval width,
coverage, no-effect exclusion, and held-out conditional prey log score, plus
rho accuracy/precision and interval boundary/connectedness diagnostics.
Primary prediction is the average over holdout sites of
`log P(prey, predator | training fit) - log P(predator | same training fit)`.
Conditioning on holdout predator observations is permitted prediction input;
holdout prey observations only score predictions. The matched null fixes effect
at one with the same known background and detection. Its conditional prey score
is independent of rho and therefore identical between analyses. For secondary
joint scores the null uses the known true rho in the known-speed analysis and
estimates its own rho from training predator observations in the estimated-speed
analysis. Thus each secondary comparator has the same speed information as
the effect model it is compared with.

Resample complete calibration dataset indices and complete evaluation indices
separately, preserving pairing across analyses and cases. Recalculate cutoffs
and support metrics in 1000 bootstrap resamples from saved profiles, without
additional simulations. These intervals include calibration-sample variation,
but condition on this integration bank and generating model. Never resample
sites as independent units. Retain event yield and exposure as explanatory
truth-assisted diagnostics, not inference inputs.

Continuous differences and their uncertainty are primary. For context retain
prior effect error 0.20/log-width 0.80, rho error 0.10/log-width 0.50, and
approximately 95% exclusion/coverage benchmarks. Null cases have no interior
requirement at effect=1. Report false exclusions with binomial uncertainty;
do not require every descriptive coverage interval to contain 0.95. Distinguish
both-analyses-weak cases from deterioration specific to estimating speed.

Forecasts: central fivefold recovery should remain informative; slower spread
should reduce observed post-arrival events; the added estimation cost may be
largest near the threefold case. These are predictions, not acceptance tests.

## Stages and checks

1. Build a small joint likelihood using the accepted Arc 2B kernel, verify
   known-speed restriction and no-effect factorisation, and run a reduced
   end-to-end check plus a production-grid timing probe.
2. Freeze source before the detached six-case production run on deep-server.
3. Synthesize the paired evidence with a six-case table, ecological comparison
   figure, preselected first-evaluation-dataset likelihood plots, and memo.
4. Run one focused review/repair pass and independent final scientific review;
   preserve a compact active path and publish exact reviewed paths.

Tests protect likelihood equivalence, latent-arrival sharing, holdout exclusion,
parameter profiling, null factorisation, paired bootstrap resampling and file
round-trip. Check finite probabilities, split integrity, complete rows, and
grid/bank numerical stability on reduced canaries before production. A doubled
bank or refined-grid canary is numerical diagnosis, not new biological cases.
Retain compact raw profiles outside Git so bootstrap decisions are replayable.

## Authority and stop rules

Barry authorizes autonomous implementation, native specialist subagents,
remote execution, intermediate source commits/pushes, independent review,
bounded consolidation, and fast-forward publication to main. Stage exact
paths. No unrelated cleanup or destructive Git operations. External reads and
actions are limited to global skills/instructions, nectar control-plane docs,
deep-server under /data/codex, GitHub source publication, and the requested
Codex heartbeat. No legacy spatext dependency or sibling-project edits.

Use the Mac mini for development and deep-server for detached production after
timing/memory checks. Escalate projected production over 24 hours or a material
scientific change. Once launched, check every two hours with a quiet heartbeat;
while running, perform only a bounded status probe and end the wake. On success,
retrieve evidence and resume review/closeout. On failure, diagnose the cause
before proposing a rerun; never silently change the scientific design. Pause
the heartbeat once the goal is complete or human input is required.

No unknown background/detection, new landscape, sampling change, enrichment,
new response surfaces, simultaneous-coverage claim, real data, or next goal.
Stop after the six cases and the material review pass. Do not chase a desired
recovery threshold. Material numerical failure or contradictory calibration
can trigger diagnosis; a negative ecological result is not an implementation bug.

## Execution record

- 2026-09-05: scope approved; source branch created from clean main at 4d6d23b.
- Implemented separate design, shared-arrival likelihood, paired campaign and
  synthesis modules, reusing the accepted Arc 2B kernel rather than copying it.
- Local reduced campaign passed all 12 structural/numerical invariants. The
  reduced synthesis wrote seven review files and 18 parameter-summary rows;
  reduced runs are explicitly labelled non-scientific. Diagnostic event
  accounting refers to the 120 training sites.
- Focused new-module and Arc 2B regression tests: 28 passed. Scoped Ruff and
  strict mypy passed. Independent review prompted a tight floating-point
  tolerance for equivalent no-effect event times, explicit null-case direction
  labels, and consistent nonproduction outcomes; no scientific design changed.
- Full-grid-shaped local likelihood probe: 0.590 GB integration storage,
  approximately 0.831 GB process peak, six evaluations in 0.63 seconds serial
  or 0.26 seconds across six threads. This used a small bank and is timing
  evidence only, not the full-bank numerical check.
- The prespecified numerical canary uses the first evaluation dataset in each
  frozen case, nested 4096/8192 integration banks and local half-grid checks.
  Review limits: effect log-MLE change 0.05, rho log-MLE change 0.06, profile LR
  change 0.5 within the original LR<=10 range, and local maximum log-likelihood
  gain 0.25. All three parameter profiles and both analysis maxima are checked.
  These are numerical review prompts, not new ecological selection gates.
- Full-bank timing, canary results, frozen source SHA, and remote production
  location will be recorded before the scheduled-monitoring handoff.
