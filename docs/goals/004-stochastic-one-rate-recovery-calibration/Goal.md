# Goal 004: Stochastic One-Rate Recovery And Calibration

## Objective

Determine whether the single spread-rate multiplier `rho = 1` can be
recovered from imperfect direct predator observations when both the accepted
Goal 003 spread process and Goal 001 detection process are stochastic.

This is the first inferential benchmark for the accepted stochastic generator.
It must estimate process-marginal behavior rather than condition on the
realized latent edge field, and it must calibrate its uncertainty before
claiming recovery.

## Scientific Question

Conditional on the frozen landscape, source zones, exponential edge-time
process, access-constrained sampling design, and known detection model:

1. is a one-rate stochastic spread model practically identifiable at
   `rho = 1`;
2. is its empirically calibrated support well behaved under repeated process
   and detection realizations; and
3. does it predict held-out detections better than a full-support, time-only
   neutral baseline?

## Frozen Inputs

Pin the accepted Latent Landscapes source state:

- repository commit:
  `b7b17b611baa2b5abe9093c1f4af421f0672dfa9`;
- Goal 001 landscape blob:
  `a376df359e09b2357a0b5262479bcebaeee2ff25`;
- Goal 001 design blob:
  `ca9c60d3f113fcde48985395652974337421dfa7`;
- Goal 003 stochastic-spread blob:
  `d20440415ea33cee0f64f41427ae81197ca8fd9e`;
- Goal 002 neutral-baseline blob:
  `290cc0b608004ec75cbfa2f922d5c29f56b5271c`.

Retain without redesign:

- the 72 by 84 landscape, 5,225 passable cells, 823 water cells, source
  zones, conductance surface, water-neighbour penalties, and stable rook
  graph;
- the Goal 003 edge law
  `tau_e = c_e * Exp(1) / rho`, with no normalization;
- simultaneous occupation of all 81 source cells at `t = 0`;
- truth `rho = 1` and closed candidate domain `[0.25, 4]`;
- the 32 Goal 001 clusters and 160 sites;
- the 24-training-cluster and 8-holdout-cluster split;
- two replicate visits per site and survey;
- known `p_detect = 0.65`; and
- zero generating false positives.

The legacy SpatExt source commit remains provenance, not the Goal 004 runtime
source identity. Goal 004 must not read any sibling or legacy repository.

## Prospective Observation Window

Replace only the deterministic-era survey calendar with:

```text
10, 20, 30, 40, 50, 60
```

This choice is frozen before Goal 004 process or detection seeds are drawn.
It follows the accepted Goal 003 review: mean stochastic occupancy at the 160
frozen sites was approximately `0.153, 0.275, 0.428, 0.702, 0.848, 0.925`
at these times, whereas every frozen site was occupied in every reviewed
realization by `t = 90`.

Changing the calendar is an observation-design decision, not a rescaling of
the process. Sites, clusters, splits, visits, and detection remain unchanged.
Each generated dataset contains exactly 1,920 records.

## Seed And Replicate Contract

Use NumPy `SeedSequence(20260728)` and `PCG64`.

Spawn exactly three phase roots in this order:

1. `integration_bank`;
2. `calibration`;
3. `validation`.

### Integration bank

Spawn exactly 4,096 indexed process children. Each child generates one
complete Goal 003 edge field at `rho = 1`. Retain in memory only its arrival
times at the 160 frozen survey sites. Do not retain or write full landscape
arrival grids.

### Calibration and validation

Spawn exactly 500 indexed dataset children from each phase root. Each dataset
child spawns exactly two ordered children:

1. `process`;
2. `detection`.

The process child generates one complete stochastic truth at `rho = 1`.
The detection child generates the entire 1,920-record observation history
from that truth. Training and holdout records must never be simulated
separately.

Record phase, dataset or bank index, entropy, spawn key, sufficient state
words, and stream role. The three phases and all child streams must be unique,
ordered, replayable, and disjoint. Do not extend, replace, filter, or select
seeds after seeing results.

## Rate Grid

Evaluate exactly 601 log-spaced candidate rates:

```text
rho_j = 2 ** (-2 + 4 * j / 600),  j = 0, ..., 600
```

The grid covers `[0.25, 4]` and contains `rho = 1` exactly at index 300.
No optimizer or adaptive grid refinement is permitted.

## Site-History Simulated Composite Likelihood

The primary inferential object is a **site-history simulated composite
likelihood**. It is not a full joint spatial likelihood.

For site `i`, integration-bank draw `m`, and candidate `rho`, use the exact
Goal 003 scaling:

```text
T_im(rho) = T_im(1) / rho
```

The six surveys define seven mutually exclusive latent onset categories:

1. occupied by `t = 10`;
2. first occupied in `(10, 20]`;
3. first occupied in `(20, 30]`;
4. first occupied in `(30, 40]`;
5. first occupied in `(40, 50]`;
6. first occupied in `(50, 60]`;
7. not occupied by `t = 60`.

For every site, rate, and category, count integration-bank arrivals and apply
the frozen Jeffreys half-count. For the bank size `M` used in that analysis:

```text
w_ic(rho) = (n_ic(rho) + 0.5) / (M + 7 * 0.5)
```

Thus `M = 4096` for the primary analysis and `M = 2048` for each stability
analysis.

For each category, calculate the probability of the complete 12-record site
history under known detection `0.65` and zero false positives. Marginalize
that history over the seven category weights. Sum log site-history
probabilities across sites:

```text
CL(rho) = sum_i log(sum_c w_ic(rho) * P(Y_i | category c))
```

This construction preserves dependence among repeated visits and survey
times within a site. It deliberately omits between-site dependence induced by
the shared stochastic edge field. All documentation, tables, and figures must
name this limitation explicitly.

Construct:

- a full-data profile over all 160 sites for recovery and support;
- a training profile over the 120 training sites for held-out prediction.

MLE sets contain every grid point equal to the maximum within absolute
tolerance `1e-12`. Support contains grid points satisfying:

```text
2 * (CL_max - CL(rho)) <= calibrated_cutoff
```

Contiguous grid indices form support components. Report component count,
boundary contact, arithmetic width, log-rate width, MLE set, truth-to-MLE-set
distance, and set-valued absolute natural-log-rate error:

```text
min(abs(log(rho_hat) - log(1))) over every rho_hat in the MLE set
```

Do not reduce tied MLEs to an arbitrary single point.

## Calibration And Validation

For each calibration dataset, calculate the full-data profile and:

```text
R = 2 * (CL_max - CL(rho = 1))
```

The 95% cutoff is the 476th sorted value from the 500 calibration statistics
(one-based rank `ceil((500 + 1) * 0.95)`), with no interpolation.

For each validation dataset:

- construct the calibrated full-data support;
- record truth inclusion, component count, boundary contact, widths, MLE set,
  truth-to-MLE-set distance, and absolute log-rate error;
- fit the stochastic model using training sites only; and
- score the frozen holdout records without using holdout data in fitting.

Summarize calibrated truth coverage with a 95% Wilson interval. This
calibration applies only at `rho = 1` for this fixed landscape, design,
calendar, detection process, rate grid, and fixed integration scheme. It is
not Wilks support and does not establish calibration at other rates.

## Integration-Bank Stability

Repeat the complete calibration, validation, and classification calculations
with:

- the full 4,096-draw bank;
- bank draws `0:2048`;
- bank draws `2048:4096`.

Each bank variant receives its own calibration cutoff. Determine the
downstream scientific class for each variant before applying the bank
stability gate.

If the three downstream classes differ, the overall result is
`likelihood_approximation_unstable`. Report numerical differences among
cutoffs, coverage, MLE error, support topology, and predictive scores even
when the class is stable.

## Full-Support Neutral Comparator

Generalize Goal 002's neutral baseline without changing its default behavior.
Fit it on training records only.

For each frozen Goal 004 survey time `t`:

```text
q_t = (y_t + 0.5) / (n_t + 1)
```

The baseline may use only survey time and training detections. It must not use
coordinates, habitat, sources, conductance, latent arrivals, truth labels, or
holdout records. Every holdout prediction must lie strictly in `(0, 1)`.

For the stochastic model, obtain each holdout record's marginal detection
probability from the same seven-category weights used by the fitted
site-history composite likelihood. For site `i`, survey time `t`, candidate
`rho`, and the applicable full or half bank:

```text
P(detected_it = 1 | rho) =
    0.65 * sum_c w_ic(rho) * I(category c is occupied at time t)
```

The positive Jeffreys-smoothed category weights make these predictions
full-support and keep held-out prediction coherent with the fitted model.
Score every rate in the training MLE set. The primary paired validation
statistic is:

```text
delta_j =
    maximum stochastic-MLE mean Brier score
    - neutral mean Brier score
```

Lower is better. Report its mean and 95% normal Monte Carlo interval. Finite
recordwise log scores are secondary diagnostics.

## Hard Implementation Gates

Require:

- exact reconciliation of the pinned source state and all frozen counts;
- unchanged Goal 001-003 numerical regressions;
- exactly 4,096 bank, 500 calibration, and 500 validation process streams;
- complete and replayable stream provenance;
- no seed overlap across phases or stream roles;
- exact same-edge-field `1 / rho` scaling;
- 1,920 records generated jointly per dataset;
- no cluster leakage and no holdout fitting;
- finite composite likelihood at every grid rate;
- the truth criterion evaluated at exact grid index 300;
- full-support neutral and stochastic held-out predictions;
- full MLE sets and calibrated supports preserved;
- compact tables, JSON, and figures reconciling exactly;
- two clean output bundles with identical file sets and bytes; and
- generated outputs ignored and unstaged.

Failure of a hard implementation gate yields `implementation_blocked`.
Bank-class disagreement, support topology, and calibrated coverage are
scientific classification gates below; their failure must not be relabelled as
an implementation failure.

Support width and set-valued MLE precision are decision-relevant review
quantities but do not receive an arbitrary automated cutoff.

## Decision Classes

Apply the first matching class:

1. `implementation_blocked`: any hard frozen-input, generation, seed, replay,
   leakage, scaling, numerical-finiteness, MLE/support-construction,
   prediction, artifact, or reproducibility invariant fails. Scientifically
   valid bank disagreement, topology, and coverage results are excluded from
   this class.
2. `likelihood_approximation_unstable`: the downstream class differs among
   the full bank and either disjoint half bank.
3. `design_limited`: fewer than 475 of 500 full-bank validation supports are
   one connected component strictly inside the rate domain.
4. `calibration_not_ready`: the 95% Wilson interval for full-bank calibrated
   validation coverage does not contain `0.95`.
5. `rate_recoverable_neutral_better`: recovery and calibration gates pass,
   and the lower endpoint of the paired Brier interval is greater than zero.
6. `rate_recoverable_mechanism_inconclusive`: recovery and calibration gates
   pass, but the paired Brier interval contains zero.
7. `advance_one_rate_stochastic_spread`: recovery and calibration gates pass,
   and the upper endpoint of the paired Brier interval is below zero.

A negative class is a completed scientific result. No class establishes
general calibration beyond the frozen generating rate and design.

## Review Surface

Write exactly 12 ignored files under:

```text
artifacts/goal004_stochastic_one_rate_recovery/
```

Required files:

- `config.json`
- `seed_manifest.csv`
- `calibration_results.csv`
- `validation_results.csv`
- `bank_stability_summary.csv`
- `predictive_summary.csv`
- `representative_profile.csv`
- `summary.json`
- `verification.json`
- `review.md`
- `visuals/recovery_calibration.svg`
- `visuals/predictive_comparison.svg`

`representative_profile.csv` is the prespecified validation replicate zero,
not a visually or statistically selected realization. It contains all 601
rates for all three bank variants.

Retain compact per-replicate summaries, not the 4,096 full arrival grids or
the 1.92 million raw calibration/validation observation records.
`review.md` must separate observations, inference, assumptions, uncertainty,
and limitations.

## Stop Rules

Stop and report rather than retune if:

- the accepted stochastic generator or faster temporal scale is altered;
- the `10-60` calendar is saturated or otherwise scientifically weak;
- bank halves yield different decision classes;
- the finite bank produces unstable or nonfinite likelihoods;
- phase or process/detection seeds overlap or cannot be replayed;
- holdout information enters model or neutral fitting;
- the neutral loses full support;
- the composite likelihood is described as a full spatial likelihood;
- support calibration is described as valid away from `rho = 1`;
- runtime or memory becomes unsuitable for a moderate local run;
- the scientific result is disappointing; or
- a focused implementation repair fails to produce material improvement.

Do not normalize, retune the survey calendar, extend seeds, enlarge the bank,
change the rate grid or domain, substitute another likelihood, add process
parameters, estimate detection, add false positives, add prey, use real data,
run remote compute, or begin Goal 005.

## Authority

Implementation and local validation on
`codex/latent-landscapes-goal004-stochastic-recovery` are authorized.
Generated artifacts and build outputs must remain ignored and unstaged.

After orchestrator review and independent final review, publication of an
accepted completed result is authorized if all implementation gates pass.
Stage exact accepted source, test, script, and documentation paths only.
