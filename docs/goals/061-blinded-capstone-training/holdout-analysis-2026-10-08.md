# Released holdout scoring: scope and execution

8 October 2026, Hobart. This stage advances Charter Pillar 5's predictive
model comparison in the Arc 4 capstone. It follows the completed Goal 061
training endpoint and retains its scientific design.

Barry stated: **"Holdout released, hash matches."** Claude's acceptance of the
training lock is correspondence thread 53, message 1054. This authorizes use
of the released holdout under the already locked
[predictive specification](predictive-specification.md). Truth remains sealed.
Barry's standing bundled commit-and-push authority applies to this stage.

## Fixed scope

Evaluate the exact four saved training fits for each of the four cases, using
the qualified conditional-prey score, the original K=131,072 integration bank,
whole-map normalization and observation model. No fit, model, comparator,
profile, calibration table or declaration changes. Report all 16 total and
per-site mean log scores, 640 site contributions, 128 cluster contributions,
and all six pairwise differences per case. Higher scores are better under this
fixed rule. The training and held-out observations share each case's spatial
process; neither sites nor clusters are independent replication for an
automatic standard error.

Evaluate the recorded leading-pair forecasts using exact saved maxima and
their original intersection rule. Retain co-winners, every score difference
and the winning margin. Each forecast named two of four models. Defer all
generating-truth forecast checks until the separate truth release.

## Execution and evidence

This record is written after release and schema verification, before score
calculation. The plaintext holdout archive must match the earlier commitment
`53903e56b0b86d8d713bf643d9c3062e8ce918fa8b84afa48f9b8ace6859fe6a`.
Validate the salted archive, neutral case labels, site order, count arrays and
their complementarity with the frozen training data. Preserve the original
archive and training lock. Record the release verification under
`artifacts/goal061_holdout/`.

Use the existing qualified Linux runtime on `deep-server`: Python 3.14.5,
NumPy 2.5.1 and SciPy 1.18.0, verified live on 8 October. The scientific
source, public map/bank and training fits remain in the original run directories;
the new scoring adapter and outputs use a separate dated directory under
`/data/codex/scratch/`. Run one scoring process with one numerical-library
thread. Perform targeted adapter checks before the actual scores, and return
the complete new output to the local repository with hashes. Record measured
runtime and memory; no reference generation or optimization is needed.

Independently audit input/fit bindings, per-site calculations, cluster/total
aggregation and forecast scoring, then review the report's claims. Keep the
old training report immutable and add a combined report with the released
holdout results. Lock that report and its evidence before requesting the
separate truth release. Numerical or schema failures retain their evidence;
repairing an adapter does not authorize a scientific change.

## Human input

Decision Inbox is available for consequential questions, following
`/Users/bwbrook/work/decision-inbox/docs/decision-priming.md`. The guide was read
on 8 October. No questionnaire is needed for this already specified scoring
stage. A change to the estimand, model comparison or release boundary would
require Barry's decision; routine implementation and verification proceed
within the existing authorization.

## Completed scoring and evidence return

The release check recomputed the plaintext archive and member hashes, verified
the neutral case/schema identities, and rehashed all 3,734 training-lock files
(6,375,566,653 bytes), with no mismatch. Its receipt is
`artifacts/goal061_holdout/release-verification.json`. The original training
root, report, predictive specification and prereveal forecasts remain intact.

The new scoring adapter uses canonical public site order when joining training
and holdout. Four meaningful mechanical tests cover input validation,
interleaved site placement and cached emissions, invalid-fit preservation,
exact ties and unavailable forecasts. They pass locally and in the original
Linux runtime (4 passed in 3.48 s). The independent adapter's three mechanical
tests also pass locally and on Linux (3 passed in 0.10 s). New scripts pass Ruff.
The existing qualified scientific modules were not edited.

Main scoring completed at **23:12:35 AEDT on 8 October**, exit 0, in **28.19 s**
with **467,280 KiB** maximum RSS. It produced all 16 finite scores, 640 site
contributions, 128 cluster contributions, 24 pair differences and four forecast
records. The main adapter SHA-256 is
`9e43c6664b6f47fc1b6111c243365982e6aaa39064d03e9e2067d972aa660bc7`;
the score JSON is
`a5c58a4a95f2deb6031f4b7297229e54c091f3c26e0efe33929025c54c5c43d2`.

The first independent audit passed in 8.08 s using adapter `38c9bdd5...fe0af`.
An explicit main-adapter hash check was added after that version was handed
off for execution. The original source and successful audit remain preserved;
the final adapter `545975da...1fad8` was run separately and passed in **8.05 s**
with **614,348 KiB** maximum RSS. Its computed scores and comparison records are
identical to the first audit. No numerical rule, fit, observation, threshold or
forecast changed. The final receipt
`artifacts/goal061_holdout/remote-return/outputs/independent-audit-final.json`
hashes to `41b499344e02aba943291eca52d0651ad97b48b49747536d10afdc011b3a9769`.

All site, cluster, total and mean comparisons pass the existing 1e-8 absolute
numerical tolerance. The largest score discrepancy is 5.684341886080802e-14
nats; the largest site discrepancy is 1.5987211554602254e-14, and the largest
pairwise discrepancy is 1.1368683772161603e-13. All exact winner sets and
forecast outcomes agree. Case-00 is an exact tie between identical adjusted
fits. Cases 01 and 03 have distinct but almost coincident constant fits. These
facts do not change the registered exact-max forecast rule.

The original and final runs are retained in
`deep-server:/data/codex/scratch/goal061-capstone-holdout-20261008/`; the local
copy is `artifacts/goal061_holdout/remote-return/`. All **36 returned files /
874,082 bytes** match the remote inventory, whose SHA-256 is
`2c96f83797e21b5db107a1683ce08e65fddbbcc722023691a35d91fa8eb1227a`.
The separate `artifacts/goal061_holdout/return-verification.json` also confirms
that the executed final scoring and audit adapters equal the current source.
Each run used one process/thread, an 8 GiB virtual-memory limit and a 900-second
timeout; every run exited normally. No worker or supervisor remains active.

The [complete report](complete-report.md) preserves one leading-pair hit and
three misses, both exact co-winners in case-00, all unrounded comparative
evidence and the still-unevaluated truth forecasts. Five CSVs copied into
`holdout-results/` match their original score outputs byte-for-byte. The
separate renderer produces PNG/PDF figures bound to the full-precision totals.
The [independent review](holdout-independent-review.md) and
[complete-report lock](complete-report-lock.md) complete this stage before any
truth release. No private key or truth material was accessed.
