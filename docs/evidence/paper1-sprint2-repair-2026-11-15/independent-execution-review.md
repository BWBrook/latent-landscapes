# Independent audit of the bounded repair execution

15 November 2026. Codex independent execution audit, after the complete local
result/checkpoint mirror became stable. This advances Paper 1's numerical
qualification decision under the frozen [acceptance plan](../paper1-sprint2-repair-2026-11-12/acceptance-plan.md)
and accepted specification in board message 3307. Candidate:
`a77e849ce0b0381b5c378b222bacfadce9beaf96`.

**The frozen acceptance checks have not passed.** The execution contains 47
resolved fits, two scientific failures and two fits killed at the 48-hour
limit. All 24 selected non-regression fits resolve, but two of their comparison
probes fail the frozen absolute-criterion rule. No threshold was changed. These
are development results; they establish neither qualification nor calibration.
The original rejected candidate and its verdict remain fixed. Training and
validation remain closed.

## Evidence integrity and scope

The audit used local JSON, archived baseline receipts, Git objects and native
accounting/log copies. It did not run a model, retry a task, contact a remote
host, change code or alter a receipt.

- The frozen 51-fit plan and 24-probe plan have unique tasks and the expected
  selection membership. Their JSONL task lists match their plan contents and
  recorded SHA256 hashes. All 51 started records bind their exact planned task
  and canonical task digest. Both missing fits have a preserved started
  attempt, rather than a terminal task record.
- All 49 terminal fit records and all 24 terminal probe records match their
  planned task digests, candidate source commit and clean tracked-source state.
  Root and attempt task records agree byte for byte. Their complete inventories
  contain 294 fit outputs and 120 probe outputs; every listed file hash matches,
  with no extra unlisted attempt output. Fit task/receipt hashes and probe
  receipt hashes agree with the replay summary.
- All 51 original task-record hashes match the frozen selection. For terminal
  fit replays, original fit arguments and runtime are preserved. The fit
  receipts' 5,684 recorded candidate-source file bindings match Git blobs at
  `a77e849`; 245 recorded frozen input bindings match the planned hashes.
  The 24 archived baseline receipt/search pairs match their frozen hashes.
  Baseline and candidate data identity, payload hash identities, cutoff grid,
  search mode and tight-replay contract agree.
- All 12,460 required anchors are present exactly once. Per-view coordinates
  match the frozen exact hexadecimal-coordinate digests, independently rebuilt
  from the archived profile rows, free optima and level-set boundaries.
  All 12,460 checkpoint files match their receipt-bound file hashes and their
  canonical numerical-payload hashes. Their comparison identities, coordinates
  and numerical probes match the terminal comparison receipts. No checkpoint
  error or extra checkpoint was found.
- All 480 free checks and 22,104 anchor checks were recomputed from archived
  baseline values, candidate free values and bound probe payloads, including
  each version's original free-criterion normalizer. Their results agree
  exactly with the receipts. Tolerances remain `1e-6` for absolute criterion
  shift and `1e-3` for profile-LR shift, with unchanged eligibility required.

No integrity or execution-contract contradiction was found. This is a fresh
local rehash of the downloaded results and checkpoints, **not a fresh rehash of
the remote raw arrival banks**. Target-side input checking is evidenced by the
task/reconciliation records and their recorded frozen bindings.

The completion index hash is
`64131645cda43c65c77fee524c2d710f189ca12a9b5948fdd1e8b8458efadc5b`.
All six indexed file hashes match the local files, including replay-summary
SHA256 `7a9300b0db17c07d57d2c81a1be8b98d58aba8a71d31f0bb7fc133d290a3590b`.
Its `qualification_pass=false`, `all_nonregression_passed=false` and
`scientific_review_required=true` agree with the evidence. Phase exit codes are
`[1, 0, 0]`; a completed finalizer is not a successful acceptance decision.

## Outcomes under the frozen checks

| Planned group | Resolved | Scientific failure | Missing terminal fit |
|---|---:|---:|---:|
| Originally resolved non-regression fits | 24 | 0 | 0 |
| Originally failed development fits | 23 | 2 | 2 |
| Total | 47 | 2 | 2 |

The two scientific failures are the dense and lean replays of
`fit-q-base-corridor-1-window_low-mu0.001-h1-B`. Both retain
`search_unresolved`: an unresolved candidate exceeds the selected family
envelope. Constant and exposure families are available; spatial is unavailable.
This is the explicitly excluded envelope/budget case in the accepted repair
scope. It remains failed without tuning or budget expansion.

The two missing terminal fits are development replays:

| Task suffix after `fit-q-base-` | Array index | Native wall time | Exit |
|---|---:|---:|---:|
| `corridor-0-increased_heterogeneity-mu0.001-h1-C-dense` | 31 | 48:01:14 | 143 |
| `corridor-2-b100_anchor-mu0.004-h1-C-dense` | 42 | 48:01:12 | 271 |

Both routed logs explicitly report a wall-time kill against the 172,800-second
limit. Each retains a `profile_numerically_resolved` spatial search receipt
(search elapsed 40.91 and 32.54 hours respectively), but lacks a final fit
receipt and task record. These partial search-stage results are a resource and
recovery lead, not two completed fits. No retry or resume was launched here.

All 24 comparison probes complete, with 22 passes and two
`nonregression_failure` results. There are exactly three failed checks, all
`criterion_shift`, with no profile-LR or eligibility failures and no anchor
errors:

| Original fit | Comparison location | Candidate minus baseline criterion |
|---|---|---:|
| corridor-0 window-high, C, exhaustive | spatial.standard / log h = `0x1.b35a6f90bd69bp+1` / positive_sigma | -1.199879307023366e-6 |
| corridor-0 constant, C, independent bank | spatial.standard / null / positive_sigma | -1.978426303139713e-5 |
| same constant fit | spatial.standard / log h = `0x0.0p+0` / positive_sigma | +3.069501644858974e-6 |

The mechanistic interpretation of those regressions requires reconciliation;
their small size does not waive the frozen criterion gate. The 23 recovered
development failures are useful repair evidence, not an acceptance denominator
or a new qualification result.

The earlier launcher incident is separate: the submitted-job record preserves
50 failed initial allocations, one original started fit, and correction of the
explicit array index/PBS metadata before indices 1–50 were resubmitted. Those
launcher allocations are not 50 scientific failures and are not the two later
48-hour execution losses.

## Resource and inner-solver evidence

Task wall times below are hours per task and sums across parallel tasks, not
campaign elapsed time. The two killed fits are excluded from completed-fit
summaries; native accounting adds about 48 hours each for them.

| Completed tasks | n | Minimum | Median | Maximum | Sum |
|---|---:|---:|---:|---:|---:|
| Non-regression fit replays | 24 | 1.77 | 5.54 | 19.37 | 160.62 |
| Development fit replays, including two scientific failures | 25 | 0.42 | 19.94 | 47.20 | 534.68 |
| Comparison probes | 24 | 2.21 | 4.87 | 14.51 | 143.61 |

Across the 49 terminal fit receipts, there are 1,462,456 recorded inner branch
calls and the same number of `converged` branch terminations; no other branch
termination category appears. Recorded invalid trial rejections total 14,083.
`mode_failures` and `pd_failures` are both zero. Inner branch iteration counts
have median 4, 90th percentile 8, 99th percentile 12 and maximum 27; the
histogram sums exactly to the branch-call count. Recorded mode eta spans
-13.789274608705163 to -2.324543351059409. These aggregates describe terminal
fits only; they do not certify the uncompleted later stages of the two killed
fits. Nuisance work records 9,790,640 site evaluations and 425,522.17 site
evaluation seconds.

The evidence supports that the exception-handling repair is exercised and
avoids inner-exception aborts in the completed fits. Full acceptance remains
unmet because of the frozen non-regression failures and incomplete execution.
Reciprocal scientific reconciliation must decide the next bounded step before
any fresh qualification panel is drawn.

Next: Codex — integrate this audit with the regression diagnosis for review.
