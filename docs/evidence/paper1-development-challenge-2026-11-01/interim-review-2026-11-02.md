# Independent interim review — 2 November 2026

Reviewer: Codex independent receipt-review subagent. Scope: three completed
B0 profile jobs and the first fixed-outer importance screen, copied under
`artifacts/paper1_development_challenge_20261101/wakeup-20261102/`.
**57 of 60 profile jobs were still pending in the inspected campaign snapshot.**
This is not an aggregate panel result. No scientific sources, thresholds,
running jobs or fitted results were changed during this review.

## Profile findings

`cell-00-rep-005-arm-A-B0` has individually resolved dense and lean searches,
but their frozen comparison correctly remains `failed`. Across common
points, maximum absolute W disagreement is 1.81899e-12; the absolute
log-root difference is 1.06483e-10. Both diagnostic sets extend from the
lower domain boundary h=1 to approximately h=2.454518552.

The failure is confined to nuisance-contact labels at h=2.4540858705193496,
2.454518551893358 and 2.454518552154722, all inside or numerically on the
3.84 set boundary. Dense positive-family fits have log_sigma exactly
-9.210340371976182 (sigma=0.0001), labelled `log_sigma:lower`. Lean fits
have sigma approximately 0.000100001946588, 0.000100000988576 and
0.000100000988575, respectively, outside the approximately 9.21e-8
log-coordinate contact tolerance. The exact-zero family has no nuisance
contacts in either search and exceeds the positive-family criterion by
only about 1.33e-8. Both families therefore count as owners under the
frozen 1e-4 criterion-tie rule. The implemented comparison requires contact
agreement for every common owner, so the strict categorical gate fails.
This is not evidence of materially different W curves or root locations;
those agreements can be reported separately without relabelling the gate.

Both arm-B jobs are `indeterminate` in both search modes. Each retained
evaluation stream contains an `unresolved_fit` event. Independently
subtracting the best eligible same-family criterion gives these largest
unresolved positive-family excesses:

| Dataset | Search | h at failure | Maximum criterion excess |
|---|---|---:|---:|
| cell-00-rep-005-arm-B | dense | 24.5601926535 | 5.1710022271 |
| cell-00-rep-005-arm-B | lean | 30 | 5.9988855557 |
| cell-06-rep-006-arm-B | dense | 27.1441665852 | 2.4298422609 |
| cell-06-rep-006-arm-B | lean | 30 | 0.9281220034 |

These are **ineligible candidate values**, not feasible optimized
alternatives or established profile maxima. Their outer projected-gradient
residuals are far above tolerance despite optimizer success flags.
The frozen superior-unresolved-candidate safeguard therefore prevents
qualification. Neither job has a qualified free fit or tight profile;
their retained standard-point counts are 32/4 and 33/4 (dense/lean).
These cases cannot yet support an A–B interval or ridge comparison.

## First fixed-outer screen

`cell-00-rep-005-arm-A` correctly records `pointwise_screen_passed` after
16,384 to 32,768 draws per point per stream. Both independent streams and
the draw doubling satisfy the frozen checks. The intended anchors are the
free reference, h=1 (combining null, generating h and both dense family-free
locations), and the dense tight root h=2.454518552154722. No topology-only
locations were included.

Independent arithmetic from retained batch log integrals reproduced the
integral estimates, Bonferroni t bounds, maximum-with-zero envelopes and
centred W contrasts exactly. The multiplier is 3 fitted targets × 2 streams
× 5 looks = 30. At the final draw level, maximum contrast uncertainty radii
are 0.0054310016 and 0.0063295448; both streams' intervals lie wholly inside
[-0.10, 0.10]. The root correction estimate is approximately 2.0091e-9;
the h=1 correction is approximately -9.09e-13. Conservative envelope
intervals, rather than nearly cancelling paired errors, control the decision.

Final minimum ESS is 26,823.86, minimum relative ESS is 0.818599, and maximum
normalized contribution is 3.79371e-5. Every pooled Pareto estimate is below
0.5 (final range approximately -1.89714 to -1.73876), and all sixteen batch
tail fits per target and stream are available. Variance-family ownership
remains unresolved, as permitted by the conservative envelope rule; no
material ownership reversal is established.

This pointwise pass does not overturn the separate contact-gate failure,
qualify reoptimized marginal roots, establish global topology or calibration,
or establish panel readiness.

## Provenance checks and snapshot hashes

All six profile-child hashes match their parent bindings. All four copied
B evaluation-stream hashes match their child receipts. All 111 Python
source bindings per profile parent match local source bytes. All 120
importance-screen source/input/profile/started bindings match the local
copies or corresponding repository files after mapping the remote checkout
prefix. The original profile `started.json` also agrees with the parent
source bindings and records reporting h=1. No failed hash check remains.

Paths below are relative to the copied snapshot directory named above.

| Path | SHA256 |
|---|---|
| profiles/cell-00-rep-005-arm-A-B0/receipt.json | `85fe066b165f376b97f7f310a8602464af04831e9bf44b5fdf4e2380578ea542` |
| profiles/cell-00-rep-005-arm-A-B0/started.json | `2b50501115f548831a12daa059647c748ea1a79ed7fb7bdbd88482be132ba92d` |
| profiles/cell-00-rep-005-arm-A-B0/dense/receipt.json | `18d34ad5bfda278591d52a6c6682175ef8e33f9e00916ebb1ecbb2b2e579ca99` |
| profiles/cell-00-rep-005-arm-A-B0/lean/receipt.json | `e2d1eb4cec0694946c1392b17ed4ab01c2d09f28460b525dac8db920842da2a4` |
| profiles/cell-00-rep-005-arm-B-B0/receipt.json | `6d77d92f1da1a33ed165b4e6ad46dd568925c5d2f94827f52fd7ec85b0a1f6d9` |
| profiles/cell-00-rep-005-arm-B-B0/dense/receipt.json | `c7bb6fe6490524bcc6ee354b678d4d53080d8570b25f53c14a056e62a102b0e9` |
| profiles/cell-00-rep-005-arm-B-B0/lean/receipt.json | `d247fe3f8c6c168bda140609110a5104db26005a7e3848506531022c6898d2ba` |
| profiles/cell-00-rep-005-arm-B-B0/dense/evaluations.jsonl | `685447d45144c47fbefb911c50b7d76f3c16359f5c58552f86d165d9625a312e` |
| profiles/cell-00-rep-005-arm-B-B0/lean/evaluations.jsonl | `aa251995d774aedef765988fc7ece8bb4fb21dceeecba408b3a00481467f0254` |
| profiles/cell-06-rep-006-arm-B-B0/receipt.json | `445f9785bb1e2ab4aa983be1c04d0f4f4010c4a92d523d5e54bb672e5d2aa836` |
| profiles/cell-06-rep-006-arm-B-B0/dense/receipt.json | `bbfa0d996674685c105a58cba083f649a9fb6b1e3ae97e1b206e6a0d82ad0e5b` |
| profiles/cell-06-rep-006-arm-B-B0/lean/receipt.json | `2be86f99d211b26d964b2e95e417a7b0ee4c46d8793a8d03a80dc2c21f439fb3` |
| profiles/cell-06-rep-006-arm-B-B0/dense/evaluations.jsonl | `31c00a5cded983bf79472ebd052c8f51badca85db96b62611a2726d7d6f67178` |
| profiles/cell-06-rep-006-arm-B-B0/lean/evaluations.jsonl | `478df886e4dc49241b092a47545d687330ce108a1c639b9d609503dad48c5233` |
| importance/cell-00-rep-005-arm-A/receipt.json | `120a71dc5fea91efa7fc4ff64012349b43f64330836716f921bb0bb17083f478` |

## Continuation bookkeeping acceptance

Accepted `continue_diagnostics.py` at SHA256
`35b53bf3cbdf39a5c60b27e5c8d3c84e22a6a165180cdd6897e7c8c55056e6cc`.
The parent independently confirmed that its archived source snapshot is
byte-identical. Review used the actual downloaded initial twelve-job,
remaining forty-eight-job and initial-screen manifests and terminal receipt,
not only idealized fixtures. The two profile manifests exactly partition
all sixty jobs and preserve their commands, input hashes, output paths and
frozen-panel binding.

Independent scratch checks passed for the original relative initial-screen
`--profile` path versus the builder's absolute path, skipping that completed
screen exactly once, and allowing the forty-eight-job batch/controller to
finish before the initial twelve-job batch. Original ledger commands and
manifest hashes remain checked exactly; path normalization is confined to
the initial/full screen identity comparison. A real invocation of the finite
executor with an empty manifest produced a valid empty terminal ledger in
temporary storage, confirming empty remaining-screen/comparison handling.
No scientific subprocess was launched by these checks.

The separate `jobs-summary.json` binds the unchanged execution-manifest hash
and preserves every original job field. Its only added per-job fields are
`site_count`, `observations_sha256` and, for archived cases,
`source_observations_sha256`; observation hashes agree with execution input
bindings. Controller completion remains execution bookkeeping, not scientific
acceptance. No remaining blocker was found within this bounded review.
