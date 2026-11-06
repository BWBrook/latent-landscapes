# Independent numerical entry review

Reviewed Sprint 1 source at `583c1e3` against `2e96bfc`, including the
`48de534` eigenvalue-floor normalisation, the packet, mode diagnosis,
production entry point and numerical tests. This advances the Sprint 2
procedure-qualification gate. No fresh qualification, training or validation
outcomes were generated.

**Entry verdict: repair required before qualification.** The normalised floor
is algebraically consistent, but the outer optimiser can certify a known
stationary minimum as successful. The entry point also misclassifies reduced
family execution errors. The bounded numerical repair below addresses the
first issue; independent review of that repair and integration of the separate
entry-point repair remain required.

## Material findings in the handover commit

### N1: second-order rejection does not govern acceptance

`src/latent_landscapes/spatial_profile.py:1114–1171` detects negative curvature
but returns success after a failed saddle escape, or after three escapes,
because the final predicate checks only the projected gradient. The
three-escape branch even reports “no ascent direction” when negative curvature
is still present. A final iteration can likewise finish without any
second-order check of the returned point.

Independent one-dimensional witness, using the actual optimiser:

```
criterion = x**2 - x**4
gradient = 2*x - 4*x**3
start = 0; bounds = [-2, 2]
```

At the handover commit it returns `x=0`, criterion `0`, success `True`, and
“projected gradient below tolerance; saddle escape failed”. Both full-radius
trials have criterion zero, whereas `x=0.5` has criterion `0.1875`; the true
maxima are at ±sqrt(0.5) with criterion `0.25`. This is a demonstrated solver
failure, not evidence that any archived ecological fit has the same defect.

Fixing the optimiser status alone is insufficient: `_fit_family` at line 1231
and `ReducedFamily._constant_candidates` in `scripts/fit_dataset.py:253`
compute eligibility from evaluation success and projected gradient, ignoring
optimiser success. Any repair must propagate the second-order result into
candidate eligibility. The benchmark adapter already requires optimiser
success; the direct reduced-family path still needs the matching repair.

The existing diagonal replacement for unavailable Hessian columns can guide
continued optimisation but cannot certify second-order stationarity. Treating
that replacement as measured curvature would preserve the same class of false
acceptance. Qualification should retain such numerical failures rather than
silently accepting them.

### N2: reduced-family execution errors become scientific fit failures

At `scripts/fit_dataset.py:787–797`, the `guard=False` stage rethrows every
exception, then the outer handler appends it to `family_failures` without
recording an execution error. Therefore a `MemoryError` or `OSError` in exposure
or constant fitting becomes `family_fit_failed`, contrary to the closed
taxonomy and retry policy. Preserve the exception in the execution-error
ledger and give it the documented priority; retain the family diagnostic too.
The parent assigned this repair to another editor.

## Normalised floor and deterministic score

The implemented floor is

```
f(x) = (x + tau*exp(-x/tau)) / (1 + tau*exp(-1/tau)), tau = 0.1.
```

It satisfies `f(1)=1`. As sigma approaches zero, the combined matrix tends
to the identity, so the determinant contribution tends to zero and the
positive branch joins the exact-zero score. Dividing by the constant changes
the positive-family score by `n/2 * log(1 + tau*exp(-1/tau))`; it leaves
`f'/f` and all derivatives unchanged. It does change comparisons with the
separate zero branch, which is the intended continuity correction.

The production and audit evaluators call the same floor function. The
core-gradient trace and implicit-mode terms are consistent with differentiating
this modified determinant. Existing tests independently compare gradients to
re-optimised finite differences where the floor is active, check endpoint
gradients, exact cache keys and reordered calls, strict latent-mode convergence,
and production/audit score equality. These pass in this review.

The latent solver starts only at zero. Its convergence and failure rules depend
on fixed inputs rather than warm-cache availability. Actual code accepts a
latent mode only after the strict gradient/decrement and positive-definiteness
test; the roundoff clause merely accepts a Newton step and iterates again.
Packet section 2 should clarify this, and replace its stale unnormalised floor
formula and “standard Laplace, with no clipping” wording with the actual
regularised criterion. The later status section does record the normalisation.

## Audit, ties and scientific limits

The bounded latent audit is a deterministic failure rule on the selected
procedure, not proof of a global latent optimum or exact marginal likelihood.
The code records both joint-objective and modified-criterion gains and retains
the prespecified higher-joint-mode failure trigger. The LR margin remains an
empirical choice: the exhaustive subset must actually test it before training.
No inference that the old 4.53-point discrepancy bounds unseen mode gains is
supported or needed.

The contact rule removes only a tied positive branch's lower-sigma contact;
raw scores, branch ownership and other contacts remain. Its use is conditional
on the search returning eligible branch fits. Neither the floor correction nor
the tie rule justifies weakening unresolved-family or envelope guards.

## Bounded repair made after this independent finding

At the parent's request this reviewer edited only
`src/latent_landscapes/spatial_profile.py` and
`tests/test_spatial_profile.py`:

- Require an explicit completed second-order check for optimiser success.
- Backtrack the saddle escape through 13 deterministic radii (the current
  radius through radius/4096), testing both signs, so an overshooting full
  step can find the local improving direction.
- Return failure on an exhausted escape budget, unsuccessful escape,
  unavailable curvature at stationarity, or iteration exhaustion without a
  final certificate.
- Require optimiser success for `_fit_family` candidate eligibility.
- Add six regression tests covering the overshoot witness, failed escape,
  unavailable curvature, the three-escape cap, final-iteration certification,
  and propagation into family eligibility.

The criterion, eigenvalue floor, fitted parameter bounds and latent-mode
selection are unchanged. Search/acceptance behaviour is deliberately stricter;
the six old diagnostic histories must be replayed before their prior resolved
statuses can be claimed for this repaired procedure. Qualification has not
begun, so this is a prospective entry repair, not a fresh-panel result. The
parent will obtain independent cross-review of the patch before using it.

## Verification

Before repair, the two focused suites passed **61 tests** despite the independently
reproduced false success. After the final numerical patch,
`tests/test_spatial_profile.py` passes **49 tests**. An intervening combined
run passed **72 tests**, including concurrent entry-point test additions;
the parent should report its final integrated count separately.

```
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m pytest -q tests/test_spatial_profile.py
.venv/bin/ruff check src/latent_landscapes/spatial_profile.py tests/test_spatial_profile.py
.venv/bin/ruff format --check src/latent_landscapes/spatial_profile.py tests/test_spatial_profile.py
.venv/bin/mypy src/latent_landscapes/spatial_profile.py
git diff --check
```

These checks pass. Checking the test module with strict mypy also surfaced an
existing optional-mode narrowing error at `tests/test_spatial_profile.py:258`,
outside the repair; source-module mypy is clean. No production profile,
qualification outcome, cluster job, commit or board post was created by this
reviewer.

## Independent cross-review of the parent's failure-path repair

This is a separate review of edits by the parent, rather than self-review of
the numerical patch above. Scope: `scripts/fit_dataset.py`,
`scripts/run_development_profile.py`, their tests, and downstream exception
handlers reached by their production calls.

**The parent changes correctly propagate execution errors and require
optimiser success for constant-family eligibility.** The `Run.record_error`
path preserves exception type, stage and traceback; reduced-family
`MemoryError`/`OSError` now receive `execution_error`, while an ordinary
scientific fit exception retains `family_fit_failed`. Tests exercise both
exception kinds and the scientific-failure control, and reject an uncertified
stationary constant-family candidate.

The cross-review found two additional active-path defects and the parent
repaired them before qualification:

1. `profile_level_sets.refine_level_set` caught execution exceptions from its
   callback and converted them to unavailable levels. An injected callback
   independently reproduced `MemoryError -> unavailable` and
   `OSError -> unavailable`. Both now rethrow. The same explicit propagation
   was added to `PanelSearch.post_search_points` and
   `Qualification.outer_diagnostic`, preventing a future comparison/diagnostic
   caller from relabelling resource failures as scientific failures.
2. `ReducedFamily.run` could return when its free envelope stabilised even if
   cutoff construction was unavailable. A small synthetic test independently
   reproduced a family marked `available` with an `unavailable` interval.
   It now rejects unavailable cutoff sets; the parent added a regression test.

The direct likelihood, latent solver and numerical-derivative handlers catch
numerical/domain exceptions only and do not swallow these execution errors.
The remaining `_git_identity` fallback records missing source identity if Git
cannot execute; reconciliation must still refuse promotion without source
provenance. Directory/output failures outside a stage terminate the process
without a complete receipt and must be treated as execution failures by the
campaign reconciler, not as resolved datasets.

A combined run of `test_fit_dataset`, `test_profile_level_sets`,
`test_development_profile_search` and `test_qualify_spatial_profiles` initially
exposed an integration-test mismatch after the separate high-sigma anchor
source-label change. The parent corrected its candidate-preservation assertion
to compare exact original and new candidate identities rather than an assumed
number of calls. The final settled run passes **95 tests**. The parent's
failure-path repair passes this independent review.

## Exact-pair audit producer implemented after review

At the parent's request this agent subsequently implemented
`scripts/audit_sprint2_pair.py` and `tests/test_sprint2_pair.py`. This is
implementation evidence, not independent review of those two files.

The `anchors` command writes `sprint2-common-anchors-v1`; the `gradients`
command writes `sprint2-free-gradient-v1`. Both write `receipt.json` under a
new output directory. Interfaces were agreed with the independent reducer and
campaign-preparation authors. Every audit requires the original clean source
commit, an exact complete input/source hash inventory, and the hashed nested
search receipt. Source/input identities are checked again after evaluation.

Common anchors cover the exact union, separately for spatial standard/tight,
exposure and constant, of profile nodes, selected free locations, every cutoff
root and component endpoint. Fresh fixed-profile fits use recorded parameter
starts and deterministic neighbours. Original point values and contacts remain
unchanged; fresh values are separate diagnostics. A discovery above the frozen
free maximum by more than 1e-4, a replay difference above the existing 0.01-W
tolerance, or a contradiction of frozen sets is nonpassing. No outer free
maximum is refitted or silently promoted. Spatial membership respects the
stored verified root bracket and residual tolerance; reduced-family membership
uses the 0.01 residual tolerance at exact recorded roots only.

Gradient evidence contains all eight search/regime/step combinations. Every
stencil point re-solves the deterministic latent mode; central or second-order
inward differences retain unprojected boundary derivatives. Both step scales
and the tolerance match the prospective entry document. Missing/nonfinite
stencils remain unavailable. Known numerical exceptions during probing are
scientific failures; metadata/source mismatch is unavailable; execution errors
retain a receipt and return exit code 2 for an unchanged-identity retry.

Twenty producer tests pass, including independent reducer consumption of exact
anchor evidence with a 100-unit raw bank-score offset, all eight gradient
checks, inward stencils with nonzero boundary derivatives, preservation of
original points and tight-fit seeds, source/input tampering, and the execution
retry boundary. Ruff passes. No production audit, new history or bank was run.
The parent must independently review this producer before qualification.

## Independent review of the integration-screen wrapper

The parent implemented `scripts/screen_sprint2_importance.py`; this reviewer
read its target, proposal, normalisation, stopping, status and source-binding
paths without modifying that script or its tests.

The target is the direct sampled-site likelihood multiplied by the normalised
Gaussian prior. `SpatialTarget.log_normalizer` retains
`0.5*(logdet(sigma^2*K) + n*log(2*pi))`; the eigenvalue floor does not alter this
importance target or its prior normaliser. The floor belongs to the comparison
score, replayed at the recorded positive-family outer parameters. The zero
family is replayed separately. At the free anchor, each variance family's own
recorded free parameters (including its own h) are preserved; at each 3.84 root
the recorded fixed-h parameters are used. The result is a fixed-outer comparison,
not an importance-reoptimised profile or a measured root displacement.

The two stream identifiers differ and the same identity across anchors supports
the intended paired contrasts. The highest level is 262,144 draws per point per
stream, reached through the five declared doubling levels. Previous levels,
point estimates and mode diagnostics remain as evidence. Precision or weight
failure at the cap stays indeterminate. This cap describes the largest level;
computational costing must include the work at previous levels too.

Review found a vacuous-pass edge case: with no 3.84 roots, the inherited screen
has zero contrasts, and its empty comparisons could yield
`pointwise_screen_passed`. A fabricated Estimate independently reproduced that
result. The parent repaired the wrapper to emit **`no_root_contrasts`**, retain
the descriptive free-anchor evidence and stop without claiming an LR screen
passed. The parent also added an explicit clean, nonnull source requirement,
checked loaded data identity against the fit, and hashed the imported decision
helper in addition to the wrapper and original source/input inventory.

**Verdict: accepted for the stated descriptive purpose after those repairs.**
The combined wrapper, importance-screen, spatial-target and importance-reference
suites pass **37 tests**. No importance calculation on a real campaign history
was run for this review. Descriptive statuses, including unavailable and
no-root cases, remain in the denominator and do not qualify the inference
procedure or authorise training.

## Parent review of the independent audit producer

The parent reviewed `audit_sprint2_pair.py` after the numerical delegate's
implementation. Its spatial probes retain both regimes' original neighbour
starts and free vectors; reduced probes retain original-node, neighbour and
free parameters. The exact union includes retained nodes, free locations,
roots and component endpoints in all four views. Original values are retained
in the comparison, while fresh improvements beyond the frozen maximum or
inconsistent membership/contact evidence become failures. Independent-bank
comparisons keep each bank's own normaliser. No probe silently updates the
reported fit or calibration set.

Gradient stencils re-optimise the latent mode at each perturbed coordinate,
use raw derivatives at bounds and retain both step sizes. Explicit unavailable
stencils cannot become a pass. Source/input/receipt drift is kept separate
from numerical probe failures; memory and I/O failures return a retryable
execution status. The reduced-profile serializer now supplies the original
parameter vectors and source labels this audit requires; its regression check
compares those values directly with the actual fitted nodes.

Accepted for use in the prospective qualification pipeline, subject to the
compute-node pilot and full evidence gates. Fabricated-receipt tests establish
interfaces and failure behaviour; they do not establish numerical qualification.
