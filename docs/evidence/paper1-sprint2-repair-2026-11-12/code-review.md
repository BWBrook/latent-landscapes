# Independent review of the bounded A+B+C repair

12 November 2026 · Codex (GPT-6.1 Sol). Reviewed against acceptance commit
`c717758` and Claude's board specification 3307, before repaired-candidate
data outcomes. The reviewer made no production edits, model evaluations,
commits or board posts. This is code and acceptance-apparatus review, not a
claim that replay or fresh qualification has passed.

**The numerical A+B+C implementation is accepted for frozen checks.** Zero
starts, fitted domains, optimization budgets, the envelope guard and the
multimodality audit design are preserved. No gain-only certificate or scalar
arithmetic repair D is introduced. The [arithmetic review](arithmetic-review.md)
supports deferring D within the explicitly retained-converged-mode scope.

## A: invalid inner trials and honest terminal diagnostics

The trial evaluator is protected by the requested narrow exception handler.
An arithmetic/domain failure leaves the current state unchanged and reaches
the same damping increase as an ordinary rejected step. Initial evaluation
failure remains terminal. Exceptions from the trial do not silently create a
finite objective or relaxed convergence result.

The structured branch result preserves successful state and failed-call
counts without the old tuple/None ambiguity. Initial-invalid, damping-limit,
iteration-limit and converged exits are separate; invalid trial counts and
convergence-iteration histograms are retained. On review I requested that the
counter include explicit out-of-domain proposals as well as evaluator
exceptions. That diagnostic-only correction is present, with a bounded-domain
unit test. It does not change the pre-existing rejection or damping path.

The strict score, decrement and positive-definiteness conditions are unchanged.
Iteration accounting includes rejected trials within the original limit.
Converged-only eta extrema exclude rejected proposals and failure sentinels.
An inner `converged` reason does not override subsequent Laplace, domain or
proposal-support checks; those still determine the returned mode's validity.

## B: returned-point eligibility

The production spatial and reduced constant callers now give the trust region
the same gradient threshold that eligibility uses. The returned-point
certificate requires successful evaluation, projected gradient within that
threshold and the unchanged complete finite-difference free-set second-order
check. If the final accepted step moved the point, curvature is recomputed at
the returned point. A retained curvature estimate is reused only at the exact
same point.

Optimizer success now represents this certificate, while the terminal message
still records collapse or iteration exhaustion. A small gradient does not
bypass incomplete curvature or a failing second-order check. No quadratic-gain
threshold is used. The tests cover an inside-threshold passing point, an
inside-threshold failing-curvature point, an outside-threshold point, and
certification after the last allowed optimization step.

## C: nuisance derivative accuracy and boundaries

Both nuisance coordinates use Richardson extrapolation of fixed-eta site
values, scores and curvatures. The existing relative-step convention is
explicitly retained with base `1e-3`; the four constant detection-SD checks
therefore use an actual step of `1e-3`. The latent/Laplace chain rule is
unchanged. Evaluation count and time diagnostics expose the extra cost.

The coarse step selects the stencil orientation once. Both coarse and half
steps use that same central or second-order one-sided construction. This
avoids invalid cancellation from mixing a coarse one-sided stencil with a
fine central stencil near a bound. Central extrapolation is fourth order;
the one-sided boundary remainder is correctly stated as third order. Probe
coordinates remain inside the unchanged fitted domain rather than being
clipped. Tests cover both nuisance coordinates, both boundaries and the
near-bound orientation case.

The retained real constant endpoint references and their `5e-6` tolerance
are prospective acceptance inputs. Their candidate outcomes were not used
in this review and must still be checked on the target.

## Active callers and audit preservation

The importance-reference caller and `fit_dataset.latent_audit` use the new
structured result with the same success/failure decisions and comparisons.
The active audit-start module is a direct extraction of the historical
`starts_for`: all thirteen starts, random seeds, grids and alternative-sigma
construction are unchanged; only branch-result access is updated. The old
evidence script remains unchanged. The current fitter hashes the active
module, avoiding a runtime dependency on the frozen historical CLI.

I compared this extraction line by line with the archived function, and
inspected the new unit coverage and mechanical test updates. No audit
threshold, branch selection policy or start was added or removed.

## Replay and comparison apparatus

The deterministic selection retains 24 tasks across all arm-by-role strata
and all 27 original failures. Preparation preserves original flags, inputs
and runtime, changes source/import identity explicitly, and writes separate
attempt plans. Old attempts are neither overwritten nor promoted.

Non-regression comparisons retain each version's original free normalizers,
compare every spatial variance branch and reduced family, and evaluate exact
frozen baseline anchors. No interpolation or nearest-node substitution is
used. A free candidate at its own h is explicitly distinguished from an
archived fixed-profile maximum. Candidate failure is a non-regression failure,
not a missing successful curve. Data or contract drift fails separately.

Resumed probes restore saved warm-start state in the same anchor order and
reject comparison-identity drift. Review found that numerical checkpoint
payloads initially lacked their own persistent digest. This has been corrected:
canonical payload hashes are stored atomically and verified before state
restoration or numerical use, including error records; a corruption test
fails closed. The digest is an integrity check, not protection against an
adversary rewriting both data and digest.

The point-check runner's numerical logic is consistent with the frozen
endpoint and witness checks. Review requested stronger provenance for
enriched/witness inputs. The correction is confirmed: a required selection
manifest supplies every original task-record digest, checked before model
inputs are opened. All four fixture files must be tracked inside the clean
candidate checkout, their hashes are recorded and rechecked, and tests reject
replacement task records and external unfrozen fixtures. There is no remaining
pre-dispatch review blocker.

## Review boundary

Implementation-agent checks reported the focused solver/fitter/importance and
diagnostic suites passing. The parent reports 176 adjacent tests passing,
followed by eight affected replay-harness and two point-provenance tests after
the final integrity fixes.
This reviewer inspected the critical tests and code rather than rerunning
candidate datasets. The candidate still requires source/runtime/input freeze,
the target endpoint checks, 24 non-regression comparisons and 27 development
replays. Any regression is diagnosed under the frozen tolerances. Corridor's
out-of-scope unresolved case remains a failure under unchanged budgets.

No fresh panel, training or validation is opened by this review.

## Reviewed code fingerprints

The following final bytes were reviewed before target candidate outcomes:

| File | SHA-256 |
| --- | --- |
| `src/latent_landscapes/spatial_profile.py` | `46c3c6544cbc40216976cc841d27e09d4de9ffb854334bdac02f0a281187f010` |
| `src/latent_landscapes/spatial_importance_reference.py` | `5526f4eb5651455500e87860ef3c5c5469f9115f262423c9cd40654cb06fab5e` |
| `scripts/fit_dataset.py` | `6de1d3747176e6f9def289a34933d2d78774a74bde6ace23cd861ad398039da5` |
| `scripts/benchmark_spatial_profile.py` | `7e49fb959d97a1e6854e58d4e4c62d7432d2bff678bf6ac7c6dc6a9be8860594` |
| `scripts/mode_diagnosis.py` | `f2367120be2f1f944c426491e7634c83e821887f5ae3f6bab2433ad2279445ea` |
| `scripts/prepare_solver_repair_replay.py` | `c043f491f95e6a848fd445312f1a760a5a50bac38b38ed981687782c0ad89c73` |
| `scripts/compare_solver_repair_replay.py` | `99d158bf182a8160d92fce23c480dcbc474a59f6c35d5d1ef45a716ae797b3fe` |
| `scripts/check_solver_repair_points.py` | `5dd2d2e7fad3228136daa77322729761f2309d917fb8054aee3b782729067a94` |
