# Proposed prospective comparison of spatial background adjustment

24 September 2026. **Proposal for critique; no new campaign authorized.**
Charter Pillar 4 / Roadmap Arc 4. Computational choices are delegated to Astra;
the decision here concerns fresh scientific evidence and its interpretation.

## Recommendation

Run one fresh, six-cell comparison on the current survey. It should determine
whether estimating spatial background improves predator-effect estimates and
prediction, and distinguish a cost of nuisance estimation from remaining
generator misspecification. Use 1,000 paired blocks rather than another small
development panel. Retain the constant, adjusted and adjusted no-effect fits.
Make effect-estimation error and the **direct** adjusted-minus-constant
held-out comparison the main outcomes. Additional surveys, unknown mean
background hazard and broader ecological mechanisms remain deferred.

Goal 052 makes this scientifically useful but does not predetermine the result.
Adjustment reduced aligned-null error but worsened aligned-threefold error on
the multiplicative scale and showed no consistent predictive gain. Exact
nonzero-beta controls were absent. A repetition of the original hidden-failure
nomination would not resolve those alternatives.

## Generators and information supplied

| Generator | h values | Purpose |
| --- | --- | --- |
| Exact constant background, beta=0 | 1, 3 | Measure flexibility cost when adjustment is unnecessary. |
| Exact A-adjusted background, beta=+0.60 | 1, 3 | Test recovery under the fitted nonzero-beta model. |
| Original B100-A background with residual G | 1, 3 | Test usefulness when the adjustment remains incomplete. |

This is **six cells × 1,000 paired blocks = 6,000 fresh histories**. Beta=0.60
is fixed by design near the generator's nominal A coefficient
`0.70*sqrt(log(2)) = 0.583`, rounded to the existing grid. It is not an estimate
from Goal 052 and is not asserted to be the true fitted beta under B100-A.
The exact adjusted cells contain no G and use exactly the analyst's
whole-map-normalized hazard. A negative-beta production arm would add little
to this particular discrimination; numerical controls already cover both signs.

Keep the landscape, 120/40 site split, six survey times, two visits, known
mu=0.002, known detection and spread, and the fixed independent K131072 alpha1
bank. Preserve the h=1..10 and beta=−2..2 grids at 0.05 spacing, including the
nested 0.10 check and all boundary flags. This evaluates a declared constrained
procedure; it does not silently resolve the pilot's +2 truncation. Use new,
disjoint process/observation/field streams, paired across the six cells; freeze
all seeds and scientific rules before revealing the production outcomes.
Holdout observations must not affect fitting or numerical search choices.

For the four exact-model cells, also report h fits with beta fixed to its
generating value (0 or +0.60). This uses a saved grid row and little extra
computation. It is an explicitly evaluator-assisted diagnostic, not another
analyst method offered extra information without acknowledgement. It separates
the cost of estimating beta from difficulty estimating h even when background
is known.

Fit the actual latent-arrival procedure on all 6,000 histories. Restrict full
oracle-arrival geometry to the first 250 registered blocks in the four exact
cells (1,000 histories), with the same known-beta diagnostic. This addresses
the outstanding cause of weak separation without repeating full oracle
surfaces over every misspecified history. Oracle results cannot substitute for
the actual procedure. The subset is fixed by stream index, never by outcome.

## Outcomes, precision and reporting

Freeze the following outcome vector for every cell before simulation:

1. Paired change in mean absolute log-h error,
   `abs(log(h_adjusted/h_true)) − abs(log(h_constant/h_true))`.
   Negative is better. Also retain signed log error, all fitted values and the
   proportion exceeding the established 1.5-fold point-error threshold.
2. Paired held-out conditional-prey score of the fitted adjusted model minus
   the fitted constant model, divided by 40 sites. Positive is better. Report
   the adjusted-versus-adjusted-null advantage separately: it answers whether
   h contributes within the adjusted model and cannot replace direct comparison.
3. Exact-model free-beta versus known-beta error and likelihood geometry;
   finite-box contacts and coarse/fine movements in every cell. Report beta
   error only where a generating beta exists.

The aligned-null error contrast addresses the original vulnerability. The
aligned-threefold and beta=0 cells are required checks on correction of a real
effect and the cost of extra flexibility. Report all six cells; do not select
the most favourable error scale, average them into a repair claim, or treat
one favourable contrast as universal model improvement. These are estimation
and prediction outcomes, not calibrated per-history effect declarations.

Use analytic paired Monte Carlo SEs and a fixed 2,000-draw bootstrap of whole
block indices, shared across all six cells, for summary uncertainty. The
reporting targets are MCSE ≤0.02 for paired mean absolute-log-error change and
≤0.002 nats per held-out site for the direct score change. They justify the
fixed sample size; they are not success gates or permission to redraw. Report
achieved SEs and unresolved precision if either is missed.

The largest direct score-difference SD in the six-block pilot was 2.090 nats
over 40 sites. Its projected MCSE is 0.00165 per site at 1,000 blocks, versus
0.00331 at 250. The largest pilot projected MCSE for the error contrast is
0.0108 at 1,000 blocks. Those are uncertain planning estimates from a small
retrospective panel, especially for the new exact-beta cells. Worst-case
binomial MCSE at 1,000 is 1.58 percentage points. No formal power or equivalence
claim is made from this calculation.

Before execution, register these expectations as predictions, not acceptance
conditions: adjustment will reduce aligned-null absolute log error on average;
estimating beta will cost precision relative to known-beta fits in the exact
nonzero-beta cells; and any estimation benefit need not produce a positive
direct held-out score contrast. The direction of the aligned-threefold error
contrast remains an open question. Retain failed predictions.

## Calibration route and its boundary

This proposed comparison deliberately reports point-estimation performance,
predictive scores and raw geometry. It does not attach 95% confidence labels
to h profiles or reuse Goal 049/050 cutoffs. The across-history bootstrap above
quantifies simulation-summary uncertainty, not parameter uncertainty within
one history. It also does not confirm the original H nomination, whose
effect-set construction and detector remain a different fixed procedure.

If later inference requires a calibrated declaration of h>1, a defensible
finite-grid route is to simulate the **entire fitted statistic**
`T = 2*(max_h,beta logL − max_beta logL_at_h1)` under each null beta node.
For each node compute the plus-one Monte Carlo tail probability, then take
the maximum across null beta nodes. For a grid-valued true beta that maximum
is at least its exchangeable candidate-specific p-value. This gives a
conservative assumed-model test conditional on the fixed analysis bank;
it gives no guarantee for beta between nodes or for omitted G. Null-reference
histories must be independent of the evaluation histories, with realised size
and power measured rather than inferred from nominal levels.

Illustratively, 249 null histories at each of 81 beta nodes require **20,169
full fitted histories**, about **296 million candidate score evaluations**.
Its tail precision is coarse and a supremum can be conservative. A future
registration should compare this simple route with a justified nuisance-set
or sequential allocation strategy before paying for it. Such changes need
their own mathematical checks; a fitted-node bootstrap is not silently
substituted as a guaranteed test.

Naive full profile-confidence calibration at all 181×81 candidate truths with
249 histories each would require **3,650,589 full fitted histories**, about
**53.5 billion candidate score evaluations**. That is not the recommended next
experiment. Calibration is deferred until the prospective error/prediction
comparison establishes whether this adjustment merits an inferential procedure.

## Compute estimate and execution route

Goal 052 completed its 24-history full latent/oracle panel in **741 s**, with
**2.25 GiB peak resident memory** on eight workers. The unchanged legacy
integration accounted for 258 s. The slowest complete beta row took 48.34 s.
These are measured costs; a 6,000-history workload has not yet been timed.

A deliberately pessimistic sizing calculation assigns that complete row cost,
including shared construction and oracle work, proportionally to every group
of 24 histories:

`1.5 * (48.34/24) * 81 * N / 8` seconds.

It gives **about 51 elapsed hours at eight workers** for N=6,000, before small
additional generation, controls and synthesis allowances. The actual design
shares beta-row integrations across many histories and limits oracle work, so
this may substantially overestimate scoring cost. It is a planning surrogate,
not a qualified bound. The illustrative null calibration above scales to
about 171 hours at eight workers by the same surrogate; full-box confidence
calibration scales to about 31,019 hours and is excluded.

Use deep-server first, where the bank already resides. Once the scientific
scope is approved, qualify complete workloads and choose parallelism, batching
and any Nectar/Kunanyi distribution from measured throughput and capacity.
Reusable integration moments and immutable scored blocks should avoid repeated
bank construction. Source or execution changes require proportionate numerical
qualification; higher concurrency is not assumed to scale linearly. Resource
and time decisions belong to Astra and require no additional Barry approval.

## Decision and stopping point

Recommend approval of this fresh six-cell estimation/prediction comparison
after Fable's critique, including the exact-background and known-beta controls,
fixed precision targets, and limited oracle subset. The meaningful endpoint
is a verified comparison of benefit, flexibility cost and residual
misspecification, with independent review and a recommendation on whether to
develop calibration or change the observation design. Mixed or negative
results are valid completion.

This proposal does not authorize itself. No new generator campaign, calibration,
survey augmentation, unknown nuisance, additional landscape, commit, push or
publication has begun. Fable's next role is scientific critique; Barry's next
decision concerns the resulting scope, not compute resources.
