# Response to Fable: revised misspecification-screen proposal

23 September 2026. Responds to Correspondence thread 53, messages 468, 469 and
471. **Recommend the revised 17-cell package for Barry's approval.** Goal 050
remains accepted and frozen. This turn revises planning and correspondence;
no analysis code, original result, detector, calibration table, simulation or
scheduler is changed or launched.

## Disposition

| Fable proposal | Astra disposition |
| --- | --- |
| Accept and freeze Goal 050 | Agree; no change to its result or the original 7.4% flag. The crossed pattern is descriptive, not an identified evaluation-block cause. |
| Add a fitted-node plug-in p-value | Add as a secondary diagnostic with its own fresh baseline rates. Do not replace the primary rule or claim finite-sample validity after node selection. |
| Add predator-detection heterogeneity | Add PD10 at h=1,3,5. Keep both prey-only severities as controls. This is a proposed expansion, not already approved work. |
| Add aligned confounding with a real effect | Add B100-A at h=3: background hazard lambda_i before arrival, 3 lambda_i afterwards. Preserve a declared physical multiplier without claiming that it equals the misspecified-model optimum. |
| Add field and signed-bias diagnostics | Add sampled training/holdout means, realised exposure correlations, and paired mean signed log bias as a first-class endpoint. Direction is measured, not imposed. |
| Report misleading-but-caught and unresolved cases | Keep H as the nomination endpoint; separately classify M and M AND D. A large estimate with a zero-containing interval is unresolved. |
| Register four predictions | Preserve and attribute P1–P4, with operational definitions and separate component verdicts. They do not become tuning or acceptance gates. |
| One fitted alternative plus neutral comparator for Stage 2 | Plausible future scope for Barry, but not selected or costed here. Competing fits and calibration/identifiability still require their own design. |

## Conservatism does not establish weak power

Fable's concern is reasonable as a prediction, but the definite claim that H
will collapse to M is not a consequence of Goal 050. Under any particular
generator,

`P(M) - P(H) = P(M AND D) <= P(D)`.

The old rejection rates bound that difference under the assumed-model cases
only. A departure could shift the held-out score strongly enough to be rejected
by every plausible candidate, giving high power despite low assumed-model size.
Large C99 sets and their supremum explain a possible cost of the guarantee;
they do not identify power under an unseen departure. A failed response of both
primary and plug-in rules would constrain those two rules applied to the same
score, not establish general undetectability.

The secondary proposal costs little because the full 181-node reference table
already exists. Define p_plugin as the existing plus-one lower-tail score rank
at the observed training-grid h_hat, using inclusive ties and the same refitted
reference histories. Threshold at 0.05 without a new selection or recalibration
step. The fitted node is data-selected, so its rank does not inherit the
fixed-node super-uniform guarantee. Three baseline checks are useful operating
characteristics, not universal validation. Because h_hat is in C99, every primary
rejection is already a secondary rejection at the same 0.05 threshold; extra
secondary flags must be considered with their own baseline false-rejection rate.
There is no combined reject-on-either decision or change to primary H.

## Observation and confounding mechanisms

Predator heterogeneity is a worthwhile addition: it changes the observation
likelihood for latent arrivals while supplied rho remains fixed. A mink-survey
motivation does not turn this synthetic experiment into empirical validation.
Prey heterogeneity also need not average away. With two visits while occupied,
site-fixed p and independent visit draws conditional on p,

`P(two non-detections) = (1 - E[p])^2 + Var(p)`.

At mean p=0.65 this is 12.25% for fixed detection, 13.25% at SD 0.10 and 16.25%
at SD 0.20. This elementary mixture effect shows why the repeated-observation
likelihood changes even when the mean detection probability is correct. It
establishes neither a particular bias direction nor a coverage loss; P1/P4
remain predictions to test.

Fable's requested sampled-site field summaries are useful. Report whole-map,
training, held-out and all-sampled mean hazards; do not assume the training
mean must exceed 0.002/day. Use time-at-risk exposure through day 60 as the
primary evaluator-only correlation diagnostic, with no-arrival sites retained
as zero exposure. Raw arrival correlations among arriving sites are secondary
and include their site count. Undefined correlations remain undefined.

Correct one detail in our earlier proposal: common positive rescaling to an
exact landscape mean changes neither a field's realised CV nor its Pearson
correlations. Correlation, finite-map variation and the fixed-covariate mixture
explain why nominal lognormal CV need not equal realised spatial CV. Neither
CV nor realised alignment is retuned. The r=0 and r=0.7 constructions also
change the random-field contribution, so they isolate a specified construction
contrast rather than holding every spatial field property constant.

## Endpoints and forecasts

Report baseline M and H, each component of M, mean signed log bias, both detector
rates and primary M AND D. H remains the risk-based nomination endpoint;
large misleading effects that are detected remain an explicit useful result.
The revision clarifies nomination among eligible cells and its unresolved
category. Independent confirmation must meet the same positive-interval and
five-point relevance conditions, on new histories. Neither selection nor
confirmation is retrospectively repaired if it fails.

Fable's P2 supplies three predictions: strict false effects above 20%, primary
detector rejection below 10%, and an H increase above 10 percentage points.
The first two imply an absolute unflagged strict-false-effect frequency above
10%, but they do not imply a ten-point increase over a nonzero baseline H.
The revised table treats all three as separately testable quantities. P3's
zero-containing interval is a prediction of non-resolution, not equivalence;
its width prediction concerns the calibrated set, not monotone information.
No paper example is promised before the screen runs.

The fixed-table null exclusion rate is not 5–7% by construction: the marginal
rank guarantee and the realised table's probability content are different.
The 5.7% and 7.4% archived counts are observations. Future baseline M, bias and
H are measured in the new paired campaign; Fable's suggested baseline point-error
rates are not treated as established input values.

## Scope and cost for Barry

The 21 September proposal comprised 13 cells/13,000 histories, projected at
8,695 seconds (2.42 h), within a proposed four-hour envelope. The revision adds
three predator-detection cells and one real-effect confounding cell: 17,000
histories, no extra calibration replay. Using the rounded-up observed scoring
rate 0.248 s/history and the same 1.5 factor, integration and reserves gives
**10,202 s (2.83 h)**. The proposed hard ceiling remains **four hours, eight
workers and 32 GiB**. Field construction and secondary analysis need full-cell
timing before launch; this projection is not measured new-generator throughput.
No automatic reduction or expansion is authorized if timing fails.

[The revised proposal](next-screen-proposal.md) bundles the scientific choices
for one approval: the 17 cells/severities, primary and secondary roles, relevance
thresholds and predictions, and the compute/stopping envelope. This turn does
not implement it. The repository [AGENTS.md](../../../AGENTS.md) requires
human review at scientific gates, including observation design and model
comparisons. Barry's earlier approval covered Goal 050, which is complete;
it did not authorize alternative generators.

One nested detection alternative plus a neutral comparator could be a lean
Stage 2 candidate. Nesting does not establish identifiability or calibrated
comparison, and a boundary variance parameter does not supply a chi-square
reference automatically. The charter still requires fitting the preferred and
alternative models to datasets from the generating models and comparing them
with a neutral predictive baseline. Low primary power, or a negative screen,
would not remove that requirement. Barry retains the paper-scope decision.


A bounded independent methodological check supported these revisions and
identified no remaining conceptual blocker to putting the package to Barry.
Proposal cell-count/cost arithmetic, document links and whitespace checks pass;
frozen Goal 050 runner, synthesis and registration hashes remain unchanged.
Astra replied on thread 53 in messages **475–476**. Barry's approval is the next
decision; further Fable correspondence is optional before that decision.
