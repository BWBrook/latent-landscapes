# Diagnosis of the two frozen non-regression failures

15 November 2026. This is post-outcome diagnosis of the bounded A+B+C repair,
advancing Paper 1's numerical-qualification decision. It does not amend the
frozen acceptance plan or open qualification, training or validation. The
parent session subsequently ran the bounded fixed-vector diagnostic described
below; it performed no optimization or fit replay. This reviewer used local
receipts, outputs and source inspection only.

**The frozen non-regression check failed.** The retained evidence supports
changed stopping accuracy and start-dependent selection within the
near-zero-variance positive family as the leading explanation. The subsequent
controlled diagnostic finds exactly equal criteria under both sources at all
five retained vectors. It does not establish that the repaired nuisance
derivative is correct there. Neither the small LR changes nor an improvement
in one branch makes a failed criterion check acceptable.

## Evidence and unchanged verdict

The baseline is `99af5206b6a4e53f5b8e9d71cbf348f95e9ae574`; the repaired source
is `a77e849ce0b0381b5c378b222bacfadce9beaf96`. The 24 tasks and baseline hashes
were frozen before execution in `../paper1-sprint2-repair-2026-11-12/`.
The acceptance limits remain absolute criterion shift `1e-6`, profile-LR shift
`1e-3`, and unchanged eligibility at the exact same locations.

I read all 24 completed probe receipts under
`artifacts/sprint2/repair-20261112/final-20261115/probe-results/`: all 12,460
required anchors were present, with no probe errors. There are 22 passing tasks
and two failing tasks. Across their 22,488 criterion comparisons and 22,200 LR
comparisons, exactly three checks failed, all for criterion shift in the
standard positive-sigma family. There are no eligibility changes or failed LR
checks; the largest absolute LR shift is `6.139019205875229e-6`.

Use these task abbreviations only within this note:

- **W:** `fit-q-base-corridor-0-window_high-mu0.001-h10-C-exhaustive`.
- **C:** `fit-q-base-corridor-0-constant-mu0.004-h1-C-independent_bank`.

| Task, standard positive family | Baseline criterion | Candidate criterion | Candidate minus baseline | LR shift |
| --- | ---: | ---: | ---: | ---: |
| W, exact h=30 probe | -1896.2767000651468 | -1896.276701265026 | -1.199879307023366e-6 | +2.399758614046732e-6 |
| C, full-fit null h=1 | -1676.79605571835 | -1676.7960755026131 | -1.978426303139713e-5 | Not a separate LR row |
| C, exact h=1 probe | -1676.79605571835 | -1676.7960526488484 | +3.069501644858974e-6 | -6.139019205875229e-6 |

Both eligibility verdicts are true in every row. W uses the exact recorded log-h
`0x1.b35a6f90bd69bp+1`, converted by the existing clamp to h=30. C uses
`0x0.0p+0`. These are not interpolated or nearest-node comparisons.

The breaches are **not failures of every fitted family or of the spatial
envelope**. Every envelope, sigma-zero, tight-spatial, exposure and constant
comparison passes. Across all 24 tasks, the largest standard spatial-envelope
criterion shift is `1.5392288332805037e-8`; the largest tight positive-family
shift is `1.4263559933169745e-7`. The frozen plan nevertheless explicitly checks
the separate positive-sigma family, so its three failures control the verdict.

## What the retained optimizer states show

The projected-gradient infinity norms below are recorded quantities, not new
derivative calculations. The last column is the criterion advantage of the
separately fitted sigma-zero family at the same h.

| Task/state | Sigma | Projected gradient | Outer iterations | Sigma-zero minus positive criterion |
| --- | ---: | ---: | ---: | ---: |
| W, baseline standard | 0.0008362010077508787 | 4.9047863012978334e-5 | 13 | 1.6938315638981294e-7 |
| W, candidate full standard | 0.0023773208354244835 | 3.979420250812011e-4 | 19 | 1.3692629181605298e-6 |
| C, baseline standard | 0.00108461540457486 | 5.3469299694278765e-5 | 17 | 3.0974342735134996e-6 |
| C, candidate full standard | 0.0029478607017998214 | 3.9443946246290305e-4 | 15 | 2.2880534061187063e-5 |
| C, candidate exact standard probe | 0.00010000000000000009 | 4.6380897079165417e-4 | 3 | 2.7928535928367637e-8 |

All five rows report successful evaluations, eligible optimizer exits and
`projected gradient below tolerance; no ascent direction`. Their latent modes
strictly converged; the baseline mode-score norms are at most `3.19e-12` and
the repaired ones at most `1.74e-10`. The repaired full fits record no invalid
inner-trial rejections or mode failures. These are not observed inner-crash
recoveries or stalls at these endpoints.

W's new full fit and exact probe select exactly the same positive-family
parameters and criterion. The probe certifies its original point in one outer
iteration. C's new full fit and probe, using the same candidate source and
data at h=1, differ by **`2.2853764676256104e-5`** in criterion. The probe's
cached candidates retain the original null parameters with exactly the same
criterion and gradient as the original full fit, then select a better eligible
candidate at the unchanged lower sigma bound `1e-4`. Thus the within-candidate
discrepancy is observed selection among different parameter vectors, not a
different value for the same retained vector.

The additional start has an identifiable source. The exact probe starts from
the candidate's original point, neighboring original points and frozen free
fit before ordinary defaults. At C's first standard probe, h=1, source
`neighbour_or_default_2` corresponds to its frozen free fit, whose log-sigma is
already at the lower bound. The original full h=1 fit had only the ordinary
default and high-sigma anchor available. The extra probe start therefore gives
the fitter a route to the near-zero branch that the original null fit did not
retain. This demonstrates sensitivity to the available starts under the
current stopping rule; it does not justify replacing the failed null receipt.

The old standard positive fit for C was itself `3.0974342735134996e-6` below
the sigma-zero criterion, already greater than the symmetric component
comparison's `1e-6` limit. The improved new probe closes almost that whole gap
and consequently fails in the positive direction. An old approximately
optimized positive branch is therefore not an exact objective reference. That
observation explains why both better and worse fits can fail this check, and
does not change the check retrospectively.

## Source mechanism and limits of causal attribution

Repair B changes `_fit_family`'s internal target from `0.1*kkt_tolerance` to
`kkt_tolerance`. For standard fits these are respectively `1e-4` and `1e-3`;
eligibility remains `1e-3`. Both worsened new endpoints stop between the old
and new targets. Their sigma values are farther from zero than the corresponding
baseline values. The tight fits show the same ordering at smaller scale: W's
old/new sigmas are `0.00026249`/`0.00081099`, with gradients
`4.59383e-6`/`4.63616e-5`; their criterion shift remains below `1e-6`.
These observations are consistent with earlier stopping on a weakly identified
near-zero positive branch.

Repair C changes nuisance derivatives, which can also change optimizer paths
and endpoint selection. Its implementation does not replace the criterion
formula; the inner solver preserves its original valid-trial arithmetic and
strict convergence tests. The original retained summaries lack the full
gradient vector, outer curvature eigenvalues and predicted gain. Although
`optimizer_success`
requires the unchanged complete second-order check in this source, the numeric
curvature is not archived in these rows. It is therefore unjustified to assert
an objective-error bound from the gradient norm, prove flatness from an observed
Hessian, or rule out a residual derivative error. The later diagnostic below
does identify the gradient components at the five endpoints.

The relevant source is `src/latent_landscapes/spatial_profile.py` (stopping,
Richardson derivatives and eligibility), `scripts/qualify_spatial_profiles.py`
(starts and best eligible family selection), `scripts/audit_sprint2_pair.py`
(`AnchorSearch`'s additional original/free starts), and
`scripts/compare_solver_repair_replay.py` (the frozen symmetric comparisons).

## Completed fixed-vector diagnostic and scientific decision

The parent ran the agreed **post-outcome, observational** comparison as PBS job
880733, using one CPU with a 20-minute cap. It finished with exit status zero
in 53 seconds wall time and 35 seconds CPU, according to the parent's native
accounting check. The five exact vectors below were evaluated separately under
the two frozen sources with identical original inputs/runtime and no
optimization. The script was independently reviewed before its results were
inspected. Plan, script and output files are retained alongside this note.

| Task/state | h | Alpha | Beta | Log sigma | Detection SD |
| --- | ---: | ---: | ---: | ---: | ---: |
| W baseline | 30 | -7.6873038544938534 | -0.22298655591097474 | -7.0866415338872155 | 0.2132586969270118 |
| W candidate full/probe | 30 | -7.687303861766772 | -0.22298655297240366 | -6.041781124775699 | 0.21325869532450978 |
| C baseline | 1 | -5.422248841490678 | 0.051648881737176244 | -6.826529820657198 | 0.19330300570482983 |
| C candidate full | 1 | -5.422248847893498 | 0.05164888478969745 | -5.826675557535415 | 0.19330300072267045 |
| C candidate probe | 1 | -5.422246304661208 | 0.05165389673739461 | -9.210340371976182 | 0.19330295643415277 |

Independent inspection of `baseline.json` and `candidate.json` establishes:

- All five positive-family criteria are exactly equal across sources in the
  serialized outputs and exactly reproduce their stored receipt criteria.
- All five sigma-zero evaluations at the same nuisance parameters are exactly
  equal across sources. These are controlled evaluations, not refitted
  sigma-zero optima or replacements for the frozen envelope rows.
- The alpha, beta and log-sigma gradient components are exactly equal across
  sources at each vector. All five pairs of positive-family latent-mode
  summaries also agree across sources and report strict convergence.
- The detection-SD derivative changes, as intended by C: by approximately
  `-1.089e-5` at the two W vectors and `-2.615e-5` at the three C vectors.
  This comparison does not independently establish derivative accuracy.

| Task/state | Gradient norm under baseline source | Gradient norm under candidate source | Dominant candidate component |
| --- | ---: | ---: | --- |
| W baseline | 4.9047863012978334e-5 | 5.993751069269341e-5 | Detection SD |
| W candidate full/probe | 3.8705114617976856e-4 | 3.979420250812011e-4 | Detection SD |
| C baseline | 5.3469299694278765e-5 | 6.008990411479084e-5 | Detection SD |
| C candidate full | 3.9443946246290305e-4 | 3.9443946246290305e-4 | Alpha |
| C candidate probe | 4.6380897079165417e-4 | 4.6380897079165417e-4 | Beta |

These are infinity norms of the full criterion gradient. They equal the
projected norms here: at C's probe the active log-sigma coordinate is not the
largest component. Both original standard endpoints remain below the old
internal `1e-4` target under either source; both worsened repaired endpoints
exceed that target under either source and remain below the unchanged `1e-3`
eligibility threshold. This strengthens the stopping-accuracy explanation
without needing a claim that the repaired derivative is exact.

**Scoped conclusion:** there is no changed objective value at these five
vectors. The observed regressions compare different eligible endpoints of the
same numerically reproduced objective, and the constant-task probe demonstrably
selects a better endpoint from its additional start. The diagnostic supports
the stopping/start-selection explanation; it does not reconstruct the entire
optimization trajectory, prove global objective equality, certify objective
accuracy from gradients, or separate B's and C's contributions to every path.

The next scientific decision is whether the optimizer's absolute
stationarity rule supplies the accuracy required for separately reporting a
near-zero positive-family criterion. Any further diagnostic or repair needs a
written rationale and independent review. Do not lower the frozen thresholds,
replace tasks or retroactively declare envelope agreement sufficient. Predicted
gain can remain a diagnostic; it is not a rigorous acceptance certificate.
The first diagnostic question is answered without a campaign rerun; no further
compute or repair was undertaken here.

The two missing development-fit receipts are a separate walltime/execution
issue. They neither cause nor resolve these non-regression failures. The
corridor-1 window-low B envelope failures remain outside this repair's tuning
scope.

## Evidence identity and reproduction of this read-only assessment

The two baseline root/search receipts and candidate root receipts were
independently rehashed against the corresponding selected-probe bindings; all
six hashes agree. For both tasks, recorded data identities and the hashes of
public inputs, exposure, observations, arrival bank and compressed bank agree
between baseline and candidate.

- Baseline receipts: `artifacts/sprint2/repair-20261112/replay-scout/<task>/`.
- Candidate receipts and evaluation streams:
  `artifacts/sprint2/repair-20261112/final-20261115/fit-results/repair-<task>/attempt-0001/fit/`.
- Exact-probe receipts:
  `artifacts/sprint2/repair-20261112/final-20261115/selected-probes/<task>/receipt.json`.
- Full probe state, candidates and exact parameters:
  `artifacts/sprint2/repair-20261112/final-20261115/probe-checkpoints/<task>/spatial.standard--<log-h-hex>.json`.
- Aggregate ledger:
  `artifacts/sprint2/repair-20261112/final-20261115/replay-summary.json`.

For the fixed-vector diagnostic, both outputs bind the same plan/script SHA256,
Python/platform and runtime SIF SHA256
`e71239ad4246ba7a1037d3dd3bc3d29667b7c3081992d95ab33d5d979e3f12ce`.
All 110 recorded source-file hashes in each output were independently checked
against the corresponding pinned Git blobs. The five plan receipt hashes,
vectors and stored criteria also match the archived evidence. The two outputs'
loaded data identities and input-hash maps are identical; the executed script
freshly checks those input hashes on the target before evaluation.

To reproduce the diagnostic, use the retained `evaluate-fixed-vectors.py` and
`fixed-vector-plan.json` inside that pinned runtime. Set `PINNED_REPO` to a clean
checkout of the appropriate plan source, `VERSION` to `baseline` or `candidate`,
`ORIGINAL_ROOT` to the preserved original campaign, and `EVIDENCE_DIR` to this
directory. Run a separate process for each version with a new output filename:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
LL_RUNTIME_SIF_SHA256=e71239ad4246ba7a1037d3dd3bc3d29667b7c3081992d95ab33d5d979e3f12ce \
PYTHONPATH="$PINNED_REPO/src:$PINNED_REPO/scripts" \
python "$EVIDENCE_DIR/evaluate-fixed-vectors.py" \
  --plan "$EVIDENCE_DIR/fixed-vector-plan.json" \
  --original-root "$ORIGINAL_ROOT" --repo "$PINNED_REPO" \
  --version "$VERSION" --output "$EVIDENCE_DIR/$VERSION-reproduction.json"
```

This reviewer's work remained read-only apart from this diagnosis note. The
parent's fixed-vector job was an explicitly labelled diagnostic extension;
there were no new optimizer runs, threshold changes or production-source edits.
