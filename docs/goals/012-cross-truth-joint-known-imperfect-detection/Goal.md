# Goal 012: Cross-Truth Joint Recovery Under Known Imperfect Detection

## Status

Approved for execution by Barry on 2026-07-30.

## Objective

Determine whether the central Goal 011 recovery of predator spread rate `rho`
and landscape-resistance contrast `eta` transports across the frozen 3 by 3
truth grid under the same known imperfect-detection model.

This goal estimates local recoverability separately at every truth. It does
not test transport of one numerical cutoff, construct an operational
unknown-truth confidence procedure, or estimate detection probability.

## Scientific Question

Conditional on one frozen landscape and sampling design, the accepted
stochastic first-passage process, two visits, known homogeneous `p = 0.65`,
and zero false positives:

1. which truth cells are locally calibrated, connected, interior, and
   practically precise;
2. are the cellwise decisions stable to the full integration bank and its two
   disjoint halves;
3. where do physical-null contact, artificial-domain contact, calibration,
   precision, or prediction first limit recovery; and
4. does the central cell reproduce Goal 011 exactly?

A mixed or negative surface is a completed scientific result.

## Frozen Inputs

Pin the accepted Goal 011 source state:

```text
2182172d207049105955c9f1acc0e1501096d920
```

Retain unchanged:

- the Goal 001 landscape, graph, three sources, access-constrained 32-cluster /
  160-site design, and 24-training / 8-holdout cluster split;
- the Goal 003 stochastic edge law and Goal 006 resistance transform;
- survey times `10, 20, 30, 40, 50, 60`;
- two visits at every site-time, known `p = 0.65`, and zero false positives;
- all 1,920 visit records per dataset, split into 1,440 training and 480
  holdout records;
- the Goal 004 onset categories, complete-history marginalization, and
  Jeffreys half-count;
- the Goal 011 601-point `rho` grid and primary eta grid
  `0, 0.25, ..., 2.5`;
- the non-gating eta projection `0, 0.25, ..., 2`;
- the 4,096-draw bank, full and two half-bank variants, 500 calibration
  datasets, 500 validation datasets, and 476th-of-500 cutoff rule;
- the training-only time-stratified neutral and held-out target
  `0.65 * Pr(occupied)`; and
- the Goal 007 numerical precision and prediction thresholds.

Do not optimize, interpolate, refine the grids, or tune any setting after
inspecting production evidence.

## Truth Grid

Evaluate exactly this row-major grid:

| Cell | `rho` | `eta` | Rho index | Eta index |
| --- | ---: | ---: | ---: | ---: |
| `cell-00` | 0.5 | 0.5 | 150 | 2 |
| `cell-01` | 1.0 | 0.5 | 300 | 2 |
| `cell-02` | 2.0 | 0.5 | 450 | 2 |
| `cell-03` | 0.5 | 1.0 | 150 | 4 |
| `cell-04` | 1.0 | 1.0 | 300 | 4 |
| `cell-05` | 2.0 | 1.0 | 450 | 4 |
| `cell-06` | 0.5 | 1.5 | 150 | 6 |
| `cell-07` | 1.0 | 1.5 | 300 | 6 |
| `cell-08` | 2.0 | 1.5 | 450 | 6 |

Every truth lies exactly on the candidate grid.

## Seed And Pairing Contract

Use `SeedSequence(20260730)` with seven ordered roots:

1. `integration_bank`;
2. `calibration_process`;
3. `validation_process`;
4. `calibration_central_detection`;
5. `validation_central_detection`;
6. `calibration_noncentral_detection`;
7. `validation_noncentral_detection`.

The first five roots and their central streams must reproduce Goal 011
exactly. Within each phase, reuse one edge-shock block across all three eta
truths and derive the three rho truths by exact arrival-time scaling.

Cell 04 uses the exact Goal 011 detection stream for each block. Each
noncentral cell uses a unique block-specific child from the appended detection
root. Thus truth cells are process-paired but observation-noise-distinct.
There are 500 independent process blocks per phase, not 4,500 independent
datasets. Cross-cell contrasts are descriptive and correlated, not paired
observation-error effects.

Calibration, validation, process, and detection streams must remain disjoint.
Worker order and scheduling must not change any stream.

## Cellwise Inference

For every truth cell:

1. generate 500 calibration and 500 validation process histories;
2. generate all 1,920 known-detection visit records for each history;
3. calculate complete-history joint profiles over all candidate `(rho, eta)`
   cells for the full bank and both halves;
4. recalibrate separate expanded and old-domain cutoffs for every bank;
5. summarize expanded and old-domain support, tied MLEs, errors, widths,
   boundary faces, and held-out predictions; and
6. retain the expanded-domain result as primary and the old-domain result as
   descriptive only.

Use truth-specific cutoffs. Do not pool or transport the central Goal 011
cutoff.

## Central Reconciliation

Cell 04 must reproduce the accepted Goal 011 central evidence:

- exact process and detection seeds;
- exact observations and discrete support fields;
- exact counts and downstream meanings;
- nine-decimal platform-stable numerical projections; and
- the accepted overall central decision.

This is an implementation-continuity check, not an independent replication.
Do not compare two calls through the same Goal 012 path and call that
reconciliation.

## Decision Logic

Record every gate boolean even though the class uses first-match precedence.

For each expanded-domain truth-cell and bank:

1. `cell_candidate_domain_unclosed` if more than 25 of 500 validation supports
   contact an artificial face: `eta_max`, `rho_min`, or `rho_max`;
2. `cell_design_limited` if fewer than 475 supports are one rook-connected
   component and strictly interior for another reason, including contact with
   the accepted `eta = 0` uniform-resistance null;
3. `cell_local_calibration_not_ready` if the pointwise Wilson interval excludes
   `0.95`;
4. `cell_recovery_imprecise` if any median exceeds absolute log-rho error
   `0.10`, absolute eta error `0.25`, projected log-rho width `0.50`, or
   projected eta width `0.75`;
5. `cell_neutral_better` if the paired-Brier interval is wholly above zero;
6. `cell_recoverable` if the paired-Brier interval is wholly below zero; and
7. `cell_mechanism_inconclusive` if the interval overlaps zero.

Overall precedence is:

1. `implementation_blocked`;
2. `likelihood_approximation_unstable` if the three bank classes disagree
   within any truth cell;
3. `cross_truth_candidate_domain_unclosed`;
4. `cross_truth_design_limited`;
5. `cross_truth_local_calibration_not_ready`;
6. `cross_truth_recovery_imprecise`;
7. `cross_truth_neutral_better`;
8. `cross_truth_mechanism_inconclusive`; and
9. `cross_truth_joint_known_detection_recoverable` only if every full-bank
   cell is recoverable and bank-stable.

The more than 25 face-contact threshold is a bounded-domain warning, not proof
of universal non-identifiability. The all-cell rule is a prespecified
worst-cell benchmark, not familywise 95% coverage.

## Comparison Guard

Goal 009 and Goal 010 provide historical perfect-detection context only.
Their eta domains differed across parts of the truth grid, so neither raw
metric differences nor Brier differences are causal estimates of the effect
of imperfect detection. Likewise, Brier superiority does not establish
parameter identifiability.

## Review Pack

Write exactly 15 ignored files under:

```text
artifacts/goal012_cross_truth_joint_known_imperfect_detection/
```

Required files:

- `config.json`
- `compute_provenance.json`
- `seed_manifest.csv`
- `observation_signal_summary.csv`
- `calibration_results.csv`
- `validation_results.csv`
- `truth_cell_summary.csv`
- `representative_profiles.csv`
- `central_reconciliation.json`
- `summary.json`
- `verification.json`
- `review.md`
- `visuals/truth_grid_recovery_calibration.svg`
- `visuals/truth_grid_prediction.svg`
- `visuals/truth_grid_domain_and_ridge.svg`

The 27-row truth-cell summary must retain both-domain cutoffs, face-specific
counts, all gate booleans, precision metrics, predictive intervals, and
classes. Raw rows must be sufficient to recompute every decision.

## Completion And Stop Rules

Complete all 27 truth-cell-by-bank analyses in one campaign. An incomplete
truth grid is not a completed scientific result.

Do not change the truth grid, candidate grid, bank, observation model,
replicate counts, cutoffs, thresholds, neutral, or decision order after seeing
production results. Do not run a rescue campaign.

Perform one focused self-review and at most one material repair. Stop when
additional work is cosmetic, duplicative, or does not change the scientific
decision.

## Authority

This goal authorizes:

- the Goal 012 packet, source, tests, CLI, docs, and ignored artifacts;
- read-only consultation of `/Users/bwbrook/work/nectar/docs/workflows/` and
  `/Users/bwbrook/work/nectar/docs/exchange/current_status.md` for remote
  compute routing;
- one implementation commit on the dedicated Goal 012 branch;
- one clean detached Git-bundle checkout on `deep-server`;
- one reduced remote smoke and one nine-worker production campaign in `tmux`;
- single-threaded numerical libraries within every worker;
- retrieval and independent audit of the generated evidence;
- one material repair if a genuine defect is found;
- one result-documentation commit; and
- exact-path staging, fast-forward merge to `main`, and push if all hard gates
  pass and the orchestrator accepts the result.

It does not authorize a second campaign, unknown or fitted detection,
heterogeneous detection, false positives, observation-design changes, a full
spatial likelihood, new truth cells, real data, prey dynamics, legacy-repo
access, unrelated cleanup, force, reset, rebase, or deletion.
