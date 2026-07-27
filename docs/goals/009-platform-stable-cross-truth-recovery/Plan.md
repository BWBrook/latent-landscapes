# Goal 009 Implementation Plan

## Outcome

Complete the unchanged Goal 008 campaign with a platform-stable central
continuity gate, or preserve enough trusted evidence to identify any remaining
hard block without a further production run.

## Task 1: Reconciliation Tests

Modify the Goal 008 benchmark and tests.

Write failing tests for recursive canonicalization, exact structural
continuity, reviewed canonical reference hashes, one-ULP tolerance, material
numeric rejection, structural rejection, and non-finite rejection.

Derive canonical expected hashes from accepted Goal 007 artifacts in an
independent one-time audit. Hard-code only the reviewed constants and
canonicalization metadata.

## Task 2: Diagnostic Persistence

Retain cell invariant maps in the aggregate result.

Add a three-file blocked diagnostic writer and tests for:

- exact file contract;
- strict JSON;
- complete false-invariant reporting;
- central observed-versus-expected evidence;
- 27 cell-by-bank summaries;
- portable trusted provenance;
- deterministic hashes;
- tagged non-finite values; and
- stale-directory refusal.

Update the Goal 008 CLI so a returned blocked campaign writes diagnostics and
then exits nonzero. Worker exceptions and pre-campaign trust failures continue
to exit nonzero without claiming a completed campaign.

## Task 3: Local Acceptance

Run focused tests, diff checks, Ruff, mypy, the full test suite, and build.
Use one focused review-and-repair pass only.

Obtain an independent pre-production review of the central comparison,
diagnostic completeness, frozen scientific surface, and source diff.

Create one exact pre-production feature commit.

## Task 4: Trusted Remote Campaign

Create and verify a Git bundle and manifest. On `deep-server-ts`, verify the
bundle, detached commit, clean status, lockfile, runtime, focused tests, and
nine-worker miniature smoke.

Run one unchanged production campaign using nine workers and one numerical
thread per worker. Preserve command, stdout, stderr, exit status, timing,
memory, and recursive checksums.

Do not rerun.

## Task 5: Review And Publication

For a scientific pack, recompute all decisions and inspect all figures. For a
diagnostic pack, identify the exact blocker from the retained fields.

Request one independent final review. Update the Goal 009 log with observed
evidence, interpretation, limitations, and the publication decision.

If accepted under the authority in `Goal.md`, commit the exact documentation
update, fast-forward `main`, push, and verify a clean synchronized checkout.
