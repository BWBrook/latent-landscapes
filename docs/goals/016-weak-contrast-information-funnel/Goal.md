# Goal 016: Weak-Contrast Information Funnel

## Scientific Question

Where does information distinguishing uniform passable-edge resistance
(`eta = 0`) from weak landscape-resistance contrast (`eta = 0.5`) cease to be
useful: in the stochastic process, spatial sampling, temporal/detection
observation, or the current sitewise inferential statistic?

This is a test of single-history practical separability on the accepted fixed
landscape. It is not a claim of structural identifiability or a new final
inference method.

## Motivation

Goals 009 and 012 showed that calibrated 95% support regions often retained
the physical `eta = 0` boundary when truth was `eta = 0.5`. They did not show
that the fitted mode usually selected the wrong grid value. External
reconnaissance further suggests that independent weak-contrast waves remain
strongly distinguishable after global speed is removed and after the accepted
observation process is applied. That reconnaissance is an evidence lead, not
accepted project evidence.

Goal 016 will confirm the lead and compare two statistics on the same sealed
waves and detection histories:

1. a regularised linear discriminator that can combine the whole spatial
   pattern; and
2. the accepted site-history composite statistic, profiled over `rho`, which
   uses correct site marginals but omits dependence induced by a shared wave.

## Frozen Scientific Inputs

Retain unchanged:

- the accepted 72 by 84 landscape, water mask, sources, passable graph, and
  160-site clustered design;
- the geometric-mean-preserving edge-cost transform and exponential edge
  shocks;
- `eta = {0, 0.5}` and truth `rho = {0.5, 1, 2}`;
- survey times `10, 20, 30, 40, 50, 60`;
- two visits, known homogeneous detection `p = 0.65`, and zero false
  positives;
- the accepted 601-point candidate `rho` grid for the current statistic; and
- one 4,096-wave integration bank, independent of classifier development and
  final evaluation waves.

No landscape, generator, site, calendar, detection, or likelihood retuning is
permitted.

## Independent Unit And Partitions

One independently generated edge-shock field and all representations derived
from it form one independent wave. Cells, sites, times, visits, and exact-rho
rescalings are features or descendants, not replicates.

Freeze disjoint process roots for:

- classifier training: 1,000 waves per eta class;
- model selection: 250 waves per eta class;
- null-threshold calibration: 1,000 additional `eta = 0` waves; and
- final evaluation: 1,000 waves per eta class.

The same wave never crosses partitions. Every final scientific interval uses
waves as the independent units. A reduced smoke configuration may use smaller
counts but is explicitly non-scientific.

## Information Funnel

Carry the same waves through these prespecified representations:

1. `global_time_only`: median positive log arrival, measuring overall timing;
2. `full_map_centered_log`: complete positive-cell log arrival after subtracting
   its wave median, exactly invariant to `rho`;
3. `full_map_ranks`: complete arrival ordering, also invariant to `rho`;
4. `sample_sites_centered_log`: median-centred exact arrival times at the 160
   accepted sites;
5. `sample_sites_perfect_occupancy`: six-time occupancy at the accepted sites;
6. `sample_sites_imperfect_detection`: two-visit detection counts at the same
   site-times; and
7. `current_composite_statistic`: the profiled difference between the accepted
   sitewise criterion at `eta = 0.5` and `eta = 0`, evaluated on the exact same
   imperfect-detection histories as rung 6.

The classifier for the observed rungs is trained on an equal mixture of the
three frozen rho values without receiving rho as a feature. All descendants of
one base wave remain in the same partition.

## Primary Methods And Decisions

Use one standardised ridge linear classifier with a small frozen penalty grid.
Select the penalty on the model-selection partition only. Do not add a
nonlinear model unless the completed goal is explicitly reopened after human
review.

For the imperfect-detection classifier and current composite statistic:

1. calculate a separate 95th-percentile null score at each rho using the
   null-calibration waves;
2. use the maximum of those three thresholds as the common conservative
   decision threshold;
3. report empirical false-positive rate under `eta = 0` and power under
   `eta = 0.5` at each rho on sealed final waves; and
4. compare both statistics on identical final waves.

The primary interpretation is:

| Result | Interpretation |
| --- | --- |
| Centred complete maps weak | intrinsic practical overlap at weak contrast |
| Complete maps strong; 160-site exact arrivals weak | spatial sampling loss |
| Exact sites strong; perfect or imperfect histories weak | temporal/detection loss |
| Imperfect-history classifier strong; current statistic weak | inferential-statistic inefficiency |
| Both imperfect-history statistics strong but support often touches zero | stringent continuous support target/calibration, not absent class information |

For a claim of practically useful weak-contrast evidence, the lower 95% Wilson
limit on power must exceed 0.80 while the common-threshold false-positive rate
does not exceed 0.06 at any rho. This is a decision convention for this
controlled diagnostic, not a universal ecological threshold.

## Compact Review Pack

Write one ignored artifact bundle containing:

- configuration and frozen seed/partition summary;
- `funnel_performance.csv`;
- `final_wave_scores.csv` for the imperfect-history classifier and current
  statistic;
- `method_comparison.csv`;
- `summary.json` and `review.md`;
- an information-funnel figure;
- same-data score-distribution comparison; and
- one spatial coefficient figure for ecological interpretation.

Do not reproduce old ledgers, source bundles, historical artifact schemas, or
full likelihood surfaces. Retain only what is needed to review and reproduce
the Goal 016 decision.

## Validation

- tests first for partition isolation, rho-invariant representations,
  whole-wave metric accounting, conservative thresholding, and a deterministic
  reduced smoke;
- Ruff formatting and lint;
- strict MyPy over source and tests;
- focused Goal 016 tests;
- full test suite and package build once;
- one reduced local CLI smoke; and
- one frozen production run on `deep-server` if the smoke and review gates
  pass.

## Boundaries

- no new sampling design;
- no generator or parameterisation change;
- no continuous posterior, parameterised ratio estimator, pairwise likelihood,
  block likelihood, particle method, or nonlinear classifier;
- no prey dynamics or real data;
- no reinterpretation of accepted Goal 009-013 results; and
- no commit, push, or publication without later explicit authority.

## Stop Rule

Stop after one complete information-funnel campaign and at most one focused
repair pass for a material defect. Do not begin improving the inferential
method inside Goal 016. Report the located bottleneck, residual uncertainty,
and the smallest scientifically justified follow-up.

Barry authorised Goal 016 implementation on 7 August 2026.

## Outcome

The frozen production campaign completed successfully on `deep-server` using
1,000 independent final waves per eta class at each retained rho. The accepted
outcome is `information_retained_support_target_limited`.

- Complete centred maps and arrival ranks separated `eta = 0` from `eta = 0.5`
  essentially perfectly (final AUC `1.000` for both; rank-based power `1.000`).
- Restriction to the accepted 160 sites did not erase the pattern. Perfect
  occupancy retained power `0.912`, `0.987`, and `0.987` across rho truths
  `0.5`, `1`, and `2`.
- Imperfect two-visit detection reduced information but still retained strong
  discrimination: classifier AUC was `0.973` to `0.994`, with power `0.840` to
  `0.954`.
- Most importantly, the existing profiled sitewise composite statistic was
  itself practically useful at all three rho truths: AUC `0.966` to `0.992`,
  power `0.868` to `0.957`, and false-positive rates `0.026` to `0.053`.

Thus weak resistance contrast is strongly encoded in the stochastic wave,
survives the fixed sampling and imperfect-detection process, and remains
detectable by the current statistic. The earlier difficulty excluding
`eta = 0` from a calibrated 95% continuous support region is not evidence of
intrinsic overlap or absent class information. It is a difference between
inferential targets: binary contrast detection, point estimation, and a
profiled continuous uncertainty region are not interchangeable questions.

The first production serialization incorrectly reported
`intrinsic_weak_contrast_overlap` because outcome precedence allowed a
full-map false-positive rate of `0.061` to fail a `0.060` finite-sample gate
before considering successful downstream rungs. The decision logic was
repaired to diagnose from the deepest useful rung. The repaired campaign used
the same frozen inputs and seeds; all numerical CSVs were byte-identical and
all rendered figures pixel-identical to the first run. Only the diagnosis and
review text changed.

## Validation And Residuals

- Ruff, strict MyPy, package build, focused Goal 016 checks, and all 220 tests
  passed after the single repair pass.
- Both remote campaigns exited zero; the repaired production run completed in
  18 minutes 27 seconds with peak resident memory below 0.9 GB.
- The wave classifier narrowly missed the prespecified false-positive gate at
  `rho = 2` (`0.068`), so it is not claimed useful at every rho. This does not
  overturn the conclusion because the current statistic passed at every rho.
- Binary discrimination does not by itself establish precise continuous
  estimation of eta or rho. That unresolved distinction is the next
  scientific decision boundary.
- No new likelihood, sampling design, nonlinear classifier, prey process, or
  real-data analysis was started. No commit or push was performed.
