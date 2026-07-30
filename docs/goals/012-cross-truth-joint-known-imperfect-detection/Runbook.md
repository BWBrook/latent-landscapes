# Goal 012 Runbook

## Local Acceptance

From the repository root:

```bash
git status --short --branch
git diff --check
uv run pytest \
  tests/test_goal012_benchmark.py \
  tests/test_goal012_artifacts_cli.py
uv run pytest \
  tests/test_goal008_benchmark.py \
  tests/test_goal011_likelihood.py \
  tests/test_goal011_benchmark.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
```

Run only the reduced Goal 012 smoke locally.

## Remote Layout

Use a unique UTC run ID beneath:

```text
/data/codex/scratch/<run-id>/
```

The directory must contain the source bundle and manifest, clean detached
checkout, preflight evidence, smoke pack, production output, launch script,
start/end times, exit status, worker telemetry, run log, recursive checksum
manifest, and exactly one of `DONE` or `FAILED`.

## Bundle And Detached Checkout

After the accepted implementation commit, prepare the dispatch payload locally:

```bash
SOURCE_COMMIT=$(git rev-parse HEAD)
RUN_ID="goal012-$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short=7 HEAD)"
DISPATCH="artifacts/goal012_dispatch/$RUN_ID"
mkdir -p "$DISPATCH"
git bundle create "$DISPATCH/source.bundle" HEAD
git bundle verify "$DISPATCH/source.bundle"
BUNDLE_SHA=$(shasum -a 256 "$DISPATCH/source.bundle" | awk '{print $1}')
LOCK_SHA=$(shasum -a 256 uv.lock | awk '{print $1}')
jq -n \
  --arg run_id "$RUN_ID" \
  --arg source_commit "$SOURCE_COMMIT" \
  --arg bundle_sha256 "$BUNDLE_SHA" \
  --arg uv_lock_sha256 "$LOCK_SHA" \
  '{
    run_id: $run_id,
    source_commit: $source_commit,
    bundle_sha256: $bundle_sha256,
    uv_lock_sha256: $uv_lock_sha256,
    worker_count: 9,
    thread_limits: {
      OMP_NUM_THREADS: "1",
      OPENBLAS_NUM_THREADS: "1",
      MKL_NUM_THREADS: "1",
      NUMEXPR_NUM_THREADS: "1"
    }
  }' > "$DISPATCH/source-manifest.json"
```

Stage into a new directory and create the detached checkout:

```bash
W="/data/codex/scratch/$RUN_ID"
ssh utas-ubuntu "test ! -e '$W' && mkdir -p '$W/source'"
scp "$DISPATCH/source.bundle" "$DISPATCH/source-manifest.json" \
  "utas-ubuntu:$W/source/"
ssh utas-ubuntu "
  git clone '$W/source/source.bundle' '$W/repo' &&
  git -C '$W/repo' checkout --detach '$SOURCE_COMMIT' &&
  test -z \"\$(git -C '$W/repo' status --porcelain)\"
"
```

Do not reuse an existing run directory.

## Remote Preflight And Provenance

Verify remote `HEAD`, clean status, bundle hash, `uv.lock` hash, Python, uv,
NumPy, host, and operating system. Use the explicit installed `uv` path if a
non-login shell does not expose it.

Inside the remote shell:

```bash
set -euo pipefail
RUN_ID="<run-id>"
W="/data/codex/scratch/$RUN_ID"
UV="/home/bwbrook/.local/bin/uv"
export PATH="/home/bwbrook/.local/bin:$PATH"
SOURCE_COMMIT=$(jq -r .source_commit "$W/source/source-manifest.json")
BUNDLE_SHA=$(jq -r .bundle_sha256 "$W/source/source-manifest.json")
LOCK_SHA=$(jq -r .uv_lock_sha256 "$W/source/source-manifest.json")
cd "$W/repo"

{
  git status --short --branch
  git rev-parse HEAD
  git bundle verify "$W/source/source.bundle"
  sha256sum "$W/source/source.bundle" uv.lock
  "$UV" --version
  "$UV" run --frozen python -c \
    'import json, numpy, platform; print(json.dumps({
      "host_id": platform.node(),
      "python_version": platform.python_version(),
      "numpy_version": numpy.__version__,
      "os_identifier": platform.platform()
    }, sort_keys=True))'
} > "$W/preflight.log" 2>&1

test "$(git rev-parse HEAD)" = "$SOURCE_COMMIT"
test "$(sha256sum "$W/source/source.bundle" | awk '{print $1}')" = "$BUNDLE_SHA"
test "$(sha256sum uv.lock | awk '{print $1}')" = "$LOCK_SHA"
test -z "$(git status --porcelain)"
"$UV" sync --frozen --all-groups >> "$W/preflight.log" 2>&1
"$UV" run pytest \
  tests/test_goal012_benchmark.py \
  tests/test_goal012_artifacts_cli.py \
  >> "$W/preflight.log" 2>&1
```

Append both commands' output to `preflight.log` in the actual run. Create a
portable smoke declaration and run the explicitly reduced CLI smoke:

```bash
jq -n \
  --arg run_id "$RUN_ID-smoke" \
  --arg host_id "$(hostname)" \
  '{provenance_mode: "test", run_id: $run_id, host_id: $host_id}' \
  > "$W/smoke-provenance.json"
env \
  OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 \
  "$UV" run --frozen python scripts/run_goal012.py \
    --reduced-smoke \
    --workers 3 \
    --output-dir "$W/smoke" \
    --compute-provenance-json "$W/smoke-provenance.json" \
  >> "$W/preflight.log" 2>&1
```

Only after bundle verification, a clean exact `HEAD`, focused tests, and the
smoke all pass, write the production declaration. Its required schema is:

```bash
export RUN_ID SOURCE_COMMIT BUNDLE_SHA LOCK_SHA W
"$UV" run --frozen python - <<'PY'
import json
import os
import platform
import subprocess
from pathlib import Path

import numpy as np

payload = {
    "provenance_mode": "production",
    "run_id": os.environ["RUN_ID"],
    "host_id": platform.node(),
    "source_commit": os.environ["SOURCE_COMMIT"],
    "bundle_sha256": os.environ["BUNDLE_SHA"],
    "uv_lock_sha256": os.environ["LOCK_SHA"],
    "worker_count": 9,
    "thread_limits": {
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    },
    "bundle_verified": True,
    "remote_head_clean": True,
    "focused_tests_passed": True,
    "smoke_passed": True,
    "python_version": platform.python_version(),
    "uv_version": subprocess.run(
        ["uv", "--version"], check=True, capture_output=True, text=True
    ).stdout.strip(),
    "numpy_version": np.__version__,
    "os_identifier": platform.platform(),
}
Path(os.environ["W"], "compute-provenance.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
jq -S . "$W/compute-provenance.json" >> "$W/preflight.log"
```

Re-read `source-manifest.json` rather than manually transcribing
`SOURCE_COMMIT`, `BUNDLE_SHA`, or `LOCK_SHA`. The scientific provenance JSON
must contain no `/Users/`, `/tmp/`, or `/data/` paths.

## Production

Create `$W/source/launch.sh` with this exact behavior:

```bash
#!/usr/bin/env bash
set +e

W="/data/codex/scratch/<run-id>"
UV="/home/bwbrook/.local/bin/uv"
export PATH="/home/bwbrook/.local/bin:$PATH"

date -u +%Y-%m-%dT%H:%M:%SZ > "$W/start.utc"
if cd "$W/repo"; then
  env \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    /usr/bin/time -v \
    "$UV" run --frozen python scripts/run_goal012.py \
      --output-dir "$W/output" \
      --workers 9 \
      --compute-provenance-json "$W/compute-provenance.json" \
    > "$W/run.log" 2>&1
  status=$?
else
  status=125
  printf '%s\n' "Unable to enter detached checkout" > "$W/run.log"
fi

printf '%s\n' "$status" > "$W/exit.status"
date -u +%Y-%m-%dT%H:%M:%SZ > "$W/end.utc"
if [ "$status" -eq 0 ]; then
  touch "$W/DONE"
else
  touch "$W/FAILED"
fi
exit "$status"
```

Substitute the literal run ID once, make the launcher executable, and launch
exactly one named session:

```bash
chmod 700 "$W/source/launch.sh"
tmux new-session -d -s "$RUN_ID" "$W/source/launch.sh"
tmux has-session -t "$RUN_ID"
```

Do not retry a failed or scientifically negative production command without a
new explicit decision.

## Probe

After inserting the run ID:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 bwbrook@utas-ubuntu 'RUN_ID=<run-id>; W=/data/codex/scratch/$RUN_ID; if tmux has-session -t "$RUN_ID" 2>/dev/null; then echo RUNNING; tmux capture-pane -pt "$RUN_ID":0 -S -40; elif [ -f "$W/DONE" ]; then echo SUCCESS; cat "$W/exit.status"; tail -40 "$W/run.log"; elif [ -f "$W/FAILED" ]; then echo FAILED; cat "$W/exit.status"; tail -80 "$W/run.log"; else echo UNKNOWN; fi'
```

Poll timeouts are observations, not worker deadlines.

## Retrieval And Audit

After the session ends, create and verify a relative recursive SHA-256
manifest over source metadata, preflight, smoke, launcher, logs, sentinels,
telemetry, and production output:

```bash
set -euo pipefail
RUN_ID="<run-id>"
if [[ ! "$RUN_ID" =~ ^goal012-[A-Za-z0-9._-]+$ ]]; then
  printf '%s\n' "Invalid Goal 012 run ID" >&2
  exit 2
fi
test "$(
  ssh utas-ubuntu \
    "jq -r .run_id '/data/codex/scratch/$RUN_ID/source/source-manifest.json'"
)" = "$RUN_ID"
ssh utas-ubuntu "
  [[ '$RUN_ID' =~ ^goal012-[A-Za-z0-9._-]+\$ ]] &&
  cd '/data/codex/scratch/$RUN_ID' &&
  test \"\$(jq -r .run_id source/source-manifest.json)\" = '$RUN_ID' &&
  if [ -f DONE ] && [ ! -f FAILED ]; then
    SENTINEL=DONE
  elif [ -f FAILED ] && [ ! -f DONE ]; then
    SENTINEL=FAILED
  else
    exit 1
  fi &&
  {
    for directory in source smoke output; do
      [ ! -d \"\$directory\" ] || find \"\$directory\" -type f -print0
    done
    printf '%s\0' compute-provenance.json smoke-provenance.json \
      preflight.log run.log start.utc end.utc exit.status \"\$SENTINEL\"
  } |
    sort -z |
    xargs -0 sha256sum > recursive.sha256 &&
  sha256sum --check recursive.sha256
"
mkdir -p "artifacts/goal012_remote_runs/$RUN_ID"
rsync -a --exclude "repo/" "utas-ubuntu:/data/codex/scratch/$RUN_ID/" \
  "artifacts/goal012_remote_runs/$RUN_ID/"
(
  cd "artifacts/goal012_remote_runs/$RUN_ID"
  sha256sum --check recursive.sha256
)
```

Do not read the scientific result before the remote and retrieved manifests
both verify.

Recompute every cutoff, summary, class, and central reconciliation from the raw
tables. Inspect each SVG once against its source data. Do not repair production
evidence in place or rerun the campaign.
