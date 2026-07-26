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
