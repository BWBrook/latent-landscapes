# Goal 003 Stochastic Spread Process Review Implementation Plan

## Global Constraints

- Implement the exact process and 100-replicate ensemble in `Goal.md`.
- Preserve Goal 001 and Goal 002 behavior.
- Use test-first development for new behavior.
- Reuse the accepted landscape, edge-cost, and Dijkstra components.
- Do not add a dependency or read the legacy SpatExt repository.
- Do not normalize, tune, fit, or simulate observations.
- Do not retain raw ensemble arrival grids in generated artifacts.
- Perform the core implementation and one focused repair pass only.
- Do not stage, commit, merge, or push before orchestrator acceptance.

## Task 1: Reusable Frozen Graph And Stochastic Spread

**Files**

- Modify: `src/latent_landscapes/goal001/spread.py`
- Modify: `tests/test_landscape_spread.py`
- Create: `src/latent_landscapes/goal003/__init__.py`
- Create: `src/latent_landscapes/goal003/spread.py`
- Create: `tests/test_goal003_spread.py`

Extract a stable helper for the accepted Goal 001 passable rook edges and
source labels without changing deterministic results. Implement exponential
edge transit sampling and stochastic multi-source arrival/source provenance.

Tests must first fail on the missing Goal 003 API, then cover exact replay,
water/source/reachability invariants, graph order/count, rate scaling, and
Goal 001 regression preservation.

## Task 2: Canonical Ensemble And Compact Summaries

**Files**

- Create: `src/latent_landscapes/goal003/benchmark.py`
- Create: `tests/test_goal003_benchmark.py`

Implement the fixed 100-child seed manifest, one-pass ensemble orchestration,
compact per-replicate summaries, per-cell quantiles, habitat summaries,
mechanical representative selection, and decision classification.

Do not retain the ensemble after the summaries and representative grids needed
for artifact construction have been derived in memory.

Tests must cover seed uniqueness/replay, exact replicate count, deterministic
representative ranks, table reconciliation, temporal-scale classification,
and scientifically negative-but-complete results.

## Task 3: Review Pack, CLI, And Programme Documentation

**Files**

- Create: `src/latent_landscapes/goal003/artifacts.py`
- Create: `scripts/run_goal003.py`
- Create: `tests/test_goal003_artifacts_cli.py`
- Modify: `README.md`
- Modify: `docs/programme.md`
- Modify: `docs/goals/003-stochastic-spread-process-review/Log.md`

Write the exact 13-file deterministic review pack, compact scientific review,
four readable SVGs, strict CLI, and documentation. Generated JSON must reject
NaN/infinity; water is excluded or explicitly encoded in CSV tables.

The CLI must exit zero for every completed scientific decision class and
non-zero for `implementation_blocked`. It must not expose ensemble size, seed,
rate, process law, or normalization as tuning options.

Tests must cover the exact artifact contract, readable labels, no absolute
machine paths, bundle byte identity, CLI behavior, and ignored-output
boundaries.

## Task 4: Validation And Review

Run:

```bash
git diff --check
uv run pytest tests/test_landscape_spread.py tests/test_goal003_spread.py \
  tests/test_goal003_benchmark.py tests/test_goal003_artifacts_cli.py --no-cov
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
uv run python scripts/run_goal003.py
```

Write a second bundle to a temporary ignored location and require identical
file sets and bytes. Inspect every SVG visually once. Record exact commands,
results, runtime, source identity, decision-driving values, artifact hashes,
and ignored/unstaged status in `Log.md`.

Stop for orchestrator review. Do not begin Goal 004.
