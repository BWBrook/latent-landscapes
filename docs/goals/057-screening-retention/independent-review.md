# Goal 057 independent post-run review

**Decision: GO for the bounded descriptive screening result.** The production run,
screening tables, diagnostic fits, and synthesis are internally consistent with the
registered design. This is not evidence of calibrated coverage, power, or causal
identification, and it does not qualify the screening set for an inferential claim beyond
the fixed public panel.

## 1. Scientific target and scope

The target is computational feasibility and descriptive retention for a finite nuisance
grid under the pre-invasion observation model. For each of 16 fixed synthetic histories,
the estimand is the 3,645-vector of nodewise Monte Carlo screening probabilities

\[
q_j = \{1 + \#(D^*_{rj} \geq D_{\mathrm{obs},j} - \epsilon_j)\}/100,
\]

where each node has 99 registered reference histories and
\(\epsilon_j=10^{-10}+10^{-12}\max(1,|D_{\mathrm{obs},j}|)\). A node is retained when
\(q_j>0.01\). The prediction target is therefore retention for these exact histories and
this discrete reference design. The 792 nuisance fits at eight represented truth nodes
estimate finite-sample error distributions for \(\log(\hat\mu/\mu)\),
\(\hat\beta-\beta\), and \(\hat\sigma_p-\sigma_p\); they are diagnostics rather than a
population-level bias study.

The data-generating process has 160 spatial sites, with 120 training sites, seven
pre-invasion occasions at ten-day spacing, and two visits per occasion. Site loss times
arise from whole-map-normalized hazards. Detection probability has mean 0.65 and either
is fixed or is one persistent site-level Beta draw. The likelihood integrates loss time
and persistent detection heterogeneity. The local statistic compares the centre node
with its immediate axis neighbours. Screening uses the 99 reference statistics at each
node; the 1,820 four-case unions reuse the same 16 histories.

## 2. Independent evidence and model comparisons

The audit used the separate analytic pre-only likelihood and did not import production
screening, calibration, generator, likelihood, fitting, or synthesis helpers. It rebuilt
the grid, axis-neighbour map, local contrasts, conservative tie rule, candidate masks,
four-case unions, whole-map hazard normalization, PCG64 streams, and diagnostic summaries
from constants and raw arrays.

| Check | Independent result | Decision |
|---|---:|---|
| Public likelihood surface | 58,320 scores; maximum absolute difference \(2.61\times10^{-12}\) | pass at \(10^{-8}\) |
| Local contrasts | 58,320 contrasts; maximum absolute difference \(7.28\times10^{-12}\) | pass at \(10^{-8}\) |
| Inclusive q values and candidate masks | maximum q difference 0; 0 mask mismatches | exact pass |
| True-node retention | 16/16 retained; true q range 0.03--1.00 | descriptive result |
| Four-case unions | all 1,820 rows reconstructed; 0 mismatches | exact pass |
| Diagnostic reference contrasts | 792 contrasts; maximum absolute difference \(6.82\times10^{-13}\) | pass at \(10^{-8}\) |
| Diagnostic true and fitted scores | all 792; maximum score difference \(4.55\times10^{-13}\) | pass at \(10^{-8}\) |
| Direct RNG replays | 21 fixed node/reference addresses; maximum contrast difference \(9.09\times10^{-13}\) | pass at \(10^{-8}\) |
| Seed ledger | all 1,082,565 ordered addresses and fingerprints | exact pass |
| Synthesis summaries | all nodewise means, MCSEs, covariance matrices, pooled summaries | exact to \(10^{-12}\) |
| Effect-cost projections | all eight cells rebuilt with 999 references per node | exact pass |
| Post-run arithmetic \(\mu\) supplement | all eight nodes and balanced mean rebuilt from 792 rows | exact pass |
| Artifact bindings | panel, frozen scorer, run inputs, and 12 synthesis outputs | all hashes pass |

All 792 fits returned `converged`; all parameter triples were finite; no independent
failure occurred; and no fitted-minus-truth likelihood gap was below \(-10^{-6}\). The
synthesis fit-status and finite-row accounting matched the raw rows exactly.

The candidate sets remain broad: 420--990 of 3,645 nodes per history. Four-case unions
range from 577 to 1,901 nodes, with median 1,266. These widths establish that this
registered local-statistic screen is broad on the fixed panel. Alongside the observed
estimator variability they are consistent with limited nuisance localization, but they
do not distinguish weak information in the observations from low sensitivity of the
local statistic. The high-R retained points make statistic limitation a plausible
contributor. The widths should not be presented as a defect in the computation or as
calibrated confidence-set sizes.

Using the registered 999 later effect references per retained node, a 1.5 worker margin,
and the Goal 056 median/maximum wall-workload surrogates, the independently reconstructed
16-worker projections are 59.1--71.6 hours for the smallest observed union,
129.7--157.2 hours for the median union, 194.8--236.0 hours for the largest union, and
373.5--452.6 hours for the whole grid. These are ideal parallel projections from summed
wall workloads. They are neither measured CPU requirements nor Kunanyi speed estimates,
and Goal 057 does not choose a resource cap.

The equally weighted eight-node diagnostic means and stratified MCSEs were:

| Error | Mean | Stratified MCSE | Approximate 95% interval |
|---|---:|---:|---:|
| \(\log(\hat\mu/\mu)\) | -0.01594 | 0.01216 | [-0.03982, 0.00793] |
| \(\hat\beta-\beta\) | 0.00496 | 0.01731 | [-0.02901, 0.03894] |
| \(\hat\sigma_p-\sigma_p\) | 0.01009 | 0.00071 | [0.00868, 0.01149] |

After viewing the registered results, a supplementary arithmetic-scale summary was added
to address the distinct quantity \(\hat\mu/\mu-1\). Independent reconstruction from the
same 792 unchanged fits gives a balanced mean of +0.03952, MCSE 0.01178, and approximate
95% Monte Carlo interval [0.01639, 0.06265]. The eight node means range from -0.01534 to
+0.08215. This supplement is explicitly post-run and is not the registered primary
diagnostic. The registered mean log-ratio is -0.01594 with interval
[-0.03982, 0.00793]. These quantities differ because averaging ratios and averaging log
ratios are not interchangeable. The evidence does not support a blanket 20% inflation
claim, nor does it support zero bias at every node.

The last row is dominated by the non-negative boundary: when the true detection SD was
zero, 47--51 of 99 fits per node landed exactly at zero and the nodewise mean error was
+0.018 to +0.025. This is the expected direction under truncation. The MCSE of the mean
across 99 independent draws remains a useful pointwise Monte Carlo summary, and its
approximate t interval is reported as such; boundary-induced skew can still limit that
finite-sample approximation. The boundary chiefly rules out regular symmetric
parameter-level inference and a pooled common-bias interpretation. At true SD 0.2,
nodewise mean errors ranged from -0.00394 to +0.00151. The largest absolute estimated
error correlation was about 0.43, between log-hazard and beta error at one node; the sign
changed across nodes. This supports moderate, design-dependent parameter trade-offs and
does not support a single common confounding relationship.

## 3. Verification and failure-mode assessment

- **Localization and information:** broad candidate sets and large four-case unions show
  that the registered local-statistic screen is broad. Beta-error SDs of about 0.40--0.62
  and log-hazard-ratio SDs of about 0.28--0.38 show appreciable finite-sample estimator
  variability. These results do not apportion the broad screen between observation-level
  information and statistic sensitivity; convergence alone does not establish strong
  identification.
- **Boundary estimates and non-regularity:** detection SD at truth zero is a boundary
  problem. The pointwise Monte Carlo SE still quantifies simulation error in the sampled
  mean, while the positive pooled SD error is not evidence of ordinary unconstrained
  bias or a regular ecological-parameter interval. A boundary-aware recovery or coverage
  study would be needed for those claims.
- **Parameter trade-offs:** covariance matrices show moderate and node-dependent
  log-hazard/beta association. No severe universal aliasing was observed, but the eight
  nodes do not rule out stronger trade-offs elsewhere on the grid.
- **Pseudoreplication and multiple reuse:** the 1,820 unions are deterministic,
  overlapping summaries of 16 histories. They are not 1,820 independent replicates and
  cannot estimate coverage or Monte Carlo uncertainty.
- **Selection and preview:** some registered reference streams were publicly previewed
  before final source freeze. Specifically, all 99 unique node-0 references were
  generated during development, node-0 references 0 and 1 were generated again in early
  tests, and the first eight uniform variates of node 17/reference 23/loss stage were
  inspected. The final audit found unchanged addresses, methods, and source/input
  bindings, but the study cannot be described as wholly frozen before preview.
- **Spatial dependence and scale:** spatial covariates enter the hazard surface, while
  this bounded audit does not test residual spatial autocorrelation, non-stationarity, or
  transfer to other landscapes, site samples, calendars, or map resolutions.
- **Observation misspecification:** the verification assumes the registered exponential
  loss model, persistent Beta detection heterogeneity, fixed 0.65 detection mean, and
  error-free site covariates. Zero inflation, extra-binomial visit dependence,
  informative missingness, and alternative loss-time laws were not varied.
- **Screen discreteness:** with 99 references, q values have resolution 0.01 and the
  strict \(q>0.01\) rule excludes a node only when no reference exceeds the conservative
  threshold. This is the registered test, not a finely resolved tail estimate.
- **Global versus local diagnostics:** retained nodes can have descriptive
  \(R=2(\max\ell-\ell)>10\) because retention uses a local-neighbour statistic. R has no
  chi-square interpretation here.
- **Numerical and provenance risks:** no non-finite scores, optimizer failures, objective
  reversals, ledger discrepancies, serialization differences, or synthesis hash
  mismatches were found. The 21 direct replays are audit checks, not new references.

Five manual-array checks, Ruff, and strict mypy passed before the post-run audit. The
machine-readable result is
`artifacts/goal057_execution/independent-audit/result-v3/report.json` (SHA-256
`32891bca029707bf1bb0a35a8289a8b86e9ba6d722d7344777280e633b52202b`). It binds the
unchanged raw-audit report (SHA-256
`c1c819e33be8f65c650f94b145589b5af34d6fab7351a3da3413967e58f71c4c`) to the accepted
v3 synthesis without further RNG draws or likelihood evaluations. The verifier is
`artifacts/goal057_execution/independent-audit/verify_screening.py` (SHA-256
`5b70184ca6e5d2cae77623715053b45ab2def270e5faba4f44c97bd2ae971e6a`).

The original synthesis is preserved but is not accepted for cost reporting: its displayed
999-reference metadata was paired with arithmetic that used 99. A corrected v2 fixed that
factor; its audit receipt stopped only because the live synthesis script had already
advanced to the subsequent visual correction. The accepted v3 retains the corrected cost
arithmetic and fixes the surface rendering for non-uniform \(\mu\) spacing. All v3 input,
output, source-workload, and synthesis-script hashes passed.

## 4. Residual risk and recommendation

Proceed with Goal 057 as a qualified descriptive feasibility and screening-retention
result. Preserve the fixed-panel, overlapping-union, discrete-q, boundary, and preview
qualifications in any synthesis or manuscript language. Do not claim calibrated coverage,
power, estimator recovery, common bias, or causal identification from this run.

A further independent review is unlikely to change confidence in the computational GO,
because the likelihood surface, RNG addresses, raw diagnostics, derived summaries, and
hash bindings were independently reconstructed. Independent scientific review would
materially affect confidence before using these results to choose an inferential design
or make a manuscript claim about calibration, recovery, or generality; those questions
require a prospectively frozen multi-replicate study with boundary-aware diagnostics and
validation across alternative observation processes and landscape realizations.
