# Goal 059 final independent review

4 October 2026, Hobart. **Decision: the registered run ended correctly as a
terminal negative map qualification. `public_ready=false`; no handoff to Fable
is warranted.** The failure is numerical certification, not a result about
effect recovery, calibration, power, coverage, or ecological inference.

## Scientific target and scope

The eventual Paper 1 target is the casewise exact-family decision about a
post-invasion hazard multiplier `h`, conditional on a fixed synthetic map,
sampling design, numerical arrival bank and complete nuisance-reference
procedure. Goal 059 was a preparation gate: establish that those fixed public
inputs and numerical machinery could be qualified before any sealed history
was drawn. The immediate quantity at the failed gate was narrower still:
whether the fitted box `beta in [-2,2]`, `mu <= .006` and `h <= 10` stays inside
the compressed transform domain `x <= 5` on the first structurally admissible
map.

The data-generating and observation processes therefore did not run at the
registered root. No public history, confirmatory reference, sealed history,
prey or predator observation, likelihood fit, screen, retained nuisance set,
Berger--Boos p-value, or declaration exists. The 64-row bank under
`qualify/arrival_bank/` is a mechanical-root qualification fixture, not the
registered `K=131,072` bank. It cannot support a scientific claim about the
production map or eventual procedure.

## Decisive findings

1. **The registered stopping rule was followed.** Attempt 0 was the first
   structurally valid Arc 3 candidate, with map seed
   `2286118029579671682` and sampling seed `12049465925351981407`. Its
   Gaussian-field checks passed: field shape `72 x 84`, embedding shape
   `142 x 166`, minimum eigenvalue `0.04181608164610457`, and reconstruction
   error `6.66e-16`. The frozen interval certificate returned
   `site_hazard_upper=0.05944609676570008` and
   `transform_x_upper=5.350148708913006`, above the fixed limit 5. The run
   stopped without trying another map.

2. **The independent frozen auditor reproduced the terminal failure.** Every
   map/design array, seed address, exposure array, artifact hash, certificate,
   field diagnostic and first-structural-candidate condition passed the
   map-only audit. The audit explicitly records
   `scientific_qualification_passed=false` and
   `terminal_negative_qualification=true`.

3. **The interval certificate is conservative on this map.** A separate
   deterministic calculation over the stored 6,048-cell exposure normalizer
   and all 160 sampled sites gives the actual continuous-box maximum at
   `beta=2`, `mu=.006`, `h=10`, site `cell_35_04`:

   - exact normalized hazard ratio: `9.0631832443458366...`;
   - maximum site hazard: `0.05437909946607502...`;
   - maximum transform value: `4.8941189519467518...`;
   - margin below the domain boundary: `0.1058810480532482`.

   For nonnegative beta, the site with maximum exposure is necessarily the
   maximizer. The log normalized ratio is concave, with derivative equal to
   that site's exposure minus the exponentially weighted whole-map mean. Its
   derivative remains positive at beta 2 (`0.2871262663`), so the branch
   maximum is the endpoint. For negative beta, the minimum-exposure site is
   the only candidate; its unique stationary maximum occurs near beta
   `-1.6613888695` and gives `x=1.2092469962`. The positive endpoint is thus
   the global maximum. The winning value was re-evaluated at 80-decimal
   precision from exact conversions of the stored float64 values.

   The interval construction exceeds the actual maximum by `0.45602975697`
   in transform units and inflates the hazard bound by 9.32%. This is a false
   negative of the sufficient enclosure relative to the intended finite-map
   domain property. It does not retroactively turn the registered run into a
   pass: the frozen algorithm failed its prespecified gate and the run stopped
   correctly. The calculation and input hashes are preserved in
   [independent-map-diagnosis.json](../../../artifacts/goal059_execution/independent-map-diagnosis.json).

   A bounded refinement using the identical enclosure is sufficient and is
   methodologically leaner than introducing a root-solving certificate. With
   the same endpoint numerator upper bound, whole-map denominator lower bound
   and outward rounding, 320 equal beta intervals still give `x=5.0049877292`
   and fail; 384 give `x=4.9863660980` and pass. Fixed power-of-two partitions
   of 512, 1,024 and 2,048 give `x=4.9631699802`, `4.9285439278` and
   `4.9113063526`, respectively. These are post-stop diagnostics, not reruns
   or reclassifications of the registered result.

4. **Provenance and failure recovery are coherent.** I independently checked
   all 51 returned artifact hashes and their declared total of 45,619,719
   bytes. The 44,446,852-byte v3 archive matches its recorded SHA-256, and all
   273 archived files match the v3 source manifest. Relative to v2, v3 adds
   only the previously omitted
   `artifacts/goal056_execution/panel/panel/manifest.json`; no common file
   changed. The v2 run stopped during regression testing with 272 passes and
   six `FileNotFoundError` failures before mechanical qualification or any
   registered generation. The final Linux run passed 278 tests, Ruff and
   strict mypy. Mechanical qualification passed at root 987654321, including
   all 17 domain points, repeat fits and the adjusted-pair primitive. Both
   supervised v3 process groups report no remaining members.

## Assumptions and failure-mode assessment

The map diagnosis assumes the stored exposure arrays are the registered map;
that identity is supported independently by the map audit and hashes. The
continuous maximization applies to the exact-family hazard normalization used
by the fitted box. It does not certify the stochastic B100-A background, but
that branch is outside the fitted exact-family transform parameterization and
was never generated in this run.

The calculation is strong numerical evidence rather than a formal
machine-checked interval proof. Its boundary margin is about 2.12% of the
allowed transform range, much larger than float64 rounding, and the maximizing
branch is separated from the negative-beta branch by 3.68 transform units.
An independent implementation in the frozen Linux runtime would nevertheless
be appropriate before replacing a prospective gate.

Identifiability, h--beta--mu--detection trade-offs, boundary estimates,
optimizer multimodality, finite-bank error, profile stability, held-out
prediction, misspecification, selection by the nuisance screen, Monte Carlo
calibration and four-case dependence remain unassessed for this map. Mechanical
tests establish code identities on synthetic patterns; they do not resolve
those scientific risks. Spatial dependence is built into the planned generator
and cluster-held-out design, but no realized observations exist with which to
assess it. There is no missingness, censoring, extrapolation, multiple testing
or uncertainty-propagation result to interpret because execution stopped
upstream of those stages.

The earlier development preview remains a provenance limitation. It exposed
the root under an incorrect constructor, but the corrected structural-first
rule and terminal behavior were frozen before this registered run. Selecting a
new candidate or root in response to this failure would introduce a clear
selection effect and would violate the registered stopping rule.

## Recommendation

Close this Goal 059 execution as a valid negative numerical qualification and
do not hand the package to Fable. Do not reroll the map, expand the transform
domain, construct the registered bank, generate public fixtures, materialize
confirmatory references, or draw sealed histories under the failed
registration.

The narrow next scientific decision is whether the intended gate is the actual
finite-map condition `max x <= 5` or the particular 80-interval enclosure. If
the actual condition is intended, the evidence supports a separately approved,
prospectively frozen recovery goal that retains this same map, root, design,
parameter box, domain and enclosure algorithm and changes only the prospectively
fixed beta partition from 80 to **1,024 equal intervals**. This preserves the
existing proof structure, avoids optimizer or root-finding behavior, costs only
about 12.4 million map-cell endpoint evaluations, and retains a transform-bound
margin of `0.0714560722` on the known map. The concavity calculation above can
remain an independent diagnostic rather than become production machinery.

The new registration must disclose that the map and favorable refinement table
are known, freeze 1,024 before execution, retain the existing outward rounding,
and require locked-Linux reproduction plus an independent map-only audit before
any bank or history draw. It must not adaptively stop partition refinement after
the first passing resolution. If this post-outcome gate amendment is judged
unacceptable, the programme should retain the negative result and stop this
capstone branch.

Independent scientific review would materially affect confidence in a gate
amendment because the map outcome is now known. It is unlikely to change the
present decision: the frozen interval certificate failed, the stop and audit
are valid, and there are no inferential results to rescue or reinterpret.
