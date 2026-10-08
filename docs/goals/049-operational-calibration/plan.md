# Goal 049 proposal: uncertainty without knowing the prey-effect truth

20 September 2026. **State: completed; see the [synthesis](synthesis.md) and
[independent review](final-review.md).**
Barry's “please proceed” follows Fable's critique on Correspondence thread 44,
messages 276–280. The original proposal is preserved in
[plan-2026-09-19.md](plan-2026-09-19.md). This revision accepts the matched-weight
bank comparison, separate regulariser sweep, cutoff-curve figure, archived
speed-transport check and fourfold evaluation truth. The
[pre-run registration](registration-2026-09-20.md) freezes predictions and
execution choices before diagnostics or new simulation. No commit, push or
publication authority is inferred.

Programme role: a short calibration bridge from Arc 3 to Arc 4; Charter
Pillars 2 and 4 and the paper's uncertainty-calibration question. Arc 3 remains
conditionally closed with its four numerical failures preserved.

## Recommendation and review summary

Build one analyst-usable **discrete confidence set for prey effect**, first
conditional on supplied spread speed and the other currently known inputs.
Calibrate a test at every candidate effect, then retain the candidates whose
tests do not reject. The analyst receives the entire fixed calibration table,
not a cutoff selected using the hidden generating effect.

Three stages are authorised within this contract:

1. Apply the reviewed interpretation amendments identified in the
   [claims audit](claims-audit.md), preserving original results and decisions.
2. Use the accepted Arc 2C archive for cutoff-transfer and three-candidate
   test-inversion diagnostics. This is retrospective evidence, not validation
   on unseen datasets.
3. If the bounded timing check permits, construct the full existing 181-node
   calibration table and evaluate it on fresh histories at six frozen truths.
   Finish with either a usable model-conditional procedure and measured
   resolution, or a named computational/numerical limitation. Then move toward
   Arc 4; do not expand into a general calibration-method competition.

The important new evidence will be **set geometry, exclusion of false
candidates and non-null detection power**. Coverage at the true candidate,
point estimates and predictions cannot improve against a matched oracle
benchmark: they are identical by construction under the comparison below.
This invariant is a central review question, not a minor implementation detail.

### Questions for Fable

1. Does the candidate-wise construction and its separation from oracle
   flat-cutoff supports correctly remove access to the unknown effect while
   retaining the stated finite-grid, known-nuisance scope?
2. Are the coverage identities and the distinction between a calibrated
   approximate score and exact-integration fidelity correct? What claim could
   our proposed experiment genuinely falsify?
3. Are the full grid, 999 calibration replicates, six evaluation truths and
   numerical tolerances below proportionate? Prefer a specific alternative
   before implementation if they are not.
4. Do the proposed cross-arc interpretation amendments preserve the earlier
   evidence honestly, especially Arc 2B's coverage-only classification failure?

These original review questions are retained as context. Fable answered all
four on thread 44; the registration records the resulting amendments.

## 1. What the claims audit found

The historical syntheses use different calibration and prediction regimes;
they cannot all be relabelled with the same blanket rule. Arc 2A measures
joint-region coverage and projected widths, whereas Arc 2B/C use effect
supports. Same-truth joint coverage is a calibration check; marginal coverage
of a projection does not inherit an exact zero-contrast statement automatically.

The clearest consequential finding is Arc 2B S08: its sole failed
full-recovery gate is coverage. Removing that gate would change the historical
3/10/19 category counts to 4/9/19, with no changed observations. This is a
reviewed retrospective interpretation amendment, not a change to observations
or to the original decision record. The 19 weak
detection cases and the point-error/prediction evidence survive. Arc 2C's
30 zero-including contrasts contain eight calibration checks; the remaining
22 still support its bounded no-detected-added-cost conclusion.

Arc 1 already contains a nontransportable-cutoff result in Goal 005. The new
archive diagnostic targets the prey-effect procedure and usable test inversion,
rather than rediscovering transport failure for predator speed.

## 2. Inferential object and mathematical contract

Let h be the prey post-arrival hazard multiplier and
G = {1, 1.05, ..., 10}, the existing 181-node effect grid. Fix the accepted
reference landscape, access design, 120 training/40 holdout sites, six surveys,
two visits, resistance 1, supplied speed rho=1, both detection probabilities
0.65 and background hazard 0.002/day. Arrival remains latent. Only h is
unknown to this initial analysis; this is not a field-ready unknown-nuisance
procedure.

For a frozen integration bank B, define the deterministic composite score

`T_g(y; B) = 2 * [max_{u in G} CL_B(u; y) - CL_B(g; y)]`.

For each candidate g, simulate complete training datasets under the declared
model at g and apply exactly the same score. Let c_g(B) be the chosen ordered
calibration statistic. Return the set

`C(y; B) = {g in G : T_g(y; B) <= c_g(B)}`.

Do not smooth/interpolate cutoffs, fill holes, select a table row using the
evaluation truth, or substitute an estimated parameter for that truth.
Report the exact membership set, components, cardinality, boundary contact
and log hull span. The hull is a summary, not a replacement for membership.
On the full G grid, the set must contain a grid maximizer because its score
is zero and every calibrated cutoff is nonnegative. This invariant does not
apply to the three-candidate archive subset, whose fitted maximum can lie
outside that subset.
Claims cover truths on G only; no continuous-parameter or off-grid coverage
claim is licensed. Inverting candidate tests is the standard confidence-set
construction; see [Stark's inference notes](https://www.stat.berkeley.edu/~stark/Teach/S240/Notes/ch5.htm).

With 999 calibration histories per candidate and the 950th ordered statistic,
exchangeable tie-free scores give marginal true-node inclusion 950/1000=0.95.
Inclusive ties can increase coverage. This averages over calibration and
evaluation histories. The coverage conditional on one realised calibration
table is not fixed at 0.95; under iid continuous scores its probability content
at a candidate has the Beta(950,50) law. Across-node dependence from common
random numbers does not invalidate each candidate's rank argument.

The guarantee applies to the bank-specific scoring algorithm if the bank is
independent of calibration/evaluation generation and identical scoring is
used in both phases. Exact integration is not required for exchangeability.
Generate complete histories from the original stochastic process and
observation model, not by resampling the fitting bank or drawing sites
independently. Retain the accepted scoring and pseudocount rules; no replacement
integrator is adopted in this experiment.
Poor integration may still impair point accuracy, power, set geometry and
reproducibility. Calibration does not validate an exact likelihood or protect
against a wrong generating-model assumption.

### Exact comparison invariants

The diagnostic oracle benchmark uses the same table but applies c_h to every
candidate when evaluating histories generated at h. At the true node,
candidate-wise and oracle supports both compare T_h with c_h. Therefore:

- their truth membership is identical for every history, including ties;
- null-truth false exclusion is identical;
- MLEs and held-out predictions are identical when fitting is unchanged;
- under h>1, candidate-wise null exclusion uses c_1 while oracle exclusion
  uses c_h, so non-null power can differ;
- inclusion of other false candidates, width and topology can differ.

Neither coverage improvement nor a point-accuracy gain is a possible discovery
in this comparison. Coverage and point/prediction identities are verification
controls. Set resolution and non-null power are the scientific outcomes.

## 3. Archive diagnostic: fixed, cheap and retrospective

Use the existing Goal 045 reference bundles:

- `artifacts/goal045_execution/reference65536/output/`;
- `artifacts/goal045_execution/reference131072/output/`.

Their profile and run-summary identities must match their recorded receipts.
The schema has six conditions, two lanes, 250 calibration and 250 evaluation
histories, and all 181 effect-profile values. Retain known-speed analyses only.
Analyse rho=1 and rho=0.5 separately as supplied, known design contexts; never
pool them as independent confirmations for the effect-set construction. A separately labelled speed-cutoff
transport diagnostic below deliberately tests transfer across speed.

Within each speed, use calibration sources and evaluation truths {1,3,5}:

1. **Scalar transport matrix:** for each source a and evaluation truth t,
   apply the source cutoff c_a to the full saved profile. Record source,
   truth, coverage, exact-set geometry and null exclusion. Diagonal coverage
   is a calibration check; off-diagonal coverage tests transport. The c_1
   null test has a calibrated null size; using c_1 for every candidate does
   not confer that guarantee on a whole confidence set.
2. **Candidate-acceptance matrix:** record
   `I[t,a,j] = 1{T_a(y_tj) <= c_a}`, for a,t in {1,3,5}. Contrast it with
   oracle-flat acceptance `1{T_a(y_tj) <= c_t}` on the same histories. This
   yields three candidate tests, not a continuous interval or an interpolated
   181-node confidence set. Retain empty subsets if they occur.
3. Reproduce the diagonal/oracle identities and compare banks. Cutoffs remain
   rank 239 of 250, retaining the archive's 239/251 tie-free benchmark.
   If uncertainty summaries are needed, use one fixed 2,000-draw complete-
   history bootstrap, independent calibration/evaluation resampling, shared
   across candidates and banks. Label conditional-binomial and calibration-
   aware uncertainty separately. Do not select a winning cutoff source or
   tune Stage 4's design to favourable off-diagonal results.

4. **Archived speed-cutoff transport:** use the saved spread-score profiles and
   spread calibration statistics to apply the rho=0.5 and rho=1 cutoffs to
   evaluation histories at both speeds, separately at effects 1, 3 and 5.
   This diagnoses the earlier speed statistic; it is not a transfer of the
   effect-set construction or an unknown-nuisance qualification.

Both archived banks used alpha=0.5. Their comparison therefore mixes empirical
bank movement and relative regulariser-weight movement; it is descriptive,
not the matched-weight check specified for the fresh experiment.

Deliver a two-panel effect matrix, a separate speed-transport display, source/
truth labels and a short interpretation.
No new process histories or model fits are needed. Stage 4 proceeds only if
the existing score semantics and the stated identities reconcile; an identity
failure triggers diagnosis, not a silent change of estimand.

## 4. Proposed full-grid, fresh-history experiment

Use the fixed rho=1 reference context above. Supply one table covering all
181 candidates. Generate 999 calibration replicates per candidate, then 1,000
new evaluation histories at each of h={1,2,3,4,5,10}. These represent null,
weak effect, two transition anchors, strong anchor and upper-domain boundary.
The truths were chosen before any Goal 049 outcomes, but their values are not
claimed to be previously unseen in the programme. Independence refers to new
history streams, not new landscapes, biological models or parameter values.

This is 180,819 candidate-specific calibration histories and 6,000 evaluation
histories: 186,819 history evaluations, each scored on G. Common random numbers
may pair candidates within a phase; each candidate's replicate sequence must
remain iid, and calibration/evaluation phases must be disjoint. There are about
33,814,239 dataset-candidate score cells per scoring variant. This is a workload count,
not a measured runtime estimate. Do not retain a large joint rho/effect tensor
when only the supplied-speed slice is used.

The primary comparator is the matched oracle-flat cutoff with the same 999
calibration histories per candidate. It must not reuse the old 250-history
oracle as if the calibration budget were matched. A fixed c_1 scalar support
may be shown as the prespecified transport comparator, explicitly lacking a
general coverage guarantee away from h=1. A fixed chi-square(1) 95% cutoff is a descriptive comparator without a
coverage guarantee; compare its membership and geometry empirically rather
than inferring similarity from cutoff proximity. No plug-in or fitted cutoff method
is added to this initial comparison.

### Separation of truth from analysis

Before execution, freeze the generator/design, source identities, seed roots,
node order, calibration rule and analysis contract. Because the working tree
contains earlier uncommitted research, a Git HEAD alone is not a sufficient
source identity. Use a compact source/inputs receipt, not a new control system.

The calibration engine knows g to generate its row; the analyst receives the
complete frozen table and known nuisance/design inputs. Evaluation observations
carry opaque IDs. The analysis interface must not accept true h, truth role,
realised arrival/extirpation times or a condition label encoding h. Freeze
outputs before the evaluator joins truth to them. Truth-assisted diagnostics
and the oracle comparator are evaluator-only. Holding out prey observations
for prediction does not replace this separation.

### Outcomes and uncertainty

Report candidate-membership/false-candidate-exclusion matrices; mean log hull
span, set cardinality, components and boundary frequencies; null rejection at
h=1; and non-null exclusion of 1 at the other truths. Pair methods and banks
within history. Retain point error and held-out prediction as context and
identity checks, not evidence of a gain caused by calibration.

For rates, report denominators and conditional binomial intervals. Separately
show calibration-aware paired resampling uncertainty using the fixed 2,000
bootstrap draws, resampling whole histories with candidate pairing preserved.
These are empirical-bootstrap diagnostics, not a new exact coverage theorem.
Make the candidate-cutoff curve a primary figure. Show pointwise LR-scale
order-statistic confidence bands for each population 95% score quantile,
using binomial rank limits; these are not simultaneous curve bands. Mark
chi-square(1) 95% and 90% quantiles as heuristic references only, and show
zero-score fractions at the two domain boundaries. Beta(950,50) describes
probability content, not uncertainty in LR units. Preserve full calibration
and evaluation score curves for paired reanalysis.
Near-zero interval conclusions remain unresolved; no bootstrap top-ups to
force exclusion. Avoid classifying recovery by counting significant contrasts.

The true-node coverage and null-size checks assess implementation against the
rank construction. Under continuous scores, evaluation counts averaged over
calibration have a beta-binomial reference, not a simple Binomial(N,0.95).
Ties can yield conservative coverage. Do not require every realised Wilson
interval to contain 0.95 or classify broad sets as successful ecological
recovery merely because coverage is nominal. An unexplained severe departure
triggers a pipeline/model audit; retain the original draw and do not rerun for
a more favourable coverage count.

## 5. Numerical checks, resources and stopping

Use the existing K65536 bank at alpha=0.5 and its nested K131072 reference
at alpha=1.0 for the **primary matched-relative-weight comparison**. Reweight
integration sufficient statistics with `integration_weights.reweight_integration`;
never try to reweight saved LR curves. This holds the pseudocount fraction fixed,
not exact integration bias or a pure Monte Carlo variance estimate.

At fixed K131072, separately report alpha={0.25,0.5,1.0} sensitivity without a
pass/fail gate. Thus there are four scoring variants in total. The optional
same-alpha bank comparison is available but labelled confounded. Use the same
new histories and a separately recalibrated candidate table for every variant.
The old six-case acceptance does not certify all new candidate scores. Begin
with fixed boundary/interior canaries (h=1,3,10; first two calibration and
evaluation histories) and a timing probe before the full campaign.

Declared **endpoint-sensitivity tolerances**, at each of the six
evaluation truths, are bank movements no larger than:

| Operational outcome | Absolute bank-movement tolerance |
| --- | ---: |
| True-node inclusion or null-exclusion frequency | 0.01 |
| Mean log hull span | 0.01 |
| Boundary-contact or disconnected-set frequency | 0.01 |
| Mean absolute log point error | 0.005 |

These declared tolerances protect interpretability of the reported outcomes;
they are not bounds on exact-integration bias or consequences of the rank
theorem. Report all movements, cutoff shifts, individual membership changes
and pointwise uncertainty, including failures. Ratios to estimated standard error are descriptive only;
when SE is zero, report the absolute movement and an undefined ratio. No added cutoff-LR gate overrides
the endpoint comparison. If an outcome fails, report it as bank-sensitive;
do not enlarge the bank or relax the tolerance in this tranche. No speed-lane
equivalence or all-landscape method qualification follows from a pass.

The resource ceiling is 24 elapsed hours total for
timing, all four scoring variants and analysis, no more than eight CPU workers and
32 GiB aggregate memory, with no GPU requirement. Route a substantial run to
the established Linux compute host after normal live preflight; no remote
work begins until controls and timing support this ceiling. Project the full workload from the timing
probe. If it exceeds the ceiling, stop with a costed alternative for review;
do not silently shrink the grid, lower replication or replace calibration by
interpolation. At most one implementation repair is allowed after a failed
control, retaining its evidence and before decisive evaluation.

The scientific stopping rule is one complete comparison and explanation of
what is established, bank-sensitive, uninformative or unaffordable. Negative
power or broad/disconnected sets are valid results. Success does not require
better widths, power or coverage than the oracle benchmark. Do not launch
extra calibration blocks, maps or independent-bank studies to obtain a
preferred finding. More general numerical accuracy remains a separate claim.

## 6. What follows and what is deferred

The deliverable is a source-bound known-speed confidence-set procedure on G,
or a precise bounded limitation, with the archive matrix and one operational
resolution/power figure. Acceptance concerns the truth separation, rank-rule
implementation, declared limits and reproducibility; useful resolution is an
empirical result. The paper must distinguish those two outcomes.

Estimated speed, unknown detection/background/resistance, continuous-parameter
coverage, additional maps and the independent-arrival dependence experiment
are deferred. Plugging in estimated rho is not an automatically valid extension;
joint candidate-wise calibration with projection or another justified nuisance
treatment needs a separate scientific design.

For subsequent Arc 4 work, freeze the assumed-model fitting/calibration rule
while changing the generating mechanism. Do not recalibrate under the actual
alternative generator: that would hide the misspecification the experiment
is meant to expose. The alternative-model set remains to be reviewed.

## Review disposition

Fable supported implementation once the matched-weight comparison and predictions
were written. Those conditions are recorded in the registration. The critique
is advisory evidence; Barry's current instruction authorises this bounded work.
A compact implementation review and the specified controls precede the main run.
There is no new requirement for a second model approval before execution.
