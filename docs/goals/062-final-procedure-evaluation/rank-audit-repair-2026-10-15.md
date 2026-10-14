# Goal 062 canonical-rank audit repair

Prepared 15 October 2026. **Proposed source amendment; production is held.**
This addresses the final-procedure operating-characteristics evidence gap in
Paper 1. It changes audit plumbing and continuation custody, with no change
to the registered statistical procedure or resource envelope.

## Failure and diagnosis

Production attempt 001 stopped at 2026-10-14 07:56:01 UTC, without a resource
stop, on the decision audit for cell 00, replicate 263. All 466 new reference
tables and their independent audits, the 765-table cache, and all 5,000 input
and main-fit bundles had already completed. There are 274 persisted decision
records and 273 accepted decision checkpoints. Held-out scoring and
diagnostics have not started; no declaration lock exists.

The producer ranked canonical persisted scores. The auditor instead ranked
independently reconstructed scores and required exact agreement between the
discrete ranks. Floating-point differences that were acceptable for the
continuous-score audit changed ranks near the fixed tie boundary. In the
failed case, observed T was 1.2596501619555056e-10 and the registered inclusive
tolerance was 1.01e-10. Of the reference scores for 117 retained nodes, 124
crossed the cutoff, changing 67 node p-values. The maximum reference-statistic
difference across the full cache was 4.092726157978177e-12. The final p-value
was 0.602 under both calculations for this case. This is not a claim that all
5,000 final decisions would be invariant to substituting reconstructed scores.

The original failed audit is evidence of a software defect. It is not an
ordinary numerical-fit failure or a scientific abstention.

## Proposed repair

The numerical audit continues to reconstruct the observed screen, fitted
scores and reference statistics independently and compare their continuous
values using the existing tolerances. The separate rank audit independently
reconstructs the rank arithmetic using the verified canonical stored observed
surface, observed statistic and reference values. The observed statistic is
also independently re-derived from the stored raw free/null fit scores and
statuses. Its two existing audit hash bindings, model set, bank and identity
must agree. Nonconverged pairs retain the registered abstention rule.

The production decision implementation, tie constants, thresholds, estimands,
models, observation design, maps, bank, reference panel, random addresses and
all-500 denominators remain unchanged. There is no tolerance widening or
post hoc recalibration.

## Continuation custody and approval

Prepare a separate execution root and frozen source manifest. The old root
and all failed/passed original receipts remain intact. The new manifest pins
a carry-forward inventory of exact predecessor hashes, the original source
manifest, and the original persistent deadline. Only the repaired auditor,
runner, freezer, supervisor and their focused tests may differ between source
manifests; all scientific kernels must match byte for byte.

Copy the complete reference cache and its databases/audits, all 5,000 input
and main-fit bundles, both seed ledgers, and all 274 existing decision records.
Accept predecessor bindings only for explicitly inventoried input/main
checkpoints and the reference cache. Do not copy any old decision audit or
completion into the continuation. Independently audit all 5,000 decisions
under the repaired source before creating the declaration lock and proceeding
to held-out scoring and diagnostics. Existing decision records remain
immutable; the remaining decisions use the registered procedure.

The supervisor must inherit the exact original start and deadline, including
when a continuation deadline file is absent. Deleting that file must never
create another 72-hour window. The deadline remains
**2026-10-16 11:51:16.785553 UTC / 22:51:16 AEDT**. The limits remain 51 workers,
one library thread each, 64 GiB RSS and 50 GiB free scratch. Resume requires
explicit approval bound to the new source and successful qualification,
including when the runtime itself has not changed.

## Evidence and verification

The interrupted evidence archive is preserved locally under
`artifacts/goal062_execution/incident-20261015/`. Its SHA-256 is
`2ec0ff3b6ce5490c421f9af8ca3ec0461a6c43ef4bd512c9c2c10a91765d633a`.
All 46,768 manifest hashes passed after extraction. Raw reference databases
remain on Deep and are checked against the cache receipt before reuse.

The repaired canonical-statistic and main-audit binding checks passed for
all 5,000 stored main records, without generation or refitting. The local
focused auditor and runner tests currently pass (38 tests). Final frozen-source
qualification, exact incident replay on Deep and integrated independent review
will be recorded here before seeking approval.

Deep remains on qualified kernel 6.8.0-146. Barry's authorised reboot remains
conditional on successful campaign/audit completion, verified output return
and a host clear of other active work.
