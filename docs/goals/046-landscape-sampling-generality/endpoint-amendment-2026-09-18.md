# Arc 3 endpoint review and completion envelope

18 September 2026. State: completed under delegated authority; conditional
reporting amendment, not numerical method acceptance.

## Authority and reporting horizon

After Fable's replies 227–228, Barry instructed Astra: “I'm happy for you to
proceed autonomously now, on this basis, using your own judgement and the
[$twilight-laboratory](/Users/bwbrook/.codex/skills/twilight-laboratory/SKILL.md)
workflow.” This authorizes choosing and executing the bounded Arc 3 route
discussed in that exchange. It supersedes the earlier requirement to return
for selection between the proposed completion and sharpening routes. It does
not authorize publication, commits, pushes, unrelated scientific changes or
unbounded compute.

The question remains Goal 046's equal-effort comparison of access-constrained
and balanced sampling across the nine fixed maps (Charter Pillar 3). The
reporting horizon is an independently reviewed decision and an inspectable
synthesis: what the existing evidence resolves, what remains sensitive or
imprecise, and whether further computation is necessary for that conclusion.
A negative or unresolved result is valid. Significance is not an acceptance
criterion. The generator, observations, comparators, truths and map ensemble
remain unchanged.

## Staged route

1. Verify Fable's numerical summaries against the hash-bound archived profiles
   and bootstrap replicates. Recover the registered equal-map archetype
   contrasts rather than inferring them from counts of map-level intervals.
2. Diagnose calibration versus evaluation resampling uncertainty with the
   empirical law of total variance, retaining the complete-history pairing.
   Separate a conditional computational diagnosis from ecological variability
   and from an untested forecast about a larger calibration ensemble.
3. Review a bounded endpoint sensitivity amendment alongside the original
   failed criteria. Decide whether archival, conditional synthesis suffices or
   whether a targeted new qualification is necessary. Freeze any new-run
   criteria before unseen results; identify retrospective judgments as such.
4. Produce the decision-relevant table/figure, interpretation, independent
   review and updated handover. Report at that horizon, not after each stage.

## Archive checks specified before the additional diagnostic

Compare K65536 and K131072 on all five declared contrasts, three effects, both
lanes, all nine maps, and the equally weighted fixed-map archetype summaries.
Use the K131072 calibration-aware bootstrap SE as the reference scale. Record
point movement, interval endpoints and interval sign class (below zero,
including zero, above zero), without treating counts of unadjusted intervals
as independent discoveries or a global test. Record leave-one-map-out point
ranges separately from within-map bootstrap intervals.

Fable's proposed 0.25-SE sensitivity tolerance will be reported as a diagnostic
yardstick, not an error bound or proof of qualification. For zero/tiny SEs,
report the absolute movement and the original endpoint tolerance instead of
dividing by an arbitrary positive floor: 0.005 mean absolute log error, 0.01
mean log support span, 1/250 coverage/exclusion proportion, and 0.0001 nats per
holdout site for score. Do not adjust these after seeing diagnostic results.
No interval or map is dropped because it is awkward.

For each calibration resample C at the reference bank, let D_i(C) be the
balanced-minus-access per-history metric for the 250 evaluation histories.
Recalculate cutoffs within C. The empirical bootstrap variance decomposes as

`Var_C(mean_i D_i(C)) + E_C[Var_i(D_i(C), ddof=0) / 250]`.

The terms quantify calibration and evaluation resampling conditional on the
empirical histories, maps and integration bank. Estimate the calibration
expectations using 1000 draws with the existing seed and recorded pairing.
For linear point-error and score metrics, the calibration term must be zero.
The hypothetical calculation replacing the first term by one quarter is only
a scaling scenario; it is not evidence that 1000 fresh calibration histories
would deliver that result for these discrete, tail-quantile statistics.

### Finite-bootstrap precision check

The initial archetype table contains interval bounds very near zero. Before
interpreting exclusions, apply the following computational-precision check
uniformly to all 90 archetype endpoints at both banks. From the 1000 stored
bootstrap draws, form order-statistic bands for each 0.025 and 0.975 quantile
using the 0.025/0.975 binomial count quantiles. A positive exclusion is robust
to this rank uncertainty only if the band around the lower percentile remains
above zero; a negative exclusion only if the band around the upper percentile
remains below zero. Otherwise label the nominal exclusion
bootstrap-boundary-sensitive. Keep the ordinary percentile interval visible.
These are pointwise computational-precision bands, not simultaneous intervals
or corrections for ecological multiple testing, bootstrap validity or map
generalization. This rule responds to the diagnostic and is retrospective.

Six of eleven nominal exclusions were sensitive in the initial 1000 draws.
One uniform 10,000-draw refinement was therefore specified and completed,
using seed 20260918046 and the same archived histories and pairing. It gives
nine nominal exclusions, seven retaining exclusion under the rank check, at
each bank. The remaining two borderline contrasts stay unresolved. No new
process or calibration histories were generated and no further resampling
was used to seek a different classification.

## Disposition

Close the bounded equal-effort sampling comparison as a conditional
synthesis: no general sampling-design effect is resolved at this replication,
with the barrier fivefold accuracy/span pattern as the principal candidate
exception. Coverage and null-truth false exclusion are calibration checks,
not sampling-benefit evidence. The [interpretation correction](calibration-interpretation-correction-2026-09-18.md)
supersedes the initial coverage-trade-off wording. No equivalence is claimed.
The [synthesis](synthesis.md) reports absolute recovery, paired comparisons,
map variation, explanatory context and numerical limitations. The
[independent review](endpoint-final-review-2026-09-18.md) defines the closure
boundary.

No fourfold calibration campaign is launched: the diagnosis supports possible
precision gains for width, but the goal has no unmet prespecified precision
target requiring that extension to report the current conditional result. The
0.25-SE comparison remains a descriptive sensitivity tolerance, not a new
universal convergence gate. Original failures remain failures; this amendment
permits archival conditional reporting, not a claim of numerical accuracy or
prospective qualification. No replacement integrator is adopted.

## Preserved boundaries

The original four final-bank failures, Goal 047 regulariser sensitivity and
Goal 048 failed corridor qualification remain evidence. Nested-bank agreement
does not bound absolute integration error or substitute for independent
bank replication. The existing alpha and independent-bank diagnostics cover
specific stress cases, not the full map/effect/lane ensemble. A retrospective
endpoint-stability result cannot be called prospective method qualification.

The known-speed pseudocount-free route is a candidate if necessary. Its one-map
null-width pilot does not qualify all outcomes or provide a full-route cost
estimate. Any new process campaign requires a scoped timing check, finite
resource ceiling, independent banks and conditional-arithmetic controls before
dispatch. Escalation beyond a modest bounded campaign is a consult trigger.
Do not extend the calibration ensemble merely to chase significant effects.

Accepted Arc 2 classifications are preserved. Parameter supports may be
described as truth-calibrated nominal 95% supports, while bootstrap confidence
intervals for operating-characteristic contrasts retain their name. Removing
coverage from prior classification rules is outside this Arc 3 completion.
