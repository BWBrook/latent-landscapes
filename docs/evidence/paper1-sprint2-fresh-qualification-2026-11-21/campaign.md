# Fresh qualification campaign

This advances Paper 1 charter pillars 3, 4 and 6 and the Sprint 2 numerical qualification decision. Board 3617 and 3618 retain the registered generator and gate. The frozen candidate is `453739428d75bf3a456aebf48b282b5ebbd870ee`, the audit-journal and passive-prefix derivative of `432bb6e56e672f9e57f2f7bc369546023b07662e`. The campaign binds the clean candidate and the existing Kunanyi image and interpreter. Keep the orchestration checkout and output tree outside the numerical checkout. The native numerical-audit twin must pass before launch. The fresh draw is held for reciprocal review of the evidence rule and resource sizing in board messages 3621 and 3626.

## Panel identity

The old panel generator registers history addresses as `[5, map_index, mu_index, h, stratum_code, replicate]`, with replicate 0. Freeze replicate 1 prospectively. The original generator reads the full address before spawning each stochastic history stream. The sixth coordinate changes together for all arms of a history and for the two enriched backgrounds that share an address. Keep the 81 distinct addresses and every design cell, arm, background, parameter, map and selection flag. The 207 rows are 162 base, 18 boundary, 18 enriched and nine trend. Qualification remains conditional on the same nine maps and the same bank recipes. The bank comparison flags apply to 54 arm datasets, exhaustive to 18 and integration to nine. Old and fresh task names can match, so use a unique fresh results root and bind its freeze hash to every task.

The `freeze` operation verifies the old panel and staged map hashes, recomputes the unchanged generator's old and new seeds and rejects overlaps or within-panel collisions. It writes the prospectively specified panel and a receipt binding design, runtime, source and registration files. The history phase later invokes the original simulator 207 times. Keep qualification evaluation arrays, training and validation outside the fit data interface. Stage only the nine registered qualification maps and the original pinned runtime. The planner checks that map payloads resolve within the staged directory before opening them. It generates 18 fixed bank replicates using the registered K=131,072, order 192 and replicates 0/1. The original bank receipts belong to an older source and panel plan, so this path regenerates those fixed inputs under the accepted runtime and verifies seed reconstruction, payload hashes and non-overlap for all nine bank pairs, including connected-0, which has no selected independent-bank fit. [Sprint 1 generator and fixed design](../paper1-sprint1-2026-11-05/qualification_manifest.py) · [Registered numerical qualification and task graph](../../paper1-sprint2-entry-2026-11-06.md)

## Allocation accounting

Use one ledger on the target and run each campaign allocation through it or inside an explicitly frozen external upper bound recorded at initialization. Reserve the numerical-audit twin at 25 one-core hours for three at most 8-hour allocations plus a 1-hour comparator. Keep its native job, interruption, completion and actual consumption evidence beside its own plan. Retain the 25-hour debit in the campaign ledger. Charge any other separately launched smoke, setup, preparation or worker allocations by adding their maxima to the external envelope before initialization. Reserve 12 hours within the cap for terminal indexing, gate reduction and the completion mail job. Set a larger closeout envelope before initialization if the intended reduction needs it.

One fit allocation requests one core and a 48-hour ceiling. Each task gets at most three total native admissions. Both the immutable task record and the scheduler enforce the fit limit. The campaign admits natural-order first attempts ahead of retries in each phase. Scientific failures are terminal. Losses with a durably preserved fit checkpoint resume from it on the next attempt. An audit or screen with a terminal scientific or indeterminate receipt stays in evidence. Sidecars reporting an execution error can retry with unchanged input identity. A killed pair or integration job starts its computation again on the next attempt. The registered pair search can carry candidate state between coordinates, so this implementation keeps its original uninterrupted ordering inside each attempt.

Each job has its full one-core walltime and 120 seconds for scheduler accounting reserved durably before `qsub`. Admission and refunds serialize under one shared file lock. Jobs are held and non-rerunnable, with one immutable ticket each. Record and verify the native job ID, owner, non-rerunnable flag, resources and hold before `qrls`. A worker checks the recorded job and claims its ticket once before any scientific command. PBS sends abort mail for each allocation and abort/end mail for explicitly selected checkpoints and closeout.

Reconciliation pulls native terminal records while PBS retains them. A terminal single-run one-core accounting record with positive walltime releases the unused reservation, rounding its charge upward by one second. An unverifiable charge retains the maximum. An observed rerun, extra allocated cores or overrun beyond the margin freezes admission and requires reconciliation of the native billing record. On an interrupted submission or a nonzero `qsub` exit, the pending reservation survives at full charge. `recover-held --name NAME --job PBS_ID` releases the identified and verified held job. Unknown submissions retain the full reservation. A release of that reservation would require positive native evidence of non-acceptance and an independently documented adjustment. A silently requeued allocation is an anomaly, even if a ticket claim blocks the second scientific execution. The ledger records commitments and charges in integer one-core seconds. Verify shared lock and atomic rename behavior on the chosen coordination filesystem.

| Work | Registered maximum task count | Per-allocation walltime request |
| --- | ---: | ---: |
| Fixed banks | 18 | 8 h |
| Histories | 207 | 15 min |
| Dense / lean / independent bank / exhaustive | 207 / 207 / 54 / 18 | 48 h |
| Exact dense/lean and independent-bank anchor pairs | 207 + 54 | 48 h |
| Free-point gradients | 207 | 12 h |
| Capped integration screens | 9 | 48 h |

Archived grids and one-sided replay times imply **about 6,540 one-core hours for the anchor pairs alone**, a sizing sensitivity using observed older workloads. The executable calculation verifies the original and replay receipt hashes. It forms the exact union separately by view using the registered audit inventory, including original rows, free points, roots and component endpoints. Every exact pair node invokes the probe on both sides. [Sizing calculation](campaign-sizing.py) · [Independent old-panel assessment](old-panel-assessment.md)

| Resolved comparison group on original `99af520` | Resolved / fresh required pairs | Standard + tight + exposure + constant union nodes | Mean union nodes per old pair |
| --- | ---: | ---: | ---: |
| Dense / lean | 168 / 207 | 38,636 + 38,636 + 48,548 + 56,145 = 181,965 | 1,083.125 |
| Lean / independent bank | 50 / 54 | 7,982 + 7,982 + 12,378 + 14,562 = 42,904 | 858.08 |

The 24 accepted one-sided replays consumed 542,141.23 worker-wall seconds over 12,460 evaluations with zero checkpoint hits, or 43.5105 seconds per call. Scaling the two union groups separately and evaluating both sides gives `2 × (181965 × 207/168 + 42904 × 54/50) = 541086.39` calls. The pooled rate gives 6,539.71 hours. Timing the intervals between successive checkpoints separately for the four views gives means of 77.42, 90.57, 21.94 and 14.51 seconds. Applying each rate to its corresponding projected view count gives 6,823.88 hours, with setup and teardown outside the timing intervals. [Accepted source probe evidence](../paper1-sprint2-acceptance-2026-11-21/README.md) · [Native checkpoint timings](campaign-probe-timing.json) · [Reproduced projections](campaign-sizing.json)

Using the earlier 4,700–6,000-hour fit estimate gives **about 11,200–12,800 hours for fits and anchor pairs**, before gradients, screens, fixed banks, the twin, receipt reduction or scheduler losses. Both projections transfer archived rates and grids to the fresh task mix. Differences in fit complexity, grid inventories, shared evaluator state and eligibility losses may change the realised balance. The two projections are planning sensitivities. The 9,000-hour cap protects spend and can leave the registered packet incomplete.

Run the read-only sizing calculation from the repository root after restoring the same receipt archives.

```sh
.venv/bin/python docs/evidence/paper1-sprint2-fresh-qualification-2026-11-21/campaign-sizing.py \
  --original-results artifacts/sprint2/fresh-qualification-20261121/old-panel/original-results \
  --accepted-probes artifacts/sprint2/boundary-resume-20261121/raw/probe-results
```

## Target sequence

Set absolute paths on Kunanyi. `HARNESS` contains this workflow. `CANDIDATE` is a clean checkout of the accepted derivative. `WORK` is the unique campaign storage root, including output receipts, plans and the one ledger. `MAPS` is the staged qualification map root and `RUNTIME` is the verified unchanged-image runtime receipt rebound to the reviewed source. `REGISTER` is the reviewed freeze record covering source, candidate twin verdict, panel recipe, unchanged gate and secondary analyses. `PRECHARGED` binds the external twin job plan, native settings and its 25-hour cap. Include any additional explicitly bounded allocation outside this ledger in that file and the `--external-hours` total. `PBS_EMAIL` is the project notification recipient. Controller argument ordering matters because `--` forwards every following argument to the charged Python script.

```sh
export MODULEPATH="${MODULEPATH:-/opt/ohpc/pub/moduledeps/gnu8:/opt/ohpc/pub/modulefiles:/share/apps/modules:/share/apps/eb-modules/all:/share/apps/eb-modules/rosalind/Core}"
. /opt/ohpc/admin/lmod/lmod/init/bash
module load Python/3.11.5-GCCcore-13.2.0 git/2.42.0-GCCcore-13.2.0
export PATH="/opt/pbs/bin:$PATH"
CANDIDATE_SHA=453739428d75bf3a456aebf48b282b5ebbd870ee
llctl() {
  python3 "$HARNESS/scripts/pbs/fresh_campaign.py" --ledger "$WORK/ledger" "$@"
}
llctl init --candidate "$CANDIDATE" --runtime-receipt "$RUNTIME" \
  --results-root "$WORK/results" --email "$PBS_EMAIL" \
  --bind "$WORK" --bind "$CANDIDATE" --bind "$HARNESS" --bind "$MAPS" \
  --external-hours 25 --external-evidence "$PRECHARGED" --closeout-hours 12

llctl submit-aux --label allocation-smoke --notify --python --wall-minutes 15 --memory 2gb \
  --script "$HARNESS/scripts/prepare_fresh_qualification.py" -- \
  --candidate "$CANDIDATE" --source-commit "$CANDIDATE_SHA" \
  --runtime-receipt "$RUNTIME" verify-runtime
```

Before the draw, reconcile this smoke after it finishes. Verify the held and terminal native captures, the single-run charge release, ticket claim, unchanged SIF and end mail. Confirm the project queue and remaining allocation separately. Check that the source import guard resolves package and script code to the expected checkout in the native container. Collect representative abort or interruption evidence from the numerical twin and exercise a native failed attempt on fixtures if the twin used a different resource path. Native PBS walltime/billing semantics, termination visibility and notification delivery need target evidence.

```sh
freeze_plan() {
  local job_label="$1" wall_minutes="$2"
  shift 2
  llctl submit-aux --label "$job_label" --python --wall-minutes "$wall_minutes" --memory 8gb \
    --script "$HARNESS/scripts/prepare_fresh_qualification.py" -- \
    --candidate "$CANDIDATE" --source-commit "$CANDIDATE_SHA" \
    --maps-root "$MAPS" --runtime-receipt "$RUNTIME" "$@"
}
freeze_plan panel-freeze 30 freeze --output "$WORK/freeze" --registration "$REGISTER"
```

After the charged freeze job exits and its receipt verifies, bind the freeze once with `llctl bind-panel --freeze "$WORK/freeze/panel-freeze.json"`. Prepare `banks` and `histories` using `freeze_plan LABEL 60 prepare PHASE --freeze "$WORK/freeze/panel-freeze.json" --results-root "$WORK/results" --output-dir "$WORK/plans/PHASE"`. Admit each saved task list with `llctl submit --tasks "$WORK/plans/PHASE/tasks.jsonl" --max-jobs N`. Choose `N` for queue turnover. Call `llctl reconcile` regularly so finished jobs refund their unused reservations before history expires. The same submit command continues a later wave or re-admits eligible losses. If an independent closeout or file review is still outstanding, a scheduler exit only records execution state.

Prepare `fits` after all input receipts are available, passing both earlier `--dependency-plan "$WORK/plans/PHASE/plan.json"` files. Inspect the fit plan for all 486 rows and admit it through the same command. Reserve every new native job through the ledger. After fit attempts settle, prepare `audits` and `integration` with the bank, history and fit dependency plans. The plans list absent/unusable prerequisites explicitly and produce tasks only for the checks the original planner can execute. Keep the full fit and diagnostic plan denominators in closeout. Later waves use the original task list for consistent receipt verification. Run the plans again in a new directory only to capture newly available prerequisites. Never edit a frozen task or substitute a later fit for a registered scientific failure.

Prepare `index` under `submit-aux --closeout` with every prior dependency plan after outcomes or the cap stop has been reconciled. Preserve the final `qualification-index.json`, every terminal and missing task entry, probe ceilings and exclusion reasons. Planner phases cache byte digests within a single run and check file identity, length and modification/change timestamps before publishing the plan. Workers and the reducer still verify the underlying input and receipt identities.

Once the reviewed source holds all its prerequisites, submit the unchanged `scripts/summarise_sprint2_qualification.py` from the candidate via `llctl submit-aux --label registered-gate --python --closeout --notify --wall-minutes N --memory 8gb --script ... -- --panel "$WORK/freeze/panel.json" --index "$WORK/plans/index/qualification-index.json" --output "$WORK/qualification-summary.json"`. Keep the native completion mail, its job/charge, the final `llctl reconcile` snapshot and auxiliary/twin accounting manifest. A nonzero exit can represent the registered scientific or incomplete verdict, so classify from the bound summary and native evidence. Training and validation remain closed.

## Local verification and target boundary

`tests/test_fresh_qualification.py` uses fake rows, task receipts and native PBS accounting. It exercises unchanged pairing/design fields, fit argument adaptation to the accepted commit, same-run hash reuse and drift detection, atomic competing reservations, retention after ambiguous submission, conservative refunds, rerun detection, duplicate admission rejection, exclusive worker claims, exhausted retry selection and closeout capacity. The existing planner and PBS tests exercise the underlying unchanged task and evidence checks.

A read-only Kunanyi query confirmed native Python 3.11.5 and Git 2.42.0 after loading the named modules. The two active twin allocations were running on one core, and the later two were dependency-held. All four were non-rerunnable with their registered ceilings and mail points. Kunanyi's `qstat -xf -F json` exposed the expected allocation fields and the prior terminal replay completion job exposed the single-run accounting fields. Native smoke 882707 verified the held submission, release and exclusive ticket claim. It bound the candidate and existing runtime, exited zero after 32 PBS wall-seconds and reconciled to a 33-core-second ledger charge. Its ledger records the four external twin jobs and the 12-hour closeout reserve with no fresh panel bound. PBS delivery for the twin comparator can be confirmed when job 882706 ends. [Native smoke receipt](campaign-smoke.json)
