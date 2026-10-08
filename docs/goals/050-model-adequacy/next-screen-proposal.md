# Proposed first misspecification screen after Goal 050

Revised 23 September 2026 after Fable's thread 53 critique (messages 468–471).
The [review response](fable-screen-response-2026-09-23.md) records the
original 13-cell scope and the reasons for these changes.
**Proposal for Barry's scientific review; no implementation,
simulation, remote launch, Stage 2 fitting or publication authority is inferred.**
This is the costed next-screen design required by the
[Goal 050 registration](registration-2026-09-20.md). It advances Charter
Pillar 4 and Roadmap Arc 4 by asking whether two plausible departures can
produce misleading prey-effect estimates under the frozen original analysis.
It is a robustness screen, not the Arc 4 model-discrimination experiment or
exit gate.

## Recommendation

Screen two mechanisms together in one paired, prospective campaign:

1. site-fixed heterogeneity in prey or predator detection, varied separately
   with the correct marginal mean;
2. spatially correlated background prey loss, including an exposure-aligned
   field at both a physical null and a real threefold effect.

Use 1,000 independent complete histories per cell on the accepted landscape
and sampling design. Generate one matched assumed-model baseline at each of
`h = 1, 3, 5`, paired by replicate with every relevant departure. Analyse every
history using the unchanged constant-detection, constant-background model,
the frozen Goal 049 rank-950 effect table, and the frozen Goal 050 primary
detector. Add the fitted-node plug-in p-value as a secondary diagnostic using
the same saved reference scores; measure its own baseline rejection rates.
No calibration history, cutoff, detector reference score, C99 rule or fitting
grid is regenerated.

This design targets the two most immediate ways the current known-nuisance
analysis could be persuasive but wrong. Detection heterogeneity changes the
observation process while preserving the effect estimand. Correlated background
loss can generate a fitted predator effect when the physical truth is no causal
predator effect. Recolonisation and decaying post-arrival impact remain valuable
process departures, but adding them now would weaken attribution and enlarge
the scientific decision before these two mechanisms are understood.

Goal 050's prospective fresh-null detector rejection was `19/1,000 = 1.9%`
(calibration-aware 95% bootstrap interval `1.1–3.2%`; conditional Wilson
interval `1.22–2.95%`). This supports the prediction that
the frozen detector can be conservative under the assumed model. It does not establish low power against
a departure. Broad C99 sets and
confidence-set maximization motivate that prediction, but power remains an
empirical endpoint. A small response from both proposed tests would concern
those two tests of the same score; it would not establish undetectability by
other statistics or competing models.

## Scientific targets and scope of inference

For heterogeneous detection, the target remains the generating post-arrival
prey-extirpation hazard multiplier `h`. The prey-detection cells vary site-level prey
detection while predator
detection remains `0.65`. Three added predator-detection cells do the reverse.
The fitted model always fixes both detection probabilities at `0.65`. The latter
cells change the observation evidence about latent arrival histories even with
spread speed supplied; no spread-speed parameter is estimated. Neither bias
direction nor negligible harm from prey heterogeneity is assumed.

For four background-loss cells, physical `h = 1`: predator arrival has no
causal effect on prey loss. Add `B100-A` at `h = 3`, with site hazard `lambda_i`
before arrival and `3 * lambda_i` afterwards. This keeps the generating
post-arrival multiplier defined while asking about distortion of a real effect.
Site hazards vary around `0.002/day`; the fitted model fixes that background
value and estimates a single h. Its misspecified-model best fit need not equal
the physical multiplier. Evaluate against the declared physical h without
calling it an identified target of the misspecified constant-background model.

Inference is marginal over complete 160-site histories on the one accepted
landscape, including a fresh site field in each replicate. It does not establish
robustness to other landscapes, access networks, off-grid effects, unknown
spread speed, estimated nuisance parameters, or field data. The complete
history, including its spatial field and all sites, is the independent unit;
sites are never treated as independent replicates.

All other layers remain fixed: the accepted landscape and 120/40 split,
six survey occasions with two visits, zero false positives, stochastic spread
at supplied `rho = 1`, resistance contrast `eta = 1`, latent arrival, absorbing
prey loss, the 181-node effect grid and the K131072/alpha1 likelihood bank.

## Proposed generators and severities

### Site-heterogeneous prey detection

Within each complete history, draw one detection probability `p_i` for every
sampled site and retain it across all visits. Draw sites independently from a
Beta distribution with expectation `0.65`. Two severities are proposed:

| ID | Site-level SD | Beta concentration | Alpha | Beta | Spatial pattern |
| --- | ---: | ---: | ---: | ---: | --- |
| `D10` | `0.10` | `21.75` | `14.1375` | `7.6125` | iid among sites |
| `D20` | `0.20` | `4.6875` | `3.046875` | `1.640625` | iid among sites |

The baseline uses `p_i = 0.65`. Apply the same prey-detection uniform draw to
the baseline and departure at each visit, so only the threshold changes. Share
the predator process, prey-state process and every other random stream. Test
each severity at `h = 1, 3, 5`. The null detects spurious effects; `h = 3` and
`h = 5` test moderate and strong effects without treating dense grid points as
independent scientific conditions.

The iid pattern is deliberate: it establishes whether unmodelled site
heterogeneity alone matters. Access-aligned or spatially correlated detection
would mix heterogeneity with sampling and spatial-confounding mechanisms and
is deferred unless this screen or ecological judgment justifies it.

### Site-heterogeneous predator detection

Add `PD10` at `h = 1, 3, 5`. Draw predator detection independently among sampled
sites from Beta(14.1375, 7.6125), mean 0.65 and SD 0.10, fixed across visits;
prey detection stays 0.65. Couple baseline and departure through the same
predator-detection uniforms and share spread and prey-state streams. Use a
separate registered field stream from prey detection, and pair PD10 across the
three truths. This adds three cells while retaining both prey-only severities
as observation-mechanism controls. No simultaneous predator/prey heterogeneity
or new severity is added.

### Spatially correlated background loss

Generate a lognormal background-hazard field over the landscape. Let
`A_i` be the centred, unit-variance normal-score transform of negative
least-cost resistance distance from the frozen predator source: larger values
mark cells with greater deterministic invasion exposure. This covariate is
derived from the accepted map and conductance surface, not from realised
histories or the likelihood integration bank. Let `G_i` be a zero-mean,
unit-variance Gaussian field with
exponential correlation `corr(G_i,G_j) = exp(-d_ij/10)`, where distance is in
grid cells. Define

```text
Z_i = r A_i + sqrt(1-r^2) G_i
lambda_i proportional to exp(sigma Z_i)
```

and rescale each realised landscape field so its arithmetic mean over all
cells is exactly `0.002/day`. Use `sigma = sqrt(log(1 + CV^2))`. Here `CV` is
a nominal lognormal severity parameter: spatial correlation, the fixed `A_i`
component and finite-grid realization mean it need not equal the realised
across-cell CV. Scaling every hazard by the same positive constant to fix its
mean leaves the realised CV and Pearson correlations unchanged. Likewise,
`r` is a mixing coefficient, not
a guaranteed realised field-exposure correlation. Proposed cells cross two
nominal CV values with two exposure-mixing values:

| ID | Nominal hazard CV | Sigma | Exposure mixing `r` | Scientific role |
| --- | ---: | ---: | ---: | --- |
| `B50-I` | `0.50` | `0.4724` | `0.0` | correlated but exposure-independent negative control |
| `B100-I` | `1.00` | `0.8326` | `0.0` | stronger exposure-independent field |
| `B50-A` | `0.50` | `0.4724` | `0.7` | moderate aligned confounding |
| `B100-A` | `1.00` | `0.8326` | `0.7` | strong aligned confounding |

At `h = 1`, use `lambda_i` before and after predator arrival. At `h = 3`,
use `lambda_i` before and `3 * lambda_i` after arrival. Reuse each replicate's
B100-A field at both truths; the multiplier is the only change between them.
Couple each field cell to its constant-hazard
baseline using the same event-time uniform variate; share predator spread and
detection streams. The independent fields provide controls for adding
deterministic exposure
alignment to a spatially heterogeneous field; they do not hold every realised
field feature fixed. Pair the same Gaussian field across background variants
before applying each fixed mixing/severity transformation. The aligned fields
test the scientifically important
case in which background risk and expected invasion exposure share spatial
structure. They do not identify the biological source of that shared structure.

The exposure score, correlation length, CV values and alignment coefficient
must be frozen from the reference map and checked before outcome generation.
They are proposed ecological severities, not values established by Goal 050.
Record each field's achieved across-cell CV and correlation with `A_i`
descriptively. Also report the arithmetic mean hazard over all landscape cells,
all 160 sampled sites, the 120 training sites and the 40 held-out sites. The
sampled means can differ from 0.002/day; their direction is a prediction, not a
constraint. Do not recenter them to the landscape mean.

As evaluator-only diagnostics, report sampled-site correlations of background
hazard with the fixed map score A and with realised exposure
`E_i = max(0, 60 - arrival_i)`, using zero exposure for no arrival by day 60.
Report hazard-versus-arrival correlation separately among sites arriving by
60, with its site count; do not silently discard never-arriving sites from the
primary exposure measure. Give training/holdout summaries and an explicit
undefined value when variance is zero. These are diagnostics, not inference
inputs or tuning targets. Do not redraw, rescale beyond the fixed landscape
mean constraint, or retune a field to match nominal CV, mixing or sample means.
Anti-alignment (`r = -0.7`) and its possible masking effect are deferred.

## Cell design, pairing and replication

The revised 17 unique cells are:

| Generator | Truths | Severities | Cells | Histories per cell | Histories |
| --- | --- | ---: | ---: | ---: | ---: |
| Assumed-model matched baseline | `1, 3, 5` | one | 3 | 1,000 | 3,000 |
| Heterogeneous prey detection | `1, 3, 5` | two | 6 | 1,000 | 6,000 |
| Heterogeneous predator detection | `1, 3, 5` | SD 0.10 | 3 | 1,000 | 3,000 |
| Correlated background loss | `1` | four | 4 | 1,000 | 4,000 |
| Aligned background loss, B100-A | `3` | one | 1 | 1,000 | 1,000 |
| **Total** |  |  | **17** |  | **17,000** |

One replicate index supplies a common random-number block across all 17 cells.
Within each truth, its assumed-model history is the matched baseline for all
departures at that truth. The `h = 1` baseline is shared by the detection and background
variants. Phase roots must be new and disjoint from Goals 049 and 050; they are
to be registered only after Barry accepts the scientific design. Existing
evaluation histories are retained as historical evidence but are not reused
as the prospective matched baseline.

One thousand histories give a worst-case binomial 95% half-width of about
3.1 percentage points and about 1.9 percentage points for a 10% event rate.
Pairing should improve precision for departure-minus-baseline contrasts, but
no precision gain is assumed in the compute or interpretation contract.

## Frozen analysis and endpoints

For every generated history, fit only the frozen original 181-node model.
Apply the original Goal 049 candidate-specific rank-950 effect set and the
original Goal 050 conditional-score detector, including its rank-990 C99 and
`p_BB <= 0.05` rule. A matched assumed-model baseline is evaluated under the
same frozen tables. No departure-specific calibration, detector tuning,
interpolation, nuisance
estimation or alternative-model fit is permitted.

The secondary diagnostic is

```text
p_plugin(y) = (1 + count{S*_(h_hat,b) <= S(y)}) / 1000,
D_plugin = [p_plugin <= 0.05].
```

Use the same training-grid h_hat, lowest-index tie rule, held-out conditional
prey score S and frozen candidate references as the primary rule. Every
reference history was already refitted in Goal 050. Selecting its reference
node from y does not inherit the fixed-node finite-sample rank guarantee.
Measure rejection on each of the three fresh matched baselines; those checks
do not establish uniform validity across all truths or changed nuisances.

The primary D remains `[p_BB <= 0.05]`. Do not reject on either detector or
change primary H or its nomination rule using the secondary. Because h_hat
belongs to C99, the plug-in rule at the same threshold includes every primary
rejection; a larger secondary rejection rate alone is not evidence of better
calibrated discrimination. Report both rates and paired changes from each
rule's own baseline, plus secondary `H_plugin = M AND NOT D_plugin`. Do not
recalibrate the secondary threshold after seeing baseline or alternative rates.
Even failure of both rules concerns these score-based tools, not all possible
model checks.

Define a materially misleading estimate before generation as

```text
M = [true h is excluded from the rank-950 effect set]
    OR [abs(log(h_hat / h)) >= log(1.5)]
```

and the key screen endpoint as

```text
H = M AND [p_BB > 0.05].
```

`H` is the frequency of materially misleading original-model inference that
the frozen detector does not flag. Detector non-rejection is not evidence that
the model is adequate. For every physical-null cell (including the background-loss
nulls), report the
stricter false-effect event `[1 excluded] AND [h_hat >= 1.5]` and its unflagged
counterpart. The 1.5-fold threshold is a proposed scientific relevance
threshold for Barry's review; it is not derived from Monte Carlo precision.

Report, by cell and as paired departure-minus-baseline changes:

- primary `H`, `M`, both components of M separately, and both detector
  rejection rates, alongside secondary `H_plugin`;
- mean signed log bias `b = mean(log(h_hat / h))` as a first-class endpoint,
  with its paired departure-minus-baseline interval (h=1 has a lower-grid
  boundary, so baseline bias need not be zero);
- truth inclusion, fitted `h` and absolute log error;
- effect-set width, cardinality, topology and boundary contact;
- C99 truth inclusion as a detector diagnostic;
- the false-effect endpoints at physical `h = 1`; and
- conditional held-out prey score, labelled as the detector statistic rather
  than a neutral predictive comparison.

Individual event rates receive conditional Wilson intervals. Use exactly 1,000
paired bootstrap draws, resampling complete replicate indices jointly across
all 17 cells, for departure-minus-baseline intervals. These intervals condition
on the frozen reference tables; they do not resample calibration uncertainty.
Spatial sites are not resampled. Because this is a screen, cell estimates and
prespecified contrasts
are reported without multiple-testing declarations or post hoc severity
selection. Preserve baseline M, H and each component, rather than judging
changes against a zero or nominal-rate baseline. Algebraically, under each
generator, `P(M) - P(H) = P(M AND D) <= P(D)`: H approximates M only if
rejection is rare under that generator. Goal 050 null rejection rates cannot
establish that premise for a new generator.

A low detector rejection rate under the matched baseline establishes only its
realised assumed-model behaviour. It does not establish power against either
departure. Conversely, high rejection under a departure does not show that an
alternative model can be identified or fitted reliably.

## Decision rule after the screen

The screen may nominate at most one departure class for an independent
confirmation block. Nomination is governed by primary `H`. Among cells with a
paired H increase
of at least 5 percentage points and a paired 95% bootstrap interval entirely
above zero, nominate the cell with the largest increase (break exact ties by
fixed cell ID order). Its departure class is the one nominated for independent
confirmation. A point increase of at least 5 points whose interval includes
zero is explicitly unresolved, not a null result. A value below 5 points means
it does not meet this relevance threshold, not evidence of equivalence.

Apply the same descriptive threshold/interval classification to `M` and show
`M AND D`: a large misleading-estimate increase that is usually caught is a
separate scientifically useful outcome, not an automatic nomination under H.
Prey heterogeneity, predator heterogeneity and background fields are separately
named classes; the primary H rule selects at most one. Preserve all cells and
the rule if no class qualifies; do not tune the detector, redraw fields, add
replicates or search unregistered severities.

This largest-cell rule is a nomination heuristic across a deliberately small
screen, not a multiplicity-controlled discovery claim. Its selected estimate
is subject to winner's bias; the independent confirmation below is therefore
required before the class can influence a Stage 2 scientific decision.

Nomination is not confirmation. Before any Stage 2 fitting campaign, freeze
the selected generator and severity and repeat that cell plus its matched
baseline on 1,000 new histories from disjoint roots. Require the independent
block to reproduce a paired increase in `H` of at least 5 percentage points
with its 95% paired interval above zero before using that nominated departure
to design a competing model. This confirmation is a separate future tranche and is not included in
the screen authority or cost below.

If no class qualifies, the result is that this bounded screen did not find a
large hidden-failure increase over its specified domains. It is not evidence
of general robustness. Barry would then decide whether ecological knowledge
supports a different severity, anti-aligned confounding, recolonisation
or time-varying impact before Arc 4 proceeds.

Even a confirmed screen result does not satisfy the Arc 4 exit gate. Stage 2
would require a separately registered campaign fitting the preferred model,
the selected scientifically interpretable alternative and a neutral predictive
comparator with equivalent information. Model selection and discrimination
claims would need independent histories beyond those used to choose the
alternative.

## Predictions to freeze before any screen histories

These are attributed scientific predictions from Fable (thread 53 message 471),
made operational here for review. They are not acceptance, tuning or additional
simulation gates. Keep each prediction, observed estimate and uncertainty even
when contradicted or unresolved. Treat a compound prediction component by
component; do not select a paper example in advance.

| ID | Proposed prediction and measurement |
| --- | --- |
| P1 | At every h, D10 has `abs(delta b) < 0.05` and primary `delta H < 0.02`. At h=3 and 5, D20 attenuates the geometric mean fitted effect relative to baseline by less than 15% (`0.85 < exp(delta b) < 1`); its truth-exclusion increase is under 0.03 at all three truths. |
| P2 | B100-A at h=1 has strict false-effect frequency above 0.20, primary detector rejection below 0.10, and primary `delta H > 0.10`. These are three distinct predictions: the first two do not imply the baseline-adjusted third. |
| P3 | At h=1, each r=0 background variant has a strict false-effect change whose paired 95% interval includes zero, and mean effect-set width greater than baseline. The first is a prediction of non-resolution, not equivalence; calibrated width is not a monotone information measure. |
| P4 | At h=3 and 5, PD10 has larger `abs(b)` than prey-only D20; its truth-exclusion increase is at least 0.03 at one of the three truths. Report paired bias contrasts as well as their absolute magnitudes. |

For each scalar inequality, show the point-predicate outcome and its paired or
rate interval. Call the prediction supported when its 95% interval lies wholly
in the predicted range, contradicted when wholly outside, and unresolved when
it overlaps a boundary. Apply this separately to each compound component. P3's
explicit zero-containing-interval forecast is recorded as met/unmet without
being relabelled equivalence. For P4, bootstrap the difference in absolute mean
signed log biases from the same paired draws; this is not mean absolute error.

Astra does not treat any of these directions or thresholds as established by
Goal 050. In particular, no theorem fixes the power of the primary detector,
the relative harm of the two detection mechanisms, the sign of background
bias, or the sampled mean hazard. Estimates and paired intervals determine
whether each prediction is supported, contradicted or unresolved. B100-A at
h=3 tests possible inflation of a real effect without adding an unsupported
quantitative forecast.

## Conservative compute cost

Goal 050 measured approximately 247 seconds per 1,000 one-truth histories with
eight scoring workers; this is slower than the 478.6 seconds measured for
6,000 original six-truth histories and is therefore the conservative basis.
Use a rounded-up rate of `0.248 s/history`. Scoring 17,000 histories gives
4,216 seconds; the 1.5 factor gives 6,324 seconds. The integration build measured
278 seconds. No calibration replay is needed. Extra cost for field generation
and the secondary diagnostic is not yet measured and must be included in the
complete-workload timing; the unused ceiling is not assumed throughput.

| Charge | Conservative seconds | Basis |
| --- | ---: | --- |
| Integration construction | 278 | measured Goal 050 |
| Production scoring | 6,324 | `17,000 * 0.248 * 1.5` |
| Preparation, generator controls and focused tests | 1,200 | explicit reserve |
| Source-bound full-cell timing and validation | 600 | explicit reserve before production |
| Synthesis, 1,000 paired bootstraps, figures and independent review | 1,800 | Goal 050 fixture projected 79 s and actual bootstrap took 35.67 s; reserve dominates |
| **Projected charged total** | **10,202 s (2.83 h)** |  |

Proposed hard ceiling: **14,400 elapsed seconds (4 h), eight workers, 32 GiB,
single-threaded numerical libraries**, on `deep-server-ts`. Run a source-bound
timing prefix covering all 17 cells before production and retain at least a
1.5 factor on measured scoring. If the complete projection plus reserves does
not fit the four-hour ceiling, stop with the costed limitation. Do not reduce
replication, omit cells, increase resources or borrow unused Goal 050 time
without a revised scientific decision.

## Decisions requested from Barry

The recommended package is coherent, but four choices are scientific rather
than implementation details:

1. **Detection mechanisms:** approve prey-only SD `{0.10, 0.20}` and
   predator-only SD `0.10`, with the other species fixed at `0.65`, at all three
   truths; retain the primary detector and add the plug-in secondary diagnostic.
2. **Background field:** approve nominal CV `{0.5, 1.0}`, exponential correlation
   length 10 grid cells, and exposure mixing `{0, 0.7}` with exact realised
   mean hazard `0.002/day`, plus B100-A at physical `h = 3`.
3. **Truths and relevance:** approve detection truths `{1, 3, 5}` and the
   1.5-fold point-error/false-effect threshold.
4. **Campaign size and gate:** approve all 17 cells with 1,000 histories each,
   the four-hour envelope, predictions above, and the 5-percentage-point primary
   H nomination rule with explicit unresolved/caught outcomes.

Recommendation: approve these choices as written unless their ecological
severity is implausible for the intended paper. After approval, register exact field construction, roots, reporting tables and
stopping rules before generating histories. Implement and qualify that frozen
design, then bind its final code identities and complete-workload timing before
production.
