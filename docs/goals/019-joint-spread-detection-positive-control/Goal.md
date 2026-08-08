# Goal 019: Joint Spread-Detection Positive Control

## Scientific Question

With landscape resistance fixed at its generating value, can the accepted
two-visit design distinguish a genuinely slower predator wave from a normally
paced wave that was detected less often?

This is the first benchmark in which spread rate `rho` and detection
probability `p` are both unknown. Resistance contrast remains fixed at
`eta = 1` so that a failure has a narrow interpretation.

## Frozen Design

Reuse Goal 018's central landscape, 160 sites, survey times
`10, 20, 30, 40, 50, 60`, stochastic truth `(rho, eta) = (1, 1)`, two visits,
generating `p = 0.65`, zero false positives, and 4,096-draw process bank.

Use one moderate, decision-adequate candidate grid:

- `101` log-even rho values from `0.25` to `4`, including `rho = 1`; and
- `p = 0.05, 0.07, ..., 0.95`, including `p = 0.65`.

Use 250 calibration histories, 250 independent validation histories, and the
239th ordered calibration likelihood-ratio statistic as the empirical 95%
cutoff. The reduced counts and grid are intentional Pareto choices: their
resolution is well inside the recovery thresholds below, while the Wilson
interval explicitly represents Monte Carlo uncertainty.

## Analysis And Decision

For each complete site history, calculate the composite likelihood surface
over `(rho, p)` using the accepted process-category bank weights at known
`eta = 1`. Preserve all tied grid maxima.

Calibration histories determine the joint support cutoff. Validation histories
report:

- truth inclusion and calibrated coverage;
- support connectedness and candidate-boundary contact;
- minimum MLE-set error in `log(rho)` and in `p`;
- projected support width in `log(rho)` and in `p`; and
- the correlation between `log(rho)` and `p` within the support as a
  descriptive speed-detection ridge diagnostic.

Return `advance_to_resistance_detection_pair` when:

- the validation Wilson interval contains nominal coverage `0.95`;
- at least 238 of 250 supports are connected and interior;
- median absolute log-rho error is at most `0.10`;
- median absolute p error is at most `0.05`;
- median projected log-rho width is at most `0.50`; and
- median projected p width is at most `0.20`.

Otherwise return the first applicable diagnosis: support-design-limited,
calibration-not-ready, or recovery-imprecise. A negative result completes the
goal; do not retune after inspection.

## Compact Review Surface

Write exactly four ignored files:

- `replicate_results.csv` with calibration and validation rows;
- `summary.json`;
- `review.md`; and
- `spread_detection_recovery.svg`, combining validation recovery summaries
  with one prespecified representative joint surface.

## Validation And Stop Rule

- one scientific module and one CLI;
- three or four focused tests for likelihood arithmetic, joint support and
  decisions, and the exact review surface;
- one reduced non-scientific smoke, then one production campaign;
- Ruff, strict MyPy, one full test run, and package build;
- one inspection of the table, memo, and rendered figure; and
- at most one repair for a material scientific or interpretability defect.

Do not estimate eta, change the observation design, add heterogeneity or false
positives, score predictions, add a neutral comparator, run multiple truth
cells, simulate prey, access real data, or begin the three-parameter model.
Stop at human review. Commit and publication require later acceptance.

Barry approved proceeding with Goal 019 on 8 August 2026.

## Outcome

The prespecified campaign returned `advance_to_resistance_detection_pair`.

- joint validation coverage was `238/250 = 0.952`, with a 95% Wilson interval
  of `0.918-0.972` containing the nominal `0.95` target;
- all `250/250` validation supports were connected and interior;
- median absolute log-rho error was `0.0277`;
- median absolute p error was `0.020`;
- median projected log-rho width was `0.166`;
- median projected p width was `0.200`; and
- median support correlation between log-rho and p was `-0.134`.

Mean biases were small (`-0.0065` in log-rho and `+0.0038` in p), and every
design, seed, grid, integration-weight, record-count, and zero-false-positive
invariant passed. Thus spread speed and homogeneous detection probability are
separable at this central truth when resistance is known.

The result is a qualified rather than emphatic pass for detection precision.
The median projected p width sits exactly at the prespecified `0.20` boundary;
the validation range was `0.18-0.22`. Point estimates were nevertheless close
to truth, with p errors from `0` to `0.04`, and there was no strong joint ridge.
This uncertainty must remain visible in later rungs.

## Validation And Residuals

- the expected test-first import failure was observed before implementation;
- three focused Goal 019 tests passed, covering hand-checked likelihood
  arithmetic, two-dimensional support and decision gates, and the exact
  four-file review surface;
- the three Goal 018 regression tests also passed after exposing its shared
  complete-history reduction;
- the reduced CLI smoke wrote four files and labelled itself non-scientific;
- one scientific production campaign wrote the required ignored review pack;
- the table, memo, and rendered SVG were inspected once;
- the allowed visual repair zoomed the figure to the decision-relevant region,
  and deterministic regeneration left all numerical files byte-identical;
- Ruff formatting and lint passed;
- strict MyPy passed over `107` source files;
- the package build passed; and
- the full suite passed (`230` tests; three inherited Goal 006 Matplotlib
  deprecation warnings).

Resistance contrast was fixed at `eta = 1`, detection was homogeneous, and
false positives were absent. The next conservative rung is therefore the
complementary `(eta, p)` pair with rho fixed, not the full three-parameter
model. No commit or publication is authorised by this goal.
