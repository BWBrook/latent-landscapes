# Goal 002: Detection-Noise Calibration and Full-Support Neutral Benchmark

## Objective

Measure how reliably the accepted Goal 001 one-rate deterministic spread model
recovers `rho = 1` across repeated detection histories, empirically calibrate
its likelihood-ratio support, and test its held-out predictive value against a
simple full-support neutral baseline.

This is an observation-noise calibration rung. It must not introduce focal
process stochasticity, another spread parameter, or a revised survey design.

## Scientific Question

Conditional on the frozen landscape, deterministic spread truth, and sampling
design, how variable and well calibrated is inference for the global spread
rate under repeated imperfect detections, and does habitat-aware spread retain
graded predictive value beyond a non-spatial neutral detection baseline?

## Frozen Inputs

Reuse the accepted Goal 001 implementation without copying it:

- the 72 by 84 landscape, source cells, conductance surface, and path costs;
- deterministic arrival truth `T_i(rho) = D_i / rho` with `rho = 1`;
- the 32 clusters, 160 sites, whole-cluster training/holdout split, six survey
  times, and two replicate visits;
- known `p_detect = 0.65` and zero generating false positives;
- the closed rate domain `[0.25, 4]`;
- exact breakpoint likelihood and endpoint conventions; and
- the geometry-only hard-front comparator, retained as a diagnostic only.

No site, split, time, parameter bound, or observation rule may depend on
replicate results.

## Replicate Design

Use NumPy `SeedSequence(20260726)` as the Goal 002 master seed.

1. Spawn exactly two phase roots in order: calibration then validation.
2. Spawn exactly 500 indexed child sequences from each phase root.
3. Generate one complete 1,920-record observation tuple from each child.
4. Split that tuple by the already frozen cluster labels; never simulate
   training and holdout separately.
5. Record phase, replicate index, entropy, spawn key, and sufficient child
   state for exact replay in `seed_manifest.csv`.

The 500 calibration and 500 validation realizations are fixed before analysis.
Do not extend, replace, filter, or rerun seeds in response to outcomes.

## Likelihood Calibration

For each calibration realization, fit the full-data habitat profile and compute

```text
R = 2 * (LL_max - LL(rho = 1))
```

using the likelihood at the exact generating rate, not a class midpoint.

The calibrated 95% cutoff is the 476th sorted calibration statistic (one-based
rank `ceil((500 + 1) * 0.95)`, zero-based index 475), with no interpolation.
This finite-sample rank convention is frozen before validation.

For each validation realization:

- report truth inclusion under the nominal cutoff `3.841458820694124`;
- construct exact support under the calibrated cutoff;
- record truth inclusion, component count, boundary contact, total width, MLE
  set, and distance from `rho = 1` to the MLE set; and
- summarize nominal and calibrated coverage with 95% Wilson intervals.

Calibration applies only at `rho = 1` for this fixed landscape and design. It
does not establish coverage over a truth-rate grid or other observation
conditions.

## Full-Support Neutral Baseline

Fit a separate neutral detection baseline within every validation realization
using training records only.

For each survey time `t`, let `y_t` be training detections and `n_t` be training
records. The predictive probability is

```text
q_t = (y_t + 0.5) / (n_t + 1)
```

This is the Jeffreys-smoothed posterior predictive mean for a time-specific
Bernoulli prevalence. It must use no coordinates, habitat, conductance,
sources, path costs, latent arrivals, truth labels, or holdout records. Because
`0 < q_t < 1`, every holdout binary history has finite log score.

The geometry-only hard-front comparator remains unchanged and is reported only
through its held-out Brier range and the frequencies with which any or every
training-MLE partition assigns zero probability to a held-out detection.

## Predictive Comparison

Fit the habitat model on training clusters and evaluate every partition of its
set-valued training MLE on the frozen holdout.

The primary paired statistic for validation realization `j` is

```text
delta_j =
    maximum habitat MLE-partition mean Brier score
    - neutral baseline mean Brier score
```

Lower is better, so negative values favour habitat spread. Report the mean
paired difference and its 95% normal Monte Carlo interval.

Habitat and hard-front log scores, finite-score frequencies, and structural
zero-probability counts are diagnostics. They do not determine the Goal 002
decision because a single hard zero can dominate an ensemble log-score sum.

## Decision Classes

Apply the first matching class:

1. `implementation_blocked`: any frozen-input, seed-separation, train/holdout,
   full-support, replay, numerical, artifact, or determinism invariant fails.
2. `design_limited`: fewer than 95% of validation calibrated supports are one
   connected interval strictly inside `[0.25, 4]`.
3. `calibration_not_ready`: the 95% Wilson interval for calibrated validation
   coverage does not contain `0.95`.
4. `mechanism_inconclusive`: calibration and topology pass, but the upper
   endpoint of the 95% interval for mean paired Brier difference is not below
   zero.
5. `advance_stochastic_spread`: calibration and topology pass, the full-support
   neutral scores are finite, the paired Brier interval lies wholly below zero,
   and all invariants pass.

A negative class is a completed scientific result. Do not retune the design,
baseline, seed count, cutoff convention, parameter bounds, score, or decision
thresholds after seeing results.

## Review Surface

Generate exactly ten ignored files under
`artifacts/goal002_detection_calibration/`:

- `seed_manifest.csv`
- `replicate_results.csv`
- `calibration_summary.csv`
- `predictive_summary.csv`
- `summary.json`
- `verification.json`
- `review.md`
- `visuals/coverage_support.svg`
- `visuals/mle_recovery.svg`
- `visuals/predictive_scores.svg`

Tables must contain compact per-replicate summaries, not the 1.92 million raw
observation records or retained likelihood profiles. Figures must be readable,
nonblank, unclipped, and interpretable without latent record-level output.

`review.md` must separate observation, inference, assumptions, and limitations.
It must distinguish Monte Carlo uncertainty from inferential uncertainty.

## Stop Rules

Stop and report rather than retune if:

- calibration and validation seeds overlap or cannot be replayed;
- fixed Goal 001 inputs do not reconcile exactly;
- any holdout information reaches model or baseline fitting;
- the neutral baseline loses full support;
- `rho = 1` likelihood is evaluated through a representative midpoint;
- set-valued habitat predictions are reduced to an arbitrary single MLE;
- profiles are retained across the ensemble and memory growth becomes material;
- the prespecified 1,000-realization local run is not operationally feasible;
- generated bundles are nondeterministic or inconsistent; or
- a decision class is scientifically disappointing.

Do not add stochastic spread, new focal parameters, prey, survey redesign,
truth-rate grids, MCMC, ABC, real data, remote compute, or Goal 003.

## Authority

Implementation and local validation on
`codex/latent-landscapes-goal002-detection-calibration` are authorized.
Generated artifacts and build outputs must remain ignored and unstaged.

Do not commit, merge, push, publish, or expose the repository until the
orchestrator has reviewed the complete pack and accepted the goal. Publication
is authorized after that acceptance if every validation gate passes.

