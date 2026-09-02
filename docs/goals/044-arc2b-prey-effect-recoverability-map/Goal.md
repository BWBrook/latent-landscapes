# Goal 044: Arc 2B Prey-Effect Recoverability Map

## Programme role

This goal completes Roadmap Arc 2B and advances Charter Pillar 2. It replaces
isolated prey-response positive controls with a prospectively tested map of
when the predator effect on prey persistence is recoverable across ecological
signal, background event yield, and prey observability.

Goal 044 is the first full Twilight Laboratory tranche. Barry approved the
scientific destination and staged design on 2 September 2026. The orchestrator
may execute the stages autonomously inside the boundaries below, provide
non-blocking progress updates, and pause only at a named scientific or
operational escalation boundary.

## Scientific question

Across the accepted reference landscape and sampling design, how do true
predator-effect strength, counterfactual 60-day background prey-extirpation
risk, and known prey-detection probability jointly determine:

- accuracy and precision of the estimated predator effect;
- calibrated uncertainty and reliable exclusion of no effect; and
- held-out predictive advantage over an observation-matched neutral model?

The intended output is an interpretable recoverability map, not a catalogue of
independent pass/fail cells.

## Frozen scientific context

- accepted 72 by 84 reference landscape and access network;
- 160 sites with the accepted cluster-isolated 120/40 training/holdout split;
- surveys on days 10, 20, 30, 40, 50, and 60, with two visits per survey;
- zero false positives for predator and prey observations;
- central stochastic predator process `rho = 1` and resistance contrast
  `eta = 1`;
- known per-visit predator detection probability `0.65`;
- latent realised predator arrival, integrated through one independent
  4,096-draw arrival bank from the known central process;
- absorbing prey extirpation and the accepted observation-aware constant-
  hazard neutral comparator; and
- the parameter-specific calibrated likelihood-support interpretation used by
  the accepted prey-effect positive controls.

Within each site, predator and prey histories must share the same candidate
arrival draw before marginalisation. Across sites, retain the accepted
site-marginal composite likelihood. Do not claim that between-site dependence
from the shared stochastic spread field has been modelled.

Estimate exactly one parameter: the post-arrival prey-extirpation hazard
ratio. Background risk, predator-process parameters, predator detection, prey
detection, and false-positive rates are known to the generator and likelihood.

## Factor domain and design

Generate a reproducible 32-point nested scrambled Sobol design using scramble
seed `20260831`:

| Factor | Domain | Design scale | Ecological meaning |
| --- | ---: | --- | --- |
| Predator-effect multiplier | `1.5` to `6.0` | uniform in log multiplier | post-arrival prey-extirpation hazard divided by background hazard |
| Counterfactual 60-day background risk | `0.05` to `0.20` | linear probability | prey loss by day 60 if the predator never arrived |
| Per-visit prey detection | `0.35` to `0.85` | linear probability | probability of observing prey when it persists |

Use `S01-S16` as the pilot block and `S17-S32` as the prospective block. Add
two separately labelled controls outside the continuous surface:

- `R00`: fivefold effect, reference background hazard `0.002` (about 11.3%
  60-day risk), and prey detection `0.65`; and
- `N00`: no predator effect with the same background risk and prey detection.

`R00` reconciles the accepted latent-arrival positive control. `N00` audits
false effect detection and neutral behaviour and is not subject to an
interior-support requirement because truth lies at the physical null boundary.

### Control decision contract

`R00` is valid only when its 250 validation histories satisfy the accepted
Goal 031 gates at the smaller ensemble size:

- the 95% Wilson interval for coverage contains `0.95`;
- at least `238/250` supports are connected and interior;
- at least `238/250` supports exclude a hazard ratio of `1`;
- median absolute log-effect error is at most `0.20`;
- median log-support width is at most `0.80`; and
- the paired 95% lower bound on held-out log-score advantage is above zero.

Report descriptive differences from Goal 031's accepted coverage `0.963`,
topology `0.993`, exclusion `1.000`, median error `0.128`, median width `0.757`,
and mean held-out advantage `0.0530`. Do not require numerical identity because
`R00` uses smaller, independent calibration and validation ensembles.

`N00` is valid only when:

- its 95% Wilson interval for coverage contains `0.95`;
- at least `238/250` supports are connected, with no interior requirement;
- at most `19/250` supports falsely exclude the no-effect truth; and
- the paired 95% lower bound on held-out advantage is at most zero, so the
  process model has no demonstrated predictive advantage over the true neutral.

Report null point error and width descriptively without imposing the positive-
control precision gates. Any control failure returns `control_review_required`;
do not rerun, top up, or retune it automatically.

At each condition use 250 calibration histories, the 239th one-based ordered
likelihood-ratio statistic as the fixed local cutoff, and 250 independent
validation histories. Use common random numbers across conditions within a
phase and disjoint calibration and validation roots. Reuse the accepted
hazard-ratio candidate domain from `1` to `10`, inserting each exact generating
truth into its condition-specific grid.

These ensembles estimate operating-performance surfaces. Do not top up
individual conditions merely to narrow Monte Carlo intervals.

## Staged execution

### 1. Lean design and campaign path

Build scientific components named for their roles: Arc 2B design, campaign,
and synthesis. Reuse accepted Goal 031 mechanics without retaining a runtime
dependency on its report machinery. Provide one campaign CLI and one synthesis
CLI. Run a reduced Mac mini reconciliation and timing probe before production.

### 2. Pilot block

Run `R00`, `N00`, and `S01-S16`. Inspect condition-level results and fit only
the following prespecified low-order response models. Scale the predictors to
`[-1, 1]` as:

```text
xE = 2 * (log(effect) - log(1.5)) / (log(6) - log(1.5)) - 1
xB = 2 * (background_risk - 0.05) / 0.15 - 1
xP = 2 * (prey_detection - 0.35) / 0.50 - 1
```

The additive design is `[1, xE, xB, xP]`. The interaction design adds
`[xE*xB, xE*xP, xB*xP]`. Do not add quadratics, individual interaction
searches, weights, or alternative predictor transforms.

Model median absolute log-effect error, median log-support width, and mean
held-out log-score advantage on their observed scales. Model connected-and-
interior and no-effect-exclusion frequencies using the Jeffreys empirical
logit `log((k + 0.5) / (250 - k + 0.5))`. Coverage remains a condition-level
local-calibration check rather than a learned ecological surface. Event and
exposure diagnostics remain observed explanatory overlays, not adjustment
covariates.

For each nonconstant primary outcome, retain the interaction model only when
its leave-one-truth-out RMSE is at least 10% lower than the additive model
(`RMSE_interaction <= 0.90 * RMSE_additive`). Otherwise retain the additive
form. A zero-variance response is an invariant threshold check and receives no
surface. Flexible emulators and automated search are excluded.

Freeze the selected forms, predictor transforms, coefficients, thresholds,
predictions for `S17-S32`, the pilot mean on the fitting scale, and the selected
model's leave-one-truth-out RMSE in a tracked prospective-prediction table
before the prospective block is generated.

### 3. Prospective block

Run `S17-S32` without changing the pilot models. Score the frozen predictions
against the new truth-level outcomes and compare them with the corresponding
pilot-mean predictor. Do not refit or reinterpret the pilot model until these
scores have been preserved.

For each metric calculate prospective skill on its fitting scale as:

```text
1 - sum((observed - frozen_prediction)^2)
    / sum((observed - frozen_pilot_mean)^2)
```

Positive skill is prospectively supported; zero or negative skill is surface-
limited. An outcome with a zero denominator is reported as invariant and not
credited as successful. Also report prospective RMSE and whether each observed
value lies within plus or minus the frozen leave-one-truth-out RMSE as a
diagnostic, not a gate.

Use 1,000 paired bootstrap resamples of validation-history index `1-250` for
Monte Carlo intervals. Each sampled index represents a complete 160-site
history and must be applied jointly across common-random-number-linked
conditions. Keep local calibration cutoffs and frozen predictions fixed. These
intervals quantify simulation precision conditional on the realised cutoffs;
they are not total response-surface uncertainty. Never resample sites as
independent units.

### 4. Arc 2B synthesis

After prospective scoring, combine all 32 truths for fixed-form descriptive
refits. Report which outcomes generalise, where prey-effect recovery is
reliable or conditional, and whether event yield or observation quality
explains the important transitions. Identify only the small set of conditions
or interactions that deserves later Arc 2C testing.

### 5. Bounded consolidation and publication

Perform one focused consolidation after the scientific result is fixed. Retain
one obvious `design -> campaign -> synthesis` route and delete prey-related
developmental code and tests that the accepted Arc 2B components supersede.
Historical goal records and Git preserve the development path; do not add
compatibility aliases or archives.

## Evaluation surface

For every continuous truth report:

- median absolute log-effect error;
- median log-support width;
- empirical support coverage with its Wilson interval;
- connected/interior support frequency;
- probability of excluding the no-effect value;
- held-out log-score advantage over the fitted neutral with paired uncertainty;
- observed prey-extirpation event yield, pre- and post-arrival events,
  censoring, post-arrival at-risk exposure, and observation support; and
- an explicit failure classification.

Classify a truth as `fully_recovered` only when coverage contains `0.95`, at
least `238/250` supports are connected and interior, at least `238/250` exclude
no effect, median error is at most `0.20`, median width is at most `0.80`, and
the paired lower 95% bound on held-out advantage is positive. Classify it as
`detected_but_not_fully_recovered` when the exclusion and predictive gates pass
but another recovery gate fails. Otherwise use `not_reliably_detected` and
record the failed gates.

The principal review figure should show recovery across effect strength and
background risk at representative prey-detection levels. Event information
should explain the pattern rather than replace the inferential outcomes.
Pass/fail thresholds are secondary annotations.

## Scientific decision and valid outcomes

The goal succeeds with any valid positive or negative map. It does not require
recovery at every truth. Apply these outcome classes:

- `close_arc2b_validated`: both controls are valid and every eligible
  nonconstant primary surface has positive prospective skill;
- `close_arc2b_with_surface_limits`: both controls are valid and the primary
  surfaces have a mixture of positive and nonpositive skills; retain
  unsupported outcomes as condition-level evidence;
- `review_arc2b_design_before_arc2c`: both controls are valid but no eligible
  surface beats its frozen mean, or the continuous domain is effectively
  invariant or belongs to one recovery class throughout;
- `control_review_required`: either control fails its prespecified criteria;
  and
- `implementation_blocked`: a scientific invariant or required computation
  fails.

Do not refit before prospective scoring. The final 32-point descriptive refits
must retain the pilot-selected forms.

## Success and stopping rules

Completion requires valid controls, all 32 prespecified truths, a genuinely
frozen prospective test, an intelligible scientific synthesis, compact
replayable evidence, and a lean active path.

Stop after 32 truths and two controls. Do not add enrichment points, alter the
factor ranges after seeing production results, estimate background risk or
detection, vary predator parameters, introduce alternative landscapes, add a
flexible emulator, or begin Arc 2C. Perform one focused self-review and at most
one material repair pass.

Interpret every result conditionally. Truth-specific local calibration is an
oracle operating-performance experiment, so coverage is chiefly a calibration
check rather than a field-transfer claim. Background risk also changes event
yield, absolute post-arrival hazard, exposure, censoring, and pre-arrival prey
loss; it is not a causal background-risk effect. Truth-assisted event metrics
are explanatory diagnostics only. The known central predator process does not
support conclusions about unknown or misspecified spread dynamics, other
landscapes, or between-site dependence.

## Escalation boundaries

Pause for Barry only if:

- either control materially contradicts the accepted prey model;
- the domain is effectively all-trivial or all-unrecoverable and changing it
  would alter the approved experiment;
- progress requires changing the estimand, process, observation model, or
  factor domain;
- production is projected to exceed about 24 hours wall time on `deep-server`
  or requires a materially different compute architecture; or
- competing scientific interpretations imply substantively different Arc 2C
  programmes.

Ordinary implementation, debugging, low-order model choice, proportional
testing, figure design, subagent supervision, and valid negative results are
within orchestrator authority.

## Compute, evidence, and publication authority

Development and reduced checks run on the Mac mini. Detached production on
`deep-server` with bounded workers is authorised after a timing probe. Preserve
seeds, factor transforms, truth tables, code commits, runtime, compact
condition summaries, and the tracked prospective predictions. Do not retain
or commit raw simulation histories when they are reproducible from seeds.

Approval authorises creation of the goal branch, native specialist subagents,
remote production, intermediate exact-path commits and pushes, ignored review
artifacts, the bounded consolidation, documentation of the observed result,
and fast-forward publication to canonical `main` when the scientific and
repository gates pass. Generated artifacts and build outputs remain ignored.
Goal 045 or Arc 2C is not authorised.
