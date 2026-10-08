# Arc 3 execution and numerical pilot

Status: execution pilot passes; larger-bank numerical qualification is running
under Barry's approved 24-hour envelope. No prey-effect recovery result is
accepted from this pilot.

## What has been established

The nine specified production maps and three sacrificial pilot maps preserve
the declared habitat inventory, sources and reachability. Both sampling
strategies meet their allocation and separation constraints on every map.
The [design review](design-review.md) records construction and its limits.
The parent inspected both galleries. Corridor dependence and barrier detours
are visible and supported by the graph descriptors.

All three pilot archetypes ran through the accepted simulation and likelihood
kernels, new union-site adapter and fixed-map synthesis. Each uses four
calibration and four evaluation histories, K64, and a reduced parameter grid.
All twelve campaign invariants pass, including common holdout observations,
shared observations at overlapping training sites, bank alignment, independent
calibration/evaluation seeds, and the rho-independent conditional null.
Synthesis completes 1000 paired bootstrap resamples and remains explicitly
labelled `non_scientific_pilot`.

The implementation uses one union of physical site coordinates per map.
Simulation generates the union once per history and then slices it into the
two designs. Each likelihood receives only that design's own 120 training and
40 holdout records. The accepted reference likelihood arithmetic is unchanged.
The two small reference seams allow a history subset of an integration bank
and explicit condition labels when assembling profiles.

Focused review repaired two synthesis errors before using its outputs:
map-specific campaign seeds must be allowed to differ, and the no-effect
exclusion quantity is already false exclusion under the onefold truth.
Regression tests cover both. Bootstrap evaluation validates the large saved
arrays once rather than rescanning them at every resample. Rho is reported
only as point-estimate accuracy context.

## Measured cost

The connected pilot also ran on the full G201/H181 parameter grid with the
first two calibration and first two evaluation histories. Measurements below
are seconds on this Mac mini, with two history workers. They are local timing
measurements, not a Linux performance guarantee.

| Bank draws | Bank generation | Integration | Four paired histories | Total |
| ---: | ---: | ---: | ---: | ---: |
| 128 | 3.77 | 21.45 | 7.67 | 32.90 |
| 2048 | 57.15 | 230.68 | 7.39 | 295.24 |

The larger run confirms that bank generation and integration dominate the
four-history numerical pilot. Integration is shared by all calibration and
evaluation histories within a map. A linear extrapolation is useful for
planning, but the eventual bank size must satisfy the prospective numerical
criteria and Linux timing must be checked on its target.

## Numerical status

The K128 to K2048 exploratory comparison moves centred *joint-surface* LR by
up to 2.68 in calibration and 4.19 in evaluation, within the union where either
joint LR is at most ten. This is a diagnosis of the tiny execution bank, not
the declared marginal-profile convergence test or evidence against K2048.
The subsequent declared checks give:

| Nested bank comparison | Passing histories | Largest supplied / estimated effect-profile LR movement | Largest rho-profile LR movement | Largest generating-value LR movement |
| --- | ---: | ---: | ---: | ---: |
| 128 / 256 | 0 / 24 | 0.117 / 0.621 | 3.665 | 3.815 |
| 2048 / 4096 | 18 / 24 | 0.034 / 0.190 | 0.700 | 0.543 |

At K2048, effect MLE movement is at most one H181 cell and rho MLE movement
is at most one G201 cell. The six failing comparisons are the access design's
three effects in calibration history 1 and evaluation history 1; their rho
profiles exceed the unchanged 0.5 LR limit. K2048 is therefore not accepted.

The separate K128 half-grid check gives maximum rho gain 0.272 log-likelihood
units, exceeding 0.25; effect gain is below 0.000374. Half-grid accuracy at a
larger bank remains to be assessed. The K2048 check is explicitly bank-only;
there is no need to spend further refinement work accepting a bank that has
already failed its bank criterion. No cutoff, coverage, support topology or
sampling benefit is accepted from four histories.

The full-ensemble selected/doubled-bank comparison remains mandatory under
[Goal 046](Goal.md), including numerical stability of the primary sampling
contrasts. Conditional nested-bank agreement alone does not establish exact
integration or landscape-population uncertainty.

## Evidence and current boundary

Raw reproducible bundles are under `artifacts/arc3_pilot/`, with source hashes,
seed manifests, saved banks and profile checksums. The three-map execution
synthesis is in `artifacts/arc3_pilot/execution-synthesis/`. The profile runner
rejects reserved production map seeds and production mode remains unavailable
until its settings are frozen.

The focused suite passed 45 tests covering Arc 3 and the affected
Arc 2C likelihood, campaign and synthesis paths. Scoped Ruff, formatting and
strict mypy pass. A read-only server probe found `deep-server-ts` idle with
about 123 GiB available RAM and 4.4 TiB free under `/data`. The bounded Linux
preflight subsequently passed 13 tests and reproduced the full-grid K128
Mac pilot: bank checksums and MLE arrays are identical, with maximum numeric
profile difference 1.37e-12. Linux elapsed time is 108.70 seconds. Its K2048
serial and four-worker runs are complete: integration takes 807.62 and 224.18
seconds respectively, a 3.60-fold speedup, and every saved profile array is
exactly equal. Whole-run time falls from 988.05 to 398.45 seconds. The parallel
implementation also passes bitwise serial/parallel integration and campaign
tests. The updated numerical checker uses the same bounded parallel builder;
its 11-test Linux campaign/checker suite passes before larger qualification.

The three K16384/32768 qualification jobs are now running under new Goal 046
authority. Their paths, common deadline and monitoring are recorded in
[execution state](execution-state.md). The work remains uncommitted, and
Goal 045's exceptional compute and publication authority has not been reused.
