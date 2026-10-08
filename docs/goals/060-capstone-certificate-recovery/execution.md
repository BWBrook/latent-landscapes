# Goal 060 execution record

5 October 2026, Hobart. **Public qualification is complete. The recovered
certificate, producer gates, repaired full independent audit and public sealer
preflight all passed. Real sealing remains unexecuted.**

The [approved registration](registration-2026-10-04.md) fixes the 1,024-interval
certificate on Goal 059 candidate 0. Recovery copies all original accepted
artifacts and preserves its negative metadata. The original 240 Python source,
script and test files match their Goal 059 freeze; the implementation adds a
recovery layer, an independent audit layer and a sealing script. The
[predecessor bindings](../../../artifacts/goal060_execution/predecessor-bindings.json)
cover all 87 Goal 059 artifact and goal-document files present before this work.

The public execution directory is
`/data/codex/scratch/goal060-capstone-recovery-20261004` on `deep-server-ts`.
It has a separate source checkout and environment. The locked numerical runtime
is Python 3.14.5, NumPy 2.5.1, SciPy 1.18.0 and PCG64 on Linux. Mac development
checks showed exposure differences below 9e-16 relative to the frozen Linux
map; exact replay remains a Linux requirement, and the identity check was not
weakened. Two local recovery integration tests consequently defer to Linux.

The frozen driver first runs the targeted tests, Ruff, mypy, exact recovery and
independent fixed-map audit, then a 64-history mechanical bank at root 987654321.
Its successful receipt is required before the registered run can start. The
run copies that qualified recovery, independently rechecks it, binds the
unchanged confirmatory address rule, builds the 131,072-history public bank,
and applies the unchanged mechanical and eight-fixture public gates. Every
stored main, profile and coarse-grid point is checked by the independent
direct-bank audit. The readiness receipt remains negative unless all gates
pass.

The one-attempt supervisor preserves the original 30-minute qualification and
four-hour public-run bounds, a 64 GiB sampled aggregate-RSS cap, at most 32 bank
workers and 16 fitting workers, and one numerical-library thread per process.
It verifies the source, driver, supervisor and runtime hashes before each
phase, refuses an existing attempt receipt and checks for remaining workers.

The sealing script is included for Fable's later leak review. Its public
preflight is separate from the explicit `seal` command. Mechanical tests may
use disposable encryption keys and root 987654321; no real private root,
production sealed history or Barry private identity is used in this goal.
Ciphertext-size padding and generic private-section error handling are part
of the pre-freeze leak review.

A development review exceeded the mechanical-root restriction while exploring
archive-size coverage. It scanned truth selections at integer roots 1..294,
selected the first occurrence of each of 16 background-branch patterns, and
generated 64 test histories on the root-987654321 mechanical map. The selected
root subset was not persisted. The histories and 32 tar archives stayed in
memory; no bank, fit, registered public draw, private entropy or Barry key was
used. This was a test-scope deviation and those results are excluded from
qualification. The [development receipt](../../../artifacts/goal060_execution/development-review/deviation.json)
preserves the range, selection algorithm, aggregate output and command text.
The review was stopped without replay. Fixed-shape size bounds and the frozen
root-987654321 tests supply the permitted padding checks.

The final independent review accepted the package for target qualification at
22:28 AEDT on 4 October. The frozen archive contains 303 files and is
44,580,505 bytes:

- Source manifest: `21351e3be65091a8db9b4d3c50efb129faaa0c51419294fe6b114d9e765c1833`.
- Source archive: `6c78cdbc37ab0dcef8ac98b39b0e02c87e008f3d1b37bf8742c11520c4e9ef1e`.
- Runtime: `77153eb0a977749e4ba95d9cae33c1f6d31457bdc2cc2d91d2358cede7ec88e1`.

Parent integration checks passed 25 tests with three deferred exact Linux
replay checks. Ruff, mypy and driver syntax checks passed. The source archive
includes the independent review and development-test deviation; the excluded
exploration is not executed by the driver.

Target qualification ran from 22:30:05 AEDT for 213.625 seconds and finished
with exit 0, no resource stop and no remaining worker processes. All 306 tests
passed on Linux, followed by Ruff, mypy, exact map/exposure replay, independent
certificate reproduction at `4.928543927785195`, and the 64-history mechanical
qualification. Sampled peak group RSS was 533,884,928 bytes (0.497 GiB).
The [qualification receipt](../../../artifacts/goal060_execution/qualify-attempt.json)
binds the unchanged source manifest.

The registered run finished at 22:55:55 AEDT after 1,257.562 seconds, with exit
0 through its explicit negative branch, no resource stop and no remaining
workers. Sampled peak RSS was 5,581,811,712 bytes (5.20 GiB). The bank completed
all 131,072 histories; mechanical qualification passed; all eight public
fixtures were generated; all 24 fit/profile tasks, three coarse grids and all
producer stability gates passed. The independent audit then stopped before
direct scoring because the wrapper omitted the bank manifest's derived file
hash from an exact object comparison. The
[independent diagnosis](independent-review.md) establishes the precise mismatch
and limits of the producer's result. Original readiness remains false.

All 658 returned artifact hashes, 303 frozen archive members and 87 preserved
Goal 059 files passed the [closure check](../../../artifacts/goal060_execution/completed-check.json).
The original source, outputs, failed audit and negative readiness stay intact.

The [audit-interface repair](audit-interface-repair-2026-10-04.md) adds a small
adapter while retaining every old source file and every scientific predicate.
Its [independent review](audit-repair-review.md) and eight focused tests passed.
Parent integration checks passed 13 tests with one Linux-only replay deferred.
The separate target package is
`/data/codex/scratch/goal060-capstone-recovery-20261004-audit-repair`.
Its 603 copied input/evidence files match their bindings. The new freeze has
321 files, including all 303 original source files unchanged:

- Source manifest: `9ee6aad80f0cf132a54a59e7b030c58459008d517ecb31b54d0f3200f9dbd0de`.
- Source archive: `0f1808d60bd3d04a0312892bc6edf5d305fa3500e3090dbe487b43a4ce2384f5`.
- Runtime: unchanged `77153eb0a977749e4ba95d9cae33c1f6d31457bdc2cc2d91d2358cede7ec88e1`.

Repair target qualification started at 23:12:24 AEDT on 4 October and passed
all 14 relevant tests, Ruff and mypy in 20.847 seconds, with no remaining
workers. The audit-only run started at 23:13:28 AEDT and finished at
**00:09:24 AEDT on 5 October**, after 3,355.807 seconds. It exited 0, with no
resource stop or remaining processes; sampled peak aggregate RSS was
626,774,016 bytes (0.584 GiB).

The repaired full audit passed every registered predicate, including all 24
task rows, direct main/profile and held-out scores, all three 1,350-point coarse
grids and all eight full/half-bank stability reconstructions. Its largest
coarse-grid score discrepancy was `1.1368683772161603e-11`, below the unchanged
`1e-8` tolerance. The unchanged sealer's public preflight passed in 3.591
seconds, without drawing a private history root. The new readiness receipt is
positive; the original negative receipt remains unchanged.

Final bindings are:

- Independent audit: `30e9f5ac8f9cbf6cb47a21c3370dadc0fdda200979ad024ba5636bef12b0242b`.
- Positive readiness: `e42501fcb5cc438c1706d6e32352f17b22969b89811d3f3114809bd2802b64a2`.
- Returned repair manifest: `bbbb5c1ecea42077644af5d306795ee0abb0ea30b2028e166eb92517b1a9de24`.

The [final completion check](../../../artifacts/goal060_execution/audit-repair/completed-check.json)
verified 637 returned repair files, 603 copied inputs, all 321 repair archive
members, all 303 original source files, all 658 original returned files and all
87 preserved Goal 059 files. The confirmatory contract differs only in its new
source-manifest binding; every address, runtime and registration field remains
identical.

Combined target qualification used 234.472 seconds. Combined original public
construction and repaired audit used 4,613.369 seconds (76.89 minutes), within
the original 30-minute and four-hour limits respectively. No scientific bank,
fixture or fit was regenerated or replaced during the repair. No real private
root, sealed history, confirmatory reference campaign, private-key read,
commit, push or publication occurred. Fable's final leak review and the
[sealing handoff](sealing-handoff.md) are next.
