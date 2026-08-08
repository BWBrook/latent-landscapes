# Goal 014: Lean Active Path

## Product Promise

Latent Landscapes provides controlled synthetic experiments that reveal when
spatial predator-spread parameters are identifiable and recoverable from
imperfect observations. Barry is the current user. The active contract is the
scientific result, its compact review evidence, and enough provenance to
reproduce it; historical executable layouts are not supported contracts.

## Objective

Make the current Goal 013 execution path easier to change without weakening a
scientific decision boundary. Complete a bounded architecture audit and remove
runtime source-identity gates that treat edits to predecessor code as failed
science. Preserve numerical results, evidence-pack authentication, seed replay,
semantic reconciliation, decision rules, and production provenance.

## Protected Invariants

- Synthetic truth, sampling design, observations, likelihood, candidate grids,
  calibration, and outcome precedence do not change.
- Random streams remain deterministic, disjoint, and replayable.
- Goal 009 and Goal 012 evidence packs remain authenticated and semantically
  reconciled before reuse.
- Negative scientific outcomes remain successful completed outcomes.
- Production runs still require a clean source state, explicit compute
  provenance, fixed worker/thread settings, and recorded source commit.
- No accepted result is reclassified and no production campaign is rerun.

## Active Flow

```text
landscape + sampling design
          -> stochastic spread process
          -> imperfect observations
          -> likelihood and calibration
          -> scientific decision
          -> compact review evidence
```

Historical goal packages currently cross these boundaries and remain in the
repository for this tranche. Future work should depend on scientific units,
not on the number of the goal that first introduced them.

## Module Dispositions

| Current modules | Disposition | Reason |
| --- | --- | --- |
| `goal001/{design,landscape,likelihood,observations,spread}.py` | Retain, later extract | Small reusable scientific primitives. |
| `goal001/{benchmark,artifacts,__init__}.py` | Defer deletion | Completed Goal 001 wrapper and presentation. |
| `goal002/{baseline,calibration}.py` | Retain, later extract | Reusable neutral comparison and calibration. |
| `goal002/{benchmark,artifacts,__init__}.py` | Defer deletion | Completed Goal 002 wrapper and presentation. |
| `goal003/spread.py` | Retain, later merge | Current stochastic process primitive. |
| `goal003/{benchmark,artifacts,__init__}.py` | Defer deletion | Completed process-review wrapper. |
| `goal004/{likelihood,observations}.py` | Retain, later extract | Current imperfect-observation likelihood units. |
| `goal004/{benchmark,artifacts,__init__}.py` | Simplify, then delete wrapper | Large orchestration and historical report code. |
| `goal005/{benchmark,artifacts,__init__}.py` | Defer deletion | Completed cross-rate experiment; no current scientific unit originates here. |
| `goal006/spread.py` | Retain, later merge | Resistance transformation and paired spread unit. |
| `goal006/{benchmark,artifacts,__init__}.py` | Defer deletion | Completed contrast-review wrapper. |
| `goal007/{likelihood,observations}.py` | Retain, later extract | Current joint likelihood and observation units. |
| `goal007/benchmark.py` | Simplify now | Active upstream code mixes science with source-identity compatibility gates. |
| `goal007/{artifacts,__init__}.py` | Defer deletion | Historical review output and package shim. |
| `goal008/benchmark.py` | Source gate removed; extract later | Large cross-truth orchestration and replay machinery still used downstream. |
| `goal008/{artifacts,__init__}.py` | Defer deletion | Historical review and blocked-pack machinery. |
| `goal010/{benchmark,artifacts,__init__}.py` | Defer deletion after evidence extraction | Goal 013 uses its Goal 009 evidence reader. |
| `goal011/likelihood.py` | Retain, later extract | Current known-detection likelihood unit. |
| `goal011/benchmark.py` | Simplify later | Active integration-bank builder mixed with historical experiment orchestration. |
| `goal011/{artifacts,__init__}.py` | Defer deletion | Historical review output and package shim. |
| `goal012/benchmark.py` | Source gate removed; extract next | Current cell engine is buried in a 2,245-line historical campaign module. |
| `goal012/artifacts.py` | Simplify later | Goal 013 reuses private row serializers. |
| `goal012/__init__.py` | Defer deletion | Empty package shim. |
| `goal013/{design,evidence}.py` | Retain, simplify only when earned | Current intervention and authenticated evidence input. |
| `goal013/benchmark.py` | Simplify now and next | Current orchestration; remove recursive source-identity gate first. |
| `goal013/artifacts.py` | Simplify next | Current report, figures, serialization, and provenance are mixed. |
| `goal013/__init__.py` | Retain temporarily | Current package entry. |

## Duplication Map

- Twelve goal-specific artifact writers total 8,781 lines.
- Mechanical helpers recur across them: 12 CSV writers, 8 JSON writers,
  7 SVG writers, 6 SVG-ID normalizers, and 4 provenance validators.
- Twelve benchmark modules total 12,346 lines; the largest is Goal 012 at
  2,245 lines.
- The Goal 013 static import closure reaches 32 modules and 17,477 lines.
- Thirty-seven test files contain 178 tests; artifact-contract and exact-byte
  checks repeatedly cover the same serialization failure classes.
- Fifty-two Goal/Plan/Runbook/Log files total 8,100 lines. This goal uses one
  file deliberately.

## Proportional Gates

### Fast change gate

- focused Goal 007 and Goal 013 tests;
- Ruff formatting and lint;
- MyPy over source and tests;
- compare reduced Goal 013 scientific tables before and after the change.

### Release gate

- full test suite;
- package build;
- one reduced Goal 013 CLI smoke;
- verify generated scientific tables and outcome, not exact historical bytes.

No production or remote campaign is justified because this tranche changes no
scientific calculation.

## Acceptance

- The current Goal 013 path no longer gates its outcome on hard-coded Git
  ancestry or predecessor source-blob identities.
- Source commit and environment provenance remain recorded at the production
  boundary.
- Evidence-pack hashes and semantic reconciliation remain enforced.
- Reduced scientific results are unchanged, apart from removal of obsolete
  source-identity invariant fields and consequent bundle hashes.
- One focused review/repair pass completes the tranche; further historical
  cleanup is deferred.

## Authority and Stop Rule

Barry authorised this bounded audit and implementation. Commit, push, and
publication are not authorised. Stop once the accepted gates pass and report
the remaining large-module and historical-wrapper burden for the next tranche.

## Outcome

- Removed 234 lines of hard-coded Git ancestry, blob-identity, and recursive
  source-gate code from Goals 007, 008, 012, and 013; added nine focused lines.
- Before and after reduced Goal 013 runs produced byte-identical scientific
  tables, figures, report, configuration, and outcome
  (`likelihood_approximation_unstable`). Only runtime telemetry and the removed
  source-invariant metadata changed.
- Evidence-pack hashes, semantic reconciliation, deterministic seeds,
  numerical reference checks, production cleanliness/provenance, and
  scientific decision rules remain protected.
- Ruff formatting and lint, MyPy, all 209 tests, the reduced Goal 013 CLI, and
  the package build passed. The only warnings are three pre-existing Goal 006
  plotting-library deprecations.
- Stop here. The highest-value next tranche is to extract the Goal 012 cell
  engine behind a small scientific API so current work no longer depends on a
  2,000-line historical campaign wrapper. Artifact-writer consolidation and
  historical test deletion remain deliberately deferred.
