# Goal 010 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans`.

**Goal:** Deliver one auditable boundary-anatomy review and one bounded
upper-`eta` sensitivity campaign without changing the accepted inferential
method.

**Architecture:** A new `goal010` package reads and reconciles the published
Goal 009 evidence, delegates the three expanded-domain truth-cell calculations
to the public Goal 008 cell runner, pairs old and new rows, applies conservative
Goal 010 decisions, and writes a compact review bundle. Goals 008-009 remain
unchanged.

**Tech Stack:** Python 3.12+, NumPy, Matplotlib, standard-library CSV/JSON,
pytest, Ruff, mypy, uv.

## Global Constraints

- Synthetic-only and perfect detection.
- Candidate `rho`, seeds, blocks, likelihood, neutral, thresholds, and class
  order are frozen.
- Candidate `eta` changes only by appending `2.25` and `2.5`.
- Numeric cutoffs are recomputed using the frozen 476th-of-500 rule.
- Exactly one three-cell production campaign; no adaptive follow-up.
- Generated review and remote evidence stay ignored.

### Task 1: Tests and Data Model

**Files:**

- Create `tests/test_goal010_benchmark.py`
- Create `src/latent_landscapes/goal010/__init__.py`
- Create `src/latent_landscapes/goal010/benchmark.py`

- [ ] Write failing tests for strict Goal 009 pack reconciliation, all-cell
  boundary anatomy, exact selected-cell identity, old-slice replay, paired row
  identity, recomputed cutoffs, class decisions, and production runtime limits.
- [ ] Run the focused tests and confirm the expected import/API failures.
- [ ] Implement the smallest typed data model and benchmark functions needed to
  pass them.
- [ ] Run the focused tests and inspect the diff for accidental Goal 008-009
  changes.

### Task 2: Artifact Contract and CLI

**Files:**

- Create `tests/test_goal010_artifacts_cli.py`
- Create `src/latent_landscapes/goal010/artifacts.py`
- Create `scripts/run_goal010.py`

- [ ] Write failing tests for the exact 14-file contract, strict JSON,
  deterministic CSV ordering, figure/table agreement, nonproduction smoke
  behavior, blocked-run behavior, and provenance validation.
- [ ] Implement deterministic writers, the two figures, concise review text,
  CLI arguments, production declaration, and nonzero blocked exit.
- [ ] Run both focused test modules.

### Task 3: Programme Documentation and Local Validation

**Files:**

- Modify `README.md`
- Modify `docs/programme.md`
- Update `docs/goals/010-boundary-aware-joint-identifiability-diagnosis/Log.md`

- [ ] Document the bounded sensitivity, the recomputed-cutoff rationale, and
  the conservative interpretation of a still-open `eta = 2.5` ridge.
- [ ] Run focused tests, full tests, Ruff format/check, mypy, build, and a tiny
  CLI smoke.
- [ ] Request one independent preproduction review.
- [ ] Make at most one focused repair if it changes scientific validity or
  execution safety.

### Task 4: One Remote Campaign

- [ ] Commit the accepted implementation and record the exact commit and lock
  hashes.
- [ ] Create and verify a Git bundle and a Goal 009 input-file manifest.
- [ ] Stage a unique run directory under `/data/codex/scratch/` on
  `deep-server`.
- [ ] Verify the detached clean checkout, lock, environment, provenance input,
  focused tests, and three-worker smoke.
- [ ] Run exactly one production command with three workers and four thread
  limits set to one.
- [ ] Retrieve source manifest, logs, compute provenance, checksums, and the
  scientific pack with checksum-preserving transfer.

### Task 5: Audit, Decision, and Publication

- [ ] Verify every returned checksum and internal payload hash.
- [ ] Independently recompute baseline anatomy, paired transitions, summaries,
  and machine-readable decisions.
- [ ] Inspect both figures once against their source tables.
- [ ] Obtain one independent final review.
- [ ] Record observation, inference, assumptions, and residual uncertainty in
  `Log.md`.
- [ ] Commit exact result-documentation paths.
- [ ] Fast-forward `main`, rerun the full suite, push, and verify local/remote
  identity if all acceptance gates pass.
