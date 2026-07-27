# Goal 009: Platform-Stable Cross-Truth Recovery

## Objective

Recover the unanswered Goal 008 cross-truth perfect-detection benchmark by
replacing a platform-brittle continuity check with a scientifically equivalent
comparison and by preserving useful diagnostics whenever a hard invariant
blocks acceptance.

Goal 009 does not alter the scientific experiment. It changes only:

1. how the accepted Goal 007 central result is reconciled across computing
   platforms; and
2. what evidence is retained when a completed campaign is classified
   `implementation_blocked`.

## Motivation And Observed Failure

The first Goal 008 production attempt used verified source commit
`9a21469b73b4c0e82a4f7e716909fed7a50c1f40` on `deep-server`. All nine worker
processes returned after 50 minutes 44 seconds, but the aggregate result was
`implementation_blocked`. The CLI correctly suppressed the scientific review
pack.

Post-run probes established that all frozen-source and inherited fixed-input
invariants were true. The blocked result, cell invariant maps, and central
observed values existed only in memory and were discarded, so the exact failed
invariant cannot now be recovered.

The leading diagnosis is a bit-exact central-projection mismatch between the
accepted Goal 007 calculation on the Apple Silicon Mac and the Goal 008
calculation on x86-64 Linux. This is an inference, not an observed fact. A
genuine cell-level invariant failure remains possible.

## Frozen Scientific Contract

Retain Goal 008 unchanged at source commit
`9a21469b73b4c0e82a4f7e716909fed7a50c1f40`, including:

- the 3 by 3 truth grid and its row-major order;
- 500 independent calibration and 500 independent validation shock blocks;
- paired counterfactual truth cells within each block;
- the 4,096-draw integration bank and two disjoint 2,048-draw halves;
- the candidate rho and eta grids;
- all observation, likelihood, support, neutral, prediction, and local-cutoff
  definitions;
- all topology, calibration, precision, predictive, bank-stability, and
  worst-cell decision rules; and
- the nine-process, single-threaded `deep-server` production layout.

Do not change a seed, truth, bank, grid, cutoff, tolerance used by the
likelihood itself, scientific threshold, class, precedence rule, observation,
or model component.

## Platform-Stable Central Reconciliation

The central `(rho, eta) = (1, 1)` result must still reconcile to independently
accepted Goal 007 evidence. Separate two concepts:

1. **Structural continuity**, which remains exact.
2. **Floating-point continuity**, which must be stable across supported
   platforms while remaining far tighter than any scientific decision
   threshold.

Require exact equality for:

- row order and row identity;
- phase, dataset index, and bank label;
- all counts, booleans, category strings, indices, support sets, MLE sets,
  reasons, and class labels;
- seed and source identities; and
- the central outcome.

For continuity projection fields that are finite floating-point values,
canonicalize to nine digits after the decimal point, normalize negative zero
to zero, then compute deterministic projection hashes. Reject non-finite
values before canonicalization.

Nine-decimal canonicalization is an implementation-continuity tolerance, not a
scientific uncertainty tolerance. It is several orders of magnitude tighter
than the Goal 008 likelihood-ratio cutoffs and decision bounds.

Derive the expected canonical hashes independently from the accepted Goal 007
artifact tables. Hard-code those reviewed constants. Do not create a runtime
dependency on ignored artifacts and do not establish compatibility by
comparing two calls through the same Goal 008 path.

Retain the raw, bit-exact observed hashes as audit evidence, but do not use
cross-platform raw hash equality as an acceptance gate. Record:

- raw observed and historical hashes;
- canonical observed and expected hashes;
- exact structural checks;
- canonical numerical checks; and
- the canonicalization rule.

Tests must show that:

- exact replay passes;
- a one-ULP finite perturbation remains compatible;
- a material `1e-6` perturbation fails;
- a discrete or structural change fails; and
- NaN or infinity fails.

## Blocked Diagnostic Contract

If a completed campaign is `implementation_blocked`, write exactly three
ignored quarantine files under:

```text
artifacts/goal009_cross_truth_blocked_diagnostics/
```

Required files:

- `diagnostics.json`
- `compute_provenance.json`
- `verification.json`

The diagnostic bundle is explicitly non-accepted evidence. It must contain:

- all campaign invariants and the names of false invariants;
- every truth cell's invariant map and false-invariant names;
- central observed, expected, raw-hash, canonical-hash, and check fields;
- the complete 27-row cell-by-bank class and decision-metric surface;
- campaign and per-cell execution telemetry;
- source identity and campaign digest;
- the stated reason no scientific review pack was accepted; and
- explicit encoding and field paths for any non-finite values.

Diagnostic JSON must remain valid strict JSON. Encode non-finite values as
explicit tagged strings rather than emitting NaN or infinity tokens.

The same trusted production provenance gate used by Goal 008 applies to the
diagnostic bundle. Hash both payload files in `verification.json`. Refuse stale
diagnostic directories.

If the campaign is not blocked, write the existing exact 16-file Goal 008
review pack and do not write a quarantine diagnostic bundle.

## Production And Review

Use the Mac mini for test-first development and local validation. Create one
clean pre-production Goal 009 feature commit descended from Goal 008 commit
`9a21469`.

Transfer a verified Git bundle to `deep-server-ts`. Require exact commit and
lockfile hashes, clean detached source, focused tests, a nine-worker miniature
smoke, runtime identifiers, and all four numerical-library thread limits set
to `1`.

Run the unchanged production campaign once with nine isolated workers. Do not
rerun within Goal 009.

If a scientific review pack is produced:

- return it and all remote logs with recursive checksums;
- independently recompute every cell and overall class;
- inspect all four SVGs once; and
- obtain one independent final scientific/code/artifact review.

If a diagnostic bundle is produced:

- return it and all remote logs with recursive checksums;
- identify the exact failed invariant from persisted evidence;
- obtain one independent diagnostic review; and
- close without another campaign.

## Completion And Stop Rules

Goal 009 succeeds scientifically if the unchanged campaign produces a trusted
Goal 008 review pack and a reviewable completed scientific class.

Goal 009 succeeds diagnostically if a blocked campaign produces the complete
trusted three-file diagnostic bundle and therefore converts the previous
opaque block into a specific actionable finding.

Perform one focused local self-review and at most one material implementation
repair before production. After production, do not change reconciliation,
scientific logic, or diagnostics and do not rerun.

Do not begin imperfect detection, prey dynamics, model selection, landscape
changes, a new likelihood, Goal 010, or any scientific retuning.

## Authority

Implementation, local validation, one pre-production Goal 009 feature commit,
one bounded `deep-server-ts` campaign, checksummed evidence return, and one
post-run documentation commit are authorized on
`codex/latent-landscapes-goal009-portable-cross-truth-recovery`.

After orchestrator review and one independent final review, publication of
either:

- an accepted scientific cross-truth result; or
- a complete accepted diagnostic result

is authorized. Publication includes the unpublished Goal 008 parent commit.
Stage exact source, tests, scripts, goal packets, and programme documentation
only. Generated artifacts, remote logs, build outputs, and quarantine
diagnostics remain ignored and unstaged.

Do not force, reset, clean, rebase, delete remote evidence, expose services, or
stage unrelated files.
