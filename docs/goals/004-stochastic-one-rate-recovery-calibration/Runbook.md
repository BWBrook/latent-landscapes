# Goal 004 Runbook

## Environment

From the repository root:

```bash
uv sync --all-groups
```

## Focused Development Checks

```bash
uv run pytest tests/test_goal002_baseline.py \
  tests/test_goal004_observations.py tests/test_goal004_likelihood.py \
  tests/test_goal004_benchmark.py tests/test_goal004_artifacts_cli.py --no-cov
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
```

## Production Review Pack

```bash
uv run python scripts/run_goal004.py
```

The command writes exactly 12 files under:

```text
artifacts/goal004_stochastic_one_rate_recovery/
```

The seed, rate grid, survey calendar, bank size, outer replicate counts,
detection probability, smoothing rule, and scientific thresholds are not
command-line options.

## Reproducibility Check

```bash
uv run python scripts/run_goal004.py \
  --output-dir artifacts/goal004_stochastic_one_rate_recovery_repeat
diff -rq artifacts/goal004_stochastic_one_rate_recovery \
  artifacts/goal004_stochastic_one_rate_recovery_repeat
```

The file sets and bytes must match. Both locations are ignored.

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
artifacts/goal004_stochastic_one_rate_recovery/review.md
artifacts/goal004_stochastic_one_rate_recovery/visuals/recovery_calibration.svg
artifacts/goal004_stochastic_one_rate_recovery/visuals/predictive_comparison.svg
```

Confirm that:

- the method is labelled as a site-history simulated composite likelihood;
- full-bank and half-bank conclusions are separated;
- calibrated coverage is restricted to `rho = 1`;
- MLE precision and support width are visible without being converted into
  an invented pass threshold;
- held-out stochastic and neutral predictions use training data only; and
- observations, inference, assumptions, uncertainty, and limitations are
  distinguished.

## Publication Boundary

Do not stage generated outputs. Publication is permitted only after the
orchestrator accepts the completed pack and an independent final review finds
no material unresolved defect.
