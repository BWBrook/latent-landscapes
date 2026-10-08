# Goal 057 execution record

4 October 2026 (Hobart). The approved public pilot launched at **14:59:04
AEDT / 03:59:04 UTC**, under the [registration](registration-2026-10-04.md).

## Preparation and qualification

Use the isolated run root
`deep-server-ts:/data/codex/scratch/goal057-screening-retention-20261004`.
At the resource check the host had 64 logical CPUs and about 89 GiB available
memory, with another project using twenty workers. This eight-worker pilot
fits the remaining single-host capacity; no other workload or allocation was
changed. The source snapshot uses the existing lockfile with Python 3.14.5,
NumPy 2.5.1 and SciPy 1.18.0.

The [source manifest](../../../artifacts/goal057_execution/source-manifest.json)
binds 238 source/input files, the two frozen seed files, the supervisor and
the exact qualify/run commands. Its SHA256 is
`834afa9fbd0408eef63abf7b10912965d465a7cf835baba6b983250d55695cf4`.
The source archive SHA256 is
`baad0063352249c78251b2f7e73969abdc0f12616d493c7c4f77c2d3357dc746`.
Predecessor bindings preserve 156 Goal 056 evidence files and 44 pre-existing
scientific source modules. Earlier results and the frozen likelihood, fitter
and screening statistic were unchanged.

Linux [158 focused tests](../../../artifacts/goal057_execution/tests.log),
[Ruff](../../../artifacts/goal057_execution/ruff.log) and
[mypy](../../../artifacts/goal057_execution/mypy.log) passed. Mechanical
qualification found maximum batched-versus-individual discrepancy
4.5475e-13 nats. The numerical check itself took .0164 s; the complete
qualification wrapper took 26.03 s including full seed-ledger verification,
with sampled peak RSS .138 GiB and exit 0. The independent analytic likelihood
agreed with frozen Goal 056 fixtures within 1.3e-12 nats.

The supervisor's separate [mechanical process-group test](../../../artifacts/goal057_execution/wrapper-smoke-check.json)
stopped both a sleeping parent and child at the short test limit, with no
surviving group members. The scientific run uses a 3,600-second ceiling,
16 GiB aggregate child-process-group RSS, at most eight workers and one
numerical-library thread per worker. RSS is sampled once per second.

The [implementation receipt](../../../artifacts/goal057_execution/implementation-checks.json)
and registration disclose an early development preview: 99 unique histories
at node 0 and a uniform prefix from node 17/reference 23/loss. Repetition
counts are the executor's account because development logs were not retained.
Tests were corrected to a separate mechanical root. All production addresses,
reference counts, methods and thresholds remained unchanged. No wholly
pre-preview registration claim is made.

## Campaign and verification

The launcher started supervisor PID 267457 at 03:59:04 UTC. The one-shot
attempt generates the complete node-addressed reference table, scores the
sixteen frozen fixtures and fits/audits the 792 reused histories. Partial
node and fit records are written as work completes. No further registered
simulation or full effect table is authorized after this attempt without
diagnosis and the applicable scientific decision.

The run finished at **15:05:41 AEDT / 04:05:41 UTC**, exit 0, after 397.280 s
under the 3,600-second ceiling. The sampled peak child-process-group RSS was
1,058,578,432 bytes (.9859 GiB); the final process-group check found no remaining
members. The [attempt receipt](../../../artifacts/goal057_execution/run-attempt.json)
and [runner completion](../../../artifacts/goal057_execution/run/completed.json)
record all 360,855 histories, 3,645 nodes and 792 diagnostic fits. The runner's
timed body took 371.026 s; the supervisor also covers startup and seed-ledger
verification. No resource or numerical stop occurred and the campaign was not
restarted.

| Measured component | Seconds | Interpretation |
| --- | ---: | --- |
| Reference generation | 181.940 | Sum of node-worker wall intervals |
| Reference preparation | 66.390 | Sum of node-worker wall intervals |
| Reference point scoring | 344.699 | Sum of node-worker wall intervals |
| Reference assignment | .043 | Parent assignment work |
| Node checkpoint serialization | 4.508 | Parent checkpoint writes |
| Diagnostic count serialization | .682 | Persisting the 792 histories |
| Diagnostic fitting and checks | 242.458 | Serial diagnostic phase wall time |
| Independent diagnostic score checks | 1.116 | Included in diagnostic phase |
| Sixteen fixture surfaces | 47.273 | Observed surface scoring wall time |
| Final screen output serialization | 1.558 | Tables/arrays/report writes |

Worker sums overlap in elapsed time and are not CPU measurements. The
diagnostic phase includes fitting, checks and its output handling; do not add
the independent-check row to it a second time. The exact reference score count
is 2,292,543 scalar-equivalent evaluations (23,157 node/neighbour calls each
batched across 99 histories), plus 58,320 fixture point evaluations, excluding
optimizer probes and independent audits.

The returned run payload contains 3,657 files and 18,043,876 bytes. The
[return manifest](../../../artifacts/goal057_execution/return-manifest.json)
also binds five launcher/log/source receipts, for 3,662 verified files total,
and records that source, frozen inputs and
supervisor remained unchanged on the target. Its archive contains 10,895,566
bytes with SHA256
`c466e34fbd288b8b4c6f771b20664a9e4bb351d816fdd8ceb73e4eea1709f5f6`.
Every returned file was verified locally. The original source snapshot and all
Goal 056 evidence remain intact.

## Independent reconstruction

The [independent review](independent-review.md) gives a GO for this bounded
descriptive result. It reconstructs all sixteen surfaces (58,320 scores,
maximum discrepancy 2.61e-12 nats), all local contrasts (maximum 7.28e-12),
exact q values/candidate masks, all 1,820 unions, all 792 reused-reference
contrasts and true/fitted scores, and 21 direct PCG64 generator replays.
The complete 1,082,565-row seed ledger is exact. Replays are audit checks of
assigned histories, not additional references. All 792 fits converged; the
smallest fitted-minus-true score gap is .01408 nats, and no numerical failure
or independent-score discrepancy exceeded its registered tolerance.

The final [audit receipt](../../../artifacts/goal057_execution/independent-audit/result-v3/report.json)
binds the unchanged raw audit to the accepted synthesis. Its SHA256 is
`32891bca029707bf1bb0a35a8289a8b86e9ba6d722d7344777280e633b52202b`.
All corrected 999-reference costs and nodewise/pooled nuisance summaries were
rebuilt independently. The original raw audit and intermediate rebind receipt
are preserved.

## Postprocessing repairs and accepted outputs

The first synthesis incorrectly multiplied future effect costs by 99 while
labelling the table as 999 references/node. The parent caught the discrepancy
before reporting those costs. The original `synthesis/` directory remains
unaltered. Separating the 99 screening and 999 effect constants produced
`synthesis-v2/`; all projection cells were independently checked. This was an
analysis-only repair with no change to the campaign.

Visual inspection then found a transposed surface heatmap with uniform mu
spacing, although the raw surfaces and contour/retention overlays were correct.
The plot now uses the correctly oriented beta-by-mu mesh and irregular mu
spacing; caption margins and labels were also repaired. Accepted outputs are
in [synthesis-v3](../../../artifacts/goal057_execution/synthesis-v3/manifest.json).
Its numerical report is exactly identical to v2. The parent inspected the three
figure families; PDF page counts are 16, 1 and 1. The v2 audit rebind stopped
because the live plotting script had already advanced, as expected; v3 passed.

| Synthesis version | Script SHA256 |
| --- | --- |
| Frozen original | `900a075564d5bc9cb348d540294a2306a65b21ec2ef1b2fa464c3c1675608e71` |
| Cost repair | `f2800cf43a3f27b2bdf624ad353762c56c40a9a91fee4ca0eaa90364e5249c21` |
| Accepted plot and cost repair | `54d3299da7833cae687cacbb72726059e876383f0105f4ef1fb191b81a34acad` |

The original synthesis script remains in the immutable source archive.
Post-run changes are confined to this reporting script and completion
documentation; the production modules, tests, registration, seeds, data and
fits remain unchanged. Ruff, Python compilation and focused arithmetic/plot
checks passed after the repairs.

The supplementary arithmetic background-error summary was added after seeing
the registered log-error results. Its [script](../../../artifacts/goal057_execution/supplementary-arithmetic-mu.py)
and [output](../../../artifacts/goal057_execution/supplementary-arithmetic-mu.json)
identify it as post-run, use only the same 792 fits and passed independent
reconstruction. It does not replace the primary diagnostic.

The [completion check](../../../artifacts/goal057_execution/completed-check.json)
binds the original archives, all returned outputs, accepted synthesis, audit,
supplement and predecessor files. No full effect references, sealed histories
or new-map simulations were generated; no commit, push or publication occurred.
