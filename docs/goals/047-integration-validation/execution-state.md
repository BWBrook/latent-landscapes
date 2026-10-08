# Goal 047 execution record

12 September 2026 (Hobart). **Complete: registered Stage A rejection.**
Stage B is unrun by design; the completion heartbeat is paused. The current
integrator is pseudocount-sensitive for the connected calibrated-width
functional. See [results](results.md), [verification](completed-check.json) and
[independent terminal review](final-review.md).

## Registration and preflight

Barry approved the separate study on 11 September. Both stages were frozen at
2026-09-11 11:13:17 UTC in `registration.json`, before any study outcomes.
The seed ledger is `artifacts/goal047_execution/registered-seeds.npz`; the
registration binds its SHA256, the design and immutable-input manifests.
All 393,216 prospective bank seeds are unique and disjoint from 1,179,648
Goal 046 bank seeds. The 4,000 fresh history-stream seeds are unique and
disjoint from the prospective bank streams. These seeds were registered but
never used to generate Stage B banks or controls.

The independent pre-execution review passed the design and decision checker.
All 23 focused tests passed locally and on the target, including independent
raw-bank pseudocount formulas, the linear half-bank combination identity,
reproduction of the accepted history/likelihood helper for both maps and all
alphas, and the decision rules. Scoped Ruff passed. The launcher verified
76 staged files and all 22 immutable input hashes before dispatch.

## Completed calculation

Stage A launched at **2026-09-11 11:21:50 UTC** and finished at
**11:48:28 UTC**. The runner took 1594.921 seconds (26.58 minutes); peak
sampled aggregate RSS was 3.101 GiB. Runner and decision-check exit codes are
both zero. The two-hour timeout, four-worker ceiling, one native thread,
10 GiB address-space limit per process and 96 GiB aggregate RSS limit held.
The recorded supervisor, timeout group and runner processes are all absent.

The remote directory remains
`/data/codex/scratch/goal047-integration-validation-20260911-stagea` on
`deep-server-ts`. Runtime used the existing Goal 046 pilot environment and the
fresh, hash-bound study source. Original bank bundles and source snapshots were
read only. No fresh bank generation or replacement method implementation ran.

## Return and independent verification

The full reduced output, raw training surfaces, decision, exact staged source,
input manifests, preflight and launch receipts, exit record and logs are
returned under `artifacts/goal047_execution/`. The independent verifier is
`verify_completed_stage_a.py`; its local and remote check receipts agree exactly.
It verifies all 76 preflight files, 22 original inputs and both 82-file source
snapshots. The design and seed ledger remain unchanged.

All 18 connected LR/drop arrays reconstruct bitwise from retained raw training
likelihoods. Every numerical metric and pass/fail flag in all 16 comparison
records reconstructs exactly. Both first-half saved replays are exact; the
maximum combined replay error is 1.819e-12 against the 1e-9 limit.
An independent scientific reviewer separately reconstructed the decisive
quantities and confirmed the terminal rejection and conditional claim boundary.

Six of nine within-bank alpha comparisons fail the connected width and
boundary gates. All 27 corridor within-bank alpha case comparisons pass and
all maxima remain inside the fixed window. The registered negative branch
therefore ends the study before Stage B. Equal-K and matched-weight comparisons
are retained as contextual diagnostics, including the corridor tail failure.

## Stopping boundary

`goal-047-integration-validation-check` is paused; the older Goal 046 and Goal
045 heartbeats remain paused. Goal 047 is complete with a negative method
result, while Goal 046 retains all four failures. No ecological synthesis or
production acceptance is authorized. A reviewed integration/regularization
redesign and numerical accuracy plan would be a new scientific decision.
Current changes remain uncommitted; no push or publication occurred.
