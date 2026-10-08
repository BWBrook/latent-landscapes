# Fixed predictive comparison for the training lock

5 October 2026, Hobart. This restates the approved Goal 059 comparison before
inspection of the actual training fits. It adds no model, estimator or release
authority.

After Fable confirms the completed training lock and Barry releases the
committed holdout package, evaluate the same four frozen training fits for each
neutral case: constant background/free h, adjusted background/free h, constant
background/h=1, and adjusted background/h=1. Keep their exact parameters,
statuses, K=131,072 integration bank, whole-map normalization and observation
model. Do not refit, select a model or use a profile optimum as a replacement.

Use the qualified conditional-prey scoring path in
`capstone_qualification._heldout_row` and `preinvasion_likelihood.point_score`.
For each model report the sum of the 40 site contributions in nats, the mean
per site, and the eight five-site cluster contributions. Retain all model
scores and pairwise differences so weak separation or disagreement remains
visible. Higher conditional-prey log score indicates better performance for
this fixed set of held-out observations under this scoring rule.

The held-out sites belong to prospectively reserved clusters but share the
map and case-level spatial process with training. They are not 40 independent
replicates, and the eight cluster contributions do not license an automatic
independent-cluster standard error. Do not attach site-IID confidence intervals,
claim transfer to new maps, or use these four cases as operating-rate estimates.

If a main fit is numerically invalid, retain its failure and mark its predictive
score unavailable. If a fixed fit has an unresolved diagnostic discrepancy,
preserve that flag with its score; a held-out result cannot repair the training
fit or retroactively change its declaration. Any scoring/schema defect must be
diagnosed with original evidence preserved.

The training lock must include its input/source/runtime hashes, fitted
parameters, likelihood-support profiles, calibrated declarations, numerical
diagnostics, this predictive specification and the prerelease interpretation.
Holdout results are added only after the authorized release. Freeze the complete
report before Barry releases the separately committed truth package.
