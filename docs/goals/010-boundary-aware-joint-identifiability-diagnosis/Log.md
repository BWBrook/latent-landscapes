# Goal 010 Log

## 2026-07-28: Goal Authorized

Barry approved the bounded boundary-aware diagnosis proposed after Goal 009.

The orchestrator refreshed the clean published repository at
`aa3f07e5dcd2011e4033461e25dd857cd0fc1ed6` and created branch
`codex/latent-landscapes-goal010-boundary-identifiability`.

Two read-only reviews were commissioned before implementation:

- repository reconnaissance confirmed that the Goal 009 pack retains all
  13,500 validation rows, including support indices, components, faces,
  widths, errors, and predictions, plus 27 complete representative profile
  surfaces;
- independent methodological review identified that expanding the candidate
  domain changes the profile maximum. The numerical cutoff therefore must be
  recalibrated on the same blocks using the unchanged 476th-of-500 rule.

The review also clarified that same-shock integration-bank slices are preserved
for the old domain while the expanded bank gains two new slices. Continued
contact at `eta = 2.5` will be interpreted as an unclosed practical ridge, not
proof of genuine non-identifiability.

Barry's approval already covers the proposed three high-`eta` cells. Cell 06 is
the primary diagnostic; cells 07-08 remain prespecified comparators at no
additional campaign wall-time when run as three parallel workers.

No implementation or remote campaign had started at this log entry.

## 2026-07-28: Local Implementation

Development began test-first on the dedicated Goal 010 branch. The first red
gate failed at the intentionally absent `goal010` package. After adding only
the empty module surfaces, the focused suite collected 21 behavioral checks
and failed on every absent benchmark, artifact, provenance, and CLI API.

The implementation is a thin wrapper around the public Goal 008 per-cell
runner. It:

- authenticates the exact 16-file Goal 009 pack and all 15 declared payload
  hashes before parsing scientific evidence;
- validates CSV schemas, row order and identity, counts, classes, outcome,
  seed replay, and the accepted nine-decimal cross-platform rho-grid identity;
- constructs old and expanded same-seed integration banks separately and
  requires bit-exact equality of every old eta slice;
- runs only cells 06-08, recomputes all nine local cutoffs, and pairs every
  selected validation row by block, cell, and bank;
- retains calibration, validation, summary, support, MLE, prediction, and
  paired-transition evidence needed to recompute the decision; and
- writes the exact deterministic 14-file bundle atomically only after strict
  internal hash validation.

Production provenance is rejected before pack parsing or simulation unless it
declares and matches the clean detached source, commit, bundle, lock and input
manifest hashes, three workers, four single-thread limits, focused tests,
reduced smoke, runtime environment, and exact command. A completed scientific
negative exits zero. An implementation or provenance block exits nonzero and
writes no scientific pack; no Goal 010 quarantine path is authorized.

The decision wording was made mechanical without adding a threshold: any
primary-bank expanded upper-face count above 25 is `domain_not_closed`;
resolution requires at least 475 connected-interior supports and a recoverable
class in every bank; otherwise an upper-face count at most 25 that is strictly
below baseline, with another unchanged gate failing, is `contributes`. MLE
counts at `eta = 2.5` remain descriptive.

The first focused green gates were:

```text
Goal 010 benchmark tests       6 passed
Goal 010 artifact/CLI tests   15 passed
```

No production campaign, remote access, commit, push, threshold change, second
eta expansion, or Goal 009 reclassification occurred.

## 2026-07-28: Local Acceptance And Reduced Smoke

The bounded local acceptance suite completed:

```text
git diff --check                         passed
focused Goal 010 tests                   21 passed
relevant Goal 008 tests                  18 passed
Ruff format check                        79 files already formatted
Ruff check                               passed
mypy src tests                           70 source files passed
full pytest                              176 passed, 3 inherited warnings
uv build                                 sdist and wheel built
```

The fixed reduced CLI smoke used both one-draw bank halves, two calibration
blocks, two validation blocks, all eleven eta values, and three selected-cell
worker processes. It wrote and revalidated the exact 14-file contract at:

```text
artifacts/goal010_reduced_smoke_20260728T042436Z/output/scientific-pack/
```

The smoke outcome was
`bounded_upper_expansion_domain_not_closed`. This is implementation evidence,
not a scientific result. The smoke bundle contained 27 baseline anatomy rows,
18 expanded calibration rows, 18 expanded validation rows, nine summaries, 18
paired transitions, nine domain comparisons, and 297 representative-profile
rows. Both SVGs were rendered independently in Chrome and were readable,
non-overlapping, and consistent with the deliberately tiny tables.

Generated smoke evidence and build outputs remain ignored and unstaged. The
production Goal 009 pack was read only; the production Goal 010 campaign was
not run.

## 2026-07-28: Preproduction Decision-Precedence Repair

An overlap regression reproduced a precedence defect: when one primary bank
had 26 expanded upper-face contacts and a design-limited class while the other
banks were recoverable, the decision incorrectly returned
`likelihood_approximation_unstable`. The first red test captured that exact
failure.

The open-domain gate now follows only implementation invariants and primary-bank
identity, before downstream class agreement. Thresholds and the resolution and
contribution rules are unchanged. The focused regression then passed, and the
requested Goal 010 plus Goal 008 suite completed with `40 passed in 50.88s`.

The post-repair preproduction checkpoint then completed with `177 passed` in
the full suite, the same 40 focused Goal 010 and Goal 008 tests passing again,
Ruff format and lint checks clean, mypy clean across 70 source files, a
successful package build, and `git diff --check` clean. One test-only mypy
annotation issue and two formatting differences were repaired before this
checkpoint; neither changed scientific behavior.

## 2026-07-28: Production Campaign

The accepted implementation was committed as
`46cbdf4a592c609d2ba1ba08a5c438fb388890a4`. Run
`goal010-20260728T045355Z-46cbdf4` used a clean detached checkout of that
commit on `deep-server`, Python 3.14.5, NumPy 2.5.1, three worker processes,
and all four numerical-library thread limits set to one. The Git bundle,
lockfile, and exact 16-file Goal 009 input pack were verified before compute.

The first reduced smoke attempt correctly blocked because it paired the
three-rho smoke configuration with the full 601-rho production input pack.
Every other invariant passed. Before production, the intended internally
validated three-rho fixture was generated and the unchanged smoke then passed.
The production command used the untouched, checksum-authenticated 601-rho
Goal 009 pack. This was a smoke-fixture mismatch, not a scientific retry or a
source change; both the failed diagnostic and correction record are retained
in the returned run evidence.

The one authorized production command started at `2026-07-28T05:05:42Z`,
finished at `2026-07-28T07:32:20Z`, and exited zero after about 2 hours 26
minutes. It wrote and internally validated the exact 14-file scientific pack.
No second expansion, retuning, cell change, threshold change, or production
retry occurred.

## 2026-07-28: Scientific Result

The completed decision is:

```text
bounded_upper_expansion_resolves_primary_decision_limit
```

For the primary `cell-06`, the full, first-half, and second-half banks changed
as follows:

```text
bank         eta-upper contact     connected interior       class
full             152 -> 0              344 -> 479       design-limited -> recoverable
first_half       150 -> 0              347 -> 481       design-limited -> recoverable
second_half      156 -> 0              338 -> 478       design-limited -> recoverable
```

All three banks retained truth coverage at `479/500`. Their recomputed
476th-order-statistic cutoffs were respectively `80.44725329481041`,
`80.85234464173627`, and `81.16875882526983`; these equal the original
cutoffs because the appended domain never improved the corresponding profile
maximum. No validation support or descriptive MLE reached `eta = 2.5`.

The prespecified comparators agreed. Cell 07 changed from 48, 49, and 47
upper-face contacts to zero and from 449, 450, and 451 connected-interior
supports to 497, 499, and 498. Cell 08 changed from 14, 14, and 13 contacts to
zero and from 486, 486, and 485 connected-interior supports to 500, 500, and
498. Every expanded cell-bank row classified as recoverable.

### Observation And Inference

Observed: appending only `eta = 2.25, 2.5` removed all new upper-face contact,
restored the prespecified topology gate in the three high-eta truth cells,
preserved coverage and predictive guards, and left the numerical cutoffs
unchanged.

Inferred: within this frozen perfect-detection benchmark, Goal 009's high-eta
design limitation was caused by truncation at the artificial `eta = 2`
candidate ceiling rather than by a ridge that persisted to `eta = 2.5`.
This is a local bounded-domain diagnosis, not evidence of universal joint
identifiability.

The result remains conditional on one landscape, sampling design, calendar,
perfect detection, candidate grid, and a site-history simulated composite
likelihood that omits between-site process dependence. Cells 07-08 are
comparators rather than independent replications. The inability of low-eta
truth cells to exclude the accepted `eta = 0` uniform-resistance null is
untouched and remains a scientifically meaningful practical-identifiability
limit. Goal 009 remains `joint_cross_truth_design_limited`; it is not
retrospectively reclassified.

## 2026-07-28: Local Evidence Audit

The returned recursive SHA-256 manifest verified all 36 files. A standalone
standard-library audit, without importing Goal 010, then:

- reproduced all nine 476th-of-500 calibration cutoffs directly from 4,500
  calibration rows, and confirmed all 4,500 profile maxima and likelihood
  ratios were unchanged from Goal 009;
- recomputed likelihood ratios, rook-connected components, boundary faces,
  truth inclusion, Wilson intervals, normal-mean intervals, medians, cell
  classes, and the overall decision from all 4,500 validation rows;
- reconciled every original/expanded validation pair against the authenticated
  Goal 009 table;
- reconciled the 27-row baseline anatomy, nine cell-bank summaries, nine
  domain comparisons, and 59,499 representative-profile rows; and
- reproduced the primary-bank counts and
  `bounded_upper_expansion_resolves_primary_decision_limit`.

Both SVGs were rendered in Chrome and visually inspected. They are readable,
non-overlapping, and agree with the source tables.

An independent final reviewer separately verified the returned manifests,
primary counts, calibration cutoffs, coverage and precision gates, predictive
intervals, comparator consistency, and both figures. The verdict was
`ACCEPT`: the initial smoke failure was confined to its fixture mismatch, no
material provenance or scientific blocker remained, and no rerun or further
repair was justified before publication.
