# Goal 039: Arc 2A Predator Recoverability Pilot

## Programme role

This goal begins Charter Pillar 2 and Roadmap Arc 2A. It converts the accepted
Goal 038 design into the first multivariate predator-only production campaign.

## Scientific question

Across the approved ranges of spread rate, landscape-resistance contrast, and
per-visit detection, where does the current fixed experiment recover each
parameter accurately and with calibrated uncertainty, and where does it fail?

## Frozen design

- the accepted 72 by 84 landscape, 160 sites, 120/40 spatial split, six survey
  dates, two visits, and zero false positives;
- 16 scrambled Sobol truths from Goal 038 plus the separate `eta = 0`
  diagnostic;
- 250 calibration and 250 independent validation histories per truth;
- common process shocks and detection streams across truth conditions within
  each replicate index, with disjoint calibration and validation roots;
- the accepted three-parameter simulated composite likelihood and fitted
  time-stratified neutral comparator; and
- the Arc 1 candidate domains, augmented per condition so that each continuous
  generating coordinate is represented exactly rather than rounded.

## Required outcomes

1. Build the expensive stochastic integration bank once over the union of
   resistance values required by the 17 conditions.
2. Run locally calibrated three-parameter inference at every frozen truth,
   preserving common random numbers across conditions.
3. Record point bias and absolute error, support width and topology, empirical
   coverage, exclusion of `eta = 0`, and held-out prediction against the fitted
   neutral baseline.
4. Reconcile the shared generator against the accepted Arc 1 central generator
   without adding a central production cell.
5. Produce a compact truth-level table, paired replicate table, plain-language
   review, and one figure suitable for deciding whether Goal 040 should fit a
   response surface.
6. Run a reduced local smoke and timing gate before detached production on
   `deep-server`.

## Review bundle

Write exactly eight ignored files under `artifacts/goal039_arc2a_pilot/`:

- `truth_design.csv`;
- `calibration_statistics.csv`;
- `validation_metrics.csv`;
- `truth_summary.csv`;
- `summary.json`;
- `run_provenance.json`;
- `review.md`; and
- `truth_level_recovery.svg`.

Raw landscapes, histories, likelihood cubes, and integration-bank arrays are
replayable intermediates and must not be retained in the bundle.

## Authority and boundaries

Barry approved Goal 039 on 29 August 2026, including local development and a
detached `deep-server` production run after the smoke and timing gates pass.
A branch-only staging commit and push are authorized when required to place an
exact source revision on the remote host. Merging or publishing to canonical
`main` remains a later human decision.

Do not change the landscape, sampling design, survey schedule, truth table,
factor domains, observation model, inference likelihood, calibration rank, or
neutral comparator. Do not fit the Arc 2 response surface, add design points,
introduce prey dynamics, or start Goal 040.

## Success and stop rules

The goal succeeds when all 17 conditions complete with exact truth coordinates,
paired random streams, complete finite metrics, and an auditable eight-file
review pack. A negative or uneven recoverability map is a valid result. Stop
after one focused implementation review and one material repair. Do not extend
the Sobol design or increase replication until Barry has reviewed the raw
truth-level evidence.

## Observed production result

The accepted design completed on `deep-server` from source commit
`57df84a82f793e30984245c292fdca82f1bf177c` using 12 workers. The detached run
finished with exit status 0 in 24 minutes 37 seconds and wrote the exact
eight-file review bundle. All generator, pairing, truth-coordinate, row-count,
finite-metric, and Arc 1 reconciliation invariants passed.

The first-order scientific pattern is:

- 5 of 16 continuous truths met every inherited Arc 1 recovery gate;
- empirical calibrated coverage ranged from 0.932 to 0.964, straddling the
  nominal 0.95 target at every truth;
- median point errors were below their prespecified thresholds at every truth;
- all 16 process models had lower mean held-out Brier error than their fitted
  time-only neutral baselines;
- 6 truths were classified as support-design limited, with 5 of those 6 at
  resistance contrast below 0.75; and
- 5 truths were classified as imprecise solely because of interval width: four
  for detection probability and one for resistance contrast.

The separate `eta = 0` diagnostic behaved as a useful null: its support
excluded zero in only 1 of 250 validation histories and touched the parameter
boundary in 249 of 250. These are raw condition-level findings. No response
surface has yet been fitted and no additional design points are authorized.
