# Goal 011: Central Joint Recovery Under Known Imperfect Detection

## Status

Approved for execution by Barry on 2026-07-30.

## Objective

Determine whether the central predator-spread parameters
`(rho, eta) = (1, 1)` remain jointly recoverable when the accepted stochastic
process is observed with the known imperfect-detection design already used in
Goal 004.

This is the first joint imperfect-detection benchmark. It changes the
observation layer only: two conditionally independent visits at each frozen
site and survey time, known constant detection probability `p = 0.65`, and
zero false positives. It does not estimate detection probability.

## Scientific Question

Conditional on one frozen landscape, one access-constrained sampling design,
one central truth, the accepted stochastic first-passage process, and known
homogeneous detection:

1. are `rho` and `eta` locally recoverable from the complete two-visit
   detection histories;
2. is calibrated two-dimensional support connected, interior, and practically
   informative;
3. is the conclusion stable to two disjoint integration-bank halves; and
4. do training-fitted process predictions beat a full-support, training-only,
   time-stratified neutral comparator on held-out clusters?

The result is a central-truth benchmark, not a claim of cross-truth robustness
or a field-ready observation model.

## Frozen Inputs

Retain unchanged:

- the accepted Goal 001 landscape, graph, sources, access-constrained
  32-cluster / 160-site design, and 24-training / 8-holdout cluster split;
- the Goal 003 stochastic edge law and the Goal 006 geometric-mean-preserving
  resistance transform;
- truth `(rho, eta) = (1, 1)`;
- the Goal 004 survey calendar `10, 20, 30, 40, 50, 60`, two visits per
  site-time, known `p = 0.65`, and zero false positives;
- the Goal 004 seven onset categories and Jeffreys half-count;
- the Goal 007 601-point candidate rho grid, 4,096-draw bank, full/two-half
  bank variants, 500 calibration datasets, 500 validation datasets,
  476th-of-500 cutoff rule, cluster holdout, neutral comparator, decision
  thresholds, and first-match gate ordering; and
- NumPy `SeedSequence(20260730)` with `PCG64`.

The candidate eta grid is the accepted closed Goal 010 grid:

```text
eta = 0, 0.25, ..., 2.0, 2.25, 2.5
```

No optimizer, interpolation, adaptive refinement, or sub-grid precision claim
is permitted.

## Seed Contract

Spawn exactly five phase roots in this order:

1. `integration_bank`;
2. `calibration_process`;
3. `validation_process`;
4. `calibration_detection`;
5. `validation_detection`.

The first three roots preserve the exact Goal 007 process streams because they
retain the same entropy, root order, and indexed children. The two appended
detection roots are independent of each other and of every process stream.

Each calibration and validation process child is paired by dataset index with
one detection child. Generate the complete 1,920-record observation table
before applying the frozen cluster split. Retain all 12 outcomes per site:
1,440 training records and 480 holdout records.

The implementation must verify exact Goal 007 process-seed identity, exact
old-domain integration-slice replay, unique process and detection streams,
and finite added eta slices. It must not derive detection seeds from process
children or collapse same-time visits.

## Joint Imperfect-Detection Composite Likelihood

For each site `i` and onset category `c`, compute the probability of its
complete 12-record detection history under known `p = 0.65`:

```text
h_ic = P(Y_i | onset category c, p = 0.65)
```

For each candidate `(rho_j, eta_k)`, combine those history probabilities with
the applicable full- or half-bank category weights:

```text
CL(rho_j, eta_k) =
    sum_i log(sum_c w_ikjc(rho_j, eta_k) * h_ic)
```

This is the direct joint-parameter analogue of Goal 004. It preserves
within-site dependence across repeated observations but omits between-site
dependence induced by the shared stochastic edge field. It is not a full
joint spatial likelihood.

Build full-data profiles from all 160 sites and training profiles from the 120
training sites. Full-data profiles determine calibration statistics and
validation support. Training profiles select every tied MLE cell for held-out
prediction. Preserve all global ties within absolute tolerance `1e-12`.

## Calibration, Support, And Prediction

Recalibrate a separate numeric likelihood-ratio cutoff for each full and
half-bank variant from the 500 Goal 011 calibration histories. Goal 007's
numeric cutoffs are historical evidence and must not be reused.

Use four-neighbour rook connectivity and report truth inclusion, support-cell
count, connected components, separate boundary-face contacts, projected
log-rho and eta widths, all tied MLE cells, minimum MLE-set errors, and the
descriptive rho-eta support correlation.

For each tied training MLE cell, predict each held-out visit as:

```text
P(detection) = 0.65 * P(occupied at the survey time)
```

Fit the time-only Jeffreys-smoothed neutral to the 1,440 training records and
score the same 480 held-out records. The process comparator uses the worst
mean Brier score over tied training MLE cells. A 95% normal Monte Carlo
interval summarizes the paired Brier difference over validation datasets.

## Eta-Domain Attribution Guard

The primary decision uses the closed eta grid through `2.5`.

From the same calculated profiles, also slice the eta grid at `eta <= 2`,
recalibrate a separate old-domain cutoff, and summarize the old-domain result.
This projection is descriptive and non-gating. Report:

- both numeric cutoffs and downstream classes;
- validation MLE and support contact with `eta > 2`;
- whether the expanded-domain MLE or support materially uses the appended
  cells; and
- the accepted Goal 007 perfect-detection summary as historical context.

Because Goal 007 used `eta <= 2`, neither the old-domain nor expanded-domain
comparison alone is a strict causal estimate of the effect of imperfect
detection.

## Decision Gates

Apply the frozen Goal 007 numerical gates to each expanded-domain bank, using
Goal 011-specific labels:

1. `joint_imperfect_detection_design_limited`: fewer than 475 of 500 supports
   are one rook-connected component and strictly interior.
2. `joint_imperfect_detection_local_calibration_not_ready`: the validation
   truth-inclusion Wilson interval does not contain `0.95`.
3. `joint_imperfect_detection_recovery_imprecise`: any median exceeds:
   absolute log-rho MLE-set error `0.10`, absolute eta error `0.25`,
   projected log-rho width `0.50`, or projected eta width `0.75`.
4. `joint_imperfect_detection_neutral_better`: the paired-Brier interval lies
   wholly above zero.
5. `advance_to_cross_truth_joint_imperfect_detection`: the paired-Brier
   interval lies wholly below zero.
6. `joint_imperfect_detection_mechanism_inconclusive`: the paired-Brier
   interval overlaps zero.

Overall precedence is:

1. `implementation_blocked` if a source, seed, replay, history, likelihood,
   numerical, artifact, or reproducibility invariant fails;
2. `likelihood_approximation_unstable` if full- and half-bank expanded-domain
   classes disagree; otherwise
3. the shared expanded-domain class.

## Review Pack

Write exactly 15 ignored files under:

```text
artifacts/goal011_joint_known_imperfect_detection/
```

Required files:

- `config.json`
- `seed_manifest.csv`
- `observation_signal_summary.csv`
- `calibration_results.csv`
- `validation_results.csv`
- `bank_summary.csv`
- `predictive_summary.csv`
- `domain_comparison.csv`
- `representative_profile.csv`
- `summary.json`
- `verification.json`
- `review.md`
- `visuals/joint_profile_surface.svg`
- `visuals/recovery_calibration.svg`
- `visuals/domain_and_bank_comparison.svg`

The pack must distinguish observation from inference, state the known-detection
assumption, name the composite-likelihood limitation, and label all
perfect-detection comparisons as historical rather than strictly matched.

## Acceptance And Stop Rules

Complete one campaign of 500 calibration and 500 validation datasets for all
three bank variants. A ridge, broad support, failed calibration, neutral
parity, bank disagreement, or other negative class is a completed scientific
result.

Do not change `p`, visits, calendar, sites, split, truth, grids, bank size,
replicate counts, cutoff rank, thresholds, or neutral after inspecting the
production result. Do not run a rescue campaign. Do not start cross-truth
recovery.

Use one focused self-review and at most one material repair pass. Stop when
additional work is cosmetic, duplicative, or does not change the scientific
decision.

## Authority

This goal authorizes:

- the named source, tests, scripts, documentation, and ignored artifacts;
- one implementation commit on the dedicated Goal 011 branch;
- one clean detached Git-bundle checkout on `deep-server`;
- one reduced remote smoke and one single-process 500/500 production campaign
  in `tmux`, with all numerical-library thread limits set to one;
- retrieval and audit of the generated evidence;
- one focused material repair if a genuine defect is found;
- one result-documentation commit; and
- exact-path staging, fast-forward merge to `main`, and push if all hard gates
  pass and the orchestrator accepts the completed result.

It does not authorize remote source edits, a second production campaign,
unknown or heterogeneous detection, false positives, missing visits, fitting
`p`, Goal 007 reclassification, a full spatial likelihood, real data, prey
dynamics, unrelated cleanup, force, reset, rebase, or delete operations.
