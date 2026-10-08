# Arc 4 design brief: detecting misleading estimates

20 September 2026. **Detector/null-check tranche approved by Barry in Codex on
20 September; subsequent alternative-model campaigns remain proposals.**
This develops Fable's Correspondence messages 378–379 and Astra's reply 389.
An independent mathematical check supports the repaired marginal construction.
Goal 049 remains closed, with its original calibration table, null flag and
all earlier numerical failures preserved.

## Recommended next tranche

Qualify one model-inadequacy detector and run the bounded crossed null-block
check before launching alternative generators. Deliver a frozen detector,
its realised baseline error rates, the four null-check counts with uncertainty,
a costed robustness-screen design, and an explicit decision to proceed or stop.
This is preparation for Charter Pillar 4, not completion of model discrimination.

Proposed ceiling: 12 elapsed computation hours on deep-server, eight workers,
32 GiB; one measured timing trial precedes production. Reuse the primary
K131072/alpha1 bank and the full 181-node effect grid. No larger bank, landscape
expansion, unknown-nuisance lane, or automatic resource escalation. If the
measured complete workload cannot fit, return the costed limitation before
production. This is a new proposed envelope, not unused Goal 049 permission.

## Detector and finite-grid validity

Fit h on the original 120 training sites with the frozen scoring rule and a
fixed tie rule. The primary discrepancy is the held-out conditional prey log
score, summed over the original 40 held-out sites, at that fitted h. Low scores
are adverse. Spatial independence between training and holdout is not assumed:
reference histories must reproduce the complete joint generator and identical
splitting, fitting and scoring operations.

There is an important source-level correction to Fable's proposal:
`known_nuisance_calibration.score_observations` saves the **joint** held-out
predator/prey score and discards the predator-only component returned by
`arc2c_likelihood.evaluate_dataset`. Conditional prey score requires subtracting
that component. It is not a lookup in the currently saved array alone.
Calibration holdout scores were not retained at all. Replay the deterministic
calibration histories and recover both components; also recover the component
for the existing evaluation histories. Keep original artifacts unchanged.
Verify replayed training LR curves/fit choices against their frozen identities.
Reusing saved fitted nodes after this check implements the same fitting rule;
it does not require repeating an optimizer merely for form's sake.

For each fixed candidate g, refit every one of its 999 reference histories on
training sites and compute its held-out statistic S_gb using its own fit.
For observed S, use the lower-tail conservative Monte Carlo rank

`p_g = (1 + count{b: S_gb <= S}) / 1000`.

With complete histories exchangeable at the fixed true node, this is a
super-uniform Monte Carlo p-value, including ties, marginal over reference
histories and the evaluation history. A plug-in p at the selected node has
no such general guarantee.

Use gamma=0.01 and derive a **separate 99% candidate set**, C99, from the
990th of the 999 saved calibration LR values at each node. Goal 049's rank950
95% set remains the reported effect set and cannot be used with a 0.01 penalty.
Compute

`p_BB = min(1, max_{g in C99} p_g + 0.01)`.

This follows the confidence-set maximization approach of
[Berger and Boos (1994)](https://asu.elsevierpure.com/en/publications/p-values-maximized-over-a-confidence-set-for-the-nuisance-paramet/).
For this proposed finite-grid implementation the validity argument is explicit:
for true node h and alpha >= gamma,

`P_h(p_BB <= alpha) <= P_h(h not in C99) + P_h(p_h <= alpha-gamma) <= alpha`.

No independence between C99 and p_h is required, so the same calibration
histories can supply both. The guarantee is marginal over random reference
tables and histories, conditional on a fixed independent integration bank;
it is not uniformity, exact 5% size, or control conditional on the realised table.
Ties may make it conservative. C99 always contains a grid maximizer under the
present nonnegative LR rule; an empty set is an implementation failure.

Every member of C99 on the original grid must be represented. Restriction to
an arbitrary node subset or a neighbourhood of the estimated truth does not
preserve the guarantee. No interpolation or nearest-node substitution is used.
No off-grid or unknown-nuisance validity is asserted.

A training-site predator-only discrepancy is a useful secondary diagnostic,
but h does not enter it in the known-speed model. It must not be described as
an additional effect fit. Initially report it separately, with no combined
rejection claim. If a two-statistic omnibus rule is wanted, register and
calibrate that combined rule before examining outcomes. The primary
inadequacy decision uses only p_BB <= 0.05 from the held-out prey statistic.

## Qualification evidence and null-block check

Use the 6,000 archived assumed-model evaluation histories for a labelled
**retrospective baseline check**, after reconstructing the required score
components. Their aggregate outcomes have already informed this design;
they are not fresh prospective validation. Report empirical rejection rates,
C99 inclusion and Monte Carlo uncertainty at all six truths. The marginal
validity proof does not force every realised rate to equal 5%.

Add exactly one independent 999-history null calibration block and one
independent 1,000-history null evaluation block. Freeze roots and all reporting
before generating either. At rank950, cross original/new null cutoffs with
original/new evaluation blocks; report all four counts and both cutoffs,
conditional and calibration-aware uncertainty, and their shared-block
structure. The primary effect table is never replaced. The new evaluation
block can also provide fresh null validation of the primary detector using
its frozen original-reference table.

This experiment can support a calibration-block or evaluation-block explanation;
it cannot uniquely prove absence of a phase bug. Fable's greater-than-three-SE
power assertion is not established. Under the continuous-score marginal null,
a 1,000-history count with a rank950/999 random cutoff has beta-binomial SD
9.742, rather than binomial SD 6.892. A 24-count shift is about 2.46 of these
single-cell SDs; that calculation is not itself the power of the dependent
four-cell comparison. No large-power claim or extra replication follows.
Report the registered output whatever its direction. Broken provenance or
scoring identities stop execution; surprising scientific counts do not
trigger redraws or tuning.

The replay cost is not established as six hours. Only the primary variant is
needed, while conditional-score recovery adds work relative to simple array
reuse. Time the actual complete operation, including score recovery, replay
checks, both fresh blocks and synthesis; retain a conservative budget reserve.

## The subsequent robustness screen and discrimination

Fable's four proposed classes form a useful shortlist. The ecological choice
and severity definitions remain for Barry's scientific judgement. My priority
for the first screen is heterogeneous detection and spatial background
confounding: they test whether observation error or non-predator losses can
produce apparently persuasive effects. Recolonisation and decaying impact
remain valuable process extensions, rather than automatically approved work.

| Candidate departure | Shared target or comparison | Definition still needed before registration |
| --- | --- | --- |
| Site-heterogeneous detection | Generating hazard multiplier h remains the target | Which species vary; distribution, spread and spatial pattern; fitted p remains 0.65 |
| Correlated background loss | h=1 is the physical null; report false-effect frequency and fitted h | Field variance, correlation length, and independence or alignment with invasion; fixed mean hazard 0.002 |
| Recolonisation after loss | Shared first-loss hazard multiplier h | Recolonisation timing/rate and state transitions; bias direction is a prediction, not guaranteed |
| Decaying post-arrival impact | Initial multiplier h0 plus a precisely defined window summary | Decay timescale and exposure weights; a constant-model estimate need not target that window summary |

An exposure-weighted average depending on each realised arrival history is a
random latent target, not automatically the pseudo-true constant parameter.
If it is reported, define the weights, distinguish conditional and population
summaries, and do not call off-grid membership in the finite candidate set
coverage of that quantity. Nesting does not settle this estimand issue.

Stage 1 generates approved departures and evaluates the frozen original model,
its effect set and detector, against a matched-generator baseline under the same
table. Report hidden failure (misleading estimates without detection) as a
scientific result, not as a trigger for tuning the detector. Specify severities,
truths, replication and meaningful effect thresholds before running.

Stage 2 fits competing models and a neutral comparator, with equivalent
information and held-out predictive evaluation. Choose the escalation rule
before Stage 1; use separate histories to confirm selection/discrimination
claims for cases selected by Stage 1. A screen alone does not meet the roadmap's
model-discrimination exit gate. New likelihoods, nuisance handling, fit checks
and any simulation-calibrated comparisons must be costed separately. No
chi-square calibration follows automatically from nested alternatives.

## Decision and stopping point

Recommendation to Barry: authorize the bounded detector/null-check tranche
above, then decide the first alternative classes from its report and a costed
screen design. If preferred, select the ecological priorities now; their
implementation still follows an explicit estimand and severity registration.
The detector/null tranche would end after one verified synthesis, including
unfavourable results, without an automatic Stage 1 or Stage 2 launch.

No new simulation, replay campaign, source implementation, scheduler, commit
or push has been performed in preparing this brief.
