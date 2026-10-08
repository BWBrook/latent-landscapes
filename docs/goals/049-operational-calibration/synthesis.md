# Goal 049: known-nuisance candidate calibration

20 September 2026. **Complete: a known-nuisance finite-grid reference, with a
retained null calibration-quality flag.**

## Decision and scientific result

The candidate-wise construction removes the need to know the generating prey
effect when selecting a cutoff. In this fixed reference setting its interior
cutoffs are near the chi-square(1) reference, while the boundary cutoffs differ
substantially. Numerical sensitivity is small under the registered matched-weight
comparison. This establishes a model-conditional, finite-grid procedure; it does
not establish conditional 95% coverage for its one realised calibration table.

That last qualification matters: the realised null exclusion rate is 7.4%.
The table is retained unchanged, with this calibration-quality flag visible.
There is no extra calibration block, threshold repair or favourable redraw.
The original four Arc 3 numerical failures also remain unchanged.

## Design and comparison

The [registration](registration-2026-09-20.md) fixes 181 effects from 1 to 10,
999 calibration histories per candidate and rank 950. Each candidate's sequence
contains 999 independent replicate blocks; common random numbers pair those
blocks across candidates. Another 1,000 independent blocks generate evaluation
histories at effects 1, 2, 3, 4, 5 and 10. This is one landscape and one survey
design with supplied speed, resistance, detection and background hazard.

The analyst receives observations and the complete candidate-cutoff table,
with no generating effect or latent event times. It retains candidate g when
its LR score is no greater than c_g. The diagnostic oracle instead applies
c_h, selected using the evaluator's generating truth h, to every candidate.
Their true-node inclusion agrees on every evaluation history. Point estimates
and prediction use the same frozen fits, so calibration cannot improve them.
The scientific comparisons concern false-candidate inclusion, geometry and
non-null exclusion, not a coverage gain over that oracle.

## Cutoff predictions

The primary high-bank table has c_1=2.27937 and c_10=2.78286. Over the registered
interior 2<=g<=8, cutoffs range from 3.72810 to 4.33948, with median 4.01873.
Thus the boundary/interior ratio is 0.5672 against the predicted maximum 0.85.
All 121 interior nodes lie within 30% of 3.84146; maximum/minimum is about
1.164 against the predicted maximum 1.5. These meet P1's cutoff criterion and
P2's registered descriptive criteria, without assuming a chi-square or boundary
mixture theorem for the composite score. The calibration score is exactly
zero in 55.5% of histories at g=1 and 50.6% at g=10.

Applying the null cutoff c_1 to the whole effect profile gives coverage 0.863
at h=3 and 0.873 at h=5, as P1 predicted. Candidate-wise null exclusion is
0.918 versus oracle-flat 0.851 at h=3, and 1.000 versus 0.998 at h=5. The paired calibration-aware 95% intervals for these differences are
[0.044,0.115] and [0,0.006], respectively: the h=3 difference is resolved,
whereas the h=5 ceiling difference is unresolved. The null
rule is identical to the c_1 test, whose realised size is 0.074, so these powers
must not be represented as comparisons at identical realised 5% size.

P3 was tested in the separate [archive diagnostic](archive-diagnostic.md).
Transporting the smaller slow-speed cutoff to the usual-speed truth gives
coverage 0.800–0.808; reverse transport gives 0.980–0.984. The direction and
at-least-one-direction severity criterion pass for all three effects in both
archived banks. These are correlated retrospective checks, not six independent
replications or qualification of a candidate-wise speed procedure. The archived
P1 precursor's strict h=5 power-increase prediction failed at the ceiling
(both methods excluded the null in every history); that failure is retained.
The fresh h=5 point difference does not turn it into a resolved power finding.

## Resolution and detection

The following primary-table values are means/frequencies across 1,000 evaluation
histories at each truth. Log hull span describes the enclosing hull, not filled
membership. Coverage is included as calibration quality control.

| True effect | Truth inclusion | Null exclusion | Candidate log hull span | Oracle log hull span | Disconnected sets |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.926 | 0.074 | 0.8180 | 0.6652 | 0 |
| 2 | 0.960 | 0.565 | 1.0863 | 1.1395 | 0 |
| 3 | 0.954 | 0.918 | 1.0640 | 1.0850 | 0 |
| 4 | 0.957 | 0.994 | 0.9657 | 1.0134 | 0 |
| 5 | 0.957 | 1.000 | 0.8673 | 0.8713 | 0 |
| 10 | 0.958 | 1.000 | 0.3582 | 0.3022 | 0.005 |

The construction has useful non-null detection in this model, but broad sets
persist. In a retrospective reading of the saved primary memberships, h=5
is retained in 47.5% of histories generated at h=3, and h=3 in 42.6%
generated at h=5. Discrimination between these values is incomplete; it is
not absent. Width changes are not uniformly favourable: candidate-wise hulls are
wider at the two domain boundaries and modestly narrower at interior evaluation
truths than their oracle-flat counterparts. At h=10, five sets are disconnected;
the hull summary must not hide those holes. Paired calibration-aware width
contrasts support the increases at h=1 and h=10 and the decrease at h=2;
the h=3,4,5 width-contrast intervals include zero. In particular, the h=1
increase is 0.153 [0.119,0.200], h=2 decrease is -0.053 [-0.083,-0.013],
and h=10 increase is 0.056 [0.034,0.080].

Near-chi-square cutoffs do not mean identical sets. Compared with the fixed
chi-square reference, candidate-wise membership differs somewhere on the grid
in 50.1–95.6% of histories across the six truths, but the mean number of differing
nodes is only 0.869–2.898 out of 181. Thus mean spans can be close while exact
membership changes frequently. The chi-square comparator has no asserted
coverage guarantee here; its observed null exclusion is 2.5%, versus 7.4% for
the realised candidate table. Its lower null size is conservative relative
to 5%, not evidence of superior calibration. A boundary-mixture reference
would suggest a lower cutoff, but that law has not been established for this
composite score.

## Numerical sensitivity and uncertainty

All 36 declared endpoint checks (six metrics at six truths) pass for
K65536/alpha=0.5 versus K131072/alpha=1.0. True-node inclusion, null exclusion
and boundary-contact frequencies do not move. The maximum absolute mean log
hull-span movement is 0.0000528, against 0.01; mean absolute log point-error
movement is at most 0.000108, against 0.005. Disconnected-set frequency changes
by 0.001 at h=2, against 0.01. Between 0.4% and 1.3% of histories at each truth change some candidate membership;
passing aggregate tolerances does not imply identical sets or exact integration.

At fixed K131072, the alpha=0.25/0.5/1 sweep leaves coverage, null exclusion,
boundary contact and disconnected-set frequencies unchanged. Maximum mean
log-span movement is 0.0000314 and maximum mean log-error movement is 0.0000886.
This is descriptive sensitivity, without a new pass/fail gate.

The fixed 2,000-draw bootstrap independently resamples calibration and evaluation
blocks, sharing indices across paired candidates, truths, methods and banks.
Conditional Wilson intervals hold the realised table fixed; calibration-aware
bootstrap intervals include empirical table variation. Cutoff-curve bands are
pointwise order-statistic confidence bands for population score quantiles, not
simultaneous bands or Beta probability-content intervals in LR units.

## The null calibration flag

The null's 926 inclusions are below the continuous-score beta-binomial central
95% count range [930,968]. Under that marginal reference, P(count<=926)=0.01276.
This is a diagnostic reference, not a selection-adjusted test across six paired
truths; ties also limit the continuous-score interpretation. The conditional
Wilson interval for the observed 7.4% false-exclusion rate is 5.94–9.19%.
The calibration-aware bootstrap interval is 5.6–9.7%, also excluding 5%.

The correct guarantee averages over calibration and evaluation draws with the
same independent-bank scoring algorithm. It does not fix the coverage of this
particular table at 95%. The phase/generator/score contract was checked: fixed inputs and scoring
paths match, roots are disjoint, and no pipeline discrepancy was found. A
post hoc two-sample score-distribution check detected no phase shift (KS
p-values 0.38–0.78 across truths); this does not prove exchangeability or
exclude a tail-specific discrepancy. The positive null cutoff has no
evaluation ties, so inclusive cutoff ties do not explain the low count.
The defensible interpretation is an uncommon marginal realisation, retained
as a limitation rather than redrawn. The [independent review](final-review.md)
records this diagnostic and its limits.

## Evidence figure and reporting

![Candidate cutoffs, set resolution and null exclusion](../../../artifacts/goal049_execution/review/calibration_resolution.png)

Left: candidate-specific cutoffs and pointwise 95% order-statistic quantile
bands; the matched-bank curves nearly overlap. Middle: mean log-hull span,
which does not represent holes. Right: null size at h=1 and power elsewhere;
shading is pointwise calibration-aware uncertainty from the fixed 2,000 draws.
Oracle-flat uses the evaluator's true effect and is not an analyst alternative.
The 90% chi-square line is a descriptive boundary reference, not an assumed law.

Reviewed [outcome tables](../../../artifacts/goal049_execution/review/outcomes.csv)
and [paired contrasts](../../../artifacts/goal049_execution/review/contrasts.csv)
remove floating-point excursions up to 1.0000000000000007 and give exactly zero
SE to mathematically constant bootstrap series, with the required undefined
movement/SE ratios. This [reporting correction](../../../artifacts/goal049_execution/review/reporting-correction.json)
uses the same saved draws: no new draws, altered point estimates, or changed
tolerance decisions. Original CSVs, source and receipts remain intact. The
review figure changes only labels and annotation placement.

## Provenance and next step

Production completed at 07:33:28 UTC after 6 h 11 min 55 s wrapper wall time,
using about 1.59 GiB peak RSS. It exceeded the 5.40-hour timing projection but
remained inside the registered 24-hour and 32-GiB ceilings. All source, bank,
seed and frozen score checks pass. Full profiles and the original cutoffs are
retained under `artifacts/goal049_execution/`; the [execution record](execution.md)
gives the remote copy and receipts. Synthesis finished at 07:44:39 UTC in
246.87 s wrapper time (234.86 s for the registered 2,000 draws), peaking at
611,268 KiB RSS. Computation including timing and the conservative one-hour
prior-work allowance totals about 7.40 h, before a few minutes of local
reporting and verification, within the 24-hour ceiling.
The [completion check](../../../artifacts/goal049_execution/completed-check.json)
verifies all 70 bound source/registration files, 14 frozen score files,
13 synthesis outputs, bank identity, four measured identities and six seed
checks. Both exit receipts are zero and no scoring process remains.
No historical simulation output was rewritten.

The next scientific task is the Arc 4 design discussion. Freeze the assumed-model
calibration and include a matched-generator baseline under that same table before
varying the actual generator; compare with its realised baseline, not only an
ideal nominal rate. Unknown nuisance parameters and candidate-wise speed
calibration remain separate methodological extensions. The severe archived speed
transport failure motivates that extension but does not implement it here.
No Arc 4 alternative-model set or new campaign is selected by this closeout.

Fable supports closure in messages 366–368. The [response to that review](fable-closeout-response-2026-09-20.md)
records accepted framing, a fitted-node LR goodness-of-fit proposal rejected
on algebraic grounds, and the remaining Arc 4 design questions.
