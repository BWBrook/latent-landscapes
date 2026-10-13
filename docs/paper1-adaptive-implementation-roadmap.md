# Paper 1 Adaptive Implementation Roadmap

- **Companion to:** `docs/paper1-experimental-design-charter.md`
- **Planning horizon:** Synthetic methods paper
- **Status:** Adaptive programme map, not a fixed goal sequence

## Purpose

This roadmap translates the Paper 1 charter into scientific arcs, decision
gates, and consolidation points. It deliberately avoids specifying every
future goal. Results from one arc may alter the most useful question in the
next, but should not alter the paper's governing purpose without explicit
review.

## Current Position

The [11 October charter-level evidence synthesis](paper1-evidence-synthesis-2026-10-11.md)
is complete after the capstone truth assessment. The main proposed experiment
is a replicated evaluation of the final observed-nuisance procedure at null
and positive effects, if it is presented as a practical positive-effect method.
Earlier procedure generations supply substantial recovery, power and
calibration evidence, but those operating properties cannot be
transferred to the final method. Landscape numerical qualification and the
common competing-model ambition also remain material charter decisions.
No new experiment or change to the charter is authorized by this synthesis.
Barry subsequently requested preparation of
[Goal 062's six-cell prospective design](goals/062-final-procedure-evaluation/registration-2026-10-11.md),
with 500 histories per cell, calibration-reference costing and independent
review before launch. Barry then approved the
[ten-cell B100-A amendment](goals/062-final-procedure-evaluation/amendment-2026-10-11.md)
with independent review followed by implementation, qualification, the bounded
run and audit without another routine approval. Amendment and
[implementation reviews](goals/062-final-procedure-evaluation/implementation-review-2026-10-11.md)
are complete; [nonproduction qualification](goals/062-final-procedure-evaluation/execution.md)
passed on Deep, with [independent receipt review](goals/062-final-procedure-evaluation/qualification-review-2026-10-11.md)
supporting acceptance. Barry [approved the qualified runtime and launch](decisions/2026-10-13-goal062-runtime-approval.md)
on 13 October; production began at 22:51 AEDT on Deep with 51 workers after
the runtime and custody checks passed again. The planning estimate remains
46–57 hours, with the unchanged persistent deadline at 22:51 AEDT on
16 October. The campaign is completing references before evaluating histories.

Arc 1 is frozen. Arc 2A and Arc 2B have completed prospectively tested
32-truth recoverability syntheses on one accepted landscape and observation
design. The working
end-to-end reference laboratory has demonstrated:

- recovery of spread rate across several wave speeds;
- a practical transition from weak to informative resistance contrast;
- interaction between wave timing, survey window, and detection precision;
- a strict prey-effect recovery transition between threefold and fourfold at
  the reference background risk, plus conditional loss of precision at low
  event yield;
- recovery of a strong prey effect under imperfect observation and latent
  predator arrival; and
- a distinction between informative point estimates, parameter-specific
  uncertainty, and an overly broad simultaneous joint envelope.

The predator recoverability map adds prospectively validated relationships for
detection precision, resistance precision, resistance exclusion, and held-out
predictive advantage across continuous spread-rate, resistance, and detection
conditions. Boundary contact remains a truth-level topology diagnostic rather
than a reliable smooth surface. These results meet the Arc 2A exit gate but do
not establish generality across prey-process conditions, landscapes, sampling
designs, or generating models. The accepted Arc 2A path has now been
consolidated into one frozen design, one campaign kernel, and one synthesis.

The prey-effect map varied the true predator-effect multiplier, counterfactual
60-day background prey-loss risk, and known prey detection. All five low-order
surfaces learned from the first 16 truths predicted the untouched second 16
better than the frozen pilot mean. The map is informative precisely because
recovery is not universal. The historical classifier gives 3/32 fully recovered,
10/32 detected but incomplete, and 19/32 not reliably detected. The accepted
[coverage-free interpretation](goals/049-operational-calibration/interpretation-amendments.md)
gives 4/9/19, changing only S08; the historical table remains unchanged.
Every tested effect below threefold fell in the weak-detection class. Event
yield and observation quality help explain this transition, but remain
conditional associations within the synthetic experiment.

The Arc 2B pilot prompted a disclosed comparator amendment before prospective
simulation: the primary no-effect model now receives the same known background
hazard as the process model, while the fitted neutral remains a secondary
description. Exact replay preserved the histories, calibration, and cutoffs.
The accepted Arc 2B path is consolidated into the same clear
`design -> campaign -> synthesis` structure. Goal 045's Arc 2C bridge is now
scientifically closed after numerical acceptance and independent final review. Across six
paired cases, estimating spread speed produces no detected systematic
prey-effect recovery penalty; all 30 paired bootstrap intervals include zero.
This is not equivalence, and both analyses remain weak in the threefold cases
and the slow fivefold case. Usual-speed fivefold effect coverage is 91.6% in
both analyses. The [synthesis](goals/045-spread-prey-oracle-bridge/synthesis.md)
records the conditional claim and uncertainty. A documented G201 grid repair
and 65536/131072 bank comparison resolved the numerical review without changing
the scientific cases, calibration rule or acceptance tolerances.

## Arc 1: Close And Freeze The Reference Case

### Objective

Resolve only the remaining questions that materially affect the design or
interpretation of the broader study.

### Resolved decision targets

- fourfold prey effect sharpened strict recovery to a threefold-fourfold
  reference-case bracket;
- low, reference, and high counterfactual 60-day background extirpation risks
  distinguished reliable detection from event-limited precision;
- parameter-specific intervals are defensible marginal statements, while the
  tested simultaneous joint region remains too broad;
- core estimands, standard response metrics, and the reference design are
  frozen; and
- remaining generality questions move to the broader sensitivity design.

### Exit gate

Freeze the reference case when additional work would mainly polish transition
locations rather than change factor selection, interpretation, or downstream
experimental design.

**Gate met:** accepted Arc 1 evidence now satisfies this condition. Reopening a
reference truth requires a new decision-relevant reason, not a desire to refine
its threshold.

### Fallback

If a component remains unresolved, preserve it as an explicit failure mode or
conditional result. Do not hold the entire programme hostage to perfect
recovery of every joint quantity.

## Arc 2: Map Process And Observation Recoverability

### Objective

Estimate how recovery, calibration, and prediction vary jointly across the
continuous ecological and observation conditions that matter most.

### Factor families

Process candidates include spread rate, resistance contrast, prey-effect
strength, and counterfactual 60-day background extirpation risk. Observation
candidates include detection probability, survey duration, survey frequency,
sampling effort, and sampling density.

The final factor list and ranges require scientific review before production.
Factors should be included because they test a paper claim, not merely because
the simulator exposes them.

### Layered design

1. **Anchor contrasts:** retain a small number of easily interpreted reference
   and boundary cases.
2. **Space-filling sample:** cover the continuous factor domain efficiently.
   A scrambled Sobol sequence is provisionally preferred because it can be
   extended sequentially; a well-designed Latin hypercube remains a reasonable
   alternative.
3. **Stochastic replication:** repeat process and observation realizations at
   each design point sufficiently to estimate operating performance.
4. **Adaptive enrichment:** add points near important transitions, interactions,
   or uncertain regions only when doing so could change the scientific
   conclusion.

Do not mix structural landscape or model categories indiscriminately into one
continuous design. Those belong to explicit scenario blocks in later arcs.

### Primary outputs

- bias and absolute error surfaces;
- interval width and coverage surfaces;
- null-exclusion probability;
- held-out predictive advantage over neutral;
- failure-mode classification; and
- interpretable estimates of important main effects and interactions.

The analysis should begin with the simplest response-surface method that
adequately describes these patterns. More elaborate emulation is justified only
if the initial design shows that it changes interpretation or enables material
compute savings.

### Exit gate

Stop when the major transitions and interactions are stable enough to support
paper-level conclusions and additional points mainly refine local contours.

## Arc 3: Test Landscape And Sampling Generality

Current status, 18 September 2026: the bounded comparison in
[Goal 046](goals/046-landscape-sampling-generality/Goal.md) is closed as a
[conditional synthesis](goals/046-landscape-sampling-generality/synthesis.md),
following Barry's delegated continuation and
[independent review](goals/046-landscape-sampling-generality/endpoint-final-review-2026-09-18.md).
No general sampling-design effect is resolved at this replication, with a
barrier fivefold candidate exception: lower point error and wider
truth-calibrated supports. Coverage and null-truth false exclusion are
calibration checks, not design-benefit evidence; the
[correction](goals/046-landscape-sampling-generality/calibration-interpretation-correction-2026-09-18.md)
records this distinction. Neither equivalence nor a blanket null is claimed. Absolute recovery,
paired archetype contrasts, map variation and landscape/event descriptors are
reported. Uncertainty conditions on the supplied maps and truth-calibrated
support procedure.

The [retrospective reporting amendment](goals/046-landscape-sampling-generality/endpoint-amendment-2026-09-18.md)
does not turn the original four final-bank failures into passes. Exact
integration accuracy and general method qualification remain unresolved.
The [original numerical diagnosis](goals/046-landscape-sampling-generality/final-bank-diagnosis.md),
[Goal 047 regulariser screen](goals/047-integration-validation/results.md) and
[Goal 048 prototype result](goals/048-integration-redesign/results.md) remain
part of the evidence. The prototype is not adopted. No process-bank or
calibration enlargement is required for this conditional conclusion, and none
is launched. Stronger accuracy, operational calibration or landscape-population
claims require a separately scoped study. Other candidate layers below remain
future options, not implied completion claims or authorized launches.

### Objective

Determine which recovery conclusions generalise beyond the reference map and
which depend on landscape or access geometry.

### Landscape structure

Define a small set of procedural, ecologically interpretable archetypes rather
than many arbitrary maps. Candidate families include:

- open and well-connected habitat;
- fragmented, corridor-dependent habitat;
- barrier-dominated habitat; and
- alternative source number or source geometry.

Generate several realizations within each accepted archetype. Record landscape
descriptors such as fragmentation, connectivity, barrier burden, source
geometry, and path-cost heterogeneity so that results can be explained rather
than merely grouped by map identifier.

### Sampling structure

Treat access and sampling as a separate experimental layer. Candidate designs
include:

- road- or transect-constrained access;
- habitat-targeted effort;
- spatially balanced effort; and
- at most one adaptive design with a clear ecological rationale.

Sampling effort and training/holdout logic should be comparable across designs
unless effort itself is the focal contrast.

### Experimental structure

Use a small factorial or crossed set of landscape and sampling archetypes for
interpretability. Within each structural block, use selected anchor conditions
or a reduced continuous space-filling design from Arc 2. Do not repeat the full
global campaign in every map unless the evidence demonstrates that it is
necessary.

### Exit gate

Conclude the arc when the main findings can be classified as robust,
landscape-dependent, sampling-dependent, or unresolved across the prespecified
families.

## Arc 4: Test Model Discrimination And Misspecification

Known-nuisance calibration bridge completed, 20 September 2026:
[Goal 049's revised contract](goals/049-operational-calibration/plan.md),
[claims audit](goals/049-operational-calibration/claims-audit.md) and
[pre-run registration](goals/049-operational-calibration/registration-2026-09-20.md)
incorporate Fable's thread 44 critique. Barry instructed Astra to proceed.
Candidate-specific tests on the existing effect grid with supplied speed
separate calibration checks from set resolution and non-null power. The
matched-weight bank comparison and descriptive regulariser sweep have distinct
roles. Historical classifications remain alongside retrospective interpretation
amendments. This bridge precedes the misspecification experiment below; it
does not replace Pillar 4 or choose its alternative-model set.
The [completed synthesis](goals/049-operational-calibration/synthesis.md)
passes all 36 matched-bank endpoint tolerances. It retains the realised
7.4% null false-exclusion rate (calibration-aware 95% interval 5.6–9.7%)
as a calibration-quality flag. Arc 4 should freeze this calibration rule and
include a matched-generator baseline under the same table, so departures
from its realised baseline are distinguished from nominal-rate discrepancies.
The subsequent approved generator comparison is recorded below.

The [Goal 050 detector](goals/050-model-adequacy/synthesis.md) completed its
assumed-model baseline. The [Goal 051 screen](goals/051-misspecification-screen/synthesis.md)
then evaluated 17 paired cells with 1,000 complete histories each under the
frozen analysis. Aligned background variation at the null is the sole
nomination: primary H rises by 23.0 percentage points [19.9,25.9], while
the primary detector rejects 2.7%. Prey-detection heterogeneity also causes
errors and is more often detected; failed predictions remain recorded.
These results establish a conditional generator–analysis vulnerability, not
model discrimination or completion of this arc. The original
[independent two-cell confirmation proposal](goals/051-misspecification-screen/confirmation-proposal.md)
remains an unchanged historical record. Following Fable's critique, Astra's
[24 September response](goals/051-misspecification-screen/fable-response-2026-09-24.md)
withdraws that recommendation and proposes an
[adjusted-background identifiability pilot](goals/051-misspecification-screen/adjusted-background-pilot-proposal.md)
on 24 archived histories with the current surveys and an adjusted neutral
comparator. Barry approved the confirmation-first sequence amendment and the
[Goal 052 pilot](goals/052-adjusted-background-pilot/registration-2026-09-24.md)
on 24 September, also delegating resource/timing choices. The completed
[pilot synthesis](goals/052-adjusted-background-pilot/synthesis.md) establishes
computational feasibility but leaves broad h–beta trade-offs and no consistent
predictive repair. The oracle-sharpening expectation was not supported.
The [prospective proposal](goals/052-adjusted-background-pilot/prospective-comparison-proposal.md)
therefore adds exact nonzero-beta controls and known-beta diagnostics on fresh
histories, with direct error and prediction comparisons. Fable reviewed it and
Barry approved the six-cell comparison on 27 September. The
[Goal 053 registration](goals/053-prospective-background/registration-2026-09-27.md)
fixes 1,000 paired blocks and the diagnostic subsets. Its
[completed synthesis](goals/053-prospective-background/synthesis.md) finds
conditional error reduction under exact nonconstant and residual-field
backgrounds, with a substantial flexibility cost under constant background.
Direct predictive gains are smaller than forecast, and oracle arrivals change
matched averages little. The
[calibration proposal](goals/053-prospective-background/null-effect-calibration-proposal.md)
was reviewed and approved with a nonlinear stress pair. The
[Goal 054 synthesis](goals/054-null-effect-calibration/synthesis.md), completed
30 September, supplies a finite-grid adjusted null-effect decision and its
fresh eight-cell evaluation. It reduces aligned-null declarations at a
measurable sensitivity cost, while retaining the constant-background estimation
cost. The primary cutoff is set by an interior beta; Berger–Boos recovers no
sensitivity, and the nonlinear contrast does not locate a failure boundary.
The guarantee averages over reference/evaluation generation at exact registered
nodes; the realised table has no conditional 5% guarantee. Magnitude confidence
calibration and broader model discrimination remain unresolved. The original
Goal 051 nomination remains unconfirmed under its registered endpoint/rule.
Barry approved [Goal 055](goals/055-arc4-synthesis/registration-2026-10-01.md)
on 1 October; it was [completed](goals/055-arc4-synthesis/synthesis.md) on 2 October.
The Arc 4 claim audit, paper draft/figures and concrete capstone protocol retain
the earlier experiments as separate evidence. Under the unchanged Goal 054
rules, supplied mean .8 times truth raises adjusted null declarations to
7.8%/10.8%, and persistent prey-detection SD .20 yields 19.8% versus a paired
3.8% baseline. Both registered design failures trigger. The protocol selects
60 days of pre-invasion monitoring and a shared site-detection model, with an
observed-data likelihood/timing feasibility tranche before separate calibration
or any sealed truth draw. Fable is the future truth-holder; Astra is blinded.
The exact background-state mixture and model/report locks are specified in the
[protocol](goals/055-arc4-synthesis/capstone-protocol.md). The independent review
supports closing this synthesis; neither the prerequisite nor capstone has
launched. Charter Pillar 4's common competing-model requirement and Pillar 5's
blinded application remain open. Fable's critique in thread 53 messages 811–813
was read and acknowledged on 3 October. [Astra's response](goals/055-arc4-synthesis/fable-response-2026-10-03.md)
recommends a scalable calibration route as a feasibility deliverable, four
sealed histories and private key/draw custody. Barry approved the bounded
[Goal 056 feasibility study](goals/056-observed-nuisance-feasibility/registration-2026-10-03.md)
on 3 October, with scalable calibration required at closeout. He approved four
future sealed histories, simple blinding against accidental exposure and his
password manager for private-key custody. [Goal 056 is complete](goals/056-observed-nuisance-feasibility/synthesis.md):
64 main fits, sixteen pre-only fits and 7,088 profile nodes converged;
independent direct-bank replay passed. A separately frozen profile-only repair
preserved all histories and main fits. The sixteen fixtures show variable
magnitude estimates and weak h–mean-hazard separation in some histories;
no recovery, error-rate or coverage claim follows.
The [screening-retention proposal](goals/056-observed-nuisance-feasibility/calibration-proposal.md)
specified union-cap/failure handling and actual cost measurement before a
separate effect-reference pilot. On 4 October Barry supplied the public recipient;
Astra answered Fable's review as thread 53 message 880. The revised screening
pilot adds reused-reference nuisance-error checks and a global-surface
retention diagnostic. Barry approved this tranche with full execution authority
on 4 October; [Goal 057 is complete](goals/057-screening-retention/synthesis.md).
All 360,855 reference histories and 792 diagnostic fits completed in 6 min 37 s;
independent reconstruction passed. Retained sets have 420–990 nodes, with
four-fixture unions of 577–1,901 (median 1,266). All known true nodes are retained
in this fixed descriptive panel. The median union projects to 32–39 hours at
64 workers for the later effect references. Many retained nodes lie well below
the best global grid score, motivating the
[next proposal](goals/057-screening-retention/next-stage-proposal.md): review one
fixed coarser global screen before large calibration. Registered log-background
errors do not show a common upward shift; the supplementary arithmetic mean
error is +3.95%, not a general 20% inflation. Neither establishes full-data
effect bias or unbiasedness. The stream-preview and reporting repairs are
disclosed. New-map qualification, large calibration and capstone generation
remain separate decisions; no sealed draw has run.
Barry's later 4 October decision approved
[Goal 058](goals/058-effect-reference-micro-pilot/registration-2026-10-04.md):
coarsen only the beta reference lattice to .25 (765 nodes), skip the proposed
global screen for now, and run the fixed four-node, 3,996-history full effect
micro-pilot. The continuous fitting algorithm is unchanged.
[Goal 058 is complete](goals/058-effect-reference-micro-pilot/synthesis.md):
all 3,996 null/free pairs and all independent direct-bank checks passed; all
four 999-reference tables are usable. Production plus audit took 29.64 minutes
with 7.461 GiB sampled peak RSS, after Linux 209-test qualification. Strong
boundary behaviour at the low-rate corner remains informative: 73 null
histories reached h=10. This is four-node pipeline feasibility, not power,
coverage, magnitude recovery or full-grid reliability. The
[next proposal](goals/058-effect-reference-micro-pilot/next-stage-proposal.md)
measures the existing local screen on the approved 765-node support with fresh
99-reference tables. Large tables, a final sealed truth distribution and new
map qualification remain separate decisions. The old beta=.6 and residual-field
branches cannot silently inherit an on-grid exact-family guarantee.
Resources/time remain delegated within approved scope.
Barry then approved [Goal 059](goals/059-capstone-preparation/registration-2026-10-04.md):
skip the old-map screening pilot, use the whole 765-node union without a smaller
cost cap, adopt Fable's public truth law and prepare the new connected map.
Eight fixed public fixtures qualify the numerical method before Fable's four
sealed draws. [Goal 059 closed with a preserved negative qualification](goals/059-capstone-preparation/synthesis.md):
the first structurally accepted map's conservative transform bound was 5.350, beyond the
frozen 5.0 domain. Independent reconstruction reproduced the failure before
bank or fixture generation. The fixed map and approved design remain. A post-stop
calculation gives an actual maximum of 4.894 within the domain. Barry approved
[Goal 060](goals/060-capstone-certificate-recovery/registration-2026-10-04.md)
to use 1,024 certificate intervals on the same map, complete the unchanged
public qualification and prepare the sealing script for Fable's review.
[Goal 060 completed public qualification](goals/060-capstone-certificate-recovery/synthesis.md)
on 5 October. The refined bound is 4.92854; the fixed 131,072-history bank,
eight fixtures and all producer and independent numerical gates passed.
A narrow audit-interface repair retained all scientific outputs and criteria,
with the original failed audit and Goal 059 failure preserved. The sealing
script's public preflight passed, enabling Fable's final leak review and sealed
generation. Earlier
development deviations remain disclosed and excluded from qualification.

Fable completed that review and the single four-case seal on 5 October. Barry
authorized [Goal 061's blinded training analysis](goals/061-blinded-capstone-training/analysis-plan-2026-10-05.md).
The unchanged scientific procedure passed qualification through new training
and audit adapters before actual training inspection. Blinded production
launched at 13:20 AEDT on 5 October with 51 workers and ended normally at
04:51 AEDT on 6 October. All four training audits, the 75,735-reference screen
and all 298,701 effect references at the 299 union nodes passed the independent
numerical audits. The
[completed report](goals/061-blinded-capstone-training/training-report.md)
records four valid non-declarations (p_BB 1, 1, 0.422, 1), with no abstention
or diagnostic hold. These results do not establish absence or recovery of an
effect. The [execution record](goals/061-blinded-capstone-training/execution.md)
preserves three mechanical interface failures and the separate repair freezes.
The [training lock](goals/061-blinded-capstone-training/training-lock.md)
binds the complete returned evidence, independent claims review, figures and
unchanged predictive specification and prereveal forecasts. This completes the
blinded training endpoint. Claude (historically Fable) accepted the lock on
6 October in thread-53 message 1054 after independently verifying all 3,734
bound files. Barry released the committed holdout on 8 October. The
[combined report](goals/061-blinded-capstone-training/complete-report.md) evaluates
all 16 unchanged fits: the case-00 leading-pair forecast matches, while the
three other pair forecasts miss. The independent direct-bank audit reproduces
every maximizing set and forecast outcome. No calibrated declaration changes,
and these four comparisons do not establish recovery or operating rates. The
complete report passed independent review and was
[locked before truth release](goals/061-blinded-capstone-training/complete-report-lock.md).
Claude accepted that lock on 9 October in thread-53 message 1278; Barry then
released truth. The [truth assessment](goals/061-blinded-capstone-training/truth-report.md)
closes the registered forecast checks: all four truths are h=1, with exact
backgrounds in cases 00/03 and B100-A in 01/02. The four primary null forecasts
are correct; the two B100-A branch forecasts were wrong. Mu grid forecasts hit
three cases and detection-SD points hit all four. No original result changed.
This all-null realization cannot demonstrate positive-effect power or recovery,
and the B100-A cases lie outside the exact-family on-grid guarantee. The
capstone should enter the paper as a bounded blinded demonstration, with its
negative and ambiguous comparisons retained. The
[completed charter synthesis](paper1-evidence-synthesis-2026-10-11.md)
separates earlier operating evidence from unmeasured final-procedure recovery,
power and magnitude coverage, and recommends bounded prospective follow-up
subject to scientific review.

### Objective

Test whether reliable parameter estimates depend on already knowing the correct
generating model.

### Model set

Prespecify a preferred model, a small number of scientifically plausible
alternatives, and a neutral predictive comparator. Alternatives should differ
in an interpretable process assumption, not merely in arbitrary mathematical
form.

### Core design

- generate data under each model;
- fit each candidate model to each generated dataset;
- evaluate parameter recovery only where parameters have comparable meanings;
- compare held-out prediction and model-selection evidence; and
- quantify parameter bias when the wrong model is nevertheless selected or
  retained.

### Exit gate

The paper should distinguish settings where the generating model is reliably
selected, where several models are predictively equivalent, and where
misspecification produces misleading ecological estimates.

### Fallback

If formal model selection proves unstable, report a model-equivalence region or
predictive ambiguity rather than manufacturing a winner.

## Arc 5: Synthetic-Realistic Capstone

### Objective

Pressure-test the accepted workflow in one integrated ecological scenario while
truth remains available for final audit.

### Design principles

- use an ecologically credible but generic landscape rather than a literal
  Great Britain analogue;
- combine only complications justified by earlier arcs;
- freeze the generator, observation design, and truth before analysis;
- separate the role that knows truth from the analysis role where practical;
- analyse the observations as if they were field data; and
- reveal truth only for the final recovery and failure audit.

### Exit gate

The capstone is complete when it demonstrates which lessons transfer to the
integrated case, which break down, and why. Success does not require every
parameter to be recovered.

## Arc 6: Synthesis And Paper-Ready Consolidation

### Objective

Convert the accepted scientific evidence into a coherent manuscript and one
lean, transferable active workflow.

### Scientific synthesis

- reconcile claims against prespecified evidence;
- separate robust conclusions from landscape- or design-specific findings;
- select main figures and move secondary evidence to supplements;
- state remaining uncertainty and non-identifiability directly; and
- articulate how Paper 1 informs the known-truth bridge and real-data analysis
  in Paper 2.

### Code synthesis

- retain reusable kernels for landscape, spread, observation, prey, inference,
  design, and evaluation;
- replace goal-specific duplication with shared components only after repeated
  use has demonstrated the correct abstraction;
- delete superseded scripts, compatibility code, redundant artifact contracts,
  and tests that protect no live scientific decision;
- retain a few numerical invariants and representative end-to-end workflows;
  and
- use Git history and goal records as provenance rather than keeping obsolete
  code active.

## Consolidation Cadence

Perform one bounded leanification tranche after each major scientific arc, not
after every goal and not only at the end of the paper.

Each tranche should answer:

1. Which scientific components are now stable and reusable?
2. Which code existed only to reach a historical decision?
3. Which tests protect a consequential numerical or inferential property?
4. Which tests merely preserve an obsolete artifact shape or implementation?
5. Is there one obvious active route through the accepted workflow?

Stop after one focused review and repair pass unless a material scientific or
data-integrity defect remains.

## Goal Selection Rule

Every substantial future goal should state:

- which charter pillar and roadmap arc it advances;
- the scientific decision it enables;
- the review surface or likely manuscript output;
- the factor, assumption, or layer allowed to change;
- what remains frozen;
- a prospective stop rule; and
- whether the result triggers continuation, redesign, consolidation, or human
  adjudication.

A goal that cannot answer these questions probably does not yet deserve to be
run.

## Compute Strategy

- use the Mac mini for development, reduced smoke checks, and moderate
  experiments;
- use `deep-server` for long single-host campaigns and parallel ensembles;
- use `kunanyi` only when the design genuinely benefits from HPC scale;
- pilot runtime and memory before production;
- preserve compact scientific summaries and provenance rather than raw output
  volume; and
- use detached remote jobs for long runs rather than holding the orchestrator
  open without scientific work to do.

## Immediate Decision Boundary

The completed reference arcs and staged capstone remain closed. The
[Paper 1 synthesis](paper1-evidence-synthesis-2026-10-11.md) now supplies the
decision basis. The approved work is
[Goal 062 with the B100-A amendment](goals/062-final-procedure-evaluation/amendment-2026-10-11.md):
ten fixed cells, 500 independent histories each, and a complete fixed reference
panel. The [amended estimate](goals/062-final-procedure-evaluation/compute-estimate-amended-2026-10-11.md)
includes 465,534 new effect references and an estimated 46–57 hours on up to
51 workers, within the 72-hour ceiling. Independent amendment review is
complete, as is independent source review; nonproduction qualification has
passed and its independent review requires no repair. Barry accepted the exact
qualified runtime on 13 October and the bounded campaign is now running.
Completion, independent scientific audit and interpretation remain pending.
The broader landscape-generality and competing-process
model ambitions remain separate scientific decisions.
Narrow final-method claims about exact-grid null control, feasibility and the
blinded demonstration do not strictly require another simulation.

Numerically qualified landscape claims need an accepted integration method
before adding maps. Formal generating-family discrimination needs a common
candidate set capable of representing the chosen alternative. Final-method
magnitude coverage needs a defined interval method before an evaluation can
test it. None of these requirements is met by another four-case blinded panel.
Those broader changes remain outside the approved Goal 062 amendment.
