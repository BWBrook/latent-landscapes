# Independent review before the retrospective pilot

12 September 2026. Separate methodological and execution reviews support
proceeding with the frozen K256/K1024 pilot after constraining the prototype
API to its documented H181/background-hazard domain.

The methodological reviewer confirmed that static undirected independent
exponential first passage has the SI continuous-time Markov representation.
Conditional on infection order, holding times are independent exponentials
with the recorded cut rates. Infection order is a coarser conditioning variable
than normalized edge proportions: its conditional estimates have no greater
per-draw variance for each linear mass or survival contribution. This is not
an ordering of nonlinear LR, calibration, width or cost-adjusted performance.
The exact controls, local/target refinement checks and target timing support a
bounded pilot. Three banks provide a feasibility screen, not a precise error
estimate or prospective qualification.

The implementation review independently checked node/site order, all 81 map
source cells and four sampled source atoms, frozen history selection, the
256-plus-768 draw-count-weighted aggregation, averaging before logarithms,
resource controls and exact seed-ledger regeneration. Its small four-node
runner wiring check passed. It found a launcher cross-binding gap: hashes in
the registration were consistent but not explicitly enforced by the launcher.
The launcher now checks design and seed hashes and the 6144-order count against
that registration as well as verifying each staged file.

Review also required explicit source-node validation, unequal-chunk aggregation
coverage, and bounds for internally split polynomial moments. Those corrections
are implemented. The final API domain guard rejects effects outside [1,10] or
a changed background hazard; this preserves the scope of its reported Taylor
and uniformization bounds.

A failed pilot rejects the specified finite-budget configuration, not the
conditioning identity. A successful pilot supports preparing a prospective
accuracy and calibration contract, not adoption. One independent terminal
review remains planned when all results and provenance have returned.
