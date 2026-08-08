# Goal 018: Detection-Probability Positive Control

## Question

With spread rate `rho = 1` and resistance contrast `eta = 1` fixed at their
generating values, do the accepted two replicate visits contain enough
information to estimate detection probability `p`?

This isolates the observation layer before any attempt to estimate spread,
resistance, and detection jointly.

## Frozen Design

Reuse the Goal 011 central stochastic process and observation streams:

- accepted landscape, sources, 160 sites, and survey times
  `10, 20, 30, 40, 50, 60`;
- stochastic truth `(rho, eta) = (1, 1)`;
- two visits per site-time, generating `p = 0.65`, and no false positives;
- 4,096 process-bank draws, 500 calibration histories, and 500 independent
  validation histories; and
- the 476th ordered calibration statistic as the empirical 95% cutoff.

Fit only `p` over `0.05, 0.06, ..., 0.95`. Use the full integration bank at
the known process truth. Goal 011 already established stability of this bank
and its halves at the same truth, so do not repeat half-bank analyses here.

## Analysis And Decision

For every history, calculate the complete site-history profile over `p`.
Calibration histories determine the likelihood-ratio cutoff; validation
histories report the MLE, absolute error, support interval, width, truth
coverage, connectedness, and candidate-boundary contact.

Return `advance_to_joint_unknown_detection` when:

- the validation Wilson interval contains nominal coverage `0.95`;
- at least 475 of 500 validation supports are connected and interior;
- median absolute error is at most `0.05`; and
- median support width is at most `0.20`.

Otherwise return the first applicable diagnosis: design-limited,
calibration-not-ready, or imprecise. A negative result completes the goal.
These thresholds are bounded progression rules, not general ecological
standards.

## Compact Review Surface

Write exactly four ignored files:

- `replicate_results.csv` containing calibration and validation rows;
- `summary.json`;
- `review.md`; and
- `detection_recovery.svg`, combining the validation MLE distribution with
  one prespecified representative profile.

## Validation And Stop Rule

- one scientific module and one CLI;
- three or four tests protecting likelihood arithmetic, decision gates, and
  the end-to-end review surface;
- one reduced non-scientific smoke, then one production campaign;
- Ruff, strict MyPy, one full test run, and package build;
- one human inspection of the table, memo, and figure; and
- at most one repair for a material scientific or interpretability defect.

Do not add prediction scoring, a neutral comparator, train/holdout splitting,
half-bank repetition, detection heterogeneity, false positives, joint
`(rho, eta, p)` fitting, real data, or prey dynamics. Stop at human review.
Commit and publication require later acceptance.

Barry approved Goal 018 on 8 August 2026.

## Outcome

The prespecified campaign returned `advance_to_joint_unknown_detection`.

- validation coverage was `474/500 = 0.948`, with a 95% Wilson interval of
  `0.925-0.964` containing the nominal `0.95` target;
- all `500/500` validation supports were connected and interior;
- median absolute error in `p` was `0.010`;
- median support width was `0.060`;
- mean MLE bias was `-0.00056`; and
- the empirical likelihood-ratio cutoff was `4.8133`.

All recorded design, replay, integration-weight, record-count, and
zero-false-positive invariants passed. Thus the accepted replicate-visit design
contains ample information about homogeneous detection probability when the
spread process is fixed at its generating parameters. This is the intended
observation-layer positive control; it does not establish that `p` remains
identifiable when `rho` and `eta` are also unknown.

## Validation And Residuals

- the three focused tests passed, covering likelihood arithmetic, decision
  gates, and the exact four-file review surface;
- the reduced CLI smoke wrote four files and labelled itself non-scientific;
- one production campaign wrote the prespecified ignored review pack;
- the table, memo, and rendered SVG were inspected once;
- the allowed repair only zoomed and labelled the representative likelihood
  profile, leaving all regenerated numerical files byte-identical;
- Ruff formatting and lint passed;
- strict MyPy passed over `105` source files;
- the package build passed; and
- the full suite passed (`227` tests; three inherited Goal 006 Matplotlib
  deprecation warnings).

The remaining scientific limitation is deliberate: detection is homogeneous,
false positives are absent, and both process parameters are known. The next
incremental question is therefore joint recovery with unknown `p`, not a more
elaborate observation model. No commit or publication is authorised by this
goal.
