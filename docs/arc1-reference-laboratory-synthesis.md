# Arc 1 Reference Laboratory Synthesis

- **Status:** Frozen reference case, pending Goal 037 acceptance
- **Paper role:** Charter Pillar 1 and planned Figure 2 evidence
- **Claim scope:** One synthetic landscape, sampling design, survey calendar,
  process family, and prespecified set of generating values

## Why Arc 1 existed

Arc 1 asked whether the separate scientific layers could be learned in a known-
truth system before they were combined into a broad sensitivity experiment.
The work established positive controls, located useful failure transitions, and
diagnosed whether failures arose from ecological signal, observation, or
uncertainty construction. It was not intended to estimate universal ecological
thresholds.

Additional reference-case experiments would now mostly move numerical
boundaries within this one design. The evidence is therefore frozen and the
next scientific question moves to variation across process and observation
conditions.

## Frozen reference design

The anchor experiment uses:

- a reproducible 72 by 84 cell landscape with 5,225 passable cells,
  impassable water, low-quality matrix, higher-quality patches, corridors, and
  three western invasion sources;
- a fixed access-constrained sample of 160 sites, split by spatial cluster into
  120 training and 40 holdout sites;
- survey days 10, 20, 30, 40, 50, and 60, with two visits per survey in the
  predator-observation experiments;
- stochastic first-passage predator spread with central spread rate `rho = 1`
  and resistance contrast `eta = 1`;
- homogeneous per-visit predator detection probability `p = 0.65` and zero
  false positives;
- an absorbing prey-extirpation process with daily background hazard `0.002`,
  equivalent to 11.3% counterfactual 60-day background extirpation risk, and a
  fivefold post-arrival hazard as the strong prey-effect anchor; and
- simulation-calibrated likelihood supports, independent calibration and
  validation histories, spatially held-out prediction, and a fitted
  full-support neutral comparator.

`Eta` is a model-scale exponent: zero removes habitat resistance, one applies
the reference edge costs, and larger values amplify their contrast. Its
ecological interpretation through induced edge-cost ratios must be completed
before its Arc 2 domain is frozen.

## Evidence and claim matrix

| Layer | Direct observation from the synthetic experiments | Defensible inference | Claim boundary |
| --- | --- | --- | --- |
| Spread rate | Locally calibrated support recovered `rho = 0.5`, `1`, and `2`; all validation supports were connected and interior. | The fixed landscape and survey window contain information about global wave speed across the tested range. | This is not yet a recovery surface or evidence across other landscapes. |
| Resistance | At `eta = 0.5`, 84/250 supports reached no resistance; at `eta = 0.75`, none did. | The practical discrimination transition lies between 0.5 and 0.75 in the reference experiment. | `Eta` is not yet expressed in an ecological edge-cost scale, and the bracket is design-specific. |
| Predator detection | With process fixed, `p = 0.65` was recovered with median error 0.01 and median width 0.06. In the central joint model, detection width was borderline but acceptable. | Repeated visits separate imperfect detection from occupancy when sufficient change occurs in the survey window. | Detection is homogeneous and false positives are absent. Slow waves retain wider detection intervals. |
| Prey effect | At 11.3% background risk, threefold was detected but slightly too broad; fourfold and fivefold passed strict recovery. | Strict reference-case recovery changes between threefold and fourfold, while reliable detection occurs by threefold. | These are hazard multipliers under known background hazard, not universal biological effect thresholds. |
| Background event information | A fivefold effect was detected but imprecise at 5% background risk and fully recovered at 11.3% and 20%; median observed events were 22, 47, and 74. | Low event yield can limit effect precision even when a nonzero signal is clear. | Changing background risk also changes absolute post-arrival hazard, censoring, and event yield; this is not a causal hazard comparison. |
| Prey observation and arrival | The fivefold effect remained recovered with known imperfect prey detection and when predator arrival was latent under the central spread model. | Explicit observation and arrival integration can preserve a strong prey signal without reconstructing a single event date first. | Detection parameters and the spread process were still constrained in these positive controls. |
| Joint spread and prey effect | Point estimates were centred near truth and held-out prediction beat neutral, but the simultaneous joint support reached grid boundaries and only 130/1000 regions excluded no prey effect. | One shared cutoff was dominated by between-wave variability and was too blunt for useful simultaneous inference. | Joint simultaneous recovery is unresolved; informative point estimates do not license a joint uncertainty claim. |
| Parameter-specific uncertainty | Separate central-case prey-effect profiles achieved 0.946 coverage, 994/1000 connected interior supports, 1000/1000 null exclusions, and median log width 0.693. | The prey effect remains marginally recoverable when spread rate is profiled out and uncertainty is calibrated for that parameter. | These are marginal 95% intervals, not a simultaneous 95% region for all parameters. |
| Prediction | Process models beat fitted full-support neutral comparators on held-out observations in the accepted predator and prey benchmarks. | The mechanistic structure contributes predictive information beyond time-only or nonspatial baselines in these cases. | Predictive advantage does not by itself establish parameter identifiability or model uniqueness. |

## Frozen uncertainty language

### Parameter-specific uncertainty

The defensible marginal statement is: a simulation-calibrated profile interval
for a named parameter achieved approximately nominal repeated-sampling coverage
under the stated generating truth and design. Other fitted parameters may be
profiled over. These intervals answer one-parameter questions and may be useful
even when a simultaneous region is broad.

### Simultaneous joint uncertainty

The defensible joint statement is: the tested shared-cutoff joint region was
calibrated for simultaneous coverage but was too broad to support useful joint
recovery of spread rate and prey effect. Arc 1 did not establish a precise
simultaneous region. It identified shared invasion-wave variability as the
leading reason the common cutoff was uninformative.

The Wilson bounds shown around empirical coverage quantify Monte Carlo
uncertainty in the estimated coverage frequency. They are not Bayesian
credible intervals and are not the parameter-support intervals themselves.

## Standard evaluation surface

Future experiments should reuse this compact set where applicable:

1. bias and absolute error of the point estimate;
2. support width, connectedness, and boundary contact;
3. empirical coverage with Monte Carlo uncertainty;
4. probability of excluding a scientifically relevant null;
5. held-out predictive advantage over a fitted neutral comparator; and
6. an explicit failure classification tied to signal, observation,
   calibration, model structure, or computation.

Continuous values are primary. Pass/fail gates are useful summaries, not the
scientific response surface.

## Operational brackets from the reference case

These brackets guide Arc 2 design; they are not universal thresholds:

- resistance discrimination: `eta = 0.5` to `0.75`;
- joint spread/detection precision: approximately `rho = 0.871` to `1.0` for
  the prespecified detection-width criterion;
- strict prey-effect recovery at 11.3% counterfactual 60-day background risk:
  threefold to fourfold; and
- fivefold prey-effect recovery across background risk: detected but not
  precise at 5%, fully recovered at 11.3% and 20%.

## What Arc 1 established

- Each major layer has a working known-truth positive control.
- Weak ecological signal can be distinguished from observation-limited
  precision and from over-broad uncertainty construction.
- Independent calibration/validation and held-out neutral prediction provide a
  credible common evaluation grammar.
- Negative outcomes can be attributed without repeatedly retuning the
  reference case.

## What Arc 1 did not establish

- generality across continuous combinations of process and observation values;
- generality across landscapes, access networks, or sampling allocations;
- recovery when background prey risk is also estimated;
- precise simultaneous uncertainty for the joint predator-prey model;
- robustness to false positives, heterogeneous detection, alternative process
  models, or misspecification; or
- relevance to any real mink, water vole, murid, cat, or fox population.

Those are later paper pillars. Arc 2 begins with the smallest useful extension:
a predator-only recoverability map on the frozen reference design.
