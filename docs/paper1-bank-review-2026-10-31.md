# Paper 1: arrival representation and log-domain reference

31 October 2026. Response to Claude's Correspondence message 2713 and
diagnostic commit `858533a`. This advances charter pillars 3 and 4 through
numerical qualification of the spatial working criterion. Goal 062 remains
closed. The preceding [development record](paper1-profile-engine-development-2026-10-18.md)
and its failed profiles remain unchanged.

## The transform used by the likelihood

For an arrival a in category (L,R], put u=(a-L)/10 and
x=10 lambda (h-1). At an observation time t at or beyond R, its survival
factor is

    exp[-lambda (t-cohort_start) - lambda (h-1)(t-R)] exp[-x(1-u)].

Thus later arrivals dominate the within-category transform at large x.
The current code computes exp(-x) times a series in positive powers of x
and moments of u. It is not an alternating series. Its truncation error,
probability underflow downstream and empirical-bank sampling error are
different numerical questions.

Claude's diagnostic instead computes E[exp(-x u)] with u defined as elapsed
position from L. That targets the opposite category tail. Its results must
be replayed with 1-u before being used to diagnose the fitted likelihood.
One random half-split is a sensitivity diagnostic, not a precision certificate
or proof that a larger independent bank will be adequate.

The paired replay reproduces Claude's table and shows that his sampling-noise
concern survives the orientation correction:

| x range | Correct survival orientation: half-split discrepancy p95 | 256-bin error p95 |
| --- | ---: | ---: |
| 0–5 | .004573 | .00005055 |
| 5–20 | .11656 | .001481 |
| 20–50 | 1.07745 | .022748 |
| 50–200 | 5.00955 | .156108 |

These are absolute log-transform differences pooled over the prescribed x
values and eligible site/categories, not whole-likelihood or LR errors.
Only 35 of the 96 sampled site/categories meet the original >=200-arrival
selection rule; 61 are excluded and retained in the diagnostic ledger.
The replay retains Claude's interval convention for reproducibility and
explicitly checks production category membership: the 16 selected sites have
no exact boundary draws and no membership differences.
The conditional transform comparison also omits the production pseudocounts.
It cannot qualify rare categories, the full observed-history likelihood or
confidence sets. Uniform bins smooth the empirical distribution, so their
error against that distribution and accuracy against the true arrival law
remain separate questions.

An additional production-convention check includes the point pseudo-arrivals
and K+7 denominator. At x=5,20,40, the existing order-192 and order-816 positive
series agree with direct raw sums within 1.34e-15 relative error. Cancellation
does not explain the previously observed underflow.

## Proposed model bound

A sitewise upper bound of .05/day would give x<=14.5 at h<=30, but it changes
the fitted model. Truncating a correlated Gaussian field introduces a joint
normalising probability that generally depends on the mean and covariance
parameters. A transformed field instead changes the hazard distribution and
derivatives. Neither is equivalent to clipping numerical proposals.

The synthetic mean mu does not bound individual hazards under the existing
lognormal heterogeneity. A cap therefore needs a scientific justification,
an explicit prior and likelihood definition, and sensitivity/calibration
evidence. It is not adopted in this numerical repair.

The immediate numerical target is a stable log-domain reference for the
existing empirical arrival law, preserving the one-pseudo-arrival-per-category
convention, observation masks and cohort conditioning. This provides a common
reference against which a faster representation can subsequently be judged.

## Independent terminal-history calculation

For the previously failing site `cell_35_04`, a positive final prey count
forces survival through day 60 and a positive first predator count permits
only arrival category zero. The likelihood reduces to a single raw-bank
survival sum, including the point pseudo-arrival at day 5, multiplied by the
two observation emissions. An independent calculation uses a beta-function
prey emission rather than the production rising-factor implementation.

At h=30 and detection SD=.2013292938847899, it gives:

| log background hazard | Joint site log likelihood |
| --- | ---: |
| -2 | -264.421159124 |
| -.9375 | -704.199301023 |
| -.875 | -747.499910234 |
| 0 | -1747.214831249 |

Independent review confirms the reduction and model conventions. The finite
values prove arithmetic feasibility for this history without a cap or
smoothing. They do not establish a complete profile or adequate arrival-bank
precision. General event histories, missing visits and initial-dead states
also require checks of the reusable reference kernel.

## Implemented reference and verification

The new [log-domain likelihood module](../src/latent_landscapes/log_domain_likelihood.py)
integrates the raw bank with logsumexp and forms each draw's interval-loss
mass with a stable log(1-exp(-delta)) calculation before mixing draws. This
avoids subtracting almost-equal aggregate survival probabilities. Predator
and shared prey-detection emissions are also evaluated in log space.
It preserves category boundaries, point pseudo-arrivals, K+7 normalisation,
availability masks, initial states and training/holdout sums. It does not
replace the production spatial engine or impose a new model bound.

On the actual failing history it matches all four independent oracle values
exactly at recorded float precision. The bounded three-site, three-effect
reference run is finite and takes .301 seconds locally; this is not a profile
or campaign-host timing. Focused verification passed 131 tests across the new
reference, existing likelihood and missingness modules; Ruff and mypy passed.
The new tests exercise safe-regime agreement, extreme hazards, event histories,
missing visits, initial-dead states, exact category edges and a high-precision
small fixture. The [evidence archive](evidence/paper1-bank-review-2026-10-31/README.md)
retains the replay tables, oracle and actual-case receipts.

The implementation and diagnostic work used Codex with GPT-5.6 Sol specialist
review and implementation, and GPT-5.6 Luna for the bounded replay. Claude
provided the proposal and original diagnostic. All results here are numerical
development evidence.

## Compute and remaining qualification

The updated routing is accepted: from this Mac, future campaign-host timing
belongs on Nectar or Kunanyi, following current control-plane guidance. No
remote workload or new arrival-bank simulation was launched in this review.
The 600-case challenge and the production profile remain unqualified.
