# Independent review of the capstone truth assessment

9 October 2026, Hobart. This review covers the authorized Goal 061 truth
release, the locked truth forecasts and the final truth report. I independently
read only the released truth metadata fields needed for scoring, the
hash-bound prereveal predictions and the four original `adjusted_free_h` fit
records. I did not inspect the latent-case arrays, rerun a model or generator,
or access a private encryption identity.

## Decision

**Accept the truth forecast scores and `truth-report.md` without scientific or
numerical repair.** The main scorer transcribes the locked forecast rules
correctly, the published CSV agrees exactly with my separate calculation, and
the report preserves the material limitations of the realized panel.

All four primary null-effect forecasts are hits and their absolute log-h errors
are zero. The exact-background forecast is correct in cases 00 and 03 and wrong
in the two B100-A cases, 01 and 02. Conditional beta prediction is correct in
one of the two cases where beta exists. Mean hazard is correct on the exact
truth grid in three cases, while detection SD is correct in all four both as a
point forecast and, separately, under the broad forecast sets. These are four
realized forecast checks, not estimates of operating rates.

## Scientific target, rules and results

The target is the agreement between each generating truth and the forecasts
recorded before holdout and truth release. It is distinct from the earlier
held-out predictive score. For a positive quantity h, the registered error is

\[
\left|\log\left(h_{\mathrm{forecast}}/h_{\mathrm{true}}\right)\right|.
\]

Background is an exact categorical hit or miss. Beta is scored only when the
truth belongs to the exact family; it is undefined under B100-A. Mean hazard
and detection SD use exact equality to the locked discrete point forecast plus
absolute error. The broad detection-SD sets are evaluated separately and are
not confidence or credible intervals. The four Berger--Boos results remain
inferential declarations rather than truth forecasts: declaration requires
`p_BB <= 0.05`, and none declared.

| Case | Effect and h forecast | Continuous fitted-h log error | Background | Conditional beta | Mean hazard | Detection SD |
| --- | --- | ---: | --- | --- | --- | --- |
| case-00 | Hit; error 0 | 0 | Exact hit | Hit; error 0 | Hit; error 0 | Point and set hit; point error 0 |
| case-01 | Hit; error 0 | 0 | Exact forecast misses B100-A | Not applicable | Hit; error 0 | Point and set hit; point error 0 |
| case-02 | Hit; error 0 | 0.2527983638884294 | Exact forecast misses B100-A | Not applicable | Hit; error 0 | Point and set hit; point error 0 |
| case-03 | Hit; error 0 | 0 | Exact hit | Miss; error 0.25 | Miss; error 0.0006/day | Point and set hit; point error 0 |

The primary counts are therefore 4/4 effect-class and h hits, 2/4 background
hits, 1/2 applicable beta hits, 3/4 mean-hazard hits, 4/4 detection-SD point
hits and 4/4 broad-set hits. The unchanged `p_BB` values are 1, 1, 0.422 and 1.
All four are valid non-declarations and, because all four revealed effects are
null, there is no realized false declaration.

The continuous adjusted-fit comparisons support the same interpretation but
are not substitutes for the locked grid forecasts. Only case-02 has nonzero
log-h error, 0.2527983638884294, from h-hat 1.2876236192375865 against h=1.
For the exact-family cases, fitted beta absolute errors are
0.012643528738643522 and 0.15991662742942414. Continuous fitted mean-hazard
absolute errors for cases 00--03 are 0.00026427374485050656,
0.000006475464959488156, 0.0000796950339721355 and
0.0005249655750763132 per day. Fitted detection-SD absolute errors are
0.015468479479845976, 0.00033542635443978286, 0.006405811718544874 and
0.016627019708837718. These continuous errors are diagnostic context; the
preregistered scoring rules require a continuous comparison only for h.

## Independent verification

The released archive matches SHA-256
`f4145408b52e24e459e751f9fa646a3365fb9d596f8a3da8476853e48c56af8d`.
The read truth-metadata member matches
`cacd35e8432dccee5a125b051c74f1b8cbc27b7e6aa82e78c0ef0cb4c6eef135`.
The forecast text matches its locked digest
`ea017c2300214b834ddb28fae577d9c5f9e43ba9f43337a185d448bd7bab1895`.
The four fit records match their original digests:

- `692a35dd3d421755b8024310a2e39a42dd38ff28154e801e160aa789a9da4bd1`;
- `7433ba16f1e5a21d14650bbe895da6c4042ef98577dea9bde183ab910787865d`;
- `a2ad1c2a840a6eababcbe16d52d8ae6b88655c23e1d5021c2c0d9eb48ef430f5`;
- `597aaf31524009e8b082d96dd82272cbdf0c29496ba09c7add15282abcfb0a8f`.

All saved adjusted fits retain converged status.

My independent calculation is
`artifacts/goal061_truth/independent-audit.json`, SHA-256
`fa40c887a6e1f5737d75470a65e60a6732ae4892320ba443e91f5aca93ae2e62`.
It was created before I inspected the main scorer output or truth report. For
every case, its truth values, categorical outcomes, applicable errors and
declaration values match
`artifacts/goal061_truth/score-run/scores.json` exactly. The documentation CSV
is byte-identical to the scorer CSV; both have SHA-256
`64888b0b90f9c53554562826460cf10f6223cacc1f4aff9489f77d3e6b8128a2`.
Blank beta fields occur only for B100-A truths and correctly mean “not
applicable,” rather than zero error or missing analysis.

The reviewed main scoring source has SHA-256
`5de46fa23fa9ebccae0eac3ea49190adb0a4b238635a17433108530f3370c474`.
It verifies the release gate, truth commitment, complete-report lock,
prereveal forecast digest, training and computation manifests, and exact fit
files before scoring. Its three focused tests pass in the local project
environment; they cover a positive truth against the null forecast, beta
inapplicability with separate SD-set scoring, and commitment failure before
archive parsing. Ruff lint and format checks pass. The reviewed truth report
has SHA-256
`15066a66c899cb04de412bf0ab2b5e4507801497c4fbaf87654a04323da23a4d`.

## Failure modes, implications and recommendation

The realized composition is the dominant limitation. All four cases are h=1;
under four independent one-half null draws, this composition had probability
1/16. The draw was neither replaced nor selected after inspection, so it is a
valid capstone outcome. It contains no positive-effect case and therefore
provides no evidence about positive-effect sensitivity, power, magnitude
recovery or false-negative behavior. Four correct null forecasts and zero
false declarations must not be generalized into such claims.

Only cases 00 and 03 are exact-family on-grid nulls covered by the registered
conditional casewise guarantee. Cases 01 and 02 are B100-A. Their realized
non-declarations are scientifically useful observations, but they do not
extend the exact-family guarantee to misspecified backgrounds or estimate a
false-declaration rate. The beta parameter is absent under B100-A, so neither
the working-model beta estimate nor its grid forecast can be called parameter
recovery in those cases.

The branch forecasts were identical prior-modal “Exact” judgments because the
training analysis had no branch-specific likelihood or residual diagnostic.
Two hits and two misses do not establish branch-selection skill. Claude's
postholdout, pretruth B100-A expectation for case-01 used additional
information and was correct, but it was unregistered and must remain outside
the locked forecast score.

The joint holdout/truth pattern is suggestive rather than causal. Case-01 is
B100-A and its large training advantage for adjustment reverses on holdout,
which is compatible with the working exposure term absorbing background
structure. Case-02 is also B100-A but shows much smaller predictive
differences. Without a paired exact-family counterfactual, replicated maps or
a branch diagnostic, background identity cannot be assigned as the cause of
the case-01 reversal. Shared-map spatial variation and finite-sample effects
remain competing explanations.

The 4/4 detection-SD result is a successful point-forecast outcome. The broad
sets cover two or three of the four permitted values in every case, so their
4/4 result is weaker and supplies no coverage estimate. Likewise, the 3/4
mean-hazard result and 1/2 conditional beta result are descriptive checks with
estimation, sampling and case-composition uncertainty unquantified. No
multiple-testing correction or interval calculation would repair the absence
of replication for operating-rate claims.

I recommend accepting the truth report as the final capstone reveal record and
preserving every miss without retuning. The next synthesis should compare
these realized checks with the earlier controlled experiments before deciding
which Paper 1 claims are supported. Any added positive-effect or
misspecification panel should be a separately registered prospective study,
not a replacement for this all-null panel. Further independent review is
unlikely to change confidence in the arithmetic or provenance; it would
materially matter if a later synthesis tries to claim positive-effect power,
robustness to B100-A, branch identification, calibrated broad-set coverage or
new-map generalization from these four cases.
