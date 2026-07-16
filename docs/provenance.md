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
