# Goal 058 execution record

4 October 2026, Hobart. **Complete; one registered attempt, independently checked.**

The approved scope is the [registration](registration-2026-10-04.md): 999 full
null histories at each of four fixed nodes, followed by independent direct-bank
checks. The 765-node support is frozen; this run does not calibrate its screening
statistic or generate the other 761 effect-reference tables.

## Frozen inputs and implementation

The seed ledger contains 3,996 rows and five stage seeds per row, with root
2026100402 and namespace 58. Its array SHA-256 is
`82cc2a026e11439e36614f4c5fb8403246f30ad62bbed8c7e9d8c55b0f061011`.
The external freeze JSON hash is
`f1248dc14fed526fe05ac3a9e0fb5e1d24f111950635d8d0260b9291bbe36c6e`.
These were written before any registered reference history was generated.

The final source package contains 256 files, including both scorers, tests,
registration, methods review, lockfile and the public fixtures used in checks.
The source-manifest SHA-256 is
`0fa472c470b7246ce5ef14eaf84e41bd04241f7dd9f892bedf875914bf8b836e`;
the 44,343,056-byte source archive hash is
`08a592bee1cb211cfeaa2dd078574be786ce4defb888d3ae8ec85fc355d387f8`.
The manifest also binds the process supervisor, stage driver and frozen inputs.

Production uses the existing adjusted-null and adjusted-free fitting primitive
without editing it. The wrapper records separate optimizer statuses, all starts
and objective evaluations, truth/null/free scores, raw and clamped statistics,
generation/fitting/write timings and raw observations plus latent quantities.
A table loader checks the complete union cap before opening files; missing or
invalid nodes propagate through the existing casewise combiner. An unavailable
node does not suppress an unrelated case.

## Preparation and qualification

Independent methods/code review cleared the frozen implementation for target
qualification. Local checks passed 199 likelihood, fitting and pipeline tests
and 10 independent-audit tests. Linux passed all **209 tests**, Ruff and strict
mypy. The native tests exercise shared tables, inclusive rank arithmetic,
missing/invalid-node abstention and an over-cap union that opens no table.

The first packaging attempt omitted the open Goal 051 archive needed by one
historical regression test: 208 tests passed and that fixture check failed.
The archive with its original SHA-256 was added; no scientific source or seed
changed. The original package and failed test log remain in `package-v1/`.
This happened before target qualification or any registered draw.

The Linux supervisor was tested with a parent and child process. Its two-second
test cap terminated both, recorded exit -15 and left no group members. Actual
qualification has a 900-second cap. The registered run and its independent
audit share a 7,200-second ceiling, at most sixteen production/four audit workers
and 48 GiB aggregate process-group RSS. All numerical libraries use one thread.

Target: `deep-server-ts`, isolated directory
`/data/codex/scratch/goal058-effect-reference-20261004`.
The fresh locked environment uses Python 3.14.5, NumPy 2.5.1 and SciPy 1.18.0.
The qualified arrival bank is read from its existing Goal 045 cache; it is not
regenerated or used to replace the full correlated-spread history generator.

Qualification started at **17:36:10 AEDT**. It uses root 987654321 exclusively,
compares the adjusted pair with the existing four-model route at all four
nodes, runs eight histories through two workers and serialization, then audits
those saved histories with the independent direct-bank scorer. Qualification
finished at 17:39:08 AEDT in 177.159 s, peak 2.092 GiB, exit 0, with no remaining
process-group members. All eight pairs were valid; all independent checks
passed. Maximum absolute differences were 2.274e-13 log-likelihood units and
4.547e-13 in the effect statistic. The bank identity matched Goal 056 exactly.

## Registered run and independent audit

The single registered attempt began at **17:41:56 AEDT** with sixteen workers.
Production completed at **18:02:35 AEDT**, after 1,239.246 s. All 3,996 assigned
histories were retained, with 999 valid pairs at every node. Both returned fits
were converged for every history; the truth/null/free finite-score and nesting
checks all passed. There was no redraw, restart or post-run optimization.
This does not assert that every individual multistart attempt converged or
that a global optimum was proved.

The four-worker independent audit finished at **18:11:34 AEDT**, taking
538.733 s including its launch overhead. It checked all 3,996 histories at
the true, fitted-null and fitted-free points using the independent direct-bank
kernel. Maximum differences were **1.137e-12** log-likelihood units and
**2.728e-12** effect-statistic units. All seed/address/latent checks, 8,003
manifest-listed file hashes and four complete node tables passed. All twelve
designated generator replays matched bitwise; these establish deterministic
replay of the same generator, not independent validation of spread biology.

Total supervised elapsed time was **1,778.282 s (29.64 minutes)**. The sampled
aggregate process-group peak was **8,011,198,464 bytes (7.461 GiB)**, below the
48 GiB ceiling. The supervisor exited 0 with no stop reason and no remaining
group members. Qualification was separate from the registered two-hour budget.

Returned production contains **8,004 files / 66,866,422 bytes**, including the
manifest itself. Its compressed return archive is 25,961,641 bytes, SHA-256
`9697c179624994344bbbc5a5ca0163754dbb5c128391f9f195fcf16282309345`.
All 8,003 payload hashes were checked after transfer. Final audit rows, stage
logs, resource receipts and the source archive are also retained locally.

The [synthesis](synthesis.md) gives per-node timings, statistic distributions,
failure uncertainty and qualified cost arithmetic. The
[independent review](independent-review.md) and
[completion check](../../../artifacts/goal058_execution/completed-check.json)
bind the accepted closeout. No Goal 058 process remains active.

## Evidence locations

All local execution material is under `artifacts/goal058_execution/`: frozen
seeds, source package/manifest, supervisor test, target test logs, qualification,
run and audit receipts, followed by returned raw histories and synthesis.
The predecessor binding recorded 181 earlier source files and 3,909 Goal 056/057
evidence/document files; all matched before this run and again at closeout.
No prior scientific source, Goal 056/057 evidence, private key or sealed history
was changed. No commit, push or publication occurred.
