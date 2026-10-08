# Goal 049 cross-arc interpretation amendments

20 September 2026. **Reviewed retrospective interpretation; no regenerated
simulation evidence and no historical output rewrite.** Fable thread 44
approved the amendments below. This record separates calibration quality
control from evidence about biological recoverability while preserving all
original observations, tables, classifications, and closeout decisions.

## Scientific decision

Same-truth coverage, and false exclusion when the tested null is the generating
truth, assess whether a truth-specific calibrated procedure behaves as intended
in a finite repeated-sampling experiment. They do not independently show that
the ecological parameter is learnable. Recoverability is assessed by point
accuracy, support resolution and topology, non-null detection power, and
held-out prediction, under the limits of each calibration design.

This is an interpretation amendment. The Arc 2B historical classifier remains
frozen because changing it would silently rewrite an accepted result. A
versioned retrospective rule omits coverage from the full-recovery gates and
is shown side by side with the historical rule.

## Evidence base and scope

The amendments use only saved summaries from the synthetic Paper 1 programme.
The observation process, sampling design, and experimental unit are unchanged:
each campaign simulates complete histories on the fixed reference landscape,
fits the declared process/observation model to 120 training sites, evaluates
prediction on 40 spatially held-out sites where applicable, and treats a whole
simulated history as the replicate. Calibration and evaluation histories are
separate. The inference remains conditional on the tested landscape, access
network, survey calendar, model family, known nuisance parameters, effect grid,
and truth-specific oracle calibration used by the historical arc.

## Gate-to-estimand trace

| Quantity or gate | Estimand or decision target | Interpretation after amendment |
| --- | --- | --- |
| Point error | Accuracy of the estimator at a stated generating truth | Biological-recovery evidence, conditional on the model and design. |
| Support width | Resolution of the locally calibrated support | Recovery evidence conditional on the oracle cutoff; not a transport claim. |
| Connected/interior support | Topology and boundary adequacy of the support on the tested grid | Recovery and numerical-domain evidence, conditional on the oracle cutoff. |
| Non-null exclusion of no effect | Probability of detecting the prespecified null as false at that non-null truth | Conditional power evidence. Under truth-specific oracle cutoffs it is not automatically the power curve of one fixed analyst-usable test. |
| Same-truth coverage | Repeated-sampling inclusion probability of the generating truth for the local calibrated procedure | Calibration quality control. A realised miss is not an ecological condition effect by itself. |
| Null-truth false exclusion | Type-I behavior at the generating null; the complement of truth inclusion there | Calibration quality control, not a second independent recovery gate. |
| Held-out predictive advantage | Expected predictive-score difference for the stated held-out observations and comparator | Predictive evidence; it does not alone identify the ecological parameter. |
| Validation count | Completeness of the intended Monte Carlo block | Execution/data-integrity gate rather than an ecological estimand. |

## Arc-specific amendments

### Arc 1

The accepted evidence ladder is retained. Same-truth coverage is labelled as
calibration quality control, while error, width, topology, non-null exclusion,
and prediction retain their stated evidential roles. This does not erase
independent failures: the threefold prey-effect case also failed width, the
low-background fivefold case retained topology/width failures, and Goal 005
directly showed that a central-speed cutoff did not transport to flank truths.

### Arc 2A

Arc 2A uses truth-specific rank-239-of-250 **joint** three-parameter regions and
reports projected widths separately. `S20`'s 91.6% joint truth inclusion is a
realised finite calibration check, not evidence that its ecological condition
causes deficient coverage. Point recovery, prediction, prospective validation,
and the retained width/exclusion/topology surfaces are unchanged. The synthesis
bootstrap resampled evaluation histories with the fitted calibration tables
held fixed, so its intervals omit calibration-table variation; their historical
conditional scope is retained.

### Arc 2B

The frozen condition table reproduces the historical `3 / 10 / 19` counts.
`S08` has coverage 0.98 and passes every other full-recovery gate; coverage is
its sole recorded failure. Omitting only coverage from the retrospective
full-recovery rule changes `S08` to `fully_recovered`, giving amended counts
`4 / 9 / 19`. No other truth changes, and all 19 weak-detection classifications
survive because they depend on non-null exclusion and prediction.

The reproducible side-by-side table is
`artifacts/goal049_claims/arc2b_classification_side_by_side.csv`, derived from
`artifacts/arc2b_synthesis/condition_outcomes.csv` by
`scripts/derive_goal049_claims.py`. The source classifier and historical CSV
remain unchanged. The source table used here has SHA-256
`721301d778ed59f30576f82283eb08d37ab17729b268fb3d8bf62fe98d5c4554`.

### Arc 2C

All 30 recorded paired intervals still contain zero. Six coverage contrasts
and the two null-truth false-exclusion contrasts are calibration checks. The
remaining 22 substantive contrasts are six point-error, six oracle-width, four
non-null-exclusion, and six conditional-prediction comparisons. Thus the
bounded conclusion of no detected added cost from estimating spread speed is
retained on 22 substantive contrasts; it remains a failure to detect a cost,
not evidence of equivalence.

The 91.6% usual-speed fivefold truth inclusion in both lanes is a realised
finite calibration result. It is not an ecological weakness and is not assigned
a stronger theoretical reference distribution here. The threefold and slow
fivefold limitations retain their independent error, width, and power evidence.

## Code disposition

The historical classifier is intentionally frozen. If a future goal adopts the
amended semantics in active code, `_classification` in
`src/latent_landscapes/arc2b_synthesis.py` would still calculate and report the
coverage check but would exclude it from the `fully_recovered` conjunction.
Detection would continue to require non-null exclusion and predictive
advantage. Control logic would report calibration status separately from
recovery status and would avoid counting null coverage and null false exclusion
as independent gates. Such a code change would regenerate decisions and is not
part of this retrospective amendment.

## Verification and remaining limits

The saved Arc 2B table was reclassified mechanically under both rules. The
historical fields reproduced exactly; the only changed truth was `S08`; counts
were historical `3 / 10 / 19` and amended `4 / 9 / 19`. The saved Arc 2C paired
table contains exactly 30 rows partitioning into 22 substantive and eight
calibration checks as stated above. No bootstrap, model fit, process simulation,
cutoff, or response surface was rerun.

These amendments do not produce an analyst-usable transferable interval, prove
off-grid coverage, resolve unknown nuisance parameters, or establish ecological
generality. They narrow the meaning of existing evidence before Goal 049 tests
operational calibration explicitly.
