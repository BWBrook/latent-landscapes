# Goal 054: calibrated effect decisions with spatial background adjustment

30 September 2026 (Hobart). **Complete, with conditional scientific support.**

The adjusted decision reduces false effect declarations under aligned
background loss, while retaining useful sensitivity to a threefold effect.
It pays a measurable sensitivity and estimation cost when background loss is
constant. This advances Charter Pillar 4 and Roadmap Arc 4 by separating three
questions: which background model predicts better, how accurately the effect
is estimated, and whether an effect can be declared under a stated null model.
The experiment supports a conditional decision procedure; it does not establish
general model discrimination or complete the synthetic-realistic capstone.

The [registration](registration-2026-09-29.md),
[execution record](execution.md), [methods review](methods-review.md) and
[independent result review](final-review.md) define the design and its evidence.
All earlier numerical failures and Goal 049–053 results remain intact. The
Goal 051 nomination remains unconfirmed under its original endpoint and rule.

## Experiment and inferential boundary

The reference panel contains 999 paired blocks across all 81 exact-null
background slopes, beta = −2 to 2 by .05. The independent evaluation panel
contains 1,000 paired blocks in eight cells. Both use the full 181-by-81
effect/background rectangle, h = 1 to 10 by .05, the frozen K131072/alpha1
bank, known spread and observation nuisances, and the current landscape and
survey. There are 88,919 fitted histories. Training observations determine
all fits and decisions; held-out sites supply prediction scores only.

E0 and E06 are exact log-linear background models with beta = 0 and .60.
B100-A adds an aligned linear field and a Gaussian residual field. N100-A
replaces the linear alignment component with a standardized strict top-third
indicator, retaining the paired residual draw and map mean hazard. Both stress
families lie outside the fitted log-linear model. Each has h = 1 and h = 3.

The primary statistic is twice the improvement from fitting h and beta over
fitting beta with h fixed at 1. The rule declares an effect only when every
nodewise plus-one Monte Carlo p-value is at most .05. Its finite-sample
guarantee applies at an exact on-grid null, conditional on the fixed analysis
bank, and averages over reference-table and evaluation-history generation.
It is **not a conditional 5% guarantee for this realised table**, nor a
continuous-beta or misspecification guarantee. The constant-background
comparator is calibrated at beta = 0 alone.

The fixed 2,000-draw bootstrap independently resamples whole reference and
evaluation blocks, preserving pairing across nodes and cells. Intervals below
are calibration-aware 95% percentile intervals unless specified otherwise.
Frozen-table intervals are retained in the evidence. These intervals describe
uncertainty in operating performance, not confidence coverage for ecological h.

## Effect decisions: benefit and cost

All entries are percentages; differences are percentage points. Each cell has
1,000 evaluation histories. Primary and constant intervals and paired contrasts
come from the same registered bootstrap draws.

| Cell | Adjusted primary | Constant-background rule | Adjusted minus constant |
| --- | ---: | ---: | ---: |
| E0, h1 | 4.2 [2.2, 5.5] | 3.5 [2.1, 5.0] | +0.7 [−1.4, 2.0] |
| E0, h3 | 76.1 [70.8, 78.9] | 85.3 [82.1, 88.4] | −9.2 [−14.1, −6.7] |
| E06, h1 | 3.2 [2.0, 4.5] | 17.1 [14.4, 20.8] | −13.9 [−17.3, −11.4] |
| E06, h3 | 93.0 [89.3, 94.6] | 99.2 [98.5, 99.7] | −6.2 [−9.9, −4.7] |
| B100-A, h1 | 2.5 [1.5, 3.7] | 15.7 [12.8, 19.1] | −13.2 [−16.3, −10.6] |
| B100-A, h3 | 87.5 [82.9, 89.5] | 97.4 [96.0, 98.3] | −9.9 [−14.0, −8.0] |
| N100-A, h1 | 2.8 [1.5, 3.9] | 14.7 [11.9, 18.4] | −11.9 [−15.6, −9.4] |
| N100-A, h3 | 86.2 [81.9, 88.2] | 98.1 [97.1, 98.9] | −11.9 [−16.0, −10.1] |

Under the exact nonconstant null, adjustment removes 13.9 points of false
declarations while losing 6.2 points of threefold-effect sensitivity. Under
constant background, it costs 9.2 points of sensitivity. High sensitivity of
the constant rule under nonconstant backgrounds must be read beside its
inflated false-declaration rate. The two residual-field families show similar
protection, but their h1 rates are descriptive misspecification operating
rates without nominal size guarantees.

The added nonlinear case does not expose a failure boundary: N100-A minus
B100-A at h1 is +0.3 points [−0.9, 1.3]. This unresolved contrast neither
establishes equivalence nor warrants another stress campaign to obtain a
failure. The comparison also changes realised alignment and hazard variation,
so it cannot isolate a causal effect of field shape alone.

The [report figure](../../../artifacts/goal054_execution/report/calibration_tradeoff.png)
separates null and threefold results and displays the full cutoff curve.
Its [PDF](../../../artifacts/goal054_execution/report/calibration_tradeoff.pdf)
is suitable for inspection or export. It uses frozen evidence and existing
draws; the original synthesis figures remain unchanged.

## Cutoff curve, Berger–Boos and textbook benchmarks

The primary cutoff is **3.46649**, uniquely set by the interior node
**beta = .55**. Nodewise cutoffs range from 1.58021 to 3.46649; the extreme
slopes do not set the maximum. The constant-rule cutoff is 3.04816. Thus the
suggested concern that extreme slopes would dominate conservatism was not
realised here. Boundary contributors to tied max-p values are a different
diagnostic and do not identify the cutoff-setting node.

The secondary Berger–Boos rule uses gamma = .01 and the registered Monte Carlo
candidate set. Mean set sizes are 38–40 nodes at h1 and 25–29 at h3; none is
empty. Every observed Berger–Boos declaration is also a primary declaration.
It recovers no sensitivity: threefold rates fall by 2.2–2.7 points. In the two
exact-null evaluation cells, the true beta is excluded from the candidate set
in 1.7% and 1.2% of histories. These realised-table frequencies illustrate why
the gamma guarantee must be stated over reference and evaluation generation.

The prespecified fixed-cutoff benchmarks are reported below, without selecting
a replacement rule from their observed performance. Entries are percentages.

| Cell | Berger–Boos | Adjusted 2.71 | Adjusted 3.84 | Constant 2.71 | Constant 3.84 |
| --- | ---: | ---: | ---: | ---: | ---: |
| E0, h1 | 2.9 | 6.3 | 3.2 | 4.3 | 2.1 |
| E0, h3 | 73.5 | 82.1 | 73.9 | 87.4 | 81.4 |
| E06, h1 | 2.9 | 5.0 | 2.9 | 19.0 | 13.3 |
| E06, h3 | 90.8 | 94.6 | 91.1 | 99.4 | 98.7 |
| B100-A, h1 | 2.2 | 4.8 | 2.2 | 17.9 | 11.0 |
| B100-A, h3 | 84.8 | 91.4 | 85.0 | 97.7 | 96.1 |
| N100-A, h1 | 2.1 | 4.6 | 2.2 | 17.5 | 10.4 |
| N100-A, h3 | 83.7 | 90.6 | 84.3 | 98.3 | 96.4 |

The adjusted 2.71 benchmark gives higher sensitivity and 6.3% null declarations
at beta = 0; 3.84 gives lower sensitivity and low null rates in these cells.
This is a design-specific comparison, not general asymptotic validation or a
simulation-free recommendation. The complete
[rates table](../../../artifacts/goal054_execution/synthesis/rule_rates.csv)
retains intervals for all seven rules. Fixed-cutoff intervals involve evaluation
uncertainty only, so their narrower width is not an inferential advantage over
calibrated rules. The full
[cutoff table](../../../artifacts/goal054_execution/synthesis/cutoff_curve.csv)
retains all 81 slopes and the candidate-set cutoffs.

## Magnitude estimation and held-out prediction

Calibration of a declaration leaves the estimation trade-off intact. Mean
absolute log error is higher after adjustment under constant background and
lower in all six nonconstant cells. Paired adjusted-minus-constant intervals
exclude zero in all eight cells. The following rates concern unconditional
point errors of at least 1.5-fold, with 1,000 histories per entry.

| Cell | Adjusted error rate | Constant error rate | Difference, percentage points |
| --- | ---: | ---: | ---: |
| E0, h1 | 30.2% | 18.3% | +11.9 [9.1, 14.7] |
| E0, h3 | 33.1% | 19.4% | +13.7 [10.9, 16.8] |
| E06, h1 | 20.2% | 47.1% | −26.9 [−29.9, −23.7] |
| E06, h3 | 15.2% | 35.4% | −20.2 [−23.5, −16.8] |
| B100-A, h1 | 20.2% | 43.1% | −22.9 [−25.9, −19.9] |
| B100-A, h3 | 19.8% | 27.2% | −7.4 [−10.9, −3.7] |
| N100-A, h1 | 19.8% | 43.4% | −23.6 [−26.7, −20.5] |
| N100-A, h3 | 18.7% | 24.3% | −5.6 [−9.2, −2.0] |

Declared-subset summaries below pair each rule with its registered estimator.
Every percentage in the last column uses the full 1,000-history denominator;
the selected-error column uses the stated declaration count.

| h3 background | Primary declarations | Large error among declarations | Joint declaration and large error |
| --- | ---: | ---: | ---: |
| E0 | 761 | 21.9% | 16.7% |
| E06 | 930 | 9.5% | 8.8% |
| B100-A | 875 | 10.1% | 8.8% |
| N100-A | 862 | 7.0% | 6.0% |

Among the 761 E0/h3 declarations, mean signed log error is .1571, corresponding
to about **17% geometric-mean overestimation**. At h1, all 42, 32, 25 and 28
primary declarations respectively have at least 1.5-fold point error. No
declared-subset bootstrap denominator is undefined in this run. The full
[error table](../../../artifacts/goal054_execution/synthesis/error_metrics.csv)
also contains cross-product estimator/rule diagnostics; only adjusted estimates
with adjusted rules, and constant estimates with constant rules, support the
registered selected-subset claims.

Direct held-out adjusted-minus-constant log-score differences at h3 are
−.131 [−.170, −.095] under E0, +.286 [.213, .359] under E06,
+.196 [.110, .276] under B100-A and +.431 [.348, .511] under N100-A.
At h1 the E06 and B100-A differences remain unresolved; E0 favours the
constant model and N100-A favours adjustment. The adjusted model outperforms
its separately fitted adjusted neutral at all four h3 truths. Its h1
advantages over that neutral are negative. Neutral comparisons and direct
background-model comparisons remain separate quantities; neither supplies a
confidence guarantee for h. See
[prediction_metrics.csv](../../../artifacts/goal054_execution/synthesis/prediction_metrics.csv).

## Realised fields and registered predictions

The field construction holds the map mean hazard at .002. Normalisation and
alignment do not fix the realised CV, sample means or fitted-shape mismatch.
Means across the 1,000 paired fields are:

| Background | Map hazard CV | Hazard–A correlation | Training mean hazard | Holdout mean hazard | Affine-A log-hazard residual RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| E0 | 0 | Undefined | .0020000 | .0020000 | 0 |
| E06 | .663 | .931 | .0020858 | .0019054 | 0 |
| B100-A | .947 | .627 | .0020885 | .0019117 | .561 |
| N100-A | .941 | .527 | .0020220 | .0019089 | .664 |

The nonlinear indicator selects 2,015 of 6,048 habitat cells; the strict
threshold keeps tied A values together. Its larger residual RMSE verifies
departure from the fitted shape, while its lower correlation and changed
training mean qualify comparisons with B100-A. Field SDs, ranges, sample
diagnostics and undefined values are retained in
[field_summary.csv](../../../artifacts/goal054_execution/report/field_summary.csv).
These across-field ranges describe realised generators, not uncertainty in
an estimated ecological relationship.

Four registered forecasts have calibration-aware intervals wholly supporting
them: E06/h1 in 2–5%, E0/h3 in 65–80%, E06/h3 at least 88%, and B100-A/h1
adjusted at most 6%. Three remain unresolved by those intervals. E0/h1 meets
the 2–5% forecast at its point estimate but its interval reaches 5.5%.
The constant B100-A/h1 forecast of at least 18% **fails at the 15.7% point
estimate**, although its interval overlaps 18%. The forecast that nonlinear
h1 exceeds B100-A is met by only +0.3 points, with an interval crossing zero.
No forecast is interval-refuted. Forecast status does not determine completion,
and the pointwise miss remains visible.

## Verification, limits and decision

Production took 11,139 receipt seconds; the single fixed synthesis took 42.
The controller verified 168 production outputs and 11 synthesis outputs,
including unchanged source, input, helper and bank bindings. Independent
raw-score reconstruction was exact for 12 reference and 24 evaluation histories
across all 81 rows. A separate reviewer reproduced all seven rules, all 56
rule rates, all 56 registered estimator/rule selected-subset rows, and six
registered bootstrap draws with maximum discrepancy zero. The
[completed check](../../../artifacts/goal054_execution/completed-check.json)
indexes the receipts; authenticated bulk score arrays remain on deep-server.

The remaining limits are substantive: one landscape and survey, known
nuisances, finite parameter grids and a fixed regularised integration bank;
fresh exact-null evaluation at two beta nodes rather than all 81; uncertainty
in the reference table; and two particular misspecification fields. There is
no new confidence support, continuous-nuisance validity, empirical application,
or general model-selection result. Earlier numerical failures have not been
retrospectively passed.

Freeze the primary rule and this evidence. The independent review recommends
no repair or rerun. The
[next-tranche proposal](next-tranche-proposal.md) consolidates Arc 4's scientific
claims and designs one capstone for review, before any further simulation or
scope expansion. Effect declaration is now a demonstrated conditional
capability; accurate magnitude estimation and recognition of incorrect
structure remain separate obligations.
