# Goal 046: final uniform K65536/131072 comparison

Approved continuation, 10 September 2026 (Hobart). Barry authorized extending
the deadline at the agent's discretion and delegated routine approval judgments
within this programme. This advances the same Arc 3 landscape-and-sampling
question and its existing numerical acceptance requirements.

The original proposed extension date is almost past at restart. The fresh
bounded window is **2026-09-09 23:00 UTC to 2026-09-11 05:00 UTC** (11 September,
3 pm Hobart), allowing 30 hours for the final comparison, artifact return and
review. Exact authority is recorded in [compute-authority.json](compute-authority.json);
the original record is retained as [compute-authority-initial.json](compute-authority-initial.json).
This changes the available time, not the scientific criteria or bank ceiling.

## Completed predecessor and remaining work

All nine K32768/65536 map calculations finished under the original deadline.
Four ensemble reports fail: barrier 2026090811, connected 2026090812 and
2026090813, and corridor 2026090812. Five pass. All nine separate selected-
K32768 half-grid reports pass. The original batch exit is 1, matching the
numerical failures. All nine bundles and adoption receipts are now returned and independently
verified, including actual nested banks, complete seeds, original/new freezes,
source manifests and exact replay of every ensemble metric. All 216 half-grid
comparison rows reproduce exactly; saved and replayed surfaces and retained
grid nodes agree exactly. See the [ensemble check](k32768-ensemble-check.json)
and [half-grid check](k32768-halfgrid-check.json).

The slowest K65536 campaign took 28103 seconds (7.81 hours). Its bank plus
integration took 25236 seconds and history evaluation 2866 seconds; linear
scaling gives approximately 14.8 hours for K131072. The completed selected-
K32768 half-grid checks took 2.81–3.25 hours, suggesting approximately 5.6–6.5
hours at K65536. Thus roughly 21–23 hours of calculation plus setup, transfer,
verification and scientific review motivates the 30-hour window. These are
planning estimates. Only completed, verified numerical reports can qualify
scientific evidence.

## Frozen continuation

Use K65536 selected and K131072 reference uniformly on all nine maps. The
[new freeze](production-freeze-k65536.json) differs from the K32768 freeze only
in its two bank sizes. Retain the original 82-file campaign source unchanged.
Reuse each immutable completed K65536 reference as the selected input, through
a new separate adoption receipt binding the old and new freezes, source roots,
all bundle hashes, seeds and actual nested banks. Do not rewrite original
campaign receipts or regenerate the K65536 campaign.

Compute each K131072 reference, then run its adoption-aware full-ensemble
comparison and the complete selected-K65536 replay plus separate rho/effect
half-grid checks. Both numerical reviews run even when the first reports a
failure. All nine maps must qualify at this same final pair before synthesis.
Selected inputs for synthesis will be the predecessor's K65536 reference
bundles, not the newly computed K131072 references.

Retain at most nine active map calculations, four workers per map, native
library threads one, aggregate RSS below 96 GiB and the checked 10 GiB address-
space cap per map. All predecessor processes have exited. The new launcher
uses a duplicate-launch guard and the remaining time to the single deadline,
with a process-group timeout and memory watchdog. Stage and test the exact
source/review/dispatch snapshot and obtain an independent dispatch check before
launch.

The final bank ceiling remains K65536/131072. Preserve any further failure as
numerical uncertainty; do not alter the estimand, map ensemble, comparisons or
criteria to obtain acceptance. Publication, commits, pushes, cloud resizing and
sibling-project modifications remain outside scope.

The completion heartbeat used a four-hour cadence through completion, within Barry's
requested three-to-five-hour range. Adapt that cadence only when an approaching
completion or decision makes a closer check useful. Continue approved technical
work autonomously and report a consequential scientific boundary if one arises.

## Verified dispatch

Launched 2026-09-09 23:12:16 UTC under
`/data/codex/scratch/goal046-production-20260910-k65536/`, timeout PID/group
58695, with 107264 seconds remaining. All nine K131072 campaigns were observed
active at startup, with four workers and checked native-thread/address-space
limits. The Linux preflight passed all 19 focused tests in 51.52 seconds;
parent and independent reviewer reconciled the exact 82 campaign and 11
review/dispatch files and cleared launch after repairing a prelaunch receipt
race. See [execution state](execution-state.md) for exact hashes and receipts.
At dispatch the completion automation was active with a four-hour interval.

## Final ensemble result and bounded diagnosis

All nine K131072 references are complete. Independent return verification
reconciles source/freezes, adoption receipts, seeds, nested banks and exact
ensemble metric replay. Five maps pass and four fail the unchanged criteria;
see [the numerical diagnosis](final-bank-diagnosis.md) and
[independent review](final-bank-diagnosis-review.md). The final bank pair is
rejected and ecological synthesis remains blocked.

All nine half-grid reviews are complete and independently verified, with
213 of 216 comparison rows passing; three repeat the known corridor tail
failure. All separate grid refinements pass. The [bounded bank-half diagnosis](split-bank-diagnostic-results.md)
also completed successfully in 35.6 minutes and is independently verified and
reviewed. The final pair remains rejected. The completion heartbeat is paused
at the scientific integration/validation design decision; no further run is
queued or authorized by this completed amendment.
