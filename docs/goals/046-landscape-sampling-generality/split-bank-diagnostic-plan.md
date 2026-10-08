# Goal 046: bounded diagnosis using existing bank halves

Execution decision, 11 September 2026 (Hobart). This implements the
[independent numerical review](final-bank-diagnosis-review.md) within Goal 046's
existing authority to preserve and diagnose numerical failures. Barry delegated
routine execution and timing judgments. No production acceptance criterion,
biological setting, map, simulated history, bank ceiling or inferential claim
changes. The final K65536/131072 production comparison remains rejected.

## Fixed diagnostic

Use only connected 2026090812 and corridor 2026090812, with their immutable
K131072 banks split into the first and second 65536 rows. No new bank or
biological history is generated. Reconstruct the declared histories from their
original seed manifests using the frozen campaign source. Retain H181 and the
known detection, background and resistance settings.

For connected 2026090812, evaluate rho=1 and the no-effect condition only.
For each half, recompute all 250 calibration and 250 evaluation histories for
both access and balanced designs. Derive each design's rank-239 cutoff from
that same half and report its paired mean log-width contrast. Record the
calibration order around histories 124 and 131. Never import a cutoff from
another bank into the within-half comparison.

For corridor 2026090812, evaluate access evaluation history 0 at each of the
three original effect truths. Freeze the rho candidates to the generating
value plus the seven existing G201 nodes centred at the observed coarse MLE:

`1.0, 1.0570180405613805, 1.0717734625362931, 1.0867348625260582,
1.1019051158766109, 1.11728713807222, 1.1328838852957988,
1.148698354997035`.

Retain all H181 effect candidates. Report raw and locally centred,
effect-profiled rho likelihoods for both halves and their combination. A
half-bank maximum at an edge of the seven-node window makes that local
comparison inconclusive; do not widen the window after seeing the result.

These cases and nodes are selected after examining the failure and are
explicitly diagnostic. They are not a new validation sample or a replacement
for the frozen production comparison.

## Verification and compute bounds

Hash-check the saved banks, profiles and seed manifests against the existing
adoption bindings. Preserve original receipts and their remote absolute paths.
Use the original likelihood and history helpers. The existing integration kernel adds 0.5 pseudocount per arrival category.
Therefore a literal mean of normalized half-bank category masses and survival
moments would count this contribution twice. Undo each half-bank normalization,
remove one duplicated pseudocount contribution and apply the full-bank
denominator. Verify this exact existing-kernel combination against direct
integration of a small concatenated bank before use. Do not average summed
log likelihoods, because site probabilities are combined before their logs
are summed. This preserves the frozen kernel rather than changing its smoothing.

Require first-half calculations to reproduce the corresponding saved K65536
quantities and combined-half calculations to reproduce the saved K131072
quantities within 1e-9 absolute error. A mismatch stops the diagnostic for
technical diagnosis and cannot justify a scientific result. Save the reduced
arrays and a compact report with input/output hashes.

Prepare and smoke-test locally with small inputs. Run the full diagnostic only
on `deep-server-ts`, after all nine current half-grid calculations have exited
and their results have been returned. Use one map diagnostic at a time, four
workers at most, native library threads one, 10 GiB address space, and an
explicit timeout of the smaller of one hour or the remaining time to
2026-09-11 05:00 UTC. Retain the 96 GiB aggregate ceiling. Use a fresh output
directory and a launch receipt to prevent a duplicate run. Do not extend the
window solely to repeat an unchanged diagnostic failure.

The reviewed planning estimate is approximately 3–5 minutes for connected and
20–30 minutes for corridor; actual full-run cost remains unmeasured. Preparation
is retained under
`artifacts/goal046_execution/split-diagnostic/`, separately from the immutable
campaign and review snapshots.

## Interpretation and stopping point

The two equal-sized disjoint halves can reveal Monte Carlo variation and
calibration-rank fragility conditional on the fixed histories and bank stream.
Each half retains the same K65536 pseudocount weight, while the combined K131072
bank has a smaller relative pseudocount weight. Half-versus-combined differences
therefore need not isolate Monte Carlo variation alone. The combined bank is
correlated with both halves. Agreement cannot prove convergence to exact
integration, and disagreement does not by itself estimate exact bias.

Finish the half-grid verification and this bounded diagnosis, update the
independent numerical review, and pause the completion heartbeat at the
scientific decision. Choosing a different integration method, a higher bank
ceiling, a changed validation rule, or omission of Arc 3 remains a consequential
programme decision. No ecological synthesis, commit, push or publication is
authorized by this diagnostic.

## Preparation verified

The helper, explicit 22-file input-hash manifest and small tests are prepared.
The [preparation receipt](split-diagnostic-preparation-check.json) binds the
final code and real-helper smoke. Five focused tests and Ruff pass. The smoke
uses 8+8 saved rows, H181, both frozen map contexts and the real dataset helper;
pseudocount-corrected integration agrees with direct 16-row integration within
4.45e-16, and generated surfaces are finite with the expected shapes. The
connected path reuses the original six-condition helper internally but retains
and diagnoses only the two null-condition outputs. Corridor edge or isolated
rho=1 maxima explicitly mark the diagnostic inconclusive.

At preparation completion, no full diagnostic had launched. The subsequent
Linux preflight and full launch are recorded below.

## Linux preflight verified

At 19:19 UTC on 10 September, the exact preparation was staged under
`/data/codex/scratch/goal046-split-diagnostic-20260911/` on deep-server-ts.
Both 82-file campaign snapshots, the four prepared code/document files and all
22 explicit input hashes reconciled. The five focused tests passed in 1.45
seconds; the 16-row real-helper smoke passed in 20.87 seconds under a 10 GiB
address-space limit and native library threads one. The combined moments
agree with direct 16-row integration within 4.45e-16 on both maps. See the
[Linux preflight receipt](split-diagnostic-linux-preflight.json).

At 19:19 UTC the staged directory contained only preflight evidence. The
later launch required all nine half-grid jobs to have exited and their results
to be checked, fresh source/input reconciliation and a separate exclusive
launch receipt. Those prerequisites passed before the launch recorded below.

## Full diagnostic launched

At 23:28:34 UTC on 10 September, the reviewed diagnostic launched under the
staged remote directory, after all nine production jobs exited and every
half-grid comparison was independently reproduced. Of 216 rows, 213 pass;
the three failures repeat the known corridor generating-rho LR issue. All
separate grid refinements pass. The final ensemble rejection is unchanged.

`full-launch-receipt.json` records the exclusive launch and fresh source/input
checks. The parent strengthened the reviewed launcher to require the exact
nine map identities, 216 verified rows, exact saved/replayed/node checks and
current report, sidecar and adoption hashes. The original prepared numerical
runner is unchanged. The process is limited to 3600 seconds, approximately
00:28 UTC on 11 September, and retains every declared resource bound.

The initial supervisor PID is 84385; `full-process.json` records the calculation
PID/process group. `full-exit.json` will record completion, and `full-output/`
will contain the report and reduced arrays only after successful completion.
Do not relaunch merely because the output directory is not yet present.
Collect and independently review the result at the next four-hour check,
then pause at the consequential scientific decision.

## Completion

The single run completed at 00:04:11 UTC on 11 September with exit 0,
2135.51 seconds numerical runtime and peak RSS 3.0452 GiB. All outputs are
returned; local and remote checks of source, inputs, receipts and 38 reduced
arrays agree exactly. First-half saved-result replay is exact; the combined
bank reproduces saved K131072 quantities within 1.365e-12. See the
[results](split-bank-diagnostic-results.md), [return check](split-bank-diagnostic-check.json)
and [independent review](split-bank-diagnostic-review.md).

The original production comparison remains rejected. All calculations have
stopped and the completion heartbeat is paused at the method decision. The
review's proposal for a new integration-validation study is not an approved
extension of this diagnostic.
