# Independent implementation review: Goal 062 final-procedure evaluation

11 October 2026 (Hobart). This is a read-only adversarial review of the
implemented ten-cell Goal 062 adapter, runner, independent auditor,
qualification workflow, supervisor and synthesis. It follows the prospective
[registration](registration-2026-10-11.md),
[amendment](amendment-2026-10-11.md),
[design review](design-review-2026-10-11.md) and
[amendment review](amendment-review-2026-10-11.md).

The implementation accepted for remote non-production qualification is bound
by the SHA-256 of
`artifacts/goal062_execution/qualification2/source-manifest.json`:

`f8653edeca65c4ddfc5c3433ee6d199897b8ee41de1d0dcd6b4ead15346ceefe`.

I independently reproduced that digest. I also checked all 12 new source,
runner and test paths against both the manifest entries and the frozen
`qualification2/source/` payload; all three identities agreed. The manifest
records the unchanged Goal 061 binding
`5879fbdaf7b3880151358319a7b7c7c0837463b06ba06f1a34fb80a3fbc2e36a`,
258 verified inherited source/script/test files and no inherited scientific
source changes.

## Claim audited

The implemented system claims to preserve the frozen Goal 061 likelihood and
procedure while evaluating 500 complete histories in each of the six exact and
four B100-A cells. It must complete and audit the full 765-node reference panel
before evaluating histories; keep truth outside the fitter; retain the original
299 and new 466 reference bindings; use producer statistics for decisions and
separately reconstructed values for audits; preserve inclusive ranks, failures
and all-500 denominators; lock declarations before holdout and diagnostic work;
and resume only from hash-bound immutable artifacts. It must also freeze all
27,000 evaluation addresses and 20,000 bootstrap addresses before any new
production reference generation.

For this claim to hold, the fitter records and decision inputs must be
internally consistent, audit failures must block release rather than be
relabelled as numerical outcomes, qualification evidence must be bound to the
frozen source, and resource or runtime drift must fail closed. Plausible
alternatives are an adapter-induced change to the frozen procedure, truth
leakage, incomplete or mixed reference caches, corrupt fit bookkeeping that
still passes audit, biased complete-case reporting, a stale qualification
binding, or resource failure that silently changes the experiment.

## 1. Audit verdict

**Supported for bounded non-production qualification.** The final source
implements the registered ten-cell procedure and closes every material defect
found during this review. I found no remaining source-level reason to withhold
the remote qualification run against the exact binding above.

This verdict does not establish that remote qualification has passed, that the
target runtime is approved, that production will fit within its resource
envelope, or that any scientific result has been generated. It confers no
production authority. Production remains contingent on a completed and
independently reviewed qualification receipt and any required human runtime
approval.

## 2. Strongest supporting evidence

- The freeze verifies the exact Goal 061 manifest and archive payload before
  adding non-overlapping Goal 062 files. Original runtime and completion
  evidence are copied rather than reconstructed.
- The fitting boundary receives observations, the public design and numerical
  bank, but no truth, cell effect, generator field or holdout information.
  B100-A generating beta is explicitly undefined.
- The runner constructs and independently audits every new reference table,
  then freezes one complete cache before any history evaluation. Original 299
  and new 466 tables retain their separate bindings. Producer and auditor
  statistic arrays remain distinct.
- The independent main-fit audit enforces the exact fit and start schemas,
  deterministic starts, nested candidates, selection and Powell rules,
  numerical status, evaluation counts, objective gaps, boundary flags and
  fixed-parameter constraints. It independently scores the selected points and
  reconstructs the observed effect statistic. Extra nested parameter payloads
  are rejected.
- Screening and effect decisions are independently rebuilt with the registered
  inclusive plus-one ranks. Cached rows must identify the exact
  `history-NNNN` case. Invalid tables and verified numerical failures propagate
  to the registered abstention or unavailable states.
- Synthesis requires exactly replicate IDs 0--499 in every cell. Declaration,
  non-declaration, abstention and recovery categories retain denominator 500.
  Bootstrap summaries use the registered whole-history indices, Type-7
  quantiles and failure rule. One valid resampled observation supports a
  defined mean, median or quantile; only zero-valid or nonfinite resamples count
  as undefined. Nuisance error and physical-discrepancy summaries now receive
  the same registered uncertainty treatment.
- Main and decision work for all 5,000 histories precedes an immutable
  declaration lock. Holdout and diagnostic stages follow it. Existing stage
  receipts, hashes, addresses and phase labels must match exactly on resume.
- Before production reference generation, the runner persists and hashes the
  complete 27,000-row domain-1 evaluation ledger and 20,000-row domain-2
  bootstrap ledger. It verifies exact evaluation membership, uniqueness within
  each ledger and absence of collisions across all 47,000 derived seeds.
- The supervisor enforces one persistent 72-hour production deadline, a
  process-group 64-GiB limit, minimum scratch space and the qualified worker
  ceiling. Production source and runtime must match the qualification binding;
  permitted kernel-only drift still requires explicit approval tied to the
  source, runtime and qualification evidence.

## 3. Findings and corrections

| Finding | Scientific consequence | Final disposition |
| --- | --- | --- |
| Summary publication targeted its own populated input directory | Could fail or leave ambiguous final synthesis artifacts | Corrected with separate temporary staging, immutable publication and a resume test. |
| `observed_effect_statistic` was consumed without an independent comparison | A changed decision statistic could pass the main audit | Corrected by reconstructing it from independently scored adjusted fits; a mutation test blocks discrepancies. |
| A single cached row could be accepted under the wrong case identifier | An audit could bind one history's decision to another history | Corrected by requiring the exact `history-NNNN` identity in the case list, screen and decision rows. |
| Main-fit audit did not fully validate starts, selection bookkeeping or the top-level schema | Corrupt status, starts, objective gap, flags, counts or shadow parameters could survive audit | Corrected with exact fit/start schemas and frozen-selection reconstruction, including rejection of nested parameter smuggling. |
| A finite optimizer objective paired with nonfinite final coordinates was initially treated as a terminal numerical outcome | The auditor could not verify how an internally inconsistent record affected selection | Corrected in the final source: this condition raises `AuditStopError` and blocks release. A genuinely invalid objective (`1e300`, no finite raw score) remains an accepted observed numerical failure. |
| Qualification did not initially bind the failure, rank, resume and synthesis regression tests | Unit results could not serve as qualification evidence | Corrected by running all five frozen Goal 062 test files in a subprocess and recording their source hashes, command, interpreter, log and exit status in the qualification evidence. |
| Bootstrap support and undefined-draw accounting conflated one valid observation with an undefined statistic | Sparse endpoints could receive incorrect undefined counts | Corrected for cell summaries and independent-cell contrasts, with explicit zero-, one- and two-support tests. |
| Nuisance errors lacked the registered bootstrap intervals | Secondary error summaries were incomplete | Corrected for means, medians and the five Type-7 empirical quantiles; B100-A beta remains correctly not applicable. |
| Extended bootstrap addresses were deterministic in code but not prospectively frozen with the evaluation ledger | The amended seed-freeze gate was incomplete | Corrected by the 20,000-row domain-2 ledger and the cross-ledger 47,000-seed uniqueness check before reference production. |

The first frozen package, `qualification1`, is superseded. Its manifest digest
is `e35633db8ab55cce7cf884748002ea20e7693ccd051ce761863e91e7588f3761`;
it contains the pre-repair audit source
`d97b2b71b79c4fd03aa2b12367a21a916e143e617e3c2c207b1d7a1fe3814f09`.
The accepted `qualification2` audit source is
`da8d2ec965f9a3b8a1d9719cd188391cfbd40395cfb8a14749caae3fefedc072`.
Any Qualification 1 runtime output is therefore historical superseded evidence
and cannot qualify production.

## 4. Independent checks and outcomes

- I traced the registration and amendment through the freezer, evaluator,
  auditor, runner, qualifier, supervisor and summarizer. The final code paths
  preserve the frozen likelihood boundary, truth isolation, cache ordering,
  rank rule, failure states, denominators, phase order and resume invariants.
- I inspected the repaired audit against the frozen fitter's actual
  `FitResult`, `StartRecord`, multistart ordering, nested-candidate and Powell
  selection rules. The selected point and score now have both mechanical and
  independent numerical checks.
- I checked the repaired bootstrap logic for original support of zero and one,
  resampled support of zero and one, independent-cell contrasts and nuisance
  summaries. The code now matches the literal registered distinction between
  insufficient original support and an undefined resampled statistic.
- I checked that `production()` calls `freeze_seed_ledgers()` before
  `prepare_reference_cache()`, and that the receipt hashes both ledgers. The
  test derives production seeds only; it does not generate a production
  history or reference row.
- I checked the frozen qualification gate: it verifies the five test-file
  hashes from the source manifest, runs them from the frozen source with the
  controlled qualification environment, records the interpreter identity and
  log, and fails qualification on any nonzero exit. The qualification writer
  binds all benchmark evidence files in its final receipt.
- I independently verified the Qualification 2 manifest digest and the 12
  new implementation/test file identities. No mismatch exists between the
  live reviewed files, manifest hashes and frozen payload.

The implementation team reports that, before the Qualification 2 freeze, all
65 Goal 062 tests passed, Ruff passed over the 12 new files, and strict mypy
passed over the seven source modules. I inspected the relevant tests and source
but did not rerun those suites in this read-only review. All 68 inherited tests
were also reported green during implementation. These local results support
the launch of qualification; they are not a substitute for the frozen remote
qualification receipt.

No production seed was used to generate a history, no new production reference
row was generated, no full production fit was run and no remote qualification
result was available when this record was written.

## 5. Required gates before the implementation can be relied upon

1. Complete bounded remote non-production qualification against source-manifest
   digest `f8653edeca65c4ddfc5c3433ee6d199897b8ee41de1d0dcd6b4ead15346ceefe`.
   Do not substitute a Qualification 1 receipt.
2. Independently inspect the Qualification 2 receipt, its bound pytest log,
   selected inherited reference re-audits, mechanical new-reference audits,
   public fixture refits, ten-cell stage receipts, time projection, 51-worker
   memory probe and all recorded hashes.
3. Confirm the live numerical runtime. If the only permitted difference is the
   recorded kernel drift, obtain the explicit human approval bound to the final
   source, runtime comparison and Qualification 2 receipt before production.
4. At production start, verify that the two immutable ledgers and their audit
   receipt are written before any new reference row. Complete and audit all 765
   reference nodes before drawing any evaluation history.
5. Preserve all 5,000 addresses and all failure, abstention and pending states.
   Release results only after the complete history audit and synthesis receipts
   receive an independent scientific closure review.

## 6. Residual uncertainty

Source review and local tests cannot establish remote runtime compatibility,
wall time, peak concurrent memory, filesystem behaviour, optimizer convergence
rates or the realised frequency of invalid reference and history fits. Those
questions remain for Qualification 2 and, if it passes, the bounded production
run. The generator replay audit also shares the inherited spatial spread
kernel with production, so it cannot exclude every common-mode kernel defect.

Even after successful execution, the scientific result remains conditional on
the registered ten synthetic cells, one map, design, bank and realised
reference panel. It will not establish landscape generality, panel-marginal
calibration, robustness to other misspecification laws, causal isolation of the
background field, or confidence-interval coverage. This implementation review
authorizes neither broader claims nor production execution.
