# Retrospective infection-order integration pilot

Frozen design before pilot likelihood outcomes, 12 September 2026. This is
Goal 048 method development under the approved autonomous scope. It neither
adopts a replacement integrator nor qualifies the ecological results.

## Fixed calculation

Use the accepted exponential-edge generator with eta=1, the unchanged paired
observation model, site-marginal composite likelihood, H181 effect grid,
background hazard 0.002 and detection 0.65. Integrate holding times conditional
on each sampled infection order, with no pseudocount, floor or clipping.
Average linear conditional moments before taking likelihood logarithms.

The two old stress maps are `connected-2026090812` and
`corridor-2026090812`. Reconstruct their maps, sampling designs and history seed
schedules from the Goal 046 production65536 reference metadata. Connected uses
all original 250 calibration and 250 validation histories, null truth, both
designs and known rho=1. Corridor uses original validation history 0, access
design, all three effect truths, and the unchanged eight-rho Goal 047 window.
These deliberately reused histories are retrospective numerical controls.

For each map, generate three independent banks of 1024 infection orders, each
with its first 256 orders as a nested prefix. Order seeds are the unique uint64
outputs of `SeedSequence(20260912048).spawn(6144)`, assigned in map order
(connected, corridor), replicate order (0,1,2), then draw order (0,...,1023).
Save and hash this seed ledger before dispatch. No seeds are selected by outcome.

Use a common physical-time mesh containing every rho-times-survey endpoint,
maximum cell width 0.25, local moment degree 6, maximum internal Poisson mean
50 and Poisson tail tolerance 1e-14. Check source atoms explicitly. Average
compact curves in deterministic batches of 32; expand the effect grid only
after averaging. Retain compact means at each prefix and raw training
likelihood arrays so numerical conclusions can be reconstructed.

## Numerical and decision checks

Require the independent small-graph CTMC controls and implementation tests to
pass before dispatch. A one-order target-host smoke check must produce finite,
nonnegative arrays and category normalization error below 1e-10. Before the
full pilot, compare degree 6/width 0.25 with degree 8/width 0.125 on one fixed
order per map: maximum absolute mass/moment difference below 1e-10. Report
relative errors for positive entries above 1e-100 separately; do not infer
relative tail accuracy from an absolute check.

Recompute Goal 047's unchanged width and tail summaries. Compare all three
equal-K replicate pairs at K256 and K1024, and each replicate's K256 versus
K1024 prefix. The existing numerical movement thresholds remain descriptive
pilot advancement gates; no post-outcome relaxation is allowed. Any nonfinite
observed-history likelihood is a support failure for that configuration.
Any corridor maximum at the fixed window boundary is window-inconclusive.
Report all comparisons, including failures. A failed finite-K pilot does not
invalidate the exact conditioning identity or justify changing the biology.

Even a completely stable pilot supports only a prospective validation proposal.
It does not establish full-map absolute accuracy, all-map generality, calibrated
coverage or inferential acceptance. Scientific adoption remains for Barry.

## Cost and stopping bounds

Use the existing `deep-server-ts` environment in a fresh Goal 048 scratch
directory, with read-only copies of the required Goal 046 metadata and a
hash-bound source snapshot. Maximum two map jobs, four worker processes per
map, one native thread per process, 10 GiB address space per process, 96 GiB
aggregate RSS and two hours wall time for the full pilot. No automatic bank
extension. Stop on invalid arithmetic, resource failure or expired wall time;
preserve partial checkpoints and report the limitation. Target smoke timing
must support this envelope before the full run starts.
