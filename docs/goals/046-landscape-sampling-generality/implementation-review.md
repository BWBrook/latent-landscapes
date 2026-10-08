# Arc 3 implementation review

The focused review supports the map, sampling, union-history and likelihood
wiring for pilot execution. It does not accept numerical accuracy or scientific
results from the production ensemble.

An independent read-only review traced the shared holdout selection, separate
training-selection streams, physical-site union, history slicing and accepted
likelihood calls. It found no material wiring issue. The parent also inspected
the two reference-code changes and the new adapters, then replayed affected
Arc 2C tests and the three-archetype execution pilot.

The sampling strategies retain identical site-visits and the same prediction
target. Selection uses geometry and eligibility, not simulated arrivals or
outcomes. A complete process/observation realization is generated once on the
physical-site union, with the accepted kernel sharing random variates across
effect truths. Common sites therefore retain identical observed histories
across sampling designs. Calibration and evaluation seed branches remain
separate. Each fit and score uses its own design's correctly ordered records.

The synthesis review corrected map-seed compatibility and the null
false-exclusion complement before accepting any summary. It also removed
unrequested calibrated rho intervals. Per-map effect cutoffs and complete
history bootstrap draws remain separate between maps; each draw is shared
across designs, effects and speed-information lanes within a map. Equal map
weights, map ranges and leave-one-map-out ranges keep the landscape
replication distinct from within-map Monte Carlo uncertainty.

The numerical checks bind saved banks and profiles to their receipts and
require nested bank prefixes and identical simulated histories. The bounded
checker reconstructs the map and sampling pair and replays the saved surfaces
before comparison. Source drift is recorded explicitly; an old Git HEAD is
not treated as proof that an uncommitted implementation is unchanged.

Production admission now checks the explicit Goal 046 freeze, exact map/seed
branches, 250+250 histories, rank 239, grids and selected/reference bank roles.
Both numerical reviewers reconcile the recorded freeze and its canonical hash.
The four-history reviewer can reuse a verified full reference bundle while
retaining selected-bank replay and refinement; production cannot skip the
half-grid checks. Synthesis rejects mixed pilot/production inputs and retains
source profile and bank hashes, with production outputs pending review.

The final focused selection passes 52 Arc 3 and affected Arc 2C regression tests.
Scoped Ruff and strict mypy checks pass. These checks establish implementation
readiness; the three large-bank qualification runs remain incomplete and no
production result is scientifically accepted.

The existing pairing invariant does not independently reconstruct shared
random variates across effect truths. That sharing is implemented in the
unchanged `paired_histories()` kernel and is exercised through its existing
regression tests. This remains a stated limit of the adapter's invariant,
rather than a new claim of independent generative verification.
