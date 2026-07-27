# Goal 008: Cross-Truth Joint Recovery Under Perfect Detection

## Objective

Determine whether Goal 007's local joint recovery of predator spread rate
`rho` and landscape-resistance contrast `eta` transports across a
prespecified 3 by 3 truth grid under perfect detection.

This is the final perfect-detection positive-control gate before any imperfect
observation model is introduced. It tests local recovery separately at each
truth. It does not test cutoff transport, familywise confidence coverage, or
operational uncertainty calibration when truth is unknown.

## Scientific Question

Conditional on the frozen landscape, sampling design, survey calendar,
candidate grid, integration-bank construction, composite likelihood, and
neutral comparator:

1. do all nine truth cells satisfy the Goal 007 topology, calibration,
   precision, and held-out predictive gates;
2. do the full and disjoint half banks give the same conclusion within every
   truth cell;
3. how do bias, support width, boundary contact, and the descriptive
   `rho`-`eta` ridge change across truths; and
4. does the central cell reproduce the independently accepted Goal 007
   evidence exactly?

A completed negative or mixed result is scientifically valid and must map the
failure surface rather than trigger retuning.

## Frozen Source

Pin the accepted repository state:

- repository commit:
  `8602f6ba0f55353252730c1fb68994bd37f90802`;
- Goal 007 benchmark blob:
  `f1b68e7f9ae4efef87be81a4df6beb24d9d11bec`;
- Goal 007 likelihood blob:
  `00aa5d329dc0f500ace0305c0ca1bf6a3e046847`;
- Goal 007 observation blob:
  `77bc13adf83317f3c2402e15a885e1032eeff941`;
- Goal 007 artifact blob:
  `2769d24959607a6e5b54f3c4e4fe0d58d7722a9e`;
- accepted Goal 007 log blob:
  `d3fe2e6a73ef0031c5ce3de46eb7cd8a1204d27b`;
- lockfile blob:
  `56ac1fe55b4c1182e4f89448a95d1864745261dc`.

Retain unchanged all Goal 007 inputs and methods:

- 72 by 84 landscape, graph, sources, conductance, and resistance transform;
- 32 clusters and 160 access-constrained sites with the accepted split;
- survey times `10, 20, 30, 40, 50, 60`;
- perfect direct predator detection, zero false positives, and no detection
  random stream;
- duplicate same-time analyst visits collapsed before inference;
- the 601-point `rho` grid on `[0.25, 4]`;
- the nine-point `eta` grid on `[0, 2]` at 0.25 spacing;
- the 4,096-draw integration bank and its two disjoint 2,048-draw halves;
- the seven-category Jeffreys-smoothed site-history simulated composite
  likelihood;
- four-neighbour rook support;
- training-only process fitting and the full-support time-only neutral on
  held-out clusters; and
- all Goal 007 decision thresholds.

Do not modify Goals 001-007.

## Truth Grid

Evaluate exactly this row-major order:

| Cell | `rho` | `eta` | Rho index | Eta index |
|---|---:|---:|---:|---:|
| `cell-00` | 0.5 | 0.5 | 150 | 2 |
| `cell-01` | 1.0 | 0.5 | 300 | 2 |
| `cell-02` | 2.0 | 0.5 | 450 | 2 |
| `cell-03` | 0.5 | 1.0 | 150 | 4 |
| `cell-04` | 1.0 | 1.0 | 300 | 4 |
| `cell-05` | 2.0 | 1.0 | 450 | 4 |
| `cell-06` | 0.5 | 1.5 | 150 | 6 |
| `cell-07` | 1.0 | 1.5 | 300 | 6 |
| `cell-08` | 2.0 | 1.5 | 450 | 6 |

Every truth is an exact candidate-grid cell. Do not add, remove, reorder, or
adapt truth cells after inspecting results.

## Paired Seed And Process Contract

Reuse the exact Goal 007 `SeedSequence(20260730)` tree:

1. `integration_bank`;
2. `calibration`;
3. `validation`.

The integration bank is exactly the Goal 007 bank and remains independent of
the outer ensembles.

Each of the 500 calibration and 500 validation child streams draws one
complete 10,120-edge exponential shock vector. Reuse that shock vector across
truth `eta = 0.5, 1.0, 1.5` at `rho = 1`, then derive truth
`rho = 0.5, 1.0, 2.0` by exact arrival-time scaling.

The independent outer unit is therefore one shock block. Each phase has 500
independent blocks, not 4,500 independent datasets. The nine derived
truth-cell datasets within a block are paired correlated counterfactuals.
Calibration and validation roots remain disjoint. Scheduling and worker
assignment must not affect seeds.

Every result row must record phase, block index, pairing group, truth cell,
truth coordinates and indices, bank, and cutoff-source coordinates.

## Cellwise Calibration And Support

For each of nine truth cells and each of three bank variants, compute the
Goal 007 likelihood-ratio statistic over 500 calibration blocks. Use the 476th
sorted value without interpolation. There are exactly 27 local cutoffs.

Apply only the cutoff matching the truth cell and bank. Do not pool truth
cells, transport the central cutoff, interpolate cutoffs, or adjust them after
seeing validation results.

For every validation block and bank, retain the Goal 007 support and
prediction fields, including:

- truth inclusion;
- connected components and contacted boundary face;
- projected log-rho and eta widths;
- tied MLE cells and minimum truth errors;
- descriptive support-cell `rho`-`eta` correlation;
- training MLE cells;
- process and neutral held-out scores; and
- paired Brier difference.

Strict interiority is defined against every edge of the frozen candidate
domain. Boundary contact at a flank truth is evidence of limited recovery, not
a reason to expand the grid.

## Central Compatibility Projection

`cell-04`, truth `(1, 1)`, must reproduce the accepted Goal 007 result.
Compare generated central calibration LR rows, validation decision fields,
cutoffs, bank summaries, predictive summaries, and outcome against frozen
constants or hashes transcribed from the accepted Goal 007 evidence.

Do not establish compatibility by calling Goal 007 through the same Goal 008
result path and comparing two executions of shared code. The comparison is an
implementation-continuity check, not an independent validation of the
underlying method.

## Pointwise Intervals And Multiplicity

Use the Goal 007 95% Wilson interval for truth inclusion and 95% normal Monte
Carlo interval for paired Brier differences separately within each truth cell
and bank. Do not pool the nine cells and do not apply a multiplicity
adjustment to local cutoffs.

The overall all-cell rule is a prespecified worst-cell benchmark. It is not a
simultaneous or familywise 95% coverage statement. Cross-cell comparisons are
paired and correlated.

## Decision Logic

For each truth cell and bank, apply the first matching class:

1. `cell_joint_design_limited` if fewer than 475 of 500 supports are one
   rook-connected component and strictly interior.
2. `cell_joint_local_calibration_not_ready` if the pointwise Wilson interval
   excludes 0.95.
3. `cell_joint_recovery_imprecise` if any validation median exceeds:
   - minimum MLE-set absolute log-rho error: `0.10`;
   - minimum MLE-set absolute eta error: `0.25`;
   - projected support log-rho width: `0.50`;
   - projected support eta width: `0.75`.
4. `cell_joint_neutral_better` if the paired-Brier interval is wholly above
   zero.
5. `cell_joint_recoverable` if the paired-Brier interval is wholly below zero.
6. `cell_joint_mechanism_inconclusive` if it overlaps zero.

Apply overall precedence:

1. `implementation_blocked` if any source, seed, pairing, replay, shape,
   observation, numerical, central-reconciliation, remote-provenance,
   artifact, or reproducibility invariant fails.
2. `likelihood_approximation_unstable` if the three bank classes disagree
   within any truth cell.
3. `joint_cross_truth_design_limited` if any full-bank cell has the
   corresponding design class.
4. `joint_cross_truth_local_calibration_not_ready` if any full-bank cell has
   the corresponding calibration class.
5. `joint_cross_truth_recovery_imprecise` if any full-bank cell has the
   corresponding precision class.
6. `joint_cross_truth_neutral_better` if any full-bank cell has the
   corresponding neutral-better class.
7. `joint_cross_truth_mechanism_inconclusive` if any full-bank cell is
   inconclusive.
8. `advance_to_joint_imperfect_detection` only if all nine full-bank cells
   are recoverable and every truth cell is stable across banks.

Always report the complete 3 by 3 class and metric surfaces.

## Compute And Provenance

Use the Mac mini for test-first development and miniature smoke checks.

Use `deep-server-ts` for production with nine isolated single-threaded cell
processes. Set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
`MKL_NUM_THREADS`, and `NUMEXPR_NUM_THREADS` to `1`. Kunanyi is not justified
for this campaign.

Because GitHub SSH is unavailable on `deep-server-ts`, transfer a trusted Git
bundle for one clean pre-production feature commit. Record and verify:

- source commit;
- bundle SHA-256;
- `uv.lock` SHA-256;
- remote `HEAD` and clean status;
- Python, uv, NumPy, host, and operating-system versions;
- exact command and thread limits;
- per-cell exit status, wall time, and maximum RSS; and
- recursive artifact checksums.

Use paths beneath:

```text
/data/codex/tmp/latent-landscapes/<run-id>/
/data/codex/scratch/latent-landscapes/goal008/<run-id>/
/data/codex/artifacts/latent-landscapes/goal008/<run-id>/
```

Do not delete remote evidence during this goal. If the remote source,
environment, smoke gate, or any cell fails, retain logs and make at most one
same-seed material repair. Do not retune.

## Review Pack

Write exactly 16 ignored files under:

```text
artifacts/goal008_joint_rho_eta_cross_truth_perfect_detection/
```

Required files:

- `config.json`
- `compute_provenance.json`
- `seed_manifest.csv`
- `truth_cell_summary.csv`
- `calibration_results.csv`
- `validation_results.csv`
- `predictive_summary.csv`
- `representative_profiles.csv`
- `central_reconciliation.json`
- `summary.json`
- `verification.json`
- `review.md`
- `visuals/truth_grid_recovery.svg`
- `visuals/truth_grid_calibration.svg`
- `visuals/truth_grid_ridge.svg`
- `visuals/truth_grid_predictive.svg`

The pack must distinguish observed benchmark results from interpretation,
identify the 500 independent blocks and paired truth cells, state the
pointwise-not-familywise limitation, name the composite-likelihood
approximation, and preserve negative or mixed truth-cell results.

## Completion And Stop Rules

Complete all 27 truth-cell-by-bank calibration and validation analyses before
making a scientific cross-truth conclusion. An incomplete cell campaign is
not a completed partial result.

Do not retune the truth grid, candidate grids, calendar, bank, replicate
counts, local cutoff rule, precision bounds, support topology, neutral, or
decision order after inspecting production.

Perform one focused self-review and at most one material repair. Do not repeat
the production campaign merely for cosmetic or already-tested deterministic
packaging changes. Stop after a material repair fails, a hard provenance
invariant cannot be restored, or further work offers no decision-relevant
gain.

Do not begin imperfect detection, prey dynamics, a full joint spatial
likelihood, model selection, landscape changes, or Goal 009.

## Authority

Implementation, local validation, one exact pre-production feature commit,
the bounded `deep-server-ts` run, and checksummed artifact return are
authorized on
`codex/latent-landscapes-goal008-cross-truth-joint-recovery`.

Generated artifacts, remote logs, and build outputs remain unstaged.

After orchestrator review and one independent final review, publication of an
accepted completed result is authorized. Stage exact accepted source, test,
script, and documentation paths only. Do not force, reset, clean, rebase,
delete, expose services, or stage unrelated files.
