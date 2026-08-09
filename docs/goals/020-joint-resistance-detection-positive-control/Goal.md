# Goal 020: Joint Resistance-Detection Positive Control

## Scientific Question

With spread rate fixed at its generating value, can the accepted two-visit
design distinguish landscape resistance contrast from imperfect detection?

This is the complementary pairwise benchmark to Goal 019. It estimates
resistance contrast `eta` and detection probability `p` while fixing
`rho = 1`, so that a failure can be attributed narrowly before any
three-parameter fit is attempted.

## Frozen Design

Reuse the accepted central landscape, 160 sites, survey times
`10, 20, 30, 40, 50, 60`, stochastic truth `(rho, eta) = (1, 1)`, two visits,
generating `p = 0.65`, zero false positives, and 4,096-draw process bank.

Use:

- the accepted eta grid `0, 0.25, ..., 2.5`; and
- `p = 0.05, 0.07, ..., 0.95`.

Use 250 calibration histories, 250 independent validation histories, and the
239th ordered calibration likelihood-ratio statistic as the empirical 95%
cutoff.

## Analysis And Decision

For each complete site history, calculate the composite likelihood surface
over `(eta, p)` using bank weights at known `rho = 1`. Preserve all tied grid
maxima.

Validation histories report joint coverage, connectedness, boundary contact,
minimum MLE-set errors, projected widths, and the correlation between eta and
p within the calibrated support as a descriptive resistance-detection ridge
diagnostic.

Return `advance_to_three_parameter_benchmark` when:

- the validation Wilson interval contains nominal coverage `0.95`;
- at least 238 of 250 supports are connected and interior;
- median absolute eta error is at most `0.25`;
- median absolute p error is at most `0.05`;
- median projected eta width is at most `0.75`; and
- median projected p width is at most `0.20`.

Otherwise return the first applicable diagnosis: support-design-limited,
calibration-not-ready, or recovery-imprecise. Goal 019's p-width result was
exactly on its `0.20` boundary, so Goal 020 must report rather than conceal any
similar borderline result. Do not retune after inspection.

## Compact Review Surface

Write exactly four ignored files:

- `replicate_results.csv`;
- `summary.json`;
- `review.md`; and
- `resistance_detection_recovery.svg`, combining validation recovery with one
  prespecified representative joint surface.

## Validation And Stop Rule

- one scientific module and one CLI;
- three focused tests for likelihood arithmetic, support and decision gates,
  and the exact review surface;
- one reduced non-scientific smoke, then one production campaign;
- Ruff, strict MyPy, one full test run, and package build;
- one inspection of the table, memo, and rendered figure; and
- at most one material repair.

Do not estimate rho, change the observation design, add heterogeneity or false
positives, score predictions, add a neutral comparator, run multiple truth
cells, simulate prey, access real data, or begin the three-parameter fit. Stop
at human review. Commit and publication require later acceptance.

Barry approved proceeding with Goal 020 on 8 August 2026.

## Outcome

The prespecified campaign returned `advance_to_three_parameter_benchmark`.

- joint validation coverage was `233/250 = 0.932`, with a 95% Wilson interval
  of `0.894-0.957` containing the nominal `0.95` target;
- all `250/250` validation supports were connected and interior;
- median absolute eta error was `0`;
- median absolute p error was `0.020`;
- median projected eta width was `0`;
- median projected p width was `0.180`; and
- the median eta-p support correlation was `-0.140` among the `118/250`
  supports for which both axes varied.

Eta was estimated at its exact generating grid value in `202/250` validation
histories. Every other eta estimate was one grid step away at `0.75` or
`1.25`; eta support widths ranged only from `0` to `0.25`. Detection-support
widths ranged from `0.16` to `0.20`, improving modestly on Goal 019. Mean biases
were small (`-0.002` in eta and `+0.002` in p).

Thus resistance contrast and homogeneous detection probability are separable
at this central truth when spread rate is known. The result remains qualified:
observed coverage was below nominal, and its Wilson interval only narrowly
included `0.95`. This passes the prespecified calibration gate but should not
be described as strong cross-truth calibration evidence.

## Validation And Residuals

- the expected test-first import failure was observed before implementation;
- three focused Goal 020 tests passed, covering hand-checked likelihood
  arithmetic, two-dimensional support and decision gates, and the exact
  four-file review surface;
- the six Goal 018-019 regression tests passed after extracting the shared
  parameter-by-detection likelihood calculation;
- the reduced CLI smoke wrote four files and labelled itself non-scientific;
- one production campaign completed locally in about 13 minutes and wrote the
  required ignored review pack;
- the table, memo, and rendered SVG were inspected once, with no material
  repair required;
- Ruff formatting and lint passed;
- strict MyPy passed over `109` source files;
- the package build passed; and
- the full suite passed (`233` tests; three inherited Goal 006 Matplotlib
  deprecation warnings).

Spread rate was fixed at `rho = 1`, detection was homogeneous, and false
positives were absent. The two complementary pairwise checks now justify
framing one bounded three-parameter central-truth benchmark, but they do not
guarantee that the full `(rho, eta, p)` support will be precise or calibrated.
No commit or publication is authorised by this goal.
