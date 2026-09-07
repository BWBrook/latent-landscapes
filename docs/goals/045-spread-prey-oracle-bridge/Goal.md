# Goal 045: The Cost of Estimating Predator Spread Speed

Status: original scientific scope retained. Barry authorized one further
131072-draw reference on 7 September; running on deep-server. No bank promoted.
Programme role: Arc 2C, Charter Pillar 2, selected joint-recovery bridge.

## Question and completion condition

How much does estimating predator spread speed, instead of supplying its true
value, change recovery of the predator's effect on prey? Earlier arrival with
a smaller effect can resemble later arrival with a stronger effect. The result
is the paired difference between analyses of identical observations.

Complete the six-case comparison, evaluate the evidence with proportional
checks, produce an intelligible synthesis, review independently, consolidate
the new active path where warranted, and publish. A valid weak or negative
result completes the goal. Successful recovery in every case is not required.

## Frozen scientific design

| Condition | Spread rate rho | Prey hazard multiplier | Role |
| --- | ---: | ---: | --- |
| usual_1 | 1 | 1 | No-effect control |
| usual_3 | 1 | 3 | Transition candidate |
| usual_5 | 1 | 5 | Strong reference |
| slow_1 | 0.5 | 1 | Slow-wave no-effect control |
| slow_3 | 0.5 | 3 | Combined challenge |
| slow_5 | 0.5 | 5 | Slow-wave strong effect |

Retain the reference landscape, resistance eta=1, 160 access-constrained sites,
cluster-isolated 120 training/40 holdout allocation, days 10 through 60 in
10-day steps, two visits, and zero false positives. Both detection probabilities
are known at 0.65. Background prey hazard is known at 0.002/day, equivalent to
11.3% loss over 60 days without predators. Prey extirpation is absorbing.

The `known_speed` analysis estimates only prey effect. The `estimated_speed`
analysis estimates rho and prey effect jointly. All fitting and interval
construction use the same 120 training sites; the 40 holdout sites never fit
parameters. This differs from earlier recovery summaries that used all 160
sites, so historical headline gates are context, not exact replay targets.
Both analyses keep realised predator arrival latent. Within each site both
species share the same candidate arrival before integration. Across sites we
retain the site-marginal composite likelihood, with no spatial dependence claim.

Use the existing broad rho domain 0.25-4 (201 log-spaced points, including exact 0.5 and 1)
and effect domain 1-10 (181 linear points), including all generating values.
Rho scales each base arrival by 1/rho exactly under the accepted spread model.
Use the numerically verified 16384-draw arrival integration bank. Master seed is
20260905, independent of Arc 2A/B. Use common random numbers across the six cases and paired analyses,
with separate integration, calibration, and evaluation streams.

Each case has 250 calibration and 250 independent evaluation datasets. The
239th ordered calibration statistic defines each local 95% cutoff. Calibrate
the known-speed effect profile, estimated-speed effect profile, and estimated-
speed rho profile separately. They provide parameter-specific intervals, not a
simultaneous region. Calibration still knows the generating condition; this
is a process-oracle relaxation, not a field-ready calibration method.

## Primary comparisons

Report paired changes in effect absolute log error, log interval width,
coverage, no-effect exclusion, and held-out conditional prey log score, plus
rho accuracy/precision and interval boundary/connectedness diagnostics.
Primary prediction is the average over holdout sites of
`log P(prey, predator | training fit) - log P(predator | same training fit)`.
Conditioning on holdout predator observations is permitted prediction input;
holdout prey observations only score predictions. The matched null fixes effect
at one with the same known background and detection. Its conditional prey score
is independent of rho and therefore identical between analyses. For secondary
joint scores the null uses the known true rho in the known-speed analysis and
estimates its own rho from training predator observations in the estimated-speed
analysis. Thus each secondary comparator has the same speed information as
the effect model it is compared with.

Resample complete calibration dataset indices and complete evaluation indices
separately, preserving pairing across analyses and cases. Recalculate cutoffs
and support metrics in 1000 bootstrap resamples from saved profiles, without
additional simulations. These intervals include calibration-sample variation,
but condition on this integration bank and generating model. Never resample
sites as independent units. Retain event yield and exposure as explanatory
truth-assisted diagnostics, not inference inputs.

Continuous differences and their uncertainty are primary. For context retain
prior effect error 0.20/log-width 0.80, rho error 0.10/log-width 0.50, and
approximately 95% exclusion/coverage benchmarks. Null cases have no interior
requirement at effect=1. Report false exclusions with binomial uncertainty;
do not require every descriptive coverage interval to contain 0.95. Distinguish
both-analyses-weak cases from deterioration specific to estimating speed.

Forecasts: central fivefold recovery should remain informative; slower spread
should reduce observed post-arrival events; the added estimation cost may be
largest near the threefold case. These are predictions, not acceptance tests.

## Numerical amendment before production, 6 September 2026

The original 51-point log-rho grid plus exact 0.5 did not resolve the joint
likelihood maximum in the first preselected usual-speed history. Its recorded
half-grid gains of 1.19–1.25 log-likelihood units exceeded the 0.25 numerical
review limit, while doubling the bank changed the old-node profile LRs by
less than 0.038. Production had not started.

A local nested-grid diagnosis reused that history and the saved 4096-draw bank.
It covered the original LR<=10 speed ranges plus one coarse neighbour on each
side, retaining all 181 effect values. Against the locally evaluated 401-point
grid, the largest maximum-LL deficit was 1.311 on the original grid and 0.0741
on the 201-point grid. The 101-point grid happened to place this history's peak
equally well, but its larger spacing is less robust to a peak falling elsewhere
between candidates. The fixed 201-point grid is the numerical repair; this is
not a new biological domain, estimator, or recovery threshold. The original
evidence remains under `artifacts/goal045_execution/` and its recorded remote
run directories. The diagnosis is under
`/data/codex/scratch/goal045-grid-diagnosis-20260906-fbc6f77/`.

The expanded preflight uses the two calibration and two evaluation histories
already included in the timing run, with the six cases kept paired. Save their
training surfaces and compare the 4096/8192 banks at the new candidate nodes.
Assess profile changes over the union where either comparison has LR<=10,
including direct truth-LR changes. Recheck the local half-grid maxima and
profile shapes, retaining the original 0.25 LL-gain, 0.5 LR-change and MLE
review limits. Inspect the eventual calibrated cutoffs against the numerical
range before final acceptance. Seeds, production ensembles, effect grid,
observation design, comparator information and calibration rule are unchanged.
The experiment will be reported as prospectively completed after a numerical
amendment, rather than described as wholly prespecified.

## Bank amendment before production, 6 September 2026

The four-history check on the repaired rho grid revealed finite-bank sensitivity
in one shared calibration predator history. The 4096-to-8192 comparison changed
its spread-profile LR by 1.012, exceeding 0.5, with sparse compatible arrivals
at two influential sites. The larger nested-bank screen and subsequent full
joint check support 16384 draws against a 32768-draw reference.

The full joint check covered all 201 rho values, all 181 effect values and all
24 paired case/history profiles, followed by local rho midpoint and known-speed
effect midpoint checks. All original numerical limits passed. Maximum bank
profile-LR change was 0.3592, maximum direct truth-LR change 0.1904, maximum
grid profile-LR change 0.1752 and maximum LL gain 0.0876. Rho support components,
boundary contact and endpoint movement passed the checks at cutoffs 2, 5 and 10.
Saved array checks independently reproduced the spread-LR comparisons and the
no-effect factorisation against the separate predator-only screen.

The production bank is therefore amended from 4096 to 16384. It is the first
16384 draws of the verified nested 32768 bank; its array checksum is
`087cdd674d84c5df8ba217fd6013a6421d0d4a3c61d626c6969aac3db5ea5e93`.
Reuse it with exact seed, site-order and checksum validation. The root seed,
all calibration/evaluation histories, grid domain, pseudo-count, observation
model, estimands, comparators and numerical limits are unchanged. This is a
documented numerical-accuracy amendment within the approved diagnostic scope.
Numerical evidence remains conditional on four paired histories; inspect the
eventual calibrated cutoffs before final scientific acceptance.

## Stages and checks

1. Build a small joint likelihood using the accepted Arc 2B kernel, verify
   known-speed restriction and no-effect factorisation, and run a reduced
   end-to-end check plus a production-grid timing probe.
2. Freeze source before the detached six-case production run on deep-server.
3. Synthesize the paired evidence with a six-case table, ecological comparison
   figure, preselected first-evaluation-dataset likelihood plots, and memo.
4. Run one focused review/repair pass and independent final scientific review;
   preserve a compact active path and publish exact reviewed paths.

Tests protect likelihood equivalence, latent-arrival sharing, holdout exclusion,
parameter profiling, null factorisation, paired bootstrap resampling and file
round-trip. Check finite probabilities, split integrity, complete rows, and
grid/bank numerical stability on reduced canaries before production. A doubled
bank or refined-grid canary is numerical diagnosis, not new biological cases.
Retain compact raw profiles outside Git so bootstrap decisions are replayable.

## Authority and stop rules

Barry authorizes autonomous implementation, native specialist subagents,
remote execution, intermediate source commits/pushes, independent review,
bounded consolidation, and fast-forward publication to main. Stage exact
paths. No unrelated cleanup or destructive Git operations. External reads and
actions are limited to global skills/instructions, nectar control-plane docs,
deep-server under /data/codex, GitHub source publication, and the requested
Codex heartbeat. No legacy spatext dependency or sibling-project edits.

On 7 September 2026 Barry explicitly authorized the projected 25.34-hour
131072-draw reference on idle deep-server if scientifically useful. Independent
reassessment and parent judgment support this one final bank doubling. This is
a run-specific exception to the 24-hour boundary, not standing authority for
serial escalation. The narrower primary-only closeout proposal was not approved.
All scientific settings, estimands and numerical criteria remain unchanged.

Use the Mac mini for development and deep-server for detached production after
timing/memory checks. Escalate projected production over 24 hours or a material
scientific change. Once launched, check every two hours with a quiet heartbeat;
while running, perform only a bounded status probe and end the wake. On success,
retrieve evidence and resume review/closeout. On failure, diagnose the cause
before proposing a rerun; never silently change the scientific design. Pause
the heartbeat once the goal is complete or human input is required.

No unknown background/detection, new landscape, sampling change, enrichment,
new response surfaces, simultaneous-coverage claim, real data, or next goal.
Stop after the six cases and the material review pass. Do not chase a desired
recovery threshold. Material numerical failure or contradictory calibration
can trigger diagnosis; a negative ecological result is not an implementation bug.

## Execution record

- 2026-09-05: scope approved; source branch created from clean main at 4d6d23b.
- Implemented separate design, shared-arrival likelihood, paired campaign and
  synthesis modules, reusing the accepted Arc 2B kernel rather than copying it.
- Local reduced campaign passed all 12 structural/numerical invariants. The
  reduced synthesis wrote seven review files and 18 parameter-summary rows;
  reduced runs are explicitly labelled non-scientific. Diagnostic event
  accounting refers to the 120 training sites.
- Focused new-module and Arc 2B regression tests: 28 passed. Scoped Ruff and
  strict mypy passed. Independent review prompted a tight floating-point
  tolerance for equivalent no-effect event times, explicit null-case direction
  labels, and consistent nonproduction outcomes; no scientific design changed.
- Full-grid-shaped local likelihood probe: 0.590 GB integration storage,
  approximately 0.831 GB process peak, six evaluations in 0.63 seconds serial
  or 0.26 seconds across six threads. This used a small bank and is timing
  evidence only, not the full-bank numerical check.
- The prespecified numerical canary uses the first evaluation dataset in each
  frozen case, nested 4096/8192 integration banks and local half-grid checks.
  Review limits: effect log-MLE change 0.05, rho log-MLE change 0.06, profile LR
  change 0.5 within the original LR<=10 range, and local maximum log-likelihood
  gain 0.25. All three parameter profiles and both analysis maxima are checked.
  These are numerical review prompts, not new ecological selection gates.
- Independent pre-launch review passed after the material repairs. Build also
  passed. Source is frozen and pushed on the goal branch at
  `b67e5e6cf0f7d297883c265dd5c245ce1f90ea5e`; canonical main remains the accepted
  Goal 044 checkpoint until results are reviewed.
- Detached timing run: `deep-server-ts`,
  `/data/codex/scratch/goal045-timing-20260905-b67e5e6`, tmux
  `ll-goal045-timing`. It started at 07:00 UTC on 5 September 2026.
- Guarded workflow: `/data/codex/artifacts/goal045-production-20260905-b67e5e6`,
  tmux `ll-goal045-workflow`. It waits for successful timing, runs the numerical
  canary, and starts eight-worker production only if all numerical review limits
  pass and the conservative runtime estimate is <=24 hours. Failure preserves
  the stage and logs for diagnosis; it does not relax the scientific design.
  Frozen source checkouts were materialised from a Git bundle and `uv sync
  --frozen`; no remote GitHub credentials are required.
- Last receipt at 07:05 UTC: workflow `RUNNING`, stage `waiting_for_timing`.
  Full-bank timing and production scientific results remain pending.
- Active Codex heartbeat `goal-045-completion-check` checks every two hours.
  It ends unchanged wakes after a bounded probe, resumes review after success,
  diagnoses failure narrowly, and pauses itself after closeout or a genuine
  human decision. No live monitoring loop is required.
- Next continuation: inspect `workflow.status`, `workflow.stage`,
  `workflow.exit.status`, numerical evidence and output `run_summary.json`;
  retrieve compact artifacts excluding source/venv; synthesize with 1000
  bootstrap resamples; review independently; update the roadmap/report and
  publish exact accepted paths. Do not mark the goal complete merely because
  simulation exited successfully.
- Handover update, 2026-09-05 08:35 UTC: timing exited zero (566.7 seconds),
  but the workflow stopped at `preflight_gate` with exit 1. Production did not
  start. Bank-doubling profile changes were <0.038; local joint-grid refinement
  gained 1.19-1.25 log-likelihood units in the three usual-speed cases, above
  the 0.25 review limit. This needs bounded numerical diagnosis, not an unchanged
  relaunch or an ecological failure claim. The original evidence is preserved.
- Barry requested a fresh successor task in the code repo. `HANDOVER.md` is the
  compact entry point. The old task's heartbeat is paused to avoid competing
  execution; its target must be changed before any resumption. No remote job
  was interrupted, no model repair was made, and this goal remains unfinished.
- Subsequent cleanup request, 2026-09-05: Barry explicitly authorised a clean
  handover with only `main` retained. Consolidate the existing Goal 045 source
  and handover into `main` without changing simulation code, then remove goal
  branches only after their tips are verified as preserved in `main` and
  `origin/main`. This is an administrative handover snapshot, not scientific
  acceptance of Goal 045; all numerical and result-review gates remain open.
  The obsolete heartbeat has now been deleted, and the retiring Chief worktree
  removed. Project evidence and remote runs were not deleted or restarted.
- Resumed 6 September 2026 (Hobart): bounded diagnosis and independent numerical
  review selected the fixed 201-point rho grid described above. Source commit
  `ce368b36824b51b859e1136b60c95fe4b9d35a15` is frozen and pushed to main.
  The four-history canary retains calibration/evaluation surfaces, checks union
  LR<=10 changes and truth LRs, and verifies replay at retained candidate nodes.
  All 17 focused likelihood/campaign/synthesis/canary tests, scoped Ruff and
  strict mypy passed. These are implementation checks, not numerical acceptance.
- New detached workflow launched at 2026-09-05 14:33 UTC on `deep-server-ts`,
  tmux `ll-goal045-rho201`, under
  `/data/codex/artifacts/goal045-rho201-20260906-ce368b3/`.
  The first receipt confirms `RUNNING`, stage `timing`, correct source commit,
  and bank generation underway. The original failed workflow remains intact.
  `workflow_rho201.sh` runs eight-worker timing into `timing/`, the expanded
  numerical canary, and then eight-worker production into `output/` only after
  numerical limits and the conservative <=24-hour runtime gate pass.
  Source was transferred in a Git bundle and installed with `uv sync --frozen`.
- The successor task now owns active two-hour heartbeat
  `goal-045-completion-check`. While running it performs a bounded quiet probe;
  after completion it resumes retrieval, calibrated-range numerical review,
  1000-bootstrap synthesis, independent scientific review and exact-path
  publication. It pauses after closeout or a required human decision. Goal 045
  remains unfinished until those scientific completion conditions are met.
- At 2026-09-05 16:23 UTC the repaired-grid workflow stopped at `preflight_gate`.
  Timing and the expanded canary completed successfully as computations; the
  numerical gate failed. Conservative production projection was 3.46 hours.
  All 24 case/history grid checks passed: maximum half-grid LL gain 0.0741 and
  maximum grid profile-LR change 0.1482. Three bank checks failed, all sharing
  calibration history 0 at usual speed: spread profile-LR changes were
  1.009–1.012 against the 0.5 limit. Other bank profile, MLE and direct truth-LR
  checks passed. These three cases share the same predator observations and
  constitute one numerical sensitivity event, not three independent failures.
- At rho 0.972655, that history's no-effect spread LR changed from 6.969 to
  7.978 between 4096 and 8192 draws, while its MLE stayed at rho 1.013959.
  Two influential training sites had only 10 and 14 compatible bank arrivals
  at that node (27 and 34 at the MLE). A draw-level delta-method diagnostic,
  retaining covariance across sites, gave approximate LR Monte Carlo SE 0.839
  at 4096 draws. Repeating the identical empirical bank while only reducing
  pseudo-count weight changed this LR by 0.056 on doubling, much less than the
  observed 1.009. This supports finite-bank rare-event error as the next issue.
  Rho-support component counts agreed between the original, doubled and refined
  surfaces at LR cutoffs 2, 5 and 10; this does not override the failed LR limit.
- Independent numerical review recommended a cheap nested 8192/16384/32768
  predator-marginal screen over all 201 rho values and all four timing histories,
  followed by a full joint 16384-versus-32768 check with all 181 effects and all
  six paired cases over the union of relevant likelihood windows. The screen
  is diagnostic only. Production bank size remains 4096 pending evidence and
  a recorded numerical amendment; no acceptance limit or pseudo-count changes.
- The diagnostic-only screen launched at 2026-09-05 16:43 UTC under
  `/data/codex/scratch/goal045-bank-convergence-20260906-ce368b3/`, tmux
  `ll-goal045-bank`, using frozen source `ce368b3`. Seven independent 4096-draw
  chunks extend the original bank in exact seed order; BLAS threads are capped
  at one. The initial receipt confirms `RUNNING` and all seven chunks started.
  The standalone ignored script `artifacts/goal045_execution/bank_convergence.py`
  saves the full bank before screening and validates hashes and seeds on reuse.
  Its category calculation and reduced predator profiles matched the accepted
  kernel; Ruff and strict mypy passed. Separate direct checks confirmed that
  16384/32768 bank sizes preserve all 250 calibration and 250 evaluation seeds.
- Current heartbeat `goal-045-completion-check` now follows the diagnostic
  `status`/`exit.status`/`run.log`, then resumes full joint numerical review.
  This launch does not modify production configuration or automatically start
  production. Detailed artifact paths and next-stage instructions are at the
  top of `HANDOVER.md`.
- The predator-marginal screen completed at 2026-09-05 16:50 UTC in 404 seconds.
  Checksums of the saved profiles and full bank were independently verified.
  Between 16384 and 32768 draws, the maximum LR change within the union LR<=10
  range was 0.35357 and the maximum generating-rho LR change was 0.18985; all
  fitted speeds were unchanged. Support components and domain-boundary contact
  agreed at cutoffs 5 and 10. In contrast, 8192 versus 16384 changed one
  generating-rho LR by 0.77669. These results support 16384 as the next candidate
  bank to test; they do not yet certify the joint predator-prey likelihood.
- The next check evaluates both 16384- and 32768-draw joint likelihoods across
  all 201 rho values, all 181 effects, and all four frozen timing histories.
  Independent rho rows use up to eight processes. Computing the full original
  grid avoids combining old-bank likelihoods outside a restricted window with
  new-bank likelihoods inside it. The additional 16384-draw midpoint check
  remains confined to the union LR<=10 windows plus neighbours. The original
  effect/rho MLE, profile/truth-LR and maximum-LL limits remain unchanged;
  rho support topology and endpoint movement are also inspected.
- The full joint check launched around 2026-09-05 18:40 UTC under
  `/data/codex/scratch/goal045-joint-bank-check-20260906-ce368b3/`, tmux
  `ll-goal045-joint`, and was initially verified `RUNNING`. It reuses the saved
  32768-draw bank and frozen source `ce368b3`. The standalone diagnostic's
  per-rho workers matched direct integration exactly for all 24 reduced
  history/case evaluations; known-effect halfsteps and topology failure checks
  also passed. Ruff and strict mypy passed. Original-grid surfaces are saved
  before refinement; final JSON distinguishes computational completion from
  numerical acceptance. The heartbeat now follows this check. Production
  configuration is unchanged pending the result.
- At 2026-09-05 19:15 UTC the full joint check completed in 2143 seconds. All
  24 original numerical and rho-topology checks passed. Its profile checksums
  and LR values were independently reconciled, along with no-effect
  factorisation against the predator-only screen. The accepted bank amendment
  above records the numerical result and preserved scientific settings.
- Production source `e8c08f10f7b67118a85ee37770d8ee48ee2c213a` was frozen and
  pushed after 18 focused tests, Ruff and strict mypy passed. Optional bank-cache
  loading validates exact seed list, site order, dimensions and checksum;
  tests established identical profiles to regeneration and rejected invalid
  metadata. The cache is exported from the verified 32768-draw bank prefix.
- Detached production launched at 2026-09-05 20:38 UTC under
  `/data/codex/artifacts/goal045-production-16384-20260906-e8c08f1/`, tmux
  `ll-goal045-production`. The initial receipt confirms `RUNNING`, stage
  `production`, correct source commit and successful 16384-draw cache loading.
  The preflight records accepted numerical evidence and a conservative 6.66-hour
  runtime estimate, including bank-generation cost that cache reuse eliminates.
  Eight workers run the frozen six cases with 250 calibration and 250 evaluation
  datasets per case. The heartbeat now follows this production root and resumes
  provenance/range checks, 1000-bootstrap synthesis and independent final review
  after completion. Numerical acceptance does not itself close the goal.
- Production completed successfully in 4500.9 seconds (75.0 minutes): 3492.7
  seconds integration, 504.3 calibration and 503.3 evaluation. All invariants,
  six cases, 250+250 histories, source and bank checksum were verified. The
  first two calibration/evaluation surfaces matched the accepted 16384-draw
  canaries within 1e-9. Profiles checksum:
  `f268bc56d437aa8978acf57a3e81944c26ebd51c71b4a70fc9a4de572a64b11b`.
- The provisional 1000-resample synthesis completed and its figures were
  inspected. Primary effect cutoffs were 2.665–4.613 (bootstrap upper bounds
  below 6), within the verified LR<=10 range. Calibrated rho cutoffs were
  44.02–44.82 at usual speed and 20.14–20.31 at half speed, extending beyond it.
  The saved 16384/32768 canaries differ by up to 1.027 LR at an interior node
  in that wider range. Observed-cutoff endpoints were unchanged; at bootstrap
  cutoff bounds only two endpoints moved, each by one G201 cell.
- Independent methodological review distinguished the original LR<=10 accuracy
  criterion from the wider-range review. It supports the primary effect
  comparison, but requires a bounded check of the actual reported rho quantities
  before closure: paired 16384/32768 predator-marginal recalibration across all
  250+250 histories, followed by full joint checks of calibration-rank and
  interval-boundary sentinels. The materiality criteria are cutoff movement
  <=0.5 LR, unchanged topology/boundary classification, endpoints and mean/median
  log-width movement <=one G201 cell, and coverage movement <=one dataset per
  case. This does not redefine the original LR<=10 criterion. A production
  rerun or bank escalation is warranted only if the reported quantities fail
  these checks. The automatic synthesis outcome label is not final acceptance.
- Actual production runtime made a full matched 32768-draw reference more
  proportionate than implementing a selected-history approximation. Independent
  methodological review endorsed this substitution: it gives exact paired
  comparisons of every calibration cutoff and evaluation support without
  sentinel-selection assumptions. The 16384 result remains the candidate;
  the reference is numerical sensitivity evidence, not independent replication
  or automatic replacement. No new biological histories are generated.
- The full reference launched at 2026-09-05 22:49 UTC under
  `/data/codex/scratch/goal045-full-bank-reference-20260906-e8c08f1/`, tmux
  `ll-goal045-reference`. Initial status was `RUNNING`; frozen source `e8c08f1`
  and successful 32768-draw cache loading were verified. Its wrapper checks
  full-bank and 16384-prefix checksums, identical 250+250 history seeds and
  the <=24-hour runtime boundary. It uses the existing campaign path, with
  `timing` marking a nonproduction numerical reference despite full ensemble
  sizes. The heartbeat follows this run and will compare complete paired
  outputs before final scientific review. The optional predator-only full-
  ensemble screen is no longer needed for closure and has not been launched.

- The complete 32768 reference finished successfully in 10749.6 seconds. All
  provenance, seed, event and retained-canary checks reconciled. Full paired
  comparison failed the recorded cutoff limit in usual_1 (+0.51923 LR) and
  usual_3 (+0.51608); other observed support criteria passed. The same
  calibration history 198 drives both failures. Primary effect contrasts and
  their interpretation are stable. See [numerical-review.md](numerical-review.md)
  and its compact JSON for the full diagnostic and paired bootstrap evidence.
- Independent methodological review supports retaining the G201 grid and
  explicitly reporting discrete-grid supports, with no continuum-endpoint
  claim. It recommends the prescribed full matched 65536 reference against
  32768. No bank promotion or acceptance-criterion change is authorized by the
  numerical result itself. The observed 32768 runtime gives a conservative
  next-run projection below nine hours, within the existing 24-hour boundary.
- The full 65536 reference launched at 2026-09-06 02:52:32 UTC under
  `/data/codex/scratch/goal045-full-bank-reference64-20260906-e8c08f1/`, tmux
  `ll-goal045-reference64`. Frozen-source/input checks passed and all eight
  4096-draw extension workers were verified running. The conservative runtime
  projection is 8.78 hours. The runner preserves the complete 32768 prefix,
  validates exact histories and profile hashes, saves its bank receipt before
  campaign execution, and does not promote any bank automatically. Python/Bash
  syntax and Ruff passed; a four-draw serial-versus-spawned-worker equivalence
  check passed locally and on deep-server. Both original four-history bank
  criteria and full-ensemble materiality criteria must pass before any 32768
  amendment. The active two-hour heartbeat now follows this reference.
- The 65536 reference completed at 2026-09-06 11:35 UTC, after 30965.1
  campaign seconds. All provenance checks passed, including direct verification
  of both bank prefixes. The original four-history bank canary passes all 24
  comparisons, but wider-range cutoff changes fail in all three usual-speed
  cases (+0.67085, +0.72610, +0.58645 LR). Other observed interval criteria pass.
  The primary contrasts remain stable; diagnostic pseudo-count dilution is too
  small to explain the tail shifts. Full evidence and a decision-grade audit
  are in [numerical-decision.md](numerical-decision.md).
- Independent scientific audit recommends an explicit human amendment: retain
  the original 16384 primary result with three-bank sensitivity and narrow
  claims, mark secondary rho calibration unresolved, and stop full-bank
  escalation. A 131072 replay projects to 25.34 hours under the same conservative
  rule and has not been launched. This recommendation does not itself amend
  the contract or complete the goal. The heartbeat is paused pending Barry.
- The report generator now distinguishes automatic synthesis classification
  from scientific acceptance, states actual ensemble sizes for reference runs,
  and explicitly describes discrete-grid supports. This is a presentation
  correction; campaign kernels, profiles, statistics and thresholds are unchanged.

- On 7 September Barry offered explicit authority for the projected 25.34-hour
  doubling on idle deep-server. Live checks confirmed negligible load and about
  123 GiB available memory. Independent audit reassessment supports one final
  65536/131072 comparison: two correlated nested increments do not establish
  persistent bias, and the next comparison has useful decision value under the
  unchanged gates. No promise of convergence is made.
- Preserve frozen source e8c08f1, all 250+250 histories, the complete 65536 bank
  prefix, G201/H181, rank 239 and every acceptance criterion. Both the original
  four-history canary and full-ensemble reported-quantity checks must pass
  before a documented 65536 candidate amendment. On any criterion failure,
  stop automatic doubling; no 262144 run or tolerance relaxation is authorized.
  Return the unresolved secondary-calibration decision for scientific review.
- A disjoint-half predator-only diagnostic uses existing first/second 32768 bank
  halves for calibration histories 198 and 221. It characterizes empirical bank
  variation only; it does not select favourable seeds or substitute for the
  full joint comparison. The final reference launch does not depend on the
  direction of that diagnostic. No new biological histories are introduced.
- The disjoint-half diagnostic completed before launch. At the generating rho,
  predator-marginal LR differences between the two 32768 halves were +1.37119
  (history 198) and +1.32924 (history 221), while the maximum near-peak profile
  changes within union LR<=10 were 0.33648 and 0.33273. Pooled 65536 truth LRs
  lie between the two halves. Hashes, seeds and prior diagnostic values reconcile.
  This supports empirical bank variability; it neither guarantees convergence
  nor alters the joint acceptance criteria. Compact evidence is in
  [half-bank-predator-diagnostic.json](half-bank-predator-diagnostic.json).
- The final 131072 reference launched at 2026-09-07 02:10:12 UTC under
  `/data/codex/scratch/goal045-full-bank-reference128-20260907-e8c08f1/`, tmux
  `ll-goal045-reference128`. Initial status is RUNNING; frozen inputs verified,
  projection 25.341 hours, and all eight 8192-draw extension workers started.
  Python/Bash syntax, Ruff, and four-draw serial/spawn equivalence passed both
  locally and on deep-server. The quiet two-hour heartbeat is active again.
