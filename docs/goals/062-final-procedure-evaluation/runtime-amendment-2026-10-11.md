# Proposed Goal 062 runtime amendment

11 October 2026 (Hobart). **Proposed; not approved.** This additive amendment
addresses the runtime-mismatch boundary in the approved
[registration](registration-2026-10-11.md). The
[ten-cell scientific amendment](amendment-2026-10-11.md), original receipts
and approved resource ceiling remain unchanged.

## Proposed decision

Accept the currently qualified deep-server runtime, whose Linux kernel changed
from `6.8.0-142-generic` to `6.8.0-146-generic`, and proceed with the already
approved implementation, bounded production run and independent audit. This
acceptance would be limited to the actual source, runtime and qualification
receipt identified below. It would not approve a later runtime change or a
failed qualification.

The recorded Python 3.14.5, NumPy 2.5.1, SciPy 1.18.0, PCG64, x86-64 and glibc
2.39 fields match. All 258 inherited source/script/test files and the two
package configuration files remain byte-identical. The new adapter was
[independently reviewed](implementation-review-2026-10-11.md), and production
still uses the fixed map, design, bank, models, optimizer, screen, reference
law and decision rule.

## Binding and qualification evidence

The proposed source-manifest SHA-256 is
`f8653edeca65c4ddfc5c3433ee6d199897b8ee41de1d0dcd6b4ead15346ceefe`.
Its remote root is
`/data/codex/scratch/goal062-final-procedure-20261011-qualification2`.
The [execution record](execution.md) preserves the superseded first attempt.

Qualification passed on 11 October at 03:21:32 UTC (14:21:32 AEDT). Its receipt
SHA-256 is
`01952a5aaf2b027db06e40726172e35d6fefab265b147169110aa581c83fab65`;
the complete current runtime's canonical SHA-256 is
`acd43764a5d0c2ee574007912a90236f669548a512c460cceb7768bb044e854a`.
All 165 bound evidence files were returned and rehashed with no mismatch.
The supervisor finished with exit zero and no remaining workers.

All 65 focused Linux tests passed. Re-auditing nine existing effect tables
and three screening tables reproduced the accepted reference arrays exactly;
eight full-bank public histories reproduced all fitted parameters, objective
values and numerical statuses exactly. Ten mechanical histories passed
generator, fit, screening, decision and held-out audits; two diagnostic
histories passed all profile/lattice reconstructions. Maximum observed
independent score discrepancies were below `3.64e-12` nats. These finite checks
support observed compatibility, not universal equivalence.

All 51 workers were observed in the concurrent resource probe, which used
28.58 GiB, or 35.73 GiB with 25% headroom, below the 64 GiB cap. The whole-run
supervisor peak was 28.78 GiB. The workload qualification model gives a
conservative 40.579-hour projection, within 72 hours. Retain the approved
46–57-hour planning allowance because the timing samples are small and
production scheduling, anomalies, transfers and reporting remain uncertain.
The concurrency probe covers loaded producer/auditor resources and
representative scoring; a simultaneous 51-optimizer peak remains unmeasured.
The production process-group memory guard remains binding throughout the run.

[Independent receipt review](qualification-review-2026-10-11.md) conditionally
supports accepting this exact runtime. It finds no required correction or
repeat qualification and preserves the explicit human decision boundary.
No approval record exists and no new production reference or evaluation
history has been generated. The final
qualification state is `qualified_pending_runtime_review`, with
`production_authorized=false`.

## Effect on the reference panel

Approval would retain the 765 existing screening tables and 299 existing
effect tables under their original source/runtime receipts and generate the
remaining 466 effect tables under the newly accepted runtime. Original tables
and receipts would not be regenerated, rewritten or relabelled. The runner
verifies their custody, independently audits every new table and completes the
whole panel before generating evaluation histories.

Compatibility qualification compares selected inherited reference
reconstructions and accepted public refits with the original saved evidence.
These checks assess observed numerical compatibility. The old receipt did not
hash executable or extension binaries, so binary identity with the previous
environment is not established. Current binaries, build configuration, library
thread settings and runtime fields are recorded prospectively.

## Unchanged scope and limits

The campaign remains ten cells with 500 independent histories each, 465,534
new effect-reference histories, 50 prespecified diagnostic histories and the
registered anomaly-diagnostic allowance. Its evaluation and bootstrap seed
ledgers must be persisted and checked before new production reference
generation. Numerical failures remain registered outcomes; source, scorer or
integrity discrepancies block release.

The allocation remains at most 51 workers, one numerical-library thread per
worker, 64 GiB aggregate RSS, at least 50 GiB initial free scratch and one
72-hour production deadline retained across resumptions. Approval would not
reduce sample sizes or audits, change scientific endpoints, authorize further
retuning, purchase compute or change host configuration.

All operating-characteristic claims remain conditional on the registered
fixed map, design, bank, algorithm and realised reference panel. B100-A results
remain descriptive for its specified misspecification law. Compatibility
checks do not establish equivalence for every possible history or grant new
landscape, causal, model-discrimination or interval-coverage claims.

## Activation rule

After completed qualification and independent receipt review, an explicit
Barry decision is required by the registered runtime-mismatch boundary. An
approval record must bind the actual qualification-file SHA-256, complete
runtime digest and source-manifest digest. The supervisor and production
runner verify those bindings and recheck the runtime before any new production
draw. A missing approval or changed binding leaves production blocked.
