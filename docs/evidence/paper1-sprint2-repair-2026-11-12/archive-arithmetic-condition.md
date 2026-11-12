# Arithmetic condition D: defer using a conservative retained-mode bound

12 November 2026 · Codex (GPT-6.1 Sol). This read-only archive query implements
the conditional check in board message 3307, before repaired-candidate fit
outcomes. No model, repaired candidate or additional mode solve was run, and
no raw arrival bank was read or downloaded.

**Recommendation: defer the scalar arithmetic repair D.** The archive does
not store an observed maximum mode log hazard. However, the retained converged
mode summaries admit a conservative coordinate bound of **91.1933**, far below
the scalar polynomial-overflow regime even after allowing ten log-hazard units.
This recommendation covers retained converged modes; it does not claim the
arithmetic is safe at unarchived or rejected inner trial proposals.

## Archive coverage and what it actually contains

All **417 resolved fit receipts** were read and SHA-256 checked against their
original task output inventories: 211,175,248 bytes. Their nested search
receipts were then independently hash-checked against the same inventories:
362,848,274 bytes. These contain **93,752 serialized positive-variance candidate
records with successful latent modes**, including repeated summaries of the
same fitted state. Every one of the 417 fits contributes such records. No
deduplication is needed for a maximum bound.

The top-level and nested archives do not retain raw latent vectors or mode
eta extrema. Candidate summaries retain criterion, parameters, convergence
flags and scalar mode diagnostics. The root backend counter
`max_observed_x = max(10 exp(eta)(h-1))` is not a mode maximum: it aggregates
successful site-evaluator calls, including inner trial proposals, mixes h
values and is identically zero at h=1. Its largest archived value is
`1.4014392639449873e102`; treating that as a converged-mode hazard would be
incorrect.

Nine small public `site_a` exposure arrays were copied and hash-checked
against original fit input bindings. Their common maximum absolute exposure
is **2.5656020641595263**. These are public covariates, not raw arrival banks.

## Coordinate bound

Write the frozen positive-family criterion as

`f = sum_i ell_i - q/2 - logdet(F)/2`, with `q = u' C^-1 u` and
`C = sigma^2 K`.

The empirical-plus-pseudo observed-history law is a probability law, so its
site log probabilities satisfy `ell_i <= 0` in exact arithmetic. The direct
series uses positive finite Taylor sums for arrival transforms, with a
certified relative-tail tolerance of `1e-10`; it does not introduce a positive
likelihood-density normalization. The calculation below adds `1e-6` to the
quadratic-form bound as a conservative numerical allowance. This is an
algebraic bound evaluated in floating point, not an interval-arithmetic proof.
The sensitivity check below makes the large separation explicit.

The normalized smooth floor is not exactly 0.1. From frozen
`spatial_profile._floored_eigenvalues`, its minimum for a valid positive
eigenvalue is

`c = 0.1 / (1 + 0.1 exp(-10)) = 0.09999954600276352`.

Thus `logdet(F) >= n log(c)` and

`q <= -2 f - n log(c) + 1e-6`.

The registered covariance builder has `K_ii = exp(0) = 1`, with no diagonal
jitter added. Coordinate Cauchy-Schwarz in the precision norm gives
`|u_i| <= sigma sqrt(q)`. Therefore every retained successful positive-mode
record has

`eta_i <= alpha + |beta| max|site_a| + sigma sqrt(-2 f - n log(c) + 1e-6)`.

The maximum of this bound across all 93,752 records is
**91.19321406576661**, at a tight connected-0 increased-heterogeneity C lean
record (`h=5.477225575051661`, `n=260`, `f=-1782.927159015343`,
`sigma=1.5`). This is not the actual eta at that mode. Sigma-zero families
have no latent vector; the fitted parameter box directly bounds their eta
by `-3 + 2 max|site_a| = 2.1312041283190526`.

As a deliberately much looser sensitivity check, combining the minimum
retained criterion (`-1958.4790457866534`), largest n (260), sigma limit 1.5
and parameter-box limits yields an upper bound **102.9289**. Even allowing
every site's log probability to be as high as **one**, rather than zero,
raises that coarse bound only to **108.5745**. The decision is not sensitive
to ordinary rounding or the small certified series approximation.

## Comparison with scalar overflow

The problematic scalar expression forms `z (1 - 3z + z^2)` before multiplying
by a vanishing reciprocal. Its large-z cubic scale reaches binary64 overflow
at approximately `log(z) = log(DBL_MAX)/3 = 236.59423763112798`.
For a conservative safe lower comparison, for `z >= 1` the polynomial
magnitude is at most `5 z^3`, giving an overflow-free floor
`log(z) <= (log(DBL_MAX)-log(5))/3 = 236.05775832698328`.

All archived calendars have maximum prey interval 10, and the fitted effect
is at most 30. Hence the loss argument is at most `z = 300 exp(eta)`.
Even the conservative scalar boundary corresponds to
`eta = 230.3539758523271`, more than **139.16** units above the candidate-specific
retained-mode bound. It remains more than 121 units above the deliberately
loose sensitivity bound. Condition D's ten-unit proximity is therefore not
met for the retained converged modes.

This comparison concerns the requested scalar polynomial repair. It does
not establish global safety of mixture moments or arbitrary trial hazards.
The already demonstrated oversized inner trial remains an inner-globalization
problem addressed by repair A; no finite evaluator domain or relaxed guard is
introduced by this archive check.

## Reproduction and provenance

The ignored directory `artifacts/sprint2/repair-20261112/archive-query/`
retains the 417 expected receipt hashes, read-only query scripts, compact
projections, nine exposure arrays and the condition summary. The scripts read
original receipts and calculate summaries; they never invoke a model evaluator.
Run the receipt and nested-bound query scripts through the approved target
transport with target `python3 -`, redirecting their JSON stdout to the
corresponding projection files. The bound script embeds the original expected
hashes, the verified exposure maximum and the floor formula. Absolute target
paths remain only in the ignored operational scripts.

| Retained file | SHA-256 |
| --- | --- |
| `receipt-projection.json` | `0330f44dbc6c7796dc76a5ca294406170bd37a2f192fb8413a0f3ddd9a05ae1c` |
| `mode-bound-projection.json` | `5c23183b8d65f484d5f9c99298942615045001b8703d5495fa155efc4be7a9a2` |
| `exposure-projection.json` | `bf44c90ef0c6fdc16d9b9e2e8f0a4c9e7822fd83ee1d9c0f6b19b6037868b140` |
| `condition-summary.json` | `7b3b41f6a06bb2c9bf4d0ea84cb1d898e75e7f3cc47ebf232d1321ec6a0624d9` |

No source, threshold, convergence rule or original receipt was changed.
Independent code review should check this bound and its retained-mode scope
before using it to omit D from the repaired candidate.
