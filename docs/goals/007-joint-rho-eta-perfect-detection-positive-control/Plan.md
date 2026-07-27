# Goal 007 Implementation Plan

> **For agentic workers:** `Goal.md` is the authoritative scientific contract.
> Use test-first development and stop after one focused repair pass.

**Goal:** Test local joint recovery of spread rate and landscape-resistance
contrast at `(rho, eta) = (1, 1)` under perfect detection.

**Architecture:** Keep Goals 001-006 frozen. Add a thin Goal 007 package that
constructs eta-specific paired integration banks, evaluates exact rho scaling
on a fixed two-dimensional grid, calibrates support locally, and writes a
compact deterministic review pack.

**Tech stack:** Python 3.14, NumPy, Matplotlib, standard library, pytest, Ruff,
mypy, uv.

## Global Constraints

- Implement the exact values, formulas, and precedence in `Goal.md`.
- Do not change prior-goal behavior or source contracts.
- Use test-first development for new behavior.
- Treat perfect detection as a limiting positive control.
- Do not count duplicate same-time visits as independent information.
- Name the method `site-history simulated composite likelihood`.
- Never call it a full joint spatial likelihood.
- Keep all seed phases disjoint and replayable.
- Do not retain full-landscape banks or raw outer ensembles.
- Use the Mac mini; stop before unplanned parallel or remote execution.
- Do not stage generated artifacts or build outputs.
- Do not begin Goal 008.

## Task 1: Perfect Observations

Create:

- `src/latent_landscapes/goal007/__init__.py`
- `src/latent_landscapes/goal007/observations.py`
- `tests/test_goal007_observations.py`

Produce deterministic two-visit analyst-facing observations, verify
within-time duplicate agreement, collapse to one site-time response, and
derive exactly one onset category per site. Test counts, record order, split
integrity, exact truth mapping, absence of a detection RNG, and rejection of
inconsistent duplicate visits.

## Task 2: Joint Likelihood And Support

Create:

- `src/latent_landscapes/goal007/likelihood.py`
- `tests/test_goal007_likelihood.py`

Produce:

- the exact rho and eta grids;
- eta-specific Jeffreys-smoothed category weights;
- joint full and training profiles;
- tied two-dimensional MLE sets;
- rook-connected calibrated supports;
- projected widths and descriptive ridge correlation; and
- recordwise full-support process predictions.

Write hand-checkable fixtures before implementation. Test exact rho scaling,
truth indices, shape validation, one-hot histories, rook rather than flattened
adjacency, boundary detection, disconnected supports, tied MLEs, prediction
support, and invalid input rejection.

## Task 3: Bank, Calibration, Validation, And Decision

Create:

- `src/latent_landscapes/goal007/benchmark.py`
- `tests/test_goal007_benchmark.py`

Produce the 4,096-draw paired eta bank, two disjoint halves, independent 500
calibration and 500 validation process ensembles, local cutoffs, validation
summaries, training-only prediction, neutral comparison, bank diagnostics,
source invariants, and final decision.

Use tiny configurations for focused tests. Cover stream separation and replay,
common shocks across eta, eta-specific arrival fields, exact eta-one and rho
scaling, no split simulation, truth lookup, separate cutoffs, class
precedence, leakage prevention, worst-tied-MLE Brier scoring, and scientifically
negative completed outcomes.

## Task 4: Review Pack, CLI, And Documentation

Create:

- `src/latent_landscapes/goal007/artifacts.py`
- `scripts/run_goal007.py`
- `tests/test_goal007_artifacts_cli.py`

Modify:

- `README.md`
- `docs/programme.md`
- `docs/goals/007-joint-rho-eta-perfect-detection-positive-control/Log.md`

Write the exact 14-file deterministic bundle. Reject NaN, infinity, absolute
machine paths, stale files, and implementation-blocked bundles. The CLI may
accept an output-directory override but no scientific tuning arguments.

Tests cover exact file set, tiny-fixture byte identity, table/JSON
reconciliation, readable nonblank SVGs, ignored outputs, and representative
validation-dataset-zero selection.

## Task 5: Production, One Review, And Handoff

Run:

```bash
git diff --check
uv run pytest tests/test_goal007_observations.py \
  tests/test_goal007_likelihood.py \
  tests/test_goal007_benchmark.py \
  tests/test_goal007_artifacts_cli.py --no-cov
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
uv run python scripts/run_goal007.py
uv run python scripts/run_goal007.py \
  --output-dir artifacts/goal007_joint_rho_eta_perfect_detection_repeat
diff -rq artifacts/goal007_joint_rho_eta_perfect_detection \
  artifacts/goal007_joint_rho_eta_perfect_detection_repeat
```

Inspect all three SVGs once and independently recompute decision-driving
metrics from the generated tables. Perform one independent final
scientific/code/artifact review. Apply at most one focused repair for a
material defect, rerun affected checks, and stop for orchestrator acceptance
or authorized publication.
