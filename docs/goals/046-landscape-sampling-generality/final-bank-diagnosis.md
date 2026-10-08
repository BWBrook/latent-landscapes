# Goal 046: numerical ceiling diagnosis

Final numerical diagnosis, 11 September 2026 (Hobart). All nine K131072 reference
campaigns have completed. Their K65536/131072 ensemble reports give five passes
and four failures. The separate selected-K65536 replay and half-grid checks
are complete and independently verified on all nine maps. All 216 rows
reproduce exactly; 213 pass and three repeat the same corridor generating-rho
LR failure. All separate effect and rho grid-refinement gains pass. All nine bundles, adoption receipts, seed manifests, actual
nested banks and ensemble metrics are returned and independently verified.
Independent review confirms rejection of the final pair; this document does
not grant scientific acceptance.

The final permitted bank pair does not meet the frozen all-nine-map numerical
gate. No sampling-design synthesis is authorized from this comparison. This is
unresolved numerical accuracy, not evidence of no ecological sampling benefit.

## Observed failures

History indices below are zero-based. The fixed effect grid spans multipliers
1–10 in steps of 0.05. Each changed boundary classification involves one
evaluation history and a one-cell endpoint movement; all support component
counts remain unchanged in the ensemble reports.

| Map | Failing condition | Numerical change |
|---|---|---|
| Barrier 2026090811 | Access, onefold, estimated speed | Evaluation history 198 newly includes the lower effect boundary. Boundary LR minus cutoff changes from +0.003036 to −0.001199. |
| Barrier 2026090812 | Access, fivefold, estimated speed | Evaluation history 166 ceases to include the upper effect boundary. Boundary LR minus cutoff changes from −0.015765 to +0.000901. |
| Connected 2026090812 | Balanced, onefold, supplied speed | Evaluation history 231 newly includes the lower boundary. The paired mean log-width contrast also moves +0.012041, exceeding the 0.01 limit. |
| Corridor 2026090812 | Access, all three effects, estimated speed | Evaluation history 0 has generating-speed LR changes 0.888265, 0.887308 and 0.879710, exceeding the 0.5 limit. |

The five ensemble passes are connected 2026090811 and 2026090813, corridor
2026090811 and 2026090813, and barrier 2026090813. Passing the ensemble check
does not override the frozen all-nine-map global gate.

## Cutoff sensitivity in connected map 2026090812

The balanced no-effect supplied-speed cutoff rises from 2.299503 to 2.394133 LR.
The fixed local rank is 239 out of 250 calibration histories. Calibration
history 131 moves from LR 2.288567 (rank 238) to 2.394133 (rank 239), overtaking
history 124, whose LR changes only from 2.299503 to 2.299812. No calibration
history or rank was changed by the analysis.

A diagnostic decomposition holds the selected cutoffs fixed while substituting
the reference profiles, then substitutes the reference cutoffs. The first step
moves the paired mean log-width contrast −0.000370; recalibration adds
+0.012411, giving the observed +0.012041 total. In the balanced no-effect
supplied-speed case, 116 of 250 evaluation widths change. This decomposition
explains the failure; it does not replace recalibration or amend acceptance.
The cutoff movement itself remains below its separate 0.5-LR limit, showing why
the declared contrast-level check adds information.

## Rho-tail sensitivity in corridor map 2026090812

The affected access-history fitted speed remains 1.101905 at K32768, K65536
and K131072 for all three effect conditions. The generating speed rho=1 lies
outside the LR<=10 core. For the no-effect condition its LR is 38.306290,
38.484579 and 39.372844 at those successive bank sizes; the other two effect
conditions give the same qualitative pattern. The final near-core rho-profile
movement is at most 0.205906 for these three rows, whereas the generating-value
movement exceeds 0.5. This identifies a tail likelihood issue rather than a
changed grid MLE. The generating-value criterion was prespecified and remains
binding even though calibrated rho intervals are not an Arc 3 endpoint.

The three effects share this map/design/history through the approved common
random numbers. These are three related failures, not independent replications.

## Decision boundary

Preserve every failed comparison. All half-grid evidence is now returned
and verified; it adds no new failure mode. Do not enlarge banks beyond K65536/131072, discard maps, relax limits,
freeze cutoffs across bank sizes, or switch to a subset of endpoints to accept
this run. The currently available evidence does not justify an Arc 3 recovery
claim.

The [completed bank-half diagnosis](split-bank-diagnostic-results.md) has
passed local/remote provenance and numerical replay checks and an
[independent final review](split-bank-diagnostic-review.md). Connected
half-bank cutoffs agree closely, but the combined bank reverses the influential
calibration ranks and moves the width contrast. Corridor half-bank tail LRs
differ by about 1.85 despite an unchanged fitted-speed node in the checked
window. These findings do not separate pseudocount sensitivity from nonlinear
likelihood combination or estimate exact numerical bias. The heartbeat is
paused for the consequential integration/validation design decision.

A further full-ensemble bank increase is not justified merely by the existence
of failures: the influential cutoff and tail behaviour need explanation first.
Any new production method or acceptance rule would require a recorded scientific
amendment and fresh qualification, with the present failed evidence retained.

## Evidence

The reproducible diagnostic is
`artifacts/goal046_execution/production65536/diagnose_final_bank.py`; its
remote result is `final-bank-diagnosis-remote.json` in the same mirror. It binds
all examined saved profile files by SHA256 and computes boundary margins,
width contributions, calibration ranks and the three-bank rho comparison.
The [ensemble return check](k65536-ensemble-check.json) verifies both campaign
sources, freezes, all nine adoption chains, seeds, actual nested banks and
exact replay of every ensemble metric. The [diagnostic check](final-bank-diagnosis-check.json)
records exact agreement between remote and local recomputation of all diagnostic
quantities and profile hashes. A deterministic tie order is used when listing
equally influential histories. The [independent review](final-bank-diagnosis-review.md)
confirms the numerical rejection. The [completed half-grid return check](k65536-halfgrid-check.json)
verifies all nine reports. Maximum separate refinement gains are 0.00095434
for effect and 0.13877691 for rho, both below the 0.25 log-likelihood limit.
The three failed rows are corridor access evaluation history 0 at the three
effect truths, reproducing the already recorded generating-rho LR movements.
