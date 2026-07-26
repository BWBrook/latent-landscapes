# Goal 006 Implementation Plan

> **For agentic workers:** `Goal.md` is the authoritative scientific contract.
> Use test-first development and stop after one focused repair pass.

**Goal:** Determine whether landscape-resistance contrast produces a spatial
spread signature distinct from global rate scaling.

**Architecture:** Keep Goals 001-005 frozen. Add a thin Goal 006 process layer
that transforms accepted edge costs, reuses one Goal 003 edge-shock vector
across the eta grid, computes paired spatial diagnostics, and writes a compact
deterministic review pack.

**Tech stack:** Python 3.14, NumPy, Matplotlib, pytest, Ruff, mypy, uv.

## Task 1: Resistance-Contrast Process

Create:

- `src/latent_landscapes/goal006/__init__.py`
- `src/latent_landscapes/goal006/spread.py`
- `tests/test_goal006_spread.py`

Implement the geometric-mean-preserving edge transform, explicit exact
`eta = 1` branch, paired edge-shock sampling, and multi-source spread. Test the
frozen eta grid, edge ordering, exact eta-one equality, common-shock reuse,
rho scaling, source/water/reachability invariants, and invalid inputs.

## Task 2: Paired Benchmark

Create:

- `src/latent_landscapes/goal006/benchmark.py`
- `tests/test_goal006_benchmark.py`

Implement the exact Goal 003 seed replay, compact retained state, raw and
aligned spatial summaries, deterministic matched fronts, habitat/source
contrasts, representative selection, frozen Goal 003 reconciliation, and
decision precedence. Use tiny configurations for development. Do not treat
cells as independent replicates.

## Task 3: Review Pack And CLI

Create:

- `src/latent_landscapes/goal006/artifacts.py`
- `scripts/run_goal006.py`
- `tests/test_goal006_artifacts_cli.py`

Write the exact 15-file deterministic pack. Reject NaN, infinity, absolute
paths, stale files, and implementation-blocked bundles. Ensure visual labels
identify raw versus aligned quantities and the conditional single-landscape
scope.

## Task 4: Documentation

Modify:

- `README.md`
- `docs/programme.md`
- `docs/goals/006-stochastic-landscape-resistance-contrast-review/Log.md`

Record the completed outcome, validation evidence, runtime, canonical hashes,
ignored state, assumptions, and the distinction between process suitability
and joint identifiability.

## Task 5: Production And Review

Run:

```bash
git diff --check
uv run pytest tests/test_goal006_spread.py \
  tests/test_goal006_benchmark.py \
  tests/test_goal006_artifacts_cli.py --no-cov
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
uv run python scripts/run_goal006.py
uv run python scripts/run_goal006.py \
  --output-dir artifacts/goal006_stochastic_resistance_contrast_repeat
diff -rq artifacts/goal006_stochastic_resistance_contrast \
  artifacts/goal006_stochastic_resistance_contrast_repeat
```

Inspect all five SVGs once. Independently recompute the primary decision
metrics from raw tables. Perform one independent final review and at most one
focused repair for a material defect.
