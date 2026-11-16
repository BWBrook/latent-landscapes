# Registered real-task interrupted twin

16 November 2026. This implements the additional check accepted in board
message 3491. It runs alongside the 51-fit replay and gates a fresh
qualification panel; it does not hold up that replay or re-score the
15 November failure. Training and validation remain closed.

The numerical candidate remains
`432bb6e56e672f9e57f2f7bc369546023b07662e`. The separate
[execution observer/controller/comparator](../../../scripts/run_interrupted_twin.py)
is frozen at SHA256
`85dd7c5d4b8859d158fb0a4d98e2e9cf92bfe16c57e60e222ed96ef20aecba1e`.
It is staged outside the pinned checkout and never changes the numerical
source files. Its [27 focused tests](../../../tests/test_interrupted_twin.py)
have SHA256
`2535b4ab841b2c9288ba41a1111392262cb8776c6828234fedf4fd2a78ac71ff`.
Ruff and focused Mypy pass. These local scheduler tests use mocks; no
target interruption or real equivalence result is claimed by this plan.

## Fixed selection

The selected task is
`fit-q-base-connected-1-matched_exposure-mu0.001-h1-A-exhaustive`.
It is the shortest of the 24 non-regression tasks by the recorded completed
A+B+C task `wall_seconds`, with lexicographic task ID breaking any exact tie.
All 24 task records and bound fit receipts are inspected, not just the winner.

- Frozen selection SHA256:
  `099f28d9a45a8a4eb12b103ddaf23714ed3ced72120bb5c9184c9c75e514dfaf`.
- Prior task wall time: `6358.104871034622` seconds; the fit itself took
  `6325.417826866731` seconds. These are different timing scopes.
- Prior A+B+C task-record SHA256:
  `6cd0bca17a26791e0e1d81d38f9ab38a43844964c20df33e6274087cab51ace4`.
- Prior fit-receipt SHA256:
  `8e741c85eddccae6d1ee05def18fefd107c5f133c2c5b292e13219e5dfe42a22`.
- The complete 24-row selection plan is generated under the ignored execution
  directory, at SHA256
  `09b627de8e09f26c8e0bf0da556d8aa2d2bac5b57d1d4c4b7a1096a0b9d62207`.
  The harness refuses any different plan, source, selection or segment count.

The exact same task is also the shortest in the earlier original-candidate
receipt set; choosing the latest completed task wall time does not change
the selected dataset. The new data, bank, runtime, model flags and numerical
budgets are those of its source task in the 51-fit plan.

## What the two interruptions establish

There are three total twin attempts, each capped at 48 hours, in a separate
output tree with a stable checkpoint directory. The reference is the
selected task's uninterrupted first attempt in the 51-fit replay. If that
reference itself uses a second attempt, this comparison refuses to call it
an uninterrupted reference; it does not silently substitute one.

The first twin attempt is deleted while search is active. A narrow observer
calls the original `_fit_family` without changing its arguments or result.
After at least one completed, hash-bound search operation exists, the next
actual family solve must return candidates with at least one recorded
evaluation. The observer then waits inside that unfinished search operation,
before the operation can persist its new result. The proof records active
search frames, the durable prior operation count/hash, real evaluation count,
task/runtime/checkpoint identity and worker native job ID. Resume must reuse
the prior completed operation and repeat the unfinished one faithfully.

The second attempt is deleted inside the actual latent-audit loop. The exact
shortest task's enclosing latent-audit stage lasted only `0.001359790563583374`
seconds (the audit loop itself recorded `0.0010651256889104843` seconds) and
performed **zero numerical mode audits**: all 142 retained locations had
sigma at the existing floor and failed the audit's variance threshold. An
external timed poll therefore cannot reliably catch that stage. The observer
calls the original `latent_audit` for each location, unchanged, and waits
after half the actual calls have returned, before returning that call's
result to `audit_all`. For the retained 142-call traversal, this is call 71.
The proof records its actual ordinal/total, sigma and `performed` result.

This is a real data-driven **audit-loop and stage restart** check. It is not
an interruption of a numerical latent-mode solve, and it does not claim to
test partial numerical-audit state that this task never produces. Selection,
sigma threshold, audit starts and the solver are not altered to manufacture
such work. The actual new traversal count/result is retained in the proof.

The observer wraps `Run.stage`, `_fit_family`, `audit_all` and `latent_audit`
only to observe active frames, count genuine calls and provide the two
bounded rendezvous. It always delegates numerical work with the original
arguments and returns the original results. The third attempt uses the
same observer wrappers with waiting disabled and must finish normally.

## Native deletion and identity guards

The three workers are normal single PBS jobs named `ll_tw_s1`, `ll_tw_s2`
and `ll_tw_s3`, with native `afterany` dependencies. They invoke the frozen
campaign worker with explicit task index zero, one worker and retry enabled;
the immutable twin task retains the three-attempt cap. All jobs are registered
while held, before release. The external controller is a separate native
job named `ll_tw_ctl`, using the verified native Python module rather than
trying to execute host PBS tools inside the model container. Its wall-time
and wait budget is 12 hours. The model workers and comparator retain the
original pinned interpreter/SIF; the workers' caps remain 48 hours each.

The parent releases the controller first. After registration/source and native
controller name/running-state/current-owner checks, it atomically seals
`controller-ready.json`, binding its native job ID, registration SHA256, owner,
source, observer bytes and raw initial native status. The parent requires that
ready record and a fresh native running-state check before releasing worker 1.
The controller's scheduler state alone does not establish successful bootstrap.
This handshake prevents a failed or delayed controller startup from consuming
the worker's ten-minute interruption rendezvous.

The registration binds the exact plan, observer bytes, source task, cloned
twin task, source task file, twin task file and all four native job IDs.
Scientific model arguments, data/runtime identities and numerical source remain
fixed. The outer argv/metadata additionally name the observer, plan, control
directory and their hash bindings; the outer twin ID and output/checkpoint
storage are separate. The task dictionaries are not otherwise claimed identical.
The controller is forbidden from naming one of the workers as itself.

Before each `qdel`, the controller requires the native controller to be
running under the expected name and current account, and the target worker
to be running with the exact registered ID/name and controller owner. It
checks a fresh, sealed worker heartbeat, the active stage/progress, the
checkpoint identity and the durable prior-operation hash. It records the
deletion intent before requesting cancellation. A completed target stage,
stale/mismatched marker, wrong owner or changed source/task bytes refuses
deletion. The controller calls `qdel` only for that registered worker ID.

The worker stays at the rendezvous for at most ten minutes. Failure to delete
it causes a harness execution abort, not normal scientific completion. The
controller requires successful native `qdel` and matching terminal, nonzero
PBS accounting, retaining raw before/after/controller output and hashes.
The next worker waits for the preceding deletion confirmation, bound to the
same registration and native ID, before model work begins.

## Exact comparison

The comparator verifies the complete safe output inventories, every listed
raw hash, root/attempt task-record equality and the nested search/event hashes
before reading their scientific contents. It checks:

- The reference has exactly one attempt and is the original 51-plan task.
- The twin has exactly three attempts, with no final fit receipt in the first
  two deleted attempts, and the third task record names the registered third
  native job.
- Both source tasks retain identical original model arguments and runtime.
- Baseline and resumed checkpoint source/input/runtime identities agree.
- Both native cancellations, the controller's completion and the third
  worker's completion have matching registered provenance.

It then compares the fit receipt, nested search receipt and complete event
stream under exactly the pinned
`fit_checkpoints.scientific_payload` and canonical digest. There is no new
numeric tolerance and no additional excluded field. Scientific counters,
candidate rows, gradients, eligibility and classifications must match exactly.
Raw provenance and timing-bearing files remain separately hashed. The result
receipt has `status: passed|failed`, the candidate source commit, all raw and
scientific hashes, interruption proofs and the explicit audit limitation.
An execution/identity error is a failed gate, not a successful equivalence
result. A matched scientific failure does not itself qualify the candidate;
the full replay still supplies its own acceptance outcome.

## Execution interface

Infrastructure values and native job IDs belong in the ignored execution
record, not this public plan. Parent orchestration uses these commands, with
the model commands inside the pinned runtime and the controller on the host:

```sh
python "$HARNESS" select --selection "$SELECTION" \
  --prior-results "$PRIOR_RESULTS" --output "$PLAN"
python "$HARNESS" prepare --plan "$PLAN" --source-tasks "$FIT_TASKS" \
  --repo "$PINNED_REPO" --control-dir "$CONTROL" --output "$TWIN_TASKS"
python "$HARNESS" register --plan "$PLAN" --source-tasks "$FIT_TASKS" \
  --twin-tasks "$TWIN_TASKS" --control-dir "$CONTROL" \
  --jobs "$SEARCH_JOB" "$AUDIT_JOB" "$FINAL_JOB" --controller-job "$CONTROL_JOB"
python "$HARNESS" controller --control-dir "$CONTROL" \
  --qstat /opt/pbs/bin/qstat --qdel /opt/pbs/bin/qdel --timeout-seconds 43200
python "$HARNESS" compare --control-dir "$CONTROL" --repo "$PINNED_REPO" \
  --baseline-record "$BASELINE_RECORD" --twin-record "$TWIN_RECORD" --output "$RESULT"
```

The worker command is generated in the immutable twin task; it is not a
separate scientific argv chosen after an outcome. Native controller setup,
dependencies, actual interruptions and final equality remain target evidence
to be collected. No target job, cancellation or numerical fit was performed
while preparing this harness.

Next: Codex — independently review and stage the frozen twin harness alongside the accepted replay.
