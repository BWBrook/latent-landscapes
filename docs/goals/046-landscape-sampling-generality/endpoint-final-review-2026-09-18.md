# Independent review of Arc 3 conditional closeout

**Subsequent correction:** Fable's message 247 identified a material omission
in this review and the initial synthesis: coverage contrasts under
truth-specific calibration were incorrectly used as sampling-benefit
evidence. The [calibration correction](calibration-interpretation-correction-2026-09-18.md)
supersedes that interpretation and records a targeted methodological check.
The original verdict below is retained as the historical review record, not
as validation of the superseded coverage-trade-off narrative. Conditional
closure and the original numerical failures remain unchanged.

18 September 2026. Reviewer: the independent native scientific reviewer
`arc3_amendment_review`, with read-only ownership. Astra integrated the review;
the reviewer did not implement the audit or write the synthesis. This is an
internal scientific audit, not external peer review or independent empirical
replication. Barry delegated the completion choice in the instruction quoted
in the [amendment](endpoint-amendment-2026-09-18.md).

## Final verdict

The reviewer supplied this final assessment after inspecting the refined
results and synthesis:

> **GO for conditional archival closure.**
>
> The evidence supports closing Arc 3 as a mixed, landscape- and
> outcome-dependent comparison. It supports neither a general
> balanced-sampling advantage nor a blanket ecological null. The 10,000-draw
> refinement leaves 7 rank-robust and 2 unresolved nominal exclusions,
> identically classified at both archived banks.
>
> The original numerical qualification still failed. Nested-bank stability
> does not establish convergence, bound shared bias, or qualify the
> integrator generally. Inference remains conditional on three matched map
> triplets, oracle calibration, correlated endpoints and unadjusted pointwise
> intervals.
>
> No further simulations are justified for this bounded conclusion. Update
> the amendment status, roadmap and handover from ongoing/paused to
> conditionally complete.

The earlier detailed review covered the charter and Goal 046 contract,
Goal 046–048 numerical diagnoses, endpoint and variance audits, refined
bootstrap, provenance, synthesis and figures. It confirmed reporting of
absolute recovery, common-holdout prediction, support summaries, map
variability and explanatory landscape/event descriptors. No material
scientific repair remained. The matched-triplet wording and distinction
between nominal and finite-bootstrap-stable exclusions were incorporated
before this final verdict.

## Verification and disposition

The parent independently reproduced the percentile/rank classifications and
confirmed zero interval-sign or rank-sensitivity changes across all 90
archetype endpoints between the archived banks. Point estimates reproduce
the original table exactly. Three resamples for each of 18 map-bank pairs
replay the existing analysis to at most 5.38e-16 absolute difference; the
explicit 1e-12 check tolerance covers floating-point reduction order only.
Two direct conditional-variance calculations independently match the audit.
Artifact hashes and the final checks are in the
[original verification receipt](../../../artifacts/arc3_calibration_wording_20260918/before/artifacts/arc3_endpoint_synthesis_20260918/final_verification.json).

The rank check is retrospective relative to the ecological experiment and
was specified before the single 10,000-draw computational refinement. Its
retained exclusions address only finite-bootstrap precision, not shared
integration error, multiplicity or unobserved landscapes. The two remaining
borderline contrasts are reported as unresolved, with no further resampling.

The reporting amendment, synthesis, Goal 046 status, README, roadmap and
handover now record conditional closure. The four original numerical
failures, regulariser sensitivity and failed corridor prototype remain
unchanged. No model code, estimand, observation design, recovery
classification or integrator adoption is changed by this review.

Stronger numerical-accuracy or generality claims require another bounded
qualification study. No such campaign, commit, push or publication was
launched as part of this closeout.
