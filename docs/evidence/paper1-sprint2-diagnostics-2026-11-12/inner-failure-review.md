# Independent review of inner-evaluation failure

12 November 2026 · Codex (GPT-6.1 Sol). This advances the Paper 1 numerical
qualification decision. This review reads the frozen solver, completed
development diagnostics and the subsequent unchanged observational replay.
The independent reviewer made no model runs or production changes.

## What is demonstrated

All three enriched new-start traces contain 17 rejected outer trials. Every
trial returns `success=false`, `mode_success=false` and `latent mode did not
strictly converge`. No trial is accepted and each current parameter vector
stays unchanged. The outer ratio of -1 is the code's invalid-candidate sentinel,
not a measured ratio of actual to predicted gain. Thus the immediate cause of
these 51 rejections is unavailable inner evaluation, rather than observed poor
agreement between a finite objective and its local model.

The unsuccessful mode returns a zero vector in `mode()`
(`spatial_profile.py:648–663`). Its displacement from the valid baseline mode
is not an alternative converged branch. These records therefore do not supply
the registered branch-switching signature. Their unavailable directional
differences must remain unavailable, even when a stored failure vector has a
large apparent displacement.

The registered sweep output alone cannot distinguish why `_mode_branch`
returned `None`. It uses that same return for the damping limit, the iteration
limit and caught evaluation/numerical exceptions. The outer result discards
the relevant inner iteration and state. This motivated the bounded
observational extension below, rather than assigning the failure to one of
the registered finite-objective signatures.

## A source-visible globalization defect

The inner solver evaluates a proposed trial at line 598. An unsuccessful
finite trial would ordinarily reach its ratio rejection and increased damping
at lines 617–621. However, `CurveDomainError`, `FloatingPointError` or
`ValueError` from the trial evaluation propagate to the handler around the
whole solve at lines 623–624. That immediately returns `None`, abandoning the
valid current inner state without trying a more damped step.

The direct evaluator explicitly raises `FloatingPointError` when any of its
value or first three derivatives is nonfinite
(`differentiable_likelihood.py:727–728`). The code can therefore turn a
nonfinite trial into total mode failure rather than a rejected trial. This
exception-handling behavior is established from source. The subsequent replay
demonstrates its occurrence in one exact recorded trial; it does not establish
that all 51 trials followed this same inner exit.

## Completed observational extension

The parent replayed the exact first invalid outer trial in
`enriched-collapse-1-trace.jsonl`, with the same frozen target data/runtime and
unchanged `_mode_branch`. This extension was selected after the registered
sweep revealed invalid inner solves; it is not part of the original
preregistration and is not a new search, altered budget or qualification retry.

Independent checks verify the replay hash, exact plan agreement, original
outer-trace hash and first trial vector/iteration, original task-record hash,
and all 113 recorded production-source identities against both frozen Git
`99af520` and the local inspected files. The observer attaches a Python trace
hook to the actual function; it does not replace solver operations. The log
also records successful replay-driver and plan hash checks. Recorded target
input hashes were verified by the runner; this independent review did not
reopen or rehash remote raw banks.

The failed outer vector is
`(-8.76871200089982, 0.9662104363433778, 0.4054651081081644,
0.1909382250865868)` at fixed `h=5.477225575051663`.
At inner iteration zero, damping is zero and the current latent vector is
exactly zero. Its joint objective is finite, `-1087.7954261395473`, with a
positive-definite Newton system. The undamped Newton proposal has maximum
absolute displacement `270.4515070171641`, taking the proposed site log hazard
as high as `261.51092544258927` from a current maximum of `-6.290033670977397`.
The predicted inner gain is `262.7727151967216`.

At `spatial_profile.py:598`, the proposal's `curves.evaluate` raises
`FloatingPointError("differentiable likelihood produced nonfinite output")`.
The next recorded handler location is line 624, returning `None` at the same
iteration and damping. There is no damping retry. The replay consequently
returns the same invalid outer status. Its log records overflow/invalid
warnings from both the log-loss third-derivative algebra and mixture moments.
This establishes a nonfinite trial evaluation followed by premature whole-mode
abandonment in this witness. It does not isolate one arithmetic expression as
the sole cause, establish a different converged latent branch, or demonstrate
the same exit in every other failed evaluation.

The replay output is retained at
`artifacts/sprint2/diagnostics-20261112/operations/inner-replay.json`, SHA-256
`e086168753e4a914c26eb2361ae28e9b41371e10c7b98413eec01b3bc36a399c`.
The bound original outer-trace hash is
`5e38fa2421641f8893b2a7029d8ff58dc39a2a3275763a3f735e8ce5ba15b11d`.

## Repair implication for subsequent review

The replay supports treating an invalid inner trial as a rejected proposal,
retaining the valid current state and increasing damping under a fixed finite
retry policy. Keep the zero start,
strict latent convergence checks, finite-output guard and existing acceptance
requirements. An invalid initial state, exhausted budget or unresolved final
state must still fail. Record the new policy and its resource accounting;
this review does not implement it or authorize a relaxed guard.

Such a deterministic globalization repair keeps the criterion a function of
parameters, data and fixed solver settings, independent of prior outer calls.
It also need not alter the trajectory of any evaluation that previously
completed without a trial exception. By contrast, seeding a call from the
previous accepted outer mode introduces evaluation-history dependence unless
branch selection is separately defined and reconciled. The current evidence
does not justify choosing that continuation policy merely from zero-vector
failure placeholders.

The constant-family stopping/eligibility mismatch and detection-SD derivative
bias retain their separate evidence. They do not resolve this inner-evaluation
hole. A local quadratic gain threshold alone should not conceal it or be
promoted to a rigorous likelihood-ratio error certificate. Any repaired
candidate still requires independent review and a fresh qualification panel;
the rejected panel remains development data, and training and validation stay
closed.

Next: Claude — review the bounded inner-globalization repair alongside the
separate stopping/eligibility and derivative-consistency proposals.
