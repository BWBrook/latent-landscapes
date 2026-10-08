# Goal 051: first prospective misspecification screen

23 September 2026. Barry approved the revised 17-cell package in Codex with
“Approved!” This registration implements the scientific choices in the
[reviewed proposal](../050-model-adequacy/next-screen-proposal.md), following
Fable's thread 53 critique and Astra's replies 475–476. It advances Paper 1
Charter Pillar 4 and Roadmap Arc 4. It is a robustness screen, not a fitted-model
discrimination experiment or completion of Pillar 4.

The approved reporting horizon is implementation, independent qualification,
source-bound timing, the complete screen if it fits the budget, and a verified
scientific synthesis. Negative results and failed predictions are valid
outcomes. No further permission is needed within this envelope. Independent
confirmation, alternative-model fitting, new calibration, bank enlargement,
additional landscapes, commits, pushes and publication are outside it.

## Fixed analysis and complete-history design

Retain the accepted reference landscape, predator source, conductance surface,
160 sampled sites and fixed 120 training / 40 holdout split. Survey at days
10,20,30,40,50,60, with two visits per occasion and no false positives. Spread
speed rho=1, resistance contrast eta=1, nominal background prey-loss hazard
0.002/day and fitted predator/prey detection probability 0.65 remain supplied.
The effect grid is exactly 181 nodes, 1,1.05,...,10. Use the independent frozen
K131072 integration bank with alpha=1 and the unchanged likelihood.

There are exactly 1,000 independent complete-history replicate blocks, paired
across these 17 cells in the order below. A complete history, including its
spatial field and all sites, is the independent unit.

| Order | Cell ID | Physical h | Departure |
| ---: | --- | ---: | --- |
| 0 | B_h1 | 1 | assumed-model baseline |
| 1 | B_h3 | 3 | assumed-model baseline |
| 2 | B_h5 | 5 | assumed-model baseline |
| 3 | D10_h1 | 1 | prey-only detection SD 0.10 |
| 4 | D10_h3 | 3 | prey-only detection SD 0.10 |
| 5 | D10_h5 | 5 | prey-only detection SD 0.10 |
| 6 | D20_h1 | 1 | prey-only detection SD 0.20 |
| 7 | D20_h3 | 3 | prey-only detection SD 0.20 |
| 8 | D20_h5 | 5 | prey-only detection SD 0.20 |
| 9 | PD10_h1 | 1 | predator-only detection SD 0.10 |
| 10 | PD10_h3 | 3 | predator-only detection SD 0.10 |
| 11 | PD10_h5 | 5 | predator-only detection SD 0.10 |
| 12 | B50-I_h1 | 1 | background nominal CV 0.5, mixing r=0 |
| 13 | B100-I_h1 | 1 | background nominal CV 1, mixing r=0 |
| 14 | B50-A_h1 | 1 | background nominal CV 0.5, mixing r=0.7 |
| 15 | B100-A_h1 | 1 | background nominal CV 1, mixing r=0.7 |
| 16 | B100-A_h3 | 3 | background nominal CV 1, mixing r=0.7 |

The physical multiplier is h even when the constant-background fitted model's
projection differs. No general identification claim is made under departure.

## Generator details fixed before evidence

Detection fields are iid among sampled sites, fixed over all visits, with
mean 0.65. D10 and PD10 use Beta(14.1375,7.6125); D20 uses
Beta(3.046875,1.640625). Prey and predator field streams are separate. D10 and
D20 transform common site uniforms through their respective Beta quantiles.
The other species has detection 0.65. Detection fields are shared across h.

All cells in a replicate share one spread realization, prey event-time
uniforms and visit-level predator/prey detection uniforms. Only the relevant
field, threshold or effect changes. Given background lambda_i and arrival a_i,
loss occurs when cumulative hazard
`lambda_i * (min(t,a_i) + h * max(0,t-a_i))` first exceeds the same unit-rate
exponential variate. Infinity denotes no arrival. This retains absorbing prey
loss and makes the constant-background case the existing generator's law.
For bitwise replay, B/D/PD cells retain the original risk-to-hazard conversion
`-log1p(-(1-exp(-0.002*60)))/60`, represented as 0.0020000000000000005.
Nonzero background fields retain literal 0.002 as their whole-map mean target.
This floating-point distinction does not change the declared daily hazard.

The background field covers every cell of the accepted 72 by 84 landscape.
Compute shortest-path resistance distance from all frozen source-zone cells on
the existing passable rook graph, using the unchanged edge cost
`0.88/mean_endpoint_conductance + 0.46*(water_neighbors_i+water_neighbors_j)/4`
at eta=1. Apply average ranks to negative distances across all 6048 cells;
unreachable/water cells have infinite distance and share the lowest exposure
rank. Transform `(rank-0.5)/6048` by the standard-normal quantile, then center
and divide by the population SD (ddof=0), obtaining A.
Larger A means greater deterministic invasion exposure. Neither realised
arrival nor the integration bank defines A.

Draw G with mean-zero, unit-variance Gaussian marginals and covariance
`exp(-Euclidean_grid_distance/10)`. Use exact circulant embedding of size
142 by 166: toroidal lags, the exponential covariance row, its real FFT
eigenvalues and a Gaussian white-noise FFT filter. The cropped 72 by 84 field
has the specified finite-grid covariance. Require strictly positive embedding
eigenvalues and covariance reconstruction error at most 1e-12. No eigenvalue
clipping, covariance approximation or changed correlation length is allowed.
Do not center or standardize each realised G field.

For each replicate and each registered background pair (CV,r), set
`sigma=sqrt(log(1+CV^2))`, `Z=r*A+sqrt(1-r^2)*G` and
`lambda=0.002*exp(sigma*Z)/mean_all_cells(exp(sigma*Z))`.
The same G is used for all background variants; B100-A shares its lambda map
at h=1 and h=3. Mean hazard over the entire landscape is 0.002/day to numerical
precision. Sampled-site means are not recentered. Nominal CV and r do not
specify realised CV/correlation; common mean rescaling leaves both unchanged.
Before arrival the hazard is lambda_i and after arrival it is h*lambda_i.

Record whole-map, sampled, training and holdout hazard means and CVs,
correlations with A, and sampled/train/holdout correlations with realised
exposure `max(0,60-arrival)` (zero for no arrival by 60). Separately record
arrival correlation among sites arriving by 60, their count, and explicit
undefined correlations for zero variance. Detection-field means/SDs are
diagnostics too. These diagnostics stay outside the analyst observation
boundary and never determine redraws, fit inputs or tuning.

## Random streams, timing and controls

Freeze roots: production 2026092301; timing 2026092302; small implementation
fixtures 2026092303; paired synthesis 2026092304. Within each generator root,
spawn seven independent streams for spread, prey event thresholds, predator
visit uniforms, prey visit uniforms, prey site field, predator site field and
Gaussian background field. NumPy SeedSequence child states supply uint64
seeds; the exact spawning order is recorded in the source and seed manifest.
Require full production/timing/fixture stream identities to be unique and
disjoint from the bank and Goals 049/050 streams, not just disjoint root labels.
Opaque observation identifiers do not encode the cell or physical truth.

Timing uses 16 complete paired blocks, all 17 cells, the full bank and full
181-node fit, from the separate timing root. It measures the entire pathway,
including field construction, generation, scoring, serialization, input/output
hashing and validation. Timing outcomes are not used in scientific summaries
or threshold/design decisions. Production uses its full 1,000 fresh blocks.

Before timing, verify baseline equivalence with the original generator using
matched primitive randomness, zero-SD/zero-CV controls, exact hazard inversion,
paired field/visit streams, whole-map scaling, the Gaussian covariance, source
distance direction, finite scores, first-node ties, and the analyst boundary.
Independent implementation review must inspect scientific controls and the
frozen estimator/endpoint code. Original Goal 049/050 source, table and input
identities remain unchanged. Preserve all four earlier Arc 3 numerical failures.

## Frozen detector, estimation and uncertainty

The Goal 049 rank950 candidate cutoffs define the effect set. Original Goal
050 rank990 cutoffs define C99. Reference score row g contains the 999 already
refitted original calibration histories at candidate g. No reference row or
cutoff is regenerated. The training maximum uses the lowest-index tie rule;
S is held-out joint log score minus held-out predator log score at that fit.

`p_g=(1+count[S*_g<=S])/1000`, using inclusive ties.
`p_BB=min(1,max(g in C99)p_g+0.01)`; primary D is `p_BB<=0.05`.
C99 must be nonempty and include the fitted node. Secondary `p_plugin` uses
the reference row at the fitted node and also rejects at 0.05. Its selected
reference row has no fixed-node finite-sample guarantee. Report its own fresh
baseline rates. Every primary rejection must also be a secondary rejection;
extra secondary flags alone are not better calibrated discrimination. No
either-test omnibus or revised threshold is used.

Define M as truth exclusion from the effect set OR
`abs(log(h_hat/h))>=log(1.5)`. Primary hidden failure H is `M AND NOT D_BB`;
secondary H_plugin uses the plug-in detector. Report each M component, M,
M AND D, both detector rates and both H rates. At physical h=1 also report
strict false effect `[1 excluded] AND [h_hat>=1.5]` and its unflagged forms.
Report mean signed log bias, its paired change, absolute log error, fitted h,
truth inclusion, effect-set width/cardinality/components/boundary contact,
C99 truth inclusion and S. Set width is a calibration-dependent diagnostic,
not a monotone measure of information. The primary width summary and P3 use
log span `log(max_set_h/min_set_h)`, consistent with earlier recovery endpoints;
also retain the raw h span `max_set_h-min_set_h`. Gaps are described by the
separate component count, not filled and called connected. A singleton has
zero span.

Use exactly 1,000 paired bootstrap draws with root 2026092304, resampling whole
replicate indices jointly across all 17 cells. Pair each departure with the
baseline at the same physical h. Keep reference tables fixed. Use empirical
2.5% and 97.5% percentile intervals (NumPy linear quantiles); individual event
rates also receive conditional Wilson 95% intervals. Do not resample sites or
calibration histories, refine draws after seeing intervals or claim simultaneous
coverage. Preserve baseline M/H and components; baseline bias need not be zero
at the lower h boundary.

## Predictions and screen decision

Fable's four predictions are retained with attribution, component by component:

- P1: at every h, D10 has abs(delta mean signed log bias)<0.05 and delta H<0.02.
  For D20 at h=3,5, 0.85<exp(delta bias)<1; D20 truth-exclusion increase<0.03
  at every h.
- P2: B100-A at h=1 has strict false effects>0.20, primary rejection<0.10 and
  primary delta H>0.10. These are three separate claims.
- P3: each r=0 background null has a strict-false-effect contrast interval
  containing zero, and larger mean effect-set width than baseline. The first
  is a forecast of non-resolution, not equivalence.
- P4: at h=3,5, PD10 has greater absolute mean signed log bias than D20;
  its truth-exclusion increase is at least 0.03 at one of the three truths.

For scalar inequalities, show the point predicate and interval: wholly in the
predicted range supports, wholly outside contradicts, boundary overlap is
unresolved. For P3's explicit interval forecast report met/unmet without an
equivalence claim. For P4 bootstrap the difference in absolute mean biases,
not mean absolute error. Predictions are not execution or acceptance gates.

Across all departure cells together, select at most one cell whose primary
delta H is at least 0.05 and paired 95% interval lies entirely above zero.
Choose the largest delta H; exact ties use the frozen cell order. Its mechanism
class (prey detection, predator detection or background hazard) is the sole
nomination. A point increase >=0.05 whose interval contains zero is unresolved.
An estimate below 0.05 does not establish equivalence. Classify M descriptively
using the same rule and show caught failures, but do not nominate on M.

Subsequent independent confirmation would require 1,000 new paired histories
and the same delta H threshold and positive interval; that is a separate
decision, as are Stage 2 fitted alternatives and the neutral comparator.

## Four-hour execution and completion boundary

Use deep-server-ts, remote root
`/data/codex/scratch/goal051-misspecification-screen-20260923`, with eight scoring
workers, numerical threads one and 32 GiB aggregate process address space.
The hard cap is 14,400 elapsed computation seconds. Charge 1,200 seconds for
preparation/controls (or actual compute if greater), measured timing, measured
production and at least 1,800 seconds reserved for synthesis/verification.
Do not charge human waiting or idle scheduling delays as computation, but count
failed compute attempts and all actual phase computation.

Before production, project the complete 1,000-block workload from all-cell
timing, with at least 1.5 on generation/scoring and measured setup/hash/output
costs. Add preparation, actual timing and synthesis reserve. Bind the passing
projection to the final source, registration, input identities, wrappers and
actual remaining timeout in a production-budget receipt. Source changes
invalidate timing qualification. Preserve timeouts with explicit exit/start/end
receipts and a run lock; never duplicate an active or completed phase.

If full workload does not fit, controls fail or the cap is reached, preserve
evidence and report the registered stopping outcome. Do not drop cells,
reduce replication, enlarge resources, change severities or repeat an unchanged
failure. A diagnosed technical repair may proceed before new decisive evidence
only inside the remaining cap; it invalidates earlier source timing and must
be documented. No partial campaign is relabelled the registered screen.

Completion requires verified frozen score/output identities, a fixed-bootstrap
synthesis, inspected tables and standalone figure, independent result review,
an updated handover and substantive Correspondence thread 53 findings as Astra.
Retain failed predictions and the finite-grid, fixed-table/bank, known-nuisance,
single-landscape scope. The next independent confirmation or competing-model
choice returns to Barry. Until completion or a material stopping decision,
Astra owns the next action; another Fable or Barry reply is not required.
