# Goal 040: Arc 2A Transparent Recoverability Surface

## Programme role

This goal completes the first analysis pass for Charter Pillar 2 and Roadmap
Arc 2A. It converts Goal 039's accepted 16-condition predator-only pilot into
an interpretable recoverability map without generating new simulations.

## Scientific question

How do spread rate, habitat-resistance contrast, and per-visit detection jointly
affect parameter precision, resistance discrimination, support integrity, and
predictive value under the frozen reference experiment?

## Frozen inputs

- the 16 continuous Sobol truths and paired validation histories from Goal 039;
- the separate `eta = 0` diagnostic as an overlay only;
- `log2(rho)`, `eta`, and `p` on their approved Arc 2A scales; and
- the accepted Goal 039 metrics, thresholds, neutral comparator, and common
  random-number structure.

## Analysis contract

1. Fit two transparent candidates for each decision-relevant response: an
   additive model and the same model with the three two-way interactions.
2. Retain the interaction model only when its leave-one-truth-out RMSE is at
   least 10% lower than the additive model; otherwise retain the additive form.
3. Model boundary-contact and `eta = 0` exclusion probabilities on an empirical
   logit scale. Model interval widths and held-out Brier differences on their
   observed scales.
   The 0.95 line for resistance exclusion is a descriptive plotting reference,
   not a new progression gate.
4. Preserve pairing by resampling validation-history indices jointly across
   all truth conditions when calculating Monte Carlo uncertainty. Separately
   use the selected model's leave-one-truth-out RMSE as a conservative surface
   error envelope; do not present paired bootstrap precision as total model
   uncertainty.
5. Show observed truth points on every fitted surface and report
   leave-one-truth-out predictions. A smooth surface must not hide a poorly
   predicted condition.
6. Treat uniformly successful point-error and calibration results as threshold
   checks rather than forcing uninformative surfaces through small residual
   variation.
7. Use the separate no-resistance condition only to verify boundary behaviour;
   exclude it from continuous model fitting.

## Required outcomes

- identify broad factor effects that are supported by leave-one-truth-out
  prediction;
- distinguish accurate point estimation from adequately narrow uncertainty;
- state whether the 16-point design is sufficient for the Arc 2A conclusion;
  and
- if more points are needed, name the single unresolved decision they would
  address rather than launching an automatic expansion.

## Review bundle

Write exactly eight ignored files under `artifacts/goal040_arc2a_surface/`:

- `condition_outcomes.csv`;
- `surface_coefficients.csv`;
- `leave_one_out_predictions.csv`;
- `surface_grid.csv`;
- `analysis_summary.json`;
- `review.md`;
- `recoverability_surface.svg`; and
- `leave_one_out_diagnostics.svg`.

## Success and stop rules

The goal succeeds when all 16 continuous truths reconcile with Goal 039, the
paired uncertainty analysis is reproducible, observed points remain visible,
and the design-extension recommendation follows from prespecified
leave-one-truth-out evidence. Stop after one focused repair pass. Do not tune
surfaces for visual smoothness or add a more flexible emulator.

## Authority and boundaries

Barry approved Goal 040 on 30 August 2026. Local implementation, ignored
artifact generation, exact-path commits, and branch publication are
authorized. Canonical `main` publication remains a later human decision.

Do not run new process simulations, extend to 32 Sobol points, add targeted
points, change Goal 039 data or thresholds, alter the landscape or observation
design, introduce prey dynamics, or start Goal 041.

## Observed outcome

The analysis reconciled all 16 continuous truths and the separate diagnostic,
then completed 1,000 paired validation-history bootstrap resamples. All point
error limits passed, every condition's coverage interval included 0.95, and the
process model beat its fitted neutral comparator at every truth.

Leave-one-truth-out prediction supported useful low-order structure for
boundary contact, detection-probability interval width, resistance exclusion,
and held-out predictive advantage. Their selected surfaces reduced squared
prediction error relative to a mean-only predictor by 64%, 53%, 50%, and 93%,
respectively.

Resistance-contrast interval width was different: one condition exceeded the
accepted 0.75 limit, yet neither low-order candidate predicted a hidden truth
better than the mean-only comparator. Goal 040 therefore recommends
`extend_to_nested_32_for_eta_precision_validation`. The next nested block, if
approved, should test this one unresolved precision question and prospectively
validate the current surfaces. No new simulations were started here.
