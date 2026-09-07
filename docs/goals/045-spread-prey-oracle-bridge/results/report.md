# The cost of estimating predator spread speed

Automated synthesis classification: **bridge_complete**. Six cases with 250 calibration and 250 evaluation datasets per case. This classification does not establish numerical acceptance or scientific closeout; those require the separate numerical and scientific reviews recorded in Goal 045.

## What was compared

The same observations were analysed with spread speed supplied at its true value and with speed estimated together with prey effect. Rho=1 is usual spread and rho=0.5 is half speed. Effects of 1x, 3x, and 5x multiply prey loss hazard after predator arrival; 1x is the no-effect control. Background hazard is known at 0.002/day (11.3% 60-day loss risk without predators), and both detection probabilities are known at 0.65.

All fitting uses the same 120 training sites. The 40 cluster-isolated holdout sites only evaluate prediction. Both analyses keep predator arrival latent, share the candidate arrival between species within a site, and use a site-marginal composite likelihood without claiming spatial independence of the observed sites. Previous all-160-site summaries are contextual comparisons, not exact replay targets.

## Primary paired changes

Each change is estimated-speed minus supplied-speed, averaged over paired complete evaluation datasets. Positive error or width changes are deterioration; negative coverage, no-effect exclusion, or conditional prey score changes are deterioration for non-null effects. In no-effect controls, a positive exclusion change is worse because it means more false alarms. An interval excluding zero indicates a detectable difference, not necessarily a material ecological penalty.

| Case | Error change | Log-width change | Coverage change (pp) | Exclusion change (pp) | Prey score change (nats/site) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Usual speed, 1x effect | +0.0003 [-0.0016, +0.0022] | -0.023 [-0.040, +0.027] | -1.200 [-2.400, +1.200] | +1.200 [-1.200, +2.400] | +0.00002 [-0.00006, +0.00010] |
| Usual speed, 3x effect | +0.0002 [-0.0020, +0.0026] | -0.018 [-0.024, +0.054] | +0.000 [-0.800, +2.400] | +1.600 [-3.200, +2.400] | +0.00015 [-0.00013, +0.00042] |
| Usual speed, 5x effect | +0.0001 [-0.0028, +0.0031] | -0.010 [-0.031, +0.039] | +0.000 [-3.200, +2.800] | +0.000 [-0.400, +0.000] | +0.00023 [-0.00022, +0.00073] |
| Half speed, 1x effect | +0.0002 [-0.0017, +0.0022] | -0.013 [-0.021, +0.033] | +0.000 [-1.200, +0.400] | +0.000 [-0.400, +1.200] | +0.00000 [-0.00006, +0.00006] |
| Half speed, 3x effect | -0.0001 [-0.0024, +0.0022] | +0.016 [-0.021, +0.048] | -0.400 [-1.600, +1.200] | -2.000 [-2.800, +1.600] | -0.00000 [-0.00020, +0.00021] |
| Half speed, 5x effect | -0.0020 [-0.0043, +0.0002] | -0.022 [-0.039, +0.038] | -0.800 [-1.600, +1.200] | +0.400 [-0.400, +2.000] | +0.00009 [-0.00022, +0.00039] |

Brackets are 95% percentile intervals from 1000 bootstrap resamples. Complete calibration dataset indices and complete evaluation dataset indices are sampled independently; each draw is shared across all six cases and both analyses. Separate effect cutoffs for both analyses and the estimated-speed rho cutoff are recomputed in every resample. No sites are resampled, simulated, or refitted. Uncertainty includes calibration-sample variation but remains conditional on this integration bank and generating model.
The saved run uses 65536 arrival integration draws with no additional draws during synthesis.

Primary prediction is the holdout-site mean of log P(prey,predator | training fit) minus log P(predator | that same fit). Holdout predator observations are permissible conditioning information; holdout prey observations only score predictions. The matched no-effect model uses the same known background and detection information; its conditional prey score is independent of rho and identical between analyses. The saved advantage is relative to that common null, so its paired change is also the paired change in conditional prey score. Secondary joint-score advantages use the null's own training-only rho estimate when speed is estimated.

## Intervals and calibration

Each case uses 250 calibration and 250 independent evaluation datasets, with order statistic 239/250 as each local cutoff (239/250 in production). These are 95% parameter-specific, marginal calibrated profile intervals, not Bayesian intervals or a simultaneous joint region. Calibration still knows the generating condition: the experiment relaxes the process oracle, but does not establish field-ready calibration. Grid support is retained exactly; reported log width is log(upper/lower) across support extrema, with disconnected components and boundary contacts reported separately. Endpoints, connectivity and widths describe the discrete fitting grid; continuous-profile endpoints have not been validated.

| No-effect control | Analysis | False exclusions / datasets | Rate [95% Wilson interval] |
| --- | --- | ---: | ---: |
| usual_1 | Speed supplied | 10/250 | 0.040 [0.022, 0.072] |
| usual_1 | Speed estimated | 13/250 | 0.052 [0.031, 0.087] |
| slow_1 | Speed supplied | 11/250 | 0.044 [0.025, 0.077] |
| slow_1 | Speed estimated | 11/250 | 0.044 [0.025, 0.077] |

Coverage and false-exclusion Wilson intervals describe evaluation Monte Carlo uncertainty at the realised cutoff; the accompanying bootstrap intervals also include calibration variation. Coverage is not required to have a Wilson interval containing 0.95 in every case. Signals below nominal coverage or above 5% null false exclusion are prompts to examine magnitude and uncertainty, not automatic failure. Physical boundary contact at effect=1 is expected under the null and has no interior requirement.

## Secondary context

The condition table contains median absolute log error and median log interval width for both effect analyses and for rho when estimated. Reference benchmarks are effect error 0.20 and width 0.80, rho error 0.10 and width 0.50, and approximately 95% coverage/exclusion. These labels are descriptive context, not scientific completion criteria; exclusion is not a desired outcome for the no-effect controls.

- usual_1: no effect control.
- usual_3: both analyses weak by effect context.
- usual_5: both meet effect context benchmarks.
- slow_1: no effect control.
- slow_3: both analyses weak by effect context.
- slow_5: both analyses weak by effect context.

Both-analyses-weak cases already have weak effect recovery with speed supplied; their total weakness cannot be attributed to estimating speed. Added estimation cost is assessed by the paired continuous changes, including when both analyses are weak. Differences between usual and half-speed generating waves are explanatory comparisons, not causal evidence for a specific event-yield mechanism. No case is required or retuned to become recovered.

## Figures and event information

`paired_recovery.svg`: dots show paired mean changes and bars show their 95% calibration-aware bootstrap intervals. The first five panels use estimated minus supplied speed; percentage-point axes multiply proportions by 100. The final panel shows mean true post-arrival prey losses among 120 training sites, with evaluation bootstrap intervals. Colours identify generating wave speed, not analysis lane.

`representative_likelihoods.svg`: each panel uses evaluation dataset index 0, chosen in advance for all cases. Colours show twice the joint training log-likelihood loss from that panel's maximum, not a confidence region. Crosses mark generating values, circles mark joint maximum-likelihood fits, and dashed lines show supplied speed. Every panel displays rho from 0.8 to 1.2 times its generating speed, with the same relative scale in both rows. The full fitting domain remains rho=0.25 to 4 and effect=1 to 10; the display zoom does not alter fitting.

`event_information.csv` reports true loss counts by day 60, pre-arrival and post-arrival loss counts, censored sites, post-arrival at-risk exposure in site-days, and summed prey detections, all over 120 training sites. These are truth-assisted explanatory diagnostics and never inference inputs. Absorbing prey extirpation means later detections are unavailable after a true loss.

## Calibration review signals

- coverage_below_nominal_wilson_signal:usual_5:known_speed:effect
- coverage_below_nominal_wilson_signal:usual_5:estimated_speed:effect

Profiles SHA-256: `68cb9acc72e07589d6ab752841dba74313a1f1d9d4a297923f560d586f07d8ad`. Source commit: `e8c08f10f7b67118a85ee37770d8ee48ee2c213a`.
