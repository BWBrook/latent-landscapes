# Goal 062 compute estimate

11 October 2026 (Hobart). **Planning estimate from saved receipts, not a new
benchmark or launch authorization.** The [registration](registration-2026-10-11.md)
defines six cells and 500 independent evaluation histories per cell.

## Recommended envelope

Budget **42–50 hours of elapsed compute on deep-server at up to 51 workers**,
including completion/audit of the full calibration grid and evaluation. Use
a **72-hour checkpointing ceiling**, 64 GiB aggregate RSS and at least 50 GiB
free scratch. The time range is an engineering allowance, not a statistical
prediction interval or guaranteed upper bound. Availability has not been
probed and no job has been dispatched.

The calibration estimate is substantially better grounded than the evaluation
estimate. A new panel adapter still needs implementation and mechanical
qualification; developer/reviewer elapsed time is separate from compute time.
An approved launch would first benchmark that adapter on mechanical or existing
public fixtures, without previewing the evaluation streams. If the updated
estimate exceeds the envelope, stop before production and report it.

## Count the work once

| Work | Already available | New work in the registered proposal |
| --- | ---: | ---: |
| Fixed map, sampling split, exposure and K131072 arrival bank | Qualified Goal 060 package | None; verify/reuse |
| Pre-only screening references | 765×99 = 75,735, independently audited | None; verify/reuse |
| Full null-effect references | 299×999 = 298,701, independently audited | **466×999 = 465,534** |
| Effect-reference tables after completion | 299 | 765 total; 999 rows each |
| Fresh evaluation histories | None | **3,000**, all 160 sites generated |
| Main model fits | None | **12,000**; four per history |
| Observed pre-only score surfaces | None | 3,000×765 = 2,295,000 node scores |
| Held-out candidate scores | None | 12,000 totals with site/cluster contributions |
| Prespecified profile/lattice subset | None | 30 histories: 13,290 profile + 40,500 lattice points |
| Independent evaluation generator replay | None | All 3,000 histories |
| New effect generator spot replay | None | 466×3 = 1,398, plus any anomalous rows |

Reference tables are shared across cells and histories. The cost is not
465,534 references per cell, nor a new 999-reference ensemble per evaluation
history. Reference rows do not count toward the 500 evaluation histories.

Completing all 466 nodes before evaluation is the registered simplification,
not a mathematical necessity. A prospectively chosen lazy strategy could
freeze all addresses, calculate the complete evaluation-screen union, then
materialize only missing union nodes before effect scoring. It must never
drop required nodes or be selected after inspecting effect results. The
registered proposal pays for a complete fixed panel; no claim is made that
every node would otherwise be required. Switching to the lazy route requires
a revised prospective registration and independent review before any
production draw. It is not a runtime cost-saving option under this proposal.

## Measured reference cost and extrapolation

The [Goal 061 execution record](../061-blinded-capstone-training/execution.md)
and its original `run-001.log` separate the stages:

| Historical stage | Observed wall time | Interpretation |
| --- | ---: | --- |
| 299-node effect generation/fitting | 48,331.954 s = 13.4255 h | 51-worker production stage |
| Independent effect audit | 4,708.214 s = 1.3078 h | 299 nodes; same 51-worker allocation |
| Full original run | 55,849.606 s = 15.5138 h | Also includes four-case fitting, diagnostics, screening and rank reconstruction |
| Full screening production | 93.995 s | All 765×99 references in that run |
| Screening node audit | 31.706 s | All 765 nodes |

Do not describe 15.5 hours as the effect-reference producer cost alone. The
incremental same-throughput calculation for n new nodes is

`reference_hours(n) = (48,331.954 + 4,708.214) × n / (299 × 3,600)`.

| New nodes | New reference histories | Production h | Audit h | Sum h | Sum ×1.5 h | New DB GB |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 99,900 | 4.49 | .44 | 4.93 | 7.39 | 2.02 |
| 250 | 249,750 | 11.23 | 1.09 | 12.32 | 18.48 | 5.06 |
| **466 (registered proposal)** | **465,534** | **20.92** | **2.04** | **22.96** | **34.44** | **9.42** |

The smaller rows illustrate scaling if a different materialization strategy
is approved; they are not predictions of retained-union size. Reserve **36–40
hours for reference completion, audit and custody/I/O overhead**. The 1.5
factor and rounding are explicit planning margins, not measured speedups or
confidence limits.

The 299 completed node receipts contain overlapping worker intervals: mean
7,764 s/node, median 7,550, p90 10,085, range 4,985–11,013; their sum is
2,321,502 worker-seconds. They must not be summed as campaign wall time. The
remaining 466 nodes are not a random sample of the completed nodes, and
extreme nuisance settings can have different optimization costs. A rough
stress calculation assigning every new node the largest observed node cost,
allowing one terminal scheduling batch and adding the scaled audit, gives
about **33.05 hours**. This is a scenario, not a worst-case bound on unseen
nodes. The 72-hour campaign ceiling protects against underestimation without
changing reference counts or scientific failure rules.

## Evaluation, diagnostics and reporting allowance

Reserve a further **6–10 hours**, with lower confidence than the reference
estimate. Its basis is a workload model, not multiplication of one pilot's
reference cost by 3,000.

- The four Goal 061 observed histories' four-model elapsed totals were
  47.169, 66.507, 69.127 and 88.920 seconds. Scaling their mean to 3,000
  histories and 51 equally effective workers gives **1.11 hours** for main
  fitting alone. This assumes effective process-level parallelism and ignores
  startup, contention and changed positive-effect geometry. Public Goal 060
  full-bank fixtures took 6.96–10.67 seconds per four-model fit, showing that
  context and scheduling materially affect these timings. Use the slower
  observed-case evidence for planning, then benchmark the new wrapper.
- The historical four-case fit/profile/lattice stage took 1,138.701 seconds
  with at most four concurrent case threads. Its four subsequent direct-bank
  case audits took about 1,373 seconds serially. A deliberately conservative
  scaling of that complete workload to 30 diagnostic histories gives about
  **5.23 hours**. It double-counts the subset's main fits relative to the
  preceding allowance. It is not a benchmark for the new h=5 profiles; faster
  diagnostic parallelism may reduce it, but is not assumed for the budget.
- The balance covers generation/replay of all evaluation histories, observed
  screening, independent main-score and held-out audits, summary bootstraps,
  data transfer and report production. These components have no clean
  persisted 3,000-history benchmark. Additional anomaly diagnosis uses the
  campaign's remaining wall allowance and stops pending if it exceeds it.

The old `decide` stage took 107.225 seconds for four cases while performing
four-case-oriented loading/verification. Repeating that entire command per
four histories would cost about **22.34 hours** and is not the planned adapter.
Validate and cache reference statistics once, then reconstruct all ranks in
bounded batches. At most 765×999 float64 reference statistics require about
6.1 MB; even the full 3,000×765 node-p matrix is about 18.4 MB. Exact inclusive
rank arithmetic, tie tolerance and failure propagation must match the scalar
implementation. This efficiency is an implementation requirement to verify,
not a promised measured throughput.

The initial 6–10-hour evaluation allowance is therefore plausible but uncertain.
Qualification must measure main fits, the 765-node observed screen, batched
ranks, held-out/direct audits and diagnostic profiles separately. Failing the
72-hour projected total or memory envelope returns for a resource decision;
it never permits smaller reference counts, fewer than 500 histories or altered
scientific endpoints.

## Storage, memory and resource choice

The 299 existing SQLite reference databases occupy **6,046,998,528 bytes**:
about 20.224 MB/node. Proportional estimates are **9.424 GB additional** and
**15.471 GB total** for 765 tables (14.409 GiB total). These are decimal GB;
storage scaling is approximate because compressed payloads vary by node.
Allow at least **50 GiB free scratch** for the complete reference set, a
verified return copy, evaluation data, diagnostics, bank/source files and
checkpoint/WAL headroom. Transfer only required durable evidence; do not
duplicate the entire archive on every worker.

Goal 061's measured peak aggregate RSS was **23.21 GiB** at 51 workers, below
its 64 GiB cap. New observed-fit/profile workers can have different memory
requirements. Retain a 64 GiB aggregate cap and one numerical-library thread
per worker; qualify the new process layout before selecting up to 51 workers.
If fewer workers are available, reference time scales roughly as 51/W as a
first approximation, with an additional scheduling tail. That is not a linear
speedup guarantee.

The proposed target is the existing deep-server, following the previously
qualified Linux path under `/data/codex/scratch/` and returning evidence to
this repository. No cloud purchase is proposed; electricity and opportunity
cost are not priced here. A 42–50-hour reservation at 51 worker slots is about
2,142–2,550 slot-hours; the 72-hour ceiling is 3,672 slot-hours, not measured
CPU consumption. No live host-capacity or filesystem-space claim is made.

## Reuse identities and launch checks

The compatibility bridge is the original Goal 061 manifest
`artifacts/goal061_execution/qualification-repair3/source-manifest.json`,
SHA-256 `5879fbdaf7b3880151358319a7b7c7c0837463b06ba06f1a34fb80a3fbc2e36a`.
All **258 source/script/test files** named there match the current files at
this planning check. A new adapter must preserve scientific kernels and retain
both original and new source identities.

| Fixed input | SHA-256 |
| --- | --- |
| Map/design NPZ | `f5c590d1b600c74a686a77215488844e78e19e30fdc59fe34ab44f39acebdfc2` |
| Exposure NPZ | `b74004fc9ecf03499cfdc9ecca4919b0e17987eba405709f4e3f95f9bc9c0831` |
| Arrival array | `168bd6ddd2aca5a0a0bbae27773a6c3b89e011e23713a6124632787b89b738dc` |
| Confirmatory address contract | `106fe8a9c8a0b2f03a0f8be6dec21bd01a0e9d20926e08bbbddd047a92fbdaa0` |
| Canonical nuisance-node list | `20f2de54cb8a39901b733e06def5cf0a91d9c2b1abf32cb4cd43a8018a3b8fd3` |
| Locked Linux runtime JSON | `77153eb0a977749e4ba95d9cae33c1f6d31457bdc2cc2d91d2358cede7ec88e1` |

The qualified public package is indexed by
`artifacts/goal060_execution/audit-repair/public-ready.json`; the completed
screen/effect tables and their audits are indexed by
`artifacts/goal061_execution/qualification-repair3/analysis/computation-complete.json`.
Planning used the existing compact manifests/receipts; it did not rehash all
6 GB of databases. Before reuse, verify the actual payload hashes, counts,
addresses, valid/invalid status and original audits, together with the map,
bank and runtime. A missing or changed artifact is a custody problem to resolve,
not permission to redraw or silently calibrate with a different algorithm.

Supporting extraction notes are in
`artifacts/paper1_six_cell_design_20261011/`. The independent review must check
the count arithmetic, cost assumptions, full-grid choice and separation of
scientific outcomes from numerical/resource stopping rules before launch.
