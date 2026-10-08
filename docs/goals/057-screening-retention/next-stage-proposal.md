# Next decision after Goal 057

4 October 2026. **Proposal for scientific review; no new campaign authorized.**
This advances Charter Pillar 4 calibration and Pillar 5 capstone preparation.
Goal 057 leaves a concrete choice: improve the screening statistic before
buying a large effect-reference table, or retain the present screen and budget
for its substantial unions. I recommend reviewing one fixed coarser global
screen first, while preserving Goal 057 as the comparison baseline.

## Cost of keeping the present screen

The table uses 999 full null references per required node, Goal 056's
median/maximum pair-plus-generation wall workloads of 3.939114/4.772396 seconds,
and a 1.5 scheduling margin. Values are ideal parallel projections, not CPU
measurements, runtime bounds or demonstrated Kunanyi throughput. Generation
still includes the earlier .104625-second filesystem-timestamp proxy. The
real effect path must simulate correlated spread and fit null/free models.

| Required nodes | 16 workers, hours: median / maximum workload | 64 workers, hours: median / maximum workload |
| ---: | ---: | ---: |
| 577: smallest observed union | 59.13 / 71.64 | 14.78 / 17.91 |
| 1,266: median observed union | 129.74 / 157.18 | 32.43 / 39.30 |
| 1,901: largest observed union | 194.81 / 236.02 | 48.70 / 59.01 |
| 3,645: whole grid | 373.53 / 452.55 | 93.38 / 113.14 |

These unions describe the old sixteen-fixture panel. A new capstone map may
have different retention and fit costs. Benchmark target-host throughput,
memory and I/O before a large table, including a Kunanyi array when its
multi-node scale is useful. Do not infer linear speedup from core counts or
choose a final cap from sixteen-worker convenience. Any eventual cap applies
to the complete required union before reference dispatch; exceeding it gives
abstention, never a favourable subset.

## Recommended next scientific tranche

The existing local statistic leaves 20–66% of retained points beyond the
descriptive R=10 marker. That warrants testing one statistic that can compare
a node with distant, better-fitting points. It does not justify dropping the
current high-R nodes or calling a future set calibrated before its reference
experiment is implemented and checked.

One concrete candidate for review is a fixed anchor set containing beta
{-2,-1,0,1,2}, all nine existing mu values and all five existing SD values:
225 anchors. At node nu, compare its score with the maximum over those anchors
and its original local neighbourhood. This is at most 232 point evaluations,
with duplicates evaluated once. Compute that same deterministic statistic for
the observation and each of 99 freshly addressed public references at nu;
retain the existing inclusive ranks, conservative ties and q>.01 rule.
The nodewise rank argument requires symmetry of the observation/reference
algorithm, not an exact continuous maximum. No chi-square approximation or
post-hoc R truncation enters this candidate. Its retained sets need not be
subsets of Goal 057's sets because its reference distribution also changes.

The rank justification is prospective: the statistic must be fixed before
the observations and references to which an inferential claim applies. Since
this candidate was motivated by the already-open panel, new reference streams
alone would not make the old-panel ranks nominally exact after that selection.
The next public panel comparison would therefore remain descriptive; future
calibration observations must be generated only after the method is frozen.

This anchor set is a proposal chosen after the public pilot, not a registered
or adopted method. Review its computational and inferential tradeoff with
Fable before Barry's decision. Freeze exactly one agreed statistic and its
fresh streams before another draw. Use the existing open panel for descriptive
retention, keep Goal 057 unchanged and report all candidate sizes, all unions,
truth-point retention, numerical checks and costs even if compression fails.
Do not search several anchor sets and report only the best.

For cost context, Goal 057 made 2,292,543 scalar-equivalent reference point
evaluations in 344.70 summed worker-wall seconds. The 232-point bound gives
83,718,360 evaluations for the same 360,855 reference histories. Scaling that
measured scoring workload gives about 26.2 minutes on eight workers before
generation, preparation, orchestration, checking and margin. This is a rough
same-host projection; cache behaviour and throughput need a mechanical target
check. A proposed ceiling is eight workers, 16 GiB aggregate RSS and one hour,
with stop-and-preserve on any numerical or resource failure and no automatic
retry. If qualification cannot support that envelope, return the measured
cost for a resource decision before the registered draw.

The rank construction continues to concern the exact family and on-grid
nuisance values. A public redesign pilot cannot establish empirical operating
rates, solve off-grid robustness, qualify a new map or authorize sealed cases.
No effect estimate or truth-based correction changes in this proposal.

## Effect micro-pilot remains a separate prerequisite

The existing four-node micro-pilot remains useful for the full effect path:
(beta,mu,SD)=(0,.0025,.2), (-2,.0005,0), (2,.006,.4), (-2,.006,.4), all h=1;
999 full histories per node, 3,996 total. The current projection is .410–.497
hours at sixteen workers including the same margin, with a proposed ceiling
of sixteen workers, 48 GiB and two hours. It would measure generation,
null/free fitting, failure propagation, serialization and shared-table use.
Its nodes must stay fixed and it would preserve every failed fit as abstention.
It would not measure the final decision's power or false-declaration rate.

I recommend the screen comparison before large calibration; the small effect
micro-pilot can follow or be independently approved without claiming that it
settles the retained-union cost. Operating-rate design, new-map numerical
qualification and sealed generation still require their own scientific
decisions. The revised screen and effect micro-pilot have not been run.
