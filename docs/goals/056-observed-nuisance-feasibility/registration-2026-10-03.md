# Goal 056: observed-data nuisance and calendar feasibility

3 October 2026 (Hobart). **Approved study; implementation in preparation.**
This advances Charter Pillar 4 calibration and Pillar 5 capstone preparation,
following the two failures established by Goal 055. The source/implementation
review will freeze this registration before the sixteen-history panel runs.

## Authority and completed outcome

Barry approved the feasibility study with a scalable calibration method as a
required output, four future sealed histories, simple blinding against
accidental exposure, and private-key custody in his password manager. His
decisions were relayed on Correspondence thread 53 as message 846, replying to
Fable's message 843. This authorizes the likelihood implementation, limiting
checks, openly labelled development panel, measured costs, independent review
and a concrete next calibration proposal. Routine resources remain delegated.

Close when the study has produced: a verified observation likelihood; complete
four-model fits and profile diagnostics for the sixteen histories, or a
preserved diagnosed numerical failure; measured component and complete-panel
costs; a defensible scalable calibration algorithm with its validity domain;
and an independently reviewed recommendation for the next scientific decision.
A negative feasibility result is a valid outcome. Do not enlarge the panel or
retune criteria in response to disappointing precision.

No large reference calibration, new capstone landscape/truth/observations,
private key generation, commit, push or publication is included. Goals 049–055
and their numerical evidence remain frozen. New code lives in separate modules.

## Development experiment

Use the existing fixed connected 72-by-84 reference landscape and its public
whole-map standardized exposure covariate A, including the unreachable-cell
ties. Retain the same 160 sampled sites and cluster-isolated 120 training / 40
holdout split. This tests the new likelihood on an understood laboratory map;
it does not qualify the future capstone's new map. Retain known spread speed,
resistance and predator detection .65, mean prey detection .65, two visits per
occasion, zero false positives and the verified K131072/alpha1 empirical
arrival bank. Sitewise integration preserves each predator/prey shared arrival;
it does not remove dependence among sites in the generating spread.

One prey cohort starts present at day -60. Prey occasions are -60,-50,-40,-30,
-20,-10,0,10,20,30,40,50,60; predator occasions remain 10,20,30,40,50,60.
Carry prey loss across day 0 without resetting or selecting observed survivors.
Background hazard is mu exp(beta A_i)/mean_all_map(exp(beta A)). After the
local predator arrival, multiply that hazard by h. One Beta-distributed prey
detection probability per site is shared across every visit; its population
mean is .65 and its SD is estimated. SD zero is the fixed-detection limit.

The **sixteen independent openly labelled histories** cross once:

- h = 1, 3;
- whole-map mean mu = .0016, .0025 per day;
- beta = 0, .60;
- detection SD = 0, .20.

Order cells lexicographically by those four axes. Use NumPy SeedSequence root
2026100301, spawn one child per cell, then separate children for spread, prey
loss, predator visits, site detection and prey visits. Publish the child seeds,
observation identities and latent evaluator truth. These are development
fixtures, not future sealed histories or new operating-rate replicates.

## Likelihood and numerical domain

All four candidates estimate the same unknown mu and detection dispersion:
constant background/free h; adjusted background/free h and beta; constant/h=1;
adjusted/h=1. All fitting uses training observations only. Held-out conditional
prey log scores are calculated afterwards at the fixed fits, with total
40-site nats and nats/site kept distinct. No model selection or refitting uses
the holdout.

Parameter bounds for this feasibility study are h in [1,10], beta in [-2,2],
mu in [.0005,.006]/day and detection SD in [0,.40]. Optimize log h, beta,
log mu and the variance fraction SD squared / .16. The boundary parameterization
avoids a zero derivative with respect to SD at SD=0. Constant and null models
fix beta=0 and h=1 respectively. The fixed bounded multistart algorithm uses
nine domain starts, L-BFGS-B (ftol 1e-12, gtol 1e-9, maxiter 2000, maxls 50),
and bounded Powell fallback when the best L-BFGS-B candidate fails. The reviewed
source fixes starts and fallback tolerances. Prefer a successful candidate
within 1e-8 log likelihood of the best candidate; otherwise retain the failed
status. Persist every fit's status and evaluation count. Evaluate the fitted
null point in the corresponding unrestricted fit, retaining its convergence
qualification.

For each alive prefix, integrate the shared Beta probability analytically using
its joint success/failure moment, retaining binomial multiplicities and rejecting
loss intervals followed by a positive observation. Do not multiply independent
per-visit Beta mixtures. The pre-invasion-only likelihood has no effect or
arrival parameter and supplies a cheap nuisance-fitting path.

To support arbitrary mu without repeatedly traversing the full arrival bank,
the new implementation may compress each ten-day arrival category into moments
of U=(arrival-lower edge)/10, including its existing pseudo-arrival. Evaluate
its transform as exp(-x) times the degree-48 positive Taylor series, where
x=10 lambda_i (h-1). Enforce x<=5. Certify that bound over the continuous beta
domain using interval bounds on the actual whole-map normalizer and sampled
numerators. The relative truncation bound is exp(x) Pr[Poisson(x)>48]. Preserve
the exact empirical kernel as a comparator. This is a new numerical path, not
an adopted replacement for any frozen experiment.

Profiles use the existing 181 h points from 1 to 10 and 81 beta points from -2
to 2, maximizing remaining parameters. Compute h profiles for both free-h
models and a beta profile for the adjusted free-h model. Visit nodes in
ascending order with two deterministic starts: main fit plus a fixed default
at the first node, then the previous successful node plus main fit, removing
duplicates. Report curvature in log h only at a resolved interior maximum.
Profiles are likelihood support, not calibrated confidence intervals.

A separate fixed lattice h={1,1.5,3,6,10}, beta={-2,-1,0,.6,1,2}, all nine
mu nodes below and all five SD nodes provides 1,350 point scores per history.
Its h=1 and beta=0 slices also audit the nested candidates. Each main maximum
must dominate its applicable lattice and converged profile values within
1e-6 log likelihood. Preserve larger discrepancies as numerical failures;
never promote a diagnostic point or feed it back into the main statistic.
This checks a lower bound, not global optimality. The effect statistic is
defined by the fixed numerical algorithm, not a certified global maximum.

## Required checks and forecasts

Before the full panel, verify the zero-SD/six-occasion/cohort-day-0 limit against
the frozen score; shared-site Beta integration against independent small
enumeration; known-arrival recursion; continuity of cohort survival through
day 0; h=1 arrival invariance; predator-marginal invariance; observation-only
interfaces and holdout isolation; normalized hazards; and compressed versus
exact final log likelihoods. Compare the full empirical bank at fixed domain
edges and interior points, including challenging all-zero and all-positive
observation patterns. Require absolute whole-history log-score error <=1e-8
for this numerical comparison. Preserve and diagnose a failure before launch.
Also fit all four models twice to those four fixed mechanical observation
patterns on the training sites. Require finite converged results and repeated
log likelihoods agreeing within 1e-8. These controls are not generated
development histories and do not use any panel seed.

Report numerical statuses, boundaries, parameter estimates/errors, parameter
trade-offs, h and beta profiles, conditional held-out scores and timings for
every cell and candidate. Explicitly report an absent or non-quadratic local
curvature estimate. Fable's forecasts are SE(log h) about .40–.60 at h=3 and
detection-SD absolute error about .03 at true SD .20. Describe the observed
cellwise values and counts inside those ranges; these forecasts are not
acceptance gates. Sixteen histories cannot validate recovery, size, coverage,
power or general identifiability. Pre-invasion visits are not all
known-occupied detection trials because prey may already have been lost.

## Calibration deliverable

The leading candidate is a **pre-invasion-only nuisance screen** followed by
full-data Monte Carlo effect tests at retained nuisance nodes. The reference
domain proposed for costing is beta81 crossed with nine mu values
(.0005,.001,.0016,.002,.0025,.0032,.004,.005,.006) and five SD values
(0,.10,.20,.30,.40): 3,645 nodes. This is a proposed future calibration domain,
not a reference table to construct during this study.

At each node nu, compare its pre-only log likelihood with the largest value
over that node and its immediate neighbours along each grid axis (at most
seven nodes). Use D_nu=2[max(neighbour log likelihood)-log likelihood at nu].
Exactly 99 pre-only references generated at nu give the inclusive plus-one
q=(1+number of reference D values at least observed D)/100. Retain q>.01;
this screen requires no arrival simulation or nuisance optimisation.

At every retained node use exactly 999 independently generated full-null
references, applying the same fixed adjusted numerical effect statistic as to
the observation. Its inclusive plus-one rank is p_nu; use
p_BB=min(1,.01+max_retained(p_nu)) and declare at p_BB<=.05. The fixed
scale-aware tie tolerance can only add exceedances. An empty set, missing
required table, failed fit or cost-cap excess yields p=1 and abstention.
Never select only the cheapest or most favourable retained nodes. Shared
tables over four cases' candidate-set union support casewise statements.

Freeze stage/node/reference seed schedules and the maximum affordable union
size before later sealed data. Lazy generation of retained-node tables is
allowed only from those preassigned streams, with no redrawing or interim
stopping. Cost the cheap screen and expensive effect stage separately, showing
worst-case retention and explicit retention scenarios. Do not claim measured
retention or operating error rates without an authorized calibration experiment.

Distinguish the finite-grid probability argument, numerical implementation
qualification and an empirical operating-rate campaign. Exact-family null
validity is on-grid and averaged over reference/evaluation generation, conditional
on the fixed numerical bank; it does not guarantee each realized reference
table, off-grid truths, residual-field transfer, effect-magnitude accuracy or
confidence coverage. The next proposal must identify sufficient independent
controls and cost broader evaluation separately, before Barry decides the
calibration campaign.

## Execution boundary

Use a new isolated deep-server run directory, with at most 16 workers, one BLAS
thread per worker, 48 GiB and a four-hour ceiling for the first complete panel.
This cap is not a runtime prediction. Qualify code locally and on Linux before
launch. Freeze source, this registration, public inputs and seeds; preserve
logs, exit status and partial output on failure. Never restart a completed phase
or overwrite an earlier attempt. Record complete-workload costs including
bank preparation, generation, all fits, profiles, holdout scoring, serialization
and review. Return compact evidence with source/output identities and one
independent method/result audit before closing the study.
