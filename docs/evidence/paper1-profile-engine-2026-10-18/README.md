# Profile-engine development evidence

18 October 2026. These are development diagnostics on archived, already-open
histories and outcome-free map geometry. They are not calibration or validation
results. Goal 062 remains closed.

The [development record](../../paper1-profile-engine-development-2026-10-18.md)
explains the implementation, numerical failures and next repair. The
[independent review](review.md) defines the accepted scope. The
[manifest](manifest.json) records every archived snapshot's original local
path, byte count and SHA-256, current source dependencies and the retained
large local payloads.

The principal records are:

- [120-site profile traversal](benchmark/B_H3-training120.json): 190.73 seconds,
  both free families resolved, positive variance resolved at 18/35 mesh nodes.
- [Local derivative checks](kernel/kernel-check.json), with the initial
  knot-crossing diagnostic and corrected step study retained alongside it.
- [Wider-grid canary](canary/wide-grid-canary.json) and
  [direct underflow diagnosis](canary/upper0-underflow-diagnostic.json): both
  positive fits remain unresolved; log-domain scoring is required.
- [Thirty-map capacity diagnostic](sampling/capacity-30map.json) and
  [three seeded master-panel selections](sampling/master-selector-three-map.json).
- [Focused test output](checks/final-focused-tests.txt): 151 passed.

The order-192 and order-816 banks represent the same 131,072 arrival draws.
Their preparation scripts and receipts are in `bank/`; large NPZ and NPY
payloads stay in the original local artifact directories, identified by the
manifest. The earlier order-816 receipt with incorrect upper-grid metadata is
retained as historical evidence and superseded by the corrected receipt.

Scripts in this archive are exact source snapshots. Several derive the
repository root from their original location or import another frozen
snapshot. To replay an old result, restore the listed original paths in a
separate checkout, including the exact driver and engine hashes recorded by
that receipt. Do not run a renamed archive script in place or substitute the
current driver while claiming exact source identity. Inputs must match the
receipt hashes; restored scripts reject existing result paths.

The initial benchmark used the frozen driver in `benchmark/executed-driver.py`.
The corrected kernel check and canaries use
`benchmark/kernel-canary-driver.py`; the engine is
`benchmark/executed-engine.py` in both cases. These snapshots preserve the
distinction between executed source and later reporting improvements.

All mesh receipts deliberately report `profile_certified: false`. Finite
endpoints, a small pointwise gradient, completed traversal or green tests do
not supply confidence-set topology, global-mode, tail-support, calibration or
coverage evidence.
