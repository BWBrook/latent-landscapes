# Goal 047 independent terminal scientific review

**Review date:** 12 September 2026 (Hobart), after Stage A and before any
Stage B bank generation.

## Decisive finding

Stage A is a valid terminal negative result: **the current integrator is
pseudocount-sensitive under the prospectively registered rule**. Six of the
nine within-bank alpha comparisons fail the connected calibrated-width gate.
The empirical arrival bank, histories, map, sites, likelihood grid and
calibration rank are identical within each comparison, so changing alpha is
the isolated intervention. Stage B must remain unrun. This result rejects the
current integration method for Goal 046; it does not select a replacement
alpha, establish exact integration bias or support an ecological sampling
contrast.

The numerical evidence distinguishes two sensitivities. The connected
calibrated width responds materially to the relative pseudocount weight. The
corridor far-tail LR is stable across alpha within a bank but remains unstable
between the two equal-K bank halves. A single remedy therefore cannot be
inferred from these results.

## Independent reconstruction from the reduced arrays

I reconstructed every decision quantity directly from
`diagnostic-arrays.npz`, without using the values in `stage-a-decision.json`.
For each bank/alpha I derived the calibration LR and validation LR drops again
from the raw connected training likelihoods; all 18 derived arrays agree
bitwise with their saved counterparts. I then independently applied the
rank-239 cutoff, inclusive support mask, component count, H181 endpoints, null
coverage and balanced-minus-access mean log-width calculation. All history
indices reported below are zero-based.

### Connected calibrated-width sensitivity

| Bank representation | Alpha 0.25 | Alpha 0.5 | Alpha 1.0 | Maximum range | Failing alpha pairs |
|---|---:|---:|---:|---:|---|
| First K65536 half | 0.076328065 | 0.064522619 | 0.064528787 | 0.011805446 | 0.25/0.5; 0.25/1 |
| Second K65536 half | 0.076898180 | 0.064268444 | 0.064259167 | 0.012639014 | 0.25/0.5; 0.25/1 |
| Combined K131072 | 0.084567570 | 0.076563427 | 0.064292859 | 0.020274711 | 0.25/1; 0.5/1 |

All three ranges exceed the registered 0.01 tolerance. Each of the six failing
pairs also changes the lower/upper boundary classification for one evaluation
history, violating the zero-change rule. The boundary case is history 231.
Support-component counts never change, endpoints move by no more than one H181
cell, coverage/exclusion changes by at most one history, and cutoff movement
never exceeds 0.158 LR. The failure is therefore not diffuse profile failure:
it is alpha sensitivity propagated through a high calibration order statistic
and discrete support endpoints.

The balanced calibration cutoff drives the material movement. At the decisive
alpha transition, calibration histories 131 and 124 exchange the rank-239
position. That cutoff change alters endpoints for 115--190 of the 250 balanced
evaluation histories in the six failing comparisons, compared with only one to
three access histories. The resulting balanced-minus-access mean width crosses
the registered threshold even though most lower-level limits pass. This is the
same non-smooth propagation mechanism implicated by Goal 046, now isolated by
holding the empirical bank fixed.

### Corridor alpha sensitivity and bank variability

All 27 within-bank corridor cases pass: three bank representations, three alpha
pairs and three effect truths. Across them, the largest generating-rho LR
movement is 0.0629103 against the 0.5 limit; the largest rho-core movement is
0.0067741 and the largest effect-core movement is 0.0002123. Rho and effect MLE
indices are unchanged. Every maximum is the interior rho node
1.1019051158766109, so no fixed-window case is inconclusive.

The equal-K comparison tells a different story. At primary alpha=0.5, the two
K65536 halves differ by 1.8378--1.8597 LR at generating rho=1 for the three
effect views, while their local rho-core movements are 0.4049--0.4117 and their
MLEs are identical. The three effect rows share one predator history and are
not independent replicates. This remains post-selected stress evidence rather
than a frequency statement, but it shows that the known corridor tail failure
persists at fixed K and alpha and is not explained by pseudocount choice.

### Matched relative pseudocount weight

All four connected matched-weight comparisons pass. Comparing half-bank
alpha=0.25 with combined-bank alpha=0.5, or half-bank alpha=0.5 with
combined-bank alpha=1, keeps the normalized pseudocount fraction fixed while K
doubles. The paired mean-width movement is at most 0.000335, cutoff movement at
most 0.00205 LR, and no boundary classification changes.

This alignment supports pseudocount weight as a material driver of the
connected width movement. It does not prove that pseudocount weight explains
all of the original bank-doubling change: each combined bank contains its half,
K and empirical draws also change, and likelihood formation, profiling and
calibration are nonlinear. The matched-weight corridor comparisons still move
0.862--0.987 LR at the generating rho and fail the tail tolerance, consistent
with a separate bank-realization effect.

## Verification and claim boundary

The reviewed NPZ has SHA256
`bb29664ec8197bfd1811c4ca23271b2f8801d485f2b3c6be3070f73e70259967`.
All 47 arrays are finite and have the registered H181, eight-rho,
two-design and 250-history shapes. My independent classification reproduces
`pseudocount_sensitive`, all six connected failures, all corridor alpha passes,
and the absence of window-edge maxima.

The frozen alpha=0.5 replay errors are zero for both first halves,
1.819e-12 for the connected combination and 4.547e-13 for the corridor
combination, all below 1e-9. The run completed with exit 0 in 1594.92 seconds
(26.58 minutes), with peak sampled RSS 3.10 GiB and no memory-limit breach.
These checks establish faithful execution of the registered calculation; they
do not establish exact numerical accuracy.

The causal statement is conditional and narrow: on connected map 2026090812,
for the original known-rho null histories and the frozen pseudo-arrival
locations, changing only alpha is sufficient to change the calibrated width
functional beyond its accepted numerical tolerance. The study does not show
which alpha is closer to an exact integral, whether a fixed relative
pseudocount weight is scientifically preferable, or how frequently this occurs
across maps or new histories. No qualified higher-accuracy reference exists.

Goal 046's four numerical failures remain binding. Nothing here supports
balanced-versus-access ecological inference, and the two barrier endpoint
failures remain outside Goal 047.

## Recommendation and residual risk

Stop Goal 047 at Stage A exactly as registered. Do not generate the six fresh
K65536 banks, run prospective controls, double K, relax the width tolerance or
adopt alpha=0.25 or 1 because one output appears more stable. The current
integrator is not eligible for Goal 046 requalification.

If Charter Pillar 3 remains necessary, the next decision is between closing Arc
3 as numerically unresolved and registering a replacement integration method.
A replacement should address both the calibration functional's dependence on
regularization weight and the corridor tail's bank-realization variance. Making
the pseudocount fraction constant with K would change the integration method
and its asymptotic regularization, so it requires prospective scientific review
rather than an implementation patch. A variance-reduced estimator is one
candidate for reducing the observed bank-tail variability. Any claim of reduced
bias or convergence would additionally require a separately qualified
higher-accuracy reference or other direct accuracy evidence.

Further independent review is unlikely to change the present stop decision:
the failure repeats across both disjoint halves and their combination, exceeds
a frozen threshold, and is derived under an isolated within-bank alpha change.
Independent methodological review would materially improve confidence before
choosing any replacement method or changing the inferential claim.
