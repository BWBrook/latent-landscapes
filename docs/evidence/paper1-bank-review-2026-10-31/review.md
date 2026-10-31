# Independent review: arrival representation and log-domain reference

31 October 2026. Read-only methodological and code review of the arrival-bank
diagnosis and raw-bank log-domain likelihood reference. This review does not
approve a production-engine replacement, a fitted-model change or a Paper 1
profile.

## Verdict

Accept `src/latent_landscapes/log_domain_likelihood.py` at SHA-256
`791a5f53938d3f046eaee57ed6ec40903ff8ec03e68588f9c5a3519dce9b55d4`
as a high-accuracy reference kernel for the existing empirical-plus-pseudo
arrival law. It preserves every raw arrival, one point pseudo-arrival in each
of seven categories, the `K+7` denominator, canonical `side="left"` category
membership, observation masks, initial state and cohort calendar. It neither
smooths the bank nor bounds the fitted background hazard.

The implemented factorisation is correct. For every raw arrival it evaluates
interval loss as `log S_j + log(1 - exp(log S_(j+1) - log S_j))`, then mixes
arrivals, categories, predator emissions and prey event/alive emissions with
`logsumexp`. This avoids subtracting underflowed or nearly equal aggregate
survival probabilities.

## Evidence and model consequences

The production finite-category transform is
`exp(-x) E[exp(x u)] = E[exp(-x (1-u))`, not the diagnostic's original
`E[exp(-x u)]`; the production moment series has positive terms. The corrected
orientation replay shows that the large-x empirical-bank half-split concern
survives this correction, but only 35 of 96 sampled site/category pairs pass
the diagnostic's minimum-count filter. The split therefore remains a warning,
not a bank-precision certificate. The 256-bin result measures smoothing error
against the same finite empirical bank and does not establish accuracy against
the generating arrival law or the full observed-history likelihood.

The existing order-192 and order-816 moment representations agree with direct
raw sums to `1.34e-15` maximum relative error at the tested x values 5, 20 and
40. The recorded zero at the difficult site is instead probability-scale
underflow: the raw-bank log kernel returns finite joint log likelihoods and
matches the independently reduced terminal-history oracle exactly at all four
tested log hazards, including `-747.4999102337309` at log hazard `-0.875`.

A sitewise `.05/day` hazard cap is not a numerical representation change. A
truncated correlated GP introduces a parameter-dependent joint normalising
probability and boundary integration; a transformed GP changes the background
distribution, derivatives, Laplace target and importance weights. Either can
alter the background--effect trade-off and would require a separately defined,
reviewed and calibrated fitted model. Neither the cap nor histogram smoothing
is supported by the present evidence.

## Verification

The independent terminal oracle covers the actual forced-survival/category-zero
underflow history. A separate 80-decimal-place fixture enumerates empirical
arrivals exactly at days 10, 20 and 60, a day-61 arrival and all seven
pseudo-arrivals. It independently calculates category membership, Beta-binomial
prey emissions, predator emissions, interval-loss and terminal contributions;
both event and terminal masses are positive, and its joint log likelihood agrees
with the kernel within `3e-13`. This closes the earlier general-mixture test gap.

At test-source SHA-256
`de33627a9cc47b7062b2d87da5966608c124652c82cf6f9b61020c9c59bb4630`,
the parent independently ran 131 focused tests successfully in 0.58 seconds;
Ruff and mypy were clean. The actual-case receipt is archived at SHA-256
`6271520d49532b73f4b0b2b7fb8820ed1c8965b2ce22c1a56eb9a7d34ae9a247`.

## Residual risks and recommendation

This establishes arithmetic feasibility and a defensible reference, not
empirical-bank adequacy, fast production scoring, interpolation derivatives,
Laplace accuracy, importance-sampling accuracy, profile convergence, confidence
sets or calibration. Retain the current fitted model. Use this kernel to judge
candidate faster representations at the complete site-likelihood and profile
levels, including rare categories and difficult histories. Independently
qualified production integration and complete profiles remain necessary before
the 600-case challenge. Further independent review would materially increase
confidence only at that production/profile gate or if a bounded background
model is proposed; it would not change the present reference-kernel decision.
