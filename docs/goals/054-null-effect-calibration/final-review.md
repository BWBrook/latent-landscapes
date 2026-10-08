# Goal 054 independent result review

30 September 2026. **Audit verdict: conditionally supported.** No fatal flaw or
material result-level implementation defect was found. The registered primary
full-supremum rule is correctly implemented and gives a useful balance between
false effect declarations and sensitivity in this fixed finite-grid experiment.
It can be relied upon as a conditional operating rule for the 81 exact beta
nodes, one landscape and site design, known nuisance quantities and the fixed
K131072/alpha1 bank. It does not establish conditional 5% size for this one
realised reference table, continuous-beta validity, improved magnitude recovery,
or general robustness to misspecification.

Goal 054 should close as a successful but deliberately narrow calibration
experiment. Its misspecification cells did not find the boundary where adjusted
false declarations increase. That is an informative negative result, not a
reason to add histories, retune the rule or extend the campaign after inspection.

## Claim audited and conditions for it to hold

The operational claim is that a statistic

`T_adj = 2 {max_(h,beta) ell(h,beta) - max_beta ell(h=1,beta)}`

calibrated from 999 reference histories at each of 81 beta nodes can declare
`h>1` with at most 5% long-run probability under an exact on-grid null, while
retaining scientifically useful sensitivity at `h=3`. The primary rule rejects
only when every nodewise plus-one p-value is at most .05. The constant rule has
the analogous guarantee only at beta=0. The secondary Berger--Boos rule must
exclude the true beta with probability at most gamma=.01 and, while retaining
it, use a .04 T tail so that the union bound remains .05.

This claim requires the registered reference and evaluation histories to be
independent blocks, exchangeable at the true node, and scored with the same fixed
analysis bank and observation-only likelihood. It also requires the full
181-by-81 fits, deterministic tie convention, inclusive plus-one tails, correct
Berger--Boos candidate sets, no holdout leakage into decisions, and whole-block
resampling. The probability guarantee averages over both reference-table and
evaluation-history generation. It is not a guarantee conditional on the table
that happened to be generated.

## Decisive results

The intervals below are the registered calibration-aware 95% percentile
intervals. They resample the 999 reference blocks and 1,000 evaluation blocks,
preserving pairing across beta nodes and cells. Primary and Berger--Boos rates
are calibrated false-declaration rates only in the exact `h=1` E0 and E06 cells.
The constant rate is calibrated only in E0_h1. Rates in B100-A and N100-A are
misspecification operating rates without a nominal size meaning.

| Cell | Primary full supremum | Constant beta0 | Berger--Boos | Primary minus constant |
| --- | ---: | ---: | ---: | ---: |
| E0_h1 | .042 [.022, .055] | .035 [.021, .050] | .029 [.016, .044] | +.007 [-.014, .020] |
| E0_h3 | .761 [.708, .789] | .853 [.821, .884] | .735 [.672, .761] | -.092 [-.141, -.067] |
| E06_h1 | .032 [.020, .045] | .171 [.144, .208] | .029 [.015, .039] | -.139 [-.173, -.114] |
| E06_h3 | .930 [.893, .946] | .992 [.985, .997] | .908 [.871, .928] | -.062 [-.099, -.047] |
| B100-A_h1 | .025 [.015, .037] | .157 [.128, .191] | .022 [.011, .030] | -.132 [-.163, -.106] |
| B100-A_h3 | .875 [.829, .895] | .974 [.960, .983] | .848 [.808, .873] | -.099 [-.140, -.080] |
| N100-A_h1 | .028 [.015, .039] | .147 [.119, .184] | .021 [.010, .031] | -.119 [-.156, -.094] |
| N100-A_h3 | .862 [.819, .882] | .981 [.971, .989] | .837 [.797, .862] | -.119 [-.160, -.101] |

The strongest supporting evidence is the joint pattern, not any single rate.
The primary rule gives observed exact-null rates of 4.2% at beta=0 and 3.2% at
beta=.60, with sensitivities of 76.1% and 93.0%. At beta=0, estimating beta
costs 9.2 percentage points of sensitivity relative to the correctly specified
constant rule. At beta=.60 it cuts the misspecified constant rule's false
declarations by 13.9 points at a 6.2-point sensitivity cost. The two residual-
field stresses show the same qualitative protection: primary `h=1` rates are
2.5% and 2.8%, with `h=3` rates of 87.5% and 86.2%.

The primary cutoff is 3.46649 and is set uniquely by beta=.55, an interior node.
The nodewise primary cutoffs range from 1.58021 to 3.46649. No rank-950,
rank-960 or rank-990 reference cutoff has an exact or tolerance-level tie, and
no evaluation T or D lies within `1e-12` of its operative cutoff. Thus the
registered conservative tie convention is correct but does not decide any
production classification. Adjusted beta-edge fits are at most 2.6% by cell,
and only three of 8,000 adjusted fits reach h=10, so the observed rates do not
show material fit-box truncation.

The textbook thresholds provide a coherent descriptive check. At E0_h1 the
adjusted 2.71 and 3.84 rules declare 6.3% and 3.2%, while the corresponding
constant rules declare 4.3% and 2.1%. At E06_h1 the adjusted rates are 5.0% and
2.9%, versus 19.0% and 13.3% for the misspecified constant analysis. The
empirical primary threshold lies between the two textbook cutoffs. These rates
do not confer a chi-square guarantee on either threshold.

Berger--Boos did not recover sensitivity. Its declarations are a strict subset
of primary declarations in all 8,000 evaluation histories. It reduces
sensitivity by 2.6 points in E0_h3, 2.2 in E06_h3, 2.7 in B100-A_h3 and 2.5 in
N100-A_h3. Candidate sets are broad: their mean size is 38--40 of 81 nodes in
the four h1 cells and 25--29 in the h3 cells. None is empty. In the realised
exact-null evaluations, the true beta is excluded from the candidate set in
1.7% of E0_h1 and 1.2% of E06_h1 histories. This does not refute the unconditional
gamma guarantee, but it demonstrates why the guarantee must not be described as
conditional on the realised reference table.

The nonlinear stress is measurably different from B100-A: mean affine-A log-
hazard residual RMSE is .664 rather than .561, and mean map hazard--A correlation
is .527 rather than .627. Nevertheless its primary h1 rate is only .3 percentage
points higher, with a paired calibration-aware interval of [-.9, +1.3] points.
The experiment therefore found no excess declarations from this added threshold
shape. It did not identify a robustness boundary or isolate a causal effect of
nonlinearity, because the contrast also changes realised CV and alignment after
normalisation.

Magnitude recovery remains separate from declaration validity. Every primary
false declaration in the four h1 cells has at least a 1.5-fold fitted-h error.
Among h3 histories, the joint primary declaration-and-large-error rates are
16.7% in E0, 8.8% in E06, 8.8% in B100-A and 6.0% in N100-A. Calibration controls
an effect decision under its stated null; it does not repair h--beta confounding
or turn a declaration into an accurate effect estimate. Unconditional adjusted
mean absolute log-h error is worse than constant in the two E0 cells and better
in the other six cells, preserving Goal 053's conditional estimation result.

Holdout prediction also remains conditional and was not used in any decision.
Adjusted-minus-constant score is negative with intervals below zero in both E0
cells, positive with intervals above zero in E06_h3 and B100-A_h3, and unresolved
in E06_h1 and B100-A_h1. It is positive in both nonlinear cells. Every adjusted-
minus-neutral h1 mean is negative and every h3 mean is positive. This is
compatible with predictive information from a real effect, but it is not a
calibrated declaration or evidence of transfer to another landscape.

## Registered forecasts

Pointwise, the primary forecasts are met: exact-null rates lie in 2--5%, E0_h3
and E06_h3 sensitivities lie in their forecast ranges, B100-A_h1 is below 6%,
and N100-A_h1 is slightly above B100-A_h1. Reference-table uncertainty weakens
three statements. E0_h1 has an interval extending to 5.5%; N100-A_h1 minus
B100-A_h1 is +.3 points with interval [-.9, +1.3]; and the constant B100-A_h1
forecast of at least 18% fails pointwise at 15.7% although its [.128, .191]
interval overlaps 18%. These must be reported as pointwise outcomes separately
from uncertainty-supported comparisons. They were forecasts, never acceptance
gates.

## Strongest threats, ranked by scientific consequence

1. **Major scope restriction:** exact validity stops at the 81 beta nodes on one
   landscape, site split, schedule, known-nuisance specification and fixed
   integration bank. Off-grid beta, unknown detection or process quantities,
   another landscape and another bank are untested. A claim about a continuous
   spatial-background family would exceed the evidence.
2. **Major unresolved robustness boundary:** two aligned residual-field shapes
   both give low h1 operating rates. They show that failure was not detected in
   these stresses; they do not show where protection ends or support general
   misspecification robustness.
3. **Moderate reference-table uncertainty:** calibration-aware intervals are
   materially wider than frozen-table intervals. For example, the E0_h3 primary
   interval widens from [.733, .787] to [.708, .789]. Across six independently
   reconstructed registered bootstrap draws, the effective cutoff ranges from
   3.292 to 3.661 and the cutoff-setting beta changes, although all six setters
   are interior. The realised table is usable, but its conditional operating
   rate is not known exactly.
4. **Moderate sensitivity and estimation cost:** the primary rule is useful, not
   dominant. Adjustment costs sensitivity under beta=0 and retains appreciable
   magnitude error. Berger--Boos adds no sensitivity benefit in these data.
5. **Minor reporting hazards:** `error_metrics.csv` contains both estimators for
   every rule, although the registration calls for the adjusted estimator with
   adjusted rules and the constant estimator with constant rules. The registered
   rows are correct, but off-target method-by-rule rows should not enter the
   scientific table. The synthesis forecast status also summarises interval
   support, so it cannot replace the separate pointwise forecast audit above.

## Independent checks and outcomes

- I authenticated the reduced table as SHA256
  `33c94ad6d7bb58701c68b611c70400c0228787e1782026c7df7d9b747aa40900`
  and the synthesis summary as
  `7112017925c7487f9c7187c47eb632d3cae20db7723ddc0fcd012e693a2c0a57`.
  The local [production verification](../../../artifacts/goal054_execution/production-verification.json)
  covers all 168 outputs. The separate [raw-score crosscheck](../../../artifacts/goal054_execution/production-crosscheck.json)
  authenticates all 81 rows and reconstructs 12 reference and 24 evaluation
  histories with maximum absolute error zero.
- A separate NumPy path, with no campaign or synthesis imports, reconstructed
  all seven rules from direct plus-one counts and from ranks 950, 960 and 990.
  The two routes have zero primary, constant, candidate-membership or
  Berger--Boos disagreements. All 56 rule-rate rows and all 56 registered
  estimator/rule declared-subset rows match exactly. The evidence and script
  are in the [independent reconstruction](../../../artifacts/goal054_execution/review/independent_reconstruction.json).
- Registered bootstrap draws 0, 1, 37, 499, 999 and 1999 were reconstructed
  from the registered RNG stream and compared with the saved archive. Frozen and
  calibration-aware rule rates, metric means, declared-subset metrics and paired
  contrasts all match with maximum absolute error zero. See the
  [selected-draw verification](../../../artifacts/goal054_execution/review/selected_bootstrap_draw_verification.json).
- The synthesis uses exactly 2,000 draws, whole reference blocks paired across
  beta and whole evaluation blocks paired across all eight cells. Its 11 outputs
  pass the [synthesis verification](../../../artifacts/goal054_execution/synthesis-verification.json).
  I did not rerun production, model fitting, the full synthesis or an additional
  bootstrap, and I did not duplicate the independent raw-row replay.

## Required closeout corrections and residual uncertainty

No campaign or synthesis-code repair is required. Before relying on the result,
the scientific synthesis should:

- call the guarantee finite-grid, on-node and joint over reference/evaluation
  generation, rather than conditional 5% control for this table;
- distinguish calibrated size/sensitivity from misspecification operating rates
  and descriptive textbook thresholds;
- report only the registered estimator for each decision rule, with every
  declared-subset denominator and undefined value retained;
- preserve the pointwise forecast failure and uncertainty-unresolved cases;
- state that Berger--Boos recovered no sensitivity and that the nonlinear pair
  did not locate a failure boundary; and
- avoid presenting declaration calibration as point-estimator repair, confidence
  coverage, structural identifiability or landscape-general evidence.

After those corrections, residual uncertainty is dominated by off-grid beta,
unknown nuisances, integration-bank variation, new landscapes/designs and
unexplored misspecification. Those are new scientific experiments rather than
repairs to Goal 054. I support freezing this campaign and moving to a bounded
Arc 4 comparative synthesis and capstone-design registration using Goals
050--054, rather than immediately adding another calibration axis. Another
same-scope numerical review is unlikely to change the decision. Independent
review would again be valuable if a capstone or manuscript expands the claim
beyond this conditional finite-grid result.

## Final closeout consistency acceptance

I subsequently checked the completed [scientific synthesis](synthesis.md) and
[next-tranche proposal](next-tranche-proposal.md) against this audit. Their
decision rates, calibration-aware intervals, paired contrasts, cutoff and
candidate-set diagnostics, estimator/error statements, field summaries,
forecast outcomes and claim boundaries agree with the independently
reconstructed evidence. The 16 reporting-only paired estimation contrasts
match the saved bootstrap draws to at most `1.3e-15`; all 424 field-summary rows
match the production diagnostics exactly, using population SD across the 1,000
realised fields. The report manifest binds those tables and both report-figure
formats to the authenticated synthesis.

I accept the synthesis and proposed Arc 4/capstone-design tranche without a
further scientific correction. At the time of this check, the final
`completed-check.json` had not yet been written and the execution record still
ended at synthesis launch. Those two provenance records must be completed and
must bind the final synthesis, review and reporting outputs before administrative
closeout. They do not change the scientific verdict above.

**Astra administrative completion note, 30 September 2026:** the execution
record now contains the zero-exit synthesis and full closeout; the completed
check binds the final synthesis, this review, reporting outputs and receipts.
The result and proposal were posted as messages784–785, and the heartbeat was
deleted. This resolves the temporal administrative caveat above without
changing the independent scientific review.
