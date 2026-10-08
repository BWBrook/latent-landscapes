# Goal 057: screening is cheap, but leaves a large effect-reference workload

4 October 2026 (Hobart). The approved public pilot is complete. The registered
screen retains 420–990 of 3,645 nuisance nodes per fixture and 577–1,901 nodes
across a union of four fixtures. All sixteen known true nodes are retained.
The median union is 1,266 nodes: about 32–39 hours at 64 workers under the
qualified assumptions below. This is a descriptive fixed-panel result, not
an estimate of screen coverage, false-declaration probability or power.

The [registration](registration-2026-10-04.md), [execution record](execution.md),
[independent review](independent-review.md), [figure captions](figure-captions.md)
and [costed recommendation](next-stage-proposal.md) complete this tranche.
The accepted machine-readable analysis is
[synthesis-v3](../../../artifacts/goal057_execution/synthesis-v3/report.json).
Earlier synthesis attempts remain preserved with their documented cost and
plotting errors; they are not the accepted analysis.

## Retention and the global likelihood surface

Exactly 99 pre-only references at each node give 360,855 histories. The
inclusive rank, tie tolerance and q>.01 rule remain unchanged. The sixteen
Goal 056 fixtures are unchanged. Their candidate counts, in case order 0–15,
are 805, 444, 562, 990, 522, 518, 549, 420, 574, 525, 524, 505, 528, 443, 592
and 572. Their true-node q values range from .03 to 1.00. See the complete
[case table](../../../artifacts/goal057_execution/synthesis-v3/case_summary.csv).

| Four-fixture union summary | Nuisance nodes |
| --- | ---: |
| Minimum | 577 |
| 10th percentile | 1,092 |
| Median | 1,266 |
| 90th percentile | 1,691 |
| Maximum | 1,901 |

All 1,820 combinations are included in the
[union table](../../../artifacts/goal057_execution/synthesis-v3/four_case_unions.csv).
They overlap within a fixed panel; they are not independent calibration
replicates or a guaranteed forecast for four future cases. The observed
minimum already exceeds a 500-node cap, but this does not choose a resource
cap for a future map.

The prespecified global contrast is R=2(max_grid ell_pre-ell_pre). Depending
on the fixture, 20.0–65.9% of retained nodes have R>10; in twelve of sixteen
fixtures the retained median R exceeds ten. The largest retained R is 109.46.
The full-grid R<=10 regions contain 183–555 nodes. These comparisons show that
the local one-step screen retains many points well below the best grid score,
supporting investigation of a global or coarser global statistic. They do not
establish identifiability, prescribe an R cutoff, or prove that another
calibrated screen will compress the sets substantially. Ten remains a
descriptive marker without chi-square or confidence-set meaning. No node was
removed using this diagnostic.

## Reused-reference nuisance errors

All 792 five-start fits returned converged estimates. All finite returned
estimates enter the summaries; none was discarded, redrawn or refitted. The
following intervals quantify Monte Carlo uncertainty in the mean log error
from 99 histories per node. They are pointwise descriptive intervals, not
simultaneous tests or intervals for ecological parameters.

| Node | beta | mu | True SD | Mean log(mu-hat/mu) | Approximate 95% MC interval | Mean SD error | SD-hat=0, of 99 |
| ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 1810 | 0 | .0016 | 0 | -.0786 | [-.1519, -.0052] | .02144 | 50 |
| 1812 | 0 | .0016 | .2 | .0160 | [-.0540, .0860] | .00151 | 0 |
| 1820 | 0 | .0025 | 0 | .0311 | [-.0322, .0944] | .02460 | 47 |
| 1822 | 0 | .0025 | .2 | .0003 | [-.0688, .0694] | -.00026 | 0 |
| 2350 | .6 | .0016 | 0 | .0255 | [-.0392, .0901] | .01813 | 51 |
| 2352 | .6 | .0016 | .2 | -.0438 | [-.1205, .0329] | .00107 | 0 |
| 2360 | .6 | .0025 | 0 | -.0308 | [-.0870, .0255] | .01815 | 51 |
| 2362 | .6 | .0025 | .2 | -.0472 | [-.1178, .0234] | -.00394 | 0 |

The balanced eight-node mean log error is -.01594, MCSE .01216, with approximate
95% MC interval [-.03982, .00793]. Mean beta error is .00496, interval
[-.02901, .03894]. This mixture does not estimate a common bias across all
nuisance values. Medians, per-node MCSEs, all boundary counts and the 3-by-3
parameter-error covariance matrices are retained in the
[report](../../../artifacts/goal057_execution/synthesis-v3/report.json) and
[node table](../../../artifacts/goal057_execution/synthesis-v3/diagnostic_node_summary.csv).

At true SD=0, fitted SD has a positive mean .0181–.0246 while 47.5–51.5% of
estimates lie on zero. This is consistent with finite-sample behaviour at a
nonnegative boundary. At true SD=.2, mean errors range from -.00394 to .00151.
Independent score agreement rules out the checked likelihood discrepancy as
an explanation; convergence and true-point dominance do not prove every fit
is the exact global maximum. No truth-based correction was applied.

To address the earlier suggestion of approximately 20% upward background error
on its own scale, a separately labelled
[post-run arithmetic supplement](../../../artifacts/goal057_execution/supplementary-arithmetic-mu.json)
computes mu-hat/mu-1 from the same 792 estimates. Its equal-node mean is
**+3.95%**, MCSE 1.18 percentage points, with approximate 95% MC interval
**[+1.64%, +6.26%]**. Individual node means range from -1.53% to +8.22%.
This supplement was chosen after viewing results and is not the registered
primary diagnostic. The arithmetic and log means answer different questions;
neither supports a general 20% upward shift, and neither establishes that the
estimator is unbiased at every node. These pre-only results cannot determine
the full-data effect estimator's repeated-sampling bias or settle the variable
threefold estimates in Goal 056.

## Resource use and verification

The eight-worker run completed in **397.28 seconds (6 min 37 s)** under the
one-hour ceiling, with sampled peak aggregate process-group RSS **.986 GiB**
under the 16 GiB cap. All 360,855 references and 792 diagnostic fits are present.
The runner's timed body took 371.03 s; the supervisor also includes startup and
full seed-ledger verification. The run payload is 18,043,876 bytes across 3,657
files; five accompanying launcher/log/source receipts bring the verified return
to 3,662 files. Workload timers and hashes are in the execution record.

Independent reconstruction checked all 58,320 fixture scores, local contrasts,
ranks and candidate indicators, all 1,820 unions, all 792 diagnostic reference
contrasts and true/fitted scores, and 21 exact generator replays. Candidate
sets and unions match exactly; largest independent fixture-score difference
is 2.61e-12 nats. All 1,082,565 seed-ledger rows were checked. Source, inputs,
returned outputs and all preserved Goal 056 bindings pass hash verification.

Two technical deviations remain explicit. Development checks previewed 99
unique registered histories at node 0 and a prefix of one other stream before
the final freeze; no production addresses or methods were changed in response.
The executor's repetition counts could not be independently recovered because
the development logs were not retained. Separately, the first synthesis used
99 rather than 999 in future-effect cost multiplication, and its heatmap
transposed the axes. Postprocessing repairs preserved the original outputs and
left every generated history, fit, score, rank and retained set unchanged.
The campaign must not be represented as wholly frozen before any reference
preview.

## Scientific decision

The local screen is computationally practical, but its retained unions leave
a substantial full-effect reference workload. A separately reviewed comparison
with one frozen global or coarser global screen is the next useful scientific
decision. The [proposal](next-stage-proposal.md) costs that route and the
previously proposed four-node effect micro-pilot without authorizing either.
The union-cap and failed-fit abstention rules are implemented and mechanically
tested. Large effect calibration, operating-rate estimation, new-map
qualification and sealed generation remain separate work. This tranche makes
no recovery, coverage, power or new causal-identification claim.
