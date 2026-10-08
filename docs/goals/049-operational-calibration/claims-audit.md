# Read-only claims audit for the operational-calibration proposal

19 September 2026. **Findings for critique; no historical classifications or
accepted syntheses changed.**

Update, 20 September: this dated audit is preserved; the reviewed
[interpretation amendments](interpretation-amendments.md) have now been applied
to the syntheses, with original classifications retained alongside the
retrospective rule. This audit covers the principal Arc 1 and Arc
2A–2C syntheses and the calibration/classification paths supporting them. It
does not claim to revalidate every historical experiment. A scientific audit
delegate located the evidence; Astra checked the consequential classification,
joint-support and transport points against their source records.

For exchangeable tie-free scores, a rank-k cutoff from n calibration histories
has marginal same-truth coverage k/(n+1). Inclusive ties can raise coverage;
conditioning on the realised cutoff is different from averaging over its
simulation. Thus local coverage is a calibration check. Null-truth exclusion
is its complement only when the tested null is that generating truth. Non-null
exclusion remains informative, but under the historical oracle cutoff it is
not automatically the power of one analyst-usable, fixed-size null test.

Width and topology remain observed properties of the stated calibrated
supports. Their dependence on the calibration construction must be explicit;
they are not stand-alone rankings of information. Point error and held-out
prediction do not depend on these cutoff choices.

## Arc 1: several calibration regimes, not one uniform procedure

The [reference synthesis](../../arc1-reference-laboratory-synthesis.md),
especially its evidence matrix and frozen uncertainty language, mixes
positive controls using different budgets and targets. For example:

- [Goal 005](../005-stochastic-one-rate-cross-rate-recovery/Goal.md), lines
  114–148: 500 calibration histories, rank 476, 500 validation histories per
  spread truth, plus a genuinely separate transported-cutoff diagnostic.
- [Goal 018](../018-detection-probability-positive-control/Goal.md), line 14
  onward: the 500/476/500 design for a detection positive control.
- [Goal 033](../033-parameter-specific-uncertainty-calibration-diagnostic/Goal.md),
  line 24 onward, and [Goal 036](../036-prey-effect-background-risk-reference-closure/Goal.md),
  line 31 onward: 2,000 calibration histories, rank 1901, 1,000 validation
  histories for the prey/parameter-specific reference evidence.

The tie-free coverage benchmarks are respectively 476/501 and 1901/2001.
Local coverage contributes no independent evidence that the ecological
parameter is learnable. The error, non-null exclusion, topology, conditional
width and prediction observations remain. The threefold–fourfold bracket
also has a width basis: the threefold case failed width as well as coverage.
The low-background fivefold case has topology/width failures independent of
coverage. These are still oracle-support findings, not field-transfer results.

The [Goal 005 review](../../../artifacts/goal005_stochastic_one_rate_cross_rate/review.md)
records `one_rate_recovery_robust_cutoff_nontransportable`. A central-speed
cutoff was evaluated at flank truths separately from local calibration.
That is real evidence about transport and a precedent for Goal 049, not a
same-truth coverage finding to demote.

**Proposed handling:** preserve the reference ladder and historical gates;
annotate which parts show point recovery, prediction or conditional support
resolution. Present same-truth coverage as calibration quality control.
Avoid turning projected or simultaneous-region statements into claims about
operational marginal intervals without a separate construction.

## Arc 2A: joint coverage and projected precision

[Goal 042](../042-arc2a-32-truth-synthesis/Goal.md), lines 35–60, identifies the
retained response surfaces and closeout criteria. The campaign uses a
truth-specific rank-239-of-250 joint three-parameter score. The
[support constructor](../../../src/latent_landscapes/arc2a_likelihood.py),
lines 182–237, tests joint truth inclusion and separately reports projected
widths. Its coverage is joint-region coverage. One must not apply the exact
zero-contrast argument indiscriminately to marginal coverage of projections.

The S20 coverage flag is a finite calibration/evaluation diagnostic, not
evidence that its ecological condition causes deficient coverage. The
campaign classifier can fail on coverage, but Goal 042's final closeout rule
does not require it: point error, prediction and prospective performance of
the retained width/exclusion/score surfaces drive the decision.

The [synthesis bootstrap](../../../src/latent_landscapes/arc2a_synthesis.py),
around line 689, resamples validation histories with cutoffs fixed. Its
intervals therefore do not include calibration-table variability. This must
not be retroactively described as Arc 2C's calibration-aware bootstrap.

**Proposed handling:** retain the point-recovery and prediction conclusions;
describe projected widths as oracle-conditioned joint-support geometry.
Move S20 into calibration diagnostics. Preserve the actual prospective
response-surface validation, with its conditional uncertainty scope.

## Arc 2B: a consequential classification dependency

[Goal 044](../044-arc2b-prey-effect-recoverability-map/Goal.md), especially
lines 137 onward and 297–304, already calls coverage chiefly a calibration
check and excludes it from the recovery response surfaces. Each truth has
250 calibration and 250 evaluation histories, with rank 239. Yet the
[classification function](../../../src/latent_landscapes/arc2b_synthesis.py),
lines 361–375, still includes coverage as a full-recovery gate. Control
decisions also include coverage. At the null, coverage and false exclusion
are complementary, not two independent successes.

The [archived condition table](../../../artifacts/arc2b_synthesis/condition_outcomes.csv)
lists S08 as `detected_but_not_fully_recovered`, with `coverage` its only
failed gate. Its observed coverage is 0.98; this is not a point-recovery
failure. Removing only that gate would change the categories from 3 fully
recovered / 10 detected but not fully recovered / 19 not reliably detected
to **4 / 9 / 19**. This is a counterfactual consequence of the proposed rule
change, not a newly accepted classification or endorsement of all remaining
historical gates as measures of information.

The 19 weak-detection cases are defined by exclusion and predictive score,
so that count survives. The finding that tested effects below threefold were
not reliably detected, and the five prospectively tested response surfaces,
also survive with oracle-calibration qualifications on width/topology/power.
Primary prediction uses the matched known-background no-effect model;
fitted-neutral scoring is a separate secondary benchmark.

**Proposed handling:** review an explicit classification amendment rather
than silently revising 3/10/19. Preserve both historical and amended rules if
accepted. Treat local coverage/null false exclusion as calibration checks;
retain point error, prediction and qualified non-null power as recovery
evidence. No classification function or published count is edited now.

## Arc 2C: eight calibration checks among thirty contrasts

[Goal 045's design](../045-spread-prey-oracle-bridge/Goal.md), lines 50–78,
specifies separate rank-239-of-250 cutoffs for each truth and analysis lane,
with 250 evaluation histories and calibration-aware resampling. These are
parameter-specific effect/rho supports, not Arc 2A's projected joint sets.

The [synthesis](../045-spread-prey-oracle-bridge/synthesis.md) reports all
30 paired intervals containing zero. Six coverage contrasts and two
null-truth false-exclusion contrasts are calibration checks with tie-free
zero marginal benchmarks. The other **22** comprise six point-error, six
oracle-width, four non-null exclusion and six conditional-prediction
contrasts. Their recorded intervals also contain zero, so the bounded
no-detected-added-cost conclusion survives. It is not equivalence.

The 91.6% usual-speed fivefold coverage is a realised calibration/evaluation
outcome, not evidence that both lanes share an ecological recovery weakness.
The threefold and slow-fivefold limitations retain error/width/power evidence.
The [context classifier](../../../src/latent_landscapes/arc2c_synthesis.py),
around line 397, already omits coverage; it need not be changed to remove that
particular dependency. Width and non-null power remain conditional on the
truth-specific support construction.

**Proposed handling:** state the comparison using the 22 substantive contrasts
and retain eight separately labelled calibration checks. Replace the shared-
undercoverage interpretation with a calibration diagnostic. Keep the existing
calibration-aware uncertainty and all numerical evidence.

## Changes to consider after critique

Prepare one explicit interpretive amendment spanning the affected synthesis
paragraphs and, if accepted, Arc 2B's classification rule. Do not rerun process
simulations to repair a wording or estimand problem. Distinguish amendments
to the meaning of evidence from regenerated results. The audit found that
correct caveats were already present in some prose but did not constrain the
decision code; future review must trace each decision back to its estimand,
not just verify its numerical reproduction.
