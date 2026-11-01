# Paper 1 development challenge panel

1 November 2026. Status: independently reviewed design frozen before panel fits.

Barry's instruction in this chat was: "Claude has now responded. Proceed."
The bounded objective follows Claude's Correspondence message 2801, thread 87:
challenge the spatial procedure across weaker information and misspecified
backgrounds while assessing latent-integration sensitivity and whether a lean
profile search can reproduce the dense numerical reference. It advances the
charter's uncertainty and generality pillars and the integrated development
protocol. This is development, not calibration, registration or validation.

## Operating scope and completion condition

Complete the prespecified archived panel, retain all failures, compare dense
and independently started lean searches, assess higher-accuracy integration
at fitted locations, and synthesize the arm-A/B descriptives. A negative or
indeterminate numerical result is a valid panel outcome. Do not choose cases
or revise thresholds after inspecting their outcomes. Freeze the detailed
design after independent review and before panel fitting. The optional
260-site extension requires a tested general-site biological-data adapter;
its readiness and scope will be decided before new outcomes are generated.

Authorised work includes the necessary modular Python changes, tests, small
smokes, project compute, receipts, reports, commits and pushes to the existing
private remote. It includes read-only consultation of the Nectar control
plane under `/Users/bwbrook/work/nectar`, live readiness checks through the
`nectar` SSH alias, and project source/data/runs/archives under
`nectar:/data/codex/latent-landscapes/` and `/data/share/latent-landscapes/`.
Use Git for source and rsync for payloads. Bulk panel receipts stay in the
project archive; Git holds compact summaries, manifests and hashes. No public
release, external-person messages, campus route changes, production campaign
or recurring monitoring is included. Any deliberate machine resize follows
the existing Nectar coordination and return-to-c3.large policy.

## Cases fixed before outcome inspection

Use Goal 062 cells 0, 1, 3, 4, 6, 7, 8 and 9: exact/B100-A backgrounds crossed
with mu .001/.004 and h 1/3. Select replicates 005 and 006 in every cell.
This deterministic choice avoids the two previously profiled rep000 cases and
the original Goal 062 rep000–004 diagnostic subset; it does not make these
archived data untouched validation. Each of the sixteen histories supplies
arm A and arm B on the same 120 training sites, for 32 datasets. All forty
holdout sites remain excluded.

A retains prey dates -60,-50,...,60. B masks dates through day zero and retains
10,...,60. Both preserve cohort_start=-60, initial_alive and all predator
observations. No conditioning on observed survivors or cohort restart is
permitted. An explicit prey-observation mask will be checked against the raw
sliced-calendar likelihood before use; masked observations contribute neutral
emissions, never observed absences. The full latent calendar may be retained
for exact compressed evaluation. Fit using frozen stored exposure arrays.

The current 260-site master sampler is available, but frozen Goal 062 setup
wrappers explicitly require 160 sites. A new history cannot be obtained by
extending archived outcomes. The reusable biological kernels accept arbitrary
site coordinates; a separate adapter must generate the full master history
jointly and preserve the common predator network, missing predator data at
the extra 140 training sites, whole-map normalization and forty holdouts.

## Scientific gates

The dense reference and lean candidate retain both spatial-variance families,
the h domain [1,30], nuisance bounds and projected-gradient gate 1e-3. Their
searches are independent of generating h, dense roots and dense nuisance
starts. Report W(1), W(h_true), free maxima and all c=3.84 components after
search. A 10–15-fit cost is a hypothesis, not an assumed achievement or a cap.
Same-h W disagreement must be at most .01, log-root movement at most .005,
with agreement on components and domain contacts and no unresolved superior
candidate. All flat, tied, full, boundary and unavailable outcomes are retained.

Integration diagnostics require independent random streams, common draws
across compared points, draw doubling, tail/ESS diagnostics and Monte Carlo
uncertainty. A fixed-outer-parameter correction must not be presented as a
reoptimised importance profile. The reviewed estimator, bounded draw budget and
precision/decision rules are specified below.

Arm-A/B contrasts are descriptive: free sigma, ridge slope, diagnostic roots
and sigma-bound contact inside the diagnostic set. The depletion account's
directional expectation is a scientific prediction, not a numerical pass
condition. Definitions for zero variance, missing/domain-truncated roots and
disconnected sets are fixed below before arm-B fits.

## Readiness evidence

Two independent code scouts verified the eight public cell mappings and the
existence of all sixteen selected observation files without scanning outcomes.
They found the arm-B raw-evaluation performance trap and the absent general-site
assembly adapter. Independent methodological review accepted the design and subsequent repairs.
Nectar's initial live check found 8 vCPU, about 15 GiB available RAM, 255 GiB
free on /data, zero load and no scientific compute process. A measured target
smoke and coordination check precede any allocation or panel launch.

## Detailed execution specification (before outcome generation)

The following completes the design above; the final independent acceptance
and freeze identifiers are recorded below before execution.

### Searches and reporting

Both searches use the existing positive-spatial-SD and exact-zero families,
parameter bounds, direct likelihood, 192-term bank compression with raw-bank
fallback, and projected-gradient threshold 0.001. The dense reference starts
with 35 log-spaced nodes and their 34 midpoints, followed by adaptive feature
checks. The lean search starts from five log-spaced sentinels, independent
free fits started at log h = 0, log(30)/2 and log(30), and bounded Brent peak
searches where the sentinels identify a bracket. Both use warm starts from
their own neighbouring fits and refine cutoff crossings, family changes,
nuisance-bound changes, directional disagreement and nonmonotonic features.
The lean search has no mandatory dense spacing and no 10–15-fit cap. A
160-point operational guard retains an indeterminate result if exceeded.
A complete tighter-tolerance replay tests numerical convergence.

Generating h enters only post-search reporting. Neither search receives the
other's roots, parameters or caches. After freezing both results, evaluate
the union of their null, free-family locations and roots, plus generating h.
Any newly observed superior maximum, missing component, hole or unsupported
non-tied family transition invalidates the frozen result. Do not silently
repair the search using this information. Root residual tolerance applies
only inside verified root brackets. Record flat, tied, full-domain,
disconnected, truncated and unavailable outcomes explicitly.

Dense/lean agreement requires |delta W| <= 0.01 at common h, absolute
log-root displacement <= 0.005, agreement on components/domain contacts,
compatible owners (criterion ties within 0.0001), nuisance-bound contacts
inside the set, and no unresolved superior candidate. Count unique h values,
family fits, actual evaluations and elapsed time separately for search and
post-search checks. All c=3.84 sets are diagnostic development sets.

### Independent arrival banks

The sixteen high-hazard A/B datasets also receive the previously prepared
independent bank A, with the same fixed search procedure. Compare bank A
against B0 at common h with |delta W| <= 0.10 and log-root displacement <=
0.05, retaining component, ownership and boundary differences. Arrival-bank
sensitivity is separate from latent-integration sensitivity.

### Optional C extension

Include six cases if the independently reviewed adapter and outcome-free
selector replay pass: three frozen pilot archetypes (connected, corridor and
barrier), each at h=1 and h=3, exact background, mean hazard 0.004, beta 0.5
and detection SD 0.2. Use the original pilot maps and master-selector
receipt. Generate each biological history jointly over 300 sites, then keep
260 training sites. Only the common 120-site network has predator data;
prey observations are masked through day zero. The forty holdout histories
are not written to the analyst package. These six cases form a separate
numerical stratum, not a controlled A-versus-C experiment.

Biological seeds use root 2026110107, namespace 711, stage 1, with map,
effect and process addresses in the frozen manifest. Arrival banks use
SeedSequence([2026110107,711,2,map_index,row]), yielding independent B0 rows
0:131072 and A rows 131072:262144. Generate on the full public geometry,
then align/subset columns by explicit site identifiers. C uses both banks;
small bank smokes use prefixes of these disjoint blocks and are never
substituted for the 131072-row panel banks.

### Fixed-outer integration screen

At the dense free fit, null, generating h and all diagnostic roots, replay
both fitted variance families. Evaluate the positive-family marginal
likelihood with ordinary unnormalised, stratified defensive importance
sampling, and the zero family exactly. The target includes the normalized
Gaussian prior and the same empirical arrival law. This is a fixed-outer
screen: nuisance parameters are held at their Laplace-fit values. It does
not estimate movement of an optimised marginal profile or its roots.

Each qualified latent mode contributes a mixture with weights .80 normal
at inverse-Hessian covariance, .15 normal at four times that covariance,
and .05 Student t with five degrees of freedom and scale matrix .6 times
that covariance. Distinct qualified zero-start and neighbouring warm-start
modes are weighted by Laplace mass; Mahalanobis duplicate tolerance is
1e-8. A replay discrepancy above 0.0001 is a numerical failure, not an
integration correction. This finite start set does not establish that all
latent modes have been found.

Use sixteen independent batches per stream, stratified over mixture
components with their exact mixture weights. Common base random draws
couple locations; component streams nest under draw doubling. A second
independent stream confirms the result. The frozen draw levels are 16384,
32768,65536,131072,262144 per point per stream. Randomness uses SHA256 of
the dataset identity and SeedSequence root 2026110109, namespace 713,
stream/batch/component/variate addresses. Proposal construction is complete
before drawing samples. No proposal adaptation to observed weights occurs.

Retain ESS >=1000, relative ESS >=.01, maximum normalized contribution
<=.01, and pooled raw-weight generalized-Pareto shape k<.5. Fit the largest
min(N/5,3 sqrt(N)) raw weights with SciPy's fixed-zero-location GPD fit;
at least fifty positive tail excesses are required. All batch tail fits
must be available; report their median and maximum separately. Missing or
failed tail diagnostics mean indeterminate, not a pass.

Use independent-batch replication for Monte Carlo uncertainty. The screen
retains paired contrast intervals and uses conservative envelope intervals
for decisions: simultaneous positive-log-integral bounds [L,U] become
[max(L,z),max(U,z)] with exact zero-family value z. Difference bounds then
bound the centred W correction. Bonferroni allocation covers the fitted
locations, two streams and five scheduled looks within a dataset; these
are nominal Monte Carlo intervals, not ecological confidence intervals.
This permits a tied family without claiming a unique owner.

A decision requires contrast uncertainty radius <=.01 in both streams,
weight gates, agreement between streams, and stability on draw doubling
(point estimates within .01 and overlapping intervals). Both streams must
place every correction interval inside [-.10,.10] for a pointwise pass.
A precise correction wholly outside that range in the same direction, or
a confirmed material ownership reversal beyond the 1e-4 tie tolerance,
requires repair. A threshold-straddling or unresolved result remains
indeterminate at the draw cap. Keep individual point estimates and failures.
Complete this screen for every numerically available dataset even if an
earlier case requires repair.

A pointwise pass alone cannot qualify optimised marginal roots. If the
whole pointwise panel supports continuation, a separately reviewed second
stage would reoptimise the importance criterion and resolve its roots,
with independent gradient and root Monte Carlo checks. If the first stage
already denies readiness, report that decision and retain optimised root
movement as unquantified; do not add a costly second stage that cannot
change the readiness decision.

### Paired-arm descriptive summaries

For each biological history report the free sigma and boundary status,
all c=3.84 components, their actual roots and contacts, and the ridge slope.
Where each arm has a single component with two actual roots, define
lower expansion dL = log(lower_A)-log(lower_B) and upper expansion
dU = log(upper_B)-log(upper_A). Missing roots and domain-truncated sets
are categorical, not imputed endpoints. With disconnected sets retain
all components and mark a single expansion contrast unavailable.

Define the ridge slope by uniform-log-h least squares for the piecewise
linear log-sigma profile within the unique diagnostic component. Report it
only when the positive family uniquely owns that whole component and sigma
has no bound contact there. Zero-family, tied, disconnected, truncated or
unresolved cases receive explicit categories, not fabricated log(0).
The depletion prediction is dU>dL and slope_B-slope_A>=0; neither is a
numerical pass criterion. These sixteen paired histories support descriptive
development contrasts only.

## Pre-execution checks and review record

- Independent mask review accepted 45 tests plus 864 likelihood values
  assembled independently from survival and beta-binomial terms; maximum
  absolute discrepancy was 1.82e-12, including extreme log hazards.
- The adapter review found and repaired holdout-payload and source/selector
  identity defects before any selected outcomes were generated or fitted.
- The controller review found and repaired missed-component, unseen-owner
  and final-replay validation defects before execution. Independent replay
  of the adversarial examples and 66 focused tests accepted those repairs;
  subsequent adversarial review also accepted cross-evaluation of both
  searches' family-transition witnesses, switch brackets and tie endpoints.
- The importance core passed Gaussian controls and one-site adaptive
  quadrature checks at h=1,3,30, including the near-zero variance limit.
  An already-used 120-site H3 history took 2.68 seconds for 16384 draws;
  this was a cost smoke, not a new challenge-panel observation.
- Final independent review accepted portable data association and the
  importance-screen decisions/provenance. The integrated local check passed
  335 focused tests; a separate reviewer reran 59 controller/integration tests.
  The detailed design and case identities are now frozen; no panel fitting
  or selected outcome generation preceded this freeze.

Freeze recorded 2026-11-01T22:16:46.792896+11:00.
