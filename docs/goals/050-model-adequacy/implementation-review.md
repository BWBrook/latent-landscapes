# Goal 050 implementation review

20 September 2026. **GO for the registered timing run.** Production remains
conditional on passing the replay controls and the source-bound 12-hour budget
gate. This review examined the registration, runner, synthesis, CLIs, focused
tests and bounded remote wrappers before any timing or production launch.

## Scientific construction

The target is model adequacy for the assumed known-nuisance simulator on the
fixed 181-node effect grid and independent K131072/alpha1 integration bank. It
is not a biological goodness-of-fit claim, a test of unknown nuisances, or an
alternative-generator power study. Each complete history is split by the
frozen design. The training data select the lowest-index likelihood maximizer;
the primary statistic is the held-out joint log score at that fit minus the
held-out predator marginal log score. Repeating generation, selection and
scoring within every candidate-specific reference history correctly propagates
the selection step and the dependence within a complete spatial history.

The detector implements the registered lower-tail rank
`(1 + count(S* <= S))/1000` with inclusive ties. Its C99 uses candidate-specific
rank-990 LR cutoffs, includes a training maximizer, and takes the full-grid
Berger--Boos supremum plus gamma 0.01, capped at one. Sharing the same 999
calibration histories between C99 and score ranks is valid: the union-bound
argument does not require independence. The guarantee is marginal over the
reference table and a new history, conditional on the bank and finite grid; it
does not give exact 5% size for the realised frozen table.

The Goal 049 rank-950 effect table remains separate and unchanged. The four
old/fresh calibration-by-evaluation null cells and their paired contrasts use
the intended blocks. The 1,000-draw bootstrap independently resamples the four
blocks, shares original-calibration weights across all candidates and both LR
and score quantities, and shares original-evaluation weights across the six
truths. Exact constant series receive zero SE, standardized changes remain
undefined when SE is zero, and rates are clipped only for floating-point
roundoff. The predator score is descriptive and cannot trigger the primary
decision; its expected invariance across effect values is an enforced control.

## Pipeline and provenance checks

The runner regenerates each original history once and obtains the LR profile,
held-out joint vector, fitted index and both scores in that scoring pass.
Original profiles, fitted indices, evaluation held-out joint scores and opaque
IDs are checked at the registered tolerance before use. Fresh phases use roots
2026092004 and 2026092005 for both generated streams and opaque IDs. All
registered original and fresh stream values are checked for within-phase
uniqueness, pairwise separation and separation from the archived bank; the
synthesis root is reserved.

Goal 049 completion, its exact four identity controls, manifests, primary file
hashes, schemas and finite values are required. Source binding includes the
runner and synthesis modules and both CLIs. Resume shards bind source and seed
fingerprints and verify a content digest before reuse. Final phase NPZ files are
whole-file hashed, and synthesis rechecks the run contract, replay controls,
source hashes, file hashes, schemas and first-maximizer indices.

Timing uses the registered two-replicate prefixes under the legacy timing
contract. The projection scales complete phase wall time, adds integration and
measured fixed validation/hash overhead, then applies the registered 1.5
scoring factor. The production receipt independently binds the timing summary,
source/input identities, preparation charge, measured timing, production
projection, synthesis reserve and remaining timeout. The wrappers enforce one
run at a time, eight workers, one numerical thread, a 32-GiB address-space
limit, terminating timeouts and non-overwriting start/exit receipts.

## Verification and decision

At the reviewed source snapshot:

- 26 integrated Goal 049/050 focused tests passed in 7.15 s;
- scoped Ruff passed;
- strict mypy passed for both modules and CLIs;
- `git diff --check` passed;
- campaign SHA256 is
  `8423e5c0d43e4595bf652f63d0cecd4149e8c2ccedf183f836198c501def7f27`;
- synthesis SHA256 is
  `87821696eba34f2221b9035ad8a1a1ff31ed6567767d72f85afbd645be374339`.

Earlier review found and the final snapshot repaired duplicate replay scoring,
fresh-ID root reuse, incomplete timing accounting, unbound resume payloads,
vacuous original-control acceptance, partial seed checks, boundary-rate
roundoff, and an invalid timing-mode legacy configuration. No consequential
calculation or implementation defect remains in the reviewed snapshot.

Timing results still must demonstrate exact replay identities and affordable
complete workload before production. Production results will remain a
conditional known-nuisance, finite-grid adequacy baseline. A low null rejection
rate will not establish useful misspecification power, and the crossed null
cells cannot uniquely distinguish chance from a phase-specific mechanism.
Independent scientific review has already materially improved the implementation;
another pre-timing review is unlikely to change the launch decision. A final
result-level review remains necessary after synthesis because inference then
depends on the realised detector rates, memberships and crossed contrasts.
