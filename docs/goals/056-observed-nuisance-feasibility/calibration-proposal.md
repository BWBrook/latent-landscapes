# Proposed next decision: measure screening retention before effect calibration

3 October 2026; revised 4 October after Fable's messages 875–876.
**Ready for Barry's scientific decision.** No reference campaign or sealed
generation is authorized by this document. The revision adds two diagnostics
and resource/custody clarifications without changing the proposed screen or
the frozen Goal 056 results.

The observed-data likelihood is computationally feasible on the existing
laboratory map. The outstanding affordability question is how many nuisance
nodes the pre-invasion screen retains, especially in the union of four cases.
A valid screen can retain many nodes. The next useful tranche is a public
screen-retention pilot, followed, if warranted, by a small end-to-end effect
pilot. Neither should be described as full empirical calibration.

## Decision rule and its domain

Retain the registered exact family and parameter bounds. The nuisance grid
has 3,645 nodes: 81 beta values in [-2,2], nine whole-map mean hazards and five
site-level detection SDs. At each node, the pre-only statistic compares its
log likelihood with the maximum among that node and its immediate neighbours
along each of the three axes, at most seven evaluations. Exactly 99 independent
pre-only references give the inclusive rank q=(1+# reference statistics at
least the observed statistic)/100, with the fixed conservative tie tolerance.
Retain C={nodes:q>.01}.

At a retained node, exactly 999 independent full null histories give the
inclusive plus-one effect rank p_nu. Fit observations and references with the
same frozen adjusted numerical algorithm and use
p_BB=min(1,.01+max_C p_nu), declaring only when p_BB<=.05. Full references
must simulate correlated predator spread. The sitewise composite score does
not justify replacing that generator with independent site arrivals.

For a true exact-family on-grid node nu0, the screen excludes nu0 with
probability at most .01, while its full-data rank is at most .04 with
probability at most .04. Declaration implies at least one of those events, so
its probability is at most .05. This union bound does not require independence
between screening and the observed effect statistic. It averages over reference
and observation generation, conditional on the fixed map, sampling design,
empirical bank and numerical procedure. It does not guarantee size conditional
on a particular realized reference table. It does not cover off-grid nuisance,
residual spatial fields, an unknown mean detection probability, missing visits,
temporal changes, magnitude accuracy or confidence coverage. Four casewise 5%
tests do not control the probability of any false declaration across four cases
at 5%.

Empty candidate sets, missing required tables, non-finite scores, any failed
required observed/reference fit, or a predeclared resource-cap excess must
produce p=1 and abstention. The current arithmetic prototype has a per-case
candidate cap; a future caller must add a single cap on the four-case **union**
before building tables. A finite clamped statistic from a failed fit must not
be passed to the combiner as a valid result. Preserve the failure status, and
never discard or redraw a failed reference.

For future sealed work, freeze node-addressed stage/reference RNG streams
before evaluation data are generated. For the already-open fixtures, freeze
those streams before scoring them.
Lazy construction of a required effect table is permitted from those assigned
streams; adaptive reference counts, favourable subsets of C, retries with new
seeds and outcome-dependent stopping are excluded. These constraints preserve
the fixed rank experiment.

## Measured cost and unresolved retention

The sixteen histories gave a median adjusted-null/adjusted-free pair cost plus
generation proxy of 3.9391 seconds, with observed maximum 4.7724 seconds. The
generation contribution is .104625 seconds/history from filesystem timestamps,
not a flushed generation timer. The fit timings are wall workloads measured
under concurrent execution, not CPU-time measurements or a hard worst-case
bound. The table uses 999 references/node and a 1.5 scheduling margin with
ideal division across workers; it omits unmeasured campaign orchestration and
additional scientific evaluation. Recheck throughput on the chosen host.

| Required union nodes | 16 workers, hours: median / maximum-based | 64 workers, hours: median / maximum-based |
| ---: | ---: | ---: |
| 1 | 0.102 / 0.124 | 0.026 / 0.031 |
| 10 | 1.025 / 1.242 | 0.256 / 0.310 |
| 25 | 2.562 / 3.104 | 0.640 / 0.776 |
| 50 | 5.124 / 6.208 | 1.281 / 1.552 |
| 100 | 10.248 / 12.416 | 2.562 / 3.104 |
| 250 | 25.620 / 31.039 | 6.405 / 7.760 |
| 500 | 51.239 / 62.078 | 12.810 / 15.520 |
| 3,645 | 373.534 / 452.552 | 93.384 / 113.138 |

The worst grid requires 3,641,355 full reference histories. Screening requires
360,855 pre-only histories and at most 2,525,985 scalar point evaluations.
At the qualified .855994 ms/pre-only point, those evaluations alone cost
approximately 2,162 serial seconds (36.0 minutes) for the reference stage.
For the proposed sixteen-fixture pilot, cache one complete pre-only grid
surface per fixture and derive all local contrasts from it. That adds 58,320
point evaluations, giving at most 2,584,305 evaluations or about 2,212 serial
seconds (36.9 minutes) across reference and observed-fixture scoring. This
reuse is exact because each node has one fixed point likelihood per fixture.
Generation, observation preparation, scheduling and serialization remain
unmeasured. The bound of
seven evaluations is a count bound, not a runtime guarantee. No retained-set
size or operating error rate was measured in Goal 056.

## Proposed bounded public pilot

First implement and test the union-cap and failed-fit rules, keeping the
likelihood and main fitter fixed. Use only the existing public map, sampling
layout and open sixteen histories. Generate exactly 99 pre-only references at
each of the 3,645 nodes, with all seeds frozen beforehand and separate from the
open panel. Stream or chunk generation; persist scalar screening statistics,
seed identities and receipts, rather than all raw simulated histories.

Apply the complete screen to the existing sixteen fixtures. Report each
candidate-set size, whether its known true node is retained as a descriptive
check, and all 1,820 unions of four distinct fixtures. These overlapping unions
are an exhaustive description of this panel, not 1,820 independent replicates
or a forecast guaranteed for four future cases. Record actual generation,
preparation, scoring and serialization times, peak RSS and output size.
Translate the observed sizes into effect-campaign costs, retaining worst-grid
costs. The fixed-map pilot cannot select or validate a resource cap for a new
capstone map; that map needs its own public retention/resource check or a
conservative resource-based cap with mandatory abstention. Do not report false-declaration rates, power or screen coverage from
these sixteen cases.

### Added diagnostic: pre-only nuisance-estimator error

Reuse the same 99 screening references at each of the eight unique nuisance
nodes represented in the open panel: mu={.0016,.0025}, beta={0,.6}, SD={0,.2}.
Fit the frozen pre-only model to those **792 references**, without additional
generated histories. The h=1 and h=3 labels do not require duplicated references:
their pre-invasion laws are identical at a given nuisance node.

Report each node separately: mean and median log(mu-hat/mu), beta and detection-SD
errors, Monte Carlo standard errors/intervals, boundary frequencies, optimizer
failures and the covariance of parameter errors. Keep SD-zero boundary nodes
visible. An equal-weight pooled summary describes the balanced eight-node
mixture; it is not evidence of a common bias at every nuisance value. Failed
fits remain in the accounting; do not quietly condition the summary on success.

For each generated reference, compare the production pre-only log likelihood
at the true and fitted parameter points against an independent analytic
pre-only calculation. Its cohort-survival and shared-Beta count emissions must
not call the production scorer. Retain the existing 1e-8 absolute whole-history
score tolerance. Flag a fitted objective more than 1e-6 below the value at the
true point as a numerical failure rather than silently improving that fit.
These checks require no new histories or full arrival bank traversal.

This experiment estimates finite-sample behavior at the eight nodes. Agreement
of likelihoods with persistent estimation error supports a finite-sample or
boundary explanation and a need for further diagnosis; disagreement locates an
implementation problem. Ninety-nine replicates/node cannot settle small bias
at every node, and the pre-only results cannot determine the full-data effect
estimator's repeated-sampling bias. Do not apply a truth-based correction or
retune the estimator/screen during the pilot.

The observed pre-only fit time has median .260364 s, mean .256320 s and maximum
.405366 s. The 792-fit addition therefore projects to about 203–321 serial
wall-workload seconds (3.4–5.4 minutes), before its independent checks and
orchestration. This is a timing projection, not a three-minute guarantee.
Keep the complete pilot within the proposed one-hour envelope.

### Added diagnostic: retained nodes on the global grid surface

For each of the sixteen cached pre-only surfaces, compute
R(nu)=2[max_grid ell_pre - ell_pre(nu)] at every grid node and overlay the
original retained set C. Report |C|, the median/upper quantiles/maximum of R
inside C, and the count and fraction with R>10, alongside the visual overlay.
Also report the number of grid nodes with R<=10 for context. Ten is a
prespecified descriptive support-scale marker, not a calibrated cutoff,
chi-square rule, p-value or confidence threshold. Computing this overlay
requires no extra likelihood evaluations; plotting/reporting still has a cost.

Many high-R retained nodes would show that the local one-step screen leaves
room for a global or coarser-global statistic to compress candidate sets in
these histories. Concentration near the peak would instead show that C follows
the realized likelihood-support region; it would not prove that no other valid
statistic could make C smaller. This diagnostic does not establish
identifiability or choose a new statistic by itself. Do not remove nodes using
R, change q, redraw references or recalibrate the same pilot adaptively. Any
screen redesign is a separately frozen and qualified method for later work.

### Pilot execution envelope

A proposed execution envelope is eight workers, one BLAS thread each, 16 GiB
RSS and one hour, with a small deterministic implementation check before the
registered reference draw. Stop and preserve any resource or numerical failure;
no seed replacement or extra reference counts. This envelope is a proposed
cap, not a predicted runtime. The screen pilot is informative even if most
nodes remain and the effect stage is unaffordable.

Before a large effect table, a separate public micro-pilot should run the
complete 999-reference effect path at one to four predeclared boundary/interior
nodes. For a concrete four-node option, use (beta,mu,SD) =
(0,.0025,.2), (-2,.0005,0), (2,.006,.4), and (-2,.006,.4), all at h=1.
Keep those nodes fixed regardless of screening results. It would comprise
3,996 full histories, cost about .410–.497 hours at sixteen workers under the
current extrapolation, and test actual serialization, numerical failures,
shared table loading and resource use. A proposed cap is sixteen workers,
48 GiB and two hours. This is a separately approved tranche; the screen alone
does not authorize it or establish performance at all nuisance nodes.

### Resource decision for a later effect campaign

Do not set the final union cap from sixteen-worker convenience alone. The
existing table already includes ideal 64-worker scenarios: 250 required nodes
project to 6.40–7.76 hours, and 500 to 12.81–15.52 hours, with the same 1.5 margin.
For 500 nodes the underlying summed fit-wall surrogate is about 547–662 hours
before that margin. This is work accounting, not measured CPU consumption.

The current compute guidance supports deep-server for ordinary 16–64-worker
single-host work and Kunanyi for qualified PBS arrays or ensembles at genuine
multi-node scale. Keep this short development pilot on an appropriate modest
resource. For a later large effect campaign, benchmark target-node throughput
and measure memory/I/O, then cost deep-server and a Kunanyi array using the
actual available allocation, queue and transfer overhead. No Kunanyi
availability or cross-machine linear speedup has been measured here. Routine
resource selection remains delegated; this proposal does not request a new
resource-permission gate.

Freeze an affordable **four-case union** cap from that resource decision before
any sealed observations. The future four-case caller must abstain if it exceeds that cap.
A larger operating-rate study would separately specify independent null and
alternative evaluation histories, Monte Carlo precision and reference-table
uncertainty. A finite-grid rank proof, a numerically correct implementation and
an empirical operating-rate study are different kinds of evidence.

## Sealed-case custody

Barry has approved four future histories and simple protection against
accidental exposure. Fable supplied the [key-custody and staged-release
instructions](../../advisor/capstone-key-custody.md). Barry reported creating
the key on 4 October and supplied the public recipient already registered
there. Astra verified that the public string matches and that age accepts it
for encryption; this does not verify Barry's private-key backup or decryption
self-test. Neither was accessed. Barry retains the passphrase and performs
both later releases. No capstone truth, generator seed or sealed observation
has been generated. The strict-private-environment proposal from Goal 055 is
superseded by Barry's chosen custody arrangement.
A new capstone map will require its own bank/numerical qualification and
resource check; the timings and error-control conditioning here refer to the
existing fixed map.
