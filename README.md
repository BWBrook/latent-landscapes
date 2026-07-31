# Latent Landscapes

Latent Landscapes is a research programme on identifiability, recoverability,
and uncertainty calibration in spatially explicit predator-prey inference.

The definitive North Star is:

> Under what landscape, process, and observation conditions are the parameters
> of spatially explicit predator-prey dynamics identifiable and recoverable
> from imperfect data, and how well is inferential uncertainty calibrated when
> the generating system is known?

Paper 1 is synthetic-only. A real mink-vole application is reserved for a
later, separate programme or paper.

The repository is private initially. The Python package namespace is
`latent_landscapes`.

Goal 001's machine-readable `neutral` model is a geometry-only hard-front
comparator: a deterministic nearest-source radial wave with known zero false
positives. Its held-out `-Infinity` log score, when it occurs, is a structural
support violation rather than an optimizer failure or a calibrated measure of
superiority. The finite Brier score is retained as corroborating descriptive
evidence.

Goal 001 implements one canonical deterministic predator-spread
identifiability benchmark. From the repository root:

```bash
uv sync --all-groups
uv run python scripts/run_goal001.py
```

The ignored nine-file human review pack is written to
`artifacts/goal001_deterministic_spread/`. Use `--output-dir PATH` to write the
same bundle elsewhere. Scientifically negative outcome classes still exit
successfully. An `implementation_blocked` outcome writes no review bundle,
emits a concise blocker on stderr, and exits nonzero.

Goal 002 freezes the Goal 001 landscape, deterministic `rho = 1` truth, sampling
design, detection probability, and holdout split. It varies only the imperfect
detection realization across 500 calibration and 500 validation children:

```bash
uv run python scripts/run_goal002.py
```

The ignored ten-file review pack is written to
`artifacts/goal002_detection_calibration/`. It contains compact replicate
summaries, a replayable seed manifest, calibration and predictive summaries,
verification metadata, a scientific review, and three summary figures. Raw
ensemble observations and likelihood profiles are not retained.

Goal 002 calibrates likelihood-ratio support at the exact generating rate and
compares the habitat model's worst training-MLE-partition holdout Brier score
with a training-only, time-stratified Jeffreys-smoothed neutral baseline. The
geometry-only hard-front comparator remains a diagnostic. As in Goal 001,
scientifically negative outcomes exit successfully; only
`implementation_blocked` suppresses the bundle and exits nonzero. Use
`--output-dir PATH` to write the same deterministic bundle elsewhere.

Programme scope and method sequence are in `docs/programme.md`. Legacy-source
handling is governed by `docs/provenance.md` and
`docs/decisions/0001-rebuild-from-spatext.md`.

Goal 003's frozen stochastic review is run with:

```bash
uv run python scripts/run_goal003.py
```

The ignored 13-file review pack is written to
`artifacts/goal003_stochastic_spread_process/`. It uses exactly 100 ordered
`SeedSequence(20260727)` PCG64 children, exponential edge times with
`rate = rho / c_e` at `rho = 1`, and no normalization or tuning. The pack
retains compact summaries and mechanically selected t50-rank realizations,
never raw ensemble grids. A completed `time_scale_review_required` outcome is
scientifically valid when stochastic path competition shifts global timing
relative to Goal 001.

Goal 004 combines the accepted stochastic spread process with imperfect
detection and evaluates one-rate recovery on the prospectively frozen
`10, 20, 30, 40, 50, 60` survey calendar:

```bash
uv run python scripts/run_goal004.py
```

The ignored 12-file review pack is written to
`artifacts/goal004_stochastic_one_rate_recovery/`. It calibrates a
seven-category, Jeffreys-smoothed site-history simulated composite likelihood
at `rho = 1`, checks the full 4,096-draw integration bank against two disjoint
2,048-draw halves, and compares training-only fitted stochastic predictions
with the full-support time-stratified neutral. The method preserves dependence
within each site's repeated history but is not a full joint spatial likelihood.
Use `--output-dir PATH` only to redirect the deterministic bundle. Scientifically
negative classes remain successful completed runs; only
`implementation_blocked` suppresses the bundle and exits nonzero.

## Goal 005

Goal 005 extends the one-rate benchmark to prespecified generating rates
`rho = 0.5, 1, 2` without changing the landscape, calendar, detection model,
rate grid, likelihood, or neutral comparator. Each truth receives its own
locally calibrated cutoff; the frozen `rho = 1` cutoff is transported to the
flanks only as a separate diagnostic. The ignored 15-file review bundle is
written to `artifacts/goal005_stochastic_one_rate_cross_rate/`. The completed
result is `one_rate_recovery_robust_cutoff_nontransportable`: local recovery
favours the stochastic process at all three truths, but the `rho = 1` cutoff
is too conservative at both flanks. The result remains conditional on one
landscape and a composite likelihood that omits between-site process
dependence.

## Goal 006

Goal 006 tests whether geometric-mean-preserving landscape-resistance contrast
produces a spatial signal beyond a global change in spread speed. It evaluates
`eta = 0, 0.5, 1, 1.5, 2` at fixed `rho = 1`, reusing one exponential edge
shock vector across all eta values within each of 100 edge-field replicates:

```bash
uv run python scripts/run_goal006.py
```

The ignored 15-file review pack is written to
`artifacts/goal006_stochastic_resistance_contrast/`. Raw arrivals are retained
only long enough to form compact replicate, habitat, source, and representative
summaries. Alignment removes global-time confounding only in diagnostics; it
does not alter the generator. This is a process-suitability review, not a
joint `(rho, eta)` identifiability or observation benchmark.

## Goal 007

Goal 007 is the central-truth joint `(rho, eta)` positive control under perfect
direct predator detection:

```bash
uv run python scripts/run_goal007.py
```

The ignored 14-file review pack is written to
`artifacts/goal007_joint_rho_eta_perfect_detection/`. The frozen two same-time
visits are verified as exact duplicates and collapsed before fitting. Separate
full- and half-bank calibrations use a two-dimensional rook-connected support,
while held-out predictions use training-only tied MLE cells and the frozen
time-only neutral. The site-history simulated composite likelihood omits
between-site process dependence and is not a full joint spatial likelihood.
Scientifically negative classes exit successfully; only
`implementation_blocked` suppresses the pack and exits nonzero.

## Goal 008

Goal 008 extends the same joint perfect-detection benchmark to the frozen
3 by 3 grid crossing `rho = {0.5, 1, 2}` with `eta = {0.5, 1, 1.5}`:

```bash
uv run python scripts/run_goal008.py \
  --workers 9 \
  --compute-provenance-json compute-provenance.json
```

Each truth-cell and bank combination receives its own local cutoff. The 500
independent shock blocks per phase generate nine paired counterfactuals, so
cellwise intervals are pointwise rather than familywise. The ignored 16-file
review pack is written to
`artifacts/goal008_joint_rho_eta_cross_truth_perfect_detection/`. Completed
negative or mixed results exit successfully. Goal 009 keeps discrete central
continuity exact while comparing finite projection values after recursive
nine-decimal rounding; raw hashes remain non-gating audit evidence. A returned
`implementation_blocked` campaign suppresses the scientific pack, writes only
the three-file quarantine at
`artifacts/goal009_cross_truth_blocked_diagnostics/`, and exits nonzero.

## Goal 010

Goal 010 is a bounded perfect-detection sensitivity for the three high-`eta`
truth cells. It appends only `eta = 2.25, 2.5` to the candidate grid, preserves
the Goal 009 rho grid, shocks, seeds, block order, and bank halves, and
recomputes each local cutoff under the unchanged 476th-of-500 rule:

```bash
uv run --frozen python scripts/run_goal010.py \
  --goal009-pack PATH \
  --output-dir PATH \
  --workers 3 \
  --compute-provenance-json PATH
```

The ignored 14-file review bundle is written to
`artifacts/goal010_boundary_aware_joint_identifiability/`. Goal 009 remains
unchanged. More than 25 primary-cell contacts at the expanded `eta = 2.5`
face means the bounded candidate domain did not close; it is not proof of
universal or genuine non-identifiability. Scientifically negative outcomes
exit successfully. Provenance, exact bank replay, row-pairing, or other
implementation failures exit nonzero and write no scientific pack.

## Goal 011

Goal 011 returns to the central truth `(rho, eta) = (1, 1)` and retains both
known imperfect-detection visits at every site-time:

```bash
uv run python scripts/run_goal011.py
```

The primary candidate domain uses `eta = 0, 0.25, ..., 2.5`; a separately
recalibrated `eta <= 2` projection is descriptive and non-gating. Complete
12-record site histories are marginalized under known `p = 0.65` and zero
false positives, while held-out predictions target
`0.65 * Pr(occupied)`. The exact 15-file ignored review pack is written to
`artifacts/goal011_joint_known_imperfect_detection/`. Goal 007 remains
historical perfect-detection context rather than a strictly matched causal
contrast.

The completed production campaign returned
`advance_to_cross_truth_joint_imperfect_detection` for the full integration
bank and both halves. Coverage was `470/500`, `472/500`, and `471/500`, with
all three Wilson intervals containing `0.95`; connected-interior support was
`494/500`, `492/500`, and `494/500`, with no boundary contacts. No fitted
support or MLE used the appended `eta > 2` slices. The result authorizes the
next cross-truth known-detection benchmark, not a claim of general robustness
to observation error.

## Goal 012

Goal 012 evaluates the same known-`p = 0.65` joint recovery method at all nine
frozen `(rho, eta)` truths. It preserves Goal 011 exactly at cell 04, pairs
process shocks across truth cells, and uses a unique appended detection stream
for every noncentral cell and process block:

```bash
uv run python scripts/run_goal012.py \
  --output-dir artifacts/goal012_cross_truth_joint_known_imperfect_detection \
  --workers 9 \
  --compute-provenance-json PATH
```

The CLI also accepts `--reduced-smoke` for the explicit non-scientific local
check. Scientific grids, replicate counts, detection, cutoffs, thresholds, and
decision order are not command-line settings.

Every cell recalibrates full- and half-bank cutoffs separately for the primary
`eta <= 2.5` domain and descriptive `eta <= 2` projection. Artificial
candidate-face contact is reported separately from inability to exclude the
physical `eta = 0` null. The exact ignored review pack contains 15 files,
including all 27 cell-by-bank summaries and the three truth-grid figures.
Scientifically negative or mixed outcomes exit successfully; implementation or
provenance failures do not produce an accepted scientific pack.

The completed production campaign returned `cross_truth_design_limited`,
stable across the full bank and both halves. All three `eta = 0.5` truths
frequently retained the physical `eta = 0` uniform-resistance null; all six
truths with `eta >= 1` were recoverable. No primary-domain support contacted
an artificial face, all precision gates passed, and the process model beat the
time-only neutral predictively in every cell. The result therefore identifies
a practical weak-contrast limit under this frozen design and likelihood, not
universal non-identifiability or predictive failure.
