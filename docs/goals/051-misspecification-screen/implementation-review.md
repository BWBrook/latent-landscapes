# Goal 051 independent implementation review

23 September 2026 (Hobart). **GO for the registered source-bound timing run.**
Production remains conditional on an unchanged-source 16-block timing run, the
complete four-hour budget projection, the bound production receipt and all
remote qualification controls. No Goal 051 production history or endpoint has
been generated or examined.

## Scientific construction

The reviewed generator implements the approved 17 cells in their registered
order. One complete replicate shares predator spread, prey-event thresholds
and visit uniforms across cells. Prey- and predator-detection fields have
separate streams, are fixed by site over visits, and are shared across physical
truths. The `B100-A` field is identical at `h=1` and `h=3`; only the registered
post-arrival multiplier changes. Baseline cells replay the original generator
bitwise, including its `0.0020000000000000005` risk-to-hazard representation.

The exposure score uses resistance shortest paths from all source cells on the
frozen rook graph, average ranks over all 6,048 cells, the registered normal
score transform, and a single tied lowest score for unreachable cells. The
Gaussian field uses the registered 142 by 166 exact circulant embedding. Its
positive eigenvalues and covariance reconstruction are checked without
clipping; realised fields are not centred or standardized. Background hazards
are scaled once to mean 0.002 over the full map, leaving sampled means, CVs and
correlations unconstrained. The field, latent arrivals, true detection
probabilities and all diagnostics remain evaluator-only and do not enter the
unchanged analyst likelihood.

The campaign uses seven disjoint full-width streams per replicate and checks
all production, timing and fixture stream values against each other, the Goal
049/050 streams and the archived bank. Opaque identifiers are unique and reveal
neither cell nor truth. Frozen Goal 049 cutoffs, Goal 050 C99 cutoffs and the
181 by 999 refitted conditional-score table are hash-pinned through the Goal
050 production and synthesis provenance chain.

## Estimation and decision checks

Training profiles use the lowest-index maximum. The primary score is the
held-out joint log score minus the held-out predator marginal at that fitted
node. The separately reported predator diagnostic is the training predator
score. A direct calculation from real 17-cell fixture histories verifies both
denominators and the fixed fitted detection probability.

Candidate p-values use inclusive lower-tail ties. The Berger--Boos rule remains
primary; the fitted-node plug-in rule is secondary, has no selected-node
finite-sample guarantee, cannot nominate a departure and is not combined into
an omnibus test. The implementation enforces that every primary rejection is
also a plug-in rejection.

`M`, primary and secondary hidden failure, caught failures, strict false
effects, signed bias, set geometry and detector diagnostics match the
registration. Exactly 1,000 bootstrap draws resample complete replicate indices
jointly across all 17 cells while holding reference tables fixed. Nomination is
global: at most one cell qualifies from primary delta `H >= 0.05` with a paired
lower limit above zero, with ties resolved by frozen cell order. `M` never
drives nomination.

P1--P4 are operationalized component by component. Strict and inclusive
inequalities retain their registered boundaries. P4's truth-exclusion claim is
evaluated once as the bootstrap maximum across its three truths; per-truth
contrasts remain descriptive. The synthesis states that its intervals are not
simultaneous or multiplicity-controlled and preserves failed and unresolved
predictions.

## Audit repairs and runtime boundary

This review identified three pre-timing defects, all repaired and regression
tested before any scientific run:

1. the runtime wrappers and budget preparer were recorded in the budget receipt
   but were not enforced by production validation;
2. a shortened production timeout and a false `within_4h` flag could pass an
   otherwise arithmetically consistent receipt; and
3. inclusive `>=` and `<=` prediction boundaries were classified as strict,
   while P4 additionally classified three per-truth statements that were not
   registered predictions.

The final contract binds the actual timing and production wrappers and budget
preparer, rejects helper drift, requires `within_4h`, and requires the timeout
to cover at least the ceiling of the conservative projected workload. The
projection charges preparation, actual timing, one production integration
construction, linearly scaled generation/scoring/serialization/validation with
the 1.5 factor, the synthesis reserve and termination grace. Source changes
invalidate timing.

One preparatory check previously instantiated 20 unscored timing-root blocks
and printed only generator timing and analytic field controls. It consumed
1.2734765 seconds, saved no histories or diagnostics, and evaluated no score or
endpoint. It is preparation evidence, not prospective evaluation or timing
qualification. The registered production root remains unused. The required
source-bound timing run must still regenerate and score its registered 16
complete blocks across all 17 cells, the full bank and full grid, under the
final source hashes below.

## Verification and source identity

Independent local verification on the reviewed tree produced:

- `30 passed in 4.50s` across the four Goal 051 test files;
- Ruff clean for the three modules, two CLIs and four test files;
- mypy clean for the three modules and two CLIs;
- `git diff --check` clean.

Reviewed SHA256 identities:

| File | SHA256 |
| --- | --- |
| registration | `1334ebd634dcfa09f4ac2837301fb6eaf854f67ea3b0c65ed988a75b887dd758` |
| reviewed proposal | `29bd6730c486d6f500953c9ddb4c33c66ad606f47314d5203e7081fc51686cfe` |
| generator | `e323f7554b1a6b72cfbccdba664d12a094811c12108c4537b5fad3b0519ecfbb` |
| campaign | `ecd162cc50e6e253763ac5cf092ecae170a89c4559eba97e0f72e36187c2f574` |
| synthesis | `0959e99762d33e28f9be95267775268db2416f78bf5f4e16112c2046a8b40f4f` |
| runner CLI | `b168d154d0c9b5f70e64f91c03115e300e4c97be9113d0373ad6d82d49ccbcd6` |
| synthesis CLI | `b8b358f599bd42ed957ca062fbd3831d52794611eb4b3d482c55121ad29fb2f0` |
| bounded wrapper | `e9720784e70a1d16a135ce078a2a77296ab3598b8053b2da8e1854df1096a1b4` |
| synthesis wrapper | `8271fb26026d3d1484859bdb5e75003598e18b4d40f149f9be1098f97d2a6baf` |
| budget preparer | `3abfd04c22b8e913a9d2b8a3607df9eb5b20a7b700434b116bffa527195d57a3` |

These are review identities, not substitutes for the remote timing contract;
the staged tree must reproduce them and bind every additional source file that
the runner records.

## Residual limits and recommendation

The implementation supports a prospective robustness screen on one landscape
with frozen known nuisances, a fixed bank and fixed calibration tables. It does
not establish plug-in size control, model identifiability, general
detectability, alternative-model discrimination or Paper 1 Pillar 4
completion. Selection of a largest cell remains winner-biased and requires the
registered independent confirmation.

No remaining material scientific or implementation defect blocks timing.
Another pre-timing scientific review is unlikely to change this decision if the
staged source and remote qualification checks agree. Independent result review
will materially affect confidence in any prediction, nomination or manuscript
claim and remains required after synthesis.
