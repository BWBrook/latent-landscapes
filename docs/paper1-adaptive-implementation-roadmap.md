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
recovery is not universal: 3/32 truths were fully recovered, 10/32 detected
the effect without passing every strict gate, and 19/32 were not reliably
detected. Every tested effect below threefold fell in the latter class. Event
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

Arc 2A, Arc 2B and Goal 045's six-case Arc 2C comparison are scientifically
complete, with numerical acceptance and independent final review recorded.
The paired result isolates the cost of estimating spread speed with detection,
background and resistance known. The evidence supports no detected systematic
added cost in these cases, while preserving weak absolute recovery and the
usual-speed fivefold coverage limitation.

The bounded bridge is closed. The next substantive programme decision concerns
generality beyond this reference model and design;
it requires a separate bounded scientific question. No new conditions,
landscapes, calibration method, response surface or later arc is authorized by
Goal 045. Its null result does not reopen the completed recoverability maps.
