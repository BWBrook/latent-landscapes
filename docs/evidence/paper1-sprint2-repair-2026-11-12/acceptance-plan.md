# Bounded numerical repair: frozen acceptance plan

12 November 2026, before repaired-candidate outcomes. This implements Claude's
accepted specification in board message 3307 and advances Paper 1's numerical
qualification decision. The rejected `99af520` candidate, original attempts,
failure classifications and qualification verdict remain fixed. These inputs
are development data; training and validation remain closed.

Implement only A, B and C from that message: invalid inner-trial rejection with
the existing damping path; consistent stopping/eligibility with the unchanged
second-order check; and nuisance Richardson derivatives. Preserve deterministic
zero starts, evaluator domains, budgets, envelope and multimodality guards.
Predicted gain remains diagnostic only. Arithmetic repair D is conditional on
the archive exposure query below; do not silently broaden this candidate.

## Checks frozen before candidate runs

1. Unit coverage: an invalid inner trial is damped and later converges; an
   invalid initial state fails; initial-invalid, damping-limit, iteration-limit
   and converged exits are distinct; invalid-trial rejections and iteration
   counts are retained. Eligibility requires successful evaluation, projected
   gradient within the existing threshold and a passing second-order check,
   including at a stall. Test inside/passing, inside/failing and outside cases.
2. Richardson: use `(4 D(t/2)-D(t))/3`, base relative step `t=1e-3`, for both
   log h and detection SD. Interior differences are central. At a fitted bound,
   stay inside the unchanged domain and record the bounded stencil explicitly;
   do not claim fourth-order cancellation for an unsymmetric first-order
   stencil. Independently review boundary handling before fit replays. At the
   four already frozen constant endpoints, the detection-SD gradient must
   agree with the converged small-stencil values within `5e-6`. Record additional
   evaluation cost. No parameterisation or analytic-derivative change.
3. Non-regression: select 24 of the 417 resolved tasks, two from each of the
   twelve arm-by-role strata (A/B/C times dense/lean/independent-bank/exhaustive).
   Within a stratum use ascending SHA256 of
   `repair-3307-nonregression-v1:` followed by the task ID. All fits contain the
   three fitted families. Freeze their IDs and baseline receipt hashes before
   repaired fit execution. Require absolute criterion shifts at most `1e-6`,
   profile-LR shifts at most `1e-3`, and unchanged eligibility verdicts. Compare
   the same families/locations; use exact evaluations, not interpolated matches.
   A regression triggers diagnosis, never changed thresholds or replacement.
4. Development replay: all 27 original failed tasks (14 datasets), all three
   enriched endpoints and the exact inner witness. Preserve original starts,
   budgets and required families/cutoffs/tight replay; retain new attempts
   separately. Report terminal reasons, invalid-trial counts, distributions of
   inner iterations to convergence and wall time per fit. This is not a gate.
   Before fresh qualification, require no remaining inner-exception aborts and
   a recorded, understood reason for every remaining failure. Corridor-1
   window-low B's unresolved envelope/budget case stays a failure if unresolved;
   no tuning or budget expansion for it.
5. Arithmetic condition D: query archived extrema from all 417 resolved fits.
   Include an equivalent overflow-safe arithmetic repair only if its log-hazard
   overflow threshold is within ten units of the largest retained mode.
   Distinguish observed extrema from bounds or unavailable archived quantities.
   If the archive cannot answer directly, document that limitation and review
   the smallest valid check before including D.

Independent code review precedes frozen target checks. Unit tests during
implementation verify the specified paths; they do not replace review or
target replay. Do not tune the implementation to outcomes after freezing it.
Record any necessary protocol clarification or diagnostic extension explicitly.

## Completion and next boundary

Freeze source, runtime, inputs and the comparison implementation before target
submission. Use a separate candidate checkout; never update the rejected
campaign checkout or overwrite original attempts. Report execution losses
separately from numerical failure and preserve all receipts. Routine submissions
may proceed after review within this accepted repair envelope.

After the frozen checks and reciprocal scientific reconciliation, prepare a
new qualification panel under the same generator and gate, with resumability
and per-subjob abort notification. No fresh panel, training or validation is
opened by this implementation step. Report any unresolved scientific or
resource limitation; do not equate a completed replay with qualification.
