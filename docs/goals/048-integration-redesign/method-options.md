# Goal 048 integration redesign: method options and recommended validation route

**Status:** methodological recommendation for review. This document does not
accept a replacement integrator, change Goal 046, or authorize an ecological
synthesis or production rerun.

The registered pilot is now complete. Its finite-budget corridor failure and
the next proposed variance diagnosis are recorded in [results.md](results.md)
and [final-review.md](final-review.md). The design below remains the method
rationale and pre-pilot validation plan.

## Decision

Prototype an exact **infection-order Rao--Blackwellized integrator**, with
independently seeded embedded jump chains and no category pseudocount. It
preserves the stochastic spread generator, observation model, site-marginal
composite-likelihood estimand, parameter grids and calibrated support summaries.
Conditional on an infection order, every non-source arrival is a
hypoexponential prefix sum with its proper continuous support. Unobserved Monte
Carlo categories therefore receive model-based probability rather than
arbitrary mass at pseudo-arrival locations.

This is now the strongest feasible first replacement. Retained restricted-grid
full-map smokes propagated one 5,144-phase order in 0.384 seconds for connected
and 0.498 seconds for corridor locally; their compact curves occupied about 3.7
and 4.7 MB. Initial target-host order times were about 2.2 and 4.0 seconds,
supporting the registered 30--55 minute pilot estimates with four workers. A
full-G201 compact curve is estimated from the implemented array dimensions and
mesh construction at about 22 MB; it has not been retained as a measured
full-grid runtime receipt. More importantly, infection order is a coarser
conditioning variable than normalized exponential edge proportions, so it
removes at least as much Monte Carlo variance for every linear category-mass
and survival-moment contribution. This ordering does not guarantee lower
variance after finite-sample logarithms, profiling, calibration ranks or support
endpoints; the complete pipeline still requires the bounded pilot below.

Use the exact infected-set continuous-time Markov chain (CTMC) on small graphs
as the accuracy benchmark. Retain global-Gamma conditioning as a diagnostic
comparator, not as a second primary candidate. Do not promote target-deletion
conditioning, importance sampling, a revised pseudocount or plain QMC without
additional evidence.

## Scientific target and preserved estimand

Goal 046 asks whether spatially balanced sampling changes recovery relative to
access-constrained sampling at equal observation effort across three synthetic
landscape archetypes. Its five declared balanced-minus-access contrasts remain
separate by prey-effect truth and speed-information lane. The map, not a site or
a history, is the replicate for landscape generality. Calibration and
evaluation histories quantify within-map process and observation variation.

The prediction target remains the conditional prey log score at the same 40
cluster-isolated holdout sites, after fitting the same 120 training sites. The
known-speed lane supplies rho; the estimated-speed lane profiles rho. Detection
probabilities, background prey hazard, resistance contrast, survey calendar,
visit count and false-positive assumption remain fixed as in Goal 046.

For a site `s`, let `Y_s` denote its complete predator and prey observation
history and `T_s` its latent predator-arrival time. The fitted quantity is the
site-marginal composite likelihood

```text
CL(rho, h) = product_s integral p(Y_s | T_s=t, h) dF_s(t | rho),
ell(rho, h) = sum_s log integral p(Y_s | T_s=t, h) dF_s(t | rho),
```

where `h` is the post-arrival prey-hazard multiplier. Predator and prey share
the same candidate arrival within a site. Dependence among sites induced by the
shared edge field is omitted from the fitted likelihood. Replacing the
calculation of each exact site marginal therefore preserves the accepted
composite estimand; it does not turn the analysis into a full joint spatial
likelihood or assume that sites are independent in nature.

The downstream inferential objects also remain unchanged: exhaustive H181
effect and G201 rho profiles, locally calibrated rank-239-of-250 likelihood-ratio
cutoffs, parameter-specific support endpoints, coverage and exclusion, and the
five paired sampling contrasts. A new integration method requires fresh
calibration because integration error propagates nonlinearly through logarithms,
profiling, an order statistic and discrete support endpoints.

## Generator, observation process and present failure

For each undirected passable edge `e`, the accepted generator draws

```text
X_e independently from Exponential(rate=1),
w_e = c_e X_e / rho,
T_s(rho) = minimum over source-to-s paths of sum_e w_e.
```

The `c_e` are the accepted habitat and water-neighbour costs. The nine Goal 046
maps have 5,225 passable cells and 10,066--10,094 undirected edges; observed
edge costs range from 0.6471 to 3.2417. Sources, landscape construction and the
edge-cost equation are unchanged.

At surveys on days 10, 20, ..., 60, predator observations depend on which of
the seven arrival intervals contains `T_s`. Prey survival to time `t`, given
arrival `T_s`, background hazard `b=0.002` and multiplier `h`, is

```text
S(t | T_s, h) = exp{-b[min(t,T_s) + h (t-T_s)_+]}.
```

The current integration bank estimates arrival-interval masses and interval-
restricted survival moments empirically. It adds 0.5 to every one of the seven
categories and locates that mass at days 5, 15, ..., 55 and 70. The denominator
is `K + 3.5`. Goal 047 showed that changing this arbitrary weight, while holding
the bank and histories fixed, moves the connected-map balanced-minus-access
mean log-width contrast by 0.01181--0.02027 and changes a support-boundary
classification. The matched-relative-weight comparisons nearly remove that
movement, identifying the finite-sample regularizer as a material driver.

That is not the only problem. In corridor map 2026090812, the two disjoint
K65536 halves differ by 1.84--1.86 likelihood-ratio units at generating
`rho=1` for one shared access history, although the local fitted rho node is
unchanged. The three effect rows share one predator history and are not three
independent failures. Grid refinement passed. Thus a defensible redesign must
remove arbitrary support mass and control rare/tail integration error through
an explicit accuracy reference. Merely fixing the pseudocount fraction, raising
`K`, or choosing the most favourable alpha would not meet that requirement.

## Recommended conditional integrator

The static exponential-edge first-passage process has an equivalent susceptible-
infected CTMC. Let `A_k` be the source set plus the first `k` infected
non-source vertices. At state `A_k`, the total cut rate at rho=1 is

```text
Lambda_k = sum_{e in boundary(A_k)} 1/c_e.
```

The next vertex is selected with probability equal to its incident cut rate
divided by `Lambda_k`. Given the resulting embedded order `O`, the holding
times are independent,

```text
H_k | O ~ Exponential(rate=rho Lambda_k),
T_s | O = sum_{k=0}^{m_s-1} H_k,
```

where `m_s` is the position of site `s` in the order. This equivalence relies
on exponential memorylessness: a cut edge that has not fired retains its
original residual law. It also relies on the accepted undirected edge being
drawn once; replacing it with two directed clocks would be a different
generator.

The order can be sampled directly by successive rate-weighted choices. It is
also determined by the normalized edge direction `P=X/sum(X)`, because a
common positive rescaling changes all arrival times but not their order. Thus
`sigma(O)` is contained in `sigma(P)`. For any square-integrable linear
integrand `Y` used in a category mass or survival moment,

```text
E[Y | O] = E(E[Y | P] | O),
Var(E[Y | O]) <= Var(E[Y | P]) <= Var(Y).
```

This proves per-draw variance dominance over global-Gamma conditioning for the
linear sufficient quantities. It does not prove cost-adjusted dominance or a
variance ordering for the nonlinear profile, cutoff and width outputs.

For one order, arrival distributions for all sites are prefixes of the same
sequential pure-birth process. Propagate its phase probabilities by
uniformization. With `nu=max_k Lambda_k`, the discrete transition from phase
`k` to `k+1` has probability `Lambda_k/nu`, and evolution over duration `d` is
the non-negative Poisson mixture

```text
p(t+d) = sum_n Poisson(n; nu*d) p(t) P^n.
```

For a site infected at position `m_s`, the arrival density is
`Lambda_(m_s-1) p_(m_s-1)(t)`. Use a deterministic physical-time mesh containing
every G201 endpoint `rho * survey_time`, subdivided to width at most 0.25. On
each mesh interval `[a_i,a_i+d_i]`, retain the seven local coefficients

```text
mu_(i,j,s) = integral_0^d_i u^j/j! f_s(a_i+u) du,
j = 0,...,6,
```

plus rho-specific survival at day 60. These quantities are linear in the
conditional arrival law and share one mesh across all orders. Average them with
compensated summation before expanding effects. This is the decisive memory
property. From the exact implemented array shapes, one full-G201 order is
estimated to use about 22 MB of compact coefficients, whereas expanding each
order separately to the rho-by-effect `BridgeIntegration` would approach 4 GB
per order. These are memory-scaling estimates rather than retained full-grid
runtime measurements. Expand H181 only once per averaged bank.

For effect `h`, set `theta=b(h-1)/rho`. On a mesh interval,

```text
integral exp(theta*t) f_s(t) dt
  = exp(theta*a_i) sum_j theta^j mu_(i,j,s) + remainder.
```

Across the full G201/H181 candidate domain, `0 <= theta <= 0.072`: the maximum
uses `rho=0.25`, `h=10` and `b=0.002`. At degree six and mesh width 0.25, the
analytic relative Taylor bound `exp(x) x^7/7!`, with `x=theta*d_i`, is
`1.24e-16`. It tightens to `9.58e-19` for the exact-control domain
`rho>=0.5`, and to `7.45e-21` in the rho=1 connected pilot. The registered
degree-six/width-0.25 versus degree-eight/width-0.125 comparison had a retained
maximum absolute discrepancy of `2.61e-12`. Effects below one would invalidate
the present positive-series argument and are outside H181.

Poisson truncation and Taylor truncation are separate. Record the accumulated
Poisson tail, propagated probability-mass error, a bound on every omitted local
polynomial moment, and a conservative tilted-moment error bound. The
implementation must not rely only on adding extra Poisson terms after a
quantile. Non-negativity makes lost probability observable: category sums and
the final survival must reconcile to one within the declared bound. The
prototype now carries these bounds explicitly.

Source sites are exact atoms in category zero. They must be passed as an
explicit source-node set; a site absent from the sampled order cannot silently
be reclassified as a source. Reachable non-source conditional laws have
positive mathematical mass in every arrival interval, although probabilities
smaller than floating-point range can still be represented as zero for an
individual order. Count those zeros, never floor, clip or renormalize them, and
require every observation-relevant marginal to be positive after orders are
averaged.

The retained connected and corridor smokes each contained 5,144 phases and 278
union sites, including four explicit source atoms. Their restricted meshes had
240 and 300 intervals, and their compact curves occupied about 3.7 and 4.7 MB.
Category sums erred by at most `1.32e-12` in either coarse single-order
calculation. These measurements establish practical feasibility and arithmetic
plausibility on the registered stress grids, not Monte Carlo accuracy for a bank
of orders or a measured full-G201 runtime.

## Exact small-graph accuracy benchmark

Independent exact controls are possible because exponential first-passage
percolation has an infected-set CTMC representation. If `A` is the current set
of infected vertices, the transition adding uninfected vertex `v` has rate

```text
q(A, A union {v}) = rho * sum_{u in A, (u,v) in E} 1/c_uv.
```

This is equivalent to the static exponential-edge generator: each newly
exposed boundary edge starts an exponential clock and the memoryless property
gives the stated race. For a target `v`, retain transient states not containing
`v`. If `Q_v` is their subgenerator, `q_v=-Q_v 1`, and `a` selects the source
state, then

```text
F_v(t) = 1 - a' exp(Q_v t) 1,
G_v(z,t) = integral_0^t exp(z u) a' exp(Q_v u) q_v du.
```

Matrix exponentials, including an augmented-block evaluation of `G_v`, give
category masses and tilted interval moments without Monte Carlo. Enumerating
the embedded infection orders and their hypoexponential holding times provides
a second exact calculation on very small graphs. Agreement between these two
representations checks the reference itself.

The bounded reference implementation in
`src/latent_landscapes/conditional_reference.py` supplies both calculations.
Use at least a line/tree, a two-route diamond, a bottleneck/corridor motif and a
small cyclic lattice, with no more than eight total vertices for the initial
exact suite. Span the observed cost range, near and distant targets,
the survey boundaries, representative rho values including 0.25, 1 and 4, and
effects including 1 and 10. Split cases before inspecting candidate errors:
development cases may diagnose formula and tail failures; held-out graph,
cost/parameter and history combinations are the prospective exact tests.

Keep deterministic arithmetic checks separate from outer Monte Carlo checks.
For a fixed infection order, compare uniformization with a direct
hypoexponential or matrix-exponential calculation. For a small graph, enumerate
all orders with their exact jump probabilities and compare the weighted mixture
with the infected-set CTMC. The `1e-10` ordinary-probability target applies to
these deterministic comparisons. A randomly sampled finite order bank is an
unbiased Monte Carlo approximation to the all-order mixture; its difference
from the CTMC contains sampling error and must be judged by replicated-bank
uncertainty, not by the deterministic `1e-10` threshold.

Compare, in this order:

1. category masses and every restricted survival moment;
2. complete site-history probabilities, including rare early and late
   histories;
3. composite log-likelihood and centred profile values;
4. MLE cells, calibrated cutoffs, support endpoints and widths on small
   synthetic ensembles.

The CTMC calculation is exact only up to matrix-exponential and floating-point
error, which must be bounded by internal agreement and tighter arithmetic on a
subset. Passing a few analytic one-edge or line cases alone is insufficient:
path competition and a bottleneck are the mechanisms relevant to Arc 3.

## Bounded development pilot on the known failures

The first full-landscape likelihood run is a post-selected feasibility and
stress pilot, not prospective accuracy evidence. Its inputs and stopping rules
are frozen in `jump-chain-pilot-registration.md` before any bank likelihood
output is inspected.

Use connected and corridor map 2026090812 only. For each map, sample three
independently seeded banks of 1,024 infection orders and retain each bank's first
256 orders as a nested prefix. Use the registered common physical-time mesh,
degree-six local moments, deterministic batches of 32 and no pseudocount,
floor, clipping or automatic bank extension. Hash the complete seed ledger and
source snapshot before dispatch.

For connected 2026090812, run rho=1 over H181 for the original null histories,
all 250 calibration and 250 evaluation datasets, and both access and balanced
designs. Recompute each design's rank-239 cutoff and the balanced-minus-access
mean log-width contrast. For corridor 2026090812, run the frozen eight-rho local
window over H181 for access evaluation history 0 at effects 1, 3 and 5. Treat
the three effect views as one related stress case because they share one
predator history.

Compare all three equal-K replicate pairs at K256 and K1024, plus each
replicate's nested K256-to-K1024 movement. The original 0.01 log-width and 0.5
LR movement limits remain descriptive advancement gates. They are not accuracy
tolerances and cannot be relaxed after inspection. Any non-finite
observed-history likelihood is a support failure for that configuration; a
corridor maximum on the fixed window boundary is window-inconclusive. A K256 or
K1024 failure rejects that finite budget for advancement. It does not refute
the exact conditioning identity, prove the whole estimator family unusable, or
justify changing the generator or biology.

Before the full pilot, the fixed-order degree-six/width-0.25 calculation was
compared with degree eight/width 0.125 on both maps. The maximum absolute
mass/moment discrepancy was `2.61e-12` for connected and `1.99e-12` for
corridor; category normalization error was at most `1.32e-12`. Relative
discrepancies above `1e-100` were `2.25e-9` and `1.74e-9`, respectively. Both
checks pass the registered absolute `1e-10` rule, while also showing why the
absolute and extreme-tail relative claims must remain distinct. Coarse-order
times were 0.38 and 0.50 seconds locally. The corresponding initial target-host
smokes also passed at about 2.2 and 4.0 seconds per coarse order, projecting
roughly 30--55 minutes for each three-bank pilot with four workers. This fits
the two-hour cap with useful margin. These are deterministic resolution and
runtime checks, not evidence that 1,024 sampled orders are accurate.

The earlier global-Gamma old-prefix support screen remains a diagnostic only.
Across its 56 registered rows, every observed predator-history marginal was
positive and finite; the minimum was `3.90e-22`. Yet each row retained 321--389
zero site-category cells from floating-point underflow in categories unused by
that observed history. This shows that selected likelihoods can remain finite
despite conditional table zeros. It neither qualifies Gamma integration nor
establishes full support for arbitrary histories or survival moments.

Stop the full pilot at two hours or the registered memory/process limits and
preserve partial checkpoints. If it completes, use its timing and replicated
movement only to design a prospective contract. The pilot cannot adopt the
integrator, qualify Goal 046, restart production or support an ecological
claim.

## Prospective validation and accuracy claims

Validation needs two distinct references.

First, the held-out exact CTMC cases test implementation bias and full-support
behavior against a known integral. Predeclare tolerances for masses, moments,
site log probabilities and centred likelihood ratios after measuring only
reference arithmetic error and development-case variability. The likelihood-
scale tolerance must be materially smaller than the downstream Goal 046 gate;
`0.1` LR is a defensible ceiling because it is one fifth of the corridor limit.

Second, full landscapes need a disjoint, higher-budget numerical reference.
Use independently seeded infection-order banks with at least four times the
candidate's total outer orders and enough independent banks to estimate
between-bank variation; four banks is the minimum defensible starting point,
not an automatic guarantee of precision. Freeze the candidate and reference
budgets from pilot timings and variance before drawing prospective seeds. On
the targeted corridor cells, also compare the global-Gamma representation or a
prespecified normalized importance sampler where feasible. Those alternative
representations are useful checks for estimator-specific anomalies, but they
are references only if their own uncertainty meets the same accuracy budget.

Before seeing prospective outputs, require the combined candidate-reference
uncertainty to be no more than:

- 0.002 for the connected balanced-minus-access mean log-width contrast;
- 0.1 LR for the corridor generating-rho comparison; and
- a classification agreement whose uncertainty interval for the relevant
  `LR-cutoff` margin excludes zero.

These are accuracy-allocation limits, not replacements for Goal 046's original
acceptance gates. If the reference cannot meet them within the frozen compute
cap, classify the result as reference-inconclusive. Do not substitute agreement
between two noisy estimates for accuracy.

After the algorithm and budget are frozen, use disjoint order seeds and fresh
calibration/evaluation history seeds. Include both sampling designs, both
speed-information lanes, null and non-null effects, and prospectively chosen
cases from each landscape archetype. Carry the full rank-239 recalibration and
width calculation through every comparison. Report all controls, including
negative or boundary results. Reusing the nine maps tests numerical generality
conditional on those maps; fresh histories do not create new map replication.

A successful Goal 048 validation would qualify the method for a separately
authorized all-nine-map Goal 046 rerun. It would not itself qualify the old
profiles or ecological contrasts. Every map would still need the new method's
frozen all-map numerical assessment, because landscape-specific rare-arrival
behavior is the problem under review.

## Serious alternatives

### Global-Gamma Rao--Blackwellization

For `M` independent unit exponential edge shocks, write `S=sum_e X_e` and
`P=X/S`. Then `S~Gamma(M,1)`, `P` is uniform on the simplex and independent of
`S`. Conditional on `P`, shortest-path homogeneity gives

```text
T_s(rho) = d_s(P) S / rho.
```

Gamma CDFs and exponentially tilted Gamma integrals therefore provide exact
conditional masses and survival moments. This is a valid Rao--Blackwellized
estimator, and replaying old edge draws supplies iid directions without new
Dijkstra solves. It remains useful as a cross-representation diagnostic.

It is not the primary candidate because infection order is a coarser function
of `P` and has the proven per-draw variance advantage for every linear
sufficient quantity. Gamma conditioning leaves high-dimensional direction
variation and shortest-path switching in the outer estimator. Its preliminary
old-prefix screen also produced hundreds of floating-point zero category cells
per row, despite positive selected-history marginals. Log-domain evaluation may
repair representable tail arithmetic, but it cannot remove outer direction
variance. A scrambled simplex construction could improve integration, yet the
effective dimension and non-smooth shortest-path map make the gain an empirical
question requiring independent scrambles and the same full-pipeline validation.

### Leave-one-target incident-edge conditioning

Remove target `v` and its incident edges, compute source-to-neighbour distances
`D_u^(-v)`, and integrate the independent incident exponentials:

```text
P(T_v > t | graph without v)
  = exp{-sum_{u adjacent v} (rho/c_uv) (t-D_u^(-v))_+}.
```

The independence is exact only because every incident edge is removed from the
conditioning graph. Ordinary full-graph neighbour distances are invalid here.
This method integrates path-entry uncertainty local to a target, but requires a
target-deleted shortest-path problem for each site and outer draw unless a
verified replacement-path algorithm is added. It also gives exactly zero
conditional mass below `min_u D_u^(-v)`, so a finite outer sample can still miss
an early category. The cost and support behavior make it unsuitable as the
first production candidate, though it may be useful for selected-site checks.

### Importance sampling

Exponential tilting of a prespecified corridor cut set can increase late-arrival
frequency while retaining the generating model through the exact likelihood
ratio `f(X)/g(X)`. A defensive mixture can cover early and late regimes. This
directly targets rare tails but introduces proposal choice, weight instability,
site dependence and multiple-target tuning. Only normalized densities with
ordinary, non-self-normalized importance estimates preserve the integral
without additional ratio bias. Weight effective sample size, maximum-weight
influence and replicate agreement would be mandatory. It is better reserved
for an independently designed tail reference than used as the initial general
integrator.

### Plain randomized QMC or a revised pseudocount

Scrambled Sobol shocks without conditional Gamma integration retain hard
category indicators and can still produce empty categories. A fixed
pseudocount vanishes asymptotically but remains arbitrary at finite K; scaling
it with K fixes the relative weight by making the regularization persist
asymptotically. A Dirichlet prior would give smoothing an interpretation, but
would change the statistical method and still require prior sensitivity. None
of these choices addresses the observed corridor bank variability by itself.

## Failure modes and stopping recommendation

The redesign leaves the biological generator and observation model fixed, so
it cannot diagnose ecological misspecification, heterogeneous detection,
informative missingness, real-world extrapolation or causal effects of access.
It also retains the composite likelihood's omission of between-site process
dependence. Local calibration remains conditional on known synthetic truths,
fixed maps and a discrete parameter grid.

The main candidate risk is weak information in rare but influential infection
orders. Holding-time variation is integrated out, but path-order variation can
remain heavy-tailed or multimodal, especially in a corridor with competing
bottlenecks. Three banks reveal gross instability but give imprecise variance
estimates. K256 and K1024 share a prefix, so their movement diagnoses
incremental stability rather than independence. Equal-K banks supply the
independent comparison.

Uniformization adds deterministic risks from Poisson truncation, accumulated
mass loss, extreme rate ranges, floating-point underflow in individual-order
tails and Taylor approximation of tilted moments. The explicit mass, local
moment and tilted-error bounds address these risks only within their verified
parameter domain. Source misclassification, disconnected sites, mismatched
order weights and averaging unequal batch sizes are implementation failure
modes that must fail loudly. A higher-budget order bank shares implementation
bias with the candidate, which is why fixed-order phase controls, exhaustive
small-graph mixtures and a targeted alternative representation are required.

Downstream logarithms, rho profiling, discrete MLE ties and the rank-239 cutoff
can amplify small integration changes and produce non-Gaussian output
variation. Rho and prey effect may trade off in weakly informed histories; the
integrator cannot resolve that inferential aliasing. Multiple inspected cells,
maps, seeds or budgets create selection risk unless targets are frozen and all
results reported. Reused maps and histories are retrospective stress cases;
treating order banks or within-map histories as landscape replicates would be
pseudoreplication. Spatial dependence among sites, map-specific
non-stationarity and extrapolation beyond the nine synthetic maps remain
outside the numerical qualification.

Proceed with the registered two-hour jump-chain pilot because the exact
identity, deterministic controls, measured memory use and both map-resolution
smokes support that bounded test. Advance to prospective validation only if the
calculation remains finite without floors, the registered full-pipeline
movements contract, and a higher-budget independent-bank reference can meet the
accuracy allocation. If K1024 fails, report finite-budget failure and use the
observed variance and timing to decide whether one pre-registered larger budget
is scientifically affordable; do not retune seeds, omit a map, reinstate a
pseudocount or relax the old thresholds.

Independent scientific review would materially improve confidence before
freezing the prospective contract and is necessary before any all-nine-map
rerun or inferential adoption. It would not change the current conclusion that
Goal 046 remains numerically unresolved.
