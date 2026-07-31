# Goal 013 Runbook

## Local Gates

Run:

```bash
git status --short --branch --untracked-files=all
git diff --check
uv run pytest tests/test_goal013_design.py --no-cov
uv run pytest tests/test_goal013_benchmark.py --no-cov
uv run pytest tests/test_goal013_artifacts_cli.py --no-cov
uv run pytest tests/test_goal012_benchmark.py tests/test_goal012_artifacts_cli.py --no-cov
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
```

Run one reduced non-scientific smoke:

```bash
uv run python scripts/run_goal013.py \
  --output-dir artifacts/goal013_reduced_smoke_local_20260731 \
  --reduced-smoke
```

Verify the exact file contract, finite portable outputs, deterministic design
digest, authenticated predecessor evidence, and nonblank SVGs.

## Production Inputs

The production CLI requires:

```text
--goal009-evidence-dir PATH
--goal012-evidence-dir PATH
--output-dir PATH
--workers 4
--compute-provenance-json PATH
```

The two evidence directories must be complete authenticated accepted packs.
Production must refuse `--reduced-smoke`, altered workers, missing thread
limits, dirty or incorrect source state, or non-portable provenance.

## Remote Campaign

Consult the current `nectar` control-plane docs before dispatch. Use one
detached Git-bundle checkout and transfer the two authenticated evidence packs
without adding them to Git.

The remote preflight must prove:

- exact implementation commit, Git bundle, and lockfile hashes;
- clean detached checkout;
- frozen environment and single-thread numerical libraries;
- focused Goal 013 and Goal 012 tests;
- one reduced smoke;
- complete predecessor evidence and portable compute provenance.

Launch exactly one four-worker production command inside `tmux`. Record the
run ID, command, start time, worker telemetry, exit status, completion
sentinel, recursive checksums, and `/usr/bin/time -v` output.

Do not launch a second campaign.

## Retrieval And Acceptance

Retrieve the complete run directory to ignored local storage. Verify recursive
checksums before interpreting the scientific pack.

Independently recompute:

- selector candidates, quantiles, 10,000-attempt search, winning coordinates,
  split, digest, and balance metrics;
- predecessor evidence hashes and six reconciliation rows;
- all intervention cutoffs from raw calibration rows;
- support topology, boundary faces, coverage, precision, prediction
  intervals, bank classes, block-indexed comparisons, and overall precedence;
- exact 18-file contract and every displayed figure value.

Accept a negative result when all implementation and evidence gates pass.
Perform at most one material repair and never retune or rerun after observing
production outcomes.
