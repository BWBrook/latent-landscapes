# Goal 017: Weak-Contrast Decision-Target Reconciliation

## Scientific Question

Why can weak landscape-resistance contrast be detected reliably while a
calibrated 95% continuous support region often still includes uniform
resistance (`eta = 0`)?

This goal reconciles three different questions that earlier work sometimes
described collectively as "identifiability":

1. does the fitted grid value equal the generating `eta = 0.5` value;
2. can a size-controlled binary comparison distinguish `eta = 0.5` from
   `eta = 0`; and
3. does the calibrated joint support region exclude `eta = 0` while profiling
   the unknown spread rate `rho`?

These targets are related but not interchangeable.

## Evidence And Scope

Reuse, read-only:

- Goal 012's accepted production `validation_results.csv`,
  `truth_cell_summary.csv`, and `representative_profiles.csv`; and
- Goal 016's accepted repaired-production `funnel_performance.csv` and
  `summary.json`.

Restrict the primary comparison to Goal 012's three weak-contrast truths
(`eta = 0.5`) and full integration bank. Use the two half banks only as a
stability check.

Goal 012 supplies paired wave-level point-estimate and continuous-support
decisions. Goal 016 supplies a separate, independently generated campaign for
binary detection. Therefore binary performance may be compared at matched
truth-rho campaign level, but it must not be presented as a wave-level
cross-tabulation with Goal 012.

No new simulation is required or authorised.

## Required Analysis

For each weak-contrast truth rho and integration-bank variant, report:

- the fraction of validation histories whose MLE eta equals `0.5`;
- the fraction whose MLE eta is nonzero;
- the fraction whose calibrated support excludes `eta = 0`;
- the paired MLE-correct by support-exclusion cross-tabulation; and
- the corresponding Goal 016 binary-test power and false-positive rate for the
  accepted current composite statistic.

For each full-bank representative profile, reduce the joint surface to a
profile over eta and show:

- the fitted eta;
- the zero-contrast likelihood-ratio distance from the global maximum;
- the calibrated support cutoff and margin to that cutoff;
- the fixed `eta = 0.5` versus `eta = 0` profile-score difference; and
- the descriptive effect of fixing rho at its generating value rather than
  profiling it. This last quantity is explanatory only because a known-rho
  procedure would require its own calibration.

## Review Pack

Write one ignored artifact bundle containing exactly:

- `decision_target_summary.csv`;
- `paired_disagreement.csv`;
- `representative_profile_mechanics.csv`;
- `summary.json`;
- `review.md`;
- `visuals/decision_target_comparison.svg`; and
- `visuals/representative_profiles.svg`.

The review must use plain ecological language and distinguish observation
from inference. It must explicitly state the independent-campaign limitation.

## Decision Outcomes

Choose one primary diagnosis from the evidence:

- `contrast_information_absent` if binary detection is also weak;
- `point_estimation_limited` if binary detection is useful but the MLE rarely
  selects nonzero contrast;
- `continuous_support_conservative_relative_to_detection` if binary detection
  is useful and nonzero MLEs are common, but support exclusion is materially
  lower; or
- `decision_targets_broadly_concordant` if all three targets give similar
  answers.

Do not turn these labels into universal identifiability claims.

For this bounded diagnostic, binary contrast information is useful only when
Goal 016's prespecified `practically_useful` gate passes at all three rho
truths. Call point estimation limiting when the mean nonzero-MLE rate is below
0.80. Call continuous support materially more conservative when, at every rho,
both binary power and the nonzero-MLE rate exceed the support-exclusion rate by
at least 0.15. These are review conventions for this reconciliation, not
general inferential thresholds.

## Validation

- tests first for schema checks, wave-level cross-tabulation, profile
  reduction, campaign-level joining, and bundle writing;
- one focused test run observed failing before implementation and passing
  afterward;
- Ruff format and lint, strict MyPy, full tests, and package build once;
- one CLI run over the accepted production evidence; and
- one scientific inspection of the generated tables, memo, and figures.

## Boundaries And Stop Rule

- no new likelihood, classifier, sampling design, estimator, cutoff, or
  simulation;
- no claim that independent Goal 012 and Goal 016 waves are paired;
- no prey process, real data, legacy-repo access, or remote compute;
- at most one focused repair for a material defect; and
- stop once the existing evidence explains the apparent contradiction well
  enough to choose the next scientific question.

This goal authorises source, tests, CLI, this goal contract, and ignored local
review artifacts. It does not authorise commit, push, or publication.

Barry approved proceeding with Goal 017 on 8 August 2026.

## Outcome

The existing evidence supports
`continuous_support_conservative_relative_to_detection`.

Across the three full-bank Goal 012 weak-contrast truths:

- the MLE selected a nonzero eta in `97.6%`, `100.0%`, and `99.6%` of 500
  histories at rho `0.5`, `1`, and `2`;
- the MLE selected the exact generating eta `0.5` in `55.8%`, `67.0%`, and
  `74.0%`;
- the calibrated 95% support region excluded `eta = 0` in only `50.2%`,
  `69.0%`, and `65.8%`; and
- the independent Goal 016 binary comparison had power `86.8%`, `94.4%`, and
  `95.7%`, with false-positive rates `5.3%`, `2.6%`, and `4.5%`.

The full-bank versus half-bank rates differed by at most `0.024`, so the
distinction is not an integration-bank accident. The paired Goal 012 table
also shows directly that an exact point estimate does not guarantee exclusion
of zero: this occurred in 123, 62, and 104 histories across the three rho
truths.

The representative profiles clarify the mechanism without estimating its
frequency. Goal 012's empirically calibrated likelihood-ratio cutoffs are
large (`27.39` to `61.94` in these truth cells). Profiling rho markedly reduces
the zero-contrast likelihood-ratio distance in two of the three examples, and
two examples fit the adjacent eta `0.25` value rather than exact truth. These
features widen the continuous support question even though contrast remains
detectable.

The scientific resolution is therefore conceptual rather than architectural:
binary contrast detection, exact grid-point recovery, and continuous parameter
precision must be reported separately. The evidence does not currently justify
replacing the likelihood.

## Validation And Residuals

- test-first red and green states were observed for the Goal 017 analysis;
- the focused Goal 017 suite passed (`4` tests);
- Ruff formatting and lint passed;
- strict MyPy passed over `103` source files;
- the package build passed;
- the full suite passed (`224` tests; three inherited Goal 006 deprecation
  warnings); and
- the production-evidence CLI wrote the required seven-file ignored review
  pack, whose tables, memo, and two rendered SVG figures were inspected once.

Goal 012 and Goal 016 used independent waves. The campaign-level comparison is
scientifically informative, but it is not a paired per-wave comparison. The
three reduced likelihood profiles are representative block-zero examples and
must not be interpreted as a frequency sample. No new simulation, estimator,
cutoff, likelihood, sampling design, remote compute, commit, or push occurred.

Barry accepted Goal 017 and authorised publication on 8 August 2026.
