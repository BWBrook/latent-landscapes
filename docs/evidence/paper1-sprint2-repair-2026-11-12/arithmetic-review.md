# Independent review of arithmetic repair condition D

12 November 2026 · Codex (GPT-6.1 Sol). This review reads the frozen `99af520`
source and the archived projections; it makes no model evaluations or source
changes.

**Accept deferring D for this bounded candidate, with the stated retained-mode
scope.** The archive note does not claim an observed maximum mode log hazard.
Its conservative bound is sufficient to exclude the ten-unit proximity
condition for retained converged modes, without treating transient inner trial
proposals as converged modes.

I checked `_floored_eigenvalues`, the criterion expression, the registered
covariance constructor and the scalar derivative expression against the frozen
source. For positive eigenvalues the normalized smooth floor is increasing
from `c = 0.1 / (1 + 0.1 exp(-10))`, so `logdet(F) >= n log(c)`. The
observed-history law has site probabilities at most one in exact arithmetic.
Consequently the criterion identity gives
`q = u' C^-1 u <= -2 f - n log(c)` before the stated numerical allowance.
Coordinate Cauchy-Schwarz yields `u_i^2 <= C_ii q`; the registered kernel has
`C_ii = sigma^2`, giving the note's coordinate bound. This does not require
a bound on the largest covariance eigenvalue.

I independently recomputed the maximizing archived record's bound as
`91.19321406576661`, using the recorded criterion, n, parameters and verified
exposure maximum. The scalar comparison is conservative: bounding the
large-z polynomial by `5 z^3` gives a safe log-z floor of `236.05775832698328`;
the maximum calendar/effect exposure of 300 reduces that to log hazard
`230.35397585232707`. The separation exceeds 139 log-hazard units. The much
looser sensitivity calculation allowing every site log probability to equal
one still leaves more than 121 units. This is robust to ordinary floating-point
rounding and the certified series approximation, while remaining an algebraic
floating-point bound rather than an interval proof.

The three archived projection hashes agree with `condition-summary.json`.
The read-only query checks original receipt hashes, traverses all 417 nested
search receipts and includes successful positive-mode records with finite
stored criteria; duplicate serializations do not invalidate a maximum. The
reported 93,752 records are retained candidate summaries, not 93,752 distinct
mode calls. I inspected the query and projections, but did not independently
rehash all remote receipt bytes or reopen raw banks.

The limitation matters: an archive that omits raw mode vectors and extrema
cannot establish the literal maximum over every unarchived converged inner
call, nor does this bound cover arbitrary or rejected trial states. The
`max_observed_x` counter mixes trials and h values and cannot replace that
missing quantity. The decision to defer the conditional scalar repair is
therefore scoped to the retained converged-mode evidence, and must not be
described as global safety of the likelihood arithmetic or mixture moments.
Repair A remains necessary for invalid inner proposals. Recording actual mode
extrema in future candidate diagnostics would remove this archive limitation
without changing the estimator.

No objection to omitting D from the present A+B+C implementation on this
evidence. The exact A+B+C code and acceptance machinery require the separate
code review before repaired-candidate runs.
