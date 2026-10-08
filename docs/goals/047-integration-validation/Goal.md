# Goal 047: integration sensitivity and prospective repeatability

Status: **complete — registered Stage A rejection (pseudocount-sensitive)**.
Barry approved the study on 11 September 2026. Stage A completed successfully
at 2026-09-11 11:48:28 UTC; independent verification and terminal review confirm
six of nine within-bank alpha comparisons fail the connected width gates.
Stage B remains unrun under the prospective stopping rule. The heartbeat is
paused. See [results](results.md), [verification](completed-check.json) and
[final review](final-review.md).

Programme role: resolve the numerical obstacle to Charter Pillar 3 and the
Arc 3 landscape/sampling comparison. Goal 046 remains rejected under its
original frozen criteria. This study does not reclassify its four final map
failures or authorize ecological synthesis.

## Question and completion condition

Does the current arrival-bank integrator provide stable calibrated effect
widths and likelihood profiles when numerical pseudocount weight and bank
realization are varied separately?

Complete a prospectively specified numerical study that either rejects the
current integrator on a decisive sensitivity/repeatability failure or supports
limited operational repeatability sufficient to propose later all-map
qualification. Exact integration accuracy is not claimed without an adequate
numerical reference. A registered early rejection is a complete study outcome;
conditional stages should then remain unrun.

## Staged comparison

Register both stages, including controls, seeds and decision criteria, before
new study quantities are examined. The original alpha=0.5 pseudocount per
arrival category remains the primary method; alpha=0.25 and 1 are diagnostic
perturbations, not candidates that may be selected after looking at results.

Stage A uses the existing connected and corridor 2026090812 K131072 banks,
their two disjoint K65536 halves and original histories. Evaluate each bank
representation at all three alpha values. Hold the empirical bank fixed to
measure pseudocount sensitivity. Also compare matching relative pseudocount
weights across bank sizes: half alpha=0.25 against combined alpha=0.5, and half
alpha=0.5 against combined alpha=1. Combine empirical category masses and
survival moments before logarithms; preserve the frozen pseudo-arrival locations.
Require the original alpha=0.5 first-half and combined-bank outputs to reproduce
the saved Goal 046 quantities within 1e-9.

The connected stress test uses the original 250 calibration and 250 evaluation
null histories, both designs, known rho=1 and H181. The corridor stress test
uses original access evaluation history 0 at the three effect truths on H181
and the already fixed eight rho nodes. A window-edge maximum is inconclusive;
no adaptive widening is allowed. These are post-selected stress settings,
not prospective generality evidence.

A material same-bank alpha sensitivity failure rejects the present integrator
and stops before Stage B. Otherwise Stage B uses three freshly and independently
seeded K65536 banks for each map, independent history controls, full G201 for
corridor controls, and the same predeclared alpha levels. Recalculate each
bank's own cutoffs; never import a different bank's cutoff. All pairwise
comparisons are reported. Do not switch alpha, banks, histories or criteria
in response to outcomes.

The [detailed registration](design-proposal.md) states the exact seeds, controls,
thresholds, reference limitations and branch conditions. A fixed-window maximum
at its edge or isolated rho=1 stops as inconclusive, separately from an alpha
sensitivity rejection. Existing K131072
results are contextual references, not exact integrals. The two barrier failures
are outside this focused study and remain binding for future all-map acceptance.

## Authority and boundaries

Barry's approval authorizes registration, implementation, tests, independent
scientific review and the bounded study. Routine details that preserve its
question, biological/observation model and claim boundary are settled within
this approval. Keep all original Goal 046 source snapshots, banks and receipts
immutable; new numerical-weight primitives must not alter accepted kernels.

Use the local Mac mini for small tests and the existing user-owned
`deep-server-ts` for substantial calculations. Read the named compute-routing
and data-placement documents in `/Users/bwbrook/work/nectar/`; do not modify
that sibling repository. Use a fresh `/data/codex/scratch/goal047-*` source/run
directory, test the target first, record exact limits before launch, and retain
at most six simultaneous map/replicate calculations, four workers each, native
library threads one, 96 GiB aggregate RSS and 10 GiB address space per process.
Stage A has a two-hour hard timeout. The conditional new-bank stage requires
an explicit measured runtime plan within this study's bounded compute envelope
before dispatch; it is not an automatic unbounded campaign.

No ecological model change, changed Goal 046 estimand, production acceptance,
full Arc 3 rerun, larger-than-K131072 bank, cloud resize, service change,
commit, push or publication is authorized. Return verified evidence and an
independent interpretation at the numerical-method decision. A production
method amendment or new inferential claim requires the corresponding scientific
review; unsuccessful validation does not permit post-hoc retuning.
