# Independent bank completion and allocation review

8 November 2026. Independent reviewer: Codex (GPT-6.1 Sol). **Recommendation: accept the completed bank resource pilot and execute the remaining 17 frozen bank tasks using the proposed four-worker allocations. A separate four-bank packing pilot is unnecessary for this decision.** Concurrent generation of the already reviewed 207 qualification histories is also consistent with the existing entry gate, subject to the identity checks below. Neither action opens training or validation.

This review read local evidence and source only. It wrote only this ignored note; no source, tracked document, original receipt or task was changed. No fits, histories, remote commands, commits or board messages were run.

## Completed bank and independently checked identities

The final receipt identifies `bank-barrier-0-r0`, attempt 1, clean source `99af5206b6a4e53f5b8e9d71cbf348f95e9ae574`, status `completed`, exit zero and no error. The task is exactly task 0 of the existing 18-task plan. The original start, task receipt, extracted pilot-task object and plan object agree, including their independently recalculated canonical task digest. Root and attempt task receipts are byte-identical. All five locally present output hashes verify. The sixth output, raw `arrivals.npy`, remains on the target.

I independently reconstructed all 131,072 seeds from the registered root/namespace/map/replicate/row rule, verified uniqueness and reproduced the manifest's seed hash. I verified the nine maps' five input-file hashes against all 18 task objects, plus frozen panel/map-manifest/lock/runtime references. All nine public maps have a 72×84 grid and 300 site IDs; all tasks preserve K=131072, one bank worker, replicate 0 or 1, compression order 192 and the frozen candidate. There are exactly 18 distinct map/replicate addresses.

The compressed payload hash and site order match the manifest/map. Its shapes are counts/masses 300×7 and moments 300×6×193. Counts are nonnegative integers summing to K per site; masses equal `(counts+1)/(K+7)` and sum to one; moments are finite/nonnegative, order-zero values equal the corresponding finite-category masses, and powers decrease as required on the normalised [0,1] support. All stored compressed arrays total 2,833,472 uncompressed bytes.

The parent remote audit's task, manifest, compressed and raw hashes bind to these same local receipts. The actual raw shape 131072×300, NPY size 314,572,928 bytes, raw checksum and target runtime/source/input freshness rely on that remote audit and the task driver. I did not read or rederive the raw arrival matrix, its full float-array checksum or its moments locally. The local compressed checksum field has the correct form; this is not a substitute claim of independent raw recompression.

One metadata clarification is recorded without editing the original plan: `bank-pilot-plan.json`'s ambiguously named `task_file_sha256` hashes the extracted single-task JSON, whose verified SHA-256 is `29869658574ddd74f36a7f4d0da674a40e0a3890dc9fe92c1f573f8d9f5fb89a`. It is not the full 18-line task file. The full locally retained JSONL hashes to `3564b8934cfc7909ea02a6265fbd4e1bd68df75013931b8b66cf4eb3ce632ae6`; its parsed objects exactly equal the plan's task list. This distinction explains the initial apparent mismatch, with no task-object drift demonstrated. Parent is separately checking the target file's exact bytes before submission.

The saved scheduler record confirms finish/exit zero. Reconciliation at this capture reports one completed bank, 17 missing, zero invalid and zero execution/scientific failures. This is not completion of the bank phase or numerical qualification.

## Resource decision

Observed task cost is 15,317.0223 seconds wall and 14,968.2649 seconds CPU, about 4.25 and 4.16 hours. The one-task fresh worker reports lifetime completed-child peak RSS 1,056,804,864 bytes. It is not aggregate-node memory. The scheduler's job-memory observation is 1,115,136 KiB, or 1,141,899,264 bytes, which provides a separate approximate aggregate observation for this single-task job.

The bank builder's dominant storage follows fixed K×site shapes: the 300 MiB raw matrix/mapping, roughly 300 MiB of retained completed chunk results and a 300 MiB integer category matrix. Compression moments, per-site work and graph/FFT objects add overhead. Category values and passable geometry can change timing, but all nine grids and site counts have the same dimensions. This is a source-based memory argument alongside a measurement, not a formal worst-case RSS proof.

Four times the observed scheduler peak is 4,567,597,056 bytes. A 16 GiB allocation is 3.76 times that scaled observation; even allowing sampling error, additional interpreter/parent overhead and ordinary geometry variation, the margin is substantial. Each task uses one numerical worker internally. Four campaign workers and four CPUs therefore form a defensible small packing step. Twenty CPUs across five allocations is modest, and a second packing pilot is unlikely to change this allocation decision. Concurrent throughput and I/O efficiency still remain unmeasured.

Use the same 18-task file, chunk 4/workers 4 and array indices 0–4. Chunk lengths are 4/4/4/4/2; verified task 0 is skipped, leaving 17 new banks and at most four active tasks per allocation. Preserve completed and failed attempts, and reconcile task identities/output hashes before reuse. A 24-hour ceiling is 5.64 times this observed single-task wall time. It is a reasonable engineering allowance, not a guaranteed maximum over geometries or shared-node contention. No inference, seed, K, compression or source change is needed.

## Qualification histories

The existing reviewed runbook explicitly permits bank and history phases concurrently after runtime and historical compute-node pilot checks. Both precede fitting; the history producer has no bank-result dependency. The historical pilot has passed and the candidate remains fixed. Bank completion alone does not establish qualification, but it need not delay generation of the registered histories.

I also checked the now-local history plan: exactly 207 task objects match its plan and the hash-frozen qualification panel; strata are 162 base, 18 boundary, 18 enriched and 9 trend across nine maps. Every address is in qualification namespace 5. Each task's map, background, mu, h, arm, detection SD, result schema and runtime/source match its registered row. No validation paths or training tasks are included. Parent owns final target input/runtime and exact task-file checks.

Chunk 32/workers 4 gives seven subjobs (32/32/32/32/32/32/15). Four CPUs/8 GB per subjob with a two-hour ceiling is a reasonable provisional allocation: the producer draws one history/arrival, uses 300-site observation arrays and a 142×166 FFT embedding, and does not build a K-row bank or fit a likelihood. Its runtime/RSS has not yet been measured on this target, so label these resource values as estimates until receipts arrive. There is no scientific gate requiring a separate four-history pilot, and the code's much smaller working shapes do not justify another mandatory resource-measurement stage here. Preserve execution failures and record realised resource use.

All future fit/audit/integration and finite-panel qualification gates remain intact. Qualification histories cannot silently become untouched rule-training evidence, and training's unresolved executable uncertainty/forecast/precision/comparator specification and the validation boundary remain closed.
