# Arc 4 reusable figure captions

## Figure 1. Detectability, hidden failure and adjustment error change

**(A)** Goal 051 h=1 endpoint rates for three conditions in the same 1,000-block
experiment: the matched assumed-model baseline (`B_h1`), prey-detection
heterogeneity (`D20_h1`), and the aligned residual-background departure
(`B100-A_h1`). The three subpanels show primary adequacy-detector rejection
(`p_BB <= 0.05`), primary hidden failure `H`, and the strict false-effect
endpoint. Here `M` is truth exclusion from the registered effect set or
`abs(log(h_hat / h)) >= log(1.5)`, primary hidden failure is `M AND NOT D_BB`,
and a strict false effect at physical `h=1` is `[truth excluded] AND
[h_hat >= 1.5]`. Points are unconditional rates over complete histories;
whiskers are the archived conditional Wilson 95% intervals. These are Goal
051 screen endpoints and remain separate from the later Goal 054 decision
experiment.

**(B)** Goal 053's adjusted-minus-constant change in mean absolute log-h error,
`mean(abs(log(h_hat / h)))`, for exact constant background (`E0`), exact
nonconstant log-linear background (`E06`), and the aligned residual-background
departure (`B100-A`) at `h=1` and `h=3`. Negative values favour the adjusted
estimator. Whiskers are the registered paired whole-block percentile 95%
intervals from the existing 2,000 draws (seed `2026092703`) over the 1,000
evaluation histories. This panel is a Goal 053 estimation summary, not a
decision-rule calibration or a claim of accurate ecological magnitude.

The two panels use different archive experiments, each with 1,000 histories
per condition; no rates or intervals are pooled. All plotted rows are copied into
`artifacts/goal055_execution/report/arc4_figure_source_data.csv`, with source
row keys and input hashes recorded in `arc4_figures_manifest.json`.

## Figure 2. Calibrated declaration versus magnitude error

**(A)** Goal 054 declaration rates for the frozen adjusted full-supremum rule
and the frozen constant-`beta=0` calibrated comparator across the four
evaluation backgrounds (`E0`, `E06`, `B100-A`, `N100-A`) at the physical null
(`h=1`) and a threefold effect (`h=3`). Each point is an unconditional rate
over 1,000 complete evaluation histories. The dashed line in the null panel
marks 5%. Whiskers are archived calibration-aware percentile 95% intervals
from the existing 2,000 paired reference/evaluation bootstrap draws (seed
`2026092905`); they include variation in the frozen reference table and
evaluation blocks. `B100-A` and `N100-A` are out-of-family stress cells, so
their null rates do not carry the exact-model nominal-size guarantee.

**(B)** Unconditional probability of at least a 1.5-fold point error,
`abs(log(h_hat / h)) >= log(1.5)`, for the matching adjusted or constant
estimator in the same eight cells. Each denominator is all 1,000 histories;
the plot does not condition on declaration and does not combine one rule with
the other estimator. Whiskers are the archived calibration-aware percentile
95% intervals from Goal 054's 2,000 draws. A calibrated binary declaration
under a specified null does not make the fitted `h` an accurate magnitude;
these lower panels are descriptive magnitude-error probabilities under the
fixed synthetic landscape, survey, grid and integration bank.

The adjusted and constant colours identify the estimator/rule pairing only in
this figure. All plotted rows are copied into
`artifacts/goal055_execution/report/arc4_figure_source_data.csv`, with source
row keys and input hashes recorded in `arc4_figures_manifest.json`.

## Figure 3. Sensitivity to the supplied mean and persistent detection variation

Goal 055 retrospective archive checks under the **unchanged Goal 054 rules**.
The upper panels show false declarations at h=1; the lower panels show h3
declarations. Blue denotes the full-supremum adjusted rule and orange its
constant-beta0 comparator. Each point uses all 1,000 complete histories in
its condition, with pointwise calibration-aware 95% percentile intervals from
the single registered 2,000-draw bootstrap, seed 2026100105. The h1 dashed line
marks 5%. Higher h3 rates under a departure do not establish improved
size-controlled power when null protection is lost.

Left and middle columns reuse the same Goal 054 E0 and E06 observations at
supplied/true map-mean ratios .80, 1.00 and 1.25. True mean hazard is .002/day;
only the supplied value changes. E0/E06 have generating beta0/.60. The ratio 1
point estimates reuse verified Goal 054 fits; their intervals use Goal 055's
bootstrap stream and do not replace the original Goal 054 intervals. Right
panels use the separate Goal 051 archive's B baseline and D20 histories;
D20 has site-level prey-detection mean .65 and SD .20, with that site effect
fixed across visits. The fitted observation model remains p=.65.

Bootstrap indices pair conditions and comparators within each archive, while
Goal 051, Goal 054 evaluation and Goal 054 reference resamples are independent.
Lines connect the prespecified discrete conditions; they do not imply tested
interpolation, a continuum of supplied means, or an ordering of untested
observation models. The archive checks remain distinct from the original
Goal 051 screen and Goal 054 experiment. D20's prior selection precludes an
independent-confirmation interpretation.

All 32 plotted source rows are copied exactly from
`artifacts/goal055_execution/synthesis/output/rule_rates.csv` into
`artifacts/goal055_execution/report/nuisance_figure_source_data.csv`.
The source table, PNG, PDF and rendered-PDF preview identities, together with
visual checks, are recorded in
`artifacts/goal055_execution/nuisance-figure-verification.json`.
