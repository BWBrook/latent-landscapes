# Independent review: profile and bank qualification

1 November 2026. Bounded numerical development on the two archived 120-site
histories; no calibration, globality or higher-accuracy integration claim.

## Method before execution

The independent methodological reviewer accepted the prospective design in
`../../paper1-profile-bank-qualification-2026-11-01.md`: three diagnostic level
sets, both variance families throughout, dense baseline refinement, tighter
root/free replay and casewise independent-bank comparisons. The review rejected
using 10–15 adaptive fits as an already-qualified substitute for topology
checks. It distinguished nuisance-bound contact from an endpoint proved to be
bound-determined, and a likelihood ridge consistent with depletion from a
causal mechanism established by observation-design ablation. Arm B and remote
throughput work remain separate follow-ups.

Equal-K sampling sensitivity is separated from the pseudo-mass change when K
increases. Adup repeats the A empirical distribution at nominal 2K while keeping
seven pseudo-arrivals; it is not an independent 2K bank. Both variance families
must enter the fixed-fit envelopes and projected-gradient checks. A material
perturbation requires an actual Adup profile refit. The outer quadratic
criterion-deficit estimate q/2 is distinguished from its one-fit LR contribution
q and from the latent-mode decrement.

## Endpoint and input audit

A second independent reviewer accepted the free-effect endpoint repair: test
log(h) membership before exponentiation, clamp only the valid roundoff at 30,
and preserve invalid out-of-domain coordinates. Both variance families pass the
endpoint and neighbouring-outside-domain regression tests. The real-input
replay adds eight checks across both histories, both families and h=1/30;
free and fixed criterion values agree exactly, with finite gradients.

The bank loader's initial failure was diagnosed rather than bypassed. Frozen
file hashes, all 17 arrival-generating arrays and original row replay match
exactly. Reconstructed exposure values differ at the last floating-point bits.
Arrival simulation never consumes that reconstructed exposure or generator
setup. Review accepted a dedicated arrival-only loader with exact frozen-input
checks, preserving the old loader and input files. The input-reconstruction
receipt records the numerical difference, three original-row replays and
393216 unique seed values with zero pairwise intersections across B0/A/B.
The actual new generator uses precisely the reviewed row range K:3K.

## Implementation review before profile launch

Review found and prompted repairs to the first orchestration draft:

- retain and reconcile both sweep directions rather than overwriting them;
- close the free maximum again after new roots, switches and tighter points;
- replay the complete discovery mesh under tighter controls;
- enforce original-bank identity and 69-node refinement for B0;
- verify archived parameter values separately from legitimate reoptimisation;
- preserve unavailable sets and every detected component and root;
- verify narrow root brackets explicitly rather than treating Brent tolerance
  alone as a measured final bracket;
- distinguish numerical single-bank status from the external bank gate;
- bind bank role, seed provenance, data identities and scientific source bytes;
- classify Hessian diagnostics as unavailable if finite/PD/asymmetry/conditioning
  checks fail, while preserving the original gradient gate.

The independently accepted frozen qualifier hash is
`838c50fe02aba4624174b7713a74cbc6b56d6d57e080d2acab919125f53d3c25`.
The level-set helper hash is
`098076b28b8a2d40fe8646d12d8b5a28af99779bca0e8b5d5334139bee17dbd3`.
Thirty focused qualifier/helper tests and scoped Ruff/mypy passed before
launch. This authorises B0 execution and receipt inspection, followed by the
prespecified bank comparisons; it is not acceptance of unobserved results.

## Pseudo-mass and aggregate gate review

Independent tests verify actual K=131072 duplication, category counts, all
193 positive moments and the 2K+7 denominator; source-A substitution rejection;
and both-family replay at the tight free fits/final roots and standard anchors.
The review also prompted exact cross-history/source/role checks, binding Adup
to the supplied A bank and its manifest, and binding the pseudo diagnostic to
the exact fitted A receipt. The aggregate recomputes the required-refit trigger
from retained LR, gradient and family-ownership evidence rather than trusting
a Boolean summary. It does not average away a failed history or anchor.
Fourteen focused pseudo-mass/aggregate tests pass after those corrections.

## Execution receipt review

Independent receipt review accepted initial H3 B0 numerical resolution:
100 standard / 99 tighter points, maximum selected projected gradients
6.89549e-4 / 9.20295e-5, no retained candidate above its family maximum,
maximum W discrepancy 2.43444e-8 across 89 common points, and maximum root
residual 7.62144e-6. All 72 archived parameter replays are exact; maximum
archived W movement is 5.45697e-12. All three detected sets are connected;
the c=6.63 set contacts h=1. A positive-variance lower-bound contact at the
lower c=3.84 root is tied with exact zero and is not interpreted as causal
bound determination. The parent verified all 114 source/input bindings.

B_H3's initial indeterminate receipt remains a failure. Independent review
found the implementation's three-depth refinement cap was reached at 76
standard points, with no tighter points. Only repeated interior-peak triggers
near the already fitted h=4.195183447 maximum remain. No cutoff, switch or
bound-contact novelty caused the stop. The parent verified its 114 bindings
and all 109 generation source/input bindings.

Review accepts a disclosed post-outcome implementation repair: retain every
feature detector and threshold, replace the arbitrary three-depth cap with
continuation until features resolve or the existing 160-point guard raises.
Tests must cover refinement beyond three rounds and exhaustion. Preserve the
old source and receipts; replay H3 B0 too so the existing exact-source bank
comparison contract needs no exception. Fresh H3 A/B may run with both B0
replays under the four-process amendment. Final receipt review and cross-bank
acceptance remain pending.


The amended runner hash is
`ef484ba6e4db750e41ce5a5615283b03ef503c59f5e5ccc73ffca0c344f7446e`.
Independent patch review accepts launch: feature predicates, tolerances,
160-point guard, both-family fitting and downstream checks are unchanged.
The regression suite passes 19 tests, including deeper smooth-peak refinement,
actual point-budget exhaustion and non-representable-midpoint failure. Ruff,
production-script strict mypy and diff whitespace checks pass. A strict mypy
check of the test module additionally exposes three pre-existing dynamic-module
`no-any-return` errors; these are outside this repair and remain unchanged.
