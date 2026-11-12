# Independent review: partial Sprint 2 qualification failure lower bound

Review date: 12 November 2026. Reviewer: independent Codex (GPT-6.1 Sol) subagent.
Scope: frozen synthetic-only qualification, source
`99af5206b6a4e53f5b8e9d71cbf348f95e9ae574`. Training and validation remain
closed. No fits, simulations, remote calls, tracked edits or board posts were
made. This advances the Sprint 2 numerical-qualification decision under charter
pillars 3, 4 and 6.

## Decision and evidence status

The recorded terminal scientific failures already make both full A/B/C
qualification and the registered A/B continuation impossible. The proof uses
a lower bound on the mean failure fraction, not a monotonicity assumption about
the full empirical acceptance score. Even universal success for all remaining
execution and audit work cannot change that decision. The terminal failures
have now been independently verified at fit-receipt level under their frozen
identities.

**Receipt-level review complete:** all 27 failed fit receipts match their root
recorded SHA-256 and scientific failure class; all 162 files in those attempts'
recorded output inventories independently hash-verify (46,110,928 bytes total).
Each receipt has the required schema, clean frozen source, correct search mode,
registered observation hash, unchanged eight cutoffs and always-on tight replay.
Every `all_triggered` list is exactly its terminal class: 25 contain only
`family_fit_failed`; two contain only `search_unresolved`. Every fit input hash
entry agrees with the frozen task or the corresponding frozen Git object:
162 data/input bindings plus 3,105 source bindings across 115 unique source
files, with no mismatch. These are binding checks against the frozen task and
Git objects, not a fresh rehash of remote raw-bank inputs. All ten forced base
failures have a verified required dense fit failure. This is a conclusive
rejection lower bound for the frozen numerical gate, while the run and full
qualification packet remain incomplete. It is not a completed qualification
report and makes no central biological inference.

## Frozen evidence and checks

The qualification panel has 207 registered arm datasets: 162 base (18 on each
of nine maps), 18 boundary, 18 enriched and nine trend. The fit plan binds 486
required fit tasks: 207 dense, 207 lean, 54 independent-bank lean and 18
exhaustive lean. All tasks name the same frozen commit. The current reducer
is byte-identical to its `99af520` version.

The observed snapshot reports 417 resolved tasks, 27 terminal scientific
failures (25 `family_fit_failed`, two `search_unresolved`) and 42 without a
final record. Resolved fits are not qualified datasets: comparisons, gradient
and other registered evidence remain necessary. Absence of a local record is
not evidence of remote absence. The 42 tasks remain incomplete, with no
replacement by successes or scientific failures.

All 27 mirrored root `_task.json` records agree with the snapshot, embed the
exact frozen task object and its canonical SHA-256, record clean frozen source
identity, have exit code zero, and bind a fit-receipt SHA-256. Scientific
failures are terminal under `scripts/pbs/campaign.py`; only execution losses
may retry with unchanged identity.

Evidence hashes:

- `operations/qualification-progress-20261112.json`:
  `6a7391b259acd8b7026507fa1c75cfc0366e66a538db37effcc781e9edb3efb6`
- `operations/fit-plan/tasks.jsonl`:
  `09a42f38f1d579119afdd3b7b53bec0a968e269fc16fc48e426310e66e86a042`
- `docs/evidence/paper1-sprint1-2026-11-05/qualification-panel.json`:
  `51006aa0355ab4ce9f28e572a4272f09c0dc9fcdb52ae6ed0570aacbb1cf240d`
- `scripts/summarise_sprint2_qualification.py`, both current and frozen:
  `4f138512341825dbe348a227a4a9ac769707e38eb091e17ea14557f536563439`

Operations and phase-result paths in this note are relative to
`artifacts/sprint2/pilot-20261107/`.

## Deduplicated case lower bounds

The 27 failed tasks represent **14 unique arm datasets**, not 27 failed
qualification cases. Fourteen are dense-role failures, ten lean, two
independent-bank and one exhaustive. Every one of the 14 unique cases has a
dense failure, so the conclusion does not rely on treating an optional role
as required.

| Stratum | A | B | C | Forced failed cases / registered cases |
| --- | ---: | ---: | ---: | ---: |
| Base | 3 | 4 | 3 | 10 / 162 |
| Boundary | 0 | 0 | 0 | 0 / 18 |
| Enriched | 0 | 2 | 0 | 2 / 18 |
| Trend | 2 | 0 | 0 | 2 / 9 |
| All | 5 | 6 | 3 | 14 / 207 |

Zero in this table means no presently recorded terminal scientific failure;
it does not mean the stratum or arm has passed.

| Base map | A | B | C | Forced failures / 18 |
| --- | ---: | ---: | ---: | ---: |
| barrier-0 | 0 | 0 | 0 | 0 / 18 |
| barrier-1 | 0 | 0 | 0 | 0 / 18 |
| barrier-2 | 0 | 0 | 0 | 0 / 18 |
| connected-0 | 0 | 0 | 0 | 0 / 18 |
| connected-1 | 0 | 0 | 0 | 0 / 18 |
| connected-2 | 2 | 1 | 1 | 4 / 18 |
| corridor-0 | 0 | 0 | 1 | 1 / 18 |
| corridor-1 | 1 | 2 | 0 | 3 / 18 |
| corridor-2 | 0 | 1 | 1 | 2 / 18 |

Unique forced failures and the recorded failing required roles:

| Registered dataset ID | Failed roles | Terminal class |
| --- | --- | --- |
| q-enriched-connected-1-increased_heterogeneity-mu0.001-h1-B | dense, lean | family_fit_failed |
| q-base-connected-2-window_low-mu0.001-h10-A | dense, lean | family_fit_failed |
| q-base-connected-2-window_low-mu0.001-h10-B | dense | family_fit_failed |
| q-base-connected-2-window_low-mu0.001-h10-C | dense, lean | family_fit_failed |
| q-base-connected-2-window_high-mu0.004-h1-A | dense, lean | family_fit_failed |
| q-trend-connected-2-temporal_trend-mu0.004-h3-A | dense, lean | family_fit_failed |
| q-base-corridor-0-increased_heterogeneity-mu0.001-h1-C | dense, lean, independent_bank, exhaustive | family_fit_failed |
| q-base-corridor-1-window_low-mu0.001-h1-B | dense, lean | search_unresolved |
| q-base-corridor-1-window_high-mu0.001-h3-B | dense, lean | family_fit_failed |
| q-base-corridor-1-b100_anchor-mu0.004-h3-A | dense, lean, independent_bank | family_fit_failed |
| q-enriched-corridor-1-window_high-mu0.001-h1-B | dense | family_fit_failed |
| q-base-corridor-2-window_high-mu0.001-h1-B | dense | family_fit_failed |
| q-base-corridor-2-b100_anchor-mu0.004-h1-C | dense | family_fit_failed |
| q-trend-barrier-1-temporal_trend-mu0.004-h3-A | dense, lean | family_fit_failed |

## Exact reducer interpretation and proof

In `assess_case`, each required fit with `family_fit_failed` or
`search_unresolved` contributes a failed check. Any such fit makes the case
nonpassing and skips its dependent numerical audits as not applicable; it does
not turn the scientific failure into missing execution. Missing other required
fits can still make the case incomplete. `case_result` separates `passed` from
`complete`. `summarise` reports `incomplete` before `repair_required` while
required evidence is missing, and never authorises training. The present note
therefore establishes rejection inevitability without claiming full packet
completion or substituting a fabricated successful remainder into the report.

For each base map m let f_m be its final failed-case count and l_m the count in
the map table. Terminal scientific failures imply f_m >= l_m. With nine equal
18-case denominators,

`mean(p_m) = sum(f_m)/162 >= sum(l_m)/162 = 10/162 = 0.06172839506`.

The frozen score is
`S = mean(p_m) + t(.95,8) * sample_SD(p_m)/3`, where
`t(.95,8) = 1.85954803753` and SD is nonnegative. Therefore

`S >= mean(p_m) >= 0.06172839506 > 0.05`.

Full A/B/C qualification is impossible regardless of additional failures or
successes. This remains valid even if later failures reduce between-map SD.
No coordinatewise monotonicity of S is assumed. The existing maximum map
fraction lower bound is 4/18 = 0.2222222, so the max <= 0.25 criterion alone
has not yet forced rejection.

For transparency, calling the actual frozen `finite_panel_gate` after marking
only these 14 cases failed and every other case passed yields A/B/C score
0.11464254877 and max 0.22222222222. This is an illustrative completion,
**not a rigorous lower bound on the full score**. The mean-only argument above
is the decisive bound.

## Registered A/B continuation

The continuation requires all base failures to be in C, complete base evidence,
and a passing gate with 12 A/B cases per map. Seven known base failures are
already in A/B (three A, four B), so the C-only requirement cannot hold.
Moreover, even ignoring that eligibility violation, its own score obeys

`S_AB >= mean(p_m_AB) >= 7/108 = 0.06481481481 > 0.05`.

Thus the A/B continuation fails independently on two grounds. The illustrative
all-other-checks-pass A/B score is 0.13205340027 with max 0.25; again this score
is not being used as a lower bound.

Two enriched B and two trend A failures are outside the base denominator and
independently require diagnosis before training. They cannot be dropped, pooled
into base, or waived because some base criterion passes. No retrospective
removal of C, strata, fitted families, replay, cutoffs or audit roles is
accepted.

## Recommendation and limits

The failed-receipt validation is complete. Finish the bounded execution
diagnosis and review the need for any further resource use before considering
retries. Resource-only retries of the 42 incomplete
tasks can complete provenance, characterize the procedure and reveal additional
failures; they cannot rescue this frozen qualification panel because its
terminal scientific failures are verified. Retry only established execution losses, preserving the
same task/source/input identities and all attempts. Never retry or relabel
scientific failures as execution losses merely to obtain passing evidence.

Preserve stale running jobs and partial outputs until the parent has reconciled
scheduler state and made a bounded operational decision; this note does not
authorise cancellation, discard attempts, or infer a scheduler cause.

The highest-value next work is diagnosis of the existing failures plus the
stalled execution, followed by independent review of any proposed repair. A
substantive repair after outcomes uses the registered one-repair/new-panel
branch and records the deviation; it does not revise the observed panel into a
new pre-outcome design. No method, estimand, threshold, training or validation
change is accepted here. A full qualification packet would still require
reconciliation, the remaining registered numerical evidence and descriptive
integration screens. These are finite-panel numerical conclusions, not a
population failure probability or a statement about the biological scientific
hypothesis.

Next: Codex — complete execution diagnosis and independent scientific review before any retry decision.
