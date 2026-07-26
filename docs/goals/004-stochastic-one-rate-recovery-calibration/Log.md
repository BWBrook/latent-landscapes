# Goal 004 Log

## 2026-07-26: Goal Authorized

Barry accepted Goal 003's faster induced stochastic landscape-scale wave
without normalization and approved Goal 004 as a combined one-rate recovery
and calibration benchmark.

The prospective survey calendar is `10, 20, 30, 40, 50, 60`; the accepted
Goal 001 sites, clusters, split, visits, known detection probability, and
zero-false-positive observation rule remain fixed.

The primary method is a site-history simulated composite likelihood that
marginalizes within-site detection histories over an independent stochastic
arrival bank. It explicitly does not claim to represent the full joint
spatial likelihood. The full-support time-only neutral remains the predictive
baseline.

No Goal 004 source, generated artifact, simulation, fitting, commit, or push
had been started when this contract was frozen.

## 2026-07-26: Production Benchmark Completed

Goal 004 was executed locally without scientific tuning, normalization, seed
replacement, bank enlargement, remote compute, staging, commit, push, or
publication. The fitted method is the site-history simulated composite
likelihood. It preserves dependence within each site's repeated history and
omits between-site process dependence, so it is not a full joint spatial
likelihood.

### Source identity

The production checkout remained at the pinned parent commit
`b7b17b611baa2b5abe9093c1f4af421f0672dfa9`. Runtime reconciliation proved
that this commit is an ancestor of `HEAD` and that its four source paths have
the frozen blobs:

| source | pinned blob |
| --- | --- |
| Goal 001 landscape | `a376df359e09b2357a0b5262479bcebaeee2ff25` |
| Goal 001 design | `ca9c60d3f113fcde48985395652974337421dfa7` |
| Goal 003 stochastic spread | `d20440415ea33cee0f64f41427ae81197ca8fd9e` |
| Goal 002 neutral baseline | `290cc0b608004ec75cbfa2f922d5c29f56b5271c` |

The authorized Goal 004 adaptation of
`src/latent_landscapes/goal002/baseline.py` had working-tree blob
`f4aec0393fbba8b70b5ac6321898cde09256fd75`; its regression tests prove that
the Goal 002 default calendar and behavior remain unchanged. Goal 001
landscape and design and Goal 003 spread runtime files also matched their
pinned blobs.

The checkout branch was
`codex/latent-landscapes-goal004-stochastic-recovery`. The final 17-file Goal
packet, implementation, documentation, and test snapshot, excluding this
self-referential log, had SHA-256
`defa1b9809c317774abced394e95d91a461f9214998f14eef03ad80b9d9ae160`.
It was calculated by hashing each sorted relative path followed by a NUL byte
and its file bytes. The runtime was Python `3.14.4`, NumPy `2.5.1`, and
Homebrew `uv 0.11.31`.

### Execution and repair chronology

The first pre-repair canonical command started at `2026-07-26 16:11:02 +1000`.
Its tool wrapper returned without exposing the still-running session handle.
The canonical files were written at `16:12:35 +1000`; the exact wall runtime
was therefore not captured and is not inferred here.

While recovering the missing handle, a duplicate invocation was started in
error. It was detected through the process table and interrupted after a
captured `real 15.04 s`, while still generating its integration bank and before
writing any output. Its partial calculation was discarded and never used. The
original canonical process remained the sole writer. The first pre-repair
repeat then completed in a captured `real 90.41 s`, and its bundle was
byte-identical to that canonical bundle.

The final focused gate then exposed four material review-surface gaps:

1. incomplete runtime reconciliation of the pinned parent commit and all four
   source blobs;
2. omission of the between-site-dependence limitation from every CSV and both
   figure surfaces;
3. publication of `verification.json` before artifact-set reconciliation; and
4. failure to map artifact-writer errors to `implementation_blocked` at the
   CLI boundary.

One authorized focused repair resolved those gaps without changing the fixed
science, seeds, grid, bank, calibration, validation, or decision rules. Because
the added review-surface fields changed serialized bytes, the earlier bundles
were discarded and replaced with one fresh canonical/repeat pair using the
unchanged production configuration. The replacement canonical files completed
at `2026-07-26 16:26:15 +1000`; the repeat completed at
`2026-07-26 16:27:58 +1000`. Exact replacement wall runtimes were not captured
and are not inferred. These replacement bundles are the retained bundles and
are byte-identical.

Independent final audit then found that refreshing an already-valid target
rejected its existing final verification marker. A writer-only idempotence
repair now removes that prior marker before deterministic refresh and restores
it only after file-set reconciliation. A same-target byte-identity regression
test passes. This last repair changes neither serialized content nor scientific
calculation, so the production ensemble was not rerun.

### Validation

Fresh post-repair validation from the repository root:

| command | result | runtime |
| --- | --- | ---: |
| `uv sync --all-groups` | 26 packages resolved; 25 checked | real 0.03 s |
| `git diff --check` | pass | real 0.00 s |
| focused Goal 002/004 `pytest --no-cov` command from `Plan.md` | 41 passed in 2.07 s | real 2.23 s |
| `uv run ruff format --check .` | 43 files already formatted | real 0.02 s |
| `uv run ruff check .` | all checks passed | real 0.02 s |
| `uv run mypy src tests` | no issues in 39 source files | real 0.08 s |
| `uv run pytest` | 104 passed in 21.72 s | real 21.88 s |
| `uv build` | sdist and wheel built | real 0.38 s |
| replacement canonical `uv run python scripts/run_goal004.py` | 12 files; completed at `16:26:15 +1000` | exact wall time not captured |
| replacement repeat CLI with `--output-dir ..._repeat` | 12 files; completed at `16:27:58 +1000` | exact wall time not captured |
| `diff -rq` between the two bundles | no differences | real 0.00 s |

Both SVGs were rendered in headless Chrome and inspected. Both were nonblank,
readable, unclipped, and explicitly labelled
`between-site process dependence omitted`.

### Scientific result

Every hard implementation invariant passed. All three bank variants produced
the same downstream class:

| bank | cutoff | coverage, 95% Wilson interval | interior topology | boundary contacts | mean support width, arithmetic / log-rate | mean MLE set size | mean truth distance / absolute log-rate error | mean worst-MLE stochastic / neutral Brier | paired Brier mean, 95% normal interval | class |
| --- | ---: | --- | ---: | ---: | --- | ---: | --- | --- | --- | --- |
| full, 4,096 | 52.43798271483206 | 468/500 = 0.936, [0.911047591162316, 0.9543039839552107] | 500/500 | 0 | 0.17464778502700037 / 0.17396145839573135 | 1.0 | 0.039719289762211556 / 0.03966650265284379 | 0.13925053919808486 / 0.18708956199101254 | -0.04783902279292768, [-0.04857410235067318, -0.047103943235182175] | `advance_one_rate_stochastic_spread` |
| first half, 2,048 | 51.461724484605156 | 467/500 = 0.934, [0.9087605988391466, 0.9526214736402262] | 500/500 | 0 | 0.1730783197396917 / 0.17244577656090693 | 1.0 | 0.03936307971032969 / 0.03932455004376755 | 0.13926418060694193 / 0.18708956199101254 | -0.047825381384070616, [-0.048559386695618344, -0.04709137607252289] | `advance_one_rate_stochastic_spread` |
| second half, 2,048 | 53.317375493515556 | 468/500 = 0.936, [0.911047591162316, 0.9543039839552107] | 500/500 | 0 | 0.17605830138611045 / 0.1753015429448139 | 1.0 | 0.039845981950280586 / 0.03976816423932592 | 0.13924426076894134 / 0.18708956199101254 | -0.04784530122207121, [-0.048580435689708955, -0.04711016675443346] | `advance_one_rate_stochastic_spread` |

The overall class is `advance_one_rate_stochastic_spread`. This conclusion is
conditional on the frozen landscape, design, `rho = 1`, calendar, known
detection model, rate grid, and finite integration scheme. Calibration was
not assessed away from `rho = 1`, and the composite likelihood omits
between-site process dependence.

### Artifact identity

The canonical and repeat bundles each contain exactly 12 ignored files and
are byte-identical. Their shared SHA-256 hashes are:

| file | SHA-256 |
| --- | --- |
| `bank_stability_summary.csv` | `9558bf306adefe23353a5101b5fa4719915e2e77774ab11c6d331ee7f03328ff` |
| `calibration_results.csv` | `b58948c1cef673d7db5af6cec1e702dbbef4c0086476c4446655ea510b60d33e` |
| `config.json` | `c8fb894f57b867f4f44d72dfc991a2383a0573495c12286ec840f98ffddbe3f9` |
| `predictive_summary.csv` | `72b1837b47f0a273b305251c624848dbbbcfc6ad3516747909acb50101936766` |
| `representative_profile.csv` | `60c57bfb470d2af83f8aa8e895745c1ba63e3fbde3d56459398a4c3bb25845b4` |
| `review.md` | `21b5c4fdbc7354a361962875c4f7e737c623cd5bb0e08eef9c1ffb19889f31bd` |
| `seed_manifest.csv` | `10d13f2acb203f42776f06e863a537b6da7a8ee7c6ee172fdb3bca7f99262e92` |
| `summary.json` | `c2a0cd524f97af0879c7d54fdf31863898446ec35ca53a43d6c7c1385f743093` |
| `validation_results.csv` | `dd85b194d19317f9f44f3b9849f3f073e733c9d6944b197d3aab19ddc82ac606` |
| `verification.json` | `5aab8c75154b2f6c7515fa388f06d5f62149812a325e562729630b71fd71f583` |
| `visuals/predictive_comparison.svg` | `3b34a41ff5eff281435df204b7ffad06f33eec1764b860a10b91fb574c58dc08` |
| `visuals/recovery_calibration.svg` | `a61c118169f29794123bec77a2b75bc49660a957f1ef7144cf5211ddc8247d98` |

The canonical output is
`artifacts/goal004_stochastic_one_rate_recovery/`; the repeat is
`artifacts/goal004_stochastic_one_rate_recovery_repeat/`. Both are ignored and
unstaged. Build products under `dist/`, the local `.venv/`, and SVG inspection
renders are also ignored and unstaged. All Goal 004 source, tests,
documentation, and control-log changes remain unstaged. No commit, push,
merge, publication, remote compute, or Goal 005 work was performed.
