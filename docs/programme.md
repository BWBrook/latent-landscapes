# Latent Landscapes Programme

## Definitive North Star

> Under what landscape, process, and observation conditions are the parameters
> of spatially explicit predator-prey dynamics identifiable and recoverable
> from imperfect data, and how well is inferential uncertainty calibrated when
> the generating system is known?

## Programme Boundary

Paper 1 is synthetic-only. Its purpose is controlled study of identifiability,
recoverability, and calibration when the generating system is known. A real
mink-vole application is a later, separate programme or paper.

## Synthetic Ladder

1. **synth-small:** historical failure discovery in legacy SpatExt.
2. **synth-medium:** modular method development.
3. **synth-realistic:** future ecologically plausible controlled stress test.

## Method Ladder

1. Deterministic predator spread with one unknown global spread rate and known
   landscape, sources, and conductance.
2. Detection-noise calibration of the deterministic one-rate benchmark,
   including a full-support predictive neutral baseline.
3. Stochastic spread-process review, followed by one-rate recovery under
   process and observation uncertainty.
4. Additional spread parameters only after the one-rate stochastic benchmark.
5. Prey-impact dynamics with direct predator observations.
6. Indirect inference from prey responses.
7. A synth-realistic stress test.
8. A small, prespecified alternative-model set for model discrimination and
   misspecification robustness.

Progression up the ladder depends on scientific review of the preceding step.
Negative or weak-identifiability results are valid outcomes.

## Goal 001

Goal 001 is the deterministic predator-spread identifiability benchmark. Its
scope is an exact one-dimensional likelihood profile for spread rate from
imperfect direct predator observations on the approved synth-medium landscape.

The observation design will use:

- fixed, access-constrained stratified clusters chosen before simulation;
- repeated surveys;
- known constant detection probability below 1;
- no false positives; and
- spatial cluster holdout.

A geometry-only nearest-source radial wave is the `neutral` machine-readable
**geometry-only hard-front comparator**. It is a deliberately rigid comparator
with deterministic occupancy and no false positives, not yet a full-support
neutral predictive baseline. The analysis distinguishes ideal process
identifiability from design-specific practical identifiability. Failure triggers
diagnosis, not retuning. The approved implementation contract is in
`docs/goals/001-deterministic-predator-spread-identifiability-benchmark/`.

## Goal 002

Goal 002 freezes the Goal 001 process truth and sampling design and varies only
the Bernoulli detection realization. It estimates the operating characteristics
of the set-valued spread-rate estimator, calibrates its likelihood-ratio support
at the generating rate, and tests predictive value against a time-stratified,
full-support neutral baseline.

This calibration rung deliberately precedes stochastic spread or additional
focal parameters. Its purpose is to separate observation-driven uncertainty
from process uncertainty before those sources are combined.

## Goal 003

Goal 003 introduces a frozen conductance-weighted stochastic first-passage
spread process while retaining `rho` as the sole future focal rate. It reviews
latent arrival morphology, stochastic variation, landscape signal, source
provenance, and temporal scale before any observation simulation or fitting.

The process preserves Goal 001 mean edge transit times, not its deterministic
whole-landscape arrival surface. Path competition can therefore accelerate the
global wave. Goal 003 reports that effect explicitly and requires human review
rather than post-hoc normalization.

## Goal 004

Goal 004 is the first recovery benchmark for the accepted stochastic generator.
It retains the frozen Goal 001 sampling sites and cluster split, replaces only
the saturated deterministic-era observation calendar with the prospectively
chosen `10, 20, 30, 40, 50, 60` schedule, and generates one complete stochastic
arrival field plus one joint detection history per dataset.

Inference uses a seven-category, Jeffreys-smoothed site-history simulated
composite likelihood over one independent 4,096-draw integration bank. The
construction preserves within-site dependence across repeated visits and
surveys, but deliberately omits between-site dependence from the shared
stochastic edge field and is not a full joint spatial likelihood. Likelihood
support is calibrated only at `rho = 1` under the frozen landscape, design,
calendar, detection model, rate grid, and integration scheme.

The complete calibration and validation calculation is repeated with two
disjoint 2,048-draw bank halves. Held-out predictions use rate and neutral
fits based on training clusters only, with the stochastic comparison taking
the worst Brier score over every tied training-MLE grid point. Bank instability,
weak support topology, failed calibration, neutral superiority, and predictive
inconclusiveness are all completed scientific outcomes rather than reasons to
retune the accepted process.

## Goal 005

Goal 005 tests whether one-rate recovery is robust across slow, central, and
fast generating rates (`rho = 0.5, 1, 2`). Local calibration is performed
separately at each truth, while the accepted `rho = 1` cutoff is transported
to flank validation sets as a distinct diagnostic. The frozen calendar is
intentionally retained: sparse or saturated flank information and cutoff
nontransportability are scientific results, not reasons to retune. The
completed class is `one_rate_recovery_robust_cutoff_nontransportable`: local
stochastic recovery passes at all three truths, but the central cutoff does
not transport. The benchmark remains conditional on one landscape and the
Goal 004 composite likelihood, which omits between-site process dependence.

## Operating Style

Work is goal-based and modular, with human review at scientific gates. Apply
Pareto discipline and add contract machinery only when it materially improves
scientific validity. Use native subagents only under machine-wide policy. No
commit or push is authorized without explicit goal authority.
