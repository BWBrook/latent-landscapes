# Goal 004 Stochastic One-Rate Recovery Implementation Plan

> **For agentic workers:** implement this plan task by task with test-first
> development. Treat `Goal.md` as the authoritative scientific contract.

**Goal:** Build and calibrate a site-history simulated composite likelihood
for the accepted one-rate stochastic spread generator.

**Architecture:** Reuse the frozen landscape, design, and Goal 003 simulator.
Generate one independent integration bank of arrival times at the 160 survey
sites, then use exact rate scaling to construct site-history composite
profiles. Run independent calibration and validation datasets, compare
training-only predictions with the full-support neutral, and write compact
review artifacts.

**Tech Stack:** Python 3.14, NumPy, standard library, pytest, Ruff, mypy, uv.

## Global Constraints

- Implement the exact fixed values and formulas in `Goal.md`.
- Preserve Goal 001, Goal 002, and Goal 003 default behavior.
- Use test-first development for new behavior.
- Name the method `site-history simulated composite likelihood`.
- Never claim that the composite likelihood is a full joint spatial
  likelihood.
- Keep all seed phases disjoint and replayable.
- Do not retain raw full-landscape banks or raw outer-ensemble observations.
- Perform the core implementation and one focused repair pass only.
- Do not normalize, tune, add parameters, or begin Goal 005.
- Do not stage generated artifacts or build outputs.
- Do not publish before orchestrator and independent final review.

## Task 1: Goal 004 Observations And Reusable Neutral

**Files**

- Create: `src/latent_landscapes/goal004/__init__.py`
- Create: `src/latent_landscapes/goal004/observations.py`
- Create: `tests/test_goal004_observations.py`
- Modify: `src/latent_landscapes/goal002/baseline.py`
- Modify: `tests/test_goal002_baseline.py`

**Produces**

- `SURVEY_TIMES = (10, 20, 30, 40, 50, 60)`
- a Goal 004 observation generator accepting one stochastic truth and one
  detection generator;
- exactly 1,920 records with the existing analyst-facing schema; and
- a time-stratified neutral API that accepts an explicit frozen calendar
  while preserving Goal 002 defaults.

Write failing tests first. Cover record order/count, exact replay, known
detection, zero false positives, lack of latent truth fields, frozen split
counts, the new calendar, neutral full support, and Goal 001/002 regression.

## Task 2: Site-History Composite Likelihood

**Files**

- Create: `src/latent_landscapes/goal004/likelihood.py`
- Create: `tests/test_goal004_likelihood.py`

**Consumes**

- 160-site `rho = 1` arrival arrays from an integration bank;
- Goal 004 observations; and
- the exact 601-rate grid in `Goal.md`.

**Produces**

- seven-category Jeffreys-smoothed site onset probabilities;
- complete site-history marginal likelihoods;
- full-data and training composite profiles;
- tied grid MLE sets;
- calibrated grid-support components;
- smoothed recordwise held-out process predictions; and
- exact truth-index and same-field scaling checks.

Write hand-calculated fixtures before implementation. Tests must distinguish
site-history marginalization from an incorrect product of recordwise
marginals, prove full support, preserve tied MLEs, reconcile component
construction, and reject invalid bank shapes, calendars, rates, and
probabilities.

## Task 3: Integration Bank, Calibration, Validation, And Stability

**Files**

- Create: `src/latent_landscapes/goal004/benchmark.py`
- Create: `tests/test_goal004_benchmark.py`

**Consumes**

- frozen Goal 001 landscape and design;
- Goal 003 stochastic simulator;
- Goal 004 observations and composite likelihood;
- Goal 002 order-statistic, Wilson, and normal-interval helpers; and
- generalized full-support neutral.

**Produces**

- the 4,096-process integration bank at the 160 design sites;
- hierarchical seed records for every phase and stream role;
- 500 calibration and 500 validation compact results;
- separate full, first-half, and second-half analyses;
- calibration cutoffs, coverage, support topology, MLE diagnostics,
  predictive comparisons, bank-stability diagnostics, invariants, and final
  decision class.

Use tiny configurations in focused tests. Tests must cover phase separation,
replay, no split simulation, truth evaluation at grid index 300, separate
bank cutoffs, class precedence, leakage prevention, worst-MLE Brier scoring,
set-valued natural-log-rate error, coherent category-marginal held-out
prediction, and scientifically negative completed outcomes.

## Task 4: Review Pack, CLI, And Documentation

**Files**

- Create: `src/latent_landscapes/goal004/artifacts.py`
- Create: `scripts/run_goal004.py`
- Create: `tests/test_goal004_artifacts_cli.py`
- Modify: `README.md`
- Modify: `docs/programme.md`
- Modify:
  `docs/goals/004-stochastic-one-rate-recovery-calibration/Log.md`

Write the exact 12-file review pack, deterministic tables and JSON, concise
scientific review, and two readable SVG figures. JSON must reject NaN and
infinity. The CLI may accept an output-directory override but no scientific
tuning arguments.

The CLI exits zero for every completed scientific class and nonzero only for
`implementation_blocked`. Tests cover exact file set, byte identity under
tiny fixtures, no absolute machine paths, nonblank visual labels, ignored
outputs, and validation-replicate-zero profile selection.

## Task 5: Production Validation And Independent Review

Run:

```bash
git diff --check
uv run pytest tests/test_goal002_baseline.py \
  tests/test_goal004_observations.py tests/test_goal004_likelihood.py \
  tests/test_goal004_benchmark.py tests/test_goal004_artifacts_cli.py --no-cov
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
uv run python scripts/run_goal004.py
```

Write a second clean bundle under an ignored temporary path and require
identical file sets and bytes. Inspect both SVGs once. Record source identity,
exact commands, runtimes, decision-driving values, artifact hashes, and
ignored/unstaged state in `Log.md`.

Perform one independent final scientific/code review. Apply at most one
focused repair pass for material defects, rerun affected checks, and stop for
orchestrator acceptance. Do not begin Goal 005.
