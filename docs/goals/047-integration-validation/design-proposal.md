# Goal 047 integration-validation design proposal

**Status:** prospective design for Barry's separately approved
integration-validation study, 11 September 2026. This proposal does not accept,
repair or synthesize Goal 046. Its four recorded failures remain binding.

## Decision and scope

The study will decide whether the existing pseudocount-regularized Monte Carlo
arrival integration is sufficiently repeatable for a future, separately
registered Goal 046 numerical requalification. It will not decide whether
balanced sampling improves ecological recovery. The numerical experimental
unit is an independently seeded integration bank; maps, histories, effect cases
and the two sampling designs are fixed evaluation conditions, not independent
bank replicates.

The primary numerical targets are:

1. the rank-239 calibrated effect cutoff and the resulting
   balanced-minus-access mean log-width functional at known rho=1; and
2. the effect-profiled rho likelihood in its LR<=10 core and at the generating
   rho, including the previously unstable far tail.

The study is deliberately limited to connected 2026090812 and corridor
2026090812. The former contains the calibrated-width failure and the latter the
rho-tail failure. The two barrier endpoint failures are retained unchanged and
untested here. Even a pass cannot qualify those maps, the other five maps, or
the ecological comparison.

## Why the present evidence is insufficient

The process bank samples stochastic edge-shock realizations and maps them to
latent arrival times at the union of physical sites. The frozen integration
sorts each site's arrivals into seven survey-time categories and adds 0.5
pseudo-observations per category. It then forms effect-dependent survival
moments, converts these with the observed predator and prey histories into site
probabilities, sums their logarithms over sites, profiles over the H181 effect
and G201 rho grids, centres each profile at its own maximum, and finally applies
a rank-239 calibration cutoff to support sets and widths.

Thus bank draws and the pseudocount act before several nonlinear and non-smooth
operations: logarithms, maximization, profile centring, an order statistic and
grid-defined support endpoints. The Goal 046 half-to-combined comparison changed
both the empirical draws and the relative pseudocount weight. A combined LR is
not an average of the half-bank LRs, and a change in a calibrated width cannot
be additively attributed after these transformations. The similar connected
halves and the discrepant corridor tail show functional-specific sensitivity;
they do not identify its cause or establish exact integration bias.

The fitted and generating models, landscape, sampling sites and histories are
identical here, so model misspecification, detection bias, sampling leakage and
spatial pseudoreplication are not candidate explanations for between-bank
movement. Exhaustive fixed-grid evaluation and the completed half-grid checks
also make optimizer failure and local grid aliasing implausible for the observed
Goal 046 failures. Remaining live explanations are bank-realization variation,
pseudocount sensitivity, their propagation through nonlinear profiling and
calibration, and possible systematic finite-bank bias that replicate agreement
alone cannot reveal.

## Frozen factors and independence

The primary method remains the existing alpha=0.5 pseudo-observation per arrival
category. Alpha=0.25 and alpha=1.0 are symmetric half/double sensitivity cases,
not candidate settings from which to choose a winner after inspection. All
three alphas will be computed from the same empirical category counts and
survival sums before likelihood evaluation.

Before any Stage A result is inspected, freeze Goal 047 root seed `2026091147`
and derive separate roots for banks and histories. The master seed for a fresh
bank is the first uint64 state from
`SeedSequence([2026091147, 1, map_code, replicate]).generate_state(1,
dtype=uint64)`, with
map codes connected=1 and corridor=2 and zero-based replicates. The exact
masters are:

| Map | Replicate 0 | Replicate 1 | Replicate 2 |
|---|---:|---:|---:|
| Connected | 3601440426550850330 | 11651118097552831154 | 13290793667067844025 |
| Corridor | 11665640418403590756 | 16187956828646708561 | 17954444234867233391 |

Each master is expanded by the existing nine-root `spawn_seed_manifest`
schedule, and only that manifest's 65,536 bank seeds belong to the replicate.
No fresh bank may share seeds with Goal 046, another map, or another replicate;
none is a prefix, half or antithetic transform of another. Record the full seed
manifests and require disjoint seed sets and distinct bank checksums. A
pre-outcome reconstruction with the existing seed scheduler finds 65,536 unique
seeds in each proposed bank, zero overlap among the six fresh banks and zero
overlap with all nine returned Goal 046 K131072 manifests.

Under the independent history root, use the same construction with branch 2
and no replicate index. The connected history master is
`1583491067288872631`; the corridor history master is
`9521341156732209215`. Expand each through `spawn_seed_manifest` with 250
calibration and 250 evaluation histories, discard its bank branch, and reuse
those exact histories for every fresh bank. The known-rho
null width control uses the onefold truth for both access and balanced designs.
For the corridor tail control, also evaluate the first ten new evaluation
history groups under effects 1, 3 and 5 for the access design. Common random
numbers across the three effects remain part of the accepted simulator, so the
three effect views of one history count as one history group, giving ten tail
controls rather than thirty independent replicates. Calibration and evaluation
streams remain independent. No realized arrival, event, fit or stability result
may select a control history.

The two proposed history manifests contain 2,000 unique process/observation
seeds each (four streams by 500 histories), with zero overlap between maps or
with any of the six fresh-bank streams.

The original connected 250+250 null ensemble and original corridor access
evaluation history 0 are declared retrospective stress cases. Report them
separately from the fresh controls. The corridor's three original effect cases
share one predator history and remain one stress unit.

## Stage A: existing-bank pseudocount screen

Use the immutable connected and corridor K131072 banks already returned by Goal
046, represented as first K65536 half, second K65536 half and their correctly
reconstructed combination. Extract empirical category counts and survival sums
once for each required rho/effect slice, then apply alpha=0.25, 0.5 and 1.0
without regenerating a bank or history.

For the connected map, use rho=1, H181 and the original null 250 calibration
plus 250 evaluation histories for both designs. Recalculate each bank/alpha's
own rank-239 cutoffs, support topology, endpoints, coverage and exclusion counts,
and paired mean log width. Never import a cutoff from another bank or alpha.

For the corridor map, use the original access evaluation history 0 at all three
effect truths, H181 and the already frozen eight rho nodes comprising rho=1 plus
the seven-node window around 1.1019051158766109. Compare raw likelihoods and
separately centred effect-profiled rho likelihoods. A maximum at an edge of the
seven-node window, or at the isolated rho=1 node rather than inside that window,
makes the fixed-window diagnosis inconclusive and stops before Stage B. It is
not evidence of pseudocount sensitivity; do not widen the window after
inspection.

Stage A provides three deliberately distinct contrasts:

- the two K65536 halves at a common alpha compare equal-size bank realizations;
- alphas within one empirical bank isolate pseudocount-weight sensitivity
  conditional on that bank; and
- K65536 alpha=0.25 versus K131072 alpha=0.5, and K65536 alpha=0.5 versus
  K131072 alpha=1.0, preserve the normalized pseudocount fraction exactly when
  K doubles. These matched-weight comparisons remain correlated half-versus-
  combined calculations and do not by themselves estimate exact bias.

First-half alpha=0.5 quantities must reproduce the saved K65536 profiles and
combined alpha=0.5 quantities must reproduce K131072 within 1e-9 absolute error.
The existing pseudocount-corrected combination identity must also be retained.
A technical mismatch stops for repair and supplies no method result.

Apply the decision criteria below to the maximum pairwise movement across the
three alphas within each fixed empirical bank. Any Stage A breach classifies the
current integrator as materially pseudocount-sensitive for a declared Goal 046
functional. Stop Goal 047 with a negative method decision; do not spend new bank
generation to confirm an already disqualifying sensitivity. The separate
fixed-window inconclusive condition above stops without that classification.

## Stage B: prospective equal-K replication

Run Stage B only if every Stage A gate passes. Generate exactly three fresh,
mutually independent K65536 banks for each of the two maps. There is no adaptive
fourth replicate, bank doubling or extension above the existing K131072 ceiling.

For connected, integrate only rho=1 over H181. Evaluate both the retrospective
width stress ensemble and the new 250+250 known-rho null control ensemble, with
bank-specific cutoffs for access and balanced designs.

For corridor, integrate full G201 by fixed-size rho chunks over H181. This is
necessary because a new history's maximum cannot validly be sought only in the
post-selected stress window. Accumulate raw likelihood surfaces for the
retrospective stress and ten prospective control history groups, then profile
only after all chunks are present. Process alpha values sequentially and discard
chunk-level integration arrays after their likelihood contribution is retained;
do not hold three approximately 4 GB full-grid moment objects in memory. Verify
the chunked path against an unchunked tiny-bank calculation before production.
Use the rho=1 chunk additionally to evaluate the corridor's new 250+250 null
width-control ensemble for both designs, with its own cutoff under every
bank/alpha combination.

For every fresh bank, calculate alpha=0.5 first and alpha=0.25/1.0 from the same
sufficient quantities. Histories, grids and controls stay identical across
banks. Save per-bank results; do not pool the three banks into an effective
K196608 reference or report their median as an exact integral.

## Prespecified numerical criteria

The criteria deliberately reuse the conservative Goal 046 scales. For any
quantity below, "movement" is the maximum range over all three fresh banks at
alpha=0.5 for Stage B, or over all three alphas within a bank for the alpha
sensitivity check. Every named stress and control case must pass; averages
cannot compensate for a failure.

For each connected or corridor known-rho null width ensemble:

- each effect cutoff moves by at most 0.5 LR;
- support component and lower/upper boundary classifications are unchanged;
- each finite support endpoint moves by at most one H181 cell (0.05 effect
  multiplier);
- each design's coverage and exclusion count changes by at most one of 250
  evaluation histories, and the balanced-minus-access count contrast changes
  by at most 1/250; and
- the balanced-minus-access mean log-width contrast moves by at most 0.01.

For every corridor stress or prospective tail-control profile:

- the effect MLE moves by at most one H181 cell and the rho MLE by at most two
  G201 cells (absolute log movement 0.027726, allowing numerical rounding);
- effect-profile and rho-profile LR movement is at most 0.5 over the union of
  nodes where either compared profile has LR<=10; and
- direct LR movement at the generating rho=1 is at most 0.5, even when that
  point lies outside the LR<=10 core.

A G201 boundary maximum or non-finite/non-positive likelihood is a failure, not
an invitation to enlarge the grid. The alpha criteria are a robustness screen:
alpha=0.5 remains the primary method even if another alpha looks better. Do not
retune alpha, histories, grids, thresholds or bank seeds after seeing results.

## Decision rule and claims

After technical reproduction has passed, there are only four terminal method
classifications:

1. **Fixed-window inconclusive:** a Stage A corridor maximum occurs at a
   seven-node window edge or at the isolated rho=1 node. Stop without widening
   the post-selected window and without calling the result alpha-sensitive. A
   newly registered full-grid diagnostic would be needed to continue.
2. **Pseudocount-sensitive:** any Stage A alpha-movement gate fails. Reject the current
   integration method for Goal 046 and redesign the regularization or
   integration before further ecological work.
3. **Not operationally repeatable:** Stage A passes but any prospective
   equal-K bank gate or any Stage B alpha gate fails. Reject K65536 under the
   current method. Do not double the bank, add replicates, relax a tolerance or
   select an apparently favourable alpha.
4. **Operationally repeatable in the tested scope:** every Stage A and Stage B
   gate passes. This supports stability at K65536 for the two maps, two
   functionals and declared controls. It permits proposing a separate all-map
   numerical requalification; it does not accept Goal 046 production evidence,
   resolve either barrier failure or establish exact integration accuracy.

The existing K131072 combined bank is a contextual comparator, not a gold
standard: it shares draws with the old halves, has only one stream and is not an
exact integral. No deterministic or independently qualified higher-accuracy
reference is currently available. Consequently, even a complete pass supports
only operational repeatability. A claim about exact bias or convergence would
require a separately reviewed reference method, such as demonstrably accurate
quadrature or a higher-accuracy estimator with synthetic recovery evidence.

## Cost, reproducibility and stopping

The completed split diagnostic took 35.59 minutes and 3.05 GiB peak RSS for its
two reduced maps. Stage A adds two cheap alpha reweightings after each empirical
sufficient-quantity calculation and should remain approximately 45--60 minutes.

Under the previous nine-map load, a K65536 bank required 7,537 seconds on the
connected map and 7,787 seconds on the corridor map to generate. Full G201/H181
integration required 16,521 and 17,448 seconds respectively. A fresh full
corridor replicate therefore has about 7.0--7.8 hours of measured-cost analogue;
the connected replicate avoids 200 of 201 rho slices and should be dominated by
about 2.1 hours of bank generation plus history work. With the three corridor
and three connected jobs run concurrently within the previously used resource
envelope, Stage B should take about 7--8 elapsed hours and approximately 31
map-hours. These are planning estimates, not new compute authority.

Any execution plan should cap Stage B at six jobs, four workers per job, native
library threads one, 10 GiB address space per process, 96 GiB aggregate memory
and ten elapsed hours including serialization and checks. Use fresh output directories, atomic completion
markers, per-stage input/output hashes and restart only incomplete map-replicate
units. Chunked corridor integration is the failure-recovery boundary. Preserve
raw banks, seed manifests, empirical sufficient quantities and reduced
likelihood arrays so every profile and decision statistic can be reconstructed.

No ecological synthesis, production restart, external publication, commit or
push belongs to this study. Independent scientific review before Stage A and
again at the terminal decision would materially improve confidence because the
acceptance contract controls whether a major Paper 1 pillar can proceed. It
would not turn operational repeatability into exact-accuracy evidence.
