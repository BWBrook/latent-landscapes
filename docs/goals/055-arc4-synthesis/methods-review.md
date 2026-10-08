# Goal 055 independent pre-scoring methods review

1 October 2026 (Hobart). Charter Pillar 4 and capstone-design preparation.

## Decision

**REPAIR, then GO for timing and archive scoring.** The two checks are bounded,
scientifically useful stress tests of the frozen Goal 054 decision procedure.
They do not recalibrate that procedure, estimate either nuisance, or validate a
random external background estimate. No new histories are needed. The
registration has the correct workload: 8,000 wrong-level Goal 054 fits, 2,000
Goal 051 D20 fits and 2,000 matched Goal 051 baseline fits, with four Goal 054
correct-level columns reused.

Before timing, freeze four points in implementation or the capstone protocol:

1. authenticate Goal 051 reconstruction by opaque ID and exact complete
   constant-model training and held-out profile replay for every reused B/D20
   history, and describe this as generator-and-profile authenticated recovery;
2. define the detection-heterogeneity capstone trigger as an exact predicate,
   rather than the current phrase “resolved false-declaration excess”;
3. keep any external-information branch conditional on an explicit external
   measurement model and nuisance-aware calibration; and
4. if the capstone uses a `1/E_pre + 1/E_post` precision expression, label it
   only as an ideal complete-data information benchmark and define whether E is
   an event count, expected count or exposure. It is not a field-data precision
   bound for this observation model.

These are design repairs, not reasons to change the registered histories,
grids, reference table, replication or bootstrap draws.

## Scientific target, estimands and pairing

The target is the operating behaviour of one already frozen effect-declaration
procedure when a supplied nuisance is wrong or when prey detection varies by
site. At physical `h=1`, the estimand is the marginal probability of declaring
an effect over complete generated histories under each named departure. At
physical `h=3`, it is the setting-specific declaration probability, best called
an “h3 declaration rate under departure” rather than unqualified power. Point
error and held-out score are separate estimands. None measures recovery of the
background mean or detection field.

The independent unit is a complete 160-site history. Sites, six occasions and
two visits are dependent components of that history. Goal 054 indices pair the
four cells across correct, 0.8-times and 1.25-times supplied means because the
observations are identical and only the analysis changes. Goal 051 indices pair
B with D20 because their generator shares spread, prey-event and visit-uniform
streams within a block while changing the registered site detection field.
Those common-random-number contrasts estimate the effect of the named
generator change under that coupling. The two archives are independent panels
and must never be paired with each other.

The three bootstrap resamples respect this structure. One reference index
vector is shared across all 81 nodes and every rule; one Goal 054 vector is
shared across its 12 columns; and a separate Goal 051 vector is shared across
its four columns. Frozen-table intervals omit reference resampling.
Calibration-aware intervals resample the same original assumed-model reference
table and are sensitivity summaries for table randomness, not newly calibrated
coverage under either departure.

## Evidence and exact legacy reconstruction

The Goal 054 archive contains the full evaluation observations and identities,
the 999-by-81 adjusted reference statistics, beta0 constant statistics,
999-by-81 null-beta discrepancies, and the eight-cell evaluation reductions.
The likelihood API already accepts an explicit positive `mean_hazard`, so each
new integration can use the unchanged A map and bank while binding its cache
identity to `(mean_hazard, beta, effects, bank checksum, site order)`. At beta
zero the adjusted row and constant comparator must use the same integration and
score profile. Both fitted models must receive the same supplied mean.

The Goal 051 packed archive is different. It retains `profiles` and
`holdout_joint` arrays of shape 17 by 1,000 by 181, fitted indices, prey and
predator score components, diagnostics and opaque IDs, but no raw predator or
prey counts. The selected cells occupy the frozen ordinals B_h1=0, B_h3=1,
D20_h1=6 and D20_h3=7. Production root 2026092301 and the seven-stream spawning
scheme deterministically reconstruct all 17 cells in each block; opaque IDs are
the frozen hash of goal, root, phase, block and ordinal. The currently inspected
Goal 051 generator and campaign match their archived production-contract
SHA256 identities.

Accordingly, replay the original full 17-cell generator for each frozen seed,
extract those four ordinals, and require every opaque ID plus every 181-node
training and held-out constant-model score to match the archive under the
original tie rule. Also match saved fitted indices and prey/predator score
components. Save the reconstructed numeric observation arrays and hashes in the
Goal 055 output before adjusted scoring. This is exact archive recovery, not a
new stochastic replicate. Because Goal 051 stored no observation-count hashes,
the final provenance statement must not claim an independent byte comparison
to archived raw observations: identity rests on the hash-pinned generator,
frozen seeds and exhaustive derived-profile replay.

Qualification should additionally require: all predecessor and bank hashes;
site order and 120/40 split identity; exact beta/effect grids; correct-level
Goal 054 score reconstruction on an outcome-independent selected panel; beta0
recovery of the old constant profile; `h=1` nesting; finite scores; deterministic
ties; direct site-hazard checks at both new means and representative beta
values; decision equivalence from saved Goal 054 statistics; and an independent
evaluation-only reducer. Cache identities must prevent a .0016, .002 or .0025
integration from being substituted for another. The timing projection must
include reconstruction, the complete constant-profile authentication,
integration construction, all scoring, serialization and synthesis.

## Interpretation and capstone branch criteria

The frozen reference table has its finite-grid exchangeability argument only
under the registered exact model. Reusing it is nevertheless the right test of
the procedure an analyst would actually carry forward. An excess physical-null
declaration rate under wrong mean or heterogeneous detection is therefore a
robustness failure of that frozen workflow, not a failed Monte Carlo proof and
not evidence for a replacement cutoff. Conversely, a low rate at two supplied
means does not establish validity for intermediate values, more extreme error,
another landscape, or an estimated external mean whose error is random and may
depend on the capstone data.

The wrong-level branch rule is appropriately asymmetric: an interval wholly
above 5% identifies clear failure, while recommending the external-information
candidate requires every wrong-level h1 upper limit to be at most 5%. Even in
that favourable case, the capstone protocol must specify the source population,
measurement scale, independence or data sharing, bias model, uncertainty
distribution and how that uncertainty enters calibration. The result supports
considering that bounded branch; it does not license fixing the analyst's mean
at a noisy point estimate and calling the effect rule calibrated. Intermediate
outcomes remain inconclusive and should not be converted into evidence of
robustness.

For detection heterogeneity, register two distinct quantities before scoring:
the absolute D20_h1 primary declaration rate relative to 5%, and the paired
D20_h1-minus-B_h1 change. A “resolved excess” should mean that the
calibration-aware 95% interval for the paired change has lower limit above
zero. State separately whether the absolute D20 interval is wholly above 5%.
The capstone prerequisite must specify which of these predicates, or their
prespecified union, activates observation-model or survey repair. This prevents
the decision from being chosen after seeing a small but precise contrast or a
high rate shared with baseline.

Any proposed `1/E_pre + 1/E_post` expression needs the same discipline. For
fully observed independent Poisson or exponential events, the local variance
of a log rate ratio is approximately `1/D_pre + 1/D_post`, or in expectation
`1/(lambda_pre*T_pre) + 1/(lambda_post*T_post)`. Exposure time alone is not an
event count. Latent invasion times, imperfect and heterogeneous detection,
interval-censored prey loss, spatial dependence, nuisance estimation and
selection of sampled sites all reduce or redistribute observed-data
information. Thus the expression can be an optimistic design-screening
benchmark. Capstone precision must ultimately be assessed from the actual
observed-data likelihood and blinded recovery/calibration diagnostics, not
presented as a field-data bound.

## Residual risks and recommendation

The two supplied means are sparse, deliberately chosen stress points on one
fixed landscape. D20 was selected after Goal 051 showed harm, so its new-rule
result is retrospective sensitivity evidence and cannot confirm the original
nomination or estimate general detection misspecification risk. The full grid
avoids optimiser and MCMC failures, but h--beta trade-offs, beta/h boundary
contacts and flat surfaces still represent weak information rather than
identification. Fixed-bank, finite-grid, one-landscape, known spread/resistance
and fixed detection-in-the-fit limits remain. Multiple reported rules and
metrics are descriptive; only the prespecified primary branch predicates may
drive the capstone recommendation.

After the four repairs and successful source-bound qualification, proceed with
the measured timing panel and then the authorized archive scoring. No
simulation, production scoring or capstone launch was performed in this review.
Independent post-result reconstruction and claim review will materially affect
confidence in the Arc 4 synthesis and should remain a completion condition.
