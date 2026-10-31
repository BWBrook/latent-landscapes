# Independent numerical review

31 October 2026. Read-only review by the GPT-5.6 Sol specialist subagent
`fast_likelihood_audit`; integration and additional checks by Codex.

## Method and code

The reviewer checked positive survival/transition identities, centred mixture
cumulants and vectorisation, h=1, category boundaries, missing observations,
initial states, cohort timing, the derivative-aware series gate, and direct
integration into the Laplace criterion. Review found and caused repair of an
h=1 construction error and a memory-heavy representation that duplicated
category-degree terms across calendar components. Parent review found an
incomplete coarse-calendar support gate; independent review confirmed the
repair routes (0,20,40,60) calendars to the raw law at h=1 and h=3.

The final source hash beginning `154dcb6f` preserves canonical-calendar
algebra from the independently timed source `19157fbe`; both exact versions
are retained. The latter is historical evidence for the fixed-h3 run, not
an alternative implementation offered to callers.

## Independent real-input checks

The B_H3 h=3 fit resolves positive and zero variance. The positive criterion
is -1716.952013929 with projected gradient 1.73e-6 and latent-mode score
1.02e-10. The zero-variance criterion is -1717.668739144 with projected
gradient 5.46e-6. It takes 88.06 seconds including setup (87.36 seconds fitting), at peak RSS about
796.7 MB, using order-816 moments plus raw arrivals. There are 6,786 evaluator
calls, 718,320 series-site evaluations and no raw-path or domain failures.

The reviewer independently replayed the formerly underflowing `cell_35_04`
through the order-816 series path at h=30, eta=-2,-.9375,-.875,0. All values
match raw evaluation at recorded precision; maximum absolute differences in
d1,d2,d3 are 5.69e-13, 1.14e-13 and 1.151e-9. The replay retains the source
and input hashes and explicitly verifies the branch used.

The reviewer checked kernel and complete-criterion gradient receipts against
the live source. Every core-gradient coordinate has a stable finite-difference
step; the worst discrepancy over both tested step sizes is 9.83e-7. This
supports bounded numerical use of the kernel and Laplace derivatives, not
accuracy of the Laplace approximation or arrival-bank precision.

## Execution decision and remaining scope

The reviewer initially recommended reducing mode-solver calls before a full
35-node traversal because the independent fixed-h3 fit took 87 seconds.
The parent retained that recommendation as a performance follow-up and chose
to measure a bounded whole profile after the high-h numerical gates. The
20-second goal is an engineering target rather than a scientific acceptance
rule; a warm-started profile is also not priced accurately by multiplying
cold fixed-node timings. No optimiser redesign was adopted in this tranche.

The completed full-mesh findings and independent acceptance appear below. Independent-bank sensitivity,
continuous-profile roots/topology, global modes, importance-reference precision,
calibration and the 600-case challenge remain outside this acceptance.

## Prospective solver optimisation gate

After the completed three-node profile took 453.62 seconds and 78,022
likelihood calls, the parent revisited the performance recommendation. Before
editing the solver, the design specialist and independent reviewer both
recommended trying the existing damped Newton procedure first. Failure must
return to the old L-BFGS-plus-polish path from the original branch start,
not from the partially moved Newton point. Zero and warm starts, branch
selection, outer optimisation, fitted bounds and KKT=.001 remain fixed.

The prospective scientific checks are:

1. At identical outer parameters and each identical start, both solvers must
   succeed; penalised mode values and Laplace criteria must agree within
   1e-8 and site log hazards within 1e-6. Existing stationarity checks remain
   in force. Newton convergence alone does not establish the same mode for
   this potentially nonconcave likelihood.
2. Cross-evaluate both solvers at old and new fitted parameters for h3, h6.05348,
   h30 and the three-node profile. A refitted criterion may not deteriorate by
   more than 1e-6. Improved optima require fixed-parameter agreement and an
   explicit record; movement along a ridge is not automatically a failure.
3. Report LR movement, using 1e-5 as the initial equivalence check and
   investigating larger movement. Audit retained free, h1, near-support and
   h30 modes with the old solver before drawing conclusions.

The proposed Pareto targets are at most 40% of the baseline evaluator calls,
at most 60% of elapsed time, and at least 80% of branches finishing by Newton.
These are engineering adoption targets, not scientific accuracy thresholds.
Any failure must be investigated or the implementation reverted; thresholds
are not silently relaxed after outcomes are seen.

## First Newton result and bounded correction

The initial Newton source (`888ab4d9`) passes all seven fixed-parameter,
14-branch comparisons: maximum eta difference 5.10e-10, penalised-value
difference 4.55e-13 and Laplace difference 4.27e-10. Fixed h3 and h6 refits
are faster. The h30 refit is slower (80.02 versus 50.91 seconds), despite
2,869 versus 7,065 evaluator calls: raw-site evaluations rise from 461 to
2,708 and trial x reaches 8.58e55. This fails the recorded engineering target
and is retained as a developmental failure of the first acceleration.

The gradient replay also reveals an unnecessarily sharp mode-stopping effect.
Maximum finite-difference discrepancy rises to 6.96e-5, although every
coordinate still has a stable tested step within 2.21e-8. Independent replay
finds h30 alpha+1e-4 stopping at score 9.05e-9 while its paired perturbation
continues to 1.9e-14. The resulting criterion imbalance is about 1.4e-8.
The high-effect projected gradient worsens from 9.01e-6 to .000574, still
under the unchanged .001 gate. This diagnoses precision and path cost,
not a new estimand or a different fitted objective.

Before a second implementation, independent review approves two changes
confined to Newton-first: limit each proposed log-hazard increment to an
infinity norm of 1, and attempt one guarded correction after first meeting
tolerance. The limit applies to a single step, never cumulative eta or model
support. Unscaled steps still define stationarity and Newton decrement.
A polished point may replace the already-valid incumbent only if it satisfies
the existing objective slack, improves the residual, remains in-domain with
a positive-definite Hessian, and passes the same stationarity rule. Otherwise
the valid incumbent is retained. The old L-BFGS path remains unchanged.

The cap is supported by direct inspection: retained real zero-start Newton
steps have norms .24–1.54 except the h30 step at 29.58; warm starts are about
.10. Scientific and engineering comparison gates are not relaxed. New tests,
fixed-parameter comparisons, derivative replay and matched refits are required
before adoption or the full mesh.


## Final bounded solver acceptance

Source `3716ac2d` passes 23 spatial tests and independent structural review.
The fallback source is unchanged. All seven parameter points and fourteen
branch comparisons pass again: maximum eta movement 2.22e-10, penalised
value movement 2.28e-13 and Laplace/full-criterion movement 4.01e-10. All
18 gradient comparisons pass with maximum discrepancy 2.10e-8. The final
parent suite passes 167 tests, Ruff, strict mypy and diff-check.

The matched fixed h3/h6/h30 fits take 11.62/21.97/27.18 seconds against
88.06/37.10/50.91 seconds, respectively. All satisfy the elapsed-time target;
criteria and convergence remain consistent. The h30 call count is 42.25%
of baseline and therefore misses the 40% target. Its 752 raw-site evaluations
also exceed the old 461, although far below the rejected Newton version's
2,708. The original finite trial range is restored and projected gradient is
8.80e-6, against the original 9.01e-6.

The independent reviewer explicitly accepts this recorded call-target miss:
guarded polishing adds about 192 h30 attempts and removes demonstrated
objective roughness, while the miss is only 159 calls. Removing polish to
pass a counter would worsen numerical smoothness. Aggregate fixed-canary
calls are 31.4% and elapsed time 34.5% of baseline; these aggregate results
do not relabel the h30 call target as passed. This is a transparent Pareto
adjudication, not a changed scientific accuracy threshold or a silently
relaxed engineering rule. The solver is retained for numerical development;
production qualification remains separate.

## Pre-existing endpoint follow-up

Parent inspection and independent replay confirm that `exp(log(30))` is
`30.000000000000004` on this runtime. Both free-effect evaluators reject h>30,
and their optimiser upper bound is exactly log(30). Archived source `5fac48e1`
has the same behaviour, so this is not a regression from direct scoring or
Newton-first. Fixed-h30 evaluations bypass the transform; an interior free
optimum is unaffected. Reliable upper-bound free-MLE qualification requires
a targeted repair and tests in both variance families. This follow-up is
recorded without altering source during the current frozen executions.

## Full-mesh closure

Both histories resolve 35/35 positive-variance and 35/35 zero-variance nodes,
both free endpoints, and the combined envelope. No unresolved candidate or
fixed node exceeds the selected free endpoint. B_H3 takes 1551.74 seconds;
H3 takes 954.64 seconds. Their free optima are interior. B_H3's selected
projected gradient is .000962, near the unchanged .001 limit; its criterion
remains consistent with the coarse refit. Upper-SD and near-zero boundaries
are explicitly reported in the development record.

Independent review verifies the H3 receipt, input/source bindings and all
36 retained positive points from two identical starts. Independent review also verifies
that comparison for B_H3. All 144 branch comparisons across both histories
pass: maximum full-criterion movement is 5.832e-10 for B_H3 and 7.783e-10
for H3; maximum log-hazard movement is 5.482e-10 and 5.239e-10 respectively.
This closes the bounded finite-mesh computation and solver-equivalence checks.
It does not establish continuous/root accuracy, global uniqueness, independent-
bank precision, Laplace accuracy, calibrated uncertainty or campaign speed.

Independent final review accepts this finite-mesh closure. B_H3 hits the
upper spatial SD bound at h>=22.222 (four nodes); H3 hits the lower positive
bound at h=1 and 1.105 and the upper bound at h>=18.193 (six nodes). Raw
fallback is exercised at 32,782 and 5,605 site evaluations respectively, with
no final criterion domain/PD failures. All source and input identities match.
The 263 bound identities and 14 benchmark scope checks pass the archive audit.
