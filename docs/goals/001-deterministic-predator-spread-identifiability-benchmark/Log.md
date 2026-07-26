# Goal 001 Log

## 2026-07-16: Goal Approved

Barry approved the deterministic predator-spread foundation benchmark and the
separate synthetic road/transect accessibility design. The agreed purpose is
to test one spread-rate parameter under imperfect direct observations before
adding process stochasticity, more parameters, prey, or indirect inference.

The design was refined collaboratively to include a frozen whole-cluster
holdout and a same-parameter geometry-only neutral comparator. The goal treats
negative identifiability or model-comparison outcomes as valid evidence and
forbids unrecorded retuning.

Implementation began on branch
`codex/latent-landscapes-goal001-deterministic-spread` from
`804cec502de03c9de52e2c9afa84f37e26ea096f`.

## Progress Notes

- Legacy reconnaissance identified the minimal transplant as the in-memory
  synth-medium landscape builder plus deterministic weighted multi-source
  arrival primitive.
- The accepted legacy provenance endpoint is
  `53462d0365babf2c8070714a930f69b4071af276`.
- The legacy movement-scale value `0.88` is retained inside the baseline cost
  surface; the new estimand is an intuitive multiplicative rate `rho` with
  truth `1.0`.
- One canonical realization is intentionally retained. Repeated-seed recovery
  and calibration belong to a later goal.

## 2026-07-16: Implementation Result and Independent Review

The canonical implementation completed with outcome `advance_goal002`. The
full-data habitat support is `[0.9994971078624002, 1.000069859134422)`, width
`0.0005727512720217209`; it contains `rho = 1`. The habitat held-out total
Bernoulli log score is `-130.21690767826243`. The neutral held-out score is
`-Infinity`, with four impossible positive records under the frozen model.
Exactly nine deterministic ignored review files were generated.

Independent review accepted the frozen scientific result but identified five
reporting and regression defects requiring a narrow final fix:

- `implementation_blocked` still wrote a bundle and exited successfully;
- negative outcomes inherited positive advance/habitat-win prose in
  `review.md` and `likelihood_holdout.svg`;
- the neutral `-Infinity` score lacked its observable-data explanation and
  explicit observation/inference/assumption/limitation split;
- structural versus practical identifiability and the descriptive,
  non-Wilks-calibrated stepwise support needed sharper wording; and
- the holdout-partition test did not assert endpoint closure or exact,
  gap-free, non-overlapping coverage of the training-MLE class.

The fixes were confined to `scripts/run_goal001.py`, the artifact renderer,
the two affected test modules, this log, and exact CLI wording in `README.md`.
No science, RNG, design, likelihood calculation, dependency, outcome, or
nine-file contract was changed.

## 2026-07-16: Final-Fix Validation and Publication Stop

Test-first evidence was recorded before the implementation edits: the focused
suite failed in the intended places with 8 failures and 7 passes, including a
real `__main__` invocation that wrote nine files and did not raise
`SystemExit` for `implementation_blocked`. After the narrow fixes, the same
focused suite passed all 15 tests.

Fresh repository-root validation then produced:

- `uv run pytest --cov=latent_landscapes --cov-report=term-missing`: 26 passed,
  97% total coverage;
- `git diff --check`: clean;
- `uv run ruff format --check .`: 15 files already formatted;
- `uv run ruff check .`: all checks passed;
- `uv run mypy src tests`: no issues in 14 source files; and
- `uv build`: source distribution and wheel built successfully.

The canonical bundle and two clean temporary bundles each contained exactly
nine files, and recursive byte comparisons found no differences. The
regenerated summary retained the exact scientific values above and now records
the four zero-probability detections at `cluster_22_site_1` (`t=50`, one),
`cluster_22_site_3` (`t=50`, two replicates), and `cluster_26_site_1` (`t=90`,
one). Analyst-facing `observations.csv` remains free of latent truth fields.

Generated `artifacts/` and `dist/` products remain ignored and unstaged, and
the staging area is empty. Stop before publication: no staging, commit, push,
merge, Goal 002 work, or external exposure is authorized until Barry completes
human review and explicitly approves the pack.

## 2026-07-16: Re-review Conditional Reporting Fix

Re-review found that the neutral zero-probability counts were data-derived but
their accompanying summary and review narrative was still unconditional: a
noncanonical result with no universally zero-probability detection would still
claim four records and `-Infinity`. The SVG also lacked enough standalone
context for the neutral score and nominal support.

The regression now constructs a coherent noncanonical neutral comparator by
recomputing its training profile and holdout evaluation from matched distances
and observation records. That case has one neutral training-MLE partition, a
finite held-out log score of `-130.21690767826243`, zero impossible positives,
and no detection record assigned zero probability by every partition. Its
summary, review, and figure report that finite evidence and contain none of the
canonical four-record identifiers or `-Infinity` narrative.

Artifact reporting is now conditional on the supplied neutral distances,
partitions, and score range. `summary.json` also records the algebraic scope of
ideal structural identifiability, `likelihood_shape = discontinuous_stepwise`,
and `wilks_calibrated = false`. The likelihood/holdout figure compactly reports
the zero-probability count, hard zero-false-positive assumption or finite-score
state as applicable, descriptive non-Wilks support, and the outcome decision;
site identifiers remain in `review.md` rather than the figure.

Test-first evidence for this re-review fix was 2 intended failures and 8 passes
before the renderer change, followed by 10 focused passes. Final root
validation remained 26 passes with 97% total coverage; `git diff --check`, Ruff
format and lint, mypy, and `uv build` all passed. The canonical and two clean
temporary bundles again contained exactly nine byte-identical files. A Chrome
render confirmed that figure panels, legend, axes, bars, and the compact
textbox remain legible without overlap or clipping.

The canonical outcome and all scientific numbers remain unchanged. Generated
`artifacts/` and `dist/` outputs remain ignored and unstaged. The same
stop-before-publication boundary applies: no staging, commit, push, merge,
Goal 002 work, or external exposure before Barry's explicit approval.

## 2026-07-26: Comparator Framing Repair

Barry approved a narrow interpretive repair in response to review of the
canonical held-out comparison. The machine-readable `neutral` model is now
described consistently as the geometry-only hard-front comparator. Its
canonical held-out `-Infinity` score is explicitly identified as a structural
support violation under deterministic occupancy and known zero false positives,
not an optimizer failure or a calibrated magnitude of model superiority.

The finite Brier comparison is presented as corroborating descriptive evidence,
and a distinct full-support predictive neutral baseline is reserved for later
work rather than retrofitted into Goal 001. Likelihood calculations, frozen
design, comparator geometry, numeric scores, outcome class, and the nine-file
artifact contract are unchanged. Generated artifacts remain ignored and
unstaged pending Barry's review.
