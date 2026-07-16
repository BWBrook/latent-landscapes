# Decision 0001: Rebuild from SpatExt

- **Status:** Accepted
- **Date:** 2026-07-16

## Context

Legacy SpatExt contains the synth-small failure-discovery history and potentially
useful components, but Latent Landscapes has a narrower scientific question and
a staged method programme centred on identifiability, recoverability, and
uncertainty calibration.

Carrying the legacy repository forward wholesale would blur the boundary
between historical exploration and the new programme's controlled evidence.

## Decision

Create Latent Landscapes as a new repository. Treat legacy SpatExt at accepted
scientific endpoint commit `53462d0365babf2c8070714a930f69b4071af276` as a
read-only laboratory notebook and parts catalogue.

Transplant only independently useful components. Each transplant must record
its origin commit and file and whether it was copied, adapted, or rewritten.
The new repository must not depend on SpatExt at runtime.

## Deliberately Not Inherited

The new repository does not inherit by default:

- SpatExt Git history or repository structure;
- legacy package, environment, workflow, or goal-control scaffolding;
- legacy APIs, module boundaries, or naming;
- exploratory parameter choices or inferential assumptions;
- generated outputs, caches, or intermediate data; or
- failed designs as implementation defaults.

The synth-small history remains evidence for failure discovery, not a template
for the new implementation. Scientific conclusions and useful components may
be carried forward only through explicit review and provenance.

## Consequences

The programme starts with a small, reviewable surface and can build modularly
from synth-medium. Reuse requires deliberate evaluation and documentation, but
the resulting methods and evidence remain independent of the legacy checkout.
