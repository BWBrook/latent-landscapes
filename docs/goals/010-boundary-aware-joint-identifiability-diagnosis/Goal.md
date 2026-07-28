# Goal 010: Boundary-Aware Joint Identifiability Diagnosis

## Status

Approved for execution by Barry on 2026-07-28.

## Objective

Determine whether Goal 009's high-`eta` support failures were materially caused
by the artificial `eta = 2` candidate-domain ceiling, while separately
cataloguing the low-`eta` inability to exclude the accepted `eta = 0`
uniform-resistance null.

This is a bounded perfect-detection sensitivity experiment. It is not a new
recovery benchmark and does not reclassify Goal 009.

## Scientific Question

For the three prespecified `eta = 1.5` truth cells, does extending only the
candidate `eta` domain from `2.0` to `2.5` close the upper support tail and
restore connected, interior, calibrated support under the unchanged Goal 009
decision rules?

## Frozen Inputs

The following remain unchanged from Goals 008-009:

- landscape, graph, sources, conductance transform, and sampling design;
- perfect direct observations and survey calendar;
- truth cells and truth-generating parameters;
- master seed, integration shock members and ordering, calibration blocks,
  validation blocks, and bank-half membership;
- candidate `rho` grid;
- site-history composite likelihood and neutral comparator;
- 476th-of-500 local calibration rule;
- topology, coverage, precision, and predictive thresholds;
- class ordering and pointwise interpretation.

The numeric likelihood-ratio cutoffs are not frozen. Expanding the candidate
domain can change the profile maximum, so each truth-cell and bank combination
must recompute its cutoff from the same 500 calibration blocks.

## Deliberate Change

Append only `eta = 2.25` and `eta = 2.5` to the accepted candidate grid.
The integration bank therefore gains two same-shock slices; its random shock
members, order, and half-bank partition remain unchanged.

The remote campaign evaluates exactly:

- `cell-06`: truth `(rho, eta) = (0.5, 1.5)`;
- `cell-07`: truth `(rho, eta) = (1.0, 1.5)`;
- `cell-08`: truth `(rho, eta) = (2.0, 1.5)`.

`cell-06` is the primary diagnostic because Goal 009 recorded the largest
stable upper-face contact count (`152/500`, with half-bank counts `150/500`
and `156/500`). Cells 07-08 are prespecified gradient and positive-comparator
cells. Conclusions remain cellwise.

## Low-Eta Interpretation

`eta = 0` is the accepted scientific parameter-space boundary: passable edges
have uniform resistance while water remains impassable. Negative `eta` would
reverse the accepted resistance ordering and define a different model.

Goal 010 will not extend below zero. Low-`eta` contact is retained as evidence
that the design cannot exclude the uniform-resistance null.

## Required Deliverables

Create:

- `src/latent_landscapes/goal010/__init__.py`
- `src/latent_landscapes/goal010/benchmark.py`
- `src/latent_landscapes/goal010/artifacts.py`
- `scripts/run_goal010.py`
- `tests/test_goal010_benchmark.py`
- `tests/test_goal010_artifacts_cli.py`

Update `README.md` and `docs/programme.md`.

Write the ignored review bundle to
`artifacts/goal010_boundary_aware_joint_identifiability/`:

1. `config.json`
2. `compute_provenance.json`
3. `baseline_boundary_anatomy.csv`
4. `expanded_calibration_results.csv`
5. `expanded_validation_results.csv`
6. `expanded_truth_cell_summary.csv`
7. `paired_boundary_transitions.csv`
8. `domain_comparison.csv`
9. `representative_profiles.csv`
10. `decision.json`
11. `verification.json`
12. `review.md`
13. `visuals/boundary_anatomy.svg`
14. `visuals/domain_comparison.svg`

## Evidence Requirements

The implementation must:

- strictly reconcile the published Goal 009 pack, including its declared file
  hashes, row counts, truth-cell order, bank order, seeds, classes, and outcome;
- summarize all nine truth cells and three banks from disk before simulation;
- pair every original and expanded validation row by block, cell, and bank;
- report boundary faces, connected components, truth inclusion, projected
  widths, estimation errors, MLEs, and predictive guards;
- report the original and recomputed cutoffs without treating their numerical
  difference as scientific drift;
- verify exact equality of the old integration-bank slices and seed/bank
  identities, and verify the new slices are finite, nonnegative, and preserve
  the accepted process construction;
- retain enough expanded calibration and validation evidence for independent
  recomputation;
- keep full- and half-bank conclusions visible;
- render two readable, non-overlapping figures that agree with the tables.

Predictive superiority is a guard against a broken process comparison, not
evidence of parameter identifiability.

## Decision Classes

The primary decision concerns `cell-06`; cells 07-08 provide prespecified
comparative evidence.

- `bounded_upper_expansion_resolves_primary_decision_limit`: all three banks
  for cell 06 have at least 475 connected-interior supports, retain truth
  coverage/calibration, pass unchanged precision and predictive gates, and
  agree on a recoverable class.
- `bounded_upper_expansion_contributes_primary_still_limited`: every cell-06
  bank has at most 25 `eta = 2.5` contacts, each count is strictly below its
  Goal 009 baseline, but another unchanged recovery gate still fails.
- `bounded_upper_expansion_domain_not_closed`: any cell-06 bank has more than
  25 supports contacting `eta = 2.5`.
- `likelihood_approximation_unstable`: full- and half-bank scientific classes
  disagree.
- `implementation_blocked`: provenance, replay, finiteness, row-pairing, or
  artifact invariants fail.

Persistence above the allowed 25-of-500 connected-interiority failure count at
`eta = 2.5` means this bounded expansion did not close the domain. It is not
proof of universal or genuine non-identifiability.
Counts of MLEs at `eta = 2.5` are retained as descriptive evidence and do not
independently gate the decision.

An `implementation_blocked` run exits nonzero and writes no scientific review
bundle. Goal 010 authorizes no separate quarantine artifact path.

## Acceptance Criteria

Goal 010 is complete when:

1. the goal packet and implementation are present on a dedicated branch;
2. focused tests, full `pytest`, Ruff format/check, strict mypy, build, and a
   tiny CLI smoke pass;
3. an independent preproduction reviewer accepts the scientific identity and
   decision implementation;
4. one provenance-gated deep-server campaign runs with exactly three workers
   and all four numerical-library thread limits set to one;
5. the returned manifest and all internal artifact hashes verify locally;
6. the orchestrator independently recomputes the paired tables and classes,
   and inspects both figures;
7. one independent final reviewer accepts or identifies a material blocker;
8. the result and limitations are recorded in `Log.md`.

## Authority

This goal authorizes:

- the repository mutations and ignored artifacts named above;
- one implementation commit before remote execution;
- one clean, detached, verified Git-bundle checkout on `deep-server`;
- one three-worker production campaign and retrieval of its evidence;
- one focused material repair pass if review finds a real defect;
- one result-documentation commit; and
- exact-path staging, fast-forward merge to `main`, and push if all gates pass.

It does not authorize imperfect detection, threshold retuning, a second domain
expansion, an adaptive cell change, Goal 009 reclassification, real data,
remote source edits, or unrelated cleanup.

## Pareto Stop

After one focused repair pass, stop when remaining issues are cosmetic,
duplicative, or do not affect the scientific decision. A completed negative or
ambiguous bounded-expansion result is valid.
