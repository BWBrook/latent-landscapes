# Direct spatial-profile development evidence

This is the bounded numerical evidence for the
[31 October development record](../../paper1-direct-profile-development-2026-10-31.md).
It preserves a fixed empirical-plus-pseudo arrival law. It is not production
qualification or evidence of calibrated uncertainty.

- `kernel/kernel-receipt.json`: 120-site value/derivative checks, historical
  high-hazard raw evaluation, order-816 high-x roundoff and timings.
- `kernel/laplace-gradient-receipt.json`: analytic alpha/beta/log-sigma
  derivatives of the complete Laplace criterion versus 18 centred-difference
  comparisons, at two step sizes and three effects. These are criterion
  checks at an incumbent, not three new fitted optima.
- `audit/fixed-h3-receipt.json`: independently executed real B_H3 fixed-h3
  fit using the order-816 bank plus matching raw arrivals.
- `mode_solver/`: identical-parameter comparisons of the original solver
  against the final solver, including cross-evaluation at refitted points.
- `benchmark/`: original, rejected-Newton and final guarded-solver receipts.
- `source/`: exact final kernel, profile adapter and benchmark source, plus
  the original and rejected solver versions for reproducible comparisons.
- `kernel/differentiable_likelihood-19157fbe.py`: exact earlier source used by
  the independent h3 fit. The final source adds the sparse-calendar gate and
  a branch-mask repair; canonical-calendar likelihood algebra is unchanged.
  The receipt's earlier hash is retained, not relabelled as the final version.

Inputs remain in their existing ignored artifact directories. Receipts retain
input paths, hashes, training-site identities and bank count. No evaluator or
truth files are opened. The observation package contains
160 sites; its 40 held-out rows are excluded before constructing the fitting
criterion. The small archived replay scripts retain their original bytes and
location-relative roots; to rerun, copy them to the original artifact paths
recorded in their receipts. The mode comparison also needs the original
`spatial_profile-lbfgs.py` snapshot beside its script. Run from the repository root with the
project environment and `OPENBLAS_NUM_THREADS=1`,
`VECLIB_MAXIMUM_THREADS=1`, `OMP_NUM_THREADS=1`.
`verify_receipts.py` runs directly from the repository root and checks bound
source/input identities, explicit historical source snapshots and profile
scope. `verification.json` also hashes the archived payload.

The independently run h3 invocation was:

```sh
.venv/bin/python scripts/benchmark_spatial_profile.py \
  --input-dir artifacts/goal060_execution/audit-repair/public_inputs \
  --arrival-bank artifacts/goal060_execution/audit-repair/arrival_bank/arrivals.npy \
  --compressed-bank artifacts/paper1_profile_development_20261018/arrival-bank-order816-max290.npz \
  --observations artifacts/goal062_execution/completed-20261015/snapshot/production/evaluation/cell-09/rep-000/observations.npz \
  --likelihood-backend direct --fixed-h 3 --profile-points 3 \
  --output-dir /tmp/latent-fast-fixed-h3-audit
```

`profile_certified=false` remains intentional even when all reported mesh
nodes resolve. The direct backend's `proposal_grid_supported` reports domain
support, not a joint Gaussian-tail or integration-accuracy certificate.
Kernel truncation bounds exclude floating-point roundoff. Acceptance keys
such as `value_error_le_1e_11` denote the receipt's stated 1e-11 error tolerance.

The two `*-trust-full35-order192.json` receipts contain complete mesh results.
The corresponding `mode_solver/*-full35-old-solver-comparison.json` files
cross-evaluate every retained positive node and free optimum. The generalized
replay accepts `--observations` for the H3 package. `profile-meshes.png` and
`profile-meshes.pdf` plot these uncalibrated meshes; `plot_profiles.py` regenerates
them from the archived receipts when run from the repository root.

The final verification log records 167 focused tests, Ruff and strict mypy.
Source hashes distinguish original, rejected and adopted solver versions.
