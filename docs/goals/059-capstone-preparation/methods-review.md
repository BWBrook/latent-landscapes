# Independent methods review: Goal 059 capstone preparation

4 October 2026 (Hobart). This review covers the prospective registration,
current public-input and bank-construction source, and the planned independent
qualification. At the start of the review I believed that no production-root
public map had been generated. Subsequent forensic recovery established that a
development command had already evaluated the production root and retained an
old-source candidate. The provenance correction and its consequence are
recorded below. No arrival bank, public fixture, confirmatory reference, fit,
likelihood evaluation or sealed history had been generated.

## Decision

**The registered inferential design is defensible, but public execution is not
yet ready.** The finite-grid screen plus pointwise Monte Carlo effect tests has
the claimed casewise size bound under the registered exact-family null, and the
lazy four-case union does not invalidate it. The registration also now
distinguishes a scheduler interruption from a completed numerical failure and
correctly removes any scientific cost cap below the complete 765-node union.

Four implementation matters must be resolved and independently checked before
the first registered map attempt:

1. the current B100-A implementation does not normalize the realised field to
   the registered whole-map mean hazard;
2. the current map-selection loop can reject a structurally accepted map after
   a hazard or Gaussian-field numerical failure and continue to a later map,
   contrary to the stopping rule;
3. the source uses the Goal 001 sampling constructor while the registration and
   implementation reconnaissance appear to specify the Arc 3 access member of
   `build_sampling_pair`; and
4. the public stream list currently inherits a five-stream development schema
   and omits the registered `background_field` stream required by B100-A.

These were prereveal source defects or unresolved design identity, not adverse
scientific results. Three have since been repaired in source: structural
acceptance is persisted before numerical certification, the Arc 3 access design
is explicit, and all six fixture streams are addressed and recorded. The B100-A
formula has the correct scale, and the current exposure mask happens to include
all 6,048 cells; the final implementation should nevertheless normalize the
full arrays directly and assert that identity so a later mask change cannot
silently alter the estimand. All repairs still require the independent audit.

## Scientific target and scope of inference

The primary target is a **casewise declaration of a post-arrival multiplicative
prey-loss hazard effect**. The declaration statistic is

\[
T=2\max\{0,\ell_{\mathrm{adjusted,free}\ h}
              -\ell_{\mathrm{adjusted},h=1}\},
\]

where both likelihoods use the same 120 training sites and continuously fit the
registered nuisance parameters within their physical bounds. A coarse node
indexes a generating null distribution; it does not fix nuisance parameters in
the fitted pair. The constant-background candidates diagnose omitted spatial
structure. The profiles describe likelihood support. Held-out conditional-prey
scores assess prediction by the already fitted candidates. Neither profiles nor
holdout scores are confidence procedures, model-selection rules, or independent
replicate estimates.

The exact probability claim is deliberately narrower than the scientific
capstone. For an exact-family, on-grid, h=1 case, the declaration probability is
at most .05 over repeated observation and reference generation, conditional on
the fixed map, sampling design, empirical arrival bank and numerical algorithm.
It is not a guarantee conditional on the realised reference tables. It does not
cover B100-A, off-grid nuisance values, effect-size recovery, profile coverage,
or any-error control across the four cases. The B100-A branch is a registered
transfer stress test and must retain that label after reveal.

The four sealed histories are independent draws from the approved mixture, but
four cases cannot estimate power, calibration, coverage, model-selection
performance or robustness rates. Site observations are dependent through
shared spread and landscape fields. The 40 holdout sites form eight dependent
clusters, not 40 replicate landscapes.

## Data-generating and observation processes

The registration fixes the landscape generator, first-valid structural rule,
access design, deterministic exposure score, correlated predator spread,
background hazards, persistent site detection, cohort survival and visit
emissions. This is sufficient to define the exact-family and B100-A generators
provided the sampling constructor is named unambiguously in source and receipt.
The resulting estimand depends on several supplied design assumptions: rho=1,
eta=1, mean prey detection .65, predator detection .65, zero false positives,
complete visits and no recolonisation. A declaration therefore cannot be
generalized to unknown spread, resistance, mean detection, missingness or
recolonisation.

The exact-family normalization makes `mu` the arithmetic mean of the 6,048
cell hazards. For B100-A, the required computation is

\[
r_i=\exp\{\sqrt{\log 2}[.7A_i+\sqrt{.51}G_i]\},\qquad
\lambda_i=\mu r_i/\bar r.
\]

The Gaussian realisation must not be centred or standardized before this
transformation. The final hazard normalization is nevertheless required. The
current `_b100_hazard` instead multiplies `r` by `mu/.002`; because `r` has mean
near one rather than .002, it produces hazards around order one rather than the
registered order of 0.002. The existing test accepts this incorrect scale. The
repair must require the full-map arithmetic mean to equal `mu` to floating-point
tolerance and must retain realised map/sample/training/holdout CVs and
correlations as diagnostics.

The homogeneous expression `1-exp(-60*mu)` is only a reference risk. The actual
heterogeneous map mean is `mean(1-exp(-60*lambda_i))`, which is no greater than
the homogeneous reference by concavity and is generally smaller when hazards
vary. Neither quantity is a sampled-site risk unless evaluated on that target
set.

## Screening, lazy effect tables and failures

At the true on-grid nuisance node, the inclusive 99-reference screen excludes
the node with probability at most .01. If it is retained, declaration implies
that the true node's inclusive 999-reference effect rank is at most .04, an
event with probability at most .04. Their union bounds the declaration
probability by .05. No independence between the observed screen statistic and
the observed effect statistic is needed.

It is also unnecessary to materialize all effect tables before observing the
screen. Lazy construction is valid because the complete address function,
node ordering, reference counts, generator, fitter and combination rule are
frozen first, and the effect streams are independent of observations and screen
reference streams. The retained union selects which preassigned experiments to
retrieve; it cannot select their outcomes. This conclusion would fail if a
node were dropped for cost, a failed reference were replaced, reference counts
were extended after inspection, or a favourable subset of a retained set were
used.

The registered failure policy is appropriately conservative. An invalid shared
screen makes all four cases abstain. A case with a nonfinite observed screen,
empty retained set or invalid observed adjusted pair abstains. A missing,
corrupt or invalid effect table makes every case requiring that node abstain,
while cases not requiring it may proceed. One invalid row makes the entire
fixed-size table unusable. A finite clamped statistic does not override fit
status. Hardware or scheduler interruption instead leaves the frozen work
pending; it can resume from verified checkpoints at the same addresses. It must
not create a partial-reference rank or a final p=1 solely because the complete
union is expensive.

## Map selection, random addresses and provenance

The map rule has two distinct stages. First, search attempts 0--99 only until
the first map and sampling design pass the registered structural criteria.
Second, freeze that map and apply the hazard-box, Gaussian-field, bank and
likelihood qualifications. A second-stage failure is a negative or inconclusive
qualification on the selected map. The current `freeze_public_inputs` catches
both stages in one loop and can continue after a certificate failure. Those
paths must be separated before execution, and the receipt must retain every
failed structural attempt plus the single accepted attempt.

The design identity must also be explicit. `goal001.design.build_design` and
`arc3_design.build_sampling_pair(...)[0]` both produce 120 access-constrained
training and 40 holdout sites, but they do not define the same holdout frame,
site identifiers or random transformation. The registration's reference to a
sampling-pair comparator indicates the latter, while the current source uses
the former. One must be named in registration, source, tests and receipts before
the public seed is evaluated. This choice cannot be changed after seeing map,
bank or fixture outcomes.

The registered SeedSequence address tuples separate public map, sampling, bank,
fixtures, confirmatory screening and confirmatory effects. The implementation
must save and verify all six public fixture streams -- spread, prey loss,
predator visits, site detection, prey visits and background field -- even when
one is unused in an exact-family fixture. Confirmatory screen addresses require
only their three pre-invasion streams; effect addresses require their five full
exact-null streams. The audit should verify the address ranges, node order,
NumPy/bit-generator identity and absence of duplicate emitted uint64 seeds in
the materialized public ledger. Deterministic replay verifies addressing and
serialization, but it is not an independent validation of the biological
generator.

## Numerical qualification and alternatives

The public qualification asks whether the complete fixed numerical method is
operationally stable on eight named histories. It does not estimate operating
rates. The direct empirical-bank reconstruction versus the compressed path is
a technical identity check with absolute tolerances `1e-8` for scores and
`1e-6` for nesting and T. The lattice-dominance check is a lower-bound search
diagnostic, not proof of global optimization.

The K=131,072 bank is primary. Both disjoint K=65,536 halves use alpha=1 and
provide two correlated nested comparisons plus one equal-K realization
contrast. The prespecified gates target the quantities used in scientific
claims: T, centred h/beta profiles, direct generating-value LR and held-out
candidate score contrasts. Every history must pass; averages cannot compensate
for a failure. Keeping MLE and boundary movements descriptive is correct because
h=1 profiles are nonregular and a shallow profile can move its maximizer while
remaining nearly unchanged. Raw likelihood offsets are also descriptive.

The .5 thresholds are prospectively adopted Goal 059 operational tolerances.
They are informed by the programme's prior LR scale, not inherited validation
from a different map or functional. Alpha=1 has different normalized
pseudo-arrival weight at K=65,536 and K=131,072, so the comparison includes
both empirical-bank size and regularization weight. A matched-weight comparison
could separate those mechanisms, and independent equal-K banks could better
measure repeatability, but neither is needed for casewise Monte Carlo validity.
Adding either after seeing these results would create an adaptive study. If a
gate fails, stop before sealing; the result cannot identify whether K=131,072,
the half bank, pseudo-arrival weight or a particular flat history caused the
movement. A separately registered numerical study would be needed.

The central distinction is that the effect test remains a valid Monte Carlo
rank test conditional on any fixed numerical bank when observations and null
references use the same frozen statistic. Bank qualification instead supports
the scientific adequacy and reproducibility of fitted effects, profiles and
predictions. A nested-bank pass cannot establish convergence to an exact
process likelihood or stability of future reference-table tail ranks.

## Required independent audit

Before readiness, an independent script must:

- reconstruct the public map/design/A arrays, site order, bank seeds, row order,
  raw array hashes and both K=65,536 halves without trusting production metadata;
- verify the corrected B100 full-map normalization and replay all eight public
  histories from their saved stream addresses, comparing latent and observed
  arrays bitwise;
- evaluate the direct empirical-bank likelihood at every stored main-fit,
  lattice and profile point for all eight histories and three bank
  representations, without calling the production likelihood, hazard
  normalizer or fitter and without refitting;
- reconstruct T, centred profiles, generating-value LR, held-out pairwise score
  contrasts, all .5 stability predicates, and the final predicate counts from
  stored raw scores;
- independently exercise the frozen 765-node ordering, local-neighbour
  discrepancy, tie-aware ranks, retained sets, four-case union and
  Berger--Boos arithmetic on mechanical arrays, including empty, failed and
  boundary-node cases; and
- bind source, registration, runtime, manifests, inputs and outputs with hashes,
  distinguishing an execution stop, audit failure and scientific stability
  failure.

The auditor should fail closed on missing points, duplicate identities,
nonfinite values, inconsistent site order, wrong profile grids, altered
addresses or an incomplete predicate surface. It should report maximum errors
and every failed history/gate, not only a global pass flag.

## Residual risks and recommendation

After the four blockers are repaired and the independent audit passes, the
design is suitable for the qualified public handoff. The remaining major risks
are weak identification and parameter trade-offs, frequent boundary solutions,
finite-bank approximation, model misspecification in B100-A, and generalization
from one map and four cases. The exact-family rank argument handles nuisance
selection on the registered grid; it does not repair those other limitations.

Independent scientific review materially changes confidence at this gate
because map/design identity, field normalization, stopping semantics and the
failure contract determine what experiment is being run. Review after the
qualified public return should verify the evidence and receipts, but it cannot
turn an operational nested-bank pass into convergence, recovery, power or
misspecification validity.

## Provenance correction and disposition

The preserved development receipt at
`artifacts/goal059_execution/development-preview/provenance_receipt.json`
records a command at 2026-10-04 09:17:18.818 UTC that evaluated production root
2026100403 before this review and before the final registration text was saved.
That old implementation used the Goal 001 design and allowed numerical
certification to participate in map selection. It rejected attempts 0--4 after
their numerical certificate and accepted attempt 5. The retained files contain
the candidate-5 map/design metadata and arrays. No bank, history, panel, fit or
likelihood was produced. The source revision at the event was not recorded, so
the receipt correctly does not claim a retrospective source hash.

Candidate 5 is **not** the registered map and must not be copied into the
qualified package. The final source instead replays root 2026100403 using the
fixed Arc 3 constructor and stops at the first structurally valid candidate;
failure of that candidate's numerical certificate is a terminal negative
qualification. Retaining the already chosen root is more defensible than
choosing a fresh root after seeing the preview: the corrected constructor,
structural-first rule and scientific criteria were fixed independently of the
candidate arrays, and the inferential claim is conditional on the ultimately
fixed map. A new root selected now would itself be an adaptive response. This
disposition requires an explicit registration amendment, permanent binding of
the development receipt, no further map/root/rule discretion, and independent
reconstruction before bank construction.

The preview weakens prospective landscape generality and provenance, even
though it does not by itself invalidate a casewise conditional rank test. The
final report must disclose it. Independent review would materially change
confidence in that disclosure and replay; it would not restore the evidential
status of a never-previewed root.

## Qualification implementation follow-up

Review of the first panel implementation found two additional mismatches that
must be repaired before execution. Its stability gate compared the adjusted
free-h point estimate, whereas the registration requires movement of the
adjusted likelihood-ratio statistic T. It also took the maximum profile
movement over the entire grid and did not evaluate the registered generating-h
and generating-beta profile ordinates. The required calculation uses the union
of nodes where either centred profile has R<=10, plus explicit generating-value
checks, independently for each half versus the full bank. Whole-grid movement
and MLE movement may be reported descriptively but cannot replace those gates.
The completed artifacts must retain raw main-fit, profile and 1,350-point
lattice parameters and scores so the independent direct-bank scorer can
reconstruct every predicate without refitting.

Those panel defects are now repaired in the reviewed source. The producer
records adjusted-T movement, restricts centred-profile comparisons to the
registered union of R<=10 nodes, evaluates generating h in both h profiles and
generating beta in exact-family beta profiles, and passes the eight public
truth rows into those gates. It retains raw main fits, all profile parameters
and scores, held-out site and cluster contributions, and all 1,350 lattice
rows. The public B100 generator now operates on the full 72 x 84 arrays,
asserts that every cell belongs to the exposure normalization domain, and
persists the full hazard field for replay.

The independent auditor is fail-closed and does not import the production
hazard normalizer, likelihood, fitter, public-preparation, qualification or
calibration modules. It reconstructs the structural candidate and exposure;
binds the bank to map/site identities; verifies every bank chunk and four
boundary-spanning rows; replays all eight six-stream public histories bitwise;
uses the Goal 056 direct empirical scorer at every stored main, profile and
lattice point; recomputes T, nesting, profile support, generating-coordinate
and held-out gates; and evaluates the mechanical 765-node screen/union/effect
fixture. The landscape, sampling, spread and Gaussian-field kernels are reused
below the orchestration layer, so their replay checks implementation identity
and provenance rather than independent biological correctness.

Mechanical-root tests now include a complete generate-and-replay round trip for
all eight fixtures and a reproducible terminal numerical failure on the first
structurally accepted map. The focused audit, public, qualification and
calibration tests pass, as do Ruff and mypy on the independent auditor. These
are pre-execution checks; they are not evidence that the production-root map,
bank or public panel will qualify.

**Readiness recommendation:** freeze this final source, registration, runtime,
driver and independent auditor together; run the bounded Linux target
qualification at mechanical root 987654321; then evaluate production root
2026100403 exactly once. A first-structural map certificate failure is a valid
terminal negative qualification and must receive the map-only independent
audit. If the map passes, bank and panel construction may proceed, but public
readiness requires both producer qualification and the complete independent
audit. No sealed generation should follow a missing, partial or negative gate.
With those conditions, no additional independent scientific review is needed
before the public preparation run. Independent review of the resulting
receipts remains material before handoff to Fable because the one-map numerical
and stability outcomes do not exist yet.
