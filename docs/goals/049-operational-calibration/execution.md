# Goal 049 execution record

20 September 2026. The [registration](registration-2026-09-20.md) and
[implementation review](implementation-review.md) govern this run.

## Completed preparation and archive work

- Fable's critique incorporated; Astra replies on thread 44, messages 330, 335 and 339.
- [Interpretation amendments](interpretation-amendments.md) completed, preserving
  historical results and the four Arc 3 numerical failures.
- [Archive diagnostic](archive-diagnostic.md) completed with 2,000 paired
  bootstrap draws and verified profile identities; no new process histories.
- Focused implementation/synthesis tests, lint and strict type checks passed.
  Review repaired resume identity, provenance coverage, measured-control
  failure handling and the production timing gate.
- Bootstrap timing fixture on deep-server: eight full-shape draws took 1.030 s,
  projecting 257.45 s for 2,000. Reserve 900 s for synthesis, verification,
  tables and figures. This is a synthetic timing fixture, not a scientific run.

## Compute location and boundaries

Host: `deep-server-ts` (64 logical CPUs; about 24 busy at preflight). Run root:
`/data/codex/scratch/goal049-known-nuisance-20260920/`.
The isolated `source/` copy has a frozen uv environment. The original bank
cache is read-only; its full and 65,536-prefix hashes match Goal 045.
Local preflight evidence is in `artifacts/goal049_execution/`.

`run-bounded.sh` limits the threaded Python process to 32 GiB address space,
sets numerical libraries to one thread, requests eight scoring workers and
uses a terminating timeout. No source in an older experiment is changed.
The source/registration/environment-lock hashes bind timing to production.

Current phase: **verified completion**, with the null calibration-quality flag
retained in the [synthesis](synthesis.md). The following timing/projection
record documents the prospective launch decision. The timing trial finished
successfully in 459.81 s (wrapper wall time 461.41 s), with peak RSS
1,064,992 KiB (about 1.02 GiB). All four measured score/set controls and six
seed checks passed. The canaries covered the full grid and all four variants.

Measured integration took 421.75 s; two paired full-grid calibration replicates
took 28.95 s and two paired evaluation replicates took 1.51 s. The conservative
production projection is 19,440.64 s (5.40 h). Including timing, a conservative
3,600-s allowance for prior work and a 900-s analysis reserve gives
24,400.45 s (6.78 h), below the 24-hour ceiling. The bound evidence is
`artifacts/goal049_execution/production-budget.json`; the production CLI
verified its matching timing/source/registration identities before launch.

## Completed production and synthesis

Production wrapper PID at launch was 181110. Production started at
2026-09-20 01:21:32 UTC and finished at 07:33:28 UTC with exit status zero.
Wrapper wall time was 6:11:55, with peak RSS 1,666,064 KiB (1.59 GiB).
The measured workload exceeded the 5.40-hour projection but remained well
within the registered cap. Scientific scoring took 22,314.41 s in total:
20,792.42 s calibration, 1,084.23 s evaluation and 416.16 s integration.

After source/input/score identity verification, the frozen synthesis ran once
under `run-synthesis.sh`, with a 900-second terminating timeout, 32-GiB address
space limit and single-threaded numerical libraries. It finished at
2026-09-20 07:44:39 UTC with exit status zero. Exactly 2,000 bootstrap draws
used seed 2026092003; resampling took 234.86 s and the complete wrapper took
246.87 s. Peak RSS was 611,268 KiB (0.58 GiB). Including the prior-work
allowance, timing and both wrappers gives 26,623.28 s (7.40 h), before a few
minutes of local reporting and verification, within 24 h.

Full production profiles were retrieved into
`artifacts/goal049_execution/production/output/`; synthesis is in the sibling
`synthesis/` directory. The [completion check](../../../artifacts/goal049_execution/completed-check.json)
records verification at 07:53 UTC: all 70 bound source/registration files,
14 frozen score/identity files and 13 synthesis outputs match their receipts.
The original remote bank hash matches, all four measured identities and six
seed controls pass, and no scoring process remains. The production summary
SHA256 is `fb32dd32f3a7d3359b7b04738a54d1916d1e366c8c1d5e04601be2af99fd22a6`.
Both local and remote copies retain zero exit receipts and completion times.

The independent scientific review required preserving the realised null size
of 7.4%, whose calibration-aware interval is 5.6–9.7%. The generator/score
inspection found no mismatch; the calibration table remains unchanged.
A presentation correction from the saved bootstrap draws removed only
machine-roundoff rate excursions and constant-series SEs; it generated no
new draws and changed no point estimate or tolerance decision. Corrected
report tables and the inspected figure are in `review/`, with their own
receipts; raw outputs, source and original receipts remain unchanged.

The Goal 049 completion heartbeat has been removed after verified closure.
Astra posted the substantive closeout as message 358 on Correspondence thread
44. Goals 045–048 heartbeats remain paused. No campaign is running or queued by
this tranche. The next task is the Arc 4 design discussion, not an automatic
simulation launch. The four original Arc 3 numerical failures remain failures.

## Commands and durable evidence

The scientific runner is `scripts/run_known_nuisance_calibration.py`; production
requires `--budget-receipt`. The synthesis runner verifies all frozen score
hashes before joining the evaluation truth sidecar. It reports pointwise
quantile bands, conditional binomial intervals and separately paired
calibration-aware uncertainty; the three are not interchangeable.

The bootstrap shares replicate resamples across truths only because the
campaign receipt certifies the shared-random-number construction. Between-bank
membership changes are retained individually, so aggregate stability cannot
hide compensating changes. Held-out prediction is context from the same frozen
fits for every set construction, not a claimed gain from calibration.

No commit, push, publication, alternative-model selection, or second landscape
campaign is included in this tranche.
