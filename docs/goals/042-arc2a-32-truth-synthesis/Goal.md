# Goal 042: Arc 2A 32-Truth Synthesis

## Programme role

This goal closes the first predator-only recoverability block for Charter
Pillar 2 and Roadmap Arc 2A. It combines the accepted `S01-S16` pilot and the
prospectively evaluated `S17-S32` block only after preserving Goal 041's held-
out scores.

## Scientific question

Across the frozen reference landscape and observation design, what have the 32
truths established about recovery of spread rate, habitat-resistance contrast,
and detection probability, and is further Arc 2A simulation likely to change
that conclusion?

## Frozen evidence

- Goal 039's accepted `S01-S16` production bundle;
- Goal 040's selected low-order model forms and thresholds;
- Goal 041's accepted `S17-S32` bundle and prospectively frozen scores; and
- the accepted Arc 2A domains, likelihood, neutral comparator, calibration,
  validation, and common-random-number design.

Goal 041's prospective scores are the primary evidence about generalization.
They must be copied into the synthesis before any combined refit is interpreted.

## Analysis contract

1. Reconcile exactly 32 continuous truths, each with 250 paired validation
   histories and unique IDs `S01-S32`.
2. Preserve Goal 041's prospective skill, threshold accuracy, and error-
   envelope coverage unchanged.
3. Refit the accepted Goal 040 forms on all 32 truths without model reselection:
   additive models for detection-probability and resistance interval widths,
   and two-way-interaction models for resistance exclusion and held-out Brier
   difference.
4. Use 1,000 paired bootstrap resamples of validation-history index for Monte
   Carlo intervals. Treat these as simulation precision, not total response-
   surface uncertainty.
5. Do not refit boundary-contact probability. Show the 32 observed values as
   a truth-level support-topology diagnostic because its frozen smooth surface
   failed prospective validation.
6. Summarize point recovery, calibration, predictive advantage over neutral,
   and the isolated `S20` coverage flag. Do not convert one simultaneous Wilson
   miss into a systematic undercoverage claim.
7. Produce one plain-language review, compact tables, and one candidate Arc 2A
   figure. The figure is a review surface, not a submission-ready graphic.

## Decision rule

Recommend `arc2a_ready_for_closeout_with_topology_limit` when:

- all 32 truths reconcile and satisfy the accepted point-error limits;
- the process model outpredicts neutral at all 32 truths;
- the four retained smooth outcomes have finite combined fits;
- the prospective evidence remains positive for detection precision,
  resistance precision, resistance exclusion, and predictive advantage; and
- no evidence justifies targeted enrichment beyond local contour refinement.

Otherwise recommend a named redesign or bounded follow-up only when the failed
condition could materially change an Arc 2A conclusion.

## Review bundle

Write exactly eight ignored files under `artifacts/goal042_arc2a_synthesis/`:

- `combined_condition_outcomes.csv`;
- `prospective_evidence.csv`;
- `combined_surface_coefficients.csv`;
- `combined_surface_grid.csv`;
- `support_topology_points.csv`;
- `synthesis_summary.json`;
- `synthesis.md`; and
- `arc2a_recoverability_synthesis.svg`.

## Success and stop rules

The goal succeeds when the evidence sources reconcile, the prospective result
is visibly separated from the combined descriptive refit, the Arc 2A claims
and limits are intelligible without implementation jargon, and the decision
rule is applied. Stop after one focused scientific and visual review. Do not
add simulations, targeted points, flexible emulators, new landscapes, prey,
or local contour polish.

## Authority and boundaries

Barry approved Goal 042 on 30 August 2026. Local implementation, ignored
artifact generation, exact-path commits, and review-branch publication are
authorized. Canonical `main` publication remains a later human decision.

Do not change the accepted experiment, thresholds, input evidence, selected
model forms, factor domains, likelihood, or neutral comparator. Do not start
Arc 2B or the Arc 2A consolidation tranche.

## Observed outcome

The synthesis reconciled all 32 truths and their paired 250-history validation
blocks, preserved the five Goal 041 prospective scores unchanged, and completed
the four fixed descriptive refits with 1,000 paired bootstrap resamples. The
exact eight-file ignored review bundle was written under
`artifacts/goal042_arc2a_synthesis/`.

All 32 truths met the accepted median point-error limits. The largest observed
median errors were `0.053` for log spread rate, `0.125` for resistance
contrast, and `0.020` for detection probability. Every process model had lower
mean held-out Brier error than its fitted time-only neutral comparator.

The primary prospective evidence remained decisive: detection-probability
precision (`skill = 0.842`), resistance precision (`0.314`), resistance
exclusion (`0.202`), and predictive advantage (`0.879`) all beat their frozen
first-block mean comparators. Boundary-contact probability did not
(`skill = -0.234`), so it was not refitted and remains an observed truth-level
support-topology diagnostic.

The combined descriptive fits had positive leave-one-truth-out skill for all
four retained outcomes. Resistance intervals were strictly broader than the
accepted `0.75` limit at `S10` and `S19`; `S19` had already been correctly
classified by the prospective surface. The only calibrated-coverage Wilson
interval not containing 0.95 was the previously identified `S20` flag. Neither
finding justifies local enrichment under the prespecified stop rule.

The outcome is `arc2a_ready_for_closeout_with_topology_limit`. This is a
conditional result for the accepted landscape, access network, observation
schedule, likelihood, and process model. The next tranche, after Barry's
review, is bounded Arc 2A code consolidation rather than further simulation.
