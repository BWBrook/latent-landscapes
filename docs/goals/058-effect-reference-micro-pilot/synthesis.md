# Goal 058: the full effect-reference path passes at four null settings

4 October 2026, Hobart. **Complete; all four 999-reference tables are usable.**
This advances Charter Pillar 4 calibration and Pillar 5 capstone preparation.
Barry's approved beta spacing .25 gives a frozen 765-node reference support;
continuous fitting and the existing local-screen construction remain unchanged.

The full pipeline generated 3,996 correlated-spread histories, fitted the
adjusted null and free-effect models, preserved observations and latent
quantities, wrote shared reference tables and passed independent direct-bank
checks. It finished in **29.64 minutes** with a sampled **7.461 GiB** aggregate
peak. No reference was invalid and no table required abstention. This removes
the implementation and resource uncertainty at these four fixed settings.
It does not establish reliability across the other 761 nodes or measure the
final procedure's false-declaration rate, power, coverage or effect recovery.

## Results at the registered nodes

Every generating history has h=1. T is the fitted effect statistic
max(0, 2[log L_free - log L_null]). Its quantiles are descriptive summaries
of the reference draws, not newly selected critical values.

| Setting (beta, mu, detection SD) | Valid / attempted | T <= 1e-6 | T 95th percentile | Mean worker seconds/history |
| --- | ---: | ---: | ---: | ---: |
| Interior (0, .0025, .2) | 999 / 999 | 508 | 2.709 | 5.555 |
| Lower corner (-2, .0005, 0) | 999 / 999 | 667 | 1.609 | 4.765 |
| Upper corner (2, .006, .4) | 999 / 999 | 440 | 2.811 | 3.978 |
| Opposite slope (-2, .006, .4) | 999 / 999 | 614 | 2.067 | 4.209 |

Both returned optimizer statuses were converged for every history. Null scores
dominated the true null point and free scores dominated fitted null scores
within the registered tolerance. These are numerical acceptance checks, not
proofs of global optimization. Individual starts need not all converge.

The observed invalid fraction is zero at each node. A pointwise exact 95%
binomial interval is **[0, .003686]** per node; it is neither a simultaneous
full-grid bound nor a guarantee that a future 999-reference table will contain
no failure. The all-or-nothing table rule remains: one invalid required
reference makes its table unavailable, and a case requiring it abstains.

Effect magnitudes remain poorly constrained in some null histories. At the
low-background corner, 73/999 fitted free effects hit the upper h=10 boundary,
while 667/999 hit h=1. The mean fitted effect there is 2.576 despite true h=1.
This is a descriptive boundary/weak-information pattern, not a calibrated
declaration rate or evidence that the threefold recovery question is solved.
No fit was altered in response.

![Null statistic distributions and component timings](../../../artifacts/goal058_execution/synthesis/null-statistics-and-cost.png)

Figure: Panel A shows empirical distributions of all finite T values; all
3,996 happen to meet the validity rules. Panel B shows mean generation, null-fit
and free-fit elapsed times. It excludes audit and parent/checkpoint overhead;
the table's worker measure also includes preparation and score calculation.
The [PDF](../../../artifacts/goal058_execution/synthesis/null-statistics-and-cost.pdf)
and [row table](../../../artifacts/goal058_execution/synthesis/reference-summary.csv)
are retained with the machine-readable
[summary](../../../artifacts/goal058_execution/synthesis/summary.json).

## Numerical and provenance evidence

The independent kernel checked true/null/free scores for **every history**.
Maximum absolute disagreement was **1.137e-12** log-likelihood units and
**2.728e-12** in T, against tolerances 1e-8 and 1e-6 respectively. All 3,996
addresses, 19,980 stage seeds, latent/observation identities, complete tables
and shared-table summaries passed. Twelve registered-address generator replays
matched bitwise; this is a same-generator determinism check.

Target qualification matched the existing four-model route's adjusted pair at
all four settings, verified the original K=131,072 arrival bank, and passed
an eight-history serialization/audit smoke test using a separate mechanical
root. Linux passed 209 tests, Ruff and strict mypy before the registered draw.
The source and all predecessor evidence remain preserved. The initial missing
public test fixture and its pre-launch repair are documented in the
[execution record](execution.md); no registered stream was previewed or redrawn.

## What the measured costs support

Production took **20.65 minutes** with sixteen workers; the four-worker audit
took **8.98 minutes**. Mean summed worker-wall workload was **4.627 seconds per
history**, ranging from 3.978 to 5.555 across node means. These are elapsed
workloads under the actual host load, not measured CPU times. The return
contains 8,004 production files and 66.87 MB, plus separate audit and receipts.

The earlier coarse-subset median unions, 268 using the old local-screen masks
and 163 using the descriptive R<=10 masks, are still **proxies**. Goal 058 did
not recalibrate the coarse screen or establish an attainable union size.

| Hypothetical nodes, 999 references/node | Same 16-fit / 4-audit allocation, h | Ideal 64 workers in both stages, h | That ideal arithmetic with 1.5 margin, h |
| --- | ---: | ---: | ---: |
| 163: old R<=10 proxy | 20.13 | 3.89 | 5.83 |
| 268: old local-mask proxy | 33.09 | 6.39 | 9.59 |
| 765: entire coarse effect-reference grid | 94.46 | 18.25 | 27.37 |

The first column scales the two observed stage durations by nodes/4. The
64-worker column scales their inferred work as
nodes*999*(16*production_seconds + 4*audit_seconds)/(3996*64*3600).
It assumes unconstrained linear scaling in both stages; it is **not** the
approved 16/4 pipeline at 64 workers or a demonstrated host capacity.
The margin is a planning allowance, not a confidence bound. These calculations
include pilot stage startup but omit transfer and later synthesis, and cannot
predict new-node costs or the new screen's retention. Generating all 765
effect tables is distinct from the much cheaper 765 x 99 pre-only screen.

## Next decision

The [next proposal](next-stage-proposal.md) recommends measuring the existing
local screen on the approved coarse support before purchasing a large effect
table. It keeps the deferred global-screen idea deferred. The sealed truth
distribution still needs explicit reconciliation with this support; beta=.6
is off-grid and a residual-field branch is outside the exact family.
Goal 058 tables remain design evidence; fresh confirmatory references after
the final truth law and procedure are frozen avoid reference-driven selection.
No large calibration, new map or sealed history has been generated.
