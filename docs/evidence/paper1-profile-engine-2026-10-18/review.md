# Independent numerical and design review

18 October 2026. Review by independent GPT-5.6 Sol specialist/auditor
subagents, integrated by Codex GPT-6. This records review of a development
implementation, not acceptance of a scientific performance claim.

The methodological review accepted the direction of an explicitly operational
Laplace working criterion with analytic derivatives. It required separation
of accurate computation of that criterion from sensitivity to a more accurate
integral. It rejected a population-level 99% subgroup-agreement interpretation
of the proposed 600-case suite, required adequate Monte Carlo precision for
importance references, and required full confidence-set topology rather than
only interval endpoints. These points are incorporated in the protocol.

Independent geometry review supported a common two-cell network-centre buffer,
joint 300-site selection and independently seeded holdout/arm labels after the
original frame failed capacity checks. The minimum separation, stratum counts,
nested panels and all failed seeds must be retained. This was an outcome-free
development decision. Subsequent 30-map feasibility and three-map seeded-selector
receipts test the amended geometry; they do not establish general statistical
performance or a uniform sampling distribution.

The code auditor independently checked the Laplace algebra using a correlated
positive-definite covariance and smooth synthetic site curves. The combined
determinant agreed with explicit `log|C| + log|H|` evaluation within 2.06e-15.
Maximum five-coordinate analytic/finite-difference discrepancies were 2.21e-10
at spatial SD .02 and 1.46e-9 at SD .25.

The review found and triggered repairs to the following substantive defects:

- The initial benchmark adapter passed holdout sites into a criterion that
  sums every supplied site. All inputs are now subset consistently, and the
  engine rejects mixed training/holdout inputs.
- Noncanonical predator calendars were accepted by fixed arrival-category
  emissions. Observation construction now rejects them.
- A compressed-only bank could request exact fallback without raw arrivals.
  The engine now fails explicitly instead of using pseudo-arrivals alone.
- Near-stationary latent modes could fail under tiny parameter perturbations
  because the Newton objective increment was below numerical resolution.
  After repair, all 22 independently checked evaluations succeeded; maximum
  raw score, Newton step and decrement were 9.19e-17, 8.07e-18 and 3.46e-17.
- Profile reporting mixed fixed-grid and free candidates when defining the
  LR maximum, labelled partial family envelopes resolved, and overstated
  completion. The receipt now preserves signed LR values, flags points above
  the selected free endpoint, distinguishes partial families and explicitly
  reports `profile_certified: false`.
- Receipt provenance omitted an active subsetting module, and accepted-mode
  diagnostics omitted the Newton step/decrement. Both are now recorded.

The auditor also verified the order-192 bank and preparation/source identities.
A bounded real 120-site h=3 check found finite curves and agreement among three
deliberately different warm starts. However, 42 of 120 splines had some positive
curvature. Latent-mode globality therefore remains an empirical qualification
question. Zero plus one warm start is not a proof of a global mode.

The four-marginal-SD grid check is a guard, not a joint tail certificate. A
Bonferroni bound for any coordinate leaving such marginal intervals is about
.76% at 120 sites and 1.65% at 260 sites. Qualification needs recorded grid
expansion or direct joint-tail assessment, followed by recomputation.

The Laplace gradient can jump across cubic-spline knot surfaces through the
third site derivative. A small pointwise projected gradient alone is not a
smooth KKT certificate at or arbitrarily near such a surface; interval-aware
local perturbation checks must qualify optimizer convergence.

The wider-grid investigation independently verified the order-816 bank's
tail bound and direct comparisons. Its failure is downstream probability
arithmetic: both raw and compressed scoring first underflow at h=30 and
log-hazard -.875. The one permitted intermediate grid, [-14,-1], failed the
prespecified convergence/support checks. At h=6.05348 the projected gradient
is .001803; at h=30 a candidate's proposal maximum is -.986191, beyond the
grid. The last numerically valid node would leave only .04869 support slack,
less than the required .25. Starting base and SD perturbations remain finite
at log-hazard -1 (minimum approximately 6.85e-289), which does not establish
support for the attempted endpoint. Neither positive family fit is accepted.
The auditor separately rescanned at the pressured candidate detection SD
.476965 and at SD minus .0001: the same last valid/first invalid nodes remain.
At that candidate SD the minimum positive probability at -.9375 is 1.77e-311;
at -.875 one history probability is zero. The support-overlap conclusion
therefore does not combine incompatible starting and candidate SD values.
The review supports stopping grid adjustments and requiring log-domain
scoring before a new complete-profile attempt. It does not support a full
mesh rerun using the current arithmetic or changing the support guard.

The audited scope supports a developmental commit with the limitations made
explicit. It does not support calibrated declaration, coverage, effect recovery
or generality across maps. The smallest next numerical tranche is to repair
log-domain scoring and rerun the 35-node traversal, then test 260-site and
difficult-geometry canaries,
refine peaks/cutoffs and compare confidence-set topology before the 600-case
challenge and separate importance-integration sensitivity study.

Final verdict: conditionally supported for a development-only commit with
these limitations. Numerical qualification and whole-profile completion are
not supported. The independent audit changed no source or canonical result.
