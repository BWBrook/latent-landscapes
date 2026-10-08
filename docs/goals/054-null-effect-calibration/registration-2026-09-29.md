# Goal 054: an adjusted null-effect decision

29 September 2026. Approved implementation; Pillar 4 / Arc 4.

Barry's authority in Codex: **“Yes, calibration run approved. Yes to extra
conditions. You remain in control of compute decisions.”** This accepts the
Goal 053 [proposal](../053-prospective-background/null-effect-calibration-proposal.md)
and the nonlinear stress pair in Fable's thread 53 messages 646–647. Routine
resource and time decisions remain with Astra. No commit, push or publication
is authorized. This registration is frozen before fresh reference/evaluation
generation. Implementation and independent methods review precede production.

## Question and completion

Can adjustment control false effect declarations under its assumed spatial
background family, at an acceptable sensitivity cost, and where does that
protection end under misspecification? Close with a verified reference table,
independent eight-cell evaluation, fixed 2,000-draw uncertainty analysis,
independent result review and conditional scientific synthesis. Conservative
tests, poor sensitivity and failed forecasts are valid outcomes. Do not alter
the rule or generate extra histories in response to an unfavourable outcome.

Goal 053 remains closed. Its retrospective cutoff preview motivates this
experiment but is not fresh calibration or validation. The new simulated
supremum cutoff is not mathematically required to exceed an independently
estimated old two-node cutoff: superset monotonicity holds within the same
reference table, not between independently estimated tables.

## Frozen science

Keep the accepted landscape, 120 training and 40 cluster-isolated held-out
sites, six surveys at times 10 through 60, two visits, known mean background
hazard 0.002, detection 0.65, spread speed/rho 1, and the original K131072
alpha1 empirical arrival bank. Fit the full rectangle h=1..10 by .05 and
beta=-2..2 by .05 (181 by 81 nodes). All estimation and decision statistics
use training observations only. Holdout observations enter prediction summaries
only. Reuse authenticated integrations of the unchanged likelihood. No oracle
campaign, new nuisance estimates, survey, landscape, confidence support or
model-selection pretest is included.

Reference panel: **999 independent paired blocks × 81 exact-null beta nodes =
80,919 histories**, all at h=1. Within a block share process, prey-event and
detection variates across beta; keep blocks independent. Exact background is
`mu_i = .002 * exp(beta*A_i) / mean_map(exp(beta*A))`. A is the frozen map
exposure score. The denominator uses the whole accepted map.

Evaluation panel: **1,000 new independent paired blocks × eight cells =
8,000 histories**. Cell order is E0_h1, E0_h3, E06_h1, E06_h3, B100-A_h1,
B100-A_h3, N100-A_h1, N100-A_h3. The first six reproduce the Goal 053 laws,
including exact beta0 and beta.60 and the original aligned residual field.
All eight share each block's underlying streams. Total new histories: 88,919.

For the new nonlinear pair define `I_i = 1[A_i > q_(2/3)(A)]`, with NumPy's
linear empirical quantile over accepted map cells; tied A values receive the
same indicator. Define `B=(I-mean_map(I))/sd_map(I)`, then
`z=.70*B + sqrt(.51)*G` and
`mu=.002*exp(sqrt(log(2))*z)/mean_map(exp(sqrt(log(2))*z))`.
G is the same unconditioned stationary Gaussian sampler and same block draw
as in B100-A. It is not orthogonalized against A. This replaces only the
structured linear component; the nominal mixing and transformation stay fixed.
The deterministic map has 2,015 of 6,048 cells strictly above the threshold.
The aligned component is a plateau near the invasion source, which a
log-linear A term cannot represent exactly. Residual G remains present, so
this is functional-form plus residual-field misspecification, not a pure
unmeasured-covariate test. Nominal strength does not assert identical realised
CV, correlation or training/holdout hazard means. Report these diagnostics,
the selected fraction, and the residual of the best affine-A approximation.

## Seeds and independence

Use the existing seven-stream SeedSequence scheme, with these distinct roots:
reference 2026092901; evaluation 2026092902; timing reference 2026092903;
timing evaluation 2026092904; bootstrap 2026092905; smoke 2026092906.
Record full stream identities and check separation from all earlier campaign
roots and bank seeds. Reference/evaluation independence concerns stochastic
histories, not landscapes, sites or the fixed analysis bank. Fresh production
histories must not be generated during testing or timing. Opaque IDs include
goal, panel, root, block and cell; analysts never receive latent event times.

## Registered rules

`T_adj = 2*(max_(h,beta) ell(h,beta) - max_beta ell(1,beta))`.
At each reference truth beta_j fit this whole statistic, with beta estimated
in both maxima. For observed t, `p_j=(1+sum(T_ref,j >= t-1e-12))/1000`.
**Primary:** declare only if `max_j p_j <= .05` over all 81 nodes.
Numerical equality is retained conservatively. Report all nodewise rank-950
cutoffs, their maximum and all contributors, including whether box edges
determine it. Do not narrow the fit box after seeing this curve.

The constant comparator uses
`T_const=2*(max_h ell(h,0)-ell(1,0))` and the same plus-one rule against the
999 beta0 reference histories. Its assumed-model guarantee is only at beta0.

**Prespecified secondary Berger–Boos rule:** gamma=.01. In each null reference
history generated at beta_j retain
`D_ref,j=2*(max_beta ell(1,beta)-ell(1,beta_j))`.
For every evaluation history form all 81 `D_obs,j` in the same way and
`q_j=(1+sum(D_ref,j >= D_obs,j-1e-12))/1000`.
Set `C={j:q_j>.01}` and `p_BB=min(1,max_(j in C) p_j+.01)`; declare if
`p_BB<=.05`. A numerically empty C conservatively returns p=1 and is flagged.
Report candidate-set size and boundary inclusion. This rule is secondary
regardless of its observed power. Do not substitute an ordinary uncalibrated
likelihood interval for C. Rank-990 membership and rank-960 T thresholds may
accelerate computation only after exact equivalence to the plus-one rule is
tested, including ties and floating-point thresholds.

**Textbook benchmarks:** report T_adj and T_const exceeding 2.71 and 3.84.
These are empirical comparisons, not assumed chi-square laws. Agreement in
this design cannot establish simulation-free validity for other landscapes,
unknown nuisances or composite likelihoods in general.

The primary true-node plus-one p-value is super-uniform by exchangeability
of reference and evaluation histories conditional on the fixed bank. Its
supremum is therefore conservative under an exact on-grid null, averaging
over both reference and evaluation randomness. For Berger–Boos, exclusion of
the true beta has probability at most gamma; rejection while it is included
requires its p-value at most .05-gamma. A union bound supplies the .05 bound;
independence of the two quantities is unnecessary. Neither proof gives
conditional size for every realised table, covers between-node beta or any
misspecified stress field, or validates confidence coverage/estimation accuracy.

The restricted-nuisance construction follows Berger and Boos (1994),
[P Values Maximized Over a Confidence Set for the Nuisance Parameter](https://doi.org/10.1080/01621459.1994.10476836).
The finite-grid Monte Carlo implementation and probability argument above are
specified here rather than assuming an asymptotic nuisance confidence set.

## Outcomes and uncertainty

Primary outcomes are eight adjusted declaration rates and paired differences
from the constant calibrated rule. Show exact-null size and h3 sensitivity
separately from stress-field operating rates. Report all secondary rules.
Retain mean absolute and signed log estimation error, at-least-1.5-fold error,
joint declaration/error events, declared-subset counts and error, and paired
held-out adjusted-minus-constant and adjusted-minus-adjusted-neutral scores.
Declared-subset error is selected-subset description; a valid declaration is
not a guarantee of accurate magnitude. Use the existing deterministic grid
maximum/tie convention and retain boundary contacts.

For each rule, use the adjusted estimate for adjusted rules and the constant
estimate for constant rules. Let e=log(h_hat/h_truth) and J denote declaration.
Report sum(J), sum(J*e)/sum(J), sum(J*abs(e))/sum(J), and
sum(J*1[abs(e)>=log(1.5)])/sum(J). An empty denominator is undefined (null/NaN),
never zero. The joint declaration/large-error rate divides that last numerator
by all 1,000 histories. Use the same definitions inside bootstrap draws and
report undefined-draw counts rather than replacing them with zero.

Exactly 2,000 bootstrap draws independently resample the 999 reference blocks
and 1,000 evaluation blocks. Each resample preserves pairing across beta or
cells. Recalculate calibration, nuisance sets and decisions from stored scores.
Use the same evaluation draws for frozen-table and calibration-aware summaries.
Report percentile intervals and SEs, including paired contrasts. Do not
bootstrap sites independently. Bootstrap intervals approximate Monte Carlo
uncertainty; finite-grid validity comes from the argument above. No increased
replication is licensed by broad intervals or undesirable results.

Fable's quantitative forecasts are registered for the **primary full-supremum
rule**: realised exact-null rates 2–5%; E0_h3 sensitivity 65–80%; E06_h3
sensitivity at least 88%; B100-A_h1 adjusted at most 6% and constant at least
18%; N100-A_h1 adjusted rate greater than B100-A_h1. These are forecasts,
not run acceptance gates. Preserve all failures and distinguish pointwise
forecast outcomes from uncertainty-supported comparisons. No new quantitative
prediction is imposed on the secondary Berger–Boos rule.

## Execution, qualification and stopping

Use isolated root `deep-server-ts:/data/codex/scratch/goal054-null-effect-calibration-20260929`.
Deep-server was idle on 29 September with approximately 122 GiB available and
4.3 TiB free on /data. Its capacity supports this single-host workload.
The Goal 053 timing surrogate projects about 48.6 hours for 88,919 histories
before a 1.5 allowance; it is not a measured bound for the new implementation.
Use process workers, one numerical thread each, bounded history batches and
authenticated cached integrations. Choose final concurrency and timeout from
complete-workload timing (generation, all coefficient rows, output and synthesis),
with recorded measured resource use and a verification reserve. Resources/time
may be adapted under Barry's delegation while keeping the science unchanged.

Before production verify original source/input identities; all-grid legacy
score replay; six-cell generator replay under common test seeds; exact-null
and beta0 controls; seed separation; numerical ranks, ties and BB membership;
complete rectangular coverage and observation-only inference. Timing uses
disjoint histories. Source changes invalidate timing. Record source, helpers,
input, integration and output hashes plus start/end/exit receipts. Never
duplicate an active/completed phase. Resume only authenticated completed units
under unchanged scientific source after diagnosing an operational failure.
An unchanged failure is not repeated. Scientific failure is preserved rather
than retuned. Long runs use a quiet heartbeat; notify Barry only on completion,
material failure, a meaningful scientific finding or a decision needing him.

Close with figures/tables, source-bound evidence, independent result review,
scientific synthesis, updated handover and substantive Correspondence thread53
reply. Retain Goals 049–053, the unconfirmed Goal051 nominee and all previous
numerical failures. Full confidence calibration, new surveys/landscapes,
unknown nuisance and publication require a subsequent scientific decision.
