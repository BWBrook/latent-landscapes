# Goal 009 Runbook

## Local Development

```bash
uv run pytest tests/test_goal008_benchmark.py \
  tests/test_goal008_artifacts_cli.py --no-cov
```

Record the expected red tests before implementation.

## Local Validation

```bash
git diff --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
```

Require no change to Goals 001-007 or the frozen Goal 008 scientific surface.

## Trusted Transfer

After the clean pre-production commit:

```bash
git bundle create <bundle> \
  codex/latent-landscapes-goal009-portable-cross-truth-recovery main
git bundle verify <bundle>
shasum -a 256 <bundle> uv.lock
```

Transfer the bundle and a manifest with `rsync --checksum`. Verify both on
`deep-server-ts` before creating the detached checkout.

## Remote Gates

Use a unique run ID beneath the established `/data/codex` control-plane
directories. Require:

- exact detached Goal 009 commit;
- clean `git status --porcelain`;
- exact `uv.lock` SHA-256;
- `uv sync --frozen --all-groups --python 3.14.5`;
- focused tests;
- a nine-worker miniature campaign; and
- `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, and
  `NUMEXPR_NUM_THREADS` equal to `1`.

## Production

Run the fixed Goal 008 CLI once with the trusted production-provenance JSON.
Capture `/usr/bin/time -v`, stdout, stderr, and exit status.

Do not run a second production campaign in this goal.

## Evidence Return

Create a recursive SHA-256 manifest for the remote evidence directory and
return it with `rsync --checksum`.

Locally verify the manifest and require exactly one of:

1. the complete 16-file scientific review pack; or
2. the complete three-file blocked diagnostic bundle.

## Stop Conditions

Stop without rerunning if:

- source, bundle, lockfile, commit, or environment verification fails;
- focused tests or smoke fail;
- a worker raises;
- the campaign writes a blocked diagnostic bundle;
- the returned file contract or checksum fails; or
- the independent reviewer finds a material unresolved defect.

Do not retune or begin Goal 010.
