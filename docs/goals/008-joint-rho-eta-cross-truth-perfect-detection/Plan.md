# Goal 008 Implementation Plan

> **For agentic workers:** `Goal.md` is the authoritative scientific contract.
> Use test-first development and stop after one focused repair pass.

**Goal:** Test joint `(rho, eta)` recovery across the frozen 3 by 3 truth grid
under perfect detection.

**Architecture:** Reuse Goal 007's observation, likelihood, support, bank, and
prediction units. Add a thin Goal 008 campaign layer whose nine deterministic
cell tasks independently rebuild the same frozen integration bank and use the
same outer shock blocks. Aggregate cell results in stable row-major order and
write one deterministic review pack.

**Tech stack:** Python 3.14, NumPy, Matplotlib, standard library,
`concurrent.futures`, pytest, Ruff, mypy, uv, Git bundle, rsync.

## Global Constraints

- Implement every frozen value and decision in `Goal.md`.
- Do not change Goals 001-007.
- Use test-first development.
- Treat the shock block, not the derived truth cell, as the independent unit.
- Use one local cutoff per truth cell and bank.
- Preserve the pointwise-not-familywise interpretation.
- Reconcile the central cell to independent accepted constants.
- Do not add scientific tuning arguments to the production CLI.
- Keep generated and remote outputs unstaged.
- Use `deep-server-ts`, nine cell processes, and one thread per process.
- Apply at most one material repair after production.

## Task 1: Truth Grid, Paired Seeds, And Cell Engine

Create:

- `src/latent_landscapes/goal008/__init__.py`
- `src/latent_landscapes/goal008/benchmark.py`
- `tests/test_goal008_benchmark.py`

Write failing tests first for exact truth order and indices, Goal 007 seed-tree
replay, disjoint calibration and validation roots, common shock reuse,
eta-specific spread, exact rho arrival scaling, perfect observation mapping,
cell-local calibration, stable row identity, and rejection of unknown or
duplicate cells.

Implement a production configuration and a small explicit test
configuration. The cell function must be top-level and process-picklable. A
worker receives one literal truth cell and deterministic configuration;
scheduling must not enter any seed calculation.

## Task 2: Aggregation And Scientific Decision

Continue in:

- `src/latent_landscapes/goal008/benchmark.py`
- `tests/test_goal008_benchmark.py`

Write failing tests for 27 cutoffs, truth-specific cutoff lookup, central
compatibility projection, pointwise coverage, full/half-bank disagreement,
worst-cell precedence, tied MLE preservation, and every completed negative
class.

Implement sequential and multi-process campaign entry points that return
results in the same stable order. Tiny sequential and two-worker results must
be identical. No worker may write the final review pack.

## Task 3: Deterministic Review Pack And CLI

Create:

- `src/latent_landscapes/goal008/artifacts.py`
- `scripts/run_goal008.py`
- `tests/test_goal008_artifacts_cli.py`

Modify:

- `README.md`
- `docs/programme.md`
- `docs/goals/008-joint-rho-eta-cross-truth-perfect-detection/Log.md`

Write failing tests for the exact 16-file set, deterministic bytes, checksum
reconciliation, complete 3 by 3 surfaces, central evidence, portable
provenance, nonblank SVGs, and ignored destinations. The CLI accepts only an
output directory, worker count, and a compute-provenance JSON path.

The production CLI must reject scientific parameter overrides. A scientifically
negative completed result exits zero; only implementation blockage exits
nonzero.

## Task 4: Local Validation And Trusted Remote Source

Run the focused tests, quality checks, full suite, and build locally. Create
one clean feature commit containing the packet, implementation, tests, script,
and documentation. Create and verify a Git bundle and manifest for that exact
commit.

Transfer the bundle and manifest with `rsync --checksum`. On
`deep-server-ts`, verify checksums, bundle integrity, detached `HEAD`, clean
status, lockfile, environment, and focused tests before production.

## Task 5: Production, Review, And Handoff

Run one miniature nine-cell smoke campaign, then one production campaign with
nine isolated workers and thread limits set to one. Return the exact review
pack and remote logs by checksummed rsync.

Locally:

- verify transfer checksums and exact file set;
- independently recompute every cutoff, cell class, and overall class;
- inspect all four SVGs once;
- verify central reconciliation and remote provenance;
- run the final validation ladder; and
- request one independent scientific/code/artifact review.

Apply at most one focused material repair. If accepted, update the Goal log,
commit exact paths, fast-forward `main`, rerun proportionate checks, and push.
