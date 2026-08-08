# Goal 015: Cross-Truth Cell Engine

## Product Promise

Latent Landscapes uses controlled synthetic experiments to determine when
spatial predator-spread parameters are identifiable and recoverable. Current
science should depend on named scientific components, not on the historical
goal wrapper that first introduced them.

## Objective

Extract the reusable known-detection cross-truth cell engine from the Goal 012
campaign module and migrate Goal 013 to its public scientific API. Leave the
completed Goal 012 campaign as a smaller historical orchestrator. Do not add a
compatibility facade or redesign the likelihood, evidence packs, or reports.

## Protected Scientific Invariants

- Landscape, sampling design, truth cells, candidate grids, observation model,
  likelihood, calibration, validation, and outcome precedence are unchanged.
- Random streams remain deterministic, disjoint, and replayable.
- Goal 009 and Goal 012 evidence authentication remains unchanged.
- Reduced Goal 013 scientific tables, figures, report, and outcome remain
  byte-identical; runtime telemetry may differ.
- Negative scientific outcomes remain valid successful outcomes.

## Intended Architecture

```text
cross_truth.py
  configuration + seeds + truth generation + observations
  cell calibration + validation + classification
          |
          +--> Goal 012 historical nine-cell campaign
          +--> Goal 013 current intervention campaign
```

Goal 013 must no longer import the Goal 012 benchmark for its cell engine.
Goal 012 may import the shared engine because it remains a genuine campaign
consumer, but no new alias or adapter exists solely to preserve old imports.

## Review Surface

- new numbered-goal-independent scientific module;
- smaller Goal 012 campaign wrapper;
- Goal 013 imports and type annotations;
- focused engine and campaign tests;
- byte comparison of reduced Goal 013 outputs before and after extraction;
- line-count and import-closure evidence.

## Proportional Gates

- Ruff formatting and lint;
- MyPy over source and tests;
- focused Goal 012 and Goal 013 tests;
- reduced Goal 013 CLI and scientific-output comparison;
- full test suite and package build once after the focused gate passes.

## Non-Goals

- no likelihood, parameter-grid, observation-design, estimand, or decision
  change;
- no production or remote campaign;
- no Goal 012 evidence-pack or artifact-schema redesign;
- no general artifact-writer consolidation;
- no wholesale deletion of historical goals or tests.

## Acceptance and Stop Rule

Accept when Goal 013 uses the public cell engine, Goal 012 is materially
smaller, scientific outputs are unchanged, and the proportional gates pass.
Perform at most one focused repair pass for material defects. Stop before
presentation-layer cleanup or further historical pruning.

Barry authorised implementation of this tranche. Commit, push, and publication
are not authorised.

## Outcome

- Added `src/latent_landscapes/cross_truth.py`, a 1,458-line scientific module
  containing the configuration, seed design, truth and observation generation,
  cell calibration, validation, and cell classification API.
- Reduced the Goal 012 benchmark from about 2,180 lines to 816 lines. It now
  contains only the historical nine-cell campaign, central reconciliation,
  telemetry, and campaign-level classification.
- Migrated Goal 013 configuration, seed manifests, result types, and cell
  execution directly to `cross_truth`; its benchmark no longer imports the
  Goal 012 benchmark.
- Reduced Goal 013 runs before and after the extraction produced byte-identical
  scientific tables, figures, report, configuration, and outcome
  (`likelihood_approximation_unstable`). Only wall-time and memory telemetry,
  plus the consequent telemetry hash, differed.
- Ruff, MyPy, all 209 tests, the reduced Goal 013 CLI, and the package build
  passed. Three pre-existing Goal 006 plotting deprecation warnings remain.

## Deliberate Residuals

- The cell engine is cohesive but still substantial; split it only when a
  concrete scientific extension makes a second boundary useful.
- Goal 013 artifacts still reuse Goal 012's row serializers and published
  evidence schema. This is presentation-layer debt, not a current scientific
  dependency, and was outside this goal.
- Stop here. Further codebase cleanup would not change the present scientific
  decision. The next step should return to the ecological and inferential
  question before another engineering tranche is proposed.
