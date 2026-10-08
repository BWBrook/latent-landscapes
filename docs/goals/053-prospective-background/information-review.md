# Goal 053 information-bound review

27 September 2026. **Retain the day-0 Fisher calculation as an advisory
complete-data benchmark; do not treat it as a finite-sample bound or a diagnosis
of the observed-data ridge.**

## Scientific target and scope

Goal 053 estimates the across-history performance of constant-background and
fitted A-adjusted analyses in fresh synthetic histories. Its principal targets
are log-h estimation error and direct held-out conditional-prey prediction,
conditional on one landscape, survey design, known nuisances and analysis bank.
The information calculation addresses a narrower object: local information for
`(eta=log(h), beta)` if the analyst observes every continuous prey-loss time
through day 60 and is given each true predator-arrival time. It conditions on
the six archived Goal 052 arrival geometries and uses only the 120 training
sites. It is therefore more informative than both the actual latent-arrival fit
and Goal 052's oracle-arrival fit, which still sees six imperfect-detection
surveys rather than exact loss times.

The loss process at site i has hazard `lambda_i(beta)` before arrival `tau_i`
and `h*lambda_i(beta)` afterwards, where

`lambda_i(beta) = mu*exp(beta*A_i)/mean_map(exp(beta*A))`.

Writing `a_i = d log(lambda_i)/d beta = A_i - weighted_mean_map(A)` and
letting `Epre_i` and `Epost_i` be the probabilities of an observed loss before
and after arrival by day 60, the conditional counting-process information is

```
I_eta,eta  = sum(Epost_i)
I_eta,beta = sum(Epost_i*a_i)
I_beta,beta= sum((Epre_i+Epost_i)*a_i^2).
```

The known-beta standard error is `1/sqrt(I_eta,eta)`. The free-beta standard
error uses the Schur complement
`1/sqrt(I_eta,eta - I_eta,beta^2/I_beta,beta)`. These formulae and the whole-map
normalization derivative are correct.

## Independent numerical reproduction

The [reproduction script](../../../artifacts/goal053_execution/information-review/reproduce_information_bound.py)
does not import or execute Fable's script. It derives the matrix above from the
frozen Goal 052 arrays and checks it against the finite-difference Hessian of an
independently quadrature-integrated expected complete-data log likelihood. The
maximum absolute matrix difference over all 24 block/case checks is
`1.80e-6`. The four Goal 052 cells share arrival times exactly within block
(maximum difference zero), so using the `B_h3` row to represent each shared
arrival block is valid. The evidence SHA256 is
`d923a768ae60f542ac1f001da1cc7477d30861f30eb23d5e5bcd70e0421027b5`.
Fable's read-only source has SHA256
`89033435a4a61310c6d3779040b6cb24e034d885aca0f25755e40cf887b8b550`.

Means across the six conditional arrival blocks reproduce Fable's values:

| beta | h | Expected pre losses | Expected post losses | SE log h, beta known | SE log h, beta free | Free/known SE | Asymptotic corr(log h, beta) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.00 | 1 | 7.139 | 6.431 | 0.395 | 0.473 | 1.199 | -0.550 |
| 0.00 | 3 | 7.139 | 17.868 | 0.237 | 0.299 | 1.261 | -0.607 |
| 0.60 | 1 | 5.506 | 8.386 | 0.345 | 0.362 | 1.048 | -0.297 |
| 0.60 | 3 | 5.506 | 21.808 | 0.214 | 0.225 | 1.048 | -0.297 |

The exact unrounded values and all per-block matrices are in
[results.json](../../../artifacts/goal053_execution/information-review/results.json).
The six empirical baseline-h3 adjusted/known-beta LR<=2 log-width ratios also
reproduce as 1.989, 1.311, 1.201, 1.553, 1.304 and 1.300. These are realised,
finite-grid, uncalibrated widths; their resemblance to the beta0 Fisher ratio is
descriptive rather than a coverage or RMSE validation.

## What the calculation supports

The ideal data contain few expected losses: about 5.5-7.1 before arrival and
6.4-21.8 afterwards among 120 sites. The information matrices are nonsingular,
and the local nuisance penalty at h=3 is modest in this idealized model: 1.261
at beta0 and 1.048 at beta.60. This supports event scarcity plus a negative
h-beta trade-off as plausible mechanisms. It does not show that the broad
observed-data geometry is *mostly* event-limited. Survey coarsening, imperfect
detection, latent arrivals, the h boundary, finite-grid behavior and, for
B100-A, omitted G remain entangled. Full-rank local complete-data information
also does not prove global or observed-data identifiability.

The [conditional finite-sample experiment](../../../artifacts/goal053_execution/information-review/simulate_complete_data_boundary.py)
simulated 1,000 exact loss-time histories for each of the six archived arrival
blocks at each exact truth (6,000 per case; audit-only seed 2026092799). At h=3, free/known
log-h RMSE ratios were 1.275 at beta0 and 1.041 at beta.60, close to the Fisher
ratios. This makes Fable's 1.25 and 1.05 predictions reasonable mechanism-based
forecasts for ideal complete data, but does not convert the 1.60 and 1.30
advisory thresholds into mathematical upper bounds for the production estimator.

At h=1 the regular Fisher approximation is especially limited because eta=0 is
the lower boundary. Constrained complete-data fits had free-beta mean h of
1.297 versus 1.160 with beta known at beta0, and 1.181 versus 1.138 at beta.60.
The frequency of h>=1.5 was 0.216 versus 0.110 at beta0 and 0.121 versus 0.082
at beta.60. Among free-beta fits with h>1, beta fell below its truth in 68.9%
and 58.1% of histories, respectively. Thus upward h bias and negatively shifted
beta under the null can arise from the boundary plus the trade-off even under
the exact model. The complete results are in
[finite_sample_results.json](../../../artifacts/goal053_execution/information-review/finite_sample_results.json).
They are a mechanism check conditional on six arrival maps, not a test of the
registered latent-survey predictions.

This auxiliary calculation generated only exponential prey-loss thresholds
conditional on the already examined Goal 052 arrival arrays. It generated no
new predator-spread process, field, survey observation or registered Goal 053
history; it did not invoke the Goal 053 generator, latent-arrival scorer or
production roots, and it accessed no Goal 053 outcome. Its outputs belong only
to this information audit.

## Rejected extension and remaining limits

Ignore the source script's `D=60` and `D=120` pre-release augmentation rows.
With `fixed_riskset=True`, it adds expected pre-release losses while retaining
all sites at risk at release. A single unreplaced cohort cannot both lose sites
before release and retain the full release-day risk set. The alternative
unconditional cohort would attenuate post-release information by pre-release
survival; replacing lost sites would introduce additional sampling units.
Either design requires an explicit observation and selection model. This flaw
does not affect any reported `D=0` result, and no survey augmentation is in
Goal 053.

Fisher information is a local expected curvature and the Cramer-Rao result
requires regularity and unbiasedness. It is not a finite-sample RMSE guarantee,
does not propagate latent-arrival or detection uncertainty, and is nonregular at
h=1. Averaging six block-specific standard errors describes the six conditional
geometries; it is not the standard error of a pooled six-block estimator. The
registered sharper predictions should therefore remain secondary predictions,
with the direct predictive-score direction treated as an empirical model
forecast unrelated to this Fisher derivation.

**Recommendation:** keep the registered wording that complete event-time
information informs expectations but does not establish observed-data ratios,
finite-sample bias or structural identifiability. Describe event limitation and
the h-beta boundary interaction as supported mechanism hypotheses. Do not use
this calculation to alter the six-cell design, set success criteria, justify
pre-release monitoring or advance calibration. Independent scientific review of
the completed production result remains material because only that result can
show how these mechanisms survive the actual observation and fitting pipeline.
