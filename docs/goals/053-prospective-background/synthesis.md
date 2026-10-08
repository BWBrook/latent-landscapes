# Goal 053: spatial adjustment helps conditionally and costs precision

27 September 2026. Charter Pillar 4 / Roadmap Arc 4.

The approved prospective comparison is complete. Estimating spatial background
loss improves predator-effect estimates when background variation follows the
fitted spatial proxy, including when an unmodelled residual field remains.
The same adjustment substantially worsens estimation and prediction when
background loss is constant. It is a useful conditional correction, not a
generally preferable estimator or a reliable way to identify the generating
model from one history.

This closes the [registered six-cell comparison](registration-2026-09-27.md).
The [independent result review](final-review.md) and [next-step proposal](null-effect-calibration-proposal.md)
address the scientific interpretation and the remaining inferential decision.
Goal 051's original hidden-failure nomination remains unconfirmed under its
original procedure. No confidence calibration or survey change was performed.

## Evidence and uncertainty

The experiment contains 1,000 fresh paired blocks, with six histories per
block. All 6,000 actual histories use the current 120/40 training/holdout split,
survey schedule, known nuisance quantities, K131072/alpha1 bank and full
181-by-81 h/beta rectangle. Exact-background cells have beta=0 or +0.60 and
h=1 or 3. B100-A retains the original aligned background and residual Gaussian
field; it has a known h but no true fitted beta.

All 81 beta rows, frozen Goal 052 replays, h=1 identities, source/input bindings
and 170 production output hashes passed verification. Production took 3 h
16 min 37 s; the single fixed synthesis took 15 receipt seconds. The source and
earlier results remain unchanged. Direct extraction from every actual and
oracle score surface exactly reproduces the saved fitted coordinates,
training maxima, direct prediction contrasts and adjusted-neutral contrasts.
The [execution record](execution.md) gives receipts and provenance.

Intervals below are percentile 95% intervals from the registered 2,000 shared
whole-block bootstrap draws. They describe Monte Carlo uncertainty in
across-history summaries, conditional on this landscape, survey, fixed bank
and procedure. They are neither per-history confidence intervals nor
simultaneous guarantees across all reported outcomes.

## Estimation benefit and flexibility cost

The primary error is absolute log(h estimate / h truth). A negative paired
change favours adjustment. All cells retain all 1,000 histories.

| Background and truth | Constant error | Adjusted error | Adjusted minus constant [95% interval] | At least 1.5-fold point error: constant → adjusted |
| --- | ---: | ---: | ---: | ---: |
| Exact beta0, h1 | 0.1505 | 0.3092 | +0.1587 [0.1327, 0.1858] | 16.3% → 30.1% |
| Exact beta0, h3 | 0.2281 | 0.3254 | +0.0973 [0.0835, 0.1114] | 13.8% → 32.3% |
| Exact beta.60, h1 | 0.3689 | 0.1925 | −0.1764 [−0.1940, −0.1596] | 45.8% → 20.9% |
| Exact beta.60, h3 | 0.3205 | 0.2123 | −0.1082 [−0.1231, −0.0940] | 33.8% → 13.3% |
| B100-A, h1 | 0.3395 | 0.1872 | −0.1522 [−0.1699, −0.1334] | 42.0% → 20.4% |
| B100-A, h3 | 0.2911 | 0.2445 | −0.0466 [−0.0613, −0.0318] | 28.6% → 20.2% |

Adjustment reduces mean error by approximately 45% in the aligned null and
16% in the aligned threefold case. The latter reverses the descriptive
direction in Goal 052's six-block pilot; that original adverse result remains
part of the record. The new evidence supports a population-average benefit
over histories in this specific setting, while retaining considerable
individual-history error.

At exact beta.60/h3 the constant model has mean signed log error +0.2901
[0.2764, 0.3041], whereas adjustment gives −0.0057 [−0.0217, 0.0107]. Under
B100-A/h3 adjustment reduces positive bias but leaves mean signed log error
−0.0579 [−0.0771, −0.0390]. Omitting residual G therefore still matters; the
adjusted model has not recovered the entire generating process.

Point-error rates are estimation outcomes. In particular, a null history with
h estimate at least 1.5 is not automatically a false calibrated declaration:
no adjusted-model declaration procedure has yet been calibrated.

![Mean absolute log errors](../../../artifacts/goal053_execution/synthesis/mean_errors.png)

## Prediction and model preference

These comparisons use fitted training-site parameters and untouched holdout
observations. Scores are conditional-prey log scores per holdout site;
positive adjusted-minus-constant values favour adjustment. Preference uses the
registered sign rule with its numerical tie tolerance, retaining all histories.

| Background and truth | Direct score change [95% interval], nats/site | Adjusted / constant / tie |
| --- | ---: | ---: |
| Exact beta0, h1 | −0.00488 [−0.00620, −0.00359] | 41.4% / 54.0% / 4.6% |
| Exact beta0, h3 | −0.00354 [−0.00449, −0.00261] | 39.9% / 54.2% / 5.9% |
| Exact beta.60, h1 | +0.00196 [0.00057, 0.00336] | 59.2% / 38.9% / 1.9% |
| Exact beta.60, h3 | +0.00674 [0.00488, 0.00848] | 64.8% / 34.4% / 0.8% |
| B100-A, h1 | +0.00063 [−0.00109, 0.00228] | 55.0% / 42.2% / 2.8% |
| B100-A, h3 | +0.00485 [0.00305, 0.00671] | 59.8% / 37.9% / 2.3% |

The aligned-null estimation improvement has no resolved mean predictive
advantage. Its 55% preference frequency does not contradict that: the sign
frequency and the mean score weight gains and losses differently. Exact
nonzero-beta histories favour the correct background family only about
59–65% of the time. These rates do not establish reliable model identification,
calibrated test size or power, and model preference does not establish an
accurate h estimate. At beta0 the adjusted family also contains the truth.

The fitted adjusted h=1 comparator is a separate neutral benchmark. Descriptive
mean adjusted-minus-adjusted-neutral scores are −0.00199, −0.00157 and
−0.00190 nats/site in the three null cells, versus +0.02945, +0.04472 and
+0.03585 in their h3 counterparts. This preserves evidence that h contributes
to prediction when the effect is real, without turning a predictive difference
into a significance test. The fixed synthesis reports these secondary means
without additional bootstrap intervals; none were generated after inspection.

![Direct predictive contrasts](../../../artifacts/goal053_execution/synthesis/paired_contrasts.png)

![Preference frequencies with ties](../../../artifacts/goal053_execution/synthesis/model_preference.png)

## Predictions and information diagnostics

The quantitative predictions were advisory, not acceptance gates.

- At exact h3, the free-beta/known-beta log-RMSE ratio is **1.404
  [1.338, 1.475]** for beta0 and **1.082 [1.053, 1.112]** for beta.60.
  Both exceed the respective target values 1.25 and 1.05, especially beta0;
  neither exceeds the prespecified contradiction bound 1.60 or 1.30. The
  complete-event-time calculation understated observed-data nuisance cost.
- At beta.60/h3, constant-model signed bias exceeds the predicted +0.10.
  Adjusted minus known-beta signed bias is **+0.0239 [0.0163, 0.0313]**,
  within the declared absolute 0.05 bound. This supports those two forecasts.
- In exact nulls, free-beta estimates cross h=1.5 more often than known-beta
  estimates: **30.1% versus 16.3%** at beta0 and **20.9% versus 11.2%** at
  beta.60. Among free-beta fits above h1, fitted beta is below/above/equal to
  truth in **72.6/23.3/4.1%** of 489 beta0 histories and **61.6/34.4/3.9%**
  of 482 beta.60 histories. The registered boundary pattern is present;
  these descriptive associations do not identify all causes of error.
- The forecast of **0.01–0.025 nats/site** predictive improvement fails at
  both exact beta.60 truths: both observed 95% intervals lie below 0.01.
  The h1 preference rate is 59.2% [56.2, 62.1], below the two-thirds target;
  the h3 rate is 64.8% [61.9, 67.7]. No retrospective success band is attached
  to the word “roughly”.

The oracle diagnostic uses only the registered first 250 blocks in the four
exact cells. A descriptive comparison with the **same 250 actual blocks**
avoids confounding oracle information with a different history sample:

| Exact cell | Actual / oracle mean absolute log error | Actual / oracle mean raw LR≤2 h span |
| --- | ---: | ---: |
| beta0, h1 | 0.2705 / 0.2595 | 2.4616 / 2.4458 |
| beta0, h3 | 0.3164 / 0.3119 | 3.6172 / 3.6210 |
| beta.60, h1 | 0.1858 / 0.1809 | 1.2510 / 1.2158 |
| beta.60, h3 | 0.2050 / 0.2028 | 2.3536 / 2.3466 |

Supplying true arrivals changes these averages little and does not uniformly
narrow the raw profile span. Arrival uncertainty alone cannot explain the
remaining trade-off. This neither establishes structural non-identifiability
nor proves that event scarcity is the dominant limitation. Known-beta and
oracle fits are explicitly evaluator-assisted diagnostics, not operational
competitors supplied equivalent information.

## Precision, numerical boundaries and claim limits

All six actual primary error MCSEs meet the 0.02 target (largest **0.01337**);
all six direct-score MCSEs meet the 0.002 nats/site target (largest
**0.000971**). Oracle summaries retain N=250 and their larger uncertainty;
they do not replace the N=1,000 primary endpoints.

Finite-grid limitations remain visible. Across the actual fits, 36 touch a
beta boundary and six touch h10. The physical h1 boundary is reached by
1,585 fits. The nested 0.10-grid check flags **425/6,000** fits, including
237/1,000 in exact beta0/h3. The largest h-coordinate movement is 0.60, while
the largest raw LR movement is only 0.0422 and the largest beta movement is
0.05. Small changes in likelihood height can therefore move the fitted h
along a shallow trade-off. These observations qualify the declared constrained
estimator; they do not justify post-outcome grid enlargement or erase earlier
numerical failures. Raw LR≤2 spans remain uncalibrated geometry.

A descriptive check using the already saved coarse fits changes cell mean
absolute log error by at most 0.00114. It leaves the six primary error directions
unchanged; it is not an additional simulation, bootstrap or grid qualification.

The evidence is conditional on one landscape, one site split and survey,
known mean background hazard/detection/spread, a fixed empirical-arrival bank
and the finite parameter rectangle. It does not establish transport to other
landscapes, unknown-nuisance inference, confidence coverage, causal identification
or immunity to residual background variation. The holdout is spatial transfer
within the same simulated landscape and history. Across-history uncertainty
does not quantify integration-bank or model uncertainty.

The next useful question is whether a properly calibrated adjusted-model
**null-effect decision** can control false declarations while retaining useful
sensitivity to a real effect. That narrower inferential step is justified by
the estimation gains and the flexibility cost. Full profile confidence and a
new survey design should remain deferred pending its outcome. The
[costed proposal](null-effect-calibration-proposal.md) requires scientific
approval; no follow-on computation has begun.

## Reviewable evidence

- [Per-cell summaries](../../../artifacts/goal053_execution/synthesis/cell_summary.csv)
  and [paired contrasts](../../../artifacts/goal053_execution/synthesis/paired_contrasts.csv).
- [Per-history metrics](../../../artifacts/goal053_execution/synthesis/metrics.csv),
  [oracle metrics](../../../artifacts/goal053_execution/synthesis/oracle_metrics.csv),
  [fixed bootstrap summaries](../../../artifacts/goal053_execution/synthesis/bootstrap_summary.csv)
  and [forecast/geometry record](../../../artifacts/goal053_execution/synthesis/summary.json).
- [Retrieval manifest](../../../artifacts/goal053_execution/retrieval-manifest.json):
  observations, evidence metadata, row receipts and synthesis are local. The
  four complete score rectangles and 81 compressed row arrays remain intact
  at the authenticated remote run root, with all their hashes recorded.
- [Direct score-to-metric check](../../../artifacts/goal053_execution/score-metric-crosscheck.json)
  reproduces every fitted coordinate and prediction contrast from those raw
  rectangles for the 6,000 actual and 1,000 oracle histories.
