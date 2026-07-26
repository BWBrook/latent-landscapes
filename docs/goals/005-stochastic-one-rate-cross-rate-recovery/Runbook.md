# Goal 005 Runbook

## Environment

From the repository root:

```bash
uv sync --all-groups
```

## Focused Checks

```bash
uv run pytest tests/test_goal005_benchmark.py \
  tests/test_goal005_artifacts_cli.py --no-cov
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
```

## Production Review Pack

```bash
uv run python scripts/run_goal005.py
```

This writes exactly 15 ignored files under:

```text
artifacts/goal005_stochastic_one_rate_cross_rate/
```

Only `--output-dir PATH` may redirect the output. Scientific truths, seeds,
replicate counts, rate grid, calendar, likelihood, and thresholds are not CLI
options.

## Reproducibility

```bash
uv run python scripts/run_goal005.py \
  --output-dir artifacts/goal005_stochastic_one_rate_cross_rate_repeat
diff -rq artifacts/goal005_stochastic_one_rate_cross_rate \
  artifacts/goal005_stochastic_one_rate_cross_rate_repeat
```

The file sets and bytes must match.

## Full Validation

```bash
git diff --check
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv build
git status --ignored --short artifacts dist .venv
```

## Human Review

Open:

```text
artifacts/goal005_stochastic_one_rate_cross_rate/review.md
artifacts/goal005_stochastic_one_rate_cross_rate/visuals/local_recovery_across_rates.svg
artifacts/goal005_stochastic_one_rate_cross_rate/visuals/cutoff_transportability.svg
artifacts/goal005_stochastic_one_rate_cross_rate/visuals/predictive_comparison.svg
```

Confirm that:

- local and transported cutoffs are not conflated;
- each truth has separate coverage and predictive intervals;
- observation-window sparsity or saturation is visible;
- Goal 004 reconciles exactly;
- calibration is not claimed to be operational when truth is unknown;
- between-site process dependence is explicitly omitted; and
- negative outcomes are reported without retuning.

## Publication Boundary

Do not stage generated outputs. Publication is permitted only after
orchestrator acceptance and independent final review.
