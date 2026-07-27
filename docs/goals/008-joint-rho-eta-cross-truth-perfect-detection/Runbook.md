# Goal 008 Runbook

## Local Development

```bash
uv sync --all-groups
uv run pytest tests/test_goal008_benchmark.py \
  tests/test_goal008_artifacts_cli.py --no-cov
```

Tests use small explicit configurations. Verify the test suite observes the
expected red gate before implementation.

## Local Validation

```bash
git diff --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
```

The miniature campaign must give byte-identical results with one and two
workers.

## Trusted Source Transfer

After a clean pre-production feature commit:

```bash
git bundle create /tmp/latent-landscapes-goal008.bundle \
  codex/latent-landscapes-goal008-cross-truth-joint-recovery main
shasum -a 256 /tmp/latent-landscapes-goal008.bundle uv.lock
```

Record the exact commit and hashes in a manifest, transfer both files using
`rsync --checksum`, then verify the bundle before cloning on
`deep-server-ts`. Do not rely on remote GitHub authentication.

## Remote Environment

Use a unique run ID under:

```text
/data/codex/tmp/latent-landscapes/<run-id>/
/data/codex/scratch/latent-landscapes/goal008/<run-id>/
/data/codex/artifacts/latent-landscapes/goal008/<run-id>/
```

Require the recorded detached commit and clean status, then:

```bash
uv sync --frozen --all-groups --python 3.14.5
uv run --frozen pytest tests/test_goal008_benchmark.py \
  tests/test_goal008_artifacts_cli.py --no-cov
```

## Production

Set:

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
```

Run the miniature smoke first. Then run:

```bash
/usr/bin/time -v uv run --frozen python scripts/run_goal008.py \
  --workers 9 \
  --compute-provenance-json <remote-provenance.json> \
  --output-dir <remote-artifact-directory>
```

Capture stdout, stderr, exit status, wall time, and maximum RSS. Generate a
recursive SHA-256 manifest and return the artifact directory and logs with
`rsync --checksum`.

## Local Review

Require exactly 16 files, valid recorded hashes, no absolute remote paths in
the review pack, and only ignored `artifacts/` and `dist/` locally. Recompute
the cell and overall decisions from CSV/JSON and inspect every SVG once.

## Stop Conditions

Stop and report:

- source, lockfile, bundle, or remote commit mismatch;
- seed/pairing/replay or central-reconciliation failure;
- incomplete truth-cell campaign;
- non-finite likelihood or score;
- failed hard artifact invariant; or
- one focused repair that does not resolve a material defect.

Do not retune or begin Goal 009. A completed negative class exits zero.
