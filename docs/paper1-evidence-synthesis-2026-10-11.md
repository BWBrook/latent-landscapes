# Paper 1 evidence synthesis against the charter

11 October 2026 (Hobart). Evidence assessment and recommendations, prepared at
Barry's request after the capstone truth assessment. This document advances
the charter's paper-level stopping decision and Roadmap Arcs 3, 4 and 6.
It does not register or authorize another experiment, change an estimand or
claim boundary, or supersede a frozen result.

## Recommendation

**I recommend one targeted experiment if Paper 1 presents the final
observed-nuisance procedure as a practical method for detecting and estimating
positive effects.** Measure its recovery and operating performance on a
modest, prospectively registered panel of independent null and positive-effect
histories. Earlier work already supplies substantial conditional recovery,
power and coverage evidence. It does not measure these properties for the
changed final procedure. Another broad recovery campaign or four-case blinded
panel would not answer this question.

No new simulation is strictly required if final-method claims are limited to
the exact-grid null-control construction, feasibility and the bounded blinded
demonstration. Positive-effect performance would then remain explicitly
unmeasured. The recommendation reflects the value of evaluating the practical
endpoint, not a requirement to repair an all-null realization.

The unchanged [charter](paper1-experimental-design-charter.md) also leaves two
material issues: numerical qualification of the landscape comparison and
assessment under a common set of competing process models. A single new power
panel would not close these. First review whether Paper 1 will retain those
broader claims or present explicitly bounded results on numerical limitations
and misspecification vulnerability. The present evidence supports writing the
paper's argument, but not declaring the full charter complete.

No further simulation is recommended merely to replace the all-null capstone,
obtain positive model-discrimination results, refine old transition thresholds,
or bring a realised calibration rate closer to its nominal target.

## Evidence against the six pillars

| Charter pillar | Evidence and scientific conclusion | Completion assessment |
| --- | --- | --- |
| **1. Trusted reference laboratory** | Positive controls for spread, resistance, detection and prey effect; selected joint estimates recover while one simultaneous uncertainty region fails. The threefold-to-fourfold reference transition and low-event limitations are understood sufficiently to select later factors. | **Satisfied conditionally and frozen.** No reason to reopen the reference ladder. See [Arc 1 synthesis](arc1-reference-laboratory-synthesis.md). |
| **2. Recoverability map** | Two 32-truth maps were tested prospectively on their second 16 truths. Four predator surfaces and all five prey surfaces generalized within their prespecified domains. Recovery was selective; the predator boundary-contact surface failed. Estimating spread speed in six paired prey cases produced no detected systematic penalty, without establishing equivalence. | **Satisfied for the reference experiment and its procedure versions.** These are not maps for the final unknown-nuisance analysis. See [Arc 2A](goals/042-arc2a-32-truth-synthesis/Goal.md), [Arc 2B](goals/044-arc2b-prey-effect-recoverability-map/Goal.md) and [Arc 2C](goals/045-spread-prey-oracle-bridge/synthesis.md). |
| **3. Landscape and sampling generality** | Goal 046 examined three seed-matched realizations in each of three archetypes, two sampling designs and three effect truths. No general sampling benefit was resolved; a barrier fivefold case traded lower point error for wider support. Four of nine final-bank map qualifications failed. Goals 047–048 diagnosed problems without qualifying a replacement. | **A defensible conditional result, with numerical generality unresolved.** Neither landscape-population inference nor numerical qualification follows from this closure. See [Goal 046 synthesis](goals/046-landscape-sampling-generality/synthesis.md), [047](goals/047-integration-validation/results.md), [048](goals/048-integration-redesign/results.md). |
| **4. Model discrimination and misspecification** | Fresh, replicated comparisons expose harmful undetected misspecification and the benefit/cost of background adjustment. A calibrated effect test is available under stated null conditions. Generating-family identification remains weak, and no fitted candidate represents the residual spatial field in B100-A. | **Strong vulnerability and adjustment evidence; common competing-model assessment remains incomplete.** Closing the pillar as robustness alone requires explicit review of the intended claim, not relabelling the existing comparisons. See [051](goals/051-misspecification-screen/synthesis.md), [053](goals/053-prospective-background/synthesis.md), [054](goals/054-null-effect-calibration/synthesis.md), [055 claim audit](goals/055-arc4-synthesis/claims-audit.md). |
| **5. Synthetic-realistic capstone** | The frozen integrated scenario combines a new connected map, stochastic spread, biased access, imperfect detection and prey response. Training, holdout and truth were released in stages. All four truths were null; branch and holdout forecast misses were retained. | **Satisfied as a bounded blinded demonstration.** It supplies neither positive-effect recovery nor operating rates. Preserve it unchanged. See [complete report](goals/061-blinded-capstone-training/complete-report.md) and [truth report](goals/061-blinded-capstone-training/truth-report.md). |
| **6. Lean and transferable implementation** | Reusable scientific components and audited execution paths exist, and earlier arcs were consolidated. The programme still contains later developmental paths and large evidence closures. | **Final consolidation and paper reproduction remain to be assessed.** This synthesis is not a code audit and does not certify this pillar or authorize deletion. Scientific scope should precede a bounded consolidation. |

The charter allows negative results and does not require every experiment to
report every metric. That permits the weak simultaneous region, failed model
diagnostics and conditional landscape result to remain scientific findings.
It does not turn unmeasured operating properties or failed numerical gates
into successful qualification.

## Keep the generations of inference separate

For within-map operating rates, the experimental replicate is a complete
stochastic history, including its shared spatial spread and observation
process. For landscape-class generality, map realization is an additional,
higher-level unit; more histories on one map do not replace more maps. Sites,
visits, profile nodes, integration draws and calibration references are not
additional evaluation replicates. Common random numbers pair histories across
conditions; they do not make those conditions independent discoveries.

| Procedure generation | What is estimated and calibrated | Evidence that can be claimed |
| --- | --- | --- |
| **Reference and recoverability maps, Goals 001–046** | Different one- and joint-parameter fits, usually with other quantities supplied. Cutoffs are learned at the generating truth; calibration and evaluation histories are disjoint. | Conditional point recovery, same-truth coverage, support geometry, non-null exclusion and held-out prediction. The exclusion maps are not power curves for one procedure usable without knowledge of truth. |
| **Candidate-wise magnitude sets, Goal 049** | Effect candidates calibrated separately on 181 grid nodes, with background, spread and detection known. Each node has 999 reference histories; six truths each have 1,000 fresh evaluation histories. | An operational finite-grid magnitude-set procedure under known nuisances. It does not transfer to estimated nuisances or continuous/off-grid truths. |
| **Adjusted background and null calibration, Goals 053–055** | Effect and spatial background slope estimated; mean background, spread and observation nuisances supplied. Goal 054 calibrates the null across 81 beta nodes, using 999 reference blocks and 1,000 independent evaluation blocks per cell. | Conditional effect-declaration rates and power for this fixed rule, plus estimation and predictive trade-offs. A null test does not provide effect-magnitude coverage. |
| **Observed-nuisance feasibility, Goals 056–060** | Mean background hazard, exposure slope and persistent prey-detection SD are estimated; pre-invasion observations are added. Spread/resistance and mean detection remain known. Public fixtures and reference pilots assess feasibility and numerical behaviour. | Feasibility and bounded numerical evidence. One history per fixture cell, screening references and effect references do not estimate evaluation-panel size, power or coverage. |
| **Final capstone procedure, Goal 061** | Pre-only screening over 765 nuisance nodes, then a Berger–Boos null decision using 999 full-history references at every retained node. Four models are fitted: constant/adjusted background, each with effect free/fixed at one. | A casewise exact-family, on-grid null-error bound conditional on map, design, bank and algorithm, averaged over reference and observation generation. Four realised non-declarations are case results. There is no magnitude-interval coverage or positive-effect power result. |

These distinctions follow the [Goal 049 interpretation amendment](goals/049-operational-calibration/interpretation-amendments.md),
[Goal 054 registration](goals/054-null-effect-calibration/registration-2026-09-29.md)
and [Goal 061 methods review](goals/061-blinded-capstone-training/methods-review.md).
The final guarantee is not conditional on the realised reference tables, is
not four-case family-wise control, and does not cover B100-A or off-grid
nuisance truths. Within-map held-out prediction is also distinct from
prediction on a new landscape or under a new survey regime.

## Recovery, power and calibration: what is already known

**Recovery is well evidenced in the controlled laboratory.** In Goal 031's
latent-arrival fivefold positive control, 1,000 validation histories gave
median absolute log-effect error 0.128, coverage 0.963 and null exclusion
1.000. The Arc 2B map spans median absolute log errors 0.100–0.426 and
non-null exclusion 0.164–1.000. Its reviewed classification is **4 fully
recovered, 9 detected but incomplete, 19 not reliably detected**. The
historical classifier was 3/10/19; only S08 changes when same-truth coverage
is correctly separated from biological recovery. Both records remain valid
as versioned interpretations. Every tested effect below threefold stayed in
the weak-detection class. These findings depend on supplied background and
detection quantities; they are not claims about the capstone likelihood.

**Operational power exists for earlier, simpler procedures.** Goal 049's
known-nuisance candidate-set null-exclusion rates at h=2, 3 and 4 were
56.5%, 91.8% and 99.4%. Goal 054 gives particularly useful prospective
evidence for the adjusted null rule:

| Generating background | False declaration at h=1 | Declaration at h=3 | Conditions |
| --- | ---: | ---: | --- |
| Exact constant, beta=0 | 4.2% | 76.1% [70.8, 78.9] | Known mean background and observation/spread nuisances |
| Exact exposure gradient, beta=.60 | 3.2% | 93.0% [89.3, 94.6] | Same known-nuisance procedure |
| B100-A residual-field stress | 2.5% | 87.5% [82.9, 89.5] | Descriptive robustness; outside nominal guarantee |
| N100-A nonlinear stress | 2.8% | 86.2% [81.9, 88.2] | Descriptive robustness; outside nominal guarantee |

Each cell contains 1,000 evaluation histories. Brackets are the registered
calibration-aware 95% bootstrap intervals for the h=3 rates. Adjustment costs
9.2 and 6.2 percentage points of sensitivity relative to the constant rule
in the two exact families. Under nonconstant backgrounds the constant rule's
higher sensitivity accompanies inflated false declarations. These are
substantive trade-offs, not evidence of a uniformly better model.

**The change to observed nuisances was scientifically necessary.** With the
Goal 054 rule held fixed, [Goal 055](goals/055-arc4-synthesis/synthesis.md)
found 7.8% and 10.8% adjusted null declarations when supplied mean hazard was
20% below truth, and 19.8% under omitted persistent detection SD .20 versus
3.8% in its paired baseline. These are registered failures, using archived
histories and additional fits, not 12,000 new independent histories.

**Magnitude recovery for the changed procedure remains uncertain.** The
[Goal 056 feasibility panel](goals/056-observed-nuisance-feasibility/synthesis.md)
has one history in each of 16 cells. Its eight adjusted h=3 estimates range
from 1.717 to 4.020, with median 2.005 and mean absolute log error 0.361;
six lie below truth. This is a reason to measure recovery, not a replicated
estimate of bias. Final capstone profiles are likelihood-support diagnostics,
not confidence intervals. Curvature and a calibrated null declaration cannot
be substituted for magnitude coverage.

**Calibration has several distinct levels of evidence.** Early same-truth
coverage is a genuine check of a locally calibrated procedure, but requires
truth information unavailable in ordinary analysis. Goal 049 has a stronger
candidate-wise construction: coverage across its six evaluation truths was
92.6–96.0%. Its realised null false exclusion was 7.4%, with a calibration-aware
interval of 5.6–9.7%; this remains a quality-control flag. The later adequacy
detector's 1.9% fresh assumed-model rejection is evidence about a different
test, not a correction to those magnitude sets. None supplies confidence-set
coverage for the final unknown-nuisance fit.

Goal 061 used 75,735 screening references and 298,701 effect references over
299 required nodes. Its `p_BB` values, 1, 1, .422 and 1, produced four valid
non-declarations with no realised false declaration. Only two cases had an
exact-family background; the other two were B100-A. These counts cannot
estimate an error rate with useful precision, validate the guarantee under
misspecification, or supply power. Three statistics were effectively zero,
so their p=1 results require no unusually conservative reference cutoff.

## Material gaps and proportionate next work

### 1. Replicated evaluation of the final procedure: recommended

If the final observed-nuisance method is presented as a usable endpoint of
Paper 1, its recovery and sensitivity should be measured. Register a small
panel on the fixed capstone map using fresh complete histories, the frozen
observation model and the actual screen-plus-`p_BB` decision. Retain all four
fitted comparators and the same information supplied to each. Do not replace
the registered all-null capstone or call this follow-up blinded evidence.
The proposed estimand is the distribution of declarations, abstentions and
point-estimation errors **conditional on the fixed map and reference tables**
at selected truths. It excludes magnitude-interval coverage and performance
averaged over independently generated reference tables.

A concrete starting design for review is h={1,3,5} at two prospectively
selected, exact on-grid nuisance settings representing contrasting event
information. Six cells with **500 independent evaluation histories each**
would estimate a cell probability with a worst-case approximate 95% half-width
of 4.4 percentage points, or about 1.9 points near a 5% rate, conditional on
the frozen reference tables. These numbers are a design proposal, not an
accepted sample size or an assurance of adequate power. Choose the actual
anchors and required precision before generation; two combined nuisance
regimes would not isolate individual nuisance effects.

Report declaration and abstention rates on all histories; signed log bias,
absolute log error and large-error rates; support geometry labelled as such;
and paired held-out score differences. Report recovery among declarations
separately to expose selection effects. Compare null and positive conditions
together: an elevated declaration rate is not a power benefit if false
declarations are also inflated. Do not create an arbitrary pass threshold
after seeing the results.

Reference generation dominates feasibility. If the existing tables and exact
algorithm are reused, fresh histories estimate performance **conditional on
those tables**. New retained sets may require more than the existing 299
nodes: completing all 765 would require up to 466×999 = **465,534 additional
effect-reference histories**, as well as the evaluation fits. The earlier
299-node campaign took about 15.5 hours on 51 workers; that is an observed
receipt, not a forecast or resource authorization. A registration should
cost reference completion, fitting, storage and audit before production.

If performance averaged over reference-table generation is itself a reported
empirical target, it needs a design that varies those tables and propagates
that uncertainty. One frozen-table evaluation cannot estimate that target;
reused null references must not also serve as independent evaluation cases.
The existing mathematical null bound and a conditional empirical evaluation
can be reported together without pretending they target the same randomness.

Matched B100-A null/positive cells or off-grid nuisance cells would be useful
secondary stress tests **if robustness of the final procedure is claimed**.
They would estimate robustness, not extend the on-grid theorem. Do not expand
to the full nuisance cube by default.

### 2. Landscape result: resolve numerical scope before adding maps

Retain Goal 046's accepted conditional conclusion and its failed gates.
For stronger numerically qualified generality, use the saved connected and
corridor stress histories for method development, then freeze the method and
validate it against independent or demonstrably higher-accuracy numerical
evidence, including untouched challenge histories, before reanalysing the
landscape results. Reusing the development histories alone would provide
retrospective sensitivity analysis, not independent qualification. Validation
must cover the actual effect and spread-profile quantities being reported,
not just agreement between two scorers using the same bank.

This may require substantive numerical-method work: Goals 047–048 already
show why another pseudocount sweep or automatic bank doubling is not an
evidenced repair. It should have a bounded feasibility decision before any
large reanalysis. New ecological histories or maps would not resolve that
numerical gap. Alternatively, an explicitly reviewed paper boundary can
retain the conditional landscape findings and numerical failures without
claiming that method generality is established. The final connected-map
capstone qualification does not repair the older corridor/spread analysis.

### 3. Competing process models: required for the fuller charter claim

Goal 051's aligned-background null raised harmful-undetected outcomes from
19.3% to 42.3%, while the adequacy detector rejected only 2.7%. Goal 053
prospectively showed that adjustment helps estimation under nonconstant
background but harms it under constant background; even the correct exact
nonconstant family wins prediction only about 59–65% of the time. These
support vulnerability and predictive ambiguity. They do not establish
reliable generating-family discrimination.

If the original common-model ambition is retained, register a small shared
comparison of constant, exact exposure-gradient and residual spatial-field
generators at null and positive effect, with every dataset assessed by the
same candidate set and a fitted neutral. A claim of selecting the generating
residual-field family needs a candidate capable of representing that family;
adding it is a substantive model decision. Compare only commensurate
parameters and prespecify predictive ties, selection and harmful-error
endpoints. A new-map or map-blocked component is needed if this comparison
also claims landscape generality.

This is a larger methods commitment than the proposed final-procedure panel.
Do not launch both automatically or count the power panel as its substitute.
The alternative is a reviewed scope change to a paper about recovery,
calibration boundaries and misspecification vulnerability, explicitly leaving
generating-family discrimination unresolved. The current charter has not
been amended by this recommendation.

### 4. Magnitude intervals: a claim decision before a coverage experiment

The paper already has uncertainty-calibration evidence from early marginal
procedures and Goal 049. It can report final-method profiles as support
diagnostics and final-method decisions as null tests. If it instead promises
calibrated effect-magnitude uncertainty with estimated nuisances, an interval
procedure must first be specified and reviewed, then evaluated on independent
histories. More replicates alone cannot validate an interval that has not
been defined. Useful simultaneous spread–effect uncertainty likewise remains
a separate optional methods problem; the existing negative result is valid.

## Work that does not need another simulation

- Assemble the manuscript around recovery transitions, the limits of local
  versus operational calibration, nuisance trade-offs, misspecification and
  the unchanged blinded demonstration. Keep procedure versions visible.
- Extract signed-bias summaries where needed from existing compact estimation
  rows. Absolute error alone should not be described as bias.
- Retain the failed boundary-contact surface, original Goal 046 numerical
  failures, Goal 049 null flag, unconfirmed original Goal 051 nomination,
  unsuccessful prototype, and capstone branch/holdout misses.
- After the scientific boundary is agreed, audit live callers and evidence
  dependencies for one bounded code consolidation and manuscript reproduction
  tranche. Preserve archived results and provenance.

Repeated reference-domain Sobol points, finer recovery-transition searches,
more within-map bootstrap draws, another assumed-model adequacy baseline,
or a balanced four-case capstone would not close the material gaps above.

## Verification and review boundary

This is a synthesis of registrations, accepted reports, independent reviews
and compact saved results, not a replay of every historical simulator. Two
independent evidence passes covered Goals 001–045 and 046–053; the integrating
pass checked Goals 054–061. Selected primary CSVs were checked directly:
Goal 054's eight declaration counts, Goal 055's four diagnostic null rates,
Goal 056's eight positive-effect estimates, and Goal 058's four blocks of
999 references. The Arc 2B classification amendment was traced to its accepted
decision and side-by-side table. Supporting read-only extraction notes and
input hashes are in `artifacts/paper1_evidence_synthesis_20261011/` under the
existing generated-artifact policy.

The [independent synthesis review](paper1-evidence-synthesis-review-2026-10-11.md)
records the challenge to the conclusions and recommendations. No new
simulations, refits, calibration changes, charter amendments or code cleanup
were performed for this assessment.
