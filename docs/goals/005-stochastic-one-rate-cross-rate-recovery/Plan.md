# Goal 005 Cross-Rate One-Rate Recovery Implementation Plan

> **For agentic workers:** use test-first development and execute this plan
> task by task. `Goal.md` is the authoritative scientific contract.

**Goal:** Extend the accepted Goal 004 one-rate benchmark to the frozen truth
rates `0.5`, `1`, and `2`, while separating local calibration from cutoff
transportability.

**Architecture:** Keep Goal 004 frozen. Add a thin Goal 005 package that
reconstructs the exact Goal 004 bank and central ensembles, processes flank
truths sequentially with new disjoint seeds, and reuses Goal 004 likelihood,
observation, calibration, classification, and prediction primitives.

**Tech Stack:** Python 3.14, NumPy, standard library, Matplotlib, pytest, Ruff,
mypy, uv.

## Global Constraints

- Implement the exact values and classes in `Goal.md`.
- Preserve all Goal 001-004 defaults and regressions.
- Write failing tests before production behavior.
- Do not make Goal 005 depend on ignored Goal 004 artifacts.
- Do not mutate Goal 004 source or its artifact writer unless a material
  blocker is proved and escalated to the orchestrator.
- Keep local and transported support fields separate.
- Perform one focused repair pass only.
- Do not stage generated outputs or begin Goal 006.

## Task 1: Cross-Rate Seed And Benchmark Core

**Files**

- Create: `src/latent_landscapes/goal005/__init__.py`
- Create: `src/latent_landscapes/goal005/benchmark.py`
- Create: `tests/test_goal005_benchmark.py`

**Produces**

- frozen truth-rate and index mapping;
- exact reconstruction of the Goal 004 bank and central ensembles;
- disjoint flank seed records under `SeedSequence(20260729)`;
- local calibration/validation rows for all truth and bank combinations;
- transported-cutoff validation fields;
- truth-specific predictive and observation-window summaries;
- local bank-stability and overall decision classes; and
- compact retained state only.

Use tiny configurations for red-green development. Tests must cover exact
truth indices, seed replay/uniqueness, central Goal 004 reconciliation, one
shared bank, truth-specific data generation, local versus transported
cutoffs, truth-specific MLE error, train/holdout isolation, unpooled
prediction, class precedence, and scientifically negative completed outcomes.
Central reconciliation must compare with the exact frozen cutoffs, coverage
counts and Wilson bounds, topology/boundary counts, paired Brier intervals,
bank classes, and overall class in `Goal.md`; comparing two calls through the
same implementation is insufficient.

## Task 2: Deterministic Review Pack And CLI

**Files**

- Create: `src/latent_landscapes/goal005/artifacts.py`
- Create: `scripts/run_goal005.py`
- Create: `tests/test_goal005_artifacts_cli.py`

**Produces**

- the exact 15-file deterministic review pack;
- JSON with NaN and infinity rejected;
- compact CSVs with `truth_rate`, `bank_variant`, and cutoff-source fields;
- three readable SVG figures;
- a CLI with only an output-directory override; and
- zero exit for every completed scientific class, nonzero with no bundle only
  for `implementation_blocked`.

Tests must cover exact file set, byte identity on tiny results, same-target
idempotence, no absolute paths, ignored output locations, central Goal 004
reconciliation in verification, readable scientific labels, and CLI failure
handling.

## Task 3: Documentation And Goal Log

**Files**

- Modify: `README.md`
- Modify: `docs/programme.md`
- Modify:
  `docs/goals/005-stochastic-one-rate-cross-rate-recovery/Log.md`

Document the local-versus-transport distinction, the conditional nature of
truth-specific calibration, and the decision outcome. Record source identity,
validation commands, captured runtimes only, decision-driving values, bundle
hashes, ignored state, and limitations.

## Task 4: Production Validation And Review

Run:

```bash
git diff --check
uv run pytest tests/test_goal005_benchmark.py \
  tests/test_goal005_artifacts_cli.py --no-cov
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
uv run python scripts/run_goal005.py
uv run python scripts/run_goal005.py \
  --output-dir artifacts/goal005_stochastic_one_rate_cross_rate_repeat
diff -rq artifacts/goal005_stochastic_one_rate_cross_rate \
  artifacts/goal005_stochastic_one_rate_cross_rate_repeat
```

Inspect all three SVGs once. Perform one independent final scientific/code
review against the current diff and raw artifacts. Apply at most one focused
repair for a material defect, rerun affected checks, and return for
orchestrator acceptance.
