# Goal 025: Spread-Duration / Detection Transition Benchmark

## Scientific Question

How fast must the invasion wave progress during the survey period before
delayed arrival can be separated reliably from imperfect detection?

## Frozen Comparison

Treat the accepted Goal 023 production evidence as two fixed anchors:

- `rho = 0.7578582832551991` (`log2(rho) = -0.4`): `250/250`
  connected interior supports, median detection-probability width `0.26`, and
  `three_parameter_recovery_imprecise`; and
- `rho = 1.0`: `250/250` connected interior supports, median
  detection-probability width `0.20`, and
  `advance_to_cross_truth_three_parameter_benchmark`.

Evaluate one new on-grid log-scale midpoint truth only:

- `(rho, eta, p) = (0.8705505632961241, 1, 0.65)`, equivalent to
  `log2(rho) = -0.2`.

Keep the accepted refined eta grid, rho and detection grids, 4,096-draw
integration bank, landscape, 160-site design, survey calendar, two visits,
zero-false-positive observation model, seed streams, 250 calibration histories,
250 validation histories, and 239th ordered calibration cutoff unchanged.
Calibrate the midpoint truth independently. Do not recompute the accepted
anchors.

## Decision

The spread-detection gate requires:

- calibrated coverage whose 95% Wilson interval contains `0.95`;
- at least `238/250` connected interior supports;
- median log-rho error at most `0.10` and width at most `0.50`; and
- median detection-probability error at most `0.05` and width at most `0.20`.

Report the inherited full three-parameter decision separately. After evidence
reconciliation and invariant checks, return:

- `spread_detection_transition_between_0_758_and_0_871` if the midpoint meets
  every spread-detection gate;
- `spread_detection_transition_between_0_871_and_1_0` if calibration and
  topology are valid but one spread-detection precision gate fails; or
- `spread_detection_transition_unresolved` if the accepted anchors,
  calibration, topology, or implementation do not reconcile.

Either bracket completes the goal. Do not extend the survey window, add
another midpoint, or retune a threshold after seeing the result.

## Compact Review Surface

Write exactly five ignored files:

- `transition_summary.csv`, containing the two accepted anchors and new
  midpoint;
- `midpoint_validation.csv`;
- `summary.json`;
- `review.md`; and
- `spread_detection_transition.svg`, comparing connected-interior frequency,
  coverage, point recovery, and interval widths across the three rho values.

## Validation And Stop Rule

- one Goal 025 scientific module and one CLI;
- three focused tests for accepted-anchor reconciliation, decision logic, and
  the exact reduced-smoke review surface;
- one reduced non-scientific smoke, one timing probe, and one production run;
- one inspection of the table, memo, validation distribution, and rendered
  figure;
- Ruff, strict MyPy, one full test run, and package build; and
- at most one material repair.

Do not add interacting truths, survey-window changes, alternative observation
designs, prediction scoring, neutral models, prey dynamics, real data, or a
finer spread-rate search. Stop at human review; commit and publication require
later acceptance. Hold a collaborator discussion before any interaction-truth
or observation-redesign goal.

Barry approved proceeding with Goal 025 on 9 August 2026.

## Outcome

The production run completed locally in 26 minutes 7 seconds and returned
`spread_detection_transition_between_0_871_and_1_0`.

The accepted Goal 023 anchors reconciled exactly. At the new midpoint
`rho = 0.8705505632961241`, calibrated coverage was `236/250 = 0.944`
(95% Wilson interval `0.908` to `0.966`), and all `250/250` likelihood-ratio
supports were connected and interior. Median log-rho error was `0.028` and
median log-rho width was `0.388`, both within their gates. Median detection
error was also within its gate at `0.020`.

The sole failed spread-detection gate was median detection-probability width:
`0.24` against the prespecified `0.20` limit. The evidence therefore brackets
the practical transition, for this synthetic landscape and survey calendar,
between `rho = 0.871` and `rho = 1.0`. This is an uncertainty limitation rather
than evidence of systematic bias or disconnected likelihood support.

The slower accepted anchor remained imprecise at detection width `0.26`; the
central anchor remained acceptable at `0.20`. No survey extension, finer
midpoint, threshold retuning, or interaction truth was attempted.

## Validation

The reduced smoke, timing probe, production run, five-file artifact contract,
transition table, validation distribution, review memo, and rendered figure
were inspected. Final repository checks comprised the focused Goal 023-025
tests, full test suite, Ruff formatting and linting, strict MyPy, package build,
and `git diff --check`. Generated artifacts and build outputs remained ignored
and unstaged. Goal 025 stops here for collaborator review; no Goal 026 work was
started.
