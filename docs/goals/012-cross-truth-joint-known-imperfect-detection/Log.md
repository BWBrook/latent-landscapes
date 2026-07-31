# Goal 012 Log

## 2026-07-30: Approval And Design Freeze

Barry approved the cross-truth known-detection benchmark after Goal 011's
central positive control. No implementation began before approval.

Repository reconnaissance found that Goal 012 can remain a thin composition
layer. Goal 008 supplies paired process truth blocks and cross-cell execution
patterns; Goal 011 supplies the expanded bank, complete-history likelihood,
known-detection prediction, and dual-domain calibration.

An independent methodological review accepted the design with two refinements:

1. truth-specific cutoffs define locally calibrated cross-truth recovery, not
   transport of Goal 011's numeric cutoff; and
2. artificial candidate-boundary contact must be distinguished from failure to
   exclude the accepted physical `eta = 0` null.

Goal 004 draws detection randomness only for occupied records. Reusing one
detection seed across truth cells would therefore not create record-aligned
common random numbers. Goal 012 instead preserves the first five Goal 011
roots, uses exact Goal 011 streams for cell 04, and appends two roots providing
unique block-specific detection streams to the eight noncentral cells. Truth
cells are process-paired but observation-noise-distinct.

No source, tests, production simulation, remote compute, commit, or push had
occurred at this design-freeze point.

## 2026-07-30: Test-First Red Gate

Two focused behavioral modules were added before Goal 012 production code:

- `tests/test_goal012_benchmark.py`;
- `tests/test_goal012_artifacts_cli.py`.

The initial focused command:

```text
uv run pytest tests/test_goal012_benchmark.py tests/test_goal012_artifacts_cli.py
```

collected zero tests and returned the expected two import errors:

```text
ModuleNotFoundError: No module named 'latent_landscapes.goal012'
2 errors during collection
```

This is the intended red state. The tests reached the absent Goal 012 package
and pin the seed tree, cross-truth generation, central replay, local dual-domain
calibration, decision precedence, deterministic workers, review pack, and CLI
contracts rather than failing on an unrelated fixture or environment error.

## 2026-07-30: Minimal Implementation

The implementation adds a thin Goal 012 package without changing predecessor
code. Goal 008 generates one shared edge-shock block across the nine truths and
applies exact rho scaling. A narrow `StochasticSpreadTruth` view passes each
contrast truth to Goal 004's unchanged complete-visit generator. Goal 011's
public bank, complete-history profile, prediction, and eta-projection APIs
supply the inference path.

The seed manifest spawns seven roots. Its first five streams are exactly equal
to Goal 011, including both cell-04 detection phases. The appended roots create
one unique detection child for every noncentral cell and block. Every support
summary receives explicit truth rho and eta, and every cell-bank summary
retains both local cutoffs, both-domain face counts and precision metrics, all
gate booleans, predictive intervals, and classes.

The central reconciliation projects cell 04 back onto Goal 011's accepted
public contracts. Production acceptance requires the pinned source blobs,
exact seed and discrete projections, the accepted downstream meaning, and
nine-decimal canonical hashes derived from the accepted Goal 011 evidence.

The review writer produces the exact 15-file ignored pack and refuses blocked
or invariant-failed results. The CLI exposes only output directory, workers,
portable compute provenance, and the explicit reduced smoke. Negative or mixed
scientific classes return success; implementation-blocked results do not write
an accepted pack.

The first focused green gates were:

```text
benchmark tests    7 passed
artifact/CLI tests 3 passed
```

No production campaign, remote access, commit, push, earlier-goal edit, or
scientific retuning occurred.

## 2026-07-30: Local Acceptance And Reduced Smoke

The bounded local acceptance gates completed as follows:

```text
git diff --check                         passed
focused Goal 012 tests                   10 passed
relevant Goal 008/011 tests              20 passed
Ruff format check                        93 files already formatted
Ruff check                               passed
mypy src tests                           82 source files passed
full pytest                              199 passed, 3 inherited warnings
uv build                                 sdist and wheel built
```

The one local reduced CLI smoke retained the full 601 by 11 candidate grid,
used two integration draws, two calibration blocks, two validation blocks, and
three deterministic workers. It exited successfully with the non-production
negative class:

```text
likelihood_approximation_unstable
```

The ignored smoke pack at
`artifacts/goal012_reduced_smoke_local_20260730/` contains exactly 15 files.
Its tables contain 42 seed rows, 54 observation-signal rows, 54 calibration
rows, 54 validation rows, 27 cell-bank summaries, and 178,497 representative
profile rows. All campaign and cell invariants are true, and all 14 hashes
declared outside `verification.json` independently verified.

All three SVGs passed XML validation and rendered cleanly in headless Chrome.
The figures were inspected once against the full-bank table values. Cell 04's
smoke projection reconciled to the independently executed Goal 011 public path;
the production reference hashes correctly remain unchecked for this reduced
configuration.

Generated smoke, render-inspection, and build outputs remain ignored and
unstaged. No 500/500 campaign, remote access, commit, push, or Goal 013 work
occurred.

## 2026-07-30: Independent Preproduction Review

An independent code/science review accepted the seven-root seed contract,
cross-truth generation, local dual-domain calibration, decision precedence,
Goal 011 central projection, deterministic worker ordering, and strict
production runtime guards. Its focused Goal 012 and predecessor suites passed.

An independent artifact/provenance review recomputed every reduced-smoke
cutoff, aggregate, gate, bank-stability result, hash, and figure annotation
from the serialized evidence. It accepted the artifact and scientific paths
but rejected the initial Runbook as too sparse for the single authorized
production campaign.

The one material repair was therefore operational only. `Runbook.md` now gives
the exact Git-bundle, detached-checkout, portable production-provenance,
preflight, reduced-smoke, `tmux`, sentinel, checksum, retrieval, and local
verification recipe. No scientific code, candidate or truth grid, seed,
cutoff, threshold, neutral, decision rule, or reduced-smoke outcome changed.

## 2026-07-31: Production Campaign And Acceptance

The single authorized nine-worker campaign ran on `deep-server` from clean
detached implementation commit
`b2bdfbb95051bfec09676c4cdbfa4e2e0303fd97`. Run
`goal012-20260730T142431Z-b2bdfbb` completed once with exit status zero in
`2:08:44` and returned:

```text
cross_truth_design_limited
```

The complete 45-file remote evidence bundle passed recursive checksum
verification before and after retrieval. All nine worker processes exited
zero; the production pack contains exactly the required 15 files and all raw
table, seed, source, environment, and central Goal 011 reconciliation checks
passed.

The result is stable across the full integration bank and both halves. The
three `eta = 0.5` truths are `cell_design_limited`: their full-bank
connected-interior counts are `251`, `344`, and `327` of 500, driven
principally by `249`, `155`, and `171` supports contacting the physical
`eta = 0` uniform-resistance null. The six truths with `eta >= 1` are
`cell_recoverable`. No primary-domain support contacts an artificial face,
every precision gate passes, and every paired Brier interval lies wholly below
zero. Cell 00 additionally shows conservative overcoverage, but the same
physical-null limitation remains at calibrated cells 01 and 02.

The descriptive old `eta <= 2` projection shows artificial upper-face contact
for cells 06 and 07; it is non-gating, and the primary `eta <= 2.5` domain
removes that truncation.

Two independent audits accepted the result. The scientific audit reconstructed
all 54 cutoffs and every aggregate, gate, and class from the 13,500 calibration
and 13,500 validation rows. The provenance audit verified the complete bundle,
14,096 unique seed streams, worker telemetry, source and lock hashes, all
declared output hashes, rendered figure annotations, and exact Goal 011 central
replay.

The inference is deliberately narrow: under this frozen landscape, sampling
design, known homogeneous `p = 0.65`, and composite likelihood, weak
landscape-resistance contrast cannot reliably be separated from uniform
resistance. This is not evidence of universal structural non-identifiability,
a sharp threshold between `eta = 0.5` and `eta = 1`, or failed prediction.
Goal 012 stops without retuning or a rescue campaign.
