# Historical compute-node portability pilot

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
Arrival-bank memory and runtime also remain unmeasured on the target. A single
frozen bank-generation task is now running as a resource pilot, with one worker,
8 GB and a 24-hour ceiling, before choosing bank concurrency. It builds
barrier-0 replicate 0 at the frozen bank size and order. Fresh observation
histories and rule training have not run. The [independent training-feasibility review](training-feasibility-review.md)
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
