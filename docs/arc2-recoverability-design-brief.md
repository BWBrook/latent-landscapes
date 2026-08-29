# Arc 2 Recoverability Design Brief

- **Status:** Provisional design for collaborator review
- **Charter role:** Pillar 2, Recoverability Map
- **Production authority:** None

## Scientific purpose

Arc 2 should replace isolated reference truths with continuous maps showing
where inference is accurate, precise, calibrated, and predictively useful. The
first block should remain predator-only. It asks how recovery changes jointly
with global spread rate, habitat-resistance contrast, and detection
probability, while the accepted landscape and observation budget remain fixed.

This ordering keeps the first multivariate experiment interpretable. The prey
layer and the combined predator-prey bridge follow only after the predator map
is understood.

## Arc 2A: Direct predator-observation map

### Factors and provisional domains

| Factor | Provisional domain | Sampling scale | Ecological role |
| --- | --- | --- | --- |
| Spread rate `rho` | `0.5` to `2.0` | uniform in `log2(rho)` | compresses or expands the invasion-wave timescale |
| Resistance contrast `eta` | `0.25` to `2.0`, plus `eta = 0` as a diagnostic boundary | continuous on the model scale | weakens or amplifies variation in movement cost among habitat edges |
| Per-visit detection `p` | `0.35` to `0.85` | linear probability scale | controls missed detections during repeated visits |

Retain interpretable anchors at `rho = 0.5, 1, 2`, `eta = 0, 0.5, 0.75, 1,
2`, and `p = 0.35, 0.65, 0.85` when reviewing the generated design. They do
not all need to be additional full factorial cells.

The `eta` domain is not frozen. Before production, translate candidate `eta`
values into induced edge-cost ratios and summaries for corridor, patch, matrix,
and water-adjacent movement on the reference landscape. Barry should approve a
range expressed in those ecological contrasts, not only in an abstract
exponent.

### Frozen experimental context

- the accepted reference landscape, access network, 160 sites, and spatial
  120/40 training/holdout split;
- six surveys on days 10, 20, 30, 40, 50, and 60;
- two visits per survey;
- homogeneous detection within a truth condition;
- zero false positives;
- the accepted stochastic spread generator and predator-observation
  likelihood; and
- the Arc 1 evaluation definitions and fitted neutral comparator.

Prey dynamics, prey observation, background prey risk, alternative landscapes,
sampling density, survey duration, visit count, false positives, heterogeneous
detection, model misspecification, and real data are excluded from Arc 2A.

### Staged design

1. Generate a reproducible 16-point scrambled Sobol block across the three
   continuous factor domains. These 16 new points define the initial response
   surface.
2. Evaluate `eta = 0` as a separately labelled diagnostic boundary cell, not as
   part of the continuous surface. Overlay compatible accepted Arc 1 anchors as
   external references rather than rerunning their full ensembles. A reduced
   central replay is an implementation reconciliation gate, not a new science
   cell.
3. At each new truth, use a local calibration ensemble of 250 histories and an
   independent validation ensemble of 250 histories.
4. Use common random numbers across design points to reduce Monte Carlo noise in
   contrasts, while keeping calibration and validation seed roots disjoint.
   Analyse paired contrasts as paired evidence rather than treating condition
   estimates as independent.
5. Review raw truth-level outcomes and a simple response surface before adding
   more points.
6. Only if the 16-point surface leaves a decision-relevant interaction or
   transition unresolved, run the next nested Sobol block to reach 32 points.
   Predict that second block from the first-block surface before refitting, so
   it provides prospective held-out design-point validation.
7. Permit at most eight targeted enrichment points near transitions that could
   alter a scientific conclusion. Enrichment is a human decision, not an
   automatic optimizer loop.

The initial 250 + 250 histories per truth are exploratory operating-performance
replicates, not a promise of final Monte Carlo precision. Increase replication
only if its uncertainty could change a substantive conclusion.

### Analysis and review surface

Continuous outcomes are primary:

- point-estimate bias and absolute error for `rho`, `eta`, and `p`;
- marginal and joint support widths;
- empirical coverage;
- boundary-contact and disconnected-support frequencies;
- probability of excluding `eta = 0` where relevant;
- held-out predictive advantage over neutral; and
- failure-mode probabilities.

Start with a transparent low-order response surface using transformed main
effects and only scientifically interpretable two-way interactions. Inspect
residuals and leave-one-design-point-out predictions. Do not introduce a
Gaussian-process emulator or elaborate adaptive design unless the simple model
materially fails and a more complex model would change the scientific
decision.

Pass/fail gates remain secondary annotations. The manuscript output is a
recoverability surface with uncertainty, not a coloured catalogue of binary
cells.

### Compute and reproducibility

Develop and smoke-test on the Mac mini. Run the production ensembles on
`deep-server` with bounded parallel workers and detached execution. Record the
Sobol scramble seed, factor transform, truth table, calibration and validation
seed roots, code commit, runtime, and compact condition summaries. Do not retain
raw histories when a replayable seed manifest and decision-relevant summaries
suffice.

### Stop rules

- Stop after the 16-point review unless more points could change factor-domain,
  interaction, or recovery-boundary conclusions.
- Stop and redesign if central anchors fail to reconcile Arc 1 or if the
  ecological translation rejects the proposed `eta` range.
- Extend to 32 only after Barry reviews the first surface and its Monte Carlo
  uncertainty.
- Add no more than eight targeted points, and only for a named unresolved
  decision.
- Stop the arc when major transitions and interactions are stable enough for a
  paper claim; local contour polish is not a reason to continue.

## Later Arc 2 blocks

### Arc 2B: Prey-effect and event-information map

After Arc 2A, map prey-effect recovery across an ecologically expressed
predator-effect range and counterfactual 60-day background extirpation risk.
Begin with known predator arrival and perfect or known prey observation. Use
Arc 1's threefold/fourfold effect and 5%/11.3%/20% background-risk anchors.

### Arc 2C: Selected predator-prey bridge

Combine only the interactions that Arc 2A and 2B show to be decision-relevant.
This is not a full cross-product. It should test whether separately understood
recovery transitions persist when spread and prey response are estimated
together, and it must retain the distinction between marginal and simultaneous
joint uncertainty.

## Decisions required before Arc 2A production

Barry should explicitly approve or modify these five choices:

1. **Predator-only first:** Arc 2A varies `rho`, `eta`, and `p`; prey is deferred
   to Arc 2B.
2. **Factor domains:** `rho = 0.5-2` on a log2 scale, `p = 0.35-0.85`, and an
   `eta` domain accepted only after ecological edge-cost translation.
3. **Fixed observation budget:** retain the current sites, split, six survey
   times, two visits, and zero false positives throughout Arc 2A.
4. **Continuous outcomes first:** model recovery and prediction surfaces;
   display pass/fail gates only as secondary interpretation aids.
5. **Staged compute:** review 16 Sobol points before any extension to 32, then
   allow at most eight human-approved targeted enrichment points.
