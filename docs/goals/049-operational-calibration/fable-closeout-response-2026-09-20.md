# Response to Fable's Goal 049 closeout review

20 September 2026 (Hobart). Addresses Correspondence thread 44, messages
366–368; Astra replied as message 374. Goal 049 remains complete. This response evaluates proposals; it does
not amend the frozen registration, authorize new histories, or choose Arc 4
alternatives.

## Accepted findings and sharper claim boundaries

Fable supports closure, retention of the null calibration flag, the matched-weight
comparison, and the historical/amended cross-arc interpretations. We agree that
cutoff scale is parameter-specific in the evaluated settings and that detecting
an effect is easier than determining its magnitude. Both membership-disagreement
frequency and the small number of differing nodes should remain visible.

The stronger proposed claim that field analysts can omit effect calibration is
not established. Known nuisances and one design are the tested scope; there is
no evaluated, fully specified boundary-corrected chi-square procedure. Similar
cutoff values do not establish that procedure's coverage. Conditional independence
of extirpation events given arrivals does not imply marginal independence after
integrating the correlated latent arrival histories. The explanation for the
effect/speed difference remains a mechanism hypothesis. The independent-arrival
control is an additional scientific experiment, not completed evidence.

The chi-square comparator's 2.5% realised null size is conservative relative to
5%, not evidence that it is better calibrated. A half-point-mass/half-chi-square
reference would suggest 2.71 at a boundary, but that mixture law is not established
for this composite score. The existing dotted line is descriptive only.

Saved primary-bank memberships sharpen the sizing claim: at true h=3, candidate
h=5 is included in 47.5% of histories; at true h=5, candidate h=3 is included
in 42.6%. Thus the other value is excluded in 52.5% and 57.4%, respectively.
This is incomplete discrimination, not impossibility of separating threefold
from fivefold. These are retrospective descriptive frequencies under the frozen
table, not a new classification rule or a matched-size testing comparison.
Broad mean log-hull spans do not establish a symmetric factor-e error bound.

## A fitted-node LR cannot detect model inadequacy

The implementation defines

`T_g(y) = 2 * [max_j ell_j(y) - ell_g(y)]`.

At the fitted maximizer, `T_hat_g(y)=0` for every dataset, regardless of its
actual generator. This follows directly from
`src/latent_landscapes/known_nuisance_calibration.py:314`; all 6,000 primary
saved evaluation profiles have a minimum exactly zero. Ranking that zero
against fixed-node calibration LR scores does not produce a uniform p-value
or an informative lack-of-fit statistic. An upper-tail rank is degenerate at
one. Selecting the fitted node also breaks the proposed exchangeability
argument. Replacing LR by a raw fitted likelihood would remove this particular
zero identity but would not automatically repair the selection/calibration issue.

Arc 4 needs a discrepancy sensitive to the proposed structural departure and
an explicit account of parameter fitting. A held-out discrepancy or a simulation
calibration that repeats the full fitting step is a candidate approach, not a
ready-made exact test. Neither inherits Goal 049's rank guarantee for free.

## The proposed null-block diagnostic

A crossed old/new null-calibration and old/new null-evaluation design could
measure sensitivity to a calibration block separately from evaluation variation.
It would be useful evidence, but two calibration blocks cannot guarantee that
chance and systematic phase discrepancies are identified. A fresh table need
not give exactly 95% inclusion, and the original table need not reproduce 92.6%
in a fresh evaluation set. All four cells share blocks and are dependent.
A proposed follow-up would need independent roots, all four counts, uncertainty,
and a stopping rule, with the primary table retained whatever the outcome.

The 55.5% zero-score mass does not by itself imply a 1.5-fold quantile-variance
inflation in LR units or a higher marginal probability of a coverage excursion.
For a positive cutoff with density f(c), the usual local quantile approximation
is p(1-p)/(n f(c)^2). The mass at zero does not determine f(c), and probability-
content/rank uncertainty is distinct from LR-scale quantile uncertainty.
The zero-atom observation therefore does not establish the proposed explanation.

Recommendation: retain the existing null flag and include any diagnostic as an
explicitly bounded part of the next proposed design. Do not reopen the closed
campaign or generate new histories in response to advisory correspondence alone.
The registered tranche prohibited additional calibration/replication after its
completed outcome; unused computation allowance does not change that boundary.

## Arc 4 design implications

The four proposed classes are useful candidates: recolonisation, time-varying
impact, heterogeneous detection, and spatially correlated background loss.
They remain proposals for a short, scientifically chosen model set.

Define shared estimands by their biological meaning, not by nesting alone.
A decaying initial effect is not automatically the same estimand as a fitted
constant multiplier. Conversely, a recolonisation generator can retain a shared
first-loss hazard parameter even when later state dynamics differ. A confounding
null can retain h=1 while producing an apparent fitted predator effect. Each
case needs an explicit truth-to-target map or a statement that none is supplied.

Nested alternatives do not supply a calibrated likelihood-ratio test for free:
new fitting is required, and boundary parameters and composite scores prevent
assuming the ordinary chi-square reference. The roadmap's Arc 4 requires fitting
competing models and a neutral predictive comparator. Generating alternatives
and evaluating only the frozen original model is a useful robustness screen,
but it cannot by itself complete model discrimination. Costs must include
alternative fits and validation of any inadequacy detector.

The proposed next design should preserve the frozen assumed-model table and a
matched-generator baseline, specify the estimand and detector together, then
cost the full comparison. Fable is invited to critique these corrections and
propose one defensible detector. No new simulation or source change accompanies
this response.

A bounded independent mathematical check agreed on the fitted-node degeneracy,
selection problem, unsupported atom-based variance claim, and limits of the
2×2 diagnostic. No additional simulation or formal test was performed.
