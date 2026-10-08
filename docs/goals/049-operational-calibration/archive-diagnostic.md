# Goal 049 archive calibration transport diagnostic

This is a retrospective, known-speed diagnostic over the saved Goal 045 profiles. It performs no refits and draws no new process histories.

Inputs are K65536 and nested K131072; both archived runs use the accepted relative-arrival pseudocount alpha=0.5. Their comparison is descriptive and confounded by relative pseudocount weight; no matched bank-acceptance gate is applied.

The registered pre-run record is `registration-2026-09-20.md` (SHA256 `be4b6b35ebf3d3808d1b658c90a8c22c78b0dad3dc4e1ab8993d0c7a8a7aebbc`). The fixed bootstrap root is 2026092003, with 2,000 independent complete-history calibration/evaluation resamples shared across banks and source/truth cells.

## Effect cutoff transport

For each rho in {1, 0.5}, each source effect in {1, 3, 5} supplies its rank-239-of-250 known-speed cutoff. That cutoff is applied to the full saved 181-node effect profile for each evaluation truth. The two-panel matrix is coverage; exact membership, hull, component, boundary and effect-one exclusion summaries are in `effect_transport.csv`. Per-history support membership and the candidate-wise/oracle three-candidate indicators are retained in the `indicators_*.npz` files.

At K131072, effect-matrix coverage ranges from 0.908 to 0.984; all 18 source/truth cells have non-empty supports. The largest descriptive K65536-to-K131072 movement is 0.12431 LR in a source cutoff, 0.004 in coverage and 0.000566 in mean log-hull span. These are descriptive bank movements, not acceptance gates.

The candidate-wise/oracle matched-truth membership identity was checked for all six speed/truth combinations and all 250 evaluation histories. Conditional Wilson intervals are fixed-cutoff binomial summaries. Bootstrap intervals separately include cutoff variation; full profile geometry was not bootstrapped because the retained per-history indicators reproduce it exactly and the requested uncertainty target is transport rates.

## Speed-cutoff transport

The speed diagnostic is separate from the effect test. For each effect in {1, 3, 5}, the rank-239 speed cutoff from rho=0.5 or rho=1 is applied to the original saved 201-node rho profile at each evaluation rho. The second figure shows the original rho profiles and source cutoffs.

P3 is reported as a prediction audit rather than an acceptance rule. The registered criterion requires the predicted direction and at least one direction with severity at least 0.05; it passes 6/6 bank/effect rows. The smaller-source rho=1 coverage deficit is 0.144 to 0.152; the larger-source rho=0.5 excess is 0.028 to 0.032. The high-source +0.05 severity threshold is infeasible because 1 - 239/251 is less than 0.05, but it is not required for the registered at-least-one-direction criterion.

The archived P1 precursor at K131072 has c1/median(c3,c5)=0.815 at rho=1 and 0.758 at rho=0.5. Flat c1 coverage at h=3,h=5 is 0.916,0.908 (rho=1) and 0.924,0.912 (rho=0.5). The strict precursor oracle-exclusion comparison passes at slow speed but fails at usual speed because the h=5 null-exclusion rates tie; this is an archive precursor, not the full-grid P1 result.

## Registered prediction scope

P1's full-grid cutoff and P2's interior 2<=g<=8 table require the later 181-node calibration campaign and are not silently inferred from this three-anchor archive. The archive supplies a retrospective P1 precursor only (c1 versus the median of c3 and c5); P3 is evaluated above.

The archived P1 precursor is recorded numerically in `p1_prediction_audit.csv`. It is not promoted to the full-grid P1 claim.

## Files

- `effect_transport.csv`, `speed_transport.csv`: exact cutoffs, rates and support geometry.
- `cutoffs.csv`: source cutoffs and ranks.
- `indicators_65536.npz`, `indicators_131072.npz`: per-history membership and test indicators.
- `bootstrap_summary.csv`, `bootstrap_samples.npz`: fixed 2,000-draw calibration-aware rates.
- `p1_prediction_audit.csv`, `p3_prediction_audit.csv`: registered prediction audits.
- `effect_source_truth_matrix.png`, `speed_cutoff_transport.png`: requested figures.
- `receipt.json`: input hashes, schema checks, registration hash and execution provenance.
