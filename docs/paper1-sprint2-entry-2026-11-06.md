# Sprint 2: entry repairs and qualification specification

**8 November pilot update.** Both historical compute-node cases now pass the
predeclared limited portability gate on clean candidate `99af520`. The
[evidence record](evidence/paper1-sprint2-pilot-2026-11-08/README.md) preserves
measured costs, exact comparison scope and the first 260-site walltime failure.
Target fit wall times were 4578.981 seconds (120 sites) and 33499.084 seconds
(260 sites); the latter used 22805.725 CPU seconds. These are historical
portability diagnostics. Fresh observation qualification and training have not
run. Bank resources and multi-node throughput remain to be measured. This
update supersedes the access/PBS status at the original stopping point below;
the scientific gates and numerical method remain unchanged.

Sprint 2 advances charter pillars 3, 4 and 6 under the
[reviewed sprint envelope](paper1-sprints-2026-11-05.md). The entry source is
`583c1e3`, incorporating Claude's handover in message 2906. Entry review found
material numerical, execution and design gaps. Sprint 1 supplies a substantial
candidate; it has not yet supplied an accepted qualification or a measured PBS
pilot. Validation remains closed. No qualification or rule-training history has
been generated in this turn.

## Decisions before fresh outcomes

Retain the complete tight replay, all eight interval cutoffs, all three fitted
families, and all six training truths. Removing replay and reducing histories
remain unaccepted cost proposals. A target-host pilot will measure the complete
procedure before those proposals are reconsidered.

The normalised eigenvalue floor is accepted algebraically. The criterion is a
**regularised Laplace composite score**, with
`f(x)=(x+0.1*exp(-10*x))/(1+0.1*exp(-10))`. It has the exact zero-variance limit;
it is not the unmodified Laplace determinant. No inference about exact-integral
fidelity or global latent optimality follows from this acceptance.

The outer solver must actually pass its numerical second-order check. A small
projected gradient alone cannot rescue failed saddle escape, exhausted escape
attempts or unavailable curvature. Independent review reproduced a stationary
minimum incorrectly reported as successful, then verified bounded backtracking
and strict rejection. Both spatial and reduced constant-family eligibility now
require that certificate. The score itself is unchanged. Original replay
receipts remain historical diagnostics and must be rerun on the repaired source.

Execution failures must survive every root/search/family wrapper as execution
failures. Unavailable reduced-family intervals cannot be reported as resolved.
Campaign reconciliation separates scientific failures from execution losses;
only the latter may retry with unchanged identity. Every attempt retains its
logs, partial output and source/input hashes. A scheduler exit alone is not a
scientific result.

## Prospective qualification amendment

This records a pre-outcome amendment to Sprint 1's qualification packet, not a
change to the completed development challenge. Its 207 arm datasets comprise
162 base, 18 boundary, 18 enriched and nine trend cases. The 162 base cases are
54 paired biological histories across nine maps. This finite challenge replaces
the older provisional 600-case design; it does not estimate a tightly bounded
population failure probability across arbitrary maps.

Keep the original numerical acceptance score
`mean(p_map)+t(.95,8)*sd(p_map)/3 <= .05`, together with
`max(p_map) <= .25`, where each `p_map` uses all 18 registered base arm datasets.
Call it an **empirical finite-panel acceptance score**, never a 95% upper
population bound. It is zero after zero observed failures, which is why that
population interpretation is invalid. All raw map, archetype, arm and stratum
denominators remain visible. The A/B-only continuation is permitted only if all
base failures are in C and the same rule passes on A/B, using 12 cases per map.
It does not qualify C.

Qualification cannot pass on missing, invalid or indeterminate evidence.
Execution losses are reconciled and retried, not counted as successful cases.
Scientific failures are retained. Boundary/enriched/trend failures remain
separate from the base denominator and block training for diagnosis; a demonstrated
procedure defect cannot be ignored because the base score passes. A substantive
repair after outcomes invokes the existing one-repair/new-panel branch. There
are no fresh outcomes at the time of this amendment.

### Bank identities

For each qualification map, use independently addressed primary and comparison
banks with explicit replicate IDs 0 and 1, each of size 131,072, compression
order 192 and the unchanged empirical-plus-seven-pseudo law. Freeze the complete
seed recipe in the generation manifests. Reconstruct both seed arrays, reject
any overlap, verify all payload hashes and reject identical raw or compressed
banks. A different output directory or nested prefix is not an independent bank.
The manifest flags 18 biological histories (54 arm datasets) for this comparison.

### Numerical comparisons

Compare spatial standard and tight profiles, exposure and constant profiles.
Use each run's own frozen free score to normalise `W=2*(free-profile)`; do not
compare raw bank-dependent score offsets. Evaluate both runs on the exact union
of their retained nodes, free locations, cutoff roots and domain endpoints.
No interpolated score is accepted. Additional probes are diagnostic: a higher
candidate that invalidates a frozen free maximum or set is a nonpassing check,
not permission to silently replace the original result.

Require every one of the eight sets to be available. Match all ordered roots
and components, set classes, singleton flags and domain contacts. Compare free,
root and inside-set nuisance contacts using the accepted pointwise tie rule.
Dense/lean limits are 0.01 in W and 0.005 in log-h endpoints; independent-bank
limits are 0.10 and 0.05. The packet did not define its tangency exemption
operationally. Remove that exemption prospectively: any topology mismatch is
nonpassing, with near-tangent cases described separately. Do not invent a
waiver after observing which cases fail.

At the selected spatial free family, compare the analytic gradient against
reoptimised-mode finite differences in every fitted coordinate for dense/lean
and standard/tight. Use steps `1e-4` and `3e-5` times `max(1,abs(theta))`, central
inside bounds and second-order inward at a bound. Require each estimate to agree
with the analytic derivative within `1e-5+1e-4*max(abs(analytic),abs(fd))`.
Do not project away nonzero boundary derivatives. Missing/nonfinite stencils
are indeterminate, not passes.

The 18 flagged exhaustive-audit cases retain the original all-location audit.
A distinct converged mode at a production-skipped location with score gain
above 5 blocks training and requires reviewed repair/fresh qualification. The
subset is an empirical check, not a bound on every omitted location. Preserve
the nine capped importance screens as descriptive evidence, including
indeterminate results. Record high-sigma-anchor envelope-guard failures by
candidate source.

## Training remains a separate gate

The 30-map development allocation and six-truth 200/100 history plan are retained
as proposals. The exact map-population upper-bound estimator used to select
cutoffs, forecasting model/targets/scoring, bootstrap selection and temporal
stress allocation still need an executable specification before training.
Neither compute availability nor a passing numerical panel supplies these.

The independent design review supplies a distribution-free KL-bound option,
not an adopted rule. With ten independent maps per archetype, even all-zero
map error fractions give a 95% upper bound of 0.259 under that option; 59 maps
are the minimum to get below 0.05 at zero. Thus a large number of histories on
ten maps does not establish an arbitrary-map 5% error guarantee. Before
training, review the scientific tradeoff between more maps, justified model
assumptions/approximate inference, and a legitimate negative training result.
Do not silently select the interval method that makes the existing allocation
pass. The integrated protocol's map-population target and six-truth claims
remain unchanged.

The reach-threshold intervention T remains the proposed planning-only nonlinear
stress. Correct its justification: perfect Spearman correlation does not imply
linear dependence or a numerically zero residual from regression on [1,A].
Choosing the threshold stress is a substantive intervention choice, not a
mathematical consequence of that correlation. No stress history has been used
to select it in this turn.

A geometry-only check on the existing connected-0, corridor-0 and barrier-0
development maps finds Spearman correlation **-1**, rather than the packet's
+1, and raw-arrival linear residual SDs of 4.05, 5.57 and 20.98 days
(13.3%, 19.8% and 28.5% of the original SD). These are not numerical noise.
The [reproduction script](evidence/paper1-sprint2-2026-11-06/check_planning_residual.py)
uses no observations or validation maps; its JSON preserves the values.

## Execution and evidence

Independent entry reviews are in
[evidence/paper1-sprint2-2026-11-06/](evidence/paper1-sprint2-2026-11-06/).
The implementation and fabricated-receipt tests must pass before a frozen
candidate is used. A target-host pilot on historical diagnostic cases comes
before fresh qualification; pilot-driven changes cannot borrow qualification
histories and still call them untouched evidence.

The documented cluster route has no reusable authenticated connection, and its
login attempt closed before authentication. Barry has been asked to open the
portal SSH-access window. No PBS job has been submitted. Local tests and repairs
continue independently of that access requirement.

## Operational runbook: frozen qualification campaign

**Status: the commands below have not been run on the cluster.** Access, queue
policy, image availability, container bindings and PBS execution remain untested.
Complete the runtime preparation and a compute-node pilot on historical diagnostic
cases before generating any fresh qualification history. Freeze the reviewed
candidate and pilot-derived resource settings first. The paths below are project
variables, not access instructions.

### Stage the source, maps and runtime

Set `LL_REPO` to the clean, pinned source checkout; `LL_COMMIT` to its full reviewed
commit; `LL_DATA_ROOT` and `LL_WORK_ROOT` to the project's absolute data and work
directories. Stage the nine existing qualification maps under
`$LL_DATA_ROOT/maps/qualification`. The producer checks their records and payload
hashes against the frozen manifest. Do not stage or generate validation maps.

Set `LL_IMAGE_URI` to a verified OCI digest (`docker://…@sha256:…`), using an image
that supplies Python 3.12, uv and Git. Set the runtime preparation resource values
in accordance with the live queue policy. These variables must be exported; use
paths without commas because PBS `-v` separates assignments with commas.

```sh
: "${LL_REPO:?absolute pinned source checkout}"
: "${LL_COMMIT:?full reviewed commit}"
: "${LL_DATA_ROOT:?absolute project data directory}"
: "${LL_WORK_ROOT:?absolute project work directory}"
: "${LL_IMAGE_URI:?digest-pinned OCI image}"
: "${LL_RUNTIME_NCPUS:?runtime preparation CPU request}"
: "${LL_RUNTIME_MEMORY:?runtime preparation memory request, for example 8gb}"
: "${LL_RUNTIME_WALLTIME:?runtime preparation walltime request}"
LL_IMAGE="$LL_WORK_ROOT/runtime.sif"
LL_RUNTIME_RECEIPT="$LL_WORK_ROOT/runtime.json"
LL_PLANS="$LL_WORK_ROOT/plans"
LL_RESULTS="$LL_DATA_ROOT/task-results"
LL_MAPS="$LL_DATA_ROOT/maps/qualification"
LL_PYTHON="$LL_REPO/.venv/bin/python"
export LL_REPO LL_COMMIT LL_DATA_ROOT LL_WORK_ROOT LL_IMAGE_URI
export LL_IMAGE LL_RUNTIME_RECEIPT
mkdir -p "$LL_WORK_ROOT/logs" "$LL_PLANS" "$LL_RESULTS"
cd "$LL_REPO"
qsub -N ll_runtime \
  -v "LL_REPO=$LL_REPO,LL_COMMIT=$LL_COMMIT,LL_IMAGE=$LL_IMAGE,LL_IMAGE_URI=$LL_IMAGE_URI,LL_RUNTIME_RECEIPT=$LL_RUNTIME_RECEIPT" \
  -l "select=1:ncpus=$LL_RUNTIME_NCPUS:mem=$LL_RUNTIME_MEMORY" \
  -l "walltime=$LL_RUNTIME_WALLTIME" -o "$LL_WORK_ROOT/logs" \
  scripts/pbs/prepare_runtime.pbs
```

The preparation script refuses existing SIF and receipt targets. It builds the
SIF once, installs the frozen dependency lock, checks source identity and package
imports inside the container, and writes the **actual** SIF checksum and runtime
identity. It does not predict the checksum of an Apptainer conversion. Preserve
an unsuccessful preparation's files; use fresh target names for a diagnosed
rerun. Skip preparation for an already verified runtime: the producer rechecks
its source, lock and SIF hash. A successful scheduler exit without the runtime
receipt is insufficient.

After that receipt and the historical pilot have been checked, use this shell
helper for preparation, reconciliation and explicitly allocated-node work:

```sh
export APPTAINERENV_LL_EXECUTION_CONTEXT=apptainer
export APPTAINERENV_LL_RUNTIME_SIF_SHA256="$(sha256sum "$LL_IMAGE" | awk '{print $1}')"
ll_python() {
  apptainer exec --bind "$HOME,$LL_REPO,$LL_DATA_ROOT,$LL_WORK_ROOT" \
    "$LL_IMAGE" "$LL_PYTHON" "$@"
}
ll_prepare() {
  ll_phase=$1
  ll_plan_name=$2
  shift 2
  ll_python scripts/prepare_sprint2_campaign.py "$ll_phase" \
    --maps-root "$LL_MAPS" --results-root "$LL_RESULTS" \
    --runtime-receipt "$LL_RUNTIME_RECEIPT" --source-commit "$LL_COMMIT" \
    --python "$LL_PYTHON" --execution-context apptainer \
    --output-dir "$LL_PLANS/$ll_plan_name" "$@"
}
```

Every preparation writes a new `plan.json`, `tasks.jsonl` and
`qualification-index.json`. Existing plan directories are refused. Missing or
invalid dependencies produce explicit pending entries, not fabricated success.
Do not submit an empty task list. If a phase was prepared before its dependencies
completed, prepare a new named plan after reconciliation and retain the earlier
one; do not edit a frozen task or silently replace a failed scientific result.

### Prepare and execute each phase

| Phase | Full task count | Dependencies |
|---|---:|---|
| banks | 18 | nine frozen maps; replicates 0/1, K=131072, order 192 |
| histories | 207 | nine frozen maps; registered addresses and observation arms |
| fits | 486 | verified banks and histories: 414 dense/lean, 54 independent-bank lean, 18 exhaustive lean |
| audits | 468 | resolved prerequisite fits: 261 common-anchor pairs and 207 gradient checks |
| integration | 9 | verified lean receipts, including terminal scientific failures |
| index | 0 | all available verified phase receipts |

The audit count is the all-resolved maximum. A scientific fit failure remains in
the denominator and index; its unavailable derived checks are handled explicitly
by the reducer. An execution loss remains incomplete until recovered. Integration
outcomes are descriptive and are retained even when indeterminate or unavailable.

For each phase, set `LL_WORKERS`, `LL_CHUNK`, `LL_MEMORY` and `LL_WALLTIME` from the
pilot. Each array subjob requests one node; `LL_WORKERS` is the number of independent
single-threaded workers within that allocation, and `LL_CHUNK` is the number of
tasks assigned to that subjob. Bank tasks themselves use one worker. Verify the
array size and simultaneous allocation against current queue/account policy.

```sh
ll_submit() {
  : "${LL_WORKERS:?measured workers per node}"
  : "${LL_CHUNK:?measured tasks per array subjob}"
  : "${LL_MEMORY:?measured memory per subjob}"
  : "${LL_WALLTIME:?measured walltime per subjob}"
  ll_task_file="$LL_PLANS/$1/tasks.jsonl"
  ll_task_count=$(wc -l < "$ll_task_file")
  test "$ll_task_count" -gt 0 || return 1
  ll_last_index=$(( (ll_task_count + LL_CHUNK - 1) / LL_CHUNK - 1 ))
  qsub -N "ll_$1" -J "0-$ll_last_index" \
    -v "TASKS=$ll_task_file,OUT=$LL_RESULTS,CHUNK=$LL_CHUNK,LL_WORKERS=$LL_WORKERS,LL_REPO=$LL_REPO,LL_IMAGE=$LL_IMAGE,LL_DATA_ROOT=$LL_DATA_ROOT,LL_WORK_ROOT=$LL_WORK_ROOT" \
    -l "select=1:ncpus=$LL_WORKERS:mem=$LL_MEMORY" \
    -l "walltime=$LL_WALLTIME" -o "$LL_WORK_ROOT/logs" scripts/pbs/array.pbs
}
ll_reconcile() {
  ll_python scripts/pbs/campaign.py reconcile \
    --tasks "$LL_PLANS/$1/tasks.jsonl" --out "$LL_RESULTS"
}

ll_prepare banks banks
ll_prepare histories histories
ll_submit banks
ll_submit histories
```

After the corresponding scheduler work finishes, inspect its logs and reconcile
both phases. Reconciliation verifies task identities and saved artifacts; exit
zero means that execution evidence is complete, not that scientific checks pass.
It writes `$LL_RESULTS/_reconcile.json`, which is replaced by each reconciliation;
copy that derived summary into the phase plan directory when retaining a snapshot.
All attempt receipts and outputs remain separately preserved.

```sh
ll_reconcile banks
ll_reconcile histories
ll_prepare fits fits \
  --dependency-plan "$LL_PLANS/banks/plan.json" \
  --dependency-plan "$LL_PLANS/histories/plan.json"
ll_submit fits
```

After fit execution and reconciliation, prepare both forms of diagnostics. Their
inputs come only from verified attempts matching the frozen dependency plans.

```sh
ll_reconcile fits
ll_prepare audits audits \
  --dependency-plan "$LL_PLANS/banks/plan.json" \
  --dependency-plan "$LL_PLANS/histories/plan.json" \
  --dependency-plan "$LL_PLANS/fits/plan.json"
ll_prepare integration integration \
  --dependency-plan "$LL_PLANS/banks/plan.json" \
  --dependency-plan "$LL_PLANS/histories/plan.json" \
  --dependency-plan "$LL_PLANS/fits/plan.json"
ll_submit audits
ll_submit integration
```

### Recover execution losses, then build the final index

Use the same frozen task file and original chunk size. On an allocated compute
node, rerun only the affected array slice with `--retry-failed`; this skips both
resolved tasks and terminal scientific failures. Every retry receives a new
attempt directory, preserving the earlier logs and scientific artifacts. A task,
source, runtime or input change is rejected rather than treated as a retry.

```sh
: "${LL_RETRY_PLAN:?phase plan directory name}"
: "${LL_RETRY_INDEX:?zero-based affected array index}"
(
  unset PBS_ARRAY_INDEX APPTAINERENV_PBS_ARRAY_INDEX
  ll_python scripts/pbs/campaign.py work \
    --tasks "$LL_PLANS/$LL_RETRY_PLAN/tasks.jsonl" --out "$LL_RESULTS" \
    --chunk "$LL_CHUNK" --index "$LL_RETRY_INDEX" --workers "$LL_WORKERS" \
    --retry-failed
)
ll_reconcile "$LL_RETRY_PLAN"
```

Do not run this fitting command on a login node. An invalid receipt or changed
artifact requires diagnosis; deleting the evidence to force a rerun is not a
recovery method. The array template currently has no retry flag, so the command
above is the explicit worker invocation for an allocated retry session.

After audit and integration work is reconciled, produce a fresh index and reduce
it. Reusing the earlier pre-execution index would leave its references missing.

```sh
ll_reconcile audits
ll_reconcile integration
ll_prepare index final-index \
  --dependency-plan "$LL_PLANS/banks/plan.json" \
  --dependency-plan "$LL_PLANS/histories/plan.json" \
  --dependency-plan "$LL_PLANS/fits/plan.json" \
  --dependency-plan "$LL_PLANS/audits/plan.json" \
  --dependency-plan "$LL_PLANS/integration/plan.json"
ll_python scripts/summarise_sprint2_qualification.py \
  --panel docs/evidence/paper1-sprint1-2026-11-05/qualification-panel.json \
  --index "$LL_PLANS/final-index/qualification-index.json" \
  --output "$LL_PLANS/final-index/qualification-summary.json"
```

The reducer preserves numerical failures and the nine descriptive screens. Its
output does not authorise rule training; the separate training-design gate above
still applies.

### Interpret timing and memory receipts

`wall_seconds` covers the task attempt's source/input checks, subprocess execution
and output hashing, excluding queue delay and final receipt writing. `cpu_seconds`
is the difference in the worker's `RUSAGE_CHILDREN` user-plus-system counters:
it includes the task subprocess and source-check Git subprocesses completed in
that interval, but excludes the worker's own hashing/bookkeeping CPU. Taking a
difference avoids accumulating previous tasks' CPU time when a worker is reused.

`worker_children_peak_rss_bytes` is deliberately **not** a per-task memory value:
it is the lifetime maximum across completed children of that reused worker. It
cannot be subtracted between attempts or summed to estimate node memory. Use the
fresh fit subprocess's `cost.peak_rss_bytes`, together with measured simultaneous
node usage, for worker packing. Bank child-process memory also needs a live
concurrency measurement. No scheduler/runtime or scaling claim is made from the
local tests.

## Verification and present stopping point

The final source/test suite passes **1,259 tests, with three skips**
(`.venv/bin/python -m pytest -q`, 212.42 seconds). Scoped Ruff checks pass;
strict mypy with imported modules followed silently passes for the eight changed
numerical/audit modules. Both PBS scripts and all seven runbook shell blocks
pass shell syntax checks. The qualification producer's read-only manifest check
verified all nine staged maps and all 207 frozen rows. No observation was
simulated by that check. The focused campaign, reducer and audit tests use
fabricated evidence and deliberately failed attempts.

Two historical 120-site datasets were rerun concurrently with one numerical
thread each. Both resolve through the complete dataset entry point, retain
all three families and all eight cutoffs, and show no latent-mode or anchor-guard
flag. The results are **diagnostic evidence only**:

| Dataset | Wall seconds | CPU seconds | Peak process memory, bytes |
|---|---:|---:|---:|
| cell-00-rep-005-arm-B | 956.922 | 955.581 | 747454464 |
| cell-06-rep-006-arm-B | 920.468 | 919.257 | 747520000 |

The precise values, input/source hashes and receipt paths are in
[diagnostic-replay.json](evidence/paper1-sprint2-2026-11-06/diagnostic-replay.json).
[diagnostic-source.patch](evidence/paper1-sprint2-2026-11-06/diagnostic-source.patch)
reconstructs the run's exact source from `583c1e3`; all 115 recorded source
hashes were verified independently, together with parent/child receipts and
evaluation streams. Source bytes remained unchanged during both runs. Subsequent
changes to `fit_dataset.py` add reduced-profile parameters/source labels and
required input-path metadata, and fix type annotations; they do not change
numerical computation. The stored receipts are never relabelled as clean-commit
qualification runs. Remaining historical histories and the 260-site case await
the target pilot.

To replay the two diagnostic cases, reconstruct that source in a separate
checkout, restore the hash-matched input artifacts referenced by the JSON,
install `uv.lock`, and invoke `scripts/fit_dataset.py` with the archived public
input directory, each case's observations, raw arrival bank and compressed bank.
The exact original arguments and logs remain with
`artifacts/sprint2/entry-replay-20261106/summary.json`; the existing Sprint 1
`replay_fit_dataset.py` records the same input locations and can rerun all six
historical cases. Use a new output directory, never overwrite the evidence.

The numerical, execution and design delegates reviewed disjoint work and
cross-reviewed substantive repairs. The parent reviewed the common-anchor
producer and integrated its reduced-family serialization. The design reviewer
checked producer/reducer interfaces and independently audited replay provenance.
These reviews are recorded in the evidence directory, preserving their initial
findings and subsequent acceptance conditions.

Sprint 2 remains in progress. Access has not been restored and no PBS job has
been submitted. The runtime/container pilot, fresh qualification and training
are still outstanding. Training additionally requires the reviewed executable
specification above. The scientific repair allowance and validation boundary
are unchanged. Correspondence message 2916 records this status and the response
to Claude's handover.
