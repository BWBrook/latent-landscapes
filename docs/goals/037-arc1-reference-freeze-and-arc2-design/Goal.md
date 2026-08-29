# Goal 037: Arc 1 Reference Freeze And Arc 2 Design

## Programme role

This goal closes Roadmap Arc 1 and Charter Pillar 1 after Barry accepted Goal
036. It turns the accumulated reference-case experiments into one durable
scientific decision surface, removes a bounded set of caller-free developmental
machinery, and prepares Arc 2A for human design review. It does not authorize an
Arc 2 simulation campaign.

## Required outcomes

1. Synthesize the accepted Arc 1 evidence in ecological language, separating
   direct observations, defensible inferences, and claim boundaries.
2. Freeze the reference design, estimands, standard evaluation surface, and the
   distinction between parameter-specific and simultaneous joint uncertainty.
3. Preserve the decision-relevant evidence in a compact machine-readable table.
4. Draft a provisional, staged Arc 2A predator-only recoverability design for
   Barry to review before any production work.
5. Delete only the named historical execution islands after proving that no
   surviving production source imports them.

## Authority and boundaries

The authorized deletion set is:

- `src/latent_landscapes/goal016/`;
- `src/latent_landscapes/goal017/`;
- `src/latent_landscapes/goal027.py`;
- `src/latent_landscapes/goal036.py`;
- their four matching CLI scripts;
- their seven matching test files; and
- the Goal 036-only `ValidationDiagnostics` extension in Goal 026.

Goal records remain as the historical scientific account. Git preserves the
deleted executable implementations. Do not add an archive, compatibility shim,
replacement abstraction, migration, or deletion ledger.

Retain Goals 018-033 and `cross_truth.py`. Their code contains active joint,
observation, prey, and uncertainty kernels, but the correct reusable boundary
has not yet been earned by an Arc 2 runner. Extracting them now would be
speculative refactoring.

No simulation, inference, generated-artifact regeneration, web work, remote
compute, new scientific result, Arc 2 production, commit, or push is authorized.

## Protected scientific invariants

Surviving tests must continue to protect:

- reference landscape geometry and sampling design;
- stochastic spread and resistance mechanics;
- imperfect-detection semantics and zero false positives;
- absorbing prey hazard and interval censoring;
- full-support neutral held-out prediction;
- calibration/validation separation;
- likelihood-support topology; and
- marginal uncertainty calibration.

## Success and stop rules

The goal succeeds when the three durable documents and compact evidence table
are internally consistent; the deletion targets have no surviving production
callers or residue; the protected focused tests and one full release gate pass;
and Arc 2A remains explicitly provisional. Perform one serious review and at
most one material repair. Stop if further work is cosmetic, if an extraction
would require guessing the future architecture, or if Arc 2 requires a material
scientific choice from Barry.

Barry approved proceeding on 29 August 2026.

## Observed outcome

Arc 1 is frozen conditionally to the single reference landscape, access design,
survey window, process family, and tested truths. The synthesis preserves three
operational reference-case transitions: resistance discrimination between
`eta = 0.5` and `0.75`; joint spread/detection precision between approximately
`rho = 0.871` and `1.0`; and strict prey-effect recovery between threefold and
fourfold at 11.3% counterfactual 60-day background extirpation risk. A fivefold
prey effect was detected but not precisely recovered at 5% background risk and
fully recovered at 11.3% and 20%.

The Arc 2A brief recommends a 16-point predator-only scrambled Sobol pilot over
spread rate, resistance contrast, and per-visit detection probability. It
contains a hard human gate before expansion to 32 points or targeted
enrichment. Resistance bounds remain provisional until translated from `eta`
into induced edge-cost contrasts that an ecologist can interpret.

## Consolidation account

The pre-deletion AST import audit found no production source outside the named
islands importing Goals 016, 017, 027, or 036. The bounded tranche then:

| Disposition | Files | Python lines | Collected tests |
| --- | ---: | ---: | ---: |
| Deleted source islands | 9 | 3,477 | - |
| Deleted CLI scripts | 4 | 196 | - |
| Deleted historical tests | 7 | 734 | 22 |
| Simplified Goal 026 result contract | 1 modified | 40 | - |
| **Total removed** | **20 deleted + 1 simplified** | **4,447** | **22** |

The tracked Python surface fell from 168 files and 54,004 lines to 148 files
and 49,557 lines. Test files fell from 59 to 52 and collected tests from 282 to
260. This is an 8.2% reduction in active Python lines without changing a live
scientific workflow.

Deleted paths were exactly:

- `src/latent_landscapes/goal016/{__init__,artifacts,benchmark,discrimination}.py`;
- `src/latent_landscapes/goal017/{__init__,artifacts,reconciliation}.py`;
- `src/latent_landscapes/goal027.py` and `goal036.py`;
- `scripts/run_goal{016,017,027,036}.py`;
- `tests/test_goal016_{artifacts,benchmark,cli,discrimination}.py`;
- `tests/test_goal017_reconciliation.py`;
- `tests/test_goal027.py`; and
- `tests/test_goal036.py`.

The retained Goal 018-033 modules and tests defer further consolidation until
Arc 2A establishes a concrete runner and its actual kernel needs. Goal 026
retains its original compact result contract; only the caller-free Goal 036
truth-assisted diagnostic payload was removed.

## Validation

The pre-deletion search and AST audit found no surviving production import of
the authorized source islands. After deletion, a second AST audit found no
deleted-module import, and targeted residue checks found no deleted CLI,
module, or `validation_diagnostics` implementation. Historical references to
accepted Goal 027 evidence remain intentionally in Goal 028-029; they load
published evidence and do not import the deleted Goal 027 runner.

Proportional validation passed:

- 31 focused tests covering reference design and landscape, Goal 006 resistance
  mechanics, Goal 019 joint predator inference, Goal 026 prey persistence,
  Goal 029 imperfect prey detection, Goal 031 latent arrival, and Goal 033
  parameter-specific uncertainty;
- the full suite: 260 passed in 2 minutes 52 seconds, with three inherited Goal
  006 Matplotlib pending-deprecation warnings;
- Ruff format check: 148 files already formatted;
- Ruff lint: all checks passed;
- strict MyPy: no issues in 121 source files;
- source distribution and wheel build;
- tracked and new-file whitespace checks; and
- final CSV/schema, deleted-path, ignored-output, and semantic residue checks.

The focused review repairs corrected the slow-wave evidence label to the exact
rounded truth `rho = 0.758`, made Sobol anchors and common-random-number pairing
explicit in the Arc 2 brief, and separated the accepted predator and prey
neutral-prediction evidence in the compact table. They changed no accepted
result or active scientific code. No scientific production CLI or production
workflow ran. `artifacts/` and `dist/` remain ignored, and nothing was staged,
committed, or pushed.
