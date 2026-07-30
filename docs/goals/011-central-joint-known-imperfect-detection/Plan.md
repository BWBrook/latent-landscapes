# Goal 011 Implementation Plan

**Goal:** Deliver one central-truth joint `(rho, eta)` recovery benchmark under
known imperfect detection, retaining complete two-visit histories.

**Architecture:** Compose Goal 004's observation/history likelihood with Goal
007's joint bank weights, support summaries, calibration, prediction, and
decision machinery. Add a thin `goal011` package; do not modify earlier goals.

## Constraints

- One central truth and one known observation model.
- Expanded eta grid through `2.5` is primary; `eta <= 2` is a non-gating
  projection calculated from the same profiles.
- Exact Goal 007 process streams and old bank slices replay.
- Complete 12-record site histories are retained.
- One production campaign; no retuning or rescue run.
- Generated artifacts and remote evidence remain ignored.

## Task 1: Goal Packet And Tests

- Create the four Goal 011 packet files.
- Write failing focused tests for the joint history likelihood, tied MLEs,
  complete/disagreeing visits, seed identity, old-bank replay, stream
  separation, fixed counts, prediction semantics, domain projection, decisions,
  and artifact contract.
- Record the expected red state before implementing production APIs.

## Task 2: Minimal Scientific Implementation

Create:

- `src/latent_landscapes/goal011/__init__.py`
- `src/latent_landscapes/goal011/likelihood.py`
- `src/latent_landscapes/goal011/benchmark.py`
- `src/latent_landscapes/goal011/artifacts.py`
- `scripts/run_goal011.py`
- `tests/test_goal011_likelihood.py`
- `tests/test_goal011_benchmark.py`
- `tests/test_goal011_artifacts_cli.py`

Reuse public Goal 004 and Goal 007 APIs. Implement only the new joint-history
marginalization, paired seed/data path, expanded/old-domain summaries, and
Goal 011 result/artifact layer.

## Task 3: Local Acceptance

- Update `README.md`, `docs/programme.md`, and `Log.md`.
- Run focused tests, relevant predecessor tests, Ruff format/check, strict
  mypy, full pytest, build, and one reduced CLI smoke.
- Inspect the diff and reduced artifacts.
- Obtain one independent preproduction review.
- Make at most one material repair.

## Task 4: One Remote Campaign

- Commit the accepted preproduction implementation.
- create and checksum one Git bundle;
- stage a unique run directory under `/data/codex/scratch/` on `deep-server`;
- verify a clean detached checkout and frozen environment;
- run focused tests and one reduced smoke;
- launch one single-process production command in a named `tmux` session;
- write start/end time, exit status, log, and `DONE`/`FAILED` sentinels; and
- return the exact WSL probe command and an evidence-based ETA to Barry.

Do not poll continuously. Stop after launch and await a wake-up.

## Task 5: Result Audit And Publication

- Retrieve the complete run evidence with checksums.
- Recompute cutoffs, bank summaries, domain comparisons, decisions, and
  artifact identities independently from returned tables.
- Inspect all three figures once against the source tables.
- Obtain one independent final review.
- Record observations, inferences, assumptions, and limitations in `Log.md`.
- Publish exact accepted paths only if all hard gates pass.
