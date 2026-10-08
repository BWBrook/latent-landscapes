# Goal 050 final independent review

21 September 2026 (Hobart). **PASS: freeze the registered implementation and
report the result as a conservative known-nuisance adequacy baseline.** The
production and synthesis evidence support the numerical results in
[synthesis.md](synthesis.md). They do not establish misspecification power,
biological adequacy, or a cause for Goal 049's realised 7.4% null exclusion.

## Independent checks

Production exited zero after 9,706 wrapper seconds. Its contract fingerprint
recomputes exactly; all 73 bound source/registration hashes and all four phase
file hashes match. Saved arrays have the registered shapes, types and finite
values. The original calibration and evaluation LR profiles, fitted nodes,
opaque IDs and evaluation held-out joint scores replayed with maximum difference
zero. All registered stream-separation controls passed. Peak production memory
was 1,881,336 KiB, or 1.79 GiB.

I independently reconstructed the point estimates from the Goal 049 profiles
and Goal 050 saved scores, without drawing or fitting anything. Detector
rejections for retrospective h = 1, 2, 3, 4, 5 and 10 were respectively
22, 23, 24, 24, 16 and 4 of 1,000; the registered fresh null count was 19 of
1,000. C99 truth inclusions were 988, 997, 993, 994, 991 and 993 of 1,000,
with 992 of 1,000 in the fresh null block. These counts match every endpoint
row. Candidate p-values lie on the required 0.001 lattice, all candidate sets
are nonempty, and every saved Berger--Boos value reconstructs exactly from the
saved candidate p-values and memberships.

The synthesis exited zero after 42 wrapper seconds and used exactly 1,000
bootstrap draws from root 2026092006. All eight synthesis-output hashes match
the receipt. Recomputing SEs and percentile bounds from the saved bootstrap
arrays gives zero discrepancy for every endpoint, crossed cell and contrast.
The only constant bootstrap endpoint is h=10 effect-null exclusion, for which
SE is exactly zero. The nonzero h=5 SE despite a displayed 100% point estimate
is real calibration resampling variability, not a rounding or constant-series
error. The standalone PNG and PDF are legible and consistent with the tables.

## Scientific findings

The adequacy test is materially conservative under its own assumed model. The
fresh prospective h=1 rejection rate is 1.9%, with calibration-aware 95%
interval 1.1--3.2%; retrospective assumed-model rates span 0.4--2.4%. All six
h values are adequacy-null cases, so none of these rows estimates detector
power. C99 truth inclusion spans 98.8--99.7%, with 99.2% in the fresh block,
which is compatible with the intended near-99% candidate-set coverage.

Candidate sets are broad: their mean sizes range from 40.9 to 111.3 of 181
nodes across the six retrospective truths, and average 40.6 nodes in the fresh
null block. When C99 contains the true node, as it does in at least 98.8% of
these histories, taking its supremum and adding gamma cannot lower the p-value
relative to the true-node candidate value. This is a plausible mechanical
contributor to conservatism, but it does not by itself explain the variation
among h values and is not evidence about performance under misspecification.

The original and fresh rank-950 null cutoffs are 2.279370 and 2.490251, a 9.25%
increase. The crossed exclusion counts reconstruct as 74 and 57 of 1,000 under
the original cutoff, and 69 and 48 under the fresh cutoff, for original and
fresh evaluation blocks respectively. The paired cutoff changes are -0.5 and
-0.9 percentage points; evaluation-block changes are -1.7 and -2.1 points; the
interaction is -0.4 points. Every registered calibration-aware contrast
interval includes zero. Only the original-calibration/original-evaluation cell's
interval, 5.6--9.60%, excludes 5%; the other three cell intervals include 5%.

Thus the original 7.4% realised false-effect rate remains a genuine property of
the fixed Goal 049 table and histories. The fresh/fresh cell is 4.8%, and the
original cutoff on fresh evaluation is 5.7%, but the dependent four-cell result
does not distinguish an unlucky table from a phase-specific mechanism. It
provides no basis to replace, redraw or retrospectively recalibrate the original
table. Adequacy rejection and effect-set exclusion remain different endpoints:
the conservative 1.9% adequacy rate neither explains nor repairs the 5.7--7.4%
effect-set rates.

## Recommendation and residual scope

Accept Goal 050 as a reproducible negative/qualification result and freeze the
implementation, reference table and evidence. The reported claims should stay
conditional on the supplied nuisances, fixed independent integration bank and
finite grid. Existing six-truth results are retrospective; the fresh block tests
only assumed-model null behaviour. The detector's sensitivity to ecological
misspecification remains unidentified.

The next useful evidence is a separately approved alternative-generator screen
that asks whether heterogeneous detection or background-risk confounding can
produce misleading effect estimates without an adequacy rejection. Its
severity choices and ecological interpretation require scientific review before
execution. Another audit of the frozen Goal 050 arithmetic is unlikely to alter
this decision; independent review would materially improve confidence in that
next screen because its generator choices define the scientific question.
