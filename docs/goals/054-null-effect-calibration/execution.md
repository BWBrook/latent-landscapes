# Goal 054 execution

30 September 2026 (Hobart). **Verified completed outcome; independent review
accepted the conditional claims. No run remains active.** The chronological
launch instructions below are historical records, not permission to repeat
a completed phase. See the final section for closeout and the next action.

Scientific scope and rules are in [registration-2026-09-29.md](registration-2026-09-29.md).
Fable's critique (thread53 messages646–647) was read and acknowledged through647;
the task-local retrieval checkpoint is773. Barry approved the calibration and
extra pair, retaining Astra's authority over compute and time.

The decision and scope response is Astra message777 on thread53. The
[independent methods review](methods-review.md) supports the two finite-grid
rules; its coefficient, indicator tie, one-sided tolerance and conditional-error
specifications are incorporated in the registration before qualification.

Live host check at 2026-09-29 12:36:58 UTC: deep-server idle, 122 GiB available,
4.3 TiB free under /data. The new root did not exist. Goal053 remains frozen.
New root: `/data/codex/scratch/goal054-null-effect-calibration-20260929`.

Qualification will use all81 coefficient rows on four disjoint reference
blocks and eight disjoint evaluation blocks (388 histories), plus the full
24-history Goal052 replay at every row. Initial concurrency16 independent
processes, one numerical thread each. The production timeout will use measured
generation, scoring, serialization and reduction, with a conservative allowance
and at least 3,600 seconds reserved for synthesis/verification. These operational
choices can change with measured evidence; scientific replication cannot.

Astra owns implementation, qualification, dispatch, verification and closeout.
No Barry or Fable response is needed now.

## Qualified source and first timing launch

All 72 focused tests passed locally and on deep-server, with Ruff and strict
mypy passing for the five new source/CLI files. The initial Linux test attempt
had 71 passes and one missing archived Goal051 fixture; its failure log is
preserved. A read-only link to the original archive, verified as
`6d98c61d8ecee7b53335dec13de536bfbead700fee6d97a48644efafba11e381`,
resolved the fixture without changing source. No failed simulation was repeated.

The manifest binds 89 source files and three helpers. Manifest SHA256:
`1ba742e40329a1d75424aa0944712e6ee56708c090245ac4d8ca4067d49a6a00`.
All86 Goal053-bound source files remain unchanged. Preflight verified the
original bank and Goal053 contract, disjoint new streams against 161,344 old
campaign/bank seeds, and absence of prior attempts.

Timing launched once at **2026-09-29 13:05:38.180848 UTC**, wrapper PID **41299**,
Python PID **41306**, timeout **3,600 seconds**, **16** processes and one numerical
thread per process. The address-space limit is 48 GiB per process. The first
324 reference and64 evaluation timing histories were committed successfully;
the all81-row frozen score replay was active at the first live check.

Continuation: inspect timing/attempts, timing.log and process state. After a
zero exit use `source/.venv/bin/python ../control.py verify timing` from source,
then the root `crosscheck.py` against timing/output, saving its receipt outside
the bound timing/output directory. Only after both pass, use `control.py budget`,
inspect the complete measured projection and launch production once through
`control.py launch production`. Never change source or rewrite an attempt to
force qualification. No additional scientific authorization is needed.

The thread heartbeat **goal-054-calibration-completion** is active every
30 minutes. It owns unattended continuation and stays quiet while unchanged;
delete it after verified closeout/stopping or a scientific decision requiring
Barry. It must inspect live receipts rather than assuming the initial launch
state in its prompt is current.

## Verified timing and production launch

Timing exited zero at **2026-09-29 13:07:29 UTC**, after111 receipt seconds.
The controller verified all168 output files, all81 coefficient rows, unchanged
source/helpers/integrations and the frozen24-history replay at every row.
Independent reconstruction of12 boundary/interior reference histories and24
evaluation histories from all81 raw rows matched the reduced evidence exactly
(maximum absolute error0). Receipts: `timing-verification.json` and
`timing-crosscheck.json` under the root and local evidence directory.

Contract fingerprint:
`6ec66934da77fc2e054b257c3b3246fbfb5a7ceb3a7f64677b61db5304e9a92a`.
Timing summary SHA256:
`25d7190816033002bf74082182f1995ee8cac773c3b1fac35ffcd4f05a83cae5`.
Timing reduced-statistic SHA256:
`e687c57a96849cecf4801fdbeb9572670b59e1c77ca4f49a699eb7d9856a6052`.

The measured projection includes generation332s, ceiling-wave scoring11,722s,
conservative serial serialization/reduction4,675s and fixed replay52s. Applying
the1.5 allowance plus3,600s reserve gives28,771s; the production timeout is
rounded to **25,200s (7hours)** with a separate **3,600s** synthesis allowance.
This fits the delegated operational envelope; no scientific dimension changed.
These are projections, not observed production timings.

Production launched once at **2026-09-29 13:09:16.365817 UTC**, wrapper PID
**42115**, Python PID **42122**. Its first live process check showed it actively
generating the registered reference panel. No exit receipt was present then.
The new reference/evaluation histories must not be regenerated or duplicated.
A subsequent live check confirmed all80,919 reference histories committed and
the original production process still active. Astra posted the qualified
launch receipt as Correspondence thread53 message782.

After production exits zero: `control.py verify production`; then
`crosscheck.py production/output --receipt production-crosscheck.json` using
absolute root paths (or paths relative to source with `../`). After both pass,
`control.py launch synthesis` runs the fixed2,000 draws once. Verify synthesis,
retrieve the evidence, inspect tables/figures and obtain independent scientific
result review before closeout. The heartbeat remains active until that outcome.

## Verified production and synthesis launch

Production exited zero at **2026-09-29 16:14:55 UTC**, after **11,139 seconds
(3 h 5 min 39 s)**. All 81 coefficient rows and 88,919 histories are present;
the all-row frozen replay's maximum absolute error is 1.93e-12. The controller
verified all 168 output files and unchanged source, helper, original-input and
integration bindings. Production summary SHA256:
`d2cf651e6425cf58af93913fbb3a1c1c0721396d6a5bbfc66f1d7ed8ae2ea047`.

The independent raw-score crosscheck authenticated all 81 rows and reconstructed
12 reference and 24 evaluation histories exactly (maximum absolute error 0).
Reduced-statistic SHA256:
`33c94ad6d7bb58701c68b611c70400c0228787e1782026c7df7d9b747aa40900`.
Receipts are `production-verification.json` and `production-crosscheck.json`.
All 87 retrieved non-bulk output files match the verified manifest; the 81
bulk score files remain authenticated in the remote production directory.

The single fixed 2,000-draw synthesis launched at **2026-09-29 16:42:35.751589
UTC**, wrapper PID **44935**, with the bound **3,600-second** timeout.
Do not duplicate it. An independent result-level audit is in progress.

## Verified synthesis and scientific closeout

The single fixed 2,000-draw synthesis exited zero at **2026-09-29 16:43:17
UTC**, after **42 receipt seconds**. The controller verified all **11** output
files, the production-statistic input identity and all unchanged source,
helper, original-input and integration bindings. Synthesis summary SHA256:
`7112017925c7487f9c7187c47eb632d3cae20db7723ddc0fcd012e693a2c0a57`.
The reduced-statistic SHA256 remains
`33c94ad6d7bb58701c68b611c70400c0228787e1782026c7df7d9b747aa40900`.
All local source89/helper3, production87 and synthesis11 files passed hash
checks against the registered or verified manifests. The 81 bulk row arrays
remain authenticated on deep-server. The local
`artifacts/goal054_execution/retrieval-manifest.json` indexes both locations.

The final remote check found one zero-exit attempt for each phase, an available
run lock and no active scientific process. The local copies of all attempts,
launches and logs match their remote hashes. Timing, production and synthesis
used 111, 11,139 and 42 elapsed receipt seconds respectively (3 h 8 min 12 s
in total, excluding development and human/agent review). No timeout or scope
adaptation was required.

The [scientific synthesis](synthesis.md) and [independent result review](final-review.md)
retain the sensitivity cost, magnitude-estimation trade-off, all forecasts,
reference-table uncertainty, actual fields and negative secondary results.
The reviewer reconstructed all seven rules through independent counting and
rank paths, all 56 rule rates, all 56 registered estimator/rule selected-subset
rows and six saved bootstrap draws with maximum discrepancy zero. A focused
review of the final synthesis/proposal found no material correction needed.
The reporting-only paired contrasts matched the existing draws to 1.22e-15;
all 424 field summaries matched exactly. No new simulation, fit or full
bootstrap was run for review or reporting.

Both original synthesis figures and the separate three-panel report figure
were visually inspected. The latter and its PDF, source, field summary and
paired estimation contrasts are bound by
`artifacts/goal054_execution/report/report_manifest.json`. The original
registered synthesis output is unchanged.

Astra posted the verified findings and the [next-tranche proposal](next-tranche-proposal.md)
on Correspondence thread53 as **messages 784 and 785**. Message785 corrects a
manually typed timestamp in784; the authoritative posting receipt for784 is
**30 September 2026, 03:00:28 AEST**. The completion heartbeat
**goal-054-calibration-completion was deleted** after verified completion.
`artifacts/goal054_execution/completed-check.json` binds the final closeout.

**Next action: Fable critiques the proposed Arc4 synthesis/capstone-design
scope, then Barry decides that scientific scope.** There is no current
scientific-compute task for Astra to launch. Resource/time decisions remain
delegated. All previous failures, Goal049–053 and the original unconfirmed
Goal051 nomination remain preserved. No commit, push or publication occurred.
Correspondence was caught up and acknowledged through message785; the final
task-local retrieval checkpoint is785.
