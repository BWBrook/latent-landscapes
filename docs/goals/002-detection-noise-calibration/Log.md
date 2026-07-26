# Goal 002 Log

## 2026-07-26: Goal Approved

Barry approved inserting a detection-only calibration rung before stochastic
spread or additional focal parameters. The accepted purpose is to determine
whether Goal 001 recovery, nominal support, and habitat predictive advantage
persist across observation randomness while the generating process and survey
design remain fixed.

Barry also approved a distinct full-support neutral prediction: training-only,
time-stratified Jeffreys-smoothed detection prevalence. Paired Brier difference
is the primary graded comparison; log-score hard zeros remain diagnostics.

Implementation begins on branch
`codex/latent-landscapes-goal002-detection-calibration` from accepted Goal 001
commit `70b02e1d8061b347afc5fff3720450c09677cba2`.

The fixed ensemble contains 500 calibration and 500 validation realizations.
Calibration and validation use separate child roots spawned from
`SeedSequence(20260726)`. The empirical 95% cutoff uses finite-sample rank 476
of 500 calibration statistics with no interpolation.

No Goal 002 source, tests, scripts, generated artifacts, commit, or publication
existed when this packet was written.

## 2026-07-26: Implementation and Local Validation Complete

Goal 002 was implemented on
`codex/latent-landscapes-goal002-detection-calibration` from accepted Goal 001
commit `70b02e1d8061b347afc5fff3720450c09677cba2`. The uncommitted implementation
manifest, excluding this log and combining the authorized packet, programme,
README, source, script, and tests in sorted path order, has SHA-256
`ff5a4b593916809da8a641d8c13d01c02eb72cd6b7da784f4ff5e829ce805a8f`.

The canonical production command

```bash
uv run python scripts/run_goal002.py
```

completed the fixed 500-calibration plus 500-validation ensemble in 210.93
seconds and wrote exactly ten ignored files to
`artifacts/goal002_detection_calibration/`. A second clean production bundle
completed in 212.18 seconds. Both bundles contained ten files and `diff -rq`
printed nothing.

The prespecified decision class was `advance_stochastic_spread`:

- the rank-476 empirical likelihood-ratio cutoff was
  `4.199288497994303`;
- nominal validation coverage was `437/500 = 0.874`, with 95% Wilson
  interval `[0.842032282280136, 0.900264711054623]`;
- calibrated validation coverage was `478/500 = 0.956`, with 95% Wilson
  interval `[0.934280557127672, 0.970766044371393]`;
- all `500/500` calibrated supports were one connected interval strictly
  inside `[0.25, 4]`;
- the mean paired worst-habitat-minus-neutral Brier difference was
  `-0.0595956277648168`, with 95% normal Monte Carlo interval
  `[-0.0602499365042150, -0.0589413190254186]`; and
- all `500/500` Jeffreys-smoothed neutral holdout log scores were finite.

The geometry-only hard-front comparator assigned zero probability to a
held-out detection in every validation realization and in every
training-MLE partition. Habitat MLE partitions had at least one such structural
zero in 62 realizations and every partition had one in 6 realizations. These
remain diagnostics and did not enter the graded decision statistic.

Final local validation:

```text
uv run pytest --cov=latent_landscapes --cov-report=term-missing
    61 passed; 95% total coverage
uv run ruff format --check .
    25 files already formatted
uv run ruff check .
    All checks passed
uv run mypy src tests
    Success: no issues found in 23 source files
uv build
    source distribution and wheel built successfully
git diff --check
    no output
```

Goal 001 numerical regressions were unchanged: outcome `advance_goal002`,
full-data maximum log likelihood `-539.6304429931859`, MLE/support interval
`[0.9994971078624002, 1.000069859134422)`, habitat holdout Brier
`0.09444791666666677`, and hard-front holdout Brier
`0.15633333333333344`.

The three SVGs were raster-inspected in Chrome and were readable, nonblank,
unclipped, and consistently labelled. Independent compact-data recomputation
confirmed the cutoff rank, coverage counts, topology count, paired-Brier mean
and standard deviation, neutral full support, and 1,000 unique seed spawn keys
and states. Sampled calibration and validation children replayed exactly.

Canonical artifact SHA-256 values:

```text
9aefff392505ed20fb66bf6851a3c7c29ab8141bc025a5851340d262cd1b40c3  calibration_summary.csv
971b4d26af4d71c8afaf941cf16aef8b7da7cbac4e665312e9a5e0a5036e6c46  predictive_summary.csv
d3ca5b936c1c96280db8169ddd3b6b626e9673d5d141314aacc32a7e22731892  replicate_results.csv
a06cbc0e2bbcb4def029fc0f62db7b08d6a0f342e4572a824a6ba417090c7bf3  review.md
8e40e9b8b19afabc0bf952bbe49437be1b83833143b2264566046ebd1bf6e5a8  seed_manifest.csv
45c90a5d6a47fbee148592ced00105c9c8f6f930fb2c23df70af28667c662df2  summary.json
ed6d38110947b13c50696726306dc90d667c3427caf767be7f104f7ecbc01cc0  verification.json
14d7546bd5bcd7ed3fba1769216ac7c7f7cb53ff2f012eca66d04e5d8800fe1b  visuals/coverage_support.svg
4e166997627cf0781ddb1db4639fe4b59cda58e401726bf708b238e4e8c122ed  visuals/mle_recovery.svg
418ba76537b82a550988049c83ae45ba9b0a92e2cda25a773064619c5d0b3285  visuals/predictive_scores.svg
```

Generated artifacts, distributions, caches, and the virtual environment remain
ignored and unstaged. No commit, merge, push, publication, remote compute,
retuning, raw ensemble-observation retention, or Goal 003 work was performed.
