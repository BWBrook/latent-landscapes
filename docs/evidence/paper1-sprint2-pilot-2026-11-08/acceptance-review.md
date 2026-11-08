# Historical compute-node pilot acceptance review

Predeclared on 2026-11-07 before the two target fits start. Scope: numerical
portability and resource measurement for the Sprint 2 historical pilot, using
clean source `99af5206b6a4e53f5b8e9d71cbf348f95e9ae574`, lean search, tight replay
and one numerical thread. This advances the roadmap's procedure-qualification
entry gate; it is not itself fresh qualification or training evidence.

**Accepted as a practical minimum pilot comparison**, subject to the checks
below. Both cases must pass independently; a missing check is indeterminate,
not passing. Preserve disagreements and investigate them before expansion.

## Cases and reference identity

- `cell-00-rep-005-arm-B`, 120 sites: compare with
  `artifacts/sprint2/entry-replay-20261106/cell-00-rep-005-arm-B/receipt.json`
  and its hashed child search receipt. The local source was dirty `583c1e3`
  plus the exact preserved `diagnostic-source.patch`, not clean `99af520`.
  The independent provenance audit in
  `docs/evidence/paper1-sprint2-2026-11-06/design-entry-review.md` reconstructs
  all 115 source hashes and limits the later `fit_dataset.py` differences to
  serialization, required-input metadata and type annotations. This supports
  numerical-procedure equivalence, not identical source bytes. Keep the base,
  patch hash and complete source inventory with the comparison.
- `connected-0-arm-C`, 260 sites: compare with the parent-selected local
  `99af520` replay already running. Freeze its output path and receipt hashes
  when complete. Its outcome has not been inspected for this review. Missing
  or failed reference completion prevents a passing cross-host comparison.

The older `48de534` receipts in `historical-pilot-inputs.json` remain historical
cost/context baselines. They do not replace these candidate-procedure numerical
references because optimizer eligibility changed after that commit.

## Minimum numerical checks

For spatial standard, spatial tight, exposure and constant separately:

1. Require complete, hash-verified parent/child receipts, matching five data
   hashes and recorded search settings. Verify the target source against the
   frozen candidate, and record the runtime/image, lock, interpreter, numerical
   libraries, host and thread settings. Preserve original receipts unchanged.
2. Require `resolved` on both hosts, all families available, and all eight
   cutoff sets available: 2.71, 3.84, 5.02, 6.63, 7.88, 9.55, 12 and 15.
   Require consistent failure/trigger classifications, latent-multimodality
   flag and bound-contact diagnostics. Compare free-fit contacts and contacts
   at shared exact nodes; report aggregate contacts over the remaining nodes.
   Any new trigger, unresolved envelope guard or unexplained contact mismatch
   is nonpassing pending diagnosis. Numerical event counts need not be equal.
3. At every exactly shared recorded h node, compare
   `W(h) = 2 * (recorded free maximum - recorded profile criterion)` using each
   host's own frozen envelope. Require maximum absolute W difference <= 0.01.
   Include h=1 and the shared fixed search mesh, and report the identities and
   counts of compared nodes for every family/regime. Missing expected fixed
   mesh evidence or an empty comparison is indeterminate. Do not round h to
   create matches, interpolate, refit or silently update either envelope.
4. Compare the complete eight level sets: root count and ordered roots,
   connected-component count/order, boundary truncation and endpoint types.
   Require identical topology and absolute log-h difference <= 0.005 for
   every corresponding finite root and component endpoint. A topology change
   is nonpassing even if two nearby roots might be interpreted as a tangency.
5. Report both mesh sizes and local-only/target-only node counts and ranges,
   plus free/null criterion differences and free h values. Adaptive meshes
   can differ because of floating-point branching; mesh equality and identical
   optimizer paths are not required. Unshared nodes are explicitly untested
   pointwise. The complete level-set check still applies.

The shared-node comparison is a bounded portability check. It is not the
exact-union anchor audit required for fresh qualification, does not establish
agreement between shared nodes, and does not prove a global optimum or exact
marginal likelihood. Existing diagnostic tie/contact rules remain unchanged.

## Resources and disposition

Record total/stage wall and CPU time, peak RSS, scheduler allocation/exit state,
and numerical work counts for each attempt. Assess whether the requested
allocation completed both full fits and derive a conservative next allocation
from observed use; no cross-host speed ratio is an acceptance threshold.
Local timings can reflect concurrency and different libraries. A successful
scheduler exit without complete valid receipts is insufficient.

Keep scientific failure distinct from execution failure. An execution retry
retains the same inputs/source/settings, uses a new attempt directory, and
preserves the failed attempt. Do not retune scientific settings to pass this
pilot. Any needed procedural amendment is recorded and reviewed before use.

Passing permits the planned historical pilot/replay progression under the
parent's existing authority. It does not approve fresh-panel qualification,
rule training, validation access or scientific claims beyond these two cases.
This review writes only this ignored note; it runs no fits or remote commands
and changes no source files.
