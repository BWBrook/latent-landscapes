# Goal 049 independent final scientific review

20 September 2026. Review scope: the registered known-nuisance, finite-grid
calibration result, its archive transport precursor, and the fixed 2,000-draw
synthesis. This review did not alter source, histories, scores, calibration
draws, or synthesis outputs.

## Decision

**GO, with a required calibration caveat.** Goal 049 establishes an
analyst-usable candidate-wise confidence-set construction for the frozen
reference generator and the 181-node effect grid. The matched K65536,
alpha=0.5 versus K131072, alpha=1 comparison is stable under every registered
endpoint tolerance, and all three preregistered predictions are supported in
their stated scopes. The procedure is nevertheless only *marginally*
rank-calibrated over random calibration tables. The realised primary table had
true-node inclusion 926/1000 at h=1, equivalent to a 7.4% false-positive rate;
it must not be described as a conditionally 95% table.

This is a successful conditional synthetic result, not biological
recoverability, exact-integration validation, field readiness, or evidence for
unknown-nuisance coverage.

## Scientific target and scope

The inferential target is the discrete candidate set

`C(y; B) = {g in G: T_g(y; B) <= c_g(B)}`

for prey-effect multiplier `h` on `G={1,1.05,...,10}`. Each candidate cutoff is
the registered 950th order statistic from 999 new histories generated at that
candidate. The relevant operating characteristics are true-node inclusion,
false-candidate exclusion, set cardinality/topology, and log-hull span. The
held-out prediction score and grid MLE are shared by all support methods and
therefore provide context and identity checks, not evidence that calibration
improved prediction.

The generator fixes the reference landscape, 160-site clustered design (120
training, 40 holdout), six surveys with two visits, spread speed rho=1,
background hazard 0.002/day, and predator/prey detection probabilities 0.65.
It samples spatial spread shocks, extirpation thresholds, and detections as
complete histories. Calibration and evaluation use the same generator and
scorer with independent deterministic roots; replicates are iid within phase,
while common random numbers deliberately pair candidate truths within a
replicate. The integration bank is independent of both phases. Thus the six
truth checks and 181 cutoff nodes are dependent comparisons, not independent
replications.

## Decisive evidence

### Registered predictions

- **P1, boundary effect:** the primary cutoff was `c1=2.27937`; the median over
  `2<=g<=8` was `4.01873`, giving the preregistered ratio 0.567. A flat `c1`
  cutoff included the true node in only 0.863 of h=3 histories and 0.873 of
  h=5 histories. Candidate-wise null exclusion exceeded the oracle-flat value
  by 0.067 at h=3 (paired calibration-aware 95% interval 0.044 to 0.115) and
  by 0.002 at h=5 (0 to 0.006). The h=3 difference is resolved; the h=5
  direction is too small to treat as a resolved effect.
- **P2, interior cutoff scale:** all 121 point cutoffs for `2<=g<=8` lay between
  3.72810 and 4.33948, inside the registered 2.68902--4.99390 heuristic range;
  maximum/minimum was 1.164. Even the pointwise order-statistic bands remained
  inside that range (overall lower minimum 3.34770; upper maximum 4.95359).
  These are correlated nodes and pointwise, nonsimultaneous bands. Proximity to
  chi-square(1) is descriptive and does not confer an asymptotic law.
- **P3, archived speed transport:** all six bank/effect rows had the predicted
  cutoff ordering. Applying the rho=0.5 cutoff at rho=1 produced coverage
  0.800--0.808, deficits of 0.144--0.152 from 239/251. Applying the rho=1
  cutoff at rho=0.5 produced 0.980--0.984, excesses of 0.028--0.032. The
  registered at-least-one-direction severity condition passes at every effect.
  An excess of 0.05 in the latter direction is arithmetically impossible from
  the 239/251 reference and is not evidence supplied by this result.

### Resolution, power, and comparators

For the primary candidate-wise procedure, coverage at h={1,2,3,4,5,10} was
{0.926, 0.960, 0.954, 0.957, 0.957, 0.958}. Null-effect exclusion was
{0.074, 0.565, 0.918, 0.994, 1.000, 1.000}. Mean set cardinality was
{28.5, 50.3, 65.6, 77.2, 85.4, 59.2} of 181 nodes, and mean log-hull span was
{0.818, 1.086, 1.064, 0.966, 0.867, 0.358}. Thus detection of departure from
the null becomes strong by h=3, but discrimination among non-null effect sizes
remains weak. The procedure usually returns connected sets; observed
disconnection was zero except 0.5% at h=10.

Candidate-wise and oracle-flat true-node membership were identical for every
history, as they must be. Their MLEs and holdout predictions were also
identical by construction. The oracle-flat comparator is evaluator-only because
it selects a cutoff using the hidden truth; it is not an operational
alternative. The fixed chi-square comparator has no finite-sample guarantee:
its apparent h=1 coverage of 0.975 does not repair the candidate table or
justify replacing the registered construction.

### Numerical and regulariser sensitivity

The matched high-minus-low bank comparison had zero movement in true-node
inclusion, null exclusion, and boundary contact at all six truths. The largest
absolute registered movements were 0.0000528 in mean log-hull span, 0.001 in
disconnection frequency, and 0.000108 in mean absolute log point error. All
were far inside the declared 0.01, 0.01, and 0.005 tolerances. Only 0.4--1.3%
of evaluation histories at a truth had any candidate-membership change; across
all history-by-node cells the change rate was 0.0022--0.0072%. The maximum
point-cutoff shift was 0.0100 LR units. The fixed-K alpha sweep was similarly
small, but it has no preregistered pass rule. These nested-bank results support
endpoint robustness only; they do not estimate pure Monte Carlo variance or
prove exact integration.

## Calibration check and diagnostic interpretation

The h=1 inclusion count 926 lies below the tie-free beta-binomial central 95%
reference range 930--968 for `Ncal=999`, rank 950, and `Neval=1000`. Its
one-sided predictive tail probability is 0.01276. The calibration-aware
bootstrap interval was 0.903--0.944; the fixed-cutoff Wilson interval was
0.908--0.941. This is a decision-relevant realised-table limitation.

No corresponding pipeline discrepancy was found. Calibration and evaluation
call the same observation generator and scoring function with identical fixed
inputs; the phase label is stripped before scoring and only selects a disjoint
root. Post hoc score-distribution comparisons detected no phase shift at the
six tested truths (two-sample KS p-values 0.38--0.78), but these checks do not
prove exchangeability or rule out a tail-specific discrepancy. At h=1, the score has a substantial
boundary atom at zero (calibration 0.555; evaluation 0.524), but the positive
cutoff had one calibration equality and no evaluation equality, so inclusive
cutoff ties do not explain the low count. All four numerical variants reproduce
the same 926/1000 classification. Given the prespecified beta-binomial tail,
dependence among the six truth checks, and absence of a mechanistic mismatch,
the defensible interpretation is an uncommon marginal low-tail realisation,
not grounds for redrawing or post hoc retuning.

The raw bootstrap CSV contains harmless floating-point rate bounds up to
`1.0000000000000007` and machine-epsilon standard errors for mathematically
constant series. The parent applied the reporting correction in
`artifacts/goal049_execution/review/reporting-correction.json` from the same
saved draws: bounded rate summaries, exactly zero constant-series SEs and
undefined movement/SE ratios where required. Point estimates and tolerance
decisions are unchanged; raw outputs and receipts remain intact. This resolves
the reporting issue without new draws.

## Residual risks and recommendation

The dominant uncertainty is structural rather than computational. Spread,
detection, background hazard, resistance, map, and observation design are
known and fixed; nuisance confounding, misspecification, informative missingness,
spatial transfer, off-grid coverage, and continuous-parameter behaviour remain
untested. Full-grid evaluation avoids optimiser and MCMC convergence failures,
but it does not resolve weak information: broad sets and boundary contact show
where the likelihood remains uninformative. Pointwise cutoff bands are not a
simultaneous confidence band, and correlated nodes must not be counted as 121
independent confirmations.

Retain this table as a reproducible known-nuisance finite-grid reference and
state both the marginal rank guarantee and the realised h=1 7.4% false-positive
rate wherever coverage is discussed. Do not redraw this campaign. The next
discriminating experiment is the already planned Arc 4 misspecification study:
freeze this fitting/calibration rule, change the generator, and measure loss of
coverage, power, and geometry without recalibrating under the alternative.
Unknown-nuisance or field use requires a separately reviewed joint or projected
calibration design.

Another independent audit is unlikely to change the Goal 049 decision because
the decisive identities, tolerances, and prediction contrasts are directly
reproducible. Independent scientific review would materially matter before
choosing the Arc 4 alternative generators or promoting this conditional result
to a manuscript-level generality claim.
