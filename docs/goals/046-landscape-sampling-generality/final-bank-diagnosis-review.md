# Goal 046 independent final-bank diagnosis

Completion note, 11 September 2026: the text below records the review before
the diagnostic ran. All subsequent half-grid and bank-half evidence is now
returned and verified. See the [completed diagnostic review](split-bank-diagnostic-review.md)
for the current disposition; the four production failures remain binding and
the completion heartbeat is paused.

Status: **final ensemble-bank decision complete; K65536/131072 is not
acceptable under the frozen global rule.** The nine selected-K65536 half-grid
reports remain in progress as an authorized diagnostic collection. Their
outcome cannot reverse this decision, although failures could identify
additional numerical problems. This review does not authorize scientific
acceptance or synthesis.

## Decision under review

Goal 046 asks whether spatially balanced sampling changes prey-effect recovery
relative to access-constrained sampling at equal survey effort. The estimands
are the five predeclared balanced-minus-access contrasts, reported separately
by effect and speed-information lane. The map is the experimental unit for
landscape generality: there are three fixed maps per archetype, while the 250
calibration and 250 evaluation histories quantify within-map process and
observation variation. The likelihood integrates imperfectly observed predator
arrival and prey persistence over a Monte Carlo arrival bank. This review asks
whether that integration is sufficiently stable at the final authorized nested
bank pair, K65536 selected versus K131072 reference. It does not test an
ecological null hypothesis.

The final pair fails the prospectively frozen ensemble criteria on four of nine
maps. Because every map had to qualify at one common bank pair, K65536/131072
cannot be accepted under the current protocol. This is a **numerical stop at the
authorized ceiling**, not evidence that balanced and access-constrained sampling
perform equally and not evidence for or against a prey effect.

## Evidence

The source, maps, sampling designs, histories, grids and bank seeds are held
fixed within each nested comparison. The returned reports record five passes
and four failures. I recalculated the failure locations, support endpoints,
calibrated cutoffs, paired width changes and saved-surface likelihood-ratio
values from the immutable K65536 and K131072 profile arrays. These calculations
are conditional on the separate provenance audit reconciling the campaign
bundles, adoption receipts and exact bank prefixes.

| Map | Frozen failure | Diagnostic interpretation |
|---|---|---|
| barrier 2026090811 | Estimated-speed `access_1`, evaluation history 198: lower-boundary classification changes. | A one-history endpoint crossing. LR-minus-cutoff changes from +0.003036 to -0.001199; the endpoint moves one H181 cell and all other criterion families pass. |
| barrier 2026090812 | Estimated-speed `access_5`, evaluation history 166: upper-boundary classification changes. | A one-history endpoint crossing. LR-minus-cutoff changes from -0.015765 to +0.000901; the endpoint moves one cell and all other criterion families pass. |
| connected 2026090812 | Known-speed `balanced_1`, evaluation history 231: lower-boundary classification changes; the paired mean log-width movement is 0.0120408, above 0.01. | The boundary flip accompanies a broader calibrated-width instability, rather than being only a near-zero classification margin. |
| corridor 2026090812 | Estimated-speed access evaluation history 0, all three effect conditions: generating-rho LR movements are 0.888265, 0.887308 and 0.879710, above 0.5. | The MLE remains at rho=1.101905 and near-core rho-profile movement is at most 0.205906. The failure is at the generating rho=1, whose LR is about 39--41 and therefore lies outside the LR<=10 core. |

The two barrier failures are threshold-sensitive endpoint classifications. Their
small crossing margins, unchanged support-component counts, one-cell endpoint
movement and passing aggregate contrasts argue against describing them as
large changes in recovery. They still fail the frozen requirement that boundary
classification remain unchanged. Similar endpoint failures moved among maps,
conditions and histories over earlier bank doublings, so the evidence does not
show uniform endpoint convergence.

The connected-map failure is more consequential for the primary effect-support
endpoint. The null, known-speed balanced cutoff increases from 2.299503 to
2.394133 when calibration histories 124 and 131 exchange positions around rank
239. At the old cutoff, changing only the profiles alters the paired mean
log-width contrast by -0.000370. Recalibrating with the K131072 profiles then
changes it by +0.012411, giving the net +0.012041 failure. The access mean width
changes by -0.000116, whereas the balanced mean changes by +0.011925 and 116 of
250 balanced validation histories change width. The paired contrast therefore
moves from 0.064523 to 0.076563. This is a calibration-order-statistic problem
distributed over many validation histories, not a single endpoint tie, and its
magnitude is 20% above the prospective tolerance.

The corridor failure is different again. For the shared access evaluation
history 0, generating-rho LR values for `access_1` progress from 38.3063 at
K32768 to 38.4846 at K65536 and 39.3728 at K131072; the other two effects show
the same approximately 0.88 final-step movement because they share the predator
history. The stable MLE and passing near-core profile criterion indicate that
this is likelihood-tail instability, even though rho=1 is an interior grid
point. The three failed rows are not independent replicates. The direct
generating-value criterion was nevertheless declared in advance and applies
outside the LR<=10 core, so the current result cannot be reclassified as a pass.

Across successive production ladders, ensemble failures decline from seven of
nine at K16384/32768 to four of nine at K32768/65536, but remain four of nine at
K65536/131072. The failure modes also migrate rather than shrinking uniformly.
More bank draws improved several maps, but did not establish the required
uniform accuracy before the bank ceiling was reached.

## Decision and next diagnostic

Close the current Goal 046 production route as numerically unresolved and do
not synthesize its ecological contrasts under the present acceptance contract.
Do not raise the bank beyond K131072, drop maps, or relax a tolerance after
seeing these results. Continue the already authorized half-grid collection to
completion, return all nine reports and reconcile their receipts. Any
half-grid failure should be added to this diagnosis. Nine passes would show
that local grid refinement is adequate for those checks, but would not
overturn the ensemble-bank decision because the reviews address different
numerical risks.

Before deciding whether to redesign the integration or omit Arc 3 from Paper 1,
one small, diagnostic-only analysis would be informative and can use the banks
already generated:

1. Split each relevant K131072 bank into its two disjoint K65536 halves. For
   connected map 2026090812, recompute the known-speed null calibration
   profiles and corresponding validation widths for both access and balanced
   designs. Derive both rank-239 cutoffs independently within each half, then
   compare its coherent paired width contrast with the other half and the
   combined bank. Examine calibration histories 124 and 131 in the balanced
   design in particular.
2. For corridor map 2026090812, evaluate access history 0 on the two disjoint
   halves at rho=1 and a small fixed window around the observed MLE, profiling
   over effect. This tests whether the 0.88 LR movement is consistent with
   Monte Carlo variation confined to the likelihood tail without rebuilding
   the full production ensemble.

This diagnosis must not be used to rescue the current run. Its purpose is to
choose between two new scientific paths: stop Arc 3 with numerical uncertainty
reported, or register a new variance-reduced or otherwise redesigned
integration and a prospective validation contract before re-running any
ecological comparison. A new contract could reconsider whether far-tail rho LR
accuracy is decision-relevant, because calibrated rho intervals are not a Goal
046 endpoint, but the connected calibrated-width instability would still need
to be resolved rather than waived.

The minimal implementation needs no new bank generation and no full campaign
rerun. Hash-verify each saved K131072 bank, split its rows into `[0:65536]` and
`[65536:131072]`, and reconstruct the predeclared histories from the saved seed
manifest. The frozen integration kernel adds 0.5 pseudo-observations in each
arrival category. Therefore, do not average the two already normalized
half-bank integrations to reconstruct K131072. For both category masses and
survival moments, first undo each half's `65536 + 0.5 * category_count`
denominator, subtract the duplicated pseudo contribution, sum the empirical
numerators, add one pseudo contribution, and apply the single
`131072 + 0.5 * category_count` denominator. This is an algebraic
reconstruction of the existing frozen kernel's full-bank sufficient
quantities, before taking logarithms; it is not a new integration method.

For connected 2026090812, build each half-bank integration only at rho=1 over
the unchanged H181 effect grid. Recompute 250 null known-speed calibration and
250 null validation profiles for each of the access and balanced designs.
Within each half-bank, use its own access and balanced rank-239 cutoffs to
calculate the paired log-width contrast; then compare both cutoffs and the
contrast between halves and with the exactly reconstructed combined-bank
result. No cutoff may be imported from a different bank.

For corridor 2026090812, freeze the diagnostic rho set before execution as
`{1.0, 1.0570180405613805, 1.0717734625362931, 1.0867348625260582,
1.1019051158766109, 1.11728713807222, 1.1328838852957988,
1.148698354997035}`: the generating value plus three existing G201 cells on
either side of the observed coarse-grid MLE. On each half-bank, retain the full
H181 effect grid and evaluate only access evaluation history 0 for the three
effect-generating conditions. Compare raw and locally centred effect-profiled
rho likelihoods. If a half-bank maximum lies on an edge of the frozen window,
record the diagnostic as inconclusive rather than widening the window after
inspection.

Using the recorded K131072 runtimes as a scale guide, this reduced calculation
should require roughly 3--5 minutes for the two connected half-bank
integrations and 20--30 minutes for the two corridor integrations on the same
four-worker deep-server setup, plus receipt checks and serialization. These are
planning estimates, not measured diagnostic runtimes. The two halves are
disjoint Monte Carlo samples conditional on the same histories and frozen bank
stream; they can reveal half-to-half variability and a fragile calibration
order statistic. They do not estimate exact integration error or bias, the
combined result is correlated with both halves, and agreement between halves
would not prove convergence to the exact likelihood. The two K65536 halves
have the same pseudocount weight, so their mutual difference reflects draw
realization at that fixed smoothing rule. A K65536-half versus reconstructed
K131072 comparison changes both the sampled arrivals and the pseudocount's
relative weight. The overall split diagnostic therefore does not isolate a
pure Monte Carlo component of the bank-doubling change.

## Remaining uncertainty

The ensemble-bank disposition is final under the current frozen contract. The
remaining uncertainty concerns whether the nine pending half-grid reports add
further failure modes or confirm that local grid refinement is otherwise
adequate. Their receipts and sidecars still require independent reconciliation
after return. The optional disjoint-half diagnostic would inform a future
method decision; it cannot qualify or rescue the present run.
