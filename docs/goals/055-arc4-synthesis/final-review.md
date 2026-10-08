# Goal 055 independent final result and claim review

2 October 2026 (Hobart). Charter Pillar 4 synthesis and Pillar 5 design
preparation.

## Decision

**The two registered archive checks are scientifically and mechanically
complete. Their result is a clear failure of the frozen procedure under both
named departures, and the capstone remains NO-GO pending the registered
observation and nuisance-model prerequisites.** The supplied-mean result selects
the pre-invasion-information branch; the prey-detection result independently
requires an observation-model or survey repair. These are design decisions for
future qualification, not evidence that either proposed repair works.

The integrated record now preserves both required repairs. Goal 055 holdout
differences are explicitly labelled as totals over 40 holdout sites, with both
estimates and interval endpoints divided by 40 whenever reported as nats per
site. The capstone generator defines one mutually exclusive background state
`L` with probabilities `E0=1/4`, `E06=1/4` and `B100-A=1/2`, gives the exact
three weight formulae and whole-map normalization, and draws no separate beta
in the `B100-A` state. This resolves the data-generating-process ambiguity.

## Scientific target and scope of inference

The target is the operating behaviour of the frozen Goal 054 effect-declaration
procedure when the analyst receives a wrong whole-map mean background hazard or
fits homogeneous prey detection to histories generated with persistent
site-level heterogeneity. At physical `h=1`, the estimand is the marginal
probability of a false effect declaration over complete generated histories in
each named archive condition. At `h=3`, it is a condition-specific declaration
probability under departure; it is not clean power because misspecification can
itself create the apparent effect. Point error and held-out score are separate
estimands.

One complete 160-site history is the experimental and resampling unit. The
sites, survey occasions, paired visits, latent spread and prey losses are
dependent components of that unit. Goal 054 wrong-mean and correct-mean columns
reuse identical histories and are paired. Goal 051 D20 and B columns share the
registered replicate streams and are paired within that archive. The two
archives are independent panels and were resampled independently. Inference is
conditional on one landscape and site split, the fixed finite parameter grids,
known spread and other retained nuisances, the K131072/alpha1 bank, and the two
specified misspecifications.

## Evidence and independent reconstruction

Production remained bound to source manifest
`df80a971211e786eb7de811561ead5937abb0fa4b14e15bc72fedf6a81324ad5`.
The completed run scored all 1,000 blocks by 12 new columns and 81 beta rows.
Its controls replayed 4,000 Goal 051 histories with every opaque identity,
training profile, held-out profile and fitted index exact; an eight-block
Goal 054 full-rectangle control reproduced all ten reduced statistics exactly.
The independent production crosscheck then reconstructed those ten statistics
from all saved score rectangles with zero maximum error
([production crosscheck](../../../artifacts/goal055_execution/production-crosscheck.json)).

The production statistics SHA256 is
`4ef41f90559053de69f84450f06189a6c6dcff65f87bc5ae3559a9ab5c48d15b`;
the frozen Goal 054 table is
`33c94ad6d7bb58701c68b611c70400c0228787e1782026c7df7d9b747aa40900`.
The independent synthesis audit regenerated the three seeded bootstrap streams,
all 2,000 frozen and calibration-aware primary/constant rate draws, and all
544,000 metric-draw values exactly. It also verified every reported point
metric, paired contrast, percentile interval, forecast and branch flag
([synthesis crosscheck](../../../artifacts/goal055_execution/synthesis-crosscheck.json)).

I separately reconstructed the complete saved point-decision cube without
calling either synthesis implementation. Inclusive plus-one tails and the
`1e-12` tolerance reproduced all 16,000 primary, 16,000 constant and 16,000
Berger--Boos decisions; direct nuisance-tail membership reproduced all
1,296,000 candidate indicators. The four fixed-cutoff rules were evaluated
directly. Across seven rules and 16,000 condition-history cells there were
zero mismatches in 112,000 decisions. The respective total declaration counts
were 7,097, 8,271, 6,802, 7,675, 6,846, 8,487 and 7,774 in the saved rule order.
This confirms the secondary diagnostics without expanding the registered
bootstrap or selecting among them.

The exhaustive finite grids avoid MCMC mixing and optimiser-convergence
failure. They do not remove h--beta--background trade-offs, coarse-grid
dependence, boundary estimates or weak information. Fitted-beta boundary rates
were at most 3.1%, but h=1 is itself the lower effect-grid boundary; apparent
reductions in h=1 point error when a high background mean is supplied partly
reflect more estimates being pinned at that boundary.

## Decisive results

The calibration-aware intervals below are the registered sensitivity summaries
that resample both whole evaluation histories and the frozen reference table.
They are pointwise bootstrap intervals, not simultaneous bounds or new
misspecification-valid coverage guarantees.

| Condition | Primary null declaration | Paired change from control | Primary h3 declaration | Paired change from control |
| --- | ---: | ---: | ---: | ---: |
| supplied mean 0.0016, E0 | 0.078 [0.053, 0.095] | +0.036 [0.024, 0.049] | 0.887 [0.841, 0.904] | +0.126 [0.104, 0.148] |
| correct mean 0.002, E0 | 0.042 [0.021, 0.054] | reference | 0.761 [0.706, 0.788] | reference |
| supplied mean 0.0016, E06 | 0.108 [0.071, 0.128] | +0.076 [0.045, 0.092] | 0.974 [0.959, 0.983] | +0.044 [0.033, 0.072] |
| correct mean 0.002, E06 | 0.032 [0.020, 0.044] | reference | 0.930 [0.892, 0.944] | reference |
| supplied mean 0.0025, E0 | 0.015 [0.007, 0.023] | -0.027 [-0.036, -0.011] | 0.548 [0.465, 0.579] | -0.213 [-0.255, -0.193] |
| supplied mean 0.0025, E06 | 0.012 [0.005, 0.019] | -0.020 [-0.030, -0.011] | 0.781 [0.737, 0.810] | -0.149 [-0.174, -0.125] |
| Goal 051 D20 | 0.198 [0.152, 0.221] | +0.160 [0.121, 0.178] from B | 0.921 [0.892, 0.937] | +0.149 [0.126, 0.186] from B |
| Goal 051 B | 0.038 [0.022, 0.051] | reference | 0.772 [0.717, 0.802] | reference |

Both 0.0016/day physical-null intervals lie wholly above 0.05, so the
preregistered wrong-level failure predicate is triggered. The paired directions
show the mechanism clearly: understating background loss shifts declarations
and fitted h upward; overstating it shifts both downward. Fitted beta changes
with the supplied mean but does not absorb the error. This is direct evidence
of a nuisance/effect trade-off in the fitted workflow and defeats a fixed rough
plug-in mean as the capstone design. The branch rule was prespecified but its
four cell intervals are pointwise. As an unregistered multiplicity sensitivity
check, even the 0.625th percentile lower bound for the 0.0016/E06 null rate is
0.065, still above 0.05; the decision therefore does not depend on the marginal
0.053 lower bound in E0. At h=3, both wrong means worsen adjusted mean absolute log
error relative to the correct-mean fit: increases range from 0.068 to 0.094 log
units across the four comparisons, despite the opposite declaration shifts.

Both prey-detection predicates also trigger. D20's physical-null declaration
rate has lower limit 0.152, and its paired increase from B has lower limit
0.121. D20 simultaneously raises adjusted mean signed log error at the null
from 0.313 to 0.631 and the at-least-1.5-fold point-error rate from 0.308 to
0.648. The observation departure therefore creates a false-effect problem as
well as an adequacy discrepancy. The increase in the h3 declaration rate
cannot be presented as an unqualified sensitivity benefit: mean signed log
error also rises from 0.013 to 0.234 and the large-error rate from 0.312 to
0.359.

The constant-rule forecast for 0.0016/E0/h1 was pointwise correct at 0.088, but
its interval [0.065, 0.112] did not support the narrow 0.08--0.10 range. The D20
primary forecast was supported at 0.198 [0.152, 0.221], wholly above 0.12. That
is a preregistered cross-rule projection on a retrospectively selected archived
departure, not an independent validation sample.

Held-out prediction does not overturn either failure. The saved
adjusted-minus-constant values are total 40-site log-score differences. After
division by 40, the D20 values are -0.00354 nats/site at h=1 and -0.00233 at
h=3, both favouring constant on average. Across the wrong-mean conditions the
direct differences range from about -0.0055 to +0.0101 nats/site and change
sign with truth and supplied mean. Paired changes from the matching controls
are at most 0.0030 nats/site in absolute value. These are small,
within-landscape predictive contrasts; a score sign is not a calibrated model
test and does not certify the effect magnitude.

## Failure modes and inferential limits

- The supplied whole-map mean, spatial coefficient and effect multiplier trade
  off in the likelihood. Goal 055 diagnoses that confounding but does not
  identify or estimate an unknown background mean.
- Persistent prey-detection heterogeneity is omitted from the fitted model.
  The D20 result shows substantial bias and false declarations; it does not
  estimate the detection distribution or show that Beta mixing will be
  identifiable from two visits.
- D20 was selected after Goal 051 found harm. Its Goal 055 analysis is a useful
  frozen-rule transfer check, but it cannot confirm the original nomination or
  estimate general observation-model risk.
- Whole histories were resampled, preserving spatial, temporal and visit
  dependence. One fixed landscape and split remain the scale of inference;
  the analysis supplies no landscape-general or site-iid guarantee.
- All visits are complete in these synthetic archives. The result says nothing
  about informative missingness, effort variation, site selection after prey
  loss, censoring beyond the specified interval observation, or field-data
  leakage.
- The calibration-aware bootstrap measures archive and reference-table
  sensitivity under the registered coupling. It does not calibrate the frozen
  rule under either departure, propagate uncertainty from an external
  background study, or protect a family of reported secondary comparisons.
- Magnitude summaries are unconditional log-ratio errors. They are not
  confidence coverage, and declaration is not magnitude recovery. Holdout
  differences are conditional predictive scores, not causal effects of model
  structure.

## Capstone recommendation and residual risk

The registered result selects the pre-invasion-information candidate and makes
heterogeneous-detection modelling or a defensible survey alternative a
prerequisite. Before any truth draw, the smallest defensible next tranche is
the proposed observed-data nuisance-and-calendar feasibility study. It must
freeze the exact generator formula, likelihood, parameter bounds, grids or
priors, Beta-mixing integration and random streams; recover known parameters
on synthetic fixtures; probe h/background/beta/detection-dispersion trade-offs,
zero-dispersion and effect boundaries, flat or multimodal profiles and weak
event histories; and qualify prediction under the eight-cluster holdout design.
A separate prospectively registered calibration is then required for any
effect declaration or coverage claim.

The blinding sequence is otherwise defensible: public map and sampling streams
are separate from private truth streams; Fable remains outside Astra's
workspace; training code, inputs, candidate set and predictive distributions
are locked before holdout release; no refit follows holdout; and truth follows
the complete prereveal report hash. One sealed history remains a diagnostic
case study, not a discrimination, calibration or coverage experiment.

Goal 055 is **GO for closing the registered Arc 4 synthesis and for reviewing
the named feasibility study as a future tranche**. It remains **NO-GO for
capstone truth draw, observation generation, calibration transfer or sealed
launch**. This independent review materially changed confidence by extending
the point-decision reconstruction to all seven rules and locating the holdout
unit and generator-definition issues. The integrated prose and protocol now
repair both issues, so another independent review is unlikely to change the
Goal 055 decision. Independent scientific review remains material before
authorizing the new feasibility design, calibration or capstone launch.
