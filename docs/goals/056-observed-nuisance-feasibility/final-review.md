# Goal 056 independent final review

3 October 2026. Independent result review of the observed-nuisance feasibility
study. This review does not authorize a reference campaign, sealed histories,
or a change to the registered statistic.

## Review targets and gates

The scientific target is feasibility of the observed-data likelihood and its
fixed numerical fitter on sixteen openly labelled development histories. The
effect estimand remains the post-arrival prey-loss hazard multiplier `h`. The
prediction target is conditional prey log score at the 40 cluster-isolated
holdout sites after fitting on the 120 training sites. The panel cannot estimate
size, power, coverage, general recovery, or performance on a future map.

The independent replay uses the actual K131072 arrival bank plus one registered
pseudo-arrival in each of seven arrival categories. It reconstructs whole-map
hazard normalization, predator marginalization, continuous survival from day
-60, and the analytic site-shared Beta detection probability with binomial
multiplicities. It does not call the production compressed-moment likelihood,
emission helpers, point scorer, or fitter. The prespecified acceptance limits
are `1e-8` maximum absolute difference for fitted training totals and held-out
conditional-prey totals, and `1e-6` for the two nested effect statistics.

The review also replays the 1,350-point/profile lower-bound audit from raw JSON,
checks every completed-file hash, binds the panel to the passed qualification
and 98-file source manifest, and verifies the observation/evaluator hashes in
the open-panel manifest.

## Qualification evidence

The Linux full-bank qualification passed before the panel. Its independent
verification records 17 parameter points, 32 repeated mechanical model fits,
zero repeat-fit log-likelihood discrepancy, maximum absolute full-bank errors
of approximately `9.17e-13` sitewise, `2.27e-12` on training totals and
`9.09e-13` on holdout totals, plus the continuous hazard certificate
`x<=4.177633319818649<5`. Qualification and its verification are bound to the
same 98-source manifest.

## Diagnostic recovery provenance

The first panel attempt exited 1 after 149.150845 seconds. It had generated all
sixteen histories, saved all 64 converged main fits and all sixteen pre-only
fits, and completed twelve cells. Cells 1, 9, 11 and 15 stopped in beta-profile
continuation because decoding the registered upper bound produced
`10.000000000000002` and the next seed validator rejected it as greater than
10. This happened outside the observation generator, likelihood and main-fit
calculation.

The recovery source changes only `_profile_starts` and its regression test. It
snaps values within eight floating-point ULPs of a physical bound to that bound
and continues to reject larger violations. An AST comparison confirms that
every other node in the fitter, including the main-fit algorithm, is identical
to the qualified source. The recovery snapshot passed 174 Linux tests, Ruff and
mypy before launch. Its manifest binds the original source and resource
receipts, the repair patch and AST check, the recovery wrapper, the amended
source, and the recovery protocol. The protocol copies the observations,
evaluator, sixteen main-fit files and twelve completed cells byte-for-byte;
reuses the four saved main/pre-only payloads; computes only the missing
profiles and fixed-fit holdout scores; and then runs the registered coarse
lattice once. The independent audit treats any identity mismatch as failure.

## Panel and independent replay

The recovered panel and independent replay pass. All 64 main fits converged.
All 48 conditional profiles, comprising 7,088 profile-grid nodes, had zero failed
nodes. Every main fit exceeded its applicable 1,350-point lattice lower bound;
the largest lattice-minus-main difference was `-0.00405881`. The largest
profile-minus-main difference was `2.96e-12`, consistent with floating-point
re-evaluation. No diagnostic value replaced a main fit.

The independent direct-bank replay passed all tolerances across the 64 fixed
fits. Maximum absolute differences were `6.82e-13` for training totals,
`1.14e-13` for holdout conditional-prey totals, `2.66e-14` for individual
holdout sites and `1.36e-12` for the effect statistics. Predator log marginals
and category masses agreed exactly. All qualification, source-chain,
completed-file, original-file preservation, recovered-payload and numerical
row checks passed. The first independent-audit wrapper preserved a failed
receipt after its comparator omitted the recovery-only `profile_source_id`
field; its direct scores had already passed. Adding that field to the audit row
and a tamper-detection fixture produced the passing v2 receipt without changing
any scientific source or panel output.
The passing independent-audit receipt has SHA-256
`90ab4ef25b01d4c369551878e9abd00c5291e76d719f97ba07d9f38a6ab71445`;
the recovered `completed.json` hash is
`c5e6167b0402d6ca6bd29204db3ff62f6397617ab4976f72890af936c4002171`.

The sixteen cells show usable effect information and important weak-information
cases. In the adjusted model, the eight `h=3` cells had fitted `h` from 1.717 to
4.020 (median 2.005, descriptive bias -0.572, RMSE 0.973), and all effect
statistics were positive, from 1.487 to 12.613. The eight `h=1` cells had median
fitted `h=1`, but ranged to 3.355; five were on the lower bound and one weak,
shallow profile produced `T=2.589`. Their statistic range, 0 to 2.589, overlaps
the `h=3` range, so the fixture does not supply an uncalibrated decision
threshold.

Every interior h profile had one conditional grid maximum; lower-bound fits
were monotone away from `h=1`. The shallowest adjusted profile spanned only
1.407 log-likelihood units over the full `h` domain. At true `h=3`, all eight
adjusted profiles had negative local curvature. Their `SElogh` scales were
0.339--0.486 (median 0.393), with three of eight inside the forecast 0.40--0.60
and the other five below it. Curvature was absent for the five adjusted
lower-bound h fits, as it should be. All adjusted beta estimates were interior,
and both beta-profile endpoints lay at least 7.81 log-likelihood units below
their grid maxima. Among free-h fits, h-lower flags occurred in four constant
and five adjusted fits, all at true `h=1`; detection-SD-lower flags occurred in
five fits of each model, all at true SD zero. The 32 h-lower flags in the two
null models are fixed constraints and are not boundary-estimation evidence.

For true detection SD 0.20, seven of eight adjusted estimates were within the
forecast absolute error 0.03; the median absolute error was 0.0129 and the
maximum was 0.0489. Adjusted beta error had MAE 0.212. Mean-hazard error had
MAE 0.000571,
and adjusted h and mean-hazard errors had descriptive correlation -0.72. That
trade-off, the large null-cell h estimate, and the downward h bias at `h=3`
show that magnitude remains weakly constrained in some of these histories even
in the exact family. All sixteen pre-only fits converged, but their beta and
mean-hazard MAEs were 0.291 and 0.000737; screen retention may therefore be
broad and remains an empirical question.

Held-out prediction gives mixed support. Against the adjusted `h=1` fit, the
adjusted free-h fit improved conditional-prey score in seven of eight `h=3`
cells. Its summed difference divided by all 320 holdout site scores was 0.0318
nats/site, but it lost in one cell. At `h=1`, the analogous mean difference was
only 0.00245 nats/site, with three wins, one loss and four effective
ties. Against constant free-h, the adjusted free-h model won 11 of 16 cells but
gained only 1.878 nats over all 640 holdout sites (0.00293/site), including one
3.804-nat cell loss. The constant and adjusted alternatives therefore do not
establish general predictive superiority; the adjustment's main role remains
control of the registered spatial-background nuisance.

The failed panel wrapper plus successful recovery used 257.458 seconds of wall
time; their respective peak group RSS values were 5.76 GB and 1.42 GB. The
separate qualification used 132.548 seconds and 0.589 GB. The passing
independent replay used 18.414 seconds and 535,716 KiB peak child RSS. These are
well inside the four-hour/48-GiB feasibility envelope. The generation estimate
of 1.674 seconds is a labelled filesystem-timestamp proxy. For future costing,
the measured adjusted-null plus adjusted-free workload including that proxy had
median 3.939 seconds and maximum 4.772 seconds per history; these wall workloads
are not hard CPU-time bounds.

## Calibration contract not implemented by this panel

The calibration arithmetic is a reviewed prototype, not a complete reference
campaign orchestrator. Its current `max_candidates` gate is per case. Four
cases can therefore require a union of as many as four times that number of
node tables. A future proposal must freeze a maximum affordable **union** size
before sealed observations and abstain for all affected cases if that union is
exceeded, unless resources explicitly budget the full four-case maximum. It
must never select a convenient subset of a retained nuisance set.

The paired fitter can also return a finite clamped statistic when a constituent
fit has failed. A future reference generator and caller must propagate fit
status separately: any failed observed or reference fit becomes `no_fit` or a
non-finite statistic and produces conservative abstention. Passing the finite
clamped value alone to the combiner would violate the registered failure rule.

The preferred next tranche is a separate public screen-retention pilot, after
those two caller repairs: exactly 99 node-addressed pre-only references at each
of 3,645 nodes, applied to the sixteen open fixtures, with all 1,820 four-fixture
unions reported. It should stream or chunk histories, prohibit redraws and
adaptive stopping, and record fit failures, true-node retention as a diagnostic,
candidate and union sizes, wall time, peak memory and setup/generation cost.
This can establish screen and union affordability on the fixed public design.
It cannot guarantee a future sealed union size or establish effect-table
affordability. Any future union cap must therefore be fixed from resources
before sealed generation and force abstention when exceeded. If the screen
pilot passes, a separate one-to-four-node public 999-reference effect
micro-pilot at predeclared boundary and interior nodes should verify end-to-end
fit failure handling and actual effect-calibration cost before any large table.

## Residual risks and recommendation

Accept Goal 056 as positive numerical-feasibility evidence for the fixed public
map, empirical bank, exact on-grid family and deterministic fitter. The direct
replay and lower-bound audits make another review unlikely to change that
bounded numerical decision. Do not interpret the panel as recovery, size,
power, coverage, causal-identification or general predictive validation.

The principal observed scientific limitation is the h--mean-hazard trade-off,
with fitted h substantially above 1 in one null history and downward h error in
most `h=3` cells. The cluster-isolated holdout reduces direct spatial leakage,
but its score is still one dependent spatial realization and supplies no
sampling uncertainty. Off-grid nuisance, residual spatial fields, missing or
informative visits, temporal change, censoring, extrapolation and transfer to a
new map remain outside the evidence. The panel also does not resolve reference
fit-failure frequency or retained-set size.

Proceed only to the proposed public screen-retention pilot after implementing
the four-case union cap and failed-fit propagation described above. That pilot
can establish screen affordability on this map. It cannot choose a defensible
cap for a new map without a new-map public qualification and retention/resource
check. If the screen is affordable, use the separately reviewed one-to-four
node public effect micro-pilot before any large 999-reference table. A large
effect campaign, sealed histories and publication claims remain new decisions.
Independent scientific review would materially affect those decisions because
the rank proof, four-case multiplicity, map-specific retention, failure handling
and resource cap jointly determine validity.

Any reported `SElogh = 1/sqrt(-ell''(log h))` is only a local profile-curvature
scale. The sitewise product does not model the generator's residual spatial
dependence, so this quantity is not a validated sampling standard error,
Godambe standard error or confidence-interval basis. This limitation does not
invalidate Monte Carlo rank calibration when the complete spatial null
generator and fixed statistic are used for every observed and reference
history.
