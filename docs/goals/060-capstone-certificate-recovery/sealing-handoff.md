# Sealing handoff for Fable

5 October 2026, Hobart. **The public package and public preflight passed.
Fable's final leak review and execution are next.** The script is prepared under
Goal 060; real private generation has not been executed in this tranche.

Review the frozen copies of `src/latent_landscapes/capstone_sealing.py`,
`scripts/seal_capstone.py`, their tests and the methods review in the qualified
package at `/data/codex/scratch/goal060-capstone-recovery-20261004-audit-repair/source` on
`deep-server-ts`. Use the frozen package, whose receipt verifies its source and
runtime, rather than a later live working tree. Barry's private identity is
not needed for generation or encryption.

This command rechecks the qualified package without drawing a private history
root. It already passed on the frozen target:

```sh
ssh deep-server-ts 'cd /data/codex/scratch/goal060-capstone-recovery-20261004-audit-repair/source && OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python scripts/seal_capstone.py preflight --ready /data/codex/scratch/goal060-capstone-recovery-20261004-audit-repair/public-ready.json'
```

After Fable's explicit leak review, the single generation command is:

```sh
ssh deep-server-ts 'cd /data/codex/scratch/goal060-capstone-recovery-20261004-audit-repair/source && OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python scripts/seal_capstone.py seal --ready /data/codex/scratch/goal060-capstone-recovery-20261004-audit-repair/public-ready.json --output /data/codex/scratch/goal060-capstone-recovery-20261004-audit-repair/sealed-v1'
```

It produces the four training histories, encrypted truth and holdout archives,
and hash receipts. Its only printed output is filenames, byte counts and
hashes. The script obtains private entropy once and uses the frozen independent
case/stream addresses. It generates all 160 sites and releases only the 120
training sites; truth and the remaining 40 observations stay in salted,
fixed-size encrypted archives. No private identity, root, realised branch,
parameter, field or latent state belongs in the correspondence report.

An existing output or staging directory is an intentional stop. A failed or
interrupted attempt must be preserved and reported by neutral receipt hashes;
do not delete it, select a new root or rerun under a different output name to
replace the histories. A new attempt needs a recorded decision about recovery.
Successful encryption tests with disposable keys do not establish custody of
Barry's private identity. The later releases follow the existing
[key-custody protocol](../../advisor/capstone-key-custody.md).

The public preflight draws no private history root. Its public-recipient
encryption probe can use operating-system cryptographic randomness. The real
sealing command, which obtains the private root, has not been executed here.

The original package remains preserved with its failed manifest-interface
audit and negative readiness. The repair package retains all 303 original
source files and all scientific outputs; the additive adapter supplies the
independently verified manifest hash to the unchanged audit gate. The repair
source manifest is
`9ee6aad80f0cf132a54a59e7b030c58459008d517ecb31b54d0f3200f9dbd0de`.
See the [repair review](audit-repair-review.md) and
[execution record](execution.md) for the complete chain. The
[final independent review](final-review.md) confirms the qualified public
package and its readiness for this handoff.

The final bindings are:

| Record | SHA-256 |
|---|---|
| Source manifest | `9ee6aad80f0cf132a54a59e7b030c58459008d517ecb31b54d0f3200f9dbd0de` |
| Source archive | `0f1808d60bd3d04a0312892bc6edf5d305fa3500e3090dbe487b43a4ce2384f5` |
| Runtime | `77153eb0a977749e4ba95d9cae33c1f6d31457bdc2cc2d91d2358cede7ec88e1` |
| Independent audit | `30e9f5ac8f9cbf6cb47a21c3370dadc0fdda200979ad024ba5636bef12b0242b` |
| Positive readiness | `e42501fcb5cc438c1706d6e32352f17b22969b89811d3f3114809bd2802b64a2` |
| Returned repair manifest | `bbbb5c1ecea42077644af5d306795ee0abb0ea30b2028e166eb92517b1a9de24` |

The [completion check](../../../artifacts/goal060_execution/audit-repair/completed-check.json)
verified the complete returned package and preservation of the original run.
Qualification is numerical and conditional on this fixed public map/panel;
it does not establish operating characteristics or confirmatory conclusions.
