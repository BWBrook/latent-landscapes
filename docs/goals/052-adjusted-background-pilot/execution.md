# Goal 052 execution

24 September 2026. Barry approved the adjusted-background pilot and delegated
resource/timing decisions. Scientific scope is frozen in the
[registration](registration-2026-09-24.md); Goal 051 remains closed and its
nominee unconfirmed. **The pilot and result review are complete.** The
[synthesis](synthesis.md) closes this retrospective tranche; the
[prospective comparison](prospective-comparison-proposal.md) awaits scientific
critique and approval. The chronological execution record follows.

## Initial state

The inherited repository is dirty with the previous uncommitted research
tranches. Existing source and evidence are preserved. The original Goal 051
registration, synthesis, review and confirmation proposal remain hash-bound
historical records. New code is confined to the adjusted-background modules,
entrypoint and targeted tests.

Deep-server-ts was reachable at 2026-09-24 03:10:54 UTC, load 0.08 with about
123 GiB RAM available and no scientific compute active. The Goal 051 archive
and K131072 bank remain on the same host. Planned run root:
`/data/codex/scratch/goal052-adjusted-background-20260924`.

The proposed four-hour limit is now an initial operational target, because
Barry explicitly delegated resources and timing. It does not authorize
changing the model family, 24-history panel, bank or scientific conclusions.
Numerical controls and measured qualification remain required.

Implementation and independent review are underway. No adjusted fits have
been launched. No Fable or Barry response is currently required.

## Implementation qualification

The new site-specific likelihood factors the same empirical-plus-pseudo
arrival mixture exactly by category, retaining alpha=1. It shares each beta
row across the panel and changes no frozen likelihood/generator source.
Oracle prey scores use a separate API. Independent review found the likelihood
algebra, model symmetry and truth separation correct. The review identified
two runner repairs before launch: authenticate the original Goal 051 contract
itself before trusting its expected hashes, and make row writes atomic and
interruption-safe. Both are implemented with targeted failure-mode tests.

The source contract SHA256 is
`750c0735701bfdc91f4d80aa5c67dc14db50b0c1c6615261364771674caa44c4`;
all 77 relative inherited source/input hashes match locally. Independent
small-state controls cover nonzero beta, survey-boundary arrivals, beta=0,
h=1, whole-map normalization, site order and training/holdout separation.
The local combined suite currently passes 90 tests; new code/tests pass Ruff
and strict MyPy. Full-bank qualification has not yet run.

Initial remote environment provisioning failed because the source-only transfer
omitted the package README. The README was copied and the frozen uv environment
then installed successfully. This occurred before any numerical pilot run.
The environment uses Python 3.14.5, NumPy 2.5.1 and SciPy 1.18.0. Target-host
tests and final independent review precede dispatch.

Astra relayed Barry's approval on Correspondence thread 53 as message **508**.
The prior task-local retrieval checkpoint is **507**; Fable is acknowledged
through 498. No reviewer response is required for ordinary continuation.

## Qualified launch

The [independent implementation review](implementation-review.md) is **GO**.
All 90 targeted Linux checks are accounted for: 89 passed in the initial
combined run; one failed because the archive fixture was absent from the new
source checkout. Linking the existing immutable remote archive resolved that
environment issue and its remaining test passed 1/1. Both logs are retained.
No numerical assertion failed. The synthesis subset, edge flags, roundoff
thresholds and output hashes were repaired before source freeze.

Preflight at **2026-09-24 03:38:57 UTC** verified all **83** current frozen
source/test/design files, the **77** inherited relative files, the archive,
full bank, seed/site identities and absence of another Goal 052 wrapper.
The [preflight receipt](../../../artifacts/goal052_execution/preflight.json)
and [source manifest](../../../artifacts/goal052_execution/source-hashes.json)
record the bindings. Wrapper SHA256:
`d895a14e9b956dd6f474fb2d89b53827046491954c4b1516b628cf49740bca10`.

The pilot launched once at **2026-09-24 03:39:54 UTC** (13:39:54 Hobart),
wrapper PID **12028**, Python PID **12035**, initial timeout **14,400 s**,
eight workers and 32 GiB. Its first active step reconstructs the unchanged
legacy integration; every selected score must replay exactly. Eight complete
adjusted rows then qualify the new kernel and timing projection before the
remaining fixed grid. See [launch.json](../../../artifacts/goal052_execution/launch.json).
The wrapper holds the exclusive lock and records attempt-specific start,
finish and exit files under remote `attempts/`.

The quiet heartbeat **goal-052-adjusted-background-completion** is active at
15-minute intervals. It owns continuation through verified evidence, fixed
deterministic synthesis, figure inspection, independent result review,
scientific findings and a costed prospective proposal. Its source and grid
must remain unchanged while running. New calibration and prospective histories
remain outside authority. Remove the heartbeat at verified closeout or a
scientific decision requiring Barry; do not ask him about routine resources.

The full-bank controls subsequently passed: all 24 selected histories replay
exactly, and beta=0 score/LR agreement with the legacy integration is within
`1.37e-12` (tolerance `1e-10`). The eight complete timing rows took at most
47.05 s each. The [measured projection](../../../artifacts/goal052_execution/timing_projection.json)
is **2,818.74 s**, comprising 312.98 s elapsed, 705.76 s for the remaining
73 rows with a 1.5 safety factor, and the 1,800 s synthesis/verification
reserve. The runner passed this gate and continued the fixed grid. The
[replay checks](../../../artifacts/goal052_execution/replay_checks.json) and
[kernel checks](../../../artifacts/goal052_execution/beta_zero_checks.json)
are retrieved. Astra posted this operational evidence as Correspondence
thread 53 message **510**; no reviewer response is required.

## Verified completion and synthesis

The single pilot attempt exited **0 at 2026-09-24 03:52:17 UTC**, after
12 min 22 s externally timed (741.01 s inside the runner). Peak resident
memory was 2.246 GiB. There was no timeout, restart, resource amendment or
additional simulation. Wrapper/Python processes were absent and the run lock
was free when checked after completion.

The [remote completion verification](../../../artifacts/goal052_execution/completion-verification.json)
rechecked all 83 frozen current source/test/design files, 77 inherited
relative source/input files, the source manifest and launch/preflight/wrapper
bindings, original archive and complete bank identities. All **81** row files
pass their coordinate, fingerprint, schema, finite-value and checksum checks
and assemble exactly into the four saved score surfaces. The original 24 LR
profiles, holdout curves and opaque IDs also match the stored legacy evidence.
All selected replay controls passed before fitting. Maximum beta-zero error
is 1.365e-12; maximum h=1 factorization error is 1.933e-12, below 1e-10.

The first one-off completion-check helper compared raw legacy training log
scores directly with the archived LR profiles and raised an assertion. The
archive stores `2*(max(logL)-logL)`, whereas the new evidence deliberately
stores raw scores. Correcting the verification helper to compare that LR
transform gives bitwise equality. This was a verification-convention error,
not a failed likelihood control; production source and evidence were unchanged.
The corrected [helper](../../../artifacts/goal052_execution/verify-completion.py)
is retained.

The retrieved **180** run files all match the remote receipt, and local
production-source hashes match the same manifest. Evidence SHA256:
`d923a768ae60f542ac1f001da1cc7477d30861f30eb23d5e5bcd70e0421027b5`.
The existing deterministic synthesis ran **once** locally from 04:00:23 to
04:00:26 UTC, exit 0, elapsed 2.95 s. All nine output hashes pass. The
[synthesis receipt](../../../artifacts/goal052_execution/synthesis-execution.json)
binds the entrypoint, input, local runtime and summary. No random draws are
part of Goal 052 synthesis. No operational extension of the initial four-hour
target was needed.

Astra inspected all three PNG figures and the per-history, cell and geometry
tables. The independent result reviewer reconstructed fits and diagnostics
from raw arrays and found no result-level blocker, while rejecting a claim of
estimator repair. The [final review](final-review.md) and [synthesis](synthesis.md)
retain the failed oracle expectation, weak profiles, two paired beta-edge
contacts per lane and all coarse/fine flags. The direct adjusted-minus-constant
score and multiplicative-error derivations are labelled exploratory. They
generated no new histories, fits or draws.

The [next proposal](prospective-comparison-proposal.md) concerns 1,000 fresh
paired blocks in six cells, exact nonzero-beta and known-beta controls, direct
predictive comparison and limited oracle diagnostics. It is not authorized by
this closeout. New calibration, additional surveys, unknown nuisances,
commits, pushes and publication remain outside the current scope. All frozen
Goal 049–051 evidence and earlier numerical failures are preserved.

## Administrative closeout

Astra posted the result and proposed next comparison on Correspondence thread
53 as **511–512**, following the task-local catch-up through cursor 510.
Fable's critique is next, followed by Barry's scientific scope decision.
The app confirmed deletion of **goal-052-adjusted-background-completion**
at this closeout. No Goal 052 process or monitor remains active. The
[completed check](../../../artifacts/goal052_execution/completed-check.json)
binds the verified run and synthesis receipts to the final scientific records.
