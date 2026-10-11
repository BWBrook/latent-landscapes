# Goal 062 amendment: ten-cell exact-family and B100-A evaluation

11 October 2026 (Hobart). **Approved scope; independent amendment review and
implementation qualification precede production.** This amendment advances
Charter Pillar 4 by adding a specific model-misspecification comparison to the
final procedure's recovery, declaration and prediction evaluation.

## Authority and precedence

Barry's [submitted decision](../../decisions/1c886620-8524-4d69-8585-3b5ef960bea3.md)
selects “Amend first: add the cells chosen below, have the amendment reviewed,
then launch without returning to me”, with B100-A h=1 and h=3 at both
background levels. Exact-family h=2 was not selected. The decision covers
implementation, qualification, the bounded deep-server run and independent
audit as one tranche. Barry confirmed this in chat: “Approved with some
amendments. Claude has posted details on correspondence.”

The decision JSON's canonical SHA-256 is
`19cbc3060978354d40c4a9f34fef4832555439907b1ec8205cde8bd43f84ad69`, independently
matched to the Decision Inbox response. Correspondence discussion 86,
messages 1453–1455 and 1478, supplies Claude's review and the amendment details.

The [original registration](registration-2026-10-11.md), original
[compute estimate](compute-estimate.md) and [review](design-review-2026-10-11.md)
remain unchanged. This amendment supersedes their six-cell counts,
exact-family-only scope, resource estimate and unapproved-launch status.
Every other scientific, fitting, scoring, audit, stopping and resource rule
remains in force. The [amended cost estimate](compute-estimate-amended-2026-10-11.md)
and [amendment review](amendment-review-2026-10-11.md) are the current companions.
This is a prospective amendment before any Goal 062 production history.

## Fixed cell table and generating laws

| Index / label | Background | h | mu per day | Generating beta | Detection SD | Histories |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 0 / L1 | exact | 1 | .001 | .50 | .20 | 500 |
| 1 / L3 | exact | 3 | .001 | .50 | .20 | 500 |
| 2 / L5 | exact | 5 | .001 | .50 | .20 | 500 |
| 3 / H1 | exact | 1 | .004 | .50 | .20 | 500 |
| 4 / H3 | exact | 3 | .004 | .50 | .20 | 500 |
| 5 / H5 | exact | 5 | .004 | .50 | .20 | 500 |
| 6 / B_L1 | B100-A | 1 | .001 | not defined | .20 | 500 |
| 7 / B_L3 | B100-A | 3 | .001 | not defined | .20 | 500 |
| 8 / B_H1 | B100-A | 1 | .004 | not defined | .20 | 500 |
| 9 / B_H3 | B100-A | 3 | .004 | not defined | .20 | 500 |

Cells 0–5 retain their original law, indices and seed addresses. For cells
6–9, reuse the existing capstone B100-A generator without changing its law:

`G ~ fixed Gaussian field sampler; z = .7 A + sqrt(.51) G`

`lambda_i = mu exp(sqrt(log(2)) z_i) / mean_all(exp(sqrt(log(2)) z))`.

The fixed sampler uses the 72×84 map, a 142×166 circulant embedding and
covariance `exp(-distance/10)` in grid-cell distance. It does not standardize
individual field realizations. Normalization is over all 6,048 map cells,
not the training sites. Generate a fresh field independently for each B100-A
history, independent of its spread, prey loss and observation streams. The
map, exposure A, site design, arrival integration bank and numerical rule
remain fixed. This reproduces `capstone_public.generate_b100_history` and the
existing sampler; no alternative B100-A implementation or field selection
is introduced. The field is stochastic background structure, not a new map.

There is no generating adjusted-model beta under B100-A and no true nuisance
grid node. An implementation placeholder beta passed through an old data
class must never be reported as truth. The whole-map mean hazard is mu by
construction, while fitted mu and beta are parameters of a misspecified
working model. Physical h remains the generating post-arrival hazard
multiplier; it need not equal a pseudo-true fitted-model parameter.

## Independence, addresses and freeze

There are **5,000 independent complete histories**, 500 per cell, with no
cross-cell common random numbers. The four fitted candidates remain paired
within a history. Keep evaluation root 2026101101, namespace 62, domain 1 and
addresses `[root,62,1,cell,replicate,stage]`. Replicates are 0–499. Stages 1–5
retain spread, prey loss, predator visits, site detection and prey visits.
Add **stage 6, background_field**, only for B100-A cells 6–9. Derive seeds by
the original first-uint64 SeedSequence convention and use PCG64.

Freeze and verify **27,000 stage addresses/seeds**: 25,000 for stages 1–5 in
all ten cells, plus 2,000 B100-A field seeds. This preserves the original
15,000 exact-cell addresses. Check address and derived-seed uniqueness and
separation from reference, bank and mechanical streams. No production
preview, replacement seed, field filtering or selection of survivors is
permitted. Preserve all generated observations, fields or their exact replay
bindings, and failures at their original addresses.

Bootstrap root 2026101102, namespace 62 and domain 2 extends to cells 0–9.
The original 2,000 whole-history resamples per cell, percentile interval,
Type-7 quantile and undefined-draw rules apply unchanged. Between-cell
contrasts use independent cell resamples, including matched exact/B100-A
comparisons. “Matched” means common h/mu/design, not paired stochastic draws.

## Procedure, outcomes and interpretation

Use the same four candidates and observed-nuisance calibration rule in all
ten cells. B100-A truth and field values are never fitting, screening or
calibration inputs. **No B100-A reference tables or recalibrated cutoffs** are
introduced. Complete and audit the same full 765-node exact-family reference
panel before evaluation: 466 missing tables and 465,534 new references.
Both fitted background candidates omit the B100-A residual field. An exact
versus B100-A contrast changes the generating hazard structure, including its
heterogeneity and exposure relationship; it does not causally isolate model
misspecification or establish background-family identification.

The original four primary outputs apply in every cell: declaration,
abstention, the three all-history h-recovery categories, and the two paired
valid held-out score contrasts with unavailable-pair counts. Every operating
proportion retains denominator 500. Keep all ten cells visible; do not pool
families. The same physical within-1.5-fold h-recovery threshold and all
numerical-failure rules apply to B100-A.

For exact cells, retain true-node screen retention and mu/beta/SD errors.
For B100-A, true-node retention and beta error are **not applicable**, not
zero or failed. Report the fitted beta distribution and boundary mass as
working-model diagnostics. Report fitted mu deviation from generating
whole-map mean mu explicitly as a descriptive working-model discrepancy;
it is not recovery of a guaranteed pseudo-true parameter. Detection-SD and
physical-h errors remain descriptive deviations from their generating values.
Use the existing secondary absolute-log-h-error quantiles and boundaries.

The B100-A results estimate operating performance averaged over the registered
fresh field and process/observation histories, conditional on the fixed map,
design, numerical bank, algorithm and single reference panel. They are a
specific **descriptive robustness test outside the nominal guarantee**.
B100-A false declarations above .05 do not contradict the exact-family
on-grid theorem; rates below .05 do not establish a misspecification guarantee.
Display each h=3 result beside its same-family, same-mu h=1 result. The
original conditional-null flag relative to .05 remains an exact-cell
diagnostic only; B100-A comparisons to .05 are descriptive.

No exact-family h=2 cell, B100-A h=5 cell, new landscape, regenerated
reference-panel ensemble, confidence-coverage study or background-family
classifier is added. Predictive scores still condition on held-out predator
observations and the same realized history, with no refit or model selection.

Claude's beta interpretation concern is retained as a qualified expectation.
The earlier known-nuisance Goal 054 rule declared at h=3 in 93.0% of beta=.60
histories versus 76.1% at beta=0, and the advisory complete-data calculation
found less slope-estimation inflation at positive beta. This suggests the
chosen exact-family beta=.50 can be favourable for sensitivity; these anchors
must not be presented as typical of beta=0 or a general nuisance surface.
That is evidence from another procedure and an information approximation,
not a demonstrated direction or magnitude for the final observed-nuisance
rule. State this limitation beside the sensitivity results without retuning
the approved beta or adding an unapproved beta=0 cell.

## Expanded checks, cost and execution boundary

Check all **20,000 main fits** and held-out candidate scores; reconstruct all
**5,000 observed screens, statistics and declarations** and replay all 5,000
complete generators, including every B100-A field. Preserve the original
independent source-level audit boundary and tolerances.

Extend the diagnostic subset to replicates 0–4 in each of ten cells:
**50 histories, 22,150 profile points and 67,500 lower-bound lattice points**.
The same diagnostic non-interference rule applies. The lowest-ID-per-cell
failure examples can add at most 40 selected histories across the four
registered failure categories before any further justified expansion;
previously profiled cases need not be duplicated. Routine h=1 boundary
estimates do not trigger additional profiles. Additional diagnosis must fit
inside the campaign envelope or stop pending for a decision.

The amended planning range is **46–57 elapsed compute hours** at up to
51 workers, with unchanged 64 GiB aggregate RSS, 50 GiB free scratch and
**72-hour hard wall ceiling**. It is an allowance, not a guaranteed completion
time. The reference workload is unchanged; evaluation, diagnosis and reporting
increase. Qualify and benchmark both exact and B100-A paths with mechanical
or existing public fixtures before any production draw. A measured projection
outside the envelope, a scientific method/runtime/source change or another
material scope change returns to Barry. Ordinary checkpoint recovery and
registered diagnostics proceed autonomously.

After independent review of this amendment, the approved tranche proceeds
through implementation, independent qualification, custody verification,
benchmarking, reference completion/audit, evaluation, independent audit and
reporting. No additional human approval is needed for these registered stages.
