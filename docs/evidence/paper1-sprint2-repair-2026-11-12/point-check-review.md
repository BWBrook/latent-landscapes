# Independent review of the repaired endpoint smoke

12 November 2026 · Codex (GPT-6.1 Sol). This review checks retained target
output; it makes no model runs, source changes, commits or board posts.

**The frozen endpoint and witness checks pass for candidate
`a77e849ce0b0381b5c378b222bacfadce9beaf96`.** The receipt marks complete
execution, all four derivative checks pass, all three enriched starts return
eligible fits, and the exact previously invalid witness now evaluates
successfully. These are development checks, not a full replay result or fresh
qualification. The rejected candidate and its old outcomes are unchanged.

## Identity and integrity

The independently calculated receipt SHA-256 is
`eb9fba40324461bd149592ac36d395320782681e5beb227979a7fa356fe035ed`.
Its source commit and empty tracked-change list match the frozen candidate.
All **109 recorded package/point-driver source hashes** agree with that Git
commit, and the **eight reviewed code fingerprints** in `code-review.md`
agree with the same commit. This checks the repaired bytes rather than merely
accepting a source label.

All four fixture hashes agree with the committed files: replay selection,
constant endpoints, three enriched endpoints and the exact witness plan.
The source requires these fixtures to be tracked inside the clean candidate
checkout and rechecks their hashes after execution. The selection SHA-256 is
`099f28d9a45a8a4eb12b103ddaf23714ed3ced72120bb5c9184c9c75e514dfaf`.

The eight result entries use **five unique original task records**: four
constant datasets and the shared enriched dataset. Every recorded task digest
matches the frozen selection and preserved original task mirror. All **85
input-hash bindings** across those five identities equal the original task
inventories. This local review does not rehash remote raw banks; the target
loader's verified input inventories and original bindings are retained.
The retained wrapper pins the original container hash and interpreter while
explicitly importing the repaired checkout. The parent reports PBS exit zero
and 4m30s wall time; this review does not re-query native scheduler accounting.

## Four constant endpoint derivatives

| Dataset | Repaired detection-SD gradient | Absolute error from frozen reference |
| --- | ---: | ---: |
| connected-2 window-high A | -6.86440608e-5 | 2.27891839e-8 |
| connected-2 trend A | -6.37567192e-5 | 1.35283642e-7 |
| corridor-1 b100-anchor A | -4.11064868e-5 | 1.79225218e-7 |
| barrier-1 trend A | -5.72697464e-5 | 2.84198549e-8 |

I recomputed every error from the committed reference value and checked the
fixed `5e-6` tolerance. Each successful evaluation has exactly the old
criterion at the frozen endpoint. The old diagnostic receipt hashes also
match the references. The free reduced gradient in `(alpha, detection SD)`
lies below `1e-4` in every case. Beta's reported full-model gradient is not a
free coordinate in the constant family and must not be included in that norm.
This verifies derivative accuracy at the specified endpoints; it does not
assert that all four full constant searches have already been rerun.

## Enriched starts and exact witness

The three prescribed enriched starts finish after 2, 3 and 2 outer iterations,
with projected gradients `2.73519e-5`, `1.28867e-7` and `3.05235e-5`, all below
the unchanged standard threshold `1e-3`. Every result records successful
evaluation, optimizer certification and eligibility. Their final latent modes
strictly converge in 11 iterations, with score norms below `2.76e-9` and
decrements below `6.28e-9`; bound/proposal guards pass. Each final mode records
one rejected invalid trial. Aggregate mode-call counts are 8, 12 and 8, with
zero failures and convergence histograms at 11 iterations; aggregate invalid
trial counts are 6, 10 and 6 respectively. The per-final-mode count must not be
mistaken for the aggregate count.

The exact witness likewise records successful evaluation, strict latent
convergence in 11 iterations, one invalid-trial rejection and zero mode
failures. Its recorded convergence histogram and rejection counts agree.
This directly tests the accepted rejection/damping path on the previously
invalid vector. Overflow warnings remain in the retained job log; the repair
rejects invalid proposals rather than weakening the finite-output guard.

No original qualification attempt is replaced. The 24 full non-regression
fits and exact anchor comparisons, all 27 development-fit replays, terminal
reason review and resource measurements retain their separate acceptance
requirements. No fresh panel, training or validation is opened by this smoke.

Next: Codex — run and reconcile the frozen full-fit and comparison checks.
