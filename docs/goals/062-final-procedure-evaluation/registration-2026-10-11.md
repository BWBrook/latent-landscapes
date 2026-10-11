# Goal 062: prospective six-cell evaluation of the final procedure

11 October 2026 (Hobart). **Proposed design; launch not authorized.** Barry
requested the prospective design and compute estimate for six cells with 500
histories per cell, and independent review before launch. This preparation
advances Charter Pillar 4 and the paper-level recovery/power decision identified
in the [Paper 1 synthesis](../../paper1-evidence-synthesis-2026-10-11.md).

The [compute estimate](compute-estimate.md) and
[independent review](design-review-2026-10-11.md) accompany this proposal.
Approval would authorize implementation and qualification of a new panel
adapter, followed by the bounded campaign and its independent audit. This
document alone authorizes none of those production steps.

## Question and endpoint

How often does the frozen observed-nuisance procedure declare a real effect,
abstain or estimate its magnitude accurately at two background-loss regimes,
and what is its corresponding null declaration rate and held-out predictive
performance?

The endpoint is a reviewed six-cell operating-performance report, including
negative results. This is a prospective known-truth evaluation, not a second
blinded capstone. The four original capstone histories and all earlier results
remain unchanged.

The estimands are probabilities and estimation/score distributions over fresh
complete histories **conditional on the fixed map, design, numerical bank,
algorithm and one realised screening/effect-reference panel**. They do not
average over reference-table generation, maps or nuisance regimes. Effect-
magnitude confidence coverage, off-grid or B100-A robustness, general model
discrimination and simultaneous spread–effect inference are excluded.

## Six fixed cells

Use the exact background family in every cell:
`lambda_i = mu exp(beta A_i) / mean_all(exp(beta A))`.

| Cell index / label | h | mu per day | beta | Persistent prey-detection SD | Evaluation histories |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 / L1 | 1 | .001 | .50 | .20 | 500 |
| 1 / L3 | 3 | .001 | .50 | .20 | 500 |
| 2 / L5 | 5 | .001 | .50 | .20 | 500 |
| 3 / H1 | 1 | .004 | .50 | .20 | 500 |
| 4 / H3 | 3 | .004 | .50 | .20 | 500 |
| 5 / H5 | 5 | .004 | .50 | .20 | 500 |

All nuisance values lie on the existing 765-node grid; the two true nuisance
nodes are **457 and 482** in its beta-major ordering. The mu values are the
endpoints of the capstone's public generating support. Beta=.50 and SD=.20
are interior values, held fixed to isolate the background-rate contrast. The
homogeneous reference risks over 60 days are 5.82% and 21.34%; actual spatially
heterogeneous risks differ. Call these lower/higher background-loss regimes,
not lower/higher information: more background loss can also deplete the prey
available to reveal a post-arrival effect.

These anchors are selected from scientific design considerations after the
earlier programme's results, before any Goal 062 history, and not by screening
new outcomes or optimizing calibration reuse. Two anchors do not map a general
nuisance surface. The constant-background candidates are working-model
comparators; neither generating cell has beta=0.

## Fixed environment, observations and fit

Retain the accepted Goal 060 connected map, public exposure and 160-site access
design: 120 training sites in 24 five-site clusters, 40 holdout sites in eight
separate clusters, the original four strata and canonical site ordering.
Whole-map hazard normalization uses all 6,048 cells. Reuse the K=131,072
arrival bank, seven alpha=1 pseudo-arrivals and degree-48 compression.
Do not search for or regenerate a map, split or integration bank.

Retain a prey cohort from day -60, two prey visits at each of thirteen dates
-60,-50,...,60, and two predator visits at days 10,...,60. The day-zero prey
survey precedes predator introduction. Carry prey loss continuously through
day zero. Mean prey detection and predator detection are supplied as .65;
rho=eta=1 remain supplied. Each history has its own full correlated spread,
prey-loss thresholds, persistent site-level Beta detection draws and conditional
visit draws. There are no false positives, missing visits, recolonization or
selection of observed survivors.

Fit all four candidates to the same training observations: constant/free h,
adjusted/free h, constant/h=1 and adjusted/h=1. Estimate mu and detection SD
in each; estimate beta only in adjusted candidates. Use unchanged bounds
h=[1,10], beta=[-2,2], mu=[.0005,.006], SD=[0,.4], transformations, nine starts,
optimizer controls, tie rule, fallback and explicit null nesting. Truth must
never supply a start, nuisance value, calibration node or model choice.
The adjusted free/null pair alone supplies the calibrated declaration.

Generate all 160 sites, fit/screen using only the 120 training sites, persist
and freeze the main fits and declarations, then score the fixed fits on the
40 holdout sites. Use the existing conditional-prey scoring rule, with holdout
predator observations as conditioning inputs and prey observations only for
scoring. Store all four total, site and cluster contributions and all six
pairwise contrasts. Prediction never refits or selects the primary model.

## Randomness, replication and prospective freeze

Use **3,000 independent complete histories**, independent across cells as well
as within cells. The models within one history are paired on its observations;
the same replicate number in different cells does not denote a paired block.
This targets precise cellwise rates, at a cost to precision of between-cell
contrasts compared with common random numbers.

Evaluation root **2026101101**, namespace **62**, domain **1** uses addresses
`[root,62,1,cell,replicate,stage]`, cell=0..5 in the table order and
replicate=0..499. The stage IDs remain spread=1, prey_loss=2,
predator_visits=3, site_detection=4, prey_visits=5. Emit the first uint64 from
NumPy `SeedSequence(address).generate_state(1,dtype=uint64)` and use
`default_rng`/PCG64 as in the existing exact generator. This root is distinct
from the public fixtures, bank and reference roots. No private root or sealed
history is reused. Mechanical qualification uses root **987654321** only.

Before any production draw, freeze this registration, the cell table, all
15,000 evaluation stage addresses/seeds, source/runtime bindings, diagnostic
subset and reporting rules. Check seed-ledger uniqueness and separation of
address domains. No Goal 062 root preview, replacement history, extra replicate,
seed retry or truth-dependent fitting input is permitted. Preserve every
generated observation and failed result at its original address.

This is prospective relative to the new histories, not a claim that the
method, anchors or expectations were devised without earlier evidence.

## Reference panel and calibrated decisions

**Complete the full fixed reference grid before evaluation.** Reuse
the independently audited 75,735 screening references and 299 effect tables
from Goal 061 after checking their hashes and compatibility. Generate the
remaining **466×999 = 465,534** effect references at the original frozen
addresses, yielding **765×999 = 764,235** effect rows. Audit all new tables
before starting evaluation histories. This deliberately pays for a complete
panel whether or not every node will be used; it simplifies the conditional
estimand and gives a definite maximum workload. It is not additional
evaluation replication or evidence of robustness across the grid.
This proposal binds the full-grid path. Switching to selective materialization
requires a revised prospective registration and independent review before any
production draw; it is not a runtime cost-saving option.

The reference contract is unchanged: root **2026100404**, namespace **59**,
screen/effect domains **5/6**, their original stages, 99 screen references
and 999 effect references per node. No old Goal 058 pilot table is pooled.
The new panel wrapper gets its own source manifest while retaining an explicit
compatibility link to the original scientific source and reference receipts;
never relabel or overwrite an old receipt to make it appear newly generated.

Compute each observed 765-node pre-only score surface and the immediate-axis
discrepancies. Use conservative inclusive plus-one ranks with the frozen
tolerance, and retain `C={node:q>.01}`. For each retained node,
`p_nu=(1 + count(reference T >= observed T - tolerance))/1000`, where
`T=max(0,2(ell_adjusted_free-ell_adjusted_null))` and the tolerance is
`1e-10 + 1e-12 max(1,abs(observed T))`. Set
`p_BB=min(1,.01+max_C p_nu)`; declare iff `p_BB<=.05` with valid required
inputs. Reuse the established screen tie semantics as well.

Invalid/nonfinite observed screening, an empty C, an invalid adjusted pair or
an invalid required table causes the established casewise abstention. The
adjusted pair must have finite scores, both fits converged and free-minus-null
at least -1e-6; clamping T cannot rescue a failed pair. A failed row makes its
whole 999-row table unusable. Retain it; do not drop rows, replace seeds or use
partial ranks. An unavailable shared screen makes all cases abstain. Ordinary
hardware interruption leaves computation pending, not a final abstention.
Completed and independently verified numerical failures remain part of the
operating procedure. Scorer/schema/source defects require diagnosis and repair
before results can be released.

Under the original exact-family/on-grid null construction the casewise error
bound averages over observations and reference generation. This experiment
estimates performance conditional on one reference realization. Its null
rates can diagnose that realization; they neither validate nor refute the
marginal theorem, and they are not family-wise guarantees across cells.

## Prespecified outcomes and uncertainty

Every scheduled history ends as declaration, valid non-declaration or
abstention once all work and defect diagnosis are complete. Report these counts
and probabilities with **denominator 500 in every cell**.

Primary scientific outputs are:

1. Declaration probability: false declaration at h=1; operational sensitivity
   at h=3 and 5, always displayed beside the matched null rate.
2. Abstention probability, with observed-fit, observed-screen and shared-table
   reasons separately recorded. Shared-table failures are common causes,
   not hundreds of independent numerical incidents.
3. Adjusted-free effect recovery: all-history proportion with a valid estimate
   and `abs(log(h_hat/h)) < log(1.5)`, plus separate proportions with a valid
   estimate at least 1.5-fold wrong and with an unavailable estimate. These
   three categories partition all 500 histories. An invalid declaration pair
   does not automatically make an otherwise valid free-h estimate unavailable;
   store both statuses explicitly.
4. Mean total held-out score contrasts for adjusted-free versus constant-free
   and adjusted-free versus adjusted-null, using only paired valid scores and
   explicitly reporting how many pairs are unavailable out of 500.

A valid point estimate requires a converged free-h fit, finite h within the
frozen bounds, a finite main score and passing independent score reconstruction.
A scorer/source defect is a release hold requiring repair, not an ecological
failure to hide in the unavailable category.

Also report signed log bias, mean/median absolute log error, the .05, .25, .50,
.75 and .95 quantiles of absolute log error, and boundary masses among valid
free-h estimates, with their denominator. Do not
assign zero error to invalid fits. Show recovery among declarations separately
as a selection diagnostic. Report mu/beta/SD errors and boundary contacts,
true-node screening retention, C sizes, p_BB distributions, numerical warnings,
and all candidate scores as secondary diagnostics. No profile is a confidence
interval and no profile-coverage calculation is specified.

Use pointwise 95% Wilson Monte Carlo intervals for proportions. For means,
medians, error and score contrasts use **2,000 whole-history bootstrap draws
within each cell**, keeping all four models and missingness indicators together.
Resample the original 500 IDs, then apply each endpoint's validity condition;
retain the original-sample statistic as the point estimate. Use two-sided 95%
percentile intervals from the .025 and .975 bootstrap quantiles. Use NumPy
`quantile(method="linear")` (Type 7) for both bootstrap and reported empirical
quantiles. If fewer than two valid observations support an endpoint, or any
bootstrap statistic is undefined, its interval is unavailable; report the
undefined-draw count without discarding draws or assigning zero. This rule
does not change the Wilson intervals for proportions over all 500 histories.
Bootstrap root
**2026101102**, namespace 62, domain 2, address `[root,62,2,cell,draw]` generates
500 replacement indices with PCG64. For between-cell contrasts, combine the
independently resampled cells at the same draw index; do not pair histories
across cells or resample individual sites/clusters. No new reference tables
are drawn or bootstrapped for these conditional intervals.

At n=500 the approximate 95% half-width is 4.4 percentage points at probability
.5, 3.5 points at .8, and 1.9 points at .05. A difference between independent
cell rates has worst-case half-width about 6.2 points. With zero observed events,
the two-sided Wilson upper bound is about .76%, not zero. These are Monte Carlo
precision statements, not a power calculation for detecting an ecological h.
The design is not intended to establish small differences or equivalence.

Keep all six cells visible. Between-cell comparisons and the remaining model
contrasts are descriptive secondary results with pointwise intervals; do not
turn them into a family of significance discoveries or pool cells into a new
weighted power estimate.

## Numerical checks and diagnostic budget

Check every one of the 12,000 main model fits for finite/status/boundary/start
records, score replay and nesting. Independently reconstruct all stored main
scores, adjusted statistics, screening ranks, declarations and held-out
scores. Replay the full generator at all 3,000 evaluation addresses; do not
claim independence of the shared spread kernel itself.

Preselect **replicates 0–4 in each cell** for three full-bank profiles
(constant h181, adjusted h181, adjusted beta81) and the 1,350-point lower-bound
lattice: **30 histories, 13,290 profile points and 40,500 lattice points**.
Persist main fits first; diagnostics never seed or replace them. Independently
score these points, using the existing 1e-8 score and 1e-6 nesting/main-gap
tolerances. The subset characterizes examples of support geometry and checks
the algorithm; it neither estimates confidence coverage nor bounds rare
optimizer failures. No new bank or half-bank campaign is part of this study.

Record and examine all main-fit nonfinite values, failed convergence, nesting
violations, score-replay discrepancies and boundary contacts. Routine h=1
boundary estimates alone do not trigger extra profiling. For diagnostic
expansion, take the lowest replicate ID in each cell for each new failure
category (nonfinite score, nonconvergence, nesting violation, score-replay
discrepancy). Extra profiles/lattices diagnose a mechanism and are explicitly
selected, never additional operating replicates. A source/scorer defect stops
release for repair; a confirmed limitation of the frozen algorithm remains
numerical fragility without changing its stored estimate, declaration or
denominator. Diagnostic points exceeding a main optimum do not authorize
refitting. Any further expansion must be justified by defect diagnosis and
remain inside the resource envelope, or return for a decision.

New effect-reference audits retain the Goal 061 standard: exhaustive stored
row/address/status/direct truth/null/free-score checking and first/middle/last
generator replay at each new node (1,398 sampled replays), with anomalous rows
also replayed. Reused tables retain their accepted audits after custody/hash
verification. All observed ranks are independently reconstructed from audited
tables. Cache validated reference statistics once and use bounded batches;
do not reread hundreds of databases for each evaluation history. Any batching
optimization must reproduce scalar ranks, including ties, without modifying
the statistic or failure propagation.

## Interpretation and stopping rule

Complete exactly 500 histories per cell, all required reference work and the
independent audit. Do not stop for apparently high/low power, add histories to
cross a threshold or retune a nuisance anchor after seeing outcomes.

This is a measurement campaign, not a new omnibus pass/fail qualification.
Report sensitivity and recovery numerically at each registered truth. A null
Wilson interval wholly above .05 flags conditional miscalibration of the
realised table at that anchor; it does not falsify the marginal bound or
authorize recalibration. High declaration with poor magnitude recovery
supports detection but limits estimation claims. Low sensitivity, large errors,
frequent abstention or predictive ambiguity narrow the practical-method claim
and remain valid endpoints. Avoid an unregistered adjective such as “reliable”
based on a favourable post hoc threshold.

The final report must preserve all six outcomes, uncertainty targets,
deviations, numerical limitations and reference costs. It does not close the
separate landscape-generality or common-process-model gaps in the charter.

## Implementation and launch boundary

The existing training/audit/sealing adapters assume four cases. They are not
a ready 3,000-history runner. After approval, build a narrow panel wrapper and
independent audit path around the unchanged scientific primitives; qualify
counts, seeds, masks, truth isolation, failure semantics, cache/rank equivalence
and checkpoint resume before any production draw. The legacy sealed-case
schema and reports remain unchanged. No new package framework is needed.

Retain Python 3.14.5, NumPy 2.5.1, SciPy 1.18.0 and PCG64 on the qualified Linux
runtime. The [compute estimate](compute-estimate.md) specifies the inherited
identities and proposed envelope: deep-server, up to 51 workers with one
library thread each, 64 GiB aggregate RSS, 50 GiB free scratch and a **72-hour
hard wall ceiling**, with checkpointed pending status at a resource stop.
This is a proposed allocation, not a statement of current host availability.

The authorized launch tranche should include read-only consultation of
`/Users/bwbrook/work/nectar/docs/workflows/{control-plane-doctrine,compute-resource-selection,project-integration,data-placement}.md`
and `/Users/bwbrook/work/nectar/docs/exchange/current_status.md`, plus read-only
verification of deep-server capacity. No sibling writes, cloud spending or
machine changes are proposed.
Mechanical/existing-public-fixture benchmarks must check the evaluation
wrapper's throughput and memory before production. If they imply the campaign
cannot fit the envelope, return with the measured estimate. A scientific
source/runtime mismatch, change of estimand, method or grid, resource-envelope
increase, or unrecoverable defect likewise requires a decision. Routine
checkpoint recovery retains the exact same addresses and immutable results.

The present tranche ends with this reviewed design and cost estimate. No
production source was changed, no benchmark or new simulation was run, and
no launch is implied by independent review or by committing these documents.
