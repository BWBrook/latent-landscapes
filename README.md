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
evidence. A distinct full-support predictive neutral baseline is reserved for
subsequent work.

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

Programme scope and method sequence are in `docs/programme.md`. Legacy-source
handling is governed by `docs/provenance.md` and
`docs/decisions/0001-rebuild-from-spatext.md`.
