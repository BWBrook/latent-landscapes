# Prospective boundary-reporting and resume acceptance deviation

16 November 2026. Proposed specification for independent and reciprocal review,
before any A+B+C+D_boundary acceptance outcomes. **Execution is not approved by
this document alone.** Final candidate/implementation hashes, review disposition
and the exact equivalence normalization must be attached before target replay.

This advances Paper 1's numerical-qualification decision under board 3450.
The [design review](design-review.md) supplies the qualified mathematical and
execution rationale. The 12 November plan remains the historical specification
of the A+B+C run; its 15 November failed verdict is not re-scored. Original
qualification rejection, archived receipts and failure classes remain fixed.

## Declared scientific deviation

The next candidate retains A+B+C and adds an explicit reporting closure for
the positive-variance component, named **D_boundary**. This is distinct from
the conditional arithmetic D in the earlier plan, which remains deferred.
The only changed numerical-comparison quantity is the positive component's
reported closed criterion and its consistently closed free normalizer.

At an exact fixed h, let P be the retained raw positive endpoint and Z the
retained fitted sigma-zero endpoint at that same h. For comparison, use
`closed_positive = max(P.criterion, Z.criterion)`. For a free-h comparison,
use the maximum of the two retained free family criteria; if Z wins, report
its h and nuisance values as the boundary endpoint. Do not use a sigma-zero
free optimum as a fixed-h reference at another h.

Both raw endpoints remain present with their original parameters, eligibility
and diagnostics. A strict boundary win has `boundary_supremum = true` and
reported sigma = 0; no finite or infinite log-sigma is substituted into raw
optimizer state. This is a retained lower bound supported by inclusion of the
continuous zero-variance limit, not a claim of global maximization.

The baseline closure is calculated only from the archived, hash-frozen
baseline raw positive and sigma-zero rows. It does not refit or overwrite
the baseline. The candidate closure uses its corresponding retained rows.
The prior failed A+B+C receipts are never rewritten with these values.

## Unchanged sample, locations and thresholds

Use the exact selection in
`../paper1-sprint2-repair-2026-11-12/replay-selection.json`, SHA256
`099f28d9a45a8a4eb12b103ddaf23714ed3ced72120bb5c9184c9c75e514dfaf`:

- The same 24 originally resolved non-regression tasks, selected two per
  arm-by-role stratum, and all 27 originally failed development tasks.
- The same 12,460 exact required baseline view/location anchors, including
  standard/tight spatial components and the reduced families; no interpolation,
  nearest-node replacement, alternate start sample or task substitution.
- Absolute criterion shift at most `1e-6`, profile-LR shift at most `1e-3`,
  and unchanged eligibility at every required comparison.
- The same derivative checkpoints, inner witness, scalar arithmetic decision,
  numerical iteration/point budgets, zero starts, domains, cutoffs, tight
  replay, envelope guards, audit starts/selection and multimodality checks.
- Corridor-1 window-low B remains outside tuning scope and remains failed if
  unresolved under the existing numerical budgets.

All envelope, sigma-zero, reduced-family and overall envelope-LR comparands
remain raw and unchanged. Only a positive-component criterion comparand is
replaced by its closed value. Its component LR must be calculated as
`2 * (closed_positive_free - closed_positive_at_h)` separately on each side.
This can change a component LR; it does not change the overall envelope LR.
Keep raw component criteria/LRs in the output for inspection.

When both required endpoints are eligible, this closed positive criterion is
algebraically the existing spatial envelope, and its closed component LR is
the envelope LR. Those revised numerical checks therefore duplicate the
envelope checks. They no longer independently demand agreement of the raw
positive endpoints; they do not demonstrate improved raw positive optimization
accuracy. This consequence of the changed reporting definition is explicit
for reciprocal review, rather than a retrospective justification of the old
failed checks. Raw eligibility remains separately checked.

Required-family eligibility remains the raw fit's eligibility. Closure cannot
turn an ineligible or missing positive fit into a passing required family or
remove an unresolved-above-envelope condition. Report such a failure directly.
Free closure must carry the selected boundary h honestly while exact-anchor
evaluation and warm starts continue to use the unmodified raw fit state.

## Focused pre-replay checks

1. A direct criterion-limit test at sigma in `{1e-2, 1e-3, 1e-4}` approaches
   `evaluate_sigma_zero` at the same fixed h and nuisance parameters. Use an
   independently calculable site-likelihood fixture and the actual normalized
   smooth determinant floor; verify the leading sigma² behavior rather than
   demand a coefficient derived from an un-floored determinant.
2. Reporting tests cover a strict boundary win, an interior win, an exact tie,
   fixed-h mismatch rejection, differing h of free family optima, and invalid
   or absent raw eligibility. Verify raw rows, envelope, raw ownership/contact
   choices, starts and guards are unchanged. No `log_sigma = -inf` may enter
   optimizer state.
3. Comparison tests close archived baseline and new candidate values
   symmetrically, use the correct closed positive free normalizer, preserve raw
   evidence and eligibility, and retain the exact frozen anchor/digest contract.
   They must not alter or re-score the 15 November receipt set.
4. Resume equivalence uses one small deterministic fit, uninterrupted and with
   controlled interruptions inside search and at each resumable stage boundary.
   Every completed operation/stage is restored under strict source/input/runtime
   identity. An unfinished operation is restarted without introducing a new
   numerical start or logical budget.
5. Equivalence means byte-identical canonical scientific payloads under a
   closed, field-specific normalization agreed before execution. Raw nested
   file hashes are first validated. Excluded execution-only fields, including
   timing, host/PBS segment metadata, resource telemetry and their path/hash
   derivatives, must be enumerated by the implementation and reviewed; generic
   recursive dropping of all `cost`, `hash` or diagnostic fields is prohibited.
   Numerical rows/order, selections, eligibility, classifications, topology,
   cutoffs, guards, audit results and scientific diagnostics remain exact.
6. Resume rejection tests cover changed source/input/runtime/options,
   malformed or tampered checkpoints, invalid journal ordering and partial
   writes. Output existence alone is never sufficient evidence of completion.
7. Independent code review checks the complete reporting, comparison,
   persistence and PBS path before target acceptance execution. Local tests
   are implementation evidence, not an acceptance result.

The implementation must record the exact deterministic fixture, interruption
locations and normalization field paths with the passing test results. These
are execution-freeze items, not details to choose after a resumed result differs.

## Execution allowance and historical recovery smoke

Each new acceptance fit may use at most **three total 48-hour segments**,
with `afterany` dependencies, per-segment logs and abort notification. Terminal
scientific outcomes are not rerun by later segments. Missing a terminal fit
receipt after segment 3 remains explicit execution loss; it is not a fabricated
scientific fit result and counts as failed under any later qualification gate.
This authorizes a prospective maximum of 144 allocated hours per fit; all
numerical iteration and point budgets remain fixed. Record segment time and
repeated incomplete-operation effort separately.

Before a fresh panel, recover the two walltime-killed development fits from
their preserved complete search-stage receipts, under their original
`a77e849` numerical source, original inputs and runtime. An explicitly identified
resume adapter may be used only with its own recorded code hash and a reviewed
contract that preserves those old numerical bindings. Do not silently import
an old search into the new scientific candidate or change source checks to
allow a mismatch. Write new recovered attempts separately and retain both
original incomplete attempts. This smoke is A+B+C development evidence, not
new qualification or retroactive completion of the original run's verdict.

The 42 historical missing qualification tasks had heterogeneous execution
evidence, including node reboots/ghost allocations. Only the two latest routed
logs establish 48-hour kills. Resume addresses interruption resilience without
claiming all historical losses have the same demonstrated cause.

## Freeze and review boundary

Before submission, bind this specification, final candidate source, comparison
implementation, resume/PBS code, unchanged selection, runtime and input hashes
in one execution-freeze record. Attach independent review and Claude's
reconciliation. Any necessary change after that is another recorded deviation,
not an unmarked update to this specification.

Only then run the 51-task replay and exact non-regression probes with resume
active. Preserve every attempt, segment and remaining failure reason. Do not
automatically promote from development results to fresh qualification. Drawing
a new panel requires the recorded acceptance assessment and reciprocal
scientific reconciliation; training and validation remain closed throughout
this implementation tranche.

Next: Claude — review this prospective deviation and its explicit equivalence clarification before target acceptance execution.
