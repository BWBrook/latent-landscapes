# Goal 055 independent implementation and protocol review

1 October 2026 (Hobart). Charter Pillar 4 and capstone-design preparation.

## Decision

**GO for the registered remote timing phase.** The repaired implementation now
matches the registered archive experiment, preserves the two independent
replicate panels, and places the consequential controls before production. The
timing result must still be verified and converted into a source-bound
production budget; this review does not authorize or claim completion of
production scoring.

The scientific target remains the operating behaviour of the frozen Goal 054
effect-declaration workflow under two supplied-background errors and one
site-detection departure. The complete 160-site history is the independent
unit. Goal 054 contrasts are paired by replicate across the correct, 0.8-times
and 1.25-times analysis lanes; Goal 051 B--D20 contrasts are paired within that
separate archive. The outputs estimate declaration probabilities, point-error
summaries and held-out score differences under those named finite settings.
They do not estimate the unknown nuisance parameters, establish robustness
between the tested settings, or validate an external background estimate.

## Implementation evidence and model comparison

The scorer constructs 162 separately identified integrations for the two new
mean hazards over all 81 beta nodes. Each identity binds the supplied mean,
beta, effect and beta grids, bank checksum, map and site covariates, and the
complete source/input core. Timing constructs and hashes every NPZ and receipt;
production disables construction and requires the identical 324-file cache
manifest. The 81 predecessor integrations and receipts are independently bound
to the pinned Goal 054 run contract. This prevents substitution among .0016,
.002 and .0025 analyses and prevents a missing timing cache from being silently
rebuilt during production.

The 12 new columns and four reused correct-level columns implement the intended
comparisons. The reducer visits beta in increasing order, uses first h ties,
updates beta maxima only on strict improvement, and requires the predator
marginal to remain exactly invariant across beta and supplied mean. The
constant model is the beta-zero row of the same likelihood surface. Synthesis
validates the exact supplied-mean vector and archive identities, including
identity of the two wrong-mean Goal 054 lanes, uniqueness within each archive,
and separation between archives. Reference, Goal 054 and Goal 051 bootstrap
indices use three independent streams while sharing indices within each
archive. Both frozen-table and calibration-aware intervals are saved for the
registered paired declaration contrasts and for adjusted-minus-constant rule
contrasts.

The strongest legacy-recovery control is now exhaustive at production scale.
All 4,000 selected Goal 051 histories are regenerated from the frozen 1,000
block seeds, and every opaque ID, 181-node training profile, 181-node held-out
profile, scalar prey score, scalar predator score and fitted index must exactly
equal the archive. A separate h=1 calculation factors held-out joint
probability into predator and exponential-prey marginals and must agree within
the numerical tolerance. The beta-zero adjusted integration is independently
compared with the original constant route at `1e-10`; this is the only
cross-route tolerance rather than an archive-replay tolerance.

The timing control also re-scores an outcome-independent eight-block panel of
the four selected Goal 054 correct-level cells over the complete 81-by-181
rectangle and reconstructs all saved reductions. Direct hazard checks at beta
-2, 0 and 2 and both new means compare against an independent stabilized
formula, verify whole-map normalization, and require beta-zero site hazards to
equal the supplied mean. The frozen Goal 054 rule implementation is checked
against direct plus-one tail counts, and the synthesis retains the registered
primary, constant, Berger--Boos and secondary rules without recalibration.

## Timing and verification

The repaired timing pipeline separates integration construction from the
scoring-only worker phase. It records exclusive wall times for setup, Goal 051
reconstruction and replay, Goal 054 control replay, panel serialization,
integration preparation, scoring plus row serialization, reduction, statistics
serialization and final hashing. The projection scales only the
history-dependent stages from 8 to 1,000 blocks, retains the complete measured
integration/control work as a conservative fixed allowance, applies a 1.5
operational margin and adds a one-hour synthesis/review reserve. Aggregate
worker seconds remain diagnostic and are not substituted for wall time.

This projection is deliberately conservative: cache reads and final hashing
inside the eight-block timing stages contain fixed costs that are also scaled.
That can enlarge the timeout but cannot understate the registered workload.
The measured stage table should therefore be inspected before accepting a
resource envelope; an implausibly dominant scaled I/O term would justify a
second scoring-only timing panel, not a change to replication or outcomes.

The independent local verification for this review was:

- 58 focused and regression tests covering the new campaign and synthesis,
  frozen null-effect rules, adjusted likelihood and original adequacy scorer;
- Ruff clean on the campaign, synthesis, CLIs, tests and remote control;
- mypy clean on the four campaign/synthesis source and CLI files; and
- source inspection of remote locking, one-attempt receipts, predecessor and
  new-cache manifests, read-only production reuse and synthesis output hashes.

No histories were generated, no remote phase was launched and no Goal 055
scientific outcome was inspected in this review.

## Capstone-protocol review

The amended capstone is scientifically defensible as one blinded diagnostic
case study. It cannot demonstrate general discrimination, calibration,
coverage or landscape transfer, and the protocol now states that limit. A
multi-case blinded null/effect pair with randomized labels would be the serious
alternative if the target later changes from case-study transfer to empirical
discrimination; the evidence needed to choose that alternative is the
feasibility study's recovery, exact-null size, weak-event performance and
measured cost.

The observation and blinding design now resolves the material ambiguities
found in review. The 40 holdout sites are prospectively reserved in eight
spatially dependent clusters, so inference uses aggregate scores and treats
cluster contributions descriptively rather than as 40 independent
replicates. The day-0 prey survey precedes predator introduction, both visits
condition on one latent state and site probability, and all planned visits are
complete. The likelihood carries the day-60 cohort continuously through day 0
and estimates background mean and spatial coefficient rather than an
unregistered temporal trend.

The finite truth draw is independent and uniform over the disclosed h, mean,
beta, residual-field and detection-dispersion sets, with separate public-map,
truth, spread, residual, loss, site-detection and visit streams. A null or weak
history is an accepted outcome. Fable remains outside Astra's accessible
workspace, commits the draw mechanism and environment before generation,
releases holdout observations only after code/input/model/predictive hashes are
locked, and releases truth only after the complete analysis-report hash. No
training refit or candidate-set change follows holdout release.

The main capstone limitation is weak information and parameter trade-off, not
blinding mechanics. Background mean, beta, h, residual spatial structure and
detection dispersion can be aliased through interval-censored prey loss;
heterogeneous detection includes a boundary at zero, and pre-invasion loss can
remove sites before they inform h. Thirteen prey occasions and repeated visits
may help but do not establish identifiability. Before any truth draw, the
prerequisite must freeze bounds/grids, mixing integration and priors; recover
parameters on synthetic fixtures; examine profiles, boundaries and
multimodality; test exact-null size across the finite nuisance domain and
weak-event cases; assess calibration-table uncertainty; and qualify prediction
under the same clustered holdout design. Exact-family calibration and B100-A
residual-field robustness must remain distinct claims.

## Residual risks and recommendation

The Goal 055 checks remain retrospective, one-landscape, fixed-bank,
finite-grid sensitivity analyses. D20 was selected after the earlier screen;
its result cannot independently confirm the nomination. A low wrong-mean rate
at two points cannot establish robustness to an estimated, continuous or
data-dependent background error. Flat h--beta surfaces, boundary fits and
multiple descriptive rules remain evidence of weak information rather than
successful identification. Bootstrap intervals quantify archive and frozen
reference-table resampling under the registered coupling; they are not new
coverage guarantees under misspecification.

Proceed with one source-bound eight-block timing launch, verify its receipts,
controls, cache manifests and stage table, then set a reviewable production
timeout from the conservative projection. Stop and diagnose any exact Goal 051
replay failure, correct-level mismatch, cache/hash discrepancy or implausible
timing decomposition. A surprising scientific rate is a result and does not
license redraw or retuning. Independent post-result reconstruction and claim
review will materially change confidence and should remain a completion gate.
The capstone protocol is **GO for refinement and the named feasibility study,
but NO-GO for truth draw or sealed launch** until that study and a separate
calibration have passed their preregistered criteria.

## Supplementary review after failed timing attempt, 2 October 2026

The 1 October GO above is retained as the historical pre-execution decision,
but it did not predict a successful timing run. The first timing attempt
exited with status 1 after 4 minutes 32 seconds while converting reconstructed
Goal 051 histories: the wrapper requested `AnalystHistory.predator_counts`, a
field that does not exist. The attempt stopped before any new-mean integration
construction or scoring. Its source, manifest, contract, log and receipts are
preserved under `artifacts/goal055_execution/failed-timing-20261001/`. This was
an execution/API failure and supplied no scientific outcome, but it is material
negative evidence about the sufficiency of the original implementation review
and tests.

The repaired source differs from that preserved snapshot in exactly three
campaign behaviours:

1. reconstructed histories now copy the frozen
   `predator_detection_counts` and `prey_detection_counts` fields;
2. `_cell_blocks` indexes history-level arrays by replicate while copying the
   independent 160-site metadata arrays without applying history indices; and
3. legacy Goal 053 cache identities now use Goal 053's original default-JSON
   fingerprint encoding rather than Goal 055's compact-JSON encoding.

These are interface, axis and provenance repairs. They do not change the
selected histories, observations represented by those histories, likelihood,
parameter grids, supplied means, archive pairing, reducer, reference table,
bootstrap, declaration rules, estimands or claims. The site-axis repair would
have caused the 1,000-block production panel to index beyond 160-site metadata;
the legacy fingerprint mismatch would have rejected authentic frozen caches.
Fixing them before a second timing attempt therefore prevents later mechanical
failures without changing an observed result.

The added regression tests exercise a generated Goal 051 history roundtrip,
the full 1,000-block history/site-axis distinction and the authentic Goal 053
receipt encoding. The source-manifest comparison shows that only the new Goal
055 campaign and its tests changed; the two helper hash changes only redirect
the wrapper to the separate v2 execution root. All 89 frozen predecessor
source identities remain unchanged. The v2 manifest is
`df80a971211e786eb7de811561ead5937abb0fa4b14e15bc72fedf6a81324ad5`.

Qualification under that manifest passed 24 selected tests on both the local
and target Linux environments, plus Ruff and mypy. This supplementary review
independently reran the nine Goal 055 campaign tests successfully. The remote
cache smoke loaded and authenticated all 81 Goal 053 integrations in 7.21
seconds against frozen contract SHA256
`6a7d3ea33b94f0fd5db9ad28938d3a1d682a163236a67cef11ca55d9864606f9`.
The v2 preflight binds 97 files and records no prior attempt in the separate
root.

**GO for one v2 timing attempt is restored.** Confidence is narrower than the
original review implied: unit and API tests now cover the three known failure
modes, and authentic cache loading reaches beyond mocks, but only the bounded
timing run exercises the complete reconstruction, correct-level replay,
integration construction, scoring, serialization and reduction path together.
Any further interface or provenance failure must again be preserved and
diagnosed; it must not be converted into a scientific result or bypassed by
weakening controls. The scientific and capstone recommendations above are
unchanged.
