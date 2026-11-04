# Independent review of the completed development challenge

5 November 2026. Reviewer: independent Codex subagent, separate from the
execution and final-report author. Scope: receipt reconciliation, numerical
decision audit and descriptive-summary checks. No new fits, altered gates or
scientific-method changes were made.

**Decision:** accept closure of the finite development panel with its recorded
failures and indeterminate results. Do not qualify the approximate profile
procedure, begin calibration on the strength of this panel, or claim calibrated
ecological inference. The two fixed-outer integration failures already deny
readiness; the prescribed second stage of importance-profile reoptimisation is
therefore not warranted by this result. Its root movement remains unquantified.

## Evidence and provenance checks

The reviewed receipt root is
`artifacts/paper1_development_challenge_20261101/completed-review/`.
It contains the completed execution copy, including `profiles/`,
`bank-comparisons/`, `importance/`, `jobs-summary.json`, the frozen and prepared
manifests, and `summary-final/summary.json`. Remote paths embedded in receipts
remain the original execution identities; relocation did not rewrite them.

The frozen panel manifest SHA256 is
`f5a80802dc502305f186f7f0a599d20e674d26d7b3e1c917403969b01f2cecfa`;
the summary-job manifest SHA256 is
`33d86c952a04dce9a9f71045b4b996284c9bd21468970d188237b9a2a9e8ba27`;
the reviewed final summary SHA256 is
`9d5abf2925dca4b0ab91f82ca0db6ab2c98505aae73e4c03e7c6746c1479aa99`.
All three were recomputed from the local bytes and reconciled with the
reported identities. The prepared archived manifest also matches its recorded
hash, as do the C-bank manifest references in the job descriptions.

The frozen case list contains 32 archived A/B datasets and six separate C
datasets. The job list has exactly 38 B0 roles and 22 independent-A roles.
All 60 parent profile receipts and 98 dense/lean child receipts were read.
Every child's hash matches its parent; parent and dense hashes and statuses
match the final summary. Each parent's five runtime input bindings and site
count match the job description. The additional C-bank manifest references
are checked against their own bytes; those manifests are not direct runtime
inputs bound by the profile parent.

All 22 bank-comparison receipts bind both banks' parent and dense receipts.
All 36 integration receipts bind their B0 parent and dense receipts. Their
hashes match the final summary. Across the 118 parent/comparison/screen
receipts, all recorded hashes for the 113 distinct scripts and source files
available in the current checkout match the local bytes. This review did not
rehash every large raw input array or rerun its generation; bulk archive
verification is a separate finalisation operation.

## Numerical outcomes

| Unit | Completed outcome |
| --- | --- |
| 38 B0 dense/lean runs | 24 within gates, 12 failed comparison, 2 indeterminate |
| 22 independent-A dense-only runs | 22 numerically resolved |
| 22 B0/A comparisons | 16 within gates, 6 failed |
| 36 available fixed-outer screens | 13 pointwise passes, 2 repair required, 21 indeterminate at the draw cap |
| Other two datasets | Screen unavailable because both dense and lean searches are unresolved |

The two unresolved datasets are `cell-00-rep-005-arm-B` and
`cell-06-rep-006-arm-B`. Both searches retain the error “unresolved candidate
exceeds selected family envelope”. Their absent integration screens are
accounted for, not silently omitted. Thus the summary's 23 indeterminate
integration entries comprise 21 completed screens and two unavailable screens.

Among all 36 available dense/lean comparisons, the maximum absolute same-h W
difference is `9.163159120362252e-10`, and the maximum absolute log-root
movement is `2.470981647739734e-6`. All level-set checks pass and all compared
owners agree. The 12 failed comparisons fail nuisance-bound-contact agreement;
one also has unequal aggregated contacts inside the diagnostic set. Their
failure status remains binding under the frozen rule despite the close W and
root agreement. This is evidence to investigate contact classification or
near-boundary optimisation in later development, not authority to relax the
gate retrospectively.

All 22 independent-bank comparisons satisfy the numeric W and root thresholds,
component/domain checks and compared-owner agreement. The largest absolute W
difference is `0.023350347657469683`, and the largest absolute log-root movement
is `0.0005074643565898818`. The six failures have nuisance-contact mismatches
at points inside the diagnostic set. They remain failures, distinct from
large arrival-bank changes in the profile or roots.

The final importance decision was reconstructed independently from the two
streams, previous draw level, contrast intervals and ownership-reversal
flags for every available screen. Weight gates were separately reconstructed
from ESS, relative ESS, maximum weight, pooled Pareto shape and availability
of batch tail fits for all 382 final point-stream envelopes. All decisions and
weight gates agree with the receipts. All 21 completed indeterminate screens
reached 262144 draws per point per stream. Their reasons overlap: 20 fail
contrast precision, four fail weight gates, two fail draw-doubling stability,
and three fail cross-stream agreement. One otherwise qualified screen,
`cell-08-rep-006-arm-B`, straddles the correction threshold at its upper root:
the two intervals are approximately `[0.0968225, 0.1153205]` and
`[0.0998057, 0.1167508]`. It cannot be promoted to a pass or repair decision.

Both repair-required cases are the A/B arms of `cell-01-rep-006`, each decided
at 32768 draws with stable doubling and both streams passing weight and
contrast-precision gates. Both show material positive-to-zero variance-family
ownership reversals beyond the `1e-4` tie tolerance. Arm A additionally has a
centred fixed-outer correction at `h=5.57219546397124` whose conservative
decision interval is `[0.10710401210189957, 0.10710401210189957]` in both streams,
entirely above `0.10`. The interval collapses because the exact-zero branch
dominates both envelope endpoints. Arm B's maximum absolute correction is
`0.04502159767616831`; its repair decision is driven by ownership reversal.
These are fixed-outer results, not reoptimised marginal profiles or estimates
of movement in optimised roots.

## A/B descriptives and interpretation

The dense-derived free-fit, level-set and ridge summaries were reproduced
directly from the bound dense receipts and match the final summary. All eight
available individual ridge slopes were also calculated independently by exact
Simpson integration of the product of centred log-h and each linear log-sigma
segment; they agree within `1e-10`. Every available paired root expansion and
slope difference reproduces from its constituent values.

Only five of the sixteen histories have two actual roots in each arm. The
prespecified `dU > dL` prediction holds in two and fails in three. Eight pairs
are truncated in both arms, two combine a truncated A set with an unresolved
B set, and one combines a truncated A set with an available B set. Only three
pairs have both ridge slopes available; all three have negative B-minus-A
slopes, contrary to the directional prediction. The other thirteen remain
categorical. No missing roots, truncated endpoints or tied/zero-family slopes
were imputed. These selected development histories do not establish a general
depletion effect, its absence, or a calibrated uncertainty statement. The C
stratum remains separate from the A/B comparison.

## Limits and next decision

This audit accepts the accounting and the bounded negative/indeterminate
numerical conclusion. It does not certify global optimisation, all possible
latent modes, unobserved narrow profile features, the validity of nominal
Monte Carlo intervals beyond the stated estimator assumptions, or coverage of
ecological confidence sets. It does not reopen the frozen panel, inspect
holdouts, reanalyse real data, or authorise publication. Final figures and
archive/resource operations belong to the report author's separate checks.

The next scientific tranche should diagnose the contact failures and the
observed integration ownership reversals under a separately reviewed
development protocol. Preserve this panel and its failed gates as historical
evidence; any changed procedure requires fresh qualification before rule
training or untouched validation.
