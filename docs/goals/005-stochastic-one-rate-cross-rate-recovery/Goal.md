# Goal 005: Stochastic One-Rate Recovery Across Generating Rates

## Objective

Determine whether Goal 004's successful recovery of the stochastic spread-rate
multiplier is robust across slow, central, and fast generating rates, or is a
favourable local result at `rho = 1`.

This goal separates two scientific questions:

1. can `rho` be recovered with locally calibrated uncertainty at each
   prespecified generating rate; and
2. does the support cutoff calibrated at `rho = 1` transport to the two flank
   rates?

Local calibration is a controlled operating-characteristic benchmark. It is
not yet an operational uncertainty method when the true rate is unknown.
Transported-cutoff failure must not be relabelled as failed point recovery.

## Frozen Source And Model

Pin the accepted Latent Landscapes state:

- repository commit:
  `3d4909d063fc3ae39aa96502de4e10d78f98e07c`;
- Goal 001 landscape blob:
  `a376df359e09b2357a0b5262479bcebaeee2ff25`;
- Goal 001 design blob:
  `ca9c60d3f113fcde48985395652974337421dfa7`;
- Goal 002 neutral-baseline blob:
  `f4aec0393fbba8b70b5ac6321898cde09256fd75`;
- Goal 003 stochastic-spread blob:
  `d20440415ea33cee0f64f41427ae81197ca8fd9e`;
- Goal 004 observations blob:
  `c97938ab640700a6584e84cc2ed8be164b582b3c`;
- Goal 004 likelihood blob:
  `b427bdfd25e2747ca69e2272e1be2df93aa6f49e`;
- Goal 004 benchmark blob:
  `92b5f91d7f47882c2da4b44f00f82448c44fa826`.

Retain unchanged:

- the Goal 001 landscape, sources, conductance, graph, clusters, sites, and
  24-training-cluster / 8-holdout-cluster split;
- the Goal 003 process
  `tau_e = c_e * Exp(1) / rho`, with no normalization;
- the Goal 004 calendar `10, 20, 30, 40, 50, 60`;
- two visits per site and survey;
- known `p_detect = 0.65` and zero false positives;
- the Goal 004 site-history simulated composite likelihood;
- the closed rate domain `[0.25, 4]` and exact 601-point grid;
- the full-support time-only neutral comparator; and
- the full 4,096-draw bank plus its two disjoint 2,048-draw halves.

Goal 004 source and its 12-file artifact contract remain frozen. Goal 005 adds
a thin orchestration and reporting layer; it must not rewrite Goal 004.

## Generating Rates

Use exactly:

```text
rho_truth = 0.5, 1.0, 2.0
```

They occur at exact grid indices `150`, `300`, and `450`. The survey calendar
is intentionally fixed. Sparse information at `rho = 0.5` or partial
saturation at `rho = 2` is a scientific result about the frozen design, not a
reason to retune.

## Integration Bank And Seeds

Reconstruct the Goal 004 integration bank exactly from
`SeedSequence(20260728)`, phase root zero, with 4,096 process children. Use
the same bank for all candidate and generating rates through the exact scaling
`T(rho) = T(1) / rho`.

Reconstruct the `rho = 1` calibration and validation ensembles exactly from
Goal 004 phase roots one and two. Require exact numerical reconciliation with
these frozen Goal 004 values, which are independent reference constants rather
than a second call to the same Goal 004 function:

| bank | cutoff | coverage count and Wilson interval | interior topology | boundary contacts | paired Brier mean and interval | class |
| --- | ---: | --- | ---: | ---: | --- | --- |
| full | `52.43798271483206` | `468/500`, `[0.911047591162316, 0.9543039839552107]` | `500/500` | `0` | `-0.04783902279292768`, `[-0.04857410235067318, -0.047103943235182175]` | `advance_one_rate_stochastic_spread` |
| first half | `51.461724484605156` | `467/500`, `[0.9087605988391466, 0.9526214736402262]` | `500/500` | `0` | `-0.047825381384070616`, `[-0.048559386695618344, -0.04709137607252289]` | `advance_one_rate_stochastic_spread` |
| second half | `53.317375493515556` | `468/500`, `[0.911047591162316, 0.9543039839552107]` | `500/500` | `0` | `-0.04784530122207121`, `[-0.048580435689708955, -0.04711016675443346]` | `advance_one_rate_stochastic_spread` |

The frozen overall class is `advance_one_rate_stochastic_spread`. Goal 005
must compare its reconstructed central rows and summaries with these values;
it must not depend on ignored Goal 004 artifacts.

For the two flank rates, use `SeedSequence(20260729)` and spawn exactly four
phase roots in this fixed order:

1. `rho_0_5_calibration`;
2. `rho_0_5_validation`;
3. `rho_2_calibration`;
4. `rho_2_validation`.

Each phase root spawns exactly 500 indexed dataset children. Each dataset
child spawns two ordered children:

1. `process`;
2. `detection`.

Generate one complete process field and one joint 1,920-record observation
history per dataset before splitting training and holdout records. Record
master entropy, phase, generating rate, dataset or bank index, stream role,
spawn key, pool size, and sufficient state words. All 10,096 retained streams
must be ordered, unique, replayable, and disjoint. Cross-rate ensembles are
not paired.

## Local Recovery And Calibration

For every generating rate and every full/half-bank variant:

1. generate 500 calibration datasets;
2. calculate
   `R = 2 * (CL_max - CL(rho_truth))` at the exact truth index;
3. use the 476th sorted calibration statistic as that truth-and-bank-specific
   local cutoff;
4. generate 500 independent validation datasets;
5. construct local calibrated support with the local cutoff;
6. retain every tied MLE within absolute tolerance `1e-12`; and
7. report truth inclusion, support components, boundary contact, arithmetic
   width, log-rate width, truth-to-MLE-set distance, and
   `min(abs(log(rho_hat) - log(rho_truth)))`.

Log-rate width is the primary cross-rate width comparison. Arithmetic width is
descriptive. Each truth receives a separate Wilson coverage interval. Do not
pool validation replicates or predictive differences across generating rates.

The site-history likelihood remains a composite likelihood that preserves
within-site repeated-history dependence and omits between-site process
dependence.

## Cutoff Transport Diagnostic

For flank validation profiles only, also apply the reconciled Goal 004
`rho = 1` cutoff from the corresponding full or half-bank variant.

Report transported truth coverage, its Wilson interval, support topology,
boundary contact, and width separately from the locally calibrated result.
Every row must name both `truth_rate` and `cutoff_source_rate`.

The overall transport decision uses the full-bank cutoff. Half-bank transport
differences are sensitivity evidence, not local likelihood-instability
classes.

## Held-Out Prediction

At every truth and bank variant:

- fit the stochastic rate using training clusters only;
- fit the full-support time-stratified neutral using training records only;
- score the unchanged holdout clusters;
- score every tied stochastic training MLE; and
- use the worst stochastic-MLE Brier score for the paired comparison.

Report separate normal Monte Carlo intervals for the paired Brier difference
at each generating rate. Finite recordwise log score remains secondary. Do
not pool or pair results across generating rates.

## Observation-Window Diagnostics

For validation datasets, summarize by truth and survey time:

- mean and central 90% interval of true occupied-site fraction; and
- mean and central 90% interval of detection fraction.

These diagnostics explain sparse or saturated design regimes. They do not
authorize changing the calendar.

## Decision Classes

Apply the first matching class:

1. `implementation_blocked`: any frozen-source, seed, replay, scaling,
   generation, leakage, numerical, artifact, or reproducibility invariant
   fails.
2. `likelihood_approximation_unstable`: at any truth, the locally calibrated
   downstream class differs among the full and two half banks.
3. `one_rate_design_limited`: any full-bank truth has fewer than 475 of 500
   local validation supports that are one component strictly inside the rate
   domain.
4. `one_rate_local_calibration_not_ready`: any full-bank local Wilson interval
   excludes `0.95`.
5. `one_rate_recoverable_neutral_better`: recovery and local calibration pass,
   but at least one truth has a paired Brier interval wholly above zero.
6. `one_rate_recoverable_mechanism_inconclusive`: none is worse than neutral,
   but at least one truth has a paired Brier interval containing zero.
7. `one_rate_recovery_robust_cutoff_nontransportable`: all three local
   full-bank analyses favour the stochastic model, but the full-bank
   `rho = 1` transported-cutoff Wilson interval excludes `0.95` at either
   flank.
8. `advance_to_second_spread_parameter`: all three local full-bank analyses
   favour the stochastic model and the full-bank `rho = 1` cutoff transports
   to both flanks.

Scientifically negative classes are completed outcomes. An all-pass result
does not establish landscape generality or justify prey inference.

## Hard Gates

Require:

- exact Goal 004 source and `rho = 1` numerical reconciliation;
- exact generating rates and truth indices;
- one exact 4,096-draw integration bank shared through rate scaling;
- exactly 500 calibration and 500 validation datasets per truth;
- complete stream provenance with no overlap;
- one joint observation history per dataset;
- no holdout fitting or cluster leakage;
- finite likelihoods and full-support predictions;
- separate local and transported support fields;
- separate truth-rate predictive intervals;
- exact compact artifact reconciliation;
- byte-identical canonical and repeat bundles; and
- ignored, unstaged generated/build outputs.

## Review Surface

Write exactly 15 ignored files under:

```text
artifacts/goal005_stochastic_one_rate_cross_rate/
```

Required files:

- `config.json`
- `seed_manifest.csv`
- `calibration_results.csv`
- `validation_results.csv`
- `rate_summary.csv`
- `transported_cutoff_summary.csv`
- `predictive_summary.csv`
- `observation_signal_summary.csv`
- `representative_profile.csv`
- `summary.json`
- `verification.json`
- `review.md`
- `visuals/local_recovery_across_rates.svg`
- `visuals/cutoff_transportability.svg`
- `visuals/predictive_comparison.svg`

`representative_profile.csv` contains validation replicate zero for all three
truths and all three bank variants. Do not retain raw full-landscape banks or
raw outer-ensemble observation histories.

The review must distinguish observations, inference, assumptions,
uncertainty, and limitations. The figures must label local versus transported
cutoffs and state that between-site process dependence is omitted.

## Completion And Stop Rules

Complete all three prespecified truth rates and the 15-file review bundle when
implementation invariants remain valid. Report without retuning or advancing
to a second parameter if:

- a flank is sparse, saturated, boundary-limited, or poorly calibrated;
- the neutral matches or beats the stochastic model;
- local bank variants disagree;
- the `rho = 1` cutoff does not transport;
- or the scientific result is otherwise disappointing.

Stop the run early only if:

- finite-bank likelihoods are unstable or nonfinite;
- seeds overlap or cannot be replayed;
- holdout information enters fitting;
- runtime or memory ceases to be suitable for a moderate local run; or
- one focused implementation repair does not materially resolve a defect.

Do not change the calendar, truth set, grid, domain, bank, replicate counts,
detection model, landscape, or process. Do not add a second process parameter,
prey, false positives, unknown detection, alternative models, real data,
remote compute, or Goal 006.

## Authority

Implementation and local validation on
`codex/latent-landscapes-goal005-cross-rate-recovery` are authorized.
Generated artifacts and build outputs must remain ignored and unstaged.

After orchestrator review and one independent final review, publication of an
accepted completed result is authorized if all hard gates pass. Stage exact
accepted source, test, script, and documentation paths only.
