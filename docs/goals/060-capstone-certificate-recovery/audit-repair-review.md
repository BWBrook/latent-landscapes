# Review of the Goal 060 audit-interface repair

4 October 2026, Hobart. **The repair is suitable for a new source freeze and a
prospective audit-only run.** It changes the representation passed across one
provenance interface and leaves every numerical calculation, tolerance,
scientific gate and direct-scoring implementation unchanged. No repaired full
audit, data generation, fitting, scoring or readiness recovery has been run.

## Bounded defect and repair

The preserved registered audit failed because the producer's validated bank
manifest contained the raw JSON object plus a derived SHA-256 of that raw file,
while the Goal 060 wrapper supplied only the raw JSON object to an exact
dictionary comparison. The original failure, its negative readiness result and
all frozen evidence remain unchanged.

The new `audit_capstone_recovery_repair.py` imports the frozen Goal 060 recovery
auditor and the unchanged Goal 059 independent auditor. It does not copy their
certificate, reconstruction, generator-replay, likelihood, point-score,
stability or calibration logic. Its adapter performs four operations:

1. read the raw `arrival_bank/manifest.json`;
2. require that the raw object does not already contain `manifest_sha256`;
3. require a passed independent bank audit whose recorded manifest hash equals
   a fresh SHA-256 of those exact file bytes; and
4. attach that hash to a copy of the raw object before calling the existing
   `audit_panel_results` function.

If the raw manifest is denoted `M`, the only new value passed to the unchanged
gate is `M` plus `{manifest_sha256: SHA256(bytes(M))}`. This exactly reproduces
the object created by the production validator. Exact equality remains in
force for every substantive manifest field and for the derived file hash.

The new entry point also requires the original failed audit. It accepts only
SHA-256
`21cfa9c56e29d95b40524c8e5e6afbeba8c2dceef264f3494b1ddf99c5836132`
with the registered Goal 060 schema, failed status, negative audit flag and the
exact observed `ValueError`. A repaired receipt records this binding and
identifies the adapter explicitly. It retains the common top-level
`goal060-independent-public-audit-v1` schema required by the unchanged sealer;
the distinct `goal060-independent-public-audit-repair-v1` identifier is nested
under `repair.schema_version`. It refuses an existing output directory.

## Unchanged audit meaning

The new orchestration calls the same source/runtime freeze audit, recovery and
certificate audit, confirmatory-address audit, registered calibration-fixture
audit, arrival-bank audit, mechanical audit, eight-history replay and predraw
bindings in the same order as the failed wrapper. It then calls the same
`audit_panel_results` implementation for all direct main/profile/lattice and
held-out scores and all scientific and nested-bank stability gates.

The adapter does not import production likelihood code, alter an artifact,
drop a check, substitute producer scores, change a threshold or convert a
failure into a pass. Its output can qualify the existing numerical artifacts
only if the previously unreached independent checks execute and pass.

## Verification

Eight focused tests pass using only mechanical root `987654321`. The integration
fixture builds a small bank manifest, runs the actual production
`validate_bank_manifest` path to obtain its augmented object, and independently
audits the raw bank. A sentinel immediately after the unchanged completion gate
shows that the corrected object reaches the existing scoring boundary without
performing a direct score. The tests also establish that:

- a missing, wrong or non-passed independent manifest hash is rejected;
- any change to the raw manifest file is rejected against the audited hash;
- a substantive change inside the producer completion copy is rejected by the
  unchanged exact-equality gate; and
- any change to the original failed audit is rejected;
- failed and successful repaired receipts retain the common audit schema while
  recording the repair-specific schema and original-failure binding.

Ruff and strict mypy pass for both new files. No registered root, public or
private history, fitted model, arrival bank, direct score or sealed artifact was
created or changed by these checks.

## Prospective execution recommendation

Freeze the new script, test and this review with a new source manifest and the
same numerical runtime. Bind the 603 copied inputs and evidence files through
the new input-binding receipt, verify its returned members against the
preserved 658-file return manifest, and separately bind that manifest and the
post-return completion check. Also bind the original source archive, failed
audit, negative readiness receipt and registration before execution. Fable
should verify those bindings and the three new source hashes independently.

Run only the repaired full audit against the immutable existing bank, panel and
fit artifacts, writing to a new audit-repair output directory. Preserve both
the old failed receipt and any repaired receipt. Do not regenerate histories or
the bank, refit models, alter producer receipts, or reuse the old audit output
path.

Even a repaired audit pass does not by itself rewrite the frozen negative
`public-ready.json`. A separate bounded readiness-recovery step must validate
and bind the new audit before sealing can become eligible. If any previously
unreached numerical or stability gate fails, that failure is the scientific
result and this repair supplies no authority to retune or rerun it.

Independent review materially changes confidence in this repair because the
defect was discovered after favorable producer results. The explicit original-
failure binding, unchanged exact gate, mechanical-path regression tests and new
freeze make the repair auditable without treating the favorable outcome as a
reason to weaken acceptance criteria.

## Pre-freeze integration addendum

The prospective package driver, freezer, supervisor, input bindings and runtime
were reviewed before execution. No material integration defect was found.

The input map contains 603 unique, path-safe destinations and 603 unique source
files. Every source file currently matches its bound SHA-256. The metadata also
matches the original source manifest, return manifest and failed audit. The
freezer requires all 303 original source hashes to match the live files and
requires the original source archive to match its preserved receipt before it
adds the adapter, tests, review and execution records. The repair runtime is
byte-identical to the original Linux runtime. This preserves the numerical and
scientific source while making the additive interface change explicit.

The driver copies the original confirmatory-address contract and changes only
`source_manifest_sha256`. Before writing the rebound contract it requires the
original source, unchanged runtime and unchanged registration bindings; it also
compares every other contract field for equality. The repaired auditor then
independently reconstructs the complete contract, so the bridge does not alter
a root, namespace, domain, node, reference, stage or random-number algorithm.

The full-audit command invokes the new adapter with the preserved failed audit,
the original Goal 059 predecessor package, the copied Goal 060 inputs, bank,
mechanical receipt, panel and fitted results, the unchanged calibration fixture
and the rebound confirmatory contract. It writes to a new audit directory. No
driver command generates a bank or history, launches fitting, changes an input,
draws a private root or invokes sealing.

The repaired receipt retains the common audit schema expected by the unchanged
sealer. A positive readiness file can exist only as a local preflight candidate
after both audit pass flags are true and after the immutable inputs are checked
again. The unchanged preflight validates every readiness binding, source and
runtime freeze, recovery, bank, completed audit and confirmatory contract. If
preflight fails, the candidate is preserved under a failure name and the final
readiness file is rewritten negative. Handoff remains conditional on a clean
supervisor finish. The preflight does run the public `age` recipient encryption
probe, which may use operating-system randomness; it does not draw a scientific
or private-history root.

The one-attempt supervisor freezes the driver, wrapper, sources and inputs,
uses one numerical-library thread, enforces a 64 GiB process-group RSS cap and
checks for remaining group members. The repair limits are 600 seconds for
qualification and 10,800 seconds for the audit plus preflight. Together with
the original 213.625-second qualification and 1,257.562-second public run, the
respective maxima are 813.625 seconds and 12,057.562 seconds, within the
original 1,800-second and 14,400-second caps.

Execution remains the outstanding test. The freeze receipts, remote copy,
runtime, 603 inputs, new source archive, audit output, preflight and supervisor
closure must be checked from their final hashes. A transfer, audit, numerical,
preflight or supervision failure must leave the repair package negative and
does not authorize another attempt or any change to a scientific gate.
