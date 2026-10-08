# Goal 046 numerical qualification

All three sacrificial pilots qualify K16384 as the initial global production
bank, with K32768 as the nested reference. The parent and an independent
scientific reviewer recomputed all 72 comparisons from the saved diagnostic
arrays. No limit, map, seed, grid or biological setting changed after inspecting
these results.

| Archetype | Effect MLE shift | Rho log-MLE shift | Maximum profile LR shift | Maximum truth-LR shift | Rho half-grid LL gain | Effect half-grid LL gain |
|---|---:|---:|---:|---:|---:|---:|
| Connected | 0.050000 | 0 | 0.347584 | 0.172620 | 0.123327 | 0.000832 |
| Corridor | 0.050000 | 0.013863 | 0.282358 | 0.195885 | 0.159472 | 0.000711 |
| Barrier | 0 | 0 | 0.203135 | 0.213410 | 0.068198 | 0.000385 |
| Limit | 0.05 | 0.027726 | 0.5 | 0.5 | 0.25 | 0.25 |

Connected and corridor reach the permitted one-cell effect-MLE movement.
All other maxima are below their limits. Profile comparisons centre each
profile at its own maximum and use the union within LR 10. Half-grid gains
are in log-likelihood units.

The review reconciled profile, bank, seed and diagnostic hashes, exact
G201/H181 grids, four retained histories across six conditions per map,
`bank_only=false`, and all campaign invariants. Saved and replayed surfaces
are identical; each refined array reproduces the original grid nodes exactly.
The diagnostic reports retain their `incomplete_numerical_review` label because
they do not assess the 250+250 production ensembles. This is compatible with
qualifying the initial bank, not scientific acceptance of production results.

Raw receipts and diagnostic arrays remain under
`artifacts/goal046_execution/qualification16384/`. The compact
[qualification check](qualification-check.json) records all report, profile,
bank and sidecar hashes and recomputed maxima. The
[production freeze](production-freeze.json) binds the exact nine maps, bank
pair, grids, history counts, seed branches and new source snapshot before
production outcomes are generated. Post-qualification source changes concern
production admission, saved-reference review and synthesis provenance; the
landscape, sampling, generative and likelihood mathematics remain unchanged.

Every production map must still pass the full ensemble comparison and a
four-history half-grid review at the final selected bank. A failure requires
uniform reassessment at the next approved global bank size. Nested-bank
agreement remains conditional evidence; it does not establish independent-bank
Monte Carlo accuracy or generality beyond the declared maps. Earlier numerical
failures are retained.
