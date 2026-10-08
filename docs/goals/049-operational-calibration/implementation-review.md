# Goal 049 implementation review

20 September 2026. **Independent methodological review before timing or
production.** This review covers the known-nuisance calibration runner and its
scientific interfaces. It does not accept a timing result, authorise production,
or assess results that have not yet been generated.

## Decision

**GO for the registered timing gate.** The data-generating process, score
construction, bank variants, seed design, and rank rule implement the registered
experiment. Scientific identity controls now gate completion. Production
requires the parent-owned timing/total receipt, and the actual launch wrapper
enforces the registered wall-time, worker, and aggregate-memory limits. No new
scientific design decision is required.

## Scientific and implementation checks

| Check | Evidence and result |
| --- | --- |
| Data-generating process | `generate_observations()` calls the accepted `arc2b_campaign.generate_paired_datasets()` directly. The current generator, fixed-input, landscape, design, spread, survey, and observation sources are unchanged from frozen Goal 045 source `e8c08f10f7b67118a85ee37770d8ee48ee2c213a`. Generating truths vary only the prey-effect multiplier; spread is fixed at rho=1, background hazard at 0.002/day, and both detection probabilities at 0.65. |
| Sampling and observation | The live fixed design has 160 unique sites, 120 training and 40 holdout sites with cluster isolation. Sites are sorted by `site_id` in both the generator and bank construction. The reviewed live `(site_id, cluster_id, split, row, col)` digest is `4c86a821d813442c714e12a38d522c98722283687cfdb6b442f8600cd9c97bf6`. |
| Original bank | Timing and production require the exact nested Goal 045 bank. File, array, low-prefix, seed, site-order, shape, dtype, finite-value, and nonnegative-arrival checks are applied before scoring. |
| Numerical variants | The four registered variants are ordered explicitly: K65536/alpha=0.5, K131072/alpha=1, K131072/alpha=0.5, and K131072/alpha=0.25. The primary pair has identical pseudocount fractions, `0.5/65536 = 1/131072`. Independent formula tests verify the alpha reweighting to numerical tolerance. Every variant is recalibrated separately. |
| Randomness and replication | Calibration, evaluation, bootstrap, and archived-bank roots are distinct. The realised 3,996 calibration stream values and 4,000 evaluation stream values are internally unique and mutually disjoint. One four-stream seed tuple is shared across truths within a replicate, implementing the common-random-number pairing required by the bootstrap; replicate tuples remain independent within each phase. |
| Registered grid and rank | Production is fixed to 181 nodes from 1 to 10, 999 calibration histories per node, rank 950, and 1,000 evaluation histories at each of h={1,2,3,4,5,10}. Cutoffs use zero-based partition index 949 and membership uses inclusive `<=`, giving the registered 950/1000 tie-free marginal reference. |
| Analyst/evaluator separation | `AnalystHistory` contains site identity, split, detection counts, and known prey-detection probability, but no row/column, generating effect, role, arrival, extirpation, or latent state. `score_observations()` ignores the opaque dataset identifier and accepts no truth argument. Scores and holdout curves are flushed and hashed before evaluator truth is joined. Opaque identifiers remain provenance labels rather than a cryptographic blinding claim. |
| Prediction context | Fitting uses only the 120 training sites. Frozen holdout joint-score curves are retained for the 40 holdout sites. At fixed rho, comparing the fitted effect with effect=1 cancels the common predator marginal and yields the conditional prey-score contrast; set construction cannot change the fitted point or its prediction. |
| Resume and provenance | Per-replicate slices are flushed, hashed, and journalled with the frozen run fingerprint. Resume verifies fingerprint, seed hash, and slice hash before skipping work. The timestamp was removed from fingerprint construction during review. The run contract now records all Python source files, the runner, registration, bank identities, configuration, variant order, and seed manifests. |
| Freeze timing | Calibration and evaluation score arrays, holdout curves, and opaque IDs are hashed in `frozen_scores.json` before truth-sidecar construction. The evaluator rechecks every frozen file before computing cutoffs or membership. |

## Material review findings and disposition

1. **Completion was not initially conditional on the identity controls.** The
   evaluator could record a failed candidate/oracle or maximizer identity while
   the run summary still said `production_scores_complete`. Production
   completion must require all non-vacuous registered identities; construction
   guarantees such as common fitted MLE/prediction and inclusive `<=` semantics
   should be labelled as such rather than presented as independently measured
   tests. **Resolved and tested.**

2. **The direct production CLI initially had no timing-receipt gate.** The
   registration forbids production until measured scoring and bootstrap timing,
   the 24-hour ceiling, worker limit, and 32-GiB aggregate-memory limit pass.
   Production now requires the parent-owned receipt bound to the timing summary
   and declared total, while the bounded launch wrapper enforces the 24-hour,
   eight-worker and 32-GiB limits. The production record will include the
   bootstrap fixture/report hashes. This is a reproducible authorised run, not
   an adversarial attestation system. **Resolved for the registered workflow.**

3. **Resume initially included a creation timestamp in the run fingerprint.**
   That made an otherwise identical resumed invocation produce a different
   fingerprint. The timestamp now sits outside the hashed contract, and the
   smoke test resumes the same directory with an unchanged fingerprint.
   **Resolved and tested.**

4. **The first provenance set covered only selected direct modules.** Changes
   in landscape, sampling, spread, or observation dependencies could otherwise
   mix incompatible shards. The contract now hashes all repository Python
   source plus the runner and registration. **Resolved; a production receipt
   should also retain the locked environment identity.**

The opaque-ID construction can be mapped back to an ordinal by someone with
the source and seed fingerprint. This does not affect the implemented score
firewall because the scorer never reads the identifier, and full reproducibility
already permits regeneration of synthetic truths. Independent opaque IDs would
better match the prose but are not a scientific blocker.

## Verification performed

- `tests/test_known_nuisance_calibration.py` includes passing smoke, resume,
  forced-identity-failure and mandatory-production-receipt tests.
- `tests/test_integration_weights.py` plus calibration tests: 19 tests passed.
- Ruff and strict mypy passed for the calibration module and runner.
- The 999-sample quantile-band review independently confirmed ranks 935 and 963
  for the pointwise 95% population-quantile band; the calibration cutoff itself
  remains registered rank 950.
- No production histories, timing campaign, or bootstrap campaign were run in
  this review.

## Residual limits

Passing these implementation controls will establish a reproducible,
model-conditional finite-grid calibration experiment. It will not establish
unknown-nuisance validity, exact integration, off-grid coverage, transfer to a
new landscape or observation design, or ecological generality. The next action
is the already registered canary and timing gate. Production remains conditional
on the measured resource receipt and bounded launch wrapper.
