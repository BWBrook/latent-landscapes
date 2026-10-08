# Goal 055: nuisance checks and Arc 4 synthesis

2 October 2026 (Hobart). **Both registered nuisance checks identify a transfer
failure.** The approved archive checks are verified. They select pre-invasion
monitoring for capstone development and require a prey-observation-model
repair before that capstone can claim calibrated effects. The completed
scope is synthesis and design; no capstone truth or observations were drawn.

At a supplied mean of .0016/day, 80% of truth, adjusted null declarations are
7.8% [5.3, 9.5] under E0 and 10.8% [7.1, 12.8] under E06. Both lower limits
exceed 5%, triggering the registered wrong-mean failure predicate. Under
site-specific prey-detection SD .20, adjusted null declarations are 19.8%
[15.2, 22.1], versus 3.8% in the paired baseline: +16.0 percentage points
[12.1, 17.8]. Both the absolute and paired detection predicates trigger.
These are pointwise bootstrap intervals, not simultaneous bounds or a new
validity theorem.

## Design and interpretation

The [registration](registration-2026-10-01.md) fixed all conditions before new
scoring. Goal 054's 1,000 E0/E06 blocks at h=1/3 were refitted at supplied mean
hazards .0016 and .0025/day, keeping true mean .002/day and observations fixed.
Four correct-mean columns were reused after exact replay. Goal 051's 1,000
D20 h=1/3 blocks and their matched B controls were recovered from the original
seeds and authenticated against all 4,000 selected identities and full
constant-model profiles. The 12,000 new condition fits concern 8,000 unique
archived histories; they are not 12,000 new simulation replicates.

The H181 by beta81 rectangle, 120/40 training/holdout split, six occasions,
two visits, supplied spread and detection, and K131072/alpha1 bank remain
fixed. The reference contains 999 blocks at each beta node. The frozen
full-supremum adjusted rule remains primary, with the frozen constant-beta0
rule as its comparator. Their cutoffs are 3.4664939261706422 and
3.0481613698225374. No calibration was replaced or adopted.

These retrospectively selected checks estimate operating behaviour of the
frozen procedure under deliberately wrong inputs or an omitted observation
process. They cannot confirm Goal 051's selected nominee, validate a random
external estimate, establish unknown-nuisance inference, or inherit nominal
size under misspecification. Higher h3 declaration rates under a departure
are not an unqualified gain in power when null protection is lost.

Exactly 2,000 draws, seed 2026100105, used separate reference, Goal 054 and
Goal 051 resampling streams. Reference indices were shared across all 81 beta
nodes; evaluation indices were shared within each archive, never across the
two archives. Frozen intervals resample evaluation histories only;
calibration-aware intervals also resample the original reference table. All
intervals below are pointwise 95% percentile intervals. Correct-mean point
estimates are unchanged from Goal 054; their Goal 055 intervals differ slightly
because this registration uses a new fixed bootstrap stream for the paired
checks. The original Goal 054 report remains frozen.

## Declarations and paired changes

Every cell has 1,000 complete histories. `M080`, `M100` and `M125` denote the
supplied/true mean ratio; E0 and E06 have generating beta0 and .60. `S051`
identifies the separate Goal 051 archive, with B the matched baseline.
At h1 these are false-declaration rates; at h3 they are declaration/sensitivity
rates under the stated generator and supplied inputs.

| Cell | Adjusted % | Frozen 95% | Cal-aware 95% | Constant % | Frozen 95% | Cal-aware 95% |
| --- | --- | --- | --- | --- | --- | --- |
| M080_E0_h1 | 7.8 | [6.1, 9.5] | [5.3, 9.5] | 8.8 | [6.9, 10.6] | [6.5, 11.2] |
| M100_E0_h1 | 4.2 | [3.0, 5.4] | [2.1, 5.4] | 3.5 | [2.4, 4.7] | [2.0, 5.0] |
| M125_E0_h1 | 1.5 | [0.8, 2.3] | [0.7, 2.3] | 0.9 | [0.4, 1.5] | [0.4, 1.6] |
| M080_E0_h3 | 88.7 | [86.6, 90.5] | [84.1, 90.4] | 93.3 | [91.7, 94.8] | [91.4, 95.0] |
| M100_E0_h3 | 76.1 | [73.4, 78.7] | [70.6, 78.8] | 85.3 | [82.9, 87.4] | [81.7, 88.2] |
| M125_E0_h3 | 54.8 | [51.8, 57.9] | [46.5, 57.9] | 74.0 | [71.2, 76.7] | [69.9, 77.9] |
| M080_E06_h1 | 10.8 | [8.7, 12.8] | [7.1, 12.8] | 32.7 | [29.7, 35.7] | [28.2, 37.2] |
| M100_E06_h1 | 3.2 | [2.1, 4.3] | [2.0, 4.4] | 17.1 | [14.7, 19.5] | [14.3, 20.2] |
| M125_E06_h1 | 1.2 | [0.6, 1.9] | [0.5, 1.9] | 6.4 | [4.7, 8.0] | [4.3, 9.0] |
| M080_E06_h3 | 97.4 | [96.4, 98.3] | [95.9, 98.3] | 99.7 | [99.3, 100.0] | [99.3, 100.0] |
| M100_E06_h3 | 93.0 | [91.3, 94.5] | [89.2, 94.4] | 99.2 | [98.6, 99.7] | [98.5, 99.7] |
| M125_E06_h3 | 78.1 | [75.5, 80.6] | [73.7, 81.0] | 97.5 | [96.5, 98.4] | [96.4, 98.5] |
| S051_B_h1 | 3.8 | [2.7, 5.0] | [2.2, 5.1] | 3.6 | [2.5, 4.8] | [2.0, 5.1] |
| S051_D20_h1 | 19.8 | [17.5, 22.2] | [15.2, 22.1] | 20.8 | [18.3, 23.3] | [15.8, 24.2] |
| S051_B_h3 | 77.2 | [74.7, 79.9] | [71.7, 80.2] | 88.1 | [86.1, 90.2] | [85.5, 90.8] |
| S051_D20_h3 | 92.1 | [90.4, 93.8] | [89.2, 93.7] | 96.2 | [95.0, 97.3] | [94.7, 97.5] |

All paired differences use the same histories within an archive. Entries
below are percentage points; the two interval columns retain evaluation-only
and reference-table uncertainty separately.

| Paired contrast | Adjusted points | Frozen 95% | Cal-aware 95% | Constant points | Frozen 95% | Cal-aware 95% |
| --- | --- | --- | --- | --- | --- | --- |
| M080_E0_h1 minus M100_E0_h1 | 3.6 | [2.5, 4.8] | [2.4, 4.9] | 5.3 | [3.8, 6.8] | [3.8, 7.0] |
| M080_E0_h3 minus M100_E0_h3 | 12.6 | [10.6, 14.7] | [10.4, 14.8] | 8.0 | [6.3, 9.7] | [5.9, 10.5] |
| M080_E06_h1 minus M100_E06_h1 | 7.6 | [6.0, 9.4] | [4.5, 9.2] | 15.6 | [13.4, 18.0] | [12.8, 18.3] |
| M080_E06_h3 minus M100_E06_h3 | 4.4 | [3.2, 5.7] | [3.3, 7.2] | 0.5 | [0.1, 0.9] | [0.1, 1.1] |
| M125_E0_h1 minus M100_E0_h1 | -2.7 | [-3.8, -1.7] | [-3.6, -1.1] | -2.6 | [-3.6, -1.7] | [-3.8, -1.3] |
| M125_E0_h3 minus M100_E0_h3 | -21.3 | [-23.8, -18.6] | [-25.5, -19.3] | -11.3 | [-13.3, -9.4] | [-13.3, -9.2] |
| M125_E06_h1 minus M100_E06_h1 | -2.0 | [-2.9, -1.2] | [-3.0, -1.1] | -10.7 | [-12.5, -8.8] | [-12.7, -8.8] |
| M125_E06_h3 minus M100_E06_h3 | -14.9 | [-17.2, -12.7] | [-17.4, -12.5] | -1.7 | [-2.5, -0.9] | [-2.6, -0.9] |
| S051_D20_h1 minus S051_B_h1 | 16.0 | [13.7, 18.4] | [12.1, 17.8] | 17.2 | [14.8, 19.7] | [13.3, 19.9] |
| S051_D20_h3 minus S051_B_h3 | 14.9 | [12.5, 17.3] | [12.6, 18.6] | 8.1 | [6.3, 9.8] | [6.0, 10.1] |

Underestimating the mean raises primary null declarations by 3.6 points in
E0 and 7.6 points in E06. Fitting beta therefore does not absorb the supplied
mean error sufficiently to protect the decision. Overestimating the mean
reduces null rates to 1.5% and 1.2%, but lowers h3 declarations from 76.1% to 54.8%
and from 93.0% to 78.1%. Its apparently conservative null behaviour is not
robustness across the two supplied values or evidence of an unbiased estimate.

D20 raises adjusted declarations at both truths, including h3 from 77.2% to
92.1%. The adjusted null lower limit 15.2% exceeds 5%, and the paired contrast
lower limit 12.1 points exceeds zero. These are two distinct failures, both
present here. Spatial background adjustment alone does not repair the omitted
site-level detection heterogeneity.

The [complete rule table](../../../artifacts/goal055_execution/synthesis/output/rule_rates.csv)
retains all seven rules and both interval types. Berger--Boos null rates are
6.6% and 8.5% in the two low-mean cells and 17.1% for D20. The fixed 2.71/3.84
comparisons remain descriptive; none replaces the primary rule after these
results. [Within-cell adjusted-minus-constant contrasts](../../../artifacts/goal055_execution/synthesis/output/paired_rule_contrasts.csv)
and [candidate-set diagnostics](../../../artifacts/goal055_execution/synthesis/output/rule_diagnostics.csv)
are retained separately.

## Magnitude and prediction

A and C below denote the matching adjusted and constant estimators. Signed
error is mean log(h-hat/h); absolute error is its mean absolute value. Large
error means abs(log(h-hat/h)) >= log(1.5). Every denominator is all 1,000
histories; these are not summaries conditioned on a declaration. The final
column is the direct difference between training-fitted models' held-out
scores, **total nats across 40 sites**. The common predator marginal cancels.
Divide both estimate and interval endpoints by 40 to express nats/site.

| Cell | Signed log error A / C | Mean absolute log error A / C | At least 1.5-fold error % A / C | A minus C holdout, total nats [95%] |
| --- | --- | --- | --- | --- |
| M080_E0_h1 | 0.457 / 0.296 | 0.457 / 0.296 | 46.5 / 35.4 | -0.216 [-0.270, -0.162] |
| M100_E0_h1 | 0.299 / 0.158 | 0.299 / 0.158 | 30.2 / 18.3 | -0.227 [-0.287, -0.170] |
| M125_E0_h1 | 0.205 / 0.068 | 0.205 / 0.068 | 20.2 / 5.8 | -0.219 [-0.287, -0.155] |
| M080_E0_h3 | 0.266 / 0.188 | 0.392 / 0.304 | 42.8 / 28.9 | -0.125 [-0.160, -0.092] |
| M100_E0_h3 | -0.002 / -0.050 | 0.324 / 0.240 | 33.1 / 19.4 | -0.131 [-0.170, -0.093] |
| M125_E0_h3 | -0.275 / -0.288 | 0.405 / 0.329 | 43.8 / 32.8 | -0.126 [-0.170, -0.084] |
| M080_E06_h1 | 0.372 / 0.582 | 0.372 / 0.582 | 43.5 / 69.0 | -0.032 [-0.094, 0.026] |
| M100_E06_h1 | 0.196 / 0.375 | 0.196 / 0.375 | 20.2 / 47.1 | 0.024 [-0.047, 0.091] |
| M125_E06_h1 | 0.088 / 0.204 | 0.088 / 0.204 | 6.9 / 22.6 | 0.094 [0.015, 0.171] |
| M080_E06_h3 | 0.261 / 0.527 | 0.323 / 0.533 | 34.1 / 72.5 | 0.209 [0.139, 0.272] |
| M100_E06_h3 | 0.003 / 0.292 | 0.229 / 0.327 | 15.2 / 35.4 | 0.286 [0.209, 0.355] |
| M125_E06_h3 | -0.260 / 0.057 | 0.314 / 0.201 | 31.2 / 10.9 | 0.405 [0.321, 0.482] |
| S051_B_h1 | 0.313 / 0.167 | 0.313 / 0.167 | 30.8 / 19.7 | -0.191 [-0.247, -0.140] |
| S051_D20_h1 | 0.631 / 0.417 | 0.631 / 0.417 | 64.8 / 52.0 | -0.142 [-0.185, -0.102] |
| S051_B_h3 | 0.013 / -0.034 | 0.320 / 0.230 | 31.2 / 16.5 | -0.119 [-0.155, -0.084] |
| S051_D20_h3 | 0.234 / 0.135 | 0.345 / 0.248 | 35.9 / 19.0 | -0.093 [-0.128, -0.061] |

Both wrong means worsen adjusted h3 mean absolute log error in E0 and E06,
even though their declaration-rate changes have opposite signs. Low-mean
adjusted signed errors are +.266 and+.261; high-mean errors are -.275 and-.260,
compared with -.002 and+.003 at the correct mean. D20 increases adjusted h1
large-error frequency from 30.8% to 64.8%, a paired change of 34.0 points
[30.9,37.1], and h3 from 31.2% to 35.9%, +4.7 points [1.2,8.1]. Declaration,
magnitude recovery and prediction remain distinct endpoints.

Held-out scores favour the constant fit in all E0 and Goal 051 B/D20 cells on
average. Under D20 the adjusted-minus-constant means are -.142 and-.093 total
nats (about -.00354 and-.00233 nats/site), while both procedures lose null
protection. Under E06, h3 mean differences favour adjustment at all three
supplied means; the low-mean h1 contrast is unresolved. In the high-mean E06
h3 cell, adjustment improves average prediction yet has greater magnitude
error than the constant fit (.314 versus .201). These within-landscape
comparisons do not establish reliable model discrimination from one history.

The [17 metric families](../../../artifacts/goal055_execution/synthesis/output/metrics.csv)
include intervals for every entry, both fitted-null predictive comparisons,
and all boundary diagnostics. The [170 paired metric contrasts](../../../artifacts/goal055_execution/synthesis/output/paired_metric_contrasts.csv)
retain corresponding changes and their registered intervals.

## Fitted background and boundaries

The following diagnostics expose the fitted trade-offs rather than explaining
them away. A beta edge is either -2 or+2. The h lower boundary is the physical
null, so nonnegative null log error is partly imposed by the fitted domain.
No result triggered a wider grid or another fit.

| Cell | Mean beta, free-h / null | Beta edge %, free-h / null | h=1 %, A / C | h=10 %, A / C |
| --- | --- | --- | --- | --- |
| M080_E0_h1 | -0.185 / -0.001 | 0.6 / 0.3 | 34.4 / 39.1 | 0.2 / 0.0 |
| M100_E0_h1 | -0.199 / -0.061 | 1.1 / 0.4 | 50.7 / 55.4 | 0.1 / 0.0 |
| M125_E0_h1 | -0.256 / -0.148 | 2.1 / 1.1 | 65.5 / 73.7 | 0.0 / 0.0 |
| M080_E0_h3 | -0.047 / 0.425 | 0.1 / 0.0 | 0.2 / 0.4 | 0.8 / 0.0 |
| M100_E0_h3 | -0.003 / 0.417 | 0.1 / 0.0 | 1.2 / 0.6 | 0.1 / 0.0 |
| M125_E0_h3 | 0.054 / 0.407 | 0.1 / 0.0 | 4.8 / 2.4 | 0.0 / 0.0 |
| M080_E06_h1 | 0.479 / 0.602 | 0.7 / 0.6 | 29.2 / 12.7 | 0.0 / 0.0 |
| M100_E06_h1 | 0.534 / 0.610 | 1.7 / 1.5 | 50.7 / 23.2 | 0.0 / 0.0 |
| M125_E06_h1 | 0.569 / 0.612 | 3.1 / 2.4 | 74.3 / 43.2 | 0.0 / 0.0 |
| M080_E06_h3 | 0.568 / 0.863 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.2 |
| M100_E06_h3 | 0.628 / 0.875 | 0.0 / 0.0 | 0.2 / 0.0 | 0.0 / 0.0 |
| M125_E06_h3 | 0.703 / 0.896 | 0.2 / 0.1 | 0.6 / 0.0 | 0.0 / 0.0 |
| S051_B_h1 | -0.185 / -0.041 | 1.0 / 0.3 | 48.9 / 54.4 | 0.3 / 0.0 |
| S051_D20_h1 | -0.210 / 0.042 | 0.1 / 0.0 | 17.4 / 21.5 | 0.1 / 0.0 |
| S051_B_h3 | -0.003 / 0.420 | 0.0 / 0.0 | 0.7 / 0.2 | 0.4 / 0.0 |
| S051_D20_h3 | -0.084 / 0.374 | 0.0 / 0.0 | 0.1 / 0.0 | 0.5 / 0.0 |

The paired beta changes under each perturbation are:

| Paired contrast | Change in mean fitted beta [95%] |
| --- | --- |
| M080_E0_h1 minus M100_E0_h1 | +0.0136 [0.0075, 0.0199] |
| M080_E0_h3 minus M100_E0_h3 | -0.0436 [-0.0462, -0.0409] |
| M080_E06_h1 minus M100_E06_h1 | -0.0554 [-0.0645, -0.0457] |
| M080_E06_h3 minus M100_E06_h3 | -0.0598 [-0.0615, -0.0582] |
| M125_E0_h1 minus M100_E0_h1 | -0.0571 [-0.0675, -0.0473] |
| M125_E0_h3 minus M100_E0_h3 | +0.0577 [0.0545, 0.0610] |
| M125_E06_h1 minus M100_E06_h1 | +0.0347 [0.0223, 0.0460] |
| M125_E06_h3 minus M100_E06_h3 | +0.0754 [0.0735, 0.0773] |
| S051_D20_h1 minus S051_B_h1 | -0.0255 [-0.0453, -0.0041] |
| S051_D20_h3 minus S051_B_h3 | -0.0815 [-0.0928, -0.0688] |

Fitted beta moves when the supplied mean changes, but the direction depends
on the truth and boundary geometry. The remaining h bias and false declarations
rule out claiming a successful nuisance-error repair. Beta-edge contacts reach
3.1% and adjusted upper-h contacts reach 0.8% in these cells; small edge rates
do not establish exact integration accuracy or remove the inherited bank limits.

## Forecasts and the selected capstone branch

Fable's 8--10% forecast for the low-mean E0 constant null is met pointwise at
8.8%; its calibration-aware interval [6.5,11.2] extends beyond that range, so
interval support is unresolved. The D20 adjusted-null forecast of at least 12%
is met at 19.8%, and its interval [15.2,22.1] supports the threshold. This is a
registered prediction about a later rule applied to a previously selected
archive departure, not independent confirmation of the original screen.

The wrong-mean failure selects **60 days of pre-invasion monitoring** as the
proposed information branch. The detection failures make a model for persistent
site-specific prey detection a prerequisite. Neither result demonstrates that
extra surveys or a Beta mixture will solve the problem; they determine what
must be developed and qualified next. The [capstone protocol](capstone-protocol.md)
specifies one new connected landscape,13 prey occasions and 4,160 site-visits,
unknown map mean, the four information-matched fitted models, genuine Fable-held
truth and separate training, holdout and reveal locks.

The smallest proposed next tranche is observed-data likelihood feasibility for
unknown mean, the pre-invasion calendar and shared-across-visits detection
heterogeneity, using openly labelled fixtures and a measured full-dimensional
timing panel. It precedes a separately registered calibration and any sealed
truth draw. Additional effort is 2,240 prey site-visits; predator effort is
unchanged. Goal 055's 6 h 22 min production time anchors existing components only and
cannot cost new nuisance dimensions by simple scaling. The protocol states
the bounded preparation and timing gate; implementation and new calibration
remain outside this completed scope.

## Verification and Arc 4 claims

Production exited zero at 2026-10-01 20:57:14UTC after 6 h 22 min 05 s by its receipts,
within the 9 h 55 min timeout. The single synthesis exited zero at 21:04:14UTC after
33 receipt seconds. All 169 production outputs and 10 synthesis outputs passed
hash verification. The independent full-rectangle reduction reproduces all 10
statistic arrays exactly. A separate implementation reproduces all 32,000
primary/constant point decisions, all 2,000 frozen and calibration-aware rate
draws, and 544,000 metric-draw values exactly; it also verifies archive pairing,
intervals, contrasts, forecasts and both design predicates. The independent
[result/claim review](final-review.md) adds all-seven-rule point-decision and
candidate-set checks. This verifies execution, not the truth of a broader
scientific model.

All 97 bound files and 89 predecessor source identities remain unchanged.
The failed first wrapper attempt remains archived; its three mechanical repairs
and subsequent qualification are explicit in the [execution record](execution.md).
The compact evidence is local; all 81 bulk raw score arrays remain authenticated
at the preserved remote root. The [completion receipt](../../../artifacts/goal055_execution/completed-check.json)
indexes the finished package.

The [claim matrix](claims-audit.md), [paper draft](arc4-draft.md) and three
[figures and captions](figure-captions.md) consolidate the separate experiments.
The new [archive-check figure](../../../artifacts/goal055_execution/synthesis/output/nuisance_checks.png)
([PDF](../../../artifacts/goal055_execution/synthesis/output/nuisance_checks.pdf))
was inspected in both formats and is linked to its exact plotted source rows.
Goals 049--054 and earlier negative numerical results remain frozen.

Arc 4 now shows that protection of an effect declaration is conditional on its
nuisance and observation assumptions; it cannot be inferred merely from a
favourable spatial-background check. Magnitude error and weak per-history model
discrimination remain. Pillar 4 is not complete under its prespecified
competing-model requirement, and Pillar 5 has not been run. Fable critiques the
completed package before Barry's next scientific decision.
