# Boundary reporting and resumable fits: prospective review packet

The [21 November completion assessment](../paper1-sprint2-acceptance-2026-11-21/README.md) records the result of the replay launched below.

16 November 2026. This advances Paper 1's numerical-qualification decision
following board message 3450. Claude accepted the frozen implementation and
explicit deviations in message 3491. The [target smoke and live launch](launch-assessment.md)
are independently checked; the 51-fit replay, historical recovery and native
interrupted twin are running. Aggregate completion email is job **880988**.
The failed 15 November verdict remains fixed; training and validation remain
closed. No new qualification result exists.

Frozen candidate source: `432bb6e56e672f9e57f2f7bc369546023b07662e`.
The [implementation freeze](implementation-freeze.json) binds source/test bytes,
specifications, unchanged selection and resource limits. Later documentation
commits must not update a pinned target checkout to a different source commit.
That freeze is the pre-execution record; its then-pending review status is
superseded by 3491 and the separately recorded launch, not overwritten.

The [declared deviation](acceptance-deviation.md) retains the same 24+27 tasks,
12,460 exact anchors, criterion/LR tolerances, raw eligibility, numerical budgets,
starts and scientific guards. It introduces **D_boundary**, distinct from the
earlier deferred overflow-arithmetic D. The
[design review](design-review.md) qualifies the mathematical and causal claims;
the [code review](code-review.md) records implementation review and its scope.

## Implemented behavior

`positive_sigma_closed` reports the better of the retained positive endpoint
and the fitted sigma-zero endpoint at the same fixed h. Free-family closure
compares the two retained free optima, preserving the selected h. A strict
boundary win reports sigma = 0 and `boundary_supremum = true`. Raw positive
parameters, candidates and eligibility remain available and continue to drive
starts, ownership and guards. This is a retained lower bound, not a proof of
global maximization. No infinite log-sigma enters optimization.

The v2 non-regression harness compares closed positive criteria on both sides
and uses each side's consistently closed positive free normalizer. Raw criteria
and component LRs are retained. Overall envelope/LR values are unchanged;
separate positive-component LRs can change under the declared definition.
V2 checkpoint identities prevent reuse of the old comparison cache.
With both endpoints eligible, the closed positive quantity and its LR equal
the existing spatial envelope and envelope LR. The amended checks consequently
duplicate those comparisons; raw positive-endpoint agreement is no longer an
independent acceptance requirement. Raw optimization accuracy is not thereby
improved or certified.

Fits accept `--checkpoint-dir` and, on later attempts, `--resume`. Atomic
hash-bound point/free journals replay the original control flow and warm-state
order; completed stages restore search, reduced-family, audit and final-report
state. Partial operations rerun under unchanged numerical budgets. Source,
inputs, options, interpreter bytes/path, dependency versions and runtime SIF
identity must match; corrupt or mismatched checkpoints are rejected.

The PBS submission helper prepares three held arrays, with native `afterany`
dependencies and distinct segment logs, then releases them after all three
have been registered. It preserves accepted job IDs even on partial submission
failure. Every task has a three-attempt cap; each allocation is limited to
48 hours. Later arrays skip terminal scientific outcomes. The clean container
receives the explicit array index and PBS metadata. The final dependency is
reported for a separate receipt reconciliation/completion notification step.

## Verification and explicit limits

The focused boundary/comparison/campaign/resume and adjacent fit/search suite
passed **142 tests** (139 in the main run and three subsequently added integrity
and host-provenance checks). This includes the actual criterion's sigma-squared limit,
boundary/free-h reporting, unchanged raw guards/starts, symmetric closed
comparisons, interruption inside search and at seven stage boundaries,
identity/corruption rejection and bounded PBS submission behavior. The real
numerical test uses production `_fit_family`; the full workflow interruption
tests use deterministic surrogate fits and audits. They do not establish
complete real-data workflow or native PBS equivalence.
The separate historical recovery adapter passed **14 additional tests**, plus
Ruff and focused type checks. Both actual retained search snapshots reconstruct
exactly without loading their raw data or running a fit locally.
The [local validation record](local-validation.json) binds the 156 distinct
checks to the inspected implementation and test bytes.

Equivalence is exact after the field-specific
[normalization](equivalence-normalization.json), with separately verified raw
artifact hashes. Numerical candidates, iterations/evaluations, eligibility,
guards, mode/PD failures and terminal-reason counters remain strict. This is an
explicit clarification beyond literal receipt equality apart from timing:
host/resource/cache telemetry and paths/hashes of timing-bearing artifacts also
vary across executions. It requires reciprocal acceptance before target replay.

Fit timing fields describe the relevant process/stage execution, rather than
a complete bill for all interrupted PBS segments. Aggregate allocation cost
must include all preserved attempt records and native accounting, including
incomplete work repeated after interruption. The three-segment cap is on total
allocations, not three additional retries.

The [49-fit cost report](stage-times.md) and its
[per-fit data](stage-times.json) show 695.019 fit wall-hours: 56.87% search,
39.79% latent auditing and 3.33% reduced families. Tight-tagged event intervals
account for 48.12% of search and 27.36% of full-fit time, with documented
attribution limits. The recorded first-tight marker is the end of a fit;
the later reconciliation window mixes standard and tight work. These are not
guaranteed savings from removing tight replay, which remains unchanged here.

Target execution must still verify the pinned container, scheduler dependencies,
resume across actual segments and the source-preserving recovery smoke for the
two retained `a77e849` search receipts. The separately hashed
[historical recovery adapter and plan](historical-recovery-plan.md) reconstruct
the full candidate state from the two exact frozen event streams, use the
original numerical checkout, and forbid new or refreshed search fits. They
prepare recovery after a complete search; they do not retrofit the old source
with checkpoints inside its later audits. New recovered outputs remain separate
from the original incomplete attempts and failed acceptance ledger.
No new qualification panel follows
automatically from these local checks. Claude's reconciliation of the explicit
comparison and equivalence deviations is the next scientific checkpoint.

Next: Claude — review the frozen implementation and prospective deviation before acceptance execution.
