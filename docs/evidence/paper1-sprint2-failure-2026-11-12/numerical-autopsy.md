# Bounded autopsy of the 27 failed qualification fits

12 November 2026 · independent Codex (GPT-6.1 Sol) review · frozen `99af520`.
Synthetic qualification only; training and validation stayed closed. No fits,
simulations, remote calls, source/receipt changes or threshold changes were made.
The rejection lower bound in [the gate review](independent-gate-review.md)
stands. This note diagnoses archived numerical evidence, not biological results.

Evidence is the 27 hash-verified failed attempts under
`artifacts/sprint2/pilot-20261107/phase-results/qualification-results/fit-*/attempt-0001/`: `fit/receipt.json`,
`fit/search_receipt.json`, `fit/search/evaluations.jsonl`, and stdout/stderr.
The preceding independent review verified all 162 inventoried output files.
All six source files discussed below match the frozen commit. Counts refer to
fits; the gate review lists their 14 unique dataset IDs and required roles.

| Archived failure mechanism | Fits | Demonstrated immediate cause | What remains unknown |
| --- | ---: | --- | --- |
| `unresolved variance family: positive_sigma` | 16 | At the stopping location, none of 51 archived positive-variance candidates is eligible; every outer optimizer says `trust region collapsed`. | Why successive outer steps fail acceptance; no step/curvature trace survives. |
| `unresolved constant family fit` | 9 | No eligible candidate on the very first reduced constant fit: `fit_count=1`, `profile_nodes=0`. | Candidate parameters, gradients, optimizer message and curvature were not archived. |
| `unresolved candidate exceeds selected family envelope` | 2 | Three ineligible positive-variance candidates hit the 80-iteration cap while exceeding eligible same-family maxima. The envelope guard rejects them. | Whether improved optimization would certify these higher branches or find others. |

The 16 spatial exceptions comprise 14 receipts with spatial `unavailable` and
two with a partial `available` summary (connected-2 window-low C lean and
corridor-2 b100-anchor C dense). The latter had earlier free/profile information;
that status does not resolve the subsequent exception. All 16 are classified
`family_fit_failed`, alongside the nine constant failures. The remaining two
are `search_unresolved`.

**Spatial outer stalls are demonstrated; latent failure is not.** The 16 fits'
51 positive candidates finish with successful evaluations and successful latent
modes, but projected outer-gradient norms of **0.00521–5.384**, all above the
standard eligibility threshold 0.001. Collapse occurs after 38–62 iterations,
before the 80-iteration cap. Their best positive candidate scores exceed the
eligible zero-variance alternative by 1.093–28.069; dropping that family would
hide unresolved higher scores. Fifteen candidates come from the explicit
high-sigma anchor and 36 from neighbour/default-labelled starts: this is not
solely a missing-anchor problem. Seventeen finish at sigma=1.5, while 34 finish
inside its bound; boundary clipping alone is not established as the cause.

Across all 18 unresolved-fit events, all 57 positive candidates have successful
latent modes. No archived candidate reports failed saddle escape, unavailable
second-order checks or a latent-grid boundary failure. Only projected-gradient
norms, final parameters, optimizer messages and latent convergence scalars are
retained: raw gradient vectors, Hessian/eigenvalues, trial acceptance ratios and
initial vectors are absent. Source labels identify start classes, not full
initial vectors. Therefore derivative inconsistency, poor curvature/scaling,
rejected trial evaluations and difficult local geometry remain hypotheses.

**The envelope failures are one dataset, corridor-1 window-low B.** Dense stops
at h=22.2222: the high-sigma start reaches 80 iterations, gradient 4.913, and a
score 0.230522 above the best eligible positive candidate. Lean stops at h=30:
two candidates reach 80 iterations, gradients 10.961 and 16.830, with excesses
0.239916 and 0.239129. Eligible alternatives sit near zero variance. These are
observed unresolved higher branches; the guard is functioning as specified.

**The constant failures expose a diagnostic gap.** They cover four datasets:
connected-2 window-high A (dense/lean), connected-2 trend A (dense/lean),
corridor-1 b100-anchor A (dense/lean/independent-bank), and barrier-1 trend A
(dense/lean). Frozen `ReducedFamily.run/point/_starts/_fit` starts at h=1,
with no earlier points or constant seed rows. Its sole initial reduced vector
is `(alpha,detection_sd)=(-5.5,0.2)`; beta is fixed to zero. `_fit_constant`
requires both optimizer certification and gradient <=0.0001. Failure discards
candidate summaries, leaving only the exception/counts. Stdout repeats the
exception; no constant optimizer trace exists. A start failure, outer collapse,
iteration cap or curvature rejection cannot be distinguished retrospectively.

**Warnings are a lead, not a causal finding.** All 16 spatial-exception stderr
logs and the two connected-2 trend constant logs contain overflow/nonfinite
warnings in `differentiable_likelihood.py:88–115`. The loss third-derivative
formula multiplies large polynomials before a vanishing reciprocal; mixture
moments can also overflow. Its final finiteness check rejects nonfinite output
(line 727). Warnings lack stage/parameter timestamps, so they cannot be assigned
to the final failed candidate or shown to cause collapse. Seven constant failures
and both envelope failures have empty stderr; warnings are not a common proven
explanation of all 27 failures.

**Small coherent target for Claude's judgment:** investigate the shared outer
solver's derivative/curvature consistency and step acceptance before choosing
an algorithmic repair. `SpatialProfileCriterion._trust_region` (1035–1192)
uses gradient-difference curvature, clips proposed steps, accepts gain/prediction
ratio >0.1, otherwise quarters the radius until collapse. Both spatial and
constant fits call it. The existing eligibility, second-order and envelope
checks must remain intact.

Propose one bounded diagnostic tranche on three already observed checkpoints:
enriched connected-1 B at h=sqrt(30) (collapse), corridor-1 window-low B dense at
h=22.2222 (higher unresolved branch), and connected-2 window-high A at h=1
(constant). First preserve every start/final candidate, full gradients,
curvature spectrum/completeness, trial validity and actual/predicted gains;
check derivative consistency at the archived spatial endpoints and retain the
constant first-fit trace. Separately check overflow-safe evaluation of the same
loss-derivative algebra on scalar stress inputs. These would be development
diagnostics, not retries that replace qualification outcomes. Stop after those
three mechanisms are discriminated; Claude can then choose a justified repair.
No repair, extra-start/budget retuning or guard relaxation is accepted here.

Source trace: `scripts/qualify_spatial_profiles.py:86–106,474–485,507–540`
(selection/archival/starts); `scripts/benchmark_spatial_profile.py:545–585`
(retained fields); `scripts/fit_dataset.py:202–288,290–334,367–370,420–479,632–655,845–868`
(constant path, partial summaries and classification);
`src/latent_landscapes/spatial_profile.py:1035–1244` (outer solver/eligibility);
`scripts/run_development_profile.py:167–168` (free starts);
`src/latent_landscapes/differentiable_likelihood.py:38–115,727–728`
(loss/mixture arithmetic and finite-output guard).

Next: Claude — judge the bounded diagnostic tranche before selecting any repair.
