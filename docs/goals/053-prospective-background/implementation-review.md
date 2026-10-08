# Goal 053 implementation scientific review

27 September 2026. **Decision: proceed to the bounded Linux/full-bank timing
qualification. Production is scientifically cleared only if that qualification,
the frozen-input bindings and the measured budget gate all pass unchanged.**

## Scientific target and implemented comparison

The implementation matches the registered six-cell prospective comparison. One
paired block shares predator spread, prey event thresholds, detection uniforms
and, where applicable, the residual Gaussian background field across
`E0_h1`, `E0_h3`, `E06_h1`, `E06_h3`, `B100-A_h1` and `B100-A_h3`. The exact
background hazards are normalised over the whole accepted landscape at beta 0
or 0.60 and have mean 0.002. The B100-A cells replay the Goal 051 heterogeneous
background mechanism. The analyst receives only the six imperfect-detection
surveys; true arrival and extirpation times remain evaluator records.

The primary estimands are across-history error in log h and the direct
held-out conditional-prey log-score difference between the fitted adjusted and
constant-background analyses. Training uses the fixed 120 sites and scoring
uses the untouched 40-site holdout. The known-beta analysis is an evaluator
benchmark for the four exact cells. The oracle-arrival lane is restricted to
the registered first 250 blocks and those four cells. The simulation block,
rather than a site or survey, is the replicate and bootstrap unit.

This scope supports inference for repeated histories on the one fixed landscape,
sampling design, survey schedule, detection probability, nuisance settings,
integration bank and finite beta/h grids. It does not estimate performance over
new landscapes or designs and does not establish frequentist coverage, test
size, power or causal generality.

## Findings and repairs incorporated before qualification

The final code resolves the scientifically consequential defects found during
review:

- B100-A retains its known h truth, so its primary h-error outcomes are not
  discarded; only beta truth is undefined there.
- Oracle indices select exactly four exact cells in each of the first 250
  blocks, giving the registered 1,000-history oracle panel.
- The h=1 boundary diagnostic compares `E0_h1` and `E06_h1` and measures beta
  displacement relative to each cell's truth.
- Near-valued Fable forecasts are reported as estimates, distances and
  uncertainty intervals. Only the explicitly registered upper contradiction
  bounds are evaluated as bounds; the advisory target values do not gate the
  result.
- Adjusted and constant fits are selected on training likelihood before their
  direct held-out scores are evaluated. Model preference uses the sign of the
  raw paired score difference with a 1e-12 numerical tie tolerance, then reports
  the effect in nats per holdout site.
- Known-beta fits are extracted from the same training surface at the exact
  registered beta row. Log-RMSE, signed bias, point-error rates, beta error,
  model wins/ties, grid-edge contacts and coarse-grid sensitivity are retained.
- Uncertainty uses exactly 2,000 whole-block bootstrap draws with root
  2026092703. Primary draws preserve all six paired cells; oracle draws use the
  fixed 250-block subset. These intervals measure simulation Monte Carlo
  uncertainty, not parameter uncertainty for a single history.

The likelihood runner replays all 24 frozen Goal 052 score surfaces at every
beta row and checks the h=1 factorisation identity. It caches complete beta rows
with identity and checksum receipts, assembles the four registered score
rectangles only after all 81 production rows are authenticated, and refuses a
source or wrapper change within a phase. True arrivals enter only the explicit
oracle scorer; held-out prey observations do not enter fitting.

## Provenance and execution controls

Fresh production, timing, smoke and bootstrap roots are distinct from each
other and from the enumerated Goal 049--051 and archived-bank roots. The runner
binds the full source manifest, helper, registration, Goal 052 contract and
evidence, frozen legacy sources, bank provenance, worker identity, seed
manifests and observation order. The controller and wrapper add exclusive
locks, one launch per phase, wall-time and 48 GiB address-space limits, measured
timing projection, persistent start/end/exit receipts, full row coverage and
output checksum verification. A completed or partially attempted phase cannot
be silently restarted.

Local verification on the final tree passed:

- the 23-test generator/campaign suite: 13 Goal 051 generator controls plus
  ten Goal 053 generator/campaign tests, including stream replay and a
  reduced-bank cache/scoring smoke;
- the 14-test direct Goal 053 suite: those ten tests plus four synthesis tests;
- Ruff for the three modules, two CLIs, their tests and the controller;
- strict mypy for the three modules and two CLIs;
- Bash syntax for `run-bounded.sh` and Python syntax for the controller/CLIs.

The standalone controller deliberately remains a small dynamically typed
operational script; it passes Ruff and syntax checks but is not strict-mypy
clean. Its Linux commands, full bank, memory ceiling, concurrency and timing
projection still require the registered target-host timing qualification.

## Scientific limitations and decision gate

The principal remaining risks are inferential rather than implementation bugs.
The beta-h surface may be multimodal or truncated by the finite grid; h=1 is a
nonregular boundary; B100-A is misspecified because residual G is omitted from
the analyst model; latent arrivals, interval-censored loss and imperfect
detection can strengthen trade-offs that are modest with complete data. The
holdout tests spatial transfer within the same fixed landscape and process, not
extrapolation to another landscape. Shared sites within a history are not
independent replicates, and the block bootstrap correctly avoids treating them
as such. LR<=2 widths and profile shapes remain uncalibrated geometry.

The independent information review supports event scarcity and a negative
h-beta trade-off as mechanism hypotheses but does not prove that weak observed
information is mostly event-limited. Its complete-data simulation generated
only auxiliary prey-loss thresholds conditional on already examined Goal 052
arrival arrays. It generated no fresh prospective process history or survey,
did not use Goal 053 roots or scorers, and accessed no registered main outcome.

No production history, timing result or registered Goal 053 outcome was
available to this review. Proceed with preflight and the 20-block, 16-row Linux
timing phase. Launch production only if the target identity, full-bank replay,
source bindings, cache controls, measured budget and output checks pass without
repair or substitution. Independent scientific review of the completed
production synthesis remains material because the observed-data result, grid
contacts and B100-A behaviour can still overturn the mechanism forecasts or
limit the paper claim.
