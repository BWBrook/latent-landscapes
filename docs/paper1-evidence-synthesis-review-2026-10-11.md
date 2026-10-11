# Independent scientific review of the Paper 1 evidence synthesis

11 October 2026 (Hobart). Audit-only review of
[`paper1-evidence-synthesis-2026-10-11.md`](paper1-evidence-synthesis-2026-10-11.md).
No simulation, refitting, calibration change, charter amendment or source-result
edit was performed.

**Reviewed draft SHA-256:**
`6154c63a83f8ba8be95873ade959e5d28545311d47d5792dfe25a49934f3e2cf`.

## 1. Audit verdict: conditionally supported

The synthesis is scientifically reliable for deciding what the existing
programme does and does not establish. Its central operational claim is that
controlled experiments support conditional recovery, detection and uncertainty
statements, whereas the final procedure that estimates selected nuisances has
an exact-grid null-declaration guarantee but no replicated positive-effect
performance or calibrated effect-magnitude interval. That claim survives this
review.

The experiment recommendation is also proportionate after revision. A new
experiment is needed only if Paper 1 presents the final procedure as a practical
method for detecting and estimating positive effects. If the paper instead
limits that procedure to exact-grid null control, feasibility and the bounded
capstone case study, no new simulation is scientifically required. The original
all-null panel remains a valid prospective outcome and must not be replaced.

## 2. Strongest supporting evidence

The synthesis correctly preserves four distinctions that control the paper's
claim boundary.

1. Goals 001--046 use truth-local or otherwise simplified procedures. Their
   recovery maps and coverage checks are evidence for those fixed experiments,
   not for the later nuisance-estimating method.
2. Goal 049 supplies a candidate-wise finite-grid magnitude-set procedure under
   known nuisances. Its 7.4% realised null exclusion, with calibration-aware
   interval 5.6--9.7%, remains a calibration-quality flag rather than a result
   to redraw or silently pool with another test.
3. Goal 054 estimates replicated declaration rates and positive-effect
   sensitivity for a fixed known-nuisance null rule. Goal 055 then demonstrates
   transfer failures when the supplied mean background is wrong or persistent
   detection heterogeneity is omitted. The evidence therefore argues against
   extrapolating Goal 054 operating rates to Goal 061.
4. Goal 061's four non-declarations are case outcomes. Its guarantee is
   casewise, exact-family, on-grid and marginal over reference and observation
   generation, conditional on the fixed map, design, bank and algorithm. It is
   not family-wise control, realised-table calibration, B100-A validity,
   positive-effect power, magnitude coverage or a general recovery result.

The synthesis also correctly treats numerical/bank qualification and audit
closure as evidence that a frozen algorithm executed as specified. Those checks
do not establish ecological recovery, calibration, model adequacy or landscape
generality.

## 3. Strongest threats, ranked by scientific consequence

### Major threat 1: an unconditional demand for another experiment

The first draft said further work was warranted without first selecting the
paper's claim boundary. That would have converted an optional stronger claim
into an apparent charter requirement. The final draft now makes the decision
conditional: the proposed evaluation is required for a practical
positive-effect claim and unnecessary for the narrower exact-grid null-control
claim. This correction is adequate.

### Major threat 2: circular numerical qualification of Goal 046

A method developed and declared qualified on the same connected/corridor stress
histories could be tuned to the observed failures. The final draft now requires
the method to be frozen after development and validated against independent or
demonstrably higher-accuracy numerical evidence, including untouched challenge
histories. Reanalysis using only the development histories is correctly labelled
retrospective sensitivity. This correction is adequate.

### Major threat 3: treating the proposed panel as broader calibration

The proposed six cells, with 500 complete histories per cell, can estimate
declaration, abstention and point-error distributions conditional on one map and
one realised set of reference tables. It cannot estimate performance averaged
over independently generated reference tables, validate B100-A or off-grid
guarantees, or provide effect-magnitude interval coverage. The final draft now
states that estimand explicitly. The label “observed-nuisance” should continue
to travel with the qualification that spread, resistance and mean detection
remain supplied.

### Major threat 4: confusing histories with landscape replication

Complete histories are the evaluation units for within-map operating rates,
but map realizations are the higher-level units for landscape-class inference.
The revised synthesis now states this hierarchy. More histories on one map
cannot establish new-map generality.

No fatal flaw remains in the reviewed version. The unresolved common-model,
landscape-numerical and magnitude-interval questions are gaps in evidence or
scope choices, not defects that the synthesis hides.

## 4. Independent checks and outcomes

- I fixed the audit criteria before reading the draft: procedure version,
  nuisance regime, generating family/grid, evaluation unit, and uncertainty
  target had to accompany every claim.
- I checked the charter definitions and stopping rule against the roadmap,
  Goal 046 calibration correction, Goal 049 candidate calibration, Goals
  054--056, Goal 058, and Goal 061's methods and truth reports. Their inferential
  boundaries agree with the final synthesis.
- I checked the proposed sample-size arithmetic independently. For 500
  histories, the normal-approximation 95% half-width is 0.04383 at probability
  0.5 and 0.01910 at probability 0.05, matching 4.4 and 1.9 percentage points.
- I checked the stated worst-case reference completion: 466 remaining nodes
  times 999 references equals 465,534 histories. This is a workload bound, not
  a runtime prediction or scientific replication count.
- I verified the final draft digest after the four review corrections. The
  earlier challenged draft had SHA-256
  `aab58915ff8df7e33a37659d7dbee390469a357e12a84aa6431d0174c25827b7`;
  the disposition in this review applies only to the final hash above.

These are source and arithmetic checks, not a replay of the historical
simulators or an independent refit of stored observations.

## 5. Required decisions and analyses before relying on broader claims

1. **Choose the manuscript claim boundary first.** A bounded paper can proceed
   without new simulation. If the final method is claimed to recover or detect
   positive effects, register the proposed replicated panel before generation.
2. **For the replicated panel, freeze the estimand and decision consequence.**
   Prespecify the two nuisance anchors, conditional reference-table target,
   declaration/abstention and point-error summaries, precision requirement,
   stopping rule, and what outcomes would narrow or retain the practical-method
   claim. Do not describe profile support as a confidence interval.
3. **Do not substitute a balanced four-case blinded panel.** One case in each
   selected cell could demonstrate qualitative transfer, but it would not
   estimate power, false-declaration rate, bias distribution or coverage.
   Blinding protects analysis discipline; it does not create replication.
4. **Pursue Goal 046 method work only for stronger numerical generality.** Use
   independent/high-accuracy qualification before scientific reanalysis, or
   retain the accepted conditional negative result and its failed gates.
5. **Run a common candidate-model experiment only if generating-family
   discrimination remains a Paper 1 claim.** The proposed final-procedure panel
   cannot substitute for fitting every candidate to every generator. A residual
   spatial-field selection claim requires a fitted candidate that represents
   that field.
6. **Define a magnitude-interval method before a coverage experiment.** More
   histories alone cannot validate an interval that does not yet exist. The
   current profiles are diagnostics and the current calibrated endpoint is a
   null declaration.

## 6. Residual uncertainty

Even after these corrections, the paper cannot claim landscape-population
generality, reliable generating-family selection, final-method positive-effect
power, off-grid or B100-A error control, performance averaged over new reference
tables, or calibrated magnitude intervals for the nuisance-estimating fit.
Those are explicit scientific limits, not reasons to rerun the valid all-null
capstone.

The proposed six-cell panel would narrow only the fixed-map, fixed-table
positive-effect gap at two nuisance anchors. Whether that gain justifies its
reference-generation and audit cost is a human scientific decision tied to the
manuscript's intended endpoint. No current evidence shows that a larger campaign
would alter the already supported controlled-laboratory conclusions.
