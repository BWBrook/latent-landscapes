# Independent completion audit: historical portability pilot

8 November 2026. Disposition: **PASS for the two-case, predeclared historical portability claim**, with the limitations below. This is a separate read-only review of original evidence, not acceptance based on the comparator's status field. No fits, remote calls, validation access or source changes were performed. Only this ignored note was written.

## Evidence and identity checks

I read the frozen acceptance note, comparator implementation, local/target fit and child-search receipts, immutable two-task plan, retry plan/wrapper, runtime record, final reconciliation, interrupted-attempt evidence, and the new public evidence summary.

Independent Python assertions, using direct receipt fields and separate numerical comparison logic, verified:

- The task JSONL, exact acceptance-note bytes and runtime receipt match their hashes in the frozen plan. Retry wrapper/hash and unchanged task-file identity match the retry plan.
- All 15 locally retained historical input files were rehashed against their inventory. The two compared receipts have equal five-input hashes by role. Each target data hash matches its corresponding frozen inventory entry.
- Canonically computed task hashes match both final task receipts; recorded source is clean candidate `99af5206b6a4e53f5b8e9d71cbf348f95e9ae574`. Final task identities are the first 120-site attempt and second 260-site attempt, with their correct distinct PBS jobs. Root and attempt task receipts are byte-identical. All 12 final output-file hashes verify, including the parent/child search bindings.
- Runtime source, dependency lock, interpreter and SIF identities agree across task plans and runtime evidence. The retained target SIF checksum record agrees with the runtime receipt. The SIF itself is not present locally and was not downloaded or independently read remotely in this bounded review; task-driver checks and retained target checksum evidence supply that binding.
- Both final tasks/fit receipts resolve with exit zero, no errors, triggers, unresolved envelope events or latent-multimodality flags. All three families and all eight cutoffs are available, with lean search, full tighter replay and one numerical thread. Reduced free fits are eligible; latent settings agree.
- The first 260-site attempt is retained separately, with its original `_started.json`, 245 fit events, empty stderr and no final fit receipt. Its task identity equals the retry's. The scheduler log explicitly records walltime 14,481 seconds exceeding 14,400. It remains an incomplete execution attempt, not a scientific failure or a hidden replacement.
- Final reconciliation contains exactly two resolved tasks and no scientific failures, execution failures, missing or invalid final tasks.

The accepted 120-site local reference is the exact hash-selected historical dirty-source receipt plus preserved patch, as specified before target outcomes. Its numerical-procedure equivalence to the clean candidate relies on the previously recorded independent 115-file provenance reconstruction. I reverified receipt/patch identity and read that qualification; I did not redo that full historical reconstruction. The 260-site local reference records the clean candidate. Neither should be described as identical source bytes across both 120-site hosts.

## Independent numerical result

For spatial standard, spatial tight, exposure and constant separately, I recalculated W using each host's own free maximum at exactly shared stored log-h values, verified the fixed meshes/endpoints, checked canonical nuisance/domain contacts at free/null/shared nodes and aggregate contacts on unmatched nodes, and compared every ordered root/component, endpoint type, boundary contact and set class at all eight cutoffs.

| Case | Exact shared nodes: standard/tight/exposure/constant | Largest absolute W difference | Largest root or component-endpoint difference, log-h |
|---|---|---:|---:|
| 120 sites | 9 / 9 / 42 / 59 | 9.094947017729282e-13 | 1.1024514634527804e-13 |
| 260 sites | 10 / 10 / 43 / 59 | 9.094947017729282e-13 | 1.0507972270090704e-10 |

All required topology/contact checks pass. The thresholds were .01 for W and .005 for log-h endpoints. Adaptive meshes are not identical: for example, 260-site spatial profiles contain 151 local versus 150 target nodes. Unshared nodes remain untested pointwise. The full eight-level-set comparison passes nonetheless. This is the frozen bounded portability check; it establishes neither exact-union qualification nor agreement everywhere between nodes, global optimization, exact integration, calibrated inference or population performance.

## Public summary check

Every case cost value, site count, attempt, receipt/comparison/task hash, shared/unmatched node count, maximum W/root/endpoint discrepancy, contact status, cutoff list and runtime field in `docs/evidence/paper1-sprint2-pilot-2026-11-08/pilot-summary.json` matches the underlying receipts/comparison records. The public acceptance note is byte-for-byte hash-equivalent to the frozen note. Its limited-pass claim and qualifications are supported.

## Measured resources and next bounded step

| Target case | Fit wall seconds | Fit CPU seconds | Fit peak RSS bytes |
|---|---:|---:|---:|
| 120 sites | 4578.980854021385 | 4573.16678439 | 694009856 |
| 260 sites | 33499.08390591666 | 22805.725367837 | 1276227584 |

Task wall times, which include source/input checks and output hashing, are 4600.2113 and 33534.5120 seconds. Do not mix these with fit-stage times. The 260-site difference between wall and CPU time is real but its cause is not established by these receipts. Scheduler memory accounting should not replace the fresh subprocess RSS for fit packing; a reused worker's lifetime child maximum is not an independently additive task measurement.

The four-hour ceiling was inadequate; twelve hours completed this particular retry. Two historical cases do not establish a universal runtime maximum, concurrent packing efficiency, multi-node scaling or total training cost. Bank generation uses all 300 public map sites and a different memory/work path, so neither fit RSS nor the older four-worker bank timing certifies its resource needs.

I have no methodological objection to the parent's proposed **single bank-only resource pilot**, selecting index 0 from the already frozen bank task file with one worker, one CPU, 8 GB and a 24-hour ceiling. This is an engineering measurement under the existing reviewed qualification design, not an inference amendment or approval to expand biological histories. The allocation is provisional: preserve failures, verify the exact selected task/start identity and measure bank peak RSS/CPU/wall time before packing or submitting all banks. One map's result will still not prove every geometry's worst-case cost. No biological histories need be generated to obtain this measurement.

Training's executable uncertainty/forecast/comparator decisions remain open, and validation remains closed. A passing historical pilot does not itself resolve those gates.
