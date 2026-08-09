# Goal 023: One-Axis Cross-Truth Three-Parameter Benchmark

## Scientific Question

Does the accepted joint `(rho, eta, p)` inference remain calibrated and
precise when one generating parameter at a time moves into a more difficult
regime, or is identifiability limited to the central truth?

## Frozen Truth Cells

Use the Goal 022 refined eta grid, the full 4,096-draw production integration
bank, 160 sites, survey times `10, 20, 30, 40, 50, 60`, two visits, and zero
false positives. Evaluate four on-grid truths with common process and detection
random numbers across cells:

- `central`: `(rho, eta, p) = (1, 1, 0.65)`;
- `slower_spread`: `(0.7578582832551991, 1, 0.65)`, equivalent to
  `log2(rho) = -0.4`;
- `weaker_resistance`: `(1, 0.5, 0.65)`; and
- `poorer_detection`: `(1, 1, 0.45)`.

The three stress cells each change only one parameter from the centre and move
in the direction expected to reduce information. Do not add upper-direction
or interaction cells in this goal.

## Calibration And Decision

For each truth independently, use 250 calibration histories, 250 validation
histories, and the 239th ordered calibration likelihood-ratio statistic. Use
the complete-history three-parameter composite likelihood and inherited Goal
021 gates, with the numerically tolerant threshold comparisons accepted in
Goal 022.

The central cell must reproduce the accepted Goal 022 full/refined condition:
cutoff `59.15805000796831`, coverage `234/250`, `250/250` connected interior
supports, and zero boundary contacts.

Return:

- `advance_to_joint_interaction_truths` if all four cells pass every inherited
  gate;
- `one_axis_identifiability_limit_found` if the central cell reconciles and at
  least one stress cell fails; or
- an implementation/reconciliation failure if invariants or the central
  anchor fail.

A failure completes the goal. Do not retune a truth, threshold, grid, bank, or
observation design after seeing the result.

## Compact Review Surface

Write exactly five ignored files:

- `truth_summary.csv`;
- `validation_results.csv`;
- `summary.json`;
- `review.md`; and
- `cross_truth_recovery.svg`, comparing connectivity, coverage, normalized
  median errors, and normalized median widths across the four truths.

## Validation And Stop Rule

- generalize the existing observation generator and Goal 021 support summary
  only as required for explicit truth parameters;
- one Goal 023 scientific module and one CLI;
- three focused tests for paired truth generation, arbitrary-truth support and
  decision logic, and the exact reduced-smoke review surface;
- one reduced non-scientific smoke, one timing probe, and one production run;
- use a remote host only if the timing probe shows a material advantage;
- Ruff, strict MyPy, one full test run, and package build;
- one inspection of the tables, memo, and rendered figure; and
- at most one material repair.

Do not add interaction truths, prediction scoring, neutral models, alternative
process models, prey dynamics, real data, or bank-size sweeps. Stop at human
review; commit and publication require later acceptance.

Barry approved proceeding with Goal 023 on 9 August 2026.

## Outcome

The production campaign completed locally in 27 minutes 20 seconds and
returned `one_axis_identifiability_limit_found`. The central cell exactly
reconciled Goal 022. All invariants passed, all support regions were connected,
and all four truths had acceptable coverage and small median point-estimation
errors.

The decisive differences were in uncertainty:

- `central` passed with `250/250` connected interior supports and median
  detection-probability width `0.20`;
- `poorer_detection` also passed with `250/250` connected interior supports
  and median detection-probability width `0.18`;
- `slower_spread` retained `250/250` connected interior supports but failed
  precision because its median detection-probability width was `0.26`, above
  the `0.20` limit; and
- `weaker_resistance` had connected supports in all histories, but `84/250`
  reached the `eta = 0` boundary and only `166/250` remained interior. The
  design therefore could not reliably distinguish weak resistance from no
  resistance effect; its median detection-probability width was also `0.24`.

This is a substantive one-axis identifiability limit, not an implementation
failure and not evidence of systematic point bias. Interaction truths should
not be added yet.

## Validation

- three focused Goal 023 tests passed, including exact central-truth and
  central-record reconciliation to the frozen Goal 011 generator;
- focused Goal 021-023 regressions and the reduced non-scientific CLI smoke
  passed;
- the timing probe supported one proportionate local production run;
- the production run wrote exactly the five ignored review files;
- the condition table, plain-language memo, validation distributions, and
  rendered SVG were inspected once;
- one material repair localized variable-detection observation generation to
  Goal 023, restoring the intentionally frozen Goal 004 source and its Goal
  005 provenance checks without changing the production arithmetic;
- Ruff formatting and lint passed repository-wide;
- strict MyPy passed over `135` source files;
- the package build passed; and
- the full suite passed (`242` tests), with only three inherited Goal 006
  Matplotlib pending-deprecation warnings.

Generated artifacts and build outputs remain ignored and unstaged. No
interaction truth, retuning, commit, or publication was started.
