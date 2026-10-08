# Goal 054 independent pre-generation methods review

29 September 2026. Charter Pillar 4 / Roadmap Arc 4.

## 1. Decisive findings and required specifications

**Recommendation: proceed after four registration-level clarifications.** The
primary finite-grid max-p rule is valid for an exact on-grid null, conditional
on the fixed landscape, survey, known nuisance quantities and K131072/alpha1
analysis bank. The proposed Berger--Boos rule is also valid on that grid. I
found no reason to change the 999 reference blocks per beta node, 1,000 fresh
evaluation blocks, eight evaluation cells or fixed 2,000 bootstrap draws.

The scientific target is an operating rule for declaring `h>1`, not an improved
point estimator or a confidence set. Its primary estimands are the long-run
declaration probabilities of the adjusted and constant rules over fresh full
histories, conditional on this one fixed landscape, 120/40 site design, survey
schedule and analysis bank. At exact `h=1` cells these are false-declaration
rates; at `h=3` they are setting-specific sensitivities. Under B100-A and the
new threshold-aligned generator they are robustness operating rates without a
nominal size guarantee. The paired differences compare two declared analyses
on the same histories. They do not identify a universally preferable model.

Before generation, freeze these four details:

1. Define the nonlinear latent field exactly as
   `z = 0.70 * I_std + sqrt(0.51) * G`, where `I_std` is the full-map,
   population-SD-standardised indicator and `G` is the unchanged stationary
   Gaussian draw from the existing sampler. Then use
   `lambda = 0.002 * exp(sqrt(log(2)) * z) / map_mean(exp(sqrt(log(2)) * z))`.
   Omitting `0.70` from the indicator term would increase the intended aligned
   component and change the comparison. Do not centre, scale or orthogonalise
   `G`; it is distributionally generated without reference to A, but a realised
   map need not have zero mean, unit spatial SD or zero correlation with A.
2. Freeze the top-third boundary rule. On the live 6,048-cell A map, the
   empirical two-thirds quantile is `0.43311018285380926` and eight cells tie at
   it. `A > q` selects 2,015 cells (33.3168%); `A >= q` selects 2,023 (33.4491%).
   Use `A > q` so equal-A cells remain in the same class, record the realised
   fraction, and standardise that binary map over all 6,048 cells. Do not split
   the tie by cell position merely to force exactly 2,016 cells.
3. Freeze inclusive upper-tail comparisons and a one-sided numerical tolerance:
   count a reference as at least as extreme whenever
   `T_ref >= T_obs - tolerance`, and analogously for D. This can only enlarge a
   tail and preserves conservatism. Use the same frozen tolerance in production,
   reconstruction and bootstrap code.
4. Define each declaration-conditioned error summary, its numerator and its
   denominator before outcomes. Always report the declaration count. If a cell
   or bootstrap draw has no declarations, the conditional summary is undefined,
   not zero. The joint rate of declaration and at least 1.5-fold point error is
   the more stable operational summary; conditional errors remain selected-subset
   descriptions.

The nonlinear pair is a useful bounded mismatch stress, but its interpretation
must be narrow. Sharing G, process, prey-event and detection streams gives a
precise paired contrast between smooth-A and threshold-A generators. The
contrast still combines shape, realised CV and realised alignment after
whole-map normalisation. It therefore tests sensitivity to this particular
threshold-shaped aligned background, not “nonlinearity” generally and not a
CV-matched intervention. Report actual map, sampled, training and holdout CVs
and correlations with A, the threshold indicator, exposure time and arrival.

## 2. Evidence, probability argument and model comparisons

The data-generating process draws one spread history, one prey-event threshold
per site, detection uniforms and one G field per paired block. These streams are
shared across the cells in that block. Background hazard and h then determine
prey extirpation, followed by the fixed two-visit detection process. The 160
sites and their spatial and temporal observations are dependent components of
one history; the block, not a site, is the replication unit. Independent blocks
are the Monte Carlo replicates. Training observations alone determine T and D;
the 40 holdout sites remain prediction evidence and cannot select a declaration,
grid, cutoff or model.

For reference node `j`, let

`T = 2 * {max_(h,beta) ell(h,beta) - max_beta ell(1,beta)}`.

Under an exact null generated at the on-grid true node `j*`, the evaluation T
and 999 reference T values at `j*` are exchangeable conditional on the fixed
bank and other fixed design objects. Consequently

`p_j(T) = {1 + number(T_ref,j >= T)} / 1000`

is super-uniform at `j*`. The primary rule rejects only if
`max_j p_j(T) <= .05`, which implies `p_j*(T) <= .05`; hence its size is at most
.05, averaging jointly over the frozen-table generation and a fresh evaluation
history. Pairing reference streams across beta nodes creates dependence between
tables but does not alter any node's marginal exchangeability. This argument is
not a 5% guarantee conditional on the realised reference table.

With 999 references and inclusive ties, the primary nodewise event is a strict
exceedance of the 950th ascending reference order statistic. The primary rule
therefore has an effective cutoff equal to the largest nodewise cutoff, adjusted
by the frozen tolerance. Save the full 81-node cutoff curve and attribute every
node tied for its maximum. Edge attribution matters: a beta-edge node can validly
set the cutoff for the declared finite grid, but it warns that the composite
null beyond `[-2,2]` has not been covered. Do not expand the grid after seeing
that diagnostic.

The Berger--Boos secondary is defensible as specified. For each node use

`D_j = 2 * {max_beta ell(1,beta) - ell(1,beta_j)}`,

`q_j = {1 + number(D_ref,j >= D_obs,j)} / 1000`, and
`C = {j: q_j > .01}`. The true node is omitted from C with probability at most
.01. If `p_BB <= alpha` and the true node is in C, then its T p-value is at most
`alpha - .01`; a union bound gives size at most alpha. This proof needs only
the marginal super-uniformity of p and q, so using the same paired reference
histories for T and D is valid. Set `p_BB=1` when C is empty. Inclusive ties and
the frozen conservative tolerance apply to both p and q. At alpha .05, the
candidate-node T threshold corresponds to strict exceedance of the 960th
ascending reference order statistic because `p_j <= .04` is required.

The constant comparator

`T_constant = 2 * {max_h ell(h,0) - ell(1,0)}`

has the same exchangeability argument only at beta=0. Reusing the paired beta0
reference histories is preferable because it preserves the within-history
comparison. Its rates under beta=.60 or either mismatch field measure the cost
of using a wrong constant-background analysis; they are not calibrated power or
size. The fixed 2.71 and 3.84 T thresholds are useful descriptive benchmarks
for the one-sided-boundary and conventional chi-square heuristics, respectively,
but neither has the finite-sample guarantee of the Monte Carlo rules here.

Goal 053 supplies direct evidence for weak h--beta separation: free-beta h
error substantially exceeded known-beta error, lower h-profile contact was
common, and coarse-grid h shifts occurred along nearly flat likelihood geometry.
Calibration can repair the declaration's false-positive operating rate under
the assumed finite-grid family; it cannot remove this confounding, sharpen point
recovery or establish structural identifiability. The h=3 rates and the
distribution of T, fitted h/beta and boundary contacts will discriminate useful
conservatism from a rule that controls size by having little sensitivity.

## 3. Verification, diagnostics and uncertainty analysis

The pre-production qualification should establish the following with small,
reproducible checks before the 80,919-reference and 8,000-evaluation generation:

- Reproduce every original Goal 053 cell exactly under common seeds after the
  two nonlinear cells are added. Check that all old process, G and observation
  streams are unchanged and that reference, evaluation, timing, smoke, bootstrap
  and bank roots are mutually disjoint.
- Verify the threshold-map checksum, strict quantile rule, centred/unit-SD
  indicator, unchanged G draw, exact map hazard mean 0.002, finite positive
  hazards, and saved realised CV/alignment diagnostics. Do not impose an
  after-the-fact CV or correlation acceptance target.
- On crafted score arrays, reconstruct T, every D_j, max-p, C and p_BB by an
  independent path. Include exact ties, near ties on both sides of the tolerance,
  empty/full C, beta-edge maxima and multiple cutoff-setting nodes. Check the
  rank-950 primary and rank-960 Berger--Boos identities explicitly.
- On at least one exact h=1 smoke history per selected interior and boundary beta
  node, compare independently extracted full-surface maxima with the stored T
  and D values. Verify `T>=0`, `D_j>=0` up to frozen roundoff, exact h=1 nesting,
  beta=.60 node lookup, complete 181-by-81 coverage and deterministic tie-breaking.
- Keep reference and evaluation histories opaque to synthesis until coverage,
  shapes, finite scores, manifests and hashes pass. Holdout scores may be
  calculated in the same run but must not enter T, D, C or either declaration.

The fixed-table bootstrap should resample the 1,000 evaluation block indices,
with one weight vector shared across all eight cells and both fitted analyses,
while leaving reference tables fixed. The calibration-aware bootstrap should,
for each of the same 2,000 registered draws, independently resample the 999
reference block indices and the 1,000 evaluation block indices. A single
reference weight vector must be shared across all 81 generating nodes, T and D,
the adjusted rules and the beta0 constant comparator. Recompute p-values,
Berger--Boos sets, cutoff-setting nodes, declarations and all paired summaries
inside each draw. These percentile intervals estimate simulation-summary
uncertainty from the empirical reference/evaluation distributions; they do not
strengthen the exact finite-grid proof or describe new landscapes.

Store reduced reference evidence sufficient for exact reconstruction: T and D
for every node/block, beta0 constant T, opaque IDs, seed bindings and numerical
flags. Full reference score rectangles are not scientifically necessary once an
independent reduction replay has passed. Streaming by fitted-beta row with
resumable, hash-bound accumulators avoids retaining roughly 9.5 GB of reference
training surfaces in memory and permits failure recovery without changing the
registered sample. Preserve raw observations and provenance regardless of this
reduction.

Report, without multiplicity-adjusted scientific claims, the primary max-p
rates, constant-rule paired contrasts, secondary Berger--Boos rates, 2.71/3.84
benchmark rates, cutoff curve and boundary attribution, h/beta boundary fits,
point errors, declaration-and-error joint rates, declaration-conditioned error
with denominators, and held-out prediction. Retain all eight cells and all
failures. The primary decision remains the single max-p rule; secondary screens
must not be combined into an either-test omnibus.

## 4. Residual risks and final recommendation

The exact guarantee stops at the 81 beta nodes. It does not cover off-grid beta,
unknown detection or process nuisance quantities, integration-bank variation,
another survey, another landscape or either residual-field generator. One fixed
landscape and one fixed site design also preclude population-level landscape
generality. Spatial and temporal dependence are handled within histories and by
whole-block resampling, but the experiment cannot separate all causes of weak
information. Boundary fits can reveal grid truncation without repairing it.

The max-p rule may be severely conservative because it protects against the
worst of 81 nuisance nodes. Berger--Boos may recover sensitivity, but its
data-dependent confidence set adds a second Monte Carlo tail and remains
finite-grid. The mismatch pairs address two aligned shapes sharing one G draw;
they do not span plausible residual fields. Bootstrap tails based on 999
references are useful uncertainty diagnostics, not a replacement for the
plus-one proof. Conditional error summaries remain vulnerable to sparse and
selected denominators.

Subject to the four specifications above and successful qualification, fresh
generation is scientifically justified. A successful result would support an
effect-declaration rule only for this conditional finite-grid experiment; poor
sensitivity, excess mismatch declarations or a boundary-set cutoff are valid
negative results and should prompt a new scientific decision rather than
retuning. This independent pre-generation review materially increases confidence
in the design. A second pre-generation review is unlikely to change the decision
once the required controls pass, but an independent post-generation reconstruction
of ranks, Berger--Boos sets, bootstrap recomputation and manuscript claims would
materially strengthen confidence in the completed result.
