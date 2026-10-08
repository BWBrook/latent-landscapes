# Goal 052: adjusted-background identifiability pilot

24 September 2026. **Approved; numerical design frozen before adjusted fits.**
Charter Pillar 4 / Roadmap Arc 4. This is model-development evidence from
archived histories, not confirmation of the selected Goal 051 departure.

## Authority and reporting horizon

Barry approved the [pilot proposal](../051-misspecification-screen/adjusted-background-pilot-proposal.md):
“Agreed. I approve of your suggested approach: proceed.” He also delegated
compute decisions: “you don't need to ask me for specific approval regarding
compute resources and timing: you have authority to make those decisions as
you deem best.” Deep-server, Nectar and Kunanyi are available within that
delegation. This supersedes the proposal's requirement for a human resource
or timing amendment; it does not expand the scientific panel or authorize
fresh confirmation, calibration, additional surveys, commits or publication.

The approved scientific amendment permits this retrospective pilot before
standalone confirmation. The Goal 051 nominee remains unconfirmed. All frozen
Goal 049–051 results, original proposals and earlier numerical failures remain
unchanged. The gold stamp is a verified numerical/identifiability assessment
and a costed prospective comparison recommendation, or a preserved scientific
or computational stopping outcome. No larger campaign follows automatically.

## Fixed scientific comparison

Keep the accepted landscape, source, 120 training / 40 held-out sites, survey
times 10,20,30,40,50,60, two visits per survey, known detection probabilities
0.65, spread speed/resistance 1, K131072 independent bank and alpha=1 empirical
arrival-category regularization. The analyst receives the same known whole-map
mean background hazard, mu=0.002, in all three models.

Let A be Goal 051's normal-score source-distance proxy over **all 6,048 map
cells**, including its tied unreachable cells. Define

`lambda_i(beta) = mu*exp(beta*A_i)/mean_all_map(exp(beta*A))`.

Hazard is lambda_i before arrival and h*lambda_i afterwards. Compare constant
background (beta=0, fitted h), adjusted background (fitted beta and h), and
adjusted no-effect (fitted beta, h=1). The no-effect comparator uses exactly
the same training observations and known inputs. Holdout observations never
select parameter bounds, grid, fit or model. A matches the proxy used in the
generator, a deliberately favourable adjustment; the omitted Gaussian field
G still makes the adjusted model misspecified under B100-A.

Use only original production replicate indices **0–5** in B_h1, B_h3,
B100-A_h1 and B100-A_h3: 24 histories in six paired blocks. Reconstruct the
original seven-stream seeds from root 2026092301. The unchanged generator
replays the complete coupled block internally; discard the other cell outputs.
The selected histories and indices are not chosen for apparent fit or error.
No new random process histories or calibration are included. These six blocks
cannot establish population bias, recovery, coverage or power.

## Likelihood and numerical design

The latent-arrival analysis retains the existing joint site-composite
likelihood. It integrates prey survival against the same empirical arrival
bank and seven pseudo-arrivals (5,15,25,35,45,55,70), with alpha=1 per category.
Site-specific lambda changes survival moments, not predator emissions or bank
weights. Use exact algebraic category transforms, without arrival binning,
quadrature or a new integration approximation. Build each beta row once and
score all 24 histories against it.

The oracle diagnostic supplies replayed true arrivals to the prey-observation
likelihood, with imperfect prey detection retained. Its true arrivals enter
only that explicitly oracle API; actual fits consume analyst observations,
the known map proxy and independent bank. For comparisons of geometry use
each lane's likelihood differences, not absolute joint-vs-oracle levels.

Freeze these finite search rules before any adjusted fit:

- Fine grid: **h=1..10 by 0.05 (181 nodes); beta=-2..2 by 0.05 (81 nodes)**.
- Nested coarse grid: every second node on each axis (0.10 spacing).
- Compute the entire fine rectangle. Coarse/fine comparisons use these saved
  surfaces; there is no selected local search, additional optimizer or
  outcome-dependent expansion. Lowest beta then lowest h wins exact ties.
- Profile h by maximizing over beta; profile beta by maximizing over h.
  Store the complete joint surfaces and all fitted model coordinates.
- Report coarse/fine maximum changes and coordinate shifts. Flag a movement
  exceeding 0.10 LR units, 0.10 in h or 0.10 in beta as resolution-sensitive;
  a coordinate jump on a near-flat surface is reported alongside its LR
  change. These are pilot sensitivity diagnostics, not uncertainty coverage
  guarantees or a reason to redraw histories.
- Flag beta edges and h=10 as potentially truncated fits. h=1 is a physical
  boundary and expected under a null, not a numerical failure. Preserve edge
  contacts and weak ridges. Do not introduce penalties or narrow the box to
  manufacture identification.

Joint contours at LR 0.5,2,4,8 and profile ranges at LR<=2 may summarize shape,
explicitly as **uncalibrated likelihood geometry**. They are not confidence
regions. Do not reuse Goal 049/050 cutoffs after adding the fitted nuisance.
The finite box cannot establish uniqueness or identifiability outside it.

## Required controls

1. Verify frozen source and input identities, including Goal 051 production
   arrays SHA256 `6d98c61d8ecee7b53335dec13de536bfbead700fee6d97a48644efafba11e381`
   and the existing full bank provenance. Reproduce original profiles, joint
   holdout curves, fitted nodes, conditional prey scores, predator scores and
   opaque IDs **exactly** with the unchanged legacy scorer before fitting.
2. Verify whole-map hazard normalization, positivity and site ordering;
   beta=0 gives the constant background model. The new factored kernel must
   agree with the unchanged alpha=1 kernel within 1e-10 absolute log-score/LR
   units on the pilot controls. Algebraic rearrangement need not be bitwise.
3. On small deterministic banks, independently enumerate empirical and pseudo
   arrival atoms and extinction/censoring states, including survey-boundary
   arrivals. Verify joint and conditional probabilities at nonzero beta.
4. At h=1 prey likelihood must be independent of arrivals and predator
   observations. Verify oracle likelihood against a separate two-state
   recursion, and enforce the truth-free actual-scoring interface.
5. Verify nested model maxima, finite probability/survival calculations, fixed
   training/holdout separation, source bindings and complete output coverage.
   Preserve a failed control, diagnose it and requalify changed source before
   substantive fits; do not repeat an unchanged failure or skip a control.

## Diagnostics and predictions

Retain per-history fitted h/beta, profile and joint surfaces, coarse/fine
movement, edge contacts, raw training improvement, and held-out score against
the **fitted adjusted no-effect** comparator. Separately report the original
constant fit and its h=1 comparator. No held-out sign is converted into a new
adequacy decision rule. Label differences as conditional-prey predictive
contrasts: the invariant predator marginal cancels from joint differences.
Absolute joint levels are not measures of prey fit alone.

Report A overlap and arrival-time support across the split, counts of survey
occasions before true arrival, and evaluator-only pre-arrival at-risk time
`sum(min(arrival, extirpation, 60))`. Distinguish observed survey opportunities
from latent exposure diagnostics. Also count sites and survey occasions with
`t < min(arrival, extirpation)`, so dead prey do not inflate the pre-arrival
information diagnostic. Retain each block, not just six-block means.

Pre-fit expectations, not acceptance gates:

1. Adjustment will reduce fitted h in aligned-null histories relative to the
   constant model, but may trade bias for a weaker h/beta separation.
2. Baseline threefold histories will retain evidence for h above one after
   adjustment more consistently than aligned-null histories; the supplied
   overall background mean is still favourable information.
3. Oracle arrival information will usually sharpen separation relative to the
   latent analysis, but individual histories need not follow that ordering.

Report the six paired outcomes descriptively, including failed expectations.
Do not attach population significance to a small development panel.
There is no exact nonzero-beta adjusted-model generating control in this
panel: the baselines validate beta=0 and B100-A retains omitted G. A ridge
cannot be uniquely attributed to survey design rather than misspecification.
Expected h=1 contact under a null still leaves one-sided/truncated geometry;
h=1 contact in a true h=3 history is a substantive warning.

## Execution and resource decisions

Use deep-server-ts initially: live inspection found an idle host with about
123 GiB available RAM and the archived bank already present. Keep numerical
library threads at one; start with eight beta-row workers and a 32 GiB process
address-space ceiling. Shared bank/prepared arrays avoid per-worker copies.
Four hours remains an initial planning target, not a human approval boundary.

Before the remaining grid, time complete rows at beta
`[-2,-1.5,-1,-0.5,0,0.5,1,2]`, including all latent/oracle scoring. Reuse those
eight rows in the final grid. Project the remaining workload from the slowest
measured row with factor 1.5, plus measured construction and at least 1,800 s
for synthesis/verification. Bind the projection to source, grid and inputs.
Preparation and construction costs count once. Routine changes to host,
parallelism or wall-time are Astra's decisions, documented with measured
reason and verified capacity; scientific grids, replication and bank stay fixed.

Use an exclusive run lock, persistent start/exit receipts and bounded phases;
never duplicate a running or completed phase. Source changes invalidate that
source's numerical/timing qualification. Preserve completed row files and
their bindings; avoid redoing successful work. If sustained computation needs
asynchronous continuation, create a quiet heartbeat and remove it at closeout.

## Closeout

Inspect figures and tables, obtain an independent result-level scientific
review, and write the feasibility/identifiability synthesis and costed next
comparison. A stable fit is not recovery under the omitted G field. A weak
ridge, truncation or computational limitation is a valid pilot outcome.
Future decisive evaluation needs appropriate calibration, exact adjusted-model
positive controls and fresh independent histories under separately agreed scope.
Post substantive findings on Correspondence thread 53 as Astra; Barry is not
needed for routine compute choices. No commit, push or publication is authorized.
