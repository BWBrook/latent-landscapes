# Capstone truth reveal and forecast assessment

9 October 2026, Hobart. Codex (historically Astra). This is the final reveal
assessment for the registered capstone. It advances the Charter's predictive
comparison and uncertainty pillars and the roadmap's model-comparison and
integrated-capstone evidence. The [prereveal predictions](prereveal-predictions.md),
[training report](training-report.md) and [training-plus-holdout report](complete-report.md)
remain unchanged.

**All four generating effects are null, h=1.** The four null-class forecasts
were correct, and the four calibrated analyses made no false declaration in
these cases. However, the capstone contains no positive-effect realization,
so it cannot demonstrate positive-effect detection or recovery. Two cases were
generated under B100-A rather than the working background family; both of my
locked branch forecasts were wrong. Accurate detection-SD forecasts and the
mostly accurate mean-hazard forecasts coexist with this failure to identify
the background mechanism.

## Released truths and unchanged training decisions

| Case | True h | True background | True beta | True mu/day | True detection SD | Saved adjusted h estimate | Unchanged p_BB |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| case-00 | 1 | Exact | 0.25 | 0.0040 | 0.3 | 1 | 1 |
| case-01 | 1 | B100-A | Undefined | 0.0040 | 0.2 | 1 | 1 |
| case-02 | 1 | B100-A | Undefined | 0.0010 | 0.3 | 1.28762361924 | 0.422 |
| case-03 | 1 | Exact | 0 | 0.0016 | 0.1 | 1 | 1 |

All four outputs remain valid non-declarations under the registered procedure,
with no abstention or diagnostic hold. The reveal establishes that no false
declaration occurred in this realized panel; a non-declaration itself did not
establish absence before the reveal. Cases 00 and 03 are exact-family on-grid
nulls. Cases 01 and 02 lie outside that family, so the conditional casewise
finite-grid guarantee does not extend to them. Their two non-declarations are
observations, not a robustness or false-positive-rate estimate.

The public law independently assigned probability one half to h=1 for each
case. An all-null four-case draw therefore had probability 1/16 under that
law. No case has been replaced or redrawn to obtain a more informative mix.
This probability describes the registered random composition; it is not a
post hoc test of the data or evidence that the generator failed.

## Every committed truth forecast

The primary effect forecast was null with h=1 in every case. All four are hits,
and every primary absolute log-h error is zero. Using the unchanged continuous
adjusted estimates instead, the absolute natural-log errors
`abs(log(h_hat / h_true))` are **0, 0, 0.2527983638884294 and 0**. Case-02's
estimate is about 28.8% above its actual null value. This is a realized error
in a misspecified case, not an estimate of systematic bias. Its previously
recorded weak discrimination remains weak; the correct primary forecast does
not retrospectively make it a strong judgment.

The exact-family branch forecast is correct for cases 00 and 03 and wrong for
cases 01 and 02. These were explicitly weak, prior-modal judgments, with no
branch-specific likelihood or residual adequacy test. The two misses remain
misses; successful prediction of other quantities does not repair them.

| Case | Branch forecast | Branch outcome | Beta forecast, if exact | Revealed beta | Conditional absolute beta error |
| --- | --- | --- | ---: | ---: | ---: |
| case-00 | Exact | Hit | 0.25 | 0.25 | 0 |
| case-01 | Exact | Miss | 1.00 | Undefined | Not scored |
| case-02 | Exact | Miss | 0.00 | Undefined | Not scored |
| case-03 | Exact | Hit | 0.25 | 0.00 | 0.25 |

Beta is a generating parameter only under the exact branch. The fitted
exposure coefficient in a B100-A case can still describe the working model,
but comparing it with an invented true beta would change the question.

| Case | Mu/day forecast | True mu/day | Exact-grid outcome | Absolute error/day | Detection-SD forecast and truth | SD point outcome |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| case-00 | 0.004 | 0.0040 | Hit | 0 | 0.3 | Hit |
| case-01 | 0.004 | 0.0040 | Hit | 0 | 0.2 | Hit |
| case-02 | 0.001 | 0.0010 | Hit | 0 | 0.3 | Hit |
| case-03 | 0.001 | 0.0016 | Miss | 0.0006 | 0.1 | Hit |

All four SD point errors are zero. The separately committed broad SD sets also
contain all four truths: {0.2,0.3}, {0.1,0.2,0.3}, {0.2,0.3} and {0,0.1,0.2}.
Those sets cover respectively two, three, two and three of the four permitted
SD values. Their four hits are reported separately from the point forecasts
and do not establish interval coverage. The mu and SD point forecasts were
rounded to permitted truth-law values; their grid hits do not mean the
continuous estimates recovered the generating values exactly.

The [full-precision forecast table](truth-results/forecast_scores.csv) records
every outcome and error, including inapplicable beta errors as blank fields.
The four-case counts are descriptive results, not estimated operating rates.
No departure from a locked forecast rule was needed.

## What the holdout and truth together show

The predictive assessment stays **one leading-pair hit and three misses**.
The truth does not redefine a held-out winner. In case-01, the 10.51-nat
training advantage for adjustment reversed to a 1.85-nat holdout disadvantage,
and the revealed branch is B100-A. The result is consistent with a working
exposure gradient capturing background structure that does not generalize to
these held-out clusters. It does not isolate that mechanism causally: there
is no paired exact-family counterfactual, and finite-sample spatial variation
also affects the comparison. Case-02 is also B100-A but has much smaller
predictive differences. Branch identity alone therefore does not supply a
validated diagnostic for the magnitude or direction of a holdout reversal.

Claude's message 1278, after holdout but before truth, separately favored
B100-A for case-01. That advisory expectation was correct. It was explicitly
unregistered, used additional information, and does not replace my earlier
locked exact-family forecast or enter its score. The earlier report's tiny
case-01 and case-03 within-family rankings retain their original qualifications.

The capstone demonstrates an intact blinded workflow and an informative
mixture of correct and incorrect scientific judgments. It does not establish
positive-effect power, reliable branch selection, uncertainty coverage,
general parameter recovery or transfer to new maps. The right next synthesis
step is to place these results alongside the earlier controlled experiments
and identify which Paper 1 claims already have suitable evidence. Any new
positive-effect panel would be a separate prospective experiment, not a
replacement for this realized capstone.

## Release, computation and review

Claude accepted the complete-report lock in correspondence thread 53,
message 1278 on 9 October. Barry then stated **"Truth released, hash matches."**
Before reading the truth metadata, Codex recomputed the archive commitment:
`f4145408b52e24e459e751f9fa646a3365fb9d596f8a3da8476853e48c56af8d`.
The archive has the expected eight regular members and 32-byte salt. Its
truth-metadata member hashes to
`cacd35e8432dccee5a125b051c74f1b8cbc27b7e6aa82e78c0ef0cb4c6eef135`.
The original archive is retained. No private encryption identity was accessed.

All 3,793 files and 6,376,862,557 bytes in the accepted pretruth closure were
reverified without mismatch. Its root remains
`baa0ec8660321d698e4cb5b2d3ef9f41ef41fec9b3a7e751fe18a00813e835af`.
The new scorer was implemented after release to apply the previously locked
rules; it is not described as code frozen before truth. It binds the forecast
text and each saved adjusted fit to their original hashes. Three mechanical
tests passed, covering a wrong null forecast under a positive truth,
inapplicable beta with separate SD-set scoring, and commitment verification
before archive parsing. Ruff lint and format checks passed.

The command was `.venv/bin/python scripts/score_capstone_truth.py --output
artifacts/goal061_truth/score-run`. This is a local, standard-library arithmetic
assessment; no fitting, calibration, integration-bank calculation, simulation
or generator replay was run. Source/input hashes, runtime and complete scores
are in `artifacts/goal061_truth/score-run/scores.json`; the release receipt is
`artifacts/goal061_truth/release-verification.json`.

The [independent truth review](truth-independent-review.md) recomputes the
forecast checks from the released metadata and original fit files, separately
from the main scorer. Its receipt and the final artifact inventory are retained
under `artifacts/goal061_truth/`. All earlier locked reports, declarations,
failed qualification evidence and release commitments remain intact.
