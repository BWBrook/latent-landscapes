# Goal 052: adjustment is feasible, but repair is not established

24 September 2026. **Closed as a retrospective feasibility and likelihood-geometry pilot.**
Charter Pillar 4 / Roadmap Arc 4. The Goal 051 nominee remains unconfirmed.

The added background coefficient can reduce fitted predator-effect inflation,
but this pilot does not demonstrate better recovery or consistently better
prediction. Broad trade-offs between the predator multiplier h and the spatial
background coefficient beta persist even when true arrival times are supplied.
The next useful experiment is a fresh comparison with exact nonzero-beta
generating controls, rather than further fitting of these six blocks.

## What was evaluated

The [registration](registration-2026-09-24.md) fixed 24 archived histories:
blocks 0–5 in the baseline and aligned-background conditions, each at h=1 and
h=3. Every history was fitted with constant background, A-adjusted background,
and an A-adjusted no-effect comparator. The adjustment uses the known
source-distance proxy A and a known whole-map mean hazard. It omits the
generator's residual Gaussian field G. All actual fits use latent arrivals;
true arrivals enter a separate oracle diagnostic only.

All 81 beta rows and 181 h nodes completed. Original profiles, held-out curves,
point estimates, score components and identities replay exactly. Source,
archive, bank, row and assembled-output checks passed; numerical details and
the initial verification-helper correction are in [execution.md](execution.md).
The fixed synthesis ran once, and the figures were inspected. The
[independent result review](final-review.md) supports closure under these limits.

## Effect estimates and predictive comparisons

Each row below averages six histories. These are development-panel summaries,
not estimates with demonstrated population precision. Absolute log error is
`abs(log(fitted h / true h))`; the two error columns and the direct predictive
comparison are **exploratory summaries derived after the registered synthesis**.

| Generator and truth | Mean h, constant → adjusted | Mean absolute log error, constant → adjusted | Direct held-out score, adjusted − constant (nats) |
| --- | ---: | ---: | ---: |
| Baseline, h=1 | 1.125 → 1.442 | 0.103 → 0.286 | +0.294 |
| Baseline, h=3 | 2.692 → 2.617 | 0.330 → 0.348 | −0.132 |
| Aligned background, h=1 | 1.225 → 1.083 | 0.170 → 0.068 | +0.028 |
| Aligned background, h=3 | 3.633 → 2.750 | 0.310 → 0.402 | −0.334 |

The aligned-null change comes from two blocks; four were already fitted at
h=1 and remain there. In the aligned threefold histories, adjustment lowers h
in all six blocks. It moves the average closer to three while increasing
average absolute log error. Raw-h absolute error changes only from 1.083 to
1.033. Neither selecting the more favourable error scale nor the shift in the
average estimate would justify calling this a repair. Flexibility also raises
the baseline-null mean from 1.125 to 1.442.

The registered held-out comparison asks whether the fitted predator effect
adds prediction **within the adjusted model**, against its fitted no-effect
version. That advantage is positive in all six baseline threefold histories
and four of six aligned threefold histories. It is positive in none of the
aligned-null histories. Mean advantages are 1.387, 0.768 and −0.018 nats,
respectively. The baseline-null mean is −0.108 nats, with one positive block.

That comparison does not test whether adjustment improves prediction over the
constant model. The direct comparison in the table answers the latter question:
adjustment wins in only 2/6 aligned-null and 3/6 aligned-threefold histories.
Its mean training improvement in the aligned threefold condition is 4.396 LR
units, yet its mean direct held-out score falls by 0.334 nats. Training gain
therefore supplies no evidence by itself of a useful predictive repair.
All score differences are conditional-prey contrasts over the 40 held-out
sites; the unchanged predator marginal cancels. A sign is not a calibrated
effect declaration or an adequacy test.

![Paired fitted effects and within-model predictive contrasts](../../../artifacts/goal052_execution/synthesis/primary_paired_comparison.png)

The right column compares each fitted effect model with its own no-effect
comparator; it is **not** the direct adjusted-minus-constant comparison above.

## Likelihood geometry and registered expectations

The [latent surfaces](../../../artifacts/goal052_execution/synthesis/joint_contours_latent.png)
and [oracle surfaces](../../../artifacts/goal052_execution/synthesis/joint_contours_oracle.png)
show connected, often broad h–beta trade-offs: a stronger spatial background
association can substitute for part of the post-arrival multiplier. Contours
are raw LR 0.5, 2, 4 and 8, from inner purple to outer yellow. Profile ranges
at LR≤2 describe shape; they are not 95% intervals or calibrated support sets.

| Registered expectation | Observed descriptive outcome |
| --- | --- |
| Adjustment lowers aligned-null h, possibly weakening separation | Limited support: mean movement −0.142; two decreases, four ties. |
| Baseline h=3 separates from the adjusted null more consistently than aligned h=1 | Supported in this panel: raw adjusted-null LR averages 5.799 versus 0.122 and is larger in all six paired blocks. Fitted h>1 occurs in 6/6 versus 1/6. |
| Oracle arrivals usually sharpen separation | Not supported: oracle LR≤2 h profiles are narrower in 12/24, equal in 3/24 and wider in 9/24. Mean width reduction is only 0.046 h units. |

The second result is qualified: the uncalibrated profile reaches h=1 in three
of six baseline threefold histories and one of six aligned threefold histories.
No threefold history has its maximum at h=1. The oracle changes neither the
broad qualitative pattern nor the need for exact adjusted-model controls.
It suggests arrival uncertainty alone is insufficient to explain the observed
weakness; it does not identify the remaining cause or prove structural
non-identifiability.

Two beta maxima in each lane reach the upper edge +2. They are the two paired
null cells in block 0, hence one shared block pattern rather than independent
failures. Their beta profiles also reach that edge. No fitted h or LR≤2 h
profile reaches h=10. These finite-box limits remain unresolved; no expansion
or penalty was introduced after observing them.

Coarse/fine LR movement is at most 0.01855 in the latent lane and 0.02764 in
the oracle lane, below the registered 0.10 diagnostic tolerance. Coordinate
movement flags two latent histories (baseline h=1/block 3 and h=3/block 5)
and one oracle history (baseline h=3/block 5). The largest h movement is 0.20
latent and 0.15 oracle; beta movement is at most 0.05. The small LR changes
alongside coordinate movement are consistent with flat local geometry. The
flags remain reported; nested-grid stability does not establish exact-bank
accuracy or behavior outside the box.

## What the survey diagnostics establish

Held-out A spans −0.830 to 1.355, entirely inside the training range −1.072
to 1.950. Prediction interpolates within that covariate range, while using
different sites in the same landscape and spatial process. It is not external
landscape or independent-field validation.

Across the 24 histories there are 280–327 training survey occasions at which
prey is still alive and predator arrival has not occurred, spanning 94–100
training sites. Held-out counts are 93–105 occasions at 34–38 sites. These
evaluator-only quantities differ from the 287–338 and 98–111 occasions that
precede arrival without checking whether prey is alive. Latent pre-arrival
risk time totals 3,393–3,841 training site-days and 1,114–1,266 held-out
site-days. Their presence does not establish that the survey identifies the
background coefficient precisely.

The supplied whole-map mean does not fix the mean at training or held-out
sites. Changing beta can alter those means as well as their spatial pattern.
Beta is an association with A, not a causal estimate of distance effects or
recovery of G. The baseline cells only provide exact beta=0 controls; B100-A
retains omitted G. This panel cannot isolate survey information from that
remaining misspecification. Known detection, spread and mean hazard, one
landscape, one fixed empirical bank and six previously examined blocks also
limit every interpretation.

## Decision and evidence

Close Goal 052 with a valid numerical pilot and an unresolved scientific
trade-off. Do not adopt the adjusted model as a repair, repeat the old
nomination as confirmation, or interpret raw geometry with old cutoffs.
The [prospective proposal](prospective-comparison-proposal.md) specifies the
next discriminating comparison, including exact nonzero-beta controls, a
known-beta diagnostic, fresh paired histories and direct held-out model
comparisons. Its scientific scope awaits review and approval; resource choices
remain delegated to Astra.

The [24-row table](../../../artifacts/goal052_execution/synthesis/metrics.csv),
[four-cell table](../../../artifacts/goal052_execution/synthesis/cell_summary.csv),
[survey diagnostics](../../../artifacts/goal052_execution/synthesis/geometry_summary.csv),
[exploratory derivations](../../../artifacts/goal052_execution/descriptive-findings.json)
and [completion verification](../../../artifacts/goal052_execution/completion-verification.json)
retain the evidence. No new process histories or calibration were generated.
All earlier numerical failures and frozen Goal 049–051 results remain intact.
