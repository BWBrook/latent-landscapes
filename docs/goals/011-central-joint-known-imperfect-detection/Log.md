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

## 2026-07-30: Single Remote Campaign

The accepted implementation was committed before dispatch:

```text
d7a1670852e9b8cb7e6e30cd098db38fabdbd91a
feat: add joint known-detection benchmark
```

The campaign used the clean detached source bundle
`goal011-20260730T055654Z-d7a1670` on `deep-server`. Its frozen lockfile hash
was:

```text
c6452f1ada29e08ba0b97c0df0d8d3fad61ff0e821348e305b9a6caaa890deb5
```

The first non-login preflight stopped before tests or simulation because `uv`
was not on that shell's `PATH`. Repeating the operational preflight with the
explicit installed path passed the 12 focused tests and the reduced smoke. This
did not consume the single production attempt.

The production command started at `2026-07-30T05:58:53Z` and completed at
`2026-07-30T07:30:20Z`:

```text
exit status       0
elapsed           1:31:26
maximum RSS       449844 KiB
outcome           advance_to_cross_truth_joint_imperfect_detection
```

The recursive retrieval manifest covered 39 evidence files. Every returned
hash, the internal 15-file review-pack contract, the source bundle, source
manifest, commit identity, and lockfile hash verified locally. Generated
remote evidence was retained under ignored `artifacts/` and was not staged.

## 2026-07-30: Scientific Result

The expanded-domain results were:

| Bank | Coverage | Wilson interval | Connected interior | Boundary contacts | Median absolute log-rho error | Median absolute eta error | Log-rho width | Eta width |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| full | 470/500 | 0.9156-0.9577 | 494/500 | 0 | 0.041589 | 0 | 0.346574 | 0.5 |
| first half | 472/500 | 0.9203-0.9610 | 492/500 | 0 | 0.041589 | 0 | 0.346574 | 0.5 |
| second half | 471/500 | 0.9179-0.9593 | 494/500 | 0 | 0.041589 | 0 | 0.351195 | 0.5 |

All three paired-Brier intervals were wholly below zero. Mean process Brier
scores were approximately `0.13915`, compared with `0.18699` for the
training-only time neutral. Expanded and separately recalibrated old-domain
cutoffs and outcomes were identical in every bank, and neither fitted support
nor any MLE used `eta > 2`.

The observed coverage estimates were `0.940-0.944`; they passed because their
Wilson intervals contained `0.95`, not because the point estimates equalled
the nominal target. Median precision gates also do not mean every replicate
was precise: 52-56 of 500 validation datasets per bank exceeded absolute
log-rho error `0.10`, and two per bank exceeded absolute eta error `0.25`.

The accepted conclusion is therefore bounded: at the central truth, with one
landscape and sampling design, known homogeneous detection `p = 0.65`, zero
false positives, and this calibrated composite likelihood, the process model
is practically recoverable and predictively superior to the neutral. The
likelihood retains within-site histories but omits shared between-site spatial
dependence. The result does not establish cross-truth robustness or recovery
under estimated or heterogeneous detection.

## 2026-07-30: Independent Result Review

Two independent read-only reviews accepted publication. The science reviewer
recomputed all cutoffs, Wilson intervals, topology counts, errors, widths,
paired-Brier intervals, domain-use counts, and downstream classes from the raw
tables. The provenance reviewer verified all retrieval and internal hashes,
reconstructed all 6,096 unique seed streams, reconciled table row counts and
timing records, and rendered all three SVGs against their source tables.

The only non-blocking provenance limitation was that `preflight.log` began at
environment synchronisation rather than retaining the earlier remote Git and
lock-hash probe output. The adjacent verified bundle, manifest, frozen command,
focused remote tests, and recursive retrieval manifest provide the source
linkage used for acceptance.
