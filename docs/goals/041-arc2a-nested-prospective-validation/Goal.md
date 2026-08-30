# Goal 041: Arc 2A Nested Prospective Validation

## Programme role

This goal completes the prospective validation step for Charter Pillar 2 and
Roadmap Arc 2A. It tests whether Goal 040's first-block relationships predict
new parameter combinations before any surface is refitted.

## Scientific question

Do the low-order relationships learned from the first 16 predator-only truths
predict inferential performance at the next 16 nested Sobol truths, and is the
isolated broad resistance interval from Goal 039 reproducible?

## Frozen experiment

- the accepted 72 by 84 landscape, access network, 160 sites, 120/40 spatial
  split, six survey dates, two visits, and zero false positives;
- the accepted spread-rate, resistance-contrast, and detection-probability
  domains;
- the next 16 points, `S17` to `S32`, from the same scrambled Sobol sequence,
  with no targeted or post hoc points;
- 250 calibration and 250 independent validation histories per truth;
- the Goal 039 common-random-number roots, candidate-grid policy, likelihood,
  calibration rank, evaluation metrics, thresholds, and neutral comparator;
  and
- Goal 040's selected low-order model forms, coefficients, first-block means,
  and leave-one-truth-out errors.

The separate `eta = 0` diagnostic and Arc 1 anchors are not rerun.

## Prospective prediction contract

Before running any new process simulation, write and commit the predicted value
for all five Goal 040 outcomes at every new truth. The frozen table must record
the source Goal 040 commit and use its accepted coefficient and scaling rules.
The resulting 80-row table is `prospective_predictions.csv`, with SHA-256
`1f57091555acde69aedaa5712bdf4668c513fe3f02fad1aff9634d355fab91b9`.

For each metric, calculate prospective skill against the frozen first-block
mean:

```text
1 - sum((observed - surface prediction)^2)
    / sum((observed - first-block mean)^2)
```

A positive value means that the surface predicts the new block better than the
mean-only comparator. Report the magnitude without converting it into a new
binary recovery gate. Also report the original leave-one-truth-out error, the
new-block error, threshold classification, and whether observations fall
inside the frozen Goal 040 error envelope.

Resistance-interval width remains a deliberately separate question. A new
condition strictly above the accepted width limit of `0.75` reproduces the
broad-interval phenomenon; values equal to the limit do not.

## Decision rule

- Recommend `freeze_arc2a_validated` when all four previously learnable
  surfaces have positive prospective skill and no new resistance interval is
  broader than `0.75`.
- Recommend `freeze_arc2a_with_surface_limits` when no broad resistance
  interval is reproduced but one or more fitted surfaces fail to beat their
  frozen mean comparator. Preserve the reliable qualitative conclusions and
  state the failed interpolation explicitly.
- Recommend `review_bounded_eta_precision_followup` when at least one new
  resistance interval is broader than `0.75`. Any later enrichment proposal
  is limited to at most eight named points and requires Barry's review.

These classes govern the next discussion; they do not authorize further
simulation.

## Review bundle

Write exactly eleven ignored files under `artifacts/goal041_arc2a_nested_validation/`:

- `new_truth_design.csv`;
- `frozen_predictions.csv`;
- `calibration_statistics.csv`;
- `validation_metrics.csv`;
- `truth_summary.csv`;
- `prospective_scores.csv`;
- `metric_validation_summary.csv`;
- `summary.json`;
- `run_provenance.json`;
- `review.md`; and
- `prospective_validation.svg`.

Raw landscapes, histories, likelihood cubes, and integration-bank arrays are
replayable intermediates and must not be retained.

## Success and stop rules

The goal succeeds when the frozen predictions are committed before production,
all 16 new truths complete with paired finite metrics, prospective scores are
reconciled, and the recommendation follows the rule above. A failed surface is
a valid result. Stop after one focused implementation review and one material
repair. Do not refit the surfaces, add points, or search for a more flexible
emulator in this goal.

## Authority and boundaries

Barry approved Goal 041 on 30 August 2026. Local development, ignored artifact
generation, an exact branch commit and push, and one detached production run on
`deep-server` after reduced smoke checks are authorized. Canonical `main`
publication remains a later human decision.

Do not change the landscape, observation design, factor domains, likelihood,
neutral comparator, thresholds, replication counts, or common-random-number
roots. Do not add prey dynamics, targeted design points, alternative models,
new landscapes, or Goal 042 work.
