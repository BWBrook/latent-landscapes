# Goal 021: Central Three-Parameter Positive Control

## Scientific Question

When spread rate, landscape resistance, and detection probability are all
unknown, can the accepted observations recover all three simultaneously at the
central generating truth?

This is the first full `(rho, eta, p)` benchmark. Goals 019 and 020 established
the two complementary pairwise positive controls; they do not guarantee that
the three-way problem remains precise or calibrated.

## Frozen Design

Reuse the accepted landscape, 160 sites, survey times
`10, 20, 30, 40, 50, 60`, stochastic truth `(rho, eta, p) = (1, 1, 0.65)`,
two visits, zero false positives, and 4,096-draw process bank.

Use the accepted pairwise grids unchanged:

- 101 log-even rho values from `0.25` to `4`;
- eta `0, 0.25, ..., 2.5`; and
- p `0.05, 0.07, ..., 0.95`.

Use 250 calibration histories, 250 independent validation histories, and the
239th ordered calibration likelihood-ratio statistic as the empirical 95%
cutoff.

## Analysis And Decision

Calculate the complete-history composite likelihood over `(rho, eta, p)`.
Calibration histories determine one three-dimensional support cutoff.
Validation histories report:

- truth inclusion and Wilson coverage;
- six-neighbour support connectedness and boundary contact;
- minimum MLE-set error and projected support width for every parameter; and
- descriptive support correlations for rho-eta, rho-p, and eta-p where both
  axes vary.

Return `advance_to_cross_truth_three_parameter_benchmark` when:

- the validation Wilson interval contains nominal coverage `0.95`;
- at least 238 of 250 supports are connected and interior;
- median absolute log-rho error is at most `0.10`;
- median absolute eta error is at most `0.25`;
- median absolute p error is at most `0.05`;
- median projected log-rho width is at most `0.50`;
- median projected eta width is at most `0.75`; and
- median projected p width is at most `0.20`.

Otherwise return the first applicable diagnosis: support-design-limited,
calibration-not-ready, or recovery-imprecise. Do not relax the inherited
pairwise thresholds or run a rescue campaign.

## Compact Review Surface

Write exactly four ignored files:

- `replicate_results.csv`;
- `summary.json`;
- `review.md`; and
- `three_parameter_recovery.svg` with three validation estimate distributions
  and three representative likelihood slices through the generating values.

## Validation And Stop Rule

- one scientific module and one CLI;
- three focused tests for likelihood arithmetic, three-dimensional support and
  decisions, and the exact review surface;
- one reduced non-scientific smoke, one timing probe, then one production
  campaign;
- use `deep-server` under `tmux` only if the timing probe makes local execution
  materially inefficient;
- Ruff, strict MyPy, one full test run, and package build;
- one inspection of the table, memo, and rendered figure; and
- at most one material repair.

Do not add cross-truth cells, prediction scoring, a neutral comparator,
observation heterogeneity, false positives, prey dynamics, real data, or
alternative models. A negative result completes the goal. Stop at human
review. Commit and publication require later acceptance.

Barry approved proceeding with Goal 021 on 9 August 2026.

## Outcome

The production campaign completed in 13 minutes 45 seconds and returned
`three_parameter_support_design_limited`. This was a narrow failure of the
prespecified support-topology gate, not a general failure to recover the three
parameters:

- validation coverage was `234/250 = 0.936`; its 95% Wilson interval
  (`0.899-0.960`) contained `0.95`;
- all 250 supports were interior, but only `229/250` were connected, below the
  required `238/250`;
- each of the remaining 21 supports had exactly two components;
- median absolute errors were `0.055` in log-rho, `0.000` in eta, and `0.020`
  in detection probability; and
- median projected widths were `0.305`, `0.500`, and `0.200`, respectively.

Thus every calibration, point-recovery, and width gate passed. The result
stopped because a non-negligible minority of histories admitted two separated
regions of parameter space. The representative rho-eta slice showed two
likelihood basins along a strong inverse ridge, and median rho-eta support
correlation was `-0.858`. This is evidence of a spread-rate/resistance
trade-off, but this goal does not distinguish genuine data-supported
multimodality from discrete-grid or integration-bank roughness.

## Validation

- three focused tests passed for hand-checked likelihood arithmetic,
  six-neighbour 3D support decisions, and the exact four-file review surface;
- the reduced CLI smoke passed and labelled itself non-scientific;
- the timing probe showed that integration-bank construction dominated
  runtime, making one local production run proportionate;
- the production campaign wrote exactly four ignored review files;
- the CSV, memo, and rendered SVG were inspected once, with no material repair
  required;
- Ruff formatting and lint passed repository-wide;
- strict MyPy passed over `111` source files;
- the package build passed; and
- the full suite passed (`236` tests), with only three inherited Goal 006
  Matplotlib pending-deprecation warnings.

No rescue run, threshold change, cross-truth cell, commit, or publication was
started. The result is ready for human review.
