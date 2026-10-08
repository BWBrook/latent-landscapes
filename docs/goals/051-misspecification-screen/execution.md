# Goal 051 execution record

23 September 2026, Australia/Hobart.

Barry approved the revised 17-cell screen. The
[registration](registration-2026-09-23.md) is the scientific contract.

## Initial preparation record

- At the initial preparation checkpoint, generator, scoring-runner and synthesis
  implementation were in progress in
  separate owned modules. Existing Goal 049/050 source and outputs are retained.
- Source-bound qualification and full-cell timing had not run; production had
  not launched and no Goal 051 scheduler was active. Later phase records below
  supersede this initial status.
- Remote root: `/data/codex/scratch/goal051-misspecification-screen-20260923`.
  Read-only check at 2026-09-23 12:06 UTC found that this root does not yet exist,
  64 logical CPUs, about 123 GiB available memory and 4.3 TiB free on /data.
  No scientific compute process was visible. Recheck before launch.
- Aggregate computation cap is 14,400 seconds; preparation allowance 1,200,
  actual timing and production, and synthesis/verification reserve at least
  1,800. Runtime wrappers must enforce eight workers, one numerical thread,
  32 GiB address space, lock ownership and exact receipts.

## Correspondence

Thread 53 was caught up through global retrieval checkpoint 480, with actual
last message 476 (Astra's own response). Fable's contiguous read boundary was
already 471. Barry's Codex approval supersedes the pending decision in 476.
Astra owns implementation and the next substantive report; no reviewer or
human reply is needed now.

## Completion requirements

Record registration/source/input identities, focused controls and independent
review, timing and budget receipts, exact production/synthesis receipts and
output hashes here as they become available. Review final scientific findings,
predictions, nomination and limitations before closure. No simulation result
or gate pass is asserted by this preparation record.

## Implementation qualification, 23 September

The remote preflight at 12:11:48 UTC verified all 70 Goal 049 source identities
and 14 output files, all 73 Goal 050 source identities and four phase outputs,
both completed-run exit receipts, the original bank, and the exact frozen
detector/reference artifacts. No prior Goal 051 process or launch existed.
The [preflight receipt](../../../artifacts/goal051_execution/preflight.json)
records the evidence. A separate remote source copy and environment were
created from the unchanged uv.lock; Python is 3.14.5. No original run was changed.

Qualification caught and repaired three implementation mistakes before the
source-bound timing run: an incorrect positional small-bank configuration;
scaling one-time integration construction as if it repeated per block; and a
synthesis identity check confusing training predator score with the held-out
predator denominator. A direct held-out marginal-probability calculation on
all 17 small-bank fixture cells now verifies the scorer's decomposition.

The baseline generator control also exposed a floating-point detail: the
original risk-to-hazard conversion is 0.0020000000000000005. B/D/PD now retain
that exact representation for bitwise replay; heterogeneous fields retain the
registered literal 0.002 whole-map mean. This is documented in the registration.

One preparatory microbenchmark instantiated 20 unscored timing-root blocks
before final qualification (approximately 12:15–12:20 UTC). It printed only
setup/generation times and analytic field controls: setup 0.012796625 s;
generation 0.063673825 s/block (1.2734765 s total); covariance reconstruction
error 5.551115123125783e-16; minimum embedding eigenvalue 0.04181608164610457;
823 unreachable tied cells. No cell outcomes, observations, diagnostics or
scores were inspected or saved. This is disclosed as a non-outcome timing
precheck, charged within preparation. It does not qualify source or replace
the registered 16-block full-workload timing. Production root remains untouched.

The [independent implementation review](implementation-review.md) gives GO for
timing, with production still conditional on its complete-workload budget.
Review SHA256 is `722666ae38398064371304c6a4534c558f30f5dc055cc172842efb108655f807`.
It additionally repaired/enforced wrapper identity and timeout/receipt guards,
inclusive prediction thresholds, and the single existential P4 component.

Final Linux qualification: **56 tests passed in 38.84 s**, with the final source
also passing scoped Ruff/mypy and diff checks. The independent auditor ran
30 Goal 051 checks locally. All **82 source/input/helper identities** match
between the local and staged remote trees. The source manifest SHA256 is
`eedc529f40a31d370c270e75628ff76ffa2eb68c3c1a172791b6cf222666af0b`.

## Timing launched

Timing launched once at **2026-09-23 12:36:02 UTC** (22:36:02 Hobart), wrapper
PID **6862**, timeout **600 s**, eight workers, numerical threads one and
32 GiB address-space limit. See `artifacts/goal051_execution/timing-launch.json`
and the remote `timing/{started_at.txt,wrapper.pid,budget_seconds.txt,run.log}`.
It uses 16 complete blocks across all 17 cells with the full grid and bank.
Production had not launched at this checkpoint. Do not duplicate this phase
or change bound source.

On zero exit and verified controls/hashes, run the existing
`prepare-production-budget.py`, inspect its complete projection and receipt,
then launch `run-bounded.sh production` once with that receipt's exact timeout
only if it passes. Preserve a failed budget as a registered stopping outcome.

The `goal-051-screen-completion` heartbeat is active every 30 minutes on this
Codex task. It continues timing/budget/production/synthesis inside the same
envelope, remains quiet while unchanged, and must be deleted after verified
completion or a registered stopping outcome. Neither Barry nor Fable needs
to respond before this approved tranche finishes.

## Timing qualified and production launched

Timing exited **0** at **2026-09-23 12:40:51 UTC**. Its receipt duration was
**289 s** (internal timer 287.485293 s). Full integration construction took
265.525939 s; generation and scoring for 16 complete 17-cell blocks took
16.203063 s. Serialization took 0.088068 s and final validation 0.000625 s.
Every array, seed-disjointness, registered-grid/order, lowest-index fit and
finite-score control passed. Timing endpoints were not evaluated.

The unchanged budget preparer verified all 82 source/input/helper identities,
the frozen score manifest and all timing output hashes before writing
[`production-budget.json`](../../../artifacts/goal051_execution/production-budget.json).
Its SHA256 is `e654cab55095b5a43cfd479a14b1f5e590b85bed61d3118a0bfc25196f82268f`.
The timing summary SHA256 is
`ee9892e1dbb62c0a1f1f1fefd312fb0e0ba9e94338715673a9b4b55615934875`.

| Charged or projected component | Seconds |
| --- | ---: |
| Preparation allowance | 1,200 |
| Actual timing receipt duration | 289 |
| Production fixed construction/startup cost before factor | 271.193537 |
| Production scalable workload before factor | 1,018.234800 |
| Production projection, factor 1.5 on both costs | 1,934.142506 |
| Synthesis/verification reserve | 1,800 |
| Termination grace allowance | 30 |
| Complete conservative projection | **5,253.142506** |
| Registered total cap | **14,400** |

The projection passes. Production launched once at **2026-09-23 12:44:17 UTC**
(22:44:17 Hobart), wrapper PID **7440**, with the bound exact timeout
**11,081 s**, eight workers, one numerical thread and 32 GiB address space.
The dispatch rechecked source, frozen timing outputs, implementation review,
bank SHA256 and absence of any running scorer or prior production start.
See [`production-launch.json`](../../../artifacts/goal051_execution/production-launch.json).
The registration, source and runtime helpers remain unchanged after timing.

At this launch checkpoint production was running; no scientific screen result
was available yet. On zero
exit, verify the frozen production score/output/source identities before
running the existing synthesis wrapper exactly once with its actual remaining
budget and fixed 1,000 paired draws. Retrieve and inspect the evidence, obtain
independent result review, write the scientific synthesis and report on thread
53. Preserve failures and failed predictions. The active heartbeat owns
continuation; no Barry or Fable response is needed. Delete it at verified
completion or a registered stopping outcome.

## Production and fixed synthesis completed

Production exited **0** at **2026-09-23 13:05:58 UTC**, after **1,301 s**
(21 min 41 s; internal timer 1,299.492186 s). All 1,000 paired blocks/17,000
histories were written. Integration construction took 258.254774 s,
generation/scoring 1,031.824731 s, serialization 3.622231 s and final validation
0.021800 s. Maximum reported RSS was 1,051,244 KiB, within the 32 GiB cap.

The 13:09:34 UTC verification checked all 82 bound source/input/helper hashes,
the unchanged bank, all output hashes, all registered controls and seed
disjointness, exact timing/budget input identities and absence of any scorer.
The frozen score manifest still recorded no prior endpoint evaluation. The
[`production-check.json`](../../../artifacts/goal051_execution/production-check.json)
receipt records 11,580 seconds remaining after preparation, timing, production
and a 30-second termination allowance.

The existing synthesis wrapper launched once at **2026-09-23 13:09:49 UTC**,
PID **8012**, with a **1,800-second timeout**. It used exactly **1,000 paired
bootstrap draws**, root **2026092304**, and held the references fixed. It exited
**0** at **13:09:57 UTC** (8 s in the date receipts; `/usr/bin/time` 8.33 s).
The primary nomination is B100-A_h1, delta H=0.230 [0.199,0.259].

All nine synthesis output hashes pass locally and remotely, all 82 source
identities remain unchanged, and no scoring or synthesis process remains.
Verification-receipt SHA256:
`bb487cabaffa5bcbbf870fd4f46a6042328e3a3022f2071eee5f8ebc218933b6`.
Production arrays SHA256:
`6d98c61d8ecee7b53335dec13de536bfbead700fee6d97a48644efafba11e381`.
Frozen production scores SHA256:
`cde04fe4f847f2c3ecb7d97c17b5083195b493a0bfd2ef79f9edb07695efe0d1`.

The full production arrays, receipts and synthesis evidence have been retrieved
to `artifacts/goal051_execution/`; replicate shards remain preserved remotely.
The standalone figure was visually inspected. All 442 cell-metric rows,
364 paired-contrast rows, 21 prediction components and 578 field-diagnostic
rows are retained. Failed predictions were not execution gates.

Charging the full 1,800-second synthesis/verification reserve and 30-second
termination allowance gives **4,620 seconds (77 minutes)** in total, including
preparation 1,200, timing 289 and production 1,301. This is below the registered
14,400 seconds. Recorded synthesis time is covered by that reserve, not added
to it again. No further simulation is required to complete Goal 051.

## Independent review and verified closeout

The [independent final review](final-review.md) gives **PASS**. It reconstructed
all detector and endpoint arrays from the raw production profiles and frozen
references, replayed all 26 bootstrap metrics and paired deltas from the saved
1,000 index draws with maximum difference zero, and reproduced all 578 field
diagnostics and nine synthesis output hashes. It confirms five qualifying
cells and the single global B100-A_h1 nomination. No new histories or bootstrap
draws were generated for verification.

The review checked the [scientific synthesis](synthesis.md) and
[confirmation proposal](confirmation-proposal.md), including endpoint meaning,
failed predictions, coupled field changes, conditional uncertainty and the
unapproved next scope. Review SHA256:
`a364a4a3ad74b90f5f8b31486dbe182f1baaa96ae0895ec7105d5fd53a12ae04`.
The [completed check](../../../artifacts/goal051_execution/completed-check.json)
binds final scientific documents to the verified source and evidence. All 77
relative source hashes, both archived reference files and all three runtime
helpers also match in the local copy: **82/82**.

Goal 051 is complete within its approved scope. Independent confirmation is
proposed as 1,000 new B100-A_h1/B_h1 pairs under a 75-minute/eight-worker/32-GiB
ceiling; it is not authorized or launched. Stage 2 and publication remain out
of scope. The substantive Correspondence report and heartbeat deletion are the
final administrative closeout actions recorded below.

Astra posted the verified scientific findings on Correspondence thread 53 as
**message 491**, then failed predictions, field limitations and the costed
confirmation proposal as **message 492**. The preceding retrieval checkpoint
was 490, whose only new actual message was Astra's approval relay 483.
The completion heartbeat `goal-051-screen-completion` was successfully
**deleted at 2026-09-23 13:24 UTC**. No scoring/synthesis process remains.
Fable's critique is the next correspondence action; Barry then decides on
the separate confirmation proposal. All authorized Goal 051 work is complete.

## Post-closeout critique and revised recommendation, 24 September

Fable's messages 496–498 on Correspondence thread 53 accept closing the screen
and advise against the standalone confirmation as the next step. Astra
reproduced the saved-data diagnostics using
[`posthoc-20260924/reproduce_feedback.py`](../../../artifacts/goal051_execution/posthoc-20260924/reproduce_feedback.py),
which verifies production/evidence/retained-bootstrap input hashes before
reading them. The [results](../../../artifacts/goal051_execution/posthoc-20260924/checks.json)
are descriptive, post hoc evidence. No new process histories, fits, calibration
or bootstrap draws were generated. Registration, synthesis, final review and
the original confirmation proposal still match the completed-check hashes.

The [dated response](fable-response-2026-09-24.md) preserves the failed
predictions, corrects the M/H decomposition, and distinguishes a score blind
spot from a general information limit and field associations from causal bias
allocation. A separate bounded methodological review supported these limits
and the proposed direction; it did not perform a second numerical audit.

Astra withdraws the recommendation for standalone confirmation and proposes
an [adjusted-background pilot](adjusted-background-pilot-proposal.md). Its
24 archive replays, fixed current survey and four-hour computation cap are
**unapproved**. This changes the confirmation-first sequence and requires
Barry's scientific amendment; the screen nominee remains unconfirmed. No
new phase was launched and the completed heartbeat remains deleted.

Astra posted the evidence response and next-route proposal as messages
**502 and 504**, acknowledged all Fable messages through **498**, and read
through task-local retrieval checkpoint **504**. Barry's decision is next;
no Fable response is required. Goal 051's completed scientific outcome and
all original receipts remain unchanged.
