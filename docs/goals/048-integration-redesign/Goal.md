# Goal 048: integration redesign with exact numerical controls

Status: **complete, with a finite-budget pilot failure**, 12 September 2026.
The infection-order prototype passes exact controls, but its K1024 corridor
profiles do not stabilize. The reviewed result and next diagnostic are in
[results.md](results.md) and [final-review.md](final-review.md). No adoption or
production requalification follows from this completion.

Barry requested: “Proceed,
as autonomous as is feasible please,” following the recommendation to develop
a reviewed integration redesign addressing pseudocount-sensitive widths and
bank-sensitive corridor tails. The authorized development and retrospective
pilot are complete; further order-variance diagnosis is the next proposed tranche.

## Destination and completion condition

Advance Charter Pillar 3 / Arc 3 by identifying and implementing a defensible
replacement integration calculation, with exact or independently qualified
small controls and a concrete validation plan. Complete at a reviewed,
evidence-backed method recommendation: a mathematically valid candidate with
bounded numerical and feasibility evidence, or a demonstrated obstacle that
requires a new scientific choice. A design memo alone is insufficient where
a reversible prototype can resolve the issue.

The biological generating model, observation design, site-marginal composite
likelihood and ecological estimands remain fixed. The approved work includes
mathematical derivation, source inspection, small independent reference
calculations, prototype implementation, tests, and bounded retrospective
numerical diagnosis. Numerical approximation choices inside that scope can be
settled autonomously. No candidate is selected from favourable ecological
results. Preserve all Goal 046/047 failures and frozen inputs.

## Initial route

1. Exploit the accepted independent exponential edge weights to derive
   conditional integration methods. Compare target-deleted neighbourhood,
   global Gamma scale and infection jump-chain formulations, including their
   support, residual variance and computational cost.
2. Construct exact small-graph controls, retaining predator/prey arrival sharing,
   survey categories and survival moments. Separate algebraic correctness,
   floating-point accuracy and Monte Carlo approximation error.
3. Implement the strongest tractable candidate and compare with the exact
   controls. Use a bounded old-stress feasibility check when informative;
   predeclare its bank/history subset and limits before outcomes. These are
   developmental diagnostics, not prospective all-map qualification.
4. Independently review the derivation, numerical evidence, practical cost and
   proposed next validation. Do not equate repeatability with exact accuracy.

## Operating envelope and review boundary

Work in this repository; keep accepted production kernels and previous source
snapshots unchanged. Use the Mac mini for short prototype and exact-reference
checks. Existing deep-server-ts resources and the named Nectar routing documents
may be used for a bounded diagnostic if local measurements justify it; record
its cost and stopping bounds before dispatch. No cloud resize, new external
service, legacy-repository access or sibling modification is authorized.

No production requalification, ecological synthesis, changed estimand or
observation model, relaxed acceptance threshold, unbounded simulation campaign,
commit, push or publication is authorized. A replacement method's adoption or
new inferential claim remains a scientific review boundary. Bring a concrete
recommendation and evidence to that boundary, rather than requesting approval
for each routine implementation step.
