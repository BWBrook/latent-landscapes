# Goal 051 independent final scientific review

23 September 2026 (Hobart). **PASS: close the registered 17-cell screen and
retain B100-A_h1 as the sole nomination for independent confirmation.** I found
no material discrepancy in the production arrays, frozen detector calculations,
saved bootstrap evidence, tables, figure, or proposed claim boundary. The result
is a conditional robustness finding for one landscape and one fixed analysis;
it is not confirmation, a general detector-power estimate, or completion of
Paper 1 Charter Pillar 4.

## Scientific target and inferential scope

The screen asks whether a constant-detection, constant-background fit can return
a materially misleading estimate of the physical post-arrival prey-loss
multiplier without rejection by the frozen Berger--Boos adequacy test. The
primary event is `H = M AND NOT D_BB`, where `M` is truth exclusion from the
frozen effect set or at least a 1.5-fold point-estimation error. The principal
estimand is the paired change in the marginal probability of H from the
assumed-model baseline at the same physical h. H is broader than a false-effect
declaration and its nonzero baseline must remain visible.

Each independent unit is a complete generated history, including its spatial
field and all sites. Common random numbers pair the 17 cells within each of
1,000 independent blocks. The 160 sites, repeated visits and spatial cells are
therefore dependent parts of a history, not replicates. The fixed-bootstrap
analysis correctly resamples complete block indices jointly across cells and
does not resample sites or the 999 calibration references.

The data-generating departures change prey detection, predator detection, or
background prey-loss hazard while the analyst retains the original frozen
known-nuisance model, 181-node effect grid, K131072 bank, effect cutoffs, C99
cutoffs and conditional-score references. Physical h is the generating
multiplier; under misspecification it need not equal the fitted model's
pseudo-true projection. This distinction is essential to interpretation.

## Independent reconstruction and provenance checks

I derived the endpoint arrays again from the production profiles and scores and
the local Goal 049/050 references. The reconstruction agrees exactly with the
saved synthesis evidence for effect-set and C99 membership, all 17 by 1,000 by
181 inclusive-tie candidate p-values, Berger--Boos p-values, fitted-node plug-in
p-values, both rejection indicators, every M component, primary and plug-in H,
strict false effects, fitted h and signed log bias. Every primary rejection is
also a plug-in rejection, as required; this nesting does not make the plug-in
rule a calibrated omnibus test.

The bootstrap file contains seed 2026092304 and exactly 1,000 arrays of 1,000
complete replicate indices. Applying those saved indices to the independently
reconstructed 26 metrics reproduces every stored cell mean and paired delta
with maximum absolute difference zero, including all reported percentile
limits. This was a replay of retained indices, not additional resampling.

The production array SHA256 is
`6d98c61d8ecee7b53335dec13de536bfbead700fee6d97a48644efafba11e381`,
matching the production check and synthesis receipt. All nine synthesis output
hashes reproduce their receipt, including evidence
`5d21067f4a9ed768b48cf77ff2825236fec4c27dddea85abfe16a4be08e2846b`
and bootstrap draws
`ed4c53a777ccb681624805cc0d51d8274af48bbaa81d4addf69c9a43b9d9926a`.
Timing, production and synthesis have zero exit receipts; the completed
production check records unchanged input and source identities, all controls
passing, and 82 source files verified.

All 578 published diagnostic rows also reproduce exactly from the raw diagnostic
arrays, including finite-value counts, undefined correlations, means, sample
SDs and quantiles. B100-A_h1 and B100-A_h3 have identical field diagnostics,
and the registered detection fields are identical across physical truths.
The standalone figure is legible and agrees with the tabulated H rates, paired
contrasts and signed-bias point estimates.

## Decisive results

Five departure cells pass the prospective screen rule; the rule requires a
point delta H of at least 0.05 and a paired lower interval limit above zero,
not a lower limit above 0.05.

| Eligible cell | Delta primary H | Paired 95% interval |
| --- | ---: | ---: |
| **B100-A_h1** | **0.230** | **0.199 to 0.259** |
| D20_h1 | 0.191 | 0.157 to 0.220 |
| B50-A_h1 | 0.137 | 0.112 to 0.164 |
| B100-A_h3 | 0.102 | 0.068 to 0.135 |
| D10_h1 | 0.056 | 0.034 to 0.077 |

B100-A_h1 is therefore the correct single global nomination. Its primary H
rate is 423/1,000 versus 193/1,000 at baseline. Its M rate is 434/1,000, of
which the primary detector catches only 11; primary rejection is 2.7% versus
2.4% at baseline, a paired change of 0.003 [-0.004, 0.010]. The secondary
plug-in result is substantively concordant but remains diagnostic: plug-in H
changes by 0.231 [0.201, 0.260], while plug-in rejection changes by -0.004
[-0.013, 0.005]. A data-selected reference row has no fixed-node finite-sample
guarantee, and neither result supports a reject-on-either rule.

The contrast with D20_h1 clarifies what was selected. D20_h1 has more M events
than B100-A_h1 (520 versus 434) and more strict false effects (275 versus 216),
but its primary detector catches 136 M events. Both cells have 212 unflagged
strict false effects. B100-A_h1 wins on the registered broader H endpoint; it
does not have the largest total misleading-event rate or strict false-effect
rate. Failure of both score tests in a history also does not prove that the
departure is intrinsically undetectable.

The same aligned B100-A field at physical h=3 shifts mean fitted h from 3.020
to 3.871, raises mean signed log bias by 0.2565 [0.2421, 0.2706], raises truth
exclusion by 0.113 [0.088, 0.139], and raises primary H by 0.102 [0.068,
0.135]. This makes a pure lower-boundary explanation implausible within the
registered construction. It does not identify a general causal mechanism or
show that a constant-background fitted model should recover physical h under
this departure.

## Predictions and field diagnostics

The 21 registered prediction components are preserved: five scalar inequalities
are supported, nine are contradicted and five are unresolved; the two P3
interval-containment forecasts are met without establishing equivalence. In
particular, P2's B100-A_h1 strict false-effect rate is 0.216 with Wilson interval
0.192 to 0.243, so its claim of a rate above 0.20 is unresolved. Its low primary
rejection and delta H above 0.10 are supported. D20 shifts estimates upward at
h=3 and h=5, contrary to the forecast; the independent-background fields
narrow rather than widen mean log-span; and PD10 is less biased than D20 at
h=3 and h=5 and has no material truth-exclusion increase. These failed
predictions are retained results, not reasons to retune the screen.

The field summaries support faithful execution of the registered construction.
Every heterogeneous field has whole-map mean hazard 0.002/day. B100-A averages
map CV 0.947 and sampled CV 0.801 rather than exactly one, as expected for a
finite correlated lognormal field. Mean sampled hazard is 0.002047, with
training and holdout means 0.002093 and 0.001909. Mean sampled correlations are
0.567 with the deterministic exposure score A and 0.533 with realised exposure;
the latter has a 2.5--97.5% field range of 0.221--0.717. Detection-field means
and SDs agree with their targets to sampling error.

These diagnostics also set the causal limit. Mixing with A changes realised
hazard correlation, finite-map and sampled CV, tail shape, sampled mean, and the
training/holdout hazard balance together. The screen estimates the effect of
this complete registered generator, not an isolated causal effect of r or of
hazard--exposure correlation. The fixed landscape, clustered sample and split
can amplify or attenuate the observed projection.

## Residual risks and recommendation

The main remaining uncertainties are structural. The winner's interval is not
post-selection or multiplicity adjusted, so the 0.230 estimate is selection
biased even though the prospective nomination rule was followed. Calibration
tables, integration bank and known nuisances are conditioned on rather than
propagated. One accepted landscape cannot establish spatial generality,
stationarity across landscapes, or transfer to field data. The full finite grid
avoids optimiser and MCMC convergence failures, but broad and boundary-touching
sets still represent weak information; grid stability is not continuous-
parameter identification. No competing background model was fitted, so
background variation, h, detection and spread trade-offs remain unresolved.

Close Goal 051 as the complete registered screen. The synthesis states the
correct endpoint meaning, all five qualifying cells, the single nomination,
the unresolved P2 boundary, the detector roles, field-construction confounding
and the appropriate limits. The proposed next experiment is scientifically
defensible: generate 1,000 fresh B100-A_h1/B_h1 pairs, use a newly registered
fixed bootstrap root, require new delta H at least 0.05 with lower paired limit
above zero, keep screen and confirmation histories separate, and do not rerank
or fall back if it fails. Its resource ceiling is a proposal pending Barry's
decision and source-bound timing qualification, not evidence from this review.

A successful confirmation would establish replication of this named
generator--analysis vulnerability on the same landscape and split. It would not
separate the field features above or justify Stage 2 automatically. Any fitted
background alternative and neutral comparator need a new design that addresses
identifiability, nuisance treatment and predictive validation. Another review
of the frozen Goal 051 arithmetic is unlikely to change the closeout decision;
independent scientific review would materially affect confidence after the
confirmation and before adopting a competing model or broader manuscript claim.
