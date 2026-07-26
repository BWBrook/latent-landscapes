# Goal 006 Runbook

## Preconditions

```bash
cd /Users/bwbrook/papers/latent-landscapes
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

Expected working branch:

```text
codex/latent-landscapes-goal006-resistance-contrast-review
```

The accepted base is:

```text
edbeb8cc15ea5c95acb74272f0a0122a9cee84f0
```

Do not modify prior-goal source or tests.

## Focused Validation

```bash
uv run pytest tests/test_goal006_spread.py \
  tests/test_goal006_benchmark.py \
  tests/test_goal006_artifacts_cli.py --no-cov
```

## Full Validation

```bash
git diff --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
```

## Production

After source and tests are stable:

```bash
uv run python scripts/run_goal006.py
uv run python scripts/run_goal006.py \
  --output-dir artifacts/goal006_stochastic_resistance_contrast_repeat
diff -rq artifacts/goal006_stochastic_resistance_contrast \
  artifacts/goal006_stochastic_resistance_contrast_repeat
```

Expected canonical pack:

```text
artifacts/goal006_stochastic_resistance_contrast/
```

Both packs must contain exactly 15 files. Generated artifacts and `dist/`
remain ignored and unstaged.

## Review

Inspect the five SVGs and independently check:

- exact eta grid and paired seed count;
- eta-one Goal 003 reconciliation;
- edge-cost ranges and geometric means;
- replicate-level alignment and front metrics;
- habitat contrast signs at eta 0.5 and 1.5;
- decision-class precedence; and
- canonical/repeat byte identity.

Accept a scientifically negative class when the computation is valid. Do not
retune the grid or process in this goal.

## Publication

Publication is allowed only after orchestrator acceptance and independent
final review. Stage exact accepted source, test, script, and documentation
paths. Never stage `artifacts/`, `dist/`, `.venv/`, or caches.
