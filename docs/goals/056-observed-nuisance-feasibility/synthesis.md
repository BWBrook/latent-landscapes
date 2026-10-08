# Goal 056: observed-nuisance likelihood is feasible; calibration cost remains conditional

3 October 2026 (Hobart). The approved feasibility study is complete. It advances
Charter Pillar 4 calibration and Pillar 5 preparation by implementing the changed
observation model, testing it on the registered open sixteen-history panel and
costing a defensible next calibration route. It does not close either pillar.

The new likelihood accommodates continuous prey loss from day -60, unknown
whole-map mean background hazard, an estimated spatial background coefficient
and persistent site-level Beta detection heterogeneity. All 64 main model fits,
16 pre-only fits and 7,088 diagnostic profile nodes converged. The independent
raw-bank replay agrees with every saved main and holdout score. Magnitude
estimates still vary substantially. The next scientific decision is whether to
run the [public screening-retention pilot](calibration-proposal.md), before a
large effect-reference campaign or sealed observations.

## Numerical evidence and preserved repair

The full K131072 empirical arrival bank plus its seven pseudo-arrivals was
qualified at 17 domain-edge/interior points and four mechanical observation
patterns. Maximum whole-training error was 2.274e-12 against the direct bank,
below the frozen 1e-8 tolerance; all 32 repeated mechanical fits converged with
exactly repeated objectives. The continuous parameter-box certificate gives
x<=4.17763332<5 for the positive Taylor transform. The original Linux gates
passed 173 tests, Ruff and mypy.

The panel generated its sixteen histories exactly once and saved all 64 main
fits. Four beta-profile continuations failed because exp(log(10)) rounded to
10.000000000000002. The separately frozen [repair](profile-recovery-amendment.md)
snaps profile seeds within eight ULP of a declared bound and otherwise retains
validation. An AST comparison verifies that only this profile helper changed;
likelihood, generator and main fitting procedure did not. Linux gates then
passed 174 tests. Recovery copied all observations, all sixteen main-fit files
and the twelve complete diagnostic cells byte-for-byte. Only the four missing
diagnostic cells were recomputed; the fixed 1,350-point lattice ran once.

Every one of the 64 main maxima dominates its applicable lattice and converged
profile values within the registered 1e-6 tolerance. The largest
profile-minus-main discrepancy is 2.96e-12; the largest grid-minus-main gap is
-0.004059. All 7,088 profile nodes report convergence. These lower-bound checks
do not certify global maxima. The fixed numerical algorithm defines the
statistic; diagnostic values never replaced its saved main fits.

An independent scorer, using direct empirical-arrival sums and an independently
coded shared-Beta emission, replayed all 64 fitted points without importing the
production likelihood or fitter. Maximum absolute differences were:

| Quantity | Maximum discrepancy |
| --- | ---: |
| 120-site training total | 6.82e-13 nats |
| 40-site conditional-prey holdout total | 1.14e-13 nats |
| Individual held-out conditional-prey score | 2.66e-14 nats |
| Nested effect statistic | 1.36e-12 |
| Predator marginal / arrival-category mass | 0 |

The first audit reported a schema mismatch because the recovered numerical rows
contained an additional profile-source identity. Its direct numerical and
provenance checks had passed. Adding that identity to the independent row
reconstruction produced a fully passing second audit, with both attempts
preserved. [Execution](execution.md), [independent review](final-review.md) and
the [completion check](../../../artifacts/goal056_execution/completed-check.json)
index the source and output identities.

## What the sixteen histories show

This is one independent history per registered cell, crossing h={1,3},
mu={.0016,.0025}, beta={0,.6}, and detection SD={0,.2}. All training used only
the 120 training sites; conditional prey scoring at the 40 cluster-isolated
holdout sites occurred at the fixed fitted parameters. Neither true nuisance
values nor latent states were supplied to the fitter. Mean prey and predator detection remain fixed at .65, with two visits per
occasion and no false positives. This single-map fixture
cannot estimate size, power, coverage, general recovery or general identifiability.

For adjusted free-h fits, five of eight null histories reach the h=1 boundary.
The other estimates are 1.123, 1.159 and 3.355. The last is cell 1, whose mean
hazard estimate is .000943 rather than .0016; its effect statistic is 2.589.
It has not been assigned a calibrated declaration. The h profile remains broad,
illustrating the trade-off between effect and background loss even with the
added pre-invasion observations.

At true h=3, adjusted estimates span 1.717–4.020; six of eight are below 3,
and their median is 2.005. The constant free-h comparator spans 1.765–6.061.
Its median is 2.676. Mean absolute log error in these eight particular histories
is .361 for the adjusted model and .302 for the constant model. These descriptive
values do not demonstrate a population advantage or failure for either model.
They show why a completed likelihood implementation is not a magnitude-recovery
claim.

| Cell | True mu | True beta | True SD | Adjusted h estimate | Local log-h curvature scale |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | .0016 | 0 | 0 | 1.878 | .4273 |
| 9 | .0016 | 0 | .2 | 3.386 | .4856 |
| 10 | .0016 | .6 | 0 | 1.717 | .3872 |
| 11 | .0016 | .6 | .2 | 4.020 | .3694 |
| 12 | .0025 | 0 | 0 | 2.009 | .3994 |
| 13 | .0025 | 0 | .2 | 1.862 | .4748 |
| 14 | .0025 | .6 | 0 | 2.001 | .3388 |
| 15 | .0025 | .6 | .2 | 2.550 | .3744 |

The last column is 1/sqrt(-ell''(log h)) at a resolved interior profile maximum.
Three of eight values fall in Fable's forecast .40–.60 range, while five lie
below it. Because this is a sitewise composite likelihood under spatial
spread, this curvature scale is not a validated sampling standard error,
Godambe estimate or confidence interval. Smaller values cannot be claimed as
better uncertainty calibration. The adjusted null profiles at the h boundary
have no reported interior curvature scale.

At true detection SD .2, adjusted estimates range .1511–.2216. Seven of eight
absolute errors are at most .03; cell 3 misses at -.0489. At true SD zero,
five of eight adjusted free-h fits are exactly on the SD boundary and the
remaining estimates are .0291, .0336 and .0498. Thus the detection forecast
largely holds in this small fixture, while a replicated adequacy or recovery
claim remains untested. All pre-only nuisance fits converged; their individual
estimates are retained in the output table, not treated as truth.

The adjusted-minus-constant free-h held-out conditional-prey advantage is
positive in eleven of sixteen histories, but varies from -3.803 to +2.037 nats
across 40 sites. Its sum is +1.878 nats over all sixteen histories: an average
of +.1174 nats/history, or +.00293 nats/site/history. Gains are mixed under both
background settings. These descriptive scores provide no decisive model
comparison and do not inform training or a calibrated effect decision.

Across all 64 model records, 41 h-lower flags include the 32 structurally fixed
null fits. Only nine of the 32 free-h fits lie on that boundary. Twenty records
have SD=0, including ten free-h records. There are no fitted beta, mu or h-upper
boundary flags. Boundary solutions are reported outcomes, not optimizer
failures. The [64 model rows](../../../artifacts/goal056_execution/synthesis/all64_model_rows.csv),
[16 pre-only rows](../../../artifacts/goal056_execution/synthesis/preonly16.csv),
[48 profile diagnostics](../../../artifacts/goal056_execution/synthesis/profile_diagnostics.csv)
and [figures/captions](figure-captions.md) retain the complete cellwise evidence.

## Costs and next decision

Full-bank qualification took 132.55 seconds, including 30.54 seconds to load
and compress the bank. The interrupted original panel took 149.15 seconds;
profile-only recovery and the first coarse-grid audit took 108.31 seconds.
The total panel cost is therefore 257.46 seconds, including work lost at the
four interrupted cells. Peak summed RSS was 5.76 GB in the sixteen-worker
original panel and 1.42 GB in the four-worker recovery. The two independent
audits added 17.61 and 18.41 seconds. These are recorded execution-phase wall
times; setup, code development, testing and plotting are not included in their
sum.

An adjusted null/free pair plus the per-history generation proxy took a median
3.939 seconds and observed maximum 4.772 seconds. Generation itself is a
filesystem-timestamp proxy because the failed run did not flush its timer.
Using 999 references per required nuisance node, ideal sixteen-worker division
and a 1.5 scheduling margin gives 2.56–3.10 hours for 25 nodes, 10.25–12.42 hours
for 100 nodes and 15.6–18.9 days for all 3,645 nodes. These are planning
extrapolations from this map, not measured reference-campaign runtimes.
Retention is unknown, and a four-case union can be much larger than any one
case's candidate set.

The [calibration proposal](calibration-proposal.md) supplies a finite-grid
casewise rank argument, explicit conservative failure rules, cost scenarios
and a concrete public screen-retention pilot. It then proposes a separately
approved small effect-reference pilot before a large table. Neither has run.
A new capstone map requires its own qualification and retention/resource check,
or a conservative resource cap fixed before sealed observations with mandatory
abstention. Four future histories and password-manager private-key custody are
approved in principle; no sealed histories or key material were generated.

The independent review accepts this feasibility closeout and the bounded next
proposal. The next owner is Fable for critique, followed by Barry's scientific
decision. Goal 055 and its 97 bound files remain unchanged. No commit, push or
publication occurred.
