# Goal 006: Stochastic Landscape-Resistance Contrast Review

## Objective

Introduce and review one second predator-spread process parameter before any
two-parameter fitting is attempted.

The parameter `eta` controls the contrast among the accepted passable-edge
resistances while the global rate remains fixed at `rho = 1`. This goal asks:

> Does resistance contrast produce a stable spatial signature that cannot be
> reduced to a global change in spread speed?

Goal 006 is a process-design and human-review gate. It does not simulate
observations, fit `rho` or `eta`, calibrate uncertainty, or claim joint
identifiability.

## Frozen Source

Pin the accepted repository state:

- commit:
  `edbeb8cc15ea5c95acb74272f0a0122a9cee84f0`;
- Goal 001 landscape:
  `a376df359e09b2357a0b5262479bcebaeee2ff25`;
- Goal 001 spread:
  `ea42352590c8cb3b217ac0b8203a3cb7b3238800`;
- Goal 003 stochastic spread:
  `d20440415ea33cee0f64f41427ae81197ca8fd9e`;
- Goal 003 benchmark:
  `92db1fd224a652bcac591d0959c3ac5d28893670`;
- Goal 003 artifacts:
  `4d6e6ca6ff98aa8d5c23700b111e6e0fda2d46d4`.

Retain unchanged the accepted landscape, water mask, source zones, passable
rook graph, stable edge ordering, habitat conductances, water-neighbour
penalty, multi-source shortest-path algorithm, exponential edge shocks, and
Goal 003 seed children. Prior goal source and artifact contracts remain
frozen.

## Resistance-Contrast Parameter

Let `c_e` be the accepted positive cost of passable edge `e`, and let

```text
g = exp(mean_e(log(c_e)))
```

be the geometric mean across all 10,120 accepted passable edges. Define

```text
c_e(eta) = g * (c_e / g) ** eta
tau_e(eta) = c_e(eta) * E_e / rho
E_e ~ Exponential(1)
rho = 1
```

Use exactly:

```text
eta = 0, 0.5, 1, 1.5, 2
```

Interpret `eta` as **landscape-resistance contrast**, not habitat preference.
The accepted edge cost combines habitat conductance with an additive
water-neighbour penalty. At `eta = 0`, passable-edge resistance is uniform,
but water remains an impassable geometric barrier. At `eta = 1`, the process
must reproduce Goal 003 exactly.

Do not normalize simulated arrival times. Preserving the geometric mean edge
cost does not preserve landscape-scale speed because shortest paths can
change.

## Paired Process Ensemble

Reconstruct exactly the 100 ordered Goal 003
`SeedSequence(20260727)` PCG64 children.

For each replicate:

1. draw one 10,120-element exponential edge-shock vector in frozen edge order;
2. reuse that exact vector at all five `eta` values; and
3. compute the five multi-source first-passage arrival fields.

The edge-field replicate is the independent experimental unit. Cells are
spatial summaries, not independent replicates. Record exactly 100 unique,
ordered, replayable seed records with the complete paired `eta` grid. Do not
spawn eta-specific process streams.

## Removing Global-Time Confounding

For replicate `r`, contrast value `eta`, and every non-source passable cell
`i`, define the diagnostic scale factor

```text
s_eta,r = exp(median_i(log(T_1,r,i) - log(T_eta,r,i)))
```

and aligned log residual

```text
R_eta,r,i = log(s_eta,r * T_eta,r,i / T_1,r,i).
```

This alignment is diagnostic only. It must never alter the generator or raw
arrival outputs.

At occupancy fraction `q` in `0.25, 0.5, 0.75`, define the front as the first
`ceil(q * 5225)` passable cells ordered by arrival time and then row-major cell
index. Report Jaccard distance from the paired `eta = 1` front.

## Required Summaries

For every replicate and `eta`, report:

- raw `t25`, `t50`, `t75`, `t90`, and maximum arrival;
- the diagnostic alignment scale;
- median and 90th percentile absolute aligned log residual;
- matched-front Jaccard distances at 25%, 50%, and 75% occupancy;
- arrival-rank correlation and the fraction of cells displaced by at least
  10% of the passable-cell rank range;
- source-zone reassignment fraction relative to `eta = 1`; and
- source-zone contribution fractions.

Across replicates, report aligned residuals by habitat class and these
prespecified contrasts:

- corridor minus low-quality matrix;
- high-quality patch minus low-quality matrix; and
- water-adjacent low-quality matrix minus non-water-adjacent low-quality
  matrix.

Define the decision operands within each edge-field replicate:

```text
A_eta,r = median_i(abs(R_eta,r,i))
J_eta,r = 50%-front Jaccard distance from paired eta = 1
H_eta,r = median_corridor(R_eta,r,i)
          - median_low_quality_matrix(R_eta,r,i)
```

Decision thresholds use the median of these replicate-level values across the
100 edge fields. Also report their 5th and 95th percentiles. Do not pool cells
across replicates for decision-making.

Mechanically select one detailed representative edge field: the Goal 003
median-`t50` realization, replicate index `29`. No visual selection is
permitted.

## Frozen Goal 003 Reconciliation

At `eta = 1`, require exact process replay and reconciliation with these
published Goal 003 constants:

- 100 replicates;
- median of per-cell stochastic median arrival:
  `31.69888227914729`;
- correlation of deterministic arrival with stochastic ensemble median:
  `0.9937734843350453`;
- temporal-scale ratio:
  `0.4626972981816758`;
- standard deviation of replicate `t50`:
  `1.6196762763006858`; and
- representative median-`t50` replicate:
  index `29`, time `31.29398268570847`.

Comparison must use frozen numerical constants rather than ignored Goal 003
artifacts or a second call through the same Goal 006 implementation.

## Decision Classes

Apply the first matching class:

1. `implementation_blocked`: any frozen-source, graph, seed, replay,
   eta-one reconciliation, generation, numerical, artifact, or reproducibility
   invariant fails.
2. `resistance_contrast_pathological`: any eta has non-finite or invalid
   arrivals, a median `t50` outside `[0.25, 4]` times the eta-one median, or a
   transformed maximum-to-minimum edge-cost ratio above 100.
3. `resistance_contrast_effectively_global_rate_only`: neither adjacent
   contrast (`eta = 0.5` or `1.5`) has both a median absolute aligned log
   residual of at least `0.05` and a median 50%-front Jaccard distance of at
   least `0.05`.
4. `resistance_contrast_spatial_signal_asymmetric`: at least one adjacent
   contrast passes both median spatial thresholds, but the other does not; the
   corridor-minus-matrix residual lacks the expected positive sign at
   `eta = 0.5` or negative sign at `eta = 1.5`; or any adjacent contrast fails
   the replicate-consistency requirement below.
5. `advance_to_joint_rho_eta_recovery`: both adjacent contrasts pass both
   median spatial thresholds, the directional corridor contrast is coherent,
   at least 80 of 100 replicates at each adjacent contrast simultaneously have
   `A_eta,r >= 0.05` and `J_eta,r >= 0.05`, at least 80 of 100 have the
   expected sign of `H_eta,r`, and all process and reproducibility gates pass.

Complete and report all five eta values even when a scientifically negative
class is reached. The extreme values `0` and `2` are diagnostic stress points;
advancement is determined by the adjacent values `0.5` and `1.5`.

## Review Pack

Write exactly 15 ignored files under:

```text
artifacts/goal006_stochastic_resistance_contrast/
```

Required files:

- `process_config.json`
- `seed_manifest.csv`
- `edge_cost_summary.csv`
- `replicate_summary.csv`
- `spatial_effect_summary.csv`
- `cell_summary.csv`
- `representative_realizations.csv`
- `summary.json`
- `verification.json`
- `review.md`
- `visuals/edge_cost_transformation.svg`
- `visuals/aligned_residual_maps.svg`
- `visuals/matched_occupancy_fronts.svg`
- `visuals/habitat_contrast_curves.svg`
- `visuals/source_reassignment.svg`

The pack must distinguish raw process observations, diagnostic alignment,
scientific inference, assumptions, and limitations. Do not retain all 500 raw
arrival grids.

## Verification Gates

Require:

- the pinned source commit and runtime blobs;
- 5,225 passable cells, 823 water cells, 81 source cells, and 10,120 edges;
- finite positive accepted and transformed edge costs;
- exact `eta = 1` baseline edge costs and Goal 003 reconciliation;
- exactly 100 unique, ordered, replayable paired edge-shock streams;
- source cells at zero, water at infinity, and all passable cells reachable;
- no eta-specific seed generation;
- complete five-eta results for every replicate;
- diagnostic alignment applied only in summaries;
- exact table, JSON, and visual reconciliation;
- byte-identical canonical and repeat bundles; and
- ignored, unstaged generated/build outputs.

## Stop Rules

Report without tuning if the resistance-contrast signal is weak, asymmetric,
strongly confounded with global speed, or pathological. Do not change the eta
grid, landscape, edge-cost formulation, shocks, replicate count, thresholds,
or representative selection after inspecting results.

Stop early only for invalid source provenance, replay failure, non-finite
computation, unsuitable local runtime, or one focused repair that fails to
resolve a material implementation defect.

Do not add observations, fitting, likelihoods, calibration, a free process
noise parameter, prey dynamics, alternative landscapes, real data, remote
compute, or Goal 007.

## Authority

Implementation and local validation on
`codex/latent-landscapes-goal006-resistance-contrast-review` are authorized.
Generated artifacts and build outputs must remain ignored and unstaged.

After orchestrator review and one independent final review, publication of an
accepted completed result is authorized if all gates pass. Stage exact
accepted source, test, script, and documentation paths only.
