# Independent review: Goal 058 effect-reference micro-pilot

4 October 2026 (Hobart). This review covers the registered four-node null
experiment, its frozen source and random addresses, the 3,996 production
histories, the independent direct-bank likelihood audit, and the descriptive
synthesis. It does not review or authorize a new screening calibration,
full-grid effect references, a sealed truth-draw law, or a capstone run.

## Decision

**Accept the completed attempt as a successful four-node numerical and
operational qualification. All four 999-reference tables are usable under the
registered fixed-address rule.** Every registered history was generated and
retained; all null and free fits met the prospective validity criteria; the
independent scorer reproduced all stored likelihoods and statistics far inside
their tolerances; and the production-plus-audit path remained inside the
two-hour, 48-GiB, 16-production-worker and 4-audit-worker envelope.

This decision is pointwise and conditional on the frozen landscape, site
design, observation schedule, generator, empirical integration bank, fitting
algorithm, source state and four nuisance settings. It establishes neither
false-declaration control nor power, coverage, effect recovery, screening
calibration, off-grid validity, robustness to residual fields, map transfer,
or computational performance at the other 761 coarse-grid nodes.

## Scientific target and observed result

At each fixed nuisance node, the target was the Monte Carlo null distribution
of

\[
T=2\max\{0,\ell_{\mathrm{free}}-\ell_{h=1}\},
\]

where both likelihoods fit the same 120 training-site observations extracted
from the full 160-site generated history and retain continuous nuisance
optimization. The sampling unit is a correlated-spread history; the 160 sites
within a history are not independent replicates, and the 40 holdout sites do
not enter these fits. The 3,996 histories therefore provide 999 independent
registered Monte Carlo addresses at each of four purposively selected nodes,
not 639,360 site-level replicates and not a factorial estimate of separate
beta, hazard and detection effects.

All four nodes produced 999 valid returned fit pairs from 999 assigned
addresses. There were no nonconverged returned null or free fits, non-finite
pairs, null-below-truth failures, free-below-null failures, replacements or
dropped histories. This does not assert that every internal attempt in the
frozen multistart procedure converged; validity applies to the retained fit
result and its recorded diagnostics. The pointwise observed address-level
failure fraction is consequently zero at every node, but its exact 95%
binomial interval is `[0, 0.003686]`; the experiment does not prove a zero
failure probability.

| Node | Setting `(beta, mu, detection SD)` | Near-zero `T` (`<=1e-6`) | `T` 95th / 99th percentile | Mean worker seconds | Main free-fit boundary contacts |
| ---: | --- | ---: | ---: | ---: | --- |
| 382 | `(0, .0025, .2)` | 508 / 999 | 2.709 / 4.915 | 5.555 | `h` lower: 508 |
| 0 | `(-2, .0005, 0)` | 667 / 999 | 1.609 / 3.176 | 4.765 | `h` lower: 667; `h` upper: 73; beta lower: 730; mu lower: 632; detection SD lower: 495 |
| 764 | `(2, .006, .4)` | 440 / 999 | 2.811 / 5.335 | 3.978 | `h` lower: 440; beta upper: 422; mu upper: 324; detection SD upper: 517 |
| 44 | `(-2, .006, .4)` | 614 / 999 | 2.067 / 3.744 | 4.209 | `h` lower: 614; beta lower: 444; mu upper: 360; detection SD upper: 511 |

Boundary counts overlap. They diagnose non-regularity and parameter trade-offs;
they are not additional failures. In particular, the lower-rate corner often
placed `h` at either bound and nuisance parameters at their bounds despite
formal convergence. This is evidence of weak information at that setting and
precludes interpreting `h-hat` as recovery evidence. The marked differences
in the near-zero mass and upper tail also support node-specific empirical
reference tables rather than a common chi-square approximation.

## Numerical, provenance and serialization evidence

The target qualification used the registered Goal 045 empirical integration
bank with shape `(131072, 160)`, file SHA-256
`d4f564030cf1ece2b56d3f735e4c2e12d3ec76eeba3c85f43a425bdeb5841dd9`
and the exact Goal 056 bank receipt. On one mechanical history at each node,
the thin adjusted-pair wrapper exactly reproduced the parameters, raw scores
and statuses from the existing four-model route. The eight-history target
smoke run was fully valid and its independent audit passed before any
registered address was generated.

The registered source manifest has SHA-256
`0fa472c470b7246ce5ef14eaf84e41bd04241f7dd9f892bedf875914bf8b836e`.
It binds the reviewed production module, auditor, driver, registration,
and frozen seed inputs. The production manifest additionally binds the exact
qualification receipt and has SHA-256
`1f2cbbf298bd8fb7328c43834bf2e406c144d41bec61e2710c886cdfcb55395d`.
Its 8,003 listed artifacts total 65,995,338 bytes and independently rehashed
with no mismatch. Including the manifest, the returned run contains 8,004
files and 66,866,422 bytes.

The run contains exactly 3,996 unique `(node, reference)` addresses, references
0--998 once at each node, with the registered root `2026100402`, namespace 58
and five named stage streams. The frozen and copied `(3996, 5)` seed ledgers
both match SHA-256
`82cc2a026e11439e36614f4c5fb8403246f30ad62bbed8c7e9d8c55b0f061011`.
Every root table contains the exact reference vector, raw null and free scores,
`T`, validity flags and usable flag; these agree with the row artifacts and
their node summaries.

The independent auditor evaluated the true, fitted-null and fitted-free points
for every history using the direct empirical-bank reconstruction, without
calling the production likelihood, hazard normalizer, emissions functions,
fitter or Goal 058 production module. All 3,996 rows passed identity, latent,
seed, opaque-observation, fit-contract, score, nesting, statistic and declared-
validity checks. There were zero scorer mismatches and zero kernel failures.
The largest absolute production-versus-independent discrepancies were
`1.137e-12` log-likelihood units and `2.728e-12` in `T`, against tolerances of
`1e-8` and `1e-6`; reconstructed site hazards agreed exactly. Tiny negative
free-minus-null differences of order `1e-13` are round-off and remained far
inside the registered nesting tolerance.

The auditor also verified every production file hash, source and qualification
binding, ledger, table and node-summary hash. Same-generator replays at
references 0, 499 and 998 for all four nodes reproduced arrivals, losses,
hazards, detection values, latent prey states, prey and predator counts and
opaque identifiers bitwise. These 12 replays demonstrate deterministic
addressing and serialization; as prospectively stated, they are not an
independent reimplementation of the correlated-spread generator.

## Resource result and cost interpretation

Production took 1,239.246 seconds and the four-worker independent audit took
538.733 seconds. The supervised production-plus-audit attempt took 1,778.282
seconds (29.64 minutes), with sampled peak process-group RSS of 7.461 GiB,
exit code zero, no resource stop and no remaining child process. The summed
per-history worker wall time was 18,489.276 seconds, or 4.627 seconds per
history; this excludes pool startup and parent-side checkpoint writes and is
not CPU time.

The synthesis reports arithmetic scaling scenarios separately from observed
cost. The 163- and 268-node counts are medians from old Goal 057 descriptive
subsets, not newly calibrated retained unions or executable workloads. The
765-by-999 scenario is a hypothetical full effect-reference grid, not the
required 99-reference screening recalibration. Equal-worker 16/64 scenarios
are unconstrained ideal scaling and do not describe the frozen 16-worker
production and 4-worker audit implementation. None of these calculations is a
cost forecast for untested nodes or authority to launch a larger run.

## Residual risks and recommendation

The principal residual scientific risks are weak identification and frequent
boundary solutions, selection or extrapolation beyond the four nodes, and a
shared generator defect that deterministic replay would not reveal. The
direct-bank score audit gives strong evidence against a production likelihood
or serialization error, but it does not independently validate every
assumption in the data-generating process. The four-node panel is purposive and
non-factorial, so differences among its tables cannot be assigned separately
to beta, hazard or detection variability.

For a later fixed on-grid `theta`, an earlier reference bank can support an
exact Monte Carlo rank when the complete test and `theta` were selected
independently of that bank and the sealed observation is an independent draw
from the same law. A prospectively fixed bank-independent mixture over such
pointwise-valid settings preserves that validity. Time order alone does not
invalidate a bank.

Here, however, the final sealed truth-draw law and complete capstone test are
still unresolved, while Goal 058 outputs are now available for design. Reserve
these four tables as development evidence and do not pool them into primary
capstone ranks. A separately approved 99-reference recalibration of the local
screen on the 765-node support can serve as a developmental study of retention,
union behavior and resource caps. If its realised reference outcomes inform
the final truth law, test or cap, keep those screen references developmental.
Then reconcile the sealed support and branch weights and freeze the truth-draw
law, complete test, cap, abstention and multiplicity rules. After that freeze,
use new roots or namespaces for both confirmatory screening and effect-reference
streams and for independent sealed observations. A later change that depends
on the realised confirmatory references and lacks a demonstrated
validity-preserving argument would make those references developmental and
require a newly authorized refreeze and fresh streams. This is a conditional
recommendation for the present design sequence, not a claim that every future
change, including a justified conservative change, necessarily invalidates an
earlier bank.

An old beta `.6` truth can receive pointwise exact-family reference treatment
only through a prospectively specified exact-`.6` reference law, or through a
prospective change of the truth law to approved on-grid support; silently
snapping `.6` is not valid. A residual-field B100 branch remains a
misspecification experiment and needs separately registered robustness or
operating-characteristic evidence. Fresh random streams cannot turn it into an
exact-family case.

No further experiment is authorized by this review. Additional independent
review is unlikely to change the four-node numerical acceptance unless it
independently reimplements the generator, but scientific review at the future
screening-cap and sealed-law gate could materially change the capstone design
and remains warranted.
