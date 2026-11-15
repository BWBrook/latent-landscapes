# Bounded repair: completed execution, acceptance unmet

15 November 2026. This assesses the Paper 1 numerical-qualification repair
after completion job 879239 exited with status 1. Candidate
`a77e849ce0b0381b5c378b222bacfadce9beaf96` implements the bounded A+B+C repair
accepted in board message 3307. The [12 November acceptance plan](../paper1-sprint2-repair-2026-11-12/acceptance-plan.md)
and frozen selection remain unchanged.

**The repair has not passed its frozen acceptance checks.** Most original
failures now resolve, but two comparison probes fail the absolute-criterion
rule and two development fits were killed at the 48-hour limit. No fresh
qualification panel, training or validation has been opened. The rejected
original candidate and its qualification verdict remain fixed.

## What completed

| Planned group | Resolved fits | Scientific failures | Missing terminal fits |
|---|---:|---:|---:|
| 24 originally resolved non-regression fits | 24 | 0 | 0 |
| 27 originally failed development fits | 23 | 2 | 2 |
| All 51 fit replays | 47 | 2 | 2 |

All 24 non-regression probes completed all **12,460 exact required anchors**,
with no anchor errors: 22 probes passed and two failed. Exactly three checks
exceed the frozen `1e-6` absolute-criterion tolerance, all in the standard
positive-variance family:

- Corridor-0 window-high C exhaustive, h=30: shift `-1.199879307023366e-6`.
- Corridor-0 constant C independent bank, full-fit null h=1:
  shift `-1.978426303139713e-5`.
- The same constant task, exact h=1 probe: shift `+3.069501644858974e-6`.

All profile-LR checks pass their unchanged `1e-3` tolerance and all eligibility
verdicts agree. Every envelope, sigma-zero, tight-spatial, exposure and constant
comparison passes. Those agreements do not overturn the failed criterion
checks: the frozen plan explicitly includes the separate positive family.

The [regression diagnosis](nonregression-diagnosis.md) identifies earlier
stopping and start-dependent selection near zero variance as the leading
explanation. A separately reviewed, post-outcome fixed-vector diagnostic
evaluated five retained endpoints under both frozen sources without optimization.
All five positive-family criteria reproduce their archived values exactly and
are identical across sources, as are five sigma-zero controls at the same
nuisance parameters. Core gradients agree; detection-SD gradients change with
the repaired derivative. This supports endpoint selection over an objective
change at these vectors, without proving derivative truth or an objective-error
bound. It cannot retroactively change the frozen gate.

The [plan](fixed-vector-plan.json), [evaluation script](evaluate-fixed-vectors.py),
[baseline result](baseline.json) and [candidate result](candidate.json) retain
the diagnostic. One allocated job (880733) ended successfully in 53 seconds;
both sources, all input bytes, common runtime, plan and script identities were
verified. The sigma-zero controls are evaluations at the retained positive
fit's nuisance parameters, not refitted maxima.

The two scientific failures remain the dense and lean corridor-1 window-low B
fits: `search_unresolved`, because an unresolved candidate exceeds the selected
family envelope. Constant and exposure are available; spatial is unavailable.
This is the case explicitly excluded from tuning under the accepted repair.

## Execution losses and resources

The two missing terminal fits are corridor-0 increased-heterogeneity C dense
(index 31) and corridor-2 b100-anchor C dense (index 42). Native accounting and
both routed logs identify 48-hour walltime kills. They retain complete spatial
search receipts marked `profile_numerically_resolved`, after 40.91 and 32.54
search hours respectively, but lack final fit receipts. Their partial outputs
are preserved as a recovery lead; neither fit counts as resolved and neither
was retried by this assessment.

| Completed task group | n | Median hours | Maximum hours | Summed task hours |
|---|---:|---:|---:|---:|
| Non-regression fits | 24 | 5.54 | 19.37 | 160.62 |
| Development fits, including two scientific failures | 25 | 19.94 | 47.20 | 534.68 |
| Comparison probes | 24 | 4.87 | 14.51 | 143.61 |

These sums describe parallel task allocations, not campaign elapsed time. The
two missing fits add about 48 hours each and are excluded from the completed
fit rows. Search completion alone is insufficient for sizing the full workflow;
the later fit/audit stages also need resumability and adequate walltime.

The earlier 50 failed launcher allocations are a separate, preserved incident.
Only one original task started before the array-index/PBS-metadata correction;
the other indices were resubmitted without changing scientific source or inputs.
Those allocations are not 50 scientific failures and are distinct from the two
later walltime kills.

## Repair efficacy and evidence identity

Across the **49 terminal fit receipts**, all 1,462,456 recorded inner branch
calls terminate as converged, with 14,083 invalid trial rejections and zero
recorded mode or positive-definiteness failures. Inner iterations have median
4, 90th percentile 8, 99th percentile 12 and maximum 27. This supports the
invalid-trial repair's efficacy within completed fits; it does not certify the
uncompleted stages of the two killed fits.

The [independent execution audit](independent-execution-review.md) verified all
73 terminal task records, all 414 inventoried outputs, all 12,460 checkpoint
file/payload hashes, exact frozen anchor coordinates and all 22,584 comparison
rows. It found no integrity or execution-contract contradiction. Source hashes
bind the candidate Git commit. Raw remote banks were not freshly rehashed by
the local audit; their frozen input checks remain recorded target-side evidence.

The canonical aggregate evidence is
`artifacts/sprint2/repair-20261112/final-20261115/`, especially
`completion-index.json`, `fit-reconcile.json`, `probe-reconcile.json` and
`replay-summary.json`. The index and all six indexed file hashes agree. Its
`all_nonregression_passed=false`, `qualification_pass=false` and
`scientific_review_required=true` correctly preserve the decision.

Next: Claude — reconcile the failed criterion checks and execution losses before choosing the next bounded step.
