# Goal 002 Implementation Plan

> **For agentic workers:** implement this packet task by task using test-first
> changes. The goal packet, not conversational history, is the source of truth.

**Goal:** Calibrate one-rate deterministic spread inference across repeated
detection histories and compare it with a full-support neutral baseline.

**Architecture:** Reuse Goal 001's fixed landscape, truth, design, observation
generator, exact likelihood, and holdout evaluator. Add small Goal 002 modules
for neutral prediction, calibration mathematics, ensemble orchestration, and
review artifacts. Build fixed inputs once, summarize each replicate, and
discard its observations and likelihood profiles before continuing.

**Tech stack:** Python 3.14, NumPy, standard library, Matplotlib, pytest, Ruff,
mypy, uv.

## Global Constraints

- Implement exactly 500 calibration and 500 validation realizations.
- Preserve Goal 001 behavior and regression results.
- Fit all predictive models using training records only.
- Keep generated outputs ignored and deterministic.
- Do not retain per-replicate likelihood profiles or raw ensemble observations.
- Perform the core implementation and one focused repair pass only.
- Do not stage, commit, merge, or push before orchestrator acceptance.

## Task 1: Threshold and Calibration Primitives

**Files**

- Modify: `src/latent_landscapes/goal001/likelihood.py`
- Modify: `tests/test_likelihood.py`
- Create: `src/latent_landscapes/goal002/__init__.py`
- Create: `src/latent_landscapes/goal002/calibration.py`
- Create: `tests/test_goal002_calibration.py`

**Interfaces**

- Preserve `profile_likelihood()` defaults exactly.
- Add an optional explicit LR threshold used only to build support classes and
  components; MLE classes and likelihood values must not change.
- Provide deterministic phase-child seed records, the frozen rank cutoff,
  Wilson interval, normal mean interval, exact LR-at-truth calculation, and
  interval/MLE-set summary helpers.

**Test cycle**

1. Write failing tests for Goal 001 default equivalence, rank 476 with ties,
   phase seed separation/replay, Wilson edge cases, and exact truth evaluation.
2. Run the focused tests and confirm the expected missing-interface failures.
3. Implement the minimum public helpers with validation for counts,
   probabilities, finite statistics, and empty samples.
4. Run Goal 001 likelihood tests and Goal 002 calibration tests.

## Task 2: Full-Support Baseline

**Files**

- Create: `src/latent_landscapes/goal002/baseline.py`
- Create: `tests/test_goal002_baseline.py`

**Interfaces**

- `fit_time_stratified_baseline(training_records)` returns one probability per
  frozen survey time using `(y + 0.5) / (n + 1)`.
- `score_time_stratified_baseline(model, holdout_records)` returns finite total
  Bernoulli log score and mean Brier score.

**Test cycle**

1. Write failing hand-calculated tests, including all-zero/all-one training
   strata, unknown times, and proof that predictions stay strictly in `(0,1)`.
2. Implement the smallest immutable model and scorer.
3. Verify that changing holdout outcomes cannot change fitted probabilities
   and that no spatial or truth input is accepted.

## Task 3: Detection Ensemble

**Files**

- Create: `src/latent_landscapes/goal002/benchmark.py`
- Create: `tests/test_goal002_benchmark.py`

**Interfaces**

- `build_fixed_inputs()` builds and reconciles Goal 001 landscape, truth,
  design, habitat distances, and hard-front distances once.
- `run_calibration_phase(config, fixed_inputs)` returns 500 compact calibration
  summaries and the frozen cutoff.
- `run_validation_phase(config, fixed_inputs, cutoff)` returns 500 compact
  validation summaries.
- `run_goal002(config=Goal002Config())` returns aggregate summaries and
  invariants without retaining profiles or raw observations.

**Test cycle**

1. Write failing tests using small injected replicate counts while asserting
   that production defaults remain exactly 500 plus 500.
2. Test training/holdout isolation, exact truth likelihood, calibrated support,
   worst-partition habitat Brier, neutral fitting, and both hard-front
   any/every zero-probability diagnostics.
3. Implement one complete-observation generation per child seed and compact
   per-replicate summaries.
4. Add a memory-oriented regression that result objects contain no observation
   tuples, likelihood profiles, or prediction signatures.
5. Run Goal 001 and Goal 002 focused tests.

## Task 4: Decision and Review Pack

**Files**

- Create: `src/latent_landscapes/goal002/artifacts.py`
- Create: `scripts/run_goal002.py`
- Create: `tests/test_goal002_artifacts_cli.py`
- Modify: `README.md`
- Update: `docs/goals/002-detection-noise-calibration/Log.md`

**Interfaces**

- Classify outcomes in the frozen precedence order from `Goal.md`.
- Write exactly the ten-file artifact contract.
- Serialize non-finite diagnostic values explicitly without invalid JSON.
- Keep figures summary-level and reviewer-readable.
- CLI exits nonzero and writes no review bundle only for
  `implementation_blocked`; negative scientific outcomes exit successfully.

**Test cycle**

1. Write failing small-ensemble artifact and decision fixtures for every outcome
   class, exact paths, required columns, finite neutral scores, and CLI exit
   behavior.
2. Implement CSV/JSON/Markdown/SVG output without embedding raw observations.
3. Generate a small test bundle twice and require identical files and bytes.
4. Run the production 500 plus 500 CLI once and inspect all tables, summaries,
   and figures.

## Task 5: Validation and Handoff

1. Reconcile Goal 001 regression numbers before and after the change.
2. Run `git diff --check`.
3. Run the complete pytest suite with coverage.
4. Run Ruff format check, Ruff lint, and mypy.
5. Build source and wheel distributions.
6. Generate two clean production bundles and require ten identical files.
7. Confirm `artifacts/`, `dist/`, caches, and `.venv/` are ignored and unstaged.
8. Inspect the diff and review pack once for scientific overstatement,
   clipping, leakage, and label legibility.
9. Stop for orchestrator review; do not begin Goal 003.

