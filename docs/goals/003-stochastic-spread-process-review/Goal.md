# Goal 003: Stochastic Predator-Spread Process Review

## Objective

Build and review one frozen stochastic predator-spread generating process on
the accepted Latent Landscapes synth-medium landscape before attempting any
inference under process uncertainty.

This goal answers a deliberately narrower question than parameter recovery:

> Does a conductance-weighted continuous-time spread process produce
> reproducible, spatially coherent, non-degenerate arrival patterns that are
> suitable for a later one-parameter inference benchmark?

Goal 003 is a generating-process and human-review gate. It does not fit
`rho`, simulate imperfect observations, or claim identifiability.

## Scientific Context

Goal 001 showed that the deterministic one-rate process is practically
identifiable in one fixed imperfect-observation realization. Goal 002 showed
that observation-only uncertainty can be calibrated at `rho = 1`, and that
the habitat-aware model has a finite predictive advantage over a full-support
time-stratified neutral baseline.

The next rung introduces process stochasticity while keeping the future focal
parameter set to `rho` alone. Additional spread parameters, prey dynamics, and
indirect inference remain out of scope.

## Frozen Process Definition

Use the accepted Goal 001 landscape, water mask, source zones, rook graph,
habitat conductances, water-neighbour penalty, and deterministic edge cost
`c_e`.

For every undirected passable edge, in stable row-major graph order, draw one
independent transit time

```text
tau_e ~ Exponential(rate = rho / c_e)
```

so that

```text
E[tau_e] = c_e / rho.
```

All 81 source-zone cells are colonized at `t = 0`. Stochastic arrival times
and source provenance are the multi-source shortest paths through the sampled
edge transit times. The canonical truth is `rho = 1`.

This is weighted stochastic first-passage percolation, equivalently a
continuous-time SI spread process with conductance-weighted edge hazards. The
same seed coupled at two rates must preserve path choices and scale every
finite arrival time exactly as `1 / rho`.

## Temporal-Scale Interpretation

The stochastic process preserves the Goal 001 **local mean edge time**, not
the Goal 001 deterministic whole-landscape arrival surface. Competition among
alternative stochastic paths makes the minimum realized path faster than the
minimum path of expected edge times in general.

Do not silently normalize the process, tune a multiplier to recover the old
survey horizon, change `rho`, or replace the exponential law after inspecting
the ensemble. A material global time-scale shift is a valid Goal 003 result
and must trigger human review before Goal 004.

## Canonical Ensemble

- Master seed: `20260727`, distinct from the Goal 002 observation-calibration
  root.
- Child construction: one `numpy.random.SeedSequence` spawning exactly 100
  ordered process children.
- Generator: `numpy.random.Generator(numpy.random.PCG64(child))`.
- Replicates: exactly 100; no filtering, extension, replacement, or
  command-line override.
- Canonical rate: `rho = 1`.
- Review times: `10, 20, 30, 40, 50, 60`.
- Goal 001 reference times retained as diagnostics: `70, 90, 110`.

The review times describe latent-process progression only. They do not adopt a
future observation schedule.

## Required Scientific Summaries

Record, without retaining the 100 raw arrival grids:

- per-replicate occupancy fractions at every review and reference time;
- times to 25%, 50%, 75%, and 90% passable-cell colonization;
- maximum arrival time and source-zone contributions;
- per-cell stochastic arrival quantiles and deterministic Goal 001 arrival;
- habitat-class arrival summaries;
- ensemble variation in spread trajectories;
- association between deterministic arrival and the stochastic ensemble
  median, clearly labelled as a geometry/landscape-signal diagnostic; and
- the ratio between stochastic ensemble-median and deterministic arrival
  quantiles, clearly labelled as a temporal-scale diagnostic.

Select representative realizations mechanically from the ordered 10%, 25%,
50%, 75%, and 90% ranks of time to 50% colonization, breaking ties by
replicate index. Do not choose visually attractive realizations.

## Required Review Pack

Write exactly these 13 ignored files under
`artifacts/goal003_stochastic_spread_process/`:

```text
process_config.json
seed_manifest.csv
replicate_summary.csv
cell_arrival_quantiles.csv
habitat_arrival_summary.csv
representative_realizations.csv
summary.json
verification.json
review.md
visuals/arrival_quantile_maps.svg
visuals/representative_realizations.svg
visuals/spread_trajectories.svg
visuals/temporal_scale_diagnostic.svg
```

The figures must distinguish observed ensemble summaries from interpretation,
use stable representative-selection labels, and remain readable without
opening machine-readable tables.

## Verification Gates

All implementation gates must pass:

- Goal 001 deterministic landscape and spread regressions remain unchanged.
- The graph has 5,225 passable cells, 823 water cells, 81 source cells, and
  10,120 undirected passable rook edges.
- Every replicate has finite non-negative arrival for every passable cell,
  infinite arrival for water, zero arrival for all source cells, and valid
  source provenance.
- All 100 child seeds are unique, phase-labelled, ordered, and replayable.
- Selected replicate replay matches its stored compact summaries.
- A same-seed `rho = 2` check gives finite arrival times exactly half of the
  `rho = 1` values within numerical tolerance.
- Stochastic variation is non-zero and the stochastic ensemble-median arrival
  retains a positive, material association with deterministic arrival.
- Tables, JSON summaries, and visual labels reconcile.
- Two clean bundle writes are byte-identical.
- Generated outputs remain ignored and unstaged.

## Decision Classes

`approve_stochastic_process_for_inference`
: The process and provenance gates pass, stochastic variation is informative,
  landscape structure remains visible, and no material temporal-scale issue
  requires a prior human decision.

`time_scale_review_required`
: The stochastic process is coherent and reproducible, but path competition
  materially changes landscape-scale timing or saturates the old Goal 001
  horizon. This is a completed scientific result, not an implementation
  failure. Do not normalize or redesign observations automatically.

`reject_process_formulation`
: Structural invariants fail, spatial landscape signal is effectively erased,
  or stochastic variation is degenerate or pathological.

`implementation_blocked`
: The required simulator, deterministic bundle, or verification contract
  cannot be completed reliably.

The decision is a bounded process-review judgement, not a hypothesis test or
inferential calibration claim.

## Stop Rules

Stop and report rather than repair by tuning if:

- the old observation horizon is saturated;
- the stochastic global time scale differs materially from Goal 001;
- a different distribution, normalization, or process parameter appears
  desirable;
- landscape structure is overwhelmed by stochasticity; or
- a second focused implementation attempt produces no material improvement.

Do not add observations, likelihoods, fitted parameters, neutral-model
comparisons, calibration ensembles, prey, false positives, survey redesign,
Gamma edge times, a free noise parameter, real data, remote compute, or Goal
004.

## Authority

Implementation and local validation on
`codex/latent-landscapes-goal003-stochastic-process-review` are authorized.
Generated artifacts and build outputs must remain ignored and unstaged.

Do not commit, merge, push, or publish until the orchestrator has reviewed and
accepted the complete pack. Publication is authorized after acceptance if all
implementation gates pass. A scientifically negative decision class may still
be accepted and published.
