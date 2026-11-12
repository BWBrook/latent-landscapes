# Incomplete qualification run: conclusive rejection bound

This advances Paper 1 charter pillars 3, 4 and 6 and Sprint 2's registered
numerical-qualification decision. The candidate is frozen at 99af520. The run
remains incomplete, but validated failures already prevent it from passing
the registered gate. No threshold, dataset, failure classification or numerical
method has changed.

The [summary](rejection-summary.json) records receipt hashes and bounds.
The [independent gate review](independent-gate-review.md) verifies the failed
receipts, their source/input bindings and the deduction. The
[numerical autopsy](numerical-autopsy.md) separates observed solver failures
from hypotheses and proposes a bounded next diagnostic.

At the snapshot, 486 task records comprised 417 resolved, 27 terminal numerical
failures and 42 without final receipts. The 27 failed fits represent 14 unique
datasets. Ten are required base cases, each with a failed dense fit. With 162
base datasets, any possible completion has mean failure fraction at least
10/162 = 0.0617284. The registered finite-panel score adds a nonnegative
dispersion term, so it cannot satisfy its 0.05 gate. This proof does not assume
that adding failures monotonically raises the entire score.

Seven failed base cases are A/B: their independent mean-only lower bound is
7/108 = 0.0648148. They also violate the predeclared C-only condition for A/B
continuation. Four failed datasets are nonbase: two enriched and two trend.

This conclusively rejects the current numerical candidate while the run and
full qualification packet remain incomplete. The registered reducer's
missing-evidence status has not been replaced with a fabricated completed
result. Missing execution attempts stay incomplete. These are fixed-panel
computation criteria, with no population-error or biological interpretation.

The delayed email had an operational cause. Six allocations still appeared
running after their three nodes rebooted, but direct checks found no surviving
project workload processes. Their accounting and fit-event streams were stale.
After preserving records and all 42 incomplete attempts, the parent cleared
only those six defunct allocations. The original array then finished, releasing
the existing receipt-reconciliation/email job. It finished with the expected
nonzero exit after 25 minutes 32 seconds: 417 resolved, 27 scientific failures,
42 missing and zero invalid records. Email delivery is not independently
confirmed. Walltime losses and other terminated attempts remain preserved.

Both parent and independent Codex (GPT-6.1 Sol) checks validate all 27 failed fit
receipts and their 162 output files. The autopsy identifies 16 unresolved
positive-variance exceptions with outer trust-region collapse, nine first
constant-fit failures without retained candidate diagnostics, and two envelope
rejections of higher unconverged branches. Reported latent-mode convergence
does not establish outer convergence. Overflow warnings are a lead; causation
has not been demonstrated.

The next proposed tranche is three observed diagnostic checkpoints and scalar
loss-derivative stress checks, before selecting one reviewed repair. Preserve
the criterion, eligibility and envelope guards. Archive full new start, step,
gradient and curvature diagnostics; missing historical vectors prevent claims
of exact warm-start replay. No blanket retry or repair was launched. Training
and validation remain closed.

To reproduce the logical bound, restore the hash-matched failed attempts and
frozen panel/source, verify each failure receipt against its task-output hash,
deduplicate required failed fits by dataset, then calculate 10/162 and 7/108.
The independent note gives exact dataset IDs and maps. Standard task
reconciliation checks retained execution evidence and must retain the 42
unfinished tasks.

For future arrays, per-subjob abort notifications should accompany the aggregate
completion check. The existing parent-only abort setting did not provide an
early notice for individual failed subjobs. No new monitoring automation was
created during this incident.
