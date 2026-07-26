# Goal 001 Plan

## 1. Rebuild the Process Primitive

- Add the minimal Python package scaffold.
- Adapt the accepted synth-medium landscape and deterministic weighted
  multi-source arrival calculation from SpatExt.
- Reconcile fixed cell, passability, source, habitat, and arrival invariants.
- Represent the estimand as a rate multiplier around the accepted baseline
  path-cost surface.

## 2. Freeze the Survey Design

- Lay down the synthetic road/transect network without consulting ecological
  or spread state.
- Select eligible five-site clusters within the four prespecified
  nearest-source geometry strata; this allocation variable is known design
  information, not latent spread truth.
- Freeze the 24-cluster training and 8-cluster holdout split.
- Test independence, eligibility, separation, balance, and leakage invariants.

## 3. Generate Direct Observations

- Simulate repeated direct detections at the frozen schedule with known
  constant detection probability and no false positives.
- Keep latent truth out of the analyst-facing observation table.
- Preserve stable record ordering and deterministic random streams.

## 4. Evaluate Exact Identifiability

- Construct exact breakpoint-defined likelihood-equivalence classes.
- Check structural identifiability of the ideal full-landscape process map.
- Evaluate the habitat process and the `neutral` geometry-only hard-front
  comparator with the identical observation likelihood and parameter domain.
- Report complete MLE class sets and nominal likelihood-ratio support unions.
- Compare held-out log-score and Brier-score ranges over each model's MLE set.
- Use total Bernoulli log score as the prespecified model-comparison criterion;
  retain finite Brier score as secondary descriptive corroboration when the
  hard-front comparator assigns zero probability to observed positives.
- Fit the habitat model to all clusters for the final recovery assessment.

## 5. Build the Human Review Pack

- Write the exact nine-file deterministic artifact bundle.
- Show landscape/access/design, spread/observations, and likelihood/holdout
  evidence in three legible SVGs.
- State observations, inferences, assumptions, and one-realization limitations
  separately in `review.md` and `summary.json`.

## 6. Validate and Review

- Run focused and full tests, formatting, linting, typing, build, and CLI
  checks.
- Generate twice and compare every artifact byte-for-byte.
- Obtain independent scientific and code/provenance review.
- Resolve material findings, then present the pack to Barry and stop.
