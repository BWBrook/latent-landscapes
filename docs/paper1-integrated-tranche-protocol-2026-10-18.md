# Paper 1: reviewed protocol and numerical development

18 October 2026. Codex consolidation of Correspondence thread 87 through
Claude's messages 2009–2010 and 2037, Codex's replies 2012, 2028 and 2051,
and independent numerical/design review. This is the current
development protocol; the
[first plan](paper1-integrated-tranche-planning-2026-10-18.md) and
[iteration-2 review](paper1-design-model-review-2026-10-18.md) preserve its
development. Claude has accepted the stratum-mean error target and precision
rule. The new fitted effect domain is [1,30], R3 is dropped, and bootstrap
coverage is assessed by truth inclusion without bootstrap endpoint inversion.
The [first numerical development record](paper1-numerical-development-2026-10-18.md)
reports the frailty recheck, prototype repairs and computational checks.
The [profile-engine record](paper1-profile-engine-development-2026-10-18.md)
records the subsequent engine, monitoring geometry and qualification review.
The [31 October direct-evaluator record](paper1-direct-profile-development-2026-10-31.md)
continues numerical qualification with stable empirical-bank scoring and
analytic site derivatives. It preserves the fitted model and records
whole-profile checks separately from bank adequacy and integration accuracy.
Numerical implementation and qualification are under way. The final executable
design must still be frozen and independently reviewed before validation.

## Purpose and authority

**Which combinations of monitoring design and background model permit reliable
inference about invasion effects across landscapes, and can their performance
be forecast before outcomes are observed?**

This is one Paper 1 experiment advancing charter pillars 3 and 4, connected
to the existing spread–resistance–detection–prey recovery ladder and blinded
capstone. It does not replace that wider argument with a standalone frailty
paper. Success includes learning where inference fails and why.

Barry selected the integrated, broader direction in the
[18 October decision](decisions/2ae00028-a20e-431b-bc79-88a10b53cbf1.md).
His direct instruction was: “we have compute to burn, we're not on a time or
compute budget, and I don't want this to be a salami slice.” His updated
standing instructions also say: “Walk through two-way doors and show him
afterwards” and “If running something could answer the question, run it
instead of asking.” Reversible investigation and preparation should proceed.
The original submitted planning/launch boundary remains historical evidence.
The updated repository guidance in commit `5dda09a` routes scientific gates
through independent AI review and authorises coherent commits/pushes to the
existing remote. This continuation advances reversible numerical development
under that guidance. Registered and blinded results stay fixed; new validation
requires a complete, independently reviewed and frozen procedure.

## Prospective gate amendment — 5 November 2026

Claude's proposal 2890 and Codex's independent
[Turn 9 review](paper1-procedure-review-2026-11-05.md) accept empirical
calibration of the specified spatial random-field composite criterion with
Laplace integration. Exact-integral agreement is descriptive approximation
evidence for that future procedure, not a prerequisite to its calibration.
The completed challenge's frozen failures remain unchanged; this is an
explicit post-outcome development amendment. Numerical computation of the
chosen score, complete failure handling and fresh qualification still precede
rule training. Two unresolved searches expose a latent-start consistency issue
requiring a bounded diagnosis before freezing. No new campaign is authorised
by simply changing the integration gate, and no validation data are opened.

## Evidence now established, and its limits

An independent reconstruction and parent replay reproduced Claude's
complete-data calculation for 2,000 archived histories, 500 in each cell:

| Cell | Mean log(h estimate / 3), exposure weights | True relative-background weights | Paired difference, MCSE |
| --- | ---: | ---: | ---: |
| H3 | -0.000259 | -0.000259 | 0, numerical precision |
| B_H3 | -0.141924 | +0.012824 | -0.154748, 0.004107 |
| L3 | -0.017026 | -0.017026 | 0, numerical precision |
| B_L3 | -0.020335 | +0.030716 | -0.051051, 0.004148 |

The estimator is `(D_post/S_post)/(D_pre/S_pre)`, with true arrival/loss times
and weighted time at risk. It supplies the **relative background shape and
estimates a common scale**; it does not remove all nuisance estimation. The
exposure weights use beta=.5 for the exact cells and beta=`.7 sqrt(log 2)` for
B100-A. The unchanged exact-cell estimate follows from cancellation of a
common weight multiplier, so that equality alone is not a code validation.

This establishes that omitting residual heterogeneity is sufficient to produce
attenuation in this complete-data estimator under these histories. Supplying
the correct relative shape removes most of its mean attenuation. Imperfect
detection or latent-arrival integration is not necessary for that result.
It strengthens the risk-set selection explanation without identifying an
additive depletion/alignment decomposition or the causes of every error in
the full fitted procedure. The benchmark retains finite-event error and is
not a mathematical performance ceiling. Compare absolute errors and biases;
do not report a universal “fraction of attainable correction”. It uses hidden
pre-period events and is a mechanism reference, not information available to
the post-only design.

Audit artifacts: `artifacts/paper1_planning_20261018/codex-oracle-rate-ratio-check.{py,csv,json}`.
All site orders and exposure partitions were checked; all 2,000 histories have
finite arrivals and positive event/exposure denominators. Twenty-six histories
have at least one unconstrained ratio outside [1,10]; none was discarded.
The CSV also records the distinct absolute-known-hazard estimator `D_post/S_post`.

Parent replay of Claude's 4,000-field diagnostic also reproduced
`SD(log N)=0.17124053049808413` and
`corr(log N, mean sampled-site G)=0.8634058774840997` at seed 1.
The script and receipt are `claude-normaliser-check.{py,json}` in the same
directory. This confirms dependence of the normaliser on sampled field values;
it does not measure its effect on fitted h. These are post hoc diagnostics,
not new validation data. Goal 062 and the capstone remain closed.

## Shared experimental structure

Use independent open/connected, corridor-dependent and barrier-dominated
maps. Freeze the map distributions, accessibility rules and ecological
admissibility checks before validation. A numerical failure stays in the
denominator; do not replace a difficult map because its fit fails.

Let A be the fixed standardised exposure surface, T a standardised planning
arrival surface orthogonalised against the intercept and A, and G the
independent exponential-covariance Gaussian field, range 10 cells. T must use
map/planning information, never realised validation arrival times. Set

    z(s,kappa) = .7 A + sqrt(.51) [s a T + kappa G]
    lambda_i = mu exp(sqrt(log 2) z_i) / mean_map(exp(sqrt(log 2) z)).

The six backgrounds are:

| Name | Construction | Role |
| --- | --- | --- |
| Constant | lambda=mu | Simplest family |
| Matched exposure | s=0, kappa=0 | Dose-zero anchor, beta=.582788… |
| B100 anchor | s=0, kappa=1 | Shared dose/direction reference |
| Increased heterogeneity | s=0, kappa=sqrt(2) | Double residual log-variance |
| Earlier/later alignment | s=-1 and +1, kappa=1 | Signed mean-surface interventions |

The matched exposure background is not Goal 062's beta=.5 exact cell. Do not
transfer its old reference calibration. Within the directional comparison,
stochastic covariance is fixed, while realised hazard moments and survival
selection can change. Within the dose comparison, residual variance changes
without adding a directional mean. Neither contrast changes only one aspect
of the realised risk set. Report the zero-sign bias, odd contrast
`(b_plus-b_minus)/2`, and even departure `(b_plus+b_minus)/2-b_zero` with
their literal intervention meanings.

Use one global directional amplitude a, chosen using development map geometry
and expected arrival/hazard diagnostics, then frozen. Do not optimise it for
large observed estimator bias. Its numerical value and the construction of T
are qualification outputs that must appear in the final executable design.

Retain mu=.001 and .004/day and the accepted B100 detection anchor: mean prey
detection .65 with persistent site-level SD .2, and predator detection .65.
Null h=1 and positive h=3 are the primary scientific
contrast. Add h=2,4,5,10 to the same crossed experiment to assess interval
coverage and recovery beyond two truths, including the no-effect boundary and
large effects. All new fitted candidates use [1,30], making h=10 an interior
truth. Claims between tested truths remain interpolation claims. The widened
domain requires numerical qualification through h=30 and reporting of upper-bound
contacts. Existing campaigns and exploratory pilot fits retain [1,10].

Pair the background and monitoring comparisons with shared process/observation
streams where meaningful, retaining independent replicate addresses. Always
simulate the full cohort from day -60; do not replace early losses or restart
survivors at release. Truth-assisted complete-data references accompany all
cells. The expanded experiment uses the constrained profile MLE on h in [1,30],
with the common background scale profiled out, rather than deleting zero-event
histories or adding pseudocounts to the rate ratio. A flat profile is reported
as nonidentifiable with its full maximiser set; do not invent a point estimate.
Retain boundary, tied and unavailable outcomes in the denominator. Preserve
the archived unconstrained ratios above as the original diagnostic; do not
rewrite them as results from this new constrained benchmark.
For the new benchmark, compute signed/absolute point error conditional on a
unique MLE, including unique boundary estimates, and state that denominator.
Report flat, tied/non-singleton and unavailable outcomes as unconditional
frequencies. Also report unconditional usable recovery: a unique estimate
within a factor of 1.5; all nonunique/unavailable cases fail that endpoint.
Do not impute midpoints or choose a tied maximiser after seeing truth.

## Monitoring effort and prediction

The agreed primary currency is **prey site-visits conditional on a fixed
predator network**, not equal total field cost.

| Arm | Prey training observations | Prey site-visits |
| --- | --- | ---: |
| A: pre/post | 120 sites, days -60,-50,…,60, two replicates | 3,120 |
| B: masked baseline | Same 120 sites, days 10,…,60, two replicates | 1,440 |
| C: equal effort, more sites | 260 sites, days 10,…,60, two replicates | 3,120 |

A versus C is primary; A versus B diagnoses the extra information in the
baseline. B masks day 0 as well as negative days. The 140 additional sites in
C have missing predator observations, not observed predator absences. The
common predator network, its calendar, and the training/holdout distinction
must be represented explicitly. The 190-site post-only sensitivity uses the
alternative additive predator-plus-prey ledger
`120*(26+12)=190*(12+12)=4,560`; it changes the predator allocation and is a
development-only sensitivity, not another version of the fixed-network claim.
Travel, shared trips and holdout-survey costs are not monetised by either ledger.

The original narrow access frame cannot accommodate the requested training
union on all three pilot archetypes. Following independent geometry review,
the development design instead selects a 300-site master panel jointly: 15
five-site clusters in each of four source-distance strata, with centres at
least eight grid cells apart across all strata. Eligible centres lie within
two Euclidean grid cells of the fixed road/transect network; every satellite
site must be passable and source-reachable. This is a centre-access rule:
satellites can lie farther than two cells from the network.

A seeded random-priority mixed-integer programme selects the master panel.
This is not uniform sampling over feasible panels. Record solver, objective,
input hashes and selected site identities. Independently seeded labels then
reserve two clusters per stratum as the 40 common holdout sites. The remaining
13 clusters per stratum supply C's 260 training sites; an independently seeded
six-cluster subset per stratum supplies the nested 120-site A/B panel and its
fixed predator network. All selection and labels precede biological histories.
Retain every map failure, infeasible geometry and unresolved solver result;
do not replace failed seeds. Broader capacity checks precede design freeze.
The first prespecified 30-map feasibility scan passed on all maps; the seeded
priority selector also passed on the three pilot maps. These checks establish
sampling capacity, not statistical performance or coverage of all possible
geometries.

Score identical post-release prey
observations, conditioning on the same predator observations at prediction
sites. This targets conditional prediction at new sites on the same realised
map. It is neither joint predator–prey prediction nor prediction to a new
latent field. New-map generality is tested by independent maps. Keep final
holdouts out of tuning and model selection; report their sampling frame.

## Common models and numerical qualification

Fit constant, exposure-linked and exposure-plus-spatial-residual backgrounds
to every dataset, each with free h and matching neutral h=1: six main fits.
The prespecified spatial procedure supplies primary effect inference. Report
family ranking and predictive regret separately; choosing the best family
after seeing a holdout does not produce a calibrated effect estimate.
Comparative declaration/coverage claims for the simpler families require their
own frozen calibrations under the same development protocol. An uncalibrated
profile result can be a diagnostic, but cannot inherit the spatial rule's
cutoff or protection claim.

The proposed spatial working criterion integrates a sampled-site GP with
`log lambda=alpha+beta A+u`, exponential range 10 and estimated residual SD.
It retains site-marginal arrival contributions, so it remains a composite
criterion. The 31 October development implementation prepares a differentiable
site evaluator for each outer h and detection-SD value, using positive power
moments within their checked domain and the same empirical-plus-pseudo raw
arrival sum elsewhere. Optimisation of alpha, beta and spatial SD uses
Laplace integration over the latent site effects. The earlier spline grid
remains a numerical comparator; it does not bound the direct evaluator's
latent field. Qualify at both 120 and 260 sites.

Separate two numerical questions. First, qualify computation of the specified
Laplace criterion against tighter optimisation, independent raw site
likelihoods and derivative checks (and refined grids for a spline comparator).
Matching compressed and raw evaluation does not establish arrival-bank
sampling precision; independent-bank sensitivity is a separate requirement.
Second, characterise sensitivity to higher-accuracy integration as a
separate descriptive diagnostic. The 5 November amendment removes exact-integral
agreement as a promotion prerequisite for the specified Laplace procedure.
Fixed-outer checks do not quantify reoptimised root movement; a separately
budgeted reoptimisation may investigate that question, but unresolved reference
precision must remain indeterminate. A successful Laplace computation does not
establish equivalence to the integral. The operational criterion can be
empirically calibrated, with its approximation defined as part of the procedure
rather than described as exact integration.

Use a 600-case development challenge suite, provisionally 360 base cases and
240 enriched difficult cases across the six site-count-by-archetype cells.
Keep their denominators separate. This is a finite challenge suite, not
evidence for 99% agreement in every regime: even zero discordances among 100
independent cases gives a one-sided 95% upper discordance bound of about 2.95%.
At least 299 independent zero-discordance cases would be needed for a 1%
bound in one prespecified regime, before multiple-regime adjustments.

Check profile statistics and complete confidence sets as well as estimates:
component counts, every boundary, contact with h=1 or h=30, and empty, full or
unavailable sets. A 35-point logarithmic h mesh is a starting search. Sweep
in both directions, include the exact variance-zero family at each h, propagate
better branches, and refine peaks and cutoff crossings. Every retained point
must lie below the selected free maximum within 1e-4 criterion units, or force
refitting/failure. The projected gradient tolerance is 1e-3. Assess curve
support using posterior curvature and tail mass, not mode position alone.
For a finite-grid evaluator, unsupported proposals require a recorded grid
expansion and recomputation. Direct scoring removes that grid boundary but
does not certify joint-tail behaviour or Laplace integration accuracy.

For an importance reference, require independent random streams, common draws
across compared profile points, draw doubling and stable confidence-set topology.
Proposed precision targets are paired 95% Monte Carlo half-widths at most .01
for the LR difference and .005 for each log boundary. Report ESS and tail
diagnostics; an insufficiently precise reference is indeterminate. Agreement
targets (99% observed declaration/truth-inclusion agreement, 95th-percentile
absolute LR difference at most .10 and log-boundary difference at most .05)
are descriptive development targets. They do not excuse unresolved tail cases.
Any integration fallback must have a frozen observable trigger, and the entire
hybrid procedure must be calibrated. Development outcomes cannot retrospectively
choose the procedure applied to a validation case.

The difficult cases must
include variance zero, weak information and corridor rare-arrival orderings.
Measure free-intercept versus full-normaliser discrepancies using the exact
generator. Range 5 and 20, plus an explicit iid-lognormal `K=I` candidate, are
prespecified sensitivities. Implement the iid limit directly; do not divide by
a numerical range of zero. Gamma frailty is a different mixing distribution
and cannot stand in for the iid-lognormal comparison. A successful working
approximation supports empirical performance claims; exact generating-family
inclusion requires the normaliser or a demonstrated equivalent joint law.

Qualification must freeze integration, optimisation, parameter bounds, failure
handling, profile searches and score conditioning before validation. Increasing
the arrival bank alone did not solve the historical corridor failure. Numerical
development has no arbitrary one-week deadline. Failure calls for diagnosis,
not removal of an archetype or a new unrecorded estimand.

## Portable inference: agreed calibration target

Use map-population mean false
declaration and noncoverage, separately within every archetype × background ×
mu × monitoring-arm stratum, as the primary calibration targets. Weight maps
equally. Target <=.05 for each; report confidence intervals, the map distribution
and its 90th-percentile error prominently. Do not average away a failing
background or call the tail protected. This keeps the target estimable and
the scientific failure regimes visible. Claude accepted this target and
withdrew the proposed tail-protection rule in message 2010. Map-cells sharing
a map are not independent replicates.

Develop and compare R1 (raw LR >2.71) and R2 (one common empirical declaration
cutoff). Select R2 from a finite development-only cutoff grid, with a
prespecified simplicity tie rule and equal-stratum h=3 power objective subject
to the chosen error constraints. For the agreed mean target, require
development one-sided 95% upper bounds on each stratum error rate to be <=.05,
providing an uncertainty allowance in training. These selected development
bounds are not post-selection guarantees. The grid and its bounds are frozen after
numerical qualification, before rule-training histories. Use map-level
cross-validation to examine development overfitting; only untouched validation
establishes prospective performance. If no useful rule qualifies, report that
failure instead of relaxing the target after seeing outcomes.

Report all registered denominators: null declarations, positive declarations,
signed/absolute log-h error, recovery within a factor of 1.5, coverage, width,
boundary mass and numerical failures. Define harmful confident error as a
nonempty reported interval lying wholly below h/1.5 or above 1.5h; report
empty/unavailable sets separately as failures and count them as noncoverage.
Use maps as independent units for generality claims and retain paired-history
Monte Carlo uncertainty. Development success and validation confidence bounds
must remain distinct; an uncertain error-rate estimate is not proof of control.

The event-dependent R3 cutoff is dropped. R1 versus R2 answers whether an
ordinary cutoff suffices or an empirical correction is needed without adding
another selection layer. No validation-driven expansion of the rule set.

For magnitude, invert the profile statistic over [1,30]. Before rule-training
histories, freeze a finite interval-cutoff grid C_I and choose its smallest
eligible cutoff, requiring development one-sided 95% upper bounds on mean
noncoverage <=.05 in every claimed stratum and truth. Evaluate the h=1 boundary
and all positive truths separately. Use a fixed numerical tie rule; if none qualifies, report that no
candidate interval procedure qualified. Failed/unavailable intervals count
as noncoverage and cannot gain eligibility by being omitted from width
summaries. Record disconnected
sets, boundary contact, truncation and unavailable sets. Calibration at a finite
truth grid supports empirical coverage there, not a uniform nuisance/effect
guarantee. A failed fit counts as noncoverage; an empty/unavailable set cannot
disappear from the denominator. Declaration and interval rules may differ;
report any disagreement between declaring an effect and excluding h=1.

## Same-statistic bootstrap comparison

Retain Claude's proposed audit: two development and three untouched validation
maps per archetype, arm A, 200 histories per background × mu × h=1/3 cell,
at most 999 bootstrap replicates per audited dataset. Map identities and selection
rules are fixed before outcomes; validation audit results cannot retune the
portable rule. This compares calibration methods for the same spatial statistic.

For a test of h=h0, fit nuisance parameters under that constraint, simulate
from the working joint generator, and refit constrained and unrestricted
criteria. Draw fresh spread with the supplied rho=eta=1 and introduction zone,
independently of a sampled-site Gaussian field at the fitted spatial SD and
fixed covariance K. Simulate prey loss from day -60 using fitted alpha/beta
and tested h0; the working model has no map normaliser. Apply persistent Beta
prey detection with mean .65 and fitted SD, predator detection .65, and the
exact monitoring calendar/missingness. Sigma=0 gives the deterministic
background. For declaration, h0=1 even on datasets generated at h=3. Use
`p=(1+count(T_star>=T_observed))/1000`, rejecting at `p<=.05` for a complete
999-replicate sequence. Preserve shared seeds where comparisons permit.

This is a **plug-in parametric-bootstrap comparator**, not nuisance-protected
calibration and not a gold standard. Its own error is measured on these
replicates; special care is needed at spatial variance zero. Correctly
specified working-family performance and robustness under the exact normalised
B100 generator are separate comparisons.

Audit bootstrap coverage by testing h0 at the generating truth. On h=3
histories this requires a separate constrained bootstrap from the h=1
declaration check; at h=1 the test is shared. Truth inclusion is exactly the
coverage event of the corresponding inverted test set. No bootstrap endpoint
inversion is required: report width only for the deployable profile interval.
The bootstrap comparison covers its prespecified h=1/3 subset; the portable
rule is evaluated across all six truths.

Early stopping preserves the complete fixed-cap decision: after t replicates
and S exceedances, its p-value lies in
`[(1+S)/1000, (1+S+999-t)/1000]`. Stop for non-rejection at 50 exceedances;
stop for rejection at 950 non-exceedances. Otherwise continue to 999. This
returns a decision and p-value bounds, not the uncomputed fixed-cap p-value.
It does not make a fitted-nuisance bootstrap statistically exact. Failed fits
are not non-exceedances; apply the frozen numerical repair or report an
unresolved comparator. This computational stopping rule is related to
[Besag and Clifford (1991)](https://doi.org/10.1093/biomet/78.2.301), while its
pathwise equivalence follows directly from the count bounds. An independent
check covered 49,146 small-cap sequences. Actual saved work depends on the
exceedance probability: about 100 replicates at .5, 500 at .1, 942 at .05,
and 950–999 for strong rejections. These are conditional arithmetic results,
not measured bootstrap wall times.
The historical Berger–Boos procedure remains a labelled Goal 062 anchor.

## Map/history precision and forecasts

Start with 10 development maps per archetype, 30 total. This is an initial
development allocation, not proof that a tail rule or flexible forecast is
learnable. Keep the forecast low dimensional, using planning inputs such as
expected pre/post event information, arrival-duration spread and accessibility.
Compare with total-event and archetype-only forecasts. Hidden realised hazards,
losses and arrivals are mechanism diagnostics, not deployment inputs.

For validation, define each primary paired contrast within a map, retaining
within-map Monte Carlo variance v. Estimate between-map variance tau² after
accounting for v. Use its one-sided 90% upper planning
bound, rather than the proposed 80%, and a minimum of 20 validation maps per
archetype. Use the maximum requirement over primary A–C contrasts in false
declarations, h=3 declarations, coverage and mean absolute log-h error, across
the registered backgrounds and mu values; interval coverage includes all six
truths. Target pointwise 95% half-width .05 for these paired contrasts.

Size the primary **absolute** false-declaration and noncoverage rates separately:
target pointwise 95% half-width .01 for each claimed stratum/truth mean, using
its own between-map and within-map variances. Take the maximum map requirement
over absolute rates and paired contrasts. For an absolute error rate, a
one-sided 95% upper bound <=.05 supports the nominal target; a lower bound
>.05 establishes failure; overlap is unresolved. No positive tolerance margin
is silently added. Freeze the map-level interval construction before validation;
handle zero observed events without a zero-width interval. These are pointwise
assessments, not simultaneous protection across all strata. Do not retune a
rule or extend sampling based on observed validation success/failure.

For a paired contrast, choose n iteratively so that

    t(.975,n-1) sqrt[(tau_U² + v_plan)/n] <= .05.

Apply the corresponding .01 target and variance components to absolute rates.

If v is .25 tau², omitting it understates the variance by 25%. The histories
per map-cell must meet both the relative target v <= .25 tau² when meaningful
and absolute paired-contrast MCSE targets .005 for rates and .01 for mean
absolute log error. Absolute calibration-rate MCSE must also be <=.005.
For near-zero tau², use the absolute targets, the minimum
map count, and planning-only SD floors .01 for rates / .02 for log-error
contrasts; do not impose these floors on the reported estimated variance.
Freeze the calculation before validation and use no resource cap. These are
planning rules, not guaranteed realised widths; report achieved uncertainty.
The .05 widths are pointwise, not simultaneous protection of all contrasts.

More histories cannot substitute for missing independent maps. Freeze
forecasts, cutoffs, map counts and history
counts before inspecting any validation outcomes. Any later revised procedure
requires new validation maps; the first test remains reported.

Include the prespecified temporal-background boundary stress in the same paper.
Its trend/shock formula and balanced map subset must be defined before freeze.
It remains a robustness test outside the stationary background family, not
evidence that baseline monitoring alone identifies a causal invasion effect.

## Workload and the measurement still needed

There is no time/compute ceiling. Costs guide implementation and allocation.
The archived Goal 062 benchmark averaged 6.544 seconds for four existing main
fits, excluding profiles, audit, calibration and the proposed spatial model.
Its 466 reference tables sum to 825.734 serial table-hours; its 20.08-hour run
inherited 299 tables. Neither number measures this new method.

At the proposed minimum 90 maps (30 development, 60 validation), using **300
histories only as a costing example**, the six-background, two-mu design gives:

| Workload | h=1/3 only | Six-point h grid |
| --- | ---: | ---: |
| Biological histories | 648,000 | 1,944,000 |
| Datasets, three paired arms | 1,944,000 | 5,832,000 |
| Six main fits per dataset | 11,664,000 | 34,992,000 |
| Four legacy fits, ideal hours at 40 workers | 88.3 | 265.0 |
| Six fits if spatial pair costs 1 / 10 / 50 legacy pairs, hours at 40 workers | 132.5 / 530.1 / 2,296.9 | 397.5 / 1,590.2 / 6,890.8 |

These are arithmetic scenarios, not measured elapsed times. They exclude
profiles, development, sensitivities, temporal stress and bootstrap work.
The precision calculation may require many more than 300 histories or 90 maps.

The proposed bootstrap audit contains
`15 maps * 6 backgrounds * 2 mu * 2 h * 200 = 72,000` original datasets.
At 999 replicates and two spatial fits per replicate, declaration auditing
has a cap of **143,856,000 spatial fits**. Adding truth-inclusion checks at
h0=3 on positive histories raises that cap to **215,784,000**. Bootstrap
interval widths are outside this comparison. For declaration auditing alone,
the no-early-stopping ideal time at 40 workers
is `999 * seconds_per_spatial_fit` hours: a hypothetical one-second fit means
41.6 days, ten seconds means 416.3 days. This is not a measured timing forecast.

The first prototype now runs on two archived 120-site histories, but the
[development report](paper1-numerical-development-2026-10-18.md) records why
its initial optimizer timings did not qualify a cost benchmark.
The numerical qualification must measure complete constrained/free pairs,
profile evaluations, 120/260-site memory and reference-replicate cost on the
intended host. Then choose appropriate parallel resources and update the
end-to-end estimate, including I/O and audit. Any reference pooling or sequential
Monte Carlo shortcut must preserve and qualify the intended comparison; its
failure does not reduce the landscape scope. Do not call this packet fully
costed until the relevant measurements, including sequential work and the
deployable interval profiles, are supplied.

## Paper argument, review and completion

The manuscript should make a single argument through six evidence questions:

1. Where does information about spread, detection and impact arise? Use the
   established recovery ladder, distinguishing earlier and final procedures.
2. How do heterogeneity dose and directional alignment change impact inference?
   Use the paired interventions and complete-data mechanism references.
3. When do pre/post observations beat an equal prey-visit expansion in sites?
4. When does background-model flexibility help, and when does it absorb signal
   or produce confident error? Show all common candidates and predictive regret.
5. What does calibration cost in power and computation, and does reported
   uncertainty perform as claimed on untouched maps?
6. Can planning information forecast useful monitoring, and where do temporal
   stress and the original blind capstone expose its limits?

Write the editor pitch and proposed captions together with the executable
protocol. Every central claim must have a figure, a denominator and an outcome
that could falsify it. Use placeholders and alternative findings until results
exist. After the experiment, exchange specialist and generalist-editor reviews
and rewrite the claims to fit the evidence. Preserve AI system/version roles
and the human–AI decision record for transparent reporting.

The shared calibration target, truth grid, precision rule and bootstrap
comparison are now specified. Remaining numerical items—amplitude, exact
tuning grids, integration tolerances,
temporal stress and measured cost—belong in one implementation/qualification
packet before validation is frozen. They should not become repeated routine
permission requests. No new production fits have been run in this review.

Independent methodological review identified three material omissions that
were repaired here: sizing absolute calibration rates separately from paired
design contrasts; specifying interval-cutoff training; and defining zero-event
and nonunique complete-data estimates and their summaries. The corrected
calibration passages passed focused re-review. Parent checks reproduced the
archived numerical diagnostics and workload arithmetic, and verified local
document links. These checks establish the proposal's coherence and provenance;
they are not numerical qualification of the new spatial procedure.
The verified diagnostic reply and this protocol were sent to Claude in thread
87, messages 2007 and 2008. Claude reviewed them in 2009–2010, and Codex replied
in 2012. The new survivor-conditioned frailty pilot does not establish the
proposed baseline-trap claim: it changes cohort membership using hidden truth
and omits the selection-induced change in the frailty distribution. The central
model-by-design interaction remains a hypothesis. Numerical development now
tests the sampled-GP approximation and has rechecked 4,000 archived complete-data
histories using stored cluster identities and explicit optimiser diagnostics.
The linked development report distinguishes the verified mechanism result
from the still-unqualified observed-data procedure.
