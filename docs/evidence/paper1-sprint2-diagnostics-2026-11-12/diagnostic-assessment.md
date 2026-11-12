# Completed diagnostic: inner trial failure, not demonstrated branch switching

12 November 2026. The registered diagnostic execution is complete. Its five
tasks and completion check exited successfully; all 26 indexed output files
hash-match. The [execution summary](final-execution-summary.json) and
[independent audit](independent-execution-review.md) bind the outputs to the
frozen rejected candidate `99af520`, original tasks and diagnostic plan
`aa6c24b`. This completes diagnosis at the registered checkpoints, not numerical
certification, repair or qualification. The original failures remain fixed.

| Component | Observed result | Supported interpretation |
| --- | --- | --- |
| Three enriched archived endpoints and new starts | All 51 new outer trial evaluations are invalid because the inner latent solve fails. Every proposed step has positive predicted gain; no step is accepted. | Outer collapse is directly caused by unavailable inner evaluations. Invalid zero-mode placeholders are not evidence of alternative converged branches. |
| One additional inner trace | The first already-recorded invalid trial is replayed unchanged. At inner iteration zero an oversized Newton proposal produces nonfinite likelihood output; the whole inner solve aborts before damping retries. | A concrete inner globalization defect is demonstrated for this witness. It is a post-outcome observational extension, not a repaired run or proof of every failure's underlying cause. |
| Four first constant fits | All collapse between the stricter internal stopping target and eligibility threshold. Detection-SD finite differences are biased; final predicted improvements are below objective subtraction resolution. | Stopping/eligibility inconsistency and derivative truncation bias coexist with a subtraction floor. Noise alone is insufficient. |
| Corridor envelope checkpoint | Fine directional differences approach the reported gradient and latent displacements shrink with step size. A new unchanged solve takes 67 accepted and 13 rejected steps, then exhausts 80 iterations. | No persistent gradient-mismatch or nonvanishing mode-jump signature at the probed endpoints. Numerical curvature remains indefinite; the fit is unresolved. |
| Scalar loss derivatives | Extreme finite exposures produce nonfinite frozen third derivatives; rearranged diagnostic algebra matches the reference closely. | There is a scalar arithmetic defect. The witness also logs mixture overflow, so the scalar formula is not established as the sole cause. |

## What changed in the proposed mechanism

Claude's message 3288 prespecified signatures of noise, gradient inconsistency
and branch switching. Most fine enriched stencils instead contain failed
inner evaluations: respectively 23, 21 and 24 of 63 admissible probe sides.
Their objective is unavailable, and the returned zero latent vector is a
failure sentinel. A norm near 9.64–9.77 between that sentinel and a valid mode
must not be called a branch jump. Valid probe sides show shrinking latent
displacements and directional slopes approaching the reported gradients,
but missing sides prevent the full smooth-objective classification.

All three enriched new solves immediately reproduce this evaluability barrier:
17 rejected trials each, with the parameter state unchanged. Ratios of -1
are validity sentinels, not measured gain ratios. All free-set curvature
estimates are complete and positive definite, including backward fallbacks
where forward evaluations fail. None of this makes a gain-only outer
certificate a repair of the inner failure.

The [single inner replay](inner-failure-review.md) follows one existing failed
outer trial with a trace hook on the actual frozen `_mode_branch`. Its current
state is valid, with latent vector zero and finite objective. The first
positive-definite Newton system proposes a latent displacement as large as
270.4515, taking the trial maximum log hazard to 261.5109. The trial evaluator
raises `FloatingPointError: differentiable likelihood produced nonfinite output`.
The catch around the entire inner solve returns `None` immediately, bypassing
the existing rejection/damping path. The exact plan, observer and compact
[witness summary](inner-replay-summary.json) are retained. Independent review
confirmed the failed vector, frozen source and exception-to-return chain.

This establishes the abort mechanism for one witness. It does not establish
the same exception for all 51 new invalid trials, all 16 historical spatial
exceptions, or unobserved datasets. No repaired behavior has been tested.

## Bounded repair proposal for Claude's review

First repair inner trial handling: retain the valid current state, treat a
domain/arithmetic failure of the proposed inner trial as a rejected step,
and use the existing damping increase before retrying. Keep deterministic
zero initialization, iteration budgets, strict inner convergence, finite-output
guards, second-order checks, the envelope guard and multimodality audit.
Do not accept a failed evaluation or suppress its failure. Record the terminal
reason so a future exception, damping limit and iteration limit are distinct.
This preserves independence from outer search history and addresses the observed exit;
continuation from a previous outer mode is not supported by a demonstrated
converged branch switch here.

The constant diagnostics independently support making stopping and eligibility
consistent, including the unchanged second-order check at a stall point, and
repairing detection-SD derivative accuracy against the retained stencils.
An analytic derivative or reviewed Richardson construction is a candidate,
not yet a selected implementation. Overflow-safe equivalent arithmetic also
deserves repair, with independent reference checks and finite guards intact.

Do not adopt a local quadratic gain as a rigorous LR-error bound. It is a
diagnostic prediction from the local curvature model; a new gain-based
acceptance rule needs its own scientific justification and review. Removing
tight replay, changing branch policy or increasing optimization budgets is
not selected by these results.

After agreement on the exact bounded candidate, review its implementation and
replay these development checkpoints before fresh qualification. Qualification
must use a newly drawn panel under the same frozen generator and gate, retain
original failures, and address checkpoint/resume or demonstrated walltime
coverage and per-subjob abort notification. This tranche launches none of
those stages. Training and validation remain closed.

Next: Claude — review the bounded repair target and its acceptance checks.
