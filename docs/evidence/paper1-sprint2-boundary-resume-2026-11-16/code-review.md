# Independent review of boundary reporting and resumable execution

16 November 2026. This review advances Paper 1's numerical-qualification gate.
It covers the implementation and integration proposed in board message 3450,
not a completed amended acceptance run. The 15 November failed frozen checks
remain failed and are not re-scored.

**Decision:** no remaining code blocker was found in the main candidate paths
listed below. The candidate can be frozen for reciprocal review and the
specified execution checks. This is not a finding of target readiness, passed
acceptance or qualification.

## Independence and scope

This reviewer independently inspected the parent's comparison harness and PBS
changes and the other implementation agent's checkpoint/search/fit changes.
The reviewer authored the small boundary-reporting helper, its selection
sidecar insertion and its focused tests; this note is not an independent
implementation audit of those self-authored lines. Their integration with the
raw search and comparison contracts was reviewed here, and the scientific
definition is separately assessed in [the design review](design-review.md).

The review used source, focused local tests and retained protocol evidence.
No model campaign, remote job, submission, historical recovery, board post or
protected-data access was performed by this reviewer.

## Boundary reporting and comparisons

The `positive_sigma_closed` sidecar reports the better eligible raw positive
endpoint and fitted sigma-zero endpoint. Boundary winners have sigma exactly
zero in the report's sigma-coordinate parameters; the original finite
log-sigma candidate remains intact for optimizer starts and latent audits.
Both raw families remain required and eligible. Fixed-h reports require the
same h; the free closure may choose the sigma-zero free optimum at its own h.
This closes the mathematical positive family, rather than lowering the
optimizer's finite sigma floor.

The root spatial free, null and profile reports retain that sidecar alongside
the raw rows. Raw candidate selection, higher unresolved-candidate guard,
contact ownership, search starts, budgets and envelope calculations remain
unchanged. The closure does not replace an unresolved required family or
promote a scientific failure.

With both eligible raw endpoints, the closed positive criterion is
max(P,Z), algebraically identical to the existing spatial envelope at each
fixed h and for the two free optima. Its closed component LR is consequently
the envelope LR. The amended positive criterion/LR checks therefore duplicate
the envelope checks: they cease independently requiring agreement of the raw
positive-family optimum. Raw eligibility remains separately checked, and raw
positive criterion/LR values remain recorded. Passing these amended numeric
checks would not show that raw positive-endpoint accuracy improved.

Comparison schema v2 computes closed positive values on both sides of the
new comparison. At profile locations it also closes each version's positive
free normalizer. Overall envelope LR and sigma-zero comparisons retain their
original values. Separately normalized positive-family LR may change under
closure; the harness preserves its raw counterpart and raw criterion and
eligibility values for inspection. The new cache identity includes the
comparison schema/definition, source and bound receipts/coordinates, so a v1
probe cannot be silently reused for v2.

The focused boundary test uses a three-site Gaussian likelihood and an
independently assembled normalized determinant calculation at sigma 1e-2,
1e-3 and 1e-4. It verifies a sigma-squared gap tending to the sigma-zero
criterion. The production determinant floor is smooth, not a hard inactive
floor: its normalization gives f(1)=1 exactly while f'(1) differs slightly
from one. The test respects that arithmetic. It does not prove that a few
retained endpoints exclude a distant interior maximum or provide a global
criterion-error bound.

## Checkpoint and segment behavior

Checkpoint JSON is data-only, canonical-hashed and written by temporary file,
flush/fsync, atomic replacement and directory fsync. Identity binds source and
source/input hashes, interpreter path/binary, library versions, container
identity, threads and the search/audit contract. The origin metadata has its
own header hash. Existing checkpoint JSON is validated before reuse; mismatches
refuse continuation rather than being repaired or silently ignored.

The operation journal binds ordered point/free operations, retained candidates,
directional warm state, numerical counters and event payloads. It rejects
missing/reordered/corrupt operations. A durable final operation whose head
write was interrupted can be recovered after verifying the payload. Search
restarts replay those operations in their original control flow before new
fitting. Stage checkpoints preserve completed search, spatial reporting,
exposure, constant, audit and guard results, and the final fit receipt.
Execution interruption propagates as an execution failure; terminal numerical
and scientific failures retain their classifications.

The initial equivalence projection was too broad: it removed whole statistics
subtrees. Review prompted a narrower named projection. Mode and PD failures,
branch outcomes, fit/iteration/evaluation counts, criteria, gradients,
parameters, eligibility and scientific flags remain strict. Regression tests
explicitly protect failure-counter changes, with an additional real numerical
operation interruption/replay test.

The amended equivalence contract must explicitly freeze the projection in
`fit_checkpoints.scientific_payload`: execution host/origin, named timing and
RSS fields, named cache-construction/eviction/evaluator-instance telemetry,
artifact locations and hashes of timing-bearing nested artifacts are omitted
from canonical comparison. Nested search payloads and event contents are
compared separately. This is canonical numerical-payload equivalence with
specified exclusions, not literal byte identity of raw receipts apart only
from timing. Actual raw provenance remains recorded.

The segment driver builds three held, one-worker, 48-hour PBS arrays with
native `afterany` dependencies and distinct logs, journals submitted IDs before
releasing them, and preserves partial submission state. Fit tasks use a stable
checkpoint directory and preserved attempt directories. The campaign counts
started killed attempts toward the three-segment cap; completed or scientific
failure receipts are terminal and skipped rather than retried. After the
bounded chain, an unfinished fit remains an execution/missing failure.
Container launch explicitly forwards the PBS index/job ID and candidate import
path under `--cleanenv`, addressing the earlier index-loss incident.

## Verification and remaining execution conditions

This reviewer observed 27 boundary/qualification tests and 27 comparison,
segment-planning and campaign tests pass, together with Ruff and helper mypy
checks. The latest checkpoint implementation and its real-solver interruption
test were additionally inspected after the tightened equivalence changes;
its implementation agent supplies the complete resume-test execution record.
No native PBS submission was used to validate the driver.

Before claiming amended acceptance or fresh-panel readiness:

- Freeze the [acceptance deviation](acceptance-deviation.md), including the
  comparison definition, exact original 51-task selection, unchanged tolerances,
  equivalence projection and three-segment budget. Preserve the original
  failed record and excluded corridor-1 window-low B case.
- Verify native PBS command availability, array dependency behavior, runtime
  bindings, stage reuse and abort notification configuration on the target.
  Local mocked submission tests establish command construction and failure
  handling, not deployment or delivery.
- Run the prescribed two retained-search smoke cases under the explicitly
  bound original numerical source. The separate archived-a77 adapter has now
  passed the independent review below; target execution and result verification
  remain outstanding. It must not bypass source/input/runtime identity or
  overwrite the preserved attempts.
- Complete the amended 51-task checks before drawing a fresh qualification
  panel. No successful development replay by itself opens training or
  validation.

For sizing, elapsed search time after the first tight evaluation includes
subsequent standard/tight reconciliation. It must not be labelled pure tight
runtime without a finer supported decomposition; see the scoped
[stage-time report](stage-times.md).

## Independent archived-a77 adapter review

The subsequently prepared [two-case recovery plan](historical-recovery-plan.md),
`resume_archived_repair.py` and its tests were reviewed independently of their
author. **No code blocker was found for the bounded target smoke.** This is a
separate orchestration adapter with its own frozen SHA256; it does not modify
or import the new candidate's numerical/reporting code into a77.

The adapter admits only the two explicitly bound development cases. It verifies
the original started-record/task digest, complete search receipt and event
stream hashes, excludes an already terminal original attempt, and reconstructs
full point/free candidate histories from the bound events. Compact projection
must exactly reproduce the frozen search receipt, including both regimes,
null points, retained cutoff roots and event counts. This reviewer independently
inspected both actual local archived attempts: each has 133 standard points,
133 tight points, two free regimes and 301 fixed-fit events; all fixed file
hashes and reconstructions agree.

Before creating output, run mode requires its supplied adapter hash to match
the actual script, the exact recorded candidate import root, clean a77 HEAD,
and tracked Python/source/lock bytes matching that commit. Imports are checked
against that verified inventory before and after importing the historical
entry point. The unchanged a77 campaign guards verify original source,
interpreter/context/SIF and every frozen task input; these checks repeat after
continuation. The historical contract did not bind every installed external
package file, and neither the plan nor this review asserts an invented package
inventory. Target runtime compatibility still requires live verification.

Output must be new and outside both the original attempt and numerical
checkout. Frozen started/search records are copied into it; the search event
stream is copied byte-for-byte and rehashed. The original raw numerical search
state is restored, while exposure, constant and latent-audit code run from the
unchanged historical source under the original arguments/starts/budgets.
Only already retained point reads are permitted. Any missing/refreshed/
directional point or free refit raises adapter-only `RecoveryExecutionError`,
a `SystemExit` subclass that escapes a77's broad `Exception` handlers. Its
execution-failure report cannot be relabelled as a scientific failure or
continue to fabricate a final fit receipt on that path.

The wrapper restores the original class even after failure, repeats source,
input and runtime checks after continuation, and inventories every new output
by hash in its separate recovery report. A completed adapter may still report
a terminal scientific fit failure; target review must require the appropriate
failure class as well as execution completion. The preserved 15 November
result is not changed.

This reviewer observed all **14 adapter tests pass** and the two actual archive
inspections above, without opening raw banks or running target numerical fits.
The test of an unretained point demonstrates immediate escape from a simulated
historical broad exception handler and absence of a fabricated final fit
receipt. Remaining conditions are the target smoke, identity/output/raw
spatial-report checks and resource accounting. A further kill during historical
post-search work is another retained interruption: this adapter does not add
new stage or intra-audit checkpoints to the frozen a77 source and is not an
uninterrupted-fit byte-equivalence claim.

## Reviewed source fingerprints

These SHA256 values identify the bytes inspected, rather than asserting a
clean or committed Git HEAD. Later source changes require review of the delta
and updated fingerprints.

| File | SHA256 |
| --- | --- |
| `scripts/compare_solver_repair_replay.py` | `084138679efab2b1bbbd636c4a9df54ead7f1e4a1491441687848b9582d721bf` |
| `scripts/prepare_solver_repair_replay.py` | `ff38ba08205593c45d912392d890e2ec8c714ec7c8d2822a4a81c6e3c3277017` |
| `scripts/audit_sprint2_pair.py` | `a18d8122dbbcd816e83ca74bd5c8b7cc1fc6aac88709f3b2b03ef861d1a6438a` |
| `scripts/pbs/campaign.py` | `7c4cf820ca1cf05b1cc3f9ac1a3022da874c7b35d756e3e4bfd618fa20ce7f67` |
| `scripts/pbs/array.pbs` | `977fd34d006e84c29a351762245c26c780dc94eef9464dd52d3f48e517c2360d` |
| `scripts/pbs/submit_fit_segments.py` | `3cc13c13169d1502fbe11f7b68a298aca78b357446ae543be8ddcb8765cf8b6d` |
| `scripts/fit_checkpoints.py` | `ccbb25ad76a7cb017ba7489bb720bb90cb8ba3c7c8b34d5b1b060ef96c2d61ff` |
| `scripts/fit_dataset.py` | `20bf2dc7046fba4851a462f7e83bf5fbbea280ade324d9e6c4d74aafa3776198` |
| `scripts/run_development_profile.py` | `402d841a2e8adce873ce901fcdd33b1702996c5729a869e4705cc1e3fc60af97` |
| `src/latent_landscapes/spatial_family_reporting.py` | `c50d04c8ac02b0ce26b3bf1e93afe14e42a3baad4bda945b5e6723d19c5eee48` |
| `scripts/qualify_spatial_profiles.py` | `a0a881684a6c65b84f361713079d8861bf4d445760c3b823fbc02e3d27ae95a5` |
| `tests/test_solver_repair_replay.py` | `e7ae43f1c70f3a86495c4e199782fbe56a32aabc5067d7ea48578efc833f0e01` |
| `tests/test_fit_segments.py` | `c5b3e2491619cfb02d7edfdb538eccef00e414cfc4a0743c90854b72d0b03015` |
| `tests/test_pbs_campaign.py` | `d242e11abbb4c8a88d5a453d0f42fe3d4b474ae266fc6323a5cdc9392d996861` |
| `tests/test_fit_resume.py` | `1a01e3ccbb3d1f627a7f269c4477b3a44f24b96794a8210c8f16d0cf9174eded` |
| `tests/test_boundary_reporting.py` | `ab3c59a568073d8cf82aa6f347b6fc3f449aec8b8e4a9c06bb35ef25eca950b2` |
| `scripts/resume_archived_repair.py` | `c782bd61b1fcb7b669ce62cb32caa7d6ae26a1a76f90cf5629da4c4fc827c99f` |
| `tests/test_archived_repair_resume.py` | `dac727b3738ff100239b449f545a96f67973cb7a03e24625ec2263d3e33695c8` |

Next: Claude — review the frozen deviation and execution conditions before the amended run.
