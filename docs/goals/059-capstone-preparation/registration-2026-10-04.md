# Goal 059: freeze and qualify the new-map capstone

4 October 2026, Hobart. **Approved design; public preparation in progress.**
Barry's decisions on Fable's thread 53 messages 915–916 were: “Yes (skip),
Approved (truth law), Yes (confirmed)”. This adopts the stated truth law,
skips the old-map screening pilot, removes a cost cap below the full grid and
confirms the new connected capstone map. It advances Charter Pillar 5 and the
conditional Pillar 4 declaration procedure.

This registration supersedes the unexecuted Goal 058 next-stage proposal and
the older proposed truth mixture/cost cap in Goal 055. It preserves all earlier
results. The approved sequence is: freeze the complete design and reference
addresses; prepare and qualify the new map and its numerical bank on public
fixtures; hand the qualified public package to Fable; Fable generates the four
sealed histories; Astra later analyzes released observations with the frozen
procedure. This tranche closes at that qualified public handoff, or at a
preserved, independently diagnosed negative qualification. It does not draw
private truth or access a private key.

### Disclosed development preview and pre-execution correction

A development command at about 20:17 AEDT used public root 2026100403 despite
the instruction to use only mechanical root 987654321. The incorrect old
implementation used Goal 001 sampling and continued after numerical certificate
failures at candidates 0–4, accepting candidate 5. A separate earlier erroneous
structural-check run rejected all 100 candidates. No bank, observation history,
likelihood, fitting, screening or effect-reference campaign was run. Structural
counts and numerical metadata were exposed. The original accepted JSON/NPZ and
failed-attempt ledger are preserved in
[development-preview evidence](../../../artifacts/goal059_execution/development-preview/provenance_receipt.json).
The initial report of no accepted map, and the subsequent report of a lost
artifact, were incorrect; the artifact was recovered from a separate temporary
directory. Its source hash at execution was not recorded.

The original task brief already specified the Arc 3 sampling constructor,
structural-only first-feasible selection and mechanical-only tests. Code is
being corrected to that brief. The root and those criteria are retained;
candidate 5 is excluded from adoption. Independent review supports applying
the corrected rule once at the existing root, with explicit disclosure that
the root has been previewed. This is prospectively frozen after an implementation
correction, not an entirely unpreviewed registration. No rule, seed or numerical
domain is selected from the preview. Numerical failure on the first structurally
accepted map remains terminal. The finite-grid guarantee remains conditional
on the eventual fixed map and numerical bank; no bank or sealed observation
has influenced this correction.

## Public map and observation design

Use the existing Arc 3 connected-landscape generator on 72 x 84 cells, retaining
the fixed habitat inventory, source geometry, access network, known spread
speed rho=1 and resistance eta=1. Public root **2026100403**, namespace **59**,
assigns candidate map seed from the first uint64 of
`SeedSequence([root,59,1,attempt]).generate_state(1,dtype=uint64)` and sampling
seed analogously from `[root,59,2,attempt]`, for attempts 0..99. Accept the first
candidate satisfying the existing structural map and sampling checks; preserve
failed attempts. Selection concerns only inventory, geometry, connectivity,
reachability and feasible sampling, never likelihood, information, retention
or recovery. If no candidate passes, stop. Once accepted, numerical failure
does not authorize replacing the map.

Use the existing access-constrained design: 120 training sites in 24 five-site
clusters and 40 prospectively reserved holdout sites in eight separate
five-site clusters. Keep four strata with 30 training/10 holdout sites each,
minimum cluster separation, unique physical sites and split isolation. The
existing sampling-pair constructor may also check its balanced comparator,
but the capstone uses the access design only. Canonical order is ascending
site ID. Freeze map, source, access, site, split and cluster metadata and
their hashes before any bank or history draw.

Compute the public exposure A with the existing rank-normal transformation of
negative deterministic resistance distance. Retain whole-map standardization,
all 6,048 cells and unreachable-cell ties. It depends on the public map and
supplied process assumptions, never on a realized spread or background field.
The continuous hazard-box certificate must cover beta [-2,2], mu<=.006 and
h<=10 within the unchanged compressed-transform domain x<=5. A failed
certificate stops qualification on this map; it does not trigger map selection.

A cohort is present at day -60. Prey has two visits at each of thirteen days
-60,-50,...,0,...,60; predators have two visits on days 10,20,...,60. The day 0
prey survey precedes predator introduction. Visits share the same occasion
state and the same persistent site detection probability. Mean prey detection
and predator detection are supplied as .65; there are no false positives,
missing visits, recolonization or selection of observed survivors. Carry prey
loss through day 0 without reset. All 160 sites are generated; only the 120
training sites enter fitting, screening and declaration.

## Approved public truth law; only future draws are sealed

Each of four histories is drawn independently from the same law, with no
stratification, replacement or forced composition. The following coordinates
are independent except where a background branch specifies its own field.

- h=1 with probability 1/2; otherwise log h is uniform on [log 2, log 5].
- Background branch is exact family with probability 3/4, B100-A with 1/4.
- Whole-map mean mu is uniform on {.001,.0016,.002,.0025,.0032,.004}/day.
- Persistent site-level prey-detection SD is uniform on {0,.1,.2,.3}.
- In the exact branch, beta is uniform on {-1,-.75,-.5,-.25,0,.25,.5,.75,1}.

Exact-family hazards are lambda_i=mu exp(beta A_i)/mean_all(exp(beta A)).
For B100-A, draw G with marginal N(0,1) and covariance exp(-distance/10), using
the existing positive-definite 142 x 166 circulant embedding. Do not center or
standardize its realization. Set
Z_i=.7 A_i+sqrt(.51) G_i and
lambda_i=mu exp(sqrt(log 2) Z_i)/mean_all(exp(sqrt(log 2) Z)).
There is no additional beta in this branch. Nominal CV=1 and alignment=.7
describe the construction, not a guaranteed realized hazard CV/correlation.
mu is the whole-map arithmetic mean hazard; sampled means are not recentered.

The supplied rate range corresponds to homogeneous/mean-hazard reference
risks 1-exp(-60 mu), about 5.8%–21.3%. Actual heterogeneous whole-map risk is
mean_i[1-exp(-60 lambda_i)] and generally differs. The narrower truth support
is a deliberate capstone scenario choice; it does not establish universal
ecological plausibility limits. The alternative very-low-mean truth was not
selected. The analysis grid retains its full wider support.

Site detection is one Beta draw with population mean .65 and the drawn SD,
shared across all visits; SD=0 gives constant .65. Conditional on the fields,
generate one full correlated predator spread, one prey-loss threshold per
site, and independent conditional observation draws. h multiplies the loss
hazard after local predator arrival. No independent-site spread approximation
may replace the full generator.

Fable is the truth-holder. After readiness, Fable uses operating-system entropy
once, with NumPy PCG64/SeedSequence and separately addressed child streams for
truth selection, spread, background field, prey loss, site detection, prey
visits and predator visits. Fable records algorithm/version, exact private
roots and all truth in the sealed evaluator package, without logging them.
The expected mix is two nulls/two effects and three exact/one stress; any mix
is valid. All-null and all-effect probabilities are each 1/16.

## Complete analyst procedure

Retain the Goal 056 continuous fitting algorithm and bounds: h [1,10], beta
[-2,2], mu [.0005,.006]/day, detection SD [0,.4]. Retain transformed log h,
log mu and variance fraction, nine domain starts, L-BFGS-B controls, successful-
candidate tie rule, fixed Powell fallback and explicit null-candidate nesting.
Do not optimize on the coarser reference grid. Freeze the actual source and
locked numerical runtime before the public experiment and sealed observations.

Fit all four candidates to identical training observations: constant/free h,
adjusted/free h, constant/h=1 and adjusted/h=1. The adjusted free/null pair is
the sole primary calibrated declaration. Constant-model contrasts are
diagnostic comparisons. Use the unchanged full empirical arrival integration,
seven alpha=1 pseudo-arrivals and degree-48 positive-series compression.
Primary bank size is **K=131,072** at the new fixed sites. It supplies a fixed
numerical statistic; reference histories themselves use full correlated spread.

The nuisance support is exactly 765 nodes: beta=-2,-1.75,...,2; mu=
(.0005,.001,.0016,.002,.0025,.0032,.004,.005,.006); SD=(0,.1,.2,.3,.4), in
beta-major, mu-middle, SD-minor order. At each node the pre-only discrepancy
is twice the difference from the greatest log score among itself and its
immediate axis neighbours. Use the .25 beta stencil for both observations and
references. Exactly 99 pre-only references/node give inclusive plus-one q;
retain C={nodes:q>.01}. There is no global/anchor screen or post-hoc R cutoff.

At each required node, exactly 999 full h=1 references undergo the same
adjusted null/free numerical fit as the observation. T=max(0,2[ell_free-
ell_null]); p_nu=(1+# reference T at least observed T)/1000. Apply the existing
conservative threshold tolerance 1e-10+1e-12*max(1,abs(observed statistic))
in both ranks. Set p_BB=min(1,.01+max_C p_nu), declaring only at p_BB<=.05.

The allowed union size is **765**, the entire support: there is no smaller
cost cap and no exclusion of expensive retained nodes. Shared tables cover
the complete union of the four C sets. Lazy materialization after screening
is permitted solely as retrieval from the fixed node/reference addresses.
It must not change reference counts, seeds, fitting, the union or stopping
rules after outcomes. Hardware/scheduler interruptions leave work pending;
continuation uses identical addresses and verified checkpoints. Cost alone
must not convert a case into a final abstention or a partial-reference rank.

Invalid/incomplete shared screen references make the screen unavailable and
all cases abstain. A nonfinite observed screen makes that case abstain. An
empty C, invalid required observed adjusted fit, or a missing/corrupt/invalid
required effect table gives p=1/abstention for the affected case. One failed
reference makes its complete 999-row table unusable; do not drop or replace it.
Unaffected cases retain their own valid tables. A finite clamped T cannot
rescue a failed fit. Independent scorer/source/schema failures stop execution
for diagnosis. Pending computation is distinguished from a completed
numerical failure. No optimizer or reference retry with new seeds is allowed.

For a true exact-family on-grid null, exclusion of its node has probability
<=.01 and its inclusive effect rank being <=.04 has probability <=.04.
The union bound gives **casewise <=.05** without independence between the
observed screen and effect statistic. The claim averages over reference and
observation generation conditional on the fixed map/design/numerical bank;
it is not conditional on the realized reference tables. Four shared-table
decisions do not provide four-case 5% family-wise error control. No guarantee
covers B100-A, off-grid nuisance, magnitude recovery or profile coverage.
The approved sequence uses this finite-grid argument and implementation
qualification; it does not claim a new empirical operating-rate campaign.

## Random addresses and freezes

Public inputs/bank/panel use root2026100403, namespace59, separated domains:
map=1, sampling=2, bank=3, public histories=4. Bank row j has the first uint64
from SeedSequence([root,59,3,j]), j=0..131071. Public fixture i, stage s uses
SeedSequence([root,59,4,i,s]); stage IDs are spread1, prey_loss2,
predator_visits3, site_detection4, prey_visits5, background_field6. Each emits
one uint64 seed as above, passed to default_rng/PCG64. Save public ledgers
before their draws. Tests use **987654321** exclusively.

Confirmatory reference root is **2026100404**, namespace59, with domain5 for
screening and domain6 for effects. Address (domain,node,reference,stage) emits
the first uint64 from SeedSequence([root,59,domain,node,reference,stage]).
Screen references0..98 use prey_loss2,site_detection4,prey_visits5; effect
references0..998 use spread1,prey_loss2,predator_visits3,site_detection4,
prey_visits5. Node index is the frozen beta-major 765-node index. Freeze this
complete derivation rule, range, node list, source, NumPy version and receipt
before Fable's sealed draw; lazy generation does not require materializing all
histories beforehand. Confirmatory streams are separate from public fixtures,
the integration bank, prior pilots and Fable's private entropy. Goal 058 tables
remain open development evidence and are not pooled into these ranks.

## Small public numerical qualification

Generate eight independent, openly labelled histories, once each, in order:

| Public fixtures | Background | beta | mu | SD | h values |
| --- | --- | ---: | ---: | ---: | --- |
| 0,1 | exact | 0 | .0025 | .2 | 1,3 |
| 2,3 | exact | -1 | .001 | 0 | 1,3 |
| 4,5 | exact | 1 | .004 | .3 | 1,3 |
| 6,7 | B100-A | not applicable | .0025 | .2 | 1,3 |

These are public fixtures, not draws from the sealed mixture and not estimates
of operating rates. Mechanical bank/code qualification precedes their draw:
check fixed all-zero, all-two, modulo-three and early-prey/late-predator patterns
at sixteen h/beta/mu/SD domain corners plus (3,0,.0025,.2). Require direct-
empirical versus compressed whole-history and site log-score error <=1e-8,
finite converged repeat fits agreeing <=1e-8, exact adjusted-pair/four-model
equivalence and holdout perturbation leaving training outputs unchanged.

Fit all four models and three profiles (constant h181, adjusted h181, adjusted
beta81) for each public history with the primary bank and both disjoint
K=65,536 halves, all alpha=1. Persist main fits before diagnostics. Retain the
fixed 1,350-point Goal 056 lower-bound lattice; main fits must dominate their
applicable lattice and converged profiles within 1e-6. No diagnostic point is
fed back into a main fit. All required finite/status/nesting checks must pass.
At each representation independently check direct-bank scores at the stored
fit/profile points; numerical tolerances are 1e-8 scores and 1e-6 T/nesting.

Adopt a prospective **operational nested-bank stability** tolerance, informed
by the programme's earlier decision scale, for every history and each half
versus the full bank:

- adjusted T movement <=.5;
- centered profile R(x)=2[max ell-ell(x)] movement <=.5 over the union of nodes
  where either profile has R<=10, for each of the three profiles;
- R movement at generating h, and at generating beta for exact-family cases,
  <=.5 even if outside that core;
- movement of every held-out candidate score contrast <=.5 total 40-site
  conditional-prey nat.

Report half-versus-half contrasts, raw likelihood offsets, MLE/boundary/support
changes and timings. MLE/boundary movement is diagnostic, not a hard gate for
flat or nonregular profiles. Alpha=1 changes its normalized weight with K;
this checks the complete numerical method, not pure draw convergence. One
nested comparison cannot establish process-likelihood accuracy, map-wide
convergence or tail-rank invariance. The primary bank remains K131072; passing
does not select a half. A failure is negative/inconclusive qualification and
stops before sealed generation. Preserve outputs; do not enlarge the bank or
panel, relax gates, replace the map or retune in response.

Independent review reconstructs input identities, generator normalization,
direct likelihoods, all numerical gates and the new coarse-grid rank/union
arithmetic. It includes public B100 field checks and deterministic generator
replays, explicitly distinguished from independent biological validation.
Run on deep-server in an isolated directory, at most 32 bank/16 fitting workers,
one numerical-library thread each, 64 GiB aggregate process RSS and four hours
for bank construction plus public qualification/audit. This is a bounded
prerequisite, not a cap on the later confirmatory union. Qualify target code
before launch and preserve partial evidence on any resource/numerical stop.

## Reporting, custody and readiness handoff

Lead each future case report with the adjusted declaration and its assumptions,
then h/beta/mu/detection estimates, likelihood-support profiles, numerical
diagnostics and predictive ambiguity. A point estimate at a flat or boundary
profile does not establish magnitude recovery. Profiles are support regions,
not confidence intervals. A low T with an extreme h estimate in Goal 058 is
consistent with weak information; it did not itself estimate false declarations.

Before holdout release, hash the training inputs, fixed map/bank, code/runtime,
all four fits/profiles, candidate set, declaration and interpretive decisions.
Fable checks that lock; Barry decrypts only the committed holdout package.
Score the same fixed fits without model selection or refitting, reporting
conditional-prey total 40-site nats, nats/site and eight dependent cluster
contributions. Then hash the complete report before Barry releases truth.
No site-iid uncertainty claim is made from these holdout sites.

Use the existing public age recipient and Barry's private-key custody.
Fable writes only training observations publicly; salted holdout/truth packages
remain encrypted with separate commitments and hashes. No truth-bearing IDs,
seeds, fields, branch labels, diagnostics or log messages enter the analyst
package. A root subagent sharing Astra's workspace cannot substitute for Fable.
Fable's source/runtime and private stream contract must be frozen in the
generation receipt before drawing; no private value is needed for Astra's
public checks. The readiness handoff binds this design, public map/site/A
arrays, qualified bank, source/runtime and confirmatory address contract.

The reveal audits each declaration, magnitude error, working-family failure,
predictive comparison and whether prereveal diagnostics anticipated problems.
No revealed stress case acquires an exact-family guarantee retrospectively.
All four original histories remain; no replacement for weak information or
unfavourable composition is allowed. No commit, push or publication is
authorized by this tranche; named Nectar workflow reads and the isolated
deep-server computation are within the preparation scope.
