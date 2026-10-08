# Independent methods review: four-node effect-reference micro-pilot

4 October 2026 (Hobart). This review is limited to the approved public
micro-pilot: 999 null histories at each of four fixed nuisance nodes, with
`h = 1`, using the full correlated-spread generator and the adjusted null and
free-`h` fits. It does not authorize or review the later 765-node screening
calibration, a new arrival map, sealed outcomes, or publication claims.

## Decision

**Proceed with implementation and bounded execution after the registration
freezes the fixed RNG addresses, fit-success fields, failure propagation, and
independent-audit rules below.** The design can test whether the existing full
effect-reference path is numerically valid and operationally feasible at the
four selected nodes. It cannot establish screening calibration, type-I error,
power, coverage, effect recovery, map transfer, or broad-grid cost.

An optimizer failure is an observed pilot outcome, not a reason to abort the
whole campaign or replace a draw. The campaign should continue to its resource
cap, retain the failed address and diagnostics, and make the affected node
unavailable for downstream reference-table use. This distinction permits an
informative negative pilot without silently selecting histories that are easy
to fit.

## Scientific target and scope of inference

The scientific object needed later is the nodewise null distribution of

\[
T = 2\max\{0,\ell_{\mathrm{free}}-\ell_{h=1}\},
\]

where both likelihoods are fitted to the same complete synthetic history and
the nuisance parameters remain continuous within their registered bounds. For
this micro-pilot, the estimands are narrower:

1. the empirical distribution of `T` at each of the four fixed nodes,
   conditional on the fixed landscape, empirical arrival bank, observation
   schedule, generator, fitting algorithm, and source state;
2. the per-node count of valid and failed null/free fit pairs, with failure
   modes, boundary frequencies, objective-ordering violations, and runtime;
3. the process-level wall time and peak memory needed to produce and audit the
   3,996 registered histories.

The sampling units for Monte Carlo inference are independently addressed full
histories. Sites within a history are not replicates: their latent predator
arrivals arise from the correlated-spread process and their observations share
that history. Generating sites independently, resampling sites, or conditioning
away the spread dependence would target a different null distribution.

Fitted likelihood integration must use the qualified empirical bank identified
by its receipt and hashes, with shape `(131072, 160)`, rather than a reduced
development bank or an unverified path. History generation separately uses the
full correlated-spread generator. The adjusted fit pair must preserve the
existing fitting sequence: fit `adjusted_h1`, then fit `adjusted_free_h` with
the null parameters and convergence flag supplied as the extra candidate and
success flag. A thin wrapper around the existing primitive is acceptable only
if a mechanical check shows that its two outputs equal the adjusted pair
returned by the existing four-model route on fixed test histories. The fitter
itself should not change for this pilot.

The four nodes are

| beta | mu | detection SD | role |
| ---: | ---: | ---: | --- |
| 0 | .0025 | .2 | interior reference node |
| -2 | .0005 | 0 | joint low-rate and boundary stress test |
| 2 | .006 | .4 | high-rate and beta-boundary stress test |
| -2 | .006 | .4 | opposite-beta high-rate stress test |

This is a deliberately non-factorial stress panel. Differences among nodes
cannot be attributed separately to beta, mu, or detection SD. Boundary nodes
are valuable for finding non-regular optimization behavior, but they do not
estimate a population average or justify interpolation across the nuisance
space. All histories are generated under `h = 1`; the pilot contains no
alternative-effect experiment and therefore provides no power or non-null
recovery evidence.

With 999 valid references, a later fixed nodewise rank test would have Monte
Carlo resolution `1 / (999 + 1) = .001`. That arithmetic does not itself
validate the table. It applies only when the registered reference sample and
fitting rule have been executed without outcome-dependent deletion or
replacement.

## Consequences of the revised screening grid

The approved screening lattice has 17 beta values from -2 to 2 in steps of
.25, nine mu values, and five detection-SD values: 765 nodes. This changes only
the discrete screening/calibration lattice. It must not change the continuous
nuisance domains or multistart optimization used in the null and free effect
fits.

The local screening statistic must consequently use beta neighbours separated
by .25. Existing 99-reference screening tables were generated for a different
stencil and cannot calibrate that revised statistic. Before any later
retention, four-case union, coverage, or Berger--Boos decision claim, the
revised statistic needs fresh nodewise calibration on the 765-node lattice.
The present four-node effect micro-pilot does not provide that calibration.

The earlier public fixtures with true `beta = .6` are now off-grid; .5 and .75
are neighbouring lattice values, not substitutes for the true node. Those
fixtures cannot receive an exact known-truth-retention or finite-grid guarantee
under this lattice without a separately registered off-grid analysis. The four
micro-pilot beta values are on-grid, so this issue does not alter the pilot's
own fixed-node reference target.

## Fixed-address failure and acceptance rules

Each of the 3,996 references needs a preassigned address derived from the
registered master seed, node, and replicate index. The authoritative row must
record generation status, null-fit status, free-fit status, likelihoods,
parameters, optimizer diagnostics, elapsed time, and whether the independent
audit passed. A failed fit remains at its address. It must not be dropped,
redrawn under a new seed, or repeatedly optimized until it happens to pass.

There is no automatic second registered attempt after an infrastructure
interruption. Preserve the failure and partial artifacts. Any same-address
recovery requires a separately authorized, qualified repair that cannot select
among competing outcomes. Numerical optimizer failure is the result for that
address and must propagate to abstention. If either required fit is invalid,
`T` is invalid; do not coerce it to zero or infinity.

Fit nonconvergence, a free fit below its nested null fit, or a null optimum
below the known generating point beyond tolerance are address-level numerical
failures. Record them, do not retune their starts after inspecting the result,
and continue other addresses while resources permit. In contrast, an
independent likelihood mismatch, non-finite likelihood kernel at a defined
finite point, broken schema/addressing, provenance failure, or resource-cap
breach can invalidate more than one reference. Stop new dispatch on such an
event, preserve partial output, and diagnose it before resumption.

Three levels of outcome should be reported separately:

- **Campaign complete:** every registered address has one authoritative,
  accounted outcome; manifests, hashes, node counts, RNG-address checks, and
  serialization checks pass. Numerical failures may be present and are part
  of the result.
- **Node table usable:** all 999 registered fit pairs at that node are valid,
  the independent audits pass, and no unresolved ordering or provenance
  violation remains. Under the current exact-rank contract, any invalid
  reference makes the node table unavailable and forces downstream abstention
  (`p = 1`). A different failure-aware rank rule would require prospective
  registration and calibration; it must not be invented after seeing failures.
- **Pilot operationally successful:** all four node tables are usable and the
  run stays within 16 workers, 48 GiB process-group peak memory, and two hours,
  with generation, bank loading, fitting, auditing, and serialization included
  in the timing. A completed campaign with unusable nodes is still an
  informative negative result, not a reason to erase or replace histories.

Continue past individual optimizer failures. The cross-row failures just
listed are campaign safety stops, not opportunities to replace affected draws.
Preserve and receipt all partial output on such a stop.

## Independent numerical audit

The production scorer is not sufficient evidence for its own output. Adapt
the already qualified direct-bank reconstruction in
`scripts/audit_preinvasion_feasibility.py`; keep the independent implementation
separate from production likelihood, compression, fitting, and execution code.
For every successfully fitted history, evaluate the independent whole-history
log likelihood at:

1. the generating true null point;
2. the production null optimum (`h = 1`);
3. the production free-`h` optimum.

Compare each independent score with the corresponding stored production score
to absolute tolerance `1e-8`, and reconstruct `T` independently to tolerance
`1e-6`. Also require, to `1e-6` log-likelihood tolerance,
`ell_null >= ell_true` and `ell_free >= ell_null`, because the null optimizer
is optimized over a feasible domain containing the true point and the free
domain contains the null model; the true point need not be an optimizer start.
A larger ordering violation is an address-level optimization failure even if
an optimizer reports success; it is not an independent-scorer mismatch.
Retain the row, do not refit it after inspection, and propagate its invalid
status rather than clamping away the diagnostic. A
production-versus-independent score disagreement at a defined point is a
campaign safety stop because the same defect may contaminate otherwise
converged references.

The audit should cover every successful reference because direct score
evaluation is cheap relative to the two fits and because rare, node-specific
errors matter in an extreme-tail reference table. For failed fits, audit any
finite stored score that has a defined parameter point, preserve the failure
status, and do not manufacture a valid statistic. Report maxima and counts by
node and evaluation point, not only a pooled pass flag.

## Claims that the pilot cannot resolve

- A small count such as `R <= 10` under a proposed screening statistic is a
  descriptive support proxy. It is neither a best-possible retained-set result
  nor an upper bound such as 40% on a future four-case union or computational
  cost.
- Coarsening the beta stencil can increase an observed local discrepancy, but
  it also changes the reference distribution of that discrepancy. Candidate
  sets and unions may shrink or grow. A claim that recalibration will be “no
  worse” requires the fresh registered ranks; geometry alone does not prove it.
- Pre-invasion mu error and its observed compensation with `h` describe one
  component of a joint fit. They do not determine the sign or probability of
  full-data `h` error once correlated arrivals, post-invasion observations,
  detection parameters, and nuisance trade-offs are fitted jointly. The
  micro-pilot may describe the null distribution of `h-hat` at four nodes, but
  it cannot establish non-null bias or recovery.
- Pointwise fit-failure fractions and statistic summaries have binomial or
  Monte Carlo uncertainty, but four purposively selected nodes do not support
  extrapolation to all 765 screening nodes, new maps, or empirical data.

## Residual risks and recommendation

The main remaining risks are multimodal or boundary optimization, informative
fit failure, numerical disagreement between compressed production and direct
likelihoods, and underestimation of process-group memory or contention at 16
workers. The fixed-address abstention rule protects validity against selective
deletion; the all-row independent audit tests the central numerical claim; and
separate generation/fit/audit timing will show where the resource estimate
fails.

The approved micro-pilot is scientifically worthwhile on those terms. Its
result should be reviewed independently before any tables are reused in a
later test. Independent review can materially change confidence in numerical
qualification and failure handling, but it cannot turn this four-node null
experiment into evidence for screening calibration, power, or generality.
