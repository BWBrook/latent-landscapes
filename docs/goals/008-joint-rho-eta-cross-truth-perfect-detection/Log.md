# Goal 008 Log

## 2026-07-27: Authorized And Frozen

Barry approved the 3 by 3 cross-truth joint `(rho, eta)` perfect-detection
benchmark after Goal 007 passed at the central truth.

The frozen truth grid is `rho = {0.5, 1, 2}` crossed with
`eta = {0.5, 1, 1.5}`. Every cell receives its own local cutoff for the full
and two disjoint half banks. The Goal 007 candidate grids, likelihood,
calendar, perfect observations, neutral comparator, and decision thresholds
remain unchanged.

The same 500 calibration and 500 validation shock blocks are reused across
all nine truth cells. The nine cells are therefore paired counterfactuals,
not 4,500 independent datasets. Cellwise intervals remain pointwise; the
prespecified all-cell decision is not a familywise 95% statement.

Goal 007's central result must reconcile to independent accepted constants.
Ridges, boundary contact, imprecision, local calibration failure, neutral
parity, bank instability, and mixed truth-cell classes are valid completed
results. No retuning, cutoff transport, imperfect detection, prey layer, or
Goal 009 work is authorized.

A live read-only compute probe found `deep-server-ts` healthy and nearly idle
with 64 logical CPUs, 125 GiB RAM, and 4.4 TiB free under `/data`. GitHub SSH
authentication is unavailable there, so the production source will be a
checksummed Git bundle for one clean feature commit. The production campaign
will use nine isolated workers with numerical-library thread counts fixed at
one. Kunanyi is not warranted for this bounded campaign.

## 2026-07-27: Local Implementation And Validation

Test-first implementation began with:

```bash
uv run pytest tests/test_goal008_benchmark.py \
  tests/test_goal008_artifacts_cli.py --no-cov
```

The red gate collected no tests and produced two expected
`ModuleNotFoundError` errors because `latent_landscapes.goal008` did not yet
exist. The implementation then added a thin Goal 008 campaign layer that
reuses Goal 007's fixed inputs, integration bank, perfect observations,
duplicate collapse, joint likelihood, support summaries, tied-MLE prediction,
neutral comparator, and scientific thresholds.

Goal 008 owns the exact row-major truth grid, common-shock block generation,
exact rho scaling, 27 cell-local cutoffs, deterministic sequential or
multi-process aggregation, worst-cell decision precedence, independently
frozen central reconciliation, exact 16-file review pack, and fixed-surface
CLI. Tiny one-worker and two-worker campaigns produced identical hashes of all
returned scientific content. Two independently written tiny review packs were
byte-identical, including normalized SVG identifiers.

Local verification outcomes were:

```text
git diff --check
  passed
uv run pytest tests/test_goal008_benchmark.py \
  tests/test_goal008_artifacts_cli.py --no-cov
  10 passed
uv run ruff format --check .
  passed
uv run ruff check .
  passed
uv run mypy src tests
  passed; 65 source files checked
uv run pytest
  147 passed; three inherited Goal 006 PendingDeprecationWarning entries
uv build
  passed; source distribution and wheel built
```

No production campaign, remote compute, staging, commit, push, Git bundle, or
Goal 009 work was performed. Generated test outputs were temporary, and
`artifacts/` plus `dist/` remain ignored.

## 2026-07-27: Provenance And Boundary-Audit Repair

Independent review identified two material audit gaps. First, the production
CLI accepted a missing provenance path and the pack writer did not couple
declared provenance to the actual campaign. Second, validation retained only a
boundary-contact boolean, preventing reviewers from distinguishing contact
with `rho_min`, `rho_max`, `eta_min`, or `eta_max`.

One bounded repair wave made `--compute-provenance-json` required. Production
now requires exactly nine workers and all four numerical-library thread limits
set to `1` before campaign execution. Pack writing then requires production
provenance with portable run and actual host identifiers; exact current source
commit and `uv.lock` SHA-256; a 64-hex bundle SHA-256; successful bundle,
clean-HEAD, focused-test, and smoke declarations; matching Python, uv, NumPy,
and operating-system identifiers; and successful actual campaign/cell
telemetry. The final `compute_provenance.json` records the actual worker and
thread settings plus every cell's exit status, wall time, and normalized
maximum RSS. Reduced provenance is accepted only for explicitly labelled
nonproduction tests. Execution telemetry is excluded from the scientific
worker-count-equivalence digest.

Every validation row now retains the deterministic ordered set of contacted
faces. Truth-cell summaries count contact with each face separately while the
existing any-face boolean continues to drive the frozen decision rule.

The new test-first red gate failed at the absent `support_boundary_faces` API.
During that initial pre-fix test run, the CLI missing-provenance subprocess
incorrectly launched nine local workers. The stale test process tree was
identified and terminated before completion. It wrote no Goal 008 review-pack
files and is not treated as a scientific production attempt. The corrected
CLI was then directly confirmed to exit `2` immediately without provenance,
and live process inspection confirmed no benchmark or test workers remained.

Fresh post-repair validation was:

```text
uv run pytest tests/test_goal008_benchmark.py \
  tests/test_goal008_artifacts_cli.py --no-cov
  11 passed
git diff --check
  passed
uv run ruff format --check .
  passed
uv run ruff check .
  passed
uv run mypy src tests
  passed; 65 source files checked
uv run pytest
  148 passed; three inherited Goal 006 PendingDeprecationWarning entries
uv build
  passed; source distribution and wheel built
```

No remote run, completed production campaign, scientific review pack, staging,
commit, push, Git bundle, or Goal 009 work followed this repair.
