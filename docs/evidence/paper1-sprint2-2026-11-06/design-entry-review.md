# Independent design entry review for Sprint 2

Reviewed by an independent Codex subagent on 6 November 2026, against source
`583c1e3` and the Sprint 1 packet, revised sprint envelope and integrated
protocol. Scope: qualification design, experimental allocation, seed identity,
calibration, cross-validation and comparison scope. This review did not generate
histories, fit models, launch jobs, inspect validation seed files or access
validation outcomes. Numerical implementation review is a separate task.

**Verdict: revise before fresh qualification; training entry is not yet ready.**
The design is substantially more concrete than the earlier proposal. The
remaining issues can be repaired inside Sprint 2 without changing the scientific
question or asking Barry to approve routine choices. A measured compute pilot
on explicitly labelled diagnostic cases can proceed while these are resolved;
its outcomes must not be called untouched qualification if they influence repairs.

## Findings that affect qualification entry

### 1. The map-level t expression is not a reliable population failure bound

Packet lines 343–348 call nine maps the replication units and use
`mean(p_m) + t(.95,8) sd(p_m)/3 <= .05`. Accounting for clustering is right,
but this expression is exactly zero after zero failures and does not supply
nonzero uncertainty for rare failures. It also pools three deliberately
balanced archetypes, rather than nine identically distributed random maps.

A simple counterexample illustrates the problem. If an otherwise permitted
map population has a 6% chance of a map on which every dataset fails, nine
independent maps miss that class with probability `.94^9 = .573`. On that
event the proposed upper bound is zero although the population mean failure
rate is 6%. The extreme construction is not a prediction for this study; it
shows the claimed bound has no general finite-sample validity under its stated
assumptions. Even the exact zero-event bound for a *map-level event* is 28.31%
with nine maps, although that is a different estimand from dataset failure.

**Minimal repair:** explicitly make this a finite-panel computational
acceptance rule and remove any interpretation as a 95% population bound. Freeze
an empirical gate and report every map/archetype/arm denominator and original
failure. Alternatively, if a population failure bound is required, independently
review an actual cluster-aware interval method and its sample requirements
before outcomes. Do not replace clustering with an independent-binomial count
of 162 correlated datasets. The same correction applies to the A/B continuation.
The integrated protocol already calls numerical qualification a finite challenge
suite (lines 263–269), so a finite-panel interpretation is available.

### 2. The supplied bank builder cannot produce the independent comparison bank

`scripts/generate_history.py:184–190` derives every bank solely from the root,
fixed namespace, map spawn key and row number. `build_bank` invokes it without
another identifier (line 201); the CLI has no bank-replicate argument (lines
263–275). A second output directory therefore reproduces the same bank, and
changing bank size merely changes its prefix length. This does not implement
the independent-bank checks required for 18 histories / 54 datasets.

**Minimal repair:** freeze distinct primary/comparison bank identities,
size(s), seed recipes and compression settings, and put these identities and
hashes in the qualification execution manifest. Add a bank-replicate key to
the generator and a bounded seed-level check for disjoint primary/comparison
streams and deterministic regeneration. Do not call a nested prefix an
independent bank. The current CLI default of 131,072 is not an explicit packet
freeze of the bank specification.

### 3. Finish the exact qualification decision specification

The panel now contains 207 arm datasets: 162 base, 18 boundary, 18 enriched and
9 trend; base comprises 54 biological histories on nine maps. This is a
prospective replacement for the integrated protocol's provisional 600-case
challenge (360 base / 240 enriched), not the same panel. The older completed
challenge remains historical evidence. Record the smaller replacement explicitly
and justify its finite-panel scope; do not infer broad per-regime failure control.

Packet lines 320–341 still leave operational ambiguities that can change a gate:

- Are dense/lean and independent-bank comparisons required for all three
  inferential families, or just the spatial family? The new all-family interval
  claims require their set construction to be qualified too.
- Define the common normalisation used for W comparisons, matching of all
  interval components/roots, treatment of full/empty/unavailable sets, and the
  exact calculation of the quoted tangency margin. “Near tangent” cannot become
  an outcome-dependent exemption.
- Specify the finite-difference stencil/step and boundary treatment for the
  free-fit gradient check. It must operate at h=1 and sigma/detection boundaries.
- Give boundary/enriched failures an explicit consequence. “Descriptive” and
  “trigger diagnosis” must not allow a newly demonstrated procedure defect to
  disappear when the base empirical gate passes. If a repair changes the
  procedure, follow the reviewed fresh-panel branch.
- Freeze the consequences of the exhaustive-audit margin failure, including
  whether widening triggers fresh qualification and which previous outputs
  become diagnostic. The 18-dataset audit subset measures a finite subset; it
  cannot establish that all omitted locations have bounded gains.

These items should be executable in a qualification reducer before outcomes,
with small fabricated receipts exercising pass, fail and unavailable cases.
They do not require new general-purpose workflow infrastructure.

## Findings that affect training or the final packet

### 4. The interval method used to choose cutoffs is still unspecified

Packet lines 244–249 freeze grids and “one-sided 95% upper bounds”, but do not
say how those bounds are constructed. The integrated protocol gives the target,
equal-map weighting and zero-event requirement, not a ready-made estimator.
A map-level t interval, pooled-binomial interval, cluster bootstrap and
hierarchical model can select different C_D/C_I values. A zero-event correction
must not be invented after seeing which cutoff would pass.

**Minimal repair before training:** freeze and independently review the
stratum-level estimator/UCB, map and within-map uncertainty, zero-event handling,
missing/failure treatment and numerical tie rules. Explicitly apply interval
eligibility at all six truths, all declared strata and each comparator family.
The smallest eligible common declaration cutoff already maximises every
stratum's declaration power for nested threshold rules; state this relation to
the protocol's equal-stratum h=3 objective and retain the objective as a reported
quantity. R1 is evaluated, never trained (packet line 251's wording should be
corrected).

The 200/100 training allocation is an explicit initial allocation and retains
all six truths. Its 2,000-null-history binomial SE of 0.00487 ignores map
variation, as the packet acknowledges, so “enough to separate .04 from .05”
is not a guaranteed design property. Per-map SE at p=.05 and 200 histories is
0.01541. These are not violations of the *validation* precision rule by
themselves: development and validation counts have different roles. However,
no further intermediate-truth reduction is accepted by this review. Keep the
current counts unless a prospective, independently reviewed allocation amendment
preserves the six-truth interval claim; h=1/3 alone is not the final experiment.

### 5. Complete the comparison and forecasting specification

The declaration-plus-interval comparator scope is now clear and is supported
in principle by returning all three profiles. Whole-map ten-fold CV, holding
one map per archetype out per fold, and reselecting cutoffs/refitting forecasts
within folds correctly prevents the earlier cutoff leakage.

Before running the corresponding evaluation, freeze:

- the exact fold map assignment, forecast targets, model class, preprocessing,
  any model-selection steps, map weights and scoring metrics; all fitting or
  tuning must occur inside the training fold;
- the temporal-stress map/cell allocation for development and eventual
  validation (the qualification trend rows are not the paper's full robustness
  experiment), while keeping it outside stationary cutoff training;
- the complete-data mechanism-reference outputs required for every cell by the
  integrated protocol; the new entry point's fitted-family outputs are not
  those references;
- the bootstrap audit map-selection rule and actual selected development
  identities before outcomes, preserving the declared h=1/3 coverage/declaration
  distinction and three validation maps per archetype at the later freeze.

The measured-cost bootstrap amendment trigger is an appropriate decision point,
not permission to omit the audit. The cost projection must include separate
h=3 truth-constrained coverage fits, plus the h=1 declaration fits, and the
actual early-stopping distribution. The bootstrap reduction proposal needs
independent review before the affected main outcomes.

Before opening validation, the planned variance decomposition, one-sided 90%
upper planning bound on between-map variance, map-level intervals including
zero events, counts and forecast rules must be executable and reconciled.
Keep the protocol's absolute-rate and paired-contrast precision targets, minimum
maps and all six coverage truths. No cost ceiling replaces those targets.

## Accepted aspects and narrowly qualified interpretation

- Qualification map role 2 and development role 1 use distinct map spawn keys;
  qualification histories use namespace 5 and proposed training uses 4. Within
  the read qualification panel all dataset IDs are unique. The 162 base rows
  contain 54 distinct history addresses, with A/B/C sharing each address as
  intended. All six backgrounds have nine base histories overall and nine arm
  datasets per archetype. The panel contains 54 independent-bank flagged rows,
  18 exhaustive-audit rows and nine integration rows.
- The generator keys spread, loss thresholds, detection, visits and G by history
  address, not background, supporting background/arm pairing. Full cohort
  simulation begins at day −60. The arm builder explicitly checks 120/260 sites,
  shared holdout exclusion, absence of pre-period prey observations in B/C,
  and predator-network masking in the added C sites.
- The new reach-threshold T is an explicit planning-only nonlinear confounding
  stress, with a=1 and a frozen temporal trend. It should be described as a
  reviewed change of intervention. Spearman correlation 1 between planning
  arrival and A does **not** imply that the residual from *linear* regression
  of raw arrival on [1,A] is numerical noise; a monotone nonlinear transform
  can have a substantial residual. Remove that mathematical justification in
  packet lines 203–209 unless the actual intended transformed arrival surface
  is specified and its residual is measured. This does not invalidate the
  threshold intervention itself.
- Failed fits remain non-declarations and noncoverage; execution losses may be
  retried with unchanged identity. Explicitly versioned repairs with preserved
  failed attempts are distinct from silently retrying a scientific outcome.
- Removing tight replay is not accepted automatically. It may be a defensible
  production simplification if a reviewed candidate retains qualified peak,
  component and boundary discovery for all cutoff values and all families.
  Qualification must compare the exact final production procedure against a
  stronger reference; dropping replay from both sides would weaken the check.
- Protected validation files/outcomes were not read. No evidence in this review
  claims validation readiness or population error-rate control.

## Checks performed

Read the packet, revised sprint envelope, relevant integrated-protocol sections,
qualification generator/manifest, map/history generation paths, background
family and existing generator tests. Parsed the qualification manifest and
recomputed counts, unique IDs, history sharing, background balance and flagged
subset sizes. Recomputed the simple uncertainty examples above. No simulation,
model fit, bank build or fresh qualification outcome was run. Only this review
file was written.

## Explicit candidate amendments requested by the parent

These are proposals for the parent's integrated amendment and subsequent
independent review, not an already frozen procedure.

### Finite-panel qualification

Retain the existing 207 dataset identities and all comparison tolerances, after
making the missing comparison definitions in finding 3 explicit. Retain tight
replay and the complete eight-cutoff grid. Define each base dataset's indicator
as one if *any* required family/search/bank/gradient check fails or is numerically
unavailable. Apply the existing map-score expression and 0.25 map cap only as a
**finite-panel acceptance score**, explicitly not as a confidence bound or an
estimated population failure guarantee. Publish the whole map-by-arm and
archetype breakdown, not only pass/fail. Scientific failures found in the
boundary/enriched checks require a recorded diagnosis and independently reviewed
disposition before promotion; they are not added to or diluted in the base rate.
Retain the already declared A/B continuation only when every base failure is C,
recalculating the same score with each map's twelve A/B datasets. No C training
or three-arm claim follows that continuation. A method repair invalidates the
relevant panel as untouched qualification and invokes the fresh-panel rule.
No criterion may be relaxed after qualification outcomes.

### An explicit conservative training UCB, and its consequence

A simple distribution-free option for each fixed family × archetype ×
background × mu × arm × truth × candidate cutoff is:

1. Define X_m as that map's observed error fraction over its frozen histories;
   for declaration use h=1 false declarations, and for intervals use truth
   noncoverage with every scientific failure counted as noncoverage. Execution
   errors leave the map incomplete until reconciled. Use the same history
   denominator for every cutoff and retain failed procedures in it.
2. Set pbar = mean_m X_m with equal weights over the M independent maps in
   the archetype. Within-map observations need not be independent for this
   bounded-map argument; the registered random generation must still make
   X_m an unbiased sample proportion of its map's history distribution.
3. Define U as the largest q in [pbar,1] satisfying
   `M * kl(pbar,q) <= log(20)`, where
   `kl(p,q)=p log(p/q)+(1-p)log((1-p)/(1-q))`.
   Solve the monotone scalar equation deterministically. Endpoint rules:
   pbar=0 gives `U=1-0.05^(1/M)`; pbar=1 gives U=1.
4. Require U <= .05 separately in every claimed error stratum (and every truth
   for intervals). Select the smallest eligible grid value, separately by
   inferential family and rule type. Recompute inside every CV training fold.
   If none qualifies, report no qualified rule; do not report the largest
   cutoff as if it had passed. R1 remains a fixed descriptive benchmark.

For independent [0,1]-valued map fractions, the Bernoulli exponential-moment
bound and Chernoff inversion give a one-sided 95% bound on their common
map-population mean. This includes both map and history sampling variation;
it does not incorrectly use M times histories as the independent sample size.
The bound is pointwise in each predeclared candidate/stratum, not simultaneous
and not a post-selection guarantee. These limitations match the protocol's
stated distinction between training allowance and untouched validation.

**This option exposes a serious feasibility limitation:** with M=10 maps,
even pbar=0 gives U=0.258866, so the existing training design can never certify
U<=.05 by this method. At least 59 maps per archetype are needed even at zero
errors (U=0.049508); at pbar=.04 this particular conservative bound requires
2,659 maps. Within-map replication cannot solve that limitation. The worst-case
rare-all-failing-map construction explains why a valid distribution-free bound
cannot simply be patched to near zero with ten maps.

Therefore do not mechanically install this estimator and launch a training
campaign whose failure is predetermined. Before training choose and record one
of: (a) a prospectively enlarged map design with an independently reviewed
finite-sample method and measured feasible cost; (b) explicit, scientifically
justified distributional assumptions supporting a less conservative approximate
map-level interval, independently tested before use; or (c) a documented design
feasibility failure with the preserved six-truth study proposed for revision.
I do not independently accept a t interval plus a cosmetic zero-event correction
as satisfying (b). Keep all six truths and the current history counts until an
actual amendment is accepted; no intermediate-truth reduction or removal of
tight replay is recommended here.

### Independent disposition of the parent's qualification amendment

The parent proposed retaining the original empirical map score and map cap,
explicitly discarding its population-confidence interpretation; keeping all 207
cases with separate denominators; treating every topology mismatch as failure or
indeterminate rather than applying an undefined tangency waiver; and using
primary/comparison bank replicates 0/1, each of size 131,072, compression order
192 and unchanged pseudo-mass. Full replay and all six training truths remain.

**Accepted as a prospective finite-panel qualification design**, subject to the
execution manifest spelling out the other comparison definitions listed above
and the reducer classing an indeterminate required check as non-passing. The
conservative topology rule is scientifically defensible; its subsequent
relaxation would be a recorded post-outcome amendment and require review.
Separate denominators must not hide a demonstrated boundary/enriched procedure
defect. The acceptance gives no training-rule or validation-readiness approval.

### UCB proof and primary source

For a map fraction X in [0,1] and any real t, convexity gives
`exp(tX) <= 1-X+X exp(t)`. Therefore for independent map fractions with mean
q, `E exp(t sum X_m) <= (1-q+q exp(t))^M`. Markov's inequality with t<0
and optimisation over t yields
`P(pbar <= x) <= exp[-M kl(x,q)]` for x<q. Inverting this lower-tail bound
is the UCB above. This proof also covers independent nonidentically distributed
maps when q denotes their mean expectation, by concavity of the logarithm;
it does not remove the requirement to sample the declared map population.

The primary reference for bounded-sum concentration is
[Hoeffding (1963), Probability Inequalities for Sums of Bounded Random Variables](https://www.tandfonline.com/doi/abs/10.1080/01621459.1963.10500830),
with an [original-paper scan](https://www.cs.rpi.edu/academics/courses/spring06/random/hoefding.pdf).
The manuscript identifier is `10.1080/01621459.1963.10500830`. The map-level
application and numerical feasibility calculations here are this review's
explicit derivation, not a claim made by that paper about this experiment.

## Final prospective design disposition

Reviewed the integrated amendment in `docs/paper1-sprint2-entry-2026-11-06.md`
at SHA-256 `15b4447f3cbf6d7b92c0b5b75c97a81d10c3ac7f42381a9250b1d03720f257c7`.
**Accepted for the proposed finite-panel qualification, before fresh outcomes.**
The document retains full replay and all six truths, explicitly replaces the
population failure-bound interpretation, defines the bank identities, compares
all inferential families with exact union anchors, removes the undefined
tangency waiver, freezes two raw-gradient step sizes with boundary stencils,
and keeps integration descriptive. It requires a historical diagnostic pilot
before fresh qualification and keeps the separate training/validation gates closed.

The geometry-only script and its saved JSON support the corrected raw-arrival
residual statement for the three named development maps. I inspected those
source/results; I did not rerun the geometry calculation or generalise it to
unexamined maps. The chosen threshold intervention remains an explicit
prospective stress, rather than a claimed mathematical necessity.

Independently inspected `scripts/screen_sprint2_importance.py` at SHA-256
`16a69b50531c2aec5a7c034912258f481333bd4d0e9e8a5e096e180983df2114`.
Its reuse of the fixed-outer importance machinery, free/3.84-root anchors,
262,144 cap, two streams and descriptive-only receipts is appropriate. Input,
source and child-receipt checks remain outside the numerical-unavailability
handler; OS/memory errors propagate. One narrow requested producer repair is
to reject absent/unknown parent failure classes instead of describing every
non-resolved string as a scientific failure. The qualification reducer already
requires a recognised terminal scientific class for that disposition.

At the parent's request I implemented `scripts/summarise_sprint2_qualification.py`
and `tests/test_sprint2_qualification.py`. This is implementation work, not an
independent audit of my own reducer. Its header specifies the exact indexed
evidence interfaces. Thirty-two fabricated-evidence checks, Ruff and strict
mypy pass. No histories, numerical fits or integration screens were executed.
The parent retains implementation integration/review responsibility.

## Historical diagnostic replay provenance audit

Independently checked `diagnostic-replay.json` at SHA-256
`967bd68a41f2a71050741df7d1c74e215cbaad717fbf24270ac04a63b8fabe44`
and its ignored local receipts under `artifacts/sprint2/entry-replay-20261106`.
The recorded patch hash matches; applying that patch to the named base
`583c1e3d9f012a90db57cbf11cbe6ea4d1b041cd` reconstructs all 115 recorded
source hashes exactly. Those hashes agree with the saved source snapshot. Both
parent receipt hashes, their child search-receipt hashes and evaluation-stream
hashes verify. Each receipt's 121 input/source hashes verifies against the
reconstructed source or the retained historical inputs; the published summary
preserves the same hashes with repository-relative paths.

Both 120-site historical B-arm cases report `resolved`, with all three families
and all eight cutoff sets available, tight replay enabled, and zero recorded
envelope-guard events. Recorded wall times are 956.922 and 920.468 seconds; CPU
times are 955.581 and 919.257 seconds. These are receipt measurements from two
concurrent local processes, not a target-host resource projection. The launch
summary records exit code zero for both. Source snapshots and receipt hashes
are consistent with the runner's no-source-change assertion; this audit did
not observe execution continuously or rerun either fit.

The only current difference among the 115 recorded source files is
`fit_dataset.py`: reduced-profile serialization fields, required-input metadata
and type annotations, matching the stated post-replay changes. The replay
therefore identifies its exact historical candidate and does not claim to test
the final source verbatim. **Accepted as historical diagnostic evidence only.**
It supplies no fresh qualification, independent-bank comparison, population
calibration, globality proof, 260-site benchmark or cluster pilot. No histories,
fits, source edits or tests were run for this provenance audit.
