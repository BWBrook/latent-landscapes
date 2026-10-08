# Goal 053 independent result review

27 September 2026. **No result-level implementation defect was found. Accept
Goal 053 as a completed prospective performance comparison, with mixed rather
than universal support for spatial background adjustment.** The result supports
a bounded calibration experiment before any survey redesign. It does not
establish a repaired estimator, calibrated effect declaration, structural
identifiability, or confirmation of the Goal 051 nominee under its original
procedure.

## Scientific target and audit scope

The registered estimands are repeated-history performance on one fixed
landscape and survey design: adjusted-minus-constant absolute log-h error and
direct held-out conditional-prey log score. The prediction target is the fixed
set of 40 holdout sites under each newly generated process history; it is
spatial transfer within the same site split and landscape, not transfer to
newly sampled sites or another landscape. The simulation block is the
replicate. Sites, visits and the six paired cells within a block are dependent
and were not treated as independent replicates.

The data-generating comparison contains exact beta=0 and beta=.60 controls at
h=1 and h=3, plus the original B100-A generator with residual field G omitted
from the fitted model. All actual fits use the six imperfect-detection surveys
at 120 training sites. Known-beta fits are evaluator-assisted benchmarks for
the exact cells; the first 250 blocks also have true-arrival oracle fits. The
constant, adjusted and adjusted-null parameter fits are selected using training
likelihood alone, then evaluated on untouched holdout observations. The separate
model-preference label is assigned from the sign of the resulting held-out
adjusted-minus-constant score. The fitted adjusted h=1 model is the neutral
predictive comparator within the adjusted family.

I inspected the [registration](registration-2026-09-27.md),
[implementation review](implementation-review.md),
[information review](information-review.md), generator, campaign and synthesis
code, per-history metrics, bootstrap summaries, diagnostics and all three
figures. I independently recomputed the primary means and analytic Monte Carlo
SEs directly from the 6,000 rows in
[metrics.csv](../../../artifacts/goal053_execution/synthesis/metrics.csv).
They agree with the saved summaries to floating-point precision. The table has
exactly one row for every block-cell pair; the oracle table has exactly the
registered four cells in blocks 0--249.

## Decisive results

Negative error changes favour adjustment; positive predictive-score changes
favour adjustment. Intervals are the registered 2,000-draw whole-block
percentile intervals and quantify simulation-summary uncertainty.

| Cell | Change in mean absolute log-h error (MCSE; 95% interval) | Direct held-out score, nats/site (MCSE; 95% interval) |
| --- | ---: | ---: |
| E0_h1 | +0.1587 (.0134; .1327, .1858) | -.00488 (.00065; -.00620, -.00359) |
| E0_h3 | +0.0973 (.00730; .0835, .1114) | -.00354 (.00049; -.00449, -.00261) |
| E06_h1 | -.1764 (.00868; -.1940, -.1596) | +.00196 (.00074; .00057, .00336) |
| E06_h3 | -.1082 (.00748; -.1231, -.0940) | +.00674 (.00092; .00488, .00848) |
| B100-A_h1 | -.1522 (.00942; -.1699, -.1334) | +.00063 (.00087; -.00109, .00228) |
| B100-A_h3 | -.0466 (.00791; -.0613, -.0318) | +.00485 (.00097; .00305, .00671) |

All registered precision targets were achieved: the largest error-contrast
MCSE is .0134 against .02, and the largest direct-score MCSE is .000971 against
.002. The signs resolve five of the six direct-score comparisons and every
error comparison. B100-A_h1 prediction is genuinely unresolved, rather than a
small positive result.

Adjustment therefore has a conditional benefit. It materially improves h
error when the true background varies with A and under the residual-G stress,
but unnecessary beta flexibility harms both h estimation and prediction in the
exact beta=0 cells. Under B100-A, improvement is not adequacy: adjusted signed
log-h error remains +.187 at h=1 and -.058 at h=3, and at least 1.5-fold point
errors occur in 20.4% and 20.2% of histories. Neither fitted family is correct
under residual G.

The neutral comparisons reinforce the separation between estimating h and
choosing a background family. Adjusted-minus-adjusted-null prediction averages
-.00199, -.00157 and -.00190 nats/site in the three h=1 cells, but +.02945,
+.04472 and +.03585 at h=3. Thus a fitted predator effect adds conditional
predictive information at h=3 but not at h=1. Nevertheless, the constant model
predicts better in E0_h3 because it represents that cell without the nuisance
cost. Under B100-A, adjusted wins occur in 55.0% of h=1 and 59.8% of h=3
histories; those relative wins do not validate h or identify G.

## Predictions and information diagnostics

The registered forecast audit is mixed and must remain visible.

- Free/known-beta log-RMSE ratios at h=3 are 1.404 [1.338, 1.475] for E0 and
  1.082 [1.053, 1.112] for E06. Neither crosses the registered contradiction
  bounds of 1.60 and 1.30. The E0 target of 1.25 understated the realised
  nuisance cost; the E06 result is close to the 1.05 forecast.
- At E06_h3 the constant signed log error is +.290 [.276, .304], while adjusted
  and known-beta errors are -.006 [-.022, .011] and -.030 [-.044, -.014]. The
  adjusted-minus-known mean difference is +.024 [.016, .031], supporting the
  registered bias forecasts without implying equal RMSE.
- The h=1 boundary forecast is supported. Adjusted h>=1.5 occurs in 30.1%
  versus 16.3% with beta known at E0, and 20.9% versus 11.2% at E06. Among
  adjusted fits with h>1, beta is below truth in 72.6% and 61.6%, above truth
  in 23.3% and 34.4%, and tied in 4.1% and 3.9%.
- The forecast direct gains of .01--.025 nats/site at E06 are contradicted:
  observed gains are .00196 and .00674. The h=1 adjusted-win rate is 59.2%
  [56.2%, 62.1%], below the two-thirds forecast. The h=3 rate is 64.8%
  [61.9%, 67.7%], compatible with roughly two thirds despite the smaller score
  magnitude.

Known-beta fits show that beta estimation, rather than background adjustment
itself, accounts for appreciable loss: adjusted versus known-beta mean absolute
log error is .309 versus .151 at E0_h1, .325 versus .228 at E0_h3, .192 versus
.126 at E06_h1, and .212 versus .195 at E06_h3. This is weak-information and
boundary evidence, not structural non-identifiability.

The oracle lane does not make latent arrival uncertainty the leading diagnosis.
In matched blocks 0--249, oracle minus latent adjusted absolute error is only
-.0110, -.00445, -.00492 and -.00214 across E0_h1, E0_h3, E06_h1 and E06_h3.
Mean LR<=2 h-profile width changes are -.0158, +.0038, -.0352 and -.0070 h
units. These are descriptive matched checks without a new bootstrap. They agree
with the complete-data information review: event scarcity and an h-beta
trade-off are plausible mechanisms, but known arrivals alone do not materially
resolve the observed-data problem.

## Numerical, design and uncertainty limits

The finite-grid diagnostics do not overturn the comparisons. There are 36 beta
edge fits and six h=10 fits among 6,000 actual histories. All h profiles are
connected; one B100-A_h1 beta profile is disconnected. The 425 coarse-grid
flags are entirely h-coordinate shifts along flat likelihood geometry: maximum
LR movement is .0422, maximum beta movement is .05, and the largest h movement
is .60. Replacing fine-grid adjusted h by the nested coarse-grid value changes
cell mean absolute log error by at most .00114. The estimates remain conditional
on the registered .05 grid; this check does not justify continuous-parameter or
off-grid claims.

Lower h-profile contact is expected and frequent in h=1 cells (91.3--93.0%).
At h=3 it remains 13.5% in E0, 2.9% in E06 and 7.6% in B100-A, showing limited
profile separation in a non-negligible subset. LR<=2 ranges are explicitly
uncalibrated geometry and cannot be reported as confidence intervals.

The design has no history selection, outcome-dependent refitting or holdout
leakage. Whole-block resampling correctly preserves within-block pairing and
spatial/temporal dependence. Its intervals do not represent uncertainty for a
single fitted history, calibration-table uncertainty, new landscapes, other
survey schedules, unknown nuisances or off-grid truth. The forecast checks are
multiple descriptive checks with no multiplicity-adjusted decision claim.

The local [synthesis verification](../../../artifacts/goal053_execution/synthesis-verification.json)
records 13 authenticated outputs and summary SHA256
`d3aa7622c89cd378b2fbe0775fe73903f2abb8461e04f140782fb728616f448e`;
I reproduced that hash and the two synthesis-source hashes. Production's 81
rows, 6,000 actual/1,000 oracle histories, 170 files, numerical controls and
source bindings passed the completed remote controller verification recorded
in the [execution record](execution.md). A separate direct extraction from all
remote score surfaces reproduced every saved fitted coordinate, training
maximum and held-out contrast exactly; its zero-difference results are in the
[score-metric crosscheck](../../../artifacts/goal053_execution/score-metric-crosscheck.json).
The [retrieval manifest](../../../artifacts/goal053_execution/retrieval-manifest.json)
authenticates 85 local production records and 13 local synthesis outputs; the
four multi-gigabyte score rectangles and 81 redundant compressed row arrays
remain intentionally at the authenticated remote root. I did not independently
read those bulk arrays or rerun simulations, fitting, synthesis or bootstrap
draws.

## Recommendation

Proceed next, subject to a new scientific registration, with a finite-grid
calibration and fresh evaluation of the adjusted h=1 decision rule before
redesigning the survey. A defensible first rule is the composite-null profile
statistic

`T = 2 {max_(h,beta) ell(h,beta) - max_beta ell(h=1,beta)}`,

with plus-one Monte Carlo p-values at each of the 81 beta nodes and the supremum
of those p-values as the analyst-usable finite-grid null test. Exact E0/E06
h=1 cells should measure assumed-model size, B100-A_h1 should remain an explicit
residual-G stress with no theoretical calibration guarantee, and the h=3 cells
should measure conditional power, error and prediction. This would test an
inferential operating rule; it would not improve point estimates or calibrate
the full profile.

Calibrate a matched constant-background test from the same beta0 reference
histories. Its guarantee applies only under beta0, but its paired evaluation
separates the operational cost of adjustment from the harm caused by ignoring
background variation without importing the old Goal 049 table.

Use 999 reference histories per beta node if the tranche is meant to decide
whether the rule is a useful inferential repair. At a 5% tail, 249 references
provide only about 12 tail observations and a tail-probability SE near .014,
larger than the roughly .007 evaluation SE from 1,000 fresh histories. A
249-reference stage is suitable only as a predeclared feasibility or gross-
discrimination pilot. Resample reference and evaluation blocks in the final
uncertainty analysis; conditioning on one realised reference table would
understate calibration-bank variability.

Survey redesign is premature because the current evidence does not identify
arrival observation as the dominant limitation and the fitted adjustment
already improves point recovery under the target background conditions. If the
calibrated rule remains severely conservative, underpowered, or falsely rejects
under residual G, the next design comparison should then target information on
background loss and beta, with its observation and replacement process stated
explicitly. Goal 053 itself needs no further independent review to support this
limited closure. Independent scientific review of the calibration registration
would materially improve confidence because the nuisance supremum, realised
reference-table variability and misspecification claim boundary determine what
that next result can mean.
