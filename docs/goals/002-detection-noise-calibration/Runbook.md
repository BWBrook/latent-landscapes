# Goal 002 Runbook

## Environment

From the repository root:

```bash
uv sync --all-groups
```

## Focused Development

```bash
uv run pytest \
  tests/test_likelihood.py \
  tests/test_goal002_calibration.py \
  tests/test_goal002_baseline.py \
  tests/test_goal002_benchmark.py \
  tests/test_goal002_artifacts_cli.py
```

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
```

## Production Run

```bash
uv run python scripts/run_goal002.py
```

Expected ignored output:

```text
artifacts/goal002_detection_calibration/
```

The production command uses exactly 500 calibration and 500 validation
realizations. Test-only injected counts must not be exposed as production CLI
options.

## Full Validation

```bash
git diff --check
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv build
```

Generate two clean production bundles and compare them:

```bash
a="$(mktemp -d)"
b="$(mktemp -d)"
uv run python scripts/run_goal002.py --output-dir "$a"
uv run python scripts/run_goal002.py --output-dir "$b"
diff -rq "$a" "$b"
find "$a" -type f | wc -l
find "$b" -type f | wc -l
```

Both counts must be ten and `diff -rq` must print nothing.

## Human Review

Inspect:

```text
artifacts/goal002_detection_calibration/review.md
artifacts/goal002_detection_calibration/summary.json
artifacts/goal002_detection_calibration/calibration_summary.csv
artifacts/goal002_detection_calibration/predictive_summary.csv
artifacts/goal002_detection_calibration/visuals/coverage_support.svg
artifacts/goal002_detection_calibration/visuals/mle_recovery.svg
artifacts/goal002_detection_calibration/visuals/predictive_scores.svg
```

Confirm that calibration and validation are visibly separate, coverage
uncertainty is labelled as Monte Carlo uncertainty, the neutral model remains
full-support and non-spatial, and the hard-front diagnostic is not used as the
graded decision evidence.

## Publication Boundary

Do not stage generated outputs. Do not commit, merge, push, publish, or begin
Goal 003 until the orchestrator accepts the review pack.

