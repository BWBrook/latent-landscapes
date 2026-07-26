# Goal 001: Deterministic Predator-Spread Identifiability Benchmark

## Objective

Build one minimal end-to-end synthetic benchmark that estimates a single
global predator spread-rate multiplier from imperfect direct predator
observations. The benchmark must separate ideal process identifiability from
the practical identifiability created by a finite, access-constrained survey
design.

This is the first foundation stone of Latent Landscapes. It is deliberately a
single canonical realization, not a general inference framework.

## Scientific Question

When the landscape, source locations, conductance surface, detection model,
and deterministic spread mechanism are known, can one global spread-rate
parameter be recovered from imperfect observations collected through a fixed,
ecologically plausible access network?

## Required Outcome

The completed review pack must contain:

1. the approved synth-medium landscape reconstructed locally with recorded
   SpatExt provenance and no runtime dependency on SpatExt;
2. a deterministic multi-source spread truth with arrival time
   `T_i(rho) = D_i / rho`, truth `rho = 1`, and larger `rho` meaning faster
   spread;
3. a fixed road/transect accessibility network defined independently of
   habitat, source locations, conductance, spread truth, and detections;
4. a stratified clustered survey design with whole-cluster spatial holdout;
5. direct predator detections with known `p_detect = 0.65` and no false
   positives;
6. an exact one-dimensional likelihood profile over `rho in [0.25, 4]`;
7. a same-complexity geometry-only hard-front comparator (`model=neutral`);
8. explicit set-valued MLE and nominal likelihood-ratio support results;
9. held-out predictive comparison between the process and the geometry-only
   hard-front comparator, with finite Brier corroboration when a hard-zero log
   score occurs;
10. readable figures and compact audit tables for Barry's scientific review.

## Frozen Design

- Landscape: 72 rows by 84 columns; 5,225 passable cells and 823 water cells.
- Access network: columns `6, 20, 34, 48, 62, 76` and rows
  `5, 17, 29, 41, 53, 65`, using zero-based row and column indices. The
  network is fixed before and without consulting habitat, conductance, source
  locations, arrival state, `rho`, or detection draws.
- Cluster footprint: centre plus offsets `(-2,0)`, `(2,0)`, `(0,-2)`,
  `(0,2)`.
- Four nearest-source Euclidean-distance strata: `[0,21)`, `[21,42)`,
  `[42,63)`, `[63,infinity)`.
- Eight clusters per stratum, minimum centre separation 8 cells.
- Eligible centres are network cells at least two cells from every landscape
  edge whose complete five-site footprint is passable and source-reachable.
  Within each stratum, candidates are sorted by `(row, column)`, permuted by
  the dedicated centre-selection stream, and greedily accepted in near-to-far
  stratum order while enforcing Euclidean centre separation at least 8 across
  all already selected clusters. Cluster IDs follow stratum then acceptance
  order.
- Two complete clusters per stratum held out; within each stratum, sort the
  eight cluster IDs, permute them with the dedicated holdout stream, and take
  the first two. This yields 24 train and 8 holdout clusters.
- Survey times: `10, 30, 50, 70, 90, 110`.
- Two replicate visits per site and time; 1,920 records in total.
- Master seed: `20260716`; three spawned NumPy `PCG64` streams in the fixed
  order centre selection, holdout selection, detections.
- Neutral arrival: `120 * (d_i / d_max) / rho`, where Euclidean nearest-source
  distance ignores habitat and water and `d_max` is the maximum such distance
  over all passable landscape cells.
- Nominal likelihood-ratio threshold: `3.841458820694124` on
  `2 * (LL_max - LL)`.
- A site is occupied at equality: `D_i / rho <= survey_time`. Conditional on
  occupancy, replicate detections are independent Bernoulli draws with known
  probability `0.65`; predicted absence has detection probability zero.
- Exact equivalence classes must preserve endpoint closure. Construct state
  regions at every in-domain breakpoint and between adjacent breakpoints,
  then merge only contiguous regions with identical prediction signatures.
  The rate domain is closed at both `0.25` and `4.0`.

## Operational Definitions

- **Ideal process identifiability:** on the full passable landscape with exact
  continuous arrival times observed, the mapping from `rho` to the arrival
  vector is injective over `[0.25,4]`. This is checked directly, including the
  requirement that at least one path cost is positive.
- **Training data:** records from the 24 non-holdout clusters.
- **Holdout data:** records from the 8 frozen holdout clusters.
- **Full data:** training and holdout records combined, used only after the
  frozen holdout comparison.
- **Practical support:** the complete union of full-data habitat-model
  likelihood-equivalence classes satisfying the nominal likelihood-ratio
  threshold. It is descriptive, not a calibrated confidence set.
- **Rate criteria pass:** ideal process identifiability holds and practical
  support is one interior interval containing `rho = 1`.
- **Robust habitat win:** the worst held-out total Bernoulli log score over the
  habitat training-MLE set is greater than the best score over the neutral
  training-MLE set. A robust neutral win reverses this inequality; otherwise
  the comparison is inconclusive. Brier-score ranges are secondary descriptive
  evidence and do not determine the decision class.

## Decision Classes

Apply the first matching class in this precedence order:

1. `implementation_blocked`: a deterministic, provenance, structural-
   identifiability, eligibility, leakage, or numerical invariant fails.
2. `recovery_failure`: full-data nominal support excludes the generating
   value. This describes this realization only; it is not a calibrated
   rejection statement.
3. `design_limited`: nominal support is disconnected or touches the
   rate-domain boundary.
4. `mechanism_not_supported`: rate criteria pass and the geometry-only
   hard-front comparator robustly wins.
5. `advance_goal002`: rate criteria pass and habitat spread robustly wins.
6. `rate_recoverable_mechanism_inconclusive`: rate criteria pass but neither
   model robustly wins.

No arbitrary support-width cutoff is permitted. Width is reported for human
judgement and cannot by itself trigger an automated outcome class. A negative
scientific class is a successful Goal 001 result.

## Review Surface

Generate exactly nine ignored files under
`artifacts/goal001_deterministic_spread/`:

- `design.csv`
- `observations.csv`
- `likelihood_profile.csv`
- `holdout_predictions.csv`
- `summary.json`
- `review.md`
- `visuals/landscape_design.svg`
- `visuals/spread_observations.svg`
- `visuals/likelihood_holdout.svg`

The analyst-facing observations must not expose latent truth. Outputs must be
byte-identical across repeated runs.

## Stop Rules

Stop and report rather than retune if the legacy landscape/spread primitive
cannot be reconciled, the access network depends on source or ecological
state, cluster allocation depends on arrival state, `rho`, or detection draws,
clusters leak across train and holdout, latent truth appears in analyst data,
the hand-calculated likelihood fixture fails, scoring differs between models,
the approved design cannot supply its required clusters, or artifacts are
nondeterministic, blank, clipped, or internally inconsistent.

Do not proceed to repeated seeds, calibration, stochastic spread, prey,
optimization, MCMC, ABC, real data, or Goal 002.

The nominal support and outcome class apply only to this canonical
realization. They do not establish interval coverage, unbiasedness, general
recoverability, general model identifiability, ecological realism, or
applicability to mink-vole data.

The `neutral` comparator is deliberately deterministic and may assign zero
probability to observed positives under the frozen no-false-positive design.
Such a held-out `-Infinity` score is a structural support violation, not an
optimizer failure or a calibrated magnitude of model superiority. A distinct
full-support predictive neutral baseline is reserved for later work.

## Authority

Implementation and local validation on
`codex/latent-landscapes-goal001-deterministic-spread` are authorized. Reading
SpatExt at accepted commit `53462d0365babf2c8070714a930f69b4071af276`
is authorized for provenance-controlled adaptation only. Do not modify
SpatExt. Do not stage generated artifacts. Do not commit, push, merge, publish,
or expose the repository before Barry reviews and approves the Goal 001 pack.
