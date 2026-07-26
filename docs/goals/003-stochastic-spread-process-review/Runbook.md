# Goal 003 Runbook

## Environment

From the repository root:

```bash
uv sync --all-groups
```

## Focused Development Checks

```bash
uv run pytest tests/test_landscape_spread.py tests/test_goal003_spread.py \
  tests/test_goal003_benchmark.py tests/test_goal003_artifacts_cli.py --no-cov
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
```

## Production Review Pack

```bash
uv run python scripts/run_goal003.py
```

The command must write exactly 13 files under:

```text
artifacts/goal003_stochastic_spread_process/
```

The process law, rate, seed, and ensemble size are intentionally not
command-line options.

## Reproducibility Check

Write a second clean bundle using the CLI output-directory option:

```bash
uv run python scripts/run_goal003.py \
  --output-dir artifacts/goal003_stochastic_spread_process_repeat
diff -rq artifacts/goal003_stochastic_spread_process \
  artifacts/goal003_stochastic_spread_process_repeat
```

The file sets and bytes must match. Remove neither bundle as part of Goal 003;
both are ignored.

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
artifacts/goal003_stochastic_spread_process/review.md
artifacts/goal003_stochastic_spread_process/visuals/arrival_quantile_maps.svg
artifacts/goal003_stochastic_spread_process/visuals/representative_realizations.svg
artifacts/goal003_stochastic_spread_process/visuals/spread_trajectories.svg
artifacts/goal003_stochastic_spread_process/visuals/temporal_scale_diagnostic.svg
```

Confirm that representative realizations are rank-selected, stochastic
variation is visible, water/source handling is coherent, deterministic and
stochastic timing are not conflated, and any old-horizon saturation is
reported rather than normalized away.

## Publication Boundary

Do not stage generated outputs. Do not commit, merge, push, publish, alter the
process definition, or begin Goal 004 until the orchestrator accepts the
review pack.
