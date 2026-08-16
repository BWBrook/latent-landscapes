# AGENTS.md for Latent Landscapes

## Scope

This repository contains the Latent Landscapes research programme. Work only
inside this repository unless an explicit goal authorizes a named external
read or side effect. Do not alter sibling repositories or treat them as
runtime dependencies.

The Paper 1 scientific North Star and definition of done are defined in
`docs/paper1-experimental-design-charter.md`. Adaptive execution is governed by
`docs/paper1-adaptive-implementation-roadmap.md`. The detailed historical record
remains in `docs/programme.md`. Provenance and legacy reuse are governed by
`docs/provenance.md` and the decision records under `docs/decisions/`.

## Authority

- Work from an explicit, bounded goal.
- Keep methods modular and preserve independently testable scientific units.
- Require human review at scientific gates, including changes to estimands,
  observation design, model comparisons, or inferential claims.
- Treat negative results as valid results. Failure triggers diagnosis, not
  unrecorded retuning.
- Apply Pareto discipline: add machinery only when it materially improves
  scientific validity, reproducibility, or reviewability.
- Do not introduce exhaustive contract machinery by default.
- Every substantial goal must identify the charter pillar, roadmap arc,
  scientific decision, or planned manuscript evidence it advances.
- Perform bounded code consolidation at major scientific arc boundaries rather
  than preserving goal-specific developmental machinery indefinitely.
- Do not commit, push, publish, create remotes, or expose the repository
  externally without explicit goal authority.

## Legacy Material

`/Users/bwbrook/papers/spatext` and `https://github.com/BWBrook/spatext` are
read-only laboratory notebook and parts-catalogue sources. Access them only
when an explicit goal permits it. Never modify them and never create a runtime
dependency on them. Any transplant must follow `docs/provenance.md`.

## Implementation Boundaries

- Paper 1 remains synthetic-only.
- The real mink-vole application belongs to a later, separate programme or
  paper.
- The reserved Python namespace is `latent_landscapes`.
- Do not add package infrastructure, source code, or goal-control files unless
  a future goal explicitly requires them.

## Subagents

Use native subagents only under the machine-wide policy. This file does not
pin models, reasoning settings, or delegation profiles. Delegation does not
expand repository scope or publication authority.
