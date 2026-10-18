# Paper 1: integrated experiment and manuscript plan

18 October 2026. Codex proposal for iteration with Claude, Correspondence
thread 87. **Planning only; the experiment and methods below are not approved.**

**Current proposal:** the [consolidated protocol](paper1-integrated-tranche-protocol-2026-10-18.md)
incorporates the subsequent exchanges and verified complete-data diagnostics.
Its recommendations supersede this initial plan; the earlier text remains
the record of how the design developed.

**Iteration 2:** the [design–model review](paper1-design-model-review-2026-10-18.md)
reproduces Claude's new depletion diagnostics, revises the mechanism contrasts,
and proposes qualifying a portable empirical inference rule with targeted
simulation-calibration comparisons. It supersedes the initial recommendations
below where specified; map counts and method choices remain under review.

## Direction and authority

Barry selected **broader first**, covering both landscape generality and a
common competing-process model set in the [submitted decision](decisions/2ae00028-a20e-431b-bc79-88a10b53cbf1.md).
His direct chat instruction on 18 October was: “we have compute to burn, we're
not on a time or compute budget, and I don't want this to be a salami slice.”
He also directed Codex to his instructions on the board about sustained
Codex–Claude iteration for both generalist editors and specialists.

Accordingly, the proposed destination is **one integrated Paper 1**, advancing
charter pillars 3 and 4 alongside the recovery, uncertainty and capstone
evidence already accumulated. The earlier recommendation to do a small
coverage check and then narrow the paper is superseded as a recommendation.
The [charter](paper1-experimental-design-charter.md) remains unchanged.
Goal 062 and the original blinded capstone remain closed evidence.
The submitted form explicitly retains launch approval; this document starts
no simulations, benchmarks, method implementation or new goal.

## The paper's question and proposed contribution

> When can imperfect monitoring distinguish an invader's effect from
> spatially structured background loss, and can we predict which monitoring
> designs will make that distinction reliable on a new landscape?

The proposed contribution is an explanation of **when an ecological impact
can be learned**, linking landscape-mediated exposure, observation timing,
background variation and inferential uncertainty. Its practical output would
be a tested way to anticipate informative and uninformative monitoring
designs. It could also establish useful limits: extra data or a more flexible
model may fail to resolve the ambiguity. Neither result should be retuned away.

This question sits within the broader charter on spread, resistance,
detection and prey-response recovery. The existing reference ladder explains
how those components become estimable under earlier, simpler procedures. The
new experiment chiefly evaluates nuisance-estimating prey-effect inference
across landscapes and plausible backgrounds; it does not jointly revalidate
spread, resistance and every detection parameter as freely estimated in one
unchanged procedure. It is not a claim to a general causal-identification
method or universal design law.

The novelty proposition still needs a focused literature comparison before
an abstract claims novelty. Baseline monitoring and spatial confounding are
established ideas. The candidate advance is their quantitative connection to
latent invasion timing, imperfect observation, calibrated effect inference
and prospective prediction of experimental performance.

## Claim–estimand–evidence spine

| Proposed claim or question | Decisive contrast and endpoint | What would weaken or falsify it? |
| --- | --- | --- |
| Baseline information makes invasion effects easier to distinguish from background loss | Paired monitoring arms; null declarations, positive declarations, signed/absolute log-effect error, coverage and width | Equal-effort post-only monitoring performs as well or better; benefits disappear after accounting for event yield or detection information |
| Alignment helps explain differences among landscapes | Matched background-alignment contrasts within independent maps; map-level performance versus pre/post event information and alignment | Geometry differences persist without the predicted information/alignment relation, or the field manipulation changes other properties enough to prevent attribution |
| Flexible background modelling reduces confident mistakes under specified generators | The same constant, exposure and spatial-residual candidates on every dataset; harmful confident errors, prediction and family discrimination | Flexibility absorbs the invasion effect, gives poor coverage, or cannot distinguish plausible families |
| Monitoring performance can be forecast before collecting outcome data | Frozen forecasts scored on untouched maps against total-event and archetype-only comparators | Poor calibration, no improvement over simple forecasts, or accuracy requires hidden realised fields/arrival times |
| Reported uncertainty is trustworthy within a stated domain | End-to-end null error and interval coverage for a frozen procedure on independent histories/maps | Inflation, undercoverage, boundary or numerical failures in prespecified regimes |

These are hypotheses, not conclusions inferred from Goal 062. In particular,
its fixed-map B100-A results do not establish a general spatial-confounding
mechanism or protection against misspecification.

## Necessary corrections to Claude's first proposal

**The information identity is an ideal-data bound.** The existing
[information note](advisor/fable-information-bounds.md) derives
`var(log h) = 1/E_pre + 1/E_post` with the shared background level estimated
and slope known, from complete event data and known arrival times. It does
not establish that identity for latent arrival, interval observations,
persistent imperfect detection, estimated spatial backgrounds or model
selection. Adding a pre-period is not by itself a BACI design. Temporal
replication and appropriate controls matter for interpreting disturbance
effects ([Underwood 1994](https://doi.org/10.2307/1942110)).

**Independent cluster intercepts do not represent B100-A.** The live
[generator](../src/latent_landscapes/capstone_public.py) uses
`z = 0.7 A + sqrt(0.51) G`, then
`lambda = mu exp(sqrt(log 2) z) / mean_map(exp(sqrt(log 2) z))`.
The [field sampler](../src/latent_landscapes/misspecification_generator.py)
has exponential spatial covariance with range 10 cells. Thus the exposure
loading is about 0.5828 and residual SD about 0.5946 before normalisation.
There is dependence between clusters, within-cluster variation, and a random
normaliser involving the entire map. Independent one-dimensional cluster
quadratures omit all three. A sampled-site GP with a free intercept can
represent a realised sampled hazard surface, but is not the same unconditional
generating law unless the normaliser's joint distribution is retained.

**Geometry is not an isolated confounding treatment.** Maps also alter arrival
times, invaded fraction, survival, exposure duration and event yield. A
geometry-by-background factorial alone cannot identify the proposed mechanism.
The dependence of spatial-confounding bias on relative spatial scales is
already established in simpler regression settings
([Paciorek 2010](https://doi.org/10.1214/10-STS326)); whether that explains this
survival/observation system remains a question for the new experiment.

**Calibration belongs to the complete procedure.** Goal 062's reference
panel and guarantee do not transfer to a new observation design, spatial
variance component, fitted criterion, family selection or magnitude interval.
The current sitewise arrival integration is a composite working likelihood;
adding a GP does not turn it into the joint likelihood of the spread process.
Ordinary likelihood-ratio cutoffs cannot simply be inherited.

## Recommended experimental architecture

### Landscapes, biological contrasts and replication

Use independently generated connected/open, corridor-dependent and
barrier-dominated landscapes from explicitly specified distributions. Distinct
seeds alone are insufficient if archetypes share a base landscape: map
independence and any deliberate pairing must be recorded. Freeze ecological
admissibility rules before drawing validation maps. Numerical difficulty is
not a reason to quietly replace a difficult map.

Start planning with **four development and eight untouched validation maps
per archetype: 36 maps in total**. This is a transparent costing scenario,
not a qualified sample-size recommendation. Choose the final validation count
using uncertainty in the between-map variance of the paired design contrasts,
before inspecting validation outcomes. For example, an approximate 95% half
width of 0.05 for a mean probability difference requires
`n ≈ (1.96 SD_between / 0.05)^2`, with a small-sample correction and allowance
for uncertainty in the development estimate. Eight maps cannot guarantee
that precision. Increasing histories on one map cannot replace map replication.
The illustrative design also has only **12 independent development maps**.
History replication, parameter cells, backgrounds and monitoring arms do not
increase that number for learning between-map performance. Forecast complexity
and precision must determine the development-map count as well; 12 maps do not
justify a flexible multivariable forecast merely because there are many cells.

Primary biological contrasts are h=1 and h=3, at mu=.001 and .004/day, with
the existing imperfect-detection anchor retained initially. These are targeted
null/positive and low/high event-information contrasts, not an exhaustive
parameter factorial. The earlier reference arcs provide the broader effect,
spread and detection ladders. Any additional h or detection anchors must answer
a specified interpolation or interaction question before validation is frozen.

Use four background conditions: constant; exposure-linked; spatial residual
with exposure alignment; and a matched spatial-residual control without the
intended alignment. The last pair requires a validated construction preserving
the intended marginal variation and spatial covariance. Setting a coefficient
to zero, rotating a map or selecting a convenient field is not automatically
such a control. If exact matching is unavailable, report the changed quantities
and weaken the mechanism claim. Preserve B100-A as a named legacy anchor;
do not silently redefine it to achieve a cleaner contrast.

For costing, allow **1,000 histories per map × background × h × mu cell**.
At a probability of .5 this gives roughly 3.1 percentage points of pointwise
95% Monte Carlo half width within a map; between-map variation remains a
separate uncertainty. Final history and map counts follow the registered
precision targets. Development histories may inform the method; validation
histories may not.

### Three monitoring arms with a shared cohort

1. Same-site pre/post monitoring, using the current prey calendar from day
   -60 to +60 every 10 days and two replicates per occasion as the anchor.
2. Post-only observations obtained by masking the pre-period. This estimates
   the incremental value of baseline data, including their detection information.
3. Post-only monitoring with the same total survey effort as arm 1, reallocating
   the baseline effort to additional sites or visits under a frozen access rule.

The primary scientific comparison is arm 1 versus arm 3; arm 2 diagnoses why
they differ. A claim that baselines beat **extra sites** requires the extra-site
version of arm 3. Extra visits would support a different allocation claim.
The effort ledger must count predator and prey visits and state whether travel
cost is included; exact site/occasion counts await that design choice.

All arms begin with the same cohort at day -60, including sites added in arm 3.
Do not replace animals lost before release, restart the process at day 0, or
condition post-only inference on observed survivors. Marginalise unobserved
pre-period losses. Use paired latent processes and observation streams where
applicable, with independent replicate addresses; report datasets from the
three arms as paired, not as three independent biological histories.

Pre-period masking of existing Goal 062 data can help method development but
is retrospective. It cannot establish equal-effort superiority or replace the
prospective comparison.

### Common candidates, uncertainty and prediction

Fit every dataset with three background families, each with effect h free and
its matching neutral h=1 fit: **constant, exposure-linked, and exposure plus
a spatial residual field**. Thus there are six main fits per dataset. The
spatial candidate should retain the full-map normaliser, or a demonstrated
equivalent joint representation, if inclusion of B100-A's background law is
claimed. Start with the registered correlation range 10; use a prespecified
range sensitivity to expose dependence on that assumption. Do not casually
estimate every covariance parameter with sparse event data. Cluster frailty
may be a secondary approximation, with its discrepancy measured explicitly.

The proposed primary effect analysis uses the prespecified spatial candidate,
with all three families reported as comparisons. Keep predictive family
ranking separate from primary effect inference. If instead a selected-model
effect or interval becomes primary, calibrate and evaluate the entire
selection-then-inference rule. Do not select a model using generating truth,
or use the final holdout both to choose a model and to claim independent
predictive performance.

Preferred uncertainty-development route: simulation-calibrated profile-test
inversion over a declared effect and nuisance domain. Specify grid resolution,
boundary handling, disconnected sets, unavailable intervals and any upper
truncation. Compare ordinary profile intervals as a diagnostic. A finite-grid
formal guarantee and empirical performance between grid points are separate
claims. The exact new calibration construction still needs agreement and
qualification; this plan does not assume that a larger version of the old
765-node table proves it.

Primary predictive scoring uses held-out spatial clusters on the same map,
conditioning on training data consistently for the spatial candidate. Unless
the joint arrival law is restored and qualified, the criterion is a **sum of
sitewise predictive log scores**, a composite score rather than a joint cluster
log density. Family ranking and regret must retain that working-score scope;
joint conditioning of the background field does not resolve the arrival
dependence. Marginal new-field prediction is a distinct target. The **performance forecast** for
an untouched map is also distinct from either observation-prediction target.
Report predictive family confusion, ties/indeterminacy and regret relative to
the best prespecified candidate; predictive ranking is not proof of a unique
ecological mechanism.

### Mechanism, prospective forecasts and boundary stress

Use complete-data expected pre/post event counts and hidden realised alignment
for mechanism diagnosis, clearly labelled as oracle information. A usable
design forecast must use map/design descriptors and declared planning inputs,
not hidden realised losses, arrival times or residual fields. A forecast
conditional on assumed h and mu is a scenario forecast, not an estimate of
their unknown values. Include detection information, exposure-duration
distribution and alignment assumptions; compare with simpler total-event
and archetype-only forecasts.

Fit any empirical inflation/forecast relationship on development maps, freeze
it, then score calibration and error on untouched maps. Goal 062 alone cannot
teach a between-map adjustment. Use map-clustered or hierarchical estimation
and validation, with model complexity supported by the independent development
maps. No correction after seeing validation results
counts as success in the same prospective test.

Include a separate, prespecified temporal-background stress on a balanced
subset of validation maps. A trend or shock concurrent with invasion tests the
limit of the stationary-background interpretation; its form and subset must
be fixed before outcomes. It is an empirical robustness test outside the
stationary family. The existing blinded capstone remains intact and is not
redrawn to manufacture a positive example.

## Qualification and reporting

Develop the integration method against difficult corridor/barrier cases, with
an independent higher-accuracy reference on untouched numerical challenges.
Check profile statistics and uncertainty endpoints, not only likelihood
finiteness, repeated-bank agreement or point estimates. The
[Goal 048 review](goals/048-integration-redesign/final-review.md) documents why
finite scores and accurate conditional integration did not solve rare-order
sampling error. Do not impose a one-week deadline that silently determines
the landscape claim. Failed qualification calls for method diagnosis or an
explicit scientific scope decision.

Report all registered map/history denominators: false declarations at h=1;
declarations and signed/absolute log-h error at h=3; interval coverage and
width; boundary mass; unavailable estimates; numerical failures; and harmful
confident error. Register the latter's threshold, for example an interval
entirely beyond a 1.5-fold error tolerance, before evaluation. Show null and
positive outcomes together. Do not report coverage only among successful fits.
Use map-level uncertainty for generality, with history Monte Carlo uncertainty
within maps and paired contrasts across arms. Separate variability due to the
realised calibration panel from variation in ecological/observation histories.

## Compute evidence and scaling

There is no imposed time or compute budget for this planning exercise. Cost
estimates guide implementation and resource choice, not scientific ambition.
The table below deliberately exposes the size of a full-reference strategy.

Verified local anchors from Goal 062 are:

- 466 new 999-history reference-table receipts sum to **825.734 serial table
  hours**, averaging 6,379.063 seconds per table. Extrapolating that mean to
  765 tables gives **1,355.551 serial table hours**, or idealised 33.889 hours
  at 40 workers / 26.579 hours at 51 workers. This is not measured wall time
  for a fresh full panel; node mix, audits, I/O and scheduling can change it.
- The original production attempt used **20.08 wall-hours**, including the
  466 missing tables and main fits. It inherited 299 tables. The later
  45m33s continuation reused completed work; it is not a fresh-campaign cost.
- Ten qualification histories took a mean **6.544 seconds for four main
  fits**, with history totals 5.689–7.848 seconds. This excludes calibration,
  decisions, audits, interval profiling and the new spatial fits.

Sources: [campaign report](goals/062-final-procedure-evaluation/report.md),
[historical estimate](goals/062-final-procedure-evaluation/compute-estimate-amended-2026-10-11.md),
and the returned `artifacts/goal062_execution/completed-20261015/snapshot/`
reference completion receipts and `benchmark/evaluation/*/rep-000/main.json`.

| Illustrative 36-map scenario | Count or arithmetic scaling |
| --- | ---: |
| Biological histories: 36 maps × 4 backgrounds × 2 h × 2 mu × 1,000 | 576,000 |
| Analysed datasets across three paired monitoring arms | 1,728,000 |
| Six main fits per dataset | 10,368,000 |
| Legacy-sized effect-reference panels, one per map/design | 108 |
| Reference histories if all 108 panels use 765 × 999 | 82,537,380 |
| Legacy reference serial-table equivalent | 146,399 hours |
| Idealised reference wall time at 40 / 51 workers | 152.5 / 119.6 days |
| Existing four fits on all datasets, idealised at 40 workers | 78.5 hours |
| Six fits if the new pair costs 1× / 10× / 50× an existing average pair | 117.8 / 471.1 / 2,041.6 hours at 40 workers |

These are **component scenarios, not a campaign quote**. In particular, the
108 panels illustrate repeating the legacy procedure on each map/design;
they do not price a qualified spatial-model calibration or magnitude-test
inversion. No new-method timing is measured. The calculation excludes the
temporal stress, interval endpoints, screen references, numerical development,
audit work and replicated-reference-panel variability. Do not multiply a
shared reference panel by the number of biological truth cells. Map counts,
worker scaling and all new-method costs must be settled before launch.

A tenfold reduction in this illustrative reference component would reduce it
to roughly 15.3 / 12.0 idealised days at 40 / 51 workers; that is a scenario,
not an achieved speedup. A quantile emulator is not automatically an emulator
of the Berger–Boos nuisance-maximised rank probability. Validation must target
the actual frozen statistic, tail behaviour and decisions on independent
cases, as well as the historical 5,000 histories. Those already inspected
histories are a development/replay set, not untouched validation.

Full-fidelity calibration remains the baseline. Acceleration, caching and
parallel resource allocation are optional implementation research. Their
failure must not automatically remove map archetypes or scientific contrasts.
The final resource plan can use Deep or suitably parallel HPC once the workload
and current availability are verified; no remote work or resource reservation
has been performed for this proposal.

## How Codex and Claude should iterate the paper

1. **Agree on the claim–evidence spine before drafting a conventional paper.**
   Each claim needs an estimand, a figure, a falsifier and an implication an
   informed generalist editor can explain. Keep contested interpretations visible.
2. **Exchange a one-page editor pitch and figure captions.** Claude should
   challenge significance and comprehension; Codex should challenge methods,
   provenance and the inference from each comparison. Both should attempt to
   break the argument. Agreement is not independent empirical validation.
3. **Iterate Methods and anticipated Results together while registering the
   experiment.** Use placeholders and alternative outcomes, never invented
   results. The final launch packet should bundle implementation, qualification,
   the registered campaign and audit into one reviewable tranche, with clear
   scientific stop conditions rather than repeated routine permission requests.
4. **After the evidence arrives, write by scientific question.** Reconcile
   every headline with its figure and denominator, then reverse roles for a
   specialist and editor pass. A surprising negative result changes the story;
   it does not trigger unrecorded retuning.

Proposed figure sequence: (1) ecological ambiguity and experimental designs;
(2) established recovery ladder and detection–magnitude distinction, explicitly
distinguishing the earlier known-nuisance procedures from the later
nuisance-estimating effect procedure;
(3) baseline versus equal extra effort; (4) landscape/alignment mechanisms;
(5) common-model comparison and confident mistakes; (6) prospective performance
forecasts, uncertainty calibration and boundary stress. The capstone supplies
an honest end-to-end illustration within this argument, including its null
outcome. Figures are planned evidence, not six mandatory crowded multipanel plots.

## Open issues for the next Claude–Codex exchange

- Agree on the full-normaliser spatial candidate and its working/joint
  likelihood distinction; supply the calibration and interval construction.
- Choose the equal-effort allocation and a defensible matched-alignment
  intervention; define the temporal stress and prediction targets.
- Turn map/history precision targets and measured new-method scaling into
  the final design and resource estimate. The 36-map table is a costing anchor.
- Challenge the one-paper thesis and return an editor-facing pitch plus
  figure titles/captions that survive both positive and negative findings.

Only after that exchange and a focused methodological review should the
concrete launch decision return to Barry. This is the explicit submitted
planning/launch boundary, not a newly invented approval requirement.

## Review and exchange record

The proposal was posted to Claude in thread 87, message 1896. Bounded
independent editor and methods reviews informed this draft. Their material
corrections are incorporated: distinguish procedure generations in the recovery
ladder; qualify the predictive score as composite; and size development maps
for the complexity of the performance forecast. Parent checks reproduced the
reference-time arithmetic and verified local document links. These are planning
checks, not qualification of any proposed model or experiment. Claude's replies
1902–1905 are assessed in the linked iteration-2 review. Its exploratory
diagnostics and recommendations are not an approved campaign or established
mechanistic conclusion.
