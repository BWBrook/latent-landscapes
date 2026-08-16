# Paper 1 Experimental Design Charter

- **Status:** Approved programme direction, 16 August 2026
- **Scope:** Synthetic spatial predator-prey methods paper
- **Role:** Governing scientific North Star for future Paper 1 goals

## Purpose

This charter defines what the first Latent Landscapes paper is intended to
establish, what evidence is needed, and what counts as complete. It is not a
fixed sequence of simulations. Individual goals remain adaptive, but each must
advance a named part of this charter or close a material uncertainty that
blocks it.

The existing synthetic landscape is the reference laboratory, not an object to
perfect indefinitely. It should be closed at a scientifically useful point,
frozen as an anchor case, and then used to support broader tests of process,
observation, landscape, and model conditions.

## Definitive Question

> Under what landscape, process, and observation conditions are the parameters
> of spatially explicit predator-prey dynamics identifiable and recoverable
> from imperfect data, and how well is inferential uncertainty calibrated when
> the generating system is known?

## Intended Scientific Contribution

Paper 1 will test and characterise the proposition that recoverability in
spatial predator-prey systems is a property of the whole experiment:
ecological signal, landscape structure, observation design, model
specification, and uncertainty calibration.

Known-truth experiments should distinguish at least four causes of weak
inference:

1. the ecological process leaves little distinguishable signal;
2. the sampling design or survey window fails to observe that signal;
3. the fitted model differs materially from the generating process; or
4. the uncertainty method fails to represent the information in the data.

The paper need not conclude that every parameter is identifiable. A clear map
of where recovery fails, and why, is a substantive scientific result.

## Working Definitions

- **Identifiability:** whether distinct parameter values or models generate
  sufficiently distinguishable observable patterns under a stated design.
- **Recoverability:** finite-data operating performance when estimating a known
  generating value, including bias, precision, and reliable exclusion of
  scientifically relevant null values.
- **Calibration:** whether reported uncertainty contains the generating truth
  at its intended long-run frequency under the stated experiment.
- **Prediction:** performance on observations withheld from model fitting.
- **Model discrimination:** whether the generating model can be distinguished
  from prespecified alternatives and neutral comparators.

These terms must always be qualified by the landscape, process, observation,
candidate-model, and calibration conditions under which they were evaluated.

## Paper Boundary

### Included

- synthetic landscapes and known generating truth;
- predator spread, landscape resistance, imperfect detection, and prey
  response;
- individual and selected joint parameter recovery;
- uncertainty calibration;
- held-out prediction against fitted neutral baselines;
- a small prespecified alternative-model set;
- generality across a designed family of landscape and sampling conditions;
- one ecologically credible synthetic stress test.

### Excluded

- inference from real mink-water vole data;
- inference from Australian murid, cat, or fox data;
- exhaustive coverage of every plausible ecological mechanism;
- a claim of universal identifiability thresholds;
- full factorial exploration merely because it is computationally possible;
- production software compatibility or enterprise-style validation machinery.

A known-truth Great Britain analogue is best treated as a bridge into Paper 2,
not as the main realistic test in Paper 1, unless later scientific review finds
a compelling reason to change that boundary.

## Evidence Pillars And Definition Of Done

### 1. Trusted Reference Laboratory

The current synthetic landscape must provide an understood positive-control
ladder for:

- predator spread rate;
- landscape-resistance contrast;
- predator detection;
- prey effect and background prey turnover; and
- selected joint estimation problems.

The reference case is complete when remaining questions would refine a
numerical transition rather than overturn the interpretation or prevent design
of the broader experiment. Consequential open issues currently include the
fourfold prey-effect transition, dependence on background prey hazard, and the
defensible interpretation of parameter-specific versus simultaneous joint
uncertainty.

### 2. Recoverability Map

The paper must describe how inference changes over a prespecified domain of
ecological and observational conditions. Candidate dimensions include:

- spread rate and resistance contrast;
- prey-effect strength and background prey turnover;
- detection probability;
- survey frequency, duration, and effort; and
- sampling density and access bias.

The output is a response surface or recovery map, not a catalogue of isolated
pass/fail experiments. It should identify important transitions and
interactions while retaining interpretable anchor cases.

### 3. Landscape And Sampling Generality

The main conclusions must be tested across a small, designed family of
ecologically interpretable landscape and access-network archetypes. Candidate
contrasts include open connected landscapes, fragmented or corridor-dependent
landscapes, barrier-dominated landscapes, and alternative source geometries.

Several generated realizations within an archetype should separate properties
of a landscape class from accidents of one map. Sampling design is a related
but distinct layer and may include access-biased, habitat-targeted, spatially
balanced, and one carefully justified adaptive design.

### 4. Model Discrimination And Misspecification

Data must be generated under the preferred model and a small set of plausible
alternatives. Each dataset should be assessed under the competing models and a
neutral predictive baseline.

This pillar asks both:

1. whether parameters are recovered when the fitted model is correct; and
2. whether incorrect model structure can be detected before its parameter
   estimates are interpreted ecologically.

The alternative-model set must remain small enough that every member has a
clear scientific purpose.

### 5. Synthetic-Realistic Capstone

One integrated scenario should combine an ecologically credible landscape,
stochastic spread, biased access, imperfect observation, and prey response.
The generating truth should be frozen before analysis and concealed from the
analysis step where practical.

After inference is complete, truth is revealed and the analysis is audited.
The purpose is to demonstrate diagnostic transfer from controlled experiments,
not to prove that the full real-world problem is solved.

### 6. Lean And Transferable Implementation

The final research code should expose reusable scientific components for:

- landscape generation and description;
- predator spread;
- observation processes;
- prey response;
- likelihood or other inference;
- experimental design; and
- evaluation and visualisation.

Goal-specific developmental code is not permanent architecture. Git history and
goal records preserve provenance, allowing superseded paths, redundant tests,
and elaborate artifact contracts to be removed during scheduled consolidation.

## Standard Evaluation Surface

Not every experiment needs every metric, but the paper-level evidence should be
expressed through a stable, interpretable set:

- point-estimate bias and absolute error;
- uncertainty width and topology where relevant;
- empirical coverage;
- probability of excluding a scientifically relevant null;
- held-out predictive score relative to neutral;
- model-selection or discrimination success; and
- an explicit failure classification.

Computational diagnostics remain supporting evidence rather than scientific
endpoints unless they affect validity.

## Experimental Principles

1. **Known truth first.** Record generating values and design choices before
   examining recovery outcomes.
2. **Positive controls before complications.** Demonstrate that a quantity can
   be recovered under favourable conditions before adding observation or
   process uncertainty.
3. **Change one scientific layer at a time when diagnosing mechanisms.** Use
   broader multivariate designs only after the component effects are understood.
4. **Separate observation from inference.** Report what the simulations show,
   what is inferred, and what remains conditional.
5. **Retain neutral and alternative comparators.** Parameter recovery alone is
   insufficient if a simpler model predicts equally well.
6. **Use held-out evidence.** Evaluate prediction outside the data used to fit
   the model.
7. **Treat negative results as results.** Do not silently retune truths, grids,
   landscapes, or success criteria after seeing production evidence.
8. **Prespecify consequential decisions.** Calibration targets, comparison
   rules, and stopping boundaries should precede the evidence they judge.
9. **Use proportional engineering.** Verification must protect the scientific
   decision, not reproduce enterprise infrastructure.

## Paper-Level Stopping Rule

Paper 1 is ready for synthesis when:

- all six evidence pillars have a defensible result;
- the important failure modes can be attributed rather than merely observed;
- the principal conclusions persist across the prespecified landscape and
  model families, or their limits are clearly described;
- the synthetic-realistic capstone has been analysed without post hoc truth
  tuning;
- the active code path is modular, reproducible, and lean; and
- further simulation is unlikely to change the scientific decisions, even if
  it could refine individual numerical boundaries.

## Anticipated Manuscript Structure

The planned evidence should support approximately six main visual arguments:

1. conceptual framework and reference synthetic laboratory;
2. reference-case recovery ladder;
3. recoverability surface across process and observation conditions;
4. generality across landscape and sampling designs;
5. model discrimination and misspecification; and
6. the blinded synthetic-realistic stress test.

This figure-level destination is a planning aid, not a requirement to force
every useful result into the main paper.

## Governance

- Barry reviews changes to estimands, model families, ecological assumptions,
  major factor domains, and the paper's claim boundary.
- The project orchestrator may decide routine, reversible implementation and
  experimental details when they remain within this charter.
- Every substantial goal should name the evidence pillar, decision, or planned
  manuscript output it advances.
- At the end of each major arc, scientific review precedes one bounded code
  consolidation tranche.
- This charter may be revised as evidence accumulates, but changes must be
  explicit. Unexpected results should change the roadmap before they silently
  change the question.
