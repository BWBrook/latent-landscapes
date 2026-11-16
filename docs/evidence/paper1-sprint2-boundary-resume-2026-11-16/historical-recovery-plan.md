# Frozen two-case historical search recovery plan

16 November 2026. Prepared for independent review before any target smoke.
This is a source-preserving recovery adapter for the two A+B+C development
fits killed after their spatial searches had completed. It is not the new
candidate, a compatibility path, or a retrofit of a77 with within-audit
checkpointing. No target job or numerical fit has been run by this preparation.

## Source and fixed cases

Numerical source remains `a77e849ce0b0381b5c378b222bacfadce9beaf96`.
The adapter is [resume_archived_repair.py](../../../scripts/resume_archived_repair.py),
separately bound at SHA256 `c782bd61b1fcb7b669ce62cb32caa7d6ae26a1a76f90cf5629da4c4fc827c99f`.
A reviewed change to that file needs a new adapter hash before submission.
The run command refuses an adapter hash mismatch.

Both original search snapshots are `profile_numerically_resolved`, with
133 standard points, 133 tight points, two free regimes and 301 fixed-fit
events. Their full event streams preserve candidate histories omitted from
the compact search receipts. Reconstruction from the last full event at each
point/free regime exactly reproduces the frozen compact receipt. All cutoff
roots and both null points are already retained.

The source/runtime/partial-file checks are fixed per case:

```json
{
  "fit-q-base-corridor-0-increased_heterogeneity-mu0.001-h1-C-dense": {
    "task_sha256": "53c54d7a557ba60a89a604d562b84833da520e5b50535d30470a15f6fbb3e1f0",
    "_started.json": "c975b2bdaaaad8754a768ecb6c8272ef4836497e5fae1496aee9eaa3456692ae",
    "fit/search_receipt.json": "ecce3ec4a9cb6d7bdef0815108ab95e818557dc1081ee66ec4f75e38b9f9128b",
    "fit/search/evaluations.jsonl": "5fff9614ba398949271e5855eb14f9f00838b8f7a022e9088983757f6e06e780"
  },
  "fit-q-base-corridor-2-b100_anchor-mu0.004-h1-C-dense": {
    "task_sha256": "b160936f33dfa6de28d5715fecf1c99d2f29528160fc180927ae0933bb3ce72c",
    "_started.json": "d2680a909012fbca9c06116b633016172c8613add265ea5fbf5e48321f946c5e",
    "fit/search_receipt.json": "de304151183cf375e552d25344d0a24c3413e08528c29f0bce92ef3ed4335887",
    "fit/search/evaluations.jsonl": "7ee64c836764fccc8b1c3b5b9078b6fed0adc6ebbdc98dc0397e72d9df2fb42f"
  }
}
```

The common recorded runtime is the original Apptainer context and interpreter
path from each frozen started task, with runtime SIF SHA256
`e71239ad4246ba7a1037d3dd3bc3d29667b7c3081992d95ab33d5d979e3f12ce`.
The adapter uses the unchanged a77 campaign guards to rehash all task inputs
including the SIF, check the exact interpreter path and context, and enforce
the original numerical thread settings. It separately verifies the checkout
is clean at a77 and every tracked Python source under `scripts` and
`src/latent_landscapes`, plus `pyproject.toml` and `uv.lock`, against a77 Git
blobs. Production imports must originate in that verified inventory.

This enforces the runtime contract that was actually recorded. A complete
historical installed-package file inventory was not recorded for these
incomplete attempts; this plan does not invent one or claim that the runtime
SIF alone contains the external virtual environment.

## Bounded continuation

The adapter invokes the unchanged historical `fit_dataset.fit_dataset` with
the original fit arguments and a fresh output directory. Its temporary
`FitSearch` subclass restores only the completed search state, including full
point/free candidate histories, meshes, closure metadata and recorded counters.
It copies the original event stream byte for byte and checks the copied hash.
It does not execute the original search algorithm again.

Cached point reads needed by old spatial reporting/LR are allowed. Any missing
point, refresh, directional fit or free refit causes an immediate adapter
execution abort. `RecoveryExecutionError` inherits `SystemExit` so the old
solver’s broad `Exception` handlers cannot relabel that abort as a scientific
fit failure or continue into expensive later stages. The adapter writes an
explicit `execution_failure` recovery record and leaves no fabricated terminal
fit receipt on that path.

The remaining exposure, constant and latent-audit code is the original a77
code, with its original starts, budgets and guards. No new boundary-reporting
helper is imported. Source/input/runtime identities are checked again after
continuation. A terminal scientific failure is retained as such; completion
of adapter execution is not equivalent to a resolved fit or qualification.

The new output must not exist, must lie outside the original attempt and
numerical checkout, and contains copies of the frozen started/search records,
the regenerated a77 fit outputs, and `recovery.json`. The latter identifies the
adapter separately, records the original input/task/source/runtime bindings
and inventories new outputs by hash. The original attempts are never modified.
An original attempt that has acquired a terminal fit receipt is rejected.

The receipt records reused historical search elapsed time separately. New fit
wall time covers continuation/restoration, not a new complete uninterrupted
fit; neither a sum nor an equivalence claim should hide the original killed
work after search. A kill during this historical adapter’s remaining audit
would leave another partial output; this adapter does not supply new intra-
audit checkpoints to the historical source. The new candidate’s resume path
is reviewed separately.

## Local verification and target boundary

Local verification passed 14 focused tests covering exact state/candidate
restoration, missing history or roots, incomplete/reordered/inconsistent search
state, frozen archive tampering, source commit/dirty changes, runtime/input
drift before output, adapter mismatch, original-output preservation, existing
terminal/output rejection, and immediate execution abort on an unretained
point. Ruff and focused Mypy checks pass. Both actual retained snapshots were independently checked
with `inspect`; this confirmed their fixed hashes and exact reconstruction
without reading raw banks or claiming target source/runtime verification.

Read-only archive inspection:

```sh
.venv/bin/python scripts/resume_archived_repair.py inspect \
  --case "$CASE" --archived-attempt "$ARCHIVED_ATTEMPT"
```

After independent code review and execution freeze, the target smoke must use
the original pinned interpreter/SIF and environment. With local infrastructure
values supplied privately, the invocation is:

```sh
"$ORIGINAL_PYTHON" "$ADAPTER" run \
  --case "$CASE" --archived-attempt "$ARCHIVED_ATTEMPT" \
  --pinned-repo "$FROZEN_REPO" --output-dir "$NEW_RECOVERY_DIR" \
  --adapter-sha256 "c782bd61b1fcb7b669ce62cb32caa7d6ae26a1a76f90cf5629da4c4fc827c99f"
```

Require the frozen search identity and raw spatial report to remain unchanged,
then inspect all remaining family/audit results and the adapter inventory.
Record wall/CPU/resource use and terminal failure class per recovered case.
A completed recovery remains development evidence. Do not overwrite or re-score
the 15 November failure, draw a fresh panel, open training/validation, or run
the 51-task new-candidate replay from this plan alone.

Next: Codex — obtain independent adapter review before the two-case target smoke.
