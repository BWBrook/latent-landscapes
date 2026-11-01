# Paper 1: endpoint, bank and continuous-profile qualification

1 November 2026. Numerical development advancing charter pillars 3 and 4 and
the broader model-comparison programme. Barry authorised the h=30 repair,
independent-bank sensitivity and continuous-profile qualification. Goal 062
remains closed. This record continues the
[direct-profile development](paper1-direct-profile-development-2026-10-31.md).

## Prospective design and independent review

Claude's Correspondence message 2754 accepts the direct evaluator and completed
meshes and requests bank sensitivity. An independent methodological subagent
reviewed the following bounded design before fresh-bank results or refined
roots were examined. The two fixed archived histories (B_H3 cell 09 and H3
cell 04, replicate 000) retain 120 training sites, the original observation
calendars, covariance range, all nuisance bounds and both variance families.
Forty holdout sites are excluded. No new biological histories or outcome truth
files are used. The prior 35-node meshes are development evidence, not a
registered validation sample.

For each bank b, C_b(h) is the larger of the positive-spatial-variance and
exact-zero criteria; M_b is the selected free maximum over h in [1,30], and
W_b(h)=2(M_b-C_b(h)). Level sets W_b(h)<=c use fixed diagnostic levels
c={1,3.84,6.63}. These numbers carry **no nominal confidence or coverage claim**.

The original bank B0 has K=131072 rows. Fresh A and B use disjoint row
addresses K:2K and 2K:3K under the unchanged original seed rule
`SeedSequence([root,59,3,row]).generate_state(1,dtype=uint64)[0]`.
AB pools A and B at 2K. Public map/site inputs and the spread law remain fixed.
Equal-K comparisons are B0/A, B0/B and A/B; nested comparisons are A/AB and
B/AB. All seed addresses, seed values, input/source identities and row/site
ordering are retained. Original rows are not regenerated as a supposedly
independent bank.

## Numerical gates

- Every required family-point must have an eligible finite fit; failed
  candidates are retained. Both variance families must resolve,
  under the unchanged main projected-gradient threshold 1e-3. A retained
  unresolved candidate or fixed profile point above its selected family free
  maximum by more than 1e-4 forces refitting or an indeterminate result.
- B0 adds all 34 logarithmic midpoints to the existing 35-node mesh. Detected
  maxima, family switches and all cutoff crossings are refined. Fresh banks
  start from the same 35-node mesh, with default and neighbouring nuisance
  starts. Both families are refit at every new h.
- Fresh-bank midpoint checks cover intervals with a peak, cutoff crossing,
  family switch, nuisance-bound transition, branch disagreement above 1e-4
  criterion units, changed topology, or an endpoint within 0.25 LR of a cutoff
  without a crossing. Refinement reaches at least the baseline midpoint
  spacing in triggered intervals. All selected free peaks are reoptimised.
- Crossings are bracketed in log(h), then solved with Brent tolerance 1e-4.
  The free maxima and roots receive a separate tighter replay with projected
  gradient <=1e-4 and root tolerance 1e-5. Each root must have |W-c|<=.01;
  standard and tighter evaluations at the **same h** must differ in W by at
  most .01; corresponding log roots must differ by at most .005. Component
  counts and h-domain contacts must agree. Family differences within 1e-4
  criterion units are numerical ties, not ownership failures.
- The tighter replay includes the complete discovery mesh, not just the root
  brackets, plus all refined roots/free/switch locations. B0 additionally
  replays archived parameters at a 1e-8 criterion tolerance. Reoptimisation can
  improve an archived fit that only met the 1e-3 gradient gate: such improvements
  are reported separately, cannot reduce the best criterion by more than 1e-8,
  and must move W by at most .01 for the bounded replay comparison.
- Root calculations retain every detected component, including singleton,
  empty, full and unavailable sets. A failed bracket or fit never becomes an
  empty set. Mesh refinement supports finite-resolution topology only; it
  cannot prove absence of arbitrarily narrow unseen features or global modes.
- Each history/bank may use up to 160 distinct standard h points and 160
  tighter replay points. Exhaustion is indeterminate, not permission to omit
  a crossing. These are generous execution guards, not statistical targets;
  the 10–15-fit costing proposal is not adopted as a qualification algorithm.

## Bank sensitivity gates and pseudo mass

Apply the following casewise to all listed comparisons, without averaging
across the two histories: maximum common-anchor |Delta W|<=.10, every finite
root |Delta log(h)|<=.05, and identical component counts and h-domain contacts.
Movement in the fitted h is descriptive. Failure is a bank-sensitivity result;
it does not justify changing bounds, histories or thresholds after inspection.
Two histories cannot estimate the distribution of bank errors.

K-to-2K comparisons change both sampled arrivals and the total pseudo-arrival
mass, from 7/(K+7) to 7/(2K+7). Duplicate every empirical row of A to construct
Adup: its empirical distribution is unchanged, but it has nominal size 2K and
the same seven pseudo-arrivals. Resolve latent modes under Adup at A's fitted
free/anchor/root nuisance points. A centred LR-scale perturbation above .05,
projected gradient above 1e-3 or material non-tied family-ownership reversal
triggers a full Adup profile refit. Both family free optima and both family
parameter vectors at standard anchors and final tightly refined roots are
replayed. Otherwise this
is explicitly a fixed-fit pseudo-mass perturbation, not an optimised-profile
certificate. Adup/AB shares nominal K and pseudo mass.

Report h=1/30 contact as h-domain truncation, and nuisance-bound contact
separately at free maxima, crossings and sampled points inside each level set.
Bound contact alone does not establish that the bound determines an endpoint.
No nuisance bound is widened.

For the outer negative criterion, report q=g' H^-1 g when the reduced Hessian
is positive definite and adequately conditioned. The local estimated criterion
deficit is q/2, and its one-fit LR-scale contribution is q. This is a local
quadratic diagnostic, not an error bound or replacement for projected-gradient
qualification. It is distinct from the latent-mode Newton decrement.
The reduced Hessian must be finite, positive definite, have condition number
at most 1e10 and relative asymmetry at most .01 before symmetrisation. Results
at finite-difference scales 1e-4 and 3e-5 are reported together; unavailable
diagnostics do not imply that a finite-difference Hessian passed qualification.

## Endpoint repair and initial checks

The free log-effect is checked against [0,log(30)] before exponentiation.
The valid upper endpoint is clamped to h=30 to remove the floating-point
overshoot. Truly out-of-domain coordinates still fail, including adjacent
floating-point values and large positive inputs. Both variance families retain
their original parameter vectors and all KKT/optimiser tolerances.
The focused endpoint suite passes 37 tests plus Ruff and strict scoped mypy.
Independent audit accepts the repair.

Claude's x=8.58e55 question refers to the rejected **uncapped** Newton version,
source 888ab4d9. The adopted per-step cap limits each proposed Newton increment,
not accumulated log hazard or unchanged L-BFGS fallback. Adopted B_H3/H3 mesh
diagnostics still reach x=1.52e6/600.31, handled by raw evaluation. Independent
audit found no accepted nonfinite criteria, domain errors or final
positive-definiteness failures in those receipts. The old failed version remains
preserved and is not relabelled as the adopted implementation.

## Execution and scope

A local bank smoke test precedes the resource choice. BLAS threads are limited
to one; independent histories can run in separate processes within Mac mini
memory/CPU capacity. Receipts preserve failures, source hashes and partial
progress. Execution findings will be added below without revising these gates.

The original public loader failed before generating any bank: reconstructing
the frozen exposure differed by at most 8.88e-16 from the stored values.
All frozen files, seed identities and 17 reconstructed arrival-generating
arrays remained byte-identical. Independent review accepted an arrival-only
loader that validates those arrays and all frozen file hashes, without
reconstructing the exposure/setup that arrival simulation does not use.
It does not relax the original loader or its scientific checks. The exact
floating-point operation responsible for the exposure difference is not known.

The repaired 256-row smoke (two workers) completed in 5.73 seconds. Independent
replay of original rows 0, 1 and 131071 reproduced all 480 arrival values exactly.
All 393216 seed values across B0/A/B were unique; pairwise intersections were
empty. Fresh 2K generation uses four local workers and 256-row chunks, alongside
at most two single-thread profile processes. The smoke suggests roughly 49
minutes for generation; this is a forecast, not the completed runtime.

The proposed Arm-B pre-period ablation is deferred: it changes observation
design and asks a separate mechanism question. The observed h–sigma trade-off
is consistent with depletion-mediated confounding but does not establish its
cause. A later ablation needs an explicit masking and contrast specification.
Kunanyi throughput, 260-site behaviour, the 600-case challenge suite,
higher-accuracy integration and calibration remain separate work.
