# Full-ensemble bank review, 6 September 2026

The matched 32768-draw reference completed in 10749.6 seconds (2.99 hours).
Both bundles use source `e8c08f10f7b67118a85ee37770d8ee48ee2c213a`, the same
250 calibration and 250 evaluation histories, six conditions, and G201/H181
grids. Exact history seeds, bank-seed prefixes, event diagnostics, checksums,
and all 24 retained canary surfaces (four histories across six conditions)
reconciled. This is numerical sensitivity
evidence from nested banks, not independent replication.

## Decision

The 16384-draw candidate does **not** pass the recorded wider-range cutoff
criterion. The next check is a complete matched 65536-draw reference against
32768. No bank is promoted automatically. Scientific settings, numerical
criteria and calibration rank remain unchanged.

| Condition | Cutoff at 16384 | Cutoff at 32768 | Change | Coverage count change |
| --- | ---: | ---: | ---: | ---: |
| usual_1 | 44.01769 | 44.53693 | +0.51923 | +1 |
| usual_3 | 44.57865 | 45.09474 | +0.51608 | +1 |
| usual_5 | 44.81918 | 45.19271 | +0.37354 | +1 |
| slow_1 | 20.17938 | 19.98955 | -0.18983 | 0 |
| slow_3 | 20.13833 | 19.94932 | -0.18901 | 0 |
| slow_5 | 20.30831 | 20.22087 | -0.08744 | -1 |

All individual rho endpoints moved at most one G201 cell. No support component
or domain-boundary classification changed. Mean log-width changes were at most
0.001165, below the 0.013863 log-grid spacing; median widths were unchanged.
The first two cutoff changes nevertheless exceed the recorded 0.5-LR limit.

Calibration history 198 remains rank 239 in usual_1 and usual_3, so their
exceedance is not a rank-switch artefact. A separate predator-marginal diagnostic
reproduced a 0.51873-LR change, with unchanged fitted rho 1.086735. Training site
`cluster_20_site_0` contributed 0.32978 of this change; its integrated predator
history probability at generating rho fell from 0.000127666 to 0.000111202.
This localises sensitivity to a rare history under the integration bank.
The diagnostic holds the effect at one; it is not numerically identical to the
joint profile that maximizes over effect.

## Primary comparison and bootstrap sensitivity

The same 1000 calibration/evaluation bootstrap index pairs were used for both
banks. All 30 primary paired confidence intervals include zero at both bank
sizes. Coverage and no-effect-exclusion point contrasts were unchanged. Maximum
changes in the paired mean-error, log-width and conditional-score contrasts
were 0.0003601, 0.0005007 and 0.00001415, respectively.

Speed cutoff bootstrap bounds changed by less than 0.141 LR; individual paired
bootstrap cutoff differences reached 0.922 LR. Coverage bootstrap bounds
changed by at most 0.0001, although individual resampled coverage differences
reached 0.02 because resampling can repeat an affected history. These are
paired sensitivity diagnostics, not independent confidence intervals for a
second experiment. Exact results and hashes are in
[bank16-32-comparison.json](bank16-32-comparison.json).

## Grid interpretation and independent methodological review

A specialist reviewed the retained midpoint checks and full saved grid profiles.
The original four-history midpoint check found maximum LL gain 0.08756 and
spread-profile LR change 0.1751. Across the two complete saved bundles, all
3000 evaluation profiles were monotone outward from their grid MLE, and every
observed-cutoff support was one connected interior component. The parent
independently verified this monotonicity. Minimum adjacent-node LR jumps at
support crossings were 3.859 and 4.052 in the two banks.

The review supports retaining G201 and describing intervals explicitly as
**grid-based profile supports**. Their endpoints, connectivity and widths are
discrete-grid quantities; continuous-profile endpoints have not been verified.
The midpoint evidence concerns four preselected histories, not every campaign
history. It does not justify a universal continuum-resolution claim.
No G401 replay is required for the stated grid-based estimator.

The full 32768/65536 comparison avoids selecting favourable calibration-rank
or endpoint sentinels after seeing the failure. Apply the same cutoff,
topology, endpoint, width, coverage and primary-interpretation criteria. Also
repeat the original bank canary on the four preselected histories: known-speed
effect, profiled effect and profiled rho LR changes in the union LR<=10 range,
direct truth-LR changes, MLE movement, and rho topology/endpoints at cutoffs
2, 5 and 10. Both families must pass; unchanged G201 does not require rerunning
the midpoint calculation. If they pass, document any candidate-bank amendment before final acceptance and run
the final synthesis from that accepted bundle. If it fails, diagnose before
further escalation. A fresh independent final scientific audit remains pending.

## Reproducibility pointers

- Candidate remote output:
  `/data/codex/artifacts/goal045-production-16384-20260906-e8c08f1/output`.
- Matched reference:
  `/data/codex/scratch/goal045-full-bank-reference-20260906-e8c08f1`.
- Local comparison script:
  `artifacts/goal045_execution/compare_full_banks.py`.
- Local reference/provenance and rank diagnostic:
  `artifacts/goal045_execution/reference32768/`.
- Bulky banks remain remote and raw profiles remain outside Git.

## Next reference launch receipt

The matched 65536 reference launched at 2026-09-06 02:52:32 UTC under
`/data/codex/scratch/goal045-full-bank-reference64-20260906-e8c08f1/`, with
status `RUNNING` and all eight extension workers started. The conservative
runtime projection is 8.78 hours. The runner and wrapper passed syntax/Ruff
checks; the next four bank seeds generated identical arrays serially and with
spawned workers both locally and on deep-server. No outcome is yet accepted.

Frozen runner SHA-256:
`bd2cde5536b67c6df50b117a3de5c41c82a4512493a9a7dd2edfd78f055846d0`.
Wrapper SHA-256:
`996d1a56100ae9141fcdd1ad10ce49938d252f0035b4ee330c969cdfd3ed3b99`.
The exact files, `full_reference64.py` and `run_reference64.sh`, are retained
in the remote run root and locally under `artifacts/goal045_execution/`.
