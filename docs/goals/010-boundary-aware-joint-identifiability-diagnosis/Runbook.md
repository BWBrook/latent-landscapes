# Goal 010 Runbook

## Local Preproduction

From `/Users/bwbrook/papers/latent-landscapes`:

```bash
git status --short --branch
git diff --check
uv run pytest tests/test_goal010_benchmark.py tests/test_goal010_artifacts_cli.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
```

Run the tiny smoke defined by the CLI tests. Do not run the production
configuration on the Mac mini.

## Production Inputs

The trusted Goal 009 source pack is:

```text
artifacts/goal009_remote_runs/goal009-20260727T093142Z-9cb53de/scientific-pack/
```

Create a SHA-256 manifest for every copied input file. The remote run must use
the checksum-verified copy, not an unverified standing remote artifact.

Create a Git bundle containing the accepted preproduction commit. Record:

- exact commit;
- branch;
- bundle filename and SHA-256;
- `uv.lock` SHA-256;
- Goal 009 input-manifest SHA-256.

## Remote Staging

Use `deep-server-ts` and a unique UTC run ID:

```text
/data/codex/scratch/<run-id>/
  input/
  repo/
  output/
  logs/
```

Transfer the verified Git bundle and Goal 009 input pack using
`rsync --checksum`. Verify both manifests remotely before checkout or compute.

Clone from the bundle into `repo/`, detach at the recorded commit, and require:

```bash
git status --short --branch
git rev-parse HEAD
sha256sum uv.lock
uv sync --frozen --all-groups
```

The checkout must be clean and the hashes must match the local source
manifest.

## Compute Provenance

Write a strict JSON provenance input containing at least:

- run ID and `host_id = deep-server`;
- source commit, bundle SHA-256, and verified-bundle flag;
- lock SHA-256;
- Goal 009 input-manifest SHA-256 and verification flag;
- detached-clean checkout flags;
- Python, NumPy, uv, and OS identifiers;
- `worker_count = 3`;
- all four thread limits equal to `"1"`;
- focused-test and smoke flags;
- exact production command.

The CLI must reject incomplete or false production provenance before expensive
compute.

## Remote Checks

Run focused Goal 010 tests, then the implementation's explicitly reduced
three-worker smoke. The smoke is not a scientific campaign and must write only
inside the unique run directory.

## One Production Command

Run exactly once:

```bash
OMP_NUM_THREADS=1 \
OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 \
uv run --frozen python scripts/run_goal010.py \
  --goal009-pack /data/codex/scratch/<run-id>/input/goal009-scientific-pack \
  --output-dir /data/codex/scratch/<run-id>/output/scientific-pack \
  --workers 3 \
  --compute-provenance-json /data/codex/scratch/<run-id>/input/compute-provenance.json
```

Do not retry, widen the grid, change cells, or alter thresholds after observing
the result. A nonzero exit is a completed operational failure for review.

## Retrieval

Create a recursive SHA-256 manifest covering:

- source manifest;
- stdout and stderr;
- compute provenance;
- exit-status record;
- scientific pack, if written.

Retrieve the complete run evidence to:

```text
artifacts/goal010_remote_runs/<run-id>/
```

Verify the manifest locally before opening the scientific result.

## Acceptance Review

Recompute the paired row identities, boundary counts, summary values, bank
classes, and overall decision independently from the returned CSV files.
Render and inspect both SVGs against their tables. Record discrepancies rather
than silently repairing generated evidence.
