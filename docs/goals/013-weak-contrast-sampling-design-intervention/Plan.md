# Goal 013 Implementation Plan

## Outcome

Deliver one deterministic contrast-balanced design, authenticate the accepted
weak-contrast evidence, run four locally calibrated intervention truth cells,
and produce the exact 18-file review pack and frozen decision.

## Task 1: Freeze The Design

- Add `src/latent_landscapes/goal013/design.py`.
- Reuse Goal 001 landscape, access, eligibility, cluster, site, and separation
  contracts.
- Implement deterministic `D0`, `D1`, `u`, `z`, tertile pools, constrained
  search, ranking, split, and design digest.
- Write failing design tests first, including exact replay and no access to
  stochastic or observation inputs.

## Task 2: Authenticate Existing Evidence

- Add strict readers for the accepted Goal 009 and Goal 012 packs.
- Verify required files, hashes, row identities, counts, classes, and
  decision operands.
- Recompute the six weak-contrast reconciliation rows from raw validation
  evidence.
- Reject missing, malformed, duplicate, non-finite, or tampered evidence.

## Task 3: Reuse The Frozen Inference

- Add a minimal optional fixed-input and seed-manifest path to Goal 012's
  truth-cell runner.
- Prove the default runner is unchanged.
- Add the two appended intervention-detection roots.
- Run only cells 00, 01, 02, and 04 with intervention fixed inputs.
- Preserve every Goal 012 inference, calibration, prediction, and class rule.

## Task 4: Compare And Classify

- Match accepted baseline and intervention validation rows by block, cell, and
  bank for descriptive differences.
- Build design, habitat, signal, cell-bank, and baseline-comparison summaries.
- Apply the frozen Goal 013 first-match decision.
- Make worker ordering deterministic.

## Task 5: Write The Review Pack

- Add `src/latent_landscapes/goal013/artifacts.py`.
- Add `scripts/run_goal013.py`.
- Write exactly 18 ignored files, including two readable SVGs.
- Require portable compute provenance for production.
- Refuse an accepted pack when implementation invariants fail.

## Task 6: Validate And Review

- Run focused red/green tests and predecessor regressions.
- Run Ruff, mypy, full pytest, build, diff check, reduced smoke, artifact
  reconciliation, and SVG render inspection.
- Obtain one independent preproduction code/science/provenance review.
- Make at most one material repair.

## Task 7: Run And Close

- Commit the accepted implementation exactly.
- Follow `Runbook.md` for one detached deep-server campaign.
- Retrieve and checksum the evidence.
- Independently recompute selectors, cutoffs, summaries, differences, gates,
  and classes.
- Record the result, commit exact documentation paths, fast-forward, and push
  only if accepted.
