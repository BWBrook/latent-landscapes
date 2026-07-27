# Goal 007 Runbook

## Environment

From the repository root:

```bash
uv sync --all-groups
```

The production benchmark is designed for the Mac mini. No remote clone,
parallel runtime, or scheduler is required.

## Focused Development

```bash
uv run pytest tests/test_goal007_observations.py \
  tests/test_goal007_likelihood.py \
  tests/test_goal007_benchmark.py \
  tests/test_goal007_artifacts_cli.py --no-cov
```

Use small explicit configurations in tests. Do not expose scientific tuning
arguments through the production CLI.

## Production

```bash
uv run python scripts/run_goal007.py
```

Expected output:

```text
artifacts/goal007_joint_rho_eta_perfect_detection/
```

Scientifically negative completed classes exit zero. Only
`implementation_blocked` exits nonzero and must not leave a review bundle.

## Deterministic Repeat

```bash
uv run python scripts/run_goal007.py \
  --output-dir artifacts/goal007_joint_rho_eta_perfect_detection_repeat

diff -rq artifacts/goal007_joint_rho_eta_perfect_detection \
  artifacts/goal007_joint_rho_eta_perfect_detection_repeat
```

The file sets and bytes must match.

## Validation

```bash
git diff --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
git status --ignored --short artifacts dist
```

Require only ignored `artifacts/` and `dist/` outputs. Inspect every SVG once
and recompute the final class from the CSV/JSON review surface.

## Stop Conditions

Stop and report:

- a pinned-source or replay mismatch;
- invalid or non-finite likelihood values;
- an unsuitable measured local runtime;
- a failed hard artifact or reproducibility invariant; or
- one focused repair that does not resolve a material defect.

Do not retune after seeing production results. A scientifically negative
outcome is complete.
