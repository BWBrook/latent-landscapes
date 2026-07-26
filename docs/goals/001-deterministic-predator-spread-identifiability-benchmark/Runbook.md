# Goal 001 Runbook

## Environment

From the repository root:

```bash
uv sync --all-groups
```

## Focused Development Checks

```bash
uv run pytest tests -q
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
```

## Generate the Review Pack

```bash
uv run python scripts/run_goal001.py
```

Expected output directory:

```text
artifacts/goal001_deterministic_spread/
```

The command must complete successfully for scientifically negative outcome
classes. It should fail only for implementation or frozen-design invariants.

## Full Validation

```bash
git diff --check
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv build
```

Generate the pack into two clean temporary directories and require identical
file sets and bytes:

```bash
a="$(mktemp -d)"
b="$(mktemp -d)"
uv run python scripts/run_goal001.py --output-dir "$a"
uv run python scripts/run_goal001.py --output-dir "$b"
diff -rq "$a" "$b"
find "$a" -type f | wc -l
find "$b" -type f | wc -l
```

Both counts must equal nine and `diff -rq` must print nothing.

## Human Review

Inspect:

```text
artifacts/goal001_deterministic_spread/review.md
artifacts/goal001_deterministic_spread/summary.json
artifacts/goal001_deterministic_spread/visuals/landscape_design.svg
artifacts/goal001_deterministic_spread/visuals/spread_observations.svg
artifacts/goal001_deterministic_spread/visuals/likelihood_holdout.svg
```

Confirm that the access network is plausible but visibly independent of the
ecological surface, clusters cover the spread gradient, held-out clusters are
meaningfully spatial, detections span pre- and post-arrival periods, likelihood
plateaus and truth are legible, and habitat-versus-neutral predictive evidence
is not overstated.

## Publication Boundary

Do not stage `artifacts/`. Do not commit, push, merge, or publish until Barry
explicitly approves the review pack.
