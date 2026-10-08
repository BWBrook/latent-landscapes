# Goal 056 calibration-method review

3 October 2026. Independent design and source review within the approved
feasibility study. This record does not authorize a reference campaign or a
sealed capstone history.

## Decision and inferential target

Use a two-stage finite-grid Monte Carlo test for the future effect declaration.
The estimand remains the multiplicative post-arrival prey-loss hazard `h`; the
null is `h=1`. The nuisance is the background coefficient, whole-map mean loss
hazard and population SD of a site-shared prey-detection probability whose mean
is known to be .65. The declaration target is casewise control of false effect
declarations under the exact fitted generator at a public on-grid nuisance.

Prediction remains a separate target: conditional prey log score on the 40
cluster-isolated holdout sites after all fitting choices are locked. The method
does not turn a declaration into an accurate magnitude estimate, a confidence
interval, a model-selection result or a population statement across maps. Four
future sealed histories would supply four case studies; their individual 5%
tests do not confer 5% familywise control for the statement that any case has an
effect.

## Data and likelihood structure

The exact-family data generator has one cohort present at day -60, irreversible
prey loss, background hazard

`mu * exp(beta * A_i) / mean_map(exp(beta * A))`,

and a multiplier `h` after latent predator arrival. Predator arrival is
stochastic and spatially dependent. One Beta-distributed detection probability
is drawn per site and shared across all prey visits. All visits are completed,
false positives are absent, and training and holdout sites belong to disjoint
five-site clusters. Full-data references must retain the correlated spread
generator even though the fitted score sums sitewise marginal likelihoods.
Monte Carlo exchangeability can calibrate that fixed composite statistic; it
does not make the site contributions independent.

For an alive prefix of `n` occasions with two-visit counts `y_j`, let
`Y=sum(y_j)`. With Beta shapes `a,b`, its detection factor is

`I(all later counts are zero) * product(comb(2,y_j)) * B(a+Y,b+2n-Y)/B(a,b)`.

At SD zero this reduces continuously to fixed detection .65. The likelihood
must retain the binomial multiplicities in both branches. During this review,
the first positive-SD implementation omitted those factors while retaining
them at SD zero; that would create a discontinuity and bias dispersion fitting.
The likelihood owner was notified and a zero-limit continuity regression is a
required gate. The Beta mixing law is an observation model, not a prior on the
ecological parameters.

## Scalable finite-grid construction

The public reference grid has 3,645 nodes: 81 beta values from -2 to 2 by .05,
nine means `(.0005,.001,.0016,.002,.0025,.0032,.004,.005,.006)`, and five
detection SDs `(0,.10,.20,.30,.40)`. Actual future truth must be drawn exactly
on this support for the proof below to apply.

For node `nu`, define the pre-invasion screening statistic

`D_nu = 2 * (max_{eta in N(nu)} l_pre(eta) - l_pre(nu))`,

where `N(nu)` contains the node and its immediate predecessor and successor on
each grid axis. Boundary nodes simply have fewer neighbours. This local
likelihood contrast needs at most seven point scores per reference, contains no
arrival integration or effect parameter, and avoids profiling the entire grid
inside every screen reference. Remote local modes can be retained; this costs
compute but cannot invalidate coverage.

Generate exactly 99 independent pre-invasion references at every node. With a
fixed conservative tie tolerance, set

`q_nu = (1 + number(D_ref,nu >= D_obs,nu - tolerance)) / 100`

and `C={nu:q_nu>.01}`. Thus the attainable value `.01` excludes a node and any
tie within tolerance retains it. The screen costs 360,855 pre-only histories
and at most 2,525,985 point likelihood evaluations, instead of a full-grid fit
within every reference history.

The full effect statistic is

`T = 2 * (max_full l - max_h=1 l)`.

Both maxima use the same frozen bounded multistart algorithm for observation and
reference histories. The unrestricted numerical maximum is clamped to be at
least the fitted null maximum, because the scientific parameter domain is
nested even when two numerical optimizer calls are not. Bounds, transforms,
starts, ordering, stopping tolerances, fallback, environment and failure rules
are part of the statistic. Numerical profiling is therefore permissible: the
rank proof requires a fixed exchangeable statistic, not a true maximum or a
chi-square likelihood-ratio law. Optimizer failure may not cause a reference
history to be discarded or redrawn.

At every retained node, generate exactly 999 independent full null references
from a stream disjoint from the screen. Define the inclusive plus-one `p_nu` in
the same way, then

`p_BB = min(1, .01 + max_{nu in C} p_nu)`.

Declare only when `p_BB<=.05`. An empty set, a missing table, a failed required
fit, or a candidate set larger than a cost cap fixed before the sealed data
returns `p=1`. It is invalid to retain only the most convenient subset of `C`.
For four cases, construct one reference table for the union of their eligible
candidate sets and reuse a node table across cases. Each decision remains
casewise.

If the true exact-family nuisance is an on-grid `nu_0`, inclusive Monte Carlo
ranks give

`P(nu_0 not in C)<=.01` and `P(p_nu0<=.04)<=.04`.

Therefore

`P(declare)<=P(nu_0 not in C)+P(p_nu0<=.04)<=.05`.

Independence of screen selection and the effect p-value is unnecessary for this
union bound, although separate public roots simplify review. The guarantee
averages over reference and evaluation generation conditional on the fixed
map, design, bank and numerical algorithm. It is not a conditional guarantee
for each realised reference table.

## Numerical compression and profiling

For a ten-day empirical arrival category, write
`U=(arrival-lower)/10`, `x=10*lambda*(h-1)`. The required transform is

`exp(-x) * sum_k E(U^k) x^k/k!`.

All terms are nonnegative. Truncation after degree `N` has relative bound at
most `exp(x) Pr(Poisson(x)>N)`. With the registered `x<=5` and `N=48`, this is
about `3.3e-29`; floating-point accumulation, not Taylor truncation, will
dominate. The continuous-beta hazard bound must cover the entire parameter box
on the actual public map. A maximum over the 81 diagnostic beta nodes is not a
certificate. The runtime `x<=5` check is a secondary guard.

Because event probabilities subtract successive survival moments, qualification
must compare final site probabilities, whole-history likelihoods and `T` with
the exact K131072 sums. A fixed approximation would still define a rank-valid
statistic if applied symmetrically, but it could not be described as reproducing
the empirical-bank likelihood without this numerical check. Compression does
not establish that K131072 approximates a population arrival law adequately and
must be requalified for a future capstone map and bank.

Fit quality is checked against a fixed, affordable lower bound rather than an
exhaustive product of every profile and nuisance node. The diagnostic lattice
crosses `h=(1,1.5,3,6,10)`, `beta=(-2,-1,0,.6,1,2)`, all nine registered `mu`
nodes and all five registered detection-SD nodes. Its 1,350 direct point scores
per history also contain the `h=1` and `beta=0` slices needed to lower-bound all
four candidate maxima. Every main fit must be at least its applicable lattice
maximum minus `1e-6` log-likelihood units. A larger lattice or conditional-profile
value is a diagnosed optimization failure; it is not substituted into an
observed statistic after inspection. The 181-point h and 81-point beta profiles
provide additional conditional lower bounds under their frozen start policy.
Neither check certifies a global maximum. The Monte Carlo guarantee instead
applies to the resulting algorithm-defined statistic when the same frozen
fitter and failure rules are used for observations and references.

## Alternatives considered

- Full supremum calibration at all 3,645 nodes is simplest but requires about
  3.64 million full histories and fits before evaluation or robustness work.
- A global pre-invasion likelihood-ratio screen has a valid proof but restores
  a grid fit inside every one of the 360,855 screen histories. The local
  neighbour contrast preserves true-node coverage with linear rather than
  quadratic grid cost.
- Plug-in nuisance bootstrap, asymptotic chi-square cutoffs and an ordinary
  fitted likelihood interval are cheaper but do not control the composite null
  at weakly identified or boundary nodes.
- Adaptive reference counts or dropping retained nodes based on interim ranks
  could save work, but require a separate anytime-valid construction. They are
  excluded from this proposal.

## Required evidence before a calibration proposal

1. Zero-SD, six-occasion, known-arrival, day-0 continuity, initial-state,
   predator-marginal and holdout-isolation checks must pass. Shared-Beta
   emissions must match direct small enumeration, including multiplicities and
   the SD-to-zero limit.
2. Compressed transforms must match exact full-bank calculations at domain
   boundaries and fixed interior points for every site/category. Whole-history
   absolute log-score error must not exceed `1e-8`; all event probabilities
   must stay positive and survival monotone.
3. On all sixteen open histories, each main optimizer must not fall more than
   `1e-6` log-likelihood units below its applicable slice of the fixed
   1,350-point diagnostic lattice. It must also not fall below a registered h
   or beta conditional-profile value beyond that tolerance. These are bounded
   lower-bound audits, not global-MLE certificates. Flat, all-zero,
   all-positive, boundary and multimodal fixtures require finite repeatable
   results. The unrestricted statistic must include the null result explicitly.
4. Exhaustive toy tests must reproduce inclusive ranks, the `.01` screen
   boundary, the `.04` effect boundary, ties, empty sets, missing tables,
   over-cap abstention and super-uniform ranks under every designation of a
   small exchangeable dataset. The implemented tests pass these arithmetic
   checks without generating calibration histories.
5. The complete sixteen-history benchmark must finish inside the registered
   four-hour/48-GiB feasibility ceiling and report screen cost, full-fit cost,
   peak memory and worst-case retention. A later cost cap is calculated from
   those measurements with an explicit margin; the feasibility panel cannot
   estimate operating error or typical retention.

## Residual risk and recommendation

The main scientific risks are trade-offs among mean background loss, spatial
coefficient and effect; confusion between persistent low detection and terminal
loss; beta-effect alignment with arrival; boundary maxima; and multiple or flat
profiles. Pre-invasion monitoring supplies information about these directions
but does not guarantee identifiability. Spatial residual fields, off-grid
truths, temporal change, missing visits and a future map remain outside the
exact-family proof. In particular, B100-A stays a labelled misspecification
stress whose declarations have no nominal 5% license.

Proceed with this method as the calibration deliverable for Goal 056, without
constructing the 99/999 reference campaign. A later calibration proposal should
freeze the public seed schedule, measured cost cap and independent null controls
before any sealed draw. Independent scientific and numerical review would
materially change confidence because the rank proof, deterministic optimizer,
compression certificate, failure handling and random-stream separation jointly
determine validity.
