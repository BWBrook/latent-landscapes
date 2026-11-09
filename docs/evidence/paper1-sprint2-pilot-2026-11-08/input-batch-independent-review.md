# Independent batch-completion and fit-allocation review

9 November 2026. Reviewer: Codex (GPT-6.1 Sol). **Accept the completed bank/history batch and historical diagnostic replay evidence within the limits below. The proposed full 486-task numerical qualification allocation is defensible without another resource-only pilot: 243 PBS array subjobs, chunk 2, two single-threaded workers, two CPUs, 8 GB and a 48-hour ceiling per subjob.** Final promotion to a fit plan still requires the parent's target-side raw-bank and dependency verification; that is an input-integrity check, not a new pilot or scientific redesign.

This bounded review advances Paper 1 charter pillars 3, 4 and 6 and Sprint 2 numerical qualification. It used local source, frozen plans, original receipts and analyst observation arrays only. I wrote only this ignored note. I changed no tracked file, source, original task or receipt; ran no fit, history generator, remote command or evaluator analysis; and sent no board message or external communication. Training and validation remain CLOSED.

## Completion and identity

The final phase ledgers and their reconciliation log report 18 completed banks, 207 completed qualification arm datasets and five resolved historical diagnostic fits, with zero missing, invalid, execution-failed or scientifically failed tasks. I independently checked all 230 root records against the exact frozen task objects rather than accepting those counts alone. There are exactly 225 qualification-input task directories and five historical-fit directories, with no extra or missing root task identity.

The bank and history plan objects exactly match their 18- and 207-line task files, respectively. Their pending lists are empty. The three task-file SHA-256 values match `remaining-phase-plan.json`; `remaining-phase-submission.json` binds to that plan's exact bytes. Every task has source `99af5206b6a4e53f5b8e9d71cbf348f95e9ae574`. Canonical task digests, original start records, root/attempt receipts, expanded execution arguments, result schemas, exit-zero/error-free completion and clean recorded source identities agree. The runtime bindings match `operations/runtime.json`, its SHA-256 `f273d592d9499d50197c2e9a2663b045d7cfc1aa4a2fc4b1b9dc03733ae65079`, the frozen lock and SIF identity. I independently rehashed 118 unique frozen tracked input blobs from Git objects, including the historical fit receipts' recorded numerical source inputs.

All **1,362 locally present output hashes** in the 230 task receipts verify, including start/log/result payloads and the reporting-only history files as opaque bytes. The only 18 absent output entries are `bank/arrivals.npy`, deliberately retained on the target. Those raw files were not reread locally. The historical task data hashes also equal their fits' recorded data hashes; this review did not freshly reread all historical input payloads or the remote SIF. The parent retains responsibility for target freshness and raw payload checks. The large combined audit completed 8,761 assertions with zero discrepancies; the separate bank-seed and array checks below also passed.

## Qualification inputs and protected boundaries

The qualification panel is still SHA-256 `51006aa0355ab4ce9f28e572a4272f09c0dc9fcdb52ae6ed0570aacbb1cf240d`; its map-manifest binding is `60e1bd8a4a42dca81c42d9a12f9dfa3a64d1a7853940289cf3de743e697fb0bb`. All nine local qualification-map compact records and payload hashes match. Map roles, successful status, namespace-2 map spawn keys and all per-task/per-history map-input hashes agree. No validation map or identity was opened.

All 207 history receipts match their exact registered rows: qualification namespace 5, map, background, address, arm, effect, mean hazard, detection SD 0.2 and independently reconstructed stream seeds. Denominators remain 162 base, 18 boundary, 18 enriched and nine trend datasets. Each map contributes its prescribed 18 base arm datasets. All 54 base biological histories have the three registered A/B/C arm identities. Analyst arrays independently confirm:

- A/B contain exactly the 120 baseline sites; C contains the 260 registered nested sites; all exclude the 40 held-out sites, retain unique site IDs and have a true training mask.
- The full frozen prey/predator calendars and day-minus-60 cohort are retained. A has all prey occasions; B/C have no prey availability at or before day zero. C predator availability is confined to the same 120 baseline sites, while A/B retain their complete predator network.
- Unavailable counts are zero; observed counts have the allowed 0/1/2 representation. For each base history, A/B post-zero prey counts agree, C agrees on those same baseline sites, and predator counts agree across the nested arms. The common biology is therefore backed by array equality as well as shared seeds.

All 18 bank manifests retain K=131072, order 192, one internal bank worker, and exactly replicate 0 or 1 for each of nine qualification maps. I reconstructed all 2,359,296 simulation seeds and their 18 recorded seed digests; each bank has unique seeds, and each map's two 131,072-seed arrays have zero overlap. Both manifests in every pair use the same map-input hashes, and their raw-file and compressed-file digests are distinct. All compressed file hashes already verify against task receipts/manifests. Every compressed bank has the correct 300-site order, category shapes 300×7 and moment shape 300×6×193; nonnegative integer counts sum to K, masses equal `(counts+1)/(K+7)` and sum to one, and finite/nonnegative moments have the expected order-zero values and nonincreasing powers on [0,1].

The compressed `bank_checksum` is the contiguous float-array digest, whereas `raw_sha256` hashes the NPY file including its header. They are different quantities. Without the remote raw matrix this review neither independently recomputed the former nor checked compressed moments by raw recompression. Parent target-side producer verification is the remaining explicit integrity dependency.

## Historical replay status

All five new historical cases are 120-site **development diagnostics**, not fresh qualification successes. Their task data hashes, clean frozen source, pinned runtime, single numerical threads, lean mode and always-on tight replay agree. All three fitted families are available. Spatial standard, spatial tight, exposure and constant each provide all eight available cutoff sets `{2.71,3.84,5.02,6.63,7.88,9.55,12,15}`; all eight standard/tight comparison flags pass. Failure class is resolved, with no triggered/message/error, latent-multimodality or envelope-guard flags. Child search receipt hashes verify and explicitly retain `development_only=true`, `calibration_claim=false`, `globality_proven=false` and `truth_used_in_search=false`.

Together with the earlier separately accepted 120/260-site compute-node portability pilot, this completes the outstanding historical replay tranche. It establishes neither the fresh finite-panel numerical acceptance score nor calibration, exact-integral accuracy or global optimality. The fresh panel still needs its 486 fits, exact-union comparisons, gradient audits and prescribed exhaustive checks.

## Resources and proposed fit batch

The observed concurrent batch provides materially stronger allocation evidence than the earlier lone timing:

| Work | Tasks | Task wall hours | Task CPU hours | Largest recorded child peak |
|---|---:|---:|---:|---:|
| Frozen banks, including pilot | 18 | 4.255–4.651 | 4.158–4.641 | 1.062 GB |
| Qualification history generation | 207 | 0.00169–0.01281 | 0.000709–0.000786 | 0.1025 GB |
| Outstanding 120-site diagnostics | 5 | 1.406–3.305 | 1.399–3.299 | 0.6870 GB |
| Earlier accepted 260-site pilot | 1 | 9.305 | 6.335 | 1.276 GB |

The five historical diagnostics ran in three two-worker/8-GB allocations on two physical hosts, with pairs actually overlapping and CPU approximately equal to wall time for each fit. The completed bank phase spans six physical hosts including the pilot, with the 17 new banks in five four-worker allocations. Every 300-site bank took at most 4.66 hours, and their nominal combined raw NPY size is about 5.66 GB. This supplies practical multi-node execution and bank I/O evidence. It does not establish linear scaling to 486 concurrent fit workers, peak shared-filesystem bandwidth, or an exact campaign completion time.

`worker_children_peak_rss_bytes` comes from the worker process's `RUSAGE_CHILDREN.ru_maxrss` after a task. It is a lifetime high-water mark over completed children, potentially inherited from an earlier task handled by that same pool worker. It is **not aggregate-node RSS**, and summing it is not a measured node peak. These five fit workers each processed one historical task in their allocation. Their own fit receipts provide compatible fit-process peak measurements; the earlier 260-site fit independently records 1,276,227,584 bytes. Two such observed large fits total about 2.55 GB before ordinary parent/runtime overhead, leaving substantial room in 8 GB. Dominant bank/series dimensions remain fixed; these observations are an engineering basis, not a worst-case memory proof for every dense or exhaustive search.

The immutable panel and producer specify 414 dense/lean fits, 54 independent-bank lean fits and 18 exhaustive lean fits, totaling 486. Their arm allocation is 164 A, 166 B and 156 C fits. Twelve exhaustive audits are C cases. The proposed two-task/two-worker allocation permits each pair to run concurrently; it does not divide the 48-hour limit between two sequential fits. Forty-eight hours is about 5.16 times the observed 260-site lean wall cost and 14.5 times the slowest new 120-site diagnostic. Dense and exhaustive cases can cost more, so this is a sensible generous ceiling rather than a completion guarantee. Preserve any execution loss and retry only with unchanged scientific/task identity and retained attempts.

The saved queue preflight permits 48 hours, 128 GB per allocation and 7,000 queued CPUs, with 4,000 queued and 3,000 running jobs at the recorded checkpoint. This proposal requests at most 243 allocations/486 CPUs/1,944 GB, and at most 23,328 reserved core-hours if every subjob runs to its ceiling; those are upper reservations, not runtime predictions. Parent should verify current scheduler/account limits during submission as required by the runbook. This local review did not perform a new live scheduler check.

There is no decision-relevant reason to insert another mandatory resource-only pilot: the complete 120/260-site entry point has already run on target, concurrent two-worker historical fits now run across allocations, and the full bank phase tests several-node data I/O with large files. Preparing and executing the frozen numerical panel is the next substantive evidence step. Accept this resource setting while preserving source, all three families, tight replay, the full cutoff grid and registered failures. Qualification outcomes themselves must not be used for undocumented method retuning.

## Decision and limits

**Accept with no scientific or resource objection to the proposed full qualification-fit batch**, after the target producer verifies the 18 raw bank payloads and nine bank pairs and produces exactly 486 tasks with no pending dependencies. I audited the producer's frozen role logic, not a subsequently generated fit-plan artifact. No new scientific gate, seed choice or allocation criterion is introduced here.

Passing numerical qualification still does not authorise training. The executable map-population uncertainty/precision rule, forecasting targets/scoring, bootstrap/comparator choices and temporal-stress specification remain a separate unresolved training gate. Validation remains closed through the existing cross-review/reconciliation boundary.

Private node identifiers are omitted from this public copy; the original review is retained with the bulk evidence.
