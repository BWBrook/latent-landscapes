# Goal 013: Weak-Contrast Sampling-Design Intervention

## Status

Approved by Barry on 2026-07-31.

## Objective

Determine whether one prespecified, equal-effort, contrast-balanced allocation
of the accepted accessible sampling clusters materially improves practical
separation of weak landscape-resistance contrast `eta = 0.5` from the physical
`eta = 0` uniform-resistance null.

This goal changes cluster locations and their training/holdout assignment
only. It does not change sampling effort, the access network, process,
observation model, likelihood, candidate domain, calibration rule, recovery
thresholds, or neutral comparator.

## Scientific Question

Under the frozen landscape, stochastic first-passage process, known
homogeneous `p = 0.65`, and site-history composite likelihood:

1. does balanced sampling of low and high deterministic path-resistance
   signatures reduce physical-null contact at each `eta = 0.5` truth;
2. does any improvement restore stable practical recovery without degrading
   the accepted central `(rho, eta) = (1, 1)` positive control; and
3. is the result consistent with the already accepted perfect- and
   imperfect-detection weak-contrast evidence?

A negative or mixed intervention result is a completed scientific result.

## Existing-Evidence Reconciliation

Authenticate rather than rerun the accepted evidence:

- Goal 009 perfect detection:
  `artifacts/goal009_remote_runs/goal009-20260727T093142Z-9cb53de/scientific-pack/`;
- Goal 012 known `p = 0.65`:
  `artifacts/goal012_remote_runs/goal012-20260730T142431Z-b2bdfbb/output/`.

The expected SHA-256 values for `truth_cell_summary.csv` are:

```text
Goal 009 bc4fce39bd3e2e0ca034089d0a800623e278783c4e88d7d6b75dacdd44599096
Goal 012 40b1481af552b94573de4379d727fc1223ed08c6b6d8f1214117cfd9e01f34c9
```

Recompute the six weak-contrast rows from the raw validation tables. Record
the two observation representations, candidate eta domains, three-bank
coverage, connected-interior and `eta = 0` counts, full-bank precision and
prediction fields, artificial-face counts, classes, paths, and hashes.

The reconciliation supports recurrence of a practical weak-contrast
limitation. It is not a matched causal estimate of the effect of detection:
the observation representations and prediction targets differ.

## Frozen Intervention Selector

Retain the Goal 001:

- road/transect access network;
- 635 eligible centres and five-site footprint;
- four nearest-source Euclidean-distance strata;
- global minimum centre separation of eight cells; and
- total of 32 clusters and 160 sites.

Let `g` be the geometric mean of the accepted positive passable-edge costs.
Using no stochastic shocks, construct:

```text
D0: multi-source shortest-path time with every passable edge cost equal to g
D1: multi-source shortest-path time with the accepted edge costs
```

Exclude the six eligible centres whose footprint overlaps a zero-arrival
source cell. Retain exactly 629 all-positive candidates, with stratum counts
`196, 122, 154, 157`. For each retained centre `c`, calculate over all five
footprint cells:

```text
u_c = mean(log(D0))
z_c = mean(log(D1 / D0))
```

The six exclusions and their source overlap must be reported. The selector
must not access stochastic edge shocks, integration-bank arrivals, truth
labels, observations, detections, fitted values, or recovery outcomes.

Within each distance stratum, calculate the default NumPy linear `1/3` and
`2/3` quantiles of `z`. Define the low tail as `z <= q1/3`, the high tail as
`z >= q2/3`, and discard the middle. Require exactly four low and four high
centres in every stratum.

Use exactly this constrained search:

1. initialize `PCG64(SeedSequence(20260731))`;
2. create 32 quota slots in stratum order, low before high, with four
   consecutive copies of every `(stratum, tail)` pair;
3. perform exactly 10,000 attempts with the same continuing generator;
4. in each attempt, traverse `rng.permutation(32)` of that frozen slot list;
5. for each slot, sort currently feasible candidates by `(row, col)`, retain
   only candidates at least eight cells from every selected centre, and choose
   one using `rng.integers(len(feasible))`;
6. discard incomplete attempts and deduplicate complete designs by their
   sorted `(stratum, row, col)` coordinate tuple; and
7. rank unique complete designs lexicographically by:
   - largest minimum, across strata, of the high-minus-low mean `z` difference
     divided by the `z` IQR of all retained candidates in that stratum;
   - smallest maximum, across strata, of the absolute Pearson correlation
     between `u` and `z` among that stratum's eight selected centres;
   - largest sum of squared within-stratum-centred `z`;
   - largest minimum pairwise centre distance; then
   - lexicographically smallest sorted `(stratum, row, col)` tuple.

Compute ranking operands in `float64`, round them to 12 decimal places before
lexicographic comparison, and normalize negative zero. A zero-variance
stratum is invalid. The selected design must have maximum absolute
within-stratum `corr(u,z) <= 0.60`.

If no complete design is found or the winning design fails the correlation
gate, stop `implementation_blocked`. Do not change the seed, number of
attempts, tails, quotas, ranking, rounding, or gate.

Within each stratum-tail group of four selected clusters, calculate the mean
`z` over those four selected centres and assign to holdout the centre closest
to that mean, breaking ties by `(row, col)`. The other three are training
clusters. This yields 24 training and eight holdout clusters, with one low-
and one high-tail holdout in every stratum.

Order cluster identifiers by stratum, low before high, then `(row, col)`.
Canonicalize selector-manifest finite floats to 12 decimal places, normalize
negative zero, and hash the selected cluster and site rows before simulation.

## Frozen Campaign

Evaluate exactly four truths:

| Cell | `rho` | `eta` |
| --- | ---: | ---: |
| `cell-00` | 0.5 | 0.5 |
| `cell-01` | 1.0 | 0.5 |
| `cell-02` | 2.0 | 0.5 |
| `cell-04` | 1.0 | 1.0 |

Retain Goal 012 unchanged:

- survey times `10, 20, 30, 40, 50, 60`;
- two visits, known homogeneous `p = 0.65`, and zero false positives;
- 1,920 visit records, split into 1,440 training and 480 holdout records;
- 601-point rho grid and eta grid `0, 0.25, ..., 2.5`;
- non-gating old eta projection through `2`;
- 4,096 integration members and the same full and two half-bank membership;
- 500 calibration and 500 validation process blocks;
- local 476th-of-500 calibration cutoffs;
- complete-history likelihood, training-only time-stratified neutral;
- support topology, boundary definitions, recovery thresholds, and class
  precedence.

The intervention bank is a new site projection of the same ordered stochastic
edge-shock members. It is not a byte-identical site tensor.

Preserve the first seven Goal 012 seed roots exactly. Append calibration and
validation intervention-detection roots, each yielding one unique
block-and-truth stream for the four target cells. Intervention detection
streams are disjoint from Goal 012 and from one another. Baseline and
intervention rows are process-block matched but not record-level
detection-noise matched.

Calibrate every intervention truth and bank locally. Never transport a Goal
012 numerical cutoff.

## Minimal Predecessor Change

Goal 013 may add an optional fixed-input and seed-manifest path to Goal 012's
public truth-cell runner so the unchanged calculation can be applied to the
intervention design. The default Goal 012 path must remain exactly
reproducible under a focused regression test. Do not change Goal 012's
scientific outputs, defaults, thresholds, or accepted result.

## Decision Logic

Record every component even though the overall result uses first-match
precedence:

1. `implementation_blocked` if evidence authentication, selector, source,
   seed, bank, numerical, artifact, or invariant checks fail;
2. `likelihood_approximation_unstable` if any intervention truth has
   different classes across the full and two half banks;
3. `intervention_candidate_domain_unclosed` if more than 25 of 500
   intervention supports contact an artificial face in any truth-bank row;
4. `intervention_invalidates_central_positive_control` if cell 04 is not
   `cell_recoverable` in all three banks;
5. `contrast_balanced_design_restores_low_eta_recovery` if cells 00-02 are
   `cell_recoverable` in all three banks;
6. `contrast_balancing_contributes_not_resolves` if the central control
   remains recoverable, at least one low-eta cell remains
   `cell_design_limited`, and every low-eta full-bank physical-null comparison
   meets both material-contribution criteria:
   - at least 25 fewer `eta = 0` contacts than its authenticated Goal 012
     baseline; and
   - the 95% normal interval for the mean of the 500 block-indexed
     intervention-minus-baseline contact indicators lies wholly below zero;
7. `contrast_balancing_not_supported` otherwise.

The block index pairs the process shock, not the detection realization.
Report the differences as design-specific operating-performance contrasts;
do not imply record-level paired detection noise or universal causality.

## Review Pack

Write exactly 18 ignored files under:

```text
artifacts/goal013_weak_contrast_sampling_design_intervention/
```

Required files:

- `config.json`
- `compute_provenance.json`
- `design_candidates.csv`
- `selected_clusters.csv`
- `design_sites.csv`
- `seed_manifest.csv`
- `existing_evidence_reconciliation.csv`
- `calibration_results.csv`
- `validation_results.csv`
- `cell_bank_summary.csv`
- `baseline_intervention_comparison.csv`
- `observation_signal_summary.csv`
- `representative_profiles.csv`
- `summary.json`
- `verification.json`
- `review.md`
- `visuals/design_comparison.svg`
- `visuals/recovery_comparison.svg`

The pack must expose selector balance, overlap with the current design, habitat
composition, all decision operands, baseline evidence hashes, and the
scientific interpretation boundary.

## Completion And Stop Rules

Run one four-worker intervention campaign on `deep-server`. Reuse the accepted
baseline evidence; do not rerun the baseline arm.

Perform one focused self-review and one independent preproduction review.
After retrieval, perform one independent scientific/provenance audit and at
most one material repair. Do not run a rescue campaign.

Do not alter the selector, cluster allocation, split, truth cells, process,
observation model, grids, bank, replicate counts, cutoffs, thresholds, neutral,
or decision order after viewing production evidence.

## Authority

This goal authorizes:

- the Goal 013 packet, source, tests, CLI, docs, and ignored artifacts;
- read-only use of the accepted Goal 009 and Goal 012 artifact packs;
- a minimal regression-protected Goal 012 runner parameterization;
- read-only consultation of the `nectar` control-plane docs;
- one implementation commit on the dedicated Goal 013 branch;
- one clean detached Git-bundle checkout on `deep-server`;
- transfer of authenticated predecessor evidence needed by the run;
- one reduced remote smoke and one four-worker production campaign in `tmux`;
- retrieval and independent evidence audit;
- one material repair if a genuine defect is found;
- one result-documentation commit; and
- exact-path staging, fast-forward merge to `main`, and push if all hard gates
  pass and the orchestrator accepts the result.

It does not authorize another intervention, adaptive design search, baseline
production rerun, changed observation effort or access, estimated detection,
heterogeneous detection, false positives, a full spatial likelihood, prey
dynamics, real data, legacy-repo access, broad optimization, unrelated cleanup,
force, reset, rebase, or deletion.
