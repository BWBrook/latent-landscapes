# Goal 051: aligned background variation can conceal effect-estimation failure

23 September 2026, Australia/Hobart. **Completed; independent result review passed.**

The registered screen nominates **B100-A_h1**, spatial background prey-loss
variation aligned with invasion exposure at a physical null effect, for one
independent confirmation. Its primary hidden-failure rate is **42.3% versus
19.3%** in the paired assumed-model baseline: **+23.0 percentage points**
(paired 95% interval **19.9 to 25.9**). The adequacy detector rejects only
2.7% of these histories. This is a conditional robustness result on the accepted
synthetic landscape, not confirmation, a general power assessment, or completion
of Paper 1 Charter Pillar 4.

All 17,000 production histories and the fixed 1,000-draw synthesis completed
successfully. The [execution record](execution.md),
[registration](registration-2026-09-23.md),
[verification receipt](../../../artifacts/goal051_execution/synthesis/verification_receipt.json)
and [independent review](final-review.md) define the evidence and claim boundary.
Original Goal 049/050 tables and all earlier numerical failures remain unchanged.

## What the endpoint means

The registered event M is exclusion of physical h from the frozen
candidate-calibrated effect set **or** at least a 1.5-fold point-estimation error.
Primary H is M without a Berger–Boos adequacy rejection. It includes imprecise
point estimates even when the effect set contains the truth. It must not be
called a false-effect declaration rate: the null baseline already has H=19.3%.
The separate strict false-effect event requires null exclusion and a fitted
multiplier at least 1.5 when physical h=1.

The analysis fixes 181 effect nodes, known nuisances, the independent K131072
alpha=1 integration bank and the realised Goal 049/050 cutoff/reference tables.
One complete history, including the spatial field and every observation, is
the independent unit. The bootstrap resamples 1,000 complete paired blocks
jointly across all 17 cells, exactly 1,000 times. It conditions on the realised
reference tables and bank. Cell-rate intervals are Wilson intervals; contrast
intervals are paired percentile intervals. Neither is a simultaneous screening
guarantee.

## Complete primary screen

Rates are percentages; differences and intervals are percentage points relative
to the baseline at the same physical h. D10/D20 vary prey detection with site SD
0.10/0.20; PD10 varies predator detection with SD 0.10. Background fields have
nominal CV 0.5 or 1 and exposure mixing r=0 (I) or 0.7 (A).

| Cell | Primary H | Primary rejection | Plug-in rejection | Delta H [paired 95% interval] |
| --- | ---: | ---: | ---: | ---: |
| B_h1 | 19.3 | 2.4 | 4.4 | baseline |
| B_h3 | 15.7 | 3.3 | 4.5 | baseline |
| B_h5 | 6.6 | 2.0 | 4.2 | baseline |
| D10_h1 | 24.9 | 7.8 | 10.6 | 5.6 [3.4, 7.7] |
| D10_h3 | 13.3 | 7.5 | 10.4 | -2.4 [-4.2, -0.5] |
| D10_h5 | 6.6 | 4.6 | 8.8 | 0.0 [-1.2, 1.2] |
| D20_h1 | 38.4 | 27.0 | 32.6 | 19.1 [15.7, 22.0] |
| D20_h3 | 14.8 | 21.9 | 27.2 | -0.9 [-3.6, 1.7] |
| D20_h5 | 6.5 | 16.4 | 23.6 | -0.1 [-1.8, 1.6] |
| PD10_h1 | 19.6 | 2.4 | 4.4 | 0.3 [0.0, 0.7] |
| PD10_h3 | 15.8 | 3.3 | 4.5 | 0.1 [-0.2, 0.4] |
| PD10_h5 | 6.6 | 2.0 | 4.3 | 0.0 [-0.3, 0.3] |
| B50-I_h1 | 17.4 | 2.7 | 4.9 | -1.9 [-4.2, 0.5] |
| B100-I_h1 | 16.1 | 3.0 | 4.1 | -3.2 [-5.8, -0.7] |
| B50-A_h1 | 33.0 | 2.5 | 4.5 | 13.7 [11.2, 16.4] |
| **B100-A_h1** | **42.3** | **2.7** | **4.0** | **23.0 [19.9, 25.9]** |
| B100-A_h3 | 25.9 | 2.2 | 4.2 | 10.2 [6.8, 13.5] |

Five cells satisfy the screening rule: point delta H at least five percentage
points and paired lower limit above zero. The rule does not require the lower
limit to exceed five points. B100-A_h1 has the largest point difference and is
the **single global nomination**. The other four are not additional nominations.
The ranking is subject to selection bias; it does not establish that background
variation is intrinsically more consequential than detection heterogeneity.

### Aligned background variation

At physical h=1, B100-A produces strict false effects in **21.6%** of histories
(Wilson 95% interval 19.2–24.3%), versus 6.3% at baseline. The paired increase
is 15.3 points [13.0, 18.0]. In **21.2%** of histories that strict false effect
occurs without a primary adequacy flag, versus 6.1% at baseline: +15.1 points
[12.7, 17.6]. Only 11 of the 434 M events are caught by the primary detector.

This is not solely an artefact of the physical null or the lower grid boundary.
With the same aligned field at physical h=3, mean fitted h rises from 3.020 to
3.871. Mean signed log bias rises by 0.2565 [0.2421, 0.2706]; truth exclusion
rises from 5.0% to 16.3%, and primary H rises by 10.2 points. The result supports
distortion of a real effect in this construction as well as spurious null effects.

### Detection departures and the two detector roles

Prey-detection SD0.20 at the null produces more M events than B100-A_h1:
52.0% versus 43.4%. It also produces more strict false effects, 27.5% versus
21.6%, but the primary detector rejects 27.0% of all D20_h1 histories and
catches 136 of its 520 M events. Both departures have exactly 21.2% unflagged
strict false effects. The registered nomination therefore depends on the
broader primary-H endpoint, not on choosing the largest false-effect count.

The primary detector responds to prey-detection departures: rejection reaches
16.4–27.0% across D20 truths, compared with fresh baseline rates of 2.0–3.3%.
Low assumed-model rejection alone did not establish poor sensitivity to every
departure. Conversely, the aligned-background construction shows that
non-rejection can accompany substantial effect-estimation failure.

The secondary plug-in rule rejects 4.2–4.5% on the three fresh baselines and
23.6–32.6% across D20 truths. It does little to expose aligned background
confounding: B100-A_h1 has plug-in H=41.9% versus 18.8% at baseline, a paired
increase of 23.1 points [20.1, 26.0]. These are measured operating rates under
the frozen table, not proof of selected-node size control. The plug-in rule
does not replace Berger–Boos, drive nomination or form an either-test omnibus.

Predator-detection SD0.10 produces primary-H changes from 0.0 to 0.3 points
here, with small paired intervals. This is a negative result at the registered
severity, known nuisance values and survey design. It does not establish
robustness to unknown detection/spread parameters or general irrelevance of
predator observation error.

## Predictions retained, including failures

There are 19 scalar inequality predictions: **five supported, nine contradicted
and five unresolved** under the registered interval rule. Both P3 forecasts of
an interval containing zero are met; they are forecasts of non-resolution,
not equivalence tests. Every component and unrounded interval is retained in
[predictions.csv](../../../artifacts/goal051_execution/synthesis/predictions.csv).

- **P1:** D10_h1 increases H by 5.6 points, contradicting the prediction of less
  than two. D10_h3/h5 satisfy the H prediction. D20 shifts mean log estimates
  upward at h=3/5: exp(delta bias)=1.185 [1.174, 1.196] and 1.110
  [1.102, 1.117], contradicting the predicted downward shift. Its null truth
  exclusion increases by 21.2 points, contradicting the predicted increase
  below three points. Several remaining P1 bounds are unresolved.
- **P2:** the aligned null's low primary rejection and delta H above ten points
  are supported. Its observed strict false-effect rate is 21.6%, but the
  interval spans 20%; the claim that the rate exceeds 20% remains unresolved.
- **P3:** unaligned background fields have strict-false-effect contrast
  intervals containing zero. Their mean effect-set log spans are smaller,
  by 0.0178 [0.0070, 0.0297] and 0.0361 [0.0220, 0.0508], contradicting the
  predicted widening. Width alone is not an adequacy or information measure.
- **P4:** predator SD0.10 has less absolute mean log bias than prey SD0.20 at
  h=3/5; both predicted orderings are contradicted. The largest predator
  truth-exclusion increase across h=1/3/5 is 0.1 points [-0.1, 0.5],
  contradicting the predicted increase of at least three points somewhere.

These outcomes test predictions; they are not reasons to alter severities,
redraw fields, change the detector, or classify the scientific run as failed.

## Realised fields and interpretation

The whole-map mean background hazard is fixed at 0.002/day in every field.
Realised variability and correlation are not forced to their nominal parameters.
The following are averages across the 1,000 independent fields; correlations
are computed within each field before averaging.

| Background cell | Map CV | Sampled CV | Sampled mean hazard/day | Training mean | Holdout mean | Sampled corr(hazard, exposure) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B50-I_h1 | 0.472 | 0.466 | 0.002005 | 0.002007 | 0.001999 | -0.001 |
| B100-I_h1 | 0.911 | 0.883 | 0.002010 | 0.002014 | 0.001997 | 0.001 |
| B50-A_h1 | 0.489 | 0.423 | 0.002064 | 0.002082 | 0.002007 | 0.569 |
| B100-A_h1 | 0.947 | 0.801 | 0.002047 | 0.002093 | 0.001909 | 0.533 |

Here realised exposure is max(0,60-arrival). For B100-A, its sampled
hazard–exposure correlation has a 2.5–97.5% field range of 0.221–0.717;
its sampled hazard–A correlation averages 0.567 and map hazard–A correlation
0.629. Raw hazard–arrival correlation among sites arriving by day 60 averages
-0.519. The mean number of those sites is 148.8/160. Non-arrivals were handled
as zero exposure, not silently omitted from the primary exposure correlation.

B100-A_h1 and h3 use identical hazard fields. The training/holdout mean
difference is allowed by whole-map scaling and is part of this registered
construction. The screen does not isolate correlation from all accompanying
distributional and sampled-hazard changes, or prove a single causal explanation
for its effect on the estimator.

Across detection fields the realised site means are 0.6503/0.6506 for D10/D20
and 0.6501 for PD10; mean site SDs are 0.09949/0.19895 and 0.09967 respectively.
All summaries, field quantiles and undefined-correlation counts are retained in
[field_diagnostics.csv](../../../artifacts/goal051_execution/synthesis/field_diagnostics.csv).
They were not used to tune or redraw histories.

## Evidence, limits and next decision

The inspected [figure](../../../artifacts/goal051_execution/synthesis/misspecification_screen.png)
shows primary-H rates, paired H differences and point estimates of signed log
bias. Bias intervals and all set/score/component diagnostics are in
[cell_metrics.csv](../../../artifacts/goal051_execution/synthesis/cell_metrics.csv)
and [paired_contrasts.csv](../../../artifacts/goal051_execution/synthesis/paired_contrasts.csv).
The [PDF](../../../artifacts/goal051_execution/synthesis/misspecification_screen.pdf)
is a standalone export. Frozen production profiles, held-out scores, candidate
p-values, memberships and the actual bootstrap indices remain archived.

These are single-landscape, synthetic, finite-grid, fixed-bank, fixed-table,
known-nuisance findings. The physical multiplier can differ from the parameter
best approximating a misspecified generator. Calibration-table uncertainty,
integration error, unknown nuisance estimation, additional landscapes and
competing fitted models are outside this tranche. No original numerical
failure is converted into a pass by the present screen.

Recommend the [bounded independent confirmation](confirmation-proposal.md)
of B100-A_h1 against its paired baseline before any Stage 2 model comparison.
It requires Barry's decision and has not launched. No fallback candidate,
extra replication, new calibration or alternative-model campaign is authorized
by the present nomination.
