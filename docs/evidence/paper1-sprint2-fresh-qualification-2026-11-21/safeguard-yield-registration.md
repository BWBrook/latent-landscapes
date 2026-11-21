# Prospective safeguard-yield analyses

This registration implements Correspondence 3617 and 3618 for the next 207-dataset panel. It advances the Paper 1 profile qualification decision in Sprint 2. The primary run and its qualification verdict use tight replay, the production numerical latent-mode audit and the 18 exhaustive-audit fits. Both analyses below are secondary reductions of that same panel. They perform zero additional fits, likelihood evaluations or latent-mode solves. Training and validation require their existing separate decisions.

## Standard search before tight replay

The first standard `close_profiles` call in `PanelSearch.run` returns eight cutoff sets and the family switches before any tight operation. Up to that point, `fixed_fit` and `free_fit` events contain the latest eligible raw family winners and envelope criterion at each exact retained log-h and at the free maximum. Freeze that prefix at the first tight operation. Record a guard failure as pre-tight only when the terminal `unresolved_fit` contains standard-labelled candidates exclusively, the root receipt records a terminal scientific failure and the nested search names the corresponding guard. Preserve other unlocated failures and unavailable streams as indeterminate.

An auxiliary checkpoint stores the already-computed eight levels and switches before the first tight operation. It binds those results to the frozen fit checkpoint identity, operation count and digest of the standard free and fixed winners. The reducer checks those winners independently against the hash-bound event prefix. Resuming through the boundary checks equality of the auxiliary payload. The checkpoint adds no new numerical evaluations and leaves the primary fit, search and event receipt schemas intact. Archived development fits lack this auxiliary checkpoint. The event prefix still identifies their exact sampled criteria and eligibility at the first tight marker.

The **final** standard-phase output belongs to the full procedure. The same-h loop acquires standard fits at tight-discovered locations. Later standard free fits take starts from the tight free endpoints and from the union of the standard and tight fixed candidates. Exposure can directly reuse tight sigma-zero rows. Both reduced families start their free fit from spatial standard and tight sigma-zero results, and both receive the post-replay standard mesh. There is no fitted exposure or constant-family result for a run stopping at this prefix.

For each fit, compare the pre-tight spatial envelope with the final primary tight spatial envelope. Use each view's own free score in `W(x) = 2 × (free criterion − fixed criterion(x))`. Compare the exact log-h intersection only, and count `|ΔW| > 0.001` with a strict inequality. Count h=1 separately as a subset of the profile comparisons. Compare the raw positive and zero family winners' eligibility at each paired coordinate and at the paired free fits. A failed effort to obtain an eligible family enters the fit-verdict denominator. An absent winner or coordinate is unavailable and supplies no paired comparison. Report the post-replay standard comparison with the same calculations as a descriptive check on prefix contamination.

Where the auxiliary checkpoint exists, compare its eight cutoff sets with primary tight's recorded sets using the existing within-fit topology, bracket, root and component-endpoint checks. Use the existing 0.005 log-h and 0.01 root-residual tolerances, and show both isolated-switch counts. These comparisons retain each view's recorded topology and use only saved results. They do not establish dense/lean or independent-bank agreement on the complete standard-prefix procedure. A primary common-anchor sidecar is built for post-replay nodes, free normalisers and level sets. For extra anchors it can use post-replay starts, and may omit pre-tight free locations or roots. Primary gradient sidecars use the final free parameters. Neither substitutes for an independently evaluated pre-tight procedure.

The full no-tight verdict is identifiable as a failure where a required fit has a verified pre-tight standard guard failure. Otherwise report it as indeterminate. The pointwise comparative data and cutoff topology do not supply the missing reduced-family, exact-common-anchor or gradient checks. This applies even when every paired spatial score and eligibility agrees.

## Numerical latent-mode audit omitted

Keep tight replay and each stored pre-audit fit. Remove only the `multimodal_latent` trigger and scientific errors attributable exclusively to `latent_audit` from the fit classification. Keep search, family, non-audit numerical and execution failures. If a rescued receipt does not have a resolved search and available spatial, exposure and constant reports, its pre-audit result is indeterminate. A fit without an indexed terminal receipt is censored, even if another fit completed or a scheduler attempt timed out during the audit. The analysis does not assume that omitting an audit would have avoided a walltime loss.

The 18 exhaustive-role fits remain required. Omit their numerical latent-mode audit check, including the all-location coverage and beyond-margin gain checks, when the fit itself has a verified resolved pre-audit report. Retain the dense/lean and bank comparisons, original bank identities, frozen free-gradient checks and any other numerical qualification checks. Keep the nine integration screens descriptive with their primary evidence and report the secondary **numerical** gate. An audited fit that became terminally non-resolved usually has no dependent common-anchor and gradient tasks because the producer schedules them only from resolved prerequisite fits. If removing the audit trigger exposes a comparison or derivative requirement with missing evidence, keep the case indeterminate. Verified sidecars remain bound to the original receipt hashes.

The audit reads fits that have already been reported, so all saved raw eligibility and W comparisons have zero change by construction. Counts of comparable endpoints are the available retained profiles and free family winners in those original reports. Distinguish structural zero change in an unchanged report from missing reports. Report audit flags, fit-class changes, dataset-verdict changes and indeterminate transitions separately. Qualification's `case_result` and required-check logic remain the reference for rescoring.

## Comparison and interpretation

Compare each secondary dataset verdict with the primary on the registered 207 addresses. Report passed, failed and indeterminate outcomes, the full paired transition table and changed verdicts among pairs with determinate results on both sides. Report fit roles against all 486 required roles, datasets with any and with all roles contributing paired LR data, and denominators for exact profile locations, h=1, and family eligibility comparisons. Missing evidence and locations outside the shared h support stay visible. Do not treat the number of observed changes in a censored comparison as a full-panel zero.

For each variant use the registered numerical gate. Base denominators remain nine maps of 18 datasets for A/B/C and nine of 12 for A/B. The 45 non-base cases retain their separate zero-failure rule. The reducer records the complete-panel gate where identified, and when incomplete reports definite failures, indeterminate non-base cases, and the exact possible score range and possibility/guarantee of meeting both base thresholds over all assignments of unresolved dataset verdicts. These are completion bounds. The empirical score is not monotone in each map's failure count, so imputing every unknown as success or every unknown as failure need not attain its extrema. The two score bounds are computed separately for A/B/C and A/B. A known base A/B failure forbids the C-only fallback. The primary packet status remains that of the unchanged primary reducer.

A definitive no-effect result can inform a later Barry decision about training only with complete paired verdict evidence for that safeguard. For the standard prefix, small spatial differences support agreement on the observed coordinates. They cannot justify dropping tight replay from a three-family procedure. Unresolved audit-only rescues show audit yield at the fit level and leave their effect on full qualification uncertain. Any later proposal to omit a safeguard must make those limitations visible and preserve the primary qualification result.

## Execution from immutable evidence

After both primary reduction and required twin review, pass the same frozen panel, final qualification index and primary summary to the standalone secondary reducer. Preserve the indexed fit receipts, nested search receipts/event streams, and each fit task's identity and pre-tight topology checkpoint in their existing directory layout. The result records the panel, final index, primary receipt summary, fit, search, event stream and available auxiliary topology digests.

```sh
python scripts/sprint2_safeguard_yield.py \
  --panel "$PANEL" --index "$FINAL_INDEX" --primary-summary "$PRIMARY_SUMMARY" \
  --output "$OUTPUT/safeguard-yield.json"
```

The accepted old replay provides a pre-draw extraction check only. Its own 24 comparison tasks and 12,460 old-anchor checks compare candidate and archived fits. They do not supply the new pre-tight common-anchor, gradient, or reduced-family counterfactuals. Running on the 51 frozen terminal fit receipts recovers 49 prefixes and the two verified pre-tight corridor-1 window-low B failures. Every resolved fit has standard events after the first tight marker. These add 1,047 standard locations in total, and 22 standard free scores differ from their prefix values. The prefix and final tight views share 4,330 exact profile locations. There are no absolute W changes greater than 0.001 or raw eligibility changes among the 8,758 paired endpoint checks. Maximum absolute W change is 1.80349 × 10⁻⁶ against tight and 1.34015 × 10⁻⁹ against post-replay standard. The numerical audit did not change any of the 51 selected fits' classes. These selected development observations do not estimate fresh-panel safeguard yield.

```sh
python scripts/sprint2_safeguard_yield.py \
  --development-raw artifacts/sprint2/boundary-resume-20261121/raw \
  --output artifacts/sprint2/fresh-qualification-20261121/yield-development.json
```

Development extraction SHA-256 `0a792bc2341d5aef8dd370156caef1029901eb3fed57c04a30dd102acbe2eb48`.
