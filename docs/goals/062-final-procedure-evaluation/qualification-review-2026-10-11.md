# Independent review of Goal 062 qualification 2

11 October 2026 (Hobart). This review audits whether the completed
nonproduction qualification is an adequate basis for Barry to accept the exact
kernel-changed runtime and permit the already approved Goal 062 campaign to
start. Operationally, that claim requires the returned evidence to be complete
and immutable; the frozen source, tests, inputs and runtime to match their
bindings; the runner and independent auditor to agree on the registered
mechanics; the complete workload to fit the approved resource envelope; and no
production draw to have occurred. It does not require, and cannot establish,
that the method has favourable operating characteristics. Those are outcomes
of the prospective campaign.

## Verdict

**Conditionally supported.** Qualification 2 supports presenting the
[runtime amendment](runtime-amendment-2026-10-11.md) for explicit approval.
No evidence defect or document correction requires another qualification.
The condition is procedural and material: the current state is
`qualified_pending_runtime_review`, and production remains unauthorized until
Barry accepts the exact source, runtime and qualification bindings. This
review does not supply that acceptance.

The accepted identities for any approval record are:

- source-manifest SHA-256
  `f8653edeca65c4ddfc5c3433ee6d199897b8ee41de1d0dcd6b4ead15346ceefe`;
- complete current-runtime canonical SHA-256
  `acd43764a5d0c2ee574007912a90236f669548a512c460cceb7768bb044e854a`;
- qualification-receipt SHA-256
  `01952a5aaf2b027db06e40726172e35d6fefab265b147169110aa581c83fab65`.

The additive postqualification custody receipt has SHA-256
`4a050294181c021164d50cd160bccc45809c0d18c7b8db354c30be3fefe6006f`.
It corroborates continued remote custody but is not a substitute for the three
approval bindings above.

## Strongest supporting evidence

The receipt is internally coherent and its primary claims survive independent
reconstruction. All 165 listed evidence files rehash exactly. The 354-file
source manifest has no missing or extra payload files; every payload hash and
the 44,842,041-byte archive agree with the manifest, and the archive contains
only the expected safe regular-file members. All 334 inherited files are
unchanged, including the 258 scientific source, script and test files. The
three frozen input receipts also rehash exactly. The bound Linux test log
records 65 passes in 14.52 seconds and has the registered test-set identity.

The numerical evidence covers distinct parts of the production path. Twelve
selected inherited reference tables passed their accepted audit bindings and
direct rescoring; their reconstructed arrays were identical and the largest
direct-score discrepancy was `2.046e-12` nats. Three new mechanical effect
tables passed independent row, address, status and score audit. Eight public
histories reproduced all four fitted models with exactly equal parameters,
scores and numerical statuses. One mechanical history in each of the ten
cells passed bitwise generator replay and independent main-fit, screening,
decision and held-out checks; two also passed profile and lower-bound-lattice
diagnostics. Across these histories the audit covered 40 fits, 7,650 screen
nodes, 1,500 retained-node effect ranks, 60 held-out contrasts, 886 profile
points and 2,700 lattice points. Rank results were exact; the largest score
difference was `3.638e-12` nats.

The supervisor exited zero after 1,503.778 seconds, left no process-group
member, and recorded neither a resource stop nor pending work. The concurrent
probe initialized all 51 requested workers with producer and auditor resources
loaded. Its process-group peak was 30,690,643,968 bytes; adding 25% gives
38,363,304,960 bytes, leaving 30,356,171,776 bytes below the 64-GiB cap. The
whole qualification peaked at 30,900,539,392 bytes. Independently recomputed
timing terms give 0.463 evaluation hours, 8.411 measured reference hours, and
a conservative historical upper projection of 40.579 hours, below the 72-hour
deadline. The approved 46--57-hour planning allowance remains the credible
schedule because the benchmark samples are small.

Finally, the receipt records zero production reference rows and histories and
`production_authorized=false`. The later remote custody check reports no
production directory or approval record and zero mismatches across 354 source,
three input, 3,220 old-reference-closure, 97 public-package and 165
qualification files.

## Strongest threats, ranked by scientific consequence

1. **Previous-runtime binary identity is unknowable.** The old receipt did not
   hash the Python executable or numerical extension binaries. The old and new
   records agree on Python 3.14.5, NumPy 2.5.1, SciPy 1.18.0, PCG64, x86-64 and
   glibc 2.39, and differ in the recorded core fields only at Linux kernel
   `6.8.0-142-generic` versus `6.8.0-146-generic`. The qualification therefore
   demonstrates strong finite numerical compatibility, not binary equivalence.

2. **Rare production-only numerical behaviour remains possible.** Ten
   mechanical histories, eight public refits and selected old references are
   unusually broad qualification evidence, but they are a minute fraction of
   465,534 new effect-reference histories and 5,000 evaluation histories.
   Shared numerical libraries and parts of the same mathematical specification
   also leave scope for common-mode error. A rare optimizer, filesystem or
   kernel-dependent failure could first appear during production.

3. **The resource extrapolation does not reproduce the full campaign.** The
   memory probe held all 51 workers concurrently with the required resources
   and representative point scoring, but it did not run 51 simultaneous full
   optimizers through their worst states. Reference timing is projected from
   nine produced rows and assumes ideal worker scaling; evaluation timing is
   based on ten histories. Queueing, long optimizer tails, I/O and anomaly
   diagnostics can therefore exceed the point estimates. The large measured
   memory margin, persistent 64-GiB supervisor and retained 46--57-hour
   allowance reduce this to a managed residual risk rather than a reason to
   reject qualification.

4. **Custody after return is evidenced at two levels of detail.** The local
   165-file closure was independently enumerated and rehashed. The later
   producer-side remote custody receipt is a content-hashed aggregate
   claim with counts and zero mismatches, rather than a returned per-file
   listing independently reconstructed here. Its value is corroborative; the
   launch-time checks remain necessary.

These threats could overturn a claim of universal equivalence or guaranteed
completion. Neither stronger claim is made in the proposed amendment.

## Independent checks performed

| Check | Outcome |
| --- | --- |
| Qualification, runtime and source identities | Exact; qualification state and authorization flags agree with the proposal |
| Returned evidence manifest | 165 of 165 hashes exact; no eligible benchmark evidence omitted |
| Frozen source and archive | 354 of 354 payload hashes exact; expected set and safe archive membership exact |
| Inherited source and input custody | All 334 inherited files and all three input receipts exact |
| Test binding | Five test files, canonical test-set digest and Linux log exact; 65 passed |
| Runtime comparison | Five nonplatform core fields exact; only the kernel differs among the six old core fields; current executable and extension hashes recorded prospectively |
| Cell, phase and randomness identities | Ten distinct cells, `replicate=0`, history index `cell*500`, mechanical root `987654321`; all 54 checked addresses and recomputed uint64 seeds exact and unique; B100 truth/background-stage rules exact |
| Stage and audit closure | Inputs, main, decision and holdout closure in all ten histories; diagnostics only in the two intended histories; every stage receipt and JSON/NPZ binding exact |
| Numerical reconstruction | All generator, fit-selection, score, rank, decision, held-out and diagnostic checks passed within the registered tolerances |
| Reference compatibility | Twelve inherited tables and their accepted provenance checked; three mechanical tables independently checked; eight public four-model refits exact |
| Budget and memory arithmetic | Recomputed from raw timings and byte counts; both gates pass, with the limitations ranked above |
| Production exclusion | No production output in the qualification, launch or postqualification evidence |

During this review, opening the three returned mechanical SQLite databases for
integrity checks removed their transient, unbound `-wal`/`-shm` sidecars. The
WAL files had been observed at zero bytes, those sidecars are excluded from the
receipt and stage-complete bindings, and all three database hashes and all 165
bound evidence hashes remained exact afterwards. No inherited production
reference database was opened. SQLite reported all three databases `ok`.

## Required gates before reliance

No additional refit, sensitivity analysis or source correction is required to
decide the runtime amendment. Before any production draw, Barry must explicitly
approve the amendment with the three exact hashes above. The launch path must
then rehash the frozen source and runtime, verify the approval binding, persist
and validate the registered 27,000 evaluation-stage and 20,000 bootstrap
addresses, recheck the 51-worker, one-thread, 64-GiB, scratch and 72-hour gates,
and fail closed on any mismatch. A changed runtime, source, resource envelope,
seed ledger or scientific method requires a new decision under the
[registration](registration-2026-10-11.md).

Production results cannot be relied upon until the full reference panel and
all 5,000 histories complete under those bindings and the registered
independent audit passes. Numerical failures must remain outcomes; a source,
scorer or integrity discrepancy remains a release hold rather than an
abstention.

## Residual uncertainty

After those gates, residual uncertainty will remain about rare numerical and
resource-tail events and about common-mode defects not exposed by the finite
fixtures. The persistent supervisor, immutable checkpoints and exhaustive
production audit are the appropriate controls. Qualification provides no
evidence yet about declaration, abstention, recovery or predictive-performance
rates, and it does not widen inference beyond the fixed map, design, model
bank, algorithm and realised reference panel registered for Goal 062.
