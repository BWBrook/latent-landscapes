# Historical compute-node portability pilot

**9 November completion and launch.** All 18 banks, 207 frozen qualification
arm datasets and five outstanding historical diagnostic fits completed with no
missing/invalid tasks. The [batch summary](input-batch-summary.json) records
hashes and measured costs; the [independent review](input-batch-independent-review.md)
checked 230 task identities and 1,362 locally available output hashes, seed
pairs, observation masks and paired biology. Target preparation additionally
checked all raw bank payloads and nine bank pairs and produced 486 fit tasks
with zero pending dependencies.

The full frozen numerical-qualification fit batch is now submitted: 207 dense,
207 lean, 54 independent-bank lean and 18 exhaustive lean. It uses 243
two-worker/two-CPU/8-GB allocations with a 48-hour ceiling, retaining the entire
tight replay and cutoff grid. The completed multi-node historical/bank runs
and source storage dimensions support that allocation; they do not predict
linear scaling or an exact finishing time. A dependent standard reconciler
checks all fit attempts and sends a completion email. Execution completion
still precedes the registered common-anchor, gradient, integration and final
qualification checks. Training and validation remain closed.

This dated update supersedes the earlier running/submitted status paragraphs
below; the historical evidence and original bank-pilot measurements stay intact.


Both cases pass the [predeclared limited portability gate](acceptance-review.md)
on frozen candidate `99af5206b6a4e53f5b8e9d71cbf348f95e9ae574`. This advances
Sprint 2's numerical/execution entry gate. The
[independent completion audit](independent-review.md) recomputed the comparisons
directly from receipt fields. The [summary](pilot-summary.json) records exact receipt hashes, resource measurements,
shared-node counts and all eight cutoffs for every comparison.

| Historical case | Target wall seconds | Target CPU seconds | Peak fit RSS, bytes |
|---|---:|---:|---:|
| 120 sites, cell-00-rep-005-arm-B | 4578.981 | 4573.167 | 694009856 |
| 260 sites, connected-0-arm-C | 33499.084 | 22805.725 | 1276227584 |

For spatial standard, spatial tight, exposure and constant separately, both
cases resolve without trigger, latent-multimodality or envelope-guard flags.
The maximum absolute W difference on exactly shared nodes is
`9.094947017729282e-13`. All eight complete level sets have matching component,
root, endpoint and truncation types. The largest ordered root/component-endpoint
difference is `1.0507972270090704e-10` in log h. These are comparisons between
executions of the specified numerical procedure; they do not certify a global
optimum or exact-integral fidelity.

Each spatial view has nine exactly shared nodes in the 120-site case and ten
in the 260-site case. The complete spatial meshes have 70 nodes in the former
and 151 local versus 150 target nodes in the latter. Many adaptive nodes differ
in their exact floating-point locations. Those unmatched nodes remain untested pointwise.
The acceptance gate deliberately compares exact shared nodes and complete
level sets without interpolation. Fresh qualification still requires its
separate exact-union anchor audits and fixed panel.

The 120-site local reference has the preserved dirty-source reconstruction in
[the entry evidence](../paper1-sprint2-2026-11-06/diagnostic-replay.json).
Its numerical procedure is equivalent to the clean candidate, with the
source-byte differences documented there. Both 260-site executions record the
clean candidate. Input hashes match by their five data roles. The pinned OCI
manifest, actual SIF hash, dependency lock, interpreter and package versions are
retained with the raw runtime receipt; its public subset and hash appear here.

The first 260-site attempt was killed when its four-hour scheduler limit was
exceeded. Its 245 fixed-fit events and unfinished attempt remain intact. A
second attempt used the same frozen task, source, runtime, data and numerical
settings under a twelve-hour ceiling. It resolved. Final task reconciliation
reports two resolved, zero missing and zero invalid tasks. The successful
retry does not erase the failed attempt or its resource use.

The 260-site execution used 9.31 wall hours and 6.33 CPU-hours; their difference
has not been attributed to a particular cause. These two shared-allocation
measurements do not establish packing or multi-node scaling efficiency.
The first arrival-bank resource pilot has now completed and verified; see the
[bank resource summary](bank-summary.json) and [independent allocation review](bank-independent-review.md).
The task used 15,317.022 wall seconds, 14,968.265 CPU seconds and a fresh
single-task completed-child peak of 1,056,804,864 bytes. Its raw matrix is
131072 by 300; raw and compressed hashes, frozen map and seed identities,
category/moment invariants, task/source/runtime and retained outputs verify.

The remaining 17 banks are submitted using the same frozen 18-task file in
five allocations of four workers, four CPUs and 16 GB, with a 24-hour ceiling.
The already completed task is verified and skipped. This margin follows the
measured peak and the fixed dominant storage shapes; concurrent throughput
and other geometries' realised resource use remain to be measured.

The 207 frozen qualification histories are submitted concurrently in seven
four-worker allocations of 8 GB/two hours. All task identities, qualification
addresses, map inputs, backgrounds, truths, arms and runtime match the frozen
panel. Five outstanding historical diagnostic replays run separately. No
fresh qualification likelihood fits, rule training or validation are launched.
A native scheduler dependency runs task reconciliation after all three arrays
finish, preserves separate phase summaries, and emails the result. It neither
changes scientific settings nor retries failures. Scheduler completion still
requires receipt review. The [independent training-feasibility review](training-feasibility-review.md)
identifies the executable population-uncertainty/forecast decisions still open.
Validation remains closed.

## Reproduce the comparison

Restore the original hash-matched bulk pilot directory and local reference
artifacts. Keep receipts unchanged, including their original absolute child
paths. Set `REMOTE_RESULTS_PREFIX` to the original results-directory prefix
recorded in the task receipts, and `LOCAL_REFERENCE` to the relevant local
receipt. Then run, using a new output path:

```sh
.venv/bin/python docs/evidence/paper1-sprint2-pilot-2026-11-08/compare_pilot.py \
  "$LOCAL_REFERENCE" "$TARGET_RECEIPT" \
  --target-results-root "$LOCAL_RESULTS_MIRROR" \
  --remote-results-prefix "$REMOTE_RESULTS_PREFIX" \
  --target-task "$TARGET_TASK_RECEIPT" --output "$NEW_COMPARISON"
```

The explicit prefix maps the archived absolute target paths into the local
mirror. The comparator checks parent/child and task-output hashes, data-role
identity, source disposition, availability, flags, contacts, shared-node W and
all complete level sets. Full source/runtime/task-plan verification is a
separate parent audit; a comparator pass alone is insufficient. The public
summary excludes raw infrastructure details while preserving receipt hashes.

Verification: 28 fabricated comparator checks pass, covering missing evidence,
changed inputs/source, numerical disagreement, topology/contact disagreement,
and task-output corruption. Run them with:

```sh
.venv/bin/python -m pytest -q \
  docs/evidence/paper1-sprint2-pilot-2026-11-08/test_compare_pilot.py
```

No numerical solver code changed during this pilot or its retry.

## Reproduce the bank resource checks

Use the frozen candidate/runtime and restore the original task and bank paths.
The standard reconciler checks all task inputs and saved output hashes:

```sh
python scripts/pbs/campaign.py reconcile --tasks "$BANK_TASKS" --out "$BANK_RESULTS"
sha256sum "$RAW_BANK" "$COMPRESSED_BANK"
```

At the single-bank checkpoint the full 18-task reconciliation deliberately
returned one completed and 17 missing, with zero invalid. Compare the two
payload hashes with `bank-summary.json`; the raw NPY file is 314,572,928 bytes.
The independent review documents the separately reconstructed seeds, local
compressed-array checks and the raw checks performed on the target. The raw
matrix and its file bytes have different checksums because the NPY header is
part of the file. Neither hash should be substituted for the other.

The PBS completion job depends on all three parent arrays through `afterany`,
then runs each phase's existing reconciler and saves its summary before the
shared derived index is overwritten by the next phase. Any incomplete or
invalid execution makes the completion job fail; terminal scientific failures
in the historical diagnostics remain separately classified. There is no
automatic retry, rule change or promotion to a scientific pass. Email uses
`-m ae` on that final job. These are standard scheduler capabilities
([PBS 19.2 User's Guide, sections 2.5 and 6.2](https://2019.help.altair.com/19.2/PBSProfessional/PBSUserGuide19.2.1.pdf)).
