# Proposed blinded capstone protocol

**Review update, 3 October 2026:** Fable's messages 811–813 have been read and
answered in [Astra's review response](fable-response-2026-10-03.md). That response
proposes scalable-calibration feasibility, four histories and concrete private
custody, and explains the limits of an already disclosed truth envelope. Barry
decides those amendments next. The 2 October proposal below is retained as the
reviewed version; it does not authorize a launch.

2 October 2026 (Hobart). **Design for review; no capstone launch.** This advances
Charter Pillar 5 and tests transfer of the conditional Pillar 4 findings. Barry
approved this design work and Fable as truth-holder, with Astra blinded. The
recommendation below follows the verified Goal 055 checks; no hidden truth,
generator seed or capstone history has been drawn.

## Scientific decision

Can an analyst distinguish an effect declaration, a useful estimate and a
predictively adequate model when access bias, stochastic arrival, spatial
background loss and imperfect prey detection occur together? One sealed
scenario supplies a diagnostic case study. It cannot estimate population
coverage or complete a landscape-generality experiment.

The analysis must be allowed to conclude that the effect magnitude or model
family is unresolved. The design must not guarantee a positive effect or
exclude the null from the analyst's candidate set. All model fits, diagnostics
and ecological conclusions are frozen before reveal.

**Selected information branch: 60 days of pre-invasion monitoring.** Goal 055's
low supplied mean produces adjusted null rates of 7.8% [5.3, 9.5] and 10.8%
[7.1, 12.8] in E0/E06. Both pointwise calibration-aware lower limits exceed
5%, triggering the [registered](registration-2026-10-01.md) failure predicate.
The analyst must estimate the mean from an explicitly modelled observation
history. The extra observations are a proposed source of information, whose
adequacy remains to be demonstrated.

**Detection prerequisite: triggered by both registered flags.** D20's adjusted
null rate is 19.8% [15.2, 22.1], and its paired increase above baseline is
16.0 points [12.1, 17.8]. Thus both absolute excess above 5% and deterioration
relative to the paired baseline are present. The common observation model must
accommodate persistent site-level prey-detection heterogeneity before a
calibrated capstone analysis is possible. These pointwise archive checks do
not validate the proposed replacement likelihood or its calibration.

## Fixed ecological scenario

Use one new 72-by-84 **connected** landscape from the existing Arc 3 generator,
with its fixed habitat inventory, source geometry and access network. This
retains an ecologically interpretable habitat mosaic without adding the
corridor regime whose tail-integration difficulties remain unresolved. A new
map still needs numerical qualification. Freeze the first structurally valid
map under a public map seed, chosen before observations; retain any failed
structural-generation attempt. Do not search maps for strong information or
clean results.

Use the existing access-constrained 120-site training design and 40 prospectively
reserved, cluster-isolated holdout sites, preserving five-site clusters and preventing overlap.
The split and coordinates are public and fixed before any predator/prey
history. Eight five-site holdout clusters remain dependent through landscape
and spread; they are not 40 independent replicates. Report aggregate scores
and cluster contributions descriptively, with full-generative calibration
where required rather than site-iid intervals. Holdout observations are released
only after training fits and model choices are locked; no holdout feedback may
change the candidate set or trigger a training refit.

Retain the registered stochastic predator-spread family, source locations and
invasion start at day 0. To keep this first capstone bounded, supply spread
speed and resistance as explicit design assumptions, together with predator
detection probability .65, mean prey detection .65 and zero false positives. These are genuine remaining
known-nuisance limitations: this is not an analysis with every field nuisance
unknown. The realised arrival times and spread seed remain sealed.

The prey effect is the multiplicative change in site loss hazard after local
predator arrival. The hidden generator uses one h in {1,3}; the analyst searches
the full h=1..10 grid. Background hazard has a hidden whole-map mean selected uniformly from
{.0016,.002,.0025}/day; the analyst must not receive its realised value. A
single background state L has probabilities E0=1/4, E06=1/4 and B100-A=1/2.
This preserves an equal chance of residual-field presence and absence, with
equal beta0/.60 choices within the exact family. It avoids adding an
independent beta to B100-A, which already contains its own aligned component.
For every cell i of the 72-by-84 map, define

- E0: w_i = 1.
- E06: w_i = exp(.60 A_i).
- B100-A: w_i = exp(sqrt(log 2) [ .70 A_i + sqrt(.51) G_i ]).

In every state, lambda_i = mu w_i / mean_all_6048_cells(w). The scalar mu is
the drawn whole-map mean, and sampled-site means are not recentered. B100-A
retains the original Gaussian field law, covariance exp(-grid distance/10),
exact 142-by-166 circulant embedding and its numerical checks; each realised
G is neither centred nor standardized. Its nominal CV 1 does not imply a
realised whole-map CV of exactly 1. These are mutually exclusive background
states, not an extra residual multiplier layered over an independently drawn
beta. The analyst knows this finite envelope but fits the stated small model
set below. An actual null and an exact-family case remain possible while
retaining one justified misspecification.
Do not add the weak N100-A stress, temporal trend, recolonisation or another
new process merely to make the capstone harder.

Site-specific prey detection follows the existing Beta construction, fixed
across visits, with supplied population mean .65 and hidden SD selected from {0,.20}. The
known mean is an explicit remaining nuisance assumption; realised site
probabilities and dispersion are withheld. The analyst knows this family and
envelope but not the draw or whether heterogeneity is present. Goal 055 activated the detection prerequisite, so the analyst model must
accommodate this site-level variation and pass design-specific qualification
before generation.

Fable draws h, map mean, background state L and detection SD independently,
using the stated probabilities for L and uniform draws for the other finite
sets, committing this joint distribution, RNG algorithm/version and environment
before generation. No separate beta is drawn in the B100-A state. Thus
h=1 has probability one half, and an exact-model or weak-information history
is an accepted case-study outcome. Separate child streams generate truth,
spread, residual field, prey loss, site detection, prey visits and predator
visits. The public map/sampling streams are separate from these private
streams; no private seed is released before reveal. There is one capstone history and no replacement for
weak information, a surprising result or failed detection. Numerical or schema
failures are diagnosed with the original package retained; an authorised
regeneration, if ever necessary, must be labelled a new attempt.

## Observation and information design

The selected proposal adds **60 days of observation at the
same selected sites before invasion**. Observe prey on days -60,-50,-40,-30,
-20,-10,0 and retain the six post-invasion surveys on days 10,20,30,40,50,60,
with two visits per occasion. Predator surveys retain the six original
post-invasion occasions; pre-invasion absence is a specified design fact. The day 0 prey survey occurs
immediately before predator introduction; source arrival occurs immediately
afterwards. Both within-occasion visits see the same latent state and site
detection probability, with independent detection draws conditional on those
quantities. All planned visits are completed; there is no missingness process
or post hoc visit exclusion in this first capstone.
The prey cohort is present at the start of day -60 by construction, an explicit
initial-state assumption supplied to the analyst. Do not select or discard
sites on their later observed presence, and do not reset prey survival at day 0.
The likelihood must carry pre-invasion loss through the post-invasion period.

This is 13 prey occasions, 26 visits per site and 4,160 site-visits, compared
with 1,920 in the six-occasion design. The 60-day extension adds 2,240 prey
site-visits (including the initial occasion); predator effort is unchanged.
The proposed branch estimates background mean and spatial coefficient jointly from the
observed history, with prey detection integrated over sites. The extra surveys
are a design candidate, not an already demonstrated solution.

Compute A using only the public habitat/resistance map, source geometry and
analyst-supplied spread assumptions, following the existing deterministic
exposure calculation and whole-map standardization. Astra computes and hashes
this array before reading observations. Fable independently checks its identity.
Do not supply A derived from the realised spread, latent arrivals, background
field, prey losses or hidden true coefficients.

## Analyst models and locked reporting

Fit every history under the same small prespecified set, with identical
training data, nuisance treatment, effort and predictive targets:

| Model | Scientific role |
| --- | --- |
| Constant background, free h | Quantify the flexibility cost and vulnerability of omitting spatial background structure. |
| A-adjusted background, free h and beta | Primary effect model; its nuisance treatment must be qualified for the chosen information branch. |
| A-adjusted background, h=1 | Information-matched no-effect comparator for declaration and prediction. |
| Constant background, h=1 | Nested baseline required to interpret the constant model's effect decision. |

All four models estimate the same unknown map mean and use the same prey
observation model. If heterogeneous detection is included, its site-level
random effect is shared across visits, not redrawn each visit. Estimate its
dispersion from training observations, using the explicitly supplied population
mean .65, rather than hand the analyst the hidden site probabilities. A Beta mixing distribution is the minimal
matched candidate; its identifiability is a qualification question.

Report h/beta/background profiles, fitted detection dispersion, boundaries,
likelihood trade-offs, point estimates and integration/grid diagnostics. A raw
likelihood support region must be called a support region unless confidence
coverage has been separately established. Compare held-out conditional-prey
log score per site, and publish direct differences among the four candidates.
Do not name a model winner from a score sign alone. Report the original
adequacy discrepancy only as a descriptive statistic unless a new calibration
qualifies it under this design.

An effect declaration is permitted only under a newly qualified rule that
includes the chosen map, calendar, unknown background level and observation
model. The Goal 054 table cannot transfer. The prerequisite must freeze the full finite nuisance domain, numerical
grids/bounds, mixing integration and any priors before calibration. Publish
the exact finite-grid validity argument and independently evaluate false
declarations across that domain, including boundaries and weak-event cases,
with reference-table uncertainty and separate h3 sensitivity. Pointwise
checks at a few nodes cannot license a continuous-nuisance claim. A new
calibration registration must state its replication and acceptance criteria
before outcomes; none is chosen from capstone truth or observations.
Exact-family calibration and residual-field robustness remain distinct. Unless
the residual-field family is explicitly covered by that new validity argument,
the prereveal declaration must state its fitted-family assumptions. A revealed
residual-field case then audits transfer under misspecification; it does not
inherit nominal error control merely because the analysis was calibrated.
Failure to qualify leads to a descriptive capstone with an explicit absence
of calibrated effect claims only if Barry approves that reduced claim; the
analyst cannot make that change after seeing the sealed observations.

The prereveal report must contain: data/schema exclusions; all fits and model
comparisons; numerical diagnostics; a qualified declaration or explicit lack
of license; effect-magnitude uncertainty; predictive ambiguity; and a short
scientific interpretation with testable predictions about what the reveal
will show. Hash this complete report, code, inputs and generated outputs.

## Genuine blinding, handoff and reveal

Fable's truth bundle contains the generator version, exact coefficients,
seeds, arrival/loss/detection fields and all generator diagnostics. It remains
outside Astra's accessible repository, tools, correspondence payloads and
shared agent context. Fable publishes only its cryptographic commitment and
an observation-package hash. A subagent in Astra's shared workspace is not a
truth-holder substitute. No instruction to simply avoid opening a shared file
counts as blinding.

The analyst package contains public map/source/access metadata, fixed site and
visit identifiers, the declared initial-state and known-nuisance assumptions,
training counts, and the schema and commitment hash for the unreleased holdout
package. Holdout counts remain outside Astra-accessible storage until the
training lock. The analyst package excludes latent
arrays, generator seeds, truth-bearing filenames, branch IDs, debug logs and
truth-derived field summaries. Fable checks for leakage before release. Astra
checks only public schema, units and hash consistency.

The fitted-model lock includes executable code/environment, training inputs,
parameter estimates, candidate set and fitted predictive-distribution hashes.
Fable releases holdout observations only after this lock; no refit or model-set
change follows that release. Fable then releases
truth only after receiving the immutable complete analysis-report hash. The
reveal record verifies the original commitment and evaluates: declared versus
actual effect; multiplicative point error; any qualified interval coverage;
background/detection misspecification; predictive preference; and whether
prereveal diagnostics warned of the realised failure. Latent arrival/oracle
fits may be used afterwards solely as labelled audit diagnostics, with no
replacement of the prereveal result.

## Smallest prerequisite and stopping boundary

The current software does not yet qualify unknown background mean, a
pre-invasion calendar or heterogeneous prey-detection inference. The smallest
useful next tranche is **one observed-data
nuisance-and-calendar feasibility study**, before a capstone calibration or
sealed generator launch. It would implement those modular likelihood pieces
in a new path, verify limiting cases against frozen kernels, use known-arrival
synthetic fixtures for exact checks, then inspect parameter profiles, identifiability and numerical
cost on openly labelled sacrificial histories, including boundaries and
weak-event cases. A separate subsequent calibration must assess size and any
claimed coverage before the capstone truth is drawn. That feasibility study must
settle parameter bounds and the calibration design from its own declared
criteria; the capstone truth is not drawn until the path is frozen.

Fable's ideal SE calculations (.24 versus .51 under the current survey and
.36 with 60 pre-invasion days) are advisory complete-data information
benchmarks, not verified performance predictions. In `1/E_pre + 1/E_post`, E
is an expected event count, not time exposure. Actual precision must include
latent arrival, imperfect detection and nuisance estimation. No guaranteed
threefold sensitivity or effect sizing follows from that calculation.

The proposed first implementation request is bounded to the likelihood pieces,
limiting-case tests and one openly labelled timing panel, with an independent
review. Freeze its nuisance bounds, numerical axes and acceptance tolerances
in that future registration before running the panel. Use 16 exact-family
histories spanning h={1,3}, mean={.0016,.0025}, beta={0,.60} and detection
SD={0,.20}, crossed once, with the proposed calendar and all four candidate
fits. These histories are expendable development fixtures, never a source for
capstone truth or operating-rate claims. Add deterministic checks of zero
heterogeneity, the original six-occasion limit, known arrivals, day 0 survival
continuity and the shared site-detection mixture. A 16-history panel cannot
establish recovery, size, coverage or general identifiability.

Use deep-server for this proposed benchmark, with at most 16 workers, one BLAS
thread each and 48 GiB, and a four-hour ceiling for the first complete timing
attempt. This is a resource limit, not an empirical runtime forecast. A timeout
is evidence that the proposed numerical path is not yet qualified; preserve
it and diagnose before proposing a larger campaign. No incomplete panel can
support a cost or scientific qualification claim. Routine resource choices
remain delegated, while changed scientific scope requires review.

Cost any subsequent feasibility or calibration campaign from that complete
full-dimensional timing. Include bank/integration construction, every candidate
fit, held-out scoring, serialization, synthesis and independent review, with
an explicit margin. Goal 055 production took 6 h 22 min for its existing fixed
nuisance path; its new integrations were already constructed during the
16 min 43 s timing run. Those times anchor unchanged components only. Extra
visits and nuisance dimensions make simple scaling by history count invalid.
The first feasibility deliverable is a tested likelihood, a diagnosis of
parameter trade-offs, a measured budget and a proposed calibration
registration. No precision or threefold-sensitivity target is promised from
this timing exercise. This document stops at a reviewable design; it does not
implement or launch the prerequisite, new calibration or capstone.
