# Goal 046 independent split-bank diagnostic review

## Decisive finding

The bounded diagnostic completed correctly and is scientifically informative,
but it does not qualify the Goal 046 production evidence. The frozen
K65536/131072 comparison remains rejected on four of nine maps, including the
connected-map calibrated-width failure and the corridor generating-rho tail
failure examined here. The two unexamined barrier endpoint failures also remain
binding: barrier 2026090811 estimated-speed `access_1` evaluation history 198
and barrier 2026090812 estimated-speed `access_5` evaluation history 166. The
selected-K65536 half-grid review also remains 213 of
216 rows passing, with its three failures confined to that same corridor
history; every separate effect and rho grid-refinement gain passes. These facts
locate the observed failures in finite-bank integration and its interaction
with calibrated profile summaries; the declared local parameter-grid checks
pass.

For connected map 2026090812, the two disjoint K65536 halves give almost the
same known-speed null cutoffs and paired mean log-width contrast. The exactly
reconstructed K131072 bank nevertheless reverses calibration histories 124 and
131 around rank 239 and raises the balanced cutoff enough to move the paired
mean log-width contrast by more than the frozen 0.01 tolerance. This is direct
evidence that the calibrated endpoint is not stable under the current
integration procedure. It is not evidence that either half or the combined
bank is closer to the exact integral.

For corridor map 2026090812, access evaluation history 0 has the same local rho
MLE, 1.1019051159, for all three effect-generating conditions and for both
halves and their combination. No maximum is at an edge of the fixed local
window. The two K65536 halves differ by 1.84--1.86 LR units at the generating
rho=1, while their maximum difference across the seven contiguous local rho
nodes is only 0.405--0.412 LR. This supports the diagnosis of appreciable
finite-bank variability in a far likelihood tail with a comparatively stable
local fit. The three effect rows share one predator history and are related
views of one failure, not independent replications.

## Scientific target, estimand and scope

Goal 046's scientific estimands are the five predeclared
balanced-minus-access sampling contrasts, separately by prey-effect truth and
speed-information lane, over common 40-site holdout targets. The map is the
replicate for the bounded landscape-generality question; calibration and
evaluation histories characterize within-map process and observation
variation. The present diagnostic has a narrower numerical target: determine
whether two previously observed failures are consistent with bank-realization
variation, a fragile calibration order statistic, or local grid failure.

The synthetic data-generating process, 120/40 clustered sampling designs,
imperfect-detection observation process, fixed histories, H181 effect grid and
arrival-bank likelihood are unchanged. The connected calculation retains only
the no-effect, known-speed access and balanced conditions across all 250
calibration and 250 evaluation histories. The corridor calculation retains
only access evaluation history 0 for the three effect truths, evaluated at the
generating rho plus seven frozen G201 nodes around the observed MLE. These cases
were chosen after their numerical failures were known. They are stress tests,
not held-out validation data, and they support no frequency statement across
histories, maps or landscapes. The computed width contrast is used only to diagnose numerical stability;
this analysis does not qualify ecological inference about sampling designs.

## Independent recomputation from the reduced arrays

I recomputed all quantities below directly from
`diagnostic-arrays.npz`, without using the summary values in
`diagnostic-report.json`.

### Connected calibrated widths

| Bank | Access cutoff | Balanced cutoff | Balanced history at ranks 238 / 239 | Paired mean log width |
|---|---:|---:|---|---:|
| First K65536 half | 2.0230219721 | 2.2995031822 | 131 / 124 | 0.0645226185 |
| Second K65536 half | 2.0233829986 | 2.3001070500 | 131 / 124 | 0.0642684438 |
| Reconstructed K131072 | 2.0226291260 | 2.3941334564 | 124 / 131 | 0.0765634267 |

Each cutoff is exactly its own bank's 239th ordered calibration LR; no cutoff
is imported across banks. All 1,500 validation support masks (two designs by
250 histories by three banks) are non-empty and contain exactly one connected
component, so the endpoint-based log widths are coherent. Recomputing every
width from the H181 endpoints reproduces the saved paired means exactly.

The half-to-half paired-mean difference is -0.0002541748. Only four of 250
paired contrasts change between equal-sized halves. Relative to the first
half, the combined bank changes one access width and 116 balanced widths,
moving the access and balanced mean log widths by -0.00011595 and +0.01192486,
respectively; the net paired movement is +0.0120408081. Relative to the second
half, it changes no access widths and 119 balanced widths, for a paired movement
of +0.0122949829.

The calibration switch is also exact. In the first and second halves, balanced
history 131 has LR 2.2885674567 and 2.2927970687 at rank 238, while history 124
has LR 2.2995031822 and 2.3001070500 at rank 239. In the combined bank, history
124 is rank 238 at LR 2.2998118666 and history 131 becomes rank 239 at LR
2.3941334564. Because calibration histories and evaluation histories are held
fixed, this propagation from one numerical rank switch into more than one
hundred validation widths is integration uncertainty propagated through a
non-smooth calibrated summary, not calibration-sample resampling uncertainty.

### Corridor rho profiles

| Condition | rho=1 LR, first half | rho=1 LR, second half | rho=1 LR, combined | Half-to-half difference |
|---|---:|---:|---:|---:|
| `access_1` | 38.4845794380 | 40.3442733375 | 39.3728441100 | 1.8596938995 |
| `access_3` | 38.5276993690 | 40.3857220894 | 39.4150068886 | 1.8580227204 |
| `access_5` | 39.7730867784 | 41.6108801937 | 40.6527969883 | 1.8377934153 |

All nine local profiles have their maximum at the fifth listed node,
rho=1.1019051159, rather than at the isolated generating node or either edge of
the seven-node contiguous window. The largest half-to-half LR movements within
that contiguous local window are 0.4116691, 0.4100519 and 0.4049331; the
combined-to-first-half maxima are 0.2059058, 0.2051200 and 0.2022544. The fixed
window diagnosis is therefore conclusive under its prespecified edge rule and
shows a stable local maximum alongside unstable far-tail LR values. It does not
show convergence of the local profile to an exact likelihood.

### Reproduction and provenance evidence

The runner checks the old K65536 bank as the exact prefix of K131072 and
reconstructs the full-bank integration from linear category masses and survival
moments before evaluating log likelihoods. The saved first-half profiles
reproduce with zero maximum absolute error. The reconstructed combined
connected profiles reproduce the saved K131072 calibration and validation
quantities within 9.10e-13 and 1.37e-12; the corridor surface reproduces within
4.55e-13. All 38 reduced arrays have finite values and expected shapes.

The full run exited 0 after 2135.506 seconds using four workers, with peak RSS
3,193,108 KiB (3.045 GiB), within its declared bounds. The evidence identities
are:

- runner SHA256:
  `c92736d3bbe6e504076e8e3efbe5561c91b9b47fc23cda4e1528b01dd5001362`;
- reduced-array SHA256:
  `959cbc9fe5f65a62a5874ea4ee7c73c1132118831981e581f59837c9684ed5d3`;
- report SHA256:
  `93f6d9ac645b93fe4b1fda6916c300e746febfaaddf21eddfa4a5c3422e711ac`;
- frozen source snapshot SHA256:
  `6ee147ed17b3324bc2c432b9a1ce7f686f527417f9abb9fa290cea05c53e4c87`.

## Competing explanations and limits

The equal-sized halves use the same K65536 pseudocount rule and therefore give
the cleanest available comparison of draw-realization variability conditional
on these fixed histories. Their close connected results and discrepant corridor
tail values show that bank variability depends strongly on the functional and
likelihood region being examined.

Half-to-combined changes have a different interpretation. The kernel has seven
arrival categories and adds 0.5 pseudo-observations per category, giving
denominators 65539.5 for each half and 131075.5 for the combination. Thus a
half-to-combined comparison changes the empirical arrivals and the relative
pseudocount weight. Site probabilities are then logged, summed and profile
centred, so the combined LR need not lie between the two half LRs. The connected
combined cutoff lying outside the two half cutoffs does not identify the
pseudocount as the cause; finite-bank mixture non-linearity and centring are
also plausible. The current arrays cannot separate these mechanisms.

Local grid aliasing or optimiser failure is not a persuasive explanation:
inference uses fixed exhaustive grids, every connected support is a single
component, all separate grid-refinement checks pass, and the corridor maxima
are interior. The diagnostic also gives no evidence about model
misspecification, detection bias, sampling leakage, spatial pseudoreplication
or extrapolation because it reuses synthetic histories generated under the
fitted model and examines only two post-selected failure settings. The three
corridor effect conditions and the combined bank are correlated, so treating
them as replicated convergence evidence would exaggerate information.

## Recommendation and residual risk

Pause Goal 046 at the method decision. Do not run another bank increase,
synthesize ecological contrasts, relax the existing gate or reinterpret this
diagnostic as a rescue. Further review of these reduced arrays is unlikely to
change that decision.

Because landscape-and-sampling generality is a stated Paper 1 pillar, I
recommend a new, separately registered integration-validation study rather
than immediately abandoning Arc 3. It should use the known connected and
corridor failures as declared stress tests plus prospectively selected control
histories, compare multiple independently seeded equal-K banks, and explicitly
separate bank realization from pseudocount-weight sensitivity. It also needs a
predeclared higher-accuracy numerical reference; if that is infeasible, it
needs an explicitly operational replicate-stability rule that makes no claim
about exact bias. The study must test stability of the calibrated effect-width
functional, rather than only pointwise likelihood profiles. Evidence that
independent banks give stable cutoffs and local/tail profiles under one frozen
method would justify fresh all-map qualification and a new production run, but
would establish exact accuracy only if an adequate reference supports it.
Persistent rank switches or tail dispersion would support stopping Arc 3 or
redesigning the likelihood before any ecological claim.

An independent scientific review would materially improve confidence in that
new study's design and acceptance contract before compute begins. It would not
materially change confidence in the present disposition: the current
production evidence is numerically unresolved under its frozen rule, and the
completion heartbeat is ready to remain paused at this scientific decision.
