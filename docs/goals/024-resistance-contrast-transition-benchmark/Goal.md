# Goal 024: Resistance-Contrast Transition Benchmark

## Scientific Question

How strong must habitat resistance be before the current road-biased survey
design can reliably distinguish it from no resistance effect?

## Frozen Comparison

Treat the accepted Goal 023 production evidence as two fixed anchors:

- `eta = 0.5`: `166/250` connected interior supports, `84/250` boundary
  contacts, and `three_parameter_support_design_limited`; and
- `eta = 1.0`: `250/250` connected interior supports, zero boundary contacts,
  and `advance_to_cross_truth_three_parameter_benchmark`.

Evaluate one new on-grid midpoint truth only:

- `(rho, eta, p) = (1, 0.75, 0.65)`.

Keep the accepted refined eta grid, rho and detection grids, 4,096-draw
integration bank, landscape, 160-site design, survey calendar, two visits,
zero-false-positive observation model, seed streams, 250 calibration histories,
250 validation histories, and 239th ordered calibration cutoff unchanged.
Calibrate the midpoint truth independently. Do not recompute the accepted
anchors.

## Decision

The primary resistance-discrimination gate is at least `238/250` validation
supports that are both connected and interior. This asks whether the data rule
out the `eta = 0` no-resistance boundary reliably. Report the inherited Goal
021 three-parameter decision separately.

After evidence reconciliation and invariant checks, return:

- `resistance_transition_between_0_5_and_0_75` if the midpoint meets the
  primary gate;
- `resistance_transition_between_0_75_and_1_0` if it does not; or
- `resistance_transition_unresolved` if the accepted anchors, calibration, or
  implementation do not reconcile.

Either bracket completes the goal. Do not add another midpoint, alter the
sampling design, or retune a threshold after seeing the result.

## Compact Review Surface

Write exactly five ignored files:

- `transition_summary.csv`, containing the two accepted anchors and new
  midpoint;
- `midpoint_validation.csv`;
- `summary.json`;
- `review.md`; and
- `resistance_transition.svg`, comparing connected-interior frequency,
  boundary contact, coverage, and joint precision across the three eta values.

## Validation And Stop Rule

- one Goal 024 scientific module and one CLI;
- three focused tests for accepted-anchor reconciliation, decision logic, and
  the exact reduced-smoke review surface;
- one reduced non-scientific smoke, one timing probe, and one production run;
- one inspection of the table, memo, validation distribution, and rendered
  figure;
- Ruff, strict MyPy, one full test run, and package build; and
- at most one material repair.

Do not add interacting truths, survey-window changes, alternative observation
designs, prediction scoring, neutral models, prey dynamics, real data, or a
finer resistance search. Stop at human review; commit and publication require
later acceptance.

Barry approved proceeding with Goal 024 on 9 August 2026.

## Outcome

The production midpoint campaign completed locally in 26 minutes 22 seconds
and returned `resistance_transition_between_0_5_and_0_75`. The accepted Goal
023 anchors reconciled exactly.

At `eta = 0.75`:

- all `250/250` validation supports were connected and interior;
- zero supports reached the `eta = 0` no-resistance boundary;
- calibrated coverage was `234/250 = 0.936`, with a 95% Wilson interval of
  approximately `0.899-0.960`;
- median point errors remained small: `0.028` in log-rho, `0.125` in eta, and
  `0.020` in detection probability; and
- median support widths were `0.333` in log-rho, `0.625` in eta, and `0.24` in
  detection probability.

The midpoint therefore passed the resistance-specific discrimination gate
decisively, bracketing the practical transition between `eta = 0.5` and
`0.75`. Its inherited full three-parameter label remained
`three_parameter_recovery_imprecise` solely because detection-probability
width was `0.24`, above the `0.20` limit. This is a joint-precision issue, not
failure to distinguish habitat resistance from zero.

No finer threshold search is warranted at this stage.

## Validation

- three focused tests passed for anchor reconciliation, the resistance-specific
  decision, and the exact reduced-smoke review surface;
- focused Goal 023-024 regressions and the reduced CLI smoke passed;
- the timing probe supported one local production run;
- the production run wrote exactly five ignored review files;
- the transition table, all 250 midpoint validation rows, plain-language memo,
  and rendered SVG were inspected once;
- Ruff formatting and lint passed repository-wide;
- strict MyPy passed over `138` source files;
- the package build passed; and
- the full suite passed (`245` tests), with only three inherited Goal 006
  Matplotlib pending-deprecation warnings.

Generated artifacts and build outputs remain ignored and unstaged. No finer
midpoint, observation-design change, interaction truth, commit, or publication
was started.
