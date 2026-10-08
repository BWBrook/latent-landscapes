# Goal 061 blinded training methods review

5 October 2026, Hobart. **Independent pre-observation review; implementation
conditions accepted.** No training values, holdout observations, sealed truth,
private key or production result was inspected for this review.

## Scientific target and scope

The primary target is a casewise calibrated declaration of a post-arrival prey-
loss hazard effect. The statistic is the adjusted-background free-`h` versus
adjusted-background `h=1` training likelihood ratio. The nuisance set is selected
by the registered pre-only immediate-axis screen over the complete 765-node grid.

The casewise false-declaration bound of at most 0.05 applies only to an exact-
family, on-grid, `h=1` null, averaged over observation and reference generation
conditional on the fixed map, sampling design, numerical arrival bank and frozen
algorithm. It is not conditional on the realized reference tables. It does not
provide four-case family-wise control, B100-A or off-grid validity, effect-size
coverage, profile coverage, power, or empirical operating-rate validation. The
four sealed cases are case studies rather than independent calibration
replicates.

The later prediction target is the fixed training fit's conditional-prey score
on 40 held-out sites in eight dependent clusters. The held-out stage does not
refit or select models and does not support site-IID uncertainty claims. It is
outside Goal 061's current training-only computation and audit.

## Data-generating and observation processes

The fixed public map and 160-site clustered sampling design determine the whole-
map hazard normalization and the 120/40 training/holdout split. The K=131,072
arrival bank supplies a fixed empirical numerical integration rule. It does not
replace the reference generator: every effect reference receives its own full
correlated-spread realization. Each reference is generated over all 160 public
sites and only then evaluated on the fixed training mask.

Screening uses exactly 99 pre-only references at every node. Each reference is
scored at its generating node and immediate beta, mean-hazard and detection-SD
neighbours. The retained set is `C={node:q>.01}` using inclusive plus-one ranks.
Exactly 999 full `h=1` effect references are required for every node in the
complete union of the four retained sets. The effect rank is inclusive, with the
registered absolute/relative tie tolerance, and the casewise value is
`min(1,.01+max_C p_nu)`.

The reference streams remain root `2026100404`, namespace `59`, domain `5` for
screening and domain `6` for effects. Lazy construction changes storage and
scheduling only. It cannot change addresses, counts, generators, fitting,
retained nodes, stopping rules or rank arithmetic.

## Decisive implementation findings

The orchestration may proceed with two explicit semantics.

1. The observed adjusted pair is valid only when both stored scores are finite,
   both fits have status `converged`, and free minus null is at least `-1e-6`.
   A finite clamped statistic cannot rescue an invalid pair. An invalid observed
   adjusted pair causes casewise abstention.
2. Profiles, constant-model comparisons, the 1,350-point lattice and nested-bank
   comparisons are diagnostics. A profile or lattice point exceeding the main
   fit, a failed profile node, or a half-bank movement does not edit the frozen
   main fit, statistic or declaration. It pauses report release for bounded
   diagnosis. A scorer, source or schema defect stops execution and is repaired
   with original results preserved; confirmed behaviour of the frozen algorithm
   is reported as numerical fragility without refitting or replacement.

The first locked mechanical qualification stopped before production because the
independent auditor treated `exp(log(10)) = 10.000000000000002` as a genuine
parameter-bound violation. The frozen fitter already recognizes decoding spill
within eight ULP of every physical bound. The auditor now applies that same
representation tolerance to `h`, beta, mean hazard and detection SD, while
directly scoring the exact stored floating-point value without snapping it.
Values more than eight bound-ULP outside the registered domain still stop the
audit. The original `ad197` freeze and failed qualification logs remain
preserved; the repair requires a separate freeze and run root.

The one-SQLite-file-per-node effect store is scientifically acceptable. Every
row is uniquely keyed by its registered reference index and atomically binds the
observation blob, payload, hashes, fit records, statuses and statistic. A crash
before commit may rerun the same address. A committed numerical failure remains
terminal and cannot become pending or be retried. A usable node contains exactly
references 0 through 998 once each and no invalid row. Missing work is pending;
it is not a cost-based abstention. One terminal invalid row makes the completed
node table unusable for each case that requires it.

## Independent audit implemented

`scripts/audit_capstone_training.py` is independent of the producer likelihood,
fitter, calibration module, training adapter and reference writer. It reuses the
qualified public auditor's direct empirical-bank reconstruction and the separate
analytic pre-only likelihood.

The audit performs the following checks.

- Reconstruct and hash-check the qualified public map, site design and complete
  arrival bank before scoring.
- Reject undocumented training arrays and bind the four neutral cases to the
  canonical 120 public training sites without fabricating held-out observations.
  Require the exact sealed training manifest and registered NPZ digest; reject a
  self-consistent substitute archive and rewritten manifest.
- Independently reconstruct all 3,060 observed pre-only likelihoods (four cases
  by 765 nuisance nodes), including the exact finite/nonfinite pattern, before
  accepting the observed screening surface.
- Directly score every stored main fit, every profile point and all 1,350 stored
  lattice points. Independently reconstruct both likelihood ratios, adjusted-pair
  validity and diagnostic gaps.
- For every screen node, validate all addresses and stored seeds, replay all 99
  pre-only histories, independently score the complete immediate-axis stencil,
  and reconstruct every contrast.
- For every completed effect row, verify SQLite integrity, metadata, row and
  payload hashes, exact table constraints, row-count and reference uniqueness,
  the known node-null truth, address streams, latent arrays, optimizer-status
  consistency, and direct truth/null/free scores. Independently reconstruct `T`,
  nesting predicates and the terminal-valid flag.
- Replay effect generators at references 0, 499 and 998 for every retained node,
  plus every anomalous row. Reduced mechanical tests use the corresponding first,
  middle and final indices.
- Independently reconstruct all four observed screen contrasts, `q` values,
  retained sets, their union, node ranks, Berger–Boos values, declarations and
  abstentions. When a stored chain is supplied, require its complete exact schema
  and compare every component, including invalid-shared-screen branches. Missing
  effect tables remain pending; present invalid tables cause scoped abstention.

Every effect statistic participates in the tail rank and one invalid row changes
the complete-table decision. Consequently the score, validity and rank chain is
audited exhaustively conditional on the stored histories. Deterministic effect-
generator replay remains the registered sample of references 0, 499 and 998 plus
every anomalous row. Screen generation is cheap enough to replay exhaustively.
This sample does not independently exclude an isolated, internally coherent
history substitution in an otherwise valid effect table; that provenance claim
also depends on frozen-source custody, per-row seed and hash checks, and the
producer's primary-key store.

Every helper returns the common audit fields `schema`, `kind`, `passed`,
`status`, `numerical_status`, `diagnostic_passed`, `release_blocked` and
`audit_binding`. A successfully verified terminal optimizer failure has
`passed=true` and `numerical_status=terminal_invalid`; pending work has
`passed=false`, `numerical_status=pending` and blocks release. Source, schema,
hash or direct-score disagreement raises `AuditStopError` and stops the stage.
Bindings cover the qualified public receipt, training/checkpoint inputs and
their exact hashes; the rank-chain binding covers every supplied numerical
array and stored decision record.

## Training lock

Before holdout release, the training lock should bind:

- analyst input and ciphertext commitments;
- public map, site, exposure, K=131,072 bank and random-address contract;
- frozen scientific source, runtime and the post-sealing orchestration/audit
  source;
- all four main fits, starts, parameters, likelihoods, statuses and explicit
  adjusted validity records;
- profiles, lattice results and diagnostic flags;
- observed pre-only surfaces, contrasts, `q` values, four retained sets and their
  union;
- the complete screen table and per-node effect-database manifests, row statuses
  and statistics;
- node ranks, Berger–Boos values, declarations and reasons;
- predictive specification, prerelease interpretation and independent audit;
- hashes or manifest roots for all bulk evidence.

The lock excludes held-out observations, sealed case truth, private keys and
generating-coordinate diagnostics. Likelihood-support profiles must remain
described as support regions rather than confidence intervals.

## Residual risks and recommendation

Weak information, boundaries, shallow or multimodal profiles and frozen-
optimizer failures may make an individual effect magnitude unstable even when
the calibrated declaration is valid. Shared reference tables create dependence
across the four cases, and spatially clustered sites preclude site-IID inference.
The finite grid leaves off-grid nuisance values and model misspecification
uncovered. The fixed empirical arrival bank is operationally qualified but is
not a proof of process-likelihood accuracy or tail-rank invariance under another
bank. Effect replay reuses the previously qualified spread kernel used by the
producer, so it confirms deterministic source-bound replay rather than providing
a fully independent spread implementation. The audit checks scores at every
stored parameter point but neither reproduces optimiser trajectories nor proves
global optimality.

Proceed with the registered analysis once the wrapper and mechanical audit pass
in the locked Linux runtime. Preserve negative and incomplete outcomes. Fable's
review of the complete training lock and claims materially increases confidence
in execution, leakage control and reporting discipline; it cannot enlarge the
registered inferential scope.
