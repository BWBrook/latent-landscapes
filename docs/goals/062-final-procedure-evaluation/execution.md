# Goal 062 execution record

Updated 13 October 2026 (Hobart). This record implements the approved
[ten-cell amendment](amendment-2026-10-11.md) to the
[prospective registration](registration-2026-10-11.md). It advances the
final-procedure operating-characteristics gap identified in the
[Paper 1 evidence synthesis](../../paper1-evidence-synthesis-2026-10-11.md).
The approval includes implementation, qualification, the bounded campaign
and independent audit. Changes to scientific methods, the registered runtime
or the resource envelope retain their explicit decision boundary.

## Current status

**Production is running.** Barry accepted the exact runtime amendment and
launch in this chat on 13 October: “Approved, proceed.” The
[approval record](../../decisions/2026-10-13-goal062-runtime-approval.md)
and its JSON preserve the authority and exact three bindings. The related
Decision Inbox form has no submitted answer; it is not a remaining approval
gate. The reviewed 11 October proposal and qualification remain unchanged.

The final preflight at 11:49:52 UTC reverified the approved source/runtime,
all 165 qualification files and original reference/public custody. Deep had
118.77 GB available memory, 4.482 TB free scratch and 64 logical CPUs. No
existing production directory or run attempt was present. The installed
approval JSON has SHA-256
`c4a9f1902295de547583a26480345c05ae0e58395487b4e879b74ac9b5238f6c`.

| Production launch | Observed value |
| --- | --- |
| Start | 2026-10-13 11:51:16.785553 UTC / 22:51 AEDT |
| Persistent deadline | 2026-10-16 11:51:16.785553 UTC / 22:51 AEDT |
| Root | `/data/codex/scratch/goal062-final-procedure-20261011-qualification2` |
| Attempt | `run` / `001` |
| Initial supervisor / process group | 280990 / 280991 |
| Worker allocation | 51, one numerical-library thread each |
| Seed ledgers | 27,000 evaluation and 20,000 bootstrap addresses; 47,000 distinct derived seeds |
| Initial active work | 51 effect-reference databases; 53 process-group members |
| Process-group RSS at 11:53:57 UTC | 22,741,749,760 bytes, below 64 GiB |

The registered bootstrap and evaluation ledgers were frozen before reference
generation. Their SHA-256 values are
`f739fd639b9cc26bfad0c24de4375c519038bc185fec5d8825ece9a84eab8eee`
and `b91fede6a82ec872c48cfc1a265c6d4ee8bebc520cfd70577ad603417326a28a`,
respectively. The seed-audit receipt binds both to the unchanged source.

The campaign first generates and audits the remaining 466 effect tables,
then completes the registered 5,000-history evaluation, scoring, diagnostics
and synthesis. Completion and scientific results are not yet available.
The hourly thread heartbeat `goal-062-campaign-follow-through` monitors this
same run and continues the already approved audit/reporting work. It stays
quiet while state is unchanged or non-actionable and pauses at verified
terminal reporting, a hard resource stop or a decision requiring Barry.
The 46–57-hour planning allowance and all registered scope limits remain.

## Qualification before runtime acceptance (11 October)

Implementation and [independent source review](implementation-review-2026-10-11.md)
are complete. **Nonproduction qualification 2 passed** on deep-server, running
from **2026-10-11 02:56:29 to 03:21:33 UTC** (13:56:29–14:21:33 AEDT).
All numerical, audit, workload and 51-worker memory checks passed within the
three-hour qualification guard. [Independent receipt review](qualification-review-2026-10-11.md)
supports presenting the exact runtime amendment to Barry, with no required
repair or repeat qualification. No new production reference row or evaluation
history has been generated.

The accepted receipt records Linux `6.8.0-142-generic`; the current host runs
`6.8.0-146-generic`. Python 3.14.5, NumPy 2.5.1, SciPy 1.18.0 and PCG64 match
the original version fields. The compatibility measurements support a
[proposed additive runtime amendment](runtime-amendment-2026-10-11.md), pending
Barry's decision after independent review. A successful numerical
qualification alone cannot authorize production under the changed runtime.

## Source and evidence identity

| Item | Identity |
| --- | --- |
| Approved design/amendment commit | `f1f5929` |
| Original Goal 061 source-manifest SHA-256 | `5879fbdaf7b3880151358319a7b7c7c0837463b06ba06f1a34fb80a3fbc2e36a` |
| Qualification 2 source-manifest SHA-256 | `f8653edeca65c4ddfc5c3433ee6d199897b8ee41de1d0dcd6b4ead15346ceefe` |
| Qualification 2 archive SHA-256 | `c41abbb56b104f62238b164c8177f731e8b4aeca60fb89bdf250aeb04e8647eb` |
| Qualification 2 receipt SHA-256 | `01952a5aaf2b027db06e40726172e35d6fefab265b147169110aa581c83fab65` |
| Complete current runtime canonical SHA-256 | `acd43764a5d0c2ee574007912a90236f669548a512c460cceb7768bb044e854a` |
| Frozen files / compressed bytes | 354 / 44,842,041 |
| Local evidence root | `artifacts/goal062_execution/qualification2/` |
| Remote execution root | `/data/codex/scratch/goal062-final-procedure-20261011-qualification2` |

The implementation is committed and pushed as `2d4a04b`. Its new source/test
bytes match the frozen manifest; that manifest records the preceding approved
design commit as the export's repository HEAD and binds all additions by hash.
All 165 files listed by the qualification receipt were returned locally and
rehashed with zero mismatches. The supervisor exited zero, with no remaining
process-group members and no resource stop.

A postqualification check on Deep rehashed all 354 frozen files, three input
receipts, 3,220 accepted reference-closure files, 97 public-package files and
165 qualification files with zero mismatches. Its additive receipt is
`postqualification-custody.json`, SHA-256
`4a050294181c021164d50cd160bccc45809c0d18c7b8db354c30be3fefe6006f`.
It also confirms that neither a production directory nor a runtime-approval
record existed at 03:25:48 UTC. Original qualification evidence is unchanged.

All 258 inherited scientific source, script and test files, together with
`pyproject.toml` and `uv.lock`, were verified byte-identical to the accepted
manifest. The new freeze adds the panel adapter, runner, independent auditor,
summary, qualifier, freezer, supervisor, five focused test files and approved
design/decision documents. Existing reference receipts retain their original
binding; new tables will retain the new binding. Neither is relabelled.

The original runtime, manifest and completion receipt accompany the new
freeze. Current executable/extension hashes and numerical-library configuration
are collected as new evidence. The old receipt has no corresponding binary
hashes, so identical numerical version labels do not establish binary identity.

## Execution and audit structure

The adapter preserves the frozen four-model fit, screen and Berger–Boos
decision. It generates observations separately from evaluator truth and makes
the main fit immutable before diagnostics. The runner completes and audits
all 466 missing reference tables before generating the evaluation panel.
It then records all main fits and declarations before held-out scoring.
Profiles and lower-bound lattices diagnose the fixed main fit and never
replace its estimate or decision.

Before production generation, the locked runtime will persist and verify
27,000 evaluation stage addresses and 20,000 bootstrap addresses, including
cross-domain uniqueness. The 5,000 histories retain their registered cell and
replicate identities across resumptions. Checkpoint reuse verifies hashes and
identity rather than silently refitting. An unverified artifact or a direct
reconstruction discrepancy blocks release; ordinary registered numerical
failure remains an observed endpoint under the frozen procedure.

The independent auditor reconstructs generators, main scores, fit-record
selection mechanics, all 765 observed screen scores, rank/tie arithmetic,
decisions, diagnostic points and held-out site/cluster contrasts. It does not
import the production panel adapter, fitter or likelihood. Summary code uses
all 500 histories per cell for outcome proportions and the registered
whole-history resampling for continuous summaries. Undefined bootstrap draws
are counted explicitly, without dropping and replacing them.

Qualification uses only mechanical root `987654321` and released public
fixtures. Its stages include frozen-source tests; selected old screen/effect
reference replay and direct-score comparisons; nine new mechanical reference
rows; eight accepted full-bank public refits; one mechanical history in every
cell; exact and B100-A diagnostic examples; measured budget projection; and
51 simultaneous producer/auditor workers for the memory probe. Synthetic rank
tables used here are explicitly mechanical and cannot qualify as a production
reference panel.

## Verification and superseded attempt

The final local check passed **65 focused tests**, Ruff across the 12 new
source/test files, strict mypy across seven source modules and `git diff --check`.
An earlier integration check also passed 68 targeted inherited tests. The
same final 65 focused tests passed on Deep in 14.52 seconds, with a receipt
bound to the frozen source and test log.

Qualification 1 used manifest
`e35633db8ab55cce7cf884748002ea20e7693ccd051ce761863e91e7588f3761`.
Independent closure review identified a remaining integrity defect: a finite
optimizer objective paired with missing final coordinates could not be
reconstructed yet did not stop release. The repaired auditor raises a release
hold for that inconsistent record while preserving the legitimate
`objective=1e300`, `raw_logjoint=null` optimizer-failure case. Its regression
test passed. This changes artifact validation, not the inferential rule.

The first qualification was explicitly stopped at 02:53:06 UTC, before
production, and its evidence was preserved under `qualification1/`. Its
supervisor finished with exit -15 after 69.745 seconds, with no remaining
process-group members. It cannot qualify the repaired source. Qualification 2
is a new directory and freeze; no failed receipt was overwritten.

## Resource and release boundary

The completed qualification provides the following numerical evidence. These
are mechanical checks, not estimates of scientific operating characteristics.

| Check | Observed result |
| --- | --- |
| Inherited reference compatibility | Nine effect tables ×999 rows and three screen tables ×99 rows re-audited; reconstructed arrays match accepted arrays exactly; maximum direct-score discrepancy `2.047e-12` nats |
| New mechanical references | Three nodes ×3 rows generated and independently audited using root `987654321` |
| Accepted public fixtures | Eight four-model full-bank refits; parameters, scores and numerical statuses match exactly |
| Ten-cell generator replay | All generator arrays match bitwise, including the four B100-A fields |
| Main fits and screening | 40 fits and 7,650 screen nodes independently scored; maximum discrepancies `6.822e-13` and `2.047e-12` nats |
| Cached decisions | 1,500 retained-node effect ranks independently rebuilt; rank probabilities agree exactly |
| Held-out scores | All four models and six contrasts per history audited; maximum discrepancy `1.137e-13` nats |
| Diagnostics | 886 profile and 2,700 lattice points reconstructed; maximum discrepancy `3.638e-12` nats; both cases pass the registered profile/lattice diagnostics |
| Memory | All 51 requested workers initialized; probe peak 30,690,643,968 bytes (28.58 GiB), 35.73 GiB with 25% headroom; whole-run supervisor peak 28.78 GiB |
| Qualification duration | 1,501.299 seconds within the qualifier, 1,503.778 seconds under the supervisor |

The concurrency probe measures loaded producer/auditor resources and
representative scoring. A simultaneous 51-optimizer peak remains unmeasured;
the supervisor enforces the production memory cap throughout execution.

The timing model gives 0.463 evaluation hours and 8.411 reference-generation
hours under ideal worker scaling. Those small-sample extrapolations are not
campaign forecasts. The qualifying gate instead retains the historical
36–40-hour reference allowance and uses the greater projection, **40.579 hours**
including its evaluation margin. This is below 72 hours. Retain the approved
**46–57-hour planning allowance** to cover timing variation, scheduling tails,
extra anomaly diagnosis, transfers and reporting. No resource reduction or
increase is being proposed.

Immediately before the second qualification, Deep had 121.15 GB available
memory and 4.499 TB free scratch. These are launch-time observations, not a
reservation. The supervisor bounds only its own process group and preserves
unrelated host work.

Production remains capped at 51 workers, one numerical-library thread per
worker, 64 GiB aggregate RSS, at least 50 GiB initial free scratch and one
persistent 72-hour wall deadline across resumptions. A resource stop leaves
unfinished work pending. The source-bound qualification must support the
selected workers and the projected complete workload before launch. Kernel
approval, if given after review, will bind the actual runtime and qualification
receipt without changing original receipts, scientific methods or workloads.

No production outcome or final-method operating rate is available from this
implementation and qualification work. B100-A results will remain descriptive
for the registered misspecification law, and the broader landscape,
competing-model and magnitude-interval questions remain separate.
