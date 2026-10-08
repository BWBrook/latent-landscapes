# Arc 4 draft: detection, declaration and magnitude under background misspecification

2 October 2026 (Hobart). This manuscript-oriented synthesis uses frozen
Goals 049--054 and the separately registered Goal 055 archive checks. It is a
research draft; the experiments retain their own estimands and uncertainty.

## Results

### An assumed-model adequacy check did not protect effect estimation uniformly

The held-out conditional prey-score detector was conservative when data were
generated under the fitted model. It rejected 19 of 1,000 fresh null histories
(1.9%, calibration-aware 95% interval 1.1--3.2%) and 0.4--2.4% across six
retrospective assumed-model truths. These rows estimate false rejection, not
power against alternative generators. The detector also answered a different
question from effect-set exclusion: in the crossed null check, the four
effect-set exclusion counts were 74, 57, 69 and 48 per 1,000, and all paired
contrast intervals included zero ([Goal 050](../050-model-adequacy/synthesis.md)).

The registered misspecification screen then showed that low baseline rejection
did not imply low power against every departure, or safety following a
non-rejection. Spatial background loss aligned with invasion exposure at a
physical null (B100-A_h1) increased the compound hidden-failure rate from
19.3% to 42.3%, a paired difference of 23.0 percentage points [19.9, 25.9],
while the detector rejected only 2.7% of histories. Strict false effects rose
from 6.3% to 21.6%, and 21.2% of all histories contained an unflagged strict
false effect. At h=3, the same construction increased mean fitted h from 3.020
to 3.871 and truth exclusion from 5.0% to 16.3%. This was a conditional
generator--analysis vulnerability, not confirmation of the selected B100-A_h1
nominee or a general model-discrimination result ([Goal 051](../051-misspecification-screen/synthesis.md)).

Prey-detection heterogeneity at site SD 0.20 produced a different pattern. The
detector rejected 27.0%, 21.9% and 16.4% of histories at h=1,3,5, showing that
the discrepancy was observable under this survey. Yet at h=1 its compound
misleading-estimate event reached 52.0%, and its unflagged strict false-effect
rate was also 21.2%. The original forecasts of downward D20 bias at h=3/5 and
less than a three-point increase in null truth exclusion were contradicted.
The departure therefore changed both effect estimation and absolute fit, but
detector response remained incomplete.

### Spatial adjustment exchanged bias protection for flexibility

A 24-history retrospective pilot showed that fitting a background coefficient
was computationally feasible but did not establish a repair. Under aligned
background variation, adjustment moved mean fitted h from 1.225 to 1.083 at
the null, but at h=3 moved 3.633 to 2.750 while mean absolute log error worsened
from 0.310 to 0.402. Adjustment improved direct held-out score in only two of
six aligned-null and three of six aligned-threefold histories. Likelihood
surfaces retained broad h--beta trade-offs, and supplying true arrivals
narrowed h profiles in only 12 of 24 histories ([Goal 052](../052-adjusted-background-pilot/synthesis.md)).

The subsequent 1,000-block prospective comparison resolved the average
estimation direction. Under constant background, adjustment increased mean
absolute log error from 0.1505 to 0.3092 at h=1 and from 0.2281 to 0.3254 at
h=3. Under an exact nonconstant background (beta=.60), it reduced error from
0.3689 to 0.1925 and from 0.3205 to 0.2123; under B100-A, it reduced error from
0.3395 to 0.1872 and from 0.2911 to 0.2445. All six paired directions were
resolved by the registered bootstrap. The adjustment was therefore useful
conditional on nonconstant background structure and costly when that
flexibility was unnecessary. It did not recover the omitted residual field,
and considerable individual-history error remained ([Goal 053](../053-prospective-background/synthesis.md)).

Held-out prediction only partly discriminated the background models. The
adjusted model was favoured on average under exact beta=.60, but won by the
registered sign rule in only 59.2% of null and 64.8% of threefold histories.
Its mean advantage under B100-A at h=1 was unresolved. Conversely, constant
background was favoured under beta=0. The forecast adjusted advantage of
0.01--0.025 nats per holdout site failed in both exact beta=.60 cells. Thus
held-out scores contained information about background structure without
reliably identifying it in a single history, and predictive preference did not
guarantee accurate h.

### A calibrated declaration was possible, but it did not calibrate magnitude

Goal 054 calibrated the adjusted statistic over all 81 beta nodes
using 999 reference blocks per node, then evaluated eight cells in 1,000 paired blocks
generated independently of the reference. The full-supremum rule declared an effect in
4.2% [2.2, 5.5] of exact beta=0 null histories and 3.2% [2.0, 4.5] of exact
beta=.60 null histories, while declaring 76.1% [70.8, 78.9] and 93.0%
[89.3, 94.6] of their h=3 counterparts. Relative to the beta=0 constant rule,
estimating beta cost 9.2 percentage points of sensitivity when background was
constant. Under beta=.60 it reduced false declarations by 13.9 points while
costing 6.2 points of sensitivity. The operative cutoff was 3.46649 and was
set by the interior beta=.55 node, rather than by an extreme slope
([Goal 054](../054-null-effect-calibration/synthesis.md)).

The two out-of-family residual-field stresses showed the same qualitative
protection, with adjusted h=1 declaration rates of 2.5% for B100-A and 2.8%
for N100-A and h=3 rates of 87.5% and 86.2%. These are descriptive operating
rates without nominal size guarantees. The nonlinear-minus-linear null
contrast was only +0.3 points [-0.9, 1.3], so the additional shape did not
locate a robustness boundary and did not establish equivalence. The registered
forecast that the constant B100-A null rate would be at least 18% failed at
the 15.7% point estimate, although its interval overlapped 18%.

The Berger--Boos refinement recovered no sensitivity. Every declaration was a
subset of the primary rule, and threefold declaration rates fell by another
2.2--2.7 points. This negative result was retained rather than used to tune the
candidate set or gamma.

Calibrated declaration and magnitude recovery remained
separate. Adjustment increased the probability of at least 1.5-fold point
error under constant background from 18.3% to 30.2% at h=1 and from 19.4% to
33.1% at h=3. Among h=3 histories declared by the adjusted rule, 21.9% of E0,
9.5% of E06, 10.1% of B100-A and 7.0% of N100-A declarations had at least
1.5-fold point error. Among the 761 E0 h=3 declarations, mean signed log error
corresponded to about 17% geometric-mean overestimation. Calibration protected
a binary effect decision under its specified null; it did not make the fitted
effect an accurate ecological magnitude.

### Nuisance error broke transfer of the frozen declaration rule

The declaration result depended on receiving the true scalar whole-map mean
background hazard. In a registered retrospective check, the same 1,000
E0/E06 evaluation blocks at h=1/3 were refitted with supplied means .0016 and
.0025/day, respectively .8 and 1.25 times their true .002/day mean. Neither
the observations nor the Goal 054 reference table changed. At the low mean,
adjusted null declarations rose from 4.2% to 7.8% [5.3, 9.5] in E0 and from
3.2% to 10.8% [7.1, 12.8] in E06. Paired increases were 3.6 points [2.4, 4.9]
and 7.6 points [4.5, 9.2]. Both pointwise lower limits exceeded 5%, triggering
the registered failure criterion. At the high mean, null rates fell to 1.5%
and 1.2%, while h3 declarations fell from 76.1% to 54.8% and from 93.0% to
78.1%. The two stress points therefore do not support treating an approximate
supplied mean as known truth ([Goal 055](synthesis.md); Figure 3).

Fitted beta changed with the supplied mean but did not protect h from the
error. At h=3, adjusted signed log errors were +.266 and +.261 under the low
mean, and -.275 and -.260 under the high mean, compared with -.002 and +.003
at the correct mean. Both wrong means worsened adjusted mean absolute log
error. Better average prediction also did not guarantee better magnitude:
with the high mean in E06 h3, adjustment improved held-out score by .405 total
nats over 40 sites [.321, .482], yet its mean absolute log error was .314
versus .201 for the constant fit.

The separate observation check passed archived Goal 051 D20 and matched B
histories through the same frozen Goal 054 rules. Adjusted null declarations
rose from 3.8% [2.2, 5.1] to 19.8% [15.2, 22.1], a paired increase of
16.0 points [12.1, 17.8]. Constant-model declarations rose from 3.6% to
20.8%. Both registered detection prerequisites were met: an absolute null
excess and a positive paired increase. Under D20 h3 the adjusted declaration
rate increased from 77.2% to 92.1%, but this was not a gain in properly
size-controlled power. Adjusted large-error rates also rose, from 30.8% to
64.8% at the null and from 31.2% to 35.9% at h3. Spatial background flexibility
could not repair the omitted persistent site-level observation process.

These checks used 12,000 new condition fits of 8,000 unique archived
histories, with four correct-mean columns reused. Their fixed 2,000-draw
bootstrap resampled the reference, Goal 054 evaluation blocks and Goal 051
blocks independently, preserving within-archive pairing. The quoted
calibration-aware intervals include reference-table uncertainty and are
pointwise. Correct-mean estimates remain unchanged; their intervals use the
new registered bootstrap stream and do not replace the frozen Goal 054 report.
The check is retrospective, and D20 had already been selected as harmful.
It cannot retrospectively make the original screen prospective.

Both registered forecasts were met pointwise. The constant E0 low-mean rate
was 8.8%, within the forecast 8--10%, but its interval [6.5, 11.2] left that
range unresolved. D20's adjusted rate of 19.8% [15.2, 22.1] supported the
forecast of at least 12%. That support concerns a cross-rule prediction on
an existing selected archive, not independent validation.

## Discussion

These experiments separate three questions that are often collapsed. An
adequacy detector asks whether observed holdout behaviour is unusually poor
under a fitted-model reference. A calibrated effect rule asks whether h=1 can
be rejected while protecting a specified long-run error rate. Magnitude
recovery asks whether fitted h is close enough to the generating multiplier to
support ecological interpretation. Arc 4 found no implication from one answer
to the next: a detector could miss substantial error, adjustment could improve
average h while leaving model preference ambiguous, and a calibrated
declaration could coexist with sizeable magnitude error.

The positive result is conditional. With the current landscape,
survey, known registered nuisances, fixed integration bank and finite h--beta
grid, the adjusted full-supremum rule provided a defensible declaration
trade-off at the exact tested null nodes. It materially reduced declarations
from a misspecified constant analysis under nonconstant background. Its cost
was lower sensitivity when beta had to be estimated and worse magnitude
recovery when background was actually constant. The guarantee averages over
reference-table and evaluation-history generation; it is not 5% control
conditional on the realised table, continuous-beta validity, or confidence
coverage for h.

The strongest misspecification result also remains selected and conditional.
B100-A_h1 was nominated from 17 screened cells, and the later experiments did
not rerun its original endpoint and rule as an independent confirmation.
Likewise, Goal 051's detector and Goal 054's decision rule were developed for
different estimands and reference experiments. Their rates should not be
presented as successive measurements from one common experiment. Goal 055
shows how the later rules behave on that frozen observation departure; its
retrospective role and the original selection remain explicit.

The phrase "known background rate" also requires care. The documented
analyses often received a scalar whole-map mean, while site-specific background
hazards and residual spatial structure were deliberately unknown or omitted.
Even with the mean fixed over the map, training and holdout subsets had
different realised means. The paper should therefore name exactly what was
supplied: a whole-map mean, the A proxy, or the full generating rate surface.
In Goal 054 both models received the true whole-map mean, .002/day. Goal 055
showed that the adjusted rule did not protect its nominal null rate when
that supplied mean was 20% too low. This selects 60 days of pre-invasion
monitoring for the proposed capstone, with mean hazard estimated through an
observed-data likelihood. The detection result additionally requires a model
for shared site-level prey-detection variation. The extra surveys and a Beta
mixing model are candidates for development, not established solutions. New
numerical qualification and calibration must precede any sealed truth draw.

Several negative and numerical results constrain the claim. Goal 051 retained
nine contradicted and five unresolved scalar predictions. Goal 053 retained
425/6,000 nested-grid flags and failed its forecast predictive gains. Goal 054
retained the failed constant B100-A point forecast, an unresolved nonlinear
contrast, and a Berger--Boos rule that lost sensitivity. Earlier Arc 3 work
retained four bank-stability failures; the infection-order K1024 prototype
showed corridor LR movement of 7.7774 against a 0.5 limit and was not adopted.
The Goal 049 table retained its 7.4% realised null exclusion [5.6, 9.7] rather
than being redrawn. Goal 055 preserved the wrong-mean and detection failures,
without recalibrating the table or selecting a more favourable secondary rule. Exact integration accuracy and general transfer therefore
remain open even though the frozen Arc 4 calculations replayed exactly.

Charter Pillar 4 is partly answered. The evidence shows that incorrect
structure can bias h without reliable warning and that a small, named
background adjustment can improve estimation and protect a null decision under
specific generators. It does not yet assess each dataset under one
prespecified competing-model set with a calibrated discrimination decision.
Pillar 5 is also open. A blinded synthetic-realistic capstone can test whether
these diagnostics transfer when stochastic invasion, biased access, imperfect
observation and prey response occur together, but its truth must remain sealed
from the analyst and its calibration cannot be inherited silently from the
current landscape and nuisance regime.

## Reusable figures

1. **Detectability, hidden failure and estimation cost.** The
   [first figure](../../../artifacts/goal055_execution/report/arc4_hidden_error_and_estimation.png)
   combines separately labelled Goal 051 null-screen endpoints and Goal 053
   paired changes in magnitude error. [PDF](../../../artifacts/goal055_execution/report/arc4_hidden_error_and_estimation.pdf).
2. **Declaration and magnitude remain distinct.** The
   [second figure](../../../artifacts/goal055_execution/report/arc4_decision_and_magnitude.png)
   shows Goal 054 null/h3 declaration rates above matching-estimator,
   unconditional large-error rates. [PDF](../../../artifacts/goal055_execution/report/arc4_decision_and_magnitude.pdf).
3. **Supplied-mean and detection sensitivity.** The separately labelled
   [third figure](../../../artifacts/goal055_execution/synthesis/output/nuisance_checks.png)
   shows the Goal 055 wrong-mean/correct-mean and D20/baseline checks under
   the frozen Goal 054 rules. [PDF](../../../artifacts/goal055_execution/synthesis/output/nuisance_checks.pdf).
   Its 32 plotted rows come from the new archive-check rule table; it remains
   separate from the original registered experiments.

[Captions](figure-captions.md) specify endpoint definitions, matching estimators,
denominators and uncertainty. The first two figures contain 47 exact plotted
source rows in a [source table](../../../artifacts/goal055_execution/report/arc4_figure_source_data.csv),
with input/output identities in the
[manifest](../../../artifacts/goal055_execution/report/arc4_figures_manifest.json).
