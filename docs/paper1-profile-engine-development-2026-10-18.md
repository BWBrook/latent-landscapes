# Paper 1: profile engine and monitoring-input development

18 October 2026. This work advances charter pillars 3 and 4: reliable
effect inference across monitoring designs and competing background models.
It implements the numerical direction discussed in Correspondence thread 87,
Claude message 2037 and Codex reply 2051. The preceding
[development record](paper1-numerical-development-2026-10-18.md) retains the
earlier fitted endpoints and their checks. Goal 062 remains closed.

The work here develops a reusable observed-data engine and the inputs for
the [integrated study](paper1-integrated-tranche-protocol-2026-10-18.md).
It does not establish calibration, effect recovery, confidence-set coverage,
or new-map generality. No 600-case qualification experiment has been launched.

## Criterion and implementation

The new [spatial engine](../src/latent_landscapes/spatial_profile.py) fits
`log lambda = alpha + beta A + u` with the specified sampled-site GP covariance.
It retains the site-marginal arrival likelihood and the Laplace working
criterion. It evaluates the exact variance-zero family separately. The
interpolation grid currently has 161 log-hazard nodes from -12 to -2.

Vectorised cubic-spline evaluation supplies the first three site derivatives.
The analytic outer derivatives include the dependence of the latent mode on
alpha, beta and log spatial SD. With site second derivatives D, third
derivatives T, prior precision Q and mode Hessian H=Q-D, the mode sensitivities
solve `H u_alpha = D 1`, `H u_beta = D A`, and
`H u_log_sigma = 2 Q u`. The Laplace derivative includes the corresponding
third-derivative trace term. h and detection-SD derivatives currently use
guarded finite differences.

Exact-key bounded caches avoid the rounding defect found in the earlier
prototype. Each latent-mode calculation compares a deterministic zero start
with a supplied warm start. Positive-definiteness, mode stationarity, outer
projected gradients and support are checked explicitly. A four-posterior-SD
support guard rejects unsupported spline proposals. Automatic grid expansion
and a joint tail-mass certificate are still outstanding.

Independent audit also found a continuity defect: near a converged mode,
strict objective improvement could reject a Newton correction smaller than
floating-point resolution. The repair permits objective roundoff only with
residual improvement. A secondary stationarity check requires raw score at
most 1e-7, Newton decrement at most 1e-8 and a parameter-scaled Newton step
at most 1e-8; its diagnostics are retained. The ordinary mode-score target is
1e-8 and the outer projected-gradient target remains 1e-3. A correlated-covariance,
small-variance regression covers the perturbations that exposed the failure.

The initial profile search sweeps 35 logarithmic h nodes from 1 to 30 in both
directions, includes variance zero at every node, and carries neighbouring
solutions forward. Local mesh maxima supply free-h optimisation starts.
Bounded Powell recovery handles an observed L-BFGS failure to move. The
benchmark reports the best eligible value at each h, retaining every start
and identifying unresolved candidates above that envelope. A successful free
fit is not a certificate for the entire profile: adaptive peak and cutoff
refinement and confidence-set topology checks remain necessary.

The [benchmark driver](../scripts/benchmark_spatial_profile.py) aligns public
site identities, observation calendars, initial cohort state, training labels
and availability masks. It accepts arbitrary site counts and raw or compressed
arrival banks, and reads no evaluator truth. Receipts retain input/source
hashes, versions, thread settings, timings, memory and branch diagnostics.

## Component checks

On the two archived 120-site histories used in the earlier prototype:

| Check | B_H3 | H3 |
| --- | ---: | ---: |
| Absolute criterion difference at the stored free optimum | 3.81e-9 | 1.16e-9 |
| Maximum analytic-gradient difference from local central differences | 5.47e-8 | 9.63e-8 |

At spatial SD .001, the maximum gradient discrepancy was 1.01e-8.
The exact-zero criteria agreed within 2.27e-13. Cached endpoint evaluation
took approximately .0026–.0028 seconds, about 12 times faster than the earlier
implementation. Cold evaluation improved by about 1.5 times. These component
timings do not measure complete profiles or the six-model analysis.

The durable check additionally compares step sizes and fitted-mode spline
intervals. Broad optimizer-style finite differences differed from analytic
core derivatives by as much as 4.98e-4; five coordinate checks crossed knots.
The selected local steps leave every fitted mode in its original interval.
Across all four endpoints their maximum discrepancy is 9.63e-8. Cubic site
splines are twice continuously differentiable, but the Laplace derivative
uses their third derivatives and can jump at knots. This is a property to
qualify through grid refinement and optimisation checks, not a reason to label
every broad-step disagreement a derivative error. Both the initial diagnostic
and the corrected step study are preserved.
The pointwise projected gradient is therefore not by itself a smooth KKT
certificate at or arbitrarily near a spline-knot surface. Optimizer convergence
also needs interval-aware local perturbation checks.

## First complete mesh traversal

The single-thread Mac mini B_H3 run traversed all 35 h nodes in both directions
and fitted both free endpoint families in 190.73 seconds (190.80 including
loading and reporting), with peak RSS 358 MiB. It retained 712 optimizer
candidates, 19,623 curve builds and 33,952 mode calls. The selected free optimum
was h=4.1916456, criterion -1716.447035491 and projected gradient 5.53e-6.
The h=1 criterion was -1724.602373144, giving LR=16.310675307. These reproduce
the earlier endpoint result closely.

The traversal did **not** produce a complete eligible profile. Variance zero
resolved at all 35 nodes, but positive variance resolved at only 18. Every
node from h=6.05348 through 30 was unresolved. No retained eligible point
exceeded the free maximum; that check alone cannot certify missing profile
branches. The receipt therefore states `profile_certified: false`. This
191-second spatial-only mesh traversal does not meet the 20-second six-fit
plus full-profile target, and it is not a Deep-core timing measurement.

Independent reproduction identified the first failure precisely: at
h=6.05348, the fitted base proposal was just inside the four-SD support guard,
but a detection-SD finite-difference perturbation moved its upper edge to
-1.999999898, outside the grid ending at -2. The optimizer had reached an
artificial support boundary. One-sided differentiation would conceal the
problem; the remedy is to widen the grid and recompute. This is distinct from
the spline-knot derivative issue above.

The original order-48 compressed arrival bank covers an exponential-series
argument only up to 5; large h proposals therefore triggered expensive raw-bank
integration. A separately identified order-192 representation of the same
131,072 arrival draws covers arguments up to 40. The h=30, log-hazard=-2 corner
requires 39.2472. The positive-term series has an independently computed
geometric tail bound of 2.90e-50 at 40. On three selected real sites, comparison
with direct integration at arguments 5, 20 and 40 gave maximum absolute
differences 1.39e-17, 1.08e-19 and 1.48e-21, respectively. This changes the
numerical representation, not the arrival draws or the scientific design.

The raw array checksum and category masses/counts were preserved exactly.
Recomputing moments at the higher order changed 32 of 47,040 shared lower-order
entries by one floating-point ULP (maximum absolute difference 2.78e-17).
The preparation receipt records that roundoff explicitly; it does not claim
bitwise preservation of those moments.

## Wider-grid diagnosis and stopping decision

The reviewed extension retained the original .0625 log-hazard spacing and
the same arrival draws. An order-816 representation covers series arguments
up to 290, sufficient for a grid from -14 to 0. Its independently calculated
tail bound is 4.44e-15; selected direct-integration comparisons at arguments
40, 145 and 290 agree within 1.29e-14 relative error, with no underflow
mismatches. At the stored free optimum, extending the grid changes the
criterion by exactly zero at the recorded precision.

The enlarged bank is adequate, but probability-scale likelihood arithmetic
is not. At h=30 the first failed grid node is log-hazard -.875: one observed
history probability becomes exactly zero. Direct integration over the raw
arrival draws reproduces the same failure at the same site. At the preceding
node, -.9375, the minimum positive probability is 1.48e-306. This is arithmetic
underflow, not error in the compressed series.

Independent review allowed one intermediate nested grid, [-14,-1], requiring
both variance families to resolve and positive-variance proposals to have
at least .25 log-unit support slack. The starting base and detection-SD
perturbations have finite probabilities at the upper node (minimum about
6.85e-289 at h=30), but the fits fail the acceptance rule:

- At h=6.05348, the candidate criterion improves to -1717.05357022 and has
  .891 upper support slack, but its projected gradient is .001803, above .001.
- At h=30, a search candidate pushes the proposal maximum to -.986191,
  outside the intermediate grid. Even the last numerically valid node would
  leave only .04869 support slack for that candidate, below the required .25.

Neither positive-variance fit is accepted. No further grid adjustment or
full-mesh rerun was made. Stable log-domain likelihood scoring is the next
implementation prerequisite; automatic expansion, local convergence checks,
cutoff refinement and joint-tail assessment still need qualification after
that repair. The retained free optimum and successful component checks do
not establish the missing upper profile.

## Observation masks and monitoring geometry

The observation object now carries an optional immutable predator-visit
availability mask. An unavailable visit contributes a neutral emission,
including before latent arrival; its placeholder count supplies no evidence
of absence. The mask survives site sorting, train/holdout subsetting and the
oracle-arrival diagnostic. Omitting the mask preserves fully observed inputs.
Development exposed and repaired an existing ordering error: cached predator
emissions had been calculated before the corresponding site counts were
sorted. The archived public inputs used here were already sorted.
The fixed arrival-category representation also requires the canonical six
predator survey times. Unsupported shifted calendars now fail explicitly.
The spatial API requires preselected training sites; the benchmark subsets
all aligned inputs and records the excluded holdout count. These guards close
two errors found before the real profile benchmark was started.

The original access rule failed a basic capacity check. With the first
40 holdout sites fixed, all three pilot archetypes were infeasible for the
260-site training union. Joint selection of all 300 sites on the original
network solved the connected and corridor pilots, but the barrier pilot
remained infeasible. Independent review supported a common two-cell buffer
around network centres and joint selection of the master panel before random
holdout labels. This changes the sampling design prospectively; no biological
histories were examined to make the change.

The new [monitoring module](../src/latent_landscapes/monitoring_design.py)
selects 60 five-site clusters jointly, 15 per source-distance stratum, with
eight-cell minimum centre separation. Independent seeded labels reserve
40 holdout sites and define nested 120/260 training panels. The 120-site panel
also identifies the fixed predator network; the other 140 C sites have missing
predator visits. The seeded MILP priority objective is explicitly nonuniform
over feasible panels. Freeze selected identities and solver/input receipts;
do not interpret a solver timeout as map infeasibility or silently replace it.

All 30 prespecified maps passed the zero-objective capacity diagnostic:
10 connected, 10 corridor and 10 barrier maps. Counts, global spacing, unique
footprints, passability and reachability all passed. No seed was replaced.
The actual seeded-priority selector also completed on the three pilot maps,
in 2.01, 3.10 and 1.01 seconds respectively, including map construction and
checks. These selected panels contain the required 300/260/120/40 sites;
no biological histories have yet been generated on them.

## Qualification decision

Independent methodological review separates numerical accuracy of the chosen
criterion from sensitivity to a more accurate integral. It also rejects a
population-level 99% agreement claim from 600 cases partitioned into many
regimes. The protocol now defines those cases as a challenge suite, keeps base
and enriched cases separate, requires complete confidence-set comparisons and
specifies Monte Carlo precision for importance references. A reference that
fails its precision check is indeterminate. Any adaptive integration fallback
needs an observable frozen trigger and calibration of the resulting procedure.

Claude's 20-second target applies to six fits plus the complete profile on one
Deep core. It remains an engineering target, not a scientific acceptance rule.
Even at that target, the illustrative 5.832-million-dataset allocation costs
about 26.5 ideal days on 51 workers before overhead. A one-week estimate for
only arm A cannot price the full three-arm study.

The next numerical decision first requires log-domain scoring and then
complete, independently checked profiles
on both site counts and difficult geometries, followed by the frozen challenge
suite. It must retain difficult cases and diagnose failures, rather than trade
away the agreed scientific design to meet a runtime target.

The final focused test run passed 151 tests covering likelihoods, missing
visits, execution/subsetting, monitoring geometry and the spatial engine.
Lint and type checks passed for the changed implementation and drivers.
The [evidence archive](evidence/paper1-profile-engine-2026-10-18/README.md)
retains receipts, exact executed source snapshots and payload hashes;
the [independent review](evidence/paper1-profile-engine-2026-10-18/review.md)
records the scope of acceptance and remaining limitations.

Codex GPT-6 integrated this work. Specialist implementation, execution and
independent review used the configured GPT-5.6 Sol and Luna subagents; Claude
provided the peer proposal on Correspondence. Final human review remains
required before release.
