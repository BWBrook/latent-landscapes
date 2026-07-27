# Goal 007 Log

## 2026-07-27: Goal Authorized And Contract Frozen

Barry approved the first joint `(rho, eta)` recovery benchmark as a central
positive control under perfect direct predator detection.

The contract freezes the Goal 001 landscape, access-constrained sites and
cluster split; the Goal 003 stochastic process; the Goal 004 prospective
calendar, onset categories, and time-only neutral; and the Goal 006
geometric-mean-preserving resistance transform.

The candidate surface has 601 exact rho values and nine eta values at 0.25
spacing. Truth is `(1, 1)`. The acceptance analysis retains the established
4,096 integration bank with two disjoint 2,048 halves, plus independent 500
calibration and 500 validation process ensembles. Every bank receives its own
local empirical likelihood-ratio cutoff.

Perfect detection removes the detection stream. The two frozen same-time
visits remain in the analyst-facing table but are verified and collapsed so
they cannot spuriously double information. Two-dimensional support uses rook
connectivity; eta precision is explicitly grid-limited.

A read-only local timing probe measured approximately 0.0172 seconds per
eta-specific shortest-path field on the M4 Mac mini. The production benchmark
is therefore routed locally. `deep-server` remains appropriate for later
parallel campaigns or substantially larger grids; `kunanyi` is not justified
for this bounded serial goal.

Ridges, imprecise support, calibration failure, neutral parity, and bank
instability are valid completed results. No cross-truth sweep, imperfect
detection, prey layer, fitting redesign, remote compute, or Goal 008 work was
authorized.

## 2026-07-27: Goal 007 Implemented And Completed

Implementation added a Goal 007-specific perfect-observation layer,
two-dimensional likelihood and rook-support types, paired eta-bank benchmark,
exact 14-file review-pack writer, and production CLI. Goals 001-006 remained
unchanged. The two nominal same-time visits are retained as 1,920
analyst-facing records, verified as exact duplicates, and collapsed to 960
distinct site-time outcomes before likelihood fitting, neutral fitting, or
scoring. There is no detection stream.

Test-first development began with:

```bash
uv run pytest tests/test_goal007_observations.py \
  tests/test_goal007_likelihood.py \
  tests/test_goal007_benchmark.py \
  tests/test_goal007_artifacts_cli.py --no-cov
```

The red gate produced four expected collection errors because
`latent_landscapes.goal007` did not yet exist. The implemented focused suite
subsequently passed. Final verification commands and outcomes were:

```text
git diff --check
  passed
uv run pytest tests/test_goal007_observations.py tests/test_goal007_likelihood.py \
  tests/test_goal007_benchmark.py tests/test_goal007_artifacts_cli.py --no-cov
  passed
uv run ruff format --check .
  passed
uv run ruff check .
  passed
uv run mypy src tests
  passed
uv run pytest
  passed
uv build
  passed; source distribution and wheel built
```

The canonical Mac-mini run:

```bash
uv run python scripts/run_goal007.py
```

completed in 775.81 seconds with maximum resident set size 409,944,064 bytes.
It wrote exactly 14 ignored files under
`artifacts/goal007_joint_rho_eta_perfect_detection/` and returned:

```text
advance_to_joint_cross_truth_perfect_detection
```

The deterministic repeat completed in 749.16 seconds with the same scientific
class and file set. Its first byte comparison exposed one material packaging
defect: Matplotlib randomized the referenced internal
`C0_0_<10-hex-digit>` path-collection identifier between Python processes.
One focused repair extended the existing SVG identifier canonicalization and
added a direct regression test. The two completed packs were canonicalized
and re-hashed with that repaired writer logic. The final command:

```bash
diff -rq artifacts/goal007_joint_rho_eta_perfect_detection \
  artifacts/goal007_joint_rho_eta_perfect_detection_repeat
```

returned no differences.

All three bank variants independently reached the advance class. The
decision-driving summaries were:

| Bank | Cutoff | Coverage | Interior connected | Median abs log-rho error | Median abs eta error | Median log-rho width | Median eta width | Paired Brier 95% interval |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full | 90.524248 | 475/500 | 494/500 | 0.036968 | 0.000 | 0.346574 | 0.500 | [-0.112825, -0.110822] |
| first half | 91.985528 | 476/500 | 491/500 | 0.036968 | 0.000 | 0.351195 | 0.500 | [-0.112814, -0.110809] |
| second half | 87.520852 | 475/500 | 494/500 | 0.036968 | 0.000 | 0.341953 | 0.500 | [-0.112796, -0.110786] |

For the full bank, the Wilson interval for 475/500 truth inclusions was
`[0.927232, 0.965906]`. There were zero support boundary contacts. Mean
worst-tied-process-MLE Brier score was 0.027120 versus 0.138944 for the
training-only time neutral. Independent recomputation from the calibration
and validation CSVs exactly reconciled every cutoff, coverage count, topology
count, error and width median, paired-Brier interval, and downstream class.
All three SVGs rendered clearly on inspection.

The result contains a material residual ridge despite passing the deliberately
coarse positive-control gates. For the full bank, support-cell rho-eta
correlation had 5th, median, and 95th percentiles
`[-0.873997, -0.837781, -0.819547]`; all 500 values were defined. Supported
cell counts had corresponding percentiles `[101, 109, 118]`. This correlation
is descriptive only, not an inferential correlation estimate. Eta precision
remains limited to the frozen 0.25 grid. Conclusions remain conditional on one
landscape, one central truth, perfect detection, and a site-history simulated
composite likelihood that omits between-site process dependence. Cross-truth
recovery is the next scientific gate, not part of this goal.

Final stable artifact evidence:

```text
pack checksum-manifest SHA-256:
  c729082e2ec199858884bbc647e16fa69d7e68c70e74b10b0c35f942bcb920b0
summary.json SHA-256:
  5bd80e7e2f033c00f91939709a0d9dcc9ebfa3d213c71ad2eb7de899bf19f367
verification.json SHA-256:
  212c711e738d010dfb85c4453fb0ca24fdd1951ca18bdc05edbd2099ba45a575
```

`git status --ignored --short artifacts dist` reported only ignored
`artifacts/` and `dist/`. No source, test, script, or documentation path was
staged, committed, or pushed.
