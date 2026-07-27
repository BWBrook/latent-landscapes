# Goal 007: Joint Rate-Resistance Recovery Under Perfect Detection

## Objective

Determine whether the central predator-spread parameters
`(rho, eta) = (1, 1)` are jointly recoverable before observation error is
reintroduced.

This is a deliberately favourable positive control. It combines the accepted
Goal 003 stochastic spread process with the Goal 006
landscape-resistance-contrast parameter, but observes predator presence
perfectly at the frozen access-constrained sampling sites. The goal asks
whether process stochasticity and finite spatial sampling alone still leave a
material joint ridge or other identifiability failure.

## Scientific Question

Conditional on one frozen landscape, one access-constrained sampling design,
one prospective survey calendar, and the accepted stochastic first-passage
model:

1. can `rho` and `eta` be recovered jointly at the central truth;
2. is locally calibrated two-dimensional support connected, interior, and
   practically informative;
3. is the result stable to two disjoint integration-bank halves; and
4. do training-fitted process predictions beat a full-support time-only
   neutral model on held-out clusters?

This goal establishes only a local central-truth positive control. It does not
establish cross-truth recovery, operational uncertainty calibration when truth
is unknown, or robustness to imperfect detection.

## Frozen Source And Inputs

Pin the accepted Latent Landscapes state:

- repository commit:
  `559e38b4455fc8a2d2958e6e5ef0c4d59b4e4291`;
- Goal 001 landscape blob:
  `a376df359e09b2357a0b5262479bcebaeee2ff25`;
- Goal 001 design blob:
  `ca9c60d3f113fcde48985395652974337421dfa7`;
- Goal 002 neutral-baseline blob:
  `f4aec0393fbba8b70b5ac6321898cde09256fd75`;
- Goal 003 stochastic-spread blob:
  `d20440415ea33cee0f64f41427ae81197ca8fd9e`;
- Goal 004 observation blob:
  `c97938ab640700a6584e84cc2ed8be164b582b3c`;
- Goal 004 likelihood blob:
  `b427bdfd25e2747ca69e2272e1be2df93aa6f49e`;
- Goal 004 benchmark blob:
  `92b5f91d7f47882c2da4b44f00f82448c44fa826`;
- Goal 006 contrast-spread blob:
  `da0ae999dcdcfaf3b721a4f0204acc110e6560e7`.

Retain unchanged:

- the 72 by 84 landscape, 5,225 passable cells, 823 water cells, 81
  simultaneously occupied source cells, conductance surface,
  water-neighbour penalty, 10,120-edge rook graph, and stable edge order;
- the 32 clusters and 160 sites, including the 24-training-cluster /
  8-holdout-cluster split with 120 training and 40 holdout sites;
- the Goal 003 edge law and Goal 006 resistance transform:

```text
c_e(eta) = g * (c_e / g) ** eta
tau_e(rho, eta) = c_e(eta) * E_e / rho
E_e ~ Exponential(1)
```

- the Goal 004 survey calendar `10, 20, 30, 40, 50, 60`;
- the Goal 004 seven onset categories and Jeffreys half-count;
- zero false positives; and
- the full-support training-only, time-stratified neutral comparator.

Do not modify Goals 001-006 or read a sibling or legacy repository at runtime.

## Perfect-Detection Observation Limit

Use truth `(rho, eta) = (1, 1)` and perfect direct predator detection at the
160 frozen sites.

The two nominal same-time visits are retained in the analyst-facing record
table to reconcile the frozen design. Under perfect detection they are exact
duplicates. Verify their agreement, then collapse them to one binary
site-time outcome for likelihood construction, neutral fitting, and held-out
scoring. Thus each dataset has 1,920 analyst-facing records but only 960
distinct site-time outcomes, and the site-history composite likelihood uses
one observed onset category per site.

No detection random-number stream is permitted. Perfect detection is a
limiting benchmark, not the eventual observation model.

## Seed And Replicate Contract

Use NumPy `SeedSequence(20260730)` and `PCG64`.

Spawn exactly three phase roots in this order:

1. `integration_bank`;
2. `calibration`;
3. `validation`.

### Integration bank

Spawn 4,096 indexed process children. Each child draws one complete
10,120-element exponential edge-shock vector. Reuse that vector across every
candidate `eta` value at `rho = 1`, compute all nine first-passage fields, and
retain only arrival times at the 160 survey sites.

The retained bank has shape `(4096, 9, 160)`. Do not derive non-unit eta fields
from eta-one arrivals, apply Goal 006 diagnostic alignment, or retain complete
landscape fields. Use the full bank and the two disjoint halves `0:2048` and
`2048:4096`.

### Calibration and validation

Spawn 500 indexed process children from each outer phase root. Each child
generates one complete central truth field at `(rho, eta) = (1, 1)`, from which
the full analyst-facing observations are produced before applying the frozen
training/holdout split.

Record phase, index, entropy, spawn key, sufficient state words, and stream
role. Every stream must be unique, ordered, replayable, and disjoint. Do not
extend, filter, replace, or select seeds after seeing results.

## Candidate Grid

Evaluate exactly:

```text
rho_j = 2 ** (-2 + 4 * j / 600), j = 0, ..., 600
eta_k = k / 4,                     k = 0, ..., 8
```

The 5,409-cell grid covers `rho in [0.25, 4]` and `eta in [0, 2]`.
Truth occurs exactly at `(eta index 4, rho index 300)`.

No optimizer, interpolation, adaptive refinement, or sub-grid precision claim
is permitted. Eta precision is limited by the frozen 0.25 grid spacing.

## Joint Simulated Composite Likelihood

For integration draw `m`, site `i`, and eta slice `k`, retain
`T_mik(1, eta_k)`. Exact rate scaling gives:

```text
T_mik(rho_j, eta_k) = T_mik(1, eta_k) / rho_j
```

For each eta slice, candidate rate, site, and onset category, apply the Goal
004 Jeffreys-smoothed bank weight:

```text
w_ikjc = (n_ikjc + 0.5) / (M + 7 * 0.5)
```

where `M` is 4,096 or 2,048 for the applicable bank.

Perfect observation assigns each site to exactly one of the seven onset
categories. The site-history simulated composite log likelihood is:

```text
CL(rho_j, eta_k) = sum_i log(w_ikjc(i))
```

where `c(i)` is the observed category for site `i`.

Construct a full-data profile over all 160 sites and a training profile over
the 120 training sites. Calibration statistics and validation support use
only the full-data profile. The training profile is used only to select
candidate cells for held-out prediction. The likelihood preserves repeated
history within each site by reducing it to one onset category, but it
deliberately omits between-site dependence induced by the shared edge field.
It is not a full joint spatial likelihood.

MLE sets include every grid cell equal to the maximum within absolute
tolerance `1e-12`. Never collapse tied MLE cells to an arbitrary point.

## Local Calibration And Two-Dimensional Support

For each calibration dataset and bank variant calculate:

```text
R = 2 * (CL_max - CL(rho = 1, eta = 1))
```

The local 95% cutoff is the 476th sorted value from 500 calibration
statistics, with no interpolation. Each full or half bank receives its own
cutoff.

For each validation profile, support is:

```text
2 * (CL_max - CL(rho_j, eta_k)) <= calibrated_cutoff
```

Use four-neighbour rook adjacency on the eta-by-rho grid. Report:

- truth inclusion;
- support-cell count;
- rook-connected component count;
- contact with any rho or eta grid boundary;
- projected natural-log-rho width;
- projected eta width;
- all tied MLE cells;
- minimum absolute log-rho error over the MLE set;
- minimum absolute eta error over the MLE set; and
- support-cell rho-eta correlation as a descriptive ridge diagnostic.

The projected width spans the minimum to maximum supported coordinate. When
support has only one cell or is constant on either axis, encode correlation as
JSON `null` with a deterministic reason rather than as NaN. Correlation is
descriptive, is excluded from hard numerical invariants, and must not be
interpreted as an inferential correlation estimate.

## Held-Out Neutral Comparison

Fit both candidate mechanisms using training sites only and score the 40
holdout sites using the 240 distinct site-time outcomes.

For every tied training MLE cell, calculate the Jeffreys-smoothed marginal
occupancy probability from the applicable bank weights. These probabilities
remain strictly within `(0, 1)` despite perfect realized detection.

Fit the neutral model on the 720 distinct training site-time outcomes. It may
use survey time only and must not use coordinates, habitat, sources,
conductance, latent arrivals, truth labels, eta, rho, or holdout data.

For each validation dataset, define:

```text
delta =
    worst tied-process-MLE mean Brier score
    - neutral mean Brier score
```

Lower is better. Summarize delta with a 95% normal Monte Carlo interval.
Finite log scores are secondary.

## Prespecified Decision Gates

For each bank variant, apply the first matching downstream class:

1. `joint_design_limited`: fewer than 475 of 500 validation supports are both
   one rook-connected component and strictly interior.
2. `joint_local_calibration_not_ready`: the 95% Wilson interval for validation
   truth inclusion does not contain 0.95.
3. `joint_recovery_imprecise`: any of these applicable bank variant's
   500-validation-dataset medians exceeds its deliberately coarse
   positive-control bound:
   - minimum MLE-set absolute log-rho error: `0.10`;
   - minimum MLE-set absolute eta error: `0.25`;
   - projected support log-rho width: `0.50`;
   - projected support eta width: `0.75`.
4. `joint_recoverable_neutral_better`: the paired-Brier interval lies wholly
   above zero.
5. `advance_to_joint_cross_truth_perfect_detection`: the paired-Brier interval
   lies wholly below zero.
6. `joint_recoverable_mechanism_inconclusive`: the paired-Brier interval
   overlaps zero.

The error and width bounds are practical positive-control gates, not universal
biological thresholds. Always report their empirical distributions and the
grid-limited eta resolution.

Apply overall precedence:

1. `implementation_blocked` if any source, graph, seed, replay, shape,
   perfect-observation, likelihood, numerical, artifact, or reproducibility
   invariant fails;
2. `likelihood_approximation_unstable` if the full and two half-bank
   downstream classes differ; otherwise
3. the shared downstream class.

Numerical bank differences and ridge diagnostics must be reported even when
the class is stable.

## Review Pack

Write exactly 14 ignored files under:

```text
artifacts/goal007_joint_rho_eta_perfect_detection/
```

Required files:

- `config.json`
- `seed_manifest.csv`
- `observation_signal_summary.csv`
- `calibration_results.csv`
- `validation_results.csv`
- `bank_summary.csv`
- `predictive_summary.csv`
- `representative_profile.csv`
- `summary.json`
- `verification.json`
- `review.md`
- `visuals/joint_profile_surface.svg`
- `visuals/recovery_calibration.svg`
- `visuals/bank_predictive_comparison.svg`

The pack must distinguish generated observations from scientific inference,
name the composite-likelihood limitation, label perfect detection as a positive
control, and state that all conclusions are conditional on one landscape and
one central truth.

## Completion And Stop Rules

Complete all 500 calibration and 500 validation datasets for all three banks
and write the full review pack when implementation invariants pass.

A ridge, broad support, failed calibration, neutral parity, or negative class
is a completed scientific result. Do not retune the landscape, sites, split,
calendar, grids, bank size, replicate counts, cutoff, decision bounds, or
neutral after inspecting production results.

Use the Mac mini for this moderate serial benchmark. Stop and report before
introducing parallelism or remote execution if a measured production run is
materially outside the expected local envelope. Do not begin cross-truth
recovery, imperfect detection, prey dynamics, a full spatial likelihood,
real-data work, or Goal 008.

Perform one focused self-review and at most one material repair pass. Stop when
additional work is only cosmetic or repeats evidence.

## Authority

Implementation and local validation on
`codex/latent-landscapes-goal007-joint-recovery-positive-control` are
authorized. Generated artifacts and build outputs must remain ignored and
unstaged.

After orchestrator review and one independent final review, publication of an
accepted completed result is authorized if all hard gates pass. Stage exact
accepted source, test, script, and documentation paths only. Do not force,
reset, clean, rebase, delete, or stage unrelated files.
