# Goal 062 amended compute estimate: ten cells

11 October 2026 (Hobart). This updates the [original receipt-based estimate](compute-estimate.md)
for the approved [B100-A amendment](amendment-2026-10-11.md). It preserves all
historical measurements and their uncertainty. The four added cells require
no new reference-table family and no expansion of the 765-node grid.

## Count and elapsed-time changes

| Work | Original six cells | Amended ten cells |
| --- | ---: | ---: |
| Evaluation histories | 3,000 | **5,000** |
| Main model fits | 12,000 | **20,000** |
| Observed screen-node scores | 2,295,000 | **3,825,000** |
| Held-out candidate totals | 12,000 | **20,000** |
| Evaluation generator replay | 3,000 | **5,000**, including 2,000 fresh-field B100-A histories |
| Evaluation stage seeds | 15,000 | **27,000** |
| Prespecified diagnostic histories | 30 | **50** |
| Profile points | 13,290 | **22,150** |
| Lower-bound lattice points | 40,500 | **67,500** |
| New effect-reference histories | 465,534 | **465,534**, unchanged |
| Scheduled new-reference generator spot replays | 1,398 | **1,398**, unchanged |

Retain **36–40 hours** for completion/audit of 466 effect tables and custody/I/O.
The underlying receipt extrapolation remains 22.96 hours before margin and
34.44 hours after the explicit 1.5 factor. Reference histories are shared
across all ten cells. There is no multiplier of ten on that cost.

Scaling the previous 6–10-hour evaluation/diagnostic/reporting allowance by
5,000/3,000 gives **10–16.67 hours**, rounded to **10–17 hours**. This adds
about 4–7 hours and produces the amended **46–57-hour total**. It is a workload
allowance, not measured B100-A throughput. Fresh field generation, possible
optimizer difficulty under misspecification and extra anomaly diagnosis can
change the cost. The existing conservative profile/audit workload estimate
scales from 5.23 to about **8.72 hours** for 50 diagnostic cases; main-fit-only
ideal scaling increases from 1.11 to about **1.85 hours** at 51 workers.
The diagnostic term partly double-counts main fits, as before. These are
components of the 10–17-hour allowance, not extra additions to it.

The extra field arrays are small relative to the reference databases: storing
one float64 value per map cell for 2,000 fields is 96,768,000 bytes before
metadata/compression. The fully materialized 5,000×765 node-p matrix would
be 30.6 MB, while the cached 765×999 reference-statistic matrix remains
about 6.1 MB. Use bounded batches and the same qualified scalar-rank semantics.
The existing 15.471 GB estimate for the completed SQLite reference panel is
unchanged. Retain the **50 GiB free-scratch requirement**, including verified
return copies, evaluation/diagnostic payloads, source/bank and checkpoint
headroom; qualify actual payload and peak-memory use before production.

## Approved envelope and measurement gate

The allocation remains deep-server, up to **51 workers**, one numerical-library
thread each, **64 GiB aggregate RSS** and a **72-hour hard wall ceiling**.
The amended 46–57-hour range corresponds to 2,346–2,907 allocated slot-hours;
72 hours remains 3,672 slot-hours. Slot-hours are not measured CPU consumption.
No cloud purchase or host-configuration change is authorized or proposed.

The first read-only capacity check on 11 October found the expected deep-server
with 64 logical CPUs, about 121.2 GB available RAM, 4.50 TB free on /data and
three busy single-CPU R processes. This is a point-in-time observation, not a
reservation. Recheck capacity immediately before qualification and launch;
preserve unrelated work. The locked Python/NumPy/SciPy runtime and source
compatibility checks from the original estimate still apply.

Benchmark generation, main fits, observed screens, cached ranks, held-out and
direct audits, profiles/lattices and checkpoint I/O for both generating
families using mechanical root 987654321 or existing public fixtures. Do not
preview production root 2026101101. The benchmark must support the chosen
worker count and memory use and a projected full campaign within 72 hours.
If it does not, preserve the measurements and return for a resource decision;
do not silently reduce histories, references, diagnostics or audit coverage.

After amendment review and implementation qualification, the approval covers
the bounded run and audit without another launch question. Developer/reviewer
elapsed time is outside this compute estimate. A wall or memory stop leaves
unfinished work pending and preserves addresses and completed results.
