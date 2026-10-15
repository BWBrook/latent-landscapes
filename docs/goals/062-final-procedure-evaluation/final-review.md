# Independent final review of Goal 062

16 October 2026 (Hobart).

## Verdict

Goal 062 is scientifically and numerically adequate to close the registered
fixed-design operating-performance gap. I found no material discrepancy in the
machine summary, report tables, uncertainty calculations or bounded
interpretation. This verdict applies to the frozen observed-nuisance procedure
under the registered ten cells. It does not close Paper 1's landscape-generality
or common-process-model gaps.

The main result is mixed rather than a general validation. Exact-family
threefold-effect declaration was 44.4% at mu=.001/day and 90.8% at mu=.004/day;
within-1.5-fold magnitude recovery was 55.0% and 83.2%. At h=5, declaration was
91.6% and 99.6%, while recovery was 61.8% and 84.8%. The corresponding exact
null declaration rates were 2.4% and 2.6%. B100-A h=3 declaration was 45.6%
and 77.6%, with recovery of 49.0% and 76.0%; its null rates were 2.6% and 0.6%.
All cells had zero abstentions and zero unavailable adjusted-free h estimates.

## Scientific target and scope of inference

The target is the declaration, abstention, point-recovery and held-out
predictive operating performance of one frozen algorithm over fresh complete
histories. The exact-family estimands are conditional on one fixed map, site
design, arrival bank, algorithm, nuisance grid and realised reference panel.
The B100-A estimands additionally average over the registered fresh spatial
field, process and observation histories, while retaining the same fixed
infrastructure and exact-family calibration panel.

The data-generating and observation pipeline matches that target: each cell has
500 independent complete histories; the four candidates are paired within a
history; 120 clustered sites are used for fitting and screening; 40 separate
clustered sites are reserved for conditional-prey scoring; and no replicate is
paired across cells. B100-A replaces the exact exposure-gradient background
law with the preregistered exposure-plus-residual-field law. It does not supply
a generating adjusted-model beta or a true nuisance node. Held-out scoring uses
fixed training fits and conditions on predator observations from the same
realised history.

These design facts exclude broader readings. The results do not average over
maps, designs, banks or reference-panel generation. Held-out scores do not
measure transfer to a new landscape or survey regime. The two mu values do not
identify a general nuisance surface, and exact/B100-A contrasts change several
features of the generating hazard simultaneously.

## Independent verification

The returned archive contained 76,283 verified files and matched source binding
`a4f3515f396457130286fb6294f57c32db210f4dff659da1a14e780268b0cb35`.
The completed stage counts were 5,000 main-fit bundles (20,000 fits), 5,000
decisions, 5,000 held-out scores and 50 diagnostic histories. Independent ledger regeneration matched all
27,000 evaluation and 20,000 bootstrap streams.

I ran the prewritten independent checker against the returned `histories.json`,
`summary.json` and bootstrap ledger. It imports no production summarizer. The
[receipt](results/arithmetic-check.json) passed 2,150 comparisons with zero
discrepancies, a maximum absolute difference of 8.674e-19, zero internal-history
discrepancies and exact agreement for all 20,000 bootstrap streams. The
[checker](results/check_arithmetic.py) and receipt are preserved with the report.
The copied machine summary and both original summary CSVs are byte-identical to
the verified returned files.

All 20,000 main fits converged, had finite scores, passed independent score
replay and nesting checks, and generated no registered numerical warnings. All
5,000 decision and held-out audits passed. Audit integrity and diagnostic
geometry are separate claims: here, all 50 fixed diagnostic histories also
passed the profile checks and the lattice checks. There were no profile or
lattice failures to enumerate. The largest positive profile-minus-main gap was
4.093e-12 nats, within the frozen 1e-6 tolerance; every lattice maximum was
below its main fit. Direct profile and lattice replay discrepancies were at
most 1.137e-12 and 8.868e-12 nats.

## Interpretation of the evidence

The two exact null Wilson intervals, 1.4–4.1% and 1.5–4.4%, do not trigger the
registered conditional-null flag. They describe this reference realisation;
they neither prove the marginal exact-family theorem nor provide a guarantee
under misspecification. Zero observed abstentions imply a per-cell Wilson upper
bound of 0.76%, not a zero failure probability.

Detection and magnitude recovery are empirically distinct. At low hazard and
h=3, recovery exceeded declaration, but only 50.0% of declarations were within
1.5-fold of truth. At low hazard and h=5, declaration reached 91.6% while
recovery was 61.8%, only 67.0% of declarations recovered magnitude, and 9.6%
of estimates hit the upper h bound. The higher-hazard cells performed better on
both endpoints, but this contrast does not identify a causal benefit of
background loss or establish monotonic performance beyond the two anchors.

The B100-A high-hazard h=3 cell had 13.2 percentage points lower declaration
(pointwise 95% interval -17.4 to -9.0) and 7.2 points lower recovery (-12.2 to
-2.4) than its exact-family counterpart. This is evidence of reduced operating
performance under the specified alternative law. It cannot isolate
misspecification as the cause, classify the generating family, or support a
general misspecification error guarantee. B100-A fitted beta and mu summaries
remain working-model diagnostics rather than recovery of true or pseudo-true
parameters.

Adjusted-free h outscored constant-free h on average in every cell. Pointwise
intervals excluded zero except in L1 and B_L1; the B_L1 interval was -0.004 to
0.268 nats. Adjusted-free h scored lower than adjusted h=1 in all null cells and
higher in all positive-effect cells. These are paired predictive summaries on
reserved sites within the same histories, not evidence of landscape transfer or
a model-selection exercise.

## Residual risks and recommendation

The remaining limitations are scientific scope rather than unresolved closure
defects. The study has one map, one survey design, one numerical bank, one
reference-panel realisation, two nuisance anchors, no B100-A h=5 cell, no
off-grid experiment and no confidence-coverage estimand. Pointwise intervals
do not support pooled power, equivalence or a family of significance claims.
The 50 preregistered diagnostic histories support the stored optima but cannot
certify global optimisation or bound rare failures. The null-cell h estimates
also inherit the h=1 lower bound, so their zero medians and positive mean log
errors should not be read as general precision.

I recommend accepting Goal 062 as the final registered measurement of this
procedure's conditional operating performance and carrying its mixed results
and limits into the Paper 1 synthesis. No further campaign run or retuning is
justified by these results. This independent reconstruction and diagnostic
review materially increased confidence in numerical closure; another review of
the same artifacts is unlikely to change that decision. Independent manuscript
review would materially affect confidence only if later claims extend beyond
this fixed design, reference panel or specified B100-A stress test.
