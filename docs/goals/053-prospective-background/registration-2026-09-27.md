# Goal 053: prospective comparison of spatial background adjustment

27 September 2026. **Approved; freeze before production outcomes.**
Charter Pillar 4 / Roadmap Arc 4.

## Authority and endpoint

Barry: “Fable has responded. I approve the proposed six-cell comparison.”
This approves the [24 September proposal](../052-adjusted-background-pilot/prospective-comparison-proposal.md)
following Fable's thread 53 messages 514–515. Resource and timing decisions
remain delegated to Astra. This registration makes routine numerical and
reporting choices concrete; it does not enlarge the scientific comparison.

Complete one independently reviewed comparison of estimation benefit,
flexibility cost and prediction under exact and incomplete background models.
Mixed and negative results are valid. Do not change replication or select a
favourable error scale after inspecting results. No old confidence cutoff,
new calibration, additional survey, unknown nuisance, landscape expansion,
commit, push or publication is authorized. Goal 051 remains unconfirmed under
its original procedure; all frozen Goal 049–052 results and failures remain.

## Fixed six-cell design

| Cell | h | Background |
| --- | ---: | --- |
| E0_h1 | 1 | Exact beta=0 |
| E0_h3 | 3 | Exact beta=0 |
| E06_h1 | 1 | Exact beta=+0.60 |
| E06_h3 | 3 | Exact beta=+0.60 |
| B100-A_h1 | 1 | Original CV1, mixing0.70, residual Gaussian field G |
| B100-A_h3 | 3 | Original CV1, mixing0.70, residual Gaussian field G |

Generate **1,000 paired blocks**, ordered as above within each block. Retain
the landscape, 120 training and 40 holdout sites, surveys at 10,20,30,40,50,60,
two visits, known detection 0.65, spread/resistance 1 and mu=0.002. Exact cells
use `lambda_i=.002*exp(beta*A_i)/mean_all_map(exp(beta*A))`, with the same
deterministic proxy and full-map normalization as the analyst. Beta=+0.60 is
fixed near the nominal A coefficient .70*sqrt(log2)=.583, not estimated from
the pilot. B100-A retains the original generator and has no true fitted beta.

The seven process/observation/field streams remain independent within a block;
the six cells share their process arrivals, prey thresholds, detection uniforms
and G where applicable. Fresh roots: production **2026092701**, timing
**2026092702**, summary bootstrap **2026092703**, smoke **2026092704**.
Spawn the complete production manifest of 1,000 blocks once, and preserve its
full-width seeds and opaque identities. Timing uses 20 disjoint blocks; smoke
uses two. Neither enters scientific estimates. Check seed collisions against
the known previous campaign and bank manifests before production.

## Analysis and diagnostic information

Use the unchanged qualified empirical-arrival likelihood: K131072, alpha1,
rho1; h=1..10 by .05 and beta=−2..2 by .05 (181×81). Compute every node for
all 6,000 actual latent-arrival fits. Compare constant beta0, free beta/h, and
adjusted h1. Exact ties choose lowest beta then lowest h. Holdout observations
never select fits, search bounds or model settings.

For all four exact-model cells, extract h fits with beta fixed to its true
value from the saved row. Label this as evaluator-assisted information.
Full oracle-arrival surfaces are restricted to blocks 0–249 in those four
cells (1,000 histories), including the known-beta diagnostic. All actual
scoring APIs receive analyst observations only; true arrivals enter the
explicit oracle scorer and evaluator diagnostics separately.

Keep both score surfaces, fitted coordinates, profile ranges/components and
the registered nested .10-grid check. LR contours/ranges remain uncalibrated
geometry, not confidence sets. Flag h10 and either beta edge as potentially
truncated; h1 is the physical boundary. Retain shifts >.10 in LR, h or beta,
with a 1e-12 roundoff tolerance, without post-outcome enlargement or penalties.

## Outcomes and precision

Report the following by cell, with all 1,000 blocks retained:

- Primary error contrast: adjusted minus constant mean absolute log-h error,
  `abs(log(hhat/htrue))`. Also report signed log error, RMSE of log error and
  the frequency of at least a 1.5-fold point error (tolerance 1e-12 at the cut).
- Primary predictive contrast: adjusted minus constant conditional-prey held-out
  log score divided by 40 sites. Separately report adjusted versus fitted
  adjusted-null prediction; it addresses the contribution of h within that model.
- Known-beta comparisons and beta error in exact cells; no beta-recovery claim
  for B100-A. Retain boundary, resolution and profile diagnostics in all cells.
- Secondary model-preference rule: select adjusted when its held-out score
  exceeds constant by >1e-12 nats, constant when below by >1e-12, otherwise tie.
  Report all three frequencies. At beta0 this measures preference for unnecessary
  flexibility; the adjusted family still contains the true model. At beta.60 it
  measures preference for the correct background family. These are performance
  rates of this declared predictive rule, not calibrated test size/power or
  proof that a selected h is correct. Neither family is fully correct under G.

Compute analytic paired Monte Carlo SEs and exactly **2,000** bootstrap draws
of complete block indices shared across all six cells, using root2026092703.
Use percentile 2.5/97.5 intervals for simulation-summary uncertainty only.
For oracle summaries use the registered 250-block subset and label that N.
The actual primary contrasts retain N=1,000. Do not count sites as independent
replicates or pool cells to manufacture a general repair finding.

Reporting targets: MCSE<=.02 for the paired absolute-log-error change and
<=.002 nats/holdout-site for the direct predictive contrast. Report achieved
precision; missing a target does not authorize redrawing or reducing N.
Fable's optional 500-block suggestion is not adopted.

## Predictions, not acceptance gates

Retain the proposal's expectations: aligned-null error improves on average;
estimating beta costs precision relative to knowing it; estimation benefit need
not improve direct prediction. The aligned-threefold error direction is open.
Register Fable's sharper forecasts as advisory predictions to be checked:

1. Exact h3: free/known-beta root mean squared log-error ratios near 1.25 at
   beta0 and 1.05 at beta.60. Values above 1.60 and 1.30, respectively, contradict
   the proposed modest-nuisance-cost account. Report ratios and uncertainty;
   the Fisher calculation does not mathematically bound finite-sample RMSE.
2. Exact beta.60/h3: constant mean signed log error >=+.10; adjusted mean
   signed log error differs from known-beta mean by no more than .05 in
   absolute value. Report both scalar comparisons and intervals.
3. At h1 in both exact cells, adjusted hhat>=1.5 is more frequent than under
   known beta. Conditional on adjusted hhat>1, betahat below the truth is more
   frequent than above it; report equality as well, without discarding ties.
   This is a boundary-mechanism prediction, not a claim about false declarations.
4. Exact beta.60 at each h: adjusted-minus-constant prediction averages
   .01–.025 nats/site and favours adjusted in roughly two thirds of histories.
   Report estimates, intervals and distance from those forecasts. “Near” and
   “roughly” do not create retrospectively chosen success bands.

Retain outcomes outside the ranges and unresolved precision. Perfect event-time
information can inform expectations about event scarcity but cannot establish
observed-data information ratios, finite-sample bias or structural identifiability.
Agreement of a few calibrated cutoffs would not establish nuisance-invariant
inference; all calibration proposals remain deferred.

## Qualification and execution

Use deep-server first (idle, approximately123GiB available at initial check).
Begin with 16 beta-row workers and numerical threads1, 48GiB address space.
Cache each exact integration row once, binding it to bank, source, map and
grid; reuse across timing and production. Preserve all old sources. No fresh
approximation, binning or numerical kernel replaces Goal052.

Before production require generator pairing/normalization tests, legacy-cell
reproduction under common streams, known-beta extraction controls, seed
disjointness, exact/small-state likelihood tests and source-bound full-bank
replay against Goal052 saved scores. Timing measures 20 complete paired
blocks with the oracle workload in all four exact cells at 16 beta rows:
−2,−1.75,−1.5,−1.25,−1,−.75,−.5,−.25,0,.25,.5,.6,.75,1,1.5,2.
Bind construction, generation, scoring and serialization times separately;
project complete production conservatively with factor1.5 plus synthesis and
verification reserve. Inspect every control before launching production.

Use persistent phase start/end/exit receipts and exclusive locks; never duplicate
a running or completed phase. Verify source/input/cache/output hashes and
schema before continuation. Retain interrupted work with its original binding;
source changes invalidate qualification and prevent mixing cached results.
Astra can revise resources/timing from measured demand while keeping scientific
design fixed. Preserve and diagnose failures; do not repeat an unchanged failure.

After production verify provenance and complete coverage, run the fixed synthesis
once, inspect figures/tables and obtain independent result review. Report the
benefit/cost/misspecification comparison, failed predictions and limits, update
the handover and Correspondence thread53. A quiet monitor may continue long
compute and should be deleted at verified closeout or a scientific decision gate.
