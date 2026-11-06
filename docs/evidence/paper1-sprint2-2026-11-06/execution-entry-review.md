# Sprint 2 execution and provenance entry review

Reviewed candidate: `583c1e3`, including analysis source `48de534` and the Sprint 1 packet. Scope: batch execution, recovery, bank identity, error handling and the reported replay receipts. Numerical-method and experimental-design acceptance are separate reviews. No remote operation, fit, fresh history or validation access was performed.

**Entry verdict: the handed-over driver was not ready for qualification.** The execution repairs below are implemented and pass local checks. Parent review, the remaining entry-point repair and a compute-node pilot are still required before campaign launch.

## Findings and repairs

1. **Execution errors were silently terminal on resume.** Original `fit_dataset.py:850–852` exits zero after writing any result, including `execution_error`. Original `scripts/pbs/campaign.py:51–56,102–115` skipped/reconciled solely by process exit code. A small actual driver probe wrote an `execution_error` receipt, exited zero and was skipped even with `--retry-failed`. The revised driver reads the explicitly expected result schema, distinguishes resolved results, scientific failures and execution losses, and retries only the last category. Scientific failures remain terminal even when retry is requested.

2. **Reduced-family resource errors became scientific failures.** In the original `fit_dataset.py:787–797`, `Run.stage(..., guard=False)` rethrows without recording an error, and the outer handler records every exception as `family_fit_failed`. A mocked entry-point call making each reduced family raise `MemoryError` returned `family_fit_failed` with an empty `errors` list. Parent owns this entry-point repair. It affects denominators and retry eligibility and must be corrected before outcomes.

3. **Resume accepted different tasks and missing scientific outputs.** Original `campaign.py:51–56` trusted any `_task.json` with exit zero. Probes confirmed that changed argv and a deleted result were both skipped. The revised task contract freezes argv, expected commit, input/runtime hashes, result path and schema. Resume and reconcile verify the task digest and saved output hashes; changed/missing evidence is rejected. Source and inputs are checked before and after execution. Each attempt has a pre-launch identity receipt, so interrupted attempts cannot be reassigned to a changed task.

4. **Failed attempts lost logs and could not safely resume actual fits.** Original retry kept only `_task.N.json` while truncating `_stdout.log` and `_stderr.log`; actual analysis/generation entry points refuse existing output directories. The revised driver creates `attempt-0001`, `attempt-0002`, etc., retaining every attempt's inputs descriptor, logs, result and task receipt. Commands explicitly put scientific outputs under `{attempt_dir}/result`; task logs live at the attempt root. Spawn errors and zero exits without an expected result now receive execution-failure receipts. An interrupted attempt requires an explicit retry.

5. **The new-map bank builder could not supply an independent replicate.** Original `generate_history.py:184–192` keyed every bank solely by map and row; no CLI argument changed the bank identity. Repeating construction for a map reproduced the exact same seed array, and increasing its size merely extended it. Bank generation now requires an explicit nonnegative `--bank-replicate`. The new seed rule and `sprint2-map-arrival-bank-v1` manifest record replicate and seed hash. These are prospective new banks; historical Sprint 1 banks are unchanged. `verify_independent_banks(left_manifest, right_manifest)` requires the same map, equal sizes, independently reconstructed/disjoint seeds, correct payload hashes and nonidentical payloads. The qualification orchestrator must call this helper before admitting a comparison.

6. **Runtime and worker allocation were insufficiently pinned.** Original `prepare_runtime.pbs:18` pulled a mutable image tag and silently reused an existing SIF; `array.pbs:21` could silently select one worker if `NCPUS` was absent. The templates now require a digest-pinned image URI, staged SIF checksum, full source commit and explicit `LL_WORKERS`, and explicitly bind source/task/output locations. Task inputs must include the frozen SIF and dependency lock. This is local template validation only: queue limits, worker/resource agreement, filesystem visibility and measured throughput remain compute-node pilot requirements. A SIF checksum must be obtained from the staged immutable image; it must not be guessed from a fresh conversion.

## Evidence checked

- Reconstructed all six rows of `replay-fit-dataset.json` from their local raw receipts using its existing summariser: exact equality, including receipt SHA-256 values. All six record clean source `48de534af82b658157af32ce01d18e407b3ddc3c`.
- The arm-C raw receipt also records that clean source, `resolved`, and 5055.20815416699 wall seconds. These are verified local retrospective results, not qualification or cluster-cost evidence.
- Paired-arm generation reuses the same history-address streams; `arm_arrays` checks baseline/C site identity, holdout exclusion and observation masks. Qualification dataset IDs are distinct. Background pairing intentionally omits background from the history stream key.
- Input loading already verifies raw/compressed arrival checksums and site correspondence. The new fit entry point's source/input capture is narrower than the older runner's complete-source capture and does not itself recheck drift; the batch driver now enforces a clean frozen source and all declared input hashes. Parent should retain complete analysis-source hashing in the entry point too, particularly for local diagnostic runs.
- Local mock/probe outcomes before repair: execution-error retry skipped; changed task skipped; missing result skipped; missing executable produced no task receipt; reduced-family `MemoryError` misclassified.

## Verification and handover

Commands run after the execution repairs:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -m pytest -q tests/test_pbs_campaign.py tests/test_sprint2_bank_identity.py
.venv/bin/ruff check scripts/pbs/campaign.py scripts/generate_history.py tests/test_pbs_campaign.py tests/test_sprint2_bank_identity.py
bash -n scripts/pbs/array.pbs scripts/pbs/prepare_runtime.pbs
git diff --check
```

Result: **14 tests passed**; scoped lint, shell syntax and diff checks passed. Tests exercise retry preservation, every scientific-failure terminal class, task/output drift, launch failure, missing results, source/input preflight, reconciliation, interrupted attempts and bank independence. No scheduler-level behavior was tested.

Files changed by this delegate: `scripts/pbs/campaign.py`, `scripts/pbs/array.pbs`, `scripts/pbs/prepare_runtime.pbs`, `scripts/generate_history.py`, `tests/test_pbs_campaign.py`, `tests/test_sprint2_bank_identity.py`, and this review. No commit was made. Parent owns entry-point error propagation, the qualification orchestrator, prospective frozen task/seed manifests, final review and remote pilot.

## Independent cross-review of the numerical repair

Separately reviewed the numerical delegate's working-tree changes to `spatial_profile.py` and `test_spatial_profile.py` against `583c1e3`. **Accepted as a bounded numerical-eligibility repair**, subject to the new qualification and the parent's matching constant-family enforcement. This acceptance does not qualify the old replay receipts under the changed procedure.

- `certified` can become true only at a projected-gradient stationary point with all required curvature columns available and no numerically material negative eigenvalue of the negative Hessian on the free coordinates. Substituted diagonal curvature remains a step proposal, never a certificate.
- Saddle escape now tries both directions over decreasing radii. Each accepted escape must improve the actual criterion. Failure, the three-escape limit and the iteration limit leave the certificate false.
- `_fit_family` requires optimizer success as well as evaluator success and the projected-gradient limit. A stationary but uncertified point cannot become an eligible family maximum.
- The existing bound-maximum/backward-difference test still passes. The free-coordinate curvature criterion is a numerical local check, not proof of global maximality; it can conservatively reject constrained boundary cases. No stronger claim is needed for this repair.

Independent focused run: `pytest -q tests/test_spatial_profile.py -k 'trust_region or optimizer_certificate'` with numerical threads fixed to one: **9 passed, 40 deselected**. No numerical source or tests were edited by this reviewer.

The PBS array now explicitly binds the project data and work roots, task/output/source paths and SIF directory. `LL_WORKERS` is required and checked against `NCPUS` when supplied by PBS; it never silently defaults to one. The submitting pilot must verify the requested per-node allocation and pass that worker count; this local review does not infer site-specific scheduler variables or allocation policy.

## Concrete qualification task preparation

Added `scripts/prepare_sprint2_campaign.py` and its six focused tests at the parent's request. The producer checks the exact frozen panel hash and all nine staged qualification map records/payloads before writing anything. It rejects validation paths/roles, requires the full clean candidate commit and an actual runtime-preparation receipt, and consumes previously frozen dependency plans. Dependencies are verified against their planned task specifications and preserved attempt/output hashes, never merely a self-reported successful exit.

The separate phases prepare:

- `banks`: 18 bank tasks, replicates 0/1 on each map, K=131072 and order 192.
- `histories`: the exact 207 registered datasets, retaining the shared biological address across paired arms/backgrounds.
- `fits`: 414 dense/lean tasks, 54 independent-bank lean tasks and 18 exhaustive lean tasks; 486 total.
- `audits`: 261 common-anchor comparisons plus 207 gradient checks when all prerequisite fits resolve. Failed scientific fits stay in the index; their impossible derived audits are explicitly pending/omitted and the reducer handles their decisive failure.
- `integration`: the nine flagged descriptive screens. Terminal scientific fit failures are still passed to the screen wrapper so its reasoned unavailable result can be retained.
- `index`: a fresh `sprint2-qualification-index-v1` from verified results, with missing references left null and separate execution statuses. Bank-identity sidecars bind the actual compared fit and bank manifests.

Each phase writes `plan.json`, `tasks.jsonl` and `qualification-index.json` to a new directory. Supply earlier `plan.json` files with repeated `--dependency-plan`; supply the shared task-output root with `--results-root`. Other required arguments are `--maps-root`, `--runtime-receipt`, `--source-commit`, `--python`, `--execution-context apptainer` and `--output-dir`. It never launches jobs, generates histories or opens validation.

Runtime preparation was corrected during parent review: it now builds a **new** SIF once from a digest-pinned OCI reference and records its actual hash, source commit, dependency-lock hash, interpreter and installed distributions in `sprint2-runtime-v1`. It refuses existing image/receipt targets. It does not require an impossible predicted SIF-conversion hash. The array passes the actual selected SIF hash/context into the container; each task checks those and its interpreter against the frozen runtime. Runtime preparation also verifies Git/source identity and imports the scientific packages inside the container; the chosen image must therefore include Git. None of this has been exercised on a compute node yet.

Final focused suite: **20 tests passed** across `test_pbs_campaign.py`, `test_sprint2_bank_identity.py` and `test_prepare_sprint2_campaign.py`. The new tests use fabricated dependency artifacts; they run no fit or simulation. A separate read-only call to `load_qualification` verified all 207 real frozen dataset rows and all nine staged map records/files. Scoped lint, shell syntax and diff checks pass. Parent owns immutable commit/remote staging, independent review of this producer and the first live runtime/PBS pilot.
