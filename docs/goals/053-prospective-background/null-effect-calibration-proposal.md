# Proposed next tranche: calibrate an adjusted null-effect decision

27 September 2026. **Proposal for Fable's critique and Barry's scientific
approval. No follow-on implementation or simulation is authorized by this file.**
Charter Pillar 4 / Roadmap Arc 4. Routine resource and timing decisions remain
delegated to Astra.

## Recommendation and scientific question

Calibrate one finite-grid test of **h=1** in the adjusted-background model,
then evaluate its false-declaration rate and sensitivity on fresh histories
from the same six cells. Retain the fixed landscape, survey, known nuisances,
K131072/alpha1 bank and full h/beta rectangle. Use **999 reference histories
at each of the 81 null beta nodes**, followed by **1,000 independent paired
evaluation blocks in six cells**. Do not undertake full profile-confidence
calibration, redesign the survey or expand the landscape set in this tranche.

Goal 053 supplies the reason. Adjustment lowers mean estimation error in both
exact nonconstant-background cells and both residual-field cells, but roughly
doubles null error under constant background and worsens beta0/h3 error.
It creates a clear benefit/cost trade-off. Direct model preference is only
59–65% even in the exact nonconstant-background cases, and oracle arrivals
change matched estimation error little. A calibrated declaration is the next
unresolved capability; better arrival information alone is not an established
solution. This recommendation agrees with the [independent result review](final-review.md).

The question is narrow: **can this declared analysis control false effect
declarations under its assumed background family while retaining useful
sensitivity to a real threefold effect, and what fails when residual G is
omitted?** A conservative rule with weak sensitivity is an informative negative
result. Neither a successful run nor nominal calibration establishes estimator
repair, model identification, interval coverage or robustness outside the model.

## Statistic, nuisance treatment and validity boundary

For each history fit the whole existing rectangle and compute

`T_adj = 2 * (max_{h,beta} logL(h,beta) - max_beta logL(1,beta))`.

Both fits use only training observations. For each null node beta_j generate
999 independent reference histories with h=1 under the exact adjusted model,
then fit the **entire statistic**, including estimation of beta in both
maxima. For an evaluation statistic t, calculate

`p_j(t) = (1 + count(T_reference,j >= t)) / 1000`

and declare an effect only when **`max_j p_j(t) <= 0.05`**. Retain equal
statistics conservatively; freeze the numerical comparison tolerance before
generation. Do not substitute the fitted-node p-value or a chi-square cutoff.

For an exact on-grid null, the observed statistic and the true node's reference
statistics are exchangeable conditional on the fixed analysis bank. The
plus-one true-node p-value is super-uniform. Rejection by the maximum p-value
requires rejection at that true node, so the test has size at most 0.05,
averaging over the reference and evaluation histories. Dependence among
reference tables at different beta nodes does not invalidate this implication.

This does **not** guarantee a 5% conditional rejection rate for every realised
frozen reference table. It does not cover beta between nodes, omitted residual
G, unknown nuisance parameters, a different bank or another landscape. The
finite-grid proof and realised operating rates must both be reported. A
Berger–Boos restriction or any smaller nuisance search would require a
separate justified procedure and is not silently introduced if the supremum
is conservative.

For context, retain a constant-background decision based on

`T_constant = 2 * (max_h logL(h,0) - logL(1,0))`.

Calibrate it using the same 999 exact beta0 reference histories and the same
plus-one rule. Its assumed-model guarantee applies at beta0 only. This permits
a matched comparison of the operational cost of background adjustment and
the harm from ignoring background variation, without mixing in the old
Goal 049 reference table. The two analyses receive the same survey and known
nuisance information. The adjusted null remains the neutral fitted model.

## Reference and evaluation panels

The reference panel is **999 paired blocks × 81 exact-null beta nodes =
80,919 histories**. Share underlying process, prey-event and detection streams
across beta nodes within a block; keep blocks independent. This pairing improves
comparability while preserving each node's marginal reference law. It is not
81 independent replicates of the landscape. All exact hazards retain the
whole-map normalization and known mean 0.002.

The fresh evaluation panel is **1,000 paired blocks × the six Goal 053 cells =
6,000 histories**: exact beta0 and beta.60 at h1/h3, plus the original B100-A
at h1/h3. Generate evaluation and reference blocks from disjoint roots,
separate also from Goals 049–053 and the integration bank. Freeze the roots,
opaque identities and full procedure in a new registration before either
panel is generated. Goal 053 histories can support development checks but
must not become the new prospective evaluation sample.

Exact beta0/h1 and beta.60/h1 assess realised assumed-model size at those two
nodes. B100-A/h1 assesses robustness to residual-field misspecification, for
which no nominal guarantee is claimed. Their h3 partners assess sensitivity.
Fresh evaluation at two exact null nodes does not empirically certify the
realised table over all 81 beta nodes. The theoretical finite-grid guarantee
has the different, reference-averaged meaning stated above.

Do not add an oracle campaign: the diagnostic has already answered the present
arrival-information question sufficiently to choose this next step.

## Outcomes, uncertainty and predictions

The primary outcomes are the six effect-declaration frequencies for the
adjusted rule and their paired differences from the new constant rule. Report
the absolute null rates beside 0.05 and the absolute h3 rates, including weak
sensitivity or strong conservatism. Retain all six cells and numerical flags.

Keep secondary estimation error, at least 1.5-fold point-error rates, direct
held-out prediction and the adjusted-neutral prediction comparison. Describe
joint events such as a declaration with a large point error. Conditional
error summaries among declared histories are selected-subset descriptions;
they are not unbiased recovery summaries or confidence guarantees. Do not
equate the selected background family with correct estimation of h.

Use a fixed **2,000-draw** summary bootstrap with two independent block
resamples per draw: the 999 reference blocks, paired across all beta nodes,
and the 1,000 evaluation blocks, paired across the six cells. Recalculate
the declared rule from the stored statistics under each resample. Report
both frozen-table evaluation uncertainty and calibration-aware uncertainty.
Do not resample sites independently or generate additional fitted histories
to obtain the bootstrap. The exact finite-sample validity argument does not
depend on bootstrap accuracy.

With 1,000 evaluation histories, binomial MCSE near a 5% null rate is about
0.0069 before reference-table uncertainty; the worst-case rate MCSE is about
0.0158. At a 5% reference tail, 999 histories give about 50 tail observations
and tail-probability SE near 0.0069. These are planning approximations, not
the SE of the final supremum test or its estimated quantile. Using 249 would
give only about 12 tail observations and SE near 0.0138, so it would repeat
the weak reference precision exposed earlier in the programme. The
999-history choice supports an operating-characteristic comparison, while
still requiring explicit reference-table uncertainty.

Register these qualitative predictions before running: the supremum rule
will be conservative relative to true-node calibration; adjustment will reduce
residual-field null declarations relative to the constant rule; this protection
will cost some h3 sensitivity when background is constant; and residual G may
still produce excess declarations despite the exact-model guarantee. Report
counterexamples and ambiguous contrasts. Do not invent a favourable cutoff,
calibration node subset, nominal level or model-selection pretest after seeing
the outcomes. Numerical precision is reported, not repaired by outcome-driven
additional reference histories.

## Cost and qualification

Goal 053's complete production took 11,797 receipt seconds for 6,000 actual
histories plus 1,000 oracle histories on deep-server, with 16 row workers,
one numerical thread each and 3.64 GiB peak RSS. Assigning **all** that cost
to its 6,000 actual histories gives a conservative planning rate of 1.966
seconds per full fitted history. The proposed **86,919** reference/evaluation
histories therefore project to **47.5 elapsed hours** under that surrogate,
or about **71.2 hours with a factor 1.5 allowance**, before a small synthesis
and verification reserve. These are projections, not measured timing bounds.
The corresponding 249-reference design would project to 14.3 hours before
the allowance, but its reference precision is not the recommended trade-off.

Reuse authenticated integrations; no larger bank is proposed. New generator
truths and the larger panel require a measured complete-workload qualification
before production, with exact replay of current kernels, source/input identity,
reference/evaluation separation and plus-one/tie controls. Choose concurrency,
chunking and deep-server/Nectar/Kunanyi routing from that measurement. Higher
worker counts are not assumed to scale linearly. Resource/time decisions are
already delegated and need no new Barry approval; scientific panel sizes and
inferential rules remain fixed once approved.

## Completion and decision boundary

The tranche ends with one verified frozen reference table, the independent
six-cell evaluation, uncertainty that includes reference-table variation,
independent scientific review and a recommendation on the scope of effect
declarations. Excess realised false declarations, poor sensitivity or
misspecification failure are valid completed outcomes and remain visible.
They trigger interpretation and a new scientific decision, not automatic
recalibration or another simulation campaign.

If the declaration is useful only under restrictive assumptions, say so.
If conservatism makes it practically uninformative, observation redesign or a
different inferential formulation becomes the next substantive question.
Full confidence calibration, unknown nuisances, new surveys/landscapes and
publication remain outside this proposal.

Fable's next action is critique of this inferential scope and its interpretation.
Barry's subsequent decision concerns that scientific scope. No new resource
approval is requested, and no part of this proposal has been launched.
