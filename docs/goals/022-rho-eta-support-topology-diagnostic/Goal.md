# Goal 022: Spread-Rate / Resistance Support-Topology Diagnostic

## Scientific Question

Goal 021 recovered spread rate, resistance contrast, and detection probability
accurately on average, but 21 of 250 validation histories admitted two separate
parameter regions. Are those split regions caused by the coarse resistance
grid or finite integration-bank noise, or do they persist as a genuine
spread-rate/resistance ambiguity?

## Frozen Design

Keep the complete Goal 021 landscape, sampling design, truth, observation
model, seeds, rho grid, detection grid, 250 calibration histories, 250
validation histories, and 239th ordered calibration cutoff rule unchanged.

Compare:

- the accepted coarse eta grid `0, 0.25, ..., 2.5`; and
- a refined eta grid `0, 0.125, ..., 2.5`.

Use common edge shocks so the coarse eta slices are embedded exactly in the
refined integration bank. Evaluate both grids with:

- the full 4,096-draw bank;
- its first disjoint 2,048 draws; and
- its second disjoint 2,048 draws.

Calibrate each of these six conditions independently. Do not apply the Goal
021 cutoff to a likelihood surface with a different grid or bank.

## Reconciliation And Evidence

The full-bank coarse condition must reproduce Goal 021, including cutoff
`57.041556096360864`, coverage `234/250`, connected interior supports
`229/250`, and zero boundary contacts.

For each condition report coverage, connected interior count, boundary
contact, median parameter errors, median projected widths, and the inherited
Goal 021 decision class. For every validation history report coarse/refined
component counts under all three bank variants. Retain one full-bank history
that was split on the coarse grid for paired coarse/refined likelihood slices.

## Decision

After reconciliation and invariant checks:

- return `coarse_eta_resolution_explains_split_supports` if the full and both
  half-bank refined conditions all pass the inherited Goal 021 progression
  gates;
- return `rho_eta_ambiguity_persists_after_refinement` if all three refined
  conditions remain support-design-limited; and
- otherwise return `integration_bank_sensitivity_unresolved`.

Do not relax any Goal 021 recovery or topology threshold. These classes answer
only whether the numerical diagnosis is stable; they do not retroactively
change the Goal 021 result.

## Compact Review Surface

Write exactly five ignored files:

- `condition_summary.csv`;
- `validation_topology.csv`;
- `summary.json`;
- `review.md`; and
- `rho_eta_topology.svg`, showing condition-level connectivity, full-bank
  topology transitions, and paired coarse/refined slices for one split
  history.

## Validation And Stop Rule

- one diagnostic module and one CLI;
- three focused tests for embedded coarse slices, decision logic, and the
  exact reduced-smoke review surface;
- one reduced non-scientific smoke, one timing probe, and one production run;
- use a remote host only if the timing probe shows a material local advantage;
- Ruff, strict MyPy, one full test run, and package build;
- one inspection of the table, memo, and rendered figure; and
- at most one material repair.

Do not change the observation design, likelihood, truth, parameter ranges,
support thresholds, or Goal 021 result. Do not add cross-truth cells,
prediction scoring, neutral models, prey dynamics, real data, or alternative
models. A persistent or mixed result completes this goal. Stop at human review;
commit and publication require later acceptance.

Barry approved proceeding with Goal 022 on 9 August 2026.

## Outcome

The production diagnostic completed in 26 minutes 52 seconds and returned
`integration_bank_sensitivity_unresolved`. The full/coarse condition exactly
reproduced Goal 021, including its cutoff, coverage, `229/250` connected
supports, and zero boundary contacts.

Halving the eta step resolved every split support under every bank variant:

- full bank: `229 -> 250` connected supports; all `21/21` splits merged;
- first half-bank: `231 -> 250`; all `19/19` splits merged; and
- second half-bank: `234 -> 250`; all `16/16` splits merged.

After repairing a floating-point boundary comparison, the full/refined and
second-half/refined conditions passed every inherited Goal 021 gate. The
first-half/refined condition remained `three_parameter_recovery_imprecise`
only because its median detection-support width was `0.22`, one probability
grid step above the `0.20` threshold. Its connectivity, coverage, and median
parameter errors matched the other refined conditions.

The formal mixed label therefore reflects marginal integration-bank
sensitivity in detection precision, not disagreement about rho-eta topology.
The direct topology evidence supports the inference that the Goal 021 split
regions were caused by coarse eta resolution. The full 4,096-draw production
bank with the refined eta grid passes the central three-parameter positive
control, but the detection-width threshold remains borderline and should be
carried explicitly into any cross-truth decision.

## Validation

- three focused tests passed for exact coarse-profile embedding, decision
  classes, and the reduced five-file review surface;
- the reduced CLI smoke passed and labelled itself non-scientific;
- the timing probe supported one proportionate local production run;
- the production run wrote exactly five ignored review files;
- one material repair added numerical tolerance to inherited floating-point
  threshold comparisons; focused Goal 021-022 tests passed afterward;
- the numeric campaign was not repeated because the repair changed labels
  only; the corrected CSV, JSON, and memo agree, and a fresh run would use the
  repaired classifier;
- the condition table, topology transitions, memo, and rendered SVG were
  inspected once; and
- Ruff formatting and lint passed repository-wide;
- strict MyPy passed over `113` source files;
- the package build passed; and
- the full suite passed (`239` tests), with only three inherited Goal 006
  Matplotlib pending-deprecation warnings.

No observation, likelihood, truth, support threshold, parameter range,
cross-truth cell, commit, or publication was changed or started. The result is
ready for human review.
