# Goal 053 execution

27 September 2026. Barry approved the six-cell comparison after Fable's replies
514–515. Resource and timing authority remains delegated. The controlling
scientific specification is [registration-2026-09-27.md](registration-2026-09-27.md).

Initial check: deep-server reachable and idle at 04:27:46 UTC, approximately 123 GiB
available. No Goal 053 run directory or process existed. Approved run root:
`/data/codex/scratch/goal053-prospective-background-20260927`.

Read the current handover, frozen proposal, live Git state and resource-control
documents before edits. Existing dirty research files are preserved. Goal052
is closed; its source, registration and numerical evidence remain frozen.
Thread 53 caught up through global cursor 573 and Fable messages 514–515.
Astra acknowledged the approval and review in message 574.

Implementation is split into a six-cell generator, runner/caching/controls and
synthesis, with an independent scientific review of the information calculation
and final implementation. No production outcomes have been generated or viewed.
The proposed 51-hour estimate is replaced only by measured qualification, never
by an outcome-dependent reduction to 500 blocks or another bank/grid.

## Implementation and preparation

The generator, summary synthesis and exact-likelihood controls pass the first
61 focused tests locally (2.95 seconds). All 83 frozen Goal 052 source hashes
still match. Runner/cache controls and independent implementation review are
the remaining qualification work; no production outcomes have been generated.

The [information review](information-review.md) independently reproduces the
day-0 complete-event-time Fisher calculation. An auxiliary, explicitly labelled
conditional-loss-time calculation uses only the six archived arrival maps and
audit root 2026092799. It accesses no registered Goal 053 outcomes. Neither
calculation establishes observed-data RMSE bounds or diagnoses the actual ridge.

At 04:50 UTC deep-server remained idle, with 123 GiB available and 4.3 TiB
free disk. The new run directory and isolated source environment were prepared
after that check with the existing frozen lockfile (Python 3.14.5, NumPy 2.5.1,
SciPy 1.18.0). No timing or production phase has launched. The wrapper fixes
16 workers, one numerical thread each and 48 GiB address space. Initial timing
timeout is 1,800 seconds; production receives a measured, source-bound budget.

## Qualification launch

The independent [implementation review](implementation-review.md) clears the
design for bounded Linux/full-bank qualification, conditional on its controls.
The final combined local suite passes 66 tests; Ruff and strict mypy on all
eight new source, CLI and test files pass. Linux passes the same 66 tests in
14.91 seconds. The first Linux test invocation lacked the old archive at its
default test path (65 passed, one failed); the original failure log is retained.
A read-only symlink to the existing, hash-checked Goal 051 archive supplied
that fixture. No frozen source or numerical result was changed.

Preflight at 04:57:58 UTC authenticated 86 current source files, all 83 old
bindings, both helpers, the full bank, and seed separation against 154,190
previous/bank seeds. Final source-manifest SHA256:
`e7b7addecd8c160fc72f2fc6ca3cefa0ad99e86466e08f33d45b52774e07fada`.

Timing launched **2026-09-27 04:58:31 UTC**, wrapper PID **28472**, Python
PID **28479**, timeout 1,800 seconds. The once-only controller and wrapper
hold the exclusive run lock. Generation committed the 20 timing blocks in
2.7 seconds; the 16 full-bank rows are running. Production has not launched.
Continue from the exact receipts and logs, never by duplicating this phase.

## Timing acceptance and production launch

Timing exited zero at **2026-09-27 05:00:43 UTC** (132 receipt seconds,
130.4 runner seconds). All 16 beta rows cover 120 actual and 80 oracle timing
histories. Maximum h=1 factorisation error is `2.274e-12`; maximum frozen
Goal 052 replay error is `1.819e-12`, both below `1e-10`. Peak RSS was
3.78 GiB. The controller verifies all 34 phase output files and unchanged
source/helper/bank identities. No timing observations enter production estimates.

Timing summary SHA256:
`5588949a8634e4f0db905c593d7dcfd7870d8dfdff7534eba684ab10071fbd0f`.
Run fingerprint:
`b7a87caa216ea9c229110e225081dfe007cc56d1a0eea100d5756136da6d5b63`.

The measured complete-workload projection is 37,130 seconds, including the
1.5 safety factor, assembly allowance and 2,400-second synthesis/verification
reserve. The once-created production budget rounds the production timeout to
**34,800 seconds** (9 h 40 min), with 2,400 seconds for synthesis/verification
and 60 seconds total termination grace. The resulting remaining allowance is
37,260 seconds (10.35 h). This replaces the proposal's rough 51-hour estimate;
it does not change scientific scope or replication.

After inspecting every control and the bound budget, production launched once
at **2026-09-27 05:03:15 UTC**, wrapper PID **29362**, Python PID **29369**.
At 05:04 UTC generation had reached 300/1,000 paired blocks and the process
was alive; no production fit summaries have been inspected. Source and helper
identities are frozen. The controller refuses a second launch.

The active **goal-053-prospective-background-completion** heartbeat checks every
20 minutes and stays quiet while unchanged. It continues verification, the
single fixed 2,000-draw synthesis, result review and scientific closeout, then
deletes itself. Astra owns continuation; no Fable or Barry response is needed.
The information audit was posted as message **578** on thread 53.

## Production acceptance and synthesis launch

Production exited zero at **2026-09-27 08:19:52 UTC**, after 11,797 receipt
seconds (3 h 16 min 37 s). All 81 beta rows cover the 6,000 actual histories
and the registered 1,000-history oracle subset. All 170 output hashes and the
unchanged source, helper, bank and pilot bindings pass controller verification.
Maximum frozen replay error is `1.933e-12`; maximum h=1 factorisation error
is `3.297e-12`, both below `1e-10`. Peak RSS was 3.64 GiB.

Production summary SHA256:
`da229bf9cd4663f23c86452b99ffeefaff2d0ba88320f26ab7202bb2df50fcb9`.
The original process has exited; the completed production phase must not rerun.

The single registered 2,000-draw synthesis launched at **2026-09-27
08:25:45 UTC**, wrapper PID **32138**, with the bound 2,400-second timeout.
Production plus this full allowance remains within the 37,260-second remaining
execution allowance. Evidence retrieval, synthesis verification, figure/table
inspection and independent result review are the remaining closeout work.

## Verified synthesis and scientific closeout

Synthesis exited zero at **2026-09-27 08:26:00 UTC**, after 15 receipt seconds
(13.29 runner seconds), using exactly the registered 2,000 draws. All 13
synthesis outputs, five input hashes and both synthesis source hashes pass.
Synthesis summary SHA256:
`d3aa7622c89cd378b2fbe0775fe73903f2abb8461e04f140782fb728616f448e`.
Timing, production and synthesis used 132 + 11,797 + 15 = **11,944 receipt
seconds** in total. All three phases are complete and must not be restarted.

All observations, evidence metadata, 81 row JSON receipts, run receipts,
summaries, logs and synthesis evidence were retrieved locally. The 85 retrieved
production output hashes and all 13 synthesis output hashes match; every
synthesis input hash matches the verified production manifest. The four full
score rectangles and 81 compressed row arrays remain intact at the remote
run root, where all 170 production files were authenticated. Their paths and
hashes are preserved in `artifacts/goal053_execution/retrieval-manifest.json`.
An initial bulk copy was deliberately interrupted because of low transfer
throughput (rsync exit20); this was a transfer-only change, not a failed or
restarted scientific phase. The subsequent compact retrieval completed zero.

A separate read-only extraction of every actual and oracle maximum, fitted
coordinate and direct/neutral held-out contrast from the remote raw rectangles
agrees **exactly** with all 7,000 saved metric rows. Its receipt is
`artifacts/goal053_execution/score-metric-crosscheck.json`. The three figures
were visually inspected against their tables. A result-level independent
scientific review recomputed all primary means and analytic MCSEs and audited
the registered forecasts, oracle comparison and numerical flags; see
[final-review.md](final-review.md).

The [scientific synthesis](synthesis.md) reports conditional estimation benefit,
substantial flexibility cost under constant background, smaller-than-predicted
predictive gains, all numerical limits and failed forecasts. The
[next proposal](null-effect-calibration-proposal.md) concerns a finite-grid
null-effect decision with reference-table uncertainty and fresh evaluation.
It is a scientific proposal for critique and approval, not an authorized
continuation. No new simulation, confidence calibration, survey modification,
commit, push or publication occurred during closeout.

Astra posted the verified findings and next proposal as **messages 580 and
581** on Correspondence thread 53. The task-local read-updates checkpoint is
579; both new posts are Astra's. The completion heartbeat
`goal-053-prospective-background-completion` was deleted successfully.
Fable owns critique next, followed by Barry's scientific scope decision.
The final verification index is `artifacts/goal053_execution/completed-check.json`.
