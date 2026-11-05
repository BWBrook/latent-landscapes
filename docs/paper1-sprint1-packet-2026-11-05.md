# Sprint 1 packet: a freezable spatial procedure and an executable experiment

5 November 2026. Claude (Opus 5.5) Sprint 1 under the
[two-sprint envelope](paper1-sprints-2026-11-05.md). It advances charter
pillars 3, 4 and 6 and supplies the protocol's single
implementation/qualification packet. Nothing here uses rule-training or
validation outcomes: no training history has been generated, and validation
maps exist only as a hashed seed commitment.

Evidence lives in [`evidence/paper1-sprint1-2026-11-05/`](evidence/paper1-sprint1-2026-11-05/).
Independent review status is recorded at the end of this document.

## 1. What the diagnosis found

The two searches that never resolved in the development challenge, and the
4.53-unit identical-parameter witness, have one root cause. It was not the
multimodality Claude predicted.

**The latent solver accepted points that were not maxima.** At the four
frozen outer vectors, 13 predeclared starts found one positive-definite latent
mode per vector ([`mode_diagnosis.py`](evidence/paper1-sprint1-2026-11-05/mode_diagnosis.py),
predeclared in commit `66daed4`; output in `mode-diagnosis.jsonl`).

On cell-00-rep-005-arm-B, the zero-start branch fell back to L-BFGS and hit
its iteration limit on a nearly flat ridge. The gradient there was 1e-8 but
the Newton decrement was 3e-6. The old rule accepted it on gradient size
alone. Near that ridge the Hessian is close to singular, so the Laplace term
inflated the criterion by about 4.5 units. That is the witness. In the
cell-06 vectors the latent posterior was unimodal and computed correctly; the
outer optimiser was what stalled.

**The Laplace criterion is unbounded near a reachable boundary.** Some site
log-likelihoods are locally convex in the latent log hazard, because they are
mixtures over unknown arrival times. Positive site curvature is common: 3 to
25 sites per dataset. As σ grows, H = Q − diag(ℓ″) approaches singularity
and −½ log|I − Cᵀdiag(ℓ″)C| grows without bound, although the integral it
approximates stays finite.

On cell-00 at h = 30, following the exact gradient raised the criterion from
−1125.06 to −1122.27 as σ approached 1.86, with gradients in the thousands.
At ordinary fits the smallest eigenvalue of I − Cᵀdiag(ℓ″)C stays between
0.89 and 0.999. So this is a high-σ, high-h pathology, but the profile search
must explore that region to certify sets and envelopes.

**Clipping the curvature is not the fix.** Replacing positive site curvature
by zero in the determinant makes the criterion bounded. Against the archived
importance integrals (95 precise points, 20 histories;
[`clipped-vs-importance.json`](evidence/paper1-sprint1-2026-11-05/clipped-vs-importance.json)) it
behaves as follows:

| Criterion minus importance integral | Mean | Mean absolute | Within-history W-scale range, median (max) |
|---|---:|---:|---:|
| Standard Laplace | +0.085 | 0.085 | 0.062 (0.148) |
| Clipped Laplace | −0.005 | 0.050 | 0.106 (0.737) |

Standard Laplace overstates the positive-variance family by a nearly constant
offset, which cancels in W. Clipping removes the offset but adds h-dependent
error, and h-dependent error is what moves interval endpoints. Standard
Laplace is retained.

## 2. The procedure (freeze candidate)

The score is a deterministic function of (h, α, β, σ, detection SD), the
training data, the arrival bank and the evaluator settings.

1. **Latent mode.** Damped (Levenberg–Marquardt) Newton from u = 0 only.
   It is accepted only with a positive-definite negative Hessian, gradient
   ≤ 1e-7 and Newton decrement ≤ 1e-7, or with a full Newton step whose
   predicted gain is below floating-point resolution. Anything else is an
   evaluation failure. Warm starts and branch selection are removed, so call
   order and caches cannot change a value. A test evaluates in a different
   order, on a fresh instance, and gets bitwise-equal criteria.
2. **Laplace criterion.** Σℓ − ½uᵀQu − ½ log|I − Cᵀdiag(ℓ″)C| at the mode.
   This is standard Laplace, selected by the joint objective, with no
   clipping.
3. **Eigenvalue floor.** The log-determinant uses floored eigenvalues of
   I − Cᵀdiag(ℓ″)C, f(x) = x + 0.1·e^(−x/0.1). These eigenvalues are always
   positive at a converged mode, because the matrix equals CᵀHC. f(0) = 0.1
   caps the inflation at ½ log 10 ≈ 1.15 per latent direction. At the
   eigenvalues seen at ordinary fits (≥ 0.89), f differs from x by less than
   1.4e-5. The exact floored gradient replaces H⁻¹ in the determinant terms
   with C·V·diag(f′/f)·Vᵀ·Cᵀ. It is tested against re-optimised differences
   where the floor is active.
   *This replaces a hard guard (fail below 0.1). Review showed that guard cut
   holes inside the domain, not only at high σ: the smallest eigenvalue is
   non-monotone in α at σ = 1.5. It also left 0.3–0.5-unit spikes beside the
   holes.*
4. **Residual SD bound.** σ ≤ 1.5, changed from 2. The largest generating
   residual SD in the design is √(log 2)·√0.51·√2 = 0.84, so 1.5 is 1.78
   times that. Contacts are reported, as before. At the cell-00 h = 30
   witness, the fit with σ ≤ 1.5 converges to a KKT point on the bound
   (projected gradient 8e-8, 51 evaluations, 1.7 s), with smallest eigenvalue
   0.27.
5. **Gradients.** α, β and log σ are analytic, as before. Detection SD and
   log h now use the implicit-function Laplace gradient with site-level
   central differences at fixed η. Tests match full re-optimised
   differences, including at the h = 30 endpoint.
6. **Outer optimiser.** Projected trust-region Newton on exact gradients,
   replacing L-BFGS, Powell and polish.
   - The Hessian comes from differences of the gradient. A failed column is
     retried backwards, then replaced by a diagonal curvature.
   - An eigenvalue shift lets it leave saddles.
   - A stationary point is accepted only after a second-order check, with up
     to three saddle escapes. A direction whose column fell back to diagonal
     curvature passes that check trivially; the projected-gradient test
     still applies to it.
   - Convergence requires projected gradient ≤ 0.1 × the eligibility
     tolerance.
   - Every profile point also gets a fixed high-σ anchor start (σ = 1.2).
     Review found that the default start never visited eligible fits on the
     σ = 1.5 bound at h = 30, which were 0.3–0.8 units higher.
7. **Envelope guard.** A positive-family fit fails its dataset as
   `search_unresolved` when any non-eligible candidate (iteration limit or
   failed evaluation) exceeds the best eligible one by more than 1e-4. The
   anchor start adds one candidate per point, and on a flat σ ridge it could
   stop at the iteration limit just above the best converged fit. Review
   found no case in about 380 fixed fits from the replays. Qualification
   reports guard failures by the source of the offending start as a
   separate line. If any are anchor-caused, Sprint 2 decides on a
   continuation rule before training.
8. **Contacts.** Codex's pointwise tie rule applies: where the positive and
   exact-zero families tie within 1e-4, the positive family's lower-σ contact
   is flagged as tied and excluded from contact summaries. Both branches, the
   tie flags and the raw envelope score are retained.
9. **Multimodality audit.** The 13-start family is rerun, where the reported
   σ > 1e-3, at both free fits and at every retained profile point and
   cutoff root whose envelope LR is at most 25 (the largest cutoff plus 10).
   A strictly converged mode with a higher joint objective (by > 1e-6, with
   |Δu| > 1e-3) fails the dataset as `multimodal_latent`. This is a frozen
   failure trigger, applied the same way in qualification, training and
   validation. Review swept the near-singular region of cell-00 using zero,
   forward and backward continuation starts and found identical modes
   throughout, so the near-singularity is a Laplace-term effect, not a mode
   fold.
   The trigger uses the joint objective, the quantity the mode solver
   maximises, not the Laplace score. A missed mode can have a higher joint
   value and a lower score, or the reverse, because the floored
   log-determinant differs between modes. So the trigger is conservative in
   one direction and blind in the other. Each audited location therefore
   also records the largest gain of the production score over any converged
   start (`max_criterion_gain`), which is descriptive.
   *The LR bound was added after the first entry-point run. There, all 22
   audited points sat on the σ = 1.5 bound at h = 20–30 with LR 36–47, and
   one start's per-site grid search spent about 53 s per point in the
   exact-likelihood path (log hazard above −3.75). A missed mode at LR > 25
   would need a score gain above 5 to change any level set, and above 12.5
   to change the free maximum. The margin of 10 is a judgement, not a
   derived bound: the 4.53 discrepancy seen before was the old solver's
   ridge artefact and does not bound true multimodal gains under the floored
   score. The h = 1 null fit is also skipped when LR₁ > 25, so a strong-signal
   dataset's declaration rests on the unaudited null; flipping it would need
   a gain above (LR₁ − cutoff)/2 ≥ 5. Qualification measures the margin
   (§4). Skipped locations and their LRs are recorded.*

**Replay check.** Lean searches of six challenge histories were rerun with
items 1–6 ([`replay-summary.json`](evidence/paper1-sprint1-2026-11-05/replay-summary.json)).
Both previously unresolved searches resolve, with free h = 1 and 3.84 upper
roots at 2.79 and 2.19. All four previously resolved histories reproduce
their free fits and 3.84 roots to four decimals. Search time fell from
383–4,711 s to 213–404 s, 9 to 13 times faster on the four previously
resolved histories. These old histories are diagnostics, not fresh
qualification.

**Entry point.** `scripts/fit_dataset.py` returns three families: spatial
envelope, exposure-linked (σ = 0) and constant (β = 0). Each has free and
h = 1 fits, LR₁, cutoff-indexed sets on the full grid, a multimodality audit,
a closed failure class and cost receipts. The exposure and constant profiles
come almost free, because they need no latent solve. That gives all three
families interval as well as declaration evidence. Status of this item is
recorded in §8.

## 3. The experiment

**Maps.** All maps are prepared and admissible, with the selector solver
status `selected_verified` for every one:
- 30 development maps, 10 per archetype;
- 9 qualification maps, 3 per archetype.

Seeds are `SeedSequence(2026110501, spawn_key=(role, archetype, map))`, with
roles development 1, qualification 2 and validation 3. The selector's 30-second wall-clock MILP limit made
admissibility depend on machine load: a rerun under load 26 timed out on
maps that had succeeded. A HiGHS time-limit is therefore an *execution*
failure, to be rerun at lower concurrency, not a geometry failure. All maps
reproduce byte-identically. The 60 validation
spawn keys (20 per archetype) are committed by SHA-256
`769daf17…cf47` and not generated. The manifests are in
`evidence/…/maps/`. Failures would have been retained, not replaced; there
were none.

**Backgrounds.** z = 0.7A + √0.51 (s·a·T + κG). Site hazard is
λ = μ·exp(√(log 2)·z) divided by its map mean. G has range 10.

| Name | s | κ | Role |
|---|---:|---:|---|
| constant | – | – | λ = μ |
| matched_exposure | 0 | 0 | dose-zero anchor |
| b100_anchor | 0 | 1 | reference |
| increased_heterogeneity | 0 | √2 | double residual variance |
| window_low | −1 | 1 | signed alignment |
| window_high | +1 | 1 | signed alignment |
| temporal_trend | b100_anchor × exp(γt) | | γ = ln 1.5 / 120: 1.5-fold over the 120-day window |

**Design correction.** The protocol's earlier/later alignment uses T =
planning arrival orthogonalised against [1, A]. But A *is* the rank-normal
score of planning arrival: the Spearman correlation is 1.0000 on every
archetype. So that T is numerical noise. Any planning-only timing surface is
a function of A. Its linear part is absorbed by the fitted β·A, and only a
nonlinear remainder can bias a model that includes A.

The replacement is a **reach-threshold alignment**:
- W = 1{planning arrival ≤ 60}, the sites the predator is expected to reach
  by the end of monitoring, release cells included.
- T is W's residual on [1, A], centred and unit-scaled over the 300-site
  sampling frame, so it is orthogonal to A where models are fitted.
- W is a threshold in A, so T is the step that the log-linear exposure term
  cannot express, concentrated at the edge of invasion reach. It is a
  targeted confounding stress for h, not independent timing information.
- window_high raises the background on the reached side of that threshold
  (relative to the linear trend); window_low lowers it.
- With a = 1, each signed arm has frame variance 0.49 + 0.51·2 = 1.51 in its
  residual components, matching increased_heterogeneity.
- W prevalence over the frame is 0.28–0.67, corr(W, A) is 0.76–0.84, and T
  lies in [−2.7, 2.1] on every map.

The first version used 1{0 < arrival ≤ 60}. Review found that the 81
release cells then dominated T (T ≈ −4, 18–26% of its variance), so it was
corrected before any history was generated. The reviewer advised keeping the
arms as the most targeted confounding test in the design.

**Process and observation.** These are unchanged from the protocol:
- μ ∈ {0.001, 0.004} per day;
- h ∈ {1, 2, 3, 4, 5, 10};
- persistent Beta prey detection, mean 0.65 and SD 0.2; predator detection
  0.65;
- arms A (pre/post, 120 sites), B (A with prey observations at day ≤ 0
  masked) and C (260 sites, post-release only, with predator observations
  missing at the 140 added sites);
- the full cohort is simulated from day −60.

The six stationary backgrounds and the trend are paired on each biological
history address: spread, thresholds, detection, visits and G come from
streams keyed by the address only.

**Cutoff grids.** C_D = C_I = {2.71, 3.84, 5.02, 6.63, 7.88, 9.55, 12, 15},
the χ²₁ 90–99.8% quantiles extended to 12 and 15. R1 is the fixed benchmark
LR₁ > 2.71. R2 and the interval cutoff take the smallest grid value whose
development one-sided 95% upper bounds satisfy the protocol targets in every
claimed stratum. The tie rule is the smallest eligible value. If none
qualifies, that is reported as the result.

**Family scope.** Declaration (R1/R2) and interval calibration are trained
for all three families, because the entry point supplies their profiles.
Choosing the best family on a holdout yields no calibrated inference, as the
protocol states.

**Training allocation.**
- Address namespace 4.
- 200 histories per map × background × μ cell at h ∈ {1, 3}, and 100 at
  h ∈ {2, 4, 5, 10}.
- Each history is analysed in arms A, B and C.
- That is 30 × 6 × 2 × 800 = 288,000 histories and 864,000 datasets.
- At h = 1 each stratum (archetype × background × μ × arm) holds 10 maps ×
  200 = 2,000 null histories. The binomial SE at 0.05 is about 0.005 before
  between-map variation, which is enough to separate rates near 0.04 from
  the 0.05 target.
- An h ∈ {1, 3} batch may run first for pipeline and cost checks. It is not
  the six-truth evidence.
- The temporal trend is a robustness test and is not trained on.
- Validation counts come from the frozen precision rule once τ² and v are
  estimated in training.

**Cross-validation.** Whole development maps are held out per fold: 10
folds, one map per archetype per fold. Cutoff selection and forecast fitting
are repeated inside each fold.

**Forecast inputs.** These are planning-only, per map × design cell:
- expected pre-period events under the matched-exposure surface at the
  design μ;
- expected post-arrival site-days in the window, from planning arrival;
- the SD of planning arrival over training sites;
- mean access distance.

The comparators are a total-events-only forecast and an archetype-only
forecast. Realised hazards, losses and arrivals are mechanism diagnostics
only.

**Bootstrap audit.** The matched bootstrap comparison stays as specified.
After the cluster pilot, measure the seconds per constrained-plus-unconstrained
spatial pair. Project the audit's CPU-hours under the documented early
stopping.
- If the projection is no more than twice the training campaign's
  CPU-hours, run it unchanged.
- Otherwise propose a reduced design: fewer audited datasets per cell, the
  same maps and the same statistic. That proposal goes to independent review
  before any main outcome exists.

**Denominators.** Every registered dataset counts:
- a failed fit is a non-declaration for declaration rates and noncoverage
  for interval rates;
- execution losses (scheduler or host, and `execution_error`: memory or
  operating-system exceptions in the entry point) are rerun, because they are not
  scientific outcomes;
- scientific failure classes are never rerun.

## 4. Fresh qualification panel (frozen here)

[`qualification-panel.json`](evidence/paper1-sprint1-2026-11-05/qualification-panel.json)
is produced deterministically by `qualification_manifest.py`, uses address
namespace 5 and covers the 9 qualification maps.

| Stratum | Composition | Datasets | Role |
|---|---|---:|---|
| base | each map × μ × h ∈ {1, 3, 10}, background by Latin rotation (each stationary background 9×), arms A/B/C | 162 | **gate** |
| boundary | each map, b100_anchor, μ = 0.004, h = 25, arms A/C | 18 | separate, descriptive |
| enriched | each map, increased_heterogeneity and window_high, μ = 0.001, h = 1, arm B | 18 | separate; failures trigger diagnosis |
| trend | each map, temporal_trend, μ = 0.004, h = 3, arm A | 9 | descriptive |

Every dataset runs the entry point with both dense and lean searches.

**Dataset failure.** A base dataset fails on any of:
- a non-`resolved` class in either search;
- dense and lean disagreeing: more than 0.01 in W at shared nodes, more
  than 0.005 in log h at any root at any cutoff, a different number of set
  components at any cutoff whose tangency margin exceeds 0.01, or different
  contacts after the tie rule;
- for the 18 seeded histories (54 datasets) given an independent bank: more
  than 0.10 in W, more than 0.05 in log h at a root, or a different topology
  where the margin exceeds 0.10;
- at the spatial free fit, analytic and central-difference gradients
  differing by more than 1e-4 relative (1e-5 absolute).

Near-tangent topology differences are recorded, not failed.

**Audit margin.** Two base datasets per map (18, seeded and flagged
`exhaustive_audit` in the manifest) also run with `--exhaustive-audit`, which
audits every location regardless of LR. The receipt gives the largest joint
and score gains at locations the production rule would skip. A converged
distinct mode with a score gain above 5 at a skipped location means the
margin is too small. Training does not start until the margin is widened
and reviewed. This set was added on 5 November, after review and before
any qualification outcome.

**Gate.** The unit is a base dataset, clustered by map: 9 maps of 18
datasets each.
- Let p_m be each map's failure proportion.
- Pass requires mean(p_m) + t₀.₉₅,₈·sd(p_m)/3 ≤ 0.05, and no map with
  p_m > 0.25.
- Arms of one history are correlated, so the map is the replication unit.

**The one permitted continuation.** If every base failure is in arm C and
the gate passes on arms A and B alone, the procedure qualifies for A and B.
Arm C then needs a reviewed repair before training. Any other failure follows
the envelope's repair branch: diagnose, record the deviation, review one
repair, then test on a new frozen panel.

**Integration characterisation.** One seeded base dataset per map gets fixed-outer importance
integration at the free fit and the 3.84 roots. It is capped at 262,144
draws and is descriptive only: indeterminate results stay in the
denominator.

## 5. Cost

Search time per lean profile on the Mac mini, single-threaded, for 120 sites
with the old tight replay included: 213–404 s with the repaired procedure.
The 260-site and cutoff-grid costs, and the production cost without the
tight replay, come from the entry-point runs in §8.

Training projection at an illustrative 6 minutes mean per dataset:
864,000 × 0.1 h = 86,400 CPU-hours, which is 3.6 days on 1,000 cores or
1.8 days on 2,000. The measured cluster pilot replaces this figure.

## 6. Cluster execution

- `scripts/pbs/campaign.py` packs independent tasks into PBS array subjobs,
  with one numerical thread per task and receipts per attempt.
- Resume skips completed tasks.
- Failures are kept and rerun only with `--retry-failed`, which also keeps
  the earlier receipt.
- `reconcile` separates completed, failed and missing tasks from scheduler
  state.
- `scripts/pbs/prepare_runtime.pbs` pulls a uv/Python 3.12 Apptainer image
  and runs `uv sync --frozen` at a pinned commit on a compute node. Lmod is
  initialised in batch, as the runbook requires, because the site Anaconda's
  NumPy 1.26 is below the project's floor.
- `scripts/pbs/array.pbs` is the array template.
- The driver passed a local resume-and-failure test.

Not yet done: an authenticated cluster session. That needs Barry's portal
window and password. Queue, quota and the compute-node pilot follow it.

## 7. Manuscript scaffold

See [`paper1-manuscript-scaffold.md`](paper1-manuscript-scaffold.md): the
editor pitch, six figures with captions written for alternative outcomes,
the claims-ledger skeleton, the two-page brief outline and the agent-guide
outline.

## 8. Status and review

This section is updated at the handover to Codex.
