# Goal 046 execution state

Updated 11 September 2026, 03:27 UTC. Goal 046 is paused at the scientific
method decision. All production campaigns and numerical checks are complete
and returned. The final K65536/131072 pair has five ensemble passes and four
failures, all independently verified. All 216 replay/half-grid rows reproduce
exactly; 213 pass and three repeat the known corridor generating-rho LR
failure. Every separate grid-refinement gain passes.

The bounded bank-half diagnostic completed successfully in 35.6 minutes,
with peak RSS 3.0452 GiB. Both source snapshots, all 22 inputs and all 38 reduced
arrays are verified. Local and remote checks agree exactly; first-half replay
is exact and combined replay is within 1.365e-12. The [result](split-bank-diagnostic-results.md)
and [independent review](split-bank-diagnostic-review.md) retain the numerical
rejection and recommend a separately registered integration-validation study.
No Goal 046 calculation remains running. The completion heartbeat is paused.
Scientific synthesis and a new method/validation design remain unapproved.

## Authority and deadline

The original window ended at 2026-09-09 00:35:54 UTC. Barry's new instruction
approves an extension at agent discretion. The resumed window is
**2026-09-09 23:00 UTC to 2026-09-11 05:00 UTC** (11 September, 3 pm Hobart).
The slowest measured predecessor timings imply roughly 21–23 hours for the
final campaign and numerical reviews; 30 hours also allows staging, transfer,
verification and scientific review. See [the final bank amendment](bank-escalation-k65536.md)
and [current compute authority](compute-authority.json). The original authority
is preserved in [compute-authority-initial.json](compute-authority-initial.json).
Every new timeout uses only the remaining time to the resumed deadline.

Keep at most nine active map calculations, four workers each, native library
threads one, 96 GiB aggregate RSS and 10 GiB address space per map. The maximum
remains K65536 selected / K131072 reference. No commit, push, publication,
cloud resize or sibling-project change is authorized.

Barry requested three-to-five-hour scheduled checks. The completion heartbeat
used a four-hour cadence through completion and is now paused; Goal 045's
remains paused.

## Completed final K65536/131072 comparison

The remote root is
`/data/codex/scratch/goal046-production-20260910-k65536/`, mirrored locally at
`artifacts/goal046_execution/production65536/`. The campaign source remains the
same 82-file snapshot. The new freeze changes only selected and reference bank
sizes; source, maps, seeds, grids, 250+250 histories and rank 239 remain fixed.
Selected inputs are the immutable K65536 references in
`goal046-production-20260908-k32768/<map>/reference/`. Each new K131072 reference
was followed by a new adoption receipt, full-ensemble comparison and
selected-K65536 replay plus separate half-grid checks, including maps whose
ensemble comparison failed. All nine must qualify before synthesis. The final batch launched at **2026-09-09 23:12:16 UTC**, timeout
PID/process group **58695**, with **107264 seconds** remaining to the fixed
resumed deadline. Startup verified all nine active campaigns at 23:12:44 UTC,
each with the checked 10 GiB address-space cap and native library threads one.
The selected/reference bank sizes are 65536/131072 and every campaign uses four
workers. Startup had no exit or resource-failure marker. Campaign outputs are written
at bundle completion; an absent output directory alone does not imply no work.

At the **15:16 UTC check on 10 September**, all nine K131072 reference
campaigns and ensemble reviews are complete. Campaign runtimes are
47190–54689 seconds (13.11–15.19 hours). Five ensemble reports pass. Four fail:
barrier 2026090811 and 2026090812 have one boundary classification change each;
connected 2026090812 has a boundary change and mean log-width contrast movement
0.012041 against 0.01; corridor 2026090812 has generating-rho LR movement up to
0.888265 against 0.5. These failures do not authorize synthesis or further bank
escalation. Fresh remote checks reconcile both canonical freezes, both 82-file
campaign snapshots, all 11 review/dispatch files and all nine adoption chains.
Local verification reconciles bundle hashes, complete seeds and actual nested
bank prefixes; every ensemble metric reproduces exactly. See the
[returned ensemble check](k65536-ensemble-check.json).

At the **19:17 UTC check on 10 September**, barrier 2026090812 and
2026090813 have completed their separate selected-K65536 replay and half-grid
reviews. All 48 comparison rows pass and reproduce exactly from the returned
arrays, with valid profile/adoption/sidecar hashes, saved/replayed surfaces and
retained grid nodes. See the [first half-grid return check](k65536-first-halfgrid-check.json).
Their review runtimes were 22790.13 and 22085.74 seconds (6.33 and 6.14 hours).
Barrier 2026090812 has map exit 1 because its ensemble boundary criterion fails;
barrier 2026090813 has exit 0. These are consistent numerical exit markers.

At the **23:18 UTC check on 10 September**, all nine half-grid jobs and
process group 58695 have exited. Batch exit 1 matches the four known numerical
map failures; the other five map exits are zero. No memory-limit marker exists.
Peak sampled RSS was 63.8034 GiB. Half-grid review runtimes range from 22085.74
to 28567.90 seconds (6.14–7.94 hours).

All nine reports and sidecars are returned. Independent recomputation verifies
all 216 rows exactly, alongside saved/replayed/reference surfaces, retained
original nodes, adoption/profile/bank hashes and original remote receipt paths.
See [the full half-grid check](k65536-halfgrid-check.json); the earlier two-map
receipt is preserved. Eight reports pass. Corridor 2026090812 fails three
access evaluation-history-zero generating-rho comparisons, repeating the
0.888265/0.887308/0.879710 ensemble failures. All separate grid-refinement gains
pass: maxima are 0.00095434 for effect and 0.13877691 for rho against 0.25.
The final uniform ensemble pair remains rejected.

The bounded split-bank diagnostic launched at **23:28:34 UTC on 10 September**
under `/data/codex/scratch/goal046-split-diagnostic-20260911/`, after the full
half-grid verification. The exclusive `full-launch-receipt.json` binds the
verified 216-row receipt, prepared runner and launcher. Startup rechecked both
82-file source snapshots, all 22 diagnostic inputs, and all nine current
report/sidecar/adoption hashes. The two maps run serially with four workers,
native library threads one, 10 GiB address space and a 96 GiB RSS watchdog.
The single timeout is 3600 seconds, expiring around **00:28 UTC on 11 September**,
earlier than the overall 05:00 UTC deadline. Do not launch a duplicate.

The supervisor PID is 84385 and the calculation PID/process group is 84386.
The 23:30 UTC probe confirms it running with the intended native-thread and
10 GiB limits, no exit receipt or supervisor error, and about 1.53 GiB sampled
RSS. See [the launch check](split-diagnostic-launch-check.json). `full-process.json` records the calculation
process group; `full-run.log`, `full-memory.tsv`, and `full-exit.json` record
execution, resource use and final status. Successful output is written only
at completion to fresh `full-output/diagnostic-report.json` and
`full-output/diagnostic-arrays.npz`. Its absence while a process runs is not a
failure. Return and verify these outputs before interpreting the diagnostic.
The small Linux preflight passed five tests and the 16-row real-helper smoke;
see [the preflight receipt](split-diagnostic-linux-preflight.json).

At the **03:19 UTC check on 11 September**, the diagnostic has finished
successfully with exit 0 at 00:04:11 UTC, after 2135.51 numerical seconds.
Process group 84386 is no longer running, the supervisor log is empty, and
peak RSS is 3193108 KiB (3.0452 GiB). All outputs and final receipts are returned.
Fresh local and remote checks reconcile both 82-file sources, all 22 inputs,
prepared runner/launcher, original remote adoption records and completed
output hashes. Every one of the 38 reduced arrays passes shape/finite checks;
cutoffs, ranks, widths and fixed-window profiles reconstruct exactly. First-half
saved-result errors are zero and combined-bank errors are at most 1.365e-12.
See [the completed diagnostic check](split-bank-diagnostic-check.json).

The [independent final review](split-bank-diagnostic-review.md) confirms the
technical completion and all four unresolved production failures. Equal-sized
connected halves have nearly identical calibrated widths, whereas the combined
bank changes the rank-239 balanced cutoff; corridor halves show substantial
generating-speed tail variation with the same checked local MLE. This does
not isolate exact bias or prove convergence. The heartbeat is paused at the
consequential scientific design decision. No additional computation is queued.

The exact Linux preflight passed 19 focused tests in 51.52 seconds. Both parent
and independent reviewer verified all 82 unchanged campaign files and all 11
review/dispatch files against their manifests. The source snapshot SHA256 is
`6ee147ed17b3324bc2c432b9a1ce7f686f527417f9abb9fa290cea05c53e4c87`;
REVIEW_SNAPSHOT.json SHA256 is
`ef22313befcdda407d03c152e8853d009e5ac3f6e5b8ebca0fe5305ef6e79aaa`.
The new freeze file SHA256 is
`7ec2c8bbb876ce78323cafdb482a73b64286f439b0f5831f6b4c6b91526e6172`,
canonical SHA256
`2e72b2ad5f716bdb2c041a8d5f36d48bcab026de2a93d63f0fc9496c87b50d8a`.

A prelaunch review caught and repaired a race between the launch receipt and
startup preflight before any campaign ran. The duplicate-launch guard remains
in the launcher; startup verifies hashes, authority and prior evidence without
repeating the already-passed test suite. The final manifest and Linux preflight
cover the repaired package. Dispatch authority is bound separately from the
unchanged campaign snapshot, whose historical authority file remains intact.

The local mirror contains launch-receipt.json, startup-check.json, batch.log,
memory_samples.tsv and preflight receipts. Initial campaign PIDs are:

| Archetype | 2026090811 | 2026090812 | 2026090813 |
|---|---:|---:|---:|
| connected | 58710 | 58713 | 58718 |
| corridor | 58724 | 58726 | 58732 |
| barrier | 58734 | 58738 | 58740 |

The four-hour heartbeat monitored this final root, process group, deadline
and adoption chain through completion; it is now paused.

## Completed K32768/65536 predecessor

All nine complete bundles and reports are now returned. A fresh remote check
on 9 September reconciles all 82 files in both campaign snapshots, the ten
review/dispatch files, every original/new adoption, actual nested banks, seeds
and canonical freezes. Local file hashes and all numerical metrics reproduce
exactly. See [the nine-map ensemble check](k32768-ensemble-check.json) and
[the 216-row half-grid check](k32768-halfgrid-check.json).

Four ensemble failures remain, all in the estimated-speed lane:

- Barrier 2026090811: access fivefold upper-boundary and balanced threefold
  lower-boundary classifications change.
- Connected 2026090812: access onefold lower-boundary classification changes.
- Connected 2026090813: balanced threefold lower-boundary classification changes.
- Corridor 2026090812: access onefold lower-boundary classification changes.

Other criterion families pass, including endpoints and count movements within
their limits. All nine half-grid checks pass all 24 rows each. Saved/replayed
surfaces, retained grid nodes and reference surfaces match exactly. Campaign
runtimes are 6.35–7.81 hours; half-grid reviews take 2.81–3.25 hours. The batch
exits 1 with four numerical-failure map exits and five zero exits. Its process
group 38737 has exited; no resource failure occurred. Peak sampled memory was
45.73 GiB. The old reviews do not qualify the future selected-K65536 setting.

The following dated details retain the predecessor's dispatch and first-return
history. Their former active/pending descriptions refer to those earlier checks.

### K32768/65536 dispatch history

- Host: `deep-server-ts`; root:
  `/data/codex/scratch/goal046-production-20260908-k32768/`.
- Queued at **2026-09-08 11:13:09 UTC**, timeout PID/group **38737**,
  with **48165 seconds** remaining to the original deadline. Startup and all
  nine per-map queues were verified. At that check every map was waiting for
  its corresponding original half-grid review; no K65536 calculation had
  started yet. Inspect live state rather than assuming that remains true.
- At **18:55 UTC**, the three barrier K65536 campaigns are complete after
  6.35–6.40 hours each. Their selected-K32768 half-grid reviews are active:
  barrier 2026090812 PID 47043 (52 minutes), 2026090813 PID 47085 (49 minutes),
  and 2026090811 PID 47280 (33 minutes). The six other campaigns remain active,
  6.15–6.73 hours after their starts. Connected 2026090813 has completed all
  calibration histories and at least 25 evaluation histories; corridor
  2026090811 has completed at least 125 calibration histories. The other four
  continue integration. There are still nine active map calculations total.
  No new map exits, completed half-grid reviews or memory-limit marker exists.
  About 5 hours 40 minutes remained at the probe. Campaign output directories
  are created at final bundle writing, so absence of `reference/` alone is not
  evidence that a logged, live process has not started. The start/PID table
  below records original campaign PIDs; the three completed barrier campaign
  PIDs have been replaced by the review PIDs above.
- Each map waits for its original `exit_code` plus the complete reference,
  ensemble and half-grid receipts. It then runs only K65536, retaining the
  same grids, 250+250 histories, rank 239 and four workers. Original numerical
  exit 1 is expected for failing maps; missing complete artifacts prevent
  continuation. At most nine active map calculations run across both batches.
- The new watchdog sums groups **30177 and 38737** while they overlap and
  enforces the common 96 GiB RSS ceiling. Each active map retains a checked
  10 GiB address-space cap and native library threads one. The first combined
  sample was 26.21 GiB. Both groups retain the original hard deadline.
  At the 18:55 check, memory is 42.08 GiB, with a 45.73 GiB peak
  since this successor was queued (the earlier original-batch peak is 42.83 GiB).
- Selected inputs remain `<old-v2-root>/<map>/reference/`; new references are
  `<new-root>/<map>/reference/`. No original campaign receipt is rewritten.
  `make_adoption.py` writes a separate per-map `adoption-receipt.json` after
  K65536 completes, binding both original bundles, source roots and freezes.
- Adoption-aware ensemble and final-selected-K32768 half-grid reviews then
  run sequentially, even if ensemble criteria fail. Both receive
  `--adoption-receipt`; reports preserve that receipt's hash and both freezes.
  Per-map and batch exit markers retain failures. This is not automatic
  scientific acceptance.

| Map | K65536 start (UTC) | PID |
|---|---|---:|
| barrier 2026090811 | 12:00:43 | 40877 |
| barrier 2026090812 | 11:41:43 | 39992 |
| barrier 2026090813 | 11:41:43 | 39994 |
| connected 2026090811 | 12:37:43 | 42027 |
| connected 2026090812 | 12:31:13 | 41865 |
| connected 2026090813 | 12:11:13 | 41244 |
| corridor 2026090811 | 12:22:13 | 41599 |
| corridor 2026090812 | 12:45:43 | 42216 |
| corridor 2026090813 | 12:27:43 | 41763 |

The local mirror is `artifacts/goal046_execution/production32768/`. The
[new freeze](production-freeze-k32768.json) changes only the two bank sizes;
its file SHA256 is `b0ea5b39f1c99b6d609ac552e0b57982b916c6aa3b22f85dd198548da01205be`
and canonical SHA256 is `9d332a1c35592f0b5cb3dbf77e07b7b95605a791e195a93bbdf820f50222da7d`.
The 82-file campaign snapshot is byte-identical to the original, with the same
source snapshot SHA below. Review scripts and dispatch are separately frozen:
`REVIEW_SNAPSHOT.json` SHA256 is
`52ee6a6b1976f7f4dbde257e47c533a0031e6baf2b3b9f87ade955dde0f176cc`.

The independent methodological and concrete dispatch review passed. All 19
focused adoption/ensemble/half-grid tests passed locally and against the final
review snapshot on Linux (93.56 seconds), including both checkers operating on
real reduced campaign bundles without modifying either input. Scoped Ruff and
strict mypy passed. Startup reconciled all 82 campaign and ten review/dispatch
files; the old PID/group identity was checked immediately before launch.
A preceding passing Linux preflight, before adding three stable metadata
comparisons, is retained under `preflight-first/`. The final preflight log and
zero exit receipt are returned. The hourly automation now names both batches
and the explicit adoption path.

## First returned K32768/65536 evidence and resource decision

All three barrier bundles, adoption receipts and ensemble reports are returned.
Remote adoption validation reconciles actual original/new source files, both
canonical freezes, campaign metadata, seeds, four bound files per bundle and
actual nested bank prefixes. A separate 18:57 UTC source recheck verifies all
82 files in each campaign snapshot and all ten review/dispatch files. Locally,
every returned file matches those bindings and the actual bank prefix is exact.
Every numerical-report field is independently recomputed with exact agreement.
See [the compact return check](k32768-first-ensemble-check.json); raw receipts
and the reproducible local check are in the successor mirror.

Local replay uses the unchanged frozen numerical checker with an explicit
in-memory adapter supplying the remotely verified adoption record after local
file/hash/prefix checks. Original adoption paths and campaign receipts are not
rewritten; local replay does not pretend that remote absolute source paths
exist on the Mac. The remote source check and local numerical replay jointly
establish the returned evidence's provenance and agreement.

Barrier 2026090811 fails estimated-speed access fivefold upper-boundary and
balanced threefold lower-boundary classification stability. All other criterion
families pass. Barrier 2026090812 and 2026090813 pass their ensemble reviews;
all three selected-bank half-grid reviews are pending. The all-nine global
qualification requirement means the current bank pair is already rejected.

The independent decision reviewer confirms that a final K65536/131072 pair
cannot fit the remaining original time. Measured components imply about
12 hours for K131072 campaigns, followed by selected-K65536 replay and half-grid
checks. The proposed 24-hour extension retains all current caps and numerical
criteria. It is not authorized yet. No K131072 work has been launched.
Existing calculations may finish under their original hard timeout; pausing
monitoring neither terminates them nor extends their authority.

## Original K16384/32768 batch

- Host: `deep-server-ts`.
- Root: `/data/codex/scratch/goal046-production-20260908-k16384-v2/`.
- Started: **2026-09-08 04:54:14 UTC**, epoch 1788843254.
- Timeout PID/group: **30177**; inspect live state before relying on it.
  `launch-receipt.json` records 70900 remaining seconds to the original deadline.
- All nine declared maps were observed active in production mode immediately
  after launch: connected, corridor and barrier crossed with map seeds
  2026090811, 2026090812 and 2026090813. Each uses four workers, native
  BLAS/OpenMP thread counts one, 250 calibration plus 250 evaluation histories,
  rank 239, G201/H181, K16384 selected and K32768 reference.
- The batch starts nine map processes. Within each map it runs selected,
  reference, full-ensemble numerical review, then selected-bank replay and
  separate half-grid reviews against the saved reference. Both reviews run
  even if the ensemble comparison reports a numerical failure; failures remain
  visible in their individual receipts and terminal markers.
- Each map process has a hard 10 GiB address-space limit, placing their
  aggregate resident memory below the 96 GiB budget. A 30-second process-group
  RSS monitor records `memory_samples.tsv` and terminates the group if 96 GiB
  is exceeded. Inspect `memory_limit_exceeded` and logs if a process disappears.
  A resource failure is not a scientific numerical result.
- The outer timeout terminates the whole process group at the common deadline,
  with a 30-second kill fallback. No new clock starts with this batch.

All nine selected-bank campaigns completed successfully in 7247.65–7866.00
seconds (2.01–2.19 hours), with full 250+250 histories. All nine K32768 reference
campaigns are complete and returned. Every ensemble comparison was independently
reproduced locally with exact agreement, including bundle hashes, seed manifests,
shared freeze/source metadata and actual nested bank prefixes. See
[the compact check](initial-production-ensemble-check.json), also retained as
`reference-return-check.json` in the original local mirror.

Seven maps fail support-boundary stability. Connected 2026090812 and corridor
2026090811 also move declared counts/paired count contrasts by two histories,
beyond the one-history limit. Corridor 2026090812 additionally moves the
generating-rho LR by up to 0.797754 against the 0.5 limit. Connected 2026090811
and barrier 2026090813 pass their ensemble comparisons. These are numerical
results, not scientific recovery conclusions. All original half-grid reviews
are complete, taking 4905.56–5935.02 seconds each. Eight maps pass all 24 rows;
corridor 2026090812 fails the same three generating-rho LR comparisons found
in its ensemble review (maximum 0.797754 versus 0.5). Separate half-grid gains
remain within limits on every map. In total 213 of 216 rows pass.

All nine returned reports and diagnostic arrays were independently checked
locally: sidecar/profile/bank hashes reconcile, selected/reference surfaces
match their campaign bundles, replay differences are zero, original grid nodes
are preserved exactly, and every numerical row reproduces its reported values
and pass/fail classification. See [the compact half-grid check](initial-production-halfgrid-check.json),
also retained as `halfgrid-return-check.json` in the original mirror.

The original batch has `batch_exit_code=1`, matching its seven numerical-failure
map exits. Connected 2026090811 and barrier 2026090813 exit 0. The completed
original group 30177 is no longer running; no resource failure or memory-limit
marker occurred. Its peak sampled memory was 42.83 GiB. The global rejection
of K16384/32768 is unchanged, and no selected-K32768 review is complete yet.

All nine selected bundles have been returned and verified locally at 07:51 UTC.
Checks reconcile profile and bank hashes, complete seed manifests and counts,
the exact shared freeze and source hashes, profile shapes and campaign
invariants. The receipts are `selected-campaign-check.json` (remote validation)
and `selected-return-check.json` (local returned-file validation) in the local
mirror. These establish campaign integrity, not production numerical acceptance.

Per-map paths are `<archetype>-<seed>/selected/`, `reference/`,
`ensemble-review.json`/`.csv`, `halfgrid-review.json`/`.npz`, `run.log`, and
`exit_code`. The batch writes `batch_exit_code` only when its processes finish.
A zero campaign exit alone does not establish numerical qualification.

## Source, freeze and preflight

The local mirror is `artifacts/goal046_execution/production16384-v2/`.
Its 82-file source snapshot SHA256 is
`6ee147ed17b3324bc2c432b9a1ce7f686f527417f9abb9fa290cea05c53e4c87`.
The [production freeze](production-freeze.json) file SHA256 is
`65a70cbee33faf6cb1676ca04169fbf7c55cdda4c1f15898b2e29bb1cc72fc5e`.
The run startup verified all source files and the deadline. The freeze preserves
all map/seed branches, numerical grids and counts, qualification report hashes,
and source snapshot identity. It is stored alongside the source snapshot to
avoid self-referential hashes.

The runtime is the locked Goal 046 Linux environment at
`/data/codex/scratch/goal046-pilot-20260908/source/.venv/bin/python`, with
`PYTHONPATH` bound to this production snapshot's `src/`. Startup confirms that
imports resolve within the production snapshot.

The initial 81-file staging under
`/data/codex/scratch/goal046-production-20260908-k16384/` passed 51 tests but
omitted the unchanged Arc 2C CLI needed by one regression test. That staging
and failed preflight are retained locally and remotely; no production ran
there. The `-v2` snapshot adds only that CLI file. All previous 81 files were
verified byte-identical, and the corrected regression passed in 2.89 seconds.
Thus all 52 focused tests pass on Linux across the two reconciled preflight
receipts. The local full 52-test selection, scoped Ruff and strict mypy passed.
Do not erase the original staging failure or confuse its root with the active
`-v2` production root.

## Qualification evidence

All three sacrificial pilots at K16384/32768 passed 72 unchanged comparisons,
including separate half-grid checks. The parent and an independent scientific
reviewer recomputed the numerical metrics and reconciled profile, bank, seed
and sidecar hashes. Maximum profile LR movement was 0.347584 against 0.5;
maximum half-grid gain was 0.159472 log-likelihood units against 0.25.
Connected and corridor reach the permitted one-cell effect-MLE movement.
See [qualification review](qualification-review.md) and the compact
[qualification check](qualification-check.json).

The completed qualification root is
`/data/codex/scratch/goal046-qualification-20260908-k16384/`, mirrored at
`artifacts/goal046_execution/qualification16384/`. Its three `exit_code` files
and `batch_exit_code` are zero. All reports and diagnostic arrays are returned.
Its immutable 74-file source snapshot SHA256 remains
`b0abe1985f0df19417182cb75311b6ae86165d48c0e7f75f48e227b89e125318`.
Post-qualification source changes only add production admission, saved-reference
review and synthesis provenance; generative and likelihood mathematics,
landscapes and sampling are unchanged.

## What follows

The current execution and diagnostic work is complete. Keep the heartbeat
paused and preserve all original failed comparisons and remote receipts.
The final production evidence does not support the intended ecological
sampling-design synthesis under its frozen numerical rule.

The [independent review](split-bank-diagnostic-review.md) recommends a new,
separately registered integration-validation study, because landscape/sampling
generality remains a Paper 1 pillar. Its scientific design would separate
bank-realization variation from pseudocount-weight sensitivity, include
prospective controls alongside the known stress cases, and test the calibrated
width functional with an explicit accuracy or stability reference. This is a
recommendation for Barry's scientific review, not an approved new experiment.
Closing Arc 3 as numerically unresolved is the alternative programme decision.
No bank increase, criterion relaxation, map omission, ecological synthesis,
commit, push or publication is authorized by the completed diagnosis.
