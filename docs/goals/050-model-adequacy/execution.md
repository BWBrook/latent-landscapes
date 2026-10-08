# Goal 050 execution record

20 September 2026. **Completed; production and synthesis verified.**
Barry's Codex approval resolves the previous scope decision. The
[registration](registration-2026-09-20.md) fixes all scientific choices before
fresh histories or recovered detector scores are examined. SHA256:
`3ca7648c8cb55f439ee2ad3dbcff5a9f8d34b30f03631621c848fe26a3f2d037`.
Astra posted the approved scope on Correspondence thread 44 as message 393.

## Scope and provenance

Remote host: `deep-server-ts`; run root:
`/data/codex/scratch/goal050-model-adequacy-20260920`.
Only this run's new files may be changed remotely. Original Goal 049 profiles,
source and calibration table are read-only inputs at
`/data/codex/scratch/goal049-known-nuisance-20260920`.
The original Goal 045 nested bank remains read-only at
`/data/codex/scratch/goal045-full-bank-reference128-20260907-e8c08f1/bank_cache`.

Preflight at 10:19 UTC verified the completed Goal 049 exit receipts, all 14
frozen score/identity files, 70 source/registration files and original bank hash.
No Goal 050 process or earlier launch receipt existed. Deep-server had 64 logical
CPUs, load about 14, approximately 85 GiB available RAM, no swap use and 4.4 TiB
available on `/data`. The eight-worker/32-GiB job can coexist with the existing
workloads. Evidence: `artifacts/goal050_execution/preflight.json`.
The existing frozen environment uses Python 3.14.5; the new source copy will have
its own uv environment built from the unchanged project lock.

## Execution controls

The complete computation budget is 43,200 elapsed seconds: conservative 1,800-s
preparation allowance, measured timing, production and a 3,600-s synthesis/
verification reserve. Worker count remains at most eight and numerical-library
thread counts one. A bound wrapper enforces memory and terminating timeout;
explicit start/end/exit receipts and logs are retained. Timing uses exactly the
first two registered replicate blocks in each phase; it is not a scientific
pilot or a source of extra independent histories.

Before production, require a successful source/input-bound timing receipt,
all replay controls, and a conservative complete-workload projection within
budget. Hash changes invalidate qualification. Production must not be launched
by an unreviewed placeholder command, and a running process must never be
restarted or duplicated.

## Current work and stopping point

Implementation is split between the replay/fresh-block runner and the paired
synthesis, with independent review of their scientific and provenance contracts.
The registration review supports the construction and resampling design; it
clarified that small p rejects assumed-model adequacy. All future statuses and
launch identities will be appended here as they become observed evidence.

The final-source full-shape synthetic bootstrap fixture on deep-server took
0.316 s for four draws, projecting 79.0 s for 1,000. This uses synthetic arrays,
not experimental histories, and fits inside the 3,600-s analysis reserve.
The synthesis passed six focused tests, scoped Ruff, strict mypy and independent
scientific review. The final independent implementation review returned GO for timing; 26 integrated
Goal 049/050 tests, scoped Ruff, strict mypy and diff checks passed.

Timing launched at **2026-09-20 10:40:15 UTC** (20:40:15 Hobart), wrapper PID
212260, under the 1,800-s terminating timeout. Its exact receipts and log are
`timing/{started_at.txt,wrapper.pid,budget_seconds.txt,run.log,exit.status,finished_at.txt}`
under the remote run root. At that timing launch, production had not launched. All 73 bound local and
remote source/registration hashes matched before launch; the local manifest is
`artifacts/goal050_execution/launch-source-sha256.json`. Reviewed campaign SHA256
is `8423e5c0d43e4595bf652f63d0cecd4149e8c2ccedf183f836198c501def7f27`;
synthesis SHA256 is
`87821696eba34f2221b9035ad8a1a1ff31ed6567767d72f85afbd645be374339`.
The [independent review](implementation-review.md) records the pre-evidence
repairs and remaining result-review requirement. No alternative-model campaign,
commit, push or publication is included. Completion means verified results and
a costed next-screen proposal, with limitations retained, not automatic
acceptance of the detector for unknown nuisances or field use.


## Autonomous follow-up

The active thread heartbeat `goal-050-detector-completion` checks every 30
minutes, continuing the registered sequence through the timing/budget gate,
production and fixed synthesis. It stays quiet while unchanged or non-actionable
and notifies Barry only for completion, failure, a meaningful scientific finding
or a required decision. It must be deleted when the tranche reaches a verified
completion or stopping outcome. Astra owns the next action; no Fable/Barry reply
is pending. Existing remote helpers are `prepare-production-budget.py`,
`run-bounded.sh` and `run-synthesis.sh`; do not replace them or restart a phase
merely because this task wakes again.


## Timing qualification and production launch

At the 11:14 UTC follow-up, timing had exited zero at **10:45:14 UTC** after
299 wrapper seconds (297.616 s measured within the runner). All four phases
completed. The original calibration/evaluation LR profiles and evaluation joint
holdout scores reproduced exactly (maximum difference zero), with identical
fitted nodes and opaque IDs. All full registered seed separation checks passed.
All 73 source/registration hashes and four timing output hashes verified locally;
remote source, original input manifest and bank identity were rechecked before
production. Timing summary SHA256:
`455410632e48155d5f34c7adee48ee940b1120a90cd3f38a43e336f9ce1a59f9`.

Integration took 275.722 s. The registered 1.5-factor complete production
projection is **11,266.421 s (3.13 h)**; adding the fixed preparation charge,
measured timing and one-hour synthesis reserve gives **16,965.421 s (4.71 h)**,
within the 12-hour cap. The source-bound `production-budget.json` qualified the
unchanged runner. No scientific detector summary was used for this decision.

Production launched once at **2026-09-20 11:15:17 UTC** (21:15:17 Hobart), wrapper
PID **215504**, with the receipt's exact **37,471-s** terminating timeout and
30-s kill grace. The unchanged eight-worker/32-GiB controls apply. Its receipts
are under `production/`; no result or completion is claimed yet. Local evidence:
`artifacts/goal050_execution/{timing/,production-budget.json,production-launch-check.json}`.
The existing heartbeat remains active for completion and the registered synthesis.


## Production completion and synthesis launch

Production exited zero at **2026-09-20 13:57:03 UTC**, after **9,706 wrapper
seconds (2 h 41 min 46 s)**. All 999 original calibration blocks, 1,000 original
evaluation blocks, 999 fresh null calibration histories and 1,000 fresh null
evaluation histories completed. Every original profile and held-out joint score
replayed with maximum difference zero; fitted nodes and opaque IDs matched.
All seed controls, 73 bound source/registration hashes, original input identity,
bank hash and four final phase-file hashes pass. Local retrieval reproduced
those hashes. Peak RSS was 1,881,336 KiB (1.79 GiB); no process remained.

The unchanged wrapper launched the fixed 1,000-draw synthesis once at
**2026-09-20 14:22:02 UTC**, wrapper PID **231159**, with 3,600 seconds reserved.
The computation charge before synthesis is 1,800 + 299 + 9,706 = **11,805 s**,
leaving 31,395 s within the original cap. The wrapper independently checks this
remaining budget. Synthesis receipts use `synthesis.*` under the remote root.


## Verified synthesis and closeout

Synthesis exited zero at **2026-09-20 14:22:44 UTC** (00:22:44 on 21 September
in Hobart), after **42 wrapper seconds**. The registered 1,000 bootstrap draws
used root 2026092006 and took 35.666 s. All eight saved synthesis products,
four phase inputs, source/registration identities and original Goal 049
receipt identities verified after retrieval. The local and remote synthesis
receipt SHA256 is
`3a8ed36fbe71084b297ef0e6f4ca63aeea861fff39b1930408cdf13f70cbea4c`;
production summary SHA256 is
`5d1a71486823ba93e4867bc86cccab8965e25234268c7c5f4a7047ab61c168ab`.
No production or synthesis process remained at final inspection.

The [synthesis](synthesis.md), [final independent review](final-review.md),
[proposed next screen](next-screen-proposal.md) and local
`artifacts/goal050_execution/completed-check.json` record the result and next
decision. Actual preparation/timing/production/synthesis charge is 11,847 s;
charging the entire one-hour synthesis/verification reserve gives 15,405 s
(4.28 h), below 43,200 s. No redraw, source change, restart or scientific
amendment occurred after the timing qualification.


Final independent result review passed after reconstructing all point counts,
Berger–Boos values, saved-bootstrap intervals and hashes. The completed
`goal-050-detector-completion` heartbeat was deleted on 21 September (Hobart).
No automatic continuation remains. Fable is invited to critique the next-screen
proposal; Barry then decides its ecological scope and authority.

Astra posted verified findings and the proposed next screen on Correspondence
thread 44 as messages **430** and **431**. Fable's critique is the next
correspondence action; Barry's subsequent scientific approval is required
before implementing the new screen.
