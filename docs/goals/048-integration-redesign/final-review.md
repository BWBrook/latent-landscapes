# Independent terminal review of the jump-chain pilot

12 September 2026. This review reconstructs the registered summaries from the
returned raw likelihood arrays. It was conducted independently of the pilot
comparison code and then reconciled with the completed provenance and numerical
checks.

## Verdict

**The registered finite-budget configuration fails and must not be adopted.**
The connected-map result is nearly stable at K1024, but the corridor stress
case is not: none of its nine registered bank or prefix comparisons passes, and
all 27 truth-specific views fail both the generating-rho and rho-core LR
movement limits. K1024 does not show a reliable reduction in between-bank
variation. A blind bank increase, prospective campaign, or ecological
interpretation is therefore unsupported.

This failure is evidence about Monte Carlo integration over infection orders at
K256/K1024. It does not invalidate the exact conditional jump-chain identity,
the conditional holding-time calculation, the biological generator, or the
observation model. The conditional engine has passed the registered exact
controls and smoke cases, and should be retained as a supported prototype while
the outer order estimator is diagnosed. These checks do not provide a universal
relative-error qualification for extreme tails.

## Scientific target and reconstruction

The fixed prediction target is the site-marginal probability of the paired
predator/prey survey outcome under the accepted synthetic SI generator and
observation model. The inferential summaries under review are (i) connected-map
calibration cutoffs, interval widths, coverage and exclusions, and (ii)
corridor-map profile-likelihood behaviour over the registered rho window and
H181 effect grid. The ecological estimands, survey designs, histories, rho
window, effect grid, background hazard, detection probability and site-marginal
composite-likelihood convention were fixed before execution.

The data-generating and computational chain is:

1. an infection order is sampled from the SI jump chain;
2. independent exponential holding times are integrated conditional on that
   order on the registered physical-time mesh;
3. conditional site/category masses and survival moments are averaged in
   linear space across orders;
4. the observation model maps those means to observed-history probabilities;
5. site log probabilities are summed to the composite log likelihood; and
6. nonlinear profiling, LR contrasts, calibrated cutoffs and interval summaries
   are computed.

This identifies the remaining random approximation as the outer infection-order
average. Conditional arithmetic error can propagate through logarithms and
profiles, but the checks below put it many orders of magnitude below the
observed corridor movement. The registered corridor views reuse one predator
history with three prey-effect truths; they probe different likelihood slices
but are not three independent histories. Inference is therefore limited to a
retrospective stress diagnosis on the two named maps.

## Independent recomputation

I loaded the raw returned likelihood arrays and recalculated every registered
summary without importing or calling the official comparison functions. For
connected calibration, I sorted each null LR sample and selected the frozen
rank-239 cutoff. For each validation history and design, I formed

\[
LR_h(e)=2\{\max_{e'}\ell_h(e')-\ell_h(e)\},
\]

then reconstructed accepted grid cells, connected components, boundary contact,
coverage, exclusion and log-width summaries. For corridor, I independently
formed the two-dimensional maximum, the profile over effect and rho, the LR at
generating rho, the registered core-window LR vectors and grid-index movements.

The independently calculated scalars and pass/fail classifications match
`returned/pilot-comparisons.json` exactly: maximum absolute scalar difference
zero and no classification mismatch.

### Connected map

Only four of nine comparisons pass. All three equal-bank K1024 comparisons
pass; all three equal-bank K256 comparisons and two of three nested-prefix
comparisons fail solely because one or two interval lower-boundary flags change.
No comparison changes component count. Every cutoff movement is at most
0.07019 LR units, every mean log-width-contrast movement is at most 0.008439,
and endpoint movement is at most one grid cell.

| Bank | Access cutoff | Balanced cutoff | Access coverage | Balanced coverage | Width contrast |
|---|---:|---:|---:|---:|---:|
| rep0 K256 | 2.034990 | 2.534413 | 229/250 | 233/250 | 0.091580 |
| rep1 K256 | 2.035350 | 2.464232 | 229/250 | 232/250 | 0.083775 |
| rep2 K256 | 2.005165 | 2.504213 | 229/250 | 233/250 | 0.092214 |
| rep0 K1024 | 2.016528 | 2.528226 | 229/250 | 232/250 | 0.093512 |
| rep1 K1024 | 2.013669 | 2.503597 | 229/250 | 232/250 | 0.091777 |
| rep2 K1024 | 2.030452 | 2.496473 | 229/250 | 232/250 | 0.088521 |

The only boundary-sensitive histories are balanced-design validation histories
6 and 189 at effect 1; all K1024 banks exclude both consistently. Thus the
connected case supports practical stability at K1024 for these histories, but
cannot rescue a configuration that fails its prespecified corridor stress case.

### Corridor map

All nine pair-level comparisons fail and all 27 truth-specific comparisons fail.
The stable features are the effect profile and the location of the maximum:
effect-MLE movement is at most one H181 cell, log-rho-MLE movement is at most
0.013863, and effect-core LR movement is at most 0.2274. The failed quantities
are the generating-rho LR and rho-core profile shape.

| Comparison class | Truth views | Generating-rho LR movement | Rho-core LR movement | Passing views |
|---|---:|---:|---:|---:|
| Equal-bank K256 | 9 | 0.5811-2.2310 | 1.1274-2.4234 | 0 |
| Equal-bank K1024 | 9 | 0.9604-7.7774 | 1.4231-3.2048 | 0 |
| K256-to-K1024 prefix | 9 | 0.7377-7.6096 | 0.5864-2.6776 | 0 |

The fitted rho is always an interior grid point (index 3 or 4; rho 1.0867 or
1.1019), so the fixed window does not make the result inconclusive. Across all
banks and truths, the LR at generating rho ranges from 32.9352 to 41.7675.
The largest K1024 discrepancy is rep1 versus rep2: 7.2824, 7.2103 and 7.7774 LR
units for truths 1, 3 and 5. The worse K1024 spread and only three independent
banks do not support a 1/sqrt(K) extrapolation or a defensible larger-K budget.

## Arithmetic, provenance and failure diagnosis

The evidence strongly separates outer-order Monte Carlo variation from
conditional arithmetic failure:

- every observed-history likelihood and every registered support status is
  finite; there are no observed-history support failures;
- degree-6/width-0.25 versus degree-8/width-0.125 smoke differences are
  2.849e-12 for connected and 1.908e-12 for corridor, both below 1e-10;
- category-sum error is at most 1.382e-12 for connected and 8.877e-13 for
  corridor; final probability-mass error is at most 4.722e-12 and 2.302e-12;
- the largest reported accumulated tilted-uniformization bound is 9.587e-12
  for connected and 4.407e-11 for corridor;
- 78 independent compact-curve-to-likelihood replays agree within 6.822e-13;
  the targeted implementation suite passes; and
- the completion audit verifies 83 preflight files, 27 returned receipt hashes,
  all 6144 registered seeds, 64 staged source files against the executed
  snapshot, 60 accepted source files unchanged, and absence of the recorded
  process groups after completion. Peak aggregate RSS was 1,939,396 KiB and the
  two map jobs completed within the registered two-hour envelope.

There are hundreds to thousands of category entries reported as numerical zero
(370-408 for connected and 3465-3720 for corridor, depending on bank). These
are not structurally unvisited categories: for every non-source order, the
hypoexponential holding-time model gives strictly positive mathematical mass in
every finite category. The zeros therefore arise from finite Poisson truncation
or floating-point underflow. The registered observed histories retain finite
support, but the zero counts preclude a universal relative-tail qualification
for other histories.

A site decomposition of the largest K1024 contrast localizes the signal rather
than showing a uniform numerical offset. For rep1 versus rep2, six corridor-tail
sites (`cell_17_69`, `cell_17_67`, `cell_16_76`, `cell_16_78`, `cell_16_74`,
`cell_14_76`) account for net LR differences of 6.329, 6.304 and 6.911 across
the three truths: 86.9%, 87.4% and 88.9% of the total discrepancies. At
`cell_17_69`, the predator marginal at generating rho changes from 8.365e-5 to
3.758e-5; at `cell_17_67`, it changes from 6.290e-4 to 2.317e-4. The associated
joint probabilities are about 1e-8 to above 1e-6, far above the roughly 4e-11
registered accumulated tilted-uniformization/truncation bound. That bound does
not cover total floating-point error, so this comparison supports a scale
diagnosis rather than a rigorous error enclosure.

The most plausible diagnosis is weak sampling of influential infection-order
modes at a small set of corridor-tail sites, amplified by the log transform and
rho profiling. Diffuse order variance and a mixture of rare-mode and nonlinear
amplification remain viable. A shared implementation bias cannot be ruled out
by replicate agreement alone, but it does not explain the between-bank pattern;
the exact controls, mesh refinement and curve replays make floating-point or
conditional-integration error implausible at the observed scale. The pilot has
no basis for assessing full-map accuracy, spatial generality, calibrated
coverage, model-selection uncertainty or ecological adequacy.

## Recommendation and discriminating next evidence

Do not adopt this K256/K1024 estimator, launch prospective all-map validation,
or increase K without a variance diagnosis. Retain the conditional holding-time
prototype and pre-register one bounded replay of the existing corridor
order seeds. Accumulate per-order, or deterministic 32-order-batch, linear
sufficient statistics for the six dominant sites together with path/bottleneck
and order-class indicators. Examine batch influence, effective sample size,
tail concentration, convergence of linear probabilities before logarithms, and
the propagation from site probabilities to the rho profile.

That replay would discriminate among the serious remedies:

- a few rare, high-influence order classes favour stratification, conditional
  allocation or defensible importance sampling;
- diffuse high variance with approximately regular batch behaviour may justify
  a larger independently replicated K after a precision calculation;
- strong correlation with inexpensive order/path summaries favours control
  variates or Rao-Blackwellization over further brute-force sampling; and
- stability in linear site probabilities but instability after log/profile
  transformations requires a precision contract on likelihood summaries and
  possibly direct allocation to their influential sites and rho contrasts.

No new bank is needed for this first discrimination step. Any redesigned outer
estimator then requires independent synthetic recovery and prospective
validation before scientific adoption. Another independent review of the
current returned arrays is unlikely to change the stop-and-diagnose decision.
Independent scientific review would materially improve confidence only after a
specific variance-reduction design and validation contract exist, and remains
required before adoption or a changed inferential claim.
