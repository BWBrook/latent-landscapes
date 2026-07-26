# Provenance Policy

## Legacy Sources

The following are read-only laboratory notebook and parts-catalogue sources:

- `/Users/bwbrook/papers/spatext`
- `https://github.com/BWBrook/spatext`

The accepted scientific endpoint is legacy commit
`53462d0365babf2c8070714a930f69b4071af276`.

Latent Landscapes must have no runtime dependency on the legacy repository.
Legacy content is evidence and a source of candidate parts, not an inherited
codebase.

## Transplant Rule

Transplant only components that are independently useful in the new programme.
For every transplant, record:

- origin repository;
- origin commit;
- origin file path; and
- status as **copied**, **adapted**, or **rewritten**.

Record substantive adaptation or reinterpretation alongside the transplant.
Do not imply continuity merely because a component originated in SpatExt.

## Reproducibility Boundary

All code, configuration, and data interfaces required to run Latent Landscapes
must eventually live in this repository or in explicitly documented external
data sources. Reproduction must not require a local checkout of SpatExt.

## Goal 001 Transplant Record

Goal 001 uses two provenance-controlled SpatExt sources from the accepted
commit `53462d0365babf2c8070714a930f69b4071af276` in origin repository
`/Users/bwbrook/papers/spatext`:

| New component | Legacy source path | Legacy blob SHA-1 | Status |
| --- | --- | --- | --- |
| `src/latent_landscapes/goal001/landscape.py` | `src/spatext/synth/medium/landscape.py` | `f2f5fc24e64274e443f8eec8c314e212e2a6889f` | **adapted** |
| `src/latent_landscapes/goal001/spread.py` | `src/spatext/synth/medium/spread_impact.py` | `cb15f2178ff9e2f359f06fdac34a9b551e163cd5` | **rewritten** |

The landscape adaptation retains the accepted 72 by 84 synthetic geometry,
water, habitat classes, corridors, western source zones, quality surface, and
local water-neighbour counts, but replaces the legacy review-pack machinery
with a minimal in-memory NumPy representation.

The spread rewrite retains the accepted `balanced_corridor_detour_v2`
conductances, `0.88` baseline edge-cost numerator, `0.46` water-neighbour
penalty, multi-source Dijkstra seeding, and lexicographic equal-cost source
tie-break. It removes prey dynamics, candidate tuning, horizons, and legacy
artifact/report code, and expresses the estimand as the global multiplier
`T_i(rho) = D_i / rho` with generating value `rho = 1`.

Goal 001 records the two legacy Git blob identifiers as evidence and also
tests canonical SHA-256 digests of the rebuilt landscape and full arrival
truth. Running or reproducing Goal 001 imports no SpatExt module and does not
require a SpatExt checkout.
