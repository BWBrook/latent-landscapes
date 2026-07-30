# Goal 011 Runbook

## Local Acceptance

From the repository root:

```bash
git status --short --branch
git diff --check
uv run pytest \
  tests/test_goal011_likelihood.py \
  tests/test_goal011_benchmark.py \
  tests/test_goal011_artifacts_cli.py
uv run pytest \
  tests/test_goal004_likelihood.py \
  tests/test_goal007_likelihood.py \
  tests/test_goal007_benchmark.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
```

Run only the reduced Goal 011 smoke locally. Do not run the 500/500 campaign
on the Mac mini.

## Remote Layout

Use a unique UTC run ID:

```text
/data/codex/scratch/<run-id>/
  source/
  repo/
  smoke/
  output/
  run.log
  start.utc
  end.utc
  exit.status
  DONE or FAILED
```

Create a Git bundle from the accepted preproduction commit. Record and verify
the commit, bundle SHA-256, and `uv.lock` SHA-256 locally and remotely. Clone
the bundle into `repo/`, detach at the recorded commit, and require a clean
checkout before computation.

## Remote Preflight

On `deep-server`:

```bash
git status --short --branch
git rev-parse HEAD
sha256sum uv.lock
uv sync --frozen --all-groups
uv run pytest \
  tests/test_goal011_likelihood.py \
  tests/test_goal011_benchmark.py \
  tests/test_goal011_artifacts_cli.py
```

Run the explicitly reduced CLI smoke into `<run-id>/smoke/`. It is not a
scientific campaign.

## Production Launch

Launch exactly one named `tmux` session. The wrapper must set:

```bash
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
```

The single production command is:

```bash
uv run --frozen python scripts/run_goal011.py \
  --output-dir /data/codex/scratch/<run-id>/output
```

The wrapper writes `start.utc`, captures stdout and stderr in `run.log`, writes
the numeric status to `exit.status`, records `end.utc`, and touches exactly one
of `DONE` or `FAILED`.

Do not retry a failed or scientifically negative production command without a
new explicit decision.

## WSL Probe

After substituting the launched run ID, provide Barry this one-line probe:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 bwbrook@utas-ubuntu 'RUN_ID=<run-id>; W=/data/codex/scratch/$RUN_ID; if tmux has-session -t "$RUN_ID" 2>/dev/null; then echo RUNNING; tmux capture-pane -pt "$RUN_ID":0 -S -40; elif [ -f "$W/DONE" ]; then echo SUCCESS; cat "$W/exit.status"; tail -40 "$W/run.log"; elif [ -f "$W/FAILED" ]; then echo FAILED; cat "$W/exit.status"; tail -80 "$W/run.log"; else echo UNKNOWN; fi'
```

Treat probe timeouts as connection observations, not worker deadlines.

## Retrieval And Audit

Create a recursive SHA-256 manifest covering the source metadata, log,
sentinels, and output bundle. Retrieve the whole run directory without
modification and verify it locally before opening scientific results.

Recompute every decision-driving count and class from the returned CSVs.
Inspect each SVG once against its source table. Record discrepancies; do not
silently repair production evidence or rerun the campaign.
