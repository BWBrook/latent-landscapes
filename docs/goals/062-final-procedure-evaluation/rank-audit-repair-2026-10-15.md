# Goal 062 canonical-rank audit repair

Prepared 15 October 2026. **Approved at 15:48 AEDT; continuation launched at
15:51 AEDT.** The proposal and pre-approval evidence below are preserved.
See the [approval and operational discretion record](../../decisions/2026-10-15-goal062-source-amendment-approval.md).
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
all 5,000 stored main records, without generation or refitting. The complete local focused suite passes (85 tests); scoped Ruff, strict mypy
and the diff whitespace check also pass. The [independent source/provenance
review](rank-audit-review-2026-10-15.md) found no blocker to nonproduction
qualification and independently passed all 63 tests in the changed modules.

The repair is committed as `465ee23`. Its frozen 354-file manifest is
`a4f3515f396457130286fb6294f57c32db210f4dff659da1a14e780268b0cb35`, with
exactly seven permitted source/test changes and all other source files
unchanged. The new remote root is
`/data/codex/scratch/goal062-final-procedure-20261015-rank-repair1`.
All **46,676 copied payloads / 9,227,058,106 bytes** passed remote checksum
verification, including all 466 raw SQLite databases. No old decision audit
or completion was copied. The exact failed history and three existing controls pass both independent
continuous reconstruction and canonical-rank checks on Deep, with no new
histories/fits or production-file changes. Full nonproduction qualification
also passed, as detailed below.

An attempted local direct replay stopped at the frozen public-input
reconstruction guard before reaching a history audit. The direct incident
replay evidence above therefore comes from the qualified Deep environment;
the local 5,000-record check concerns stored arithmetic and bindings only.

Deep remains on qualified kernel 6.8.0-146. Barry's authorised reboot remains
conditional on successful campaign/audit completion, verified output return
and a host clear of other active work.


## Completed qualification and requested decision

The frozen repair completed qualification on Deep from **05:37:43 to 06:02:16
AEDT on 15 October** (18:37:43–19:02:16 UTC on 14 October), in 24 minutes
33 seconds including supervision. All **85 Linux tests**, inherited-reference
checks, mechanical reference generation, eight public-fixture refits, all ten
mechanical histories, held-out/diagnostic checks and the 51-worker memory probe
passed. The runtime fingerprint exactly matches the 13 October approved run.
Peak process-group RSS was **30,943,731,712 bytes (28.82 GiB)**. The supervisor
exited zero, with no resource stop or remaining process-group members.

The measured full-workload budget gate is 40.548 hours, below 72 hours. This
is the same qualification projection rule; the approved **46–57-hour planning
allowance** remains the planning reference. The original production deadline
continues to run while this source amendment is awaiting approval.

| Binding | SHA-256 |
| --- | --- |
| Frozen repair source manifest | `a4f3515f396457130286fb6294f57c32db210f4dff659da1a14e780268b0cb35` |
| Unchanged runtime | `acd43764a5d0c2ee574007912a90236f669548a512c460cceb7768bb044e854a` |
| Successful qualification receipt | `824c9ccb00f9ebd4f57a9e533a078748f9a566d2f23198762753db65beff90d4` |
| Returned qualification archive | `51cbb0ac2b36b8dc828d4e10fbc923a2081f2beec5d0c47fbc8304456f724b6f` |
| Return manifest | `aaea2ea8dfb7b5c773a9d21a6d826a51ec2eaf02c37258802847a48a11ba53bb` |

The final independent review supports seeking approval: all 42 numerical
audits passed without release blocks, and all eight public-fixture refits
matched their accepted scores, parameters and statuses exactly.
All 186 returned-file hashes and all 354 frozen-source hashes passed locally.
Before return, Deep reverified all 46,676 carried payloads and the qualification
file bindings. The continuation contains no production decision audit or
completion, declaration lock, held-out score, or production approval file.
The exact incident replay is a separate diagnostic receipt and did not alter
these production files.

**Requested approval:** accept the source amendment bound to the source,
runtime and qualification identities above, and continue the registered
campaign from the preserved checkpoints. Re-audit all 5,000 decisions, then
complete the already authorised declaration lock, held-out scoring,
diagnostics, synthesis, independent scientific closure and output return.
Keep the original absolute deadline, resource limits and interpretation.
This approval would authorise the changed audit/continuation source; it would
not approve a changed statistical procedure, replacement histories, rerunning
their main fits, or an extension of the deadline.

The existing heartbeat is **paused** at this material decision. The 13 October
approval binds the predecessor source and does not itself approve this new
source manifest. No new production attempt or reboot has been made.

## Acceptance and continuation

Barry approved this source amendment in chat on 15 October and explicitly
delegated routine operational repairs and sensible compute decisions. Earlier
wording requiring renewed approval for every source/runtime adjustment is
superseded by that authority; proportionate verification and preservation of
prior evidence remain necessary. The exact accepted proposal is preserved at
commit `13e8abf` and hashed in the approval JSON.

After successful custody/runtime preflight, continuation `run/001` launched
at 04:51:58 UTC / 15:51:58 AEDT with 40 workers to leave headroom for unrelated
jobs. The source/runtime/qualification identities and original absolute
deadline above are unchanged. The heartbeat is active. Completion, scientific
closure, verified output return and the authorised safe reboot remain pending.
