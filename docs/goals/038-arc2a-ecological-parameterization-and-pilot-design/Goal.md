# Goal 038: Arc 2A Ecological Parameterization And Pilot Design

## Programme role

This goal is the human design gate between the accepted Arc 1 reference
laboratory and Roadmap Arc 2A production. It advances Charter Pillar 2 without
running a new inference ensemble.

## Scientific question

Can the provisional predator-only Arc 2A experiment be expressed in ecological
terms, cover its three-dimensional factor space efficiently, and fit a
proportionate compute and Monte Carlo budget before production is authorized?

## Required outcomes

1. Translate resistance exponent `eta` into expected per-edge movement-cost
   contrasts for dry corridor, high-quality patch, medium habitat, dry matrix,
   and water-adjacent matrix movement on the frozen reference landscape.
2. Show the spatial consequences of representative `eta` values using a local
   incident-edge cost map, without simulating a spread history.
3. Generate the exact reproducible 16-point scrambled Sobol pilot over
   `log2(rho) = [-1, 1]`, `eta = [0.25, 2]`, and `p = [0.35, 0.85]`.
4. Keep the central `eta = 0` no-resistance diagnostic separate from that
   continuous design and identify the accepted Arc 1 reference points that
   should be overlaid rather than rerun.
5. Quantify simulation-history counts, exploratory Monte Carlo precision, and
   a transparent wall-time planning proxy from accepted Arc 1 timings.
6. Produce a compact table, visual, and plain-language review surface that
   Barry can approve or modify before Arc 2A production.

## Frozen inputs

- Goal 037 commit `0047b2830703a14922f155a350df492c788b8280`;
- the accepted 72 by 84 landscape and 10,120 passable rook edges;
- the baseline edge-cost equation and geometric-mean-preserving transform
  `c_eta = g * (c / g) ** eta`;
- the accepted Arc 1 reference points in Goals 005, 022, 023, 024, and 025;
- 250 calibration and 250 independent validation histories per new truth;
- scramble seed `20260829`; and
- the staged 16 to 32 Sobol structure proposed in Goal 037.

## Review bundle

Write exactly nine ignored files under
`artifacts/goal038_arc2a_design_freeze/`:

- `eta_ecological_translation.csv`;
- `arc2a_pilot_truths.csv`;
- `arc1_reference_points.csv`;
- `compute_budget.csv`;
- `summary.json`;
- `review.md`;
- `eta_cost_contrasts.svg`;
- `eta_cost_maps.svg`; and
- `arc2a_pilot_design.svg`.

The figures must explain their units directly. The review must distinguish
measured Arc 1 timing anchors from workload-scaled planning estimates.

## Decisions reserved for Barry

- whether matrix-to-corridor contrasts at the proposed upper `eta` bound remain
  ecologically credible;
- whether `rho = 0.5-2` and `p = 0.35-0.85` remain the appropriate first-map
  domains;
- whether the fixed sampling and survey design should remain fixed in Arc 2A;
- whether 16 Sobol points plus the no-resistance diagnostic are sufficient for
  the first production review; and
- whether the resulting runtime warrants immediate `deep-server` execution.

## Boundaries

No predator spread simulation, observation generation, likelihood fitting,
calibration, validation ensemble, response-surface fit, remote compute, prey
model, landscape change, observation redesign, commit, or push is authorized.
Do not alter the accepted Arc 1 inference machinery. Adding SciPy as an
explicit dependency is authorized because the project already receives it
transitively through scikit-learn and its public `scipy.stats.qmc.Sobol`
implementation avoids a bespoke design generator.

## Success and stop rules

The goal succeeds when the deterministic tables reconcile the accepted edge
transform, the 16 Sobol points are unique and space-filling within the proposed
domains, the figures are readable, the workload and Monte Carlo limitations
are explicit, and no production workflow runs. Perform one focused review and
at most one material repair. Stop at Barry's design review; local contour or
layout polish is not a reason to continue.

Barry approved proceeding on 29 August 2026.

## Observed outcome

The deterministic pack returned `ready_for_human_arc2a_design_review`. The
geometric-mean-preserving transform was reconciled across all eight review
values. Dry-matrix movement ranges from 1.36 times dry-corridor cost at
`eta = 0.25` to 3.39 times at the reference `eta = 1` and 11.52 times at
`eta = 2`. The corresponding whole-edge maximum/minimum ratio at `eta = 2` is
23.35. Water adjacency adds a smaller median contrast: 1.04 times dry matrix at
`eta = 1` and 1.09 times at `eta = 2`.

The exact scramble seed produced 16 unique continuous truths. Every factor
occupies each of its 16 one-dimensional strata once. Realized points range from
`rho = 0.512-1.894`, `eta = 0.317-1.924`, and `p = 0.365-0.835`; the bounds are
domains rather than forced endpoint cells. A central `(rho, eta, p) =
(1, 0, 0.65)` diagnostic is the seventeenth new condition. Six accepted Arc 1
anchors are shown as overlays and are not scheduled for full reruns.

The initial workload is 8,500 condition histories. History-count scaling from
Goal 023 gives a 116-minute Mac proxy and a 145-minute planning upper value.
These are deliberately labelled estimates rather than runner benchmarks. With
250 validation histories, 238/250 nominal coverage has a Wilson interval of
approximately 0.918-0.972, adequate for an exploratory response surface but
not necessarily for final inference at selected transition conditions.

The provisional recommendation is to retain `eta = 2` as a strong stress bound
while treating `eta = 0.25-1.5` as the more ecologically central range. Barry
may cap the domain at 1.5 before production if the 23-fold whole-edge contrast
is not useful.

## Validation

- three focused Goal 038 tests passed for the ecological translation, exact
  Sobol design, compute accounting, and nine-file review surface;
- 11 inherited landscape, resistance-transform, and Goal 023 tests passed;
- the full suite passed: 263 tests, with three inherited Goal 006 Matplotlib
  pending-deprecation warnings;
- Ruff formatting and lint passed;
- strict MyPy passed over 123 source files;
- the source distribution and wheel build passed;
- the CLI wrote exactly nine ignored review files; and
- the CSV tables, plain-language memo, and all three rendered SVGs were
  inspected once.

The focused visual repair added accepted Arc 1 anchors to the design figure and
recorded the two-visit interpretation of `p`. It changed no factor domain,
truth point, cost calculation, workload estimate, or accepted result. No
production simulation, remote job, commit, or push was started.
