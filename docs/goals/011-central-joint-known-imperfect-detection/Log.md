# Goal 011 Log

## 2026-07-30: Authorized And Framed

Barry approved the central joint known-imperfect-detection benchmark and
authorized `deep-server`, `tmux`, and a wake-up handoff for the long campaign.

The clean accepted repository state was
`17ba6b7b036013eee1fdf940e8d68b8de839220e` on `main`. Work began on
`codex/latent-landscapes-goal011-known-detection`.

Read-only reconnaissance found that the required vertical slice composes
without redesign:

- Goal 004 already generates complete two-visit histories with known
  `p = 0.65`, zero false positives, and an exact site-history probability
  calculation;
- Goal 007 already supplies paired joint category weights, two-dimensional
  rook support, calibrated bank comparisons, held-out prediction, and the
  deliberately coarse central positive-control gates; and
- Goal 010 established `eta <= 2.5` as the closed candidate domain for this
  frozen central perfect-detection experiment.

The new likelihood therefore marginalizes each complete detection history over
the seven latent onset categories at every `(rho, eta)` cell. It does not
collapse visits and it does not estimate detection.

Independent scientific review required an attribution guard: the primary
Goal 011 result uses `eta <= 2.5`, while a separately recalibrated `eta <= 2`
projection is reported but does not gate the decision. Goal 007 remains a
historical positive-control reference rather than a strictly matched
detection-only counterfactual.

The seed plan preserves Goal 007's integration, calibration-process, and
validation-process roots exactly, then appends independent calibration- and
validation-detection roots. The one 500/500 campaign will stop on any completed
scientific class. No observation retuning, threshold relaxation, or rescue run
is authorized.

## 2026-07-30: Test-First Red Gate

Three focused behavioral modules were added before production code:

- `tests/test_goal011_likelihood.py`;
- `tests/test_goal011_benchmark.py`; and
- `tests/test_goal011_artifacts_cli.py`.

The initial focused command collected zero tests and returned the expected
three import errors:

```text
ModuleNotFoundError: No module named 'latent_landscapes.goal011'
3 errors during collection
```

This is the intended red state: the tests identify the absent Goal 011
likelihood, benchmark, artifact, and CLI surfaces rather than an unrelated
fixture or environment failure.

## 2026-07-30: Minimal Implementation

The implementation adds a thin Goal 011 package without modifying earlier
goal code. Its only new likelihood operation is the eta-by-rho analogue of
Goal 004's history marginalization:

```text
site probability = sum(category weight * complete-history probability)
composite log likelihood = sum(log(site probability))
```

The benchmark spawns five roots, verifies exact identity with Goal 007's first
three process roots, independently rebuilds the old eta slices, and requires
bit-exact replay before accepting the appended `2.25` and `2.5` slices. It
retains every visit record, recalibrates full and half-bank cutoffs separately
for both domains, keeps separate boundary-face evidence, and gates only on the
expanded-domain classes.

The review writer produces the exact 15-file contract, including both domain
summaries, visit-level prediction evidence, the noncausal historical Goal 007
context, and three deterministic SVGs. The CLI exposes only the output
destination and an explicit non-scientific reduced smoke; detection, grids,
replicate counts, thresholds, and other scientific settings are not tunable.

The first complete focused green gate was:

```text
12 passed
```

No production campaign, remote access, prior-goal edit, commit, or push
occurred.

## 2026-07-30: Local Acceptance And Reduced Smoke

The bounded local acceptance gates completed as follows:

```text
git diff --check                         passed
focused Goal 011 tests                   12 passed
relevant Goal 004/007 tests              23 passed
Ruff format check                        87 files already formatted
Ruff check                               passed
mypy src tests                           77 source files passed
full pytest                              189 passed, 3 inherited warnings
uv build                                 sdist and wheel built
```

The one local reduced CLI smoke retained the full 601 by 11 candidate grid,
used two integration draws, two calibration datasets, two validation datasets,
and both one-draw bank halves. It completed with the scientifically valid
non-production class:

```text
joint_imperfect_detection_design_limited
```

The ignored smoke pack at
`artifacts/goal011_reduced_smoke_local_20260730/` contains exactly 15 files.
Its verification document reports all invariants true. The tables contain ten
seed streams, six calibration rows, six validation rows, three bank summaries,
three predictive summaries, three domain comparisons, and 19,833
representative profile cells plus the CSV header.

All three SVGs are valid deterministic XML. The joint surface and domain
comparison were visually inspected against their source tables. The
calibration source SVG has the intended wide three-panel view box and complete
panel geometry; macOS Quick Look's square thumbnail crops the right edge of
that wide preview, which is a preview limitation rather than a source-file
layout defect.

Generated smoke evidence and build outputs remain ignored and unstaged. No
500/500 production campaign, remote access, prior-goal modification, commit,
or push occurred.

## 2026-07-30: Independent Preproduction Review

An independent read-only reviewer accepted the implementation for the single
remote campaign without a repair request. The review:

- matched the joint likelihood tensor against an explicit
  eta-by-rho-by-site-by-category calculation;
- independently reconstructed both-domain cutoffs, coverage and topology
  counts, Wilson and paired-Brier intervals, precision medians, downstream
  classes, appended-domain use counts, and representative-profile support and
  MLE masks from the smoke CSVs;
- verified every declared file hash and all five seed-root families;
- reran the 12 Goal 011 tests and 23 relevant Goal 004/007 tests; and
- confirmed that the production CLI exposes no scientific retuning controls
  and that no earlier-goal source is modified.

The remaining risks are the declared composite-likelihood approximation and
ordinary remote operational failure. Neither is an implementation blocker.
