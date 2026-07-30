# Goal 012 Implementation Plan

**Goal:** Deliver one cross-truth joint `(rho, eta)` recovery benchmark under
known imperfect detection.

**Architecture:** Add a thin `goal012` composition layer over Goal 008
truth-block generation and Goal 011 complete-history inference. Earlier goals
remain unchanged.

## Task 1: Contract And Red Tests

- Freeze the seven-root stream contract, nine truth cells, local dual-domain
  calibration, cell/overall decisions, central replay, and 15-file pack.
- Add focused failing tests for seed identity and separation, truth generation,
  complete visits, local cutoffs, noncentral observation streams, central
  reconciliation, decision precedence, deterministic workers, and artifacts.
- Record the expected red state in `Log.md`.

## Task 2: Minimal Benchmark

Create:

- `src/latent_landscapes/goal012/__init__.py`
- `src/latent_landscapes/goal012/benchmark.py`
- `src/latent_landscapes/goal012/artifacts.py`
- `scripts/run_goal012.py`
- `tests/test_goal012_benchmark.py`
- `tests/test_goal012_artifacts_cli.py`

Reuse public Goal 004, Goal 007, Goal 008, and Goal 011 APIs. Do not add a new
likelihood implementation or modify earlier-goal source.

## Task 3: Local Acceptance

- Update `README.md`, `docs/programme.md`, and this log.
- Run focused and predecessor tests, Ruff format/check, mypy, full pytest, and
  build.
- Run one reduced local CLI smoke.
- Inspect the diff, tables, and three figures once.
- Obtain one independent preproduction review and make at most one material
  repair.

## Task 4: One Remote Campaign

- Commit the accepted implementation.
- Create and verify a Git bundle and lockfile hash.
- Use one unique clean detached checkout on `deep-server`.
- Run focused tests and one reduced smoke.
- Launch one nine-worker production command in named `tmux` with numerical
  thread limits set to one.
- Record worker telemetry, command, environment, times, status, and recursive
  checksums.
- Return a WSL probe and evidence-based ETA to Barry, then await wake-up.

## Task 5: Result Audit And Publication

- Retrieve and verify the complete evidence tree.
- Independently recompute all 54 cutoffs, 27 summaries, gates, and overall
  decision from raw tables.
- Reconcile cell 04 to Goal 011 and inspect three figures against their data.
- Obtain independent scientific and provenance review.
- Record observations, inference, assumptions, and limitations.
- Publish only the exact accepted source and documentation paths.
